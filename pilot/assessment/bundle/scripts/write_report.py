"""Write the UMAWS completion report in chunks to stay within token limits."""
import os

OUT = r"C:\temp\projects\testproject1\pilot\assessment\report-opencode-umaws-completion-v1.md"

FRONT = """---
document: "UMAWS Completion Report and Assessment Bundle"
version: "1.0.0"
author: "OpenCode (Laguna S 2.1)"
date: "2026-10-24"
commit_hash: "a93da888831b4177c65fa62751e92c9cf7466f24"
dirty: "clean (clone)"
scope: "UMAWS Fleet / QuotaGate pilot P-01"
prompt_version: "1.0.0"
---

# UMAWS Completion Report — OpenCode Assessment

**Assessor:** OpenCode (Laguna S 2.1). The assessing agent is also the system's builder/author. This self-assessment is disclosed; independence is limited to what the evidence permits.

**Yardstick (verbatim, in order):** (1) Pilot v1 (`docs/sources/pilot-proposal.md`): H1–H7, gates G0–G6, T1–T6, Q1–Q5, H6, C1; (2) User Manual (`UMAWS_USER_MANUAL.md`); (3) Fleet Launcher amendment (`docs/sources/fleet-launcher-proposal.md`): FR1–FR15, D-L1–D-L14, F1–F14, H8–H12; (4) Gates amendment (`pilot/amendment-gates.md`).

---

## 1. Executive Summary

**Lead with what failed, diverged, was not built or is unverified.**

**Tier claim diverges:** The manual (`UMAWS_USER_MANUAL.md`) ends with "Tier C achieved, Sentinel clean" and "production-ready for supervised use." The actual tier reached is **A (Foundation) with a working Fleet** (pilot-report.md §1: "Tier reached: A"). Tier B (harness-lite, first tasks under the Kernel) and Tier C (one-click run, capacity report, all acceptance tests green) are **not** achieved. The manual's Tier C / production-ready claim is **WRONG-DOC**.

**Two defects found live in the clone** (reported, not fixed):
1. **FLEET_ASSIGNED spam / no backoff:** `Dispatcher.tick()` → `harness.start` → `kernel.claim` raises on the T-0002 vs T-0001 `hello.txt` write-scope overlap (D-L6 holds) but `FLEET_ASSIGNED` is recorded before the claim and has no backoff → **319 events / ~2.6 MB/h** per stuck task. (console-side-effects-ran-now.txt)
2. **Dispatcher does not honor `pilot/STOP`:** Only the conductor checks the stop file. The Console auto-starts both dispatch and conductor loops on startup. Starting the Console on a repo with READY tasks + enabled profiles dispatches immediately without operator action. (console-side-effects-ran-now.txt, console-smoke-ran-now.txt)

**Sentinel is clean** (post-console RUN-NOW): `ok=true`, all 16 invariants pass (I1, I3, I4, I5, I6, I7, I8', I13, I14, I15, I16). Event log hash chain verifies end-to-end (584 events, 0 repairs). Views equal projection (I13). (views-check-ran-now.txt)

**234 tests pass** in 71.77s. (full-suite-ran-now.txt)

**Verdict counts:**

| Verdict | Count |
|---|---|
| VERIFIED-NOW | 31 |
| VERIFIED-EARLIER | 28 |
| UNVERIFIED | 21 |
| FAILED | 1 |
| NOT-BUILT | 6 |
| DIVERGES | 3 |
| WRONG-DOC | 6 |

**Key divergences from the manual's claims:**

| Manual claim | Reality | Verdict |
|---|---|---|
| Tier C achieved | Tier A reached | WRONG-DOC |
| "production-ready for supervised use" | Tier A, 2 live defects, dispatcher auto-dispatches on Console start | WRONG-DOC |
| Sentinel clean | Sentinel is clean | VERIFIED-NOW |
| 100-agent test complete | F7 scale drill ran with **fake** workers (100/100 DONE in 104.8s); real capacity was G5 (6 real workers) | VERIFIED-EARLIER (with caveat) |
| Quota-limit tests complete | Q3 ramp tests done (solar-mini4, step-3.7); full Q3 drill (structured 429, clock advance) not done; Q4 not done | UNVERIFIED |
| All 400+ models tested and work | NO supporting artefact exists. S-A1 used 13 requests across 5 CLIs. | UNVERIFIED |
| Console on port 8080 | `DEFAULT_PORT = 8765` in `src/console/app.py` | WRIGHT-DOC |
| Console tabs: Overview, Tasks, Leases, Profiles, Events, Gateway, Sentinel | Actual: Projects, Fleet, Tasks, Queue, Overseer, Manual launcher, Metrics | WRONG-DOC |

---
"""

with open(OUT, "w", encoding="utf-8") as f:
    f.write(FRONT)
print(f"Wrote front matter + §1 ({len(FRONT)} chars)")
