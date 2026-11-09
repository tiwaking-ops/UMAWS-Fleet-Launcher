"""Tests for B-R2b: merge queue with temporary worktree.

These tests use REAL git in a tmp repo, with an UNRELATED uncommitted
file present in main in every case.
"""

from __future__ import annotations

import json
import sys
import tempfile
import subprocess
from pathlib import Path

import pytest

from pmk.api import Kernel
from pmk.clock import FakeClock
from pmk.store import Repo
from pmk.bundle import Bundle, CommandResult, OracleResult
from fleet.merge import integrate
from fleet import spawn as spawn_mod


def _git(repo: Repo, *args: str) -> tuple[int, str, str]:
    """Run git command in the repo."""
    return repo.git(*args)


def _make_kernel_with_git() -> tuple[Kernel, Repo]:
    """Create a kernel with a git repo that has an initial commit."""
    tmp = Path(tempfile.mkdtemp())
    r = Repo(tmp / "repo")
    r.ensure_layout()

    subprocess.run(["git", "init"], cwd=r.root, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=r.root, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=r.root, capture_output=True)
    (r.root / "README.md").write_text("# Test Repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=r.root, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=r.root, capture_output=True)

    clock = FakeClock()
    k = Kernel(root=r.root, clock=clock)
    k.init()
    return k, r


def _create_task_and_bundle(kernel: Kernel, write_scope: list[str]):
    """Create a task, claim it, and submit a passing bundle."""
    from pmk.models import DONE, LEASED

    card = kernel.task_create(
        title="Test task",
        type="implement",
        goal_ref="G-001",
        scope={"write": write_scope, "read": ["src/"]},
        oracles=["exit 0"],
        budget={"tokens": 10000, "wall_min": 10},
    )
    lease = kernel.claim(card.id, holder="fake", agent="fake", role="implement")
    # Create a proper git worktree
    worktree = spawn_mod.create_worktree(kernel.repo, card.id, lease.fence)

    # Write a file in the worktree
    for path in write_scope:
        f = worktree / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("test content\n", encoding="utf-8")

    bundle = Bundle(
        task=card.id,
        fence=lease.fence,
        base_commit=_git(kernel.repo, "rev-parse", "HEAD")[1].strip(),
        outputs=[{"path": p, "sha256": "deadbeef"} for p in write_scope],
        diff_scope_check={"violations": []},
        commands=[CommandResult(cmd="exit 0", cwd=".", exit=0, stdout_hash="h1", stderr_hash="h2")],
        oracle_results=[OracleResult(cmd="exit 0", exit=0, ok=True, stdout_hash="h1", stderr_hash="h2")],
        premise_check={"refuted": False},
        budget_used={"tokens": 1200, "wall_min": 3},
        resolved_models=[{"provider": "fake", "model": "fake-1"}],
        constitution_hash="c0n5t1tut10n",
        context_hash="c0nt3xth4sh",
    )
    kernel.submit(card.id, lease.fence, bundle)
    kernel.verify(card.id, lease.fence, ok=True)

    return card, lease, worktree


def _create_uncommitted_file_in_main(repo: Repo, filename: str, content: str = "uncommitted\n"):
    """Create an uncommitted file in the main working tree."""
    f = repo.root / filename
    f.write_text(content, encoding="utf-8")


def test_gate_fails_main_unchanged():
    """Gate fails -> main HEAD unchanged, git status identical, unrelated file untouched."""
    kernel, repo = _make_kernel_with_git()

    # Create unrelated uncommitted file in main
    _create_uncommitted_file_in_main(repo, "unrelated.txt")

    card, lease, worktree = _create_task_and_bundle(kernel, ["src/thing.py"])

    # Get main's HEAD and status before
    _, head_before, _ = _git(repo, "rev-parse", "HEAD")
    head_before = head_before.strip()
    _, status_before, _ = _git(repo, "status", "--porcelain")

    result = integrate(kernel, card, lease, worktree, gate_cmd="exit 1")

    # Get main's HEAD and status after
    _, head_after, _ = _git(repo, "rev-parse", "HEAD")
    head_after = head_after.strip()
    _, status_after, _ = _git(repo, "status", "--porcelain")

    assert result.ok is False
    assert result.failure_class == "GATE_FAILED"
    assert head_after == head_before, "main HEAD changed after gate failure"
    assert status_after == status_before, "main working tree changed after gate failure"

    # Verify unrelated file still exists
    assert (repo.root / "unrelated.txt").exists()


def test_gate_passes_main_head_is_merge_commit():
    """Gate passes -> main HEAD == merge commit == result.commit."""
    kernel, repo = _make_kernel_with_git()

    _create_uncommitted_file_in_main(repo, "unrelated.txt")

    card, lease, worktree = _create_task_and_bundle(kernel, ["src/thing.py"])

    result = integrate(kernel, card, lease, worktree, gate_cmd="exit 0")

    assert result.ok is True
    assert result.commit != ""

    _, head_after, _ = _git(repo, "rev-parse", "HEAD")
    head_after = head_after.strip()
    assert head_after == result.commit, f"main HEAD {head_after} != result.commit {result.commit}"

    # Verify unrelated file still exists
    assert (repo.root / "unrelated.txt").exists()


@pytest.mark.parametrize("exit_code,expected_ok", [(0, True), (7, False)])
def test_gate_output_is_persisted_in_the_bundle(tmp_path, exit_code, expected_ok):
    """H6: the gate verdict and its tails survive both outcomes."""
    kernel, repo = _make_kernel_with_git()
    card, lease, worktree = _create_task_and_bundle(kernel, ["src/thing.py"])
    gate_script = tmp_path / "gate_output.py"
    gate_script.write_text(
        "import sys\n"
        "print('GATE-STDOUT')\n"
        "print('GATE-STDERR', file=sys.stderr)\n"
        f"sys.exit({exit_code})\n",
        encoding="utf-8")
    gate_cmd = f'"{sys.executable}" "{gate_script}"'

    try:
        result = integrate(kernel, card, lease, worktree, gate_cmd=gate_cmd)
        assert result.ok is expected_ok, result.message

        bundle_path = (repo.evidence_dir / f"EB-{card.id}-{lease.fence}"
                       / "bundle.json")
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        output = bundle["gate_output"]
        assert output["cmd"] == gate_cmd
        assert output["exit"] == exit_code
        assert output["ok"] is expected_ok
        assert "GATE-STDOUT" in "\n".join(output["stdout_tail"])
        assert "GATE-STDERR" in "\n".join(output["stderr_tail"])
    finally:
        _git(repo, "worktree", "remove", "--force", str(worktree))


def test_main_moves_mid_run_retry_and_success():
    """Main moves mid-run -> retry and success."""
    import tempfile
    from pathlib import Path
    
    kernel, repo = _make_kernel_with_git()

    _create_uncommitted_file_in_main(repo, "unrelated.txt")

    card, lease, worktree = _create_task_and_bundle(kernel, ["src/thing.py"])
    
    # Create a gate script that commits to main ONCE (first run only)
    # This simulates another process moving main while we're in the gate
    marker_file = repo.root / ".gate_moved_marker"
    gate_script = f'''import subprocess
from pathlib import Path
marker = Path(r"{marker_file}")
if not marker.exists():
    marker.write_text("moved")
    subprocess.run(["git", "-C", r"{repo.root}", "commit", "--allow-empty", "-m", "main moved by gate"], capture_output=True)
'''
    gate_script_path = Path(tempfile.mktemp(suffix=".py"))
    gate_script_path.write_text(gate_script, encoding="utf-8")
    
    # Get main's HEAD before
    _, head_before, _ = _git(repo, "rev-parse", "HEAD")
    head_before = head_before.strip()

    result = integrate(kernel, card, lease, worktree, gate_cmd=f'python "{gate_script_path}"')

    # Get main's HEAD after
    _, head_after, _ = _git(repo, "rev-parse", "HEAD")
    head_after = head_after.strip()
    
    # Clean up
    gate_script_path.unlink(missing_ok=True)
    marker_file.unlink(missing_ok=True)

    assert result.ok is True, f"Expected retry success, got: {result.message}"
    assert result.commit != ""
    assert head_after != head_before, "main HEAD should have changed (moved by gate then merged)"
    assert head_after == result.commit, f"main HEAD {head_after} != result.commit {result.commit}"
    
    # Verify the task's file IS in main (the merge succeeded)
    task_file = repo.root / "src" / "thing.py"
    assert task_file.exists(), "Task's file should be in main after successful merge"
    assert task_file.read_text(encoding="utf-8") == "test content\n"
    
    # Verify the "moved" commit is in history
    _, log_out, _ = _git(repo, "log", "--oneline", "-5")
    assert "main moved by gate" in log_out


def test_main_moves_on_every_try_infrastructure_failed():
    """Main moves on every try -> INFRASTRUCTURE_FAILED stage main-moved after 2 retries."""
    import tempfile
    from pathlib import Path
    
    kernel, repo = _make_kernel_with_git()

    _create_uncommitted_file_in_main(repo, "unrelated.txt")

    card, lease, worktree = _create_task_and_bundle(kernel, ["src/thing.py"])
    
    # Create a gate script that commits to main EVERY TIME it runs
    # This simulates another process moving main concurrently
    gate_script = f'''import subprocess
subprocess.run(["git", "-C", r"{repo.root}", "commit", "--allow-empty", "-m", "main moved by concurrent process"], capture_output=True)
'''
    gate_script_path = Path(tempfile.mktemp(suffix=".py"))
    gate_script_path.write_text(gate_script, encoding="utf-8")
    
    # Get main's HEAD before
    _, head_before, _ = _git(repo, "rev-parse", "HEAD")
    head_before = head_before.strip()

    result = integrate(kernel, card, lease, worktree, gate_cmd=f'python "{gate_script_path}"')

    # Get main's HEAD after
    _, head_after, _ = _git(repo, "rev-parse", "HEAD")
    head_after = head_after.strip()
    
    # Clean up
    gate_script_path.unlink(missing_ok=True)

    assert result.ok is False, f"Expected INFRASTRUCTURE_FAILED, got ok={result.ok}: {result.message}"
    assert result.failure_class == "INFRASTRUCTURE_FAILED"
    assert "main-moved" in result.message.lower() or "retries" in result.message.lower(), f"Expected 'main-moved' or 'retries' in message: {result.message}"
    
    # Main should NOT have the task's merge commit (the task's changes should not be promoted)
    # But it WILL have the empty commits from the gate script (simulated concurrent moves)
    # Verify the task's file is NOT in main
    task_file = repo.root / "src" / "thing.py"
    assert not task_file.exists(), f"Task's file should not be in main after failed merge: {task_file}"
    
    # Main working tree should be clean (no half-merged state, no MERGE_HEAD, no modified tracked files)
    # Untracked files (.pm/, pytest.ini, unrelated.txt, work/) are expected and OK
    _, status_after, _ = _git(repo, "status", "--porcelain")
    # Filter out untracked files (??)
    tracked_changes = [line for line in status_after.splitlines() if line and not line.startswith("??")]
    assert not tracked_changes, f"main working tree has tracked changes: {tracked_changes}"
    # No MERGE_HEAD should exist
    merge_head = repo.root / ".git" / "MERGE_HEAD"
    assert not merge_head.exists(), "MERGE_HEAD exists - merge was not aborted properly"


def test_dirt_overlapping_merge_refusal():
    """Dirt overlapping the merge -> refusal, main untouched."""
    kernel, repo = _make_kernel_with_git()

    # Create a file in main that overlaps with the task's write scope
    f = repo.root / "src" / "thing.py"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("main version\n", encoding="utf-8")

    card, lease, worktree = _create_task_and_bundle(kernel, ["src/thing.py"])

    _, head_before, _ = _git(repo, "rev-parse", "HEAD")
    head_before = head_before.strip()
    _, status_before, _ = _git(repo, "status", "--porcelain")

    result = integrate(kernel, card, lease, worktree, gate_cmd="exit 0")

    _, head_after, _ = _git(repo, "rev-parse", "HEAD")
    head_after = head_after.strip()
    _, status_after, _ = _git(repo, "status", "--porcelain")

    assert result.ok is False
    assert result.failure_class == "INFRASTRUCTURE_FAILED"
    assert head_after == head_before, "main HEAD changed despite dirty overlap"
    # The overlapping file should be present in status (git shows untracked directory as "?? src/")
    assert "?? src/" in status_after or "?? src\\" in status_after, f"Expected overlapping file in status: {status_after}"
    assert f.read_text(encoding="utf-8") == "main version\n", "overlapping file content was modified"


def test_merge_conflict_clean():
    """Merge conflict -> clean."""
    kernel, repo = _make_kernel_with_git()

    # Create a file in main that the task will also modify
    conflict_file = repo.root / "conflict.txt"
    conflict_file.write_text("main version\n", encoding="utf-8")
    subprocess.run(["git", "add", "conflict.txt"], cwd=repo.root, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add conflict.txt"], cwd=repo.root, capture_output=True)

    # Now create a task that modifies the same file
    _create_uncommitted_file_in_main(repo, "unrelated.txt")

    card = kernel.task_create(
        title="Test task",
        type="implement",
        goal_ref="G-001",
        scope={"write": ["conflict.txt"], "read": ["src/"]},
        oracles=["exit 0"],
        budget={"tokens": 10000, "wall_min": 10},
    )
    lease = kernel.claim(card.id, holder="fake", agent="fake", role="implement")
    worktree = spawn_mod.create_worktree(kernel.repo, card.id, lease.fence)

    # Worker writes a different version of the file
    conflict_wt = worktree / "conflict.txt"
    conflict_wt.write_text("worktree version\n", encoding="utf-8")

    # Now create a conflicting commit on main (simulating another task completing)
    conflict_file_main = repo.root / "conflict.txt"
    conflict_file_main.write_text("main version 2\n", encoding="utf-8")
    subprocess.run(["git", "add", "conflict.txt"], cwd=repo.root, capture_output=True)
    subprocess.run(["git", "commit", "-m", "update conflict.txt"], cwd=repo.root, capture_output=True)

    bundle = Bundle(
        task=card.id,
        fence=lease.fence,
        base_commit=_git(repo, "rev-parse", "HEAD")[1].strip(),
        outputs=[{"path": "conflict.txt", "sha256": "deadbeef"}],
        diff_scope_check={"violations": []},
        commands=[CommandResult(cmd="exit 0", cwd=".", exit=0, stdout_hash="h1", stderr_hash="h2")],
        oracle_results=[OracleResult(cmd="exit 0", exit=0, ok=True, stdout_hash="h1", stderr_hash="h2")],
        premise_check={"refuted": False},
        budget_used={"tokens": 1200, "wall_min": 3},
        resolved_models=[{"provider": "fake", "model": "fake-1"}],
        constitution_hash="c0n5t1tut10n",
        context_hash="c0nt3xth4sh",
    )
    kernel.submit(card.id, lease.fence, bundle)
    kernel.verify(card.id, lease.fence, ok=True)

    # Get main's HEAD and status before
    _, head_before, _ = _git(repo, "rev-parse", "HEAD")
    head_before = head_before.strip()
    _, status_before, _ = _git(repo, "status", "--porcelain")

    result = integrate(kernel, card, lease, worktree, gate_cmd="exit 0")

    # Get main's HEAD and status after
    _, head_after, _ = _git(repo, "rev-parse", "HEAD")
    head_after = head_after.strip()
    _, status_after, _ = _git(repo, "status", "--porcelain")

    assert result.ok is False
    assert result.conflict is True
    assert result.failure_class == "GATE_FAILED"
    assert "merge conflict" in result.message.lower()
    # Main must be untouched
    assert head_after == head_before, f"main HEAD changed despite conflict: {head_before} -> {head_after}"
    assert status_after == status_before, f"main working tree changed despite conflict: {status_after}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
