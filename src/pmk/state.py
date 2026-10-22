"""Rebuilding state from the event log (pilot v1 section 9.1).

The log is the authority.  Task cards and leases are projections of it, so
this module can rebuild everything after a crash, after a torn tail, or
after the log is copied onto another machine.

Invariant I13 (*views equal projection*) is checked by comparing what
:func:`rebuild` produces with what the view files contain.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .events import Event
from .models import (ACTIVE_STATES, BLOCKED, DONE, LEASED, PROPOSED, READY,
                      REWORK, SUBMITTED, VERIFYING, INTEGRATING, VOID,
                      Lease, TaskCard, next_task_id)

#: Project lifecycle states (fleet amendment section 10).
PROJECT_STATES = ("NEW", "PLANNING", "DECOMPOSING", "RUNNING", "CLOSING",
                  "DONE", "PAUSED", "STALLED")


@dataclass
class State:
    """Everything the Kernel knows, derived from the log."""

    tasks: dict[str, TaskCard] = field(default_factory=dict)
    leases: dict[str, Lease] = field(default_factory=dict)
    project_state: str = "NEW"
    queue: list[dict] = field(default_factory=list)
    incidents: list[dict] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)

    # -- queries ----------------------------------------------------------
    def task(self, task_id: str) -> TaskCard | None:
        return self.tasks.get(task_id)

    def task_list(self, state: str | None = None) -> list[TaskCard]:
        items = sorted(self.tasks.values(), key=lambda t: t.id)
        if state:
            items = [t for t in items if t.state == state]
        return items

    def active_leases(self) -> dict[str, Lease]:
        return {tid: lease for tid, lease in self.leases.items()
                if lease.task_id in self.tasks
                and self.tasks[lease.task_id].state in ACTIVE_STATES}

    def ready_tasks(self) -> list[TaskCard]:
        """READY tasks whose dependencies are all DONE.

        A task whose dependency is not done is not ready, even if the
        scheduler put it in READY.  Dependency order is a correctness
        property, not a scheduling hint.
        """
        out = []
        for task in self.task_list(READY):
            unmet = [d for d in task.depends_on
                     if d in self.tasks and self.tasks[d].state != DONE]
            if not unmet:
                out.append(task)
        return out

    def next_task_id(self) -> str:
        return next_task_id(self.tasks.keys())

    def counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for task in self.tasks.values():
            counts[task.state] = counts.get(task.state, 0) + 1
        return counts

    def conservation_ok(self) -> tuple[bool, str]:
        """Invariant I3: every task is in exactly one state.

        A task that appears twice, or in no state, is a conservation breach.
        """
        for task_id, task in self.tasks.items():
            if not task.state:
                return False, f"{task_id} has no state"
            if task.state not in (
                    PROPOSED, READY, LEASED, SUBMITTED, VERIFYING, INTEGRATING,
                    DONE, REWORK, BLOCKED, VOID):
                return False, f"{task_id} is in unknown state {task.state!r}"
        return True, ""


def rebuild(events: list[Event]) -> State:
    """Fold the event log into a :class:`State`."""
    state = State(events=list(events))

    for event in events:
        etype = event.type
        payload = event.payload or {}
        subject = event.subject

        if etype == "TASK_CREATED":
            card = TaskCard.from_obj(payload.get("card") or {})
            if not card.id:
                card.id = subject or ""
            state.tasks[card.id] = card

        elif etype == "TASK_ADMITTED":
            card = state.tasks.get(subject or "")
            if card:
                card.state = READY

        elif etype == "TASK_READY":
            card = state.tasks.get(subject or "")
            if card:
                card.state = READY
                card.block_reason = ""

        elif etype == "TASK_BLOCKED":
            card = state.tasks.get(subject or "")
            if card:
                card.state = BLOCKED
                card.block_reason = str(payload.get("reason", ""))

        elif etype == "TASK_VOIDED":
            card = state.tasks.get(subject or "")
            if card:
                card.state = VOID
                card.block_reason = str(payload.get("reason", ""))

        elif etype == "TASK_REWORKED":
            card = state.tasks.get(subject or "")
            if card:
                card.state = REWORK

        elif etype == "CLAIMED":
            card = state.tasks.get(subject or "")
            if card:
                card.state = LEASED
                card.attempt = int(payload.get("attempt", card.attempt + 1))
                card.fence = int(payload.get("fence", card.fence))
            lease = Lease.from_obj(payload.get("lease") or {})
            lease.task_id = subject or lease.task_id
            lease.fence = int(payload.get("fence", lease.fence))
            state.leases[lease.task_id] = lease

        elif etype == "RENEWED":
            lease = state.leases.get(subject or "")
            if lease:
                lease.renewed_at = str(payload.get("ts", lease.renewed_at))
                lease.expires_at = str(payload.get("expires_at", lease.expires_at))
                if payload.get("digest"):
                    lease.failure_history = lease.failure_history  # unchanged
            card = state.tasks.get(subject or "")
            if card:
                card.state = LEASED

        elif etype == "REVOKED":
            card = state.tasks.get(subject or "")
            if card:
                # Revocation bumps the fence and returns the task to READY
                # (or BLOCKED once attempts are exhausted).
                card.fence = int(payload.get("new_fence", card.fence + 1))
                if card.attempt >= int(card.attempts.get("max", 3)):
                    card.state = BLOCKED
                    card.block_reason = str(payload.get("reason", "attempts exhausted"))
                else:
                    card.state = READY
            state.leases.pop(subject or "", None)

        elif etype == "SUBMITTED":
            card = state.tasks.get(subject or "")
            if card:
                card.state = SUBMITTED
            lease = state.leases.get(subject or "")
            if lease:
                lease.pid = payload.get("pid", lease.pid)
                lease.session = str(payload.get("session", lease.session))

        elif etype == "VERIFIED":
            card = state.tasks.get(subject or "")
            if card:
                card.state = VERIFYING if payload.get("ok") else REWORK
            lease = state.leases.get(subject or "")
            if lease:
                lease.last_failure_class = str(payload.get("class", ""))

        elif etype == "INTEGRATING":
            card = state.tasks.get(subject or "")
            if card:
                card.state = INTEGRATING

        elif etype == "INTEGRATED":
            card = state.tasks.get(subject or "")
            if card:
                card.state = DONE

        elif etype == "QUARANTINED":
            lease = state.leases.get(subject or "")
            if lease:
                lease.last_failure_class = str(payload.get("class", ""))

        elif etype == "PREMISE_REFUTED":
            card = state.tasks.get(subject or "")
            if card:
                card.state = VOID
                card.block_reason = str(payload.get("reason", "premise refuted"))

        elif etype == "AGENT_FAILED":
            lease = state.leases.get(subject or "")
            if lease:
                lease.restart_count = int(payload.get("restart_count",
                                                      lease.restart_count))
                lease.last_failure_class = str(payload.get("class", ""))
                lease.failure_history.append({
                    "class": lease.last_failure_class,
                    "ts": event.ts,
                    "detail": str(payload.get("detail", "")),
                })

        elif etype == "AGENT_RESUMED":
            lease = state.leases.get(subject or "")
            if lease:
                lease.session = str(payload.get("session", lease.session))
                lease.restart_count = int(payload.get("restart_count",
                                                      lease.restart_count))

        elif etype == "PROJECT_STATE":
            state.project_state = str(payload.get("state", state.project_state))

        elif etype == "QUEUE_ITEM":
            state.queue.append({
                "id": str(payload.get("id", "")),
                "topic": str(payload.get("topic", "")),
                "options": payload.get("options") or [],
                "recommended": str(payload.get("recommended", "")),
                "safe_default": str(payload.get("safe_default", "")),
                "class_k": bool(payload.get("class_k", False)),
                "state": "open",
                "created": event.ts,
            })

        elif etype == "QUEUE_DECIDED":
            item_id = str(payload.get("id", ""))
            for item in state.queue:
                if item["id"] == item_id:
                    item["state"] = "decided"
                    item["choice"] = str(payload.get("choice", ""))
                    item["decided_at"] = event.ts

        elif etype == "INCIDENT":
            state.incidents.append({
                "subject": subject,
                "message": str(payload.get("message", "")),
                "severity": str(payload.get("severity", "warn")),
                "ts": event.ts,
            })

    return state
