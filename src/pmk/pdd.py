"""PDD structure check (fleet amendment section 12.G).

``pmk pdd lint <file>`` is the oracle for the ``plan`` task that produces
``docs/PDD.md``.  The lint is deterministic and cheap: it checks structure,
not quality.

Lint rules (fleet amendment section 12.G, verbatim):

* all seven sections present;
* goal IDs unique and sequential;
* every goal has acceptance criteria and exactly one of ``oracle`` or
  ``manual-check``;
* ``gate_cmd`` present.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_SECTIONS = (
    "Purpose", "Goals", "Non-goals", "Constraints",
    "Architecture sketch", "Definition of done", "Open questions",
)

GOAL_HEADING = re.compile(r"^#{2,4}\s*G-(\d{3})\b(.*)$", re.MULTILINE)
ORACLE_LINE = re.compile(r"^\s*[-*]?\s*oracle:\s*`?(.+?)`?\s*$", re.MULTILINE)
MANUAL_LINE = re.compile(r"^\s*[-*]?\s*manual-check:\s*(.+?)\s*$", re.MULTILINE)
GATE_CMD = re.compile(r"^\s*gate_cmd:\s*`?(.+?)`?\s*$", re.MULTILINE)


@dataclass
class LintResult:
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"ok": self.ok, "errors": self.errors,
                "warnings": self.warnings, "goals": self.goals}


def lint_text(text: str) -> LintResult:
    """Lint a PDD's text."""
    result = LintResult()

    # -- the seven sections ------------------------------------------------
    headings = [line.strip("# ").strip() for line in text.splitlines()
                if line.startswith("#")]
    lowered = [h.lower() for h in headings]
    for section in REQUIRED_SECTIONS:
        needle = section.lower()
        if not any(needle in h for h in lowered):
            result.errors.append(f"missing section: {section}")

    # -- goals -------------------------------------------------------------
    matches = list(GOAL_HEADING.finditer(text))
    ids = [m.group(1) for m in matches]
    result.goals = [f"G-{i}" for i in ids]
    if not matches:
        result.errors.append("no goals found (expected headings like '### G-001 ...')")
    if len(set(ids)) != len(ids):
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        result.errors.append(f"duplicate goal ids: {', '.join('G-' + d for d in duplicates)}")
    for index, ident in enumerate(ids, start=1):
        expected = f"{index:03d}"
        if ident != expected:
            result.errors.append(
                f"goal ids must be sequential: expected G-{expected}, got G-{ident}")

    # -- acceptance criteria and exactly one of oracle / manual-check -----
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end]
        goal_id = f"G-{match.group(1)}"
        if not re.search(r"^\s*[-*]\s+\S", body, re.MULTILINE):
            result.errors.append(f"{goal_id} has no acceptance criteria")
        oracles = ORACLE_LINE.findall(body)
        manuals = MANUAL_LINE.findall(body)
        if not oracles and not manuals:
            result.errors.append(
                f"{goal_id} needs exactly one of 'oracle:' or 'manual-check:'")
        if oracles and manuals:
            result.errors.append(
                f"{goal_id} has both an oracle and a manual-check; "
                f"exactly one is required")
        if len(oracles) > 1:
            result.errors.append(f"{goal_id} has more than one oracle")

    # -- gate command ------------------------------------------------------
    if not GATE_CMD.search(text):
        result.errors.append("missing gate_cmd in the Definition of done section")

    result.ok = not result.errors
    return result


def lint_file(path: str | Path) -> LintResult:
    """Lint a PDD file."""
    target = Path(path)
    try:
        text = target.read_text(encoding="utf-8")
    except OSError as exc:
        return LintResult(ok=False, errors=[f"cannot read {target}: {exc}"])
    return lint_text(text)
