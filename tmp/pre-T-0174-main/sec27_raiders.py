"""Desert raiders, prisoners, weather, the Mediterranean Fleet and Rommel.

RULE: 27.11-31.0

The Desert Raider, Raid on Rommel, SAS Raid, Weather, Chariot and Port
Capacity tables are R-04/R-07 and stay caller-supplied.  Unit counters,
ship names, ratings and arrival dates are R-06 caller data; this module
implements the procedures only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Callable

RULE = "27.11-31.0"


class RaiderError(ValueError):
    """A raider, prisoner, weather, fleet or Rommel input is invalid."""


def _int(value: Any, *, name: str = "value", minimum: int | None = None,
         maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RaiderError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise RaiderError(f"{name} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise RaiderError(f"{name} must be at most {maximum}")
    return value


def _points(value: Any, *, name: str = "points") -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise RaiderError(f"{name} must be an integer or Fraction")
    result = Fraction(value)
    if result < 0:
        raise RaiderError(f"{name} must not be negative")
    return result


def _bool(value: Any, *, name: str) -> bool:
    if not isinstance(value, bool):
        raise RaiderError(f"{name} must be a bool")
    return value


# ---------------------------------------------------------------------------
# 27 Desert Raiders
# ---------------------------------------------------------------------------

LRDG_MAX = 2                 # 27.11
DSA_MAX = 1                  # 27.2a
RAIDER_CPA = 50              # 27.14, 27.37
LRDG_REFORM_TURNS = 4        # 27.16
SPOT_ROLL = 6                # 27.43
RAID_CP = 5                  # 27.52-27.58
ROMMEL_RAID_CP = 10          # 27.63
SAS_CPA = 15                 # 27.81
SAS_CPA_WITH_LRDG = 30       # 27.88
SAS_RAID_CP = 3              # 27.87
RAIDER_SOURCE_TYPES = frozenset({"recce", "armored_car"})


def raider_formation_allowed(*, kind: str, existing: int, source_type: str,
                             source_at_max_morale: bool,
                             german_source: bool) -> tuple[bool, str]:
    """27.11-27.13, 27.2: form an LRDG or DSA from a trained Recce/AC point."""
    if kind not in ("lrdg", "dsa"):
        raise RaiderError(f"unknown raider kind: {kind!r}")
    count = _int(existing, name="existing", minimum=0)
    if source_type not in RAIDER_SOURCE_TYPES:
        return False, "27.13"
    if not _bool(source_at_max_morale, name="source_at_max_morale"):
        return False, "27.12"
    if kind == "lrdg":
        if count >= LRDG_MAX:
            return False, "27.11"
        return True, ""
    if count >= DSA_MAX:
        return False, "27.2a"
    if not _bool(german_source, name="german_source"):
        return False, "27.2b"
    return True, ""


def raider_capability_points() -> int:
    """27.14, 27.37: fifty, and exceeding it eliminates the raider."""
    return RAIDER_CPA


def raider_cp_exceeded(*, cp_spent: int) -> bool:
    """27.37: a raider forced over 50 CP is eliminated."""
    return _int(cp_spent, name="cp_spent", minimum=0) > RAIDER_CPA


def raider_reform_turns() -> int:
    """27.16: an eliminated LRDG may be formed four Game-Turns later."""
    return LRDG_REFORM_TURNS


def raider_spot_required(*, enters_enemy_controlled: bool,
                         enemy_enters_hex: bool) -> bool:
    """27.41: spotting is triggered by either entry."""
    return (_bool(enters_enemy_controlled, name="enters_enemy_controlled")
            or _bool(enemy_enters_hex, name="enemy_enters_hex"))


def raider_spotted(roll: int) -> bool:
    """27.43: a six eliminates the raider."""
    return _int(roll, name="roll", minimum=1, maximum=6) == SPOT_ROLL


def raider_spot_cp() -> int:
    """27.44: one CP to try to spot, once per Operations Stage."""
    return 1


def raider_may_enter_enemy_zoc() -> bool:
    """27.34: raiders need not stop, but risk being spotted."""
    return True


def raider_supply_cost() -> tuple[int, int]:
    """27.35: one Ammunition and two Fuel Points per Game-Turn."""
    return 1, 2


def raider_water_status(*, water_taken: bool) -> str:
    """27.35: no water by the end of the Game-Turn eliminates the raider."""
    return "ok" if _bool(water_taken, name="water_taken") else "eliminated"


def raider_breakdown_required() -> bool:
    """27.38: raiders do not break down."""
    return False


def pipeline_raid(roll: int) -> bool:
    """27.52: the pipeline is blown on 1-4."""
    return _int(roll, name="roll", minimum=1, maximum=6) <= 4


def airfield_raid(roll: int, *, enemy_combat_units: bool,
                  major_city: bool, landing_strip: bool) -> tuple[int, str]:
    """27.53: a 1 or 2 reduces airfield capacity by one level."""
    value = _int(roll, name="roll", minimum=1, maximum=6)
    _bool(enemy_combat_units, name="enemy_combat_units")
    _bool(major_city, name="major_city")
    _bool(landing_strip, name="landing_strip")
    if landing_strip or major_city or enemy_combat_units:
        return 0, "27.53"
    return (1 if value <= 2 else 0), ""


@dataclass(frozen=True)
class PlaneRaid:
    destroyed_fraction: Fraction
    raider_eliminated: bool

    def to_obj(self) -> dict[str, Any]:
        return {"destroyed_fraction": str(self.destroyed_fraction),
                "raider_eliminated": self.raider_eliminated,
                "rule": "27.54"}


def plane_raid(roll: int, *, enemy_combat_units: bool,
               major_city: bool) -> PlaneRaid:
    """27.54: 1-2 destroys at least 10%, a 6 also eliminates the raider."""
    value = _int(roll, name="roll", minimum=1, maximum=6)
    if _bool(enemy_combat_units, name="enemy_combat_units") or _bool(
            major_city, name="major_city"):
        raise RaiderError("27.54: planes there may not be raided")
    destroyed = Fraction(1, 10) if value <= 2 else Fraction(0)
    return PlaneRaid(destroyed, value == 6)


@dataclass(frozen=True)
class DumpRaid:
    supplies_destroyed: Fraction
    raider_eliminated: bool
    dummy_revealed: bool

    def to_obj(self) -> dict[str, Any]:
        return {"supplies_destroyed": str(self.supplies_destroyed),
                "raider_eliminated": self.raider_eliminated,
                "dummy_revealed": self.dummy_revealed, "rule": "27.55"}


def dump_raid(*, raid_roll: int, guarded: bool = False,
              guard_total: int = 0, guard_raw_defense: int = 0,
              dummy: bool = False) -> DumpRaid:
    """27.55-27.56: unguarded on 1-2; guarded needs 2d6 over Raw Defense."""
    value = _int(raid_roll, name="raid_roll", minimum=1, maximum=6)
    _bool(guarded, name="guarded")
    _bool(dummy, name="dummy")
    if guarded:
        total = _int(guard_total, name="guard_total", minimum=2, maximum=12)
        defense = _int(guard_raw_defense, name="guard_raw_defense", minimum=0)
        if total <= defense:
            return DumpRaid(Fraction(0), True, dummy)
        destroyed = Fraction(1, 10) if value <= 2 else Fraction(0)
        return DumpRaid(destroyed, value == 6, dummy)
    destroyed = Fraction(1, 10) if value <= 2 else Fraction(0)
    return DumpRaid(destroyed, False, dummy)


@dataclass(frozen=True)
class TruckRaid:
    trucks_destroyed: int
    raider_eliminated: bool

    def to_obj(self) -> dict[str, Any]:
        return {"trucks_destroyed": self.trucks_destroyed,
                "raider_eliminated": self.raider_eliminated, "rule": "27.58"}


def truck_convoy_raid(roll: int, *, replacement_points_present: bool,
                      all_trucks_replacement: bool) -> TruckRaid:
    """27.58: 1-2 kills a truck; Replacement cargo raises the risk."""
    value = _int(roll, name="roll", minimum=1, maximum=6)
    any_rp = _bool(replacement_points_present,
                   name="replacement_points_present")
    all_rp = _bool(all_trucks_replacement, name="all_trucks_replacement")
    if all_rp:
        return TruckRaid(0, True)
    if any_rp:
        value += 1
        if value >= 6:
            return TruckRaid(0, True)
    return TruckRaid(1 if value <= 2 else 0, False)


def interception_allowed(*, cp_distance: int) -> bool:
    """27.59: intercept a convoy passing within four Movement CP."""
    return _int(cp_distance, name="cp_distance", minimum=0) <= 4


def rommel_raid_allowed(*, raids_used: int, campaign: bool) -> tuple[bool, str]:
    """27.64: four raids in a campaign, one in a shorter scenario."""
    used = _int(raids_used, name="raids_used", minimum=0)
    limit = 4 if _bool(campaign, name="campaign") else 1
    if used >= limit:
        return False, "27.64"
    return True, ""


def rommel_raid(roll: int, table: Callable[[int], str]) -> str:
    """27.63: two dice on the caller's Raid on Rommel Table."""
    value = _int(roll, name="roll")
    if not (11 <= value <= 66) or not all(1 <= int(d) <= 6 for d in str(value)):
        raise RaiderError("roll must be a sequential two-dice read-out")
    return table(value)


def layforce_landing_allowed(*, full_turn_in_alexandria: bool,
                             coastal_hex: bool,
                             transporting_hexes: int = 0) -> tuple[bool, str]:
    """27.72-27.73: one full Game-Turn in Alexandria before any coastal landing."""
    _bool(coastal_hex, name="coastal_hex")
    _int(transporting_hexes, name="transporting_hexes", minimum=0)
    if not _bool(full_turn_in_alexandria, name="full_turn_in_alexandria"):
        return False, "27.73"
    if not coastal_hex:
        return False, "27.72"
    return True, ""


def layforce_landing_cp(*, transporting_hexes: int) -> int:
    """27.73: 5 CP per 50 hexes moved by the transports."""
    hexes = _int(transporting_hexes, name="transporting_hexes", minimum=0)
    return 5 * math.ceil(hexes / 50)


def layforce_supply_free_stages() -> int:
    """27.74: the landing Stage needs no supplies."""
    return 1


def layforce_replacement_cost() -> tuple[int, int]:
    """27.76: three Infantry Replacement Points trained for 12 OpStages."""
    return 3, 12


def sas_supply_free_stages() -> int:
    """27.84: three OpStages of supply after sea or air transport."""
    return 3


def sas_raid_allowed(*, enemy_combat_units: bool) -> bool:
    """27.82, 27.85: no raid while Axis combat units hold the facility."""
    return not _bool(enemy_combat_units, name="enemy_combat_units")


def sas_raid_interval_ok(*, stages_since_last_raid: int,
                         raids_this_month: int) -> bool:
    """27.87: one raid per month and six OpStages between raids."""
    stages = _int(stages_since_last_raid, name="stages_since_last_raid",
                  minimum=0)
    used = _int(raids_this_month, name="raids_this_month", minimum=0)
    return stages >= 6 and used < 1


def sas_plane_losses(percent: int, *, planes: int) -> int:
    """27.86: remove the table percentage of each type and make present."""
    share = _int(percent, name="percent", minimum=0, maximum=100)
    count = _int(planes, name="planes", minimum=0)
    return math.ceil(count * share / 100)


def sas_capability_points(*, stacked_with_lrdg: bool) -> int:
    """27.81, 27.88: 15 CP, or 30 when stacked with an LRDG."""
    return SAS_CPA_WITH_LRDG if _bool(stacked_with_lrdg,
                                      name="stacked_with_lrdg") else SAS_CPA


def sas_replacement_cost() -> tuple[int, int]:
    """27.89: three Infantry Replacement Points over 12 OpStages."""
    return 3, 12


# ---------------------------------------------------------------------------
# 28 Prisoners
# ---------------------------------------------------------------------------

PRISONER_CP = 8              # 28.13
PRISONER_HEX_MAX = 40        # 28.14
DETENTION_CAMP_POINTS = 5    # 28.14
GUARD_CP = 10                # 28.22


def prisoner_points(infantry_toe: int) -> int:
    """28.11: one Prisoner Point per infantry TOE Point, never tanks or guns."""
    return _int(infantry_toe, name="infantry_toe", minimum=0)


def prisoner_free_move_hexes() -> int:
    """28.12: three hexes immediately after surrender."""
    return 3


def prisoner_capability_points() -> int:
    """28.13: eight, for movement only."""
    return PRISONER_CP


def prisoner_hex_maximum() -> int:
    """28.14: forty Prisoner Points per hex."""
    return PRISONER_HEX_MAX


def detention_camp_threshold() -> int:
    """28.14: more than five standing points may form a camp."""
    return DETENTION_CAMP_POINTS


def prisoner_food_cost(points: int) -> int:
    """28.15: one Store per five Prisoner Points per Operations Stage."""
    return _int(points, name="points", minimum=0) // 5


def departure_points(side: str) -> tuple[str, ...]:
    """28.16: Sirte for the Axis; Alexandria or Cairo for the Commonwealth."""
    if side == "axis":
        return ("sirte",)
    if side == "commonwealth":
        return ("alexandria", "cairo")
    raise RaiderError(f"unknown side: {side!r}")


def guards_required(*, prisoners: int, moving: bool) -> int:
    """28.17: one guard per camp; one per Prisoner Point when moving."""
    count = _int(prisoners, name="prisoners", minimum=0)
    if count == 0:
        return 0
    return count if _bool(moving, name="moving") else 1


def guard_characteristics() -> dict[str, Any]:
    """28.22: a Guard Point is 1 TOE infantry with 0/1 ratings and CPA 10."""
    return {"toe": 1, "offensive": 0, "defensive": 1, "cpa": GUARD_CP}


def prisoners_escape(*, prisoners: int, guards: int,
                     guards_abandoned: bool) -> bool:
    """28.23: excess prisoners without guards escape."""
    count = _int(prisoners, name="prisoners", minimum=0)
    watch = _int(guards, name="guards", minimum=0)
    return _bool(guards_abandoned, name="guards_abandoned") or count > watch


def escapee_recovery_allowed(*, within_eight_cp: bool) -> bool:
    """28.24: within 8 CP they join a Friendly unit and become Replacements."""
    return _bool(within_eight_cp, name="within_eight_cp")


def escapee_water_loss(points: int) -> int:
    """28.24: 10% per waterless OpStage, rounded up."""
    return math.ceil(_int(points, name="points", minimum=0) * 10 / 100)


# ---------------------------------------------------------------------------
# 29 Weather
# ---------------------------------------------------------------------------

WEATHERS = ("normal", "hot", "sandstorm", "rainstorm")
STORMY = frozenset({"sandstorm", "rainstorm"})
SEASON_STARTS = {"spring": (3, 3), "summer": (6, 3), "fall": (9, 3),
                 "winter": (12, 3)}
SEASON_ENDS = {"spring": (6, 2), "summer": (9, 2), "fall": (12, 2),
               "winter": (3, 2)}


def season_for(*, month: int, period: int) -> str:
    """29.1: the season of a Game-Turn, periods I-III."""
    month_ = _int(month, name="month", minimum=1, maximum=12)
    period_ = _int(period, name="period", minimum=1, maximum=3)
    key = (month_, period_)
    for season in ("spring", "summer", "fall", "winter"):
        start, end = SEASON_STARTS[season], SEASON_ENDS[season]
        if season == "winter":
            if key >= start or key <= end:
                return season
        elif start <= key <= end:
            return season
    raise RaiderError(f"no season for {key!r}")


def weather_from_table(roll: int, *, season: str,
                       table: Callable[[int, str], str]) -> str:
    """29.1: two sequential dice on the caller's Weather Table."""
    value = _int(roll, name="roll")
    if not (11 <= value <= 66) or not all(1 <= int(d) <= 6 for d in str(value)):
        raise RaiderError("roll must be a sequential two-dice read-out")
    if season not in SEASON_STARTS:
        raise RaiderError(f"unknown season: {season!r}")
    weather = table(value, season)
    if weather not in WEATHERS:
        raise RaiderError(f"unknown weather from table: {weather!r}")
    return weather


def effective_weather(weather: str, *, affected_area: bool) -> str:
    """29.1: map sections not named by the Foul Weather Table stay normal."""
    if weather not in WEATHERS:
        raise RaiderError(f"unknown weather: {weather!r}")
    if weather in STORMY and not _bool(affected_area, name="affected_area"):
        return "normal"
    return weather


def aircraft_may_fly(weather: str) -> bool:
    """29.43, 29.52: no flying into or out of a storm."""
    return weather not in STORMY


def construction_weather_allowed(weather: str) -> bool:
    """29.42, 29.54: no construction in a storm."""
    return weather not in STORMY


def movement_multiplier(weather: str) -> int:
    """29.44: sandstorm hexes cost double."""
    return 2 if weather == "sandstorm" else 1


def breakdown_shift(weather: str, *, sandstorm_majority: bool = False) -> int:
    """29.33, 29.45: Hot is +1; Sandstorm is +1 with majority movement."""
    return _int(0) if weather == "normal" else (
        1 if weather == "hot" or (weather == "sandstorm"
                                  and _bool(sandstorm_majority,
                                            name="sandstorm_majority")) else 0)


def fuel_water_factor(weather: str) -> Fraction:
    """29.34: all Fuel and Water Levels are reduced by 5% in Hot weather."""
    return Fraction(95, 100) if weather == "hot" else Fraction(1)


def water_requirement_multiplier(weather: str) -> int:
    """29.35: water requirements double in Hot weather."""
    return 2 if weather == "hot" else 1


def wadi_crossable(*, weather: str, on_road: bool) -> bool:
    """29.55: wadis are uncrossable in rain except by road."""
    if weather == "rainstorm":
        return _bool(on_road, name="on_road")
    return True


def river_crossable(*, weather: str, on_road_or_rail: bool) -> bool:
    """29.57: non-road rivers are impassable in rain."""
    if weather == "rainstorm":
        return _bool(on_road_or_rail, name="on_road_or_rail")
    return True


def delta_movement_allowed(*, weather: str, on_road_or_rail: bool,
                           already_there: bool) -> bool:
    """29.58: vehicles need a road in a delta during rain, or must remain."""
    if weather != "rainstorm":
        return True
    return _bool(on_road_or_rail, name="on_road_or_rail") or _bool(
        already_there, name="already_there")


def roads_are_tracks(weather: str) -> bool:
    """29.56: roads use track costs and breakdown rates in rain."""
    return weather == "rainstorm"


def wells_filled(weather: str) -> bool:
    """29.53: all depleted wells refill in a rainstorm."""
    return weather == "rainstorm"


# ---------------------------------------------------------------------------
# 30 Commonwealth Mediterranean Fleet
# ---------------------------------------------------------------------------

SHIP_RANGE = 100             # 30.15
VALETTA_MAX = 5              # 30.18
SHIP_REPAIR_STAGES = 6       # 30.37
CHARIOT_PLANNING_STAGES = 6  # 30.42


def ship_range() -> int:
    """30.15: one hundred sea hexes from Alexandria."""
    return SHIP_RANGE


def valetta_capacity() -> int:
    """30.18: at most five ships in Valetta."""
    return VALETTA_MAX


def ship_after_damage(*, gun_rating: int, aa_rating: int,
                      damage: int) -> tuple[int, int]:
    """30.13, 30.34: Gun Rating is strength; AA falls in proportion."""
    gun = _int(gun_rating, name="gun_rating", minimum=1)
    aa = _int(aa_rating, name="aa_rating", minimum=0)
    lost = _int(damage, name="damage", minimum=0)
    left = max(0, gun - lost)
    return left, math.floor(aa * left / gun)


def ship_sunk(*, gun_rating: int) -> bool:
    """30.36: a ship with no Gun Rating left is sunk."""
    return _int(gun_rating, name="gun_rating", minimum=0) == 0


def ship_can_leave_port(*, gun_rating: int, face_value: int) -> bool:
    """30.36: must be repaired above 50% before leaving port."""
    gun = _int(gun_rating, name="gun_rating", minimum=0)
    face = _int(face_value, name="face_value", minimum=1)
    return gun * 2 > face


def ship_repair_allowed(*, consecutive_port_stages: int) -> bool:
    """30.37: six consecutive Stages in Alexandria repairs one Gun Rating."""
    return _int(consecutive_port_stages, name="consecutive_port_stages",
                minimum=0) >= SHIP_REPAIR_STAGES


def offshore_bombardment_allowed(*, distance_hexes: int,
                                 battleship_or_heavy_cruiser: bool,
                                 same_hex: bool) -> bool:
    """30.21: any ship in the hex; only 4-pointers may fire at two hexes."""
    distance = _int(distance_hexes, name="distance_hexes", minimum=0)
    if _bool(same_hex, name="same_hex"):
        return True
    if distance > 2:
        return False
    return _bool(battleship_or_heavy_cruiser,
                 name="battleship_or_heavy_cruiser")


def naval_barrage_strength(*, gun_rating: int, distance_hexes: int) -> int:
    """30.22: battleships and heavy cruisers halve at two hexes."""
    gun = _int(gun_rating, name="gun_rating", minimum=0)
    distance = _int(distance_hexes, name="distance_hexes", minimum=0)
    if distance >= 2:
        return gun // 2
    return gun


def ship_barrage_once_per_stage() -> int:
    """30.24: one barrage per ship per Operations Stage."""
    return 1


def ship_port_stages_after_barrage() -> int:
    """30.25: two Operations Stages in Alexandria after bombarding."""
    return 2


def ship_aa_always_available() -> bool:
    """30.38: AA fire is always possible, even while repairing."""
    return True


def chariot_raid_allowed(*, year: int, month: int, planned_stage: int,
                         current_stage: int, used: bool,
                         campaign: bool) -> tuple[bool, str]:
    """30.41-30.45: from July 1941, six Stages planned, once per campaign."""
    year_ = _int(year, name="year", minimum=1900)
    month_ = _int(month, name="month", minimum=1, maximum=12)
    planned = _int(planned_stage, name="planned_stage", minimum=0)
    current = _int(current_stage, name="current_stage", minimum=0)
    if (year_, month_) < (1941, 7):
        return False, "30.41"
    if not _bool(campaign, name="campaign"):
        return False, "30.45"
    if _bool(used, name="used"):
        return False, "30.45"
    if current - planned != CHARIOT_PLANNING_STAGES + 1:
        return False, "30.42"
    return True, ""


def chariot_raid(roll: int, table: Callable[[int], str]) -> str:
    """30.44: one die on the caller's Chariot Table."""
    return table(_int(roll, name="roll", minimum=1, maximum=6))


def port_transfer_capacity(*, port_a: int, port_b: int) -> int:
    """30.54: the smaller of the two port personnel capacities."""
    return min(_int(port_a, name="port_a", minimum=0),
               _int(port_b, name="port_b", minimum=0))


def port_personnel_blocked(*, capacity: int, maximum: int) -> bool:
    """30.58: below two thirds, rounded up, no personnel move."""
    have = _int(capacity, name="capacity", minimum=0)
    full = _int(maximum, name="maximum", minimum=1)
    return have < math.ceil(full * 2 / 3)


def transfer_supply_penalty() -> int:
    """30.57: a port that moves troops loses 25% of its supply capacity."""
    return 25


# ---------------------------------------------------------------------------
# 31 Rommel
# ---------------------------------------------------------------------------

ROMMEL_CPA = 60              # 31.1
ROMMEL_CPA_BONUS = 5         # 31.4
ROMMEL_MORALE_BONUS = 1      # 31.3
ROMMEL_ABSENCE_ROLL = 12     # 31.4
ROMMEL_ABSENCE_INITIATIVE = 3


def rommel_capability_points() -> int:
    """31.1: sixty CP, treated as a medium truck."""
    return ROMMEL_CPA


def rommel_may_react(*, approached_by_lrdg: bool) -> bool:
    """31.2: Rommel may react and retreat before assault, except versus LRDG."""
    return not _bool(approached_by_lrdg, name="approached_by_lrdg")


def rommel_retreat_through_zoc() -> bool:
    """31.2: Rommel retreats through an Enemy ZOC with impunity."""
    return True


def rommel_morale_bonus() -> int:
    """31.3: all units in Rommel's stack gain +1 Morale."""
    return ROMMEL_MORALE_BONUS


def rommel_cpa_bonus(*, entire_stage: bool) -> int:
    """31.4: five extra CP for a unit he stays with for the whole Stage."""
    return ROMMEL_CPA_BONUS if _bool(entire_stage,
                                     name="entire_stage") else 0


def rommel_absent(roll: int) -> bool:
    """31.4: a two-dice total of 12 sends Rommel to Germany."""
    value = _int(roll, name="roll")
    if not (11 <= value <= 66) or not all(1 <= int(d) <= 6 for d in str(value)):
        raise RaiderError("roll must be a sequential two-dice read-out")
    return value == ROMMEL_ABSENCE_ROLL


def rommel_absence_initiative() -> int:
    """31.4: Axis Initiative falls to 3 while Rommel is away."""
    return ROMMEL_ABSENCE_INITIATIVE


def rommel_returns_next_turn() -> bool:
    """31.4: he returns the next Game-Turn unless another 12 is rolled."""
    return True
