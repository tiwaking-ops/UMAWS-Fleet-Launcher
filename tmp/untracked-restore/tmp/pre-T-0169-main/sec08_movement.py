"""Land movement.

RULE: 8.0, 8.11-8.18, 8.21-8.24, 8.31-8.34, 8.41-8.47, 8.51-8.55, 8.61-8.68,
8.91-8.94, 8.98

A unit has no movement allowance: every hex it enters is paid for out of its
CPA (8.11, 8.16), and the price comes from the Terrain Effects Chart.  The
chart is R-04 and is **caller-supplied** through ``MoveContext.cost``: this
module implements the rules that constrain a path, never a terrain price of
its own.  :func:`crossing` applies the numeric effects the rules *do* state
for wadis, escarpments, tracks, salt marsh and desert (8.41-8.47) on top of
a caller-supplied base cost.

The module consumes the Enemy-controlled hex set and the 10.24 helper from
:mod:`sec10_zoc`; the caller still supplies that set.  Stacking is kept out
of the path (the caller applies the Road/Track passage check from
:mod:`sec09_stacking`), which keeps movement testable without a full game
state.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Callable, Iterable

from cna.rules.sec10_zoc import may_move_zoc_to_zoc

RULE = "8.11-8.24, 8.41-8.47, 8.51-8.55, 8.61-8.68, 8.91-8.94, 8.98"

#: A unit at this Cohesion or worse may not move (6.26, 8.17).
COLLAPSE_AT = -26

#: Break Off costs (8.24, 8.65, 8.66).
CONTACT_BREAK_OFF_CP = Fraction(2)
ENGAGED_BREAK_OFF_CP = Fraction(4)

#: A Phasing unit must finish within this distance of an Enemy unit to move
#: again in the same Movement/Combat Phase (8.23).
CONTINUE_DISTANCE = 2

#: Track movement (8.46).
TRACK_CP_PER_HEX = Fraction(1)

#: Wadi crossing Breakdown (8.41).
WADI_BREAKDOWN_VEHICLE = Fraction(8)
WADI_BREAKDOWN_TRACK = Fraction(4)
WADI_BREAKDOWN_ROAD = Fraction(2)
WADI_RAIN_ROAD_CP = Fraction(2)

#: Escarpment descent by Track (8.42).
ESCARPMENT_TRACK_DOWN_CP = Fraction(8)
ESCARPMENT_TRACK_DOWN_BREAKDOWN = Fraction(6)

#: Unit classes used by the terrain rules.  They are labels, not ratings.
INFANTRY = "infantry"
TANK = "tank"
AFV = "afv"
TRUCK = "truck"
LIGHT_TRUCK = "light_truck"
ARTILLERY = "artillery"
RECCE = "recce"
MOTORCYCLE_INFANTRY = "motorcycle_infantry"
MOTORCYCLE_RECCE = "motorcycle_recce"
CAMEL = "camel"
OTHER = "other"

UNIT_CLASSES = frozenset({
    INFANTRY, TANK, AFV, TRUCK, LIGHT_TRUCK, ARTILLERY, RECCE,
    MOTORCYCLE_INFANTRY, MOTORCYCLE_RECCE, CAMEL, OTHER,
})

#: Classes that are vehicles for movement and Breakdown purposes.
VEHICLE_CLASSES = frozenset({
    TANK, AFV, TRUCK, LIGHT_TRUCK, ARTILLERY, RECCE,
    MOTORCYCLE_INFANTRY, MOTORCYCLE_RECCE,
})

#: 8.45: these may not enter a Desert hex even along a Track.
DESERT_FORBIDDEN = frozenset({
    LIGHT_TRUCK, MOTORCYCLE_INFANTRY, MOTORCYCLE_RECCE,
})

#: 8.44: the vehicles that may enter or leave a Salt Marsh off Road/Track.
SALT_MARSH_EXEMPT = frozenset({
    LIGHT_TRUCK, RECCE, MOTORCYCLE_INFANTRY, MOTORCYCLE_RECCE,
})

COMBAT_KINDS = frozenset({"combat", "artillery", "antitank", "aa"})
PHASES = frozenset({"movement", "truck_convoy", "reaction",
                    "retreat_before_assault"})


class MovementError(ValueError):
    """A move is illegal, or a movement input is not a valid §8 position."""


def _points(value: Any, *, name: str = "points") -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise MovementError(f"{name} must be an integer or Fraction")
    result = Fraction(value)
    if result < 0:
        raise MovementError(f"{name} must not be negative")
    return result


@dataclass(frozen=True)
class MovingUnit:
    """One unit beginning a move."""

    unit_id: str
    side: str
    base_cpa: int
    unit_class: str = INFANTRY
    motorized: bool = False
    kind: str = "combat"
    cohesion: int = 0
    stacking_points: Fraction = Fraction(1)
    contact: bool = False
    engaged: bool = False
    voluntary_spent: Fraction = Fraction(0)
    in_reserve: bool = False
    attached: bool = True
    transport_cpa: int | None = None
    stacked_with_friendly_combat: bool = False
    size_level: str = "battalion"
    raider: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.unit_id, str) or not self.unit_id.strip():
            raise MovementError("unit_id must be a non-empty string")
        if not isinstance(self.side, str) or not self.side.strip():
            raise MovementError("side must be a non-empty string")
        if isinstance(self.base_cpa, bool) or not isinstance(self.base_cpa, int):
            raise MovementError("base_cpa must be an integer")
        if self.base_cpa < 0:
            raise MovementError("base_cpa must not be negative")
        if self.unit_class not in UNIT_CLASSES:
            raise MovementError(f"unknown unit class: {self.unit_class!r}")
        if self.kind not in ("combat", "truck_convoy", "noncombat"):
            raise MovementError(f"unknown movement kind: {self.kind!r}")
        if isinstance(self.cohesion, bool) or not isinstance(self.cohesion, int):
            raise MovementError("cohesion must be an integer")
        object.__setattr__(self, "stacking_points", _points(self.stacking_points))
        object.__setattr__(self, "voluntary_spent",
                           _points(self.voluntary_spent, name="voluntary_spent"))
        for name in ("motorized", "contact", "engaged", "in_reserve",
                     "attached", "stacked_with_friendly_combat", "raider"):
            if not isinstance(getattr(self, name), bool):
                raise MovementError(f"{name} must be a bool")
        if self.transport_cpa is not None:
            if (isinstance(self.transport_cpa, bool)
                    or not isinstance(self.transport_cpa, int)
                    or self.transport_cpa < 0):
                raise MovementError(
                    "transport_cpa must be a non-negative integer or None")
        if self.size_level not in ("company", "battalion", "brigade", "division"):
            raise MovementError(f"unknown size level: {self.size_level!r}")

    @property
    def cpa(self) -> int:
        """The effective allowance (6.17, 8.92)."""
        return self.transport_cpa if self.transport_cpa is not None else self.base_cpa

    @property
    def is_vehicle(self) -> bool:
        return self.unit_class in VEHICLE_CLASSES

    @property
    def is_combat(self) -> bool:
        return self.kind == "combat"

    @property
    def non_motorized(self) -> bool:
        """8.17 defines non-motorized by a base CPA of ten or less."""
        return not self.motorized and self.base_cpa <= 10

    @property
    def can_move(self) -> bool:
        """6.26: a collapsed unit may not move."""
        return self.cohesion > COLLAPSE_AT

    @property
    def voluntary_cap(self) -> Fraction | None:
        """8.17: 50% above the base CPA for non-motorized units."""
        if not self.non_motorized:
            return None
        return Fraction(3, 2) * self.base_cpa


CostFn = Callable[[MovingUnit, str, str], Fraction | None]
AdjacencyFn = Callable[[str, str], bool]


@dataclass(frozen=True)
class MoveContext:
    """Everything the movement rules need that the map or TEC supplies.

    ``cost`` returns the CP cost to enter the destination, or ``None`` when
    the terrain or hexside is prohibited to that unit (8.31-8.32).  The
    caller is responsible for the Road/Track benefit (8.33) and for the
    Road/Track stack passage check (9.33); ``sec09_stacking`` provides the
    latter.
    """

    cost: CostFn
    enemy_occupied: frozenset[str] = frozenset()
    enemy_zoc: frozenset[str] = frozenset()
    friendly_combat: frozenset[str] = frozenset()
    advance_allowed: frozenset[str] = frozenset()
    adjacent: AdjacencyFn | None = None
    phase: str = "movement"

    def __post_init__(self) -> None:
        if not callable(self.cost):
            raise MovementError("cost must be callable")
        for name in ("enemy_occupied", "enemy_zoc", "friendly_combat",
                     "advance_allowed"):
            object.__setattr__(self, name,
                               frozenset(str(item) for item in getattr(self, name)))
        if self.phase not in PHASES:
            raise MovementError(f"unknown movement phase: {self.phase!r}")
        if self.adjacent is not None and not callable(self.adjacent):
            raise MovementError("adjacent must be callable or None")

    @property
    def controlled(self) -> frozenset[str]:
        """Enemy-controlled hexes after 10.26 (friendly combat negates)."""
        return self.enemy_zoc - self.friendly_combat


@dataclass(frozen=True)
class MoveResult:
    unit_id: str
    origin: str
    entered: tuple[str, ...]
    position: str
    break_off: Fraction
    movement_cost: Fraction
    total: Fraction
    stopped: str
    remaining: tuple[str, ...]
    voluntary_spent: Fraction

    def to_obj(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "origin": self.origin,
            "entered": list(self.entered),
            "position": self.position,
            "break_off": str(self.break_off),
            "movement_cost": str(self.movement_cost),
            "total": str(self.total),
            "stopped": self.stopped,
            "remaining": list(self.remaining),
            "voluntary_spent": str(self.voluntary_spent),
            "rule": RULE,
        }


def break_off_cost(unit: MovingUnit, *, phase: str = "movement") -> Fraction:
    """The CP to leave Contact or Engaged before moving (8.64-8.66).

    Reaction pays none (8.52); Movement Segments and Retreat Before Assault
    do (8.64).
    """
    if phase not in PHASES:
        raise MovementError(f"unknown movement phase: {phase!r}")
    if phase not in ("movement", "retreat_before_assault"):
        return Fraction(0)
    if unit.engaged:
        return ENGAGED_BREAK_OFF_CP
    if unit.contact:
        return CONTACT_BREAK_OFF_CP
    return Fraction(0)


def move_unit(unit: MovingUnit, origin: str, path: Iterable[str],
              context: MoveContext) -> MoveResult:
    """Move one unit along *path*, stopping where the rules require.

    Illegal moves raise :class:`MovementError` with the case that forbids
    them.  A move that is legal but must stop early (10.23) returns the
    prefix actually entered and the reason in ``stopped``.
    """
    if not isinstance(origin, str) or not origin.strip():
        raise MovementError("origin must be a non-empty hex id")
    if not unit.can_move:
        raise MovementError(
            "6.26: a unit with Cohesion -26 or worse may not move")
    if unit.kind == "truck_convoy" and context.phase != "truck_convoy":
        raise MovementError(
            "8.18: a Truck Convoy moves only in the Truck Convoy Movement Phase")
    if unit.kind != "truck_convoy" and context.phase == "truck_convoy":
        raise MovementError(
            "8.18: only unattached Truck Convoys move in the Truck Convoy Phase")

    steps = tuple(path)
    controlled = context.controlled
    break_off = break_off_cost(unit, phase=context.phase)
    spent = break_off
    voluntary = unit.voluntary_spent + break_off
    if (context.phase == "movement" and unit.non_motorized
            and voluntary > (unit.voluntary_cap or Fraction(0))):
        raise MovementError(
            "8.17: a non-motorized unit may not voluntarily expend more than "
            "50% above its base CPA in its own portion of the Operations Stage")

    entered: list[str] = []
    current = origin
    stopped = ""
    movement = Fraction(0)
    for index, destination in enumerate(steps):
        if not isinstance(destination, str) or not destination.strip():
            raise MovementError("a move path must contain non-empty hex ids")
        if context.adjacent is not None and not context.adjacent(current, destination):
            raise MovementError(
                "8.13: movement from hex to hex must be consecutive")
        if destination in context.enemy_occupied:
            raise MovementError(
                "8.13: a unit may never enter a hex containing an enemy unit")
        if not may_move_zoc_to_zoc(current, destination, controlled,
                                   advance_into=context.advance_allowed):
            raise MovementError(
                "10.24: no unit may move directly from one Enemy-controlled "
                "hex into another")
        if destination in controlled:
            if unit.kind == "truck_convoy":
                raise MovementError(
                    "10.29: a Truck Convoy may not enter an Enemy ZOC unless "
                    "the hex is occupied by a Friendly combat unit")
            if not unit.is_combat:
                raise MovementError(
                    "10.29: a non-combat unit may not voluntarily enter an "
                    "unoccupied hex in an Enemy ZOC")
        step = context.cost(unit, current, destination)
        if step is None:
            raise MovementError(
                "8.31/8.32: the Terrain Effects Chart prohibits this unit "
                "from entering that hex or crossing that hexside")
        step = _points(step, name="step cost")
        spent += step
        voluntary += step
        if context.phase == "movement" and unit.non_motorized:
            cap = unit.voluntary_cap or Fraction(0)
            if voluntary > cap:
                raise MovementError(
                    "8.17: a non-motorized unit may not voluntarily expend "
                    f"more than {cap} CP ({unit.base_cpa} base CPA + 50%) in "
                    "its own portion of the Operations Stage")
        if context.phase == "truck_convoy" and spent > unit.cpa:
            raise MovementError(
                "8.98: Truck Points moved in the Truck Convoy Phase may not "
                "exceed their CPA")
        entered.append(destination)
        movement += step
        current = destination
        if destination in controlled:
            stopped = "enemy ZOC (10.23)"
            remaining = steps[index + 1:]
            return MoveResult(
                unit_id=unit.unit_id, origin=origin,
                entered=tuple(entered), position=current,
                break_off=break_off, movement_cost=movement, total=spent,
                stopped=stopped, remaining=remaining,
                voluntary_spent=voluntary)

    return MoveResult(
        unit_id=unit.unit_id, origin=origin, entered=tuple(entered),
        position=current, break_off=break_off, movement_cost=movement,
        total=spent, stopped="", remaining=(), voluntary_spent=voluntary)


def may_continue_moving(unit: MovingUnit, *, distance_to_enemy: int,
                        reserve: bool | None = None) -> bool:
    """8.23: move again only if within two hexes of an Enemy unit.

    Reserve Status is the exception (18.0).  ``reserve`` defaults to the
    unit's own flag.
    """
    if isinstance(distance_to_enemy, bool) or not isinstance(distance_to_enemy, int):
        raise MovementError("distance_to_enemy must be an integer")
    if distance_to_enemy < 0:
        raise MovementError("distance_to_enemy must not be negative")
    if not unit.can_move:
        return False
    if reserve if reserve is not None else unit.in_reserve:
        return True
    return distance_to_enemy <= CONTINUE_DISTANCE


# ---------------------------------------------------------------------------
# Contact and Engaged (8.61-8.68)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ContactState:
    contact: bool = False
    engaged: bool = False

    def __post_init__(self) -> None:
        for name in ("contact", "engaged"):
            if not isinstance(getattr(self, name), bool):
                raise MovementError(f"{name} must be a bool")

    def to_obj(self) -> dict[str, Any]:
        return {"contact": self.contact, "engaged": self.engaged,
                "rule": "8.62-8.63"}


def contact_state(*, in_enemy_zoc_at_segment_start: bool,
                  engaged_result: bool = False) -> ContactState:
    """8.62-8.63: Contact is beginning a Segment in an Enemy ZOC."""
    if not isinstance(in_enemy_zoc_at_segment_start, bool):
        raise MovementError("in_enemy_zoc_at_segment_start must be a bool")
    if not isinstance(engaged_result, bool):
        raise MovementError("engaged_result must be a bool")
    return ContactState(contact=in_enemy_zoc_at_segment_start,
                        engaged=engaged_result)


def break_off_clears(remaining_in_contact: int) -> bool:
    """8.67: the enemy is clear once every unit in Contact has broken off."""
    if isinstance(remaining_in_contact, bool) or not isinstance(
            remaining_in_contact, int):
        raise MovementError("remaining_in_contact must be an integer")
    if remaining_in_contact < 0:
        raise MovementError("remaining_in_contact must not be negative")
    return remaining_in_contact == 0


def marker_applies(unit_was_present_at_placement: bool) -> bool:
    """8.68: a Contact/Engaged marker affects only units then in the hex."""
    if not isinstance(unit_was_present_at_placement, bool):
        raise MovementError("unit_was_present_at_placement must be a bool")
    return unit_was_present_at_placement


# ---------------------------------------------------------------------------
# Reaction (8.51-8.55)
# ---------------------------------------------------------------------------

_SIZE_ORDER = {"company": 0, "battalion": 1, "brigade": 2, "division": 3}


def _pin_blocked_by_size(enemy: MovingUnit, unit: MovingUnit) -> bool:
    """8.54: a battalion may never pin a division, a company a brigade."""
    return (_SIZE_ORDER[unit.size_level] - _SIZE_ORDER[enemy.size_level]) >= 2


def reaction_allowed(unit: MovingUnit, enemy: MovingUnit, *,
                     close_assault_announced: bool,
                     in_enemy_zoc: bool,
                     in_combat: bool) -> tuple[bool, str]:
    """8.53-8.54: may *unit* React to *enemy* moving adjacent?

    Returns ``(allowed, case)``; the case is empty when allowed.
    """
    if unit.non_motorized:
        return False, "8.53a"                                 # 8.53a
    if unit.kind == "truck_convoy" and not unit.stacked_with_friendly_combat:
        return False, "8.53a"
    if unit.kind == "noncombat":
        return False, "8.53a"
    if in_enemy_zoc:
        return False, "8.53c"                                 # 8.53c
    if in_combat:
        return False, "8.53d"                                 # 8.53d
    if close_assault_announced and enemy.cpa >= unit.cpa + 6:
        if not _pin_blocked_by_size(enemy, unit):             # 8.54
            return False, "8.53b"                             # 8.53b
    return True, ""


def reaction_step_allowed(destination: str,
                          enemy_zoc: Iterable[str]) -> bool:
    """8.55: a reacting unit may never enter an Enemy ZOC."""
    return destination not in frozenset(enemy_zoc)


# ---------------------------------------------------------------------------
# Terrain effects the rules state numerically (8.41-8.47)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TerrainCrossing:
    cp: Fraction
    breakdown: Fraction = Fraction(0)
    prohibited: bool = False
    abandoned: bool = False
    reason: str = ""

    def to_obj(self) -> dict[str, Any]:
        return {"cp": str(self.cp), "breakdown": str(self.breakdown),
                "prohibited": self.prohibited, "abandoned": self.abandoned,
                "reason": self.reason}


def crossing(unit: MovingUnit, *, base_cp: Fraction | int,
             base_breakdown: Fraction | int = 0, terrain: str = "clear",
             hexside: bool = False, road: bool = False, track: bool = False,
             unconstructed_road: bool = False, rainstorm: bool = False,
             direction: str = "") -> TerrainCrossing:
    """Apply 8.41-8.47 to a caller-supplied base terrain cost.

    ``base_cp`` and ``base_breakdown`` are the Terrain Effects Chart values
    for the hex or hexside; the rules here only *modify* them.  A Track is
    one CP per hex and halves hexside costs and Breakdown (8.46); an
    unconstructed Road is a Track (8.47); a Road ignores the other terrain
    (8.33).  ``direction`` is ``"up"`` or ``"down"`` for an escarpment.
    """
    cp = _points(base_cp, name="base_cp")
    breakdown = _points(base_breakdown, name="base_breakdown")
    if direction not in ("", "up", "down"):
        raise MovementError("direction must be '', 'up' or 'down'")
    for name, value in (("hexside", hexside), ("road", road), ("track", track),
                        ("unconstructed_road", unconstructed_road),
                        ("rainstorm", rainstorm)):
        if not isinstance(value, bool):
            raise MovementError(f"{name} must be a bool")
    if unconstructed_road:
        track = True                                          # 8.47

    if terrain == "desert" and unit.unit_class in DESERT_FORBIDDEN:
        return TerrainCrossing(                                 # 8.45
            cp=Fraction(0), breakdown=Fraction(0), prohibited=True,
            reason="8.45: this unit may not enter a Desert hex")

    if terrain == "salt_marsh" and unit.is_vehicle:
        if unit.unit_class not in SALT_MARSH_EXEMPT and not (road or track):
            return TerrainCrossing(                             # 8.44
                cp=Fraction(0), breakdown=Fraction(0), prohibited=True,
                abandoned=True,
                reason="8.44: a prohibited vehicle entering a Salt Marsh "
                       "off Road/Track is Abandoned")

    if terrain == "escarpment" and unit.is_vehicle:
        if direction == "up":
            return TerrainCrossing(                             # 8.42
                cp=Fraction(0), breakdown=Fraction(0), prohibited=True,
                reason="8.42: no vehicle may move up an escarpment")
        if direction == "down" and track:
            return TerrainCrossing(                             # 8.42
                cp=cp + ESCARPMENT_TRACK_DOWN_CP,
                breakdown=ESCARPMENT_TRACK_DOWN_BREAKDOWN,
                reason="8.42: vehicle moving down an escarpment by Track")

    if terrain == "wadi" and hexside:
        if rainstorm and not road:
            return TerrainCrossing(                             # 8.41
                cp=Fraction(0), breakdown=Fraction(0), prohibited=True,
                reason="8.41: a rain-swollen wadi is impassable except by Road")
        if road:
            return TerrainCrossing(                             # 8.41
                cp=cp + (WADI_RAIN_ROAD_CP if rainstorm else 0),
                breakdown=WADI_BREAKDOWN_ROAD if unit.is_vehicle else Fraction(0),
                reason="8.41: wadi crossed by Road")
        if track:
            return TerrainCrossing(                             # 8.41/8.46
                cp=cp / 2,
                breakdown=WADI_BREAKDOWN_TRACK if unit.is_vehicle else Fraction(0),
                reason="8.41: wadi crossed by Track")
        return TerrainCrossing(                                 # 8.41
            cp=cp,
            breakdown=WADI_BREAKDOWN_VEHICLE if unit.is_vehicle else Fraction(0),
            reason="8.41: wadi crossed without Road or Track")

    if road:
        return TerrainCrossing(cp=cp, breakdown=breakdown,   # 8.33
                               reason="8.33: Road ignores other terrain")

    if track:
        if hexside:
            return TerrainCrossing(cp=cp / 2,                 # 8.46
                                   breakdown=breakdown / 2,
                                   reason="8.46: Track halves a hexside cost")
        return TerrainCrossing(cp=TRACK_CP_PER_HEX,           # 8.46
                               breakdown=breakdown / 2,
                               reason="8.46: Track is one CP per hex")

    return TerrainCrossing(cp=cp, breakdown=breakdown)
