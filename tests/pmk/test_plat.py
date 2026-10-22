"""Platform layer tests (spike S-P1 findings, locked in)."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

from pmk import plat


# ---------------------------------------------------------------------------
# Locking
# ---------------------------------------------------------------------------

def test_lock_is_exclusive(tmp_path):
    lock = plat.FileLock(tmp_path / "a.lock", timeout=0.2)
    lock.acquire()
    other = plat.FileLock(tmp_path / "a.lock", timeout=0.2)
    with pytest.raises(plat.LockTimeout):
        other.acquire()
    lock.release()
    other.acquire()
    other.release()


def test_lock_sidecar_is_used_not_the_data_file(tmp_path):
    """Decision D-04: the lock lives on a sidecar, never on the data file.

    Windows enforces byte-range locks against writes, so locking the file
    being appended to fails with PermissionError.  This test would fail
    loudly if the sidecar were removed.
    """
    data = tmp_path / "events.jsonl"
    plat.append_line_locked(data, "first")
    assert (tmp_path / "events.jsonl.lock").exists()


def test_append_line_locked_writes_terminated_lines(tmp_path):
    data = tmp_path / "events.jsonl"
    plat.append_line_locked(data, "one")
    plat.append_line_locked(data, "two")
    assert data.read_text(encoding="utf-8") == "one\ntwo\n"


def test_atomic_write_replaces_the_file(tmp_path):
    target = tmp_path / "x.txt"
    plat.atomic_write_text(target, "hello")
    plat.atomic_write_text(target, "world")
    assert target.read_text(encoding="utf-8") == "world"
    assert not (tmp_path / "x.txt.tmp").exists()


# ---------------------------------------------------------------------------
# Process identity
# ---------------------------------------------------------------------------

def test_process_info_reports_a_live_process():
    info = plat.process_info(os.getpid())
    assert info.alive
    assert info.creation_time is not None


def test_process_info_reports_a_dead_process():
    info = plat.process_info(0x7FFFFFF0)
    assert not info.alive


def test_same_process_refuses_a_mismatched_creation_time():
    info = plat.process_info(os.getpid())
    assert plat.same_process(info.pid, info.creation_time)
    assert not plat.same_process(info.pid, (info.creation_time or 0) + 1)


def test_kill_refuses_a_process_it_did_not_spawn():
    """Fleet rule 17: only kill what you spawned."""
    info = plat.process_info(os.getpid())
    killed, detail = plat.kill_tree(info.pid,
                                    creation_time=(info.creation_time or 0) + 5)
    assert not killed
    assert "refused" in detail.lower()


def test_kill_refuses_a_none_pid():
    killed, detail = plat.kill_tree(12345)
    assert not killed


# ---------------------------------------------------------------------------
# Executable resolution
# ---------------------------------------------------------------------------

def test_resolve_executable_finds_a_native_executable():
    resolved = plat.resolve_executable("cmd")
    assert resolved is not None
    assert resolved.kind in ("native", "cmd")


def test_resolve_executable_peels_an_npm_cmd_shim(tmp_path):
    """A ``.cmd`` shim must be resolved to its real target, not run via cmd.exe.

    Spike S-A1 measured that cmd.exe mangles arguments (``%PATH%`` expands,
    ``^`` doubles), so the Fleet bypasses cmd.exe entirely.
    """
    npm_dir = tmp_path / "npm"
    (npm_dir / "node_modules" / "pkg" / "bin").mkdir(parents=True)
    script = npm_dir / "node_modules" / "pkg" / "bin" / "tool.js"
    script.write_text("console.log('hi');\n", encoding="utf-8")
    shim = npm_dir / "tool.cmd"
    shim.write_text(
        '@ECHO off\r\n'
        'GOTO start\r\n'
        ':find_dp0\r\n'
        'SET dp0=%~dp0\r\n'
        'EXIT /b\r\n'
        ':start\r\n'
        'SETLOCAL\r\n'
        'CALL :find_dp0\r\n'
        'endLocal & goto #_undefined_# 2>NUL || title %COMSPEC% & '
        'set PATHEXT=%PATHEXT:;.JS;=;% & "node"  "%dp0%\\node_modules\\pkg\\bin\\tool.js" %*\r\n',
        encoding="utf-8")

    resolved = plat._resolve_cmd_shim(str(shim))
    assert resolved is not None
    assert resolved.kind == "node"
    assert resolved.runner == "node"
    assert resolved.target.endswith("tool.js")

    argv = plat.argv_for_executable(resolved, ["a", "b"])
    assert argv[0] == "node"
    assert argv[2:] == ["a", "b"]


def test_resolve_executable_falls_back_for_an_unknown_shim(tmp_path):
    shim = tmp_path / "weird.cmd"
    shim.write_text("@ECHO off\r\necho hello\r\n", encoding="utf-8")
    resolved = plat._classify_executable(str(shim))
    assert resolved.kind == "cmd"
    assert resolved.degraded


def test_null_path_is_platform_correct():
    assert plat.null_path() in ("NUL", "/dev/null")


# ---------------------------------------------------------------------------
# Redaction and memory
# ---------------------------------------------------------------------------

def test_redact_replaces_secret_values():
    text = "the key is sk-abc123456789 and also sk-abc123456789"
    out = plat.redact(text, ["sk-abc123456789"])
    assert "sk-abc123456789" not in out
    assert out.count("[REDACTED]") == 2


def test_redact_ignores_short_values():
    assert plat.redact("abc", ["ab"]) == "abc"


def test_free_ram_is_a_positive_number():
    value = plat.free_ram_mb()
    assert value is None or value > 0


def test_tail_file_returns_the_last_lines(tmp_path):
    target = tmp_path / "log.txt"
    target.write_text("\n".join(f"line {i}" for i in range(100)), encoding="utf-8")
    tail = plat.tail_file(target, 5)
    assert len(tail) == 5
    assert tail[-1] == "line 99"


def test_tail_file_of_a_missing_file_is_empty(tmp_path):
    assert plat.tail_file(tmp_path / "nope.txt") == []


def test_scrub_environment_drops_provider_keys():
    env = {"OPENAI_API_KEY": "x", "ANTHROPIC_API_KEY": "y", "PATH": "p",
           "MY_TOKEN": "z"}
    out = plat.scrub_environment(env, keep=["PATH"])
    assert "OPENAI_API_KEY" not in out
    assert "ANTHROPIC_API_KEY" not in out
    assert out["PATH"] == "p"
    assert out["MY_TOKEN"] == "z"
