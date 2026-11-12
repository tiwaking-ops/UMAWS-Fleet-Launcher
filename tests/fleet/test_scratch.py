"""The fleet's throwaway directories: where they live, and that they go away.

Regression cover for the defect recorded in :mod:`fleet.scratch`: the merge
queue and the precheck built their scratch in the **global** ``%TEMP%``,
the lease-admission precheck never removed the directory around its
worktree at all, and ``shutil.rmtree(..., ignore_errors=True)`` hid the
Windows read-only case, so leftovers accumulated permanently.

Every test here passes its own ``temp_root``, so "nothing left behind" is
asserted against a directory this test owns rather than against a namespace
other processes are writing to.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path

from fleet import scratch
from fleet.merge import integrate
from fleet.precheck import dry_run, oracles_already_pass
from pmk.bundle import Bundle, CommandResult, OracleResult
from pmk.models import Lease

from _fleet_fixtures import make_task


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True, text=True)


def _lease_worktree(kernel, task, name: str):
    """A lease worktree on the branch the merge queue expects."""
    lease = Lease(task_id=task.id, fence=1)
    worktree = kernel.repo.root / "work" / name
    branch = f"pmk/{task.id}-{lease.fence}"
    _git(kernel.repo.root, "worktree", "add", "-B", branch, str(worktree),
         "HEAD")
    return lease, worktree


def _write_passing_bundle(kernel, task, lease) -> None:
    """Write a valid bundle with a PASSING oracle."""
    evidence_dir = kernel.repo.evidence_dir / f"EB-{task.id}-{lease.fence}"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    constitution_hash = hashlib.sha256(
        kernel.repo.constitution_path.read_text(encoding="utf-8-sig").encode("utf-8")
    ).hexdigest()
    bundle = Bundle(
        task=task.id,
        fence=lease.fence,
        base_commit="dummy",
        outputs=[],
        diff_scope_check={"ok": True, "changed": ["src/thing.py"],
                          "violations": []},
        commands=[CommandResult(cmd="echo", cwd=str(kernel.repo.root), exit=0)],
        oracle_results=[OracleResult(cmd="test -f src/thing.py",
                                     exit=0, ok=True, note="file exists")],
        premise_check={"ok": True},
        budget_used={},
        resolved_models=[],
        constitution_hash=constitution_hash,
        context_hash="",
    )
    (evidence_dir / "bundle.json").write_text(
        json.dumps(bundle.to_obj()), encoding="utf-8")


def _pmk_dirs(root: Path) -> list[str]:
    """Every ``pmk-*`` scratch directory under *root*."""
    return sorted(p.name for p in root.glob("pmk-*"))


# ---------------------------------------------------------------------------
# scratch_dir / remove_scratch
# ---------------------------------------------------------------------------

def test_scratch_dir_honours_temp_root(tmp_path):
    made = scratch.scratch_dir("pmk-merge-", tmp_path)
    assert made.parent == tmp_path
    assert made.name.startswith("pmk-merge-")


def test_remove_scratch_clears_the_read_only_bit(tmp_path):
    """Read-only files and directories are what made rmtree leak silently.

    Verified on win32: ``shutil.rmtree(path, ignore_errors=True)`` leaves the
    tree behind in all four arrangements below, and the old merge/precheck
    cleanup used exactly that call.
    """
    def arrangements():
        yield "readonly-file", lambda d: os.chmod(d / "file.txt", stat.S_IREAD)
        yield "readonly-subdir", lambda d: os.chmod(d / "sub", stat.S_IREAD)
        yield "readonly-root", lambda d: os.chmod(d, stat.S_IREAD)
        yield "readonly-all", lambda d: [os.chmod(p, stat.S_IREAD)
                                         for p in (d, d / "file.txt", d / "sub",
                                                   d / "sub" / "inner.txt")]

    for name, make_readonly in arrangements():
        tree = tmp_path / name
        (tree / "sub").mkdir(parents=True)
        (tree / "file.txt").write_text("bytes\n", encoding="utf-8")
        (tree / "sub" / "inner.txt").write_text("bytes\n", encoding="utf-8")
        make_readonly(tree)

        assert scratch.remove_scratch(tree) is True, name
        assert not tree.exists(), name


def test_remove_scratch_is_true_for_a_path_that_is_already_gone(tmp_path):
    assert scratch.remove_scratch(tmp_path / "never-existed") is True


def test_default_scratch_never_lands_in_the_global_temp(monkeypatch, tmp_path):
    """The autouse fixture: no fleet test puts scratch in the global %TEMP%."""
    fake_global = tmp_path / "global-temp"
    fake_global.mkdir()
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(fake_global))

    made = scratch.scratch_dir("pmk-merge-")        # no temp_root on purpose

    assert str(made).startswith(str(tmp_path))
    assert list(fake_global.iterdir()) == []


# ---------------------------------------------------------------------------
# the merge queue
# ---------------------------------------------------------------------------

def test_integrate_removes_its_merge_scratch_on_success(kernel, tmp_path):
    task = make_task(kernel)
    lease, worktree = _lease_worktree(kernel, task, "scratch-merge-ok")
    (worktree / "src" / "thing.py").write_text("VALUE = 99\n", encoding="utf-8")
    _write_passing_bundle(kernel, task, lease)

    result = integrate(kernel, task, lease, worktree, gate_cmd="exit 0",
                       temp_root=tmp_path)

    assert result.ok is True
    assert _pmk_dirs(tmp_path) == []


def test_integrate_removes_its_merge_scratch_on_a_red_gate(kernel, tmp_path):
    """The refusal path cleans up too: a red gate is not an excuse to leak."""
    task = make_task(kernel)
    lease, worktree = _lease_worktree(kernel, task, "scratch-merge-red")
    (worktree / "src" / "thing.py").write_text("VALUE = 99\n", encoding="utf-8")
    _write_passing_bundle(kernel, task, lease)

    result = integrate(kernel, task, lease, worktree, gate_cmd="exit 1",
                       temp_root=tmp_path)

    assert result.ok is False
    assert result.failure_class == "GATE_FAILED"
    assert _pmk_dirs(tmp_path) == []


# ---------------------------------------------------------------------------
# the precheck
# ---------------------------------------------------------------------------

def test_oracles_already_pass_removes_its_directory(kernel, tmp_path):
    """The husk leak: the directory around the worktree is ours too."""
    task = make_task(kernel, oracles=["exit 0"])

    ok, _rows = oracles_already_pass(kernel, task, temp_root=tmp_path)

    assert ok is True
    assert _pmk_dirs(tmp_path) == []


def test_oracles_already_pass_cleans_up_when_the_worktree_cannot_be_added(
        kernel, tmp_path, monkeypatch):
    """The early refusal path cleans up as well."""
    from pmk.store import Repo
    task = make_task(kernel, oracles=["exit 0"])
    monkeypatch.setattr(Repo, "default_branch", lambda self: "no-such-branch")

    ok, rows = oracles_already_pass(kernel, task, temp_root=tmp_path)

    assert ok is False
    assert rows and "error" in rows[0]
    assert _pmk_dirs(tmp_path) == []


def test_dry_run_removes_its_scratch(kernel, tmp_path):
    """A dry run that satisfies nothing still takes its directories with it."""
    task = make_task(kernel, oracles=["exit 1"])

    report = dry_run(kernel, task, temp_root=tmp_path)

    assert report["canary_valid"] is False
    assert _pmk_dirs(tmp_path) == []
