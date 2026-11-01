"""Errors raised by the CNA decision-point engine.

Two families:

* :class:`EngineError` — the model itself is misused (a bad ``Action`` or
  ``Decision`` definition).  These are programming errors, raised at
  construction time wherever possible.
* :class:`IllegalAction` — a well-formed action taken at the wrong time.
  This is a *rules* outcome, not a crash: it is what ``apply`` raises when
  an action is closed, unknown, guarded off or already spent.
"""

from __future__ import annotations

__all__ = ["EngineError", "IllegalAction", "ClosedDecision",
           "AlreadyResolved", "UnknownAction"]


class EngineError(RuntimeError):
    """Base class for every engine error."""


class IllegalAction(EngineError):
    """An action was taken that is not legal in this state.

    Carries the identifiers so a caller can report the refusal without
    parsing the message text.
    """

    def __init__(self, decision_id: str, action_id: str, reason: str) -> None:
        super().__init__(
            f"action {action_id!r} is not legal at decision "
            f"{decision_id!r}: {reason}")
        self.decision_id = decision_id
        self.action_id = action_id
        self.reason = reason


class ClosedDecision(IllegalAction):
    """The decision point is not open in this state."""

    def __init__(self, decision_id: str, action_id: str) -> None:
        super().__init__(decision_id, action_id, "decision is not open")


class AlreadyResolved(IllegalAction):
    """A choice has already been recorded for this decision point."""

    def __init__(self, decision_id: str, action_id: str,
                 chosen: str | None = None) -> None:
        detail = "already resolved"
        if chosen is not None:
            detail = f"already resolved as {chosen!r}"
        super().__init__(decision_id, action_id, detail)
        self.chosen = chosen


class UnknownAction(IllegalAction):
    """The action is not one of the decision point's declared actions."""

    def __init__(self, decision_id: str, action_id: str) -> None:
        super().__init__(decision_id, action_id, "not declared at this decision")
