"""Dice used by the CNA rules.

RULE: 3.0 (dice), 7.14 (initiative), 29.1 (weather)

CNA uses three forms:

* one six-sided die;
* two dice summed;
* the **sequential** roll: two dice read as a two-digit number with the
  larger die first, so the result is always in 11..66.  The tens digit is
  therefore never smaller than the units digit.

Every function takes an explicit RNG.  There is no module-level random
generator, so a game is reproducible from its seed and its action log.
"""

from __future__ import annotations

import random
from typing import Protocol


class Rng(Protocol):
    """The small slice of ``random.Random`` the dice need."""

    def randint(self, a: int, b: int) -> int:  # pragma: no cover - protocol
        ...


def d6(rng: Rng) -> int:
    """Roll one six-sided die (RULE: 3.0)."""
    value = rng.randint(1, 6)
    if not isinstance(value, int) or not 1 <= value <= 6:
        raise ValueError(f"RNG returned an invalid d6 face: {value!r}")
    return value


def two_dice(rng: Rng) -> tuple[int, int]:
    """Roll two dice, returning them in the order rolled (RULE: 3.0)."""
    return d6(rng), d6(rng)


def two_dice_sum(rng: Rng) -> int:
    """Roll two dice and return their sum (RULE: 3.0)."""
    first, second = two_dice(rng)
    return first + second


def sequential(rng: Rng) -> int:
    """Roll the CNA sequential value in 11..66 (RULE: 3.0).

    The larger die is the tens digit.  ``(3, 5)`` and ``(5, 3)`` both read
    as 53; the smaller die is never placed first.
    """
    first, second = two_dice(rng)
    high, low = max(first, second), min(first, second)
    return high * 10 + low


def seeded(seed: int) -> random.Random:
    """A seeded RNG suitable for a headless game or a replay."""
    if not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    return random.Random(seed)


class Dice:
    """A small recording wrapper around a seeded RNG.

    The recorded rolls are useful in tests and in an evidence log.  A game
    should persist the RNG state (see :mod:`cna.state.model`), not rely on
    this convenience class for replay.
    """

    def __init__(self, seed: int) -> None:
        self._rng = seeded(seed)
        self.rolls: list[tuple[str, object]] = []

    def d6(self) -> int:
        value = d6(self._rng)
        self.rolls.append(("d6", value))
        return value

    def two_dice(self) -> tuple[int, int]:
        value = two_dice(self._rng)
        self.rolls.append(("2d6", value))
        return value

    def two_dice_sum(self) -> int:
        value = two_dice_sum(self._rng)
        self.rolls.append(("2d6-sum", value))
        return value

    def sequential(self) -> int:
        value = sequential(self._rng)
        self.rolls.append(("sequential", value))
        return value

    @property
    def rng(self) -> random.Random:
        return self._rng
