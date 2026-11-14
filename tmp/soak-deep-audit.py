"""Deep AI-vs-AI soak with a per-history-entry audit.

This deliberately mirrors cna.tools.soak.run_game but keeps the legal set
and the expected actor for every step.  It then checks:

* every history entry has exactly {decision, action, actor};
* the actor is the side whose turn/stage it is (and is a known side);
* the action was in legal_actions immediately before apply;
* apply appended exactly one entry and recorded the same resolution;
* the spent decision offers nothing afterwards;
* history length, decision count, order and uniqueness agree;
* both sides acted, and the audited final state matches run_game exactly.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cna.ai.player import RandomLegalPlayer  # noqa: E402
from cna.engine import (HISTORY_KEY, RESOLUTIONS_KEY,  # noqa: E402
                        Decision, actor_in_play, apply, legal_actions)
from cna.state.model import new_state as fresh_state, state_hash  # noqa: E402
from cna.state.views import view  # noqa: E402
from cna.tools.soak import SYNTHETIC_SCENARIO, _end, _step, run_game  # noqa: E402

SIDES = ("axis", "commonwealth")
SEEDS = 100
TURNS = 12


def audit_game(seed: int, turns: int) -> dict:
    state = fresh_state(seed)
    state["steps"] = 0
    state["segments"] = 0
    state["actions_in_segment"] = 0
    rng = random.Random(seed)
    players = {"axis": RandomLegalPlayer(), "commonwealth": RandomLegalPlayer()}
    steps = 0
    segments = 0
    records: list[dict] = []
    errors: list[str] = []

    while state["turn"] <= turns:
        actor = "axis" if (state["turn"] + state["stage"]) % 2 == 0 \
            else "commonwealth"
        state["actor"] = actor
        state["actions_in_segment"] = 0
        actions_here = 0
        while True:
            decision = Decision(
                f"T{state['turn']}S{state['stage']}N{actions_here}",
                (_step(), _end()),
                prompt="synthetic movement/end segment",
                actor=actor,
            )
            legal = legal_actions(decision, state)
            legal_ids = tuple(action.id for action in legal)
            expected_actor = actor_in_play(state, decision)
            if not legal:
                errors.append(f"{decision.id}: no legal actions")
                break
            if expected_actor != actor:
                errors.append(
                    f"{decision.id}: actor_in_play={expected_actor!r}, expected {actor!r}")
            if any(action.id not in {item.id for item in decision.actions}
                   for action in legal):
                errors.append(f"{decision.id}: legal action not declared")

            chosen = players[actor].choose(view(state, actor), decision,
                                            legal, rng)
            if chosen.id not in legal_ids:
                errors.append(
                    f"{decision.id}: player chose {chosen.id!r}, legal={legal_ids}")

            before_count = len(state.get(HISTORY_KEY, []))
            before_decisions = dict(state.get(RESOLUTIONS_KEY, {}))
            new_state = apply(decision, state, chosen)
            history = new_state.get(HISTORY_KEY)
            if not isinstance(history, list) or len(history) != before_count + 1:
                errors.append(f"{decision.id}: history did not grow by one")
                history = history if isinstance(history, list) else []
            entry = history[-1] if history else {}
            expected_entry = {"decision": decision.id, "action": chosen.id,
                              "actor": expected_actor}
            if entry != expected_entry:
                errors.append(
                    f"{decision.id}: entry {entry!r} != {expected_entry!r}")
            if set(entry) != {"decision", "action", "actor"}:
                errors.append(f"{decision.id}: entry keys {sorted(entry)}")
            if entry.get("actor") not in SIDES:
                errors.append(f"{decision.id}: unknown history actor {entry.get('actor')!r}")
            if entry.get("action") not in legal_ids:
                errors.append(
                    f"{decision.id}: history action {entry.get('action')!r} "
                    f"not in legal {legal_ids}")
            if entry.get("actor") != expected_actor:
                errors.append(
                    f"{decision.id}: history actor {entry.get('actor')!r} "
                    f"!= decision actor {expected_actor!r}")
            if new_state.get(RESOLUTIONS_KEY, {}).get(decision.id) != chosen.id:
                errors.append(f"{decision.id}: resolution does not match chosen action")
            if set(new_state.get(RESOLUTIONS_KEY, {})) != set(before_decisions) | {decision.id}:
                errors.append(f"{decision.id}: resolutions gained or lost keys")
            if legal_actions(decision, new_state):
                errors.append(f"{decision.id}: spent decision still offers actions")

            records.append({
                "decision": decision.id,
                "action": chosen.id,
                "actor": expected_actor,
                "legal": list(legal_ids),
            })
            state = new_state
            steps += 1
            actions_here += 1
            if chosen.id == "end_segment":
                break
            if actions_here > 1000:
                errors.append(f"{decision.id}: segment did not end")
                break
        segments += 1
        if state["stage"] < 3:
            state["stage"] += 1
        else:
            state["stage"] = 1
            state["turn"] += 1

    history = state.get(HISTORY_KEY, [])
    if len(history) != steps:
        errors.append(f"history length {len(history)} != steps {steps}")
    if len(records) != steps:
        errors.append(f"audit record length {len(records)} != steps {steps}")
    for index, (entry, record) in enumerate(zip(history, records)):
        if entry.get("decision") != record["decision"]:
            errors.append(f"history[{index}] decision order mismatch")
        if entry.get("action") != record["action"]:
            errors.append(f"history[{index}] action mismatch")
        if entry.get("actor") != record["actor"]:
            errors.append(f"history[{index}] actor mismatch")
        if entry.get("action") not in record["legal"]:
            errors.append(f"history[{index}] action was not legal at the time")
    decisions = state.get(RESOLUTIONS_KEY, {})
    if set(decisions) != {entry.get("decision") for entry in history}:
        errors.append("resolutions and history decision sets differ")
    if len({entry.get("decision") for entry in history}) != len(history):
        errors.append("duplicate decision id in history")
    actors = {entry.get("actor") for entry in history}
    if actors != set(SIDES):
        errors.append(f"history actors {sorted(actors)} != both sides")

    return {
        "seed": seed,
        "turns": state["turn"] - 1,
        "stages": segments,
        "steps": steps,
        "history_entries": len(history),
        "actors": sorted(actors),
        "legal_checks": steps,
        "actor_checks": steps,
        "state_hash": state_hash(state),
        "errors": errors,
    }


def main() -> int:
    games = []
    errors = 0
    for seed in range(SEEDS):
        try:
            audited = audit_game(seed, TURNS)
            production = run_game(seed, game_turns=TURNS)
            if production.state_hash != audited["state_hash"]:
                audited["errors"].append("audited hash != production hash")
            if production.steps != audited["steps"]:
                audited["errors"].append("audited steps != production steps")
            if production.turns != TURNS:
                audited["errors"].append(
                    f"production turns {production.turns} != {TURNS}")
            if production.stages != audited["stages"]:
                audited["errors"].append("audited stages != production stages")
        except Exception as exc:  # report, never hide a failed game
            audited = {
                "seed": seed, "turns": TURNS, "stages": 0, "steps": 0,
                "history_entries": 0, "actors": [], "legal_checks": 0,
                "actor_checks": 0, "state_hash": "",
                "errors": [f"{type(exc).__name__}: {exc}"],
            }
        games.append(audited)
        errors += len(audited["errors"])

    summary = {
        "scenario": SYNTHETIC_SCENARIO,
        "seeds": SEEDS,
        "turns": TURNS,
        "games": len(games),
        "total_steps": sum(game["steps"] for game in games),
        "total_history_entries": sum(game["history_entries"] for game in games),
        "total_actor_checks": sum(game["actor_checks"] for game in games),
        "total_legal_checks": sum(game["legal_checks"] for game in games),
        "games_with_both_actors": sum(
            game["actors"] == sorted(SIDES) for game in games),
        "games_with_errors": sum(bool(game["errors"]) for game in games),
        "errors": errors,
        "ok": errors == 0,
    }
    report = {"summary": summary, "games": games}
    out = ROOT / "tmp" / "soak-deep-report.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
