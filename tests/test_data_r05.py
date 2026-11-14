"""Tests for the verified R-05 rail map loader.

The fixtures are explicitly labelled chart fixtures.  No real R-05 map values
are vendored here; these tests exercise the provenance gate, route shape and
scenario-map reference checks.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cna.data import DataError  # noqa: E402
from cna.data.r05 import load_rail_map  # noqa: E402
from cna.rules.sec08_transport import RailNetwork  # noqa: E402

VERIFIED = "chart:R-05:rail:fixture"
SYNTHETIC = "synthetic-test:rail:fixture"


def rail_table(records, *, status="verified"):
    source = VERIFIED if status == "verified" else SYNTHETIC
    return {
        "schema_version": 1,
        "source": source,
        "status": status,
        "records": [
            {"provenance": source, "status": status, **record}
            for record in records
        ],
    }


def line(**overrides):
    return {
        "line": "alexandria_mersa_matruh",
        "hexes": ["E3613", "E3714", "D3714"],
        "active": True,
        **overrides,
    }


def test_load_rail_map_builds_lines_and_the_active_set():
    network = load_rail_map(rail_table([
        line(),
        line(line="soluch_benghazi_barce",
             hexes=["A4130", "B4921"], active=False),
    ]))

    assert isinstance(network, RailNetwork)
    assert set(network.lines) == {
        "alexandria_mersa_matruh", "soluch_benghazi_barce"}
    assert [item.name for item in network.active_lines()] == [
        "alexandria_mersa_matruh"]
    assert network.line("alexandria_mersa_matruh").hexes == (
        "E3613", "E3714", "D3714")
    assert network.line("alexandria_mersa_matruh").usable("E3714")
    assert not network.line("soluch_benghazi_barce").usable("A4130")


def test_rail_hexes_must_resolve_to_the_scenario_map():
    with pytest.raises(DataError, match="R05-S01"):
        load_rail_map(rail_table([line()]),
                      map_hexes={"E3613", "E3714"})


def test_rail_map_rejects_duplicate_or_malformed_lines():
    with pytest.raises(DataError, match="duplicates line"):
        load_rail_map(rail_table([line(), line()]))

    with pytest.raises(DataError, match="repeats a hex"):
        load_rail_map(rail_table([line(hexes=["E3613", "E3613"])]))

    with pytest.raises(DataError, match="not on the line"):
        load_rail_map(rail_table([line(destroyed=["Z9"])]))

    with pytest.raises(DataError, match="both destroyed and unconstructed"):
        load_rail_map(rail_table([
            line(destroyed=["E3613"], unconstructed=["E3613"])]))

    with pytest.raises(DataError, match="active must be a bool"):
        load_rail_map(rail_table([line(active=None)]))

    with pytest.raises(DataError, match="no lines"):
        load_rail_map(rail_table([]))


def test_rail_map_requires_verified_or_admitted_synthetic_provenance():
    synthetic = rail_table([line()], status="synthetic")
    with pytest.raises(DataError, match="verified"):
        load_rail_map(synthetic)
    assert load_rail_map(synthetic, allow_synthetic=True).lines

    mixed = rail_table([line()])
    mixed["records"][0]["status"] = "synthetic"
    with pytest.raises(DataError, match=r"records\[0\]"):
        load_rail_map(mixed)

    wrong_source = rail_table([line()])
    wrong_source["source"] = "rulebook:8.71"
    with pytest.raises(DataError, match="chart:"):
        load_rail_map(wrong_source)


def test_rail_map_rejects_bad_hex_shapes_and_missing_names():
    with pytest.raises(DataError, match="must be a sequence"):
        load_rail_map(rail_table([line(hexes="E3613")]))

    record = line()
    del record["line"]
    with pytest.raises(DataError, match="line must be a non-empty string"):
        load_rail_map(rail_table([record]))
