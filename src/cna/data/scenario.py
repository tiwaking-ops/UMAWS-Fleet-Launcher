"""Load a CNA scenario document with its TEC, map and initial units.

R-04 (Charts and Tables) and R-05 (map) are not vendored in this repository.
This module is the door through which a verified transcription enters the
engine: a scenario document names the scenario, its sides and turn span, the
Terrain Effects Chart, the hex map and the initial order of battle.

The provenance contract is the one in :mod:`cna.data.schema`.  A playable
scenario must be ``verified`` and cite ``rulebook:``/``chart:`` sources.  A
``synthetic`` fixture is admitted only when the caller passes
``allow_synthetic=True``, and its records must all say ``synthetic`` too:
synthetic and historical data are never mixed.  ``placeholder`` and
``ocr_suspect`` data cannot start a playable scenario at all.

The loader validates structure, not history.  It rejects duplicate hexes and
unit ids, unknown terrain, a missing or asymmetric neighbour, a unit on an
unknown hex and an Operations-Stage count that disagrees with the turn span.
It does not invent a missing value, and it does not claim that R-04/R-05 are
present.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from cna.data.r04 import load_tec
from cna.data.schema import DataError, DataHeader, validate_header, validate_record
from cna.engine.loop import StageScenario
from cna.rules.sec08_movement import TEC, TECError
from cna.state.model import SIDES, new_state

__all__ = ["KIND", "SCHEMA_VERSION", "Scenario", "ScenarioHex", "load_scenario"]

#: The only document schema this loader understands.
SCHEMA_VERSION = 1

#: A scenario document is distinguishable from a bare chart table.
KIND = "scenario"

#: Source prefixes a playable record may cite, by table status.
_PREFIXES = {
    "verified": ("rulebook:", "chart:"),
    "synthetic": ("synthetic-test",),
}


@dataclass(frozen=True)
class ScenarioHex:
    """One hex of the scenario map: terrain plus symmetric adjacency."""

    hex_id: str
    terrain: str
    neighbours: tuple[str, ...]


@dataclass(frozen=True)
class Scenario:
    """A loaded scenario: identity, turn span, TEC, map and units."""

    id: str
    name: str
    source: str
    status: str
    sides: tuple[str, ...]
    start_turn: int
    start_stage: int
    end_turn: int
    end_stage: int
    operations_stages: int
    player_a: str
    player_b: str
    tec: TEC
    hexes: Mapping[str, ScenarioHex]
    units: Mapping[str, Mapping[str, Any]]

    def stage_scenario(self, *, breakdown_table=None) -> StageScenario:
        """Build the :class:`StageScenario` the Operations Stage loop consumes.

        Costs and stacking limits come from the loaded TEC; adjacency comes
        from the loaded map.  ``breakdown_table`` is supplied by the caller:
        a playable scenario must not acquire a breakdown table the document
        did not carry.
        """
        tec = self.tec
        hexes = self.hexes
        limits = {}
        for hex_id, record in hexes.items():
            limit = tec.stacking_limit(record.terrain)
            if limit is not None:
                limits[hex_id] = limit
        return StageScenario(
            neighbours=lambda hex_id: (
                hexes[hex_id].neighbours if hex_id in hexes else ()),
            cost=lambda moving, source, destination: tec.enter(
                moving, hexes[destination].terrain),
            hex_limits=limits,
            breakdown_table=breakdown_table,
            player_a=self.player_a,
            player_b=self.player_b,
        )

    def initial_state(self, seed: int) -> dict[str, Any]:
        """A fresh state at the scenario's start turn and stage."""
        state = new_state(seed, turn=self.start_turn, stage=self.start_stage)
        state["units"] = {unit_id: dict(record)
                          for unit_id, record in self.units.items()}
        return state


def _mapping(value: Any, what: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DataError(f"{what} must be a mapping")
    return value


def _sequence(value: Any, what: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(
            value, Sequence):
        raise DataError(f"{what} must be a sequence")
    return value


def _string(value: Any, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DataError(f"{what} must be a non-empty string")
    return value


def _integer(value: Any, what: str, *, minimum: int = 0,
             maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DataError(f"{what} must be an integer")
    if value < minimum:
        raise DataError(f"{what} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise DataError(f"{what} must be at most {maximum}")
    return value


def _admit(header: DataHeader, *, allow_synthetic: bool) -> tuple[str, ...]:
    """Return the source prefixes this table may cite, or raise."""
    if header.status == "synthetic":
        if not allow_synthetic:
            raise DataError(
                "scenario status must be 'verified'; pass "
                "allow_synthetic=True only for a labelled synthetic fixture"
            )
        return _PREFIXES["synthetic"]
    if header.status != "verified":
        raise DataError(
            f"scenario status {header.status!r} cannot start a playable "
            "scenario; only 'verified' (or an explicitly admitted "
            "'synthetic' fixture) is allowed"
        )
    return _PREFIXES["verified"]


def _records(document: Mapping[str, Any], key: str, *,
             status: str, prefixes: tuple[str, ...]
             ) -> Sequence[Mapping[str, Any]]:
    """Validate one record list and require it to match the table status."""
    raw = document.get(key)
    if raw is None:
        raise DataError(f"scenario document is missing {key!r}")
    records = _sequence(raw, f"scenario {key}")
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise DataError(f"scenario {key}[{index}] must be a mapping")
        validate_record(record)
        if record["status"] != status:
            raise DataError(
                f"scenario {key}[{index}] status must match the table's "
                f"{status!r}, got {record['status']!r}"
            )
        if not record["provenance"].startswith(prefixes):
            raise DataError(
                f"scenario {key}[{index}] provenance must cite one of "
                f"{prefixes}, got {record['provenance']!r}"
            )
    return records


def _start_end(document: Mapping[str, Any]) -> tuple[int, int, int, int, int]:
    start = _mapping(document.get("start"), "scenario start")
    end = _mapping(document.get("end"), "scenario end")
    start_turn = _integer(start.get("turn"), "scenario start turn", minimum=1)
    start_stage = _integer(start.get("stage"), "scenario start stage",
                           minimum=1, maximum=3)
    end_turn = _integer(end.get("turn"), "scenario end turn", minimum=1)
    end_stage = _integer(end.get("stage"), "scenario end stage",
                         minimum=1, maximum=3)
    if (end_turn, end_stage) < (start_turn, start_stage):
        raise DataError("scenario end is before its start")
    expected = ((end_turn - start_turn) * 3
                + (end_stage - start_stage) + 1)
    declared = _integer(
        document.get("operations_stages", expected),
        "scenario operations_stages", minimum=1)
    if declared != expected:
        raise DataError(
            f"scenario declares {declared} Operations Stages but "
            f"{start_turn}/{start_stage} to {end_turn}/{end_stage} "
            f"contains {expected}"
        )
    return start_turn, start_stage, end_turn, end_stage, declared


def _sides(document: Mapping[str, Any]) -> tuple[str, ...]:
    raw = _sequence(document.get("sides"), "scenario sides")
    sides = tuple(_string(value, "scenario side") for value in raw)
    if len(sides) != 2 or set(sides) != set(SIDES):
        raise DataError(
            f"scenario sides must be exactly {SIDES}; got {sides!r}")
    return sides


def _players(document: Mapping[str, Any], sides: tuple[str, ...]
             ) -> tuple[str, str]:
    raw = _mapping(
        document.get("players", {"a": "axis", "b": "commonwealth"}),
        "scenario players")
    player_a = _string(raw.get("a"), "scenario player a")
    player_b = _string(raw.get("b"), "scenario player b")
    if player_a == player_b:
        raise DataError("scenario players a and b must be different sides")
    for name, side in (("a", player_a), ("b", player_b)):
        if side not in sides:
            raise DataError(
                f"scenario player {name} names {side!r}, which is not a "
                f"scenario side")
    return player_a, player_b


def _map(document: Mapping[str, Any], *, tec: TEC, status: str,
         prefixes: tuple[str, ...]) -> Mapping[str, ScenarioHex]:
    hexes: dict[str, ScenarioHex] = {}
    for index, record in enumerate(
            _records(document, "map", status=status, prefixes=prefixes)):
        hex_id = _string(record.get("hex"), f"scenario map[{index}] hex")
        terrain = _string(record.get("terrain"),
                          f"scenario map[{index}] terrain")
        raw_neighbours = _sequence(record.get("neighbours"),
                                   f"scenario map[{index}] neighbours")
        neighbours = tuple(
            _string(value, f"scenario map[{index}] neighbour")
            for value in raw_neighbours)
        if len(set(neighbours)) != len(neighbours):
            raise DataError(
                f"scenario map[{index}] ({hex_id!r}) repeats a neighbour")
        if hex_id in hexes:
            raise DataError(f"scenario map repeats hex {hex_id!r}")
        try:
            tec.row(terrain)
        except TECError as exc:
            raise DataError(
                f"scenario map[{index}] ({hex_id!r}) has unknown terrain "
                f"{terrain!r}: {exc}") from exc
        hexes[hex_id] = ScenarioHex(hex_id, terrain, neighbours)

    if not hexes:
        raise DataError("scenario map has no hexes")
    for hex_id, record in hexes.items():
        for neighbour in record.neighbours:
            if neighbour == hex_id:
                raise DataError(f"scenario hex {hex_id!r} neighbours itself")
            if neighbour not in hexes:
                raise DataError(
                    f"scenario hex {hex_id!r} names missing neighbour "
                    f"{neighbour!r}")
            if hex_id not in hexes[neighbour].neighbours:
                raise DataError(
                    f"scenario adjacency is not symmetric: {hex_id!r} -> "
                    f"{neighbour!r} is not returned")
    return MappingProxyType(hexes)


def _units(document: Mapping[str, Any], *, hexes: Mapping[str, ScenarioHex],
           sides: tuple[str, ...], status: str, prefixes: tuple[str, ...]
           ) -> Mapping[str, Mapping[str, Any]]:
    units: dict[str, Mapping[str, Any]] = {}
    for index, record in enumerate(
            _records(document, "units", status=status, prefixes=prefixes)):
        unit_id = _string(record.get("id"), f"scenario unit[{index}] id")
        side = _string(record.get("side"), f"scenario unit[{index}] side")
        position = _string(record.get("hex"), f"scenario unit[{index}] hex")
        if unit_id in units:
            raise DataError(f"scenario units repeat id {unit_id!r}")
        if side not in sides:
            raise DataError(
                f"scenario unit {unit_id!r} names unknown side {side!r}")
        if position not in hexes:
            raise DataError(
                f"scenario unit {unit_id!r} is on unknown hex {position!r}")
        if "position" in record:
            raise DataError(
                f"scenario unit {unit_id!r} must use 'hex', not 'position'")
        payload = {
            key: value for key, value in record.items()
            if key not in {"id", "hex", "provenance", "status"}
        }
        payload["side"] = side
        payload["position"] = position
        units[unit_id] = MappingProxyType(payload)
    return MappingProxyType(units)


def load_scenario(document: Mapping[str, Any], *,
                  allow_synthetic: bool = False) -> Scenario:
    """Load a scenario document, its TEC, map and initial units.

    A ``verified`` document is playable.  A ``synthetic`` document is
    accepted only with ``allow_synthetic=True`` and must be wholly synthetic;
    mixing statuses is an error.  Placeholder and OCR-suspect data are refused.
    """
    if not isinstance(document, Mapping):
        raise DataError("scenario document must be a mapping")
    header = validate_header(document)
    if header.schema_version != SCHEMA_VERSION:
        raise DataError(
            f"scenario schema_version {header.schema_version} is not "
            f"supported; expected {SCHEMA_VERSION}")
    if document.get("kind") != KIND:
        raise DataError(
            f"scenario document kind must be {KIND!r}, got "
            f"{document.get('kind')!r}")
    prefixes = _admit(header, allow_synthetic=allow_synthetic)
    if not header.source.startswith(prefixes):
        raise DataError(
            f"scenario source must cite one of {prefixes}, got "
            f"{header.source!r}")

    scenario_id = _string(document.get("id"), "scenario id")
    name = _string(document.get("name"), "scenario name")
    sides = _sides(document)
    player_a, player_b = _players(document, sides)
    start_turn, start_stage, end_turn, end_stage, stages = _start_end(document)

    tec_document = _mapping(document.get("tec"), "scenario tec")
    tec_header = validate_header(tec_document)
    if tec_header.status != header.status:
        raise DataError(
            f"scenario and TEC status must match; scenario is "
            f"{header.status!r} and TEC is {tec_header.status!r}")
    tec = load_tec(tec_document,
                   allow_synthetic=header.status == "synthetic")

    hexes = _map(document, tec=tec, status=header.status, prefixes=prefixes)
    units = _units(document, hexes=hexes, sides=sides,
                   status=header.status, prefixes=prefixes)

    return Scenario(
        id=scenario_id, name=name, source=header.source, status=header.status,
        sides=sides, start_turn=start_turn, start_stage=start_stage,
        end_turn=end_turn, end_stage=end_stage, operations_stages=stages,
        player_a=player_a, player_b=player_b, tec=tec, hexes=hexes,
        units=units,
    )
