"""Refuse a lease whose work the base already satisfies (S8).

T-0145 attempt 2 was re-leased onto a base that already contained the change
(``e08fa8d``), so its agents spent the attempt discovering that the task was
"already passing".  The check here is not a heuristic: it runs the task's own
oracles on a throwaway worktree of the default branch, exactly as the harness
would run them after the work.

Failure to run the check (git error, timeout) is **advisory**: it never blocks
a lease.  Only a full pass of every oracle blocks, and only when the fleet
config enables it.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

__all__ = ["oracles_already_pass"]


def oracles_already_pass(kernel, task, *, timeout: int = 600) -> tuple[bool, list[dict]]:
    """Return ``(all_passed, results)`` for *task*'s oracles on the base.

    ``all_passed`` is False when the check could not run, so a broken
    precheck can never suppress real work.
    """
    # Imported here: harness imports this module from ``start``; a module-level
    # import would close the cycle.
    from .harness import run_command

    repo = kernel.repo
    oracles = list(getattr(task, "oracles", []) or [])
    if not oracles:
        return False, []

    temp_dir = Path(tempfile.mkdtemp(prefix="pmk-precheck-"))
    worktree = temp_dir / "tree"
    code, out, err = repo.git("worktree", "add", "--detach", str(worktree),
                              repo.default_branch())
    if code != 0:
        return False, [{"error": f"precheck worktree: {(err or out).strip()}"}]

    results: list[dict] = []
    try:
        for oracle in oracles:
            exit_code, _stdout, _stderr = run_command(oracle, worktree, timeout=timeout)
            results.append({"cmd": oracle, "exit": exit_code, "ok": exit_code == 0})
    finally:
        repo.git("worktree", "remove", "--force", str(worktree))

    return all(result.get("ok") for result in results), results
