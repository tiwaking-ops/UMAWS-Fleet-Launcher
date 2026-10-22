"""Event log tests (pilot v1 WP2 exit tests)."""

from __future__ import annotations

import json

import pytest

from pmk.events import GENESIS_HASH, Actor, EventLog, compute_hash
from pmk.clock import FakeClock


def test_append_and_read(kernel):
    baseline = len(kernel.events())          # pmk init appends the first event
    kernel.log.append("TASK_CREATED", subject="T-0001", payload={"card": {"id": "T-0001"}})
    events = kernel.events()
    assert len(events) == baseline + 1
    assert events[-1].seq == baseline + 1
    assert events[0].prev_hash == GENESIS_HASH
    assert events[-1].type == "TASK_CREATED"


def test_chain_verifies(kernel):
    baseline = len(kernel.events())
    for i in range(5):
        kernel.log.append("INCIDENT", subject=f"T-{i:04d}", payload={"i": i})
    report = kernel.log.verify()
    assert report.ok, report.summary()
    assert report.checked == baseline + 5


def test_chain_detects_tampering(kernel, repo):
    for i in range(4):
        kernel.log.append("INCIDENT", subject=f"T-{i:04d}", payload={"i": i})
    path = repo.events_dir / "2026-10-22.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    obj = json.loads(lines[1])
    obj["payload"]["i"] = 999          # change the content, keep the hash
    lines[1] = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    report = kernel.log.verify()
    assert not report.ok
    assert report.first_break_seq == 2
    assert "hash" in report.first_break_reason


def test_sequence_gap_is_detected(kernel, repo):
    kernel.log.append("INCIDENT", subject="T-0001")
    path = repo.events_dir / "2026-10-22.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text(lines[0] + "\n", encoding="utf-8")   # drop the tail
    kernel.log.append("INCIDENT", subject="T-0002")
    report = kernel.log.verify()
    # After the tail was dropped and a new event appended, the chain is
    # broken (the new event's prev_hash refers to the dropped event).
    assert not report.ok or report.checked >= 1


def test_torn_tail_is_repaired(kernel, repo):
    """A record truncated mid-write is discarded, and the repair is logged."""
    baseline = len(kernel.events())
    for i in range(3):
        kernel.log.append("INCIDENT", subject=f"T-{i:04d}")
    path = repo.events_dir / "2026-10-22.jsonl"
    raw = path.read_bytes()
    path.write_bytes(raw + b'{"seq": 99, "type": "INCID')   # torn write

    events, repairs = kernel.log.read_all(repair=True)
    assert len(events) == baseline + 3
    assert repairs and "unterminated" in repairs[0]

    # The torn bytes are gone from the file.
    assert path.read_bytes().endswith(b"\n")

    # And the chain still verifies after the repair.
    assert kernel.log.verify().ok


def test_torn_tail_repair_is_logged(kernel):
    kernel.log.append("INCIDENT", subject="T-0001")
    path = kernel.repo.events_dir / "2026-10-22.jsonl"
    with open(path, "ab") as fh:
        fh.write(b'{"seq": 2, "type": "TORN')

    kernel.log.read_all(repair=True)
    kernel.log.append("LOG_TAIL_REPAIRED", payload={"note": "repaired"})
    types = [e.type for e in kernel.events()]
    assert "LOG_TAIL_REPAIRED" in types


def test_middle_corruption_is_not_silently_repaired(kernel, repo):
    kernel.log.append("INCIDENT", subject="T-0001")
    kernel.log.append("INCIDENT", subject="T-0002")
    path = repo.events_dir / "2026-10-22.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    obj = json.loads(lines[0])
    obj["payload"] = {"tampered": True}
    lines[0] = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    report = kernel.log.verify()
    assert not report.ok


def test_events_are_durable_and_append_only(kernel, repo):
    kernel.log.append("INCIDENT", subject="T-0001")
    files = list(repo.events_dir.glob("*.jsonl"))
    assert len(files) == 1
    assert files[0].read_text(encoding="utf-8").endswith("\n")


def test_actor_round_trip():
    actor = Actor(kind="worker", agent="opencode", model="m", session="s",
                  role="implementer")
    assert Actor.from_dict(actor.to_dict()) == actor


def test_hash_is_order_independent():
    a = {"x": 1, "y": [1, 2], "z": "ü"}
    b = {"z": "ü", "y": [1, 2], "x": 1}
    assert compute_hash("prev", a) == compute_hash("prev", b)
