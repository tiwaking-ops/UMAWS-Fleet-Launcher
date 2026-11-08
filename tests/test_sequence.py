"""Tests for the rule 5.2 sequence of play."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cna.rules.sec05_sequence import (SequenceState, SequenceError,
                                      TOTAL_PHASES, TURN_PHASES,
                                      new_sequence, phase_for,
                                      phase_index)  # noqa: E402
from cna.state.model import new_state  # noqa: E402


def test_rule_5_2_has_one_originating_phase_and_three_operations_stages() -> None:
    assert TURN_PHASES[0].id == "I"
    assert TURN_PHASES[-1].id == "VI"
    assert TOTAL_PHASES == 55
    assert [phase.id for phase in TURN_PHASES].count("III.A.A") == 1
    assert [phase.id for phase in TURN_PHASES].count("IV.A.A") == 1
    assert [phase.id for phase in TURN_PHASES].count("V.A.A") == 1


def test_player_b_repeats_only_f_through_l() -> None:
    ops1 = [phase for phase in TURN_PHASES
            if phase.operations_stage == 1]
    a_phases = [phase for phase in ops1 if phase.actor == "A"]
    b_phases = [phase for phase in ops1 if phase.actor == "B"]
    assert [phase.id.split(".")[-1] for phase in a_phases] == [
        "A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L"
    ]
    assert [phase.id.split(".")[-1] for phase in b_phases] == [
        "F", "G", "H", "J", "K", "L"
    ]


def test_advancing_through_a_whole_turn_wraps_to_the_next() -> None:
    sequence = new_sequence()
    for _ in range(TOTAL_PHASES):
        sequence = sequence.advance()
    assert sequence.turn == 2
    assert sequence.phase.id == "I"


def test_phase_index_and_lookup_round_trip() -> None:
    assert phase_for("III.B.L").id == "III.B.L"
    assert phase_index("III.B.L") == phase_index("III.B.L")
    try:
        phase_for("nope")
    except SequenceError:
        pass
    else:  # pragma: no cover
        raise AssertionError("unknown phase was accepted")


def test_sequence_writes_the_rule_5_2_position_into_game_state() -> None:
    state = new_state(11)
    sequence = SequenceState(turn=2, index=phase_index("IV.B.F"))
    updated = sequence.apply_to_state(state)
    assert updated["turn"] == 2
    assert updated["stage"] == 2
    assert updated["phase"] == "IV.B.F"
    assert updated["acting"] == "B"
    assert state["turn"] == 1  # untouched witness
