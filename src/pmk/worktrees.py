"""Worktree lifecycle helpers (incident REC-04 / REC-06).

Per-lease worker worktrees live at ``<root>/work/<task>-<fence>``.  Before
this module the repository had no operator surface over them at all: they
were created by the fleet, never listed, never measured and never collected
(the incident report ``incident-report-worktree-lifecycle-leak-v1``).

This module is deliberately **read-mostly**:

* :func:`records` and :func:`stats` only inspect the filesystem and git;
  they change nothing.
* :func:`prune` is conservative and **dry-run by default**.  Without
  ``archive=True`` it refuses to touch a tree with uncommitted content;
  with it, a dirty tree is captured (REC-02) and the capture verified
  before the tree becomes a removal candidate.  It never touches
  ``work/context-sync``, which the Kernel owns and reclaims itself.
* :func:`archive_tree` only **copies** stranded work into
  ``<root>/stranded/``; it never modifies or deletes a worktree.

Nothing here is on the coordination hot path: ``pmk status`` and
``pmk worktree`` use it, and the sentinel ``I17`` observation uses it.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path

#: The per-lease worktree directory (``Repo.work_dir``).
WORKTREE_SUBDIR = "work"

#: Where REC-02 captures land, relative to the repository root.
ARCHIVE_SUBDIR = "stranded"

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
    """Cheap aggregate for ``pmk status``: count, bytes, dirty count.

    ``dirty`` is ``None`` (unknown) unless *with_git* is true.  Reporting a
    ``0`` we did not compute would be the same misleading "nothing here"
    signal the incident was about, so the count is left explicitly unknown
    rather than guessed.
    """
    recs = records(repo, state, with_git=with_git)
    return {
        "count": len(recs),
        "bytes": sum(r["bytes"] for r in recs),
        "dirty": sum(1 for r in recs if r["dirty"]) if with_git else None,
    }


def is_dirty(repo, path: Path) -> bool:
    """Public wrapper over the git-status check."""
    return _dirty(repo, path)[0]


# ---------------------------------------------------------------------------
# REC-02 -- capture (archive) before any reclaim
# ---------------------------------------------------------------------------

def archive_root(repo) -> Path:
    return Path(repo.root) / ARCHIVE_SUBDIR


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _tar_untracked(worktree: Path, files: list[str], tar_path: Path) -> int:
    """Write *files* (relative to *worktree*) into *tar_path*.  Returns count."""
    written = 0
    with tarfile.open(tar_path, "w") as tf:
        for rel in files:
            full = worktree / rel
            try:
                tf.add(full, arcname=rel)
                written += 1
            except (OSError, ValueError):
                continue
    return written


def archive_tree(repo, state, path: Path, *, target_root: Path | None = None) -> dict:
    """Capture one worktree's uncommitted work (REC-02).

    Writes ``<root>/stranded/<task>-<fence>/`` containing:

    * ``diff.patch``      -- ``git diff HEAD --binary`` (all tracked changes);
    * ``untracked.tar``   -- every untracked, non-ignored file;
    * ``RESULT.md``       -- a copy of the agent's own result, when present;
    * ``manifest.json``   -- task, fence, base commit, counts and sha256s.

    This **only copies**; it never modifies or deletes the worktree.  The
    manifest's sha256s make the capture independently verifiable.
    """
    path = Path(path)
    task_id, fence = parse_name(path.name)
    root = Path(target_root) if target_root else archive_root(repo)
    dest = root / (f"{task_id}-{fence}" if fence is not None else path.name)

    # Everything is read through git_bytes: repo.git() decodes stdout in
    # text mode, which strips the CR from CRLF and would make a captured
    # patch fail to apply to its CRLF base.
    code, base_raw, _ = repo.git_bytes("rev-parse", "HEAD", cwd=path)
    base = base_raw.decode("utf-8", "replace").strip() if code == 0 else ""

    code, diff, err = repo.git_bytes("diff", "HEAD", "--binary", "--", ".",
                                     cwd=path)
    if code != 0:
        reason = err.decode("utf-8", "replace").strip() or "git diff failed"
        return {"name": path.name, "archived": False, "reason": reason}

    code, others, _ = repo.git_bytes("ls-files", "--others",
                                     "--exclude-standard", "-z", "--", ".",
                                     cwd=path)
    untracked = [p.decode("utf-8", "replace")
                 for p in others.split(b"\0") if p]

    dest.mkdir(parents=True, exist_ok=True)
    # Byte-for-byte: never pass this through a text-mode write.
    (dest / "diff.patch").write_bytes(diff)
    tar_path = dest / "untracked.tar"
    written = _tar_untracked(path, untracked, tar_path)

    result_src = path / ".pmwork" / "RESULT.md"
    has_result = result_src.is_file()
    if has_result:
        shutil.copyfile(result_src, dest / "RESULT.md")

    task = state.tasks.get(task_id) if state is not None else None
    manifest = {
        "task": task_id,
        "fence": fence,
        "worktree": path.name,
        "state": task.state if task is not None else "?",
        "base_commit": base,
        "tracked_changes": bool(diff.strip()),
        "untracked_count": len(untracked),
        "untracked_packed": written,
        "untracked_files": untracked[:500],
        "result_md": has_result,
        "diff_bytes": (dest / "diff.patch").stat().st_size,
        "diff_sha256": _sha256_file(dest / "diff.patch"),
        "untracked_tar_bytes": tar_path.stat().st_size,
        "untracked_tar_sha256": _sha256_file(tar_path),
        "archived_at": _now_iso(),
    }
    # Also byte-faithful: no platform newline translation for the manifest.
    (dest / "manifest.json").write_bytes(
        (json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    return {"name": path.name, "archived": True, "dest": str(dest),
            "diff_bytes": manifest["diff_bytes"], "untracked_count": len(untracked)}


def verify_archive(dest: Path) -> tuple[bool, list[str]]:
    """Re-read an archive and check its sha256s against ``manifest.json``."""
    dest = Path(dest)
    problems: list[str] = []
    manifest_path = dest / "manifest.json"
    if not manifest_path.is_file():
        return False, ["manifest.json is missing"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return False, [f"manifest.json is unreadable: {exc}"]

    diff = dest / "diff.patch"
    if not diff.is_file():
        problems.append("diff.patch is missing")
    elif _sha256_file(diff) != manifest.get("diff_sha256"):
        problems.append("diff.patch sha256 does not match the manifest")

    tar_path = dest / "untracked.tar"
    if not tar_path.is_file():
        problems.append("untracked.tar is missing")
    else:
        if _sha256_file(tar_path) != manifest.get("untracked_tar_sha256"):
            problems.append("untracked.tar sha256 does not match the manifest")
        try:
            with tarfile.open(tar_path, "r") as tf:
                tf.getmembers()
        except (OSError, tarfile.TarError) as exc:
            problems.append(f"untracked.tar is unreadable: {exc}")
    return (not problems), problems


def reclaim_after_capture(repo, state, path: Path, *,
                          target_root: Path | None = None) -> dict:
    """REC-01: capture a worktree, verify the capture, then remove it.

    This is the **only** function that deletes a worktree.  It never
    deletes anything whose capture did not verify, so a reclaim cannot
    lose work that was not first stored under ``stranded/``.  A tree that
    does not exist, or whose capture or removal fails, is left in place
    and the result says why.

    Returns a result dict; ``reclaimed`` is true only when the worktree
    was actually removed.
    """
    path = Path(path)
    result: dict = {"worktree": str(path), "reclaimed": False, "archived": False}
    if not path.is_dir():
        result["reason"] = "not on disk"
        return result

    capture = archive_tree(repo, state, path, target_root=target_root)
    if not capture.get("archived"):
        result["reason"] = (f"capture failed: "
                            f"{capture.get('reason', 'unknown')}")
        return result
    dest = Path(capture["dest"])
    ok, problems = verify_archive(dest)
    if not ok:
        result["reason"] = "capture not verified: " + "; ".join(problems)
        return result
    result["archived"] = True
    result["archive"] = str(dest)

    code, out, err = repo.git("worktree", "remove", "--force", str(path))
    if code != 0:
        result["reason"] = ("git worktree remove failed: "
                            f"{(err.strip() or out.strip())}")
        return result
    result["reclaimed"] = True
    return result


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

    ``archive=True`` wires REC-02: a dirty tree is captured first, the
    capture is verified, and only then does the tree become eligible for
    removal.  While *dry_run* is true nothing is archived and nothing is
    removed — the plan simply reports which dirty trees would be captured.
    """
    recs = records(repo, state)
    candidates: list[dict] = []
    skipped: list[dict] = []
    archived: list[dict] = []

    for r in recs:
        if r["fence"] is None:
            skipped.append({"name": r["name"],
                            "reason": "not a lease worktree name"})
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
        if r["dirty"]:
            if not archive:
                skipped.append({"name": r["name"],
                                "reason": "dirty tree; capture (REC-02) "
                                          "required before pruning"})
                continue
            if dry_run:
                # A dry run must not write anything.
                candidates.append(r)
                continue
            capture = archive_tree(repo, state, Path(r["path"]))
            if not capture.get("archived"):
                skipped.append({"name": r["name"],
                                "reason": "capture failed: "
                                          f"{capture.get('reason', 'unknown')}"})
                continue
            ok, problems = verify_archive(Path(capture["dest"]))
            if not ok:
                skipped.append({"name": r["name"],
                                "reason": "capture not verified: "
                                          + "; ".join(problems)})
                continue
            archived.append({"name": r["name"], "dest": capture["dest"]})
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
        "archived": archived,
        "skipped": skipped,
        "counts": {"candidates": len(candidates), "removed": len(removed),
                   "archived": len(archived), "skipped": len(skipped)},
        "recoverable_bytes": sum(c["bytes"] for c in candidates),
    }
