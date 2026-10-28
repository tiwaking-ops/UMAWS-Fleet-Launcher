"""Shared fixtures for the Fleet tests.

The Fleet tests run against the **fake CLI**, never a real one: fleet rule
19 says every Fleet behaviour is tested on the fake before any real CLI or
real quota is used.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pmk.api import Kernel  # noqa: E402
from pmk.clock import FakeClock  # noqa: E402
from pmk.store import Repo  # noqa: E402

FIXTURE_ROOT = ROOT / "tests" / "fleet" / "fixtures"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True, text=True)


@pytest.fixture()
def git_repo(tmp_path: Path) -> Repo:
    """A real git repository, because leases use git worktrees."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "umaws-pilot")
    _git(root, "config", "user.email", "umaws-pilot@localhost")
    _git(root, "config", "extensions.worktreeConfig", "true")
    _git(root, "config", "core.longpaths", "true")

    (root / "src").mkdir()
    (root / "src" / "thing.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "README.md").write_text("# test repo\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "initial")

    repo = Repo(root)
    repo.ensure_layout()
    constitution = ROOT / ".pm" / "constitution.md"
    if constitution.is_file():
        repo.constitution_path.write_text(
            constitution.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        repo.constitution_path.write_text("# Constitution\n", encoding="utf-8")
    return repo


@pytest.fixture()
def git_repo_master(tmp_path: Path) -> Repo:
    """A git repository whose branch is 'master', not 'main'.

    Tests that hard-code 'main' fail here; the fix uses repo.default_branch().
    """
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-b", "master")
    _git(root, "config", "user.name", "umaws-pilot")
    _git(root, "config", "user.email", "umaws-pilot@localhost")
    _git(root, "config", "extensions.worktreeConfig", "true")
    _git(root, "config", "core.longpaths", "true")

    (root / "src").mkdir()
    (root / "src" / "thing.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "README.md").write_text("# test repo\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "initial")

    repo = Repo(root)
    repo.ensure_layout()
    constitution = ROOT / ".pm" / "constitution.md"
    if constitution.is_file():
        repo.constitution_path.write_text(
            constitution.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        repo.constitution_path.write_text("# Constitution\n", encoding="utf-8")
    return repo


def write_agents(repo: Repo, profiles: list[dict], fleet: dict | None = None,
                 overseer: dict | None = None) -> None:
    """Write an ``agents.toml`` with the given profiles."""
    lines = ["[fleet]"]
    for key, value in (fleet or {"max_total_agents": 20,
                                 "dispatch_tick_s": 1,
                                 "stall_minutes": 15,
                                 "min_free_ram_mb": 0}).items():
        lines.append(f"{key} = {value}")
    lines.append("")
    lines.append("[overseer]")
    lines.append(f"profiles = {overseer or {'profiles': []}['profiles']}")
    lines.append("")
    for profile in profiles:
        lines.append("[[profile]]")
        for key, value in profile.items():
            if isinstance(value, list):
                rendered = ", ".join(f'"{v}"' for v in value)
                lines.append(f"{key} = [{rendered}]")
            elif isinstance(value, bool):
                lines.append(f"{key} = {'true' if value else 'false'}")
            elif isinstance(value, str):
                lines.append(f'{key} = "{value}"')
            else:
                lines.append(f"{key} = {value}")
        lines.append("")
    repo.agents_path.write_text("\n".join(lines), encoding="utf-8")


def fake_profile(profile_id: str = "fake-a", *, priority: int = 10,
                 scenario: str = "ok", family: str = "unknown",
                 max_concurrent: int = 2,
                 roles: list | None = None) -> dict:
    return {
        "id": profile_id,
        "adapter": "fake",
        "family": family,
        "priority": priority,
        "max_concurrent": max_concurrent,
        "via_gateway": False,
        "roles": roles or ["implement", "review", "plan", "verify"],
        "argv_new": [],
        "argv_resume": [],
        "scenario": scenario,
    }


@pytest.fixture()
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture()
def kernel(git_repo: Repo, clock: FakeClock) -> Kernel:
    k = Kernel(root=git_repo.root, clock=clock)
    k.init()
    return k


@pytest.fixture()
def fake_kernel(kernel: Kernel, git_repo: Repo) -> Kernel:
    """A kernel whose only profile is the fake CLI."""
    write_agents(git_repo, [fake_profile()])
    return kernel


def make_task(kernel: Kernel, **overrides):
    kwargs = dict(
        title="Do the thing",
        type="implement",
        goal_ref="G-001",
        scope={"write": ["src/thing.py"], "read": []},
        oracles=["pytest -q tests/test_thing.py"],
        budget={"tokens": 1000, "wall_min": 5},
    )
    kwargs.update(overrides)
    return kernel.task_create(**kwargs)
