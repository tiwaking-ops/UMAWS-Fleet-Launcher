"""Weather-effect tests, one named case per test (RULE: 29.2-29.58).

All map-section and storm-location data here is synthetic-test data.  The
real R-04 tables are absent; these tests only fix the rule procedures and the
provenance boundary.
"""

from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cna.rules.sec29_weather import (  # noqa: E402
    MAP_SECTIONS,
    STORMY,
    SYNTHETIC_WEATHER_LOCATION_TABLE,
    WeatherError,
    WeatherLocationTable,
    WeatherResult,
    effects_for,
    sandstorm_majority,
)


def outcome(weather: str, location: int = 3) -> WeatherResult:
    return WeatherResult(
        season="summer",
        roll=11,
        weather=weather,
        location=location if weather in STORMY else None,
        provenance="synthetic-test: weather table",
        status="synthetic",
    )


def test_29_2_normal_weather_has_no_play_effect() -> None:
    """RULE: 29.2."""
    effects = effects_for(outcome("normal"))
    assert effects.affected_sections == frozenset(MAP_SECTIONS)
    assert effects.movement_cost_multiplier("C") == 1
    assert effects.breakdown_column_shift("C") == 0
    assert effects.fuel_water_factor() == 1
    assert effects.water_requirement_multiplier() == 1
    assert not effects.wells_filled("C")


def test_29_31_hot_weather_affects_every_map_section() -> None:
    """RULE: 29.31."""
    effects = effects_for(outcome("hot"))
    assert effects.affected_sections == frozenset(MAP_SECTIONS)
    assert all(effects.is_affected(section) for section in MAP_SECTIONS)


def test_29_32_hot_construction_requires_ten_water() -> None:
    """RULE: 29.32."""
    assert effects_for(outcome("hot")).construction_water_cost() == 10
    assert effects_for(outcome("normal")).construction_water_cost() == 0


def test_29_33_hot_weather_shifts_breakdown_one_column() -> None:
    """RULE: 29.33."""
    assert effects_for(outcome("hot")).breakdown_column_shift("C") == 1
    assert effects_for(outcome("normal")).breakdown_column_shift("C") == 0


def test_29_34_hot_weather_reduces_fuel_and_water_by_five_percent() -> None:
    """RULE: 29.34."""
    assert effects_for(outcome("hot")).fuel_water_factor() == Fraction(95, 100)
    assert effects_for(outcome("normal")).fuel_water_factor() == 1


def test_29_35_hot_weather_doubles_water_requirements() -> None:
    """RULE: 29.35."""
    assert effects_for(outcome("hot")).water_requirement_multiplier() == 2
    assert effects_for(outcome("normal")).water_requirement_multiplier() == 1


def test_29_41_sandstorm_affects_only_listed_sections_and_never_map_e() -> None:
    """RULE: 29.41."""
    affected = effects_for(outcome("sandstorm", location=6))
    assert affected.affected_sections == frozenset({"A", "B"})
    assert affected.is_affected("A")
    assert not affected.is_affected("C")
    # The synthetic table maps roll 5 to map E; 29.41 removes it.
    delta = effects_for(outcome("sandstorm", location=5))
    assert delta.affected_sections == frozenset()
    assert not delta.is_affected("E")


def test_29_42_storm_blocks_construction_in_affected_hexes() -> None:
    """RULE: 29.42."""
    sand = effects_for(outcome("sandstorm", location=3))
    assert not sand.construction_allowed("C")
    assert sand.construction_allowed("A")
    rain = effects_for(outcome("rainstorm", location=3))
    assert not rain.construction_allowed("C")


def test_29_43_sandstorm_blocks_aircraft_in_affected_hexes() -> None:
    """RULE: 29.43."""
    effects = effects_for(outcome("sandstorm", location=3))
    assert not effects.aircraft_allowed("C")
    assert effects.aircraft_allowed("A")


def test_29_44_sandstorm_doubles_movement_cost() -> None:
    """RULE: 29.44."""
    effects = effects_for(outcome("sandstorm", location=3))
    assert effects.movement_cost_multiplier("C") == 2
    assert effects.movement_cost_multiplier("A") == 1


def test_29_45_sandstorm_breakdown_shift_needs_half_the_movement() -> None:
    """RULE: 29.45."""
    assert sandstorm_majority(5, 10)
    assert not sandstorm_majority(4, 10)
    effects = effects_for(outcome("sandstorm", location=3))
    assert effects.breakdown_column_shift("C", sandstorm_majority=True) == 1
    assert effects.breakdown_column_shift("C", sandstorm_majority=False) == 0
    with pytest.raises(WeatherError):
        sandstorm_majority(0, 0)
    with pytest.raises(WeatherError):
        sandstorm_majority(2, 1)


def test_29_46_sandstorm_stops_at_the_coast() -> None:
    """RULE: 29.46."""
    assert not effects_for(outcome("sandstorm", location=3)).storm_reaches_sea()
    assert effects_for(outcome("rainstorm", location=3)).storm_reaches_sea()


def test_29_51_rainstorm_affects_only_listed_sections() -> None:
    """RULE: 29.51."""
    effects = effects_for(outcome("rainstorm", location=4))
    assert effects.affected_sections == frozenset({"D"})
    assert effects.is_affected("D")
    assert not effects.is_affected("C")


def test_29_52_rainstorm_blocks_aircraft_in_affected_hexes() -> None:
    """RULE: 29.52."""
    effects = effects_for(outcome("rainstorm", location=4))
    assert not effects.aircraft_allowed("D")
    assert effects.aircraft_allowed("C")


def test_29_53_rainstorm_fills_wells_in_affected_sections() -> None:
    """RULE: 29.53."""
    effects = effects_for(outcome("rainstorm", location=4))
    assert effects.wells_filled("D")
    assert not effects.wells_filled("C")


def test_29_54_rainstorm_blocks_construction_in_affected_hexes() -> None:
    """RULE: 29.54."""
    effects = effects_for(outcome("rainstorm", location=4))
    assert not effects.construction_allowed("D")
    assert effects.construction_allowed("C")


def test_29_55_rainstorm_closes_wadis_except_by_road() -> None:
    """RULE: 29.55."""
    effects = effects_for(outcome("rainstorm", location=4))
    assert not effects.wadi_crossing_allowed("D")
    assert effects.wadi_crossing_allowed("D", road=True)
    assert effects.wadi_crossing_allowed("C")


def test_29_56_rainstorm_makes_roads_use_the_track_profile() -> None:
    """RULE: 29.56."""
    effects = effects_for(outcome("rainstorm", location=4))
    assert effects.road_uses_track_profile("D")
    assert not effects.road_uses_track_profile("C")
    assert not effects_for(outcome("sandstorm", location=4)).road_uses_track_profile("D")


def test_29_57_rainstorm_closes_unbridged_river_hexsides() -> None:
    """RULE: 29.57."""
    effects = effects_for(outcome("rainstorm", location=4))
    assert not effects.river_crossing_allowed("D")
    assert effects.river_crossing_allowed("D", road_or_rail=True)
    assert effects.river_crossing_allowed("C")


def test_29_58_rainstorm_restricts_delta_vehicles_and_forces_units_to_hold() -> None:
    """RULE: 29.58."""
    effects = effects_for(outcome("rainstorm", location=4))
    assert not effects.delta_vehicle_allowed("D", in_delta=True)
    assert effects.delta_vehicle_allowed("D", in_delta=True,
                                         on_road_or_rail=True)
    assert effects.delta_vehicle_allowed("D", in_delta=False)
    assert effects.delta_unit_must_remain("D", in_delta=True)
    assert not effects.delta_unit_must_remain("D", in_delta=True,
                                               on_road_or_rail=True)
    assert not effects.delta_unit_must_remain("C", in_delta=True)


def test_synthetic_location_table_is_complete_and_labelled() -> None:
    assert SYNTHETIC_WEATHER_LOCATION_TABLE.status == "synthetic"
    assert "R-04" in SYNTHETIC_WEATHER_LOCATION_TABLE.provenance
    assert set(SYNTHETIC_WEATHER_LOCATION_TABLE.rows) == set(range(1, 7))


def test_location_table_rejects_missing_rolls_and_unknown_sections() -> None:
    with pytest.raises(WeatherError, match="missing rolls"):
        WeatherLocationTable({1: ("A",)}, provenance="bad")
    with pytest.raises(WeatherError, match="unknown map section"):
        WeatherLocationTable(
            {location: ("A",) for location in range(1, 7)}
            | {1: ("Z",)},
            provenance="bad",
        )


def test_weather_effects_report_synthetic_provenance_and_require_a_storm_location() -> None:
    effects = effects_for(outcome("rainstorm", location=3))
    payload = effects.to_obj()
    assert payload["location_provenance"].startswith("synthetic-test:")
    assert payload["location_status"] == "synthetic"
    assert payload["affected_sections"] == ["C"]
    with pytest.raises(WeatherError, match="location"):
        effects_for(WeatherResult("summer", 11, "rainstorm", None,
                                  "synthetic-test: weather table", "synthetic"))
