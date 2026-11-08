# Repair drift classification (P0.3)

**Date:** 2026-11-08 · **Base:** `ebe46ce` · **Method:** `git status --porcelain`, `git diff --numstat`,
`git diff --ignore-cr-at-eol`, `git show HEAD:<path> | file -`, and direct inspection.
**Rule applied:** nothing is deleted; tracked files are either committed with their real content or restored to
the committed bytes; untracked scratch artifacts move to `quarantine/2026-11-08/` with a manifest.

## Tracked modifications

| Path | Raw diff | Finding | Action |
|---|---|---|---|
| `.pm/events/2026-11-07.jsonl` | +97 | Kernel ledger, append-only, real events | **Not committed.** It is live Kernel-owned state; committing the ledger mid-window would freeze a partial slice. Left for the Kernel's own cadence. |
| `.pm/views/ledger.md`, `.pm/views/status.md` | ±6 | projections of the ledger | Regenerated with `pmk views`. **Not committed** for the same reason as the ledger. |
| `HANDOFF.md` | 224 | real session memory | Commit. |
| `agents.toml` | 325 | **real operator edit**: `max_total_agents` 100 → 10, new overseer order, `pi-orca-*` profiles | Validate with `pmk fleet check`, then commit. |
| `docs/PDD.md` | 54 | real re-scope to the CNA project (G-001/G-002) | Commit with the P2 oracle change. |
| `docs/free-models.md` | 37 | reference data, real | Commit. |
| `pilot/decisions.md` | **731 / 720** | **CRLF churn + 11 real lines.** `git diff --ignore-cr-at-eol` = **+11 / −0**: the working copy already contained D-58, D-59, D-60, D-61 which were never committed. Working file was CRLF while the committed file is LF. | Normalised to LF, content preserved, committed. A blind commit would have rewritten the whole decision log. |
| `pi-test.txt` | 2 | scratch probe | Restored to committed bytes. |
| `pytest_junit.xml` | 2 | generated test artifact | Restored to committed bytes. |

## Untracked triage

| Class | Examples | Count | Action |
|---|---|---|---|
| Evidence cited by decision records | `report-umaws-problems-and-issues-v1.md`, `proposal-*.md`, `assessment-*.md`, `incident-report-*.md`, session reports | ~60 | **Kept in place.** They are the provenance the decision log references; moving them would break citations. |
| Patch series and one-off scripts | `*.patch` (13), `check_*.py`, `fix_*.py`, `renumber*.py`, `decide_q61.py`, `submit_*.py` | ~35 | Moved to quarantine, manifest written. |
| Test/collection dumps | `pytest_*.txt`, `collect*.txt`, `cc_out.txt`, `cc_err.txt`, `cov_test.txt`, `eng_test.txt` | ~15 | Moved to quarantine. |
| Scratch text | `single.txt`, `small.txt`, `fleetonly.txt`, `fleetq.txt`, `queue_raw.txt`, `agents-bak.toml` | 6 | Moved to quarantine. |
| Ledger history | `.pm/events/2026-10-31.jsonl.bak` | 1 | Moved to quarantine (a backup copy, not the live log). |
| Live ledger | `.pm/events/2026-11-08.jsonl` | 1 | **Left alone** — Kernel-owned. |

`quarantine/` is added to `.gitignore`, so the move is recorded in git history while the files themselves stay on disk, untracked.

## Pre-existing failures recorded, not fixed

`pmk sentinel` is **red at baseline** (exit 1) and was red before this repair:

| Invariant | Finding | Disposition |
|---|---|---|
| I6 | `INTEGRATED` events for T-0118, T-0119, T-0127, T-0129, T-0130 carry no bundle reference | Historical ledger content. Fixing it would mean rewriting the event log, which the Kernel owns and this repair forbids. Recorded in the checkpoint and in D-68's draft. |
| I13 | `view status.md does not equal the projection` — persists after `pmk views` | Suspected CRLF/normalisation mismatch in the projection writer. Out of scope for the isolation repair; recorded. |

Consequence for the plan: the P4 gate cannot say "sentinel clean". It says **"sentinel unchanged from the recorded baseline"**, with the five I6 findings and the I13 finding listed explicitly. Claiming clean would be false.
