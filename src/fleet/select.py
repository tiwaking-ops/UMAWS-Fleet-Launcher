"""Profile selection (fleet amendment section 7.4).

Which profile gets which task.  The rules are fixed and the result is
**deterministic**: the same fleet state and the same task always produce the
same choice, and the reason for the choice is logged.

1. Keep profiles that are enabled, not cooling, below ``max_concurrent``,
   below the fleet cap, and eligible for the task's type (``roles``).
2. If the task is a verification task: drop profiles whose ``family`` is
   ``unknown`` or equals the implementer's family (D-L12).
3. If the task carries ``agent_hint``, prefer matches — a hint is a
   preference, not a requirement.
4. Sort by **priority** (lower first), then **utilisation**
   (``running / max_concurrent``, lowest first), then longest idle, then
   profile id.
5. Record ``FLEET_ASSIGNED`` with the ordered candidates and the reason for
   the pick.  If nothing qualifies, the task stays READY and the Console
   shows why.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .profiles import Profile
from .state import FleetState


@dataclass
class Candidate:
    """One profile considered for a task."""

    profile: Profile
    running: int = 0
    utilization: float = 0.0
    idle_seconds: float = 0.0
    eligible: bool = True
    reason: str = ""

    def to_dict(self) -> dict:
        return {"profile": self.profile.id,
                "running": self.running,
                "utilization": round(self.utilization, 3),
                "idle_seconds": int(self.idle_seconds),
                "eligible": self.eligible,
                "reason": self.reason}


@dataclass
class Selection:
    """The outcome of a selection round."""

    chosen: Profile | None = None
    candidates: list = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "chosen": self.chosen.id if self.chosen else None,
            "reason": self.reason,
            "candidates": [c.to_dict() for c in self.candidates],
        }


def could_serve(profile: Profile, served: set[str]) -> bool:
    """Could this profile be *one of* the models that served?

    ``True`` means "not ruled out", which is deliberately the conservative
    reading.  An opaque router (``kilo-auto``) can route to anything, so it is
    never ruled out even when it does not literally list the model - that is
    the whole reason the string comparison was not enough.
    """
    if not served:
        return False
    # Anything the profile declares or may swap to.
    declared = set(profile.models) | {profile.model}
    declared.discard("")
    if declared & served:
        return True
    # An alias cannot be ruled out: we do not know what it would pick.
    for candidate in declared:
        if "/" in candidate and candidate.rsplit("/", 1)[-1].split(":")[0] in (
                "free", "auto", "best-coding", "best-reasoning", "chat",
                "fast", "cheap", "offline", "smart", "chaos"):
            return True
    return False


def select_profile(task, profiles: list[Profile], fleet_state: FleetState,
                   running_counts: dict[str, int], *,
                   fleet_cap: int = 20, total_running: int = 0,
                   implementer_family: str = "",
                   implementer_served: set[str] | None = None,
                   now: float | None = None) -> Selection:
    """Choose a profile for *task*.

    *task* needs ``id``, ``type`` and ``agent_hint``.  *running_counts*
    maps a profile id to the number of slots it currently holds.

    *implementer_served* is the set of models that actually served the work
    being verified, as recorded by the gateway (``MODEL_SERVED``).  When it is
    known it beats the family guess, because a declared family is a claim
    about a string while this is a fact about the request.
    """
    now = time.time() if now is None else now
    is_verification = task.type in ("verify", "review")

    candidates: list[Candidate] = []
    for profile in profiles:
        state = fleet_state.profile(profile.id)
        running = int(running_counts.get(profile.id, 0))

        candidate = Candidate(profile=profile, running=running)

        if not state.enabled or not profile.enabled:
            candidate.eligible = False
            candidate.reason = "disabled"
        elif state.cooling(now):
            candidate.eligible = False
            candidate.reason = f"cooling for {state.cooling_remaining(now)}s"
        elif running >= profile.max_concurrent:
            candidate.eligible = False
            candidate.reason = (f"at concurrency limit "
                                f"({running}/{profile.max_concurrent})")
        elif total_running >= fleet_cap:
            candidate.eligible = False
            candidate.reason = f"fleet cap reached ({total_running}/{fleet_cap})"
        elif not profile.eligible_for(task.type):
            candidate.eligible = False
            candidate.reason = f"not eligible for type {task.type!r}"
        elif (is_verification and implementer_served
                and could_serve(profile, implementer_served)):
            # Provenance, which outranks a declared family: this profile
            # could be a model that already served the work under review.
            candidate.eligible = False
            candidate.reason = ("provenance: could be one of "
                                f"{sorted(implementer_served)}, which "
                                "implemented this task")
        elif is_verification and (profile.family == "unknown"
                                  or profile.family == implementer_family):
            # D-L12: an unverifiable family can never be an independent
            # verifier, and neither can the author's own family.
            candidate.eligible = False
            candidate.reason = (f"family {profile.family!r} cannot verify "
                                f"(implementer family {implementer_family!r})")

        if candidate.eligible:
            candidate.utilization = (running / profile.max_concurrent
                                     if profile.max_concurrent else 1.0)
            candidate.idle_seconds = max(0.0, now - (state.last_used or 0.0))
        candidates.append(candidate)

    eligible = [c for c in candidates if c.eligible]

    # A hint is a preference, not a requirement: hinted profiles are
    # considered first, but unhinted ones are still used.
    hint = (getattr(task, "agent_hint", "") or "").strip()

    def sort_key(candidate: Candidate):
        hinted = 0 if (hint and candidate.profile.id == hint) else 1
        return (hinted,
                candidate.profile.priority,
                candidate.utilization,
                -candidate.idle_seconds,
                candidate.profile.id)

    eligible.sort(key=sort_key)
    candidates.sort(key=lambda c: (not c.eligible, sort_key(c)))

    if not eligible:
        return Selection(chosen=None, candidates=candidates,
                         reason=_no_candidate_reason(candidates))

    chosen = eligible[0]
    if hint and chosen.profile.id != hint:
        reason = (f"profile {chosen.profile.id} chosen "
                  f"(hint {hint!r} not available)")
    else:
        reason = (f"profile {chosen.profile.id} chosen by priority "
                  f"{chosen.profile.priority}, utilisation "
                  f"{chosen.utilization:.2f}")
    return Selection(chosen=chosen.profile, candidates=candidates, reason=reason)


def _no_candidate_reason(candidates: list[Candidate]) -> str:
    """Explain, in the operator's terms, why nothing qualified."""
    if not candidates:
        return "no profiles are configured"
    reasons = {}
    for candidate in candidates:
        reasons[candidate.reason or "eligible"] = \
            reasons.get(candidate.reason or "eligible", 0) + 1
    parts = ", ".join(f"{count} x {reason}"
                      for reason, count in sorted(reasons.items()))
    return f"no profile qualifies ({parts})"
