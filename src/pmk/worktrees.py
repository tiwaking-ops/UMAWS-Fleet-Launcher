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
import io
import json
import os
import shutil
import stat
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from . import plat

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


def _rmtree_force(path: Path) -> None:
    """Remove a directory tree, clearing the read-only bits git leaves.

    A linked worktree's ``.git`` file (and files copied from a git object)
    can be read-only, which makes ``shutil.rmtree`` fail on Windows.  Clear
    the bit deepest-first, then remove the tree.
    """
    for parent_dir, dirs, files in os.walk(path, topdown=False):
        for name in files + dirs:
            try:
                os.chmod(os.path.join(parent_dir, name), stat.S_IWRITE)
            except OSError:
                pass
    shutil.rmtree(path)


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


def is_git_worktree(repo, path: Path) -> bool:
    """True only when *path* is itself a work tree git can resolve.

    ``git rev-parse --is-inside-work-tree`` is not enough: a plain directory
    dropped inside ``work/`` sits *inside* the main checkout, so git answers
    ``true`` for it too.  Comparing ``--show-toplevel`` to *path* means an
    orphaned scratch directory (a stale merge tree whose repository is gone)
    is correctly reported as not a worktree, and is captured as raw bytes
    rather than as a git diff of the main checkout.
    """
    code, out, _err = repo.git("rev-parse", "--show-toplevel", cwd=path)
    if code != 0:
        return False
    try:
        top = Path(out.strip()).resolve()
        target = Path(path).resolve()
    except OSError:
        return False
    return os.path.normcase(str(top)) == os.path.normcase(str(target))


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


class CaptureError(RuntimeError):
    """A capture could not be proven complete; nothing may be deleted."""


def _write_file(path: Path, data: bytes) -> None:
    """Write *data* and flush it to disk before returning.

    A capture that is deleted before it reaches the disk is not a capture.
    """
    with path.open("wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())


def _run_git(repo, path: Path, *args: str) -> bytes:
    code, out, err = repo.git_bytes(*args, cwd=path)
    if code != 0:
        message = err.decode("utf-8", "replace").strip() or "git failed"
        raise CaptureError(f"git {' '.join(args[:2])} failed: {message}")
    return out


def _list_paths(repo, path: Path, *, ignored: bool = False) -> list[str]:
    """Untracked (or ignored) files relative to *path*.

    The exit status is checked: an empty list from a failed ``ls-files``
    would make a capture look complete while omitting every file in it.
    """
    args = ["ls-files", "--others"]
    if ignored:
        args.append("-i")
    args += ["--exclude-standard", "-z", "--", "."]
    return [p.decode("utf-8", "surrogateescape")
            for p in _run_git(repo, path, *args).split(b"\0") if p]


def _scan_tree(repo, path: Path) -> tuple[str, bytes, list[str], list[str]]:
    """Base commit, tracked diff, untracked files and ignored files.

    Ignored files are part of the capture: ``git status`` calls a tree
    holding only ignored files clean, yet deleting it would still lose
    them.
    """
    base = _run_git(repo, path, "rev-parse", "HEAD").decode(
        "utf-8", "replace").strip()
    diff = _run_git(repo, path, "diff", "HEAD", "--binary", "--", ".")
    return (base, diff, _list_paths(repo, path),
            _list_paths(repo, path, ignored=True))


def _new_digest(diff: bytes):
    """Start a digest of exactly what a capture stores."""
    hasher = hashlib.sha256(b"pmk-tree-v1\0")
    hasher.update(str(len(diff)).encode("ascii") + b"\0" + diff)
    return hasher


def _digest_add(hasher, tag: str, rel: str, digest: str, size: int) -> None:
    hasher.update(tag.encode("ascii") + b"\0"
                  + rel.encode("utf-8", "surrogateescape") + b"\0"
                  + digest.encode("ascii") + b"\0"
                  + str(size).encode("ascii") + b"\0")


def _read_entry(worktree: Path, rel: str):
    """Read one file once: ``(tar member, bytes or None, sha256, size)``."""
    full = worktree / rel
    st = full.lstat()
    info = tarfile.TarInfo(rel)
    if stat.S_ISLNK(st.st_mode):
        target = os.readlink(full)
        info.type = tarfile.SYMTYPE
        info.linkname = target
        info.mode = 0o777
        digest = hashlib.sha256(
            b"link\0" + target.encode("utf-8", "surrogateescape")).hexdigest()
        return info, None, digest, 0
    data = full.read_bytes()
    info.size = len(data)
    info.mtime = int(st.st_mtime)
    info.mode = (st.st_mode & 0o777) or 0o644
    return info, data, hashlib.sha256(data).hexdigest(), len(data)


def _pack_files(worktree: Path, files: list[str], tar_path: Path,
                hasher, tag: str) -> int:
    """Write *files* to *tar_path*, folding the same bytes into *hasher*.

    Each file is read exactly once, so the manifest can never describe a
    version of a file the archive does not contain.  A file that cannot be
    read raises: a capture that omits a listed file is not a capture.
    """
    packed = 0
    with tarfile.open(tar_path, "w") as tf:
        for rel in sorted(files):
            try:
                info, data, digest, size = _read_entry(worktree, rel)
                tf.addfile(info, io.BytesIO(data) if data is not None else None)
            except (OSError, ValueError, tarfile.TarError) as exc:
                raise CaptureError(f"could not capture {rel!r}: {exc}") from exc
            _digest_add(hasher, tag, rel, digest, size)
            packed += 1
        try:
            tf.fileobj.flush()
            os.fsync(tf.fileobj.fileno())
        except (AttributeError, OSError) as exc:
            raise CaptureError(
                f"could not flush {tar_path.name}: {exc}") from exc
    if packed != len(files):
        raise CaptureError(
            f"{tar_path.name}: packed {packed} of {len(files)} files")
    return packed


def _quiescence_digest(repo, path: Path) -> str:
    """Digest the tree as it is on disk right now, the way a capture would.

    Used after a capture and before a removal: if this differs from the
    manifest's ``tree_digest``, something wrote to the tree in between and
    the tree must be kept.
    """
    _base, diff, untracked, ignored = _scan_tree(repo, path)
    hasher = _new_digest(diff)
    for tag, files in (("u", untracked), ("i", ignored)):
        for rel in sorted(files):
            try:
                _info, _data, digest, size = _read_entry(path, rel)
            except (OSError, ValueError) as exc:
                raise CaptureError(f"could not read {rel!r}: {exc}") from exc
            _digest_add(hasher, tag, rel, digest, size)
    return hasher.hexdigest()


def _raw_entries(path: Path) -> list[str]:
    """Every non-directory entry under *path*, as posix-relative names."""
    entries: list[str] = []
    for entry in path.rglob("*"):
        try:
            if entry.is_dir() and not entry.is_symlink():
                continue
        except OSError:
            continue
        entries.append(entry.relative_to(path).as_posix())
    return sorted(entries)


def _raw_digest(path: Path) -> str:
    """Digest a non-git directory exactly as :func:`archive_plain_dir` packs it.

    Same seed (``b""``), same tag and same order as that capture, so the
    post-capture barrier compares like for like.
    """
    hasher = _new_digest(b"")
    for rel in _raw_entries(path):
        try:
            _info, _data, digest, size = _read_entry(path, rel)
        except (OSError, ValueError) as exc:
            raise CaptureError(f"could not read {rel!r}: {exc}") from exc
        _digest_add(hasher, "u", rel, digest, size)
    return hasher.hexdigest()


def _claim_dest(root: Path, stem: str, *, limit: int = 1000) -> Path:
    """Create a fresh archive directory; never reuse an existing one."""
    root.mkdir(parents=True, exist_ok=True)
    for index in range(limit):
        candidate = root / (stem if index == 0 else f"{stem}.{index + 1}")
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        return candidate
    raise CaptureError(f"no free archive destination for {stem!r}")


def archive_tree(repo, state, path: Path, *, target_root: Path | None = None,
                 stem: str | None = None) -> dict:
    """Capture one worktree's uncommitted work (REC-02).

    Writes ``<root>/stranded/<task>-<fence>/`` containing:

    * ``diff.patch``      -- ``git diff HEAD --binary`` (all tracked changes);
    * ``untracked.tar``   -- every untracked, non-ignored file;
    * ``ignored.tar``     -- every ignored file, when the tree has any;
    * ``RESULT.md``       -- a copy of the agent's own result, when present;
    * ``manifest.json``   -- task, fence, base commit, counts, sha256s and a
      ``tree_digest`` of exactly the bytes the archive stores.

    This **only copies**; it never modifies or deletes the worktree.  The
    capture is complete or it is reported as failed: every listed file is
    read once and packed, and any failure removes the partial archive
    directory.  A destination is never reused, so a second capture of the
    same fence cannot hide the first.
    """
    path = Path(path)
    task_id, fence = parse_name(path.name)
    root = Path(target_root) if target_root else archive_root(repo)
    failed = {"name": path.name, "archived": False}

    try:
        base, diff, untracked, ignored = _scan_tree(repo, path)
        hasher = _new_digest(diff)
        dest = _claim_dest(root, stem or (f"{task_id}-{fence}"
                                          if fence is not None else path.name))
    except (CaptureError, OSError) as exc:
        return dict(failed, reason=str(exc))

    try:
        # Byte-for-byte: never pass this through a text-mode write.
        _write_file(dest / "diff.patch", diff)
        untracked_packed = _pack_files(path, untracked,
                                       dest / "untracked.tar", hasher, "u")
        ignored_packed = 0
        if ignored:
            ignored_packed = _pack_files(path, ignored,
                                         dest / "ignored.tar", hasher, "i")

        result_src = path / ".pmwork" / "RESULT.md"
        has_result = result_src.is_file()
        if has_result:
            _write_file(dest / "RESULT.md", result_src.read_bytes())

        task = state.tasks.get(task_id) if state is not None else None
        manifest = {
            "task": task_id,
            "fence": fence,
            "worktree": path.name,
            "state": task.state if task is not None else "?",
            "base_commit": base,
            "tracked_changes": bool(diff.strip()),
            "untracked_count": len(untracked),
            "untracked_packed": untracked_packed,
            "untracked_files": untracked[:500],
            "ignored_count": len(ignored),
            "ignored_packed": ignored_packed,
            "ignored_files": ignored[:500],
            "result_md": has_result,
            "diff_bytes": len(diff),
            "diff_sha256": hashlib.sha256(diff).hexdigest(),
            "untracked_tar_bytes": (dest / "untracked.tar").stat().st_size,
            "untracked_tar_sha256": _sha256_file(dest / "untracked.tar"),
            "tree_digest": hasher.hexdigest(),
            "capture_version": 2,
            "archived_at": _now_iso(),
        }
        if ignored_packed:
            manifest["ignored_tar_bytes"] = (dest / "ignored.tar").stat().st_size
            manifest["ignored_tar_sha256"] = _sha256_file(dest / "ignored.tar")
        # Also byte-faithful: no platform newline translation for the manifest.
        _write_file(dest / "manifest.json",
                    (json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
        # H2: the manifest described the tree as it was when packing began.
        # Re-scan before calling the capture complete; a file that appeared
        # during the capture must fail it, not be silently omitted.
        try:
            settled = _quiescence_digest(repo, path)
        except CaptureError as exc:
            raise CaptureError(
                f"the worktree changed while it was being captured: {exc}"
            ) from exc
        if settled != manifest["tree_digest"]:
            raise CaptureError(
                "the worktree changed while it was being captured")
    except (CaptureError, OSError, ValueError, tarfile.TarError) as exc:
        # A partial archive must not be mistaken for a complete one.
        shutil.rmtree(dest, ignore_errors=True)
        return dict(failed, reason=str(exc))

    return {"name": path.name, "archived": True, "dest": str(dest),
            "diff_bytes": manifest["diff_bytes"],
            "untracked_count": len(untracked),
            "ignored_count": len(ignored),
            "tree_digest": manifest["tree_digest"]}


def archive_plain_dir(path: Path, *, target_root: Path, stem: str) -> dict:
    """Capture a directory that is not a git worktree, in REC-02's shape.

    A stale ``%TEMP%/pmk-merge-*`` directory whose repository is gone still
    holds bytes that exist nowhere else, so it is captured before it is
    removed.  There is no base commit, so ``diff.patch`` is empty and every
    non-directory entry lands in ``untracked.tar``; :func:`verify_archive`
    then re-checks it exactly as it does a lease capture (counts, sha256 and
    a ``tree_digest`` rebuilt from the archive's own bytes).
    """
    path = Path(path)
    root = Path(target_root)
    failed = {"name": path.name, "archived": False}
    try:
        files = _raw_entries(path)
        dest = _claim_dest(root, stem)
    except (CaptureError, OSError) as exc:
        return dict(failed, reason=str(exc))
    hasher = _new_digest(b"")
    try:
        _write_file(dest / "diff.patch", b"")
        packed = _pack_files(path, files, dest / "untracked.tar", hasher, "u")
        manifest = {
            "task": stem,
            "fence": None,
            "worktree": path.name,
            "state": "?",
            "base_commit": None,
            "raw": True,
            "tracked_changes": False,
            "untracked_count": len(files),
            "untracked_packed": packed,
            "untracked_files": files[:500],
            "ignored_count": 0,
            "ignored_packed": 0,
            "result_md": False,
            "diff_bytes": 0,
            "diff_sha256": hashlib.sha256(b"").hexdigest(),
            "untracked_tar_bytes": (dest / "untracked.tar").stat().st_size,
            "untracked_tar_sha256": _sha256_file(dest / "untracked.tar"),
            "tree_digest": hasher.hexdigest(),
            "capture_version": 2,
            "archived_at": _now_iso(),
        }
        _write_file(dest / "manifest.json",
                    (json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
        # Same barrier as a git capture: the directory must still be exactly
        # what was packed, or it is kept.
        if _raw_digest(path) != manifest["tree_digest"]:
            raise CaptureError(
                "the directory changed while it was being captured")
    except (CaptureError, OSError, ValueError, tarfile.TarError) as exc:
        shutil.rmtree(dest, ignore_errors=True)
        return dict(failed, reason=str(exc))
    return {"name": path.name, "archived": True, "dest": str(dest),
            "raw": True, "diff_bytes": 0, "untracked_count": len(files),
            "ignored_count": 0, "tree_digest": manifest["tree_digest"]}


def _tar_entries(tar_path: Path) -> tuple[list[str], str]:
    try:
        with tarfile.open(tar_path, "r") as tf:
            return [m.name for m in tf.getmembers() if not m.isdir()], ""
    except (OSError, tarfile.TarError) as exc:
        return [], f"{tar_path.name} is unreadable: {exc}"


def _verify_tar(dest: Path, manifest: dict, kind: str, *,
                required: bool) -> list[str]:
    """Check one tar against the counts and hashes its manifest claims."""
    count = manifest.get(f"{kind}_count")
    packed = manifest.get(f"{kind}_packed")
    if not isinstance(count, int) or not isinstance(packed, int):
        return [f"manifest.json has no {kind}_count/{kind}_packed"]
    problems: list[str] = []
    if packed != count:
        problems.append(f"{kind}_packed ({packed}) does not equal "
                        f"{kind}_count ({count})")
    tar_path = dest / f"{kind}.tar"
    if not tar_path.is_file():
        if required or count:
            problems.append(f"{kind}.tar is missing")
        return problems
    if _sha256_file(tar_path) != manifest.get(f"{kind}_tar_sha256"):
        problems.append(f"{kind}.tar sha256 does not match the manifest")
    entries, error = _tar_entries(tar_path)
    if error:
        problems.append(error)
    elif len(entries) != packed:
        problems.append(f"{kind}.tar holds {len(entries)} entries but the "
                        f"manifest says {packed}")
    return problems


def _archive_digest(dest: Path, manifest: dict) -> tuple[str, list[str]]:
    """Recompute ``tree_digest`` from the archive's own bytes (H3).

    ``verify_archive`` used to check only that each file matched the hash
    in the manifest.  A manifest edited alongside a tampered archive could
    therefore still pass.  This rebuilds the digest from ``diff.patch`` and
    the tar members, so the archive has to reproduce the exact tree the
    capture claimed to store.
    """
    problems: list[str] = []
    try:
        diff = (dest / "diff.patch").read_bytes()
    except OSError as exc:
        return "", [f"diff.patch is unreadable: {exc}"]
    hasher = _new_digest(diff)
    for kind, tag in (("untracked", "u"), ("ignored", "i")):
        count = manifest.get(f"{kind}_count")
        if not isinstance(count, int):
            problems.append(f"manifest.json has no {kind}_count")
            continue
        tar_path = dest / f"{kind}.tar"
        if count == 0 and not tar_path.is_file():
            continue
        try:
            with tarfile.open(tar_path, "r") as tf:
                members = sorted(
                    (m for m in tf.getmembers() if not m.isdir()),
                    key=lambda m: m.name)
                if len(members) != count:
                    problems.append(
                        f"{kind}.tar holds {len(members)} entries but the "
                        f"manifest says {count}")
                for member in members:
                    if member.issym():
                        target = member.linkname
                        digest = hashlib.sha256(
                            b"link\0" + target.encode(
                                "utf-8", "surrogateescape")).hexdigest()
                        _digest_add(hasher, tag, member.name, digest, 0)
                    elif member.isfile():
                        handle = tf.extractfile(member)
                        if handle is None:
                            problems.append(
                                f"{kind}.tar member {member.name!r} is "
                                "unreadable")
                            continue
                        data = handle.read()
                        _digest_add(hasher, tag, member.name,
                                    hashlib.sha256(data).hexdigest(),
                                    len(data))
                    else:
                        problems.append(
                            f"{kind}.tar member {member.name!r} is neither "
                            "a file nor a symlink")
        except (OSError, tarfile.TarError) as exc:
            problems.append(f"{kind}.tar is unreadable: {exc}")
    return hasher.hexdigest(), problems


def verify_restore(repo, dest: Path) -> tuple[bool, list[str]]:
    """Prove the captured diff applies to its recorded base commit.

    Archive self-verification proves the bytes are consistent; it does not
    prove the stored patch can reconstruct the captured tracked changes.
    Before a reclaim may delete the tree, create a throwaway worktree at the
    manifest's ``base_commit`` and apply the patch there.  Any failure keeps
    the source tree on disk.
    """
    dest = Path(dest)
    manifest_path = dest / "manifest.json"
    if not manifest_path.is_file():
        return False, ["manifest.json is missing"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return False, [f"manifest.json is unreadable: {exc}"]

    base = str(manifest.get("base_commit") or "").strip()
    if (len(base) not in (40, 64)
            or any(char not in "0123456789abcdefABCDEF" for char in base)):
        return False, ["manifest.json has no valid base_commit"]
    patch = dest / "diff.patch"
    if not patch.is_file():
        return False, ["diff.patch is missing"]

    code, out, err = repo.git("rev-parse", "--verify", f"{base}^{{commit}}")
    if code != 0:
        detail = (err.strip() or out.strip() or "not found")[:500]
        return False, [f"base commit {base} is unavailable: {detail}"]
    resolved_base = out.strip()
    if patch.stat().st_size == 0:
        # No tracked changes: the base commit itself is the complete restore.
        return True, []

    try:
        temp = Path(tempfile.mkdtemp(prefix=".pmk-restore-",
                                     dir=str(repo.root)))
        temp.rmdir()
    except OSError as exc:
        return False, [f"could not create a restore worktree: {exc}"]

    try:
        code, out, err = repo.git("worktree", "add", "--detach", str(temp),
                                  resolved_base, timeout=120)
        if code != 0:
            detail = (err.strip() or out.strip() or "git worktree add failed")[:500]
            return False, [f"could not create restore worktree: {detail}"]
        code, out, err = repo.git("apply", str(patch.resolve()), cwd=temp,
                                  timeout=120)
        if code != 0:
            detail = (err.strip() or out.strip() or "git apply failed")[:500]
            return False, [f"diff.patch does not apply to base {base}: {detail}"]
        return True, []
    finally:
        repo.git("worktree", "remove", "--force", str(temp), timeout=120)
        shutil.rmtree(temp, ignore_errors=True)


def verify_archive(dest: Path) -> tuple[bool, list[str]]:
    """Re-read an archive and prove it is complete, not just self-consistent.

    Beyond hash agreement this checks the invariant a silent omission would
    break: the number of files packed equals the number the capture listed,
    and each tar really holds that many entries.  A capture that dropped a
    file must never verify, because verification is what authorises the
    deletion of the only copy.
    """
    dest = Path(dest)
    problems: list[str] = []
    manifest_path = dest / "manifest.json"
    if not manifest_path.is_file():
        return False, ["manifest.json is missing"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return False, [f"manifest.json is unreadable: {exc}"]

    if not manifest.get("tree_digest"):
        problems.append("manifest.json has no tree_digest")

    diff = dest / "diff.patch"
    if not diff.is_file():
        problems.append("diff.patch is missing")
    elif _sha256_file(diff) != manifest.get("diff_sha256"):
        problems.append("diff.patch sha256 does not match the manifest")

    problems.extend(_verify_tar(dest, manifest, "untracked", required=True))
    problems.extend(_verify_tar(dest, manifest, "ignored", required=False))
    if not problems:
        digest, digest_problems = _archive_digest(dest, manifest)
        problems.extend(digest_problems)
        if not digest_problems and digest != manifest.get("tree_digest"):
            problems.append("archive contents do not reproduce tree_digest")
    return (not problems), problems


#: Suffix of the sidecar lock held for the duration of a reclaim.
LOCK_SUFFIX = ".reclaim.lock"


def _lock_path(path: Path) -> Path:
    return path.parent / f".{path.name}{LOCK_SUFFIX}"


def _lock_is_stale(lock: Path) -> bool:
    """A lock is stale only when its holder is provably gone."""
    try:
        payload = json.loads(lock.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    pid = payload.get("pid")
    if pid is None:
        return False
    return not plat.same_process(int(pid), payload.get("creation_time"))


def _acquire_lock(path: Path) -> tuple[Path | None, str]:
    """Take the per-worktree reclaim lock, or say why it cannot be taken."""
    lock = _lock_path(path)
    holder = {"pid": os.getpid(),
              "creation_time": plat.process_info(os.getpid()).creation_time,
              "at": _now_iso()}
    payload = json.dumps(holder).encode("utf-8")
    for _attempt in range(2):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if _lock_is_stale(lock):
                try:
                    lock.unlink()
                except OSError:
                    pass
                continue
            return None, f"another reclaim holds {lock.name}"
        except OSError as exc:
            return None, f"cannot create {lock.name}: {exc}"
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
        except OSError as exc:
            try:
                lock.unlink()
            except OSError:
                pass
            return None, f"cannot write {lock.name}: {exc}"
        return lock, ""
    return None, f"another reclaim holds {lock.name}"


def _release_lock(lock: Path | None) -> None:
    if lock is None:
        return
    try:
        lock.unlink()
    except OSError:
        pass


def recorded_processes(state, task_id: str, fence: int | None) -> list[dict]:
    """Every process the log says was started for this task and fence.

    A fix round starts a second process.  Reading only the newest
    ``AGENT_STARTED`` would leave the older one writing into a tree the
    reaper is about to delete.
    """
    if state is None:
        return []
    found: list[dict] = []
    seen: set[tuple[int, object]] = set()
    for event in state.events:
        if event.type != "AGENT_STARTED" or event.subject != task_id:
            continue
        if fence is not None and event.fence != fence:
            continue
        payload = event.payload or {}
        pid = payload.get("pid")
        if pid is None:
            # H4: a start record without a pid is not evidence that no
            # process was started.  Keep it so the deletion barrier can
            # refuse rather than silently treating it as absent.
            found.append({"pid": None, "creation_time": None,
                          "profile": payload.get("profile", ""),
                          "adapter": payload.get("adapter", "")})
            continue
        identity = (int(pid), payload.get("creation_time"))
        if identity in seen:
            continue
        seen.add(identity)
        found.append({"pid": identity[0],
                      "creation_time": identity[1],
                      "profile": payload.get("profile", ""),
                      "adapter": payload.get("adapter", "")})
    return found


def live_conflicts(processes: list[dict]) -> list[dict]:
    """Processes that are alive now, with whether their identity matched."""
    conflicts: list[dict] = []
    for proc in processes:
        pid = proc.get("pid")
        if pid is None:
            continue
        info = plat.process_info(int(pid))
        if not info.alive:
            continue
        recorded = proc.get("creation_time")
        verified = (recorded is not None and info.creation_time is not None
                    and int(recorded) == int(info.creation_time))
        conflicts.append({"pid": int(pid), "verified": bool(verified),
                          "profile": proc.get("profile", "")})
    return conflicts


def _unverifiable_processes(processes: list[dict]) -> list[dict]:
    """H4: start records whose process cannot be checked at all."""
    return [p for p in processes if p.get("pid") is None]


def _deletion_refusal(repo, state, path: Path, *, allow_scratch: bool = False,
                      root: Path | None = None) -> str:
    """H1: only a direct, unprotected worktree with no live lease.

    *root* is the container whose direct children may be reclaimed; by
    default the lease worktree root (``<repo>/work``).  A scratch prune
    passes the parent of a merge tree instead.

    *allow_scratch* additionally permits a directory whose name is **not**
    ``<task>-<fence>`` -- the canary/gate/merge scratch trees the fleet
    leaves behind and the lease-only rule refuses.  Such a tree holds no
    lease, so the active-lease guard cannot apply to it; the protected-name
    and containment checks still do.
    """
    root = Path(root) if root is not None else worktree_root(repo)
    try:
        root_resolved = root.resolve()
        target_resolved = path.resolve()
    except OSError as exc:
        return f"cannot resolve the worktree path: {exc}"
    if path.name in PROTECTED:
        return f"{path.name} is protected; refusing to delete it"
    if path.is_symlink() or target_resolved.parent != root_resolved:
        return "not a direct child of the worktree root"
    task_id, fence = parse_name(path.name)
    if fence is None:
        if not allow_scratch:
            return "not a lease worktree name"
        return ""
    if state is None:
        return "no Kernel state; cannot prove the lease is inactive"
    # Only an *active* lease may refuse reclamation.  ``state.leases`` can
    # still hold an entry for a task that has left ACTIVE_STATES (for example
    # after PREMISE_REFUTED), and reading that raw table made a finished
    # task's worktree permanently unreclaimable; the active set is the
    # authority on what is still held.
    lease = state.active_leases().get(task_id)
    if lease is not None and lease.fence == fence:
        return "an active lease still owns this worktree"
    task = state.tasks.get(task_id)
    if task is not None and task.state == "LEASED" and lease is None:
        return "the task is still marked LEASED"
    return ""


def reclaim_after_capture(repo, state, path: Path, *,
                          target_root: Path | None = None,
                          extra_processes: list[dict] | None = None,
                          allow_scratch: bool = False,
                          root: Path | None = None,
                          stem: str | None = None,
                          remove_parent: bool = False) -> dict:
    """REC-01: capture a worktree, verify it, prove quiescence, remove it.

    This is the **only** function that deletes a worktree.  It never
    deletes anything whose capture did not verify, so a reclaim cannot
    lose work that was not first stored under ``stranded/``.  A tree that
    does not exist, or whose capture or removal fails, is left in place
    and the result says why.

    H4 adds two guards around the deletion:

    * the sidecar lock serialises reclaims of one worktree, and
    * no process recorded for the lease may be alive — and after the
      capture the tree is digested again, so anything that wrote to it
      while it was being captured keeps it on disk.

    A **scratch** reclaim (``allow_scratch=True``) extends this to a
    directory the lease path refuses: a non-lease name under *root*, or a
    ``%TEMP%/pmk-merge-*`` tree.  Such a directory is still protected-name
    and containment checked, still captured and verified, and — when it is
    not itself a git worktree, as a stale merge directory is not — captured
    as raw bytes (:func:`archive_plain_dir`) rather than as a git diff.
    ``stem`` names its archive, and ``remove_parent`` drops the now-empty
    parent (a ``pmk-merge-*`` directory around a ``merge`` worktree).

    Returns a result dict; ``reclaimed`` is true only when the worktree
    was actually removed.
    """
    path = Path(path)
    result: dict = {"worktree": str(path), "reclaimed": False, "archived": False}
    if not path.is_dir():
        result["reason"] = "not on disk"
        return result

    # H1: never delete a protected path, a path outside work/, or a tree
    # whose lease is still active.  This is checked before any archive or
    # lock work, so a refusal leaves no side effects.
    refusal = _deletion_refusal(repo, state, path, allow_scratch=allow_scratch,
                                root=root)
    if refusal:
        result["reason"] = refusal
        return result

    task_id, fence = parse_name(path.name)
    processes = (recorded_processes(state, task_id, fence)
                 + list(extra_processes or []))
    unverifiable = _unverifiable_processes(processes)
    if unverifiable:
        result["reason"] = ("a recorded process has no pid; cannot prove "
                            "it is not writing to the tree")
        result["processes"] = unverifiable
        return result
    busy = live_conflicts(processes)
    if busy:
        result["reason"] = ("a process may still be writing to the tree: "
                            + ", ".join(str(p["pid"]) for p in busy))
        result["processes"] = busy
        return result

    lock, reason = _acquire_lock(path)
    if lock is None:
        result["reason"] = reason
        return result
    try:
        # A process can start between the check above and the lock.
        busy = live_conflicts(processes)
        if busy:
            result["reason"] = ("a process may still be writing to the tree: "
                                + ", ".join(str(p["pid"]) for p in busy))
            result["processes"] = busy
            return result

        is_git = is_git_worktree(repo, path)
        if is_git:
            capture = archive_tree(repo, state, path, target_root=target_root,
                                   stem=stem)
        elif allow_scratch:
            capture = archive_plain_dir(
                path,
                target_root=(Path(target_root) if target_root
                             else archive_root(repo)),
                stem=stem or path.name)
        else:
            result["reason"] = "not a git worktree"
            return result
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

        if is_git:
            # Restore proof: the archive must be able to reconstruct the
            # captured tracked changes on its recorded base before deletion.
            # A raw directory capture has no base commit, so there is no
            # patch to replay; verify_archive already proved its bytes.
            restored, restore_problems = verify_restore(repo, dest)
            if not restored:
                result["reason"] = ("restore proof failed: "
                                    + "; ".join(restore_problems))
                return result
            result["restore_verified"] = True

        # The barrier: the tree must still be exactly what was captured.
        try:
            digest = (_quiescence_digest(repo, path) if is_git
                      else _raw_digest(path))
        except CaptureError as exc:
            result["reason"] = f"post-capture recheck failed: {exc}"
            return result
        if digest != capture.get("tree_digest"):
            result["reason"] = ("the worktree changed while it was being "
                                "captured; it was not removed")
            return result
        busy = live_conflicts(processes)
        if busy:
            result["reason"] = ("a process may still be writing to the tree: "
                                + ", ".join(str(p["pid"]) for p in busy))
            result["processes"] = busy
            return result

        if is_git:
            code, out, err = repo.git("worktree", "remove", "--force", str(path))
            if code != 0:
                result["reason"] = ("git worktree remove failed: "
                                    f"{(err.strip() or out.strip())}")
                return result
        else:
            try:
                _rmtree_force(path)
            except OSError as exc:
                result["reason"] = f"could not remove the directory: {exc}"
                return result
        result["reclaimed"] = True
    finally:
        _release_lock(lock)
    # Runs after the lock is released, so the lock file is not itself the
    # thing that stops the parent directory from being empty.
    if result["reclaimed"] and remove_parent:
        _remove_empty_parent(path, result)
    return result


def _remove_empty_parent(path: Path, result: dict) -> None:
    """After a scratch reclaim, drop the parent when it is now empty.

    A ``%TEMP%/pmk-merge-*`` directory normally holds only its ``merge``
    worktree, so once that worktree is reclaimed the parent is empty.  Any
    remaining entry is kept and reported rather than deleted.
    """
    parent = path.parent
    try:
        leftovers = sorted(p.name for p in parent.iterdir())
    except OSError:
        return
    if leftovers:
        result["parent_kept"] = leftovers[:20]
        return
    try:
        parent.rmdir()
        result["parent_removed"] = True
    except OSError as exc:
        result["parent_note"] = f"empty parent not removed: {exc}"


def discover_merge_trees(temp_root: Path | str | None = None) -> list[dict]:
    """Report scratch merge worktrees under ``%TEMP%/pmk-merge-*``.

    Read-only discovery: the trees are listed for operator visibility but never
    removed by :func:`prune`.
    """
    root = Path(temp_root) if temp_root is not None else Path(tempfile.gettempdir())
    if not root.is_dir():
        return []
    found: list[dict] = []
    for path in sorted(root.glob("pmk-merge-*")):
        try:
            if not path.is_dir():
                continue
            found.append({"name": path.name, "path": str(path),
                          "bytes": dir_bytes(path)})
        except OSError:
            continue
    return found


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

    Every actual removal goes through :func:`reclaim_after_capture`, so it
    takes the per-worktree lock, refuses while a recorded process is alive,
    and is re-checked against its capture before ``git worktree remove``.
    A tree ``git status`` calls clean can still hold ignored files, so it
    is captured too rather than deleted on the strength of that status.

    Scratch merge trees under ``%TEMP%/pmk-merge-*`` are reported in
    ``merge_trees`` for visibility and are never removed here.
    """
    recs = records(repo, state)
    candidates: list[dict] = []
    skipped: list[dict] = []
    merge_trees = discover_merge_trees()

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
        candidates.append(r)

    removed: list[str] = []
    archived: list[dict] = []
    if not dry_run:
        for r in candidates:
            # H4: one function removes a worktree, so every removal takes
            # the lock and the quiescence barrier.
            outcome = reclaim_after_capture(repo, state, Path(r["path"]))
            if not outcome.get("reclaimed"):
                skipped.append({"name": r["name"],
                                "reason": outcome.get("reason",
                                                      "reclaim failed")})
                continue
            removed.append(r["name"])
            archived.append({"name": r["name"],
                             "dest": outcome.get("archive", "")})

    return {
        "dry_run": dry_run,
        "candidates": [c["name"] for c in candidates],
        "removed": removed,
        "archived": archived,
        "skipped": skipped,
        "counts": {"candidates": len(candidates), "removed": len(removed),
                   "archived": len(archived), "skipped": len(skipped)},
        "recoverable_bytes": sum(c["bytes"] for c in candidates),
        "merge_trees": merge_trees,
    }


# ---------------------------------------------------------------------------
# Scratch trees -- the non-lease worktrees the fleet leaves behind
# ---------------------------------------------------------------------------

def scratch_records(repo, state) -> list[dict]:
    """Directories under ``work/`` whose name is not ``<task>-<fence>``.

    These are the canary and gate worktrees (``gate-*``, ``H1-H4-*``,
    ``launcher-repair-*``): real git worktrees, but not leases, so the
    lease-only :func:`prune` refuses them by name.
    """
    return [record(repo, state, p) for p in iter_dirs(repo)
            if parse_name(p.name)[1] is None]


def merge_tree_records(temp_root: Path | str | None = None) -> list[dict]:
    """Every ``%TEMP%/pmk-merge-*`` directory, with the worktree it holds."""
    out: list[dict] = []
    for tree in discover_merge_trees(temp_root):
        parent = Path(tree["path"])
        worktree = parent / "merge"
        out.append({"name": parent.name,
                    "path": str(parent),
                    "merge": str(worktree) if worktree.is_dir() else "",
                    "has_worktree": worktree.is_dir(),
                    "bytes": tree["bytes"]})
    return out


def prune_scratch(repo, state, *, dry_run: bool = True,
                  target_root: Path | None = None,
                  temp_root: Path | str | None = None,
                  include_work: bool = True,
                  include_merge: bool = True) -> dict:
    """Reclaim the non-lease scratch trees the fleet leaves behind.

    Two classes, both of which the lease-only :func:`prune` refuses:

    * a directory under ``work/`` whose name is not ``<task>-<fence>``
      (a canary or gate tree); and
    * a ``%TEMP%/pmk-merge-*`` directory -- the ``merge`` worktree it holds,
      or the directory itself when that worktree is gone.

    Dry-run by default.  Every removal goes through
    :func:`reclaim_after_capture`, so each tree is captured (REC-02, or a
    raw directory capture when it is not a git worktree) and the capture is
    verified before anything is deleted.  A merge directory is removed in
    full only once its worktree is gone and nothing else remains in it.
    """
    root = Path(target_root) if target_root else archive_root(repo)
    planned: list[str] = []
    removed: list[dict] = []
    skipped: list[dict] = []

    candidates: list[tuple[str, Path, dict]] = []
    if include_work:
        for rec in scratch_records(repo, state):
            candidates.append(("work", Path(rec["path"]), {}))
    if include_merge:
        default_temp = Path(temp_root) if temp_root is not None \
            else Path(tempfile.gettempdir())
        for rec in merge_tree_records(temp_root):
            parent = Path(rec["path"])
            if rec["has_worktree"]:
                candidates.append(("merge", parent / "merge",
                                   {"root": parent, "remove_parent": True}))
            else:
                candidates.append(("merge-dir", parent,
                                   {"root": default_temp}))

    for kind, path, extra in candidates:
        name = path.parent.name if kind == "merge" else path.name
        planned.append(name)
        if dry_run:
            continue
        outcome = reclaim_after_capture(repo, state, path, target_root=root,
                                        allow_scratch=True, stem=name, **extra)
        entry = {"name": name, "kind": kind, "path": str(path),
                 "reclaimed": bool(outcome.get("reclaimed")),
                 "archive": outcome.get("archive", ""),
                 "reason": outcome.get("reason", "")}
        if outcome.get("reclaimed"):
            removed.append(entry)
        else:
            skipped.append(entry)

    return {
        "dry_run": dry_run,
        "include_work": include_work,
        "include_merge": include_merge,
        "candidates": planned,
        "removed": removed,
        "skipped": skipped,
        "counts": {"candidates": len(planned), "removed": len(removed),
                   "skipped": len(skipped)},
    }
