"""The release-status note must keep the two completion scopes separate."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTE = ROOT / "docs" / "release-status.md"
PDD = ROOT / "docs" / "PDD.md"
COVERAGE = ROOT / "coverage" / "rules_coverage.json"


def _note() -> str:
    return NOTE.read_text(encoding="utf-8")


def test_note_separates_the_pdd_release_from_the_full_product():
    text = _note()
    assert "PDD-scoped release" in text
    assert "G-001" in text and "G-002" in text
    assert "full product" in text.lower()
    assert "incomplete" in text.lower()
    assert "close-check" in text


def test_note_links_the_phase_plan_and_data_gap_register():
    text = _note()
    for path in (
        "docs/PDD.md",
        "docs/plans/cna-p1b-p4-implementation-plan.md",
        "docs/plans/cna-p1b-p4-case-backlog.csv",
        "docs/data-gaps.md",
        "coverage/rules_coverage.json",
    ):
        assert path in text


def test_note_does_not_claim_full_product_completion():
    text = _note().lower()
    for claim in (
        "the project is complete",
        "the full product is complete",
        "the full proposal is complete",
        "all rules are implemented",
    ):
        assert claim not in text

    counts = json.loads(COVERAGE.read_text(encoding="utf-8-sig"))["counts"]
    assert counts["cases_unimplemented"] + counts["cases_partial"] > 0


def test_pdd_still_records_the_released_scope():
    pdd = PDD.read_text(encoding="utf-8")
    assert "released (G-001/G-002)" in pdd
