import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cna.tools.coverage as cov


def test_glob_matches_basic():
    assert cov.glob_matches("src/pmk/**", "src/pmk/events.py") is True
    assert cov.glob_matches("src/pmk/**", "src/pmk") is False
    assert cov.glob_matches("src/fleet/**", "src/fleet/recover.py") is True
    assert cov.glob_matches("**/*", "anything/at/all.txt") is True


def test_glob_matches_wildcards():
    assert cov.glob_matches("src/*.py", "src/top.py") is True
    assert cov.glob_matches("src/*.py", "src/sub/top.py") is False
    assert cov.glob_matches("src/m?.py", "src/m1.py") is True
    assert cov.glob_matches("src/m?.py", "src/mx.py") is True
    assert cov.glob_matches("src/m?.py", "src/mxx.py") is False


def test_iter_source_paths(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x", encoding="utf-8")
    pc = tmp_path / "src" / "__pycache__"
    pc.mkdir()
    (pc / "a.cpython-312.pyc").write_bytes(b"\x00")
    paths = cov.iter_source_paths(["src"], root=tmp_path)
    assert paths == ["src/a.py"]


def test_frontmatter_paths_lenient():
    text = "---\npaths:\n  - src/pmk/**\n  - .pm/**\n---\nbody"
    globs, has = cov._frontmatter_paths(text)
    assert has is True
    assert globs == ["src/pmk/**", ".pm/**"]
    bad = "---\nother: 1\n---\n"
    assert cov._frontmatter_paths(bad)[0] == []
    assert cov._frontmatter_paths("no frontmatter")[1] is False


def test_build_coverage_uncovered_and_counts(tmp_path):
    rules = tmp_path / "rules"
    src = tmp_path / "src"
    rules.mkdir()
    (rules / "r.md").write_text("---\npaths:\n  - src/a.py\n---\n", encoding="utf-8")
    a = src / "a.py"
    a.parent.mkdir()
    a.write_text("x", encoding="utf-8")
    b = src / "b.py"
    b.write_text("y", encoding="utf-8")
    scanned = ["src/a.py", "src/b.py"]
    report = cov.build_coverage(rules, scanned)
    assert report["schema_version"] == cov.SCHEMA_VERSION
    assert report["counts"]["paths"] == 2
    assert report["counts"]["covered"] == 1
    assert report["counts"]["uncovered"] == 1
    assert report["uncovered_paths"] == ["src/b.py"]
    assert report["rules"][0]["globs"] == ["src/a.py"]
    assert report["rules"][0]["matched_paths"] == ["src/a.py"]


def test_write_load_determinism(tmp_path):
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "a.md").write_text("---\npaths:\n  - '**/*'\n---\n", encoding="utf-8")
    scanned = ["x.py", "y.py"]
    report = cov.build_coverage(rules, scanned)
    out = tmp_path / "out.json"
    cov.write_coverage(report, out)
    loaded = cov.load_coverage(out)
    assert loaded == report
    assert cov.dumps_coverage(loaded) == cov.dumps_coverage(report)


def test_main_up_to_date_and_drift(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rules = tmp_path / "docs" / "rules"
    src = tmp_path / "src"
    rules.mkdir(parents=True)
    src.mkdir()
    (rules / "r.md").write_text("---\npaths:\n  - 'src/**'\n---\n", encoding="utf-8")
    (src / "a.py").write_text("x", encoding="utf-8")
    out = Path("coverage") / "rules_coverage.json"
    rc = cov.main([])
    assert rc == 0
    assert out.is_file()
    rc = cov.main(["--check"])
    assert rc == 0
    # stale report should be detected
    report = cov.load_coverage(out)
    report["counts"]["covered"] = 999
    cov.write_coverage(report, out)
    rc = cov.main(["--check"])
    assert rc == 1


def test_main_missing_rules_returns_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = cov.main(["--rules", "does/not/exist", "--out", "out.json"])
    assert rc == 2


def test_case_inventory_reports_reviewed_statuses(tmp_path):
    rules = tmp_path / "rules"
    sections = rules / "sections"
    sections.mkdir(parents=True)
    (sections / "section-05.adoc").write_text(
        "[#5_2]\n=== Sequence\n", encoding="utf-8")
    (sections / "section-07.adoc").write_text(
        "[#7_14]\n*[7.14]* Initiative\n", encoding="utf-8")
    (sections / "section-32.adoc").write_text(
        "== Abstract Logistics\n", encoding="utf-8")

    report = cov.build_coverage(rules, ["src/example.py"])
    cases = {case["case"]: case for case in report["cases"]}

    assert cases["5.2"]["status"] == "partial"
    assert cases["7.14"]["status"] == "implemented"
    assert cases["32.0"]["status"] == "deferred"
    assert report["counts"]["cases"] == len(report["cases"])
    assert report["counts"]["cases"] >= 3
    assert report["counts"]["cases_implemented"] == 1
    assert report["counts"]["cases_partial"] == 1
    assert report["counts"]["cases_deferred"] == 1