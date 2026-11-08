"""Every subprocess spawn under ``src/`` must pass ``env=`` or be allowlisted.

This is the regression guard for the T-0145/T-0146 class of defect: one
unpinned spawn judged a worktree with the installed code.  The check is
static (AST) so it runs in milliseconds and fails at review time rather than
at the next lost attempt.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_unguarded_subprocess_spawns():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "check_subprocess_env.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT))
    assert proc.returncode == 0, proc.stdout + proc.stderr
