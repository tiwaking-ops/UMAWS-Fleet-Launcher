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
