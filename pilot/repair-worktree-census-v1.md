# Repair worktree census (P0.4)

Measured 2026-11-08. `pmk status` reports **15** worktrees; `git worktree list` reports **27** entries (**26** additional).
Read-only: nothing below was removed.

| Worktree | Branch | Size | Dirty paths | Branch merged into main |
|---|---|---|---|---|
| `agent-a8ea164055f940daf` | `worktree-agent-a8ea164055f940daf` | 6 MB | 28 | yes |
| `T-0118-100` | `pmk/T-0118-107` | 9 MB | 0 | yes |
| `T-0119-101` | `pmk/T-0119-101` | 11 MB | 0 | yes |
| `T-0130-102` | `pmk/T-0130-102` | 9 MB | 0 | yes |
| `T-0136-113` | `pmk/T-0136-113` | 9 MB | 0 | yes |
| `T-0136-114` | `pmk/T-0136-114` | 9 MB | 0 | yes |
| `T-0136-115` | `pmk/T-0136-115` | 9 MB | 0 | yes |
| `T-0139-116` | `pmk/T-0139-116` | 9 MB | 0 | yes |
| `T-0139-117` | `pmk/T-0139-117` | 10 MB | 0 | no |
| `T-0141-118` | `pmk/T-0141-118` | 9 MB | 0 | yes |
| `T-0142-119` | `pmk/T-0142-119` | 9 MB | 2 | yes |
| `T-0145-122` | `pmk/T-0145-122` | 13 MB | 2 | yes |
| `T-0145-123` | `pmk/T-0145-123` | 13 MB | 0 | yes |
| `T-0146-124` | `pmk/T-0146-124` | 13 MB | 1 | yes |
| `T-0148-120` | `pmk/T-0148-120` | 15 MB | 0 | no |
| `T-0150-121` | `pmk/T-0150-121` | 13 MB | 0 | yes |
| `merge` | `(detached)` | 11 MB | 0 | ? |
| `merge` | `(detached)` | 11 MB | 0 | ? |
| `merge` | `(detached)` | 11 MB | 0 | ? |
| `merge` | `(detached)` | 9 MB | 0 | ? |
| `merge` | `(detached)` | 11 MB | 0 | ? |
| `merge` | `(detached)` | 11 MB | 0 | ? |
| `merge` | `(detached)` | 11 MB | 1 | ? |
| `merge` | `(detached)` | 15 MB | 0 | ? |
| `merge` | `(detached)` | 11 MB | 0 | ? |
| `merge` | `(detached)` | 15 MB | 0 | ? |

## Reading

- A branch marked `yes` with 0 dirty paths is reclaimable after capture (REC-01 policy permits reclaim on reap).
- A branch marked `no` may hold unmerged work: it must be inspected, not deleted.
- The count gap (15 vs 26) means the Kernel does not know it owns 11 of these directories.
- Disposition is an operator decision (proposal §4.3 excludes deletion from this repair).

---

## Re-measurement 2026-11-09 (repair execution)

Measured with `pmk worktree list` and `git worktree list` after the Phase 1
capture (`tmp/rb-7-pmk-census.txt`, `tmp/rb-7-git-census.txt`).

- **`pmk`:** 32 worktrees, 417.6 MiB, **7 dirty** (all archived).
- **git:** **44** entries.
- **Union difference:** git knows 12 entries `pmk` does not — `main`, the
  `.claude/worktrees/agent-a8ea164055f940daf` tree, and **10**
  `%TEMP%/pmk-merge-*` trees. `pmk` counts 8 non-lease trees under `work/`
  (gate trees, the H1–H4 branch, the two H1–H4 clean trees, the launcher-repair
  clean tree, and the legacy cwd-fallback tree) as worktrees; their task/fence
  is `None` and state `?`.
- **Dirty capture:** `pmk worktree archive --all-dirty` captured all 7 dirty
  trees under `stranded/` (dry-run first, no refusals, no deletions):
  `T-0142-119`, `T-0145-122`, `T-0146-124`, `T-0189-156`,
  `H1-H4-clean-1794215552`, `H1-H4-clean-1794218904`,
  `launcher-repair-clean-1794220000`. Output: `tmp/capture-pmk-archive.txt`.
- **Deletion:** not performed. CP-3 was not exercised; the proposal reserves
  deletion for operator approval, and the archive is the prerequisite either
  way. The `%TEMP%/pmk-merge-*` trees remain untouched.

Delta from the 2026-11-08 measurement: +17 git entries and +17 pmk entries,
explained by the repair's detached gate/clean trees (`work/`) and the session's
new gate tree; no unexplained tree appeared.
