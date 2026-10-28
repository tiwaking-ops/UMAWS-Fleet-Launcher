# Task: Diagnose UMAWS failures and propose comprehensive repairs

## Role

Act as a forensic software engineer, Windows/WSL integration specialist, and
technical proposal author.

Your task is to establish why UMAWS fails in its real project-creation workflow
and produce an evidence-based, implementation-ready repair proposal. Do not
confuse passing component tests with a functioning autonomous project system.

Be rigorous but practical. The proposal will be implemented by LLM coding
agents and approved by the human project owner.

## Workspace and deliverable

Repository:
C:\temp\projects\testproject1

Work from this repository. Verify the actual repository root, branch, working
tree, Python environment, and execution context before making claims about them.

Read these three reports in full:

- report-beam-project-state-v1.md
- report-codebuff-project-state-v1.md
- report-deepseek-project-state-v1.md

Produce the formal project proposal in the repository root as:

report-codebuff-recommendations-v1.md

Include:
- Title
- Author: Claude Code
- Document version: 1.0
- Actual preparation date
- Repository and inspected commit/snapshot identifiers
- Document status: Proposed — awaiting owner approval
- Assessment scope and verification limitations

Do not claim a specific underlying model or model version unless it is actually
available and verifiable. The filename is prescribed; it does not imply
Codebuff authorship.

If the target report already exists, preserve it in an identified archive before
replacing it. Never overwrite the only copy of an existing artefact.

## Context and desired outcome

UMAWS creates project folders and Git repositories, installs or applies the
UMAWS system, and uses an Overseer/agent workflow to complete projects.

The owner's practical problem is that attempts to create small working
applications have failed. The owner does not know why.

toy1, toy2, and toy3 were sample project attempts. They failed at different
stages. They are failed case studies to investigate, not assumed examples of
successful operation.

The goal is a reliable tool for the owner's regular use. A successful system
must take a fresh brief through project setup, implementation, verification,
and completion, producing a genuinely working small application.

The original UMAWS approach was developed through practical use and has had
successful outcomes. Do not assume that all of its design is defective because
this implementation or these project attempts fail.

## Audience

Primary implementers: LLM coding agents.
Decision-maker and final acceptance authority: the human owner.

Write both:
1. A decision-focused formal proposal.
2. A detailed execution backlog that coding agents can implement without
   inventing missing requirements.

## Scope

Cover both:
- Repairs to existing defects, configuration, operational state, integration,
  documentation, and verification.
- Completion of intended but unfinished capabilities needed for reliable use.

Discover the intended scope from repository requirements, source proposals,
decision records, and implementation evidence. Distinguish essential completion
from optional expansion.

Include a comprehensive testing-suite recommendation and a staged validation
programme.

Prefer repair. Also evaluate whether a clean successor would be a better
alternative. The owner may approve building and validating a successor before
attempting repairs, retaining repair as a fallback.

All design commitments may be challenged. However, if you propose changing
foundational application architecture or governance, that alternative must be
built separately and must leave the original application preserved and untouched
by that redesign.

Do not silently redefine UMAWS to make the tests easier to pass.

## Operational and decision constraints

### Approval and autonomy

The intended workflow is:
- Owner approval at major steps.
- Mostly unattended execution between those steps.
- Escalation when needed.
- Owner decisions can override previous decisions, with the override recorded.

The owner describes automatic forking when the system is unsure whether a
decision is major, followed by later verification.

Interpret this provisionally as isolated experimentation only. Investigate
the current mechanism and recommend explicit rules for:
- What counts as a major decision.
- When to pause and ask.
- When an isolated fork may proceed.
- What a fork may and may not change.
- How results return for approval.
- How overrides supersede earlier decisions without erasing history.

An experimental fork must not silently merge, deploy, spend money, or change
the authoritative project.

### Cost

Runtime implementation and verification must be strictly free.

Paid models may be used by the owner for planning, but do not assume that paid
models are available to the runtime or required to pass acceptance.

Discover the required agents, providers, and integrations from repository
records. Identify contradictions or missing requirements explicitly.

Treat “free” as requiring verification, not as a model-name suffix or an
unverified profile label. Do not use automatic paid fallback.

Before live calls, establish how the chosen account, endpoint, and routing
avoid charges. If this cannot be established, mark the live test blocked and
explain the specific evidence or owner decision needed.

QuotaGate must support understanding and managing remaining free quota.
Do not pretend provider limits or remaining quota are knowable when the
available evidence supports only estimates.

### Platform

Target Windows plus WSL.

Define supported execution paths and their boundaries, including:
- Shell and command syntax.
- Python and dependency environments.
- Git and worktree behaviour.
- Paths and filesystem ownership.
- Process identity, supervision, and termination.
- Ports and service discovery.
- Line endings and encoding.
- Agent executable and authentication configuration.

Do not assume Windows and WSL share interchangeable environments.

### Preservation

Nothing may be deleted or discarded. Archive instead.

Preserve existing:
- Source and configuration.
- Task and event history.
- Evidence bundles and logs.
- Failed projects.
- Worktree contents and branches.
- Environments displaced during diagnostics.
- Reports and generated diagnostic artefacts.

Record archive locations and provenance. Protect credentials and secrets from
accidental inclusion in reports or shareable evidence.

A backup already exists, but that does not waive the no-deletion requirement.

### Current authority

This assignment authorises investigation and proposal preparation, not execution
of the repair programme.

You may run tests, create isolated diagnostic projects, install dependencies in
isolated environments, and conduct verified-free live tests.

The owner permits necessary diagnostic environment modifications, but prefer
isolation and preserve the original state. Explain and record any changes made.

Other agents and dispatchers may be paused for a stable inspection window.
Coordinate this explicitly; do not terminate unidentified processes.

Do not apply queued repairs, migrate production state, rewrite historical
events, or implement a successor during proposal preparation.

## Investigation requirements

### 1. Establish a reproducible baseline

Capture:
- Repository identity, commit, dirty state, and relevant worktrees.
- Active writers, dispatchers, services, and agent processes.
- Actual executable and import resolution.
- Installed environment versus repository source.
- Relevant configuration and platform details.
- Baseline commands, exit codes, logs, and artefact locations.

Do not treat a command run against a sibling repository as verification of this
repository.

If diagnostics themselves mutate state, document that fact.

### 2. Read the governing and historical evidence

Inspect the three assessments and the repository's:
- Requirements and source proposals.
- README and agent instructions.
- Brief/PDD and lifecycle records.
- Decisions, queues, incidents, and prior failure reports.
- Tests, launchers, adapters, runtime code, and provider configuration.
- Relevant task cards, event history, evidence bundles, and merge records.

Locate toy1/toy2/toy3 from evidence rather than assuming their paths.
Inspect accessible cases without altering their preserved state.
If unavailable, document the missing evidence and its impact.

### 3. Reconcile the reports

Create a deduplicated findings register covering every issue raised by the
three reports.

For each finding, distinguish:
- Confirmed current defect.
- Historical defect.
- Environment or sandbox limitation.
- Incomplete intended capability.
- Unverified risk.
- Disputed or unsupported claim.
- Already resolved issue.

Resolve conflicting claims against primary evidence.

In particular, investigate whether T-0003's completion is supported by the
correct passing oracle and evidence for the integrated result. Check the exact
attempt, fence, worktree, commit, gate stage, and evidence references before
drawing a conclusion.

A later passing gate may or may not resolve an earlier failure; prove the
relationship rather than assuming it.

Never propose editing old hash-chained events merely to correct labels.

### 4. Trace the actual failed workflow

Map:
fresh brief → project folder/Git setup → UMAWS bootstrap → requirements/PDD →
task admission → selection → dispatch → worktree → agent execution →
oracle/evidence → integration → application launch → close-check.

For each failed sample project, identify:
- Intended result.
- Last verified successful stage.
- First observed failing stage.
- Exact symptom and evidence.
- Root cause or competing hypotheses.
- Why existing checks did not detect or prevent it.
- Reproduction procedure.
- Proposed repair and regression test.

Distinguish application defects from infrastructure, model/provider, quota,
permissions, shell, configuration, and coordination failures.

Do not repeatedly run an expensive end-to-end attempt when a smaller diagnostic
can isolate the failing boundary.

### 5. Preserve an honest evidence standard

Classify conclusions as observed, reproduced, inferred, or unverified.

Record exact commands, execution context, exit codes, relevant artefact paths,
and source references. Use file paths with line references where practical,
plus event/task/commit identifiers where relevant.

Passing tests and clean sentinel output are evidence for their checked
properties, not proof of overall project health.

If blocked, explain the blocker and the smallest concrete next action needed.

## Required proposal content

Use the following structure, expanding where necessary:

1. Document control and executive decision summary.
2. User objective and definition of reliable operation.
3. Assessment method, baseline, scope, and limitations.
4. Intended architecture versus observed implementation.
5. Failed-project reconstructions and causal analysis.
6. Reconciled findings register and source-report crosswalk.
7. Options appraisal:
   - Repair in place.
   - Repair with isolated component replacement.
   - Separately built clean successor.
8. Recommended approach and decisions required from the owner.
9. Detailed repair and completion work packages.
10. Comprehensive testing and acceptance programme.
11. Agent execution, concurrency, and approval model.
12. Archive, recovery, migration, and fallback strategy.
13. Risks, unresolved questions, and residual limitations.
14. Implementation backlog and final acceptance checklist.

Compare options by evidence, reliability, disruption, preservation,
maintainability, testability, integration compatibility, and free-runtime
feasibility. Do not manufacture effort estimates or deadlines.

For each work package provide:
- Stable identifier.
- Findings and requirements addressed.
- Intended outcome.
- Affected components and verified paths.
- Concrete implementation actions.
- Dependencies and ordering.
- Safe parallelisation boundaries.
- Approval requirements.
- Tests and objective acceptance criteria.
- Evidence to retain.
- Archive/recovery procedure.
- Definition of done.

Avoid speculative exact commands or file paths. If implementation details
cannot yet be established, identify a bounded discovery task.

## Testing-suite requirements

Recommend a layered suite covering:

- Unit and component behaviour.
- Installed-package and launcher behaviour, not just source-path imports.
- Windows and WSL execution boundaries.
- Fresh setup and clone reproducibility.
- Lifecycle and task-admission correctness.
- Oracle correctness, evidence binding, and rejection of false completion.
- Agent adapters, model identity, provenance, and resume/restart behaviour.
- Quota handling, classification, routing, exhaustion, and free-only guarantees.
- Process crashes, stale leases, recovery, and bounded retries.
- Incident escalation without repeated wake storms.
- Concurrency, worktree isolation, integration conflicts, and state integrity.
- Console accuracy and operator controls.
- Context generation and injection-related risks where relevant.
- Archive and recovery procedures.

Separate:
1. Deterministic offline/fake-agent tests.
2. Controlled verified-free live integration tests.
3. Fresh-project end-to-end acceptance tests.

Specify which tests block which progression gates.

Design new isolated sample projects that reproduce the failure boundaries found
in toy1/toy2/toy3 and then prove the repaired workflow.

At least one acceptance scenario must start from a fresh brief and produce a
small working application through UMAWS itself.

Check the generated application independently, including functionality,
launch behaviour, and required outputs. UMAWS's own DONE label is not
sufficient acceptance evidence.

The application and its acceptance oracle must not depend on the same agent's
unsupported claim that its work is correct.

Include negative tests showing that broken applications, failed oracles,
missing evidence, unavailable models, exhausted quota, and dead workers cannot
be reported as successful completion.

Define sensible repeated-run and recovery demonstrations, explaining the basis
for the proposed thresholds. Do not promise perfect reliability from a single
successful demo.

## Length and writing standard

Write a substantial formal Markdown proposal. Use no arbitrary word limit:
be comprehensive enough for implementation without padding or duplicating
the same explanation across sections.

Use tables for findings, option comparisons, dependencies, and test matrices.
Use numbered procedures for executable sequences.

Separate facts, recommendations, owner decisions, and unresolved questions.
Make the executive section understandable without reading the full backlog.

## Success criteria

A great proposal must:

1. Explain the failed fresh-brief-to-working-application workflow with traceable
   evidence, resolving contradictions and exposing remaining uncertainty.

2. Translate every confirmed issue and required unfinished capability into
   actionable work with dependencies, approval boundaries, preservation rules,
   and objective regression tests.

3. Provide a credible free-runtime path to repeated successful real-project
   acceptance on Windows/WSL, rather than equating unit-test success with
   operational reliability.

## Examples and reference material

Use the three supplied project-state reports as assessment inputs.

Use toy1/toy2/toy3 and repository failure reports as case studies once located.
No successful reference application or accepted proposal template has been
supplied; do not invent either.

## Completion instructions

Write proposal-claude-repair-v1.md to the repository root and verify
that it exists and contains the complete proposal.

Then report:
- The document created.
- The principal diagnosed causes, with confidence levels.
- The options and recommendation.
- Decisions required from the owner.
- Diagnostics performed and any environment/state changes made.
- Unresolved blockers or unexecuted tests.

Stop and await approval. Do not begin implementing the proposal.