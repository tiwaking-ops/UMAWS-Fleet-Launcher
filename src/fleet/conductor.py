"""The Conductor (fleet amendment sections 7.8 and 10).

The Conductor drives the project lifecycle and wakes the Overseer **on
events**.  It never runs a busy loop over the Overseer: it decides, once
per tick, whether a wake is warranted and whether the bounds allow it.

State machine::

    NEW -> PLANNING -> DECOMPOSING -> RUNNING -> CLOSING -> DONE

plus ``PAUSED`` and ``STALLED``.

The Conductor also runs the **merge queue**: submitted work is integrated
serially, and the gate command runs on the tree that will become
canonical.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from pmk.api import Kernel, KernelError

from . import merge as merge_mod
from . import project as project_mod
from .dispatcher import Dispatcher
from .overseer import OverseerRunner

#: The Dispatcher pauses for more than this long -> the project stalls.
DISPATCH_PAUSE_LIMIT_S = 1800


@dataclass
class Conductor:
    """Drives the lifecycle and the merge queue."""

    kernel: Kernel
    dispatcher: Dispatcher
    overseer: OverseerRunner
    replan_rounds: int = 0
    last_periodic: float = 0.0
    last_wake_reason: str = ""
    notes: list = field(default_factory=list)
    _stop = threading.Event()

    # ------------------------------------------------------------------
    # Wake detection
    # ------------------------------------------------------------------
    def detect_wake_reason(self) -> str:
        """Why should the Overseer be woken now?

        The order matters: the most specific reason wins, so the Overseer
        is never woken for ``replan`` when it actually needs to write the
        PDD.
        """
        state = self.kernel.state()
        repo = self.kernel.repo
        pdd = repo.root / project_mod.PDD_PATH
        plan_tasks = [t for t in state.task_list() if t.type == "plan"]
        other_tasks = [t for t in state.task_list() if t.type != "plan"]

        if plan_tasks and not pdd.is_file():
            return "needs-pdd"

        if pdd.is_file() and not other_tasks:
            return "needs-decomposition"

        if [t for t in state.task_list() if t.state in ("SUBMITTED", "VERIFYING")]:
            return "review"

        if [q for q in state.queue if q["state"] == "open"]:
            return "incident"

        ready = state.ready_tasks()
        if not ready and other_tasks and state.project_state not in (
                project_mod.DONE, project_mod.CLOSING):
            return "replan"

        now = time.time()
        periodic = float(self.overseer.periodic_s)
        if not self.last_periodic or (now - self.last_periodic) >= periodic:
            self.last_periodic = now
            return "periodic"

        return ""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def advance(self) -> dict:
        """Move the project one step, if it can move."""
        state = self.kernel.state()
        current = state.project_state
        repo = self.kernel.repo
        pdd = repo.root / project_mod.PDD_PATH
        notes: list[str] = []

        if current == project_mod.PAUSED or current == project_mod.STALLED:
            return {"state": current, "moved": False, "notes": notes}

        # -- PLANNING -> DECOMPOSING ---------------------------------
        if current == project_mod.PLANNING and pdd.is_file():
            kernel = self.kernel
            try:
                kernel.project_set_state(project_mod.DECOMPOSING,
                                         reason="the PDD is in place")
                notes.append("PDD ready; decomposing")
                return {"state": project_mod.DECOMPOSING, "moved": True,
                        "notes": notes}
            except KernelError:
                pass

        # -- DECOMPOSING -> RUNNING -----------------------------------
        if current == project_mod.DECOMPOSING:
            others = [t for t in state.task_list() if t.type != "plan"]
            if others:
                self.kernel.project_set_state(project_mod.RUNNING,
                                              reason="task cards exist")
                notes.append(f"{len(others)} task cards; running")
                return {"state": project_mod.RUNNING, "moved": True,
                        "notes": notes}

        # -- RUNNING -> CLOSING ----------------------------------------
        if current == project_mod.RUNNING:
            open_tasks = [t for t in state.task_list()
                          if t.state not in ("DONE", "VOID")]
            if not open_tasks:
                self.kernel.project_set_state(project_mod.CLOSING,
                                              reason="no open tasks")
                notes.append("no open tasks; closing")
                return {"state": project_mod.CLOSING, "moved": True,
                        "notes": notes}

        # -- CLOSING -> DONE or back to RUNNING ------------------------
        if current == project_mod.CLOSING:
            check = project_mod.close_check(self.kernel)
            if check.ok:
                self.kernel.project_set_state(project_mod.DONE,
                                              reason="the close-check is green")
                notes.append("close-check green; done")
                return {"state": project_mod.DONE, "moved": True,
                        "notes": notes,
                        "close_check": check.to_dict()}
            max_rounds = int(self.kernel.policy().get("recovery", {})
                             .get("max_replan_rounds", 3))
            if self.replan_rounds >= max_rounds:
                self.kernel.project_set_state(
                    project_mod.STALLED,
                    reason=f"max_replan_rounds ({max_rounds}) reached")
                self.kernel.queue_add(
                    topic="The project cannot be closed: the goal oracles "
                          "still fail.",
                    options=["fix the failing goal by hand",
                             "re-scope the goals",
                             "accept the project as incomplete"],
                    recommended="re-scope the goals",
                    safe_default="accept the project as incomplete",
                    details="; ".join(check.failures))
                notes.append("replan budget exhausted; stalled")
                return {"state": project_mod.STALLED, "moved": True,
                        "notes": notes, "close_check": check.to_dict()}
            self.replan_rounds += 1
            self.kernel.project_set_state(
                project_mod.RUNNING,
                reason=f"replan round {self.replan_rounds}")
            notes.append(f"close-check failed; replan round "
                         f"{self.replan_rounds}")
            return {"state": project_mod.RUNNING, "moved": True,
                    "notes": notes, "close_check": check.to_dict()}

        return {"state": current, "moved": False, "notes": notes}

    # ------------------------------------------------------------------
    # The merge queue
    # ------------------------------------------------------------------
    def drain_merge_queue(self) -> list[dict]:
        """Integrate submitted work, serially."""
        state = self.kernel.state()
        policy = self.kernel.policy()
        gate_cmd = policy.get("gate", {}).get("cmd", "")
        results = []
        for task in state.task_list():
            if task.state not in ("SUBMITTED", "VERIFYING"):
                continue
            lease = state.leases.get(task.id)
            if lease is None or not lease.worktree:
                continue
            worktree = lease.worktree
            if not (self.kernel.repo.root / "work").exists():
                continue
            result = merge_mod.integrate(self.kernel, task, lease, worktree,
                                         gate_cmd=gate_cmd)
            results.append(result.to_dict())
            if result.ok:
                try:
                    self.kernel.integrate(task.id, lease.fence,
                                          commit=result.commit)
                except KernelError as exc:
                    results[-1]["message"] += f"; integrate refused: {exc}"
            else:
                try:
                    self.kernel.verify(task.id, lease.fence, ok=False,
                                       reasons=[result.message])
                except KernelError:
                    pass
        return results

    # ------------------------------------------------------------------
    # Stalling
    # ------------------------------------------------------------------
    def check_stall(self) -> str:
        """Return ``STALLED`` when the project cannot continue."""
        state = self.kernel.state()
        if state.project_state in (project_mod.DONE, project_mod.PAUSED):
            return ""

        if self.kernel.stopped():
            return "the stop-the-line flag is set"

        profiles = self.dispatcher.profiles()
        if profiles:
            enabled = [p for p in profiles
                       if self.dispatcher.fleet_state.profile(p.id).enabled]
            if not enabled:
                return "every profile is disabled"

        fleet_state = self.dispatcher.fleet_state
        if fleet_state.dispatch_paused and fleet_state.paused_at:
            if (time.time() - fleet_state.paused_at) > DISPATCH_PAUSE_LIMIT_S:
                return (f"dispatch has been paused for more than "
                        f"{DISPATCH_PAUSE_LIMIT_S // 60} minutes")

        return ""

    # ------------------------------------------------------------------
    # One tick
    # ------------------------------------------------------------------
    def tick(self) -> dict:
        """One conductor tick."""
        result: dict = {"state": self.kernel.project_state(), "notes": []}

        merged = self.drain_merge_queue()
        if merged:
            result["merged"] = merged

        advanced = self.advance()
        result["state"] = advanced["state"]
        result["notes"].extend(advanced.get("notes", []))
        if "close_check" in advanced:
            result["close_check"] = advanced["close_check"]

        reason = self.detect_wake_reason()
        if reason:
            wake = self.overseer.wake(reason)
            result["wake"] = wake.to_dict()
            self.last_wake_reason = reason

        stall = self.check_stall()
        if stall:
            self.kernel.project_set_state(project_mod.STALLED, reason=stall)
            self.kernel.queue_add(
                topic=f"The project stalled: {stall}",
                options=["fix the cause and resume", "re-scope the project",
                         "stop the project"],
                recommended="fix the cause and resume",
                safe_default="stop the project",
                details=stall)
            result["stalled"] = stall
            result["state"] = project_mod.STALLED

        return result

    def run_forever(self, stop_event: threading.Event | None = None,
                    max_seconds: float | None = None) -> None:
        """The conductor loop."""
        tick = float(self.dispatcher.fleet_config.get("dispatch_tick_s", 5))
        deadline = None if max_seconds is None else time.time() + max_seconds
        while not self._stop.is_set():
            if stop_event is not None and stop_event.is_set():
                break
            if deadline is not None and time.time() > deadline:
                break
            try:
                self.tick()
            except Exception as exc:                # noqa: BLE001
                print(f"[conductor] tick failed: {exc}", flush=True)
            self._stop.wait(tick)

    def stop(self) -> None:
        self._stop.set()
