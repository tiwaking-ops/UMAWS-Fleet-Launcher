"""The fake CLI adapter.

The fake CLI (``tests/fleet/fakecli.py``) stands in for a real agent so the
Fleet can be tested without LLMs, without quota and without network.  Its
fixtures are **synthetic**: they describe what the fake prints, and they
make no claim about any real provider.

The fake is the only adapter whose capabilities are known to be true, because
the fake's behaviour is defined by the script in this repository.
"""

from __future__ import annotations

import re
from typing import Literal

from .base import BaseAdapter, Caps

#: The fake prints a session id like ``fake-session: fake-0001``.
SESSION_PATTERN = re.compile(r"fake-session:\s*(\S+)")


class FakeAdapter(BaseAdapter):
    """Adapter for the scriptable fake CLI."""

    name = "fake"

    @property
    def caps(self) -> Caps:
        return Caps(
            headless=True,
            can_resume=True,
            can_swap_model_on_resume=True,
            reports_session_id=True,
        )

    def verified(self) -> bool:
        return True

    def build_argv(self, profile: dict, mode: Literal["new", "resume"],
                   prompt: str, cwd: str, session: str | None) -> list[str]:
        import sys
        from pathlib import Path

        fake = Path(__file__).resolve().parents[3] / "tests" / "fleet" / "fakecli.py"
        argv = [sys.executable, str(fake)]
        scenario = str(profile.get("scenario", "ok"))
        argv += ["--scenario", scenario]
        if mode == "resume":
            argv.append("--resume")
            if session:
                argv += ["--session-id", session]
        if cwd:
            argv += ["--cwd", cwd]
        return argv

    def parse_session_id(self, log_text: str) -> str | None:
        match = SESSION_PATTERN.search(log_text or "")
        return match.group(1) if match else None
