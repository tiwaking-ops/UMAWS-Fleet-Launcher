"""Unit tests for the decision-record reconciliation report (S4)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import decision_reconcile as dr  # noqa: E402


def test_parse_decisions_reads_the_entry_ids():
    text = "# log\n\nD-01 | a | b\nD-02 | c | d\nD-02 | duplicate\nD-04 | e | f\n"

    numbers = dr.parse_decisions(text)

    assert numbers == [1, 2, 2, 4]


def test_duplicates_and_missing_ids():
    numbers = [1, 2, 2, 4]

    assert dr.duplicate_ids(numbers) == [2]
    assert dr.missing_ids(numbers) == [3]


def test_missing_ids_empty_sequence():
    assert dr.missing_ids([]) == []


def test_render_names_the_gap():
    report = dr.render(
        [1, 2], [2], [],
        [{"commit": "abc1234", "subject": "policy change",
          "files": [".pm/policy.toml"]}])

    assert "duplicate ids: [2]" in report
    assert "`abc1234`" in report
    assert "1" in report
