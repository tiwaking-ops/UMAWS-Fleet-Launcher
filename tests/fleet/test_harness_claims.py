"""Agent-claim checks and the main-tree path sets (R-02, R-11).

The NO_CHANGES check runs ``git status --porcelain -z`` in the worktree.  A new
file, a modified file and a rename all count as changes; ``.pmwork/`` does not;
and a git failure is *not* "no changes": the check is skipped and recorded, and
the oracles decide.
"""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

from fleet import spawn as spawn_mod
from fleet.harness import Harness, _check_agent_claims


def _git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.com",
                    *args], cwd=cwd, check=True, capture_output=True)


def _repo(tmp_path, name="wt", *, committed=()):
    wt = tmp_path / name
    wt.mkdir()
    _git(wt, "init", "-q")
    for filename in committed:
        (wt / filename).write_text("original\n", encoding="utf-8")
    if committed:
        _git(wt, "add", "-A")
        _git(wt, "commit", "-q", "-m", "base")
    return wt


def _task(task_type="implement"):
    return SimpleNamespace(id="T-0001", type=task_type, write_scope=["out.txt"],
                           read_scope=[])


def test_a_new_file_counts_as_a_change(tmp_path):
    wt = _repo(tmp_path)
    (wt / "out.txt").write_text("new\n", encoding="utf-8")
    problems, advisories = _check_agent_claims(_task(), wt, "")
    assert problems == []
    assert advisories == []


def test_a_modified_tracked_file_counts_as_a_change(tmp_path):
    wt = _repo(tmp_path, committed=("a.txt",))
    (wt / "a.txt").write_text("changed\n", encoding="utf-8")
    problems, _ = _check_agent_claims(_task(), wt, "")
    assert problems == []


def test_a_staged_rename_counts_as_a_change(tmp_path):
    wt = _repo(tmp_path, committed=("a.txt",))
    _git(wt, "mv", "a.txt", "b.txt")
    problems, _ = _check_agent_claims(_task(), wt, "")
    assert problems == []


def test_only_pmwork_files_is_no_changes(tmp_path):
    wt = _repo(tmp_path)
    (wt / ".pmwork").mkdir()
    (wt / ".pmwork" / "RESULT.md").write_text("T-0001 done", encoding="utf-8")
    problems, _ = _check_agent_claims(_task(), wt, "")
    assert any("NO_CHANGES" in p for p in problems)


def test_an_untouched_worktree_is_no_changes(tmp_path):
    wt = _repo(tmp_path, committed=("a.txt",))
    problems, _ = _check_agent_claims(_task(), wt, "")
    assert any("NO_CHANGES" in p for p in problems)


def test_a_git_failure_is_not_no_changes(tmp_path):
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    problems, advisories = _check_agent_claims(_task(), plain, "")
    assert problems == []
    assert any("NO_CHANGES check skipped" in a for a in advisories)


def test_other_task_types_skip_the_change_check(tmp_path):
    wt = _repo(tmp_path)
    problems, advisories = _check_agent_claims(_task("review"), wt, "")
    assert problems == []
    assert advisories == []


def test_a_result_md_without_the_task_id_is_an_advisory_only(tmp_path):
    wt = _repo(tmp_path)
    (wt / "out.txt").write_text("new\n", encoding="utf-8")
    (wt / ".pmwork").mkdir()
    (wt / ".pmwork" / "RESULT.md").write_text("done", encoding="utf-8")
    problems, advisories = _check_agent_claims(_task(), wt, "")
    assert problems == []
    assert any("does not mention the task id" in a for a in advisories)


def test_parse_status_z_handles_renames_and_odd_paths():
    text = "R  b.txt\0a.txt\0?? c.txt\0 M sp ace/\u00e9.py\0"
    assert spawn_mod.parse_status_z(text) == [
        ("R ", "b.txt"), ("??", "c.txt"), (" M", "sp ace/\u00e9.py")]
    assert spawn_mod.parse_status_z("") == []
    assert spawn_mod.parse_status_z("\0\0") == []


def test_new_changes_in_scope_uses_the_full_path_sets():
    """The event summary keeps 20 paths; the comparison must not."""
    dirty = frozenset(f"dirt/{i:03d}.txt" for i in range(60))
    after = dirty | {"src/thing.py", "unrelated/x.py"}
    harness = Harness.__new__(Harness)          # the comparison needs no kernel
    found = harness._new_changes_in_scope(dirty, after, ["src/thing.py"])
    assert found == ["src/thing.py"]

    # The same comparison from 20-path samples, as the old code did, misses it.
    sample_before = {"paths": sorted(dirty)[:20]}
    sample_after = {"paths": sorted(after)[:20]}
    assert harness._diff_main_tree_status(sample_before, sample_after,
                                          ["src/thing.py"]) == []


def test_a_path_dirty_at_spawn_is_not_new():
    dirty = frozenset({"src/thing.py"})
    harness = Harness.__new__(Harness)
    assert harness._new_changes_in_scope(dirty, dirty, ["src"]) == []
