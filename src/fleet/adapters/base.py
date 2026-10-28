"""The adapter interface (fleet amendment section 12.B).

An adapter knows three things about one CLI:

1. how to build an argv list for a new run or a resumed run;
2. how to find a session id in the output, if the CLI reports one;
3. how to classify a failure.

Everything else — the worktree, the lease, the order file, the oracles, the
recovery ladder — belongs to the harness, not to the adapter.

**Capabilities default to ``False``.**  They are only set to ``True`` from a
captured observation (spike S-A1 or a live run).  An adapter that has never
been observed therefore does the safe thing: no resume, no model switch, no
session id, and a console window instead of a headless process.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from ..classify import PatternBook, classify as classify_failure


#: Hermes prints the session id on a line ``session_id: <id>`` to STDERR,
#: which plat.spawn merges into the stdout log.  The id format is
#: YYYYMMDD_HHMMSS_<hex6> (operator-verified, 2026-10-28).  We tighten the
#: regex to the known format so a stray "session_id:" line from a different
#: process cannot inject a bogus id.
HERMES_SESSION_PATTERN = re.compile(r"session_id:\s*(\d{8}_\d{6}_[0-9a-f]+)")


@dataclass(frozen=True)
class Caps:
    """What the adapter is known to be able to do.

    All fields default to ``False`` because "unknown" must behave like
    "no" (fleet amendment section 12.B, risk R-F1).
    """

    headless: bool = False            # False = needs a console window
    can_resume: bool = False
    can_swap_model_on_resume: bool = False
    reports_session_id: bool = False

    def to_dict(self) -> dict:
        return {
            "headless": self.headless,
            "can_resume": self.can_resume,
            "can_swap_model_on_resume": self.can_swap_model_on_resume,
            "reports_session_id": self.reports_session_id,
        }


class ResumeUnsupported(RuntimeError):
    """Raised when a resume is requested from an adapter that cannot resume."""


class Adapter(Protocol):
    """The adapter protocol."""

    name: str
    caps: Caps

    def build_argv(self, profile: dict, mode: Literal["new", "resume"],
                   prompt: str, cwd: str, session: str | None) -> list[str]:
        ...

    def parse_session_id(self, log_text: str) -> str | None:
        ...

    def classify(self, exit_code: int | None, log_tail: str) -> str:
        ...


class BaseAdapter:
    """Shared behaviour for the template-driven adapters."""

    name = "base"

    def __init__(self, fixture_root: str | Path | None = None):
        self.fixture_root = fixture_root
        self.book = PatternBook(adapter=self.name)

    # -- capabilities ------------------------------------------------------
    @property
    def caps(self) -> Caps:
        return Caps()

    def verified(self) -> bool:
        """Has this adapter's behaviour been observed?"""
        return False

    # -- argv --------------------------------------------------------------
    def build_argv(self, profile: dict, mode: Literal["new", "resume"],
                   prompt: str, cwd: str, session: str | None) -> list[str]:
        template = profile.get("argv_new") if mode == "new" else \
            profile.get("argv_resume")
        if mode == "resume":
            if not template:
                raise ResumeUnsupported(
                    f"adapter {self.name!r} has no resume template "
                    f"(profile {profile.get('id')!r}); resume is UNVERIFIED")
            if not self.caps.can_resume:
                raise ResumeUnsupported(
                    f"adapter {self.name!r} cannot resume (caps default to "
                    f"False until an observation says otherwise)")
        return self._fill(list(template or []), profile, prompt, cwd, session)

    def _fill(self, template: list[str], profile: dict, prompt: str,
              cwd: str, session: str | None) -> list[str]:
        out = []
        for token in template:
            out.append(token
                       .replace("{prompt}", prompt)
                       .replace("{cwd}", cwd)
                       .replace("{session}", session or "")
                       .replace("{model}", str(profile.get("model", ""))))
        return out

    # -- session -----------------------------------------------------------
    def parse_session_id(self, log_text: str) -> str | None:
        """Find a session id in the merged stdout/stderr log.

        Returns the *last* match so a stray early match (e.g. from a
        resumed sub-process) does not shadow the real one.  Returns
        ``None`` when the adapter does not claim to report a session id,
        or when the log contains no ``session_id:`` line at all.
        """
        if not self.caps.reports_session_id:
            return None
        last = None
        for m in HERMES_SESSION_PATTERN.finditer(log_text or ""):
            last = m.group(1)
        return last

    # -- classification ----------------------------------------------------
    def load_patterns(self, fixture_root: str | Path | None = None) -> None:
        root = fixture_root if fixture_root is not None else self.fixture_root
        if root is None:
            return
        self.book = load_book_for(self.name, root)

    def classify(self, exit_code: int | None, log_tail: str) -> str:
        return classify_failure(exit_code, log_tail, self.book)

    def to_dict(self) -> dict:
        return {"name": self.name, "caps": self.caps.to_dict(),
                "verified": self.verified(),
                "patterns": self.book.to_dict()}


def load_book_for(adapter: str, fixture_root: str | Path):
    """Load a pattern book for *adapter* (thin wrapper for readability)."""
    from ..classify import load_book
    return load_book(adapter, fixture_root)
