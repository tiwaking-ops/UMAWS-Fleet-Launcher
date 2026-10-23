"""Provenance: capture, read-back, and the D-L12 rule that now uses facts."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from fleet.profiles import Profile  # noqa: E402
from fleet.select import could_serve, select_profile  # noqa: E402
from fleet.state import FleetState  # noqa: E402
from quotagate.provenance import ProvenanceLedger, served_from_response  # noqa: E402


class _Task:
    def __init__(self, type="verify", hint=""):
        self.id = "T-0009"
        self.type = type
        self.agent_hint = hint


def _profile(pid, family="unknown", model="", models=()):
    return Profile(id=pid, adapter="kilo", family=family,
                   argv_new=["kilo", "run"], argv_resume=[],
                   model=model, models=list(models), roles=["verify"])


# ---------------------------------------------------------------------- capture

def test_served_from_response_body_names_the_model():
    got = served_from_response({"model": "command-a-03-2025"},
                               {"x-request-id": "r1"})
    assert got["model"] == "command-a-03-2025"


def test_served_from_response_decision_names_the_provider():
    got = served_from_response(
        {"model": "auto/best-free"},
        {"x-omniroute-decision": "strategy=auto; provider=cohere; latency_ms=741"})
    assert got["model"] == "auto/best-free"
    assert got["provider"] == "cohere"


def test_served_from_response_nothing_names_it_is_unknown_not_empty():
    assert served_from_response({"usage": {}}, {}) == {}


def test_ledger_reads_by_task_and_window():
    led = ProvenanceLedger()
    led.record("T-1", "p", "dep", "model-a", latency_ms=100, at=1000.0)
    led.record("T-1", "p", "dep", "model-b", latency_ms=200, at=2000.0)
    led.record("T-2", "p", "dep", "model-c", at=1500.0)

    assert led.served_models("T-1") == {"model-a", "model-b"}
    by_window = {r["served_model"] for r in led.for_window("dep", 0, 2500)}
    assert by_window == {"model-a", "model-b", "model-c"}
    # a narrower window excludes the later call
    early = {r["served_model"] for r in led.for_window("dep", 0, 1200)}
    assert early == {"model-a"}


def test_ledger_files_nothing_for_uncorrelated_traffic():
    led = ProvenanceLedger()
    led.record("", "p", "dep", "m")
    assert led.served_models("") == set()


# ------------------------------------------------------------------- the rule

def test_could_serve_matches_a_declared_model():
    assert could_serve(_profile("p", model="m"), {"m"}) is True


def test_could_serve_matches_any_swapable_model():
    p = _profile("p", model="kilo/kilo-auto/free",
                 models=["kilo/poolside/laguna-s-2.1:free"])
    assert could_serve(p, {"poolside/laguna-s-2.1:free"}) is True


def test_could_serve_cannot_rule_out_an_opaque_router():
    """A router is never ruled out, even when it does not list the model."""
    p = _profile("p", model="kilo/kilo-auto/free")
    assert could_serve(p, {"some-model-never-listed"}) is True


def test_could_serve_rules_out_an_unrelated_concrete_model():
    p = _profile("p", model="kilo/poolside/laguna-s-2.1:free")
    assert could_serve(p, {"totally-different-model"}) is False


def test_could_serve_with_no_provenance_rules_everything_out():
    assert could_serve(_profile("p", model="kilo/kilo-auto/free"), set()) is False


# ------------------------------------------------------------- D-L12 with facts

def test_provenance_rejects_a_profile_that_served_the_work():
    """The case the family string could not see.

    The implementer's *declared* family is upstage, so the family rule happily
    lets a poolside profile verify.  But the model that actually served was
    poolside's, and the candidate is an opaque router that could route there
    too.  Family says "independent"; provenance says "same model".  Provenance
    wins, because it is a fact about the request rather than a guess about a
    string.
    """
    profiles = [_profile("kilo-auto", family="poolside",
                         model="kilo/kilo-auto/free"),
                _profile("kilo-v2", family="poolside",
                         model="kilo/poolside/laguna-xs-2.1:free")]
    served = {"poolside/laguna-s-2.1:free"}

    sel = select_profile(_Task(), profiles, FleetState(),
                         {"kilo-auto": 0, "kilo-v2": 0},
                         implementer_family="upstage",
                         implementer_served=served)
    assert sel.chosen is not None
    assert sel.chosen.id == "kilo-v2"
    rejected = [c for c in sel.candidates
                if c.profile.id == "kilo-auto" and not c.eligible]
    assert rejected, "kilo-auto should have been rejected"
    assert "provenance" in rejected[0].reason


def test_provenance_can_only_narrow_not_widen():
    """An unknown family is still out, however clean the provenance.

    This is deliberate, and it is why provenance alone does not unblock
    anything today: every ``agents.toml`` profile declares ``family =
    "unknown"``, so nothing is eligible to verify regardless of what the
    gateway reports.  Widening that needs a declared family, which is the
    operator's decision (D-43) and not the implementer's.
    """
    profiles = [_profile("kilo-v2", family="unknown",
                         model="kilo/poolside/laguna-xs-2.1:free")]
    served = {"some-totally-unrelated-model"}
    sel = select_profile(_Task(), profiles, FleetState(), {"kilo-v2": 0},
                         implementer_family="upstage",
                         implementer_served=served)
    assert sel.chosen is None
    assert "family" in sel.reason


def test_family_rule_still_applies_without_provenance():
    """A direct-CLI profile never reaches the gateway, so the family veto stays."""
    profiles = [_profile("pi", family="deepseek",
                         model="deepseek/deepseek-v4-flash-free")]
    sel = select_profile(_Task(), profiles, FleetState(), {"pi": 0},
                         implementer_family="deepseek",
                         implementer_served=set())
    assert sel.chosen is None
    assert "family" in sel.reason


def test_provenance_does_not_block_an_unrelated_family():
    profiles = [_profile("pi", family="deepseek",
                         model="deepseek/deepseek-v4-flash-free")]
    served = {"poolside/laguna-s-2.1:free"}
    sel = select_profile(_Task(), profiles, FleetState(), {"pi": 0},
                         implementer_family="poolside",
                         implementer_served=served)
    assert sel.chosen is not None
    assert sel.chosen.id == "pi"
