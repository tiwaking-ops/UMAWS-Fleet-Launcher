---
audience: "Primary: system designer/operator. Secondary: coding agent
  implementing the approved design."
author: GPT-6 (OpenAI)
companion_documents:
- Ultimate-Multi-Agent-Workflow-System - Claude.md
- proposal-claude-llm-gateway-v1-1.md
date: 2026-10-25
document:
  status: Non-canonical design proposal; not implemented or tested
  title: UMAWS Orchestration Manager with QuotaGate Integration
  version: 0.1
evidence_basis: The two companion proposals/documents and the user's
  design-interview decisions dated 2026-10-25. No implementation,
  framework benchmark, or live capacity test was performed for this
  proposal.
---

# UMAWS Orchestration Manager with QuotaGate Integration

## 1. Status and decision summary

**Status:** Non-canonical proposal. Nothing described here should be
treated as implemented, tested, or promoted into UMAWS policy. The human
designer retains final authority.

**Recommendation:** Build a custom Orchestration Manager as a bounded
orchestration layer integrated with UMAWS. Do not build a second Kernel,
replace the LLM Overseer, or turn QuotaGate into a policy authority. Use
a small custom orchestration core and evaluate framework components
against UMAWS invariants before adopting them.

The proposed division of responsibility is:

-   **Human operator:** defines goals, policy envelopes, hard ceilings,
    and approval requirements; can stop the system and adjudicates
    decisions reserved for human authority.
-   **UMA​​WS Kernel:** sole authority for coordination state, policy
    enforcement, task admission, leases and fencing, budgets, trusted
    timestamps, event history, generated views, and promotion gates.
-   **LLM Overseer:** interprets goals, decomposes work, proposes plans
    and task cards, prioritises within policy, judges evidence,
    adjudicates conflicts, and recommends process changes.
-   **Orchestration Manager:** manages team and subteam lifecycle,
    orchestrator/worker assignment, execution coordination,
    dependency-aware scheduling, bounded parallelism, recovery, and
    result reconciliation. It acts only through Kernel-authorised
    interfaces.
-   **Harness and adapters:** execute worker sessions and external
    orchestrators under isolation, tool/network policy, lease fencing,
    logging, and evidence collection.
-   **QuotaGate:** determines which eligible concrete deployment can
    serve a permitted model request now, enforces hierarchical quota
    rules, reports the model that actually answered, and exposes
    availability/events. It does not decide what model class a task
    deserves.
-   **Verifiers and auditors:** independently test submitted work and
    challenge claims using evidence, oracles, and appropriately
    independent model instances.

The Manager is an orchestration capability within the UMAWS ecosystem,
not an alternative source of truth. The Overseer and Manager may
cooperate closely, but neither may write coordination state around the
Kernel.

### 1.1 Confirmed design decisions

1.  The intended scope is **both** a richer UMAWS Overseer workflow and
    adapters for independent orchestrators, including nested
    hierarchies.
2.  The orchestration engine should be custom with minimal dependencies.
    Frameworks may own parts of agent-execution lifecycle, but must be
    evaluated against UMAWS invariants before selection.
3.  The Overseer owns goal decomposition, planning, judgment, and
    adjudication; the Manager owns team lifecycle, scheduling, execution
    coordination, and recovery; the Kernel remains the sole authority
    over coordination state.
4.  Team creation, resizing, nesting, restart, and retirement are
    dynamic within Kernel-enforced limits. Human approval is reserved
    for actions outside pre-authorised policy envelopes.
5.  The system should support all three worker/orchestrator paths:
    existing coding-agent CLIs, direct LLM execution through QuotaGate,
    and other orchestrators as subordinate teams.
6.  Disagreement handling should combine executable
    evidence/re-verification, diverse adjudicators, stronger-model
    retries when justified, and human escalation, with bounded attempts
    and preserved dissent.
7.  Concurrency is dynamic but constrained by configurable hard
    ceilings.
8.  UMAWS task ledger/event log, leases and fencing, Git/artifact
    workflow, isolated workspaces, and evidence bundles remain the
    durable coordination and evidence model.
9.  The first release includes Overseer integration, bounded dynamic
    teams, at least one existing CLI adapter and one QuotaGate-backed
    adapter, structured evidence-bearing results, failure recovery,
    independent verification, and invariant/integration tests. Nested
    orchestrators and advanced adaptive scheduling can follow after the
    basic contracts are proven.
10. The three primary success criteria are invariant preservation,
    unattended completion within an authorised envelope, and safe
    handling of failures/conflicts without losing work or falsely
    reporting success.
11. **Token consumption is not an optimisation objective.** Correctness,
    reliability, verification, and effective use of available free-model
    capacity take priority. Actual service quotas, request limits, and
    explicit policy ceilings still apply.

### 1.2 Material discrepancy to resolve

The QuotaGate v1.1 proposal describes a catalog of about twelve
permanent free-tier models. The user identifies six permanently free,
strong models as a priority pool for Overseer-guided capacity
allocation. These statements may refer to different subsets (all
permanent free models versus the strong active subset), but this has not
been confirmed. Before implementation, inventory the actual deployments
and label each as verified, unverified, temporary, or permanently free.
Do not hard-code either count as a capacity guarantee.

## 2. Problem statement and goals

A single Overseer can reason about a plan, but large or mixed tasks
benefit from parallel specialist teams, heterogeneous execution systems,
independent verification, and recovery from failed or unavailable
workers. Without a clear orchestration layer, each agent CLI or
framework can develop its own lifecycle state, retry logic, team
hierarchy, and scheduling decisions. That creates duplicate authorities,
hidden work, inconsistent status, and false completion.

The Manager should turn an Overseer-approved plan into a controlled,
observable, resumable execution graph while preserving UMAWS's
deterministic Kernel authority.

### 2.1 Goals

-   Support teams, subteams, multiple orchestrator instances, and
    heterogeneous worker backends through a common contract.
-   Dynamically allocate work and concurrency within explicit
    Kernel-enforced envelopes.
-   Use QuotaGate availability and quota facts to make eligible model
    capacity usable without confusing availability with task policy.
-   Preserve every accepted result, disagreement, failed attempt, and
    recovery action in durable state/evidence.
-   Make the system replaceable and restartable: a new Overseer or
    Manager process can recover from a Kernel-generated briefing and
    durable state rather than relying on a conversation transcript.
-   Use independent verification, not model confidence or orchestration
    success messages, to decide whether work meets its acceptance
    criteria.
-   Keep implementation small enough for a single operator to maintain,
    adding dependencies only when they demonstrably reduce risk or
    effort.

### 2.2 Non-goals for the initial release

-   Replacing the UMAWS Kernel or redefining its invariants.
-   Giving the Manager direct write access to the event log, policy,
    canonical state, promotion gates, or lease records.
-   Allowing an LLM to unilaterally expand its own authority envelope or
    hard concurrency ceilings.
-   Selecting a particular agent framework before a documented
    evaluation.
-   Building a universal adapter for every CLI or orchestrator at
    launch.
-   Guaranteeing throughput from model counts alone.
-   Optimising for minimum token use.
-   Treating a successful worker exit, plausible narrative, or green
    orchestration status as proof of task correctness.
-   Multi-host replicated-Kernel consensus in the first release unless
    deployment requirements later justify it.

## 3. Architectural boundaries

``` text
                         HUMAN OPERATOR
             goals · policy envelopes · approvals · stop
                               |
                               v
                  UMAWS KERNEL (authority)
        policy · task admission · leases/fencing · budgets
       event log · trusted time · views · promotion gates
                 ^            ^              ^
                 | authorised | commands     | evidence/events
                 | proposals  |              |
          +------+-------------+--------------+------+
          |                                         |
          v                                         v
     LLM OVERSEER                           ORCHESTRATION MANAGER
 goals · decomposition                     teams/subteams lifecycle
 plans · judgment                           scheduling and dispatch
 conflict adjudication                      retries/recovery
 verifier strategy                          adapter coordination
          |                                         |
          +------------------+----------------------+
                             |
                             v
                      HARNESS / ADAPTERS
             isolated workers · tool policy · logs
              lease-aware execution · evidence bundles
                    /             |             \
                   v              v              v
          Coding-agent CLIs   QuotaGate API   Subordinate
          via adapters        model calls     orchestrators
                                   |
                                   v
                             Model providers
```

The diagram is conceptual. The actual interface boundary must be the
Kernel API and generated briefing/task contracts already defined by
UMAWS, not a new Manager-owned state database.

### 3.1 Kernel: authoritative control plane

The Kernel remains responsible for deterministic decisions and durable
coordination facts, including:

-   validating task cards and their goal/invariant linkage, acceptance
    oracles, scope, premise assertions, budgets, stop conditions, and
    base commit;
-   admitting or rejecting tasks and team-lifecycle requests under
    policy;
-   issuing, renewing, revoking, and fencing leases;
-   enforcing data-class restrictions, tool/network policy, hard
    concurrency ceilings, budgets, approval gates, and allowed
    operations;
-   recording state transitions, attempts, heartbeat/silence events,
    approvals, conflicts, submissions, verifier outcomes, and final
    dispositions;
-   generating role-specific briefings and views from the event log;
-   preventing a stale worker or orchestrator from submitting work under
    a revoked lease/fence;
-   ensuring a DONE task has evidence whose hashes match committed
    outputs.

The Manager can request a transition; it cannot make the transition
authoritative by writing a file, database row, or message itself.

### 3.2 LLM Overseer: semantic planning and judgment

The Overseer remains the semantic decision-maker within its authorised
envelope. It may:

-   decompose goals into linked, admissible task proposals;
-   decide which expertise or independent perspectives are needed;
-   propose team topology, task dependencies, execution strategies, and
    verifier plans;
-   inspect Kernel-generated briefings, evidence bundles, conflicts, and
    incidents;
-   judge whether evidence addresses acceptance criteria and recommend
    an outcome;
-   adjudicate conflicts using the UMAWS resolution ladder;
-   ask for a stronger model, different model family, or human review
    when justified;
-   propose changes to process or framework selection for explicit
    review.

It may not directly mutate coordination state, bypass admission or
leases, change pinned policy/gates, approve actions outside its
envelope, or declare completion without the Kernel's required evidence
and gate process.

### 3.3 Orchestration Manager: execution coordination

The Manager is responsible for translating accepted plans into a live
orchestration graph and keeping that graph progressing. It may:

-   instantiate and retire team records through Kernel-authorised
    operations;
-   map tasks to teams, workers, and adapters using capability cards and
    measured outcomes;
-   track dependencies as projections of authoritative task state;
-   dispatch eligible work, subject to Kernel admission and lease
    grants;
-   request concurrency changes within configured limits;
-   coordinate nested orchestrators through a common protocol;
-   monitor progress, deadlines, heartbeats, stalls, adapter health, and
    provider availability;
-   trigger bounded retries, alternative backends, recovery, quarantine,
    or requeue according to policy;
-   collect results and evidence references for the Overseer and
    verifiers;
-   maintain disposable runtime views and caches that can be rebuilt
    from Kernel state.

It cannot invent authoritative task status, override policy, release or
reassign a lease without Kernel action, suppress an incident, silently
discard a failed attempt, or mark an output accepted merely because an
adapter returned success.

### 3.4 Harness and adapters: controlled execution

The UMAWS Harness remains the deterministic wrapper around each worker
session. It should enforce the existing task/lease/workspace contract:
isolated worktree, tool allowlist, network policy, data-class ceiling,
time and resource controls, lease fencing, tool-call/file-write logging,
heartbeat/progress digest, and evidence-bundle collection.

The Manager's adapters translate between the common orchestration
protocol and a backend's native interface. Adapters are not allowed to
become miniature kernels. Their local state must be recoverable or
disposable, and all material lifecycle outcomes must be reported back
through the Harness/Kernel boundary.

## 4. Common orchestration model

### 4.1 Distinguish goals, tasks, teams, sessions, and orchestrators

These are separate concepts:

-   **Goal:** durable desired outcome or invariant-linked objective.
-   **Task:** bounded unit of work with scope, acceptance oracle(s),
    evidence requirements, risk class, budget, premise assertions, and
    stop conditions.
-   **Team:** a logical grouping of tasks and roles; it need not map
    one-to-one to a process.
-   **Worker session:** one execution attempt by an agent/model/CLI
    under a lease and fencing token.
-   **Orchestrator instance:** a process or agent that plans/manages a
    subordinate execution graph through the common protocol.
-   **Adapter:** the translation and supervision boundary for a specific
    backend.

One model may be used by multiple sessions; a team may contain
heterogeneous workers; an orchestrator may manage several teams; and a
team may delegate a bounded subgraph to a subordinate orchestrator.
These mappings must be explicit in the event/task model, not inferred
from chat titles or process names.

### 4.2 Team lifecycle

Proposed lifecycle:

`PROPOSED → VALIDATING → ACTIVE → QUIESCING → RETIRED`

Additional failure or containment states may include `SUSPENDED`,
`DEGRADED`, or `QUARANTINED`, but the exact authoritative status
vocabulary must be reconciled with existing UMAWS schemas before
implementation.

1.  The Overseer or an authorised team may propose a team with a
    purpose, parent/team relationship, role mix, target outcomes,
    allowed task classes, data classes, maximum size/depth, and resource
    envelope.
2.  The Kernel validates goal linkage, duplicate work, policy,
    depth/size limits, budget, and approval requirements.
3.  The Manager materialises the approved team, selects adapters, and
    requests leases for eligible tasks.
4.  Resizing is expressed as a request. The Kernel enforces ceilings and
    policy; the Manager then reconciles runtime workers with the
    approved state.
5.  Retirement stops new assignments, allows or explicitly cancels
    active work under policy, records outcomes, releases leases through
    the Kernel, and preserves artifacts/events.
6.  A failed team is recoverable from durable state. A replacement
    session receives a fresh briefing; it must not inherit authority
    from stale process memory.

### 4.3 Nested orchestrators

Treat a subordinate orchestrator as a specialised adapter with a bounded
delegation contract, not as a trusted peer Kernel.

Each delegation must carry: - parent task/team and goal references; -
permitted child task classes and scope; - permitted backends/model
classes and data classes; - depth and fan-out ceilings; - time,
resource, and optional token safety caps; - required evidence and
acceptance oracles; - stop/cancellation rules; - a correlation ID and
the Kernel-issued lease/capability context needed for authorised
operations.

The child may propose a plan and child tasks, but those tasks must be
admitted through the authoritative Kernel boundary. A child cannot mint
more authority than it received. The parent remains responsible for
aggregating the child result and surfacing unresolved disagreements.
Nested delegation depth and total active descendants must be bounded to
prevent recursive runaway work.

### 4.4 Common task/adapter contract

At minimum, the common contract should express:

**Input:** task ID, goal reference, scope, base commit/artifact version,
acceptance criteria/oracles, premise assertions, risk/data class,
allowed tools, lease/fence identity, budget/stop conditions, permitted
model/worker classes, and required evidence format.

**Execution:** capability discovery, health/availability,
start/resume/cancel, progress/heartbeat, logs, output/artifact
references, and explicit failure classification.

**Output:** terminal or resumable status, exit classification, changed
artifacts, test/oracle results, evidence bundle reference and hashes,
resolved provider/model/backend where relevant, usage/measurement fields
where available, and unresolved disagreements.

**Failure:** distinguish at least transient provider failure, quota
exhaustion, authentication/configuration error, model/backend
unavailable, worker crash, timeout/stall, policy denial, invalid
premise, failed acceptance oracle, lease/fence rejection, and adapter
protocol failure.

Do not collapse these into a generic `failed` string. Failure
classification drives safe recovery.

## 5. Scheduling and dynamic concurrency

### 5.1 Policy: dynamic within hard ceilings

Concurrency should respond to measured eligible capacity, dependency
readiness, work risk, provider quotas, adapter health, local
CPU/memory/process limits, and current contention. It must never exceed
Kernel-enforced ceilings.

Use distinct limits for: - total active worker sessions; - active
sessions per adapter/backend; - active calls per provider, account,
quota group, or deployment; - concurrent tasks by risk class and data
class; - team size, delegation depth, and descendant count; - local
process/resource limits; - verification concurrency and reserved
verification capacity.

The specific numeric limits are **not yet known**. Start with
conservative configurable values, measure behaviour, and change them
through an authorised configuration path. Do not claim that six models
support six concurrent workers: quota pools, RPM/TPM limits, shared
account limits, latency, context size, and failures determine usable
capacity.

### 5.2 Admission and dispatch loop

1.  Read a fresh Kernel-generated briefing and current authoritative
    task/lease state.
2.  Identify ready tasks whose dependencies are satisfied and whose
    premises remain valid.
3.  Ask the Kernel to admit or lease eligible work within the current
    envelope.
4.  Filter worker/model candidates by hard constraints first: data
    class, tools, context, capability, quota availability, backend
    health, and verifier independence.
5.  Rank eligible choices using measured performance for the task class
    and the task's acceptance oracle---not brand, self-reported
    confidence, or a generic model leaderboard alone.
6.  Dispatch through the Harness and the appropriate adapter.
7.  Monitor progress and quota/availability events. Adjust concurrency
    only through policy-checked operations.
8.  On completion, collect evidence and send it for verification; on
    failure, follow the bounded recovery ladder.
9.  Emit an auditable explanation for dispatch, escalation, deferral,
    and no-capacity outcomes.

### 5.3 QuotaGate allocation and the six-model priority pool

The user wants the Overseer to help supervise QuotaGate capacity
allocation across six permanently free, strong models. A sound division
is:

-   The **Overseer** proposes what task classes need which model
    capabilities, when diversity is important, and when quality warrants
    escalation.
-   The **Kernel policy/router** determines the permitted model class,
    task envelope, verifier exclusions, and task-specific routing
    constraints.
-   **QuotaGate** selects an eligible concrete deployment based on
    current quotas/availability and its pinned routing configuration; it
    records the resolved model and attempted deployments.
-   The **Manager** coordinates queueing, concurrency, retries, and team
    placement using the availability and event contracts. It does not
    silently substitute a model class prohibited by the task policy.

The six-model pool should be represented as a named, measured priority
group only after provider identities and quota independence are
verified. Each deployment should have explicit metadata for
provider/account/quota group, permanent-free status and evidence, model
identity, context/tool capabilities, data-class ceiling, request/token
limits, observed latency, error classes, and measured task-class
performance.

The six are not necessarily six independent quota pools. If several
deployments share an account-wide cap, QuotaGate must model them as one
hierarchical quota constraint. Do not count shared capacity twice.

### 5.4 Token usage is not an optimisation objective

Do not use minimum-token cost as a scheduler reward or prefer a weaker
model merely because it emits fewer tokens. It is acceptable to spend
more inference to obtain correct decomposition, independent checks, or a
robust synthesis when those actions serve the task.

This does **not** mean ignoring real provider rate limits or removing
all task safety caps. Existing UMAWS budget envelopes and QuotaGate
lease-token caps remain enforceable where configured. They are
guardrails against runaway work and provider constraints, not a mandate
to minimise token use. If a cap blocks useful work, the system must
report the block and request an authorised envelope change rather than
silently stopping verification or exceeding the cap.

### 5.5 Capacity measurement

Before making throughput claims, implement a repeatable capacity report
covering: - observed RPM/TPM and daily limits by deployment and shared
quota scope; - concurrent requests that remain stable; - latency
distributions and streaming behaviour; - error/rate-limit classification
and cooldowns; - context-size effects and token estimation
uncertainty; - how often fallback changes the resolved model; - capacity
reserved for independent verification and recovery; - effect of multiple
workers sharing the same account/provider; - observed success rate by
task class and acceptance oracle.

Use synthetic and low-risk workloads first. Provider limits may change;
mark timestamps and evidence sources. The scheduler should fail safely:
if no eligible deployment exists, keep the task READY/BLOCKED with a
reason and earliest availability where known, rather than falsely
failing the underlying task.

## 6. QuotaGate integration contract

The QuotaGate v1.1 proposal is the integration baseline. Preserve its
division: QuotaGate is the mechanism for concrete deployment
availability and quota; the Kernel is policy.

### 6.1 Request authorization

The preferred path is a Kernel-issued, scoped, expiring capability for a
task/lease. It must constrain the allowed model combinations, data
classes, token ceiling if configured, and relevant task/lease identity.
Workers should not receive provider secrets. QuotaGate should validate
the capability and the pinned configuration/hash contract before
forwarding.

Do not let a worker bypass QuotaGate to call a provider directly when
the task is required to use the gateway. Direct provider access must be
explicitly permitted by policy and mediated by a registered adapter.

### 6.2 Resolved-model contract

Every response, including errors and fallback cases, should expose the
actual resolved provider/model/deployment, attempted deployments and
outcomes, request ID, failure class, and usage/estimation status where
available. Silent fallback is unacceptable because it corrupts routing
measurements and may violate verifier-independence requirements.

The Manager must persist a reference to this response metadata in the
attempt/evidence record. It should never report only the requested alias
when a different deployment answered.

### 6.3 Events and authoritative time

Use QuotaGate's proposed event outbox and Kernel pull/ingest contract
unless implementation evidence supports a safer alternative. Gateway
timestamps are non-authoritative; the Kernel re-stamps events on
ingestion. QuotaGate must not write UMAWS coordination state.
Availability endpoints should allow the scheduler to defer work when
every permitted deployment is exhausted.

### 6.4 Pinned configuration

Gateway limits and model combinations are treated as pinned policy under
the existing QuotaGate proposal. Changes must follow the authorised,
hash-matching update process; a runtime agent must not mutate the pin.
The precise mechanism for delivering and validating the configuration
hash is an unresolved implementation detail in the QuotaGate proposal
and must be specified before integration tests are considered complete.

## 7. Verification, disagreement, and completion

### 7.1 Evidence-first completion

A worker result is a submission, not a successful task. A task can be
marked DONE only through the existing UMAWS acceptance path, with
evidence bundle hashes matching the committed outputs and required
verification gates passing.

The Manager should gather and present: - acceptance criteria and oracle
results; - patch/artifact hashes and base commit; - test commands and
results; - logs and failure classifications; - resolved model/backend
and attempt metadata; - independent verifier findings; - remaining
limitations, assumptions, and unresolved disagreements.

For false premises, submit a `premise-refuted` or equivalent
evidence-bearing outcome and use the existing VOID pathway rather than
forcing completion.

### 7.2 Disagreement-resolution ladder

Use the existing UMAWS conflict-resolution logic, not a Manager-specific
competing hierarchy:

1.  **Executable arbitration:** run the relevant test, oracle, or
    reproducible check when it can decide the issue.
2.  **Precedence:** apply established human rulings and
    canonical/settled material according to the source system's
    authority model. Recency, repetition, or document length must not
    act as authority.
3.  **Blind independent adjudication:** use a third agent given both
    positions and their evidence without being told which is newer or
    preferred.
4.  **Diversity escalation:** if needed, select another model family or
    verifier with different context/evidence exposure; independence must
    be measured rather than assumed.
5.  **Stronger-model retry:** escalate when the task's difficulty or a
    failed oracle justifies it, and record the reason.
6.  **Human queue:** escalate conflicts involving design intent, policy,
    high-risk promotion, exhausted retry policy, or unresolved
    adjudicator disagreement.

Preserve both sides of a real conflict. Mark affected artifacts/claims
contested and block dependent promotions as required by UMAWS. Continue
unrelated work where safe. Do not turn a disagreement into a consensus
merely to close a task.

### 7.3 Bounded recovery

The retry policy should be failure-class-specific: - transient
transport/rate-limit failure: cooldown, then retry or route to another
eligible deployment; - quota exhausted: requeue with known availability
timing; do not spin; - worker crash/stall: use Kernel liveness protocol,
then revoke/fence and quarantine if confirmed dead; - stale submission:
reject or quarantine based on lease/fence identity; - failed oracle:
preserve evidence, classify the defect, and retry/escalate only within
policy; - authentication/configuration/policy failure: stop repeated
attempts and surface an incident; - repeated identical failure
fingerprint: stop the loop and block/escalate; - no eligible model:
retain task state and report the limiting constraint.

Retry count, backoff, deadlines, and escalation conditions must be
configurable by task class and bounded by Kernel policy. The Manager
must not keep retrying merely because capacity is available.

## 8. Framework evaluation and dependency policy

The orchestration core should be custom and small. A framework may be
used for bounded parts of execution (for example, model/tool invocation
or an adapter runtime) only if it does not become an alternative
authority over task state or policy.

Evaluate candidate frameworks against a recorded scorecard before
selection:

  -----------------------------------------------------------------------
  Criterion                           Required question
  ----------------------------------- -----------------------------------
  Kernel authority                    Can all durable coordination and
                                      policy transitions remain
                                      Kernel-mediated?

  Lease/fencing integration           Can stale sessions be stopped from
                                      submitting accepted work?

  Lifecycle control                   Can teams, sessions, cancellation,
                                      retries, and recovery be managed
                                      without hidden framework state
                                      becoming authoritative?

  Observability                       Can tool calls, model resolution,
                                      attempts, and failure details be
                                      captured reliably?

  Adapter flexibility                 Can CLI agents, QuotaGate calls,
                                      and subordinate orchestrators share
                                      a stable contract?

  Security                            Can secrets, tool permissions,
                                      network restrictions, and data
                                      classes be enforced at the
                                      boundary?

  Resumability                        Can a session restart from durable
                                      state without relying on its prior
                                      conversation?

  Failure behaviour                   Are timeouts, cancellation, partial
                                      streaming, quota exhaustion, and
                                      worker death observable and
                                      testable?

  Dependency burden                   Does the framework materially
                                      reduce code/maintenance without
                                      adding an opaque control plane?

  Portability                         Does it work in WSL Ubuntu and
                                      remain viable on Linux?

  Testability                         Can invariants be tested with fake
                                      clocks, stub adapters, fault
                                      injection, and deterministic
                                      fixtures?

  Licensing/maintenance               Are license, release activity,
                                      compatibility, and upgrade risks
                                      acceptable?
  -----------------------------------------------------------------------

Do not select a framework based on popularity or feature count alone.
Prototype the smallest meaningful lifecycle and run invariant tests
against the candidate. If the framework cannot be constrained to the
required boundary, use it only behind an adapter or reject it.

## 9. Security, authority, and invariants

The implementation must preserve applicable UMAWS invariants, including
at minimum:

-   **I1 --- single authoritative log/state:** retain the source
    document's exact invariant wording and implementation meaning.
-   **I2 --- workers/gateway do not write coordination state:** Manager,
    adapters, and QuotaGate report facts through the Kernel boundary.
-   **I5 --- promotion requires evidence and policy reference:** no
    Manager shortcut around promotion.
-   **I6 --- DONE requires an evidence bundle matching committed
    outputs.**
-   **I7 --- Kernel timestamps are the only trusted time.**
-   **I8 --- Kernel code, policy, and gate definitions are hash-pinned;
    changes require the prescribed two-key event.**
-   **I9 --- artifacts are not deleted; use supersession/quarantine.**
-   **I10 --- accepted factual claims link to evidence or are marked as
    assumptions.**
-   **I11 --- contested artifacts propagate contested status to
    dependents.**
-   **I12 --- human queue items have safe defaults and blocked sets.**
-   **I13 --- generated views equal the event-log projection;
    discrepancies trigger sentinel findings.**
-   **I14 --- missing expected heartbeats/renewals are recorded as
    events.**

The list above is a concise selection, not a replacement for the source
invariant register. Before implementation, import and test the complete
current invariant set from the UMAWS source. Do not infer missing
invariant wording from this proposal.

Additional Manager-specific controls:

-   Every delegated team has an explicit envelope; child envelopes
    cannot exceed parent authority.
-   Hard concurrency, depth, fan-out, data-class, tool, and resource
    limits are enforced outside the LLM.
-   Provider credentials remain in the gateway/adapter secret boundary,
    never in worker prompts or evidence artifacts.
-   Treat task artifacts, repository files, and tool output as untrusted
    input; prompt injection cannot change Kernel policy.
-   Every state-changing request is attributable to an actor/session,
    task, lease/fence, policy version, and event.
-   Cancellation and retirement are explicit, auditable state
    transitions.
-   Failure to reach the Kernel or validate authorization must fail
    closed for new privileged work.
-   A Manager crash must not strand accepted work without a recorded
    status; a Manager restart reconstructs from Kernel briefings and
    event-derived state.
-   No agent may suppress sentinel findings, erase conflicts, delete
    evidence, or grant itself more authority.

## 10. Observability and operator experience

The operator needs one coherent view rather than separate contradictory
dashboards. The first release can provide a CLI/status view; a richer
dashboard can follow. Views must be generated from authoritative events
and current projections, not maintained as independent truth.

Minimum operational views: - active goals, task graph,
ready/blocked/leased/submitted/done tasks; - active teams, nesting
depth, worker sessions, adapter/backend health; - current concurrency
versus hard ceilings; - per-provider/account/quota-group/deployment
usage and cooldowns; - resolved models and fallback attempts; - tasks
awaiting verification, contested results, and human decisions; - lease
expiry, missed heartbeat, fencing, quarantined workspaces, and recovery
activity; - reasons for no dispatch, no eligible model, retry
suppression, or approval requirement; - invariant/sentinel findings and
the event-log/view consistency status.

Every autonomous run should produce a concise final report containing
completed outcomes, evidence links, failed/blocked work, unresolved
disagreements, policy-envelope usage, and actions requiring human
decision. It must distinguish DONE from submitted, blocked, void,
contested, or partially completed.

## 11. Phased implementation plan

Milestone order is proposed, not a commitment to dates. Exit criteria
matter more than elapsed time.

### M0 --- Source reconciliation and contracts

-   Read the current UMAWS schemas, Kernel API, task-card format, role
    briefings, adapter conventions, and full invariant register.
-   Reconcile Manager terms/statuses with existing Kernel terms; do not
    introduce duplicate status vocabularies without an explicit mapping.
-   Reconcile the QuotaGate contract, including capability format,
    resolved-model response, event ingestion, availability, pinned
    config hash, and failure classes.
-   Inventory the six priority free models and compare them with the
    QuotaGate proposal's broader catalog; verify quota-scope
    independence.

**Exit:** reviewed contract document; no unresolved ambiguity about
which component owns each state transition; all invariant IDs mapped to
tests or explicitly marked not applicable.

### M1 --- Kernel-mediated Manager skeleton

-   Implement Manager as a process/module that reads briefings, proposes
    orchestration plans, requests authorised operations, and maintains
    rebuildable runtime views.
-   Implement team/worker/task identifiers, correlation IDs, and
    lifecycle projection without adding an independent source of truth.
-   Add fake-clock and stub-adapter tests.

**Exit:** restart/replay tests reconstruct the same Manager view from
Kernel state; unauthorized state writes are impossible through the
public contract.

### M2 --- Common adapter contract and first worker backend

-   Define the versioned adapter contract.
-   Integrate one existing coding-agent CLI through the UMAWS Harness.
-   Capture structured progress, logs, exit classifications, artifacts,
    and evidence bundles.
-   Test cancellation, timeout, worker crash, stale submission, and
    restart.

**Exit:** worker success is not accepted without the evidence/gate
process; stale-fence output cannot be merged or promoted.

### M3 --- QuotaGate adapter and capacity telemetry

-   Add the QuotaGate-backed model adapter using capability
    authorization and the documented request/response/event contracts.
-   Preserve resolved-model identity on success and error.
-   Consume availability and quota events; defer work safely when no
    permitted deployment is eligible.
-   Produce an initial measured capacity report.

**Exit:** stub and live tests where available verify authorization,
secret isolation, resolved-model reporting, quota exhaustion, cooldown,
and no-eligible-deployment handling. Clearly label which tests used real
providers.

### M4 --- Dynamic teams and bounded concurrency

-   Add team creation/resize/retire operations through the Kernel.
-   Implement dependency-aware dispatch and
    per-backend/provider/account/concurrency ceilings.
-   Add delegation depth and fan-out enforcement.
-   Use measured capacity as an input, not a promise.

**Exit:** stress and adversarial tests prove no configured ceiling can
be exceeded and no task dispatches before dependencies and policy permit
it.

### M5 --- Verification, disagreement, and recovery

-   Integrate executable oracles and independent verification.
-   Add conflict records, contested propagation, diverse adjudicator
    selection, stronger-model escalation, human queue, retry budgets,
    and repeated-failure suppression.
-   Reserve capacity for verification/recovery where policy calls for
    it.

**Exit:** planted disagreement, verifier failure, provider outage,
exhausted quota, repeated failure, and false-premise tests produce
correct durable dispositions without silent conflict resolution.

### M6 --- Subordinate orchestrator adapter

-   Integrate one independent orchestrator as a child adapter.
-   Enforce inherited envelopes, Kernel-mediated child task admission,
    bounded depth/fan-out, and parent/child evidence aggregation.
-   Demonstrate that the child cannot create privileged work or claim
    completion outside its authority.

**Exit:** a child orchestrator can be terminated/replaced and resumed
from durable state; all child work remains visible in the Kernel's
task/event model.

### M7 --- Framework decision gate and operational polish

-   Benchmark any proposed framework against the scorecard and invariant
    suite.
-   Add status CLI, operator diagnostics, config validation, secret
    redaction, event replay checks, backup/recovery procedures, and
    docs.
-   Add a dashboard only after the status/event contract is stable.

**Exit:** documented framework decision; reproducible test suite;
recovery runbook; status views match event projections.

## 12. Acceptance and adversarial test matrix

  -----------------------------------------------------------------------
  Test                                Expected result
  ----------------------------------- -----------------------------------
  Overseer asks for team above hard   Kernel rejects or clamps only if
  ceiling                             policy explicitly permits; event
                                      and reason recorded

  Child orchestrator exceeds          Request rejected; no privileged
  inherited scope/depth               child work starts

  Worker submits after lease          Stale submission
  revocation                          rejected/quarantined; cannot merge

  Manager crashes with active tasks   Kernel state remains authoritative;
                                      replacement Manager resumes from
                                      briefing/events

  QuotaGate deployment exhausts quota Cooldown/exhaustion recorded;
                                      eligible fallback used only within
                                      task policy; otherwise task remains
                                      queued

  All eligible models unavailable     No false task failure; explicit
                                      no-capacity status and next
                                      availability where known

  Silent model substitution           Test fails; resolved model must
                                      match actual responder

  Shared account limit across         Capacity counted as one shared
  multiple deployments                quota pool, not double-counted

  Provider auth/config error          Retries stop according to policy;
                                      incident surfaced rather than
                                      looping

  Worker reports success but oracle   Task is not DONE; evidence and
  fails                               failed result retained

  Two verifiers disagree              Conflict preserved; dependent
                                      promotion blocked as required;
                                      adjudication path triggered

  Verifier is same as author or       Excluded where policy requires
  non-independent                     independence; selection reason
                                      recorded

  False premise                       Evidence-bearing
                                      premise-refuted/VOID result, not
                                      forced completion

  Repeated identical failure          Retry loop stopped and
                                      incident/blocked state recorded

  Kernel clock differs from gateway   Kernel timestamp is authoritative;
  clock                               gateway timestamp remains
                                      non-authoritative

  Pinned config hash mismatch         Request/config update rejected or
                                      disabled according to QuotaGate
                                      contract; event recorded

  Secret appears in worker output/log Redaction/security test fails;
                                      secret must not be exposed to
                                      worker or persisted artifacts

  Event projection and generated view Sentinel finding raised; view
  diverge                             rebuilt from event log

  Human approval required outside     Work pauses safely with a human
  envelope                            queue item and explicit blocked set

  Token use rises during verification Not penalised merely for token
                                      count; actual configured
                                      safety/provider caps still enforced

  Agent tries to delete evidence or   Operation denied; source artifacts
  erase a conflict                    preserved or quarantined/superseded
  -----------------------------------------------------------------------

## 13. Risks and trade-offs

### 13.1 Manager becomes a second Kernel

**Risk:** The Manager accumulates its own authoritative task database,
leases, policy decisions, or completion flags.

**Mitigation:** Keep all state transitions Kernel-mediated. Manager
state is a projection/cache only. Test replay equivalence and prohibit
adapter-side coordination writes.

### 13.2 Framework lifecycle becomes hidden authority

**Risk:** A framework silently owns retries, memory, cancellation, tool
execution, or task status that the Kernel cannot inspect or fence.

**Mitigation:** Use the framework behind a constrained adapter. Require
observability and explicit lifecycle mapping. Reject integrations that
cannot honour lease fencing and evidence capture.

### 13.3 Model count is mistaken for usable capacity

**Risk:** Six strong free models may share quota pools, have strict rate
limits, or perform poorly on some task classes.

**Mitigation:** Inventory quota scope and measure throughput. Use actual
availability, response metadata, and oracle outcomes. Never infer worker
count from model count.

### 13.4 Dynamic teams create runaway work

**Risk:** Nested teams repeatedly spawn tasks, retry failed work, or
create near-duplicates.

**Mitigation:** Goal-linked task admission, seed budgets, duplicate
suppression, depth/fan-out ceilings, repeated-failure fingerprints,
stagnation checks, and explicit stop conditions.

### 13.5 Parallelism increases conflict and rework

**Risk:** Teams edit overlapping artifacts, produce incompatible
conclusions, or duplicate effort.

**Mitigation:** Isolated worktrees, explicit scope/base commit,
dependency-aware dispatch, merge queue, artifact ownership, conflict
records, and evidence-based synthesis.

### 13.6 Verification is expensive but necessary

**Risk:** Independent verification consumes additional model capacity
and latency.

**Mitigation:** Do not minimise tokens as a goal. Allocate verification
according to risk and evidence requirements; prioritise independence and
oracle value. Use low-cost executable checks where sufficient, but do
not replace needed independent judgment solely to save tokens.

### 13.7 The Kernel is a single point of failure

**Risk:** A deterministic Kernel can itself contain defects or become
unavailable.

**Mitigation:** Keep it small, hash-pinned, tested, replayable, and
protected by sentinel checks. Fail closed for new privileged actions,
preserve accepted state, and use a tested restart/recovery procedure.
Replication is deferred unless single-host requirements change.

### 13.8 Metrics can be gamed or drift

**Risk:** Workers optimise visible pass rates; model updates change
performance; verifier families may share blind spots.

**Mitigation:** Measure oracle outcomes, escape/rework rates, canary
catch rates, and disagreement outcomes; sample blind audits; detect
drift; record sample sizes; avoid treating self-reported confidence as
ground truth.

## 14. Assumptions and unresolved decisions

  -----------------------------------------------------------------------------
  ID                      Item                          Status / next action
  ----------------------- ----------------------------- -----------------------
  A1                      Six permanently free strong   User-provided design
                          models are a priority pool    context; inventory
                                                        exact model/provider
                                                        IDs before
                                                        configuration

  A2                      QuotaGate's broader catalog   Stated in its v1.1
                          contains about twelve         proposal; reconcile
                          permanent free models         with A1 instead of
                                                        assuming conflict or
                                                        equivalence

  A3                      The initial environment is    Confirmed from the
                          Windows with WSL Ubuntu,      companion
                          portable to Linux             proposal/context

  A4                      The first Manager release     Recommendation; revisit
                          uses a CLI status surface     after the core
                          before a dashboard            contracts work

  A5                      The Manager and QuotaGate can Likely simplest, but
                          run alongside the Kernel on   confirm process and
                          one host initially            failure-isolation
                                                        requirements

  A6                      The Kernel already has        Unverified; map
                          suitable API operations for   existing APIs and
                          all proposed team lifecycle   propose the smallest
                          actions                       explicit extensions

  A7                      Existing UMAWS policy         Unverified; identify
                          envelopes can express nested  missing fields and
                          delegation and adapter limits propose a policy schema
                                                        change if required

  A8                      Exact task/team state         Unverified; reconcile
                          vocabulary can be extended    in M0
                          without conflicting with      
                          existing schemas              

  A9                      Framework ownership can be    Must be proven by
                          limited to execution          prototype and invariant
                          lifecycle behind an adapter   tests

  A10                     The free-model quota scopes   Capacity measurement
                          and concurrency limits are    required before
                          not yet measured for this     throughput claims
                          proposed integration          

  A11                     Token caps remain as optional Interpretation of the
                          safety ceilings, not as a     user's priority and
                          token-minimisation objective  existing
                                                        UMAWS/QuotaGate budget
                                                        contracts; confirm if
                                                        the policy meaning
                                                        differs

  A12                     Initial execution is          Based on the companion
                          single-operator/single-host   QuotaGate proposal;
                                                        revisit if multi-user
                                                        or multi-host operation
                                                        is required
  -----------------------------------------------------------------------------

## 15. Proposed first-release boundary

The first release should demonstrate the core architecture, not every
possible orchestration feature:

**Include** - Kernel-mediated Manager/Overseer integration; - versioned
task/team/adapter contracts; - bounded dynamic team lifecycle and
concurrency; - one coding-agent CLI adapter through the Harness; - one
QuotaGate-backed direct model adapter; - structured attempts,
resolved-model metadata, logs, and evidence bundles; - basic independent
verification and evidence-based conflict handling; - bounded
retry/recovery paths; - invariant, contract, integration, and
fault-injection tests; - a CLI/status report and measured capacity
report.

**Defer until the base contracts are proven** - broad adapter catalog; -
sophisticated adaptive scheduling or learned routing; - multiple
nested-orchestrator implementations; - framework-specific
optimisations; - advanced dashboard and analytics; - multi-host
orchestration or replicated Kernel; - automated self-modification of
policy or Kernel code.

These are sequencing recommendations, not a claim that the deferred
capabilities are unimportant. The architecture should leave room for
them without requiring them for the first proof of correctness.

## 16. Final recommendation

Proceed with a custom, minimal Orchestration Manager, but make the
Kernel boundary the first implementation gate. The most important early
deliverable is not dynamic agent spawning; it is a precise, tested
contract proving that teams, adapters, subordinate orchestrators, and
QuotaGate can coordinate work without acquiring independent authority.

Then add one real CLI backend and one QuotaGate-backed backend, measure
capacity, and demonstrate safe parallel work, evidence-bearing
completion, independent verification, and crash/quota recovery. Only
after those tests pass should the system broaden its adapter ecosystem
or increase concurrency.

The system should be judged by verified outcomes, preservation of
authority boundaries, recovery behaviour, and useful unattended
progress---not by the number of agents it spawns or how few tokens it
consumes.
