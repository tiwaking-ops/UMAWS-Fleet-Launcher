"""Evidence bundles (pilot v1 section 9.2).

A bundle is what "done" means.  Constitution point 3: *"Done means an
evidence bundle: outputs, commands with exit codes recorded by the harness,
oracle results, premise check.  Prose does not substitute for evidence."*

A worker's own claim that its tests pass is never evidence.  The harness
records the exit codes; the Kernel records the oracle results.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: Keys a bundle must carry.  Absence is a validation failure, not a default.
REQUIRED_KEYS = (
    "task",
    "fence",
    "base_commit",
    "outputs",
    "diff_scope_check",
    "commands",
    "oracle_results",
    "premise_check",
    "budget_used",
    "resolved_models",
    "constitution_hash",
    "context_hash",
)


@dataclass
class CommandResult:
    """One command the **harness** ran, with its exit code."""

    cmd: str
    cwd: str
    exit: int
    stdout_hash: str = ""
    stderr_hash: str = ""

    def to_obj(self) -> dict:
        return {
            "cmd": self.cmd,
            "cwd": self.cwd,
            "exit": self.exit,
            "stdout_hash": self.stdout_hash,
            "stderr_hash": self.stderr_hash,
        }

    @classmethod
    def from_obj(cls, obj: dict) -> "CommandResult":
        return cls(
            cmd=str(obj.get("cmd", "")),
            cwd=str(obj.get("cwd", "")),
            exit=int(obj.get("exit", -1)),
            stdout_hash=str(obj.get("stdout_hash", "")),
            stderr_hash=str(obj.get("stderr_hash", "")),
        )


@dataclass
class OracleResult:
    """The outcome of one acceptance oracle."""

    cmd: str
    exit: int
    ok: bool
    stdout_hash: str = ""
    stderr_hash: str = ""
    note: str = ""

    def to_obj(self) -> dict:
        return {
            "cmd": self.cmd,
            "exit": self.exit,
            "ok": self.ok,
            "stdout_hash": self.stdout_hash,
            "stderr_hash": self.stderr_hash,
            "note": self.note,
        }

    @classmethod
    def from_obj(cls, obj: dict) -> "OracleResult":
        return cls(
            cmd=str(obj.get("cmd", "")),
            exit=int(obj.get("exit", -1)),
            ok=bool(obj.get("ok", False)),
            stdout_hash=str(obj.get("stdout_hash", "")),
            stderr_hash=str(obj.get("stderr_hash", "")),
            note=str(obj.get("note", "")),
        )


@dataclass
class Bundle:
    """The evidence bundle for one attempt at one task."""

    task: str
    fence: int
    base_commit: str = ""
    outputs: list = field(default_factory=list)
    diff_scope_check: dict = field(default_factory=dict)
    commands: list = field(default_factory=list)
    oracle_results: list = field(default_factory=list)
    premise_check: dict = field(default_factory=dict)
    budget_used: dict = field(default_factory=dict)
    resolved_models: list = field(default_factory=list)
    constitution_hash: str = ""
    context_hash: str = ""
    extras: dict = field(default_factory=dict)

    def to_obj(self) -> dict:
        obj = {
            "task": self.task,
            "fence": self.fence,
            "base_commit": self.base_commit,
            "outputs": self.outputs,
            "diff_scope_check": self.diff_scope_check,
            "commands": [c.to_obj() if isinstance(c, CommandResult) else c
                         for c in self.commands],
            "oracle_results": [o.to_obj() if isinstance(o, OracleResult) else o
                               for o in self.oracle_results],
            "premise_check": self.premise_check,
            "budget_used": self.budget_used,
            "resolved_models": self.resolved_models,
            "constitution_hash": self.constitution_hash,
            "context_hash": self.context_hash,
        }
        obj.update(self.extras)
        return obj

    @classmethod
    def from_obj(cls, obj: dict) -> "Bundle":
        known = set(cls.__dataclass_fields__) - {"extras"}
        extras = {k: v for k, v in obj.items() if k not in known}
        return cls(
            task=str(obj.get("task", "")),
            fence=int(obj.get("fence", 0)),
            base_commit=str(obj.get("base_commit", "")),
            outputs=list(obj.get("outputs") or []),
            diff_scope_check=obj.get("diff_scope_check") or {},
            commands=[CommandResult.from_obj(c) for c in (obj.get("commands") or [])],
            oracle_results=[OracleResult.from_obj(o)
                            for o in (obj.get("oracle_results") or [])],
            premise_check=obj.get("premise_check") or {},
            budget_used=obj.get("budget_used") or {},
            resolved_models=list(obj.get("resolved_models") or []),
            constitution_hash=str(obj.get("constitution_hash", "")),
            context_hash=str(obj.get("context_hash", "")),
            extras=extras,
        )

    # -- validation -------------------------------------------------------
    def validation_errors(self) -> list[str]:
        """Why this bundle would not be accepted.

        The rules come from the constitution and from pilot v1 section 9.6:
        nothing is promoted without a bundle, and a bundle without oracle
        results is not evidence of anything.
        """
        problems: list[str] = []
        if not self.task:
            problems.append("bundle.task is required")
        if not self.commands:
            problems.append("bundle.commands is empty: the harness must record "
                            "the commands it ran")
        if not self.oracle_results:
            problems.append("bundle.oracle_results is empty: oracles decide, "
                            "not the worker's claim")
        if not self.constitution_hash:
            problems.append("bundle.constitution_hash is required (I17)")
        for result in self.oracle_results:
            if not isinstance(result, OracleResult):
                continue
            if result.exit == 0 and not result.ok:
                problems.append(
                    f"oracle {result.cmd!r} exited 0 but is marked not-ok")
            if result.exit != 0 and result.ok:
                problems.append(
                    f"oracle {result.cmd!r} exited {result.exit} but is marked ok")
        scope = self.diff_scope_check or {}
        if scope.get("violations"):
            problems.append(
                f"diff scope check reports {len(scope['violations'])} violation(s)")
        premise = self.premise_check or {}
        if premise.get("refuted"):
            problems.append("premise was refuted: this is not a completion")
        return problems

    def all_oracles_passed(self) -> bool:
        return bool(self.oracle_results) and all(
            r.ok for r in self.oracle_results if isinstance(r, OracleResult))

    # -- storage ----------------------------------------------------------
    def write(self, evidence_dir: Path) -> Path:
        """Write the bundle to ``<evidence_dir>/EB-<task>-<fence>/bundle.json``."""
        target = Path(evidence_dir) / f"EB-{self.task}-{self.fence}"
        target.mkdir(parents=True, exist_ok=True)
        path = target / "bundle.json"
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(self.to_obj(), fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        return path


def hash_output(path: Path) -> str:
    """SHA-256 of a file, or ``""`` if it does not exist."""
    try:
        data = Path(path).read_bytes()
    except OSError:
        return ""
    return hashlib.sha256(data).hexdigest()


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
