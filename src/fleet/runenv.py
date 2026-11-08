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

import os
from pathlib import Path

__all__ = ["WORKTREE_PATH_ENTRIES", "worktree_env"]

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
