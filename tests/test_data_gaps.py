import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cna.tools.data_gaps as gaps


def test_report_contains_the_hard_blockers_and_no_invented_resources():
    report = gaps.build_report()
    ids = {gap["id"] for gap in report["gaps"]}
    assert {"R-04", "R-05"} <= ids
    assert report["open_count"] == len(gaps.GAPS)
    assert all(gap["status"] != "HAVE" for gap in report["gaps"])
    r04 = next(gap for gap in report["gaps"] if gap["id"] == "R-04")
    assert "P1b" in r04["blocks"]


def test_render_is_deterministic_and_states_the_policy():
    first = gaps.render_markdown(gaps.build_report())
    second = gaps.render_markdown(gaps.build_report())
    assert first == second
    assert first.endswith("\n")
    assert "`--allow-placeholder`" in first
    assert "fabricated historical data" in first
    assert "| R-05 |" in first


def test_write_then_check_passes_and_detects_drift(tmp_path):
    out = tmp_path / "data-gaps.md"
    assert gaps.write_report(out) == out
    assert out.is_file()
    assert gaps.main(["--out", str(out), "--check"]) == 0

    out.write_text(out.read_text(encoding="utf-8") + "\nmanual edit\n", encoding="utf-8")
    assert gaps.main(["--out", str(out), "--check"]) == 1


def test_check_missing_file_returns_failure(tmp_path):
    assert gaps.main(["--out", str(tmp_path / "absent.md"), "--check"]) == 1
