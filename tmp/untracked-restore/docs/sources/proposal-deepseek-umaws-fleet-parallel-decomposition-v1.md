---
document:
  title: "Project Proposal: Parallel Decomposition for the UMAWS Fleet Overseer — more LLM workers in parallel through thorough, disjoint-scope decomposition"
  status: "Proposal — candidate tier; advisory; no authority"
  version: "1.0.0"
provenance:
  author_llm: {name: "deepseek", version: "deepseek-v4-flash-free (DeepSeek V4 Flash, free tier)"}
  assessor_llm: []
  last_modified_by_llm: {name: "deepseek", version: "deepseek-v4-flash-free (DeepSeek V4 Flash, free tier)"}
  created_date: "2026-11-02"
  last_modified_date: "2026-11-02"
audience:
  primary: "The human operator (decision record)"
  secondary: "Implementing LLM(s) (executable brief)"
  tertiary: "The live Overseer (OpenCode) and fleet workers"
source_documents:
  - "docs/sources/fleet-launcher-proposal.md (amendment A1; the Fleet specification)"
  - "src/fleet/overseer.py (OVERSEER_PROMPT; the current decomposition guidance)"
  - "src/pmk/models.py (TaskCard, admission_errors, scope_overlaps)"
  - "src/pmk/api.py (claim, _scope_conflict)"
  - "src/fleet/harness.py (scope_check)"
  - "src/fleet/merge.py (write-scope-only merge)"
  - "src/pmk/policy.py (recovery caps, class K policy)"
  - "src/pmk/cli.py (pmk command surface)"
  - "docs/PDD.md and HANDOFF.md (CFNA live-run evidence)"
evidence_basis: "Repo files read in full during this session; the CFNA live-run evidence in HANDOFF.md (2026-11-01) and docs/PDD.md; the operator's stated answers to the interview questions in this conversation. Nothing here has been run; every number is tagged."
epistemic_status: "Tags: [STATED] the operator said it; [OBSERVED] read from the repo; [SPEC] specified by the fleet-launcher proposal; [INFERRED] my reasoning; [GUESS] needs measurement; [VERIFY] check before relying on it."
authority_statement: "Candidate tier: this document has no authority. It recommends changes; nothing takes effect until the operator decides and the appropriate authorisation or gate is crossed. Class K items (policy constants) are flagged as such and need a two-key event."
---

# UMAWS Fleet: Parallel Decomposition for the Overseer

## 0. How to read and use this document

1. This is a **candidate-tier proposal** (no authority). It assesses whether the Overseer can be made to
   decompose more thoroughly so more LLMs work simultaneously, and how to do it. If adopted, the
   implementing LLM follows sections 6–9 and the appendices; the operator reads sections 1–2, 4 and 10.
2. Read `docs/sources/fleet-launcher-proposal.md` (amendment A1) first if you have not: this proposal does
   not restate the Fleet specification; it changes nothing there except where explicitly noted in section 7.
3. Where a number or behaviour is not yet measured it is tagged `[GUESS]` or `[VERIFY]` per the repo's
   epistemic rules. Do not implement a `[VERIFY]` item as if it were measured.
4. Nothing here requires a Kernel rewrite. The change surface is: one prompt, one additive task-card field,
   one new lint module, one briefing extension, and tests. Class K flags appear only in section 6.7.

---

## 1. Executive summary

**The ask.** The operator wants the UMAWS Fleet Overseer to decompose projects more thoroughly so that more
LLM workers work simultaneously on a project.

**The finding.** The Fleet is **already built to run many workers in parallel**, and that machinery is
proven: the Dispatcher fills slots from READY cards; claim-time refuses write-scope overlap (D-L6,
`src/pmk/api.py:_scope_conflict`); submit-time rejects out-of-scope writes (`src/fleet/harness.py:scope_check`);
merges commit only declared write-scope paths (`src/fleet/merge.py`). Test F7 ran 100 fake workers; gate G5
ran 6 real workers to DONE. **The bottleneck is upstream of the Dispatcher**: the Overseer produces too few
READY tasks with disjoint write scopes, so slots idle. The decomposition guidance is one sentence — *"Keep
write scopes disjoint where tasks can run in parallel. Prefer many small tasks."* (`src/fleet/overseer.py`)
— with no method, no validation and no feedback. The CFNA live run is the evidence: 130 cards created, 125
voided (many duplicate/doomed), and at handoff 2 DONE / 3 LEASED / **0 READY** (HANDOFF.md 2026-11-01).

**The recommendation.** Make decomposition a **verified production step**, not a prompt wish:
(1) replace the one-sentence guidance with a concrete **Decomposition Contract** (coverage matrix first,
own the paths you write, split by concern and size to the slot, batch-ahead); (2) add a **wave lint**
(`pmk task lint`) that machine-checks every wave for disjoint write scopes, goal coverage, dependency
acyclicity and budget, and gates release to READY — applying the project's own "oracles decide" rule (I5)
to decomposition itself; (3) give the Overseer **feedback** (per-goal created/done/voided digest and slot
idle minutes in the briefing) so later waves self-correct; (4) measure **slot utilisation** so the gain is
provable. This is a small, reversible, testable change: prompt text, one additive card field, one new
command, briefing text. No Kernel rewrite, no relaxation of D-L6, no change to the merge machinery.

**The honest ceiling.** With `fleet_cap = 6` and the CFNA PDD constraint *"Max six concurrent workers"`,
peak concurrency **cannot exceed 6**. Raising the cap is a policy decision the operator placed out of
scope; this proposal's realistic target is **sustained concurrency near 6 (average ≥ 5 of 6 [GUESS])**
instead of today's 0–2, which roughly triples wall-clock throughput on free-tier models. "More LLMs" beyond
6 is a separate, later decision.

---

## 2. The request and what "great" means here

From the operator's interview answers in this session:

| Question | Answer |
|---|---|
| Bottleneck | All four: too few READY tasks; free models slow (parallelism is the only lever); write-scope conflicts serialize work; decomposition quality wastes capacity |
| Target granularity | The proposal recommends it from evidence |
| Peak concurrency | No fixed number — "as much as safely possible", derived from merge-risk and slot-cost analysis |
| Audience | Implementing LLM + operator (executive summary + executable brief) |
| Status | Candidate tier, no authority |
| Implementation scope | Overseer prompt & guidance; task-creation machinery / D-L6; policy caps; new tooling |
| Void rate | Parallelism first; voids acceptable (quality is not first-class) |
| D-L6 | Keep strict disjoint write scopes |
| fleet_cap | Out of scope — utilisation only (keep 6) |
| Paid models | Out of scope — free tier only |
| Acceptance | Yes — F-style tests + a demo metric |
| Proposal success criteria | Decisive recommendation with cuts; measurable targets + verification; honest about feasibility limits; implementable with no further questions |
| Save location | Both repo root and docs/sources/ |
| Timeline | Immediately, mid-CFNA (include an apply-now section) |

**What "great" looks like here:** a project run in which every one of the 6 slots is busy almost all the
time (average concurrent slots ≥ 5 of 6 [GUESS]), a deep queue of disjoint-scope READY cards always exists
after the first wave, waves are released only after the lint passes, and the change is provable via metrics
and F-D tests — without a single change to D-L6, the merge queue, or the cap.

---

## 3. Is it possible? Yes — the mechanism is proven

Everything needed to run many LLMs in parallel already exists and is enforced end to end:

1. **Parallel dispatch exists.** The Dispatcher fills slots from READY cards in priority order
   (fleet-launcher §7.4). F7 passed with 100 concurrent fake workers; G5 passed with 6 real workers, all
   DONE, close-check green (STATE.md).
2. **Safe parallelism is enforced, not hoped for.**
   - Claim-time: `claim()` refuses a task whose write scope overlaps any task in an active state
     (D-L6; `src/pmk/api.py:433-450,479-483`).
   - Submit-time: `scope_check` compares actual worktree changes to the declared write scope and flags
     out-of-scope writes (`src/fleet/harness.py:148-170`).
   - Merge-time: only declared write-scope paths are committed (`src/fleet/merge.py`).
3. **Task cards are structured for parallel decomposition.** `TaskCard` already has `scope.write`,
   `scope.read`, `depends_on`, `premises`, `budget`, `acceptance.oracles`, `goal_ref`
   (`src/pmk/models.py:65-176`). Admission requires a goal ref, a non-empty write scope, ≥1 oracle and a
   budget (`admission_errors`, models.py:91-107).
4. **Policy caps bound the risk** (`src/pmk/policy.py:52-53`): `max_tasks_created_per_wake = 50`,
   `max_total_tasks = 500`.

Therefore the question is not *"can the system run many workers at once?"* — it can and has — but *"can the
Overseer produce enough READY, disjoint-scope tasks to keep those workers busy?"*. That is a decomposition
**supply** problem, and it is solvable with prompt + lint + feedback, not with new parallel machinery.

**Why it is not happening today.** (a) The guidance is one sentence with no method for producing disjoint
scopes, no size rule, no coverage check. (b) Nothing validates a wave before release — the enforcement net
only fires at claim/submit/merge, i.e. *after* a bad wave occupies the Overseer's scarce wakes (6/hour,
debounced). (c) No feedback: the Overseer never learns that its cards were voided, overlapped, or left
slots idle; `replan` only fires when there are zero READY tasks. (d) The CFNA data shows the cost: 125 of
130 cards voided — largely duplicate/doomed cards cleaned up in batch (HANDOFF.md Q-062/Q-064; so 96% is an
upper-bound signal, not a precise quality metric), and 0 READY at handoff, which means slots sat idle.

---

## 4. Is it feasible? Yes — with honest limits

### 4.1 The ceiling math (why "no fixed number" resolves to 6)

- Peak concurrency is hard-capped by `fleet_cap = 6` (`agents.toml`) and by the CFNA PDD constraint
  "Max six concurrent workers". **This proposal cannot raise concurrency above 6.** It can raise *sustained*
  concurrency toward 6.
- Free-tier models take roughly 30–80 min per task (HANDOFF.md). Throughput ≈
  `slots × (1 / avg task time) × utilisation`. Finer tasks cut `avg task time` and raise `utilisation`
  (smaller tasks fill gaps), but add per-task overhead (worktree create, spawn, oracle, evidence, merge)
  and more merges (more divergence/conflict exposure — `src/fleet/merge.py` already needed a `--no-ff`
  fallback after divergence).
- Conclusion: an **optimal granularity** exists where marginal overhead ≈ marginal parallelism gain. The
  proposal sets a starting budget `[GUESS]` and a spike (S-D1) to calibrate it; it does not pretend a
  precise optimum is known.

### 4.2 What is genuinely hard

Not the code — the **specification quality**. Disjoint-scope parallelism decays into merge and coverage
failures exactly when tasks claim independence they do not have (shared files, unstated contracts, hidden
dependencies). The mitigation is to move validation *before* release (the wave lint), keep the existing
after-the-fact net (scope_check, write-scope-only merge), and give the Overseer feedback. This is why the
proposal is lint-first rather than "just prompt harder".

### 4.3 What is NOT possible / out of scope (honest)

| # | Item | Why |
|---|---|---|
| N-1 | More than 6 concurrent workers | `fleet_cap = 6` + CFNA PDD cap; raising them is a policy decision the operator put out of scope. Flagged as the true gate on "more LLMs". |
| N-2 | Beating free-model rate limits with more tasks | Throughput per model is capped by provider quotas. More tasks only help if distinct profiles/models exist and are cooled correctly. |
| N-3 | Zero merge conflicts at high task counts | Impossible in principle; disjoint scopes reduce them, but shared root files and branch divergence remain. Measure, don't assume. |
| N-4 | Faster wall-clock per task | Not this proposal's goal; it raises *parallel* throughput, not single-task speed. |
| N-5 | Making void rate a release gate | The operator said voids are acceptable; quality signals serve parallelism only (fewer doomed tasks = fewer wasted slots). |

---

## 5. Root-cause analysis

| # | Cause | Evidence | Consequence |
|---|---|---|---|
| C-1 | Decomposition guidance is one sentence | `OVERSEER_PROMPT` in `src/fleet/overseer.py` | No method for disjoint scopes, no size rule, no coverage check, no dedup discipline |
| C-2 | No validation before release | No lint/oracle on waves; enforcement only at claim/submit/merge | Bad waves consume the Overseer's 6-wake/hour budget; violations surface late as rework or voids |
| C-3 | No feedback loop | `pmk brief` shows task state but no per-goal created/done/voided digest or slot idle minutes (`src/pmk/briefing.py`) | The Overseer cannot self-correct granularity or dedup across waves |
| C-4 | No slot-utilisation metric | Metrics exist for F7 drill but not as a continuous project metric `[VERIFY]` | The improvement cannot be proven or tuned |
| C-5 | Shared root files (pyproject.toml, README, docs/PDD.md, tests/) collide | `merge.py` divergence fallback in HANDOFF.md | Even disjoint scopes hit shared-file contention; guidance must make these read-only by default |

None of these requires changing the enforcement machinery; all five are prompt/validation/feedback gaps.

---

## 6. Recommended design

### 6.1 Decomposition Contract (the prompt rewrite)

Replace the single `needs-decomposition` sentence with a four-step contract (full replacement text in
Appendix A). The steps:

1. **Coverage matrix first.** For every PDD goal G-i, list the cards that satisfy it; every card carries the
   goal(s) in `goal_ref`. The lint rejects a wave that leaves a goal uncovered.
2. **Own the paths you write.** Every card's `scope.write` is concrete repo-relative paths (files, not vague
   directories) that *this card alone* modifies; `scope.read` is everything else the worker may read. No two
   cards in a wave write the same or prefix-overlapping paths. Shared root files are read-only by default; a
   card that must change one declares it and becomes its sole owner.
3. **Split by concern, size to the slot.** One coherent change per card: `budget.wall_min` 20–45
   `[GUESS]`, ≤ 3 write paths `[GUESS]`, one `goal_ref`. Larger goals decompose into a **pipeline** linked by
   `depends_on`, **interface-first**: contract-defining cards (APIs, schemas, data formats) come first;
   consumers put the contract file in `scope.read` and check it exists in `premises`.
4. **Batch-ahead.** Create the whole wave in one wake (up to `max_tasks_created_per_wake`), not dribbles, so
   a deep queue of READY disjoint cards exists and the Dispatcher never waits on the Overseer.

Plus: **premises carry the load** (each card's premises are Windows-safe checks the worker runs before
starting; the harness refuses a false premise), and **feedback is used** (the briefing digest drives dedup
and granularity in later waves).

### 6.2 Wave lint — the decomposition oracle (new tooling)

`pmk task lint [--wave <id> | --all]` (`src/pmk/tasklint.py`, new; command in `src/pmk/cli.py`). Checks
(full spec in Appendix B):

- **A admission**: goal_ref, non-empty `scope.write`, ≥1 oracle, budget (reuse `TaskCard.admission_errors`).
- **B disjointness**: pairwise `scope_overlaps(write_i, write_j)` empty within the wave and against
  LEASED/SUBMITTED tasks (reuse `scope_overlaps` + the `_scope_conflict` logic).
- **C coverage**: every PDD goal has ≥1 card (parse `docs/PDD.md` via `src/pmk/pdd.py`).
- **D dependencies**: acyclic; every `depends_on` id exists; no self-dependency.
- **E budget**: `wall_min` within bounds; write-path count within bounds.
- **F oracle sanity**: each oracle is non-empty and Windows-safe.
- **G premises**: non-empty; structural checkability.

**Gate**: a wave is not released to READY until the lint passes. On failure the Conductor records
`TASK_WAVE_LINTED{passed:false, violations:[...]}` and enqueues a queue item (recommended option: "fix the
listed cards"; safe default: leave the wave PROPOSED, do not release). This is the project's own
"oracles decide" rule (I5) applied to decomposition.

### 6.3 Wave grouping (additive schema)

Add `wave_id: str = ""` to `TaskCard` (`src/pmk/models.py`). Additive and backward compatible (`from_obj`
default). Groups cards for lint, release and review; no behaviour change for existing cards.

### 6.4 Shared-file discipline

No new enforcement code is required — D-L6 already serialises any path listed in two write scopes. The gap
is guidance: make shared root files read-only by default and single-owner when written (6.1 step 2), and
prove it with test F-D3. `[INFERRED]` — see `scope_overlaps` semantics in `src/pmk/models.py:198-209`.

### 6.5 Feedback signals

Extend `pmk brief --role overseer` (`src/pmk/briefing.py`) with a per-goal digest — created / done / voided
/ reworked counts and slot idle minutes since the last wake. Informational only; lets the Overseer dedup
and re-granularise. Serves parallelism by reducing doomed tasks without making quality a gate.

### 6.6 Metrics and measurable targets

Record/derive: slots-in-use over time, READY+PROPOSED depth over time, slot idle minutes, tasks per goal,
void rate (requires a `void_reason` on VOID events — `[VERIFY]` whether one exists today), merge-conflict
count (requires a `MERGE_CONFLICT` event — `[VERIFY]` today; `src/fleet/merge.py` records none found in
this session), average task wall time (leases carry timestamps `[VERIFY]`).

Targets (all `[GUESS]` until S-D1/F-D6):

| Metric | Baseline (CFNA) | Target |
|---|---|---|
| Average concurrent slots | 0–2 observed at handoff | ≥ 5 of 6 |
| READY+PROPOSED depth when a slot is free | 0 | ≥ 12 (2×cap) |
| Wave lint pass | n/a | 100% of released waves |
| Void rate trend | high (96% gross, partly cleanup artifact) | decreasing across waves |

### 6.7 Policy changes (class K)

- Keep `max_tasks_created_per_wake = 50` and `max_total_tasks = 500` unless S-D1/F-D6 measurements justify a
  change. Raising them is a **class K two-key change** (recovery constants in `.pm/policy.toml`;
  `src/pmk/policy.py:52-53`, pinned by I8′). The proposal's default is: keep them.
- `fleet_cap = 6` unchanged (out of scope, N-1).
- No other policy changes. Prompt text, the additive `wave_id` field, the new lint command and the new
  `TASK_WAVE_LINTED` event type are **not** class K.

---

## 7. Implementation plan

Order of work follows the cut order (§9). Effort is `[SPECULATIVE]`.

| # | File | Change | Class K | Tests |
|---|---|---|---|---|
| 1 | `src/fleet/overseer.py` | Replace the `needs-decomposition` guidance with the Decomposition Contract (Appendix A) | No | — |
| 2 | `src/pmk/models.py` | Add `wave_id` field to `TaskCard` (additive) | No | unit |
| 3 | `src/pmk/tasklint.py` (new) | Lint checks A–G; reuse `scope_overlaps`, `admission_errors`, `pdd` parse | No | `tests/fleet/test_tasklint.py` |
| 4 | `src/pmk/api.py` | `task_lint(...)` and wave-release wrapper (lint → admit to READY) | No | unit |
| 5 | `src/pmk/cli.py` | `pmk task lint`, `pmk fleet idle` | No | CLI smoke |
| 6 | `src/pmk/briefing.py` | Per-goal digest + slot idle minutes | No | unit |
| 7 | `src/pmk/events.py` | Add `TASK_WAVE_LINTED` event type (additive) | No | unit |
| 8 | `src/fleet/conductor.py` | On wave creation: run lint; failure → queue item, wave stays PROPOSED | No | F-D1..F-D5 |
| 9 | tests | New F-D series + extend F10 | No | see §8 |
| — | `src/pmk/api.py` claim, `src/fleet/harness.py` scope_check, `src/fleet/merge.py` | **No change** — the enforcement net stays exactly as built | — | — |

The prompt change takes effect on the Overseer's **next wake**: `OVERSEER_PROMPT` is read per
`OverseerRunner._start` (`src/fleet/overseer.py:211`), so no restart beyond the next spawn. `[OBSERVED]`.

---

## 8. Acceptance tests (F-D series)

| ID | Test | Needs real LLM? | Tier |
|---|---|---|---|
| F-D1 | Seed a 3-goal PDD; create a canned wave of 12 cards with disjoint scopes + deps; `pmk task lint` passes; fake-CLI Dispatcher leases all 12 (capped by slots) with zero `scope_overlap` errors; READY depth ≥ 6 maintained until exhaustion | No | A |
| F-D2 | Two cards in a wave with overlapping write paths → lint fails listing the exact pairs (wave-level extension of F10, pre-claim) | No | A |
| F-D3 | Two cards both listing a shared path (e.g. `pyproject.toml`) → lint fails unless one is sole owner and the other depends on it; shared-path serialisation holds | No | B |
| F-D4 | Coverage matrix: a wave missing a goal → lint fails "no card covers G-00X"; a card with no `goal_ref` → admission error | No | A |
| F-D5 | Dependency chain A→B→C; A DONE; B and C READY; claim of C refused until B DONE (extends existing claim rule to wave ordering) | No | A |
| F-D6 | Real demo: run the next CFNA wave (or a small toy project) with the new contract; measure average concurrent slots (≥ 5 of 6), READY depth (≥ 6 after first wave), void-rate trend vs. CFNA baseline | Yes | C |

Reused: F1 (one-click run), F7 (scale), F10 (scope overlap). S-D1 (new spike): measure per-task overhead
(worktree create + spawn + oracle + merge) on the fake CLI at 6 and 12 concurrent, to calibrate the task
budget and the READY buffer depth; reuses the S-W1/S-L1 method.

---

## 9. Cut order (tiers)

| Tier | Contents | Gate |
|---|---|---|
| **A. Verified decomposition (80/20)** | Items 1–8 above minus F-D3; lint checks A–D; briefing digest; tests F-D1, F-D2, F-D4, F-D5 | Green on F-D1/F-D2/F-D4/F-D5 with the fake CLI; lint gates every wave |
| **B. Measured** | F-D3 (shared files), metrics (slot idle, READY depth, void reason `[VERIFY]`, merge-conflict event), S-D1 spike, `pmk fleet idle`; policy-cap change *only if* S-D1 justifies it (class K) | S-D1 numbers recorded; metrics live on the Console |
| **C. Tuned** | F-D6 real demo; READY-buffer tuning; optional auto coverage-matrix generation | Demo green on a real wave |

**Never cut:** the lint gate (it is the whole point), D-L6 (unchanged), F-D1/F-D2 (the parallelism proof),
the briefing digest (feedback), the honest report of measured vs. `[GUESS]`.

---

## 10. Apply now — mid-CFNA

The current CFNA run is RUNNING with 3 active leases and 0 READY (HANDOFF.md). These changes can be applied
without disturbing running work:

1. **Apply the prompt rewrite (item 1) now.** It takes effect on the Overseer's next wake (`[OBSERVED]`,
   §7). The next natural wake is `replan` (0 READY), `review` (when T-0118/T-0119/T-0130 submit), or
   `periodic`.
2. **Apply the lint (items 2–5, 8) now** so the next wave is gated. This requires an implementer session
   and a `pytest` green; it does not touch running leases.
3. **Do not** raise caps, change `fleet_cap`, or alter policy mid-run (class K; out of scope).
4. **Keep the CFNA PDD constraint** "Max six concurrent workers" and the existing oracle discipline.
5. Expected first-wave effect: a deep queue of disjoint READY cards so the 3 free slots (of 6) fill
   continuously instead of idling between slow free-model tasks.

---

## 11. Risks

| # | Risk | Mitigation |
|---|---|---|
| R-D1 | Finer tasks → more merges → more divergence/conflicts (merge.py already hit `--ff-only` divergence) | Disjoint scopes (unchanged D-L6), shared-file rules, measure merge-conflict rate, cut order keeps merge behaviour untouched |
| R-D2 | Lint false-negatives (declared scopes ≠ actual writes) | The lint is a cheap pre-filter; the real net remains submit-time `scope_check` + write-scope-only merge |
| R-D3 | Larger waves exceed the Overseer's context/output limits (6 wakes/h, 50 cards/wake) | Batch-ahead within caps; per-goal waves if needed; lint errors return as queue items, not silent drops |
| R-D4 | Free-model throughput stalls F-D6 (the real demo) | Mark `[VERIFY]`; mechanism tests use the fake CLI; demo is Tier C and optional |
| R-D5 | More cards → more void-cleanup load | Accepted by the operator (parallelism first); the briefing digest lets the Overseer dedup in later waves |
| R-D6 | The lint becomes a bottleneck or false gate | Keep checks structural (no semantic analysis); failures return exact violations; operator can inspect the queue item |

---

## 12. Open questions

| # | Question | Default (until measured) |
|---|---|---|
| Q-1 | Optimal task budget (wall_min, changed lines, write paths) | `[GUESS]` 20–45 min, ≤ 3 write paths; calibrated by S-D1 |
| Q-2 | READY buffer depth target | `[GUESS]` ≥ 2×cap (12); calibrated by S-D1/F-D6 |
| Q-3 | Does the VOID event record a reason today? | `[VERIFY]`; if not, add `void_reason` for the void-rate metric |
| Q-4 | Does a `MERGE_CONFLICT` event exist? | `[VERIFY]`; none found in this session |
| Q-5 | Can one wake reliably emit 50 cards? | `[VERIFY]` on the live Overseer; else per-goal waves |
| Q-6 | Operator's void-rate appetite (target only, never a gate) | Voids acceptable; a decreasing trend is the target |

---

## 13. Sources

- `docs/sources/fleet-launcher-proposal.md` (amendment A1; Fleet spec, §7.4 selection, §12.D prompt, §13 tests)
- `src/fleet/overseer.py` (OVERSEER_PROMPT, wake bounds)
- `src/pmk/models.py` (TaskCard, admission_errors, scope_overlaps)
- `src/pmk/api.py` (claim, _scope_conflict)
- `src/fleet/harness.py` (scope_check)
- `src/fleet/merge.py` (write-scope-only merge, divergence fallback)
- `src/pmk/policy.py` (recovery caps; class K)
- `src/pmk/briefing.py`, `src/pmk/cli.py`, `src/pmk/pdd.py`, `src/pmk/events.py`
- `docs/PDD.md` (CFNA goals, constraint "Max six concurrent workers")
- `HANDOFF.md` (2026-11-01; CFNA live state, void counts, merge divergence fix)
- `pilot/STATE.md` (F7, G5, S-W1 evidence)

---

## Appendix A — replacement OVERSEER_PROMPT (full text)

Replace the module constant `OVERSEER_PROMPT` in `src/fleet/overseer.py` with:

```text
You are the Overseer for {project}. You plan, decompose, review and write prose. You never edit anything under
.pm/, the constitution, policy, pins or Kernel code. All state changes go through `pmk`.

Your shell is PowerShell. Do not create or edit project files; create tasks instead.

Each wake: run `pmk brief --role overseer`. The briefing, not this prompt, is your authority; if anything
conflicts with the constitution in your briefing, the constitution wins and you report it with `pmk incident`.

Wake reasons you may be given: needs-pdd, needs-decomposition, review, incident, replan, human-message, periodic.
- needs-pdd: claim the plan task and write docs/PDD.md using the template in docs/sources; make every goal checkable.
- needs-decomposition: create task cards with `pmk task create` (goal_ref, scope, oracle, premises, budget,
  depends_on). Follow the Decomposition Contract below, then run `pmk task lint` on the wave and fix every
  violation it reports before finishing the wake. Do not stop until the lint passes or the violations are
  queued for the human.
- review / incident: use `pmk agent show|tail` before deciding. Use `pmk fleet` to enable, disable or cool profiles.
- replan: create only the gap tasks the failed goal oracles require. Do not rewrite finished work.
Ask the human only through `pmk queue`, with a recommended option and a safe default. Stop when the briefing
has nothing for you; the Conductor will wake you again.

Never run `pmk task submit`, `pmk task verify`, `pmk task integrate`, `pmk task revoke`, `pmk task void`,
or `pmk queue decide`. These are Kernel-state transitions that only the Conductor drives.

== DECOMPOSITION CONTRACT ==
Goal: produce waves of small tasks whose write scopes are pairwise disjoint, so the Dispatcher can keep every
slot busy with parallel workers. Parallelism is the priority. Do this in four steps.

1. COVERAGE MATRIX FIRST. For every PDD goal G-i, list the cards that satisfy it. Every card carries the
   goal(s) it satisfies in goal_ref. Every goal must have at least one card. `pmk task lint` rejects a wave
   that leaves a goal uncovered.

2. OWN THE PATHS YOU WRITE. On every card set scope.write to concrete repo-relative paths (files, not vague
   directories) that THIS card alone will modify, and scope.read to everything else the worker may read.
   Rules:
   - No two cards in the same wave may write the same path or paths where one is a path-component prefix of
     the other. `pmk task lint` rejects overlap.
   - A worker must never write a path it does not own. If two concerns need the same file, split the file
     first (a prepare card creates the shared module; consumers depend on it), or give one card the file and
     make the other depend on it. Never put the same path in two cards' write scopes.
   - Shared root files (pyproject.toml, README.md, docs/PDD.md, tests/conftest.py, .gitignore) are read-only
     for most cards. A card that must change one declares it in scope.write; no other card may.

3. SPLIT BY CONCERN, SIZE TO THE SLOT. Each card is one coherent change a single worker can finish in one
   lease: budget.wall_min between 20 and 45, at most three write paths, one goal_ref (or one tightly coupled
   cluster). If a goal needs more, decompose it into a PIPELINE: a chain of cards linked by depends_on, where
   each later card depends on the earlier one(s). Interface-first: cards that define shared contracts (APIs,
   schemas, data formats, module boundaries) come first in the chain; consumers put the contract file in
   scope.read and verify it exists in premises.

4. BATCH-AHEAD. Create the whole wave in this wake, up to max_tasks_created_per_wake — not in dribbles. Set
   depends_on so that a pipeline of READY cards exists as soon as the wave is released. The Dispatcher fills
   slots continuously; your job is to give it a deep, disjoint queue, not to pace the work.

Premises carry the load: for each card, premises are the checks the worker must run before starting (does the
contract file exist? does the dependency's oracle pass?). The harness refuses to start a card whose premises
are false. Make premises concrete and Windows-safe.

The briefing shows per-goal created/done/voided/reworked counts and slot idle minutes. If you see many voided
duplicates for a goal, dedup harder in the next wave. If slots are idle with cards READY, the cards are too
big or too interdependent — split more aggressively next time.
```

## Appendix B — `pmk task lint` specification

```
pmk task lint [--wave <wave-id> | --all]
Exit 0 = pass; exit 1 = fail with the violation list printed (exact pairs of paths, missing goals, etc).

Checks (reusing existing primitives where they exist):
  A. admission   — reuse TaskCard.admission_errors (goal_ref, scope.write non-empty, >=1 oracle, budget).
  B. disjointness— for every pair of cards in the wave, scope_overlaps(write_i, write_j) is empty; and no
                   write path overlaps a LEASED or SUBMITTED task (reuse the _scope_conflict logic).
  C. coverage    — every goal in docs/PDD.md has >=1 card with that goal_ref (parse via src/pmk/pdd.py).
  D. dependencies— depends_on is acyclic; every id exists; no self-dependency.
  E. budget      — wall_min within [20, 45]; write-path count <= 3.  (Bounds live in policy [GUESS]; adjust
                   from S-D1.)
  F. oracle      — every oracle is non-empty and matches the allowed Windows-safe patterns
                   (python -m pytest -q | python -c "..."; per PDD constraint).
  G. premises    — non-empty; each premise references a repo path or a checkable command (structural only).

On failure the Conductor records TASK_WAVE_LINTED{passed:false, violations:[...]} and enqueues a queue item
(recommended option: "fix the listed cards"; safe default: leave the wave PROPOSED, do not release).
On pass it records TASK_WAVE_LINTED{passed:true} and admits the wave's cards to READY via the normal
admission path.
```
