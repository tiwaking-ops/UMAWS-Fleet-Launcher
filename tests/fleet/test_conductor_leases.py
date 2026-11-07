"""Lease expiry in the Conductor: orphaned leases only.

A lease expires when nobody supervises it and its last heartbeat (the later of
``granted_at`` and ``renewed_at``) is older than the TTL.  Supervised leases,
leases of tasks past the running stage, and everything while the project is
PAUSED are left alone.  The agent process is stopped before the revoke, but
only when the pid and the creation time both match the recorded process.
"""

from __future__ import annotations

import os
import sys
import time

import pytest

from fleet import spawn as spawn_mod
from fleet.conductor import REAP_RETRY_S, Conductor
from fleet.dispatcher import Dispatcher
from fleet.overseer import OverseerRunner
from fleet.state import FleetState
from pmk import plat
from pmk.api import KernelError

from conftest import FIXTURE_ROOT, make_task

TTL_S = 600.0


def _conductor(kernel, ttl_s: float = TTL_S) -> Conductor:
    fleet_state = FleetState()
    dispatcher = Dispatcher(kernel, fleet_state, fixture_root=FIXTURE_ROOT)
    conductor = Conductor(kernel=kernel, dispatcher=dispatcher,
                          overseer=OverseerRunner(kernel, fleet_state))
    conductor.lease_ttl_seconds = lambda: ttl_s
    return conductor


def _claim(kernel, name: str):
    """A task with its own write scope, claimed with no process behind it."""
    task = make_task(kernel, scope={"write": [f"src/{name}.py"], "read": []})
    lease = kernel.claim(task.id, holder="fake-a", agent="fake",
                         role="implement")
    return task, lease


def _events(kernel, event_type: str) -> list:
    return [e for e in kernel.events() if e.type == event_type]


def _sleeper(tmp_path):
    """A real child process that outlives the test unless it is stopped."""
    return plat.spawn([sys.executable, "-c", "import time; time.sleep(120)"],
                      cwd=tmp_path, log_path=tmp_path / "sleeper.log",
                      env=dict(os.environ))


def _record_started(kernel, task, lease, sleeper, creation_time=None):
    kernel.record_event(
        "AGENT_STARTED", subject=task.id, fence=lease.fence,
        payload={"pid": sleeper.pid,
                 "creation_time": (sleeper.creation_time
                                   if creation_time is None else creation_time),
                 "adapter": "fake", "profile": "fake-a"})


def _wait_for_exit(sleeper, seconds: float = 10.0):
    deadline = time.time() + seconds
    while sleeper.proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    return sleeper.proc.poll()


# ---------------------------------------------------------------------------
# Which leases expire
# ---------------------------------------------------------------------------

def test_the_ttl_comes_from_policy(fake_kernel):
    fleet_state = FleetState()
    conductor = Conductor(
        kernel=fake_kernel,
        dispatcher=Dispatcher(fake_kernel, fleet_state, fixture_root=FIXTURE_ROOT),
        overseer=OverseerRunner(fake_kernel, fleet_state))
    minutes = float(fake_kernel.policy().get("lease", {}).get("ttl_minutes", 20))
    assert conductor.lease_ttl_seconds() == minutes * 60.0


def test_an_orphaned_lease_past_the_ttl_is_revoked(fake_kernel, clock):
    task, lease = _claim(fake_kernel, "a")
    conductor = _conductor(fake_kernel)
    clock.advance(TTL_S + 1)

    results = conductor.reap_expired_leases()

    assert [r["task"] for r in results] == [task.id]
    assert results[0]["reaped"] is True
    state = fake_kernel.state()
    assert task.id not in state.leases
    assert state.tasks[task.id].state == "READY"
    revoked = _events(fake_kernel, "REVOKED")[-1]
    assert revoked.subject == task.id
    assert "lease expired" in revoked.payload["reason"]
    assert _events(fake_kernel, "LEASE_REAPED")[-1].subject == task.id


def test_a_lease_within_the_ttl_is_left_alone(fake_kernel, clock):
    task, lease = _claim(fake_kernel, "a")
    conductor = _conductor(fake_kernel)
    clock.advance(TTL_S - 1)

    assert conductor.reap_expired_leases() == []
    assert task.id in fake_kernel.state().leases


def test_the_ttl_counts_from_the_later_of_grant_and_renewal(fake_kernel, clock):
    task, lease = _claim(fake_kernel, "a")
    conductor = _conductor(fake_kernel)
    clock.advance(TTL_S - 100)
    fake_kernel.renew(task.id, lease.fence, digest="heartbeat")
    clock.advance(TTL_S - 100)      # past the TTL since the grant, within it since the renewal

    assert conductor.reap_expired_leases() == []

    clock.advance(200)              # now past the TTL since the renewal as well
    assert [r["task"] for r in conductor.reap_expired_leases()] == [task.id]


def test_a_stale_lease_on_a_done_task_is_not_revoked(fake_kernel, clock):
    """The T-0003 case: a finished task keeps its lease record."""
    task, lease = _claim(fake_kernel, "a")
    fake_kernel.record_event("INTEGRATED", subject=task.id, fence=lease.fence,
                             payload={"bundle": "EB-test", "commit": "abc"})
    assert fake_kernel.state().tasks[task.id].state == "DONE"
    conductor = _conductor(fake_kernel)
    clock.advance(TTL_S * 10)

    assert conductor.reap_expired_leases() == []
    assert fake_kernel.state().tasks[task.id].state == "DONE"
    assert not _events(fake_kernel, "REVOKED")


@pytest.mark.parametrize("event_type, payload, expected", [
    ("SUBMITTED", {}, "SUBMITTED"),
    ("VERIFIED", {"ok": True}, "VERIFYING"),
    ("INTEGRATING", {}, "INTEGRATING"),
])
def test_tasks_past_the_running_stage_are_left_alone(
        fake_kernel, clock, event_type, payload, expected):
    task, lease = _claim(fake_kernel, "a")
    fake_kernel.record_event(event_type, subject=task.id, fence=lease.fence,
                             payload=payload)
    assert fake_kernel.state().tasks[task.id].state == expected
    conductor = _conductor(fake_kernel)
    clock.advance(TTL_S * 10)

    assert conductor.reap_expired_leases() == []
    assert fake_kernel.state().tasks[task.id].state == expected
    assert not _events(fake_kernel, "REVOKED")


def test_a_lease_this_process_supervises_is_not_reaped(fake_kernel, clock):
    task = make_task(fake_kernel, oracles=["python -c \"print('ok')\""])
    dispatcher = Dispatcher(fake_kernel, FleetState(), fixture_root=FIXTURE_ROOT)
    dispatcher.tick()
    assert task.id in dispatcher.runs
    try:
        conductor = Conductor(
            kernel=fake_kernel, dispatcher=dispatcher,
            overseer=OverseerRunner(fake_kernel, dispatcher.fleet_state))
        conductor.lease_ttl_seconds = lambda: TTL_S
        clock.advance(TTL_S * 3)

        assert conductor.reap_expired_leases() == []
        state = fake_kernel.state()
        assert task.id in state.leases
        assert state.tasks[task.id].state == "LEASED"
    finally:
        spawn_mod.kill_slot(dispatcher.runs[task.id].slot)


def test_nothing_is_reaped_while_the_project_is_paused(fake_kernel, clock):
    task, lease = _claim(fake_kernel, "a")
    conductor = _conductor(fake_kernel)
    fake_kernel.project_set_state("PAUSED", reason="test")
    clock.advance(TTL_S * 2)

    assert conductor.reap_expired_leases() == []
    assert task.id in fake_kernel.state().leases

    fake_kernel.project_set_state("RUNNING", reason="test")
    assert [r["task"] for r in conductor.reap_expired_leases()] == [task.id]


# ---------------------------------------------------------------------------
# The agent process
# ---------------------------------------------------------------------------

def test_the_recorded_process_is_stopped_before_the_revoke(
        fake_kernel, clock, tmp_path):
    task, lease = _claim(fake_kernel, "a")
    sleeper = _sleeper(tmp_path)
    try:
        _record_started(fake_kernel, task, lease, sleeper)
        conductor = _conductor(fake_kernel)
        clock.advance(TTL_S + 1)

        results = conductor.reap_expired_leases()

        assert results and results[0]["reaped"] is True
        assert results[0]["process"]["ok"] is True
        assert _wait_for_exit(sleeper) is not None, "the agent was not stopped"
        assert task.id not in fake_kernel.state().leases
    finally:
        if sleeper.proc.poll() is None:
            sleeper.proc.kill()


def test_a_process_whose_creation_time_does_not_match_is_not_killed(
        fake_kernel, clock, tmp_path):
    task, lease = _claim(fake_kernel, "a")
    sleeper = _sleeper(tmp_path)
    try:
        _record_started(fake_kernel, task, lease, sleeper,
                        creation_time=sleeper.creation_time + 10 ** 10)
        conductor = _conductor(fake_kernel)
        clock.advance(TTL_S + 1)

        results = conductor.reap_expired_leases()

        assert results and results[0]["reaped"] is True
        assert "process" not in results[0]
        assert sleeper.proc.poll() is None, "an unrelated process was killed"
    finally:
        if sleeper.proc.poll() is None:
            sleeper.proc.kill()


def test_a_process_that_cannot_be_stopped_blocks_the_revoke(
        fake_kernel, clock, tmp_path, monkeypatch):
    task, lease = _claim(fake_kernel, "a")
    sleeper = _sleeper(tmp_path)
    try:
        _record_started(fake_kernel, task, lease, sleeper)
        monkeypatch.setattr(spawn_mod, "kill_slot",
                            lambda slot: (False, "access denied"))
        conductor = _conductor(fake_kernel)
        clock.advance(TTL_S + 1)

        results = conductor.reap_expired_leases()

        assert results[0]["reaped"] is False
        assert results[0]["stage"] == "kill"
        assert task.id in fake_kernel.state().leases
        assert not _events(fake_kernel, "REVOKED")
        failed = _events(fake_kernel, "LEASE_REAP_FAILED")
        assert [e.payload["stage"] for e in failed] == ["kill"]

        # Not retried on the next tick, retried after the retry interval.
        assert conductor.reap_expired_leases() == []
        clock.advance(REAP_RETRY_S + 1)
        assert len(conductor.reap_expired_leases()) == 1
    finally:
        if sleeper.proc.poll() is None:
            sleeper.proc.kill()


# ---------------------------------------------------------------------------
# Failures do not stop the loop
# ---------------------------------------------------------------------------

def test_a_failed_revoke_is_recorded_and_the_next_lease_is_still_handled(
        fake_kernel, clock, monkeypatch):
    a, lease_a = _claim(fake_kernel, "a")
    b, lease_b = _claim(fake_kernel, "b")
    real_revoke = fake_kernel.revoke

    def flaky(task_id, fence, **kwargs):
        if task_id == a.id:
            raise KernelError("boom", task=task_id)
        return real_revoke(task_id, fence, **kwargs)

    monkeypatch.setattr(fake_kernel, "revoke", flaky)
    conductor = _conductor(fake_kernel)
    clock.advance(TTL_S + 1)

    results = {r["task"]: r for r in conductor.reap_expired_leases()}

    assert results[a.id]["reaped"] is False
    assert results[a.id]["stage"] == "revoke"
    assert results[b.id]["reaped"] is True
    state = fake_kernel.state()
    assert a.id in state.leases
    assert b.id not in state.leases
    failed = _events(fake_kernel, "LEASE_REAP_FAILED")
    assert [e.subject for e in failed] == [a.id]


# ---------------------------------------------------------------------------
# REC-01: reclaiming the worktree a bumped fence leaves behind
# ---------------------------------------------------------------------------

def _orphan_with_worktree(kernel, name: str, *, dirty: bool = True):
    import subprocess
    task = make_task(kernel, scope={"write": [f"src/{name}.py"], "read": []})
    tree = kernel.repo.work_dir / f"{task.id}-reclaim"
    tree.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "worktree", "add", "--detach", str(tree), "HEAD"],
                   cwd=kernel.repo.root, capture_output=True)
    if dirty:
        (tree / "README.md").write_text("# stranded\n", encoding="utf-8")
    lease = kernel.claim(task.id, holder="fake-a", agent="fake",
                         role="implement", worktree=str(tree))
    return task, tree, lease


def _enable_reclaim(kernel, monkeypatch) -> None:
    policy = kernel.policy()
    policy.setdefault("worktree", {})["reclaim_on_reap"] = True
    monkeypatch.setattr(kernel, "policy", lambda: policy)


def test_reap_reclaims_the_worktree_when_policy_enables_it(
        fake_kernel, clock, monkeypatch):
    task, tree, lease = _orphan_with_worktree(fake_kernel, "a")
    _enable_reclaim(fake_kernel, monkeypatch)
    conductor = _conductor(fake_kernel)
    clock.advance(TTL_S + 1)

    results = conductor.reap_expired_leases()

    assert results[0]["reaped"] is True
    assert not tree.exists()
    reclaims = _events(fake_kernel, "WORKTREE_RECLAIMED")
    assert len(reclaims) == 1
    assert reclaims[0].subject == task.id
    assert reclaims[0].payload["reclaimed"] is True
    assert (fake_kernel.repo.root / "stranded" / tree.name).is_dir()


def test_reap_leaves_the_worktree_alone_by_default(fake_kernel, clock):
    task, tree, lease = _orphan_with_worktree(fake_kernel, "a")
    conductor = _conductor(fake_kernel)
    clock.advance(TTL_S + 1)

    conductor.reap_expired_leases()

    assert tree.exists()                          # reclaim is opt-in
    assert not _events(fake_kernel, "WORKTREE_RECLAIMED")


def test_reap_keeps_the_worktree_when_the_capture_does_not_verify(
        fake_kernel, clock, monkeypatch):
    from pmk import worktrees
    task, tree, lease = _orphan_with_worktree(fake_kernel, "a")
    _enable_reclaim(fake_kernel, monkeypatch)
    monkeypatch.setattr(worktrees, "verify_archive",
                        lambda dest: (False, ["boom"]))
    conductor = _conductor(fake_kernel)
    clock.advance(TTL_S + 1)

    conductor.reap_expired_leases()

    assert tree.exists()                          # kept: capture not verified
    reclaim = _events(fake_kernel, "WORKTREE_RECLAIMED")[-1]
    assert reclaim.payload["reclaimed"] is False
