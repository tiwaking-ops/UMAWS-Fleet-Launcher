"""Tests for the versioned CNA state model."""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cna.state.model import (SCHEMA_VERSION, StateError, canonical_json,
                             decode_rng_state, encode_rng_state, from_json,
                             new_state, state_hash, to_json,
                             validate_state)  # noqa: E402


def test_new_state_is_valid_and_carries_schema_version() -> None:
    state = new_state(42)
    validate_state(state)
    assert state["schema_version"] == SCHEMA_VERSION
    assert state["seed"] == 42
    assert state["turn"] == 1 and state["stage"] == 1
    assert state["sides"]["axis"]["name"] == "Axis"


def test_state_hash_ignores_mapping_insertion_order() -> None:
    first = new_state(1)
    second = dict(reversed(list(first.items())))
    assert canonical_json(first) == canonical_json(second)
    assert state_hash(first) == state_hash(second)


def test_state_hash_changes_when_state_changes() -> None:
    state = new_state(1)
    before = state_hash(state)
    state["turn"] = 2
    assert state_hash(state) != before


def test_save_load_round_trip_is_bit_exact() -> None:
    state = new_state(99, turn=3, stage=2, phase="movement")
    loaded = from_json(to_json(state))
    assert loaded == state
    assert state_hash(loaded) == state_hash(state)


def test_invalid_schema_version_is_refused() -> None:
    state = new_state(1)
    state["schema_version"] = 999
    with pytest.raises(StateError):
        validate_state(state)
    with pytest.raises(StateError):
        from_json(to_json(new_state(1)).replace('"schema_version": 1',
                                                 '"schema_version": 999'))


def test_missing_required_key_is_refused() -> None:
    state = new_state(1)
    del state["units"]
    with pytest.raises(StateError):
        validate_state(state)


def test_rng_state_round_trips() -> None:
    rng = random.Random(2026)
    expected = [rng.randint(1, 6) for _ in range(10)]

    original = random.Random(2026)
    payload = encode_rng_state(original)
    restored = random.Random()
    restored.setstate(decode_rng_state(payload))
    assert [restored.randint(1, 6) for _ in range(10)] == expected


def test_new_state_does_not_share_mutable_sides() -> None:
    first = new_state(1)
    second = new_state(1)
    first["sides"]["axis"]["hand"].append("secret")
    assert second["sides"]["axis"]["hand"] == []
