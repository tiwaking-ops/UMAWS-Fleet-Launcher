"""Re-integration must run the gate, not trust the first pass.

Regression tests for the defect recorded at the G5 close-out: a clean
worktree used to return ``ok = True`` with the message "the worker
changed nothing" *before* the merge stage ran -- so re-integrating a
lease whose work is already committed (the first merge crashed halfway,
the close-out is re-run) reported ok **without the gate ever running**,
skipping invariant I5 quietly.  Fixed 2026-10-24: every path goes
through the merge stage; only a green gate reaches ``ok``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from pmk.models import Lease

from fleet.merge import integrate

from conftest import make_task


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True, text=True)


def _lease_worktree(kernel, task, name: str):
    """A lease worktree on the branch the merge queue expects."""
    lease = Lease(task_id=task.id, fence=1)
    worktree = kernel.repo.root / "work" / name
    branch = f"pmk/{task.id}-{lease.fence}"
    _git(kernel.repo.root, "worktree", "add", "-B", branch, str(worktree),
         "HEAD")
    return lease, worktree


def test_reintegration_runs_the_gate(kernel):
    """A crash between merge and record is re-run through the gate.

    First pass: green gate, main has the work -- then the queue dies
    before recording anything.  On re-integration the worktree is clean;
    the fixed queue re-runs the gate rather than reporting ok unseen.
    """
    task = make_task(kernel, scope={"write": ["src/thing.py"], "read": []})
    lease, worktree = _lease_worktree(kernel, task, "reint-a")
    try:
        (worktree / "src" / "thing.py").write_text("VALUE = 99\n",
                                                   encoding="utf-8")
        first = integrate(kernel, task, lease, worktree, gate_cmd="exit 0")
        assert first.ok, first.message

        # The re-integration: clean worktree, work already in main.
        refused = integrate(kernel, task, lease, worktree, gate_cmd="exit 1")
        assert not refused.ok, refused.message
        assert refused.gate_cmd == "exit 1"
        assert refused.gate_exit == 1            # <- the gate actually ran

        # And a green re-run is honest idempotency, explicitly labelled.
        again = integrate(kernel, task, lease, worktree, gate_cmd="exit 0")
        assert again.ok, again.message
        assert "re-integration" in again.message
    finally:
        _git(kernel.repo.root, "worktree", "remove", "--force", str(worktree))


def test_a_worker_that_wrote_nothing_cannot_skip_the_gate(kernel):
    """The same line used to promote a no-work lease with no gate."""
    task = make_task(kernel, scope={"write": ["src/thing.py"], "read": []})
    lease, worktree = _lease_worktree(kernel, task, "reint-b")
    try:
        red = integrate(kernel, task, lease, worktree, gate_cmd="exit 1")
        assert not red.ok, red.message
        assert red.gate_exit == 1

        # With a green gate the no-work lease goes through; nothing was
        # credited to this merge (no new commit, no files listed).
        green = integrate(kernel, task, lease, worktree, gate_cmd="exit 0")
        assert green.ok, green.message
        assert green.files == []
        assert green.message == ("the worker changed nothing "
                                 "(re-integration: the gate re-ran and passed)")
    finally:
        _git(kernel.repo.root, "worktree", "remove", "--force", str(worktree))


def test_reintegration_does_not_credit_someone_elses_files(kernel):
    """An already-merged lease lists no files on its re-run.

    Without the up-to-date guard, ``git diff HEAD~1 HEAD`` on an
    unchanged tree reported the *previous* merge's files as this one's.
    """
    task = make_task(kernel, scope={"write": ["src/thing.py"], "read": []})
    lease, worktree = _lease_worktree(kernel, task, "reint-c")
    try:
        (worktree / "src" / "thing.py").write_text("VALUE = 77\n",
                                                   encoding="utf-8")
        first = integrate(kernel, task, lease, worktree, gate_cmd="exit 0")
        assert first.ok and first.files == ["src/thing.py"], first.message

        again = integrate(kernel, task, lease, worktree, gate_cmd="exit 0")
        assert again.ok, again.message
        assert again.files == []
    finally:
        _git(kernel.repo.root, "worktree", "remove", "--force", str(worktree))
