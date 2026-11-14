---
document:
  title: "Proposal: A Decomposition System for the UMAWS Fleet — finer-grained cards, more agents on the ledger"
  status: "Proposal — candidate tier; advisory; no authority"
  version: "1.0.0"
provenance:
  author_llm: {name: "Inkling 2 Small (free)", version: "thinkingmachines/inkling-2-small:free (via openrouter)"}
  assessed_documents:
    - "proposal-deepseek-umaws-fleet-parallel-decomposition-v1.md (deepseek-v4-flash-free, 2026-11-02; advisory)"
    - "assessment-claude-umaws-fleet-parallel-decomposition-v1.md (Claude Sonnet 5.5, 2026-11-02; advisory)"
    - "relay-C-phase0-census-v1.md (census of 2026-11-02 ledger copy)"
  created_date: "2026-11-11"
  last_modified_date: "2026-11-11"
audience:
  primary: "The human operator (decision record)"
  secondary: "Implementing LLM(s) (executable brief, sections 6 and 8; appendices A–C)"
  tertiary: "The Overseer and future fleet agents (the Decomposition Contract, appendix A)"
source_documents:
  - "src/pmk/decompose.py (width analysis, MAX_PATHS_PER_CARD = 3, TREE_ROOTS)"
  - "src/fleet/overseer.py (OVERSEER_PROMPT; needs-decomposition guidance)"
  - "src/pmk/models.py (TaskCard; scope_overlaps — prefix-overlap rule)"
  - "src/pmk/api.py (claim-time scope-conflict refusal, line ~476)"
  - "src/fleet/harness.py (scope_check at submit/integrate)"
  - "src/pmk/briefing.py (briefing rendering)"
  - "agents.toml (max_total_agents = 10, operator-set 2026-11-01; raised from 6)"
  - "HANDOFF.md — 'Latest evidence (2026-11-11)' (212 cards: 155 VOID / 43 DONE / 12 READY / 1 VERIFYING / 1 LEASED; 2 active leases; dispatch PAUSED)"
  - "pilot/STATE.md; docs/PDD.md; pilot/decisions.md"
evidence_basis: "Repo files read this session (decompose.py, overseer.py, models.py scope_overlaps signature, agents.toml, HANDOFF.md 2026-11-11 evidence block, relay-C census). The CFNA ledger itself was NOT re-queried; every ledger number below is tagged [OBSERVED-HANDOFF] or [OBSERVED-RELAYC] and must be re-measured by Phase 0. No code in this document has been run."
epistemic_status: "Tags: [STATED] the operator said it (interview 2026-11-11); [OBSERVED] read from repo/HANDOFF this session; [INFERRED] my reasoning; [GUESS] needs measurement; [VERIFY] check before relying on it."
authority_statement: "Candidate tier: no authority. Nothing here takes effect until the operator decides. Changes to admission rules, policy.toml, constitution.md or class K constants are two-key and are flagged explicitly in sections 6 and 9. Preserving the Kernel, D-L6's default, the merge machinery and I5 is a design requirement, not a preference."
---

# UMAWS Fleet: A Decomposition System for More Concurrent Agents

## 0. How to read and use this document

1. **Operator:** read §1 (verdict), §3 (why "gated by scope" is a hypothesis, not a fact), §9 (decisions needed) and §10 (what this is not). Everything else can wait.
2. **Implementing LLM:** §4 (the design), §6 (phases and exit criteria), §7 (success metrics), appendices A–C. Do not start beyond Phase 1 until the Phase 0 census report has been reviewed by the operator.
3. **Overseer / agents:** appendix A is the contract you will operate under, once ratified. It is not in force until the operator decides (§9).
4. Every claim carries a tag. Do not implement a [GUESS] or [VERIFY] as if it were measured.
5. This is a **fresh design**. It references the two 2026-11-02 documents as prior art (§8) and keeps what survived contact with the repo; it does not inherit their plans.

---

## 1. Verdict

**Build decomposition as a verified production step, then make the cards smaller — in that order.**

The fleet is already built to run many agents in parallel (leases with fencing, claim-time scope-conflict refusal, submit-time scope check, write-scope-only merge) [OBSERVED: src/pmk/api.py, src/fleet/harness.py]. The bottleneck is upstream of the Dispatcher: the Overseer emits too few READY cards, too coarse, with scopes that collide, so slots idle [INFERRED from ledger counts + decompose.py's existence; CONFIRMED-DIRECTION by relay-C; NOT re-measured this session — Phase 0 required].

The fix is not "ask the Overseer to try harder" and not "abolish D-L6". It is a system with four parts:

1. **A census first** (Phase 0) — classify every card and every gate, so we fix the real causes, not the loudest one. [STATED: operator chose census + design]
2. **A finer-grained card contract** — a granularity *ladder* (§4.2), with the default tightened to one-file cards and an opt-in sub-file mode; interfaces become tiny "contract cards" that land first so implementations can fan out without waiting on each other (§4.5).
3. **A wave lint as the release oracle** (§4.4) — machine-check a whole wave (disjoint scopes, width ≥ target, acyclic, goal coverage, budget) *before* cards are released to READY. This extends I5 (Oracles decide) to decomposition itself.
4. **Feedback and look-ahead** — a per-goal digest and slot-idle minutes in the briefing, plus batch-ahead card creation so the next wave is ready before the current one drains (§4.6–4.8).

D-L6 is **explored, kept by default, and extended opt-in** (§4.3): additive/append-only scope kinds and symbol-level scopes are proposed as *operator-ratified* extensions, never as silent relaxation. The Kernel is not rewritten. The merge machinery is untouched.

**Expected outcome, honestly stated:** sustained concurrency near the cap — currently **10** (`agents.toml`, operator-set 2026-11-01; the 2026-11-02 docs' "6" is stale) [OBSERVED]. A realistic, measurable target is **≥8 of 10 busy slots sustained over a working week, ≥75 % of waves at ≥ cap-width of disjoint READY cards, and a void rate halved from the observed ~73 %** [GUESS — to be ratified by Phase 0 baseline and the §7 metrics]. No decomposition work can exceed provider capacity, merge serialisation, or the Overseer's wake budget (§10.3).

---

## 2. Where this stands (evidence, tagged)

| Fact | Value | Tag |
|---|---|---|
| Ledger (2026-11-11) | 212 cards: 155 VOID, 43 DONE, 12 READY, 1 VERIFYING, 1 LEASED; 2 active leases; dispatch **PAUSED**; 104 incidents | [OBSERVED-HANDOFF] |
| Void rate | 155/212 ≈ **73 %** of all cards ever created were voided | [OBSERVED-HANDOFF → computed] |
| 12 READY cards | T-0192–T-0195, T-0199, T-0200, T-0202–T-0207 | [OBSERVED-HANDOFF 2026-11-10; not re-verified] |
| Fleet cap | `max_total_agents = 10` (operator edit 2026-11-01, raised from 6; note in `agents.toml` cites free-model slowness at high concurrency) | [OBSERVED] |
| Width tooling | `src/pmk/decompose.py`: pairwise-disjoint greedy width, narrow-first seating; `MAX_PATHS_PER_CARD = 3`; `TREE_ROOTS`; renders the "Decomposition" section of the Overseer briefing | [OBSERVED] |
| Overlap rule | `scope_overlaps`: one path is a path-component-wise prefix of another ⇒ overlap | [OBSERVED] |
| Claim refusal | `pmk.api.claim` refuses a card overlapping an active lease's write scope | [OBSERVED] |
| Overseer guidance | One sentence: disjoint scopes, "prefer many small tasks", ≤3 paths, 12–20 cards/wave, ≥ cap leaseable | [OBSERVED] |
| Prior census (2026-11-02) | 138 cards then: 130 VOID, 5 DONE, 3 READY; voiding is operator-only (`task_void` refuses non-human) | [OBSERVED-RELAYC] |
| CFNA live run | At handoff: 0 READY, 2 DONE, 3 LEASED | [OBSERVED — quoted by 2026-11-02 docs; not re-verified] |

Two observations fall out of this table, and both shape the design:

- **The failure mode is upstream and structural.** A 73 % void rate is not bad luck; it is the Overseer creating cards that are doomed at birth (duplicates, unreachable dependencies, oversized scopes) or that no agent can ever claim because every sibling overlaps them. [INFERRED]
- **Width, not cap, is the binding constraint — today.** `decompose.analyse` already computes the greedy disjoint width; the briefing already shows it; the Overseer already reads it. The missing pieces are (a) the granularity to *create* narrow cards, (b) a gate that *refuses* wide waves, and (c) feedback so the Overseer learns from its own void rate. [INFERRED]

---

## 3. Diagnosis: "gated by scope" is one of nine gates — measure before you cut

[STATED: the operator's premise is scope-gating. It is plausible and partially instrumented; it is not yet quantified on the current ledger.]

| # | Gate | Mechanism | Instrument |
|---|---|---|---|
| G1 | **Write-scope overlap** (prefix rule) | `claim` refuses overlapping cards | `decompose.analyse` conflicts; `pmk brief` Decomposition section |
| G2 | **Dependency chains** | `depends_on` unsatisfied ⇒ not claimable | `decompose._depth`; briefing "longest dependency chain" |
| G3 | **Whole-tree scopes** | `src/`, `docs/` … block every card beneath | `decompose.TREE_ROOTS` / `Shape.broad` |
| G4 | **Oversized cards** | >3 write paths ⇒ blocks beside siblings | `MAX_PATHS_PER_CARD` / `Shape.oversized` |
| G5 | **Fleet cap** | `max_total_agents` | `agents.toml`; currently 10 |
| G6 | **Too few READY cards** | Overseer under-produces; PROPOSED never released | PROPOSED→READY admission path; briefing digest (§4.8) |
| G7 | **Void clutter / lifetime caps** | Voided cards may count against lifetime `max_total_tasks` [VERIFY in policy.toml]; void is operator-only | ledger count; `task_void` actor check |
| G8 | **Orphaned / cyclic / stale deps** | dep on VOID/REJECTED/never-READY card | lint check (§4.4 L4) — currently unchecked [VERIFY] |
| G9 | **Human-authority gates / class K** | Constitution/policy; some transitions operator-only | HANDOFF 2026-11-11 (CP-3/CP-4, authority gate) |

**Phase 0 census (read-only, half a day, first thing).** Script over `.pm/` (copy, never the live ledger) answering: per card — state, scope size, breadth (tree-root?), dependency depth, void reason, time-to-void, sibling overlap matrix; per wave — greedy disjoint width vs cap, conflicts by G-class. Output: `pilot/decomposition-census-2026-11-<date>.md` + machine-readable width time-series. **No design claim is treated as fact until this lands.** [STATED: operator chose census + design]

**What the census decides:** if G1+G3+G4 dominate → §4 as written. If G2 dominates → weight §4.5 (contract-first) and the critical-path lint over everything else. If G7 dominates → the cheapest win is ledger hygiene + admission feedback, not new lint. If G6 dominates → the Overseer prompt (§4.6) is the whole game and the lint is secondary. [INFERRED]

---

## 4. The design — "Narrow Waves"

### 4.0 Principles

1. **Decomposition is a production step, with an oracle.** I5, extended upstream: no wave reaches READY until a machine checks it. [STATED: constraint I5]
2. **Own the paths you write.** Every card declares its write scope; an agent that needs a path outside it stops and queues (existing harness `scope_check` behaviour) — decomposition exists to make "outside it" rare. [OBSERVED]
3. **Narrowest first.** Prefer cards with one small path; the wave seats narrow cards first (already `decompose.py`'s seating rule — keep it). [OBSERVED]
4. **Contracts before implementations.** Interfaces are tiny, stable cards; implementations fan out behind them and never block each other. (§4.5)
5. **Batch ahead.** The Overseer creates the next wave while the current one runs; slots never idle waiting for decomposition. (§4.7)
6. **Never relax a safety invariant to buy width.** D-L6 stays the default; new scope *kinds* are additive and operator-ratified. (§4.3)

### 4.1 Task-shape vocabulary (additive, no Kernel rewrite)

Extend the card **additively** (new optional fields; old readers ignore them):

- `scope_kind`: `"file"` (default) | `"symbol"` (`path#symbol`) | `"append"` (append-only shared file) | `"generated"` (regenerated artifact, never hand-merged). Kernel stores it; `scope_overlaps` is untouched unless §4.3 is ratified.
- `goal_ref`, `oracle`, `premises`, `budget`, `depends_on` — unchanged.
- New card type `contract` (additive to TASK_TYPES behind operator decision — class K flag if TASK_TYPES is pinned; [VERIFY] where TASK_TYPES is defined and pinned).

### 4.2 The granularity ladder — options and tradeoffs [as STATED requested]

| Level | Card shape | Parallelism ceiling | Cost / risk | When to use |
|---|---|---|---|---|
| **A. Today** | ≤3 paths, leaf dirs, no tree roots | Width ≈ number of sibling modules/files; collides fast on shared roots | Zero change; proven limits | Keep as the floor |
| **B. One-file cards** *(recommended default)* | Exactly one file path (plus that file's declared test file if unavoidable — count as 2) | One lane per touched file; integrations serialise per file | More cards; more merges; more planning calls | **Default for all new waves** |
| **C. Symbol cards** | `path#Symbol` (class/function/doc-section/test-case-id) | Multiple lanes per file | Needs parseable boundaries (Python AST via stdlib `ast`; Markdown by heading); merge order matters; oracle must be section-scoped | Hot files (e.g. `models.py`, `api.py`), test files, doc indexes |
| **D. Append-only lanes** | Several agents append to one shared file (e.g. `index.json`, changelog, `decisions.md`) with ordered merge | Many lanes per file | Ordered merge queue; append-only discipline; conflicts = human | Registries, ledgers, docs indexes |
| **E. Generated artifacts** | Cards declare *producers* of generated files; generators run at integrate time, not in worktrees | Removes the hottest shared files from the scope graph entirely | Correctness of generator; determinism | Manifests, checksums, index files |

**Recommendation:** default **B**, opt-in **C/D/E** per-wave by Overseer judgement, ratified per-project in the PDD, and **never below B without the wave lint of §4.4 passing**. A is not a goal, only the floor.

Tradeoff headline: **granularity trades planning cost and merge overhead for width.** Every level down the ladder multiplies card count and integration events; the §7 metrics must show the trade is net-positive before C/D/E become routine. [INFERRED]

### 4.3 D-L6 — explored, kept by default, extended opt-in

[STATED: operator asked to explore both; this is the exploration.]

**Option 1 — Abolish D-L6 (overlapping writes allowed, merge reconciles).** Rejected. It moves conflict detection from claim-time (cheap, local) to merge-time (expensive, mid-flight, potentially after hours of agent work), breaks the write-scope-only merge invariant and the evidence chain (I5), and converts silent waste into loud, costly failure. Not recommended.

**Option 2 — Keep D-L6 exactly as-is; buy all width from B.** Safe, zero kernel change; ceiling = number of disjoint files ≈ finite but large; collides on `models.py`-class hotspots.

**Option 3 (recommended) — Keep D-L6 as the claim invariant; add ratified scope kinds.**
- `append` lanes (D above): claim-time allows N append-cards per append-only file **iff** the card declares `scope_kind: "append"` **and** the file is listed in a per-project `append_ok` registry (operator-ratified, in the PDD; additive config, class K if stored in policy.toml — [VERIFY] storage location; default proposal: `agents.toml`-adjacent additive section or PDD, not policy.toml). Merge order = lease order; harness enforces append-only diffs (added lines only, no edits to prior lines — checkable with `git diff --unified=0` semantics).
- `symbol` lanes (C): claim-time treats `path#Sym1` vs `path#Sym2` as disjoint; same-symbol overlaps as today. Kernel change surface: `scope_overlaps` gains an optional `kind` parameter; default behaviour byte-identical. This is a Kernel-adjacent change ⇒ **class K review**; flagged, not slipped in.
- `generated` (E): no scope at all; artifact excluded from merge conflicts; generator runs under the integrator.

**Recommendation: Option 3, staged — B immediately (no ratification needed), C/D only after Phase 0 shows hotspot-bound waves, each behind an explicit operator decision.** D-L6's default refusal is never removed; extensions only ever *narrow* what counts as a conflict, never widen it.

### 4.4 Wave lint v2 — the decomposition oracle (extended `decompose.py` + new `pmk wave lint`)

Run **before** release PROPOSED→READY; refuse the release on failure (advisory mode first, gate mode after ratification — §9 decision 2; admission-gate change = class K flag). Checks:

- **L1 Disjointness:** pairwise write scopes (kind-aware) conflict-free within the wave.
- **L2 Width:** greedy disjoint width ≥ target (default = min(cap, 10)); report shortfall (existing `WidthReport`).
- **L3 Acyclicity:** `depends_on` graph acyclic; no self-deps.
- **L4 Dependencies resolvable:** every dep exists, is not VOID/REJECTED, and (for cross-wave deps) is DONE or earlier in this wave's topo order.
- **L5 Critical path:** longest chain ≤ K cards (recommend K=4; [GUESS — ratify]).
- **L6 Goal coverage:** every PDD goal referenced by ≥1 card; every card references ≥1 goal (existing `goal_ref`) — orphan cards refused.
- **L7 Duplicates:** normalised (goal, scope-set, title-signature) uniqueness across the wave and vs READY/LEASED cards (guards the 2026-11-02 duplication mode [OBSERVED-RELAYC]).
- **L8 Budget feasibility:** sum(card budgets) ≤ remaining project budget; per-card budget sane.
- **L9 Oracle exists:** every card names a runnable `oracle`/`gate_cmd`; lint parses it (reuse `oracle_lint.py` [OBSERVED src/pmk/oracle_lint.py]).
- **L10 Tree-root / oversize refusal:** existing TREE_ROOTS / MAX_PATHS_PER_CARD checks, raised as errors in gate mode.

Output: a wave report (width, depth, conflicts by class, coverage gaps, duplicates) stored as evidence bundle + printed in the briefing. Refusal, when in gate mode, records `WAVE_REFUSED` (new event type — additive).

### 4.5 Contract-first fan-out — dissolving dependency chains [STATED: explore both]

**Strict `depends_on` (today):** real prerequisite → sequential. Correct for data prerequisites (schema before migrations), wrong for *interface* prerequisites (everyone waits for the type module to merge before writing anything).

**Contract-first (proposed):** a goal's interface surface is cut into **contract cards** (one per interface: types, protocol, schema, fixture — one file each, scope = that file). Contract cards merge first (they are tiny). Implementation cards then depend on the *contract card*, not on each other; the lint (L4/L5) treats contracts as depth-1 seeds. Implementations are built against the signed interface; if the interface must change, that is a **contract amendment queue item**, not a silent rewrite.

**Explored honestly:** contract-first pays when (a) many implementations share an interface, (b) the interface is stable once written. It fails when the interface is speculative — hence: contracts are written from the PDD's goal text and existing code, never invented; a contract that proves wrong is amended via queue, and affected implementation cards REWORK through the normal ladder. **Recommendation: contract-first for interfaces; strict `depends_on` for data prerequisites; both enforced by L3–L5. No speculation of behaviour, ever — only of signatures.** [INFERRED]

### 4.6 Overseer Decomposition Contract (drop-in; appendix A)

Replaces the one-sentence guidance. Core moves: **coverage matrix first** (goal × path), **own every path you write**, **one file per card by default**, **contracts before implementations**, **12–20 cards/wave, ≥ cap leaseable disjoint**, **batch ahead** (create wave N+1 while N runs), **void-rate feedback read every wake** (§4.8). Embedded in `OVERSEER_PROMPT` (needs-decomposition branch) and in the briefing's Decomposition section.

### 4.7 Dispatcher look-ahead & low-water wake

- **Low-water mark:** when READY-count < cap (or < ½ cap), the Conductor/Dispatcher emits `needs-decomposition` [VERIFY current wake-reason plumbing in `src/fleet/overseer.py` / conductor]. Overseer wakes; creates the gap wave.
- **Batch-ahead:** Overseer's standing instruction — always keep ≥ 1.5× cap leaseable cards queued. [GUESS — tune from §7 metrics]
- **No dispatcher rewrite:** this is a wake-reason + briefing change, not a scheduling algorithm. (Smarter scheduling — priority, critical-path-first dispatch — is Phase 6, explicitly deferred.)

### 4.8 Feedback digest (briefing extension)

Per goal: cards created / DONE / VOID / REWORK; per wave: width vs cap; slot-idle minutes since last wave; **void-rate trailing-20**. The Overseer reads its own failure data on every wake and self-corrects the next wave. (Pattern proven by `decompose.render_section` [OBSERVED]; this extends it from scopes to outcomes.)

### 4.9 Staged re-scope of the existing ledger [STATED: both, staged]

Applies to the 12 READY (T-0192–T-0195, T-0199, T-0200, T-0202–T-0207) [OBSERVED-HANDOFF — re-list at execution time] and any un-merged PROPOSED:

1. **Score** each READY card: paths count, breadth (tree-root?), depth, goal ref, void-risk signature (duplicate of a DONE card? oracle missing?).
2. **Split candidates** go to the operator as a queue item with a recommended split (void + recreate finer). Voiding is operator-only by design — correct and preserved.
3. **Orphans/doomed** (duplicates, unreachable deps) are recommended for void, with evidence.
4. **Recreate** as B-cards + contract cards; the wave passes the §4.4 lint before release.
5. T-0192 specifically (H1 done but scope excludes two fleet test helpers; HANDOFF 2026-11-11): it is a live example of under-scoped cards blocking merge — fold it into the same pass. [OBSERVED]

Deliverable of the pass: a re-plan report; **zero** kernel events without operator decision.

---

## 5. Invariants preserved

| Invariant | Status under this design |
|---|---|
| I2 — Kernel as sole writer | Untouched; new event types additive only |
| I5 — Oracles decide | Extended: decomposition itself gets an oracle (§4.4) |
| I8 — Pinned policy | No PIN changes except if §4.3 C/D ratified; flagged class K |
| I13 — Views as projections | Wave report folded into existing view machinery; sentinel re-run |
| D-L6 — Disjoint write scopes | Default preserved; extensions opt-in, ratified, narrow-only (§4.3) |
| Merge machinery (`merge.py`) | Untouched; append lanes use ordered merge, not concurrent merge |
| Recovery ladder L0–L4 / dispatch PAUSED posture | Untouched; dispatch remains operator-controlled |

---

## 6. Phases and exit criteria (the executable brief)

**Phase 0 — Census (read-only; ~half day).** Classify all historical cards (G1–G9), width time-series, void-reason Pareto. *Exit:* `pilot/decomposition-census-*.md` reviewed by operator; §3 table replaced with measured numbers.

**Phase 1 — Briefing + prompt + narrower cards (no gate).** Extend `render_section` with §4.8 digest (additive); replace OVERSEER_PROMPT needs-decomposition branch with appendix A; Overseer instructed to B-default. *Exit:* two waves created under the new contract; width report attached; no code beyond `decompose.py`/`overseer.py`/`briefing.py` + tests; `pytest -q` green; sentinel clean.

**Phase 2 — Wave lint (advisory → gate).** Implement §4.4 L1–L10 in `src/pmk/decompose.py` + `pmk wave lint` CLI; advisory first; then gate mode behind operator decision (class K if it changes PROPOSED→READY admission — [VERIFY] where admission is enforced; if in kernel API, two-key). *Exit:* a wave refused in advisory that would have been released before; gate mode only after ratification.

**Phase 3 — Feedback + low-water wake.** §4.7–4.8; conductor emits `needs-decomposition` at low water. *Exit:* measured idle-slot minutes drop across two consecutive waves.

**Phase 4 — Re-scope the existing ledger.** §4.9; operator-only voids. *Exit:* all 12 (re-listed) cards either DONE, re-cut to B-cards through a green lint, or void-recommended with evidence.

**Phase 5 — Opt-in scope kinds (only if Phase 0 demands).** §4.3 Option 3 C/D/E; contract type; `append_ok` registry; kind-aware `scope_overlaps`. *Exit:* class K ratification; regression tests proving default behaviour byte-identical; one live wave using an append lane under supervision.

**Phase 6 (deferred) — Critical-path-first dispatch scheduling.** Out of scope here; noted so nobody smuggles it in.

---

## 7. Measuring success (the only kind that counts) [STATED: provable/measured]

Baseline (Phase 0) then weekly:

1. **Width per wave** ≥ cap (10) for ≥75 % of waves (target; ratify in §9).
2. **Sustained utilisation** = busy slot-minutes ÷ (cap × elapsed wall minutes) ≥ 0.6 (target ≥ 0.8); measured from AGENT_STARTED→LEASE_ENDED/AGENT_STARTED pairs in the event log. [GUESS — define exactly in Phase 0 tooling]
3. **Void rate** (trailing 30) from 73 % → <40 % by Phase 2, <25 % by Phase 4. [GUESS]
4. **Time-to-READY** for a wave ≤ 20 min of Overseer wall time (wake budget 6/hour respected). [VERIFY overseer wake caps]
5. **I5 intact:** 100 % of merges green gate; rework rate ≤ Phase-0 baseline.

Every number has a command: `pmk brief --role overseer`, `pmk fleet status`, `pmk sentinel`, and the Phase 0 census script. Any "improvement" the operator cannot re-run is not an improvement.

---

## 8. Relation to prior art (fresh design, referenced — not inherited)

- **kept** from the deepseek proposal: decomposition as verified step; coverage matrix; briefing feedback; keep cap and D-L6. **changed:** no fixed 20–45 min card budget (sized from Phase 0 instead); wave lint moved *before* card creation; dependency handling made explicit (§4.5).
- **kept** from the Claude assessment: census-first ordering; lint-before-creation; width/critical-path measurement; orphaned-dependency handling; REWORK awareness. **changed:** target cap is **10**, not 6; the "≤3 paths" rule becomes a ladder with a one-file default (§4.2); the re-scope pass over existing cards (§4.9) is new and staged; contract-first is added as the answer to dependency-chain gating (§4.5).
- **both** documents under-weighted: the 73 % void rate as the headline metric, and the append-only/generated-artifact lanes that dissolve the hottest shared files (§4.2 D/E).

## 9. Decisions needed from the operator

1. Ratify the Phase 0 census first (read-only; no downside)?
2. Wave lint: advisory now, gate mode later — and is the PROPOSED→READY gate **class K** in this repo? [VERIFY where admission is pinned]
3. Adopt **B (one-file) as the default card granularity**? And C/D/E opt-in — now or never?
4. Contract-first fan-out (§4.5): amend PDD/contract process to allow contract cards?
5. Targets in §7 — especially sustained utilisation ≥0.6/0.8 and the void-rate goal.
6. Re-scope pass (§4.9): authorise the void recommendations it will produce, case by case?
7. `scope_kind` additive card field + contract card type — additive Kernel/API change OK? (class K if TASK_TYPES/admission pinned — [VERIFY])
8. Fleet cap stays 10 (this design assumes it) or is raised? (Raising is out of scope here.)

## 10. What this is not

1. **Not a Kernel rewrite.** Phases 1–4 touch `decompose.py`, `briefing.py`, `overseer.py`, CLI/tests. Only Phase 5 touches Kernel-adjacent code, and only behind §9 decision 7.
2. **Not D-L6 abolition.** Option 1 (§4.3) is documented and rejected.
3. **Not a ceiling-raiser for free-tier reality.** Provider rate limits, `MODEL_GONE`/`QUOTA` failures, the Overseer's 6 wakes/hour, merge serialisation and the human-authority gate all still bind. Utilisation above ~0.8 with free models would require cap/health/provider work outside decomposition. [INFERRED]
4. **Not authority.** Candidate tier; nothing here runs, merges, voids or dispatches without operator decision. No live provider calls are proposed or needed.
5. **Not finished measurement.** Every [GUESS]/[VERIFY] tag is a debt with a named phase to pay it.

## Appendix A — Overseer Decomposition Contract (drop-in for OVERSEER_PROMPT needs-decomposition branch / briefing)

> Create cards only from a **coverage matrix**: rows = PDD goals, columns = paths/modules; every cell empty or a card. Rules: (1) one deliverable per card; **one file per card by default** (declared test file may be a second path; three paths is a lint failure in gate mode); never a tree root. (2) **Contracts first**: if ≥2 cards share an interface, create the contract card(s) (types/protocol/fixture, one file each) before any implementation card; implementations `depends_on` contracts, never each other. (3) `depends_on` only for real data prerequisites; aim for chains ≤4. (4) Cards in one wave must have pairwise-disjoint write scopes (`path#Symbol` disjointness only if §4.3 ratified). (5) Aim **12–20 cards/wave, ≥ max_total_agents leaseable-disjoint** (check with `pmk wave lint`); do not stop while the briefing reports a shortfall and you have PDD goals left. (6) **Batch ahead**: keep ≥1.5× cap leaseable cards queued; create wave N+1 while N runs. (7) Read your trailing-20 void rate and idle-slot minutes in the briefing; if either trend is bad, shrink cards further and re-split shared scopes before creating anything new. (8) Hot shared file? Propose an `append` or `generated` lane in your report instead of widening scopes. (9) Oracle runs only the card's own tests; no card names another card's merge.

## Appendix B — Worked example (one goal → 14 cards, width 12)

Goal: "Regenerate `docs/rules/index.json` and enforce freshness in CI."

1. `contract` — `tools/rules_index_schema.md` (scope: that file) — depth 1
2. `B` — `src/cna/rules_index.py` generator (1 file) — depends 1
3. `B` — `tests/cna/test_rules_index.py` (1 file) — depends 1
4. `B` — `src/cna/rules_freshness.py` CI check (1 file) — depends 1
5. `B` — `tests/cna/test_rules_freshness.py` (1 file) — depends 1
6. `B` — `.github/workflows/rules-freshness.yml` (1 file) — depends 4
7. `E` — regenerate `docs/rules/index.json` at integrate time (no scope; generated) — depends 2,3
8. `B` — `docs/rules/README.md` regeneration note (1 file) — depends 7
9.–14. six `B` cards, one per rule-file validator gap found by the coverage matrix — depends 1 only.

Wave lint: L1 ✓ (all scopes disjoint; generated excluded), L2 width 12 ≥ 10 cap ✓, L3 acyclic ✓, L5 depth 3 ✓, L6 all cards → goal 8-ish refs ✓. Idle slots: 0 with cap 10 and 12-wide wave.

## Appendix C — File-touch list per phase

| Phase | Files | Tests |
|---|---|---|
| 0 | `pilot/decomposition-census-*.md`; `tools/census.py` (new, read-only) | none (report) |
| 1 | `src/pmk/decompose.py` (digest section), `src/fleet/overseer.py` (prompt), `src/pmk/briefing.py` (if digest renders there) | `tests/pmk/test_decompose.py` extensions |
| 2 | `src/pmk/decompose.py` (L1–L10), `src/pmk/cli.py` (`pmk wave lint`), event type (additive) | new `tests/pmk/test_wave_lint.py` |
| 3 | `src/fleet/overseer.py`, conductor low-water wake, briefing digest | fleet tests |
| 4 | none (ledger ops via `pmk` + operator) | — |
| 5 | `src/pmk/models.py` (kind-aware overlap, `scope_kind`), `src/fleet/merge.py` (append-order), `agents.toml`/PDD registry | regression: default-behaviour byte-identical |

**End of proposal. Candidate tier. The operator decides; nothing here is in force.**
