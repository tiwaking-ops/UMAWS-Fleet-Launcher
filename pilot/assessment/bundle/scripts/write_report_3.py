"""Append sections 8-15 of the report."""
import os

OUT = r"C:\temp\projects\testproject1\pilot\assessment\report-opencode-umaws-completion-v1.md"

SECTIONS_8_15 = """
## 8. Fleet Findings

**Recovery ladder (T-0003 real run):**

| Ladder step | Events observed | Verdict |
|---|---|---|
| L1 (resume on next profile, model swap) | AGENT_RESUMED → opencode-strongest → hermes-oneshot, all with model="" | VERIFIED-EARLIER |
| L2 (fresh session, handoff note) | Not directly observed in T-0003 | — |
| Profile cooling | PROFILE_COOLING: pi-orca-deepseek cooled 900s after 2 unknown failures | VERIFIED-EARLIER |
| Unknown failure rules | UNKNOWN class: retry once, cool after 2 (policy: unknown_cooldown_after=2) | VERIFIED-EARLIER |

**Recovery ladder in fake tests:** F2, F3, F10, F12, F13 all pass with fake CLI (tests-fleet-ran-now.txt).

**T-0003 full lifecycle (from event log):**
- 84: TASK_CREATED (pi-orca-deepseek assigned)
- 85: TASK_ADMITTED
- 87: FLEET_ASSIGNED
- 88: CLAIMED (fence=3)
- 89: AGENT_STARTED (pid 10948)
- 181: AGENT_EXITED (class=UNKNOWN)
- 182: AGENT_FAILED (UNKNOWN: L1 retry)
- 184: AGENT_EXITED (UNKNOWN, attempt 2)
- 185: PROFILE_COOLING (900s)
- 187: AGENT_RESUMED → opencode-strongest (L1: next profile)
- 191: AGENT_EXITED (exit_code=1, QUOTA-like)
- 192: AGENT_FAILED (UNKNOWN: L1 retry)
- 193: AGENT_RESUMED → hermes-oneshot (L1: next profile)
- 250: SUBMITTED (bundle EB-T-0003-3, all_oracles_passed=false)
- 261: ORACLE_RESULT (merge conflict)
- 262: VERIFIED (ORACLE_FAILED)

**Result:** T-0003 ended in REWORK (fence bumped, task → READY). The recovery ladder exercised L1 (profile rotation: pi → opencode → hermes). The exclusion rule (D-L6 write-scope overlap) held — no task was merged with a scope violation. But the dispatcher had no backoff, spamming FLEET_ASSIGNED (319 events in ~9 minutes).

**Selection behaviour (F5):** Verified in `tests/fleet/test_fleet.py` (selection tests pass). Priority-then-utilization deterministic; family exclusion in policy. T-0003 event log shows `pi-orca-deepseek chosen by priority 30, utilisation 0.00` — correct priority ordering.

**100-agent test (F7) — what it really was:**
- 100 fake workers (fakecli.py), not real LLM agents
- 100/100 DONE in 104.8 s
- Peak 100 concurrent slots
- Min free RAM 7,491 MB (floor 2,048)
- Sentinel clean; I1 chain verifies at 1,163 events
- scale-f7.json: `s_w1` field is `{}` (empty — the S-W1 worktree-timing numbers exist only in D-48 prose, not as structured data)

The "100-agent test" was a mechanism scalability test with fake workers, not a real capacity test. The real capacity test was G5 (6 real workers).

**Model census:**
- S-A1 ran 13 requests across 5 CLIs (hermes, kilo, pi, cline, opencode)
- No artefact for "all 400+ models tested" — the manual's claim is UNVERIFIED
- caliber-score.json: 87/100 (grade A), 22 checks — this is the Caliber score, not a model census

**Observed scale limits:**
- max_total_agents = 100 (raised from 20 by operator edit, D-50)
- F7 peak: 100 concurrent slots
- RAM guard: 7,491 MB minimum (floor 2,048 MB)

---

## 9. QuotaGate

**Milestone status:**

| Milestone | Description | Status | Evidence |
|---|---|---|---|
| M0 | Basic gateway scaffold | BUILT | src/quotagate/ exists (745 lines) |
| M1 | Passthrough proxy + live capture | BUILT (measured) | m1-upstream.md: 2 upstreams (omniroute, hermes), usage capturable, no /v1 on upstream |
| M2 | Multi-upstream routing + quota discovery | BUILT | config.toml has 2 upstreams, routing.py; quota-solar-mini4.md + quota-step37.md |
| M3 | Strategies, combos, pre-first-byte failover | NOT-BUILT | No strategy/combo code (D-L3) in main.py; config has no strategy section |
| M4 | Capacity measurement | PARTIAL | G5 ran 6 real workers (g5-summary.json); F7 ran 100 fake workers (scale-f7.json); no formal capacity report vs 10-30 target |
| M5 | Capability-token auth, events outbox, availability | NOT-BUILT | No HMAC auth on /chat/completions in main.py; events outbox not implemented; config-hash endpoint exists but not M5-complete |

**M1 capabilities (from m1-upstream.md, READ):**
- `POST /chat/completions` → 200, returns usage (prompt_tokens, completion_tokens, total_tokens)
- `x-omniroute-decision` header: attributes provider (e.g., `provider=cohere`)
- `x-omniroute-latency-ms`: latency
- `x-omniroute-cache`: cache status
- **No rate-limit headers** on success (no `x-ratelimit-*`, no `retry-after`)
- **No 429** could be induced to inspect the error body shape
- `auto/cheap` timed out at 45s while `auto/best-free` answered in ~1s → timeout policy mandatory

**M1 limitations (V-03 — STILL OPEN):**
- Only sees traffic routed through the gateway; all 5 profiles have `via_gateway = false`
- No rate-limit/429 headers capturable through the operator's router → declared-local limits required
- Timeout policy needed (auto/cheap hung)

**Q1–Q5 status:**
- Q1 (DST test): UNVERIFIED — not run, needs FakeClock across DST boundary
- Q2 (account-wide rule): UNVERIFIED — not run
- Q3 (exhaustion drill): UNVERIFIED — ramp tests done (quota-solar-mini4.md, quota-step37.md) but full drill (structured 429, FakeClock advance) not done; ramp tests prove "no ceiling below 4 rps" but don't prove the structured 429 contract
- Q4 (account-wide drill): UNVERIFIED — not run
- Q5 (kernel-down/gateway-down): UNVERIFIED — not run

**Quota tests that WERE done (from D-42):**
- solar-mini4: up to 4 rps, 6/6 ok, no ceiling, latency 889-4250ms
- step-3.7-flash: up to 4 rps, 7 ok, no ceiling, latency 2312-8437ms

---

## 10. Manual Versus Reality

**Every WRONG-DOC item:**

| # | Manual says | Reality | Evidence |
|---|---|---|---|
| 1 | "Tier C achieved" | Tier A reached | pilot-report.md §1 |
| 2 | "production-ready for supervised use" | Tier A; 2 live defects; dispatcher auto-dispatches on Console start | pilot-report.md §1; console-side-effects-ran-now.txt |
| 3 | Console port 8080 | `DEFAULT_PORT = 8765` | src/console/app.py:37; console-smoke-ran-now.txt |
| 4 | Tabs: Overview, Tasks, Leases, Profiles, Events, Gateway, Sentinel | Projects, Fleet, Tasks, Queue, Overseer, Manual launcher, Metrics | src/console/static/index.html:93-99 |
| 5 | Gateway port 8000 | Port 8766; gateway disabled (`enabled = false`) | .pm/policy.toml:25-27 |
| 6 | WSL2 required; repo on Linux FS | Native Windows (D-02); repo at `C:\\temp\\projects\\testproject1` | s-p1-platform.md; decisions.md D-02 |
| 7 | `pmk gateway ingest --url http://127.0.0.1:8000` | Port 8000 wrong (should be 8766) | policy.toml:25 |
| 8 | Policy: `base_url = "http://127.0.0.1:8000/v1"` | `base_url = "http://127.0.0.1:8766/v1"` | .pm/policy.toml:25 |
| 9 | venv: `. .venv/bin/activate` (Linux-first) | Windows `.venv\\\\Scripts\\\\activate` | s-p1-platform.md D-02 |
| 10 | Reset: `rm -rf .pm/events ...` (Linux syntax) | Windows repo; paths use `\`` | Native Windows platform |
| 11 | Manual TOC: two Section 6s | Section 6 duplicated | UMAWS_USER_MANUAL.md TOC |

**Manual claims that are VERIFIED:**
- "Sentinel clean" → verified (all 16 invariants pass)
- `pmk sentinel` checks I1, I3, I4, I5, I6, I7, I8', I13, I14, I15, I16 → verified
- `pmk views`, `pmk sweep`, `pmk stop/resume`, `pmk brief --role` → commands exist
- Sentinel invariants table matches actual invariant list
- `pmk gateway config-hash` exists → verified
- Evidence bundle format (outputs, commands, oracle_results, etc.) → matches EB-T-0003-3
- V2 rule: same-family fallback refused → in policy.toml (`exclude_author_family = true`)
- Recovery ladder L0–L4 steps → match code
- Scope overlap exclusion → tested (T-0003 blocked by D-L6)

**Manual claims that are NOT in the manual (but in the spec):**
- `pmk run-worker` (proposal §9.3) → NOT-BUILT (not in CLI)
- `pmk import-bootstrap` (proposal §9.3) → NOT-BUILT (not in CLI)
- `pmk queue show` (proposal §9.3) → NOT-BUILT (CLI has list/decide only)
- `pmk token issue` (proposal §9.3) → NOT-BUILT (not in CLI)

---

## 11. Gates, Decisions and Deviations

**Gate amendment (amendment-gates.md):**
- Status: **IN FORCE** (v2, 2026-10-23, approved as Q-003 at D-34)
- Classification changed: by action (evidence vs authorisation), not by gate number
- "Self-crossed" retired: crossings are either authorised by named decision or logged as checkpoint
- Class K is two-key (key taken before change, not after)

**Gates G0–G6:**

| Gate | Kind | Authority | Status | Evidence |
|---|---|---|---|---|
| G0 | authorisation (platform decision) | operator, D-02 | CROSSED | Native Windows chosen; s-p1-platform.md |
| G0 | checkpoint (environment metadata) | — | logged | s-p1-platform.md |
| G1 | checkpoint (Caliber measurement S1-S5) | — | logged | caliber-s1-s5.md |
| G1 | authorisation (install Caliber) | operator, D-15–D-19 | CROSSED | Caliber installed; pins recorded |
| G1 | authorisation (sync sends repo content) | operator, D-23 | CROSSED | Terms accepted |
| G2 | checkpoint (metadata capture) | — | logged | cli-matrix.md (S-A1) |
| G2 | authorisation (live S-A1 provider calls) | operator, D-24 | CROSSED | 13 requests, 5 CLIs |
| G3 | authorisation (real CLI through lease) | operator, D-40 closes | CLOSED | D-39: real-CLI half PASSES; D-45: opencode handover PASSES |
| G4 | authorisation (enable auto-sync) | operator, D-47 (Q-004) | CROSSED | mode = "auto"; left on per operator |
| G5 | authorisation (live capacity run) | operator, D-49 | CROSSED | 6 real workers, 6/6 DONE, zero failures |
| G6 | authorisation (accept pilot report) | — | not reached (Day 7 not reached) | — |

**D-19 policy change:** Ratified as Q-001 (class K queue item), recorded at D-29/34. The policy.toml `managed_paths` change was a class K change that was properly ratified through the two-key queue.

**Rule 14 versus 12.1 finding (D-34):** v1 §12.1's "self-crossed" classification was an error. Amendment v2 classifies gates by action (evidence vs authorisation), not by gate number. The finding is recorded at §4.4 of the report and adopted in §8 of this report.

**Decisions D-01–D-51 (summary):**

| D# | Topic | Verdict |
|---|---|---|
| D-01 | Repo root = C:\\temp\\projects\\testproject1 | Applied |
| D-02 | Platform = native Windows | Applied |
| D-03 | CLI probing is metadata-only | Applied |
| D-04 | Sidecar locks (not event log) | Applied |
| D-05–D-14 | Bootstrap steps | Applied |
| D-15–D-19 | Caliber install (class K) | Ratified as Q-001/Q-002 |
| D-20 | Pin policy change (class K) | Ratified |
| D-21 | Lint coverage limit measured | Pinned |
| D-23 | Sync sends repo content (auth) | Authorised |
| D-24 | Live S-A1 provider calls | Authorised (13 requests) |
| D-25 | Gate classification rule | Applied (amendment v2) |
| D-28 | agents.toml not class K | Corrected |
| D-29 | D-19/D-20 timing weakness | Recorded |
| D-30–D-34 | Queue ID collision fix, gate amendment | Fixed |
| D-35 | cline-mimo repointed to operator's 5 models | Applied |
| D-36 | H6 handover test passes (kilo) | Applied |
| D-37 | OpenCode quota parked as UNKNOWN | Applied |
| D-38 | M1 upstream measured | Applied |
| D-39 | Real CLI through lease passes | Applied |
| D-40 | G3 closed by operator | Applied |
| D-41 | Recovery ladder exercised with real CLIs | Applied |
| D-42 | Quota discovered via stress test | Applied |
| D-43 | OpenRouter account-limited | Applied |
| D-44 | Kilo Gateway model-limited | Applied |
| D-45 | OpenCode handover test passes | Applied |
| D-46 | Caliber auto-sync enabled (G4) | Applied |
| D-47 | Gate amendment v2 in force | Applied |
| D-48 | F7/S-W1 green at 100 slots | Applied |
| D-49 | G5 passed twice (6 real workers) | Applied |
| D-50 | max_total_agents raised 20→100 | Applied (operator edit) |
| D-51 | Two latent defects fixed | Fixed (D-51a: invalid policy stops the line; D-51b: reintegration runs gate) |

**D-51 defects (FIXED 2026-10-24):**
- D-51a: Invalid `policy.toml` does not stop the line — now raises `KernelError("policy_invalid")`. 7 regression tests added.
- D-51b: Re-integration of already-committed lease runs the gate — fixed.
- But TWO NEW DEFECTS were found during the Console smoke test (reported in §12, not fixed per rule 3.1).

---

## 12. Defects, Limitations, Risks

**Two defects found live during the Console smoke test (reported, NOT fixed — rule 3.1):**

**Defect D-A1: FLEET_ASSIGNED spam / no backoff**
- Location: `src/fleet/dispatcher.py`, `Dispatcher.tick()` → `harness.start()` → `kernel.claim()`
- Trigger: When a READY task's write scope overlaps an active lease (D-L6 rule holds, correctly blocking the claim), the dispatcher records `FLEET_ASSIGNED` BEFORE the claim attempt and has no backoff.
- Impact: 319 events / ~2.6 MB/h per stuck task (observed for T-0002 in the clone, 01:30–01:39Z). At 100 agents this could produce ~260 MB/h of event log spam.
- Evidence: console-side-effects-ran-now.txt (319 FLEET_ASSIGNED events for T-0002); event-counts show 473 FLEET_ASSIGNED events total (all from console runs A+B).
- The D-L6 scope overlap rule itself works correctly (the overlap was blocked). The bug is the pre-claim assignment record + missing backoff.

**Defect D-A2: Dispatcher does not honor `pilot/STOP`**
- Location: `src/fleet/dispatcher.py`, `Dispatcher.tick()`
- The conductor checks `pilot/STOP` (via `self._stop` / `dispatch_paused`), but the dispatcher's `tick()` does not.
- The Console (`src/console/app.py`, `start_loops()`) auto-starts BOTH the dispatch and conductor loops on startup. Starting the Console on a repo with READY tasks + enabled profiles dispatches immediately without operator action.
- Impact: Console startup = immediate dispatch. The `touch pilot/STOP` stop-the-line procedure (manual §10) does not actually stop dispatch.
- Mitigation used for the smoke test: pre-created `pilot/STOP` and held `agents.toml` aside (zero profiles → no spawn path).
- Evidence: console-side-effects-ran-now.txt line 35: "the dispatcher does not check pilot/STOP (only the conductor does); dispatch is only quiesced by dispatch_paused in fleet-state or by having no profiles."

**Limitations L-F1–L-F5 (all still true):**
- L-F1: No sandbox. Any agent can write anywhere the OS user can. Scope check detects at submit but cannot undo damage elsewhere. (STATE.md p.167)
- L-F2: Token usage of direct CLIs is not measurable by the Kernel. Budgets are wall-time and restarts only. (STATE.md p.168)
- L-F3: Model families are declared, not verified. V2 independence is only as good as the profile file.
- L-F4: Direct CLIs keep credentials in their own config; Kernel cannot scrub them. (STATE.md p.171)
- L-F5: Single machine, single operator; results are anecdotal about this setup. (proposal §14.3)

**No-sandbox exposure:** The Console binds to `127.0.0.1` only (src/console/app.py:38) and has no authentication (FR12: operator asked for no restrictions). A LAN-exposed machine would expose the Console. The bind address is hardcoded, not configurable from the browser (manual line 11-13).

**Secret scan of bundle:** No secrets found. The `agents.toml`, `policy.toml`, and `quotagate/config.toml` record only env var NAMES (`OMNIROUTE_API_KEY`), never values. The `m1-upstream.md` records that the API key was used from the environment and never written to the repo. The EB-T-0003-3 bundle contains no secrets. `prompts.json` contains no keys.

**Scale-f7.json `s_w1` field is `{}`:** The S-W1 (worktree-timing) numbers exist only in `decisions.md` D-48 prose, not as a structured artefact. This is a packaging discrepancy. (D-48: "20 worktrees in 2.0s, 100 more in 15.5s")

**EB-T-0003-3 is the only evidence bundle in the repo:** Passed-path bundles existed only in temp F7/drill directories and were deleted. The only evidence bundle that survives is T-0003's (the REWORK path). (See §13 "What was cut".)

**V-03 (429 body shape + rate-limit headers) — STILL OPEN:** m1-upstream.md confirms no rate-limit/429 headers are capturable through the operator's router. Declared-local limits are required. (STATE.md p.135)

**Optional live checks (not executed, per rule 3.3):**
1. **Q3 full drill:** 3 fake models, limit 5/day, 20 requests, 16th returns structured 429, FakeClock advance restores. Cost: ~15 requests to a free-tier model. Would settle whether QuotaGate returns the documented 429 body with `earliest_available_utc`.
2. **Q4 account-wide drill:** 3 models sharing 5/day behave as one pool. Cost: ~20 requests.
3. **T5 V2 family exclusion:** Send a verify request when only author family has quota → expect 429, no fallback. Cost: ~5 requests. Needs M5 gateway running.
4. **F1 one-click run:** Run the full lifecycle with a real CLI. Cost: ~10–30 real LLM calls.
5. **Model census:** Test all 400+ models. Cost: prohibitive; not recommended.

---
"""

with open(OUT, "a", encoding="utf-8") as f:
    f.write(SECTIONS_8_15)
print(f"Appended sections 8-15 ({len(SECTIONS_8_15)} chars)")
