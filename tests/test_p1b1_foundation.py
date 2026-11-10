"""Integrated P1b.1 tests for §§5–7 sequence, capability, and initiative.

The units and initiative ratings here are synthetic fixtures.  No historical
OA/TOE or R-05 rating data is asserted.
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

from cna.rules.sec05_sequence import (  # noqa: E402
    GAME_TURN_DAYS,
    OPERATIONS_STAGES,
    TOTAL_PHASES,
    TURN_PHASES,
    new_sequence,
)
from cna.rules.sec06_capability import (  # noqa: E402
    DYNAMIC_CP_COSTS,
    CapabilityError,
    CapabilityState,
    cp_cost,
)
from cna.rules.sec07_initiative import (  # noqa: E402
    InitiativeError,
    InitiativeResult,
    ScenarioInitiative,
    choose_order,
    first_turn_initiative,
    initiative_for_turn,
)


class FixedRng:
    def __init__(self, values: list[int]) -> None:
        self.values = list(values)
        self.calls = 0

    def randint(self, a: int, b: int) -> int:
        assert (a, b) == (1, 6)
        self.calls += 1
        return self.values.pop(0)


def test_rule_5_1_game_turn_has_one_week_and_three_operations_stages() -> None:
    assert GAME_TURN_DAYS == 7
    assert OPERATIONS_STAGES == 3
    stages = {phase.operations_stage for phase in TURN_PHASES
              if phase.operations_stage is not None}
    assert stages == {1, 2, 3}
    assert TOTAL_PHASES == 55


def test_rule_5_1_sequence_reaches_each_operations_stage_once() -> None:
    sequence = new_sequence()
    seen: list[int] = []
    while sequence.turn == 1:
        stage = sequence.phase.operations_stage
        if stage is not None and (not seen or seen[-1] != stage):
            seen.append(stage)
        sequence = sequence.advance()
    assert seen == [1, 2, 3]
    assert sequence.turn == 2
    assert sequence.phase.id == "I"


def test_rule_6_3_capability_costs_and_over_allowance_are_locked() -> None:
    assert cp_cost("phasing_barrage_or_assault") == 5
    assert cp_cost("construct_supply_dump") == Fraction(3, 2)
    assert "enter_enemy_minefield" in DYNAMIC_CP_COSTS
    with pytest.raises(CapabilityError, match="TEC/CPA"):
        cp_cost("enter_enemy_minefield")

    unit = CapabilityState("synthetic-inf", base_cpa=10).spend(12)
    assert unit.spent == 12
    assert unit.dp_earned == 2
    assert unit.cohesion == -2
    assert unit.is_disorganized is True


def test_rule_7_15_scenario_fixes_first_turn_without_a_roll() -> None:
    rng = FixedRng([])
    result = initiative_for_turn(rng, 1, 4, turn=1,
                                 first_turn_winner="commonwealth")
    assert isinstance(result, ScenarioInitiative)
    assert result.winner == "commonwealth"
    assert result.turn == 1
    assert result.source == "scenario"
    assert result.to_obj()["rule"] == "7.15"
    assert rng.calls == 0

    order = choose_order(result.winner, "last")
    assert order.player_a == "axis"
    assert order.player_b == "commonwealth"


def test_rule_7_15_later_turns_roll_again() -> None:
    rng = FixedRng([2, 6])
    result = initiative_for_turn(rng, 0, 0, turn=2,
                                 first_turn_winner="axis")
    assert isinstance(result, InitiativeResult)
    assert result.winner == "commonwealth"
    assert result.rounds == 1
    assert rng.calls == 2


def test_rule_7_15_rejects_an_unknown_scenario_winner() -> None:
    with pytest.raises(InitiativeError, match="winner"):
        first_turn_initiative("nobody")
    with pytest.raises(InitiativeError, match="winner"):
        initiative_for_turn(FixedRng([]), 0, 0, turn=1,
                            first_turn_winner="nobody")
    with pytest.raises(InitiativeError, match="turn"):
        initiative_for_turn(FixedRng([]), 0, 0, turn=0,
                            first_turn_winner="axis")


def test_sections_5_to_7_form_one_deterministic_turn() -> None:
    sequence = new_sequence()
    unit = CapabilityState("synthetic-inf", base_cpa=10)
    rng = FixedRng([])
    initiative = initiative_for_turn(rng, 0, 0, turn=1,
                                     first_turn_winner="axis")
    order = choose_order(initiative.winner, "first")
    assert order.player_a == "axis"

    closed_stages: list[int] = []
    for expected_index in range(TOTAL_PHASES):
        phase = sequence.phase
        assert sequence.index == expected_index
        if phase.operations_stage is not None:
            if phase.actor == "A":
                unit = unit.spend(Fraction(1, 2))
            if phase.id.endswith(".B.L"):
                unit = unit.end_operations_stage()
                closed_stages.append(phase.operations_stage)
        sequence = sequence.advance()

    assert closed_stages == [1, 2, 3]
    assert sequence.turn == 2
    assert sequence.phase.id == "I"
    assert unit.spent == 0
    assert unit.cohesion == 0
    assert rng.calls == 0
