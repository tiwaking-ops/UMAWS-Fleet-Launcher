"""Shared fixtures for the QuotaGate tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT / "src", ROOT / "gateway"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from pmk.clock import FakeClock  # noqa: E402


@pytest.fixture()
def clock() -> FakeClock:
    """A clock the test drives by hand.

    The quota engine's windows are all computed from this, so the DST test
    and the exhaustion drill are deterministic rather than slow.
    """
    return FakeClock(start=__import__("datetime").datetime(
        2026, 10, 22, 12, 0, 0, tzinfo=__import__("datetime").timezone.utc))
