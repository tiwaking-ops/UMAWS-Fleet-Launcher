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
from cna.engine.loop import (StageScenario, apply_off_map_move,  # noqa: E402
                             build_decision, legal_off_map_moves,
                             legal_rail_moves, legal_rail_stacks,
                             play_operations_stage, stage_phases)
from cna.rules.sec08_transport import (ALEXANDRIA_LINE, AXIS,  # noqa: E402
                                       BENGHAZI_LINE, COMMONWEALTH, GABES,
                                       MAP_EXIT_HEX, RAIL_PHASE, TRIPOLI,
                                       TUNIS, OffMapChart, OffMapTransit,
                                       OffMapUnit,
                                       RAIL_STACK_LIMIT, RailLine,
                                       RailNetwork, RailUsage, SupplyLedger,
                                       TransportError, TruckCargo,
                                       advance_off_map, arrival_box_locked,
                                       in_transit_label, map_exit_allowed,
                                       off_map_box_properties,
                                       off_map_entry_allowed,
                                       off_map_entry_hexes,
                                       plan_off_map_move, plan_rail_move,
                                       plan_rail_supply_move,
                                       supply_dump_allowed,
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


OFF_MAP_CHART = OffMapChart(
    lambda origin, destination, cpa: 2
    if {origin, destination} == {TRIPOLI, TUNIS} else 1)


def off_map_scenario():
    return StageScenario(
        neighbours=lambda hex_id: (),
        cost=lambda moving, source, destination: Fraction(1),
        hex_limits={},
        off_map_chart=OFF_MAP_CHART,
        off_map_boxes=(TRIPOLI, TUNIS),
    )


def off_map_unit(position, **overrides):
    record = rail_unit(position, side=AXIS)
    record.update({"off_map_box": True, "base_cpa": 5,
                   "stacking_points": 1,
                   "reinforcement_or_replacement": False})
    record.update(overrides)
    return record


class OffMapPlayer:
    def choose(self, view, decision, legal, rng):
        move = next((action for action in legal
                     if action.id.startswith("offmap:")), None)
        if move is not None:
            return move
        return next(action for action in legal
                    if action.id == "end_segment")


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


def test_phase_j_groups_a_multi_unit_rail_stack_into_one_action():
    """RULE: 8.72, 8.74, 8.75."""
    state = rail_state(("cw-1", rail_unit("A", stacking_points=1)),
                       ("cw-2", rail_unit("A", stacking_points=1)))
    phase = rail_phase()
    decision = build_decision(state, phase, COMMONWEALTH, rail_scenario())
    action = next(action for action in decision.actions
                  if action.id == "rail:cw-1+cw-2:C")
    assert action.payload["unit_ids"] == ["cw-1", "cw-2"]

    after = apply(decision, state, action)
    assert after["units"]["cw-1"]["position"] == "C"
    assert after["units"]["cw-2"]["position"] == "C"
    assert after["units"]["cw-1"]["moved"] == "T1S1.III.B.J"
    assert after["units"]["cw-2"]["moved"] == "T1S1.III.B.J"
    assert after["rail_used"] == [[ALEXANDRIA_LINE, "east"]]
    assert after["actions_in_segment"] == 1

    again = build_decision(after, phase, COMMONWEALTH, rail_scenario())
    assert [action.id for action in again.actions] == ["end_segment"]


def test_phase_j_rail_stack_keeps_the_two_point_limit():
    """RULE: 8.75."""
    state = rail_state(("cw-1", rail_unit("A", stacking_points=1)),
                       ("cw-2", rail_unit("A", stacking_points=1)),
                       ("cw-3", rail_unit("A", stacking_points=1)))
    stacks = legal_rail_stacks(state, COMMONWEALTH, rail_scenario())
    assert all(stack.stacking_points <= RAIL_STACK_LIMIT for stack in stacks)
    offered = {stack.unit_ids for stack in stacks}
    assert ("cw-1", "cw-2", "cw-3") not in offered
    assert ("cw-1", "cw-2") in offered

    heavy = rail_state(("cw-1", rail_unit("A", stacking_points=2)),
                       ("cw-2", rail_unit("A", stacking_points=1)))
    heavy_stacks = legal_rail_stacks(heavy, COMMONWEALTH, rail_scenario())
    assert ("cw-1", "cw-2") not in {stack.unit_ids
                                     for stack in heavy_stacks}


def test_grouped_rail_stack_checks_destination_stacking():
    """RULE: 8.75, 8.77."""
    state = rail_state(("cw-1", rail_unit("A", stacking_points=1)),
                       ("cw-2", rail_unit("A", stacking_points=1)),
                       ("cw-3", rail_unit("C", stacking_points=5)))
    to_c = {stack.unit_ids for stack in legal_rail_stacks(
        state, COMMONWEALTH, rail_scenario())
        if stack.destination == "C"}
    assert to_c == {("cw-1",), ("cw-2",)}


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


# ---------------------------------------------------------------------------
# the Tripoli/Tunisia transit in the stage loop
# ---------------------------------------------------------------------------

def test_off_map_transit_advances_stage_by_stage_in_the_stage_loop():
    """RULE: 8.81-8.84, 8.89; phase G drives one box step per Stage."""
    state = rail_state(("ax-1", off_map_unit(TRIPOLI)))
    first = play_operations_stage(
        state, off_map_scenario(),
        players={"axis": OffMapPlayer(), "commonwealth": EndPlayer()},
        stage=1)
    record = first.state["units"]["ax-1"]
    assert record["position"] == in_transit_label(1)
    assert record["off_map_transit"]["origin"] == TRIPOLI
    assert record["off_map_transit"]["destination"] == TUNIS
    assert record["off_map_transit"]["stages"] == 2
    assert record["off_map_transit"]["elapsed"] == 1
    assert record["spent"] == "5"
    assert record["off_map_box"] is True
    assert first.moves == 1
    assert "breakdown_pending" not in record

    second = play_operations_stage(
        first.state, off_map_scenario(),
        players={"axis": OffMapPlayer(), "commonwealth": EndPlayer()},
        stage=2)
    record = second.state["units"]["ax-1"]
    assert record["position"] == TUNIS
    assert record["off_map_transit"]["arrived"] is True
    assert record["arrived_this_stage"] is True
    assert record["off_map_box"] is True
    assert second.moves == 1


def test_off_map_move_spends_exact_cpa_and_skips_breakdown():
    """RULE: 8.83."""
    state = rail_state(("ax-1", off_map_unit(
        TRIPOLI, base_cpa=7, motorized=True)))
    phase = next(phase for phase in stage_phases(1)
                 if phase.id.endswith(".A.G"))
    decision = build_decision(state, phase, AXIS, off_map_scenario())
    action = next(action for action in decision.actions
                  if action.id == "offmap:ax-1:tunis")
    after = apply(decision, state, action)
    record = after["units"]["ax-1"]
    assert record["spent"] == "7"
    assert record["fuel_required"] is True
    assert "breakdown_pending" not in record
    assert "breakdown_roll" not in record


def test_off_map_transit_can_turn_back():
    """RULE: 8.84."""
    state = rail_state(("ax-1", off_map_unit(TRIPOLI)))
    first = apply_off_map_move(state, AXIS, "ax-1", TUNIS,
                               off_map_scenario(), phase_key="k1")
    options = legal_off_map_moves(first, AXIS, off_map_scenario(),
                                  phase_key="k2")
    assert {(option.kind, option.destination) for option in options} == {
        ("continue", TUNIS), ("reverse", TRIPOLI)}
    after = apply_off_map_move(first, AXIS, "ax-1", TRIPOLI,
                               off_map_scenario(), phase_key="k2")
    record = after["units"]["ax-1"]
    assert record["position"] == TRIPOLI
    assert record["off_map_move"] == "reverse"
    assert record["off_map_transit"]["stages"] == 1


def test_off_map_land_transit_refuses_commonwealth_land():
    """RULE: 8.82."""
    state = rail_state(("cw-1", off_map_unit(
        TRIPOLI, side=COMMONWEALTH)))
    assert legal_off_map_moves(state, COMMONWEALTH, off_map_scenario(),
                               phase_key="k") == ()


def test_8_86_arrived_reinforcement_cannot_leave_its_box():
    """RULE: 8.86."""
    state = rail_state(("ax-1", off_map_unit(
        TUNIS, reinforcement_or_replacement=True)))
    state["units"]["ax-1"]["arrived_this_stage"] = True
    assert legal_off_map_moves(state, AXIS, off_map_scenario(),
                               phase_key="k") == ()


# ---------------------------------------------------------------------------
# supply cargo (8.72, 8.88)
# ---------------------------------------------------------------------------

def test_8_72_rail_carries_supplies_once_in_each_direction():
    """RULE: 8.72, 8.74."""
    ledger = SupplyLedger({"B": 4, "D": 1})
    east = plan_rail_supply_move(
        LINE, side=COMMONWEALTH, phase=RAIL_PHASE, supply_points=2,
        origin="B", destination="D")
    assert east.direction == "east"
    assert east.entered == ("C", "D")
    moved = ledger.rail_deliver(east)
    assert moved.dump_at("B") == 2
    assert moved.dump_at("D") == 3

    with pytest.raises(TransportError, match="8.74"):
        plan_rail_supply_move(
            LINE, side=COMMONWEALTH, phase=RAIL_PHASE, supply_points=1,
            origin="B", destination="C", usage=east.usage)
    west = plan_rail_supply_move(
        LINE, side=COMMONWEALTH, phase=RAIL_PHASE, supply_points=1,
        origin="D", destination="A", usage=east.usage)
    assert west.direction == "west"
    assert moved.rail_deliver(west).dump_at("A") == 1


def test_8_72_8_75_rail_supply_restrictions_and_stock():
    """RULE: 8.71-8.73, 8.75-8.78."""
    kwargs = {
        "side": COMMONWEALTH,
        "phase": RAIL_PHASE,
        "supply_points": 1,
        "origin": "A",
        "destination": "D",
    }
    with pytest.raises(TransportError, match="8.71"):
        plan_rail_supply_move(LINE, **{**kwargs, "side": AXIS})
    with pytest.raises(TransportError, match="8.72"):
        plan_rail_supply_move(LINE, **{**kwargs, "phase": "movement"})
    with pytest.raises(TransportError, match="8.73"):
        plan_rail_supply_move(LINE, **kwargs, enemy_zoc=("B",))
    with pytest.raises(TransportError, match="8.75"):
        plan_rail_supply_move(LINE, **{**kwargs,
                                       "supply_points": RAIL_STACK_LIMIT + 1})
    with pytest.raises(TransportError, match="8.78"):
        plan_rail_supply_move(LINE, **kwargs, axis_combat_hexes=("E",))
    blocked = RailLine(ALEXANDRIA_LINE, ("A", "B", "C", "D", "E"),
                       destroyed=frozenset({"C"}))
    with pytest.raises(TransportError, match="8.76"):
        plan_rail_supply_move(blocked, **kwargs)

    scarce = SupplyLedger({"A": 1})
    move = plan_rail_supply_move(
        LINE, side=COMMONWEALTH, phase=RAIL_PHASE, supply_points=2,
        origin="A", destination="B")
    with pytest.raises(TransportError, match="8.72"):
        scarce.rail_deliver(move)


def test_8_88_truck_cargo_dumps_and_the_stage_lock():
    """RULE: 8.87, 8.88, 8.95."""
    assert supply_dump_allowed(TRIPOLI) is True
    assert supply_dump_allowed(in_transit_label(1)) is False
    assert off_map_box_properties(TRIPOLI)["supplies"] == "unlimited"

    ledger = SupplyLedger(
        {TRIPOLI: 10, TUNIS: 0},
        {"truck-1": TruckCargo("truck-1", capacity=5)},
    )
    loaded = ledger.load("truck-1", TRIPOLI, 3, stage=1)
    assert loaded.dump_at(TRIPOLI) == 7
    assert loaded.truck("truck-1").load == 3
    assert loaded.truck("truck-1").may_move(stage=1) is False
    with pytest.raises(TransportError, match="8.88"):
        loaded.truck("truck-1").require_move(stage=1)
    assert loaded.truck("truck-1").may_move(stage=2) is True

    unloaded = loaded.unload("truck-1", TUNIS, 2, stage=2)
    assert unloaded.dump_at(TUNIS) == 2
    assert unloaded.truck("truck-1").load == 1
    assert unloaded.truck("truck-1").may_move(stage=2) is False
    assert unloaded.truck("truck-1").may_move(stage=3) is True

    with pytest.raises(TransportError, match="8.95"):
        loaded.load("truck-1", TRIPOLI, 3, stage=1)
    with pytest.raises(TransportError, match="8.72"):
        loaded.load("truck-1", TRIPOLI, 8, stage=1)
    with pytest.raises(TransportError, match="8.87"):
        loaded.load("truck-1", in_transit_label(1), 1, stage=1)
    with pytest.raises(TransportError, match="8.72"):
        unloaded.unload("truck-1", TUNIS, 2, stage=3)

    motorization = SupplyLedger(
        {TUNIS: 2},
        {"motorization-point-1": TruckCargo("motorization-point-1", 2)},
    ).load("motorization-point-1", TUNIS, 2, stage=4)
    assert motorization.truck(
        "motorization-point-1").may_move(stage=4) is False
    assert motorization.truck(
        "motorization-point-1").may_move(stage=5) is True
    with pytest.raises(TransportError, match="8.95"):
        TruckCargo("truck-2", capacity=1, load=2)
