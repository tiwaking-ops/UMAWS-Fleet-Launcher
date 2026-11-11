"""The shared human-authority gate (reviewer items 2-3, incident seq 3630).

One helper, :func:`pmk.authority.require_human_authority`, covers task void,
pins record, class-K ``queue_decide``, ``resume_dispatch`` / ``--resume``,
profile enable/disable/cooling, ``cmd_agent_swap`` and ``MANUAL_LAUNCH``.  It
requires ``PMK_ACTOR=human:<name>`` **and** an interactive TTY, and its
refusal must not tell the caller what to set.

The tests drive the TTY seam (``pmk.authority.stdin_is_interactive``); they
never touch the live tree.
"""

from __future__ import annotations

import argparse

import pytest

from pmk import authority
from pmk.api import KernelError
from pmk.authority import AuthorityError, require_human_authority
from pmk.events import Actor

from _pmk_fixtures import make_card


HUMAN = "human:alice"


def _terminal(monkeypatch) -> None:
    monkeypatch.setattr(authority, "stdin_is_interactive", lambda: True)


def _no_terminal(monkeypatch) -> None:
    monkeypatch.setattr(authority, "stdin_is_interactive", lambda: False)


# ---------------------------------------------------------------------------
# The helper itself
# ---------------------------------------------------------------------------

def test_helper_refuses_with_no_env(monkeypatch):
    monkeypatch.delenv("PMK_ACTOR", raising=False)
    _terminal(monkeypatch)
    with pytest.raises(AuthorityError):
        require_human_authority("act")


def test_helper_refuses_a_worker_even_with_a_terminal(monkeypatch):
    monkeypatch.setenv("PMK_ACTOR", "worker:hermes")
    _terminal(monkeypatch)
    with pytest.raises(AuthorityError):
        require_human_authority("act")


def test_helper_refuses_without_a_terminal_even_for_a_human(monkeypatch):
    monkeypatch.setenv("PMK_ACTOR", HUMAN)
    _no_terminal(monkeypatch)
    with pytest.raises(AuthorityError):
        require_human_authority("act")


def test_helper_returns_the_human_when_both_hold(monkeypatch):
    monkeypatch.setenv("PMK_ACTOR", HUMAN)
    _terminal(monkeypatch)
    who = require_human_authority("act")
    assert who.kind == "human"
    assert who.agent == "alice"


def test_refusal_text_does_not_say_what_to_set(monkeypatch):
    monkeypatch.delenv("PMK_ACTOR", raising=False)
    _terminal(monkeypatch)
    with pytest.raises(AuthorityError) as exc:
        require_human_authority("task void")
    text = str(exc.value)
    assert "PMK_ACTOR" not in text
    assert "human:" not in text
    assert "--actor" not in text


def test_explicit_human_actor_is_accepted_with_a_terminal(monkeypatch):
    monkeypatch.delenv("PMK_ACTOR", raising=False)
    _terminal(monkeypatch)
    who = require_human_authority("act", actor=Actor.human("bob"))
    assert who.agent == "bob"


def test_explicit_worker_actor_is_refused(monkeypatch):
    monkeypatch.delenv("PMK_ACTOR", raising=False)
    _terminal(monkeypatch)
    with pytest.raises(AuthorityError):
        require_human_authority("act", actor=Actor(kind="worker", agent="w"))


# ---------------------------------------------------------------------------
# class-K queue decisions (Kernel API)
# ---------------------------------------------------------------------------

def test_class_k_decision_requires_a_human(monkeypatch, kernel):
    monkeypatch.delenv("PMK_ACTOR", raising=False)
    _terminal(monkeypatch)
    item = kernel.queue_add(topic="class K", options=["yes", "no"],
                            class_k=True, actor=Actor.kernel())
    with pytest.raises(KernelError) as exc:
        kernel.queue_decide(item, "yes")
    assert exc.value.reason == "not_authorized"
    # A refused decision must not consume the item.
    assert kernel.queue_list()[0]["state"] == "open"


def test_class_k_decision_refuses_a_worker_actor(monkeypatch, kernel):
    monkeypatch.delenv("PMK_ACTOR", raising=False)
    _terminal(monkeypatch)
    item = kernel.queue_add(topic="class K", options=["yes"], class_k=True)
    with pytest.raises(KernelError) as exc:
        kernel.queue_decide(item, "yes",
                            actor=Actor(kind="worker", agent="agent"))
    assert exc.value.reason == "not_authorized"


def test_class_k_decision_records_the_human(monkeypatch, kernel):
    monkeypatch.setenv("PMK_ACTOR", HUMAN)
    _terminal(monkeypatch)
    item = kernel.queue_add(topic="class K", options=["yes"], class_k=True)
    kernel.queue_decide(item, "yes")
    decided = [e for e in kernel.events() if e.type == "QUEUE_DECIDED"][-1]
    assert decided.actor.kind == "human"
    assert decided.actor.agent == "alice"


def test_non_class_k_decision_keeps_the_agent_path(monkeypatch, kernel):
    monkeypatch.delenv("PMK_ACTOR", raising=False)
    item = kernel.queue_add(topic="ordinary question", options=["a"])
    kernel.queue_decide(item, "a", actor=Actor(kind="worker", agent="a"))
    decided = [e for e in kernel.events() if e.type == "QUEUE_DECIDED"][-1]
    assert decided.actor.kind == "worker"


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

def _void_args(kernel, card):
    return argparse.Namespace(root=str(kernel.repo.root), task_id=card.id,
                              reason="authority test", actor=None)


def test_cli_task_void_refuses_without_authority(monkeypatch, kernel):
    from pmk.cli import cmd_task_void

    monkeypatch.delenv("PMK_ACTOR", raising=False)
    _terminal(monkeypatch)
    card = make_card(kernel)
    assert cmd_task_void(_void_args(kernel, card)) != 0
    assert kernel.state().tasks[card.id].state != "VOID"


def test_cli_task_void_refuses_without_a_terminal(monkeypatch, kernel):
    from pmk.cli import cmd_task_void

    monkeypatch.setenv("PMK_ACTOR", HUMAN)
    _no_terminal(monkeypatch)
    card = make_card(kernel)
    assert cmd_task_void(_void_args(kernel, card)) != 0
    assert kernel.state().tasks[card.id].state != "VOID"


def test_cli_task_void_voids_with_authority(monkeypatch, kernel):
    from pmk.cli import cmd_task_void

    monkeypatch.setenv("PMK_ACTOR", HUMAN)
    _terminal(monkeypatch)
    card = make_card(kernel)
    assert cmd_task_void(_void_args(kernel, card)) == 0
    assert kernel.state().tasks[card.id].state == "VOID"


def test_cli_pins_record_refuses_without_authority(monkeypatch, kernel):
    from pmk.cli import cmd_pins_record

    monkeypatch.delenv("PMK_ACTOR", raising=False)
    _terminal(monkeypatch)
    before = [e for e in kernel.events() if e.type == "PINS_CHECKED"]
    args = argparse.Namespace(root=str(kernel.repo.root))
    assert cmd_pins_record(args) != 0
    after = [e for e in kernel.events() if e.type == "PINS_CHECKED"]
    assert len(after) == len(before)


def test_cli_resume_refuses_without_authority(monkeypatch, kernel):
    from pmk.cli import cmd_resume

    monkeypatch.delenv("PMK_ACTOR", raising=False)
    _terminal(monkeypatch)
    kernel.repo.stop_file.parent.mkdir(parents=True, exist_ok=True)
    kernel.repo.stop_file.write_text("stopped\n", encoding="utf-8")
    assert cmd_resume(argparse.Namespace(root=str(kernel.repo.root))) != 0
    assert kernel.repo.stop_file.exists()


def test_cli_agent_swap_refuses_without_authority(monkeypatch, kernel):
    from pmk.cli import cmd_agent_swap

    monkeypatch.delenv("PMK_ACTOR", raising=False)
    _terminal(monkeypatch)
    card = make_card(kernel)
    kernel.claim(card.id, holder="p")
    args = argparse.Namespace(root=str(kernel.repo.root), task=card.id,
                              profile="p")
    assert cmd_agent_swap(args) != 0
    assert not [e for e in kernel.events() if e.type == "AGENT_RESUMED"]


def test_cli_fleet_enable_refuses_without_authority(monkeypatch, kernel):
    from pmk.cli import cmd_fleet_enable

    monkeypatch.delenv("PMK_ACTOR", raising=False)
    _terminal(monkeypatch)
    args = argparse.Namespace(root=str(kernel.repo.root), profile_id="p")
    assert cmd_fleet_enable(args) != 0
    assert not [e for e in kernel.events() if e.type == "PROFILE_ENABLED"]
