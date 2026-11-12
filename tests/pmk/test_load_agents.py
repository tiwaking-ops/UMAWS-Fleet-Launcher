"""Tests for R4: load_agents and pmk fleet check (B10)"""

from __future__ import annotations

import pytest
import tomllib

from pmk.policy import load_agents
from pmk.store import Repo
from pathlib import Path


def make_repo_with_agents(agents_toml: str, root: Path) -> Repo:
    """Create a temp repo with the given agents.toml content.

    *root* is a pytest-managed directory (``tmp_path``); the global-temp
    ``mkdtemp`` this used to call leaked an unprefixed directory per call.
    """
    r = Repo(root / 'repo')
    r.ensure_layout()
    r.agents_path.write_text(agents_toml, encoding="utf-8")
    return r


def test_load_agents_valid(tmp_path):
    """A valid agents.toml loads without errors."""
    agents_toml = """
[fleet]
max_total_agents = 10

[overseer]
profiles = ["profile-a"]

[[profile]]
id = "profile-a"
adapter = "fake"
family = "test"
priority = 1
max_concurrent = 1
roles = ["implement"]
argv_new = ["fake"]

[[profile]]
id = "profile-b"
adapter = "fake"
family = "test"
priority = 2
max_concurrent = 1
roles = ["implement"]
argv_new = ["fake"]
"""
    repo = make_repo_with_agents(agents_toml, tmp_path)
    result = load_agents(repo)
    
    assert result["errors"] == []
    assert result["cap_keys"] == ["fleet.max_total_agents"]
    assert len(result["profiles"]) == 2
    assert result["overseer"]["profiles"] == ["profile-a"]


def test_load_agents_duplicate_ids(tmp_path):
    """Duplicate profile ids are reported as errors."""
    agents_toml = """
[fleet]
max_total_agents = 10

[[profile]]
id = "duplicate-id"
adapter = "fake"
family = "test"
priority = 1
max_concurrent = 1
roles = ["implement"]
argv_new = ["fake"]

[[profile]]
id = "duplicate-id"
adapter = "fake"
family = "test"
priority = 2
max_concurrent = 1
roles = ["implement"]
argv_new = ["fake"]
"""
    repo = make_repo_with_agents(agents_toml, tmp_path)
    result = load_agents(repo)
    
    assert len(result["errors"]) == 1
    assert "duplicate profile ids" in result["errors"][0]
    assert "duplicate-id" in result["errors"][0]


def test_load_agents_unknown_overseer(tmp_path):
    """Overseer profiles that don't exist are reported as errors."""
    agents_toml = """
[fleet]
max_total_agents = 10

[overseer]
profiles = ["profile-a", "profile-nonexistent"]

[[profile]]
id = "profile-a"
adapter = "fake"
family = "test"
priority = 1
max_concurrent = 1
roles = ["implement"]
argv_new = ["fake"]
"""
    repo = make_repo_with_agents(agents_toml, tmp_path)
    result = load_agents(repo)
    
    assert len(result["errors"]) == 1
    assert "overseer profiles not found" in result["errors"][0]
    assert "profile-nonexistent" in result["errors"][0]


def test_load_agents_multiple_errors(tmp_path):
    """Multiple errors are all reported."""
    agents_toml = """
[fleet]
max_total_agents = 10

[overseer]
profiles = ["profile-a", "profile-nonexistent"]

[[profile]]
id = "profile-a"
adapter = "fake"
family = "test"
priority = 1
max_concurrent = 1
roles = ["implement"]
argv_new = ["fake"]

[[profile]]
id = "profile-a"
adapter = "fake"
family = "test"
priority = 2
max_concurrent = 1
roles = ["implement"]
argv_new = ["fake"]
"""
    repo = make_repo_with_agents(agents_toml, tmp_path)
    result = load_agents(repo)
    
    assert len(result["errors"]) == 2
    assert any("duplicate profile ids" in e for e in result["errors"])
    assert any("overseer profiles not found" in e for e in result["errors"])


def test_load_agents_cap_keys(tmp_path):
    """Concurrency cap keys are reported correctly."""
    # max_total_agents
    agents_toml1 = """
[fleet]
max_total_agents = 10
"""
    repo1 = make_repo_with_agents(agents_toml1, tmp_path)
    result1 = load_agents(repo1)
    assert result1["cap_keys"] == ["fleet.max_total_agents"]
    
    # fleet_cap
    agents_toml2 = """
[fleet]
fleet_cap = 20
"""
    repo2 = make_repo_with_agents(agents_toml2, tmp_path)
    result2 = load_agents(repo2)
    assert result2["cap_keys"] == ["fleet.fleet_cap"]
    
    # both
    agents_toml3 = """
[fleet]
max_total_agents = 10
fleet_cap = 20
"""
    repo3 = make_repo_with_agents(agents_toml3, tmp_path)
    result3 = load_agents(repo3)
    assert set(result3["cap_keys"]) == {"fleet.max_total_agents", "fleet.fleet_cap"}
    
    # neither
    agents_toml4 = """
[fleet]
"""
    repo4 = make_repo_with_agents(agents_toml4, tmp_path)
    result4 = load_agents(repo4)
    assert result4["cap_keys"] == []


def test_load_agents_missing_file(tmp_path):
    """Missing agents.toml returns error."""
    r = Repo(tmp_path / 'repo')
    r.ensure_layout()
    # Don't create agents.toml
    result = load_agents(r)
    
    assert len(result["errors"]) == 1
    assert "file not found" in result["errors"][0]
    assert result["profiles"] == []
    assert result["cap_keys"] == []


def test_load_agents_invalid_toml(tmp_path):
    """Invalid TOML returns error with line info."""
    r = Repo(tmp_path / 'repo')
    r.ensure_layout()
    r.agents_path.write_text("invalid toml [[[", encoding="utf-8")
    result = load_agents(r)
    
    assert len(result["errors"]) == 1
    assert "TOML parse error" in result["errors"][0]
    assert "line 1" in result["errors"][0]
    assert result["profiles"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
