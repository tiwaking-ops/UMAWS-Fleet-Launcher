"""Combat tests, one named case per test (RULE: 11.11-15.96).

The Barrage, Anti-Armor and Close Assault tables are R-04 and are absent.
Every table used here is synthetic and labelled as such; no historical rating
or table value is invented.
"""

import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cna.rules.sec11_combat import (
    ARMOR,
    BACK,
    COMBAT_STAGES,
    CP_NON_PHASING_ATTACK,
    CP_PHASING_ATTACK,
    FORWARD,
    GUN,
    INFANTRY,
    TRUCKS,
    AdjustedDifferential,
    Assignment,
    AssaultRoll,
    BarrageOrder,
    BarrageRoll,
    CombatError,
    CombatUnit,
    LossTarget,
    UnitSize,
    aa_points,
    absorb_anti_armor,
    actual_points,
    anti_armor_column,
    anti_armor_prohibited,
    anti_armor_shifts,
    armor_loss_targets,
    artillery_vulnerability,
    assault_differential,
    assault_hexes_allowed,
    assault_raw_strength,
    assault_terrain_allowed,
    barrage_strength,
    basic_differential,
    capture_path_allowed,
    check_anti_armor_targets,
    check_assignment,
    check_assault_targets,
    check_barrage_orders,
    close_assault_strength,
    combat_cp,
    combined_arms_reduction,
    defenders_surrender,
    empty_defence,
    facility_barrage_points,
    group_may_coordinate,
    hex_combat_cp,
    hexside_shift,
    is_barrage_target,
    is_overrun_column,
    is_probe,
    may_close_assault,
    may_participate_anti_armor,
    may_retreat_before_assault,
    may_split_fire,
    must_retreat_unattackable,
    parenthesized_defence,
    parenthesized_rating_usable,
    pinned_effects,
    position_change_allowed,
    probe_defender_cp,
    raw_points,
    reassigned_to_close_assault,
    resolve_barrage,
    resolve_close_assault,
    resolve_truck_barrage,
    retreat_action_allowed,
    retreat_allowance,
    retreat_before_assault_effects,
    retreat_break_off,
    retreat_path_check,
    shifted_band,
    size_shift,
    strength,
    surrenders,
    targets_by_class,
)

ADJ = {"A": {"B", "C"}, "B": {"A", "C"}, "C": {"A", "B"}, "D": {"E"}}


def adjacent(source, destination):
    return destination in ADJ.get(source, set())


def cu(unit_id="u", **kwargs):
    kwargs.setdefault("side", "Axis")
    return CombatUnit(unit_id=unit_id, **kwargs)


def lt(unit_id, toe=4, rate=2, hex_id="A", weight=0):
    return LossTarget(unit_id=unit_id, toe_available=toe, absorb_rate=rate,
                      hex_id=hex_id, weight=weight)


def raises(error_type, call):
    try:
        call()
    except error_type:
        return
    raise AssertionError(f"expected {error_type.__name__}")


def synthetic_barrage(column, roll, target_class):
    """A labelled synthetic Barrage table; not an R-04 value."""
    assert column >= 0
    if target_class == TRUCKS:
        return BarrageRoll(roll=roll, truck_losses=4)
    return BarrageRoll(roll=roll, pin=roll == 11, toe_losses=2,
                       truck_losses=1)


# ---------------------------------------------------------------------------
# 11.1 combat characteristics
# ---------------------------------------------------------------------------


def test_11_11_only_artillery_has_a_barrage_rating():
    """RULE: 11.11."""
    gun = cu("gun", barrage_rating=9, toe_strength=3)
    infantry = cu("inf", toe_strength=3)
    assert gun.barrages and not infantry.barrages
    assert raw_points(gun.barrage_rating, gun.toe_strength) == 27


def test_11_12_guns_possess_vulnerability_ratings():
    """RULE: 11.12."""
    gun = cu("gun", target_class=GUN, vulnerability_rating=7)
    assert gun.is_gun
    assert artillery_vulnerability(gun) == 7
    assert not cu("inf").is_gun


def test_11_13_anti_armor_rating_direct_fire():
    """RULE: 11.13."""
    gun = cu("at", anti_armor_rating=5, toe_strength=6)
    assert strength([gun], "anti_armor") == 3


def test_11_14_armor_protection_marks_armor():
    """RULE: 11.14."""
    tank = cu("tank", armor_protection=3, toe_strength=7, target_class=ARMOR)
    assert tank.armour_target
    assert not cu("inf").armour_target


def test_11_15_offensive_and_defensive_close_assault_differ():
    """RULE: 11.15."""
    unit = cu("inf", offensive_close_assault=2, defensive_close_assault=4,
              toe_strength=7)
    assert strength([unit], "offensive") == 1
    assert strength([unit], "defensive") == 3


def test_11_16_aa_rating():
    """RULE: 11.16."""
    flak = cu("flak", aa_rating=4, toe_strength=2)
    assert aa_points(flak) == 8


# ---------------------------------------------------------------------------
# 11.2 Capability Point expenditures
# ---------------------------------------------------------------------------


def test_11_21_non_phasing_unit_expends_three():
    """RULE: 11.21."""
    assert combat_cp(phasing=False, activities={"barrage"}) == 3
    assert combat_cp(phasing=False, activities={"holding_off"}) == 3
    assert combat_cp(phasing=False, activities={"undergoes_assault"}) == 3


def test_11_22_phasing_unit_expends_five_to_attack():
    """RULE: 11.22."""
    for activity in ("barrage", "anti_armor", "close_assault"):
        assert combat_cp(phasing=True, activities={activity}) == 5


def test_11_23_probe_is_two_and_undergoing_barrage_three():
    """RULE: 11.23."""
    assert combat_cp(phasing=True, activities={"probe"}) == 2
    assert combat_cp(phasing=True, activities={"undergoes_barrage"}) == 3


def test_11_24_segment_caps():
    """RULE: 11.24."""
    assert combat_cp(phasing=True, activities={"barrage"}, spent=4) == 1
    assert combat_cp(phasing=True, activities={"barrage"}, spent=5) == 0
    assert combat_cp(phasing=False, activities={"barrage"}, spent=2) == 1
    assert combat_cp(phasing=False, activities={"barrage"}, spent=3) == 0


def test_11_25_expenditure_applies_to_every_unit_in_the_hex():
    """RULE: 11.25."""
    units = [cu("a"), cu("b")]
    assert hex_combat_cp(units, 5) == {"a": 5, "b": 5}


def test_11_26_probe_with_barraging_units_is_five():
    """RULE: 11.26."""
    assert combat_cp(phasing=True,
                     activities={"probe", "barrage"}) == CP_PHASING_ATTACK


def test_11_27_routed_defence_costs_one_cp():
    """RULE: 11.27."""
    assert combat_cp(phasing=False, activities={"defends"},
                     final_differential=-4) == 1
    assert combat_cp(phasing=False, activities={"defends"},
                     final_differential=-3) == CP_NON_PHASING_ATTACK


# ---------------------------------------------------------------------------
# 11.3 calculation of combat strengths
# ---------------------------------------------------------------------------


def test_11_32_actual_strength_rounds_halves_up():
    """RULE: 11.32."""
    assert actual_points(108) == 11
    assert actual_points(65) == 7
    assert actual_points(114) == 11
    assert actual_points(115) == 12


def test_11_33_below_half_an_actual_point_is_zero():
    """RULE: 11.33."""
    assert actual_points(4) == 0
    assert actual_points(5) == 1


def test_11_34_raw_points_are_totalled_before_dividing():
    """RULE: 11.34."""
    units = [cu("a", barrage_rating=9, toe_strength=3),
             cu("b", barrage_rating=9, toe_strength=3)]
    assert strength(units, "barrage") == 5          # 54 Raw, not 3 + 3


def test_11_37_aa_points_are_never_divided():
    """RULE: 11.37."""
    flak = cu("flak", aa_rating=5, toe_strength=3)
    assert aa_points(flak) == 15
    assert strength([flak], "aa") == 15


def test_11_38_vulnerability_is_not_scaled_by_toe():
    """RULE: 11.38."""
    gun = cu("gun", target_class=GUN, vulnerability_rating=9, toe_strength=3)
    assert artillery_vulnerability(gun) == 9


# ---------------------------------------------------------------------------
# 12.1 artillery positions
# ---------------------------------------------------------------------------


def test_12_11_a_unit_has_one_position():
    """RULE: 12.11."""
    assert cu("gun", position=FORWARD).position == FORWARD
    assert cu("gun", position=BACK).position == BACK
    raises(CombatError, lambda: cu("gun", position="split"))


def test_12_12_positions_change_only_at_the_segment_start():
    """RULE: 12.12."""
    assert position_change_allowed(at_combat_segment_start=True)
    assert not position_change_allowed(at_combat_segment_start=False)


def test_12_13_forward_guns_coordinate_across_hexes():
    """RULE: 12.13."""
    first = cu("a", position=FORWARD, hex_id="A")
    second = cu("b", position=FORWARD, hex_id="B")
    assert group_may_coordinate([first, second]) == (True, "")


def test_12_14_italian_forward_guns_coordinate_only_in_their_hex():
    """RULE: 12.14."""
    italian = cu("it", position=FORWARD, hex_id="A", italian=True)
    german = cu("de", position=FORWARD, hex_id="B")
    assert group_may_coordinate([italian, german]) == (False, "12.14")
    same_hex = cu("de2", position=FORWARD, hex_id="A")
    assert group_may_coordinate([italian, same_hex]) == (True, "")


def test_12_15_forward_guns_may_split_their_fire():
    """RULE: 12.15."""
    assert may_split_fire(cu("gun", position=FORWARD), targets=2)
    assert not may_split_fire(cu("gun", position=BACK), targets=2)


def test_12_16_back_guns_neither_coordinate_nor_split():
    """RULE: 12.16."""
    back = cu("back", position=BACK, hex_id="A")
    forward = cu("fwd", position=FORWARD, hex_id="B")
    assert group_may_coordinate([back, forward]) == (False, "12.16")
    assert group_may_coordinate([back]) == (True, "")


def test_12_18_artillery_assaulting_has_halved_vulnerability():
    """RULE: 12.18."""
    gun = cu("gun", target_class=GUN, vulnerability_rating=7)
    assert artillery_vulnerability(gun, role="offensive_close_assault") == 4


def test_12_19_anti_armor_artillery_has_vulnerability_two():
    """RULE: 12.19."""
    gun = cu("gun", target_class=GUN, vulnerability_rating=9)
    assert artillery_vulnerability(gun, role="anti_armor") == 2


# ---------------------------------------------------------------------------
# 12.2 target selection
# ---------------------------------------------------------------------------


def test_12_22_target_exceptions():
    """RULE: 12.22."""
    assert not is_barrage_target(cu("truck", kind="truck", stacking_points=0))
    assert not is_barrage_target(cu("sgsu", kind="sgsu", stacking_points=0))
    assert is_barrage_target(cu("eng", kind="engineer"))
    assert not is_barrage_target(cu("hq0", kind="hq", toe_strength=0))
    assert is_barrage_target(cu("hq1", kind="hq", toe_strength=2))
    assert not is_barrage_target(cu("hq2", kind="hq", toe_strength=2,
                                    parenthesized_close_assault=True))
    assert is_barrage_target(cu("dummy", kind="dummy_tank"))


def test_12_23_targets_are_stated_by_class():
    """RULE: 12.23."""
    units = [cu("gun", target_class=GUN), cu("tank", target_class=ARMOR),
             cu("inf", target_class=INFANTRY),
             cu("truck", kind="truck", stacking_points=0)]
    grouped = targets_by_class(units)
    assert grouped[GUN] == ("gun",)
    assert grouped[ARMOR] == ("tank",)
    assert grouped[INFANTRY] == ("inf",)


def test_12_24_unknown_targets_are_refused():
    """RULE: 12.24."""
    order = BarrageOrder("gun", "A", "ghost", "B", 1)
    violations = check_barrage_orders([order], [cu("gun", barrage_rating=9)])
    assert any(v.case == "12.23" for v in violations)


# ---------------------------------------------------------------------------
# 12.3-12.5 barrage restrictions and results
# ---------------------------------------------------------------------------


def test_12_31_targets_are_occupied_adjacent_hexes():
    """RULE: 12.31."""
    gun = cu("gun", barrage_rating=9, position=FORWARD, hex_id="A")
    target = cu("inf", side="Commonwealth", hex_id="B")
    far = BarrageOrder("gun", "A", "inf", "D", 1)
    assert any(v.case == "12.31" for v in
               check_barrage_orders([far], [gun, target], adjacent=adjacent))
    same = BarrageOrder("gun", "A", "inf", "A", 1)
    assert any(v.case == "12.31" for v in
               check_barrage_orders([same], [gun, target], adjacent=adjacent))


def test_12_32_a_target_is_barraged_once_per_adjacent_hex():
    """RULE: 12.32."""
    gun = cu("gun", barrage_rating=9, position=FORWARD, hex_id="A")
    target = cu("inf", side="Commonwealth", hex_id="B")
    one = BarrageOrder("gun", "A", "inf", "B", 1)
    duplicate = BarrageOrder("gun", "A", "inf", "B", 1)
    assert any(v.case == "12.32" for v in
               check_barrage_orders([one, duplicate], [gun, target],
                                    adjacent=adjacent))


def test_12_33_terrain_shifts_the_barrage_row():
    """RULE: 12.33."""
    bands = ((1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12))
    assert shifted_band(bands, 12, 2) == (7, 8)


def test_12_34_shifts_below_the_lowest_row_have_no_effect():
    """RULE: 12.34."""
    bands = ((1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12))
    assert shifted_band(bands, 12, 6) is None


def test_12_44_pin_results_skip_guns_and_artillery_hqs():
    """RULE: 12.44."""
    infantry = cu("inf", toe_strength=3)
    outcome = resolve_barrage(column=10, roll=11, target=infantry,
                              table=synthetic_barrage)
    assert outcome.pinned
    gun = cu("gun", target_class=GUN, toe_strength=3)
    assert not resolve_barrage(column=10, roll=11, target=gun,
                               table=synthetic_barrage).pinned
    hq = cu("hq", kind="hq", barrage_rating=9, toe_strength=3)
    assert not resolve_barrage(column=10, roll=11, target=hq,
                               table=synthetic_barrage).pinned


def test_12_45_a_number_result_destroys_toe_points():
    """RULE: 12.45."""
    def table(column, roll, target_class):
        return BarrageRoll(roll=roll, toe_losses=9)

    outcome = resolve_barrage(column=10, roll=21,
                              target=cu("inf", toe_strength=3), table=table)
    assert outcome.toe_losses == 3


def test_12_46_trucks_roll_separately_and_motorized_losses_take_trucks():
    """RULE: 12.46."""
    motorised = cu("inf", toe_strength=5, motorized=True)
    outcome = resolve_barrage(column=10, roll=21, target=motorised,
                              table=synthetic_barrage)
    assert outcome.toe_losses == 2
    assert outcome.truck_losses == 3        # one from the table, two carried
    assert resolve_truck_barrage(column=10, roll=21,
                                 table=synthetic_barrage) == 4


def test_12_54_supply_dumps_and_air_facilities_use_raw_points():
    """RULE: 12.54."""
    assert facility_barrage_points(facility="supply_dump",
                                   actual_points_used=7,
                                   raw_points_used=78) == 78
    assert facility_barrage_points(facility="major_city",
                                   actual_points_used=7,
                                   raw_points_used=78) == 7


# ---------------------------------------------------------------------------
# 13 Retreat Before Assault
# ---------------------------------------------------------------------------


def test_13_1_pinned_and_collapsed_units_cannot_retreat():
    """RULE: 13.1."""
    assert may_retreat_before_assault(pinned=True, cohesion=0) == (False, "12.44")
    assert may_retreat_before_assault(pinned=False, cohesion=-26) == (False, "13.1")
    assert may_retreat_before_assault(pinned=False, cohesion=-25)[0]


def test_13_21_retreat_is_voluntary_movement():
    """RULE: 13.21."""
    assert retreat_action_allowed("move")
    assert not retreat_action_allowed("barrage")


def test_13_22_break_off_costs_are_paid():
    """RULE: 13.22."""
    assert retreat_break_off(contact=False, engaged=False) == 0
    assert retreat_break_off(contact=True, engaged=False) == 2
    assert retreat_break_off(contact=True, engaged=True) == 4


def test_13_23_adjacent_units_may_spend_as_many_cp_as_they_wish():
    """RULE: 13.23."""
    assert retreat_allowance(adjacent_to_enemy_combat=True) is None


def test_13_24_other_units_are_capped_at_four_cp_or_one_hex():
    """RULE: 13.24."""
    assert retreat_allowance(adjacent_to_enemy_combat=False,
                             one_hex_cost=3) == 4
    assert retreat_allowance(adjacent_to_enemy_combat=False,
                             one_hex_cost=6) == 6


def test_13_25_only_movement_is_permitted():
    """RULE: 13.25."""
    assert retreat_action_allowed("move")
    assert retreat_action_allowed("blow_supply_dump")
    assert not retreat_action_allowed("close_assault")


def test_13_26_stop_in_a_zoc_and_never_zoc_to_zoc():
    """RULE: 13.26."""
    assert retreat_path_check("A", ["B"], {"B"}) == (True, "10.23")
    assert retreat_path_check("A", ["B"], {"A", "B"}) == (False, "13.26")
    assert retreat_path_check("A", ["B", "C"], {"C"}) == (True, "10.23")


def test_13_28_retreated_units_take_anti_armor_but_do_not_fire():
    """RULE: 13.28."""
    effects = retreat_before_assault_effects()
    assert effects.takes_anti_armor
    assert not effects.may_fire_anti_armor
    assert not effects.adds_close_assault_ratings
    assert effects.toe_counts_for_losses


# ---------------------------------------------------------------------------
# 14 Anti-Armor Combat
# ---------------------------------------------------------------------------


def test_14_11_only_committed_anti_armor_units_fire():
    """RULE: 14.11."""
    gun = cu("at", anti_armor_rating=4)
    assert may_participate_anti_armor(gun) == (True, "")
    assert may_participate_anti_armor(cu("inf")) == (False, "14.11")
    assert may_participate_anti_armor(gun, withheld=True) == (False, "14.21")


def test_14_12_only_committed_units_are_taxed():
    """RULE: 14.12."""
    committed = cu("a", armor_protection=3, toe_strength=2)
    withheld = cu("b", armor_protection=2, toe_strength=2)
    targets = armor_loss_targets([committed, withheld], withheld={"b"})
    assert [target.unit_id for target in targets] == ["a"]
    assert [target.unit_id for target in
            armor_loss_targets([committed, withheld], committed={"b"})] == ["b"]


def test_14_13_back_artillery_cannot_fire_anti_armor():
    """RULE: 14.13."""
    gun = cu("gun", anti_armor_rating=4, position=BACK)
    assert may_participate_anti_armor(gun) == (False, "14.13")


def test_14_14_artillery_in_anti_armor_role_has_vulnerability_two():
    """RULE: 14.14."""
    gun = cu("gun", target_class=GUN, vulnerability_rating=8)
    assert artillery_vulnerability(gun, role="anti_armor") == 2


def test_14_21_withheld_armor_is_not_affected():
    """RULE: 14.21."""
    tank = cu("tank", armor_protection=3, toe_strength=2)
    assert armor_loss_targets([tank], withheld={"tank"}) == ()


def test_14_22_a_hex_is_attacked_once():
    """RULE: 14.22."""
    assert check_anti_armor_targets(["A", "B"]) == ()
    assert any(v.case == "14.22" for v in check_anti_armor_targets(["A", "A"]))


def test_14_23_unused_points_reassign_when_no_armor_defends():
    """RULE: 14.23."""
    assert reassigned_to_close_assault(7, defending_armor_present=False) == 3
    assert reassigned_to_close_assault(7, defending_armor_present=True) == 0


def test_14_26_one_toe_point_cannot_serve_both_roles():
    """RULE: 14.26."""
    unit = cu("u", toe_strength=5, anti_armor_rating=3)
    check_assignment(Assignment("u", anti_armor_toe=2,
                                close_assault_toe=3), unit)
    raises(CombatError, lambda: check_assignment(
        Assignment("u", anti_armor_toe=3, close_assault_toe=3), unit))


def test_14_32_terrain_shifts_the_anti_armor_column():
    """RULE: 14.32."""
    assert anti_armor_column(9, 1) == 8


def test_14_33_a_hexside_shift_adds_to_the_hex_shift():
    """RULE: 14.33."""
    assert anti_armor_shifts(hex_shift=1, hexside_shift=1) == 2
    assert anti_armor_column(9, anti_armor_shifts(hex_shift=1,
                                                  hexside_shift=1)) == 7


def test_14_34_some_hexsides_forbid_anti_armor_fire():
    """RULE: 14.34."""
    assert anti_armor_prohibited(feature="ridge")
    assert not anti_armor_prohibited(feature="ridge", crossed_by_track=True)
    assert anti_armor_prohibited(feature="escarpment", crossed_by_road=True)
    assert not anti_armor_prohibited(feature="escarpment",
                                     crossed_by_track=True)


def test_14_35_shifts_never_go_below_the_zero_row():
    """RULE: 14.35."""
    assert anti_armor_column(1, 3) == 0


def test_14_42_armor_protection_absorbs_damage():
    """RULE: 14.42."""
    m13 = cu("m13", armor_protection=3, toe_strength=1, target_class=ARMOR)
    m11 = cu("m11", armor_protection=2, toe_strength=2, target_class=ARMOR)
    plan = absorb_anti_armor(7, [m13, m11])
    assert plan.removed("m13") == 1
    assert plan.removed("m11") == 2
    assert plan.absorbed == 7


def test_14_43_enough_toe_points_must_be_removed():
    """RULE: 14.43."""
    m13 = cu("m13", armor_protection=3, toe_strength=1)
    plan = absorb_anti_armor(3, [m13])
    assert plan.removed("m13") == 1
    assert plan.absorbed == 3


def test_14_45_excess_damage_is_ignored():
    """RULE: 14.45."""
    tank = cu("tank", armor_protection=3, toe_strength=1)
    plan = absorb_anti_armor(20, [tank])
    assert plan.removed("tank") == 1
    assert plan.excess == 17


def test_14_47_self_propelled_guns_absorb_armor_plus_vulnerability():
    """RULE: 14.47."""
    spg = cu("spg", armor_protection=2, vulnerability_rating=3,
             toe_strength=2, self_propelled=True)
    targets = armor_loss_targets([spg])
    assert targets[0].absorb_rate == 5


def test_14_48_halftracks_double_their_armor_protection():
    """RULE: 14.48."""
    halftracks = [cu("h1", armor_protection=2, toe_strength=1, halftrack=True),
                  cu("h2", armor_protection=2, toe_strength=1, halftrack=True)]
    targets = armor_loss_targets(halftracks)
    assert [target.absorb_rate for target in targets] == [4, 4]


def test_14_53_captured_tanks_move_three_hexes():
    """RULE: 14.53."""
    assert capture_path_allowed(["X", "Y", "Z"])
    assert not capture_path_allowed(["X", "Y", "Z", "W"])
    assert not capture_path_allowed(["X", "Y"], enemy_zoc={"Y"})
    assert not capture_path_allowed(["X", "Y"], impassable={"Y"})


# ---------------------------------------------------------------------------
# 15.1-15.3 which units participate and how
# ---------------------------------------------------------------------------


def test_15_11_close_assault_ratings_both_ways():
    """RULE: 15.11."""
    unit = cu("inf", offensive_close_assault=2, defensive_close_assault=4,
              toe_strength=7)
    assert assault_raw_strength([unit], offensive=True) == 14
    assert assault_raw_strength([unit], offensive=False) == 28


def test_15_12_pinned_and_retreated_units_do_not_add_ratings():
    """RULE: 15.12."""
    unit = cu("inf", defensive_close_assault=4, toe_strength=7)
    assert assault_raw_strength([unit], offensive=False,
                                excluded={"inf"}) == 0


def test_15_14_withheld_units_do_not_add_ratings():
    """RULE: 15.14."""
    first = cu("a", offensive_close_assault=2, toe_strength=5)
    second = cu("b", offensive_close_assault=2, toe_strength=5)
    assert assault_raw_strength([first, second], offensive=True,
                                excluded={"b"}) == 10


def test_15_15_out_of_ammo_units_cannot_assault_or_defend():
    """RULE: 15.15."""
    dry = cu("dry", offensive_close_assault=2, toe_strength=5,
             out_of_ammo=True)
    assert not may_close_assault(dry, offensive=True)
    assert defenders_surrender([dry])
    assert not defenders_surrender([dry, cu("wet", toe_strength=5)])


def test_15_16_and_15_23_a_hex_is_assaulted_once():
    """RULE: 15.16."""
    assert check_assault_targets(["A", "B"]) == ()
    assert any(v.case == "15.23" for v in check_assault_targets(["A", "A"]))


def test_15_17_parenthesized_ratings_need_an_empty_hex():
    """RULE: 15.17."""
    flak = cu("flak", parenthesized_close_assault=True,
              defensive_close_assault=1, toe_strength=2)
    assert parenthesized_rating_usable(flak, [flak])
    assert not parenthesized_rating_usable(flak, [flak, cu("inf", toe_strength=2)])


def test_15_18_three_to_one_against_parenthesized_defenders():
    """RULE: 15.18."""
    result = parenthesized_defence(attacker_raw=30, defender_raw=10)
    assert result.attacker_ignores_first_20
    assert result.defender_captured_at_20
    weak = parenthesized_defence(attacker_raw=20, defender_raw=10)
    assert not weak.attacker_ignores_first_20


def test_15_21_offensive_close_assault_needs_a_rating():
    """RULE: 15.21."""
    assert may_close_assault(cu("inf", offensive_close_assault=2),
                             offensive=True)
    assert not may_close_assault(cu("inf"), offensive=True)


def test_15_24_all_assaulted_hexes_must_adjoin_each_other():
    """RULE: 15.24."""
    assert assault_hexes_allowed("A", ["B", "C"], adjacent=adjacent)
    assert not assault_hexes_allowed("A", ["B", "D"], adjacent=adjacent)


def test_15_25_less_than_half_the_available_strength_is_a_probe():
    """RULE: 15.25."""
    assert is_probe(4, 10)
    assert not is_probe(5, 10)
    assert not is_probe(7, 10)


def test_15_26_basic_assault_differential():
    """RULE: 15.26."""
    assert basic_differential(6, 8) == -2
    assert basic_differential(6, 3) == 3


def test_15_28_fewer_than_five_raw_points_is_zero():
    """RULE: 15.28."""
    assert close_assault_strength(4) == 0
    assert close_assault_strength(6, other_raw=8) == 6
    assert close_assault_strength(6, other_raw=30) == 1


def test_15_29_an_empty_defence_retreats_three_hexes():
    """RULE: 15.29."""
    result = empty_defence()
    assert result.retreat_hexes == 3
    assert result.disorganization_points == 3


# ---------------------------------------------------------------------------
# 15.3-15.6 terrain, combined arms, size and morale
# ---------------------------------------------------------------------------


def test_15_32_defender_terrain_shifts_the_column():
    """RULE: 15.32."""
    result = assault_differential(attacker_raw=30, defender_raw=30,
                                  terrain_columns=-3)
    assert result.basic == 0
    assert result.final == -3


def test_15_33_a_hexside_shift_is_added():
    """RULE: 15.33."""
    assert hexside_shift([-2]) == -2
    result = assault_differential(attacker_raw=30, defender_raw=30,
                                  hexside_columns=-1)
    assert result.final == -1


def test_15_34_motorized_units_cannot_assault_some_terrain():
    """RULE: 15.34."""
    assert assault_terrain_allowed(motorized=True, feature="escarpment",
                                   direction="up") == (False, "15.34")
    assert assault_terrain_allowed(motorized=True, feature="escarpment",
                                   direction="down")[0]
    assert assault_terrain_allowed(motorized=True,
                                   terrain="salt_marsh") == (False, "15.34")
    assert must_retreat_unattackable(in_enemy_zoc=True, can_attack=False,
                                     other_unit_attacks=False)
    assert not must_retreat_unattackable(in_enemy_zoc=True, can_attack=True,
                                         other_unit_attacks=False)


def test_15_35_only_one_hexside_benefits_the_defender():
    """RULE: 15.35."""
    assert hexside_shift([-2, -1]) == -2
    assert hexside_shift([-2, -2], dual_terrain=True) == -4


def test_15_36_a_down_slope_offsets_an_up_escarpment():
    """RULE: 15.36."""
    assert hexside_shift([1, -3]) == -2


def test_15_4_combined_arms_reduces_unsupported_tanks():
    """RULE: 15.4."""
    assert combined_arms_reduction(tank_toe=2, supported_toe=0,
                                   tank_actual=1) == 1
    reduction = combined_arms_reduction(tank_toe=4, supported_toe=0,
                                        tank_actual=3)
    assert reduction == 1
    assert 3 - reduction == 2
    assert combined_arms_reduction(tank_toe=4, supported_toe=4,
                                   tank_actual=3) == 0


def test_15_51_double_the_raw_strength_shifts_two_columns():
    """RULE: 15.51."""
    result = assault_differential(attacker_raw=24, defender_raw=12)
    assert result.basic == 1
    assert result.final == 3
    assert any(shift.case == "15.51" and shift.columns == 2
               for shift in result.shifts)


def test_15_53_organizational_size_shift():
    """RULE: 15.53."""
    division = UnitSize("division")
    assert size_shift(division, UnitSize("brigade", points=3)) == 1
    assert size_shift(division, UnitSize("brigade", points=2)) == 2
    assert size_shift(division, UnitSize("battalion")) == 4
    assert size_shift(division, UnitSize("company")) == 8
    assert size_shift(UnitSize("brigade"), UnitSize("battalion")) == 2
    assert size_shift(UnitSize("battalion"), UnitSize("company")) == 2
    assert size_shift(unit_size := UnitSize("battalion"), unit_size) == 0


def test_15_54_zero_rated_defender_alone():
    """RULE: 15.54."""
    result = assault_differential(attacker_raw=24, defender_raw=0,
                                  zero_rated_defender_alone=True)
    assert result.basic == 2
    assert result.final == 5
    assert result.no_attacker_casualties
    assert not any(shift.case == "15.51" for shift in result.shifts)


def test_15_61_final_adjusted_morale_shifts_the_column():
    """RULE: 15.61."""
    result = assault_differential(attacker_raw=30, defender_raw=30,
                                  attacker_morale=2, defender_morale=-1)
    assert any(shift.case == "15.61" and shift.columns == 3
               for shift in result.shifts)
    assert result.final == 3


# ---------------------------------------------------------------------------
# 15.7-15.9 results, casualties and probes
# ---------------------------------------------------------------------------


def test_15_74_a_retreat_takes_priority_over_engaged():
    """RULE: 15.74."""
    outcome = resolve_close_assault(
        adjusted=AdjustedDifferential(basic=0),
        attacker_roll=AssaultRoll(roll=21),
        defender_roll=AssaultRoll(roll=21, engaged=True, retreat_hexes=1),
        attacker_raw=10, defender_raw=10,
        attacker_targets=[lt("a", 10, 2)],
        defender_targets=[lt("d", 10, 2)])
    assert not outcome.defender.engaged
    assert outcome.defender.retreat_hexes == 1


def test_15_77_overrun_rounds_defender_losses_up():
    """RULE: 15.77."""
    assert is_overrun_column(11)
    assert not is_overrun_column(10)
    outcome = resolve_close_assault(
        adjusted=AdjustedDifferential(basic=11),
        attacker_roll=AssaultRoll(roll=21),
        defender_roll=AssaultRoll(roll=21, loss_percent=15),
        attacker_raw=7, defender_raw=7,
        attacker_targets=[lt("a", 7, 2)],
        defender_targets=[lt("d", 7, 2)])
    assert outcome.overrun
    assert outcome.defender.raw_lost == 2      # 1.05 rounded up


def test_15_81_engaged_units_are_not_in_contact():
    """RULE: 15.81."""
    engaged = resolve_close_assault(
        adjusted=AdjustedDifferential(basic=0),
        attacker_roll=AssaultRoll(roll=21, engaged=True),
        defender_roll=AssaultRoll(roll=21),
        attacker_raw=10, defender_raw=10,
        attacker_targets=[lt("a", 10, 2)],
        defender_targets=[lt("d", 10, 2)])
    assert engaged.attacker.engaged
    assert not engaged.attacker.contact
    quiet = resolve_close_assault(
        adjusted=AdjustedDifferential(basic=0),
        attacker_roll=AssaultRoll(roll=21),
        defender_roll=AssaultRoll(roll=21),
        attacker_raw=10, defender_raw=10,
        attacker_targets=[lt("a", 10, 2)],
        defender_targets=[lt("d", 10, 2)])
    assert quiet.attacker.contact


def test_15_82_each_hex_not_retreated_adds_ten_percent():
    """RULE: 15.82."""
    outcome = resolve_close_assault(
        adjusted=AdjustedDifferential(basic=0),
        attacker_roll=AssaultRoll(roll=21),
        defender_roll=AssaultRoll(roll=21, loss_percent=25, retreat_hexes=2),
        attacker_raw=10, defender_raw=10,
        attacker_targets=[lt("a", 10, 2)],
        defender_targets=[lt("d", 10, 2)],
        defender_retreat_shortfall=1)
    assert outcome.defender.loss_percent == 35
    assert outcome.defender.raw_lost == 3       # 3.5, defender rounds down


def test_15_83_attacker_rounds_up_and_defender_rounds_down():
    """RULE: 15.83."""
    outcome = resolve_close_assault(
        adjusted=AdjustedDifferential(basic=0),
        attacker_roll=AssaultRoll(roll=21, loss_percent=10),
        defender_roll=AssaultRoll(roll=21, loss_percent=10),
        attacker_raw=7, defender_raw=7,
        attacker_targets=[lt("a", 7, 2)],
        defender_targets=[lt("d", 7, 2)])
    assert outcome.attacker.raw_lost == 1
    assert outcome.defender.raw_lost == 0


def test_15_85_captured_percentage_is_rounded_up():
    """RULE: 15.85."""
    outcome = resolve_close_assault(
        adjusted=AdjustedDifferential(basic=0),
        attacker_roll=AssaultRoll(roll=21),
        defender_roll=AssaultRoll(roll=21, loss_percent=20,
                                  captured_percent=50),
        attacker_raw=10, defender_raw=10,
        attacker_targets=[lt("a", 10, 2)],
        defender_targets=[lt("d", 10, 2)])
    assert outcome.defender.toe_lost == 1
    assert outcome.defender.captured_toe == 1


def test_15_87_thirty_percent_losses_earn_three_disorganization_points():
    """RULE: 15.87."""
    outcome = resolve_close_assault(
        adjusted=AdjustedDifferential(basic=0),
        attacker_roll=AssaultRoll(roll=21, loss_percent=30),
        defender_roll=AssaultRoll(roll=21, loss_percent=29),
        attacker_raw=10, defender_raw=10,
        attacker_targets=[lt("a", 10, 2)],
        defender_targets=[lt("d", 10, 2)])
    assert outcome.attacker.disorganization_points == 3
    assert outcome.defender.disorganization_points == 0


def test_15_88_low_cohesion_surrenders():
    """RULE: 15.88."""
    assert surrenders(out_of_ammo=False, cohesion=-17)
    assert not surrenders(out_of_ammo=False, cohesion=-16)
    assert surrenders(out_of_ammo=True, cohesion=0)


def test_15_93_a_probe_ignores_engaged():
    """RULE: 15.93."""
    outcome = resolve_close_assault(
        adjusted=AdjustedDifferential(basic=0),
        attacker_roll=AssaultRoll(roll=21, engaged=True),
        defender_roll=AssaultRoll(roll=21, engaged=True),
        attacker_raw=10, defender_raw=10,
        attacker_targets=[lt("a", 10, 2)],
        defender_targets=[lt("d", 10, 2)],
        probe=True)
    assert not outcome.attacker.engaged
    assert not outcome.defender.engaged


def test_15_95_a_recce_probe_loses_ten_percent_less():
    """RULE: 15.95."""
    outcome = resolve_close_assault(
        adjusted=AdjustedDifferential(basic=0),
        attacker_roll=AssaultRoll(roll=21, loss_percent=25),
        defender_roll=AssaultRoll(roll=21),
        attacker_raw=10, defender_raw=10,
        attacker_targets=[lt("a", 10, 2)],
        defender_targets=[lt("d", 10, 2)],
        probe=True, attacker_recce_only=True)
    assert outcome.attacker.loss_percent == 15


def test_15_96_a_bad_probe_costs_the_defender_nothing():
    """RULE: 15.96."""
    assert probe_defender_cp(-4) == 0
    assert probe_defender_cp(-3) == 2
    assert combat_cp(phasing=False, activities={"probe"},
                     final_differential=-4) == 0


def test_combat_stages_are_in_rulebook_order():
    """RULE: 11.0."""
    assert COMBAT_STAGES == ("position", "barrage", "retreat_before_assault",
                             "force_assignment", "anti_armor",
                             "close_assault")


def test_pinned_effects_follow_12_44():
    """RULE: 12.44."""
    pinned = pinned_effects(True)
    assert not pinned.may_move
    assert not pinned.may_anti_armor
    assert not pinned.may_close_assault
    free = pinned_effects(False)
    assert free.may_move and free.may_anti_armor and free.may_close_assault


def test_barrage_strength_totals_raw_points_per_target():
    """RULE: 12.13, 11.34."""
    first = cu("a", barrage_rating=9, position=FORWARD, hex_id="A")
    second = cu("b", barrage_rating=9, position=FORWARD, hex_id="B")
    target = cu("t", side="Commonwealth", hex_id="C")
    orders = [BarrageOrder("a", "A", "t", "C", 2),
              BarrageOrder("b", "B", "t", "C", 2)]
    assert barrage_strength(orders, [first, second, target]) == {"t": 4}


def test_assault_differential_reports_its_shifts():
    """RULE: 15.27."""
    result = assault_differential(attacker_raw=30, defender_raw=15,
                                  attacker_morale=1, defender_morale=0,
                                  terrain_columns=-2)
    assert result.final == result.basic + sum(
        shift.columns for shift in result.shifts)
    assert any(shift.case == "15.32" and shift.columns == -2
               for shift in result.shifts)
