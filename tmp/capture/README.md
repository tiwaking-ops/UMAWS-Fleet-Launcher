# Phase 1 protective capture — 2026-11-09

Repository: `C:\temp\projects\testproject1`
Capture base: `e7d272504f16d6c75a0805b56f01ad5ba7f10be6` (`main`)
Archive: `C:\temp\projects\umaws-repair-archive-2026-11-09`

## Artefacts

| Artefact | Size / count | SHA-256 |
|---|---|---|
| `tracked-changes.patch` (`git diff --binary`) | 361,682 bytes, 284 status entries | `420b4ff6606f29d5e81d37b7e8517ef289510343e8d2a2436e3bc3c22290ee51` |
| `untracked.zip` | 300 entries (298 listed at snapshot; gate log appended during capture) | `5b98ccd289bd7d08ae63e281912c6f32016e63bd0f099c79e9983cbf8ddb1937` |
| `working-tree-status.txt` | 284 lines | (in archive) |
| `untracked-list.txt` | 298 paths | (in archive) |
| `git-worktree-list.txt` | 44 entries at capture | (in archive) |
| `pmk-status.txt`, `pmk-worktree-list.txt`, `head-log.txt`, `capture-note.txt` | — | (in archive) |
| `SHA256SUMS.txt` | — | (in archive) |

`.pm/` runtime state (events `2026-11-07.jsonl`, views) is included in the patch
as disaster-recovery material only; it is never committed (N-02).

## Restorability proofs

- **Tracked patch:** applied with `git apply` in a detached worktree at
  `e7d2725`; re-generated `git diff --binary` hash equals the original
  `420b4ff…` exactly (byte-identical restore).
- **Untracked archive:** 300 entries extracted; 299 files hashed against the
  live tree. 298 matched; the only mismatch is `tmp/rb-2-head-gate.log`, which
  the running gate appended to after the snapshot. One entry
  (`tmp/review-followups/`) is a directory, skipped by `read_bytes`.
- Scratch restore worktree `work/restore-check-1794222600` was removed after the
  proof; it held no unique work.

## Deviation

`tar` could not write through the Git Bash path (`Cannot execute remote shell`);
the untracked set was archived with Python `zipfile` instead (self-contained,
same path inventory). Recorded as deviation D-P1 in the completion report.

## Kernel worktree capture

`pmk worktree archive --all-dirty` captured 7 dirty lease worktrees under
`stranded/` (T-0142-119, T-0145-122, T-0146-124, T-0189-156, the two H1–H4 clean
trees, and the launcher-repair clean tree). `--dry-run` first; no refusals, no
forced deletions. Output: `tmp/capture-pmk-archive.txt`.
