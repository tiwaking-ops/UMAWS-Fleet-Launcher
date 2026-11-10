"""Tests for §32 abstract supply and motorization in the stage loop."""

from __future__ import annotations

from fractions import Fraction

import pytest

from cna.engine.loop import (StageError, StageScenario, apply_assault,
                             apply_move, legal_moves)
from cna.rules.sec11_combat import AssaultRoll
from cna.state.model import new_state

LINE = {
    "A": ("B",),
    "B": ("A", "C"),
    "C": ("B",),
}

TRIANGLE = {
    "A": ("B", "C"),
    "B": ("A", "C"),
    "C": ("A", "B"),
}


def unit(side: str, position: str, **fields):
    record = {
        "side": side,
        "position": position,
        "kind": "combat",
        "unit_class": "infantry",
        "size_level": "battalion",
        "toe_strength": 4,
        "offensive_close_assault": 5,
        "defensive_close_assault": 5,
        "stacking_points": 3,
        "base_cpa": 12,
    }
    record.update(fields)
    return record


def supply(side: str, position: str, **fields):
    record = {"side": side, "position": position}
    record.update(fields)
    return record


def make_state(units, supplies=None):
    state = new_state(7)
    state["units"] = units
    state["supplies"] = supplies or {}
    return state


def make_scenario(graph=LINE, *, cost=None, **fields):
    return StageScenario(
        neighbours=lambda hex_id: graph.get(hex_id, ()),
        cost=cost or (lambda origin, destination, unit: Fraction(1)),
        hex_limits={hex_id: 6 for hex_id in graph},
        **fields,
    )


class FixedRng:
    def __init__(self, *values):
        self.values = iter(values)

    def randint(self, low, high):
        return next(self.values)


def no_loss(role, differential, roll):
    return AssaultRoll(roll=roll)


def test_32_24_tank_move_draws_fuel_from_its_supply_unit():
    state = make_state(
        {"ax-tank": unit(
            "axis", "A", unit_class="tank", base_cpa=12, supply_id="sup-1")},
        {"sup-1": supply("axis", "A", ammo=40, fuel=60)},
    )

    after = apply_move(state, "axis", "ax-tank", "B", make_scenario(),
                       phase_key="segment-1")

    assert after["supplies"]["sup-1"]["fuel"] == 58
    assert after["units"]["ax-tank"]["fuel_required"] == 2
    assert after["units"]["ax-tank"]["fuel_spent"] == 2
    assert after["units"]["ax-tank"]["fuel_paid_stage"] == "T1S1"


def test_32_23_first_move_that_crosses_cpa_uses_the_doubled_fuel_cost():
    state = make_state(
        {"ax-tank": unit(
            "axis", "A", unit_class="tank", motorized=True, base_cpa=1,
            supply_id="sup-1")},
        {"sup-1": supply("axis", "A", ammo=40, fuel=60)},
    )

    after = apply_move(
        state, "axis", "ax-tank", "B",
        make_scenario(cost=lambda origin, destination, moving: Fraction(2)),
        phase_key="segment-1",
    )

    assert after["supplies"]["sup-1"]["fuel"] == 56
    assert after["units"]["ax-tank"]["fuel_required"] == 4


def test_32_21_assault_draws_ammo_per_battalion_equivalent():
    state = make_state(
        {
            "ax-1": unit(
                "axis", "A", battalion_equivalents=2, supply_id="sup-1"),
            "cw-1": unit("commonwealth", "C"),
        },
        {"sup-1": supply("axis", "A", ammo=40, fuel=60)},
    )

    after = apply_assault(
        state, "axis", "ax-1", "C",
        make_scenario(TRIANGLE, assault_table=no_loss),
        phase_key="segment-1", rng=FixedRng(3, 3, 2, 2),
    )

    assert after["supplies"]["sup-1"]["ammo"] == 36
    assert after["units"]["ax-1"]["ammo_required"] == 4
    assert after["units"]["ax-1"]["ammo_spent"] == 4


def test_32_13_entering_an_enemy_supply_hex_captures_the_counter():
    state = make_state(
        {"ax-1": unit("axis", "A")},
        {"cw-sup": supply("commonwealth", "B", ammo=17, fuel=23)},
    )

    after = apply_move(state, "axis", "ax-1", "B", make_scenario(),
                       phase_key="segment-1")

    assert after["supplies"] == {}
    assert after["supply_captures"] == [{
        "by": "ax-1",
        "side": "axis",
        "hex": "B",
        "supplies": [{
            "id": "cw-sup",
            "side": "commonwealth",
            "ammo": 17,
            "fuel": 23,
            "dummy": False,
        }],
    }]


def test_32_9_abstract_supply_ignores_road_track_stacking_limit():
    state = make_state({
        "ax-1": unit("axis", "A"),
        "ax-2": unit("axis", "A"),
    })
    scenario = make_scenario(road_track=lambda origin, destination: True)

    first = apply_move(state, "axis", "ax-1", "B", scenario,
                       phase_key="segment-1")
    assert legal_moves(first, "axis", scenario, phase_key="segment-1") == ()

    abstract = make_scenario(road_track=lambda origin, destination: True,
                             abstract_supply=True)
    first_abstract = apply_move(state, "axis", "ax-1", "B", abstract,
                                phase_key="segment-1")
    assert any(option.unit_id == "ax-2"
               for option in legal_moves(first_abstract, "axis", abstract,
                                         phase_key="segment-1"))


def test_32_54_a_transported_tank_is_not_legal_but_leg_infantry_is():
    tank_state = make_state({
        "ax-tank": unit("axis", "A", unit_class="tank", transport_cpa=10),
    })
    assert legal_moves(tank_state, "axis", make_scenario(),
                       phase_key="segment-1") == ()

    infantry_state = make_state({
        "ax-leg": unit("axis", "A", transport_cpa=10),
    })
    assert any(option.unit_id == "ax-leg"
               for option in legal_moves(infantry_state, "axis",
                                         make_scenario(),
                                         phase_key="segment-1"))

    gun_state = make_state({
        "ax-gun": unit("axis", "A", unit_class="artillery",
                       transport_cpa=10),
    })
    assert any(option.unit_id == "ax-gun"
               for option in legal_moves(gun_state, "axis", make_scenario(),
                                         phase_key="segment-1"))


def test_linked_unit_without_enough_fuel_cannot_move():
    state = make_state(
        {"ax-tank": unit(
            "axis", "A", unit_class="tank", base_cpa=12, supply_id="sup-1")},
        {"sup-1": supply("axis", "A", ammo=40, fuel=1)},
    )

    assert legal_moves(state, "axis", make_scenario(),
                       phase_key="segment-1") == ()
    with pytest.raises(StageError):
        apply_move(state, "axis", "ax-tank", "B", make_scenario(),
                   phase_key="segment-1")


def test_unlinked_units_keep_the_existing_fuel_free_behavior():
    state = make_state({
        "ax-tank": unit("axis", "A", unit_class="tank", base_cpa=12),
    })

    after = apply_move(state, "axis", "ax-tank", "B", make_scenario(),
                       phase_key="segment-1")

    assert after["supplies"] == {}
    assert "fuel_required" not in after["units"]["ax-tank"]
