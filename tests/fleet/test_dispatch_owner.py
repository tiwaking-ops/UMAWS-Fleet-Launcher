"""One dispatch owner: the shared sidecar lock and its callers."""

from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest

from fleet import canary
from fleet.dispatcher import Dispatcher
from fleet.owner import (
    DispatchOwner,
    clear_stale_owner,
    owner_info_path,
    owner_lock_path,
    owner_status,
)
from fleet.state import FleetState
from pmk.api import KernelError

from _fleet_fixtures import make_task


def test_dispatch_owner_is_exclusive(fake_kernel):
    first = DispatchOwner.for_kernel(fake_kernel, "first").acquire()
    try:
        second = DispatchOwner.for_kernel(fake_kernel, "second")
        with pytest.raises(KernelError) as exc:
            second.acquire()

        assert exc.value.reason == "dispatch_owner_busy"
        assert exc.value.details["role"] == "second"
        assert str(owner_lock_path(fake_kernel)) in exc.value.details["lock"]
        assert second.held is False
    finally:
        first.release()

    replacement = DispatchOwner.for_kernel(fake_kernel, "replacement").acquire()
    try:
        assert replacement.held is True
    finally:
        replacement.release()


def test_cli_dispatch_refuses_a_second_owner(fake_kernel):
    from pmk.cli import cmd_dispatch_run

    owner = DispatchOwner.for_kernel(fake_kernel, "existing").acquire()
    try:
        args = SimpleNamespace(root=str(fake_kernel.repo.root), seconds=0.0,
                               resume=False)
        with pytest.raises(KernelError) as exc:
            cmd_dispatch_run(args)
    finally:
        owner.release()

    assert exc.value.reason == "dispatch_owner_busy"


def test_cli_dispatch_requires_resume_when_paused(fake_kernel):
    from pmk.cli import cmd_dispatch_run

    state = FleetState.load(fake_kernel.repo.fleet_state_path)
    state.dispatch_paused = True
    state.pause_reason = "test pause"
    state.save()

    args = SimpleNamespace(root=str(fake_kernel.repo.root), seconds=0.0,
                           resume=False)
    with pytest.raises(KernelError) as exc:
        cmd_dispatch_run(args)

    assert exc.value.reason == "dispatch_paused"
    assert exc.value.details["pause_reason"] == "test pause"


def test_cli_dispatch_resume_clears_the_pause(fake_kernel, monkeypatch):
    from pmk.cli import cmd_dispatch_run

    # Clearing a safety pause now requires human authority (reviewer item 3).
    monkeypatch.setenv("PMK_ACTOR", "human:operator")
    monkeypatch.setattr("pmk.authority.stdin_is_interactive", lambda: True)

    state = FleetState.load(fake_kernel.repo.fleet_state_path)
    state.dispatch_paused = True
    state.pause_reason = "test pause"
    state.save()

    class _FakeDispatcher:
        def __init__(self, kernel, fleet_state, *, fixture_root=None):
            self.fleet_state = fleet_state

        def run_forever(self, *, max_seconds=None):
            self.max_seconds = max_seconds

        def status(self):
            return {"dispatch_paused": self.fleet_state.dispatch_paused}

    import fleet.dispatcher as dispatcher_module
    monkeypatch.setattr(dispatcher_module, "Dispatcher", _FakeDispatcher)

    args = SimpleNamespace(root=str(fake_kernel.repo.root), seconds=0.0,
                           resume=True)
    assert cmd_dispatch_run(args) == 0
    assert FleetState.load(fake_kernel.repo.fleet_state_path).dispatch_paused is False
    assert any(event.type == "DISPATCH_RESUMED"
               for event in fake_kernel.events())


def test_owner_status_reports_free_then_active(fake_kernel):
    free = owner_status(fake_kernel)
    assert free["state"] == "free"
    assert free["held"] is False
    assert free["lock"].endswith("dispatch.owner.lock")

    owner = DispatchOwner.for_kernel(fake_kernel, "console").acquire()
    try:
        active = owner_status(fake_kernel)
        assert active["state"] == "active"
        assert active["held"] is True
        assert active["role"] == "console"
        assert active["pid"] == os.getpid()
    finally:
        owner.release()

    assert owner_status(fake_kernel)["state"] == "free"


def test_owner_status_reports_stale_metadata(fake_kernel):
    owner_info_path(fake_kernel).write_text(
        json.dumps({"role": "console", "pid": 1, "acquired_at": 0.0}),
        encoding="utf-8",
    )

    stale = owner_status(fake_kernel)

    assert stale["state"] == "stale"
    assert stale["held"] is False
    assert stale["role"] == "console"


def test_owner_status_treats_malformed_metadata_as_stale(fake_kernel):
    owner_info_path(fake_kernel).write_text("{not json", encoding="utf-8")

    stale = owner_status(fake_kernel)

    assert stale["state"] == "stale"
    assert stale["held"] is False
    assert stale["detail"]


def test_clear_stale_owner_removes_abandoned_metadata(fake_kernel):
    info = owner_info_path(fake_kernel)
    info.write_text(json.dumps({"role": "crashed", "pid": 1}),
                    encoding="utf-8")
    assert owner_status(fake_kernel)["state"] == "stale"

    result = clear_stale_owner(fake_kernel)

    assert result["cleared"] is True
    assert result["state"] == "free"
    assert not info.exists()


def test_clear_stale_owner_refuses_a_live_lock(fake_kernel):
    owner = DispatchOwner.for_kernel(fake_kernel, "console").acquire()
    try:
        with pytest.raises(KernelError) as exc:
            clear_stale_owner(fake_kernel)
        assert exc.value.reason == "dispatch_owner_busy"
        assert owner_info_path(fake_kernel).exists()
    finally:
        owner.release()


def test_dispatcher_status_includes_the_dispatch_owner(fake_kernel):
    state = FleetState.load(fake_kernel.repo.fleet_state_path)
    dispatcher = Dispatcher(fake_kernel, state)
    assert dispatcher.status()["dispatch_owner"]["state"] == "free"

    owner = DispatchOwner.for_kernel(fake_kernel, "console").acquire()
    try:
        active = dispatcher.status()["dispatch_owner"]
    finally:
        owner.release()

    assert active["state"] == "active"
    assert active["role"] == "console"


def test_canary_shares_the_dispatch_lock(fake_kernel):
    make_task(fake_kernel)
    owner = DispatchOwner.for_kernel(fake_kernel, "existing").acquire()
    try:
        with pytest.raises(KernelError) as exc:
            canary.run_canary(fake_kernel, seconds=1)
    finally:
        owner.release()

    assert exc.value.reason == "dispatch_owner_busy"
