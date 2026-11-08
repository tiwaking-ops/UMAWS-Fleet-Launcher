"""Tests for the CNA ruleset combinations."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cna.engine.rulesets import (FULL, LAND_ABSTRACT, LAND_AIR,
                                 LAND_LOGISTICS, RulesetError,
                                 available_rulesets, get_ruleset,
                                 require_available)  # noqa: E402


def test_land_abstract_is_the_only_available_p1_ruleset() -> None:
    assert LAND_ABSTRACT.available is True
    assert available_rulesets() == (LAND_ABSTRACT,)
    assert require_available("land_abstract") is LAND_ABSTRACT


def test_all_four_combinations_are_named() -> None:
    assert get_ruleset("LAND_AIR") is LAND_AIR
    assert get_ruleset("LAND_LOGISTICS") is LAND_LOGISTICS
    assert get_ruleset("FULL") is FULL
    assert FULL.modules == ("land", "air", "logistics")


def test_deferred_combinations_are_refused() -> None:
    for ruleset_id in ("LAND_AIR", "LAND_LOGISTICS", "FULL"):
        with pytest.raises(RulesetError):
            require_available(ruleset_id)


def test_unknown_ruleset_is_refused() -> None:
    with pytest.raises(RulesetError):
        get_ruleset("TOTAL_FANTASY")


def test_active_sections_are_stable_and_deduplicated() -> None:
    assert LAND_ABSTRACT.active_sections() == ("5.2", "32")
    assert FULL.active_sections() == ("5.2/33/48", "58", "47")
