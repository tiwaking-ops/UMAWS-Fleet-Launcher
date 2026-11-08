"""Hidden-information views.

RULE: proposal 6.4 (sealed commitments; the AI receives only a view).

The engine stores the full state; a player receives :func:`view`.  The view
keeps the viewer's own hand and public information, replaces every other
hand with its size, and hides sealed commitments until they are revealed.
"""

from __future__ import annotations

import copy
from typing import Any, Mapping

SIDES = ("axis", "commonwealth")


class ViewError(ValueError):
    """A view was requested for an unknown side or malformed state."""


def other_side(side: str) -> str:
    if side not in SIDES:
        raise ViewError(f"unknown side: {side!r}")
    return "commonwealth" if side == "axis" else "axis"


def _count(value: Any) -> int:
    try:
        return len(value)
    except TypeError:
        return 0


def _hidden(value: Any) -> dict[str, Any]:
    return {"hidden": _count(value)}


def view(state: Mapping[str, Any], side: str, *,
         reveal: bool = False) -> dict[str, Any]:
    """Return a deep copy of *state* as *side* may see it.

    ``reveal=True`` is for post-resolution inspection and tests; the AI
    must be given the default view.
    """
    if side not in SIDES:
        raise ViewError(f"unknown side: {side!r}")
    if not isinstance(state, Mapping):
        raise ViewError("state must be a mapping")

    result = copy.deepcopy(dict(state))
    hands = result.get("hands")
    if isinstance(hands, Mapping):
        redacted: dict[str, Any] = {}
        for owner, cards in hands.items():
            redacted[owner] = cards if owner == side else _hidden(cards)
        result["hands"] = redacted

    sides = result.get("sides")
    if isinstance(sides, Mapping):
        redacted_sides: dict[str, Any] = {}
        for owner, side_state in sides.items():
            if owner == side or not isinstance(side_state, Mapping):
                redacted_sides[owner] = side_state
                continue
            redacted_state = copy.deepcopy(dict(side_state))
            if "hand" in redacted_state:
                redacted_state["hand"] = _hidden(redacted_state["hand"])
            redacted_sides[owner] = redacted_state
        result["sides"] = redacted_sides

    sealed = result.get("sealed")
    if sealed is not None and not reveal:
        result["sealed"] = {"hidden": True, "count": _count(sealed)}

    result["viewer"] = side
    return result
