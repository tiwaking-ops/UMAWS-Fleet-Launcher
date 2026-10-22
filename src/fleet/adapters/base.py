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

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from ..classify import PatternBook, classify as classify_failure


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
        """Find a session id in the output.

        The base implementation looks for a generic ``session ... <id>``
        pattern.  It is a guess, and it is only used when the adapter's
        ``reports_session_id`` capability is True — which, for every
        unobserved adapter, it is not.
        """
        if not self.caps.reports_session_id:
            return None
        return None

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
