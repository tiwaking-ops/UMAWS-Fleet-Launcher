"""Append sections 13-15 of the report."""
import os

OUT = r"C:\temp\projects\testproject1\pilot\assessment\report-opencode-umaws-completion-v1.md"

SECTIONS_13_15 = """
## 13. What Was Cut or Not Done

**Tier contents vs achieved:**

| Tier | Contents | Target | Achieved? | Verdict |
|---|---|---|---|---|
| A. Foundation | Environment, Caliber spikes (G1), Kernel-lite core, QuotaGate M0-M2, handover (G3) | End of Day 4 | **Yes** | VERIFIED |
| B. Integrated | Harness-lite, worktrees, merge queue, first tasks under Kernel, QuotaGate M3+M5, Caliber sync (G4) | End of Day 6 | **Partial** | M3/M5 NOT-BUILT; Caliber sync IS on (G4 crossed); T1/T2/T3/T4/T6 pass |
| C. Measured | QuotaGate M4 capacity report, all pilot invariants, T1-T6 green, pilot report | End of Day 7 | **Not achieved** | Tier C NOT reached; only Tier A with working Fleet |

**What was cut (per the cut order, proposal §3.3):**
- QuotaGate M3 (strategies, combos, pre-first-byte failover) — NOT-BUILT
- QuotaGate M5 (capability-token auth, events outbox, availability endpoint) — NOT-BUILT
- F1 (one-click run with real LLM) — NOT executed (Tier B, needs real LLM)
- Q1-Q5 (full acceptance test drills) — Q3 ramped but not drilled; Q1/Q2/Q4/Q5 not run
- C1 (formal capacity report vs 10–30 worker target) — G5 ran 6 real workers, F7 ran 100 fake; neither matches the target

**Tier actually achieved: A (Foundation), not B or C.**

**Evidence bundle ARTEFACT MISSING:** Only EB-T-0003-3 (the REWORK path) exists in the repo. Passed-path bundles from G5/F7 existed only in temp directories and were deleted. No passed-path evidence bundle survives in this repository. (See §12.)

**pi profile (G5) never live-unrun:** G5 used hermes (3 workers) + kilo (3 workers) = 6 slots. pi-orca-deepseek was never dispatched live. Its first real dispatch is still unexercised. (STATE.md p.161)

**5 cline-mimo models offered, none verified:** D-35 repointed the profile to the operator's 5 offered free models. None has been exercised — verifying needs live provider calls (its own authorisation). (STATE.md p.170)

---

## 14. Readiness for a Toy-Project Run (NOT Executed)

Per rule 3.3, this section is a pre-flight read — no live provider calls are made.

**Commands that exist (from `pmk --help` sweep, cli-help-sweep-ran-now.txt):**
- `pmk init` → create layout, first event, pins
- `pmk status` → one-screen status (tasks, leases, pins)
- `pmk brief --role overseer|worker` → deterministic briefing
- `pmk task create|admit|list|show` → task card management
- `pmk claim|renew|revoke|submit|verify|integrate` → lease lifecycle
- `pmk sentinel` → check all 16 invariants
- `pmk views` → regenerate views
- `pmk sweep` → expire leases past TTL
- `pmk queue add|list|decide` → human decision queue (class K)
- `pmk fleet status|profiles|enable|disable|cool|import-prompts` → profile management
- `pmk dispatch run --seconds N` → run dispatch loop
- `pmk agent list|show|tail|stop|swap|send` → agent inspection
- `pmk project init|status|close-check|pause|resume|run` → project lifecycle
- `pmk gateway ingest|config-hash` → QuotaGate integration
- `pmk context sync|revert|score|drift|install|lint` → Caliber context sync
- `pmk stop|resume` → stop-the-line (Phase 2: freezes promotions + leases)
- `pmk incident` → record an incident
- `pmk pins check|record` → pinned files

**Commands that do NOT exist (NOT-BUILT):**
- `pmk run-worker` (proposal §9.3) — missing
- `pmk import-bootstrap` (proposal §9.3) — missing
- `pmk queue show` (proposal §9.3) — missing, only `list` and `decide` exist
- `pmk token issue` (proposal §9.3) — missing

**Profiles currently enabled or cooling (from event log, event-counts-ran-now.txt):**
- Active at Console start: all 5 profiles (hermes-oneshot, kilo-auto, pi-orca-deepseek, cline-mimo, opencode-strongest, opencode-fallback)
- During console runs: pi-orca-deepseek was cooling (2 unknown failures → 900s cooldown, PROFILE_COOLING event)
- opencode-strongest was rate-limited (QUOTA class, from S-A1)

**Could dispatch happen today?** YES, if the Console is started and profiles are enabled. The Console auto-starts the dispatch loop on startup (src/console/app.py:65-74). The two defects (D-A1, D-A2) mean that a repo with READY tasks + enabled profiles will immediately begin dispatching without operator action, and the dispatcher will NOT honor `pilot/STOP`.

**Steps to run a toy project (proposed, NOT executed):**
1. `cd` to a fresh clone
2. `python -m pmk.cli init` (create layout)
3. Hold `agents.toml` aside or create `pilot/STOP` (to avoid auto-dispatch)
4. Configure profiles (at least one real CLI with available quota)
5. `pmk task create "Write hello world" --type implement --write "hello.txt" --read "." --oracle "test -f hello.txt"`
6. `pmk task admit T-0001`
7. `pmk dispatch run --seconds 60` (or start Console)
8. `pmk sentinel` (check invariants)
9. `pmk views` (regenerate views)
10. `pmk status` (check final state)

**Warnings:**
- Do NOT start the Console with enabled profiles and READY tasks without first setting `pilot/STOP` — the dispatcher will dispatch immediately (D-A2).
- The dispatcher will spam `FLEET_ASSIGNED` if a scope overlap blocks claims (D-A1).
- Quotas are likely exhausted (operator confirmed). All real CLI dispatches will fail with QUOTA/UNKNOWN.

---

## 15. Appendices

### Appendix A: Environment (Step 0 snapshot)

| Item | Value |
|---|---|
| Repository | C:\\temp\\projects\\testproject1 (live, read-only) |
| Clone for runs | C:\\Users\\Tiwa Pene\\AppData\\Local\\Temp\\opencode\\clone\\repo |
| Commit (live) | a93da888831b4177c65fa62751e92c9cf7466f24 |
| Commit (clone) | a93da888831b4177c65fa62751e92c9cf7466f24 (matches) |
| Git status (live) | Clean (a93da888 is HEAD, no uncommitted changes) |
| OS | Windows 10/11 (win32) |
| Python | 3.12.10 (3.14, 3.12, 3.11 present; 3.12.10 used for venv) |
| Git | 2.55.0.windows.3 |
| Node | v26.7.0 |
| npm | 12.0.2 |
| Caliber | 1.55.2 (pinned) |
| CLIs | hermes 0.22.2, kilo 7.8.15, pi 1.2.0, cline 3.0.73, opencode 2.1.0 |

### Appendix B: Commands run, verbatim

All commands were run in the clone at `C:\\Users\\Tiwa Pene\\AppData\\Local\\Temp\\opencode\\clone\\repo`.

| # | Command | Exit code | Timestamp | Output file |
|---|---|---|---|---|
| B1 | `python -m pytest -v` | 0 | 2026-10-24T15:0x | full-suite-ran-now.txt |
| B2 | `python -m pmk.cli sentinel` (clone) | 0 | 2026-10-24T14:3x | sentinel-after-console-ran-now.txt |
| B3 | `python -m pmk.cli --help` | 0 | 2026-10-24T15:12:16 | cli-help-sweep-ran-now.txt |
| B4 | `python -m pmk.cli task --help` | 0 | 2026-10-24T15:12:17 | cli-help-sweep-ran-now.txt |
| B5 | `python -m pmk.cli task create --help` | 0 | 2026-10-24T15:12:18 | cli-help-sweep-ran-now.txt |
| B6 | `python -m pmk.cli fleet --help` | 0 | 2026-10-24T15:12:19 | cli-help-sweep-ran-now.txt |
| B7 | `python -m pmk.cli fleet profiles --help` | 0 | 2026-10-24T15:12:20 | cli-help-sweep-ran-now.txt |
| B8 | Console start + 9 GET endpoints + SSE | 0 (200) | 2026-10-24T14:47 | console-smoke-ran-now.txt |
| B9 | Console stop (clean teardown) | 0 | 2026-10-24T14:49 | console-side-effects-ran-now.txt |
| B10 | `pmk sentinel` (post-console) | 0 | 2026-10-24T01:54:37Z | sentinel-after-console-ran-now.txt |
| B11 | `python emit_event_extracts.py .pm\\events` | 0 | 2026-10-24T15:1x | event-log-head-tail-ran-now.txt |
| B12 | `python event_counts.py` | 0 | 2026-10-24T14:4x | event-counts-ran-now.txt |
| B13 | `python check_views.py <clone>` | 0 | 2026-10-24T15:0x | views-check-ran-now.txt |
| B14 | `python -m pytest tests/fleet/test_fleet.py -v` | 0 | 2026-10-24T13:5x | tests-fleet-ran-now.txt |
| B15 | `git log --oneline -100` (live repo) | 0 | 2026-10-24T13:5x | git-log-oneline.txt (read/) |

**Console endpoints verified (console-smoke-ran-now.txt):**
- GET `/` → 200 (HTML, tabs: Projects, Fleet, Tasks, Queue, Overseer, Manual launcher, Metrics)
- GET `/api/project/status` → 200
- GET `/api/fleet` → 200
- GET `/api/tasks` → 200
- GET `/api/queue` → 200
- GET `/api/overseer` → 200
- GET `/api/metrics` → 200
- GET `/api/launcher` → 200
- GET `/api/agent/list` → 200
- GET `/api/events` → 200 (SSE stream)

### Appendix C: Manifest reference

See `pilot/assessment/bundle/MANIFEST.md` for the full file manifest with SHA-256 hashes, sizes, and evidence labels.

### Appendix D: Verdict count computation

| Verdict | Count | Examples |
|---|---|---|
| VERIFIED-NOW | 31 | Sentinel clean, 234 tests pass, I13 views match, pmk --help sweep, scope overlap test, Console SSE |
| VERIFIED-EARLIER | 28 | F7 scale drill, G5 capacity, T4/T4b canary, S-A1 CLI matrix, S-P1 platform, recovery ladder, Caliber spikes |
| UNVERIFIED | 21 | Model census (400+), Q1-Q4, Q5, T5, F1, F8, F9, F11, F14, H5, H9, H10, H12, V-03, V-05, V-07, pi live-unrun |
| FAILED | 1 | M-018: `pilot/STOP` does not halt dispatch (dispatcher defect) |
| NOT-BUILT | 6 | `pmk run-worker`, `pmk import-bootstrap`, `pmk queue show`, `pmk token issue`, QuotaGate M3, QuotaGate M5 |
| DIVERGES | 3 | D-L1 (Linux→Windows), D-L9 (20→100 agents, operator edit), M-020 (policy TOML inline→section) |
| WRONG-DOC | 6 | M-001 (Tier C), M-003 (production-ready), M-007 (port 8080), M-008 (tabs), M-009 (port 8000), M-010 (WSL2) |
| **Total** | **96** | |

---

*End of report. Author: OpenCode (Laguna S 2.1). Date: 2026-10-24. Commit: a93da888.*
"""

with open(OUT, "a", encoding="utf-8") as f:
    f.write(SECTIONS_13_15)
print(f"Appended sections 13-15 ({len(SECTIONS_13_15)} chars)")
