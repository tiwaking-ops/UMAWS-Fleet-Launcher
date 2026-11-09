# HANDOFF — UMAWS Fleet CFNA Project (2026-11-01)

## Project State: PAUSED

**Root:** `C:\temp\projects\testproject1` (UMAWS repo root)  
**Last update:** 2026-11-09
**I1 chain:** Verifies (3436 events)
**Kernel:** pmk v0.1.0

> **Current evidence:** the 2026-11-01/02 sections below are historical. See **Latest evidence (2026-11-09)** at the end for the current state, the canary status and the A8 blocker.

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

## Active Leases (3 running)

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

## Task Count Summary

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

## Latest evidence (2026-11-09)

Measured at `HEAD 7910de5531f2be30948feefb9656106ae8ec5f9e`. No task was leased and no dispatch was started in this check.

| Item | Evidence |
|---|---|
| Project state | `PAUSED`; 185 cards: **143 VOID**, **32 DONE**, **10 PROPOSED**; 0 active leases; 0 open queue items; 103 incidents; 22 worktrees; `stopped: false` |
| Chain | `I1 chain verifies (3436 events)` |
| T-0146 | **VOID**, fence 125, block reason `superseded by T-0159 coverage regeneration`; `TASK_VOIDED` seq 3315 at `2026-11-08T12:40:44Z`, actor `operator` / `human` |
| Ready queue | `pmk task list --state READY` returns no cards |
| Sentinel | `pmk sentinel` returns `ok: true` with no findings (I1, I3, I4, I5, I6, I7, I8', I13, I14, I15, I16, I17). The red baseline in D-68 is historical, not current |
| Identity guard | `git config --get core.hooksPath` returns nothing (exit 1): **A8 is outstanding**; run `git config core.hooksPath .githooks` before any canary |
| Canary | No live dispatch has been run. Replacement packet: `pilot/drafts/d-69-canary-operator-packet-v1.md`; D-69 remains **PENDING** |
| Canary preflight | On the current base the oracle exits **1** because `docs/reports/dispatch-repair-verification-v1.md` is absent (required by R-11); `git apply --check pilot/evidence/canary-replacement-v1.patch` exits **0** |
| Report copies | `docs/reports/dispatch-failure-root-cause-and-remediation-v1.md` and `pilot/dispatch-failure-root-cause-and-remediation-v1.md` are byte-identical after correction: seq 3212 is **23:10:45**; seq 3225 is **2026-11-08 08:21** and its actor is recorded as **unknown** |

**Report reconciliation (2026-11-09).** The dispatch-report copies now record T-0146 as `VOID` in F-04 and OQ-04 (`TASK_VOIDED` seq 3315, `2026-11-08T12:40:44Z`; reason `superseded by T-0159 coverage regeneration`). The historical `READY` state is retained as writing-point narrative; T-0146 must not be reused. Their OQ-08 sentinel-red baseline is historical; the current sentinel is green.

**Current blocker and next action.** A8 is not applied. Run `git config core.hooksPath .githooks`, then follow the packet to create and admit one replacement card and run one supervised dispatch. Do **not** run `pmk project resume` for the canary; the project stays `PAUSED` and the Console's Conductor still drains the merge queue. D-69 is filled only after a real run; a PASS is required before A10 resumption.
