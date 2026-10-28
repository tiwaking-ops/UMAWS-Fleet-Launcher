"""The serial merge queue (pilot v1 section 9.5; fleet amendment section 10).

The queue is **serial**: one merge at a time, in the main tree, so that the
gate runs on the tree that will actually become canonical.

For each submitted lease:

1. Commit the worker's changes on the lease branch.  The worker commits
   nothing itself (constitution point 3 and the order's rules); the harness
   does the committing.
2. Create a temporary worktree from ``main``.
3. Merge the lease branch there (no fast-forward, so the merge is
   recorded).
4. Run the **gate command** on the merged tree.
5. Green: fast-forward ``main`` to the merge commit.  Red: abandon the
   merge, record the conflict, and leave the task in REWORK.

Nothing is promoted without a passing gate.  That is invariant I5.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from pmk.api import Kernel, KernelError


@dataclass
class MergeResult:
    """The outcome of one integration attempt."""

    ok: bool = False
    task: str = ""
    commit: str = ""
    gate_cmd: str = ""
    gate_exit: int | None = None
    conflict: bool = False
    message: str = ""
    files: list = field(default_factory=list)
    failure_class: str = ""  # "" (ok), "GATE_FAILED", "INFRASTRUCTURE_FAILED"

    def to_dict(self) -> dict:
        return {"ok": self.ok, "task": self.task, "commit": self.commit,
                "gate_cmd": self.gate_cmd, "gate_exit": self.gate_exit,
                "conflict": self.conflict, "message": self.message,
                "files": self.files, "failure_class": self.failure_class}


def commit_worktree(repo, worktree: str | Path, message: str,
                    paths: list | None = None) -> tuple[bool, str]:
    """Commit the worker's changes on the lease branch.

    The harness commits, never the worker.

    Only the paths in *paths* (the task's declared write scope) are
    staged.  ``git add -A`` would also stage the harness's own artefacts —
    ``.pmwork/ORDER.md`` and the agent's session file — and two leases
    would then conflict on the order file when their branches merge.  It
    would also commit work that the scope check had already flagged as a
    violation, which is exactly the work that must not be promoted.
    """
    if paths:
        for path in paths:
            repo.git("add", "--", path, cwd=Path(worktree))
    else:
        repo.git("add", "-A", cwd=Path(worktree))
    code, status, err = repo.git("status", "--porcelain",
                                 "--untracked-files=all", cwd=Path(worktree))
    if code != 0:
        return False, err or status
    if not status.strip():
        return True, ""            # nothing to commit
    code, out, err = repo.git("commit", "-m", message, cwd=Path(worktree))
    if code != 0:
        return False, err or out
    _, commit, _ = repo.git("rev-parse", "HEAD", cwd=Path(worktree))
    return True, commit.strip()


def integrate(kernel: Kernel, task, lease, worktree: str | Path, *,
              gate_cmd: str = "", keep_worktree: bool = True) -> MergeResult:
    """Run one lease through the merge queue."""
    from .harness import scope_check

    repo = kernel.repo
    result = MergeResult(task=task.id)

    # A scope violation is a refusal to promote, not something to merge.
    scope = scope_check(task, worktree, repo)
    if not scope["ok"]:
        result.message = (f"the worker changed {len(scope['violations'])} "
                          f"file(s) outside its write scope: "
                          + ", ".join(v["path"] for v in scope["violations"]))
        kernel.record_event("ORACLE_RESULT", subject=task.id, fence=lease.fence,
                            payload={"stage": "scope", "ok": False,
                                     "violations": scope["violations"]})
        return result

    # --- I5 pre-merge check: bundle must exist and all oracles pass ---
    # Defense-in-depth: even if caller bypasses Conductor, the merge queue
    # itself refuses a failing-oracle bundle before any fast-forward.
    # Uses the SAME shared path as the conductor (Bundle.load_for_task +
    # validation_problems) so Kernel.integrate and merge.py cannot disagree.
    from pmk.bundle import Bundle
    bundle = Bundle.load_for_task(kernel.repo.evidence_dir, task.id, lease.fence)
    if bundle is None:
        bundle_path = Bundle.bundle_path(kernel.repo.evidence_dir,
                                         task.id, lease.fence)
        kernel.record_event("MERGE_REFUSED", subject=task.id,
                            fence=lease.fence,
                            payload={"reason": "no_bundle",
                                     "message": f"no evidence bundle at {bundle_path}"})
        result.message = "no evidence bundle"
        return result

    problems = bundle.validation_problems()
    if problems:
        kernel.record_event("MERGE_REFUSED", subject=task.id,
                            fence=lease.fence,
                            payload={"reason": "oracles_failed",
                                     "message": "acceptance oracles failed: "
                                                + (", ".join(problems) or "unknown")})
        result.message = "acceptance oracles failed: " + (", ".join(problems))
        return result

    branch = f"pmk/{task.id}-{lease.fence}"
    main_branch = repo.default_branch()

    message = f"feat({task.id}): {task.title}\n\nFence {lease.fence}.\n"
    ok, detail = commit_worktree(repo, worktree, message, task.write_scope)
    if not ok:
        result.failure_class = "INFRASTRUCTURE_FAILED"
        kernel.record_event("INFRASTRUCTURE_FAILED", subject=task.id,
                            fence=lease.fence,
                            payload={"stage": "commit",
                                     "message": f"could not commit the worktree: {detail}"})
        result.message = f"could not commit the worktree: {detail}"
        return result

    # --- pytest.ini collision cleanup (T-0009) ---
    # Must run AFTER commit_worktree so the branch ref has the commit and
    # ``git diff --name-only <base>..<branch>`` reveals the incoming change.
    # If the root-level pytest.ini is UNTRACKED and byte-identical to the
    # Kernel's default, delete it so the fast-forward below won't refuse to
    # overwrite an untracked working-tree copy.  Never delete a tracked or
    # user-modified file.
    _cleanup_default_pytest_ini(repo, task, branch)

    # Recorded defect, fixed 2026-10-24: a clean worktree used to
    # short-circuit straight to ``ok`` here -- "the worker changed
    # nothing".  For a *re-integration* of a lease whose work is already
    # committed (the first merge crashed halfway, the close-out is
    # re-run) that returned ok **without the gate ever running** --
    # invariant I5's promise, skipped quietly.  There is no early exit
    # any more: both cases -- an already-committed lease, and a worker
    # that truly wrote nothing -- go through the merge stage below,
    # where the lease branch is merged (a no-op when it is already in
    # main) and the gate runs on the tree that would actually become
    # canonical.  Only a green gate reaches ``ok``.
    changed_nothing = not detail

    merge_dir = Path(tempfile.mkdtemp(prefix="pmk-merge-"))
    target = merge_dir / "merge"
    try:
        code, out, err = repo.git("worktree", "add", "--detach", str(target),
                                  main_branch)
        if code != 0:
            result.message = (f"could not create the merge worktree: "
                              f"{err or out}")
            result.failure_class = "INFRASTRUCTURE_FAILED"
            kernel.record_event("INFRASTRUCTURE_FAILED", subject=task.id,
                                fence=lease.fence,
                                payload={"stage": "merge-worktree",
                                         "message": f"git worktree add failed: {err or out}"})
            return result
        _, pre_head, _ = repo.git("rev-parse", "HEAD", cwd=target)
        pre_head = pre_head.strip()

        code, out, err = repo.git("merge", "--no-ff", "--no-edit", branch,
                                  cwd=target)
        if code != 0:
            # A merge conflict is deterministic: the same branch+base will
            # conflict every time.  It is NOT an infrastructure transient --
            # retrying it will not help.  Classify as GATE_FAILED so the
            # conductor does not burn INFRA_RETRY budget, and the task goes
            # to REWORK for the worker to resolve.
            result.conflict = True
            result.message = (f"merge conflict: {err or out}").strip()
            repo.git("merge", "--abort", cwd=target)
            result.failure_class = "GATE_FAILED"
            kernel.record_event("ORACLE_RESULT", subject=task.id,
                                fence=lease.fence,
                                payload={"stage": "merge",
                                         "ok": False,
                                         "message": result.message})
            return result

        # Structural up-to-date detection instead of parsing git's
        # output (whose wording is locale-dependent): the merge is a
        # no-op exactly when HEAD did not move.
        _, post_head, _ = repo.git("rev-parse", "HEAD", cwd=target)
        already_merged = pre_head == post_head.strip()

        if already_merged:
            # No new merge commit: without this guard the diff below
            # would report the *previous* merge's files as this one's.
            result.files = []
        else:
            _, files, _ = repo.git("diff", "--name-only", "HEAD~1", "HEAD",
                                   cwd=target)
            result.files = [f for f in files.splitlines() if f.strip()]

        if gate_cmd:
            import subprocess
            try:
                proc = subprocess.run(gate_cmd, shell=True, cwd=str(target),
                                      capture_output=True, timeout=900,
                                      text=True, encoding="utf-8",
                                      errors="replace")
                result.gate_cmd = gate_cmd
                result.gate_exit = proc.returncode
            except (subprocess.SubprocessError, OSError) as exc:
                result.gate_cmd = gate_cmd
                result.gate_exit = 127
                result.message = f"the gate command failed to run: {exc}"
                return result
            if result.gate_exit != 0:
                result.message = (f"the gate command {gate_cmd!r} exited "
                                  f"{result.gate_exit}")
                kernel.record_event("ORACLE_RESULT", subject=task.id,
                                    fence=lease.fence,
                                    payload={"stage": "gate", "ok": False,
                                             "cmd": gate_cmd,
                                             "exit": result.gate_exit,
                                             "reintegration": changed_nothing})
                return result

        # Green: fast-forward the main branch **and** the main working
        # tree.  Moving the ref with `update-ref` is not enough: git does
        # not touch the index or the working tree, so the merged files
        # would never appear on disk and the close-check would not see
        # them.  `merge --ff-only` does both, and it refuses rather than
        # overwriting local changes in the main tree.
        _, merge_commit, _ = repo.git("rev-parse", "HEAD", cwd=target)
        merge_commit = merge_commit.strip()
        code, out, err = repo.git("merge", "--ff-only", merge_commit)
        if code != 0:
            result.message = (f"could not fast-forward the main tree: "
                              f"{err or out}").strip()
            result.failure_class = "INFRASTRUCTURE_FAILED"
            kernel.record_event("INFRASTRUCTURE_FAILED", subject=task.id,
                                fence=lease.fence,
                                payload={"stage": "fast-forward",
                                         "message": result.message})
            return result

        result.ok = True
        result.commit = merge_commit
        if changed_nothing:
            result.message = ("the worker changed nothing (re-integration: "
                              "the gate re-ran and passed)" if gate_cmd
                              else "the worker changed nothing")
        else:
            result.message = "merged"
        kernel.record_event("ORACLE_RESULT", subject=task.id, fence=lease.fence,
                            payload={"stage": "gate", "ok": True,
                                     "cmd": gate_cmd,
                                     "reintegration": changed_nothing})
        return result
    finally:
        try:
            repo.git("worktree", "remove", "--force", str(target))
        except Exception:                       # noqa: BLE001
            pass
        shutil.rmtree(merge_dir, ignore_errors=True)


#: The exact pytest.ini content the Kernel writes on ``pmk init``.
#: Used to detect an untracked, byte-identical file so it can be removed
#: before a merge (T-0009 pytest.ini collision).
_DEFAULT_PYTEST_INI = (
    "[pytest]\n"
    "norecursedirs = work work/.pm/tmp .venv .git __pycache__\n"
    "testpaths = tests\n"
)


def _cleanup_default_pytest_ini(repo, task, branch: str) -> None:
    """Remove an untracked, default pytest.ini from the repo root.

    ``pmk init`` writes ``pytest.ini`` to the repo root so that ``pytest``
    run from the root does not descend into worktrees, ``.venv``, etc.
    When a worker's merge brings in its own ``pytest.ini``, git sees two
    untracked files at the same path and the fast-forward refuses to
    overwrite the untracked working-tree copy (T-0009).

    We only act when the incoming branch actually changes ``pytest.ini`` --
    either because the task's write scope declares it, or because it appears
    in ``git diff --name-only <base>..<branch>``.  This check must run AFTER
    ``commit_worktree`` so the branch ref has the commit and the diff is
    visible.  An unrelated merge (one that does not touch pytest.ini) must
    leave the Kernel-written root file in place.

    If the root-level ``pytest.ini`` is **untracked** and **byte-identical**
    to the Kernel default, it is deleted -- the incoming commit will re-create
    it tracked.  A file that is **tracked** or **user-modified** is left
    untouched.
    """
    from pathlib import Path

    # Only proceed if the incoming branch adds or modifies pytest.ini.
    base = repo.default_branch()
    code, changed, _ = repo.git("diff", "--name-only", f"{base}..{branch}")
    if code != 0 or "pytest.ini" not in changed.split():
        return  # unrelated merge -- leave the root pytest.ini alone

    target = Path(repo.root) / "pytest.ini"
    if not target.is_file():
        return
    # Check if it's tracked by git -- never touch tracked files.
    code, tracked, _ = repo.git("ls-files", "--", "pytest.ini")
    if code == 0 and tracked.strip():
        return  # tracked -- leave it alone
    # Check if it's byte-identical to the default.
    try:
        content = target.read_text(encoding="utf-8")
    except OSError:
        return
    if content == _DEFAULT_PYTEST_INI:
        target.unlink()
