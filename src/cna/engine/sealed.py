"""Sealed simultaneous commitments.

RULE: proposal 6.4; sequence phases 5.2 G (barrage and force assignment).

Both sides commit into an immutable box.  Neither commitment can be read
until both are present; ``reveal`` then returns both choices together.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

SIDES = ("axis", "commonwealth")


class SealedError(RuntimeError):
    """A sealed commitment was used incorrectly."""


@dataclass(frozen=True)
class SealedBox:
    """An immutable pair of pending commitments."""

    commits: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "commits", MappingProxyType(dict(self.commits)))
        unknown = set(self.commits) - set(SIDES)
        if unknown:
            raise SealedError(f"unknown committing sides: {sorted(unknown)}")

    @property
    def ready(self) -> bool:
        return all(side in self.commits for side in SIDES)

    def commit(self, side: str, action: Any) -> "SealedBox":
        """Return a new box with *side*'s commitment; never mutate this one."""
        if side not in SIDES:
            raise SealedError(f"unknown side: {side!r}")
        if side in self.commits:
            raise SealedError(f"{side} has already committed")
        merged = dict(self.commits)
        merged[side] = action
        return SealedBox(merged)

    def reveal(self) -> dict[str, Any]:
        """Reveal both commitments, or refuse while one is missing."""
        if not self.ready:
            missing = [side for side in SIDES if side not in self.commits]
            raise SealedError(f"cannot reveal; still waiting for {missing}")
        return dict(self.commits)
