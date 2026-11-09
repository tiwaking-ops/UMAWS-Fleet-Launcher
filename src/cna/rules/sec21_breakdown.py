"""Breakdown, repair, engineers, construction, fortifications and minefields.

RULE: 21.11-26.26

Every chart this block depends on is R-04 and remains caller-supplied:

* the Breakdown Table (21.38) and every vehicle's Breakdown Adjustment Rating
  that is not fixed in 21.14;
* the Broken Down Vehicle Repair Table and the Destroyed Tank Repair Table
  (22.8, 22.44);
* the Construction and Demolition Charts (24.17, 24.18);
* the Terrain Effects Chart's Breakdown Point Values and minefield entry costs
  (8.37).

The module implements the rule procedures around those tables: column shifts
and clamps, cumulative Breakdown Points, the single-point 10% exception,
stack/Parent-formation grouping and forced placement (21.28-21.29, 21.41),
supply costs, phase restrictions, structure levels and minefield effects.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Callable, Iterable, Mapping

RULE = "21.11-26.26"


class BreakdownError(ValueError):
    """A breakdown, repair, construction or minefield input is invalid."""


def _points(value: Any, *, name: str = "points") -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise BreakdownError(f"{name} must be an integer or Fraction")
    result = Fraction(value)
    if result < 0:
        raise BreakdownError(f"{name} must not be negative")
    return result


def _whole(value: Any, *, name: str = "value", minimum: int | None = None,
           maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BreakdownError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise BreakdownError(f"{name} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise BreakdownError(f"{name} must be at most {maximum}")
    return value


def _bool(value: Any, *, name: str) -> bool:
    if not isinstance(value, bool):
        raise BreakdownError(f"{name} must be a bool")
    return value


# ---------------------------------------------------------------------------
# 21 Breakdown
# ---------------------------------------------------------------------------

#: 21.11: the vehicle types subject to Breakdown.
BREAKDOWN_TYPES = frozenset({"truck", "tank", "recce", "armored_car", "sp_gun"})

#: 21.28: the three separate dice groups.
BREAKDOWN_GROUPS = {
    "truck": "trucks",
    "tank": "tanks_and_guns",
    "sp_gun": "tanks_and_guns",
    "recce": "armored_recce",
    "armored_car": "armored_recce",
}

#: 21.14: fixed Breakdown Adjustment Ratings; tanks and SP guns use their chart.
FIXED_BAR = {"truck": -2, "armored_car": -1, "recce": 0}

#: 21.31/21.38: the lower bound of each Breakdown Table column.
COLUMN_BOUNDS = (4, 11, 21, 31, 41, 51, 61, 71)

#: 21.27: no check until more than three points have accumulated.
BREAKDOWN_CHECK_MINIMUM = 3

#: 21.33: the floor column below which no Breakdown occurs.
BREAKDOWN_FLOOR = 4

WEATHER_SHIFTS = {"normal": 0, "hot": 1, "rainstorm": 0, "sandstorm": 0}


def breakdown_bar(vehicle_type: str, *, chart_bar: int | None = None) -> int:
    """21.12-21.14: the Breakdown Adjustment Rating in columns.

    Positive is right (worse), negative is left (better).  Tanks and SP guns
    have no fixed value and must supply the Tank & Gun Characteristics value.
    """
    if vehicle_type not in BREAKDOWN_TYPES:
        raise BreakdownError(f"not subject to Breakdown: {vehicle_type!r}")
    if vehicle_type in ("tank", "sp_gun"):
        if chart_bar is None:
            raise BreakdownError(
                "tank and SP gun BAR values come from their characteristics chart")
        return _whole(chart_bar, name="chart_bar", minimum=-2, maximum=2)
    return FIXED_BAR[vehicle_type]


def breakdown_group_type(vehicle_type: str) -> str:
    """21.28: the dice group one vehicle type is checked in."""
    try:
        return BREAKDOWN_GROUPS[vehicle_type]
    except KeyError:
        raise BreakdownError(
            f"not subject to Breakdown: {vehicle_type!r}") from None


def column_for(points: Fraction | int) -> int | None:
    """21.31, 21.33: the Breakdown column for accumulated points.

    Fractions round up (21.31); three or fewer points do not reach a column.
    """
    value = math.ceil(_points(points))
    if value <= BREAKDOWN_CHECK_MINIMUM:
        return None
    if value >= 71:
        return 71
    for bound in COLUMN_BOUNDS[1:]:
        if value < bound:
            return bound - 10 if bound != 11 else 4
    return 71


def weather_column_shift(weather: str, *,
                         sandstorm_majority: bool = False) -> int:
    """21.37: Hot is +1; Sandstorm is +1 only when most movement was in it."""
    if weather not in WEATHER_SHIFTS:
        raise BreakdownError(f"unknown weather: {weather!r}")
    _bool(sandstorm_majority, name="sandstorm_majority")
    if weather == "hot":
        return 1
    if weather == "sandstorm":
        return 1 if sandstorm_majority else 0
    return 0


def breakdown_column(points: Fraction | int, *, bar: int = 0,
                     weather: str = "normal",
                     sandstorm_majority: bool = False) -> int | None:
    """21.32-21.33: apply BAR and weather column shifts, clamped to the table."""
    base = column_for(points)
    if base is None:
        return None
    shift = _whole(bar, name="bar", minimum=-2, maximum=2)
    shift += weather_column_shift(weather,
                                  sandstorm_majority=sandstorm_majority)
    index = COLUMN_BOUNDS.index(base) + shift
    if index < 0:
        return None                                              # 21.33
    index = min(index, len(COLUMN_BOUNDS) - 1)
    return COLUMN_BOUNDS[index]


def breakdown_check_required(points: Fraction | int, *,
                             last_column: int | None,
                             bar: int = 0, weather: str = "normal",
                             sandstorm_majority: bool = False
                             ) -> tuple[bool, int | None]:
    """21.24-21.27: check when stopping, but only in a higher column."""
    column = breakdown_column(points, bar=bar, weather=weather,
                              sandstorm_majority=sandstorm_majority)
    if column is None:
        return False, None
    if last_column is None:
        return True, column
    if column > last_column:
        return True, column
    return False, column


@dataclass(frozen=True)
class BreakdownTrack:
    """21.25: Breakdown Points accumulate for the whole Operations Stage."""

    points: Fraction = Fraction(0)
    last_column: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "points", _points(self.points))
        if self.last_column is not None:
            _whole(self.last_column, name="last_column", minimum=0)

    def accumulate(self, points: Fraction | int) -> "BreakdownTrack":
        return BreakdownTrack(self.points + _points(points), self.last_column)

    def check(self, *, bar: int = 0, weather: str = "normal",
              sandstorm_majority: bool = False
              ) -> tuple[bool, "BreakdownTrack"]:
        """21.24-21.26: return whether a roll is due, and the new track."""
        required, column = breakdown_check_required(
            self.points, last_column=self.last_column, bar=bar,
            weather=weather, sandstorm_majority=sandstorm_majority)
        if not required:
            return False, self
        return True, BreakdownTrack(self.points, column)


@dataclass(frozen=True)
class BreakdownCheck:
    """The result of one stop-and-check (21.24-21.27, 21.34-21.35).

    ``last_column`` is the column the unit has checked in this Operations
    Stage.  It advances only after the check has actually been resolved;
    an unresolved check therefore stays due at the next stop.
    """

    points: Fraction
    column: int | None
    required: bool
    last_column: int | None
    suppressed: bool = False
    resolved: bool = False
    percent: int | None = None
    losses: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "points", _points(self.points))
        if self.column is not None and self.column not in COLUMN_BOUNDS:
            raise BreakdownError(f"not a Breakdown column: {self.column!r}")
        if self.last_column is not None:
            _whole(self.last_column, name="last_column", minimum=0)
        for name in ("required", "suppressed", "resolved"):
            _bool(getattr(self, name), name=name)
        if self.resolved and not self.required:
            raise BreakdownError("only a required check can be resolved")
        if self.percent is not None:
            _whole(self.percent, name="percent", minimum=0, maximum=100)
        if self.losses is not None:
            _whole(self.losses, name="losses", minimum=0)

    @property
    def pending(self) -> bool:
        """A check is due but has not had its dice/table applied."""
        return self.required and not self.resolved

    def to_obj(self) -> dict[str, Any]:
        return {
            "points": str(self.points),
            "column": self.column,
            "required": self.required,
            "last_column": self.last_column,
            "suppressed": self.suppressed,
            "resolved": self.resolved,
            "pending": self.pending,
            "percent": self.percent,
            "losses": self.losses,
            "rule": "21.24-21.27, 21.34-21.35",
        }


def breakdown_percent(roll: int, column: int,
                      table: Callable[[int, int], int]) -> int:
    """21.34-21.35: two sequential dice on the caller's Breakdown Table."""
    value = _whole(roll, name="roll")
    if not (11 <= value <= 66) or not all(1 <= int(d) <= 6 for d in str(value)):
        raise BreakdownError("roll must be a sequential two-dice read-out")
    if column not in COLUMN_BOUNDS:
        raise BreakdownError(f"not a Breakdown column: {column!r}")
    percent = _whole(table(value, column), name="percent", minimum=0,
                     maximum=100)
    return percent


def losses_from_percent(percent: int, toe_points: Fraction | int) -> int:
    """21.35: round up, except a single TOE Point ignores a 10% result."""
    share = _whole(percent, name="percent", minimum=0, maximum=100)
    points = _points(toe_points, name="toe_points")
    if points == 1 and share == 10:
        return 0
    return math.ceil(points * share / 100)


def evaluate_breakdown(points: Fraction | int, *, last_column: int | None,
                       bar: int = 0, weather: str = "normal",
                       sandstorm_majority: bool = False,
                       suppressed: bool = False,
                       roll: int | None = None,
                       table: Callable[[int, int], int] | None = None,
                       toe_points: Fraction | int | None = None
                       ) -> BreakdownCheck:
    """21.24-21.27, 21.34-21.35: decide and optionally resolve one check.

    The caller supplies the two-dice read-out and the Breakdown Table; this
    function supplies the cumulative points, the column shifts, the 21.26
    higher-column rule and the 21.35 loss rounding.  If the dice are not
    supplied the check is reported as pending and ``last_column`` does not
    move, so the same check remains due at the next stop.
    """
    total = _points(points)
    if last_column is not None:
        _whole(last_column, name="last_column", minimum=0)
    _bool(suppressed, name="suppressed")
    if (roll is None) != (table is None):
        raise BreakdownError("roll and table must be supplied together")
    if table is not None and not callable(table):
        raise BreakdownError("table must be callable")
    if toe_points is not None:
        _points(toe_points, name="toe_points")

    if suppressed:
        return BreakdownCheck(total, None, False, last_column,
                              suppressed=True)

    required, column = breakdown_check_required(
        total, last_column=last_column, bar=bar, weather=weather,
        sandstorm_majority=sandstorm_majority)
    if not required:
        return BreakdownCheck(total, column, False, last_column)

    percent = losses = None
    resolved = False
    if roll is not None:
        percent = breakdown_percent(roll, column, table)
        resolved = True
        if toe_points is not None:
            losses = losses_from_percent(percent, toe_points)
    return BreakdownCheck(total, column, True,
                          column if resolved else last_column,
                          resolved=resolved, percent=percent, losses=losses)


def distribute_evenly(total: int, *, groups: int) -> tuple[int, ...]:
    """21.36: spread Breakdowns proportionally and evenly."""
    amount = _whole(total, name="total", minimum=0)
    count = _whole(groups, name="groups", minimum=1)
    base, remainder = divmod(amount, count)
    return tuple(base + (1 if index < remainder else 0)
                 for index in range(count))


def forced_breakdown_share(*, near_enemy_battalion: bool) -> Fraction:
    """21.41: half the broken-down points stay at the starting hex."""
    return Fraction(1, 2) if _bool(near_enemy_battalion,
                                   name="near_enemy_battalion") else Fraction(0)


@dataclass(frozen=True)
class BreakdownPlacement:
    """21.41: where one unit's broken-down points are placed."""

    start_hex: str
    stop_hex: str
    at_start: int
    at_stop: int

    def __post_init__(self) -> None:
        for name in ("start_hex", "stop_hex"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise BreakdownError(f"{name} must be a non-empty string")
        _whole(self.at_start, name="at_start", minimum=0)
        _whole(self.at_stop, name="at_stop", minimum=0)

    @property
    def total(self) -> int:
        return self.at_start + self.at_stop


def forced_breakdown_placement(losses: int, *, start_hex: str,
                               stop_hex: str,
                               near_enemy_battalion: bool
                               ) -> BreakdownPlacement:
    """21.41: at least half the losses stay in the starting hex."""
    count = _whole(losses, name="losses", minimum=0)
    _bool(near_enemy_battalion, name="near_enemy_battalion")
    at_start = math.ceil(count * forced_breakdown_share(
        near_enemy_battalion=near_enemy_battalion))
    if start_hex == stop_hex:
        return BreakdownPlacement(start_hex, stop_hex, 0, count)
    return BreakdownPlacement(start_hex, stop_hex, at_start,
                              count - at_start)


# ---------------------------------------------------------------------------
# 21.28-21.29 stack and Parent-formation grouping
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BreakdownUnit:
    """One vehicle in the stack or Parent formation being checked.

    ``toe_points`` is TOE Strength Points, or Truck Points for a truck unit
    (21.35).  ``bar`` defaults to the fixed 21.14 rating and must be supplied
    from the vehicle chart for tanks and SP guns.
    """

    unit_id: str
    vehicle_type: str
    toe_points: Fraction | int
    breakdown_points: Fraction | int = Fraction(0)
    breakdown_last_column: int | None = None
    parent_id: str | None = None
    bar: int | None = None
    start_hex: str = ""
    stop_hex: str = ""
    near_enemy_battalion: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.unit_id, str) or not self.unit_id.strip():
            raise BreakdownError("unit_id must be a non-empty string")
        if self.vehicle_type not in BREAKDOWN_TYPES:
            raise BreakdownError(
                f"not subject to Breakdown: {self.vehicle_type!r}")
        object.__setattr__(self, "toe_points",
                           _points(self.toe_points, name="toe_points"))
        object.__setattr__(self, "breakdown_points",
                           _points(self.breakdown_points,
                                   name="breakdown_points"))
        if self.breakdown_last_column is not None:
            _whole(self.breakdown_last_column,
                   name="breakdown_last_column", minimum=0)
        if self.parent_id is not None and (
                not isinstance(self.parent_id, str)
                or not self.parent_id.strip()):
            raise BreakdownError(
                "parent_id must be a non-empty string or None")
        if self.bar is None:
            if self.vehicle_type in ("tank", "sp_gun"):
                raise BreakdownError(
                    "tank and SP gun BAR values come from their "
                    "characteristics chart")
            bar = FIXED_BAR[self.vehicle_type]
        else:
            bar = _whole(self.bar, name="bar", minimum=-2, maximum=2)
        object.__setattr__(self, "bar", bar)
        for name in ("start_hex", "stop_hex"):
            if not isinstance(getattr(self, name), str):
                raise BreakdownError(f"{name} must be a string")
        _bool(self.near_enemy_battalion, name="near_enemy_battalion")


@dataclass(frozen=True)
class BreakdownGroup:
    """One 21.28/21.29 dice group.

    Units share a Parent Formation, a 21.28 type, the same tank/gun BAR when
    that rating splits the group, and the same Breakdown Point column
    (21.29).  ``bar`` is the rating that split a tank/gun group, or ``None``
    when the group is not split by BAR.
    """

    unit_type: str
    parent_id: str | None
    bar: int | None
    column: int
    members: tuple[BreakdownUnit, ...]

    def __post_init__(self) -> None:
        if self.unit_type not in set(BREAKDOWN_GROUPS.values()):
            raise BreakdownError(
                f"unknown Breakdown group: {self.unit_type!r}")
        if self.parent_id is not None and (
                not isinstance(self.parent_id, str)
                or not self.parent_id.strip()):
            raise BreakdownError(
                "parent_id must be a non-empty string or None")
        if self.bar is not None:
            _whole(self.bar, name="bar", minimum=-2, maximum=2)
        if self.unit_type == "tanks_and_guns" and self.bar is None:
            raise BreakdownError("a tank/gun group needs its BAR")
        if self.column not in COLUMN_BOUNDS:
            raise BreakdownError(
                f"not a Breakdown column: {self.column!r}")
        members = tuple(self.members)
        if not members:
            raise BreakdownError("a Breakdown group needs at least one unit")
        for member in members:
            if not isinstance(member, BreakdownUnit):
                raise BreakdownError(
                    "a Breakdown group member must be a BreakdownUnit")
            if breakdown_group_type(member.vehicle_type) != self.unit_type:
                raise BreakdownError(
                    "a Breakdown group mixes 21.28 unit types")
            if (self.unit_type == "tanks_and_guns"
                    and member.bar != self.bar):
                raise BreakdownError(
                    "a tank/gun group mixes Breakdown Adjustment Ratings")
        object.__setattr__(self, "members", members)

    @property
    def unit_ids(self) -> tuple[str, ...]:
        return tuple(member.unit_id for member in self.members)

    @property
    def toe_points(self) -> Fraction:
        return sum((member.toe_points for member in self.members),
                   Fraction(0))


def group_breakdown_units(units: Iterable[BreakdownUnit], *,
                          weather: str = "normal",
                          sandstorm_majority: bool = False
                          ) -> tuple[BreakdownGroup, ...]:
    """21.28-21.29: group the checks due in one stack by separate dice roll.

    Only units whose 21.24 check is due are grouped; a unit that has not
    reached a higher column does not join a group or consume a roll.
    """
    if weather not in WEATHER_SHIFTS:
        raise BreakdownError(f"unknown weather: {weather!r}")
    _bool(sandstorm_majority, name="sandstorm_majority")
    ordered: list[BreakdownUnit] = []
    for unit in units:
        if not isinstance(unit, BreakdownUnit):
            raise BreakdownError("units must be BreakdownUnit instances")
        ordered.append(unit)
    ordered.sort(key=lambda unit: (
        unit.parent_id or "", breakdown_group_type(unit.vehicle_type),
        unit.unit_id))
    buckets: dict[tuple[Any, ...], list[BreakdownUnit]] = {}
    for unit in ordered:
        unit_type = breakdown_group_type(unit.vehicle_type)
        required, column = breakdown_check_required(
            unit.breakdown_points,
            last_column=unit.breakdown_last_column,
            bar=unit.bar, weather=weather,
            sandstorm_majority=sandstorm_majority)
        if not required or column is None:
            continue
        key = (unit.parent_id, unit_type,
               unit.bar if unit_type == "tanks_and_guns" else None,
               column)
        buckets.setdefault(key, []).append(unit)
    return tuple(
        BreakdownGroup(unit_type=key[1], parent_id=key[0], bar=key[2],
                       column=key[3], members=tuple(bucket))
        for key, bucket in buckets.items()
    )


@dataclass(frozen=True)
class BreakdownShare:
    """One unit's share of a group's 21.35 losses and its 21.41 placement."""

    unit_id: str
    losses: int
    placement: BreakdownPlacement

    def __post_init__(self) -> None:
        if not isinstance(self.unit_id, str) or not self.unit_id.strip():
            raise BreakdownError("unit_id must be a non-empty string")
        _whole(self.losses, name="losses", minimum=0)
        if not isinstance(self.placement, BreakdownPlacement):
            raise BreakdownError(
                "placement must be a BreakdownPlacement")


@dataclass(frozen=True)
class BreakdownGroupResult:
    """One group's 21.28/21.29 dice roll and its distributed losses."""

    group: BreakdownGroup
    roll: int
    percent: int
    losses: int
    shares: tuple[BreakdownShare, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.group, BreakdownGroup):
            raise BreakdownError("group must be a BreakdownGroup")
        _whole(self.roll, name="roll")
        _whole(self.percent, name="percent", minimum=0, maximum=100)
        _whole(self.losses, name="losses", minimum=0)
        shares = tuple(self.shares)
        if len(shares) != len(self.group.members):
            raise BreakdownError(
                "each group member needs exactly one loss share")
        if sum(share.losses for share in shares) != self.losses:
            raise BreakdownError(
                "loss shares must add up to the group losses")
        object.__setattr__(self, "shares", shares)


def resolve_breakdown_group(group: BreakdownGroup, *, roll: int,
                            table: Callable[[int, int], int]
                            ) -> BreakdownGroupResult:
    """21.28-21.29, 21.34-21.36, 21.41: one roll for one group."""
    if not isinstance(group, BreakdownGroup):
        raise BreakdownError("group must be a BreakdownGroup")
    percent = breakdown_percent(roll, group.column, table)
    losses = losses_from_percent(percent, group.toe_points)
    shares = distribute_evenly(losses, groups=len(group.members))
    results = tuple(
        BreakdownShare(
            member.unit_id, share,
            forced_breakdown_placement(
                share, start_hex=member.start_hex,
                stop_hex=member.stop_hex,
                near_enemy_battalion=member.near_enemy_battalion))
        for member, share in zip(group.members, shares)
    )
    return BreakdownGroupResult(group, roll, percent, losses, results)


def breakdown_check_suppressed(off_map_box: bool) -> bool:
    """21.15: no Breakdown checks in the Tripoli/Tunisia boxes."""
    return _bool(off_map_box, name="off_map_box")


def broken_down_capabilities() -> dict[str, bool]:
    """21.44: no Capability Points and no combat participation."""
    return {"capability_points": False, "combat": False}


def truck_cargo_transfer_cp() -> int:
    """21.45: transferring supplies to working trucks costs 2 CP."""
    return 2


def dismount_cp() -> int:
    """21.45: infantry may dismount a broken-down truck for 1 CP."""
    return 1


def vehicle_capture_allowed(*, adjacent_friendly_battalion: bool,
                            stacked_friendly: bool,
                            friendly_controlled_hex: bool,
                            passable_hexside: bool) -> bool:
    """21.52-21.54: capture by an adjacent battalion of the same side."""
    for name, value in (("adjacent_friendly_battalion",
                         adjacent_friendly_battalion),
                        ("stacked_friendly", stacked_friendly),
                        ("friendly_controlled_hex", friendly_controlled_hex),
                        ("passable_hexside", passable_hexside)):
        _bool(value, name=name)
    if stacked_friendly or friendly_controlled_hex:
        return False
    return adjacent_friendly_battalion and passable_hexside


def capture_tow_hexes() -> int:
    """21.55: a captured vehicle may be placed up to three hexes away."""
    return 3


def towing_allowed(*, in_enemy_controlled: bool, at_capture: bool = False,
                   failed_field_repair: bool = False) -> bool:
    """21.62-21.66: when a marker may be towed."""
    _bool(in_enemy_controlled, name="in_enemy_controlled")
    _bool(at_capture, name="at_capture")
    _bool(failed_field_repair, name="failed_field_repair")
    if failed_field_repair:
        return False
    return (not in_enemy_controlled) or at_capture


def towing_cp_per_repair_phase() -> int:
    """21.63: a marker tows as a Medium Truck for 10 CP per Repair Phase."""
    return 10


def towing_supply_cost() -> tuple[int, int, int]:
    """21.65: no Fuel, Stores or Water is spent to tow."""
    return 0, 0, 0


def tow_direction_ok(*, towards_nearest_facility: bool) -> bool:
    """21.67: towing must head for the nearest Temporary or Major Facility."""
    return _bool(towards_nearest_facility, name="towards_nearest_facility")


# ---------------------------------------------------------------------------
# 22 Repair
# ---------------------------------------------------------------------------

STORMY_WEATHER = frozenset({"rainstorm", "sandstorm"})

#: 22.31: the four Major Repair Facilities.
MAJOR_REPAIR_FACILITIES = ("tripoli", "tobruk", "alexandria", "cairo")

#: 22.42: supplies per destroyed tank TOE Point attempted.
DESTROYED_TANK_STORES = 2
DESTROYED_TANK_FUEL = 2

#: 22.35: supplies per broken-down point repaired at a facility.
FACILITY_STORES_PER_POINT = 1
FACILITY_FUEL_PER_POINT = 1


def repair_phase_allowed(phase: str) -> bool:
    """22.12: repairs happen in the Repair Phase, Phasing Player only."""
    return phase == "repair"


def repair_control_required(*, controls_vehicle: bool) -> bool:
    """22.11: any controlled broken-down vehicle or destroyed tank."""
    return _bool(controls_vehicle, name="controls_vehicle")


def repair_weather_allowed(*, weather: str, major_facility: bool) -> bool:
    """22.13d, 22.36: storms stop temporary facilities and field repairs."""
    if weather not in WEATHER_SHIFTS:
        raise BreakdownError(f"unknown weather: {weather!r}")
    return major_facility or weather not in STORMY_WEATHER


def field_repair_allowed(*, destroyed: bool, stacked_friendly: bool,
                         towed_this_phase: bool) -> bool:
    """22.21-22.22: broken-down vehicles only, with a friendly unit present."""
    _bool(destroyed, name="destroyed")
    return (not destroyed and _bool(stacked_friendly,
                                    name="stacked_friendly")
            and not _bool(towed_this_phase, name="towed_this_phase"))


def field_truck_repair(roll: int, *, heavy: bool = False) -> int:
    """22.23: roll 1 fixes two light/medium or one heavy; roll 2 fixes one."""
    value = _whole(roll, name="roll", minimum=1, maximum=6)
    _bool(heavy, name="heavy")
    if value == 1:
        return 1 if heavy else 2
    if value == 2 and not heavy:
        return 1
    return 0


def field_recce_repair(roll: int) -> int:
    """22.24: armored car and Recce points repair on a roll of 1."""
    return 1 if _whole(roll, name="roll", minimum=1, maximum=6) == 1 else 0


def field_tank_repair(percent: int, toe_points: Fraction | int) -> int:
    """22.25: field-repaired tank percentage, rounding up."""
    share = _whole(percent, name="percent", minimum=0, maximum=100)
    points = _points(toe_points, name="toe_points")
    if points == 1 and share == 10:
        return 0
    return math.ceil(points * share / 100)


def field_tank_fuel_cost(points: Fraction | int) -> int:
    """22.26: one Fuel Point per tank TOE Point attempted."""
    return math.ceil(_points(points, name="points"))


def facility_repair_allowed(*, facility: str, in_enemy_zoc: bool,
                            in_major_city: bool, neutralized: bool) -> bool:
    """22.13a, 22.37: temporary facilities fail in an Enemy ZOC."""
    if facility not in ("temporary", "major"):
        raise BreakdownError(f"unknown facility: {facility!r}")
    if _bool(neutralized, name="neutralized"):
        return False
    if facility == "major":
        return True
    return not _bool(in_enemy_zoc, name="in_enemy_zoc") or _bool(
        in_major_city, name="in_major_city")


def facility_repair_modifier(*, reduced_levels: int) -> int:
    """22.34a: bombing adds +1 for one level, +2 for two or three."""
    levels = _whole(reduced_levels, name="reduced_levels", minimum=0)
    if levels <= 0:
        return 0
    return 1 if levels == 1 else 2


def facility_supply_cost(points: Fraction | int) -> tuple[int, int]:
    """22.35: one Store and one Fuel per point repaired."""
    count = math.ceil(_points(points, name="points"))
    return (count * FACILITY_STORES_PER_POINT,
            count * FACILITY_FUEL_PER_POINT)


def destroyed_tank_supply_cost(points: int) -> tuple[int, int]:
    """22.42: two Stores and two Fuel per destroyed tank point, prepaid."""
    count = _whole(points, name="points", minimum=0)
    return (count * DESTROYED_TANK_STORES, count * DESTROYED_TANK_FUEL)


def facility_repair_scope(*, destroyed: bool) -> str:
    """22.21, 22.41: destroyed tanks are facility-only, field is broken-down."""
    return "facility" if _bool(destroyed, name="destroyed") else "field_or_facility"


def destroyed_tank_repair(roll: int,
                          table: Callable[[int], str]) -> str:
    """22.43-22.44: one die per point on the caller's Destroyed Tank table."""
    value = _whole(roll, name="roll", minimum=1, maximum=6)
    outcome = table(value)
    if outcome not in ("repaired", "junked", "retry"):
        raise BreakdownError(
            "the destroyed tank table must return repaired, junked or retry")
    return outcome


def repaired_vehicle_training_required() -> bool:
    """22.5: repaired vehicles are Replacement Points but need no Training."""
    return False


def tds_field_repair_modifier() -> int:
    """22.62: a Tank Delivery Squadron subtracts one from the field die."""
    return -1


def tds_destroyed_tank_success() -> int:
    """22.62: a TDS repairs a destroyed Commonwealth tank on a 1."""
    return 1


def tds_characteristics() -> dict[str, int]:
    """22.63-22.65: CPA 25, three reserve points, towing at 20 CP."""
    return {"cpa": 25, "reserves": 3, "tow_cp": 20, "tow_capacity": 3}


def tds_elimination_return_turns() -> int:
    """22.63: an eliminated TDS returns eight Game-Turns later."""
    return 8


# ---------------------------------------------------------------------------
# 23 Engineers
# ---------------------------------------------------------------------------

ENGINEER_MINE_CP = {True: 6, False: 3}      # 23.21 by motorization


def minefield_entry_cp(*, motorized: bool,
                       engineer_present: bool) -> int | None:
    """23.21: 6 CP motorized, 3 CP non-motorized with an Engineer present."""
    _bool(motorized, name="motorized")
    if not _bool(engineer_present, name="engineer_present"):
        return None
    return ENGINEER_MINE_CP[motorized]


def minefield_removal_allowed(*, full_stage: bool,
                              cp_spent: int) -> bool:
    """23.22, 26.13: a full Stage in the hex with no CP expenditure."""
    return _bool(full_stage, name="full_stage") and _whole(
        cp_spent, name="cp_spent", minimum=0) == 0


def engineer_assault_column_bonus(*, unpinned_engineer_battalion: bool,
                                  fortified: bool,
                                  major_city: bool) -> int:
    """23.24: one column against a fortified hex, but not a Major City."""
    _bool(unpinned_engineer_battalion, name="unpinned_engineer_battalion")
    _bool(fortified, name="fortified")
    _bool(major_city, name="major_city")
    if unpinned_engineer_battalion and fortified and not major_city:
        return 1
    return 0


def engineer_can_build_bridges() -> bool:
    """23.26: Engineers do not build bridges or affect escarpments."""
    return False


# ---------------------------------------------------------------------------
# 24 Construction
# ---------------------------------------------------------------------------

#: 24.31-24.34: minefield construction costs.
REAL_MINEFIELD_COST = (15, 15)
DUMMY_MINEFIELD_COST = (3, 0)

#: 24.35: where a minefield may be laid.
MINEFIELD_TERRAIN = frozenset({"clear", "sand_gravel", "rough"})

#: 24.42-24.43: fortification requirements.
FORTIFICATION_STAGES = 3
FORTIFICATION_INFANTRY_TOE = Fraction(3)
FORTIFICATION_STORES = 30

#: 24.44: terrain where new fortifications may not be built.
FORTIFICATION_BANNED_TERRAIN = frozenset({"mountain", "salt_marsh", "desert",
                                          "major_city", "delta"})

#: 24.82-24.86: temporary repair facility costs.
TEMPORARY_REPAIR_STORES = 250
TEMPORARY_REPAIR_FUEL = 150
TEMPORARY_REPAIR_STAGES = 3
TEMPORARY_REPAIR_LIMIT = 2
TEMPORARY_REPAIR_DISMANTLE_RETURNS = (120, 25)

#: 24.84: rebuilding a Major City's repair facility.
MAJOR_REPAIR_REBUILD_COST = (50, 30)


def construction_stage_counts(*, cp_spent: int, storm: bool,
                              pinned: bool) -> bool:
    """24.12, 24.22-24.23: a Stage counts only without CP, storm or pinning."""
    return (_whole(cp_spent, name="cp_spent", minimum=0) == 0
            and not _bool(storm, name="storm")
            and not _bool(pinned, name="pinned"))


def construction_completion_stage(*, start_stage: int, stages: int) -> int:
    """24.11: stages include the starting Stage; completion is the next one."""
    start = _whole(start_stage, name="start_stage", minimum=1)
    count = _whole(stages, name="stages", minimum=1)
    return start + count


def hot_water_cost(weather: str) -> int:
    """24.21: each construction site needs 10 Water in Hot weather."""
    if weather not in WEATHER_SHIFTS:
        raise BreakdownError(f"unknown weather: {weather!r}")
    return 10 if weather == "hot" else 0


def construction_supplies_ok(*, stores: int, ammo: int, fuel: int,
                             water: int, required_stores: int,
                             required_ammo: int = 0, required_fuel: int = 0,
                             required_water: int = 0) -> bool:
    """24.13: supplies must be present and are spent whether or not completed."""
    pairs = ((stores, required_stores), (ammo, required_ammo),
             (fuel, required_fuel), (water, required_water))
    return all(_whole(value, name="supply", minimum=0)
               >= _whole(need, name="need", minimum=0)
               for value, need in pairs)


def minefield_construction(*, dummy: bool, terrain: str,
                           enemy_controlled: bool, major_city: bool,
                           existing_minefield: bool) -> tuple[bool, str]:
    """24.31-24.36: one OpStage, one minefield per legal hex."""
    _bool(dummy, name="dummy")
    _bool(enemy_controlled, name="enemy_controlled")
    _bool(major_city, name="major_city")
    _bool(existing_minefield, name="existing_minefield")
    if terrain not in MINEFIELD_TERRAIN:
        return False, "24.35"
    if major_city:
        return False, "24.35"
    if enemy_controlled:
        return False, "24.36"
    if existing_minefield:
        return False, "24.35"
    return True, ""


def minefield_construction_cost(*, dummy: bool) -> tuple[int, int]:
    """24.33-24.34: 15 Stores and 15 Ammunition, or 3 Stores for a dummy."""
    _bool(dummy, name="dummy")
    return DUMMY_MINEFIELD_COST if dummy else REAL_MINEFIELD_COST


def fortification_allowed(*, engineer_present: bool, infantry_toe: Fraction | int,
                          terrain: str, enemy_zoc: bool,
                          stores: int) -> tuple[bool, str]:
    """24.42-24.45: engineer, 3-TOE infantry battalion, terrain and 30 Stores."""
    _bool(engineer_present, name="engineer_present")
    _bool(enemy_zoc, name="enemy_zoc")
    if not engineer_present:
        return False, "24.42"
    if _points(infantry_toe, name="infantry_toe") < FORTIFICATION_INFANTRY_TOE:
        return False, "24.42"
    if terrain in FORTIFICATION_BANNED_TERRAIN:
        return False, "24.44"
    if enemy_zoc:
        return False, "24.44"
    if _whole(stores, name="stores", minimum=0) < FORTIFICATION_STORES:
        return False, "24.43"
    return True, ""


def fortification_rebuild_in_zoc_allowed() -> bool:
    """24.45: rebuilding a destroyed Level may occur in an Enemy ZOC."""
    return True


def road_build_capacity(*, infantry_toe: Fraction | int = 0,
                        engineer_company: bool = False,
                        engineer_battalion: bool = False) -> int:
    """24.53: one hex, one hex, or three hexes depending on the unit."""
    toe = _points(infantry_toe, name="infantry_toe")
    if _bool(engineer_battalion, name="engineer_battalion"):
        return 3
    if _bool(engineer_company, name="engineer_company"):
        return 1
    if toe >= 3:
        return 1
    return 0


def road_build_cost(hexes: int) -> int:
    """24.54: two Stores per road hex."""
    return 2 * _whole(hexes, name="hexes", minimum=0)


def railroad_build_stages(*, nzrrc_companies: int) -> int | None:
    """24.61-24.62: one company two Stages, two companies one Stage."""
    count = _whole(nzrrc_companies, name="nzrrc_companies", minimum=0)
    if count <= 0:
        return None
    return 2 if count == 1 else 1


def railroad_rebuild_limit() -> int:
    """24.63: three destroyed railroad hexes per Construction Segment."""
    return 3


def railroad_rebuild_stores(hexes: int) -> int:
    """24.64: one Store per railroad hex rebuilt."""
    return _whole(hexes, name="hexes", minimum=0)


def air_facility_construction(*, kind: str, engineer_battalion: bool,
                              engineer_company: bool = False,
                              squadron_ground_support: bool = False,
                              terrain: str = "clear", coastal: bool = False,
                              enemy_controlled: bool = False
                              ) -> tuple[bool, str, int]:
    """24.72-24.74: who may build which air facility, and how long it takes."""
    if kind not in ("airfield", "landing_strip", "flying_boat_basin",
                    "alighting_area"):
        raise BreakdownError(f"unknown air facility: {kind!r}")
    for name, value in (("engineer_battalion", engineer_battalion),
                        ("engineer_company", engineer_company),
                        ("squadron_ground_support", squadron_ground_support),
                        ("coastal", coastal),
                        ("enemy_controlled", enemy_controlled)):
        _bool(value, name=name)
    if enemy_controlled:
        return False, "24.73", 0
    if kind in ("airfield", "flying_boat_basin"):
        if not engineer_battalion:
            return False, "24.72", 0
    elif not (engineer_battalion or engineer_company
              or squadron_ground_support):
        return False, "24.72", 0
    if kind in ("flying_boat_basin", "alighting_area"):
        if not coastal:
            return False, "24.73", 0
    elif terrain not in ("clear", "rough", "major_city", "desert",
                         "sand_gravel"):
        return False, "24.73", 0
    stages = 3 if kind in ("airfield", "flying_boat_basin") else 1
    return True, "", stages


def temporary_repair_facility_allowed(*, existing: int, engineer_present: bool,
                                      stores: int, fuel: int,
                                      enemy_controlled: bool) -> tuple[bool, str]:
    """24.81-24.87: at most two temporary facilities, 250 Stores and 150 Fuel."""
    count = _whole(existing, name="existing", minimum=0)
    if count >= TEMPORARY_REPAIR_LIMIT:
        return False, "24.85"
    if not _bool(engineer_present, name="engineer_present"):
        return False, "24.82"
    if _whole(stores, name="stores", minimum=0) < TEMPORARY_REPAIR_STORES:
        return False, "24.83"
    if _whole(fuel, name="fuel", minimum=0) < TEMPORARY_REPAIR_FUEL:
        return False, "24.83"
    if _bool(enemy_controlled, name="enemy_controlled"):
        return False, "24.87"
    return True, ""


def temporary_repair_dismantle_returns() -> tuple[int, int]:
    """24.86: dismantling returns 120 Stores and 25 Fuel."""
    return TEMPORARY_REPAIR_DISMANTLE_RETURNS


def supply_dump_cost(*, dummy: bool) -> tuple[int, int]:
    """24.9: three CP and twenty Stores, or three CP for a dummy."""
    _bool(dummy, name="dummy")
    return (3, 0) if dummy else (3, 20)


# ---------------------------------------------------------------------------
# 25 Fortifications
# ---------------------------------------------------------------------------

CITY_LEVEL = 2
CAPITAL_CITY_LEVEL = 3


def fortification_level(*, major_city: bool, capital: bool = False,
                        constructed: bool = False) -> int:
    """25.12-25.13: cities are Level 2, Cairo and Alexandria Level 3."""
    _bool(major_city, name="major_city")
    _bool(capital, name="capital")
    _bool(constructed, name="constructed")
    if capital:
        return CAPITAL_CITY_LEVEL
    if major_city:
        return CITY_LEVEL
    if constructed:
        return 1
    return 0


def constructed_fortification_max(*, capital: bool) -> int:
    """25.13: constructed Levels never exceed 2, except in Cairo/Alexandria."""
    return CAPITAL_CITY_LEVEL if _bool(capital, name="capital") else CITY_LEVEL


def air_bombardment_affects_level3_city() -> bool:
    """25.23: air bombardment has no effect until a Level 3 city is Level 2."""
    return False


def pinned_ignored_in_level3_city() -> bool:
    """25.24: units in a Level 3 city ignore all pinned results."""
    return True


def fortification_affects_movement_or_breakdown() -> bool:
    """25.21: fortifications affect neither movement nor Breakdown."""
    return False


# ---------------------------------------------------------------------------
# 26 Minefields
# ---------------------------------------------------------------------------

#: 26.24: the additional cost with an Engineer battalion.
ENGINEER_MINE_ADDITIONAL_CP = 4

#: 26.25: vehicles are destroyed on this roll or better.
MINEFIELD_VEHICLE_LOSS_ROLL = 5


def engineer_minefield_additional_cp(*, engineer_battalion_stacked: bool
                                     ) -> int | None:
    """26.24: four additional CP with an Engineer battalion, else the TEC cost."""
    if _bool(engineer_battalion_stacked,
             name="engineer_battalion_stacked"):
        return ENGINEER_MINE_ADDITIONAL_CP
    return None


def friendly_minefield_engineer_cost() -> int:
    """26.24: no extra cost for a Friendly minefield with an Engineer battalion."""
    return 0


def dummy_minefield_removal_phase() -> str:
    """26.14, 26.23: a revealed dummy survives until the end of the Movement Phase."""
    return "movement"


def minefield_vehicle_loss(roll: int) -> int:
    """26.25: a 5 or 6 destroys one TOE Point or unattached Truck Point."""
    value = _whole(roll, name="roll", minimum=1, maximum=6)
    return 1 if value >= MINEFIELD_VEHICLE_LOSS_ROLL else 0


def minefield_defender_column_shift(*, attacker_in_enemy_minefield: bool,
                                    defender_in_enemy_minefield: bool) -> int:
    """26.26: one column in the defender's favour, but never for bombardment."""
    for name, value in (("attacker_in_enemy_minefield",
                         attacker_in_enemy_minefield),
                        ("defender_in_enemy_minefield",
                         defender_in_enemy_minefield)):
        _bool(value, name=name)
    return 1 if (attacker_in_enemy_minefield
                 or defender_in_enemy_minefield) else 0
