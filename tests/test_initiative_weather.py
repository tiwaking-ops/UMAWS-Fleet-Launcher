"""Tests for initiative (7.14) and weather (29.1)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cna.rules.sec07_initiative import (InitiativeError,
                                       choose_order,
                                       determine_initiative)  # noqa: E402
from cna.rules.sec29_weather import (SYNTHETIC_WEATHER_TABLE,
                                     WeatherError, WeatherTable,
                                     determine_weather, season_for_turn)  # noqa: E402


class FixedRng:
    def __init__(self, values: list[int]) -> None:
        self.values = list(values)
        self.calls = 0

    def randint(self, a: int, b: int) -> int:
        assert (a, b) == (1, 6)
        self.calls += 1
        return self.values.pop(0)


def test_initiative_ties_are_rerolled() -> None:
    # ratings 1 and 3: totals tie at 4, tie at 5, then Axis wins 7 to 6.
    rng = FixedRng([3, 1, 4, 2, 6, 3])
    result = determine_initiative(rng, 1, 3)
    assert result.winner == "axis"
    assert result.rounds == 3
    assert result.axis_total == 7
    assert result.commonwealth_total == 6
    assert rng.calls == 6


def test_winner_can_choose_first_or_last() -> None:
    first = choose_order("commonwealth", "first")
    assert first.player_a == "commonwealth"
    assert first.player_b == "axis"
    last = choose_order("commonwealth", "last")
    assert last.player_a == "axis"
    assert last.player_b == "commonwealth"


def test_invalid_initiative_inputs_are_refused() -> None:
    with pytest.raises(InitiativeError):
        determine_initiative(FixedRng([]), -1, 2)
    with pytest.raises(InitiativeError):
        choose_order("nobody", "first")
    with pytest.raises(InitiativeError):
        choose_order("axis", "sideways")


def test_synthetic_weather_table_is_complete_and_labelled() -> None:
    assert SYNTHETIC_WEATHER_TABLE.status == "synthetic"
    assert "R-04" in SYNTHETIC_WEATHER_TABLE.provenance
    for season in ("spring", "summer", "fall", "winter"):
        assert set(SYNTHETIC_WEATHER_TABLE.rows[season]) == set(range(11, 67))


def test_weather_rolls_sequential_and_returns_a_storm_location() -> None:
    result = determine_weather(FixedRng([6, 6, 4]), "spring")
    assert result.roll == 66
    assert result.weather == "rainstorm"
    assert result.location == 4
    assert result.is_storm is True


def test_normal_weather_needs_no_location_roll() -> None:
    result = determine_weather(FixedRng([1, 1]), "spring")
    assert result.weather == "normal"
    assert result.location is None


def test_weather_seasons_advance_in_13_week_blocks() -> None:
    assert season_for_turn(1, 1) == "fall"
    assert season_for_turn(6, 1) == "winter"
    assert season_for_turn(14, 1) == "summer"
    with pytest.raises(WeatherError):
        season_for_turn(0)


def test_a_custom_incomplete_weather_table_is_refused() -> None:
    with pytest.raises(WeatherError):
        WeatherTable({"spring": {11: "normal"}}, provenance="bad")
