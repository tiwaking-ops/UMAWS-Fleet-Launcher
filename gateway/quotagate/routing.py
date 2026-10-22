"""Routing strategies (QuotaGate v1.1 section 3).

Four strategies, all **deterministic** given the ledger state and the clock:

``priority``
    The order the combo lists them in.
``headroom``
    The one with the most remaining quota.
``use-it-or-lose-it``
    The one with the **least** remaining quota — the default for free
    combos, where a quota that is not used is a quota that is lost.
``round-robin``
    Rotate through the eligible deployments.

The gateway chooses **which concrete deployment can take the call now**.
It does not choose which *class* of model a task deserves: that is the
Kernel's decision (QuotaGate v1.1 section 6).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import Combo, Deployment, GatewayConfig
from .engine import QuotaEngine

PRIORITY = "priority"
HEADROOM = "headroom"
USE_IT_OR_LOSE_IT = "use-it-or-lose-it"
ROUND_ROBIN = "round-robin"

STRATEGIES = (PRIORITY, HEADROOM, USE_IT_OR_LOSE_IT, ROUND_ROBIN)


@dataclass
class Candidate:
    deployment: Deployment
    eligible: bool = True
    reason: str = ""
    remaining: float = 0.0
    index: int = 0

    def to_dict(self) -> dict:
        return {"deployment": self.deployment.id, "eligible": self.eligible,
                "reason": self.reason, "remaining": self.remaining,
                "index": self.index}


@dataclass
class Route:
    """The outcome of a routing decision."""

    chosen: Deployment | None = None
    candidates: list = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict:
        return {"chosen": self.chosen.id if self.chosen else None,
                "reason": self.reason,
                "candidates": [c.to_dict() for c in self.candidates]}


def _remaining(engine: QuotaEngine, deployment: Deployment) -> float:
    """A single number for "how much room is left", for comparison."""
    total = 0.0
    for metric in ("requests", "tokens"):
        for rule, _key in engine.applicable(deployment, metric):
            used = engine.used(rule, deployment)
            total += max(0, rule.limit - used)
    return total


def route(engine: QuotaEngine, config: GatewayConfig, combo: Combo, *,
          exclude_families: tuple = (), data_class: str = "",
          strategy: str = "") -> Route:
    """Choose a deployment for one request.

    *exclude_families* implements verifier independence: a deployment from
    an excluded family is never eligible, and there is **no fallback into
    it**.  If nothing else is eligible, the answer is "nothing", not "the
    excluded family" (QuotaGate v1.1 section 7.2 rule 1).
    """
    strategy = strategy or combo.strategy or config.strategy
    candidates: list[Candidate] = []

    for index, deployment in enumerate(config.deployments_in_combo(combo)):
        candidate = Candidate(deployment=deployment, index=index)

        if deployment.family in exclude_families:
            candidate.eligible = False
            candidate.reason = (f"family {deployment.family!r} is excluded "
                                f"(verifier independence)")
        elif data_class and deployment.data_class != data_class:
            candidate.eligible = False
            candidate.reason = (f"data class {deployment.data_class!r} does "
                                f"not match {data_class!r}")
        else:
            usable, reason = engine.is_usable(deployment)
            candidate.eligible = usable
            candidate.reason = reason
            candidate.remaining = _remaining(engine, deployment)

        candidates.append(candidate)

    eligible = [c for c in candidates if c.eligible]
    if not eligible:
        return Route(chosen=None, candidates=candidates,
                     reason=_no_route_reason(candidates))

    if strategy == HEADROOM:
        eligible.sort(key=lambda c: (-c.remaining, c.index))
    elif strategy == USE_IT_OR_LOSE_IT:
        eligible.sort(key=lambda c: (c.remaining, c.index))
    elif strategy == ROUND_ROBIN:
        eligible.sort(key=lambda c: ((c.index + engine.now()) % max(1, len(eligible)), c.index))
    else:                                    # priority
        eligible.sort(key=lambda c: c.index)

    chosen = eligible[0]
    return Route(chosen=chosen.deployment, candidates=candidates,
                 reason=f"strategy {strategy}, chose {chosen.deployment.id}")


def _no_route_reason(candidates: list[Candidate]) -> str:
    if not candidates:
        return "the combo has no known deployments"
    counts: dict[str, int] = {}
    for candidate in candidates:
        key = candidate.reason or "eligible"
        counts[key] = counts.get(key, 0) + 1
    return "no eligible deployment (" + ", ".join(
        f"{count} x {reason}" for reason, count in sorted(counts.items())) + ")"
