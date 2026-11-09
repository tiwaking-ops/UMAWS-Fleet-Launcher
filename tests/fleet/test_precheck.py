"""S8: a lease whose oracles already pass on the base must not be claimed.

T-0145 attempt 2 burned a lease discovering that main already contained the
change.  These tests run the real precheck against a real worktree of the
fixture repository: the check is the task's own oracle, not a heuristic.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

from fleet import precheck
from fleet.harness import Harness

from _fleet_fixtures import write_agents

PY = f'"{sys.executable}"'


def _task(oracles):
    return SimpleNamespace(id="T-9001", oracles=oracles)


def test_precheck_detects_a_task_the_base_already_satisfies(kernel):
    ok, results = precheck.oracles_already_pass(
        kernel, _task([f'{PY} -c "import sys"']))

    assert ok is True
    assert results and results[0]["ok"] is True


def test_precheck_reports_an_unsatisfied_task(kernel):
    ok, results = precheck.oracles_already_pass(
        kernel, _task([f'{PY} -c "import sys; sys.exit(3)"']))

    assert ok is False
    assert results[0]["exit"] == 3


def test_precheck_without_oracles_never_blocks(kernel):
    ok, results = precheck.oracles_already_pass(kernel, _task([]))

    assert ok is False
    assert results == []


def test_precheck_is_opt_in_fleet_config(kernel):
    write_agents(kernel.repo, [],
                 fleet={"max_total_agents": 2, "dispatch_tick_s": 1,
                        "stall_minutes": 15, "min_free_ram_mb": 0,
                        "precheck_satisfied": True})

    assert Harness._precheck_enabled(SimpleNamespace(repo=kernel.repo)) is True


def test_precheck_is_off_by_default(kernel):
    write_agents(kernel.repo, [])

    assert Harness._precheck_enabled(SimpleNamespace(repo=kernel.repo)) is False
