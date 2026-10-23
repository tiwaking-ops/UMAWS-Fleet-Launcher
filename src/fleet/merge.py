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

    def to_dict(self) -> dict:
        return {"ok": self.ok, "task": self.task, "commit": self.commit,
                "gate_cmd": self.gate_cmd, "gate_exit": self.gate_exit,
                "conflict": self.conflict, "message": self.message,
                "files": self.files}


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

    message = f"feat({task.id}): {task.title}\n\nFence {lease.fence}.\n"
    ok, detail = commit_worktree(repo, worktree, message, task.write_scope)
    if not ok:
        result.message = f"could not commit the worktree: {detail}"
        return result

    branch = f"pmk/{task.id}-{lease.fence}"

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
                                  "main")
        if code != 0:
            result.message = f"could not create the merge worktree: {err or out}"
            return result
        _, pre_head, _ = repo.git("rev-parse", "HEAD", cwd=target)
        pre_head = pre_head.strip()

        code, out, err = repo.git("merge", "--no-ff", "--no-edit", branch,
                                  cwd=target)
        if code != 0:
            result.conflict = True
            result.message = (f"merge conflict: {err or out}").strip()
            repo.git("merge", "--abort", cwd=target)
            kernel.record_event("ORACLE_RESULT", subject=task.id,
                                fence=lease.fence,
                                payload={"stage": "merge", "ok": False,
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
            kernel.record_event("ORACLE_RESULT", subject=task.id,
                                fence=lease.fence,
                                payload={"stage": "fast-forward", "ok": False,
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
