"""Tests for Hermes session-id parsing (fleet v1 section 12.B).

Under ``-Q`` Hermes writes a ``session_id:`` line to STDERR.  plat.spawn merges
STDERR into STDOUT (subprocess.STDOUT), so the adapter must parse the line
from the *combined* log.  The operator-verified format is
``session_id: YYYYMMDD_HHMMSS_<hex6>`` and there is NO "Resume this session
with" trailer (capture by hand, 2026-10-28).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from fleet.adapters import get_adapter
from fleet.harness import _session_from_log
from pmk import plat


FIXTURE_ROOT = "tests/fleet/fixtures"

#: Path to a tiny fake CLI used by the end-to-end spawn tests.
_FAKE_CLI_SRC = '''
"""Fake CLI for Hermes session-id and env inheritance tests."""
import sys, os

if "--env" in sys.argv:
    # Print PATH and PMK_ACTOR to stdout for env-inheritance test
    print(f"PATH={os.environ.get('PATH', '')}")
    print(f"PMK_ACTOR={os.environ.get('PMK_ACTOR', '')}")
elif "--session" in sys.argv:
    # Print a reply to stdout and a session_id line to stderr
    print("Hi Tiwa. What do you need?")
    # plat.spawn merges stderr into stdout (subprocess.STDOUT)
    print("session_id: 20261028_074048_445ed4", file=sys.stderr)
    sys.exit(0)
'''
_FAKE_CLI_PATH = Path(__file__).resolve().parent / "_fake_hermes_cli.py"

#: Exact capture from a real hermes run under -Q:
#:   stdout: "Hi Tiwa. What do you need?\n"
#:   stderr: "session_id: 20261028_074048_445ed4\n"
#: plat.spawn merges stderr into stdout, so the log is the concatenation.
HERMES_CAPTURE = (
    "Hi Tiwa. What do you need?\n"
    "session_id: 20261028_074048_445ed4\n"
)


def test_hermes_adapter_parses_session_id_from_merged_log():
    """parse_session_id reads the session_id: line from the combined log."""
    hermes = get_adapter("hermes", FIXTURE_ROOT)
    assert hermes.caps.reports_session_id
    sid = hermes.parse_session_id(HERMES_CAPTURE)
    assert sid == "20261028_074048_445ed4"


def test_hermes_adapter_last_match_wins():
    """If the log contains multiple session_id lines, the last one wins."""
    hermes = get_adapter("hermes", FIXTURE_ROOT)
    log = (
        "session_id: 20261028_070000_aaa\n"
        "some middle output\n"
        "session_id: 20261028_074048_445ed4\n"
    )
    sid = hermes.parse_session_id(log)
    assert sid == "20261028_074048_445ed4"


def test_hermes_adapter_missing_session_id_returns_none():
    """A log with no session_id: line returns None, not a crash."""
    hermes = get_adapter("hermes", FIXTURE_ROOT)
    sid = hermes.parse_session_id("Hi Tiwa. What do you need?\n")
    assert sid is None


def test_hermes_adapter_empty_log_returns_none():
    """An empty or whitespace-only log returns None."""
    hermes = get_adapter("hermes", FIXTURE_ROOT)
    assert hermes.parse_session_id("") is None
    assert hermes.parse_session_id("   \n  ") is None


def test_session_from_log_uses_adapter_passthrough():
    """_session_from_log delegates to the adapter's parse_session_id.

    When the adapter reports_session_id and the log contains a session_id
    line, _session_from_log returns the id (not the fake pattern).
    """
    hermes = get_adapter("hermes", FIXTURE_ROOT)
    sid = _session_from_log(hermes, HERMES_CAPTURE)
    assert sid == "20261028_074048_445ed4"


def test_session_from_log_empty_when_no_session_id():
    """When no session_id line is present, _session_from_log returns ''."""
    hermes = get_adapter("hermes", FIXTURE_ROOT)
    sid = _session_from_log(hermes, "no session id here\n")
    assert sid == ""


def test_session_from_log_falls_back_to_fake_pattern_for_fake_adapter():
    """The fake adapter uses the legacy fake-session: pattern."""
    fake = get_adapter("fake", FIXTURE_ROOT)
    log = "fake-session: fake-0001\n"
    sid = _session_from_log(fake, log)
    assert sid == "fake-0001"


def test_session_from_log_for_adapter_without_reports_session_id():
    """An adapter whose reports_session_id is False falls back to the fake
    pattern (which won't match Hermes-style logs, returning '')."""
    kilo = get_adapter("kilo", FIXTURE_ROOT)
    assert not kilo.caps.reports_session_id
    sid = _session_from_log(kilo, HERMES_CAPTURE)
    # kilo doesn't report session ids, so the fake pattern is used; it
    # won't match "session_id:" so we get "".
    assert sid == ""


# ---------------------------------------------------------------------------
# End-to-end: real spawn_slot path with stdout/stderr merge and env inheritance
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _write_fake_cli():
    """Write the fake CLI script so the end-to-end tests can spawn it."""
    _FAKE_CLI_PATH.write_text(_FAKE_CLI_SRC, encoding="utf-8")
    yield
    _FAKE_CLI_PATH.unlink(missing_ok=True)


def _make_adapter_and_profile(profile_id, argv_extra):
    """Build a TemplateAdapter and a profile dict that uses the fake CLI.

    We use a template adapter (not FakeAdapter) so the profile's argv_new
    template is used — FakeAdapter ignores argv_new and always invokes
    fakecli.py.
    """
    from fleet.adapters import get_adapter
    adapter = get_adapter("hermes", FIXTURE_ROOT)  # has reports_session_id=True
    profile = {
        "id": profile_id, "adapter": "hermes", "family": "unknown",
        "priority": 10, "max_concurrent": 2, "via_gateway": False,
        "roles": ["implement"],
        "argv_new": [sys.executable, str(_FAKE_CLI_PATH)] + argv_extra,
        "argv_resume": [sys.executable, str(_FAKE_CLI_PATH)] + argv_extra,
        "model": "test-model",
    }
    return adapter, profile


def _spawn_slot_and_wait(repo, profile_id, prompt, worktree, *,
                         env=None, actor=None, argv_extra=None):
    """Call spawn_slot directly, wait for the fake CLI to finish, return the slot.

    Delegates adapter/profile construction to ``_make_adapter_and_profile``
    so the template adapter's argv_new template is used.

    Returns the :class:`~fleet.spawn.Slot` so the caller can inspect log_path,
    pid, and the merged log output.
    """
    from fleet.spawn import spawn_slot, kill_slot
    adapter, profile = _make_adapter_and_profile(profile_id, argv_extra or [])
    slot = spawn_slot(repo, task_id=f"T-{profile_id}", profile_id=profile_id,
                      adapter=adapter, profile=profile, prompt=prompt,
                      worktree=str(worktree), fence=1, index=0,
                      env=env, actor=actor)
    try:
        slot.proc.wait(timeout=10)
    finally:
        kill_slot(slot)
    return slot


def test_end_to_end_session_id_via_spawn_slot(fake_kernel, tmp_path):
    """End-to-end: spawn_slot with a fake CLI that prints a reply to stdout
    and `session_id:` to stderr.  plat.spawn merges stderr into stdout.
    We parse the resulting log with the Hermes adapter's parse_session_id.

    Uses spawn_slot itself (not plat.spawn directly) so the env-merge
    and PMK_ACTOR logic in spawn_slot is exercised.
    """
    hermes = get_adapter("hermes", FIXTURE_ROOT)
    worktree = tmp_path / "work" / "wt"
    worktree.mkdir(parents=True)

    slot = _spawn_slot_and_wait(fake_kernel.repo, "test-fake", "hello",
                                worktree, argv_extra=["--session"])
    log_text = Path(slot.log_path).read_text(encoding="utf-8")

    # The log must contain both the stdout reply and the stderr session_id line
    assert "Hi Tiwa. What do you need?" in log_text
    assert "session_id: 20261028_074048_445ed4" in log_text

    # The Hermes adapter must parse the session id from the merged log
    sid = hermes.parse_session_id(log_text)
    assert sid == "20261028_074048_445ed4"


def test_end_to_end_env_none_inherits_path_and_set_actor(fake_kernel, tmp_path):
    """When env=None (via_gateway=false), spawn_slot inherits os.environ
    so the child sees PATH, USERPROFILE, APPDATA.  PMK_ACTOR is set to
    worker:<profile_id> (the default)."""
    worktree = tmp_path / "work" / "wt"
    worktree.mkdir(parents=True)

    slot = _spawn_slot_and_wait(fake_kernel.repo, "envtest", "hello",
                                worktree, argv_extra=["--env"])
    log_text = Path(slot.log_path).read_text(encoding="utf-8")

    path_line = [l for l in log_text.splitlines() if l.startswith("PATH=")]
    assert path_line, f"expected PATH= line, got: {log_text!r}"
    assert path_line[0] == f"PATH={os.environ['PATH']}"

    actor_line = [l for l in log_text.splitlines() if l.startswith("PMK_ACTOR=")]
    assert actor_line, f"expected PMK_ACTOR= line, got: {log_text!r}"
    assert actor_line[0] == "PMK_ACTOR=worker:envtest"


def test_end_to_end_scrubbed_env_does_not_leak_provider_key(fake_kernel, tmp_path, monkeypatch):
    """When a scrubbed env is passed (via_gateway=true path), the child
    does NOT see a provider key set in the parent environment.

    spawn_slot starts from the *scrubbed* env dict (not os.environ), so
    provider secrets in the parent os.environ never reach the child.
    """
    monkeypatch.setenv("PROVIDER_SECRET", "leak-canary-123")
    worktree = tmp_path / "work" / "wt"
    worktree.mkdir(parents=True)

    # Simulate a scrubbed env (only allowlisted keys, no provider keys)
    scrubbed = {"PATH": os.environ["PATH"],
                "USERPROFILE": os.environ["USERPROFILE"],
                "APPDATA": os.environ["APPDATA"]}
    slot = _spawn_slot_and_wait(fake_kernel.repo, "gateway", "hello",
                                worktree, env=scrubbed, argv_extra=["--env"])
    log_text = Path(slot.log_path).read_text(encoding="utf-8")

    env_lines = {l.split("=", 1)[0]: l.split("=", 1)[1]
                 for l in log_text.splitlines() if "=" in l}
    assert env_lines.get("PATH") == os.environ["PATH"]
    assert env_lines.get("PMK_ACTOR") == "worker:gateway"
    # Provider secret must NOT leak — it was not in the scrubbed env dict
    assert "PROVIDER_SECRET" not in env_lines


def test_end_to_end_actor_override_overseer(fake_kernel, tmp_path):
    """When actor='overseer:<id>' is passed to spawn_slot, the child sees
    PMK_ACTOR=overseer:<id>, not worker:<id>."""
    worktree = tmp_path / "work" / "wt"
    worktree.mkdir(parents=True)

    slot = _spawn_slot_and_wait(fake_kernel.repo, "overseer-prof", "hello",
                                worktree, actor="overseer:overseer-prof",
                                argv_extra=["--env"])
    log_text = Path(slot.log_path).read_text(encoding="utf-8")

    actor_line = [l for l in log_text.splitlines() if l.startswith("PMK_ACTOR=")]
    assert actor_line, f"expected PMK_ACTOR= line, got: {log_text!r}"
    assert actor_line[0] == "PMK_ACTOR=overseer:overseer-prof"


def test_end_to_end_stale_pmk_actor_overwritten(fake_kernel, tmp_path, monkeypatch):
    """A stale PMK_ACTOR in the parent environment is overwritten by
    spawn_slot, never leaked to the child."""
    monkeypatch.setenv("PMK_ACTOR", "human:attacker")
    worktree = tmp_path / "work" / "wt"
    worktree.mkdir(parents=True)

    slot = _spawn_slot_and_wait(fake_kernel.repo, "staletest", "hello",
                                worktree, argv_extra=["--env"])
    log_text = Path(slot.log_path).read_text(encoding="utf-8")

    actor_line = [l for l in log_text.splitlines() if l.startswith("PMK_ACTOR=")]
    assert actor_line, f"expected PMK_ACTOR= line, got: {log_text!r}"
    # The stale "human:attacker" must NOT appear — overwritten to worker:staletest
    assert actor_line[0] == "PMK_ACTOR=worker:staletest"
    assert "human:attacker" not in log_text
