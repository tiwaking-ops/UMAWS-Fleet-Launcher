import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cna.tools.data_gaps as gaps

SOURCE = b"official resource scan\n"


def _write(path: Path, payload: str | bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, bytes):
        path.write_bytes(payload)
    else:
        path.write_text(payload, encoding="utf-8")
    return path


def _table(resource: str) -> dict:
    provenance = f"chart:{resource}:TEC"
    return {
        "schema_version": 1,
        "source": provenance,
        "status": "verified",
        "records": [
            {
                "provenance": provenance,
                "status": "verified",
                "terrain": "clear",
                "cp": 1,
            }
        ],
    }


def _record(root: Path, resource: str) -> dict:
    """A valid closure record for any P1c.2 resource."""
    slug = resource.lower().replace("-", "")
    _write(root / f"docs/sources/{slug}/source.pdf", SOURCE)
    _write(root / f"data/{slug}/table.json", json.dumps(_table(resource)))
    evidence = {}
    for key in gaps.REQUIRED_EVIDENCE:
        _write(root / f"docs/sources/{slug}/{key}.txt", "evidence\n")
        evidence[key] = f"docs/sources/{slug}/{key}.txt"
    return {
        "status": "HAVE",
        "source": {
            "path": f"docs/sources/{slug}/source.pdf",
            "sha256": hashlib.sha256(SOURCE).hexdigest(),
            "bytes": len(SOURCE),
            "title": f"{resource} source",
            "edition": "official printing",
            "copy": "operator scan",
            "identifiers": [f"{resource} p.3"],
        },
        "authorization": "operator placed the scan on 2026-11-09",
        "extraction": {
            "path": f"data/{slug}/table.json",
            "method": "manual transcription",
            "tool": "editor",
            "performed_by": "extractor",
            "pages": [f"{resource} p.3"],
        },
        "review": {
            "performed_by": "reviewer",
            "second_pass": True,
            "conflicts": [],
        },
        "evidence": evidence,
        "identifiers_stable": True,
    }


def _entries(*resources: str) -> list[dict]:
    entries = [dict(gap, blocks=list(gap["blocks"])) for gap in gaps.GAPS]
    for entry in entries:
        if entry["id"] in resources:
            entry["status"] = "HAVE"
    return entries


def _gate_resource(gate: dict, resource: str) -> gaps.GateResult:
    return next(item for item in gate["resources"] if item.resource == resource)


def test_gate_blocks_all_three_while_the_register_is_open():
    gate = gaps.build_gate_report()

    assert gate["status"] == "BLOCKED"
    assert gate["closed"] == 0
    assert [item.resource for item in gate["resources"]] == list(
        gaps.P1C2_RESOURCES
    )
    for item in gate["resources"]:
        assert item.result == "BLOCKED"
        assert item.intake_status == "missing"
        assert "no intake record" in item.blocker


def test_gate_passes_only_when_register_and_intake_agree(tmp_path):
    result = gaps.validate_intake_entry("R-04", _record(tmp_path, "R-04"),
                                        root=tmp_path)
    assert result.ok, result.problems

    gate = gaps.build_gate_report(
        intake={"R-04": result}, entries=_entries("R-04")
    )

    r04 = _gate_resource(gate, "R-04")
    assert r04.result == "PASS"
    assert r04.register_status == "HAVE"
    assert r04.intake_status == "valid"
    assert gate["closed"] == 1
    assert gate["status"] == "BLOCKED"
    assert _gate_resource(gate, "R-05").result == "BLOCKED"


def test_gate_passes_from_a_validated_intake_in_one_step(tmp_path):
    result = gaps.validate_intake_entry("R-04", _record(tmp_path, "R-04"),
                                        root=tmp_path)
    assert result.ok, result.problems

    gate = gaps.build_gate_report(intake={"R-04": result})

    r04 = _gate_resource(gate, "R-04")
    assert r04.result == "PASS"
    assert r04.intake_status == "valid"
    assert r04.register_status == "HAVE"
    assert gate["closed"] == 1
    assert gate["status"] == "BLOCKED"
    assert _gate_resource(gate, "R-05").result == "BLOCKED"


def test_gate_blocks_a_register_claim_with_an_invalid_intake(tmp_path):
    record = _record(tmp_path, "R-04")
    record["source"]["sha256"] = "0" * 64
    result = gaps.validate_intake_entry("R-04", record, root=tmp_path)
    assert not result.ok

    gate = gaps.build_gate_report(
        intake={"R-04": result}, entries=_entries("R-04")
    )

    r04 = _gate_resource(gate, "R-04")
    assert r04.result == "BLOCKED"
    assert r04.register_status == "UNVERIFIED"
    assert "sha256 does not match" in r04.blocker


def test_gate_passes_all_three_when_each_pair_agrees(tmp_path):
    intake = {
        resource: gaps.validate_intake_entry(
            resource, _record(tmp_path, resource), root=tmp_path
        )
        for resource in gaps.P1C2_RESOURCES
    }
    assert all(result.ok for result in intake.values())

    gate = gaps.build_gate_report(
        intake=intake, entries=_entries(*gaps.P1C2_RESOURCES)
    )

    assert gate["status"] == "PASS"
    assert gate["closed"] == 3
    assert all(item.result == "PASS" for item in gate["resources"])


def test_gate_cli_exits_zero_when_all_three_intakes_validate(
    tmp_path, capsys
):
    resources = {
        resource: _record(tmp_path, resource)
        for resource in gaps.P1C2_RESOURCES
    }
    manifest = tmp_path / "docs/sources/intake.json"
    _write(
        manifest,
        json.dumps({"schema_version": 1, "resources": resources}),
    )

    assert gaps.main(["--intake", str(manifest), "--gate"]) == 0

    output = capsys.readouterr().out
    assert "R-04 PASS" in output
    assert "P1c.2 data gate PASS (3/3 resources closed)" in output


def test_gate_cli_reports_partial_closure(tmp_path, capsys):
    manifest = tmp_path / "docs/sources/intake.json"
    _write(
        manifest,
        json.dumps(
            {
                "schema_version": 1,
                "resources": {"R-04": _record(tmp_path, "R-04")},
            }
        ),
    )

    assert gaps.main(["--intake", str(manifest), "--gate"]) == 1

    output = capsys.readouterr().out
    assert "R-04 PASS" in output
    assert "R-05 BLOCKED" in output
    assert "no intake record" in output
    assert "1/3 resources closed" in output
