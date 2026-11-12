"""Pin a subprocess's Python resolution to the worktree it is judging.

The Fleet runs oracles, gates and workers inside a lease worktree.  On a
machine where the packages are installed from the repository's ``src`` (an
editable install puts ``<repo>/src`` on ``sys.path``), that installed copy
shadows the worktree: ``cwd=`` does not change import resolution, so a
correct agent can be judged by main's code.  T-0145 and T-0146 were both lost
to exactly that.

Every spawn therefore gets the worktree's ``src`` and ``tests`` **first** on
``PYTHONPATH``, with whatever the process already had appended after them so
genuinely external packages still import.  The caller's environment is never
mutated: a copy is returned.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

__all__ = ["DEFAULT_IMPORT_PROBES", "WORKTREE_PATH_ENTRIES",
           "import_origin_problems", "worktree_env"]

#: The imports that have historically resolved to main through the editable
#: install.  A worktree that has the top-level package but not the probed
#: module is exactly where the namespace-package trap appears.
DEFAULT_IMPORT_PROBES = ("cna.tools.coverage", "pmk.api")

_IMPORT_PROBE = r'''
import importlib, json, pathlib, sys
out = {}
for name in sys.argv[1:]:
    try:
        module = importlib.import_module(name)
    except Exception as exc:
        out[name] = {"error": f"{type(exc).__name__}: {exc}"}
        continue
    paths = []
    filename = getattr(module, "__file__", None)
    if filename:
        paths.append(str(pathlib.Path(filename).resolve()))
    for entry in getattr(module, "__path__", []):
        paths.append(str(pathlib.Path(entry).resolve()))
    out[name] = {"paths": paths}
print(json.dumps(out))
'''

#: Prepended to ``PYTHONPATH``, in this order, for every worktree spawn.
WORKTREE_PATH_ENTRIES = ("src", "tests")


def worktree_env(worktree: str | Path, *,
                 base: dict[str, str] | None = None,
                 drop_pythonpath: bool = False) -> dict[str, str]:
    """Return an environment that resolves the worktree before the host.

    ``base`` is the environment to build on (default: ``os.environ``); pass a
    scrubbed dict for gateway profiles so credentials stay scrubbed and only
    the path entries are added.  ``drop_pythonpath`` discards the inherited
    ``PYTHONPATH`` entirely; the default keeps it, after the worktree, because
    dropping it would break packages that genuinely live outside the tree.
    """
    # The entries are handed to the child process, so they must be absolute
    # for the same reason the cwd must be: a relative entry would resolve
    # against the child's directory (or the parent's) and name neither the
    # worktree nor a path that exists.
    worktree = Path(worktree).resolve()
    env = dict(os.environ if base is None else base)
    prior = "" if drop_pythonpath else env.get("PYTHONPATH", "")
    entries = [str(worktree / name) for name in WORKTREE_PATH_ENTRIES]
    if prior:
        entries.append(prior)
    env["PYTHONPATH"] = os.pathsep.join(entries)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def import_origin_problems(worktree: str | Path, *,
                           modules: tuple[str, ...] | None = None,
                           timeout: int = 30) -> list[str]:
    """Return the probed modules that resolve outside *worktree*.

    ``cna`` is a namespace package.  A missing module in the worktree can
    therefore be supplied by the editable install in main even when
    ``PYTHONPATH`` starts with the worktree.  This preflight checks the
    actual module file/path, not just the environment setup.

    Modules whose top-level package is absent from the worktree are skipped:
    small fixture repositories do not carry the project packages, and a
    precheck must not refuse work merely because the project is not CNA.
    """
    wt = Path(worktree).resolve()
    selected = tuple(modules or DEFAULT_IMPORT_PROBES)
    selected = tuple(
        name for name in selected
        if (wt / "src" / name.split(".", 1)[0]).exists()
        or (wt / name.split(".", 1)[0]).exists()
    )
    if not selected:
        return []

    try:
        proc = subprocess.run(
            [sys.executable, "-c", _IMPORT_PROBE, *selected],
            cwd=str(wt), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, env=worktree_env(wt))
    except (OSError, subprocess.SubprocessError) as exc:
        return [f"import-origin probe failed: {type(exc).__name__}: {exc}"]
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        return [f"import-origin probe exited {proc.returncode}: {detail[:300]}"]

    try:
        payload = json.loads(proc.stdout)
    except (TypeError, ValueError) as exc:
        return [f"import-origin probe returned invalid JSON: {exc}"]

    problems: list[str] = []
    for name in selected:
        row = payload.get(name, {}) if isinstance(payload, dict) else {}
        if row.get("error"):
            problems.append(f"{name}: {row['error']}")
            continue
        paths = [Path(entry) for entry in row.get("paths", [])]
        if not paths:
            problems.append(f"{name}: no import path")
            continue
        outside = [str(path) for path in paths if not _is_under(path, wt)]
        if outside:
            problems.append(
                f"{name}: resolves outside the worktree: " + ", ".join(outside))
    return problems
