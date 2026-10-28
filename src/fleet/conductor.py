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
        from pmk.bundle import Bundle
        from pmk.clock import parse_iso
        from datetime import timezone

        state = self.kernel.state()
        policy = self.kernel.policy()
        gate_cmd = policy.get("gate", {}).get("cmd", "")
        max_retries = int(policy.get("merge", {}).get("infra_retries", 3))
        # Backoff schedule (seconds) for INFRASTRUCTURE_FAILED retries.
        # After max_retries (counted per task+fence), an INCIDENT is raised
        # with a unique id per task+fence, and the task is skipped on
        # subsequent ticks until the operator acts.
        backoff_schedule = [5, 30, 120]
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

            # --- Count INFRA_RETRY per (task, fence), not per task ---
            infra_retries = [e for e in self.kernel.events()
                             if e.type == "INFRA_RETRY"
                             and e.subject == task.id
                             and e.fence == lease.fence]

            # --- Skip tasks that already have an incident (operator must act) ---
            if len(infra_retries) >= max_retries:
                results.append({"ok": False, "task": task.id,
                                "message": "skipped: incident raised, awaiting operator",
                                "failure_class": "INFRASTRUCTURE_FAILED"})
                continue

            # --- Backoff: skip until the backoff period for this attempt elapsed ---
            if infra_retries:
                last_retry = infra_retries[-1]
                try:
                    last_ts = parse_iso(last_retry.ts)
                    if last_ts.tzinfo is None:
                        last_ts = last_ts.replace(tzinfo=timezone.utc)
                    backoff_s = float(last_retry.payload.get(
                        "backoff_s",
                        backoff_schedule[min(len(infra_retries) - 1,
                                             len(backoff_schedule) - 1)]))
                    now_ts = self.kernel.clock.now()
                    if now_ts.tzinfo is None:
                        now_ts = now_ts.replace(tzinfo=timezone.utc)
                    elapsed = (now_ts - last_ts).total_seconds()
                    if elapsed < backoff_s:
                        remaining = backoff_s - elapsed
                        results.append({"ok": False, "task": task.id,
                                        "message": f"backoff: waiting {remaining:.0f}s "
                                                   f"({backoff_s:.0f}s window)",
                                        "failure_class": "INFRASTRUCTURE_FAILED"})
                        continue
                except (ValueError, TypeError):
                    # A malformed timestamp on the last INFRA_RETRY means we
                    # cannot compute the backoff window.  Skip this tick
                    # (do NOT fall through to an immediate retry).  Record
                    # MERGE_REFUSED(clock_parse) at most once per (task, fence)
                    # so the event log does not grow unbounded across ticks.
                    existing = [e for e in self.kernel.events()
                                if e.type == "MERGE_REFUSED"
                                and e.subject == task.id
                                and e.fence == lease.fence
                                and e.payload.get("reason") == "clock_parse"]
                    if not existing:
                        self.kernel.record_event(
                            "MERGE_REFUSED", subject=task.id,
                            fence=lease.fence,
                            payload={"reason": "clock_parse",
                                     "message": f"bad timestamp on {last_retry.ts}"})
                    results.append({"ok": False, "task": task.id,
                                    "message": "clock parse failure: skipping tick",
                                    "failure_class": "INFRASTRUCTURE_FAILED"})
                    continue

            # --- I5 pre-merge check: bundle must exist and all oracles pass ---
            # Shared with Kernel.integrate() via Bundle.validation_problems().
            bundle_path = Bundle.bundle_path(self.kernel.repo.evidence_dir,
                                             task.id, lease.fence)
            if not bundle_path.is_file():
                self.kernel.record_event("MERGE_REFUSED", subject=task.id,
                                         fence=lease.fence,
                                         payload={"reason": "no_bundle",
                                                 "message": f"no evidence bundle at {bundle_path}"})
                try:
                    self.kernel.verify(task.id, lease.fence, ok=False,
                                       reasons=["no evidence bundle"])
                except KernelError:
                    pass  # verify may refuse if state isn't SUBMITTED/VERIFYING; record stands
                results.append({"ok": False, "task": task.id,
                                "message": "no evidence bundle"})
                continue

            try:
                bundle = Bundle.load_for_task(self.kernel.repo.evidence_dir,
                                              task.id, lease.fence)
            except (OSError, ValueError) as exc:
                self.kernel.record_event("MERGE_REFUSED", subject=task.id,
                                         fence=lease.fence,
                                         payload={"reason": "invalid_bundle",
                                                 "message": f"unreadable bundle: {exc}"})
                try:
                    self.kernel.verify(task.id, lease.fence, ok=False,
                                       reasons=[f"unreadable bundle: {exc}"])
                except KernelError:
                    pass
                results.append({"ok": False, "task": task.id,
                                "message": f"unreadable bundle: {exc}"})
                continue

            problems = bundle.validation_problems()
            if problems:
                self.kernel.record_event("MERGE_REFUSED", subject=task.id,
                                         fence=lease.fence,
                                         payload={"reason": "oracles_failed",
                                                  "message": "acceptance oracles failed: "
                                                             + (", ".join(problems) or "unknown")})
                try:
                    self.kernel.verify(task.id, lease.fence, ok=False,
                                       reasons=problems)
                except KernelError:
                    pass
                results.append({"ok": False, "task": task.id,
                                "message": "acceptance oracles failed"})
                continue

            result = merge_mod.integrate(self.kernel, task, lease, worktree,
                                         gate_cmd=gate_cmd)
            results.append(result.to_dict())
            if result.ok:
                try:
                    self.kernel.integrate(task.id, lease.fence,
                                          commit=result.commit)
                except KernelError as exc:
                    # Backstop: if integrate() refuses after fast-forward, record it.
                    self.kernel.record_event("MERGE_REFUSED", subject=task.id,
                                             fence=lease.fence,
                                             payload={"reason": "integrate_refused",
                                                      "message": str(exc)})
                    results[-1]["message"] += f"; integrate refused: {exc}"
            elif result.failure_class == "INFRASTRUCTURE_FAILED":
                # Git infrastructure failure (worktree, merge, fast-forward).
                # This is NOT an oracle failure — the bundle may be fine.
                # The task stays in SUBMITTED; the conductor retries on the
                # next tick.  After max_retries (per task+fence, with real
                # backoff — 5s, 30s, 120s), an INCIDENT is raised with a
                # unique id per task+fence and the task is skipped on
                # subsequent ticks until the operator acts.
                retry_count = len(infra_retries)
                self.kernel.record_event("INFRA_RETRY", subject=task.id,
                                         fence=lease.fence,
                                         payload={"attempt": retry_count + 1,
                                                  "message": result.message,
                                                  "backoff_s": float(
                                                      backoff_schedule[retry_count]
                                                      if retry_count < len(backoff_schedule)
                                                      else 120)})
                if retry_count + 1 >= max_retries:
                    incident_id = f"I-{task.id}-{lease.fence:04d}"
                    self.kernel.incident(
                        incident_id,
                        severity="error",
                        message=(f"{task.id}: git infrastructure failed "
                                 f"{retry_count + 1} times: {result.message}"),
                    )
                results.append({"ok": False, "task": task.id,
                                "message": result.message,
                                "failure_class": result.failure_class})
            else:
                # Gate failure (GATE_FAILED) or other non-infra refusal: this
                # is an oracle-level failure, NOT a git infrastructure failure.
                # Mark the attempt as failed via verify(ok=False), which
                # transitions the task to REWORK (not INFRA_RETRY, which is
                # only for git/worktree infrastructure failures).
                try:
                    self.kernel.verify(task.id, lease.fence, ok=False,
                                       reasons=[result.message])
                except KernelError as exc:
                    # State changed under us (e.g. task was revoked mid-drain).
                    # Record the swallowed error for observability instead of
                    # silently dropping it.  This is advisory, not a security
                    # boundary — an operator can always re-admit the task.
                    self.kernel.record_event("MERGE_REFUSED", subject=task.id,
                                             fence=lease.fence,
                                             payload={"reason": "verify_refused",
                                                      "message": str(exc)})
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
