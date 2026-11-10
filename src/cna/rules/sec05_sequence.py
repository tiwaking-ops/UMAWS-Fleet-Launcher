"""The Land Game sequence of play.

RULE: 5.1-5.2 (Land Game Game-Turn and sequence outline)

A Game-Turn represents approximately one week and contains three
Operations Stages (5.1).  The ordered phases below are the 5.2 sequence;
the sequence is data, not a chain of nested loops.  A Game-Turn has:

* Stage I, Initiative Determination;
* Stage II, Naval Convoy (schedule, then tactical shipping);
* three Operations Stages, each with Player A's A-L phases followed by
  Player B's F-L phases;
* Stage VI, End of Game-Turn.

The B player does not repeat A-E: those are the initiative/weather,
organization, arrival and fleet phases, which belong to the stage as a
whole.  This is why the per-stage list has 11 A phases and 6 B phases, not
two full 11-phase copies.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

RULE = "5.2"
GAME_TURN_RULE = "5.1"
GAME_TURN_DAYS = 7
OPERATIONS_STAGES = 3


class SequenceError(ValueError):
    """The sequence state is not a valid rule 5.2 position."""


@dataclass(frozen=True)
class Phase:
    id: str
    label: str
    stage: str
    actor: str
    operations_stage: int | None = None
    rule: str = RULE

    def to_obj(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "stage": self.stage,
            "actor": self.actor,
            "operations_stage": self.operations_stage,
            "rule": self.rule,
        }


_A_PHASES = (
    ("A", "Initiative Declaration"),
    ("B", "Weather Determination"),
    ("C", "Organization"),
    ("D", "Naval Convoy Arrival"),
    ("E", "Commonwealth Fleet"),
    ("F", "Reserve Designation"),
    ("G", "Movement and Combat"),
    ("H", "Truck Convoy Movement"),
    ("J", "Commonwealth Rail Movement"),
    ("K", "Repair"),
    ("L", "Patrol"),
)

_B_PHASES = tuple(item for item in _A_PHASES if item[0] >= "F")


def _operations_phases(stage_number: int, roman: str) -> tuple[Phase, ...]:
    phases: list[Phase] = []
    for letter, label in _A_PHASES:
        phases.append(Phase(f"{roman}.A.{letter}", label, roman, "A",
                            stage_number))
    for letter, label in _B_PHASES:
        phases.append(Phase(f"{roman}.B.{letter}", label, roman, "B",
                            stage_number))
    return tuple(phases)


TURN_PHASES: tuple[Phase, ...] = (
    (Phase("I", "Initiative Determination", "I", "both"),)
    + (
        Phase("II.A", "Naval Convoy Schedule", "II", "axis"),
        Phase("II.B", "Tactical Shipping", "II", "both"),
    )
    + _operations_phases(1, "III")
    + _operations_phases(2, "IV")
    + _operations_phases(3, "V")
    + (Phase("VI", "End of Game-Turn", "VI", "none"),)
)

TOTAL_PHASES = len(TURN_PHASES)
_INDEX = {phase.id: index for index, phase in enumerate(TURN_PHASES)}
if len(_INDEX) != TOTAL_PHASES:  # pragma: no cover - import-time guard
    raise RuntimeError("rule 5.2 contains duplicate phase ids")

_OPERATIONS_STAGE_NUMBERS = tuple(sorted({
    phase.operations_stage for phase in TURN_PHASES
    if phase.operations_stage is not None
}))
if _OPERATIONS_STAGE_NUMBERS != tuple(range(1, OPERATIONS_STAGES + 1)):
    raise RuntimeError("rule 5.1 must provide three Operations Stages")


def phases_for_turn() -> tuple[Phase, ...]:
    """The ordered phases of one Game-Turn."""
    return TURN_PHASES


def phase_index(phase_id: str) -> int:
    try:
        return _INDEX[phase_id]
    except KeyError as exc:
        raise SequenceError(f"unknown phase id: {phase_id!r}") from exc


def phase_for(phase_id: str) -> Phase:
    return TURN_PHASES[phase_index(phase_id)]


@dataclass(frozen=True)
class SequenceState:
    """A Game-Turn number plus a position in :data:`TURN_PHASES`."""

    turn: int = 1
    index: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.turn, int) or self.turn < 1:
            raise SequenceError("turn must be a positive integer")
        if not isinstance(self.index, int) or not 0 <= self.index < TOTAL_PHASES:
            raise SequenceError(f"index must be 0..{TOTAL_PHASES - 1}")

    @property
    def phase(self) -> Phase:
        return TURN_PHASES[self.index]

    @property
    def stage(self) -> str:
        return self.phase.stage

    @property
    def actor(self) -> str:
        return self.phase.actor

    def advance(self) -> "SequenceState":
        """Move to the next phase, wrapping into the next Game-Turn."""
        if self.index + 1 >= TOTAL_PHASES:
            return SequenceState(self.turn + 1, 0)
        return SequenceState(self.turn, self.index + 1)

    def apply_to_state(self, state: Mapping[str, Any]) -> dict[str, Any]:
        """Return a copy of *state* with the sequence position written in."""
        result = copy.deepcopy(dict(state))
        result["turn"] = self.turn
        result["phase"] = self.phase.id
        result["phase_index"] = self.index
        result["stage"] = self.phase.operations_stage or 1
        if self.actor in ("A", "B"):
            result["acting"] = self.actor
        else:
            result["acting"] = self.actor
        return result


def new_sequence(turn: int = 1) -> SequenceState:
    return SequenceState(turn, 0)
