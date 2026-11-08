"""Rulesets: which CNA modules are active.

RULE: 2.0 (module combinations), 32 (Land Game abstract supply/air),
33 and 47 (Air Game and its Land + Air abstract rules), 48 and 58
(Logistics Game and its Land + Logistics abstract rules).

P1 ships only ``LAND_ABSTRACT``.  The other combinations are declared so
callers can name them and receive a clear refusal, rather than silently
playing a different game.  The §2.0 combination reading is recorded in
``docs/decisions/RD-0001-ruleset-combinations.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

RULE = "2.0, 32, 33, 47, 48, 58"


class RulesetError(ValueError):
    """An unknown or unavailable ruleset was requested."""


@dataclass(frozen=True)
class Ruleset:
    id: str
    name: str
    modules: tuple[str, ...]
    supply_rule: str
    air_rule: str
    sequence_rule: str
    available: bool
    status: str
    provenance: str = "rulebook 2.0; RD-0001"

    def __post_init__(self) -> None:
        if not self.id or not self.name:
            raise RulesetError("a ruleset needs an id and a name")
        if not self.modules:
            raise RulesetError("a ruleset needs at least one module")

    def active_sections(self) -> tuple[str, ...]:
        """The rule sections this combination activates, in stable order."""
        sections = [self.sequence_rule, self.supply_rule, self.air_rule]
        return tuple(dict.fromkeys(sections))

    def to_obj(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "modules": list(self.modules),
            "supply_rule": self.supply_rule,
            "air_rule": self.air_rule,
            "sequence_rule": self.sequence_rule,
            "available": self.available,
            "status": self.status,
            "provenance": self.provenance,
            "rule": RULE,
        }


LAND_ABSTRACT = Ruleset(
    id="LAND_ABSTRACT",
    name="Land Game with abstract supply and air",
    modules=("land", "abstract_supply", "abstract_air"),
    supply_rule="32",
    air_rule="32",
    sequence_rule="5.2",
    available=True,
    status="implemented",
)

LAND_AIR = Ruleset(
    id="LAND_AIR",
    name="Land Game with the Air Game",
    modules=("land", "air"),
    supply_rule="32",
    air_rule="47",
    sequence_rule="5.2/33",
    available=False,
    status="deferred",
)

LAND_LOGISTICS = Ruleset(
    id="LAND_LOGISTICS",
    name="Land Game with the Logistics Game",
    modules=("land", "logistics"),
    supply_rule="58",
    air_rule="32",
    sequence_rule="5.2/48",
    available=False,
    status="deferred",
)

FULL = Ruleset(
    id="FULL",
    name="Land, Air and Logistics Games together",
    modules=("land", "air", "logistics"),
    supply_rule="58",
    air_rule="47",
    sequence_rule="5.2/33/48",
    available=False,
    status="deferred",
)

RULESETS: Mapping[str, Ruleset] = {
    ruleset.id: ruleset
    for ruleset in (LAND_ABSTRACT, LAND_AIR, LAND_LOGISTICS, FULL)
}


def get_ruleset(ruleset_id: str) -> Ruleset:
    """Look a ruleset up by id, case-insensitively."""
    try:
        return RULESETS[str(ruleset_id).upper()]
    except KeyError as exc:
        raise RulesetError(f"unknown ruleset: {ruleset_id!r}") from exc


def require_available(ruleset_id: str) -> Ruleset:
    """Return a ruleset or refuse a combination this phase cannot play."""
    ruleset = get_ruleset(ruleset_id)
    if not ruleset.available:
        raise RulesetError(
            f"ruleset {ruleset.id!r} is {ruleset.status}; only "
            f"{', '.join(r.id for r in RULESETS.values() if r.available)} "
            "is available in this phase"
        )
    return ruleset


def available_rulesets() -> tuple[Ruleset, ...]:
    return tuple(ruleset for ruleset in RULESETS.values() if ruleset.available)
