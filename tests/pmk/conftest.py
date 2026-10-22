"""Shared fixtures for the Kernel tests."""

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
from pmk.policy import DEFAULT_POLICY  # noqa: E402
from pmk.store import Repo  # noqa: E402


@pytest.fixture()
def repo(tmp_path: Path) -> Repo:
    """A repository with the layout, the constitution, and no log yet."""
    r = Repo(tmp_path / "repo")
    r.ensure_layout()
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


def make_card(kernel: Kernel, **overrides):
    """Create an admissible task card with sensible defaults."""
    kwargs = dict(
        title="Do the thing",
        type="implement",
        goal_ref="G-001",
        scope={"write": ["src/thing.py"], "read": ["src/"]},
        oracles=["pytest -q tests/test_thing.py"],
        budget={"tokens": 10000, "wall_min": 10},
    )
    kwargs.update(overrides)
    return kernel.task_create(**kwargs)


def make_bundle(task_id: str, fence: int, *, ok: bool = True,
                outputs=None, resolved_models=None):
    """A valid evidence bundle."""
    from pmk.bundle import Bundle, CommandResult, OracleResult
    return Bundle(
        task=task_id,
        fence=fence,
        base_commit="abc123",
        outputs=outputs or [{"path": "src/thing.py", "sha256": "deadbeef"}],
        diff_scope_check={"violations": []},
        commands=[CommandResult(cmd="pytest -q", cwd=".", exit=0,
                                stdout_hash="h1", stderr_hash="h2")],
        oracle_results=[OracleResult(cmd="pytest -q", exit=0 if ok else 1, ok=ok,
                                     stdout_hash="h1", stderr_hash="h2")],
        premise_check={"refuted": False},
        budget_used={"tokens": 1200, "wall_min": 3},
        resolved_models=resolved_models or [{"provider": "fake", "model": "fake-1"}],
        constitution_hash="c0n5t1tut10n",
        context_hash="c0nt3xth4sh",
    )
