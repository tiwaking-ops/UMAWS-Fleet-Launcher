"""Tests for the CNA rules indexer (``src/cna/tools/rules_index.py``).

The indexer turns the vendored rules corpus into a deterministic JSON index of
sections, anchors, cross-references and tables.  These tests pin that contract:

* headings become a section tree with outline numbers and 1-based lines;
* an id becomes an **anchor** only where it is defined, and an **xref**
  everywhere else;
* xrefs are resolved corpus-wide against the anchor registry;
* nothing inside a fenced code block is indexed;
* the output is byte-stable and written atomically.

Every test builds its own corpus under ``tmp_path``; nothing here depends on,
or writes to, the repository's own ``docs/rules/``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cna.tools.rules_index import (  # noqa: E402
    RulesIndexError,
    build_index,
    dumps_index,
    index_bytes,
    load_index,
    main,
    write_index,
)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _write(path: Path, text: str) -> Path:
    """Write ``text`` as UTF-8 with LF endings so line numbers are predictable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.lstrip("\n").encode("utf-8"))
    return path


@pytest.fixture()
def rules(tmp_path: Path):
    """Factory: a throwaway rules directory built from {name: markdown}."""

    def _rules(files: dict[str, str]) -> Path:
        root = tmp_path / "rules"
        for name, text in files.items():
            _write(root / name, text)
        return root

    return _rules


def _ids(document: dict) -> list[str]:
    return [anchor["id"] for anchor in document["anchors"]]


def _kinds(document: dict, kind: str) -> list[dict]:
    return [anchor for anchor in document["anchors"] if anchor["kind"] == kind]


# --------------------------------------------------------------------------
# documents, frontmatter and the section tree
# --------------------------------------------------------------------------


def test_frontmatter_is_parsed_but_not_indexed_as_body() -> None:
    document = index_bytes(
        b"""---
title: Fixture
version: 2
paths:
  - src/pmk/**
# not a heading
---

# Real Title
"""
    )
    assert document["frontmatter"] == {"title": "Fixture", "version": "2"}
    assert document["title"] == "Real Title"
    # Only one section: the frontmatter contributed neither headings nor anchors.
    assert [s["title"] for s in document["sections"]] == ["Real Title"]
    assert _ids(document) == ["real-title"]


def test_heading_tree_carries_outline_numbers_lines_and_slugs() -> None:
    document = index_bytes(
        b"""# Root

## Alpha

### Alpha One

## Beta
"""
    )
    root = document["sections"][0]
    assert (root["level"], root["number"], root["line"], root["slug"]) == (
        1,
        "1",
        1,
        "root",
    )
    alpha, beta = root["children"]
    assert alpha["number"] == "1.1"
    assert alpha["line"] == 3
    assert beta["number"] == "1.2"
    assert beta["line"] == 7
    nested = alpha["children"][0]
    assert nested["number"] == "1.1.1"
    assert nested["line"] == 5
    assert nested["slug"] == "alpha-one"


def test_authored_outline_number_becomes_the_anchor() -> None:
    document = index_bytes(b"## 2. Adjudication\n")
    section = document["sections"][0]
    assert section["number"] == "1"  # derived position
    assert section["anchor"] == "2"  # authored number
    assert section["title"] == "Adjudication"
    assert "2" in _ids(document)


# --------------------------------------------------------------------------
# fenced code is never indexed
# --------------------------------------------------------------------------


def test_fenced_code_blocks_are_ignored() -> None:
    document = index_bytes(
        b"""# Real

```
# Fake Heading
| not | a table |
| --- | --- |
R-99 in code
Case 9.9 in code
[link](#r-99)
```
"""
    )
    assert [s["title"] for s in document["sections"]] == ["Real"]
    assert document["tables"] == []
    assert document["xrefs"] == []
    assert _ids(document) == ["real"]


# --------------------------------------------------------------------------
# tables
# --------------------------------------------------------------------------


def test_pipe_table_is_parsed_and_owned_by_its_section() -> None:
    document = index_bytes(
        b"""# Root

## Rules

| Rule | Meaning |
| --- | --- |
| R-02 | Timing |
| R-03 | Ordering |

Trailing prose.
"""
    )
    assert len(document["tables"]) == 1
    table = document["tables"][0]
    assert table["headers"] == ["Rule", "Meaning"]
    assert table["rows"] == [["R-02", "Timing"], ["R-03", "Ordering"]]
    assert table["row_count"] == 2
    assert table["column_count"] == 2
    assert table["line"] == 5
    assert table["section"] == "1.1"  # owned by "## Rules"


def test_two_tables_and_escaped_pipes() -> None:
    document = index_bytes(
        b"""# Root

| A | B |
| --- | --- |
| 1 \\| 2 | 3 |

| C |
| --- |
| 4 |
"""
    )
    assert len(document["tables"]) == 2
    assert document["tables"][0]["rows"] == [["1 | 2", "3"]]
    assert document["tables"][1]["headers"] == ["C"]
    assert document["tables"][1]["rows"] == [["4"]]


def test_block_without_separator_is_not_a_table() -> None:
    document = index_bytes(b"| A | B |\n| 1 | 2 |\n")
    assert document["tables"] == []


# --------------------------------------------------------------------------
# anchors
# --------------------------------------------------------------------------


def test_explicit_html_and_pandoc_anchors() -> None:
    document = index_bytes(
        b"""## Appeals {#appeals}

<a id="custom-anchor"></a>
"""
    )
    by_id = {a["id"]: a for a in document["anchors"]}
    assert by_id["appeals"]["kind"] == "explicit"
    assert by_id["custom-anchor"]["kind"] == "explicit"
    # The pandoc attribute is stripped from the visible title.
    assert document["sections"][0]["title"] == "Appeals"


def test_rule_and_case_ids_in_headings_become_anchors() -> None:
    document = index_bytes(b"### R-02: Timing Windows\n\n#### Case 4.1: Late Filing\n")
    by_id = {a["id"]: a for a in document["anchors"]}
    assert by_id["R-02"]["kind"] == "rule"
    assert by_id["case-4.1"]["kind"] == "case"
    assert by_id["R-02"]["line"] == 1
    assert by_id["case-4.1"]["section_title"] == "Case 4.1: Late Filing"


def test_list_item_defines_an_id() -> None:
    document = index_bytes(b"- **R-03**: Ordering rules.\n- Case 2: Filing fees.\n")
    assert "R-03" in _ids(document)
    assert "case-2" in _ids(document)
    assert document["xrefs"] == []


def test_inline_mention_is_an_xref_not_an_anchor() -> None:
    document = index_bytes(b"See R-03 in practice, then Case 4.1 again.\n")
    assert [x["target"] for x in document["xrefs"]] == ["R-03", "case-4.1"]
    assert [x["kind"] for x in document["xrefs"]] == ["rule", "case"]
    # No anchor is claimed by merely mentioning an id.
    assert document["anchors"] == []


def test_table_cell_mention_is_an_xref_not_an_anchor() -> None:
    document = index_bytes(
        b"| Rule |\n| --- |\n| R-02 |\n"
    )
    assert [x["target"] for x in document["xrefs"]] == ["R-02"]
    assert document["anchors"] == []


def test_xrefs_are_emitted_in_source_order_within_a_line() -> None:
    document = index_bytes(b"Compare Case 4.1 with R-03 and see \xc2\xa74.2.\n")
    assert [(x["kind"], x["target"]) for x in document["xrefs"]] == [
        ("case", "case-4.1"),
        ("rule", "R-03"),
        ("section", "4.2"),
    ]


# --------------------------------------------------------------------------
# corpus-wide resolution
# --------------------------------------------------------------------------


def test_resolution_marks_resolved_and_unresolved(rules) -> None:
    root = rules(
        {
            "a.md": "# A\n\n- **R-02**: Timing.\n",
            "b.md": "# B\n\nApplies R-02 but never R-77.\n",
        }
    )
    index = build_index(root)
    targets = {x["target"]: x for x in index["xrefs"]}

    assert targets["R-02"]["resolved"] is True
    assert targets["R-02"]["resolved_document"] == "a.md"
    assert targets["R-02"]["resolved_line"] == 3
    assert targets["R-02"]["resolved_id"] == "R-02"

    assert targets["R-77"]["resolved"] is False
    assert targets["R-77"]["resolved_document"] is None

    assert index["stats"]["resolved_xrefs"] == 1
    assert index["stats"]["unresolved_xrefs"] == 1
    assert any("unresolved xref 'R-77' at b.md:3" in w for w in index["warnings"])


def test_anchor_lookup_tolerates_id_spelling_variants(rules) -> None:
    root = rules(
        {
            "a.md": "# A\n\n- **R-2**: Timing.\n",
            "b.md": "# B\n\nSee [timing](#R-002) here.\n",
        }
    )
    index = build_index(root)
    xref = index["xrefs"][0]
    assert xref["resolved"] is True
    assert xref["resolved_id"] == "R-2"


def test_markdown_link_xref_with_document_hint(rules) -> None:
    root = rules(
        {
            "a.md": "# A\n\n- **R-02**: Timing.\n",
            "b.md": "# B\n\nSee [timing](a.md#r-02) and [gone](missing.md#zzz).\n",
        }
    )
    index = build_index(root)
    by_raw = {x["target"]: x for x in index["xrefs"]}
    assert by_raw["r-02"]["resolved"] is True
    assert by_raw["r-02"]["resolved_document"] == "a.md"
    assert by_raw["zzz"]["resolved"] is False


def test_duplicate_anchor_within_a_document_first_wins() -> None:
    document = index_bytes(b"## Notes\n\ntext\n\n## Notes\n")
    assert _ids(document).count("notes") == 1
    assert len([w for w in document["warnings"] if "duplicate anchor 'notes'" in w]) == 1
    assert document["anchors"][0]["line"] == 1


def test_duplicate_anchor_across_documents_first_wins(rules) -> None:
    root = rules(
        {
            "a.md": "# A\n\n- **R-03**: Ordering.\n",
            "b.md": "# B\n\n- **R-03**: Ordering again.\n",
        }
    )
    index = build_index(root)
    assert list(index["anchors"]) == ["a", "R-03", "b"]
    assert index["anchors"]["R-03"]["document"] == "a.md"
    assert any("duplicate anchor 'R-03' at b.md" in w for w in index["warnings"])


# --------------------------------------------------------------------------
# manifest and checksums
# --------------------------------------------------------------------------


def test_manifest_pinned_commit_and_matching_checksums(rules) -> None:
    root = rules({"a.md": "# A\n"})
    sha = build_index(root)["documents"][0]["sha256"]
    _write(root / "manifest.json", json.dumps({"pinned_commit": "abc123", "files": {"a.md": sha}}))
    index = build_index(root)
    assert index["source"]["pinned_commit"] == "abc123"
    assert index["documents"][0]["checksum"]["matches"] is True
    assert index["warnings"] == []


def test_checksum_mismatch_is_reported_as_a_warning(rules) -> None:
    root = rules({"a.md": "# A\n"})
    _write(root / "manifest.json", json.dumps({"files": {"a.md": "0" * 64}}))
    index = build_index(root)
    assert index["documents"][0]["checksum"]["matches"] is False
    assert any("checksum mismatch for a.md" in w for w in index["warnings"])


def test_missing_rules_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(RulesIndexError):
        build_index(tmp_path / "nope")


# --------------------------------------------------------------------------
# determinism and IO
# --------------------------------------------------------------------------


def test_build_is_deterministic(rules) -> None:
    root = rules(
        {
            "b.md": "# B\n\nSee R-02.\n",
            "a.md": "# A\n\n- **R-02**: Timing.\n",
        }
    )
    first = dumps_index(build_index(root))
    second = dumps_index(build_index(root))
    assert first == second
    parsed = json.loads(first)
    assert parsed["schema_version"] >= 1
    assert "created_at" not in parsed and "generated_at" not in parsed


def test_index_json_shape_exposes_the_four_requested_collections(rules) -> None:
    root = rules({"a.md": "# A\n\n## B\n\n| X |\n| --- |\n| 1 |\n"})
    index = build_index(root)
    for key in ("documents", "anchors", "xrefs", "tables"):
        assert key in index
    assert index["stats"]["documents"] == 1
    assert index["stats"]["sections"] == 2
    assert index["stats"]["tables"] == 1
    assert index["tables"][0]["document"] == "a.md"


def test_write_index_round_trips_and_leaves_no_temp_files(tmp_path: Path, rules) -> None:
    root = rules({"a.md": "# A\n"})
    index = build_index(root)
    out = tmp_path / "nested" / "index.json"  # parent must be created
    written = write_index(index, out)

    assert written == out
    assert load_index(out) == index
    raw = out.read_bytes()
    assert b"\r\n" not in raw and raw.endswith(b"\n")
    assert list(out.parent.glob("*.tmp")) == []


# --------------------------------------------------------------------------
# command line
# --------------------------------------------------------------------------


def test_cli_writes_the_index_and_returns_zero(tmp_path: Path, rules, capsys) -> None:
    root = rules({"a.md": "# A\n\n- **R-02**: Timing.\n"})
    out = tmp_path / "out" / "index.json"
    assert main(["--rules", str(root), "--out", str(out)]) == 0
    assert out.is_file()
    captured = capsys.readouterr()
    assert "1 document(s)" in captured.out
    assert str(out) in captured.out


def test_cli_check_accepts_a_fresh_index_and_rejects_drift(
    tmp_path: Path, rules, capsys
) -> None:
    root = rules({"a.md": "# A\n"})
    out = tmp_path / "index.json"
    assert main(["--rules", str(root), "--out", str(out)]) == 0
    assert main(["--rules", str(root), "--out", str(out), "--check"]) == 0

    _write(root / "b.md", "# B\n")
    assert main(["--rules", str(root), "--out", str(out), "--check"]) == 1
    assert "stale" in capsys.readouterr().err

    assert main(["--quiet", "--rules", str(root), "--out", str(out)]) == 0
    assert capsys.readouterr().out == ""


def test_cli_check_reports_a_missing_index(tmp_path: Path, rules, capsys) -> None:
    root = rules({"a.md": "# A\n"})
    assert main(["--rules", str(root), "--out", str(tmp_path / "index.json"), "--check"]) == 1
    assert "missing" in capsys.readouterr().err


def test_cli_missing_rules_directory_returns_two(tmp_path: Path, capsys) -> None:
    assert main(["--rules", str(tmp_path / "nope")]) == 2
    assert "not found" in capsys.readouterr().err


# --------------------------------------------------------------------------
# smoke test against a real corpus, when one is present
# --------------------------------------------------------------------------


@pytest.mark.skipif(
    not (ROOT / "docs" / "rules").is_dir(),
    reason="docs/rules corpus not present in this worktree",
)
def test_real_corpus_indexes_without_crashing() -> None:
    index = build_index(ROOT / "docs" / "rules")
    assert index["stats"]["documents"] >= 1
    assert index["stats"]["sections"] >= 1
    assert json.loads(dumps_index(index))["stats"] == index["stats"]
