"""Section 8 transport: rail movement and the Tripoli/Tunisia boxes.

Every line, box, distance-chart value and map edge used here is synthetic.
The printed rail map and the Off-Map Land Unit Movement Distance Chart are
R-04/R-05 data and remain caller-supplied.
"""

from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cna.engine import apply  # noqa: E402
from cna.engine.loop import (StageScenario, build_decision,  # noqa: E402
                             legal_rail_moves, play_operations_stage,
                             stage_phases)
from cna.rules.sec08_transport import (ALEXANDRIA_LINE, AXIS,  # noqa: E402
                                       BENGHAZI_LINE, COMMONWEALTH, GABES,
                                       MAP_EXIT_HEX, RAIL_PHASE, TUNIS,
                                       OffMapChart, OffMapTransit, OffMapUnit,
                                       RAIL_STACK_LIMIT, RailLine,
                                       RailNetwork, RailUsage, TransportError,
                                       advance_off_map, arrival_box_locked,
                                       in_transit_label, map_exit_allowed,
                                       off_map_box_properties,
                                       off_map_entry_allowed,
                                       off_map_entry_hexes,
                                       plan_off_map_move, plan_rail_move,
                                       supply_transfer_allows_movement)
from cna.state.model import new_state  # noqa: E402

LINE = RailLine(ALEXANDRIA_LINE, ("A", "B", "C", "D", "E"))
NETWORK = RailNetwork({ALEXANDRIA_LINE: LINE})


def rail_kwargs(**overrides):
    values = {
        "side": COMMONWEALTH,
        "phase": RAIL_PHASE,
        "started_on_rail": True,
        "cp_spent": 0,
        "in_enemy_zoc": False,
        "stacking_points": RAIL_STACK_LIMIT,
        "origin": "A",
        "destination": "C",
    }
    values.update(overrides)
    return values


def test_8_71_only_the_alexandria_line_is_active():
    """RULE: 8.71."""
    move = plan_rail_move(LINE, "cw-1", **rail_kwargs())
    assert move.line == ALEXANDRIA_LINE
    inactive = RailLine(BENGHAZI_LINE, ("A", "B"), active=False)
    with pytest.raises(TransportError, match="8.71"):
        plan_rail_move(inactive, "cw-1", **rail_kwargs())


def test_8_72_rail_is_commonwealth_only_in_the_rail_phase():
    """RULE: 8.72, 8.74."""
    move = plan_rail_move(LINE, "cw-1", **rail_kwargs())
    assert move.direction == "east"
    assert move.entered == ("B", "C")
    with pytest.raises(TransportError, match="8.71"):
        plan_rail_move(LINE, "ax-1", **rail_kwargs(side=AXIS))
    with pytest.raises(TransportError, match="8.72"):
        plan_rail_move(LINE, "cw-1", **rail_kwargs(phase="movement"))
    with pytest.raises(TransportError, match="8.74"):
        plan_rail_move(LINE, "cw-1", **rail_kwargs(
            usage=RailUsage({(ALEXANDRIA_LINE, "east")})))


def test_8_73_rail_start_cp_and_zoc_restrictions():
    """RULE: 8.73."""
    with pytest.raises(TransportError, match="8.73"):
        plan_rail_move(LINE, "cw-1", **rail_kwargs(started_on_rail=False))
    with pytest.raises(TransportError, match="8.73"):
        plan_rail_move(LINE, "cw-1", **rail_kwargs(cp_spent=1))
    with pytest.raises(TransportError, match="8.73"):
        plan_rail_move(LINE, "cw-1", **rail_kwargs(in_enemy_zoc=True))
    with pytest.raises(TransportError, match="8.73"):
        plan_rail_move(LINE, "cw-1", **rail_kwargs(enemy_zoc={"A"}))
    with pytest.raises(TransportError, match="8.73"):
        plan_rail_move(LINE, "cw-1", **rail_kwargs(enemy_zoc={"B"}))


def test_8_74_one_stack_in_each_direction():
    """RULE: 8.74."""
    cast = plan_rail_move(LINE, "cw-1", **rail_kwargs())
    west = plan_rail_move(LINE, "cw-2", **rail_kwargs(
        origin="C", destination="A", usage=cast.usage))
    assert cast.direction == "east" and west.direction == "west"
    assert west.usage.used_direction(ALEXANDRIA_LINE, "east")
    assert west.usage.used_direction(ALEXANDRIA_LINE, "west")


def test_8_75_rail_stack_limit_is_two():
    """RULE: 8.75."""
    with pytest.raises(TransportError, match="8.75"):
        plan_rail_move(LINE, "cw-1", **rail_kwargs(stacking_points=Fraction(3)))
    move = plan_rail_move(LINE, "cw-1", **rail_kwargs(stacking_points=2))
    assert move.stacking_points == RAIL_STACK_LIMIT


def test_8_76_destroyed_and_unconstructed_rail_hexes():
    """RULE: 8.76."""
    destroyed = RailLine(ALEXANDRIA_LINE, LINE.hexes,
                         destroyed=frozenset({"B"}))
    with pytest.raises(TransportError, match="8.76"):
        plan_rail_move(destroyed, "cw-1", **rail_kwargs(destination="D"))
    unconstructed = RailLine(ALEXANDRIA_LINE, LINE.hexes,
                             unconstructed=frozenset({"B"}))
    with pytest.raises(TransportError, match="8.76"):
        plan_rail_move(unconstructed, "cw-1", **rail_kwargs(destination="D"))


def test_8_77_pick_up_and_drop_off_stops():
    """RULE: 8.77."""
    move = plan_rail_move(LINE, "cw-1", **rail_kwargs(
        destination="E", stops=("B", "D")))
    assert move.stops == ("B", "D")
    with pytest.raises(TransportError, match="8.77"):
        plan_rail_move(LINE, "cw-1", **rail_kwargs(destination="E",
                                                   stops=("Z",)))


def test_8_78_axis_rail_cutoff_and_enemy_occupation():
    """RULE: 8.78."""
    with pytest.raises(TransportError, match="8.78"):
        plan_rail_move(LINE, "cw-1", **rail_kwargs(
            destination="B", axis_combat_hexes={"C"}))
    east_of_axis = plan_rail_move(
        LINE, "cw-1", **rail_kwargs(origin="D", destination="E",
                                    axis_combat_hexes={"C"}))
    assert east_of_axis.entered == ("E",)
    with pytest.raises(TransportError, match="8.73"):
        plan_rail_move(LINE, "cw-1", **rail_kwargs(
            destination="B", enemy_occupied={"B"}))


def test_8_81_tripoli_tunisia_boxes_and_in_transit():
    """RULE: 8.81."""
    chart = OffMapChart(lambda origin, destination, cpa: 3)
    transit = plan_off_map_move("tripoli", "tunis", cpa=10, chart=chart)
    assert transit.position == "tripoli"
    assert transit.advance().position == in_transit_label(1)
    assert in_transit_label(2).startswith("in_transit:")


def test_8_82_only_axis_and_commonwealth_air_enter():
    """RULE: 8.82."""
    assert off_map_entry_allowed(OffMapUnit(AXIS, "land"))
    assert off_map_entry_allowed(OffMapUnit(AXIS, "sea"))
    assert off_map_entry_allowed(OffMapUnit(COMMONWEALTH, "air"))
    assert not off_map_entry_allowed(OffMapUnit(COMMONWEALTH, "land"))
    assert not off_map_entry_allowed(OffMapUnit(COMMONWEALTH, "sea"))
    chart = OffMapChart(lambda origin, destination, cpa: 1)
    with pytest.raises(TransportError, match="8.82"):
        plan_off_map_move("tripoli", "tunis", cpa=10, chart=chart,
                          unit=OffMapUnit(COMMONWEALTH, "land"))
    with pytest.raises(TransportError, match="8.83"):
        plan_off_map_move("tripoli", "tunis", cpa=10, chart=chart,
                          unit=OffMapUnit(COMMONWEALTH, "air"))


def test_8_83_off_map_cp_fuel_and_no_breakdown():
    """RULE: 8.83."""
    transit = OffMapTransit("tripoli", "tunis", 2)
    with pytest.raises(TransportError, match="8.83"):
        advance_off_map(transit, cp_spent=5, cpa=6, motorized=True)
    result = advance_off_map(transit, cp_spent=6, cpa=6, motorized=True)
    assert result.cp_spent == 6
    assert result.fuel_required is True
    assert result.breakdown_check is False
    assert result.transit.position == in_transit_label(1)


def test_8_84_transit_chart_and_reversal():
    """RULE: 8.84, 8.89."""
    seen = []

    def stages(origin, destination, cpa):
        seen.append((origin, destination, cpa))
        return 3

    chart = OffMapChart(stages)
    transit = plan_off_map_move("tripoli", "tunis", cpa=10, chart=chart)
    assert seen == [("tripoli", "tunis", 10)]
    assert transit.stages == 3
    moving = advance_off_map(transit, cp_spent=10, cpa=10).transit
    turned = moving.reverse()
    assert turned.position == in_transit_label(1)
    assert turned.stages == 1
    arrived = advance_off_map(turned, cp_spent=10, cpa=10).transit
    assert arrived.position == "tripoli"
    with pytest.raises(TransportError, match="8.84"):
        advance_off_map(arrived, cp_spent=10, cpa=10)
    with pytest.raises(TransportError, match="stages"):
        OffMapChart(lambda origin, destination, cpa: 0).stages_between(
            "tripoli", "tunis", 10)


def test_8_85_map_exit_and_road_entry_allocation():
    """RULE: 8.85."""
    assert map_exit_allowed(MAP_EXIT_HEX)
    assert not map_exit_allowed("A2803")
    assert off_map_entry_hexes(("A2802", "A2803", "A2804"), 13) == (
        ("A2802", Fraction(5)),
        ("A2803", Fraction(5)),
        ("A2804", Fraction(3)),
    )
    assert off_map_entry_hexes(("A2802",), 5) == (
        ("A2802", Fraction(5)),
    )
    with pytest.raises(TransportError, match="8.85"):
        off_map_entry_hexes(("A2802",), 6)


def test_8_86_arrival_box_locks_reinforcements():
    """RULE: 8.86."""
    assert arrival_box_locked("tripoli", arrived_this_stage=True,
                              reinforcement_or_replacement=True)
    assert arrival_box_locked("tunis", arrived_this_stage=True,
                              reinforcement_or_replacement=True)
    assert not arrival_box_locked(GABES, arrived_this_stage=True,
                                  reinforcement_or_replacement=True)
    assert not arrival_box_locked("tripoli", arrived_this_stage=False,
                                  reinforcement_or_replacement=True)


def test_8_87_88_off_map_stacking_water_and_supply():
    """RULE: 8.87, 8.88."""
    props = off_map_box_properties("tripoli")
    assert props["stacking_limit"] is None
    assert props["water"] == "unlimited"
    assert props["air_facilities"] is True
    assert props["supplies"] == "unlimited"
    assert props["maintenance_crews"] is True
    transit = off_map_box_properties(in_transit_label(1))
    assert transit["stacking_limit"] is None
    assert transit["water"] == "unlimited"
    assert transit["air_facilities"] is False
    assert supply_transfer_allows_movement(
        loads_or_unloads_this_stage=False) is True
    assert supply_transfer_allows_movement(
        loads_or_unloads_this_stage=True) is False


# ---------------------------------------------------------------------------
# the Commonwealth Rail Movement phase in the stage loop
# ---------------------------------------------------------------------------

RAIL_GRAPH = {
    "A": ("B",), "B": ("A", "C"), "C": ("B", "D"),
    "D": ("C", "E"), "E": ("D",),
}


def rail_unit(position, **overrides):
    record = {
        "side": COMMONWEALTH,
        "position": position,
        "base_cpa": 10,
        "unit_class": "infantry",
        "kind": "combat",
        "move_kind": "combat",
        "stacking_points": 2,
        "cohesion": 0,
        "raw_defensive_close_assault": 10,
    }
    record.update(overrides)
    return record


def rail_scenario():
    return StageScenario(
        neighbours=lambda hex_id: RAIL_GRAPH.get(hex_id, ()),
        cost=lambda moving, source, destination: Fraction(1),
        hex_limits={hex_id: Fraction(6) for hex_id in RAIL_GRAPH},
        rail=NETWORK,
    )


def rail_state(*units):
    state = new_state(7, stage=1)
    state["units"] = {unit_id: record for unit_id, record in units}
    return state


def rail_phase():
    return next(phase for phase in stage_phases(1)
                if phase.id.endswith(".B.J"))


def test_the_rail_phase_offers_and_applies_one_rail_move():
    """RULE: 8.72-8.75; phase J is wired to the transport module."""
    state = rail_state(("cw-1", rail_unit("A")))
    phase = rail_phase()
    decision = build_decision(state, phase, COMMONWEALTH, rail_scenario())
    action = next(action for action in decision.actions
                  if action.id == "rail:cw-1:C")
    after = apply(decision, state, action)
    assert after["units"]["cw-1"]["position"] == "C"
    assert after["units"]["cw-1"]["moved"] == "T1S1.III.B.J"
    assert after["rail_used"] == [[ALEXANDRIA_LINE, "east"]]
    assert after["units"]["cw-1"]["spent"] == "0"
    again = build_decision(after, phase, COMMONWEALTH, rail_scenario())
    assert [action.id for action in again.actions] == ["end_segment"]


def test_rail_usage_restricts_the_opposite_direction():
    """RULE: 8.74."""
    state = rail_state(("cw-1", rail_unit("C")))
    state["rail_used"] = [[ALEXANDRIA_LINE, "east"]]
    destinations = {move.destination for move in legal_rail_moves(
        state, COMMONWEALTH, rail_scenario())}
    assert destinations == {"A", "B"}


def test_rail_destination_stacking_is_checked():
    """RULE: 8.75, 8.77."""
    state = rail_state(("cw-1", rail_unit("A")),
                       ("cw-2", rail_unit("C", stacking_points=6)))
    offered = {(move.unit_id, move.destination) for move in legal_rail_moves(
        state, COMMONWEALTH, rail_scenario())}
    assert ("cw-1", "C") not in offered
    assert ("cw-1", "B") in offered


class EndPlayer:
    def choose(self, view, decision, legal, rng):
        return next(action for action in legal
                    if action.id == "end_segment")


def test_rail_budget_resets_for_each_operations_stage():
    """RULE: 8.74."""
    state = rail_state(("cw-1", rail_unit("A")))
    state["rail_used"] = [[ALEXANDRIA_LINE, "east"]]
    result = play_operations_stage(
        state, rail_scenario(),
        players={"axis": EndPlayer(), "commonwealth": EndPlayer()},
        stage=2)
    assert result.state["rail_used"] == []
