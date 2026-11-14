"""Organization, reorganization, reinforcements and replacements.

RULE: 19.11-19.98, 20.11-20.85

The Organization at Arrival Chart, the Formation Organization Chart, the
Maximum Attachment Chart, the Replacement Point Conversion Chart, the Axis
Replacement Pool and the Commonwealth Production Tables are all R-04/R-06/R-07
data.  None of them is embedded here: the caller supplies limits, compositions,
schedules and unit records, and this module implements only the rules that act
on them.

The distinction the section turns on is **assigned** versus **attached**
(19.11-19.14): assignment is organisational and permanent, attachment is
physical and permissive.  Costs, phase restrictions and the substitution rule
follow from that distinction, not from any chart.

Reinforcements (§20.1) and Replacements (§20.2-20.4) enter on caller-supplied
dates.  Withdrawal strength is a percentage (20.82), not a historical TOE.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Iterable, Mapping

RULE = "19.11-19.98, 20.11-20.85"

LEVELS = ("company", "battalion", "brigade", "division")

PHASES = ("reorganization", "movement", "reserve_designation")


class OrganizationError(ValueError):
    """An organization or reinforcement input is not a valid §19-§20 position."""


def _points(value: Any, *, name: str = "points") -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise OrganizationError(f"{name} must be an integer or Fraction")
    result = Fraction(value)
    if result < 0:
        raise OrganizationError(f"{name} must not be negative")
    return result


def _whole(value: Any, *, name: str = "value", minimum: int | None = None,
           maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise OrganizationError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise OrganizationError(f"{name} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise OrganizationError(f"{name} must be at most {maximum}")
    return value


def _bool(value: Any, *, name: str) -> bool:
    if not isinstance(value, bool):
        raise OrganizationError(f"{name} must be a bool")
    return value


def _counts(mapping: Mapping[str, Any] | None, *,
            name: str) -> dict[str, int]:
    if mapping is None:
        return {}
    result: dict[str, int] = {}
    for key, value in mapping.items():
        if not isinstance(key, str) or not key:
            raise OrganizationError(f"{name} keys must be non-empty strings")
        result[key] = _whole(value, name=f"{name}[{key!r}]", minimum=0)
    return result


# ---------------------------------------------------------------------------
# 19.1 Assigned versus attached
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FormationLimits:
    """The two §19.3/§19.5 chart rows for one Parent Formation.

    ``assigned`` is the Formation Organization Chart allowance by unit type;
    ``attached`` is the Maximum Attachment Chart allowance.  Both are R-04.
    """

    assigned: Mapping[str, int] = field(default_factory=dict)
    attached: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "assigned", _counts(self.assigned,
                                                     name="assigned"))
        object.__setattr__(self, "attached", _counts(self.attached,
                                                     name="attached"))


@dataclass(frozen=True)
class OrgUnit:
    """A unit's place in the organisational tree."""

    unit_id: str
    side: str
    unit_type: str
    level: str = "battalion"
    assigned_to: str | None = None
    attached_to: str | None = None
    independent: bool = False
    frozen_assignment: bool = False
    max_toe: Fraction = Fraction(0)
    toe: Fraction = Fraction(0)
    hex_id: str = ""

    def __post_init__(self) -> None:
        for name in ("unit_id", "side", "unit_type"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise OrganizationError(f"{name} must be a non-empty string")
        if self.level not in LEVELS:
            raise OrganizationError(f"unknown unit level: {self.level!r}")
        for name in ("assigned_to", "attached_to"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str)
                                      or not value.strip()):
                raise OrganizationError(
                    f"{name} must be a non-empty string or None")
        for name in ("independent", "frozen_assignment"):
            _bool(getattr(self, name), name=name)
        object.__setattr__(self, "max_toe", _points(self.max_toe, name="max_toe"))
        object.__setattr__(self, "toe", _points(self.toe, name="toe"))
        if self.toe > self.max_toe:
            raise OrganizationError("toe may not exceed max_toe")
        if not isinstance(self.hex_id, str):
            raise OrganizationError("hex_id must be a string")

    @property
    def attached(self) -> bool:
        return self.attached_to is not None

    @property
    def assigned(self) -> bool:
        return self.assigned_to is not None


def assignment_allowed(unit: OrgUnit, parent: OrgUnit, *,
                       limits: FormationLimits,
                       assigned_counts: Mapping[str, int]) -> tuple[bool, str]:
    """19.21-19.28: may *unit* be assigned to *parent*?"""
    if unit.assigned_to is not None:
        return False, "19.28"                                  # 19.28
    if unit.frozen_assignment:
        return False, "19.27"                                  # 19.27
    if not unit.independent:
        return False, "19.28"                                  # 19.28
    if parent.level not in ("brigade", "division"):
        return False, "19.3"
    counts = _counts(assigned_counts, name="assigned_counts")
    if counts.get(unit.unit_type, 0) >= limits.assigned.get(unit.unit_type, 0):
        return False, "19.21"                                  # 19.21
    return True, ""


def attachment_allowed(unit: OrgUnit, parent: OrgUnit, *,
                       limits: FormationLimits,
                       attached_counts: Mapping[str, int],
                       same_hex: bool) -> tuple[bool, str]:
    """19.41-19.46: may *unit* be attached to *parent*?

    An assigned unit attaches freely (19.4); any other unit needs a chart slot
    and the same hex (19.42, 19.46).
    """
    _bool(same_hex, name="same_hex")
    if unit.attached_to is not None:
        return False, "19.13"                                  # 19.13
    if not same_hex:
        return False, "19.42"                                  # 19.42
    if unit.assigned_to == parent.unit_id:
        return True, ""                                        # 19.4
    counts = _counts(attached_counts, name="attached_counts")
    if counts.get(unit.unit_type, 0) >= limits.attached.get(unit.unit_type, 0):
        return False, "19.5"
    return True, ""


def nested_attachment_allowed(*, parent_attached: bool,
                              substitution: bool = False) -> bool:
    """19.46: a unit attached to an attached parent is attached to the larger one."""
    _bool(parent_attached, name="parent_attached")
    _bool(substitution, name="substitution")
    return (not parent_attached) or substitution


@dataclass(frozen=True)
class CpCost:
    subsidiary: int
    parent: int
    phases: tuple[str, ...]
    rule: str

    def to_obj(self) -> dict[str, Any]:
        return {"subsidiary": self.subsidiary, "parent": self.parent,
                "phases": list(self.phases), "rule": self.rule}


def attachment_cp(unit: OrgUnit, parent: OrgUnit, *,
                  phase: str, same_hex: bool) -> CpCost:
    """19.41-19.42: one CP each when assigned, two each otherwise."""
    if phase not in PHASES:
        raise OrganizationError(f"unknown phase: {phase!r}")
    _bool(same_hex, name="same_hex")
    if not same_hex:
        raise OrganizationError("19.41/19.42: attachment needs the same hex")
    if unit.assigned_to == parent.unit_id:
        return CpCost(1, 1, PHASES, "19.41")                   # 19.41
    if phase != "reorganization":
        raise OrganizationError(
            "19.42: attaching a non-assigned unit is a Reorganization action")
    return CpCost(2, 2, ("reorganization",), "19.42")           # 19.42


def detachment_cp(unit: OrgUnit, *, phase: str) -> CpCost:
    """19.43-19.44: one CP each; attached-only units need a phase choice."""
    if phase not in PHASES:
        raise OrganizationError(f"unknown phase: {phase!r}")
    if unit.assigned_to is not None:
        return CpCost(1, 1, PHASES, "19.43")                   # 19.43
    if phase not in ("reorganization", "movement"):
        raise OrganizationError(
            "19.44: an attached-only unit detaches in the Reorganization or "
            "Movement Segment")
    return CpCost(1, 1, ("reorganization", "movement"), "19.44")


def detachment_stops_movement(*, phase: str) -> bool:
    """19.44: detaching during a Movement Segment stops both units' movement."""
    if phase not in PHASES:
        raise OrganizationError(f"unknown phase: {phase!r}")
    return phase == "movement"


def substitution_allowed(*, substitute_composition: Mapping[str, int],
                         missing_limits: Mapping[str, int]) -> bool:
    """19.45: a substitute may not exceed the missing unit's own limits."""
    composition = _counts(substitute_composition, name="substitute_composition")
    limits = _counts(missing_limits, name="missing_limits")
    return all(count <= limits.get(unit_type, 0)
               for unit_type, count in composition.items())


def reassignment_allowed(unit: OrgUnit, *, commonwealth_battalion: bool,
                         parent_exists: bool) -> tuple[bool, str]:
    """19.22-19.26: when an assigned unit may change parent."""
    _bool(commonwealth_battalion, name="commonwealth_battalion")
    _bool(parent_exists, name="parent_exists")
    if unit.frozen_assignment:
        return False, "19.27"
    if commonwealth_battalion:
        return True, "19.26"                                   # 19.26
    if not parent_exists:
        return True, "19.22"                                   # 19.22
    return False, "19.28"


# ---------------------------------------------------------------------------
# 19.6 Rebuilding and replacements
# ---------------------------------------------------------------------------

#: 19.64: which Replacement class rebuilds which unit kind.
REPLACEMENT_CLASSES = {
    "infantry": frozenset({"infantry", "hq", "engineer"}),
    "gun": frozenset({"artillery", "antitank", "aa"}),
    "tank": frozenset({"tank"}),
    "recce": frozenset({"recce", "armored_car"}),
}


def replacement_class_for(unit_type: str) -> frozenset[str]:
    """19.64: the Replacement classes that may rebuild a unit type."""
    for class_name, unit_types in REPLACEMENT_CLASSES.items():
        if unit_type in unit_types:
            return frozenset({class_name})
    if unit_type in ("heavy_weapons", "heavy_weapon"):
        return frozenset({"infantry", "gun"})                  # 19.64d
    return frozenset()


def rebuild_ceiling(unit: OrgUnit) -> Fraction:
    """19.61: rebuilding never exceeds the printed maximum TOE Strength."""
    return unit.max_toe


def rebuild_allowed(*, eliminated: bool, hq_cadre: bool = False) -> bool:
    """19.62: an eliminated unit may not be rebuilt; an HQ cadre may."""
    _bool(eliminated, name="eliminated")
    _bool(hq_cadre, name="hq_cadre")
    return (not eliminated) or hq_cadre


def hq_revive_allowed(*, assigned_alive: int, assigned_total: int,
                      infantry_replacement_points: int) -> bool:
    """19.63: an eliminated HQ returns only with 50% of its units and 2 RP."""
    alive = _whole(assigned_alive, name="assigned_alive", minimum=0)
    total = _whole(assigned_total, name="assigned_total", minimum=0)
    points = _whole(infantry_replacement_points,
                    name="infantry_replacement_points", minimum=0)
    if total == 0:
        return False
    return alive * 2 >= total and points >= 2


def rebuild_cp(replacement_points: Fraction | int) -> int:
    """19.68: one CP for every two Replacement TOE Points added."""
    points = _points(replacement_points, name="replacement_points")
    verify = _whole(math.ceil(points), name="replacement_points", minimum=0)
    if verify != points:
        raise OrganizationError("replacement_points must be a whole number")
    if verify == 0:
        return 0
    return max(1, math.ceil(verify / 2))


def rebuild_phase_allowed(phase: str) -> bool:
    """19.68, 20.49: rebuilding and absorbing happen in the Organization Phase."""
    if phase not in PHASES:
        raise OrganizationError(f"unknown phase: {phase!r}")
    return phase == "reorganization"


# ---------------------------------------------------------------------------
# 19.7 Axis Battle Groups
# ---------------------------------------------------------------------------

def german_battle_group_allowed(*, battalions: int, tanks: int,
                                infantry: int, companies: int) -> tuple[bool, str]:
    """19.72: four battalions, at most one tank and two infantry, two companies."""
    counts = {
        "battalions": _whole(battalions, name="battalions", minimum=0),
        "tanks": _whole(tanks, name="tanks", minimum=0),
        "infantry": _whole(infantry, name="infantry", minimum=0),
        "companies": _whole(companies, name="companies", minimum=0),
    }
    if counts["battalions"] > 4 or counts["tanks"] > 1:
        return False, "19.72"
    if counts["infantry"] > 2 or counts["companies"] > 2:
        return False, "19.72"
    return True, ""


def italian_battle_group_allowed(*, battalions: int, infantry: int,
                                 armor: int, companies: int,
                                 existing_groups: int) -> tuple[bool, str]:
    """19.73: three battalions, two infantry, one armor, one company, max two groups."""
    counts = {
        "battalions": _whole(battalions, name="battalions", minimum=0),
        "infantry": _whole(infantry, name="infantry", minimum=0),
        "armor": _whole(armor, name="armor", minimum=0),
        "companies": _whole(companies, name="companies", minimum=0),
        "existing": _whole(existing_groups, name="existing_groups", minimum=0),
    }
    if counts["existing"] >= 2:
        return False, "19.73"
    if counts["battalions"] > 3 or counts["infantry"] > 2:
        return False, "19.73"
    if counts["armor"] > 1 or counts["companies"] > 1:
        return False, "19.73"
    return True, ""


# ---------------------------------------------------------------------------
# 19.8-19.9 Anti-tank augmentation
# ---------------------------------------------------------------------------

#: 19.81: the most AT TOE a brigade-level infantry HQ may carry.
HQ_AT_LIMIT = Fraction(6)

#: 19.82: all AT units must be at this percentage of maximum before augmenting.
AT_READINESS_PERCENT = 67

#: 19.83: the smallest first AT assignment.
HQ_AT_INITIAL_MINIMUM = Fraction(3)

#: 19.91: the first Game-Turn Commonwealth infantry may be augmented.
CW_INFANTRY_AT_FIRST_TURN = 75


def hq_at_augmentation_allowed(*, hq_level: str, hq_symbol: str,
                               current_at_toe: Fraction | int,
                               added_toe: Fraction | int,
                               all_at_ready: bool,
                               existing_gun_type: str = "",
                               new_gun_type: str = "",
                               captured_gun: bool = False) -> tuple[bool, str]:
    """19.81-19.86: augment a brigade-level infantry-symbol HQ with AT guns."""
    if hq_level != "brigade" or hq_symbol != "infantry":
        return False, "19.81"
    current = _points(current_at_toe, name="current_at_toe")
    added = _points(added_toe, name="added_toe")
    if current + added > HQ_AT_LIMIT:
        return False, "19.81"
    if not _bool(all_at_ready, name="all_at_ready"):
        return False, "19.82"
    if captured_gun:
        return False, "19.86"
    if current == 0 and added < HQ_AT_INITIAL_MINIMUM:
        return False, "19.83"
    if existing_gun_type and new_gun_type and existing_gun_type != new_gun_type:
        return False, "19.86"
    return True, ""


def augmented_hq_stacking_points() -> Fraction:
    """19.87: an augmented HQ keeps a Stacking Point value of zero."""
    return Fraction(0)


def augmented_hq_cpa(at_toe: Fraction | int) -> Fraction:
    """19.85: the HQ's CPA becomes that of its Anti-Tank Points."""
    return _points(at_toe, name="at_toe")


def cw_infantry_at_allowed(*, game_turn: int, cpa: int,
                           offensive_rating: Fraction | int,
                           defensive_rating: Fraction | int,
                           motorized: bool, current_at_toe: Fraction | int,
                           parent_at_max: bool) -> tuple[bool, str]:
    """19.91-19.96: augment a Commonwealth infantry battalion with AT guns."""
    turn = _whole(game_turn, name="game_turn", minimum=0)
    if turn < CW_INFANTRY_AT_FIRST_TURN:
        return False, "19.91"
    if _whole(cpa, name="cpa", minimum=0) != 10:
        return False, "19.92"
    offensive = _points(offensive_rating, name="offensive_rating")
    defensive = _points(defensive_rating, name="defensive_rating")
    if (offensive, defensive) not in ((Fraction(1), Fraction(2)),
                                      (Fraction(2), Fraction(2))):
        return False, "19.92"
    limit = Fraction(2) if _bool(motorized, name="motorized") else Fraction(1)
    current = _points(current_at_toe, name="current_at_toe")
    if current >= limit:
        return False, "19.94"
    if not _bool(parent_at_max, name="parent_at_max"):
        return False, "19.96"
    return True, ""


def cw_infantry_at_cpa(unit_cpa: int) -> int:
    """19.97: absorbed AT Points take the infantry unit's CPA."""
    return _whole(unit_cpa, name="unit_cpa", minimum=0)


def cw_infantry_at_affects_shell() -> bool:
    """19.98: AT Points do not affect shell determinations."""
    return False


# ---------------------------------------------------------------------------
# 20.1 Reinforcements
# ---------------------------------------------------------------------------

#: 20.13-20.15: the named arrival ports.
COMMONWEALTH_PORTS = ("cairo", "alexandria")
AXIS_PORTS = ("tripoli", "benghazi")

#: 20.15: Benghazi diversion limits.
BENGHAZI_TRUCK_POINTS = 10
BENGHAZI_MIN_PORT_LEVEL = 3

#: 20.21: how far ahead each side plans Replacement arrivals.
AXIS_PLANNING_TURNS = 2
CW_PLANNING_TURNS = 4


def reinforcement_entry_allowed(
    *,
    side: str,
    entry: str,
    alexandria_permitted: bool = False,
    west_of_mersa_matruh: bool = True,
    port_level: int = 99,
    stacking_ok: bool = True,
    battalion_equivalents: int = 1,
    company_equivalents: int = 0,
    truck_points: int = 0,
) -> tuple[bool, str]:
    """20.12-20.15: where a Reinforcement may enter.

    Commonwealth units arrive at Cairo, or Alexandria for the named units
    (20.14).  Axis units arrive at Tripoli, or Benghazi only under the four
    20.15 conditions.
    """
    if side == "commonwealth":
        if entry == "cairo":
            return True, ""
        if entry == "alexandria" and _bool(alexandria_permitted,
                                           name="alexandria_permitted"):
            return True, "20.14"
        return False, "20.14"
    if side != "axis":
        raise OrganizationError(f"unknown side: {side!r}")
    if entry == "tripoli":
        return True, ""
    if entry != "benghazi":
        return False, "20.15"
    if _bool(west_of_mersa_matruh, name="west_of_mersa_matruh"):
        return False, "20.15"
    level = _whole(port_level, name="port_level", minimum=0)
    if level < BENGHAZI_MIN_PORT_LEVEL:
        return False, "20.15"
    if not _bool(stacking_ok, name="stacking_ok"):
        return False, "20.15"
    battalions = _whole(battalion_equivalents,
                        name="battalion_equivalents", minimum=0)
    companies = _whole(company_equivalents, name="company_equivalents",
                       minimum=0)
    trucks = _whole(truck_points, name="truck_points", minimum=0)
    if battalions > 1 or companies > 2 or trucks > BENGHAZI_TRUCK_POINTS:
        return False, "20.15"
    return True, "20.15"


def reinforcement_arrival_cp() -> int:
    """20.12: debarking and the first hex cost no Capability Point."""
    return 0


def replacement_planned_in_time(*, side: str, planned_turn: int,
                                arrival_turn: int) -> bool:
    """20.21: Axis plan two Game-Turns ahead, Commonwealth four."""
    planned = _whole(planned_turn, name="planned_turn", minimum=0)
    arrival = _whole(arrival_turn, name="arrival_turn", minimum=0)
    lead = AXIS_PLANNING_TURNS if side == "axis" else CW_PLANNING_TURNS
    if side not in ("axis", "commonwealth"):
        raise OrganizationError(f"unknown side: {side!r}")
    return arrival - planned >= lead


def even_distribution(points: int, *, stages: int) -> tuple[int, ...]:
    """20.74: divide a Game-Turn's Points as evenly as possible over its Stages."""
    total = _whole(points, name="points", minimum=0)
    count = _whole(stages, name="stages", minimum=1)
    each, remainder = divmod(total, count)
    return tuple(each + (1 if index < remainder else 0)
                 for index in range(count))


# ---------------------------------------------------------------------------
# 20.2-20.4 Replacement Points
# ---------------------------------------------------------------------------

#: 20.43: Operations Stages of Training by Replacement class.
REPLACEMENT_TRAINING_STAGES = {"gun": 1, "infantry": 3, "tank": 6,
                               "recce": 6, "armored_car": 6}

#: 20.42: an unabsorbed Replacement Point has this Basic Morale.
REPLACEMENT_MORALE = -3

#: 20.42d: exceeding the CPA collapses the points to this Cohesion.
REPLACEMENT_COLLAPSE = -26


def replacement_training_stages(replacement_class: str) -> int:
    """20.43: Gun one, Infantry three, Tank/AC/Recce six."""
    try:
        return REPLACEMENT_TRAINING_STAGES[replacement_class]
    except KeyError:
        raise OrganizationError(
            f"unknown Replacement class: {replacement_class!r}") from None


def replacement_training_location_allowed(side: str, location: str, *,
                                          major_city: bool = False) -> bool:
    """20.43: Axis at Tripoli or a major city; Commonwealth in the 17.32 areas."""
    from cna.rules.sec16_morale import TRAINING_AREAS

    if not isinstance(location, str) or not location:
        raise OrganizationError("location must be a non-empty string")
    if side == "axis":
        return location == "tripoli" or major_city
    if side == "commonwealth":
        return location in TRAINING_AREAS
    raise OrganizationError(f"unknown side: {side!r}")


def replacement_zoc_allowed(*, friendly_occupies: bool) -> bool:
    """20.42a: a Replacement Point may not enter an Enemy ZOC unless occupied."""
    return _bool(friendly_occupies, name="friendly_occupies")


def replacement_combat_role_allowed(role: str) -> bool:
    """20.42b: Replacements only defend against Close Assault."""
    return role == "defend_close_assault"


def replacement_cpa_state(*, spent: int, cpa: int) -> int | None:
    """20.42d: exceeding the CPA collapses the points to Cohesion -26."""
    used = _whole(spent, name="spent", minimum=0)
    allowance = _whole(cpa, name="cpa", minimum=0)
    return REPLACEMENT_COLLAPSE if used > allowance else None


def replacement_capacity(unit: OrgUnit) -> Fraction:
    """20.65: a unit may absorb only what fits under its maximum TOE."""
    return unit.max_toe - unit.toe


def replacement_absorption_allowed(phase: str) -> bool:
    """20.49: Replacements are absorbed in the Reorganization Segment."""
    return rebuild_phase_allowed(phase)


# ---------------------------------------------------------------------------
# 20.5 Upgrading Recce and Commonwealth infantry
# ---------------------------------------------------------------------------

#: 20.55: the earliest Upgrade month.
RECCE_UPGRADE_FIRST_MONTH = (1939, 1)

#: 20.54: the upgraded Point's ratings.
RECCE_UPGRADE_ANTI_ARMOR = 1
RECCE_UPGRADE_OFFENSIVE = 3

#: 20.77: the earliest Commonwealth infantry Upgrade month.
CW_INFANTRY_UPGRADE_FIRST_MONTH = (1942, 7)


def recce_upgrade_allowed(*, month: tuple[int, int], anti_armor_rating: Fraction,
                          excluded: bool = False) -> bool:
    """20.51-20.55: add one tank TOE Point to a zero-AA Recce/Armored Car unit."""
    if not isinstance(month, tuple) or len(month) != 2:
        raise OrganizationError("month must be a (year, month) tuple")
    year = _whole(month[0], name="year", minimum=1900)
    number = _whole(month[1], name="month", minimum=1, maximum=12)
    _bool(excluded, name="excluded")
    if (year, number) < RECCE_UPGRADE_FIRST_MONTH:
        return False
    if _points(anti_armor_rating, name="anti_armor_rating") != 0:
        return False
    return not excluded                                              # 20.51


def recce_upgrade_effect() -> tuple[int, int]:
    """20.54: Anti-Armor 1 and Offensive Close Assault 3 after upgrading."""
    return RECCE_UPGRADE_ANTI_ARMOR, RECCE_UPGRADE_OFFENSIVE


def cw_infantry_upgrade_allowed(*, month: tuple[int, int],
                                offensive_rating: Fraction | int,
                                defensive_rating: Fraction | int) -> bool:
    """20.77: 1/2 infantry become 2/2 from July 1942."""
    if not isinstance(month, tuple) or len(month) != 2:
        raise OrganizationError("month must be a (year, month) tuple")
    year = _whole(month[0], name="year", minimum=1900)
    number = _whole(month[1], name="month", minimum=1, maximum=12)
    if (year, number) < CW_INFANTRY_UPGRADE_FIRST_MONTH:
        return False
    return (_points(offensive_rating, name="offensive_rating") == 1
            and _points(defensive_rating, name="defensive_rating") == 2)


# ---------------------------------------------------------------------------
# 20.8-20.9 Withdrawals
# ---------------------------------------------------------------------------

#: 20.82: the minimum share of maximum TOE a withdrawing unit needs.
WITHDRAWAL_TOE_PERCENT = 75

#: 20.83: the ports a withdrawing unit must reach.
WITHDRAWAL_PORTS = ("cairo", "alexandria")


def withdrawal_strength_ok(unit: OrgUnit, *,
                           required_percent: int = WITHDRAWAL_TOE_PERCENT) -> bool:
    """20.82, 20.85: at least 75% of maximum TOE Strength."""
    percent = _whole(required_percent, name="required_percent", minimum=0,
                     maximum=100)
    if unit.max_toe == 0:
        return False
    return unit.toe * 100 >= unit.max_toe * percent


def withdrawal_choice(units: Iterable[OrgUnit]) -> OrgUnit | None:
    """20.82: the strongest eligible unit if none is at 75%."""
    members = tuple(units)
    if not members:
        return None
    eligible = [unit for unit in members if withdrawal_strength_ok(unit)]
    if eligible:
        return max(eligible, key=lambda unit: unit.toe)
    return max(members, key=lambda unit: unit.toe)


def withdrawal_status(*, at_port: bool, strength_ok: bool) -> str:
    """20.83: a unit not at a port, or too weak, is eliminated."""
    _bool(at_port, name="at_port")
    _bool(strength_ok, name="strength_ok")
    if at_port and strength_ok:
        return "withdrawn"
    return "eliminated"
