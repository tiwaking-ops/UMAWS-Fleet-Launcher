"""Tests for the G-002 random legal player and AI-vs-AI soak."""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cna.ai.player import NoProgressAction, RandomLegalPlayer  # noqa: E402
from cna.engine import Action, Decision  # noqa: E402
from cna.tools.soak import run_game, run_soak  # noqa: E402


def _decision() -> Decision:
    return Decision("test", (
        Action("step"),
        Action("end_segment"),
    ), actor="axis")


def test_random_player_only_returns_an_offered_action() -> None:
    player = RandomLegalPlayer(p_end=0)
    decision = _decision()
    legal = decision.legal_actions({"actor": "axis"})
    chosen = player.choose({"actions_in_segment": 0}, decision, legal,
                           random.Random(1))
    assert chosen.id in {action.id for action in legal}


def test_cap_forces_the_progress_action() -> None:
    player = RandomLegalPlayer(p_end=0, max_actions_per_segment=2)
    decision = Decision("cap", (Action("step"),), actor="axis")
    with pytest.raises(NoProgressAction):
        player.choose({"actions_in_segment": 2}, decision,
                      decision.legal_actions({"actor": "axis"}),
                      random.Random(1))


def test_same_seed_produces_the_same_game_hash() -> None:
    first = run_game(17, game_turns=2)
    second = run_game(17, game_turns=2)
    assert first.state_hash == second.state_hash
    assert first.steps == second.steps
    assert first.ok and second.ok


def test_soak_records_both_sides_as_actors() -> None:
    result = run_game(3, game_turns=1)
    assert result.actors == ("axis", "commonwealth")
    assert result.to_obj()["actors"] == ["axis", "commonwealth"]


def test_twenty_seeded_games_complete_six_turns_without_illegals() -> None:
    report = run_soak(20, game_turns=6)
    assert report.ok is True
    assert len(report.games) == 20
    assert all(game.steps > 0 for game in report.games)
    assert all(game.illegal_actions == 0 for game in report.games)
    assert all(game.error == "" for game in report.games)
    assert len({game.state_hash for game in report.games}) == 20
