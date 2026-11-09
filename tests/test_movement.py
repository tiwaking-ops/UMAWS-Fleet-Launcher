"""Movement tests, one named case per test (RULE: 8.11-8.98).

Costs and map adjacency are synthetic callables; no TEC values are invented.
"""

import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cna.rules.sec08_movement import (
    CONTACT_BREAK_OFF_CP,
    ENGAGED_BREAK_OFF_CP,
    TEC,
    HexsideRow,
    MoveContext,
    MovingUnit,
    MovementError,
    TECError,
    TerrainCrossing,
    TerrainRow,
    break_off_clears,
    break_off_cost,
    contact_state,
    crossing,
    marker_applies,
    may_continue_moving,
    move_unit,
    reaction_allowed,
    reaction_step_allowed,
)


def unit(unit_id="u", **kwargs):
    kwargs.setdefault("side", "Axis")
    kwargs.setdefault("base_cpa", 15)
    return MovingUnit(unit_id=unit_id, **kwargs)


def flat(cost=1):
    return lambda moving, source, destination: Fraction(cost)


LINE = {"A": ("B",), "B": ("A", "C"), "C": ("B", "D"), "D": ("C", "E"),
        "E": ("D",)}


def adjacent(source, destination):
    return destination in LINE.get(source, ())


def raises(error_type, call):
    try:
        call()
    except error_type as error:
        return error
    raise AssertionError(f"expected {error_type.__name__}")


def test_8_13_moves_are_consecutive_and_never_into_an_enemy():
    """RULE: 8.13."""
    context = MoveContext(cost=flat(), adjacent=adjacent)
    error = raises(MovementError, lambda: move_unit(unit(), "A", ["C"], context))
    assert "8.13" in str(error)
    occupied = MoveContext(cost=flat(), enemy_occupied=frozenset({"B"}))
    error = raises(MovementError,
                   lambda: move_unit(unit(), "A", ["B"], occupied))
    assert "8.13" in str(error)


def test_8_14_movement_stops_on_entering_an_enemy_zoc():
    """RULE: 8.14, 10.23."""
    context = MoveContext(cost=flat(), enemy_zoc=frozenset({"B"}))
    result = move_unit(unit(), "A", ["B", "C"], context)
    assert result.entered == ("B",)
    assert result.position == "B"
    assert "10.23" in result.stopped
    assert result.remaining == ("C",)


def test_8_15_break_off_costs_two_or_four_cp():
    """RULE: 8.15, 8.24, 8.64-8.66."""
    assert break_off_cost(unit(contact=True)) == CONTACT_BREAK_OFF_CP == 2
    assert break_off_cost(unit(engaged=True)) == ENGAGED_BREAK_OFF_CP == 4
    assert break_off_cost(unit(contact=True), phase="reaction") == 0
    result = move_unit(unit(contact=True), "A", ["B"],
                       MoveContext(cost=flat()))
    assert result.break_off == 2
    assert result.total == 3


def test_8_16_a_unit_may_exceed_its_cpa():
    """RULE: 8.16."""
    result = move_unit(unit(base_cpa=10, motorized=True, unit_class="tank"),
                       "A", ["B", "C", "D"], MoveContext(cost=flat(4)))
    assert result.total == 12
    assert result.total > 10


def test_8_17_non_motorized_voluntary_cap_is_fifty_percent():
    """RULE: 8.17."""
    walker = unit(base_cpa=8)
    result = move_unit(walker, "A", ["B", "C", "D"],
                       MoveContext(cost=flat(4)))
    assert result.voluntary_spent == 12
    error = raises(MovementError, lambda: move_unit(
        walker, "A", ["B", "C", "D", "E"], MoveContext(cost=flat(4))))
    assert "8.17" in str(error)
    error = raises(MovementError, lambda: move_unit(
        unit(base_cpa=10), "A", ["B", "C", "D", "E"],
        MoveContext(cost=flat(4))))
    assert "8.17" in str(error)


def test_8_18_truck_convoys_move_only_in_their_own_phase():
    """RULE: 8.18, 8.98."""
    convoy = unit(kind="truck_convoy", base_cpa=10)
    error = raises(MovementError, lambda: move_unit(
        convoy, "A", ["B"], MoveContext(cost=flat())))
    assert "8.18" in str(error)
    error = raises(MovementError, lambda: move_unit(
        unit(), "A", ["B"], MoveContext(cost=flat(), phase="truck_convoy")))
    assert "8.18" in str(error)
    result = move_unit(convoy, "A", ["B"],
                       MoveContext(cost=flat(), phase="truck_convoy"))
    assert result.total == 1


def test_8_21_and_8_22_repeated_movement_accumulates_cp():
    """RULE: 8.21, 8.22."""
    first = move_unit(unit(base_cpa=10, motorized=True, unit_class="tank"),
                      "A", ["B"], MoveContext(cost=flat(3)))
    assert first.total == 3
    second = move_unit(
        unit(base_cpa=10, motorized=True, unit_class="tank",
             voluntary_spent=first.voluntary_spent),
        "B", ["C"], MoveContext(cost=flat(3)))
    assert second.voluntary_spent == 6


def test_8_23_continue_only_within_two_hexes_or_in_reserve():
    """RULE: 8.23."""
    walker = unit(base_cpa=8)
    assert may_continue_moving(walker, distance_to_enemy=2)
    assert not may_continue_moving(walker, distance_to_enemy=3)
    assert may_continue_moving(walker, distance_to_enemy=9, reserve=True)


def test_8_26_collapsed_units_may_not_move():
    """RULE: 6.26, 8.17."""
    error = raises(MovementError, lambda: move_unit(
        unit(cohesion=-26), "A", ["B"], MoveContext(cost=flat())))
    assert "6.26" in str(error)


def test_8_31_and_8_32_prohibited_terrain_is_reported():
    """RULE: 8.31, 8.32."""
    error = raises(MovementError, lambda: move_unit(
        unit(), "A", ["B"],
        MoveContext(cost=lambda moving, source, destination: None)))
    assert "8.31/8.32" in str(error)


def test_8_33_road_benefit_comes_from_the_caller():
    """RULE: 8.33."""
    context = MoveContext(
        cost=lambda moving, source, destination: (
            Fraction(1) if destination == "B" else Fraction(3)))
    assert move_unit(unit(), "A", ["B"], context).movement_cost == 1
    assert move_unit(unit(), "A", ["C"], context).movement_cost == 3


def test_8_41_wadi_crossings():
    """RULE: 8.41."""
    vehicle = unit(unit_class="tank")
    off = crossing(vehicle, base_cp=4, terrain="wadi", hexside=True)
    assert (off.cp, off.breakdown) == (4, 8)
    track = crossing(vehicle, base_cp=4, terrain="wadi", hexside=True,
                     track=True)
    assert (track.cp, track.breakdown) == (2, 4)
    road = crossing(vehicle, base_cp=4, terrain="wadi", hexside=True,
                    road=True)
    assert road.breakdown == 2
    rain = crossing(vehicle, base_cp=4, terrain="wadi", hexside=True,
                    road=True, rainstorm=True)
    assert (rain.cp, rain.prohibited) == (6, False)
    blocked = crossing(vehicle, base_cp=4, terrain="wadi", hexside=True,
                       track=True, rainstorm=True)
    assert blocked.prohibited
    assert crossing(unit(), base_cp=4, terrain="wadi",
                    hexside=True).breakdown == 0


def test_8_42_escarpments_stop_vehicles_going_up():
    """RULE: 8.42."""
    vehicle = unit(unit_class="tank")
    assert crossing(vehicle, base_cp=2, terrain="escarpment",
                    direction="up").prohibited
    down = crossing(vehicle, base_cp=2, terrain="escarpment", track=True,
                    direction="down")
    assert (down.cp, down.breakdown) == (10, 6)
    assert not crossing(unit(), base_cp=2, terrain="escarpment",
                        direction="up").prohibited


def test_8_44_salt_marsh_abandons_prohibited_vehicles():
    """RULE: 8.44."""
    tank = unit(unit_class="tank")
    result = crossing(tank, base_cp=2, terrain="salt_marsh")
    assert result.prohibited and result.abandoned
    assert not crossing(tank, base_cp=2, terrain="salt_marsh",
                        road=True).prohibited
    assert not crossing(unit(unit_class="light_truck"), base_cp=2,
                        terrain="salt_marsh").prohibited


def test_8_45_desert_exclusions_apply_even_on_tracks():
    """RULE: 8.45."""
    assert crossing(unit(unit_class="light_truck"), base_cp=2,
                    terrain="desert", track=True).prohibited
    assert not crossing(unit(), base_cp=2, terrain="desert",
                        track=True).prohibited


def test_8_46_tracks_are_one_cp_and_halve_hexside_costs():
    """RULE: 8.46."""
    on_track = crossing(unit(), base_cp=4, base_breakdown=2, track=True)
    assert (on_track.cp, on_track.breakdown) == (1, 1)
    side = crossing(unit(), base_cp=4, base_breakdown=2, track=True,
                    hexside=True)
    assert (side.cp, side.breakdown) == (2, 1)


def test_8_47_unconstructed_road_is_a_track():
    """RULE: 8.47."""
    assert crossing(unit(), base_cp=4, unconstructed_road=True).cp == 1


def test_8_51_to_8_55_reaction_exceptions_and_size_pinning():
    """RULE: 8.51-8.55."""
    mobile = unit(motorized=True, base_cpa=15)
    enemy = unit("e", motorized=True, base_cpa=15)
    assert reaction_allowed(mobile, enemy, close_assault_announced=False,
                            in_enemy_zoc=False, in_combat=False) == (True, "")
    assert reaction_allowed(unit(base_cpa=8), enemy,
                            close_assault_announced=False,
                            in_enemy_zoc=False, in_combat=False) == (False, "8.53a")
    assert reaction_allowed(mobile, enemy, close_assault_announced=False,
                            in_enemy_zoc=True, in_combat=False) == (False, "8.53c")
    assert reaction_allowed(mobile, enemy, close_assault_announced=False,
                            in_enemy_zoc=False, in_combat=True) == (False, "8.53d")
    strong = unit("s", motorized=True, base_cpa=21)
    assert reaction_allowed(mobile, strong, close_assault_announced=True,
                            in_enemy_zoc=False, in_combat=False) == (False, "8.53b")
    division = unit("d", motorized=True, base_cpa=15, size_level="division")
    battalion = unit("b", motorized=True, base_cpa=21, size_level="battalion")
    assert reaction_allowed(division, battalion, close_assault_announced=True,
                            in_enemy_zoc=False, in_combat=False) == (True, "")
    assert not reaction_step_allowed("B", {"B"})


def test_8_61_to_8_68_contact_engaged_and_markers():
    """RULE: 8.61-8.68."""
    state = contact_state(in_enemy_zoc_at_segment_start=True)
    assert state.contact and not state.engaged
    engaged = contact_state(in_enemy_zoc_at_segment_start=False,
                            engaged_result=True)
    assert engaged.engaged and not engaged.contact
    assert break_off_clears(0)
    assert not break_off_clears(1)
    assert marker_applies(True)
    assert not marker_applies(False)


def test_8_91_and_8_92_motorized_cpa():
    """RULE: 8.91, 8.92."""
    motorized = unit(motorized=True, transport_cpa=20)
    assert motorized.cpa == 20
    assert not motorized.non_motorized
    assert unit(base_cpa=8).non_motorized


def test_8_98_truck_convoys_may_not_exceed_their_cpa():
    """RULE: 8.98."""
    convoy = unit(kind="truck_convoy", base_cpa=10)
    context = MoveContext(cost=flat(5), phase="truck_convoy")
    assert move_unit(convoy, "A", ["B", "C"], context).total == 10
    error = raises(MovementError, lambda: move_unit(
        convoy, "A", ["B", "C", "D"], context))
    assert "8.98" in str(error)


# ---------------------------------------------------------------------------
# the Terrain Effects Chart (8.31-8.37)
# ---------------------------------------------------------------------------

def chart():
    """A synthetic TEC; no value is historical (R-04 remains open)."""
    return TEC(
        terrain={
            "clear": TerrainRow(cp={"default": 1, "truck": 2},
                                breakdown=Fraction(1, 2),
                                stacking_limit=6),
            "rough": TerrainRow(cp=2, breakdown=1),
            "desert": TerrainRow(cp=1, breakdown=1,
                                 prohibited=frozenset({"light_truck"})),
            "salt_marsh": TerrainRow(cp=1, breakdown=1),
        },
        hexsides={
            "ridge": HexsideRow(cp=1, breakdown=1),
            "slope": HexsideRow(cp=1, breakdown=1),
            "escarpment": HexsideRow(cp=2, breakdown=0),
            "wadi": HexsideRow(cp=2, breakdown=0),
        },
        road_cp={"default": 1, "truck": Fraction(1, 2)},
        road_breakdown=Fraction(1, 2),
    )


def test_8_31_tec_entry_cost_uses_the_unit_class_column():
    """RULE: 8.31."""
    tec = chart()
    assert tec.enter(unit(), "clear").cp == 1
    assert tec.enter(unit(unit_class="truck"), "clear").cp == 2
    assert tec.enter(unit(), "rough").cp == 2
    context = MoveContext(
        cost=lambda moving, source, destination: tec.enter(moving, "clear"))
    assert move_unit(unit(), "A", ["B"], context).movement_cost == 1


def test_8_32_tec_prohibits_terrain_and_hexsides():
    """RULE: 8.32."""
    tec = chart()
    error = raises(MovementError, lambda: move_unit(
        unit(unit_class="light_truck"), "A", ["B"],
        MoveContext(cost=lambda moving, source, destination:
                    tec.enter(moving, "desert"))))
    assert "8.32" in str(error)
    assert tec.enter(unit(unit_class="tank"), "clear",
                     hexside="escarpment", direction="up").prohibited


def test_8_33_road_and_track_ignore_other_terrain():
    """RULE: 8.33, 8.46, 8.47."""
    tec = chart()
    truck = unit(unit_class="truck")
    road = tec.enter(truck, "rough", road=True)
    assert (road.cp, road.breakdown) == (Fraction(1, 2), Fraction(1, 2))
    track = tec.enter(truck, "rough", track=True)
    assert (track.cp, track.breakdown) == (1, Fraction(1, 2))
    unconstructed = tec.enter(truck, "rough", unconstructed_road=True)
    assert (unconstructed.cp, unconstructed.breakdown) == (
        1, Fraction(1, 2))
    wadi_road = tec.enter(truck, "clear", hexside="wadi", road=True)
    assert wadi_road.cp == Fraction(1, 2)


def test_8_35_tec_slopes_ridges_and_escarpments():
    """RULE: 8.35, 8.42-8.43."""
    tec = chart()
    ridge = tec.enter(unit(), "clear", hexside="ridge")
    assert (ridge.cp, ridge.breakdown) == (2, Fraction(3, 2))
    slope = tec.enter(unit(), "clear", hexside="slope")
    assert (slope.cp, slope.breakdown) == (2, Fraction(3, 2))
    tank = unit(unit_class="tank")
    assert tec.enter(tank, "clear", hexside="escarpment",
                     direction="up").prohibited
    down = tec.enter(tank, "clear", hexside="escarpment", track=True,
                     direction="down")
    assert (down.cp, down.breakdown) == (10, 6)


def test_8_37_tec_stacking_limit_and_missing_rows():
    """RULE: 8.37."""
    tec = chart()
    assert tec.stacking_limit("clear") == 6
    raises(TECError, lambda: tec.enter(unit(), "unknown"))
    raises(TECError, lambda: tec.enter(unit(), "clear", hexside="unknown"))


# ---------------------------------------------------------------------------
# Breakdown checks inside movement (21.21-21.27, 21.37)
# ---------------------------------------------------------------------------

def breakdown_context(**kwargs):
    return MoveContext(
        cost=lambda moving, source, destination: TerrainCrossing(
            cp=1, breakdown=1),
        adjacent=adjacent, **kwargs)


def truck(**kwargs):
    return unit(unit_id="truck", unit_class="truck", motorized=True,
                base_cpa=10, breakdown_bar=0, toe_points=3, **kwargs)


def test_21_21_24_breakdown_points_accumulate_during_movement():
    """RULE: 21.21, 21.24, 21.25, 21.27, 21.34-21.35."""
    context = breakdown_context(breakdown_roll=33,
                                breakdown_table=lambda roll, column: 10)
    result = move_unit(truck(), "A", ["B", "C", "D", "E"], context)
    check = result.breakdown
    assert check is not None
    assert check.points == 4
    assert check.column == 4
    assert check.required and check.resolved
    assert check.percent == 10 and check.losses == 1
    assert check.last_column == 4


def test_21_26_breakdown_rechecks_only_in_a_higher_column():
    """RULE: 21.26."""
    context = breakdown_context(breakdown_roll=33,
                                breakdown_table=lambda roll, column: 10)
    first = move_unit(truck(), "A", ["B", "C", "D", "E"], context)
    same = move_unit(
        truck(breakdown_points=first.breakdown.points,
              breakdown_last_column=first.breakdown.last_column),
        "E", ["D"], context)
    assert same.breakdown.points == 5
    assert not same.breakdown.required
    higher = move_unit(
        truck(breakdown_points=10, breakdown_last_column=4),
        "E", ["D"], context)
    assert higher.breakdown.points == 11
    assert higher.breakdown.required
    assert higher.breakdown.column == 11


def test_21_15_off_map_boxes_do_not_check():
    """RULE: 21.15."""
    result = move_unit(truck(off_map_box=True), "A",
                       ["B", "C", "D", "E"], breakdown_context())
    assert result.breakdown.suppressed
    assert not result.breakdown.required


def test_21_11_infantry_is_not_subject_to_breakdown():
    """RULE: 21.11."""
    context = breakdown_context()
    assert move_unit(unit(), "A", ["B"], context).breakdown is None


def test_21_37_rainstorm_road_breakdown_is_halved():
    """RULE: 21.37c."""
    road = crossing(unit(unit_class="truck"), base_cp=1, base_breakdown=2,
                    road=True, rainstorm=True)
    assert road.breakdown == 1
