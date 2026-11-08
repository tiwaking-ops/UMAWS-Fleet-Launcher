"""Decomposition width for the Fleet (D-L6 made visible).

The Dispatcher can lease two cards at once only when their write scopes are
disjoint: ``Kernel.claim`` refuses a lease that overlaps any card already
holding one.  Parallelism is therefore a property of how the Overseer *shapes*
the wave, not of the fleet cap.  Two broad cards run at width two however many
slots exist, and a card whose scope is a tree root serialises with every card
under that tree.

``analyse`` measures a card set.  ``render_section`` states the gap in the
Overseer briefing, which is the Overseer's authority on every wake, so the
number it needs to improve is in front of it rather than implied.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import scope_overlaps

#: A write scope naming one of these with no deeper path is a whole tree.
#: Such a card blocks every card under that tree for as long as it runs.
TREE_ROOTS = frozenset({
    "src", "docs", "tests", "test", "tools", "scripts", "console", "config",
    "pilot", "pmk", "fleet", "cna", "quotagate", "bundle", "work",
})

#: A card that must touch more paths than this is too coarse to sit beside
#: other cards comfortably.  Advisory: the lint never refuses work.
MAX_PATHS_PER_CARD = 3

#: The states that are candidates for a lease (PROPOSED cards are admitted
#: automatically when they pass admission, so they count toward the wave).
CANDIDATE_STATES = ("READY", "PROPOSED")


@dataclass
class Shape:
    """The parts of a card that decide whether it can run beside another."""

    id: str
    state: str
    scope: list[str]
    depends_on: list[str]

    @property
    def broad(self) -> list[str]:
        """Write paths that name a whole tree rather than a leaf."""
        hits: list[str] = []
        for path in self.scope:
            norm = str(path).strip().replace("\\", "/").strip("/")
            if not norm or norm == ".":
                hits.append(path)
            elif "/" not in norm and norm in TREE_ROOTS:
                hits.append(path)
        return hits

    @property
    def oversized(self) -> bool:
        return len(self.scope) > MAX_PATHS_PER_CARD


@dataclass
class WidthReport:
    """How wide a wave is, and why it is not wider."""

    width: int
    target: int
    considered: int
    depth: int = 0
    conflicts: list = field(default_factory=list)
    broad: list = field(default_factory=list)
    oversized: list = field(default_factory=list)

    @property
    def shortfall(self) -> int:
        return max(0, self.target - self.width)

    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "target": self.target,
            "shortfall": self.shortfall,
            "considered": self.considered,
            "depth": self.depth,
            "conflicts": list(self.conflicts),
            "broad": list(self.broad),
            "oversized": list(self.oversized),
        }


def shape_of(task) -> Shape:
    """Read a shape from a TaskCard or any object with the same fields."""
    scope = getattr(task, "write_scope", None)
    if scope is None:
        scope = (getattr(task, "scope", {}) or {}).get("write") or []
    return Shape(
        id=str(getattr(task, "id", "")),
        state=str(getattr(task, "state", "")),
        scope=[str(path) for path in scope],
        depends_on=[str(dep) for dep in (getattr(task, "depends_on", []) or [])],
    )


def _overlaps(left: Shape, right: Shape) -> bool:
    return bool(scope_overlaps(left.scope, right.scope))


def _depth(shapes: list[Shape]) -> int:
    """Longest ``depends_on`` chain inside the considered set, in cards."""
    by_id = {shape.id: shape for shape in shapes}
    best: dict[str, int] = {}

    def walk(node: str, seen: set[str]) -> int:
        if node in best:
            return best[node]
        if node in seen:
            return 0
        seen.add(node)
        deps = [d for d in by_id[node].depends_on if d in by_id]
        value = 1 + max((walk(dep, seen) for dep in deps), default=0) if deps else 1
        best[node] = value
        return value

    return max((walk(shape.id, set()) for shape in shapes), default=0)


def analyse(tasks, *, target: int = 10,
            states: tuple[str, ...] = ("READY",)) -> WidthReport:
    """Measure how many of *tasks* can hold leases at the same time.

    *width* is a **lower bound**: the size of the largest pairwise-disjoint set
    found by taking the narrowest cards first.  Finding the exact maximum is a
    maximum-independent-set problem, so the report says "greedy" rather than
    pretending to an optimum.  A width at or above *target* means the fleet cap,
    not the cards, is the limit.
    """
    shapes = sorted(
        (shape_of(task) for task in tasks if task.state in states),
        key=lambda shape: shape.id,
    )

    conflicts: list[dict] = []
    for index, left in enumerate(shapes):
        for right in shapes[index + 1:]:
            hits = scope_overlaps(left.scope, right.scope)
            if not hits:
                continue
            conflicts.append({
                "task": left.id,
                "other": right.id,
                "path": hits[0][0],
                "other_path": hits[0][1],
                "dependent": (right.id in left.depends_on
                              or left.id in right.depends_on),
            })

    # Narrowest first: a card touching one deep file is less likely to block
    # the rest of the wave than a card touching a directory.
    chosen: list[Shape] = []
    for shape in sorted(
            shapes,
            key=lambda item: (len(item.scope),
                              -max((len(p) for p in item.scope), default=0),
                              item.id)):
        if all(not _overlaps(shape, seated) for seated in chosen):
            chosen.append(shape)

    broad = [{"task": shape.id, "path": path}
             for shape in shapes for path in shape.broad]
    oversized = [{"task": shape.id, "paths": len(shape.scope)}
                 for shape in shapes if shape.oversized]

    return WidthReport(width=len(chosen), target=int(target),
                       considered=len(shapes), depth=_depth(shapes),
                       conflicts=conflicts, broad=broad, oversized=oversized)


def render_section(tasks, *, target: int,
                   states: tuple[str, ...] = CANDIDATE_STATES,
                   limit: int = 8) -> str:
    """The Overseer briefing's Decomposition section."""
    report = analyse(tasks, target=target, states=states)
    lines = ["## Decomposition (this is what limits throughput)", ""]
    lines.append(
        f"- Fleet cap: {report.target} slots. Leaseable width now: "
        f"**{report.width}** of {report.target} (pairwise-disjoint write scopes, "
        f"greedy lower bound).")
    if report.shortfall:
        lines.append(
            f"- Shortfall: {report.shortfall} more card(s) with disjoint scopes "
            f"are needed before the cap, not the wave, is the limit.")
    else:
        lines.append("- Width covers the cap; keep new scopes disjoint as the "
                     "wave grows.")
    lines.append(
        f"- Considered {report.considered} card(s) in {', '.join(states)}; "
        f"longest dependency chain: {report.depth} card(s).")
    lines.append("")
    lines.append("Contract for every card you create:")
    lines.append("- one deliverable per card; one file when possible, never "
                 f"more than {MAX_PATHS_PER_CARD} write paths;")
    lines.append("- a write scope is a file or a leaf directory, never a tree "
                 "root (`src/`, `docs/`, `tests/`);")
    lines.append("- cards meant to run together must have disjoint write scopes;")
    lines.append("- `depends_on` only for a real interface or data prerequisite;")
    lines.append("- the oracle runs only that card's own tests;")
    lines.append("- aim for 12-20 cards per wave and at least the fleet cap of "
                 "leaseable, non-conflicting cards.")
    lines.append("")

    independent = [c for c in report.conflicts if not c["dependent"]]
    dependent = [c for c in report.conflicts if c["dependent"]]
    if independent:
        lines.append("Independent overlaps (cannot hold leases together; split "
                     "or re-scope):")
        for conflict in independent[:limit]:
            lines.append(f"- {conflict['task']} <-> {conflict['other']} on "
                         f"`{conflict['path']}`")
        if len(independent) > limit:
            lines.append(f"- … and {len(independent) - limit} more")
        lines.append("")
    if dependent:
        lines.append("Overlaps held apart by `depends_on` (keep only if the "
                     "dependency is real):")
        for conflict in dependent[:limit]:
            lines.append(f"- {conflict['task']} <-> {conflict['other']} on "
                         f"`{conflict['path']}`")
        if len(dependent) > limit:
            lines.append(f"- … and {len(dependent) - limit} more")
        lines.append("")
    if report.broad:
        lines.append("Whole-tree write scopes (split them):")
        for entry in report.broad[:limit]:
            lines.append(f"- {entry['task']} writes `{entry['path']}`")
        if len(report.broad) > limit:
            lines.append(f"- … and {len(report.broad) - limit} more")
        lines.append("")
    if report.oversized:
        lines.append(f"Cards over {MAX_PATHS_PER_CARD} write paths:")
        for entry in report.oversized[:limit]:
            lines.append(f"- {entry['task']} writes {entry['paths']} paths")
        if len(report.oversized) > limit:
            lines.append(f"- … and {len(report.oversized) - limit} more")
        lines.append("")
    if not (independent or dependent or report.broad or report.oversized):
        lines.append("No scope collisions or whole-tree scopes in the considered "
                     "set.")
        lines.append("")
    return "\n".join(lines).rstrip()
