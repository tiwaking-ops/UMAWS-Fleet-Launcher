"""Decomposition width: the measure the Overseer is now asked to improve."""

from __future__ import annotations

from types import SimpleNamespace

from fleet.overseer import OVERSEER_PROMPT
from pmk import briefing
from pmk.decompose import MAX_PATHS_PER_CARD, analyse, render_section


def _card(cid: str, scope, *, state: str = "READY", deps=()) -> SimpleNamespace:
    return SimpleNamespace(id=cid, state=state, write_scope=list(scope),
                           depends_on=list(deps))


def test_disjoint_cards_all_count() -> None:
    tasks = [_card("T-1", ["src/a.py"]), _card("T-2", ["src/b.py"]),
             _card("T-3", ["docs/c.md"])]
    report = analyse(tasks, target=3)
    assert report.width == 3
    assert report.shortfall == 0
    assert report.conflicts == []


def test_overlapping_cards_serialise() -> None:
    tasks = [_card("T-1", ["src/thing.py"]), _card("T-2", ["src/thing.py"])]
    report = analyse(tasks, target=2)
    assert report.width == 1
    assert report.shortfall == 1
    assert report.conflicts[0]["task"] == "T-1"
    assert report.conflicts[0]["path"] == "src/thing.py"


def test_a_broad_scope_does_not_beat_two_narrow_ones() -> None:
    tasks = [_card("T-BROAD", ["src/pkg/"]),
             _card("T-A", ["src/pkg/a.py"]), _card("T-B", ["src/pkg/b.py"])]
    report = analyse(tasks, target=2)
    assert report.width == 2
    assert any("T-BROAD" in (conflict["task"], conflict["other"])
               for conflict in report.conflicts)


def test_whole_tree_scope_is_flagged() -> None:
    report = analyse([_card("T-1", ["src/"])], target=1)
    assert report.broad == [{"task": "T-1", "path": "src/"}]


def test_leaf_directory_is_not_flagged_as_a_tree() -> None:
    report = analyse([_card("T-1", ["src/pkg/"])], target=1)
    assert report.broad == []


def test_oversized_card_is_flagged() -> None:
    scope = [f"src/pkg/m{index}.py" for index in range(MAX_PATHS_PER_CARD + 1)]
    report = analyse([_card("T-1", scope)], target=1)
    assert report.oversized == [{"task": "T-1",
                                 "paths": MAX_PATHS_PER_CARD + 1}]


def test_depth_measures_the_longest_chain() -> None:
    tasks = [_card("A", ["a.py"]), _card("B", ["b.py"], deps=["A"]),
             _card("C", ["c.py"], deps=["B"]), _card("D", ["d.py"])]
    report = analyse(tasks, target=4)
    assert report.depth == 3
    assert report.width == 4


def test_states_filter_whether_a_card_is_considered() -> None:
    tasks = [_card("T-1", ["a.py"]), _card("T-2", ["b.py"], state="DONE")]
    assert analyse(tasks, states=("READY",)).considered == 1
    assert analyse(tasks, states=("READY", "DONE")).width == 2


def test_render_names_the_gap_and_the_contract() -> None:
    text = render_section([_card("T-1", ["src/"])], target=10)
    assert "Leaseable width now: **1** of 10" in text
    assert "Shortfall: 9" in text
    assert "never a tree root" in text
    assert "T-1 writes `src/`" in text


def test_a_dependent_overlap_is_reported_separately() -> None:
    tasks = [_card("T-1", ["src/a.py"]), _card("T-2", ["src/a.py"], deps=["T-1"])]
    report = analyse(tasks, target=2)
    assert report.conflicts[0]["dependent"] is True


def test_briefing_shows_width_and_collision(kernel) -> None:
    for name in ("A", "B"):
        kernel.task_create(
            title=f"Card {name}", goal_ref="G-001",
            scope={"write": ["src/thing.py"], "read": []},
            oracles=[f"pytest -q tests/test_{name.lower()}.py"],
            budget={"tokens": 100, "wall_min": 5})
    text = briefing.render(kernel, "overseer")
    assert "## Decomposition" in text
    assert "Leaseable width now: **1**" in text
    assert "T-0001 <-> T-0002" in text


def test_overseer_prompt_states_the_contract() -> None:
    assert "tree root" in OVERSEER_PROMPT
    assert "12-20" in OVERSEER_PROMPT
    assert "max_total_agents" in OVERSEER_PROMPT
