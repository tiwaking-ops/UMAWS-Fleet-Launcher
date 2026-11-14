"""Integrated contract locks for §§8-10 and §29.

Every map id, terrain value, stacking value and weather row in this module is a
synthetic fixture.  The official TEC, map and R-04 weather tables are absent;
these tests fix only the interfaces between movement, stacking, ZOC and weather.
"""

from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cna.rules.sec08_movement import (  # noqa: E402
    MoveContext,
    MovingUnit,
    MovementError,
    TerrainCrossing,
    crossing,
    may_continue_moving,
    move_unit,
)
from cna.rules.sec09_stacking import (  # noqa: E402
    HexContext,
    StackingUnit,
    check_end_of_movement,
    check_road_passage,
    passage_allowed,
)
from cna.rules.sec10_zoc import (  # noqa: E402
    ForcedRetreat,
    ZocUnit,
    actual_barrage_strength,
    combat_targets,
    enemy_controlled_hexes,
    holding_off_plan,
    holding_off_required,
    may_move_zoc_to_zoc,
    must_attack,
    must_stop_after_entering,
    retreat_path_allowed,
    zoc_map,
)
from cna.rules.sec29_weather import (  # noqa: E402
    WeatherResult,
    effects_for,
    sandstorm_majority,
)

LINE = {
    "A": ("B", "C"),
    "B": ("A", "C"),
    "C": ("A", "B", "D"),
    "D": ("C",),
}


def neighbours(hex_id: str):
    return LINE.get(hex_id, ())


def adjacent(source: str, destination: str) -> bool:
    return destination in LINE.get(source, ())


def moving(unit_id: str = "u", **fields) -> MovingUnit:
    fields.setdefault("side", "Axis")
    fields.setdefault("base_cpa", 15)
    return MovingUnit(unit_id=unit_id, **fields)


def flat(cost: Fraction | int = 1):
    return lambda moving_unit, source, destination: Fraction(cost)


def stack(unit_id: str, points: Fraction | int = 3) -> StackingUnit:
    return StackingUnit(unit_id=unit_id, side="Axis", stacking_points=points)


def zoc(unit_id: str, position: str, side: str = "Axis", **fields) -> ZocUnit:
    fields.setdefault("stacking_points", 3)
    return ZocUnit(unit_id=unit_id, side=side, position=position, **fields)


def storm(weather: str, location: int):
    return effects_for(WeatherResult(
        season="summer",
        roll=11,
        weather=weather,
        location=location,
        provenance="synthetic-test: T-0210 weather fixture",
        status="synthetic",
    ))


def test_8_13_enemy_occupied_hex_is_never_entered() -> None:
    """RULE: 8.13."""
    context = MoveContext(
        cost=flat(),
        adjacent=adjacent,
        enemy_occupied=frozenset({"B"}),
    )
    with pytest.raises(MovementError, match="8.13"):
        move_unit(moving(), "A", ["B"], context)


def test_8_14_10_23_zoc_entry_stops_the_path() -> None:
    """RULE: 8.14, 10.23."""
    context = MoveContext(
        cost=flat(),
        adjacent=adjacent,
        enemy_zoc=frozenset({"B"}),
    )
    result = move_unit(moving(), "A", ["B", "C"], context)

    assert result.entered == ("B",)
    assert result.position == "B"
    assert result.remaining == ("C",)
    assert "10.23" in result.stopped
    assert must_stop_after_entering("B", {"B"})


def test_8_17_non_motorized_cap_but_motorized_unit_is_exempt() -> None:
    """RULE: 8.17."""
    context = MoveContext(cost=flat(4))
    with pytest.raises(MovementError, match="8.17"):
        move_unit(moving(base_cpa=10), "A", ["B", "C", "D", "E"], context)

    result = move_unit(
        moving(base_cpa=10, motorized=True, unit_class="tank"),
        "A", ["B", "C", "D", "E"], context,
    )
    assert result.total == 16


def test_8_23_continuation_needs_two_hexes_or_reserve() -> None:
    """RULE: 8.23."""
    walker = moving(base_cpa=8)
    assert may_continue_moving(walker, distance_to_enemy=2)
    assert not may_continue_moving(walker, distance_to_enemy=3)
    assert may_continue_moving(
        moving(base_cpa=8, in_reserve=True), distance_to_enemy=9)


def test_9_31_stop_limit_is_separate_from_9_33_road_passage() -> None:
    """RULE: 9.31, 9.32, 9.33."""
    existing = [stack("existing", 3)]
    moving_unit = stack("moving", 3)

    assert check_end_of_movement(
        (*existing, moving_unit), HexContext(hex_id="H", limit=10)).allowed
    stopped = check_end_of_movement(
        (*existing, moving_unit), HexContext(hex_id="H", limit=5))
    assert [violation.case for violation in stopped.violations] == ["9.31"]

    passage = check_road_passage(existing, moving_unit)
    assert passage is not None
    assert passage.case == "9.33"
    assert passage_allowed(existing, moving_unit, road_track=False)
    assert not passage_allowed(existing, moving_unit, road_track=True)
    assert passage_allowed(
        [stack("a", 2)], stack("b", 2), road_track=True)


def test_10_21_blocked_or_impassable_hexsides_receive_no_zoc() -> None:
    """RULE: 10.21."""
    enemy = zoc("enemy", "A")
    full = zoc_map([enemy], neighbours=neighbours)
    assert full["B"] == frozenset({"enemy"})

    blocked = zoc_map(
        [enemy], neighbours=neighbours,
        blocked_hexside=lambda source, destination: destination == "B",
    )
    assert "B" not in blocked
    assert "C" in blocked

    impassable = zoc_map(
        [enemy], neighbours=neighbours,
        can_enter=lambda unit, source, destination: destination != "C",
    )
    assert "B" in impassable
    assert "C" not in impassable


def test_10_24_zoc_to_zoc_refusal_and_advance_exception() -> None:
    """RULE: 10.24."""
    controlled = frozenset({"A", "B"})
    assert not may_move_zoc_to_zoc("A", "B", controlled)

    with pytest.raises(MovementError, match="10.24"):
        move_unit(
            moving(), "A", ["B"],
            MoveContext(cost=flat(), enemy_zoc=controlled),
        )

    result = move_unit(
        moving(), "A", ["B"],
        MoveContext(cost=flat(), enemy_zoc=controlled,
                    advance_allowed=frozenset({"B"})),
    )
    assert result.position == "B"


def test_10_26_friendly_combat_unit_negates_enemy_zoc() -> None:
    """RULE: 10.26."""
    enemy = zoc("enemy", "B")
    friendly = zoc("friendly", "C", side="Allied")
    controlled = enemy_controlled_hexes(
        [enemy, friendly], "Allied", neighbours=neighbours)

    assert controlled == frozenset({"A"})
    result = move_unit(
        moving(), "A", ["C"],
        MoveContext(cost=flat(), enemy_zoc=frozenset({"A", "B", "C"}),
                    friendly_combat=frozenset({"C"})),
    )
    assert result.position == "C"


def test_10_31_10_36_holding_off_and_forced_retreat() -> None:
    """RULE: 10.31, 10.33-10.36."""
    enemy = zoc("enemy", "B")
    friendly = zoc("friendly", "A", side="Allied")
    assert combat_targets(
        [enemy, friendly], "Allied", neighbours=neighbours) == frozenset({"B"})
    assert must_attack([enemy, friendly], "Allied", neighbours=neighbours)

    artillery = zoc("artillery", "B", kind="artillery", stacking_points=1)
    gun = zoc("gun", "B", kind="artillery", stacking_points=1, is_gun=True)
    small = zoc("small", "B", kind="antitank", stacking_points=Fraction(1, 2))
    enemies = {"B": (artillery, gun, small)}
    assert holding_off_required((artillery, gun, small)) == 1
    assert actual_barrage_strength(2, Fraction(1, 2)) == 11

    held = holding_off_plan({"B": 1}, enemies)
    assert held.held_off == ("B",)
    assert held.satisfied
    assault = holding_off_plan({"B": 0}, enemies)
    assert assault.must_assault == ("B",)
    assert not assault.satisfied

    forced = ForcedRetreat()
    assert (forced.hexes, forced.disorganization_points) == (3, 3)
    assert retreat_path_allowed(("A", "B", "C"), {"D"})
    assert not retreat_path_allowed(("A", "B", "C"), {"B"})


def test_29_44_29_45_sandstorm_cost_and_breakdown_shift() -> None:
    """RULE: 29.44, 29.45."""
    sand = storm("sandstorm", 3)
    assert sand.affected_sections == frozenset({"C"})
    assert sand.movement_cost_multiplier("C") == 2
    assert sand.movement_cost_multiplier("A") == 1

    result = move_unit(
        moving(base_cpa=20), "C1", ["C2"],
        MoveContext(cost=lambda unit, source, destination:
                    Fraction(2) * sand.movement_cost_multiplier("C")),
    )
    assert result.total == 4

    assert sandstorm_majority(5, 10)
    assert not sandstorm_majority(4, 10)
    assert sand.breakdown_column_shift("C", sandstorm_majority=True) == 1
    assert sand.breakdown_column_shift("C", sandstorm_majority=False) == 0

    truck = moving("truck", base_cpa=20, unit_class="truck", toe_points=3)
    moved = move_unit(
        truck, "C1", ["C2"],
        MoveContext(
            cost=lambda unit, source, destination:
                TerrainCrossing(cp=4, breakdown=4),
            weather="sandstorm",
            sandstorm_majority=True,
            breakdown_roll=33,
            breakdown_table=lambda roll, column: 10,
        ),
    )
    assert moved.breakdown is not None
    assert moved.breakdown.points == 4
    assert moved.breakdown.column == 11


def test_29_55_29_56_rain_closes_wadis_and_makes_roads_tracks() -> None:
    """RULE: 29.55, 29.56."""
    rain = storm("rainstorm", 4)
    assert rain.affected_sections == frozenset({"D"})
    assert not rain.wadi_crossing_allowed("D")
    assert rain.wadi_crossing_allowed("D", road=True)

    truck = moving("truck", base_cpa=20, unit_class="truck")
    blocked = crossing(
        truck, base_cp=2, terrain="wadi", hexside=True, rainstorm=True)
    road = crossing(
        truck, base_cp=2, terrain="wadi", hexside=True,
        road=True, rainstorm=True)
    assert blocked.prohibited
    assert not road.prohibited

    assert rain.road_uses_track_profile("D")
    assert not rain.road_uses_track_profile("C")
    track_profile = crossing(
        truck, base_cp=3, base_breakdown=2,
        track=rain.road_uses_track_profile("D"))
    normal_profile = crossing(
        truck, base_cp=3, base_breakdown=2,
        track=rain.road_uses_track_profile("C"))
    assert (track_profile.cp, track_profile.breakdown) == (1, 1)
    assert (normal_profile.cp, normal_profile.breakdown) == (3, 2)

    moved = move_unit(
        truck, "D1", ["D2"],
        MoveContext(cost=lambda unit, source, destination: track_profile),
    )
    assert moved.movement_cost == 1


def test_29_57_29_58_rain_gates_river_and_delta_movement() -> None:
    """RULE: 29.57, 29.58."""
    rain = storm("rainstorm", 4)
    assert not rain.river_crossing_allowed("D")
    assert rain.river_crossing_allowed("D", road_or_rail=True)
    assert not rain.delta_vehicle_allowed("D", in_delta=True)
    assert rain.delta_vehicle_allowed(
        "D", in_delta=True, on_road_or_rail=True)
    assert rain.delta_unit_must_remain("D", in_delta=True)
    assert not rain.delta_unit_must_remain(
        "D", in_delta=True, on_road_or_rail=True)

    truck = moving("truck", base_cpa=20, unit_class="truck")

    def gate(unit, source, destination):
        if destination == "R" and not rain.river_crossing_allowed("D"):
            return TerrainCrossing(
                cp=0, prohibited=True, reason="29.57: unbridged river")
        if (destination == "X" and unit.is_vehicle
                and not rain.delta_vehicle_allowed("D", in_delta=True)):
            return TerrainCrossing(
                cp=0, prohibited=True, reason="29.58: delta vehicle")
        if source == "X" and rain.delta_unit_must_remain("D", in_delta=True):
            return TerrainCrossing(
                cp=0, prohibited=True, reason="29.58: delta hold")
        return Fraction(1)

    context = MoveContext(cost=gate)
    with pytest.raises(MovementError, match="29.57"):
        move_unit(truck, "D1", ["R"], context)
    with pytest.raises(MovementError, match="29.58"):
        move_unit(truck, "D1", ["X"], context)
    with pytest.raises(MovementError, match="29.58"):
        move_unit(truck, "X", ["D1"], context)
