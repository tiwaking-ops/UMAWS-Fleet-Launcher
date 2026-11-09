"""Static checks for subprocess environment and fleet cwd safety.

The T-0145/T-0146 failure was one unguarded ``subprocess.run``: it inherited
the host environment, so the oracle judged a worktree with the installed copy
of the code.  This lint makes that class of call visible at review time
instead of at the next lost attempt.

It also requires every fleet spawn (``subprocess.*`` or ``plat.spawn`` under
``src/fleet``) to supply an explicit ``cwd=``.  A missing cwd, ``None``, a
relative path, or an unresolved ``Path`` is unsafe: a relative path resolves
against the parent process's directory, which is the main tree for a fleet
spawn.  The cwd must be the result of ``resolve()`` or ``abspath``, directly
or through a local variable.

A call is allowed to inherit the environment only if it is listed, with a
reason, in ``tools/subprocess_env_allowlist.txt`` as ``path::function``.  The
key is the enclosing function, not the line number, so unrelated edits do not
churn the list.  Stale entries are reported as warnings; unlisted calls fail.

Optional extra files may follow the command, as in
``python tools/check_subprocess_env.py [FILE ...]``; each one is scanned for
fleet cwd safety in addition to ``src/fleet``.  This is how a proposed or
newly written module outside ``src/fleet`` is checked before it is placed
there.  Each file is reported by the path as given, and a relative path
resolves against the current directory.

The extra files are only checked for cwd safety: the unguarded-spawn check for
a missing ``env=`` applies to ``src/`` and its allowlist, not to these files.
A missing extra file is an input error (exit 2), reported without a traceback.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
FLEET = SRC / "fleet"
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


def _is_fleet_cwd_spawn(node: ast.Call) -> bool:
    """A process boundary the Fleet can reach, including ``plat.spawn``."""
    if _is_spawn(node):
        return True
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "spawn"
        and isinstance(func.value, ast.Name)
        and func.value.id == "plat"
    )


def _safe_cwd(node: ast.AST, assigned: dict[str, bool]) -> bool:
    """Whether *node* is statically known to name an absolute worktree."""
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name) and func.id == "str" and node.args:
            return _safe_cwd(node.args[0], assigned)
        if isinstance(func, ast.Attribute) and func.attr in {"resolve",
                                                               "abspath"}:
            return True
    if isinstance(node, ast.Name):
        return assigned.get(node.id, False)
    if isinstance(node, ast.IfExp):
        return (_safe_cwd(node.body, assigned)
                and _safe_cwd(node.orelse, assigned))
    if isinstance(node, ast.BoolOp):
        return all(_safe_cwd(value, assigned) for value in node.values)
    return False


def _assignments(scope: ast.AST) -> dict[str, bool]:
    """Names assigned in this function/module and whether they are resolved."""
    assigned: dict[str, bool] = {}

    def visit(node: ast.AST) -> None:
        if node is not scope and isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigned[target.id] = _safe_cwd(node.value, assigned)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is not None:
                assigned[node.target.id] = _safe_cwd(node.value, assigned)
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(scope)
    return assigned


def scan_cwd_file(path: Path) -> list[tuple[str, int, str]]:
    """Return missing or unsafe fleet cwds as ``(function, line, expression)``.

    A missing ``cwd=`` is reported with the expression ``<missing>``.
    """
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    scopes: list[tuple[ast.AST, str | None]] = [(tree, None)]
    scopes.extend((node, node.name) for node in ast.walk(tree)
                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))
    findings: list[tuple[str, int, str]] = []
    for scope, function in scopes:
        assigned = _assignments(scope)

        def visit(node: ast.AST) -> None:
            if node is not scope and isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                return
            if isinstance(node, ast.Call) and _is_fleet_cwd_spawn(node):
                cwd = next((keyword.value for keyword in node.keywords
                            if keyword.arg == "cwd"), None)
                if cwd is None:
                    findings.append((function or "<module>", node.lineno,
                                     "<missing>"))
                elif not _safe_cwd(cwd, assigned):
                    findings.append((function or "<module>", node.lineno,
                                     ast.unparse(cwd)))
            for child in ast.iter_child_nodes(node):
                visit(child)

        visit(scope)
    return findings


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "extra_fleet_files", nargs="*", type=Path, metavar="FILE",
        help="optional extra Python files to scan for fleet cwd safety "
             "(not for missing env=)")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    missing = [path for path in args.extra_fleet_files if not path.is_file()]
    if missing:
        for path in missing:
            reason = "not found" if not path.exists() else "not a file"
            print(f"error: extra fleet file {reason}: {path}", file=sys.stderr)
        return 2
    allow = load_allowlist(ALLOWLIST)
    seen: set[tuple[str, str]] = set()
    findings: list[str] = []
    cwd_findings: list[str] = []

    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        for function, lineno in scan_file(path):
            key = (rel, function)
            if key in allow:
                seen.add(key)
                continue
            findings.append(f"{rel}:{lineno} in {function}() has no env=")

    cwd_paths = [(path, path.relative_to(ROOT).as_posix())
                 for path in sorted(FLEET.rglob("*.py"))]
    cwd_paths.extend((path, str(path)) for path in args.extra_fleet_files)
    for path, label in cwd_paths:
        for function, lineno, expression in scan_cwd_file(path):
            detail = ("has no cwd=" if expression == "<missing>"
                      else f"passes cwd={expression}")
            cwd_findings.append(
                f"{label}:{lineno} in {function}() {detail}")

    stale = sorted(set(allow) - seen)
    for rel, function in stale:
        print(f"warning: stale allowlist entry {rel}::{function}")

    if findings:
        print("unguarded subprocess spawns (add env= or an allowlist reason):")
        for finding in findings:
            print(f"  {finding}")
    if cwd_findings:
        print("fleet spawns without an explicit, resolved cwd "
              "(pass cwd=Path(...).resolve()):")
        for finding in cwd_findings:
            print(f"  {finding}")
    if findings or cwd_findings:
        return 1

    print(f"ok: no unguarded subprocess spawns ({len(seen)} allowlisted); "
          "fleet cwd checks pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
