"""Helper builders shared by the Fleet tests.

These live outside ``conftest.py`` so that ``tests/fleet`` and ``tests/pmk``
can be collected in one pytest invocation: a bare ``from conftest import …``
resolves to whichever ``conftest`` module was imported first.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "tests" / "fleet" / "fixtures"


def _toml_value(value) -> str:
    """Render a scalar the way TOML expects: booleans are lower case."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    return str(value)


def write_agents(repo, profiles: list[dict], fleet: dict | None = None,
                 overseer: dict | None = None) -> None:
    """Write an ``agents.toml`` with the given profiles."""
    lines = ["[fleet]"]
    for key, value in (fleet or {"max_total_agents": 20,
                                 "dispatch_tick_s": 1,
                                 "stall_minutes": 15,
                                 "min_free_ram_mb": 0}).items():
        lines.append(f"{key} = {_toml_value(value)}")
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


def make_task(kernel, **overrides):
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
