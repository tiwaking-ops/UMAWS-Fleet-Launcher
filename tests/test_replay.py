"""Tests for the append-only event log and replay."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cna.core.events import (GENESIS_HASH, EventError, EventLog)  # noqa: E402
from cna.state.model import new_state, state_hash  # noqa: E402


def test_log_starts_at_genesis_and_chains() -> None:
    log = EventLog()
    first = log.append("ROLL", {"value": 42})
    second = log.append("MOVE", unit="A", hex="C4218")
    assert first.seq == 1 and first.prev_hash == GENESIS_HASH
    assert second.seq == 2 and second.prev_hash == first.hash
    assert log.verify().ok is True
    assert len(log) == 2


def test_tampering_with_a_payload_breaks_the_chain() -> None:
    log = EventLog()
    log.append("ROLL", {"value": 42})
    event = log.events[0]
    tampered = type(event)(event.seq, event.kind, {"value": 43},
                           event.prev_hash, event.hash)
    broken = EventLog.__new__(EventLog)
    broken._events = [tampered]
    report = broken.verify()
    assert report.ok is False
    assert "hash" in report.error


def test_jsonl_round_trip_preserves_the_chain() -> None:
    log = EventLog()
    log.append("SEED", {"seed": 7})
    log.append("ACTION", {"id": "end_segment"})
    loaded = EventLog.from_jsonl(log.to_jsonl())
    assert loaded.events == log.events
    assert loaded.to_jsonl() == log.to_jsonl()


def test_jsonl_rejects_a_tampered_line() -> None:
    log = EventLog()
    log.append("ROLL", {"value": 42})
    text = log.to_jsonl().replace('"value":42', '"value":43')
    with pytest.raises(EventError):
        EventLog.from_jsonl(text)


def test_replay_is_deterministic_and_does_not_mutate_the_initial_state() -> None:
    initial = new_state(3)
    witness = copy.deepcopy(initial)
    log = EventLog()
    log.append("ADD", amount=2)
    log.append("ADD", amount=5)

    def add(state, event):
        return {**state, "total": state.get("total", 0) + event.payload["amount"]}

    first = log.replay(initial, {"ADD": add})
    second = log.replay(initial, {"ADD": add})
    assert initial == witness
    assert first.state["total"] == 7
    assert state_hash(first.state) == first.state_hash
    assert first.state_hash == second.state_hash


def test_unknown_events_are_ignored() -> None:
    initial = new_state(1)
    log = EventLog()
    log.append("NOT_IMPLEMENTED", {"x": 1})
    result = log.replay(initial)
    assert result.state == initial
    assert result.events == 1


def test_a_handler_must_return_a_mapping() -> None:
    log = EventLog()
    log.append("BAD", {})
    with pytest.raises(EventError):
        log.replay(new_state(1), {"BAD": lambda state, event: 42})
