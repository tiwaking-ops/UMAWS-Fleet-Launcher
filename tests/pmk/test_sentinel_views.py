"""Sentinel, views, briefing and PDD lint tests."""

from __future__ import annotations

import json

import pytest

from pmk.pdd import lint_text
from pmk.sentinel import check
from conftest import make_bundle, make_card


# ---------------------------------------------------------------------------
# Sentinel
# ---------------------------------------------------------------------------

def test_sentinel_is_clean_on_a_healthy_repo(kernel):
    report = check(kernel)
    assert report["ok"], report["findings"]
    assert "I1" in report["checked"]
    assert "I13" in report["checked"]


def test_sentinel_detects_a_tampered_chain(kernel, repo):
    kernel.log.append("INCIDENT", subject="T-0001")
    path = repo.events_dir / "2026-10-22.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    obj = json.loads(lines[-1])
    obj["payload"]["tampered"] = True
    lines[-1] = json.dumps(obj, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = check(kernel)
    assert not report["ok"]
    assert any(f["invariant"] == "I1" for f in report["findings"])


def test_sentinel_detects_a_modified_pinned_file(kernel, repo):
    make_card(kernel)
    constitution = repo.constitution_path
    constitution.write_text("# tampered\n", encoding="utf-8")
    report = check(kernel)
    assert not report["ok"]
    assert any(f["invariant"] == "I8'" for f in report["findings"])


def test_sentinel_detects_a_stale_view(kernel):
    make_card(kernel)
    kernel.render_views(force=True)
    ledger = kernel.repo.ledger_view
    ledger.write_text("stale content\n", encoding="utf-8")
    report = check(kernel)
    assert any(f["invariant"] == "I13" for f in report["findings"])


def test_sentinel_detects_promotion_without_a_bundle(kernel):
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    kernel.submit(card.id, lease.fence, make_bundle(card.id, lease.fence))
    kernel.verify(card.id, lease.fence, ok=True)
    kernel.integrate(card.id, lease.fence)
    # Remove the bundle: the promotion now has no evidence (I6).
    import shutil
    shutil.rmtree(kernel.repo.evidence_dir / f"EB-{card.id}-{lease.fence}")
    report = check(kernel)
    assert not report["ok"]
    assert any(f["invariant"] == "I6" for f in report["findings"])


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def test_views_are_generated_from_the_log(kernel):
    card = make_card(kernel, title="Build the widget")
    kernel.render_views(force=True)
    ledger = kernel.repo.ledger_view.read_text(encoding="utf-8")
    assert card.id in ledger
    assert "Build the widget" in ledger
    assert "Do not edit" in ledger


def test_queue_view_lists_open_items(kernel):
    kernel.queue_add(topic="Pick one", options=["a", "b"], recommended="a",
                     safe_default="b")
    kernel.render_views(force=True)
    text = kernel.repo.queue_view.read_text(encoding="utf-8")
    assert "Pick one" in text
    assert "recommended" in text.lower()


def test_status_view_shows_the_project_state(kernel):
    kernel.project_set_state("RUNNING")
    kernel.render_views(force=True)
    text = kernel.repo.status_view.read_text(encoding="utf-8")
    assert "RUNNING" in text


# ---------------------------------------------------------------------------
# Briefing
# ---------------------------------------------------------------------------

def test_briefing_is_deterministic(kernel):
    make_card(kernel)
    first = kernel.brief("overseer")
    second = kernel.brief("overseer")
    assert first == second


def test_briefing_contains_the_constitution(kernel):
    text = kernel.brief("overseer")
    assert "Kernel (`pmk`) is the only writer" in text


def test_briefing_lists_ready_tasks(kernel):
    card = make_card(kernel, title="Do the thing")
    text = kernel.brief("overseer")
    assert card.id in text
    assert "Do the thing" in text


def test_worker_briefing_names_the_lease(kernel):
    card = make_card(kernel)
    kernel.claim(card.id, holder="hermes-oneshot")
    text = kernel.brief("worker")
    assert card.id in text
    assert "harness runs the acceptance commands" in text.lower()


# ---------------------------------------------------------------------------
# PDD lint
# ---------------------------------------------------------------------------

GOOD_PDD = """# PDD: demo      version: 1      status: draft

## 1. Purpose
Do a thing.

## 2. Goals
### G-001 First goal
acceptance:
- it works
oracle: `pytest -q`

## 3. Non-goals
Nothing else.

## 4. Constraints
Python 3.11.

## 5. Architecture sketch
A module.

## 6. Definition of done
gate_cmd: `pytest -q`

## 7. Open questions
None.
"""


def test_pdd_lint_accepts_a_good_pdd():
    result = lint_text(GOOD_PDD)
    assert result.ok, result.errors
    assert result.goals == ["G-001"]


def test_pdd_lint_rejects_a_missing_section():
    text = GOOD_PDD.replace("## 3. Non-goals\nNothing else.\n", "")
    result = lint_text(text)
    assert not result.ok
    assert any("Non-goals" in e for e in result.errors)


def test_pdd_lint_rejects_non_sequential_goals():
    text = GOOD_PDD.replace("### G-001 First goal", "### G-002 First goal")
    result = lint_text(text)
    assert not result.ok
    assert any("sequential" in e for e in result.errors)


def test_pdd_lint_rejects_a_goal_with_neither_oracle_nor_manual():
    text = GOOD_PDD.replace("oracle: `pytest -q`", "nothing here")
    result = lint_text(text)
    assert not result.ok
    assert any("oracle" in e for e in result.errors)


def test_pdd_lint_rejects_a_goal_with_both():
    text = GOOD_PDD.replace("oracle: `pytest -q`",
                            "oracle: `pytest -q`\nmanual-check: look at it")
    result = lint_text(text)
    assert not result.ok
    assert any("exactly one" in e for e in result.errors)


def test_pdd_lint_requires_a_gate_cmd():
    text = GOOD_PDD.replace("gate_cmd: `pytest -q`", "nothing")
    result = lint_text(text)
    assert not result.ok
    assert any("gate_cmd" in e for e in result.errors)
