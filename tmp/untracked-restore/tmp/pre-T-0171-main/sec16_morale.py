"""Patrols and reconnaissance, morale, and reserve status.

RULE: 16.11-16.55, 17.21-17.56, 18.11-18.26

Three small rule clusters that share one shape: a fixed rule procedure built
around a Charts-and-Tables value that is not in the vendored corpus.

* **Patrols (16)** detach TOE Strength Points as Patrol Points, cost supply,
  roll on the Patrol Survival Table, the Reconnaissance Table and the
  Objective Loss Table.  Those three tables are R-04 and are supplied by the
  caller; :func:`patrol_points_from_hex` and :func:`patrol_cost` implement the
  limits and the price, never a table entry.
* **Morale (17)** adjusts a Basic Morale Rating from the OA sheet by the
  unit's Cohesion Level through the Morale Modification Table (R-04).  The
  clamp, the Surrender column and the +1-morale exception are rule logic and
  live here.
* **Reserve (18)** is two statuses with movement and Capability Point
  consequences; no table is involved.

Every table used in the tests is explicitly synthetic and labelled as such.
Unit identities, ratings and map hexes are caller data (R-05, R-06).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Callable, Iterable, Sequence

RULE = "16.11-16.55, 17.21-17.56, 18.11-18.26"


class MoraleError(ValueError):
    """A patrol, morale or reserve input is not a valid §16-§18 position."""


def _points(value: Any, *, name: str = "points") -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise MoraleError(f"{name} must be an integer or Fraction")
    result = Fraction(value)
    if result < 0:
        raise MoraleError(f"{name} must not be negative")
    return result


def _whole(value: Any, *, name: str = "value", minimum: int | None = None,
           maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise MoraleError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise MoraleError(f"{name} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise MoraleError(f"{name} must be at most {maximum}")
    return value


def _bool(value: Any, *, name: str) -> bool:
    if not isinstance(value, bool):
        raise MoraleError(f"{name} must be a bool")
    return value


def _die(roll: int) -> int:
    return _whole(roll, name="roll", minimum=1, maximum=6)


# ---------------------------------------------------------------------------
# 16 Patrols and Reconnaissance
# ---------------------------------------------------------------------------

#: 16.11: the unit types that may supply Patrol Points.
PATROL_TYPES = frozenset({"recce", "light_tank", "motorized_infantry"})

#: 16.13: the most TOE Strength that may patrol from one hex.
PATROL_TOE_PER_HEX = Fraction(2)

#: 16.14: the most Patrol Points that may be sent to one hex.
PATROL_POINTS_PER_TARGET = Fraction(3)

#: 16.15: a unit at this Cohesion or worse may not patrol.
PATROL_COHESION_FLOOR = -8

#: 16.16: supply cost per Patrol Point.
PATROL_AMMO_PER_POINT = 1
PATROL_FUEL_PER_POINT = 2

#: 16.17: weather that forbids patrols.
STORMY_WEATHER = frozenset({"rainstorm", "sandstorm"})

#: 16.22: patrol range in hexes.
PATROL_RANGE = 5

#: 16.51: allowed error in a disclosed TOE Strength.
TOE_DISCLOSURE_SLACK = 2

#: 16.41-16.43: Dummy Tank limits.
DUMMY_MAX = 3
DUMMY_STORES = 10
DUMMY_CPA = 0


@dataclass(frozen=True)
class PatrolUnit:
    """One unit that might supply Patrol Points."""

    unit_id: str
    side: str
    hex_id: str
    unit_type: str = "other"
    toe_strength: Fraction = Fraction(0)
    cohesion: int = 0
    size: str = "battalion"
    kind: str = "combat"

    def __post_init__(self) -> None:
        for name in ("unit_id", "side", "hex_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise MoraleError(f"{name} must be a non-empty string")
        if not isinstance(self.unit_type, str) or not self.unit_type:
            raise MoraleError("unit_type must be a non-empty string")
        object.__setattr__(self, "toe_strength",
                           _points(self.toe_strength, name="toe_strength"))
        if isinstance(self.cohesion, bool) or not isinstance(self.cohesion, int):
            raise MoraleError("cohesion must be an integer")
        if self.size not in ("company", "battalion", "brigade", "division"):
            raise MoraleError(f"unknown unit size: {self.size!r}")
        if not isinstance(self.kind, str) or not self.kind:
            raise MoraleError("kind must be a non-empty string")


def may_supply_patrol_points(unit: PatrolUnit) -> tuple[bool, str]:
    """16.11, 16.15: only Recce, light tanks and motorized infantry."""
    if unit.unit_type not in PATROL_TYPES:
        return False, "16.11"
    if unit.cohesion <= PATROL_COHESION_FLOOR:
        return False, "16.15"
    if unit.toe_strength <= 0:
        return False, "16.12"
    return True, ""


def patrol_points_from_hex(units: Iterable[PatrolUnit]) -> Fraction:
    """16.13: eligible TOE Strength from one hex, capped at two."""
    available = sum((unit.toe_strength for unit in units
                     if may_supply_patrol_points(unit)[0]), Fraction(0))
    return min(available, PATROL_TOE_PER_HEX)


def patrol_cost(points: Fraction | int) -> tuple[int, int]:
    """16.16: one Ammunition and two Fuel Points per Patrol Point."""
    amount = _points(points, name="points")
    return (math.ceil(amount * PATROL_AMMO_PER_POINT),
            math.ceil(amount * PATROL_FUEL_PER_POINT))


def patrol_weather_allowed(origin_weather: str,
                           target_weather: str) -> bool:
    """16.17: no patrol may originate in or be directed into a storm."""
    for name, weather in (("origin_weather", origin_weather),
                          ("target_weather", target_weather)):
        if not isinstance(weather, str):
            raise MoraleError(f"{name} must be a string")
    return (origin_weather not in STORMY_WEATHER
            and target_weather not in STORMY_WEATHER)


def patrol_stage_allowed(*, anti_armor_or_close_assault: bool,
                         target_barraged: bool) -> tuple[bool, str]:
    """16.21: patrolling after a combat-free stage, but not into barraged hexes."""
    if not isinstance(anti_armor_or_close_assault, bool):
        raise MoraleError("anti_armor_or_close_assault must be a bool")
    if not isinstance(target_barraged, bool):
        raise MoraleError("target_barraged must be a bool")
    if anti_armor_or_close_assault:
        return False, "16.21"
    if target_barraged:
        return False, "16.21"
    return True, ""


def patrol_range_allowed(distance: int) -> bool:
    """16.22: an Enemy-occupied hex within five hexes."""
    return 0 < _whole(distance, name="distance") <= PATROL_RANGE


def patrol_path_allowed(path: Sequence[str], *, impassable: Iterable[str] = (),
                        enemy_units: Iterable[str] = (),
                        enemy_zoc: Iterable[str] = (),
                        target_hex: str) -> bool:
    """16.22: the five-hex path may not cross impassable or Enemy hexes.

    The target hex itself may be Enemy-occupied or controlled; every other
    hex on the path may not be.  The caller supplies the map facts (R-05).
    """
    if not isinstance(target_hex, str) or not target_hex.strip():
        raise MoraleError("target_hex must be a non-empty string")
    blocked = frozenset(impassable) | frozenset(enemy_units) | frozenset(enemy_zoc)
    for hex_id in path:
        if not isinstance(hex_id, str) or not hex_id.strip():
            raise MoraleError("a patrol path must contain non-empty hex ids")
        if hex_id in blocked and hex_id != target_hex:
            return False
    return True


@dataclass(frozen=True)
class PatrolRoll:
    """One row of a caller-supplied Patrol Survival or Objective Loss table."""

    lost: int = 0
    captured: int = 0

    def __post_init__(self) -> None:
        _whole(self.lost, name="lost", minimum=0)
        _whole(self.captured, name="captured", minimum=0)


PatrolSurvivalTable = Callable[[int, int], PatrolRoll]


@dataclass(frozen=True)
class PatrolSurvival:
    points: int
    roll: int
    lost: int
    captured: int
    remaining: int

    def to_obj(self) -> dict[str, Any]:
        return {"points": self.points, "roll": self.roll, "lost": self.lost,
                "captured": self.captured, "remaining": self.remaining,
                "rule": "16.33"}


def patrol_survival(*, points: int, roll: int, recce_only: bool,
                    combat_units_present: bool,
                    table: PatrolSurvivalTable) -> PatrolSurvival:
    """16.32-16.33: resolve a patrol's own losses.

    With no combat units in the hex the table is skipped and nothing is lost
    (16.32).  An all-Recce patrol subtracts one from the die (16.33).
    """
    amount = _whole(points, name="points", minimum=0)
    _bool(recce_only, name="recce_only")
    _bool(combat_units_present, name="combat_units_present")
    rolled = _die(roll)
    if not combat_units_present:
        return PatrolSurvival(points=amount, roll=rolled, lost=0,
                              captured=0, remaining=amount)
    used = max(1, rolled - 1) if recce_only else rolled
    outcome = table(used, amount)
    if not isinstance(outcome, PatrolRoll):
        raise MoraleError("the patrol table must return a PatrolRoll")
    lost = min(outcome.lost, amount)
    captured = min(outcome.captured, amount - lost)
    return PatrolSurvival(points=amount, roll=used, lost=lost,
                          captured=captured,
                          remaining=amount - lost - captured)


ReconnaissanceTable = Callable[[int, int], int]


def reconnaissance(points: int, roll: int,
                   table: ReconnaissanceTable) -> int:
    """16.5, 16.51: the number of battalion-sized units to disclose.

    ``points`` are the Patrol Points that survived 16.33; none surviving
    means no information at all.  The table itself is R-04.
    """
    amount = _whole(points, name="points", minimum=0)
    rolled = _die(roll)
    if amount == 0:
        return 0
    revealed = _whole(table(amount, rolled), name="revealed", minimum=0)
    return revealed


@dataclass(frozen=True)
class ObjectiveLoss:
    """16.34: losses inflicted on the non-Phasing Player."""

    eliminated: int = 0
    captured: int = 0

    def __post_init__(self) -> None:
        _whole(self.eliminated, name="eliminated", minimum=0)
        _whole(self.captured, name="captured", minimum=0)

    def to_obj(self) -> dict[str, Any]:
        return {"eliminated": self.eliminated, "captured": self.captured,
                "rule": "16.34"}


ObjectiveLossTable = Callable[[int], ObjectiveLoss]


def objective_losses(roll: int, *, patrol_eliminated: bool,
                     table: ObjectiveLossTable) -> ObjectiveLoss:
    """16.34: a wiped-out patrol turns a Captured result into an Eliminated."""
    _bool(patrol_eliminated, name="patrol_eliminated")
    outcome = table(_die(roll))
    if not isinstance(outcome, ObjectiveLoss):
        raise MoraleError("the objective loss table must return an ObjectiveLoss")
    if patrol_eliminated:
        return ObjectiveLoss(eliminated=outcome.eliminated + outcome.captured,
                             captured=0)
    return outcome


@dataclass(frozen=True)
class RevealedUnit:
    """16.51: the facts a patrol may learn about one unit."""

    designation: str
    unit_type: str
    motorized: bool
    toe_strength: Fraction
    kind: str = "combat"
    is_dummy: bool = False

    def to_obj(self) -> dict[str, Any]:
        return {"designation": self.designation, "unit_type": self.unit_type,
                "motorized": self.motorized,
                "toe_strength": str(self.toe_strength), "kind": self.kind,
                "is_dummy": self.is_dummy, "rule": "16.51"}


def toe_disclosure_valid(actual: Fraction | int,
                         reported: Fraction | int) -> bool:
    """16.51: the disclosed TOE Strength must be within two of the actual."""
    difference = abs(_points(actual, name="actual")
                     - _points(reported, name="reported"))
    return difference <= TOE_DISCLOSURE_SLACK


def revealable_units(units: Iterable[PatrolUnit], *,
                     excluded: Iterable[str] = ()) -> tuple[PatrolUnit, ...]:
    """16.53-16.55: who may be disclosed, and in what order.

    Battalion-sized units first (16.53); HQs and AA/Flak are disclosed only
    when no combat unit is present (16.54); the patrolling Player may exclude
    units he already knows about (16.55).
    """
    skip = frozenset(excluded)
    members = [unit for unit in units if unit.unit_id not in skip]
    combat = [unit for unit in members
              if unit.kind not in ("hq", "aa", "flak")]
    pool = combat or members
    order = {"battalion": 0, "brigade": 1, "division": 2, "company": 3}
    return tuple(sorted(pool, key=lambda unit: (order.get(unit.size, 4),
                                                  unit.unit_id)))


def reveal_information(units: Iterable[PatrolUnit], *, count: int,
                       excluded: Iterable[str] = ()) -> tuple[RevealedUnit, ...]:
    """16.5, 16.52: disclose up to *count* units."""
    amount = _whole(count, name="count", minimum=0)
    chosen = revealable_units(units, excluded=excluded)[:amount]
    return tuple(RevealedUnit(unit.unit_id, unit.unit_type, unit.unit_type
                              == "motorized_infantry", unit.toe_strength,
                              unit.kind)
                 for unit in chosen)


def dummy_placement_allowed(*, existing_dummies: int, stores: int,
                            italian: bool) -> tuple[bool, str]:
    """16.42-16.43: 10 Stores, at most three Dummies, never Italian."""
    _whole(existing_dummies, name="existing_dummies", minimum=0)
    _whole(stores, name="stores", minimum=0)
    _bool(italian, name="italian")
    if italian:
        return False, "16.43"
    if existing_dummies >= DUMMY_MAX:
        return False, "16.43"
    if stores < DUMMY_STORES:
        return False, "16.42"
    return True, ""


def dummy_eliminated(*, close_assault: bool,
                     anti_armor_without_armor: bool) -> bool:
    """16.46: a Dummy dies in any Close Assault or armour-less Anti-Armor fire."""
    _bool(close_assault, name="close_assault")
    _bool(anti_armor_without_armor, name="anti_armor_without_armor")
    return close_assault or anti_armor_without_armor


# ---------------------------------------------------------------------------
# 17 Morale
# ---------------------------------------------------------------------------

#: 17.23: the Adjusted Morale Rating floor and ceiling.
MORALE_MIN = -3
MORALE_MAX = 3

#: 17.24: Cohesion rows are clamped into this range.
MORALE_COHESION_FLOOR = -17
MORALE_COHESION_CEILING = 8

#: 17.26: what a Surrender column result becomes for a +1-or-better unit.
SURRENDER_AS_MODIFIER = -4

#: 17.26a: a unit at this Cohesion or worse never ignores Surrender.
SURRENDER_IGNORE_FLOOR = -11

#: 17.28: Rommel's additional adjustment.
ROMMEL_MORALE_BONUS = 1

#: 17.34: Operations Stages of Training per Morale point.
TRAINING_STAGES_PER_POINT = 6

#: 17.32: Commonwealth training areas named in the rule.
TRAINING_AREAS = frozenset({"cairo", "helwan", "alexandria", "amiriya",
                            "abougir", "deghelia"})

#: 17.54: CP the accepting Enemy unit must spend.
VOLUNTARY_SURRENDER_CP = 2


@dataclass(frozen=True)
class MoraleResult:
    basic: int
    cohesion: int
    row: int
    modifier: int
    adjusted: int
    surrendered: bool
    surrender_ignored: bool = False

    def to_obj(self) -> dict[str, Any]:
        return {"basic": self.basic, "cohesion": self.cohesion,
                "row": self.row, "modifier": self.modifier,
                "adjusted": self.adjusted, "surrendered": self.surrendered,
                "surrender_ignored": self.surrender_ignored,
                "rule": "17.22-17.28"}


def _sequential_dice(roll: int) -> int:
    """17.22: the Morale Modification Table reads two dice large-first."""
    value = _whole(roll, name="roll")
    if not (11 <= value <= 66) or not all(1 <= int(digit) <= 6
                                          for digit in str(value)):
        raise MoraleError("roll must be a sequential two-dice read-out (11..66)")
    return value


MoraleTable = Callable[[int, int], int | None]


def cohesion_row(cohesion: int) -> int:
    """17.24: clamp Cohesion into the table's rows."""
    value = _whole(cohesion, name="cohesion")
    return max(MORALE_COHESION_FLOOR, min(MORALE_COHESION_CEILING, value))


def adjusted_morale(*, basic: int, cohesion: int, roll: int,
                    table: MoraleTable, rommel: bool = False,
                    enemy_triple_raw: bool = False) -> MoraleResult:
    """17.21-17.28: Basic Morale adjusted by Cohesion for one Assault.

    ``table`` is the Morale Modification Table (R-04) and returns ``None``
    for the Surrender column.  A unit with Basic Morale +1 or better turns
    that into a -4 modifier (17.26) unless its Cohesion is -11 or worse or
    the Enemy has three times its Raw strength, and :data:`ROMMEL_MORALE_BONUS`
    is added after the normal clamp (17.28).
    """
    morale = _whole(basic, name="basic", minimum=MORALE_MIN, maximum=MORALE_MAX)
    row = cohesion_row(cohesion)
    rolled = _sequential_dice(roll)
    _bool(rommel, name="rommel")
    _bool(enemy_triple_raw, name="enemy_triple_raw")
    modifier = table(row, rolled)
    surrendered = modifier is None
    ignored = False
    if surrendered:
        may_ignore = (morale >= 1 and row > SURRENDER_IGNORE_FLOOR
                      and not enemy_triple_raw)
        if may_ignore:
            modifier = SURRENDER_AS_MODIFIER
            surrendered = False
            ignored = True
    value = modifier if modifier is not None else 0
    adjusted = max(MORALE_MIN, min(MORALE_MAX, morale + value))
    if rommel:
        adjusted += ROMMEL_MORALE_BONUS
    return MoraleResult(basic=morale, cohesion=cohesion, row=row,
                        modifier=value, adjusted=adjusted,
                        surrendered=surrendered, surrender_ignored=ignored)


def mutual_surrender(first: MoraleResult, second: MoraleResult) -> bool:
    """17.25: two Surrenders cancel, no assault occurs and both are Engaged."""
    return first.surrendered and second.surrendered


def largest_unit_cohesion(units: Iterable[PatrolUnit], *,
                          largest_id: str) -> int:
    """17.27 with 6.27: the Largest Unit Rule picks the Cohesion Level."""
    members = {unit.unit_id: unit for unit in units}
    try:
        return members[largest_id].cohesion
    except KeyError:
        raise MoraleError(f"no such unit: {largest_id!r}") from None


def training_progress(stages: int, *, untrained: int,
                      maximum: int) -> int:
    """17.34: one Morale point per six Operations Stages of Training."""
    completed = _whole(stages, name="stages", minimum=0)
    start = _whole(untrained, name="untrained", minimum=MORALE_MIN,
                   maximum=MORALE_MAX)
    ceiling = _whole(maximum, name="maximum", minimum=MORALE_MIN,
                     maximum=MORALE_MAX)
    if ceiling < start:
        raise MoraleError("maximum morale may not be below the untrained rating")
    gained = completed // TRAINING_STAGES_PER_POINT
    return min(ceiling, start + gained)


def training_continues(*, cp_spent: int) -> bool:
    """17.33: any CP expenditure interrupts Training."""
    return _whole(cp_spent, name="cp_spent", minimum=0) == 0


def training_instructor_ok(*, unit_has_tanks: bool, instructor_type: str,
                           instructor_morale: int, required_morale: int,
                           instructor_toe_ratio: Fraction | int) -> bool:
    """17.35: a qualified instructor battalion must be present."""
    _bool(unit_has_tanks, name="unit_has_tanks")
    if instructor_type not in ("infantry", "tank"):
        raise MoraleError(f"unknown instructor type: {instructor_type!r}")
    base = _whole(instructor_morale, name="instructor_morale",
                  minimum=MORALE_MIN, maximum=MORALE_MAX)
    required = _whole(required_morale, name="required_morale",
                      minimum=MORALE_MIN, maximum=MORALE_MAX)
    if base < required:
        return False
    wanted = "tank" if unit_has_tanks else "infantry"
    if instructor_type != wanted:
        return False
    return _points(instructor_toe_ratio, name="instructor_toe_ratio") >= Fraction(1, 4)


def voluntary_surrender_allowed(*, during_combat_steps: bool,
                                whole_hex: bool,
                                adjacent_enemy_combat: bool,
                                acceptor_cp_available: int) -> tuple[bool, str]:
    """17.52-17.54: when a Player may surrender units voluntarily."""
    for name, value in (("during_combat_steps", during_combat_steps),
                        ("whole_hex", whole_hex),
                        ("adjacent_enemy_combat", adjacent_enemy_combat)):
        _bool(value, name=name)
    available = _whole(acceptor_cp_available, name="acceptor_cp_available",
                       minimum=0)
    if during_combat_steps:
        return False, "17.52"
    if not whole_hex:
        return False, "17.52"
    if not adjacent_enemy_combat:
        return False, "17.52"
    if available < VOLUNTARY_SURRENDER_CP:
        return False, "17.54"
    return True, ""


def destruction_percent(roll: int, *, material: str) -> int:
    """17.56: (die - 1) x 10% for tanks and guns, x 20% for trucks."""
    if material not in ("tanks_guns", "trucks"):
        raise MoraleError(f"unknown material: {material!r}")
    value = _die(roll)
    factor = 10 if material == "tanks_guns" else 20
    return (value - 1) * factor


def destroyed_points(points: Fraction | int, percent: int) -> Fraction:
    """17.56: round the destroyed fraction down."""
    total = _points(points, name="points")
    share = _whole(percent, name="percent", minimum=0, maximum=100)
    return Fraction(math.floor(total * share / 100))


# ---------------------------------------------------------------------------
# 18 Reserve Status
# ---------------------------------------------------------------------------

RESERVE_I = "reserve_i"
RESERVE_II = "reserve_ii"
RESERVE_STATUSES = (RESERVE_I, RESERVE_II)

RESERVE_DESIGNATION_PHASE = "reserve_designation"


def may_designate_reserve(*, phasing: bool,
                          phase: str) -> tuple[bool, str]:
    """18.11, 18.15: Phasing units, Reserve Designation Phase only."""
    _bool(phasing, name="phasing")
    if not isinstance(phase, str) or not phase:
        raise MoraleError("phase must be a non-empty string")
    if phase != RESERVE_DESIGNATION_PHASE:
        return False, "18.15"
    if not phasing:
        return False, "18.11"
    return True, ""


def must_choose_first_release(status: str, *, release_segment: int) -> bool:
    """18.13: Reserve I must be released or flipped in the first release."""
    if status not in RESERVE_STATUSES:
        raise MoraleError(f"unknown reserve status: {status!r}")
    index = _whole(release_segment, name="release_segment", minimum=0)
    return status == RESERVE_I and index == 0


def reserve_movement_limit(status: str) -> int | None:
    """18.22: Reserve I moves one hex, Reserve II never moves."""
    if status == RESERVE_I:
        return 1
    if status == RESERVE_II:
        return 0
    raise MoraleError(f"unknown reserve status: {status!r}")


def reserve_move_allowed(*, status: str, destination_enemy_controlled: bool
                         ) -> tuple[bool, str]:
    """18.22: Reserve I may move one hex, but not into an Enemy ZOC."""
    _bool(destination_enemy_controlled, name="destination_enemy_controlled")
    if reserve_movement_limit(status) == 0:
        return False, "18.22"
    if destination_enemy_controlled:
        return False, "18.22"
    return True, ""


@dataclass(frozen=True)
class ReserveReleaseEffects:
    """18.23-18.25: what releasing a unit from Reserve costs it."""

    status: str
    cpa_fraction: Fraction
    offensive_close_assaults: int = 1
    disorganization_on_voluntary_combat: int = 0
    may_move_beyond_two_hexes: bool = True
    cp_cost: int = 0

    def to_obj(self) -> dict[str, Any]:
        return {"status": self.status, "cpa_fraction": str(self.cpa_fraction),
                "offensive_close_assaults": self.offensive_close_assaults,
                "disorganization_on_voluntary_combat":
                    self.disorganization_on_voluntary_combat,
                "may_move_beyond_two_hexes": self.may_move_beyond_two_hexes,
                "cp_cost": self.cp_cost, "rule": "18.23-18.26"}


def reserve_release_effects(status: str) -> ReserveReleaseEffects:
    """18.23-18.26: Reserve I is unrestricted, Reserve II is halved."""
    if status == RESERVE_I:
        return ReserveReleaseEffects(status=status, cpa_fraction=Fraction(1),
                                     disorganization_on_voluntary_combat=0)
    if status == RESERVE_II:
        return ReserveReleaseEffects(status=status, cpa_fraction=Fraction(1, 2),
                                     disorganization_on_voluntary_combat=1)
    raise MoraleError(f"unknown reserve status: {status!r}")


def reserve_cp_cap(base_cpa: int, status: str) -> int:
    """18.23-18.24: the CP cap for the rest of the Operations Stage."""
    base = _whole(base_cpa, name="base_cpa", minimum=0)
    effects = reserve_release_effects(status)
    return math.floor(base * effects.cpa_fraction)


def reserve_disorganization(status: str, *, voluntary_combat: bool) -> int:
    """18.24.3: Reserve II earns a Disorganization Point for voluntary combat."""
    _bool(voluntary_combat, name="voluntary_combat")
    effects = reserve_release_effects(status)
    return (effects.disorganization_on_voluntary_combat
            if voluntary_combat else 0)


def may_move_after_release(*, distance_to_enemy: int,
                           immediate_segment: bool) -> bool:
    """18.25: a released unit may move once even outside two hexes of an Enemy."""
    distance = _whole(distance_to_enemy, name="distance_to_enemy", minimum=0)
    _bool(immediate_segment, name="immediate_segment")
    return immediate_segment or distance <= 2
