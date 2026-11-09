"""Tests for the verified R-04 data loaders.

The fixtures are labelled chart:R-04 test fixtures.  No real R-04 values are
vendored in the repository; these tests exercise the provenance gate and the
row validation, not a historical chart.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cna.data import DataError  # noqa: E402
from cna.data.r04 import (  # noqa: E402
    BreakdownTable,
    load_breakdown_table,
    load_tec,
)
from cna.rules.sec08_movement import MovingUnit  # noqa: E402
from cna.rules.sec21_breakdown import COLUMN_BOUNDS  # noqa: E402


def chart_table(records, **extra):
    source = "chart:R-04:test-fixture"
    return {
        "schema_version": 1,
        "source": source,
        "status": "verified",
        "records": [
            {"provenance": source, "status": "verified", **record}
            for record in records
        ],
        **extra,
    }


def breakdown_records():
    return [
        {"roll": tens * 10 + units, "column": column,
         "percent": (tens + units + column) % 101}
        for tens in range(1, 7)
        for units in range(1, 7)
        for column in COLUMN_BOUNDS
    ]


def test_load_tec_builds_the_movement_chart():
    table = chart_table(
        [
            {"terrain": "clear", "cp": 1, "breakdown": 0,
             "stacking_limit": 6},
            {"terrain": "rough", "cp": 2, "breakdown": 2,
             "prohibited": ["tank"], "stacking_limit": 4},
        ],
        road_cp=1,
        road_breakdown=1,
    )

    tec = load_tec(table)
    infantry = MovingUnit("inf", "axis", base_cpa=10)
    tank = MovingUnit("tank", "axis", base_cpa=10, unit_class="tank",
                      motorized=True)

    assert tec.stacking_limit("clear") == 6
    assert tec.stacking_limit("rough") == 4
    assert (tec.enter(infantry, "clear").cp,
            tec.enter(infantry, "clear").breakdown) == (1, 0)
    assert (tec.enter(infantry, "rough").cp,
            tec.enter(infantry, "rough").breakdown) == (2, 2)
    assert tec.enter(tank, "rough").prohibited
    assert tec.road_cp == 1 and tec.road_breakdown == 1


def test_load_tec_rejects_unverified_or_non_chart_data():
    table = chart_table([{"terrain": "clear", "cp": 1}])
    table["status"] = "synthetic"
    with pytest.raises(DataError, match="verified"):
        load_tec(table)

    table = chart_table([{"terrain": "clear", "cp": 1}])
    table["records"][0]["status"] = "ocr_suspect"
    with pytest.raises(DataError, match=r"records\[0\]"):
        load_tec(table)

    table = chart_table([{"terrain": "clear", "cp": 1}])
    table["source"] = "rulebook:8.37"
    with pytest.raises(DataError, match="chart:"):
        load_tec(table)


def test_load_tec_rejects_duplicate_or_incomplete_rows():
    duplicate = chart_table([
        {"terrain": "clear", "cp": 1},
        {"terrain": "clear", "cp": 2},
    ])
    with pytest.raises(DataError, match="duplicates terrain"):
        load_tec(duplicate)

    with pytest.raises(DataError, match="no terrain records"):
        load_tec(chart_table([]))

    missing_cp = chart_table([{"terrain": "clear"}])
    with pytest.raises(DataError, match="missing 'cp'"):
        load_tec(missing_cp)


def test_load_breakdown_table_builds_a_complete_grid():
    table = chart_table(breakdown_records())

    chart = load_breakdown_table(table)

    assert isinstance(chart, BreakdownTable)
    assert len(chart) == 36 * len(COLUMN_BOUNDS)
    for record in breakdown_records():
        assert chart(record["roll"], record["column"]) == record["percent"]


def test_load_breakdown_table_rejects_missing_cells():
    with pytest.raises(DataError, match="missing 1 cells"):
        load_breakdown_table(chart_table(breakdown_records()[:-1]))


def test_load_breakdown_table_rejects_duplicate_cells():
    records = breakdown_records()
    records.append(dict(records[0]))
    with pytest.raises(DataError, match="duplicates roll"):
        load_breakdown_table(chart_table(records))


def test_load_breakdown_table_validates_rolls_columns_and_percentages():
    records = breakdown_records()
    records[0]["roll"] = 17
    with pytest.raises(DataError, match="two-dice"):
        load_breakdown_table(chart_table(records))

    records = breakdown_records()
    records[0]["roll"] = 10
    with pytest.raises(DataError, match="at least 11"):
        load_breakdown_table(chart_table(records))

    records = breakdown_records()
    records[0]["column"] = 5
    with pytest.raises(DataError, match="column must be one of"):
        load_breakdown_table(chart_table(records))

    records = breakdown_records()
    records[0]["percent"] = 101
    with pytest.raises(DataError, match="percent must be at most 100"):
        load_breakdown_table(chart_table(records))


def test_load_breakdown_table_rejects_unverified_cells():
    table = chart_table(breakdown_records())
    table["records"][0]["status"] = "ocr_suspect"
    with pytest.raises(DataError, match=r"records\[0\]"):
        load_breakdown_table(table)


def synthetic_table(records):
    source = "synthetic-test:tec"
    return {
        "schema_version": 1,
        "source": source,
        "status": "synthetic",
        "records": [{"provenance": source, "status": "synthetic", **record}
                     for record in records],
    }


def test_load_tec_admits_a_labelled_synthetic_table_only_on_request():
    table = synthetic_table([{"terrain": "clear", "cp": 1}])

    with pytest.raises(DataError, match="verified"):
        load_tec(table)

    tec = load_tec(table, allow_synthetic=True)
    assert tec.stacking_limit("clear") is None


def test_load_tec_refuses_mixed_synthetic_and_verified_records():
    table = synthetic_table([{"terrain": "clear", "cp": 1}])
    table["records"][0]["status"] = "verified"

    with pytest.raises(DataError, match=r"records\[0\]"):
        load_tec(table, allow_synthetic=True)
