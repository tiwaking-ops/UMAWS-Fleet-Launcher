"""The fleet's throwaway directories, and cleanup that says what it did.

--- Recorded defect, fixed 2026-11-12 ---------------------------------
The merge queue and the precheck both built their scratch with
``tempfile.mkdtemp(prefix=...)`` **in the global temp directory**, and
between them they leaked two different ways:

* ``precheck.oracles_already_pass`` added a worktree, ran the oracles and
  removed the worktree -- but never the ``pmk-precheck-*`` directory around
  it.  The lease-admission path calls it on every claim, so the husks piled
  up (412 of them in four days, still growing) and nothing ever collected
  them: no owner exists for the global temp namespace.
* ``shutil.rmtree(path, ignore_errors=True)`` reports nothing when it
  fails, and on Windows it fails whenever one file in the tree is
  read-only -- which git does leave -- so a merge, or a precheck dry run,
  that hit that (or whose process was killed) left a whole tree behind.

A leftover whose repository is gone cannot even be proven to belong to this
project any more -- ``pmk.worktrees.prune_scratch`` deliberately refuses a
merge tree it cannot prove is ours -- so every such leftover was permanent.

``scratch_dir`` puts the scratch where the caller says: a pytest-managed
``tmp_path`` in tests, the global temp in production.  ``remove_scratch``
clears the write-protect bit before removing, so what happened is a fact
rather than something swallowed by ``ignore_errors``.
"""

from __future__ import annotations

import os
import shutil
import stat
import tempfile
from pathlib import Path

__all__ = ["remove_scratch", "scratch_dir"]


def scratch_dir(prefix: str, temp_root: Path | str | None = None) -> Path:
    """A fresh throwaway directory, under *temp_root* when one is given.

    The *prefix* keeps the family identifiable wherever the directory lands
    (``pmk-merge-``, ``pmk-precheck-``, ``pmk-precheck-dry-``).  Leaving
    *temp_root* unset keeps the production behaviour -- the global temp
    directory, whose only collector is ``pmk worktree prune --merge-trees``.
    """
    return Path(tempfile.mkdtemp(
        prefix=prefix, dir=str(temp_root) if temp_root is not None else None))


def remove_scratch(path: Path | str) -> bool:
    """Remove *path* whole.  True when nothing is left of it.

    ``shutil.rmtree(path, ignore_errors=True)`` leaves a tree behind
    whenever a file in it is read-only -- git leaves such files on Windows
    -- and says nothing about it, which is how the defect above stayed
    invisible.  Clear the write-protect bit first, then remove.  A file that
    another live process still holds open is the case that can survive;
    then the answer is honestly False and the sanctioned collector
    (``pmk worktree prune --merge-trees``) is the way back.
    """
    path = Path(path)
    if not path.exists():
        return True
    # Every file and every directory, the root included: on Windows the
    # read-only attribute blocks both deleting a directory's contents and
    # removing the directory itself.  Deepest-first, so each directory is
    # cleared only after everything under it has been.
    for parent, dirs, files in os.walk(path, topdown=False):
        for name in files + dirs:
            try:
                os.chmod(os.path.join(parent, name), stat.S_IWRITE)
            except OSError:
                pass
    try:
        os.chmod(path, stat.S_IWRITE)
    except OSError:
        pass
    try:
        shutil.rmtree(path)
    except OSError:
        pass
    return not path.exists()
