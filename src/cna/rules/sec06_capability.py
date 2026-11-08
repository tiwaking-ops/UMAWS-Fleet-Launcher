"""Capability Points, cohesion, and disorganization.

RULE: 6.11-6.29

CNA does not give a unit a movement allowance.  It gives it a **Capability
Point Allowance (CPA)** for an Operations Stage.  Every function is paid for
from that allowance (6.12); spending beyond it immediately earns
Disorganization Points (6.21), which reduce Cohesion (6.22).  Cohesion is a
per-unit value, even when a parent formation or a multi-unit assault uses a
largest-unit rule for a particular calculation (6.27-6.29).

The model here is deliberately small and immutable.  A unit's CPA, Cohesion,
parent and stacking values are caller-supplied OA/TOE data; this module does
not invent historical ratings.  CP may be fractional because section 6.3
contains half- and third-point costs.  DP are whole points: a fractional CP
is retained exactly, and DP accrue as each full point of over-allowance is
crossed.

Two R-04 dependencies are explicit rather than guessed:

* the Terrain Effects Chart is required for the "TEC" entries in 6.3;
* the Morale Modification Table (6.25, 17.22/17.4) is required for the
  modifier itself.  :func:`battle_cohesion` supplies the Cohesion value that
  the table consumes, but no modifier is invented here.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
from types import MappingProxyType
from typing import Any, Iterable, Mapping

__all__ = [
    "RULE",
    "MAX_COHESION",
    "COLLAPSE_AT",
    "CapabilityError",
    "CapabilityState",
    "CP_COSTS",
    "DYNAMIC_CP_COSTS",
    "cp_cost",
    "formation_cpa",
    "battle_cohesion",
    "formation_cohesion",
    "cohesion_by_unit",
]

RULE = "6.11-6.29"
MAX_COHESION = 10
COLLAPSE_AT = -26


class CapabilityError(ValueError):
    """A capability, cohesion, or cost input is not valid."""


def _points(value: Any, *, name: str = "points") -> Fraction:
    """Return *value* as a non-negative exact Fraction."""
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise CapabilityError(f"{name} must be an integer or Fraction")
    result = Fraction(value)
    if result < 0:
        raise CapabilityError(f"{name} must not be negative")
    return result


def _count(value: Any, *, name: str = "points") -> int:
    """Return a non-negative whole-point count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise CapabilityError(f"{name} must be an integer")
    if value < 0:
        raise CapabilityError(f"{name} must not be negative")
    return value


def _whole(value: Fraction) -> int:
    """The number of complete points in a non-negative Fraction."""
    return value.numerator // value.denominator


def _json_number(value: Fraction) -> int | str:
    """Serialise an exact Fraction without losing precision."""
    if value.denominator == 1:
        return value.numerator
    return f"{value.numerator}/{value.denominator}"


def _round_nearest(value: Fraction) -> int:
    """Round to the nearest whole number, with exact halves away from zero.

    Rule 6.27 gives an example whose average is -2/3 and is rounded to -1.
    The rules do not specify a tie convention; the deterministic convention
    here keeps a negative and positive half equidistant from zero.
    """
    if value < 0:
        return -_round_nearest(-value)
    whole = value.numerator // value.denominator
    remainder = value - whole
    return whole + (1 if remainder >= Fraction(1, 2) else 0)


@dataclass(frozen=True)
class CapabilityState:
    """One unit's CPA and cohesion record.

    ``base_cpa`` is the OA-sheet allowance.  ``transport_cpa`` is set only
    while an infantry unit is motorized (6.17); the effective :attr:`cpa`
    then follows the carrying truck.  ``stacking_points`` is used for the
    largest-unit rule in 6.27/6.28 and is not inferred from the unit id.
    """

    unit_id: str
    base_cpa: int
    cohesion: int = 0
    disorganization_points: int = 0
    spent: Fraction = Fraction(0)
    stacking_points: int = 1
    transport_cpa: int | None = None
    is_gun: bool = False
    parent_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.unit_id, str) or not self.unit_id.strip():
            raise CapabilityError("unit_id must be a non-empty string")
        for name, value in (("base_cpa", self.base_cpa),
                            ("cohesion", self.cohesion),
                            ("disorganization_points",
                             self.disorganization_points),
                            ("stacking_points", self.stacking_points)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise CapabilityError(f"{name} must be an integer")
        if self.base_cpa < 0:
            raise CapabilityError("base_cpa must not be negative")
        if self.disorganization_points < 0:
            raise CapabilityError("disorganization_points must not be negative")
        if self.stacking_points < 0:
            raise CapabilityError("stacking_points must not be negative")
        if self.cohesion > MAX_COHESION:
            raise CapabilityError(
                f"cohesion may not exceed {MAX_COHESION} (6.23)")
        if self.transport_cpa is not None:
            if isinstance(self.transport_cpa, bool) or not isinstance(
                    self.transport_cpa, int):
                raise CapabilityError("transport_cpa must be an integer")
            if self.transport_cpa < 0:
                raise CapabilityError("transport_cpa must not be negative")
        if not isinstance(self.is_gun, bool):
            raise CapabilityError("is_gun must be a bool")
        if self.parent_id is not None and (
                not isinstance(self.parent_id, str) or not self.parent_id.strip()):
            raise CapabilityError("parent_id must be a non-empty string or None")
        object.__setattr__(self, "spent", _points(self.spent, name="spent"))

    # -- allowance -----------------------------------------------------
    @property
    def cpa(self) -> int:
        """The effective allowance, including a carrying truck's CPA."""
        return self.transport_cpa if self.transport_cpa is not None else self.base_cpa

    def cpa_for(self, purpose: str = "general") -> int:
        """Allowance for *purpose* (6.11).

        A Gun unit with a printed CPA of zero is treated as CPA 10 for every
        purpose other than movement.
        """
        if purpose not in ("general", "movement"):
            raise CapabilityError("purpose must be 'general' or 'movement'")
        if self.is_gun and self.base_cpa == 0 and purpose != "movement":
            return 10
        return self.cpa

    @property
    def remaining(self) -> Fraction:
        """Unspent CP; negative once the allowance has been exceeded."""
        return Fraction(self.cpa) - self.spent

    @property
    def over_allowance(self) -> Fraction:
        """CP spent beyond the allowance this Operations Stage."""
        return max(Fraction(0), self.spent - self.cpa)

    @property
    def dp_earned(self) -> int:
        """Complete Disorganization Points earned by over-allowance."""
        return _whole(self.over_allowance)

    # -- spending ------------------------------------------------------
    def spend(self, points: int | Fraction, *,
              purpose: str = "general") -> "CapabilityState":
        """Spend CP and apply any newly crossed DP immediately (6.21-6.22).

        The returned state is new; the original is untouched.  A fractional
        cost is retained exactly, but a DP is charged only for each full CP
        of over-allowance.
        """
        amount = _points(points)
        allowance = self.cpa_for(purpose)
        before = max(Fraction(0), self.spent - allowance)
        after_spent = self.spent + amount
        after = max(Fraction(0), after_spent - allowance)
        new_dp = _whole(after) - _whole(before)
        return replace(self, spent=after_spent,
                       cohesion=self.cohesion - new_dp,
                       disorganization_points=self.disorganization_points + new_dp)

    # -- cohesion ------------------------------------------------------
    def award_disorganization(self, points: int) -> "CapabilityState":
        """Apply DP to Cohesion immediately (6.21-6.22)."""
        amount = _count(points, name="disorganization points")
        return replace(self, cohesion=self.cohesion - amount,
                       disorganization_points=self.disorganization_points + amount)

    def award_reorganization(self, points: int) -> "CapabilityState":
        """Apply RP, capped at +10 (6.23-6.24)."""
        amount = _count(points, name="reorganization points")
        return replace(self, cohesion=min(MAX_COHESION,
                                           self.cohesion + amount))

    def award_close_assault_losses(self, loss_percent: int) -> "CapabilityState":
        """Award the 3 DP for 30%+ losses in one Close Assault (6.21)."""
        if isinstance(loss_percent, bool) or not isinstance(loss_percent, int):
            raise CapabilityError("loss_percent must be an integer")
        if not 0 <= loss_percent <= 100:
            raise CapabilityError("loss_percent must be in 0..100")
        if loss_percent >= 30:
            return self.award_disorganization(3)
        return self

    def award_close_assault_victory(self) -> "CapabilityState":
        """Award the 3 RP for a defender vacating its hex (6.24.2)."""
        return self.award_reorganization(3)

    def end_operations_stage(self, *, training: bool = False) -> "CapabilityState":
        """Close the stage: reset CP and apply the no-CP RP.

        CP does not carry over (6.16).  A unit that spent no CP earns 5 RP,
        but this method only raises a negative Cohesion toward zero, never
        above it (6.24.1).  A Training unit is excluded (6.24.1, 17.33).
        """
        if not isinstance(training, bool):
            raise CapabilityError("training must be a bool")
        cohesion = self.cohesion
        if self.spent == 0 and not training and cohesion < 0:
            cohesion = min(0, cohesion + 5)
        return replace(self, cohesion=cohesion, spent=Fraction(0))

    # -- disorganization and motorization ------------------------------
    @property
    def is_disorganized(self) -> bool:
        """Whether Cohesion is negative."""
        return self.cohesion < 0

    @property
    def is_collapsed(self) -> bool:
        """Whether Cohesion is -26 or worse (6.26)."""
        return self.cohesion <= COLLAPSE_AT

    @property
    def can_act(self) -> bool:
        """A collapsed unit may not move, attack, or defend (6.26)."""
        return not self.is_collapsed

    @property
    def can_refuel(self) -> bool:
        """Collapsed units may still refuel (6.26)."""
        return True

    def surrenders_if_adjacent(self, enemy_combat_unit: bool = True) -> bool:
        """A collapsed unit surrenders when an enemy combat unit is adjacent."""
        if not isinstance(enemy_combat_unit, bool):
            raise CapabilityError("enemy_combat_unit must be a bool")
        return self.is_collapsed and enemy_combat_unit

    def motorize(self, truck_cpa: int) -> "CapabilityState":
        """Give an infantry unit a carrying truck's CPA (6.17)."""
        if self.base_cpa > 10:
            raise CapabilityError(
                "only infantry with a base CPA of 10 or less may motorize (6.17)")
        if isinstance(truck_cpa, bool) or not isinstance(truck_cpa, int):
            raise CapabilityError("truck_cpa must be an integer")
        if truck_cpa < 0:
            raise CapabilityError("truck_cpa must not be negative")
        return replace(self, transport_cpa=truck_cpa)

    def demotorize(self) -> "CapabilityState":
        """Return to the printed base CPA."""
        return replace(self, transport_cpa=None)

    # -- serialisation -------------------------------------------------
    def to_obj(self) -> dict[str, Any]:
        """A JSON-safe record, including the current derived values."""
        return {
            "unit_id": self.unit_id,
            "parent_id": self.parent_id,
            "base_cpa": self.base_cpa,
            "cpa": self.cpa,
            "spent": _json_number(self.spent),
            "remaining": _json_number(self.remaining),
            "cohesion": self.cohesion,
            "disorganization_points": self.disorganization_points,
            "over_allowance_dp": self.dp_earned,
            "stacking_points": self.stacking_points,
            "transport_cpa": self.transport_cpa,
            "motorized": self.transport_cpa is not None,
            "is_gun": self.is_gun,
            "is_disorganized": self.is_disorganized,
            "is_collapsed": self.is_collapsed,
            "can_act": self.can_act,
            "can_refuel": self.can_refuel,
            "rule": RULE,
        }


#: Fixed entries from the 6.3 Capability Point Cost Summary.  The dynamic
#: entries are listed separately so a caller cannot mistake a missing TEC or
#: CPA input for a fixed zero.
CP_COSTS: Mapping[str, Fraction] = MappingProxyType({
    "detach": Fraction(1),
    "attach_assigned": Fraction(1),
    "attach_unassigned": Fraction(2),
    "absorb_two_replacement_points": Fraction(1),
    "break_contact": Fraction(2),
    "disengage": Fraction(4),
    "reserve": Fraction(0),
    "phasing_barrage_or_assault": Fraction(5),
    "phasing_undergo_barrage": Fraction(3),
    "phasing_probe": Fraction(2),
    "nonphasing_barrage_or_defend": Fraction(3),
    "nonphasing_defend_probe": Fraction(2),
    "patrol": Fraction(0),
    "desert_raider_raid": Fraction(5),
    "poison_water": Fraction(1),
    "sweeten_water": Fraction(5),
    "draw_water_organization": Fraction(0),
    "draw_water_other": Fraction(1),
    "load_unload_organization": Fraction(0),
    "load_unload_other": Fraction(2),
    "construct_supply_dump": Fraction(3, 2),
    "construction_or_demolition_other": Fraction(0),
    "rail_or_interport_transport": Fraction(0),
    "air_transport": Fraction(0),
    "paradrop_paratroops": Fraction(0),
    "paradrop_commandos": Fraction(5),
    "ready_airplanes": Fraction(10),
})

#: 6.3 rows that require a TEC, the unit's CPA, or a choice between two
#: cases.  They are named, but not assigned invented numbers.
DYNAMIC_CP_COSTS = frozenset({
    "enter_non_minefield",
    "enter_friendly_minefield",
    "enter_enemy_minefield",
    "blow_supply_dump",
    "commando_amphibious_landing",
})


def cp_cost(action: str) -> Fraction:
    """Return a fixed 6.3 cost, or explain why the row is dynamic."""
    try:
        return CP_COSTS[action]
    except KeyError:
        if action in DYNAMIC_CP_COSTS:
            raise CapabilityError(
                f"{action!r} depends on TEC/CPA or a rule choice and is not a "
                "fixed 6.3 value") from None
        raise CapabilityError(f"unknown Capability Point action: {action!r}") from None


def formation_cpa(units: Iterable[CapabilityState], *,
                  purpose: str = "general") -> int:
    """The lowest CPA in a parent formation (6.15)."""
    members = tuple(units)
    if not members:
        raise CapabilityError("a formation must contain at least one unit")
    return min(unit.cpa_for(purpose) for unit in members)


def battle_cohesion(units: Iterable[CapabilityState]) -> int:
    """The Cohesion used by a multi-unit Close Assault (6.27).

    The largest unit by Stacking Points prevails.  If several units tie for
    largest, their Cohesion values are averaged and rounded to the nearest
    whole number.  Individual records are not changed.
    """
    members = tuple(units)
    if not members:
        raise CapabilityError("a Close Assault must contain at least one unit")
    largest = max(unit.stacking_points for unit in members)
    selected = [unit for unit in members if unit.stacking_points == largest]
    if len(selected) == 1:
        return selected[0].cohesion
    return _round_nearest(Fraction(sum(unit.cohesion for unit in selected),
                                   len(selected)))


def formation_cohesion(units: Iterable[CapabilityState], *,
                       parent_id: str | None = None) -> int:
    """The largest-unit Cohesion within a parent formation (6.28)."""
    members = tuple(unit for unit in units
                    if parent_id is None or unit.parent_id == parent_id)
    if not members:
        raise CapabilityError("no units match the requested parent formation")
    return battle_cohesion(members)


def cohesion_by_unit(units: Iterable[CapabilityState]) -> dict[str, int]:
    """Keep every unit's Cohesion individually (6.29)."""
    result: dict[str, int] = {}
    for unit in units:
        if unit.unit_id in result:
            raise CapabilityError(f"duplicate unit id: {unit.unit_id!r}")
        result[unit.unit_id] = unit.cohesion
    return result
