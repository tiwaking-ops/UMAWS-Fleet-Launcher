"""Regression tests for the I5 enforcement gap (T-0003).

T-0003 was promoted to ``DONE`` while its evidence bundle recorded a
**failing** acceptance oracle (``ok: false, exit: 1``).  Two independent
gates failed to stop it:

1. ``Kernel.integrate()`` accepted the promotion without ever reading the
   bundle, so a caller could promote a task with failing oracles.
2. The sentinel's I5 check called ``bundle.validation_errors()``, which
   validates the *structure* of the bundle but not whether its oracles
   passed -- so a promoted-but-failing bundle produced no finding.

Both are covered here.
"""

from __future__ import annotations

import pytest

from pmk.api import KernelError
from pmk.models import BLOCKED, DONE, LEASED, REWORK, VOID, VERIFYING
from pmk.events import Actor
from pmk.sentinel import check

from conftest import make_bundle, make_card

HUMAN = Actor.human("test-operator")


def _promote_with_failing_oracle(kernel, card, lease):
    """Submit a bundle whose oracle failed and try to promote it."""
    bundle = make_bundle(card.id, lease.fence, ok=False)
    kernel.submit(card.id, lease.fence, bundle)
    kernel.verify(card.id, lease.fence, ok=True)
    return bundle


def test_integrate_refuses_a_promotion_with_a_failing_oracle(kernel):
    """The Kernel must not promote a task whose oracles failed (I5)."""
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    _promote_with_failing_oracle(kernel, card, lease)

    with pytest.raises(KernelError) as exc:
        kernel.integrate(card.id, lease.fence, commit="test-commit")

    assert exc.value.reason == "invalid_bundle"
    assert any("oracle" in p for p in exc.value.details.get("problems", []))

    # The task must NOT be DONE.
    assert kernel.state().tasks[card.id].state != DONE


def test_integrate_refuses_a_promotion_without_a_bundle(kernel):
    """No bundle, no promotion (I6)."""
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    kernel.submit(card.id, lease.fence, make_bundle(card.id, lease.fence))
    kernel.verify(card.id, lease.fence, ok=True)

    import shutil
    shutil.rmtree(kernel.repo.evidence_dir / f"EB-{card.id}-{lease.fence}")

    with pytest.raises(KernelError) as exc:
        kernel.integrate(card.id, lease.fence, commit="test-commit")

    assert exc.value.reason == "no_bundle"
    assert kernel.state().tasks[card.id].state != DONE


def test_integrate_allows_a_promotion_with_a_passing_oracle(kernel):
    """The happy path still works."""
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    kernel.submit(card.id, lease.fence, make_bundle(card.id, lease.fence, ok=True))
    kernel.verify(card.id, lease.fence, ok=True)

    result = kernel.integrate(card.id, lease.fence, commit="test-commit")

    assert result["ok"] is True
    assert kernel.state().tasks[card.id].state == DONE


def test_sentinel_detects_promotion_with_failing_oracle(kernel):
    """A task that is DONE with a failing-oracle bundle triggers I5 (report-only).

    This is the check that would have caught T-0003 on the day.  Since the
    Kernel's integrate() guard now refuses failing bundles, we reproduce
    the T-0003 pattern by writing the INTEGRATED event directly (as the
    old code path did) to test the sentinel in isolation.
    """
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    bundle = make_bundle(card.id, lease.fence, ok=False)
    kernel.submit(card.id, lease.fence, bundle)
    kernel.verify(card.id, lease.fence, ok=True)

    # Force the promotion past the Kernel's new guard, the way the T-0003
    # path did: write the INTEGRATING/INTEGRATED events directly.
    kernel.record_event("INTEGRATING", subject=card.id, fence=lease.fence,
                        payload={"commit": "forced"})
    kernel.record_event("INTEGRATED", subject=card.id, fence=lease.fence,
                        payload={"commit": "forced",
                                 "bundle": f"EB-{card.id}-{lease.fence}"})

    assert kernel.state().tasks[card.id].state == DONE

    report = check(kernel)
    # I5 is now report-only (does not stop the pilot), so we check for the
    # finding's presence rather than report["ok"].
    assert any(f["invariant"] == "I5" for f in report["findings"]), report["findings"]


def test_sentinel_silent_for_revoked_task_with_failing_bundle(kernel):
    """A task that was promoted but then revoked (back to READY) must NOT
    trigger I5, even if its (stale) bundle had failing oracles.

    This is the T-0003 fix: T-0003 was promoted at fence 3 with a failing
    oracle, then revoked.  I5 must not flag it because the task is no longer
    DONE — it is back in READY/SUBMITTED.
    """
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    bundle = make_bundle(card.id, lease.fence, ok=False)
    kernel.submit(card.id, lease.fence, bundle)
    kernel.verify(card.id, lease.fence, ok=True)

    # Promote (force past the guard).
    kernel.record_event("INTEGRATING", subject=card.id, fence=lease.fence,
                        payload={"commit": "forced"})
    kernel.record_event("INTEGRATED", subject=card.id, fence=lease.fence,
                        payload={"commit": "forced",
                                 "bundle": f"EB-{card.id}-{lease.fence}"})
    assert kernel.state().tasks[card.id].state == DONE

    # Now revoke — the task goes back to READY (or REWORK if attempts exhausted).
    kernel.revoke(card.id, lease.fence, reason="oracle incompatible")
    assert kernel.state().tasks[card.id].state != DONE

    # I5 must NOT fire — the task is no longer DONE.
    report = check(kernel)
    i5_findings = [f for f in report["findings"] if f["invariant"] == "I5"
                   and f.get("subject") == card.id]
    assert not i5_findings, f"unexpected I5 finding for revoked task: {i5_findings}"


def test_sentinel_is_quiet_for_a_healthy_promotion(kernel):
    """The new I5 check must not fire on a legitimate promotion."""
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    kernel.submit(card.id, lease.fence, make_bundle(card.id, lease.fence, ok=True))
    kernel.verify(card.id, lease.fence, ok=True)
    kernel.integrate(card.id, lease.fence, commit="test-commit")

    report = check(kernel)
    assert not any(f["invariant"] == "I5" for f in report["findings"]), report["findings"]


# ---------------------------------------------------------------------------
# I4: a stale fence is never merged
# ---------------------------------------------------------------------------

def test_sentinel_flags_stale_fence_integration(kernel):
    """An INTEGRATED event whose fence was already revoked at that point
    must produce an I4 finding.  This is the real T-0003 pattern:
    promoted at fence 1, revoked (bumped to fence 2), then the stale
    fence-1 integration is recorded out of order."""
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    kernel.submit(card.id, lease.fence, make_bundle(card.id, lease.fence, ok=True))
    kernel.verify(card.id, lease.fence, ok=True)

    # Revoke the lease — fence goes from 1 to 2.
    new_fence = kernel.revoke(card.id, lease.fence, reason="oracle incompatible")
    assert new_fence == lease.fence + 1

    # Now record an INTEGRATED for the OLD (revoked) fence, as if the
    # stale work was merged after revocation.
    kernel.record_event("INTEGRATING", subject=card.id, fence=lease.fence,
                        payload={"commit": "stale"})
    kernel.record_event("INTEGRATED", subject=card.id, fence=lease.fence,
                        payload={"commit": "stale",
                                 "bundle": f"EB-{card.id}-{lease.fence}"})

    report = check(kernel)
    i4_findings = [f for f in report["findings"] if f["invariant"] == "I4"]
    assert i4_findings, f"expected I4 finding for stale fence, got: {report['findings']}"
    assert card.id in i4_findings[0]["subject"]
    assert "stale" in i4_findings[0]["detail"]


def test_sentinel_does_not_flag_valid_reintegration(kernel):
    """An INTEGRATED with the current fence is fine; a subsequent REVOKED
    with a new_fence does not retroactively flag the already-valid integration."""
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    kernel.submit(card.id, lease.fence, make_bundle(card.id, lease.fence, ok=True))
    kernel.verify(card.id, lease.fence, ok=True)
    kernel.integrate(card.id, lease.fence, commit="test-commit")

    # Revoking *after* a valid integration should NOT produce an I4 finding.
    kernel.revoke(card.id, lease.fence, reason="post-integration review")

    report = check(kernel)
    i4_findings = [f for f in report["findings"] if f["invariant"] == "I4"]
    assert not i4_findings, f"unexpected I4 finding: {i4_findings}"


# ---------------------------------------------------------------------------
# task_void: fail-closed actor, leased task, state guards
# ---------------------------------------------------------------------------




def test_void_from_ready(kernel):
    """A READY task may be voided by a human."""
    card = make_card(kernel)  # admitted=True → READY
    kernel.task_void(card.id, reason="cancelled", actor=HUMAN)
    assert kernel.state().tasks[card.id].state == VOID


def test_void_from_rework(kernel):
    """A REWORK task may be voided."""
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    # Drive the task into REWORK via a failed verify
    bundle = make_bundle(card.id, lease.fence, ok=True)
    kernel.submit(card.id, lease.fence, bundle)
    kernel.verify(card.id, lease.fence, ok=False, reasons=["oracle failed"])
    task = kernel.state().tasks[card.id]
    assert task.state == REWORK
    kernel.task_void(card.id, reason="abandoned", actor=HUMAN)
    assert kernel.state().tasks[card.id].state == VOID


def test_void_from_blocked(kernel):
    """A BLOCKED task may be voided."""
    card = make_card(kernel)  # admitted=True → READY
    kernel.task_block(card.id, reason="waiting on input")
    task = kernel.state().tasks[card.id]
    assert task.state == BLOCKED
    kernel.task_void(card.id, reason="no longer needed", actor=HUMAN)
    assert kernel.state().tasks[card.id].state == VOID


def test_void_leased_task_revokes_first(kernel):
    """Voiding a leased (LEASED) task revokes the lease, then voids."""
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    task = kernel.state().tasks[card.id]
    assert task.state == LEASED
    result = kernel.task_void(card.id, reason="done by hand", actor=HUMAN)
    assert result["ok"]
    assert kernel.state().tasks[card.id].state == VOID
    # The lease must be gone.
    assert card.id not in kernel.state().leases


def test_void_refused_for_done(kernel):
    """A DONE task cannot be voided."""
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    kernel.submit(card.id, lease.fence, make_bundle(card.id, lease.fence, ok=True))
    kernel.verify(card.id, lease.fence, ok=True)
    kernel.integrate(card.id, lease.fence, commit="test-commit")
    assert kernel.state().tasks[card.id].state == DONE
    with pytest.raises(KernelError) as exc:
        kernel.task_void(card.id, reason="too late", actor=HUMAN)
    assert exc.value.reason == "bad_transition"


def test_void_refused_for_void(kernel):
    """A VOID task cannot be voided again."""
    card = make_card(kernel)  # admitted=True → READY
    kernel.task_void(card.id, reason="cancelled", actor=HUMAN)
    assert kernel.state().tasks[card.id].state == VOID
    with pytest.raises(KernelError) as exc:
        kernel.task_void(card.id, reason="still cancelled", actor=HUMAN)
    assert exc.value.reason == "bad_transition"


def test_void_refused_for_non_human_actor(kernel):
    """A kernel/system actor (PMK_ACTOR unset, defaults to kernel) is refused.

    This is advisory, not a security boundary: a compromised process can set
    PMK_ACTOR=human:attacker and bypass it.  The guard exists to catch honest
    accidents and operator mistakes, not to withstand an attacker.
    """
    card = make_card(kernel)  # admitted=True → READY
    with pytest.raises(KernelError) as exc:
        kernel.task_void(card.id, reason="bot tries to void",
                         actor=Actor.kernel())
    assert exc.value.reason == "not_authorized"
    # The advisory nature: the task is still in READY, not VOID.
    assert kernel.state().tasks[card.id].state != VOID


# ---------------------------------------------------------------------------
# PMK_ACTOR attribution
# ---------------------------------------------------------------------------

def test_actor_from_env_human(monkeypatch, kernel):
    """PMK_ACTOR=human:<name> parses to a human actor."""
    from pmk.api import _actor_from_env
    monkeypatch.setenv("PMK_ACTOR", "human:alice")
    actor = _actor_from_env()
    assert actor.kind == "human"
    assert actor.agent == "alice"


def test_actor_from_env_worker(monkeypatch, kernel):
    """PMK_ACTOR=worker:<profile> parses to a worker actor."""
    from pmk.api import _actor_from_env
    monkeypatch.setenv("PMK_ACTOR", "worker:hermes-oneshot")
    actor = _actor_from_env()
    assert actor.kind == "worker"
    assert actor.agent == "hermes-oneshot"


def test_actor_from_env_unset(monkeypatch, kernel):
    """No PMK_ACTOR returns None (caller falls back to Actor.kernel())."""
    from pmk.api import _actor_from_env
    monkeypatch.delenv("PMK_ACTOR", raising=False)
    assert _actor_from_env() is None


def test_actor_from_env_unknown_kind(monkeypatch, kernel):
    """An unrecognised prefix is still resolved (best-effort)."""
    from pmk.api import _actor_from_env
    monkeypatch.setenv("PMK_ACTOR", "service:my-bot")
    actor = _actor_from_env()
    assert actor.kind == "service"


def test_submit_records_worker_actor(monkeypatch, kernel):
    """A worker spawned with PMK_ACTOR=worker:<profile> is attributed correctly."""
    monkeypatch.setenv("PMK_ACTOR", "worker:claude-3")
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    bundle = make_bundle(card.id, lease.fence, ok=True)
    kernel.submit(card.id, lease.fence, bundle)
    # The SUBMITTED event should carry the worker actor.
    events = [e for e in kernel.events() if e.subject == card.id]
    submitted = [e for e in events if e.type == "SUBMITTED"]
    assert submitted, events
    assert submitted[0].actor.kind == "worker"
    assert submitted[0].actor.agent == "claude-3"


def test_void_via_api_uses_pmk_actor(monkeypatch, kernel):
    """task_void honours PMK_ACTOR: a worker actor is refused."""
    monkeypatch.setenv("PMK_ACTOR", "worker:hermes")
    card = make_card(kernel)
    with pytest.raises(KernelError) as exc:
        kernel.task_void(card.id, reason="worker tries to void")
    assert exc.value.reason == "not_authorized"
    # Task must still be READY, not VOID.
    assert kernel.state().tasks[card.id].state != VOID


def test_void_via_cli_refused_under_worker_actormonkeypatch(monkeypatch, kernel, capsys):
    """The CLI refuses ``pmk task void`` when PMK_ACTOR names a non-human."""
    from pmk.cli import cmd_task_void
    import argparse
    monkeypatch.setenv("PMK_ACTOR", "worker:claude-3")
    card = make_card(kernel, admitted=True)
    args = argparse.Namespace(
        root=str(kernel.repo.root),
        task_id=card.id, reason="should fail", actor="operator")
    rc = cmd_task_void(args)
    assert rc != 0


# ---------------------------------------------------------------------------
# verify / submit guards
# ---------------------------------------------------------------------------

def test_submit_from_non_leased_fails(kernel):
    """submit() must refuse when the task is not LEASED.

    The task is READY (admitted) but has no lease.  We use fence=0 (the
    initial fence for a card with no lease) so the stale-fence check passes
    and we reach the state guard.
    """
    card = make_card(kernel)  # admitted=True → READY, no lease
    # No lease claimed.  fence=0 is the card's initial fence, so the stale
    # check passes and we reach the state guard.
    with pytest.raises(KernelError) as exc:
        kernel.submit(card.id, fence=0, bundle=make_bundle(card.id, 0, ok=True))
    assert exc.value.reason == "bad_transition"


def test_verify_from_done_fails(kernel):
    """verify() must refuse a DONE task (T-0009 double-integrate guard)."""
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    kernel.submit(card.id, lease.fence, make_bundle(card.id, lease.fence, ok=True))
    kernel.verify(card.id, lease.fence, ok=True)
    kernel.integrate(card.id, lease.fence, commit="test-commit")
    assert kernel.state().tasks[card.id].state == DONE
    with pytest.raises(KernelError) as exc:
        kernel.verify(card.id, lease.fence, ok=True)
    assert exc.value.reason == "bad_transition"


def test_verify_on_verifying_task_works(kernel):
    """The conductor REWORK path calls verify(ok=False) on VERIFYING tasks."""
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    kernel.submit(card.id, lease.fence, make_bundle(card.id, lease.fence, ok=True))
    # First verify -> task enters VERIFYING
    kernel.verify(card.id, lease.fence, ok=True)
    task = kernel.state().tasks[card.id]
    assert task.state == VERIFYING
    # The conductor REWORK path calls verify(ok=False) on VERIFYING.
    kernel.verify(card.id, lease.fence, ok=False, reasons=["needs rework"])
    task = kernel.state().tasks[card.id]
    assert task.state == REWORK


# ---------------------------------------------------------------------------
# Type check at create/admit (plan item 7)
# ---------------------------------------------------------------------------

def test_task_create_rejects_unknown_type(kernel):
    """task_create must reject an unknown task type at record time.

    TASK_TYPES = (implement, review, verify, plan, maintain, research).
    An unknown type is a structural refusal, not an admission error.
    """
    with pytest.raises(KernelError) as exc:
        kernel.task_create(title="bogus", type="bogus")
    assert exc.value.reason == "invalid_task_type"
    assert "bogus" in exc.value.details["valid"] or \
           exc.value.details["type"] == "bogus"


def test_task_create_accepts_all_valid_types(kernel):
    """Every type in TASK_TYPES is accepted at create time."""
    from pmk.models import TASK_TYPES
    for t in TASK_TYPES:
        card = kernel.task_create(title=f"task-{t}", type=t)
        assert card.type == t
        task = kernel.state().tasks[card.id]
        assert task.type == t


def test_task_create_type_check_runs_before_admission(kernel):
    """The type check happens before admission errors are computed.

    A card with a valid type but bad scope still records TASK_CREATED
    with admission_errors, while a card with a bad type is refused
    outright (no TASK_CREATED event).
    """
    # Bad type: raises before any event is appended.
    with pytest.raises(KernelError):
        kernel.task_create(title="bad type", type="nope",
                           scope={"write": [], "read": []})
    # No TASK_CREATED event for the bad-type card.
    created = [e for e in kernel.events() if e.type == "TASK_CREATED"]
    assert len(created) == 0

    # Good type but bad scope: TASK_CREATED is still appended, with errors.
    card = kernel.task_create(title="good type", type="implement",
                              scope={"write": [], "read": []},
                              oracles=["echo"])
    created = [e for e in kernel.events() if e.type == "TASK_CREATED"]
    assert len(created) == 1
    assert card.id == created[0].subject
