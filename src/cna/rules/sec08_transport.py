"""Rail movement and the Tripoli/Tunisia off-map boxes.

RULE: 8.71-8.78, 8.81-8.89

The rail network, the Off-Map Land Unit Movement Distance Chart (8.89), the
A2802 map edge and the road hexes leaving Tripolitania are R-04/R-05 data and
are **caller-supplied**.  This module implements the procedures around those
tables: line availability, the Commonwealth-only Rail phase, start and ZOC
checks, one stack per direction, the two-Stacking-Point limit, destroyed and
unconstructed rail hexes, pick-up/drop-off stops, the Axis rail cutoff, the
Tripoli/Tunisia entry restrictions, exact-CPA off-map stages, transit
reversal, map entry/exit and the off-map supply/stacking properties.

No map hex or chart value is invented here.  Tests use explicitly synthetic
lines and a synthetic distance chart.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Any, Callable, Iterable, Mapping

RULE = "8.71-8.78, 8.81-8.89"

AXIS = "axis"
COMMONWEALTH = "commonwealth"
RAIL_PHASE = "rail"

#: 8.71: the two printed lines and their availability.
ALEXANDRIA_LINE = "alexandria_mersa_matruh"
BENGHAZI_LINE = "soluch_benghazi_barce"
ACTIVE_RAIL_LINES = frozenset({ALEXANDRIA_LINE})
INACTIVE_RAIL_LINES = frozenset({BENGHAZI_LINE})

#: 8.75: the maximum Stacking Points a rail stack may carry.
RAIL_STACK_LIMIT = Fraction(2)

#: 8.85: the map hex a unit must start in to leave towards Tripolitania.
MAP_EXIT_HEX = "A2802"

#: 8.85: more than this many Stacking Points are strung out along the road.
ROAD_ENTRY_LIMIT = Fraction(5)

#: 8.81: the four large Tripoli/Tunisia boxes.
TRIPOLITANIA = "tripolitania"
TRIPOLI = "tripoli"
GABES = "gabes"
TUNIS = "tunis"
TRIPOLI_TUNISIA_BOXES = (TRIPOLITANIA, TRIPOLI, GABES, TUNIS)

#: 8.81/8.84: the smaller boxes used while a unit is in transit.
IN_TRANSIT_PREFIX = "in_transit:"

UNIT_TYPES = frozenset({"land", "sea", "air"})


class TransportError(ValueError):
    """A rail or off-map transport input is invalid."""


def _text(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TransportError(f"{name} must be a non-empty string")
    return value


def _points(value: Any, *, name: str = "points") -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise TransportError(f"{name} must be an integer or Fraction")
    result = Fraction(value)
    if result < 0:
        raise TransportError(f"{name} must not be negative")
    return result


def _whole(value: Any, *, name: str = "value", minimum: int | None = None,
           maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TransportError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise TransportError(f"{name} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise TransportError(f"{name} must be at most {maximum}")
    return value


def _bool(value: Any, *, name: str) -> bool:
    if not isinstance(value, bool):
        raise TransportError(f"{name} must be a bool")
    return value


# ---------------------------------------------------------------------------
# Rail movement (8.71-8.78)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RailLine:
    """One printed rail line, ordered west to east.

    ``destroyed`` and ``unconstructed`` are the 8.76 hexes; an unconstructed
    rail line is not usable at all until construction finishes (8.47, 24.6).
    """

    name: str
    hexes: tuple[str, ...]
    active: bool = True
    destroyed: frozenset[str] = frozenset()
    unconstructed: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, name="name"))
        hexes = tuple(self.hexes)
        if not hexes:
            raise TransportError("a rail line needs at least one hex")
        for hex_id in hexes:
            _text(hex_id, name="rail hex")
        if len(set(hexes)) != len(hexes):
            raise TransportError("a rail line may not repeat a hex")
        _bool(self.active, name="active")
        for name in ("destroyed", "unconstructed"):
            value = frozenset(str(item) for item in getattr(self, name))
            object.__setattr__(self, name, value)
        object.__setattr__(self, "hexes", hexes)

    def index(self, hex_id: str) -> int:
        _text(hex_id, name="hex_id")
        try:
            return self.hexes.index(hex_id)
        except ValueError:
            raise TransportError(
                f"{hex_id!r} is not on rail line {self.name!r}") from None

    def usable(self, hex_id: str) -> bool:
        """8.71/8.76: the hex exists, is active and is not blocked."""
        return (self.active and hex_id in self.hexes
                and hex_id not in self.destroyed
                and hex_id not in self.unconstructed)

    def path(self, origin: str, destination: str, direction: str) -> tuple[str, ...]:
        """The rail hexes entered from *origin* to *destination*."""
        start = self.index(origin)
        end = self.index(destination)
        if direction == "east":
            if end <= start:
                raise TransportError(
                    "8.72: an eastward rail move must end east of its start")
            return tuple(self.hexes[index]
                         for index in range(start + 1, end + 1))
        if direction == "west":
            if end >= start:
                raise TransportError(
                    "8.72: a westward rail move must end west of its start")
            return tuple(self.hexes[index]
                         for index in range(start - 1, end - 1, -1))
        raise TransportError("8.72: rail direction must be 'east' or 'west'")


@dataclass(frozen=True)
class RailNetwork:
    """The caller-supplied rail map; only active lines can be used."""

    lines: Mapping[str, RailLine]

    def __post_init__(self) -> None:
        lines = dict(self.lines)
        if not lines:
            raise TransportError("a rail network needs at least one line")
        for key, line in lines.items():
            if not isinstance(key, str) or not key.strip():
                raise TransportError("rail line keys must be non-empty strings")
            if not isinstance(line, RailLine):
                raise TransportError(f"rail line {key!r} must be a RailLine")
            if key != line.name:
                raise TransportError(
                    f"rail line key {key!r} does not match {line.name!r}")
        object.__setattr__(self, "lines", lines)

    def line(self, name: str) -> RailLine:
        try:
            return self.lines[name]
        except KeyError:
            raise TransportError(f"unknown rail line: {name!r}") from None

    def active_lines(self) -> tuple[RailLine, ...]:
        return tuple(self.lines[name] for name in sorted(self.lines)
                     if self.lines[name].active)


@dataclass(frozen=True)
class RailUsage:
    """The 8.74 directions already used this Operations Stage."""

    used: frozenset[tuple[str, str]] = frozenset()

    def __post_init__(self) -> None:
        normalized: set[tuple[str, str]] = set()
        for entry in self.used:
            if not isinstance(entry, tuple) or len(entry) != 2:
                raise TransportError("used rail directions must be (line, direction)")
            line, direction = entry
            _text(line, name="rail line")
            if direction not in ("east", "west"):
                raise TransportError(
                    "used rail directions must be 'east' or 'west'")
            normalized.add((line, direction))
        object.__setattr__(self, "used", frozenset(normalized))

    def used_direction(self, line: str, direction: str) -> bool:
        return (line, direction) in self.used

    def use(self, line: str, direction: str) -> "RailUsage":
        return RailUsage(self.used | {(line, direction)})

    def to_obj(self) -> dict[str, Any]:
        return {"used": [list(entry) for entry in sorted(self.used)],
                "rule": "8.74"}


@dataclass(frozen=True)
class RailMove:
    """One legal rail movement, including its 8.77 stops."""

    unit_id: str
    line: str
    direction: str
    origin: str
    destination: str
    entered: tuple[str, ...]
    stacking_points: Fraction
    stops: tuple[str, ...] = ()
    usage: RailUsage = RailUsage()

    def __post_init__(self) -> None:
        _text(self.unit_id, name="unit_id")
        _text(self.line, name="line")
        if self.direction not in ("east", "west"):
            raise TransportError("direction must be 'east' or 'west'")
        _text(self.origin, name="origin")
        _text(self.destination, name="destination")
        entered = tuple(self.entered)
        if not entered:
            raise TransportError("a rail move must enter at least one hex")
        for hex_id in entered:
            _text(hex_id, name="entered hex")
        object.__setattr__(self, "entered", entered)
        object.__setattr__(self, "stacking_points",
                           _points(self.stacking_points, name="stacking_points"))
        stops = tuple(self.stops)
        for hex_id in stops:
            _text(hex_id, name="stop")
        object.__setattr__(self, "stops", stops)

    def to_obj(self) -> dict[str, Any]:
        return {
            "unit": self.unit_id,
            "line": self.line,
            "direction": self.direction,
            "origin": self.origin,
            "destination": self.destination,
            "entered": list(self.entered),
            "stacking_points": str(self.stacking_points),
            "stops": list(self.stops),
            "usage": self.usage.to_obj(),
            "rule": "8.71-8.78",
        }


def plan_rail_move(
    line: RailLine,
    unit_id: str,
    *,
    side: str,
    phase: str,
    started_on_rail: bool,
    cp_spent: int,
    in_enemy_zoc: bool,
    stacking_points: Fraction | int,
    origin: str,
    destination: str,
    direction: str | None = None,
    stops: Iterable[str] = (),
    enemy_zoc: Iterable[str] = (),
    enemy_occupied: Iterable[str] = (),
    axis_combat_hexes: Iterable[str] = (),
    usage: RailUsage = RailUsage(),
) -> RailMove:
    """Validate and describe one 8.71-8.78 rail movement.

    ``axis_combat_hexes`` is used for 8.78: no hex west of the westernmost
    Axis combat unit on the line may be used by the Commonwealth.
    """
    if not isinstance(line, RailLine):
        raise TransportError("line must be a RailLine")
    _text(unit_id, name="unit_id")
    _text(side, name="side")
    _text(phase, name="phase")
    _bool(started_on_rail, name="started_on_rail")
    _whole(cp_spent, name="cp_spent", minimum=0)
    _bool(in_enemy_zoc, name="in_enemy_zoc")
    points = _points(stacking_points, name="stacking_points")
    _text(origin, name="origin")
    _text(destination, name="destination")
    if not isinstance(usage, RailUsage):
        raise TransportError("usage must be a RailUsage")

    if side != COMMONWEALTH:
        raise TransportError("8.71: only the Commonwealth may use Rail Movement")
    if phase != RAIL_PHASE:
        raise TransportError(
            "8.72: rail movement occurs in the Commonwealth Rail Movement Phase")
    if not line.active:
        raise TransportError(f"8.71: rail line {line.name!r} is not active")
    if not started_on_rail:
        raise TransportError(
            "8.73: the unit must start the Operations Stage on a rail hex")
    if cp_spent != 0:
        raise TransportError(
            "8.73: a unit using rail may not have expended CPs for any other reason")
    if in_enemy_zoc:
        raise TransportError("8.73: a unit in an Enemy ZOC may not use Rail Movement")
    if points > RAIL_STACK_LIMIT:
        raise TransportError(
            "8.75: Rail Movement may carry at most two Stacking Points")
    if points <= 0:
        raise TransportError("8.75: a rail stack must carry positive Stacking Points")

    line.index(origin)
    line.index(destination)
    if origin == destination:
        raise TransportError("8.72: a rail move must change hex")
    if not line.usable(origin):
        raise TransportError(f"8.76: rail hex {origin!r} is not usable")
    if not line.usable(destination):
        raise TransportError(f"8.76: rail hex {destination!r} is not usable")

    if direction is None:
        direction = ("east" if line.index(destination) > line.index(origin)
                     else "west")
    if direction not in ("east", "west"):
        raise TransportError("direction must be 'east' or 'west'")
    entered = line.path(origin, destination, direction)
    stop_list = tuple(stops)
    allowed_stops = {origin, destination, *entered}
    for stop in stop_list:
        _text(stop, name="stop")
        if stop not in allowed_stops:
            raise TransportError(
                f"8.77: stop {stop!r} is not on the rail path")
        if not line.usable(stop):
            raise TransportError(f"8.76: rail hex {stop!r} is not usable")

    controlled = frozenset(str(item) for item in enemy_zoc)
    occupied = frozenset(str(item) for item in enemy_occupied)
    axis_hexes = frozenset(str(item) for item in axis_combat_hexes)
    if origin in controlled or origin in occupied:
        raise TransportError(
            "8.73: a rail move may not start in an Enemy ZOC or occupied hex")
    for hex_id in entered:
        if not line.usable(hex_id):
            raise TransportError(f"8.76: rail hex {hex_id!r} is not usable")
        if hex_id in controlled:
            raise TransportError(
                f"8.73: rail movement may not enter Enemy ZOC hex {hex_id!r}")
        if hex_id in occupied:
            raise TransportError(
                f"8.73: rail movement may not enter Enemy-occupied hex {hex_id!r}")
        if hex_id in axis_hexes:
            raise TransportError(
                f"8.73: rail movement may not enter Axis-occupied hex {hex_id!r}")

    axis_indices = []
    for hex_id in axis_hexes:
        if hex_id in line.hexes:
            axis_indices.append(line.index(hex_id))
    if axis_indices:
        cutoff = min(axis_indices)
        if any(line.index(hex_id) <= cutoff for hex_id in entered):
            raise TransportError(
                "8.78: no rail hex west of an Axis combat unit may be used")

    if usage.used_direction(line.name, direction):
        raise TransportError(
            f"8.74: {line.name!r} has already been used {direction}ward this Stage")
    return RailMove(unit_id=unit_id, line=line.name, direction=direction,
                    origin=origin, destination=destination, entered=entered,
                    stacking_points=points, stops=stop_list,
                    usage=usage.use(line.name, direction))


# ---------------------------------------------------------------------------
# Tripoli/Tunisia off-map region (8.81-8.89)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OffMapUnit:
    """The off-map facts 8.82-8.88 need about one unit."""

    side: str
    unit_type: str = "land"
    motorized: bool = False
    stacking_points: Fraction = Fraction(1)
    reinforcement_or_replacement: bool = False
    arrived_this_stage: bool = False

    def __post_init__(self) -> None:
        if self.side not in (AXIS, COMMONWEALTH):
            raise TransportError("off-map side must be 'axis' or 'commonwealth'")
        if self.unit_type not in UNIT_TYPES:
            raise TransportError(f"unknown off-map unit type: {self.unit_type!r}")
        _bool(self.motorized, name="motorized")
        object.__setattr__(self, "stacking_points",
                           _points(self.stacking_points))
        for name in ("reinforcement_or_replacement", "arrived_this_stage"):
            _bool(getattr(self, name), name=name)


def off_map_entry_allowed(unit: OffMapUnit) -> bool:
    """8.82: Axis units and Commonwealth airplanes, nothing else."""
    if not isinstance(unit, OffMapUnit):
        raise TransportError("unit must be an OffMapUnit")
    if unit.side == AXIS:
        return True
    if unit.side == COMMONWEALTH:
        return unit.unit_type == "air"
    return False


@dataclass(frozen=True)
class OffMapChart:
    """The 8.89 distance chart, supplied by the caller.

    ``stages(origin, destination, cpa)`` returns the number of Operations
    Stages needed.  The official chart is R-04; tests use a synthetic lambda.
    """

    stages: Callable[[str, str, int], int]

    def __post_init__(self) -> None:
        if not callable(self.stages):
            raise TransportError("stages must be callable")

    def stages_between(self, origin: str, destination: str, cpa: int) -> int:
        _text(origin, name="origin")
        _text(destination, name="destination")
        _whole(cpa, name="cpa", minimum=1)
        return _whole(self.stages(origin, destination, cpa),
                      name="stages", minimum=1)


def in_transit_label(index: int) -> str:
    """The label for the In Transit box after *index* completed Stages."""
    return f"{IN_TRANSIT_PREFIX}{_whole(index, name='index', minimum=1)}"


@dataclass(frozen=True)
class OffMapTransit:
    """Progress through the abstract off-map distance for one unit.

    ``elapsed`` is the number of Operations Stages already spent.  A unit may
    pause, and 8.84's reversal turns the remaining path back into a transit
    whose length is the distance already covered.
    """

    origin: str
    destination: str
    stages: int
    elapsed: int = 0

    def __post_init__(self) -> None:
        _text(self.origin, name="origin")
        _text(self.destination, name="destination")
        if self.origin == self.destination:
            raise TransportError("an off-map transit needs two positions")
        _whole(self.stages, name="stages", minimum=1)
        _whole(self.elapsed, name="elapsed", minimum=0, maximum=self.stages)

    @property
    def arrived(self) -> bool:
        return self.elapsed >= self.stages

    @property
    def position(self) -> str:
        if self.arrived:
            return self.destination
        if self.elapsed == 0:
            return self.origin
        return in_transit_label(self.elapsed)

    def advance(self) -> "OffMapTransit":
        if self.arrived:
            raise TransportError("8.84: the transit has already arrived")
        return replace(self, elapsed=self.elapsed + 1)

    def reverse(self) -> "OffMapTransit":
        """8.84: turn back; the distance home is the distance already covered."""
        if self.elapsed == 0:
            return self
        return OffMapTransit(origin=self.position, destination=self.origin,
                             stages=self.elapsed)

    def to_obj(self) -> dict[str, Any]:
        return {
            "origin": self.origin,
            "destination": self.destination,
            "stages": self.stages,
            "elapsed": self.elapsed,
            "position": self.position,
            "arrived": self.arrived,
            "rule": "8.84",
        }


@dataclass(frozen=True)
class OffMapStageResult:
    """One off-map Operations Stage: exact CPA, fuel, no Breakdown."""

    transit: OffMapTransit
    cp_spent: int
    fuel_required: bool
    breakdown_check: bool = False

    def to_obj(self) -> dict[str, Any]:
        return {
            "transit": self.transit.to_obj(),
            "cp_spent": self.cp_spent,
            "fuel_required": self.fuel_required,
            "breakdown_check": self.breakdown_check,
            "rule": "8.83",
        }


def plan_off_map_move(origin: str, destination: str, *, cpa: int,
                      chart: OffMapChart,
                      unit: OffMapUnit | None = None) -> OffMapTransit:
    """8.82/8.84: plan the abstract transit between two boxes or the map."""
    if not isinstance(chart, OffMapChart):
        raise TransportError("chart must be an OffMapChart")
    if unit is not None:
        if not off_map_entry_allowed(unit):
            raise TransportError(
                "8.82: only Axis units and Commonwealth airplanes may enter "
                "the Tripoli/Tunisia region")
        if unit.unit_type != "land":
            raise TransportError(
                "8.83: air and sea movement use their own rules, not the "
                "off-map land distance chart")
    return OffMapTransit(origin, destination,
                         chart.stages_between(origin, destination, cpa))


def advance_off_map(transit: OffMapTransit, *, cp_spent: int, cpa: int,
                    motorized: bool = False) -> OffMapStageResult:
    """8.83: spend exactly the CPA, consume fuel, never check Breakdown."""
    if not isinstance(transit, OffMapTransit):
        raise TransportError("transit must be an OffMapTransit")
    spent = _whole(cp_spent, name="cp_spent", minimum=0)
    allowance = _whole(cpa, name="cpa", minimum=1)
    _bool(motorized, name="motorized")
    if spent != allowance:
        raise TransportError(
            "8.83: an off-map unit must expend exactly its Capability Point "
            "Allowance each Operations Stage")
    return OffMapStageResult(transit=transit.advance(), cp_spent=spent,
                             fuel_required=motorized, breakdown_check=False)


def is_off_map_position(position: str) -> bool:
    _text(position, name="position")
    return (position in TRIPOLI_TUNISIA_BOXES
            or position.startswith(IN_TRANSIT_PREFIX))


def map_exit_allowed(start_hex: str) -> bool:
    """8.85: a unit leaving the map towards Tripolitania starts at A2802."""
    _text(start_hex, name="start_hex")
    return start_hex == MAP_EXIT_HEX


def off_map_entry_hexes(road_hexes: Iterable[str],
                        stacking_points: Fraction | int
                        ) -> tuple[tuple[str, Fraction], ...]:
    """8.85: place an entering force on the road, five points per hex."""
    hexes = tuple(road_hexes)
    if not hexes:
        raise TransportError("at least one road hex is needed")
    for hex_id in hexes:
        _text(hex_id, name="road hex")
    remaining = _points(stacking_points, name="stacking_points")
    if remaining <= 0:
        raise TransportError("the entering force needs positive Stacking Points")
    allocations: list[tuple[str, Fraction]] = []
    for hex_id in hexes:
        if remaining <= 0:
            break
        take = min(ROAD_ENTRY_LIMIT, remaining)
        allocations.append((hex_id, take))
        remaining -= take
    if remaining > 0:
        raise TransportError(
            "8.85: not enough road hexes to string out the entering force")
    return tuple(allocations)


def arrival_box_locked(box: str, *, arrived_this_stage: bool,
                       reinforcement_or_replacement: bool) -> bool:
    """8.86: a newly arrived reinforcement may not leave Tunis or Tripoli."""
    _text(box, name="box")
    if box not in TRIPOLI_TUNISIA_BOXES:
        raise TransportError(f"unknown Tripoli/Tunisia box: {box!r}")
    _bool(arrived_this_stage, name="arrived_this_stage")
    _bool(reinforcement_or_replacement, name="reinforcement_or_replacement")
    return (box in (TRIPOLI, TUNIS) and arrived_this_stage
            and reinforcement_or_replacement)


def off_map_box_properties(box: str) -> dict[str, Any]:
    """8.87-8.88: no stacking, unlimited Water, and the large-box facilities."""
    _text(box, name="box")
    if box in TRIPOLI_TUNISIA_BOXES:
        return {
            "stacking_limit": None,
            "water": "unlimited",
            "air_facilities": True,
            "supplies": "unlimited",
            "maintenance_crews": True,
            "rule": "8.87-8.88",
        }
    if box.startswith(IN_TRANSIT_PREFIX):
        return {
            "stacking_limit": None,
            "water": "unlimited",
            "air_facilities": False,
            "supplies": None,
            "maintenance_crews": False,
            "rule": "8.87",
        }
    raise TransportError(f"unknown Tripoli/Tunisia box: {box!r}")


def supply_transfer_allows_movement(*, loads_or_unloads_this_stage: bool) -> bool:
    """8.88: a truck or motorization point may not move while loading/unloading."""
    return not _bool(loads_or_unloads_this_stage,
                     name="loads_or_unloads_this_stage")
