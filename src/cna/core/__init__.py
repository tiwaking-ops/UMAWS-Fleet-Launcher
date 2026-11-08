"""Core CNA primitives.

Only deterministic, I/O-free helpers belong here.  The dice module owns the
three rolls named in the rules: one die, two dice summed, and the sequential
two-digit roll (11-66, larger die first; rule 3.0).
"""

from .dice import (Dice, Rng, d6, seeded, sequential, two_dice,
                   two_dice_sum)

__all__ = ["Dice", "Rng", "d6", "seeded", "sequential", "two_dice",
           "two_dice_sum"]
