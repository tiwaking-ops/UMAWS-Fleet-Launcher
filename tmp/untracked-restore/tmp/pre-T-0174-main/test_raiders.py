"""Raider, POW, weather, fleet and Rommel tests.

RULE: 27.11-31.0

The Raid, Weather, Chariot and Port Capacity tables are R-04/R-07 and are
supplied by the caller as labelled lambdas.
"""

import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cna.rules.sec27_raiders import (
    RaiderError,
    aircraft_may_fly,
    airfield_raid,
    breakdown_shift,
    chariot_raid_allowed,
    construction_weather_allowed,
    delta_movement_allowed,
    departure_points,
    detention_camp_threshold,
    dump_raid,
    effective_weather,
    escapee_recovery_allowed,
    escapee_water_loss,
    fuel_water_factor,
    guard_characteristics,
    guards_required,
    interception_allowed,
    layforce_landing_allowed,
    layforce_landing_cp,
    layforce_replacement_cost,
    layforce_supply_free_stages,
    movement_multiplier,
    naval_barrage_strength,
    offshore_bombardment_allowed,
    pipeline_raid,
    plane_raid,
    port_personnel_blocked,
    port_transfer_capacity,
    prisoner_capability_points,
    prisoner_food_cost,
    prisoner_free_move_hexes,
    prisoner_hex_maximum,
    prisoner_points,
    prisoners_escape,
    raider_breakdown_required,
    raider_capability_points,
    raider_cp_exceeded,
    raider_formation_allowed,
    raider_may_enter_enemy_zoc,
    raider_reform_turns,
    raider_spot_cp,
    raider_spot_required,
    raider_spotted,
    raider_supply_cost,
    raider_water_status,
    river_crossable,
    roads_are_tracks,
    rommel_absence_initiative,
    rommel_absent,
    rommel_capability_points,
    rommel_cpa_bonus,
    rommel_may_react,
    rommel_morale_bonus,
    rommel_raid,
    rommel_raid_allowed,
    rommel_retreat_through_zoc,
    rommel_returns_next_turn,
    sas_capability_points,
    sas_plane_losses,
    sas_raid_allowed,
    sas_raid_interval_ok,
    sas_replacement_cost,
    sas_supply_free_stages,
    season_for,
    ship_aa_always_available,
    ship_after_damage,
    ship_barrage_once_per_stage,
    ship_can_leave_port,
    ship_port_stages_after_barrage,
    ship_repair_allowed,
    ship_sunk,
    transfer_supply_penalty,
    truck_convoy_raid,
    valetta_capacity,
    wadi_crossable,
    water_requirement_multiplier,
    weather_from_table,
    wells_filled,
)


def raises(error_type, call):
    try:
        call()
    except error_type:
        return
    raise AssertionError(f"expected {error_type.__name__}")


# ---------------------------------------------------------------------------
# 27 Raiders
# ---------------------------------------------------------------------------


def test_27_11_13_lrdg_formation_limits():
    """RULE: 27.11."""
    base = dict(kind="lrdg", existing=0, source_type="recce",
                source_at_max_morale=True, german_source=False)
    assert raider_formation_allowed(**base) == (True, "")
    assert raider_formation_allowed(**{**base, "existing": 2}) == (
        False, "27.11")
    assert raider_formation_allowed(**{**base, "source_type": "tank"}) == (
        False, "27.13")
    assert raider_formation_allowed(**{**base,
                                       "source_at_max_morale": False}) == (
        False, "27.12")


def test_27_2_dsa_needs_a_german_source_and_allows_only_one():
    """RULE: 27.2."""
    base = dict(kind="dsa", existing=0, source_type="armored_car",
                source_at_max_morale=True, german_source=True)
    assert raider_formation_allowed(**base) == (True, "")
    assert raider_formation_allowed(**{**base, "german_source": False}) == (
        False, "27.2b")
    assert raider_formation_allowed(**{**base, "existing": 1}) == (
        False, "27.2a")


def test_27_14_16_37_raider_capability_and_reform():
    """RULE: 27.14."""
    assert raider_capability_points() == 50
    assert not raider_cp_exceeded(cp_spent=50)
    assert raider_cp_exceeded(cp_spent=51)
    assert raider_reform_turns() == 4


def test_27_41_44_spotting():
    """RULE: 27.41."""
    assert raider_spot_required(enters_enemy_controlled=True,
                                enemy_enters_hex=False)
    assert raider_spot_required(enters_enemy_controlled=False,
                                enemy_enters_hex=True)
    assert raider_spotted(6)
    assert not raider_spotted(5)
    assert raider_spot_cp() == 1


def test_27_34_35_38_raider_movement_and_supply():
    """RULE: 27.35."""
    assert raider_may_enter_enemy_zoc()
    assert raider_supply_cost() == (1, 2)
    assert raider_water_status(water_taken=True) == "ok"
    assert raider_water_status(water_taken=False) == "eliminated"
    assert not raider_breakdown_required()


def test_27_52_pipeline_raid():
    """RULE: 27.52."""
    assert pipeline_raid(4)
    assert not pipeline_raid(5)


def test_27_53_airfield_raid():
    """RULE: 27.53."""
    base = dict(enemy_combat_units=False, major_city=False,
                landing_strip=False)
    assert airfield_raid(2, **base) == (1, "")
    assert airfield_raid(3, **base) == (0, "")
    assert airfield_raid(1, **{**base, "enemy_combat_units": True}) == (
        0, "27.53")
    assert airfield_raid(1, **{**base, "major_city": True}) == (0, "27.53")
    assert airfield_raid(1, **{**base, "landing_strip": True}) == (0, "27.53")


def test_27_54_plane_raid():
    """RULE: 27.54."""
    base = dict(enemy_combat_units=False, major_city=False)
    assert plane_raid(2, **base).destroyed_fraction == Fraction(1, 10)
    assert plane_raid(2, **base).raider_eliminated is False
    assert plane_raid(3, **base).destroyed_fraction == 0
    assert plane_raid(6, **base).raider_eliminated is True
    raises(RaiderError,
           lambda: plane_raid(3, enemy_combat_units=True, major_city=False))


def test_27_55_56_dump_raid():
    """RULE: 27.55."""
    assert dump_raid(raid_roll=1).supplies_destroyed == Fraction(1, 10)
    assert dump_raid(raid_roll=3).supplies_destroyed == 0
    guarded = dump_raid(raid_roll=2, guarded=True, guard_total=8,
                        guard_raw_defense=7, dummy=True)
    assert guarded.supplies_destroyed == Fraction(1, 10)
    assert guarded.dummy_revealed is True
    lost = dump_raid(raid_roll=2, guarded=True, guard_total=6,
                     guard_raw_defense=7)
    assert lost.raider_eliminated is True
    assert dump_raid(raid_roll=6, guarded=True, guard_total=8,
                     guard_raw_defense=7).raider_eliminated is True


def test_27_58_truck_convoy_raid():
    """RULE: 27.58."""
    assert truck_convoy_raid(1, replacement_points_present=False,
                             all_trucks_replacement=False).trucks_destroyed == 1
    assert truck_convoy_raid(2, replacement_points_present=True,
                             all_trucks_replacement=False).trucks_destroyed == 0
    all_rp = truck_convoy_raid(1, replacement_points_present=True,
                               all_trucks_replacement=True)
    assert all_rp.trucks_destroyed == 0 and all_rp.raider_eliminated
    assert truck_convoy_raid(5, replacement_points_present=True,
                             all_trucks_replacement=False
                             ).raider_eliminated is True


def test_27_59_interception_range():
    """RULE: 27.59."""
    assert interception_allowed(cp_distance=4)
    assert not interception_allowed(cp_distance=5)


def test_27_63_64_raid_on_rommel():
    """RULE: 27.63."""
    assert rommel_raid_allowed(raids_used=3, campaign=True) == (True, "")
    assert rommel_raid_allowed(raids_used=4, campaign=True) == (False, "27.64")
    assert rommel_raid_allowed(raids_used=0, campaign=False) == (True, "")
    assert rommel_raid_allowed(raids_used=1, campaign=False) == (False, "27.64")
    assert rommel_raid(33, lambda roll: "captured") == "captured"


def test_27_72_76_layforce():
    """RULE: 27.72."""
    assert layforce_landing_allowed(full_turn_in_alexandria=True,
                                    coastal_hex=True) == (True, "")
    assert layforce_landing_allowed(full_turn_in_alexandria=False,
                                    coastal_hex=True) == (False, "27.73")
    assert layforce_landing_cp(transporting_hexes=50) == 5
    assert layforce_landing_cp(transporting_hexes=51) == 10
    assert layforce_supply_free_stages() == 1
    assert layforce_replacement_cost() == (3, 12)


def test_27_81_89_special_air_service():
    """RULE: 27.81."""
    assert sas_raid_allowed(enemy_combat_units=False)
    assert not sas_raid_allowed(enemy_combat_units=True)
    assert sas_raid_interval_ok(stages_since_last_raid=6,
                                raids_this_month=0)
    assert not sas_raid_interval_ok(stages_since_last_raid=5,
                                    raids_this_month=0)
    assert not sas_raid_interval_ok(stages_since_last_raid=6,
                                    raids_this_month=1)
    assert sas_plane_losses(10, planes=25) == 3
    assert sas_capability_points(stacked_with_lrdg=False) == 15
    assert sas_capability_points(stacked_with_lrdg=True) == 30
    assert sas_supply_free_stages() == 3
    assert sas_replacement_cost() == (3, 12)


# ---------------------------------------------------------------------------
# 28 Prisoners
# ---------------------------------------------------------------------------


def test_28_11_13_prisoner_points_and_capability():
    """RULE: 28.11."""
    assert prisoner_points(3) == 3
    assert prisoner_free_move_hexes() == 3
    assert prisoner_capability_points() == 8


def test_28_14_prisoner_hex_and_camp_limits():
    """RULE: 28.14."""
    assert prisoner_hex_maximum() == 40
    assert detention_camp_threshold() == 5


def test_28_15_prisoner_food_cost():
    """RULE: 28.15."""
    assert prisoner_food_cost(10) == 2
    assert prisoner_food_cost(6) == 1
    assert prisoner_food_cost(4) == 0


def test_28_16_departure_points():
    """RULE: 28.16."""
    assert departure_points("axis") == ("sirte",)
    assert departure_points("commonwealth") == ("alexandria", "cairo")


def test_28_17_22_guards():
    """RULE: 28.17."""
    assert guards_required(prisoners=3, moving=True) == 3
    assert guards_required(prisoners=3, moving=False) == 1
    assert guards_required(prisoners=0, moving=True) == 0
    assert guard_characteristics() == {"toe": 1, "offensive": 0,
                                       "defensive": 1, "cpa": 10}


def test_28_23_escapes():
    """RULE: 28.23."""
    assert prisoners_escape(prisoners=3, guards=2, guards_abandoned=False)
    assert not prisoners_escape(prisoners=2, guards=2, guards_abandoned=False)
    assert prisoners_escape(prisoners=1, guards=1, guards_abandoned=True)


def test_28_24_escapee_recovery_and_water():
    """RULE: 28.24."""
    assert escapee_recovery_allowed(within_eight_cp=True)
    assert not escapee_recovery_allowed(within_eight_cp=False)
    assert escapee_water_loss(15) == 2


# ---------------------------------------------------------------------------
# 29 Weather
# ---------------------------------------------------------------------------


def test_29_1_seasons():
    """RULE: 29.1."""
    assert season_for(month=3, period=3) == "spring"
    assert season_for(month=6, period=2) == "spring"
    assert season_for(month=6, period=3) == "summer"
    assert season_for(month=9, period=3) == "fall"
    assert season_for(month=12, period=3) == "winter"
    assert season_for(month=1, period=1) == "winter"
    assert season_for(month=3, period=2) == "winter"


def test_29_1_weather_table_is_caller_supplied():
    """RULE: 29.1."""
    assert weather_from_table(53, season="summer",
                              table=lambda roll, season: "hot") == "hot"
    raises(RaiderError,
           lambda: weather_from_table(53, season="summer",
                                      table=lambda roll, season: "fog"))


def test_29_1_unaffected_areas_have_normal_weather():
    """RULE: 29.1."""
    assert effective_weather("sandstorm", affected_area=False) == "normal"
    assert effective_weather("sandstorm", affected_area=True) == "sandstorm"


def test_29_42_43_52_storms_stop_air_and_construction():
    """RULE: 29.43."""
    assert aircraft_may_fly("hot")
    assert not aircraft_may_fly("sandstorm")
    assert not aircraft_may_fly("rainstorm")
    assert not construction_weather_allowed("sandstorm")
    assert not construction_weather_allowed("rainstorm")
    assert construction_weather_allowed("normal")


def test_29_33_44_45_weather_movement_and_breakdown():
    """RULE: 29.44."""
    assert movement_multiplier("sandstorm") == 2
    assert movement_multiplier("hot") == 1
    assert breakdown_shift("hot") == 1
    assert breakdown_shift("sandstorm") == 0
    assert breakdown_shift("sandstorm", sandstorm_majority=True) == 1


def test_29_34_35_hot_weather_supplies():
    """RULE: 29.34."""
    assert fuel_water_factor("hot") == Fraction(95, 100)
    assert fuel_water_factor("normal") == 1
    assert water_requirement_multiplier("hot") == 2
    assert water_requirement_multiplier("normal") == 1


def test_29_55_57_58_rain_terrain():
    """RULE: 29.55."""
    assert not wadi_crossable(weather="rainstorm", on_road=False)
    assert wadi_crossable(weather="rainstorm", on_road=True)
    assert not river_crossable(weather="rainstorm", on_road_or_rail=False)
    assert river_crossable(weather="rainstorm", on_road_or_rail=True)
    assert delta_movement_allowed(weather="rainstorm", on_road_or_rail=False,
                                  already_there=False) is False
    assert delta_movement_allowed(weather="rainstorm", on_road_or_rail=False,
                                  already_there=True) is True
    assert delta_movement_allowed(weather="normal", on_road_or_rail=False,
                                  already_there=False) is True


def test_29_53_56_rain_effects():
    """RULE: 29.56."""
    assert roads_are_tracks("rainstorm")
    assert not roads_are_tracks("normal")
    assert wells_filled("rainstorm")
    assert not wells_filled("hot")


# ---------------------------------------------------------------------------
# 30 Mediterranean Fleet
# ---------------------------------------------------------------------------


def test_30_13_34_ship_damage_reduces_aa_proportionally():
    """RULE: 30.13."""
    assert ship_after_damage(gun_rating=4, aa_rating=8, damage=2) == (2, 4)
    assert ship_after_damage(gun_rating=4, aa_rating=8, damage=6) == (0, 0)
    assert ship_sunk(gun_rating=0)
    assert not ship_sunk(gun_rating=1)


def test_30_36_ship_port_and_repair_rules():
    """RULE: 30.36."""
    assert ship_can_leave_port(gun_rating=3, face_value=4)
    assert not ship_can_leave_port(gun_rating=2, face_value=4)
    assert ship_repair_allowed(consecutive_port_stages=6)
    assert not ship_repair_allowed(consecutive_port_stages=5)


def test_30_21_22_24_offshore_bombardment():
    """RULE: 30.21."""
    assert offshore_bombardment_allowed(distance_hexes=0,
                                        battleship_or_heavy_cruiser=False,
                                        same_hex=True)
    assert offshore_bombardment_allowed(distance_hexes=2,
                                        battleship_or_heavy_cruiser=True,
                                        same_hex=False)
    assert not offshore_bombardment_allowed(distance_hexes=2,
                                            battleship_or_heavy_cruiser=False,
                                            same_hex=False)
    assert not offshore_bombardment_allowed(distance_hexes=3,
                                            battleship_or_heavy_cruiser=True,
                                            same_hex=False)
    assert naval_barrage_strength(gun_rating=6, distance_hexes=1) == 6
    assert naval_barrage_strength(gun_rating=6, distance_hexes=2) == 3
    assert ship_barrage_once_per_stage() == 1
    assert ship_port_stages_after_barrage() == 2
    assert ship_aa_always_available()


def test_30_15_18_fleet_ranges_and_ports():
    """RULE: 30.15."""
    from cna.rules.sec27_raiders import ship_range

    assert ship_range() == 100
    assert valetta_capacity() == 5


def test_30_41_45_chariot_raid_timing():
    """RULE: 30.41."""
    base = dict(year=1941, month=7, planned_stage=1, current_stage=8,
                used=False, campaign=True)
    assert chariot_raid_allowed(**base) == (True, "")
    assert chariot_raid_allowed(**{**base, "month": 6}) == (False, "30.41")
    assert chariot_raid_allowed(**{**base, "current_stage": 7}) == (
        False, "30.42")
    assert chariot_raid_allowed(**{**base, "used": True}) == (False, "30.45")
    assert chariot_raid_allowed(**{**base, "campaign": False}) == (
        False, "30.45")


def test_30_54_58_port_transfer_capacity():
    """RULE: 30.54."""
    assert port_transfer_capacity(port_a=10, port_b=6) == 6
    assert port_personnel_blocked(capacity=6, maximum=10)
    assert not port_personnel_blocked(capacity=7, maximum=10)
    assert transfer_supply_penalty() == 25


# ---------------------------------------------------------------------------
# 31 Rommel
# ---------------------------------------------------------------------------


def test_31_1_4_rommel_effects():
    """RULE: 31.1."""
    assert rommel_capability_points() == 60
    assert rommel_may_react(approached_by_lrdg=False)
    assert not rommel_may_react(approached_by_lrdg=True)
    assert rommel_retreat_through_zoc()
    assert rommel_morale_bonus() == 1
    assert rommel_cpa_bonus(entire_stage=True) == 5
    assert rommel_cpa_bonus(entire_stage=False) == 0


def test_31_4_rommel_absence():
    """RULE: 31.4."""
    assert rommel_absent(12)
    assert not rommel_absent(11)
    assert rommel_absence_initiative() == 3
    assert rommel_returns_next_turn()
