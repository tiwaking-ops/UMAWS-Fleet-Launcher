"""Failure classification (fleet amendment section 7.5).

The rule that matters: **a classifier pattern may only be added from a
captured fixture.**  Until spike S-A1 (or a live run) captures real failure
output, every non-zero exit is ``UNKNOWN``.

That is not a limitation to apologise for; it is the safety property.  The
``UNKNOWN`` path is the one that has to be safe on its own, because it is the
path that will actually be taken.

Fixtures live under ``tests/fleet/fixtures/<adapter>/``, one file per
failure class, one regular expression per line.  The fake CLI has its own
fixtures, which are **synthetic** — they say what the fake prints, and they
say nothing about any real provider.  A real adapter never reuses them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from pmk.plat import read_text

# The failure classes (fleet amendment section 7.5).
OK = "OK"
QUOTA = "QUOTA"
AUTH = "AUTH"
NETWORK = "NETWORK"
MODEL_GONE = "MODEL_GONE"
STALL = "STALL"
CRASH = "CRASH"
UNKNOWN = "UNKNOWN"

FAILURE_CLASSES = (QUOTA, AUTH, NETWORK, MODEL_GONE, STALL, CRASH, UNKNOWN)

#: The order patterns are tested in.  The first class whose pattern matches
#: wins.  Order matters only in that a more specific class must come before
#: a more general one.
CLASS_ORDER = (QUOTA, AUTH, MODEL_GONE, NETWORK, CRASH)


@dataclass
class PatternBook:
    """The loaded patterns for one adapter."""

    adapter: str
    patterns: dict = field(default_factory=dict)
    fixture_root: Path | None = None

    @property
    def verified(self) -> bool:
        """Are there any patterns at all?

        An adapter with no fixtures classifies every non-zero exit as
        ``UNKNOWN``, which is the safe default.
        """
        return any(self.patterns.values())

    def to_dict(self) -> dict:
        return {"adapter": self.adapter,
                "verified": self.verified,
                "classes": {k: len(v) for k, v in self.patterns.items()}}


def load_book(adapter: str, fixture_root: str | Path | None = None) -> PatternBook:
    """Load the fixture patterns for *adapter*."""
    book = PatternBook(adapter=adapter)
    if fixture_root is None:
        book.patterns = {}
        return book
    root = Path(fixture_root) / adapter
    book.fixture_root = root
    if not root.is_dir():
        return book
    for path in sorted(root.glob("*.txt")):
        # "model-gone.txt" names the MODEL_GONE class.
        failure_class = path.stem.upper().replace("-", "_")
        if failure_class not in FAILURE_CLASSES:
            continue
        compiled = []
        for line in read_text(path).splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                compiled.append(re.compile(line, re.IGNORECASE))
            except re.error:
                # A broken pattern is ignored rather than crashing a worker.
                continue
        if compiled:
            book.patterns[failure_class] = compiled
    return book


def classify(exit_code: int | None, log_tail: str, book: PatternBook) -> str:
    """Classify a process outcome.

    * exit 0 with no signal -> ``OK``
    * a fixture pattern matches -> that class
    * otherwise -> ``UNKNOWN``

    A non-zero exit that matches nothing is ``UNKNOWN``, never ``CRASH``:
    "crash" means a recognised failure, and inventing recognition is how a
    classifier starts lying.
    """
    if exit_code is None:
        # No exit code means the process was killed or is still running.
        # The harness distinguishes stall from kill before calling this.
        return UNKNOWN
    if exit_code == 0:
        return OK
    if not book.verified:
        return UNKNOWN
    text = log_tail or ""
    for failure_class in CLASS_ORDER:
        for pattern in book.patterns.get(failure_class, []):
            try:
                if pattern.search(text):
                    return failure_class
            except re.error:
                continue
    return UNKNOWN
