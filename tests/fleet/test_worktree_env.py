"""Every judging path must resolve the worktree under test.

The defect this file covers (report-umaws-problems-and-issues-v1 §4.1): the
harness spawned oracles with the host environment, so on this machine the
editable install's ``<repo>/src`` shadowed the worktree and a correct agent was
judged by main's code.  The merge gate had the same trap and was fixed without
a test; the workers have it too.

Each test makes the host and the worktree provide the *same* module name with
different contents, then asserts which one a real subprocess resolved.  The
oracle and worker tests fail on the unfixed code; the gate test is the
behavioural cover the gate fix never had (proven red by removing its env block
in a scratch clone).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from pmk.bundle import Bundle, CommandResult, OracleResult
from pmk.models import Lease

from fleet.harness import Harness, run_command
from fleet.merge import integrate

from conftest import make_task


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _write_module(directory: Path, name: str, token: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.py").write_text(
        f"WHERE = {token!r}\n", encoding="utf-8")
    return directory


def _worktree_with_module(tmp_path: Path, token: str = "WORKTREE") -> Path:
    wt = tmp_path / "wt"
    _write_module(wt / "src", "pkg", token)
    return wt


def _run(env: dict[str, str], wt: Path, code: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", code], cwd=str(wt), env=env,
                          capture_output=True, text=True, encoding="utf-8")


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True, text=True)


def _lease_worktree(kernel, task, name: str):
    lease = Lease(task_id=task.id, fence=1)
    worktree = kernel.repo.root / "work" / name
    branch = f"pmk/{task.id}-{lease.fence}"
    _git(kernel.repo.root, "worktree", "add", "-B", branch, str(worktree), "HEAD")
    return lease, worktree


def _write_passing_bundle(kernel, task, lease):
    evidence_dir = kernel.repo.evidence_dir / f"EB-{task.id}-{lease.fence}"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    constitution_hash = hashlib.sha256(
        kernel.repo.constitution_path.read_text(encoding="utf-8-sig").encode("utf-8")
    ).hexdigest()
    bundle = Bundle(
        task=task.id, fence=lease.fence, base_commit="dummy", outputs=[],
        diff_scope_check={"ok": True, "changed": ["src/pkg.py"], "violations": []},
        commands=[CommandResult(cmd="echo", cwd=str(lease.worktree), exit=0)],
        oracle_results=[OracleResult(cmd="test -f src/pkg.py", exit=0, ok=True)],
        premise_check={"ok": True}, budget_used={}, resolved_models=[],
        constitution_hash=constitution_hash, context_hash="",
    )
    (evidence_dir / "bundle.json").write_text(
        json.dumps(bundle.to_obj()), encoding="utf-8")


# ---------------------------------------------------------------------------
# the oracle path
# ---------------------------------------------------------------------------

def test_oracle_resolves_worktree_module(tmp_path, monkeypatch):
    host = _write_module(tmp_path / "host", "pkg", "HOST")
    wt = _worktree_with_module(tmp_path)
    monkeypatch.setenv("PYTHONPATH", str(host))

    code, out, err = run_command(
        f'"{sys.executable}" -c "import pkg; print(pkg.WHERE)"', wt)

    assert code == 0, err
    assert out.strip() == "WORKTREE", out


def test_oracle_keeps_existing_pythonpath_after_worktree(tmp_path, monkeypatch):
    host = _write_module(tmp_path / "host", "pkg", "HOST")
    _write_module(tmp_path / "host", "only_on_host", "HOSTONLY")
    wt = _worktree_with_module(tmp_path)
    monkeypatch.setenv("PYTHONPATH", str(host))

    code, out, err = run_command(
        f'"{sys.executable}" -c "import pkg, only_on_host; '
        f'print(pkg.WHERE, only_on_host.WHERE)"', wt)

    assert code == 0, err
    assert out.split() == ["WORKTREE", "HOSTONLY"], out


# ---------------------------------------------------------------------------
# the merge gate
# ---------------------------------------------------------------------------

def test_merge_gate_resolves_worktree_module(tmp_path, kernel, monkeypatch):
    task = make_task(kernel, scope={"write": ["src/pkg.py"], "read": []})
    lease, worktree = _lease_worktree(kernel, task, "env-gate")
    host = _write_module(tmp_path / "host", "pkg", "HOST")
    monkeypatch.setenv("PYTHONPATH", str(host))
    try:
        _write_module(worktree / "src", "pkg", "WORKTREE")
        _write_passing_bundle(kernel, task, lease)
        gate = (f'"{sys.executable}" -c "import pkg, sys; '
                f"sys.exit(0 if pkg.WHERE == 'WORKTREE' else 1)\"")
        result = integrate(kernel, task, lease, worktree, gate_cmd=gate)
        assert result.ok, result.message
        assert result.gate_exit == 0
    finally:
        _git(kernel.repo.root, "worktree", "remove", "--force", str(worktree))


# ---------------------------------------------------------------------------
# the worker path
# ---------------------------------------------------------------------------

def test_worker_env_resolves_worktree_module(tmp_path, monkeypatch):
    host = _write_module(tmp_path / "host", "pkg", "HOST")
    wt = _worktree_with_module(tmp_path)
    monkeypatch.setenv("PYTHONPATH", str(host))

    env = Harness._env(SimpleNamespace(), SimpleNamespace(via_gateway=False), wt)
    proc = _run(env, wt, "import pkg; print(pkg.WHERE)")

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "WORKTREE", proc.stdout


def test_worker_env_preserves_direct_cli_environment(tmp_path, monkeypatch):
    wt = _worktree_with_module(tmp_path)
    monkeypatch.setenv("FAKE_TOKEN", "abc")

    env = Harness._env(SimpleNamespace(), SimpleNamespace(via_gateway=False), wt)

    assert env["FAKE_TOKEN"] == "abc"
    assert env["PATH"] == __import__("os").environ["PATH"]


def test_worker_env_scrubs_gateway_profile_then_prepends(tmp_path, monkeypatch):
    """Scrubbing keeps its documented prefix contract, then adds the worktree.

    ``scrub_environment`` drops known credential prefixes rather than
    allow-listing the environment (D-L3), so the assertion is about those
    prefixes, not about arbitrary names.
    """
    wt = _worktree_with_module(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("ANYROUTER_API_KEY", "sk-ar-test")

    env = Harness._env(SimpleNamespace(), SimpleNamespace(via_gateway=True), wt)

    assert "OPENAI_API_KEY" not in env
    assert "ANYROUTER_API_KEY" not in env
    assert env["PYTHONPATH"].startswith(str(wt / "src"))
