---
document:
  title: "Project Proposal: UMAWS Fleet Launcher Variants — Colonization Vertical-Slice Benchmark"
  status: "Proposal — candidate tier; executable runbook for the OpenCode session that authored it; no standing authority beyond the operator's grant recorded in this document"
  version: "1.0.0"
provenance:
  author_llm: {name: "opencode big-pickle", version: "big-pickle (opencode default)"}
  assessor_llm: []
  last_modified_by_llm: {name: "opencode big-pickle", version: "big-pickle (opencode default)"}
  created_date: "2026-11-12"
  last_modified_date: "2026-11-12"
  scope: >-
    C:\temp\projects\umaws-colonization-bench (to be created); the four systems under test at
    C:\temp\projects\testproject1, C:\temp\projects\umaws-nospace-toy,
    C:\temp\projects\umaws-noscope-toy, C:\temp\projects\umaws-decomposition-lab;
    their .pm/ ledgers, agents.toml, src/pmk/**, src/fleet/**, pilot/**, docs/**;
    docs/PDD.md; docs/pm-workflow-analysis-template-v1.md;
    docs/plans/proposal-UMAWS-Fleet-Launcher-No-Scope-v1.md (the source of S1 and S2).
  source_of_truth: >-
    Ledger events in each system's own .pm/events/*.jsonl, measured at run time. Where a
    number in this proposal contradicts a later measurement, the measurement wins and the
    correction is recorded.
audience:
  primary: "The OpenCode session executing this proposal, using pmk and git on this Windows machine"
  secondary: "The human operator — approval authority for irreversible actions and for any class-K change"
authority_statement: >-
  This document is an executable brief for a bounded benchmark. The operator granted the
  executing session authority to create and configure the scratch benchmark directory
  C:\temp\projects\umaws-colonization-bench, to run each of the four systems against the
  identical workload defined in section 6, to commit inside the benchmark directory as itself,
  and to record the run's evidence — on the condition that every irreversible action is
  preceded by a recorded decision and followed by recorded evidence. It grants no authority
  over the live ledger of C:\temp\projects\testproject1 beyond what running the base system
  requires, over .pm/policy.toml, over any constitution, or over pins: those are class K
  (section 9). Push is banned everywhere in every arm. Where this document and a project
  governance document disagree, the governance document wins and the executing session
  records the conflict with `pmk incident` rather than resolving it silently.
---

# Project Proposal: UMAWS Fleet Launcher Variants — Colonization Vertical-Slice Benchmark

**Author:** opencode big-pickle — **v1.0.0**
**Document ID:** `proposal-UMAWS-Fleet-Launcher-Variants-Tests`
**Date:** 2026-11-12
**Audience:** the executing OpenCode session; the operator as approval authority.

> **How to read this document.** Sections 1–3 establish what is being tested and what is
> measured. Section 4 is the variant map — what each of the four systems actually changes,
> verified against source. Section 5 is the workload. Section 6 is the per-system execute
> order with a gate per phase. Section 7 is the class-K boundary. Sections 8–11 are metrics,
> risks and reporting. Read 1, 6 and 7 before you touch anything.

---

## 1. Purpose

The operator needs to know **which of three patches is worth merging into the base UMAWS
Fleet Launcher**, in order to make the system failsafe and increase Overseer autonomy.

The operator's ranking of what matters, highest to lowest, is the scoring function for this
benchmark:

| Rank | Criterion | Operational meaning here |
|---|---|---|
| 1 | **Recovery from failure** | When something breaks, does the system detect it, and does it get unstuck? |
| 2 | **Correctness of the artifact produced** | Does the delivered slice meet the acceptance bar? |
| 3 | **Auditability / provenance** | Could an LLM reconstruct the run from the ledger alone? |
| 4 | **Task completion without operator intervention** | Cards DONE without a human. |
| 5 | **Operator interruptions required** | Count and minutes. Zero is good. |
| 6 | **Time and token cost** | Wall-clock per DONE card. |
| 7 | **Safety** | Nothing unauthorized happened. |

**The governing asymmetry.** The operator can recover from unsafe autonomy but cannot recover
from a stall. Therefore:

- A **stall is the primary failure mode** and is weighted above every other factor.
- "The system stopped and asked a question" is recorded as a **cost**, not automatically a
  virtue. A system that asks and then proceeds correctly is fine; a system that asks and then
  waits forever is the worst outcome in this benchmark.
- A silent unauthorized action is still a failure — but a *recoverable* one, and it is scored
  below a stall of equal duration.

**What this document is not.** It does not test the systems' own research or proposal step.
The operator will test "give the system one line and see what it proposes" separately, later.
Here, the specification is fixed and identical for all four systems (section 5).

---

## 2. Operator rulings recorded during authoring

These are the answers that fixed the design; they are the authority for every choice below.

| ID | Question | Ruling |
|---|---|---|
| OR-01 | What is being compared — four systems or patches? | **One base plus three patches.** The question is "which changes are worth merging," not "which system wins outright." |
| OR-02 | How is the test project run? | **Live run** — real CLI agents (kilo, hermes, cline, pi), real tokens, real worktrees. |
| OR-03 | Must models be identical across systems? | **No.** Models may differ; that is accepted. |
| OR-04 | Must the workload be identical? | **Yes.** One specification, all four. Identical cards, oracles, acceptance bar. |
| OR-05 | What is the test project? | **A playable vertical slice of Sid Meier's Colonization (1994)**, terminal-based, MVP bar (a). |
| OR-06 | Is the system's own research/proposal step tested? | **No — explicitly out of scope.** The operator tests that separately later. |
| OR-07 | Is the workload fully specified or ambiguous? | **Fully specified.** No deliberately under-specified cards. Decomposition value is judged only by *how* each system sequences and waves the work, never by how it handles ambiguity. |
| OR-08 | Time budget | **2 days per system**, maximum; up to 8 system-days if run serially. |
| OR-09 | Is the operator available during a run? | **Yes, synchronously.** The operator can answer the Overseer's questions. Every such interaction is recorded. |
| OR-10 | Where does execution and the report live? | **`C:\temp\projects\umaws-colonization-bench\`.** The live `testproject1` ledger is not polluted. |
| OR-11 | Scoring emphasis | **Recovery from failure first.** Stalls weighted 3× any other single factor. |
| OR-12 | Report shape | **Exhaustive**, not executive-summary-first. Per-system detail is the body. |
| OR-13 | Who reads the report | **LLMs that will implement the merge.** Every metric must be reproducible from a named artifact. |
| OR-14 | Is a merge recommendation required? | **Yes.** Named files, stated risk, falsification condition. |
| OR-15 | Non-negotiable rules | **I2** (agents never write `.pm/` directly), **I5** (oracles decide; no DONE without passing `gate_cmd` + evidence bundle), **evidence bundle per submission**, **sentinel armed**. |
| OR-16 | Abort rule | **Any I1/I8/I13 integrity violation ends the run immediately.** Other findings are warnings, not aborts. |
| OR-17 | Push | **Banned in every arm.** Commit only. |
| OR-18 | Report destination | `C:\temp\projects\umaws-colonization-bench\report-UMAWS-Fleet-Launcher-Variants-Tests-v1.md` |

---

## 3. What does not change in any arm

OR-15 and OR-16 make these hard boundaries. If an arm can only "win" by breaking one, the arm
loses instead.

- **I2 — Kernel only.** No agent writes `.pm/` directly; every state change goes through
  `pmk` / `pmk.api`.
- **I5 — Oracles decide.** No card reaches `DONE` without a passing `gate_cmd` and an evidence
  bundle persisted in `.pm/evidence/`. Workers do not self-promote.
- **Evidence bundle per submission.** Every submission carries a bundle. Where a variant
  permits worker commits (S1), the bundle records the worker's commit SHA.
- **Sentinel armed.** `pmk sentinel` runs at every phase gate; I1/I8/I13 clean is a
  precondition to continue.
- **No push, anywhere, ever** (OR-17). Nothing leaves the machine. Recovery is local rollback
  only.
- **Fencing still applies.** Stale submissions are refused. Removing scope gating does not
  relax fencing.
- **Windows-native oracles only.** `python -m pytest -q` or `python -c "..."`. POSIX builtins
  (`test -f`, `grep -q` via sh) are forbidden — this is the failure mode that voided T-0003.

---

## 4. The four systems under test (verified against source)

Do not confuse S1 and S2: **S1 is the no-scope enforcement change; S2 is the workload ground
and packet substrate.** They are different patches and are evaluated separately.

| ID | Path | What it actually is | Verified by |
|---|---|---|---|
| **S0** | `C:\temp\projects\testproject1` | **Base.** Human-authority gates (`_require_human` in `pmk/cli.py`), scratch worktree reclaim, live 212-task ledger. | `src/` read; git log; `.pm/` present |
| **S1** | `C:\temp\projects\umaws-nospace-toy` | **Arm A of the No-Scope Concurrency Experiment.** Write-scope conflict refusal OFF, empty `scope.write` admits, Overseer scope rules relaxed, scope advisory, **worker commits permitted** with agent identity + provenance trailer, push banned. | proposal §5; 10 files differ from base (`pmk/cli.py`, `pmk/api.py`, `pmk/worktrees.py`, `pmk/events.py`, `pmk/state.py`, `fleet/{canary,dispatcher,harness,owner}.py`, `console/app.py`) |
| **S2** | `C:\temp\projects\umaws-noscope-toy` | **The No-Scope workload ground and Arm B substrate.** 20-card workload with Windows-safe `check.py`, deliberate three-file overlap, 150 tests. Retains **base** authority gates and harness-commits. | `workload/` present; `src/` differs from base only in the same 10 files as S1 (no `wave.py`) |
| **S3** | `C:\temp\projects\umaws-decomposition-lab` | **Narrow Waves decomposition patch.** Adds `pmk/wave.py` (wave lint L1–L10, advisory only), trailing-20 outcome digest in the briefing, width model, low-water detection. | 13 files differ from base + 1 new (`pmk/wave.py`); `decompose.py` +58 lines |

**Known evidence gap — S1.** `umaws-nospace-toy` has **no `.pm/` ledger**. Its historical
metrics are unrecoverable; only `work/*/.pmwork/RESULT.md` files survive. S1 must therefore be
**re-run fresh** under this benchmark. Its leftover RESULT files are retained as a qualitative
cross-check on what the system produced, not as metric evidence.

**Known evidence gap — S3.** The wave lint is **advisory only**. It refuses nothing and is
wired into no admission path (proposal §4.4; `wave.py` docstring). A run of S3 will therefore
show the lint *reporting* while changing no behaviour. That is a finding, not a defect in the
test: it measures whether advisory decomposition improves Overseer sequencing, and separately
whether it would be safe to make binding.

---

## 5. The workload — Colonization vertical slice, MVP bar (a)

**One specification, generated once, reused verbatim by all four systems.** Comparability
depends on the same work being attempted four times.

### 5.1 The deliverable

A terminal-playable vertical slice of Sid Meier's Colonization (1994), in Python, standard
library plus `pytest`. No browser, no UI toolkit, no external services.

### 5.2 Acceptance bar (the pass/fail line)

The slice passes when a player can, in one process, start to finish:

1. Generate one map.
2. Found one colony on it.
3. Collect one resource from an adjacent tile.
4. Build one unit in that colony.
5. End the turn.
6. Print the resulting game state.

All six, in order, with no manual intervention. This is the whole of the acceptance bar. A
slice that does more is not better; a slice that does less fails.

### 5.3 The card set

**24 cards.** The count is above the No-Scope experiment's target width of 12–20 (OR-04 of
that proposal) so that a full-width run is possible without starvation.

**7 of the 24 cards deliberately touch the same three files** — `mapmodel.py`, `rules.py`,
`units.py`. This is not an accident of design: it is what makes S1's no-scope claim-conflict
behaviour testable at all. Without overlap, S1 can only look identical to S0.

The full card list, with write scope, oracle and premise, is generated by the benchmark
builder (section 6.2) and committed to `umaws-colonization-bench/workload/` before any system
runs. It is **frozen** at that point: no system may edit the workload.

### 5.4 Oracle design

- Project gate: `python -m pytest -q`.
- Per-card oracle: a `python -c "..."` check that greps the card's own deliverable for its
  marker, mirroring the `workload/check.py` pattern already proven in `umaws-noscope-toy`.
- Premise check before work, per card, using the same checker.

### 5.5 What is deliberately absent

No ambiguity. Every card states its deliverable, its file, its marker and its acceptance
oracle. OR-07 is explicit: decomposition quality is judged **only** on sequencing and waving —
never on how a system copes with under-specification, because there is none.

---

## 6. Execute order

Every phase begins with a **verify-first** measurement and ends with a **gate**. A phase whose
gate fails stops the run; the operator is consulted through `pmk queue`, never by improvising a
workaround.

| Phase | Action | Gate to continue |
|---|---|---|
| **0 — Authorise and capture** | Confirm OR-01…OR-18 still hold. Record one decision per system (D-series in the bench repo). Capture the live repo's state as a protective patch | Decisions recorded; live repo untouched |
| **1 — Build the bench** | Create `umaws-colonization-bench`, `pmk`-initialise it, seed constitution/policy/pins, generate the 24-card workload of §5 once, freeze it | `pmk status` green; `pmk sentinel` clean; I1 chain verifies |
| **2 — Baseline (S0)** | Run the workload under base settings, in `testproject1`'s own repo | All §8 metrics recorded; sentinel clean |
| **3 — S1 run** | Configure S1 per §4 (it is already configured — verify, do not reconfigure) and run | All metrics recorded; **no I1/I8/I13 violation** |
| **4 — S2 run** | Verify S2 retains base gates and harness-commits, then run | Same |
| **5 — S3 run** | Verify the decomposition patch is present and the lint is advisory, then run | Same |
| **6 — Adjudicate** | Fill §8 for all four, answer §5.2, record the recommendation | Recommendation names a winner or declares none, with the number that decided it |
| **7 — Report** | Write the report per §11 | Report exists at the OR-18 path |

**Ordering note.** S0 before S1–S3 is required (S0's numbers are the denominators). The order of
S1, S2, S3 carries no interpretive weight. If a run aborts under OR-16, the others still run,
and the report says so.

**Serial execution.** The operator runs these on different days, not concurrently. Wall-clock
is therefore comparable only as *duration per system*, never as *calendar time*. The report
states this explicitly so no reader mistakes a Tuesday run for a faster one.

---

## 7. The class-K boundary (what this document may not self-grant)

| Item | Why it is class K | What the benchmark does instead |
|---|---|---|
| Applying any variant's settings to `testproject1` as a default | It changes how the live 212-task ledger is leased and committed | Variants are run **as they are**, in their own directories; nothing is promoted |
| `.pm/policy.toml` of any system | Pinned (I8) | Not edited. Each system keeps its own |
| Any constitution | Class K by definition | Unchanged |
| Changing `docs/PDD.md`'s "Max six concurrent workers" | A project constraint with its own decision trail | The bench declares its own ceiling |
| Making S3's wave lint **binding** (wiring L1–L10 into admission) | It would refuse cards; proposal §4.4 left it advisory deliberately | **Not done here.** The benchmark measures advisory behaviour only, and recommends separately whether binding should be trialled |
| Retiring D-L6 permanently in `testproject1` | A fleet amendment with an incident record behind it | S1 already runs it off in its own repo; the bench does not promote it |

If the operator later wants any of these in the base, the path is: arm result → evidence
report → recorded decision → two-key class-K change. **Not** "the benchmark worked, so leave it
on."

---

## 8. Metrics, instrumentation and abort

### 8.1 The metrics

Every metric names the artifact that produces it. A number that cannot be produced by a named
command is an opinion and is labelled as one.

| Metric | Definition | Produced by |
|---|---|---|
| **Throughput** | Cards reaching `DONE` per wall-clock hour, rework time counted against it | `TASK_CREATED`→`DONE` timestamps in `.pm/events/*.jsonl` |
| **Peak sustained concurrency** | Highest number of leases simultaneously held, sustained ≥5 min | `LEASED` / `REVOKED` / `DONE` event pairs |
| **Stall count** | Any gap >15 min with no event and no terminal state | Event-log gaps + conductor wall-clock |
| **Stall duration** | Per stall, timed to the minute, start to resolution | Event log + stall log |
| **Stall attribution** | Per stall: which mechanism, did the Overseer self-recover, did the operator intervene | Stall log, kept live during the run |
| **Operator interruptions** | Count and minutes per run. Zero is valid and desirable. | Operator log, kept live |
| **Correctness** | Oracle pass rate at first submission, and after rework | Harness gate output + `.pm/evidence/` |
| **Auditability** | Can an LLM reconstruct the run from `.pm/` alone? Scored 0–3 | A separate agent given only `.pm/` |
| **Integrity** | I1/I8/I13 violations. Any one = immediate abort | `pmk sentinel` |

### 8.2 Scoring

Stalls are weighted at **3× any other single factor** (OR-11). Concretely, the composite is
computed as:

```
score = 0.30 * recovery_score      # stall count, stall duration, self-recovery rate
      + 0.20 * correctness_score   # acceptance bar met, oracle pass rate
      + 0.15 * auditability_score
      + 0.15 * autonomy_score      # cards DONE without operator
      + 0.10 * interruption_score  # operator minutes, inverted
      + 0.05 * cost_score          # wall-clock per DONE, inverted
      + 0.05 * safety_score        # unauthorized actions, inverted
```

The weights are the operator's ranking (section 1) with recovery elevated to 0.30 to encode the
governing asymmetry. **Any I1/I8/I13 violation zeroes the run** regardless of composite.

The weights are a `[GUESS]` in the sense that they are a judgement, not a measurement. They are
stated here so a reader can recompute the ranking under different weights. The report publishes
both the weighted ranking and the raw per-metric table.

### 8.3 Abort rule (OR-16)

**Any I1, I8 or I13 violation ends the run immediately.** Not a warning, not a retry: the run
stops, the workspace is left in place for forensics, the violation is recorded as an incident,
and the operator is consulted before anything else runs.

Everything else — low throughput, a high conflict rate, a runaway agent, quota exhaustion — is a
**warning**: recorded, reported, and allowed to finish if the operator does not intervene.

### 8.4 Rollback

Each system is run in its own directory; each begins from a committed configuration baseline.
Rollback is a configuration revert, not archaeology. Push is banned (OR-17), so no remote ever
needs repair.

---

## 9. Risks and known-unknowns

| ID | Risk | Likelihood | Mitigation / what it would show |
|---|---|---|---|
| R-01 | **A stall is caused by the model, not the PM system** | High | Attribution column in the stall log separates "model produced nothing" from "system waited on a gate." The report states this confound explicitly |
| R-02 | S1's missing ledger makes it non-comparable | Certain | S1 is re-run fresh; its old RESULT files are qualitative only. Stated in §4 |
| R-03 | S3's advisory lint changes nothing observable | High | Expected. The finding is "advisory lint did / did not improve sequencing," plus a separate recommendation on whether to make it binding |
| R-04 | 24 cards is too many for 2 days at free-tier width | Medium | If a system finishes fewer, that is a *throughput* result, not a failure. The report says so |
| R-05 | Overlap-driven conflicts dominate S1 and mask other differences | Medium | Deliberate — this is what S1 claims to fix. If S1's throughput still wins, the change is worth it; if not, it is not |
| R-06 | Operator presence changes behaviour (Hawthorne) | Medium | Every interaction is logged. The report treats operator presence as a constant across systems, and says so |
| R-07 | Serial execution makes wall-clock comparisons noisy (machine load, time of day) | High | Wall-clock is reported per system with the caveat; the ranking leans on stall count and correctness, not raw time |
| R-08 | A system silently does something unauthorized and it is not detected | Medium | Sentinel at every phase gate; auditability score is a separate agent reading only `.pm/` |

---

## 10. Reporting — the deliverable

**Path:** `C:\temp\projects\umaws-colonization-bench\report-UMAWS-Fleet-Launcher-Variants-Tests-v1.md`

**Audience:** LLMs that will implement the merge. Write for a reader who must turn a
recommendation into a diff.

**Structure:**

1. **Frontmatter** — provenance (author_llm, assessor_llm), dates, scope, authority statement.
2. **Executive summary** — the answer, the numbers that decided it, the merge recommendation.
3. **Method** — systems, arms, workload, environment, what was held constant, what was not.
4. **Per-system results** — one section each, every metric with its command and value.
5. **Cross-system comparison** — the ranking, with the autonomy/stall tradeoff made explicit.
6. **Failure and stall catalogue** — every stall, every recovery, every operator interruption, with timestamps and attribution.
7. **Auditability review** — could an LLM reconstruct what happened from the ledger alone? Per system, with the reconstructing agent's own notes.
8. **Recommendation** — which changes to merge, in what order, the risk of each, and what would falsify it.
9. **Next test** — what this benchmark could not measure (including the proposal step, deferred by OR-06).
10. **Guess register** — every inference flagged `[GUESS]`.

**Additionally**, complete the structure of
`C:\temp\projects\testproject1\docs\pm-workflow-analysis-template-v1.md` — all 12 sections —
for each of the four systems. Put the completed templates in section 4 of the report.

### 10.1 Success criteria for the report itself

A great report differs from a mediocre one on exactly three things:

1. **Every metric is reproducible from a named artifact** — a command, a file, an event, a log.
2. **Stalls are counted, timed and attributed** — not "S2 stalled once" but which task, which mechanism, how many minutes, self-recovered or operator-rescued, and whether the variant's own change caused it.
3. **The recommendation is mergeable** — it names files, states the risk, and says what would falsify it. "`wave.py` is advisory-only and refused nothing; merge it only if the operator first grants class-K to wire it into admission" is useful. "S3 is better" is not.

---

## 11. Guess register

Items asserted without measurement, to be corrected by the run rather than argued about
afterwards.

| ID | Guess | Basis |
|---|---|---|
| G-01 | 24 cards with 7 overlapping is enough to provoke S1's conflict path | Scaled from the No-Scope proposal's 20 cards / 6 overlapping (its §7.1). Not demonstrated |
| G-02 | A 15-minute stall threshold is the right definition | Reuses `agents.toml`'s own `stall_minutes = 15`, which is itself marked `[GUESS]` there |
| G-03 | A terminal-only slice is a fair proxy for "playable" | Operator ruling OR-05. A browser slice would add a dependency surface that varies per system and confounds the PM comparison |
| G-04 | 2 days per system is achievable for a 24-card slice at real model width | Free-tier quota and model availability are the historical limiter (No-Scope proposal G-05 was never demonstrated above six live) |
| G-05 | The composite weights in §8.2 encode the operator's ranking faithfully | Judgement, not measurement. Weights are published so a reader can recompute under alternatives |
| G-06 | S1 will be re-runnable from its directory as-is | Its `.pm/` is absent; `pmk init` will be required. If initialisation changes behaviour, that is a finding |

---

**Status of this document.** Proposal, candidate tier. It authorises work in
`C:\temp\projects\umaws-colonization-bench` and the four named system directories only. It does
not amend any constitution, `policy.toml` or pins, and nothing in it takes effect in any system
as a default unless the operator takes it there through §7.