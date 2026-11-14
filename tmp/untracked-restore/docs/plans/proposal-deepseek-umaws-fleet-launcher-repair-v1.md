---
document:
  title: "Project Proposal: UMAWS Fleet Launcher — Repair Completion, Clean-Base Verification and Dispatch Resumption (executable brief for an implementing LLM)"
  status: "Proposal — candidate tier; executable runbook for an implementing LLM; no standing authority beyond the operator's grant recorded in this document"
  version: "1.0.0"
provenance:
  author_llm: {name: "DeepSeek", version: "DeepSeek V4.1 Flash"}
  assessor_llm: []
  last_modified_by_llm: {name: "DeepSeek", version: "DeepSeek V4.1 Flash"}
  created_date: "2026-11-09"
  last_modified_date: "2026-11-09"
  scope: "C:\\temp\\projects\\testproject1 (branch main), live repo HEAD 06d3e93e23020a0b9245b7760ed500c45c8165f6 measured 2026-11-09 during authoring; the Kernel ledger .pm/events/*.jsonl; the uncommitted repair in src/fleet/** and src/pmk/**; the work/ worktrees and %TEMP%/pmk-merge-* trees; the reports and decisions cited in Appendix E"
  source_of_truth: "Ledger events by sequence number; measured pmk status / task show / worktree list / fleet check / pins check output at authoring time; report-freebuff-UMAWS-Fleet-Launcher-repair-v1.md v1.0.0 (P-01..P-33, F-01..F-19, OQ-01..OQ-13, R-01..R-14); pilot/decisions.md D-62..D-69; pilot/repair-resumption-checklist-v1.md; docs/PDD.md gate_cmd"
audience:
  primary: "Freebuff / Buffy (the implementing LLM on this Windows machine), and any capable implementing LLM"
  secondary: "The human operator (approval authority for irreversible and governance actions)"
authority_statement: "This document is an executable brief. The operator has granted the executing LLM authority to commit, revoke leases, run live agents and resume dispatch, on the condition that every irreversible action is preceded by a recorded decision and followed by recorded evidence (section 5). It does not amend the constitution, policy or pins; those remain class-K and require the project's two-key process. Where this document and a project governance document disagree, the governance document wins and the executing LLM records the conflict."
---

# Project Proposal: UMAWS Fleet Launcher — Repair Completion, Clean-Base Verification and Dispatch Resumption

**Author:** DeepSeek V4.1 Flash — **v1.0.0**
**Document ID:** `proposal-deepseek-umaws-fleet-launcher-repair-v1`
**Date:** 2026-11-09
**Audience:** the implementing LLM (Freebuff/Buffy), with the operator as approval authority.
**Supersedes for execution:** the freebuff repair report's "next actions" only; the report's problem evidence remains authoritative.

> **How to read this document.**
> If you are the executing LLM, read **sections 0, 3, 5 and 6 first**. Section 6 is the runbook you execute; sections 1–5 give it meaning and boundaries; the appendices are reference. Do not skip section 3: the repository changed after the freebuff report was written, and section 3 lists the deltas you must re-measure before you trust any number in this document.

---

## Contents

0. How to use this document (start here)
1. Executive summary
2. Context: the system, the failure, and what "works properly" means
3. Baseline delta — report v1.0.0 versus the live repository (measured 2026-11-09)
4. Definition of done — machine-checkable success criteria
5. Operating constraints and red lines
6. The repair runbook — phases 0–12, step by step
7. Evidence, decisions and bundles — what to record and where
8. Rollback and safety plan
9. Verification index
10. Traceability — OQ register and R recommendations to steps
11. Appendix A — exact command reference
12. Appendix B — templates (decision, bundle, canary result, patch archive)
13. Appendix C — rationale, order and alternatives
14. Appendix D — known traps and anti-patterns
15. Appendix E — provenance and change log

---

## 0. How to use this document (start here)

**Your objective in one sentence:** carry the UMAWS Fleet Launcher from "repair implemented but uncommitted and unproven" to "repair landed, clean-base gate green, one supervised canary `DONE`, dispatch resumed under a recorded decision."

**The five rules that govern execution.** These come from the project's own `AGENTS.md` and the freebuff report's safeguards (S-01..S-18), and they are non-negotiable:

1. **The Kernel is the writer.** Every state change goes through `pmk`. Never hand-edit `.pm/`.
2. **Oracles decide.** Verification is the card's `gate_cmd` / acceptance oracles, not a test you chose.
3. **Two modes only.** *Card work* (card + lease + `work/<task>-<fence>` worktree + gate) or *read-only investigation*. There is no third mode. Do not develop on `main`.
4. **Record, don't hide.** Each irreversible action gets a decision record and a bundle; each deviation gets written down in the artefact you produce.
5. **A green `main` is not evidence about a worktree.** Prove the clean base (Phase 2) or you have proven nothing.

**Execution discipline.** Work one phase at a time. At the end of every phase: commit (or record why you did not), run that phase's verification, and write a one-line decision or progress note. If a step's precondition is false, **stop that step and record the stop** — do not improvise a workaround that skips it.

**When you see `[VERIFY]`.** The tag means the exact command form or field may differ from what is written here. Do not invent it. Discover it (`pmk --help`, `pmk task --help`, `<tool> --help`) and record what you found, then proceed.

---

## 1. Executive summary

### 1.1 What this is

An executable repair brief for the UMAWS Fleet Launcher. It finishes the repair programme described in `report-freebuff-UMAWS-Fleet-Launcher-repair-v1.md`, lands it, proves it on a **clean base**, runs a supervised canary through the real dispatch path, and — only on a recorded `PASS` — resumes dispatch.

### 1.2 The failure in one paragraph

Between 2026-11-07T19:38Z and 2026-11-07T23:12Z the Fleet failed to carry four cards to `DONE` unattended. Two cards with byte-identical inputs and the same base received opposite verdicts fifty-eight minutes apart. The primary cause was structural, not cognitive: **no component owned the execution environment.** The editable-install `.pth` hard-coded the main working copy's `src`, the gate ran `subprocess.run(gate_cmd, cwd=temp_wt)` with no `env=`, so `cwd` was cosmetic and the gate judged the edited main tree rather than the merged tree it had just built. Contributing causes: Overseer starvation, stale/unpinned card hints, PowerShell/bash dialect mismatch, relative order paths, dead worktree-cleanup code, and evidence capture that kept only an exit code.

### 1.3 What a correct end state looks like

- The repair is **committed** (not lost to a checkout) and the identity/evidence guards are in force.
- `python -m pytest -q` (the PDD `gate_cmd`) passes **in a detached clean worktree at HEAD**, not only in dirty `main`.
- A single supervised canary, dispatched through the real path from a clean base, reaches `DONE` with an evidence bundle that includes gate output, and a decision records `PASS`.
- Dispatch resumes under a recorded authorisation; a lease can no longer be created on the repository root without a pid and an expiry.
- The Kernel's counts agree with themselves (worktree census, leases) or the disagreement is explicitly recorded.

### 1.4 Why an order matters

The canary in the freebuff report (`T-0189`) failed because the **base**, not the worker, could not satisfy its own gate. Re-running a canary on an unfixed base reproduces the failure and teaches nothing. So the order is fixed: **protect → land → clean-base green → fix residual defects → canary → resume.** Skipping forward re-creates `D-69`.

### 1.5 What the operator has authorised

The operator has granted the executing LLM authority to commit, revoke leases, run live agents and resume dispatch, provided each irreversible action is **preceded by a recorded decision and followed by recorded evidence** (section 5). The four absolute red lines remain: no hand-editing `.pm/`, no history rewrite or force-push, no worktree deletion before capture+verify, and no committing under the human operator's identity.

---

## 2. Context: the system, the failure, and what "works properly" means

### 2.1 Components

| Component | Location | Responsibility |
|---|---|---|
| Kernel (`pmk`) | `src/pmk/`, `.pm/` | Ledger, task state machine, leases/fences, views, pins, sentinel |
| Conductor | `src/fleet/conductor.py` | Wake decisions, merge drain, lease reaping, worktree reclaim |
| Dispatcher | `src/fleet/dispatcher.py` | Slot filling, profile selection, restart/backoff, `reconcile()` |
| Harness | `src/fleet/harness.py` | Spawn worker, record provenance, run oracles, scope check, bundle |
| Run environment | `src/fleet/runenv.py` | Pin `PYTHONPATH` to the worktree for every subprocess (`worktree_env()`) |
| Merge | `src/fleet/merge.py` | Commit worktree, identity guard, merge, run `gate_cmd`, ff `main` |
| Worktrees | `src/pmk/worktrees.py` | Census, capture/archive, verify, reclaim, prune, locks |
| Adapters | `src/fleet/adapters/` | CLI invocation per agent profile |
| Console | `src/fleet/console.py` (+ entry points) | Operator UI / orchestration loop |

### 2.2 The card pipeline

```
READY → CLAIMED (lease + fence) → worktree work/T-<id>-<fence>
      → ORDER.md written, CLI spawned with a one-line prompt
      → worker edits, writes .pmwork/RESULT.md, exits
      → harness checks claims, runs acceptance oracles in the worktree
      → SUBMITTED + evidence bundle EB-<id>-<fence>
      → merge into a temporary worktree, run gate_cmd there
      → fast-forward main, INTEGRATED → DONE
```

### 2.3 Load-bearing invariants (what "works properly" protects)

1. **The tree under test must be the tree that executes.** Oracles, gate and worker tools must import the worktree's code (`src/fleet/runenv.py::worktree_env()`).
2. **A card's instructions must describe the tree the worker will actually see.** `agent_hint` is a claim about a tree at a point in time and needs a recorded base (`hint_base_commit`).
3. **A verdict must be reproducible from recorded evidence.** An exit code without output cannot distinguish a defect from a flake.
4. **A lease must prove which process owns the tree and when it expires.** Without `pid`, `creation_time` and `expires_at`, a reaper cannot tell a dead lease from a quiet one.

### 2.4 "Works properly" — the operator's bar

The operator's bar is: **a supervised canary reaches `DONE` from a clean base, the repair is landed, and dispatch resumes only after a recorded `PASS`.** A one-click run-to-done on a fresh toy project (acceptance test F1) is the *next* milestone, not this one; do not attempt it before this proposal's definition of done is met.

---

## 3. Baseline delta — report v1.0.0 versus the live repository (measured 2026-11-09)

> **Read this before trusting any number elsewhere.** The freebuff report was written at HEAD `c1fac8f`. The repository has moved. The figures below were measured during authoring of this document; **re-measure them yourself in Phase 0** and record the delta, because at least one other actor was actively committing to this repository while this document was being written.

### 3.1 Deltas that change the work

| # | Report said (v1.0.0) | Live at authoring | Consequence for the runbook |
|---|---|---|---|
| **Δ-1** | HEAD `c1fac8f`; repair uncommitted; base defect P-26/OQ-01 open (`tests/test_transport.py` untracked) | HEAD moved to `06d3e93`; commits `9b3b70d` and `de107f8` **land the transport base repair**; `tests/test_transport.py` is now **tracked** | **OQ-01 is largely resolved.** Phase 2 must still *prove* clean-base green, but the specific dangling-file fix appears landed. Re-verify. |
| **Δ-2** | `active_leases: 1`; `T-0182` `LEASED`, fence 151, repo-root worktree, agent `buffy`, no pid/expiry | `active_leases: 0`. `T-0182` is now **`DONE`** (commit `06d3e93 merge: T-0182 full-product release-status note`); its old lease record still shows `pid: null`, `expires_at: ""`, `worktree = <repo root>` | **OQ-02 is resolved in state.** The *lease-integrity defect* it exposed (P-20/P-27) is **not** — Phase 5 still adds the admission check. Preserve the historical lease record; do not delete it. |
| **Δ-3** | 189 tasks: 36 `DONE` | 189 tasks: **37 `DONE`** (T-0182 merged) | Expected. No action beyond re-measure. |
| **Δ-4** | `T-0189` `REWORK`, fence 156 (unchanged) | `T-0189` **still `REWORK`**, fence 156, agent `kilo`, `hint_base_commit bcf145c`, gate failure `test_coverage_reports_case_statuses_and_evidence` | Phase 10 must dispose of T-0189 explicitly (retry as a fresh canary card on the repaired base, or `VOID` with a recorded reason). |
| **Δ-5** | 23 Kernel worktrees vs 35 git worktree entries; 10 `pmk-merge-*` | **25 Kernel worktrees** (~297.5 MiB, 4 dirty) vs **37 git worktree entries**: 25 under `work/`, 10 `%TEMP%/pmk-merge-*`, 1 `.claude/worktrees/...`, 1 main | The census still disagrees; the *numbers* differ. Phase 4 starts from the **union**, never one number. |
| **Δ-6** | 37 tracked files changed, +3126/−529 | **28 tracked files changed, +1943/−438**; 259 untracked | The repair is **still uncommitted** but the working set shrank — another actor is committing repair slices. Phase 0 and Phase 1 must inventory the *current* dirty set, not the report's. |
| **Δ-7** | Ledger chain 3,485 events | **3,492 events**, `I1 chain verifies` | The Kernel is live and writing. Treat `.pm/` modifications as Kernel-written, never as your edits. |
| **Δ-8** | One lease held on the repo root; project `PAUSED` | Still **`PAUSED`**, `open_queue_items: 0` | Dispatch must not run until Phase 11–12. `PAUSED` is your starting state, not an error to "fix" early. |

### 3.2 Concurrent-actor warning (important)

During authoring, `HEAD` advanced from `de107f8` to `06d3e93` and `T-0182` moved to `DONE` **between two read-only commands**. Something else — another agent session, the Fleet, or the operator — is working this repository. Therefore:

- **Always re-measure immediately before you mutate.** A count you took five minutes ago may be stale.
- **Before claiming a card or committing, check for new commits, new leases and a running dispatch loop** (Phase 0, Step 0.1).
- **Never `git checkout` or `git reset` the working tree** to "get a clean state" — it will destroy the uncommitted repair and you may race another actor. Protect first (Step 0.2).
- If you detect an **active lease that is not yours**, stop and reconcile through `pmk`; do not inherit it.

### 3.3 Re-baseline command block (run this in Phase 0 and paste the output into your evidence file)

```powershell
# Run from C:\temp\projects\testproject1
$stamp = Get-Date -Format "yyyy-MM-ddTHHmmss"
git rev-parse HEAD
git branch --show-current
git log --oneline -5
git status --porcelain | Measure-Object -Line
git diff --shortstat
git worktree list
pmk status
pmk task list
pmk worktree list
pmk fleet check
pmk pins check
# Write the output to your evidence file (do not commit .pm/)
$stamp | Tee-Object -FilePath ".pm/evidence/baseline-$stamp.txt"
```

> **Note on `.pm/`:** writing a *new* file under `.pm/evidence/` for your own baseline is acceptable evidence capture. What is forbidden is hand-editing Kernel-owned files (`.pm/events/*`, `.pm/views/*`, `.pm/policy.toml`, pins). When in doubt, keep your evidence under `docs/reports/` or an archive directory instead.

---

## 4. Definition of done — machine-checkable success criteria

The proposal is complete when **all** of the following hold. Each is stated so it can be checked by a command, not a judgement:

| ID | Criterion | How it is checked |
|---|---|---|
| **DOD-1** | The repair is committed to `main` (or a branch merged to `main`) in reviewable slices, with no scratch artefacts. | `git status --porcelain -- src tests tools agents.toml` is empty of *repair* changes; `git log` shows the slices. |
| **DOD-2** | `gate_cmd` passes in a **detached clean worktree** at HEAD. | `git worktree add --detach <base> <tmp>` then `python -m pytest -q` inside it → exit 0. |
| **DOD-3** | The combined `tests/fleet` + `tests/pmk` suite **collects and runs** in one command. | `python -m pytest -q tests/fleet tests/pmk` → no collection error. |
| **DOD-4** | A lease cannot be created on the repository root, or without a `pid`/`expires_at`. | A negative test (new) passes; `pmk task show <new card>` shows the guard. |
| **DOD-5** | Evidence bundles carry gate **output**, not just an exit code. | Inspect a fresh bundle's `bundle.json`; a new test asserts the field. |
| **DOD-6** | Worktree census is reconciled: no stray `%TEMP%/pmk-merge-*`; each dirty `work/` tree is captured or recorded. | `git worktree list` and `pmk worktree list` agree on the `work/` set; `pmk worktree prune` is wired into the Conductor. |
| **DOD-7** | A **supervised canary** dispatched from a clean base reaches `DONE`. | Ledger shows `CLAIMED → SUBMITTED → ORACLE_RESULT(stage=gate, exit 0) → INTEGRATED → DONE`; bundle `EB-<id>-<fence>` exists with gate output. |
| **DOD-8** | A decision records `PASS` (or the canary is `FAIL` and dispatch stays paused). | New record `D-<n>` in `pilot/decisions.md`, ratified. |
| **DOD-9** | Dispatch is resumed **only** on `PASS`, under a recorded authorisation, with `pmk status` showing the intended project state. | `pmk status` `project_state`; decision record; first real card completes or is recorded `REWORK` with output. |
| **DOD-10** | Every irreversible action in this run has a matching decision or evidence artefact. | Section 7 checklist is fully ticked. |

**A mediocre outcome is "the suite is green on my dirty tree and I think the canary will pass."** A great outcome is "the gate is green in a detached clean worktree, the canary ran through the real path and reached `DONE`, the bundle shows why, and a decision records it — reproducible by a fresh agent from the ledger alone."

---

## 5. Operating constraints and red lines

### 5.1 Absolute red lines (from the operator)

| ID | Red line | Why |
|---|---|---|
| **RL-1** | **Never hand-edit `.pm/`** (events, views, policy, pins). All transitions via `pmk`. | The Kernel is the writer; a hand edit breaks ledger provenance (`AGENTS.md`). |
| **RL-2** | **Never rewrite history and never force-push.** No `commit --amend` on shared commits, no `rebase` of pushed history, no `push --force`. | Destroys evidence and the audit trail (P-23/D-67). |
| **RL-3** | **Never delete a worktree before capture and verification.** Dirty trees are refused, not forced. | The tree may hold the only copy of unmerged work (P-17/P-18/P-22; REC-02 before REC-01). |
| **RL-4** | **Never commit under the human operator's identity.** Use the repo-local `umaws-pilot <umaws-pilot@localhost>`. | P-23; four historical commits already carry the operator's global identity and cannot be un-attributed. |

### 5.2 Authority the operator grants (with the condition attached)

The executing LLM **may** — provided it records a decision *before* the action and evidence *after*:

- **Commit** repair slices to a branch (and merge to `main` via the normal fast-forward path or the merge machinery).
- **Push** to `origin` (`github.com/tiwaking-ops/UMAWS-Fleet-Launcher`). Prefer a feature branch; a push to `main` must be fast-forward and recorded. **Never force.**
- **Revoke/close** a lease that is demonstrably invalid (root-worktree, no pid, paused project) through `pmk`, with a recorded reason.
- **Run live agents** (no quota concern stated). Still prefer the fake CLI for mechanism tests; reserve live runs for the canary and first real cards.
- **Resume dispatch** after a recorded `PASS` decision.

Recording conventions:

- A **decision** is a `D-<n>` record in `pilot/decisions.md` (or `pilot/drafts/` then ratified), with date, who, the decision, the alternatives, and **what it leaves untested** — matching the `D-62..D-69` field order.
- An **evidence** artefact is an evidence bundle `EB-<task>-<fence>` or a file under `docs/reports/` (or an archive under `work/.archives/`), named with the date.

### 5.3 Standing rules of engagement (from S-01..S-18)

- **S-01** No task work on `main`; use the card's `work/` worktree.
- **S-04** Verify with the card's `gate_cmd`, never a self-chosen test.
- **S-05** Record output, not just an exit code, in every verdict.
- **S-06** A hint without `hint_base_commit` is unverified.
- **S-08** Confirm the import path resolves to the worktree before running anything.
- **S-09** Use absolute paths for `ORDER.md`, `RESULT.md` and every named artefact.
- **S-10** State the shell dialect (PowerShell 5.1) in the work order; do not assume bash.
- **S-14** Never describe a `main`-tree green run as proof about a clean base.
- **S-17** When two authoritative counts disagree, report both and explain; never act on one alone.
- **S-18** If you deviate, record the deviation in the artefact you produce.

### 5.4 Environment assumptions (re-verify, do not assume)

- Host: Windows, PowerShell 5.1 (a bash dialect will produce parser failures — P-10).
- Python via `.venv\Scripts\python.exe`; do not rely on `Activate.ps1` (execution policy).
- `pmk` is on PATH; `git` ≥ 2.28 with `core.longpaths true`.
- The editable install hard-codes the main `src` on `sys.path`; this is exactly the shadowing trap (P-01). **Always rely on `worktree_env()` or an explicit `PYTHONPATH`.**

---

## 6. The repair runbook — phases 0–12, step by step

**Step format.** Each step gives: **Goal**, **Preconditions**, **Commands** (PowerShell, `[VERIFY]` where the exact form is uncertain), **Expected**, **Record** (evidence/decision), **Stop if**.

Phases 0–2 are mandatory and ordered. Phases 3–9 are independent hardening; do them in order but they may be re-ordered if the operator asks. Phases 10–12 close the loop and must run in order.

---

### Phase 0 — Safety, re-baseline and protection

**Purpose:** know exactly what you are standing on, protect the uncommitted repair, and detect concurrent actors — before you change anything.

#### Step 0.1 — Detect concurrent actors

**Goal.** Establish whether another process is currently working this repository.
**Preconditions.** None.
**Commands.**
```powershell
git log --oneline -10
pmk status
pmk task list | Select-String -Pattern "LEASED|SUBMITTED"   # [VERIFY] column layout
Get-Process | Where-Object { $_.ProcessName -match "python|opencode|kilo|pi|cline|hermes|node" } | Select-Object Id,ProcessName,StartTime
# note the wall clock; wait 60s; re-run git log and pmk status and compare
Start-Sleep -Seconds 60
git log --oneline -3
pmk status
```
**Expected.** You can state whether HEAD or the lease count changed in the last minute, and whether a dispatcher/conductor loop is running.
**Record.** A `baseline-<stamp>` file (section 3.3) plus a one-line note: "concurrent actor: yes/no, evidence: <..>".
**Stop if.** `active_leases` is non-zero with a lease that is **not** a documented historical record — reconcile it through `pmk` first (Step 10.2 pattern), do not inherit it.

#### Step 0.2 — Protect the uncommitted repair

**Goal.** Make the current working tree recoverable, in case a checkout, reset or merge destroys it. This is pure insurance; it changes no tracked file.
**Preconditions.** Step 0.1 done.
**Commands.**
```powershell
$stamp = Get-Date -Format "yyyy-MM-ddTHHmmss"
$safe  = "C:\temp\projects\testproject1\.pm\evidence\repair-$stamp"
New-Item -ItemType Directory -Force -Path $safe | Out-Null
# 1. tracked changes -> patch
git diff --binary > "$safe\tracked.patch"
# 2. untracked files -> list + archive
git ls-files --others --exclude-standard > "$safe\untracked-list.txt"
# archive the untracked files without touching the tree
git ls-files --others --exclude-standard -z | tar --null -T - -cf "$safe\untracked.tar"
# 3. hashes for integrity
Get-FileHash "$safe\tracked.patch","$safe\untracked.tar" -Algorithm SHA256 | Format-List
```
**Expected.** `tracked.patch` and `untracked.tar` exist; SHA-256 hashes recorded.
**Record.** Path + hashes in your evidence file; a one-line decision note (D-<n>) "repair protected before landing".
**Stop if.** Any command errors — investigate before proceeding; do not proceed with an unprotected tree.

> **Do not** run `git stash`, `git checkout .`, `git reset --hard`, or `git clean`. Each can lose work and may race the concurrent actor.

#### Step 0.3 — Create your evidence workspace and run log

**Goal.** A single place to accumulate the artefacts DOD-10 requires.
**Commands.**
```powershell
$ev = "docs/reports/evidence/fleet-launcher-repair-$(Get-Date -Format yyyy-MM-dd)"
New-Item -ItemType Directory -Force -Path $ev | Out-Null
"# Fleet Launcher repair run log" | Out-File -Encoding utf8 "$ev\RUNLOG.md"
```
**Expected.** An empty run log exists.
**Record.** The path in your decision note.

---

### Phase 1 — Land the repair in reviewable slices

**Purpose:** commit the uncommitted repair so it cannot be lost, in slices small enough to review, without mixing in Kernel state or scratch artefacts.

#### Step 1.1 — Inventory and classify the dirty tree

**Goal.** Separate four kinds of dirty path: (a) Kernel-written `.pm/` (leave uncommitted), (b) the repair code/tests/tools (commit in slices), (c) documents/decisions (commit), (d) scratch artefacts (quarantine, don't commit).
**Commands.**
```powershell
git status --porcelain
git diff --stat
git diff --name-only
git ls-files --others --exclude-standard
```
**Expected.** You can label every path.
**Record.** The classification table in your run log.
**Stop if.** You cannot classify a path — investigate; do not commit a path you do not understand.

Guidance on categories:
- **Kernel-written:** `.pm/events/*.jsonl`, `.pm/views/*.md`. Per `D-68`, these are **live Kernel state and are deliberately not committed**. Leave them.
- **Repair code:** `src/fleet/{conductor,dispatcher,harness,legacy,merge,project,spawn}.py`, `src/pmk/{events,worktrees}.py`, `tools/check_subprocess_env.py`, and the new tests. Commit in the slices below.
- **Scratch:** root-level `find_*.py`, `insert_*.py`, `submit_*.py`, `pytest_*.txt`, `*.patch`, etc. Do **not** commit; if they are evidence, move under `quarantine/<date>/` with a manifest (the `D-68` pattern), else record and leave.

#### Step 1.2 — Confirm the identity guard before committing

**Goal.** Guarantee you commit as the repo-local pipeline identity, not the human.
**Commands.**
```powershell
git config user.name
git config user.email
git var GIT_AUTHOR_IDENT
```
**Expected.** `umaws-pilot` / `umaws-pilot@localhost` (or the repo-local identity the project uses). If it shows `Tiwa Pene`, fix it with `git config user.name "umaws-pilot"; git config user.email "umaws-pilot@localhost"` **for this repo only** before committing.
**Record.** The effective identity in your run log.
**Stop if.** You cannot make the effective identity the repo-local one.

#### Step 1.3 — Commit the repair in slices

**Goal.** Land the repair as reviewable commits, each self-consistent and each verified by its own focused tests.
**Suggested slices (adjust to the current dirty set):**

1. **Environment isolation + lint:** `src/fleet/runenv.py` (if dirty), `tools/check_subprocess_env.py`, `tests/fleet/test_worktree_env.py`, `tests/test_subprocess_env_lint.py`. Verify: `python -m pytest -q tests/fleet/test_worktree_env.py tests/test_subprocess_env_lint.py`.
2. **Gate diagnostics:** `src/fleet/merge.py` (`_gate_diagnostics`). Verify the merge tests.
3. **Overseer fallback:** `src/fleet/overseer.py`. Verify the overseer tests and `pmk fleet check`.
4. **Work-order contract + precheck:** `src/fleet/harness.py`, `src/fleet/dispatcher.py`, `agents.toml` (`precheck_satisfied`), `tests/fleet/test_precheck.py`.
5. **Worktree lifecycle:** `src/pmk/worktrees.py`, `src/fleet/conductor.py`, `tests/pmk/test_worktree_lifecycle.py`, `tests/fleet/test_conductor_leases.py`.
6. **Identity guard:** `.githooks/pre-commit`, merge identity pinning, `tests/fleet/test_identity_guard.py`.
7. **Governance docs:** `pilot/decisions.md`, `pilot/repair-resumption-checklist-v1.md`, and any repair reports.

**Commands (pattern).**
```powershell
git add <slice paths>
git commit -m "fix(fleet): <what> (<P-id/OQ-id>)"
python -m pytest -q <slice tests>
```
**Expected.** Each slice commits and its focused tests pass.
**Record.** A decision record naming each slice commit SHA; a run-log line per slice.
**Stop if.** A slice's tests fail — fix within the slice, or revert *that slice only* with `git restore --staged --worktree <paths>` and record why. Never amend a commit already pushed (RL-2).

> **Do not** `git add -A` or `git add .` — it will sweep Kernel state and scratch files.

#### Step 1.4 — Push (recorded decision)

**Goal.** Off-machine durability without risking anything irreversible.
**Commands.**
```powershell
git push origin main    # fast-forward only; NEVER --force
```
**Expected.** `main` advances on the remote by fast-forward.
**Record.** A decision note: "pushed repair slices <SHAs> to origin/main; fast-forward; no history rewrite."
**Stop if.** The push is non-fast-forward — **stop**; do not force. Investigate whether the concurrent actor pushed.

---

### Phase 2 — Clean-base gate (the point of the whole exercise)

**Purpose:** prove the gate passes on the *committed* tree, not the dirty one. This is `R-01`/`R-09` and the reason `T-0189` failed.

#### Step 2.1 — Run `gate_cmd` in a detached clean worktree

**Goal.** Establish the true baseline.
**Commands.**
```powershell
$base = (git rev-parse HEAD)
$clean = Join-Path $env:TEMP "pmk-gate-$([guid]::NewGuid().ToString('N').Substring(0,8))"
git worktree add --detach $clean $base
Push-Location $clean
# Pin the environment to the clean tree (do NOT rely on the editable install)
$env:PYTHONPATH = "$clean\src;$clean\tests"
& "C:\temp\projects\testproject1\.venv\Scripts\python.exe" -m pytest -q
$code = $LASTEXITCODE
Pop-Location
"clean-base gate exit=$code base=$base" | Tee-Object -FilePath "docs/reports/evidence/fleet-launcher-repair-$(Get-Date -Format yyyy-MM-dd)\clean-base-$($base.Substring(0,8)).txt"
# leave the worktree until you have recorded the output, then:
# git worktree remove $clean
```
**Expected.** Exit 0. If not, the base is broken; the failure text is your target.
**Record.** The full output file; exit code; base SHA.
**Stop if.** The gate is red — **fix the base** (Step 2.2) before any canary. A red clean base makes every later step meaningless (this is exactly `D-69`).

#### Step 2.2 — Fix any clean-base failure at its source

**Goal.** Make the committed base satisfy its own gate.
**Notes.** The known historical cause (`tests/test_transport.py` untracked) appears already fixed (Δ-1). If a *new* failure appears: it is a real base defect. Fix it in a card-work worktree, through the gate, then re-run Step 2.1. Do **not** "fix" it by editing the dirty main tree and calling it green (S-14).
**Record.** The failure, the fix, the re-run, the new base SHA.

#### Step 2.3 — Make clean-base gating a permanent check (`R-09`)

**Goal.** Ensure dirty-main green can never again be mistaken for proof.
**Suggested implementation.** A script (e.g. `tools/clean_gate.ps1` or a pytest helper) that creates a detached worktree at HEAD, pins `PYTHONPATH`, runs `gate_cmd`, and returns its exit code; wire it into the operator's pre-dispatch routine and (if present) CI.
**Record.** A decision + a test that runs the check (may be marked slow).
**Stop if.** The check cannot create worktrees — investigate the environment first.

---

### Phase 3 — Fix the test-infrastructure collision (`OQ-06` / `R-05`)

**Purpose:** make `tests/fleet` and `tests/pmk` collectable in one command.

#### Step 3.1 — Reproduce the collision

**Commands.**
```powershell
python -m pytest -q tests/fleet tests/pmk
```
**Expected (current).** A collection error. The cause is that `tests/fleet/test_fleet.py`, `tests/fleet/test_conductor_leases.py` and `tests/fleet/test_overseer_wake.py` do `from conftest import FIXTURE_ROOT, ...` — a bare top-level `conftest` import. When both directories are collected, the two `conftest` modules collide as the module name `conftest`, and the fleet helper is shadowed by the pmk one (which has no `FIXTURE_ROOT`).

#### Step 3.2 — Remove the bare `conftest` import

**Goal.** Make the fleet fixtures importable without a module-name collision.
**Recommended approach (pick one, record the choice):**
- **Preferred:** move the shared fleet helpers (`FIXTURE_ROOT`, `make_task`, `fake_profile`, `write_agents`, …) into a real module, e.g. `tests/fleet/_fleet_fixtures.py`, and import from there (`from _fleet_fixtures import FIXTURE_ROOT, ...`), keeping only pytest `fixture()` hooks in `conftest.py`.
- **Alternative:** make `tests/fleet` and `tests/pmk` packages (`__init__.py`) and use package-qualified imports.
- **Avoid:** renaming `FIXTURE_ROOT` only — the collision is the *module*, not the symbol.

**Commands (pattern).**
```powershell
# apply the chosen refactor, then:
python -m pytest -q tests/fleet
python -m pytest -q tests/pmk
python -m pytest -q tests/fleet tests/pmk
```
**Expected.** All three succeed.
**Record.** The chosen approach and the three results.
**Stop if.** Other suites also import `conftest` bare — grep first: `rg "from conftest import" tests`.

#### Step 3.3 — Add a collection guard test

**Goal.** Prevent regression.
**Suggested.** A small test that runs `pytest --collect-only -q tests/fleet tests/pmk` in a subprocess and asserts exit 0.
**Record.** Commit the fix + guard as one slice.

---

### Phase 4 — Worktree lifecycle: census, prune, capture (`OQ-05` / `P-16..P-22` / `R-04`)

**Purpose:** stop the leak, reconcile the census, and never lose unmerged work.

#### Step 4.1 — Take the union census

**Commands.**
```powershell
pmk worktree list
git worktree list
```
**Expected.** A disagreement (Δ-5: 25 vs 37, including 10 `%TEMP%/pmk-merge-*` and one `.claude` tree).
**Record.** Both outputs verbatim; state the difference and its cause (P-33/S-17).

#### Step 4.2 — Prune the `%TEMP%/pmk-merge-*` trees

**Goal.** Remove temporary merge trees that were never cleaned up.
**Preconditions.** You have inspected one to confirm it is a throwaway merge tree with no unique work; each is `detached HEAD`.
**Commands.**
```powershell
# Preview first — the reclaim/prune path is capture-first by design
pmk worktree prune --dry-run        # [VERIFY] exact flags
# If the tool supports merge-tree awareness (R-04), use it; otherwise:
git worktree list | Select-String "pmk-merge-"   # enumerate
# For each path P:
git worktree remove --force P       # only after confirming no unique work; record each
```
> Prefer the project's `pmk worktree prune`/`reclaim_after_capture` path over raw `git worktree remove`, because the project path captures first (RL-3). Use `git worktree remove` directly only for the temp merge trees after you have verified they hold no unmerged commits.
**Record.** Each removed path and why it was safe.
**Stop if.** A `pmk-merge-*` tree contains unmerged commits (`git log <tree> --not main`) — capture it first.

#### Step 4.3 — Capture the dirty `work/` trees before any reclaim

**Goal.** Satisfy RL-3 for the 4 dirty Kernel worktrees.
**Commands.**
```powershell
pmk worktree list | Select-String "yes"    # dirty ones
# For each dirty worktree W and its task/fence:
pmk worktree reclaim W --capture-only       # [VERIFY]; or use archive_tree()/verify_archive() as the code exposes them
```
**Expected.** An archive + a verification record per dirty tree; no deletion without an archive.
**Record.** Archive path + digest + verify result per tree.
**Stop if.** An archive fails verification — do not delete.

#### Step 4.4 — Wire pruning into the Conductor (`R-04`)

**Goal.** Cleanup happens automatically, not by hand.
**Notes.** `src/fleet/conductor.py` already has reclaim/reap hooks; extend them to also retire `%TEMP%/pmk-merge-*` trees and run `worktrees.prune()` on the heartbeat. Add/extend tests.
**Record.** Decision + commit.

---

### Phase 5 — Lease integrity admission checks (`OQ-02` / `P-20` / `P-27` / `R-02`)

**Purpose:** make an invalid lease impossible to create, not just possible to detect.

#### Step 5.1 — State the invariant

A lease is **invalid** — and the Kernel must refuse it — when any of:
1. `worktree` resolves to the repository root (not a `work/<task>-<fence>` path); or
2. `pid` **and** `expires_at` are both absent (liveness unprovable); or
3. the project state is `PAUSED` and there is no explicit operator override.

#### Step 5.2 — Implement the guard

**Notes.** Add the check at the **claim/admission** path so it is impossible to bypass. Reuse the existing lease primitives (`recorded_processes`, `live_conflicts`) in `src/pmk/worktrees.py` and the claim path in `src/pmk`/`src/fleet`. Add negative tests.
**Record.** Decision + commit; the negative test proves DOD-4.
**Stop if.** The check would break the historical `T-0182` record — it must reject *new* creation, not rewrite history (RL-2 spirit).

#### Step 5.3 — Confirm current lease state

**Commands.**
```powershell
pmk status                     # expect active_leases: 0
pmk task show T-0182           # expect DONE; historical lease fields remain
```
**Record.** Verbatim.

---

### Phase 6 — Evidence capture: gate output in bundles (`P-15` / `R-10`)

**Purpose:** a verdict must be reproducible from the record.

#### Step 6.1 — Confirm/build the gate-output field

**Notes.** `src/fleet/merge.py::_gate_diagnostics()` (line ~136) already captures the last N lines of stdout/stderr. Ensure the **bundle** (`EB-<task>-<fence>/bundle.json`) actually stores it. Add a test that a failing gate produces a bundle containing the failure text.
**Commands (inspect an existing bundle).**
```powershell
Get-Content .pm/evidence/EB-T-0189-156/bundle.json -ErrorAction SilentlyContinue
```
**Record.** Decision + commit + the test.

---

### Phase 7 — Governance and provenance (`OQ-07` / `OQ-08` / `P-23` / `P-25` / `R-11` / `R-12`)

**Purpose:** the governance layer is the weaker half; make it honest.

#### Step 7.1 — Record the identity finding and stale-claim errata

**Goal.** Attribute correctly and correct documentation drift.
**Actions.**
- Record (do not rewrite) the fact that `e08fa8d`/`ebe46ce` (and per `D-67`, `82f6be1`/`9893d94`) carry the operator's identity; the actor is `Unknown`. `D-67` already does this — confirm it stands and reference it.
- Correct stale incident claims (e.g. the `write_handoff` call-site count, P-30) in place or as an erratum.
- Move root-level formal reports into `docs/reports/`, or record the placement exception (P-31).
**Record.** A decision + commits.

#### Step 7.2 — Tighten the decision-record standard (`R-11`)

**Goal.** A one-line `{"choice":"ratify"}` must never again count as a decision (`Q-077`).
**Actions.** Define a template requiring: proposer identity, the diff/artefact under decision, the ratifier identity, and the consequences/limits; validate it in the pins check or a dedicated lint. Record as `D-<n>`.
**Record.** Template + validation + commit.

#### Step 7.3 — Resolve the `Q-077` / `.pm/policy.toml` window (`OQ-08`)

**Actions.** Either a decision naming the editor and the reason, or an explicit `Unknown` entry. `D-66` partly addresses this; confirm it is sufficient or extend it. Do **not** hand-edit policy (RL-1) — any policy change goes through the class-K process.
**Record.** Decision.

---

### Phase 8 — Model attribution (`OQ-11` / `R-07`)

**Purpose:** make "which model ran" answerable or explicitly unknown.

#### Step 8.1 — Record the served model, or say "unavailable"

**Notes.** `MODEL_SERVED` currently records `served_models: []` and bundles record `"family":"unknown"` (P-14). Either populate it from the adapter, or make "unavailable" an **explicit recorded value** on every bundle so the absence is unambiguous.
**Record.** Decision + commit + test.

---

### Phase 9 — Console/startup reconciliation (`OQ-09` / `R-06`)

**Purpose:** recovery should not depend on the operator.

#### Step 9.1 — Wire `Dispatcher.reconcile()` into startup

**Notes.** `Dispatcher.reconcile()` exists at `src/fleet/dispatcher.py:520` and is tested but not called on startup (P-29). Call it from the Conductor/Console start path, and test the **startup path**, not only the method.
**Record.** Decision + commit + test.
**Stop if.** Wiring it causes duplicate execution — reconcile must respect the "never start a second worker in a worktree with a live adopted process" rule.

---

### Phase 10 — Reconcile residual ledger state

#### Step 10.1 — Dispose of `T-0189`

**Goal.** No card left in limbo.
**Options (pick one, record it):**
- **Retry:** create a **fresh** canary card with a new `hint_base_commit` at the *current repaired* HEAD (recommended if the base is now green), or
- **Void:** `VOID` `T-0189` with a recorded reason naming the superseding canary.
**Commands.** Use `pmk` (`pmk task ...`) — discover exact subcommands with `pmk task --help` `[VERIFY]`.
**Record.** Decision + the card transition.
**Stop if.** You cannot name the superseding card — resolve that first.

#### Step 10.2 — Confirm zero invalid leases

**Commands.** `pmk status`; for any lease, `pmk task show <id>`. Reconcile any invalid one via `pmk` with a recorded reason (Step 5.3 pattern).

#### Step 10.3 — Decide the sentinel baseline (`OQ-12` / `R-13`)

**Commands.**
```powershell
pmk sentinel        # [VERIFY] exact subcommand
```
**Expected.** Red at baseline (5 × I6 + 1 × I13 historically). Either fix the underlying conditions or record them as **accepted red** with an owner and a date. Do not describe them as green.

---

### Phase 11 — Supervised canary from a clean base (successor to `D-69`)

**Purpose:** the only thing that proves the system works. Everything else is preparation.

#### Step 11.1 — Fix the base and re-confirm clean-base green

Re-run Step 2.1 at the current HEAD. It must be exit 0. Record the SHA.

#### Step 11.2 — Preflight (all must be true)

| Check | Command | Required |
|---|---|---|
| Project state is dispatchable | `pmk status` | operator authorises dispatch for this card |
| Zero active leases (or only your canary) | `pmk status` | `active_leases` consistent |
| Fleet config valid | `pmk fleet check` | `ok: true` |
| Pins valid | `pmk pins check` | `ok: true` |
| Full gate green | `python -m pytest -q` | exit 0 |
| Clean-base gate green | Step 2.1 | exit 0 |
| Canary card created with a real `hint_base_commit` | `pmk task show <canary>` | base == current HEAD |

**Stop if.** Any check fails. Fix, do not proceed (this is exactly the deviation `D-69` recorded).

#### Step 11.3 — Create the canary card

**Goal.** A card whose work is a single, checkable artefact, dispatched through the real path.
**Notes.** Model the card on the existing canary design (`pilot/cards/canary-replacement-v1.md`) and the `D-69` packet. Requirements: exactly one write scope; an acceptance oracle run by the harness; `hint_base_commit` = current HEAD; a `gate_cmd` = `python -m pytest -q`. Prefer the **fake CLI** for a first mechanism pass, then one **live** run for the real canary (the operator allows live runs).
**Record.** The card payload.

#### Step 11.4 — Dispatch and observe

**Commands.**
```powershell
pmk dispatch run --seconds 900      # [VERIFY] exact form used by the project
# observe the Console / logs; do not intervene except to stop a runaway
pmk task show <canary>
```
**Expected ledger sequence (the path that must work):**
`CLAIMED → AGENT_STARTED → AGENT_EXITED(OK) → SUBMITTED → ORACLE_RESULT(stage=gate, exit 0) → INTEGRATED → DONE`, with bundle `EB-<id>-<fence>`.
**Record.** The ledger tail; the bundle; the gate output file.
**Stop if.** The worker exits 0 but the gate judges the wrong tree — that is P-01 recurring; stop and re-check `worktree_env()` wiring (Phase 1 slice 1).

#### Step 11.5 — Record the result as a decision

**Goal.** `PASS` or `FAIL`, explicitly.
**Actions.** Write `D-<n>`: canary id, base, agent/profile, worker exit, gate exit, bundle id, and (on failure) the failing assertion. State what it leaves untested.
**Stop if.** `FAIL` — record it, keep dispatch paused, return to Phase 2. Do **not** resume dispatch.

---

### Phase 12 — Resume dispatch (A10)

**Purpose:** the final, operator-authorised step.

#### Step 12.1 — Resume only on `PASS`

**Preconditions.** Step 11.5 decision is `PASS`; the operator re-affirms resumption.
**Commands.**
```powershell
pmk project resume      # [VERIFY] sets project_state RUNNING
pmk status
```
**Record.** The A10 authorisation decision + the state change.
**Stop if.** No `PASS` — do not resume.

#### Step 12.2 — Watch the first real cards

**Goal.** Catch a regression on real work before it cascades.
**Actions.** Dispatch a small number of real cards; for each, confirm the ledger path and that the bundle carries gate output. On a first `REWORK` with a genuine gate failure, capture the output and stop the line; on an `UNKNOWN`/`QUOTA` failure, note it is a different class (P-13).
**Record.** A short dispatch-observation note; any incident via `pmk incident`.

---

## 7. Evidence, decisions and bundles — what to record and where

**Per irreversible action:** one decision record **before**, one evidence artefact **after**.

| Action | Decision (before) | Evidence (after) |
|---|---|---|
| Protect the tree (0.2) | note | patch + tar + hashes |
| Commit a slice (1.3) | note naming the slice | commit SHA + focused-test result |
| Push (1.4) | note | remote status (fast-forward) |
| Clean-base gate (2.1) | — | full gate output + base SHA |
| Prune a merge tree (4.2) | note per tree | "no unmerged commits" proof |
| Capture a dirty tree (4.3) | — | archive + digest + verify result |
| Revoke/close a lease | note + reason | before/after `pmk task show` |
| Canary (11) | — | bundle + ledger tail + gate output |
| Resume dispatch (12) | A10 decision | `pmk status` before/after |

**Where.** Decisions go in `pilot/decisions.md` (drafts first, then ratified). Evidence goes in `docs/reports/evidence/<run>/` and, for card work, in the Kernel bundle `EB-<task>-<fence>`.

**The completeness check (DOD-10):** at the end, every row in the table above has both a decision *and* an evidence file, or an explicit `Unknown`/`not-applicable` note.

---

## 8. Rollback and safety plan

| Risk | Trigger | Response |
|---|---|---|
| A slice commit breaks the suite | focused/clean-base test fails after commit | `git revert <sha>` (never amend a pushed commit); record; fix forward. |
| A push is rejected (non-fast-forward) | `git push` refused | **Stop.** Investigate the concurrent actor; do not force. |
| An archive fails verification | `verify_archive()` returns false | **Do not delete** the tree; investigate; record. |
| The canary passes but a real card regresses | first real `REWORK` | Stop the line; capture output; keep dispatch paused; record an incident. |
| The concurrent actor commits over your work | new unexpected commits appear | Re-baseline; reconcile; never `reset`/`checkout` the tree; prefer merge over overwrite. |
| You cannot make the clean base green | Step 2.1 red after honest attempts | Record `FAIL`; keep dispatch paused; escalate to the operator. This is a legitimate outcome, not a failure of the process. |

**Never, as a shortcut:** hand-edit `.pm/`, force-push, `reset --hard`, `clean -fdx`, or delete a worktree you have not captured.

---

## 9. Verification index

| What you must be able to show a fresh agent | Where it lives |
|---|---|
| Current baseline snapshot | `docs/reports/evidence/<run>/baseline-*.txt` (or your Section 3.3 file) |
| The protected-before-landing archive | `.pm/evidence/repair-<stamp>/` (hashes recorded) |
| Each repair slice | `git log --oneline` |
| Clean-base gate result | `docs/reports/evidence/<run>/clean-base-*.txt` |
| Combined-collection result | your run log |
| Worktree census + prune/capture records | your run log; archives under the project's archive root |
| Canary bundle | `.pm/evidence/EB-<id>-<fence>/bundle.json` |
| Canary ledger tail | `.pm/events/<date>.jsonl` (Kernel-written) |
| Decisions | `pilot/decisions.md` (`D-<n>`) |

---

## 10. Traceability — OQ register and R recommendations to steps

### 10.1 Unresolved issues (OQ) → steps

| OQ | Status at authoring (Δ) | Step(s) |
|---|---|---|
| OQ-01 dangling `tests/test_transport.py` | **Resolved in fact** (Δ-1); still prove it | 2.1–2.2 |
| OQ-02 `T-0182` root lease | **Resolved in state** (Δ-2); defect remains | 5.1–5.3, 10.2 |
| OQ-03 repair uncommitted | **Open** (Δ-6) | 0.2, 1.1–1.4 |
| OQ-04 no passing canary / A10 blocked | **Open** | 2, 11, 12 |
| OQ-05 stray merge trees / dirty trees | **Open** (Δ-5) | 4.1–4.4 |
| OQ-06 conftest collision | **Open** | 3.1–3.3 |
| OQ-07 identity attribution | Open (record-only) | 7.1 |
| OQ-08 `Q-077` / policy window | Open | 7.2–7.3 |
| OQ-09 `reconcile()` not wired | Open | 9.1 |
| OQ-10 documentation drift | Open | 7.1 |
| OQ-11 model attribution | Open | 8.1 |
| OQ-12 sentinel baseline red | Open | 10.3 |
| OQ-13 author's out-of-band work | Record-only (report §9) | 7.1 (errata) |

### 10.2 Recommendations (R-01..R-14) → steps

| R | Step(s) |
|---|---|
| R-01 resolve dangling file / clean-base gate | 2.1–2.2 |
| R-02 lease admission check | 5.1–5.2 |
| R-03 land the repair in slices | 1.1–1.4 |
| R-04 prune-aware `worktree prune` in Conductor | 4.2, 4.4 |
| R-05 rename/collision-proof fixtures | 3.1–3.3 |
| R-06 wire `Dispatcher.reconcile()` | 9.1 |
| R-07 record served model or "unavailable" | 8.1 |
| R-08 extend env lint to all `src/fleet` subprocess sites | 1.3 (slice 1) |
| R-09 clean-base gate in local checks/CI | 2.3 |
| R-10 `gate_output` in every bundle | 6.1 |
| R-11 decision-record template + validation | 7.2 |
| R-12 correct stale claims / errata | 7.1 |
| R-13 sentinel baseline decision | 10.3 |
| R-14 standard canary path | 11.3–11.5 |

---

## 11. Appendix A — exact command reference

```powershell
# ---- read-only baseline ----
git rev-parse HEAD
git branch --show-current
git status --porcelain
git diff --shortstat
git worktree list
pmk status
pmk task list
pmk task show <task-id>
pmk worktree list
pmk fleet check
pmk pins check
pmk sentinel                      # [VERIFY]

# ---- protection ----
git diff --binary > <safe>\tracked.patch
git ls-files --others --exclude-standard -z | tar --null -T - -cf <safe>\untracked.tar

# ---- identity guard ----
git var GIT_AUTHOR_IDENT
git config user.name "umaws-pilot"
git config user.email "umaws-pilot@localhost"

# ---- clean-base gate ----
$clean = Join-Path $env:TEMP "pmk-gate-$([guid]::NewGuid().ToString('N').Substring(0,8))"
git worktree add --detach $clean (git rev-parse HEAD)
Push-Location $clean
$env:PYTHONPATH = "$clean\src;$clean\tests"
& "C:\temp\projects\testproject1\.venv\Scripts\python.exe" -m pytest -q
Pop-Location

# ---- landing ----
git add <slice paths>
git commit -m "fix(fleet): <what> (<id>)"
git push origin main              # fast-forward only

# ---- lifecycle (prefer project paths; [VERIFY] flags) ----
pmk worktree prune --dry-run      # [VERIFY]
pmk worktree reclaim <tree> --capture-only   # [VERIFY]

# ---- canary / dispatch ----
pmk dispatch run --seconds 900    # [VERIFY]
pmk project resume                # [VERIFY]

# ---- discovery (never invent flags) ----
pmk --help
pmk task --help
pmk worktree --help
```

> When a `[VERIFY]` flag differs from what the tool offers, use the tool's real flag and **record the correction** in your run log (S-18).

---

## 12. Appendix B — templates

### B.1 Decision record (matches the `D-62..D-69` field order)

```
D-<n> | <date> | <who: proposer / ratifier> | **<one-line decision.>** <detail: what changed, where, why.> |
    (a) <alternative 1>; (b) <alternative 2>; (c) <alternative 3>. |
    <what it leaves untested / residual risk.>
```

### B.2 Evidence bundle fields (per submission)

```
EB-<task>-<fence>/bundle.json contains at minimum:
  task, fence, base_commit, agent, profile,
  worker_exit, oracles: [{cmd, exit, output_tail}],   # output_tail is the point of P-15/R-10
  gate: {cmd, exit, output_tail},                      # gate output, not just exit
  scope_changed: [...], family: "..." | "unavailable"
```

### B.3 Canary result record

```
Canary <task> (fence <f>), base <sha>, profile <p>:
  worker exit <n>; gate exit <n>; bundle EB-<task>-<f>;
  verdict: PASS | FAIL;
  on FAIL: failing nodeid + first N lines of output;
  leaves untested: <list>;
  decision: D-<n>.
```

### B.4 Protection archive naming

```
.pm/evidence/repair-<yyyy-MM-ddTHHmmss>/
  tracked.patch
  untracked.tar
  untracked-list.txt
  SHA256SUMS.txt
```

---

## 13. Appendix C — rationale, order and alternatives

### 13.1 Why this order

1. **Protect before landing** — the repair exists only in the working tree (Δ-6); a single `checkout` loses it. Insurance costs one step and removes the largest single risk.
2. **Land before gating** — the gate is run from `HEAD`; if the repair is uncommitted, a "clean-base" gate tests the wrong (committed) tree. You cannot gate what you have not committed.
3. **Clean base before canary** — `T-0189` proved that a canary on a broken base fails for reasons unrelated to the worker. Reordering this re-creates `D-69`.
4. **Hardening before canary** — lease admission, evidence capture and lifecycle fixes reduce the chance the canary fails for a *secondary* reason, and they close the classes of defect the incident exposed.
5. **Canary before resume** — dispatch resumes only on recorded `PASS`. This is the operator's own rule and the point of the whole exercise.

### 13.2 Alternatives considered

- **"Just resume dispatch and fix what breaks."** Rejected: reproduces the exact failure mode (unproven base, out-of-band fixes, verdicts without evidence).
- **"Fix only the base and run the canary."** Rejected as insufficient: leaves the lease defect, the evidence gap and the census disagreement, any of which can fail the canary or the next card.
- **"Rewrite history to fix the identity commits."** Rejected by RL-2 and by `D-67`: provenance is recorded, not rewritten.
- **"Delete all worktrees to get a clean census."** Rejected by RL-3: capture and verify first; the dirty trees may hold the only copy.

### 13.3 Why the canary uses a fresh card, not `T-0189` retried in place

`T-0189`'s `hint_base_commit` (`bcf145c`) predates the base repairs (Δ-1). Retrying it would test a stale base and re-fail for the old reason. A fresh card pinned to the current repaired `HEAD`, or a `VOID` of `T-0189` naming the replacement, keeps the record honest (S-06).

---

## 14. Appendix D — known traps and anti-patterns

1. **"It passes on my tree."** A green `main` tree is not evidence about a worktree — the editable `.pth` may resolve imports to `main`. Prove the clean base (Phase 2).
2. **"The agent said it was done."** A worker's own oracle can be right while the harness judges a different tree. Trust the gate, in the worktree.
3. **"The hint says the files are missing."** Check the worktree first; hints age and can point outside scope (P-05/P-07).
4. **"I'll just fix it on main."** This is the deviation that caused the incident (§9 of the report). Use a card + worktree.
5. **"Exit code 1, so it failed."** Without output you cannot tell a defect from a flake (P-15). Record output.
6. **"The lease is there, so someone is working."** Without a pid or expiry it may be a ghost (P-20/P-27).
7. **"The worktree is old, delete it."** Capture and verify first (RL-3).
8. **"The decision is ratified, so it was reviewed."** A one-line ratify payload is not review (`Q-077`).
9. **"Force-push to make the remote match."** Forbidden (RL-2).
10. **"Commit everything so the tree is clean."** Never `git add -A`; you will commit Kernel state and scratch.

---

## 15. Appendix E — provenance and change log

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0.0 | 2026-11-09 | DeepSeek V4.1 Flash | First executable repair brief: baseline delta (Δ-1..Δ-8) against `report-freebuff-UMAWS-Fleet-Launcher-repair-v1.md` v1.0.0; definition of done DOD-1..DOD-10; red lines RL-1..RL-4; runbook phases 0–12; evidence/decision plan; rollback plan; OQ/R traceability; command reference; templates; rationale. |

### Provenance statement

This proposal was authored by **DeepSeek V4.1 Flash** from a read-only review of the freebuff repair report, the original `docs/sources/fleet-launcher-proposal.md`, the repair checklist, `pilot/decisions.md` (D-62..D-69), and live measurements of the repository (git and read-only `pmk` commands) taken on 2026-11-09. No `.pm/` file was edited; no task was transitioned; no source was changed; nothing was pushed. Where a fact could not be established from the record, it is labelled `[VERIFY]` or `Unknown` rather than inferred.

**Delta caveat.** At authoring time the repository was being modified by another actor (`T-0182` merged and `HEAD` advanced during this analysis). Every figure in section 3 is a snapshot and must be re-measured in Phase 0 before it is relied upon. This document does not replace the Kernel ledger as the source of truth.

**No authority.** This is a candidate-tier proposal. It does not amend the constitution, policy or pins. The operator's grant of authority recorded in section 5 applies to the executing agent; where this document conflicts with a governance document, the governance document wins.
