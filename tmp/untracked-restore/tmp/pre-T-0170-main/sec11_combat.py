"""Combat: framework, barrage, retreat before assault, anti-armor, close assault.

RULE: 11.11-11.38, 12.11-12.55, 13.21-13.28, 14.11-14.55, 15.11-15.96

Combat in CNA is a fixed pipeline (11.0): gun positions, secret barrage plot,
retreat before assault, force assignment, anti-armor fire, then close assault.
:data:`COMBAT_STAGES` records that order so a caller cannot invent another one.

Three things are deliberately *not* in this module, because they are R-04 data:

* the Artillery Barrage Table (12.6);
* the Anti-Armor Combat Results Table (14.6);
* the Close Assault Combat Results Table and the Prisoners Captured Table
  (15.79, 15.89).

The caller supplies each table.  The tables used by the tests are explicitly
synthetic and are never presented as historical values.  Everything the rules
state numerically is implemented here: the Actual Strength formula (11.32),
the CP costs (11.21-11.27), the barrage column shifts (12.33-12.34), the
anti-armor Damage Point arithmetic (14.41-14.48) and the Close Assault
Differential adjustments (15.27-15.64).

Units are caller-supplied records: ratings and TOE Strength Points come from
the OA sheets (R-06), never from this module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Callable, Iterable, Mapping, Sequence

from cna.rules.sec08_movement import CONTACT_BREAK_OFF_CP, ENGAGED_BREAK_OFF_CP

RULE = "11.11-11.38, 12.11-12.55, 13.21-13.28, 14.11-14.55, 15.11-15.96"

#: The Combat Segment stages, in the order 11.0 fixes them.
COMBAT_STAGES = ("position", "barrage", "retreat_before_assault",
                 "force_assignment", "anti_armor", "close_assault")

#: 11.21-11.23 combat CP costs.
CP_PHASING_ATTACK = 5
CP_PHASING_PROBE = 2
CP_PHASING_BARRAGED = 3
CP_NON_PHASING_ATTACK = 3
CP_NON_PHASING_PROBE = 2
CP_NON_PHASING_ROUTED = 1

#: 11.24: no unit may exceed this in one Combat Segment.
SEGMENT_CP_CAP = {"phasing": 5, "non_phasing": 3}

#: 13.1: a unit at this Cohesion or worse may not Retreat Before Assault.
COLLAPSE_AT = -26

#: 15.88: a defending unit at this Cohesion or worse surrenders.
SURRENDER_AT = -17

#: 3.22 target classes used by the Barrage and Anti-Armor tables.
GUN = "gun"
ARMOR = "armor"
INFANTRY = "infantry"
TARGET_CLASSES = (GUN, ARMOR, INFANTRY)

#: The distinct "trucks" section of the Artillery Barrage Table (12.46).
TRUCKS = "trucks"

#: 12.11 artillery positions.
FORWARD = "forward"
BACK = "back"
POSITIONS = (FORWARD, BACK)

#: 12.51 facilities a barrage may be directed against.
FACILITIES = ("major_city", "fortification", "road", "railroad",
              "supply_dump", "air_facility")

#: 15.77: the Overrun section starts at this Assault Differential column.
OVERRUN_COLUMN = 11

#: 15.25: a close assault committing less than this share is a Probe.
PROBE_SHARE = Fraction(1, 2)

#: 15.96: a Probe defended at worse than this uses no CP.
PROBE_DEFENDER_FLOOR = -3

#: 15.87: losses at or above this percentage earn three Disorganization Points.
DISORGANIZATION_LOSS_PERCENT = 30
DISORGANIZATION_POINTS = 3

#: 15.29: a defender that allocates nothing retreats and is disorganized.
EMPTY_DEFENCE_HEXES = 3
EMPTY_DEFENCE_DP = 3

#: 15.4: the ceiling on the Combined Arms reduction.
COMBINED_ARMS_MAX = 4

#: Counter kinds that matter to target selection (12.22).
KINDS = frozenset({
    "combat", "hq", "truck", "sgsu", "warship", "dummy_tank", "engineer",
    "informational",
})

#: 12.22: counters that are never Barrage targets.
NON_TARGET_KINDS = frozenset({"truck", "sgsu", "informational"})

#: 15.53: formation levels used by the Organizational Size table.
LEVEL_RANK = {"company": 0, "battalion": 1, "brigade": 2, "division": 3}


class CombatError(ValueError):
    """A combat input is not a valid §§11-15 position."""


# ---------------------------------------------------------------------------
# small numeric helpers
# ---------------------------------------------------------------------------

def _points(value: Any, *, name: str = "points") -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise CombatError(f"{name} must be an integer or Fraction")
    result = Fraction(value)
    if result < 0:
        raise CombatError(f"{name} must not be negative")
    return result


def _whole(value: Any, *, name: str = "value", minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CombatError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise CombatError(f"{name} must be at least {minimum}")
    return value


def _round_half_up(value: Fraction) -> int:
    """11.32: nearest whole number, halves up (11.5 = 12)."""
    return math.floor(value + Fraction(1, 2))


def raw_points(rating: Fraction | int, toe_strength: Fraction | int) -> Fraction:
    """Raw Points: Combat Rating x TOE Strength used (11.32, 11.33)."""
    return (_points(rating, name="rating")
            * _points(toe_strength, name="toe_strength"))


def actual_points(raw: Fraction | int) -> int:
    """11.32-11.33: Raw Points divided by ten, halves up, below five is zero."""
    value = _points(raw, name="raw")
    if value < 5:
        return 0
    return _round_half_up(value / 10)


# ---------------------------------------------------------------------------
# 11.1 unit combat characteristics
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CombatUnit:
    """A unit or counter with the seven combat characteristics (11.1).

    Every rating is caller-supplied OA data (R-06).  ``target_class`` is the
    3.22 class the barrage and anti-armor tables need; ``kind`` selects the
    12.22 target exceptions.  ``position`` is the 12.11 artillery position and
    is empty for a unit that is not artillery.
    """

    unit_id: str
    side: str
    hex_id: str = ""
    toe_strength: Fraction = Fraction(0)
    barrage_rating: Fraction = Fraction(0)
    vulnerability_rating: Fraction = Fraction(0)
    anti_armor_rating: Fraction = Fraction(0)
    armor_protection: Fraction = Fraction(0)
    offensive_close_assault: Fraction = Fraction(0)
    defensive_close_assault: Fraction = Fraction(0)
    aa_rating: Fraction = Fraction(0)
    target_class: str = INFANTRY
    kind: str = "combat"
    position: str = ""
    italian: bool = False
    parenthesized_close_assault: bool = False
    artillery_hq: bool = False
    self_propelled: bool = False
    halftrack: bool = False
    tank: bool = False
    recce: bool = False
    hq: bool = False
    motorized: bool = False
    stacking_points: Fraction = Fraction(1)
    pinned: bool = False
    out_of_ammo: bool = False
    cohesion: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.unit_id, str) or not self.unit_id.strip():
            raise CombatError("unit_id must be a non-empty string")
        if not isinstance(self.side, str) or not self.side.strip():
            raise CombatError("side must be a non-empty string")
        if not isinstance(self.hex_id, str):
            raise CombatError("hex_id must be a string")
        for name in ("toe_strength", "barrage_rating", "vulnerability_rating",
                     "anti_armor_rating", "armor_protection",
                     "offensive_close_assault", "defensive_close_assault",
                     "aa_rating", "stacking_points"):
            object.__setattr__(self, name,
                               _points(getattr(self, name), name=name))
        if self.target_class not in TARGET_CLASSES:
            raise CombatError(f"unknown target class: {self.target_class!r}")
        if self.kind not in KINDS:
            raise CombatError(f"unknown counter kind: {self.kind!r}")
        if self.position not in ("", *POSITIONS):
            raise CombatError(f"unknown artillery position: {self.position!r}")
        for name in ("italian", "parenthesized_close_assault", "artillery_hq",
                     "self_propelled", "halftrack", "tank", "recce", "hq",
                     "motorized", "pinned", "out_of_ammo"):
            if not isinstance(getattr(self, name), bool):
                raise CombatError(f"{name} must be a bool")
        if isinstance(self.cohesion, bool) or not isinstance(self.cohesion, int):
            raise CombatError("cohesion must be an integer")

    @property
    def barrages(self) -> bool:
        """11.11: only artillery possesses a Barrage Rating."""
        return self.barrage_rating > 0

    @property
    def is_gun(self) -> bool:
        """11.12: Artillery and Anti-Tank units are Guns."""
        return self.target_class == GUN

    @property
    def is_artillery_hq(self) -> bool:
        return self.artillery_hq or (self.kind == "hq" and self.barrages)

    @property
    def armour_target(self) -> bool:
        return self.armor_protection > 0


def strength(units: Iterable[CombatUnit],
             kind: str = "barrage") -> Fraction:
    """Total Actual Strength Points of *units* for one function (11.31-11.34).

    Raw Points are totalled first and divided once, so strengths from several
    units or hexes cannot be rounded separately.  AA is the exception: its Raw
    Points are its Actual Points (11.37).
    """
    attribute = {"barrage": "barrage_rating",
                 "anti_armor": "anti_armor_rating",
                 "offensive": "offensive_close_assault",
                 "defensive": "defensive_close_assault",
                 "aa": "aa_rating"}.get(kind)
    if attribute is None:
        raise CombatError(f"unknown strength kind: {kind!r}")
    raw = sum((getattr(unit, attribute) * unit.toe_strength
               for unit in units), Fraction(0))
    if kind == "aa":
        return raw                                            # 11.37
    return Fraction(actual_points(raw))


def aa_points(unit: CombatUnit) -> Fraction:
    """11.37: AA Actual Points are the Raw Points; there is no division."""
    return raw_points(unit.aa_rating, unit.toe_strength)


# ---------------------------------------------------------------------------
# 11.2 capability point expenditures
# ---------------------------------------------------------------------------

#: Activities a caller may attribute to one unit in one Combat Segment.
CP_ACTIVITIES = frozenset({
    "barrage", "anti_armor", "close_assault", "probe", "holding_off",
    "undergoes_barrage", "undergoes_assault", "defends",
})


def probe_defender_cp(final_differential: int) -> int:
    """15.96: a Probe defended at worse than -3 costs the defender nothing."""
    differential = _whole(final_differential, name="final_differential")
    if differential < PROBE_DEFENDER_FLOOR:
        return 0
    return CP_NON_PHASING_PROBE


def combat_cp(*, phasing: bool, activities: Iterable[str],
              final_differential: int | None = None,
              spent: int = 0) -> int:
    """The CP a unit expends in one Combat Segment (11.21-11.27).

    ``activities`` is the set of things the unit did or underwent.  A
    Phasing attacker pays five, a Probe two and a unit that only undergoes
    Barrage three (11.23).  A non-Phasing unit pays three, two when defending
    against a Probe (or nothing at all, 15.96) and one when it defends a full
    Close Assault at -4 or worse (11.27).  The 11.24 segment cap is applied
    to ``spent`` as well.
    """
    if not isinstance(phasing, bool):
        raise CombatError("phasing must be a bool")
    acts = frozenset(activities)
    unknown = acts - CP_ACTIVITIES
    if unknown:
        raise CombatError(f"unknown combat activity: {sorted(unknown)!r}")
    if "probe" in acts and "close_assault" in acts:
        raise CombatError("a Probe is a form of Close Assault, not both")
    spent = _whole(spent, name="spent", minimum=0)
    if final_differential is not None:
        differential = _whole(final_differential, name="final_differential")
    else:
        differential = None

    if phasing:
        if acts & {"barrage", "anti_armor", "close_assault"}:
            cost = CP_PHASING_ATTACK                            # 11.22, 11.26
        elif "probe" in acts:
            cost = CP_PHASING_PROBE                              # 11.23
        elif "undergoes_barrage" in acts:
            cost = CP_PHASING_BARRAGED                           # 11.23
        else:
            cost = 0
        cap = SEGMENT_CP_CAP["phasing"]
    else:
        if "probe" in acts:
            cost = (probe_defender_cp(differential)
                    if differential is not None else CP_NON_PHASING_PROBE)
        elif "defends" in acts and differential is not None and differential <= -4:
            cost = CP_NON_PHASING_ROUTED                         # 11.27
        elif acts & {"barrage", "holding_off", "undergoes_assault", "defends",
                     "undergoes_barrage"}:
            cost = CP_NON_PHASING_ATTACK                         # 11.21
        else:
            cost = 0
        cap = SEGMENT_CP_CAP["non_phasing"]

    return max(0, min(cost, cap - spent))                        # 11.24


def hex_combat_cp(units: Iterable[CombatUnit], cost: int) -> dict[str, int]:
    """11.25: a hex's combat cost applies to every unit in the hex."""
    amount = _whole(cost, name="cost", minimum=0)
    return {unit.unit_id: amount for unit in units}


# ---------------------------------------------------------------------------
# 12.1 artillery positions
# ---------------------------------------------------------------------------

def position_change_allowed(*, at_combat_segment_start: bool) -> bool:
    """12.12: gun positions change only at the start of a Combat Segment."""
    if not isinstance(at_combat_segment_start, bool):
        raise CombatError("at_combat_segment_start must be a bool")
    return at_combat_segment_start


def group_may_coordinate(units: Sequence[CombatUnit],
                         *, hexes: Sequence[str] | None = None) -> tuple[bool, str]:
    """12.13-12.16: may these artillery units combine fire on one target?

    Forward guns coordinate across hexes (12.13); an Italian unit in a
    Forward position coordinates only inside its own hex (12.14); a Back unit
    coordinates with nobody (12.16).
    """
    members = tuple(units)
    if not members:
        raise CombatError("coordinating fire needs at least one unit")
    hexes = tuple(hexes) if hexes is not None else tuple(u.hex_id for u in members)
    if len(hexes) != len(members):
        raise CombatError("hexes must be supplied once per unit")
    if len(members) == 1:
        return True, ""
    if any(unit.position == BACK for unit in members):
        return False, "12.16"                                  # 12.16
    if any(unit.italian for unit in members):
        if len(set(hexes)) > 1:
            return False, "12.14"                              # 12.14
    return True, ""


def may_split_fire(unit: CombatUnit, *, targets: int) -> bool:
    """12.15-12.16: only a Forward gun may split its TOE Strength."""
    _whole(targets, name="targets", minimum=0)
    if unit.position != FORWARD:
        return False
    return True


# ---------------------------------------------------------------------------
# 12.2 target selection
# ---------------------------------------------------------------------------

def is_barrage_target(unit: CombatUnit) -> bool:
    """12.22: counters that count as Barrage targets."""
    if unit.kind in NON_TARGET_KINDS:
        return False
    if unit.stacking_points <= 0:
        return False
    if unit.kind == "hq" and (unit.toe_strength == 0
                              or unit.parenthesized_close_assault):
        return False
    return True


def targets_by_class(units: Iterable[CombatUnit]) -> dict[str, tuple[str, ...]]:
    """12.23: the defender states target counts by Gun/Armor/Infantry class."""
    grouped: dict[str, list[str]] = {name: [] for name in TARGET_CLASSES}
    for unit in units:
        if is_barrage_target(unit):
            grouped[unit.target_class].append(unit.unit_id)
    return {name: tuple(ids) for name, ids in grouped.items()}


# ---------------------------------------------------------------------------
# 12.3-12.5 barrage allocation and resolution
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BarrageOrder:
    """One firing unit's share of a Barrage against one target."""

    firing_unit_id: str
    firing_hex: str
    target_id: str
    target_hex: str
    toe_used: Fraction

    def __post_init__(self) -> None:
        for name in ("firing_unit_id", "firing_hex", "target_id", "target_hex"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise CombatError(f"{name} must be a non-empty string")
        object.__setattr__(self, "toe_used",
                           _points(self.toe_used, name="toe_used"))
        if self.toe_used <= 0:
            raise CombatError("toe_used must be positive")


@dataclass(frozen=True)
class CombatViolation:
    case: str
    message: str

    def to_obj(self) -> dict[str, str]:
        return {"case": self.case, "message": self.message}


def check_barrage_orders(orders: Iterable[BarrageOrder],
                         units: Iterable[CombatUnit], *,
                         adjacent: Callable[[str, str], bool] | None = None
                         ) -> tuple[CombatViolation, ...]:
    """Check a secret barrage plot against 12.11-12.32.

    The caller supplies map adjacency because the map is R-05.  Violations are
    returned, never raised: a plot is checked as a whole.
    """
    members = {unit.unit_id: unit for unit in units}
    orders = tuple(orders)
    violations: list[CombatViolation] = []
    per_unit: dict[str, Fraction] = {}
    targets_per_unit: dict[str, set[str]] = {}
    seen: set[tuple[str, str]] = set()

    for order in orders:
        unit = members.get(order.firing_unit_id)
        if unit is None:
            violations.append(CombatViolation(
                "12.23", f"no such firing unit: {order.firing_unit_id}"))
            continue
        if not unit.barrages:
            violations.append(CombatViolation(
                "12.11", f"{unit.unit_id} has no Barrage Rating"))
        target = members.get(order.target_id)
        if target is None:
            violations.append(CombatViolation(
                "12.23", f"no such target: {order.target_id}"))
        else:
            if not is_barrage_target(target):
                violations.append(CombatViolation(
                    "12.22", f"{target.unit_id} is not a Barrage target"))
            if target.side == unit.side:
                violations.append(CombatViolation(
                    "12.31", "a unit may not Barrage a Friendly target"))
        if order.firing_hex == order.target_hex:
            violations.append(CombatViolation(
                "12.31", "Barrage targets are in adjacent hexes, not the firing hex"))
        elif adjacent is not None and not adjacent(order.firing_hex,
                                                   order.target_hex):
            violations.append(CombatViolation(
                "12.31", "Barrage targets must be in an adjacent hex"))
        per_unit[unit.unit_id] = (per_unit.get(unit.unit_id, Fraction(0))
                                  + order.toe_used)
        targets_per_unit.setdefault(unit.unit_id, set()).add(order.target_id)
        key = (order.firing_hex, order.target_id)
        if key in seen:
            violations.append(CombatViolation(
                "12.32",
                "a target may be barraged only once from each adjacent hex"))
        seen.add(key)

    for unit_id, used in per_unit.items():
        unit = members[unit_id]
        if used > unit.toe_strength:
            violations.append(CombatViolation(
                "12.15", f"{unit_id} commits more TOE Strength than it has"))
        if len(targets_per_unit[unit_id]) > 1 and unit.position != FORWARD:
            violations.append(CombatViolation(
                "12.16", f"{unit_id} may not split fire unless Forward"))

    for target_id in sorted({order.target_id for order in orders}):
        group = [members[order.firing_unit_id] for order in orders
                 if order.target_id == target_id
                 and order.firing_unit_id in members]
        if len(group) < 2:
            continue
        allowed, case = group_may_coordinate(group)
        if not allowed:
            violations.append(CombatViolation(
                case, f"units firing at {target_id} may not coordinate fire"))
    return tuple(violations)


def barrage_strength(orders: Iterable[BarrageOrder],
                     units: Iterable[CombatUnit]) -> dict[str, Fraction]:
    """12.13-12.15, 11.34: Actual Barrage Points per target.

    Every order's Raw Points for one target are totalled before the single
    division by ten, which is what lets Forward guns combine fire.
    """
    members = {unit.unit_id: unit for unit in units}
    raw: dict[str, Fraction] = {}
    for order in orders:
        unit = members.get(order.firing_unit_id)
        if unit is None:
            raise CombatError(f"no such firing unit: {order.firing_unit_id}")
        raw[order.target_id] = (raw.get(order.target_id, Fraction(0))
                                + raw_points(unit.barrage_rating, order.toe_used))
    return {target: Fraction(actual_points(value))
            for target, value in raw.items()}


def shifted_band(bands: Sequence[tuple[int, int]], points: int,
                 shifts: int) -> tuple[int, int] | None:
    """12.33-12.34: move a Barrage Points row the defender's shifts left.

    ``bands`` is the table's row layout, supplied by the caller (R-04).  A
    shift worse than the lowest row means the Barrage had no effect; ``None``
    is that result.
    """
    _whole(shifts, name="shifts", minimum=0)
    rows = tuple(tuple(band) for band in bands)
    if not rows:
        raise CombatError("bands must not be empty")
    for lower, upper in rows:
        _whole(lower, name="band lower bound", minimum=0)
        _whole(upper, name="band upper bound", minimum=0)
        if lower > upper:
            raise CombatError("a band's lower bound may not exceed its upper")
    for index, (lower, upper) in enumerate(rows):
        if lower <= points <= upper:
            moved = index - shifts
            return rows[moved] if moved >= 0 else None
    raise CombatError(f"{points} falls in no supplied Barrage band")


@dataclass(frozen=True)
class BarrageRoll:
    """One row of a caller-supplied Barrage table.

    The values are read from the table; nothing here is a game value of its
    own.  ``roll`` is the sequential two-dice read-out (12.42).
    """

    roll: int = 0
    pin: bool = False
    toe_losses: int = 0
    truck_losses: int = 0
    no_effect: bool = False

    def __post_init__(self) -> None:
        if self.roll:
            _sequential_roll(self.roll)


BarrageTable = Callable[[int, int, str], BarrageRoll]


def _sequential_roll(roll: int) -> int:
    """12.42/15.73: two dice read large-first, so 11..66 with 1-6 digits."""
    value = _whole(roll, name="roll")
    if not (11 <= value <= 66) or not all(1 <= int(digit) <= 6
                                          for digit in str(value)):
        raise CombatError("roll must be a sequential two-dice read-out (11..66)")
    return value


@dataclass(frozen=True)
class BarrageOutcome:
    target_id: str
    pinned: bool
    toe_losses: int
    truck_losses: int
    no_effect: bool

    def to_obj(self) -> dict[str, Any]:
        return {"target_id": self.target_id, "pinned": self.pinned,
                "toe_losses": self.toe_losses,
                "truck_losses": self.truck_losses,
                "no_effect": self.no_effect, "rule": "12.44-12.46"}


def resolve_barrage(*, column: int, roll: int, target: CombatUnit,
                    table: BarrageTable) -> BarrageOutcome:
    """12.43-12.46: resolve one target's Barrage.

    ``column`` is the row already shifted for terrain (12.33).  A Pin result
    never applies to a Gun or an Artillery HQ (12.44).  Motorized infantry TOE
    Points lost also remove their Trucks (12.46).
    """
    _whole(column, name="column", minimum=0)
    outcome = table(column, _sequential_roll(roll), target.target_class)
    if not isinstance(outcome, BarrageRoll):
        raise CombatError("the barrage table must return a BarrageRoll")
    pinned = bool(outcome.pin) and not (target.is_gun or target.is_artillery_hq)
    lost = min(_whole(outcome.toe_losses, name="toe_losses", minimum=0),
               math.floor(target.toe_strength))
    trucks = _whole(outcome.truck_losses, name="truck_losses", minimum=0)
    if target.motorized:
        trucks += lost                                           # 12.46
    return BarrageOutcome(target_id=target.unit_id, pinned=pinned,
                          toe_losses=lost, truck_losses=trucks,
                          no_effect=bool(outcome.no_effect))


def resolve_truck_barrage(*, column: int, roll: int,
                          table: BarrageTable) -> int:
    """12.46: the second roll, on the table's Trucks section."""
    _whole(column, name="column", minimum=0)
    outcome = table(column, _sequential_roll(roll), TRUCKS)
    if not isinstance(outcome, BarrageRoll):
        raise CombatError("the barrage table must return a BarrageRoll")
    return _whole(outcome.truck_losses, name="truck_losses", minimum=0)


@dataclass(frozen=True)
class PinnedEffects:
    """12.44: what a Pinned marker forbids for the rest of the segment."""

    may_move: bool = False
    may_anti_armor: bool = False
    may_close_assault: bool = False
    takes_casualties: bool = True
    rule: str = "12.44"

    def to_obj(self) -> dict[str, Any]:
        return {"may_move": self.may_move,
                "may_anti_armor": self.may_anti_armor,
                "may_close_assault": self.may_close_assault,
                "takes_casualties": self.takes_casualties,
                "rule": self.rule}


def pinned_effects(pinned: bool) -> PinnedEffects:
    """12.44: a Pinned unit may not move, fire anti-armor or assault."""
    if not isinstance(pinned, bool):
        raise CombatError("pinned must be a bool")
    if not pinned:
        return PinnedEffects(may_move=True, may_anti_armor=True,
                             may_close_assault=True)
    return PinnedEffects()


def facility_barrage_points(*, facility: str, actual_points_used: Fraction | int,
                            raw_points_used: Fraction | int) -> Fraction:
    """12.53-12.54: which points feed the Air Bombardment Table.

    A Supply Dump or Air Facility uses Raw Barrage Points; every other
    facility uses the Actual Points (12.54).
    """
    if facility not in FACILITIES:
        raise CombatError(f"unknown facility: {facility!r}")
    if facility in ("supply_dump", "air_facility"):
        return _points(raw_points_used, name="raw_points_used")
    return _points(actual_points_used, name="actual_points_used")


# ---------------------------------------------------------------------------
# 13 Retreat Before Assault
# ---------------------------------------------------------------------------

def may_retreat_before_assault(*, pinned: bool,
                               cohesion: int) -> tuple[bool, str]:
    """13.1: any non-Pinned non-Phasing unit above the collapse level."""
    if not isinstance(pinned, bool):
        raise CombatError("pinned must be a bool")
    if isinstance(cohesion, bool) or not isinstance(cohesion, int):
        raise CombatError("cohesion must be an integer")
    if pinned:
        return False, "12.44"
    if cohesion <= COLLAPSE_AT:
        return False, "13.1"
    return True, ""


def retreat_break_off(*, contact: bool, engaged: bool) -> Fraction:
    """13.22: a unit in an Enemy ZOC pays the 8.6 Break Off cost."""
    for name, value in (("contact", contact), ("engaged", engaged)):
        if not isinstance(value, bool):
            raise CombatError(f"{name} must be a bool")
    if engaged:
        return ENGAGED_BREAK_OFF_CP
    if contact:
        return CONTACT_BREAK_OFF_CP
    return Fraction(0)


def retreat_allowance(*, adjacent_to_enemy_combat: bool,
                      one_hex_cost: Fraction | int = 1) -> Fraction | None:
    """13.23-13.24: how many CP a retreat may spend.

    A unit beginning the step adjacent to an Enemy combat unit may spend as
    many CP as it wishes (``None``); otherwise the cap is four CP or one hex,
    whichever is greater.
    """
    if not isinstance(adjacent_to_enemy_combat, bool):
        raise CombatError("adjacent_to_enemy_combat must be a bool")
    if adjacent_to_enemy_combat:
        return None
    return max(Fraction(4), _points(one_hex_cost, name="one_hex_cost"))


def retreat_action_allowed(action: str) -> bool:
    """13.25: a retreating unit may only move (or blow a supply dump)."""
    if action in ("move", "blow_supply_dump"):
        return True
    if not isinstance(action, str) or not action:
        raise CombatError("action must be a non-empty string")
    return False


def retreat_path_check(origin: str, path: Iterable[str],
                       controlled: Iterable[str]) -> tuple[bool, str]:
    """13.26: stop in an Enemy ZOC, never move ZOC to ZOC.

    Returns ``(allowed, stop_reason)``; a path that would move directly from
    one Enemy-controlled hex into another is refused, which is the "may not
    Retreat Before Assault" case.
    """
    if not isinstance(origin, str) or not origin.strip():
        raise CombatError("origin must be a non-empty hex id")
    enemy_zoc = frozenset(controlled)
    current = origin
    for destination in path:
        if not isinstance(destination, str) or not destination.strip():
            raise CombatError("a retreat path must contain non-empty hex ids")
        if current in enemy_zoc and destination in enemy_zoc:
            return False, "13.26"
        current = destination
        if destination in enemy_zoc:
            return True, "10.23"
    return True, ""


@dataclass(frozen=True)
class RetreatEffects:
    """13.28: what happens to a unit that retreated into an assaulted hex."""

    takes_anti_armor: bool = True
    may_fire_anti_armor: bool = False
    adds_close_assault_ratings: bool = False
    toe_counts_for_losses: bool = True
    rule: str = "13.28"

    def to_obj(self) -> dict[str, Any]:
        return {"takes_anti_armor": self.takes_anti_armor,
                "may_fire_anti_armor": self.may_fire_anti_armor,
                "adds_close_assault_ratings": self.adds_close_assault_ratings,
                "toe_counts_for_losses": self.toe_counts_for_losses,
                "rule": self.rule}


def retreat_before_assault_effects() -> RetreatEffects:
    """13.28."""
    return RetreatEffects()


# ---------------------------------------------------------------------------
# 14 Anti-Armor Combat
# ---------------------------------------------------------------------------

def artillery_vulnerability(unit: CombatUnit, *,
                            role: str = "") -> Fraction:
    """12.18-12.19, 14.14, 14.47: a Gun's Vulnerability in one combat role.

    Artillery in an Anti-Armor role is Vulnerability 2 (12.19/14.14); one
    participating in an Offensive Close Assault has its Vulnerability halved,
    rounded up (12.18).  Any other role uses the printed rating.
    """
    if role not in ("", "anti_armor", "offensive_close_assault"):
        raise CombatError(f"unknown gun role: {role!r}")
    if role == "anti_armor":
        return Fraction(2)
    if role == "offensive_close_assault":
        return Fraction(math.ceil(unit.vulnerability_rating / 2))
    return unit.vulnerability_rating


def may_participate_anti_armor(unit: CombatUnit, *,
                               withheld: bool = False) -> tuple[bool, str]:
    """14.11-14.13: who may fire Anti-Armor Points."""
    if not isinstance(withheld, bool):
        raise CombatError("withheld must be a bool")
    if unit.position == BACK:
        return False, "14.13"
    if unit.anti_armor_rating <= 0:
        return False, "14.11"
    if withheld:
        return False, "14.21"
    return True, ""


def anti_armor_strength(units: Iterable[CombatUnit]) -> Fraction:
    """14.11, 11.32: Actual Anti-Armor Points, Raw totalled first."""
    return strength(units, "anti_armor")


def anti_armor_shifts(*, hex_shift: int = 0, hexside_shift: int = 0) -> int:
    """14.33: hex terrain is not cumulative, a hexside adds to it."""
    total = _whole(hex_shift, name="hex_shift", minimum=0)
    total += _whole(hexside_shift, name="hexside_shift", minimum=0)
    return total


def anti_armor_column(points: int, shifts: int = 0) -> int:
    """14.32, 14.35: shift the strength row down, never below the 0 row."""
    value = _whole(points, name="points", minimum=0)
    return max(0, value - _whole(shifts, name="shifts", minimum=0))


def anti_armor_prohibited(*, feature: str, crossed_by_road: bool = False,
                          crossed_by_track: bool = False) -> bool:
    """14.34: hexsides that forbid Anti-Armor fire."""
    for name, value in (("crossed_by_road", crossed_by_road),
                        ("crossed_by_track", crossed_by_track)):
        if not isinstance(value, bool):
            raise CombatError(f"{name} must be a bool")
    if feature == "ridge":
        return not (crossed_by_road or crossed_by_track)
    if feature == "slope":
        return not (crossed_by_road or crossed_by_track)
    if feature == "escarpment":
        return not crossed_by_track
    if feature not in ("", "clear", "wadi"):
        raise CombatError(f"unknown anti-armor feature: {feature!r}")
    return False


def check_anti_armor_targets(hexes: Iterable[str]) -> tuple[CombatViolation, ...]:
    """14.22: one Anti-Armor attack per hex per Combat Segment."""
    seen: set[str] = set()
    violations: list[CombatViolation] = []
    for hex_id in hexes:
        if hex_id in seen:
            violations.append(CombatViolation(
                "14.22", f"{hex_id} is attacked by Anti-Armor fire more than once"))
        seen.add(hex_id)
    return tuple(violations)


def reassigned_to_close_assault(points: int, *,
                                defending_armor_present: bool) -> int:
    """14.23: half the points (rounded down) if the target has no armor."""
    if not isinstance(defending_armor_present, bool):
        raise CombatError("defending_armor_present must be a bool")
    value = _whole(points, name="points", minimum=0)
    if defending_armor_present:
        return 0
    return value // 2


@dataclass(frozen=True)
class LossTarget:
    """One unit that can absorb losses.

    ``absorb_rate`` is what one TOE Strength Point absorbs: a Close Assault
    Rating (15.83d) or an Armor Protection Rating (14.42).  ``weight`` feeds
    the 15.83e proportional split between hexes; zero means "use strength".
    """

    unit_id: str
    toe_available: Fraction
    absorb_rate: Fraction
    hex_id: str = ""
    weight: Fraction = Fraction(0)

    def __post_init__(self) -> None:
        if not isinstance(self.unit_id, str) or not self.unit_id.strip():
            raise CombatError("unit_id must be a non-empty string")
        object.__setattr__(self, "toe_available",
                           _points(self.toe_available, name="toe_available"))
        object.__setattr__(self, "absorb_rate",
                           _points(self.absorb_rate, name="absorb_rate"))
        if self.absorb_rate <= 0:
            raise CombatError("absorb_rate must be positive")
        if not isinstance(self.hex_id, str):
            raise CombatError("hex_id must be a string")
        object.__setattr__(self, "weight", _points(self.weight, name="weight"))


@dataclass(frozen=True)
class LossPlan:
    """How a damage or casualty total is absorbed by TOE Strength Points."""

    removals: tuple[tuple[str, Fraction], ...]
    absorbed: Fraction
    excess: Fraction

    def removed(self, unit_id: str) -> Fraction:
        return next((amount for uid, amount in self.removals
                     if uid == unit_id), Fraction(0))

    def to_obj(self) -> dict[str, Any]:
        return {"removals": [[uid, str(amount)] for uid, amount in self.removals],
                "absorbed": str(self.absorbed), "excess": str(self.excess)}


def absorb_loss(amount: Fraction | int,
                targets: Iterable[LossTarget]) -> LossPlan:
    """Remove whole TOE Points until *amount* is absorbed (14.43, 15.83d).

    Points are taken from the highest-absorbing unit first, and spread between
    hexes in proportion to the strength each committed (15.83e).  Damage that
    nothing can absorb is reported as ``excess`` rather than lost silently
    (14.45).
    """
    total = _points(amount, name="amount")
    members = tuple(targets)
    if not members:
        raise CombatError("absorb_loss needs at least one loss target")
    identifiers = [target.unit_id for target in members]
    if len(set(identifiers)) != len(identifiers):
        raise CombatError("loss target unit_id values must be unique")

    remaining = {target.unit_id: target.toe_available for target in members}
    by_hex: dict[str, list[LossTarget]] = {}
    for target in members:
        by_hex.setdefault(target.hex_id, []).append(target)

    weights: dict[str, Fraction] = {}
    for hex_id, group in by_hex.items():
        weight = sum((target.weight for target in group if target.weight > 0),
                     Fraction(0))
        if weight == 0:
            weight = sum((target.toe_available * target.absorb_rate
                          for target in group), Fraction(0))
        weights[hex_id] = weight
    total_weight = sum(weights.values(), Fraction(0))
    if total_weight <= 0:
        raise CombatError("loss targets cannot absorb any points")
    desired = {hex_id: total * weight / total_weight
               for hex_id, weight in weights.items()}

    absorbed_by_hex = {hex_id: Fraction(0) for hex_id in by_hex}
    absorbed = Fraction(0)
    removed: dict[str, Fraction] = {}
    while absorbed < total:
        options = []
        for hex_id, group in by_hex.items():
            available = [target for target in group
                         if remaining[target.unit_id] >= 1]
            if available:
                options.append((desired[hex_id] - absorbed_by_hex[hex_id],
                                hex_id, available))
        if not options:
            break
        _, hex_id, available = max(options, key=lambda item: (item[0], item[1]))
        target = max(available, key=lambda item: (item.absorb_rate, item.unit_id))
        remaining[target.unit_id] -= 1
        removed[target.unit_id] = removed.get(target.unit_id, Fraction(0)) + 1
        absorbed += target.absorb_rate
        absorbed_by_hex[hex_id] += target.absorb_rate

    return LossPlan(
        removals=tuple((target.unit_id, removed[target.unit_id])
                       for target in members if target.unit_id in removed),
        absorbed=absorbed,
        excess=max(Fraction(0), total - absorbed),
    )


def armor_loss_targets(units: Iterable[CombatUnit], *,
                       committed: Iterable[str] | None = None,
                       withheld: Iterable[str] = (),
                       engagement: str = "") -> tuple[LossTarget, ...]:
    """14.41-14.48: Armor Protection absorption for one hex.

    Only committed armor is affected (14.11, 14.21); Self-Propelled guns
    absorb their Armor Protection plus Vulnerability (14.47); a hex containing
    only halftracks doubles their Armor Protection (14.48).
    """
    withheld_ids = frozenset(withheld)
    committed_ids = (None if committed is None else frozenset(committed))
    armor = [unit for unit in units
             if unit.armor_protection > 0
             and unit.unit_id not in withheld_ids
             and (committed_ids is None or unit.unit_id in committed_ids)]
    halftracks_only = bool(armor) and all(unit.halftrack for unit in armor)
    targets: list[LossTarget] = []
    for unit in armor:
        rate = unit.armor_protection
        if unit.self_propelled:
            rate += artillery_vulnerability(unit, role=engagement)   # 14.47
        if halftracks_only and unit.halftrack:
            rate *= 2                                                # 14.48
        targets.append(LossTarget(unit.unit_id, unit.toe_strength, rate,
                                  unit.hex_id))
    return tuple(targets)


def absorb_anti_armor(damage: int, units: Iterable[CombatUnit], *,
                      committed: Iterable[str] | None = None,
                      withheld: Iterable[str] = (),
                      engagement: str = "") -> LossPlan:
    """14.43-14.45: remove armor TOE Points to absorb Damage Points."""
    _whole(damage, name="damage", minimum=0)
    return absorb_loss(damage, armor_loss_targets(
        units, committed=committed, withheld=withheld, engagement=engagement))


def capture_path_allowed(path: Iterable[str], *,
                         enemy_units: Iterable[str] = (),
                         enemy_zoc: Iterable[str] = (),
                         impassable: Iterable[str] = ()) -> bool:
    """14.53: a captured Destroyed Tank may move three free hexes."""
    hexes = tuple(path)
    if len(hexes) > 3:
        return False
    blocked = (frozenset(enemy_units) | frozenset(enemy_zoc)
               | frozenset(impassable))
    return all(hex_id not in blocked for hex_id in hexes)


# ---------------------------------------------------------------------------
# 15 Close Assault
# ---------------------------------------------------------------------------

def may_close_assault(unit: CombatUnit, *, offensive: bool) -> bool:
    """15.11, 15.15: a unit out of ammunition may not Close Assault."""
    if not isinstance(offensive, bool):
        raise CombatError("offensive must be a bool")
    if unit.out_of_ammo:
        return False
    rating = (unit.offensive_close_assault if offensive
              else unit.defensive_close_assault)
    return rating > 0 or not offensive


def assault_raw_strength(units: Iterable[CombatUnit], *,
                         offensive: bool,
                         excluded: Iterable[str] = ()) -> Fraction:
    """15.83b: Raw Close Assault Points of the units whose ratings count.

    ``excluded`` holds Pinned or previously retreated units (15.12), units
    withheld from the ratings (15.14) and parenthesized units that share a hex
    with combat units (15.17).
    """
    if not isinstance(offensive, bool):
        raise CombatError("offensive must be a bool")
    skip = frozenset(excluded)
    attribute = ("offensive_close_assault" if offensive
                 else "defensive_close_assault")
    return sum((getattr(unit, attribute) * unit.toe_strength
                for unit in units if unit.unit_id not in skip), Fraction(0))


def close_assault_strength(raw: Fraction | int, *,
                           other_raw: Fraction | int | None = None) -> int:
    """15.28, 11.33: convert Raw Close Assault Points to Actual Points.

    Fewer than five Raw Points is zero; when *both* sides have fewer than ten
    Raw Points, the Raw Points are used as if they were Actual Points.
    """
    value = _points(raw, name="raw")
    if value < 5:
        return 0
    if other_raw is not None:
        other = _points(other_raw, name="other_raw")
        if value < 10 and other < 10:
            return int(value)
    return _round_half_up(value / 10)


def basic_differential(attacker_actual: int, defender_actual: int) -> int:
    """15.26: Attacker's Actual Points minus the Defender's."""
    return (_whole(attacker_actual, name="attacker_actual", minimum=0)
            - _whole(defender_actual, name="defender_actual", minimum=0))


@dataclass(frozen=True)
class ColumnShift:
    case: str
    columns: int

    def to_obj(self) -> dict[str, Any]:
        return {"case": self.case, "columns": self.columns}


@dataclass(frozen=True)
class UnitSize:
    """15.52-15.53: a formation level, and a brigade's Stacking Points."""

    level: str = "battalion"
    points: int = 0

    def __post_init__(self) -> None:
        if self.level not in LEVEL_RANK:
            raise CombatError(f"unknown formation level: {self.level!r}")
        _whole(self.points, name="points", minimum=0)


def size_shift(larger: UnitSize, smaller: UnitSize) -> int:
    """15.53: the Organizational Size column adjustment in the larger's favour."""
    if LEVEL_RANK[larger.level] <= LEVEL_RANK[smaller.level]:
        return 0
    if larger.level == "division":
        if smaller.level == "brigade":
            return 1 if smaller.points >= 3 else 2
        if smaller.level == "battalion":
            return 4
        return 8
    if larger.level == "brigade":
        return 2 if smaller.level == "battalion" else 4
    if larger.level == "battalion":
        return 2 if smaller.level == "company" else 0
    return 0


def combined_arms_reduction(*, tank_toe: Fraction | int,
                            supported_toe: Fraction | int,
                            tank_actual: int) -> int:
    """15.4: unsupported tanks lose Actual Close Assault Points.

    Tanks must be matched by infantry; the reduction is one Actual Point per
    three unsupported TOE Points (at least one), capped at four.  The two
    worked examples (two and four unsupported TOE at rating 7) fix the
    integer step: 2 TOE -> 1, 4 TOE -> 1.
    """
    unsupported = (_points(tank_toe, name="tank_toe")
                   - _points(supported_toe, name="supported_toe"))
    if unsupported <= 0:
        return 0
    reduction = max(1, int(unsupported // 3))
    return min(COMBINED_ARMS_MAX, reduction,
               _whole(tank_actual, name="tank_actual", minimum=0))


def is_probe(committed_toe: Fraction | int,
             available_toe: Fraction | int) -> bool:
    """15.25, 15.91: less than half the available TOE Strength is a Probe."""
    available = _points(available_toe, name="available_toe")
    committed = _points(committed_toe, name="committed_toe")
    if committed > available:
        raise CombatError("committed_toe may not exceed available_toe")
    return committed < available * PROBE_SHARE


def hexside_shift(shifts: Sequence[int], *, dual_terrain: bool = False) -> int:
    """15.33-15.36: hexside terrain shifts, in the attacker's favour.

    A defender benefits from one hexside type only (15.35); opposite benefits,
    such as a down slope against an up escarpment, are summed (15.36).  A
    hexside bearing two terrain types is passed with ``dual_terrain``.
    """
    if not isinstance(dual_terrain, bool):
        raise CombatError("dual_terrain must be a bool")
    values = tuple(_whole(value, name="shift") for value in shifts)
    if not values:
        return 0
    if dual_terrain:
        return sum(values)
    defender_benefits = [value for value in values if value < 0]
    attacker_benefits = [value for value in values if value > 0]
    if defender_benefits and attacker_benefits:
        return sum(values)                                    # 15.36
    return min(values)                                        # 15.35


def assault_terrain_allowed(*, motorized: bool, terrain: str = "",
                            feature: str = "",
                            direction: str = "") -> tuple[bool, str]:
    """15.34: terrain that forbids a Close Assault by unit type."""
    if not isinstance(motorized, bool):
        raise CombatError("motorized must be a bool")
    if direction not in ("", "up", "down"):
        raise CombatError("direction must be '', 'up' or 'down'")
    if motorized and feature == "escarpment" and direction != "down":
        return False, "15.34"
    if motorized and terrain == "salt_marsh":
        return False, "15.34"
    return True, ""


def must_retreat_unattackable(*, in_enemy_zoc: bool, can_attack: bool,
                              other_unit_attacks: bool) -> bool:
    """15.34: a unit that cannot attack a covering ZOC must retreat one hex."""
    for name, value in (("in_enemy_zoc", in_enemy_zoc),
                        ("can_attack", can_attack),
                        ("other_unit_attacks", other_unit_attacks)):
        if not isinstance(value, bool):
            raise CombatError(f"{name} must be a bool")
    return in_enemy_zoc and not can_attack and not other_unit_attacks


@dataclass(frozen=True)
class AdjustedDifferential:
    """15.27: Basic Assault Differential plus its column adjustments."""

    basic: int
    shifts: tuple[ColumnShift, ...] = ()
    no_attacker_casualties: bool = False

    @property
    def final(self) -> int:
        return self.basic + sum(shift.columns for shift in self.shifts)

    @property
    def overrun(self) -> bool:
        return is_overrun_column(self.final)

    def to_obj(self) -> dict[str, Any]:
        return {"basic": self.basic,
                "shifts": [shift.to_obj() for shift in self.shifts],
                "final": self.final, "overrun": self.overrun,
                "rule": "15.27"}


def is_overrun_column(differential: int) -> bool:
    """15.77: the Overrun section starts at +11."""
    return _whole(differential, name="differential") >= OVERRUN_COLUMN


def assault_differential(
    *,
    attacker_raw: Fraction | int,
    defender_raw: Fraction | int,
    attacker_size: UnitSize = UnitSize(),
    defender_size: UnitSize = UnitSize(),
    attacker_morale: int = 0,
    defender_morale: int = 0,
    terrain_columns: int = 0,
    hexside_columns: int = 0,
    zero_rated_defender_alone: bool = False,
    attacker_actual: int | None = None,
    defender_actual: int | None = None,
) -> AdjustedDifferential:
    """15.26-15.64: build the Adjusted Assault Differential.

    Positive columns favour the attacker.  ``terrain_columns`` is the
    defender's hex benefit (negative) and ``hexside_columns`` the hexside
    total from :func:`hexside_shift`.  The 15.51 two-to-one adjustment is
    skipped when 15.54 applies.
    """
    a_raw = _points(attacker_raw, name="attacker_raw")
    d_raw = _points(defender_raw, name="defender_raw")
    a_actual = (close_assault_strength(a_raw, other_raw=d_raw)
                if attacker_actual is None else
                _whole(attacker_actual, name="attacker_actual", minimum=0))
    d_actual = (close_assault_strength(d_raw, other_raw=a_raw)
                if defender_actual is None else
                _whole(defender_actual, name="defender_actual", minimum=0))
    if not isinstance(zero_rated_defender_alone, bool):
        raise CombatError("zero_rated_defender_alone must be a bool")
    basic = basic_differential(a_actual, d_actual)
    shifts: list[ColumnShift] = []

    if not zero_rated_defender_alone:
        if d_raw > 0 and a_raw >= 2 * d_raw:
            shifts.append(ColumnShift("15.51", 2))             # 15.51
        elif a_raw > 0 and d_raw >= 2 * a_raw:
            shifts.append(ColumnShift("15.51", -2))

    larger, smaller = ((attacker_size, defender_size)
                       if LEVEL_RANK[attacker_size.level]
                       >= LEVEL_RANK[defender_size.level]
                       else (defender_size, attacker_size))
    columns = size_shift(larger, smaller)
    if columns:
        shifts.append(ColumnShift("15.53",
                                  columns if larger is attacker_size else -columns))

    morale = (_whole(attacker_morale, name="attacker_morale")
              - _whole(defender_morale, name="defender_morale"))
    if morale:
        shifts.append(ColumnShift("15.61", morale))            # 15.61-15.62

    terrain = _whole(terrain_columns, name="terrain_columns")
    if terrain:
        shifts.append(ColumnShift("15.32", terrain))           # 15.31-15.32
    hexside = _whole(hexside_columns, name="hexside_columns")
    if hexside:
        shifts.append(ColumnShift("15.33", hexside))           # 15.33-15.36

    if zero_rated_defender_alone:
        shifts.append(ColumnShift("15.54", 3))                 # 15.54

    return AdjustedDifferential(basic=basic, shifts=tuple(shifts),
                                no_attacker_casualties=zero_rated_defender_alone)


def check_assault_targets(hexes: Iterable[str]) -> tuple[CombatViolation, ...]:
    """15.16, 15.23: one Close Assault or Probe per hex per Combat Segment."""
    seen: set[str] = set()
    violations: list[CombatViolation] = []
    for hex_id in hexes:
        if hex_id in seen:
            violations.append(CombatViolation(
                "15.23", f"{hex_id} is assaulted more than once in the segment"))
        seen.add(hex_id)
    return tuple(violations)


def assault_hexes_allowed(origin: str, targets: Sequence[str], *,
                          adjacent: Callable[[str, str], bool]) -> bool:
    """15.24: every assaulted hex adjoins the origin and the others."""
    if not isinstance(origin, str) or not origin.strip():
        raise CombatError("origin must be a non-empty hex id")
    members = tuple(targets)
    if not members:
        raise CombatError("an assault needs at least one target hex")
    for target in members:
        if not adjacent(origin, target):
            return False
    for first in members:
        for second in members:
            if first != second and not adjacent(first, second):
                return False
    return True


def parenthesized_rating_usable(unit: CombatUnit,
                                hex_units: Iterable[CombatUnit]) -> bool:
    """15.17: a parenthesized rating counts only in a hex of non-combat units."""
    if not unit.parenthesized_close_assault:
        return True
    others = [other for other in hex_units
              if other.unit_id != unit.unit_id
              and other.kind == "combat" and other.toe_strength > 0]
    return not others


def surrenders(*, out_of_ammo: bool, cohesion: int) -> bool:
    """15.88: a unit out of ammunition or at -17 Cohesion surrenders."""
    if not isinstance(out_of_ammo, bool):
        raise CombatError("out_of_ammo must be a bool")
    if isinstance(cohesion, bool) or not isinstance(cohesion, int):
        raise CombatError("cohesion must be an integer")
    return out_of_ammo or cohesion <= SURRENDER_AT


def defenders_surrender(units: Iterable[CombatUnit]) -> bool:
    """15.15: all defenders out of ammunition surrender en masse."""
    members = tuple(units)
    if not members:
        raise CombatError("defenders_surrender needs at least one unit")
    return all(unit.out_of_ammo for unit in members)


@dataclass(frozen=True)
class ParenthesizedDefence:
    """15.18: the 3:1 result against only parenthesized defenders."""

    attacker_ignores_first_20: bool = False
    defender_captured_at_20: bool = False
    rule: str = "15.18"

    def to_obj(self) -> dict[str, Any]:
        return {"attacker_ignores_first_20": self.attacker_ignores_first_20,
                "defender_captured_at_20": self.defender_captured_at_20,
                "rule": self.rule}


def parenthesized_defence(*, attacker_raw: Fraction | int,
                          defender_raw: Fraction | int) -> ParenthesizedDefence:
    """15.18: 3:1 Raw against parenthesized-only defenders."""
    attacker = _points(attacker_raw, name="attacker_raw")
    defender = _points(defender_raw, name="defender_raw")
    strong = defender > 0 and attacker >= 3 * defender
    return ParenthesizedDefence(attacker_ignores_first_20=strong,
                                defender_captured_at_20=strong)


@dataclass(frozen=True)
class EmptyDefence:
    """15.29: a defender that allocates nobody retreats three hexes."""

    retreat_hexes: int = EMPTY_DEFENCE_HEXES
    disorganization_points: int = EMPTY_DEFENCE_DP
    rule: str = "15.29"

    def to_obj(self) -> dict[str, Any]:
        return {"retreat_hexes": self.retreat_hexes,
                "disorganization_points": self.disorganization_points,
                "rule": self.rule}


def empty_defence() -> EmptyDefence:
    """15.29."""
    return EmptyDefence()


@dataclass(frozen=True)
class AssaultRoll:
    """One side's results from a caller-supplied Close Assault table.

    ``roll`` is the sequential two-dice read-out used for losses; ``sum`` is
    the same dice added for Engaged/Retreat/Captured (15.73).  Every field is
    table output, not a value this module invents.
    """

    roll: int = 0
    loss_percent: int = 0
    engaged: bool = False
    retreat_hexes: int = 0
    captured_percent: int = 0
    overrun: bool = False

    def __post_init__(self) -> None:
        if self.roll:
            _sequential_roll(self.roll)
        _whole(self.loss_percent, name="loss_percent", minimum=0)
        if self.loss_percent > 100:
            raise CombatError("loss_percent may not exceed 100")
        _whole(self.retreat_hexes, name="retreat_hexes", minimum=0)
        _whole(self.captured_percent, name="captured_percent", minimum=0)
        if self.captured_percent > 100:
            raise CombatError("captured_percent may not exceed 100")
        for name in ("engaged", "overrun"):
            if not isinstance(getattr(self, name), bool):
                raise CombatError(f"{name} must be a bool")


AssaultTable = Callable[[str, int, int], AssaultRoll]


@dataclass(frozen=True)
class AssaultSideResult:
    side: str
    loss_percent: int
    raw_lost: Fraction
    plan: LossPlan
    toe_lost: Fraction
    captured_toe: Fraction
    engaged: bool
    contact: bool
    retreat_hexes: int
    disorganization_points: int
    surrendered: bool

    def to_obj(self) -> dict[str, Any]:
        return {"side": self.side, "loss_percent": self.loss_percent,
                "raw_lost": str(self.raw_lost), "plan": self.plan.to_obj(),
                "toe_lost": str(self.toe_lost),
                "captured_toe": str(self.captured_toe),
                "engaged": self.engaged, "contact": self.contact,
                "retreat_hexes": self.retreat_hexes,
                "disorganization_points": self.disorganization_points,
                "surrendered": self.surrendered}


@dataclass(frozen=True)
class CloseAssaultOutcome:
    attacker: AssaultSideResult
    defender: AssaultSideResult
    probe: bool
    overrun: bool
    rule: str = "15"

    def to_obj(self) -> dict[str, Any]:
        return {"attacker": self.attacker.to_obj(),
                "defender": self.defender.to_obj(),
                "probe": self.probe, "overrun": self.overrun,
                "rule": self.rule}


def _loss_percent(roll: AssaultRoll, *, probe: bool, recce_only: bool,
                  ignores_first_20: bool, shortfall: int) -> int:
    percent = roll.loss_percent
    if ignores_first_20:
        percent = max(0, percent - 20)                        # 15.18
    if probe and recce_only:
        percent = max(0, percent - 10)                        # 15.95
    percent += 10 * _whole(shortfall, name="shortfall", minimum=0)  # 15.82
    return min(100, percent)


def _side_result(*, side: str, roll: AssaultRoll, raw: Fraction,
                 targets: Sequence[LossTarget], percent: int,
                 rounds_up: bool, probe: bool, overrun: bool,
                 captured_on_twenty: bool = False) -> AssaultSideResult:
    raw_lost = raw * percent / 100
    raw_lost = Fraction(math.ceil(raw_lost) if rounds_up
                        else math.floor(raw_lost))
    if raw_lost > 0 and not targets:
        raise CombatError("loss targets are required to absorb casualties")
    plan = (absorb_loss(raw_lost, targets) if raw_lost > 0
            else LossPlan((), Fraction(0), Fraction(0)))
    toe_lost = sum((amount for _, amount in plan.removals), Fraction(0))
    captured = Fraction(0)
    if captured_on_twenty and percent >= 20:
        captured = max(Fraction(0),
                       sum((target.toe_available for target in targets),
                           Fraction(0)) - toe_lost)          # 15.18
    elif roll.captured_percent:
        captured = Fraction(math.ceil(
            toe_lost * roll.captured_percent / 100))          # 15.85
        captured = min(captured, toe_lost)
    retreat = roll.retreat_hexes
    engaged = roll.engaged and not probe                       # 15.93
    if retreat and engaged:
        engaged = False                                       # 15.74
    if probe:
        engaged = False
    disorganization = (DISORGANIZATION_POINTS
                       if percent >= DISORGANIZATION_LOSS_PERCENT else 0)
    return AssaultSideResult(
        side=side, loss_percent=percent, raw_lost=raw_lost, plan=plan,
        toe_lost=toe_lost, captured_toe=captured, engaged=engaged,
        contact=not engaged and not probe and retreat == 0,  # 15.81
        retreat_hexes=retreat, disorganization_points=disorganization,
        surrendered=False)


def _surrender_result(*, side: str, raw: Fraction,
                      targets: Sequence[LossTarget]) -> AssaultSideResult:
    removals = tuple((target.unit_id, target.toe_available)
                     for target in targets if target.toe_available > 0)
    toe = sum((amount for _, amount in removals), Fraction(0))
    return AssaultSideResult(
        side=side, loss_percent=100, raw_lost=raw,
        plan=LossPlan(removals, raw, Fraction(0)), toe_lost=toe,
        captured_toe=toe, engaged=False, contact=False, retreat_hexes=0,
        disorganization_points=0, surrendered=True)


def resolve_close_assault(
    *,
    adjusted: AdjustedDifferential,
    attacker_roll: AssaultRoll,
    defender_roll: AssaultRoll,
    attacker_raw: Fraction | int,
    defender_raw: Fraction | int,
    attacker_targets: Sequence[LossTarget] = (),
    defender_targets: Sequence[LossTarget] = (),
    probe: bool = False,
    attacker_recce_only: bool = False,
    attacker_ignores_first_20: bool = False,
    defender_captured_on_twenty: bool = False,
    defender_retreat_shortfall: int = 0,
    attacker_retreat_shortfall: int = 0,
    defender_surrenders: bool = False,
) -> CloseAssaultOutcome:
    """15.71-15.96: apply both sides' Close Assault table results.

    The caller rolls once per side and reads the table; this function applies
    percentage losses, rounding (15.83c), Capture (15.85), Engaged/Retreat
    precedence (15.74), Disorganization (15.87) and Surrender (15.88/15.15).
    """
    if not isinstance(adjusted, AdjustedDifferential):
        raise CombatError("adjusted must be an AdjustedDifferential")
    for name, value in (("probe", probe),
                        ("attacker_recce_only", attacker_recce_only),
                        ("attacker_ignores_first_20", attacker_ignores_first_20),
                        ("defender_captured_on_twenty",
                         defender_captured_on_twenty),
                        ("defender_surrenders", defender_surrenders)):
        if not isinstance(value, bool):
            raise CombatError(f"{name} must be a bool")
    a_raw = _points(attacker_raw, name="attacker_raw")
    d_raw = _points(defender_raw, name="defender_raw")
    overrun = adjusted.overrun or defender_roll.overrun

    attacker_percent = _loss_percent(
        attacker_roll, probe=probe, recce_only=attacker_recce_only,
        ignores_first_20=attacker_ignores_first_20,
        shortfall=attacker_retreat_shortfall)
    if adjusted.no_attacker_casualties:
        attacker_percent = 0
    defender_percent = _loss_percent(
        defender_roll, probe=probe, recce_only=False, ignores_first_20=False,
        shortfall=defender_retreat_shortfall)

    attacker_result = _side_result(
        side="attacker", roll=attacker_roll, raw=a_raw,
        targets=tuple(attacker_targets), percent=attacker_percent,
        rounds_up=True, probe=probe, overrun=overrun)
    if defender_surrenders:
        defender_result = _surrender_result(
            side="defender", raw=d_raw, targets=tuple(defender_targets))
    else:
        defender_result = _side_result(
            side="defender", roll=defender_roll, raw=d_raw,
            targets=tuple(defender_targets), percent=defender_percent,
            rounds_up=overrun, probe=probe, overrun=overrun,
            captured_on_twenty=defender_captured_on_twenty)
    return CloseAssaultOutcome(attacker=attacker_result,
                               defender=defender_result, probe=probe,
                               overrun=overrun)


# ---------------------------------------------------------------------------
# 11.0 force assignment
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Assignment:
    """How one unit's TOE Points are split between the two assault roles."""

    unit_id: str
    anti_armor_toe: Fraction = Fraction(0)
    close_assault_toe: Fraction = Fraction(0)
    withheld_toe: Fraction = Fraction(0)

    def __post_init__(self) -> None:
        if not isinstance(self.unit_id, str) or not self.unit_id.strip():
            raise CombatError("unit_id must be a non-empty string")
        for name in ("anti_armor_toe", "close_assault_toe", "withheld_toe"):
            object.__setattr__(self, name,
                               _points(getattr(self, name), name=name))

    @property
    def committed(self) -> Fraction:
        return self.anti_armor_toe + self.close_assault_toe


def check_assignment(assignment: Assignment, unit: CombatUnit) -> None:
    """14.26: a TOE Strength Point may not serve both roles."""
    if assignment.unit_id != unit.unit_id:
        raise CombatError("assignment does not belong to that unit")
    if assignment.committed + assignment.withheld_toe > unit.toe_strength:
        raise CombatError(
            "14.26: assigned and withheld TOE Points may not exceed the "
            "unit's TOE Strength")
