"""Fail when a subprocess spawn under ``src/`` has no ``env=``.

The T-0145/T-0146 failure was one unguarded ``subprocess.run``: it inherited
the host environment, so the oracle judged a worktree with the installed copy
of the code.  This lint makes that class of call visible at review time
instead of at the next lost attempt.

A call is allowed to inherit the environment only if it is listed, with a
reason, in ``tools/subprocess_env_allowlist.txt`` as ``path::function``.  The
key is the enclosing function, not the line number, so unrelated edits do not
churn the list.  Stale entries are reported as warnings; unlisted calls fail.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ALLOWLIST = ROOT / "tools" / "subprocess_env_allowlist.txt"

SPAWN_ATTRS = {"run", "Popen", "check_output", "check_call", "call"}


def _is_spawn(node: ast.Call) -> bool:
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr in SPAWN_ATTRS
        and isinstance(func.value, ast.Name)
        and func.value.id == "subprocess"
    )


def scan_file(path: Path) -> list[tuple[str, int]]:
    """Return ``(enclosing function, line)`` for every unguarded spawn."""
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    findings: list[tuple[str, int]] = []

    def visit(node: ast.AST, function: str | None) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function = node.name
        if isinstance(node, ast.Call) and _is_spawn(node):
            if not any(keyword.arg == "env" for keyword in node.keywords):
                findings.append((function or "<module>", node.lineno))
        for child in ast.iter_child_nodes(node):
            visit(child, function)

    visit(tree, None)
    return findings


def load_allowlist(path: Path) -> dict[tuple[str, str], str]:
    entries: dict[tuple[str, str], str] = {}
    if not path.is_file():
        return entries
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, _, reason = line.partition("#")
        key = key.strip()
        if "::" not in key:
            continue
        rel, _, function = key.partition("::")
        entries[(rel.strip(), function.strip())] = reason.strip()
    return entries


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    allow = load_allowlist(ALLOWLIST)
    seen: set[tuple[str, str]] = set()
    findings: list[str] = []

    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        for function, lineno in scan_file(path):
            key = (rel, function)
            if key in allow:
                seen.add(key)
                continue
            findings.append(f"{rel}:{lineno} in {function}() has no env=")

    stale = sorted(set(allow) - seen)
    for rel, function in stale:
        print(f"warning: stale allowlist entry {rel}::{function}")

    if findings:
        print("unguarded subprocess spawns (add env= or an allowlist reason):")
        for finding in findings:
            print(f"  {finding}")
        return 1

    print(f"ok: no unguarded subprocess spawns ({len(seen)} allowlisted)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
