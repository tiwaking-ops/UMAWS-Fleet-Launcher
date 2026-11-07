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
from datetime import datetime

from pmk.api import Kernel, KernelError
from pmk.clock import parse_iso
from pmk.events import Actor
from pmk.models import LEASED

from . import merge as merge_mod
from . import project as project_mod
from . import spawn as spawn_mod
from .dispatcher import Dispatcher
from .overseer import OverseerRunner

#: The Dispatcher pauses for more than this long -> the project stalls.
DISPATCH_PAUSE_LIMIT_S = 1800

#: After a failed reap of one lease, wait this long before trying it again.
REAP_RETRY_S = 300


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
    #: (task id, fence) -> monotonic time before which a failed reap is not retried.
    _reap_retry_at: dict = field(default_factory=dict, repr=False)
    #: reason -> (fingerprint, monotonic time) of the last wake attempted for it.
    _wake_seen: dict = field(default_factory=dict, repr=False)
    #: (reason, fingerprint) of the wake that detect_wake_reason last returned.
    _wake_candidate: tuple | None = field(default=None, repr=False)
    _stop = threading.Event()

    # ------------------------------------------------------------------
    # Wake detection
    # ------------------------------------------------------------------
    def wake_retry_seconds(self) -> float:
        """How long the same reason, for the same facts, stays quiet (policy
        ``recovery.wake_retry_s``, default 30 minutes)."""
        return float(self.kernel.policy().get("recovery", {})
                     .get("wake_retry_s", 1800))

    def _wake_is_new(self, reason: str, fingerprint: str) -> bool:
        """Has *reason* not been attempted for this fingerprint recently?

        Wakes are edge-triggered: a reason fires when the facts behind it
        change, or again after ``wake_retry_seconds``.  Without this an open
        queue item woke the Overseer on every tick, for as long as it stayed
        open.
        """
        seen = self._wake_seen.get(reason)
        if seen is None:
            return True
        old_fingerprint, when = seen
        if old_fingerprint != fingerprint:
            return True
        return (self.kernel.clock.monotonic() - when) >= self.wake_retry_seconds()

    def detect_wake_reason(self) -> str:
        """Why should the Overseer be woken now?

        The order matters: the most specific reason wins, so the Overseer
        is never woken for ``replan`` when it actually needs to write the
        PDD.

        Wakes are edge-triggered (see :meth:`_wake_is_new`), and nothing wakes
        the Overseer while the project is PAUSED.  ``human-message`` wakes do
        not come through here: the Console calls the runner directly.  The
        periodic wake is returned only when no reason applies at all.
        """
        self._wake_candidate = None
        state = self.kernel.state()
        if state.project_state == project_mod.PAUSED:
            return ""
        repo = self.kernel.repo
        pdd = repo.root / project_mod.PDD_PATH
        plan_tasks = [t for t in state.task_list() if t.type == "plan"]
        other_tasks = [t for t in state.task_list() if t.type != "plan"]

        candidates: list[tuple[str, str]] = []

        if plan_tasks and not pdd.is_file():
            candidates.append(("needs-pdd",
                               ",".join(sorted(t.id for t in plan_tasks))))

        if pdd.is_file() and not other_tasks:
            candidates.append(("needs-decomposition", "pdd-without-tasks"))

        reviewing = [t for t in state.task_list()
                     if t.state in ("SUBMITTED", "VERIFYING")]
        if reviewing:
            candidates.append(("review", ",".join(
                sorted(f"{t.id}:{t.state}" for t in reviewing))))

        open_items = [q for q in state.queue if q["state"] == "open"]
        if open_items:
            candidates.append(("incident", ",".join(
                sorted(str(q["id"]) for q in open_items))))

        ready = state.ready_tasks()
        if not ready and other_tasks and state.project_state not in (
                project_mod.DONE, project_mod.CLOSING):
            candidates.append(("replan", ",".join(
                sorted(f"{t.id}:{t.state}" for t in state.task_list()))))

        if candidates:
            # The most specific reason wins, as before: while a higher
            # reason applies, no lower reason fires, even when the higher one
            # is quiet.  A quiet reason also silences the periodic wake; it
            # fires again by itself after wake_retry_seconds.
            reason, fingerprint = candidates[0]
            if self._wake_is_new(reason, fingerprint):
                self._wake_candidate = (reason, fingerprint)
                return reason
            return ""

        now = time.time()
        periodic = float(self.overseer.periodic_s)
        if not self.last_periodic or (now - self.last_periodic) >= periodic:
            self.last_periodic = now
            return "periodic"

        return ""

    def _note_wake_attempt(self, reason: str, wake) -> None:
        """Remember that *reason* was attempted, unless the runner merely
        deferred it (debounce or the hourly bound): a deferred wake must be
        tried again on a later tick."""
        candidate = self._wake_candidate
        if candidate is None or candidate[0] != reason:
            return
        error = str(getattr(wake, "error", "") or "")
        if not getattr(wake, "started", False) and (
                error.startswith("debounced") or error.startswith("hourly bound")):
            return
        self._wake_seen[reason] = (candidate[1], self.kernel.clock.monotonic())

    def maybe_wake(self) -> dict | None:
        """Decide whether to wake the Overseer, and do it.  Returns the wake
        record, or ``None`` when nothing warrants a wake."""
        reason = self.detect_wake_reason()
        if not reason:
            return None
        wake = self.overseer.wake(reason)
        self.last_wake_reason = reason
        self._note_wake_attempt(reason, wake)
        return wake.to_dict()

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
    # Lease expiry: orphaned leases only
    # ------------------------------------------------------------------
    def lease_ttl_seconds(self) -> float:
        """The lease time-to-live from policy, in seconds (default 20 minutes)."""
        minutes = float(self.kernel.policy().get("lease", {})
                        .get("ttl_minutes", 20))
        return minutes * 60.0

    @staticmethod
    def last_heartbeat(lease) -> datetime | None:
        """The later of ``granted_at`` and ``renewed_at``, or ``None`` if
        neither can be read.  ``expires_at`` is not used: ``claim`` never sets it."""
        beats = []
        for text in (lease.granted_at, lease.renewed_at):
            if not text:
                continue
            try:
                beats.append(parse_iso(str(text)))
            except ValueError:
                continue
        return max(beats) if beats else None

    def expired_leases(self, state=None) -> list:
        """Leases that are orphaned and past their TTL, as
        ``(task id, lease, age in seconds)``.

        A lease is considered only when its task is exactly ``LEASED`` (a
        submitted, verifying, integrating or finished task keeps its lease
        record but is not running), the project is not PAUSED or DONE and
        the stop-the-line flag is clear.  A lease this process supervises is
        never expired: the harness renews it every ``renew_every`` seconds
        and has its own stall detection.  The harness renews on the
        dispatcher's thread, so a lease can look old while another lease is
        finishing; only a lease nobody supervises is an orphan.
        """
        state = state or self.kernel.state()
        if state.project_state in (project_mod.PAUSED, project_mod.DONE):
            return []
        if self.kernel.stopped():
            return []
        now = self.kernel.clock.now()
        ttl = self.lease_ttl_seconds()
        expired = []
        for task_id, lease in sorted(state.leases.items()):
            card = state.tasks.get(task_id)
            if card is None or card.state != LEASED:
                continue
            run = self.dispatcher.runs.get(task_id)
            if run is not None and run.lease.fence == lease.fence:
                continue
            beat = self.last_heartbeat(lease)
            if beat is None:
                continue
            age = (now - beat).total_seconds()
            if age > ttl:
                expired.append((task_id, lease, age))
        return expired

    def reap_expired_leases(self) -> list:
        """Stop and revoke leases whose supervisor is gone.

        For each orphan past its TTL: stop the agent process if it is still
        the recorded process (pid and creation time must both match), then
        revoke the lease so the task returns to READY.  A failure at any
        step is recorded as ``LEASE_REAP_FAILED`` and that lease is not
        retried for ``REAP_RETRY_S``; the other leases are still handled.
        If the process is alive and cannot be stopped, the lease is not
        revoked.
        """
        results: list[dict] = []
        state = self.kernel.state()
        for task_id, lease, age in self.expired_leases(state):
            key = (task_id, lease.fence)
            retry_at = self._reap_retry_at.get(key)
            if (retry_at is not None
                    and self.kernel.clock.monotonic() < retry_at):
                continue
            info = {"task": task_id, "fence": lease.fence, "age_s": int(age)}
            try:
                results.append(self._reap_one(state, task_id, lease, age, info))
            except Exception as exc:                # noqa: BLE001
                results.append(self._reap_failed(
                    info, key, "unexpected", f"{type(exc).__name__}: {exc}"))
        return results

    def _reap_one(self, state, task_id: str, lease, age: float,
                  info: dict) -> dict:
        key = (task_id, lease.fence)
        stopped = None
        started = None
        for event in reversed(state.events):
            if (event.type == "AGENT_STARTED" and event.subject == task_id
                    and event.fence == lease.fence):
                started = event
                break
        if started is not None:
            payload = started.payload or {}
            pid = payload.get("pid")
            creation_time = payload.get("creation_time")
            if pid is not None and creation_time is not None:
                slot = spawn_mod.Slot(
                    task_id=task_id, profile_id=str(payload.get("profile", "")),
                    adapter=str(payload.get("adapter", "")), argv=[],
                    pid=int(pid), creation_time=int(creation_time))
                if spawn_mod.slot_alive(slot):
                    ok, message = spawn_mod.kill_slot(slot)
                    stopped = {"pid": int(pid), "ok": bool(ok),
                               "message": str(message)}
                    if not ok:
                        return self._reap_failed(info, key, "kill", str(message))
            elif pid is not None:
                stopped = {"pid": int(pid), "ok": False,
                           "message": "creation time not recorded; not stopped"}
        minutes = int(age // 60)
        ttl_minutes = self.lease_ttl_seconds() / 60.0
        try:
            new_fence = self.kernel.revoke(
                task_id, lease.fence, actor=Actor.kernel(),
                reason=(f"lease expired: no heartbeat for {minutes} min "
                        f"(ttl {ttl_minutes:g} min)"))
        except KernelError as exc:
            return self._reap_failed(info, key, "revoke", str(exc))
        self._reap_retry_at.pop(key, None)
        payload = dict(info, new_fence=new_fence)
        if stopped is not None:
            payload["process"] = stopped
        # REC-01: the revoke bumped the fence, so this lease's worktree is
        # now stranded.  Reclaim it -- but only when the operator has
        # enabled `worktree.reclaim_on_reap`, and only after a capture that
        # verifies (a tree whose capture fails is kept).
        reclaim = self._reclaim_worktree(lease)
        if reclaim is not None:
            payload["worktree_reclaim"] = reclaim
        self.kernel.record_event("LEASE_REAPED", actor=Actor.kernel(),
                                 subject=task_id, fence=lease.fence,
                                 payload=payload)
        if reclaim is not None:
            self.kernel.record_event("WORKTREE_RECLAIMED", actor=Actor.kernel(),
                                     subject=task_id, fence=lease.fence,
                                     payload=reclaim)
        return dict(payload, reaped=True)

    def _reclaim_worktree(self, lease) -> dict | None:
        """Capture-then-remove a bumped lease's worktree (REC-01).

        Returns ``None`` when the policy flag is off or the lease has no
        recorded worktree, so the caller records nothing.  Never raises:
        a reclaim failure must not undo a successful revoke.
        """
        if not lease.worktree:
            return None
        policy = self.kernel.policy().get("worktree", {}) or {}
        if not policy.get("reclaim_on_reap", False):
            return None
        try:
            from pmk import worktrees
            return worktrees.reclaim_after_capture(
                self.kernel.repo, self.kernel.state(), lease.worktree)
        except Exception as exc:                    # noqa: BLE001
            return {"worktree": str(lease.worktree), "reclaimed": False,
                    "reason": f"{type(exc).__name__}: {exc}"}

    def _reap_failed(self, info: dict, key: tuple, stage: str,
                     message: str) -> dict:
        self._reap_retry_at[key] = self.kernel.clock.monotonic() + REAP_RETRY_S
        payload = dict(info, stage=stage, error=message)
        self.kernel.record_event("LEASE_REAP_FAILED", actor=Actor.kernel(),
                                 subject=info["task"], fence=info["fence"],
                                 payload=payload)
        return dict(payload, reaped=False)

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

        reaped = self.reap_expired_leases()
        if reaped:
            result["reaped"] = reaped

        advanced = self.advance()
        result["state"] = advanced["state"]
        result["notes"].extend(advanced.get("notes", []))
        if "close_check" in advanced:
            result["close_check"] = advanced["close_check"]

        woke = self.maybe_wake()
        if woke:
            result["wake"] = woke

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
