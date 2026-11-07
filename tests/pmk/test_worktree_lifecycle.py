"""Tests for the worktree-lifecycle remediation (REC-04, REC-06, REC-11, REC-13).

Covers the operator surface over ``work/``, the sentinel ``I17`` observation,
the ``SUPERSEDED_BY`` traceability record, and the stale-``agent_hint``
guard at claim time.
"""

from __future__ import annotations

import subprocess

import pytest

from pmk import worktrees
from pmk.api import KernelError
from pmk.sentinel import check
from conftest import make_bundle, make_card


# ---------------------------------------------------------------------------
# REC-04 / REC-06 -- worktree listing, stats and prune
# ---------------------------------------------------------------------------

def test_parse_name_accepts_task_fence_and_rejects_others():
    assert worktrees.parse_name("T-0001-42") == ("T-0001", 42)
    assert worktrees.parse_name("context-sync") == ("context-sync", None)
    assert worktrees.parse_name("random") == ("random", None)


def test_stats_is_zero_without_a_work_dir(kernel):
    assert worktrees.stats(kernel.repo) == {"count": 0, "bytes": 0, "dirty": 0}


def test_records_counts_bytes_and_protects_context_sync(kernel, repo):
    (repo.work_dir / "context-sync").mkdir(parents=True)
    (repo.work_dir / "context-sync" / "junk.bin").write_bytes(b"x" * 100)
    tree = repo.work_dir / "T-0001-7"
    tree.mkdir()
    (tree / "work.py").write_bytes(b"y" * 250)

    recs = worktrees.records(repo, kernel.state())
    names = [r["name"] for r in recs]
    assert names == ["T-0001-7"]          # context-sync excluded
    assert recs[0]["task"] == "T-0001"
    assert recs[0]["fence"] == 7
    assert recs[0]["bytes"] == 250

    agg = worktrees.stats(repo)
    assert agg["count"] == 1
    assert agg["bytes"] == 250


def test_prune_is_a_dry_run_by_default(kernel, repo, monkeypatch):
    (repo.work_dir / "T-0001-7").mkdir()
    monkeypatch.setattr(worktrees, "_dirty", lambda repo, path: (False, 0))
    result = worktrees.prune(repo, kernel.state())
    assert result["dry_run"] is True
    assert result["candidates"] == ["T-0001-7"]
    assert result["removed"] == []
    assert (repo.work_dir / "T-0001-7").is_dir()   # nothing was removed


def test_prune_skips_dirty_trees_even_with_archive(kernel, repo, monkeypatch):
    (repo.work_dir / "T-0001-7").mkdir()
    monkeypatch.setattr(worktrees, "_dirty", lambda repo, path: (True, 3))
    result = worktrees.prune(repo, kernel.state(), archive=True)
    assert result["candidates"] == []
    assert result["skipped"][0]["name"] == "T-0001-7"
    assert "REC-02" in result["skipped"][0]["reason"]


def test_prune_honours_the_void_age_threshold(kernel, repo, monkeypatch):
    (repo.work_dir / "T-0001-7").mkdir()
    monkeypatch.setattr(worktrees, "_dirty", lambda repo, path: (False, 0))
    # A threshold with no matching VOID task excludes everything.
    result = worktrees.prune(repo, kernel.state(), older_than_days=1.0)
    assert result["candidates"] == []
    assert result["skipped"][0]["name"] == "T-0001-7"


# ---------------------------------------------------------------------------
# REC-06 -- sentinel I17
# ---------------------------------------------------------------------------

def test_sentinel_checks_i17_and_it_is_non_stopping(kernel):
    report = check(kernel)
    assert "I17" in report["checked"]
    assert all(not f["stops"] for f in report["findings"]
               if f["invariant"] == "I17")


def test_sentinel_i17_flags_an_oversized_worktree_store(kernel, repo,
                                                        monkeypatch):
    (repo.work_dir / "T-0001-7").mkdir()
    big = 3 * 1024 * 1024 * 1024       # over the 2 GiB default cap
    monkeypatch.setattr(
        worktrees, "records",
        lambda repo, state, **kw: [{"name": "T-0001-7", "bytes": big,
                                    "age_days": 0.0, "state": "VOID"}])
    report = check(kernel)
    i17 = [f for f in report["findings"] if f["invariant"] == "I17"]
    assert i17 and "over the 2048 MiB cap" in i17[0]["detail"]


# ---------------------------------------------------------------------------
# REC-11 -- SUPERSEDED_BY clears the empty-commit finding
# ---------------------------------------------------------------------------

def _done_with_empty_commit(kernel):
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    kernel.submit(card.id, lease.fence,
                  make_bundle(card.id, lease.fence, ok=True))
    kernel.verify(card.id, lease.fence, ok=True)
    kernel.record_event("INTEGRATING", subject=card.id, fence=lease.fence,
                        payload={"commit": ""})
    kernel.record_event("INTEGRATED", subject=card.id, fence=lease.fence,
                        payload={"commit": "",
                                 "bundle": f"EB-{card.id}-{lease.fence}"})
    return card


def _empty_commit_findings(report):
    return [f for f in report["findings"]
            if f["invariant"] == "I5"
            and f.get("detail", {}).get("finding") == "empty_commit_in_integrated"]


def test_supersession_clears_the_empty_commit_finding(kernel):
    card = _done_with_empty_commit(kernel)
    assert _empty_commit_findings(check(kernel)), "precondition: empty commit"

    kernel.record_supersession(card.id, commit="1a5ec9b",
                               ref="pmk/branch",
                               reason="content landed elsewhere")
    report = check(kernel)
    assert not _empty_commit_findings(report), report["findings"]


def test_record_supersession_requires_a_commit(kernel):
    card = make_card(kernel)
    with pytest.raises(KernelError) as exc:
        kernel.record_supersession(card.id, commit="   ")
    assert exc.value.reason == "invalid_supersession"


def test_record_supersession_rejects_unknown_task(kernel):
    with pytest.raises(KernelError) as exc:
        kernel.record_supersession("T-9999", commit="abc")
    assert exc.value.reason == "unknown_task"


# ---------------------------------------------------------------------------
# REC-13 -- stale agent_hint is refused at claim time
# ---------------------------------------------------------------------------

def _advance_head(repo):
    subprocess.run(["git", "add", "-A"], cwd=repo.root, capture_output=True)
    subprocess.run(["git", "commit", "-m", "advance", "--allow-empty"],
                   cwd=repo.root, capture_output=True)


def test_a_stale_hint_about_the_tree_is_refused(kernel, repo):
    card = make_card(kernel, agent_hint="Copy the corpus into docs/rules/.")
    _advance_head(repo)
    with pytest.raises(KernelError) as exc:
        kernel.claim(card.id, holder="p")
    assert exc.value.reason == "stale_agent_hint"


def test_a_stale_hint_can_be_overridden(kernel, repo):
    card = make_card(kernel, agent_hint="Copy the corpus into docs/rules/.")
    _advance_head(repo)
    lease = kernel.claim(card.id, holder="p", allow_stale_hint=True)
    assert lease is not None


def test_a_hint_at_the_current_head_is_fine(kernel):
    card = make_card(kernel, agent_hint="Copy the corpus into docs/rules/.")
    lease = kernel.claim(card.id, holder="p")     # HEAD has not moved
    assert lease is not None


# ---------------------------------------------------------------------------
# REC-05 -- the prompt names the handoff
# ---------------------------------------------------------------------------

def test_order_prompt_names_the_handoff_file(tmp_path):
    from fleet.order import order_prompt
    text = order_prompt(tmp_path)
    assert "HANDOFF.md" in text
