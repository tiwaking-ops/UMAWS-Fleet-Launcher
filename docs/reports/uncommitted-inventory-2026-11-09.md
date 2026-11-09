# Uncommitted inventory — 2026-11-09 (fleet launcher repair)

Recorded after slice commits S1–S5 on `repair/fleet-launcher-2026-11-09`.
The Phase 1 capture (`C:\temp\projects\umaws-repair-archive-2026-11-09`) holds
byte-verified copies of everything below that predates the slice commits.

## Disposition key

- **retain-untracked** — working paper or source material; stays on disk, not
  a product diff.
- **cited-evidence-retain** — referenced by a decision, report, or capture;
  deleting it would break provenance.
- **operator-to-decide** — no authority in this programme to commit or remove.
- **kernel-state** — live `.pm/` runtime state; never committed (N-02).
- **separate-work** — belongs to the CNA request, not this repair (A-12).

## Tracked modifications remaining after S1–S5

| Path | Class | Disposition |
|---|---|---|
| `.pm/events/2026-11-07.jsonl` | Kernel runtime | kernel-state |
| `.pm/views/ledger.md`, `queue.md`, `status.md` | Kernel views | kernel-state |
| `src/cna/data/scenario.py` | scenario-loader work | separate-work |
| `src/cna/engine/loop.py` | off-map stage-loop work | separate-work |
| `tests/test_scenario_loader.py` | scenario-loader test | separate-work |
| `tests/test_transport.py` | off-map transport test (now tracked, satisfying case `8.0`) | separate-work |

## Untracked material (non-`tmp/`, non-`stranded/`)

### Kernel state and capture

| Path | Disposition |
|---|---|
| `.pm/events/2026-11-08.jsonl`, `2026-11-09.jsonl` | kernel-state |
| `stranded/` (7 archived lease worktrees) | cited-evidence-retain |

### Repair evidence (retain)

| Path | Disposition |
|---|---|
| `pilot/evidence/launcher-repair-uncommitted-v1.{json,patch,patch.sha256}` | cited-evidence-retain |
| `pilot/evidence/canary-replacement-v1.{patch,precheck.json}` | cited-evidence-retain |

### Source proposals, assessments, handoffs (working papers)

| Group | Paths | Disposition |
|---|---|---|
| Synthesized source proposals | `docs/plans/proposal-glm-5-3-…`, `proposal-deepseek-…`, `proposal-mimo-2-6-…`; root `proposal-deepseek-umaws-fleet-parallel-decomposition-v1.md` | retain-untracked |
| Patch/assessment series | `assessment-claude-umaws-fleet-*` (17 files), `response-assessment-v3-…`, `relay-A-…`, `relay-C-…` | retain-untracked |
| Handoffs and prompts | `HANDOFF.previous.md`, `handoff-claude-…-v4.md`, `handoff-claude-…-v6.md`, `prompt-b5.txt`, `prompt-claim-complete1.md`, `prompt-complete-uwas-v1.md` | operator-to-decide |
| Incident and verification notes | `EVENT_LOG_VIOLATION_REPORT.md`, `report-answers-for-claude-incident-v1.md`, `verification-assessment-v2-…`, `verification-incident-order-path-v1.md`, `step1-canary-test-results.md` | retain-untracked |
| Project reports | `FINAL_REPORT-completed.md`, `report-freebuff-UMAWS-Fleet-Launcher-repair-v1.md`, `docs/reports/project-evaluation-2026-11-08-v1.md` | retain-untracked |
| CNA planning | `docs/plans/cna-p1b-p4-*`, `docs/plans/p1c2-data-gate-checklist.md`, `docs/plans/r04-r05-r06-data-intake-checklist.md`, `docs/pm-workflow-analysis-template-v1.md`, `docs/report-tiwas-full-list-project-workflow-systems-v1.md`, `docs/sources/*`, `docs/milestones/setup-report.md` | retain-untracked |
| Pilot assessments | `pilot/assessment/report-conductor-stall-v1.md`, `report-model-performance-v1.md` | cited-evidence-retain |

### Helper scripts (scratch)

`create_p0_tasks.py`, `create_t128.py`, `decide_q61.py`, `find_1203.py`,
`find_1205.py`, `find_seq.py`, `insert_1205.py`, `insert_both.py`,
`reset_blocked.py`, `submit_base_tasks.py`, `submit_new_base.py`,
`submit_t113.py`, `test_kernel_hash.py`, `test_parse.py`

Disposition: **operator-to-decide** — they are one-off ledger/DB helpers cited by
earlier sessions, captured in the Phase 1 archive; not product code.

### Separate CNA work

`tests/fixtures/scenario-60.22-partial.json` — retain-untracked; belongs to the
scenario-loader request, not this repair.

### `tmp/` evidence

`tmp/` holds this session's gate, slice, census, entry and restore-verification
logs, plus older cited evidence. **cited-evidence-retain**; no wholesale cleanup
is performed (proposal §12 reserves that decision).

## Summary

- Nothing unclassified: every remaining path fits one of the classes above.
- No untracked path was committed in S1–S5; the only new tracked files are the
  four slice commits plus `tools/check_clean_base.ps1`.
- The 2026-11-08 scratch quarantine (`quarantine/2026-11-08/`, D-68) is still
  tracked/ignored as before and is not touched here.
