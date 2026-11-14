"""Load verified R-04 Terrain Effects, Breakdown and off-map distance tables.

R-04 (Charts and Tables) is not vendored.  These loaders are the door through
which a verified transcription enters the engine: they refuse anything the
provenance schema does not mark ``verified``, and they refuse incomplete or
duplicated rows instead of filling gaps with guesses.

The TEC document is a normal schema table.  Each record names one terrain row::

    {
        "schema_version": 1,
        "source": "chart:R-04:TEC",
        "status": "verified",
        "records": [
            {"provenance": "chart:R-04:TEC", "status": "verified",
             "terrain": "clear", "cp": 1, "breakdown": 0,
             "prohibited": [], "stacking_limit": 6},
        ],
    }

The optional table-level ``road_cp`` and ``road_breakdown`` fields are passed
to :class:`~cna.rules.sec08_movement.TEC`.

The 21.38 Breakdown document has one record per (roll, column) cell::

    {"roll": 11, "column": 4, "percent": 5}

A verified table must contain every sequential two-dice roll (11-66) crossed
with every :data:`~cna.rules.sec21_breakdown.COLUMN_BOUNDS` column.  Missing
cells are an error, never a zero.

The 8.89 Off-Map Land Unit Movement Distance Chart has one record per
``(origin, destination, cpa)`` lookup.  The loader requires the complete
matrix for the CPA values the table declares, so a missing cell is a data
error rather than a guessed distance.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType
from typing import Any

from cna.data.schema import (
    DataError,
    DataHeader,
    validate_header,
    validate_table,
)
from cna.rules.sec08_movement import TEC, MovementError, TerrainRow
from cna.rules.sec08_transport import (
    MAP_EXIT_HEX,
    TRIPOLI_TUNISIA_BOXES,
    OffMapChart,
    TransportError,
)
from cna.rules.sec21_breakdown import COLUMN_BOUNDS

__all__ = [
    "BreakdownTable",
    "load_breakdown_table",
    "load_off_map_chart",
    "load_tec",
]

#: The only data-schema version these loaders understand.
SCHEMA_VERSION = 1


def _checked_records(
    table: Mapping[str, Any], *, kind: str, allow_synthetic: bool = False
) -> tuple[DataHeader, list[Mapping[str, Any]]]:
    """Validate a chart table and require verified (or admitted) provenance.

    A ``synthetic`` table is accepted only with ``allow_synthetic=True`` and
    every record must carry the same status; synthetic and historical data
    are never mixed.
    """
    if not isinstance(table, Mapping):
        raise DataError(f"{kind} table must be a mapping")
    header = validate_header(table)
    if header.schema_version != SCHEMA_VERSION:
        raise DataError(
            f"{kind} schema_version {header.schema_version} is not supported; "
            f"expected {SCHEMA_VERSION}"
        )
    if header.status == "synthetic" and allow_synthetic:
        expected_prefix = "synthetic-test"
    else:
        if header.status != "verified":
            raise DataError(
                f"{kind} table status must be 'verified', got "
                f"{header.status!r}"
            )
        expected_prefix = "chart:"
    if not header.source.startswith(expected_prefix):
        raise DataError(
            f"{kind} table source must cite a {expected_prefix!r} "
            f"provenance, got {header.source!r}"
        )
    records = validate_table(table)
    for index, record in enumerate(records):
        if record["status"] != header.status:
            raise DataError(
                f"{kind} records[{index}] status must be "
                f"{header.status!r}, got {record['status']!r}"
            )
        if not record["provenance"].startswith(expected_prefix):
            raise DataError(
                f"{kind} records[{index}] provenance must cite a "
                f"{expected_prefix!r} source, got {record['provenance']!r}"
            )
    return header, records


def _required(record: Mapping[str, Any], name: str, *, kind: str,
              index: int) -> Any:
    if name not in record:
        raise DataError(f"{kind} records[{index}] is missing {name!r}")
    return record[name]


def _integer(value: Any, *, kind: str, index: int, name: str,
             minimum: int = 0, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DataError(
            f"{kind} records[{index}] {name} must be an integer")
    if value < minimum:
        raise DataError(
            f"{kind} records[{index}] {name} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise DataError(
            f"{kind} records[{index}] {name} must be at most {maximum}")
    return value


def load_tec(table: Mapping[str, Any], *,
             allow_synthetic: bool = False) -> TEC:
    """Load a verified R-04 Terrain Effects Chart as a :class:`TEC`.

    Every record needs ``terrain`` and ``cp``; ``breakdown``, ``prohibited``
    and ``stacking_limit`` are optional.  Duplicate terrain names are
    rejected so a later record cannot silently override an earlier one.  A
    labelled synthetic chart is admitted only with ``allow_synthetic=True``.
    """
    _, records = _checked_records(table, kind="TEC",
                                  allow_synthetic=allow_synthetic)
    if not records:
        raise DataError("TEC table has no terrain records")

    terrain: dict[str, TerrainRow] = {}
    for index, record in enumerate(records):
        name = _required(record, "terrain", kind="TEC", index=index)
        if not isinstance(name, str) or not name.strip():
            raise DataError(
                f"TEC records[{index}] terrain must be a non-empty string")
        if name in terrain:
            raise DataError(
                f"TEC records[{index}] duplicates terrain {name!r}")

        cp = _required(record, "cp", kind="TEC", index=index)
        prohibited = record.get("prohibited", ())
        if isinstance(prohibited, str):
            prohibited = (prohibited,)
        if not isinstance(prohibited, Sequence):
            raise DataError(
                f"TEC records[{index}] prohibited must be a sequence")
        try:
            terrain[name] = TerrainRow(
                cp=cp,
                breakdown=record.get("breakdown", 0),
                prohibited=frozenset(prohibited),
                stacking_limit=record.get("stacking_limit"),
            )
        except MovementError as exc:
            raise DataError(
                f"TEC records[{index}] ({name!r}): {exc}") from exc

    try:
        return TEC(
            terrain=terrain,
            road_cp=table.get("road_cp", Fraction(1)),
            road_breakdown=table.get("road_breakdown", Fraction(0)),
        )
    except MovementError as exc:
        raise DataError(f"TEC: {exc}") from exc


def _breakdown_coordinates() -> frozenset[tuple[int, int]]:
    rolls = {
        tens * 10 + units
        for tens in range(1, 7)
        for units in range(1, 7)
    }
    return frozenset(
        (roll, column)
        for roll in rolls
        for column in COLUMN_BOUNDS
    )


@dataclass(frozen=True)
class BreakdownTable:
    """A complete verified R-04 21.38 Breakdown Table.

    The table is callable with the ``(roll, column)`` signature the rules
    expect, so it can be passed straight to a stage scenario.
    """

    percents: Mapping[tuple[int, int], int]
    source: str

    def __post_init__(self) -> None:
        if (not isinstance(self.source, str)
                or not self.source.startswith("chart:")):
            raise DataError(
                "Breakdown Table source must cite a chart: provenance")
        percents = dict(self.percents)
        expected = _breakdown_coordinates()
        actual = set(percents)
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing:
            raise DataError(
                f"Breakdown Table is missing {len(missing)} cells; "
                f"first is roll {missing[0][0]} column {missing[0][1]}")
        if extra:
            raise DataError(
                f"Breakdown Table has {len(extra)} unexpected cells; "
                f"first is {extra[0]!r}")
        for key, value in percents.items():
            if (isinstance(value, bool) or not isinstance(value, int)
                    or not 0 <= value <= 100):
                raise DataError(
                    f"Breakdown Table percent for {key} must be 0-100")
        object.__setattr__(self, "percents", MappingProxyType(percents))

    def __call__(self, roll: int, column: int) -> int:
        try:
            return self.percents[(roll, column)]
        except KeyError:
            raise DataError(
                f"Breakdown Table has no entry for roll {roll!r} "
                f"column {column!r}") from None

    def __len__(self) -> int:
        return len(self.percents)


def load_breakdown_table(table: Mapping[str, Any]) -> BreakdownTable:
    """Load a complete verified R-04 Breakdown Table.

    Each record supplies ``roll`` (a sequential two-dice read-out), ``column``
    and ``percent``.  Every cell is required; a partial chart cannot become a
    playable table.
    """
    header, records = _checked_records(table, kind="Breakdown Table")
    percents: dict[tuple[int, int], int] = {}
    for index, record in enumerate(records):
        roll = _integer(
            _required(record, "roll", kind="Breakdown Table", index=index),
            kind="Breakdown Table", index=index, name="roll",
            minimum=11, maximum=66,
        )
        if not all(1 <= int(digit) <= 6 for digit in str(roll)):
            raise DataError(
                f"Breakdown Table records[{index}] roll must be a sequential "
                "two-dice read-out")
        column = _integer(
            _required(record, "column", kind="Breakdown Table", index=index),
            kind="Breakdown Table", index=index, name="column",
        )
        if column not in COLUMN_BOUNDS:
            raise DataError(
                f"Breakdown Table records[{index}] column must be one of "
                f"{COLUMN_BOUNDS}")
        percent = _integer(
            _required(record, "percent", kind="Breakdown Table", index=index),
            kind="Breakdown Table", index=index, name="percent",
            maximum=100,
        )
        key = (roll, column)
        if key in percents:
            raise DataError(
                f"Breakdown Table records[{index}] duplicates roll {roll} "
                f"column {column}")
        percents[key] = percent

    try:
        return BreakdownTable(percents, header.source)
    except DataError as exc:
        raise DataError(f"Breakdown Table: {exc}") from exc


def load_off_map_chart(table: Mapping[str, Any], *,
                        allow_synthetic: bool = False) -> OffMapChart:
    """Load a verified 8.89 Off-Map Land Unit Movement Distance Chart.

    Each record supplies ``origin``, ``destination``, ``cpa`` and ``stages``.
    Origins and destinations are the four Tripoli/Tunisia boxes or the A2802
    map exit; duplicate cells are refused.  The table must cover every ordered
    pair for every CPA it declares, so a partial extraction cannot silently
    return a guessed distance.  A runtime CPA outside the declared set raises
    :class:`~cna.rules.sec08_transport.TransportError`.
    """
    _, records = _checked_records(table, kind="Off-Map Distance Chart",
                                  allow_synthetic=allow_synthetic)
    if not records:
        raise DataError("Off-Map Distance Chart has no records")

    positions = (*TRIPOLI_TUNISIA_BOXES, MAP_EXIT_HEX)
    allowed = frozenset(positions)
    values: dict[tuple[str, str, int], int] = {}
    cpas: set[int] = set()
    for index, record in enumerate(records):
        origin = _required(record, "origin", kind="Off-Map Distance Chart",
                           index=index)
        destination = _required(record, "destination",
                                kind="Off-Map Distance Chart", index=index)
        for name, value in (("origin", origin), ("destination", destination)):
            if not isinstance(value, str) or not value.strip():
                raise DataError(
                    f"Off-Map Distance Chart records[{index}] {name} must be "
                    "a non-empty string")
            if value not in allowed:
                raise DataError(
                    f"Off-Map Distance Chart records[{index}] {name} "
                    f"{value!r} must be one of {positions}")
        if origin == destination:
            raise DataError(
                f"Off-Map Distance Chart records[{index}] origin and "
                "destination must differ")
        cpa = _integer(
            _required(record, "cpa", kind="Off-Map Distance Chart",
                      index=index),
            kind="Off-Map Distance Chart", index=index, name="cpa",
            minimum=1,
        )
        stages = _integer(
            _required(record, "stages", kind="Off-Map Distance Chart",
                      index=index),
            kind="Off-Map Distance Chart", index=index, name="stages",
            minimum=1,
        )
        key = (origin, destination, cpa)
        if key in values:
            raise DataError(
                f"Off-Map Distance Chart records[{index}] duplicates "
                f"{origin!r} -> {destination!r} at CPA {cpa}")
        values[key] = stages
        cpas.add(cpa)

    missing = [
        (origin, destination, cpa)
        for origin in positions
        for destination in positions
        if origin != destination
        for cpa in sorted(cpas)
        if (origin, destination, cpa) not in values
    ]
    if missing:
        origin, destination, cpa = missing[0]
        raise DataError(
            f"Off-Map Distance Chart is missing {origin!r} -> "
            f"{destination!r} at CPA {cpa}; {len(missing)} cell(s) absent")

    def stages_for(origin: str, destination: str, cpa: int) -> int:
        try:
            return values[(origin, destination, cpa)]
        except KeyError:
            raise TransportError(
                f"8.89: Off-Map Distance Chart has no entry for "
                f"{origin!r} -> {destination!r} at CPA {cpa}") from None

    try:
        return OffMapChart(stages=stages_for)
    except TransportError as exc:
        raise DataError(f"Off-Map Distance Chart: {exc}") from exc
