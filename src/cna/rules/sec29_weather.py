"""Weather.

RULE: 29.1, 29.31, 29.35, 29.41, 29.51

Weather is determined once per Operations Stage with a sequential two-die
roll.  The real Weather Table is in the missing Charts and Tables booklet
(R-04), so this module ships an explicitly labelled **synthetic-test** table.
It is suitable for tests and early scaffolding only; it must not be
presented as the historical table.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from cna.core.dice import Rng, d6, sequential

RULE = "29.1"
SEASONS = ("spring", "summer", "fall", "winter")
WEATHERS = ("normal", "hot", "sandstorm", "rainstorm")
STORMY = ("sandstorm", "rainstorm")


class WeatherError(ValueError):
    """A weather input or table is invalid."""


def _rows(ranges: Mapping[str, tuple[tuple[int, int, str], ...]]
          ) -> dict[str, dict[int, str]]:
    result: dict[str, dict[int, str]] = {}
    for season, entries in ranges.items():
        if season not in SEASONS:
            raise WeatherError(f"unknown season in table: {season!r}")
        row: dict[int, str] = {}
        for low, high, weather in entries:
            if weather not in WEATHERS:
                raise WeatherError(f"unknown weather kind: {weather!r}")
            if not 11 <= low <= high <= 66:
                raise WeatherError("weather ranges must fall within 11..66")
            for roll in range(low, high + 1):
                if roll in row:
                    raise WeatherError(f"weather table overlaps at {roll}")
                row[roll] = weather
        missing = set(range(11, 67)) - set(row)
        if missing:
            raise WeatherError(f"{season} table is missing rolls: {sorted(missing)}")
        result[season] = row
    missing_seasons = set(SEASONS) - set(result)
    if missing_seasons:
        raise WeatherError(f"weather table is missing seasons: {sorted(missing_seasons)}")
    return result


@dataclass(frozen=True)
class WeatherTable:
    """A complete season x sequential-roll table."""

    rows: Mapping[str, Mapping[int, str]]
    provenance: str
    status: str = "synthetic"

    def __post_init__(self) -> None:
        if not self.provenance:
            raise WeatherError("weather table needs provenance")
        object.__setattr__(self, "rows", _rows({
            season: tuple((roll, roll, weather)
                          for roll, weather in sorted(row.items()))
            for season, row in self.rows.items()
        }))

    def weather_for(self, season: str, roll: int) -> str:
        if season not in self.rows:
            raise WeatherError(f"unknown season: {season!r}")
        if roll not in self.rows[season]:
            raise WeatherError(f"sequential roll {roll} is not in 11..66")
        return self.rows[season][roll]


#: Labels are deliberate: this is not R-04.  It only keeps the walking
#: skeleton playable until the Weather Table is supplied.
SYNTHETIC_WEATHER_TABLE = WeatherTable(
    rows=_rows({
        "spring": ((11, 33, "normal"), (34, 55, "hot"),
                   (56, 61, "sandstorm"), (62, 66, "rainstorm")),
        "summer": ((11, 22, "normal"), (23, 55, "hot"),
                   (56, 63, "sandstorm"), (64, 66, "rainstorm")),
        "fall": ((11, 44, "normal"), (45, 55, "hot"),
                 (56, 61, "sandstorm"), (62, 66, "rainstorm")),
        "winter": ((11, 33, "normal"), (34, 44, "hot"),
                   (45, 55, "rainstorm"), (56, 66, "sandstorm")),
    }),
    provenance="synthetic-test: R-04 Weather Table absent",
    status="synthetic",
)


@dataclass(frozen=True)
class WeatherResult:
    season: str
    roll: int
    weather: str
    location: int | None
    provenance: str
    status: str

    @property
    def is_storm(self) -> bool:
        return self.weather in STORMY

    def to_obj(self) -> dict[str, Any]:
        return {
            "season": self.season,
            "roll": self.roll,
            "weather": self.weather,
            "location": self.location,
            "provenance": self.provenance,
            "status": self.status,
            "rule": RULE,
        }


def season_for_turn(turn: int, stage: int = 1) -> str:
    """Approximate the season for a Game-Turn/Operations Stage.

    The campaign opens in September 1940; this maps each 13-week block to a
    season starting with fall.  It is deterministic scaffolding, not a claim
    about a scenario-specific calendar.
    """
    if not isinstance(turn, int) or turn < 1:
        raise WeatherError("turn must be a positive integer")
    if stage not in (1, 2, 3):
        raise WeatherError("stage must be 1, 2 or 3")
    week = (turn - 1) * 3 + (stage - 1)
    return ("fall", "winter", "spring", "summer")[(week // 13) % 4]


def determine_weather(rng: Rng, season: str,
                      table: WeatherTable | None = None,
                      location_roll: int | None = None) -> WeatherResult:
    """Roll one Operations Stage's weather (29.1)."""
    if season not in SEASONS:
        raise WeatherError(f"unknown season: {season!r}")
    table = table or SYNTHETIC_WEATHER_TABLE
    roll = sequential(rng)
    weather = table.weather_for(season, roll)
    location = None
    if weather in STORMY:
        location = d6(rng) if location_roll is None else location_roll
        if not isinstance(location, int) or not 1 <= location <= 6:
            raise WeatherError("storm location roll must be 1..6")
    return WeatherResult(season, roll, weather, location,
                         table.provenance, table.status)
