"""The append-only, hash-chained event log (pilot v1 section 9).

This is the coordination authority.  Everything else — task cards, leases,
views, the briefing — is a projection of this log (invariant I13).

Properties:

* **Append only.**  Nothing rewrites a committed event.
* **Hash chained.**  Each event carries the hash of its predecessor, so any
  edit to history breaks the chain at that point (invariant I1).
* **Durable.**  Every append is flushed and fsynced before the call returns.
* **Repairable at the tail only.**  A record truncated mid-write is
  discarded and the repair is logged.  A record damaged in the *middle* is
  an I1 breach, not something to paper over.

Event files are split by day: ``.pm/events/YYYY-MM-DD.jsonl``.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from .clock import Clock, to_iso
from .store import Repo

#: The hash of the (empty) genesis event.
GENESIS_HASH = "0" * 64

KERNEL_VERSION = "0.1.0"

#: Base event types (pilot v1 section 9) plus the fleet amendment's
#: additions (section 12.H).  Unknown types are accepted: the log is a
#: forward-compatible record, and a newer component must be able to write
#: into an older log.
KNOWN_EVENT_TYPES = frozenset({
    # --- base ---------------------------------------------------------
    "TASK_CREATED", "TASK_ADMITTED", "TASK_VOIDED", "TASK_REWORKED",
    "TASK_READY", "TASK_BLOCKED", "TASK_DONE",
    "CLAIMED", "RENEWED", "REVOKED", "SUBMITTED", "VERIFIED",
    "INTEGRATING", "INTEGRATED", "QUARANTINED", "PREMISE_REFUTED",
    "ORACLE_RESULT", "SCOPE_VIOLATION",
    "BRIEFING_GENERATED", "VIEWS_REGENERATED", "SENTINEL_RUN",
    "INCIDENT", "QUEUE_ITEM", "QUEUE_DECIDED", "PINS_CHECKED",
    "BOOTSTRAP_IMPORTED", "TOKEN_ISSUED", "GATEWAY_INGESTED",
    "CONTEXT_SYNCED", "CONTEXT_SYNC_NOOP", "CONTEXT_SYNC_REJECTED",
    "CONTEXT_REVERTED", "LOG_TAIL_REPAIRED",
    # --- fleet (amendment section 12.H) --------------------------------
    "PROJECT_STATE", "PDD_COMMITTED",
    "FLEET_ASSIGNED", "AGENT_STARTED", "AGENT_EXITED", "AGENT_FAILED",
    "AGENT_RESUMED", "FIX_ROUND",
    "PROFILE_COOLING", "PROFILE_RECOVERED", "PROFILE_DISABLED", "PROFILE_ENABLED",
    "DISPATCH_PAUSED", "DISPATCH_RESUMED",
    "OVERSEER_WOKEN", "MANUAL_LAUNCH", "RECONCILED",
    # Provenance: which model actually served a lease (D-43).  A fact about
    # the request, not a guess about the model string, so it can outrank a
    # declared family when D-L12 decides who may verify.
    "MODEL_SERVED",
})


def canonical_json(obj: Any) -> str:
    """The one serialization used for hashing.

    Sorted keys, no insignificant whitespace, non-ASCII preserved as
    itself.  Two processes must produce byte-identical output for the same
    logical event or the chain breaks.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def compute_hash(prev_hash: str, body: dict) -> str:
    """Hash an event body against its predecessor's hash."""
    payload = prev_hash + "\n" + canonical_json(body)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Actor:
    """Who did it (pilot v1 section 9.2)."""

    kind: str                    # human | overseer | worker | kernel | system
    agent: str = ""
    model: str = ""
    session: str = ""
    role: str = ""

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "agent": self.agent,
            "model": self.model,
            "session": self.session,
            "role": self.role,
        }

    @classmethod
    def from_dict(cls, obj: dict | None) -> "Actor":
        obj = obj or {}
        return cls(
            kind=str(obj.get("kind", "kernel")),
            agent=str(obj.get("agent", "")),
            model=str(obj.get("model", "")),
            session=str(obj.get("session", "")),
            role=str(obj.get("role", "")),
        )

    @classmethod
    def kernel(cls) -> "Actor":
        return cls(kind="kernel", role="kernel")

    @classmethod
    def human(cls, name: str = "operator") -> "Actor":
        return cls(kind="human", agent=name, role="supervisor")


@dataclass(frozen=True)
class Event:
    """One record in the log."""

    seq: int
    ts: str
    type: str
    actor: Actor
    prev_hash: str
    hash: str
    subject: str | None = None
    fence: int | None = None
    payload: dict = field(default_factory=dict)
    policy_hash: str = ""
    kernel_version: str = KERNEL_VERSION

    def body(self) -> dict:
        """The hashed part of the event (everything except ``hash``)."""
        return {
            "seq": self.seq,
            "prev_hash": self.prev_hash,
            "ts": self.ts,
            "actor": self.actor.to_dict(),
            "type": self.type,
            "subject": self.subject,
            "fence": self.fence,
            "payload": self.payload,
            "policy_hash": self.policy_hash,
            "kernel_version": self.kernel_version,
        }

    def to_obj(self) -> dict:
        obj = self.body()
        obj["hash"] = self.hash
        return obj

    def to_json(self) -> str:
        return canonical_json(self.to_obj())

    @classmethod
    def from_obj(cls, obj: dict) -> "Event":
        return cls(
            seq=int(obj["seq"]),
            ts=str(obj["ts"]),
            type=str(obj["type"]),
            actor=Actor.from_dict(obj.get("actor")),
            prev_hash=str(obj.get("prev_hash", "")),
            hash=str(obj.get("hash", "")),
            subject=obj.get("subject"),
            fence=obj.get("fence"),
            payload=obj.get("payload") or {},
            policy_hash=str(obj.get("policy_hash", "")),
            kernel_version=str(obj.get("kernel_version", KERNEL_VERSION)),
        )


@dataclass
class ChainReport:
    """The result of verifying the chain (invariant I1)."""

    ok: bool
    checked: int
    first_break_seq: int | None = None
    first_break_reason: str = ""
    repairs: list[str] = field(default_factory=list)

    def summary(self) -> str:
        if self.ok:
            return f"I1 chain verifies ({self.checked} events)"
        return (f"I1 BROKEN at seq {self.first_break_seq}: "
                f"{self.first_break_reason}")


class EventLog:
    """Reads and appends to ``.pm/events/``."""

    def __init__(self, repo: Repo, clock: Clock | None = None,
                 kernel_version: str = KERNEL_VERSION):
        self.repo = repo
        self.clock = clock or Clock()
        self.kernel_version = kernel_version

    # -- paths ------------------------------------------------------------
    def files(self) -> list[Path]:
        if not self.repo.events_dir.is_dir():
            return []
        return sorted(self.repo.events_dir.glob("*.jsonl"))

    def file_for(self, moment_iso: str) -> Path:
        return self.repo.events_dir / f"{moment_iso[:10]}.jsonl"

    # -- reading ----------------------------------------------------------
    def _read_raw(self) -> Iterator[tuple[Path, str, bool]]:
        """Yield ``(path, line, is_torn)`` for every line in every file.

        A torn line is one that was not terminated by a newline: the writer
        died part-way through it.
        """
        for path in self.files():
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            if not raw:
                continue
            chunks = raw.split(b"\n")
            trailing = chunks.pop()          # text after the last newline
            for chunk in chunks:
                yield path, chunk.decode("utf-8", errors="replace"), False
            if trailing:
                yield path, trailing.decode("utf-8", errors="replace"), True

    def read_all(self, *, repair: bool = True) -> tuple[list[Event], list[str]]:
        """Read every event, repairing a torn tail if there is one.

        Returns ``(events, repairs)``.  *repairs* describes what was
        discarded, so the caller can log it (pilot v1 WP2 exit test: "restart
        repairs by discarding the torn tail, logs it").
        """
        events: list[Event] = []
        repairs: list[str] = []
        pending_torn: str | None = None

        for path, line, torn in self._read_raw():
            if torn:
                pending_torn = f"{path.name}: unterminated final record ({len(line)} bytes)"
                continue
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                # A malformed record that is not the last one is a real
                # corruption.  Only a tail is repairable.
                if self._is_last_complete(path, line):
                    pending_torn = f"{path.name}: malformed final record ({exc.msg})"
                    continue
                raise LogCorruption(f"{path.name}: malformed record: {exc}") from exc
            try:
                event = Event.from_obj(obj)
            except (KeyError, TypeError, ValueError) as exc:
                if self._is_last_complete(path, line):
                    pending_torn = f"{path.name}: incomplete final record ({exc})"
                    continue
                raise LogCorruption(f"{path.name}: incomplete record: {exc}") from exc
            events.append(event)

        if pending_torn is not None:
            repairs.append(pending_torn)
            if repair:
                self._discard_torn_tail()
        return events, repairs

    def _is_last_complete(self, path: Path, line: str) -> bool:
        """True when *line* is the final complete record of *path*."""
        try:
            raw = path.read_bytes()
        except OSError:
            return False
        if not raw.endswith(b"\n"):
            return False
        tail = raw.rstrip(b"\n").split(b"\n")[-1]
        return tail.decode("utf-8", errors="replace") == line

    def _discard_torn_tail(self) -> None:
        """Drop any trailing bytes that do not form a complete record."""
        for path in self.files():
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            if not raw:
                continue
            if raw.endswith(b"\n"):
                continue
            # Keep only the complete lines.
            kept = raw.split(b"\n")[:-1]
            with open(path, "wb") as fh:
                fh.write(b"\n".join(kept) + (b"\n" if kept else b""))
                fh.flush()
                os.fsync(fh.fileno())

    def tail(self, count: int = 50) -> list[Event]:
        events, _ = self.read_all(repair=False)
        return events[-count:]

    # -- writing ----------------------------------------------------------
    def append(self, event_type: str, *, actor: Actor | None = None,
               subject: str | None = None, fence: int | None = None,
               payload: dict | None = None,
               policy_hash: str = "") -> Event:
        """Append one event.  The caller must already hold the log lock."""
        events, _ = self.read_all(repair=True)
        prev = events[-1] if events else None
        prev_hash = prev.hash if prev else GENESIS_HASH
        seq = (prev.seq + 1) if prev else 1

        body = {
            "seq": seq,
            "prev_hash": prev_hash,
            "ts": self.clock.now_iso(),
            "actor": (actor or Actor.kernel()).to_dict(),
            "type": event_type,
            "subject": subject,
            "fence": fence,
            "payload": payload or {},
            "policy_hash": policy_hash,
            "kernel_version": self.kernel_version,
        }
        digest = compute_hash(prev_hash, body)
        event = Event(hash=digest, **{
            "seq": body["seq"], "ts": body["ts"], "type": body["type"],
            "actor": Actor.from_dict(body["actor"]),
            "prev_hash": body["prev_hash"], "subject": body["subject"],
            "fence": body["fence"], "payload": body["payload"],
            "policy_hash": body["policy_hash"],
            "kernel_version": body["kernel_version"],
        })

        path = self.file_for(event.ts)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(event.to_json() + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return event

    # -- verification -----------------------------------------------------
    def verify(self) -> ChainReport:
        """Check the chain (invariant I1).

        Also reports a torn tail as a repair rather than a breach, because a
        torn tail is expected after a crash and is not evidence of tampering.
        """
        events, repairs = self.read_all(repair=True)
        prev_hash = GENESIS_HASH
        expected_seq = 1
        for event in events:
            if event.seq != expected_seq:
                return ChainReport(
                    ok=False, checked=expected_seq - 1,
                    first_break_seq=event.seq,
                    first_break_reason=f"sequence gap: expected {expected_seq}",
                    repairs=repairs)
            if event.prev_hash != prev_hash:
                return ChainReport(
                    ok=False, checked=expected_seq - 1,
                    first_break_seq=event.seq,
                    first_break_reason="prev_hash does not match the previous event",
                    repairs=repairs)
            expected = compute_hash(event.prev_hash, event.body())
            if expected != event.hash:
                return ChainReport(
                    ok=False, checked=expected_seq - 1,
                    first_break_seq=event.seq,
                    first_break_reason="event hash does not match its content",
                    repairs=repairs)
            prev_hash = event.hash
            expected_seq += 1
        return ChainReport(ok=True, checked=len(events), repairs=repairs)


class LogCorruption(RuntimeError):
    """Raised when the log is damaged somewhere other than its tail."""


def events_of_type(events: list[Event], event_type: str) -> list[Event]:
    return [e for e in events if e.type == event_type]


def latest_of_type(events: list[Event], event_type: str,
                   subject: str | None = None) -> Event | None:
    for event in reversed(events):
        if event.type == event_type and (subject is None or event.subject == subject):
            return event
    return None
