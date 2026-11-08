"""Tests for the deterministic CNA dice primitives."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cna.core.dice import (Dice, d6, seeded, sequential, two_dice,
                           two_dice_sum)  # noqa: E402


class FixedRng:
    def __init__(self, values: list[int]) -> None:
        self.values = list(values)

    def randint(self, a: int, b: int) -> int:
        assert (a, b) == (1, 6)
        return self.values.pop(0)


def test_one_die_uses_a_six_sided_face() -> None:
    assert d6(FixedRng([1])) == 1
    assert d6(FixedRng([6])) == 6


def test_two_dice_sum_and_order() -> None:
    assert two_dice(FixedRng([4, 2])) == (4, 2)
    assert two_dice_sum(FixedRng([4, 2])) == 6


def test_sequential_puts_the_larger_die_first() -> None:
    assert sequential(FixedRng([3, 5])) == 53
    assert sequential(FixedRng([5, 3])) == 53
    assert sequential(FixedRng([1, 6])) == 61
    assert sequential(FixedRng([6, 6])) == 66


def test_sequential_is_always_in_range() -> None:
    rng = seeded(20261108)
    values = [sequential(rng) for _ in range(200)]
    assert all(11 <= value <= 66 for value in values)
    assert all(value // 10 >= value % 10 for value in values)


def test_seeded_rolls_are_reproducible() -> None:
    first = seeded(1234)
    second = seeded(1234)
    assert [sequential(first) for _ in range(20)] == [
        sequential(second) for _ in range(20)
    ]


def test_dice_wrapper_records_every_roll() -> None:
    dice = Dice(7)
    assert dice.d6() in range(1, 7)
    assert sum(dice.two_dice()) in range(2, 13)
    assert dice.two_dice_sum() in range(2, 13)
    assert dice.sequential() in range(11, 67)
    assert [kind for kind, _ in dice.rolls] == [
        "d6", "2d6", "2d6-sum", "sequential"
    ]


def test_dice_rejects_an_invalid_face() -> None:
    with pytest.raises(ValueError):
        d6(FixedRng([7]))
    with pytest.raises(ValueError):
        d6(FixedRng([0]))
