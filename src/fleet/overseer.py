"""The Overseer runner (fleet amendment section 7.8).

The Overseer is **not** part of the app process.  It is an OpenCode session
that the Conductor starts and resumes, and it acts only through ``pmk``
commands (pilot v1 rule 13).  The authority for what it should do is
``pmk brief --role overseer``, not the session history (hypothesis H6).

The Conductor starts it **on events, never on a busy loop**.  Wake reasons:

``needs-pdd``
    The project has a plan task and no PDD.
``needs-decomposition``
    The PDD merged and the project needs task cards.
``review``
    A submission is waiting for review.
``incident``
    An incident or a queue item needs attention.
``replan``
    No READY tasks and the project is not done.
``human-message``
    The operator sent a message from the Console.
``periodic``
    Every 10 minutes, so a missed event cannot wedge the project.

Wakes are **debounced** (60 s) and **bounded per hour**, so a burst of
events cannot turn into a storm of model calls.

**Fallback.**  If OpenCode cannot run headless (spike S-O1), a thin Python
Overseer loop calls the same ``pmk`` commands through the gateway's
OpenAI-compatible endpoint.  That fallback is not implemented here because
the gateway is not required for Fleet-only operation; the runner degrades to
"the Overseer could not be started" and says so, which is honest and is
what the pilot's rules require.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from pmk.api import Kernel, KernelError

from . import order as order_mod
from . import spawn as spawn_mod
from .profiles import Profile
from .state import FleetState

#: The Overseer prompt (B2′, fleet amendment section 12.D).  It replaces
#: pilot v1's B2 for Phase 2.  Planner and decomposer behaviour is part of
#: this one prompt; there is no second Overseer persona.
OVERSEER_PROMPT = """You are the Overseer for {project}. You plan, decompose, review and write prose. You never edit anything under
.pm/, the constitution, policy, pins or Kernel code. All state changes go through `pmk`.

Each wake: run `pmk brief --role overseer`. The briefing, not this prompt, is your authority; if anything
conflicts with the constitution in your briefing, the constitution wins and you report it with `pmk incident`.

Wake reasons you may be given: needs-pdd, needs-decomposition, review, incident, replan, human-message, periodic.
- needs-pdd: claim the plan task and write docs/PDD.md using the template in docs/sources; make every goal checkable.
- needs-decomposition: create task cards with `pmk task create` (goal_ref, scope, oracle, premises, budget,
  depends_on). Keep write scopes disjoint where tasks can run in parallel. Prefer many small tasks.
- review / incident: use `pmk agent show|tail` before deciding. Use `pmk fleet` to enable, disable or cool profiles.
- replan: create only the gap tasks the failed goal oracles require. Do not rewrite finished work.
Ask the human only through `pmk queue`, with a recommended option and a safe default. Stop when the briefing
has nothing for you; the Conductor will wake you again.
"""

WAKE_REASONS = ("needs-pdd", "needs-decomposition", "review", "incident",
                "replan", "human-message", "periodic")


@dataclass
class Wake:
    """One wake of the Overseer."""

    reason: str
    at: float = 0.0
    session: str = ""
    profile: str = ""
    started: bool = False
    error: str = ""

    def to_dict(self) -> dict:
        return {"reason": self.reason, "at": self.at, "session": self.session,
                "profile": self.profile, "started": self.started,
                "error": self.error}


@dataclass
class OverseerRunner:
    """Starts and bounds the Overseer sessions."""

    kernel: Kernel
    fleet_state: FleetState
    debounce_s: float = 60.0
    per_hour: int = 6
    periodic_s: float = 600.0
    last_wake_at: float = 0.0
    wakes_this_hour: int = 0
    hour_started: float = 0.0
    wakes: list = field(default_factory=list)
    session: str = ""
    pending_reason: str = ""

    # ------------------------------------------------------------------
    def ordered_profiles(self) -> list[Profile]:
        """The Overseer's ordered profile list.

        Ordered strongest-first: plan quality is the largest unknown in
        the whole system, so the best available model goes first.
        """
        from pmk.policy import load_agents
        from .profiles import Profile as P
        agents = load_agents(self.kernel.repo)
        wanted = list(agents["overseer"].get("profiles") or [])
        by_id = {p.get("id"): p for p in agents["profiles"]}
        out = []
        for profile_id in wanted:
            if profile_id in by_id:
                out.append(P.from_dict(by_id[profile_id]))
        return out

    def should_wake(self, reason: str, *, now: float | None = None) -> tuple[bool, str]:
        """Is this wake allowed?  Returns ``(allowed, why)``."""
        now = time.time() if now is None else now

        if now - self.hour_started >= 3600:
            self.hour_started = now
            self.wakes_this_hour = 0

        if self.wakes_this_hour >= self.per_hour:
            return False, f"hourly bound reached ({self.wakes_this_hour}/{self.per_hour})"

        if self.last_wake_at and (now - self.last_wake_at) < self.debounce_s:
            return False, (f"debounced ({int(now - self.last_wake_at)}s "
                           f"of {int(self.debounce_s)}s)")

        return True, "allowed"

    def note_wake(self, reason: str, *, started: bool, profile: str = "",
                  error: str = "", now: float | None = None) -> Wake:
        now = time.time() if now is None else now
        wake = Wake(reason=reason, at=now, profile=profile, started=started,
                    error=error)
        self.wakes.append(wake)
        self.wakes_this_hour += 1
        self.last_wake_at = now
        if not self.hour_started:
            self.hour_started = now
        return wake

    # ------------------------------------------------------------------
    def prompt(self, project: str = "the project") -> str:
        return OVERSEER_PROMPT.format(project=project)

    def wake(self, reason: str, *, project: str = "the project",
             now: float | None = None) -> Wake:
        """Wake the Overseer, if the bounds allow it."""
        if reason not in WAKE_REASONS:
            raise KernelError("unknown_wake_reason", reason=reason,
                              known=list(WAKE_REASONS))
        allowed, why = self.should_wake(reason, now=now)
        if not allowed:
            wake = Wake(reason=reason, at=time.time(), started=False, error=why)
            self.wakes.append(wake)
            return wake

        profiles = self.ordered_profiles()
        if not profiles:
            wake = self.note_wake(reason, started=False,
                                  error="no Overseer profile is configured")
            self.kernel.record_event("OVERSEER_WOKEN", payload=wake.to_dict())
            return wake

        profile = profiles[0]
        state = self.fleet_state.profile(profile.id)
        if not state.enabled or state.cooling():
            wake = self.note_wake(
                reason, started=False, profile=profile.id,
                error=f"the Overseer profile {profile.id} is "
                      f"{'disabled' if not state.enabled else 'cooling'}")
            self.kernel.record_event("OVERSEER_WOKEN", payload=wake.to_dict())
            return wake

        try:
            session = self._start(profile, project)
        except (OSError, ValueError, KernelError) as exc:
            wake = self.note_wake(reason, started=False, profile=profile.id,
                                  error=f"{type(exc).__name__}: {exc}")
            self.kernel.record_event("OVERSEER_WOKEN", payload=wake.to_dict())
            return wake

        self.session = session
        wake = self.note_wake(reason, started=True, profile=profile.id)
        wake.session = session
        self.kernel.record_event("OVERSEER_WOKEN", payload=wake.to_dict())
        return wake

    def _start(self, profile: Profile, project: str) -> str:
        """Start an Overseer session and return its id (or slot reference)."""
        from .adapters import get_adapter
        from .harness import Harness

        adapter = get_adapter(profile.adapter, None)
        harness = Harness(self.kernel, self.fleet_state)
        prompt = self.prompt(project)

        # The Overseer runs in the project root, not in a lease worktree:
        # it plans, it does not build.
        slot = spawn_mod.spawn_slot(
            self.kernel.repo, task_id="overseer", profile_id=profile.id,
            adapter=adapter, profile=profile.raw or profile.to_dict(),
            prompt=prompt, worktree=self.kernel.repo.root,
            fence=0, index=0, env=harness._env(profile))
        return f"{slot.pid}" if slot.pid else "unknown"

    # ------------------------------------------------------------------
    def status(self) -> dict:
        return {
            "session": self.session,
            "last_wake_reason": self.wakes[-1].reason if self.wakes else "",
            "wakes": len(self.wakes),
            "wakes_this_hour": self.wakes_this_hour,
            "per_hour": self.per_hour,
            "debounce_s": self.debounce_s,
            "periodic_s": self.periodic_s,
            "last_wake_at": self.wakes[-1].at if self.wakes else 0,
            "profiles": [p.id for p in self.ordered_profiles()],
            "recent": [w.to_dict() for w in self.wakes[-10:]],
        }
