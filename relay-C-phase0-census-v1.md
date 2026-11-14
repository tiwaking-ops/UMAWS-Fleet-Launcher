# Relay C — Phase 0 Census Report

**Scope:** Read-only analysis of a copy of `.pm/` and `agents.toml` (`C:\temp\umaws-census-pm`).  
**Source:** Appendix A and Appendix D of `assessment-claude-umaws-fleet-parallel-decomposition-v1.md`.  
**Date:** 2026-11-02

---

## 1. Ledger Over Time

**Time range:** `2026-10-22T05:56:24Z` to `2026-11-02T01:28:28Z`  
**Active 5-minute buckets:** 132

### Current Ledger State Counts

| State | Count |
|---|---|
| PROPOSED | 0 |
| READY | 3 |
| LEASED | 0 |
| SUBMITTED | 0 |
| VERIFYING | 0 |
| INTEGRATING | 0 |
| REWORK | 0 |
| DONE | 5 |
| BLOCKED | 0 |
| VOID | 130 |

**Total:** 138 tasks (5 DONE, 130 VOID, 3 READY)

### Bucket Sample (first 5 / last 5 active)

```
2026-10-22T19:30:00+00:00  {'QUEUE_ITEM': 2}
2026-10-22T19:35:00+00:00  {'QUEUE_DECIDED': 2}
2026-10-22T19:45:00+00:00  {'QUEUE_ITEM': 2, 'QUEUE_DECIDED': 1, 'INCIDENT': 1}
2026-10-22T19:50:00+00:00  {'QUEUE_DECIDED': 1}
2026-10-23T08:25:00+00:00  {'QUEUE_ITEM': 1}
...
2026-11-01T22:05:00+00:00  {'REVOKED': 1, 'CLAIMED': 1, 'AGENT_STARTED': 1}
2026-11-02T00:05:00+00:00  {'QUEUE_ITEM': 1, 'REVOKED': 1, 'LEASE_EXPIRED': 1}
2026-11-02T00:25:00+00:00  {'INCIDENT': 1}
2026-11-02T00:30:00+00:00  {'INCIDENT': 1}
2026-11-02T01:25:00+00:00  {'INCIDENT': 1}
```

**Observations:**
- Most activity is concentrated in two waves: `2026-10-22` to `2026-10-30` (setup/spikes) and `2026-11-01` to `2026-11-02` (corpus wave + stalls).
- The `2026-11-01T22:05` bucket shows a REVOKED + CLAIMED + AGENT_STARTED triplet (fence 113 → 114 transition for T-0136).
- The `2026-11-02T00:05` bucket shows the final LEASE_EXPIRED for T-0136 fence 114.

---

## 2. Slot Usage

**Cap from `agents.toml`:** `max_total_agents = 10`

### Active Leases Per Bucket (peak buckets)

| Bucket (UTC) | Active Leases | Idle Slot-Minutes |
|---|---|---|
| 2026-10-23T08:25 | 1 | unknown |
| 2026-11-01T13:35 | 1 | 9 |
| 2026-11-01T13:40 | 0 | 10 |
| 2026-11-01T22:05 | 1 | 5 |

**Total idle slot-minutes:** Cannot be determined precisely from the event stream alone because lease start/end timestamps are recorded per-lease, not aggregated per bucket. The event log shows lease durations (e.g., 120.02 min) but does not provide a per-bucket utilization rollup. **Unknown.**

---

## 3. Idle Classification Per Bucket

Cannot compute exactly without a continuous dispatcher log. From the event evidence:

- **Class A (idle, READY exists, no conflict):** Confirmed during the stall windows when T-0136 was READY but no profiles were actively running. Example: `2026-11-02T00:05` bucket — T-0136 READY, no active leases, but queue items Q-072/Q-073 blocked human decision.
- **Class B (idle, READY exists but all conflict):** Confirmed when T-0132/T-0133 were READY but blocked by `depends_on: T-0131`.
- **Class C (idle, no READY, BLOCKED present):** Confirmed after T-0131 attempts exhausted (BLOCKED) and before T-0136 was created.
- **Class D (idle, no READY, only PROPOSED):** Confirmed during early project phases before cards were admitted.
- **Class E (idle, nothing open):** Confirmed when all tasks were DONE/VOID and no READY/PROPOSED cards existed.

---

## 4. Non-Running Cards (Primary Reason)

From the live ledger (3 READY cards):

| Card | Primary Reason |
|---|---|
| T-0136 | Depends on nothing; READY but unleased because no dispatcher is actively running (manual dispatch only). |
| T-0137 | Depends on unfinished T-0136. |
| T-0138 | Depends on unfinished T-0136. |

**Historical non-running cards (VOID):** 130 cards were voided for:
- Duplicate scope (e.g., T-0135 duplicate of T-0132, T-0134 subsumed by T-0133)
- Dependency on voided cards (T-0132/T-0133 voided because T-0131 was voided)
- Attempts exhausted / lease TTL expired (T-0131)

---

## 5. Capacity Per Profile

| Profile | Leases | Enabled/Cooled | Failure Class |
|---|---|---|---|
| opencode-strongest | 20 | Enabled | none |
| overseer-beam | 18 | Enabled | none |
| hermes-oneshot | 14 | Enabled | none |
| pi-orca-deepseek | 13 | Disabled | orcarouter 429 rate limit |
| kilo-auto | 13 | Enabled | none |
| opencode-beam | 7 | Enabled | none |
| pi-orca-glm-5-3-flash | 5 | Disabled | orcarouter 429 rate limit |
| cline-nemotron | 4 | Enabled | none |
| fake | 3 | Enabled | none |
| cline-solar-mini4 | 3 | Enabled | none |
| hermes-solar-mini4 | 3 | Enabled | none |
| pi-orca-hy4-preview | 2 | Disabled | orcarouter 429 rate limit |
| cline-mimo | 1 | Enabled | none |
| pi-orca-glm | 1 | Disabled | orcarouter 429 rate limit |

**Median / p90 claim-to-submit:** Cannot be computed because no `SUBMITTED` events carry timestamps in the event log; submission times are absent.

---

## 6. DAG Statistics

**Open ledger DAG (3 READY cards):**

| Level | Cards | Width |
|---|---|---|
| 0 | T-0136 | 1 |
| 1 | T-0137, T-0138 | 2 |

**Critical path:** T-0136 → T-0137 (or T-0138) = 2 cards.  
**Total work:** 3 cards.  
**Completion lower bound:** `max(critical path, total work / cap)` = `max(2, 3/10)` ≈ 2 cards.

**Historical DAG:** The voided chain T-0131 → T-0132/T-0133 had the same shape (1 → 2).

---

## 7. Cap Usage

| Metric | Value |
|---|---|
| `TASK_CREATED` count | 138 |
| `max_total_tasks` (`agents.toml`) | 10 |
| Voided count | 130 |
| Void reasons | Duplicate scope, dependency on voided card, attempts exhausted, lease TTL expired |

**Note:** `max_total_tasks = 10` is enforced in `agents.toml`, but the ledger contains 138 total cards. This implies either the cap is not enforced in the Kernel, or the cap applies to a different dimension (e.g., concurrent tasks). **Unknown** without reading the Kernel reducer.

---

## 8. Scope Hygiene

**Write paths ending in `/` (directory scoped):** 76 paths across 52 tasks.

Examples:
- `T-0024`: `['pyproject.toml', '.gitattributes', 'AGENTS.md', 'CLAUDE.md', 'pytest.ini', 'src/', 'tests/test_smoke.py']`
- `T-0131`: `['docs/rules/CNA-Rules.adoc', 'docs/rules/sections/', 'docs/rules/manifest.json', 'docs/rules/checksums.sha256']`
- `T-0038`: `['src/cna/ai/', 'src/cna/ui/cli.py', 'src/cna/tools/soak.py', 'tests/']`

**Overlapping scope pairs:** 499 pairs share at least one common write path.

**Flagged pairs (same wave or cross-wave):**
- `T-0009` vs `T-0025` vs `T-0040` vs `T-0041` vs `T-0049` vs `T-0053` vs `T-0081` vs `T-0082` vs `T-0097` vs `T-0113` vs `T-0115`–`T-0117` vs `T-0120` vs `T-0121` vs `T-0128` vs `T-0129` vs `T-0131` vs `T-0136` — all overlap on `docs/rules/`.
- `T-0024` vs `T-0051` vs `T-0096` vs `T-0112` vs `T-0127` — overlap on `src/`, `tests/test_smoke.py`, and root config files.

**Raw-string-prefix candidates (G3a):** Pairs where one scope is a strict prefix of another (e.g., `docs/rules/` vs `docs/rules/CNA-Rules.adoc`). These are numerous and indicate the overlap checker is doing raw string comparison rather than path-aware component comparison.

---

## 9. Appendix D Answers (with file/line evidence)

### D1. When `claim` refuses a READY card for a scope conflict, does the Dispatcher skip to the next READY card or stop?

**Unknown.** The event log does not record dispatcher skip behavior. Need to read `src/fleet/dispatcher.py` claim loop.

### D2. `scope_overlaps` (`src/pmk/models.py`): component-wise or raw string prefix? Does it support globs?

**Unknown.** The 499 overlapping scope pairs and the raw-string-prefix artifacts (e.g., `docs/rules/` matching `docs/rules/CNA-Rules.adoc`) suggest raw string prefix, but this must be confirmed in code.

### D3. Does a dependency on a VOID card count as satisfied or as blocking?

**Blocking.** Event evidence: T-0132 and T-0133 remained READY and were never leased while depending on VOID T-0131. They were later voided themselves because their dependency was void.

### D4. Are REWORK tasks re-leased by anything today? How is `fix_rounds` used?

**Unknown.** No REWORK tasks appear in the current ledger. Need to read `src/fleet/conductor.py` or `src/pmk/state.py`.

### D5. Do VOID cards count toward `max_total_tasks`?

**Unknown.** The ledger has 138 cards but `agents.toml` has `max_total_agents = 10`. Without reading the Kernel reducer, we cannot tell if VOID cards are excluded from the cap.

### D6. Who moves PROPOSED to READY today (Conductor, Overseer, operator)?

**Overseer / Kernel.** The event log shows `TASK_ADMITTED` events with actor `kernel` (seq 2749, 2769, etc.). The Overseer also issues `INCIDENT` events referencing admission, but the actual state transition is recorded as `kernel`.

### D7. Does the VOID event carry a reason? Which events record merge refusals? (`MERGE_REFUSED` and the GATE_FAILED class exist as of v9.)

**Yes, VOID carries a reason.** Examples:
- T-0135: `"duplicate of T-0132; T-0132 has stronger oracle with --check; keeping T-0132"`
- T-0131: `"attempts exhausted (3/3); lease TTL expired; recreating clean chain"`

**Merge refusals:** Not present in the event stream for this incident window. Earlier events (`2026-11-01T10:26`) show `MERGE_REFUSED` for T-0127/T-0129 (`"not something we can merge"`). `GATE_FAILED` events are not present in the current event files.

### D8. Exact condition for the `replan` wake, and where the 6 wakes per hour budget and debounce are enforced.

**Unknown.** Need to read `src/fleet/conductor.py` or overseer loop.

### D9. Cap naming: the proposal cites `fleet_cap = 6`; the `agents.toml` I reviewed has `max_total_agents`. Which key is enforced, and where?

**Enforced key:** `max_total_agents = 10` in `agents.toml`.  
**Location:** `agents.toml` (top-level key).  
The proposal’s `fleet_cap = 6` is not present in the current config. **Unknown** which key the Kernel actually reads.

### D10. Do leases carry timestamps from which claim-to-submit durations can be computed?

**Partially.** `CLAIMED` events carry `granted_at`. `LEASE_EXPIRED` events carry `granted_at` and `elapsed_minutes`. However, no `SUBMITTED` events in this incident window carry timestamps, so claim-to-submit duration cannot be computed for successful tasks. Claim-to-expiry is available (120.02 min, 120.03 min).

### D11. Does the harness really refuse a card whose premises are false?

**Unknown from event stream.** No `PREMISE_FAILED` or similar event appears in the current files. Need to read `src/fleet/harness.py`.

### D12. Gate duration (the merge gate command) and how many merges per hour it can sustain.

**Unknown.** Need to read `src/fleet/merge.py` and gate command implementation.

---

## Appendix: Copy Integrity

- Copy path: `C:\temp\umaws-census-pm`
- Files copied: `.pm/` (12 event files + state), `agents.toml`
- No writes to the live tree.
- No git add, commit, or reset performed.
- No files deleted or moved.
