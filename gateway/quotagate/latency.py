"""Live response-time capture (min / max) per deployment.

Why these two numbers: reliability judgement.  A deployment that used to
answer in 200 ms and now takes 8 s is sick, and the fastest and slowest
observations are enough to see it without a time-series database.

The two fields are **sentinel-initialised** for "not yet measured" and mean
opposite things, which is the whole reason they are separate:

* ``response_time_min_ms = 0``        - the floor.  No latency can be lower,
  so 0 is the natural "nothing observed yet".
* ``response_time_max_ms = 900000``   - 15 minutes, the ceiling.  There is no
  natural ceiling, so a practical one stands in for "nothing observed yet".

The first observation sets both.  Afterwards the minimum can only fall and
the maximum can only rise, so updates become rarer over time - exactly the
"updated rarely" behaviour wanted for the maximum.

Values are milliseconds.
"""

from __future__ import annotations

import threading

#: "No minimum observed yet."  The floor, so nothing can beat it.
MIN_UNSET = 0

#: "No maximum observed yet."  Fifteen minutes: no real response is slower,
#: so the first observation always replaces it rather than losing to it.
MAX_UNSET = 15 * 60 * 1000


def observe_ns(cursor: "LatencyCursor", elapsed_ms: int) -> None:
    """Record one observation under a cursor's own lock."""
    cursor.min_ms, cursor.max_ms = update(
        cursor.min_ms, cursor.max_ms, elapsed_ms)


def update(min_ms: int, max_ms: int, elapsed_ms: int) -> tuple[int, int]:
    """Fold one observation into a (min, max) pair.

    Pure, so it is testable without any thread or process:

    >>> update(0, MAX_UNSET, 300)
    (300, 300)
    >>> update(300, 300, 200)
    (200, 300)
    >>> update(200, 300, 400)
    (200, 400)
    >>> update(0, MAX_UNSET, 20)
    (20, 20)
    """
    if elapsed_ms < 0:
        raise ValueError("elapsed_ms must not be negative")

    # The sentinels mean "unset", so the first observation replaces them
    # rather than being clamped by them.
    new_min = elapsed_ms if min_ms == MIN_UNSET else min(min_ms, elapsed_ms)
    new_max = elapsed_ms if max_ms == MAX_UNSET else max(max_ms, elapsed_ms)
    return new_min, new_max


class LatencyCursor:
    """The mutable (min, max) pair for one deployment.

    A deployment's config entry is a frozen dataclass shared by every
    request, so the observed pair cannot live on it.  This cursor is the
    per-deployment mutable slice; ``reflect_into`` copies it back onto the
    config when the config is written out.
    """

    __slots__ = ("min_ms", "max_ms", "lock")

    def __init__(self, min_ms: int = MIN_UNSET, max_ms: int = MAX_UNSET):
        self.min_ms = min_ms
        self.max_ms = max_ms
        self.lock = threading.Lock()

    def observe(self, elapsed_ms: int) -> None:
        with self.lock:
            observe_ns(self, elapsed_ms)

    def to_dict(self) -> dict:
        return {"response_time_min_ms": self.min_ms,
                "response_time_max_ms": self.max_ms}

    @classmethod
    def from_deployment(cls, deployment) -> "LatencyCursor":
        """Seed a cursor from a deployment's current config values."""
        return cls(
            min_ms=getattr(deployment, "response_time_min_ms", MIN_UNSET),
            max_ms=getattr(deployment, "response_time_max_ms", MAX_UNSET))


class LatencyLedger:
    """Every deployment's cursor, and the words to describe them."""

    def __init__(self):
        self._cursors: dict[str, LatencyCursor] = {}
        self._lock = threading.Lock()

    def cursor(self, deployment_id: str, deployment=None) -> LatencyCursor:
        with self._lock:
            found = self._cursors.get(deployment_id)
            if found is None:
                found = (LatencyCursor.from_deployment(deployment)
                         if deployment is not None else LatencyCursor())
                self._cursors[deployment_id] = found
            return found

    def observe(self, deployment_id: str, elapsed_ms: int,
                deployment=None) -> LatencyCursor:
        self.cursor(deployment_id, deployment).observe(elapsed_ms)
        return self._cursors[deployment_id]

    def to_dict(self) -> dict:
        with self._lock:
            return {name: cur.to_dict()
                    for name, cur in sorted(self._cursors.items())}

    def summary(self, deployment_id: str) -> str:
        """A human sentence, for logs and the availability endpoint."""
        cur = self._cursors.get(deployment_id)
        if cur is None or cur.min_ms == MIN_UNSET:
            return "not yet measured"
        return f"min {cur.min_ms} ms, max {cur.max_ms} ms"
