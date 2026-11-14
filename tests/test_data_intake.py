import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cna.tools.data_gaps as gaps

SOURCE = b"R-04 charts and tables, operator scan\n"


def _write(path: Path, payload: str | bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, bytes):
        path.write_bytes(payload)
    else:
        path.write_text(payload, encoding="utf-8")
    return path


def _table(
    *, status: str = "verified", provenance: str = "chart:R-04:TEC"
) -> dict:
    return {
        "schema_version": 1,
        "source": provenance,
        "status": status,
        "records": [
            {
                "provenance": provenance,
                "status": status,
                "terrain": "clear",
                "cp": 1,
            }
        ],
    }


def _record(root: Path) -> dict:
    """A closure record whose source, extraction and evidence all exist."""
    _write(root / "docs/sources/r04/charts.pdf", SOURCE)
    _write(root / "data/r04/tec.json", json.dumps(_table()))
    evidence = {}
    for key in gaps.REQUIRED_EVIDENCE:
        _write(root / f"docs/sources/r04/{key}.txt", "evidence\n")
        evidence[key] = f"docs/sources/r04/{key}.txt"
    return {
        "status": "HAVE",
        "source": {
            "path": "docs/sources/r04/charts.pdf",
            "sha256": hashlib.sha256(SOURCE).hexdigest(),
            "bytes": len(SOURCE),
            "title": "Charts and Tables",
            "edition": "SPI, 1979",
            "copy": "operator scan",
            "identifiers": ["R-04 booklet p.3"],
        },
        "authorization": "operator placed the scan on 2026-11-09",
        "extraction": {
            "path": "data/r04/tec.json",
            "method": "manual transcription",
            "tool": "editor",
            "performed_by": "extractor",
            "pages": ["R-04 p.3"],
        },
        "review": {
            "performed_by": "reviewer",
            "second_pass": True,
            "conflicts": [],
        },
        "evidence": evidence,
        "identifiers_stable": True,
    }


def _entries(status: str = "HAVE") -> list[dict]:
    entries = [dict(gap, blocks=list(gap["blocks"])) for gap in gaps.GAPS]
    for entry in entries:
        if entry["id"] == "R-04":
            entry["status"] = status
    return entries


def _r04(report: dict) -> dict:
    return next(gap for gap in report["gaps"] if gap["id"] == "R-04")


def test_valid_intake_and_register_agree_to_close_r04(tmp_path):
    record = _record(tmp_path)
    result = gaps.validate_intake_entry("R-04", record, root=tmp_path)

    assert result.ok, result.problems
    assert result.status == "HAVE"
    assert result.source == "docs/sources/r04/charts.pdf"
    assert result.extraction == "data/r04/tec.json"

    report = gaps.build_report(
        intake={"R-04": result}, entries=_entries("HAVE")
    )
    assert _r04(report)["status"] == "HAVE"
    assert report["open_count"] == len(gaps.GAPS) - 1
    assert report["problems"] == []


def test_valid_intake_closes_the_register_in_one_step(tmp_path):
    result = gaps.validate_intake_entry("R-04", _record(tmp_path), root=tmp_path)

    report = gaps.build_report(intake={"R-04": result})

    assert _r04(report)["status"] == "HAVE"
    assert report["open_count"] == len(gaps.GAPS) - 1
    assert report["problems"] == []


def test_register_claim_without_an_intake_record_is_downgraded(tmp_path):
    report = gaps.build_report(entries=_entries("HAVE"))

    assert _r04(report)["status"] == "UNVERIFIED"
    assert any("no intake record" in problem for problem in report["problems"])


def test_checksum_and_size_must_match_the_recorded_source(tmp_path):
    record = _record(tmp_path)
    record["source"]["sha256"] = "0" * 64
    record["source"]["bytes"] = len(SOURCE) + 1

    result = gaps.validate_intake_entry("R-04", record, root=tmp_path)

    assert not result.ok
    assert any("sha256 does not match" in problem for problem in result.problems)
    assert any("bytes does not match" in problem for problem in result.problems)

    report = gaps.build_report(
        intake={"R-04": result}, entries=_entries("HAVE")
    )
    assert _r04(report)["status"] == "UNVERIFIED"
    assert any("sha256 does not match" in problem for problem in report["problems"])


def test_source_must_be_placed_under_docs_sources(tmp_path):
    record = _record(tmp_path)
    _write(tmp_path / "data/r04/charts.pdf", SOURCE)
    record["source"]["path"] = "data/r04/charts.pdf"

    result = gaps.validate_intake_entry("R-04", record, root=tmp_path)

    assert not result.ok
    assert any("outside docs/sources/" in problem for problem in result.problems)


def test_extraction_must_be_written_under_data(tmp_path):
    record = _record(tmp_path)
    _write(tmp_path / "docs/sources/r04/tec.json", json.dumps(_table()))
    record["extraction"]["path"] = "docs/sources/r04/tec.json"

    result = gaps.validate_intake_entry("R-04", record, root=tmp_path)

    assert not result.ok
    assert any("outside data/" in problem for problem in result.problems)


@pytest.mark.parametrize("status", ["synthetic", "placeholder", "ocr_suspect"])
def test_non_verified_extraction_is_refused(tmp_path, status):
    record = _record(tmp_path)
    _write(
        tmp_path / "data/r04/tec.json",
        json.dumps(_table(status=status, provenance="chart:R-04:TEC")),
    )

    result = gaps.validate_intake_entry("R-04", record, root=tmp_path)

    assert not result.ok
    assert any("must be 'verified'" in problem for problem in result.problems)


def test_extraction_must_carry_the_provenance_schema(tmp_path):
    record = _record(tmp_path)
    broken = _table()
    del broken["records"][0]["provenance"]
    _write(tmp_path / "data/r04/tec.json", json.dumps(broken))

    result = gaps.validate_intake_entry("R-04", record, root=tmp_path)

    assert not result.ok
    assert any("provenance" in problem for problem in result.problems)


def test_missing_or_empty_evidence_blocks_closure(tmp_path):
    record = _record(tmp_path)
    record["evidence"].pop("review_notes")
    _write(tmp_path / "docs/sources/r04/coverage_report.txt", "")

    result = gaps.validate_intake_entry("R-04", record, root=tmp_path)

    assert not result.ok
    assert any("evidence.review_notes" in problem for problem in result.problems)
    assert any("is empty" in problem for problem in result.problems)


def test_second_pass_must_be_independent_and_resolve_conflicts(tmp_path):
    record = _record(tmp_path)
    record["review"]["performed_by"] = "extractor"
    record["review"]["second_pass"] = False
    record["review"]["conflicts"] = [{"source": "R-04 p.3", "values": [1, 2]}]

    result = gaps.validate_intake_entry("R-04", record, root=tmp_path)

    assert not result.ok
    assert any("must differ" in problem for problem in result.problems)
    assert any("second_pass" in problem for problem in result.problems)
    assert any("must record a resolution" in problem for problem in result.problems)


def test_identifier_stability_and_authorization_are_required(tmp_path):
    record = _record(tmp_path)
    record["identifiers_stable"] = False
    record["authorization"] = ""

    result = gaps.validate_intake_entry("R-04", record, root=tmp_path)

    assert not result.ok
    assert any("identifiers_stable" in problem for problem in result.problems)
    assert any("authorization" in problem for problem in result.problems)


def test_unknown_resource_and_missing_manifest_are_handled(tmp_path):
    record = _record(tmp_path)

    unknown = gaps.validate_intake_entry("R-99", copy.deepcopy(record), root=tmp_path)
    assert not unknown.ok
    assert any("unknown resource" in problem for problem in unknown.problems)
    assert gaps.load_intake(tmp_path / "absent.json", root=tmp_path) == {}


def test_malformed_manifest_is_an_error(tmp_path):
    _write(tmp_path / "docs/sources/intake.json", "{not json")

    with pytest.raises(gaps.IntakeError, match="cannot read intake manifest"):
        gaps.load_intake(root=tmp_path)

    _write(
        tmp_path / "docs/sources/intake.json",
        json.dumps({"schema_version": 2, "resources": {}}),
    )
    with pytest.raises(gaps.IntakeError, match="schema_version"):
        gaps.load_intake(root=tmp_path)


def test_cli_validates_writes_checks_and_rejects_a_tampered_extraction(
    tmp_path, monkeypatch
):
    record = _record(tmp_path)
    manifest = tmp_path / "docs/sources/intake.json"
    _write(
        manifest,
        json.dumps({"schema_version": 1, "resources": {"R-04": record}}),
    )
    out = tmp_path / "data-gaps.md"
    monkeypatch.setattr(gaps, "GAPS", tuple(_entries("HAVE")))

    assert gaps.main(["--intake", str(manifest), "--validate-intake"]) == 0
    assert gaps.main(["--intake", str(manifest), "--out", str(out)]) == 0
    assert gaps.main(["--intake", str(manifest), "--out", str(out), "--check"]) == 0
    assert "| R-04 |" in out.read_text(encoding="utf-8")
    assert "| HAVE |" in out.read_text(encoding="utf-8")

    _write(
        tmp_path / "data/r04/tec.json",
        json.dumps(_table(status="placeholder", provenance="placeholder:R-04")),
    )
    assert gaps.main(["--intake", str(manifest), "--out", str(out), "--check"]) == 1
    # The static HAVE claim is downgraded, so the CLI must not rewrite it.
    assert gaps.main(["--intake", str(manifest), "--out", str(out)]) == 1


def test_cli_writes_when_a_validated_intake_closes_the_resource(tmp_path):
    record = _record(tmp_path)
    manifest = tmp_path / "docs/sources/intake.json"
    _write(
        manifest,
        json.dumps({"schema_version": 1, "resources": {"R-04": record}}),
    )
    out = tmp_path / "data-gaps.md"

    assert gaps.main(["--intake", str(manifest), "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "| R-04 |" in text
    assert "| HAVE |" in text


def test_no_intake_manifest_leaves_the_static_register_unchanged():
    report = gaps.build_report()

    assert report["open_count"] == len(gaps.GAPS)
    assert all(gap["status"] != "HAVE" for gap in report["gaps"])
    assert report["problems"] == []
