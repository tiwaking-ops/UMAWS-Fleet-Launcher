"""Rules-coverage tool for the CNA digital edition.

Every vendored rules file (``docs/rules/`` by default) declares, in its YAML
frontmatter, which parts of the repository it governs::

    ---
    paths:
      - src/pmk/**
      - .pm/**
    ---

This tool answers one question: **which files in the tree are governed by at
least one rules file, and which are governed by none?**  It scans the source
roots, matches every scanned path against every rule file's ``paths`` globs,
and writes ``coverage/rules_coverage.json`` describing:

* **rules** — each rule file, its declared globs, and the paths it matches;
* **uncovered_paths** — every scanned path that no rule file claims;
* **counts** — the headline numbers (paths, covered, uncovered, rule files).

Design notes
------------
* Standard library only; Windows-native (BOM-tolerant reads, atomic replace).
* Deterministic: the same inputs always yield byte-identical JSON, so the
  report can be diffed, hashed and regenerated at will.  No timestamps.
* Glob semantics: ``**`` spans whole path segments (at least one, so
  ``src/pmk/**`` does *not* match ``src/pmk`` itself); ``*`` and ``?`` stay
  within a single segment; ``[...]`` is a character class.  Paths are compared
  in POSIX form (forward slashes) and case-sensitively.
* Frontmatter is parsed leniently: a rule file with no usable ``paths`` block
  is reported as matching nothing rather than failing the run.
* Text in the corpus is data.  Nothing here executes, imports or follows
  instructions found in the rules files.

Usage::

    python -m cna.tools.coverage                     # src -> coverage/rules_coverage.json
    python -m cna.tools.coverage --rules X --src Y   # custom roots (repeatable --src)
    python -m cna.tools.coverage --check             # drift check, exit 1 on mismatch
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence

__all__ = [
    "SCHEMA_VERSION",
    "DEFAULT_RULES_DIRNAME",
    "DEFAULT_SRC_ROOTS",
    "DEFAULT_OUT",
    "RulesCoverageError",
    "glob_matches",
    "iter_source_paths",
    "build_coverage",
    "dumps_coverage",
    "write_coverage",
    "load_coverage",
    "case_inventory",
    "CASE_STATUS",
    "CASE_STATUSES",
    "main",
]

SCHEMA_VERSION = 1
DEFAULT_RULES_DIRNAME = Path("docs") / "rules"
DEFAULT_SRC_ROOTS: tuple[str, ...] = ("src",)
DEFAULT_OUT = Path("coverage") / "rules_coverage.json"

#: Directories that are never source files worth reporting on.
SKIP_DIRS = {"__pycache__", ".git", ".venv", "node_modules"}

#: Suffixes that are never source files worth reporting on.
SKIP_SUFFIXES = {".pyc", ".pyo", ".lock"}

#: The reviewed status vocabulary for a single CNA case.  A case is not
#: implemented merely because a path glob mentions the file that contains
#: it; the status and its evidence are explicit here.
CASE_STATUSES = ("implemented", "partial", "unimplemented",
                 "not_applicable", "deferred")

#: Cases that have deliberately reviewed implementation evidence.  Every
#: other parsed case is ``unimplemented``.  Sources are relative to the
#: repository root; tests are the files that exercise the implementation.
CASE_STATUS: dict[str, dict[str, Any]] = {
    "2.0": {
        "status": "partial", "source": "src/cna/engine/rulesets.py",
        "tests": ["tests/test_rulesets.py"],
        "reason": "LAND_ABSTRACT is available; Air and Logistics combinations are deferred",
    },
    "3.0": {
        "status": "implemented", "source": "src/cna/core/dice.py",
        "tests": ["tests/test_dice.py"], "reason": "",
    },
    "5.2": {
        "status": "partial", "source": "src/cna/rules/sec05_sequence.py",
        "tests": ["tests/test_sequence.py"],
        "reason": "sequence outline only; individual phase mechanics are not implemented",
    },
    "7.11": {
        "status": "implemented", "source": "src/cna/rules/sec07_initiative.py",
        "tests": ["tests/test_initiative_weather.py"], "reason": "",
    },
    "7.12": {
        "status": "implemented", "source": "src/cna/rules/sec07_initiative.py",
        "tests": ["tests/test_initiative_weather.py"], "reason": "",
    },
    "7.13": {
        "status": "partial", "source": "src/cna/rules/sec07_initiative.py",
        "tests": ["tests/test_initiative_weather.py"],
        "reason": "ratings are accepted as inputs; the historical ratings chart (R-05) is absent",
    },
    "7.14": {
        "status": "implemented", "source": "src/cna/rules/sec07_initiative.py",
        "tests": ["tests/test_initiative_weather.py"], "reason": "",
    },
    "7.16": {
        "status": "implemented", "source": "src/cna/rules/sec07_initiative.py",
        "tests": ["tests/test_initiative_weather.py"], "reason": "",
    },
    "29.1": {
        "status": "partial", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_initiative_weather.py"],
        "reason": "synthetic-test table only; the historical R-04 table and map areas are absent",
    },
    "29.31": {
        "status": "partial", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_initiative_weather.py"],
        "reason": "hot weather is classified; its map-wide effects are not implemented",
    },
    "29.35": {
        "status": "partial", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_initiative_weather.py"],
        "reason": "water requirements are not tracked",
    },
    "29.41": {
        "status": "partial", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_initiative_weather.py"],
        "reason": "storm location is rolled; map-section effects are not implemented",
    },
    "29.51": {
        "status": "partial", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_initiative_weather.py"],
        "reason": "rainstorms are classified; map-section effects are not implemented",
    },
    "32.0": {
        "status": "deferred", "source": "src/cna/engine/rulesets.py",
        "tests": ["tests/test_rulesets.py"],
        "reason": "abstract supply and air rules are not implemented in P1",
    },
    "33.0": {
        "status": "deferred", "source": "src/cna/engine/rulesets.py",
        "tests": ["tests/test_rulesets.py"],
        "reason": "Air Game sequence and charts are not implemented",
    },
    "47.0": {
        "status": "deferred", "source": "src/cna/engine/rulesets.py",
        "tests": ["tests/test_rulesets.py"],
        "reason": "Air Game abstract logistics rules are not implemented",
    },
    "48.0": {
        "status": "deferred", "source": "src/cna/engine/rulesets.py",
        "tests": ["tests/test_rulesets.py"],
        "reason": "Logistics Game sequence is not implemented",
    },
    "58.0": {
        "status": "deferred", "source": "src/cna/engine/rulesets.py",
        "tests": ["tests/test_rulesets.py"],
        "reason": "Air Game abstract rules are not implemented",
    },
}


class RulesCoverageError(RuntimeError):
    """Raised for operator errors: a missing rules dir, an unreadable output."""


# --------------------------------------------------------------------------
# scanning primitives
# --------------------------------------------------------------------------

_GLOB_SPECIAL = "*?[]"


def _translate_segment(segment: str) -> str:
    """Translate one non-``**`` glob segment into a regex fragment."""
    out: list[str] = []
    i = 0
    while i < len(segment):
        ch = segment[i]
        if ch == "*":
            out.append("[^/]*")
    	# collapse consecutive stars inside a segment
            while i + 1 < len(segment) and segment[i + 1] == "*":
                i += 1
        elif ch == "?":
            out.append("[^/]")
        elif ch == "[":
            end = segment.find("]", i + 1)
            if end == -1:
                out.append(re.escape("["))
            else:
                body = segment[i + 1 : end]
                negative = body.startswith(("!", "^"))
                if negative:
                    body = body[1:]
                body = body.replace("\\", "\\\\")
                if body.startswith("]"):
                    body = "\\" + body
                out.append("[" + ("^" if negative else "") + body + "]")
                i = end
        else:
            out.append(re.escape(ch))
        i += 1
    return "".join(out)


def glob_to_regex(glob: str) -> re.Pattern[str]:
    """Compile a repository-style path glob into an anchored regex.

    ``**`` matches one or more whole segments (so ``src/**`` matches
    ``src/a.py`` but ``a/**/b.py`` also matches ``a/b.py`` when the leading
    ``**`` is *not* the final segment — there it matches zero or more
    segments, mirroring shell semantics).  ``*`` and ``?`` never cross a
    slash; ``[...]`` is a character class.
    """
    glob = glob.strip().replace("\\", "/").strip("/")
    if not glob:
        raise ValueError("empty glob")
    segments = glob.split("/")
    parts: list[str] = []
    for idx, segment in enumerate(segments):
        last = idx == len(segments) - 1
        if segment == "**":
            if last:
                # At least one segment, then anything (gitignore-style: the
                # pattern names files *inside*, not the directory itself).
                parts.append(r"[^/]+(?:/[^/]+)*")
            else:
                # Zero or more full segments, each with its trailing slash.
                parts.append(r"(?:[^/]+/)*")
        else:
            parts.append(_translate_segment(segment))
            if not last:
                parts.append("/")
    return re.compile("^" + "".join(parts) + "$")


def glob_matches(glob: str, path: str | PurePosixPath) -> bool:
    """True when ``glob`` covers ``path`` (a POSIX-style relative path)."""
    posix = str(path).replace("\\", "/").lstrip("/")
    try:
        pattern = glob_to_regex(glob)
    except ValueError:
        return False
    return pattern.match(posix) is not None


def _frontmatter_paths(text: str) -> tuple[list[str], bool]:
    """Extract the ``paths:`` glob list from frontmatter, leniently.

    Returns ``(globs, has_frontmatter)``.  A file without frontmatter, or
    without a usable ``paths`` block, yields no globs.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() not in ("---", "---\t"):
        return [], False
    globs: list[str] = []
    in_paths = False
    for line in lines[1 : min(len(lines), 500)]:
        stripped = line.strip()
        if stripped in ("---", "..."):
            break
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            if in_paths:
                value = stripped[2:].strip().strip("'\"")
                if value:
                    globs.append(value)
            continue
        in_paths = stripped.rstrip(":") == "paths" and stripped.endswith(":")
    return globs, True


_CASE_ANCHOR = re.compile(r"^\s*\[#(\d+(?:_\d+)+)\]\s*$")
_CASE_INLINE = re.compile(r"^\s*\*\[(\d+(?:\.\d+)+)\]\*\s*(.*)$")
_CASE_HEADING = re.compile(r"^\s*={2,6}\s+(.*)$")
_SECTION_FILE = re.compile(r"section-(\d+)\.adoc$", re.IGNORECASE)


def _case_sort_key(case_id: str) -> tuple[int, ...]:
    return tuple(int(part) for part in case_id.split(".") if part.isdigit())


def _case_title(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _title_after(lines: list[str], start: int) -> str:
    for raw in lines[start + 1:start + 6]:
        line = raw.strip()
        if not line:
            continue
        heading = _CASE_HEADING.match(line)
        if heading:
            return _case_title(heading.group(1))
        inline = _CASE_INLINE.match(line)
        if inline:
            return _case_title(inline.group(2))
        return _case_title(line)
    return ""


def _record_case(cases: dict[str, dict[str, Any]], case_id: str,
                 title: str, rules_file: str, line: int) -> None:
    record = cases.setdefault(case_id, {
        "case": case_id, "title": "", "rules_file": rules_file, "line": line,
    })
    if title and not record["title"]:
        record["title"] = title


def case_inventory(directory: Path) -> list[dict[str, Any]]:
    """Parse the rule corpus into a deterministic case inventory.

    Explicit section anchors and inline ``*[case]*`` markers are both
    recognised.  A major section with no parsed child case gets a ``N.0``
    entry, which lets a deferred whole module remain visible rather than
    disappearing from the report.
    """
    cases: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.rglob("*.adoc")):
        rel = path.relative_to(directory).as_posix()
        lines = read_text(path).splitlines()
        for index, line in enumerate(lines):
            anchor = _CASE_ANCHOR.match(line)
            if anchor:
                case_id = anchor.group(1).replace("_", ".")
                _record_case(cases, case_id, _title_after(lines, index), rel,
                             index + 1)
            inline = _CASE_INLINE.match(line)
            if inline:
                _record_case(cases, inline.group(1), _case_title(inline.group(2)),
                             rel, index + 1)

    for path in sorted(directory.glob("sections/section-*.adoc")):
        match = _SECTION_FILE.match(path.name)
        if not match:
            continue
        case_id = f"{int(match.group(1))}.0"
        if case_id in cases:
            continue
        lines = read_text(path).splitlines()
        title = ""
        line_number = 1
        for index, line in enumerate(lines):
            heading = _CASE_HEADING.match(line.strip())
            if heading:
                title = _case_title(heading.group(1))
                line_number = index + 1
                break
        _record_case(cases, case_id, title,
                     path.relative_to(directory).as_posix(), line_number)

    return [cases[key] for key in sorted(cases, key=_case_sort_key)]


def iter_source_paths(
    roots: Iterable[str | os.PathLike[str] | Path],
    *,
    root: str | os.PathLike[str] | Path | None = None,
) -> list[str]:
    """Collect the relative POSIX paths of the files under ``roots``.

    ``root`` is the base the returned paths are relative to (default: the
    current working directory).  Deterministic: sorted, duplicates removed,
    cache/build directories and byte-code suffixes skipped.
    """
    base = Path(root) if root is not None else Path.cwd()
    found: set[str] = set()
    for one in roots:
        start = Path(one)
        if not start.is_absolute():
            start = base / start
        if start.is_file():
            found.add(start.resolve().relative_to(base.resolve()).as_posix())
            continue
        if not start.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(start):
            # Build metadata (src/*.egg-info) is not source and is not present
            # in a fresh worktree, so counting it made --check pass on main and
            # fail in every lease worktree.
            dirnames[:] = sorted(
                d for d in dirnames
                if d not in SKIP_DIRS and not d.endswith(".egg-info"))
            for filename in sorted(filenames):
                full = Path(dirpath) / filename
                if full.suffix.lower() in SKIP_SUFFIXES:
                    continue
                found.add(full.resolve().relative_to(base.resolve()).as_posix())
    return sorted(found)


# --------------------------------------------------------------------------
# the coverage report
# --------------------------------------------------------------------------


def build_coverage(
    rules_dir: str | os.PathLike[str] | Path = DEFAULT_RULES_DIRNAME,
    paths: Iterable[str] = (),
    *,
    rules_dir_label: str | None = None,
) -> dict[str, Any]:
    """Build the rules-coverage report for ``paths`` against ``rules_dir``.

    ``paths`` are POSIX-style repository-relative paths (see
    :func:`iter_source_paths`).  The returned mapping is JSON-ready and
    deterministic.
    """
    directory = Path(rules_dir)
    if not directory.is_dir():
        raise RulesCoverageError(f"rules directory not found: {directory}")

    scanned = sorted(set(str(p).replace("\\", "/").lstrip("/") for p in paths))
    covered: set[str] = set()
    rules: list[dict[str, Any]] = []

    # The vendored CNA corpus is AsciiDoc *and* it lives in subdirectories;
    # the earlier top-level ``.md``-only scan reported 3 rule files for 66,
    # which made T-0146's oracle (rule_files >= 66) unsatisfiable no matter
    # what an agent wrote.
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in (".md", ".adoc"):
            continue
        text = read_text(path)
        globs, _has = _frontmatter_paths(text)
        matched = sorted(p for p in scanned if any(glob_matches(g, p) for g in globs))
        covered.update(matched)
        rules.append(
            {
                "file": path.relative_to(directory).as_posix(),
                "globs": globs,
                "match_count": len(matched),
                "matching": bool(matched),
                "matched_paths": matched,
            }
        )

    uncovered = [p for p in scanned if p not in covered]
    cases: list[dict[str, Any]] = []
    case_counts = {status: 0 for status in CASE_STATUSES}
    for entry in case_inventory(directory):
        spec = CASE_STATUS.get(entry["case"], {})
        status = spec.get("status", "unimplemented")
        if status not in CASE_STATUSES:
            raise RulesCoverageError(
                f"unknown case status {status!r} for {entry['case']}")
        cases.append({
            **entry,
            "status": status,
            "source": spec.get("source", ""),
            "tests": list(spec.get("tests") or []),
            "reason": spec.get("reason", ""),
        })
        case_counts[status] += 1

    return {
        "schema_version": SCHEMA_VERSION,
        "rules_dir": (rules_dir_label or str(directory)).replace("\\", "/"),
        "counts": {
            "paths": len(scanned),
            "covered": len(scanned) - len(uncovered),
            "uncovered": len(uncovered),
            "rule_files": len(rules),
            "rule_files_declaring_paths": sum(1 for r in rules if r["globs"]),
            "rule_files_matching": sum(1 for r in rules if r["matching"]),
            "cases": len(cases),
            **{f"cases_{status}": count
               for status, count in case_counts.items()},
        },
        "rules": rules,
        "cases": cases,
        "uncovered_paths": uncovered,
    }


def dumps_coverage(coverage: dict[str, Any]) -> str:
    """Serialise a report deterministically (stable keys, LF endings)."""
    return json.dumps(coverage, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def write_coverage(coverage: dict[str, Any], out_path: str | os.PathLike[str] | Path) -> Path:
    """Write the report atomically (temp file + replace) beside ``out_path``."""
    destination = Path(out_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = dumps_coverage(coverage)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        dir=str(destination.parent),
        prefix=destination.name + ".",
        suffix=".tmp",
        delete=False,
    )
    try:
        with handle:
            handle.write(payload)
        os.replace(handle.name, destination)
    except BaseException:
        try:
            os.unlink(handle.name)
        except OSError:
            pass
        raise
    return destination


def load_coverage(path: str | os.PathLike[str] | Path) -> dict[str, Any]:
    """Read back a report written by :func:`write_coverage`."""
    try:
        return json.loads(read_text(Path(path)))
    except OSError as exc:
        raise RulesCoverageError(f"cannot read coverage report {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RulesCoverageError(f"coverage report {path} is not valid JSON: {exc}") from exc


# --------------------------------------------------------------------------
# small shared helpers
# --------------------------------------------------------------------------


def read_text(path: Path) -> str:
    """Read a text file BOM-tolerantly (PowerShell writes ``utf-8-sig``)."""
    return path.read_text(encoding="utf-8-sig", errors="replace")


# --------------------------------------------------------------------------
# command line
# --------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m cna.tools.coverage",
        description="Compute which repository paths are governed by the rules corpus.",
    )
    parser.add_argument(
        "--rules",
        default=str(DEFAULT_RULES_DIRNAME),
        help="rules corpus directory (default: %(default)s)",
    )
    parser.add_argument(
        "--src",
        action="append",
        default=list(DEFAULT_SRC_ROOTS),
        dest="src_roots",
        metavar="DIR",
        help="source root to scan (repeatable; default: %(default)s)",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help="output report path (default: %(default)s)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the existing report matches a fresh build; exit 1 on drift",
    )
    parser.add_argument("--quiet", action="store_true", help="suppress the summary line")
    args = parser.parse_args(argv)

    out_path = Path(args.out)
    try:
        paths = iter_source_paths(args.src_roots)
        coverage = build_coverage(args.rules, paths)
    except RulesCoverageError as exc:
        print(f"rules-coverage: error: {exc}", file=sys.stderr)
        return 2

    if args.check:
        if not out_path.is_file():
            print(f"rules-coverage: {out_path} is missing (build it first)", file=sys.stderr)
            return 1
        existing = read_text(out_path)
        if existing != dumps_coverage(coverage):
            print(f"rules-coverage: {out_path} is stale; rebuild it", file=sys.stderr)
            return 1
        if not args.quiet:
            print(f"rules-coverage: {out_path} is up to date")
        return 0

    write_coverage(coverage, out_path)
    if not args.quiet:
        counts = coverage["counts"]
        print(
            "rules-coverage: {covered}/{paths} path(s) covered, {uncovered} uncovered, "
            "{rule_files} rule file(s) ({rule_files_matching} matching) -> {out}".format(
                out=out_path, **counts
            )
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
