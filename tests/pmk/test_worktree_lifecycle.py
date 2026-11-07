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
    # dirty is None (not 0): the count is not computed unless git is asked.
    assert worktrees.stats(kernel.repo) == {"count": 0, "bytes": 0,
                                            "dirty": None}


def test_stats_reports_dirty_only_when_git_is_consulted(kernel, repo,
                                                        monkeypatch):
    (repo.work_dir / "T-0001-7").mkdir()
    monkeypatch.setattr(worktrees, "_dirty", lambda repo, path: (True, 2))
    assert worktrees.stats(repo)["dirty"] is None            # git skipped
    assert worktrees.stats(repo, with_git=True)["dirty"] == 1


def test_status_does_not_claim_a_zero_dirty_count(kernel):
    # REC-06: pmk status must not report a dirty count it did not compute.
    assert kernel.status()["worktrees"]["dirty"] is None


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


def test_prune_without_archive_skips_dirty_trees(kernel, repo, monkeypatch):
    (repo.work_dir / "T-0001-7").mkdir()
    monkeypatch.setattr(worktrees, "_dirty", lambda repo, path: (True, 3))
    result = worktrees.prune(repo, kernel.state())          # no --archive
    assert result["candidates"] == []
    assert result["skipped"][0]["name"] == "T-0001-7"
    assert "REC-02" in result["skipped"][0]["reason"]


def test_prune_with_archive_and_dry_run_lists_dirty_as_candidates(
        kernel, repo, monkeypatch):
    (repo.work_dir / "T-0001-7").mkdir()
    monkeypatch.setattr(worktrees, "_dirty", lambda repo, path: (True, 3))
    result = worktrees.prune(repo, kernel.state(), archive=True)   # dry run
    assert result["dry_run"] is True
    assert result["candidates"] == ["T-0001-7"]
    assert not (repo.root / "stranded").exists()


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
# REC-02 -- capture (archive) before reclaim
# ---------------------------------------------------------------------------

def _make_worktree(repo, name):
    """Create a real git worktree at work/<name>."""
    path = repo.work_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "worktree", "add", "--detach", str(path), "HEAD"],
                   cwd=repo.root, capture_output=True)
    return path


def test_archive_tree_captures_diff_untracked_and_manifest(kernel, repo):
    import tarfile
    tree = _make_worktree(repo, "T-0001-1")
    (tree / "README.md").write_text("# changed\n", encoding="utf-8")   # tracked
    (tree / "new.py").write_text("print(1)\n", encoding="utf-8")       # untracked

    result = worktrees.archive_tree(repo, kernel.state(), tree)
    assert result["archived"] is True

    dest = repo.root / "stranded" / "T-0001-1"
    assert (dest / "manifest.json").is_file()
    assert "README.md" in (dest / "diff.patch").read_text(encoding="utf-8")
    with tarfile.open(dest / "untracked.tar") as tf:
        assert "new.py" in tf.getnames()

    ok, problems = worktrees.verify_archive(dest)
    assert ok, problems
    # The capture is additive: the worktree is untouched.
    assert tree.is_dir()
    assert (tree / "new.py").is_file()


def test_archived_patch_is_byte_identical_to_git_diff(kernel, repo):
    """The capture must reproduce git's own diff byte for byte, and apply.

    Regression: repo.git() decodes stdout in text mode, which strips the CR
    from a CRLF; Path.write_text() then added the platform separator.  The
    patch looked fine and verify_archive() passed (it only hashes what was
    written), yet it no longer applied.
    """
    tree = _make_worktree(repo, "T-0001-1")
    (tree / "README.md").write_text("# changed\n", encoding="utf-8")
    dest = repo.root / "stranded" / "T-0001-1"
    worktrees.archive_tree(repo, kernel.state(), tree)

    gold = subprocess.run(["git", "diff", "HEAD", "--binary", "--", "."],
                          cwd=str(tree), capture_output=True).stdout
    assert (dest / "diff.patch").read_bytes() == gold
    assert b"\r\n" not in (dest / "manifest.json").read_bytes()

    # Round-trip: revert the tracked change, then re-apply the capture.
    subprocess.run(["git", "checkout", "--", "README.md"],
                   cwd=tree, capture_output=True)
    assert (tree / "README.md").read_text(encoding="utf-8") == "# Test Repo\n"
    applied = subprocess.run(["git", "apply", str(dest / "diff.patch")],
                             cwd=tree, capture_output=True, text=True)
    assert applied.returncode == 0, applied.stderr
    assert (tree / "README.md").read_text(encoding="utf-8") == "# changed\n"


def test_capture_preserves_crlf_so_the_patch_still_applies(kernel, repo):
    """CRs from a CRLF file must survive into the patch.

    The live repository stores ``docs/rules/**`` with CRLF, so a capture
    that drops CRs would produce a patch that cannot be applied.
    """
    subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=repo.root,
                   capture_output=True)
    tree = _make_worktree(repo, "T-0001-1")
    crlf = tree / "crlf.txt"
    crlf.write_bytes(b"one\r\ntwo\r\n")
    subprocess.run(["git", "add", "crlf.txt"], cwd=tree, capture_output=True)
    subprocess.run(["git", "commit", "-m", "crlf base"], cwd=tree,
                   capture_output=True)
    crlf.write_bytes(b"one\r\nTWO\r\n")            # modify; keep CRLF

    dest = repo.root / "stranded" / "T-0001-1"
    worktrees.archive_tree(repo, kernel.state(), tree)
    assert b"\r\n" in (dest / "diff.patch").read_bytes(), \
        "the CR from a CRLF file was stripped"

    subprocess.run(["git", "checkout", "--", "crlf.txt"], cwd=tree,
                   capture_output=True)
    applied = subprocess.run(["git", "apply", str(dest / "diff.patch")],
                             cwd=tree, capture_output=True, text=True)
    assert applied.returncode == 0, applied.stderr
    assert crlf.read_bytes() == b"one\r\nTWO\r\n"


def test_verify_archive_detects_tampering(kernel, repo):
    tree = _make_worktree(repo, "T-0001-1")
    (tree / "README.md").write_text("# changed\n", encoding="utf-8")
    dest = worktrees.archive_tree(repo, kernel.state(), tree)["dest"]

    with (repo.root / "stranded" / "T-0001-1" / "diff.patch").open(
            "a", encoding="utf-8") as fh:
        fh.write("tampered\n")
    ok, problems = worktrees.verify_archive(repo.root / "stranded" / "T-0001-1")
    assert not ok
    assert any("diff.patch" in p for p in problems)


def test_prune_archive_dry_run_writes_nothing(kernel, repo):
    tree = _make_worktree(repo, "T-0001-1")
    (tree / "README.md").write_text("# changed\n", encoding="utf-8")
    result = worktrees.prune(repo, kernel.state(), archive=True)
    assert result["dry_run"] is True
    assert result["candidates"] == ["T-0001-1"]
    assert not (repo.root / "stranded").exists()
    assert tree.is_dir()


def test_prune_archive_captures_verifies_then_removes(kernel, repo):
    tree = _make_worktree(repo, "T-0001-1")
    (tree / "README.md").write_text("# changed\n", encoding="utf-8")
    (tree / "new.py").write_text("print(1)\n", encoding="utf-8")

    result = worktrees.prune(repo, kernel.state(), dry_run=False, archive=True)
    assert result["removed"] == ["T-0001-1"]
    assert result["archived"][0]["name"] == "T-0001-1"
    # The archive survives the reclaim and is verifiable.
    dest = repo.root / "stranded" / "T-0001-1"
    assert dest.is_dir()
    ok, problems = worktrees.verify_archive(dest)
    assert ok, problems
    assert not tree.exists()


# ---------------------------------------------------------------------------
# REC-05 -- the prompt names the handoff
# ---------------------------------------------------------------------------

def test_order_prompt_names_the_handoff_file(tmp_path):
    from fleet.order import order_prompt
    text = order_prompt(tmp_path)
    assert "HANDOFF.md" in text
