import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cna.tools.show_rule as show


@pytest.fixture()
def rules(tmp_path):
    directory = tmp_path / "rules"
    sections = directory / "sections"
    sections.mkdir(parents=True)
    (sections / "section-07.adoc").write_text(
        "\n".join(
            [
                "== Initiative",
                "[#7_14]",
                "=== Sequence",
                "The side with the higher rating moves first; see <<7_11,7.11>>.",
                "A tie is resolved by the procedure in Case 7.12.",
                "",
                "[#7_16]",
                "=== Weather",
                "Weather is determined separately.",
            ]
        ),
        encoding="utf-8",
    )
    (sections / "section-06.adoc").write_text(
        "\n".join(["*[6.13]* Capability costs", "Spend CP as required."]),
        encoding="utf-8",
    )
    return directory


def test_load_anchor_case_with_xrefs(rules):
    case = show.load_case("7.14", rules)
    assert case.case == "7.14"
    assert case.title == "Sequence"
    assert "higher rating" in case.text
    assert "Weather" not in case.text
    assert show.case_xrefs(case.text) == ["7.11", "7.12"]
    assert case.rules_file == "sections/section-07.adoc"


def test_load_inline_case_and_underscore_alias(rules):
    case = show.load_case("6.13", rules)
    assert case.title == "Capability costs"
    assert "Spend CP" in case.text
    assert show.load_case("7_14", rules).case == "7.14"


def test_invalid_and_missing_cases_return_errors(rules):
    with pytest.raises(show.RuleLookupError, match="invalid case id"):
        show.load_case("initiative", rules)
    with pytest.raises(show.RuleLookupError, match="not found"):
        show.load_case("99.1", rules)
    with pytest.raises(show.RuleLookupError, match="rules directory not found"):
        show.load_case("7.14", rules / "absent")


def test_cli_json_output(rules, capsys):
    assert show.main(["7.14", "--rules", str(rules), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["case"] == "7.14"
    assert payload["xrefs"] == ["7.11", "7.12"]


def test_cli_missing_case_is_a_nonzero_error(rules, capsys):
    assert show.main(["99.1", "--rules", str(rules)]) == 1
    assert "not found" in capsys.readouterr().err
