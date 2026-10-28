# UMAWS Fleet — Formal Repair Proposal

**Title:** Comprehensive Repair and Stabilisation Plan for UMAWS Fleet (testproject1)
**Author:** Claude Code
**Document Version:** 1.0
**Preparation Date:** 2026-10-26
**Repository:** `C:\temp\projects\testproject1`
**Inspected Commit:** `6764d54` (Merge branch 'pmk/T-0003-3' into HEAD)
**Working Tree:** Dirty (5 modified files, 12 untracked files)
**Document Status:** Proposed — awaiting owner approval

---

## 1. Assessment Scope and Verification Limitations

### 1.1 Scope

This proposal covers the complete UMAWS Fleet codebase at `C:\temp\projects\testproject1` (branch `main`, commit `6764d54`), including:

- Kernel (`src/pmk/`) — event log, task cards, leases, views, sentinel, PDD lint, API, CLI
- Fleet (`src/fleet/`) — profiles, adapters, Dispatcher, Harness, recovery ladder L0–L4, Conductor, merge queue, Overseer runner, project lifecycle, manual launcher
- Console (`src/console/`) — FastAPI view layer on 127.0.0.1:8765 with 7 tabs
- QuotaGate (`src/quotagate/`) — hierarchical quota engine (M0–M2 core)
- Tests (`tests/`) — 242 tests across Kernel, Fleet, QuotaGate
- Pilot record (`pilot/`) — STATE.md, decisions.md, spikes, pilot-report.md, demo_one_click.py
- Coordination state (`.pm/`) — event log, views, tasks, evidence, pins, policy, constitution

### 1.2 Verification Performed

| Check | Command | Result |
|-------|---------|--------|
| Test suite | `pytest -q` (with PYTHONPATH=src) | **242 passed** in 63.18s |
| Kernel sentinel | `pmk sentinel` | Clean — 1 finding: I16 CLAUDE.md edited out-of-band |
| Hash chain | `pmk status` | I1 verifies (275 events) |
| Project status | `pmk status` | state=NEW, tasks=3 (DONE=1, LEASED=1, READY=1) |
| Fleet status | `pmk fleet status` | 6 profiles, cap=100, dispatch_paused=true |
| Console | `python -m console.app` + HTTP probes | All 11 GET routes return 200 |
| Demo lifecycle | `python pilot/demo_one_click.py` | **Exit 0** — full fake-CLI lifecycle to DONE |
| Editable install | `pip show umaws-fleet` | **Points at C:\temp\projects\toy1** (wrong tree) |
| Import resolution | `import pmk, fleet, quotagate` | Without PYTHONPATH: imports from toy1; with: testproject1 |

### 1.3 Limitations

- **Concurrent modifications:** Other sessions modified the repo during assessment (HEAD moved, event log grew, untracked files appeared). All state readings are point-in-time.
- **Sandbox constraints:** Some tests may behave differently in the user's actual environment vs. this sandbox.
- **No live provider calls:** Verification used only fake CLI and local execution; no real model endpoints were called.
- **Toy projects not fully inspected:** toy1/toy2/toy3 sibling directories were referenced but not exhaustively analysed.

---

## 2. Executive Summary

### 2.1 Diagnosis

**The UMAWS Fleet engine is sound; the operational environment is miswired.**

- ✅ **Working:** Test suite (242/242), Kernel sentinel (clean), hash chain (verified), one-click demo (green), Console (all routes), CLI surface, PDD linter.
- ❌ **Broken:** Virtual environment executes `toy1`'s source, not this repo's; project state stuck at `NEW`; task T-0003 marked `DONE` with a **failing oracle**; dead-pid lease on T-0001; no PDD.md; documentation drift; three known defect diffs unapplied.

### 2.2 Root Causes (Confidence Levels)

| # | Root Cause | Confidence | Evidence |
|---|------------|------------|----------|
| RC1 | Editable install bound to sibling `toy1` | **Critical — 100%** | `pip show`, import resolution, all three reports |
| RC2 | T-0003 evidence bundle shows oracle failure (`ok: false, exit: 1`) but task is `DONE` | **Critical �� 100%** | `.pm/evidence/EB-T-0003-3/bundle.json`, ledger.md |
| RC3 | T-0001 lease held by dead pid 16380 with no exit event | **High — 95%** | `pmk status`, status.md, worktrees T-0001-1, T-0001-2 |
| RC4 | No PDD.md exists; BRIEF.md is a one-line stub pointing to toy1 | **High — 100%** | `docs/BRIEF.md`, `ls docs/`, pilot STATE |
| RC5 | Three queued defect fixes unapplied (D-53, D-55, D-56) | **High — 100%** | Pilot decisions.md, Beam report §6, Codebuff §7 |
| RC6 | Documentation describes old layout (`gateway/quotagate/` vs `src/quotagate/`) | **Medium — 90%** | README, proposals, directory structure |
| RC7 | QuotaGate CLI entry point broken (`ImportError: main`) | **Medium — 100%** | Direct test, Beam report §5.8 |
| RC8 | Event log and views dirty in working tree (I13 risk) | **Medium — 85%** | `git status`, `.pm/events/2026-10-25.jsonl` modified |

### 2.3 Recommendation Summary

**Do not run real multi-agent dispatch from this state.**

**Immediate Stabilisation (this week):**
1. Rebind editable install to `testproject1`
2. Audit and resolve T-0003 (failing oracle → DONE)
3. Recover dead lease T-0001 and clean worktrees
4. Write and lint PDD.md
5. Apply queued defect diffs D-55 → D-53/Q-005 → D-56
6. Fix QuotaGate CLI entry point
7. Commit or archive working-tree drift

**Then validate through project's own gates:**
8. Run sentinel, status, brief, demo_one_click
9. Execute controlled live-CLI test (one task, one profile)
10. Only then unpause dispatch

---

## 3. Detailed Findings

### 3.1 Critical Findings

#### FINDING-001 [Critical]: Editable Install Points at Wrong Repository

**Evidence:**
```
pip show umaws-fleet
Editable project location: C:\temp\projects\toy1
```
```python
# Without PYTHONPATH
import pmk  # → C:\temp\projects\toy1\src\pmk\__init__.py
# With PYTHONPATH=src
import pmk  # → C:\temp\projects\testproject1\src\pmk\__init__.py
```

**Impact:** Every documented manual command (`pmk`, `quotagate`, `start.ps1`) executes **toy1's code** against **testproject1's state**. Tests pass only because they run with explicit `PYTHONPATH=src`.

**Root Cause:** `pip install -e .` was run from `toy1` directory, or the venv was created in toy1 and reused.

**Fix:** Uninstall and reinstall editable from testproject1 root.

---

#### FINDING-002 [Critical]: T-0003 Marked DONE with Failing Oracle (Violates I5)

**Evidence:** `.pm/evidence/EB-T-0003-3/bundle.json`
```json
{
  "oracle_results": [
    {
      "cmd": "python -c \"import sys; sys.exit(0 if open('pi-test.txt').read().find('pi') >= 0 else 1)\"",
      "exit": 1,
      "ok": false
    }
  ],
  "resolved_models": [{"profile": "pi-orca-deepseek", "model": "", "family": "hermes"}]
}
```

**Ledger shows:** `T-0003 | x | DONE | implement | pi live dispatch test: write pi-test.txt | G-TEST-PI | 1/3 | fence 3`

**Impact:** Invariant I5 ("Oracles decide — no task reaches DONE without a passing gate_cmd and evidence bundle") is violated. The provenance record is also inconsistent: profile `pi-orca-deepseek` (family `deepseek`) but `resolved_models` shows `family: "hermes"` and `model: ""`.

**Root Cause:** Task was merged/integrated despite oracle failure. The merge queue gate check either didn't run or was bypassed.

**Fix:** Revert T-0003 to READY or REWORK; investigate merge queue logic; add regression test.

---

#### FINDING-003 [High]: Dead Lease on T-0001 (pid 16380)

**Evidence:**
```json
// pmk status
"active_leases": 1,
"tasks": {"LEASED": 1, ...}
```
```markdown
// .pm/views/status.md
| `T-0001` | opencode-strongest | opencode | 2 | - | 16380 | - | pi live dispatch test: write hello.txt |
```
Process 16380 confirmed not running. No `LEASE_REVOKED` or `AGENT_EXITED` event recorded. Two worktrees exist: `work/T-0001-1` and `work/T-0001-2` (same base commit `a93da88`).

**Impact:** Lease fence stuck at 2; task cannot be claimed by another worker; worktrees occupy disk.

**Fix:** Revoke lease via `pmk` (bump fence), quarantine worktrees, return task to READY.

---

### 3.2 High Findings

#### FINDING-004 [High]: Project Governance Documents Missing/Broken

| File | State | Required By |
|------|-------|-------------|
| `docs/PDD.md` | **Missing** | Pilot lifecycle, PDD lint, close-check gate |
| `docs/BRIEF.md` | One-line stub: `C:/temp/projects/toy1/docs/BRIEF.md` | `pmk project init`, Overseer briefing |
| `gateway/quotagate/` | Empty directory | README, proposals reference it |

**Impact:** `pmk pdd lint docs/BRIEF.md` fails with 8 errors. Project cannot progress from `NEW` → `PLANNING` → `RUNNING` per the documented lifecycle.

---

#### FINDING-005 [High]: Three Queued Defect Fixes Unapplied

| Defect | Description | Status | Required Ceremony |
|--------|-------------|--------|-------------------|
| **D-55** | `.gitattributes` eol=lf for pinned files + `pmk pins record` | Diff ready, unapplied | Class K (two-key) — pins change |
| **D-53/Q-005** | `AGENT_RESUMED` → `AGENT_RESTARTED` event label fix; queue id collision | Diff ready, unapplied | Standard |
| **D-56** | Failure classifier gap — `UNKNOWN` handling unverified | Diff ready, unapplied | Standard |

**Impact:** Known defects with exact diffs sit unapplied while new work accumulates. D-55 is a prerequisite for clean clones (pins verification).

---

#### FINDING-006 [High]: QuotaGate CLI Entry Point Broken

**Evidence:**
```
$ quotagate --help
ImportError: cannot import name 'main' from 'quotagate.__main__' (C:\temp\projects\toy1\src\quotagate\__main__.py)
```
`pyproject.toml` declares: `quotagate = "quotagate.__main__:main"`

**Impact:** QuotaGate CLI unusable; M1 proxy cannot be tested; operator cannot inspect quota state.

---

### 3.3 Medium Findings

#### FINDING-007 [Medium]: Working Tree Drift (I13 Risk)

**Modified (uncommitted):**
- `.pm/events/2026-10-25.jsonl` — one appended `SENTINEL_RUN` event
- `.pm/views/ledger.md`, `.pm/views/status.md` — regenerated views
- `agents.toml` — comment-only addition (free-model reference)
- `CLAUDE.md` — edited out-of-band (sentinel I16 finding)

**Untracked:**
- `.pm/events/2026-10-26.jsonl` — new day file
- 11 assessment/report files in repo root

**Impact:** Invariant I13 (views are projections of the log) may not hold if views were edited directly. The repo is permanently dirty under live use — daily event files should be `.gitignore`d or managed differently.

---

#### FINDING-008 [Medium]: Documentation Drift

| Document | References | Actual Location |
|----------|------------|-----------------|
| README.md | `gateway/quotagate/` | `src/quotagate/` |
| Proposals | `gateway/quotagate/` | `src/quotagate/` |
| Pilot STATE | `gateway/quotagate/` | `src/quotagate/` |

**Impact:** New contributors and agents will look in the wrong place. The empty `gateway/quotagate/` directory is misleading.

---

#### FINDING-009 [Medium]: requirements.lock Has UTF-8 BOM

**Evidence:** `pip install --dry-run --no-index -r requirements.lock` parses but with BOM warning. PowerShell `>` redirection writes UTF-8-SIG.

**Impact:** Cosmetic but violates project's own rule (read with `utf-8-sig`). Could cause issues in strict parsers.

---

#### FINDING-010 [Medium]: pytest Summary Suppressed by Stacked `-q`

**Evidence:** `pyproject.toml` has `addopts = "-q"`; running `pytest` shows only dots. Running `pytest -v` shows full test names.

**Impact:** Hard to debug test failures; no visibility into which tests run.

---

### 3.4 Low Findings

#### FINDING-011 [Low]: Repository Hygiene — Assessment Sprawl

12 untracked assessment/report files in repo root:
- `CLAUDE.7z`, `assesment-claude-toy3-v1.md`, `prompt-claude-to-hermes-toy3-instructions.md`, `prompt-perplexity-repair-v1.md`
- `pytest_out.txt`, `pytest_out2.txt`, `report-beam-project-state-v1.md`, `report-codebuff-project-state-v1.md`, `report-deepseek-project-state-v1.md`, `single.txt`

**Impact:** Noise; risk of stale guidance; credentials potentially in archives.

---

#### FINDING-012 [Low]: Model Routing Volatility

Recent commits repoint free models:
- `kilo-auto/free` → `kilo/kilo-auto/free`
- `cline-mimo` → five offered free models (none verified)
- `opencode-strongest` → `poolside/laguna-s-2-1:free`

**Impact:** Live capacity depends on unverified free endpoints. Profile `family` declarations don't match resolved models (e.g., pi-orca-deepseek shows `family: "hermes"` in evidence bundle).

---

## 4. Options Analysis

### Option A: Repair In Place (Recommended)

**Approach:** Fix the 12 findings above in priority order, validate through project's own gates, then resume normal operation.

| Pros | Cons |
|------|------|
| Preserves all history, event log, evidence bundles | Requires careful sequencing (D-55 before D-53) |
| Engine already passes all tests | Must resolve T-0003 oracle contradiction |
| Pilot record and decisions.md retained | Working tree drift needs reconciliation |
| Minimal disruption to pilot trajectory | Editable install rebind required |

**Effort:** ~2-3 days of focused work.

---

### Option B: Clean Successor Build

**Approach:** Create a new repository (`umaws-fleet-v2`), port the verified-good engine code (Kernel, Fleet core, Console, QuotaGate), leave the original `testproject1` archived and untouched. Apply lessons learned: clean editable install, proper PDD from day one, verified model profiles only.

| Pros | Cons |
|------|------|
| Clean slate — no accumulated drift | Loses event log history (275 events) |
| Can fix architectural decisions (e.g., event log rotation) | Evidence bundles and pilot record not portable |
| Forces verification of all profiles before use | Duplicates effort on working components |
| Owner can run both in parallel | Migration of `.pm/` state non-trivial |

**Effort:** ~1-2 weeks for equivalent functionality.

---

### Option C: Hybrid — Stabilise Then Fork

**Approach:** Execute Option A stabilisation (steps 1-7), then **tag** the clean state as `stable/baseline`. From there, either continue on main or create a successor worktree/branch for architectural changes.

| Pros | Cons |
|------|------|
| Preserves optionality | Slightly more process |
| Baseline tag provides rollback point | Requires discipline to not skip stabilisation |
| Owner can approve successor after seeing repaired system work | |

**Effort:** Same as Option A + optional fork overhead.

---

### Recommendation: **Option C (Hybrid)**

**Rationale:**
1. The engine **is** working (242 tests, sentinel clean, demo green). Throwing it away wastes verified work.
2. The defects are **environmental and stateful**, not architectural — editable install, stale leases, missing docs, unapplied diffs.
3. A clean baseline tag gives the owner a decision point: "continue here" vs "fork for redesign" with evidence.
4. The pilot's own gate posture (Class K, two-key) requires preservation of history — Option B violates this.

---

## 5. Execution Backlog

### Phase 0: Preparation (Owner Decisions Required)

| # | Decision | Required From Owner | Default Recommendation |
|---|----------|---------------------|------------------------|
| D-01 | Proceed with repair vs. clean successor? | **Yes/No** | Repair (Option C) |
| D-02 | Archive or discard untracked assessment files? | Archive location | `archive/assessments/2026-10-26/` |
| D-03 | Daily event log files: commit or `.gitignore`? | Commit/Ignore | `.gitignore` `.pm/events/*.jsonl`; keep views committed |
| D-04 | Which free models to verify for profiles? | Model list | Verify current `agents.toml` models via controlled live test |
| D-05 | PDD.md: write from scratch or adopt toy1's? | Brief/Goals | Adopt CSV-to-Markdown toy (demo_one_click pattern) |
| D-06 | T-0003 resolution: REWORK, VOID, or keep DONE with explanation? | REWORK/VOID/Keep | REWORK — oracle failed, evidence proves it |

---

### Phase 1: Environment Stabilisation (Day 1)

| Step | Command | Verification |
|------|---------|--------------|
| 1.1 | `cd C:\temp\projects\testproject1` | — |
| 1.2 | `.\.venv\Scripts\python.exe -m pip uninstall -y umaws-fleet` | `pip show umaws-fleet` → not found |
| 1.3 | `.\.venv\Scripts\python.exe -m pip install -e . --no-deps` | `pip show umaws-fleet` → Location: testproject1 |
| 1.4 | `.\.venv\Scripts\python.exe -c "import pmk, fleet, quotagate; print(pmk.__file__)"` | All three resolve to `C:\temp\projects\testproject1\src\...` |
| 1.5 | `.\.venv\Scripts\python.exe -m pmk.cli sentinel` | `ok: true`, findings only I16 (CLAUDE.md) |
| 1.6 | `.\.venv\Scripts\python.exe -m pmk.cli status` | Project state, tasks, chain length reported |

**Gate:** All verifications pass before proceeding.

---

### Phase 2: State Recovery (Day 1-2)

| Step | Action | Command / Procedure | Verification |
|------|--------|---------------------|--------------|
| 2.1 | **Revoke T-0001 dead lease** | `pmk lease revoke T-0001 --reason "dead pid 16380"` | `pmk status` → T-0001 READY, active_leases=0 |
| 2.2 | **Quarantine T-0001 worktrees** | `git worktree remove work/T-0001-1`<br>`git worktree remove work/T-0001-2` | `git worktree list` → only main + T-0003-3 |
| 2.3 | **Resolve T-0003** | If D-06=REWORK: `pmk task rework T-0003 --reason "oracle failed"`<br>If D-06=VOID: `pmk task void T-0003 --reason "oracle failed, premise refuted"` | Ledger shows T-0003 as REWORK or VOID, not DONE |
| 2.4 | **Regenerate views** | `pmk views rebuild` (or `pmk sentinel` triggers) | `git diff .pm/views/` → only expected changes |
| 2.5 | **Verify hash chain** | `pmk sentinel` | `ok: true`, I1 chain verifies |

---

### Phase 3: Governance Documents (Day 2)

| Step | Action | Command / Procedure | Verification |
|------|--------|---------------------|--------------|
| 3.1 | **Write PDD.md** | Create `docs/PDD.md` per template in fleet-launcher-proposal.md §12.G<br>Goals: G-001, G-002 with oracles; gate_cmd; architecture sketch | `pmk pdd lint docs/PDD.md` → exit 0 |
| 3.2 | **Update BRIEF.md** | Replace stub with actual brief (per D-05) | `pmk brief --role overseer` renders without error |
| 3.3 | **Project init (if needed)** | `pmk project init --brief docs/BRIEF.md` | `pmk status` → project_state=PLANNING or RUNNING |

---

### Phase 4: Apply Queued Defect Fixes (Day 2-3)

**Order is critical: D-55 (pins) must be first — Class K, two-key.**

| Step | Defect | Procedure | Verification |
|------|--------|-----------|--------------|
| 4.1 | **D-55: pins + .gitattributes** | 1. Record current pins: `pmk pins record`<br>2. Add `.gitattributes`: `*.toml eol=lf`<br>`*.md eol=lf`<br>3. `pmk pins record` (Class K — requires two-key queue item)<br>4. Commit | Fresh clone → `pmk sentinel` clean, pins verify |
| 4.2 | **D-53/Q-005: event label + queue collision** | Apply diff from pilot/decisions.md D-53<br>Run regression test for queue id collision | `pytest -k "queue"` passes |
| 4.3 | **D-56: failure classifier** | Apply diff from pilot/decisions.md D-56<br>Add fixture for UNKNOWN classification | Classifier test passes; Console shows UNVERIFIED flag where appropriate |

---

### Phase 5: Code Fixes (Day 3)

| Step | Fix | Procedure | Verification |
|------|-----|-----------|--------------|
| 5.1 | **QuotaGate CLI** | Fix `src/quotagate/__main__.py` to export `main`<br>or update `pyproject.toml` entry point | `quotagate --help` prints help, exits 0 |
| 5.2 | **requirements.lock UTF-8** | Re-save as UTF-8 (no BOM): `Get-Content requirements.lock \| Set-Content -Encoding utf8 requirements.lock` | `pip install --dry-run` no BOM warning |
| 5.3 | **pytest summary** | Change `pyproject.toml`: `addopts = ""` (remove `-q`) | `pytest` shows test names; `pytest -q` still works |
| 5.4 | **Documentation paths** | Update README.md, proposals: `gateway/quotagate/` → `src/quotagate/`<br>Remove empty `gateway/quotagate/` directory | `grep -r "gateway/quotagate"` → no hits |

---

### Phase 6: Repository Hygiene (Day 3)

| Step | Action | Procedure |
|------|--------|-----------|
| 6.1 | **Archive assessment files** | `mkdir -p archive/assessments/2026-10-26`<br>`mv *.md *.txt *.7z single.txt archive/assessments/2026-10-26/` (preserve `report-*.md`) |
| 6.2 | **Handle event log files** | Per D-03: add `.pm/events/*.jsonl` to `.gitignore`<br>Commit `.pm/views/*.md` (they're projections) |
| 6.3 | **Commit or stash working tree** | `git add -A`<br>`git commit -m "stabilise: rebind env, recover state, apply D-55/D-53/D-56, fix CLI, docs"` |
| 6.4 | **Tag baseline** | `git tag stable/baseline-2026-10-26` |

---

### Phase 7: Validation Through Gates (Day 3-4)

| Step | Validation | Command | Pass Criteria |
|------|------------|---------|---------------|
| 7.1 | **Test suite** | `pytest -q` | 242 passed |
| 7.2 | **Sentinel** | `pmk sentinel` | `ok: true`, findings ⊆ {I16} |
| 7.3 | **Status** | `pmk status` | project_state ≠ NEW, tasks consistent, chain verifies |
| 7.4 | **Fleet status** | `pmk fleet status` | 6 profiles, cap=100, dispatch_paused=true |
| 7.5 | **Console** | `PYTHONPATH=src python -m console.app` + HTTP GET /api/* | All 11 routes 200 |
| 7.6 | **Demo lifecycle** | `python pilot/demo_one_click.py` | Exit 0, DONE, sentinel clean, 2 evidence bundles |
| 7.7 | **Briefing** | `pmk brief --role overseer` | Renders constitution, policy hash, project state, tasks |

**Gate:** All 7 validations pass before any dispatch unpause.

---

### Phase 8: Controlled Live Integration Test (Day 4-5)

**Only after Phase 7 gate passes.**

| Step | Test | Procedure | Acceptance |
|------|------|-----------|------------|
| 8.1 | **Single task, single profile** | Create toy project (CSV-to-Markdown per demo)<br>Claim T-0001 (plan task) with `opencode-strongest`<br>Run Dispatcher for 1 task only | Task completes → evidence bundle → oracle passes → merge → DONE |
| 8.2 | **Verify evidence independently** | Check `EB-*/bundle.json`: `oracle_results[].ok == true`<br>Verify outputs exist in worktree<br>Run gate_cmd manually | Independent verification confirms DONE |
| 8.3 | **Negative test** | Submit task with known-failing oracle<br>Verify system rejects (REWORK/VOID) | System does NOT mark DONE |
| 8.4 | **Recovery test** | Kill worker mid-task<br>Verify L1/L2 recovery activates<br>Task completes on resumed/fresh session | Recovery ladder works; fence unchanged for L1/L2 |

---

## 6. Testing Suite Recommendation

### 6.1 Three-Tier Test Architecture

| Tier | Scope | Trigger | Gate |
|------|-------|---------|------|
| **T1: Deterministic Offline** | All 242 unit/integration tests (Kernel, Fleet, QuotaGate)<br>Fake CLI only<br>Property tests on state machine | Every commit (CI) | **Blocks merge** — must pass |
| **T2: Controlled Live Integration** | Real CLI adapters (1 profile × 1 task)<br>Verified-free provider calls only<br>QuotaGate M1 proxy (when built) | Pre-dispatch unpause<br>Weekly scheduled | **Blocks dispatch unpause** — must pass |
| **T3: Fresh-Project E2E Acceptance** | `pmk project init` → brief → PDD → tasks → claim → worktree → oracles → merge → close-check → DONE<br>Independent verification of generated app | Pre-release<br>Major version | **Blocks release** — must produce working app |

### 6.2 Required New Tests

| Test ID | Description | Tier | Dependencies |
|---------|-------------|------|--------------|
| `test_t0003_oracle_gate` | T-0003 regression: failing oracle → task NOT DONE | T1 | D-56 classifier |
| `test_lease_revocation_dead_pid` | Dead pid lease revoked, fence bumped, task READY | T1 | Phase 2.1 |
| `test_merge_queue_gate_enforcement` | Gate failure quarantines submission, never merges | T1 | T-0003 root cause |
| `test_quota_gate_cli` | `quotagate --help` exits 0, prints help | T1 | Phase 5.1 |
| `test_pins_fresh_clone` | Clone repo → `pmk sentinel` clean, pins verify | T1 | D-55 |
| `test_profile_model_verification` | Each profile's declared model actually serves | T2 | D-04 decision |
| `test_e2e_csv2md` | Fresh brief → working CSV-to-Markdown app | T3 | Phase 3.1 PDD |

### 6.3 Negative Test Matrix (Must Demonstrate)

| Scenario | Expected Behaviour | Verification |
|----------|-------------------|--------------|
| Broken application (oracle fails) | Task → REWORK/VOID, not DONE | Check ledger, evidence bundle |
| Failed oracle (exit ≠ 0) | Submission quarantined, not merged | Check merge queue log |
| Missing evidence bundle | Kernel rejects SUBMITTED | Check event log |
| Unavailable model | Profile cooled, task reassigned | Check profile state, fleet status |
| Exhausted quota | Profile cooled with backoff, circuit breaker if systemic | Check fleet status, dispatch_paused |
| Dead worker (process gone) | Lease revoked, fence bumped, task READY | Check lease state, worktree quarantined |

---

## 7. Staged Validation Programme

| Stage | Name | Entry Criteria | Exit Criteria | Owner Decision |
|-------|------|----------------|---------------|----------------|
| **S0** | Baseline Capture | Current state documented | This proposal approved | Approve repair plan |
| **S1** | Environment Stabilised | Phase 1-3 complete | Editable install correct, PDD lint clean, state recovered | Confirm ready for defect fixes |
| **S2** | Defects Applied | Phase 4-5 complete | D-55/D-53/D-56 applied, CLI fixed, docs current | Confirm ready for validation |
| **S3** | Gates Green | Phase 7 complete | All 7 validations pass | Approve live test |
| **S4** | Live Integration | Phase 8.1-8.2 complete | One real task DONE with independent verification | Approve dispatch unpause |
| **S5** | Negative Tests | Phase 8.3-8.4 complete | All negative scenarios behave correctly | Approve production use |
| **S6** | Baseline Tagged | Phase 6.4 complete | `stable/baseline-2026-10-26` tagged | Archive or fork decision |

---

## 8. Free-Runtime Path Verification

### 8.1 Current Profile Model Routing (from agents.toml)

| Profile | Adapter | Declared Model | Family | Verified? |
|---------|---------|----------------|--------|-----------|
| hermes-oneshot | hermes | (none, oneshot) | anthropic | No |
| kilo-auto | kilo | kilo/kilo-auto/free | google | No |
| pi-orca-deepseek | pi | deepseek/deepseek-v4-flash-free | deepseek | No |
| cline-mimo | cline | cline-free/minimax-m3.1-flash | minimax | No |
| opencode-strongest | opencode | poolside/laguna-s-2-1:free | opencode | No |
| opencode-fallback | opencode | (none) | opencode2 | No |

### 8.2 Free-Runtime Verification Required

For each profile, the following must be established **before live dispatch**:

1. **Endpoint accessibility** — HTTP 200 from this machine, no auth errors
2. **Model identity** — Provider returns claimed model string in response headers/body
3. **Quota headers** — Presence/absence documented (QuotaGate M1 needs this)
4. **Failure modes** — QUOTA, AUTH, MODEL_GONE, NETWORK captured as fixtures
5. **Resume capability** — Session ID format, model-swap-on-resume verified

**No paid fallback:** If a profile cannot be verified free, it must be disabled (`pmk fleet disable <id>`) until verified.

### 8.3 QuotaGate M0–M2 Role

Current QuotaGate (M0–M2 core) provides:
- Hierarchical limits (RPM, TPM, RPD)
- Timezone-aware resets (DST handling)
- Rolling and fixed windows

**M1 (passthrough proxy) is NOT yet built.** Until M1 exists:
- Direct CLI profiles (`via_gateway: false`) have **no quota enforcement** by UMAWS
- Budgets are wall-time and restart-count only (L-F2 in fleet-launcher-proposal.md)
- Operator must manually monitor provider dashboards

---

## 9. Platform Execution Paths (Windows + WSL)

### 9.1 Supported Paths

| Component | Windows (Native) | WSL (Ubuntu) |
|-----------|------------------|--------------|
| **Shell** | PowerShell 5.1 / 7 (`-NoProfile -ExecutionPolicy Bypass`) | bash |
| **Python** | `py -3.12` → `.venv\Scripts\python.exe` | `python3.12` → `.venv/bin/python` |
| **Git** | Git for Windows ≥ 2.28 (`core.longpaths true`) | Git ≥ 2.28 |
| **Worktrees** | `C:\w\<project>\<task>-<fence>` (short path) | `/home/user/w/<project>/<task>-<fence>` |
| **Process Supervision** | `plat.py`: `CREATE_NO_WINDOW`, `taskkill /T /F`, pid+creation_time | `os.killpg`, `psutil` |
| **File Locks** | Sidecar `.lock` files (`msvcrt.locking`) | `fcntl.flock` |
| **Encoding** | `utf-8-sig` for all human-written files | `utf-8` |
| **Line Endings** | LF enforced via `.gitattributes` (D-55) | LF native |

### 9.2 Boundaries

- **Do not mix** Windows and WSL environments for the same project (different `.venv`, different process trees, different lock semantics).
- **Console** binds to `127.0.0.1:8765` — accessible from both Windows and WSL2 (via localhost forwarding).
- **CLI adapters** must be installed/authenticated in the target environment (Windows PowerShell or WSL bash).
- **Editable install** must be performed in the active environment.

---

## 10. Preservation and Archive Plan

| Artifact | Action | Location |
|----------|--------|----------|
| `.pm/events/*.jsonl` | Keep in repo (or `.gitignore` per D-03) | `.pm/events/` |
| `.pm/evidence/EB-*/` | **Never delete** — audit trail | `.pm/evidence/` |
| Worktree contents | Keep until branches merged/abandoned | `work/T-*/` |
| Assessment reports | Archive (don't delete) | `archive/assessments/2026-10-26/` |
| `CLAUDE.7z` | Extract, inspect for secrets, then archive | `archive/assessments/2026-10-26/` |
| `pytest_out.txt`, `pytest_out2.txt`, `single.txt` | Archive | `archive/assessments/2026-10-26/` |
| Pilot decisions.md, STATE.md | **Keep in repo** — authoritative history | `pilot/` |
| Git history | **Never rewrite** — event log depends on it | — |

**Credentials/secrets:** Scan all archives for API keys, tokens before sharing. The `CLAUDE.7z` archive must be inspected.

---

## 11. Decisions Required From Owner

| ID | Decision | Options | Recommendation |
|----|----------|---------|----------------|
| **D-01** | Repair vs. clean successor | Repair (Option A/C) / Successor (Option B) | **Repair (Option C)** |
| **D-02** | Assessment files disposition | Archive / Delete | **Archive** |
| **D-03** | Daily event logs in git | Commit / `.gitignore` | **`.gitignore`** (rebuildable) |
| **D-04** | Profile model verification | Verify all 6 / Verify subset / Disable unverified | **Verify all 6 via controlled live test** |
| **D-05** | PDD.md content | CSV-to-Markdown toy / Real project brief | **CSV-to-Markdown toy** (matches demo) |
| **D-06** | T-0003 resolution | REWORK / VOID / Keep DONE | **REWORK** |
| **D-07** | Dispatch unpause condition | After S3 / After S4 / After S5 | **After S4** (live integration proven) |

---

## 12. Diagnostics Performed and State Changes Made

### 12.1 Diagnostics (Read-Only)

- `git status`, `git log`, `git worktree list`
- `pip show umaws-fleet`, import resolution tests
- `pytest -q` (242 passed), `pytest -v` (full names)
- `pmk sentinel` (3×), `pmk status`, `pmk fleet status`, `pmk brief --role overseer`
- Console HTTP probes (11 routes)
- `python pilot/demo_one_click.py` (exit 0)
- Evidence bundle inspection (T-0003)
- Worktree inspection (T-0001-1, T-0001-2, T-0003-3)
- Source code review (Kernel, Fleet, Console, QuotaGate)
- Three assessment reports read in full

### 12.2 State Changes Made (This Session)

| Change | File | Reason |
|--------|------|--------|
| None yet | — | All diagnostics read-only |

**No modifications made to `.pm/`, source code, or configuration.** All investigation was non-destructive.

---

## 13. Unresolved Blockers and Unexecuted Tests

| Blocker | Description | Required To Resolve |
|---------|-------------|---------------------|
| **B-01** | T-0003 oracle failure vs DONE label contradiction | Owner decision D-06 + Phase 2.3 |
| **B-02** | Dead lease T-0001 (pid 16380) | Phase 2.1-2.2 (pmk lease revoke) |
| **B-03** | No PDD.md — project cannot progress | Owner decision D-05 + Phase 3.1 |
| **B-04** | Editable install bound to toy1 | Phase 1.2-1.3 (pip uninstall/install) |
| **B-05** | QuotaGate CLI broken | Phase 5.1 (fix __main__.py) |
| **B-06** | Model profiles unverified | Owner decision D-04 + Phase 8 |
| **B-07** | Concurrent session modifications during assessment | Schedule dispatch/assessment separately |

### Unexecuted Tests

| Test | Reason Not Run |
|------|----------------|
| Live CLI dispatch (any profile) | Requires Phase 1-7 gate pass; owner decision D-04 |
| QuotaGate M1 proxy | Not yet built (M0–M2 core only) |
| Overseer headless run (OpenCode) | Requires S-O1 spike verification |
| Scale drill F7 (100 slots) | Requires Phase 7 gate; fake CLI only |
| Multi-host / WSL path | Not in scope for this repair |

---

## 14. Conclusion

The UMAWS Fleet repository at `testproject1` contains a **healthy engine** (242 tests, clean sentinel, working demo) that is **operationally miswired** (wrong editable install, stale state, missing governance docs, unapplied fixes). 

The repair programme in this proposal addresses every confirmed defect with specific, verifiable steps. The staged validation programme ensures that no capability is assumed working without evidence — especially the critical invariant I5 (oracles decide).

**Upon approval of D-01 through D-07, implementation can begin immediately with Phase 1.** The baseline tag at Phase 6.4 will give the owner a clean decision point for any future architectural changes.

---

*End of proposal — `report-codebuff-recommendations-v1.md`, author Claude Code, version 1.0, 2026-10-26.*