"""Task, lease, and lifecycle tests (pilot v1 WP2 exit tests)."""

from __future__ import annotations

import pytest

from pmk.api import KernelError
from pmk.models import (BLOCKED, DONE, LEASED, PROPOSED, READY, REWORK,
                        SUBMITTED, VOID, scope_overlaps)
from conftest import make_bundle, make_card


# ---------------------------------------------------------------------------
# Tasks and admission
# ---------------------------------------------------------------------------

def test_task_is_created_and_admitted(kernel):
    card = make_card(kernel)
    assert card.id == "T-0001"
    assert card.state == READY
    assert kernel.state().tasks["T-0001"].state == READY


def test_task_without_oracle_is_not_admitted(kernel):
    card = make_card(kernel, oracles=[])
    assert card.state == PROPOSED
    assert kernel.state().tasks[card.id].state == PROPOSED


def test_task_without_goal_ref_is_not_admitted(kernel):
    card = make_card(kernel, goal_ref="")
    assert card.state == PROPOSED


def test_task_without_scope_is_not_admitted(kernel):
    card = make_card(kernel, scope={"write": [], "read": []})
    assert card.state == PROPOSED


def test_task_ids_are_sequential_and_never_reused(kernel):
    first = make_card(kernel)
    second = make_card(kernel)
    assert first.id == "T-0001"
    assert second.id == "T-0002"


def test_task_admit_reports_why_it_refused(kernel):
    card = make_card(kernel, oracles=[])
    with pytest.raises(KernelError) as exc:
        kernel.task_admit(card.id)
    assert exc.value.reason == "admission_failed"
    assert "oracle" in " ".join(exc.value.details["problems"])


# ---------------------------------------------------------------------------
# Leases and fencing
# ---------------------------------------------------------------------------

def test_claim_grants_a_lease(kernel):
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="hermes-oneshot", agent="hermes")
    assert lease.fence >= 1
    assert kernel.state().tasks[card.id].state == LEASED
    assert kernel.state().leases[card.id].fence == lease.fence


def test_claim_refuses_a_non_ready_task(kernel):
    card = make_card(kernel, oracles=[])
    with pytest.raises(KernelError) as exc:
        kernel.claim(card.id, holder="p")
    assert exc.value.reason == "not_ready"


def test_claim_refuses_when_dependencies_are_unmet(kernel):
    first = make_card(kernel)
    second = make_card(kernel, depends_on=[first.id])
    with pytest.raises(KernelError) as exc:
        kernel.claim(second.id, holder="p")
    assert exc.value.reason == "dependencies_unmet"
    assert exc.value.details["unmet"] == [first.id]


def test_claim_refuses_when_attempts_are_exhausted(kernel):
    card = make_card(kernel, attempts_max=1)
    lease = kernel.claim(card.id, holder="p")
    kernel.revoke(card.id, lease.fence, reason="test")
    with pytest.raises(KernelError) as exc:
        kernel.claim(card.id, holder="p")
    assert exc.value.reason == "attempts_exhausted"


def test_renew_requires_the_current_fence(kernel):
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    kernel.renew(card.id, lease.fence, digest="progress")
    with pytest.raises(KernelError) as exc:
        kernel.renew(card.id, lease.fence + 99)
    assert exc.value.reason == "stale_fence"


def test_revoke_bumps_the_fence(kernel):
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    new_fence = kernel.revoke(card.id, lease.fence, reason="giving up")
    assert new_fence > lease.fence
    assert kernel.state().leases.get(card.id) is None


# ---------------------------------------------------------------------------
# Scope overlap (fleet amendment D-L6)
# ---------------------------------------------------------------------------

def test_scope_overlap_detects_prefix_overlap():
    hits = scope_overlaps(["src/pmk"], ["src/pmk/events.py"])
    assert hits == [("src/pmk", "src/pmk/events.py")]


def test_scope_overlap_ignores_similar_prefixes():
    assert scope_overlaps(["src/pmk"], ["src/pmkx/a.py"]) == []


def test_scope_overlap_is_symmetric():
    assert scope_overlaps(["a/b/c.py"], ["a"]) == [("a/b/c.py", "a")]


def test_claim_refuses_overlapping_write_scope(kernel):
    """Two parallel agents on one repository conflict by construction."""
    first = make_card(kernel, scope={"write": ["src/pmk/events.py"], "read": []})
    second = make_card(kernel, scope={"write": ["src/pmk"], "read": []})
    kernel.claim(first.id, holder="p1")
    with pytest.raises(KernelError) as exc:
        kernel.claim(second.id, holder="p2")
    assert exc.value.reason == "scope_overlap"
    assert exc.value.details["conflicts"][0]["task"] == first.id


def test_disjoint_scopes_run_in_parallel(kernel):
    first = make_card(kernel, scope={"write": ["src/a.py"], "read": []})
    second = make_card(kernel, scope={"write": ["src/b.py"], "read": []})
    kernel.claim(first.id, holder="p1")
    lease = kernel.claim(second.id, holder="p2")
    assert lease.fence >= 1


# ---------------------------------------------------------------------------
# Submission and evidence
# ---------------------------------------------------------------------------

def test_submit_writes_a_bundle_and_advances_state(kernel):
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    result = kernel.submit(card.id, lease.fence, make_bundle(card.id, lease.fence))
    assert result["ok"]
    assert kernel.state().tasks[card.id].state == SUBMITTED
    assert (kernel.repo.evidence_dir / f"EB-{card.id}-{lease.fence}" /
            "bundle.json").is_file()


def test_stale_fence_submission_is_quarantined(kernel):
    """Invariant I4: a stale fence is never merged."""
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    kernel.revoke(card.id, lease.fence, reason="revoked")
    with pytest.raises(KernelError) as exc:
        kernel.submit(card.id, lease.fence, make_bundle(card.id, lease.fence))
    assert exc.value.reason == "stale_fence"
    assert (kernel.repo.quarantine_dir / f"{card.id}-{lease.fence}").is_dir()
    # The task must not have been promoted.
    assert kernel.state().tasks[card.id].state != SUBMITTED


def test_bundle_without_oracle_results_is_refused(kernel):
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    bundle = make_bundle(card.id, lease.fence)
    bundle.oracle_results = []
    with pytest.raises(KernelError) as exc:
        kernel.submit(card.id, lease.fence, bundle)
    assert exc.value.reason == "invalid_bundle"


def test_bundle_with_inconsistent_oracle_is_refused(kernel):
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    bundle = make_bundle(card.id, lease.fence)
    bundle.oracle_results[0].exit = 1
    bundle.oracle_results[0].ok = True      # claims ok but exited 1
    with pytest.raises(KernelError) as exc:
        kernel.submit(card.id, lease.fence, bundle)
    assert exc.value.reason == "invalid_bundle"


def test_bundle_without_constitution_hash_is_refused(kernel):
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    bundle = make_bundle(card.id, lease.fence)
    bundle.constitution_hash = ""
    with pytest.raises(KernelError) as exc:
        kernel.submit(card.id, lease.fence, bundle)
    assert exc.value.reason == "invalid_bundle"


def test_integrate_promotes_to_done(kernel):
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    kernel.submit(card.id, lease.fence, make_bundle(card.id, lease.fence))
    kernel.verify(card.id, lease.fence, ok=True)
    kernel.integrate(card.id, lease.fence)
    assert kernel.state().tasks[card.id].state == DONE


def test_premise_refutation_voids_the_task(kernel):
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    kernel.premise_refuted(card.id, lease.fence, reason="P1 is false")
    assert kernel.state().tasks[card.id].state == VOID


# ---------------------------------------------------------------------------
# Queue and incidents
# ---------------------------------------------------------------------------

def test_queue_item_carries_recommendation_and_safe_default(kernel):
    item_id = kernel.queue_add(topic="Choose a provider",
                                options=["a", "b"], recommended="a",
                                safe_default="b", class_k=True)
    items = kernel.queue_list()
    item = next(i for i in items if i["id"] == item_id)
    assert item["recommended"] == "a"
    assert item["safe_default"] == "b"
    assert item["class_k"] is True
    assert item["state"] == "open"


def test_queue_decision_closes_the_item(kernel):
    item_id = kernel.queue_add(topic="x", options=["a", "b"])
    kernel.queue_decide(item_id, "a")
    item = next(i for i in kernel.queue_list() if i["id"] == item_id)
    assert item["state"] == "decided"
    assert item["choice"] == "a"


def test_incident_is_recorded(kernel):
    kernel.incident("T-0001", "something broke", severity="error")
    assert any(i["message"] == "something broke"
               for i in kernel.state().incidents)


# ---------------------------------------------------------------------------
# Stop the line
# ---------------------------------------------------------------------------

def test_stop_file_blocks_mutation(kernel):
    kernel.repo.stop_file.parent.mkdir(parents=True, exist_ok=True)
    kernel.repo.stop_file.write_text("stop\n", encoding="utf-8")
    assert kernel.stopped()
    with pytest.raises(KernelError) as exc:
        make_card(kernel)
    assert exc.value.reason == "stopped"
