"""Stacking tests, one named case per test (RULE: 9.11-9.35).

All values are synthetic: Stacking Points are caller-supplied and the TEC
limit comes from the test, never from historical data (9.13, R-04).
"""

import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cna.rules.sec09_stacking import (
    Formation,
    HexContext,
    StackingError,
    StackingUnit,
    check_end_of_movement,
    check_road_passage,
    effective_points,
    formation_units,
    level_for_points,
    passage_allowed,
    points_in_hex,
    road_points,
    small_company_count,
)


def unit(unit_id, **kwargs):
    kwargs.setdefault("side", "Axis")
    return StackingUnit(unit_id=unit_id, **kwargs)


def test_9_11_printed_stacking_points_count():
    """RULE: 9.11, 9.13."""
    assert effective_points(unit("a", stacking_points=3)) == 3
    assert points_in_hex([unit("a", stacking_points=2),
                          unit("b", stacking_points=1)]) == 3


def test_9_12_hq_counts_only_with_attached_combat_units():
    """RULE: 9.12."""
    assert effective_points(unit("hq", kind="hq")) == 0
    assert effective_points(unit("hq", kind="hq", attached_combat_units=1)) == 1


def test_9_14_terrain_limit_is_caller_supplied():
    """RULE: 9.14, 9.31, 8.37."""
    stack = [unit("a", stacking_points=3), unit("b", stacking_points=3)]
    assert check_end_of_movement(stack).allowed
    result = check_end_of_movement(stack, HexContext(hex_id="H", limit=5))
    assert not result.allowed
    assert result.violations[0].case == "9.31"


def test_9_15_markers_aircraft_and_ground_support_do_not_stack():
    """RULE: 9.15."""
    for kind in ("informational", "air", "ground_support"):
        assert effective_points(unit(kind, kind=kind,
                                     stacking_points=3)) == 0


def test_9_16_garrison_and_aa_exceptions():
    """RULE: 9.16."""
    garrison = unit("g", kind="garrison", assigned_city="Tobruk")
    assert effective_points(garrison, HexContext(hex_id="Tobruk")) == 0
    assert effective_points(garrison, HexContext(hex_id="Bardia")) == 1

    aa = unit("aa", kind="aa")
    assert effective_points(aa, HexContext(major_city=True)) == 0
    assert points_in_hex([aa, unit("aa2", kind="aa"),
                          unit("c", stacking_points=2)],
                         HexContext(landing_strip=True)) == 3
    assert points_in_hex([aa, unit("aa2", kind="aa"),
                          unit("c", stacking_points=2)],
                         HexContext(airfield=True)) == 2

    zero = unit("zero", kind="aa", zero_plus_cpa=True)
    assert effective_points(zero) == 0
    assert effective_points(unit("zero", kind="aa", zero_plus_cpa=True,
                                 motorized=True)) == 1


def test_9_21_only_units_attached_to_parent_count():
    """RULE: 9.21."""
    attached = unit("a", parent_id="p1", attached_to_parent=True)
    detached = unit("b", parent_id="p1")
    other = unit("c", parent_id="p2", attached_to_parent=True)
    assert formation_units([attached, detached, other], "p1") == (attached,)


def test_9_22_level_lookup_needs_a_caller_table():
    """RULE: 9.22, 9.23."""
    assert level_for_points(3, {Fraction(3): "brigade"}) == "brigade"
    try:
        level_for_points(2, {Fraction(3): "brigade"})
    except StackingError:
        pass
    else:
        raise AssertionError("a missing §9.4 row must not be guessed")


def test_9_24_artillery_counts_one_stacking_point():
    """RULE: 9.24."""
    assert effective_points(unit("art", kind="artillery",
                                 stacking_points=2)) == 1
    assert effective_points(unit("art-hq", kind="artillery",
                                 stacking_points=2,
                                 artillery_hq=True)) == 2


def test_9_25_maximum_five_small_companies():
    """RULE: 9.25."""
    five = [unit(f"s{i}", kind="small") for i in range(5)]
    six = [unit(f"s{i}", kind="small") for i in range(6)]
    assert small_company_count(five) == 5
    assert check_end_of_movement(five).allowed
    result = check_end_of_movement(six)
    assert [v.case for v in result.violations] == ["9.25"]
    attached = [unit(f"a{i}", kind="small", attached_to_parent=True)
                for i in range(6)]
    assert check_end_of_movement(attached).allowed
    assert check_end_of_movement(six, HexContext(major_city=True)).allowed


def test_9_26_shell_thresholds():
    """RULE: 9.26."""
    assert Formation("division", max_components=4,
                     attached_components=2).is_shell()
    assert not Formation("division", max_components=4,
                         attached_components=3).is_shell()
    assert Formation("brigade", max_components=3,
                     attached_components=1).is_shell()
    assert not Formation("brigade", max_components=3,
                         attached_components=2).is_shell()
    assert Formation("battalion", max_toe_strength=6,
                     toe_strength=2).is_shell()
    assert not Formation("battalion", max_toe_strength=6,
                         toe_strength=3).is_shell()
    assert Formation("artillery", max_toe_strength=4,
                     toe_strength=Fraction(1, 2)).is_shell()
    assert not Formation("artillery", max_toe_strength=4,
                         toe_strength=1).is_shell()


def test_9_27_shells_do_not_satisfy_prerequisites():
    """RULE: 9.27."""
    division = Formation("division", max_components=2,
                         attached_components=1,
                         attached_non_shell_components=1)
    assert division.is_shell()
    assert not division.qualifies()


def test_9_28_shell_reduces_effective_level():
    """RULE: 9.28."""
    assert Formation("division", max_components=2,
                     attached_components=1).effective_level() == "brigade"
    assert Formation("brigade", max_components=2,
                     attached_components=0).effective_level() == "battalion"
    assert Formation("battalion", max_toe_strength=4,
                     toe_strength=1).effective_level() == "company"
    assert Formation("artillery", max_toe_strength=4,
                     toe_strength=Fraction(1, 2)).effective_level() == "battalion"
    assert Formation("division", max_components=2,
                     attached_components=2).effective_level() == "division"


def test_9_29_trucks_and_convoys():
    """RULE: 9.29."""
    attached = unit("t", kind="truck", stacking_points=2,
                    attached_to_parent=True)
    convoy = unit("c", kind="truck_convoy", stacking_points=3)
    assert effective_points(attached) == 0
    assert road_points([attached]) == 0
    assert effective_points(convoy) == 0
    assert road_points([convoy]) == 3
    assert effective_points(unit("t2", kind="truck", stacking_points=2)) == 2


def test_9_31_stacking_checked_only_when_movement_stops():
    """RULE: 9.31, 9.32."""
    stack = [unit("a", stacking_points=3), unit("b", stacking_points=3)]
    assert passage_allowed(stack, unit("c", stacking_points=3))
    assert not check_end_of_movement(stack, HexContext(limit=5)).allowed


def test_9_33_road_track_passage_limit():
    """RULE: 9.33."""
    existing = [unit("a", stacking_points=3)]
    moving = unit("b", stacking_points=3)
    violation = check_road_passage(existing, moving)
    assert violation is not None
    assert violation.case == "9.33"
    assert check_road_passage([unit("a", stacking_points=2)],
                              unit("b", stacking_points=2)) is None


def test_9_35_involuntary_retreat_uses_the_same_limit():
    """RULE: 9.35."""
    stack = [unit("a", stacking_points=3), unit("b", stacking_points=3)]
    result = check_end_of_movement(stack, HexContext(limit=5),
                                   involuntary_retreat=True)
    assert result.violations[0].case == "9.35"
    assert "stand" in result.violations[0].message


def test_formation_rejects_impossible_attachments():
    """RULE: 9.26-9.27."""
    try:
        Formation("division", max_components=2, attached_components=3)
    except StackingError:
        pass
    else:
        raise AssertionError("attached components may not exceed the maximum")
