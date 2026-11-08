"""Provenance-aware data schemas for the CNA digital edition.

The proposal's data policy requires every data file to say where it came from
and how trustworthy it is, and every record to carry the same two fields.  This
module is deliberately small: it defines the vocabulary and the validation
rules, not any historical unit statistics.  Missing historical data stays
missing; callers may use a ``placeholder`` record only when they explicitly opt
in.

A table is a mapping with a header and a list of records::

    {
        "schema_version": 1,
        "source": "rulebook:§60.31",
        "status": "verified",
        "records": [
            {"provenance": "rulebook:§60.31", "status": "verified", ...}
        ],
    }

No function here reads files or invents values.  Loaders should validate the
header before parsing rows and validate every row before exposing it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

__all__ = [
    "PROVENANCE_PREFIXES",
    "STATUSES",
    "DataError",
    "DataHeader",
    "require_playable",
    "validate_header",
    "validate_provenance",
    "validate_record",
    "validate_status",
    "validate_table",
]

#: The reviewed status vocabulary from the proposal.
STATUSES = frozenset({"verified", "ocr_suspect", "placeholder", "synthetic"})

#: Accepted provenance prefixes.  The prefix identifies the *kind* of source;
#: the rest of the string is free-form and should cite the case or chart.
PROVENANCE_PREFIXES = (
    "rulebook:",
    "chart:",
    "ocr-suspect",
    "placeholder",
    "synthetic-test",
)


class DataError(ValueError):
    """Raised when a data header or record violates the provenance contract."""


@dataclass(frozen=True)
class DataHeader:
    """A validated table header.

    ``source`` names the source, ``status`` says how far it has been checked,
    and ``schema_version`` lets loaders reject incompatible files.
    """

    schema_version: int
    source: str
    status: str


def _field(record: Mapping[str, Any], name: str, *, kind: str) -> Any:
    if name not in record:
        raise DataError(f"{kind} is missing required field {name!r}")
    return record[name]


def validate_status(status: Any, *, kind: str = "record") -> str:
    """Return ``status`` when it is in :data:`STATUSES`, else raise."""
    if not isinstance(status, str) or status not in STATUSES:
        allowed = ", ".join(sorted(STATUSES))
        raise DataError(f"{kind} has unknown status {status!r}; expected one of {allowed}")
    return status


def validate_provenance(provenance: Any, *, kind: str = "record") -> str:
    """Return a non-empty provenance string with an accepted prefix."""
    if not isinstance(provenance, str) or not provenance.strip():
        raise DataError(f"{kind} is missing a non-empty provenance")
    if not provenance.startswith(PROVENANCE_PREFIXES):
        prefixes = ", ".join(PROVENANCE_PREFIXES)
        raise DataError(
            f"{kind} provenance {provenance!r} must start with one of: {prefixes}"
        )
    return provenance


def validate_header(header: Mapping[str, Any] | DataHeader) -> DataHeader:
    """Validate a table header and return it as a :class:`DataHeader`."""
    if isinstance(header, DataHeader):
        raw: Mapping[str, Any] = {
            "schema_version": header.schema_version,
            "source": header.source,
            "status": header.status,
        }
    elif isinstance(header, Mapping):
        raw = header
    else:
        raise DataError("table header must be a mapping or DataHeader")

    schema_version = _field(raw, "schema_version", kind="table header")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool) or schema_version < 1:
        raise DataError("table header schema_version must be a positive integer")

    source = _field(raw, "source", kind="table header")
    if not isinstance(source, str) or not source.strip():
        raise DataError("table header source must be a non-empty string")

    status = validate_status(
        _field(raw, "status", kind="table header"), kind="table header"
    )
    return DataHeader(schema_version=schema_version, source=source, status=status)


def validate_record(record: Mapping[str, Any]) -> None:
    """Validate the common provenance fields on one data record."""
    if not isinstance(record, Mapping):
        raise DataError("data record must be a mapping")
    validate_provenance(_field(record, "provenance", kind="record"))
    validate_status(_field(record, "status", kind="record"))


def validate_table(table: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Validate a table header and every record, returning the records.

    The header's schema version is checked, but this function does not impose a
    specific version: future loaders decide which versions they understand.
    """
    if not isinstance(table, Mapping):
        raise DataError("table must be a mapping")
    validate_header(table)
    records = _field(table, "records", kind="table")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes, bytearray)):
        raise DataError("table records must be a sequence of mappings")
    for index, record in enumerate(records):
        try:
            validate_record(record)
        except DataError as exc:
            raise DataError(f"records[{index}]: {exc}") from exc
    return list(records)


def require_playable(
    header: Mapping[str, Any] | DataHeader, *, allow_placeholder: bool = False
) -> DataHeader:
    """Validate a header and reject placeholder data unless explicitly allowed.

    A rulebook scenario must not start on invented or incomplete data.  Tests
    use ``synthetic`` fixtures; placeholders are permitted only for explicitly
    labelled, non-rulebook play while the gap register remains open.
    """
    parsed = validate_header(header)
    if parsed.status == "placeholder" and not allow_placeholder:
        raise DataError(
            "placeholder data cannot start a rulebook scenario; "
            "pass allow_placeholder=True for an explicitly labelled preview"
        )
    return parsed
