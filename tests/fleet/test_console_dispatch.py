"""Console-level regression tests for D-A2: dispatch pauses until Run.

These tests use the fake CLI only.
"""

from __future__ import annotations

import subprocess

from pathlib import Path

import pytest

from pmk.api import Kernel
from pmk.clock import FakeClock

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SRC))

from console.app import Console  # noqa: E402
from conftest import fake_profile  # noqa: E402
from conftest import make_task, write_agents  # noqa: E402


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True, text=True)


def test_console_starts_with_dispatch_paused(tmp_path):
    "D-A2: Console starts with dispatch PAUSED; nothing is dispatched."
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    (repo / "src").mkdir()
    (repo / "src" / "thing.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "README.md").write_text("# test\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "initial")

    kernel = Kernel(root=repo, clock=FakeClock())
    kernel.init()
    write_agents(kernel.repo, [fake_profile()])
    make_task(kernel)

    console = Console(root=repo)
    # The Console starts paused, not running.
    assert console.fleet_state.dispatch_paused is True
    assert console.fleet_state.pause_reason
    assert console.dispatcher.fleet_state.dispatch_paused is True

    # Startup: no FLEET_ASSIGNED / AGENT_STARTED yet.
    kinds = [e.type for e in console.kernel.events()]
    assert not [k for k in kinds if k in ("FLEET_ASSIGNED", "AGENT_STARTED")]

    # The Run action resumes dispatch and events appear.
    console.fleet_state.dispatch_paused = False
    console.dispatcher.tick()
    kinds = [e.type for e in console.kernel.events()]
    assert "FLEET_ASSIGNED" in kinds
    assert "AGENT_STARTED" in kinds


def test_console_paused_until_run_with_stop_file(tmp_path):
    "D-A2: with pilot/STOP, the Console stays paused even after Run is seen."
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    (repo / "src").mkdir()
    (repo / "src" / "thing.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "README.md").write_text("# test\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "initial")

    kernel = Kernel(root=repo, clock=FakeClock())
    kernel.init()
    write_agents(kernel.repo, [fake_profile()])
    make_task(kernel)
    (repo / "pilot").mkdir(parents=True, exist_ok=True)
    (repo / "pilot" / "STOP").write_text("halt\n", encoding="utf-8")

    console = Console(root=repo)
    assert console.fleet_state.dispatch_paused is True

    # Even an explicit Run cannot dispatch while STOP is present.
    console.fleet_state.dispatch_paused = False
    console.dispatcher.tick()
    kinds = [e.type for e in console.kernel.events()]
    assert not [k for k in kinds if k in ("FLEET_ASSIGNED", "AGENT_STARTED")]

    # Removing STOP allows dispatch.
    (repo / "pilot" / "STOP").unlink()
    console.dispatcher.tick()
    kinds = [e.type for e in console.kernel.events()]
    assert "FLEET_ASSIGNED" in kinds
