"""Console startup must reconcile live workers (H3)."""

from __future__ import annotations

import importlib
import subprocess
from pathlib import Path

from pmk.api import Kernel
from pmk.clock import FakeClock

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SRC))

console_app = importlib.import_module("console.app")  # noqa: E402
Console = console_app.Console  # noqa: E402
from _fleet_fixtures import fake_profile, write_agents  # noqa: E402


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True, text=True)


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    (repo / "src").mkdir()
    (repo / "src" / "thing.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "README.md").write_text("# test\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "initial")
    return repo


def test_console_startup_reconciles_live_workers_once(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    kernel = Kernel(root=repo, clock=FakeClock())
    kernel.init()
    write_agents(kernel.repo, [fake_profile()])

    calls = {"n": 0}
    real_reconcile = Console.__module__  # keep import loaded

    from fleet.dispatcher import Dispatcher

    real = Dispatcher.reconcile

    def counted(self):
        calls["n"] += 1
        return real(self)

    monkeypatch.setattr(Dispatcher, "reconcile", counted)

    Console(root=repo)

    assert calls["n"] == 1
