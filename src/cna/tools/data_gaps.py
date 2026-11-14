"""Generate and validate the CNA data-gap register.

The proposal requires missing resources to be visible rather than quietly
replaced with invented history.  This tool is the single source of truth for
that register: it renders ``docs/data-gaps.md`` deterministically and can check
that the checked-in file still matches.

It intentionally does not inspect the network or guess whether a resource has
been found.  A resource is marked ``HAVE`` when a closure record in
``docs/sources/intake.json`` validates: the source file is under
``docs/sources/``, its SHA-256 and byte size match, the extraction is under
``data/`` and passes the provenance schema as ``verified``, the second-pass
review is independent, and the evidence pack exists.

The validated record is the single closure step: it promotes the generated
register entry and the P1c.2 gate together.  :data:`GAPS` supplies the baseline
status while a resource is open; a stale ``HAVE`` entry without a valid record
is downgraded to ``UNVERIFIED`` and the command fails.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
import tempfile
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cna.data.schema import DataError, validate_header, validate_table

__all__ = [
    "DEFAULT_OUT",
    "GAPS",
    "INTAKE_PATH",
    "P1C2_RESOURCES",
    "REQUIRED_EVIDENCE",
    "GateResult",
    "IntakeError",
    "IntakeResult",
    "build_gate_report",
    "build_report",
    "load_intake",
    "render_gate_text",
    "render_markdown",
    "validate_intake_entry",
    "write_report",
    "main",
]

DEFAULT_OUT = Path("docs") / "data-gaps.md"

#: The closure-record manifest.  It is absent while every resource is open.
INTAKE_PATH = Path("docs") / "sources" / "intake.json"

#: Evidence named by C-10 of the intake procedure.  Each value in the intake
#: record is a path under ``docs/sources/`` to a non-empty file.
REQUIRED_EVIDENCE = (
    "manifest",
    "extraction_log",
    "validator_output",
    "review_notes",
    "coverage_report",
)

#: Resource gaps from the proposal's missing-resource register.  ``blocks`` is
#: deliberately explicit so an operator can see which phase a missing file
#: actually stops.
GAPS: tuple[dict[str, Any], ...] = (
    {
        "id": "R-02",
        "resource": "Original rules PDF",
        "status": "UNVERIFIED",
        "blocks": ["P1b", "P1c"],
        "reason": "Cross-check OCR and recover the missing §4.21-4.24 pages.",
    },
    {
        "id": "R-03",
        "resource": "SPI Errata, September 1979",
        "status": "UNVERIFIED",
        "blocks": ["P1b", "P1c"],
        "reason": "Official corrections, omitted Italian OA sheets and schedule fixes.",
    },
    {
        "id": "R-04",
        "resource": "Charts and Tables booklets",
        "status": "UNVERIFIED",
        "blocks": ["P1b", "P1c", "P2", "P3"],
        "reason": "Combat, terrain, weather, breakdown, OA, reinforcement and air tables.",
    },
    {
        "id": "R-05",
        "resource": "Map data (five sheets, terrain, hex IDs)",
        "status": "NONE-FOUND as structured data",
        "blocks": ["P1b", "P1c", "P4"],
        "reason": "Map images exist, but no verified structured hex/terrain source.",
    },
    {
        "id": "R-06",
        "resource": "Counter set (unit identities and ratings)",
        "status": "UNVERIFIED",
        "blocks": ["P1b", "P1c", "P4"],
        "reason": "Unit records cannot be populated from official data without the counters.",
    },
    {
        "id": "R-07",
        "resource": "TOE Log Sheet layouts",
        "status": "UNVERIFIED",
        "blocks": ["P1c"],
        "reason": "Field layout for the per-unit digital log sheet.",
    },
    {
        "id": "R-08",
        "resource": "Air Game charts",
        "status": "UNVERIFIED",
        "blocks": ["P3"],
        "reason": "Aircraft characteristics and pilot tables.",
    },
    {
        "id": "R-09",
        "resource": "Logistics Game charts",
        "status": "UNVERIFIED",
        "blocks": ["P2"],
        "reason": "Production, convoy and port-capacity tables.",
    },
)

#: The resources whose closure is the P1c.2 data gate.
P1C2_RESOURCES = ("R-04", "R-05", "R-06")

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class IntakeError(ValueError):
    """Raised when the intake manifest itself cannot be read or parsed."""


@dataclass(frozen=True)
class IntakeResult:
    """The validator's verdict on one closure record.

    ``status`` is ``HAVE`` only when every machine-checkable gate passed.
    ``source`` and ``extraction`` are repo-relative paths for the evidence
    record; they are ``None`` when the record did not name a usable file.
    """

    resource: str
    status: str
    problems: tuple[str, ...] = ()
    source: str | None = None
    extraction: str | None = None

    @property
    def ok(self) -> bool:
        """True when this record may close its resource."""
        return self.status == "HAVE" and not self.problems


@dataclass(frozen=True)
class GateResult:
    """One resource's P1c.2 gate result.

    ``result`` is ``PASS`` only when the register status and the validated
    intake record agree on ``HAVE``; the other fields say which side was
    missing or invalid when it is ``BLOCKED``.
    """

    resource: str
    result: str
    register_status: str
    intake_status: str
    blocker: str = ""

    @property
    def passed(self) -> bool:
        return self.result == "PASS"


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _relative(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:  # pragma: no cover - containment is checked separately
        return str(path)


def _file_under(
    root: Path, raw: Any, directory: str
) -> tuple[Path | None, str | None]:
    """Resolve a manifest path that must live under ``directory``."""
    if not _nonempty_text(raw):
        return None, "is missing a path"
    path = (root / raw).resolve()
    boundary = (root / directory).resolve()
    try:
        path.relative_to(boundary)
    except ValueError:
        return None, f"{raw!r} is outside {directory}/"
    if not path.is_file():
        return None, f"{raw!r} does not exist"
    return path, None


def _string_list(value: Any) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes, bytearray))
        and bool(value)
        and all(_nonempty_text(item) for item in value)
    )


def _validate_extraction(path: Path) -> list[str]:
    """Validate one extracted dataset against the provenance schema."""
    try:
        table = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"extraction {path} cannot be read as JSON: {exc}"]
    if not isinstance(table, Mapping):
        return [f"extraction {path} must be a JSON object"]

    try:
        header = validate_header(table)
        records = validate_table(table)
    except DataError as exc:
        return [f"extraction {path}: {exc}"]

    problems: list[str] = []
    if header.status != "verified":
        problems.append(
            f"extraction {path} status must be 'verified', "
            f"got {header.status!r}"
        )
    if not header.source.startswith(("rulebook:", "chart:")):
        problems.append(
            f"extraction {path} source must cite rulebook:/chart:, "
            f"got {header.source!r}"
        )
    if not records:
        problems.append(f"extraction {path} has no records")
    for index, record in enumerate(records):
        if record["status"] != "verified":
            problems.append(
                f"extraction {path} records[{index}] status must be "
                f"'verified', got {record['status']!r}"
            )
    return problems


def validate_intake_entry(
    resource: str,
    entry: Mapping[str, Any],
    *,
    root: str | Path = ".",
    known_ids: Collection[str] | None = None,
) -> IntakeResult:
    """Validate one closure record against the C-01..C-10 evidence gates.

    Only the machine-checkable gates are enforced here.  A passing result does
    not replace the human review; it proves that the record names real files,
    the checksum matches, the extraction is verified, and the evidence exists.
    """
    base = Path(root).resolve()
    problems: list[str] = []
    if known_ids is None:
        known_ids = {gap["id"] for gap in GAPS}
    if resource not in known_ids:
        problems.append(f"unknown resource {resource!r}; not in the register")

    if not isinstance(entry, Mapping):
        return IntakeResult(
            resource, "UNVERIFIED", ("intake entry must be a mapping",)
        )
    if entry.get("status") != "HAVE":
        problems.append(
            "status must be 'HAVE' for a closure record; open resources "
            "stay open"
        )

    source_path: Path | None = None
    source = entry.get("source")
    if not isinstance(source, Mapping):
        problems.append("source must be a mapping (C-01/C-02)")
        source = {}
    else:
        for field in ("title", "edition", "copy"):
            if not _nonempty_text(source.get(field)):
                problems.append(f"source.{field} must be a non-empty string")
        if not _string_list(source.get("identifiers")):
            problems.append(
                "source.identifiers must be a non-empty list of strings"
            )

        source_path, error = _file_under(
            base, source.get("path"), "docs/sources"
        )
        if error:
            problems.append(f"source.path {error}")
        digest = source.get("sha256")
        if not isinstance(digest, str) or not _SHA256.match(digest):
            problems.append(
                "source.sha256 must be a lowercase SHA-256 hex digest"
            )
            digest = None
        size = source.get("bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            problems.append("source.bytes must be a non-negative integer")
            size = None
        if source_path is not None:
            try:
                actual = hashlib.sha256(source_path.read_bytes()).hexdigest()
            except OSError as exc:
                problems.append(f"source {source_path} cannot be read: {exc}")
            else:
                if digest is not None and actual != digest:
                    problems.append(
                        f"source.sha256 does not match {source_path}: "
                        f"expected {digest}, got {actual}"
                    )
                if size is not None and source_path.stat().st_size != size:
                    problems.append(
                        f"source.bytes does not match {source_path}: "
                        f"expected {size}, got {source_path.stat().st_size}"
                    )

    if not _nonempty_text(entry.get("authorization")):
        problems.append(
            "authorization must record the operator's placement/authorization "
            "(C-03)"
        )
    if entry.get("identifiers_stable") is not True:
        problems.append("identifiers_stable must be true (C-08)")

    extraction_path: Path | None = None
    performed_by: Any = None
    extraction = entry.get("extraction")
    if not isinstance(extraction, Mapping):
        problems.append("extraction must be a mapping (C-04)")
    else:
        performed_by = extraction.get("performed_by")
        for field in ("method", "tool", "performed_by"):
            if not _nonempty_text(extraction.get(field)):
                problems.append(
                    f"extraction.{field} must be a non-empty string"
                )
        if not _string_list(extraction.get("pages")):
            problems.append(
                "extraction.pages must be a non-empty list of source pages"
            )
        extraction_path, error = _file_under(
            base, extraction.get("path"), "data"
        )
        if error:
            problems.append(f"extraction.path {error}")
        elif extraction_path is not None:
            problems.extend(_validate_extraction(extraction_path))

    review = entry.get("review")
    if not isinstance(review, Mapping):
        problems.append("review must be a mapping (C-05)")
    else:
        reviewer = review.get("performed_by")
        if not _nonempty_text(reviewer):
            problems.append("review.performed_by must be a non-empty string")
        elif (
            _nonempty_text(performed_by)
            and reviewer.strip() == performed_by.strip()
        ):
            problems.append(
                "review.performed_by must differ from "
                "extraction.performed_by (C-05)"
            )
        if review.get("second_pass") is not True:
            problems.append("review.second_pass must be true (C-05)")
        conflicts = review.get("conflicts")
        if not isinstance(conflicts, Sequence) or isinstance(
            conflicts, (str, bytes, bytearray)
        ):
            problems.append("review.conflicts must be a list")
        else:
            for index, conflict in enumerate(conflicts):
                if not isinstance(conflict, Mapping) or not _nonempty_text(
                    conflict.get("resolution")
                ):
                    problems.append(
                        f"review.conflicts[{index}] must record a resolution"
                    )

    evidence = entry.get("evidence")
    if not isinstance(evidence, Mapping):
        problems.append(
            "evidence must be a mapping of the C-10 evidence pack"
        )
    else:
        for key in REQUIRED_EVIDENCE:
            path, error = _file_under(base, evidence.get(key), "docs/sources")
            if error:
                problems.append(f"evidence.{key} {error}")
            elif path is not None and path.stat().st_size == 0:
                problems.append(f"evidence.{key} {path} is empty")

    status = "HAVE" if not problems else "UNVERIFIED"
    return IntakeResult(
        resource=resource,
        status=status,
        problems=tuple(problems),
        source=None if source_path is None else _relative(source_path, base),
        extraction=(
            None
            if extraction_path is None
            else _relative(extraction_path, base)
        ),
    )


def load_intake(
    path: str | Path = INTAKE_PATH, *, root: str | Path = "."
) -> dict[str, IntakeResult]:
    """Load and validate the closure manifest, keyed by resource id.

    A missing manifest means no resource has been closed; it is not an error.
    A malformed manifest is an error because silently ignoring it could hide a
    closure claim.
    """
    base = Path(root).resolve()
    manifest = Path(path)
    if not manifest.is_absolute():
        manifest = base / manifest
    if not manifest.exists():
        return {}

    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntakeError(
            f"cannot read intake manifest {manifest}: {exc}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise IntakeError(f"{manifest} must be a JSON object")
    if payload.get("schema_version") != 1:
        raise IntakeError(
            f"{manifest} schema_version must be 1, "
            f"got {payload.get('schema_version')!r}"
        )
    resources = payload.get("resources")
    if not isinstance(resources, Mapping):
        raise IntakeError(
            f"{manifest} must contain a 'resources' mapping"
        )

    return {
        str(resource): validate_intake_entry(
            str(resource), entry, root=base
        )
        for resource, entry in resources.items()
    }


def _resolve_status(
    entry: Mapping[str, Any], result: IntakeResult | None
) -> tuple[str, list[str]]:
    """Apply the closure rule: a validated intake record closes the resource.

    The static register entry is the baseline while a resource is open.  A
    validated record promotes it to ``HAVE`` in the same render, so the
    register, ``docs/data-gaps.md`` and the P1c.2 gate close in one step.  A
    stale ``HAVE`` entry without a valid record is downgraded.
    """
    registered = entry["status"] == "HAVE"
    validated = result is not None and result.ok
    if validated:
        return "HAVE", []
    if registered:
        detail = (
            "; ".join(result.problems)
            if result is not None
            else "no intake record"
        )
        return "UNVERIFIED", [
            f"{entry['id']}: register says HAVE but intake validation "
            f"failed: {detail}"
        ]
    return entry["status"], []


def build_report(
    *,
    intake: Mapping[str, IntakeResult] | None = None,
    entries: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a fresh, deterministic gap register.

    ``intake`` holds validated closure records.  Without it the static
    register is unchanged.  A validated record closes its resource in one
    step: the rendered status becomes ``HAVE`` and the gap count falls.  A
    static ``HAVE`` entry with no valid record is downgraded and reported in
    ``problems``.
    """
    source_entries = GAPS if entries is None else entries
    results: Mapping[str, IntakeResult] = {} if intake is None else intake
    gaps: list[dict[str, Any]] = []
    problems: list[str] = []
    for entry in source_entries:
        gap = dict(entry)
        gap["blocks"] = list(entry["blocks"])
        status, issues = _resolve_status(entry, results.get(entry["id"]))
        gap["status"] = status
        gaps.append(gap)
        problems.extend(issues)
    return {
        "source": "docs/sources/proposal-cfna-game-v1.md §3.2",
        "gaps": gaps,
        "open_count": sum(1 for gap in gaps if gap["status"] != "HAVE"),
        "problems": problems,
    }


def build_gate_report(
    *,
    intake: Mapping[str, IntakeResult] | None = None,
    entries: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return the P1c.2 gate derived from the validated closure records.

    A resource is ``PASS`` when its intake record validates.  The same record
    promotes the register entry to ``HAVE`` in :func:`build_report`, so the
    register status and the gate close in one step instead of leaving two
    independently maintained results.  A static ``HAVE`` entry with an
    invalid record is downgraded to ``UNVERIFIED``.
    """
    register = build_report(intake=intake, entries=entries)
    gaps_by_id = {gap["id"]: gap for gap in register["gaps"]}
    results_by_id: Mapping[str, IntakeResult] = {} if intake is None else intake
    resources: list[GateResult] = []
    for resource in P1C2_RESOURCES:
        gap = gaps_by_id.get(resource)
        if gap is None:
            resources.append(
                GateResult(
                    resource=resource,
                    result="BLOCKED",
                    register_status="ABSENT",
                    intake_status="missing",
                    blocker=f"{resource} is not in the register",
                )
            )
            continue

        record = results_by_id.get(resource)
        if record is not None and record.ok:
            resources.append(
                GateResult(
                    resource=resource,
                    result="PASS",
                    register_status=gap["status"],
                    intake_status="valid",
                )
            )
            continue

        if record is None:
            intake_status = "missing"
            blocker = f"no intake record; register status {gap['status']}"
        else:
            intake_status = "invalid"
            blocker = "; ".join(record.problems) or (
                f"intake status {record.status}"
            )
        resources.append(
            GateResult(
                resource=resource,
                result="BLOCKED",
                register_status=gap["status"],
                intake_status=intake_status,
                blocker=blocker,
            )
        )

    closed = sum(1 for item in resources if item.passed)
    return {
        "scope": "P1c.2",
        "resources": resources,
        "status": (
            "PASS"
            if resources and closed == len(P1C2_RESOURCES)
            else "BLOCKED"
        ),
        "closed": closed,
        "total": len(P1C2_RESOURCES),
        "problems": register["problems"],
    }


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def render_markdown(report: dict[str, Any]) -> str:
    """Render a gap report as Markdown with LF line endings."""
    lines = [
        "# CNA data gaps",
        "",
        "<!-- Generated by `python -m cna.tools.data_gaps`; do not edit by hand. -->",
        "",
        "Missing official resources are recorded here and never replaced with",
        "fabricated historical data. Synthetic fixtures are labelled `synthetic`",
        "and are kept separate from rulebook data.",
        "",
        "Source: " + _cell(str(report["source"])),
        "",
        f"Open gaps: **{int(report['open_count'])}**",
        "",
        "| ID | Resource | Status | Blocks | Why it matters |",
        "|---|---|---|---|---|",
    ]
    for gap in report["gaps"]:
        blocks = ", ".join(gap["blocks"])
        lines.append(
            "| {id} | {resource} | {status} | {blocks} | {reason} |".format(
                id=_cell(gap["id"]),
                resource=_cell(gap["resource"]),
                status=_cell(gap["status"]),
                blocks=_cell(blocks),
                reason=_cell(gap["reason"]),
            )
        )
    lines.extend(
        [
            "",
            "## Policy",
            "",
            "1. The engine refuses to start a rulebook scenario when required data",
            "   has status `placeholder`, unless `--allow-placeholder` is supplied.",
            "2. Tests use `synthetic` fixtures and never mix them with real data.",
            "3. Placing an official resource in `docs/sources/` is the operator's",
            "   authorisation to use it; it must then be reviewed and labelled.",
            "4. A phase stays incomplete while any gap in its `Blocks` column is open.",
            "5. A validated intake record (`docs/sources/intake.json`) closes a",
            "   resource: it marks the register `HAVE` and moves the P1c.2 gate",
            "   in one step. Run `python -m cna.tools.data_gaps --validate-intake`.",
            "",
        ]
    )
    return "\n".join(lines)


def render_gate_text(report: Mapping[str, Any]) -> str:
    """Render a P1c.2 gate report as one line per resource plus a total."""
    lines: list[str] = []
    for item in report["resources"]:
        if item.passed:
            lines.append(
                f"p1c2-gate: {item.resource} PASS "
                "(register HAVE, intake validated)"
            )
        else:
            lines.append(
                f"p1c2-gate: {item.resource} BLOCKED "
                f"(register {item.register_status}, intake "
                f"{item.intake_status}): {item.blocker}"
            )
    lines.append(
        f"p1c2-gate: P1c.2 data gate {report['status']} "
        f"({report['closed']}/{report['total']} resources closed)"
    )
    return "\n".join(lines)


def _write_atomic(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        dir=str(path.parent),
        prefix=path.name + ".",
        suffix=".tmp",
        delete=False,
    )
    try:
        with handle:
            handle.write(payload)
        Path(handle.name).replace(path)
    except BaseException:
        try:
            Path(handle.name).unlink()
        except OSError:
            pass
        raise


def write_report(
    path: str | Path = DEFAULT_OUT,
    *,
    intake: Mapping[str, IntakeResult] | None = None,
) -> Path:
    """Write the current register to ``path`` and return it."""
    destination = Path(path)
    _write_atomic(destination, render_markdown(build_report(intake=intake)))
    return destination


def _manifest_root(manifest: Path, fallback: Path) -> Path:
    """Return the repository root a default manifest location implies.

    Records store repository-relative paths, so an absolute ``--intake`` path
    under ``docs/sources/`` must resolve them against that checkout rather
    than against the process working directory.
    """
    parent = manifest.parent
    if parent.name == "sources" and parent.parent.name == "docs":
        return parent.parent.parent
    return fallback


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m cna.tools.data_gaps",
        description="Render or check the CNA data-gap register.",
    )
    parser.add_argument(
        "--out", default=str(DEFAULT_OUT), help="register path (default: %(default)s)"
    )
    parser.add_argument(
        "--intake",
        default=str(INTAKE_PATH),
        help="closure-record manifest (default: %(default)s)",
    )
    parser.add_argument(
        "--validate-intake",
        action="store_true",
        help="validate closure records only; do not write the register",
    )
    parser.add_argument(
        "--gate",
        action="store_true",
        help=(
            "report the P1c.2 R-04/R-05/R-06 gate; exit 1 unless all "
            "three resources close"
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the existing register is current; exit 1 on drift",
    )
    args = parser.parse_args(argv)
    destination = Path(args.out)
    cwd = Path.cwd()
    manifest = Path(args.intake)
    manifest_path = manifest if manifest.is_absolute() else cwd / manifest
    root = _manifest_root(manifest_path, cwd)

    if args.intake != str(INTAKE_PATH) and not manifest_path.is_file():
        print(
            f"data-gaps: cannot read intake manifest {manifest_path}",
            file=sys.stderr,
        )
        return 2

    try:
        results = load_intake(manifest_path, root=root)
    except IntakeError as exc:
        print(f"data-gaps: {exc}", file=sys.stderr)
        return 2

    problems: list[str] = []
    for resource, result in sorted(results.items()):
        if result.ok:
            print(
                f"data-gaps: {resource} intake validates "
                f"(source {result.source}, extraction {result.extraction})"
            )
        else:
            problems.append(f"{resource}: {'; '.join(result.problems)}")
            for problem in result.problems:
                print(
                    f"data-gaps: {resource} intake: {problem}",
                    file=sys.stderr,
                )

    report = build_report(intake=results)
    for problem in report["problems"]:
        print(f"data-gaps: {problem}", file=sys.stderr)
        problems.append(problem)
    if args.gate:
        gate = build_gate_report(intake=results)
        print(render_gate_text(gate))
        return 0 if gate["status"] == "PASS" else 1
    if problems:
        return 1
    if args.validate_intake:
        if results:
            print(f"data-gaps: {len(results)} intake record(s) validated")
        else:
            print("data-gaps: no intake records; no resource is closed")
        return 0

    expected = render_markdown(report)
    if args.check:
        try:
            actual = destination.read_text(encoding="utf-8-sig")
        except OSError as exc:
            print(f"data-gaps: cannot read {destination}: {exc}", file=sys.stderr)
            return 1
        if actual != expected:
            print(f"data-gaps: {destination} is stale; rebuild it", file=sys.stderr)
            diff = difflib.unified_diff(
                actual.splitlines(),
                expected.splitlines(),
                fromfile=str(destination),
                tofile="fresh register",
                lineterm="",
            )
            for line in list(diff)[:40]:
                print(line, file=sys.stderr)
            return 1
        print(f"data-gaps: {destination} is up to date")
        return 0

    try:
        write_report(destination, intake=results)
    except OSError as exc:
        print(f"data-gaps: cannot write {destination}: {exc}", file=sys.stderr)
        return 2
    print(f"data-gaps: wrote {destination} ({report['open_count']} open gaps)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
