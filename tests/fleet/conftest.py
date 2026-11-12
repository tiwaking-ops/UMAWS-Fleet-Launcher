"""Shared fixtures for the Fleet tests.

The Fleet tests run against the **fake CLI**, never a real one: fleet rule
19 says every Fleet behaviour is tested on the fake before any real CLI or
real quota is used.  The non-fixture builders live in ``_fleet_fixtures`` so
they are importable by name next to ``tests/pmk``.
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
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from _fleet_fixtures import fake_profile, write_agents  # noqa: E402
from pmk.api import Kernel  # noqa: E402
from pmk.clock import FakeClock  # noqa: E402
from pmk.store import Repo  # noqa: E402


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


@pytest.fixture(autouse=True)
def fleet_scratch_stays_in_tmp(monkeypatch, tmp_path: Path):
    """Fleet scratch lives under this test's ``tmp_path``, never the global temp.

    ``fleet.scratch`` built ``pmk-merge-*`` / ``pmk-precheck-*`` directories
    in the global ``%TEMP%``, which nothing ever collected: a run killed
    mid-merge left a tree there permanently, and the lease-admission
    precheck left an empty husk behind on every call.  A pytest-managed
    ``tmp_path`` goes away with the test, so a leaked scratch directory can
    no longer outlive the run that made it.

    An explicit ``temp_root`` still wins, so a test that wants to assert on
    the scratch can pass its own directory.
    """
    from fleet import scratch

    real = scratch.scratch_dir

    def scoped(prefix: str, temp_root=None):
        return real(prefix, tmp_path if temp_root is None else temp_root)

    monkeypatch.setattr(scratch, "scratch_dir", scoped)
