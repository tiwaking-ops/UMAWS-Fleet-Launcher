"""Tests for the worktree-lifecycle remediation.

Covers the operator surface over ``work/`` (REC-04), the sentinel ``I17``
observation (REC-06), capture-before-reclaim (REC-02, REC-01), the
``SUPERSEDED_BY`` traceability record (REC-11), and the stale-``agent_hint``
guard at claim time (REC-13).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from pmk import plat, worktrees
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


def test_capture_restores_binary_and_crlf_untracked_bytes(kernel, repo):
    """A capture is restorable only if the bytes come back unchanged.

    The untracked tar is byte-oriented, but nothing proved it round-trips
    content that is not valid UTF-8: NUL bytes, a lone 0xff, and the CRLF
    pairs that the live repository stores in ``docs/rules/**``.
    """
    import tarfile

    tree = _make_worktree(repo, "T-0001-1")
    payload = bytes(range(256)) + b"\x00\xff\xfe\r\n"
    (tree / "blob.bin").write_bytes(payload)
    (tree / "notes.txt").write_bytes(b"one\r\ntwo\r\n")

    result = worktrees.archive_tree(repo, kernel.state(), tree)
    assert result["archived"] is True
    dest = Path(result["dest"])
    ok, problems = worktrees.verify_archive(dest)
    assert ok, problems

    with tarfile.open(dest / "untracked.tar") as tf:
        assert tf.extractfile("blob.bin").read() == payload
        assert tf.extractfile("notes.txt").read() == b"one\r\ntwo\r\n"


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


def test_verify_archive_rejects_a_digest_that_does_not_match_contents(
        kernel, repo):
    """H3: a self-consistent manifest cannot hide a bad archive digest."""
    tree = _make_worktree(repo, "T-0001-1")
    (tree / "new.py").write_text("print(1)\n", encoding="utf-8")
    dest = Path(worktrees.archive_tree(repo, kernel.state(), tree)["dest"])

    manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
    manifest["tree_digest"] = "0" * 64
    (dest / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    ok, problems = worktrees.verify_archive(dest)
    assert not ok
    assert any("tree_digest" in p for p in problems)


def test_reclaim_refuses_when_the_capture_does_not_restore(
        kernel, repo, monkeypatch):
    """A capture that cannot be applied to its base is not restorable."""
    tree = _make_worktree(repo, "T-0001-1")
    (tree / "README.md").write_text("# captured\n", encoding="utf-8")
    capture = worktrees.archive_tree(repo, kernel.state(), tree)
    dest = Path(capture["dest"])

    # Move the recorded base somewhere the captured patch cannot apply.
    (repo.root / "README.md").write_text("# different base\n",
                                          encoding="utf-8")
    assert repo.git("add", "README.md")[0] == 0
    assert repo.git("commit", "-m", "different base")[0] == 0
    manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
    manifest["base_commit"] = repo.head_commit()
    (dest / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    # Reuse the already-verified archive; otherwise reclaim would capture
    # against the new HEAD instead of exercising its recorded base.
    monkeypatch.setattr(worktrees, "archive_tree",
                        lambda *args, **kwargs: capture)

    result = worktrees.reclaim_after_capture(repo, kernel.state(), tree)

    assert result["reclaimed"] is False
    assert "restore" in result["reason"].lower()
    assert result["archived"] is True
    assert tree.is_dir()
    assert dest.is_dir()


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
# REC-01 -- reclaim a bumped lease's worktree, capture-first
# ---------------------------------------------------------------------------

def test_reclaim_captures_then_removes(kernel, repo):
    tree = _make_worktree(repo, "T-0001-1")
    (tree / "README.md").write_text("# stranded\n", encoding="utf-8")
    (tree / "new.py").write_text("print(1)\n", encoding="utf-8")

    result = worktrees.reclaim_after_capture(repo, kernel.state(), tree)

    assert result["reclaimed"] is True
    assert result["archived"] is True
    assert not tree.exists()
    dest = repo.root / "stranded" / "T-0001-1"
    ok, problems = worktrees.verify_archive(dest)
    assert ok, problems


def test_reclaim_preserves_binary_and_crlf_captures(kernel, repo):
    """A reclaim may only remove a tree whose bytes it can give back.

    Archive self-verification does not prove restore.  After the tree is
    gone, the untracked tar must reproduce a binary file byte for byte and
    the patch must rebuild a CRLF file on its recorded base.
    """
    import tarfile

    subprocess.run(["git", "config", "core.autocrlf", "false"],
                   cwd=repo.root, capture_output=True)
    tree = _make_worktree(repo, "T-0001-1")
    crlf = tree / "crlf.txt"
    crlf.write_bytes(b"alpha\r\nbeta\r\n")
    subprocess.run(["git", "add", "crlf.txt"], cwd=tree,
                   capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "crlf base"], cwd=tree,
                   capture_output=True, check=True)
    crlf.write_bytes(b"alpha\r\nBETA\r\n")

    payload = bytes(range(256)) + b"\x00\xff\xfe\r\n"
    (tree / "blob.bin").write_bytes(payload)

    result = worktrees.reclaim_after_capture(repo, kernel.state(), tree)

    assert result["reclaimed"] is True
    assert result["restore_verified"] is True
    assert not tree.exists()

    dest = repo.root / "stranded" / "T-0001-1"
    ok, problems = worktrees.verify_archive(dest)
    assert ok, problems
    assert b"\r\n" in (dest / "diff.patch").read_bytes()

    with tarfile.open(dest / "untracked.tar") as tf:
        assert tf.extractfile("blob.bin").read() == payload

    manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
    restore = repo.root / ".restore-check"
    subprocess.run(["git", "worktree", "add", "--detach", str(restore),
                    manifest["base_commit"]], cwd=repo.root,
                   capture_output=True, check=True)
    try:
        applied = subprocess.run(["git", "apply", str(dest / "diff.patch")],
                                 cwd=restore, capture_output=True, text=True)
        assert applied.returncode == 0, applied.stderr
        assert (restore / "crlf.txt").read_bytes() == b"alpha\r\nBETA\r\n"
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(restore)],
                       cwd=repo.root, capture_output=True)


def test_reclaim_of_a_clean_tree_still_archives_a_manifest(kernel, repo):
    tree = _make_worktree(repo, "T-0001-1")          # nothing changed
    result = worktrees.reclaim_after_capture(repo, kernel.state(), tree)
    assert result["reclaimed"] is True
    assert (repo.root / "stranded" / "T-0001-1" / "manifest.json").is_file()
    assert not tree.exists()


# ---------------------------------------------------------------------------
# H1 -- deletion is limited to an unprotected, inactive lease worktree
# ---------------------------------------------------------------------------

def test_reclaim_refuses_an_active_lease(kernel, repo):
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    tree = _make_worktree(repo, f"{card.id}-{lease.fence}")
    (tree / "README.md").write_text("# stranded\n", encoding="utf-8")

    result = worktrees.reclaim_after_capture(repo, kernel.state(), tree)

    assert result["reclaimed"] is False
    assert "active lease" in result["reason"]
    assert tree.is_dir()
    assert not (repo.root / "stranded").exists()


def test_reclaim_refuses_protected_context_sync(kernel, repo):
    tree = repo.work_dir / "context-sync"
    tree.mkdir(parents=True)

    result = worktrees.reclaim_after_capture(repo, kernel.state(), tree)

    assert result["reclaimed"] is False
    assert "protected" in result["reason"]
    assert tree.is_dir()


def test_reclaim_refuses_a_path_outside_the_worktree_root(kernel, repo):
    tree = repo.root / "outside"
    tree.mkdir()

    result = worktrees.reclaim_after_capture(repo, kernel.state(), tree)

    assert result["reclaimed"] is False
    assert "direct child" in result["reason"]
    assert tree.is_dir()
    assert not (repo.root / "stranded").exists()


def test_prune_does_not_delete_an_active_lease_even_when_allowed(kernel, repo):
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    tree = _make_worktree(repo, f"{card.id}-{lease.fence}")

    result = worktrees.prune(repo, kernel.state(), dry_run=False,
                             keep_unmerged=False)

    assert result["removed"] == []
    assert tree.is_dir()
    assert any("active lease" in s["reason"] for s in result["skipped"])


def test_reclaim_keeps_the_tree_when_the_capture_does_not_verify(
        kernel, repo, monkeypatch):
    tree = _make_worktree(repo, "T-0001-1")
    (tree / "README.md").write_text("# stranded\n", encoding="utf-8")
    monkeypatch.setattr(worktrees, "verify_archive",
                        lambda dest: (False, ["simulated corruption"]))

    result = worktrees.reclaim_after_capture(repo, kernel.state(), tree)

    assert result["reclaimed"] is False
    assert "not verified" in result["reason"]
    assert tree.is_dir()                              # kept, not deleted


def test_reclaim_reports_a_missing_worktree(kernel, repo):
    result = worktrees.reclaim_after_capture(
        repo, kernel.state(), repo.work_dir / "T-0001-404")
    assert result["reclaimed"] is False
    assert result["reason"] == "not on disk"


# ---------------------------------------------------------------------------
# REC-05 -- the prompt names the handoff
# ---------------------------------------------------------------------------

def test_order_prompt_names_the_handoff_file(tmp_path):
    from fleet.order import order_prompt
    text = order_prompt(tmp_path)
    assert "HANDOFF.md" in text


# ---------------------------------------------------------------------------
# H2 -- a capture is complete, or it fails and the tree stays
# ---------------------------------------------------------------------------

def _phantom_untracked(monkeypatch, missing: str = "ghost.py") -> None:
    """Make ``ls-files`` list a file that vanishes before it is packed."""
    real = worktrees._list_paths

    def listing(repo_, tree, *, ignored=False):
        paths = real(repo_, tree, ignored=ignored)
        return paths if ignored else paths + [missing]

    monkeypatch.setattr(worktrees, "_list_paths", listing)


def test_capture_fails_closed_when_a_listed_file_cannot_be_read(
        kernel, repo, monkeypatch):
    """H2: a file that disappears between listing and packing fails it."""
    tree = _make_worktree(repo, "T-0001-1")
    (tree / "README.md").write_text("# changed\n", encoding="utf-8")
    (tree / "new.py").write_text("print(1)\n", encoding="utf-8")
    _phantom_untracked(monkeypatch)

    result = worktrees.archive_tree(repo, kernel.state(), tree)

    assert result["archived"] is False
    assert "ghost.py" in result["reason"]
    # The partial archive was discarded; it must not look like a capture.
    assert not (repo.root / "stranded" / "T-0001-1").exists()
    assert tree.is_dir()


def test_archive_fails_when_a_file_appears_during_capture(
        kernel, repo, monkeypatch):
    """H2: the post-capture re-scan must reject a late file."""
    tree = _make_worktree(repo, "T-0001-1")
    (tree / "new.py").write_text("print(1)\n", encoding="utf-8")
    real_pack = worktrees._pack_files

    def pack_then_add(worktree, files, tar_path, hasher, tag):
        packed = real_pack(worktree, files, tar_path, hasher, tag)
        if tag == "u" and not (worktree / "late.txt").exists():
            (worktree / "late.txt").write_text("late\n", encoding="utf-8")
        return packed

    monkeypatch.setattr(worktrees, "_pack_files", pack_then_add)

    result = worktrees.archive_tree(repo, kernel.state(), tree)

    assert result["archived"] is False
    assert "changed" in result["reason"]
    assert not (repo.root / "stranded" / "T-0001-1").exists()


def test_reclaim_keeps_the_tree_when_the_capture_omits_a_file(
        kernel, repo, monkeypatch):
    tree = _make_worktree(repo, "T-0001-1")
    (tree / "README.md").write_text("# stranded\n", encoding="utf-8")
    (tree / "new.py").write_text("print(1)\n", encoding="utf-8")
    _phantom_untracked(monkeypatch)

    result = worktrees.reclaim_after_capture(repo, kernel.state(), tree)

    assert result["reclaimed"] is False
    assert result["archived"] is False
    assert "ghost.py" in result["reason"]
    assert tree.is_dir()                          # the only copy survives


def test_a_second_capture_never_overwrites_the_first(kernel, repo):
    tree = _make_worktree(repo, "T-0001-1")
    (tree / "README.md").write_text("# first\n", encoding="utf-8")
    first = Path(worktrees.archive_tree(repo, kernel.state(), tree)["dest"])
    first_manifest = (first / "manifest.json").read_bytes()

    (tree / "README.md").write_text("# second\n", encoding="utf-8")
    second = Path(worktrees.archive_tree(repo, kernel.state(), tree)["dest"])

    assert second != first
    assert (first / "manifest.json").read_bytes() == first_manifest
    assert "first" in (first / "diff.patch").read_text(encoding="utf-8")
    assert worktrees.verify_archive(first)[0]
    assert worktrees.verify_archive(second)[0]


def test_ignored_files_are_part_of_the_capture(kernel, repo):
    """A tree git calls clean can still hold a file only it has."""
    (repo.root / ".gitignore").write_text("*.log\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=repo.root, check=True,
                   capture_output=True)
    subprocess.run(["git", "commit", "-m", "ignore logs"], cwd=repo.root,
                   check=True, capture_output=True)
    tree = _make_worktree(repo, "T-0001-1")
    (tree / "debug.log").write_bytes(b"only copy\n")

    result = worktrees.archive_tree(repo, kernel.state(), tree)
    dest = Path(result["dest"])
    manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["ignored_count"] == 1
    with tarfile.open(dest / "ignored.tar") as tf:
        assert "debug.log" in tf.getnames()
        assert tf.extractfile("debug.log").read() == b"only copy\n"
    assert worktrees.verify_archive(dest)[0]

    again = worktrees.reclaim_after_capture(repo, kernel.state(), tree)
    assert again["reclaimed"] is True
    assert not tree.exists()


def test_verify_archive_rejects_a_manifest_whose_counts_disagree(kernel, repo):
    tree = _make_worktree(repo, "T-0001-1")
    (tree / "new.py").write_text("print(1)\n", encoding="utf-8")
    dest = Path(worktrees.archive_tree(repo, kernel.state(), tree)["dest"])

    manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
    manifest["untracked_packed"] = 0
    (dest / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    ok, problems = worktrees.verify_archive(dest)
    assert not ok
    assert any("untracked_packed" in p for p in problems)


# ---------------------------------------------------------------------------
# H4 -- no reclamation while a writer may still exist
# ---------------------------------------------------------------------------

def test_reclaim_refuses_while_a_recorded_process_is_alive(
        kernel, repo, tmp_path):
    card = make_card(kernel)
    lease = kernel.claim(card.id, holder="p")
    tree = _make_worktree(repo, f"{card.id}-{lease.fence}")
    (tree / "README.md").write_text("# stranded\n", encoding="utf-8")
    sleeper = plat.spawn([sys.executable, "-c",
                          "import time; time.sleep(60)"],
                         cwd=tmp_path, log_path=tmp_path / "sleeper.log",
                         env=dict(os.environ))
    try:
        kernel.record_event(
            "AGENT_STARTED", subject=card.id, fence=lease.fence,
            payload={"pid": sleeper.pid,
                     "creation_time": sleeper.creation_time,
                     "adapter": "fake", "profile": "fake-a"})
        # H1 must reject a live lease before H4 can inspect the writer;
        # release the lease so this test reaches the process barrier.
        kernel.revoke(card.id, lease.fence, reason="test writer barrier")

        result = worktrees.reclaim_after_capture(repo, kernel.state(), tree)

        assert result["reclaimed"] is False
        assert "writing" in result["reason"]
        assert result["processes"][0]["pid"] == sleeper.pid
        assert tree.is_dir()
        assert not (repo.root / "stranded").exists()
    finally:
        if sleeper.proc.poll() is None:
            sleeper.proc.kill()


def test_reclaim_refuses_when_the_tree_changes_during_capture(
        kernel, repo, monkeypatch):
    tree = _make_worktree(repo, "T-0001-1")
    (tree / "README.md").write_text("# captured\n", encoding="utf-8")
    real_verify = worktrees.verify_archive

    def verify_then_write(dest):
        ok, problems = real_verify(dest)
        (tree / "late.txt").write_text("written during the capture\n",
                                       encoding="utf-8")
        return ok, problems

    monkeypatch.setattr(worktrees, "verify_archive", verify_then_write)

    result = worktrees.reclaim_after_capture(repo, kernel.state(), tree)

    assert result["archived"] is True             # the capture is kept
    assert result["reclaimed"] is False
    assert "changed" in result["reason"]
    assert tree.is_dir()
    assert (tree / "late.txt").is_file()          # the late write survives


def test_reclaim_refuses_when_another_reclaim_holds_the_lock(kernel, repo):
    tree = _make_worktree(repo, "T-0001-1")
    lock = worktrees._lock_path(tree)
    lock.write_text(json.dumps({
        "pid": os.getpid(),
        "creation_time": plat.process_info(os.getpid()).creation_time,
    }), encoding="utf-8")
    try:
        result = worktrees.reclaim_after_capture(repo, kernel.state(), tree)

        assert result["reclaimed"] is False
        assert "reclaim" in result["reason"]
        assert tree.is_dir()
        assert not (repo.root / "stranded").exists()
    finally:
        lock.unlink()


def test_reclaim_refuses_a_start_record_without_a_pid(kernel, repo):
    """H4: no pid means quiescence cannot be proven, so the tree stays."""
    tree = _make_worktree(repo, "T-0001-1")
    (tree / "README.md").write_text("# stranded\n", encoding="utf-8")
    kernel.record_event(
        "AGENT_STARTED", subject="T-0001", fence=1,
        payload={"pid": None, "adapter": "fake", "profile": "fake-a"})

    result = worktrees.reclaim_after_capture(repo, kernel.state(), tree)

    assert result["reclaimed"] is False
    assert "no pid" in result["reason"]
    assert tree.is_dir()
    assert not (repo.root / "stranded").exists()
