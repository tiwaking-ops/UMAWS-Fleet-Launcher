"""The Operations Stage loop.

RULE: 5.2 (sequence of play), 8.11-8.24 (land movement), 9.31-9.33
(stacking when movement stops and Road/Track passage), 10.21-10.29
(Zones of Control), 21.24-21.26 (Breakdown checks when a unit stops).

The decision-point engine knows how to offer and take one choice.  This
module is the loop that walks a whole **Operations Stage** through it: the
rule 5.2 phases are read from :mod:`cna.rules.sec05_sequence`, the acting
side is derived from the A/B player mapping, and every Movement/Combat
phase offers one-hex moves that are admitted only by the three rule
modules:

* :mod:`cna.rules.sec08_movement` decides whether a unit may enter the
  destination at all (8.13, 8.16, 8.17, 8.24, 10.23, 10.24, 10.29);
* :mod:`cna.rules.sec09_stacking` decides whether it may **stop** there
  (9.31, 9.33);
* :mod:`cna.rules.sec10_zoc` builds the Enemy-controlled hex set from the
  units' current positions (10.11-10.26).

Everything the map and the Terrain Effects Chart supply is caller-owned
(``StageScenario``): hex adjacency, the cost of a hex, the stacking limit
of a hex, blocked hexsides and Road/Track hexsides.  No map, TEC value or
historical counter is invented here; tests and the soak pass explicitly
synthetic fixtures.

Two deliberate limits, so a caller is not misled:

* **Continual movement and a Close Assault handoff.**  8.22-8.23 repeated
  movement is modelled: a unit that finishes a segment within two hexes of
  an enemy combat unit, or that is in Reserve, stays eligible for another
  move in the same phase.  A unit adjacent to an enemy-occupied hex is also
  offered a Close Assault move.  It resolves through
  :mod:`cna.rules.sec11_combat`; entering the enemy hex itself is still
  forbidden by 8.13, so the attacker's position does not change.
* **Only phase G moves land units and phase J offers rail stacks.**
  Truck Convoy (H), repair (K) and patrol (L) still end their phase.
* **Combat is Close Assault only.**  The Barrage, Retreat Before Assault,
  Anti-Armor and force-assignment steps of the 11.0 Combat Segment are not
  yet driven by this loop; their rules live in :mod:`cna.rules.sec11_combat`
  for a caller that wants to run them.

The loop is pure in the engine's sense: it returns a new state and never
mutates the one it was given.  It records every choice through
:func:`cna.engine.apply`, so the resolution and ordered history survive and
the same seed and players reproduce the same stage.
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from fractions import Fraction
from itertools import combinations
from typing import Any, Callable, Iterable, Mapping

from cna.rules.sec05_sequence import Phase, phases_for_turn
from cna.rules.sec08_movement import (CONTINUE_DISTANCE, MoveContext,
                                      MovingUnit, MovementError,
                                      may_continue_moving, move_unit)
from cna.rules.sec08_transport import (COMMONWEALTH, RAIL_PHASE,
                                       RAIL_STACK_LIMIT, TRIPOLI,
                                       TRIPOLI_TUNISIA_BOXES, TUNIS,
                                       OffMapChart, OffMapStageResult,
                                       OffMapTransit, OffMapUnit, RailMove,
                                       RailNetwork, RailUsage,
                                       TransportError, advance_off_map,
                                       arrival_box_locked,
                                       is_off_map_position,
                                       off_map_entry_allowed,
                                       plan_off_map_move, plan_rail_move)
from cna.rules.sec09_stacking import (HexContext, StackingResult,
                                      StackingUnit, check_end_of_movement,
                                      check_road_passage)
from cna.rules.sec10_zoc import (COMBAT_KINDS, ZocUnit,
                                 enemy_controlled_hexes)
from cna.rules.sec11_combat import (AssaultRoll, CombatError, CombatUnit,
                                    LossTarget, assault_differential,
                                    assault_raw_strength, may_close_assault,
                                    resolve_close_assault)
from cna.rules.sec21_breakdown import WEATHER_SHIFTS, evaluate_breakdown
from cna.rules.sec32_abstract import (AbstractSupplyError, SupplyUnit,
                                      ammo_cost, captured_supply_points,
                                      fuel_for_stage, movement_fuel_cost,
                                      motorization_can_transport,
                                      road_track_stacking_ignored,
                                      supply_unit_captured)
from cna.state.views import view

from .actions import Action
from .decision import Decision, apply, legal_actions

SIDES = ("axis", "commonwealth")

RULE = ("5.2, 8.11-8.24, 8.71-8.78, 8.81-8.89, 9.31-9.33, "
        "10.21-10.29, 11.0-15.96, 21.24-21.26, 32.9, 32.13, "
        "32.21-32.24, 32.54")


class StageError(ValueError):
    """The loop cannot play this stage with the state and scenario given."""


def _fraction(value: Any, *, name: str = "value") -> Fraction:
    if value is None:
        return Fraction(0)
    if isinstance(value, bool) or not isinstance(value, (int, Fraction, str)):
        raise StageError(f"{name} must be an integer, Fraction or numeric string")
    try:
        result = Fraction(value)
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        raise StageError(f"{name} is not a number: {value!r}") from exc
    if result < 0:
        raise StageError(f"{name} must not be negative")
    return result


def _whole(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise StageError(f"{name} must be an integer")
    return value


@dataclass(frozen=True)
class StageScenario:
    """What one Operations Stage needs that the map and TEC would supply.

    ``neighbours`` and ``cost`` are the movement interface; ``hex_limits``
    is the 9.14 stacking limit (``None`` keeps the limit unknown instead of
    inventing one); ``blocked_hexside`` and ``can_enter`` narrow ZOC per
    10.21;    ``road_track`` marks a hexside where the 9.33 passage check
    applies.  ``breakdown_table`` is the caller-supplied 21.38 table: two
    sequential dice and a column in, a percentage out.  Without it a
    pending check is recorded but never rolled.  ``assault_table`` is a
    caller-supplied Close Assault CRT: ``(role, differential, roll)`` in,
    an :class:`~cna.rules.sec11_combat.AssaultRoll` out.  Without it an
    assault is recorded as pending, never resolved with invented values.
    ``player_a``/``player_b`` map rule 5.2's A/B players onto the two sides,
    because initiative decides which side is A.  ``off_map_chart`` is the
    caller-supplied 8.89 distance chart; when it is present, phase G also
    offers 8.81-8.84 off-map transit steps for land units in
    ``off_map_boxes``.  ``abstract_supply`` enables the LAND_ABSTRACT §32
    layer: 32.9 Road/Track stacking is ignored, linked records in
    ``state['supplies']`` pay 32.23-32.24 fuel and 32.21-32.22 Ammo, and a
    combat unit entering an enemy Supply Unit's hex captures it (32.13).
    A unit is linked to a Supply Unit by its ``supply_id`` field; without
    one, legacy unlinked movement remains unchanged.
    """

    neighbours: Callable[[str], Iterable[str]]
    cost: Callable[[MovingUnit, str, str], Any]
    hex_limits: Mapping[str, Fraction | int | str | None] = \
        field(default_factory=dict)
    blocked_hexside: Callable[[str, str], bool] | None = None
    can_enter: Callable[[str, str], bool] | None = None
    road_track: Callable[[str, str], bool] | None = None
    player_a: str = "axis"
    player_b: str = "commonwealth"
    weather: str = "normal"
    sandstorm_majority: bool = False
    rail: RailNetwork | None = None
    off_map_chart: OffMapChart | None = None
    off_map_boxes: tuple[str, ...] = TRIPOLI_TUNISIA_BOXES
    abstract_supply: bool = False
    breakdown_table: Callable[[int, int], int] | None = None
    assault_table: Callable[[str, int, int], AssaultRoll] | None = None

    def __post_init__(self) -> None:
        if not callable(self.neighbours):
            raise StageError("neighbours must be callable")
        if not callable(self.cost):
            raise StageError("cost must be callable")
        for name in ("player_a", "player_b"):
            if getattr(self, name) not in SIDES:
                raise StageError(f"{name} must be one of {SIDES}")
        for name in ("blocked_hexside", "can_enter", "road_track",
                     "breakdown_table", "assault_table"):
            value = getattr(self, name)
            if value is not None and not callable(value):
                raise StageError(f"{name} must be callable or None")
        if self.weather not in WEATHER_SHIFTS:
            raise StageError(f"unknown weather: {self.weather!r}")
        if not isinstance(self.sandstorm_majority, bool):
            raise StageError("sandstorm_majority must be a bool")
        if not isinstance(self.abstract_supply, bool):
            raise StageError("abstract_supply must be a bool")
        if self.rail is not None and not isinstance(self.rail, RailNetwork):
            raise StageError("rail must be a RailNetwork or None")
        if self.off_map_chart is not None and not isinstance(
                self.off_map_chart, OffMapChart):
            raise StageError("off_map_chart must be an OffMapChart or None")
        if isinstance(self.off_map_boxes, str) or self.off_map_boxes is None:
            raise StageError("off_map_boxes must be a sequence of box names")
        boxes = tuple(self.off_map_boxes)
        if not boxes:
            raise StageError("off_map_boxes must not be empty")
        for box in boxes:
            if not isinstance(box, str) or not box.strip():
                raise StageError(
                    "off_map_boxes must contain non-empty strings")
        if len(set(boxes)) != len(boxes):
            raise StageError("off_map_boxes must not contain duplicates")
        object.__setattr__(self, "off_map_boxes", boxes)
        object.__setattr__(self, "hex_limits", dict(self.hex_limits))

    def player_for(self, actor: str) -> str | None:
        """The side playing rule 5.2's A/B actor, or ``None`` if not one."""
        if actor == "A":
            return self.player_a
        if actor == "B":
            return self.player_b
        return actor if actor in SIDES else None

    def limit(self, hex_id: str) -> Fraction | None:
        raw = self.hex_limits.get(hex_id)
        if raw is None:
            return None
        return _fraction(raw, name=f"stacking limit for {hex_id!r}")


@dataclass(frozen=True)
class CombatMove:
    """An assault ordered against an adjacent enemy-occupied hex.

    The unit does not enter the hex (8.13); the move is a handoff to the
    Combat Segment.  The object carries the fields the move UI reads so an
    assault can be offered alongside ordinary one-hex moves.
    """

    target: str
    total: Fraction = Fraction(0)
    voluntary_spent: Fraction = Fraction(0)
    stopped: str = "enemy-occupied: Combat Segment"
    breakdown: None = None


@dataclass(frozen=True)
class MoveOption:
    """One legal one-hex move, or one Close Assault, for one unit."""

    unit_id: str
    destination: str
    move: Any
    stacking: StackingResult | None
    combat: bool = False

    def to_obj(self) -> dict[str, Any]:
        return {
            "unit": self.unit_id,
            "destination": self.destination,
            "total": str(self.move.total),
            "stopped": self.move.stopped,
            "stacking": (None if self.stacking is None
                         else self.stacking.to_obj()),
            "breakdown": (None if self.move.breakdown is None
                          else self.move.breakdown.to_obj()),
            "combat": self.combat,
            "rule": RULE,
        }


@dataclass(frozen=True)
class RailStackMove:
    """Several individually legal rail moves carried as one 8.72 stack.

    The phase-J action is a stack, not a list of independent moves, so the
    aggregate Stacking Point total is checked here (8.75).  A stack shares
    one line, direction, origin and destination; only its units may differ.
    """

    moves: tuple[RailMove, ...]

    def __post_init__(self) -> None:
        moves = tuple(self.moves)
        if not moves:
            raise StageError("a rail stack needs at least one unit")
        if not all(isinstance(move, RailMove) for move in moves):
            raise StageError("a rail stack may only contain RailMove values")
        first = moves[0]
        for move in moves[1:]:
            if (move.line, move.direction, move.origin, move.destination) != (
                    first.line, first.direction, first.origin,
                    first.destination):
                raise StageError("a rail stack must share one line and route")
        unit_ids = tuple(move.unit_id for move in moves)
        if len(set(unit_ids)) != len(unit_ids):
            raise StageError("a rail stack may not repeat a unit")
        total = sum((move.stacking_points for move in moves), Fraction(0))
        if total > RAIL_STACK_LIMIT:
            raise StageError(
                "8.75: Rail Movement may carry at most two Stacking Points")
        object.__setattr__(self, "moves", moves)

    @property
    def unit_ids(self) -> tuple[str, ...]:
        return tuple(move.unit_id for move in self.moves)

    @property
    def line(self) -> str:
        return self.moves[0].line

    @property
    def direction(self) -> str:
        return self.moves[0].direction

    @property
    def origin(self) -> str:
        return self.moves[0].origin

    @property
    def destination(self) -> str:
        return self.moves[0].destination

    @property
    def stacking_points(self) -> Fraction:
        return sum((move.stacking_points for move in self.moves), Fraction(0))

    @property
    def usage(self) -> RailUsage:
        return self.moves[0].usage

    def to_obj(self) -> dict[str, Any]:
        return {
            "units": list(self.unit_ids),
            "line": self.line,
            "direction": self.direction,
            "origin": self.origin,
            "destination": self.destination,
            "stacking_points": str(self.stacking_points),
            "usage": self.usage.to_obj(),
            "rule": "8.72, 8.74, 8.75",
        }


@dataclass(frozen=True)
class OffMapMove:
    """One 8.81-8.84 off-map transit step for one land unit."""

    unit_id: str
    origin: str
    destination: str
    kind: str
    result: OffMapStageResult

    def to_obj(self) -> dict[str, Any]:
        return {
            "unit": self.unit_id,
            "origin": self.origin,
            "destination": self.destination,
            "kind": self.kind,
            "transit": self.result.transit.to_obj(),
            "cp_spent": self.result.cp_spent,
            "fuel_required": self.result.fuel_required,
            "breakdown": self.result.breakdown_check,
            "rule": "8.83-8.84",
        }


@dataclass(frozen=True)
class StageResult:
    """What one call to :func:`play_operations_stage` did."""

    state: dict[str, Any]
    stage: int
    phases: int
    actions: int
    moves: int
    completed: bool
    events: tuple[dict[str, Any], ...] = ()
    combats: int = 0

    def to_obj(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "phases": self.phases,
            "actions": self.actions,
            "moves": self.moves,
            "combats": self.combats,
            "completed": self.completed,
            "events": [dict(event) for event in self.events],
            "rule": RULE,
        }


# ---------------------------------------------------------------------------
# reading the state
# ---------------------------------------------------------------------------

def _records(state: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    units = state.get("units")
    if units is None:
        return {}
    if not isinstance(units, Mapping):
        raise StageError("state['units'] must be a mapping")
    records: dict[str, dict[str, Any]] = {}
    for unit_id, record in units.items():
        if not isinstance(record, Mapping):
            raise StageError(f"unit {unit_id!r} must be a mapping")
        records[str(unit_id)] = dict(record)
    return records


def _position(record: Mapping[str, Any], unit_id: str) -> str:
    position = record.get("position")
    if not isinstance(position, str) or not position.strip():
        raise StageError(f"unit {unit_id!r} needs a non-empty position")
    return position


# ---------------------------------------------------------------------------
# §32 abstract supply integration
# ---------------------------------------------------------------------------

def _stage_key(state: Mapping[str, Any]) -> str:
    """The Game-Turn/Operations-Stage key used by 32.23's first-move rule."""
    return (f"T{_whole(state.get('turn', 1), name='turn')}"
            f"S{_whole(state.get('stage', 1), name='stage')}")


def _supply_records(state: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Read the abstract Supply Unit ledger without mutating the state."""
    raw = state.get("supplies")
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise StageError("state['supplies'] must be a mapping")
    records: dict[str, dict[str, Any]] = {}
    for supply_id, record in raw.items():
        if not isinstance(record, Mapping):
            raise StageError(f"supply {supply_id!r} must be a mapping")
        records[str(supply_id)] = dict(record)
    return records


def _supply_unit(supply_id: str, record: Mapping[str, Any]) -> SupplyUnit:
    """Build the §32 view of one Supply Dump counter."""
    try:
        return SupplyUnit(
            side=str(record.get("side", "")),
            ammo=record.get("ammo", 40),
            fuel=record.get("fuel", 60),
            dummy=record.get("dummy", False),
        )
    except AbstractSupplyError as exc:
        raise StageError(f"supply {supply_id!r} is invalid: {exc}") from exc


def _supply_link(record: Mapping[str, Any]) -> str | None:
    """The caller-supplied Supply Unit that supports this unit, if any."""
    raw = record.get("supply_id")
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise StageError("supply_id must be a non-empty string or None")
    return raw


def _supply_can_pay(state: Mapping[str, Any], record: Mapping[str, Any], *,
                    ammo: int = 0, fuel: int = 0) -> bool:
    """Can the linked Supply Unit pay this cost, if the unit is linked?"""
    if ammo < 0 or fuel < 0:
        raise StageError("supply costs must not be negative")
    supply_id = _supply_link(record)
    if supply_id is None:
        return True
    records = _supply_records(state)
    if supply_id not in records:
        return False
    unit = _supply_unit(supply_id, records[supply_id])
    if unit.side != record.get("side"):
        return False
    return unit.ammo >= ammo and unit.fuel >= fuel


def _spend_supply(state: Mapping[str, Any], supply_id: str, *,
                  ammo: int = 0, fuel: int = 0) -> dict[str, Any]:
    """Spend from one linked Supply Unit and remove it when empty (32.15)."""
    if not ammo and not fuel:
        return dict(state)
    records = _supply_records(state)
    if supply_id not in records:
        raise StageError(f"unknown Supply Unit: {supply_id!r}")
    unit = _supply_unit(supply_id, records[supply_id])
    try:
        reduced = unit.spend(ammo=ammo, fuel=fuel)
    except AbstractSupplyError as exc:
        raise StageError(
            f"Supply Unit {supply_id!r} cannot pay {ammo} Ammo / {fuel} Fuel: "
            f"{exc}") from exc
    if reduced.empty:
        records.pop(supply_id)
    else:
        record = dict(records[supply_id])
        record["ammo"] = reduced.ammo
        record["fuel"] = reduced.fuel
        records[supply_id] = record
    return {**state, "supplies": records}


def _movement_fuel_base(record: Mapping[str, Any]) -> int:
    """32.24: the Fuel Points one land move category requires."""
    unit_class = str(record.get("unit_class", "")).lower()
    size = str(record.get("size_level", "battalion")).lower()
    kwargs: dict[str, int] = {}
    if unit_class in ("tank", "afv"):
        if size == "company":
            kwargs["tank_companies"] = 1
        else:
            kwargs["tank_battalions"] = 1
    elif unit_class in ("gun", "artillery"):
        kwargs["gun_battalions"] = 1
    elif unit_class in ("recce", "motorcycle_recce"):
        kwargs["recce_battalions"] = 1
    elif bool(record.get("motorized")) and unit_class == "infantry":
        kwargs["motorization_transports"] = 1
    if not kwargs:
        return 0
    try:
        return movement_fuel_cost(**kwargs)
    except AbstractSupplyError as exc:
        raise StageError(f"invalid movement fuel category: {exc}") from exc


def _move_fuel_cost(record: Mapping[str, Any], *, total: Fraction,
                    first: bool) -> int:
    """32.23-32.24: first move, plus the cost when CPA is crossed."""
    base = _movement_fuel_base(record)
    if not base:
        return 0
    before = _fraction(record.get("spent", 0))
    cpa_raw = record.get("transport_cpa")
    if cpa_raw is None:
        cpa_raw = record.get("base_cpa", 0)
    cpa = _whole(cpa_raw, name="base_cpa")
    crosses = before <= cpa < before + total
    if first and crosses:
        return fuel_for_stage(first_move_fuel=base, exceeds_cpa=True)
    if first:
        return fuel_for_stage(first_move_fuel=base)
    if crosses:
        return base
    return 0


def _assault_ammo(record: Mapping[str, Any]) -> int:
    """32.21-32.22: Ammo for one phasing Close Assault Bn-Eq."""
    raw = record.get("battalion_equivalents")
    if raw is None:
        return 0
    try:
        count = _whole(raw, name="battalion_equivalents")
        return ammo_cost(battalion_equivalents=count, combat="assault",
                         phasing=True)
    except AbstractSupplyError as exc:
        raise StageError(f"invalid battalion_equivalents: {exc}") from exc


def _transport_allowed(record: Mapping[str, Any]) -> bool:
    """32.53-32.54: a carried unit must be leg infantry or a Gun."""
    if record.get("transport_cpa") is None:
        return True
    try:
        cpa = _whole(record.get("base_cpa", 0), name="base_cpa")
        unit_type = str(record.get("unit_class", ""))
        if unit_type == "artillery":
            unit_type = "gun"
        return motorization_can_transport(unit_type=unit_type, cpa=cpa)
    except (AbstractSupplyError, StageError):
        return False


def _capture_supplies(state: Mapping[str, Any], hex_id: str, side: str,
                      unit_id: str) -> dict[str, Any]:
    """32.13: an enemy combat unit entering a Supply Unit's hex captures it."""
    records = _supply_records(state)
    captured: list[dict[str, Any]] = []
    for supply_id in sorted(records):
        record = records[supply_id]
        if record.get("side") == side or record.get("position") != hex_id:
            continue
        unit = _supply_unit(supply_id, record)
        if not supply_unit_captured(enemy_combat_enters=True):
            continue
        ammo, fuel = captured_supply_points(unit)
        captured.append({"id": supply_id, "side": unit.side,
                         "ammo": ammo, "fuel": fuel,
                         "dummy": unit.dummy})
        records.pop(supply_id)
    if not captured:
        return dict(state)
    raw = state.get("supply_captures", ())
    if isinstance(raw, str) or not isinstance(raw, (list, tuple)):
        raise StageError("state['supply_captures'] must be a sequence")
    log = [dict(entry) for entry in raw]
    log.append({"by": unit_id, "side": side, "hex": hex_id,
                "supplies": captured})
    return {**state, "supplies": records, "supply_captures": log}


def _in_off_map(record: Mapping[str, Any]) -> bool:
    """Is this record in a Tripoli/Tunisia box or an In Transit box?"""
    if bool(record.get("off_map_box", False)):
        return True
    position = record.get("position")
    return (isinstance(position, str) and bool(position.strip())
            and is_off_map_position(position))


def moving_unit(unit_id: str, record: Mapping[str, Any]) -> MovingUnit:
    """Build the §8 view of one unit from its state record."""
    return MovingUnit(
        unit_id=unit_id,
        side=str(record.get("side", "")),
        base_cpa=_whole(record.get("base_cpa", 0), name="base_cpa"),
        unit_class=str(record.get("unit_class", "infantry")),
        motorized=bool(record.get("motorized", False)),
        kind=str(record.get("move_kind", "combat")),
        cohesion=_whole(record.get("cohesion", 0), name="cohesion"),
        stacking_points=_fraction(record.get("stacking_points", 1)),
        contact=bool(record.get("contact", False)),
        engaged=bool(record.get("engaged", False)),
        voluntary_spent=_fraction(record.get("voluntary_spent", 0)),
        in_reserve=bool(record.get("in_reserve", False)),
        attached=bool(record.get("attached", True)),
        transport_cpa=(None if record.get("transport_cpa") is None
                       else _whole(record["transport_cpa"],
                                   name="transport_cpa")),
        stacked_with_friendly_combat=bool(
            record.get("stacked_with_friendly_combat", False)),
        size_level=str(record.get("size_level", "battalion")),
        raider=bool(record.get("raider", False)),
        breakdown_points=_fraction(record.get("breakdown_points", 0)),
        breakdown_last_column=(
            None if record.get("breakdown_last_column") is None
            else _whole(record["breakdown_last_column"],
                        name="breakdown_last_column")),
        breakdown_bar=_whole(record.get("breakdown_bar", 0),
                             name="breakdown_bar"),
        toe_points=(None if record.get("toe_points") is None
                    else _fraction(record["toe_points"])),
        off_map_box=_in_off_map(record),
    )


def _off_map_unit(record: Mapping[str, Any]) -> OffMapUnit | None:
    """Build the 8.82-8.88 view of a land unit, or ``None`` if invalid."""
    try:
        return OffMapUnit(
            side=str(record.get("side", "")),
            unit_type="land",
            motorized=bool(record.get("motorized", False)),
            stacking_points=_fraction(record.get("stacking_points", 1)),
            reinforcement_or_replacement=bool(
                record.get("reinforcement_or_replacement", False)),
            arrived_this_stage=bool(record.get("arrived_this_stage", False)),
        )
    except TransportError:
        return None


def _off_map_transit(record: Mapping[str, Any],
                     unit_id: str) -> OffMapTransit | None:
    """Read a unit's persisted transit, rejecting a malformed one."""
    raw = record.get("off_map_transit")
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise StageError(
            f"unit {unit_id!r} off_map_transit must be a mapping")
    origin = raw.get("origin")
    destination = raw.get("destination")
    if not isinstance(origin, str) or not isinstance(destination, str):
        raise StageError(
            f"unit {unit_id!r} off_map_transit needs box names")
    try:
        return OffMapTransit(
            origin=origin,
            destination=destination,
            stages=_whole(raw.get("stages"), name="off_map_transit.stages"),
            elapsed=_whole(raw.get("elapsed", 0),
                           name="off_map_transit.elapsed"),
        )
    except TransportError as exc:
        raise StageError(
            f"unit {unit_id!r} has an invalid off_map_transit: {exc}") from exc


def stacking_unit(unit_id: str, record: Mapping[str, Any]) -> StackingUnit:
    """Build the §9 view of one unit from its state record."""
    return StackingUnit(
        unit_id=unit_id,
        side=str(record.get("side", "")),
        stacking_points=_fraction(record.get("stacking_points", 1)),
        kind=str(record.get("kind", "combat")),
        parent_id=record.get("parent_id"),
        attached_to_parent=bool(record.get("attached_to_parent", False)),
        attached_combat_units=_whole(record.get("attached_combat_units", 0),
                                     name="attached_combat_units"),
        motorized=bool(record.get("motorized", False)),
        assigned_city=record.get("assigned_city"),
        artillery_hq=bool(record.get("artillery_hq", False)),
        zero_plus_cpa=bool(record.get("zero_plus_cpa", False)),
        level=str(record.get("level", "")),
    )


def zoc_unit(unit_id: str, record: Mapping[str, Any]) -> ZocUnit:
    """Build the §10 view of one unit from its state record."""
    return ZocUnit(
        unit_id=unit_id,
        side=str(record.get("side", "")),
        position=_position(record, unit_id),
        stacking_points=_fraction(record.get("stacking_points", 1)),
        cohesion=_whole(record.get("cohesion", 0), name="cohesion"),
        raw_defensive_close_assault=_fraction(
            record.get("raw_defensive_close_assault", 10),
            name="raw_defensive_close_assault"),
        kind=str(record.get("kind", "combat")),
        has_attached_combat=bool(record.get("has_attached_combat", False)),
        pinned=bool(record.get("pinned", False)),
        is_gun=bool(record.get("is_gun", False)),
    )


def zoc_units(state: Mapping[str, Any]) -> tuple[ZocUnit, ...]:
    """Every unit as the §10 module sees it."""
    records = _records(state)
    return tuple(zoc_unit(unit_id, records[unit_id])
                 for unit_id in sorted(records))


def controlled_hexes(state: Mapping[str, Any], side: str,
                     scenario: StageScenario) -> frozenset[str]:
    """Hexes in Enemy ZOC for *side*, after 10.26 (friendly combat negates)."""
    if side not in SIDES:
        raise StageError(f"unknown side: {side!r}")
    can_enter = None
    if scenario.can_enter is not None:
        can_enter = lambda unit, source, destination: bool(  # noqa: E731
            scenario.can_enter(source, destination))
    return enemy_controlled_hexes(
        zoc_units(state), side,
        neighbours=scenario.neighbours,
        blocked_hexside=scenario.blocked_hexside,
        can_enter=can_enter,
    )


# ---------------------------------------------------------------------------
# movement
# ---------------------------------------------------------------------------

def _friendly_combat_hexes(records: Mapping[str, Mapping[str, Any]],
                           side: str) -> frozenset[str]:
    from cna.rules.sec10_zoc import COMBAT_KINDS
    return frozenset(
        _position(record, unit_id)
        for unit_id, record in records.items()
        if record.get("side") == side and record.get("kind", "combat") in COMBAT_KINDS
    )


def _move_context(state: Mapping[str, Any], side: str,
                  scenario: StageScenario) -> MoveContext:
    records = _records(state)
    enemy_occupied = frozenset(
        _position(record, unit_id)
        for unit_id, record in records.items()
        if record.get("side") != side
    )
    controlled = controlled_hexes(state, side, scenario)
    friendly_combat = _friendly_combat_hexes(records, side)
    return MoveContext(
        cost=scenario.cost,
        enemy_occupied=enemy_occupied,
        enemy_zoc=controlled,
        friendly_combat=friendly_combat,
        adjacent=lambda source, destination: destination in set(
            scenario.neighbours(source)),
        phase="movement",
        weather=scenario.weather,
        sandstorm_majority=scenario.sandstorm_majority,
    )


def _distance_to_enemy_combat(state: Mapping[str, Any], side: str,
                              position: str,
                              scenario: StageScenario) -> int | None:
    """8.23: hex distance to the nearest enemy combat unit, up to two.

    ``None`` means no enemy combat unit is within two hexes.  Distance is
    measured through the caller's adjacency graph, not through occupancy.
    """
    enemy_hexes = {
        _position(record, unit_id)
        for unit_id, record in _records(state).items()
        if record.get("side") != side
        and record.get("kind", "combat") in COMBAT_KINDS
    }
    if not enemy_hexes:
        return None
    seen = {position}
    frontier = [position]
    for distance in range(CONTINUE_DISTANCE + 1):
        if any(hex_id in enemy_hexes for hex_id in frontier):
            return distance
        next_frontier: list[str] = []
        for hex_id in frontier:
            for neighbour in scenario.neighbours(hex_id):
                if neighbour not in seen:
                    seen.add(neighbour)
                    next_frontier.append(neighbour)
        frontier = next_frontier
    return None


def legal_moves(state: Mapping[str, Any], side: str,
                scenario: StageScenario, *,
                phase_key: str = "") -> tuple[MoveOption, ...]:
    """Every one-hex move and Close Assault available in this state.

    A move is offered only when §8 accepts the entry, §9 accepts the stop
    (including the Road/Track passage check) and the unit has not finished a
    segment that bars another move in this phase (8.23).  An adjacent
    enemy-occupied hex is offered as a ``combat`` option instead: 8.13 still
    forbids entering it, and resolving the assault is the handoff to the
    Combat Segment.  Illegal entries are omitted, not raised: the decision
    point must not offer a move the rules withhold.
    """
    if side not in SIDES:
        raise StageError(f"unknown side: {side!r}")
    records = _records(state)
    context = _move_context(state, side, scenario)
    assaulted = _assaulted_hexes(state)
    ignore_road_track = (scenario.abstract_supply
                         and road_track_stacking_ignored())
    options: list[MoveOption] = []
    for unit_id in sorted(records):
        record = records[unit_id]
        if record.get("side") != side or record.get("combat_pending"):
            continue
        if _in_off_map(record):
            continue
        finished = bool(phase_key and record.get("moved") == phase_key)
        if record.get("assaulted") == (phase_key or "combat"):
            finished = True
        origin = _position(record, unit_id)
        if not _transport_allowed(record):
            continue
        try:
            unit = moving_unit(unit_id, record)
        except MovementError:
            continue
        first_fuel = record.get("fuel_paid_stage") != _stage_key(state)
        ammo_required = _assault_ammo(record)
        for destination in sorted(set(scenario.neighbours(origin))):
            if destination in context.enemy_occupied:
                if finished or not _assault_ready(unit_id, record):
                    continue
                if _assault_key(phase_key, destination) in assaulted:
                    continue
                if ammo_required and not _supply_can_pay(
                        state, record, ammo=ammo_required):
                    continue
                options.append(MoveOption(
                    unit_id=unit_id, destination=destination,
                    move=CombatMove(destination), stacking=None,
                    combat=True))
                continue
            if finished:
                continue
            try:
                result = move_unit(unit, origin, [destination], context)
            except MovementError:
                continue
            fuel_required = _move_fuel_cost(record, total=result.total,
                                            first=first_fuel)
            if fuel_required and not _supply_can_pay(
                    state, record, fuel=fuel_required):
                continue
            existing = tuple(
                stacking_unit(other_id, other)
                for other_id, other in sorted(records.items())
                if other_id != unit_id
                and _position(other, other_id) == destination
            )
            candidate = stacking_unit(unit_id, record)
            hex_context = HexContext(hex_id=destination,
                                     limit=scenario.limit(destination))
            stacking = check_end_of_movement(
                (*existing, candidate), hex_context)
            if not stacking.allowed:
                continue
            if (scenario.road_track is not None
                    and not ignore_road_track
                    and scenario.road_track(origin, destination)
                    and check_road_passage(existing, candidate,
                                           hex_context) is not None):
                continue
            options.append(MoveOption(unit_id=unit_id,
                                      destination=destination,
                                      move=result, stacking=stacking))
    return tuple(options)


def apply_move(state: Mapping[str, Any], side: str, unit_id: str,
               destination: str, scenario: StageScenario, *,
               phase_key: str = "",
               rng: random.Random | None = None) -> dict[str, Any]:
    """Take one move, returning a new state; the caller's state is untouched.

    An enemy-occupied destination is not entered: the option is a Close
    Assault handoff, so :func:`apply_assault` resolves it and the attacker's
    position stays where it is.
    """
    option = next((candidate for candidate in legal_moves(
        state, side, scenario, phase_key=phase_key)
        if candidate.unit_id == unit_id
        and candidate.destination == destination), None)
    if option is None:
        raise StageError(
            f"{unit_id} may not move to {destination} in this state")
    if option.combat:
        return apply_assault(state, side, unit_id, destination, scenario,
                             phase_key=phase_key, rng=rng)
    records = _records(state)
    record = records[unit_id]
    updated = dict(record)
    updated["position"] = destination
    updated["moved"] = phase_key
    updated["moves"] = _whole(record.get("moves", 0), name="moves") + 1
    updated["spent"] = str(
        _fraction(record.get("spent", 0)) + option.move.total)
    updated["voluntary_spent"] = str(option.move.voluntary_spent)
    stage_key = _stage_key(state)
    first_fuel = record.get("fuel_paid_stage") != stage_key
    fuel_required = _move_fuel_cost(record, total=option.move.total,
                                    first=first_fuel)
    supply_state = state
    if fuel_required:
        supply_id = _supply_link(record)
        if supply_id is not None:
            if not _supply_can_pay(state, record, fuel=fuel_required):
                raise StageError(
                    f"{unit_id} cannot draw {fuel_required} Fuel from "
                    f"Supply Unit {supply_id!r}")
            supply_state = _spend_supply(state, supply_id,
                                         fuel=fuel_required)
            updated["fuel_paid_stage"] = stage_key
            updated["fuel_required"] = fuel_required
            updated["fuel_spent"] = (
                _whole(record.get("fuel_spent", 0), name="fuel_spent")
                + fuel_required)
    check = option.move.breakdown
    if check is not None:
        updated["breakdown_points"] = str(check.points)
        updated["breakdown_column"] = check.column
        updated["breakdown_required"] = check.required
        updated["breakdown_resolved"] = check.resolved
        updated["breakdown_pending"] = check.pending
        if check.last_column is None:
            updated.pop("breakdown_last_column", None)
        else:
            updated["breakdown_last_column"] = check.last_column
        updated.pop("breakdown_percent", None)
        updated.pop("breakdown_losses", None)
        if check.percent is not None:
            updated["breakdown_percent"] = check.percent
        if check.losses is not None:
            updated["breakdown_losses"] = check.losses
    if phase_key:
        # 8.23: a segment that ends within two hexes of an enemy combat
        # unit, or a Reserve unit, may continue in the same phase.
        try:
            continuing = moving_unit(unit_id, updated)
        except MovementError:
            continuing = None
        distance = (None if continuing is None else
                    _distance_to_enemy_combat(state, side, destination,
                                              scenario))
        if continuing is not None and may_continue_moving(
                continuing,
                distance_to_enemy=(CONTINUE_DISTANCE + 1
                                   if distance is None else distance)):
            updated.pop("moved", None)
    records[unit_id] = updated
    result = {
        **supply_state,
        "units": records,
        "actions_in_segment": _whole(
            state.get("actions_in_segment", 0),
            name="actions_in_segment") + 1,
    }
    if updated.get("kind", "combat") in COMBAT_KINDS:
        result = _capture_supplies(result, destination, side, unit_id)
    return result


# ---------------------------------------------------------------------------
# off-map Tripoli/Tunisia transit (8.81-8.89)
# ---------------------------------------------------------------------------

def legal_off_map_moves(state: Mapping[str, Any], side: str,
                        scenario: StageScenario, *,
                        phase_key: str = "") -> tuple[OffMapMove, ...]:
    """Every legal 8.81-8.84 off-map transit step for *side*.

    A land unit in a box may start a charted transit; a unit already in
    transit may continue one step or turn back (8.84).  A step spends the
    unit's whole CPA (8.83) and never checks Breakdown.  The 8.89 chart is
    caller-supplied; without one no off-map option is offered.
    """
    if side not in SIDES:
        raise StageError(f"unknown side: {side!r}")
    if scenario.off_map_chart is None:
        return ()
    records = _records(state)
    options: list[OffMapMove] = []
    for unit_id in sorted(records):
        record = records[unit_id]
        if record.get("side") != side or record.get("combat_pending"):
            continue
        if phase_key and record.get("moved") == phase_key:
            continue
        if not _in_off_map(record):
            continue
        unit = _off_map_unit(record)
        if unit is None or not off_map_entry_allowed(unit):
            continue
        cpa = _whole(record.get("base_cpa", 0), name="base_cpa")
        if cpa < 1:
            continue
        transit = _off_map_transit(record, unit_id)
        origin = (transit.position if transit is not None
                  else _position(record, unit_id))
        if not is_off_map_position(origin):
            continue
        if (origin in (TRIPOLI, TUNIS) and arrival_box_locked(
                origin,
                arrived_this_stage=bool(record.get("arrived_this_stage",
                                                 False)),
                reinforcement_or_replacement=bool(
                    record.get("reinforcement_or_replacement", False)))):
            continue
        if transit is not None and not transit.arrived:
            result = advance_off_map(transit, cp_spent=cpa, cpa=cpa,
                                     motorized=unit.motorized)
            options.append(OffMapMove(unit_id, origin, transit.destination,
                                      "continue", result))
            if transit.elapsed > 0:
                turned = transit.reverse()
                turned_result = advance_off_map(
                    turned, cp_spent=cpa, cpa=cpa, motorized=unit.motorized)
                options.append(OffMapMove(unit_id, origin,
                                          turned.destination, "reverse",
                                          turned_result))
            continue
        for destination in scenario.off_map_boxes:
            if destination == origin:
                continue
            try:
                planned = plan_off_map_move(
                    origin, destination, cpa=cpa,
                    chart=scenario.off_map_chart, unit=unit)
                result = advance_off_map(planned, cp_spent=cpa, cpa=cpa,
                                         motorized=unit.motorized)
            except TransportError:
                continue
            options.append(OffMapMove(unit_id, origin, destination, "start",
                                      result))
    return tuple(options)


def apply_off_map_move(state: Mapping[str, Any], side: str, unit_id: str,
                       destination: str, scenario: StageScenario, *,
                       phase_key: str = "") -> dict[str, Any]:
    """Advance one unit exactly one 8.81-8.84 off-map step."""
    move = next((candidate for candidate in legal_off_map_moves(
        state, side, scenario, phase_key=phase_key)
        if candidate.unit_id == unit_id
        and candidate.destination == destination), None)
    if move is None:
        raise StageError(
            f"{unit_id} may not move off-map to {destination} in this state")
    if move.result.breakdown_check:       # pragma: no cover - 8.83 invariant
        raise StageError("8.83: off-map movement must not check Breakdown")
    records = _records(state)
    record = records[unit_id]
    updated = dict(record)
    transit = move.result.transit
    updated["position"] = transit.position
    updated["moved"] = phase_key
    updated["moves"] = _whole(record.get("moves", 0), name="moves") + 1
    updated["spent"] = str(move.result.cp_spent)
    updated["voluntary_spent"] = "0"
    stage_key = _stage_key(state)
    first_fuel = record.get("fuel_paid_stage") != stage_key
    fuel_required = _move_fuel_cost(record,
                                    total=Fraction(move.result.cp_spent),
                                    first=first_fuel)
    supply_state = state
    if fuel_required:
        supply_id = _supply_link(record)
        if supply_id is not None:
            if not _supply_can_pay(state, record, fuel=fuel_required):
                raise StageError(
                    f"{unit_id} cannot draw {fuel_required} Fuel from "
                    f"Supply Unit {supply_id!r}")
            supply_state = _spend_supply(state, supply_id,
                                         fuel=fuel_required)
            updated["fuel_paid_stage"] = stage_key
            updated["fuel_required"] = fuel_required
            updated["fuel_spent"] = (
                _whole(record.get("fuel_spent", 0), name="fuel_spent")
                + fuel_required)
    updated["off_map_box"] = True
    updated["off_map_transit"] = transit.to_obj()
    updated["off_map_move"] = move.kind
    updated["fuel_required"] = move.result.fuel_required
    if transit.arrived:
        updated["arrived_this_stage"] = True
        updated["arrived_box"] = transit.destination
    else:
        updated.pop("arrived_this_stage", None)
        updated.pop("arrived_box", None)
    records[unit_id] = updated
    result = {
        **supply_state,
        "units": records,
        "actions_in_segment": _whole(
            state.get("actions_in_segment", 0),
            name="actions_in_segment") + 1,
    }
    if (transit.arrived
            and updated.get("kind", "combat") in COMBAT_KINDS):
        result = _capture_supplies(result, transit.destination, side, unit_id)
    return result


# ---------------------------------------------------------------------------
# Close Assault handoff (11.0, 15.0)
# ---------------------------------------------------------------------------

def _assault_key(phase_key: str, target_hex: str) -> str:
    return f"{phase_key or 'combat'}:{target_hex}"


def _assaulted_hexes(state: Mapping[str, Any]) -> frozenset[str]:
    raw = state.get("assaulted_hexes", ())
    if isinstance(raw, str) or not isinstance(raw, (list, tuple, set,
                                                    frozenset)):
        raise StageError("state['assaulted_hexes'] must be a sequence")
    return frozenset(str(entry) for entry in raw)


def _combat_unit(unit_id: str, record: Mapping[str, Any]) -> CombatUnit:
    """Build the §§11-15 view of one unit from its state record."""
    try:
        return CombatUnit(
            unit_id=unit_id,
            side=str(record.get("side", "")),
            hex_id=_position(record, unit_id),
            toe_strength=_fraction(
                record.get("toe_strength", record.get("toe_points", 0)),
                name="toe_strength"),
            offensive_close_assault=_fraction(
                record.get("offensive_close_assault", 0),
                name="offensive_close_assault"),
            defensive_close_assault=_fraction(
                record.get("defensive_close_assault", 0),
                name="defensive_close_assault"),
            target_class=str(record.get("target_class", "infantry")),
            kind=str(record.get("kind", "combat")),
            cohesion=_whole(record.get("cohesion", 0), name="cohesion"),
            stacking_points=_fraction(record.get("stacking_points", 1)),
            parenthesized_close_assault=bool(
                record.get("parenthesized_close_assault", False)),
            tank=bool(record.get("tank", False)),
            recce=bool(record.get("recce", False)),
            hq=bool(record.get("hq", False)),
            motorized=bool(record.get("motorized", False)),
            pinned=bool(record.get("pinned", False)),
            out_of_ammo=bool(record.get("out_of_ammo", False)),
        )
    except CombatError as exc:
        raise StageError(
            f"unit {unit_id!r} is not a combat unit: {exc}") from exc


def _assault_ready(unit_id: str, record: Mapping[str, Any]) -> bool:
    try:
        unit = _combat_unit(unit_id, record)
    except StageError:
        return False
    return (unit.toe_strength > 0 and unit.offensive_close_assault > 0
            and may_close_assault(unit, offensive=True))


def _loss_targets(units: Iterable[CombatUnit]) -> tuple[LossTarget, ...]:
    return tuple(LossTarget(unit.unit_id, unit.toe_strength, Fraction(1),
                            unit.hex_id) for unit in units)


def _apply_combat_losses(records: dict[str, dict[str, Any]],
                         result: Any,
                         participants: Iterable[str]) -> None:
    for uid, amount in result.plan.removals:
        record = records[uid]
        current = _fraction(record.get("toe_strength",
                                       record.get("toe_points", 0)))
        remaining = max(Fraction(0), current - amount)
        if "toe_strength" not in record and "toe_points" not in record:
            record["toe_strength"] = str(remaining)
        else:
            if "toe_strength" in record:
                record["toe_strength"] = str(remaining)
            if "toe_points" in record:
                record["toe_points"] = str(remaining)
        record["combat_losses"] = str(
            _fraction(record.get("combat_losses", 0)) + amount)
    for uid in participants:
        record = records[uid]
        record["combat_engaged"] = result.engaged
        record["combat_contact"] = result.contact
        record["combat_retreat_hexes"] = result.retreat_hexes
        record["combat_disorganization_points"] = result.disorganization_points
        record["combat_surrendered"] = result.surrendered


def apply_assault(state: Mapping[str, Any], side: str, unit_id: str,
                  target_hex: str, scenario: StageScenario, *,
                  phase_key: str = "",
                  rng: random.Random | None = None) -> dict[str, Any]:
    """Resolve one Close Assault against an adjacent enemy-occupied hex.

    Both sides' rolls come from the caller's ``assault_table``; the attacker
    never enters ``target_hex`` (8.13).  Without a table the handoff is
    recorded as ``pending_combat`` and no values are invented.  Losses,
    Engaged/Contact and Disorganization results are written back to the
    participating unit records, and the resolution is appended to
    ``combat_log``.
    """
    if side not in SIDES:
        raise StageError(f"unknown side: {side!r}")
    records = _records(state)
    if unit_id not in records:
        raise StageError(f"unknown unit: {unit_id!r}")
    record = records[unit_id]
    if record.get("side") != side:
        raise StageError(f"{unit_id} does not belong to {side!r}")
    origin = _position(record, unit_id)
    if target_hex not in set(scenario.neighbours(origin)):
        raise StageError(f"{target_hex} is not adjacent to {origin}")
    defenders = sorted(
        other_id for other_id, other in records.items()
        if other_id != unit_id and other.get("side") != side
        and _position(other, other_id) == target_hex)
    if not defenders:
        raise StageError(f"{target_hex} has no enemy unit to assault")
    if _assault_key(phase_key, target_hex) in _assaulted_hexes(state):
        raise StageError(f"{target_hex} was already assaulted this phase")
    try:
        attacker = _combat_unit(unit_id, record)
        defender_units = tuple(_combat_unit(other_id, records[other_id])
                               for other_id in defenders)
    except StageError:
        raise
    if (attacker.toe_strength <= 0 or attacker.offensive_close_assault <= 0
            or not may_close_assault(attacker, offensive=True)):
        raise StageError(f"{unit_id} may not Close Assault")
    ammo_required = _assault_ammo(record)
    if ammo_required and not _supply_can_pay(
            state, record, ammo=ammo_required):
        raise StageError(
            f"{unit_id} cannot draw {ammo_required} Ammo from its linked "
            "Supply Unit")

    updated = {other_id: dict(other) for other_id, other in records.items()}
    pending = {"side": side, "attacker": unit_id, "target": target_hex,
               "origin": origin, "phase": phase_key,
               "defenders": list(defenders)}
    if scenario.assault_table is None:
        updated[unit_id]["combat_pending"] = True
        updated[unit_id]["combat_target"] = target_hex
        updated[unit_id]["moved"] = phase_key
        return {
            **state,
            "units": updated,
            "pending_combat": pending,
            "actions_in_segment": _whole(
                state.get("actions_in_segment", 0),
                name="actions_in_segment") + 1,
        }

    supply_state = state
    supply_id = _supply_link(record)
    if ammo_required and supply_id is not None:
        supply_state = _spend_supply(state, supply_id,
                                     ammo=ammo_required)
    if rng is None:
        rng = random.Random(_whole(state.get("seed", 0), name="seed"))
    try:
        attacker_raw = assault_raw_strength((attacker,), offensive=True)
        defender_raw = assault_raw_strength(defender_units, offensive=False)
        adjusted = assault_differential(attacker_raw=attacker_raw,
                                        defender_raw=defender_raw)
        attack_roll = _two_dice(rng)
        defense_roll = _two_dice(rng)
        attacker_roll = scenario.assault_table(
            "attacker", adjusted.final, attack_roll)
        defender_roll = scenario.assault_table(
            "defender", adjusted.final, defense_roll)
        if not isinstance(attacker_roll, AssaultRoll):
            raise StageError("the assault table must return an AssaultRoll")
        if not isinstance(defender_roll, AssaultRoll):
            raise StageError("the assault table must return an AssaultRoll")
        outcome = resolve_close_assault(
            adjusted=adjusted,
            attacker_roll=attacker_roll,
            defender_roll=defender_roll,
            attacker_raw=attacker_raw,
            defender_raw=defender_raw,
            attacker_targets=_loss_targets((attacker,)),
            defender_targets=_loss_targets(defender_units),
        )
    except CombatError as exc:
        raise StageError(f"Close Assault failed: {exc}") from exc

    _apply_combat_losses(updated, outcome.attacker, (unit_id,))
    _apply_combat_losses(updated, outcome.defender, defenders)
    attacker_record = updated[unit_id]
    attacker_record["assaulted"] = phase_key or "combat"
    attacker_record["moved"] = phase_key
    if ammo_required:
        attacker_record["ammo_required"] = ammo_required
        if supply_id is not None:
            attacker_record["ammo_spent"] = (
                _whole(record.get("ammo_spent", 0), name="ammo_spent")
                + ammo_required)
    attacker_record.pop("combat_pending", None)
    attacker_record.pop("combat_target", None)

    key = _assault_key(phase_key, target_hex)
    assaulted = tuple(sorted(_assaulted_hexes(state) | {key}))
    raw_log = state.get("combat_log", ())
    if isinstance(raw_log, str) or not isinstance(raw_log, (list, tuple)):
        raise StageError("state['combat_log'] must be a sequence")
    log = [dict(entry) for entry in raw_log]
    log.append({
        "phase": phase_key, "attacker": unit_id, "origin": origin,
        "defender_hex": target_hex, "defenders": list(defenders),
        "final": adjusted.final, "rolls": [attack_roll, defense_roll],
        "outcome": outcome.to_obj(), "rule": "15",
    })
    result = {
        **supply_state,
        "units": updated,
        "combat_log": log,
        "assaulted_hexes": list(assaulted),
        "actions_in_segment": _whole(
            state.get("actions_in_segment", 0),
            name="actions_in_segment") + 1,
    }
    if state.get("pending_combat") == pending:
        result.pop("pending_combat", None)
    return result


def resolve_pending_combat(state: Mapping[str, Any],
                           scenario: StageScenario, *,
                           rng: random.Random | None = None) -> dict[str, Any]:
    """Resolve a handoff recorded because no assault table was available."""
    pending = state.get("pending_combat")
    if not isinstance(pending, Mapping) or scenario.assault_table is None:
        return dict(state)
    return apply_assault(
        state, str(pending.get("side", "")),
        str(pending.get("attacker", "")), str(pending.get("target", "")),
        scenario, phase_key=str(pending.get("phase", "")), rng=rng)


# ---------------------------------------------------------------------------
# breakdown resolution
# ---------------------------------------------------------------------------

def _two_dice(rng: random.Random) -> int:
    """21.31: a sequential two-dice read-out, tens then units."""
    return rng.randint(1, 6) * 10 + rng.randint(1, 6)


def resolve_breakdown(state: Mapping[str, Any], unit_id: str,
                      scenario: StageScenario,
                      rng: random.Random) -> dict[str, Any]:
    """21.34-21.35: roll one pending check and record the losses it causes.

    A check is rolled only when the scenario supplies the 21.38 Breakdown
    Table.  Without one it stays pending, so a later call with a table can
    resolve it rather than silently losing the roll.
    """
    records = _records(state)
    if unit_id not in records:
        raise StageError(f"unknown unit: {unit_id!r}")
    record = dict(records[unit_id])
    if not record.get("breakdown_pending") or scenario.breakdown_table is None:
        return {**state, "units": records}
    suppressed = bool(record.get("off_map_box", False))
    roll = None if suppressed else _two_dice(rng)
    check = evaluate_breakdown(
        _fraction(record.get("breakdown_points", 0)),
        last_column=(None if record.get("breakdown_last_column") is None
                     else _whole(record["breakdown_last_column"],
                                 name="breakdown_last_column")),
        bar=_whole(record.get("breakdown_bar", 0), name="breakdown_bar"),
        weather=scenario.weather,
        sandstorm_majority=scenario.sandstorm_majority,
        suppressed=suppressed,
        roll=roll,
        table=None if roll is None else scenario.breakdown_table,
        toe_points=(None if record.get("toe_points") is None
                    else _fraction(record["toe_points"])),
    )
    record["breakdown_points"] = str(check.points)
    record["breakdown_column"] = check.column
    record["breakdown_required"] = check.required
    record["breakdown_resolved"] = check.resolved
    record["breakdown_pending"] = check.pending
    if check.last_column is None:
        record.pop("breakdown_last_column", None)
    else:
        record["breakdown_last_column"] = check.last_column
    record["breakdown_percent"] = check.percent
    record["breakdown_losses"] = check.losses
    if roll is not None:
        record["breakdown_roll"] = roll
    if check.losses is not None:
        record["broken_down_points"] = str(
            _fraction(record.get("broken_down_points", 0)) + check.losses)
    records[unit_id] = record
    return {**state, "units": records}


def resolve_pending_breakdowns(state: Mapping[str, Any], side: str,
                               scenario: StageScenario,
                               rng: random.Random) -> dict[str, Any]:
    """Resolve every 21.24 check pending for *side*, in unit-id order."""
    if side not in SIDES:
        raise StageError(f"unknown side: {side!r}")
    if scenario.breakdown_table is None:
        return dict(state)
    records = _records(state)
    working = state
    for unit_id in sorted(records):
        if records[unit_id].get("side") != side:
            continue
        if not records[unit_id].get("breakdown_pending"):
            continue
        working = resolve_breakdown(working, unit_id, scenario, rng)
    return working


def _rail_usage(state: Mapping[str, Any]) -> RailUsage:
    raw = state.get("rail_used", ())
    if not isinstance(raw, (list, tuple, set, frozenset)):
        raise StageError("state['rail_used'] must be a sequence")
    used: set[tuple[str, str]] = set()
    for entry in raw:
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            raise StageError("rail_used entries must be (line, direction)")
        line, direction = str(entry[0]), str(entry[1])
        if direction not in ("east", "west"):
            raise StageError("rail_used direction must be 'east' or 'west'")
        used.add((line, direction))
    try:
        return RailUsage(frozenset(used))
    except TransportError as exc:
        raise StageError(str(exc)) from exc


def legal_rail_moves(state: Mapping[str, Any], side: str,
                     scenario: StageScenario, *,
                     phase_key: str = "") -> tuple[RailMove, ...]:
    """Every legal single-unit 8.71-8.78 rail move in the current state.

    These are the building blocks for :func:`legal_rail_stacks`; the phase-J
    decision offers the grouped stacks, not these individual moves.
    """
    if side not in SIDES:
        raise StageError(f"unknown side: {side!r}")
    if scenario.rail is None or side != COMMONWEALTH:
        return ()
    records = _records(state)
    enemy_occupied = frozenset(
        _position(record, unit_id)
        for unit_id, record in records.items()
        if record.get("side") != side
    )
    controlled = controlled_hexes(state, side, scenario)
    axis_combat = frozenset(
        _position(record, unit_id)
        for unit_id, record in records.items()
        if record.get("side") == "axis"
        and record.get("kind", "combat") in COMBAT_KINDS
    )
    usage = _rail_usage(state)
    options: list[RailMove] = []
    for unit_id in sorted(records):
        record = records[unit_id]
        if record.get("side") != side:
            continue
        if phase_key and record.get("moved") == phase_key:
            continue
        if _fraction(record.get("spent", 0)) != 0:
            continue
        if _fraction(record.get("voluntary_spent", 0)) != 0:
            continue
        if bool(record.get("contact", False)) or bool(record.get("engaged", False)):
            continue
        if _in_off_map(record):
            continue
        origin = _position(record, unit_id)
        stacking = _fraction(record.get("stacking_points", 1))
        for line in scenario.rail.active_lines():
            if origin not in line.hexes:
                continue
            for destination in line.hexes:
                if destination == origin:
                    continue
                try:
                    move = plan_rail_move(
                        line, unit_id, side=side, phase=RAIL_PHASE,
                        started_on_rail=True, cp_spent=0,
                        in_enemy_zoc=origin in controlled,
                        stacking_points=stacking, origin=origin,
                        destination=destination, enemy_zoc=controlled,
                        enemy_occupied=enemy_occupied,
                        axis_combat_hexes=axis_combat, usage=usage)
                except TransportError:
                    continue
                existing = tuple(
                    stacking_unit(other_id, other)
                    for other_id, other in sorted(records.items())
                    if other_id != unit_id
                    and _position(other, other_id) == destination
                )
                check = check_end_of_movement(
                    (*existing, stacking_unit(unit_id, record)),
                    HexContext(hex_id=destination,
                               limit=scenario.limit(destination)))
                if not check.allowed:          # 8.75/8.77 stacking at the stop
                    continue
                options.append(move)
    return tuple(options)


def _rail_stack_candidates(
        moves: tuple[RailMove, ...]) -> tuple[tuple[RailMove, ...], ...]:
    """Every non-empty subset of *moves* that fits the 8.75 limit."""
    if not moves:
        return ()
    smallest = min(move.stacking_points for move in moves)
    max_size = len(moves) if smallest <= 0 else int(
        RAIL_STACK_LIMIT / smallest)
    candidates: list[tuple[RailMove, ...]] = []
    for size in range(1, max_size + 1):
        for subset in combinations(moves, size):
            total = sum((move.stacking_points for move in subset),
                        Fraction(0))
            if total <= RAIL_STACK_LIMIT:
                candidates.append(subset)
    return tuple(candidates)


def legal_rail_stacks(state: Mapping[str, Any], side: str,
                      scenario: StageScenario, *,
                      phase_key: str = "") -> tuple[RailStackMove, ...]:
    """Every legal 8.72 rail stack, grouped for one phase-J action.

    A stack is one line/direction/origin/destination with one aggregate
    8.75 limit.  Only inclusion-maximal legal subsets are offered: a pair of
    one-point units is one action, while a force over two points is split
    into legal stacks rather than carrying the excess.
    """
    if side not in SIDES:
        raise StageError(f"unknown side: {side!r}")
    individual = legal_rail_moves(state, side, scenario,
                                  phase_key=phase_key)
    grouped: dict[tuple[str, str, str, str], list[RailMove]] = {}
    for move in individual:
        key = (move.line, move.direction, move.origin, move.destination)
        grouped.setdefault(key, []).append(move)

    records = _records(state)
    stacks: list[RailStackMove] = []
    for key in sorted(grouped):
        moves = tuple(sorted(grouped[key], key=lambda move: move.unit_id))
        allowed: list[tuple[RailMove, ...]] = []
        for subset in _rail_stack_candidates(moves):
            destination = subset[0].destination
            existing = tuple(
                stacking_unit(other_id, other)
                for other_id, other in sorted(records.items())
                if _position(other, other_id) == destination
            )
            moving = tuple(stacking_unit(move.unit_id, records[move.unit_id])
                           for move in subset)
            check = check_end_of_movement(
                (*existing, *moving),
                HexContext(hex_id=destination,
                           limit=scenario.limit(destination)))
            if check.allowed:          # 8.75/8.77 stacking at the stop
                allowed.append(subset)

        allowed_ids = [frozenset(move.unit_id for move in subset)
                       for subset in allowed]
        for subset, unit_ids in zip(allowed, allowed_ids):
            if any(unit_ids < other for other in allowed_ids):
                continue
            stacks.append(RailStackMove(subset))
    return tuple(sorted(stacks, key=lambda stack: (
        stack.line, stack.direction, stack.origin, stack.destination,
        -len(stack.unit_ids), stack.unit_ids)))


def apply_rail_stack_move(state: Mapping[str, Any], side: str,
                          unit_ids: Iterable[str], destination: str,
                          scenario: StageScenario, *,
                          phase_key: str = "") -> dict[str, Any]:
    """Take one grouped 8.72 rail stack without spending CP."""
    if isinstance(unit_ids, str):
        raise StageError("unit_ids must be a sequence of unit ids")
    ids = tuple(unit_ids)
    if not ids:
        raise StageError("unit_ids must contain at least one unit")
    if not all(isinstance(unit_id, str) and unit_id.strip()
               for unit_id in ids):
        raise StageError("unit_ids must contain non-empty strings")
    if len(set(ids)) != len(ids):
        raise StageError("unit_ids must contain distinct unit ids")
    ids = tuple(sorted(ids))
    move = next((candidate for candidate in legal_rail_stacks(
        state, side, scenario, phase_key=phase_key)
        if candidate.unit_ids == ids
        and candidate.destination == destination), None)
    if move is None:
        raise StageError(
            f"{', '.join(ids)} may not use rail to {destination} in this state")
    records = _records(state)
    missing = [unit_id for unit_id in ids if unit_id not in records]
    if missing:
        raise StageError(f"unknown unit(s): {', '.join(missing)}")
    for unit_id in ids:
        updated = dict(records[unit_id])
        updated["position"] = destination
        updated["moved"] = phase_key
        updated["moves"] = _whole(updated.get("moves", 0), name="moves") + 1
        updated["spent"] = str(_fraction(updated.get("spent", 0)))
        updated["rail_line"] = move.line
        updated["rail_direction"] = move.direction
        records[unit_id] = updated
    usage = _rail_usage(state).use(move.line, move.direction)
    return {
        **state,
        "units": records,
        "rail_used": [list(entry) for entry in sorted(usage.used)],
        "actions_in_segment": _whole(
            state.get("actions_in_segment", 0),
            name="actions_in_segment") + 1,
    }


def apply_rail_move(state: Mapping[str, Any], side: str,
                    unit_id: str | Iterable[str], destination: str,
                    scenario: StageScenario, *,
                    phase_key: str = "") -> dict[str, Any]:
    """Take a rail move for one unit or a grouped stack, without spending CP.

    The phase-J decision uses :func:`apply_rail_stack_move` directly; this
    entry point keeps the single-unit form and also accepts a unit-id
    sequence for callers that already resolved a stack.
    """
    ids = ((unit_id,) if isinstance(unit_id, str)
           else tuple(unit_id))
    return apply_rail_stack_move(state, side, ids, destination,
                                 scenario, phase_key=phase_key)


# ---------------------------------------------------------------------------
# decisions
# ---------------------------------------------------------------------------

def stage_phases(stage: int) -> tuple[Phase, ...]:
    """The rule 5.2 phases of one Operations Stage, in order."""
    if stage not in (1, 2, 3):
        raise StageError("stage must be 1, 2 or 3")
    return tuple(phase for phase in phases_for_turn()
                 if phase.operations_stage == stage)


def _phase_key(state: Mapping[str, Any], phase: Phase) -> str:
    turn = _whole(state.get("turn", 1), name="turn")
    stage = _whole(state.get("stage", 1), name="stage")
    return f"T{turn}S{stage}.{phase.id}"


def _move_guard(scenario: StageScenario, side: str,
                phase_key: str) -> Callable[[Mapping[str, Any], Action], bool]:
    def guard(state: Mapping[str, Any], action: Action) -> bool:
        unit_id = action.payload.get("unit_id")
        destination = action.payload.get("destination")
        if not isinstance(unit_id, str) or not isinstance(destination, str):
            return False
        return any(
            option.unit_id == unit_id
            and option.destination == destination
            for option in legal_moves(state, side, scenario,
                                      phase_key=phase_key)
        )
    return guard


def _move_effect(scenario: StageScenario, side: str, phase_key: str,
                 rng: random.Random | None = None
                 ) -> Callable[[Mapping[str, Any], Action],
                               Mapping[str, Any]]:
    def effect(state: Mapping[str, Any],
               action: Action) -> Mapping[str, Any]:
        return apply_move(state, side,
                          str(action.payload["unit_id"]),
                          str(action.payload["destination"]),
                          scenario, phase_key=phase_key, rng=rng)
    return effect


def _rail_payload_unit_ids(action: Action) -> tuple[str, ...] | None:
    """Read a rail action's stack, accepting the legacy single-unit shape."""
    raw = action.payload.get("unit_ids")
    if raw is None:
        unit_id = action.payload.get("unit_id")
        if not isinstance(unit_id, str) or not unit_id.strip():
            return None
        return (unit_id,)
    if isinstance(raw, str) or not isinstance(raw, (list, tuple)):
        return None
    ids = tuple(raw)
    if (not ids
            or not all(isinstance(unit_id, str) and unit_id.strip()
                       for unit_id in ids)
            or len(set(ids)) != len(ids)):
        return None
    return tuple(sorted(ids))


def _rail_guard(scenario: StageScenario, side: str,
                phase_key: str) -> Callable[[Mapping[str, Any], Action], bool]:
    def guard(state: Mapping[str, Any], action: Action) -> bool:
        ids = _rail_payload_unit_ids(action)
        destination = action.payload.get("destination")
        if ids is None or not isinstance(destination, str):
            return False
        line = action.payload.get("line")
        direction = action.payload.get("direction")
        return any(
            move.unit_ids == ids and move.destination == destination
            and (line is None or move.line == line)
            and (direction is None or move.direction == direction)
            for move in legal_rail_stacks(state, side, scenario,
                                          phase_key=phase_key)
        )
    return guard


def _rail_effect(scenario: StageScenario, side: str,
                 phase_key: str) -> Callable[[Mapping[str, Any], Action],
                                             Mapping[str, Any]]:
    def effect(state: Mapping[str, Any],
               action: Action) -> Mapping[str, Any]:
        ids = _rail_payload_unit_ids(action)
        if ids is None:
            raise StageError("rail action needs unit_ids")
        return apply_rail_stack_move(state, side, ids,
                                     str(action.payload["destination"]),
                                     scenario, phase_key=phase_key)
    return effect


def _off_map_guard(scenario: StageScenario, side: str,
                   phase_key: str) -> Callable[[Mapping[str, Any], Action],
                                              bool]:
    def guard(state: Mapping[str, Any], action: Action) -> bool:
        unit_id = action.payload.get("unit_id")
        destination = action.payload.get("destination")
        if not isinstance(unit_id, str) or not isinstance(destination, str):
            return False
        return any(
            option.unit_id == unit_id
            and option.destination == destination
            for option in legal_off_map_moves(state, side, scenario,
                                              phase_key=phase_key)
        )
    return guard


def _off_map_effect(scenario: StageScenario, side: str,
                    phase_key: str) -> Callable[[Mapping[str, Any], Action],
                                               Mapping[str, Any]]:
    def effect(state: Mapping[str, Any],
               action: Action) -> Mapping[str, Any]:
        return apply_off_map_move(state, side,
                                  str(action.payload["unit_id"]),
                                  str(action.payload["destination"]),
                                  scenario, phase_key=phase_key)
    return effect


def _end_effect() -> Callable[[Mapping[str, Any], Action],
                              Mapping[str, Any]]:
    def effect(state: Mapping[str, Any],
               action: Action) -> Mapping[str, Any]:
        return {**state, "actions_in_segment": 0}
    return effect


def build_decision(state: Mapping[str, Any], phase: Phase, side: str,
                   scenario: StageScenario, *, step: int = 0,
                   rng: random.Random | None = None) -> Decision:
    """The decision point for one action in one phase.

    The engine resolves a decision point once, so a phase that can take
    several moves needs one point per action; *step* numbers them within
    the phase.  The move guard still keys on the phase; a unit that finished
    a segment beyond 8.23's continuation range is marked ``moved`` and is not
    offered again until the next phase.  A ``combat`` option is a Close
    Assault handoff, not an entry into the enemy hex.
    """
    key = _phase_key(state, phase)
    step = _whole(step, name="step")
    if step < 0:
        raise StageError("step must not be negative")
    moves = (legal_moves(state, side, scenario, phase_key=key)
             if phase.id.split(".")[-1] == "G" else ())
    off_map_moves = (
        legal_off_map_moves(state, side, scenario, phase_key=key)
        if phase.id.split(".")[-1] == "G" else ())
    rail_moves = (legal_rail_stacks(state, side, scenario, phase_key=key)
                  if phase.id.split(".")[-1] == "J" else ())
    actions = [
        Action(
            f"move:{option.unit_id}:{option.destination}",
            label=((f"Assault {option.unit_id} in {option.destination}")
                   if option.combat else
                   (f"Move {option.unit_id} to {option.destination}"
                    + (f" (stop: {option.move.stopped})"
                       if option.move.stopped else ""))),
            guard=_move_guard(scenario, side, key),
            effect=_move_effect(scenario, side, key, rng),
            payload={"unit_id": option.unit_id,
                     "destination": option.destination},
        )
        for option in moves
    ]
    actions.extend(
        Action(
            f"offmap:{move.unit_id}:{move.destination}",
            label=(f"Turn {move.unit_id} back to {move.destination}"
                   if move.kind == "reverse" else
                   f"Move {move.unit_id} off-map to {move.destination}"),
            guard=_off_map_guard(scenario, side, key),
            effect=_off_map_effect(scenario, side, key),
            payload={"unit_id": move.unit_id,
                     "destination": move.destination},
        )
        for move in off_map_moves
    )
    actions.extend(
        Action(
            "rail:" + "+".join(move.unit_ids) + ":" + move.destination,
            label=(f"Rail {', '.join(move.unit_ids)} to {move.destination}")
            if len(move.unit_ids) > 1 else
            f"Rail {move.unit_ids[0]} to {move.destination}",
            guard=_rail_guard(scenario, side, key),
            effect=_rail_effect(scenario, side, key),
            payload={
                "unit_ids": list(move.unit_ids),
                "destination": move.destination,
                "line": move.line,
                "direction": move.direction,
                **({"unit_id": move.unit_ids[0]}
                   if len(move.unit_ids) == 1 else {}),
            },
        )
        for move in rail_moves
    )
    actions.append(Action("end_segment",
                          label=f"End {phase.label}",
                          effect=_end_effect()))
    return Decision(f"{key}#{step}", tuple(actions),
                    prompt=f"{phase.id} {phase.label} - {side}",
                    actor=side)


# ---------------------------------------------------------------------------
# the loop
# ---------------------------------------------------------------------------

def play_operations_stage(
    state: Mapping[str, Any],
    scenario: StageScenario,
    *,
    players: Mapping[str, Any],
    rng: random.Random | None = None,
    stage: int | None = None,
    max_actions: int = 10_000,
) -> StageResult:
    """Play one full Operations Stage and return the new state.

    Every rule 5.2 phase of the stage is visited in order.  In a
    Movement/Combat phase the acting side is offered its legal one-hex
    moves and, when an 8.89 chart is supplied, its legal off-map transit
    steps; in the Commonwealth Rail Movement phase it is offered its legal
    rail stacks.  Either phase may then end; every other phase offers only
    its end.  The loop records each choice through the engine, so history
    and resolutions are part of the returned state.
    """
    if not isinstance(scenario, StageScenario):
        raise StageError("scenario must be a StageScenario")
    if not isinstance(players, Mapping):
        raise StageError("players must be a mapping of side to player")
    rng = rng or random.Random(_whole(state.get("seed", 0), name="seed"))
    stage = _whole(stage if stage is not None else state.get("stage", 1),
                   name="stage")
    phases = stage_phases(stage)
    working = copy.deepcopy(dict(state))
    working["stage"] = stage
    working["rail_used"] = []          # 8.74 resets each Operations Stage
    # 8.86's arrival lock lasts only for the stage of arrival.
    units = working.get("units")
    if isinstance(units, Mapping):
        for record in units.values():
            if isinstance(record, dict):
                record.pop("arrived_this_stage", None)
    actions = moves = combats = 0
    events: list[dict[str, Any]] = []

    for phase in phases:
        side = scenario.player_for(phase.actor)
        if side is None:
            raise StageError(
                f"phase {phase.id} names actor {phase.actor!r}, which is "
                "not one of the two sides")
        player = players.get(side)
        if player is None:
            raise StageError(f"no player was supplied for {side!r}")
        working["phase"] = phase.id
        working["actor"] = side
        working["acting"] = phase.actor
        working["actions_in_segment"] = 0
        step = 0

        while True:
            if actions >= max_actions:
                raise StageError(
                    f"stage {stage} exceeded {max_actions} actions")
            decision = build_decision(working, phase, side, scenario,
                                      step=step, rng=rng)
            offered = legal_actions(decision, working)
            if not offered:
                break
            chosen = player.choose(view(working, side), decision, offered, rng)
            if chosen.id not in {action.id for action in offered}:
                raise StageError(
                    f"{side} chose an action that is not offered: {chosen.id}")
            before_combat = len(working.get("combat_log") or ())
            working = apply(decision, working, chosen)
            fought = len(working.get("combat_log") or ()) > before_combat
            actions += 1
            step += 1
            if fought:
                combats += 1
            if chosen.id.startswith("move:") and not fought:
                # 21.24-21.35: the unit has stopped, so a due check is rolled
                # now.  Without a table the pending check is preserved.
                working = resolve_pending_breakdowns(working, side, scenario,
                                                     rng)
            if chosen.id == "end_segment":
                events.append({"phase": phase.id, "action": chosen.id,
                               "actor": side})
                break
            if not fought:
                moves += 1
            event = {"phase": phase.id, "action": chosen.id, "actor": side}
            if fought:
                event["combat"] = True
            events.append(event)

    return StageResult(state=working, stage=stage, phases=len(phases),
                       actions=actions, moves=moves, combats=combats,
                       completed=True, events=tuple(events))
