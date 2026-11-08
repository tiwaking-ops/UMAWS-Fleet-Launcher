"""Initiative.

RULE: 7.11, 7.12, 7.13, 7.14, 7.16

Each side rolls one die and adds its Initiative Rating; the higher total gains
the Initiative for the whole Game-Turn.  Ties are rerolled.  The winner then
chooses to move first or last in each Operations Stage; the first mover is
called Player A and the other Player B (7.16).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cna.core.dice import Rng, d6

RULE = "7.11-7.16"
SIDES = ("axis", "commonwealth")


class InitiativeError(ValueError):
    """An initiative input or result is invalid."""


def other_side(side: str) -> str:
    if side not in SIDES:
        raise InitiativeError(f"unknown side: {side!r}")
    return "commonwealth" if side == "axis" else "axis"


@dataclass(frozen=True)
class InitiativeResult:
    axis_roll: int
    commonwealth_roll: int
    axis_rating: int
    commonwealth_rating: int
    winner: str
    rounds: int
    rolls: tuple[tuple[int, int], ...]

    @property
    def axis_total(self) -> int:
        return self.axis_roll + self.axis_rating

    @property
    def commonwealth_total(self) -> int:
        return self.commonwealth_roll + self.commonwealth_rating

    def to_obj(self) -> dict[str, Any]:
        return {
            "axis_roll": self.axis_roll,
            "commonwealth_roll": self.commonwealth_roll,
            "axis_rating": self.axis_rating,
            "commonwealth_rating": self.commonwealth_rating,
            "axis_total": self.axis_total,
            "commonwealth_total": self.commonwealth_total,
            "winner": self.winner,
            "rounds": self.rounds,
            "rolls": [list(pair) for pair in self.rolls],
            "rule": RULE,
        }


def determine_initiative(rng: Rng, axis_rating: int,
                         commonwealth_rating: int,
                         max_rounds: int = 100) -> InitiativeResult:
    """Roll until the totals differ (7.14)."""
    for name, rating in (("axis_rating", axis_rating),
                         ("commonwealth_rating", commonwealth_rating)):
        if not isinstance(rating, int) or rating < 0:
            raise InitiativeError(f"{name} must be a non-negative integer")
    if not isinstance(max_rounds, int) or max_rounds < 1:
        raise InitiativeError("max_rounds must be a positive integer")

    rolls: list[tuple[int, int]] = []
    for round_number in range(1, max_rounds + 1):
        axis_roll = d6(rng)
        cw_roll = d6(rng)
        rolls.append((axis_roll, cw_roll))
        axis_total = axis_roll + axis_rating
        cw_total = cw_roll + commonwealth_rating
        if axis_total != cw_total:
            return InitiativeResult(
                axis_roll=axis_roll,
                commonwealth_roll=cw_roll,
                axis_rating=axis_rating,
                commonwealth_rating=commonwealth_rating,
                winner="axis" if axis_total > cw_total else "commonwealth",
                rounds=round_number,
                rolls=tuple(rolls),
            )
    raise InitiativeError(
        f"initiative remained tied after {max_rounds} rolls; cannot decide"
    )


@dataclass(frozen=True)
class PlayerOrder:
    """The rule 7.16 names for one Operations Stage."""

    player_a: str
    player_b: str
    winner: str

    def to_obj(self) -> dict[str, str]:
        return {"player_a": self.player_a, "player_b": self.player_b,
                "winner": self.winner}


def choose_order(winner: str, choice: str) -> PlayerOrder:
    """Apply the winner's ``first``/``last`` choice for one stage."""
    if winner not in SIDES:
        raise InitiativeError(f"unknown winner: {winner!r}")
    if choice not in ("first", "last"):
        raise InitiativeError("choice must be 'first' or 'last'")
    if choice == "first":
        player_a = winner
    else:
        player_a = other_side(winner)
    return PlayerOrder(player_a, other_side(player_a), winner)
