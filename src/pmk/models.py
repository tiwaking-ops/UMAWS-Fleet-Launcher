"""Task cards, leases, and the state machine (pilot v1 section 9).

These are *projections*: the event log is the authority, and everything here
can be rebuilt from it (invariant I13, "views equal projection").
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

# ---------------------------------------------------------------------------
# Task states (pilot v1 section 9.4)
# ---------------------------------------------------------------------------

PROPOSED = "PROPOSED"
READY = "READY"
LEASED = "LEASED"
SUBMITTED = "SUBMITTED"
VERIFYING = "VERIFYING"
INTEGRATING = "INTEGRATING"
DONE = "DONE"
REWORK = "REWORK"
BLOCKED = "BLOCKED"
VOID = "VOID"

ALL_STATES = (PROPOSED, READY, LEASED, SUBMITTED, VERIFYING, INTEGRATING,
              DONE, REWORK, BLOCKED, VOID)

#: States in which a task is still moving and holds a lease.
ACTIVE_STATES = (LEASED, SUBMITTED, VERIFYING, INTEGRATING)

#: States that count as finished for conservation purposes (I3).
TERMINAL_STATES = (DONE, VOID)

#: Legal transitions.  Anything else is a bug and is refused.
TRANSITIONS: dict[str, set[str]] = {
    PROPOSED: {READY, BLOCKED, VOID},
    READY: {LEASED, BLOCKED, VOID, PROPOSED},
    LEASED: {SUBMITTED, READY, BLOCKED, VOID, REWORK},
    SUBMITTED: {VERIFYING, REWORK, READY, BLOCKED, VOID},
    VERIFYING: {INTEGRATING, REWORK, READY, BLOCKED, VOID},
    INTEGRATING: {DONE, REWORK, READY, BLOCKED, VOID},
    REWORK: {READY, LEASED, BLOCKED, VOID},
    BLOCKED: {READY, VOID, PROPOSED},
    DONE: set(),
    VOID: set(),
}

#: The task types the Fleet knows how to dispatch.
TASK_TYPES = ("implement", "review", "verify", "plan", "maintain", "research")


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, set())


# ---------------------------------------------------------------------------
# Task card
# ---------------------------------------------------------------------------

@dataclass
class TaskCard:
    """A task card (pilot v1 section 9.2)."""

    id: str
    title: str
    type: str = "implement"
    goal_ref: str = ""
    risk_floor: str = "R2"
    scope: dict = field(default_factory=lambda: {"write": [], "read": []})
    acceptance: dict = field(default_factory=lambda: {"oracles": [],
                                                       "evidence_required": []})
    premises: list = field(default_factory=list)
    budget: dict = field(default_factory=lambda: {"tokens": 0, "wall_min": 0})
    depends_on: list = field(default_factory=list)
    attempts: dict = field(default_factory=lambda: {"max": 3})
    created_by: dict = field(default_factory=lambda: {"kind": "overseer"})
    priority: int = 100
    agent_hint: str = ""
    state: str = PROPOSED
    attempt: int = 0
    fence: int = 0
    block_reason: str = ""
    stop_conditions: list = field(default_factory=list)

    # -- admission --------------------------------------------------------
    def admission_errors(self) -> list[str]:
        """Why this task may not become READY (pilot v1 section 9.1).

        A task is admitted only if it has a goal reference, a declared write
        scope, at least one oracle, and a budget.  A task without an oracle
        cannot be verified, and the pilot's rule is that oracles decide.
        """
        problems: list[str] = []
        if not self.goal_ref:
            problems.append("goal_ref is required")
        if not self.scope.get("write"):
            problems.append("scope.write must not be empty")
        if not self.acceptance.get("oracles"):
            problems.append("at least one acceptance oracle is required")
        if not self.budget:
            problems.append("budget is required")
        return problems

    @property
    def write_scope(self) -> list[str]:
        return list(self.scope.get("write") or [])

    @property
    def read_scope(self) -> list[str]:
        return list(self.scope.get("read") or [])

    @property
    def oracles(self) -> list[str]:
        return list(self.acceptance.get("oracles") or [])

    @property
    def roles(self) -> list[str]:
        """Task types this card is eligible for.

        A card's ``type`` is the role it needs.  The Fleet matches a
        profile's ``roles`` list against this (fleet amendment section 7.4).
        """
        return [self.type]

    # -- serialisation ----------------------------------------------------
    def to_obj(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "goal_ref": self.goal_ref,
            "risk_floor": self.risk_floor,
            "scope": self.scope,
            "acceptance": self.acceptance,
            "premises": self.premises,
            "budget": self.budget,
            "depends_on": self.depends_on,
            "attempts": self.attempts,
            "created_by": self.created_by,
            "priority": self.priority,
            "agent_hint": self.agent_hint,
            "state": self.state,
            "attempt": self.attempt,
            "fence": self.fence,
            "block_reason": self.block_reason,
            "stop_conditions": self.stop_conditions,
        }

    @classmethod
    def from_obj(cls, obj: dict) -> "TaskCard":
        return cls(
            id=str(obj["id"]),
            title=str(obj.get("title", "")),
            type=str(obj.get("type", "implement")),
            goal_ref=str(obj.get("goal_ref", "")),
            risk_floor=str(obj.get("risk_floor", "R2")),
            scope=obj.get("scope") or {"write": [], "read": []},
            acceptance=obj.get("acceptance") or {"oracles": [], "evidence_required": []},
            premises=list(obj.get("premises") or []),
            budget=obj.get("budget") or {"tokens": 0, "wall_min": 0},
            depends_on=list(obj.get("depends_on") or []),
            attempts=obj.get("attempts") or {"max": 3},
            created_by=obj.get("created_by") or {"kind": "overseer"},
            priority=int(obj.get("priority", 100)),
            agent_hint=str(obj.get("agent_hint", "")),
            state=str(obj.get("state", PROPOSED)),
            attempt=int(obj.get("attempt", 0)),
            fence=int(obj.get("fence", 0)),
            block_reason=str(obj.get("block_reason", "")),
            stop_conditions=list(obj.get("stop_conditions") or []),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_obj(), indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Scope overlap (fleet amendment D-L6)
# ---------------------------------------------------------------------------

def _normalise(path: str) -> str:
    """Normalise a scope path for comparison.

    Scopes are repo-relative.  Comparison is done on ``/``-separated,
    case-folded paths so that ``src/pmk`` and ``src\\pmk`` compare equal.
    """
    text = str(path).strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text.strip("/").casefold()


def scope_overlaps(left: Iterable[str], right: Iterable[str]) -> list[tuple[str, str]]:
    """Return the pairs of paths that overlap between two write scopes.

    Two paths overlap when one is a prefix of the other (path-component
    wise).  ``src/pmk`` overlaps ``src/pmk/events.py``; ``src/pmk`` does not
    overlap ``src/pmkx``.
    """
    left_norm = [(p, _normalise(p)) for p in left]
    right_norm = [(p, _normalise(p)) for p in right]
    hits: list[tuple[str, str]] = []
    for l_raw, l_norm in left_norm:
        for r_raw, r_norm in right_norm:
            if not l_norm or not r_norm:
                continue
            if l_norm == r_norm:
                hits.append((l_raw, r_raw))
                continue
            l_parts = l_norm.split("/")
            r_parts = r_norm.split("/")
            shorter, longer = sorted((l_parts, r_parts), key=len)
            if len(shorter) < len(longer) and longer[:len(shorter)] == shorter:
                hits.append((l_raw, r_raw))
    return hits


# ---------------------------------------------------------------------------
# Lease
# ---------------------------------------------------------------------------

@dataclass
class Lease:
    """A lease over a task, with a fencing token (pilot v1 section 9)."""

    task_id: str
    fence: int
    holder: str = ""                 # profile id
    agent: str = ""                  # adapter name
    role: str = ""
    session: str = ""
    granted_at: str = ""
    renewed_at: str = ""
    expires_at: str = ""
    pid: int | None = None
    creation_time: int | None = None
    worktree: str = ""
    restart_count: int = 0
    failure_history: list = field(default_factory=list)
    last_failure_class: str = ""
    attempt: int = 1

    def to_obj(self) -> dict:
        return {
            "task_id": self.task_id,
            "fence": self.fence,
            "holder": self.holder,
            "agent": self.agent,
            "role": self.role,
            "session": self.session,
            "granted_at": self.granted_at,
            "renewed_at": self.renewed_at,
            "expires_at": self.expires_at,
            "pid": self.pid,
            "creation_time": self.creation_time,
            "worktree": self.worktree,
            "restart_count": self.restart_count,
            "failure_history": self.failure_history,
            "last_failure_class": self.last_failure_class,
            "attempt": self.attempt,
        }

    @classmethod
    def from_obj(cls, obj: dict) -> "Lease":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in obj.items() if k in known})


def next_task_id(existing: Iterable[str]) -> str:
    """Allocate the next task id.

    Ids are ``T-####`` and are allocated from the highest existing id, so
    an id is never reused and never collides with one that was voided.
    """
    highest = 0
    for task_id in existing:
        match = re.fullmatch(r"T-(\d+)", str(task_id))
        if match:
            highest = max(highest, int(match.group(1)))
    return f"T-{highest + 1:04d}"
