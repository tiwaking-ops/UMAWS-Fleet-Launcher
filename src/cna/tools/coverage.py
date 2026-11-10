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
* Every parsed section heading (``N.0``) must have an explicit reviewed
  status and a non-empty reason; a new section file cannot silently inherit
  the ``unimplemented`` default.

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
    "6.0": {"status": "not_applicable", "source": "", "tests": [], "reason": "section heading and overview; the operative rule cases are 6.11-6.29"},
    "6.1": {"status": "not_applicable", "source": "", "tests": [], "reason": "structural heading; child rules 6.11-6.17 carry the operative CPA rules"},
    "6.2": {"status": "not_applicable", "source": "", "tests": [], "reason": "structural heading; child rules 6.21-6.29 carry the operative Cohesion rules (6.25 remains partial pending R-04)"},
    "6.3": {"status": "partial", "source": "src/cna/rules/sec06_capability.py", "tests": ["tests/test_capability.py"], "reason": "fixed CP costs are implemented; TEC/CPA-dependent rows await R-04"},
    "6.11": {"status": "implemented", "source": "src/cna/rules/sec06_capability.py", "tests": ["tests/test_capability.py"], "reason": ""},
    "6.12": {"status": "implemented", "source": "src/cna/rules/sec06_capability.py", "tests": ["tests/test_capability.py"], "reason": ""},
    "6.13": {"status": "implemented", "source": "src/cna/rules/sec06_capability.py", "tests": ["tests/test_capability.py"], "reason": ""},
    "6.14": {"status": "implemented", "source": "src/cna/rules/sec06_capability.py", "tests": ["tests/test_capability.py"], "reason": ""},
    "6.15": {"status": "implemented", "source": "src/cna/rules/sec06_capability.py", "tests": ["tests/test_capability.py"], "reason": ""},
    "6.16": {"status": "implemented", "source": "src/cna/rules/sec06_capability.py", "tests": ["tests/test_capability.py"], "reason": ""},
    "6.17": {"status": "implemented", "source": "src/cna/rules/sec06_capability.py", "tests": ["tests/test_capability.py"], "reason": ""},
    "6.21": {"status": "implemented", "source": "src/cna/rules/sec06_capability.py", "tests": ["tests/test_capability.py"], "reason": ""},
    "6.22": {"status": "implemented", "source": "src/cna/rules/sec06_capability.py", "tests": ["tests/test_capability.py"], "reason": ""},
    "6.23": {"status": "implemented", "source": "src/cna/rules/sec06_capability.py", "tests": ["tests/test_capability.py"], "reason": ""},
    "6.24": {"status": "implemented", "source": "src/cna/rules/sec06_capability.py", "tests": ["tests/test_capability.py"], "reason": ""},
    "6.25": {"status": "partial", "source": "src/cna/rules/sec06_capability.py", "tests": ["tests/test_capability.py"], "reason": "Cohesion is supplied; the morale/cohesion modifier table is absent (R-04)"},
    "6.26": {"status": "implemented", "source": "src/cna/rules/sec06_capability.py", "tests": ["tests/test_capability.py"], "reason": ""},
    "6.27": {"status": "implemented", "source": "src/cna/rules/sec06_capability.py", "tests": ["tests/test_capability.py"], "reason": ""},
    "6.28": {"status": "implemented", "source": "src/cna/rules/sec06_capability.py", "tests": ["tests/test_capability.py"], "reason": ""},
    "6.29": {"status": "implemented", "source": "src/cna/rules/sec06_capability.py", "tests": ["tests/test_capability.py"], "reason": ""},
    "8.0": {"status": "partial", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py", "tests/test_transport.py"], "reason": "section overview; rail and off-map transport are implemented in sec08_transport; supply movement is deferred"},
    "8.11": {"status": "partial", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": "movement and CP are implemented; the section 21 Breakdown check is not"},
    "8.12": {"status": "partial", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": "retreat CP is charged; section 21 Breakdown is not implemented"},
    "8.13": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.14": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.15": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.16": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.17": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.18": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.21": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.22": {"status": "partial", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": "movement can repeat and accumulate CP; combat and exploitation procedures are out of scope"},
    "8.23": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.24": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.31": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.32": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.33": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.34": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.35": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.36": {"status": "partial", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": "combat terrain benefits belong to §§11-15; the TEC combat columns are R-04"},
    "8.37": {"status": "partial", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": "TEC interface is implemented; official chart values and limits are absent (R-04)"},
    "8.41": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.42": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.43": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.44": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.45": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.46": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.47": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.7": {"status": "partial", "source": "src/cna/rules/sec08_transport.py", "tests": ["tests/test_transport.py"], "reason": "rail procedure implemented; the printed rail map is caller-supplied (R-05)"},
    "8.71": {"status": "implemented", "source": "src/cna/rules/sec08_transport.py", "tests": ["tests/test_transport.py"], "reason": ""},
    "8.72": {"status": "implemented", "source": "src/cna/rules/sec08_transport.py", "tests": ["tests/test_transport.py"], "reason": ""},
    "8.73": {"status": "implemented", "source": "src/cna/rules/sec08_transport.py", "tests": ["tests/test_transport.py"], "reason": ""},
    "8.74": {"status": "implemented", "source": "src/cna/rules/sec08_transport.py", "tests": ["tests/test_transport.py"], "reason": ""},
    "8.75": {"status": "implemented", "source": "src/cna/rules/sec08_transport.py", "tests": ["tests/test_transport.py"], "reason": ""},
    "8.76": {"status": "implemented", "source": "src/cna/rules/sec08_transport.py", "tests": ["tests/test_transport.py"], "reason": ""},
    "8.77": {"status": "implemented", "source": "src/cna/rules/sec08_transport.py", "tests": ["tests/test_transport.py"], "reason": ""},
    "8.78": {"status": "implemented", "source": "src/cna/rules/sec08_transport.py", "tests": ["tests/test_transport.py"], "reason": ""},
    "8.8": {"status": "partial", "source": "src/cna/rules/sec08_transport.py", "tests": ["tests/test_transport.py"], "reason": "off-map procedure implemented; the Off-Map Distance Chart and map edge are caller-supplied (R-04/R-05)"},
    "8.81": {"status": "implemented", "source": "src/cna/rules/sec08_transport.py", "tests": ["tests/test_transport.py"], "reason": ""},
    "8.82": {"status": "implemented", "source": "src/cna/rules/sec08_transport.py", "tests": ["tests/test_transport.py"], "reason": ""},
    "8.83": {"status": "implemented", "source": "src/cna/rules/sec08_transport.py", "tests": ["tests/test_transport.py"], "reason": ""},
    "8.84": {"status": "partial", "source": "src/cna/rules/sec08_transport.py", "tests": ["tests/test_transport.py"], "reason": "abstract transit and reversal are implemented; official chart values are absent (R-04)"},
    "8.85": {"status": "implemented", "source": "src/cna/rules/sec08_transport.py", "tests": ["tests/test_transport.py"], "reason": ""},
    "8.86": {"status": "implemented", "source": "src/cna/rules/sec08_transport.py", "tests": ["tests/test_transport.py"], "reason": ""},
    "8.87": {"status": "implemented", "source": "src/cna/rules/sec08_transport.py", "tests": ["tests/test_transport.py"], "reason": ""},
    "8.88": {"status": "implemented", "source": "src/cna/rules/sec08_transport.py", "tests": ["tests/test_transport.py"], "reason": ""},
    "8.89": {"status": "partial", "source": "src/cna/rules/sec08_transport.py", "tests": ["tests/test_transport.py"], "reason": "chart interface is implemented; official Off-Map Land Unit Movement Distance Chart values are absent (R-04)"},
    "8.51": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.52": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.53": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.54": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.55": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.61": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.62": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.63": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.64": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.65": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.66": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.67": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.68": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.91": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.92": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "8.94": {"status": "partial", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": "motorized CPA is accepted; retaining it while performing non-vehicle actions is not modelled"},
    "8.98": {"status": "partial", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": "the convoy CPA cap is enforced; involuntary capture is not"},
    "9.0": {"status": "partial", "source": "src/cna/rules/sec09_stacking.py", "tests": ["tests/test_stacking.py"], "reason": "section overview; the 9.4 level chart is absent (R-04)"},
    "9.11": {"status": "implemented", "source": "src/cna/rules/sec09_stacking.py", "tests": ["tests/test_stacking.py"], "reason": ""},
    "9.12": {"status": "implemented", "source": "src/cna/rules/sec09_stacking.py", "tests": ["tests/test_stacking.py"], "reason": ""},
    "9.13": {"status": "implemented", "source": "src/cna/rules/sec09_stacking.py", "tests": ["tests/test_stacking.py"], "reason": ""},
    "9.14": {"status": "implemented", "source": "src/cna/rules/sec09_stacking.py", "tests": ["tests/test_stacking.py"], "reason": ""},
    "9.15": {"status": "implemented", "source": "src/cna/rules/sec09_stacking.py", "tests": ["tests/test_stacking.py"], "reason": ""},
    "9.16": {"status": "implemented", "source": "src/cna/rules/sec09_stacking.py", "tests": ["tests/test_stacking.py"], "reason": ""},
    "9.21": {"status": "implemented", "source": "src/cna/rules/sec09_stacking.py", "tests": ["tests/test_stacking.py"], "reason": ""},
    "9.22": {"status": "partial", "source": "src/cna/rules/sec09_stacking.py", "tests": ["tests/test_stacking.py"], "reason": "the caller supplies the 9.4 Stacking Point-to-level table"},
    "9.23": {"status": "partial", "source": "src/cna/rules/sec09_stacking.py", "tests": ["tests/test_stacking.py"], "reason": "level lookup is caller-supplied; the 9.4 chart is absent"},
    "9.24": {"status": "implemented", "source": "src/cna/rules/sec09_stacking.py", "tests": ["tests/test_stacking.py"], "reason": ""},
    "9.25": {"status": "implemented", "source": "src/cna/rules/sec09_stacking.py", "tests": ["tests/test_stacking.py"], "reason": ""},
    "9.26": {"status": "implemented", "source": "src/cna/rules/sec09_stacking.py", "tests": ["tests/test_stacking.py"], "reason": ""},
    "9.27": {"status": "implemented", "source": "src/cna/rules/sec09_stacking.py", "tests": ["tests/test_stacking.py"], "reason": ""},
    "9.28": {"status": "implemented", "source": "src/cna/rules/sec09_stacking.py", "tests": ["tests/test_stacking.py"], "reason": ""},
    "9.29": {"status": "implemented", "source": "src/cna/rules/sec09_stacking.py", "tests": ["tests/test_stacking.py"], "reason": ""},
    "9.31": {"status": "implemented", "source": "src/cna/rules/sec09_stacking.py", "tests": ["tests/test_stacking.py"], "reason": ""},
    "9.32": {"status": "implemented", "source": "src/cna/rules/sec09_stacking.py", "tests": ["tests/test_stacking.py"], "reason": ""},
    "9.33": {"status": "implemented", "source": "src/cna/rules/sec09_stacking.py", "tests": ["tests/test_stacking.py"], "reason": ""},
    "9.35": {"status": "implemented", "source": "src/cna/rules/sec09_stacking.py", "tests": ["tests/test_stacking.py"], "reason": ""},
    "10.0": {"status": "partial", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": "section overview; the hex grid and terrain predicates are caller-supplied"},
    "10.11": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "10.12": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "10.13": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "10.14": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "10.15": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "10.16": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "10.21": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "10.22": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "10.23": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "10.24": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "10.25": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "10.26": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "10.27": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "10.28": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "10.29": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "10.31": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "10.32": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "10.33": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "10.34": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "10.35": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "10.36": {"status": "implemented", "source": "src/cna/rules/sec10_zoc.py", "tests": ["tests/test_zoc.py"], "reason": ""},
    "21.0": {"status": "partial", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": "section overview; individual cases are reviewed below"},
    "21.1": {"status": "partial", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": "section heading; cases 21.11-21.15 are reviewed individually"},
    "21.2": {"status": "partial", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": "section heading; cases 21.21-21.29 are reviewed individually"},
    "21.3": {"status": "partial", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": "section heading; cases 21.31-21.38 are reviewed individually"},
    "21.4": {"status": "partial", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": "section heading; cases 21.41-21.45 are reviewed individually"},
    "21.5": {"status": "partial", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": "section heading; cases 21.51-21.55 are reviewed individually"},
    "21.6": {"status": "partial", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": "section heading; cases 21.61-21.67 are reviewed individually"},
    "21.11": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": ""},
    "21.12": {"status": "partial", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": "fixed BARs are implemented; tank and SP gun BAR charts are R-04"},
    "21.13": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": ""},
    "21.14": {"status": "partial", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": "truck/armored-car/Recce BARs are fixed; tank and SP gun charts are R-04"},
    "21.15": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "21.21": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": "TEC Breakdown Point values are caller-supplied"},
    "21.22": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "21.23": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "21.24": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "21.25": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py"], "reason": ""},
    "21.26": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py", "tests/test_movement.py"], "reason": ""},
    "21.27": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": ""},
    "21.28": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": ""},
    "21.29": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": ""},
    "21.31": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": ""},
    "21.32": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": ""},
    "21.33": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": ""},
    "21.34": {"status": "partial", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": "procedure is implemented; the official Breakdown Table is R-04"},
    "21.35": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py", "tests/test_movement.py"], "reason": ""},
    "21.36": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": ""},
    "21.37": {"status": "implemented", "source": "src/cna/rules/sec08_movement.py", "tests": ["tests/test_movement.py", "tests/test_breakdown.py"], "reason": ""},
    "21.38": {"status": "partial", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": "the official Breakdown Table is R-04; callers supply the lookup"},
    "21.41": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": ""},
    "21.42": {"status": "partial", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": "marker placement and the broken-down vehicle sheet are not integrated"},
    "21.43": {"status": "partial", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": "truck cargo transfer and un-motorization are not integrated"},
    "21.44": {"status": "partial", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": "capability/combat flags exist; broken-down unit state is not yet a game object"},
    "21.45": {"status": "partial", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": "CP costs are implemented; supply/truck transfer is not integrated"},
    "21.51": {"status": "partial", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": "capture of a marker is not integrated with movement"},
    "21.52": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": ""},
    "21.53": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": ""},
    "21.54": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": ""},
    "21.55": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": ""},
    "21.61": {"status": "partial", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": "towing lifecycle is not integrated with the Repair Stage"},
    "21.62": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": ""},
    "21.63": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": ""},
    "21.64": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": ""},
    "21.65": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": ""},
    "21.66": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": ""},
    "21.67": {"status": "implemented", "source": "src/cna/rules/sec21_breakdown.py", "tests": ["tests/test_breakdown.py"], "reason": ""},
    "2.0": {
        "status": "partial", "source": "src/cna/engine/rulesets.py",
        "tests": ["tests/test_rulesets.py"],
        "reason": "LAND_ABSTRACT is available; Air and Logistics combinations are deferred",
    },
    "3.0": {
        "status": "implemented", "source": "src/cna/core/dice.py",
        "tests": ["tests/test_dice.py"],
        "reason": "glossary heading; terminology is documented while the child definition cases remain unimplemented",
    },
    "5.1": {
        "status": "implemented", "source": "src/cna/rules/sec05_sequence.py",
        "tests": ["tests/test_p1b1_foundation.py"], "reason": "",
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
    "7.15": {
        "status": "implemented", "source": "src/cna/rules/sec07_initiative.py",
        "tests": ["tests/test_p1b1_foundation.py"], "reason": "",
    },
    "7.16": {
        "status": "implemented", "source": "src/cna/rules/sec07_initiative.py",
        "tests": ["tests/test_initiative_weather.py"], "reason": "",
    },
    "29.0": {
        "status": "partial", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"],
        "reason": "section overview; 29.1-29.7 are reviewed below",
    },
    "29.1": {
        "status": "partial", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_initiative_weather.py", "tests/test_weather_effects.py"],
        "reason": "synthetic Weather Table only; the official R-04 table is absent",
    },
    "29.2": {
        "status": "implemented", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"], "reason": "",
    },
    "29.3": {
        "status": "partial", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"],
        "reason": "section heading; 29.31-29.35 are reviewed below",
    },
    "29.4": {
        "status": "partial", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"],
        "reason": "section heading; 29.41-29.47 are reviewed below",
    },
    "29.5": {
        "status": "partial", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"],
        "reason": "section heading; 29.51-29.58 are reviewed below",
    },
    "29.6": {
        "status": "partial", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_initiative_weather.py", "tests/test_weather_effects.py"],
        "reason": "official R-04 Weather Table absent; the synthetic table is caller-supplied",
    },
    "29.7": {
        "status": "partial", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"],
        "reason": "official R-04 Four Weather Location Table absent; the synthetic table is caller-supplied",
    },
    "29.31": {
        "status": "implemented", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"], "reason": "",
    },
    "29.32": {
        "status": "implemented", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"], "reason": "",
    },
    "29.33": {
        "status": "implemented", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"], "reason": "",
    },
    "29.34": {
        "status": "partial", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"],
        "reason": "5% factor implemented; fuel/water ledger integration and rounding remain absent",
    },
    "29.35": {
        "status": "implemented", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"], "reason": "",
    },
    "29.41": {
        "status": "partial", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"],
        "reason": "storm effects implemented; official R-04 location mapping absent, synthetic table used",
    },
    "29.42": {
        "status": "implemented", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"], "reason": "",
    },
    "29.43": {
        "status": "implemented", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"], "reason": "",
    },
    "29.44": {
        "status": "implemented", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"], "reason": "",
    },
    "29.45": {
        "status": "implemented", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"], "reason": "",
    },
    "29.46": {
        "status": "implemented", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"], "reason": "",
    },
    "29.47": {
        "status": "partial", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"],
        "reason": "grounded-aircraft damage remains in §38.5 / the Air Game",
    },
    "29.51": {
        "status": "partial", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"],
        "reason": "rainstorm effects implemented; official R-04 location mapping absent, synthetic table used",
    },
    "29.52": {
        "status": "implemented", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"], "reason": "",
    },
    "29.53": {
        "status": "implemented", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"], "reason": "",
    },
    "29.54": {
        "status": "implemented", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"], "reason": "",
    },
    "29.55": {
        "status": "implemented", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"], "reason": "",
    },
    "29.56": {
        "status": "implemented", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"], "reason": "",
    },
    "29.57": {
        "status": "implemented", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"], "reason": "",
    },
    "29.58": {
        "status": "implemented", "source": "src/cna/rules/sec29_weather.py",
        "tests": ["tests/test_weather_effects.py"], "reason": "",
    },
    "32.0": {"status": "partial", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": "section overview; 32.1-32.9 are implemented for LAND_ABSTRACT; full Logistics and Air remain P2/P3"},
    "32.1": {"status": "partial", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": "section heading; Supply Units 32.11-32.18 are implemented"},
    "32.11": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.12": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.13": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.14": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.15": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.16": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.17": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.18": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.2": {"status": "partial", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": "section heading; expenditure rules 32.21-32.25 are implemented"},
    "32.21": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.22": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.23": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.24": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.25": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.3": {"status": "partial", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": "section heading; supply movement 32.31-32.37 is implemented"},
    "32.31": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.32": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.33": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.34": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.35": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.36": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.37": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.4": {"status": "partial", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": "section heading; availability procedures 32.41-32.45 are implemented; official R-04 tables remain caller-supplied"},
    "32.41": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.42": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.43": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.44": {"status": "partial", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": "planning procedure implemented; the Axis 32.46 table is R-04 caller-supplied"},
    "32.45": {"status": "partial", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": "planning procedure implemented; the Commonwealth 32.47 table is R-04 caller-supplied"},
    "32.46": {"status": "partial", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": "official Axis availability table is R-04 caller-supplied"},
    "32.47": {"status": "partial", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": "official Commonwealth availability table is R-04 caller-supplied"},
    "32.5": {"status": "partial", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": "section heading; Motorization Points 32.51-32.59 are implemented except the R-04 loss chart"},
    "32.51": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.52": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.53": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.54": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.55": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.56": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.57": {"status": "partial", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": "loss procedure implemented; the 32.59 R-04 chart is caller-supplied"},
    "32.58": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.59": {"status": "partial", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": "official Motorization Point loss chart is R-04 caller-supplied"},
    "32.6": {"status": "partial", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": "section heading; convoy rules 32.61-32.66 are implemented except the R-04 bombing chart"},
    "32.61": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.62": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.63": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.64": {"status": "partial", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": "bombing procedure implemented; the 32.66 R-04 chart and Bomb Points table are caller-supplied"},
    "32.65": {"status": "partial", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": "percentage losses implemented; tank/gun nationality distribution is caller-supplied"},
    "32.66": {"status": "partial", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": "official Simple Axis Naval Convoy Bombing Chart is R-04 caller-supplied"},
    "32.7": {"status": "partial", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": "section heading; fleet bombardment 32.71-32.75 is implemented except the R-04 results table"},
    "32.71": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.72": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.73": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.74": {"status": "partial", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": "attack-column and damage procedure implemented; the Air Bombardment results table is R-04 caller-supplied"},
    "32.75": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.8": {"status": "partial", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": "section heading; anti-air modifications 32.81-32.84 are implemented"},
    "32.81": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.82": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.83": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.84": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.9": {"status": "implemented", "source": "src/cna/rules/sec32_abstract.py", "tests": ["tests/test_abstract_supply_air.py"], "reason": ""},
    "32.10": {"status": "not_applicable", "source": "", "tests": [], "reason": "general addenda outside the abstract supply and air rules"},
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


#: P1b cases that are implemented behind a data interface but cannot claim
#: completion while the official R-04/R-05/R-06 resource is absent.  The
#: engine path and its tests exist; the status is partial because the
#: missing chart, map or counter data prevents a real-scenario claim.
P1B_DATA_GAP_GROUPS: tuple[tuple[tuple[str, ...], str], ...] = (
    (('8.17', '8.18', '8.91', '8.92'),
     'unit CPA, truck and motorization values are caller-supplied; the official counter data are absent (R-06)'),
    (('8.24', '8.61', '8.62', '8.63', '8.64', '8.65', '8.66', '8.67', '8.68'),
     'Contact/Engaged and Break Off procedures are implemented; the verified ZOC map, Assault CRT and counter unit data are absent (R-04/R-05/R-06)'),
    (('8.31', '8.32', '8.33', '8.34', '8.35', '8.41', '8.42', '8.43', '8.44', '8.45', '8.46', '8.47'),
     'terrain movement is implemented with caller-supplied values; the official Terrain Effects Chart costs and verified hex/terrain map are absent (R-04/R-05)'),
    (('8.51', '8.52', '8.53', '8.54', '8.55'),
     'reaction is implemented with caller-supplied state; verified ZOC/map data and official counter size/CPA data are absent (R-05/R-06)'),
    (('8.71', '8.72', '8.73', '8.74', '8.75', '8.76', '8.77', '8.78'),
     'rail movement is implemented; the verified rail-line, destroyed-rail and hex map are absent (R-05)'),
    (('8.81', '8.82', '8.83', '8.85', '8.86', '8.87', '8.88'),
     'Tripoli/Tunisia box procedure is implemented; the printed box/hex map, Air Distance Chart and reinforcement/supply tables are absent (R-04/R-05/R-06)'),
    (('9.11', '9.12', '9.13', '9.14', '9.15', '9.16', '9.21', '9.24', '9.25', '9.26', '9.27', '9.28', '9.29', '9.31', '9.32', '9.33', '9.35'),
     'stacking rule is implemented with caller-supplied values; official counter stacking/organization data and the TEC terrain-capacity table are absent (R-06/R-04)'),
    (('10.11', '10.12', '10.13', '10.14', '10.15', '10.26', '10.29'),
     'ZOC unit rule is implemented; official counter types, cohesion and stacking values are absent (R-06)'),
    (('10.16', '10.21', '10.22', '10.23', '10.24', '10.25', '10.27', '10.28', '10.31', '10.32'),
     'ZOC procedure is implemented with caller-supplied state; the verified hex grid, terrain and map-edge data are absent (R-05)'),
    (('10.33', '10.34', '10.35', '10.36'),
     'Holding Off barrage is implemented; the official CRT/barrage tables and verified ZOC map are absent (R-04/R-05)'),
    (('21.11', '21.13', '21.15', '21.21', '21.22', '21.23', '21.24', '21.25', '21.26', '21.27', '21.28', '21.29', '21.31', '21.32', '21.33', '21.35', '21.36', '21.37', '21.41', '21.52', '21.53', '21.54', '21.55', '21.62', '21.63', '21.64', '21.65', '21.66', '21.67'),
     'breakdown procedure is implemented with caller-supplied values; the official Breakdown Table/BAR, TEC terrain points and vehicle counter data are absent (R-04/R-05/R-06)'),
    (('29.2', '29.31', '29.32', '29.33', '29.35', '29.42', '29.43', '29.44', '29.45', '29.46', '29.52', '29.53', '29.54', '29.55', '29.56', '29.57', '29.58'),
     'weather effect is implemented with a synthetic table; the official Weather Table/Four Weather Location Table and verified map-section data are absent (R-04/R-05)'),
    (('32.11', '32.12', '32.13', '32.14', '32.15', '32.16', '32.17', '32.18'),
     'supply-unit rule is implemented; official supply-unit counter values and scenario supply tables are absent (R-04/R-06)'),
    (('32.21', '32.22', '32.23', '32.24', '32.25'),
     'ammunition/fuel expenditure is implemented; the official Ammo and Fuel cost tables are absent (R-04)'),
    (('32.31', '32.32', '32.33', '32.34', '32.35', '32.36', '32.37'),
     'supply transport is implemented; official motorization/truck capacity and coastal-shipping tables are absent (R-04/R-06)'),
    (('32.41', '32.42', '32.43'),
     'supply availability is implemented; the official Axis/Commonwealth availability tables are absent (R-04)'),
    (('32.51', '32.52', '32.53', '32.54', '32.55', '32.56', '32.58'),
     'motorization point rule is implemented; official motorization-loss and truck/counter data are absent (R-04/R-06)'),
    (('32.61', '32.62', '32.63'),
     'naval convoy rule is implemented; the official convoy/bombing tables and supply counter data are absent (R-04/R-06)'),
    (('32.71', '32.72', '32.73', '32.75'),
     'fleet bombardment is implemented; the official bombardment results table and air-unit data are absent (R-04/R-06)'),
    (('32.81', '32.82', '32.83', '32.84'),
     'anti-air modification is implemented; official counter IDs and aircraft/AA unit records are absent (R-06)'),
    (('32.9',),
     'road/track stacking is implemented; the official TEC stacking values and verified road/track map are absent (R-04/R-05)'),
)

P1B_DATA_GAP_REASONS: dict[str, str] = {}
for _cases, _reason in P1B_DATA_GAP_GROUPS:
    P1B_DATA_GAP_REASONS.update({case: _reason for case in _cases})

for _case, _reason in P1B_DATA_GAP_REASONS.items():
    CASE_STATUS[_case] = {
        **CASE_STATUS[_case], "status": "partial", "reason": _reason,
    }


#: Structural headings are navigation, not rule cases.  Their numbered
#: children carry the operative rules, so the headings are explicitly
#: not applicable rather than unimplemented or partial.
STRUCTURAL_HEADING_REASONS: dict[str, str] = {
    "5.0": "section heading; the operative sequence is case 5.2",
    "7.0": "section heading and overview; child cases 7.11-7.16 carry the operative initiative rules",
    "7.1": "structural heading; child cases 7.11-7.16 carry the operative initiative rules",
    "8.0": "section heading and overview; child cases 8.11-8.99 carry the operative movement rules",
    "8.1": "structural heading; child cases 8.11-8.19 carry the operative movement rules",
    "8.2": "structural heading; child cases 8.21-8.25 carry the operative continual-movement rules",
    "8.3": "structural heading; child cases 8.31-8.37 carry the operative terrain rules",
    "8.4": "structural heading; child cases 8.41-8.47 carry the operative special-terrain rules",
    "8.5": "structural heading; child cases 8.51-8.56 carry the operative reaction rules",
    "8.6": "structural heading; child cases 8.61-8.68 carry the operative breaking-off rules",
    "8.7": "structural heading; child cases 8.71-8.78 carry the operative rail-movement rules",
    "8.8": "structural heading; child cases 8.81-8.89 carry the operative Tripoli/Tunisia rules",
    "8.9": "structural heading; child cases 8.91-8.99 carry the operative motorized-unit rules",
    "9.0": "section heading and overview; child cases 9.11-9.35 carry the operative stacking rules",
    "9.1": "structural heading; child cases 9.11-9.16 carry the operative stacking-point rules",
    "9.2": "structural heading; child cases 9.21-9.29 carry the operative unit-equivalence rules",
    "9.3": "structural heading; child cases 9.31-9.35 carry the operative stacking-effects rules",
    "10.0": "section heading and overview; child cases 10.11-10.36 carry the operative ZOC rules",
    "10.1": "structural heading; child cases 10.11-10.16 carry the operative ZOC-unit rules",
    "10.2": "structural heading; child cases 10.21-10.29 carry the operative ZOC-effect rules",
    "10.3": "structural heading; child cases 10.31-10.36 carry the operative holding-off rules",
    "21.0": "section heading and overview; child cases 21.11-21.67 carry the operative breakdown and repair rules",
    "21.1": "structural heading; child cases 21.11-21.15 carry the operative breakdown-eligibility rules",
    "21.2": "structural heading; child cases 21.21-21.29 carry the operative breakdown-occurrence rules",
    "21.3": "structural heading; child cases 21.31-21.38 carry the operative breakdown-determination rules",
    "21.4": "structural heading; child cases 21.41-21.45 carry the operative broken-down-vehicle rules",
    "21.5": "structural heading; child cases 21.51-21.55 carry the operative capture rules",
    "21.6": "structural heading; child cases 21.61-21.67 carry the operative towing rules",
    "29.0": "section heading and overview; child cases 29.1-29.7 carry the operative weather rules",
    "29.3": "structural heading; child cases 29.31-29.35 carry the operative hot-weather rules",
    "29.4": "structural heading; child cases 29.41-29.47 carry the operative sandstorm rules",
    "29.5": "structural heading; child cases 29.51-29.58 carry the operative rainstorm rules",
    "32.0": "section heading and overview; child cases 32.11-32.84 and 32.9 carry the operative abstract supply/air rules",
    "32.1": "structural heading; child cases 32.11-32.18 carry the operative supply-unit rules",
    "32.2": "structural heading; child cases 32.21-32.25 carry the operative supply-expenditure rules",
    "32.3": "structural heading; child cases 32.31-32.37 carry the operative supply-movement rules",
    "32.4": "structural heading; child cases 32.41-32.47 carry the operative supply-availability rules",
    "32.5": "structural heading; child cases 32.51-32.59 carry the operative motorization-point rules",
    "32.6": "structural heading; child cases 32.61-32.66 carry the operative naval-convoy rules",
    "32.7": "structural heading; child cases 32.71-32.75 carry the operative bombardment rules",
    "32.8": "structural heading; child cases 32.81-32.84 carry the operative anti-air rules",
}

for _case, _reason in STRUCTURAL_HEADING_REASONS.items():
    CASE_STATUS[_case] = {
        "status": "not_applicable",
        "source": "",
        "tests": [],
        "reason": _reason,
    }


#: Major section headings that previously fell through to the implicit
#: ``unimplemented`` default.  They are explicit backlog entries: the heading
#: is a navigation node whose child cases are not implemented.  Keeping them
#: here means a new section file fails the coverage build until it is reviewed.
SECTION_HEADING_REASONS: dict[str, str] = {
    "1.0": "section heading; the introduction is narrative and has no implemented rule case",
    "4.0": "section heading; the game-equipment inventory has no implemented case",
    "11.0": "section heading; child combat-system cases remain unimplemented",
    "12.0": "section heading; child barrage cases remain unimplemented",
    "13.0": "section heading; child retreat-before-assault cases remain unimplemented",
    "14.0": "section heading; child anti-armor cases remain unimplemented",
    "15.0": "section heading; child close-assault cases remain unimplemented",
    "16.0": "section heading; child patrol and reconnaissance cases remain unimplemented",
    "17.0": "section heading; child morale cases remain unimplemented",
    "18.0": "section heading; child reserve-status cases remain unimplemented",
    "19.0": "section heading; child organization cases remain unimplemented",
    "20.0": "section heading; child reinforcement and replacement cases remain unimplemented",
    "22.0": "section heading; child repair cases remain unimplemented",
    "23.0": "section heading; child engineer cases remain unimplemented",
    "24.0": "section heading; child construction cases remain unimplemented",
    "25.0": "section heading; child fortification cases remain unimplemented",
    "26.0": "section heading; child minefield cases remain unimplemented",
    "27.0": "section heading; child raider and commando cases remain unimplemented",
    "28.0": "section heading; child POW cases remain unimplemented",
    "30.0": "section heading; child Mediterranean Fleet cases remain unimplemented",
    "31.0": "section heading; the Rommel rules have no implemented case",
    "34.0": "section heading; child aircraft cases remain unimplemented",
    "35.0": "section heading; child ground-support cases remain unimplemented",
    "36.0": "section heading; child air-facility cases remain unimplemented",
    "37.0": "section heading; child flight cases remain unimplemented",
    "38.0": "section heading; child maintenance cases remain unimplemented",
    "39.0": "section heading; child mission cases remain unimplemented",
    "40.0": "section heading; child fighter-combat cases remain unimplemented",
    "41.0": "section heading; child bombing cases remain unimplemented",
    "42.0": "section heading; child non-combat-mission cases remain unimplemented",
    "43.0": "section heading; child Axis and Aegean air-base cases remain unimplemented",
    "44.0": "section heading; child Malta cases remain unimplemented",
    "45.0": "section heading; child air-to-air cases remain unimplemented",
    "46.0": "section heading; child anti-aircraft cases remain unimplemented",
    "49.0": "section heading; child fuel cases remain unimplemented",
    "50.0": "section heading; child ammunition cases remain unimplemented",
    "51.0": "section heading; child stores cases remain unimplemented",
    "52.0": "section heading; child water cases remain unimplemented",
    "53.0": "section heading; child transport cases remain unimplemented",
    "54.0": "section heading; child supply-coordination cases remain unimplemented",
    "55.0": "section heading; child port and supply cases remain unimplemented",
    "56.0": "section heading; child Axis naval cases remain unimplemented",
    "57.0": "section heading; the Commonwealth supply-base rules have no implemented case",
    "59.0": "section heading; child scenario-introduction cases remain unimplemented",
    "60.0": "section heading; child Italian scenario cases remain unimplemented",
    "61.0": "section heading; child Desert Fox scenario cases remain unimplemented",
    "62.0": "section heading; child Crusader scenario cases remain unimplemented",
    "63.0": "section heading; child El Alamein scenario cases remain unimplemented",
    "64.0": "section heading; child North Africa campaign cases remain unimplemented",
    "65.0": "section heading; the conclusion has no executable rule case",
}

for _case, _reason in SECTION_HEADING_REASONS.items():
    CASE_STATUS[_case] = {
        "status": "unimplemented",
        "source": "",
        "tests": [],
        "reason": _reason,
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


def _validate_section_headings(cases: Sequence[dict[str, Any]]) -> None:
    """Require every parsed ``N.0`` heading to have a reviewed status/reason."""
    missing: list[str] = []
    for entry in cases:
        case_id = entry["case"]
        if not case_id.endswith(".0"):
            continue
        review = CASE_STATUS.get(case_id, {})
        if (review.get("status") not in CASE_STATUSES
                or not str(review.get("reason", "")).strip()):
            missing.append(case_id)
    if missing:
        raise RulesCoverageError(
            "section heading(s) lack an explicit reviewed status and reason: "
            + ", ".join(missing)
        )


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
    inventory = case_inventory(directory)
    _validate_section_headings(inventory)
    cases: list[dict[str, Any]] = []
    case_counts = {status: 0 for status in CASE_STATUSES}
    for entry in inventory:
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
