"""Headless AI-vs-AI soak.

RULE: PDD G-002 and proposal 7 (P1 exit).

This is deliberately a *synthetic* scenario: it exercises the decision API,
the seeded player, the hidden-information view, state hashing and the
three-stage turn loop without needing the missing map, unit charts or real
scenario data.  It is not evidence that historical CNA rules are complete.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from cna.ai.player import Player, RandomLegalPlayer
from cna.engine import (Action, Decision, IllegalAction, apply,
                        legal_actions)
from cna.state.model import new_state, state_hash
from cna.state.views import view

SYNTHETIC_SCENARIO = "synthetic-test: one-step segment, no map or unit data"


class SoakError(RuntimeError):
    """The synthetic game could not make progress."""


def _step_effect(state: Mapping[str, Any], action: Action) -> dict[str, Any]:
    return {
        **state,
        "steps": int(state.get("steps", 0)) + 1,
        "actions_in_segment": int(state.get("actions_in_segment", 0)) + 1,
    }


def _end_effect(state: Mapping[str, Any], action: Action) -> dict[str, Any]:
    return {
        **state,
        "segments": int(state.get("segments", 0)) + 1,
        "actions_in_segment": 0,
    }


def _step() -> Action:
    return Action("step", label="Advance one synthetic step", effect=_step_effect)


def _end() -> Action:
    return Action("end_segment", label="End this synthetic segment",
                  effect=_end_effect)


@dataclass(frozen=True)
class SoakResult:
    seed: int
    turns: int
    stages: int
    steps: int
    illegal_actions: int
    error: str
    state_hash: str

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
        }


@dataclass(frozen=True)
class SoakReport:
    games: tuple[SoakResult, ...]
    game_turns: int

    @property
    def ok(self) -> bool:
        return bool(self.games) and all(game.ok for game in self.games)

    def to_obj(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "scenario": SYNTHETIC_SCENARIO,
            "turns": self.game_turns,
            "seeds": len(self.games),
            "games": [game.to_obj() for game in self.games],
        }


def run_game(seed: int, *, game_turns: int = 6, max_steps: int = 5000,
             player_a: Player | None = None,
             player_b: Player | None = None) -> SoakResult:
    """Play one synthetic game and return its deterministic result."""
    if not isinstance(game_turns, int) or game_turns < 1:
        raise SoakError("game_turns must be a positive integer")
    if not isinstance(max_steps, int) or max_steps < 1:
        raise SoakError("max_steps must be a positive integer")

    state = new_state(seed)
    state["steps"] = 0
    state["segments"] = 0
    state["actions_in_segment"] = 0
    rng = random.Random(seed)
    players: dict[str, Player] = {
        "axis": player_a or RandomLegalPlayer(),
        "commonwealth": player_b or RandomLegalPlayer(),
    }
    steps = 0
    segments = 0

    while state["turn"] <= game_turns:
        actor = "axis" if (state["turn"] + state["stage"]) % 2 == 0 \
            else "commonwealth"
        state["actions_in_segment"] = 0
        actions_here = 0
        while True:
            if steps >= max_steps:
                raise SoakError(f"seed {seed} exceeded {max_steps} steps")
            decision = Decision(
                f"T{state['turn']}S{state['stage']}N{actions_here}",
                (_step(), _end()),
                prompt="synthetic movement/end segment",
                actor=actor,
            )
            legal = legal_actions(decision, state)
            if not legal:
                raise SoakError(f"seed {seed} has no legal actions at {decision.id}")
            chosen = players[actor].choose(view(state, actor), decision,
                                           legal, rng)
            if chosen.id not in {action.id for action in legal}:
                raise SoakError(
                    f"seed {seed} player chose an action not offered: {chosen.id}"
                )
            state = apply(decision, state, chosen)
            steps += 1
            actions_here += 1
            if chosen.id == "end_segment":
                break
            if actions_here > 1000:
                raise SoakError(f"seed {seed} did not end its segment")
        segments += 1
        if state["stage"] < 3:
            state["stage"] += 1
        else:
            state["stage"] = 1
            state["turn"] += 1

    return SoakResult(seed=seed, turns=state["turn"] - 1, stages=segments,
                      steps=steps, illegal_actions=0, error="",
                      state_hash=state_hash(state))


def run_soak(seeds: int | Iterable[int] = 20, *, game_turns: int = 6,
             max_steps: int = 5000) -> SoakReport:
    """Run one synthetic game per seed and collect failures, never hide them."""
    if isinstance(seeds, int):
        seed_list = list(range(seeds))
    else:
        seed_list = list(seeds)
    if not seed_list:
        raise SoakError("at least one seed is required")

    results: list[SoakResult] = []
    for seed in seed_list:
        try:
            results.append(run_game(seed, game_turns=game_turns,
                                    max_steps=max_steps))
        except IllegalAction as exc:
            results.append(SoakResult(seed, game_turns, 0, 0, 1,
                                      f"IllegalAction: {exc}", ""))
        except Exception as exc:  # the soak reports, it does not swallow
            results.append(SoakResult(seed, game_turns, 0, 0, 0,
                                      f"{type(exc).__name__}: {exc}", ""))
    return SoakReport(tuple(results), game_turns)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m cna.tools.soak")
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--turns", type=int, default=6)
    parser.add_argument("--max-steps", type=int, default=5000)
    args = parser.parse_args(argv)
    report = run_soak(args.seeds, game_turns=args.turns,
                      max_steps=args.max_steps)
    print(json.dumps(report.to_obj(), sort_keys=True))
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
