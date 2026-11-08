"""F9: the pipeline commits as the pilot identity, never as the human.

Four commits in the incident window carried the human identity while every
neighbouring commit used the repo-local one.  The merge path now pins the
identity explicitly and records an anomaly when the configured identity is
somebody else's.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from fleet.merge import (PIPELINE_EMAIL, PIPELINE_NAME, commit_worktree,
                         identity_anomaly)


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True, text=True)


def _out(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def _configure_human(root: Path) -> None:
    _git(root, "config", "user.name", "Tiwa Pene")
    _git(root, "config", "user.email", "tiwaking@gmail.com")


def test_identity_anomaly_flags_the_human_identity(kernel):
    _configure_human(kernel.repo.root)

    anomaly = identity_anomaly(kernel.repo, kernel.repo.root)

    assert "tiwaking@gmail.com" in anomaly


def test_identity_anomaly_is_quiet_for_the_pipeline_identity(kernel):
    assert identity_anomaly(kernel.repo, kernel.repo.root) == ""


def test_commit_worktree_pins_the_pipeline_identity(kernel):
    root = kernel.repo.root
    _configure_human(root)
    (root / "src" / "thing.py").write_text("VALUE = 42\n", encoding="utf-8")

    ok, commit = commit_worktree(kernel.repo, root, "pipeline commit",
                                 ["src/thing.py"])

    assert ok, commit
    assert _out(root, "log", "-1", "--format=%an <%ae>") == (
        f"{PIPELINE_NAME} <{PIPELINE_EMAIL}>")


def test_pre_commit_hook_logs_without_blocking(kernel):
    root = kernel.repo.root
    _configure_human(root)
    hook = Path(__file__).resolve().parents[2] / ".githooks" / "pre-commit"
    env = {"UMAWS_PIPELINE": "1", "PATH": os.environ["PATH"]}

    proc = subprocess.run(["sh", str(hook)], cwd=str(root), env=env,
                          capture_output=True, text=True)

    assert proc.returncode == 0
    log = root / ".pm" / "fleet" / "identity-warnings.log"
    assert log.is_file()
    assert "tiwaking@gmail.com" in log.read_text(encoding="utf-8")
