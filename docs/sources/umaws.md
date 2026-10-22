---
document:
  title: "Ultimate Multi-Agent Workflow System: a fresh-synthesis architecture for autonomous LLM project management under one human operator"
  status: "Proposal — architecture and research report (candidate tier; no authority)"
  version: "1.0.0"
provenance:
  author_llm: {name: "Claude", version: "Claude Sonnet 5.5 (claude-sonnet-5-5)"}
  assessor_llm: []
  last_modified_by_llm: {name: "Claude", version: "Claude Sonnet 5.5 (claude-sonnet-5-5)"}
  created_date: "2026-09-30"
  last_modified_date: "2026-09-30"
evidence_basis: "Supplied project documents only (LLM-authored proposals, syntheses, and two LLM-authored reports about the live Babylon5CCGGameDesign system). No primary logs, ledgers, or repositories were inspected. No web research was performed for this report."
epistemic_status: "Mixed. Tagged per claim: [OBSERVED*] [CONSENSUS] [INFERRED] [SPECULATIVE]. Nothing here has been run."
source_documents:
  - "01-comparative-assessment.md"
  - "02-unified-proposal.md"
  - "ADDPMS-Unified-Synthesis.md"
  - "multi-agent-documentation-workflow-system-architecture-2026-09-26.md (live-system architecture report)"
  - "autonomous-pm-system-replication-manual-2026-09-29.md (live-system replication manual)"
  - "project-proposal-multi-agent-documentation-workflow.md"
  - "the 21+ individual proposals in project files (llm-projman-*.md, autonomous-*.md), read selectively"
  - "prompt-greatest-llm-system2.md (the governing brief)"
authority_statement: "This architecture is a new synthesis. It inherits no authority from any source document, from ADD-PMS, or from the Babylon5 system. Where it agrees with a source, that is a design decision made on the evidence in this report, not deference."
---

# Ultimate Multi-Agent Workflow System

## 0. Reading guide

**Epistemic tags.**

| Tag | Meaning in this report |
|---|---|
| **[OBSERVED\*]** | Reported by the supplied live-system documents. The asterisk is deliberate: both are LLM-authored secondary accounts. I could not check counts, timestamps, or incident details against primary logs. |
| **[CONSENSUS]** | Independently proposed by several of the supplied proposals. Weak evidence: the proposals were produced by LLMs answering the same brief, so shared training and shared prompt inflate apparent agreement. Convergence raises my prior; it does not settle anything. |
| **[INFERRED]** | My architectural reasoning from the evidence, including from standard distributed-systems and verification practice. |
| **[SPECULATIVE]** | Frontier proposal needing new tooling or experiments. |

**Coverage map.** The brief's 35 headings are all covered; some are merged where separating them would be ceremony: §13 covers brief items 13–14, §17 covers 17–18, §20 covers 20–21, §25 covers 25–26, §29 covers 29–30, §35 includes the roadmap.

**Supplied-material caveats that matter for how far to trust this report.**

1. `03-assessment-comparison-report.md` is named in the brief but was **not** among the supplied files. Nothing here draws on it.
2. The live-system evidence comes from two documents (the 2026-09-26 architecture report and the 2026-09-29 replication manual). They agree on most points but differ in details (for example the manual says the ledger had 494 rows; the architecture report says roughly 490). Point-in-time counts are treated as illustrative, not measured.
3. The manual itself flags that `canonical/` is named in governance but absent on disk **[OBSERVED\*]**: a small but real example of specification drifting from implementation.
4. Some individual proposals cite references I cannot verify (for example one cites several 2026 items with unusual titles). No claim in this report depends on them.

---

## 1. Executive summary

**The question.** Given the supplied proposals and the live Babylon5 system, what would we build now to maximise autonomous project completion for one human while preserving correctness, auditability and recoverability?

**The central finding.** Read as a failure catalogue, the Babylon5 record says something the proposals mostly miss: **a large share of its incidents come from LLM agents hand-editing shared text files that a machine should own.** Table-pipe corruption, duplicate task IDs, orphaned claim files, placeholder timestamps, encoding drift, a ledger truncated from ~380 rows to 1 and rescued from a `.bak`, wrongful reaping from clock skew, decision-log tail contention, and shared build-output collisions are all, at root, problems of using a Markdown table and a shared working tree as a concurrent database **[OBSERVED\* + INFERRED]**. The system's genuine strengths (boot contract, authority-by-location, immutable provenance, objective gates, append-only decisions, evidence-bearing close-outs) survived because they constrain what agents *say and promote*, not because Markdown is a good transaction store.

**The design in five moves.**

1. **Split the overseer into a deterministic Kernel and an LLM Overseer.** The Kernel is a small, tested, non-LLM program that alone writes coordination state (claims, leases, heartbeats, status transitions, promotion records). The LLM Overseer plans, decomposes, adjudicates and writes prose, but requests transitions from the Kernel. Agents never edit the ledger. [INFERRED; partially CONSENSUS]
2. **Three stores with distinct jobs.** Git holds artifacts and immutable decision records. A hash-chained, kernel-written event log is the coordination authority. Markdown views (ledger, status, queue) are *generated*, not edited. [INFERRED]
3. **Leases with fencing tokens, isolated per-claim worktrees, and a merge queue.** This turns wrongful reaping from a correctness disaster into a performance nuisance, removes shared-tree collisions, and ensures the gate runs on the tree that will actually become canonical. [INFERRED from OBSERVED\* failures + standard practice]
4. **Completion means an evidence bundle, verified oracle-first.** Executable oracles beat LLM judges; independent adversarial review covers what oracles cannot; planted-defect canaries measure whether verification actually works; sampled audits catch what all of that misses. [INFERRED; SPECULATIVE at the calibration end]
5. **A minimal human control surface with an interrupt budget:** a decision queue of pre-digested items with safe defaults, policy envelopes, a weekly audit sampler, a status page, and a stop-the-line switch. Human interrupts are treated as a defect signal in the design, not a feature. [INFERRED]

**What this report does not claim.** It does not claim multi-model verification eliminates correlated error, that any component is proven, or that the Kernel is free of its own failure modes (§34). Everything in §31 can be built with current tooling; §32 lists what cannot yet.

---

## 2. Problem definition and operating assumptions

**System.** One human operator; one persistent LLM overseer/documentarian (currently OpenCode); many transient LLM workers from a heterogeneous pool; a repository/filesystem as durable environment; work spanning documentation, research, coding, testing, maintenance, coordination, recovery and self-improvement.

**Assumptions.**

| ID | Assumption | Status |
|---|---|---|
| A1 | Workers have no memory across sessions and may crash, stall, or be silently replaced by a different model. | [CONSENSUS] |
| A2 | Workers can be wrong, fabricate evidence, and claim false completion. | [CONSENSUS] |
| A3 | Worker clocks and self-reports are untrusted. | [OBSERVED\*: clock-skew reap incident] |
| A4 | One host is the default deployment; multi-host is possible but not assumed. | [INFERRED: matches single-operator scale] |
| A5 | The operator can maintain one small deterministic tool and a handful of config files, but not a fleet of services. | [INFERRED] |
| A6 | Tasks have very unequal verifiability: code with tests is strongly checkable; design intent and prose are weakly checkable. | [OBSERVED\*: B5's doc gate is a structural checklist, the code gate is a real oracle] |
| A7 | Models in the pool differ in capability and failure modes, and vendor behaviour changes without notice. | [CONSENSUS] |
| A8 | The human is a scarce, high-latency resource and can be absent for days. | [stated in brief] |

**Non-goals.** No live inter-agent chat protocol; no reliance on any single model being trustworthy; no multi-human governance; no claim of formal correctness.

---

## 3. Design objectives and optimisation priorities

The brief gives three primary objectives. I treat them asymmetrically, because they are not symmetric in what they can be traded for:

- **Correctness and auditability are floors, expressed as invariants (§8.3).** A design that raises autonomy by silently weakening either is rejected. Where autonomy and a floor conflict, the floor wins and the conflict is surfaced as a design defect to fix (usually by adding an oracle or narrowing scope), not resolved by asking the human every time.
- **Autonomy is the quantity maximised subject to the floors.** Operationalised as *human interrupts and human minutes per unit of accepted, verified progress*, subject to a ceiling on post-acceptance defect escape rate (§27).
- **Recoverability is a property of every mechanism**, not a separate feature: each mechanism in this report names what it catches, what it cannot, and how failure recovers.

Secondary priorities, in the order I let them break ties: safety/security, portability and model independence, cost, throughput, implementation simplicity, elegance.

---

## 4. Research and synthesis methodology

1. Read all supplied proposals and both live-system reports; extracted mechanisms into a table (mechanism, source, purpose, failure addressed).
2. Treated the two live-system reports as the only evidence with an operating history, and mined their **failure→fix records** (architecture report §12; replication manual §11) for *root causes*, not for the fixes chosen.
3. Treated proposal convergence as a weak prior and looked specifically for (a) points where proposals disagree, (b) points where every proposal is silent, and (c) points where the live system contradicts the proposals.
4. Evaluated each mechanism on the template in §5. Where evidence is insufficient, said so and named the experiment (§34).
5. Added standard distributed-systems and verification practice as *background reasoning*, labelled [INFERRED]. Background works I am relying on from memory and have not re-verified here: lease and fencing-token designs (Gray & Cheriton's leases; Kleppmann's critique of unfenced locks), event sourcing, merge-queue CI practice, mutation testing as a way to estimate test-suite strength. Treat these as pointers, not citations.

**Limits.** Single analyst (me), no replication, no primary data, no execution. The strongest form of the report's claims is "the evidence supports this design over the alternatives *as described*."

---

## 5. Evaluation criteria

Each candidate mechanism is scored qualitatively on:

| Criterion | Question |
|---|---|
| Autonomy | Does it reduce or increase human interrupts? Can it operate unattended for days? |
| Reliability | Which failure does it catch; which can it not catch; does it create a new failure? |
| Auditability | Can an observer reconstruct what happened from files alone? |
| Recovery | What is the automatic recovery path; what is lost? |
| Cost/throughput | Tokens, wall-clock, serialisation points. |
| Operational burden | What must the single operator maintain? |
| Evidence | Tag basis: observed, consensus, inferred, speculative. |

I do not aggregate these into a score. §7 gives verdicts with reasons and conditions.

---

## 6. Comparative assessment of the supplied architectures

### 6.1 The architectures compared

| Label | Source | Character |
|---|---|---|
| **ADD-PMS** | `01`, `02` (a synthesis of 21 proposals) | Paper design; git-commit claims, three verification rungs, optional EVM, decision register, human promotion gate for high risk. |
| **ADDPMS-Grok** | `ADDPMS-Unified-Synthesis.md` | Lighter second synthesis; risk-classed verification table, YAML task register, single-commit claim. |
| **B5-live** | architecture report + replication manual | Operating system, ~8 days of history per the manual: boot contract, file claims, heartbeats, patterns, autonomous promotion by gate. |
| **TAPMS** | `autonomous-llm-project-management-system-proposal.md` | Sole proposal grounded in a prior human-run corpus; promotion rule and append-only decisions. |
| **Heavy ladders** | RepoPM (Deepseek v4 Pro), SPARC-PM (GLM) | 4–5 rung verification, detailed schemas, overseer interface capabilities. |
| **Deterministic control** | Deepseek, Gemini 3.8 Flash, GLM (partly) | Control flow in code, LLM only for generative nodes. |
| **Skeptical evidence framing** | Perplexity APDMS, Astra | Evidence grades, "proposals are not decisions", token-volume ≠ progress. |

### 6.2 Where they agree [CONSENSUS], and how much that is worth

Repository as durable record; untrusted-by-default workers; quarantine rather than delete; risk-tiered autonomy; capability-based routing with cross-provider verification; sandboxed execution; provenance on every artifact; append-only decision record; replaceable overseer role. These survive largely intact (§7). Because every proposal answered the same brief and shares training, agreement here is best read as "nobody found a reason to disagree," not as validation.

### 6.3 Where they disagree, and my resolution

| Dispute | Positions | Resolution and basis |
|---|---|---|
| **Claim mechanism** | Git commit as lock (TAPMS, ADD-PMS); `O_EXCL` file (B5-live); lock file + jitter (Perplexity/Nova); lease with heartbeat (RepoPM) | Kernel-issued **lease with fencing token** (§13). The other mechanisms make correctness depend on reaping being right; B5 shows it was not (wrongful reap from clock skew, orphaned claim files, empty claim files) **[OBSERVED\*]**. |
| **Substrate** | Repo/filesystem as message bus (all) vs. any database | Layered: Git for artifacts, kernel event log for coordination, generated views (§8). Evidence: B5's coordination failures cluster in the Markdown ledger and shared tree **[OBSERVED\*]**. |
| **Verification depth** | 2 states (Dola, Recall) vs 3 rungs (ADD-PMS) vs 5 (SPARC-PM) | Neither count matters; **verifier class matters** (§17): oracle > provenance-mechanical > independent adversarial > sampled audit > human. Rung counts were a proxy for this. |
| **Promotion authority** | Human gate for high risk (TAPMS, ADD-PMS) vs autonomous by gate, human only for dependencies (B5-live) | Risk-classed by reversibility and blast radius (§15, §19). B5's stance works because most B5 work is code with a real oracle; it does not generalise to prose or design without an oracle. |
| **EVM** | Mandatory (Deepseek, Nova, GLM) vs optional (ADD-PMS) vs actively misleading (Perplexity) | Reject as core. Keep an *escape-adjusted yield* metric (§27). Basis: Perplexity's objection (token volume is not value) is unrebutted in the corpus. |
| **Liveness** | TTL only vs three-signal (B5 adopted B5-0659) | Three-signal is better than TTL **[OBSERVED\*]**, but signals should be *kernel-observed*, not agent-reported (§13.4). |
| **Ledger** | Markdown table (B5, most proposals) vs YAML/JSON register (ADD-PMS, Nova) | Neither: an event log with generated views. B5's own tooling grew to compensate: `ledger-query`, `run-dup-census`, `census-crosscheck`, pipe-count rules **[OBSERVED\*]**. That tooling is the Kernel trying to exist. |
| **Pattern store** | Advisory store (B5, TAPMS) vs none | Keep, but add promotion-by-evidence and expiry; unbounded advisory stores drift (60 namespaces, identity fragmentation, boot-skim cost) **[OBSERVED\*]**. |
| **Model pool** | Registry of ~130 vs small active subset | Active subset with reserve (Deepseek, GLM, ADD-PMS). [CONSENSUS] |

### 6.4 Where every proposal is silent or weak

1. **Who verifies the verifier.** Nearly all say "different provider." None measures whether the verifier catches errors. (ADD-PMS asks the question in §28 and leaves it open.) → planted-defect canaries (§18).
2. **What stops runaway self-seeding.** B5 added an opt-in, default-off seeding budget only late (B5-0900) **[OBSERVED\*]**. → §11.
3. **Overseer failure as a first-class scenario.** Mostly "replaceable role." → §9.
4. **Silence.** Distinguishing "nothing happened" from "nothing was reported" is addressed by B5's heartbeat work but only after several failures **[OBSERVED\*]**. → §24.
5. **Human effort accounting.** Everyone says "minimal human"; nobody defines a budget or a defect signal for it. → §23.

### 6.5 Contradictions inside the evidence

- The strongest anti-fabrication rule in the corpus ("detail, length or repetition confers no authority") is stated by TAPMS and B5 alike, yet B5's *documentation gate* checks structure and provenance, not truth **[OBSERVED\*]**. The rule protects promotion; it does not detect a well-formed falsehood. Section §17 exists to close that gap as far as it can be closed.
- The B5 architecture report presents a Python doc-gate as "reference implementation." The manual describes doc-only gates as "stated checklist in the task row." It is unclear which is actually running. Treated as unresolved.

---

## 7. What survives, what is rejected, and why

| Mechanism | Verdict | Tag | Reason |
|---|---|---|---|
| Repo as durable record | **Adopt, narrowed**: Git for artifacts and decisions only | INFERRED | Git is overloaded when it also carries mutable coordination state. |
| Boot contract | **Adopt, machine-issued** | OBSERVED\*/INFERRED | Cold-boot discipline works; hand-reading 11 steps every session is a failure surface. Kernel issues a signed briefing. |
| Authority by location + status | **Adopt, kernel-enforced** | CONSENSUS | Location alone can be changed by any writer; the Kernel must own the status field. |
| Immutable provenance in front matter | **Adopt, kernel-derived** | OBSERVED\* | Assessor bloat (35 entries for 7 facts) forced a compaction rule; provenance should be recorded by the Kernel and rendered into front matter. |
| Atomic claim files with TTL | **Replace** with leases + fencing | INFERRED | §13. |
| Markdown ledger as database | **Replace** with event log + generated view | INFERRED | §6.3. |
| Single `DECISIONS.md` | **Replace** with per-entry hash-chained files + generated index | INFERRED | Tail contention and a ~7,900-line file **[OBSERVED\*]**. |
| LLM-written close-out report | **Modify**: kernel-generated receipt from evidence bundle; LLM adds narrative and lesson | INFERRED | False completion is cheap when the report is prose. |
| Three-signal liveness | **Adopt, kernel-observed** | OBSERVED\* | §13.4. |
| Reap by clock comparison | **Reject** | OBSERVED\* | Kernel clock only; fencing makes wrong reaps safe. |
| Shared working tree | **Reject beyond a handful of workers** | OBSERVED\*/INFERRED | Scope violations and gate collisions. |
| Cross-provider verifier | **Keep as necessary, not sufficient** | CONSENSUS | §17. |
| 3/4/5-rung ladder | **Replace** with verifier classes by evidence type | INFERRED | §17. |
| Pattern store (advisory) | **Adopt with promotion-to-check and expiry** | OBSERVED\*/INFERRED | §25. |
| Self-seeding | **Adopt, budgeted and goal-linked** | OBSERVED\* | §11. |
| EVM | **Reject as core** | INFERRED | §6.3. |
| 8-step human promotion | **Keep for R3/R4 only** | CONSENSUS | §15. |
| Singleton documentarian | **Adopt the role, reject the single point of failure** | INFERRED | Second-reader/auditor pass (§9). |
| Process profile (`docs\|research\|game\|docs+code`) | **Adopt** | CONSENSUS | Cheap tailoring. |
| Condensed HANDOFF document | **Reject** | OBSERVED\* | B5 itself superseded it (B5-0626) because it drifted from governance. |
| Java/JDK-specific rules | **Context-specific**, expressed as per-project gate config | OBSERVED\* | Not architecture. |

---

## 8. Core architectural model

### 8.1 Six planes

```
┌───────────────────────────────────────────────────────────────────────┐
│ HUMAN PLANE      decision queue · envelopes · audit sampler ·         │
│                  status page · stop-the-line                          │
├───────────────────────────────────────────────────────────────────────┤
│ INTENT PLANE     goals → requirements → invariants → acceptance oracles│
├───────────────────────────────────────────────────────────────────────┤
│ COORDINATION     KERNEL (deterministic): leases · fencing · scopes ·   │
│ PLANE            status transitions · promotion records · event log   │
│                  ←→ LLM OVERSEER (plans, adjudicates, writes)         │
├───────────────────────────────────────────────────────────────────────┤
│ EXECUTION PLANE  Harness (deterministic wrapper) + sandboxed workers  │
├───────────────────────────────────────────────────────────────────────┤
│ ASSURANCE PLANE  oracles · independent review · canaries · sampling · │
│                  sentinel invariants · auditor overseer               │
├───────────────────────────────────────────────────────────────────────┤
│ KNOWLEDGE PLANE  facts · assumptions · decisions · patterns ·         │
│                  incidents · generated briefings                       │
└───────────────────────────────────────────────────────────────────────┘
         stores: Git (artifacts) │ Event log (coordination truth) │ Views
```

### 8.2 Three stores

| Store | Holds | Authority | Written by |
|---|---|---|---|
| **Git** | Artifacts, code, per-decision files, snapshots of the event log | Content history. *Not* coordination authority. | Kernel (merges), workers (in isolated worktrees) |
| **Event log** | Every state transition, hash-chained, kernel-clocked | Coordination authority | **Kernel only** |
| **Views** | Ledger, status, queue, dashboards, briefings | None. Regenerable. | Kernel generator |

**Why not "just Git."** [INFERRED] Git gives atomic ref updates on one remote and excellent content addressing. It gives poor semantics for leases, expiry, monotonic counters and concurrent status edits. Using it for both is the overload the brief asks about. **Why not "just a database."** A database alone loses git-native diffability and makes forensic reconstruction depend on the database file's survival; keeping a hash-chained JSONL export in Git addresses both.

### 8.3 Invariants (the floors)

Each is checkable by the sentinel (§20) without an LLM.

| ID | Invariant |
|---|---|
| I1 | The event log is append-only and its hash chain verifies. |
| I2 | Only the Kernel appends events; agents hold no write path to the log. |
| I3 | **Conservation:** every task ever created is in exactly one state; counts are conserved across transitions (detects truncation and lost rows). |
| I4 | At most one lease per task carries the current fencing token; submissions with stale fences are quarantined, never merged. |
| I5 | Nothing enters canonical without a promotion event referencing a passing evidence bundle and the promoting policy version. |
| I6 | Every DONE task has an evidence bundle whose hashes match the committed outputs. |
| I7 | Kernel timestamps are the only trusted time. |
| I8 | Kernel code, policy and gate definitions are hash-pinned; changing them requires a two-key event (§28). |
| I9 | No artifact is deleted; supersession and quarantine only. |
| I10 | Every accepted claim of fact is linked to evidence or explicitly marked as assumption. |
| I11 | Contested artifacts propagate a `contested` flag to dependents. |
| I12 | Every human queue item has a safe default and a blocked-set. |
| I13 | Generated views equal the projection of the log (any diff is a sentinel finding). |
| I14 | Silence is an event: expected heartbeats/renewals that do not arrive are recorded. |

---

## 9. Persistent overseer design

### 9.1 Two components, one role

| Component | Type | Powers | Cannot |
|---|---|---|---|
| **Kernel** | Deterministic program (small, tested, hash-pinned) | Owns all coordination state; issues/renews/revokes leases; runs merge queue; computes liveness verdicts; enforces policy; generates views and briefings; writes the event log | Make judgments about content |
| **LLM Overseer** | Persistent LLM session (OpenCode today) | Decomposes goals, writes task cards, prioritises within policy, adjudicates conflicts, writes summaries, proposes process changes | Write coordination state directly; change kernel/policy/gates; approve R3/R4 promotions; act outside kernel-issued tools |

**Replaceability.** [CONSENSUS→INFERRED] The Overseer interface is *the Kernel's API plus the briefing format*. Any agent able to read a briefing and call `pmk` can be the Overseer. OpenCode-specific behaviour is confined to an adapter. Because the Kernel holds all state, replacing the Overseer mid-run loses nothing but conversation context.

### 9.2 Overseer loop (bounded, resumable)

```text
loop:
  brief = pmk brief --role overseer          # kernel-generated, signed, current
  if brief.incidents: handle(incident) ; continue
  for item in brief.plan_gaps:   propose_tasks(item)        # goal-linked, budgeted (§11)
  for item in brief.conflicts:   adjudicate(item)            # §22
  for item in brief.proposals:   review(item)                 # process proposals
  pmk digest --write                                         # human digest, if due
  pmk heartbeat --role overseer --state idle|busy
  sleep_or_wait(brief.next_wakeup)
```

Every Overseer action is an API call that becomes an event. If the Overseer crashes, the sentinel notices its heartbeat gap (I14); restarting means fetching a fresh brief.

### 9.3 Overseer error, corruption, and independent checks

An Overseer that is wrong is more dangerous than a worker that is wrong because it holds broader authority. Controls:

1. **Bounded authority.** It cannot promote R3/R4, change policy/gates/kernel, expand its own envelope, or delete anything. [INFERRED]
2. **Sentinel.** A deterministic invariant checker runs on a timer and at each promotion; its findings cannot be suppressed by the Overseer.
3. **Auditor pass.** A *different* LLM instance, given only the event log and the evidence bundles (not the Overseer's reasoning), periodically re-derives what happened and flags disagreement with the Overseer's narrative and decisions. Disagreement freezes promotion of the affected class until adjudicated. [INFERRED; unmeasured effectiveness]
4. **Decision sampling.** A random sample of Overseer adjudications is re-adjudicated blind by another agent; the agreement rate is a tracked metric (§27).
5. **Succession.** The Overseer role can be revoked by the Kernel on sentinel or auditor findings; a new session takes over from the brief.

**What this cannot catch.** A systematically mis-calibrated Overseer whose errors are undetectable to an equally mis-calibrated auditor. Mitigation is diversity of model family and prompt for the auditor, canaries, and human audit sampling.

---

## 10. Worker-agent architecture

### 10.1 Harness-mediated workers

Workers do not touch coordination state. Every worker session runs inside a **Harness** (deterministic wrapper, part of the Kernel package) that:

1. calls `claim`, receives the work order, creates the isolated worktree;
2. enforces sandbox, tool allowlist, network policy, token and time budgets;
3. logs every tool call and file write (feeding liveness and audit);
4. emits heartbeats with a **progress digest** (files changed, tests run, tokens used);
5. collects the **evidence bundle** at submission;
6. submits, or on crash/timeout records the exit and quarantines the workspace.

The LLM only produces content and tool requests. [INFERRED; CONSENSUS on "deterministic orchestration"]

### 10.2 Worker roles

| Role | Output | Notes |
|---|---|---|
| Implementer | patch + tests + evidence bundle | code or docs |
| Researcher | evidence records with anchored quotes | sources cached |
| Verifier | verdict + falsification attempts | blind to author's rationale |
| Adjudicator | ruling on conflict | cannot be author of either side |
| Gardener | maintenance, consistency sweeps, dependency hygiene | R0/R1 by default |
| Synthesizer | merged candidate from parallel drafts | must list unresolved disagreement |

### 10.3 Task contract

Every task is a machine-readable card (§31 schema) with: objective, **scope**, **acceptance oracle(s)**, evidence requirements, risk class, budget, stop conditions, **premise assertions**.

**Premise check first.** [OBSERVED\*+INFERRED] B5 closed tasks as VOID when their premise was false (B5-0314, B5-0751) **[OBSERVED\*]**. Making this a mandatory first step (verify listed premises against the tree; if any is false, submit a `premise-refuted` result with evidence) is cheap and prevents work on stale tasks.

### 10.4 Heterogeneous capability

Each worker has a **capability card** (§12) and is assigned tasks by fit and by measured performance, not by brand. Tasks are written so weaker models can succeed on bounded slices; hard tasks are decomposed or routed to stronger models, with oracles deciding whether it worked.

---

## 11. Task decomposition and scheduling

### 11.1 Decomposition

Goals → requirements → tasks, each level linked. A task is admissible only if it has:

1. a goal or invariant it serves (or a defect it repairs),
2. a runnable or reviewable acceptance oracle,
3. a scope declaration,
4. a budget,
5. an idempotent starting state (base commit).

The brief's question about "effectively unlimited possible tasks" is answered by admission control, not by trying to prioritise everything.

### 11.2 Controlling runaway self-work [INFERRED; OBSERVED\* motivation]

- **Seed budget per epoch** (e.g. per day), by class. B5's seeding branch is default-off with an explicit invocation cap **[OBSERVED\*]**; here that becomes policy, not per-run flag.
- **Goal linkage required.** A self-seeded task with no goal/defect/invariant reference is rejected by the Kernel.
- **Marginal-value check.** If the last N tasks closed in an area produced no change in any tracked outcome metric, new tasks in that area require Overseer justification and lower priority (stagnation detector, also observed as a concept in B5's "stagnation-excluded" seeding **[OBSERVED\*]**).
- **Duplicate suppression.** Kernel compares new task cards to open/closed cards by scope + objective similarity and flags near-duplicates.
- **Depth limit.** Tasks seeded by tasks seeded by tasks are capped.

### 11.3 Scheduling

```text
score(task) = goal_weight × urgency × unblock_factor × risk_reduction
              ─────────────────────────────────────────────────────────
                    expected_cost × (1 + contention_penalty)
+ aging bonus (prevents starvation)
+ priority lanes (P0 incident preempts; §23)
```

- **WIP limits** per role and per scope group. [CONSENSUS]
- **Conflict-aware:** the Kernel avoids co-scheduling tasks whose write scopes overlap; with isolated worktrees, overlap is an efficiency problem, not a corruption problem.
- **Rate-limit aware:** provider token buckets (§30).
- **Human sets goals and weights only**; task ordering is not a human decision.

### 11.4 Task state machine

```
PROPOSED ──(admit)──▶ READY ──(claim)──▶ LEASED ──(submit)──▶ SUBMITTED
                        ▲                   │                     │
                        │                   │(reap/abandon)       ▼
                        └───────────────────┘              VERIFYING
                                                         ┌────────┴────────┐
                                                    (pass)│              (fail)│
                                                         ▼                     ▼
                                                   INTEGRATING ──(green)──▶ DONE      REWORK ─▶ READY
                                                         │(red)
                                                         ▼
                                                      REWORK
Any state ──▶ BLOCKED(reason) | VOID(premise refuted, evidence) | SUPERSEDED | CONTESTED
```

---

## 12. Agent selection and model routing

### 12.1 Capability cards

```yaml
model_id: provider/model@resolved-version
capabilities: {long_context: true, tool_use: true, code: medium, structured_output: high}
constraints: {data_classes_allowed: [public, internal], cost_tier: 2}
measured:        # per task class, from ORACLE outcomes, with sample sizes
  - {task_class: refactor_small, n: 41, oracle_pass: 0.83, escape_rate_90d: 0.05}
  - {task_class: claim_verification, n: 60, planted_defect_catch: 0.71}
provenance_of_measurement: kernel-computed
```

Measurements derive from oracle outcomes and canaries, **not** from model self-report. Self-reported confidence is recorded only as a feature whose calibration is itself measured.

### 12.2 Routing policy

1. Filter by constraints (data class, tools, context, availability, rate limit).
2. Score by posterior estimate of oracle-pass probability per task class (Beta/Thompson sampling), adjusted for cost.
3. Reserve an exploration fraction for uncalibrated models on low-risk tasks with oracles.
4. **Cheap-first cascade:** try a cheaper capable model; on oracle failure, escalate to a stronger one; escalation history is recorded.
5. **Verifier selection** maximises *independence and measured catch-rate*, excluding authors (§17.3).
6. **Fallback chain** on provider failure; if none eligible, task stays READY and appears in the status page (fail safe, not fail silent).

### 12.3 Preventing metric gaming (Goodhart) [INFERRED]

- Workers are not shown their scores or the audit sampling schedule.
- Metrics come from oracles, canaries and delayed defect-escape measurement, not from worker statements.
- Audit sample selection uses a kernel-held secret seed.
- Multiple metrics are tracked so that gaming one degrades another visibly (e.g. pass rate vs. escape rate vs. rework rate).

### 12.4 Active subset

Maintain a small active subset (roughly 10–20 models) with the full registry as reserve. Maintaining live adapters for ~130 is a maintenance cost the operator cannot bear **[CONSENSUS]**.

---

## 13. Claims, leases, concurrency and repository coordination

(covers brief items 13 and 14)

### 13.1 Why replace file claims

B5's protocol: "creating the claim file is the lock; TTL 30 minutes; reap after three-signal staleness" **[OBSERVED\*]**. Its incident record includes: claim files left behind after close-out (task looks permanently taken), empty claim files, placeholder/midnight `started_utc`, claims on already-closed rows, a live 12-minute-old claim reaped as 12 hours stale because of clock error, and a second session writing under the same identity after the first released **[OBSERVED\*]**. In every case the correctness of the system depended on an agent-written file being accurate and a reaper being right.

### 13.2 Lease protocol with fencing [INFERRED]

```text
claim(task, actor):
    require task.state == READY
    require no conflicting WRITE scope lease (advisory; see §13.5)
    fence  = kernel.next_fence()                 # global monotonic integer
    lease  = {id, task, actor, fence, granted_at, ttl, renew_every}
    workspace = git worktree add work/<task>/<fence> from base_commit
    append_event(LEASE_GRANTED, ...)
    return work_order(lease, workspace, capabilities_token)

renew(lease, progress_digest):
    if lease.fence != task.current_fence: return REJECTED(stale_fence)
    record progress; extend expiry; append_event(LEASE_RENEWED)

submit(lease, bundle):
    if lease.fence != task.current_fence:
        quarantine(bundle, reason="stale_fence")     # retained, reviewable, never merged
        append_event(LATE_SUBMISSION_QUARANTINED)
        return REJECTED
    append_event(SUBMITTED); enqueue_verification(task, bundle)

revoke(task, reason):                                # reap, preempt, incident
    task.current_fence = kernel.next_fence()         # invalidates old holder
    append_event(LEASE_REVOKED)
    task.state = READY (or BLOCKED after N attempts)
```

**Key property.** Once revocation bumps the fence, a slow or partitioned worker cannot corrupt anything: its submission is quarantined. Wrongful reaping costs wasted work, not correctness. [INFERRED from standard practice]

### 13.3 Slow versus abandoned versus livelocked

The kernel computes a liveness verdict from **kernel-observed** signals only:

| Signal | Source |
|---|---|
| S1 process supervision | Harness reports process alive/exited (exit is a positive fact) |
| S2 heartbeat with progress digest | Harness-emitted at `renew_every` |
| S3 workspace activity | File mtime/diff growth, tool-call log |
| S4 token/stream activity | Provider stream metrics |

| Verdict | Condition | Action |
|---|---|---|
| **LIVE-PROGRESSING** | S1 alive and S2/S3/S4 showing change within window | none |
| **LIVE-STALLED** | S1 alive, heartbeats arrive, no progress for N windows | soft-preempt: ask worker to submit or abandon; then revoke |
| **SILENT** | S1 unknown/absent and no heartbeat for k × cadence | record `silence` event; wait grace period |
| **DEAD-CONFIRMED** | S1 reports exit, or SILENT beyond 3× cadence | revoke, quarantine workspace, salvage partial output |
| **UNKNOWN** | required signal unavailable (e.g. harness down) | never reap on UNKNOWN; escalate to sentinel |

This keeps B5's rule that *UNKNOWN is never STALE* **[OBSERVED\*]** and its three-signal insight, but removes agent-authored signals and agent clocks.

### 13.4 Collision handling

| Collision | Handling |
|---|---|
| Two claims for one task | Impossible: kernel serialises; second gets `TASK_TAKEN`. |
| Same identity in two sessions | Identity is a **session-qualified id issued by the Kernel** (rules R1–R6 of B5-0785 become kernel behaviour **[OBSERVED\*→INFERRED]**); the pair (agent, session) is the actor. |
| Two workers, overlapping scopes | Isolated worktrees; conflict discovered at merge queue; the later submission rebases or is returned with the conflict as evidence. |
| Duplicate task IDs | IDs allocated by the Kernel only. Duplicates cannot be created by agents. |
| Crash mid-write | Kernel event append is atomic (single-writer under lock, fsync, hash chain); tail validated on restart. |

### 13.5 Scopes and isolation

- **Scope hints** (hierarchical path/section locks) reduce wasted parallel work but are *advisory*; correctness does not depend on them.
- **Undeclared writes** are detected at submission by comparing the diff to declared scope; violations quarantine the submission with the diff.
- **Merge queue.** Verified submissions are integrated serially: rebase onto current integration head → run gate (fast pre-gate plus full gate as configured) → fast-forward on green. This makes "gate green" mean "green on the exact tree that becomes canonical," closing the time-of-check/time-of-use gap of gating on a shared tree. Speculative batching of independent changes is a later optimisation. [INFERRED from B5 shared-build-output and scope-violation incidents **[OBSERVED\*]**]
- **Per-claim scratch output.** Build outputs go to per-claim directories; the B5 architecture report calls shared build output "the most underrated scaling defect" **[OBSERVED\*]**.

### 13.6 Answers to the brief's coordination questions

| Question | Answer |
|---|---|
| Is repo-as-message-bus sufficient at frontier scale? | Sufficient for a handful of workers with discipline **[OBSERVED\*: the B5 range of ~5–10 is claimed]**. Not sufficient beyond, mainly because of text-table state and shared tree. Repo remains the artifact and decision store. |
| Filesystem/Git only, or a durable event/state system as well? | Both, layered (§8.2). |
| Is Git overloaded? | Yes when it doubles as lock service and ledger. |
| What is authoritative? | Event log for coordination; Git for artifact content; decisions are Git files *anchored* by events. |
| Is atomic Git claiming sufficient at high concurrency? | Push-race retry loops work but add contention and don't provide expiry or fencing. Supplement/replace with leases. |
| Leases/locks/transactions/CAS? | Leases with fencing tokens; kernel-serialised transitions provide the transaction semantics. |

### 13.7 Multi-host

Default: single-host kernel, CLI over a Unix socket. Multi-host: the Kernel exposes the same API over an authenticated channel; workers on other hosts use it identically. SQLite over network filesystems is *not* recommended (unreliable locking) **[INFERRED]**. Replicating the Kernel itself (consensus) is deferred (§32).

---

## 14. Repository layout

Covered by §13 and §31. The compact rule: **projects keep their normal Git tree; coordination lives under `.pm/`; nothing under `.pm/` is edited by hand or by workers.**

---

## 15. Authority and promotion model

### 15.1 Authority

Authority derives from **kernel-recorded status** and location-consistent placement, never from length, repetition, recency, filename, confidence, or model prestige [CONSENSUS; the strongest single rule in the corpus, TAPMS/B5]. The Kernel refuses status changes without the required event chain.

### 15.2 Statuses

Artifact: `draft → submitted → verified → provisional → settled → superseded/archived`, plus `quarantined` and `contested` as side states.

**Provisional promotion with probation** [INFERRED]. For work without a strong oracle, promotion goes to `provisional`: usable, marked as such, with a revalidation window (fixed period plus dependent-usage triggers). It becomes `settled` only after the window passes with no contradiction or audit finding. Consumers (for example doc-first code tasks) can require `settled` inputs, replacing binary "the docs are done" with a per-section readiness state (adopting B5's readiness-contract idea **[OBSERVED\*]**).

### 15.3 Promotion classes

| Class | Definition | Examples |
|---|---|---|
| **R0** | Trivially reversible, internal, no consumers | typo, index regeneration |
| **R1** | Internal, reversible, low blast radius | draft prose, non-mainline branch work |
| **R2** | Canonical internal content, reversible by revert | mainline code with tests, spec text |
| **R3** | Externally visible, hard to reverse, policy/kernel/gate change, new dependency, spend beyond envelope, data-class change | publish, deploy, dependency add, policy edit |
| **R4** | Legal/safety/financial/irreversible | anything with real-world side effects |

### 15.4 Who can promote what

| Class | Evidence available | Decision |
|---|---|---|
| R0 | V0 | Kernel auto |
| R1 | V0 + V1 if oracle exists | Kernel auto |
| R2 with oracle | V0 + V1 + independent review (V2) for non-trivial | Kernel auto (merge queue) |
| R2 without oracle | V0 + V2 (blind adversarial) | Kernel auto to **provisional**; settle after probation; sampled audit |
| R3 | all available | **Human queue** (or pre-authorised envelope match) |
| R4 | all available | **Human always**; no envelope can cover |

This resolves the ADD-PMS vs B5 fork: B5's "gate green = promote" is right where the gate is a real oracle and reversal is cheap; ADD-PMS's human gate is right where neither holds.

### 15.4a Self-modification

Changes to Kernel code, policy, gate definitions or risk classes are R3 by definition and require a **two-key** event: Overseer proposal **and** human approval (or a pre-registered human delegate policy). The change is first run in **shadow mode** against replayed history (§26). [INFERRED]

---

## 16. Evidence, provenance and epistemic status

### 16.1 Evidence bundle (what "done" means)

```yaml
bundle_id: EB-<task>-<fence>
task: T-0142
fence: 5001
base_commit: <hash>
outputs: [{path, sha256}]
diff_scope_check: {declared: [...], actual: [...], violations: []}
commands: [{cmd, cwd, exit, stdout_hash, stderr_hash, toolchain}]
oracle_results: [{oracle, result, counts}]
sources: [{source_id, retrieved_at, sha256, locator}]
claims: [{claim_id, text, kind: fact|inference|assumption, evidence: [...], quote_anchor?: {source, span, exact_match: true}}]
premise_check: [{premise, verified_by, result}]
budget_used: {tokens, wall_s, cost}
harness_trace_ref: <hash>
```

Completion without a bundle is not completion. The receipt/report is **generated from the bundle** by the Kernel; the worker's prose adds narrative and one lesson but cannot substitute for evidence. [INFERRED; addresses false completion]

### 16.2 Claim status lattice (separate from artifact status)

`asserted → sourced → checked → oracle-verified`, with `contested` and `refuted` as side states. `assumed` is a distinct, visible kind, never silently upgraded.

### 16.3 Mechanical anti-fabrication checks

- **Quote anchoring:** a quoted span must exist verbatim in the cached source at the stated locator (mechanical string match). This catches a common fabrication class cheaply.
- **Citation resolution:** cited source IDs must exist in the evidence store with hashes.
- **Numeric recomputation** where a script can reproduce a figure.
- **Test/exit provenance:** commands and exit statuses are recorded by the Harness, not typed by the worker; "tests pass" prose with no record fails V0.

**What this cannot catch:** a real source misread, a correct quote supporting a wrong inference, or a claim about a source that is not in the store. Those need V2 and V3.

### 16.4 Provenance

The Kernel records who/what/when for every event and renders provenance into front matter (author immutable; assessors compacted as `passes`/`last_pass`, adopting B5-0655 **[OBSERVED\*]**). Agents cannot write assessor entries for others; the Kernel derives them from verification events.

---

## 17. Generation/verification architecture and verification strategy

(covers brief items 17 and 18)

### 17.1 Verifier classes by evidence strength

| Class | Mechanism | Strength | Weakness |
|---|---|---|---|
| **V0 Structural/mechanical** | schema, encoding, links, scope, secrets, quote anchors, hash checks | Deterministic, cheap | Checks form, not truth |
| **V1 Executable oracle** | compile, tests, property tests, reproduction, numeric recompute, type/lint, simulation harness | Strongest; independent of LLM belief | Only as good as the oracle; tests can be wrong or gameable |
| **V2 Independent adversarial review** | blind LLM(s) asked to falsify | Covers what oracles cannot | Correlated error; injection surface; cost |
| **V3 Calibration and sampling** | planted-defect canaries; random deep audits | Measures verifier quality | Costs; statistical, not per-item |
| **V4 Human** | decision queue / audit sampler | Ground truth of last resort | Scarce; slow |

**Rule:** use the strongest available class first; do not substitute V2 for a V1 oracle that could exist. If a task class repeatedly lands in V2-only, the Overseer creates tasks to *build an oracle* for it (a golden fixture, a consistency script, a property test). Over time the fraction of work covered by V1 should rise (§27). [INFERRED]

### 17.2 What counts as independent verification

The brief asks whether model-family diversity is sufficient. It is not. Independence has dimensions, each of which can fail:

| Dimension | How to vary |
|---|---|
| Model family | Different provider/lineage |
| Role/prompt | Adversarial falsifier vs. summariser |
| **Context** | Verifier sees claim + evidence, **not** the author's rationale |
| **Evidence path** | Verifier retrieves/re-derives independently rather than trusting the author's citations |
| Tool path | Oracle instead of judgment |
| Time | Not the same session, no shared scratch |

The Kernel records the declared independence profile of each verification. **Declared independence is not measured independence**; §17.4 measures it.

### 17.3 Verifier selection

Choose verifiers to maximise: (a) difference from the author on the dimensions above, (b) measured catch-rate on planted defects for this task class, subject to (c) cost. Cap consecutive verifications of one author by one verifier (anti-collusion, from ADD-PMS) **[CONSENSUS]**.

### 17.4 Calibrating verification: planted-defect canaries [INFERRED→SPECULATIVE on effectiveness]

The Kernel periodically injects known-defective artifacts (mutated code with a known failing behaviour, a fabricated citation, a subtly false claim with a known contradicting source) into the verification stream, unlabelled. It records whether the verifier caught them.

- Provides a *measured* catch-rate per verifier, task class and independence profile.
- Detects verifier drift after a model update.
- Estimates the fraction of errors of *that kind* likely escaping.

**Limits.** Canaries measure detection of the defect types the operator thought to plant; they say nothing about unknown types. Verifiers might learn to recognise canary style; canary generation must be varied and, where possible, derived from real past defects (mutation of genuine incidents).

### 17.5 When all agents are collectively wrong

No mechanism guarantees detection. The defences, in decreasing strength:

1. **Oracles independent of any LLM belief** (tests from human-authored golden fixtures, reference implementations, external data).
2. **Ground-truth anchors:** human-authored fixtures and canonical references that agents cannot edit.
3. **Canary miss-rate** as an estimate of the blind spot in known categories.
4. **Human stratified audit sampling** weighted toward areas where V1 coverage is low and consensus was unanimous but unverified.
5. **Delayed re-verification:** re-check promoted items after probation with a *different* profile.
6. **Disagreement mining:** unanimous verdicts on high-risk items are not treated as comfort; they trigger a deeper sample.

### 17.6 Verification as bottleneck and attack surface

- **Budgeting:** verification effort is allocated by risk class and by prior catch-rate; low-risk, oracle-covered work gets V0/V1 only.
- **Injection:** artifact contents are treated as data; verifiers run sandboxed, read-only, with no ability to alter the artifact or state; tool grants are minimal.
- **Denial of verification:** if verifiers are unavailable, promotion of classes that require V2 waits; it never silently downgrades.

### 17.7 Testing the system itself

| Test | Purpose |
|---|---|
| Property tests on Kernel transitions (state machine invariants I1–I14) | Kernel correctness |
| **Deterministic replay:** replay event log, compare projections | Log/views agreement |
| **Chaos tests:** kill workers, kernel, overseer, harness at random points; corrupt log tail | Recovery paths |
| Clock-skew and stale-fence tests | Fencing correctness |
| Injection suite against workers and verifiers | Security |
| Canary suite | Verification quality |
| Model-formalisation of the lease/fence protocol (TLA+/Alloy) | Protocol correctness [SPECULATIVE tooling effort, high value] |

---

## 18. (See §17)

The brief separates generation/verification architecture from testing strategy. They are merged in §17 because separating them duplicated the oracle-first argument.

---

## 19. Risk classification and autonomy policy

### 19.1 Classification inputs

`risk = f(reversibility, blast radius, external effect, evidence availability, novelty, data class)`. The Kernel computes a *floor* class from mechanical facts (touches external interface? adds dependency? changes policy? exceeds spend?). The Overseer may raise but never lower it. [INFERRED]

### 19.2 Policy envelopes

The human pre-authorises **envelopes**: bounded ranges within which the system acts without asking.

```yaml
envelopes:
  spend: {per_day: 30, per_task: 3}
  dependencies: {allow: [stdlib, pkg-a>=2], deny: [*]}
  external_effects: none
  autonomy_ceiling: R2
  data_classes_allowed_external_models: [public]
  rollback: {max_auto_revert_depth: 5}
```

Requests inside an envelope proceed; requests outside create queue items (§23). Widening an envelope is itself R3.

### 19.3 Autonomy defaults

| Activity | Default |
|---|---|
| Read, draft, analysis, test generation, R0–R2 with oracle | Autonomous |
| Docs/design without oracle | Autonomous to provisional |
| New dependency, publish, deploy, spend, data egress | Envelope or human |
| Policy/kernel/gate edits | Two-key |
| Anything irreversible/legal/safety | Human |

### 19.4 Emergency interrupts

A P0 lane exists: incident tasks preempt normal work by lease revocation with fence bump. **Stop-the-line** (human or sentinel triggered) freezes promotion, halts new leases, snapshots state, and leaves workers to finish or abandon safely; resumption is an explicit event. Sentinel-triggered stop is limited to invariant breaches (I1, I3, I6, I8) so it cannot be used to stall the system trivially.

---

## 20. Failure detection and recovery, crash/restart/session recovery

(covers brief items 20 and 21)

### 20.1 Failure and recovery matrix

| Failure | Detected by | Catches / cannot catch | Recovery |
|---|---|---|---|
| Worker crash | Harness S1 exit | Catches all process deaths; cannot detect "alive but useless" | Revoke; quarantine workspace; salvage; task READY with attempt count |
| Worker stall/livelock | Progress digest flat | Catches no-progress; cannot judge quality of progress | Soft preempt then revoke |
| Silent worker (harness/host lost) | Missing heartbeats (I14) | Catches silence; cannot tell dead from partitioned | Wait grace, revoke with fence; late output quarantined |
| False completion | Missing/invalid evidence bundle; oracle failure; V2 | Catches unevidenced claims; cannot catch well-evidenced wrong results (→ V2/V3/V4) | Reject to REWORK; log incident; adjust router |
| Duplicate/conflicting work | Merge queue rebase/gate | Catches textual and test-visible conflicts; cannot catch semantic conflicts with no test | Return with conflict evidence; contradiction record if semantic |
| Corrupted shared state | Sentinel I1/I3/I13 | Catches log tampering/truncation, lost rows, view drift | Rebuild from last verified log prefix; restore from Git snapshot; stop-the-line if unresolved |
| Kernel crash | OS watchdog (dead-man switch) | Catches process death | Restart; replay log; tail-validate; leases reconciled by verdict rules |
| Overseer crash | Overseer heartbeat gap | Catches death | New session from brief |
| Overseer wrong | Auditor pass, decision sampling, sentinel | Partial (§9.3) | Freeze class; adjudicate; revoke role |
| Verifier wrong | Canary miss, later escape | Detects measured classes only | Reroute verification; re-verify affected items |
| Incorrect promotion | Escape found later; probation contradiction | Only when contradiction is surfaced | Revert; mark contested; propagate to dependents (I11) |
| Silent data loss | Conservation invariant I3; hash inventory | Catches loss from tracked stores | Restore from Git/event log; incident record |
| Lost context | n/a by design | Nothing depends on a conversation | Regenerate briefing |
| Provider outage | Router health | Catches unavailability | Failover chain; degrade; READY with reason |
| Runaway cost/loop | Budget counters, failure fingerprint repeats | Catches repeated identical failures | Kill lease; block task; queue item if cross-envelope |
| Prompt-injected artifact | Injection suite, policy engine, tool denial | Partial | Deny tool call; quarantine input; incident |

### 20.2 Crash/restart procedure

**Kernel restart:**

```text
1. Locate last event; verify hash chain from last checkpoint; truncate torn tail if any.
2. Rebuild index from log.
3. For every LEASED task: compute liveness verdict from fresh signals
   (harness reconnect, process table, heartbeat files).
4. UNKNOWN → keep lease for a grace window; after grace → SILENT path (fence bump).
5. Regenerate views; compare to previous views (I13); record diffs as sentinel findings.
6. Emit KERNEL_RESTARTED with summary; sentinel runs full invariant sweep.
```

**Overseer/worker session recovery:** a fresh session calls `pmk brief`. The briefing is generated from the log: current goals, open incidents, active leases, conflicts, recent decisions, relevant patterns, and *what was in flight for the role*. No reconstruction from conversation history is needed.

**Long unattended operation:** the status page and event log show elapsed autonomous time, interrupts, incidents, and spend; an external dead-man switch alerts the human only if the Kernel/sentinel themselves stop reporting.

---

## 21. (See §20)

---

## 22. Contradiction and disagreement handling

### 22.1 Detection

- On merge: consistency checks against the claims registry and invariants.
- Nightly sweep: pairwise consistency on claims tagged with the same subject.
- Verifier and worker flags.
- Cross-artifact numeric/formula checks (adopted from ADD-PMS/TAPMS **[CONSENSUS]**).

### 22.2 Representation

A **conflict record** links the two (or more) artifacts/claims, preserves both, and sets `contested` on each; the flag propagates to dependents (I11). Nothing is silently resolved. [CONSENSUS from TAPMS; made kernel-enforced]

### 22.3 Resolution ladder

1. **Executable arbitration:** if a test/oracle can decide, run it.
2. **Precedence:** human ruling > oracle result > settled canonical text > verified claims > proposals > patterns. Recency is *not* a tiebreaker.
3. **Blind adjudication** by a third agent given both sides' evidence, not knowing which is "current."
4. **Human queue** if the conflict touches design intent, R3/R4 effects, or adjudicators disagree; default action = keep both, block dependents, continue elsewhere.

### 22.4 Worker disagreement and false premises

- Parallel drafts (for real design forks) are synthesised with unresolved disagreements listed, not merged away.
- A false task premise ends in VOID with evidence, not a forced completion.
- Disagreement between a verifier and an author, both with evidence, becomes a conflict record; neither is silently overruled.

---

## 23. Human intervention minimisation

### 23.1 The human as a scarce resource

The operator does five things, all low-frequency:

| Surface | Purpose | Cadence |
|---|---|---|
| **Decision queue** | R3/R4 and unresolved conflicts, pre-digested | batched, e.g. daily/weekly |
| **Status page** | One generated page: goal progress, incidents, spend, verified-vs-provisional counts, human-load metric | on demand |
| **Envelopes** | Set/adjust bounds | rare |
| **Audit sampler** | A random handful of accepted items with evidence and one-click "agree/disagree/why" | ~weekly, ~15 minutes |
| **Stop-the-line / rollback** | Emergency | rare |

This is the minimum viable control surface. Reading agent output in bulk is deliberately not a control surface. [INFERRED]

### 23.2 Queue item contract

The Kernel rejects queue items lacking any field:

```yaml
id: Q-0042
class: R3 | conflict | envelope_request
question: "One sentence."
options:
  - {id: A, effect: "...", reversible: true,  cost: "..."}
  - {id: B, effect: "...", reversible: false, cost: "..."}
recommended: A
evidence: [EB-..., D-...]
default_on_timeout: hold          # always the safe/no-op action
timeout: 72h
blocked_set: [T-0210, T-0211]     # what waits on this
unblocked_work_continuing: true
estimated_human_minutes: 3
batchable_with: [Q-0043]
```

### 23.3 Interrupt budget as a design signal

Track human interrupts and minutes per accepted unit and per week. Exceeding a target is treated as a **system defect**: either an envelope is too tight, a task class lacks an oracle, or decomposition puts a human decision inside routine work. The Overseer must propose a structural fix; simply asking the human more often is not an allowed remedy. [INFERRED]

### 23.4 Standing rulings

Human decisions can be stored as scoped **precedents** ("for changes of type X within scope Y, approve"). Precedents must be explicit about scope and expire or require periodic reconfirmation. Over-generalisation from a single ruling is a known risk. [SPECULATIVE → implementable with strict scoping]

### 23.5 Avoiding the human bottleneck

Work that depends on a queue item is blocked, but unrelated work continues (adopting B5's "one blocked item never blocks unrelated work" **[OBSERVED\*]**). Defaults on timeout are always safe, never "approve."

---

## 24. Auditability and forensic reconstruction

### 24.1 Event record

```json
{
 "seq": 88214,
 "prev_hash": "…",
 "ts": "kernel-clock ISO-8601Z",
 "actor": {"kind": "worker", "agent": "model-x", "session": "s-91f3", "role": "implementer"},
 "type": "SUBMITTED",
 "subject": "T-0142",
 "fence": 5001,
 "payload": {"bundle": "EB-T-0142-5001"},
 "policy_version": "p-2026-09-28",
 "kernel_version": "k-0.9.3",
 "hash": "…"
}
```

The chain is signed with a Kernel key unavailable to workers, and periodically committed to Git and pushed to an external remote (tamper-evidence beyond the host).

### 24.2 The brief's reconstruction questions, answered from files

| Question | Where the answer lives |
|---|---|
| What did the system believe was happening? | Projections of the log at `seq = N`; briefings issued (stored) |
| Which agent acted? | `actor` on each event; capability card at the time |
| What did it attempt? | Harness trace (tool calls, commands) |
| What evidence did it use? | Evidence bundle and source store |
| What changed? | Git diff + outputs hashes |
| What verification occurred? | Verification events with class, verifier profile, verdict |
| Why was a decision made? | Decision file (options, evidence, rationale, authority), promotion event |
| What failed? | Incident and quarantine records |
| What recovery occurred? | Recovery events (`LEASE_REVOKED`, `KERNEL_RESTARTED`, replay diffs) |
| Was work lost? | Conservation invariant I3 + quarantine inventory |
| What remains unresolved? | Open conflicts, contested flags, queue, blocked tasks |

No answer depends on a conversation transcript.

### 24.3 "Nothing happened" versus "nothing was reported"

- **Expected-activity contracts:** every lease has a heartbeat cadence; every role has an expected wake cadence.
- **Positive assertions:** heartbeat digests state what is held and what changed ("nothing" is an explicit value, adopting B5's `live_claims: []` insight **[OBSERVED\*]**).
- **Silence events (I14):** absent heartbeats, absent submissions past expectation, absent overseer wakeups are logged as events.
- **Harness-level process events:** exit is observed by the Harness, not reported by the model.
- **External dead-man switch:** an OS-level watchdog alerts the human if the Kernel itself stops emitting.

Cannot detect: a worker that heartbeats and emits plausible progress digests while doing useless work (→ oracles, V2, canaries).

---

## 25. Project memory, institutional learning, and continuous self-improvement

(covers brief items 25 and 26)

### 25.1 Layers

| Layer | Content | Trust |
|---|---|---|
| L0 | Event log | Authoritative history |
| L1 | Canonical artifacts | Status-governed |
| L2 | Decision files | Authoritative, append-only, hash-chained |
| L3 | **Facts registry** (claims with evidence) and **assumptions registry** | Facts require evidence; assumptions are visible and reviewable |
| L4 | Patterns/lessons | Advisory only |
| L5 | Briefings/context packs | Disposable, regenerated |

Keeping assumptions separate from facts prevents the accumulation of "poisoned assumptions": an assumption never becomes a fact by repetition; it needs evidence. [INFERRED]

### 25.2 Patterns: promotion and expiry

B5's pattern store is advisory and read at boot **[OBSERVED\*]**, and grew to ~60 namespaces with identity fragmentation. Changes:

1. **Evidence link:** a pattern cites the incidents/events it generalises from.
2. **Replication rule:** to become a *rule*, it needs ≥2 independent incidents and no counter-evidence.
3. **Convert to check:** a rule should become an executable check (lint, validator, gate) wherever possible; unenforced rules decay.
4. **Expiry and revalidation:** patterns carry a review date; unused or contradicted patterns are archived.
5. **No self-citation as evidence:** a pattern cannot be cited as evidence for a claim.
6. **Conflict handling:** contradictory patterns become conflict records (§22).

### 25.3 Learning from failures

Every incident yields an **incident record** (root cause class, detector that fired, detector that should have, fix, whether an invariant/check was added). The Overseer periodically proposes checks; recurring incident classes without a corresponding executable check are flagged.

### 25.4 Self-improvement as experiments

[INFERRED; the replay part SPECULATIVE until built]

1. Process changes are **proposals with a hypothesis and a metric**.
2. Because the log is complete, a proposed scheduling/routing/claim policy can be evaluated by **counterfactual replay** on historical events (approximate where agent behaviour would differ).
3. Then **shadow mode** (compute decisions, don't act; compare).
4. Then **canary** on a low-risk slice.
5. Adoption via two-key (§15.4a) for kernel/policy; via Overseer for non-critical process.
6. Every change has a sunset review.

**Guard against self-reinforcing bad practice:** adoption criteria are based on oracle/audit metrics and escape rate measured *after* the change, not on agents' opinions of it.

---

## 26. (See §25)

---

## 27. Metrics and feedback loops

| Metric | Definition | Guards against |
|---|---|---|
| **Accepted-verified yield** | settled items ÷ (settled + reverted + contested) per cost | Volume mistaken for progress (Perplexity's objection) |
| **Escape rate** | defects found after promotion, windowed (e.g. 30/90 d) | Weak verification; Goodhart on pass rates |
| **False-completion rate** | tasks reopened after DONE with evidence gap | Report-as-work |
| **Canary catch rate** | per verifier/class/profile | Verifier drift, false comfort |
| **V1 coverage** | share of accepted work covered by an executable oracle | Over-reliance on judgment |
| **Human load** | interrupts/week, minutes/accepted unit | Human bottleneck |
| **Claim health** | collisions, revokes, late submissions, wrongful-reap rate | Coordination defects |
| **MTTR** | incident detection→recovery | Fragility |
| **Contested backlog age** | open conflicts × age | Silent divergence |
| **Stagnation** | tasks closed without outcome-metric movement | Runaway self-work |
| **Cost per verified unit** | tokens/$ per settled item | Runaway spend |
| **Auditor–overseer agreement** | blind re-adjudication agreement | Overseer drift |

Feedback loops: metrics feed routing (12), verification allocation (17), seed budgets (11), envelopes proposals (23), and process experiments (25.4). Metrics visible to workers are limited (§12.3).

---

## 28. Security, sandboxing and least privilege

### 28.1 Threat model

Prompt injection via sources/artifacts/issues; worker attempting out-of-scope writes; credential exposure; poisoned memory; malicious/compromised dependencies; overseer compromise; kernel or log tampering; data exfiltration to model providers.

### 28.2 Controls

| Control | Detail |
|---|---|
| **Sandbox** | Workers run in containers or equivalent; read-only mounts except own worktree; no network by default; allowlisted egress through a logging proxy |
| **Capability tokens** | Kernel-issued, per-lease, scoped, expiring; workers never hold long-lived credentials |
| **Secrets** | Held by the Kernel/harness side only; redaction before model calls |
| **Data classification** | Envelope controls which models may see which classes |
| **Artifact-as-data** | External/artifact text is delimited and never treated as instructions; tool requests derived from it are policy-checked |
| **Hash pinning + two-key** | Kernel, policy, gates, sandbox profiles (I8) |
| **Signed log** | Kernel key outside workers' reach; external remote for anchoring |
| **Dependency gate** | R3; scan and pin |
| **Verifier isolation** | Read-only; cannot mutate artifact or state |
| **Least privilege** | Harness enforces tool allowlists per role |

Residual risk: sandbox escapes, a compromised Kernel host, and provider-side data handling. The design limits blast radius; it does not remove these.

---

## 29. Scalability, throughput, cost, token and rate-limit management

(covers brief items 29 and 30)

### 29.1 Bottlenecks and mitigations

| Bottleneck | Mitigation |
|---|---|
| Gate/merge queue | Fast pre-gate + full gate; affected-test selection; per-claim outputs; speculative batching (later) |
| Kernel serialisation | Event append is cheap; the Kernel is not on any data path, only transitions |
| Overseer context | Kernel-generated briefings; incremental digests |
| Verification | Risk-based allocation; V1 first; sampling |
| Human queue | Envelopes, batching, interrupt budget |
| Decision-log tail | One file per decision |
| Ledger size | Views are projections; the index handles queries |

**Design target [INFERRED]:** on the order of 10–30 concurrent workers on one host with per-claim worktrees and a merge queue. B5's shared-tree design is reported at roughly 5–10 **[OBSERVED\*]**. Beyond ~30, shard by subsystem with per-shard queues and a cross-shard integration protocol [SPECULATIVE].

### 29.2 Cost management

- **Budgets** per epoch, goal, task class, and task; hard caps in the Harness.
- **Cascades:** cheap-first with oracle-triggered escalation.
- **Verification spend** as a policy fraction tuned by escape rate.
- **Retry policy:** each retry must change one variable (model, context, decomposition, tool); the Kernel tracks *failure fingerprints* to detect thrash and blocks after N identical failures.
- **Caching** of retrieval, oracle results (keyed by input hashes), and briefings.
- **Rate limits:** per-provider token buckets in the scheduler; tasks needing a rate-limited provider queue rather than fail.
- **Anomaly detection:** spend spikes and token-per-output outliers raise incidents.
- **Cost accounting stays separate from progress accounting** (no EVM conflation).

---

## 30. (See §29)

---

## 31. Current implementation architecture (buildable with current tooling)

### 31.1 Components

| Component | Implementation | Notes |
|---|---|---|
| **Kernel (`pmk`)** | Single Python (stdlib) program: CLI + Unix-socket server; event log append under `flock`; SQLite index (rebuildable) | ~small; hash-pinned; property-tested |
| **Harness** | Python wrapper around a worker CLI/SDK call; container runner | Reuses OpenCode/other agents as the LLM side |
| **Worktree manager** | `git worktree` per lease | |
| **Merge queue** | Kernel module driving git + gate command | |
| **Gate runner** | Per-project command configuration; tiers | Language-agnostic |
| **Sentinel** | Kernel subcommand on timer; invariant suite | Deterministic |
| **View generators** | Kernel renders Markdown/HTML | ledger, status, queue |
| **Router** | Kernel module: capability cards, posteriors, verifier selection | |
| **Briefing generator** | Kernel renders role-specific context packs | |
| **Watchdog** | OS-level (systemd timer/cron) | Only external dependency |

### 31.2 Directory structure

```
project/
  AGENTS.md                    # short constitution; hash-pinned; points to policy
  .pm/
    kernel/                    # pmk source, hash-pinned (I8)
    policy.yaml                # envelopes, risk floors, gate tiers (hash-pinned)
    events/YYYY-MM-DD.jsonl    # hash-chained, kernel-append-only
    index.db                   # derived, rebuildable, gitignored
    views/                     # generated: ledger.md, status.html, queue.md
    tasks/T-####.yaml          # task cards (kernel-created from Overseer requests)
    evidence/EB-*/             # bundles (bundle.yaml, traces, outputs manifest)
    quarantine/                # late submissions, stale-fence work, failed bundles
    decisions/D-####.md        # per-decision, hash-chained
    conflicts/C-####.yaml
    memory/{facts,assumptions,patterns,incidents}/
    registry/{agents.yaml,models.yaml,scopes.yaml,sources/}
    briefings/                 # generated context packs (disposable)
  docs/ src/ tests/ ...        # normal project tree (Git)
```

### 31.3 Schemas

**Task card**

```yaml
id: T-0142
title: "imperative, specific"
type: implement | research | verify | adjudicate | maintain
goal_ref: G-07                 # required (or invariant/defect ref)
risk_floor: R2
scope: {write: [src/engine/combat/], read: [docs/rules/combat.md#resolution]}
acceptance:
  oracles: [tests/combat/test_resolution.py, gate:full]
  evidence_required: [oracle_results, diff_scope, premise_check]
premises:
  - {id: P1, statement: "docs/rules/combat.md#resolution is settled", check: "pmk status docs/rules/combat.md#resolution == settled"}
budget: {tokens: 120000, wall_min: 45, cost: 2.0}
stop_conditions: [premise_false, scope_violation_needed, budget_exhausted]
depends_on: [T-0139]
attempts: {max: 3}
created_by: {kind: overseer, session: s-17}
```

**Decision file**

```yaml
id: D-0091
subject: "..."
class: R3
options: [...]
chosen: A
authority: human | envelope:<id> | policy:<id>
evidence: [EB-..., C-...]
supersedes: [D-0044]
prev_hash: ...
hash: ...
```

**Human queue** and **event** schemas: §23.2 and §24.1.

### 31.4 Kernel pseudocode (core transitions, condensed)

```python
def claim(actor, task_id):
    with LOG.lock():
        t = state.task(task_id)
        if t.state != "READY": return err("TASK_NOT_READY")
        if not policy.actor_eligible(actor, t): return err("NOT_ELIGIBLE")
        fence = state.next_fence()
        lease = Lease(task_id, actor, fence, now_kernel(), policy.ttl(t))
        ws = git.worktree_add(f"work/{task_id}/{fence}", t.base_commit)
        LOG.append("LEASE_GRANTED", subject=task_id, fence=fence,
                   payload={"actor": actor, "workspace": ws})
        return WorkOrder(lease, ws, capability_token(lease, t.scope), t)

def submit(lease_id, bundle):
    with LOG.lock():
        l = state.lease(lease_id); t = state.task(l.task)
        if l.fence != t.current_fence:
            quarantine(bundle, "stale_fence")
            LOG.append("LATE_SUBMISSION_QUARANTINED", ...); return err("STALE_FENCE")
        r = v0_check(bundle, t)                       # structure, scope, hashes, quote anchors
        if not r.ok: LOG.append("SUBMISSION_REJECTED", ...); return err(r.reasons)
        LOG.append("SUBMITTED", subject=t.id, payload={"bundle": bundle.id})
        enqueue_verification(t, bundle)

def sweep():                                            # timer
    for l in state.active_leases():
        v = liveness_verdict(l)                         # §13.3, kernel-observed signals only
        if v == "DEAD-CONFIRMED":  revoke(l.task, "dead")
        elif v == "LIVE-STALLED":  request_submit_or_abandon(l)
        elif v == "SILENT":        LOG.append("SILENCE", ...) ; maybe_revoke_after_grace(l)
        # UNKNOWN never reaps
    sentinel.check_invariants()

def integrate(task_id):                                 # merge queue
    b = verified_bundle(task_id)
    tree = git.rebase(b.branch, onto=integration_head())
    g = run_gate(tree, tier=policy.gate_tier(b))
    if g.green and policy.promotion_allows(b):          # class/evidence table §15.4
        git.fast_forward(integration_head(), tree)
        LOG.append("PROMOTED", subject=task_id, payload={...})
    else:
        LOG.append("INTEGRATION_FAILED", ...); requeue(task_id, evidence=g)
```

### 31.5 Example lifecycle (abridged)

```
seq  event                          note
101  TASK_ADMITTED T-0142           overseer request; kernel checks goal_ref, budget
102  LEASE_GRANTED T-0142 fence=5001 worker-a (model X, session s-91f3)
103  PREMISE_CHECK ok               P1 settled
104  LEASE_RENEWED ... (x6)         progress digests: 3 files, 12 test runs
109  SUBMITTED T-0142 EB-T-0142-5001
110  V0 PASS ; V1 PASS (gate:fast)  oracle results recorded by harness
111  V2 ASSIGNED to model Y (blind) independence profile: family≠, context blind, evidence path own
112  V2 PASS_WITH_NOTES
113  INTEGRATING → rebase → gate:full green
114  PROMOTED (R2, oracle-covered) decision auto by policy p-2026-09-28
115  RECEIPT generated ; LESSON filed (advisory)
```

Failure variant: at 105 worker host dies → SILENCE at 106, DEAD-CONFIRMED at 108, `LEASE_REVOKED fence→5002`, workspace quarantined; a later submission with fence 5001 is quarantined, not merged.

### 31.6 What this build depends on

Python, SQLite, Git, a container runtime (or documented weaker isolation), a scheduler for the watchdog, and whichever LLM agent CLIs/SDKs the operator already uses. It replaces B5's growth of PowerShell census/validator scripts with one tested program. Effort is real: this is a small software project, not a configuration exercise. [INFERRED; the operator should budget for it]

---

## 32. Frontier and future architecture

| Mechanism | Tier | Why it isn't current |
|---|---|---|
| Replicated Kernel (consensus) for multi-host high availability | Needs better orchestration | Probably unnecessary at one-operator scale; single-host recovery may suffice |
| Formal specification and model checking of lease/fence/merge protocol | Needs tooling effort | High value; skills/time |
| **Counterfactual replay** of policies on historical logs | Needs research | Agent behaviour would differ under the new policy; replay is approximate |
| Learned scheduler/router with off-policy evaluation | Needs research | Bandit baseline first |
| Measured verifier independence (error-correlation matrices across models/prompts) | Needs research | Requires large labelled defect sets |
| Automatic invariant mining from event logs | Research | |
| Proof-carrying evidence (machine-checkable derivations for claims) | Research | Limited to formalizable domains |
| Continuous automated red-team agents attacking the system | Needs tooling | Safety of the red-team itself |
| Hardware-backed attestation/signing for kernel and harness | Tooling | |
| Semantic-conflict detection across accepted artifacts (beyond tests) | Research | Currently mostly LLM-judged |
| Standing-ruling generalisation with learned scope | Research | Over-generalisation risk |
| Cross-project shared memory with poisoning defences | Research | |

---

## 33. Migration path from the current Babylon5 system

Each step is reversible, keeps existing agents working, and has an exit test. [INFERRED]

| Step | Change | Exit criterion |
|---|---|---|
| **M0** | Freeze a snapshot; write the invariants I1–I14 as executable checks against the *existing* files (ledger, claims, heartbeats, decisions) | Checks run read-only; baseline violation counts recorded |
| **M1 Shadow kernel** | Kernel ingests existing ledger/claims/heartbeats/reports into an event store and *mirrors* current state; reports drift. No authority. | Projection matches reality for N days; drift explained |
| **M2 Kernel-owned claims** | Agents claim through `pmk` (thin wrapper preserves the old command names); `CLAIMS/*.json` and `HEARTBEATS/*` become generated views; fencing enabled; kernel identity issuance replaces R1–R6 by convention | Zero orphan/empty claim files; no wrongful-reap incidents over a test period; chaos tests pass |
| **M3 Isolation** | Per-claim worktrees; per-claim gate output; merge queue; gate tiers | Collision rate vs. shared tree measured; B5 gate passes on merged tree |
| **M4 Generated ledger and decisions** | Ledger becomes a generated view; DECISIONS.md split into per-entry hash-chained files with a generated index; reports generated from evidence bundles | Views equal projections; `ledger-query`/`run-dup-census` tools retired in favour of sentinel checks |
| **M5 Assurance** | Sentinel, auditor pass, canaries, blind V2 with independence profiles | Canary catch rates measured per verifier/class |
| **M6 Human surface** | Envelopes, decision queue, audit sampler, status page; interrupt budget | Human minutes/week measured and trending down without escape-rate rise |
| **M7 Self-improvement loop** | Pattern promotion/expiry; proposals with hypotheses; shadow evaluation | First process change adopted via experiment |

**What B5 keeps unchanged:** boot discipline (now machine-issued), authority by location+status, immutable provenance (now kernel-derived), the readiness contract idea, append-only decisions, self-seeding with a budget, the Java gate rules as project gate config.
**What B5 sheds:** hand-edited ledger, hand-maintained claim/heartbeat files, agent-authored liveness, shared working tree, the single decisions file, hand-written status prose as evidence.

**Risk of migration:** the Kernel becomes a new single point of failure and a new thing to get wrong. M1's shadow period exists to test that before granting authority.

---

## 34. Known limitations and unresolved research questions

| # | Limitation | Experiment that would resolve it |
|---|---|---|
| L1 | **Correlated error** between verifiers is unmeasured. Family diversity is not shown to be sufficient. | Planted-defect study across model pairs × prompts × context regimes; compute error-correlation; test whether context-blind/evidence-independent review reduces it. |
| L2 | The **claim that most B5 incidents come from text-state and shared-tree** is my inference from second-hand reports. | Classify all B5 incidents from primary ledgers/reports by root cause; count how many M2–M4 would have prevented. |
| L3 | Whether fencing + per-claim worktrees actually reduce wasted work and collision rates at 10–30 workers. | A/B or simulation with recorded B5 traces; measure collisions, rework, gate wait. |
| L4 | Oracle-availability for design/prose work is inherently limited; **provisional promotion with probation** may just delay undetected errors. | Compare escape rates and human audit findings for provisional-then-settled vs. immediate acceptance; tune probation lengths. |
| L5 | Canary realism: verifiers may detect canary style; canaries miss unknown defect types. | Vary canary generation; compare canary catch rate with real-defect catch rate found later. |
| L6 | The Kernel is a new failure surface and a maintenance burden for one operator. | Track kernel-caused incidents against incidents it prevents; cap kernel size. |
| L7 | Counterfactual replay is approximate because agents adapt to policy. | Validate replay predictions against forward experiments on small changes. |
| L8 | Optimal **human interrupt budget** and audit sample size are unknown. | Vary sampling rate; measure escape-rate detection versus human minutes. |
| L9 | Router posteriors assume task classes are stable; model updates violate that. | Drift detection on canary and oracle streams; measure how quickly posteriors go stale. |
| L10 | Auditor overseer may share the Overseer's blind spots. | Seed known overseer errors (planted adjudication mistakes) and measure catch. |
| L11 | Security: sandbox escape, provider data handling, injection completeness. | Red-team suite; external review. |
| L12 | Pattern-store quality: whether promotion-to-check actually improves outcomes rather than accreting checks. | Track incident recurrence rate vs. check count; prune unproductive checks. |
| L13 | Evidence in the supplied corpus is thin on cost/latency of verification. | Instrument spend per verification class from M5 onward. |
| L14 | Multi-host and beyond-30-worker behaviour is undesigned in detail. | Prototype sharded merge queues; measure. |

---

## 35. Final architecture and implementation roadmap

### 35.1 Summary of the final architecture

```
                     HUMAN: goals · envelopes · queue · audit · stop
                                    │
                    ┌───────────────┴───────────────┐
                    │        LLM OVERSEER            │  plans · adjudicates · narrates
                    └───────────────┬───────────────┘
                                    │ requests only
                    ┌───────────────▼───────────────┐
                    │           KERNEL               │  leases+fences · scopes · merge queue
                    │  event log (hash-chained) ·    │  routing · policy · views · briefings
                    │  sentinel · liveness           │
                    └───────┬───────────────┬────────┘
                            │               │
              ┌─────────────▼───┐     ┌─────▼──────────────┐
              │ HARNESS+WORKERS │     │ VERIFIERS/ORACLES  │  V0 mech · V1 oracle · V2 blind
              │ isolated        │     │ AUDITOR · CANARIES │  V3 sample · V4 human
              │ worktrees       │     └────────────────────┘
              └─────────────┬───┘
                            ▼
                Git (artifacts, decisions, log snapshots)
```

### 35.2 Tiers

| Tier | Contents |
|---|---|
| **Implementable now** | Kernel with event log and generated views; leases and fencing; harness; per-claim worktrees; merge queue; evidence bundles; V0/V1 verifiers; blind V2; task admission control; envelopes and decision queue; sentinel; router with posteriors; briefings; per-decision files; dead-man watchdog |
| **Needs better tooling/orchestration** | Planted-defect canary generator from real incidents; auditor overseer automation; shadow-mode policy evaluation; formal protocol model; robust sandboxing across hosts |
| **Needs research/validation** | Measured verifier independence; counterfactual replay fidelity; learned schedulers; semantic conflict detection; standing-ruling generalisation; multi-shard integration |

### 35.3 Roadmap

| Phase | Deliverable | Exit test |
|---|---|---|
| **P0 (1–2 wks)** | Invariants as read-only checks against B5 (M0); incident classification for L2 | Baseline violation counts; root-cause table |
| **P1 (2–4 wks)** | Shadow kernel + event ingestion (M1) | Drift explained, replay works |
| **P2 (3–5 wks)** | Leases, fencing, harness, kernel identity (M2) | Chaos tests pass; zero wrongful-reap harm |
| **P3 (3–5 wks)** | Worktrees + merge queue + gate tiers (M3) | Collision/gate-wait measured improvement |
| **P4 (3–4 wks)** | Generated ledger/decisions/reports (M4) | Views ≡ projection; old census tools retired |
| **P5 (4–6 wks)** | Sentinel, auditor, canaries, blind V2 (M5) | Canary catch rates recorded |
| **P6 (2–4 wks)** | Human surface and interrupt budget (M6) | Human minutes/week baseline set |
| **P7 (ongoing)** | Self-improvement loop, pattern promotion/expiry (M7) | First experiment-adopted process change |

Durations are guesses [SPECULATIVE], dominated by how much of the Kernel is written by agents under this system's own controls versus by the operator.

### 35.4 Decision summary

1. Keep: boot discipline, authority-by-status, immutable provenance, append-only decisions, evidence-bearing close-out, budgeted self-seeding.
2. Replace: file claims/TTL with leases+fencing; Markdown ledger with an event log plus generated views; shared tree with per-claim worktrees and a merge queue; agent-authored liveness with kernel-observed liveness; rung counts with verifier classes by evidence strength.
3. Add: deterministic Kernel/LLM Overseer split; sentinel and auditor; planted-defect calibration; provisional promotion with probation; envelopes, interrupt budget and audit sampler; conservation invariants; kernel-derived provenance; goal-linked task admission.
4. Reject: EVM as core; mandatory human promotion for routine work; single-host reliance on agent clocks; unbounded advisory pattern stores.
5. State plainly: verification reduces but does not eliminate error; the largest unmeasured risk is correlated failure across all agents, and the experiments in §34 exist to bound it.

---

*Status: candidate-tier proposal by Claude (Claude Sonnet 5.5), 2026-09-30. Unverified by any second assessor. To adopt any element, promote it through the target project's own governance, gate and decision record.*
