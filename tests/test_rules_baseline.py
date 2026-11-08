"""The generated CNA artifacts must match a reviewed baseline exactly.

The old oracles asserted ``documents >= 66`` and nothing else, so an index
with 413 duplicate-anchor warnings and 15 unresolved xrefs passed silently
(report §6.1).  These tests pin *sets*, not counts: adding a warning fails,
and removing one also fails until the baseline is updated in the same commit,
so the change is reviewed rather than absorbed.

The two unit tests at the bottom cover the generator defects that produced
most of that noise: the same anchor registered twice on one line, and a
coverage scan that only looked at top-level ``.md`` files.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cna.tools import coverage as cov  # noqa: E402
from cna.tools.rules_index import index_bytes  # noqa: E402

INDEX = ROOT / "docs" / "rules" / "index.json"
BASELINE = ROOT / "docs" / "rules" / "index.baseline.json"
COVERAGE = ROOT / "coverage" / "rules_coverage.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_index_matches_the_pinned_baseline():
    index = _load(INDEX)
    expect = _load(BASELINE)["expect"]
    warnings = index["warnings"]

    assert index["stats"]["documents"] == expect["documents"]

    within = [w for w in warnings if "duplicate anchor" in w and "kept, line" in w]
    assert within == [], within[:5]

    cross = sorted({
        re.search(r"duplicate anchor '([^']+)'", w).group(1)
        for w in warnings
        if "duplicate anchor" in w and "already defined at" in w
    })
    assert cross == expect["cross_document_duplicate_anchors"]

    unresolved = []
    for warning in warnings:
        match = re.match(r"unresolved xref '([^']+)' at ([^:]+):(\d+)$", warning)
        if match:
            unresolved.append({"target": match.group(1),
                               "document": match.group(2),
                               "line": int(match.group(3))})
    assert unresolved == expect["unresolved_xrefs"]

    assert index["stats"]["tables"] == expect["tables"]


def test_coverage_accounts_for_the_whole_corpus():
    counts = _load(COVERAGE)["counts"]
    assert counts["rule_files"] >= 66, counts
    assert counts["rule_files_declaring_paths"] >= 1, counts


def test_an_explicit_anchor_and_its_heading_do_not_warn():
    """One line, two scanners, one anchor: the 382-warning false positive."""
    document = index_bytes(b"[#3_2]\n=== Supply\n", name="x.adoc")
    assert document["warnings"] == []
    assert [a["id"] for a in document["anchors"]].count("3_2") == 1


def test_two_real_definitions_on_different_lines_still_warn():
    """The same-line exemption must not hide a genuine second definition."""
    document = index_bytes(
        b"# First {#dup}\n\n# Second {#dup}\n", name="y.md")
    assert any("duplicate anchor 'dup'" in w for w in document["warnings"])


def test_adoc_files_in_subdirectories_count_as_rule_files(tmp_path):
    rules = tmp_path / "rules"
    (rules / "sections").mkdir(parents=True)
    for i in range(3):
        (rules / "sections" / f"s{i}.adoc").write_text(
            "---\npaths:\n  - src/a.py\n---\n", encoding="utf-8")
    (rules / "README.md").write_text("# corpus\n", encoding="utf-8")

    report = cov.build_coverage(rules, ["src/a.py"])

    assert report["counts"]["rule_files"] == 4
    assert report["counts"]["rule_files_declaring_paths"] == 3
    assert report["counts"]["rule_files_matching"] == 3
    assert "sections/s0.adoc" in {r["file"] for r in report["rules"]}
