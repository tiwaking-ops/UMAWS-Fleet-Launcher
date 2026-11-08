"""The CNA game state: a versioned JSON mapping.

RULE: none directly; the model carries the fields the rules need.

The engine deliberately works on ordinary mappings.  This module adds the
parts a file and a replay need: a schema version, canonical JSON, a stable
hash, and a JSON-safe encoding of the RNG state.

The state is not a class on purpose.  Rules and tests can build a small
mapping without importing the whole game, while :func:`validate_state`
still enforces the contract at the persistence boundary.
"""

from __future__ import annotations

import copy
import hashlib
import json
import random
from typing import Any, Mapping

SCHEMA_VERSION = 1

#: Keys every persisted state must have.
REQUIRED_KEYS = (
    "schema_version",
    "seed",
    "turn",
    "stage",
    "phase",
    "actor",
    "sides",
    "units",
    "supplies",
)

SIDES = ("axis", "commonwealth")


class StateError(ValueError):
    """Raised when a state cannot be saved, loaded or validated."""


def _default_sides() -> dict[str, dict[str, Any]]:
    return {
        "axis": {"name": "Axis", "initiative": 0, "hand": []},
        "commonwealth": {"name": "Commonwealth", "initiative": 0, "hand": []},
    }


def _jsonable(value: Any) -> Any:
    """Recursively convert tuples to lists for JSON."""
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


def _tuples(value: Any) -> Any:
    """Recursively convert lists back to tuples for ``Random.setstate``."""
    if isinstance(value, list):
        return tuple(_tuples(item) for item in value)
    return value


def encode_rng_state(rng: random.Random) -> dict[str, Any]:
    """Encode an RNG's complete state as JSON-safe data."""
    version, internal, gauss = rng.getstate()
    return {"version": version, "state": _jsonable(internal), "gauss": gauss}


def decode_rng_state(payload: Mapping[str, Any]) -> tuple[Any, ...]:
    """Decode :func:`encode_rng_state` into ``Random.setstate`` input."""
    if not isinstance(payload, Mapping):
        raise StateError("rng state must be a mapping")
    try:
        return (int(payload["version"]), _tuples(payload["state"]),
                payload.get("gauss"))
    except (KeyError, TypeError, ValueError) as exc:
        raise StateError(f"invalid rng state: {exc}") from exc


def new_state(
    seed: int,
    *,
    turn: int = 1,
    stage: int = 1,
    phase: str = "initiative",
    actor: str = "axis",
    sides: Mapping[str, Any] | None = None,
    units: Mapping[str, Any] | None = None,
    supplies: Mapping[str, Any] | None = None,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Build a fresh, validated game state.

    A fresh state carries the RNG state as well as the seed, so loading it is
    enough to continue an action sequence without replaying every roll.
    """
    if not isinstance(seed, int):
        raise StateError("seed must be an integer")
    if turn < 1:
        raise StateError("turn must be at least 1")
    if stage not in (1, 2, 3):
        raise StateError("stage must be 1, 2 or 3")
    if actor not in SIDES:
        raise StateError(f"unknown actor: {actor!r}")
    rng = rng or random.Random(seed)
    state = {
        "schema_version": SCHEMA_VERSION,
        "seed": seed,
        "turn": turn,
        "stage": stage,
        "phase": str(phase),
        "actor": actor,
        "sides": copy.deepcopy(dict(sides) if sides is not None
                               else _default_sides()),
        "units": copy.deepcopy(dict(units or {})),
        "supplies": copy.deepcopy(dict(supplies or {})),
        "decisions": {},
        "history": [],
        "rng": encode_rng_state(rng),
    }
    validate_state(state)
    return state


def validate_state(state: Mapping[str, Any]) -> None:
    """Raise :class:`StateError` unless *state* satisfies the schema."""
    if not isinstance(state, Mapping):
        raise StateError(f"state must be a mapping, got {type(state).__name__}")
    missing = [key for key in REQUIRED_KEYS if key not in state]
    if missing:
        raise StateError(f"state is missing required keys: {missing}")
    if state["schema_version"] != SCHEMA_VERSION:
        raise StateError(
            f"unsupported schema_version {state['schema_version']!r}; "
            f"expected {SCHEMA_VERSION}"
        )
    if not isinstance(state["seed"], int):
        raise StateError("seed must be an integer")
    if not isinstance(state["turn"], int) or state["turn"] < 1:
        raise StateError("turn must be a positive integer")
    if state["stage"] not in (1, 2, 3):
        raise StateError("stage must be 1, 2 or 3")
    if state["actor"] not in SIDES:
        raise StateError(f"unknown actor: {state['actor']!r}")
    if not isinstance(state["sides"], Mapping):
        raise StateError("sides must be a mapping")
    for side in SIDES:
        if side not in state["sides"]:
            raise StateError(f"sides is missing {side!r}")
    if not isinstance(state["units"], Mapping):
        raise StateError("units must be a mapping")
    if not isinstance(state["supplies"], Mapping):
        raise StateError("supplies must be a mapping")


def canonical_json(state: Mapping[str, Any]) -> str:
    """Stable JSON: sorted keys, compact separators, no NaN."""
    try:
        return json.dumps(
            state,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise StateError(f"state is not canonically serialisable: {exc}") from exc


def state_hash(state: Mapping[str, Any]) -> str:
    """SHA-256 of :func:`canonical_json`."""
    return hashlib.sha256(canonical_json(state).encode("utf-8")).hexdigest()


def to_json(state: Mapping[str, Any], *, indent: int = 2) -> str:
    """Serialise *state* for a save file, with a trailing newline."""
    validate_state(state)
    return json.dumps(state, sort_keys=True, indent=indent,
                      ensure_ascii=False, allow_nan=False) + "\n"


def from_json(text: str) -> dict[str, Any]:
    """Parse and validate a saved state."""
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise StateError(f"invalid state JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise StateError("state JSON must contain an object")
    validate_state(parsed)
    return parsed
