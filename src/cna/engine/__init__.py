"""The decision-point engine for the CNA digital edition.

Five things, and they are the whole surface::

    Decision(id, actions, ...)      a point where one actor chooses
    Action(id, guard=, effect=)     one declared move
    pending(decision, state)        does anything still await a choice?
    legal_actions(decision, state)  which moves are offered?
    apply(decision, state, action)  take one; returns a new state

The model is deliberately small because the rules live in the corpus, not
here.  What this engine owns is the *shape* of a choice: a point offers
only the moves the rules admit, a move can be taken only while its point
is pending, and taking a move records itself and leaves the old state
untouched.  Anything a game does with those facts is game code.

Two properties the tests pin, because everything else rests on them:

**Purity.** ``apply`` never mutates what it is given.  It works on a deep
copy and returns a fresh mapping, so an old state stays a valid witness of
what happened, and a refused move changes nothing.

**Re-checking.** ``apply`` repeats the legality check rather than trusting
a caller's earlier ``legal_actions`` answer.  A caller that did not look,
or looked at an older state, gets :class:`IllegalAction` all the same.

Usage::

    from cna.engine import Action, Decision, apply, legal_actions, pending

    bid = Action(\"bid\", effect=lambda s, a: {**s, \"high\": a.payload[\"amount\"]})
    auction = Decision(\"auction\", (bid,), actor=\"north\")

    legal_actions(auction, {\"actor\": \"north\"})   # (bid,)
    pending(auction, {\"actor\": \"north\"})         # True
    apply(auction, {\"actor\": \"north\"}, \"bid\", amount=30)

Standard library only; Windows-native; no I/O, no clock, no globals, so a
game is reproducible from its initial state and its list of choices.
"""

from __future__ import annotations

from .actions import Action, Effect, Guard, requires_actor
from .decision import (HISTORY_KEY, RESOLUTIONS_KEY, Decision, actor_in_play,
                       apply, legal_actions, pending, resolved_action)
from .errors import (AlreadyResolved, ClosedDecision, EngineError,
                     IllegalAction, UnknownAction)
from .loop import (MoveOption, StageError, StageResult, StageScenario,
                   apply_move, build_decision, controlled_hexes, legal_moves,
                   play_operations_stage, stage_phases)

__all__ = [
    # the model
    "Action",
    "Decision",
    # the verbs
    "pending",
    "legal_actions",
    "apply",
    # supporting surface
    "Guard",
    "Effect",
    "requires_actor",
    "actor_in_play",
    "resolved_action",
    "RESOLUTIONS_KEY",
    "HISTORY_KEY",
    # errors
    "EngineError",
    "IllegalAction",
    "ClosedDecision",
    "AlreadyResolved",
    "UnknownAction",
    # the Operations Stage loop
    "StageScenario",
    "StageResult",
    "StageError",
    "MoveOption",
    "play_operations_stage",
    "build_decision",
    "legal_moves",
    "apply_move",
    "controlled_hexes",
    "stage_phases",
]
