"""Load verified R-05 rail map data through the provenance schema.

R-05 (map data) is not vendored in this repository.  This loader is the door
through which a verified rail transcription enters the engine.  It refuses
anything the provenance schema does not mark ``verified``, and it refuses
duplicate, incomplete or off-map lines instead of inventing a route.

A rail table is a normal schema table::

    {
        "schema_version": 1,
        "source": "chart:R-05:rail",
        "status": "verified",
        "records": [
            {
                "provenance": "chart:R-05:rail",
                "status": "verified",
                "line": "alexandria_mersa_matruh",
                "hexes": ["E3613", "E3714", "D3714"],
                "active": true,
                "destroyed": [],
                "unconstructed": []
            }
        ]
    }

``hexes`` is ordered west to east, as :class:`RailLine` expects.  ``active``
is required because it is rule data (8.71), not a default.  ``destroyed`` and
``unconstructed`` are optional and must name hexes on the line.  When the
scenario map is supplied, every rail hex must resolve to it; an unknown hex is
reported as an ``R05-S01`` gap, not dropped.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from cna.data.schema import DataError, validate_provenance_table
from cna.rules.sec08_transport import RailLine, RailNetwork, TransportError

__all__ = ["SCHEMA_VERSION", "load_rail_map"]

#: The only data-schema version this loader understands.
SCHEMA_VERSION = 1


def _text(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DataError(f"{name} must be a non-empty string")
    return value


def _hexes(value: Any, *, name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(
            value, Sequence):
        raise DataError(f"{name} must be a sequence of hex ids")
    hexes = tuple(_text(item, name=name) for item in value)
    if len(set(hexes)) != len(hexes):
        raise DataError(f"{name} repeats a hex")
    return hexes


def _blocked(value: Any, *, name: str,
             line_hexes: tuple[str, ...]) -> frozenset[str]:
    if value is None:
        return frozenset()
    blocked = _hexes(value, name=name)
    unknown = sorted(set(blocked) - set(line_hexes))
    if unknown:
        raise DataError(
            f"{name} names hex {unknown[0]!r}, which is not on the line")
    return frozenset(blocked)


def load_rail_map(
    table: Mapping[str, Any],
    *,
    map_hexes: Iterable[str] | None = None,
    allow_synthetic: bool = False,
) -> RailNetwork:
    """Load a verified R-05 rail map as a :class:`RailNetwork`.

    ``map_hexes`` is the scenario's hex set.  When supplied, every hex on
    every line must be present in it; a missing hex is refused as an R-05
    map gap.  A labelled synthetic table is admitted only with
    ``allow_synthetic=True`` and cannot be mixed with verified records.
    """
    _, records = validate_provenance_table(
        table,
        kind="rail map",
        schema_version=SCHEMA_VERSION,
        allow_synthetic=allow_synthetic,
    )
    if not records:
        raise DataError("rail map has no lines")

    known = (None if map_hexes is None
             else frozenset(_text(hex_id, name="scenario map hex")
                            for hex_id in map_hexes))
    lines: dict[str, RailLine] = {}
    for index, record in enumerate(records):
        line_name = _text(
            record.get("line"), name=f"rail map records[{index}] line")
        if line_name in lines:
            raise DataError(
                f"rail map records[{index}] duplicates line {line_name!r}")

        raw_hexes = record.get("hexes")
        if raw_hexes is None:
            raise DataError(f"rail map records[{index}] is missing 'hexes'")
        hexes = _hexes(raw_hexes, name=f"rail map records[{index}] hexes")
        if known is not None:
            missing = [hex_id for hex_id in hexes if hex_id not in known]
            if missing:
                raise DataError(
                    f"rail map records[{index}] line {line_name!r} names "
                    f"hex {missing[0]!r}, which is not on the scenario map "
                    "(R05-S01)")

        destroyed = _blocked(
            record.get("destroyed"),
            name=f"rail map records[{index}] destroyed",
            line_hexes=hexes,
        )
        unconstructed = _blocked(
            record.get("unconstructed"),
            name=f"rail map records[{index}] unconstructed",
            line_hexes=hexes,
        )
        overlap = sorted(destroyed & unconstructed)
        if overlap:
            raise DataError(
                f"rail map records[{index}] hex {overlap[0]!r} is both "
                "destroyed and unconstructed")

        active = record.get("active")
        if not isinstance(active, bool):
            raise DataError(
                f"rail map records[{index}] active must be a bool")

        try:
            lines[line_name] = RailLine(
                name=line_name,
                hexes=hexes,
                active=active,
                destroyed=destroyed,
                unconstructed=unconstructed,
            )
        except TransportError as exc:
            raise DataError(
                f"rail map records[{index}] ({line_name!r}): {exc}") from exc

    try:
        return RailNetwork(lines)
    except TransportError as exc:
        raise DataError(f"rail map: {exc}") from exc
