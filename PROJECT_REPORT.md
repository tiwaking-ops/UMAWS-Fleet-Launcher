# UMAWS Fleet — Project Status Report

**Date:** 2026-10-28  
**Author:** Claude (Web) — `claude-sonnet-4-6`, high effort  
**Version:** 1.0  
**Base commit:** `9f2dbaa` (HEAD) — *merge: gate pytest.ini cleanup on the committed branch diff*  
**Repository:** `C:\temp\projects\testproject1` (git, branch `main`)

---

## 1. Summary

UMAWS Fleet is a Kernel-lite multi-agent coordination system that runs CLI
agents unattended through a Fleet Dispatcher and provides a browser-based
Console for monitoring. The Kernel (`pmk`) is the sole writer of coordination
state via an append-only JSONL event log; the Fleet supervises processes,
worktrees, and oracles; the Console provides a FastAPI view layer.

The project has completed Phase 1 (bootstrap) of pilot P-01 and is at
**project state: NEW** with **3 READY tasks** and **3 open queue items**. The
most recent work (v11) fixed a latent defect in the merge queue's pytest.ini
collision cleanup ordering.

---

## 2. Architecture Overview

| Component | Path | Lines | Dependencies |
|---|---|---|---|
| **Kernel** | `src/pmk/` | ~3,773 | Standard library only |
| **Fleet** | `src/fleet/` | ~3,507 | Kernel, standard library |
| **Console** | `src/console/` | ~375 | FastAPI, uvicorn |
| **QuotaGate** | `src/quotagate/` | ~903 | Standard library + tomli |
| **Tests** | `tests/` | ~2,190 lines across 13 files | pytest, fake CLI |

```
Operator ── browser ──► Console (FastAPI, 127.0.0.1:8765)
                          │
                          ▼
                    umaws app process
                      Conductor   lifecycle, wakes the Overseer
                      Dispatcher  selects a profile, claims a task
                      Adapters    hermes | kilo | cline | pi | opencode | fake
                      Harness     worktree, order file, oracles, evidence
                      pmk.api     the Kernel: the only writer of state
```

---

## 3. Build & Test Status

### Environment
- **Python:** 3.12.10 (venv at `.venv`)
- **Install:** `pip install -e .` (editable, required for `pmk` CLI)
- **Platform:** Native Windows (sidecar `.lock` files, `cmd.exe` shim peeling)

### Test Results
```
303 passed in 116.31s
```
- **JUnit XML:** `pytest_junit.xml` (303 tests, 0 failures, 0 errors, 0 skipped)
- **Test coverage:** Kernel, Fleet, and QuotaGate — all green
- **Sentinel:** `pmk sentinel` clean on the live repository

### Quick Start
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe -m pip install fastapi uvicorn httpx tzdata pytest
.\start.ps1              # Console on http://127.0.0.1:8765
python pilot/demo_one_click.py   # E2E lifecycle with fake CLI
```

---

## 4. Key Invariants

| ID | Name | Description |
|---|---|---|
| I2 | Kernel Only | Agents never write to `.pm/` directly; use `pmk` CLI or `pmk.api` |
| I5 | Oracles Decide | No task is promoted to `DONE` without a passing `gate_cmd` and evidence bundle in `.pm/evidence/` |
| I8' | Pinned Policy | `.pm/constitution.md` and `.pm/policy.toml` are hashed in `.pm/pins.sha256` |
| I13 | Views as Projections | `.pm/views/` (ledger, status, queue) must equal the projection of the log |
| I16 | Context Drift | All human-written files tracked; drift reported as findings (not stops) |

---

## 5. Recent Changes (v11)

### Commit `9f2dbaa` — *merge: gate pytest.ini cleanup on the committed branch diff*

**Problem:** `_cleanup_default_pytest_ini` was called **before** `commit_worktree`,
so the lease branch ref didn't exist yet and `git diff --name-only <base>..<branch>`
couldn't see the incoming pytest.ini change. Only the write_scope check could fire.

**Fix:**
- Moved `_cleanup_default_pytest_ini(repo, task, branch)` to **after** `commit_worktree`
  succeeds and **before** the merge worktree setup
- Removed the write_scope shortcut from the function — it now relies solely on the
  git diff check (sufficient because if pytest.ini is in scope, commit_worktree
  commits it and the diff sees it)
- Updated the docstring to reflect that the check runs AFTER commit_worktree

**Files changed:**
- `src/fleet/merge.py` — 18 insertions, 26 deletions
- `tests/fleet/test_regressions.py` — updated `test_merge_cleanups_pytest_ini_via_diff_not_writescope`

**Ordering verification:**
- **OLD** (cleanup before commit): diff is empty → cleanup doesn't fire → untracked pytest.ini
  collides with fast-forward → merge fails
- **NEW** (cleanup after commit): diff shows pytest.ini → cleanup deletes untracked root file →
  fast-forward succeeds

### Commit `548885e` — *Fleet hardening v5-v11*

Includes 24 files of broader hardening: PMK_ACTOR attribution, merge gate classification,
Hermes session parsing, void and type guards, sentinel fixes (31 files total in the patch).

---

## 6. Current State

### Project State
- **Project state:** NEW
- **Tasks:** 3 (all READY)
- **Active leases:** 0
- **Open queue items:** 3 (Q-005, Q-006, Q-007)
- **Incidents:** 2
- **Policy version:** p-2026-10-23

### Open Queue Items

| ID | Topic | Recommended |
|---|---|---|
| Q-005 | Dispatcher: AGENT_RESUMED mislabelled when mode=new (D-53) | Apply diff, re-run T-0003, assert no AGENT_RESUMED with mode=new |
| Q-006 | I4 finding for T-0003: task integrated with revoked fence 3 (historical) | Acknowledge, resolve later |
| Q-007 | I5 finding for T-0003: task promoted with invalid bundle (acceptance oracles failed) | Rework T-0003 |

### Incidents

| When | Subject | Severity | Message |
|---|---|---|---|
| 2026-10-22T19:47:14Z | queue | error | Q-001 duplicate id (fixed, regression test added, see D-32) |
| 2026-10-26T05:48:28Z | seq 281/282 | warn | No-op TASK_REVOKED events from tmp script, no semantic effect on state |

### Ready Tasks

| ID | Type | Title | Hint | Write Scope |
|---|---|---|---|---|
| T-0001 | implement | pi live dispatch test: write hello.txt | — | hello.txt |
| T-0002 | implement | pi live dispatch test: write hello.txt | pi-orca-deepseek | hello.txt |
| T-0003 | implement | pi live dispatch test: write pi-test.txt | pi-orca-deepseek | pi-test.txt |

---

## 7. Completed Work (Phase 1)

Per `pilot/STATE.md`, the following are **complete and verified**:

- **Kernel-lite** (pilot v1 §9): event log with hash chain, torn-tail repair, task cards,
  leases with fencing, views, briefing, sentinel, PDD lint
- **Platform layer** (`plat.py`): sidecar locks, spawn, tree kill, pid+creation-time
  identity, npm `.cmd` shim peeling, BOM-tolerant reads, RAM guard
- **Context machinery** (`context.py`): I15 lint (CIP §14.6 rules), I16 drift check,
  sync task, snapshot-based revert
- **Fleet Dispatcher**: profiles, adapters, selection, harness (two-phase start/poll),
  recovery ladder L0–L4, Conductor, merge queue, Overseer runner, project lifecycle
- **Console**: FastAPI on 127.0.0.1 with SSE and 7 tabs (Projects, Fleet, Tasks, Queue,
  Overseer, Manual launcher, Metrics)
- **QuotaGate**: hierarchical quota engine (M0–M2 core) — scopes, windows, DST handling
- **Caliber 1.55.2** installed and pinned; spikes S1–S5 complete
- **G1 baseline**: 10 context files generated, sanitised, linted, hashed, committed
- **Acceptance tests**: F1-shaped (fake CLI); F7 scale drill passes 100/100 at peak
  100 concurrent slots (105s, 7,491 MB RAM min)
- **234+ tests** (now 303 with regression tests) passing; sentinel clean

### Provider CLIs — Measured (S-A1 live run)
- **Hermes, Kilo, Cline, Pi, OpenCode** all run headless
- **Kilo, Cline, Pi** resume from briefing alone
- **Pi** resumes on a different model
- **OpenCode** handover PASSES (session_id: `20261028_153733_33d968`)
- Cline's MODEL_GONE and OpenCode's QUOTA captured as fixtures

---

## 8. What is NOT Built / Not Verified

| Item | Status | Notes |
|---|---|---|
| QuotaGate M1 passthrough proxy | Not built | Upstream measured: no quota headers, `/v1` disagreement |
| QuotaGate M3 failover | Not built | Needs provider keys (authorisation) |
| QuotaGate M5 Kernel contract | Not built | |
| Caliber context sync | Installed but not auto-sync | S1–S5 spikes complete, G1 baseline done |
| Real-CLI E2E acceptance tests (F1, F4, F7, F9, F14) | Not run | Require real LLMs or 100+ slots |
| Context generator injection safety (V-07) | Unproven | T4 premise did not reproduce |
| Five cline free models verified | Not verified | Offered but not tested (needs live calls) |
| Verifier family declared | Not declared | All `agents.toml` profiles: `family = "unknown"` |
| REWORK task re-dispatch | Not implemented | Tasks still never re-dispatched after rework |
| Auth-expired failure classification | Not separate | Spends retries instead of being classified distinctly |
| Production access controls | Partial | `submit`, `verify`, `integrate`, `revoke` guarded only by Overseer prompt |

---

## 9. Minor Leftovers and TODO Notes

These are low-priority items flagged for a future touch:

1. **Docstring inconsistency in `_cleanup_default_pytest_ini`**: The docstring
   still mentions "either because the task's write scope declares it, or because it
   appears in the branch's diff" — but the write_scope shortcut was removed. The
   `task` parameter is now unused in the function body.

2. **Test docstring mismatch**: `test_merge_cleanups_pytest_ini_via_diff_not_writescope`
   docstring says the write scope is `["config/"]`, but the actual code uses
   `["config/", "pytest.ini"]`.

3. **Uncommitted working tree changes** (not part of the v11 fix):
   - `.pm/` changes (events, views) — these are runtime artifacts
   - `.claude/skills/quotagate-rule/SKILL.md`
   - `CLAUDE.md` and `README.md`
   - `pilot/STATE.md`

4. **Junk files in working tree** (should be gitignored):
   - `pytest_out*.txt`, `pytest_full*.txt`, `pytest_tail.txt`, `single.txt`
   - `session-report-cc-v*.md` (v1 through v11)
   - `report-*.md` (multiple vendor reports)
   - `*.patch` files (v5–v8, combined)
   - `CLAUDE.7z`
   - `tmp/` directory (contains `revert_t0003*.py` scripts — should be deleted)

---

## 10. Development Conventions

As documented in `CLAUDE.md` and `.claude/rules/`:

- **Platform:** Native Windows. Use `src/pmk/plat.py` for sidecar locks (`.lock`)
  and process-tree kills.
- **Spawning:** Always use `argv` lists. Never use shell strings. Use
  `plat.resolve_executable` to peel npm `.cmd` shims.
- **Errors:** Read all human-written files with `utf-8-sig` to handle PowerShell BOMs.
- **Kernel:** Standard library only. No external dependencies in `src/pmk/`.
- **State:** Kernel is the sole writer. Use `Kernel.record_event()` for all state
  changes. Hash chain maintained in `EventLog`.

---

## 11. File Layout

| Path | What |
|---|---|
| `src/pmk/` | Kernel: events, tasks, leases, views, briefing, sentinel, API, CLI |
| `src/fleet/` | Profiles, adapters, selection, harness, recovery ladder, Dispatcher, Conductor, merge queue, Overseer |
| `src/console/` | FastAPI Console (127.0.0.1:8765) |
| `src/quotagate/` | Hierarchical quota engine (M0–M2 core) |
| `tests/fleet/` | 41 Fleet tests + fake CLI (`fakecli.py`) |
| `tests/` | ~150 tests across Kernel, Fleet, QuotaGate |
| `pilot/` | STATE.md, decisions.md, logs, spikes, pilot report, demo |
| `.pm/` | Coordination state: event log, views, task cards, evidence |
| `AGENTS.md` | OpenCode context |
| `CLAUDE.md` | Claude Code context |

---

## 12. Decisions and Attribution

This report (v1.0) was produced by **Claude (Web)**, model `claude-sonnet-4-6`
at high effort. The most recent code changes were authored and committed by
`umaws-pilot <umaws-pilot@localhost>`.

**Co-Authored-By:** Claude Code <noreply@anthropic.com>
