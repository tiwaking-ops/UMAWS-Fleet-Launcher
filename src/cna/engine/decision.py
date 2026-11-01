"""Decision points, and the three verbs played on them.

A **decision point** is a moment in the rules where the game stops and one
actor chooses one move: respond to a challenge or not, bid or pass, which
card to discard.  Everything here is built to keep that moment honest:

* the offered moves come from :func:`legal_actions`, never from whoever
  is asking — the caller cannot reach an action the rules do not offer;
* a point is :func:`pending` only while it is open, unspent and actually
  has something lawful to choose;
* :func:`apply` is the single way forward.  It re-checks legality itself
  (it never trusts a caller's earlier answer), works on a private deep
  copy, records the choice, and returns a **new** state.  The state handed
  in is never modified, and a refused or exploding action leaves it
  untouched.

State is an ordinary ``Mapping[str, Any]``.  The engine claims exactly two
keys inside it:

``decisions``
    ``{decision id: chosen action id}`` — what has been resolved.
``history``
    an ordered list of ``{"decision", "action", "actor"}`` records, oldest
    first.  Resolution order is part of the game's evidence, so it is
    recorded rather than reconstructed.

Everything else in the mapping belongs to the game rules.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, MutableMapping

from .actions import Action
from .errors import (AlreadyResolved, ClosedDecision, EngineError,
                     IllegalAction, UnknownAction)

__all__ = ["RESOLUTIONS_KEY", "HISTORY_KEY", "Decision", "legal_actions",
           "pending", "apply", "resolved_action"]

RESOLUTIONS_KEY = "decisions"
HISTORY_KEY = "history"

State = Mapping[str, Any]
OpenPredicate = Callable[[State], bool]


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _as_mapping(value: Any, what: str) -> MutableMapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EngineError(f"{what} must be a mapping, got {type(value).__name__}")
    return dict(value)


def _resolutions(state: State) -> dict[str, Any]:
    raw = state.get(RESOLUTIONS_KEY) or {}
    return dict(raw) if isinstance(raw, Mapping) else {}


def _history(state: State) -> list[dict[str, Any]]:
    raw = state.get(HISTORY_KEY) or []
    return [dict(item) for item in raw] if isinstance(raw, Iterable) else []


def resolved_action(state: State, decision_id: str) -> str | None:
    """The action id chosen at *decision_id*, or ``None`` if still unspent."""
    choice = _resolutions(state).get(decision_id)
    return choice if isinstance(choice, str) else None


def actor_in_play(state: State, decision: "Decision") -> str | None:
    """Who is acting: the actor in the state, else the decision's own."""
    actor = state.get("actor")
    if actor is not None:
        return actor if isinstance(actor, str) else None
    return decision.actor


# ---------------------------------------------------------------------------
# the decision point
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Decision:
    """A point where one actor chooses one of several declared moves.

    Parameters
    ----------
    id:
        Stable identifier.  It is the key the resolution is filed under,
        so it must be unique within a game.
    actions:
        The declared moves, in the order they are offered.
    prompt:
        Human-facing text.  Data only; never parsed.
    actor:
        Who chooses, when the state does not say.  Either source may be
        used; the state wins (see :func:`actor_in_play`).
    is_open:
        A predicate over the state answering "is this point live now?".
        ``None`` means always open.
    """

    id: str
    actions: tuple[Action, ...] = ()
    prompt: str = ""
    actor: str | None = None
    is_open: OpenPredicate | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise EngineError("a decision needs a non-empty id")
        actions = tuple(self.actions)
        seen: set[str] = set()
        for action in actions:
            if not isinstance(action, Action):
                raise EngineError(
                    f"decision {self.id!r} has a non-action entry "
                    f"{type(action).__name__}")
            if action.id in seen:
                raise EngineError(
                    f"decision {self.id!r} declares action {action.id!r} twice")
            seen.add(action.id)
        object.__setattr__(self, "actions", actions)

    # -- reading -------------------------------------------------------
    def open(self, state: State) -> bool:
        """Is this point live in *state*?"""
        if self.is_open is None:
            return True
        return bool(self.is_open(state))

    def action(self, action_id: str) -> Action:
        """The declared action with *action_id*.

        Raises :class:`~cna.engine.errors.UnknownAction` — a missing action
        is an illegal move, not a lookup failure to be caught elsewhere.
        """
        for action in self.actions:
            if action.id == action_id:
                return action
        raise UnknownAction(self.id, action_id)

    def legal_actions(self, state: State,
                      **payload: Any) -> tuple[Action, ...]:
        return legal_actions(self, state, **payload)

    def pending(self, state: State, **payload: Any) -> bool:
        return pending(self, state, **payload)

    def apply(self, state: State, action: Action | str,
              **payload: Any) -> dict[str, Any]:
        return apply(self, state, action, **payload)


# ---------------------------------------------------------------------------
# the verbs
# ---------------------------------------------------------------------------

def legal_actions(decision: Decision, state: State,
                  **payload: Any) -> tuple[Action, ...]:
    """The moves offered at *decision* in *state*, in declaration order.

    An action is offered only when all four hold: the point is open, the
    point is unspent, the actor in play may take it, and its own guard
    admits it.  Anything else is silently absent — a caller cannot even
    name a move the rules withhold, let alone take it.

    Keyword arguments are bound to each candidate before its guard runs,
    so a parameterised move can be *previewed* with the same arguments it
    would be taken with::

        legal_actions(auction, state, amount=30)

    The actions returned are the **declared** ones: the payload filters,
    it does not stick.
    """
    if not isinstance(decision, Decision):
        raise EngineError("legal_actions takes a Decision")
    state = _as_mapping(state, "state")
    if not decision.open(state):
        return ()
    if resolved_action(state, decision.id) is not None:
        return ()
    acting = actor_in_play(state, decision)
    offered = []
    for action in decision.actions:
        if action.actor is not None and acting != action.actor:
            continue
        candidate = action.bind(**payload) if payload else action
        if candidate.legal(state):
            offered.append(action)
    return tuple(offered)


def pending(decision: Decision | Iterable[Decision], state: State,
            **payload: Any) -> bool:
    """Does anything still await a choice?

    Given one decision: it is pending while it is open, unspent and has at
    least one legal action.  A point that is open but offers nothing lawful
    is *not* pending — there is no choice to make.

    Given several: pending if **any** of them is, evaluated in order.
    Keyword arguments are bound exactly as in :func:`legal_actions`.
    """
    if isinstance(decision, Decision):
        return bool(legal_actions(decision, state, **payload))
    pending_any = False
    for item in decision:
        if not isinstance(item, Decision):
            raise EngineError("pending takes a Decision or an iterable of them")
        if pending(item, state, **payload):
            pending_any = True
    return pending_any


def apply(decision: Decision, state: State, action: Action | str,
          **payload: Any) -> dict[str, Any]:
    """Take *action* at *decision* in *state*.  Returns the new state.

    The check is repeated here rather than trusted from the caller: an
    action is legal only if it is currently offered by
    :func:`legal_actions`.  Otherwise :class:`IllegalAction` is raised and
    *state* is left exactly as it was.

    ``action`` may be an :class:`Action` or its id; keyword arguments are
    bound as payload (see :meth:`Action.bind`).

    The returned state is a fresh mapping.  Anything the effect did not
    mention is carried over, deeply copied, so nothing reachable from the
    old state is shared with the new one.
    """
    if not isinstance(decision, Decision):
        raise EngineError("apply takes a Decision")
    original = _as_mapping(state, "state")

    # Resolve what was asked for, without yet judging it.
    if isinstance(action, Action):
        # Only the *declared* definition is ever run; a caller's instance
        # supplies the id and its payload arguments, never the guard or
        # the effect, or a caller could bring its own rules.
        offered = decision.action(action.id)
        merged = dict(action.payload)
        merged.update(payload)
        asked = offered.bind(**merged)
    elif isinstance(action, str):
        offered = decision.action(action)
        asked = offered.bind(**payload)
    else:
        raise EngineError("action must be an Action or an action id")

    # Re-check legality from scratch.
    if not decision.open(original):
        raise ClosedDecision(decision.id, asked.id)
    chosen = resolved_action(original, decision.id)
    if chosen is not None:
        raise AlreadyResolved(decision.id, asked.id, chosen)
    acting = actor_in_play(original, decision)
    if asked.id not in {item.id
                         for item in legal_actions(decision, original,
                                                   **dict(asked.payload))}:
        raise IllegalAction(decision.id, asked.id,
                            _refusal_reason(offered, asked, original, acting))

    working: MutableMapping[str, Any] = copy.deepcopy(original)
    new_state = dict(asked.apply(working))

    resolutions = _resolutions(new_state)
    resolutions[decision.id] = asked.id
    new_state[RESOLUTIONS_KEY] = resolutions
    history = _history(new_state)
    history.append({"decision": decision.id, "action": asked.id,
                    "actor": acting})
    new_state[HISTORY_KEY] = history
    return new_state


def _refusal_reason(offered: Action, asked: Action, state: State,
                    acting: str | None) -> str:
    """Why a move is not offered, worded for whoever asked for it.

    *asked* — the move as it was asked for, arguments and all — is the one
    whose guard is consulted; the offer was judged on those same
    arguments.
    """
    if offered.actor is not None and acting != offered.actor:
        # Not this actor's move.  No detail beyond that: another seat's
        # options are none of this caller's business.
        return "another actor may take it"
    if not asked.legal(state):
        return "guard does not admit it"
    return "not offered in this state"
