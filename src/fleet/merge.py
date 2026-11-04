"""The serial merge queue (pilot v1 section 9.5; fleet amendment section 10).

The queue is **serial**: one merge at a time.  The merge and gate run in a
temporary worktree created from a clean main HEAD, so the main working tree
is never left in a half-merged state.  Only a passing gate results in a
fast-forward of main.

For each submitted lease:

1. Commit the worker's changes on the lease branch.  The worker commits
   nothing itself (constitution point 3 and the order's rules); the harness
   does the committing.
2. Create a temporary worktree from ``main`` (detached HEAD).
3. Merge the lease branch there (no fast-forward, so the merge is
   recorded).
4. Run the **gate command** on the merged tree in the temp worktree.
5. Red: abandon the merge in the temp worktree, record the conflict,
   clean up the temp worktree, and leave the task in REWORK.
6. Green: attempt ``git merge --ff-only <temp-commit>`` in the main tree.
   - If main's HEAD has moved since the temp worktree was created (base),
     rebuild from step 2 (at most 2 retries).
   - If git refuses the fast-forward due to uncommitted changes in main
     that overlap with the merge, record INFRASTRUCTURE_FAILED with git's
     message; main is untouched; no retry loop.
   - On success: result.commit = main's HEAD after the fast-forward.

Nothing is promoted without a passing gate.  That is invariant I5.

--- Recorded defect, fixed 2026-10-24: a clean worktree used to
short-circuit straight to ``ok`` here -- "the worker changed
nothing".  For a *re-integration* of a lease whose work is already
committed (the first merge crashed halfway, the close-out is
re-run) that returned ok **without the gate ever running** --
invariant I5's promise, skipped quietly.  There is no early exit
any more: both cases -- an already-committed lease, and a worker
that truly wrote nothing -- go through the merge stage below,
where the lease branch is merged (a no-op when it is already in
main) and the gate runs on the tree that would actually become
canonical.  Only a green gate reaches ``ok``.

--- I5 pre-merge check: bundle must exist and all oracles pass ---
Defense-in-depth: even if caller bypasses Conductor, the merge queue
itself refuses a failing-oracle bundle before any fast-forward.
Uses the SAME shared path as the conductor (Bundle.load_for_task +
validation_problems) so Kernel.integrate and merge.py cannot disagree.
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
    """Run one lease through the merge queue.

    B-R2b: The merge and gate run in a TEMP WORKTREE (not the main tree).
    1. git worktree add --detach <temp> HEAD, recording base = that sha.
    2. In <temp>: git merge --no-ff -m <msg> <task branch>. Conflict ->
       git merge --abort with cwd=<temp>, classify as before, remove <temp>.
    3. Run the gate in <temp>.
    4. Green: if main's HEAD != base, rebuild from step 1 (at most 2 retries),
       else requeue with a clear INFRASTRUCTURE_FAILED stage "main-moved".
    5. git merge --ff-only <temp commit> in main. If git refuses (dirty
       overlap), record INFRASTRUCTURE_FAILED with git's message; main is
       untouched; no retry loop.
    6. result.commit = main's HEAD after the fast-forward. Always remove
       <temp> and its temp branch.
    Keep the "changed nothing" reintegration behaviour.
    """
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
    _cleanup_default_pytest_ini(repo, task, branch)

    changed_nothing = not detail

    # Record main's HEAD before merge (the "base" for retry detection)
    _, base_head, _ = repo.git("rev-parse", "HEAD")
    base_head = base_head.strip()

    # B-R2b: Create temp worktree from clean main HEAD
    merge_dir = Path(tempfile.mkdtemp(prefix="pmk-merge-"))
    temp_wt = merge_dir / "merge"
    max_retries = 2
    retry_count = 0

    try:
        while retry_count <= max_retries:
            # Step 1: Create temp worktree from current main HEAD
            code, out, err = repo.git("worktree", "add", "--detach", str(temp_wt), main_branch)
            if code != 0:
                result.message = (f"could not create the merge worktree: {err or out}")
                result.failure_class = "INFRASTRUCTURE_FAILED"
                kernel.record_event("INFRASTRUCTURE_FAILED", subject=task.id,
                                    fence=lease.fence,
                                    payload={"stage": "merge-worktree",
                                             "message": f"git worktree add failed: {err or out}"})
                return result

            try:
                # Record the base HEAD of the temp worktree
                _, temp_base_head, _ = repo.git("rev-parse", "HEAD", cwd=temp_wt)
                temp_base_head = temp_base_head.strip()

                # Step 2: Merge lease branch in temp worktree with --no-ff
                code, out, err = repo.git("merge", "--no-ff", "--no-edit", branch, cwd=temp_wt)
                if code != 0:
                    # Merge conflict - deterministic, not transient
                    result.conflict = True
                    result.message = (f"merge conflict: {err or out}").strip()
                    repo.git("merge", "--abort", cwd=temp_wt)
                    result.failure_class = "GATE_FAILED"
                    kernel.record_event("ORACLE_RESULT", subject=task.id,
                                        fence=lease.fence,
                                        payload={"stage": "merge",
                                                 "ok": False,
                                                 "message": result.message})
                    return result

                # Check if merge was a no-op (already in main): no new commit
                _, post_head, _ = repo.git("rev-parse", "HEAD", cwd=temp_wt)
                already_merged = temp_base_head == post_head.strip()

                if already_merged:
                    # No new merge commit
                    _, merge_commit, _ = repo.git("rev-parse", "HEAD", cwd=temp_wt)
                    merge_commit = merge_commit.strip()
                    result.files = []
                else:
                    _, files, _ = repo.git("diff", "--name-only", "HEAD~1", "HEAD", cwd=temp_wt)
                    result.files = [f for f in files.splitlines() if f.strip()]
                    _, merge_commit, _ = repo.git("rev-parse", "HEAD", cwd=temp_wt)
                    merge_commit = merge_commit.strip()

                # Step 3: Run the gate in the temp worktree
                if gate_cmd:
                    import subprocess
                    try:
                        proc = subprocess.run(gate_cmd, shell=True, cwd=str(temp_wt),
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
                        result.failure_class = "GATE_FAILED"
                        kernel.record_event("ORACLE_RESULT", subject=task.id,
                                            fence=lease.fence,
                                            payload={"stage": "gate", "ok": False,
                                                     "cmd": gate_cmd,
                                                     "exit": result.gate_exit,
                                                     "reintegration": changed_nothing})
                        # Abort the merge in temp worktree
                        repo.git("merge", "--abort", cwd=temp_wt)
                        return result

                # Step 4: Gate passed - check if main's HEAD has moved
                _, current_main_head, _ = repo.git("rev-parse", "HEAD")
                current_main_head = current_main_head.strip()

                if current_main_head != base_head:
                    # Main has moved since we started - retry if we haven't exhausted retries
                    repo.git("merge", "--abort", cwd=temp_wt)
                    # Clean up this temp worktree before retry
                    try:
                        repo.git("worktree", "remove", "--force", str(temp_wt))
                    except Exception:
                        pass
                    shutil.rmtree(merge_dir, ignore_errors=True)
                    # Recreate merge_dir for next iteration
                    merge_dir = Path(tempfile.mkdtemp(prefix="pmk-merge-"))
                    temp_wt = merge_dir / "merge"
                    base_head = current_main_head
                    retry_count += 1
                    if retry_count > max_retries:
                        result.message = (f"main branch moved during merge after {max_retries} retries; "
                                          f"requeue with INFRASTRUCTURE_FAILED")
                        result.failure_class = "INFRASTRUCTURE_FAILED"
                        kernel.record_event("INFRASTRUCTURE_FAILED", subject=task.id,
                                            fence=lease.fence,
                                            payload={"stage": "main-moved",
                                                     "message": result.message,
                                                     "base_head": base_head,
                                                     "current_main_head": current_main_head})
                        return result
                    continue  # retry

                # Step 5: Fast-forward main with --ff-only
                code, out, err = repo.git("merge", "--ff-only", merge_commit)
                if code != 0:
                    # Git refused --ff-only (dirty overlap or other issue)
                    # Main is untouched; no retry loop
                    repo.git("merge", "--abort", cwd=temp_wt)
                    result.message = (f"could not fast-forward main: {err or out}").strip()
                    result.failure_class = "INFRASTRUCTURE_FAILED"
                    kernel.record_event("INFRASTRUCTURE_FAILED", subject=task.id,
                                        fence=lease.fence,
                                        payload={"stage": "fast-forward",
                                                 "message": result.message})
                    return result

                # Step 6: Success - result.commit = main's HEAD after fast-forward
                _, final_head, _ = repo.git("rev-parse", "HEAD")
                final_head = final_head.strip()
                result.ok = True
                result.commit = final_head
                if changed_nothing:
                    result.message = ("the worker changed nothing (re-integration: "
                                      "the gate re-ran and passed)" if gate_cmd
                                      else "the worker changed nothing")
                else:
                    result.message = "merged"
                kernel.record_event("ORACLE_RESULT", subject=task.id, fence=lease.fence,
                                    payload={"stage": "gate", "ok": True,
                                             "cmd": gate_cmd,
                                             "reintegration": already_merged,
                                             "no_ff_fallback": False})
                return result

            finally:
                # Always clean up temp worktree
                try:
                    repo.git("worktree", "remove", "--force", str(temp_wt))
                except Exception:
                    pass

    finally:
        shutil.rmtree(merge_dir, ignore_errors=True)

    # Should not reach here
    result.message = "merge queue exhausted retries"
    result.failure_class = "INFRASTRUCTURE_FAILED"
    return result


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
