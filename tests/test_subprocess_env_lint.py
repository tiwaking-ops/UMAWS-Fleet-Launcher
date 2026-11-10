"""Every subprocess spawn under ``src/`` must pass ``env=`` or be allowlisted.

This is the regression guard for the T-0145/T-0146 class of defect: one
unpinned spawn judged a worktree with the installed code.  The same tool also
requires every fleet spawn to pass an explicit, resolved cwd.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "tools" / "check_subprocess_env.py"


def _load_check():
    spec = importlib.util.spec_from_file_location("check_subprocess_env", CHECK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_no_unguarded_subprocess_spawns():
    proc = subprocess.run(
        [sys.executable, str(CHECK)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT))
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.fixture
def bad_fleet_file(tmp_path):
    path = tmp_path / "bad_fleet.py"
    path.write_text(
        "from pmk import plat\n"
        "def bad():\n"
        "    plat.spawn(['x'], cwd='work')\n"
        "    plat.spawn(['y'])\n",
        encoding="utf-8")
    return path


def test_cli_rejects_a_bad_fleet_file(bad_fleet_file):
    """The executable, not just the scanner function, must fail closed."""
    proc = subprocess.run(
        [sys.executable, str(CHECK), str(bad_fleet_file)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT))

    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "bad_fleet.py" in proc.stdout
    assert "passes cwd='work'" in proc.stdout
    assert "has no cwd=" in proc.stdout


@pytest.fixture
def mixed_fleet_file(tmp_path):
    path = tmp_path / "mixed_fleet.py"
    path.write_text(
        "from pathlib import Path\n"
        "from pmk import plat\n"
        "def mixed(worktree):\n"
        "    target = Path(worktree).resolve()\n"
        "    plat.spawn(['ok'], cwd=target)\n"
        "    plat.spawn(['bad'], cwd='work')\n",
        encoding="utf-8")
    return path


def test_cli_fails_a_mixed_fleet_file_and_names_only_the_rejected_line(
        mixed_fleet_file):
    """A successful spawn must not hide or launder the rejected one."""
    proc = subprocess.run(
        [sys.executable, str(CHECK), str(mixed_fleet_file)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT))

    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert f"{mixed_fleet_file}:5" not in proc.stdout
    assert f"{mixed_fleet_file}:6" in proc.stdout
    reported = [line for line in proc.stdout.splitlines()
                if str(mixed_fleet_file) in line]
    assert len(reported) == 1
    assert "passes cwd='work'" in reported[0]


@pytest.fixture
def rejected_then_accepted_fleet_file(tmp_path):
    path = tmp_path / "rejected_then_accepted_fleet.py"
    path.write_text(
        "from pathlib import Path\n"
        "from pmk import plat\n"
        "def mixed(worktree):\n"
        "    target = Path(worktree).resolve()\n"
        "    plat.spawn(['bad'], cwd='work')\n"
        "    plat.spawn(['ok'], cwd=target)\n",
        encoding="utf-8")
    return path


def test_cli_fails_when_the_rejected_spawn_is_scanned_first(
        rejected_then_accepted_fleet_file):
    """The rejected finding must survive a later accepted spawn."""
    proc = subprocess.run(
        [sys.executable, str(CHECK), str(rejected_then_accepted_fleet_file)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT))

    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert f"{rejected_then_accepted_fleet_file}:5" in proc.stdout
    assert f"{rejected_then_accepted_fleet_file}:6" not in proc.stdout
    reported = [line for line in proc.stdout.splitlines()
                if str(rejected_then_accepted_fleet_file) in line]
    assert len(reported) == 1
    assert "passes cwd='work'" in reported[0]


@pytest.fixture
def good_fleet_file(tmp_path):
    path = tmp_path / "good_fleet.py"
    path.write_text(
        "from pathlib import Path\n"
        "from pmk import plat\n"
        "def good(worktree):\n"
        "    target = Path(worktree).resolve()\n"
        "    plat.spawn(['x'], cwd=target)\n"
        "    plat.spawn(['y'], cwd=str(target))\n",
        encoding="utf-8")
    return path


def test_cli_accepts_a_good_fleet_file(good_fleet_file):
    """The companion of the reject test: a resolved cwd must exit 0."""
    proc = subprocess.run(
        [sys.executable, str(CHECK), str(good_fleet_file)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT))

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "fleet cwd checks pass" in proc.stdout
    assert "good_fleet.py" not in proc.stdout


def test_cwd_scanner_rejects_relative_and_unresolved_values(tmp_path):
    source = tmp_path / "fleet_sample.py"
    source.write_text(
        "import subprocess\n"
        "from pmk import plat\n"
        "def bad(worktree):\n"
        "    subprocess.run(['x'], cwd='work')\n"
        "    subprocess.run(['y'], cwd=worktree)\n"
        "    plat.spawn(['z'], cwd=slot.worktree)\n"
        "    subprocess.run(['w'])\n"
        "    plat.spawn(['v'], cwd=None)\n"
        "def good(worktree):\n"
        "    target = Path(worktree).resolve()\n"
        "    subprocess.run(['x'], cwd=str(target))\n"
        "    plat.spawn(['z'], cwd=target)\n",
        encoding="utf-8")

    findings = _load_check().scan_cwd_file(source)

    assert [function for function, _, _ in findings] == ["bad"] * 5
    expressions = {expression for _, _, expression in findings}
    assert "'work'" in expressions
    assert "worktree" in expressions
    assert "slot.worktree" in expressions
    assert "<missing>" in expressions
    assert "None" in expressions


def test_cli_reports_an_unreadable_extra_fleet_file_without_a_traceback(
        tmp_path):
    """An undecodable extra file is an input error, not a traceback."""
    unreadable = tmp_path / "unreadable_fleet.py"
    unreadable.write_bytes(b"\xff\xfe\x00\x00")

    proc = subprocess.run(
        [sys.executable, str(CHECK), str(unreadable)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT))

    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "Traceback" not in proc.stderr
    assert f"error: extra fleet file unreadable: {unreadable}" in proc.stderr


def test_cli_reports_a_missing_extra_fleet_file_without_a_traceback(tmp_path):
    """A bad extra-file argument is an input error, not an exception."""
    missing = tmp_path / "missing_fleet.py"

    proc = subprocess.run(
        [sys.executable, str(CHECK), str(missing)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT))

    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "Traceback" not in proc.stderr
    assert f"error: extra fleet file not found: {missing}" in proc.stderr
