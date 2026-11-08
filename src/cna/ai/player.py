"""The seeded random legal player.

RULE: proposal 6.9 and PDD G-002.

The player receives only a view, the pending decision, and the actions the
engine says are legal.  It chooses uniformly among them, with a configurable
chance of taking an always-legal progress action and a hard cap that forces
progress after enough atomic actions.  It never reaches into the state.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from cna.engine import Action, Decision


class Player(Protocol):
    """Replaceable opponent interface."""

    def choose(self, view: Mapping[str, Any], decision: Decision,
               legal: Sequence[Action], rng: random.Random) -> Action:
        ...  # pragma: no cover - protocol


class NoProgressAction(RuntimeError):
    """The player cannot end the segment and cannot legally continue."""


@dataclass(frozen=True)
class RandomLegalPlayer:
    """Choose uniformly from ``legal``, with a bounded segment length."""

    p_end: float = 0.15
    max_actions_per_segment: int = 40
    end_action_ids: tuple[str, ...] = ("end_segment", "end", "pass", "decline")

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.p_end) <= 1.0:
            raise ValueError("p_end must be between 0 and 1")
        if not isinstance(self.max_actions_per_segment, int):
            raise ValueError("max_actions_per_segment must be an integer")
        if self.max_actions_per_segment < 1:
            raise ValueError("max_actions_per_segment must be at least 1")

    def choose(self, view: Mapping[str, Any], decision: Decision,
               legal: Sequence[Action], rng: random.Random) -> Action:
        if not isinstance(view, Mapping):
            raise TypeError("view must be a mapping")
        offered = tuple(legal)
        if not offered:
            raise NoProgressAction(
                f"no legal actions at {getattr(decision, 'id', '?')}"
            )
        if any(not isinstance(action, Action) for action in offered):
            raise TypeError("legal actions must be Action instances")

        ends = tuple(action for action in offered
                     if action.id in self.end_action_ids)
        try:
            taken = int(view.get("actions_in_segment", 0))
        except (TypeError, ValueError):
            taken = 0

        if taken >= self.max_actions_per_segment:
            if ends:
                return rng.choice(ends)
            raise NoProgressAction(
                f"segment reached its cap at {decision.id!r} but offers no "
                "progress action"
            )

        if ends and rng.random() < self.p_end:
            return rng.choice(ends)
        return rng.choice(offered)
