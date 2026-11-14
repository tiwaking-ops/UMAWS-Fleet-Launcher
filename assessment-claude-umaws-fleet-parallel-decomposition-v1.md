---
document:
  title: "Assessment of the Parallel Decomposition Proposal for the UMAWS Fleet Overseer: diagnosis, gaps and an improved plan"
  type: "Assessment and recommendations"
  status: "Advisory; no authority"
  version: "1.0.0"
provenance:
  author_llm: {name: "Claude", version: "Claude Sonnet 5.5 (Anthropic)"}
  assessed_document: "proposal-deepseek-umaws-fleet-parallel-decomposition-v1.md (v1.0.0, deepseek-v4-flash-free, 2026-11-02)"
  created_date: "2026-11-02"
  last_modified_date: "2026-11-02"
audience:
  primary: "The human operator (decision record)"
  secondary: "Implementing LLM(s) (executable brief, sections 6, 7 and the appendices)"
evidence_basis: "The proposal, read in full. My earlier review of the Kernel and fleet code (hardening rounds v5 to v11, state as of 2026-10-28) and of agents.toml as of that date. I have NOT seen the CFNA ledger, event log, PDD, HANDOFF.md or the repo as it stands today."
epistemic_status: "Tags: [PROPOSAL] claimed by the assessed proposal, not checked by me; [OBSERVED] seen in code or files during my earlier review; [INFERRED] my reasoning; [GUESS] needs measurement; [VERIFY] check in code before relying on it; [SPECULATIVE] effort estimate."
authority_statement: "Candidate tier. This document recommends; nothing takes effect until the operator decides. Changes to Kernel code need the operator's acceptance; changes to .pm/policy.toml or .pm/constitution.md are class K (two-key)."
---

# Assessment: Parallel Decomposition for the UMAWS Fleet Overseer

## 0. How to use this document

1. **Operator:** read section 1 (verdict), section 5 (where "gated" really comes from) and section 8 (decisions needed).
2. **Implementing LLM:** sections 6 and 7 and the appendices. Do not start Phase 2 until the Phase 0 report has been reviewed by the operator.
3. Nothing here has been run. Statements about CFNA's current state are second-hand from the proposal. Statements about code come from my earlier review or are marked [VERIFY].

---

## 1. Verdict

**Adopt the direction. Do not implement the plan as written.**

The proposal's core idea is sound: treat decomposition as a verified production step (machine-check a wave before it is released), give the Overseer feedback, and measure slot utilisation. It correctly leaves D-L6 (strict disjoint write scopes), the merge machinery and the cap of 6 alone. [OBSERVED: those mechanisms are enforced; I reviewed them.]

It is not ready to build because of four structural problems:

1. **The diagnosis is unproven.** It blames a shortage of READY cards, from one snapshot (2 DONE / 3 LEASED / 0 READY) [PROPOSAL]. Your symptom is "too many tasks are gated". Gating has at least nine possible causes (section 5); the proposal addresses two of them.
2. **The lint checks safety, not parallelism.** A wave of 40 cards in one dependency chain passes every proposed check and yields one busy slot.
3. **Validation happens after the cards exist.** Failed waves leave PROPOSED clutter, and the 125 voided cards in CFNA [PROPOSAL] show the cost: voiding is operator-only (`task_void` refuses non-human actors) [OBSERVED], and voided cards probably count against the lifetime `max_total_tasks = 500` cap [VERIFY].
4. **It recommends pipelines of `depends_on` chains without a cost model.** Chains are one of the main things that create "gated" work.

| Part of the proposal | Verdict |
|---|---|
| Wave lint as the decomposition oracle | Adopt; move it before card creation; extend it to measure width and critical path |
| Decomposition Contract (prompt) | Adopt in shorter, template-driven form (Appendix C) |
| Briefing digest and metrics | Adopt |
| Keep D-L6, merge rules, cap 6 | Agree |
| "Bottleneck is upstream of the Dispatcher" | Unproven; run the Phase 0 census first |
| 20 to 45 min budget, at most 3 write paths | Calibrate from real lease durations, not fixed |
| Not covered at all | Capacity census, dispatcher look-ahead, REWORK and orphaned-dependency handling, low-water-mark wake, architecture-first module map |

**Recommended order:** Phase 0 diagnose (about half a day, read-only) then Phase 1 unblock (cheap fixes) then Phase 2 decompose properly (manifest, module map, lint v2, prompt v2) then Phase 3 schedule smarter and tune.

**Realistic outcome:** sustained concurrency of 4 to 6 on free-tier models [GUESS], versus about 2 today. The ceiling is the lower of the cap (6, from the CFNA PDD) and the number of healthy profile slots. No decomposition work can exceed provider capacity (the proposal's own N-2).

---

## 2. What I could and could not see

- **Read in full:** the proposal (479 lines).
- **Known from earlier review:** the Kernel and fleet code up to 2026-10-28, including `agents.toml` (profiles: hermes-oneshot 4, kilo-auto 3, pi-orca-deepseek 2, cline-mimo 1, opencode-strongest 2, opencode-fallback 1; sum 13; implement-capable sum 12) [OBSERVED, testproject1 copy; CFNA's file may differ].
- **Not seen:** the CFNA event log and ledger, current profile health, `docs/PDD.md`, `HANDOFF.md`, source changes after 2026-10-28.

This matters most for finding F-1: only the census (Appendix A) can say why slots idle.

---

## 3. What the proposal gets right (keep)

1. Correct framing: the parallel machinery exists and is proven (F7 with 100 fake workers, G5 with 6 real workers) [PROPOSAL, consistent with my review].
2. "Oracles decide" applied to decomposition: a machine check before release, not a prompt wish.
3. No relaxation of D-L6 and no change to the enforcement net (claim-time overlap refusal, submit-time `scope_check`, write-scope-only merge).
4. Interface-first splitting: contract cards before consumers.
5. Honest ceiling and honest tagging ([GUESS], [VERIFY]); the proposal says plainly that nothing has been run.
6. Metrics and an acceptance test series (F-D) with a fake-CLI tier and a real-demo tier.
7. A cut order with "never cut" items.

---

## 4. Findings on the proposal

| # | Finding | Why it matters | Fix |
|---|---|---|---|
| F-1 | **Diagnosis rests on one snapshot** (0 READY, 3 LEASED, 125/130 voided). "Upstream of the Dispatcher" is [INFERRED]. The proposal defers its own key metrics (slot idle minutes, void reason) to later work. | If slots idle while READY cards exist, more decomposition will not help. | Phase 0 census (Appendix A) before any build. |
| F-2 | **Lint has no parallelism check.** Only admission, disjointness, coverage, acyclicity, budget, oracle, premises. | A serial chain passes. | Add width, depth and critical-path checks (Appendix B, H). |
| F-3 | **Lint runs on cards that already exist** (waves sit PROPOSED, failures enqueue queue items). | Bad cards still enter the ledger, get voided by the operator, and burn the task cap. | Validate a wave manifest atomically before any card is created (R6). |
| F-4 | **`wave_id` is supplied by the LLM**, and the Conductor lints "on wave creation". | If the Overseer omits `wave_id`, nothing is gated. | Kernel assigns `wave_id` (wake id or manifest hash). |
| F-5 | **Coverage check is ambiguous** (per wave or per ledger). | A partial wave for one goal would be rejected for not covering all goals. | Coverage is ledger-wide; a wave is checked only for the goals it introduces. |
| F-6 | **Disjointness is checked only against LEASED/SUBMITTED.** | Overlaps with READY, BLOCKED, PROPOSED and REWORK cards from earlier waves serialise later. This cross-wave overlap is the most likely hidden gate. | Check against all non-terminal cards. |
| F-7 | **"Files, not directories"** for write scope. | New code has unknown filenames; real cards need directory scopes, and a directory scope blocks every other card in it. | Directory lanes owned per module, plus a skeleton card (R7). |
| F-8 | **Budget bounds contradict the data:** cards of 20 to 45 min versus 30 to 80 min observed per task [PROPOSAL, sections 4.1 and 6.1]. | Tasks that routinely exceed `wall_min` trip stalls and restarts. | Calibrate `wall_min` from p90 lease durations per profile (R13). |
| F-9 | **Pipelines recommended without a cost model.** | Each chain link adds a 30 to 80 minute serial step. Chains are what the operator experiences as "gated". | Lint measures critical path; cap chain depth; prefer fan-out after a skeleton. |
| F-10 | **Oracles unspecified per card.** `python -m pytest -q` as the allowed pattern invites full-suite oracles. | A full-suite oracle fails when another in-flight card's work is unmerged, coupling independent cards. | Per-card oracle runs only that card's tests; full suite only at goal or integration level (R9). |
| F-11 | **Replan triggers at zero READY** [PROPOSAL]. Batch-ahead does not change when the Overseer wakes. | By the time READY is 0, slots are already idle, and wakes are limited (6 per hour). | Low-water-mark trigger (R5). |
| F-12 | **Failure economics ignored.** More parallelism means more merge conflicts and gate failures. Conflicts classify as GATE_FAILED and move the task to REWORK [OBSERVED, v9]. REWORK tasks were never re-dispatched when I reviewed the code [OBSERVED v3, unchanged through v11; VERIFY]. | At 3x parallelism the number of dead tasks also rises about 3x. | R3 (REWORK sweeper). |
| F-13 | **Capacity not analysed.** N-2 admits provider limits but proposes no action. | Free-tier limits and logins change under you (for example OpenCode's free limits shifted recently and an expired Nous login took Hermes out). Fewer healthy profiles than slots means idle slots regardless of decomposition. | Capacity census and profile health fixes (R1). |
| F-14 | **Change surface understated.** Section 0 says one prompt, one field, one module; section 7 lists nine files including `api.py`, `cli.py`, `events.py`, `conductor.py`. | The operator should approve the real surface. | Use the surface table in section 6. |
| F-15 | **Open [VERIFY] items are prerequisites, not footnotes.** | Several decide whether the plan works (Dispatcher skip behaviour, void-dependency semantics). | Appendix D checklist, done in Phase 0. |
| F-16 | **Premises double as a scheduling gate** in the prompt ("harness refuses a card whose premises are false"). | A premise that depends on unmerged work bounces the card repeatedly. | Dependencies go in `depends_on`; premises are sanity checks only. |

---

## 5. Where "gated" actually comes from (the missing diagnosis)

A card can be non-runnable for any of these reasons. The census (Appendix A) attributes each non-running card, and each idle slot-minute, to exactly one.

| ID | Gate | What you see | Signal in the event log | Fix |
|---|---|---|---|---|
| G1 | **Dependency not done** (BLOCKED) | Long chains, "waiting for T-xxxx" | `depends_on` of an unfinished card | Wider DAG, skeleton then fan-out, chain-depth cap |
| G2 | **Dependency VOID (orphaned)** | Card stays BLOCKED forever after a void | `depends_on` points to a VOID card [VERIFY semantics] | Orphan report; re-point or void (R4) |
| G3 | **Write-scope overlap with an active lease** (D-L6) | READY card never claimed | Claim refusal with a scope conflict | Disjoint lanes; cross-wave lint; component-wise overlap (see G3a) |
| G3a | **False overlap from string-prefix matching** | `src/a/map.py` blocks `src/a/map_render.py` | Pairs that overlap only as strings [VERIFY: `scope_overlaps`] | Compare path components, not raw prefixes |
| G4 | **Dispatcher stops at the first conflicting READY** | Slots idle while disjoint READY cards exist | Idle slot-minutes with READY cards available | Look-ahead selection (R2) [VERIFY] |
| G5 | **Capacity**: profile disabled, cooled, auth expired, role mismatch, quota | Only 1 to 2 profiles ever lease | Profile state and failure classes per profile | Fix logins and quotas; add roles (R1) |
| G6 | **Stuck failed work**: REWORK, INFRA incident, gate failure | Cards sit in REWORK | REWORK older than N minutes | Sweeper (R3) |
| G7 | **Awaiting admission or wave release** | Cards PROPOSED | `task_admit` not yet issued | Auto-admit after lint passes |
| G8 | **Overseer supply**: wake budget (6 per hour), debounce, no low-water trigger | Idle with no READY, no BLOCKED | Time between `replan` wakes versus READY depth | Low-water wake (R5) |
| G9 | **Cap exhaustion**: `max_total_tasks` consumed by voided cards | Task creation refused | `TASK_CREATED` count versus the cap [VERIFY whether VOID counts] | Pre-creation validation (R6); policy change is class K |

**Decision tree for an idle slot (from the census):**

- Idle **and** a READY card has no scope conflict with active leases: Dispatcher or capacity problem (G4, G5). More decomposition will not help.
- Idle, READY exists but all of it conflicts with active leases: scope gate (G3, G3a).
- Idle, nothing READY, BLOCKED present: dependency gate (G1, G2).
- Idle, nothing READY, only PROPOSED: admission or wave gate (G7).
- Idle, nothing open: supply gate (G8).

---

## 6. Recommendations (improved plan)

Effort numbers are [SPECULATIVE]. "Class K" means a policy or constitution change; nothing below needs one unless stated.

### Phase 0: Diagnose (read-only, about half a day)

**R0. Gating census.** A read-only script run on a copy of the CFNA `.pm` and `agents.toml`; specification in Appendix A. It also answers the [VERIFY] list in Appendix D. Gate: operator reviews the report; Phase 1 and 2 scope is decided from it.

### Phase 1: Unblock (cheap, targeted by the census)

| ID | Change | Surface | Do it if the census shows |
|---|---|---|---|
| R1 | **Capacity fixes:** restore healthy logins (for example re-authenticate Hermes/Nous), classify "auth expired" as its own failure class (not a retryable infrastructure failure), ensure at least cap healthy slots exist for the `implement` role | `agents.toml`, `classify`, conductor | G5 |
| R2 | **Dispatcher look-ahead:** on a scope-conflicting candidate, skip it and try the next READY card | dispatcher or harness | G4 |
| R3 | **REWORK sweeper:** re-lease REWORK tasks up to `fix_rounds`, then queue to the operator; same for INFRA-incident tasks | conductor | G6 |
| R4 | **Orphan report:** when a card is voided, list dependents; show orphans in `pmk brief` and the Console; the Overseer may re-point | briefing, cli | G2 |
| R5 | **Low-water-mark replan:** wake the Overseer when (READY + unblocked PROPOSED) falls below the cap, within the existing wake budget and debounce | conductor | G8 |
| R-fix | **Component-wise `scope_overlaps`** if string-prefix matching is confirmed | `models.py` | G3a |

### Phase 2: Decompose properly

**R6. Wave manifest with pre-creation validation.** `pmk wave submit <file.toml>`: the Overseer writes one structured file (template in Appendix C) instead of up to 50 shell commands. The Kernel validates the whole manifest (lint v2) **atomically before any card is created**. On failure nothing is created and the violations are returned. On success it creates and admits all cards, assigns `wave_id`, and records `TASK_WAVE_SUBMITTED`. Benefits: no PROPOSED clutter, no void churn, no task-cap burn, deterministic duplicate rejection, and the wave quality no longer depends on a small model obeying a long prompt. `pmk task create` stays for single cards.

**R7. Architecture-first decomposition.** Parallelism is a property of the design, not of the cards. Before the first implementation wave, the Overseer (or a plan task) produces `docs/ARCH.md`: a module map (module, owned path subtree, interface file, depends on, goals served). Then:

- **Skeleton wave (short, depth 1):** one or two cards create package directories, interface stubs (signatures, dataclasses, `NotImplemented`) and contract tests, so consumers can start against stubs.
- **Fan-out:** one card per module or data file, each inside its own lane (directory subtree), depending only on the skeleton.
- **Integration cards:** one per goal, last, with the goal-level oracle.
- **Interleave goals** so the narrow phases of one goal (skeleton, integration) coincide with the wide phases of another and slots stay busy.
- **Hot-file elimination:** avoid shared files that many cards want to edit (`__init__.py`, central registries or constants, big data tables, `main`/wiring files, `tests/conftest.py`). Use auto-discovery or per-module registration, one data file per table or entity, one test file per card. Where a hot file is unavoidable, it has a single owner card and others depend on it.

[INFERRED] For a rules-heavy game such as CFNA, rule tables, scenario data and per-subsystem logic are natural fan-out material; confirm against the PDD.

**R8. Lint v2** (Appendix B): the proposal's checks A to G, with clarified semantics, plus H to O. It runs in two modes: manifest (pre-creation, atomic) and ledger (`pmk task lint --all`).

**R9. Oracle rule.** A card's oracle runs only that card's own test files (fast, independent). The full suite runs at integration-card level and as the merge gate. Measure the gate's duration: merges are sequential, so gate time times merges per hour must stay well under 60 minutes [VERIFY].

**R10. Prompt v2** (Appendix C): shorter than the proposal's Appendix A, template-driven, with the checks moved into the tool.

### Phase 3: Schedule smarter and tune

- **R11. Briefing digest and metrics** as in the proposal: per-goal created, done, voided and reworked; slot idle minutes; plus the census's idle-class percentages as a continuous metric.
- **R12. Critical-path priority:** among READY cards, prefer those on the longest remaining chain, after disjointness. Standard list scheduling.
- **R13. Calibrate budgets** from lease durations (CLAIMED to SUBMITTED): set `wall_min` so p90 for the assigned profile fits; split cards whose p90 exceeds the target.

### Real change surface

| Area | Files (indicative) | New or changed |
|---|---|---|
| Census | one script plus a report | new, read-only |
| Prompt | `src/fleet/overseer.py` | changed |
| Manifest and lint | `src/pmk/tasklint.py`, `src/pmk/cli.py` (`pmk wave submit`, `pmk task lint`), `src/pmk/api.py` | new and changed |
| Events | `src/pmk/events.py` (`TASK_WAVE_SUBMITTED`, optional `TASK_WAVE_LINTED`) | additive |
| Card schema | `src/pmk/models.py` (`wave_id`, `module`) | additive |
| Scheduling | dispatcher or harness, `src/fleet/conductor.py` | changed |
| Briefing | `src/pmk/briefing.py` | changed |
| Policy | none by default; `max_total_tasks` counting is class K if changed | flagged |

---

## 7. Phasing, acceptance tests and targets

| Phase | Gate to proceed | Targets [GUESS] |
|---|---|---|
| 0 Diagnose | Census reviewed by the operator; Appendix D answered | Every non-running card and idle slot-minute attributed to one gate |
| 1 Unblock | Tests F-D7, F-D9, F-D11, F-D12 green; census re-run | Idle-with-READY minutes close to 0 |
| 2 Decompose | F-D1 to F-D6 and F-D8, F-D10, F-D13 green on the fake CLI | New waves: manifest pass rate 100% by construction; void rate under 10% of new cards; READY depth at least the cap at 90% of dispatch ticks |
| 3 Tune | Real-wave demo (F-D6) | Average concurrent slots at least 5 of 6, if healthy capacity allows |

**New tests (extend the proposal's F-D series; fake CLI unless stated):**

| ID | Test |
|---|---|
| F-D7 | Hourglass DAG (skeleton, 8 fan-out cards, 2 integration): peak concurrency equals min(cap, 8) and idle-with-READY minutes are 0 |
| F-D8 | Cross-wave overlap: a new wave that overlaps an existing READY or BLOCKED card is rejected with the exact pair |
| F-D9 | Void a card with dependents: orphan report lists them; the dependents are never silently stuck |
| F-D10 | Manifest atomicity: one invalid card means zero `TASK_CREATED` events |
| F-D11 | Look-ahead: the top-priority READY card conflicts with an active lease; the next disjoint READY card is claimed |
| F-D12 | Low-water wake: READY depth drops below the cap, an Overseer wake is requested once (debounced), not per tick |
| F-D13 | Duplicate card (same goal and normalised write set as a non-VOID card) is rejected |

---

## 8. Decisions needed from the operator

1. **Run the Phase 0 census first?** Recommended yes. It is read-only and tells us which of G1 to G9 is actually costing you slots.
2. **Manifest creation (R6) versus keeping `pmk task create` plus a post-hoc lint.** Recommended manifest: it prevents void churn and task-cap burn.
3. **Cap.** Keep 6 (the CFNA PDD constraint) for now. Revisit only after Phase 3 metrics show healthy capacity beyond 6; merge gate throughput, per-model quotas and hot files all tighten as the cap rises.
4. **Authorise Kernel and fleet changes** for R2, R3, R5, R6 and the scheduling work. These are not class K, but they change Kernel or conductor code and follow your usual acceptance process.
5. **`max_total_tasks` counting voided cards** (if confirmed): leave as is and rely on pre-creation validation, or change it (class K, two-key).

---

## 9. Risks

| # | Risk | Mitigation |
|---|---|---|
| K-1 | More, smaller cards mean more merges and conflicts; each conflict kills a task unless REWORK is re-dispatched | R3 before scaling; measure conflicts (`MERGE_REFUSED`, `GATE_FAILED`) |
| K-2 | Provider limits cap useful parallelism regardless of decomposition | Capacity census; spread across independent models |
| K-3 | The lint gives false confidence: declared scopes may differ from actual writes | Keep submit-time `scope_check` and write-scope-only merge unchanged |
| K-4 | A free-tier Overseer writes poor manifests | Template and tool-side validation; keep waves per goal (about 12 to 20 cards); lint errors returned in plain text |
| K-5 | Skeleton and integration phases are narrow and serial | Interleave goals; keep skeleton cards small |
| K-6 | Merge gate time becomes the bottleneck | Measure gate duration in Phase 0; scope per-card oracles (R9) |
| K-7 | Stale worktrees: in-flight cards do not see newly merged interfaces | Contracts frozen in the skeleton; premises check the contract file exists |

---

## 10. Amendments to the proposal (section by section)

| Proposal section | Amendment |
|---|---|
| 1, 3 | Present the "upstream supply" diagnosis as a hypothesis to test, not a finding |
| 5 (root causes) | Add C-6 capacity, C-7 stuck failed work, C-8 orphaned dependencies, C-9 Dispatcher conflict handling, C-10 zero-READY wake trigger |
| 6.1 | Replace the four-step contract with Appendix C; add architecture-first (R7) and the oracle rule (R9) |
| 6.2 | Replace lint A to G with Appendix B; run pre-creation in manifest mode |
| 6.3 | `wave_id` assigned by the Kernel; add `module` to the card |
| 6.5 to 6.6 | Add idle-slot classification as the headline metric |
| 7 | Replace the implementation table with the section 6 surface table; state the real scope |
| 8, 9 | Add F-D7 to F-D13; reorder the cut order: Phase 0 and Phase 1 before any prompt change |
| 10 (apply now) | Apply nothing until the census is reviewed, except fixes that are independent of it (R1 login and capacity repair) |
| 12 | Promote the [VERIFY] items in Appendix D to Phase 0 prerequisites |

---

## Appendix A: Phase 0 census specification (read-only)

**Rules:** run on a **copy** of the CFNA project's `.pm` directory and `agents.toml`. Do not write to the live tree. No git add, commit or reset. Do not delete or move files. Output a single markdown report. Label anything that cannot be determined as unknown.

**Method:** replay the event stream with the Kernel's reducer (or an equivalent fold) to reconstruct ledger state at each 5-minute bucket from the first claim to now.

**Report sections:**

1. **Ledger over time:** counts per state per bucket (PROPOSED, BLOCKED, READY, LEASED, SUBMITTED/VERIFYING/INTEGRATING, REWORK, DONE, VOID).
2. **Slot usage:** active leases per bucket versus the cap; total idle slot-minutes.
3. **Idle classification per bucket** (minutes and percent of idle): A idle with a READY card that does not conflict with active leases; B idle, READY exists but all conflict; C idle, no READY, BLOCKED present; D idle, no READY, only PROPOSED; E idle, nothing open.
4. **Non-running cards, one primary reason each:** depends on an unfinished card (list), depends on a VOID card (orphan), scope conflict with named task, premise refused, REWORK older than 30 minutes, INFRA incident, awaiting admission.
5. **Capacity per profile:** `max_concurrent`, roles, enabled or cooled state and reason, leases started, failures by class, median and p90 minutes from claim to submit.
6. **DAG statistics of the open ledger:** levels, width per level, critical path in minutes (sum of `wall_min`), total work, and the completion lower bound max(critical path, total work / cap).
7. **Cap usage:** `TASK_CREATED` count versus `max_total_tasks`; voided count; void reasons if recorded.
8. **Scope hygiene:** number of cards whose write scope is a directory; pairs of non-terminal cards with overlapping scopes (flag cross-wave pairs); pairs that overlap only as raw string prefixes (G3a candidates).
9. **Appendix D answers**, each with file and line evidence.

---

## Appendix B: lint v2 specification

Two modes: **manifest** (pre-creation, atomic, used by `pmk wave submit`) and **ledger** (`pmk task lint --all`). Each violation is an error or a warning and names the exact cards, paths or goals involved.

| ID | Check | Severity |
|---|---|---|
| A | Admission: goal_ref, non-empty write scope, at least one oracle, budget (reuse `admission_errors`) | error |
| B | Pairwise disjointness within the wave (component-wise `scope_overlaps`) | error |
| I | Disjointness against **all non-terminal cards** in the ledger (READY, BLOCKED, PROPOSED, REWORK, LEASED, SUBMITTED), not only active ones | error |
| C | Coverage is ledger-wide; the wave is checked for the goals it introduces; every goal has at least one non-VOID card | error |
| D | Dependencies: acyclic, every id or key exists, no self-dependency | error |
| K | Orphans: no `depends_on` pointing at a VOID or missing card | error |
| H | **Parallelism:** ready-front width at release at least min(cap, number of cards); longest chain at most 4 cards or about 150 minutes [GUESS]; report critical path and the completion lower bound | error if width is below the minimum; otherwise warning |
| J | Duplicates: same goal and normalised write set as a non-VOID card is rejected; similar titles warn | error / warning |
| L | Lane: every write path lies inside the owning module's paths in `docs/ARCH.md` | error |
| M | Oracle scope: oracle references only the card's own test paths; a bare `pytest -q` is allowed only on integration cards | warning |
| N | Hot files (`pyproject.toml`, `README.md`, `.gitignore`, `tests/conftest.py`, package `__init__.py`, registries): allowed only for a declared sole owner | error |
| O | Budget: `wall_min` versus observed p90 for the intended profile; write-path count within bounds (defaults 20 to 45 min and at most 3 paths until calibrated) | warning |
| F, G | Oracle syntax and premises are structural only; premises are sanity checks, not scheduling | warning |

---

## Appendix C: prompt v2 and manifest template

Replace the proposal's `needs-decomposition` guidance and Decomposition Contract with the following. The rest of `OVERSEER_PROMPT` is unchanged.

```text
needs-decomposition:
  1. Read docs/ARCH.md (the module map) and docs/PDD.md. If ARCH.md is missing, your only task this wake is
     to create a plan card that writes it.
  2. Write ONE wave manifest (template below) covering the next goal(s). Aim for 12 to 20 cards.
  3. Run `pmk wave submit <file>`. If it reports violations, fix exactly those and resubmit. Nothing is
     created until the manifest passes. Do not create cards one by one unless submitting a single card.
  4. Stop when the briefing has nothing for you.

Rules the tool checks (you do not need to memorise them):
  - Each card lives in one module's lane and writes only paths inside it.
  - Many small cards that can run at the same time beat a few big ones; chains are for real dependencies only.
  - After a skeleton card, fan out: one card per module or data file, each depending only on the skeleton.
  - Each card's oracle runs only that card's own tests.
  - Do not set wave_id; the Kernel assigns it.
```

Manifest template (illustrative names; not a recommendation for CFNA's actual modules):

```toml
[wave]
note = "fan-out for goal G-002"

[[card]]
key        = "skeleton-combat"
title      = "Combat package skeleton and interface stubs"
goal_ref   = ["G-002"]
module     = "combat"
scope_write = ["src/pkg/combat/"]
scope_read  = ["docs/ARCH.md"]
depends_on  = []
wall_min    = 20
oracle      = ["python -m pytest -q tests/combat/test_contract.py"]
premises    = ["python -c \"import pathlib; assert pathlib.Path('docs/ARCH.md').exists()\""]

[[card]]
key        = "combat-crt-data"
title      = "Combat results table data file"
goal_ref   = ["G-002"]
module     = "combat"
scope_write = ["src/pkg/combat/crt_data.py", "tests/combat/test_crt_data.py"]
scope_read  = ["src/pkg/combat/api.py"]
depends_on  = ["skeleton-combat"]
wall_min    = 30
oracle      = ["python -m pytest -q tests/combat/test_crt_data.py"]
premises    = ["python -c \"import pathlib; assert pathlib.Path('src/pkg/combat/api.py').exists()\""]
```

---

## Appendix D: [VERIFY] checklist (answer in Phase 0, with file and line)

1. When `claim` refuses a READY card for a scope conflict, does the Dispatcher skip to the next READY card or stop? (`src/pmk/api.py` claim; the Dispatcher in `src/fleet/`)
2. `scope_overlaps` (`src/pmk/models.py`): component-wise or raw string prefix? Does it support globs?
3. Does a dependency on a VOID card count as satisfied or as blocking?
4. Are REWORK tasks re-leased by anything today? How is `fix_rounds` used?
5. Do VOID cards count toward `max_total_tasks`?
6. Who moves PROPOSED to READY today (Conductor, Overseer, operator)?
7. Does the VOID event carry a reason? Which events record merge refusals? (`MERGE_REFUSED` and the GATE_FAILED class exist as of v9 [OBSERVED].)
8. Exact condition for the `replan` wake, and where the 6 wakes per hour budget and debounce are enforced.
9. Cap naming: the proposal cites `fleet_cap = 6`; the `agents.toml` I reviewed has `max_total_agents`. Which key is enforced, and where?
10. Do leases carry timestamps from which claim-to-submit durations can be computed?
11. Does the harness really refuse a card whose premises are false?
12. Gate duration (the merge gate command) and how many merges per hour it can sustain.
