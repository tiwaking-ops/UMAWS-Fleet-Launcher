"""Weather.

RULE: 29.1-29.58

Weather is determined once per Operations Stage with a sequential two-die
roll.  The real Weather Table (29.6) and Four Weather Location Table (29.7)
are in the missing Charts and Tables booklet (R-04), so this module ships
explicitly labelled **synthetic-test** defaults.  They are suitable for tests
and early scaffolding only; they must not be presented as historical data.

The effect contract is deliberately independent of the map loader.  Callers
supply map-section membership; no map section, storm location or historical
weather probability is invented here.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Mapping

from cna.core.dice import Rng, d6, sequential

RULE = "29.1-29.58"
SEASONS = ("spring", "summer", "fall", "winter")
WEATHERS = ("normal", "hot", "sandstorm", "rainstorm")
STORMY = ("sandstorm", "rainstorm")
MAP_SECTIONS = ("A", "B", "C", "D", "E")

#: Boundary anchors used by the coverage tool and by reviewers.  The module
#: itself does not execute these strings; they make the case set explicit.
CASES = (
    "29.0", "29.1", "29.2", "29.3", "29.4", "29.5", "29.6", "29.7",
    "29.31", "29.32", "29.33", "29.34", "29.35",
    "29.41", "29.42", "29.43", "29.44", "29.45", "29.46", "29.47",
    "29.51", "29.52", "29.53", "29.54", "29.55", "29.56", "29.57", "29.58",
)


class WeatherError(ValueError):
    """A weather input or table is invalid."""


def _points(value: Any, *, name: str = "points") -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise WeatherError(f"{name} must be an integer or Fraction")
    result = Fraction(value)
    if result < 0:
        raise WeatherError(f"{name} must not be negative")
    return result


def _bool(value: Any, *, name: str) -> bool:
    if not isinstance(value, bool):
        raise WeatherError(f"{name} must be a bool")
    return value


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
class WeatherLocationTable:
    """The 29.7 roll-to-map-section mapping, supplied by the caller.

    R-04 is absent, so the module's default is a synthetic fixture.  A caller
    loading real data must pass a verified table with its own provenance.
    """

    rows: Mapping[int, tuple[str, ...] | str]
    provenance: str
    status: str = "synthetic"

    def __post_init__(self) -> None:
        if not isinstance(self.provenance, str) or not self.provenance.strip():
            raise WeatherError("weather location table needs provenance")
        normalized: dict[int, tuple[str, ...]] = {}
        for location, sections in self.rows.items():
            if isinstance(location, bool) or not isinstance(location, int):
                raise WeatherError("weather location keys must be integers 1..6")
            if not 1 <= location <= 6:
                raise WeatherError("weather location keys must be 1..6")
            raw = (sections,) if isinstance(sections, str) else tuple(sections)
            if not raw:
                raise WeatherError(f"location {location} has no map sections")
            for section in raw:
                if section not in MAP_SECTIONS:
                    raise WeatherError(f"unknown map section: {section!r}")
            if len(set(raw)) != len(raw):
                raise WeatherError(f"location {location} repeats a map section")
            normalized[location] = raw
        missing = set(range(1, 7)) - set(normalized)
        if missing:
            raise WeatherError(f"location table is missing rolls: {sorted(missing)}")
        object.__setattr__(self, "rows", normalized)

    def sections_for(self, location: int) -> tuple[str, ...]:
        if isinstance(location, bool) or not isinstance(location, int):
            raise WeatherError("weather location must be an integer 1..6")
        if not 1 <= location <= 6:
            raise WeatherError("weather location must be 1..6")
        return self.rows[location]


#: Synthetic-test mapping only.  It is not the R-04 Four Weather Location
#: Table and must never be presented as such.
SYNTHETIC_WEATHER_LOCATION_TABLE = WeatherLocationTable(
    rows={
        1: ("A",),
        2: ("B",),
        3: ("C",),
        4: ("D",),
        5: ("E",),
        6: ("A", "B"),
    },
    provenance="synthetic-test: R-04 Four Weather Location Table absent",
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


@dataclass(frozen=True)
class WeatherEffects:
    """The 29.2-29.58 effects for one Operations Stage.

    ``affected_sections`` is the set of map sections experiencing the
    weather.  Normal and hot weather affect every section; storms affect the
    sections returned by the location table.  Map E never experiences a
    sandstorm (29.41).
    """

    weather: str
    affected_sections: frozenset[str]
    location: int | None
    provenance: str
    status: str
    location_provenance: str = ""
    location_status: str = ""

    def __post_init__(self) -> None:
        if self.weather not in WEATHERS:
            raise WeatherError(f"unknown weather: {self.weather!r}")
        if not isinstance(self.provenance, str) or not self.provenance.strip():
            raise WeatherError("weather effects need provenance")
        if not isinstance(self.status, str) or not self.status.strip():
            raise WeatherError("weather effects need status")
        affected = frozenset(self.affected_sections)
        unknown = affected - set(MAP_SECTIONS)
        if unknown:
            raise WeatherError(f"unknown affected map sections: {sorted(unknown)}")
        if self.weather in STORMY:
            if self.location is None:
                raise WeatherError("storm effects need a location roll")
            if isinstance(self.location, bool) or not 1 <= self.location <= 6:
                raise WeatherError("storm location must be 1..6")
            if (not self.location_provenance
                    or not self.location_status):
                raise WeatherError("storm effects need location-table provenance")
        elif self.location is not None:
            raise WeatherError("normal and hot weather have no storm location")
        object.__setattr__(self, "affected_sections", affected)

    @staticmethod
    def _section(section: str) -> str:
        if section not in MAP_SECTIONS:
            raise WeatherError(f"unknown map section: {section!r}")
        return section

    def is_affected(self, section: str) -> bool:
        self._section(section)
        return section in self.affected_sections

    def movement_cost_multiplier(self, section: str) -> int:
        """29.44: sandstorm hexes cost double; other weather is unchanged."""
        self._section(section)
        return 2 if self.weather == "sandstorm" and self.is_affected(section) else 1

    def breakdown_column_shift(self, section: str, *,
                               sandstorm_majority: bool = False) -> int:
        """29.33/29.45: hot is +1; sandstorm is +1 only for majority movement."""
        self._section(section)
        _bool(sandstorm_majority, name="sandstorm_majority")
        if self.weather == "hot":
            return 1
        if (self.weather == "sandstorm"
                and self.is_affected(section)
                and sandstorm_majority):
            return 1
        return 0

    def construction_allowed(self, section: str) -> bool:
        """29.42/29.54: no construction in an affected storm hex."""
        self._section(section)
        return not (self.weather in STORMY and self.is_affected(section))

    def aircraft_allowed(self, section: str) -> bool:
        """29.43/29.52: no aircraft into or out of an affected storm hex."""
        self._section(section)
        return not (self.weather in STORMY and self.is_affected(section))

    def fuel_water_factor(self) -> Fraction:
        """29.34: hot weather reduces Fuel and Water levels by 5%."""
        return Fraction(95, 100) if self.weather == "hot" else Fraction(1)

    def construction_water_cost(self) -> int:
        """29.32/24.21: a hot-weather construction site needs 10 Water."""
        return 10 if self.weather == "hot" else 0

    def water_requirement_multiplier(self) -> int:
        """29.35: hot weather doubles unit water requirements."""
        return 2 if self.weather == "hot" else 1

    def wells_filled(self, section: str) -> bool:
        """29.53: depleted wells fill during an affected rainstorm."""
        self._section(section)
        return self.weather == "rainstorm" and self.is_affected(section)

    def road_uses_track_profile(self, section: str) -> bool:
        """29.56: roads use track movement/breakdown values in rain."""
        self._section(section)
        return self.weather == "rainstorm" and self.is_affected(section)

    def wadi_crossing_allowed(self, section: str, *, road: bool = False) -> bool:
        """29.55: wadis are uncrossable in rain except by Roads."""
        self._section(section)
        _bool(road, name="road")
        return not (self.weather == "rainstorm"
                    and self.is_affected(section)
                    and not road)

    def river_crossing_allowed(self, section: str, *,
                               road_or_rail: bool = False) -> bool:
        """29.57: unbridged river hexsides are impassable in rain."""
        self._section(section)
        _bool(road_or_rail, name="road_or_rail")
        return not (self.weather == "rainstorm"
                    and self.is_affected(section)
                    and not road_or_rail)

    def delta_vehicle_allowed(self, section: str, *, in_delta: bool,
                              on_road_or_rail: bool = False) -> bool:
        """29.58: a delta hex needs a road/rail for vehicles in rain."""
        self._section(section)
        _bool(in_delta, name="in_delta")
        _bool(on_road_or_rail, name="on_road_or_rail")
        if not in_delta:
            return True
        return not (self.weather == "rainstorm"
                    and self.is_affected(section)
                    and not on_road_or_rail)

    def delta_unit_must_remain(self, section: str, *, in_delta: bool,
                               on_road_or_rail: bool = False) -> bool:
        """29.58: a unit already in an affected delta hex must remain."""
        self._section(section)
        _bool(in_delta, name="in_delta")
        _bool(on_road_or_rail, name="on_road_or_rail")
        return (in_delta and self.weather == "rainstorm"
                and self.is_affected(section) and not on_road_or_rail)

    def storm_reaches_sea(self) -> bool:
        """29.46/29.52: sandstorms stop at the coast; rainstorms do not."""
        return self.weather == "rainstorm"

    def to_obj(self) -> dict[str, Any]:
        return {
            "weather": self.weather,
            "affected_sections": sorted(self.affected_sections),
            "location": self.location,
            "provenance": self.provenance,
            "status": self.status,
            "location_provenance": self.location_provenance,
            "location_status": self.location_status,
            "rule": RULE,
        }


def effects_for(result: WeatherResult,
                location_table: WeatherLocationTable | None = None
                ) -> WeatherEffects:
    """Build the 29.2-29.58 effect set for a weather determination."""
    if not isinstance(result, WeatherResult):
        raise WeatherError("result must be a WeatherResult")
    if result.weather not in WEATHERS:
        raise WeatherError(f"unknown weather: {result.weather!r}")
    if result.weather in ("normal", "hot"):
        return WeatherEffects(
            weather=result.weather,
            affected_sections=frozenset(MAP_SECTIONS),
            location=None,
            provenance=result.provenance,
            status=result.status,
        )
    if result.weather in STORMY:
        if result.location is None:
            raise WeatherError("storm weather needs a location roll")
        table = location_table or SYNTHETIC_WEATHER_LOCATION_TABLE
        sections = set(table.sections_for(result.location))
        if result.weather == "sandstorm":
            sections.discard("E")                 # 29.41: never on delta map E
        return WeatherEffects(
            weather=result.weather,
            affected_sections=frozenset(sections),
            location=result.location,
            provenance=result.provenance,
            status=result.status,
            location_provenance=table.provenance,
            location_status=table.status,
        )
    raise WeatherError(f"unhandled weather: {result.weather!r}")


def sandstorm_majority(cp_in_sandstorm: Fraction | int,
                       cp_total: Fraction | int) -> bool:
    """29.45: was 50% or more of the movement allowance spent in sandstorm?"""
    inside = _points(cp_in_sandstorm, name="cp_in_sandstorm")
    total = _points(cp_total, name="cp_total")
    if total == 0:
        raise WeatherError("cp_total must be positive")
    if inside > total:
        raise WeatherError("cp_in_sandstorm may not exceed cp_total")
    return inside * 2 >= total


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
