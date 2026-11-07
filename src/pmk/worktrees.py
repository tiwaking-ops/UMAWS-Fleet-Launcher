"""Worktree lifecycle helpers (incident REC-04 / REC-06).

Per-lease worker worktrees live at ``<root>/work/<task>-<fence>``.  Before
this module the repository had no operator surface over them at all: they
were created by the fleet, never listed, never measured and never collected
(the incident report ``incident-report-worktree-lifecycle-leak-v1``).

This module is deliberately **read-mostly**:

* :func:`records` and :func:`stats` only inspect the filesystem and git;
  they change nothing.
* :func:`prune` is conservative and **dry-run by default**.  It refuses to
  touch a tree with uncommitted content (capture must happen first — REC-02,
  which is not yet implemented), and it never touches ``work/context-sync``,
  which the Kernel owns and reclaims itself.

Nothing here is on the coordination hot path: ``pmk status`` and
``pmk worktree`` use it, and the sentinel ``I17`` observation uses it.
"""

from __future__ import annotations

import time
from pathlib import Path

#: The per-lease worktree directory (``Repo.work_dir``).
WORKTREE_SUBDIR = "work"

#: A Kernel-managed worktree that is not a lease and must never be pruned.
CONTEXT_SYNC_NAME = "context-sync"

#: Directory names ``prune`` will never consider.
PROTECTED = frozenset({CONTEXT_SYNC_NAME})


def worktree_root(repo) -> Path:
    return Path(repo.root) / WORKTREE_SUBDIR


def parse_name(name: str) -> tuple[str, int | None]:
    """Split ``<TASK>-<fence>`` into ``(task_id, fence)``.

    Returns ``(name, None)`` when the directory name is not a recognisable
    lease worktree, so callers can skip it rather than guess.
    """
    parts = name.rsplit("-", 1)
    if (len(parts) == 2 and parts[1].isdigit()
            and parts[0].startswith("T-")):
        return parts[0], int(parts[1])
    return name, None


def iter_dirs(repo) -> list[Path]:
    """Every candidate worktree directory, sorted, excluding protected ones."""
    root = worktree_root(repo)
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir()
                  if p.is_dir() and p.name not in PROTECTED)


def dir_bytes(path: Path) -> int:
    total = 0
    for entry in path.rglob("*"):
        try:
            if entry.is_file():
                total += entry.stat().st_size
        except OSError:
            continue
    return total


def _dirty(repo, path: Path) -> tuple[bool, int]:
    """``(is_dirty, entry_count)`` from ``git status --porcelain -uall``.

    The ``-- .`` pathspec scopes the result to the tree itself, so a plain
    directory inside the main checkout does not report the whole
    repository's status.
    """
    code, out, _ = repo.git("status", "--porcelain", "-uall", "--", ".",
                            cwd=path)
    if code != 0:
        # Not a git worktree (or git failed): treat as unknown, not clean.
        return False, 0
    lines = [ln for ln in out.splitlines() if ln.strip()]
    return (len(lines) > 0), len(lines)


def record(repo, state, path: Path, *, with_git: bool = True) -> dict:
    task_id, fence = parse_name(path.name)
    task = state.tasks.get(task_id) if state is not None else None
    if with_git:
        dirty, entries = _dirty(repo, path)
    else:
        dirty, entries = False, 0
    try:
        age_days = (time.time() - path.stat().st_mtime) / 86400.0
    except OSError:
        age_days = -1.0
    return {
        "name": path.name,
        "task": task_id,
        "fence": fence,
        "state": task.state if task is not None else "?",
        "dirty": dirty,
        "entries": entries,
        "bytes": dir_bytes(path),
        "age_days": round(age_days, 1),
        "path": str(path),
    }


def records(repo, state, *, with_git: bool = True) -> list[dict]:
    return [record(repo, state, p, with_git=with_git)
            for p in iter_dirs(repo)]


def stats(repo, state=None, *, with_git: bool = False) -> dict:
    """Cheap aggregate for ``pmk status``: count, bytes, dirty count."""
    recs = records(repo, state, with_git=with_git)
    return {
        "count": len(recs),
        "bytes": sum(r["bytes"] for r in recs),
        "dirty": sum(1 for r in recs if r["dirty"]),
    }


def prune(repo, state, *, dry_run: bool = True,
          older_than_days: float | None = None,
          keep_unmerged: bool = True,
          archive: bool = False) -> dict:
    """Plan (and, when *dry_run* is false, perform) a conservative prune.

    A tree is a **candidate** only when all of the following hold:

    * its name parses as ``<task>-<fence>``;
    * it has **no uncommitted content** (dirty trees are always skipped —
      they may hold work that exists nowhere else);
    * it is not under an active lease; and
    * if *older_than_days* is given, its task is ``VOID`` and the tree is at
      least that old.

    ``archive=True`` is accepted for forward-compatibility with REC-02, but
    because the capture path is not implemented it still refuses dirty
    trees (with an explicit reason) rather than deleting unarchived work.
    """
    recs = records(repo, state)
    candidates: list[dict] = []
    skipped: list[dict] = []

    for r in recs:
        if r["fence"] is None:
            skipped.append({"name": r["name"],
                            "reason": "not a lease worktree name"})
            continue
        if r["dirty"]:
            reason = ("dirty tree; capture (REC-02) required before pruning"
                      if not archive else
                      "archive (REC-02) is not implemented; refusing to prune "
                      "a dirty tree")
            skipped.append({"name": r["name"], "reason": reason})
            continue
        if keep_unmerged and r["state"] == "LEASED":
            skipped.append({"name": r["name"], "reason": "active lease"})
            continue
        if older_than_days is not None:
            if r["state"] != "VOID" or r["age_days"] < float(older_than_days):
                skipped.append({"name": r["name"],
                                "reason": "not a VOID tree older than the "
                                          "threshold"})
                continue
        candidates.append(r)

    removed: list[str] = []
    if not dry_run:
        for r in candidates:
            code, out, err = repo.git("worktree", "remove", "--force",
                                      r["path"])
            if code == 0:
                removed.append(r["name"])
            else:
                skipped.append({"name": r["name"],
                                "reason": f"git worktree remove failed: "
                                          f"{err.strip() or out.strip()}"})

    return {
        "dry_run": dry_run,
        "candidates": [c["name"] for c in candidates],
        "removed": removed,
        "skipped": skipped,
        "counts": {"candidates": len(candidates), "removed": len(removed),
                   "skipped": len(skipped)},
        "recoverable_bytes": sum(c["bytes"] for c in candidates),
    }
