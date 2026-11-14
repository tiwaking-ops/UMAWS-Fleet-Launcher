"""Every copy of the dispatch-failure report must keep T-0146 reconciled.

The report was written while T-0146 was still READY and OQ-04 was open.  The
2026-11-09 reconciliation recorded ``TASK_VOIDED`` seq 3315 and closed OQ-04.
The report exists in more than one directory, so the correction can survive in
one copy and be lost in another.

Scope: a "report copy" is any file with this report's exact basename in the
working tree.  Agent worktrees (``work/``), scratch output (``tmp/``) and
``quarantine/`` hold historical duplicates that are evidence, not current
report copies, and are excluded on purpose.  Only a present-tense claim
("T-0146 is READY") fails: the report legitimately records that T-0146 *was*
READY at the writing point.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_NAME = "dispatch-failure-root-cause-and-remediation-v1.md"

#: Trees that hold historical duplicates (agent worktrees, scratch, quarantine)
#: or tool output.  They are not current report copies.
EXCLUDED_DIRS = {
    ".git", ".venv", ".claude", ".pytest_cache", "__pycache__",
    "work", "tmp", "quarantine", "node_modules", "build", "dist",
}

#: A present-tense claim that T-0146 is READY.  "was still READY" is history
#: and must not fail the check.
PRESENT_READY = re.compile(
    r"\bT-0146\b\s+(?:is|remains|stays)\s+(?:still\s+)?READY\b",
    re.IGNORECASE)


def report_copies(root: Path = ROOT) -> list[Path]:
    """Every current copy of the report, wherever it sits in the tree."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIRS)
        if REPORT_NAME in filenames:
            found.append(Path(dirpath) / REPORT_NAME)
    return sorted(found)


def _plain(text: str) -> str:
    """Drop the markdown emphasis so one rule covers bold and plain cells."""
    return text.replace("`", "").replace("*", "")


def _f04_section(text: str) -> str:
    """The F-04 body: from its heading to the next same-level heading."""
    after = text.split("### F-04", 1)[1]
    return after.split("\n### ", 1)[0]


def _oq04_row(text: str) -> str | None:
    return next((line for line in text.splitlines()
                 if line.startswith("| OQ-04 |")), None)


def problems(text: str) -> list[str]:
    """Reasons this copy still presents T-0146 as READY or OQ-04 as open."""
    plain = _plain(text)
    issues: list[str] = []

    if "### F-04" not in text:
        issues.append("no F-04 section")
    else:
        section = _plain(_f04_section(text))
        if "VOID" not in section:
            issues.append("F-04 does not record T-0146 as VOID")
        if PRESENT_READY.search(section):
            issues.append("F-04 still says T-0146 is READY")

    row = _oq04_row(text)
    if row is None:
        issues.append("no OQ-04 table row")
    else:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        status = _plain(cells[2]).strip().lower() if len(cells) >= 3 else ""
        if status != "closed":
            issues.append(f"OQ-04 is not closed (status {status!r})")
        if "VOID" not in _plain(row):
            issues.append("OQ-04 does not record T-0146 as VOID")

    if PRESENT_READY.search(plain):
        issues.append("the report still says T-0146 is READY")

    return issues


def test_every_report_copy_is_reconciled():
    copies = report_copies()
    assert copies, "no report copies found"
    assert ROOT / "docs" / "reports" / REPORT_NAME in copies

    failures = {}
    for path in copies:
        issues = problems(path.read_text(encoding="utf-8"))
        if issues:
            failures[str(path.relative_to(ROOT))] = issues

    assert not failures, "\n".join(
        f"{name}: {', '.join(issues)}" for name, issues in failures.items())


def _synthetic(f04: str = "T-0146 is VOID (TASK_VOIDED seq 3315).",
               oq: str = "closed") -> str:
    return (
        "### F-04 — T-0146's hint was false and unpinnable\n\n"
        "At the writing point T-0146 was still READY.\n\n"
        f"{f04}\n\n"
        "| id | topic | status | evidence |\n"
        "|---|---|---|---|\n"
        f"| OQ-04 | T-0146 disposition | **{oq}** | "
        "T-0146 was voided at seq 3315; it is VOID. |\n")


def test_a_corrected_copy_passes():
    assert problems(_synthetic()) == []


def test_a_copy_that_still_says_t0146_is_ready_fails():
    issues = problems(_synthetic(f04="T-0146 is READY, and S8 refuses it."))

    assert "F-04 still says T-0146 is READY" in issues


def test_a_copy_that_leaves_oq04_open_fails():
    issues = problems(_synthetic(oq="open"))

    assert any(issue.startswith("OQ-04 is not closed") for issue in issues)


def test_a_copy_without_the_oq04_row_fails():
    text = _synthetic().replace("| OQ-04 | T-0146 disposition", "| OQ-05 | other")

    assert "no OQ-04 table row" in problems(text)
