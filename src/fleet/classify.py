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

from pmk.plat import read_text as plat_read_text

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
    """Load the classifier patterns for *adapter*.

    A pattern lives in ``patterns.toml`` beside the evidence, and each
    pattern names the captured file it was derived from::

        [quota]
        pattern = "Rate limit exceeded"
        source  = "quota.txt"

    **A pattern is only loaded if it actually matches its source file.**
    That is the mechanical form of fleet rule 15 — *"a classifier pattern
    may only be added from a captured fixture"* — and it means a pattern
    cannot exist without evidence that supports it.  A pattern that
    matches nothing is not loaded, and the adapter falls back to
    ``UNKNOWN``, which is the safe class.

    The captured files themselves are evidence and are never parsed as
    regular expressions.
    """
    book = PatternBook(adapter=adapter)
    if fixture_root is None:
        return book
    root = Path(fixture_root) / adapter
    book.fixture_root = root
    patterns_file = root / "patterns.toml"
    if not patterns_file.is_file():
        return book

    try:
        import tomllib
        data = tomllib.loads(plat_read_text(patterns_file))
    except (OSError, ValueError):
        return book

    for failure_class, entry in (data or {}).items():
        if not isinstance(entry, dict):
            continue
        name = str(failure_class).upper().replace("-", "_")
        if name not in FAILURE_CLASSES:
            continue
        pattern_text = str(entry.get("pattern", "")).strip()
        source = str(entry.get("source", "")).strip()
        if not pattern_text or not source:
            continue
        source_path = root / source
        if not source_path.is_file():
            # A pattern with no evidence is not loaded.
            continue
        try:
            compiled = re.compile(pattern_text, re.IGNORECASE)
        except re.error:
            continue
        try:
            evidence = plat_read_text(source_path)
        except OSError:
            continue
        if not compiled.search(evidence):
            # The pattern does not match the capture it claims to come
            # from.  It is not loaded.
            continue
        book.patterns[name] = [compiled]
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
