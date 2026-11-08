import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cna.data.schema import (
    DataError,
    DataHeader,
    require_playable,
    validate_header,
    validate_provenance,
    validate_record,
    validate_status,
    validate_table,
)


def test_header_and_record_accept_verified_provenance():
    header = validate_header(
        {"schema_version": 1, "source": "rulebook:§60.31", "status": "verified"}
    )
    assert header == DataHeader(1, "rulebook:§60.31", "verified")
    validate_record({"provenance": "chart:R-04:Table 7", "status": "ocr_suspect"})


@pytest.mark.parametrize("field,value", [("source", ""), ("source", None)])
def test_header_rejects_empty_source(field, value):
    with pytest.raises(DataError, match="source"):
        validate_header({"schema_version": 1, field: value, "status": "verified"})


@pytest.mark.parametrize("version", [0, -1, "1", True])
def test_header_rejects_invalid_schema_version(version):
    with pytest.raises(DataError, match="schema_version"):
        validate_header(
            {"schema_version": version, "source": "rulebook:§60", "status": "verified"}
        )


def test_status_and_provenance_are_strict():
    assert validate_status("synthetic") == "synthetic"
    with pytest.raises(DataError, match="unknown status"):
        validate_status("trust-me")
    with pytest.raises(DataError, match="must start with"):
        validate_provenance("my-best-guess")
    with pytest.raises(DataError, match="non-empty provenance"):
        validate_provenance("")


def test_record_requires_both_fields():
    with pytest.raises(DataError, match="provenance"):
        validate_record({"status": "verified"})
    with pytest.raises(DataError, match="status"):
        validate_record({"provenance": "rulebook:§6.0"})


def test_table_validates_every_record_with_an_index():
    table = {
        "schema_version": 1,
        "source": "synthetic-test:test-oasis",
        "status": "synthetic",
        "records": [
            {"provenance": "synthetic-test:unit", "status": "synthetic"},
            {"provenance": "synthetic-test:unit", "status": "placeholder"},
            {"provenance": "synthetic-test:unit", "status": "invented"},
        ],
    }
    with pytest.raises(DataError, match=r"records\[2\]"):
        validate_table(table)


def test_placeholder_data_requires_an_explicit_opt_in():
    header = DataHeader(1, "placeholder:R-05:map", "placeholder")
    with pytest.raises(DataError, match="placeholder data"):
        require_playable(header)
    assert require_playable(header, allow_placeholder=True) == header
    assert require_playable(DataHeader(1, "rulebook:§60", "verified")) == DataHeader(
        1, "rulebook:§60", "verified"
    )
