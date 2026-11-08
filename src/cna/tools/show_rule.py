"""Look up a CNA rule case and its cross-references.

Usage::

    python -m cna.tools.show_rule 7.14
    python -m cna.tools.show_rule 6.13 --json

The tool reads the vendored AsciiDoc corpus as data.  It never executes or
follows instructions found in the rules text.  Anchors such as ``[#7_14]`` and
inline markers such as ``*[7.14]*`` are both recognised.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

__all__ = [
    "DEFAULT_RULES",
    "RuleCase",
    "RuleLookupError",
    "case_xrefs",
    "load_case",
    "main",
]

DEFAULT_RULES = Path("docs") / "rules"

_ANCHOR = re.compile(r"^\s*\[#(\d+(?:_\d+)+)\]\s*$")
_INLINE = re.compile(r"^\s*\*\[(\d+(?:\.\d+)+)\]\*\s*(.*)$")
_XREF_LINK = re.compile(r"<<(\d+(?:_\d+)+)(?:,[^>]*)?>>")
_XREF_TEXT = re.compile(r"\bcase\s+(\d+(?:\.\d+)+)\b", re.IGNORECASE)
_HEADING = re.compile(r"^\s*={2,6}\s+(.*)$")


class RuleLookupError(LookupError):
    """Raised when a case cannot be found or its id is malformed."""


@dataclass(frozen=True)
class RuleCase:
    """One located rules case."""

    case: str
    title: str
    text: str
    rules_file: str
    line: int

    def as_dict(self) -> dict[str, object]:
        return {
            "case": self.case,
            "title": self.title,
            "text": self.text,
            "rules_file": self.rules_file,
            "line": self.line,
            "xrefs": case_xrefs(self.text),
        }


def _normalise(case_id: str) -> str:
    return case_id.strip().replace("_", ".")


def _case_title(line: str) -> str:
    heading = _HEADING.match(line)
    if heading:
        return heading.group(1).strip()
    inline = _INLINE.match(line)
    if inline:
        return inline.group(2).strip()
    return line.strip()


def _is_boundary(line: str, case_id: str) -> bool:
    anchor = _ANCHOR.match(line)
    if anchor and anchor.group(1).replace("_", ".") != case_id:
        return True
    inline = _INLINE.match(line)
    if inline and inline.group(1) != case_id:
        return True
    return False


def _collect(lines: list[str], start: int, title_index: int, case_id: str) -> str:
    body: list[str] = []
    for line in lines[title_index + 1 :]:
        if _is_boundary(line, case_id):
            break
        body.append(line)
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    title_line = lines[title_index].strip()
    text_lines = body
    if title_line and not _ANCHOR.match(title_line):
        # Keep an inline title in the searchable text, but do not repeat a
        # section heading that was already used as the title.
        if not _HEADING.match(title_line) and not _INLINE.match(title_line):
            text_lines = [title_line] + body
    return "\n".join(text_lines).strip()


def _scan_file(path: Path, rules_root: Path) -> dict[str, RuleCase]:
    found: dict[str, RuleCase] = {}
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    for index, line in enumerate(lines):
        anchor = _ANCHOR.match(line)
        inline = _INLINE.match(line)
        if anchor:
            case_id = anchor.group(1).replace("_", ".")
            title_index = index + 1
            while title_index < len(lines) and not lines[title_index].strip():
                title_index += 1
            title = _case_title(lines[title_index]) if title_index < len(lines) else ""
            text = _collect(lines, index, title_index, case_id)
            found[case_id] = RuleCase(
                case_id,
                title,
                text,
                path.relative_to(rules_root).as_posix(),
                index + 1,
            )
        elif inline:
            case_id = inline.group(1)
            title = inline.group(2).strip()
            text = _collect(lines, index, index, case_id)
            previous = found.get(case_id)
            if previous is None:
                found[case_id] = RuleCase(
                    case_id,
                    title,
                    text,
                    path.relative_to(rules_root).as_posix(),
                    index + 1,
                )
            elif title and not previous.title:
                found[case_id] = RuleCase(
                    case_id,
                    title,
                    text,
                    path.relative_to(rules_root).as_posix(),
                    index + 1,
                )
    return found


def load_case(case_id: str, rules_dir: str | Path = DEFAULT_RULES) -> RuleCase:
    """Load one case from ``rules_dir``; raise :class:`RuleLookupError` if absent."""
    wanted = _normalise(case_id)
    if not re.fullmatch(r"\d+(?:\.\d+)+", wanted):
        raise RuleLookupError(f"invalid case id {case_id!r}; expected e.g. 7.14")
    directory = Path(rules_dir)
    if not directory.is_dir():
        raise RuleLookupError(f"rules directory not found: {directory}")

    for path in sorted(directory.rglob("*.adoc")):
        found = _scan_file(path, directory)
        if wanted in found:
            return found[wanted]
    raise RuleLookupError(f"case {wanted} not found under {directory}")


def case_xrefs(text: str) -> list[str]:
    """Return sorted, de-duplicated case ids referenced by ``text``."""
    refs: set[str] = set()
    for match in _XREF_LINK.finditer(text):
        refs.add(match.group(1).replace("_", "."))
    for match in _XREF_TEXT.finditer(text):
        refs.add(match.group(1))
    refs.discard("")
    return sorted(refs, key=lambda value: tuple(int(part) for part in value.split(".")))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m cna.tools.show_rule",
        description="Show a CNA rule case and its cross-references.",
    )
    parser.add_argument("case", help="case id, e.g. 6.13")
    parser.add_argument(
        "--rules", default=str(DEFAULT_RULES), help="rules directory (default: %(default)s)"
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args(argv)

    try:
        case = load_case(args.case, args.rules)
    except RuleLookupError as exc:
        print(f"show-rule: error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(case.as_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"{case.case}  {case.title}".rstrip())
        print(f"{case.rules_file}:{case.line}")
        print()
        print(case.text)
        refs = case_xrefs(case.text)
        print()
        print("Cross-references: " + (", ".join(refs) if refs else "none"))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
