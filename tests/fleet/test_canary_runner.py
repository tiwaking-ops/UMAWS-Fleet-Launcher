"""Single-owner canary runner: strict preflight and one-owner execution."""

from __future__ import annotations

import pytest

from fleet import canary
from fleet.state import FleetState
from pmk.api import KernelError

from _fleet_fixtures import make_task


class _RecordingDispatcher:
    instances: list = []

    def __init__(self, kernel, fleet_state, *, fixture_root=None):
        self.kernel = kernel
        self.fleet_state = fleet_state
        self.fixture_root = fixture_root
        self.ticks = 0
        type(self).instances.append(self)

    def tick(self) -> None:
        self.ticks += 1


class _RecordingConductor:
    instances: list = []

    def __init__(self, kernel, dispatcher, overseer):
        self.kernel = kernel
        self.dispatcher = dispatcher
        self.overseer = overseer
        self.ticks = 0
        type(self).instances.append(self)

    def tick(self) -> None:
        self.ticks += 1


@pytest.fixture(autouse=True)
def _clear_recorders():
    _RecordingDispatcher.instances.clear()
    _RecordingConductor.instances.clear()


def _patch_owner(monkeypatch) -> None:
    monkeypatch.setattr(canary, "Dispatcher", _RecordingDispatcher)
    monkeypatch.setattr(canary, "Conductor", _RecordingConductor)
    monkeypatch.setattr(canary, "OverseerRunner",
                        lambda kernel, fleet_state: None)


def _canary_events(kernel) -> list:
    return [event for event in kernel.events()
            if event.type in ("CANARY_STARTED", "CANARY_FINISHED")]


def test_canary_requires_exactly_one_ready(fake_kernel):
    with pytest.raises(KernelError) as exc:
        canary.run_canary(fake_kernel, seconds=1)

    assert exc.value.reason == "canary_requires_exactly_one_ready"
    assert exc.value.details["count"] == 0
    assert exc.value.details["ready"] == []
    assert _canary_events(fake_kernel) == []


def test_canary_refuses_more_than_one_ready(fake_kernel):
    make_task(fake_kernel)
    make_task(fake_kernel, scope={"write": ["src/other.py"], "read": []})

    with pytest.raises(KernelError) as exc:
        canary.run_canary(fake_kernel, seconds=1)

    assert exc.value.reason == "canary_requires_exactly_one_ready"
    assert exc.value.details["count"] == 2
    assert _canary_events(fake_kernel) == []


def test_canary_refuses_active_leases(fake_kernel):
    claimed = make_task(fake_kernel)
    fake_kernel.claim(claimed.id, holder="fake-a", agent="fake",
                      role="implement")
    make_task(fake_kernel, scope={"write": ["src/other.py"], "read": []})

    with pytest.raises(KernelError) as exc:
        canary.run_canary(fake_kernel, seconds=1)

    assert exc.value.reason == "canary_active_leases"
    assert exc.value.details["leases"] == [claimed.id]
    assert _canary_events(fake_kernel) == []


def test_canary_refuses_paused_dispatch(fake_kernel):
    state = FleetState.load(fake_kernel.repo.fleet_state_path)
    state.dispatch_paused = True
    state.pause_reason = "test pause"
    state.save()
    make_task(fake_kernel)

    with pytest.raises(KernelError) as exc:
        canary.run_canary(fake_kernel, seconds=1)

    assert exc.value.reason == "dispatch_paused"
    assert exc.value.details["pause_reason"] == "test pause"
    assert _canary_events(fake_kernel) == []


def test_canary_uses_one_owner_and_records_the_run(fake_kernel, monkeypatch):
    task = make_task(fake_kernel)
    _patch_owner(monkeypatch)
    tick = [0.0]

    def now() -> float:
        return tick[0]

    def sleep(seconds: float) -> None:
        tick[0] += seconds

    result = canary.run_canary(
        fake_kernel, seconds=2.0, tick_interval=1.0,
        now=now, sleep=sleep)

    assert len(_RecordingDispatcher.instances) == 1
    assert len(_RecordingConductor.instances) == 1
    dispatcher = _RecordingDispatcher.instances[0]
    conductor = _RecordingConductor.instances[0]
    assert conductor.dispatcher is dispatcher
    assert conductor.dispatcher.fleet_state is dispatcher.fleet_state
    assert dispatcher.ticks == conductor.ticks == 2
    assert result["task"] == task.id
    assert result["ticks"] == 2
    assert result["state"] == "READY"
    assert result["ok"] is False
    assert result["started_seq"] is not None
    assert result["finished_seq"] is not None

    events = _canary_events(fake_kernel)
    assert [event.type for event in events] == [
        "CANARY_STARTED", "CANARY_FINISHED"]
    assert all(event.subject == task.id for event in events)
    assert events[0].payload["ready"] == [task.id]
    assert events[1].payload["ticks"] == 2
    assert events[1].payload["state"] == "READY"


def test_canary_run_is_wired_into_the_cli():
    from pmk.cli import build_parser, cmd_canary_run

    args = build_parser().parse_args(["canary", "run", "--seconds", "2"])

    assert args.func is cmd_canary_run
    assert args.seconds == 2.0
