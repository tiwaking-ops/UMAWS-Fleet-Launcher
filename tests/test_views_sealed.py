"""Tests for hidden-information views and sealed commitments."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cna.engine.sealed import SealedBox, SealedError  # noqa: E402
from cna.state.model import new_state  # noqa: E402
from cna.state.views import ViewError, view  # noqa: E402


def _state() -> dict:
    return {
        "hands": {
            "axis": ["A1", "A2"],
            "commonwealth": ["C1", "C2", "C3"],
        },
        "sealed": {"axis": {"barrage": "C4218"}},
        "public": {"turn": 1},
    }


def test_a_player_sees_own_hand_but_only_the_size_of_the_other() -> None:
    original = _state()
    witness = copy.deepcopy(original)
    seen = view(original, "axis")
    assert seen["hands"]["axis"] == ["A1", "A2"]
    assert seen["hands"]["commonwealth"] == {"hidden": 3}
    assert "C1" not in repr(seen)
    assert original == witness


def test_a_view_redacts_the_real_state_schema_hand() -> None:
    state = new_state(1)
    state["sides"]["axis"]["hand"] = ["A1", "A2"]
    state["sides"]["commonwealth"]["hand"] = ["C1", "C2", "C3"]
    seen = view(state, "axis")
    assert seen["sides"]["axis"]["hand"] == ["A1", "A2"]
    assert seen["sides"]["commonwealth"]["hand"] == {"hidden": 3}
    assert "C1" not in repr(seen)
    assert state["sides"]["commonwealth"]["hand"] == ["C1", "C2", "C3"]


def test_sealed_commitments_are_hidden_until_revealed() -> None:
    state = _state()
    assert view(state, "axis")["sealed"] == {"hidden": True, "count": 1}
    assert view(state, "axis", reveal=True)["sealed"] == state["sealed"]


def test_a_view_names_its_viewer_and_refuses_unknown_sides() -> None:
    assert view(_state(), "commonwealth")["viewer"] == "commonwealth"
    with pytest.raises(ViewError):
        view(_state(), "neutral")


def test_sealed_box_cannot_reveal_until_both_sides_commit() -> None:
    box = SealedBox()
    box = box.commit("axis", {"barrage": "C4218"})
    assert box.ready is False
    with pytest.raises(SealedError):
        box.reveal()
    box = box.commit("commonwealth", {"barrage": "C4219"})
    assert box.ready is True
    assert box.reveal() == {
        "axis": {"barrage": "C4218"},
        "commonwealth": {"barrage": "C4219"},
    }


def test_sealed_box_is_immutable_and_refuses_duplicates() -> None:
    original = SealedBox()
    once = original.commit("axis", "A")
    assert original.commits == {}
    assert once.commits == {"axis": "A"}
    with pytest.raises(SealedError):
        once.commit("axis", "B")
    with pytest.raises(SealedError):
        once.commit("neutral", "X")
