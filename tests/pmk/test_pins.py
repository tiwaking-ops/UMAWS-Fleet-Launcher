"""Tests for the sentinel's I8' check on a missing pins file."""

from __future__ import annotations

from pathlib import Path

from pmk.sentinel import check


def test_a_missing_pins_file_is_an_i8_breach(kernel):
    """A missing pins file means nothing is pinned, which is a breach.

    It used to report clean, because the check only turned mismatches into
    findings and a missing file has no mismatches.
    """
    pins = kernel.repo.pins_path
    if pins.exists():
        pins.unlink()
    report = check(kernel)
    assert not report["ok"]
    assert any(f["invariant"] == "I8'" for f in report["findings"])


def test_a_modified_pinned_file_is_an_i8_breach(kernel):
    kernel.repo.constitution_path.write_text("# tampered\n", encoding="utf-8")
    report = check(kernel)
    assert not report["ok"]
    assert any(f["invariant"] == "I8'" for f in report["findings"])


def test_a_healthy_repository_is_clean(kernel):
    report = check(kernel)
    assert report["ok"], report["findings"]
