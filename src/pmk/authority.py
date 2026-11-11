"""The shared human-authority gate (reviewer item 2, incident seq 3630).

One helper, :func:`require_human_authority`, guards the operator-only acts the
reviewer enumerated: ``task void``, ``pins record``, class-K ``queue_decide``,
``resume_dispatch`` / ``--resume``, profile enable/disable/cooling,
``cmd_agent_swap`` and ``MANUAL_LAUNCH``.  The canary start/finish events use
it too, so they record a verified human or refuse (item 3).

The gate requires **both**:

* a human actor -- an explicit ``Actor(kind="human")`` or
  ``PMK_ACTOR=human:<name>``; and
* an interactive TTY on stdin.

The refusal text deliberately does **not** say what to set.  A message that
names the environment variable would tell a spawned worker exactly how to
satisfy the gate.

This is a boundary against the path of least resistance, not authentication.
Any caller with access to the Kernel can still construct ``Actor.human()``
directly -- ``Kernel.task_void``'s own docstring says as much.  What this
removes is every *CLI and Console* route that turned an unset or worker
environment into a recorded human act.
"""

from __future__ import annotations

import sys

from .events import Actor


class AuthorityError(RuntimeError):
    """A human-authority gate refused an action.

    The text is intentionally generic: naming what to set would hand a
    worker the bypass.
    """

    def __init__(self, action: str) -> None:
        super().__init__(f"{action}: human authority required")
        self.action = action

    def to_dict(self) -> dict:
        return {"reason": "not_authorized", "action": self.action,
                "msg": str(self)}


def stdin_is_interactive() -> bool:
    """True when stdin is an interactive terminal.

    This is a seam: the tests patch it to drive the gate without a real TTY.
    """
    try:
        return bool(sys.stdin.isatty())
    except (AttributeError, ValueError):     # pragma: no cover - exotic stdio
        return False


def human_actor(*, actor: Actor | None = None) -> Actor | None:
    """Return a human actor from *actor* or ``PMK_ACTOR``, else ``None``."""
    if actor is not None:
        return actor if actor.kind == "human" else None
    # Imported lazily: ``pmk.api`` imports this module, so a top-level import
    # here would be a load cycle.
    from .api import _actor_from_env
    resolved = _actor_from_env()
    if resolved is not None and resolved.kind == "human":
        return resolved
    return None


def require_human_authority(action: str, *,
                            actor: Actor | None = None) -> Actor:
    """Return the human actor for *action*, or raise :class:`AuthorityError`.

    Both conditions must hold: a human identity **and** an interactive TTY.
    """
    who = human_actor(actor=actor)
    if who is None or not stdin_is_interactive():
        raise AuthorityError(action)
    return who
