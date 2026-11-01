"""The contract of the CNA decision-point engine (``src/cna/engine/``).

These tests pin what everything else in the edition is allowed to assume:

* a decision point offers **only** the moves the rules admit, in
  declaration order — :func:`legal_actions`;
* a point is pending only while it is open, unspent and has something
  lawful to choose — :func:`pending`;
* :func:`apply` is the only way forward, it re-checks legality itself, and
  it never touches the state it was given;
* a taken move is recorded (resolution and ordered history), and the point
  stops being pending;
* arguments reach guards and effects through the payload, and a caller's
  ``Action`` instance contributes **arguments only** — never its own
  guard or effect.

Every test is self-contained: no fixtures from the game, no I/O, no clock.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cna.engine import (  # noqa: E402
    HISTORY_KEY,
    RESOLUTIONS_KEY,
    Action,
    AlreadyResolved,
    ClosedDecision,
    Decision,
    EngineError,
    IllegalAction,
    UnknownAction,
    actor_in_play,
    apply,
    legal_actions,
    pending,
    resolved_action,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _bid(amount: int = 0):
    """A parameterised move: record the amount under ``"high"``."""
    return Action("bid", label=f"Bid {amount}",
                  effect=lambda s, a: {**s, "high": a.payload.get("amount", amount)})


def _pass():
    return Action("pass", effect=lambda s, a: {**s, "passed": True})


def _auction(*actions, **kw) -> Decision:
    return Decision("auction", tuple(actions) or (_bid(), _pass()), **kw)


def _state(**kw) -> dict:
    state = {"actor": "north", "high": 0}
    state.update(kw)
    return state


# ---------------------------------------------------------------------------
# construction
# ---------------------------------------------------------------------------


def test_an_action_needs_an_id() -> None:
    with pytest.raises(EngineError):
        Action("")


def test_a_decision_needs_an_id() -> None:
    with pytest.raises(EngineError):
        Decision("", (_bid(),))


def test_a_decision_rejects_two_actions_with_one_id() -> None:
    with pytest.raises(EngineError):
        Decision("auction", (_bid(10), _bid(20)))


def test_a_decision_rejects_a_non_action_entry() -> None:
    with pytest.raises(EngineError):
        Decision("auction", ("bid",))                     # type: ignore[list-item]


def test_a_decision_is_immutable() -> None:
    decision = _auction()
    with pytest.raises(Exception):
        decision.id = "other"                             # type: ignore[misc]


def test_an_actions_payload_is_frozen() -> None:
    action = Action("bid", payload={"amount": 30})
    assert action.payload["amount"] == 30
    with pytest.raises(TypeError):
        action.payload["amount"] = 40                     # type: ignore[index]


# ---------------------------------------------------------------------------
# legal_actions
# ---------------------------------------------------------------------------


def test_every_declared_move_is_offered_when_nothing_blocks_it() -> None:
    decision = _auction(_bid(), _pass())
    offered = legal_actions(decision, _state())
    assert [a.id for a in offered] == ["bid", "pass"]     # declaration order


def test_a_guard_removes_its_move_from_the_offer() -> None:
    raised = Action("raise", guard=lambda s, a: s.get("high", 0) < 15)
    decision = _auction(_bid(30), raised)
    assert [a.id for a in legal_actions(decision, _state(high=20))] == ["bid"]
    assert [a.id for a in legal_actions(decision, _state(high=5))] == \
        ["bid", "raise"]


def test_a_closed_decision_offers_nothing() -> None:
    decision = _auction(_bid(), is_open=lambda s: s.get("round") == 1)
    assert legal_actions(decision, _state(round=1)) != ()
    assert legal_actions(decision, _state(round=2)) == ()


def test_a_spent_decision_offers_nothing() -> None:
    decision = _auction(_bid(), _pass())
    spent = apply(decision, _state(), "pass")
    assert legal_actions(decision, spent) == ()


def test_a_move_belonging_to_another_actor_is_not_offered() -> None:
    decision = _auction(Action("bid", actor="north"), Action("fold", actor="east"))
    assert [a.id for a in legal_actions(decision, {"actor": "north"})] == ["bid"]
    assert [a.id for a in legal_actions(decision, {"actor": "east"})] == ["fold"]


def test_the_decisions_own_actor_is_used_when_the_state_names_none() -> None:
    decision = Decision("auction", (Action("bid", actor="north"),), actor="north")
    assert [a.id for a in legal_actions(decision, {})] == ["bid"]
    assert pending(decision, {}) is True


def test_a_move_naming_an_actor_nobody_is_is_not_offered() -> None:
    decision = _auction(Action("bid", actor="north"))
    assert legal_actions(decision, {}) == ()


def test_legal_actions_needs_a_decision() -> None:
    with pytest.raises(EngineError):
        legal_actions("auction", _state())                # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# pending
# ---------------------------------------------------------------------------


def test_pending_turns_false_once_a_choice_is_taken() -> None:
    decision = _auction(_bid(), _pass())
    state = _state()
    assert pending(decision, state) is True
    assert pending(decision, apply(decision, state, "bid")) is False


def test_pending_is_false_when_the_point_is_closed() -> None:
    decision = _auction(_bid(), is_open=lambda s: False)
    assert pending(decision, _state()) is False


def test_pending_is_false_when_nothing_lawful_is_offered() -> None:
    decision = _auction(Action("bid", guard=lambda s, a: False))
    assert pending(decision, _state()) is False


def test_pending_over_several_points_is_true_if_any_is() -> None:
    open_point = _auction(_bid(), _pass())
    closed_point = Decision("closed", (_bid(),), is_open=lambda s: False)
    state = _state()
    assert pending([closed_point, open_point], state) is True
    assert pending([closed_point], state) is False
    assert pending(iter(()), state) is False


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------


def test_apply_returns_the_effects_state() -> None:
    decision = _auction(_bid(), _pass())
    new = apply(decision, _state(), "bid", amount=30)
    assert new["high"] == 30


def test_apply_records_the_resolution_and_the_history() -> None:
    decision = _auction(_bid(), _pass())
    new = apply(decision, _state(), "pass")
    assert resolved_action(new, "auction") == "pass"
    assert new[RESOLUTIONS_KEY] == {"auction": "pass"}
    assert new[HISTORY_KEY] == [{"decision": "auction", "action": "pass",
                                 "actor": "north"}]


def test_history_keeps_the_order_choices_were_taken_in() -> None:
    first = Decision("first", (_pass(),))
    second = Decision("second", (_pass(),))
    state = _state()
    state = apply(first, state, "pass")
    state = apply(second, state, "pass")
    assert [entry["decision"] for entry in state[HISTORY_KEY]] == \
        ["first", "second"]


def test_apply_leaves_the_old_state_completely_untouched() -> None:
    decision = _auction(_bid(), _pass())
    old = _state(purse={"north": 10, "east": 10})
    witness = copy.deepcopy(old)
    new = apply(decision, old, "bid", amount=30)
    assert old == witness                       # nothing the engine did leaked
    assert new["purse"] == {"north": 10, "east": 10}


def test_the_new_state_shares_no_structure_with_the_old_one() -> None:
    decision = _auction(_bid(), _pass())
    old = _state(purse={"north": 10})
    new = apply(decision, old, "bid", amount=30)
    new["purse"]["north"] = 999
    assert old["purse"]["north"] == 10          # deep, not shallow, copy


def test_an_effect_that_mutates_its_input_cannot_corrupt_the_old_state() -> None:
    def greedy(state, action):
        state.setdefault("purse", {})["north"] -= 1      # rude, and contained
        return state

    decision = Decision("toll", (Action("pay", effect=greedy),))
    old = {"actor": "north", "purse": {"north": 5}}
    new = apply(decision, old, "pay")
    assert old["purse"]["north"] == 5
    assert new["purse"]["north"] == 4


def test_apply_is_deterministic() -> None:
    decision = _auction(_bid(), _pass())
    two_runs = [apply(decision, _state(), "bid", amount=30) for _ in range(2)]
    assert two_runs[0] == two_runs[1]


def test_an_effect_may_return_a_mapping_and_only_a_mapping() -> None:
    from cna.engine import Action as A
    bad = A("bad", effect=lambda s, a: 42)               # type: ignore[arg-type,return-value]
    decision = Decision("broken", (bad,))
    with pytest.raises(EngineError):
        apply(decision, _state(), "bad")


# ---------------------------------------------------------------------------
# apply — refusals
# ---------------------------------------------------------------------------


def test_an_unknown_action_is_refused() -> None:
    decision = _auction(_bid(), _pass())
    with pytest.raises(UnknownAction):
        apply(decision, _state(), "cheat")


def test_a_guarded_off_action_is_refused_even_when_named() -> None:
    decision = _auction(Action("bid", guard=lambda s, a: False))
    with pytest.raises(IllegalAction) as caught:
        apply(decision, _state(), "bid")
    assert caught.value.decision_id == "auction"
    assert caught.value.action_id == "bid"


def test_a_closed_point_refuses_every_move() -> None:
    decision = _auction(_bid(), is_open=lambda s: False)
    with pytest.raises(ClosedDecision):
        apply(decision, _state(), "bid")


def test_a_point_cannot_be_spent_twice() -> None:
    decision = _auction(_bid(), _pass())
    spent = apply(decision, _state(), "pass")
    with pytest.raises(AlreadyResolved) as caught:
        apply(decision, spent, "bid")
    assert caught.value.chosen == "pass"


def test_another_actors_move_is_refused() -> None:
    decision = _auction(Action("bid", actor="north"), Action("fold", actor="east"))
    with pytest.raises(IllegalAction) as caught:
        apply(decision, {"actor": "east"}, "bid")
    assert caught.value.action_id == "bid"


def test_a_refused_action_leaves_the_state_untouched() -> None:
    decision = _auction(Action("bid", guard=lambda s, a: False))
    old = _state()
    witness = copy.deepcopy(old)
    with pytest.raises(IllegalAction):
        apply(decision, old, "bid")
    assert old == witness
    assert RESOLUTIONS_KEY not in old and HISTORY_KEY not in old


def test_an_effect_that_explodes_leaves_the_state_untouched() -> None:
    def boom(state, action):
        raise RuntimeError("rule 4.2 disagrees")

    decision = Decision("fatal", (Action("risky", effect=boom),))
    old = _state()
    with pytest.raises(RuntimeError):
        apply(decision, old, "risky")
    assert old == _state()
    assert pending(decision, old) is True


# ---------------------------------------------------------------------------
# payload and caller-supplied actions
# ---------------------------------------------------------------------------


def test_payload_reaches_the_guard_and_the_effect() -> None:
    affordable = Action("bid",
                        guard=lambda s, a: a.payload["amount"] <= s["purse"],
                        effect=lambda s, a: {**s,
                                             "purse": s["purse"] - a.payload["amount"]})
    decision = Decision("auction", (affordable,))
    state = {"actor": "north", "purse": 12}
    # Previewed with the same arguments it would be taken with.
    assert legal_actions(decision, state, amount=30) == ()
    assert [a.id for a in legal_actions(decision, state, amount=12)] == ["bid"]
    assert pending(decision, state, amount=30) is False
    new = apply(decision, state, "bid", amount=5)
    assert new["purse"] == 7


def test_an_unaffordable_bid_is_refused_rather_than_going_negative() -> None:
    affordable = Action("bid",
                        guard=lambda s, a: a.payload["amount"] <= s["purse"],
                        effect=lambda s, a: {**s,
                                             "purse": s["purse"] - a.payload["amount"]})
    decision = Decision("auction", (affordable,))
    old = {"actor": "north", "purse": 12}
    with pytest.raises(IllegalAction):
        apply(decision, old, "bid", amount=30)
    assert old["purse"] == 12


def test_bound_arguments_do_not_stick_to_the_declared_action() -> None:
    decision = _auction(_bid())
    apply(decision, _state(), "bid", amount=30)
    assert dict(decision.actions[0].payload) == {}


def test_a_callers_action_instance_supplies_arguments_only() -> None:
    """A caller's Action is never allowed to bring its own rules."""

    def honest(state, action):
        return {**state, "high": action.payload.get("amount", 0)}

    def sneaky(state, action):
        return {**state, "high": 1_000_000}

    declared = Decision("auction", (Action("bid", effect=honest),))
    new = apply(declared, _state(), Action("bid", effect=sneaky, payload={"amount": 30}))
    assert new["high"] == 30                    # the declared effect ran


def test_apply_accepts_an_action_or_its_id_alike() -> None:
    decision = _auction(_bid(), _pass())
    by_id = apply(decision, _state(), "pass")
    by_object = apply(decision, _state(), _pass())
    assert by_id[RESOLUTIONS_KEY] == by_object[RESOLUTIONS_KEY] == {"auction": "pass"}


def test_apply_rejects_an_argument_that_is_neither() -> None:
    decision = _auction(_bid())
    with pytest.raises(EngineError):
        apply(decision, _state(), 42)                     # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# actor resolution
# ---------------------------------------------------------------------------


def test_the_state_named_actor_wins_over_the_decisions_own() -> None:
    decision = Decision("auction", (Action("bid", actor="north"),), actor="east")
    assert actor_in_play({"actor": "east"}, decision) == "east"
    assert legal_actions(decision, {"actor": "east"}) == ()


def test_resolved_action_is_none_before_any_choice() -> None:
    assert resolved_action(_state(), "auction") is None
