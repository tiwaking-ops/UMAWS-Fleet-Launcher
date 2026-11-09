"""Shared fixtures for the Kernel tests.

The non-fixture builders live in ``_pmk_fixtures`` so they are importable by
name next to ``tests/fleet`` in one pytest invocation.
"""

from __future__ import annotations

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


@pytest.fixture()
def repo(tmp_path: Path) -> Repo:
    """A repository with the layout, the constitution, and no log yet."""
    r = Repo(tmp_path / "repo")
    r.ensure_layout()
    # Initialize git repo with an initial commit so HEAD exists
    import subprocess
    subprocess.run(["git", "init"], cwd=r.root, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=r.root, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=r.root, capture_output=True)
    # Create an initial file and commit
    (r.root / "README.md").write_text("# Test Repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=r.root, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=r.root, capture_output=True)
    # The constitution must exist for the pins to be meaningful (I8') and
    # for the briefing to carry the rules (CIP Part B 14.4).
    constitution = Path(__file__).resolve().parents[2] / ".pm" / "constitution.md"
    if constitution.is_file():
        r.constitution_path.write_text(constitution.read_text(encoding="utf-8"),
                                       encoding="utf-8")
    else:
        r.constitution_path.write_text("# Constitution\n1. The Kernel rules.\n",
                                       encoding="utf-8")
    return r


@pytest.fixture()
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture()
def kernel(repo: Repo, clock: FakeClock) -> Kernel:
    k = Kernel(root=repo.root, clock=clock)
    k.init()
    return k
