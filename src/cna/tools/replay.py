"""Headless replay: rebuild a state from a JSON-lines event log.

Usage::

    python -m cna.tools.replay --log game.jsonl --initial game.state.json

The current handlers are intentionally empty.  A replay of gameplay passes
the game's handler table to :meth:`EventLog.replay`; this CLI is the safe
mechanical check that the log is intact and the initial state is loadable.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping, Sequence

from cna.core.events import EventLog, Handler
from cna.state.model import from_json, state_hash, to_json


def replay_log(log_path: str | Path, initial: Mapping,
               handlers: Mapping[str, Handler] | None = None):
    """Load *log_path*, replay it over *initial*, and return the result."""
    log = EventLog.from_jsonl(Path(log_path).read_text(encoding="utf-8"))
    return log.replay(initial, handlers)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m cna.tools.replay")
    parser.add_argument("--log", required=True, help="JSON-lines event log")
    parser.add_argument("--initial", required=True, help="initial state JSON")
    parser.add_argument("--out", help="write the final state JSON here")
    args = parser.parse_args(argv)

    initial = from_json(Path(args.initial).read_text(encoding="utf-8"))
    result = replay_log(args.log, initial)
    if args.out:
        Path(args.out).write_text(to_json(result.state), encoding="utf-8")
    print(json.dumps({"ok": True, "events": result.events,
                      "state_hash": result.state_hash}, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
