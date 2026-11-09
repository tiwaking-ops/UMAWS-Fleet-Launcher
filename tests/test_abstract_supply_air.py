"""Citing tests for the LAND_ABSTRACT §32 supply and air rules."""

from __future__ import annotations

from fractions import Fraction

import pytest

from cna.rules import sec32_abstract as sec32


def test_32_0_scope_is_land_only() -> None:
    """RULE: 32.0 - abstract supply applies only without Air/Logistics."""
    assert sec32.abstract_rules_apply() is True
    assert sec32.abstract_rules_apply(air_game=True) is False
    assert sec32.abstract_rules_apply(logistics_game=True) is False


def test_32_11_standard_supply_categories_ignore() -> None:
    """RULE: 32.11 - Ammo, Fuel, Stores and Water usage is ignored."""
    assert sec32.ignored_supply_categories() == (
        "ammo", "fuel", "stores", "water",
    )
    assert sec32.supply_attrition_suppressed() is True


def test_32_12_supply_unit_counter() -> None:
    """RULE: 32.12 - a Supply Unit is represented by a dump counter."""
    unit = sec32.SupplyUnit("axis")
    assert (unit.ammo, unit.fuel) == (40, 60)
    assert unit.empty is False


def test_32_13_capture_uses_remaining_supplies() -> None:
    """RULE: 32.13 - an enemy combat unit captures the remaining supplies."""
    unit = sec32.SupplyUnit("commonwealth", ammo=17, fuel=23)
    assert sec32.supply_unit_captured(enemy_combat_enters=True) is True
    assert sec32.captured_supply_points(unit) == (17, 23)
    assert unit.captured() == (17, 23)


def test_32_14_stacking_and_hex_limits() -> None:
    """RULE: 32.14 - zero stacking; 5 in a Major City; 3 in other off-map hexes."""
    assert sec32.supply_unit_stacking_value() == 0
    assert sec32.supply_unit_hex_limit(major_city=True) == 5
    assert sec32.supply_unit_hex_limit(off_map=True) == 3
    assert sec32.supply_unit_hex_limit(off_map=True, major_city=True) == 5
    assert sec32.supply_unit_hex_limit(box=True) is None


def test_32_15_spending_rearranging_and_removal() -> None:
    """RULE: 32.15 - 40/60 caps; spend to zero; rearrange in Organization."""
    unit = sec32.SupplyUnit("axis", ammo=40, fuel=60)
    spent = unit.spend(ammo=10, fuel=15)
    assert (spent.ammo, spent.fuel) == (30, 45)
    assert spent.empty is False
    assert unit.spend(ammo=40, fuel=60).empty is True

    first = sec32.SupplyUnit("axis", ammo=10, fuel=20)
    second = sec32.SupplyUnit("axis", ammo=0, fuel=0)
    arranged = sec32.rearrange_supplies((first, second), phase="organization")
    assert [(u.ammo, u.fuel) for u in arranged] == [(10, 20), (0, 0)]

    with pytest.raises(sec32.AbstractSupplyError):
        sec32.rearrange_supplies((first,), phase="movement")
    with pytest.raises(sec32.AbstractSupplyError):
        unit.spend(ammo=41)


def test_32_16_supply_draw_range_and_trace() -> None:
    """RULE: 32.16 - draw within half CPA; infantry trace as infantry."""
    assert sec32.supply_draw_range(10) == 5
    assert sec32.supply_draw_range(45) == 23
    assert sec32.supply_trace_kind(nonmotorized_infantry=True) == "infantry"
    assert sec32.supply_trace_kind(nonmotorized_infantry=False) == "medium_truck"

    assert sec32.supply_line_allowed(unit_cpa=10, trace_cost=5) is True
    assert sec32.supply_line_allowed(unit_cpa=10, trace_cost=6) is False
    assert sec32.supply_line_allowed(
        unit_cpa=10, trace_cost=1, impassable=True) is False
    assert sec32.supply_line_allowed(
        unit_cpa=10, trace_cost=1, enemy_zoc=True) is False
    assert sec32.supply_line_allowed(
        unit_cpa=10, trace_cost=1, enemy_zoc=True,
        friendly_unit_in_zoc=True) is True


def test_32_17_destruction_attempts() -> None:
    """RULE: 32.17 - half CPA, one attempt, 1-3 destroys on one die."""
    assert sec32.supply_destruction_cp((10, 11)) == 11
    assert sec32.supply_destruction_result(roll=3, stacking_points=2) is True
    assert sec32.supply_destruction_result(roll=3, stacking_points=1) is False
    assert sec32.supply_destruction_result(roll=2, stacking_points=1) is True
    assert sec32.supply_destruction_attempt_allowed(
        attempts_this_subsegment=0, prior_to_movement=True) is True
    assert sec32.supply_destruction_attempt_allowed(
        attempts_this_subsegment=1, prior_to_movement=True) is False
    assert sec32.supply_destruction_attempt_allowed(
        attempts_this_subsegment=0, prior_to_movement=False) is False


def test_32_18_dummy_allowance_and_discovery() -> None:
    """RULE: 32.18 - one dummy per three real units; removed when discovered."""
    assert sec32.dummy_supply_allowance(8) == 2
    assert sec32.dummy_supply_allowance(9) == 3
    assert sec32.dummy_supply_removed(discovered=True) is True
    assert sec32.dummy_supply_removed(discovered=False) is False
    dummy = sec32.SupplyUnit("axis", ammo=0, fuel=0, dummy=True)
    with pytest.raises(sec32.AbstractSupplyError):
        sec32.SupplyUnit("axis", ammo=1, fuel=0, dummy=True)
    with pytest.raises(sec32.AbstractSupplyError):
        dummy.spend(fuel=1)


def test_32_21_22_ammo_costs_and_timing() -> None:
    """RULE: 32.21-32.22 - Assault 1, Barrage 2 per Bn-Eq; phasing doubles."""
    assert sec32.ammo_cost(
        battalion_equivalents=3, combat="assault", phasing=False) == 3
    assert sec32.ammo_cost(
        battalion_equivalents=3, combat="barrage", phasing=False) == 6
    assert sec32.ammo_cost(
        battalion_equivalents=3, combat="assault", phasing=True) == 6
    assert sec32.ammo_paid_at_combat() is True


def test_32_23_24_25_fuel_costs() -> None:
    """RULE: 32.23-32.25 - stage fuel, tank/gun/recce costs, no patrol cost."""
    assert sec32.fuel_for_stage(first_move_fuel=2) == 2
    assert sec32.fuel_for_stage(
        first_move_fuel=2, exceeds_cpa=True) == 4
    assert sec32.movement_fuel_cost(
        tank_battalions=1, tank_companies=1, gun_battalions=1,
        recce_battalions=1, motorization_transports=1) == 6
    assert sec32.movement_fuel_cost(
        tank_battalions=1, patrolling=True) == 0
    assert sec32.patrol_supply_cost() == (0, 0)


def test_32_31_supply_movement_modes_and_arrival() -> None:
    """RULE: 32.31 - land/rail/sea/air; only land/rail on arrival."""
    assert sec32.supply_move_modes() == ("land", "rail", "sea", "air")
    assert sec32.supply_arrival_stage_move_allowed(
        mode="land", arriving_this_stage=True) is True
    assert sec32.supply_arrival_stage_move_allowed(
        mode="rail", arriving_this_stage=True) is True
    assert sec32.supply_arrival_stage_move_allowed(
        mode="sea", arriving_this_stage=True) is False
    assert sec32.supply_arrival_stage_move_allowed(
        mode="air", arriving_this_stage=False) is True


def test_32_32_33_motorization_requirements_and_phases() -> None:
    """RULE: 32.32-32.33 - 30/6 points; one movement phase and stacking."""
    assert sec32.motorization_required() == 30
    assert sec32.motorization_required(dummy=True) == 6
    assert sec32.supply_motorization_ready(assigned_points=30) is True
    assert sec32.supply_motorization_ready(assigned_points=29) is False
    assert sec32.supply_motorized_move_allowed(
        phase="movement", already_moved=False,
        begins_and_remains_stacked=True) is True
    assert sec32.supply_motorized_move_allowed(
        phase="movement", already_moved=False,
        begins_and_remains_stacked=False) is False
    assert sec32.supply_motorized_move_allowed(
        phase="truck_convoy", already_moved=False,
        begins_and_remains_stacked=False) is True
    assert sec32.supply_motorized_move_allowed(
        phase="movement", already_moved=True,
        begins_and_remains_stacked=True) is False
    assert sec32.supply_motorized_move_allowed(
        phase="movement", already_moved=False,
        begins_and_remains_stacked=False, phasing=False) is True


def test_32_34_commonwealth_rail_limit() -> None:
    """RULE: 32.34 - two Supply Units by rail, one direction per OpStage."""
    assert sec32.commonwealth_rail_supply_allowed(
        phase="rail", count=2, direction_used=False) is True
    assert sec32.commonwealth_rail_supply_allowed(
        phase="rail", count=3, direction_used=False) is False
    assert sec32.commonwealth_rail_supply_allowed(
        phase="rail", count=1, direction_used=True) is False
    assert sec32.commonwealth_rail_supply_allowed(
        phase="movement", count=1, direction_used=False) is False


def test_32_35_axis_coastal_tonnage() -> None:
    """RULE: 32.35 - 2,000 tons per Supply Unit of Axis coastal shipping."""
    assert sec32.axis_coastal_shipping_tons(1) == 2000
    assert sec32.axis_coastal_shipping_tons(2) == 4000
    assert sec32.axis_coastal_shipping_allowed(
        supply_units=2, tons_available=4000) is True
    assert sec32.axis_coastal_shipping_allowed(
        supply_units=2, tons_available=3999) is False


def test_32_36_commonwealth_sea_supply() -> None:
    """RULE: 32.36 - three ports, 50% efficiency, one per OpStage."""
    base = dict(
        phase="naval_convoy_arrival", origin="alexandria",
        destination="tobruk", port_efficiency=Fraction(1, 2),
        used_this_stage=False,
    )
    assert sec32.commonwealth_sea_supply_allowed(**base) is True
    assert sec32.commonwealth_sea_supply_allowed(
        **{**base, "port_efficiency": Fraction(49, 100)}) is False
    assert sec32.commonwealth_sea_supply_allowed(
        **{**base, "destination": "cairo"}) is False
    assert sec32.commonwealth_sea_supply_allowed(
        **{**base, "used_this_stage": True}) is False
    assert sec32.commonwealth_sea_supply_allowed(
        **{**base, "combat_transport_origin": True}) is False


def test_32_37_air_supply_transport() -> None:
    """RULE: 32.37 - one air supply per turn, 12 Fuel, all location limits."""
    base = dict(
        phase="organization", origin_type="major_city",
        destination_type="tripoli_box", fuel_available=12,
        enemy_combat_within_five=False, direction_ok=True,
        destination_hq_ok=True, used_this_turn=False,
    )
    assert sec32.air_supply_transport_allowed(**base) is True
    assert sec32.air_supply_transport_allowed(
        **{**base, "fuel_available": 11}) is False
    assert sec32.air_supply_transport_allowed(
        **{**base, "enemy_combat_within_five": True}) is False
    assert sec32.air_supply_transport_allowed(
        **{**base, "destination_type": "desert"}) is False
    assert sec32.air_supply_transport_allowed(
        **{**base, "used_this_turn": True}) is False
    assert sec32.air_supply_fuel_cost() == 12
    assert sec32.air_transported_supply_movement_allowed(
        moved_by_air_this_opstage=True) is False


def test_32_41_45_availability_tables_and_planning() -> None:
    """RULE: 32.41-32.45 - scenario start, planning lead, and R-04 tables."""
    assert sec32.initial_supply_units(4) == 4
    assert sec32.planning_lead_turns("axis") == 2
    assert sec32.planning_lead_turns("commonwealth") == 4
    assert sec32.arrival_turn(planning_turn=1, side="axis") == 3
    assert sec32.arrival_turn(planning_turn=1, side="commonwealth") == 5
    assert sec32.supply_arrival_turn_allowed(
        game_turn=1, scenario_start_turn=1, planning_roll_ok=True) is False
    assert sec32.supply_arrival_turn_allowed(
        game_turn=2, scenario_start_turn=1, planning_roll_ok=True) is True

    assert sec32.axis_supply_arrival(
        letter="A", roll=3, table=lambda letter, roll: roll + 1) == 4
    assert sec32.commonwealth_supply_arrival(
        period="1941", roll=2, table=lambda period, roll: roll * 2) == 4


def test_32_42_commonwealth_placement() -> None:
    """RULE: 32.42 - Cairo, with one per three going to Alexandria above three."""
    assert sec32.commonwealth_supply_placement(3) == (3, 0)
    assert sec32.commonwealth_supply_placement(4) == (3, 1)
    assert sec32.commonwealth_supply_placement(6) == (4, 2)
    assert sec32.commonwealth_supply_placement(9) == (6, 3)


def test_32_51_56_motorization_general_rules() -> None:
    """RULE: 32.51-32.56 - truck equivalence, transport, priority and losses."""
    assert sec32.motorization_points_are_truck_points() is True
    assert sec32.motorization_replacement_limit(
        medium_truck_replacements=7) == 7
    assert sec32.motorization_can_transport(unit_type="infantry", cpa=8) is True
    assert sec32.motorization_can_transport(unit_type="gun", cpa=0) is True
    assert sec32.motorization_can_transport(unit_type="tank", cpa=12) is False
    assert sec32.motorization_priority_allowed(
        historical_motorized=False, historical_unassigned=1) is False
    assert sec32.motorization_priority_allowed(
        historical_motorized=True, historical_unassigned=1) is True
    assert sec32.motorization_breakdown_exempt() is True
    assert sec32.motorization_loss(
        assigned_unit_eliminated=True, assigned_unit_captured=False) == "lost"
    assert sec32.motorization_loss(
        assigned_unit_eliminated=False, assigned_unit_captured=True) == "captured"
    assert sec32.motorization_loss(
        assigned_unit_eliminated=False, assigned_unit_captured=False) == "retained"


def test_32_57_59_motorization_loss_and_supply_transport() -> None:
    """RULE: 32.57-32.59 - chart losses and Supply Unit transport attributes."""
    assert sec32.abstract_motorization_loss(
        percentage=50, total_points=10) == Fraction(5, 1)
    assert sec32.motorization_supply_cpa() == 15
    assert sec32.motorization_supply_excess_action() == "return_to_last_legal_hex"
    assert sec32.motorization_supply_combat_cp() == 0
    assert sec32.motorization_supply_reaction_allowed(adjacent_cpa=34) is True
    assert sec32.motorization_supply_reaction_allowed(adjacent_cpa=35) is False


def test_32_61_62_convoy_composition_and_lane_load() -> None:
    """RULE: 32.61-32.62 - convoy items and 3 supply / 20 point lane limit."""
    assert sec32.axis_convoy_items() == (
        "supply_units", "motorization_points", "replacement_points",
    )
    assert sec32.axis_convoy_lane_load_allowed(
        supply_units=3, motorization_points=20) is True
    assert sec32.axis_convoy_lane_load_allowed(
        supply_units=4, motorization_points=20) is False
    assert sec32.axis_convoy_lane_load_allowed(
        supply_units=3, motorization_points=21) is False


def test_32_63_65_convoy_attack_and_losses() -> None:
    """RULE: 32.63-32.65 - any weather, percentage table, special 10% rule."""
    assert sec32.axis_convoy_attack_allowed(
        phase="naval_convoy", lane_announced=True, weather="rainstorm") is True
    assert sec32.axis_convoy_attack_allowed(
        phase="movement", lane_announced=True) is False
    assert sec32.axis_convoy_attack_allowed(
        phase="naval_convoy", lane_announced=False) is False
    assert sec32.convoy_bombing_percent(
        roll=33, bomb_points=10, table=lambda roll, points: points) == 10
    assert sec32.convoy_losses(
        percent=10, supply_units=5, motorization_points=5,
        replacement_points=5) == (0, 0, 1)
    assert sec32.convoy_losses(
        percent=20, supply_units=5, motorization_points=5,
        replacement_points=5) == (1, 1, 1)
    assert sec32.convoy_losses(
        percent=30, supply_units=10, motorization_points=10,
        replacement_points=10) == (3, 3, 3)


def test_32_71_75_fleet_bombardment() -> None:
    """RULE: 32.71-32.75 - plotted, one per stage, weather and table limits."""
    assert sec32.fleet_bombardment_attacks(roll=3) == 3
    assert sec32.fleet_bombardment_attacks(roll=3, campaign=True) == 5
    assert sec32.fleet_bombardment_plot_phase_allowed(
        phase="commonwealth_fleet_assignment") is True
    assert sec32.fleet_bombardment_weather_allowed(weather="normal") is True
    assert sec32.fleet_bombardment_weather_allowed(weather="sandstorm") is False
    assert sec32.fleet_bombardment_phase_allowed(
        phase="tactical_naval", attacks_this_stage=0, plotted=True,
        weather="normal") is True
    assert sec32.fleet_bombardment_phase_allowed(
        phase="tactical_naval", attacks_this_stage=0, plotted=True,
        weather="rainstorm") is False
    assert sec32.fleet_bombardment_phase_allowed(
        phase="tactical_naval", attacks_this_stage=1, plotted=True,
        weather="normal") is False
    assert sec32.fleet_bombardment_column(die=1) == 1
    assert sec32.fleet_bombardment_column(die=1, campaign=True) == 3
    assert sec32.fleet_bombardment_damage(
        roll=33, column=10, table=lambda roll, column: column) == 10


def test_32_81_84_anti_air_modifications() -> None:
    """RULE: 32.81-32.84 - side/nationality AA removals and replacements."""
    assert sec32.commonwealth_anti_air_removed(kind="unit") is True
    assert sec32.commonwealth_anti_air_removed(kind="replacement") is True
    assert sec32.captured_axis_anti_air_removed() is True

    assert sec32.german_anti_air_removed(
        id_code="z", heavy=True, kind="unit") is True
    assert sec32.german_anti_air_removed(
        id_code="other", heavy=False, kind="toe") is True
    assert sec32.german_anti_air_removed(
        id_code="other", heavy=True, kind="toe") is False

    assert sec32.italian_anti_air_removed(
        id_code="ss", heavy=True, kind="unit") is True
    assert sec32.italian_anti_air_removed(
        id_code="pp", heavy=False, kind="toe") is True
    assert sec32.italian_anti_air_removed(
        id_code="kk", heavy=True, kind="toe") is True
    assert sec32.italian_anti_air_removed(
        id_code="kk", heavy=False, kind="toe") is False
    assert sec32.italian_anti_air_removed(
        id_code="other", heavy=True, kind="replacement") is True
    assert sec32.italian_anti_air_removed(
        id_code="other", heavy=False, kind="replacement") is False
    assert sec32.italian_light_aa_replacement_limit() == 1
    assert sec32.non_anti_air_rating_unaffected() is True


def test_32_9_road_and_track_stacking() -> None:
    """RULE: 32.9 - Road/Track stacking restrictions are ignored."""
    assert sec32.road_track_stacking_ignored() is True
