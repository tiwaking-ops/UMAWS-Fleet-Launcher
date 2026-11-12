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

from pathlib import Path

from . import scratch

__all__ = ["dry_run", "oracles_already_pass"]


def oracles_already_pass(kernel, task, *, timeout: int = 600,
                         temp_root: Path | str | None = None
                         ) -> tuple[bool, list[dict]]:
    """Return ``(all_passed, results)`` for *task*'s oracles on the base.

    ``all_passed`` is False when the check could not run, so a broken
    precheck can never suppress real work.

    *temp_root* places the throwaway directory under a caller-owned root
    (a pytest-managed ``tmp_path`` in tests); see :mod:`fleet.scratch`.
    """
    # Imported here: harness imports this module from ``start``; a module-level
    # import would close the cycle.
    from .harness import run_command
    from .runenv import import_origin_problems

    repo = kernel.repo
    oracles = list(getattr(task, "oracles", []) or [])
    if not oracles:
        return False, []

    temp_dir = scratch.scratch_dir("pmk-precheck-", temp_root)
    worktree = temp_dir / "tree"
    try:
        code, out, err = repo.git("worktree", "add", "--detach", str(worktree),
                                  repo.default_branch())
        if code != 0:
            return False, [{"error": f"precheck worktree: {(err or out).strip()}"}]

        results: list[dict] = []
        origin_problems = import_origin_problems(worktree)
        if origin_problems:
            results.append({"cmd": "<import-origin>", "exit": 1, "ok": False,
                            "error": "; ".join(origin_problems)})
            return False, results

        for oracle in oracles:
            exit_code, _stdout, _stderr = run_command(oracle, worktree, timeout=timeout)
            results.append({"cmd": oracle, "exit": exit_code, "ok": exit_code == 0})
    finally:
        repo.git("worktree", "remove", "--force", str(worktree))
        # The directory around the worktree is ours too.  Removing only the
        # worktree is what left an empty ``pmk-precheck-*`` husk behind on
        # every lease admission -- 412 of them before this line existed.
        scratch.remove_scratch(temp_dir)

    return all(result.get("ok") for result in results), results


def _add_worktree(repo, path: Path, ref: str) -> tuple[bool, str]:
    code, out, err = repo.git("worktree", "add", "--detach", str(path), ref)
    return code == 0, (err or out).strip()


def _run_oracles(oracles, worktree: str | Path, timeout: int) -> list[dict]:
    from .harness import run_command

    rows: list[dict] = []
    for oracle in oracles:
        exit_code, stdout, stderr = run_command(oracle, worktree, timeout=timeout)
        rows.append({
            "cmd": oracle,
            "exit": exit_code,
            "ok": exit_code == 0,
            # Tails, not full output: enough to see why a canary oracle failed
            # without turning the report into a log dump.
            "stdout_tail": (stdout or "")[-800:],
            "stderr_tail": (stderr or "")[-800:],
        })
    return rows


def dry_run(kernel, task, *, base_ref: str = "", patch=None,
            scratch_ref: str = "", timeout: int = 600,
            temp_root: Path | str | None = None) -> dict:
    """Run *task*'s oracles at the base and on a scratch implementation.

    A canary card is valid only when its oracle **fails at the current base**
    and **passes on a tree that contains the intended work**.  This runs both
    sides in throwaway detached worktrees and writes nothing: no claim, no
    lease, no task transition.  *patch* is a ``git apply``-able file for the
    scratch tree; *scratch_ref* instead selects a ref that already contains
    the implementation.

    Returns a report dict.  ``canary_valid`` is true only when at least one
    oracle fails at the base and every oracle passes on scratch.
    """
    repo = kernel.repo
    oracles = [str(oracle) for oracle in (getattr(task, "oracles", []) or [])]
    report: dict = {
        "task": getattr(task, "id", ""),
        "state": getattr(task, "state", ""),
        "base_ref": "",
        "scratch_ref": "",
        "patch": "",
        "oracles": oracles,
        "base": {"all_pass": False, "oracles": []},
        "scratch": {"all_pass": False, "oracles": []},
        "canary_valid": False,
        "reason": "",
    }
    if not oracles:
        report["reason"] = "the card declares no oracles"
        return report

    base_ref = str(base_ref or repo.default_branch())
    scratch_ref = str(scratch_ref or base_ref)
    patch_path = Path(patch).expanduser().resolve() if patch else None
    report["base_ref"] = base_ref
    report["scratch_ref"] = scratch_ref
    report["patch"] = str(patch_path) if patch_path else ""

    temp_dir = scratch.scratch_dir("pmk-precheck-dry-", temp_root)
    base_wt = temp_dir / "base"
    scratch_wt = temp_dir / "scratch"
    try:
        ok, detail = _add_worktree(repo, base_wt, base_ref)
        if not ok:
            report["error"] = f"could not create the base worktree: {detail}"
            return report
        ok, detail = _add_worktree(repo, scratch_wt, scratch_ref)
        if not ok:
            report["error"] = (
                f"could not create the scratch worktree: {detail}")
            return report

        if patch_path is not None:
            if not patch_path.is_file():
                report["error"] = f"patch not found: {patch_path}"
                return report
            code, out, err = repo.git("apply", "--whitespace=nowarn",
                                      str(patch_path), cwd=scratch_wt)
            if code != 0:
                report["error"] = "the patch did not apply: " + (
                    err or out).strip()
                return report

        report["base"]["oracles"] = _run_oracles(oracles, base_wt, timeout)
        report["scratch"]["oracles"] = _run_oracles(
            oracles, scratch_wt, timeout)
    finally:
        for worktree in (scratch_wt, base_wt):
            repo.git("worktree", "remove", "--force", str(worktree))
        repo.git("worktree", "prune")
        scratch.remove_scratch(temp_dir)

    base_all = all(row["ok"] for row in report["base"]["oracles"])
    scratch_all = all(row["ok"] for row in report["scratch"]["oracles"])
    report["base"]["all_pass"] = base_all
    report["scratch"]["all_pass"] = scratch_all
    report["canary_valid"] = (not base_all) and scratch_all

    if report["canary_valid"]:
        report["reason"] = ("the oracle fails at the base and passes on the "
                            "scratch implementation")
    elif base_all:
        report["reason"] = ("the base already satisfies every oracle; S8 "
                            "would refuse the lease")
    elif patch_path is None and scratch_ref == base_ref:
        report["reason"] = ("no scratch implementation was supplied, so the "
                            "oracle cannot pass on the scratch tree")
    else:
        report["reason"] = ("the scratch implementation does not satisfy "
                            "every oracle")
    return report
