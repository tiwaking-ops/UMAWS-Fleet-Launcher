"""Stacking.

RULE: 9.0, 9.11-9.16, 9.21-9.29, 9.31-9.35

Stacking Points are printed on the counter and are caller-supplied OA/TOE
data (9.11, 9.13).  The Terrain Effects Chart that sets a hex's limit is
R-04 and is also caller-supplied (9.14, 8.37); this module implements the
rules that decide *what counts* against that limit and *when* the limit is
checked.  It never invents a stacking value or a terrain limit.

Three facts drive the model:

* what a unit is worth in a hex is not always its printed value (9.12 HQ,
  9.15 markers and aircraft, 9.16 garrison/AA, 9.24 artillery, 9.29 trucks);
* stacking is checked when movement stops, not as a unit passes through
  (9.31-9.32), except for the five-point Road/Track passage limit (9.33)
  and involuntary retreats (9.35);
* a shell is a smaller formation than its printed level (9.26-9.28).

Road and Track road-space stacking (9.33) is a *passage* check; call it
while building a move.  End-of-movement checks deliberately ignore it, so a
unit may move through a stack it could not stop in (9.32).
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Iterable, Mapping

RULE = "9.11-9.35"

#: The Road/Track stacking limit (9.33).
ROAD_TRACK_LIMIT = Fraction(5)

#: The maximum number of "?" companies/batteries in one hex (9.25).
SMALL_UNIT_LIMIT = 5

KINDS = frozenset({
    "combat", "hq", "artillery", "antitank", "aa", "garrison", "truck",
    "truck_convoy", "informational", "air", "ground_support", "warship",
    "small", "engineer", "noncombat",
})

LEVELS = ("division", "brigade", "battalion", "artillery", "company")


class StackingError(ValueError):
    """A stacking input is not a valid §9 position."""


def _points(value: Any, *, name: str = "stacking_points") -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise StackingError(f"{name} must be an integer or Fraction")
    result = Fraction(value)
    if result < 0:
        raise StackingError(f"{name} must not be negative")
    return result


@dataclass(frozen=True)
class HexContext:
    """The caller-supplied facts about one hex.

    ``limit`` is the Terrain Effects Chart stacking limit (9.14/8.37).
    ``None`` means the chart is unavailable (R-04): the caller still gets
    the point total, but no 9.31 terrain-limit violation is invented.
    """

    hex_id: str = ""
    limit: Fraction | None = None
    terrain: str = ""
    major_city: bool = False
    airfield: bool = False
    landing_strip: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.hex_id, str):
            raise StackingError("hex_id must be a string")
        if self.limit is not None:
            object.__setattr__(self, "limit",
                               _points(self.limit, name="limit"))
        for name in ("major_city", "airfield", "landing_strip"):
            if not isinstance(getattr(self, name), bool):
                raise StackingError(f"{name} must be a bool")


@dataclass(frozen=True)
class StackingUnit:
    """One unit or counter, with the OA/TOE facts §9 needs.

    ``kind`` selects the special cases.  ``level`` is the formation level
    used by Unit Differentiation (9.22); it is caller-supplied because the
    §9.4 sheet that maps Stacking Points to levels is absent (R-04).
    """

    unit_id: str
    side: str
    stacking_points: Fraction = Fraction(1)
    kind: str = "combat"
    parent_id: str | None = None
    attached_to_parent: bool = False
    attached_combat_units: int = 0
    motorized: bool = False
    assigned_city: str | None = None
    artillery_hq: bool = False
    zero_plus_cpa: bool = False
    level: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.unit_id, str) or not self.unit_id.strip():
            raise StackingError("unit_id must be a non-empty string")
        if not isinstance(self.side, str) or not self.side.strip():
            raise StackingError("side must be a non-empty string")
        object.__setattr__(self, "stacking_points", _points(self.stacking_points))
        if self.kind not in KINDS:
            raise StackingError(f"unknown unit kind: {self.kind!r}")
        if self.parent_id is not None and (
                not isinstance(self.parent_id, str) or not self.parent_id.strip()):
            raise StackingError("parent_id must be a non-empty string or None")
        if (isinstance(self.attached_combat_units, bool)
                or not isinstance(self.attached_combat_units, int)
                or self.attached_combat_units < 0):
            raise StackingError("attached_combat_units must be a non-negative integer")
        if not isinstance(self.attached_to_parent, bool):
            raise StackingError("attached_to_parent must be a bool")
        if not isinstance(self.motorized, bool):
            raise StackingError("motorized must be a bool")
        if self.assigned_city is not None and (
                not isinstance(self.assigned_city, str)
                or not self.assigned_city.strip()):
            raise StackingError("assigned_city must be a non-empty string or None")
        for name in ("artillery_hq", "zero_plus_cpa"):
            if not isinstance(getattr(self, name), bool):
                raise StackingError(f"{name} must be a bool")
        if self.level and self.level not in LEVELS:
            raise StackingError(f"unknown formation level: {self.level!r}")


def aa_free_allowance(context: HexContext) -> int:
    """AA/Flak units that stack free in a hex (9.16).

    One with a landing strip and three with an airfield; a Major City makes
    every AA unit free instead, which :func:`effective_points` handles.
    """
    if context.airfield:
        return 3
    if context.landing_strip:
        return 1
    return 0


def artillery_stacking_points(unit: StackingUnit) -> Fraction:
    """Artillery is one Stacking Point (9.24) unless it is an artillery HQ."""
    if unit.kind != "artillery" or unit.artillery_hq:
        return unit.stacking_points
    return Fraction(1)


def effective_points(unit: StackingUnit,
                     context: HexContext = HexContext()) -> Fraction:
    """What *unit* counts for in *context* (9.12, 9.15, 9.16, 9.24, 9.29)."""
    if unit.kind in ("informational", "air", "ground_support", "warship"):
        return Fraction(0)                                   # 9.15
    if unit.kind == "hq" and unit.attached_combat_units == 0:
        return Fraction(0)                                   # 9.12
    if (unit.kind == "garrison" and context.hex_id
            and unit.assigned_city == context.hex_id):
        return Fraction(0)                                   # 9.16
    if unit.kind == "aa" and unit.zero_plus_cpa and not unit.motorized:
        return Fraction(0)                                   # 9.16
    if unit.kind == "aa" and context.major_city:
        return Fraction(0)                                   # 9.16
    if unit.kind == "truck" and unit.attached_to_parent:
        return Fraction(0)                                   # 9.29
    if unit.kind == "truck_convoy":
        return Fraction(0)                                   # 9.29
    return artillery_stacking_points(unit)                    # 9.24


def points_in_hex(units: Iterable[StackingUnit],
                  context: HexContext = HexContext()) -> Fraction:
    """The Stacking Points counted against the hex limit (9.11-9.16, 9.29)."""
    members = tuple(units)
    free_aa = aa_free_allowance(context)
    used_free = 0
    total = Fraction(0)
    for unit in members:
        if (unit.kind == "aa" and not context.major_city
                and not (unit.zero_plus_cpa and not unit.motorized)
                and used_free < free_aa):
            used_free += 1
            continue
        total += effective_points(unit, context)
    return total


def road_points(units: Iterable[StackingUnit],
                context: HexContext = HexContext()) -> Fraction:
    """Points that count against the Road/Track limit (9.29, 9.33).

    Attached first-line trucks never count; truck convoys count only here.
    """
    total = Fraction(0)
    for unit in units:
        if unit.kind == "truck_convoy":
            total += unit.stacking_points
        elif unit.kind == "truck" and unit.attached_to_parent:
            continue
        else:
            total += effective_points(unit, context)
    return total


def small_company_count(units: Iterable[StackingUnit]) -> int:
    """Unattached "?" companies/batteries (9.25)."""
    return sum(1 for unit in units
               if unit.kind == "small" and not unit.attached_to_parent)


def formation_units(units: Iterable[StackingUnit],
                    parent_id: str) -> tuple[StackingUnit, ...]:
    """Units that count as part of a parent formation for stacking (9.21)."""
    return tuple(unit for unit in units
                 if unit.parent_id == parent_id and unit.attached_to_parent)


@dataclass(frozen=True)
class StackingViolation:
    case: str
    message: str

    def to_obj(self) -> dict[str, str]:
        return {"case": self.case, "message": self.message}


@dataclass(frozen=True)
class StackingResult:
    points: Fraction
    limit: Fraction | None
    road_points: Fraction
    violations: tuple[StackingViolation, ...]

    @property
    def allowed(self) -> bool:
        return not self.violations

    def to_obj(self) -> dict[str, Any]:
        return {
            "points": str(self.points),
            "limit": None if self.limit is None else str(self.limit),
            "road_points": str(self.road_points),
            "allowed": self.allowed,
            "violations": [violation.to_obj() for violation in self.violations],
            "rule": RULE,
        }


def check_end_of_movement(units: Iterable[StackingUnit],
                          context: HexContext = HexContext(), *,
                          involuntary_retreat: bool = False) -> StackingResult:
    """Check a hex when movement stops (9.31) or after a retreat (9.35).

    A unit may always move *through* a stack (9.32); this is the check for
    the hex it stops in.  For an involuntary retreat a violation means the
    portion that cannot retreat must stand (9.35, 15.82).
    """
    members = tuple(units)
    points = points_in_hex(members, context)
    road = road_points(members, context)
    violations: list[StackingViolation] = []
    if context.limit is not None and points > context.limit:
        case = "9.35" if involuntary_retreat else "9.31"
        violations.append(StackingViolation(
            case,
            ("an involuntary retreat may not enter a hex in violation of "
             "stacking; the portion that cannot retreat must stand (15.82)"
             if involuntary_retreat else
             "units may never cease movement in a hex in violation of "
             "stacking")))
    if not context.major_city:
        small = small_company_count(members)
        if small > SMALL_UNIT_LIMIT:
            violations.append(StackingViolation(
                "9.25",
                f"{small} unattached '?' companies/batteries in one hex "
                f"(limit {SMALL_UNIT_LIMIT})"))
    return StackingResult(points=points, limit=context.limit,
                          road_points=road, violations=tuple(violations))


def check_road_passage(existing: Iterable[StackingUnit],
                       moving: StackingUnit,
                       context: HexContext = HexContext(), *,
                       limit: Fraction = ROAD_TRACK_LIMIT) -> StackingViolation | None:
    """May *moving* pass through *existing* on a Road/Track? (9.33)"""
    limit = _points(limit, name="limit")
    total = road_points((*tuple(existing), moving), context)
    if total > limit:
        return StackingViolation(
            "9.33",
            "a motorized unit using a Road or Track may not exceed the "
            f"{limit}-point Road/Track limit by moving through friendly "
            "units; it must move around without the Road or Track benefit")
    return None


def passage_allowed(existing: Iterable[StackingUnit], moving: StackingUnit,
                    context: HexContext = HexContext(), *,
                    road_track: bool = False) -> bool:
    """9.32 allows passage; 9.33 is the Road/Track exception."""
    if not road_track:
        return True
    return check_road_passage(existing, moving, context) is None


def level_for_points(points: Fraction | int,
                     table: Mapping[Fraction | int, str]) -> str:
    """Look up the §9.4 organisational level (9.22-9.23).

    The chart itself is not in the vendored corpus, so the caller supplies
    the mapping; a missing entry is an error rather than a guessed level.
    """
    key = _points(points, name="points")
    try:
        level = table[key]
    except KeyError:
        raise StackingError(
            f"no §9.4 level supplied for {key} Stacking Points") from None
    if level not in LEVELS:
        raise StackingError(f"unknown formation level: {level!r}")
    return level


# ---------------------------------------------------------------------------
# shells (9.26-9.28)
# ---------------------------------------------------------------------------

_LEVEL_DOWN = {
    "division": "brigade",
    "brigade": "battalion",
    "battalion": "company",
    "artillery": "battalion",
    "company": "company",
}


@dataclass(frozen=True)
class Formation:
    """A formation's strength, for the shell tests (9.26-9.28).

    For a division or brigade, ``max_components`` and ``attached_components``
    count the lower-level units that may be assigned and are present; a
    shell component does not count toward the prerequisite (9.27).  For a
    battalion or artillery unit, the TOE strength ratio decides.
    """

    level: str
    max_components: int = 1
    attached_components: int = 0
    attached_non_shell_components: int = 0
    toe_strength: Fraction = Fraction(0)
    max_toe_strength: Fraction = Fraction(0)

    def __post_init__(self) -> None:
        if self.level not in _LEVEL_DOWN:
            raise StackingError(f"unknown formation level: {self.level!r}")
        for name in ("max_components", "attached_components",
                     "attached_non_shell_components"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise StackingError(f"{name} must be a non-negative integer")
        if self.max_components < 1:
            raise StackingError("max_components must be at least 1")
        if self.attached_components > self.max_components:
            raise StackingError(
                "attached_components may not exceed max_components")
        if self.attached_non_shell_components > self.attached_components:
            raise StackingError(
                "attached_non_shell_components may not exceed attached_components")
        object.__setattr__(self, "toe_strength",
                           _points(self.toe_strength, name="toe_strength"))
        object.__setattr__(self, "max_toe_strength",
                           _points(self.max_toe_strength, name="max_toe_strength"))

    def is_shell(self) -> bool:
        """9.26: the division/brigade/battalion/artillery shell tests."""
        if self.level == "division":
            return self.attached_components * 2 <= self.max_components
        if self.level == "brigade":
            if (self.max_components == 2 and self.attached_components == 2
                    and self.attached_non_shell_components >= 1):
                return False
            return self.attached_components * 3 < self.max_components * 2
        if self.level == "artillery":
            return self.toe_strength * 4 < self.max_toe_strength
        return self.toe_strength * 2 < self.max_toe_strength

    def qualifies(self) -> bool:
        """9.27: shell components do not count toward the prerequisite."""
        if self.level in ("division", "brigade"):
            return self.attached_non_shell_components >= self.max_components
        return not self.is_shell()

    def effective_level(self) -> str:
        """9.28: a shell is one level lower for Unit Differentiation."""
        return _LEVEL_DOWN[self.level] if self.is_shell() else self.level
