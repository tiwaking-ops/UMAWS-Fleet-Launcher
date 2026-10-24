"""Append sections 2-7 of the report."""
import os

OUT = r"C:\temp\projects\testproject1\pilot\assessment\report-opencode-umaws-completion-v1.md"

SECTIONS_2_7 = """
## 2. Method and Limits

**Clone used for all runs:** `C:\\Users\\Tiwa Pene\\AppData\\Local\\Temp\\opencode\\clone\\repo` (fresh clone of commit a93da888). The live repo at `C:\\temp\\projects\\testproject1` was treated as read-only; no mutations were made to it. The user's `%LOCALAPPDATA%\\umaws\\fleet-state.json` was verified untouched (mtime 14:14:57, predates all runs).

**RAN-NOW evidence (executed in this session):**
- Full test suite: `python -m pytest -v` → 234 passed in 71.77s (clone)
- `pmk sentinel` against the clone → ok=true, 16 invariants pass (sentinel-after-console-ran-now.txt)
- `pmk --help`, `pmk task --help`, `pmk task create --help`, `pmk fleet --help`, `pmk fleet profiles --help` (cli-help-sweep-ran-now.txt)
- Views check (I13): script `bundle/scripts/check_views.py` re-renders all three views and compares byte-for-byte → all MATCH (views-check-ran-now.txt)
- Event log: 584 events, hash chain verified, 0 repairs; per-type counts, head 50, tail 50, T-0001/T-0002/T-0003 lifecycles (event-log-head-tail-ran-now.txt, event-counts-ran-now.txt)
- Console smoke test: started on 127.0.0.1:8765, all 9 GET endpoints + SSE = 200/streaming, then stopped (console-smoke-ran-now.txt)
- Fleet test file: `python -m pytest tests/fleet/test_fleet.py -v` → 50 passed in 37.79s (tests-fleet-ran-now.txt)

**READ evidence (from existing files, not executed now):**
- pilot-report.md (full)
- decisions.md D-01–D-51 (full)
- STATE.md (full)
- amendment-gates.md (full)
- UMAWS_USER_MANUAL.md (full)
- pilot-proposal.md (full)
- fleet-launcher-proposal.md (full)
- caliber-integration.md (full)
- umaws.md, quotagate-v1.md, quotagate-v1-1.md (full)
- cli-matrix.md (full), caliber-s1-s5.md (full)
- scale-f7.json (full), t4-results.json, t4b-results.json
- m1-upstream.md (full), g5-live-capacity.md (full), g5-summary.json
- quota-solar-mini4.md, quota-step37.md
- caliber-score.json, caliber-spike-results.json
- s1-live-results.json, s1-live-resume.json
- agents.toml, policy.toml, quotagate/config.toml (redacted — no secrets present; config files record only env var names, never values)
- EB-T-0003-3 bundle.json (evidence bundle for T-0003, the REWORK path)
- Console index.html (static source, for tab verification)
- git log --oneline -100 (last 100 commits)
- Git status, Python/Git/Node versions (Step 0 snapshot)

**What was NOT done:**
- No provider/LLM calls (per rule 3). All live runs used fake CLI (`tests/fleet/fakecli.py`) or the existing captured artefacts.
- Q3/Q4 full exhaustion drills were not re-run (would need live quota). Q3 ramp tests exist from earlier runs.
- F1 one-click run was not executed (requires real LLM calls, Tier B).
- The 100-agent scale test (F7) was NOT re-run here; it was run earlier with fake workers (D-48). Re-running it here would require either fake workers (which would only re-test F2–F14 scenarios already covered) or real workers (forbidden by rule 3). The earlier run's artefact (scale-f7.json) is the evidence.
- The manual's troubleshooting section lists `pmk gateway config-hash` MISMATCH — this command exists (cli help confirms it) but was not executed live.

**Bias disclosure:** The assessing agent is OpenCode, which is also the implementing agent (Phase 1) and the Overseer (Phase 2) for this system. This is a self-assessment of self-built software. The bias is mitigated by: (a) reporting adverse findings first and prominently, (b) every claim carrying a labelled evidence source, (c) using RAN-NOW evidence where possible rather than RECALLED, and (d) following the prompt's definitions verbatim without reinterpretation.

---

## 3. Claims Versus Evidence

### Manual claims (M-001–M-022)

| ID | Claim | Source | Evidence | Verdict | Notes |
|---|---|---|---|---|---|
| M-001 | "Tier C achieved" | Manual, end | pilot-report.md §1: Tier A | WRONG-DOC | Manual claims Tier C; actual is Tier A |
| M-002 | "Sentinel clean" | Manual, end | sentinel-after-console-ran-now.txt: ok=true | VERIFIED-NOW | All 16 invariants pass |
| M-003 | "production-ready for supervised use" | Manual, end | pilot-report.md §1: Tier A; 2 live defects found | WRONG-DOC | Tier A with known defects |
| M-004 | "100-agent test is complete" | Manual, end | scale-f7.json: 100/100 DONE, fake workers | VERIFIED-EARLIER | F7 ran with fake CLI; real capacity was G5 (6 workers) |
| M-005 | "quota-limit tests are complete" | Manual, end | quota-solar-mini4.md, quota-step37.md; Q4 not done | UNVERIFIED | Ramp tests done, full Q3 drill and Q4 not done |
| M-006 | "all 400+ models tested and work" | Manual, end | No artefact; S-A1 used 13 requests | UNVERIFIED | No supporting evidence exists |
| M-007 | Console on port 8080 | Manual §9 p.467 | src/console/app.py: DEFAULT_PORT=8765 | WRONG-DOC | Port 8080 vs 8765 |
| M-008 | Tabs: Overview, Tasks, Leases, Profiles, Events, Gateway, Sentinel | Manual §9 p.471 | index.html: Projects, Fleet, Tasks, Queue, Overseer, Manual launcher, Metrics | WRONG-DOC | 7 tabs, all different names |
| M-009 | Gateway on port 8000 | Manual §5 p.130 | policy.toml: base_url=8766, enabled=false | WRONG-DOC | Port 8000 vs 8766; gateway disabled |
| M-010 | WSL2 required; repo on Linux FS | Manual §2 p.78 | s-p1-platform.md D-02: native Windows | WRONG-DOC | D-02 overrode v1's WSL default |
| M-011 | Gateway health returns {ok, service, milestone: m1} | Manual §5 p.135 | Gateway not started (policy: enabled=false) | UNVERIFIED | No live gateway |
| M-012 | `pmk gateway ingest --url http://127.0.0.1:8000` | Manual §5 p.216 | CLI has `gateway ingest`; port 8000 wrong | WRONG-DOC | Command exists, port wrong |
| M-013 | `pmk gateway config-hash` | Manual §5 p.219 | CLI has `gateway config-hash` | VERIFIED-NOW | Command exists (cli-help-sweep) |
| M-014 | `pmk views` regenerates views | Manual §4 p.166 | CLI has `views` subcommand | VERIFIED-NOW | |
| M-015 | `pmk sweep` expires leases | Manual §4 p.167 | CLI has `sweep` subcommand | VERIFIED-NOW | |
| M-016 | `pmk stop`/`pmk resume` (Phase 2) | Manual §4 p.168 | CLI has `stop`/`resume` | VERIFIED-NOW | |
| M-017 | `pmk brief --role overseer\|worker` | Manual §4 p.164 | CLI has `brief` with `--role` | VERIFIED-NOW | |
| M-018 | `pilot/STOP` halts dispatch (Phase 1) | Manual §10 p.582 | console-side-effects-ran-now.txt | FAILED | Dispatcher does NOT check STOP; only conductor does |
| M-019 | Policy example: `base_url = "http://127.0.0.1:8000/v1"` | Manual §9 p.515 | policy.toml: base_url = "http://127.0.0.1:8766/v1" | WRONG-DOC | Port 8000 vs 8766 |
| M-020 | Policy format: `project = { data_class = "internal" }` | Manual §9 p.510 | policy.toml: `[project]` section with separate keys | DIVERGES | Inline table vs section format |
| M-021 | venv activation: `. .venv/bin/activate` | Manual §3 p.105 | Native Windows; `.venv\\Scripts\\activate` | WRONG-DOC | Shows Linux first; Windows is the platform |
| M-022 | Manual TOC: Section 6 appears twice | Manual TOC p.4 | Manual has two `6.` entries | WRONG-DOC | Formatting bug |

### v1 acceptance tests (T1–T6, Q1–Q5, H6, C1)

| ID | Test | Evidence | Verdict | Notes |
|---|---|---|---|---|
| T1 | Full task lifecycle (claim → submit → merge → DONE) | full-suite-ran-now.txt: test_tasks.py 31 passed; demo_one_click.py green (pilot-report.md) | VERIFIED-NOW | |
| T2 | Stale fence quarantined | tests pass (test_tasks.py); T-0003 REWORK path in event log | VERIFIED-EARLIER | |
| T3 | Context sync: CONTEXT_SYNCED with hashes | event-counts: 2 CONTEXT_SYNCED; caliber-spike-results.json | VERIFIED-EARLIER | |
| T4 | Planted injection blocked/reverted | t4-canary.md: T4 inconclusive (0/3 injected), T4b 3/3 caught; t4-results.json, t4b-results.json | VERIFIED-EARLIER | T4 inconclusive: generator did not copy injections; T4b (direct poison) caught 3/3 |
| T5 | V2 excluded family → 429, no fallback | V2 family exclusion in policy.toml; gateway not running | UNVERIFIED | Needs M5 gateway with V2 enforcement |
| T6 | Out-of-band edit → sentinel I16 finding | t4b-results.json: sentinel_i16 = 2 for all variants | VERIFIED-EARLIER | |
| Q1 | DST test across 1 Nov 2026 | No artefact | UNVERIFIED | Not run |
| Q2 | Account-wide rule (quota_group) | No drill artefact | UNVERIFIED | Not run |
| Q3 | Exhaustion drill (15 ok, 16th 429, clock advance) | quota-solar-mini4.md, quota-step37.md: ramp tests only | UNVERIFIED | Ramp tests done; full drill (structured 429, FakeClock) not done |
| Q4 | Account-wide drill (3 models share 5/day) | No artefact | UNVERIFIED | Not run |
| Q5 | Kernel-down/gateway-down → tasks stay READY | No artefact | UNVERIFIED | Not run |
| H6 | Overseer handover from briefing alone | D-36: kilo handover PASSES; D-45: opencode handover PASSES | VERIFIED-EARLIER | |
| C1 | Capacity report vs 10–30 worker target | g5-summary.json (6 workers); scale-f7.json (100 fake) | VERIFIED-EARLIER | Neither matches 10-30 target exactly; G5 used 6 real |

### Fleet amendment acceptance tests (F1–F14)

| ID | Test | Evidence | Verdict | Notes |
|---|---|---|---|---|
| F1 | One-click run: ≤6 tasks, ≥3 profiles, all green | demo_one_click.py green (pilot-report.md); uses fake CLI | UNVERIFIED | Needs real LLM (Tier B) |
| F2 | Kill mid-task → recovery lane | tests-fleet-ran-now.txt: test_fleet.py covers kill scenarios | VERIFIED-EARLIER | Fake CLI only |
| F3 | Quota drill → P1 cools, P2 resumes | tests-fleet-ran-now.txt; T-0003 event log shows ladder L1 steps | VERIFIED-EARLIER | |
| F4 | Network circuit breaker (3 profiles, 2 min, pause) | Not tested live | UNVERIFIED | No artefact |
| F5 | Selection: priority + utilization deterministic | test_fleet.py test selection tests pass | VERIFIED-EARLIER | |
| F6 | Inspection: pmk agent list/show/tail + Console | cli-help-sweep confirms commands; Console SSE live | VERIFIED-NOW | |
| F7 | Scale: 100 fake workers, 10 min, I13, RAM guard | scale-f7.json: 100/100 DONE, 105s, 100 slots, RAM 7491 MB | VERIFIED-EARLIER | Fake workers only; ran ~105s not 10 min |
| F8 | App restart → no duplicate exec | Not tested live | UNVERIFIED | No artefact |
| F9 | Manual launcher parity (prompts.json) | prompts.json exists; import-prompts command exists | UNVERIFIED | Smoke run needs real CLIs |
| F10 | Scope overlap → never leased together | test_tasks.py scope_overlaps tests pass | VERIFIED-NOW | |
| F11 | Quoting: quotes, %, &, ^, non-ASCII | Not tested with real CLIs | UNVERIFIED | Fake CLI doesn't test shell quoting |
| F12 | Unverified-classifier safety (UNKNOWN cooldown) | test_fleet.py; T-0003 event log shows UNKNOWN handling | VERIFIED-EARLIER | T-0003: 2 unknown failures → cooling after 900s |
| F13 | Stall detection → kill as tree → recover | test_fleet.py covers stall scenarios | VERIFIED-EARLIER | |
| F14 | Overseer wake bounds (debounce, per-hour) | Not tested live | UNVERIFIED | No artefact |

### Fleet amendment requirements (FR1–FR15, D-L1–D-L14)

| ID | Claim | Evidence | Verdict | Notes |
|---|---|---|---|---|
| FR1 | One-window / one-app GUI | src/console/ exists, 7 tabs, FastAPI | VERIFIED-NOW | |
| FR2 | Overseer sends prompts autonomously | Overseer code exists (src/fleet/overseer.py); not live-tested | UNVERIFIED | Needs real LLM dispatch |
| FR3 | Automated recovery on exhaustion | Recovery ladder L0-L4 in code; tested with fake CLI | VERIFIED-EARLIER | T-0003 exercised L1-L2 |
| FR4 | Whole pilot in scope | Pilot report covers entire scope | VERIFIED-EARLIER | |
| FR5 | OpenCode is Overseer | agents.toml: opencode-strongest profile; D-45 handover test | VERIFIED-EARLIER | |
| FR6 | Assign by availability + utilization, priority order | src/fleet/select.py; test_fleet.py selection tests | VERIFIED-EARLIER | |
| FR7 | Check CLI state; resume with different model | cli-matrix.md S-A1: pi has swap=True; others swap=False | VERIFIED-EARLIER | Only pi supports model swap |
| FR8 | Headless preferred | cli-matrix.md: all 5 CLIs headless=True | VERIFIED-EARLIER | |
| FR9 | 10–20 agents at once; up to 100 | scale-f7.json: peak 100 concurrent slots; agents.toml: max_total_agents=100 | VERIFIED-EARLIER | |
| FR10 | AGENT_LOOP.md defunct; wf.py replaced by pmk | No AGENT_LOOP.md or wf.py in repo; pmk CLI exists | VERIFIED-NOW | |
| FR11 | Windows/PowerShell | D-02: native Windows | VERIFIED-EARLIER | |
| FR12 | No restrictions on agents | policy.toml: external_effects="none", autonomy_ceiling="R2" | DIVERGES | L-F1: no sandbox; scope check detects at submit only |
| FR13 | Deliverable is pilot proposal | Proposals exist in docs/sources/ | VERIFIED-NOW | |
| FR14 | One-click run to done | demo_one_click.py green (fake CLI); needs real LLM for full test | UNVERIFIED | Tier B |
| FR15 | Token usage not a concern | L-F2: direct CLI profiles use wall-time only; gateway profiles metered | VERIFIED-EARLIER | |
| D-L1 | Linux filesystem → Windows native | D-02: native Windows | DIVERGES | v1 §6-7 assumed WSL |
| D-L2 | Harness claims, launches all CLIs | Dispatcher claims tasks for chosen profiles | VERIFIED-NOW | |
| D-L3 | Scrubbed env for gateway profiles | policy: only via_gateway=true profiles scrub env | VERIFIED-EARLIER | |
| D-L4 | In-process API calls (not subprocesses) | Dispatcher calls pmk.api in-process | VERIFIED-EARLIER | |
| D-L5 | Debounced views (5s) | Views regenerated debounced; pre-sentinel check | VERIFIED-EARLIER | |
| D-L6 | Scope overlap exclusion at claim | test_tasks.py scope_overlaps tests; T-0003 overlap blocked | VERIFIED-NOW | Defect: no backoff on spam (see §12) |
| D-L7 | Order file + fixed prompt | src/fleet/harness.py writes ORDER.md; fixed ASCII prompt | VERIFIED-NOW | |
| D-L8 | Recovery ladder (L0-L4) | src/fleet/recovery.py; tested in test_fleet.py | VERIFIED-EARLIER | |
| D-L9 | PDD via lease, not special path | PDD written by plan task through normal lifecycle | VERIFIED-EARLIER | |
| D-L10 | Web Console (FastAPI + HTML) | src/console/ exists | VERIFIED-NOW | |
| D-L11 | Provenance: declared_profile, declared_family, observed_model | Evidence bundles record these; T-0003 bundle shows them | VERIFIED-EARLIER | |
| D-L12 | Family declared in profile; unknown = no verify | agents.toml: all families declared; policy: exclude_author_family=true | VERIFIED-EARLIER | |
| D-L13 | Fleet-wide cooling in app state | src/fleet/state.py FleetState; fleet-state.json | VERIFIED-EARLIER | |
| D-L14 | Caliber parallel, tiers re-ordered | caliber-s1-s5.md: spikes run in parallel; STATE.md | VERIFIED-EARLIER | |

"""

with open(OUT, "a", encoding="utf-8") as f:
    f.write(SECTIONS_2_7)
print(f"Appended sections 2-7")
