"""The Operations Stage loop: §§5.2, 8, 9 and 10 played end to end.

Every fixture is synthetic: a caller-supplied line or triangle, flat costs
and explicit stacking limits.  No TEC value, map hex or historical counter
is used (R-04/R-05 remain open).
"""

from __future__ import annotations

import copy
import random
import sys
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cna.ai.player import RandomLegalPlayer  # noqa: E402
from cna.engine import apply, legal_actions  # noqa: E402
from cna.engine.loop import (StageError, StageScenario, apply_assault,  # noqa: E402
                             apply_move, build_decision, controlled_hexes,
                             legal_moves, play_operations_stage,
                             resolve_pending_breakdowns,
                             resolve_pending_combat, stage_phases)
from cna.rules.sec08_movement import TEC, TerrainRow  # noqa: E402
from cna.rules.sec11_combat import AssaultRoll  # noqa: E402
from cna.state.model import new_state, state_hash  # noqa: E402

LINE = {"A": ("B",), "B": ("A", "C"), "C": ("B", "D"),
        "D": ("C", "E"), "E": ("D",)}

TRIANGLE = {"A": ("B", "C"), "B": ("A", "C"), "C": ("A", "B")}


def scenario(hexes=None, *, limits=None, road_track=None,
             player_a="axis", player_b="commonwealth",
             assault_table=None):
    graph = LINE if hexes is None else hexes
    return StageScenario(
        neighbours=lambda hex_id: graph.get(hex_id, ()),
        cost=lambda moving, source, destination: Fraction(1),
        hex_limits=({hex_id: Fraction(6) for hex_id in graph}
                    if limits is None else limits),
        road_track=road_track,
        player_a=player_a,
        player_b=player_b,
        assault_table=assault_table,
    )


def unit(side, position, **kwargs):
    record = {"side": side, "position": position, "base_cpa": 12,
              "unit_class": "infantry", "kind": "combat",
              "move_kind": "combat", "stacking_points": 3, "cohesion": 0,
              "raw_defensive_close_assault": 10}
    record.update(kwargs)
    return record


def state_with(*units, seed=7, stage=1):
    state = new_state(seed, stage=stage)
    state["units"] = {unit_id: record for unit_id, record in units}
    return state


def combatant(side, position, **kwargs):
    record = unit(side, position, toe_strength=10,
                  offensive_close_assault=5,
                  defensive_close_assault=5)
    record.update(kwargs)
    return record


def synthetic_assault_table(role, differential, roll):
    """A labelled synthetic Close Assault CRT; not an R-04 value."""
    assert role in ("attacker", "defender")
    return AssaultRoll(roll=roll,
                       loss_percent=10 if role == "attacker" else 20)


class EndPlayer:
    """Always ends the phase; used to prove the phase walk itself."""

    def choose(self, view, decision, legal, rng):
        return next(action for action in legal
                    if action.id == "end_segment")


class TwoMovePlayer:
    """Takes two moves when possible, then ends the phase."""

    def __init__(self):
        self.chosen = 0

    def choose(self, view, decision, legal, rng):
        if self.chosen < 2:
            move = next((action for action in legal
                         if action.id.startswith("move:")), None)
            if move is not None:
                self.chosen += 1
                return move
        return next(action for action in legal
                    if action.id == "end_segment")


class OneMovePlayer:
    """Takes the first offered move in each phase, then ends that phase."""

    def __init__(self):
        self._phase = None

    def choose(self, view, decision, legal, rng):
        phase = decision.id.split("#", 1)[0]
        if phase != self._phase:
            self._phase = phase
            move = next((action for action in legal
                         if action.id.startswith("move:")), None)
            if move is not None:
                return move
        return next(action for action in legal
                    if action.id == "end_segment")


# ---------------------------------------------------------------------------
# sequence
# ---------------------------------------------------------------------------

def test_rule_5_2_operations_stage_has_seventeen_ordered_phases():
    """RULE: 5.2."""
    phases = stage_phases(1)
    assert len(phases) == 17
    assert phases[0].id == "III.A.A"
    assert phases[-1].id == "III.B.L"
    assert [phase.id.split(".")[-1] for phase in phases
            if phase.actor == "B"] == ["F", "G", "H", "J", "K", "L"]


def test_a_full_operations_stage_plays_end_to_end():
    """RULE: 5.2."""
    state = state_with(("ax-1", unit("axis", "A")),
                       ("cw-1", unit("commonwealth", "E")))
    result = play_operations_stage(
        state, scenario(), players={"axis": EndPlayer(),
                                    "commonwealth": EndPlayer()})
    assert result.completed
    assert result.phases == 17
    assert result.actions == 17
    assert result.state["phase"] == "III.B.L"
    assert len(result.state["history"]) == 17
    assert [event["phase"] for event in result.events][0] == "III.A.A"
    assert state["phase"] == "initiative"          # the input is a witness


def test_only_the_movement_and_combat_phase_offers_moves():
    """RULE: 5.2 G."""
    state = state_with(("ax-1", unit("axis", "A")))
    movement = build_decision(state, stage_phases(1)[6], "axis", scenario())
    organization = build_decision(state, stage_phases(1)[2], "axis",
                                   scenario())
    assert movement.id.startswith("T1S1.III.A.G#")
    assert any(action.id.startswith("move:") for action in movement.actions)
    assert [action.id for action in organization.actions] == ["end_segment"]
    assert legal_actions(movement, state)


# ---------------------------------------------------------------------------
# movement, stacking and ZOC
# ---------------------------------------------------------------------------

def test_zoc_control_and_entry_restrictions_are_wired():
    """RULE: 10.21, 10.23, 10.26, 10.29."""
    state = state_with(("ax-1", unit("axis", "A")),
                       ("cw-1", unit("commonwealth", "C")))
    controlled = controlled_hexes(state, "axis", scenario(TRIANGLE))
    # A holds a friendly combat unit, so 10.26 removes it from the set.
    assert controlled == frozenset({"B"})
    combat_moves = legal_moves(state, "axis", scenario(TRIANGLE),
                               phase_key="k")
    stopping = next(option for option in combat_moves
                    if option.unit_id == "ax-1" and option.destination == "B")
    assert "10.23" in stopping.move.stopped
    # A non-combat unit may not voluntarily enter an unoccupied controlled
    # hex (10.29), and 10.24 refuses the controlled-to-controlled path.
    engineer_state = state_with(
        ("ax-e", unit("axis", "A", kind="engineer", move_kind="noncombat")),
        ("cw-1", unit("commonwealth", "C")))
    assert legal_moves(engineer_state, "axis", scenario(TRIANGLE),
                       phase_key="k") == ()


def test_stacking_limit_refuses_the_second_unit_stopping():
    """RULE: 9.31."""
    state = state_with(("ax-1", unit("axis", "A")),
                       ("ax-2", unit("axis", "A")))
    limited = scenario(limits={"A": Fraction(6), "B": Fraction(5)})
    first = legal_moves(state, "axis", limited, phase_key="k")
    assert {(option.unit_id, option.destination) for option in first} == {
        ("ax-1", "B"), ("ax-2", "B")}
    after = apply_move(state, "axis", "ax-1", "B", limited, phase_key="k")
    second = legal_moves(after, "axis", limited, phase_key="k")
    assert all(not (option.unit_id == "ax-2" and option.destination == "B")
               for option in second)
    assert after["units"]["ax-2"]["position"] == "A"


def test_road_track_passage_uses_the_stacking_module():
    """RULE: 9.33."""
    state = state_with(("ax-1", unit("axis", "A")),
                       ("ax-2", unit("axis", "A")))
    road = scenario(limits={"A": Fraction(6), "B": Fraction(6)},
                    road_track=lambda source, destination: True)
    offered = {(option.unit_id, option.destination)
               for option in legal_moves(state, "axis", road, phase_key="k")}
    assert offered == {("ax-1", "B"), ("ax-2", "B")}
    after = apply_move(state, "axis", "ax-2", "B", road, phase_key="k")
    remaining = legal_moves(after, "axis", road, phase_key="k")
    # The ordinary stacking limit would allow 3 + 3 = 6; only 9.33 refuses.
    assert all(not (option.unit_id == "ax-1" and option.destination == "B")
               for option in remaining)


def test_a_move_is_taken_through_the_decision_api_and_recorded():
    """RULE: 8.13; the engine records the choice."""
    state = state_with(("ax-1", unit("axis", "A")))
    decision = build_decision(state, stage_phases(1)[6], "axis", scenario())
    move = next(action for action in decision.actions
                if action.id == "move:ax-1:B")
    after = apply(decision, state, move)
    assert after["units"]["ax-1"]["position"] == "B"
    assert after["units"]["ax-1"]["moved"] == "T1S1.III.A.G"
    assert decision.id in after["decisions"]
    assert after["history"][-1]["action"] == "move:ax-1:B"


def test_8_23_a_unit_within_two_hexes_may_move_again():
    """RULE: 8.22-8.23."""
    state = state_with(("ax-1", unit("axis", "A")),
                       ("cw-1", unit("commonwealth", "C")))

    first = apply_move(state, "axis", "ax-1", "B", scenario(),
                       phase_key="k")

    assert first["units"]["ax-1"]["moves"] == 1
    assert "moved" not in first["units"]["ax-1"]
    assert any(option.unit_id == "ax-1" and option.destination == "A"
               for option in legal_moves(first, "axis", scenario(),
                                         phase_key="k"))

    second = apply_move(first, "axis", "ax-1", "A", scenario(),
                        phase_key="k")

    assert second["units"]["ax-1"]["moves"] == 2
    assert "moved" not in second["units"]["ax-1"]


def test_8_23_a_unit_beyond_two_hexes_finishes_the_phase():
    """RULE: 8.23."""
    state = state_with(("ax-1", unit("axis", "A")),
                       ("cw-1", unit("commonwealth", "E")))

    after = apply_move(state, "axis", "ax-1", "B", scenario(),
                       phase_key="k")

    assert after["units"]["ax-1"]["moved"] == "k"
    assert all(option.unit_id != "ax-1"
               for option in legal_moves(after, "axis", scenario(),
                                         phase_key="k"))


def test_8_23_reserve_status_allows_another_move():
    """RULE: 8.23, 18.0."""
    state = state_with(("ax-1", unit("axis", "A", in_reserve=True)),
                       ("cw-1", unit("commonwealth", "E")))

    after = apply_move(state, "axis", "ax-1", "B", scenario(),
                       phase_key="k")

    assert "moved" not in after["units"]["ax-1"]
    assert any(option.unit_id == "ax-1"
               for option in legal_moves(after, "axis", scenario(),
                                         phase_key="k"))


def test_the_stage_loop_allows_a_continued_move():
    """RULE: 8.22-8.23."""
    state = state_with(("ax-1", unit("axis", "A")),
                       ("cw-1", unit("commonwealth", "C")))

    result = play_operations_stage(
        state, scenario(),
        players={"axis": TwoMovePlayer(), "commonwealth": EndPlayer()})

    record = result.state["units"]["ax-1"]
    assert result.moves == 2
    assert record["moves"] == 2
    assert record["position"] == "A"
    assert "moved" not in record
    assert result.actions == result.phases + 2


def replay_stage_history(initial, scenario, history, *, stage=None):
    """Re-apply a recorded Operations Stage history to *initial*.

    The history is the engine's own ordered record
    (``{"decision", "action", "actor"}``): each decision point is rebuilt
    from the state the loop would have seen and the recorded action id is
    applied through the engine.  No player is consulted, so a replay cannot
    make a choice the recorded stage did not make.
    """
    working = copy.deepcopy(dict(initial))
    stage = int(working["stage"] if stage is None else stage)
    working["stage"] = stage
    working["rail_used"] = []          # 8.74 resets each Operations Stage
    rng = random.Random(working["seed"])
    index = 0
    for phase in stage_phases(stage):
        side = scenario.player_for(phase.actor)
        assert side is not None, f"phase {phase.id} names no side"
        working["phase"] = phase.id
        working["actor"] = side
        working["acting"] = phase.actor
        working["actions_in_segment"] = 0
        step = 0
        while True:
            assert index < len(history), "the history ended before the stage"
            record = history[index]
            decision = build_decision(working, phase, side, scenario,
                                      step=step, rng=rng)
            assert record["decision"] == decision.id
            offered = {action.id for action in legal_actions(decision, working)}
            assert record["action"] in offered, record
            before = len(working.get("combat_log") or ())
            working = apply(decision, working, record["action"])
            index += 1
            step += 1
            if (record["action"].startswith("move:")
                    and len(working.get("combat_log") or ()) == before):
                working = resolve_pending_breakdowns(working, side, scenario,
                                                     rng)
            if record["action"] == "end_segment":
                break
    assert index == len(history), "the history has actions the stage did not take"
    return working


def test_a_full_operations_stage_history_replays_to_the_same_state_hash():
    """RULE: 5.2, 8.13; the recorded history reconstructs the final state."""
    initial = state_with(("ax-1", unit("axis", "A")),
                         ("cw-1", unit("commonwealth", "E")))
    result = play_operations_stage(
        initial, scenario(),
        players={"axis": OneMovePlayer(), "commonwealth": OneMovePlayer()})

    history = result.state["history"]
    assert len(history) == result.actions
    assert (sum(record["action"] == "end_segment" for record in history)
            == result.phases)
    assert result.moves == 2

    replayed = replay_stage_history(initial, scenario(), history,
                                    stage=result.stage)

    assert state_hash(replayed) == state_hash(result.state)
    assert replayed["history"] == history
    assert replayed["units"] == result.state["units"]
    assert initial["units"]["ax-1"]["position"] == "A"


def test_an_adjacent_enemy_hex_is_offered_as_a_combat_handoff():
    """RULE: 8.13, 8.14, 15.0."""
    state = state_with(("ax-1", combatant("axis", "A")),
                       ("cw-1", combatant("commonwealth", "C")))

    options = legal_moves(state, "axis", scenario(TRIANGLE), phase_key="k")

    assault = next(option for option in options
                   if option.unit_id == "ax-1"
                   and option.destination == "C")
    assert assault.combat
    assert assault.stacking is None


def test_an_assault_resolves_without_entering_the_enemy_hex():
    """RULE: 8.13, 15.71-15.96."""
    state = state_with(("ax-1", combatant("axis", "A")),
                       ("cw-1", combatant("commonwealth", "C")))
    with_table = scenario(TRIANGLE, assault_table=synthetic_assault_table)

    after = apply_move(state, "axis", "ax-1", "C", with_table,
                       phase_key="k", rng=FixedDice(3, 3, 2, 2))

    attacker = after["units"]["ax-1"]
    defender = after["units"]["cw-1"]
    assert attacker["position"] == "A"          # 8.13: never entered C
    assert attacker["assaulted"] == "k"
    assert attacker["toe_strength"] == "5"      # 10% of 50 raw points
    assert defender["toe_strength"] == "0"      # 20% of 50 raw points
    assert defender["combat_losses"] == "10"
    entry = after["combat_log"][0]
    assert entry["final"] == 0
    assert entry["rolls"] == [33, 22]
    assert entry["outcome"]["defender"]["toe_lost"] == "10"
    assert "k:C" in after["assaulted_hexes"]


def test_a_unit_that_stops_in_zoc_can_hand_off_to_combat():
    """RULE: 8.14, 15.0; the requested ZOC-to-Combat handoff."""
    state = state_with(("ax-1", combatant("axis", "A")),
                       ("cw-1", combatant("commonwealth", "C")))
    with_table = scenario(assault_table=synthetic_assault_table)

    after_move = apply_move(state, "axis", "ax-1", "B", with_table,
                            phase_key="k")
    options = legal_moves(after_move, "axis", with_table, phase_key="k")
    assert any(option.combat and option.unit_id == "ax-1"
               and option.destination == "C" for option in options)

    after_combat = apply_move(after_move, "axis", "ax-1", "C", with_table,
                              phase_key="k", rng=FixedDice(3, 3, 2, 2))
    assert after_combat["units"]["ax-1"]["position"] == "B"
    assert len(after_combat["combat_log"]) == 1


def test_without_an_assault_table_the_handoff_stays_pending():
    """RULE: 15.7; R-04: the CRT is the caller's to supply."""
    state = state_with(("ax-1", combatant("axis", "A")),
                       ("cw-1", combatant("commonwealth", "C")))

    after = apply_move(state, "axis", "ax-1", "C", scenario(TRIANGLE),
                       phase_key="k")

    assert after["units"]["ax-1"]["position"] == "A"
    assert after["units"]["ax-1"]["combat_pending"] is True
    assert after["pending_combat"]["target"] == "C"
    assert "combat_log" not in after
    assert all(not option.combat
               for option in legal_moves(after, "axis", scenario(TRIANGLE),
                                         phase_key="k"))


def test_a_pending_handoff_resolves_when_the_table_arrives():
    """RULE: 15.7; R-04."""
    state = state_with(("ax-1", combatant("axis", "A")),
                       ("cw-1", combatant("commonwealth", "C")))
    pending = apply_move(state, "axis", "ax-1", "C", scenario(TRIANGLE),
                         phase_key="k")
    with_table = scenario(TRIANGLE, assault_table=synthetic_assault_table)

    after = resolve_pending_combat(pending, with_table,
                                   rng=FixedDice(3, 3, 2, 2))

    assert "pending_combat" not in after
    assert after["units"]["cw-1"]["toe_strength"] == "0"
    assert len(after["combat_log"]) == 1


def test_a_full_stage_is_deterministic_for_one_seed():
    """RULE: 5.2; the P1 exit's determinism requirement."""
    def run():
        state = state_with(("ax-1", unit("axis", "A")),
                           ("ax-2", unit("axis", "B")),
                           ("cw-1", unit("commonwealth", "F")),
                           ("cw-2", unit("commonwealth", "E")))
        return play_operations_stage(
            state, scenario(),
            players={"axis": RandomLegalPlayer(p_end=0.0,
                                               max_actions_per_segment=2),
                     "commonwealth": RandomLegalPlayer(
                         p_end=0.0, max_actions_per_segment=2)},
            rng=random.Random(11))

    first, second = run(), run()
    assert first.state["history"] == second.state["history"]
    assert state_hash(first.state) == state_hash(second.state)
    assert first.moves > 0
    # One end per phase plus one decision per move.
    assert first.actions == first.phases + first.moves


# ---------------------------------------------------------------------------
# refusals
# ---------------------------------------------------------------------------

def test_a_caller_must_name_both_sides_for_the_a_b_players():
    with pytest.raises(StageError):
        scenario(player_a="nobody")


def test_a_stage_needs_a_player_for_each_side():
    state = state_with(("ax-1", unit("axis", "A")))
    with pytest.raises(StageError):
        play_operations_stage(state, scenario(),
                              players={"axis": EndPlayer()})


def test_breakdown_state_persists_across_stage_moves():
    """RULE: 21.24-21.26."""
    state = state_with(("ax-t", unit(
        "axis", "A", unit_class="truck", motorized=True, base_cpa=10,
        stacking_points=1, breakdown_bar=0, toe_points=3)))
    chart = TEC(terrain={"clear": TerrainRow(
        cp=1, breakdown=1, stacking_limit=6)})

    def breakdown_scenario():
        return StageScenario(
            neighbours=lambda hex_id: LINE.get(hex_id, ()),
            cost=lambda moving, source, destination: chart.enter(
                moving, "clear"),
            hex_limits={hex_id: Fraction(6) for hex_id in LINE})

    after = state
    for index, phase_key in enumerate(("k1", "k2", "k3", "k4")):
        after = apply_move(after, "axis", "ax-t", "BCDE"[index],
                           breakdown_scenario(), phase_key=phase_key)
    record = after["units"]["ax-t"]
    assert record["breakdown_points"] == "4"
    assert record["breakdown_column"] == 4
    assert record["breakdown_required"] is True
    assert record["breakdown_pending"] is True


# ---------------------------------------------------------------------------
# breakdown resolution (21.34-21.35)
# ---------------------------------------------------------------------------

class FixedDice:
    """A two-dice source that returns the given faces in order."""

    def __init__(self, *faces):
        self._faces = list(faces)

    def randint(self, low, high):
        value = self._faces.pop(0)
        assert low <= value <= high
        return value


class FirstMovePlayer:
    """Takes a move when one is offered, otherwise ends the phase."""

    def choose(self, view, decision, legal, rng):
        return next((action for action in legal
                     if action.id != "end_segment"), legal[0])


def pending_truck():
    record = unit("axis", "A", unit_class="truck", motorized=True,
                  base_cpa=10, stacking_points=1, breakdown_bar=0,
                  toe_points=3)
    record.update({"breakdown_points": "4", "breakdown_column": 4,
                   "breakdown_required": True, "breakdown_pending": True})
    return record


def test_breakdown_resolution_rolls_two_dice_and_applies_losses():
    """RULE: 21.34-21.35."""
    state = state_with(("ax-t", pending_truck()))
    with_table = StageScenario(
        neighbours=lambda hex_id: LINE.get(hex_id, ()),
        cost=lambda moving, source, destination: Fraction(1),
        hex_limits={hex_id: Fraction(6) for hex_id in LINE},
        breakdown_table=lambda roll, column: 25)

    after = resolve_pending_breakdowns(state, "axis", with_table,
                                       FixedDice(1, 5))

    record = after["units"]["ax-t"]
    assert record["breakdown_roll"] == 15
    assert record["breakdown_percent"] == 25
    assert record["breakdown_losses"] == 1          # ceil(3 * 25 / 100)
    assert record["broken_down_points"] == "1"
    assert record["breakdown_resolved"] is True
    assert record["breakdown_pending"] is False
    assert record["breakdown_last_column"] == 4
    # The resolver is pure: the state it was given still has its check due.
    assert state["units"]["ax-t"]["breakdown_pending"] is True


def test_without_a_breakdown_table_the_check_stays_pending():
    """RULE: 21.34; R-04: the table is the caller's to supply."""
    state = state_with(("ax-t", pending_truck()))

    after = resolve_pending_breakdowns(state, "axis", scenario(),
                                       FixedDice())   # no dice may be drawn

    assert after["units"]["ax-t"]["breakdown_pending"] is True
    assert "breakdown_roll" not in after["units"]["ax-t"]
    assert "breakdown_losses" not in after["units"]["ax-t"]


def test_the_stage_loop_resolves_breakdown_after_a_move():
    """RULE: 21.24-21.35."""
    chart = TEC(terrain={"clear": TerrainRow(
        cp=1, breakdown=4, stacking_limit=6)})
    state = state_with(("ax-t", unit(
        "axis", "A", unit_class="truck", motorized=True, base_cpa=20,
        stacking_points=1, breakdown_bar=0, toe_points=3)))
    graph = {"A": ("B",), "B": ("A",)}
    with_table = StageScenario(
        neighbours=lambda hex_id: graph.get(hex_id, ()),
        cost=lambda moving, source, destination: chart.enter(moving, "clear"),
        hex_limits={hex_id: Fraction(6) for hex_id in graph},
        breakdown_table=lambda roll, column: 50)

    result = play_operations_stage(
        state, with_table,
        players={"axis": FirstMovePlayer(), "commonwealth": EndPlayer()},
        rng=FixedDice(2, 3))

    record = result.state["units"]["ax-t"]
    assert result.moves == 1
    assert record["breakdown_points"] == "4"
    assert record["breakdown_roll"] == 23
    assert record["breakdown_percent"] == 50
    assert record["breakdown_losses"] == 2          # ceil(3 * 50 / 100)
    assert record["breakdown_resolved"] is True
    assert record["breakdown_pending"] is False


class HandoffPlayer:
    """Move into ZOC once, then take the offered Close Assault."""

    def __init__(self):
        self.step = 0

    def choose(self, view, decision, legal, rng):
        if self.step == 0 and any(action.id == "move:ax-1:B"
                                  for action in legal):
            self.step = 1
            return next(action for action in legal
                        if action.id == "move:ax-1:B")
        if self.step == 1 and any(action.id == "move:ax-1:C"
                                  for action in legal):
            self.step = 2
            return next(action for action in legal
                        if action.id == "move:ax-1:C")
        return next(action for action in legal
                    if action.id == "end_segment")


def test_the_stage_loop_hands_a_zoc_stop_off_to_close_assault():
    """RULE: 8.14, 15.0; 5.2 G's Combat Segment handoff."""
    state = state_with(("ax-1", combatant("axis", "A")),
                       ("cw-1", combatant("commonwealth", "C")))
    with_table = scenario(assault_table=synthetic_assault_table)

    result = play_operations_stage(
        state, with_table,
        players={"axis": HandoffPlayer(), "commonwealth": EndPlayer()})

    assert result.phases == 17
    assert result.moves == 1
    assert result.combats == 1
    assert result.actions == result.phases + result.moves + result.combats
    assert result.state["units"]["ax-1"]["position"] == "B"
    assert len(result.state["combat_log"]) == 1
    assert any(event.get("combat") for event in result.events)
    assert result.to_obj()["combats"] == 1
