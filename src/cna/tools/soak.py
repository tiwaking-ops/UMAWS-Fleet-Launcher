"""Headless AI-vs-AI soak.

RULE: PDD G-002 and proposal 7 (P1 exit).

The soak no longer hard-codes a map.  It loads a scenario document through
:func:`cna.data.scenario.load_scenario`: identity, sides and turn span, the
Terrain Effects Chart, the hex map and the initial units.  Official R-04/R-05
data enters with ``--scenario FILE`` and must be ``verified``; the built-in
fixture is an explicitly labelled ``synthetic`` document loaded through the
same door, so the soak exercises the real loader rather than a private map.

The synthetic fixture is not evidence that historical CNA data is present.
R-04 and R-05 remain open in ``docs/data-gaps.md``.

Each Game-Turn plays its three Operations Stages end to end through
:func:`cna.engine.loop.play_operations_stage`: the rule 5.2 phases, real
movement offered only where §§8-10 admit it, and stacking/ZOC checks on the
loaded map.  Combat, supply, rail and truck convoys are still out of scope.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from cna.ai.player import Player, RandomLegalPlayer
from cna.data.scenario import load_scenario
from cna.data.schema import DataError
from cna.engine import IllegalAction
from cna.engine.loop import StageError, StageScenario, play_operations_stage
from cna.rules.sec21_breakdown import COLUMN_BOUNDS
from cna.state.model import new_state, state_hash

SYNTHETIC_SOURCE = "synthetic-test:soak-line"
SYNTHETIC_SCENARIO_ID = "synthetic-line"
SYNTHETIC_SCENARIO_NAME = (
    "Synthetic six-hex line (labelled fixture; no official data)")

#: A six-hex line, symmetric adjacency.  Six hexes keep both sides in contact
#: by the second stage without a real map.
SYNTHETIC_MAP: Mapping[str, tuple[str, ...]] = {
    "A": ("B",),
    "B": ("A", "C"),
    "C": ("B", "D"),
    "D": ("C", "E"),
    "E": ("D", "F"),
    "F": ("E",),
}

#: Terrain per hex, alternating clear and rough so a move costs more than the
#: next and Breakdown Points accumulate at two different rates.
SYNTHETIC_TERRAIN: Mapping[str, str] = {
    "A": "clear",
    "B": "rough",
    "C": "clear",
    "D": "rough",
    "E": "clear",
    "F": "rough",
}


def synthetic_breakdown_table(roll: int, column: int) -> int:
    """The synthetic 21.38 table; a caller-supplied stand-in for R-04."""
    if not 11 <= roll <= 66:
        raise ValueError(f"roll must be a two-dice read-out: {roll!r}")
    if column not in COLUMN_BOUNDS:
        raise ValueError(f"not a Breakdown column: {column!r}")
    return 25 if roll % 10 <= column else 50


def synthetic_units() -> dict[str, dict[str, Any]]:
    """Two 3-point brigades per side; one per side is a truck unit.

    The trucks give the soak a Breakdown subject (21.11/21.21); the infantry
    stay in the game as the non-vehicle control.
    """
    def brigade(side: str, position: str, *,
                truck: bool = False) -> dict[str, Any]:
        record = {
            "side": side,
            "position": position,
            "base_cpa": 12,
            "unit_class": "infantry",
            "kind": "combat",
            "move_kind": "combat",
            "stacking_points": 3,
            "cohesion": 0,
            "raw_defensive_close_assault": 10,
        }
        if truck:
            record.update({
                "unit_class": "truck",
                "motorized": True,
                "stacking_points": 1,
                "toe_points": 3,
                "breakdown_bar": 0,
            })
        return record

    return {
        "ax-1": brigade("axis", "A"),
        "ax-2": brigade("axis", "B", truck=True),
        "cw-1": brigade("commonwealth", "F"),
        "cw-2": brigade("commonwealth", "E", truck=True),
    }


def synthetic_scenario_document() -> dict[str, Any]:
    """The labelled synthetic fixture, in the official scenario schema.

    It is deliberately marked ``synthetic`` so the loader will admit it only
    with ``allow_synthetic=True`` and so it can never be mistaken for R-04 or
    R-05 data.
    """
    provenance = SYNTHETIC_SOURCE
    hexes = [
        {
            "provenance": provenance,
            "status": "synthetic",
            "hex": hex_id,
            "terrain": SYNTHETIC_TERRAIN[hex_id],
            "neighbours": list(SYNTHETIC_MAP[hex_id]),
        }
        for hex_id in sorted(SYNTHETIC_MAP)
    ]
    units = []
    for unit_id, record in synthetic_units().items():
        entry = {
            "provenance": provenance,
            "status": "synthetic",
            "id": unit_id,
            "hex": record["position"],
        }
        entry.update({key: value for key, value in record.items()
                      if key != "position"})
        units.append(entry)
    return {
        "schema_version": 1,
        "kind": "scenario",
        "source": provenance,
        "status": "synthetic",
        "id": SYNTHETIC_SCENARIO_ID,
        "name": SYNTHETIC_SCENARIO_NAME,
        "sides": ["axis", "commonwealth"],
        "players": {"a": "axis", "b": "commonwealth"},
        "start": {"turn": 1, "stage": 1},
        "end": {"turn": 6, "stage": 3},
        "operations_stages": 18,
        "tec": {
            "schema_version": 1,
            "source": provenance,
            "status": "synthetic",
            "records": [
                {"provenance": provenance, "status": "synthetic",
                 "terrain": "clear", "cp": 1, "breakdown": 1,
                 "stacking_limit": 6},
                {"provenance": provenance, "status": "synthetic",
                 "terrain": "rough", "cp": 2, "breakdown": 2,
                 "stacking_limit": 4},
            ],
        },
        "map": hexes,
        "units": units,
    }


def synthetic_scenario() -> StageScenario:
    """The labelled synthetic fixture, loaded through the real loader."""
    loaded = load_scenario(synthetic_scenario_document(),
                           allow_synthetic=True)
    return loaded.stage_scenario(breakdown_table=synthetic_breakdown_table)


@dataclass(frozen=True)
class SoakResult:
    seed: int
    turns: int
    stages: int
    steps: int
    illegal_actions: int
    error: str
    state_hash: str
    actors: tuple[str, ...] = ()
    breakdowns: int = 0

    @property
    def ok(self) -> bool:
        return not self.error and self.illegal_actions == 0

    def to_obj(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "turns": self.turns,
            "stages": self.stages,
            "steps": self.steps,
            "illegal_actions": self.illegal_actions,
            "error": self.error,
            "state_hash": self.state_hash,
            "actors": list(self.actors),
            "breakdowns": self.breakdowns,
        }


@dataclass(frozen=True)
class SoakReport:
    games: tuple[SoakResult, ...]
    game_turns: int
    scenario: str

    @property
    def ok(self) -> bool:
        return bool(self.games) and all(game.ok for game in self.games)

    def to_obj(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "scenario": self.scenario,
            "turns": self.game_turns,
            "seeds": len(self.games),
            "games": [game.to_obj() for game in self.games],
        }


class SoakError(RuntimeError):
    """The game could not make progress."""


def _scenario_label(document: Mapping[str, Any]) -> str:
    if not isinstance(document, Mapping):
        return "unknown scenario"
    return f"{document.get('id', '?')}: {document.get('name', '?')}"


def run_game(seed: int, *, game_turns: int = 6, max_steps: int = 5000,
             player_a: Player | None = None,
             player_b: Player | None = None,
             scenario_document: Mapping[str, Any] | None = None) -> SoakResult:
    """Play one loaded game, one full Operations Stage at a time."""
    if not isinstance(game_turns, int) or game_turns < 1:
        raise SoakError("game_turns must be a positive integer")
    if not isinstance(max_steps, int) or max_steps < 1:
        raise SoakError("max_steps must be a positive integer")

    document = (synthetic_scenario_document()
                if scenario_document is None else scenario_document)
    status = document.get("status") if isinstance(document, Mapping) else None
    try:
        loaded = load_scenario(document,
                               allow_synthetic=(status == "synthetic"))
    except DataError as exc:
        raise SoakError(f"scenario: {exc}") from exc

    state = loaded.initial_state(seed)
    rng = random.Random(seed)
    players: dict[str, Player] = {
        "axis": player_a or RandomLegalPlayer(),
        "commonwealth": player_b or RandomLegalPlayer(),
    }
    scenario = loaded.stage_scenario(
        breakdown_table=(synthetic_breakdown_table
                         if loaded.status != "verified" else None))
    steps = 0
    stages = 0
    last_turn = min(loaded.end_turn,
                    loaded.start_turn + game_turns - 1)

    while state["turn"] <= last_turn:
        remaining = max_steps - steps
        if remaining < 1:
            raise SoakError(f"seed {seed} exceeded {max_steps} steps")
        try:
            result = play_operations_stage(
                state, scenario, players=players, rng=rng,
                max_actions=remaining)
        except StageError as exc:
            raise SoakError(f"seed {seed}: {exc}") from exc
        state = result.state
        steps += result.actions
        stages += 1
        if state["stage"] < 3:
            state["stage"] += 1
        else:
            state["stage"] = 1
            state["turn"] += 1

    actors = tuple(sorted({
        str(entry.get("actor")) for entry in state.get("history", [])
        if entry.get("actor")
    }))
    breakdowns = sum(
        1 for record in state["units"].values()
        if record.get("breakdown_roll") is not None)
    return SoakResult(seed=seed, turns=state["turn"] - loaded.start_turn,
                      stages=stages, steps=steps, illegal_actions=0,
                      error="", state_hash=state_hash(state), actors=actors,
                      breakdowns=breakdowns)


def run_soak(seeds: int | Iterable[int] = 20, *, game_turns: int = 6,
             max_steps: int = 5000,
             scenario_document: Mapping[str, Any] | None = None) -> SoakReport:
    """Run one loaded game per seed and collect failures, never hide them."""
    if isinstance(seeds, int):
        seed_list = list(range(seeds))
    else:
        seed_list = list(seeds)
    if not seed_list:
        raise SoakError("at least one seed is required")

    document = (synthetic_scenario_document()
                if scenario_document is None else scenario_document)
    results: list[SoakResult] = []
    for seed in seed_list:
        try:
            results.append(run_game(seed, game_turns=game_turns,
                                    max_steps=max_steps,
                                    scenario_document=document))
        except IllegalAction as exc:
            results.append(SoakResult(seed, game_turns, 0, 0, 1,
                                      f"IllegalAction: {exc}", ""))
        except Exception as exc:  # the soak reports, it does not swallow
            results.append(SoakResult(seed, game_turns, 0, 0, 0,
                                      f"{type(exc).__name__}: {exc}", ""))
    return SoakReport(tuple(results), game_turns, _scenario_label(document))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m cna.tools.soak")
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--turns", type=int, default=6)
    parser.add_argument("--max-steps", type=int, default=5000)
    parser.add_argument(
        "--scenario", metavar="FILE",
        help="verified scenario document (JSON); default is the labelled "
             "synthetic fixture")
    args = parser.parse_args(argv)

    document = None
    if args.scenario:
        try:
            document = json.loads(
                Path(args.scenario).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            parser.error(f"cannot read {args.scenario}: {exc}")

    try:
        report = run_soak(args.seeds, game_turns=args.turns,
                          max_steps=args.max_steps,
                          scenario_document=document)
    except SoakError as exc:
        parser.error(str(exc))
    print(json.dumps(report.to_obj(), sort_keys=True))
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
