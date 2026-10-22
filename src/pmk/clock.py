"""Kernel time (invariant I7).

I7: *only Kernel timestamps are trusted*.  Every event timestamp comes from
here, never from a worker, a provider or the wall clock of an external
process.  The gateway keeps its own clock for quota resets but marks its
timestamps non-authoritative, and the Kernel re-stamps on ingest.

The clock is injectable so that the DST test (pilot v1 acceptance test Q1,
across the US daylight-saving change on 1 November 2026) and the quota
exhaustion drill (Q3) can move time deliberately instead of waiting.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    """The current time, as an aware UTC datetime."""
    return datetime.now(timezone.utc)


def to_iso(moment: datetime) -> str:
    """Format as ``YYYY-MM-DDTHH:MM:SSZ`` (the event-log timestamp format)."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text: str) -> datetime:
    """Parse an event-log timestamp back into an aware UTC datetime."""
    cleaned = text.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    parsed = datetime.fromisoformat(cleaned)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class Clock:
    """A source of Kernel time.  The default is the system clock."""

    def now(self) -> datetime:
        return utc_now()

    def now_iso(self) -> str:
        return to_iso(self.now())

    def monotonic(self) -> float:
        """A monotonic reading, for timeouts and deadlines.

        Deliberately separate from :meth:`now`: a wall-clock jump must not be
        able to make a lease look younger or older than it is.
        """
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class FakeClock(Clock):
    """A clock the tests drive by hand."""

    def __init__(self, start: datetime | None = None):
        self._now = start or datetime(2026, 10, 22, 12, 0, 0, tzinfo=timezone.utc)
        self._mono = 1000.0

    def now(self) -> datetime:
        return self._now

    def monotonic(self) -> float:
        return self._mono

    def advance(self, seconds: float) -> datetime:
        self._now = self._now + timedelta(seconds=seconds)
        self._mono += seconds
        return self._now

    def set(self, moment: datetime) -> datetime:
        self._now = moment
        return self._now
