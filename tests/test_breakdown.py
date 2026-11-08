"""Breakdown, repair, construction, fortification and minefield tests.

RULE: 21.11-26.26

Breakdown, repair and construction tables are R-04 and are supplied by the
caller; the tests use explicit lambdas and check the rule procedure around
them, never a table entry.
"""

import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cna.rules.sec21_breakdown import (
    BREAKDOWN_TYPES,
    BreakdownError,
    BreakdownTrack,
    air_bombardment_affects_level3_city,
    air_facility_construction,
    breakdown_bar,
    breakdown_check_required,
    breakdown_column,
    breakdown_percent,
    capture_tow_hexes,
    column_for,
    construction_completion_stage,
    construction_stage_counts,
    construction_supplies_ok,
    constructed_fortification_max,
    destroyed_tank_repair,
    destroyed_tank_supply_cost,
    distribute_evenly,
    dummy_minefield_removal_phase,
    engineer_assault_column_bonus,
    engineer_can_build_bridges,
    engineer_minefield_additional_cp,
    facility_repair_allowed,
    facility_repair_modifier,
    facility_supply_cost,
    field_recce_repair,
    field_repair_allowed,
    field_tank_fuel_cost,
    field_tank_repair,
    field_truck_repair,
    forced_breakdown_share,
    fortification_affects_movement_or_breakdown,
    fortification_allowed,
    fortification_level,
    fortification_rebuild_in_zoc_allowed,
    friendly_minefield_engineer_cost,
    hot_water_cost,
    losses_from_percent,
    minefield_construction,
    minefield_construction_cost,
    minefield_defender_column_shift,
    minefield_entry_cp,
    minefield_removal_allowed,
    minefield_vehicle_loss,
    pinned_ignored_in_level3_city,
    railroad_build_stages,
    railroad_rebuild_limit,
    railroad_rebuild_stores,
    repair_phase_allowed,
    repair_weather_allowed,
    repaired_vehicle_training_required,
    road_build_capacity,
    road_build_cost,
    supply_dump_cost,
    tds_characteristics,
    tds_destroyed_tank_success,
    tds_elimination_return_turns,
    tds_field_repair_modifier,
    temporary_repair_dismantle_returns,
    temporary_repair_facility_allowed,
    tow_direction_ok,
    towing_allowed,
    towing_cp_per_repair_phase,
    towing_supply_cost,
    vehicle_capture_allowed,
    weather_column_shift,
)


def raises(error_type, call):
    try:
        call()
    except error_type:
        return
    raise AssertionError(f"expected {error_type.__name__}")


# ---------------------------------------------------------------------------
# 21 Breakdown
# ---------------------------------------------------------------------------


def test_21_11_only_vehicle_types_break_down():
    """RULE: 21.11."""
    assert BREAKDOWN_TYPES == {"truck", "tank", "recce", "armored_car",
                               "sp_gun"}
    raises(BreakdownError, lambda: breakdown_bar("infantry"))


def test_21_12_14_fixed_breakdown_adjustment_ratings():
    """RULE: 21.12."""
    assert breakdown_bar("truck") == -2
    assert breakdown_bar("armored_car") == -1
    assert breakdown_bar("recce") == 0
    assert breakdown_bar("tank", chart_bar=1) == 1
    raises(BreakdownError, lambda: breakdown_bar("tank"))


def test_21_15_off_map_boxes_never_check():
    """RULE: 21.15."""
    from cna.rules.sec21_breakdown import breakdown_check_suppressed

    assert breakdown_check_suppressed(True)
    assert not breakdown_check_suppressed(False)


def test_21_27_three_points_are_not_enough():
    """RULE: 21.27."""
    assert column_for(3) is None
    assert column_for(Fraction(7, 2)) == 4


def test_21_31_columns_and_rounding_up():
    """RULE: 21.31."""
    assert column_for(4) == 4
    assert column_for(10) == 4
    assert column_for(11) == 11
    assert column_for(Fraction(41, 2)) == 21
    assert column_for(70) == 61
    assert column_for(71) == 71


def test_21_32_hot_weather_shifts_one_column_right():
    """RULE: 21.32."""
    assert weather_column_shift("hot") == 1
    assert breakdown_column(10, weather="hot") == 11
    assert breakdown_column(10, bar=-2, weather="hot") is None


def test_21_33_column_adjustment_clamps():
    """RULE: 21.33."""
    assert breakdown_column(71, bar=2) == 71
    assert breakdown_column(4, bar=-2) is None


def test_21_37_sandstorm_only_counts_when_most_movement_was_in_it():
    """RULE: 21.37."""
    assert weather_column_shift("sandstorm") == 0
    assert weather_column_shift("sandstorm", sandstorm_majority=True) == 1
    assert weather_column_shift("rainstorm") == 0


def test_21_25_26_breakdown_track_only_rechecks_in_a_higher_column():
    """RULE: 21.26."""
    track = BreakdownTrack().accumulate(4)
    needed, track = track.check()
    assert needed and track.last_column == 4
    track = track.accumulate(5)
    needed, track = track.check()
    assert not needed and track.last_column == 4
    track = track.accumulate(3)
    needed, track = track.check()
    assert needed and track.last_column == 11


def test_21_35_losses_round_up_and_ignore_ten_percent_for_one_point():
    """RULE: 21.35."""
    assert losses_from_percent(25, 30) == 8
    assert losses_from_percent(10, 1) == 0
    assert losses_from_percent(20, 1) == 1


def test_21_36_breakdowns_are_distributed_evenly():
    """RULE: 21.36."""
    assert distribute_evenly(5, groups=3) == (2, 2, 1)
    assert distribute_evenly(0, groups=2) == (0, 0)


def test_21_34_breakdown_table_is_caller_supplied():
    """RULE: 21.34."""
    table = lambda roll, column: 10 if (roll, column) == (33, 31) else 0
    assert breakdown_percent(33, 31, table) == 10
    raises(BreakdownError, lambda: breakdown_percent(10, 31, table))


def test_21_41_half_the_breakdowns_stay_near_the_enemy():
    """RULE: 21.41."""
    assert forced_breakdown_share(near_enemy_battalion=True) == Fraction(1, 2)
    assert forced_breakdown_share(near_enemy_battalion=False) == 0


def test_21_52_54_capturing_broken_down_vehicles():
    """RULE: 21.52."""
    base = dict(adjacent_friendly_battalion=True, stacked_friendly=False,
                friendly_controlled_hex=False, passable_hexside=True)
    assert vehicle_capture_allowed(**base)
    assert not vehicle_capture_allowed(**{**base, "stacked_friendly": True})
    assert not vehicle_capture_allowed(**{**base,
                                          "friendly_controlled_hex": True})
    assert not vehicle_capture_allowed(**{**base, "passable_hexside": False})
    assert capture_tow_hexes() == 3


def test_21_62_66_towing_restrictions():
    """RULE: 21.63."""
    assert towing_cp_per_repair_phase() == 10
    assert towing_supply_cost() == (0, 0, 0)
    assert towing_allowed(in_enemy_controlled=False)
    assert not towing_allowed(in_enemy_controlled=True)
    assert towing_allowed(in_enemy_controlled=True, at_capture=True)
    assert not towing_allowed(in_enemy_controlled=False,
                              failed_field_repair=True)
    assert tow_direction_ok(towards_nearest_facility=True)
    assert not tow_direction_ok(towards_nearest_facility=False)


# ---------------------------------------------------------------------------
# 22 Repair
# ---------------------------------------------------------------------------


def test_22_12_repairs_only_in_the_repair_phase():
    """RULE: 22.12."""
    assert repair_phase_allowed("repair")
    assert not repair_phase_allowed("movement")


def test_22_13d_weather_stops_temporary_repairs():
    """RULE: 22.13."""
    assert not repair_weather_allowed(weather="sandstorm",
                                      major_facility=False)
    assert repair_weather_allowed(weather="sandstorm", major_facility=True)
    assert repair_weather_allowed(weather="normal", major_facility=False)


def test_22_21_field_repairs_need_a_friendly_unit_and_no_tow():
    """RULE: 22.21."""
    assert field_repair_allowed(destroyed=False, stacked_friendly=True,
                                towed_this_phase=False)
    assert not field_repair_allowed(destroyed=True, stacked_friendly=True,
                                    towed_this_phase=False)
    assert not field_repair_allowed(destroyed=False, stacked_friendly=False,
                                    towed_this_phase=False)
    assert not field_repair_allowed(destroyed=False, stacked_friendly=True,
                                    towed_this_phase=True)


def test_22_23_field_truck_repair():
    """RULE: 22.23."""
    assert field_truck_repair(1) == 2
    assert field_truck_repair(1, heavy=True) == 1
    assert field_truck_repair(2) == 1
    assert field_truck_repair(3) == 0
    assert field_truck_repair(2, heavy=True) == 0


def test_22_24_field_recce_repair():
    """RULE: 22.24."""
    assert field_recce_repair(1) == 1
    assert field_recce_repair(2) == 0


def test_22_25_field_tank_repair_rounds_up():
    """RULE: 22.25."""
    assert field_tank_repair(33, 20) == 7
    assert field_tank_repair(10, 1) == 0
    assert field_tank_fuel_cost(7) == 7


def test_22_35_facility_and_destroyed_tank_supply_costs():
    """RULE: 22.35."""
    assert facility_supply_cost(3) == (3, 3)
    assert destroyed_tank_supply_cost(3) == (6, 6)


def test_22_34_bombing_modifies_the_facility_repair_die():
    """RULE: 22.34."""
    assert facility_repair_modifier(reduced_levels=0) == 0
    assert facility_repair_modifier(reduced_levels=1) == 1
    assert facility_repair_modifier(reduced_levels=2) == 2
    assert facility_repair_modifier(reduced_levels=3) == 2


def test_22_13_37_facility_repair_in_an_enemy_zoc():
    """RULE: 22.37."""
    assert not facility_repair_allowed(facility="temporary", in_enemy_zoc=True,
                                       in_major_city=False, neutralized=False)
    assert facility_repair_allowed(facility="temporary", in_enemy_zoc=True,
                                   in_major_city=True, neutralized=False)
    assert facility_repair_allowed(facility="major", in_enemy_zoc=True,
                                   in_major_city=False, neutralized=False)
    assert not facility_repair_allowed(facility="major", in_enemy_zoc=False,
                                       in_major_city=False, neutralized=True)


def test_22_43_destroyed_tank_table_outcomes():
    """RULE: 22.43."""
    assert destroyed_tank_repair(1, lambda roll: "repaired") == "repaired"
    assert destroyed_tank_repair(6, lambda roll: "retry") == "retry"
    raises(BreakdownError,
           lambda: destroyed_tank_repair(1, lambda roll: "exploded"))


def test_22_5_repaired_vehicles_need_no_training():
    """RULE: 22.5."""
    assert not repaired_vehicle_training_required()


def test_22_62_65_tank_delivery_squadron_characteristics():
    """RULE: 22.62."""
    assert tds_field_repair_modifier() == -1
    assert tds_destroyed_tank_success() == 1
    assert tds_characteristics() == {"cpa": 25, "reserves": 3, "tow_cp": 20,
                                     "tow_capacity": 3}
    assert tds_elimination_return_turns() == 8


# ---------------------------------------------------------------------------
# 23 Engineers
# ---------------------------------------------------------------------------


def test_23_21_engineer_minefield_entry_costs():
    """RULE: 23.21."""
    assert minefield_entry_cp(motorized=True, engineer_present=True) == 6
    assert minefield_entry_cp(motorized=False, engineer_present=True) == 3
    assert minefield_entry_cp(motorized=True, engineer_present=False) is None


def test_23_22_minefield_removal_needs_a_full_stage_without_cp():
    """RULE: 23.22."""
    assert minefield_removal_allowed(full_stage=True, cp_spent=0)
    assert not minefield_removal_allowed(full_stage=True, cp_spent=1)
    assert not minefield_removal_allowed(full_stage=False, cp_spent=0)


def test_23_24_engineer_assault_bonus_excludes_major_cities():
    """RULE: 23.24."""
    assert engineer_assault_column_bonus(unpinned_engineer_battalion=True,
                                         fortified=True,
                                         major_city=False) == 1
    assert engineer_assault_column_bonus(unpinned_engineer_battalion=True,
                                         fortified=True,
                                         major_city=True) == 0
    assert engineer_assault_column_bonus(unpinned_engineer_battalion=False,
                                         fortified=True,
                                         major_city=False) == 0


def test_23_26_engineers_cannot_build_bridges():
    """RULE: 23.26."""
    assert not engineer_can_build_bridges()


# ---------------------------------------------------------------------------
# 24 Construction
# ---------------------------------------------------------------------------


def test_24_11_construction_includes_the_starting_stage():
    """RULE: 24.11."""
    assert construction_completion_stage(start_stage=1, stages=1) == 2
    assert construction_completion_stage(start_stage=3, stages=3) == 6


def test_24_12_22_23_a_stage_counts_only_without_cp_storm_or_pin():
    """RULE: 24.12."""
    assert construction_stage_counts(cp_spent=0, storm=False, pinned=False)
    assert not construction_stage_counts(cp_spent=1, storm=False, pinned=False)
    assert not construction_stage_counts(cp_spent=0, storm=True, pinned=False)
    assert not construction_stage_counts(cp_spent=0, storm=False, pinned=True)


def test_24_21_hot_weather_needs_ten_water():
    """RULE: 24.21."""
    assert hot_water_cost("hot") == 10
    assert hot_water_cost("normal") == 0


def test_24_33_34_minefield_construction_costs():
    """RULE: 24.33."""
    assert minefield_construction_cost(dummy=False) == (15, 15)
    assert minefield_construction_cost(dummy=True) == (3, 0)


def test_24_35_36_minefield_locations():
    """RULE: 24.35."""
    base = dict(dummy=False, terrain="clear", enemy_controlled=False,
                major_city=False, existing_minefield=False)
    assert minefield_construction(**base) == (True, "")
    assert minefield_construction(**{**base, "terrain": "mountain"}) == (
        False, "24.35")
    assert minefield_construction(**{**base, "major_city": True}) == (
        False, "24.35")
    assert minefield_construction(**{**base, "enemy_controlled": True}) == (
        False, "24.36")
    assert minefield_construction(**{**base,
                                     "existing_minefield": True}) == (
        False, "24.35")


def test_24_42_44_fortification_requirements():
    """RULE: 24.42."""
    base = dict(engineer_present=True, infantry_toe=3, terrain="clear",
                enemy_zoc=False, stores=30)
    assert fortification_allowed(**base) == (True, "")
    assert fortification_allowed(**{**base, "engineer_present": False}) == (
        False, "24.42")
    assert fortification_allowed(**{**base, "infantry_toe": 2}) == (
        False, "24.42")
    assert fortification_allowed(**{**base, "terrain": "desert"}) == (
        False, "24.44")
    assert fortification_allowed(**{**base, "enemy_zoc": True}) == (
        False, "24.44")
    assert fortification_allowed(**{**base, "stores": 29}) == (False, "24.43")
    assert fortification_rebuild_in_zoc_allowed()


def test_24_53_54_road_building():
    """RULE: 24.53."""
    assert road_build_capacity(engineer_battalion=True) == 3
    assert road_build_capacity(engineer_company=True) == 1
    assert road_build_capacity(infantry_toe=3) == 1
    assert road_build_capacity(infantry_toe=2) == 0
    assert road_build_cost(3) == 6


def test_24_62_64_railroad_building():
    """RULE: 24.62."""
    assert railroad_build_stages(nzrrc_companies=1) == 2
    assert railroad_build_stages(nzrrc_companies=2) == 1
    assert railroad_build_stages(nzrrc_companies=0) is None
    assert railroad_rebuild_limit() == 3
    assert railroad_rebuild_stores(3) == 3


def test_24_72_74_air_facility_construction():
    """RULE: 24.72."""
    assert air_facility_construction(kind="airfield",
                                     engineer_battalion=True) == (True, "", 3)
    assert air_facility_construction(kind="airfield",
                                     engineer_battalion=False) == (
        False, "24.72", 0)
    assert air_facility_construction(kind="landing_strip",
                                     engineer_battalion=False,
                                     engineer_company=True) == (True, "", 1)
    assert air_facility_construction(kind="flying_boat_basin",
                                     engineer_battalion=True,
                                     coastal=False) == (False, "24.73", 0)
    assert air_facility_construction(kind="alighting_area",
                                     engineer_battalion=False,
                                     squadron_ground_support=True,
                                     coastal=True) == (True, "", 1)


def test_24_83_85_temporary_repair_facilities():
    """RULE: 24.83."""
    base = dict(existing=0, engineer_present=True, stores=250, fuel=150,
                enemy_controlled=False)
    assert temporary_repair_facility_allowed(**base) == (True, "")
    assert temporary_repair_facility_allowed(**{**base, "existing": 2}) == (
        False, "24.85")
    assert temporary_repair_facility_allowed(**{**base,
                                                "enemy_controlled": True}) == (
        False, "24.87")
    assert temporary_repair_facility_allowed(**{**base, "stores": 249}) == (
        False, "24.83")
    assert temporary_repair_dismantle_returns() == (120, 25)


def test_24_9_supply_dump_costs():
    """RULE: 24.9."""
    assert supply_dump_cost(dummy=False) == (3, 20)
    assert supply_dump_cost(dummy=True) == (3, 0)


def test_24_13_supplies_must_be_present():
    """RULE: 24.13."""
    assert construction_supplies_ok(stores=30, ammo=0, fuel=0, water=0,
                                    required_stores=30)
    assert not construction_supplies_ok(stores=29, ammo=0, fuel=0, water=0,
                                        required_stores=30)


# ---------------------------------------------------------------------------
# 25 Fortifications
# ---------------------------------------------------------------------------


def test_25_12_13_fortification_levels():
    """RULE: 25.12."""
    assert fortification_level(major_city=True) == 2
    assert fortification_level(major_city=True, capital=True) == 3
    assert fortification_level(major_city=False, constructed=True) == 1
    assert fortification_level(major_city=False) == 0
    assert constructed_fortification_max(capital=False) == 2
    assert constructed_fortification_max(capital=True) == 3


def test_25_21_23_24_fortification_effects():
    """RULE: 25.21."""
    assert not fortification_affects_movement_or_breakdown()
    assert not air_bombardment_affects_level3_city()
    assert pinned_ignored_in_level3_city()


# ---------------------------------------------------------------------------
# 26 Minefields
# ---------------------------------------------------------------------------


def test_26_24_engineer_minefield_costs():
    """RULE: 26.24."""
    assert engineer_minefield_additional_cp(engineer_battalion_stacked=True) == 4
    assert engineer_minefield_additional_cp(
        engineer_battalion_stacked=False) is None
    assert friendly_minefield_engineer_cost() == 0


def test_26_14_dummy_minefields_lift_after_the_movement_phase():
    """RULE: 26.14."""
    assert dummy_minefield_removal_phase() == "movement"


def test_26_25_vehicle_losses_on_five_or_six():
    """RULE: 26.25."""
    assert minefield_vehicle_loss(5) == 1
    assert minefield_vehicle_loss(6) == 1
    assert minefield_vehicle_loss(4) == 0


def test_26_26_defender_shifts_one_column_in_a_minefield():
    """RULE: 26.26."""
    assert minefield_defender_column_shift(attacker_in_enemy_minefield=True,
                                           defender_in_enemy_minefield=False) == 1
    assert minefield_defender_column_shift(attacker_in_enemy_minefield=False,
                                           defender_in_enemy_minefield=True) == 1
    assert minefield_defender_column_shift(attacker_in_enemy_minefield=False,
                                           defender_in_enemy_minefield=False) == 0
