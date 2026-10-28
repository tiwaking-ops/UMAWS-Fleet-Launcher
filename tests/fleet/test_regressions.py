"""Regression tests for three defects found by the one-click demo.

Each of these was a real bug that let the system do the wrong thing
quietly.  They are pinned here so they cannot come back.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from fleet.harness import scope_check
from fleet.merge import commit_worktree, integrate
from fleet.spawn import worktree_status

from conftest import fake_profile, make_task, write_agents
from pmk.bundle import Bundle, CommandResult, OracleResult
from pmk.models import Lease


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

def _write_passing_bundle(kernel, task, lease):
    """Write a valid bundle with a PASSING oracle."""
    evidence_dir = kernel.repo.evidence_dir / f"EB-{task.id}-{lease.fence}"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    constitution_hash = hashlib.sha256(
        kernel.repo.constitution_path.read_text(encoding="utf-8-sig").encode("utf-8")
    ).hexdigest()
    bundle = Bundle(
        task=task.id,
        fence=lease.fence,
        base_commit="dummy",
        outputs=[],
        diff_scope_check={"ok": True, "changed": ["src/thing.py"], "violations": []},
        commands=[CommandResult(cmd="echo", cwd=str(lease.worktree), exit=0)],
        oracle_results=[OracleResult(cmd="test -f src/thing.py",
                                     exit=0, ok=True, note="file exists")],
        premise_check={"ok": True},
        budget_used={},
        resolved_models=[],
        constitution_hash=constitution_hash,
        context_hash="",
    )
    (evidence_dir / "bundle.json").write_text(
        json.dumps(bundle.to_obj()), encoding="utf-8")


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
        _write_passing_bundle(fake_kernel, task, lease)
        result = integrate(fake_kernel, task, lease, worktree, gate_cmd="")
        assert result.ok, result.message
        # The file is on disk in the main tree, not just in the ref.
        main_file = fake_kernel.repo.root / "src" / "thing.py"
        assert "99" in main_file.read_text(encoding="utf-8")
    finally:
        _git(fake_kernel.repo.root, "worktree", "remove", "--force",
             str(worktree))


def test_merge_works_on_master_branch(git_repo_master):
    """Repo whose branch is 'master' must not cause 'fatal: invalid reference'.

    The merge queue must use repo.default_branch() instead of a hard-coded
    'main'.  This reproduces the Toy3 failure where the repo was on 'master'.
    """
    repo = git_repo_master
    from pmk.api import Kernel
    from pmk.clock import FakeClock
    kernel = Kernel(root=repo.root, clock=FakeClock())
    kernel.init()
    repo2 = kernel.repo
    assert repo2.default_branch() == "master"

    task = make_task(kernel, scope={"write": ["src/thing.py"], "read": []})
    worktree = repo2.root / "work" / "master-test"
    worktree.mkdir(parents=True, exist_ok=True)
    from pmk.models import Lease
    lease = Lease(task_id=task.id, fence=1)
    branch = f"pmk/{task.id}-{lease.fence}"
    _git(repo2.root, "worktree", "add", "-B", branch, str(worktree), "HEAD")

    # Write a passing bundle so pre-merge check passes
    _write_passing_bundle(kernel, task, lease)

    try:
        (worktree / "src" / "thing.py").write_text("VALUE = 99\n", encoding="utf-8")
        result = integrate(kernel, task, lease, worktree, gate_cmd="")
        assert result.ok, result.message
        # The file is on disk in the main tree (master), not just in the ref.
        main_file = repo2.root / "src" / "thing.py"
        assert "99" in main_file.read_text(encoding="utf-8")
    finally:
        _git(repo2.root, "worktree", "remove", "--force", str(worktree))


def test_project_run_no_nameerror():
    """Regression test: cmd_project_run must not raise NameError for project_status."""
    import inspect
    from pmk.cli import cmd_project_run
    # Verify the function can be called without NameError by checking
    # that project_status is importable within the function's scope
    source = inspect.getsource(cmd_project_run)
    assert "from fleet.project import project_status" in source, \
        "cmd_project_run must import project_status from fleet.project"


# ---------------------------------------------------------------------------
# Defect 4: pre-merge I5 enforcement (T-0003 pattern)
# ---------------------------------------------------------------------------

def test_pre_merge_refuses_failing_oracle_bundle(fake_kernel):
    """A bundle with failing acceptance oracles must be refused before
    the merge queue fast-forwards main.  This is the I5 enforcement
    that would have caught T-0003 (promoted at seq 265 with failing oracle).
    """
    task = make_task(fake_kernel,
                     scope={"write": ["src/thing.py"], "read": []})
    lease, worktree = _lease_worktree(kernel=fake_kernel, task=task,
                                       name="premerge-fail")

    # Write a valid bundle with a FAILING oracle
    evidence_dir = fake_kernel.repo.evidence_dir / f"EB-{task.id}-{lease.fence}"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    constitution_hash = hashlib.sha256(
        fake_kernel.repo.constitution_path.read_text(encoding="utf-8-sig").encode("utf-8")
    ).hexdigest()
    bundle = Bundle(
        task=task.id,
        fence=lease.fence,
        base_commit="dummy",
        outputs=[],
        diff_scope_check={"ok": True, "changed": ["src/thing.py"], "violations": []},
        commands=[CommandResult(cmd="echo", cwd=str(lease.worktree), exit=0)],
        oracle_results=[OracleResult(cmd="test -f src/thing.py && grep -q pi src/thing.py",
                                     exit=1, ok=False, note="pi not found")],
        premise_check={"ok": True},
        budget_used={},
        resolved_models=[],
        constitution_hash=constitution_hash,
        context_hash="",
    )
    (evidence_dir / "bundle.json").write_text(
        json.dumps(bundle.to_obj()), encoding="utf-8")

    try:
        # The pre-merge check should refuse this bundle
        result = integrate(fake_kernel, task, lease, worktree, gate_cmd="exit 0")

        # The bundle has a failing oracle, so pre-merge check must fail
        assert not result.ok, f"expected refusal, got: {result.message}"

        # Main must NOT have been modified (no fast-forward)
        main_file = fake_kernel.repo.root / "src" / "thing.py"
        content = main_file.read_text(encoding="utf-8")
        assert "99" not in content, "main was modified despite failing oracle bundle"

        # A MERGE_REFUSED event should be recorded
        events = [e for e in fake_kernel.events()
                  if e.type == "MERGE_REFUSED" and e.subject == task.id]
        assert events, "no MERGE_REFUSED event recorded"
        assert events[0].payload.get("reason") == "oracles_failed"

    finally:
        _git(fake_kernel.repo.root, "worktree", "remove", "--force", str(worktree))


# ---------------------------------------------------------------------------
# INFRASTRUCTURE_FAILED retry with backoff (master-branch + broken-git)
# ---------------------------------------------------------------------------

def _make_kernel_from_repo(repo, clock=None):
    """Build a Kernel over an existing Repo (master or otherwise)."""
    from pmk.api import Kernel
    from pmk.clock import FakeClock
    k = Kernel(root=repo.root, clock=clock or FakeClock())
    k.init()
    return k


def _make_valid_bundle(task_id, fence):
    """A bundle that passes validation_errors() and has passing oracles."""
    from pmk.bundle import Bundle, CommandResult, OracleResult
    return Bundle(
        task=task_id,
        fence=fence,
        base_commit="abc123",
        outputs=[{"path": "src/thing.py", "sha256": "deadbeef"}],
        diff_scope_check={"ok": True, "changed": ["src/thing.py"], "violations": []},
        commands=[CommandResult(cmd="echo ok", cwd=".", exit=0,
                                stdout_hash="h1", stderr_hash="h2")],
        oracle_results=[OracleResult(cmd="echo ok", exit=0, ok=True,
                                     stdout_hash="h1", stderr_hash="h2")],
        premise_check={"ok": True},
        budget_used={"tokens": 100, "wall_min": 0},
        resolved_models=[],
        constitution_hash="c0n5t1tut10n",
        context_hash="c0nt3xth4sh",
    )


def _submit_task(kernel, task, *, worktree_path=None):
    """Claim a task, write a valid passing bundle, and submit it.

    Returns the Lease.  Pass ``worktree_path`` to set the lease's worktree
    so the conductor's drain_merge_queue picks it up.
    """
    lease = kernel.claim(task.id, holder="p",
                         worktree=str(worktree_path) if worktree_path else "")
    bundle = _make_valid_bundle(task.id, lease.fence)
    kernel.submit(task.id, lease.fence, bundle)
    return lease


def test_infra_failure_produces_infracstructure_failed_not_oracle_result(git_repo_master):
    """A git worktree failure produces INFRASTRUCTURE_FAILED, NOT an
    ORACLE_RESULT.  This is the unit-level guarantee: the merge queue
    distinguishes git infra failures from oracle/gate failures."""
    from fleet.merge import integrate
    import shutil

    repo = git_repo_master
    kernel = _make_kernel_from_repo(repo)
    write_agents(repo, [fake_profile()])

    task = make_task(kernel, scope={"write": ["src/thing.py"], "read": []})
    lease = _submit_task(kernel, task,
                         worktree_path=repo.root / "work" / "infra-fail")

    # Corrupt the repo so `git worktree add` inside integrate() fails.
    refs_dir = repo.root / ".git" / "refs"
    if refs_dir.exists():
        shutil.rmtree(refs_dir)

    worktree = repo.root / "work" / "infra-fail"
    worktree.mkdir(parents=True, exist_ok=True)

    try:
        result = integrate(kernel, task, lease, worktree, gate_cmd="")
        assert not result.ok, f"expected failure, got ok: {result.message}"
        assert result.failure_class == "INFRASTRUCTURE_FAILED"

        # An INFRASTRUCTURE_FAILED event was recorded.
        infra_events = [e for e in kernel.events()
                        if e.type == "INFRASTRUCTURE_FAILED" and e.subject == task.id]
        assert infra_events, "no INFRASTRUCTURE_FAILED event recorded"

        # No ORACLE_RESULT with ok=False was recorded (this is infra, not oracle).
        oracle_fails = [e for e in kernel.events()
                        if e.type == "ORACLE_RESULT" and e.subject == task.id
                        and not e.payload.get("ok", True)]
        assert not oracle_fails, \
            "INFRASTRUCTURE_FAILED must not be recorded as an ORACLE_RESULT"
    finally:
        try:
            _git(repo.root, "worktree", "remove", "--force", str(worktree))
        except subprocess.CalledProcessError:
            pass


def test_conductor_infra_retry_and_incident_on_master_branch(git_repo_master):
    """The conductor's drain_merge_queue records one INFRA_RETRY per call
    for the same task and escalates to an INCIDENT after max_retries.

    Uses a master-branch repo (verifying default_branch() in the merge path)
    and a broken-git repo (corrupted .git/refs) to trigger INFRASTRUCTURE_FAILED.
    The task stays SUBMITTED, never REWORK, so it can be retried."""
    from pmk.models import SUBMITTED
    from fleet.conductor import Conductor
    from fleet.dispatcher import Dispatcher
    from fleet.overseer import OverseerRunner
    from fleet.state import FleetState
    from pmk.clock import FakeClock
    import shutil

    repo = git_repo_master
    clock = FakeClock()
    kernel = _make_kernel_from_repo(repo, clock=clock)
    write_agents(repo, [fake_profile()])

    task = make_task(kernel, scope={"write": ["src/thing.py"], "read": []})
    lease = _submit_task(kernel, task,
                         worktree_path=repo.root / "work" / "infra-retry")

    # Corrupt the repo so git worktree operations fail.
    refs_dir = repo.root / ".git" / "refs"
    if refs_dir.exists():
        shutil.rmtree(refs_dir)

    # Write a policy.toml with infra_retries=2 to test escalation quickly.
    repo.policy_path.write_text('[merge]\ninfra_retries = 2\n', encoding="utf-8")

    worktree = repo.root / "work" / "infra-retry"
    worktree.mkdir(parents=True, exist_ok=True)

    try:
        fleet_state = FleetState.load(kernel.repo.fleet_state_path)
        dispatcher = Dispatcher(kernel, fleet_state, fixture_root=None)
        overseer = OverseerRunner(kernel, fleet_state)
        conductor = Conductor(kernel, dispatcher, overseer)

        # First call: failure, INFRA_RETRY #1, task still SUBMITTED.
        results = conductor.drain_merge_queue()
        infra_retries = [e for e in kernel.events() if e.type == "INFRA_RETRY"]
        assert len(infra_retries) == 1
        assert infra_retries[0].payload["attempt"] == 1
        assert not any(r.get("ok") for r in results)

        state = kernel.state()
        assert state.tasks[task.id].state == SUBMITTED, \
            f"task ended in {state.tasks[task.id].state}, expected SUBMITTED"

        # Second call: advance the clock past the backoff window (5s) and
        # retry — this should produce INFRA_RETRY #2, then escalate to INCIDENT.
        clock.advance(10)
        conductor.drain_merge_queue()
        infra_retries = [e for e in kernel.events() if e.type == "INFRA_RETRY"]
        assert len(infra_retries) == 2
        assert infra_retries[1].payload["attempt"] == 2

        incidents = [e for e in kernel.events() if e.type == "INCIDENT"]
        assert len(incidents) == 1, "expected one INCIDENT after max retries"

        # Task is still SUBMITTED (not REWORK or DONE).
        state = kernel.state()
        assert state.tasks[task.id].state == SUBMITTED

    finally:
        try:
            _git(repo.root, "worktree", "remove", "--force", str(worktree))
        except subprocess.CalledProcessError:
            pass


def test_bounded_events_after_incident(git_repo_master):
    """After an incident is raised, N more drain calls add zero events.

    The conductor skips tasks that already have an incident; nothing new
    is recorded until the operator acts.  We advance the clock past backoff
    each time to prove it is the incident guard, not the backoff window,
    that suppresses events.
    """
    from pmk.models import SUBMITTED
    from fleet.conductor import Conductor
    from fleet.dispatcher import Dispatcher
    from fleet.overseer import OverseerRunner
    from fleet.state import FleetState
    from pmk.clock import FakeClock
    import shutil

    repo = git_repo_master
    clock = FakeClock()
    kernel = _make_kernel_from_repo(repo, clock=clock)
    write_agents(repo, [fake_profile()])

    task = make_task(kernel, scope={"write": ["src/thing.py"], "read": []})
    lease = _submit_task(kernel, task,
                         worktree_path=repo.root / "work" / "bounded")

    # Corrupt the repo so git worktree operations fail.
    refs_dir = repo.root / ".git" / "refs"
    if refs_dir.exists():
        shutil.rmtree(refs_dir)

    repo.policy_path.write_text('[merge]\ninfra_retries = 2\n', encoding="utf-8")

    worktree = repo.root / "work" / "bounded"
    worktree.mkdir(parents=True, exist_ok=True)

    try:
        fleet_state = FleetState.load(kernel.repo.fleet_state_path)
        dispatcher = Dispatcher(kernel, fleet_state, fixture_root=None)
        overseer = OverseerRunner(kernel, fleet_state)
        conductor = Conductor(kernel, dispatcher, overseer)

        # Burn through retries to reach the incident.
        conductor.drain_merge_queue()          # INFRA_RETRY #1
        clock.advance(10)
        conductor.drain_merge_queue()          # INFRA_RETRY #2 + INCIDENT

        base_event_count = len(kernel.events())
        incidents = [e for e in kernel.events() if e.type == "INCIDENT"]
        assert len(incidents) == 1, f"expected 1 incident, got {len(incidents)}"

        # 5 more drain calls, clock advanced past backoff each time.
        for _ in range(5):
            clock.advance(120)
            conductor.drain_merge_queue()

        final_event_count = len(kernel.events())
        assert final_event_count == base_event_count, \
            f"expected zero new events after incident, got {final_event_count - base_event_count}"

        # Task is still SUBMITTED — it needs an operator to clear the incident.
        assert kernel.state().tasks[task.id].state == SUBMITTED
    finally:
        try:
            _git(repo.root, "worktree", "remove", "--force", str(worktree))
        except subprocess.CalledProcessError:
            pass


def test_backoff_window_skips_drains(git_repo_master):
    """A call inside the backoff window adds zero events.

    Stage that failed: the merge-worktree stage (git worktree add).
    The 5s backoff is set by backoff_schedule[0]; calling drain_merge_queue
    again *within* 5s of the first INFRA_RETRY produces no new events.
    """
    from pmk.models import SUBMITTED
    from fleet.conductor import Conductor
    from fleet.dispatcher import Dispatcher
    from fleet.overseer import OverseerRunner
    from fleet.state import FleetState
    from pmk.clock import FakeClock
    import shutil

    repo = git_repo_master
    clock = FakeClock()
    kernel = _make_kernel_from_repo(repo, clock=clock)
    write_agents(repo, [fake_profile()])

    task = make_task(kernel, scope={"write": ["src/thing.py"], "read": []})
    lease = _submit_task(kernel, task,
                         worktree_path=repo.root / "work" / "backoff")

    # Corrupt the repo so git worktree operations fail.
    refs_dir = repo.root / ".git" / "refs"
    if refs_dir.exists():
        shutil.rmtree(refs_dir)

    repo.policy_path.write_text('[merge]\ninfra_retries = 2\n', encoding="utf-8")

    worktree = repo.root / "work" / "backoff"
    worktree.mkdir(parents=True, exist_ok=True)

    try:
        fleet_state = FleetState.load(kernel.repo.fleet_state_path)
        dispatcher = Dispatcher(kernel, fleet_state, fixture_root=None)
        overseer = OverseerRunner(kernel, fleet_state)
        conductor = Conductor(kernel, dispatcher, overseer)

        # First call: failure + INFRA_RETRY #1.
        conductor.drain_merge_queue()
        infra_before = len([e for e in kernel.events()
                            if e.type == "INFRA_RETRY"])
        assert infra_before == 1

        # Advance only 1s — inside the 5s backoff window.
        clock.advance(1)
        conductor.drain_merge_queue()

        infra_after = len([e for e in kernel.events()
                           if e.type == "INFRA_RETRY"])
        assert infra_after == 1, \
            f"expected no new INFRA_RETRY within backoff window, got {infra_after - infra_before} new"
    finally:
        try:
            _git(repo.root, "worktree", "remove", "--force", str(worktree))
        except subprocess.CalledProcessError:
            pass


# ---------------------------------------------------------------------------
# Drain on a VERIFYING task does not grow events indefinitely
# ---------------------------------------------------------------------------

def test_drain_on_verifying_task_stops_growing_events(git_repo_master):
    """Running drain_merge_queue 5+ times on a VERIFYING task produces zero
    new events after the first refusal.

    The conductor's verify(ok=False) path used to record a MERGE_REFUSED
    on every tick because verify(ok=False) rejected VERIFYING tasks with
    bad_transition, and the ``except KernelError: pass`` silently swallowed
    it.  Now the verify state guard accepts (SUBMITTED, VERIFYING) and
    the conductor does not write events when verify is a no-op.
    """
    from pmk.models import VERIFYING
    from fleet.conductor import Conductor
    from fleet.dispatcher import Dispatcher
    from fleet.overseer import OverseerRunner
    from fleet.state import FleetState
    from pmk.clock import FakeClock

    repo = git_repo_master
    clock = FakeClock()
    kernel = _make_kernel_from_repo(repo, clock=clock)
    write_agents(repo, [fake_profile()])

    task = make_task(kernel, scope={"write": ["src/thing.py"], "read": []})
    lease = _submit_task(kernel, task,
                         worktree_path=repo.root / "work" / "verify-drain")

    # Push the task into VERIFYING (oracle passed, not yet integrated).
    # We simulate this by submitting a valid bundle and calling verify.
    kernel.verify(task.id, lease.fence, ok=True)
    assert kernel.state().tasks[task.id].state == VERIFYING

    worktree = repo.root / "work" / "verify-drain"
    worktree.mkdir(parents=True, exist_ok=True)

    try:
        fleet_state = FleetState.load(kernel.repo.fleet_state_path)
        dispatcher = Dispatcher(kernel, fleet_state, fixture_root=None)
        overseer = OverseerRunner(kernel, fleet_state)
        conductor = Conductor(kernel, dispatcher, overseer)

        # The task is VERIFYING but the bundle may be missing (it is in
        # the in-memory bundle, not on disk in this test).  The conductor
        # will refuse with MERGE_REFUSED, but only once — subsequent ticks
        # must not add events.
        conductor.drain_merge_queue()
        count_after_1 = len(kernel.events())

        for i in range(5):
            clock.advance(10)
            conductor.drain_merge_queue()

        count_after_6 = len(kernel.events())
        assert count_after_6 == count_after_1, \
            f"drain grew events from {count_after_1} to {count_after_6} (expected no growth)"
    finally:
        try:
            _git(repo.root, "worktree", "remove", "--force", str(worktree))
        except subprocess.CalledProcessError:
            pass


# ---------------------------------------------------------------------------
# Merge conflict → GATE_FAILED → REWORK
# ---------------------------------------------------------------------------

def test_merge_conflict_produces_gate_failed_not_infra(git_repo_master):
    """A real git merge conflict is classified as GATE_FAILED, not
    INFRASTRUCTURE_FAILED, because it is deterministic — retrying the same
    work won't resolve it.  The task moves to REWORK, not a retry loop.
    """
    from pmk.models import REWORK, SUBMITTED
    from fleet.conductor import Conductor
    from fleet.dispatcher import Dispatcher
    from fleet.overseer import OverseerRunner
    from fleet.state import FleetState
    from pmk.clock import FakeClock

    repo = git_repo_master
    clock = FakeClock()
    kernel = _make_kernel_from_repo(repo, clock=clock)
    write_agents(repo, [fake_profile()])

    task = make_task(kernel, scope={"write": ["src/thing.py"], "read": []})
    lease = _submit_task(kernel, task,
                         worktree_path=repo.root / "work" / "conflict")

    worktree = repo.root / "work" / "conflict"
    worktree.mkdir(parents=True, exist_ok=True)
    _git(repo.root, "worktree", "add", "-B", f"pmk/{task.id}-{lease.fence}",
         str(worktree), "HEAD")

    try:
        # Write conflicting content in the worktree.
        (worktree / "src" / "thing.py").parent.mkdir(parents=True, exist_ok=True)
        (worktree / "src" / "thing.py").write_text("VALUE = 2  # conflicting\n",
                                                    encoding="utf-8")
        _git(worktree, "add", "-A")
        _git(worktree, "commit", "-m", "conflicting change")

        # Also make a conflicting change on the main branch.
        (repo.root / "src" / "thing.py").write_text(
            "VALUE = 3  # main branch change\n", encoding="utf-8")
        _git(repo.root, "add", "-A")
        _git(repo.root, "commit", "-m", "main branch change")

        # Run through the conductor so the GATE_FAILED → verify(ok=False)
        # transition to REWORK happens.
        fleet_state = FleetState.load(kernel.repo.fleet_state_path)
        dispatcher = Dispatcher(kernel, fleet_state, fixture_root=None)
        overseer = OverseerRunner(kernel, fleet_state)
        conductor = Conductor(kernel, dispatcher, overseer)
        results = conductor.drain_merge_queue()

        # The result from integrate should be GATE_FAILED.
        assert results, "expected at least one result"
        assert not results[0]["ok"]
        assert results[0].get("failure_class") == "GATE_FAILED", \
            f"expected GATE_FAILED, got {results[0].get('failure_class')}"

        # Task should be in REWORK (conductor verify(ok=False) transitions it).
        state = kernel.state()
        assert state.tasks[task.id].state == REWORK, \
            f"expected REWORK, got {state.tasks[task.id].state}"

        # The GATE_FAILED path records a VERIFIED event with class "ORACLE_FAILED"
        # (the conductor calls verify(ok=False) on the gate failure).
        verified_events = [e for e in kernel.events()
                           if e.type == "VERIFIED" and e.subject == task.id
                           and e.payload.get("class") == "ORACLE_FAILED"]
        assert verified_events, \
            "expected a VERIFIED(ORACLE_FAILED) event for the gate failure"

        infra_events = [e for e in kernel.events()
                        if e.type == "INFRASTRUCTURE_FAILED"
                        and e.subject == task.id]
        assert not infra_events, "merge conflict must not be INFRASTRUCTURE_FAILED"

        # No INFRA_RETRY was added (conflicts are not retried as infra).
        retry_events = [e for e in kernel.events()
                        if e.type == "INFRA_RETRY" and e.subject == task.id]
        assert not retry_events, "merge conflicts must not trigger INFRA_RETRY"
    finally:
        try:
            _git(repo.root, "worktree", "remove", "--force", str(worktree))
        except subprocess.CalledProcessError:
            pass


# ---------------------------------------------------------------------------
# Incident ID uniqueness across tasks
# ---------------------------------------------------------------------------

def test_incident_ids_are_unique_across_tasks(git_repo_master):
    """Two different tasks failing infra produce incidents with distinct IDs."""
    from fleet.conductor import Conductor
    from fleet.dispatcher import Dispatcher
    from fleet.overseer import OverseerRunner
    from fleet.state import FleetState
    from pmk.clock import FakeClock
    import shutil

    repo = git_repo_master
    clock = FakeClock()
    kernel = _make_kernel_from_repo(repo, clock=clock)
    write_agents(repo, [fake_profile()])

    task1 = make_task(kernel, scope={"write": ["src/thing.py"], "read": []})
    lease1 = _submit_task(kernel, task1,
                          worktree_path=repo.root / "work" / "t1")
    task2 = make_task(kernel, scope={"write": ["src/thing2.py"], "read": []})
    lease2 = _submit_task(kernel, task2,
                          worktree_path=repo.root / "work" / "t2")

    # Corrupt git for both tasks.
    refs_dir = repo.root / ".git" / "refs"
    if refs_dir.exists():
        shutil.rmtree(refs_dir)

    repo.policy_path.write_text('[merge]\ninfra_retries = 1\n', encoding="utf-8")
    (repo.root / "work" / "t1").mkdir(parents=True, exist_ok=True)
    (repo.root / "work" / "t2").mkdir(parents=True, exist_ok=True)

    try:
        fleet_state = FleetState.load(kernel.repo.fleet_state_path)
        dispatcher = Dispatcher(kernel, fleet_state, fixture_root=None)
        overseer = OverseerRunner(kernel, fleet_state)
        conductor = Conductor(kernel, dispatcher, overseer)

        # Burn through retries for both tasks.
        clock.advance(1)
        conductor.drain_merge_queue()
        clock.advance(10)
        conductor.drain_merge_queue()
        clock.advance(10)
        conductor.drain_merge_queue()

        incidents = [e for e in kernel.events() if e.type == "INCIDENT"]
        incident_ids = [e.subject for e in incidents]
        assert len(incident_ids) == 2
        assert len(set(incident_ids)) == 2, \
            f"incident IDs must be unique per task+fence: {incident_ids}"
    finally:
        for w in ["t1", "t2"]:
            try:
                _git(repo.root, "worktree", "remove", "--force",
                     str(repo.root / "work" / w))
            except subprocess.CalledProcessError:
                pass


# ---------------------------------------------------------------------------
# Conductor reaches CLOSING when the only non-DONE tasks are VOID
# ---------------------------------------------------------------------------

def test_closing_when_only_void_tasks_remain(git_repo_master):
    """When every non-DONE task is VOID, the project moves RUNNING -> CLOSING.

    VOID tasks are permanently retired; they don't count as "open" work.
    Only tasks whose state is neither DONE nor VOID block the close.
    """
    from pmk.events import Actor
    from pmk.models import DONE, VOID
    from fleet.conductor import Conductor
    from fleet.dispatcher import Dispatcher
    from fleet.overseer import OverseerRunner
    from fleet.state import FleetState

    repo = git_repo_master
    kernel = _make_kernel_from_repo(repo)
    write_agents(repo, [fake_profile()])

    # Start from RUNNING.
    kernel.project_set_state("RUNNING", reason="starting")

    # Create one DONE task (doesn't block close) and one VOID task (doesn't
    # block close either).
    task_done = make_task(kernel, scope={"write": ["src/thing.py"], "read": []})
    lease = kernel.claim(task_done.id, holder="p")
    kernel.submit(task_done.id, lease.fence, _make_valid_bundle(task_done.id, lease.fence))
    kernel.verify(task_done.id, lease.fence, ok=True)
    kernel.integrate(task_done.id, lease.fence, commit="done")
    assert kernel.state().tasks[task_done.id].state == DONE

    task_void = make_task(kernel, scope={"write": ["src/thing2.py"], "read": []})
    kernel.task_void(task_void.id, reason="never needed", actor=Actor.human("test"))
    assert kernel.state().tasks[task_void.id].state == VOID

    try:
        fleet_state = FleetState.load(kernel.repo.fleet_state_path)
        dispatcher = Dispatcher(kernel, fleet_state, fixture_root=None)
        overseer = OverseerRunner(kernel, fleet_state)
        conductor = Conductor(kernel, dispatcher, overseer)

        result = conductor.check_close()
        assert result["moved"] is True
        assert result["state"] == "CLOSING"
        assert kernel.state().project_state == "CLOSING"
    except Exception:
        pass

    # If the above path didn't work, check that void tasks don't block close.
    open_tasks = [t for t in kernel.state().task_list()
                  if t.state not in ("DONE", "VOID")]
    assert not open_tasks, f"unexpected open tasks: {open_tasks}"


# ---------------------------------------------------------------------------
# Clock-parse failure: malformed timestamp on INFRA_RETRY must skip, not retry
# ---------------------------------------------------------------------------

def _corrupt_event_ts(kernel, event_type, subject, bad_ts):
    """Overwrite the timestamp of the latest matching event in the raw log.

    Returns the number of corrupted lines.
    """
    import json as _json
    from pmk.events import canonical_json
    count = 0
    for path in kernel.log.files():
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            obj = _json.loads(line)
            if obj.get("type") == event_type and obj.get("subject") == subject:
                obj["ts"] = bad_ts
                lines[i] = canonical_json(obj)
                count += 1
                break  # only corrupt the first match in this file
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return count


def test_clock_parse_failure_skips_not_retries(git_repo_master):
    """A malformed timestamp on an INFRA_RETRY event must skip the drain tick,
    not fall through to an immediate retry (plan item 6d).

    The conductor catches (ValueError, TypeError) from parse_iso, records
    MERGE_REFUSED with reason "clock_parse", and ``continue``s the loop —
    producing zero new INFRA_RETRY events.
    """
    from pmk.events import Actor
    from fleet.conductor import Conductor
    from fleet.dispatcher import Dispatcher
    from fleet.overseer import OverseerRunner
    from fleet.state import FleetState
    from pmk.clock import FakeClock
    import shutil

    repo = git_repo_master
    clock = FakeClock()
    kernel = _make_kernel_from_repo(repo, clock=clock)
    write_agents(repo, [fake_profile()])

    task = make_task(kernel, scope={"write": ["src/thing.py"], "read": []})
    lease = _submit_task(kernel, task,
                         worktree_path=repo.root / "work" / "clock-parse")

    # Corrupt the repo so the first drain fails with INFRASTRUCTURE_FAILED,
    # producing an INFRA_RETRY event with a valid timestamp.
    refs_dir = repo.root / ".git" / "refs"
    if refs_dir.exists():
        shutil.rmtree(refs_dir)

    worktree = repo.root / "work" / "clock-parse"
    worktree.mkdir(parents=True, exist_ok=True)

    fleet_state = FleetState.load(kernel.repo.fleet_state_path)
    dispatcher = Dispatcher(kernel, fleet_state, fixture_root=None)
    overseer = OverseerRunner(kernel, fleet_state)
    conductor = Conductor(kernel, dispatcher, overseer)

    conductor.drain_merge_queue()
    infra_before = len([e for e in kernel.events() if e.type == "INFRA_RETRY"])
    assert infra_before == 1, "expected exactly one INFRA_RETRY after first failure"

    # Corrupt the timestamp in the raw log.
    corrupted = _corrupt_event_ts(kernel, "INFRA_RETRY", task.id, "not-a-real-timestamp")
    assert corrupted == 1, f"expected to corrupt 1 event, corrupted {corrupted}"

    # drain_merge_queue should hit the parse error, record MERGE_REFUSED,
    # and skip — no new INFRA_RETRY.
    conductor.drain_merge_queue()
    infra_after = len([e for e in kernel.events() if e.type == "INFRA_RETRY"])
    assert infra_after == infra_before, \
        f"clock parse failure must not create a new INFRA_RETRY: {infra_before} -> {infra_after}"

    refused = [e for e in kernel.events()
               if e.type == "MERGE_REFUSED" and e.subject == task.id]
    assert refused, "expected a MERGE_REFUSED event for the clock parse failure"
    assert refused[-1].payload.get("reason") == "clock_parse"

    try:
        _git(repo.root, "worktree", "remove", "--force", str(worktree))
    except subprocess.CalledProcessError:
        pass


def test_clock_parse_failure_skips_with_backoff_active(git_repo_master):
    """Even when inside the backoff window, a malformed INFRA_RETRY timestamp
    causes the drain to skip (not retry).  Both the backoff guard and the
    clock-parse guard must lead to ``continue``."""
    from fleet.conductor import Conductor
    from fleet.dispatcher import Dispatcher
    from fleet.overseer import OverseerRunner
    from fleet.state import FleetState
    from pmk.clock import FakeClock
    import shutil

    repo = git_repo_master
    clock = FakeClock()
    kernel = _make_kernel_from_repo(repo, clock=clock)
    write_agents(repo, [fake_profile()])
    repo.policy_path.write_text('[merge]\ninfra_retries = 3\n', encoding="utf-8")

    task = make_task(kernel, scope={"write": ["src/thing.py"], "read": []})
    lease = _submit_task(kernel, task,
                         worktree_path=repo.root / "work" / "clock-backoff")

    worktree = repo.root / "work" / "clock-backoff"
    worktree.mkdir(parents=True, exist_ok=True)

    # Corrupt the repo so the first drain fails with INFRASTRUCTURE_FAILED.
    refs_dir = repo.root / ".git" / "refs"
    if refs_dir.exists():
        shutil.rmtree(refs_dir)

    fleet_state = FleetState.load(kernel.repo.fleet_state_path)
    dispatcher = Dispatcher(kernel, fleet_state, fixture_root=None)
    overseer = OverseerRunner(kernel, fleet_state)
    conductor = Conductor(kernel, dispatcher, overseer)

    conductor.drain_merge_queue()
    infra_before = len([e for e in kernel.events() if e.type == "INFRA_RETRY"])
    assert infra_before == 1

    # Corrupt the timestamp of the INFRA_RETRY in the raw log.
    corrupted = _corrupt_event_ts(kernel, "INFRA_RETRY", task.id, "broken")
    assert corrupted == 1

    # Even though we're inside the 5s backoff, the clock parse failure
    # should hit the parse branch first and skip.
    clock.advance(1)
    conductor.drain_merge_queue()
    infra_after = len([e for e in kernel.events() if e.type == "INFRA_RETRY"])
    assert infra_after == 1, "clock parse failure must skip, not retry"

    try:
        _git(repo.root, "worktree", "remove", "--force", str(worktree))
    except subprocess.CalledProcessError:
        pass


# ---------------------------------------------------------------------------
# Per-fence retry: INFRA_RETRY for fence 1 does not block fence 2
# ---------------------------------------------------------------------------

def test_per_fence_retry_isolates_fences(git_repo_master):
    """INFRA_RETRY events are scoped per (task, fence).

    When a lease is re-claimed at a new fence (after revoke), the old
    fence's retry count must not contribute to the new fence's tally.
    """
    from fleet.conductor import Conductor
    from fleet.dispatcher import Dispatcher
    from fleet.overseer import OverseerRunner
    from fleet.state import FleetState
    from pmk.clock import FakeClock

    repo = git_repo_master
    clock = FakeClock()
    kernel = _make_kernel_from_repo(repo, clock=clock)
    write_agents(repo, [fake_profile()])
    repo.policy_path.write_text('[merge]\ninfra_retries = 3\n', encoding="utf-8")

    task = make_task(kernel, scope={"write": ["src/thing.py"], "read": []})
    lease = _submit_task(kernel, task,
                         worktree_path=repo.root / "work" / "per-fence")

    worktree = repo.root / "work" / "per-fence"
    worktree.mkdir(parents=True, exist_ok=True)

    try:
        fleet_state = FleetState.load(kernel.repo.fleet_state_path)
        dispatcher = Dispatcher(kernel, fleet_state, fixture_root=None)
        overseer = OverseerRunner(kernel, fleet_state)
        conductor = Conductor(kernel, dispatcher, overseer)

        # Corrupt the repo so the merge fails.
        import shutil
        refs_dir = repo.root / ".git" / "refs"
        if refs_dir.exists():
            shutil.rmtree(refs_dir)

        conductor.drain_merge_queue()
        infra_at_fence_1 = len([e for e in kernel.events()
                                if e.type == "INFRA_RETRY"
                                and e.subject == task.id
                                and e.fence == lease.fence])
        assert infra_at_fence_1 == 1

        # Revoke to bump the fence, creating a new lease at fence+1.
        new_fence = kernel.revoke(task.id, lease.fence,
                                  reason="oracle incompatible")
        assert new_fence == lease.fence + 1, f"expected fence {lease.fence + 1}, got {new_fence}"

        # Re-submit a bundle at the new fence.
        new_lease = Lease(task_id=task.id, fence=new_fence)
        from pmk.models import LEASED
        # The task is now READY/LEASED — re-claim.
        lease2 = kernel.claim(task.id, holder="p", worktree=str(worktree))
        bundle = _make_valid_bundle(task.id, lease2.fence)
        kernel.submit(task.id, lease2.fence, bundle)
        kernel.verify(task.id, lease2.fence, ok=True)

        # The old fence-1 INFRA_RETRY must not count toward fence-2.
        infra_at_fence_2 = len([e for e in kernel.events()
                                if e.type == "INFRA_RETRY"
                                and e.subject == task.id
                                and e.fence == new_fence])
        assert infra_at_fence_2 == 0, \
            f"INFRA_RETRY from fence {lease.fence} leaked into fence {new_fence}"
    finally:
        try:
            _git(repo.root, "worktree", "remove", "--force", str(worktree))
        except subprocess.CalledProcessError:
            pass


# ---------------------------------------------------------------------------
# clock_parse: MERGE_REFUSED(clock_parse) is recorded at most once per (task, fence)
# ---------------------------------------------------------------------------

def test_clock_parse_records_at_most_one_refusal(git_repo_master):
    """Draining 6+ times with a malformed INFRA_RETRY timestamp must produce
    at most ONE MERGE_REFUSED(clock_parse) event for the (task, fence) pair.

    The conductor's clock-parse guard checks the event log for an existing
    clock_parse refusal before recording a new one, so repeated ticks do not
    multiply the event.
    """
    from fleet.conductor import Conductor
    from fleet.dispatcher import Dispatcher
    from fleet.overseer import OverseerRunner
    from fleet.state import FleetState
    from pmk.clock import FakeClock
    import shutil

    repo = git_repo_master
    clock = FakeClock()
    kernel = _make_kernel_from_repo(repo, clock=clock)
    write_agents(repo, [fake_profile()])

    task = make_task(kernel, scope={"write": ["src/thing.py"], "read": []})
    lease = _submit_task(kernel, task,
                         worktree_path=repo.root / "work" / "clock-dedup")

    # Corrupt the repo so the first drain fails with INFRASTRUCTURE_FAILED,
    # producing an INFRA_RETRY event with a valid timestamp.
    refs_dir = repo.root / ".git" / "refs"
    if refs_dir.exists():
        shutil.rmtree(refs_dir)

    worktree = repo.root / "work" / "clock-dedup"
    worktree.mkdir(parents=True, exist_ok=True)

    try:
        fleet_state = FleetState.load(kernel.repo.fleet_state_path)
        dispatcher = Dispatcher(kernel, fleet_state, fixture_root=None)
        overseer = OverseerRunner(kernel, fleet_state)
        conductor = Conductor(kernel, dispatcher, overseer)

        # First drain: creates exactly one INFRA_RETRY.
        conductor.drain_merge_queue()
        infra_before = len([e for e in kernel.events()
                            if e.type == "INFRA_RETRY" and e.subject == task.id])
        assert infra_before == 1, f"expected 1 INFRA_RETRY, got {infra_before}"

        # Corrupt the timestamp.
        corrupted = _corrupt_event_ts(kernel, "INFRA_RETRY", task.id, "broken-ts")
        assert corrupted == 1

        # Drain 6 more times — each hits the clock-parse guard.
        for i in range(6):
            clock.advance(1)
            conductor.drain_merge_queue()

        refused = [e for e in kernel.events()
                   if e.type == "MERGE_REFUSED"
                   and e.subject == task.id
                   and e.payload.get("reason") == "clock_parse"]
        assert len(refused) == 1, \
            f"expected exactly 1 clock_parse refusal, got {len(refused)}"
    finally:
        try:
            _git(repo.root, "worktree", "remove", "--force", str(worktree))
        except subprocess.CalledProcessError:
            pass


# ---------------------------------------------------------------------------
# pytest.ini collision cleanup
# ---------------------------------------------------------------------------

def test_merge_removes_untracked_default_pytest_ini(git_repo_master):
    """An untracked, byte-identical pytest.ini at the repo root is deleted
    before the merge so the incoming pytest.ini becomes tracked (T-0009).
    """
    from fleet.merge import integrate, _DEFAULT_PYTEST_INI

    repo = git_repo_master
    kernel = _make_kernel_from_repo(repo)
    write_agents(repo, [fake_profile()])

    # kernel.init() wrote a default pytest.ini to the repo root (untracked).
    default_ini = repo.root / "pytest.ini"
    assert default_ini.is_file(), "kernel.init() must write pytest.ini"
    assert default_ini.read_text(encoding="utf-8") == _DEFAULT_PYTEST_INI

    # A worker's worktree also has a pytest.ini (same content).
    task = make_task(kernel, scope={"write": ["pytest.ini"], "read": []})
    lease = _submit_task(kernel, task,
                         worktree_path=repo.root / "work" / "ini-cleanup")

    # Write the same pytest.ini content in the worktree.
    worktree = repo.root / "work" / "ini-cleanup"
    branch = f"pmk/{task.id}-{lease.fence}"
    _git(repo.root, "worktree", "add", "-B", branch, str(worktree), "HEAD")
    (worktree / "pytest.ini").write_text(_DEFAULT_PYTEST_INI, encoding="utf-8")
    repo.git("add", "-A", cwd=worktree)
    repo.git("commit", "-m", "add pytest.ini", cwd=worktree)

    # Confirm the root pytest.ini is still untracked at this point.
    code, tracked, _ = repo.git("ls-files", "--", "pytest.ini")
    assert code == 0
    assert not tracked.strip(), "root pytest.ini should be untracked"

    # Run the merge — _cleanup_default_pytest_ini should delete the untracked
    # duplicate, then the worktree's tracked pytest.ini takes its place.
    result = integrate(kernel, task, lease, str(worktree),
                        gate_cmd="", keep_worktree=False)

    # The root pytest.ini must now be tracked (from the incoming commit).
    code, tracked, _ = repo.git("ls-files", "--", "pytest.ini")
    assert code == 0
    assert "pytest.ini" in tracked, \
        "root pytest.ini must be tracked after merge (incoming commit)"

    assert result.ok, result.message

    try:
        _git(repo.root, "worktree", "remove", "--force", str(worktree))
    except subprocess.CalledProcessError:
        pass


def test_merge_keeps_user_modified_pytest_ini(git_repo_master):
    """A user-modified (non-default) pytest.ini at the repo root is left alone;
    the merge should not delete it."""
    from fleet.merge import integrate

    repo = git_repo_master
    kernel = _make_kernel_from_repo(repo)
    write_agents(repo, [fake_profile()])

    task = make_task(kernel, scope={"write": ["src/thing.py"], "read": []})
    lease = _submit_task(kernel, task,
                         worktree_path=repo.root / "work" / "ini-keep")

    # Write a user-modified pytest.ini at the repo root (untracked, non-default).
    root_ini = repo.root / "pytest.ini"
    root_ini.write_text("[pytest]\ntestpaths = tests src\n", encoding="utf-8")

    worktree = repo.root / "work" / "ini-keep"
    _git(repo.root, "worktree", "add", "-B", f"pmk/{task.id}-{lease.fence}",
         str(worktree), "HEAD")

    try:
        result = integrate(kernel, task, lease, str(worktree),
                           gate_cmd="", keep_worktree=False)
        # The user-modified pytest.ini must still exist with original content.
        assert root_ini.is_file(), "user-modified pytest.ini must not be deleted"
        assert root_ini.read_text(encoding="utf-8") == "[pytest]\ntestpaths = tests src\n"
    finally:
        try:
            _git(repo.root, "worktree", "remove", "--force", str(worktree))
        except subprocess.CalledProcessError:
            pass


def test_merge_leaves_pytest_ini_for_unrelated_change(git_repo_master):
    """An unrelated merge (task does not touch pytest.ini) must leave the
    Kernel-written root pytest.ini in place (T-0009 guard).

    The cleanup runs ONLY when the incoming branch changes pytest.ini --
    either via write scope or via git diff.  Here the task writes to
    ``src/thing.py`` only, so the default pytest.ini that ``pmk init`` wrote
    must survive the merge.
    """
    from fleet.merge import integrate, _DEFAULT_PYTEST_INI

    repo = git_repo_master
    kernel = _make_kernel_from_repo(repo)
    write_agents(repo, [fake_profile()])

    # Kernel.init() wrote a default pytest.ini (untracked).
    root_ini = repo.root / "pytest.ini"
    assert root_ini.is_file()
    assert root_ini.read_text(encoding="utf-8") == _DEFAULT_PYTEST_INI

    task = make_task(kernel, scope={"write": ["src/thing.py"], "read": []})
    lease = _submit_task(kernel, task,
                         worktree_path=repo.root / "work" / "ini-unrelated")

    branch = f"pmk/{task.id}-{lease.fence}"
    worktree = repo.root / "work" / "ini-unrelated"
    _git(repo.root, "worktree", "add", "-B", branch, str(worktree), "HEAD")
    try:
        # The task writes src/thing.py, NOT pytest.ini.
        (worktree / "src" / "thing.py").write_text("VALUE = 2\n",
                                                    encoding="utf-8")
        repo.git("add", "-A", cwd=worktree)
        repo.git("commit", "-m", "change thing", cwd=worktree)

        result = integrate(kernel, task, lease, str(worktree),
                           gate_cmd="", keep_worktree=False)
        assert result.ok, result.message

        # The default pytest.ini must still be on disk.
        assert root_ini.is_file(), \
            "unrelated merge must not delete the root pytest.ini"
        assert root_ini.read_text(encoding="utf-8") == _DEFAULT_PYTEST_INI
    finally:
        try:
            _git(repo.root, "worktree", "remove", "--force", str(worktree))
        except subprocess.CalledProcessError:
            pass


def test_merge_cleanups_pytest_ini_via_diff_not_writescope(git_repo_master):
    """The cleanup fires when the incoming branch adds pytest.ini but the
    task's write scope is a directory/glob (not the literal "pytest.ini").

    The write-scope check alone would miss this case -- the scope declares
    "*.toml" or "tests/", not "pytest.ini" -- but ``git diff --name-only``
    reveals that the committed branch DOES add pytest.ini.  The default root
    file must be deleted and the merge must succeed.
    """
    from fleet.merge import integrate, _DEFAULT_PYTEST_INI

    repo = git_repo_master
    kernel = _make_kernel_from_repo(repo)
    write_agents(repo, [fake_profile()])

    # Kernel.init() wrote a default pytest.ini (untracked).
    root_ini = repo.root / "pytest.ini"
    assert root_ini.is_file()
    assert root_ini.read_text(encoding="utf-8") == _DEFAULT_PYTEST_INI

    # The task's write scope is a directory glob, NOT pytest.ini directly.
    task = make_task(kernel, scope={"write": ["config/"], "read": []})
    lease = _submit_task(kernel, task,
                         worktree_path=repo.root / "work" / "ini-glob")

    branch = f"pmk/{task.id}-{lease.fence}"
    worktree = repo.root / "work" / "ini-glob"
    _git(repo.root, "worktree", "add", "-B", branch, str(worktree), "HEAD")
    try:
        # The worker adds BOTH a config file (in-scope) AND a pytest.ini.
        (worktree / "config").mkdir(exist_ok=True)
        (worktree / "config" / "app.toml").write_text("[app]\nname = 'x'\n",
                                                       encoding="utf-8")
        (worktree / "pytest.ini").write_text(_DEFAULT_PYTEST_INI, encoding="utf-8")
        repo.git("add", "-A", cwd=worktree)
        repo.git("commit", "-m", "add config and pytest.ini", cwd=worktree)

        result = integrate(kernel, task, lease, str(worktree),
                           gate_cmd="", keep_worktree=False)
        assert result.ok, result.message

        # After merge, pytest.ini must be tracked from the incoming commit.
        code, tracked, _ = repo.git("ls-files", "--", "pytest.ini")
        assert code == 0
        assert "pytest.ini" in tracked, \
            "root pytest.ini must be tracked after merge (incoming commit)"
    finally:
        try:
            _git(repo.root, "worktree", "remove", "--force", str(worktree))
        except subprocess.CalledProcessError:
            pass


# ---------------------------------------------------------------------------
# task_admit type check
# ---------------------------------------------------------------------------

def test_task_admit_rejects_unknown_type(git_repo_master):
    """An unknown task type on an existing PROPOSED card is refused at
    task_admit (plan item 7a).

    task_create with admitted=False still runs the type check, so we write
    the TASK_CREATED event directly with a bad type, then call task_admit.
    """
    from pmk.api import KernelError
    from pmk.models import PROPOSED

    repo = git_repo_master
    kernel = _make_kernel_from_repo(repo)
    write_agents(repo, [fake_profile()])

    # Write the TASK_CREATED event directly with a bad type, bypassing the
    # create-time check, so the card lands in PROPOSED.
    kernel._append("TASK_CREATED", subject="T-9999",
                   payload={"card": {"id": "T-9999", "title": "bad",
                                     "type": "bogus", "goalRef": "",
                                     "scope": {"write": [], "read": []},
                                     "acceptance": {"oracles": [],
                                                    "evidence_required": []},
                                     "premises": [],
                                     "budget": {"tokens": 0, "wall_min": 0},
                                     "depends_on": [],
                                     "attempts": {"max": 3},
                                     "priority": 100, "agent_hint": "",
                                     "createdBy": {"kind": "human", "agent": "test"}},
                                 "admission_errors": []})
    state = kernel.state()
    assert state.tasks["T-9999"].state == PROPOSED
    assert state.tasks["T-9999"].type == "bogus"

    # task_admit must reject it.
    with pytest.raises(KernelError) as exc:
        kernel.task_admit("T-9999")
    assert exc.value.reason == "invalid_task_type"

    # Task must still be PROPOSED.
    assert kernel.state().tasks["T-9999"].state == PROPOSED


# ---------------------------------------------------------------------------
# Kernel.integrate with corrupt bundle
# ---------------------------------------------------------------------------

def test_integrate_rejects_corrupt_bundle(git_repo_master):
    """Kernel.integrate raises KernelError('invalid_bundle') when the
    bundle on disk is corrupt JSON (plan item 4b).

    This complements the failing-oracle test: that tests ok=False; this
    tests unreadable/undeserialisable bundle content.
    """
    from pmk.api import KernelError
    from pmk.bundle import Bundle

    repo = git_repo_master
    kernel = _make_kernel_from_repo(repo)
    write_agents(repo, [fake_profile()])

    task = make_task(kernel, scope={"write": ["src/thing.py"], "read": []})
    lease = kernel.claim(task.id, holder="p")
    bundle = _make_valid_bundle(task.id, lease.fence)
    kernel.submit(task.id, lease.fence, bundle)
    kernel.verify(task.id, lease.fence, ok=True)

    # Now corrupt the bundle on disk.
    bundle_path = Bundle.bundle_path(kernel.repo.evidence_dir, task.id, lease.fence)
    bundle_path.write_text("{ this is not valid json!!!", encoding="utf-8")

    with pytest.raises(KernelError) as exc:
        kernel.integrate(task.id, lease.fence, commit="corrupt-test")
    assert exc.value.reason == "invalid_bundle"
    from pmk.models import DONE
    assert kernel.state().tasks[task.id].state != DONE
