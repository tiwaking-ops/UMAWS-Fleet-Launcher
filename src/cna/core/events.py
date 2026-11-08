"""Append-only game events and deterministic replay.

RULE: none directly; the log records every die roll and action so a game can
be reconstructed from its seed and choices (proposal sections 6.5 and 6.6).

Each event carries the hash of its predecessor.  A replay therefore has both
a state hash and a chain that proves the event list was not silently edited.
The log is deliberately independent of the rules: handlers are supplied by
the caller, and an unknown event is ignored rather than guessed at.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

from cna.state.model import state_hash

GENESIS_HASH = "0" * 64


class EventError(ValueError):
    """The event log or an event handler is malformed."""


def _payload(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise EventError("event payload must be a mapping")
    result = dict(value)
    try:
        json.dumps(result, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise EventError(f"event payload is not JSON-serialisable: {exc}") from exc
    return result


def _digest(seq: int, kind: str, payload: Mapping[str, Any],
            prev_hash: str) -> str:
    material = json.dumps(
        {"seq": seq, "kind": kind, "payload": payload, "prev_hash": prev_hash},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


@dataclass(frozen=True)
class Event:
    """One immutable entry in the game log."""

    seq: int
    kind: str
    payload: Mapping[str, Any]
    prev_hash: str
    hash: str

    @classmethod
    def create(cls, seq: int, kind: str, payload: Mapping[str, Any] | None,
               prev_hash: str) -> "Event":
        if not isinstance(seq, int) or seq < 1:
            raise EventError("event seq must be a positive integer")
        if not isinstance(kind, str) or not kind:
            raise EventError("event kind must be a non-empty string")
        body = _payload(payload)
        return cls(seq, kind, body, prev_hash,
                   _digest(seq, kind, body, prev_hash))

    def to_obj(self) -> dict[str, Any]:
        return {"seq": self.seq, "kind": self.kind, "payload": dict(self.payload),
                "prev_hash": self.prev_hash, "hash": self.hash}

    @classmethod
    def from_obj(cls, obj: Mapping[str, Any]) -> "Event":
        try:
            event = cls(
                seq=int(obj["seq"]),
                kind=str(obj["kind"]),
                payload=dict(obj["payload"]),
                prev_hash=str(obj["prev_hash"]),
                hash=str(obj["hash"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise EventError(f"invalid event object: {exc}") from exc
        expected = _digest(event.seq, event.kind, event.payload, event.prev_hash)
        if event.hash != expected:
            raise EventError(f"event {event.seq} hash does not match its contents")
        return event


@dataclass(frozen=True)
class ChainReport:
    ok: bool
    checked: int
    error: str = ""


@dataclass(frozen=True)
class ReplayResult:
    state: dict[str, Any]
    events: int
    state_hash: str


Handler = Callable[[dict[str, Any], Event], Mapping[str, Any] | None]


class EventLog:
    """An ordered, hash-chained list of events."""

    def __init__(self, events: Iterable[Event] = ()) -> None:
        self._events = list(events)
        report = self.verify()
        if not report.ok:
            raise EventError(report.error)

    @property
    def events(self) -> tuple[Event, ...]:
        return tuple(self._events)

    def __len__(self) -> int:
        return len(self._events)

    def append(self, kind: str, payload: Mapping[str, Any] | None = None,
               **fields: Any) -> Event:
        """Append an event and return it."""
        merged = _payload(payload)
        merged.update(fields)
        prev = self._events[-1].hash if self._events else GENESIS_HASH
        event = Event.create(len(self._events) + 1, kind, merged, prev)
        self._events.append(event)
        return event

    def verify(self) -> ChainReport:
        """Check sequence numbers, links and hashes without changing the log."""
        prev = GENESIS_HASH
        for index, event in enumerate(self._events, start=1):
            if event.seq != index:
                return ChainReport(False, index - 1,
                                   f"event {index} has seq {event.seq}")
            if event.prev_hash != prev:
                return ChainReport(False, index - 1,
                                   f"event {index} does not link to its predecessor")
            expected = _digest(event.seq, event.kind, event.payload, prev)
            if event.hash != expected:
                return ChainReport(False, index - 1,
                                   f"event {index} hash does not match its contents")
            prev = event.hash
        return ChainReport(True, len(self._events))

    def to_jsonl(self) -> str:
        """Serialise the log with one compact JSON object per line."""
        return "".join(
            json.dumps(event.to_obj(), sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False) + "\n"
            for event in self._events
        )

    @classmethod
    def from_jsonl(cls, text: str) -> "EventLog":
        """Parse and verify a JSON-lines log."""
        events = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except ValueError as exc:
                raise EventError(f"line {line_number} is not JSON: {exc}") from exc
            if not isinstance(obj, Mapping):
                raise EventError(f"line {line_number} is not an object")
            events.append(Event.from_obj(obj))
        return cls(events)

    def replay(self, initial: Mapping[str, Any],
               handlers: Mapping[str, Handler] | None = None) -> ReplayResult:
        """Apply known events to *initial* and return the resulting state.

        A handler receives ``(state, event)`` and may return a new mapping or
        ``None`` to leave the state unchanged.  The initial mapping is never
        mutated.  Unknown kinds are skipped deliberately: a replay must not
        invent a rule for an event it does not understand.
        """
        if not isinstance(initial, Mapping):
            raise EventError("initial state must be a mapping")
        working = copy.deepcopy(dict(initial))
        handlers = handlers or {}
        for event in self._events:
            handler = handlers.get(event.kind)
            if handler is None:
                continue
            result = handler(working, event)
            if result is None:
                continue
            if not isinstance(result, Mapping):
                raise EventError(
                    f"handler for {event.kind!r} returned "
                    f"{type(result).__name__}, not a mapping"
                )
            working = copy.deepcopy(dict(result))
        return ReplayResult(working, len(self._events), state_hash(working))
