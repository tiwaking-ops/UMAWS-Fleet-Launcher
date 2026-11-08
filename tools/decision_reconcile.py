"""Report decision-record gaps.  Read-only: it never edits anything.

Six events in the incident window (Q-076, Q-077, REC-01, REC-02, the T-0150
canary, e08fa8d/ebe46ce) had no entry in ``pilot/decisions.md``.  The gap was
invisible because nothing compared the two records.

This tool answers three questions:

* are decision ids unique?
* is the numbering contiguous?
* which recent commits touching the decision log or the policy have no
  ``D-<n>`` reference in their subject?

Exit status is 0 even when gaps exist: it is a report, not a gate, so it can
run on an unfinished tree.  ``--strict`` turns gaps into a non-zero exit for
use in a future gate.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ENTRY_RE = re.compile(r"^D-(\d+)\s*\|", re.MULTILINE)
REFERENCE_RE = re.compile(r"D-(\d+)")
TRACKED = ("pilot/decisions.md", ".pm/policy.toml")


def parse_decisions(text: str) -> list[int]:
    return [int(number) for number in ENTRY_RE.findall(text)]


def duplicate_ids(numbers: list[int]) -> list[int]:
    seen: set[int] = set()
    duplicates: list[int] = []
    for number in numbers:
        if number in seen and number not in duplicates:
            duplicates.append(number)
        seen.add(number)
    return sorted(duplicates)


def missing_ids(numbers: list[int]) -> list[int]:
    if not numbers:
        return []
    return [n for n in range(1, max(numbers) + 1) if n not in set(numbers)]


def commits_without_record(root: Path, *, limit: int = 100) -> list[dict]:
    """Commits touching the log or the policy with no ``D-<n>`` in the subject."""
    root = Path(root)
    code, out, _ = _git(root, "log", f"-{limit}", "--format=%h%x1f%s", "--name-only")
    if code != 0:
        return []
    gaps: list[dict] = []
    for block in out.split("\n\n"):
        lines = [line for line in block.splitlines() if line.strip()]
        if not lines or "\x1f" not in lines[0]:
            continue
        sha, subject = lines[0].split("\x1f", 1)
        files = lines[1:]
        touches = any(f in TRACKED for f in files)
        if touches and not REFERENCE_RE.search(subject):
            gaps.append({"commit": sha, "subject": subject, "files": files})
    return gaps


def _git(root: Path, *args: str):
    try:
        proc = subprocess.run(["git", "-C", str(root), *args],
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace")
    except OSError as exc:  # pragma: no cover - defensive
        return 1, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def render(numbers: list[int], duplicates: list[int], missing: list[int],
           gaps: list[dict]) -> str:
    lines = ["# Decision-record reconciliation", "",
             f"- decisions recorded: **{len(numbers)}** (highest D-{max(numbers) if numbers else 0})",
             f"- duplicate ids: {duplicates or 'none'}",
             f"- missing ids: {missing or 'none'}",
             f"- commits touching the log or policy with no D-reference: {len(gaps)}", ""]
    if gaps:
        lines += ["| Commit | Subject |", "|---|---|"]
        for gap in gaps:
            lines.append(f"| `{gap['commit']}` | {gap['subject']} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", default="")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)

    root = Path(args.root)
    decisions = root / "pilot" / "decisions.md"
    text = decisions.read_text(encoding="utf-8-sig") if decisions.is_file() else ""
    numbers = parse_decisions(text)
    duplicates = duplicate_ids(numbers)
    missing = missing_ids(numbers)
    gaps = commits_without_record(root, limit=args.limit)
    report = render(numbers, duplicates, missing, gaps)

    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)

    if args.strict and (duplicates or missing or gaps):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
