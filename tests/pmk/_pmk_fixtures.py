"""Helper builders shared by the Kernel tests.

These live outside ``conftest.py`` so that ``tests/fleet`` and ``tests/pmk``
can be collected in one pytest invocation: a bare ``from conftest import …``
resolves to whichever ``conftest`` module was imported first.
"""

from __future__ import annotations


def make_card(kernel, **overrides):
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
