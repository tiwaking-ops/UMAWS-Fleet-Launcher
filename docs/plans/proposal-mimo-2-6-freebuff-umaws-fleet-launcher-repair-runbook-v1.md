---
document:
  title: "Proposal and Mandatory Runbook: Completing the UMAWS Fleet Launcher Repair — Full Instructions for an Executing LLM Agent"
  status: "Draft v1.0.0 — untracked working paper. Execution is NOT authorised until the operator approves this document. Written on operator instruction and deliberately left uncommitted (operator decision, 2026-11-09)."
  version: "1.0.0"
provenance:
  author_llm:
    name: "MiMo-V2.6-Flash Free"
    version: "mimo-v2.6-flash-free; document version 1.0.0"
  created_date: "2026-11-09"
  last_modified_date: "2026-11-09"
  scope: "C:\\temp\\projects\\testproject1 (branch main), measured 2026-11-09 at HEAD 06d3e93e23020a0b9245b7760ed500c45c8165f6: pmk status = PAUSED, 0 active leases, 3,491 chained events, 25 Kernel worktrees; 28 modified tracked files (+1943/−438); the document set listed in Appendix B. NOTE: the repository was observed moving during authoring — HEAD advanced from c1fac8f1 to 06d3e93, landing the OQ-01 base fix (9b3b70d, de107f8) and the T-0182 resolution (6cabebb, 06d3e93) after the source report was written. Every phase of this runbook therefore begins with a verify-first gate that re-measures state instead of trusting any snapshot, including this one."
  source_of_truth: "report-freebuff-UMAWS-Fleet-Launcher-repair-v1.md (registers P-01…P-33, F-01…F-19, OQ-01…OQ-13, S-01…S-18, R-01…R-14); proposal-umaws-problems-and-issues-repair-v1.md; pilot/repair-resumption-checklist-v1.md; docs/PDD.md (gate_cmd: python -m pytest -q); pmk CLI --help output measured 2026-11-09; live pmk/git measurements recorded per phase"
---

# Proposal and Mandatory Runbook: Completing the UMAWS Fleet Launcher Repair

**Author:** MiMo-V2.6-Flash Free (`mimo-v2.6-flash-free`) — **v1.0.0**
**Proposal ID:** `docs/plans/proposal-freebuff-umaws-fleet-launcher-repair-runbook-v1.md`
**Date:** 2026-11-09
**Status:** Draft for operator review; untracked; execution not authorised until approved.
**Evidence base:** `report-freebuff-UMAWS-Fleet-Launcher-repair-v1.md` (the "source report"), read in full before execution.
**Complements (does not supersede):** `proposal-umaws-problems-and-issues-repair-v1.md` and its 16-item `pilot/repair-resumption-checklist-v1.md`. Items 1–12 and 14 of that checklist are treated here as **done** and are never restated as work; this runbook covers what remains, why previous attempts did not finish, and how recurrence is prevented.

---

## 1. Purpose, audience, and contract of use

### 1.1 Purpose

The UMAWS Fleet Launcher was diagnosed and partially repaired, but as of the source report the repair is **not landed, not green on a clean base, and not proven by a passing canary** (source report §1.7). This document is the complete, ordered instruction set that a single executing LLM agent must follow to bring the Launcher to the definition of done in §2. It is written to be executed literally, by a fresh agent with no memory of any previous session.

### 1.2 Audience

- **Primary:** an executing LLM agent. It must treat §5 (binding rules), §6 (authority), and §8 (runbook) as mandatory, not advisory.
- **Secondary:** the operator, who reviews this document before execution and appears at the five checkpoints in §6.

### 1.3 Contract of use

1. Read §1–§7 and the source report (Appendix A reading order) **before** touching the repository.
2. Execute §8 phases **in order**. Do not skip a phase. A phase whose verify-first gate already passes is recorded as "already satisfied — evidence: …" and the executor continues to the next phase. This idempotency rule exists because the repository was observed moving during authoring of this document; state must be re-measured, never assumed.
3. There are exactly **two modes of work**: card work (lease + worktree + bundle + gate) and read-only investigation. Bootstrap steps enumerated in §8 are the only sanctioned out-of-band actions, and they are enumerated precisely so they cannot be silently widened. Inventing a third mode is the failure the source report documents in §9.
4. If a step's failure branch says STOP, stop and report to the operator. Do not improvise a workaround.

### 1.4 Single-session model

The runbook is designed for one continuous supervised session. If the session is interrupted, a later agent must restart at Phase 0 (entry gate) and re-verify every prior phase's closing evidence before continuing; nothing may be assumed complete from prose alone.

---

## 2. Definition of done

The UMAWS Fleet Launcher "works properly" when **all** of the following hold, each proven by the evidence named:

| # | Condition | Proof |
|---|---|---|
| **DoD-1** | Full gate (`python -m pytest -q`) exits 0 in a **detached clean worktree** at the repaired committed base, with `PYTHONPATH` pinned to that worktree and `import cna` resolving inside it | gate log under `tmp\rb-*.log` + recorded HEAD sha |
| **DoD-2** | The combined collection defect (OQ-06) is gone: `python -m pytest -q --collect-only tests/fleet tests/pmk` exits 0 | collection log |
| **DoD-3** | The env invariant tool passes: `python tools\check_subprocess_env.py` (exit 0), covering every `src/fleet` subprocess site | tool output |
| **DoD-4** | Worktree censuses reconcile: the `pmk worktree list` vs `git worktree list` difference is fully explained, and no dirty `work/` tree is deleted without capture-and-verify (REC-02 before REC-01) | census record + archive output |
| **DoD-5** | Lease hygiene: `pmk status` shows `active_leases: 0`, and the new admission check (R-02) rejects a repo-root or expiry-less lease in a test | `pmk status` + test name |
| **DoD-6** | One **fresh supervised canary** card, created at the repaired base, flows through the real path to `DONE`, with an evidence bundle containing non-empty `gate_output` | `pmk task show <canary-id>` events `SUBMITTED → VERIFIED → INTEGRATED` + `bundle.json` |
| **DoD-7** | A decision record (next free `D-` id) with the full payload (diff, proposer, ratifier, alternatives, what it leaves untested) is ratified, and `pilot/repair-resumption-checklist-v1.md` items 13 and 15 carry evidence links | `pilot/decisions.md` + checklist |
| **DoD-8** | Every OQ/R item in §11 is either closed with evidence or explicitly deferred with a reason | §11 traceability matrix, filled |

**Explicitly not part of done:** resuming dispatch (A10) and unpausing the project are **operator decisions that occur after** this runbook completes, only on a recorded canary `PASS` (source report §10.5 step 7). The executor must not run `pmk project resume` or `pmk dispatch run` as part of this runbook.

---

## 3. Scope

### 3.1 In scope

The full engineering set from the source report: the critical path (OQ-01 base, OQ-02 lease, OQ-03 landing, OQ-04 canary) **plus** OQ-05…OQ-13 and R-01…R-14. Governance anomalies whose facts are unrecoverable (OQ-07 identity commits `e08fa8d`/`ebe46ce`, OQ-08 `Q-077`/`.pm/policy.toml` editor) are **recorded as findings with explicit `Unknown` provenance** — not investigated to closure, because the record cannot support closure (source report §11.3).

### 3.2 Out of scope

- Resuming dispatch / unpausing (operator, post-canary).
- Pushing to `origin` (the repo has never been pushed; push is the operator's separate act).
- Buffy's uncommitted CNA work and the root-level reports/assessments: **inventoried only, left as they are** (Phase 8, step 8.4), per operator instruction.
- History rewrite to fix the identity commits — **banned** (OQ-07: "do not rewrite history unilaterally").
- Model-quality evaluation, provider billing, and the product goals in `docs/PDD.md` except where an oracle is used as evidence.

---

## 4. Why previous attempts did not finish, and how this runbook prevents it

| Observed failure (source report) | Prevention mechanism here |
|---|---|
| Repair implemented but **uncommitted** — "one checkout away from losing the repair" (§1.5.3, OQ-03) | Phase 1 archives everything **before** any other act; Phase 3 lands it in reviewable slices with an explicit file list |
| Canary `T-0189` failed because the **committed base** could not satisfy its own gate (§4.5, OQ-01) | Phase 5 is verify-first against a detached clean worktree; DoD-1 cannot be claimed from a main-tree run (rule B-14) |
| The last agent worked **out-of-band on `main`** with no card, lease, bundle, or gate (§9) | §5 binding rules + §6 checkpoints + the two-modes-only contract (§1.3); bootstrap is enumerated, everything else is card work |
| A **verdict without output** made a failure unrecoverable (P-15) | Rule B-05 + R-10 (H6): every gate result and bundle carries output, not exit codes alone |
| An **inherited phantom lease** (`T-0182`) blocked resume (OQ-02) | Phase 4 verifies zero leases and installs the R-02 admission check so it cannot recur |
| State **drifted under the report's feet** (HEAD moved during authoring) | Every phase opens with a verify-first gate; the entry gate (Phase 0) re-measures instead of trusting snapshots |
| A "done" tick without evidence would repeat the pattern (checklist discipline, §2.6 of source report) | Every step names its expected output and evidence file; §10 matrix must be filled from measurements, not from memory |

---

## 5. Binding rules for the executing LLM

These are the source report's safeguards S-01…S-18, restated as MUSTs, plus host-specific rules. Violating one is grounds for stopping the runbook.

| ID | Rule |
|---|---|
| **B-01** (S-01) | MUST NOT edit `main` directly for task work. Out-of-band work is limited to the enumerated bootstrap steps in §8 and happens on the repair branch, never as ad-hoc edits to `main`. |
| **B-02** (S-02) | MUST treat any lease lacking `pid`, `expires_at`, or a `work/T-<id>-<fence>` worktree as invalid: report it, never work under it, never hand-edit `.pm/` to remove it — use `pmk revoke`. |
| **B-03** (S-03) | MUST NOT start new card work while `project_state != RUNNING`. The runbook's own bootstrap steps are operator-authorised exceptions; everything else waits. |
| **B-04** (S-04) | MUST verify with the card's `gate_cmd` (`python -m pytest -q`, per `docs/PDD.md`), never with a self-chosen subset presented as proof. |
| **B-05** (S-05) | MUST record output (stdout/stderr tail), not just an exit code, for every verdict produced or reported. |
| **B-06** (S-06) | MUST check `hint_base_commit` before trusting any `agent_hint`; empty base = unverified hint. |
| **B-07** (S-07) | MUST NOT copy files from the main tree into a worktree because a hint says they are missing — check the worktree first. |
| **B-08** (S-08) | MUST confirm `import cna` / `import pmk` resolve **inside** the tree under test (`python -c "import cna, pmk; print(cna.__file__); print(pmk.__file__)"` with the worktree's `src` on `PYTHONPATH`) before running anything. |
| **B-09** (S-09) | MUST use absolute paths for `ORDER.md`, `RESULT.md`, bundles, logs, and every artefact named. |
| **B-10** (S-10) | MUST assume **PowerShell 5.1** for every command this document gives; MUST NOT issue bash idioms (they produced 904 parser failures, P-10). |
| **B-11** (S-11) | MUST commit as the repo-local identity `umaws-pilot <umaws-pilot@localhost>`, verified with `git var GIT_AUTHOR_IDENT` before any commit; MUST NOT commit as the human operator. |
| **B-12** (S-12) | MUST NOT create or ratify a decision record without the full payload (diff, proposer, ratifier, alternatives, what it leaves untested). A `{"choice":"ratify"}` line is not a decision (Q-077/P-24). |
| **B-13** (S-13) | MUST NOT delete any worktree before capture and verify; dirty trees are refused, not forced. REC-02 (capture) precedes REC-01 (reclaim), always. |
| **B-14** (S-14) | MUST NOT describe a main-tree green run as proof about a clean base. Clean-base claims require a detached worktree at the recorded base (this is exactly what failed in `T-0189`). |
| **B-15** (S-15) | MUST NOT hand-edit `.pm/` or "tidy" its views. The Kernel is the writer. Ledger state changes go through `pmk` verbs only. |
| **B-16** (S-16) | MUST place new formal reports under `docs/reports/` unless the operator instructs otherwise; this document is the operator-designated exception at `docs/plans/` and stays untracked. |
| **B-17** (S-17) | MUST report both numbers when two authoritative counts disagree (worktrees 23-vs-35 class of problem) and explain the difference before any decision that depends on either. |
| **B-18** (S-18) | MUST record any deviation from this runbook inside the artefact produced, in the style of source report §9. A clean-looking result must not hide an unclean process. |
| **B-19** | MUST stop at every checkpoint in §6 and wait for the operator. A checkpoint that is "almost certainly fine" is still a checkpoint. |
| **B-20** | MUST re-measure at every phase gate. If the repository has moved since the last phase (new commits, new leases, new worktrees), record the delta and continue from measured state — never from this document's snapshot. |

---

## 6. Authority model

### 6.1 Operator checkpoints (mandatory stops)

| CP | Trigger | Operator decides | Recommended default (author's) |
|---|---|---|---|
| **CP-1** | Any commit to `main`, any fast-forward, any push (applies at Phase 10 and any later main commit) | Whether/when to land the branch on `main`; push remains separate | Fast-forward only (`--ff-only`), local only; **no push** |
| **CP-2** | Phase 4, only if `active_leases > 0` or an invalid lease is found | Submit vs revoke that lease | Revoke with recorded reason; deliverables preserved by Phase 1 archive |
| **CP-3** | Phase 7, before any worktree deletion/prune | Whether to delete the extra `%TEMP%/pmk-merge-*` and stale `work/` trees | Only after `pilot/repair-worktree-census-v1.md` exists and dirty trees are archived; otherwise keep (checklist tail already says "keep the eleven extra worktrees until a separate, evidence-based decision") |
| **CP-4** | Phase 12, canary outcome | Ratify the canary decision (`PASS`/`FAIL`), sentinel baseline disposition, any `Unknown`-record decisions | Ratify only what the bundle proves; `FAIL` keeps dispatch paused |
| **CP-5** | Any proposed history rewrite, or any edit to `.pm/policy.toml` or recorded pins | Always the operator; this runbook **never** performs these | Do not perform; record the finding and stop |

> **Author's assumption (flagged):** the five-checkpoint set above was inferred after the operator left the checkpoint question unanswered twice. The report itself mandates operator approval for the lease decision, landing the repair, and dispatch resume; the other two (worktree deletion, history/policy edits) are conservative additions. If the operator wants fewer stops, they must edit §6 before approval.

### 6.2 Autonomous zone (no checkpoint needed)

Read-only commands (`pmk status/task show/worktree list/fleet check/pins check/sentinel`, `git status/log/diff/rev-parse`), creating the repair branch, writing archive files outside the repo, committing **to the repair branch** with the `umaws-pilot` identity, implementing and testing the Phase 6 hardening items, writing inventory/erratum/decision-draft documents, and updating `pilot/repair-resumption-checklist-v1.md` evidence cells (ticking only what is measured).

### 6.3 Banned outright (not a checkpoint — do not propose)

Hand-editing `.pm/`; `git reset --hard` / `git checkout --` over dirty repair files; `git push`; `git rebase`/`amend` of existing history; `--no-verify` commits; deleting evidence bundles or `tmp\` logs cited by a decision; `pmk project resume` / `pmk dispatch run` (DoD-2 exclusion); fabricating a bundle or a decision payload.

---

## 7. Phase 0 — Entry gate (read-only)

**Purpose:** establish measured truth and stop conditions before anything else. **All commands read-only.**

**0.1 Required reading (in order).** Source report §1 and §9; `pilot/repair-resumption-checklist-v1.md`; `docs/reports/dispatch-failure-root-cause-and-remediation-v1.md`; `pilot/decisions.md` D-62…D-69; this document §5–§6. (Full order: source report Appendix C.)

**0.2 Authority and state capture.**

```powershell
pmk brief --role overseer
pmk status
pmk pins check
pmk fleet check
git status --short
git rev-parse HEAD
git branch --show-current
git worktree list
pmk worktree list
```

**Expected (measured 2026-11-09 at authoring):** `project_state: PAUSED`; `active_leases: 0`; `chain` verifies; `pins ok: true`; `fleet ok: true` (18 profiles); HEAD `06d3e93…` on `main`; 28 modified tracked files; Kernel worktrees 25 vs git worktrees 35+ (record both numbers — B-17).

**On failure / deviation:**

- `pins check` or `fleet check` not ok → **STOP**, report to operator (source report §10.1.6).
- `active_leases > 0` → inspect each with `pmk task show <id>`; if invalid per B-02, go to CP-2; never inherit a lease.
- HEAD or counts differ from the snapshot above → **this is expected** (B-20): record the delta in your session notes and continue; the runbook is verify-first.
- Any evidence of another agent **actively running dispatch** (new `LEASED` events, `pmk dispatch` process) → **STOP** and report; this runbook assumes single-owner execution.

**0.3 Record the entry snapshot** to `tmp\rb-0-entry.txt` (redirect the outputs above). Evidence file for the §10 matrix.

**Gate to proceed:** all read commands succeeded; stop-conditions above not triggered (or resolved via the named checkpoint).

---

## 8. The runbook

### Phase 1 — Protect the uncommitted repair (OQ-03, first half)

**Verify-first:** if an archive for today already exists and covers all 28 modified files, record its path and skip to Phase 3.

**1.1 Create the archive outside the repository.**

```powershell
$arc = "C:\temp\projects\umaws-repair-archive-2026-11-09"
New-Item -ItemType Directory -Force -Path $arc | Out-Null
git diff --binary > "$arc\tracked-changes.patch"
git status --porcelain > "$arc\working-tree-status.txt"
git worktree list    > "$arc\git-worktree-list.txt"
pmk status           > "$arc\pmk-status.json"
git log --oneline -20 > "$arc\head-log.txt"
git ls-files --others --exclude-standard | ForEach-Object {
  $dest = Join-Path $arc $_
  New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
  Copy-Item $_ $dest -Force
}
```

**Expected:** `$arc\tracked-changes.patch` non-empty; `working-tree-status.txt` line count ≥ 257; copy loop completes without access errors (if a single file refuses to copy, record it and continue — do not delete anything).

**1.2 Verify the archive.**

```powershell
(Get-Item "$arc\tracked-changes.patch").Length
@(Get-ChildItem $arc -Recurse -File).Count
```

**Expected:** patch length > 0; file count ≥ number of `??` lines in `git status --short`.

**On failure:** retry once; if the patch is still empty while `git diff --stat` shows changes, **STOP** (something is wrong with the working tree) and report.

**1.3 Create the repair branch** (working tree carries over; no file content changes):

```powershell
git switch -c repair/fleet-launcher-2026-11-09
git branch --show-current
```

**Expected:** `repair/fleet-launcher-2026-11-09`.

**Evidence:** archive path + branch name → `tmp\rb-1-protect.txt`.

---

### Phase 2 — Verify-first survey (classify remaining OQ items from measured state)

**Purpose:** because the repository moved during authoring, each open item may already be closed. Measure, classify, and record — do not assume.

**2.1 Run the classification commands:**

```powershell
git ls-files --error-unmatch tests/test_transport.py     # OQ-01 base fix landed?
pmk status                                                # OQ-02 leases; project state
git status --short | Measure-Object -Line                # OQ-03 remaining dirty count
python -m pytest -q --collect-only tests/fleet tests/pmk 2>&1 | Select-Object -Last 5   # OQ-06
git worktree list | Measure-Object -Line                 # OQ-05 census
```

**2.2 Fill this table in your session notes** (it is the input to Phases 3–8):

| OQ | Measure | Classify |
|---|---|---|
| OQ-01 | `git ls-files --error-unmatch tests/test_transport.py` exits 0? | landed → Phase 5 becomes verify-only; else execute Phase 5 |
| OQ-02 | `active_leases` | 0 → Phase 4 verify-only; else CP-2 |
| OQ-03 | modified tracked count (28 at authoring) | minus `.pm/` files (expected-dirty, excluded by policy) → Phase 3 file list |
| OQ-06 | combined `--collect-only` exit code | 0 → Phase 6/H2 verify-only; else execute H2 |
| OQ-05 | both census numbers | execute Phase 7 regardless (deletion still needs CP-3) |

**Gate:** every row classified; anything measuring *worse* than the snapshot → **STOP** and report before proceeding.

---

### Phase 3 — Land the repair on the branch (OQ-03, R-03)

**Precondition:** Phase 1 evidence exists. **Identity check (B-11):**

```powershell
git var GIT_AUTHOR_IDENT
```

**Expected:** `umaws-pilot <umaws-pilot@localhost>`. If not:

```powershell
git config user.name  "umaws-pilot"
git config user.email "umaws-pilot@localhost"
git var GIT_AUTHOR_IDENT
```

(Repo-local config only — this is not `.pm/policy.toml` and not a pins change.)

**3.1 Commit in six reviewable slices, using this explicit file list** (never `git add -A`; the working tree contains items that must stay uncommitted):

```powershell
# Slice 1 — fleet
git add src/fleet/conductor.py src/fleet/dispatcher.py src/fleet/harness.py src/fleet/legacy.py src/fleet/merge.py src/fleet/project.py src/fleet/spawn.py
git commit -m "fix(fleet): land launcher repair — env pinning, gate diagnostics, overseer fallback, precheck, identity guard"

# Slice 2 — kernel
git add src/pmk/events.py src/pmk/worktrees.py
git commit -m "fix(pmk): land worktree lifecycle — capture/verify/reclaim, census, lease guards"

# Slice 3 — tests
git add tests/fleet/test_adapter_paths.py tests/fleet/test_conductor_leases.py tests/fleet/test_fleet.py tests/fleet/test_regressions.py tests/pmk/test_worktree_lifecycle.py tests/test_subprocess_env_lint.py
git commit -m "test: land launcher repair tests (env, leases, lifecycle, precheck, identity)"

# Slice 4 — tooling
git add tools/check_subprocess_env.py
git commit -m "chore(tools): extend subprocess-env invariant checker"

# Slice 5 — pilot records and reports
git add pilot/cards/canary-replacement-v1.md pilot/decisions.md pilot/dispatch-failure-root-cause-and-remediation-v1.md pilot/repair-canary-runbook-v1.md pilot/repair-resumption-checklist-v1.md docs/reports/dispatch-failure-root-cause-and-remediation-v1.md
git commit -m "docs(pilot): land repair records — decisions D-62..D-69, checklist, canary card/runbook"

# Slice 6 — config
git add agents.toml HANDOFF.md
git commit -m "chore(config): land fleet config and handoff state"
```

**Expected:** six commits on the branch; pre-commit hook (`.githooks/pre-commit`, F-08) logs the identity.

**3.2 Verify the landing:**

```powershell
git status --short
git log --oneline main..HEAD
```

**Expected:** remaining modified files are **only** the four Kernel-written paths (`.pm/events/2026-11-07.jsonl`, `.pm/views/ledger.md`, `.pm/views/queue.md`, `.pm/views/status.md`) — these are runtime state, excluded from the repair by policy (never hand-edited; committing them is the operator's option at CP-1) — plus untracked inventory (reports, assessments, `tmp\`, scripts, `docs\plans\`, etc.) which Phase 8 inventories.

**On failure:** a file you did not intend to stage appears staged → `git restore --staged <file>` (unstage only; never discard) and re-plan the slice. Missing file from the list (file doesn't exist) → record the delta from Phase 2 and adjust; do not invent replacements.

**Gate:** `git diff main..HEAD --stat` shows only intended files; working tree matches the expected-remaining list.

---

### Phase 4 — Lease hygiene (OQ-02)

**4.1 Verify-first:**

```powershell
pmk status
```

**Expected:** `"active_leases": 0`. If 0 → record evidence, skip to 4.3 (at authoring this is already true: `T-0182` was resolved in `6cabebb`/`06d3e93` after the source report was written — verify, do not trust).

**4.2 If `active_leases > 0`:** for each lease run `pmk task show <id>`; take it to **CP-2**. Default branch (revoke):

```powershell
pmk revoke <task_id> --fence <fence> --reason "runbook Phase 4: invalid lease reconciled; deliverables preserved in umaws-repair-archive-2026-11-09"
pmk status
```

Never touch `.pm/` by hand (B-15). Never `--force` anything.

**4.3 Confirm the admission check exists (R-02).** If `tests/pmk/test_lease_admission.py` is absent at this point, it is implemented in Phase 6/H1 — record "pending H1" and continue; DoD-5 checks it at the end.

**Evidence:** `pmk status` output → `tmp\rb-4-lease.txt`.

---

### Phase 5 — Base repair and clean-base gate (OQ-01, R-01, R-09) → DoD-1

**5.1 Verify the base fix:**

```powershell
git ls-files --error-unmatch tests/test_transport.py
```

- **Exit 0 (expected at authoring — commits `9b3b70d`/`de107f8`):** the base fix is landed; record it and go to 5.2 (the gate run is the real proof either way).
- **Non-zero (file untracked):** apply the R-01 decision rule. Measured fact for the decision: `tests/test_transport.py` is a **Section-8 transport rules test** (imports `cna.rules.sec08_transport`, which is tracked; HEAD's `src/cna/engine/loop.py` contains the symbols it needs), and `coverage/rules_coverage.json` cites it in 20 places including case `8.0`. It therefore belongs to the rules baseline → **commit it**:

```powershell
git add tests/test_transport.py
git commit -m "fix(coverage): commit the Section-8 transport test that case 8.0 cites"
```

(The alternative — removing case `8.0`'s reference — is only correct if the file fails the gate at 5.2; if that happens, **STOP** and report rather than editing coverage data to make a gate pass.)

**5.2 Run the clean-base gate (this is DoD-1's proof).**

```powershell
$wt = "C:\temp\projects\umaws-gate-base"
$sha = git rev-parse HEAD
git worktree add --detach $wt $sha
$env:PYTHONPATH = "$wt\src;$wt\tests"
Push-Location $wt
python -c "import cna, pmk; print(cna.__file__); print(pmk.__file__)"
python -m pytest -q 2>&1 | Tee-Object -FilePath "C:\temp\projects\testproject1\tmp\rb-5-clean-base-gate.log"
$gateExit = $LASTEXITCODE
Pop-Location
$gateExit
```

**Expected:** the `import cna, pmk` line prints paths **inside** `$wt` (if it prints `C:\temp\projects\testproject1\src\...`, the editable-install shadowing P-01 is back — **STOP**, this is the original root cause); `python -m pytest -q` exits `0`; log ends with a pass summary.

**On failure (gate ≠ 0):** keep the worktree (do not remove), extract the failing test ids from the log tail, classify: base defect (fix in a new branch commit, rerun 5.2) vs environment defect (check PYTHONPATH) vs your own regression (git diff the slice). Record the output tail (B-05). Never "fix" by editing tests to pass without operator review.

**5.3 Cleanup only when the gate passed and no evidence is pending:**

```powershell
git worktree remove $wt
```

**Evidence:** `tmp\rb-5-clean-base-gate.log` + `$sha` → feeds DoD-1 and checklist item 13.

**5.4 R-09 (clean-base gate as a standing check).** Add `tools/check_clean_base.ps1` implementing exactly 5.2 (create detached worktree at `HEAD`, pin `PYTHONPATH`, import-check, `python -m pytest -q`, capture log, remove worktree, exit with the gate's code), and reference it from `docs/rules/windows-platform.md` as the required pre-landing check. Verify by running it once (exit 0). Commit to the branch.

---

### Phase 6 — Hardening set (OQ-06, OQ-09, OQ-11, R-02, R-04, R-05, R-06, R-07, R-08, R-10)

Each item H1…H7: implement → focused test → run the full gate (5.2 command pattern, or `python -m pytest -q` from the branch working tree for speed, with the clean-base rerun at Phase 9) → commit slice. **Verify-first:** if the item's test already exists and passes, record it and skip.

- **H1 — R-02 lease admission check (OQ-02 recurrence).** In the claim/grant path (`grep -rn "def claim" src\pmk` as the starting point), reject: (a) a lease whose `worktree` resolves to the repository root; (b) a grant that would produce no `pid`/`expires_at` while `project_state != RUNNING`. Test: `tests\pmk\test_lease_admission.py` covering both rejections and one legitimate grant. **Never weaken the existing lease lifecycle to make this pass.**
- **H2 — R-05 conftest collision (OQ-06).** Rename the fleet fixtures so `tests/fleet/conftest.py` and `tests/pmk/conftest.py` cannot shadow each other (unique names, e.g. `fleet_*` prefix, update usages). Test: `python -m pytest -q --collect-only tests/fleet tests/pmk` exits 0 (this is DoD-2).
- **H3 — R-06 reconcile wiring (OQ-09).** Call `Dispatcher.reconcile()` from Console startup; test the **startup path**, not just the method.
- **H4 — R-07 model attribution (OQ-11).** Adapters record the served model; where genuinely unknown, write an explicit `["unavailable"]` with a non-`none` source — never an empty list. Test: no emitted `MODEL_SERVED` payload / bundle field may carry `served_models: []`.
- **H5 — R-08 env lint coverage.** Extend `tools/check_subprocess_env.py` so any new `subprocess` call in `src/fleet` that does not derive its environment from `worktree_env()` fails the lint; keep the reviewed-exception list explicit. Extend `tests/test_subprocess_env_lint.py` accordingly (feeds DoD-3).
- **H6 — R-10 `gate_output` in bundles.** The merge gate already captures output (`_gate_diagnostics`, F-03); ensure the last N lines of stdout/stderr are written into `bundle.json` as `gate_output` on **failure and success**. Test: simulate a failing gate and assert `gate_output` is non-empty (feeds DoD-6).
- **H7 — R-04 merge-tree awareness.** Make `pmk worktree prune` aware of `%TEMP%\pmk-merge-*` entries and callable from the Conductor (dry-run by default, per `pmk worktree prune -h`). Test: discovery logic + dry-run output; **actual deletion happens only in Phase 7 under CP-3.**

**Phase 6 gate:** focused tests green; full `python -m pytest -q` on the branch exits 0 (log → `tmp\rb-6-hardening-gate.log`); each H item has a commit.

---

### Phase 7 — Worktree census reconciliation (OQ-05, R-04) → DoD-4

**7.1 Measure the union (B-17):**

```powershell
pmk worktree list          > tmp\rb-7-pmk-census.txt
git worktree list          > tmp\rb-7-git-census.txt
```

Record both counts and the set difference (expected: Kernel trees under `work\` plus `%TEMP%\pmk-merge-*` merge trees plus strays such as a `.claude` worktree).

**7.2 Safety first — capture every dirty tree (REC-02 before REC-01, B-13):**

```powershell
pmk worktree archive --all-dirty --dry-run
pmk worktree archive --all-dirty
```

**Expected:** each dirty tree captured under the archive root with verification; any refusal is honoured, not forced.

**7.3 Take deletion to CP-3.** Present the operator with: the union census, the archive evidence, and the fact that `pilot/repair-resumption-checklist-v1.md` tail already instructs "keep the eleven extra worktrees until a separate, evidence-based decision; `pilot/repair-worktree-census-v1.md` is the basis". If that census document does not exist, **write it first** (a dated inventory: each extra tree, origin, size, dirty/clean, recommendation) — it is the required basis.

**7.4 Only on CP-3 approval:**

```powershell
pmk worktree prune --archive --dry-run
pmk worktree prune --archive --yes
git worktree prune                       # for stale %TEMP% merge entries after removal
```

**Expected:** both censuses shrink consistently; recount and record. Refusal paths (dirty, active) are respected.

**Evidence:** census files + prune output → `tmp\rb-7-*.txt`; feeds DoD-4.

---

### Phase 8 — Governance records, errata, and inventory (OQ-07, OQ-08, OQ-10, OQ-12, OQ-13, P-25, P-31)

**8.1 Errata for stale claims (R-12).** Append an `## Erratum (2026-11-09)` section to `incident-report-worktree-lifecycle-leak-v1.md` recording the corrected facts: `write_handoff` has **three** call sites (`src/fleet/harness.py`, `src/fleet/dispatcher.py`, `src/pmk/cli.py`), and formal-report placement convention is `docs/reports/` (P-31). Do not delete the original text; append.

**8.2 Record the unrecoverable governance facts as `Unknown` (OQ-07, OQ-08).** Draft decision records (next free ids after D-69) in `pilot/decisions.md` using the full payload required by B-12/R-11: for the `e08fa8d`/`ebe46ce` identity anomaly, and for the `Q-077`/`.pm/policy.toml` edit window — each stating *decision: record as Unknown; alternatives considered; what it leaves untested; proposer: <executor>; ratifier: <operator, at CP-4>*. **No history rewrite is proposed** (CP-5/banned).

**8.3 Sentinel baseline (R-13).**

```powershell
pmk sentinel
```

If it still reports the recorded red baseline (5 × I6 + 1 × I13): draft the choice for CP-4 — default recommendation is **record as accepted-red with a named owner and a review date**, not silently described as green. If Phase 6/H6 and the Phase 11 canary have changed the missing-bundle/empty-commit conditions, re-measure first.

**8.4 Inventory of what stays uncommitted (OQ-13).** Write `docs/reports/uncommitted-inventory-2026-11-09.md` listing every remaining dirty/untracked path with disposition, per operator instruction: root-level reports and assessments (working papers), `src/cna/**` CNA work (already landed in `de107f8` where tracked — verify), `tmp\` evidence logs (retain: several are cited by decisions), helper scripts (`*.py` at root), and **this runbook** (untracked by operator decision). Disposition values: `retain-untracked`, `operator-to-decide`, `cited-evidence-retain`.

**8.5 Checklist update (evidence cells only).** Update `pilot/repair-resumption-checklist-v1.md` items 13 and 15 **only when their proofs exist** (Phase 5 log; Phase 12 canary). Tick nothing early — the checklist's own rule: "an unticked box is a blocker, not an oversight."

**Evidence:** erratum section, decision drafts, sentinel output, inventory doc → referenced in §10.

---

### Phase 9 — Whole-system verification (DoD-2, DoD-3)

**9.1 Combined collection:** `python -m pytest -q --collect-only tests/fleet tests/pmk` → exit 0 (skip if H2 verified it).
**9.2 Env invariant:** `python tools\check_subprocess_env.py` → exit 0.
**9.3 Full gate, clean base, at branch head:** repeat 5.2 with current `HEAD` → exit 0, log `tmp\rb-9-final-gate.log`.
**9.4 Integrity:** `pmk pins check` → `ok: true`; `pmk fleet check` → `ok: true`; `pmk status` → chain verifies.
**On any failure:** return to the owning phase; never proceed to Phase 10 with a red check.

---

### Phase 10 — Land on `main` (**CP-1**)

Present to the operator: branch diffstat, Phase 9 evidence, and the exact command. **Only on approval:**

```powershell
git switch main
git merge --ff-only repair/fleet-launcher-2026-11-09
git rev-parse HEAD
```

**Expected:** fast-forward (no merge commit needed since `main` has not moved; if `main` has moved, **STOP** — no rebase, no force, report). **No push** (operator's separate act). Record the new main sha — it is the canary base.

---

### Phase 11 — Fresh supervised canary (OQ-04, R-14) → DoD-6

Follow the existing standard path (`pilot/cards/canary-replacement-v1.md` + `pilot/repair-canary-runbook-v1.md` + the D-69 operator packet pattern) — do not improvise a canary design (R-14).

**11.1 Create the card** (new id; write scope is one new file):

```powershell
pmk task create "Record the repaired dispatch verification v2 (supervised canary)" --type implement --goal-ref G-001 --write docs/reports/dispatch-repair-verification-v2.md --oracle "python -c `"import pathlib; p=pathlib.Path('docs/reports/dispatch-repair-verification-v2.md'); t=p.read_text(encoding='utf-8'); assert 'rule_files=69' in t and 'CNA-Rules.adoc' in t and 'base=' in t and 'gate=pytest -q' in t; print('verified')`"" --agent-hint "Your worktree base is the repaired tree at the commit pinned when this card was created. docs/rules/CNA-Rules.adoc and docs/rules/sections/ (66 corpus files) ARE present; copy nothing. Operate only inside your worktree. Read coverage/rules_coverage.json and note rule_files=69. Write exactly one file, docs/reports/dispatch-repair-verification-v2.md, containing: base=<actual sha from git rev-parse HEAD>; corpus=docs/rules/CNA-Rules.adoc present; rule_files=69; gate=pytest -q. Do not edit any other file. Commit nothing; the harness commits. Then stop." --propose
```

**11.2 Precheck at the new base** (already-satisfied guard, F-06):

```powershell
pmk task precheck <canary-id> --base <main-sha-from-Phase-10>
```

**Expected:** oracles satisfiable on both base and scratch tree. If not satisfiable, **STOP** — the base is still wrong; return to Phase 5.

**11.3 Admit and dispatch through the real path:**

```powershell
pmk task admit <canary-id>
```

then run the dispatch exactly as `pilot/repair-canary-runbook-v1.md` prescribes for a supervised canary (the launcher/loop command is recorded there — use it; do not hand-drive the worker).

**11.4 Judge only from recorded evidence:**

```powershell
pmk task show <canary-id>
```

**Expected for PASS:** events `SUBMITTED` → `VERIFIED` (class ok) → `INTEGRATED` → state `DONE`; bundle `.pm\evidence\EB-<canary-id>-<fence>\bundle.json` exists with non-empty `gate_output` (H6); `main` advanced to include the integration.

**On FAIL:** record the failing test id and the `stdout_tail` (already captured — the P-15 loss must not recur); take to CP-4 as a `FAIL`; dispatch stays paused; return to the owning phase. Do not retry the canary more than once without operator instruction.

---

### Phase 12 — Decision, acceptance, handoff (**CP-4**)

**12.1 Decision record.** Draft (operator ratifies at CP-4) the canary decision — next free `D-` id — with the full B-12 payload: date, who, decision (`PASS`/`FAIL`), the diff/base/sha, bundle path, alternatives, what it leaves untested, proposer/executor, ratifier/operator.

**12.2 Checklist.** Update `pilot/repair-resumption-checklist-v1.md`: item 13 ← Phase 5/9 log; item 15 ← canary evidence; item 16 remains **blocked** with note "A10 is the operator's decision on a recorded PASS".

**12.3 Completion report.** Write `docs/reports/fleet-launcher-repair-completion-v1.md` (formal report → `docs/reports/`, B-16): what was executed vs this runbook (deviations recorded per B-18), the filled §10 matrix, remaining deferrals, and the exact operator commands that remain (`pmk project resume --reason ...` and `pmk dispatch run` — **not executed**).

**12.4 Final state capture:** `pmk status`, `git status --short`, `git log --oneline -10`, both censuses → `tmp\rb-12-final.txt`.

**12.5 Hand back to the operator** with: DoD matrix (§10), the CP-4 decision awaiting ratification, and an explicit statement of what is NOT done (dispatch resume, push, sentinel disposition if still open).

---

## 9. Operator checkpoint quick-reference

| When | What you are asked | If you say no |
|---|---|---|
| CP-1 (Phase 10) | Fast-forward `main` to the green branch | Branch stays; nothing lands; system remains unrepaired on `main` |
| CP-2 (Phase 4, conditional) | Revoke/submit a found lease | Lease stays; executor stops (B-02) |
| CP-3 (Phase 7) | Delete extra/dirty worktrees | Trees stay; censuses recorded with the difference explained (B-17) |
| CP-4 (Phase 12) | Ratify canary decision + sentinel disposition + `Unknown` records | Records stay draft; dispatch stays paused regardless |
| CP-5 (anytime) | History/policy/pins changes | This runbook never performs them; findings are recorded only |

---

## 10. Definition-of-done verification matrix (fill from measurements, not memory)

| DoD | Command | Expected | Measured value | Evidence file |
|---|---|---|---|---|
| DoD-1 | `python -m pytest -q` in detached worktree at main sha, PYTHONPATH pinned | exit 0 | _pending_ | `tmp\rb-9-final-gate.log` |
| DoD-2 | `python -m pytest -q --collect-only tests/fleet tests/pmk` | exit 0 | _pending_ | H2 test output |
| DoD-3 | `python tools\check_subprocess_env.py` | exit 0 | _pending_ | tool output |
| DoD-4 | `pmk worktree list` vs `git worktree list` + archive evidence | difference fully explained; no un-captured deletion | _pending_ | `tmp\rb-7-*` |
| DoD-5 | `pmk status` + `tests\pmk\test_lease_admission.py` | `active_leases: 0`; test passes | _pending_ | `tmp\rb-4-lease.txt` + test |
| DoD-6 | `pmk task show <canary-id>` + `bundle.json` | `DONE`; `gate_output` non-empty | _pending_ | bundle path |
| DoD-7 | `pilot/decisions.md` + checklist | decision ratified w/ full payload; items 13/15 carry evidence | _pending_ | doc sections |
| DoD-8 | §11 matrix below | every row closed or deferred-with-reason | _pending_ | §11 |

---

## 11. Traceability matrix (OQ/R/S → phase)

| Item | Source report | Runbook location | Status key |
|---|---|---|---|
| OQ-01 / R-01 / R-09 | Critical base defect | Phase 5 (5.1 verify-first, 5.2 gate, 5.4 standing check) | closed-by-9b3b70d? → verify at Phase 2 |
| OQ-02 / R-02 | Phantom lease | Phase 4 (verify/revoke, CP-2) + Phase 6/H1 (admission check) | `active_leases: 0` at authoring → verify-first |
| OQ-03 / R-03 | Uncommitted repair | Phase 1 (archive) + Phase 3 (six slices) | open (28 files at authoring) |
| OQ-04 / R-14 | No passing canary; A10 blocked | Phase 11 + Phase 12 (operator A10, excluded from DoD) | open |
| OQ-05 / R-04 | Census disagreement; stale merge trees | Phase 7 (measure, archive, CP-3) + Phase 6/H7 (prune awareness) | open |
| OQ-06 / R-05 | conftest collision | Phase 6/H2 → DoD-2 | open at authoring (verify at Phase 2) |
| OQ-07 | Identity commits `Unknown` | Phase 8.2 (record `Unknown`; rewrite banned) | record-only, by scope (§3.1) |
| OQ-08 / R-11 | `Q-077`/policy edit `Unknown` | Phase 8.2 + decision-template payload (B-12) | record-only, by scope |
| OQ-09 / R-06 | `reconcile()` not wired | Phase 6/H3 | open |
| OQ-10 / R-12 | Documentation drift | Phase 8.1 (erratum) | open |
| OQ-11 / R-07 | Model attribution empty | Phase 6/H4 | open |
| OQ-12 / R-13 | Sentinel red baseline | Phase 8.3 (CP-4 disposition) | open |
| OQ-13 | Author's uncommitted work/report | Phase 8.4 (inventory) + §3.2 (scope) | inventory-only, by scope |
| S-01…S-18 | Safeguards | §5 B-01…B-18 (all embedded) | binding |
| P-01…P-33 | Problem register | Covered via the OQ/R rows above; P-class causes (env, hints, shell, evidence) are guarded by B-08/B-06/B-10/B-05 | — |
| F-01…F-19 | Fix register | Landed/local items are committed in Phase 3; documented items are referenced, not redone | verify at Phase 2/3 |

**Explicit deferrals (with reasons):** dispatch resume & project unpause → operator, by DoD definition (§2); push to remote → operator (repo has never been pushed); history rewrite → banned (CP-5); `.pm/` runtime-state commits → operator option at CP-1; investigation-to-closure of OQ-07/OQ-08 → impossible from the record (source report §11.3), recorded as `Unknown` instead.

---

## 12. Assumptions and flagged guesses (author's disclosure)

1. **Five operator checkpoints (§6.1)** were inferred after the checkpoint question went unanswered twice; the report mandates three of them. *Adjust §6 before approval if wrong.*
2. **Base-fix state:** measured during authoring that `9b3b70d`/`de107f8` already committed `tests/test_transport.py` and its dependencies, and that `T-0182` was already resolved (`6cabebb`/`06d3e93`). Phases 4 and 5 are therefore written verify-first; if a later measurement disagrees, the execute-branches apply.
3. **Commit slice file list** (Phase 3) is taken from the 28 modified files measured at authoring minus the four `.pm/` paths; if the dirty set differs at execution, adjust the list by the same classification rule and record the delta (B-18).
4. **`.pm/` commit policy** (runtime state stays uncommitted) is the author's reading of "the Kernel is the writer"; the operator may elect to commit it at CP-1.
5. **Canary dispatch mechanics** are delegated to `pilot/repair-canary-runbook-v1.md` rather than restated, because that runbook records the actual launcher invocation used for `T-0189`; the author did not re-derive it.
6. **New artefact names** (`tmp\rb-*` evidence files, `tools/check_clean_base.ps1`, `docs/reports/uncommitted-inventory-2026-11-09.md`, `docs/reports/fleet-launcher-repair-completion-v1.md`, canary id `v2`) are proposals by this document; rename freely as long as §10's evidence cells point at the real paths.
7. **Concurrent activity observed:** files appeared and disappeared in the working tree during authoring (e.g. `docs/reports/proposal-umaws-fleet-launcher-repair-execution-v1.md` existed in `git status` and was gone moments later). Phase 0's single-owner stop condition exists because of this; confirm no other agent is running before execution.
8. **No example of this document type exists** in the repo — it is a hybrid of a formal proposal (frontmatter, registers, rationale) and an executable runbook (phases, commands, failure branches), modelled on the source report's structure and the checklist's evidence discipline.

---

## Appendix A — Required reading order for the executor

1. This document §1–§7.
2. `report-freebuff-UMAWS-Fleet-Launcher-repair-v1.md` §1 and §9 (what happened; how the last agent behaved).
3. `pilot/repair-resumption-checklist-v1.md` (done / failed / blocked).
4. `docs/reports/dispatch-failure-root-cause-and-remediation-v1.md` (technical root cause).
5. `pilot/decisions.md` D-62…D-69 (especially D-69 `FAIL`).
6. Source: `src/fleet/runenv.py`, `merge.py`, `harness.py`, `conductor.py`, `src/pmk/worktrees.py`.

Reading source first invites a local fix to a systemic problem; read the record first (source report Appendix C).

## Appendix B — State snapshot at authoring (2026-11-09, for comparison only — re-measure, B-20)

| Fact | Value |
|---|---|
| HEAD | `06d3e93e23020a0b9245b7760ed500c45c8165f6` (main, local, never pushed) |
| New since source report | `9b3b70d` (base fix), `de107f8` (transport rules/data), `6cabebb`+`06d3e93` (T-0182 landed) |
| Project state | `PAUSED`; `active_leases: 0`; chain verifies (3,491 events) |
| Tasks | 189 total: 37 `DONE`, 143 `VOID`, 8 `PROPOSED`, 1 `REWORK` (T-0189) |
| Dirty tracked files | 28, +1943/−438 (repair minus what the four new commits landed) |
| Worktrees | 25 Kernel (`pmk`) vs 35+ git entries incl. `%TEMP%\pmk-merge-*` |
| Known-open at authoring | OQ-03 (28 files), OQ-04 (canary), OQ-05, OQ-06, OQ-09…OQ-13; OQ-01/OQ-02 appear closed → verify-first |
| `gate_cmd` | `python -m pytest -q` (`docs/PDD.md` line 51) |

---

**Provenance statement.** This document was authored by MiMo-V2.6-Flash Free (`mimo-v2.6-flash-free`) as version 1.0.0 on 2026-11-09 from read-only inspection of the repository, the source report, the `pmk` CLI help output, and live `pmk`/`git` measurements recorded in Appendix B. No `.pm/` file was edited, no task was claimed or transitioned, no commit was made, and this file was written untracked by explicit operator instruction. Where the operator's answers were unavailable, the assumptions are disclosed in §12 rather than hidden.
