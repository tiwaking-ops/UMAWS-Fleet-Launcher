"""Prune must report %TEMP%/pmk-merge-* scratch trees without deleting them (H7)."""

from __future__ import annotations

from pathlib import Path

from pmk import worktrees


def test_prune_reports_merge_trees_and_leaves_them_intact(kernel, repo, tmp_path, monkeypatch):
    merge = tmp_path / "pmk-merge-abc123"
    merge.mkdir()
    (merge / "payload.txt").write_text("data", encoding="utf-8")
    other = tmp_path / "other-merge-dir"
    other.mkdir()

    orig = worktrees.discover_merge_trees
    monkeypatch.setattr(worktrees, "discover_merge_trees",
                        lambda temp_root=None: orig(tmp_path))

    result = worktrees.prune(repo, kernel.state())

    assert result["dry_run"] is True
    assert "merge_trees" in result
    entries = {e["name"]: e for e in result["merge_trees"]}
    assert "pmk-merge-abc123" in entries
    assert "other-merge-dir" not in entries
    assert entries["pmk-merge-abc123"]["path"] == str(merge)
    assert entries["pmk-merge-abc123"]["bytes"] >= len("data")
    assert merge.is_dir()
    assert (merge / "payload.txt").is_file()


def test_prune_non_dry_run_does_not_remove_merge_trees(kernel, repo, tmp_path, monkeypatch):
    merge = tmp_path / "pmk-merge-keepme"
    merge.mkdir()
    (merge / "f.txt").write_text("x", encoding="utf-8")

    orig = worktrees.discover_merge_trees
    monkeypatch.setattr(worktrees, "discover_merge_trees",
                        lambda temp_root=None: orig(tmp_path))

    result = worktrees.prune(repo, kernel.state(), dry_run=False)

    assert "merge_trees" in result
    assert any(e["name"] == "pmk-merge-keepme" for e in result["merge_trees"])
    assert merge.is_dir()
    assert (merge / "f.txt").is_file()
