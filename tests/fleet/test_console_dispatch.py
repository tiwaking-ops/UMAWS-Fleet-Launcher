"""Console-level regression tests for D-A2: dispatch pauses until Run.

These tests use the fake CLI only.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pmk.api import Kernel
from pmk.clock import FakeClock

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SRC))

console_app = importlib.import_module("console.app")  # noqa: E402
Console = console_app.Console  # noqa: E402
from _fleet_fixtures import fake_profile  # noqa: E402
from _fleet_fixtures import make_task, write_agents  # noqa: E402
from fleet.dispatcher import Dispatcher  # noqa: E402
from fleet.owner import DispatchOwner, owner_info_path  # noqa: E402
from fleet.state import FleetState  # noqa: E402


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True, text=True)


def _make_repo_with_agents(tmp_path: Path, agents_toml: str) -> Path:
    """Create a git repo with the given agents.toml content."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    (repo / "src").mkdir()
    (repo / "src" / "thing.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "README.md").write_text("# test\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "initial")
    
    # Write agents.toml
    agents_path = repo / "agents.toml"
    agents_path.write_text(agents_toml, encoding="utf-8")
    _git(repo, "add", "agents.toml")
    _git(repo, "commit", "-m", "add agents.toml")
    
    return repo


def _make_kernel_and_state(repo: Path):
    """Create a kernel with FakeClock and init it."""
    kernel = Kernel(root=repo, clock=FakeClock())
    kernel.init()
    return kernel


# Valid agents.toml using [[profile]] array-of-tables syntax
VALID_AGENTS_TOML = '''
[fleet]
max_total_agents = 10

[[profile]]
id = "fake-1"
name = "Fake Profile 1"
priority = 10
enabled = true
roles = ["implement"]

[overseer]
profiles = ["fake-1"]
'''

# Duplicate profile id
DUPLICATE_ID_AGENTS_TOML = '''
[fleet]
max_total_agents = 10

[[profile]]
id = "fake-1"
name = "Fake Profile 1"
priority = 10
enabled = true
roles = ["implement"]

[[profile]]
id = "fake-1"  # duplicate!
name = "Fake Profile 2"
priority = 5
enabled = true
roles = ["review"]

[overseer]
profiles = ["fake-1"]
'''

# Unknown overseer profile
UNKNOWN_OVERSEER_AGENTS_TOML = '''
[fleet]
max_total_agents = 10

[[profile]]
id = "fake-1"
name = "Fake Profile 1"
priority = 10
enabled = true
roles = ["implement"]

[overseer]
profiles = ["fake-1", "nonexistent-profile"]  # unknown!
'''


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


@pytest.fixture()
def console_api(tmp_path, monkeypatch):
    """A Console wired into the FastAPI app with one READY task."""
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
    monkeypatch.setattr(console_app, "console", console)
    with TestClient(console_app.app) as client:
        yield console, client
    console.dispatcher.kill_all()


def test_fleet_status_matches_the_persisted_console_pause(console_api, capsys):
    """The CLI sees the same paused state as the Console before Run."""
    from pmk.cli import main as cli_main

    console, _client = console_api
    assert cli_main(["--root", str(console.repo.root), "fleet", "status"]) == 0

    status = json.loads(capsys.readouterr().out)
    assert status["dispatch_paused"] is True
    assert status["pause_reason"] == console.fleet_state.pause_reason
    assert status["dispatch_owner"]["state"] == "free"
    assert status["dispatch_owner"]["held"] is False


def test_project_run_api_reports_paused_without_dispatch(console_api):
    """Before Run, the API reports the Console's paused state and claims nothing."""
    console, client = console_api

    response = client.get("/api/fleet")

    assert response.status_code == 200
    body = response.json()["status"]
    assert body["dispatch_paused"] is True
    assert body["dispatch_owner"]["state"] == "free"
    assert body["dispatch_owner"]["held"] is False
    kinds = [event.type for event in console.kernel.events()]
    assert not [kind for kind in kinds
                if kind in ("FLEET_ASSIGNED", "AGENT_STARTED")]


def test_project_run_api_clears_pause_and_dispatches(console_api, capsys):
    """POST Run clears the pause, persists it, and starts the READY task."""
    console, client = console_api

    response = client.post("/api/project/run")

    assert response.status_code == 200
    assert console.fleet_state.dispatch_paused is False
    assert console.fleet_state.pause_reason == ""
    assert console.fleet_state.paused_at == 0.0
    assert FleetState.load(console.repo.fleet_state_path).dispatch_paused is False

    fleet = client.get("/api/fleet").json()
    assert fleet["status"]["dispatch_paused"] is False
    owner = fleet["status"]["dispatch_owner"]
    assert owner["state"] == "active"
    assert owner["role"] == "console"
    from pmk.cli import main as cli_main
    assert cli_main(["--root", str(console.repo.root), "fleet", "status"]) == 0
    cli_status = json.loads(capsys.readouterr().out)
    assert cli_status["dispatch_paused"] is False
    assert cli_status["dispatch_owner"]["role"] == "console"
    kinds = [event.type for event in console.kernel.events()]
    assert "FLEET_ASSIGNED" in kinds
    assert "AGENT_STARTED" in kinds


def test_console_page_shows_the_dispatch_owner(console_api):
    _console, client = console_api

    page = client.get("/").text

    assert 'id="pill-owner"' in page
    assert 'id="dispatch-lock"' in page
    assert "clearStaleOwner" in page
    assert "/api/fleet/owner/clear" in page


def test_console_clears_a_stale_dispatch_owner(console_api):
    console, client = console_api
    info = owner_info_path(console.kernel, console.fleet_state.path)
    info.write_text(json.dumps({"role": "crashed", "pid": 1}),
                    encoding="utf-8")
    before = client.get("/api/fleet").json()["status"]["dispatch_owner"]
    assert before["state"] == "stale"

    response = client.post("/api/fleet/owner/clear")

    assert response.status_code == 200
    body = response.json()
    assert body["cleared"] is True
    assert body["state"] == "free"
    assert not info.exists()
    after = client.get("/api/fleet").json()["status"]["dispatch_owner"]
    assert after["state"] == "free"


def test_console_refuses_to_clear_a_live_owner(console_api):
    console, client = console_api
    other = DispatchOwner.for_kernel(
        console.kernel, "test-owner", state_path=console.fleet_state.path
    ).acquire()
    try:
        response = client.post("/api/fleet/owner/clear")
        assert response.status_code == 409
        assert response.json()["detail"]["error"] == "dispatch_owner_busy"
        assert owner_info_path(
            console.kernel, console.fleet_state.path
        ).exists()
    finally:
        other.release()


def test_run_api_refuses_a_second_dispatch_owner(console_api):
    """Run fails closed when another process already owns dispatch."""
    console, client = console_api
    other = DispatchOwner.for_kernel(console.kernel, "test-owner").acquire()
    try:
        response = client.post("/api/project/run")
    finally:
        other.release()

    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "dispatch_owner_busy"
    # The refusal must not clear the safety pause.
    assert console.fleet_state.dispatch_paused is True
    assert FleetState.load(console.repo.fleet_state_path).dispatch_paused is True

    response = client.post("/api/project/run")
    assert response.status_code == 200
    assert console.dispatch_owner is not None
    assert console.dispatch_owner.held is True


def test_stop_all_releases_the_dispatch_owner(console_api):
    console, client = console_api
    assert client.post("/api/project/run").status_code == 200
    assert console.dispatch_owner is not None

    assert client.post("/api/stop-all").status_code == 200
    assert console.dispatch_owner is None


def test_console_refuses_start_duplicate_profile_id(tmp_path):
    """Console refuses to start when agents.toml has duplicate profile ids.
    
    Records exactly one FLEET_CONFIG_ERRORS event.
    """
    repo = _make_repo_with_agents(tmp_path, DUPLICATE_ID_AGENTS_TOML)
    
    with pytest.raises(RuntimeError) as exc:
        Console(root=repo)
    
    assert "Fleet configuration has errors" in str(exc.value)
    assert "duplicate profile ids" in str(exc.value)
    
    # Check exactly one FLEET_CONFIG_ERRORS event was recorded
    kernel = Kernel(root=repo, clock=FakeClock())
    kernel.init()
    events = [e for e in kernel.events() if e.type == "FLEET_CONFIG_ERRORS"]
    assert len(events) == 1, f"Expected 1 FLEET_CONFIG_ERRORS event, got {len(events)}"
    assert "duplicate profile ids" in str(events[0].payload.get("errors", []))


def test_console_refuses_start_unknown_overseer_profile(tmp_path):
    """Console refuses to start when agents.toml has unknown overseer profile name.
    
    Records exactly one FLEET_CONFIG_ERRORS event.
    """
    repo = _make_repo_with_agents(tmp_path, UNKNOWN_OVERSEER_AGENTS_TOML)
    
    with pytest.raises(RuntimeError) as exc:
        Console(root=repo)
    
    assert "Fleet configuration has errors" in str(exc.value)
    assert "overseer profiles not found in profiles" in str(exc.value)
    
    # Check exactly one FLEET_CONFIG_ERRORS event was recorded
    kernel = Kernel(root=repo, clock=FakeClock())
    kernel.init()
    events = [e for e in kernel.events() if e.type == "FLEET_CONFIG_ERRORS"]
    assert len(events) == 1, f"Expected 1 FLEET_CONFIG_ERRORS event, got {len(events)}"
    assert "overseer profiles not found in profiles" in str(events[0].payload.get("errors", []))


def test_console_refuses_start_invalid_toml(tmp_path):
    """Console refuses to start when agents.toml is invalid TOML.
    
    Records exactly one FLEET_CONFIG_ERRORS event.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    (repo / "src").mkdir()
    (repo / "src" / "thing.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "README.md").write_text("# test\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "initial")
    
    # Write invalid TOML
    agents_path = repo / "agents.toml"
    agents_path.write_text('invalid toml [ missing bracket', encoding="utf-8")
    _git(repo, "add", "agents.toml")
    _git(repo, "commit", "-m", "add invalid agents.toml")
    
    with pytest.raises(RuntimeError) as exc:
        Console(root=repo)
    
    assert "Fleet configuration has errors" in str(exc.value)
    assert "TOML parse error" in str(exc.value)
    
    # Check exactly one FLEET_CONFIG_ERRORS event was recorded
    kernel = Kernel(root=repo, clock=FakeClock())
    kernel.init()
    events = [e for e in kernel.events() if e.type == "FLEET_CONFIG_ERRORS"]
    assert len(events) == 1, f"Expected 1 FLEET_CONFIG_ERRORS event, got {len(events)}"
    assert "TOML parse error" in str(events[0].payload.get("errors", []))


def test_dispatcher_run_forever_refuses_start_duplicate_profile_id(tmp_path):
    """Dispatcher.run_forever refuses to start when agents.toml has duplicate profile ids.
    
    Records exactly one FLEET_CONFIG_ERRORS event.
    """
    repo = _make_repo_with_agents(tmp_path, DUPLICATE_ID_AGENTS_TOML)
    
    kernel = _make_kernel_and_state(repo)
    fleet_state = FleetState.load(repo / ".pm" / "fleet" / "fleet-state.json")
    
    dispatcher = Dispatcher(kernel, fleet_state)
    
    with pytest.raises(RuntimeError) as exc:
        dispatcher.run_forever(max_seconds=0)  # Just try to start
    
    assert "Fleet configuration has errors" in str(exc.value)
    assert "duplicate profile ids" in str(exc.value)
    
    # Check exactly one FLEET_CONFIG_ERRORS event was recorded
    events = [e for e in kernel.events() if e.type == "FLEET_CONFIG_ERRORS"]
    assert len(events) == 1, f"Expected 1 FLEET_CONFIG_ERRORS event, got {len(events)}"
    assert "duplicate profile ids" in str(events[0].payload.get("errors", []))


def test_dispatcher_run_forever_refuses_start_unknown_overseer_profile(tmp_path):
    """Dispatcher.run_forever refuses to start when agents.toml has unknown overseer profile name.
    
    Records exactly one FLEET_CONFIG_ERRORS event.
    """
    repo = _make_repo_with_agents(tmp_path, UNKNOWN_OVERSEER_AGENTS_TOML)
    
    kernel = _make_kernel_and_state(repo)
    fleet_state = FleetState.load(repo / ".pm" / "fleet" / "fleet-state.json")
    
    dispatcher = Dispatcher(kernel, fleet_state)
    
    with pytest.raises(RuntimeError) as exc:
        dispatcher.run_forever(max_seconds=0)
    
    assert "Fleet configuration has errors" in str(exc.value)
    assert "overseer profiles not found in profiles" in str(exc.value)
    
    # Check exactly one FLEET_CONFIG_ERRORS event was recorded
    events = [e for e in kernel.events() if e.type == "FLEET_CONFIG_ERRORS"]
    assert len(events) == 1, f"Expected 1 FLEET_CONFIG_ERRORS event, got {len(events)}"
    assert "overseer profiles not found in profiles" in str(events[0].payload.get("errors", []))


def test_dispatcher_run_forever_refuses_start_invalid_toml(tmp_path):
    """Dispatcher.run_forever refuses to start when agents.toml is invalid TOML.
    
    Records exactly one FLEET_CONFIG_ERRORS event.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    (repo / "src").mkdir()
    (repo / "src" / "thing.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "README.md").write_text("# test\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "initial")
    
    # Write invalid TOML
    agents_path = repo / "agents.toml"
    agents_path.write_text('invalid toml [ missing bracket', encoding="utf-8")
    _git(repo, "add", "agents.toml")
    _git(repo, "commit", "-m", "add invalid agents.toml")
    
    kernel = _make_kernel_and_state(repo)
    fleet_state = FleetState.load(repo / ".pm" / "fleet" / "fleet-state.json")
    
    dispatcher = Dispatcher(kernel, fleet_state)
    
    with pytest.raises(RuntimeError) as exc:
        dispatcher.run_forever(max_seconds=0)
    
    assert "Fleet configuration has errors" in str(exc.value)
    assert "TOML parse error" in str(exc.value)
    
    # Check exactly one FLEET_CONFIG_ERRORS event was recorded
    events = [e for e in kernel.events() if e.type == "FLEET_CONFIG_ERRORS"]
    assert len(events) == 1, f"Expected 1 FLEET_CONFIG_ERRORS event, got {len(events)}"
    assert "TOML parse error" in str(events[0].payload.get("errors", []))


def test_second_start_same_errors_no_second_event(tmp_path):
    """Starting Console twice with same errors records only one FLEET_CONFIG_ERRORS event."""
    repo = _make_repo_with_agents(tmp_path, DUPLICATE_ID_AGENTS_TOML)
    
    # First attempt
    with pytest.raises(RuntimeError):
        Console(root=repo)
    
    # Second attempt (same kernel, same repo)
    kernel = Kernel(root=repo, clock=FakeClock())
    kernel.init()
    
    with pytest.raises(RuntimeError):
        Console(root=repo)
    
    # Check exactly ONE FLEET_CONFIG_ERRORS event was recorded
    events = [e for e in kernel.events() if e.type == "FLEET_CONFIG_ERRORS"]
    assert len(events) == 1, f"Expected 1 FLEET_CONFIG_ERRORS event, got {len(events)}"
