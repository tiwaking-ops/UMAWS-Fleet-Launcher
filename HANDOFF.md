# HANDOFF — UMAWS Fleet CFNA Project (2026-11-01)

## Project State: PAUSED

**Root:** `C:\temp\projects\testproject1` (UMAWS repo root)  
**Last update:** 2026-11-10
**I1 chain:** Verifies (3630 events)
**Kernel:** pmk v0.1.0

> **Current evidence:** the 2026-11-01/02 sections below are historical. See **Latest evidence (2026-11-10)** at the end for the current state, the later canary **path** passes (T-0190/T-0191/T-0196; only T-0191 and T-0196 carry `gate_output`) and the A8 activation.

---

## What Was Fixed

### 1. I1 Hash Chain Repair
- **Problem:** Chain broken at seq 1203–1207 (missing seq 1204/1205, orphan seq 1203)
- **Fix:** Renumbered all 10 event files contiguously from 1→2659, recomputed all hashes with `prev_hash` field
- **Files:** `.pm/events/2026-10-30.jsonl` through `.pm/events/2026-11-01.jsonl`

### 2. Editable Install Fixed
- **Problem:** `.venv/Lib/site-packages/__editable__.umaws_fleet-0.1.0.pth` pointed to worktree `work/T-0101-65/src`
- **Fix:** Changed to `C:\temp\projects\testproject1\src`

### 3. Merge Fast-Forward Failure (merge.py)
- **Problem:** `merge --ff-only` failed when main diverged during temp worktree creation
- **Fix:** Added fallback to `merge --no-ff --no-edit` in `src/fleet/merge.py:249-257`
- **Result:** Both T-0127 and T-0129 integrated successfully

### 4. Profile Priorities & Poolside Removal
- **File:** `agents.toml`
- **Changes:** Poolside/laguna-s-2.1 removed (1-hr free tier then throttle); cline profiles priority 30-33; pi-orca 1-4; kilo 29; opencode 40-70; fleet_cap=6
- **Policy:** `.pm/policy.toml` lease TTL = 120 min

---

## Base Tasks Integrated (DONE)

| Task | Fence | Merge Commit | Deliverables in Main |
|------|-------|--------------|---------------------|
| T-0127 | 97 | e7cea34 | `pytest.ini`, `tests/test_smoke.py` |
| T-0129 | 98 | 0fc8d0c | `docs/rules/{fleet-spawning,kernel-writing,windows-platform}.md`, `manifest.json`, `checksums.sha256` |

**Verified:** `python -m pytest -q tests/test_smoke.py` → 2 passed

---

## Active Leases (historical, 2026-11-01)

| Task | Profile | Fence | PID | Title |
|------|---------|-------|-----|-------|
| T-0118 | pi-orca-glm-5-3-flash | 99 | 15768 | Coverage tool + `coverage/rules_coverage.json` |
| T-0119 | pi-orca-hy4-preview | 100 | 18372 | Decision-point model (Decision, Action, legal_actions, apply) |
| T-0130 | pi-orca-glm-5-3-flash | 101 | 17288 | Generate `docs/rules/index.json` from integrated rules |

**Expected duration:** ~30–80 min each (free models)

---

## Queue Items Resolved

| Item | Decision |
|------|----------|
| Q-062 | Option 1: Integrated base, voided 18+ duplicate/probe/doomed tasks |
| Q-063 | Closed via Q-066 as moot (work already in main) |
| Q-064 | Option 1: Voided corrupt base cards, keep clean chain |
| Q-065 | Fix cause and resume |
| Q-066 | Close Q-063 as moot — keep T-0127/T-0129 DONE |

**Open queue items:** 0

---

## Task Count Summary (2026-11-01)

```
VOID: 125
DONE: 2 (T-0127, T-0129)
LEASED: 3 (T-0118, T-0119, T-0130)
READY: 0
PROPOSED: 0
TOTAL: 130
```

---

## Next Steps for New Session

1. **Monitor leases:** `pmk status` — wait for T-0118/T-0119/T-0130 to complete
2. **Run conductor tick:** When tasks submit, Conductor will verify/integrate
3. **Overseer will wake on:** `review` (submissions), `replan` (no READY tasks), or `incident`
4. **If stalled >120 min:** Consider adding paid models or checking for lease expiry

---

## Key Commands

```powershell
# Status
pmk status

# Full briefing
pmk brief --role overseer

# Run conductor tick (checks merge queue, advances state, wakes overseer)
cd C:\temp\projects\testproject1; .venv\Scripts\activate; python -c "
import sys
sys.path.insert(0, r'C:\temp\projects\testproject1\src')
from pmk.api import Kernel
from fleet.dispatcher import Dispatcher
from fleet.overseer import OverseerRunner
from fleet.conductor import Conductor
from fleet.state import FleetState
k = Kernel(root=r'C:\temp\projects\testproject1'); k.init()
fleet_state = FleetState.load()
d = Dispatcher(k, fleet_state); o = OverseerRunner(k, fleet_state)
c = Conductor(k, d, o); print(c.tick())
"

# Check lease elapsed time
python -c "
import sys, time
from datetime import datetime
sys.path.insert(0, r'C:\temp\projects\testproject1\src')
from pmk.api import Kernel
k = Kernel(root=r'C:\temp\projects\testproject1'); k.init()
state = k.state()
for task_id, lease in state.leases.items():
    if lease.granted_at:
        granted = datetime.fromisoformat(lease.granted_at.replace('Z', '+00:00')).timestamp()
        print(f'{task_id}: {lease.holder}, fence={lease.fence}, pid={lease.pid}, elapsed={(time.time()-granted)/60:.1f} min')
"
```

---

## Important Files

| File | Purpose |
|------|---------|
| `docs/sources/proposal-cfna-game-v1.md` | Game specification (authority) |
| `docs/sources/proposal-cfna-claude-v1.md` | Setup instructions (authority) |
| `docs/PDD.md` | Project Design Document |
| `src/fleet/conductor.py` | Conductor (stall detection, merge queue) |
| `src/fleet/merge.py` | Merge queue with `--ff-only` fallback |
| `src/fleet/dispatcher.py` | Dispatcher (profile selection, lease mgmt) |
| `src/fleet/overseer.py` | Overseer runner (wakes, prompts) |
| `.pm/policy.toml` | Policy (lease TTL=120, gate cmd) |
| `agents.toml` | Fleet profiles & priorities |
| `.pm/pins.sha256` | Constitution & policy pins |

---

## Known Issues

- **Free models extremely slow:** pi-orca-deepseek rate-limited (429); cline models ~70+ min/task with 0 completions yet
- **No paid models configured:** Only free tier profiles available
- **Conductor stall detection:** Active (checks lease TTL expiry, auto-revokes, emits LEASE_EXPIRED)

---

## Provenance

- **author_llm:** nvidia/nemotron-3-ultra-550b-a55b
- **Session:** OpenCode at C:\temp\projects\testproject1
- **Date:** 2026-11-01
---

## Final Re-scope / Corpus Update (2026-11-02)

- Q-068 decided: adopted the full 66-file rule corpus (pinned 75a037f) into docs/rules/.
- Regenerated docs/rules/index.json and coverage/rules_coverage.json; full test gate passes.
- PDD goals re-scoped to G-001 and G-002 (former G-003); G-002/G-004/G-005/G-006 are accepted as incomplete/manual-check goals.
- Q-070 remains recorded as accepting the project as incomplete.
- Provenance: author_llm = beam:cloud (OpenCode session); no independent assessor LLM recorded.

---

## Latest evidence (2026-11-11)

Measured at `HEAD afcc0ba`; 0 behind / 135 ahead of `origin/main`. Full detail: `docs/reports/fleet-launcher-repair-verification-2026-11-11-v1.md` and its dated **Addendum** (**§A.11** the commit and the clean-base gate; **§A.12** the `T-0192` discharge).

| Item | Evidence |
|---|---|
| Project state | `PAUSED`; **155 VOID**, **43 DONE**, **11 READY**, **1 VERIFYING**, **1 LEASED**; **0 active leases**; 0 open queue items; 104 incidents; **21 pmk worktrees** (8 non-lease, including 3 dirty foreign gate trees); `stopped: false` |
| Chain | `I1 chain verifies (3640 events)`; `pmk sentinel` `ok: true`, no findings |
| **H1 — lease admission** | **LANDED and proven.** `src/pmk/api.py` `claim()` refuses a worktree-bearing grant that resolves to the repo root (`invalid_worktree`) or carries no `pid`/`expires_at` outside `RUNNING` (`lease_incomplete`), recording `LEASE_REFUSED` first. New `tests/pmk/test_lease_admission.py`; T-0192 oracle `pytest -q tests/pmk/test_lease_admission.py tests/pmk/test_tasks.py` = **35 passed**. Production dispatch is unaffected — `harness.py:441` claims without a worktree |
| **Gate fragilities** | **Both fixed.** `test_identity_guard.py` resolves `sh` from Git instead of `PATH` (4 passed with `Git\usr\bin` removed). `plat.kill_tree` no longer reports failure when the target is already gone; added `_liveness()` polling. Under 4-hog load: **2/12 failures before → 12/12 pass after** |
| Gate | Working tree: `python -m pytest -q` **exit 0** — **1293 passed, 1 skipped** (includes the §A.14 worktree fix); `tests/pmk + tests/fleet` **517 passed / 1 skipped**. **Clean base at `b2fe947`: `clean-base gate exit=0`**, imports resolving inside the gate worktree, **1220 tests marked — 1219 pass / 1 skip / 0 fail**. The 72-test gap vs the working tree is uncommitted test material only: 47 tests in untracked CNA test files + 25 tests added by uncommitted CNA edits. ⚠️ The gate log carries no count line — `addopts = -q` is set in **both** `pytest.ini` and `pyproject.toml` and the script adds another `-q`, so pytest runs at `-qq` (report §A.11, fragility 4) |
| Still open | **H3** (`Dispatcher.reconcile` has no production caller), **H4** (`served_models: []` still possible), **H7** (no `%TEMP%/pmk-merge-*` awareness), the human-authority gate, and CP-4. Hardening: **3 of 7 landed** (H1, H2, H6), H5 partial, H3/H4/H7 absent. CP-3's blocker is **fixed** (§A.14) |
| **T-0192 — discharged** | **`VOID`** as of 2026-11-11 (report §A.12). Decision A closed with two human-attributed events: `SUPERSEDED_BY` seq 3635 (`commit b2fe947`) then `TASK_VOIDED` seq 3636. READY queue 12 → **11**; sentinel `ok: true`, no findings. Note `supersede` alone would **not** have retired the card — no reducer reads `SUPERSEDED_BY`; only `void` does |
| **Commit `b2fe947`** | 24 files, +2185/−27; tree `77c4156…` byte-identical to the gated index tree; author and committer `umaws-pilot <umaws-pilot@localhost>`; **0** entries from `src/cna/**`, `agents.toml`, `.pm/**` or `tmp/**`. **Three provenances in one commit:** the single-owner wave (`owner.py`, `canary.py`, console/harness, cli, tests) = **Unknown session(s)** (opencode-family implicated, unproven); H1 + fragility fixes = **DeepSeek V4.1 Flash Free / opencode**; the records (this file, plan DoD rows, D-73 erratum, verification report) = same. There is no single "group A" — the wave rode along because H1's test helpers are entangled with it. Still uncommitted: the CNA body (A-12), `agents.toml` (operator), `.pm/**`, `tmp/**` |
| **CP-2 — closed** | The two invalid leases were revoked 2026-11-11: `REVOKED` seq 3638 (`T-0210`, fence 162) and seq 3639 (`T-0211`, fence 163), actor `human:operator`. **`active_leases: 0`** — `DoD-5` now satisfies **both** halves |
| **CP-3 — defect fixed** | Prune removed **14** trees, archiving each first, and correctly left the 3 foreign gate trees. **13 more were refused with a false "an active lease still owns this worktree"**: `_deletion_refusal` read the raw `state.leases` (38 retained entries, all `DONE` cards) instead of `active_leases()`. Fixed in `src/pmk/worktrees.py` (report §A.14); all 13 now return no refusal and the dry run shows no active-lease skips. Re-run `pmk worktree prune --yes --archive` to reclaim them |
| Decisions | **D-70, D-71, D-72, D-73 and D-74 are all still drafts** awaiting CP-4. `T-0189` is **VOID** (1/1 attempts); successor `T-0190` (`DONE`, merge `0edc0dc`) — superseded, not exonerated |

**Next actions.** (1) **CP-3 finish:** `pmk worktree prune` (read it) then `pmk worktree prune --yes --archive` to reclaim the 13 trees the defect blocked. (2) **Decision B was answered `A`** — the Console refuses class-K decisions and points at the terminal, no per-start token; the authority gate (reviewer items 2–4) is now unblocked. (3) **DoD-6 canary:** `pmk project resume --reason "…"` then `pmk canary run --seconds 900 --resume`, on `T-0193` (H3) in preference to a finished card. (4) **CP-4:** ratify D-72 + its erratum. Resume (A10), dispatch resumption and the first push remain operator-only.

## Latest evidence (2026-11-10) — superseded by the measurement above

Measured at `HEAD 53871a7`. Two tasks are active (T-0210 VERIFYING at fence 162, T-0211 LEASED at fence 163); no new dispatch was started in this check.

| Item | Evidence |
|---|---|
| Project state | `PAUSED`; 212 cards: **155 VOID**, **43 DONE**, **12 READY**, **1 VERIFYING**, **1 LEASED**; 2 active leases; 0 open queue items; 104 incidents; 35 worktrees; `stopped: false` |
| Chain | `I1 chain verifies (3630 events)` |
| T-0146 | **VOID**, fence 125, block reason `superseded by T-0159 coverage regeneration`; `TASK_VOIDED` seq 3315 at `2026-11-08T12:40:44Z`, actor `operator` / `human` |
| Ready queue | 12 cards: T-0192–T-0195, T-0199, T-0200, T-0202–T-0207; T-0201 is VOID |
| Sentinel | `pmk sentinel` returns `ok: true` with no findings (I1, I3, I4, I5, I6, I7, I8', I13, I14, I15, I16, I17). The red baseline in D-68 is historical, not current |
| Identity guard | **A8 applied 2026-11-09:** `git config core.hooksPath` returns `.githooks` (D-69) |
| Canary | **PATH PASS — T-0190, T-0191 and T-0196 reached `DONE` through dispatch; only T-0191 and T-0196 prove DoD-6.** T-0190 (fence 157, base `e302119`): `SUBMITTED` seq 3516 → `ORACLE_RESULT` seq 3518 (`pytest -q`, `ok: true`, no `exit` key) → `INTEGRATED` seq 3520 at `0edc0dc`, bundle `EB-T-0190-157` — **no `gate_output`**. T-0191 (fence 158, base `ce22591`): `SUBMITTED` seq 3534 → `INTEGRATED` seq 3537 at `c7fcdf3`, bundle `EB-T-0191-158`, `gate_output` present (`pytest -q`, exit 0). T-0196 (fence 159, base `9bb0139`): `SUBMITTED` seq 3554 → `INTEGRATED` seq 3558 at `951d1ee`, bundle `EB-T-0196-159`, `gate_output` present (`pytest -q`, exit 0). All three ran under `kilo-auto`/`kilo`; all three merges are authored `umaws-pilot <umaws-pilot@localhost>`. T-0189 (fence 156, base `bcf145c`, D-69) remains a real gate failure — superseded by T-0190, not exonerated. `pmk status` still reports **PAUSED**; no A10 resume is recorded |
| Canary gate history | The T-0189 gate failed at `tests/test_rules_baseline.py::test_coverage_reports_case_statuses_and_evidence`: case `8.0` referenced `tests/test_transport.py`, absent from base `bcf145c`. `tests/test_transport.py` is tracked at current HEAD (added by `9b3b70d`), and the self-contained base `53871a7` passes the full clean-worktree `pytest -q` (exit 0; `tmp/clean-head-full2.log`). T-0191 and T-0196 also passed their `pytest -q` gates and persisted `gate_output`; T-0190 recorded `ok: true` without an `exit` value and has no `gate_output` |
| Report copies | `docs/reports/dispatch-failure-root-cause-and-remediation-v1.md` and `pilot/dispatch-failure-root-cause-and-remediation-v1.md` are byte-identical after correction: seq 3212 is **23:10:45**; seq 3225 is **2026-11-08 08:21** and its actor is recorded as **unknown** |

**Isolated base canary (2026-11-10).** Because the live kernel had 12 READY cards and 2 active leases, `pmk canary run` could not satisfy its one-READY/zero-lease preflight there. A separate worktree on branch `canary-base-53871a7` at `53871a7` was used instead; the run did not write to the live kernel. Isolated-base card T-0147 (fence 120, one attempt, `kilo-auto`/`kilo`) wrote `docs/reports/canary-53871a7.md`; `SUBMITTED` seq 3132, gate `ORACLE_RESULT` seq 3133 exit 0, `INTEGRATED` seq 3135 at `05b54d2`, and `CANARY_FINISHED` seq 3136 `ok: true` with state `DONE`. Bundle `EB-T-0147-120` has non-empty gate output, and the merge is authored `umaws-pilot`. This is an isolated base result, not the live-kernel canary, and it does not authorize A10. Details: `docs/reports/canary-53871a7-supervised-2026-11-10.md`.

**Report reconciliation (2026-11-09).** The dispatch-report copies now record T-0146 as `VOID` in F-04 and OQ-04 (`TASK_VOIDED` seq 3315, `2026-11-08T12:40:44Z`; reason `superseded by T-0159 coverage regeneration`). The historical `READY` state is retained as writing-point narrative; T-0146 must not be reused. Their OQ-08 sentinel-red baseline is historical; the current sentinel is green.

**Current state and next action.** A8 is applied (`core.hooksPath=.githooks`); T-0190, T-0191 and T-0196 passed the dispatch path and integrated at `0edc0dc`, `c7fcdf3` and `951d1ee`; DoD-6's non-empty `gate_output` is proven by T-0191 and T-0196 only. T-0189's gate failure is superseded, not exonerated. At HEAD `53871a7`, `pmk status` reports `PAUSED`: 212 cards (155 VOID, 43 DONE, 12 READY, 1 VERIFYING, 1 LEASED), 2 active leases, and a verified chain of 3630 events. T-0208, T-0209 and T-0212 are DONE and integrated; T-0210 is VERIFYING at fence 162 (re-verified at seq 3629); T-0211 is LEASED at fence 163; 12 cards are READY. Next: integrate T-0210, complete T-0211, and drain the READY queue; resuming dispatch remains the operator's A10 decision.
