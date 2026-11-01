"""Actions: the declared moves available at a decision point.

An :class:`Action` is *data plus two callables*, and nothing else:

* ``guard`` — a predicate over ``(state, action)``.  It answers "is this
  move offered here?".  A guard is a **pure predicate**: no side effects,
  no mutation of the state it is given.
* ``effect`` — a function from ``(state, action)`` to a **new** state.
  It never mutates its input; ``apply`` hands it a private deep copy and
  adopts whatever mapping it returns.

Both are optional.  An unguarded action is always offered; an action
without an effect is a pure *choice* — taking it records the choice and
changes nothing else, which is exactly how "pass" and "decline" are
written.

``payload`` carries the arguments of a parameterised move (bid 30, take
two cards, target this unit).  ``bind`` returns a copy of the action with
its payload merged, so a declared action stays immutable while a specific
invocation carries its own arguments.  Guards and effects read the
arguments off the action they are handed, never from a closure.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any, Callable, Mapping, MutableMapping

from .errors import EngineError

__all__ = ["Guard", "Effect", "Action", "requires_actor"]

Guard = Callable[[Mapping[str, Any], "Action"], bool]
Effect = Callable[[Mapping[str, Any], "Action"], Mapping[str, Any]]


def requires_actor(actor: str) -> Guard:
    """A convenience guard: only *actor* may take this action.

    The engine already enforces ``Action.actor``; this exists for the case
    where the restriction belongs to the rule rather than to the move
    (for instance "only the player who was challenged may respond").
    """
    def guard(state: Mapping[str, Any], action: Action) -> bool:
        return state.get("actor") == actor
    return guard


@dataclass(frozen=True)
class Action:
    """One declared move.

    Parameters
    ----------
    id:
        Stable identifier, unique within its decision point.
    label:
        Human-facing text.  Data only; the engine never parses it.
    actor:
        Who may take this move, or ``None`` for anyone.  Compared against
        the actor in play (see :func:`cna.engine.decision.apply`).
    guard, effect:
        Pure predicate and pure state transition, as described above.
    payload:
        Immutable mapping of arguments for a parameterised move.
    """

    id: str
    label: str = ""
    actor: str | None = None
    guard: Guard | None = None
    effect: Effect | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise EngineError("an action needs a non-empty id")
        # Payloads are frozen too: a bound action must never be changed
        # under the feet of a guard or effect that already holds it.
        object.__setattr__(self, "payload",
                           MappingProxyType(dict(self.payload)))

    # -- reading -------------------------------------------------------
    def legal(self, state: Mapping[str, Any]) -> bool:
        """Does this action's own guard admit it in *state*?

        This is deliberately narrow: it answers for the **action**, not
        for the decision point.  Whether the point is open, unresolved
        and this actor's to take is decided by ``legal_actions``.
        """
        if self.guard is None:
            return True
        return bool(self.guard(state, self))

    def apply(self, state: Mapping[str, Any]) -> MutableMapping[str, Any]:
        """Run this action's effect, returning a new state.

        The action is given *state* only to hand to its effect; no engine
        bookkeeping (resolution, history) happens here.
        """
        if self.effect is None:
            return dict(state)
        result = self.effect(state, self)
        if not isinstance(result, Mapping):
            raise EngineError(
                f"effect of action {self.id!r} must return a mapping, "
                f"got {type(result).__name__}")
        return dict(result)

    def bind(self, **updates: Any) -> Action:
        """Return a copy of this action with *updates* merged into payload."""
        if not updates:
            return self
        merged = dict(self.payload)
        merged.update(updates)
        return replace(self, payload=MappingProxyType(merged))

    def describe(self) -> dict[str, Any]:
        """A JSON-able summary, for logs and for any front-end menu."""
        return {"id": self.id, "label": self.label or self.id,
                "actor": self.actor, "payload": dict(self.payload)}
