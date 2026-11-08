"""Patrol, morale and reserve tests, one named case per test.

RULE: 16.11-16.55, 17.21-17.56, 18.11-18.26

The Patrol Survival, Reconnaissance, Objective Loss and Morale Modification
tables are R-04 and are absent.  The tables here are synthetic and labelled;
no historical rating is invented.
"""

import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cna.rules.sec16_morale import (
    DUMMY_CPA,
    MORALE_MAX,
    MORALE_MIN,
    PATROL_POINTS_PER_TARGET,
    RESERVE_I,
    RESERVE_II,
    MoraleError,
    MoraleResult,
    ObjectiveLoss,
    PatrolRoll,
    PatrolUnit,
    adjusted_morale,
    cohesion_row,
    destroyed_points,
    destruction_percent,
    dummy_eliminated,
    dummy_placement_allowed,
    largest_unit_cohesion,
    may_designate_reserve,
    may_move_after_release,
    may_supply_patrol_points,
    must_choose_first_release,
    mutual_surrender,
    objective_losses,
    patrol_cost,
    patrol_path_allowed,
    patrol_points_from_hex,
    patrol_range_allowed,
    patrol_stage_allowed,
    patrol_survival,
    patrol_weather_allowed,
    reconnaissance,
    reserve_cp_cap,
    reserve_disorganization,
    reserve_move_allowed,
    reserve_movement_limit,
    reserve_release_effects,
    reveal_information,
    revealable_units,
    toe_disclosure_valid,
    training_continues,
    training_instructor_ok,
    training_progress,
    voluntary_surrender_allowed,
)


def pu(unit_id="u", **kwargs):
    kwargs.setdefault("side", "Axis")
    kwargs.setdefault("hex_id", "A")
    return PatrolUnit(unit_id=unit_id, **kwargs)


def raises(error_type, call):
    try:
        call()
    except error_type:
        return
    raise AssertionError(f"expected {error_type.__name__}")


def survival_table(lost=1, captured=0):
    def table(roll, points):
        return PatrolRoll(lost=lost, captured=captured)
    return table


def failing_table(roll, points):
    raise AssertionError("the survival table must not be consulted")


def morale_table(value):
    return lambda row, roll: value


# ---------------------------------------------------------------------------
# 16 Patrols and reconnaissance
# ---------------------------------------------------------------------------


def test_16_11_only_recce_light_tanks_and_motorized_infantry_patrol():
    """RULE: 16.11."""
    for unit_type in ("recce", "light_tank", "motorized_infantry"):
        assert may_supply_patrol_points(pu(unit_type=unit_type,
                                           toe_strength=1)) == (True, "")
    assert may_supply_patrol_points(pu(unit_type="infantry",
                                       toe_strength=1)) == (False, "16.11")


def test_16_12_toe_points_are_detached_as_patrol_points():
    """RULE: 16.12."""
    assert may_supply_patrol_points(pu(unit_type="recce",
                                       toe_strength=2))[0]
    assert may_supply_patrol_points(pu(unit_type="recce",
                                       toe_strength=0)) == (False, "16.12")


def test_16_13_two_toe_points_per_hex_at_most():
    """RULE: 16.13."""
    units = [pu("a", unit_type="recce", toe_strength=3),
             pu("b", unit_type="recce", toe_strength=3)]
    assert patrol_points_from_hex(units) == 2


def test_16_14_three_patrol_points_per_target_at_most():
    """RULE: 16.14."""
    assert PATROL_POINTS_PER_TARGET == 3


def test_16_15_collapsed_units_may_not_patrol():
    """RULE: 16.15."""
    assert may_supply_patrol_points(pu(unit_type="recce", toe_strength=1,
                                       cohesion=-8)) == (False, "16.15")
    assert may_supply_patrol_points(pu(unit_type="recce", toe_strength=1,
                                       cohesion=-7))[0]


def test_16_16_patrol_supply_cost():
    """RULE: 16.16."""
    assert patrol_cost(3) == (3, 6)
    assert patrol_cost(0) == (0, 0)


def test_16_17_no_patrols_in_a_storm():
    """RULE: 16.17."""
    assert not patrol_weather_allowed("rainstorm", "clear")
    assert not patrol_weather_allowed("clear", "sandstorm")
    assert patrol_weather_allowed("clear", "clear")


def test_16_21_patrols_after_a_combat_free_stage_only():
    """RULE: 16.21."""
    assert patrol_stage_allowed(anti_armor_or_close_assault=False,
                                target_barraged=False) == (True, "")
    assert patrol_stage_allowed(anti_armor_or_close_assault=True,
                                target_barraged=False) == (False, "16.21")
    assert patrol_stage_allowed(anti_armor_or_close_assault=False,
                                target_barraged=True) == (False, "16.21")


def test_16_22_five_hex_range_and_no_enemy_hexes_on_the_path():
    """RULE: 16.22."""
    assert patrol_range_allowed(5)
    assert not patrol_range_allowed(6)
    assert patrol_path_allowed(["B", "C"], impassable={"D"}, enemy_units={"B"},
                               enemy_zoc=set(), target_hex="C") is False
    assert patrol_path_allowed(["B", "C"], impassable=set(), enemy_units={"C"},
                               enemy_zoc=set(), target_hex="C") is True
    assert patrol_path_allowed(["B"], impassable=set(), enemy_units=set(),
                               enemy_zoc={"B"}, target_hex="C") is False


def test_16_32_no_combat_units_means_no_patrol_losses():
    """RULE: 16.32."""
    result = patrol_survival(points=2, roll=1, recce_only=False,
                             combat_units_present=False,
                             table=failing_table)
    assert result.lost == 0 and result.remaining == 2


def test_16_33_recce_patrols_subtract_one_from_the_die():
    """RULE: 16.33."""
    seen = {}

    def table(roll, points):
        seen["roll"] = roll
        return PatrolRoll(lost=1, captured=1)

    result = patrol_survival(points=3, roll=4, recce_only=True,
                             combat_units_present=True, table=table)
    assert seen["roll"] == 3
    assert result.lost == 1 and result.captured == 1
    assert result.remaining == 1


def test_16_33_a_wiped_out_patrol_gets_no_information():
    """RULE: 16.33."""
    result = patrol_survival(points=1, roll=1, recce_only=False,
                             combat_units_present=True,
                             table=survival_table(lost=1))
    assert result.remaining == 0
    assert reconnaissance(result.remaining, 4, lambda p, r: 9) == 0


def test_16_34_captured_becomes_eliminated_when_the_patrol_is_wiped_out():
    """RULE: 16.34."""
    table = lambda roll: ObjectiveLoss(eliminated=1, captured=2)
    assert objective_losses(3, patrol_eliminated=False,
                            table=table) == ObjectiveLoss(eliminated=1,
                                                          captured=2)
    assert objective_losses(3, patrol_eliminated=True,
                            table=table) == ObjectiveLoss(eliminated=3,
                                                          captured=0)


def test_16_41_dummy_tanks_have_no_cpa():
    """RULE: 16.41."""
    assert DUMMY_CPA == 0


def test_16_42_43_dummy_placement_limits():
    """RULE: 16.42."""
    assert dummy_placement_allowed(existing_dummies=0, stores=10,
                                   italian=False) == (True, "")
    assert dummy_placement_allowed(existing_dummies=0, stores=9,
                                   italian=False) == (False, "16.42")
    assert dummy_placement_allowed(existing_dummies=3, stores=20,
                                   italian=False) == (False, "16.43")
    assert dummy_placement_allowed(existing_dummies=0, stores=20,
                                   italian=True) == (False, "16.43")


def test_16_46_dummies_die_in_assault_and_armourless_anti_armor_fire():
    """RULE: 16.46."""
    assert dummy_eliminated(close_assault=True,
                            anti_armor_without_armor=False)
    assert dummy_eliminated(close_assault=False,
                            anti_armor_without_armor=True)
    assert not dummy_eliminated(close_assault=False,
                                anti_armor_without_armor=False)


def test_16_51_disclosed_toe_is_within_two():
    """RULE: 16.51."""
    assert toe_disclosure_valid(5, 3)
    assert toe_disclosure_valid(5, 7)
    assert not toe_disclosure_valid(5, 8)


def test_16_53_54_55_reveal_order_and_exclusions():
    """RULE: 16.53."""
    company = pu("company", unit_type="infantry", size="company",
                 toe_strength=1)
    battalion = pu("battalion", unit_type="infantry", size="battalion",
                   toe_strength=4)
    hq = pu("hq", unit_type="hq", size="battalion", kind="hq", toe_strength=2)
    engineer = pu("eng", unit_type="engineer", size="battalion", kind="engineer",
                  toe_strength=2)
    ordered = revealable_units([company, hq, engineer, battalion])
    assert [unit.unit_id for unit in ordered] == ["battalion", "eng", "company"]
    revealed = reveal_information([company, battalion, engineer], count=1,
                                 excluded={"battalion"})
    assert [unit.designation for unit in revealed] == ["eng"]


def test_16_54_hqs_are_revealed_only_without_combat_units():
    """RULE: 16.54."""
    hq = pu("hq", unit_type="hq", kind="hq", toe_strength=2)
    assert [unit.unit_id for unit in revealable_units([hq])] == ["hq"]
    infantry = pu("inf", unit_type="infantry", toe_strength=3)
    assert [unit.unit_id for unit in revealable_units([hq, infantry])] == ["inf"]


def test_16_5_reconnaissance_is_battalion_sized_units():
    """RULE: 16.5."""
    assert reconnaissance(2, 4, lambda points, roll: 2) == 2
    assert reconnaissance(0, 4, lambda points, roll: 2) == 0


# ---------------------------------------------------------------------------
# 17 Morale
# ---------------------------------------------------------------------------


def test_17_22_cohesion_adjusts_basic_morale():
    """RULE: 17.22."""
    result = adjusted_morale(basic=1, cohesion=-4, roll=42,
                             table=morale_table(-2))
    assert result.modifier == -2
    assert result.adjusted == -1


def test_17_23_adjusted_morale_is_clamped():
    """RULE: 17.23."""
    assert adjusted_morale(basic=2, cohesion=0, roll=11,
                           table=morale_table(4)).adjusted == MORALE_MAX
    assert adjusted_morale(basic=-2, cohesion=-17, roll=11,
                           table=morale_table(-4)).adjusted == MORALE_MIN


def test_17_24_cohesion_rows_are_clamped():
    """RULE: 17.24."""
    assert cohesion_row(-20) == -17
    assert cohesion_row(9) == 8


def test_17_25_two_surrenders_cancel():
    """RULE: 17.25."""
    fallen = adjusted_morale(basic=0, cohesion=0, roll=11,
                             table=morale_table(None))
    assert fallen.surrendered
    assert mutual_surrender(fallen, fallen)
    safe = adjusted_morale(basic=0, cohesion=0, roll=11,
                           table=morale_table(-2))
    assert not mutual_surrender(fallen, safe)


def test_17_26_high_morale_ignores_surrender_as_minus_four():
    """RULE: 17.26."""
    result = adjusted_morale(basic=1, cohesion=-4, roll=11,
                             table=morale_table(None))
    assert not result.surrendered
    assert result.surrender_ignored
    assert result.modifier == -4
    assert result.adjusted == -3
    low = adjusted_morale(basic=1, cohesion=-11, roll=11,
                          table=morale_table(None))
    assert low.surrendered
    triple = adjusted_morale(basic=1, cohesion=-4, roll=11,
                             table=morale_table(None), enemy_triple_raw=True)
    assert triple.surrendered


def test_17_27_largest_unit_rule_picks_the_cohesion():
    """RULE: 17.27."""
    units = [pu("a", cohesion=-2), pu("b", cohesion=-5)]
    assert largest_unit_cohesion(units, largest_id="b") == -5
    raises(MoraleError,
           lambda: largest_unit_cohesion(units, largest_id="ghost"))


def test_17_28_rommel_adds_one():
    """RULE: 17.28."""
    result = adjusted_morale(basic=0, cohesion=0, roll=11,
                             table=morale_table(0), rommel=True)
    assert result.adjusted == 1


def test_17_32_training_areas_are_named():
    """RULE: 17.32."""
    from cna.rules.sec16_morale import TRAINING_AREAS

    assert {"cairo", "helwan", "alexandria"} <= TRAINING_AREAS


def test_17_34_six_stages_per_morale_point():
    """RULE: 17.34."""
    assert training_progress(0, untrained=-1, maximum=2) == -1
    assert training_progress(6, untrained=-1, maximum=2) == 0
    assert training_progress(12, untrained=-1, maximum=2) == 1
    assert training_progress(60, untrained=-1, maximum=2) == 2


def test_17_33_any_cp_expenditure_interrupts_training():
    """RULE: 17.33."""
    assert training_continues(cp_spent=0)
    assert not training_continues(cp_spent=1)


def test_17_35_instructor_battalion_rules():
    """RULE: 17.35."""
    base = dict(instructor_morale=1, required_morale=1)
    assert training_instructor_ok(unit_has_tanks=True, instructor_type="tank",
                                  instructor_toe_ratio=Fraction(1, 4), **base)
    assert not training_instructor_ok(unit_has_tanks=True,
                                      instructor_type="infantry",
                                      instructor_toe_ratio=Fraction(1, 4),
                                      **base)
    assert not training_instructor_ok(unit_has_tanks=False,
                                      instructor_type="infantry",
                                      instructor_toe_ratio=Fraction(1, 5),
                                      **base)


def test_17_52_54_voluntary_surrender_conditions():
    """RULE: 17.52."""
    allowed = dict(during_combat_steps=False, whole_hex=True,
                   adjacent_enemy_combat=True, acceptor_cp_available=2)
    assert voluntary_surrender_allowed(**allowed) == (True, "")
    assert voluntary_surrender_allowed(**{**allowed,
                                          "during_combat_steps": True}) == (
        False, "17.52")
    assert voluntary_surrender_allowed(**{**allowed,
                                          "whole_hex": False}) == (False,
                                                                    "17.52")
    assert voluntary_surrender_allowed(**{**allowed,
                                          "acceptor_cp_available": 1}) == (
        False, "17.54")


def test_17_56_material_destruction_percentages():
    """RULE: 17.56."""
    assert destruction_percent(4, material="tanks_guns") == 30
    assert destruction_percent(4, material="trucks") == 60
    assert destruction_percent(1, material="trucks") == 0
    assert destroyed_points(7, 30) == 2


# ---------------------------------------------------------------------------
# 18 Reserve status
# ---------------------------------------------------------------------------


def test_18_11_only_the_phasing_player_uses_reserve():
    """RULE: 18.11."""
    assert may_designate_reserve(phasing=False,
                                 phase="reserve_designation") == (False,
                                                                  "18.11")


def test_18_15_designation_is_a_phase_action():
    """RULE: 18.15."""
    assert may_designate_reserve(phasing=True,
                                 phase="reserve_designation") == (True, "")
    assert may_designate_reserve(phasing=True,
                                 phase="movement") == (False, "18.15")


def test_18_13_reserve_i_must_be_decided_in_the_first_release():
    """RULE: 18.13."""
    assert must_choose_first_release(RESERVE_I, release_segment=0)
    assert not must_choose_first_release(RESERVE_I, release_segment=1)
    assert not must_choose_first_release(RESERVE_II, release_segment=0)


def test_18_22_reserve_i_moves_one_hex_and_reserve_ii_never_moves():
    """RULE: 18.22."""
    assert reserve_movement_limit(RESERVE_I) == 1
    assert reserve_movement_limit(RESERVE_II) == 0
    assert reserve_move_allowed(status=RESERVE_I,
                                destination_enemy_controlled=False) == (True, "")
    assert reserve_move_allowed(status=RESERVE_I,
                                destination_enemy_controlled=True) == (
        False, "18.22")
    assert reserve_move_allowed(status=RESERVE_II,
                                destination_enemy_controlled=False) == (
        False, "18.22")


def test_18_23_24_release_capability_point_caps():
    """RULE: 18.23."""
    assert reserve_release_effects(RESERVE_I).cpa_fraction == 1
    assert reserve_release_effects(RESERVE_I).offensive_close_assaults == 1
    assert reserve_release_effects(RESERVE_II).cpa_fraction == Fraction(1, 2)
    assert reserve_cp_cap(15, RESERVE_II) == 7
    assert reserve_cp_cap(15, RESERVE_I) == 15


def test_18_24_reserve_ii_earns_a_disorganization_point():
    """RULE: 18.24."""
    assert reserve_disorganization(RESERVE_II, voluntary_combat=True) == 1
    assert reserve_disorganization(RESERVE_II, voluntary_combat=False) == 0
    assert reserve_disorganization(RESERVE_I, voluntary_combat=True) == 0


def test_18_25_released_units_may_move_beyond_two_hexes_once():
    """RULE: 18.25."""
    assert may_move_after_release(distance_to_enemy=9, immediate_segment=True)
    assert not may_move_after_release(distance_to_enemy=9,
                                      immediate_segment=False)
    assert may_move_after_release(distance_to_enemy=2, immediate_segment=False)


def test_18_26_reserve_costs_no_capability_points():
    """RULE: 18.26."""
    assert reserve_release_effects(RESERVE_I).cp_cost == 0
    assert reserve_release_effects(RESERVE_II).cp_cost == 0
