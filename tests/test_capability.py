"""Tests for the Capability Point system (§6).

The units in these tests are synthetic fixtures.  All numeric CPA, Cohesion
and Stacking values stand in for OA/TOE data; no historical rating is
asserted.  The rule cases exercised are named in each test's docstring.
"""

from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cna.rules.sec06_capability import (  # noqa: E402
    COLLAPSE_AT,
    CP_COSTS,
    DYNAMIC_CP_COSTS,
    MAX_COHESION,
    CapabilityError,
    CapabilityState,
    battle_cohesion,
    cohesion_by_unit,
    cp_cost,
    formation_cohesion,
    formation_cpa,
)


def unit(unit_id: str = "u", base_cpa: int = 10, **kwargs) -> CapabilityState:
    return CapabilityState(unit_id, base_cpa, **kwargs)


# ---------------------------------------------------------------------------
# 6.11-6.17: allowance, costs, and motorization
# ---------------------------------------------------------------------------

def test_exact_fractional_cp_is_tracked() -> None:
    """6.12: a 3/2 CP cost is not rounded away."""
    u = unit(base_cpa=8).spend(Fraction(3, 2))
    assert u.spent == Fraction(3, 2)
    assert u.remaining == Fraction(13, 2)
    assert u.dp_earned == 0


def test_gun_with_zero_cpa_gets_ten_except_for_movement() -> None:
    """6.11: a zero-CPA Gun is 10 for all purposes other than movement."""
    gun = unit(base_cpa=0, is_gun=True)
    assert gun.cpa_for("general") == 10
    assert gun.cpa_for("movement") == 0
    assert unit(base_cpa=0, is_gun=False).cpa_for("general") == 0


def test_parent_formation_uses_its_lowest_cpa() -> None:
    """6.15: a moving parent formation uses the lowest member CPA."""
    units = [unit("a", 25), unit("b", 10), unit("c", 20)]
    assert formation_cpa(units) == 10


def test_motorized_infantry_assumes_the_truck_cpa() -> None:
    """6.17: infantry may assume the carrying truck's CPA."""
    infantry = unit("inf", 8)
    motorized = infantry.motorize(20)
    assert motorized.cpa == 20
    assert motorized.spent == 0
    assert motorized.demotorize().cpa == 8


def test_non_infantry_cannot_be_motorized() -> None:
    """6.17: only units with a base CPA of 10 or less may motorize."""
    with pytest.raises(CapabilityError, match="infantry"):
        unit("tank", 25).motorize(20)


# ---------------------------------------------------------------------------
# 6.21-6.24: disorganization, cohesion, and reorganization
# ---------------------------------------------------------------------------

def test_over_allowance_awards_one_dp_per_full_cp() -> None:
    """6.21: 18 CP against a CPA of 15 earns 3 DP."""
    u = unit(base_cpa=15).spend(18)
    assert u.dp_earned == 3
    assert u.cohesion == -3
    assert u.is_disorganized is True


def test_dp_is_immediate_and_accumulates() -> None:
    """6.22: DP reduce Cohesion at once and from segment to segment."""
    u = unit(base_cpa=8, cohesion=-1).spend(8).spend(3)
    assert u.cohesion == -4
    assert u.dp_earned == 3
    assert u.spend(1).cohesion == -5


def test_fractional_overage_earns_dp_when_a_full_point_is_reached() -> None:
    """6.21: fractional CP is retained, but DP are whole points."""
    u = unit(base_cpa=8).spend(Fraction(17, 2))
    assert u.spent == Fraction(17, 2)
    assert u.dp_earned == 0
    assert u.spend(Fraction(1, 2)).dp_earned == 1


def test_stage_end_resets_cp_without_carrying_it() -> None:
    """6.16: unspent CP does not carry into the next Operations Stage."""
    u = unit(base_cpa=8).spend(4).end_operations_stage()
    assert u.spent == 0
    assert u.spend(5).dp_earned == 0


def test_no_cp_stage_awards_five_rp_but_not_above_zero() -> None:
    """6.24.1: five RP, capped at zero for this method."""
    assert unit(cohesion=-7).end_operations_stage().cohesion == -2
    assert unit(cohesion=-2).end_operations_stage().cohesion == 0
    assert unit(cohesion=3).end_operations_stage().cohesion == 3


def test_training_stage_does_not_earn_the_no_cp_rp() -> None:
    """6.24.1/17.33: a Training unit is excluded from the no-CP award."""
    assert unit(cohesion=-4).end_operations_stage(training=True).cohesion == -4


def test_reorganization_is_applied_and_capped_at_ten() -> None:
    """6.23: RP improve Cohesion, but never above +10."""
    assert unit(cohesion=-3).award_reorganization(5).cohesion == 2
    assert unit(cohesion=5).award_reorganization(8).cohesion == MAX_COHESION
    assert unit(cohesion=0).award_reorganization(20).cohesion == 10


def test_thirty_percent_close_assault_loss_awards_three_dp() -> None:
    """6.21: 30%+ losses in one Close Assault earn three DP."""
    assert unit(cohesion=0).award_close_assault_losses(29).cohesion == 0
    losses = unit(cohesion=0).award_close_assault_losses(30)
    assert losses.cohesion == -3
    assert losses.disorganization_points == 3


def test_victorious_close_assault_awards_three_rp() -> None:
    """6.24.2: a defender vacating its hex earns the victor 3 RP."""
    assert unit(cohesion=-3).award_close_assault_victory().cohesion == 0


# ---------------------------------------------------------------------------
# 6.25-6.29: morale input, collapse, and formation cohesion
# ---------------------------------------------------------------------------

def test_positive_and_negative_cohesion_are_distinct_morale_inputs() -> None:
    """6.25: sign is preserved for the §17 morale table."""
    assert unit(cohesion=3).cohesion > 0
    assert unit(cohesion=-12).cohesion < 0
    assert battle_cohesion([unit(cohesion=-12)]) == -12


def test_collapsed_unit_cannot_act_or_defend_and_surrenders() -> None:
    """6.26: -26 or worse is collapsed; an adjacent enemy forces surrender."""
    assert unit(cohesion=COLLAPSE_AT + 1).can_act is True
    collapsed = unit(cohesion=COLLAPSE_AT)
    assert collapsed.can_act is False
    assert collapsed.is_collapsed is True
    assert collapsed.can_refuel is True
    assert collapsed.surrenders_if_adjacent(True) is True
    assert collapsed.surrenders_if_adjacent(False) is False


def test_largest_unit_cohesion_prevails() -> None:
    """6.27: the largest Stacking Point unit supplies the Cohesion."""
    units = [unit("battalion", stacking_points=1, cohesion=-4),
             unit("brigade", stacking_points=3, cohesion=2)]
    assert battle_cohesion(units) == 2


def test_tied_largest_units_average_and_round() -> None:
    """6.27: tied largest units average; -4, -1, +3 becomes -1."""
    units = [unit("a", stacking_points=3, cohesion=-4),
             unit("b", stacking_points=3, cohesion=-1),
             unit("c", stacking_points=3, cohesion=3)]
    assert battle_cohesion(units) == -1


def test_formation_cohesion_uses_the_largest_member() -> None:
    """6.28: a parent formation uses the same largest-unit rule."""
    units = [unit("parent-bde", stacking_points=4, cohesion=-2, parent_id="div"),
             unit("attached-bn", stacking_points=1, cohesion=3, parent_id="div"),
             unit("other", stacking_points=5, cohesion=9, parent_id="other")]
    assert formation_cohesion(units, parent_id="div") == -2


def test_individual_cohesion_is_kept_per_unit() -> None:
    """6.29: the formation rule does not overwrite individual values."""
    units = [unit("a", cohesion=-4), unit("b", cohesion=1)]
    assert cohesion_by_unit(units) == {"a": -4, "b": 1}
    assert units[0].cohesion == -4


# ---------------------------------------------------------------------------
# 6.3: fixed costs and dynamic rows
# ---------------------------------------------------------------------------

def test_fixed_cp_costs_match_the_rulebook_table() -> None:
    """6.3: the fixed cost summary is available as data."""
    assert cp_cost("break_contact") == 2
    assert cp_cost("phasing_barrage_or_assault") == 5
    assert cp_cost("nonphasing_defend_probe") == 2
    assert cp_cost("construct_supply_dump") == Fraction(3, 2)
    assert cp_cost("ready_airplanes") == 10
    assert "enter_non_minefield" not in CP_COSTS
    assert "enter_non_minefield" in DYNAMIC_CP_COSTS


def test_dynamic_cost_rows_are_not_guessed() -> None:
    """6.3: TEC/CPA-dependent rows require their missing inputs."""
    with pytest.raises(CapabilityError, match="TEC/CPA"):
        cp_cost("enter_enemy_minefield")
    with pytest.raises(CapabilityError, match="unknown"):
        cp_cost("teleport")


def test_cost_table_is_read_only() -> None:
    """6.3: the fixed table is not mutable game state."""
    with pytest.raises(TypeError):
        CP_COSTS["break_contact"] = Fraction(1)  # type: ignore[index]


# ---------------------------------------------------------------------------
# Input/reference checks
# ---------------------------------------------------------------------------

def test_invalid_capability_inputs_are_refused() -> None:
    with pytest.raises(CapabilityError, match="unit_id"):
        CapabilityState("", 10)
    with pytest.raises(CapabilityError, match="cohesion"):
        unit(cohesion=MAX_COHESION + 1)
    with pytest.raises(CapabilityError, match="negative"):
        unit(base_cpa=8).spend(-1)
    with pytest.raises(CapabilityError, match="purpose"):
        unit().cpa_for("magic")
    with pytest.raises(CapabilityError, match="formation"):
        formation_cpa([])
    with pytest.raises(CapabilityError, match="Close Assault"):
        battle_cohesion([])


def test_state_is_immutable_and_serialises_exactly() -> None:
    """6.13-6.16: a state update is a new record, not a mutation."""
    u = unit("u", 8).spend(Fraction(3, 2))
    with pytest.raises(Exception):
        u.cohesion = 0  # type: ignore[misc]
    obj = u.to_obj()
    assert obj["spent"] == "3/2"
    assert obj["remaining"] == "13/2"
    assert obj["cpa"] == 8
    assert obj["disorganization_points"] == 0
    assert obj["rule"] == "6.11-6.29"
