"""Overseer wakes are edge-triggered and silent while the project is PAUSED.

A reason fires when the facts behind it change (a new open queue item, a newly
submitted task) and again only after ``wake_retry_seconds``.  The old behaviour
was level-triggered: an open queue item woke the Overseer on every tick for as
long as it stayed open.
"""

from __future__ import annotations

import time

from fleet.conductor import Conductor
from fleet.dispatcher import Dispatcher
from fleet.overseer import OverseerRunner
from fleet.state import FleetState

from _fleet_fixtures import FIXTURE_ROOT, make_task

RETRY_S = 1800.0


class _Wake:
    def __init__(self, reason: str, started: bool = True, error: str = ""):
        self.reason, self.started, self.error = reason, started, error

    def to_dict(self) -> dict:
        return {"reason": self.reason, "started": self.started,
                "error": self.error}


def _conductor(kernel, wakes: list, *, started: bool = True,
               error: str = "") -> Conductor:
    """A Conductor whose Overseer never really starts; every wake is recorded."""
    fleet_state = FleetState()
    dispatcher = Dispatcher(kernel, fleet_state, fixture_root=FIXTURE_ROOT)
    overseer = OverseerRunner(kernel, fleet_state)

    def wake(reason, **kwargs):
        wakes.append(reason)
        return _Wake(reason, started=started, error=error)

    overseer.wake = wake
    conductor = Conductor(kernel=kernel, dispatcher=dispatcher, overseer=overseer)
    conductor.wake_retry_seconds = lambda: RETRY_S
    conductor.last_periodic = time.time()       # the periodic wake is not under test
    return conductor


def _open_item(kernel, topic: str) -> None:
    kernel.queue_add(topic=topic, options=["a", "b"], recommended="a",
                     safe_default="b", details=topic)


def test_an_open_queue_item_wakes_the_overseer_once(fake_kernel):
    wakes: list = []
    conductor = _conductor(fake_kernel, wakes)
    _open_item(fake_kernel, "first")

    for _ in range(20):
        conductor.maybe_wake()

    assert wakes == ["incident"]


def test_the_same_open_item_wakes_again_after_the_retry_interval(
        fake_kernel, clock):
    wakes: list = []
    conductor = _conductor(fake_kernel, wakes)
    _open_item(fake_kernel, "first")

    conductor.maybe_wake()
    clock.advance(RETRY_S - 1)
    assert conductor.maybe_wake() is None
    clock.advance(2)
    assert conductor.maybe_wake() is not None

    assert wakes == ["incident", "incident"]


def test_a_new_queue_item_wakes_immediately(fake_kernel):
    wakes: list = []
    conductor = _conductor(fake_kernel, wakes)
    _open_item(fake_kernel, "first")
    conductor.maybe_wake()
    assert conductor.maybe_wake() is None

    _open_item(fake_kernel, "second")
    assert conductor.maybe_wake() is not None

    assert wakes == ["incident", "incident"]


def test_nothing_wakes_the_overseer_while_the_project_is_paused(fake_kernel):
    wakes: list = []
    conductor = _conductor(fake_kernel, wakes)
    _open_item(fake_kernel, "first")
    fake_kernel.project_set_state("PAUSED", reason="test")
    conductor.last_periodic = 0.0               # a periodic wake is due, and still must not fire

    for _ in range(5):
        assert conductor.maybe_wake() is None
    assert wakes == []

    fake_kernel.project_set_state("RUNNING", reason="test")
    assert conductor.maybe_wake() is not None
    assert wakes == ["incident"]


def test_a_deferred_wake_is_tried_again_on_the_next_tick(fake_kernel):
    """Debounce and the hourly bound defer a wake; they must not consume it."""
    wakes: list = []
    conductor = _conductor(fake_kernel, wakes, started=False,
                           error="debounced (5s of 60s)")
    _open_item(fake_kernel, "first")

    conductor.maybe_wake()
    conductor.maybe_wake()

    assert wakes == ["incident", "incident"]


def test_a_wake_that_could_not_start_is_not_retried_every_tick(fake_kernel):
    wakes: list = []
    conductor = _conductor(fake_kernel, wakes, started=False,
                           error="the Overseer profile x is disabled")
    _open_item(fake_kernel, "first")

    for _ in range(10):
        conductor.maybe_wake()

    assert wakes == ["incident"]


def test_needs_pdd_wakes_once_for_the_same_plan_task(fake_kernel):
    wakes: list = []
    conductor = _conductor(fake_kernel, wakes)
    make_task(fake_kernel, type="plan")

    for _ in range(5):
        conductor.maybe_wake()

    assert wakes == ["needs-pdd"]


def test_review_wakes_once_per_newly_submitted_task(fake_kernel):
    wakes: list = []
    conductor = _conductor(fake_kernel, wakes)
    first = make_task(fake_kernel, scope={"write": ["src/a.py"], "read": []})
    lease = fake_kernel.claim(first.id, holder="fake-a", agent="fake",
                              role="implement")
    fake_kernel.record_event("SUBMITTED", subject=first.id, fence=lease.fence,
                             payload={})

    for _ in range(5):
        conductor.maybe_wake()
    assert wakes == ["review"]

    second = make_task(fake_kernel, scope={"write": ["src/b.py"], "read": []})
    lease2 = fake_kernel.claim(second.id, holder="fake-a", agent="fake",
                               role="implement")
    fake_kernel.record_event("SUBMITTED", subject=second.id, fence=lease2.fence,
                             payload={})
    conductor.maybe_wake()

    assert wakes == ["review", "review"]


def test_a_quiet_reason_also_silences_lower_reasons_and_the_periodic_wake(
        fake_kernel):
    """While a submitted task awaits review, "replan" (no task is ready) also
    applies; the more specific reason wins even when it is quiet."""
    wakes: list = []
    conductor = _conductor(fake_kernel, wakes)
    task = make_task(fake_kernel, scope={"write": ["src/a.py"], "read": []})
    lease = fake_kernel.claim(task.id, holder="fake-a", agent="fake",
                              role="implement")
    fake_kernel.record_event("SUBMITTED", subject=task.id, fence=lease.fence,
                             payload={})
    conductor.maybe_wake()
    assert wakes == ["review"]

    conductor.last_periodic = 0.0               # a periodic wake is due, and still must not fire
    for _ in range(10):
        conductor.maybe_wake()

    assert wakes == ["review"]
