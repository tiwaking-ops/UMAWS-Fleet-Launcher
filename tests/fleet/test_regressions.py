"""Regression tests for three defects found by the one-click demo.

Each of these was a real bug that let the system do the wrong thing
quietly.  They are pinned here so they cannot come back.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from fleet.harness import scope_check
from fleet.merge import commit_worktree, integrate
from fleet.spawn import worktree_status

from conftest import fake_profile, make_task, write_agents


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True, text=True)


# ---------------------------------------------------------------------------
# Defect 1: git collapses an untracked directory
# ---------------------------------------------------------------------------

def test_the_scope_check_sees_files_inside_a_new_directory(fake_kernel):
    """``git status --porcelain`` collapses ``newdir/`` into one entry.

    Without ``--untracked-files=all`` the scope check saw an empty change
    list, the evidence bundle recorded **no output files**, and the whole
    of a worker's work was invisible to verification.
    """
    task = make_task(fake_kernel,
                     scope={"write": ["newdir/module.py"], "read": []})
    worktree = fake_kernel.repo.root / "work" / "probe"
    worktree.mkdir(parents=True, exist_ok=True)
    _git(fake_kernel.repo.root, "worktree", "add", "--detach", str(worktree),
         "HEAD")
    try:
        (worktree / "newdir").mkdir()
        (worktree / "newdir" / "module.py").write_text("x = 1\n",
                                                        encoding="utf-8")
        status = worktree_status(fake_kernel.repo, worktree)
        assert "newdir/module.py" in status, status

        check = scope_check(task, worktree, fake_kernel.repo)
        assert check["ok"]
        assert "newdir/module.py" in check["changed"]
    finally:
        _git(fake_kernel.repo.root, "worktree", "remove", "--force",
             str(worktree))


# ---------------------------------------------------------------------------
# Defect 2: the merge queue staged the harness's own artefacts
# ---------------------------------------------------------------------------

def test_the_merge_queue_commits_only_the_declared_scope(fake_kernel):
    """``git add -A`` staged ``.pmwork/ORDER.md`` and the session file.

    Two leases then conflicted on the order file when their branches
    merged, and out-of-scope work was committed rather than quarantined.
    """
    task = make_task(fake_kernel,
                     scope={"write": ["src/thing.py"], "read": []})
    worktree = fake_kernel.repo.root / "work" / "probe2"
    worktree.mkdir(parents=True, exist_ok=True)
    _git(fake_kernel.repo.root, "worktree", "add", "--detach", str(worktree),
         "HEAD")
    try:
        (worktree / ".pmwork").mkdir()
        (worktree / ".pmwork" / "ORDER.md").write_text("order\n",
                                                        encoding="utf-8")
        (worktree / ".fakecli-session.json").write_text("{}\n", encoding="utf-8")
        (worktree / "src" / "thing.py").write_text("VALUE = 2\n", encoding="utf-8")
        (worktree / "outside.txt").write_text("nope\n", encoding="utf-8")

        ok, detail = commit_worktree(fake_kernel.repo, worktree, "test",
                                     task.write_scope)
        assert ok, detail

        _, staged, _ = fake_kernel.repo.git("show", "--name-only", "--format=",
                                           "HEAD", cwd=worktree)
        assert "src/thing.py" in staged
        assert ".pmwork/ORDER.md" not in staged
        assert ".fakecli-session.json" not in staged
        assert "outside.txt" not in staged
    finally:
        _git(fake_kernel.repo.root, "worktree", "remove", "--force",
             str(worktree))


def test_the_merge_queue_refuses_an_out_of_scope_change(fake_kernel):
    """An out-of-scope write is a refusal to promote, not a merge."""
    task = make_task(fake_kernel,
                     scope={"write": ["src/thing.py"], "read": []})
    worktree = fake_kernel.repo.root / "work" / "probe3"
    worktree.mkdir(parents=True, exist_ok=True)
    _git(fake_kernel.repo.root, "worktree", "add", "-B", "pmk/probe3",
         str(worktree), "HEAD")
    try:
        (worktree / "outside.txt").write_text("nope\n", encoding="utf-8")
        from pmk.models import Lease
        lease = Lease(task_id=task.id, fence=1)
        result = integrate(fake_kernel, task, lease, worktree, gate_cmd="")
        assert not result.ok, result.message
        assert "write scope" in result.message
        assert "outside.txt" in result.message
    finally:
        _git(fake_kernel.repo.root, "worktree", "remove", "--force",
             str(worktree))


# ---------------------------------------------------------------------------
# Defect 3: the merge moved the ref but not the working tree
# ---------------------------------------------------------------------------

def test_merging_updates_the_main_working_tree(fake_kernel):
    """``update-ref`` moves the branch but never checks the files out.

    The close-check runs in the main tree, so merged files that were
    never checked out would make a finished project look unfinished.
    """
    task = make_task(fake_kernel,
                     scope={"write": ["src/thing.py"], "read": []})
    worktree = fake_kernel.repo.root / "work" / "probe4"
    worktree.mkdir(parents=True, exist_ok=True)
    from pmk.models import Lease
    lease = Lease(task_id=task.id, fence=1)
    # The merge queue merges the branch named after the task and the fence.
    branch = f"pmk/{task.id}-{lease.fence}"
    _git(fake_kernel.repo.root, "worktree", "add", "-B", branch,
         str(worktree), "HEAD")
    try:
        (worktree / "src" / "thing.py").write_text("VALUE = 99\n",
                                                    encoding="utf-8")
        result = integrate(fake_kernel, task, lease, worktree, gate_cmd="")
        assert result.ok, result.message
        # The file is on disk in the main tree, not just in the ref.
        main_file = fake_kernel.repo.root / "src" / "thing.py"
        assert "99" in main_file.read_text(encoding="utf-8")
    finally:
        _git(fake_kernel.repo.root, "worktree", "remove", "--force",
             str(worktree))
