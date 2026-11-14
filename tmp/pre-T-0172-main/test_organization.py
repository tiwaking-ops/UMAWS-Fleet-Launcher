"""Organization, reinforcement and replacement tests.

RULE: 19.11-19.98, 20.11-20.85

All Formation Organization, Maximum Attachment, Replacement Pool and
Production values are R-04/R-07 and are supplied by the caller in these tests.
"""

import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cna.rules.sec19_organization import (
    AT_READINESS_PERCENT,
    CW_INFANTRY_AT_FIRST_TURN,
    HQ_AT_LIMIT,
    REPLACEMENT_MORALE,
    FormationLimits,
    OrgUnit,
    OrganizationError,
    assignment_allowed,
    attachment_allowed,
    attachment_cp,
    augmented_hq_cpa,
    augmented_hq_stacking_points,
    cw_infantry_at_allowed,
    cw_infantry_at_affects_shell,
    cw_infantry_at_cpa,
    cw_infantry_upgrade_allowed,
    detachment_cp,
    detachment_stops_movement,
    even_distribution,
    german_battle_group_allowed,
    hq_at_augmentation_allowed,
    hq_revive_allowed,
    italian_battle_group_allowed,
    nested_attachment_allowed,
    reassignment_allowed,
    rebuild_allowed,
    rebuild_ceiling,
    rebuild_cp,
    rebuild_phase_allowed,
    recce_upgrade_allowed,
    recce_upgrade_effect,
    reinforcement_arrival_cp,
    reinforcement_entry_allowed,
    replacement_absorption_allowed,
    replacement_capacity,
    replacement_class_for,
    replacement_combat_role_allowed,
    replacement_cpa_state,
    replacement_planned_in_time,
    replacement_training_location_allowed,
    replacement_training_stages,
    replacement_zoc_allowed,
    substitution_allowed,
    withdrawal_choice,
    withdrawal_status,
    withdrawal_strength_ok,
)


def unit(unit_id="u", **kwargs):
    kwargs.setdefault("side", "Axis")
    kwargs.setdefault("unit_type", "infantry")
    return OrgUnit(unit_id=unit_id, **kwargs)


def parent(unit_id="p", **kwargs):
    kwargs.setdefault("side", "Axis")
    kwargs.setdefault("unit_type", "brigade")
    kwargs.setdefault("level", "brigade")
    return OrgUnit(unit_id=unit_id, **kwargs)


def raises(error_type, call):
    try:
        call()
    except error_type:
        return
    raise AssertionError(f"expected {error_type.__name__}")


# ---------------------------------------------------------------------------
# 19.1-19.4 Assignment, attachment and cost
# ---------------------------------------------------------------------------


def test_19_21_assignment_needs_an_independent_unit_and_a_chart_slot():
    """RULE: 19.21."""
    limits = FormationLimits(assigned={"infantry": 3})
    free = unit("u1", independent=True)
    assert assignment_allowed(free, parent(), limits=limits,
                              assigned_counts={"infantry": 2}) == (True, "")
    full = assignment_allowed(free, parent(), limits=limits,
                              assigned_counts={"infantry": 3})
    assert full == (False, "19.21")
    attached = unit("u2", attached_to="p")
    assert assignment_allowed(attached, parent(), limits=limits,
                              assigned_counts={}) == (False, "19.28")


def test_19_27_asterisk_units_may_not_be_reassigned():
    """RULE: 19.27."""
    frozen = unit("u", independent=True, frozen_assignment=True)
    assert assignment_allowed(frozen, parent(), limits=FormationLimits(),
                              assigned_counts={}) == (False, "19.27")


def test_19_28_a_unit_may_not_be_assigned_twice():
    """RULE: 19.28."""
    assigned = unit("u", independent=True, assigned_to="other")
    assert assignment_allowed(assigned, parent(), limits=FormationLimits(),
                              assigned_counts={}) == (False, "19.28")


def test_19_13_attachment_needs_the_same_hex_and_one_parent():
    """RULE: 19.13."""
    limits = FormationLimits(attached={"infantry": 1})
    candidate = unit("u", independent=True)
    assert attachment_allowed(candidate, parent(), limits=limits,
                              attached_counts={},
                              same_hex=False) == (False, "19.42")
    assert attachment_allowed(candidate, parent(), limits=limits,
                              attached_counts={}, same_hex=True) == (True, "")
    already = unit("v", independent=True, attached_to="p2")
    assert attachment_allowed(already, parent(), limits=limits,
                              attached_counts={},
                              same_hex=True) == (False, "19.13")


def test_19_4_assigned_units_attach_without_a_chart_slot():
    """RULE: 19.4."""
    limits = FormationLimits(attached={})
    assigned = unit("u", assigned_to="p")
    assert attachment_allowed(assigned, parent(), limits=limits,
                              attached_counts={}, same_hex=True) == (True, "")
    stranger = unit("v", independent=True)
    assert attachment_allowed(stranger, parent(), limits=limits,
                              attached_counts={"infantry": 1},
                              same_hex=True) == (False, "19.5")


def test_19_46_nested_attachments_count_unless_substituted():
    """RULE: 19.46."""
    assert not nested_attachment_allowed(parent_attached=True)
    assert nested_attachment_allowed(parent_attached=True, substitution=True)
    assert nested_attachment_allowed(parent_attached=False)


def test_19_41_42_attachment_costs():
    """RULE: 19.41."""
    assigned = unit("u", assigned_to="p")
    assert attachment_cp(assigned, parent(), phase="movement",
                         same_hex=True).subsidiary == 1
    stranger = unit("v", independent=True)
    assert attachment_cp(stranger, parent(), phase="reorganization",
                         same_hex=True).subsidiary == 2
    raises(OrganizationError,
           lambda: attachment_cp(stranger, parent(), phase="movement",
                                 same_hex=True))


def test_19_43_44_detachment_costs_and_phases():
    """RULE: 19.43."""
    assigned = unit("u", assigned_to="p")
    assert detachment_cp(assigned, phase="movement").rule == "19.43"
    attached = unit("v", attached_to="p")
    assert detachment_cp(attached, phase="movement").rule == "19.44"
    raises(OrganizationError,
           lambda: detachment_cp(attached, phase="reserve_designation"))
    assert detachment_stops_movement(phase="movement")
    assert not detachment_stops_movement(phase="reorganization")


def test_19_45_substitution_must_fit_the_missing_slot():
    """RULE: 19.45."""
    assert substitution_allowed(substitute_composition={"infantry": 3},
                                missing_limits={"infantry": 3})
    assert not substitution_allowed(substitute_composition={"infantry": 4},
                                    missing_limits={"infantry": 3})


def test_19_22_26_reassignment_paths():
    """RULE: 19.22."""
    unit_ = unit("u", assigned_to="p")
    assert reassignment_allowed(unit_, commonwealth_battalion=True,
                                parent_exists=True) == (True, "19.26")
    assert reassignment_allowed(unit_, commonwealth_battalion=False,
                                parent_exists=False) == (True, "19.22")
    assert reassignment_allowed(unit_, commonwealth_battalion=False,
                                parent_exists=True) == (False, "19.28")


# ---------------------------------------------------------------------------
# 19.6 Rebuilding
# ---------------------------------------------------------------------------


def test_19_61_rebuilding_never_exceeds_printed_toe():
    """RULE: 19.61."""
    assert rebuild_ceiling(unit(max_toe=9, toe=4)) == 9


def test_19_62_eliminated_units_are_not_rebuilt():
    """RULE: 19.62."""
    assert not rebuild_allowed(eliminated=True)
    assert rebuild_allowed(eliminated=True, hq_cadre=True)
    assert rebuild_allowed(eliminated=False)


def test_19_63_hq_revival_needs_half_its_units_and_two_points():
    """RULE: 19.63."""
    assert hq_revive_allowed(assigned_alive=2, assigned_total=4,
                             infantry_replacement_points=2)
    assert not hq_revive_allowed(assigned_alive=1, assigned_total=4,
                                 infantry_replacement_points=2)
    assert not hq_revive_allowed(assigned_alive=3, assigned_total=4,
                                 infantry_replacement_points=1)


def test_19_64_replacement_classes_by_unit_type():
    """RULE: 19.64."""
    assert replacement_class_for("infantry") == {"infantry"}
    assert replacement_class_for("hq") == {"infantry"}
    assert replacement_class_for("tank") == {"tank"}
    assert replacement_class_for("heavy_weapons") == {"infantry", "gun"}
    assert replacement_class_for("battleship") == frozenset()


def test_19_68_rebuild_capability_points():
    """RULE: 19.68."""
    assert rebuild_cp(0) == 0
    assert rebuild_cp(1) == 1
    assert rebuild_cp(2) == 1
    assert rebuild_cp(3) == 2
    assert rebuild_cp(4) == 2


def test_19_68_49_rebuilding_is_a_reorganization_action():
    """RULE: 19.68."""
    assert rebuild_phase_allowed("reorganization")
    assert not rebuild_phase_allowed("movement")
    assert replacement_absorption_allowed("reorganization")
    assert not replacement_absorption_allowed("movement")


# ---------------------------------------------------------------------------
# 19.7 Battle Groups
# ---------------------------------------------------------------------------


def test_19_72_german_battle_group_limits():
    """RULE: 19.72."""
    assert german_battle_group_allowed(battalions=4, tanks=1, infantry=2,
                                       companies=2) == (True, "")
    assert german_battle_group_allowed(battalions=5, tanks=1, infantry=2,
                                       companies=2) == (False, "19.72")
    assert german_battle_group_allowed(battalions=4, tanks=2, infantry=2,
                                       companies=2) == (False, "19.72")
    assert german_battle_group_allowed(battalions=4, tanks=1, infantry=3,
                                       companies=2) == (False, "19.72")
    assert german_battle_group_allowed(battalions=4, tanks=1, infantry=2,
                                       companies=3) == (False, "19.72")


def test_19_73_italian_battle_group_limits():
    """RULE: 19.73."""
    assert italian_battle_group_allowed(battalions=3, infantry=2, armor=1,
                                        companies=1,
                                        existing_groups=1) == (True, "")
    assert italian_battle_group_allowed(battalions=4, infantry=2, armor=1,
                                        companies=1,
                                        existing_groups=0) == (False, "19.73")
    assert italian_battle_group_allowed(battalions=3, infantry=2, armor=2,
                                        companies=1,
                                        existing_groups=0) == (False, "19.73")
    assert italian_battle_group_allowed(battalions=3, infantry=2, armor=1,
                                        companies=1,
                                        existing_groups=2) == (False, "19.73")


# ---------------------------------------------------------------------------
# 19.8-19.9 Anti-tank augmentation
# ---------------------------------------------------------------------------


def test_19_81_to_19_86_hq_anti_tank_augmentation():
    """RULE: 19.81."""
    base = dict(hq_level="brigade", hq_symbol="infantry", current_at_toe=0,
                added_toe=3, all_at_ready=True)
    assert hq_at_augmentation_allowed(**base) == (True, "")
    assert hq_at_augmentation_allowed(**{**base, "current_at_toe": 5,
                                         "added_toe": 2}) == (False, "19.81")
    assert hq_at_augmentation_allowed(**{**base, "added_toe": 2}) == (
        False, "19.83")
    assert hq_at_augmentation_allowed(**{**base,
                                         "all_at_ready": False}) == (
        False, "19.82")
    assert hq_at_augmentation_allowed(**{**base, "captured_gun": True}) == (
        False, "19.86")
    mixed = hq_at_augmentation_allowed(**{**base, "existing_gun_type": "pak38",
                                          "new_gun_type": "flak18"})
    assert mixed == (False, "19.86")
    assert hq_at_augmentation_allowed(**{**base, "hq_level": "battalion"}) == (
        False, "19.81")


def test_19_85_87_augmented_hq_cpa_and_stacking():
    """RULE: 19.85."""
    assert HQ_AT_LIMIT == 6 and AT_READINESS_PERCENT == 67
    assert augmented_hq_cpa(4) == 4
    assert augmented_hq_stacking_points() == 0


def test_19_91_to_19_96_commonwealth_infantry_anti_tank():
    """RULE: 19.91."""
    assert CW_INFANTRY_AT_FIRST_TURN == 75
    base = dict(game_turn=75, cpa=10, offensive_rating=1, defensive_rating=2,
                motorized=False, current_at_toe=0, parent_at_max=True)
    assert cw_infantry_at_allowed(**base) == (True, "")
    assert cw_infantry_at_allowed(**{**base, "game_turn": 74}) == (
        False, "19.91")
    assert cw_infantry_at_allowed(**{**base, "cpa": 11}) == (False, "19.92")
    assert cw_infantry_at_allowed(**{**base, "offensive_rating": 2,
                                     "defensive_rating": 1}) == (False, "19.92")
    assert cw_infantry_at_allowed(**{**base, "current_at_toe": 1}) == (
        False, "19.94")
    assert cw_infantry_at_allowed(**{**base, "motorized": True,
                                     "current_at_toe": 1}) == (True, "")
    assert cw_infantry_at_allowed(**{**base, "parent_at_max": False}) == (
        False, "19.96")


def test_19_97_98_absorbed_anti_tank_uses_infantry_cpa_and_shell():
    """RULE: 19.97."""
    assert cw_infantry_at_cpa(10) == 10
    assert cw_infantry_at_affects_shell() is False


# ---------------------------------------------------------------------------
# 20.1 Reinforcements
# ---------------------------------------------------------------------------


def test_20_14_commonwealth_arrival_ports():
    """RULE: 20.14."""
    assert reinforcement_entry_allowed(side="commonwealth",
                                       entry="cairo") == (True, "")
    assert reinforcement_entry_allowed(side="commonwealth",
                                       entry="alexandria") == (False, "20.14")
    assert reinforcement_entry_allowed(side="commonwealth", entry="alexandria",
                                       alexandria_permitted=True) == (
        True, "20.14")


def test_20_15_axis_arrival_ports_and_benghazi_diversion():
    """RULE: 20.15."""
    assert reinforcement_entry_allowed(side="axis",
                                       entry="tripoli") == (True, "")
    assert reinforcement_entry_allowed(side="axis", entry="benghazi") == (
        False, "20.15")
    ok = dict(side="axis", entry="benghazi", west_of_mersa_matruh=False,
              port_level=3, stacking_ok=True, battalion_equivalents=1,
              company_equivalents=0, truck_points=10)
    assert reinforcement_entry_allowed(**ok) == (True, "20.15")
    assert reinforcement_entry_allowed(**{**ok, "port_level": 2}) == (
        False, "20.15")
    assert reinforcement_entry_allowed(**{**ok, "battalion_equivalents": 2}) == (
        False, "20.15")
    assert reinforcement_entry_allowed(**{**ok, "truck_points": 11}) == (
        False, "20.15")


def test_20_12_arrival_costs_no_capability_points():
    """RULE: 20.12."""
    assert reinforcement_arrival_cp() == 0


def test_20_21_replacement_planning_lead_times():
    """RULE: 20.21."""
    assert replacement_planned_in_time(side="axis", planned_turn=3,
                                       arrival_turn=5)
    assert not replacement_planned_in_time(side="axis", planned_turn=4,
                                           arrival_turn=5)
    assert not replacement_planned_in_time(side="commonwealth",
                                           planned_turn=1, arrival_turn=4)
    assert replacement_planned_in_time(side="commonwealth", planned_turn=1,
                                       arrival_turn=5)


def test_20_74_points_are_divided_evenly_over_the_stages():
    """RULE: 20.74."""
    assert even_distribution(10, stages=3) == (4, 3, 3)
    assert even_distribution(2, stages=3) == (1, 1, 0)
    assert even_distribution(0, stages=1) == (0,)


# ---------------------------------------------------------------------------
# 20.2-20.4 Replacement Points
# ---------------------------------------------------------------------------


def test_20_42_replacement_point_characteristics():
    """RULE: 20.42."""
    assert REPLACEMENT_MORALE == -3
    assert replacement_zoc_allowed(friendly_occupies=True)
    assert not replacement_zoc_allowed(friendly_occupies=False)
    assert replacement_combat_role_allowed("defend_close_assault")
    assert not replacement_combat_role_allowed("attack")
    assert replacement_cpa_state(spent=5, cpa=5) is None
    assert replacement_cpa_state(spent=6, cpa=5) == -26


def test_20_43_replacement_training_schedule():
    """RULE: 20.43."""
    assert replacement_training_stages("gun") == 1
    assert replacement_training_stages("infantry") == 3
    assert replacement_training_stages("tank") == 6
    assert replacement_training_stages("recce") == 6
    raises(OrganizationError, lambda: replacement_training_stages("horse"))


def test_20_43_replacement_training_locations():
    """RULE: 20.43."""
    assert replacement_training_location_allowed("axis", "tripoli")
    assert not replacement_training_location_allowed("axis", "cairo")
    assert replacement_training_location_allowed("axis", "cairo",
                                                 major_city=True)
    assert replacement_training_location_allowed("commonwealth", "cairo")


def test_20_65_replacement_capacity_is_the_unused_toe():
    """RULE: 20.65."""
    assert replacement_capacity(unit(max_toe=9, toe=4)) == 5


# ---------------------------------------------------------------------------
# 20.5 Upgrading
# ---------------------------------------------------------------------------


def test_20_51_to_20_55_recce_upgrade():
    """RULE: 20.51."""
    assert recce_upgrade_allowed(month=(1939, 1),
                                 anti_armor_rating=0)
    assert not recce_upgrade_allowed(month=(1938, 12),
                                     anti_armor_rating=0)
    assert not recce_upgrade_allowed(month=(1941, 6),
                                     anti_armor_rating=1)
    assert not recce_upgrade_allowed(month=(1941, 6), anti_armor_rating=0,
                                     excluded=True)
    assert recce_upgrade_effect() == (1, 3)


def test_20_77_commonwealth_infantry_upgrade():
    """RULE: 20.77."""
    assert cw_infantry_upgrade_allowed(month=(1942, 7), offensive_rating=1,
                                       defensive_rating=2)
    assert not cw_infantry_upgrade_allowed(month=(1942, 6),
                                           offensive_rating=1,
                                           defensive_rating=2)
    assert not cw_infantry_upgrade_allowed(month=(1942, 7),
                                           offensive_rating=2,
                                           defensive_rating=2)


# ---------------------------------------------------------------------------
# 20.8 Withdrawals
# ---------------------------------------------------------------------------


def test_20_82_withdrawal_strength_threshold():
    """RULE: 20.82."""
    assert withdrawal_strength_ok(unit(max_toe=4, toe=3))
    assert not withdrawal_strength_ok(unit(max_toe=4, toe=2))


def test_20_82_withdrawal_choice_prefers_a_full_strength_unit():
    """RULE: 20.82."""
    weak = unit("weak", max_toe=10, toe=5)
    strong = unit("strong", max_toe=4, toe=3)
    assert withdrawal_choice([weak, strong]).unit_id == "strong"
    assert withdrawal_choice([weak]).unit_id == "weak"
    assert withdrawal_choice([]) is None


def test_20_83_withdrawal_status():
    """RULE: 20.83."""
    assert withdrawal_status(at_port=True, strength_ok=True) == "withdrawn"
    assert withdrawal_status(at_port=True, strength_ok=False) == "eliminated"
    assert withdrawal_status(at_port=False, strength_ok=True) == "eliminated"
