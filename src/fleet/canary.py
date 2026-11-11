"""Single-owner canary runner.

The Console and ``pmk dispatch run`` are separate dispatch paths.  A canary
needs one owner: one Dispatcher and one Conductor, sharing one FleetState, in
one process.  This module is that owner.

The preflight is deliberately strict: exactly one READY card, no active
leases, no dispatch pause, and no ``pilot/STOP``.  The runner records
``CANARY_STARTED`` and ``CANARY_FINISHED`` events around the run; those events
are the durable record of who ran the canary and what state it reached.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from pmk.api import Kernel, KernelError
from pmk.events import Actor
from pmk.models import DONE, READY

from .conductor import Conductor
from .dispatcher import Dispatcher
from .owner import DispatchOwner, resume_dispatch
from .overseer import OverseerRunner
from .state import FleetState


def _only_canary_ready(kernel: Kernel, task_id: str) -> None:
    """Refuse if a new READY card appeared after the single-card preflight."""
    ready = [card.id for card in kernel.task_list(READY)]
    extra = [ready_id for ready_id in ready if ready_id != task_id]
    if extra:
        raise KernelError("canary_ready_set_changed", task=task_id,
                          ready=ready, extra=extra)


def run_canary(kernel: Kernel, *, seconds: float = 900.0,
               resume: bool = False,
               fixture_root: Path | None = None,
               tick_interval: float = 1.0,
               sleep: Callable[[float], None] = time.sleep,
               now: Callable[[], float] = time.monotonic) -> dict:
    """Run one canary under a single Dispatcher/Conductor owner.

    Refuses before dispatch unless exactly one card is READY, no leases are
    active, dispatch is not paused (or *resume* explicitly clears the pause)
    and ``pilot/STOP`` is absent.  The run finishes at *seconds*; ``ok`` is
    true only when the canary card is DONE and the finish event was written.
    """
    if seconds <= 0:
        raise KernelError("invalid_canary_seconds", seconds=seconds)

    state = kernel.state()
    ready = state.task_list(READY)
    if len(ready) != 1:
        raise KernelError("canary_requires_exactly_one_ready",
                          count=len(ready),
                          ready=[card.id for card in ready])
    card = ready[0]

    active = state.active_leases()
    if active:
        raise KernelError("canary_active_leases", task=card.id,
                          leases=sorted(active))
    if kernel.stopped():
        raise KernelError("stopped", detail="pilot/STOP is present")

    # The canary is a dispatch owner like the Console or ``pmk dispatch run``.
    # Take the shared lock before touching the pause state so a second owner
    # is refused without either process changing the line.
    owner = DispatchOwner.for_kernel(kernel, "canary").acquire()
    try:
        fleet_state = FleetState.load(kernel.repo.fleet_state_path)
        if fleet_state.dispatch_paused:
            if not resume:
                raise KernelError(
                    "dispatch_paused",
                    pause_reason=(fleet_state.pause_reason
                                  or "dispatch is paused"),
                    hint="pass --resume to clear the persisted pause")
            resume_dispatch(kernel, fleet_state, reason="canary run --resume")

        started_at = now()
        start_event = None
        finish_event = None
        error = None
        ticks = 0
        result: dict = {}
        try:
            start_event = kernel.record_event(
                "CANARY_STARTED", actor=Actor.kernel(), subject=card.id,
                payload={"task": card.id, "seconds": float(seconds),
                         "project_state": state.project_state,
                         "ready": [card.id]})
            dispatcher = Dispatcher(kernel, fleet_state,
                                    fixture_root=fixture_root)
            overseer = OverseerRunner(kernel, fleet_state)
            conductor = Conductor(kernel, dispatcher, overseer)
            deadline = started_at + float(seconds)
            while now() < deadline:
                if kernel.stopped():
                    raise KernelError("stopped",
                                      detail="pilot/STOP is present")
                conductor.tick()
                _only_canary_ready(kernel, card.id)
                dispatcher.tick()
                ticks += 1
                sleep(tick_interval)
        except BaseException as exc:                 # noqa: BLE001
            error = exc
            raise
        finally:
            final_state = kernel.state()
            final_card = final_state.tasks.get(card.id)
            task_state = (final_card.state if final_card is not None
                          else "MISSING")
            record_error = ""
            ok = error is None and task_state == DONE
            if start_event is not None:
                payload = {
                    "task": card.id,
                    "state": task_state,
                    "ok": ok,
                    "ticks": ticks,
                    "elapsed_s": round(max(0.0, now() - started_at), 3),
                }
                if error is not None:
                    payload["error"] = f"{type(error).__name__}: {error}"
                    payload["error_type"] = type(error).__name__
                try:
                    finish_event = kernel.record_event(
                        "CANARY_FINISHED", actor=Actor.kernel(),
                        subject=card.id, payload=payload)
                except BaseException as exc:          # noqa: BLE001
                    record_error = f"{type(exc).__name__}: {exc}"
                    payload["ok"] = False
                    payload["record_error"] = record_error
                    ok = False
            result = {
                "task": card.id,
                "state": task_state,
                "ok": ok,
                "ticks": ticks,
                "elapsed_s": round(max(0.0, now() - started_at), 3),
                "started_seq": (start_event.seq
                                if start_event is not None else None),
                "finished_seq": (finish_event.seq
                                 if finish_event is not None else None),
                "lock": str(owner.lock_path),
            }
            if error is not None:
                result["error"] = f"{type(error).__name__}: {error}"
            if record_error:
                result["record_error"] = record_error
        return result
    finally:
        owner.release()
