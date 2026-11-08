"""The order prompt must name an absolute path.

`Read .pmwork/ORDER.md` failed in 17 of T-0001's spawn logs because the CLI's
working directory was the main tree; the agents then globbed for ORDER.md and
found a *sibling* attempt's order, redoing that task instead of their own.
"""

import os
from pathlib import Path

from fleet import order


def test_relative_worktree_becomes_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    prompt = order.order_prompt("work/T-0001-1")
    expected = str(tmp_path / "work" / "T-0001-1" / ".pmwork" / "ORDER.md")
    assert prompt.startswith(f"Read {expected} ")
    first_path = prompt[len("Read "):].split(" and carry")[0]
    assert os.path.isabs(first_path)
    assert not prompt.startswith("Read .pmwork")


def test_absolute_worktree_is_preserved(tmp_path):
    wt = tmp_path / "work" / "T-0002-9"
    prompt = order.order_prompt(wt)
    assert str(Path(wt) / ".pmwork" / "ORDER.md") in prompt
    assert str(Path(wt) / ".pmwork" / "HANDOFF.md") in prompt
