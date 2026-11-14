"""Zones of Control.

RULE: 10.0, 10.11-10.16, 10.21-10.29, 10.31-10.36

A Zone of Control is the six hexes around an eligible unit.  This module
separates the three questions the rest of the engine asks:

* **who exerts** a ZOC (10.11-10.15);
* **which hexes** are controlled, given the map's blocked hexsides and
  terrain that a unit could not enter (10.21);
* **what movement and combat must do** about it (10.22-10.29, 10.31-10.36).

The hex grid and the Terrain Effects Chart are caller-supplied: hex ids are
opaque strings and the caller passes a ``neighbours`` function.  No map or
historical data is invented here.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Callable, Iterable

RULE = "10.11-10.36"

#: A unit at this Cohesion or worse exerts no ZOC (10.14).
ZOC_COHESION_FLOOR = -26

#: A hex must hold at least this many Raw Defensive Close Assault Points
#: for its units to exert a ZOC (10.15).
MIN_RAW_DEFENSIVE = Fraction(10)

#: Entering an Enemy ZOC costs no CP (10.22).
ZOC_ENTRY_CP = Fraction(0)

#: The three-hex, three-DP penalty for a unit that can neither assault nor
#: hold off (10.36).
FORCED_RETREAT_HEXES = 3
FORCED_RETREAT_DP = 3

KINDS = frozenset({
    "combat", "artillery", "antitank", "aa", "hq", "truck_convoy",
    "informational", "aircraft", "ground_support", "warship", "engineer",
    "noncombat",
})

#: Units that never exert a ZOC (10.12, 10.13).
NO_ZOC_KINDS = frozenset({
    "aircraft", "ground_support", "warship", "informational",
})

#: Kinds that count as combat units for ZOC and the holding-off requirement.
COMBAT_KINDS = frozenset({"combat", "artillery", "antitank", "aa"})

#: Kinds that are exempt from the must-attack requirement (10.32).
ATTACK_EXEMPT_KINDS = frozenset({
    "artillery", "antitank", "aa", "hq", "engineer", "ground_support",
    "noncombat", "informational",
})

Neighbours = Callable[[str], Iterable[str]]
BlockedHexside = Callable[[str, str], bool]
CanEnter = Callable[["ZocUnit", str, str], bool]


class ZocError(ValueError):
    """A Zone of Control input is not a valid §10 position."""


def _points(value: Any, *, name: str = "points") -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise ZocError(f"{name} must be an integer or Fraction")
    result = Fraction(value)
    if result < 0:
        raise ZocError(f"{name} must not be negative")
    return result


@dataclass(frozen=True)
class ZocUnit:
    """One unit, with the facts that decide whether it exerts a ZOC."""

    unit_id: str
    side: str
    position: str
    stacking_points: Fraction = Fraction(1)
    cohesion: int = 0
    raw_defensive_close_assault: Fraction = Fraction(10)
    kind: str = "combat"
    has_attached_combat: bool = False
    pinned: bool = False
    is_gun: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.unit_id, str) or not self.unit_id.strip():
            raise ZocError("unit_id must be a non-empty string")
        if not isinstance(self.side, str) or not self.side.strip():
            raise ZocError("side must be a non-empty string")
        if not isinstance(self.position, str) or not self.position.strip():
            raise ZocError("position must be a non-empty string")
        object.__setattr__(self, "stacking_points", _points(self.stacking_points))
        object.__setattr__(self, "raw_defensive_close_assault",
                           _points(self.raw_defensive_close_assault,
                                   name="raw_defensive_close_assault"))
        if isinstance(self.cohesion, bool) or not isinstance(self.cohesion, int):
            raise ZocError("cohesion must be an integer")
        if self.kind not in KINDS:
            raise ZocError(f"unknown unit kind: {self.kind!r}")
        for name in ("has_attached_combat", "pinned", "is_gun"):
            if not isinstance(getattr(self, name), bool):
                raise ZocError(f"{name} must be a bool")


def is_combat_unit(unit: ZocUnit) -> bool:
    return unit.kind in COMBAT_KINDS


def exerts_zoc(unit: ZocUnit, hex_units: Iterable[ZocUnit]) -> bool:
    """Does *unit* exert a ZOC from its hex? (10.11-10.15)

    ``hex_units`` must include every unit in the same hex, because 10.11
    looks at the stack total and 10.15 at the stack's Raw Defensive Close
    Assault Points.
    """
    if unit.kind in NO_ZOC_KINDS:
        return False                                          # 10.12/10.13
    if unit.cohesion <= ZOC_COHESION_FLOOR:
        return False                                          # 10.14
    if unit.kind == "truck_convoy":
        return False                                          # 10.11
    if unit.kind == "hq" and not unit.has_attached_combat:
        return False                                          # 10.11
    members = tuple(hex_units)
    raw = sum((member.raw_defensive_close_assault for member in members),
              Fraction(0))
    if raw < MIN_RAW_DEFENSIVE:
        return False                                          # 10.15
    total_points = sum((member.stacking_points for member in members),
                       Fraction(0))
    return unit.stacking_points > 1 or total_points > 1        # 10.11


def exerting_units(units: Iterable[ZocUnit]) -> tuple[ZocUnit, ...]:
    """Every unit in the list that exerts a ZOC, in input order."""
    members = tuple(units)
    by_hex: dict[str, list[ZocUnit]] = {}
    for unit in members:
        by_hex.setdefault(unit.position, []).append(unit)
    return tuple(unit for unit in members
                 if exerts_zoc(unit, by_hex[unit.position]))


def zoc_map(units: Iterable[ZocUnit], *, neighbours: Neighbours,
            blocked_hexside: BlockedHexside | None = None,
            can_enter: CanEnter | None = None) -> dict[str, frozenset[str]]:
    """Map each controlled hex to the ids of the units controlling it.

    10.21 excludes All-Sea, Major River, Lake and Escarpment hexsides and
    any hex the unit could not enter; those are caller-supplied predicates.
    """
    members = tuple(units)
    by_hex: dict[str, list[ZocUnit]] = {}
    for unit in members:
        by_hex.setdefault(unit.position, []).append(unit)
    control: dict[str, set[str]] = {}
    for unit in members:
        if not exerts_zoc(unit, by_hex[unit.position]):
            continue
        for destination in neighbours(unit.position):
            if not isinstance(destination, str) or not destination:
                raise ZocError("neighbours must yield non-empty hex ids")
            if blocked_hexside and blocked_hexside(unit.position, destination):
                continue                                      # 10.21a/b
            if can_enter and not can_enter(unit, unit.position, destination):
                continue                                      # 10.21c
            control.setdefault(destination, set()).add(unit.unit_id)
    return {hex_id: frozenset(ids) for hex_id, ids in sorted(control.items())}


def enemy_controlled_hexes(units: Iterable[ZocUnit], side: str, *,
                           neighbours: Neighbours,
                           blocked_hexside: BlockedHexside | None = None,
                           can_enter: CanEnter | None = None) -> frozenset[str]:
    """Hexes an enemy ZOC controls for *side* (10.26, 10.27)."""
    members = tuple(units)
    enemy = [unit for unit in members if unit.side != side]
    control = zoc_map(enemy, neighbours=neighbours,
                      blocked_hexside=blocked_hexside, can_enter=can_enter)
    friendly_combat = {
        unit.position for unit in members
        if unit.side == side and is_combat_unit(unit)
    }
    return frozenset(hex_id for hex_id in control
                     if hex_id not in friendly_combat)         # 10.26


def mutually_controlled(first: ZocUnit, second: ZocUnit, *,
                         neighbours: Neighbours) -> bool:
    """10.27: opposing units exerting on each other are in each other's ZOC."""
    return (second.position in set(neighbours(first.position))
            and first.position in set(neighbours(second.position)))


def may_enter_enemy_zoc(unit: ZocUnit, hex_id: str, controlled: Iterable[str],
                        friendly_combat: Iterable[str] = ()) -> tuple[bool, str]:
    """Can *unit* voluntarily enter an enemy-controlled hex? (10.22, 10.29)

    Returns ``(allowed, case)``; a combat unit may always enter, at no CP
    cost (10.22).  A truck convoy or non-combat unit may not enter an
    *unoccupied* controlled hex.
    """
    controlled = frozenset(controlled)
    if hex_id not in controlled:
        return True, ""
    if hex_id in frozenset(friendly_combat):
        return True, ""                                       # 10.26
    if unit.kind == "truck_convoy":
        return False, "10.29"
    if not is_combat_unit(unit):
        return False, "10.29"
    return True, ""


def must_stop_after_entering(hex_id: str, controlled: Iterable[str]) -> bool:
    """10.23: a unit must cease movement on entering an Enemy-controlled hex."""
    return hex_id in frozenset(controlled)


def may_move_zoc_to_zoc(origin: str, destination: str,
                        controlled: Iterable[str], *,
                        advance_into: Iterable[str] = ()) -> bool:
    """10.24: no direct move from one Enemy-controlled hex to another.

    *advance_into* is the 10.24 exception: a hex vacated by an Enemy unit
    as a result of combat, Retreat Before Assault or Reaction.
    """
    controlled = frozenset(controlled)
    if destination in frozenset(advance_into):
        return True
    return not (origin in controlled and destination in controlled)


def must_disclose_zoc(could_exert: bool,
                      phasing_unit_begins_or_enters: bool) -> bool:
    """10.16: the non-phasing player must answer a ZOC question."""
    if not isinstance(could_exert, bool) or not isinstance(
            phasing_unit_begins_or_enters, bool):
        raise ZocError("10.16 inputs must be bools")
    return could_exert and phasing_unit_begins_or_enters


# ---------------------------------------------------------------------------
# ZOC combat requirements (10.31-10.36)
# ---------------------------------------------------------------------------

def combat_targets(units: Iterable[ZocUnit], side: str, *,
                   neighbours: Neighbours,
                   blocked_hexside: BlockedHexside | None = None,
                   can_enter: CanEnter | None = None) -> frozenset[str]:
    """Enemy hexes whose ZOC covers a friendly combat unit (10.31)."""
    members = tuple(units)
    enemy = [unit for unit in members if unit.side != side]
    control = zoc_map(enemy, neighbours=neighbours,
                      blocked_hexside=blocked_hexside, can_enter=can_enter)
    friendly_combat = {
        unit.position for unit in members
        if unit.side == side and is_combat_unit(unit)
    }
    positions: set[str] = set()
    for hex_id, controller_ids in control.items():
        if hex_id not in friendly_combat:
            continue
        for controller_id in controller_ids:
            unit = next(u for u in enemy if u.unit_id == controller_id)
            positions.add(unit.position)
    return frozenset(positions)


def must_attack(units: Iterable[ZocUnit], side: str, *,
                neighbours: Neighbours,
                blocked_hexside: BlockedHexside | None = None,
                can_enter: CanEnter | None = None) -> bool:
    """10.31: every covering Enemy ZOC must be attacked, bar 10.32."""
    members = tuple(units)
    friendly = [unit for unit in members if unit.side == side]
    if not friendly:
        return False
    if all(unit.pinned or unit.kind in ATTACK_EXEMPT_KINDS
           for unit in friendly):
        return False                                          # 10.32
    return bool(combat_targets(members, side, neighbours=neighbours,
                               blocked_hexside=blocked_hexside,
                               can_enter=can_enter))


def actual_barrage_strength(barrage_rating: Fraction | int,
                            toe_strength: Fraction | int) -> Fraction:
    """10.34: Actual Barrage Strength = Barrage Rating x TOE Strength + 10."""
    rating = _points(barrage_rating, name="barrage_rating")
    toe = _points(toe_strength, name="toe_strength")
    return rating * toe + 10


def holding_off_units(hex_units: Iterable[ZocUnit]) -> tuple[ZocUnit, ...]:
    """Enemy units that create the Holding Off requirement (10.34).

    Individual non-Gun Artillery, Anti-Tank or AA battalion-equivalent
    combat units; units with less than one Stacking Point and Gun units do
    not count.
    """
    return tuple(unit for unit in hex_units
                 if unit.kind in ("artillery", "antitank", "aa")
                 and not unit.is_gun
                 and unit.stacking_points >= 1)


def holding_off_required(hex_units: Iterable[ZocUnit]) -> int:
    """How many Actual Barrage Strength Points a Holding Off needs (10.34)."""
    return len(holding_off_units(hex_units))


def holding_off_satisfied(strength: Fraction | int,
                          enemy_hex_units: Iterable[ZocUnit]) -> bool:
    """10.34: at least one Actual Barrage Point per eligible enemy unit."""
    return _points(strength, name="strength") >= holding_off_required(enemy_hex_units)


def holding_off_possible(strength: Fraction | int,
                         enemy_hex_units: Iterable[ZocUnit]) -> bool:
    """10.35: if Holding Off is impossible the hex must be Close Assaulted."""
    return holding_off_satisfied(strength, enemy_hex_units)


@dataclass(frozen=True)
class HoldingOffPlan:
    """10.33: which covering hexes are held off and which must be assaulted."""

    held_off: tuple[str, ...]
    must_assault: tuple[str, ...]
    satisfied: bool

    def to_obj(self) -> dict[str, Any]:
        return {"held_off": list(self.held_off),
                "must_assault": list(self.must_assault),
                "satisfied": self.satisfied, "rule": "10.33"}


def holding_off_plan(barrages: dict[str, Fraction | int],
                     enemy_hexes: dict[str, Iterable[ZocUnit]]) -> HoldingOffPlan:
    """10.33: a Holding Off barrage can replace one Close Assault.

    *barrages* maps an enemy-held hex to the Actual Barrage Strength Points
    the Friendly player allocates to it.  Hexes without a sufficient
    barrage remain in ``must_assault``; the plan is satisfied only when no
    hex is left unaddressed.
    """
    held: list[str] = []
    assault: list[str] = []
    for hex_id in sorted(enemy_hexes):
        units = tuple(enemy_hexes[hex_id])
        strength = barrages.get(hex_id)
        if strength is not None and holding_off_satisfied(strength, units):
            held.append(hex_id)
        else:
            assault.append(hex_id)
    return HoldingOffPlan(tuple(held), tuple(assault), not assault)


@dataclass(frozen=True)
class ForcedRetreat:
    """10.36: a unit that can neither assault nor hold off must retreat."""

    hexes: int = FORCED_RETREAT_HEXES
    disorganization_points: int = FORCED_RETREAT_DP
    rule: str = "10.36"

    def to_obj(self) -> dict[str, Any]:
        return {"hexes": self.hexes,
                "disorganization_points": self.disorganization_points,
                "rule": self.rule}


def retreat_path_allowed(path: Iterable[str],
                         enemy_controlled: Iterable[str]) -> bool:
    """10.36: the forced retreat may not pass through any Enemy ZOC."""
    controlled = frozenset(enemy_controlled)
    return all(hex_id not in controlled for hex_id in path)
