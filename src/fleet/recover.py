"""The recovery ladder (fleet amendment section 7.6).

When an agent is exhausted or fails, the Dispatcher recovers automatically:
it resumes the session on a different model, or reassigns the task.

===========  ==========================================================
Step         Action
===========  ==========================================================
L0           Retry the same profile and session after 30 s, 2 min, 10 min
             (``NETWORK`` only, first occurrences).  Fence unchanged.
L1           Select the next profile and **resume the session** on it with
             a short continuation prompt.  Fence unchanged.
L2           As L1, but the adapter cannot resume: start a **fresh session**
             in the **same worktree** on the next profile, with a handoff
             note.  Fence unchanged.
L3           ``max_restarts_per_task`` reached, or no profile qualifies for
             ``no_profile_minutes``: revoke the lease, bump the fence,
             quarantine the worktree, return the task to READY.  Fence
             **bumped**.
L4           ``attempts.max`` reached: task to BLOCKED and a queue item for
             the Overseer.
===========  ==========================================================

The fence is unchanged for L0–L2 because the **harness owns the lease**.  It
only changes when the harness gives up (D-L8).

Profile state changes (fleet-wide, D-L13):

* ``QUOTA`` — cool the profile: 1 hour by default, doubling after each
  failed probe, up to 24 hours.  The first use after a cooldown is a
  **probe**; a failed probe doubles the cooldown.
* ``AUTH`` and ``MODEL_GONE`` — disable the profile until the human
  re-enables it, and raise a queue item whose safe default is "stay
  disabled".
* ``NETWORK`` — no penalty at first.  If three or more **distinct
  providers** report ``NETWORK`` within two minutes, dispatch is paused
  (a circuit breaker) until a probe succeeds.
* ``UNKNOWN`` — retry once on the same profile; two in a row within ten
  minutes cool it for fifteen minutes.
* ``STALL`` — kill the process tree; two stalls on one profile within an
  hour cool it for thirty minutes.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from . import classify as classes
from .state import FleetState

L0 = "L0"
L1 = "L1"
L2 = "L2"
L3 = "L3"
L4 = "L4"


@dataclass
class RecoveryContext:
    """Everything the ladder needs to decide."""

    failure_class: str
    profile_id: str = ""
    adapter_supports_resume: bool = False
    adapter_supports_model_swap: bool = False
    restart_count: int = 0
    max_restarts: int = 5
    attempts_max: int = 3
    attempt: int = 1
    network_retries: int = 0
    unknown_retries: int = 0
    previous_profiles: list = field(default_factory=list)
    now: float = 0.0

    @property
    def can_resume(self) -> bool:
        return self.adapter_supports_resume


@dataclass
class Decision:
    """What the ladder decided to do."""

    step: str
    action: str                    # retry | resume | fresh | revoke | block
    reason: str = ""
    delay_seconds: float = 0.0
    profile_id: str = ""
    cooldown_seconds: float = 0.0
    disable_profile: bool = False
    pause_dispatch: bool = False
    queue_item: bool = False

    def to_dict(self) -> dict:
        return {
            "step": self.step, "action": self.action, "reason": self.reason,
            "delay_seconds": self.delay_seconds,
            "profile_id": self.profile_id,
            "cooldown_seconds": self.cooldown_seconds,
            "disable_profile": self.disable_profile,
            "pause_dispatch": self.pause_dispatch,
            "queue_item": self.queue_item,
        }


def decide(context: RecoveryContext, *,
           network_retry_delays: list | None = None,
           max_restarts: int = 5, attempts_max: int = 3) -> Decision:
    """Choose the next step of the ladder.

    The order of the checks matters.  L3 and L4 are terminal and must be
    checked before the recoverable steps, otherwise a task that has already
    exhausted its restarts would be retried once more.
    """
    network_retry_delays = network_retry_delays or [30, 120, 600]
    max_restarts = context.max_restarts or max_restarts
    attempts_max = context.attempts_max or attempts_max

    # -- L4: the task has run out of attempts ---------------------------
    if context.attempt >= attempts_max:
        return Decision(L4, "block",
                        reason=f"attempts exhausted ({context.attempt}/"
                               f"{attempts_max})",
                        queue_item=True)

    # -- L3: the task has run out of restarts --------------------------
    if context.restart_count >= max_restarts:
        return Decision(L3, "revoke",
                        reason=f"max_restarts_per_task reached "
                               f"({context.restart_count}/{max_restarts})")

    failure = context.failure_class

    # -- L0: a transient network problem -------------------------------
    if failure == classes.NETWORK and context.network_retries < len(network_retry_delays):
        delay = float(network_retry_delays[context.network_retries])
        return Decision(L0, "retry",
                        reason=f"network failure, retry {context.network_retries + 1}"
                               f"/{len(network_retry_delays)}",
                        delay_seconds=delay, profile_id=context.profile_id)

    # -- L1: resume the session on the next profile --------------------
    if context.can_resume:
        return Decision(L1, "resume",
                        reason=f"{failure}: resume the session on the next profile",
                        profile_id=context.profile_id)

    # -- L2: fresh session in the same worktree with a handoff note ----
    if failure in (classes.QUOTA, classes.AUTH, classes.MODEL_GONE,
                   classes.NETWORK, classes.STALL, classes.UNKNOWN,
                   classes.CRASH):
        return Decision(L2, "fresh",
                        reason=f"{failure}: the adapter cannot resume, so start a "
                               f"fresh session with a handoff note",
                        profile_id=context.profile_id)

    # -- unknown failure class: treat it as UNKNOWN ---------------------
    return Decision(L2, "fresh",
                    reason=f"{failure}: unrecognised failure, start fresh",
                    profile_id=context.profile_id)


# ---------------------------------------------------------------------------
# Profile penalties
# ---------------------------------------------------------------------------

@dataclass
class PenaltyResult:
    """What a failure did to the profile's fleet-wide state."""

    cooldown_seconds: float = 0.0
    disabled: bool = False
    pause_dispatch: bool = False
    queue_item: bool = False
    probe_pending: bool = False
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "cooldown_seconds": self.cooldown_seconds,
            "disabled": self.disabled,
            "pause_dispatch": self.pause_dispatch,
            "queue_item": self.queue_item,
            "probe_pending": self.probe_pending,
            "reason": self.reason,
        }


def apply_penalty(fleet_state: FleetState, profile_id: str,
                  failure_class: str, *, policy: dict | None = None,
                  provider: str = "", now: float | None = None) -> PenaltyResult:
    """Apply the fleet-wide consequence of a failure to one profile."""
    policy = policy or {}
    recovery = policy.get("recovery", {}) or {}
    now = time.time() if now is None else now
    result = PenaltyResult()

    state = fleet_state.profile(profile_id)
    fleet_state.record_failure(profile_id, failure_class, provider)

    if failure_class == classes.QUOTA:
        base = float(recovery.get("quota_cooldown_s", 3600))
        maximum = float(recovery.get("quota_cooldown_max_s", 86400))
        # Double after each failed probe, up to the ceiling.
        cooldown = min(base * (2 ** max(0, state.cooldown_count)), maximum)
        fleet_state.cool(profile_id, cooldown,
                         note=f"quota exhausted ({failure_class})")
        result.cooldown_seconds = cooldown
        result.probe_pending = True
        result.reason = f"quota exhausted: cooling for {int(cooldown)}s"

    elif failure_class in (classes.AUTH, classes.MODEL_GONE):
        fleet_state.disable(profile_id, note=f"{failure_class} failure")
        result.disabled = True
        result.queue_item = True
        result.reason = f"{failure_class}: profile disabled until the human re-enables it"

    elif failure_class == classes.NETWORK:
        window = float(recovery.get("network_circuit_breaker_window_s", 120))
        threshold = int(recovery.get("network_circuit_breaker_providers", 3))
        recent = [p for p in fleet_state.network_failures
                  if p and (now - state.last_failure_at) <= window]
        distinct = set(recent)
        if provider:
            distinct.add(provider)
        if len(distinct) >= threshold:
            fleet_state.dispatch_paused = True
            fleet_state.pause_reason = (
                f"circuit breaker: {len(distinct)} providers reported network "
                f"failure within {int(window)}s")
            fleet_state.paused_at = now
            result.pause_dispatch = True
            result.reason = fleet_state.pause_reason
        else:
            result.reason = "network failure: no penalty on the first failures"

    elif failure_class == classes.UNKNOWN:
        after = int(recovery.get("unknown_cooldown_after", 2))
        window = float(recovery.get("unknown_cooldown_window_s", 600))
        cooldown = float(recovery.get("unknown_cooldown_s", 900))
        recent = state.failure_counts.get(classes.UNKNOWN, 0)
        if recent >= after:
            fleet_state.cool(profile_id, cooldown,
                             note="repeated unknown failures")
            result.cooldown_seconds = cooldown
            result.reason = (f"{recent} unknown failures within "
                             f"{int(window)}s: cooling for {int(cooldown)}s")
        else:
            result.reason = "unknown failure: retry once on the same profile"

    elif failure_class == classes.STALL:
        after = int(recovery.get("stall_after", 2))
        cooldown = float(recovery.get("stall_cooldown_s", 1800))
        stalls = state.failure_counts.get(classes.STALL, 0)
        if stalls >= after:
            fleet_state.cool(profile_id, cooldown, note="repeated stalls")
            result.cooldown_seconds = cooldown
            result.reason = (f"{stalls} stalls: cooling for {int(cooldown)}s")
        else:
            result.reason = "stall: the process tree was killed"

    fleet_state.save()
    return result
