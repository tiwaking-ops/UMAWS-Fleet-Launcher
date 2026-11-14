"""Tests for the scenario document loader.

R-04 and R-05 are not vendored.  These fixtures are schema-valid but
explicitly labelled; the tests exercise provenance admission, map topology and
unit placement, not historical values.
"""

from __future__ import annotations

import json
import sys
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cna.data import DataError, load_scenario  # noqa: E402
from cna.rules.sec08_movement import MovingUnit  # noqa: E402
from cna.rules.sec08_transport import (  # noqa: E402
    MAP_EXIT_HEX,
    TRIPOLI_TUNISIA_BOXES,
)

SOURCES = {
    "verified": ("rulebook:§60.22", "chart:R-04:TEC:fixture"),
    "synthetic": ("synthetic-test:scenario", "synthetic-test:tec"),
}

PARTIAL_FIXTURE = (Path(__file__).resolve().parent / "fixtures"
                   / "scenario-60.22-partial.json")


def scenario_document(*, status="verified", start=(1, 1), end=(1, 3),
                      stages=3, hexes=None, units=None, tec=None,
                      rail=None, off_map_chart=None):
    source, tec_source = SOURCES.get(
        status, (f"{status}:scenario", f"{status}:tec"))

    def record(**fields):
        return {"provenance": source, "status": status, **fields}

    if hexes is None:
        hexes = [
            record(hex="A", terrain="clear", neighbours=["B"]),
            record(hex="B", terrain="rough", neighbours=["A", "C"]),
            record(hex="C", terrain="clear", neighbours=["B"]),
        ]
    if units is None:
        units = [
            record(id="ax-1", side="axis", hex="A", base_cpa=12,
                   unit_class="infantry", kind="combat", move_kind="combat",
                   stacking_points=3, cohesion=0),
            record(id="cw-1", side="commonwealth", hex="C", base_cpa=12,
                   unit_class="infantry", kind="combat", move_kind="combat",
                   stacking_points=3, cohesion=0),
        ]
    if tec is None:
        tec = {
            "schema_version": 1,
            "source": tec_source,
            "status": status,
            "records": [
                {"provenance": tec_source, "status": status,
                 "terrain": "clear", "cp": 1, "breakdown": 0,
                 "stacking_limit": 6},
                {"provenance": tec_source, "status": status,
                 "terrain": "rough", "cp": 2, "breakdown": 2,
                 "stacking_limit": 4},
            ],
        }
    document = {
        "schema_version": 1,
        "kind": "scenario",
        "source": source,
        "status": status,
        "id": "60.22",
        "name": "Test scenario",
        "sides": ["axis", "commonwealth"],
        "start": {"turn": start[0], "stage": start[1]},
        "end": {"turn": end[0], "stage": end[1]},
        "operations_stages": stages,
        "tec": tec,
        "map": hexes,
        "units": units,
    }
    if rail is not None:
        document["rail"] = rail
    if off_map_chart is not None:
        document["off_map_chart"] = off_map_chart
    return document


def rail_table():
    source = "chart:R-05:rail:fixture"
    return {
        "schema_version": 1,
        "source": source,
        "status": "verified",
        "records": [{
            "provenance": source,
            "status": "verified",
            "line": "alexandria_mersa_matruh",
            "hexes": ["A", "B"],
            "active": True,
        }],
    }


def off_map_chart_table():
    source = "chart:R-04:off-map:fixture"
    positions = (*TRIPOLI_TUNISIA_BOXES, MAP_EXIT_HEX)
    return {
        "schema_version": 1,
        "source": source,
        "status": "verified",
        "records": [
            {"provenance": source, "status": "verified",
             "origin": origin, "destination": destination,
             "cpa": 12, "stages": 2}
            for origin in positions
            for destination in positions
            if origin != destination
        ],
    }


def test_load_verified_scenario_builds_the_map_and_tec():
    loaded = load_scenario(scenario_document())

    assert (loaded.id, loaded.name) == ("60.22", "Test scenario")
    assert loaded.status == "verified"
    assert (loaded.start_turn, loaded.start_stage) == (1, 1)
    assert (loaded.end_turn, loaded.end_stage) == (1, 3)
    assert loaded.operations_stages == 3
    assert loaded.player_a == "axis" and loaded.player_b == "commonwealth"

    scenario = loaded.stage_scenario()
    assert scenario.neighbours("B") == ("A", "C")
    assert scenario.neighbours("missing") == ()
    infantry = MovingUnit("inf", "axis", base_cpa=10)
    assert scenario.cost(infantry, "A", "B").cp == Fraction(2)
    assert scenario.cost(infantry, "B", "C").cp == Fraction(1)
    assert scenario.hex_limits == {"A": Fraction(6), "B": Fraction(4),
                                   "C": Fraction(6)}
    assert scenario.player_a == "axis"
    assert scenario.player_b == "commonwealth"


def test_initial_state_places_the_loaded_units():
    loaded = load_scenario(scenario_document())

    state = loaded.initial_state(11)

    assert (state["turn"], state["stage"]) == (1, 1)
    assert state["units"]["ax-1"]["position"] == "A"
    assert state["units"]["cw-1"]["position"] == "C"
    assert "provenance" not in state["units"]["ax-1"]
    assert "id" not in state["units"]["ax-1"]


def test_unverified_scenario_requires_explicit_synthetic_admission():
    document = scenario_document(status="synthetic")

    with pytest.raises(DataError, match="verified"):
        load_scenario(document)

    loaded = load_scenario(document, allow_synthetic=True)
    assert loaded.status == "synthetic"


def test_placeholder_and_ocr_suspect_data_cannot_start_a_scenario():
    for status in ("placeholder", "ocr_suspect"):
        document = scenario_document(status=status)
        document["source"] = f"{status}:scenario"
        for record in document["map"] + document["units"]:
            record["provenance"] = f"{status}:scenario"
        document["tec"]["source"] = f"{status}:tec"
        for record in document["tec"]["records"]:
            record["provenance"] = f"{status}:tec"

        with pytest.raises(DataError, match="cannot start a playable scenario"):
            load_scenario(document, allow_synthetic=True)


def test_synthetic_scenario_refuses_a_verified_tec():
    document = scenario_document(status="synthetic")
    source = "chart:R-04:TEC:fixture"
    document["tec"] = {
        "schema_version": 1,
        "source": source,
        "status": "verified",
        "records": [{"provenance": source, "status": "verified",
                     "terrain": "clear", "cp": 1}],
    }

    with pytest.raises(DataError, match="status must match"):
        load_scenario(document, allow_synthetic=True)


def test_scenario_refuses_records_that_disagree_with_the_table_status():
    document = scenario_document()
    document["map"][0]["status"] = "synthetic"

    with pytest.raises(DataError, match="must match"):
        load_scenario(document)


def test_unknown_terrain_is_refused_not_defaulted():
    document = scenario_document()
    document["map"][0]["terrain"] = "swamp"

    with pytest.raises(DataError, match="unknown terrain"):
        load_scenario(document)


def test_asymmetric_or_missing_adjacency_is_refused():
    document = scenario_document()
    document["map"][0]["neighbours"] = ["B", "C"]

    with pytest.raises(DataError, match="not symmetric"):
        load_scenario(document)

    document = scenario_document()
    document["map"][0]["neighbours"] = ["Z"]

    with pytest.raises(DataError, match="missing neighbour"):
        load_scenario(document)


def test_duplicate_hex_is_refused():
    document = scenario_document()
    document["map"].append(dict(document["map"][0]))

    with pytest.raises(DataError, match="repeats hex"):
        load_scenario(document)


def test_duplicate_or_misplaced_units_are_refused():
    document = scenario_document()
    document["units"].append(dict(document["units"][0]))
    with pytest.raises(DataError, match="repeat id"):
        load_scenario(document)

    document = scenario_document()
    document["units"][0]["hex"] = "Z"
    with pytest.raises(DataError, match="unknown hex"):
        load_scenario(document)

    document = scenario_document()
    document["units"][0]["side"] = "italy"
    with pytest.raises(DataError, match="unknown side"):
        load_scenario(document)

    document = scenario_document()
    document["units"][0]["position"] = "A"
    with pytest.raises(DataError, match="must use 'hex'"):
        load_scenario(document)


def test_operations_stage_count_must_match_the_turn_span():
    document = scenario_document(end=(1, 3), stages=4)

    with pytest.raises(DataError, match="declares 4"):
        load_scenario(document)


def test_sides_and_players_must_be_the_engine_sides():
    document = scenario_document()
    document["sides"] = ["axis"]
    with pytest.raises(DataError, match="exactly"):
        load_scenario(document)

    document = scenario_document()
    document["players"] = {"a": "axis", "b": "axis"}
    with pytest.raises(DataError, match="different sides"):
        load_scenario(document)


def test_partial_60_22_fixture_is_refused_with_the_missing_r05_hex():
    document = json.loads(PARTIAL_FIXTURE.read_text(encoding="utf-8"))

    with pytest.raises(DataError) as caught:
        load_scenario(document)

    assert str(caught.value) == (
        "scenario unit 'ax-2' is on unknown hex 'C4218': "
        "R05-S01: C4218 missing from R-05 map data")


def test_document_kind_and_schema_version_are_enforced():
    document = scenario_document()
    document["kind"] = "chart"
    with pytest.raises(DataError, match="kind must be"):
        load_scenario(document)

    document = scenario_document()
    document["schema_version"] = 2
    with pytest.raises(DataError, match="schema_version"):
        load_scenario(document)


def test_scenario_carries_verified_rail_and_off_map_chart():
    loaded = load_scenario(scenario_document(
        rail=rail_table(), off_map_chart=off_map_chart_table()))

    assert loaded.rail is not None
    assert loaded.off_map_chart is not None
    stage = loaded.stage_scenario()
    assert stage.rail is loaded.rail
    assert stage.off_map_chart is loaded.off_map_chart
    assert stage.rail.line("alexandria_mersa_matruh").hexes == ("A", "B")
    assert stage.off_map_chart.stages_between("tripoli", "tunis", 12) == 2


def test_scenario_without_transport_tables_leaves_them_disabled():
    stage = load_scenario(scenario_document()).stage_scenario()

    assert stage.rail is None
    assert stage.off_map_chart is None


def test_scenario_refuses_a_rail_table_with_a_mismatched_status():
    rail = rail_table()
    rail["status"] = "synthetic"
    rail["source"] = "synthetic-test:rail"
    for record in rail["records"]:
        record["status"] = "synthetic"
        record["provenance"] = "synthetic-test:rail"

    with pytest.raises(DataError, match="status must match"):
        load_scenario(scenario_document(rail=rail))


def test_scenario_refuses_a_rail_hex_missing_from_the_map():
    rail = rail_table()
    rail["records"][0]["hexes"] = ["A", "Z"]

    with pytest.raises(DataError, match="R05-S01"):
        load_scenario(scenario_document(rail=rail))


def test_scenario_refuses_an_off_map_chart_with_a_missing_cell():
    chart = off_map_chart_table()
    chart["records"].pop()

    with pytest.raises(DataError, match="cell"):
        load_scenario(scenario_document(off_map_chart=chart))
