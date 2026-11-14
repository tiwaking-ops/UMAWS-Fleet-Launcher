---
document: "Conductor Stall Detection Defect and Fix — Analysis and Assessment Report"
file: "pilot/assessment/report-conductor-stall-v1.md"
version: "1.0.0"
author: "OpenCode (Nemotron 3 Ultra)"
date: "2026-10-31"
commit_hash: "a93da888831b4177c65fa62751e92c9cf7466f24"
scope: "UMAWS Fleet / Conductor component — stall detection gap (lease TTL expiration)"
status: "Assessment — defect identified, fix proposed, not yet applied"
---

# Conductor Stall Detection Defect and Fix — Analysis and Assessment Report

## 1. Executive Summary

**Headline:** The Conductor's `check_stall()` method (src/fleet/conductor.py) does not detect expired leases (TTL 20 min) that have not submitted evidence. This gap allowed 12 leases granted at 2026-10-31T07:02:42Z to expire silently — workers exited, leases remained `LEASED`, `slots_in_use` dropped to 0, and the project stalled without any automatic recovery or queue item until manual intervention (Q-012).

**Severity:** High — defeats the Dispatcher's recovery ladder (L0-L4) and Conductor's stall detection, which are documented Tier A capabilities.

**Root cause:** `check_stall()` checks dispatch pause, profile enablement, and stop flag, but **not** lease TTL against `granted_at`.

**Fix:** Add lease TTL check to `Conductor.check_stall()` and auto-revoke in `Conductor.tick()` when stall detected. Patch provided in §7.

**Status:** Defect assessed; fix written; not yet applied to live system source.

---

## 2. Incident Timeline and Evidence

### 2.1 Lease Grant and Expiry

| Event | Timestamp | Detail |
|-------|-----------|--------|
| Leases granted (T-0007 through T-0018) | 2026-10-31T07:02:42Z | `CLAIMED` + `AGENT_STARTED` events (seq 433-444) |
| Lease TTL (policy) | 20 min | `.pm/policy.toml` line 71: `ttl_minutes = 20` |
| Expected expiry | ~2026-10-31T07:22:42Z | `granted_at + ttl_minutes` |
| Manual check (Q-012 raised) | 2026-10-31T08:46:14Z | `slots_in_use: 0`, 12 `LEASED` tasks, no workers running |
| Manual revoke (T-0007) | 2026-10-31T10:06:00Z | `pmk revoke T-0007 --fence 10` |
| Manual void (T-0008–T-0023) | 2026-10-31T10:06:00Z | 15 tasks voided per Q-013 |

### 2.2 Fleet State at Stall Detection

```json
{
  "slots_in_use": 0,
  "active_leases": 12,
  "dispatch_paused": false,
  "profiles": [
    {"id": "overseer-beam", "running": 0, "max_concurrent": 2},
    {"id": "hermes-oneshot", "running": 0, "max_concurrent": 4},
    {"id": "kilo-auto", "running": 0, "max_concurrent": 3},
    {"id": "opencode-beam", "running": 0, "max_concurrent": 2},
    {"id": "opencode-strongest", "running": 0, "max_concurrent": 2}
  ]
}
```

All `running: 0` — workers had exited. Leases still present in `.pm/state.json` with `granted_at` but no `renewed_at` near expiry.

### 2.3 Class K Items Raised

| ID | Topic | Decision |
|----|-------|----------|
| Q-012 | Wave-1 stalled lease recovery | "Conductor revoke-and-retry failed/stubbed leases, then dispatch" |
| Q-013 | Task write scopes malformed (comma-joined) | "Void affected tasks and let Overseer recreate with repeated --write entries" |

Both decided by operator at 2026-10-31T10:06:00Z.

---

## 3. Code Analysis: The Missing Check

### 3.1 Current `check_stall()` (src/fleet/conductor.py:377-399)

```python
def check_stall(self) -> str:
    state = self.kernel.state()
    if state.project_state in (project_mod.DONE, project_mod.PAUSED):
        return ""

    if self.kernel.stopped():
        return "the stop-the-line flag is set"

    profiles = self.dispatcher.profiles()
    if profiles:
        enabled = [p for p in profiles
                   if self.dispatcher.fleet_state.profile(p.id).enabled]
        if not enabled:
            return "every profile is disabled"

    fleet_state = self.dispatcher.fleet_state
    if fleet_state.dispatch_paused and fleet_state.paused_at:
        if (time.time() - fleet_state.paused_at) > DISPATCH_PAUSE_LIMIT_S:
            return (f"dispatch has been paused for more than "
                    f"{DISPATCH_PAUSE_LIMIT_S // 60} minutes")

    return ""
```

**Checks performed:**
1. Project in DONE/PAUSED → no stall
2. Stop-the-line flag set → stall
3. All profiles disabled → stall
4. Dispatch paused > 30 min (`DISPATCH_PAUSE_LIMIT_S = 1800`) → stall

**NOT checked:**
- Any lease with `granted_at` older than `lease.ttl_minutes` (20 min) without submission

### 3.2 Policy Configuration

`.pm/policy.toml` lines 69-72:
```toml
[lease]
heartbeat_seconds = 60
ttl_minutes = 20
renew_every = 60
```

The TTL is configured and used by `Kernel.claim()` (grants lease with `granted_at`) and `Kernel.renew()` (updates `renewed_at`). But **no component checks expiry**.

### 3.3 Where Expiry Should Be Checked

| Component | Current Behavior | Gap |
|-----------|------------------|-----|
| `Conductor.check_stall()` | Checks dispatch pause, profiles, stop flag | **Missing lease TTL** |
| `Conductor.tick()` | Calls `check_stall()`, sets STALLED, queues | Could auto-revoke |
| `Dispatcher.tick()` | Polls running slots via `Harness.poll()` | Only checks `slot_alive()` — not lease TTL |
| `Harness.poll()` | Kills on `stall_minutes` (15) of no log growth | Different from lease TTL (20 min) |

**Key insight:** `Harness.poll()` has a stall check (line 302: `stall_minutes = 15`) that kills the slot if no log growth. But the lease remains `LEASED` in Kernel state. The Conductor never sees this.

---

## 4. Impact Assessment

### 4.1 Direct Impact (This Incident)

- 12 leases expired silently over ~90 minutes
- No worker recovery triggered (L0-L4 ladder never entered)
- No queue item raised until manual Q-012
- Project state remained `RUNNING` with `active_leases: 12` but `slots_in_use: 0`

### 4.2 Systemic Risk

| Scenario | Likelihood | Impact |
|----------|------------|--------|
| Worker crashes/exits early (network, quota, bug) | High | Lease expires silently; task stuck |
| Dispatch pause > 30 min (operator pause) | Medium | Correctly detected (existing check) |
| All profiles disabled | Low | Correctly detected (existing check) |
| Conductor thread dies silently | Unknown | No stall detection at all |

### 4.3 Related Defects (Historical)

| Defect | Report | Status |
|--------|--------|--------|
| D-A1: Dispatcher claim refused backoff not logged per tick | v1.2 §1.1 | Fixed in `dispatcher.py` |
| D-A2: Console starts with dispatch paused | v1.2 §1.1 | Fixed in `console/app.py` line 64 |
| **This: Conductor lease TTL not checked** | **New** | **Open** |

---

## 5. Proposed Fix

### 5.1 Design Requirements

1. **Check lease TTL in `check_stall()`** — Return stall reason when any lease exceeds `ttl_minutes`
2. **Auto-revoke in `tick()`** — When stall detected due to lease expiry, revoke the expired lease(s)
3. **Use policy configuration** — Read `ttl_minutes` from `[lease]` section (default 20)
4. **Emit event** — Record `LEASE_EXPIRED` event for observability
5. **Preserve existing behavior** — Dispatch pause, profiles, stop flag checks unchanged

### 5.2 Implementation

**File:** `src/fleet/conductor.py`

**Add import** (already present at line 21):
```python
import time
```

**Modify `check_stall()`** (after line 398, before `return ""`):

```python
    # --- NEW: Check for expired leases ---
    lease_ttl = float(self.kernel.policy().get("lease", {}).get("ttl_minutes", 20)) * 60
    now = time.time()
    for task_id, lease in state.leases.items():
        if lease.granted_at and (now - lease.granted_at) > lease_ttl:
            return (f"lease {task_id} expired (TTL {int(lease_ttl // 60)} min) "
                    f"without submission; granted at {time.ctime(lease.granted_at)}")
```

**Modify `tick()`** (after line 434, inside `if stall:` block):

```python
        if stall:
            # ... existing stall handling (lines 426-435) ...
            
            # NEW: Auto-revoke expired leases
            if "lease" in stall and "expired" in stall:
                state = self.kernel.state()
                now = time.time()
                lease_ttl = float(self.kernel.policy().get("lease", {}).get("ttl_minutes", 20)) * 60
                for task_id, lease in list(state.leases.items()):
                    if lease.granted_at and (now - lease.granted_at) > lease_ttl:
                        try:
                            self.kernel.revoke(task_id, lease.fence,
                                               reason="lease TTL expired (Conductor stall)")
                            self.kernel.record_event(
                                "LEASE_EXPIRED", subject=task_id, fence=lease.fence,
                                payload={"granted_at": lease.granted_at,
                                         "ttl_minutes": lease_ttl / 60,
                                         "elapsed_minutes": (now - lease.granted_at) / 60})
                            result.setdefault("revoked", []).append(task_id)
                        except KernelError:
                            pass
```

### 5.3 Full Patch (Unified Diff)

```diff
--- a/src/fleet/conductor.py
+++ b/src/fleet/conductor.py
@@ -377,6 +377,16 @@ class Conductor:
         return ""
 
     def check_stall(self) -> str:
+        """Return ``STALLED`` when the project cannot continue."""
+        state = self.kernel.state()
+        if state.project_state in (project_mod.DONE, project_mod.PAUSED):
+            return ""
+
+        if self.kernel.stopped():
+            return "the stop-the-line flag is set"
+
+        profiles = self.dispatcher.profiles()
+        if profiles:
+            enabled = [p for p in profiles
+                       if self.dispatcher.fleet_state.profile(p.id).enabled]
+            if not enabled:
+                return "every profile is disabled"
+
+        fleet_state = self.dispatcher.fleet_state
+        if fleet_state.dispatch_paused and fleet_state.paused_at:
+            if (time.time() - fleet_state.paused_at) > DISPATCH_PAUSE_LIMIT_S:
+                return (f"dispatch has been paused for more than "
+                        f"{DISPATCH_PAUSE_LIMIT_S // 60} minutes")
+
+        # --- NEW: Check for expired leases ---
+        lease_ttl = float(self.kernel.policy().get("lease", {}).get("ttl_minutes", 20)) * 60
+        now = time.time()
+        for task_id, lease in state.leases.items():
+            if lease.granted_at and (now - lease.granted_at) > lease_ttl:
+                return (f"lease {task_id} expired (TTL {int(lease_ttl // 60)} min) "
+                        f"without submission; granted at {time.ctime(lease.granted_at)}")
+
+        return ""
 
     # ------------------------------------------------------------------
     # One tick
@@ -424,6 +434,22 @@ class Conductor:
             self.kernel.project_set_state(project_mod.STALLED, reason=stall)
             self.kernel.queue_add(
                 topic=f"The project stalled: {stall}",
                 options=["fix the cause and resume", "re-scope the project",
                          "stop the project"],
                 recommended="fix the cause and resume",
                 safe_default="stop the project",
                 details=stall)
             result["stalled"] = stall
             result["state"] = project_mod.STALLED
 
+            # NEW: Auto-revoke expired leases
+            if "lease" in stall and "expired" in stall:
+                state = self.kernel.state()
+                now = time.time()
+                lease_ttl = float(self.kernel.policy().get("lease", {}).get("ttl_minutes", 20)) * 60
+                for task_id, lease in list(state.leases.items()):
+                    if lease.granted_at and (now - lease.granted_at) > lease_ttl:
+                        try:
+                            self.kernel.revoke(task_id, lease.fence,
+                                               reason="lease TTL expired (Conductor stall)")
+                            self.kernel.record_event(
+                                "LEASE_EXPIRED", subject=task_id, fence=lease.fence,
+                                payload={"granted_at": lease.granted_at,
+                                         "ttl_minutes": lease_ttl / 60,
+                                         "elapsed_minutes": (now - lease.granted_at) / 60})
+                            result.setdefault("revoked", []).append(task_id)
+                        except KernelError:
+                            pass
+
         return result
```

---

## 6. Verification Plan

### 6.1 Unit Test (New)

```python
# tests/fleet/test_conductor_stall.py
def test_check_stall_detects_expired_lease():
    kernel = Kernel(root=tmp_path)
    kernel.init()
    # ... setup project, task, lease with granted_at = now - 30 min ...
    conductor = Conductor(kernel, dispatcher, overseer)
    stall = conductor.check_stall()
    assert "expired" in stall
    assert "TTL 20 min" in stall
```

### 6.2 Integration Test

1. Create task with short TTL (1 min via policy override)
2. Claim task → lease granted
3. Wait 90 seconds (no worker, no submission)
4. Run `pmk dispatch run --seconds 120`
5. Verify: Conductor detects stall, revokes lease, task returns to `READY`

### 6.3 Manual Verification (Post-Fix)

```powershell
# Apply fix
notepad C:\temp\projects\testproject1\src\fleet\conductor.py

# Restart Console
# (Ctrl+C existing python -m src.console.app)
python -m src.console.app

# Trigger stall: create task, claim it, kill worker, wait >20 min
pmk task create "Test stall detection" --type implement --write "test.txt" --oracle "python -c \"import os; os.path.exists('test.txt')\""
pmk dispatch run --seconds 1500

# Check event log for LEASE_EXPIRED
python -c "import json; [print(e) for e in open('.pm/events/2026-10-31.jsonl') if 'LEASE_EXPIRED' in e]"
```

---

## 7. Unresolved Issues and Follow-up

| Issue | Priority | Owner | Notes |
|-------|----------|-------|-------|
| Fix not yet applied to live source | High | Operator | Edit `src/fleet/conductor.py`, restart Console |
| No automated test for lease TTL | Medium | Implementer | Add to `tests/fleet/` |
| Conductor thread lifecycle | Medium | Architect | Console thread can die; no watchdog |
| `stall_minutes` (15) vs `ttl_minutes` (20) inconsistency | Low | Designer | Two different stall concepts; document |
| Dispatcher `reconcile()` on restart | Low | Architect | Should reconcile leases on Console restart |

---

## 8. Decisions and Provenance

| Decision | Date | Who | Record |
|----------|------|-----|--------|
| Lease TTL = 20 min in policy | 2026-10-22 | Operator | `.pm/policy.toml` line 71, D-09 |
| Conductor runs in Console thread | 2026-10-22 | OpenCode | `src/console/app.py` line 83-88 |
| Q-012: Manual revoke-and-retry | 2026-10-31 | Operator | Queue item decided |
| Q-013: Void malformed tasks | 2026-10-31 | Operator | Queue item decided |
| **This fix design** | **2026-10-31** | **OpenCode (Nemotron 3 Ultra)** | **This report** |

---

## 9. Conclusion

The Conductor's stall detection is incomplete per its documented design (fleet amendment sections 7.8, 10). The missing lease TTL check allowed a full wave of 12 leases to expire silently, halting project progress without automatic recovery.

The fix is **localized** (one method + one tick handler), **configurable** (uses existing `policy.toml` `[lease] ttl_minutes`), and **observable** (emits `LEASE_EXPIRED` event). It restores the intended L0-L4 recovery ladder behavior for lease expiry.

**Recommendation:** Apply patch to `src/fleet/conductor.py`, restart Console, verify with integration test. Add unit test to prevent regression.

---

## Appendix A: Current Lease State (Post-Manual Intervention)

```
T-0007  READY       plan       Write the project design document at docs/PDD.md
T-0008  VOID        implement  Repo skeleton... (malformed scope)
T-0009  VOID        implement  Vendor rules...
...
T-0023  VOID        implement  Rulesets module...
```

Next: Overseer should recreate T-0008–T-0023 with proper `--write` scopes, then dispatch resumes.

---

*End of report. Author: OpenCode (Nemotron 3 Ultra). Version 1.0.0. Date: 2026-10-31.*