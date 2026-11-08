"""Zone of Control tests, one named case per test (RULE: 10.11-10.36).

The hex grid is a synthetic line; no map data is used.
"""

import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cna.rules.sec10_zoc import (
    ZOC_ENTRY_CP,
    ForcedRetreat,
    ZocUnit,
    actual_barrage_strength,
    combat_targets,
    enemy_controlled_hexes,
    exerts_zoc,
    holding_off_plan,
    holding_off_possible,
    holding_off_required,
    holding_off_satisfied,
    may_enter_enemy_zoc,
    may_move_zoc_to_zoc,
    must_attack,
    must_disclose_zoc,
    must_stop_after_entering,
    mutually_controlled,
    retreat_path_allowed,
    zoc_map,
)

ROAD = {"A": ("B",), "B": ("A", "C"), "C": ("B", "D"), "D": ("C",)}


def neighbours(hex_id):
    return ROAD.get(hex_id, ())


def z(unit_id, **kwargs):
    kwargs.setdefault("side", "Axis")
    kwargs.setdefault("position", "A")
    return ZocUnit(unit_id=unit_id, **kwargs)


def test_10_11_stacking_points_and_stack_total():
    """RULE: 10.11."""
    brigade = z("b", stacking_points=3)
    assert exerts_zoc(brigade, [brigade])
    battalion = z("c", stacking_points=1)
    assert not exerts_zoc(battalion, [battalion])
    friend = z("d", stacking_points=1)
    assert exerts_zoc(battalion, [battalion, friend])
    assert not exerts_zoc(z("convoy", kind="truck_convoy",
                            stacking_points=3),
                          [z("convoy", kind="truck_convoy",
                             stacking_points=3)])


def test_10_12_aircraft_ground_support_and_warships_never_exert():
    """RULE: 10.12."""
    for kind in ("aircraft", "ground_support", "warship"):
        unit = z(kind, kind=kind, stacking_points=3)
        assert not exerts_zoc(unit, [unit])


def test_10_13_informational_markers_never_exert():
    """RULE: 10.13."""
    marker = z("m", kind="informational", stacking_points=3)
    assert not exerts_zoc(marker, [marker])


def test_10_14_collapsed_units_never_exert():
    """RULE: 10.14."""
    unit = z("u", stacking_points=3, cohesion=-26)
    assert not exerts_zoc(unit, [unit])
    assert exerts_zoc(z("u", stacking_points=3, cohesion=-25), [unit])


def test_10_15_less_than_ten_raw_defensive_points():
    """RULE: 10.15."""
    first = z("a", stacking_points=1, raw_defensive_close_assault=4)
    second = z("b", stacking_points=1, raw_defensive_close_assault=5)
    assert not exerts_zoc(first, [first, second])
    strong = z("c", stacking_points=1, raw_defensive_close_assault=6)
    assert exerts_zoc(first, [first, strong])


def test_10_16_zoc_information_must_be_disclosed():
    """RULE: 10.16."""
    assert must_disclose_zoc(True, True)
    assert not must_disclose_zoc(True, False)


def test_10_21_blocked_hexsides_and_impassable_hexes():
    """RULE: 10.21."""
    unit = z("u", stacking_points=3)
    full = zoc_map([unit], neighbours=neighbours)
    assert full["B"] == frozenset({"u"})
    blocked = zoc_map([unit], neighbours=neighbours,
                      blocked_hexside=lambda src, dst: dst == "B")
    assert "B" not in blocked
    impassable = zoc_map([unit], neighbours=neighbours,
                         can_enter=lambda u, src, dst: dst != "B")
    assert "B" not in impassable


def test_10_22_entering_an_enemy_zoc_costs_no_cp():
    """RULE: 10.22."""
    assert ZOC_ENTRY_CP == 0
    allowed, case = may_enter_enemy_zoc(z("u", stacking_points=3), "B", {"B"})
    assert allowed and case == ""


def test_10_23_must_stop_on_entering_an_enemy_zoc():
    """RULE: 10.23."""
    assert must_stop_after_entering("B", {"B"})
    assert not must_stop_after_entering("C", {"B"})


def test_10_24_no_direct_zoc_to_zoc_move():
    """RULE: 10.24."""
    assert not may_move_zoc_to_zoc("A", "B", {"A", "B"})
    assert may_move_zoc_to_zoc("A", "B", {"A", "B"}, advance_into={"B"})
    assert may_move_zoc_to_zoc("A", "B", {"B"})


def test_10_25_movement_between_uncontrolled_hexes_is_open():
    """RULE: 10.25."""
    enemy = z("u", stacking_points=3, position="D")
    controlled = enemy_controlled_hexes([enemy], "Allied",
                                        neighbours=neighbours)
    assert controlled == frozenset({"C"})
    assert may_move_zoc_to_zoc("A", "B", controlled)


def test_10_26_friendly_combat_unit_negates_enemy_zoc():
    """RULE: 10.26."""
    enemy = z("e", stacking_points=3, position="B")
    friendly = z("f", side="Allied", position="C")
    controlled = enemy_controlled_hexes([enemy, friendly], "Allied",
                                        neighbours=neighbours)
    assert "A" in controlled
    assert "C" not in controlled


def test_10_27_mutual_control():
    """RULE: 10.27."""
    first = z("a", side="Axis", position="A", stacking_points=3)
    second = z("b", side="Allied", position="B", stacking_points=3)
    assert mutually_controlled(first, second, neighbours=neighbours)


def test_10_28_multiple_units_may_control_the_same_hex():
    """RULE: 10.28."""
    first = z("a", position="A", stacking_points=3)
    second = z("b", position="C", stacking_points=3)
    control = zoc_map([first, second], neighbours=neighbours)
    assert control["B"] == frozenset({"a", "b"})


def test_10_29_convoy_and_noncombat_entry_restrictions():
    """RULE: 10.29."""
    assert not may_enter_enemy_zoc(
        z("c", kind="truck_convoy", stacking_points=3), "B", {"B"})[0]
    assert not may_enter_enemy_zoc(
        z("e", kind="engineer"), "B", {"B"})[0]
    assert may_enter_enemy_zoc(
        z("e", kind="engineer"), "B", {"B"}, friendly_combat={"B"})[0]


def test_10_31_must_attack_covering_zocs():
    """RULE: 10.31."""
    enemy = z("e", position="B", stacking_points=3)
    friendly = z("f", side="Allied", position="A", stacking_points=3)
    assert combat_targets([enemy, friendly], "Allied",
                          neighbours=neighbours) == frozenset({"B"})
    assert must_attack([enemy, friendly], "Allied", neighbours=neighbours)


def test_10_32_artillery_and_pinned_units_are_exempt():
    """RULE: 10.32."""
    enemy = z("e", position="B", stacking_points=3)
    guns = z("g", side="Allied", position="A", kind="artillery",
             stacking_points=3)
    assert not must_attack([enemy, guns], "Allied", neighbours=neighbours)
    infantry = z("i", side="Allied", position="A", stacking_points=3,
                 pinned=True)
    assert not must_attack([enemy, infantry], "Allied", neighbours=neighbours)


def test_10_33_holding_off_can_replace_one_close_assault():
    """RULE: 10.33."""
    hexes = {"A": [z("a", kind="artillery")],
             "B": [z("b", kind="antitank")]}
    plan = holding_off_plan({"A": 1}, hexes)
    assert plan.held_off == ("A",)
    assert plan.must_assault == ("B",)
    assert not plan.satisfied
    assert holding_off_plan({"A": 1, "B": 1}, hexes).satisfied


def test_10_34_holding_off_requirement_and_barrage_strength():
    """RULE: 10.34."""
    eligible = z("a", kind="artillery", stacking_points=1)
    gun = z("g", kind="artillery", stacking_points=1, is_gun=True)
    small = z("s", kind="antitank", stacking_points=Fraction(1, 2))
    assert holding_off_required([eligible, gun, small]) == 1
    assert actual_barrage_strength(2, Fraction(1, 2)) == 11
    assert holding_off_satisfied(11, [eligible])


def test_10_35_impossible_holding_off_forces_close_assault():
    """RULE: 10.35."""
    enemies = [z("a", kind="artillery"), z("b", kind="aa")]
    assert not holding_off_possible(1, enemies)
    assert holding_off_possible(2, enemies)


def test_10_36_forced_retreat_is_three_hexes_and_three_dp():
    """RULE: 10.36."""
    requirement = ForcedRetreat()
    assert requirement.hexes == 3
    assert requirement.disorganization_points == 3
    assert retreat_path_allowed(["A", "B", "C"], {"D"})
    assert not retreat_path_allowed(["A", "B", "C"], {"B"})
