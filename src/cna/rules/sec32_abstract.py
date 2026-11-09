"""Abstract supply and air rules for the ``LAND_ABSTRACT`` ruleset.

RULE: 32.0-32.9

This module implements the Land Game's alternate logistics layer.  It does
not implement the full Logistics Game (§§48-58) or the Air Game (§§33-47);
``LAND_ABSTRACT`` uses this module instead of those systems.

The rules deliberately replace Ammo, Fuel, Stores and Water accounting with
Supply Units and Motorization Points.  Every official chart remains
caller-supplied because it is R-04 data:

* the Axis and Commonwealth Simplified Supply Availability Tables (32.46,
  32.47);
* the Abstract Motorization Point Loss Chart (32.59);
* the Simple Axis Naval Convoy Bombing Chart (32.66);
* the Air Bombardment and Secondary Barrage Targets table (32.74).

The tests use synthetic callables and never present a chart value as history.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Callable, Iterable

RULE = "32.0-32.9"

SIDES = ("axis", "commonwealth")

#: 32.15: a Supply Unit's maximum contents.
SUPPLY_MAX_AMMO = 40
SUPPLY_MAX_FUEL = 60

#: 32.14: stacking is zero, but the hex limits are explicit.
MAJOR_CITY_SUPPLY_LIMIT = 5
OFF_MAP_SUPPLY_LIMIT = 3

#: 32.3: the four movement modes.
SUPPLY_MOVE_MODES = ("land", "rail", "sea", "air")

#: 32.32: Motorization Points needed to carry a Supply Unit.
REAL_SUPPLY_MOTORIZATION = 30
DUMMY_SUPPLY_MOTORIZATION = 6

#: 32.34: the Commonwealth rail load in one direction.
COMMONWEALTH_RAIL_SUPPLY_LIMIT = 2

#: 32.35: Axis coastal shipping per real Supply Unit.
AXIS_COASTAL_TONS_PER_SUPPLY = 2000

#: 32.37: air transport cost and the enemy exclusion radius.
AIR_SUPPLY_FUEL_COST = 12
AIR_SUPPLY_ENEMY_RANGE = 5
AIR_SUPPLY_HEX_TYPES = frozenset({
    "major_city", "village", "tripoli_box", "tunisia_box",
})

#: 32.36: the three Commonwealth sea-supply ports.
COMMONWEALTH_SEA_SUPPLY_PORTS = frozenset({
    "alexandria", "benghazi", "tobruk",
})

#: 32.58: a Motorization Point carrying a Supply Unit.
MOTORIZATION_SUPPLY_CPA = 15
MOTORIZATION_REACTION_CPA_LIMIT = 35

#: 32.62: the Axis convoy-lane load.
AXIS_CONVOY_SUPPLY_LIMIT = 3
AXIS_CONVOY_MOTORIZATION_LIMIT = 20


class AbstractSupplyError(ValueError):
    """An abstract supply, air or motorization input is invalid."""


def _whole(value: object, *, name: str, minimum: int | None = None,
           maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AbstractSupplyError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise AbstractSupplyError(f"{name} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise AbstractSupplyError(f"{name} must be at most {maximum}")
    return value


def _fraction(value: object, *, name: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction, str)):
        raise AbstractSupplyError(f"{name} must be numeric")
    try:
        result = Fraction(value)
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        raise AbstractSupplyError(f"{name} is not a number: {value!r}") from exc
    if result < 0:
        raise AbstractSupplyError(f"{name} must not be negative")
    return result


def _bool(value: object, *, name: str) -> bool:
    if not isinstance(value, bool):
        raise AbstractSupplyError(f"{name} must be a bool")
    return value


def _side(side: object) -> str:
    if side not in SIDES:
        raise AbstractSupplyError(f"unknown side: {side!r}")
    return str(side)


def _two_dice(roll: object) -> int:
    value = _whole(roll, name="roll")
    if not 11 <= value <= 66 or not all(1 <= int(d) <= 6 for d in str(value)):
        raise AbstractSupplyError("roll must be a sequential two-dice read-out")
    return value


# ---------------------------------------------------------------------------
# 32.0-32.1: scope and Supply Units
# ---------------------------------------------------------------------------

def abstract_rules_apply(*, air_game: bool = False,
                         logistics_game: bool = False) -> bool:
    """32.0: the abstract rules replace supply only without the other games."""
    _bool(air_game, name="air_game")
    _bool(logistics_game, name="logistics_game")
    return not air_game and not logistics_game


def ignored_supply_categories() -> tuple[str, ...]:
    """32.11: standard Ammo/Fuel/Stores/Water usage is ignored."""
    return ("ammo", "fuel", "stores", "water")


def supply_attrition_suppressed() -> bool:
    """32.11: no unit suffers attrition from lack of Stores."""
    return True


@dataclass(frozen=True)
class SupplyUnit:
    """32.12-32.15: an abstract Supply Dump counter."""

    side: str
    ammo: int = SUPPLY_MAX_AMMO
    fuel: int = SUPPLY_MAX_FUEL
    dummy: bool = False

    def __post_init__(self) -> None:
        _side(self.side)
        _whole(self.ammo, name="ammo", minimum=0,
               maximum=SUPPLY_MAX_AMMO)
        _whole(self.fuel, name="fuel", minimum=0,
               maximum=SUPPLY_MAX_FUEL)
        _bool(self.dummy, name="dummy")
        if self.dummy and (self.ammo or self.fuel):
            raise AbstractSupplyError("a dummy Supply Unit carries no supplies")

    @property
    def empty(self) -> bool:
        """32.15: both pools at zero removes the unit."""
        return self.ammo == 0 and self.fuel == 0

    def spend(self, *, ammo: int = 0, fuel: int = 0) -> "SupplyUnit":
        """32.15/32.21-32.24: reduce the pools; never go negative."""
        if self.dummy:
            raise AbstractSupplyError("a dummy Supply Unit cannot be drawn upon")
        a = _whole(ammo, name="ammo", minimum=0)
        f = _whole(fuel, name="fuel", minimum=0)
        if a > self.ammo or f > self.fuel:
            raise AbstractSupplyError("Supply Unit does not contain enough points")
        return replace(self, ammo=self.ammo - a, fuel=self.fuel - f)

    def captured(self) -> tuple[int, int]:
        """32.13: an enemy combat unit captures the remaining supplies."""
        return (self.ammo, self.fuel)


def supply_unit_stacking_value() -> Fraction:
    """32.14: a Supply Unit has a stacking value of zero."""
    return Fraction(0)


def supply_unit_hex_limit(*, major_city: bool = False,
                          off_map: bool = False,
                          box: bool = False) -> int | None:
    """32.14: five in a Major City, three in other off-map hexes, unlimited boxes."""
    for name, value in (("major_city", major_city), ("off_map", off_map),
                        ("box", box)):
        _bool(value, name=name)
    if box:
        return None
    if off_map:
        return MAJOR_CITY_SUPPLY_LIMIT if major_city else OFF_MAP_SUPPLY_LIMIT
    return MAJOR_CITY_SUPPLY_LIMIT if major_city else None


def supply_unit_captured(*, enemy_combat_enters: bool) -> bool:
    """32.13: any enemy combat unit entering the hex captures the unit."""
    return _bool(enemy_combat_enters, name="enemy_combat_enters")


def captured_supply_points(unit: SupplyUnit) -> tuple[int, int]:
    """32.13: the captor uses the captured supplies immediately and freely."""
    if not isinstance(unit, SupplyUnit):
        raise AbstractSupplyError("unit must be a SupplyUnit")
    return unit.captured()


def rearrange_supplies(units: Iterable[SupplyUnit], *, phase: str
                       ) -> tuple[SupplyUnit, ...]:
    """32.15: rearrange at no cost among units in one hex during Organization."""
    if phase != "organization":
        raise AbstractSupplyError("supplies may be rearranged only in Organization")
    group = tuple(units)
    if not group:
        return ()
    if any(not isinstance(unit, SupplyUnit) for unit in group):
        raise AbstractSupplyError("every unit must be a SupplyUnit")
    if len({unit.side for unit in group}) != 1:
        raise AbstractSupplyError("supplies in one hex must share a side")
    real = [unit for unit in group if not unit.dummy]
    total_ammo = sum(unit.ammo for unit in real)
    total_fuel = sum(unit.fuel for unit in real)
    capacity_ammo = SUPPLY_MAX_AMMO * len(real)
    capacity_fuel = SUPPLY_MAX_FUEL * len(real)
    if total_ammo > capacity_ammo or total_fuel > capacity_fuel:
        raise AbstractSupplyError("the group cannot hold all of its supplies")
    remaining_ammo, remaining_fuel = total_ammo, total_fuel
    rearranged: list[SupplyUnit] = []
    for unit in group:
        if unit.dummy:
            rearranged.append(unit)
            continue
        ammo = min(SUPPLY_MAX_AMMO, remaining_ammo)
        fuel = min(SUPPLY_MAX_FUEL, remaining_fuel)
        rearranged.append(SupplyUnit(unit.side, ammo, fuel))
        remaining_ammo -= ammo
        remaining_fuel -= fuel
    return tuple(rearranged)


# ---------------------------------------------------------------------------
# 32.16-32.18: drawing, destruction and dummies
# ---------------------------------------------------------------------------

def supply_draw_range(unit_cpa: int) -> int:
    """32.16: one-half of the combat unit's CPA, rounded up."""
    cpa = _whole(unit_cpa, name="unit_cpa", minimum=0)
    return math.ceil(Fraction(cpa, 2))


def supply_trace_kind(*, nonmotorized_infantry: bool) -> str:
    """32.16: infantry trace as infantry; every other unit traces as a truck."""
    return "infantry" if _bool(nonmotorized_infantry,
                               name="nonmotorized_infantry") else "medium_truck"


def supply_line_allowed(*, unit_cpa: int, trace_cost: Fraction | int,
                        nonmotorized_infantry: bool = False,
                        impassable: bool = False,
                        enemy_zoc: bool = False,
                        friendly_unit_in_zoc: bool = False) -> bool:
    """32.16: trace up to half CPA, but never through impassable or bare ZOC."""
    _bool(nonmotorized_infantry, name="nonmotorized_infantry")
    _bool(impassable, name="impassable")
    _bool(enemy_zoc, name="enemy_zoc")
    _bool(friendly_unit_in_zoc, name="friendly_unit_in_zoc")
    if impassable:
        return False
    if enemy_zoc and not friendly_unit_in_zoc:
        return False
    return _fraction(trace_cost, name="trace_cost") <= supply_draw_range(unit_cpa)


def supply_destruction_cp(unit_cpas: Iterable[Fraction | int]) -> Fraction:
    """32.17: half the CPA of every unit in the hex, rounded up."""
    total = sum((_fraction(cpa, name="unit_cpa") for cpa in unit_cpas),
                Fraction(0))
    return Fraction(math.ceil(total / 2))


def supply_destruction_result(*, roll: int,
                              stacking_points: Fraction | int) -> bool:
    """32.17: 1-3 destroys; one or fewer Stacking Points adds one."""
    value = _whole(roll, name="roll", minimum=1, maximum=6)
    points = _fraction(stacking_points, name="stacking_points")
    adjusted = value + (1 if points <= 1 else 0)
    return adjusted in (1, 2, 3)


def supply_destruction_attempt_allowed(*, attempts_this_subsegment: int,
                                       prior_to_movement: bool) -> bool:
    """32.17: one attempt per Supply Unit per sub-segment, before movement."""
    attempts = _whole(attempts_this_subsegment,
                      name="attempts_this_subsegment", minimum=0)
    return _bool(prior_to_movement, name="prior_to_movement") and attempts == 0


def dummy_supply_allowance(real_units: int) -> int:
    """32.18: one dummy for every three real Supply Units received/started."""
    return _whole(real_units, name="real_units", minimum=0) // 3


def dummy_supply_removed(*, discovered: bool) -> bool:
    """32.18: a dummy is removed when discovered."""
    return _bool(discovered, name="discovered")


# ---------------------------------------------------------------------------
# 32.2: expenditures
# ---------------------------------------------------------------------------

def ammo_cost(*, battalion_equivalents: int, combat: str,
              phasing: bool) -> int:
    """32.21-32.22: Assault 1 / Barrage 2 per Bn-Eq, doubled when phasing."""
    count = _whole(battalion_equivalents, name="battalion_equivalents",
                   minimum=0)
    if combat not in ("assault", "barrage"):
        raise AbstractSupplyError("combat must be 'assault' or 'barrage'")
    per = 1 if combat == "assault" else 2
    return count * per * (2 if _bool(phasing, name="phasing") else 1)


def ammo_paid_at_combat() -> bool:
    """32.22: Ammo is expended at the instant of combat."""
    return True


def movement_fuel_cost(*, tank_battalions: int = 0, tank_companies: int = 0,
                       gun_battalions: int = 0, recce_battalions: int = 0,
                       motorization_transports: int = 0,
                       patrolling: bool = False) -> int:
    """32.24: the Fuel Points required by the units moved by land.

    Tank battalion-equivalents cost two; tank company-equivalents and
    Gun/Recce battalion-equivalents cost one.  A Motorization Point group
    transporting infantry, guns or a real Supply Unit costs one.  Patrolling
    never costs supply (32.25).
    """
    values = {
        "tank_battalions": tank_battalions,
        "tank_companies": tank_companies,
        "gun_battalions": gun_battalions,
        "recce_battalions": recce_battalions,
        "motorization_transports": motorization_transports,
    }
    for name, value in values.items():
        _whole(value, name=name, minimum=0)
    if _bool(patrolling, name="patrolling"):
        return 0
    return (2 * values["tank_battalions"] + values["tank_companies"]
            + values["gun_battalions"] + values["recce_battalions"]
            + values["motorization_transports"])


def fuel_for_stage(*, first_move_fuel: int, exceeds_cpa: bool = False) -> int:
    """32.23: first-move Fuel, with another equal cost if CPA is exceeded."""
    cost = _whole(first_move_fuel, name="first_move_fuel", minimum=0)
    return cost * (2 if _bool(exceeds_cpa, name="exceeds_cpa") else 1)


def patrol_supply_cost() -> tuple[int, int]:
    """32.25: Patrolling requires no Ammo or Fuel."""
    return (0, 0)


# ---------------------------------------------------------------------------
# 32.3: movement of Supply Units
# ---------------------------------------------------------------------------

def supply_move_modes() -> tuple[str, ...]:
    """32.31: Supply Units may move by land, rail, sea or air."""
    return SUPPLY_MOVE_MODES


def supply_arrival_stage_move_allowed(*, mode: str,
                                      arriving_this_stage: bool) -> bool:
    """32.31: a unit may use land or rail in its arrival Operations Stage."""
    if mode not in SUPPLY_MOVE_MODES:
        raise AbstractSupplyError(f"unknown supply movement mode: {mode!r}")
    if not _bool(arriving_this_stage, name="arriving_this_stage"):
        return True
    return mode in ("land", "rail")


def motorization_required(*, dummy: bool = False) -> int:
    """32.32: 30 points for a real Supply Unit, six for a dummy."""
    return DUMMY_SUPPLY_MOTORIZATION if _bool(dummy, name="dummy") else \
        REAL_SUPPLY_MOTORIZATION


def supply_motorization_ready(*, assigned_points: int,
                              dummy: bool = False) -> bool:
    """32.32: a Supply Unit needs its minimum Motorization Points to move."""
    points = _whole(assigned_points, name="assigned_points", minimum=0)
    return points >= motorization_required(dummy=dummy)


def supply_motorized_move_allowed(*, phase: str, already_moved: bool,
                                  begins_and_remains_stacked: bool,
                                  phasing: bool = True) -> bool:
    """32.33: one of Movement/Combat or Truck Convoy, with its stacking rule."""
    _bool(already_moved, name="already_moved")
    _bool(begins_and_remains_stacked, name="begins_and_remains_stacked")
    _bool(phasing, name="phasing")
    if already_moved:
        return False
    if not phasing:
        return True
    if phase == "truck_convoy":
        return True
    if phase == "movement":
        return begins_and_remains_stacked
    return False


def commonwealth_rail_supply_allowed(*, phase: str, count: int,
                                     direction_used: bool) -> bool:
    """32.34: up to two Supply Units by rail in one direction per OpStage."""
    amount = _whole(count, name="count", minimum=1)
    _bool(direction_used, name="direction_used")
    return (phase == "rail" and not direction_used
            and amount <= COMMONWEALTH_RAIL_SUPPLY_LIMIT)


def axis_coastal_shipping_tons(supply_units: int) -> int:
    """32.35: each Supply Unit needs 2,000 tons of coastal shipping."""
    return (_whole(supply_units, name="supply_units", minimum=0)
            * AXIS_COASTAL_TONS_PER_SUPPLY)


def axis_coastal_shipping_allowed(*, supply_units: int,
                                  tons_available: int) -> bool:
    """32.35: compare the required tonnage with the mission's capacity."""
    available = _whole(tons_available, name="tons_available", minimum=0)
    return axis_coastal_shipping_tons(supply_units) <= available


def commonwealth_sea_supply_allowed(*, phase: str, origin: str,
                                    destination: str,
                                    port_efficiency: Fraction | int,
                                    used_this_stage: bool,
                                    combat_transport_origin: bool = False,
                                    combat_transport_destination: bool = False
                                    ) -> bool:
    """32.36: one Supply Unit by sea to/from the three named ports."""
    if phase != "naval_convoy_arrival":
        return False
    if origin not in COMMONWEALTH_SEA_SUPPLY_PORTS:
        return False
    if destination not in COMMONWEALTH_SEA_SUPPLY_PORTS:
        return False
    if _bool(used_this_stage, name="used_this_stage"):
        return False
    if _bool(combat_transport_origin, name="combat_transport_origin"):
        return False
    if _bool(combat_transport_destination, name="combat_transport_destination"):
        return False
    return _fraction(port_efficiency, name="port_efficiency") >= Fraction(1, 2)


def air_supply_hex_allowed(hex_type: str) -> bool:
    """32.37: origin and destination must be a major city, village or box."""
    return hex_type in AIR_SUPPLY_HEX_TYPES


def air_supply_transport_allowed(*, phase: str, origin_type: str,
                                 destination_type: str, fuel_available: int,
                                 enemy_combat_within_five: bool,
                                 direction_ok: bool,
                                 destination_hq_ok: bool,
                                 used_this_turn: bool) -> bool:
    """32.37: one Supply Unit by air per Game-Turn, with all restrictions."""
    if phase != "organization":
        return False
    if not air_supply_hex_allowed(origin_type):
        return False
    if not air_supply_hex_allowed(destination_type):
        return False
    if _whole(fuel_available, name="fuel_available", minimum=0) < \
            AIR_SUPPLY_FUEL_COST:
        return False
    for name, value in (
        ("enemy_combat_within_five", enemy_combat_within_five),
        ("direction_ok", direction_ok),
        ("destination_hq_ok", destination_hq_ok),
        ("used_this_turn", used_this_turn),
    ):
        _bool(value, name=name)
    return (not enemy_combat_within_five and direction_ok
            and destination_hq_ok and not used_this_turn)


def air_supply_fuel_cost() -> int:
    """32.37: 12 Fuel Points from a Supply Unit in the origin hex."""
    return AIR_SUPPLY_FUEL_COST


def air_transported_supply_movement_allowed(*, moved_by_air_this_opstage: bool
                                            ) -> bool:
    """32.37: an air-transported Supply Unit may not move that OpStage."""
    return not _bool(moved_by_air_this_opstage,
                     name="moved_by_air_this_opstage")


# ---------------------------------------------------------------------------
# 32.4: availability
# ---------------------------------------------------------------------------

def initial_supply_units(count: int) -> int:
    """32.41: the scenario specifies the starting Supply Units."""
    return _whole(count, name="count", minimum=0)


def planning_lead_turns(side: str) -> int:
    """32.43: Axis plans two Game-Turns ahead; Commonwealth four."""
    return {"axis": 2, "commonwealth": 4}[_side(side)]


def arrival_turn(*, planning_turn: int, side: str) -> int:
    """32.43: the arrival Game-Turn for a planning turn."""
    turn = _whole(planning_turn, name="planning_turn", minimum=1)
    return turn + planning_lead_turns(side)


def supply_arrival_turn_allowed(*, game_turn: int, scenario_start_turn: int,
                                planning_roll_ok: bool) -> bool:
    """32.43: no starting-turn arrival; later turns need a successful plan."""
    game = _whole(game_turn, name="game_turn", minimum=1)
    start = _whole(scenario_start_turn, name="scenario_start_turn", minimum=1)
    return _bool(planning_roll_ok, name="planning_roll_ok") and game > start


def axis_supply_arrival(*, letter: str, roll: int,
                        table: Callable[[str, int], int]) -> int:
    """32.44: cross-index the planning letter and one die on the Axis table."""
    if not isinstance(letter, str) or not letter.strip():
        raise AbstractSupplyError("letter must be a non-empty string")
    value = _whole(roll, name="roll", minimum=1, maximum=6)
    if not callable(table):
        raise AbstractSupplyError("table must be callable")
    return _whole(table(letter, value), name="table result", minimum=0)


def commonwealth_supply_arrival(*, period: str, roll: int,
                                table: Callable[[str, int], int]) -> int:
    """32.45: cross-index the arrival period and one die on the CW table."""
    if not isinstance(period, str) or not period.strip():
        raise AbstractSupplyError("period must be a non-empty string")
    value = _whole(roll, name="roll", minimum=1, maximum=6)
    if not callable(table):
        raise AbstractSupplyError("table must be callable")
    return _whole(table(period, value), name="table result", minimum=0)


def commonwealth_supply_placement(received: int) -> tuple[int, int]:
    """32.42: Cairo normally; if more than three arrive, one per three may go
    to Alexandria.
    """
    count = _whole(received, name="received", minimum=0)
    if count <= 3:
        return (count, 0)
    alexandria = count // 3
    return (count - alexandria, alexandria)


# ---------------------------------------------------------------------------
# 32.5: Motorization Points
# ---------------------------------------------------------------------------

def motorization_points_are_truck_points() -> bool:
    """32.51: Motorization Points are Medium Truck Points in all other respects."""
    return True


def motorization_replacement_limit(*, medium_truck_replacements: int) -> int:
    """32.52: replacement rate equals the Medium Truck replacement ability."""
    return _whole(medium_truck_replacements,
                  name="medium_truck_replacements", minimum=0)


def motorization_can_transport(*, unit_type: str, cpa: int) -> bool:
    """32.53-32.54: leg infantry and Guns with CPA 0+ may be motorized."""
    _whole(cpa, name="cpa", minimum=0)
    return unit_type in ("infantry", "gun")


def motorization_priority_allowed(*, historical_motorized: bool,
                                  historical_unassigned: int) -> bool:
    """32.54: historical motorized infantry are assigned before other infantry."""
    remaining = _whole(historical_unassigned,
                       name="historical_unassigned", minimum=0)
    return not (remaining > 0
                and not _bool(historical_motorized,
                              name="historical_motorized"))


def motorization_breakdown_exempt() -> bool:
    """32.55: Motorization Points are not subject to Breakdown."""
    return True


def motorization_loss(*, assigned_unit_eliminated: bool,
                      assigned_unit_captured: bool) -> str:
    """32.56: lost with an eliminated unit; captured with a captured unit."""
    _bool(assigned_unit_eliminated, name="assigned_unit_eliminated")
    _bool(assigned_unit_captured, name="assigned_unit_captured")
    if assigned_unit_captured:
        return "captured"
    if assigned_unit_eliminated:
        return "lost"
    return "retained"


def abstract_motorization_loss(*, percentage: int, total_points: int
                               ) -> Fraction:
    """32.57: a chart percentage of total Motorization Points, exactly."""
    share = _whole(percentage, name="percentage", minimum=0, maximum=100)
    total = _whole(total_points, name="total_points", minimum=0)
    return Fraction(total * share, 100)


def motorization_supply_cpa() -> int:
    """32.58A: a Motorization Point carrying a Supply Unit has CPA 15."""
    return MOTORIZATION_SUPPLY_CPA


def motorization_supply_excess_action() -> str:
    """32.58B: return to the last hex that did not exceed CPA."""
    return "return_to_last_legal_hex"


def motorization_supply_combat_cp() -> int:
    """32.58C: no CP is required when stacked with combatants in combat."""
    return 0


def motorization_supply_reaction_allowed(*, adjacent_cpa: int) -> bool:
    """32.58D: reaction is allowed unless the adjacent unit has CPA 35+."""
    return _whole(adjacent_cpa, name="adjacent_cpa", minimum=0) < \
        MOTORIZATION_REACTION_CPA_LIMIT


# ---------------------------------------------------------------------------
# 32.6: simplified Axis naval convoys
# ---------------------------------------------------------------------------

def axis_convoy_items() -> tuple[str, ...]:
    """32.61: Supply Units, Motorization Points and Replacement Points."""
    return ("supply_units", "motorization_points", "replacement_points")


def axis_convoy_lane_load_allowed(*, supply_units: int,
                                  motorization_points: int) -> bool:
    """32.62: at most three Supply Units and twenty Motorization Points."""
    supplies = _whole(supply_units, name="supply_units", minimum=0)
    points = _whole(motorization_points, name="motorization_points", minimum=0)
    return (supplies <= AXIS_CONVOY_SUPPLY_LIMIT
            and points <= AXIS_CONVOY_MOTORIZATION_LIMIT)


def axis_convoy_attack_allowed(*, phase: str, lane_announced: bool,
                               weather: str = "normal") -> bool:
    """32.63: attack each announced lane in the Naval Convoy Phase, any weather."""
    _bool(lane_announced, name="lane_announced")
    if not isinstance(weather, str) or not weather:
        raise AbstractSupplyError("weather must be a non-empty string")
    return phase == "naval_convoy" and lane_announced


def convoy_bombing_percent(*, roll: int, bomb_points: int,
                           table: Callable[[int, int], int]) -> int:
    """32.64: the caller's bombing table returns a destruction percentage."""
    value = _two_dice(roll)
    points = _whole(bomb_points, name="bomb_points", minimum=0)
    if not callable(table):
        raise AbstractSupplyError("table must be callable")
    return _whole(table(value, points), name="percent", minimum=0,
                  maximum=100)


def convoy_losses(*, percent: int, supply_units: int,
                  motorization_points: int,
                  replacement_points: int) -> tuple[int, int, int]:
    """32.65: 10% hits only points; 20%+ hits all items, with a floor of one."""
    share = _whole(percent, name="percent", minimum=0, maximum=100)
    supplies = _whole(supply_units, name="supply_units", minimum=0)
    points = _whole(motorization_points, name="motorization_points", minimum=0)
    replacements = _whole(replacement_points,
                          name="replacement_points", minimum=0)
    if share == 0:
        return (0, 0, 0)
    if share <= 10:
        return (0, points * share // 100,
                math.ceil(replacements * share / 100))
    if share < 20:
        raise AbstractSupplyError("convoy losses are 10% or 20%+")
    lost_supplies = max(1, supplies * share // 100) if supplies else 0
    lost_points = max(1, points * share // 100) if points else 0
    lost_replacements = (max(1, replacements * share // 100)
                         if replacements else 0)
    return (lost_supplies, lost_points, lost_replacements)


# ---------------------------------------------------------------------------
# 32.7: bombardment of the Commonwealth Fleet
# ---------------------------------------------------------------------------

FLEET_BOMBARDMENT_WEATHER_EXCLUDED = frozenset({"rainstorm", "sandstorm"})


def fleet_bombardment_attacks(*, roll: int, campaign: bool = False) -> int:
    """32.72: one die, plus two attacks in the Campaign Game."""
    return _whole(roll, name="roll", minimum=1, maximum=6) + (
        2 if _bool(campaign, name="campaign") else 0)


def fleet_bombardment_plot_phase_allowed(*, phase: str) -> bool:
    """32.73: plot during the Commonwealth Fleet Assignment Segment."""
    return phase == "commonwealth_fleet_assignment"


def fleet_bombardment_weather_allowed(*, weather: str) -> bool:
    """32.75: no attack in rainstorm or sandstorm in Game-map Section E."""
    return weather not in FLEET_BOMBARDMENT_WEATHER_EXCLUDED


def fleet_bombardment_phase_allowed(*, phase: str, attacks_this_stage: int,
                                    plotted: bool, weather: str) -> bool:
    """32.73-32.75: one plotted attack per Operations Stage, weather permitting."""
    count = _whole(attacks_this_stage, name="attacks_this_stage", minimum=0)
    _bool(plotted, name="plotted")
    return (phase == "tactical_naval" and count == 0 and plotted
            and fleet_bombardment_weather_allowed(weather=weather))


def fleet_bombardment_column(*, die: int, campaign: bool = False) -> int:
    """32.74a: the table column determined by one die, +2 in the Campaign."""
    value = _whole(die, name="die", minimum=1, maximum=6)
    return value + (2 if _bool(campaign, name="campaign") else 0)


def fleet_bombardment_damage(*, roll: int, column: int,
                             table: Callable[[int, int], int]) -> int:
    """32.74b: two sequential dice on the caller's bombardment table."""
    value = _two_dice(roll)
    col = _whole(column, name="column", minimum=1)
    if not callable(table):
        raise AbstractSupplyError("table must be callable")
    return _whole(table(value, col), name="damage", minimum=0)


# ---------------------------------------------------------------------------
# 32.8: anti-air modifications
# ---------------------------------------------------------------------------

def commonwealth_anti_air_removed(*, kind: str = "unit") -> bool:
    """32.81: all Commonwealth AA units, TOE points and replacements leave play."""
    if kind not in ("unit", "toe", "replacement"):
        raise AbstractSupplyError(f"unknown anti-air kind: {kind!r}")
    return True


def captured_axis_anti_air_removed() -> bool:
    """32.81: captured Axis anti-air TOE points are removed immediately."""
    return True


def german_anti_air_removed(*, id_code: str, heavy: bool,
                            kind: str = "unit") -> bool:
    """32.82: German z/bb units, and all German light AA points, are removed."""
    if kind not in ("unit", "toe", "replacement"):
        raise AbstractSupplyError(f"unknown anti-air kind: {kind!r}")
    if kind == "unit" and id_code in ("z", "bb"):
        return True
    return kind in ("toe", "replacement") and not _bool(heavy, name="heavy")


def italian_anti_air_removed(*, id_code: str, heavy: bool,
                             kind: str = "unit") -> bool:
    """32.83: Italian AA units, pp AA points, kk heavy AA and heavy replacements."""
    if kind not in ("unit", "toe", "replacement"):
        raise AbstractSupplyError(f"unknown anti-air kind: {kind!r}")
    if kind == "unit" and id_code in ("ss", "tt", "uu"):
        return True
    if kind == "toe" and id_code == "pp":
        return True
    if kind in ("toe", "replacement") and _bool(heavy, name="heavy"):
        return id_code == "kk" or kind == "replacement"
    return False


def italian_light_aa_replacement_limit() -> int:
    """32.83.5: Italian light AA replacements are limited to one per month."""
    return 1


def non_anti_air_rating_unaffected() -> bool:
    """32.84: non-AA TOE/replacements with an AA rating are unaffected."""
    return True


# ---------------------------------------------------------------------------
# 32.9: road and track stacking
# ---------------------------------------------------------------------------

def road_track_stacking_ignored() -> bool:
    """32.9: ignore Road/Track-only stacking restrictions."""
    return True
