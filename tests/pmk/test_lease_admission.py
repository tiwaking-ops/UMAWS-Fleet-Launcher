"""H1 — Kernel lease admission for worktree grants (T-0192).

Two refusals are required and both must be *recorded*, never silently
corrected (N-15):

* a lease whose ``worktree`` resolves to the repository root
  (``invalid_worktree``);
* a worktree grant that would carry no ``pid`` or no ``expires_at`` while the
  project is not ``RUNNING`` (``lease_incomplete``).

Non-worktree claims are untouched: the wider suite leases without a worktree,
without a pid and without an expiry, and must keep working.
"""

from __future__ import annotations

import pytest

from _pmk_fixtures import make_card
from pmk.api import KernelError


def _refusals(kernel):
    return [e for e in kernel.events() if e.type == "LEASE_REFUSED"]


def _claims(kernel):
    return [e for e in kernel.events() if e.type == "CLAIMED"]


def test_a_worktree_at_the_repository_root_is_refused(kernel, repo):
    absolute = make_card(kernel)
    with pytest.raises(KernelError) as exc:
        kernel.claim(absolute.id, holder="p", worktree=str(repo.root))
    assert exc.value.reason == "invalid_worktree"

    # The same tree named relatively, which is the shape seen in the ledger.
    relative = make_card(kernel)
    with pytest.raises(KernelError) as exc:
        kernel.claim(relative.id, holder="p", worktree=".")
    assert exc.value.reason == "invalid_worktree"

    assert [e.payload["reason"] for e in _refusals(kernel)] == [
        "invalid_worktree", "invalid_worktree"]
    # A refused grant leaves no lease behind.
    assert _claims(kernel) == []


def test_a_worktree_grant_outside_running_needs_a_pid_and_an_expiry(kernel, repo):
    card = make_card(kernel)
    worktree = repo.root / "work" / "T-1"
    worktree.mkdir(parents=True)

    with pytest.raises(KernelError) as exc:
        kernel.claim(card.id, holder="p", worktree=str(worktree))
    assert exc.value.reason == "lease_incomplete"
    assert exc.value.details["pid"] is None

    with pytest.raises(KernelError) as exc:
        kernel.claim(card.id, holder="p", worktree=str(worktree), pid=4321)
    assert exc.value.reason == "lease_incomplete"

    with pytest.raises(KernelError) as exc:
        kernel.claim(card.id, holder="p", worktree=str(worktree),
                     expires_at="2999-01-01T00:00:00Z")
    assert exc.value.reason == "lease_incomplete"

    # A pid and a future expiry are sufficient while the project is not RUNNING.
    lease = kernel.claim(card.id, holder="p", worktree=str(worktree), pid=4321,
                         expires_at="2999-01-01T00:00:00Z")
    assert lease.pid == 4321
    assert lease.expires_at == "2999-01-01T00:00:00Z"
    assert lease.worktree == str(worktree)

    assert len(_refusals(kernel)) == 3
    assert len(_claims(kernel)) == 1
    assert _refusals(kernel)[0].payload["project_state"] != "RUNNING"


def test_a_running_project_may_lease_a_worktree_without_an_expiry(kernel, repo):
    card = make_card(kernel)
    worktree = repo.root / "work" / "T-2"
    worktree.mkdir(parents=True)
    kernel.project_set_state("RUNNING", reason="H1 admission test")

    lease = kernel.claim(card.id, holder="p", worktree=str(worktree), pid=1)

    assert lease.worktree == str(worktree)
    assert _refusals(kernel) == []


def test_a_claim_without_a_worktree_is_unchanged(kernel):
    # The pre-H1 shape the rest of the suite relies on.
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    assert lease.worktree == ""
    assert lease.pid is None
    assert lease.expires_at == ""
    assert _refusals(kernel) == []
