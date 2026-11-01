"""Smoke test for the UMAWS Fleet repository skeleton.

Confirms the source tree under ``src/`` is importable and that the ``cna``
rules indexer runs end to end on a trivial corpus.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_src_tree_is_importable() -> None:
    import cna  # noqa: F401
    import pmk  # noqa: F401
    import cna.tools.rules_index as rules_index  # noqa: F401
    assert rules_index.__file__


def test_cna_indexer_runs_on_trivial_corpus(tmp_path: Path) -> None:
    from cna.tools.rules_index import main

    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "a.md").write_text("# A\n\n- **R-02**: Timing.\n", encoding="utf-8")
    out = tmp_path / "out" / "index.json"
    assert main(["--rules", str(rules), "--out", str(out), "--quiet"]) == 0
    assert out.is_file()
