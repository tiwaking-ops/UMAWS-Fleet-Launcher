"""Rules indexer for the CNA digital edition.

Scans the vendored rules corpus (``docs/rules/`` by default) and writes
``docs/rules/index.json`` describing four things:

* **sections** — the heading tree of every document, with an outline number
  (``2.1``), the 1-based source line, an anchor id and a GitHub-style slug;
* **case anchors** — the citable targets.  An anchor is either explicit
  (``<a id="...">``, a pandoc ``{#id}`` attribute), an outline-numbered or
  slugged heading, a rule id (``R-02``) or a case id (``Case 4.1``);
* **xrefs** — every cross-reference in running text (``see §4.2``, ``R-02``,
  ``Case 4.1``, ``[label](#anchor)``, ``[label](other.md#anchor)``), each
  marked resolved or unresolved against the anchor table;
* **tables** — pipe tables, with their header cells, data rows and the
  section that owns them.

Design notes
------------
* Standard library only; Windows-native (BOM-tolerant reads, atomic replace).
* Deterministic: the same corpus always yields byte-identical JSON, so the
  index can be diffed, hashed and regenerated at will.  No timestamps.
* Nothing inside a fenced code block is treated as a heading, anchor,
  cross-reference or table.
* An id only becomes an *anchor* where it is **defined**: in a heading, or in a
  list item — a bullet, or any ordered marker — whose first token is the id and
  which continues with a colon, a dash or nothing at all.  Every other
  occurrence, including an id in a table cell, is a cross-reference.
* Text in the corpus is data.  Nothing here executes, imports or follows
  instructions found in the rules files.

Usage::

    python -m cna.tools.rules_index                 # docs/rules -> docs/rules/index.json
    python -m cna.tools.rules_index --rules X --out Y
    python -m cna.tools.rules_index --check         # drift check, exit 1 on mismatch
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Sequence

__all__ = [
    "SCHEMA_VERSION",
    "DEFAULT_RULES_DIRNAME",
    "INDEX_FILENAME",
    "RulesIndexError",
    "build_index",
    "write_index",
    "load_index",
    "index_bytes",
    "main",
]

SCHEMA_VERSION = 1
DEFAULT_RULES_DIRNAME = Path("docs") / "rules"
INDEX_FILENAME = "index.json"
MANIFEST_FILENAME = "manifest.json"
CHECKSUM_FILENAME = "checksums.sha256"


class RulesIndexError(RuntimeError):
    """Raised for operator errors: a missing corpus, unreadable output."""


# --------------------------------------------------------------------------
# scanning primitives
# --------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
_ATX_RE = re.compile(r"^(?P<hashes>#{1,6})[ \t]+(?P<text>.+?)[ \t]*#*[ \t]*$")
_ADOC_HEADING_RE = re.compile(r"^(?P<hashes>={1,6})[ \t]+(?P<text>.+?)\s*$")
_ADOC_ANCHOR_ATTR_RE = re.compile(r"^\[#(?P<id>[^\]]+)\]\s*$")
_OUTLINE_RE = re.compile(r"^(?P<num>\d+(?:\.\d+)*)[.)]?[ \t]+(?P<rest>.*)$")
_SEP_RE = re.compile(r"^[ \t]*\|?[ \t]*:?-{1,}:?[ \t]*(?:\|[ \t]*:?-{1,}:?[ \t]*)*\|?[ \t]*$")
_HTML_ANCHOR_RE = re.compile(r"""<a\s+(?:id|name)\s*=\s*(?P<q>["'])(?P<id>[^"']+)(?P=q)\s*>""", re.I)
_PANDOC_ANCHOR_RE = re.compile(r"\{#(?P<id>[A-Za-z0-9_.:\-]+)\}\s*$")
_RULE_ID_RE = re.compile(r"(?<![\w/.-])R-(?P<num>\d{1,4})(?!\.?\d)(?![\w-])")
_CASE_ID_RE = re.compile(r"(?<![\w-])[Cc]ase\s+(?P<num>\d+(?:[.\-]\d+)*|[A-Za-z]\d+)")
_SECTION_REF_RE = re.compile(r"§{1,2}\s*(?P<num>\d+(?:[.\-][0-9A-Za-z]+)*)")
_LINK_RE = re.compile(r"\[(?P<label>[^\]]*)\]\((?P<target>[^)\s]+)(?:\s+\"[^\"]*\")?\)")


def read_text(path: Path) -> str:
    """Read a text file BOM-tolerantly (PowerShell writes ``utf-8-sig``)."""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def slugify(text: str) -> str:
    """GitHub-style slug for a heading: lower case, word chars and hyphens."""
    base = " ".join(text.split()).lower()
    base = re.sub(r"[^\w\- ]+", "", base, flags=re.UNICODE)
    slug = re.sub(r"[ ]+", "-", base.strip())
    return slug or "section"


def _frontmatter_range(lines: Sequence[str]) -> tuple[int, int]:
    """Return the inclusive 1-based line range of YAML frontmatter, or (0, 0)."""
    if not lines or lines[0].strip() not in ("---", "---\t"):
        return (0, 0)
    for idx in range(1, min(len(lines), 500)):
        if lines[idx].strip() in ("---", "..."):
            return (1, idx + 1)
    return (0, 0)


def _code_line_numbers(lines: Sequence[str]) -> set[int]:
    """1-based line numbers that live inside a fenced code block."""
    inside: set[int] = set()
    fence_char = ""
    fence_len = 0
    for number, raw in enumerate(lines, start=1):
        match = _FENCE_RE.match(raw)
        if fence_char:
            inside.add(number)
            if (
                match
                and match.group("fence")[0] == fence_char
                and len(match.group("fence")) >= fence_len
                and not match.group("info").strip()
            ):
                fence_char, fence_len = "", 0
        elif match:
            inside.add(number)
            fence_char = match.group("fence")[0]
            fence_len = len(match.group("fence"))
    return inside


def _split_row(line: str) -> list[str]:
    """Split one pipe-table row into cells, honouring ``\\|`` escapes."""
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    cells = re.split(r"(?<!\\)\|", body)
    return [cell.replace("\\|", "|").strip() for cell in cells]


# --------------------------------------------------------------------------
# anchor keys
# --------------------------------------------------------------------------


def _key_candidates(text: str) -> list[str]:
    """Every lookup key an id or reference may answer to, most specific first."""
    base = " ".join(text.split()).strip().lower().lstrip("#")
    seen: list[str] = []
    for candidate in (base, base.replace(" ", "-"), base.replace("_", "-")):
        candidate = candidate.strip()
        if not candidate:
            continue
        if candidate not in seen:
            seen.append(candidate)
        match = re.fullmatch(r"r-(?P<num>\d+)", candidate)
        if match:
            number = int(match.group("num"))
            for variant in (f"r-{number}", f"r-{number:02d}", f"r-{number:03d}"):
                if variant not in seen:
                    seen.append(variant)
    return seen


def _is_definition(line: str, start: int, end: int, *, is_heading: bool) -> bool:
    """Is this occurrence of an id its definition rather than a reference?"""
    if is_heading:
        return True
    prefix = line[:start]
    if not re.fullmatch(r"\s*(?:[-*+]\s+|\d+[.)]\s+)?(?:\*\*|__)?\s*", prefix):
        return False
    rest = line[end:]
    return bool(re.match(r"^(?:\*\*|__)?\s*(?::|—|–|--|\||$)", rest))


# --------------------------------------------------------------------------
# per-document indexing
# --------------------------------------------------------------------------


def _index_document(path: Path, relative: str, raw: bytes) -> dict[str, Any]:
    """Index one Markdown document.  Resolution happens later (corpus-wide)."""
    text = raw.decode("utf-8-sig", errors="replace")
    lines = text.splitlines()
    code = _code_line_numbers(lines)
    fm_start, fm_end = _frontmatter_range(lines)

    document: dict[str, Any] = {
        "path": relative,
        "sha256": sha256_hex(raw),
        "bytes": len(raw),
        "lines": len(lines),
        "title": None,
        "frontmatter": {},
        "sections": [],
        "anchors": [],
        "xrefs": [],
        "tables": [],
    }
    document["frontmatter"] = _parse_frontmatter(lines[fm_start:fm_end] if fm_end else [])

    counters: dict[int, int] = {}
    stack: list[dict[str, Any]] = []  # open sections, outermost first
    current: dict[str, Any] | None = None
    warnings: list[str] = []
    pending_adoc_anchor: str | None = None

    number = 0
    index = -1
    while True:
        index += 1
        if index >= len(lines):
            break
        number = index + 1
        if fm_start <= number <= fm_end and fm_end:
            continue
        line = lines[index]
        if number in code:
            continue

        adoc_anchor = _ADOC_ANCHOR_ATTR_RE.match(line)
        if adoc_anchor:
            pending_adoc_anchor = adoc_anchor.group("id")
            continue

        heading = _ATX_RE.match(line)
        adoc_heading = _ADOC_HEADING_RE.match(line)
        if heading or adoc_heading:
            if adoc_heading and not heading:
                level = len(adoc_heading.group("hashes"))
                title = adoc_heading.group("text").strip()
                pandoc = None
                explicit_slug = pending_adoc_anchor
            else:
                level = len(heading.group("hashes"))
                title = heading.group("text").strip()
                pandoc = _PANDOC_ANCHOR_RE.search(title)
                explicit_slug = pandoc.group("id") if pandoc else None
                if pandoc:
                    title = title[: pandoc.start()].strip()
            pending_adoc_anchor = None
            counters[level] = counters.get(level, 0) + 1
            for deeper in list(counters):
                if deeper > level:
                    counters.pop(deeper)
            outline = ".".join(str(counters[depth]) for depth in sorted(counters) if depth <= level)
            outline_match = _OUTLINE_RE.match(title)
            if outline_match:
                primary = outline_match.group("num")
                display = outline_match.group("rest").strip() or title
            else:
                primary = explicit_slug or slugify(title)
                display = title
            node = {
                "level": level,
                "number": outline,
                "title": display,
                "line": number,
                "anchor": primary,
                "slug": slugify(title),
                "children": [],
            }
            while stack and stack[-1]["level"] >= level:
                stack.pop()
            if stack:
                stack[-1]["children"].append(node)
            else:
                document["sections"].append(node)
            stack.append(node)
            current = node
            if document["title"] is None:
                document["title"] = display
            if explicit_slug:
                _add_anchor(
                    document, warnings, id=explicit_slug, kind="explicit",
                    line=number, section=node, text=display,
                )
            if not explicit_slug or explicit_slug.lower() != primary.lower():
                _add_anchor(
                    document, warnings, id=primary, kind="section",
                    line=number, section=node, text=display,
                )
            if node["slug"].lower() not in (primary.lower(), ""):
                _add_anchor(
                    document, warnings, id=node["slug"], kind="section-slug",
                    line=number, section=node, text=display,
                )
            for match in _RULE_ID_RE.finditer(display):
                _add_anchor(
                    document, warnings, id=f"R-{match.group('num')}", kind="rule",
                    line=number, section=node, text=display,
                )
            for match in _CASE_ID_RE.finditer(display):
                _add_anchor(
                    document, warnings,
                    id=f"case-{match.group('num').lower()}", kind="case",
                    line=number, section=node, text=display,
                )
            continue

        # Gather everything this line mentions, then emit it in source order so
        # a consumer can replay the line left to right.
        events: list[tuple[int, str, dict[str, Any]]] = []

        # explicit HTML anchors anywhere in ordinary text
        for anchor in _HTML_ANCHOR_RE.finditer(line):
            events.append(
                (
                    anchor.start(),
                    "anchor",
                    {"id": anchor.group("id"), "kind": "explicit", "text": anchor.group(0)},
                )
            )

        # rule ids: R-02 and friends
        for match in _RULE_ID_RE.finditer(line):
            rule_id = f"R-{match.group('num')}"
            if _is_definition(line, match.start(), match.end(), is_heading=False):
                events.append(
                    (
                        match.start(),
                        "anchor",
                        {"id": rule_id, "kind": "rule", "text": line.strip()},
                    )
                )
            else:
                events.append(
                    (
                        match.start(),
                        "xref",
                        {"kind": "rule", "raw": match.group(0), "target": rule_id},
                    )
                )

        # case ids: Case 4.1 / case 12
        for match in _CASE_ID_RE.finditer(line):
            case_id = f"case-{match.group('num').lower()}"
            if _is_definition(line, match.start(), match.end(), is_heading=False):
                events.append(
                    (
                        match.start(),
                        "anchor",
                        {"id": case_id, "kind": "case", "text": line.strip()},
                    )
                )
            else:
                events.append(
                    (
                        match.start(),
                        "xref",
                        {"kind": "case", "raw": match.group(0), "target": case_id},
                    )
                )

        # outline references: see §4.2
        for match in _SECTION_REF_RE.finditer(line):
            events.append(
                (
                    match.start(),
                    "xref",
                    {
                        "kind": "section",
                        "raw": match.group(0),
                        "target": match.group("num"),
                    },
                )
            )

        # markdown links to anchors elsewhere in the corpus
        for match in _LINK_RE.finditer(line):
            target = match.group("target")
            payload: dict[str, Any] = {
                "kind": "link",
                "raw": match.group(0),
                "target": target,
            }
            if target.startswith("#"):
                payload["target"] = target[1:]
            elif ".md#" in target:
                doc_name, _, anchor = target.partition("#")
                payload["target"] = anchor
                payload["document_hint"] = doc_name
            elif target.lower().endswith(".md"):
                payload["document_hint"] = target
            else:
                continue
            events.append((match.start(), "xref", payload))

        for _, what, payload in sorted(events, key=lambda event: event[0]):
            if what == "anchor":
                _add_anchor(
                    document, warnings, line=number, section=current, **payload
                )
            else:
                _add_xref(document, line=number, section=current, **payload)

    document["tables"] = _index_tables(lines, fm_end, document["sections"])
    document["warnings"] = warnings
    return document


def _parse_frontmatter(block: Iterable[str]) -> dict[str, Any]:
    """Parse the top-level ``key: value`` pairs of frontmatter; nothing else."""
    parsed: dict[str, Any] = {}
    for line in block:
        stripped = line.strip()
        if not stripped or stripped in ("---", "..."):
            continue
        if stripped.startswith("-") or stripped.startswith("#"):
            continue
        key, sep, value = stripped.partition(":")
        if not sep:
            continue
        value = value.strip()
        # Only plain scalars. Lists, nested blocks and quoted values are left
        # to the caller; an empty value means the block below it was skipped.
        if not value or value.startswith(("[", "{", '"', "'")):
            continue
        parsed[key.strip()] = value
    return parsed


def _add_anchor(
    document: dict[str, Any],
    warnings: list[str],
    *,
    id: str,
    kind: str,
    line: int,
    section: dict[str, Any] | None,
    text: str,
) -> None:
    anchor = {
        "id": id,
        "kind": kind,
        "line": line,
        "section": section["number"] if section else None,
        "section_title": section["title"] if section else None,
        "anchor_id": section["anchor"] if section else None,
        "text": " ".join(text.split())[:200],
    }
    for existing in document["anchors"]:
        if existing["id"].lower() == id.lower():
            if existing["line"] == line:
                # The same anchor seen twice on one line: an explicit id and
                # the heading that carries it.  Registering it again is a
                # no-op, not a duplicate.  Warning here produced 382 of the
                # 413 duplicate-anchor warnings in the 66-file corpus.
                return
            warnings.append(
                f"duplicate anchor '{id}' in {document['path']} "
                f"(line {existing['line']} kept, line {line} ignored)"
            )
            return
    document["anchors"].append(anchor)


def _add_xref(
    document: dict[str, Any],
    *,
    kind: str,
    raw: str,
    target: str,
    line: int,
    section: dict[str, Any] | None,
    document_hint: str | None = None,
) -> None:
    document["xrefs"].append(
        {
            "kind": kind,
            "raw": raw,
            "target": " ".join(target.split()),
            "target_document": document_hint,
            "line": line,
            "section": section["number"] if section else None,
            "resolved": None,  # filled in by _resolve_xref
            "resolved_id": None,
            "resolved_document": None,
            "resolved_line": None,
        }
    )


def _index_tables(
    lines: Sequence[str], fm_end: int, sections: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Find every pipe table outside code fences and frontmatter."""
    code = _code_line_numbers(lines)
    tables: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        number = index + 1
        line = lines[index]
        if number in code or number <= fm_end or not line.lstrip().startswith("|"):
            index += 1
            continue
        if index + 1 >= len(lines) or (index + 2) in code:
            index += 1
            continue
        separator = lines[index + 1]
        if (index + 2) in code or not _SEP_RE.match(separator) or "-" not in separator:
            index += 1
            continue
        header = _split_row(line)
        rows: list[list[str]] = []
        end = index + 2
        while end < len(lines) and lines[end].lstrip().startswith("|") and (end + 1) not in code:
            rows.append(_split_row(lines[end]))
            end += 1
        tables.append(
            {
                "line": number,
                "end_line": end,
                "section": _owning_section(sections, number),
                "headers": header,
                "rows": rows,
                "row_count": len(rows),
                "column_count": len(header),
            }
        )
        index = end
    return tables


def _owning_section(sections: Sequence[dict[str, Any]], line: int) -> str | None:
    """The outline number of the last heading that opens at or before ``line``."""
    owner: str | None = None

    def walk(nodes: Sequence[dict[str, Any]]) -> None:
        nonlocal owner
        for node in nodes:
            if node["line"] <= line:
                owner = node["number"]
            walk(node["children"])

    walk(sections)
    return owner


# --------------------------------------------------------------------------
# corpus-level index
# --------------------------------------------------------------------------


def _walk_documents(rules_dir: Path) -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    for path in sorted(set(list(rules_dir.rglob("*.md")) + list(rules_dir.rglob("*.adoc")))):
        if path.name.startswith("."):
            continue
        relative = path.relative_to(rules_dir).as_posix()
        found.append((path, relative))
    return found


def _read_manifest(rules_dir: Path, warnings: list[str]) -> tuple[str | None, dict[str, str]]:
    manifest_path = rules_dir / MANIFEST_FILENAME
    declared: dict[str, str] = {}
    pinned: str | None = None
    if manifest_path.is_file():
        try:
            manifest = json.loads(read_text(manifest_path))
        except (ValueError, OSError) as exc:
            warnings.append(f"unreadable manifest {MANIFEST_FILENAME}: {exc}")
            manifest = {}
        if isinstance(manifest, dict):
            commit = manifest.get("pinned_commit")
            if isinstance(commit, str):
                pinned = commit
            files = manifest.get("files")
            if isinstance(files, dict):
                declared = {str(k): str(v) for k, v in files.items()}
    checksum_path = rules_dir / CHECKSUM_FILENAME
    if checksum_path.is_file():
        try:
            for raw_line in read_text(checksum_path).splitlines():
                parts = raw_line.split()
                if len(parts) >= 2 and len(parts[0]) == 64:
                    declared[parts[-1].replace("\\", "/")] = parts[0]
        except OSError as exc:  # pragma: no cover - defensive
            warnings.append(f"unreadable checksums {CHECKSUM_FILENAME}: {exc}")
    return pinned, declared


def index_bytes(raw: bytes, *, name: str = "rules.md") -> dict[str, Any]:
    """Index a single in-memory Markdown document.  Useful for tests."""
    return _index_document(Path(name), name, raw)


def build_index(rules_dir: str | os.PathLike[str] | Path = DEFAULT_RULES_DIRNAME) -> dict[str, Any]:
    """Build the whole index for the corpus under ``rules_dir``."""
    directory = Path(rules_dir)
    if not directory.is_dir():
        raise RulesIndexError(f"rules directory not found: {directory}")

    warnings: list[str] = []
    pinned, declared = _read_manifest(directory, warnings)

    documents: list[dict[str, Any]] = []
    for path, relative in _walk_documents(directory):
        declared_hash = declared.get(relative)
        document = _index_document(path, relative, path.read_bytes())
        if declared_hash:
            document["checksum"] = {
                "declared": declared_hash.lower(),
                "matches": declared_hash.lower() == document["sha256"],
            }
            if not document["checksum"]["matches"]:
                warnings.append(
                    f"checksum mismatch for {relative}: corpus changed since it was vendored"
                )
        else:
            document["checksum"] = None
        documents.append(document)

    # corpus-wide anchor registry: lookup key -> anchor
    registry: dict[str, dict[str, Any]] = {}
    anchors: dict[str, dict[str, Any]] = {}
    for document in documents:
        document_warnings = document.pop("warnings")
        for anchor in document["anchors"]:
            keys = _key_candidates(anchor["id"])
            clash = next((key for key in keys if key in registry), None)
            if clash is not None:
                first = registry[clash]
                warnings.append(
                    f"duplicate anchor '{anchor['id']}' at {document['path']}:{anchor['line']} "
                    f"(already defined at {first['document']}:{first['line']}; first wins)"
                )
                continue
            entry = dict(anchor)
            entry["document"] = document["path"]
            for key in keys:
                registry[key] = entry
            anchors[anchor["id"]] = entry
        warnings.extend(document_warnings)

    xrefs: list[dict[str, Any]] = []
    for document in documents:
        for xref in document["xrefs"]:
            entry = dict(xref)
            entry["document"] = document["path"]
            resolved = _resolve_xref(registry, entry)
            xrefs.append(entry)
            if not resolved:
                warnings.append(
                    f"unresolved xref '{entry['target']}' "
                    f"at {document['path']}:{entry['line']}"
                )

    flat_tables = []
    for document in documents:
        for table in document["tables"]:
            entry = dict(table)
            entry["document"] = document["path"]
            flat_tables.append(entry)

    stats = {
        "documents": len(documents),
        "sections": sum(_count_sections(d["sections"]) for d in documents),
        "anchors": len(anchors),
        "xrefs": len(xrefs),
        "resolved_xrefs": sum(1 for x in xrefs if x["resolved"]),
        "unresolved_xrefs": sum(1 for x in xrefs if not x["resolved"]),
        "tables": len(flat_tables),
        "warnings": len(warnings),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "generator": "src/cna/tools/rules_index.py",
        "source": {
            "rules_dir": _display_path(directory),
            "pinned_commit": pinned,
            "files": [d["path"] for d in documents],
        },
        "documents": documents,
        "anchors": anchors,
        "xrefs": xrefs,
        "tables": flat_tables,
        "warnings": warnings,
        "stats": stats,
    }


def _display_path(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(Path.cwd().resolve())
        return relative.as_posix() or "."
    except ValueError:
        return path.as_posix()


def _resolve_xref(registry: dict[str, dict[str, Any]], xref: dict[str, Any]) -> bool:
    target_document = xref.get("target_document")
    entry: dict[str, Any] | None = None
    for key in _key_candidates(xref["target"]):
        entry = registry.get(key)
        if entry is not None:
            break
    if entry is not None and target_document and target_document not in (
        entry["document"],
        Path(entry["document"]).name,
    ):
        entry = None
    if entry is None:
        xref["resolved"] = False
        return False
    xref["resolved"] = True
    xref["resolved_id"] = entry["id"]
    xref["resolved_document"] = entry["document"]
    xref["resolved_line"] = entry["line"]
    return True


def _count_sections(nodes: Sequence[dict[str, Any]]) -> int:
    return sum(1 + _count_sections(node["children"]) for node in nodes)


# --------------------------------------------------------------------------
# input / output
# --------------------------------------------------------------------------


def dumps_index(index: dict[str, Any]) -> str:
    """Serialise an index deterministically (stable keys, LF endings)."""
    return json.dumps(index, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def write_index(index: dict[str, Any], out_path: str | os.PathLike[str] | Path) -> Path:
    """Write the index atomically (temp file + replace) beside ``out_path``."""
    destination = Path(out_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = dumps_index(index)
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


def load_index(path: str | os.PathLike[str] | Path) -> dict[str, Any]:
    """Read back an index written by :func:`write_index`."""
    return json.loads(read_text(Path(path)))


# --------------------------------------------------------------------------
# command line
# --------------------------------------------------------------------------


def _find_default_rules_dir(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / DEFAULT_RULES_DIRNAME).is_dir():
            return candidate / DEFAULT_RULES_DIRNAME
    return here / DEFAULT_RULES_DIRNAME


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m cna.tools.rules_index",
        description="Index the CNA rules corpus into index.json.",
    )
    parser.add_argument("--rules", default=None, help="rules directory (default: docs/rules)")
    parser.add_argument("--out", default=None, help="output file (default: <rules>/index.json)")
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; fail if the existing index differs from a fresh build",
    )
    parser.add_argument("--quiet", action="store_true", help="print nothing on success")
    args = parser.parse_args(list(argv) if argv is not None else None)

    rules_dir = Path(args.rules) if args.rules else _find_default_rules_dir()
    out_path = Path(args.out) if args.out else rules_dir / INDEX_FILENAME

    try:
        index = build_index(rules_dir)
    except RulesIndexError as exc:
        print(f"rules-index: error: {exc}", file=sys.stderr)
        return 2

    if args.check:
        if not out_path.is_file():
            print(f"rules-index: {out_path} is missing (build it first)", file=sys.stderr)
            return 1
        existing = read_text(out_path)
        if existing != dumps_index(index):
            print(f"rules-index: {out_path} is stale; rebuild it", file=sys.stderr)
            return 1
        if not args.quiet:
            print(f"rules-index: {out_path} is up to date")
        return 0

    write_index(index, out_path)
    if not args.quiet:
        stats = index["stats"]
        print(
            "rules-index: {documents} document(s), {sections} section(s), "
            "{anchors} anchor(s), {tables} table(s), {xrefs} xref(s) "
            "({unresolved} unresolved) -> {out}".format(
                out=out_path,
                unresolved=stats["unresolved_xrefs"],
                **{k: stats[k] for k in ("documents", "sections", "anchors", "tables", "xrefs")},
            )
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
