---
document:
  title: "Project Proposal (Synthesized): UMAWS Fleet Launcher — Repair Landing, Clean-Base Verification, Supervised Canary and Handback (execution brief for an implementing LLM agent)"
  status: "Execution-ready. Operator-approved 2026-11-09 by interview; supersedes the three source proposals listed in Appendix E for execution (they remain cited provenance and evidence). Assessor signature pending — see provenance."
  version: "1.0.0"
provenance:
  author_llm:
    name: "GLM-5.3-Flash Free"
    version: "opencode/glm-5.3-flash-free; synthesized proposal v1.0.0"
  assessor_llm: ["Tiwa Pene (Human)"]
  # assessor_llm is deliberately left empty: the human operator signs this field
  # (name/version "Human") at countersignature, per operator instruction 2026-11-09.
  created_date: "2026-11-09"
  last_modified_date: "2026-11-09"
  scope: "C:\\temp\\projects\\testproject1 (branch main), measured 2026-11-09 at HEAD e7d2725 during synthesis (see section 2); the Kernel ledger .pm/events/*.jsonl; the uncommitted repair in src/fleet/**, src/pmk/**, tools/**, tests/**; the work/ worktrees; the reports, checklists and decisions cited in Appendix A; and the three superseded source proposals in Appendix E."
  source_of_truth: "The Kernel ledger (.pm/events/*.jsonl) and the outputs of pmk status / task show / worktree list / fleet check / pins check as re-measured by the executor at entry — never this document's figures, and never any snapshot in a source proposal. Documents inform; the ledger decides."
audience:
  primary: "An implementing LLM agent (agent-neutral: any capable coding agent) executing under this repository's AGENTS.md operating contract on Windows / PowerShell 5.1, with no memory of any prior session."
  secondary: "The human operator — approval authority at five named checkpoints (section 6) and sole ratifier of the final decision."
authority_statement: "This document is an execution brief. The operator has approved its programme by interview on 2026-11-09 and reserved to themselves exactly the five checkpoint decisions of section 6, plus dispatch resumption (A10), push to origin, and any history/policy/pins change. Between checkpoints the executor is expected to act without asking; every executor-facing choice in this document carries explicit decision criteria. Where this document and a project governance document (AGENTS.md, CLAUDE.md, docs/PDD.md) disagree, the governance document wins and the executor records the conflict in its completion report."
---

# Project Proposal (Synthesized): UMAWS Fleet Launcher — Repair Landing, Clean-Base Verification, Supervised Canary and Handback

**Proposal ID:** `proposal-synthesized-umaws-fleet-launcher-repair-v1`
**Author:** GLM-5.3-Flash Free (opencode) — **v1.0.0**
**Date:** 2026-11-09
**Audience:** the implementing LLM agent (executor), with the human operator as checkpoint authority.
**Supersedes for execution:** `proposal-deepseek-umaws-fleet-launcher-repair-v1.md`, `proposal-glm-5-3-umaws-fleet-launcher-repair-execution-v1.md`, `proposal-mimo-2-6-freebuff-umaws-fleet-launcher-repair-runbook-v1.md` (all in `docs/plans/`). Their problem evidence and registers remain authoritative; their conflicting execution policies are resolved in Appendix E per operator decisions of 2026-11-09.

> **Document-control note.** This document lives in `docs/plans/` by explicit operator instruction — an exception to the `docs/reports/` formal-placement convention (P-31), recorded here as the other source documents were. Its disposition (commit with the pilot-records slice, or remain untracked) is an operator option at CP-1; the default is to commit it with slice S4.

**Done condition (one sentence):** the uncommitted repair is protectively captured and landed on `main` through an operator-gated fast-forward; the gate (`python -m pytest -q`, `docs/PDD.md` line 51) is green in a detached clean worktree at the recorded landed base; a fresh supervised canary card reaches **`DONE`** through the real Launcher path with an evidence bundle carrying non-empty gate output; and a draft decision record (**D-70** or next free id) awaits operator ratification. The executor then **stops and reports**. Dispatch resumption and push are **not** part of done.

---

## Contents

1. Purpose and overview
2. State at synthesis — fresh measured baseline, drift, and the concurrent-actor warning
3. Authorizations in force
4. Hard constraints — never do
5. Binding rules of engagement
6. Operator checkpoints (CP-1…CP-5)
7. The runbook — phases 0–12
8. Evidence requirements across phases
9. Rollback, recovery, and the never-shortcut list
10. Completion report requirement
11. Aborting, blocking, and escalation
12. Out of scope — record-only backlog
13. Definition-of-done verification matrix
14. Traceability matrix (OQ / R / S → phase)
15. Assumptions and flagged guesses (author's disclosure)
- Appendix A — Required reading order for the executor
- Appendix B — Slice inventory for Phase 3
- Appendix C — Prohibited / notify-only action summary
- Appendix D — Provenance and change log
- Appendix E — Source disposition: what was taken from each proposal, and how conflicts were resolved

---

## 1. Purpose and overview

### 1.1 What this document is

The single, decision-complete instruction set that one implementing LLM agent follows to carry the UMAWS Fleet Launcher from its current state — repair implemented but uncommitted, clean-base gate red at HEAD pending the landing, no passing canary — to a landed, clean-base-proven, canary-proven state with a draft decision awaiting the operator. It synthesizes three competing proposals, resolves their conflicts per explicit operator decisions, and is written to be executed literally by a fresh agent with zero prior context.

### 1.2 Why it exists

`report-freebuff-UMAWS-Fleet-Launcher-repair-v1.md` diagnosed the dispatch failure exhaustively (registers P-01…P-33, F-01…F-19, OQ-01…OQ-13, S-01…S-18, R-01…R-14) and recorded that its own repair work was unlanded and its canary had failed. Three subsequent LLM proposals agreed on the diagnosis but disagreed on execution policy — landing mechanism, push, scope, checkpoints, and status — and each carried a stale state snapshot. The operator has adjudicated every conflict (Appendix E). The gap is no longer diagnosis; it is **landing, reconciliation, and proof**.

### 1.3 The decisive premise (two modes only)

There are exactly two modes of work on this repository:

1. **Card work through the Launcher** — claim a card, lease it, work in `work/<task>-<fence>`, submit, let the oracles decide.
2. **Read-only investigation** — no edits, no transitions.

There is no third mode. Every failure in the record came from inventing a third mode. This programme is built out of mode 2 (Phases 0, 2, and the census work) and mode 1 (Phase 6 hardening cards, the Phase 11 canary), plus one **enumerated bootstrap exception**: landing the already-written, already-reviewed repair (Phases 1, 3, 10) on a branch, because card worktrees are created from a base commit and mechanically cannot receive changes that exist in no commit. The bootstrap exception is limited to the exact steps of Phases 1, 3 and 10 and may not be silently widened (rule S-18 spirit); everything else is card work or read-only.

### 1.4 How to read this document

Each phase states its **purpose**, **verify-first gate** (re-measure before trusting any snapshot, including this one), **steps** with PowerShell 5.1 commands, **evidence** required, and a **gate to the next phase**. Phases are ordered by dependency. Do not reorder without recording why. Where the exact command form is uncertain it is tagged **`[VERIFY]`** — discover it via `pmk --help` / `pmk task --help` / `--help` on the tool, record what you found, and proceed; never invent it.

---

## 2. State at synthesis — fresh measured baseline, drift, and the concurrent-actor warning

All figures below were measured read-only on 2026-11-09 during synthesis of this document. Treat every figure in every document — including this one — as a **claim**; Phase 0 exists to supersede it. Claim vocabulary: **Confirmed** (measured here), **Derived** (inferred from evidence), **Unknown** (record cannot establish).

### 2.1 Fresh census (Confirmed, 2026-11-09)

| Measure | Value |
|---|---|
| Branch / HEAD | `main` / `e7d2725` |
| Recent commits | `e7d2725` docs(evidence): H1-H4 deletion-safety patch at c1fac8f · `4e72901` test(fleet): cover AGENT_STARTED write failure · `06d3e93` merge: T-0182 · `6cabebb` · `de107f8` · `9b3b70d` |
| Project state | `PAUSED`; `open_queue_items: 0` |
| Tasks | 189 total: 37 `DONE`, 143 `VOID`, 8 `PROPOSED`, **1 `READY` (T-0189)** |
| Active leases | **0** |
| Chain | verifies; 3,495 events; incidents 103 |
| Kernel worktrees | **29** (≈367.3 MiB); **6 dirty** (`H1-H4-clean-*` ×2, `T-0142-119`, `T-0145-122`, `T-0146-124`, `T-0189-156`) |
| Git worktree entries | **41** total: 29 under `work/`, 1 main, 1 `.claude/worktrees/…`, 10 `%TEMP%/pmk-merge-*` |
| Dirty tracked set | **31 files, +2298/−451**; 276 porcelain entries |
| Clean-base gate | **PASS at `06d3e93`** (1131 tests, exit 0; ledger seq 3493, human operator) · **FAIL at `4e72901`** (1 failure: `test_a_failed_agent_started_write_kills_the_process_and_gives_up_the_lease` — the matching harness fix is still uncommitted; ledger seq 3494) |
| `tests/test_transport.py` | tracked (Confirmed via `git ls-files --error-unmatch`) — OQ-01 base fix landed in `9b3b70d`/`de107f8` |
| Commit identity | `umaws-pilot <umaws-pilot@localhost>` already effective (Confirmed via `git var GIT_AUTHOR_IDENT`) |
| `gate_cmd` | `python -m pytest -q` (`docs/PDD.md` line 51) |
| Disabled fleet profiles (measured from FLEET_ASSIGNED, seq 3477) | `pi-orca-deepseek`, `pi-orca-glm-5-3-flash`, `pi-orca-hy4-preview`, `pi-orca-hy3` — never select for any spawn |
| Foreign work discovered | branch `h1-h4-deletion-safety-v1` (39c0dc1) checked out at `work/h1-h4-branch-1794218000`; `work/H1-H4-clean-*` ×2 (dirty); `work/gate-*` ×2 (operator gate runs, clean); a deletion-safety patch committed as evidence at `e7d2725` |
| `T-0189` | **`READY`** (operator `TASK_READY`, seq 3495, 2026-11-09T10:31Z); fence 156; `hint_base_commit bcf145c` (stale); attempts 1/1 consumed; expired kilo lease record in history — preserve it; worktree `work/T-0189-156` dirty (1 entry) |
| `T-0182` | `DONE`; historical lease record (repo-root worktree, no pid/expiry) preserved — never delete or rewrite it |

### 2.2 What changed after the three source proposals were written

| # | Source said | Measured now | Consequence |
|---|---|---|---|
| Δ-1 | HEAD `06d3e93` (DeepSeek/MiMo) or `de107f8` (GLM) | `e7d2725` — two new commits: a **regression test** (`4e72901`) landed ahead of its matching **harness fix** (still uncommitted) | The clean-base gate at HEAD is **red until the repair lands**. Phase ordering (land → verify) is now measurably mandatory, not merely principled. |
| Δ-2 | `T-0189` `REWORK` | **`READY`** — the operator ran `TASK_READY` (seq 3495) | The operator has designated the retry vehicle. Attempts are exhausted (1/1) and the hint base is stale, so Phase 11 prefers a **fresh canary card**; `T-0189`'s final disposition is a CP-4 decision. |
| Δ-3 | Dirty set 28 files (+1943/−438) | **31 files (+2298/−451)** | Phase 3 re-inventories the current dirty set; the file lists in Appendix B are the baseline, adjusted by the classification rule. |
| Δ-4 | Worktrees 23–25 Kernel vs 35–37 git | **29 vs 41**; 6 dirty; two new `H1-H4-clean-*` trees and one foreign branch | The census still disagrees — Phase 7 starts from the union. The `h1-h4-deletion-safety-v1` branch is **another actor's work: protect, never touch, coordinate at CP-3**. |
| Δ-5 | Chain 3,485–3,492 events | 3,495 events; three **human** supervisor events 09:41–10:31Z (gate runs recorded on T-0189, `TASK_READY`) | The operator is actively driving verification. Concurrent-actor discipline (§2.3) applies; treat the operator's recorded gate runs as evidence, not as your own proof. |
| Δ-6 | Disabled profile: `pi-orca-deepseek` (GLM A-11) | **Four** disabled profiles (see census) | The profile restriction applies to whatever `pmk fleet check` marks disabled at execution time — re-measure, do not rely on this list. |

### 2.3 Concurrent-actor warning

The repository moved **during the synthesis of this document** and moved again after each source proposal was written. Therefore, for the executor:

- **Always re-measure immediately before you mutate.** A count taken five minutes ago may be stale.
- Before claiming a card or committing, check for new commits, new leases, and a running dispatch loop (Phase 0, Step 0.1).
- **Never `git checkout` / `git reset` / `git clean` the working tree** to "get a clean state" — it would destroy the uncommitted repair and may race another actor. Protect first (Phase 1).
- If you detect an active lease that is not yours, stop and reconcile through `pmk`; do not inherit it (N-11).
- If the operator's session appears mid-flight (new human ledger events), record the overlap in your run log; their recorded gate outputs are evidence you may cite, never evidence you may skip.

### 2.4 Re-baseline command block (run in Phase 0; paste output into your evidence file)

```powershell
# From C:\temp\projects\testproject1 — all read-only
git rev-parse HEAD; git branch --show-current
git log --oneline -10
git status --porcelain | Measure-Object -Line
git diff --shortstat
git worktree list
pmk status
pmk worktree list
pmk fleet check
pmk pins check
pmk task show T-0189
pmk task show T-0182
git ls-files --error-unmatch tests/test_transport.py
git var GIT_AUTHOR_IDENT
# Write outputs to your evidence directory (a NEW file under .pm\evidence\ is
# acceptable capture; hand-editing Kernel-owned .pm files is never acceptable).
```

---

## 3. Authorizations in force

Granted by the operator, 2026-11-09, by interview (conflict resolutions recorded in Appendix E). Anything not listed here is **not authorized**.

| # | Authorization | Scope and rules |
|---|---|---|
| **A-1** | **Scope** | Phases 0–12 of this document. Engineering extras limited to the Phase 6 hardening set (H1…H7). Everything else record-only (§12). |
| **A-2** | **Done condition** | Canary `DONE` + draft decision. Dispatch resumption (`A10`) and push are **not** part of done and are reserved to the operator (A-7, A-8). |
| **A-3** | **Target agent** | Agent-neutral. If the executor is Buffy, it must read its own report §9 self-audit first and take S-01…S-18 as binding on itself. |
| **A-4** | **Landing mechanism** | Protective capture (Phase 1) → repair branch with reviewable slice commits (Phase 3, enumerated bootstrap exception) → operator-gated `--ff-only` merge to `main` (Phase 10, CP-1). Direct-to-`main` commits by the executor are **not** authorized. |
| **A-5** | **New engineering work** | Phase 6 items land **via pmk cards** through the normal pipeline (claim → lease → worktree → gate → merge). The card pipeline is the work. |
| **A-6** | **T-0182 lease record** | Resolved (`DONE`); its historical lease record is preserved. No action beyond Phase 4 verification. |
| **A-7** | **Push** | **Prohibited.** Local only for the entire programme; the first push is the operator's separate act, if ever. |
| **A-8** | **Project state / A10** | Reserved to the operator. The executor never runs `pmk project resume`, never runs `pmk dispatch run` outside the single supervised canary of Phase 11, and never changes `project_state`. |
| **A-9** | **Live agents** | Authorized. Prefer the fake CLI for mechanism tests; reserve live runs for the canary. Profile restriction: any spawn uses a **non-disabled** profile per the current `pmk fleet check`; if none is viable, stop and report (§11). |
| **A-10** | **Canary supervision** | The executor runs the canary autonomously and presents the full evidence bundle afterwards; the **operator ratifies** the decision (CP-4). The executor drafts; it does not ratify (N-14). |
| **A-11** | **Checkpoints** | The executor stops at CP-1…CP-5 (section 6). Between checkpoints it acts autonomously on the decision criteria in this document and does not ask. |
| **A-12** | **CNA work** | Protect, don't touch. Any still-untracked CNA fragments go into the Phase 1 capture; never judge, never commit as product work, never revert (the two landed commits `9b3b70d`/`de107f8` aside). |
| **A-13** | **Governance items** (P-23, P-24, OQ-07, OQ-08, sentinel baseline, report-placement drift) | **Record-only.** Document observations in the completion report; take no remedial action. |
| **A-14** | **Foreign branches/worktrees** (`h1-h4-deletion-safety-v1`, `H1-H4-*`, `gate-*`, `.claude` tree) | Census and protect (Phase 1, Phase 7). Never modify, never delete except via CP-3 with the operator. Verify Phase 6 H-items against that branch's patch (`e7d2725` evidence) before re-implementing anything. |

---

## 4. Hard constraints — never do

Absolute. Violating any of these aborts the programme (§11). Distilled from S-01…S-18, the source proposals' N/RL registers, and the operator's decisions; all remain binding.

| # | Never | Why (from the record) |
|---|---|---|
| **N-01** | Never edit `main` directly for task work; no new out-of-band work beyond the enumerated bootstrap (§1.3) | Out-of-band main-tree edits are invisible to the Kernel and unprotected by a fence (P-01). |
| **N-02** | Never hand-edit anything under `.pm/` (events, views, policy, pins) | The Kernel is the writer (AGENTS.md); hand edits break ledger provenance. |
| **N-03** | Never push, never force-push, never `reset --hard`, never rebase/amend shared history, never `--no-verify`, never bypass a guard | A-7; destroys evidence and the audit trail (P-23, D-67, F-07/F-08). |
| **N-04** | Never commit as the human operator | P-23. Verify `git var GIT_AUTHOR_IDENT` resolves to `umaws-pilot <umaws-pilot@localhost>` before **every** commit. |
| **N-05** | Never trust a green main/dirty tree as proof about a clean base | P-26 caused the `T-0189` failure exactly this way (S-14). Proof lives in a detached clean worktree at a recorded base. |
| **N-06** | Never record or accept a verdict as a bare exit code | P-15. Every verdict carries captured stdout/stderr with the tree and base it ran in. |
| **N-07** | Never choose your own tests for acceptance verification | S-04. The card's oracles and the project `gate_cmd` decide. |
| **N-08** | Never copy files from the main tree into a worktree because a hint claims they are missing | P-05/P-06/S-07 — check the worktree first. |
| **N-09** | Never spawn through a disabled profile, or any profile the current `pmk fleet check` marks disabled | P-12/A-9; measured disabled set in §2.1. |
| **N-10** | Never flip `project_state`, never authorize `A10`, never run `pmk dispatch run` outside Phase 11's single supervised canary | A-8. Even if everything is green. |
| **N-11** | Never inherit a lease silently — audit any lease before working near it; resolve yours before stopping | P-20/P-27; `T-0182` is the standing counterexample. |
| **N-12** | Never delete or overwrite the Phase 1 protective capture | It is the undo path for everything; it survives until the operator says otherwise. |
| **N-13** | Never ratify a decision yourself | A-10. You draft; the operator ratifies. A thin `{"choice":"ratify"}` is not a decision record (P-24/Q-077). |
| **N-14** | Never delete a worktree before capture-and-verify; dirty trees are refused, not forced | P-17/P-18/P-22; REC-02 (capture) precedes REC-01 (reclaim), always. |
| **N-15** | Never weaken an existing lease/guard mechanism to make a test pass | The guards exist for exactly the failures in the record; weakening them recreates the defects. |
| **N-16** | Never `git add -A` / `git add .` | The working tree contains Kernel state, scratch artefacts and foreign work that must never be swept into a commit. |

---

## 5. Binding rules of engagement

The source report's safeguards S-01…S-18, restated as MUSTs and cross-referenced to section 4 where they became hard constraints. Violation is grounds for stopping the runbook.

| ID | Rule |
|---|---|
| **B-01** (S-01) | Card work happens in the card's `work/` worktree; never on `main` (N-01). |
| **B-02** (S-02) | Treat any lease lacking `pid`, `expires_at`, or a `work/T-<id>-<fence>` path as invalid: report it, never work under it, reconcile via `pmk` only. |
| **B-03** (S-03) | No new card work while `project_state != RUNNING`, except the enumerated bootstrap and the Phase 11 canary. |
| **B-04** (S-04) | Verify with the card's oracles and `gate_cmd` (`python -m pytest -q`), never a self-chosen subset presented as proof (N-07). |
| **B-05** (S-05) | Record output (stdout/stderr tail), never a bare exit code (N-06). |
| **B-06** (S-06) | Check `hint_base_commit` before trusting any `agent_hint`; empty/stale base = unverified hint. |
| **B-07** (S-07) | Check the worktree first; never copy from main to "help" a hint (N-08). |
| **B-08** (S-08) | Before running anything in a tree, confirm `import cna` / `import pmk` resolve **inside that tree** (pin `PYTHONPATH` per `src/fleet/runenv.py::worktree_env()` semantics). |
| **B-09** (S-09) | Use absolute paths for `ORDER.md`, `RESULT.md`, bundles, logs, and every named artefact. |
| **B-10** (S-10) | PowerShell 5.1 only; never bash idioms (they produced 904 parser failures, P-10). |
| **B-11** (S-11) | Commit only as `umaws-pilot <umaws-pilot@localhost>`, verified before every commit (N-04). |
| **B-12** (S-12) | Decision records carry the full payload: date, who, decision, the diff/artefact under decision, alternatives, what it leaves untested, proposer, ratifier. |
| **B-13** (S-13) | Capture-and-verify before any worktree deletion (N-14). |
| **B-14** (S-14) | Never describe a main-tree green run as proof about a clean base (N-05). |
| **B-15** (S-15) | `.pm/` is Kernel-written (N-02); committing its runtime state is an operator option at CP-1, never an executor act. |
| **B-16** (S-16) | Formal reports go to `docs/reports/` unless the operator instructs otherwise; `docs/plans/` placements are recorded operator exceptions. |
| **B-17** (S-17) | When two authoritative counts disagree, report both and explain before any decision that depends on either. |
| **B-18** (S-18) | Record every deviation inside the artefact you produce. A clean-looking result must not hide an unclean process. |
| **B-19** | Re-measure at every phase gate; if the repository moved, record the delta and continue from measured state (§2.3). |
| **B-20** | Single supervised session by design. If interrupted, the successor agent restarts at Phase 0 and re-verifies every prior phase's closing evidence before continuing; nothing is assumed complete from prose alone. |

---

## 6. Operator checkpoints (CP-1…CP-5)

Mandatory stops. A checkpoint that is "almost certainly fine" is still a checkpoint (B-19/B-20 of the source runbook). Between checkpoints the executor does not ask (A-11).

| CP | Trigger | Operator decides | Recommended default (author's) |
|---|---|---|---|
| **CP-1** | Phase 10 — landing the green branch on `main` | Whether/when to fast-forward; disposition of this document and of `.pm/` runtime-state commits | `--ff-only`, local only, no push; commit this document with slice S4 |
| **CP-2** | Phase 4 — only if an active or invalid lease is found | Revoke vs submit that lease | Revoke via `pmk` with recorded reason; deliverables preserved by the Phase 1 archive |
| **CP-3** | Phase 7 — before any worktree deletion/prune | Which trees to delete | Only after the census document exists and every dirty tree is captured-and-verified; keep everything else (including the foreign `H1-H4-*`/`gate-*` trees) |
| **CP-4** | Phase 12 — canary outcome | Ratify the decision (`PASS`/`FAIL`); sentinel-baseline disposition; `Unknown`-record decisions; `T-0189` final disposition | Ratify only what the bundle proves; `FAIL` keeps dispatch paused |
| **CP-5** | Any time — proposed history rewrite, or any edit to `.pm/policy.toml` or recorded pins | Always the operator; this programme never performs these | Do not perform; record the finding and stop |

Autonomous zone (no checkpoint): all read-only commands; the Phase 1 capture; branch creation and slice commits on the repair branch with the `umaws-pilot` identity; Phase 6 card work through the normal pipeline; writing inventory/erratum/decision-draft documents; ticking checklist evidence cells only when the proof exists.

---

## 7. The runbook — phases 0–12

**Step format:** Purpose · Verify-first · Steps (PowerShell 5.1) · Evidence · Gate to next phase. A phase whose verify-first gate already passes is recorded as "already satisfied — evidence: …" and the executor continues. `pmk` is on PATH; use `.venv\Scripts\python.exe` explicitly; do not rely on `Activate.ps1` (execution policy) or on the editable install's `src` shadowing (P-01).

---

### Phase 0 — Entry gate (read-only)

**Purpose.** Anchor everything in measured reality; detect concurrent actors; protect nothing yet, change nothing yet.

**Steps.**

1. Read, in order: `AGENTS.md` + `CLAUDE.md`; `pilot/repair-resumption-checklist-v1.md` (items 1–12, 14 done; 13, 15 failed pending this programme; 16 blocked); the source report §1, §7, §9; `pilot/decisions.md` D-62…D-69 (D-69 = ratified FAIL); this document §1–§6. (Full order: Appendix A.)
2. Run the §2.4 re-baseline command block; save raw output to `tmp\entry\<timestamp>\`.
3. **Concurrent-actor detection** (from the DeepSeek source):

```powershell
Get-Process | Where-Object { $_.ProcessName -match "python|opencode|kilo|pi|cline|hermes|node" } |
  Select-Object Id, ProcessName, StartTime
# note the wall clock; wait 60 seconds; re-run and compare:
git log --oneline -3
pmk status
```

4. Confirm: `project_state == PAUSED` (A-8: you will not change it); `active_leases: 0` (else Phase 4 / CP-2 discipline applies); import resolution points where expected; identity is `umaws-pilot` (if it shows the operator's identity, **stop before any commit** and report — N-04).
5. Diff your census against §2.1. Drift is expected — record it, labelled **Confirmed / Derived / Unknown**. Material drift that changes the meaning of an authorization (different lease set, `project_state` change, a push has happened, `main` has moved under a landed landing) is reported to the operator **before Phase 3**.

**Stop if.** `pins check` or `fleet check` not ok → protection must still happen: go to Phase 1, then stop and report (§11). Evidence of another agent actively dispatching (new `CLAIMED` events, a running dispatch loop) → stop and report; this programme assumes single-owner execution.

**Evidence.** `tmp\entry\<timestamp>\*.txt` + an entry note listing every drift item with claim labels.

**Gate to Phase 1.** Census recorded; import path verified; identity safe; no un-resolved stop condition.

---

### Phase 1 — Protective capture of the uncommitted repair (OQ-03, first half)

**Purpose.** Make it impossible for any later step to lose uncommitted work. This is pure insurance; it changes no tracked file. Everything uncommitted is captured **twice** (patch + self-contained archive), **outside the repository**.

**Verify-first.** If a capture for today already exists and covers the current dirty set (hashes recorded), record its path and skip to Phase 2.

**Steps.**

```powershell
$stamp = "2026-11-09"   # use Get-Date at execution time
$arc   = "C:\temp\projects\umaws-repair-archive-$stamp"
New-Item -ItemType Directory -Force -Path $arc | Out-Null
# 1. tracked changes -> binary patch
git diff --binary > "$arc\tracked-changes.patch"
# 2. status + censuses + recent history
git status --porcelain > "$arc\working-tree-status.txt"
git worktree list      > "$arc\git-worktree-list.txt"
git log --oneline -20  > "$arc\head-log.txt"
pmk status             > "$arc\pmk-status.txt"
pmk worktree list      > "$arc\pmk-worktree-list.txt"
# 3. untracked files -> list + self-contained archive
git ls-files --others --exclude-standard > "$arc\untracked-list.txt"
git ls-files --others --exclude-standard -z |
  tar --null -T - -cf "$arc\untracked.tar"
# 4. integrity
Get-FileHash "$arc\tracked-changes.patch", "$arc\untracked.tar" -Algorithm SHA256 |
  Format-List
```

**Verify restorability without touching the live tree:** on a throwaway detached worktree or scratch clone, apply the patch / expand the archive into a scratch directory, and spot-check files byte-match. **A backup you cannot restore is not a backup.** Record the verification output.

**Dirty Kernel worktrees (6 at §2.1):** for each, use the **Kernel's** capture path (`pmk worktree archive` / `archive_tree()` → `verify_archive()`; `[VERIFY]` exact verbs via `pmk worktree --help`). Do **not** use ad-hoc copying. If any capture cannot be verified, mark it and **do not delete the tree** (N-14).

**Write the manifest** `tmp\capture\README.md`: archive path, SHA-256 hashes, file counts, per-worktree capture outcomes.

**On failure.** Retry once; if the patch is empty while `git diff --stat` shows changes, **stop** and report. If a single untracked file refuses to copy, record it and continue — never delete.

**Gate to Phase 2.** Patch + archive + hashes + restorability verification all exist and are recorded. (`.pm/` paths inside the patch are disaster-recovery only; they are **never committed** — N-02/B-15.)

---

### Phase 2 — Verify-first survey: classify the remaining work from measured state

**Purpose.** The repository moved after every source snapshot (§2.2). Measure, classify, record — never assume.

**Steps.**

```powershell
git ls-files --error-unmatch tests/test_transport.py      # OQ-01 base fix landed?
pmk status                                                # OQ-02 leases; project state
git status --porcelain | Measure-Object -Line             # OQ-03 dirty census
python -m pytest -q --collect-only tests/fleet tests/pmk  # OQ-06 collection collision
git worktree list | Measure-Object -Line                  # OQ-05 git census
git log --oneline h1-h4-deletion-safety-v1 -5             # foreign branch state
git log --oneline main..h1-h4-deletion-safety-v1          # is it ahead of main?
```

**Fill this table in your session notes** (it is the input to Phases 3–11):

| Item | Measure | Classify |
|---|---|---|
| OQ-01 base fix | file tracked? | tracked → Phase 5 is verify-only for this item |
| OQ-02 leases | `active_leases` | 0 → Phase 4 verify-only; else CP-2 |
| OQ-03 landing | dirty count + file classification | → Phase 3 slice list (Appendix B rule) |
| OQ-06 collision | combined `--collect-only` exit | 0 → H2 verify-only; else execute H2 |
| OQ-05 census | both counts + set difference | → Phase 7 (deletion still needs CP-3) |
| Gate at HEAD | clean detached run per Phase 5 §5.2, on `main` HEAD **before** landing | expect **red at `4e72901`-class HEAD** (§2.1) — this is the known unlanded-harness-fix state, not a new blocker; record it |
| Foreign work | `h1-h4-deletion-safety-v1` ahead of main? | census + record; **coordinate at CP-3**; if the branch's patch overlaps a Phase 6 H-item, verify-first against it (A-14) |
| T-0189 | state, attempts, hint base | → Phase 11 criteria and CP-4 disposition |

**Gate to Phase 3.** Every row classified. Anything measuring *worse* than §2.1 (new invalid lease, `project_state` changed, new failures beyond the known one) → **stop** and report before proceeding.

---

### Phase 3 — Land the repair on the repair branch (OQ-03, R-03; enumerated bootstrap exception)

**Purpose.** Convert the uncommitted repair into reviewable commits on a branch, so nothing further can destroy it. The code is already written and reviewed (the `assessment-claude-*` patch-review series is the review trail); this phase is about provenance, not invention.

**Precondition.** Phase 1 evidence exists.

**Step 3.1 — Identity guard (B-11/N-04):**

```powershell
git var GIT_AUTHOR_IDENT   # must be: umaws-pilot <umaws-pilot@localhost>
# if not:
git config user.name  "umaws-pilot"
git config user.email "umaws-pilot@localhost"
git var GIT_AUTHOR_IDENT
```

(Repo-local config only; this is not `.pm/policy.toml` and not a pins change.)

**Step 3.2 — Create the branch** (the working tree carries over; no file content changes):

```powershell
git switch -c repair/fleet-launcher-<date>
git branch --show-current
```

**Step 3.3 — Inventory and classify the dirty set.** Four kinds: (a) Kernel-written `.pm/` — leave, never commit; (b) repair code/tests/tools — commit in slices; (c) documents/decisions — commit; (d) scratch (root-level `find_*.py`, `insert_*.py`, `submit_*.py`, `pytest_*.txt`, ad-hoc patches) — **quarantine, don't commit**; if evidence, move under `quarantine\<date>\` with a manifest (the D-68 pattern), else record and leave. **Stop if you cannot classify a path** — investigate; never commit a path you do not understand (N-16).

**Step 3.4 — Commit in reviewable slices** using the Appendix B inventory (adjust to the current dirty set by the classification rule; record deltas). Pattern:

```powershell
git add <slice paths>
git commit -m "fix(fleet): <what> (<P-id/OQ-id/F-id>)"
python -m pytest -q <slice tests>
```

Each slice: one commit, a **slice manifest** in the commit body (files included, tests covering them, which F-/OQ-/P- items it addresses), and its focused tests green before the next slice. If a slice's tests fail, fix within the slice or revert that slice only (`git restore --staged --worktree <paths>`) and record why. **Never amend a committed slice** (N-03); never `git add -A` (N-16).

Note: slice S1 must include `src/fleet/harness.py` — the clean-base gate at HEAD fails precisely because the `AGENT_STARTED`-failure regression test (`4e72901`) landed ahead of its matching harness fix (§2.1). The combined suite after S1 is the proof this resolved.

**Step 3.5 — Verify the landing:**

```powershell
git status --short
git log --oneline main..HEAD
git diff main..HEAD --stat
```

Expected: remaining modified tracked files are only Kernel-written `.pm/` paths (never committed; operator option at CP-1) plus deliberately deferred-and-recorded items; untracked inventory remains for Phase 8.

**Evidence.** Per slice: commit SHA, focused-test output, run-log line; one decision note naming all slice SHAs.

**Gate to Phase 4.** All in-scope repair slices committed on the branch; classification table fully resolved; `active_leases` state recorded.

---

### Phase 4 — Lease hygiene (OQ-02)

**Verify-first.**

```powershell
pmk status   # expect active_leases: 0 (Confirmed at §2.1)
```

If 0 → record evidence and skip to Phase 6's H1 for the recurrence guard.

If any active lease: `pmk task show <id>` for each; an invalid one (repo-root worktree, missing `pid`/`expires_at`, project paused without override) goes to **CP-2**. Default on approval:

```powershell
pmk revoke <task_id> --fence <fence> --reason "lease reconciled: invalid shape; deliverables preserved in <archive path>"   # [VERIFY] exact verb/flags
pmk status
```

Never touch `.pm/` by hand (N-02). Never `--force` anything (N-03). The historical `T-0182` lease record is preserved — it is evidence, not a live lease (A-6).

**Evidence.** `pmk status` before/after → `tmp\rb-4-lease.txt`; CP-2 decision if taken.

**Gate to Phase 5.** `active_leases: 0` (or CP-2 resolution recorded). If `pmk` cannot reconcile cleanly (fence errors, unknown verb) → **stop and report**; do not improvise against the ledger.

---

### Phase 5 — Base verification and clean-base gate on the branch (OQ-01, R-01, R-09) → DoD-1

**Purpose.** Prove the gate passes on the *committed* tree. This is the point of the whole exercise; it is exactly what failed for `T-0189` (P-26) and what is measurably red at HEAD right now (§2.1).

**Step 5.1 — Base-fix verification (verify-first).** `tests/test_transport.py` is tracked (Confirmed). Read the coverage case `8.0` citation in `tests/test_rules_baseline.py`; confirm the committed tree satisfies it. The clean-base gate run in 5.2 is the real proof either way.

**Step 5.2 — Clean-base gate at the branch head:**

```powershell
$sha = git rev-parse HEAD
$wt  = "C:\temp\projects\umaws-gate-<stamp>"
git worktree add --detach $wt $sha
$env:PYTHONPATH = "$wt\src;$wt\tests"
Push-Location $wt
python -c "import cna, pmk; print(cna.__file__); print(pmk.__file__)"   # must resolve INSIDE $wt
python -m pytest -q 2>&1 | Tee-Object -FilePath "C:\temp\projects\testproject1\tmp\rb-5-clean-base-gate.log"
$gateExit = $LASTEXITCODE
Pop-Location
$gateExit
```

**Expected.** Import paths inside `$wt` (if they print the main tree's `src`, the P-01 editable-install shadowing is back — **stop**; that is the original root cause). Gate exit 0.

**On failure.** Keep the worktree; extract failing test ids from the log tail; classify: base defect (fix in a new branch commit, rerun 5.2), environment defect (check `PYTHONPATH`), or your own slice regression (`git diff` the slice). Record the output tail (B-05). **Never** "fix" by editing tests to pass, and never describe a dirty-tree green as proof (N-05).

**Step 5.3 — Cleanup** only after the gate passed and no evidence is pending: `git worktree remove $wt` (it is clean and treeless by construction — record that it held no work).

**Step 5.4 — Make it a standing check (R-09).** Add `tools/check_clean_base.ps1` implementing exactly 5.2 (detached worktree at HEAD, pinned `PYTHONPATH`, import check, full gate, captured log, remove worktree, exit with the gate's code); reference it from the operator's pre-landing routine and the platform rules doc. Verify by running it once (exit 0). Commit on the branch. *(If the foreign `h1-h4-deletion-safety-v1` branch or the `e7d2725` evidence patch already contains an equivalent, verify-first and reuse rather than duplicate — A-14.)*

**Evidence.** Full gate output + base SHA + import-resolution proof → feeds DoD-1 and checklist item 13.

**Gate to Phase 6.** Clean-base gate exit 0 at a recorded branch SHA.

---

### Phase 6 — Hardening set via pmk cards (H1…H7)

**Purpose.** Close the engineering gaps in scope (A-5, A-9). These are **new work** → each item is its own card through the normal pipeline: propose → admit → claim → lease → `work/<task>-<fence>` → commit with `umaws-pilot` → submit → harness/gate decide → merge. The card pipeline is the work (A-5). **Verify-first:** if the item's test already exists and passes (possibly via the foreign branch — A-14), record it and skip.

| Item | Content | Done when |
|---|---|---|
| **H1 — R-02 lease admission check (OQ-02 recurrence)** | Kernel-side admission check rejecting: (a) a lease whose `worktree` resolves to the repository root; (b) a grant that would carry no `pid`/`expires_at` while the project is not `RUNNING`. Refusal with a recorded reason, never silent correction (N-15). Test: `tests/pmk/test_lease_admission.py` covering both rejections + one legitimate grant. | Check landed `DONE` via a card; DoD-5 provable. Historical records are never retrofitted. |
| **H2 — R-05/OQ-06 conftest collision** | `tests/fleet` fixtures imported via bare `from conftest import …` collide with `tests/pmk/conftest.py` on combined collection. Preferred fix: move shared helpers into a real module (e.g. `tests/fleet/_fleet_fixtures.py`); alternative: package-qualified imports. Renaming only `FIXTURE_ROOT` does **not** fix it — the collision is the module, not the symbol. | `python -m pytest -q --collect-only tests/fleet tests/pmk` exits 0 (DoD-2); all existing fleet tests still pass. |
| **H3 — R-06/OQ-09 reconcile wiring** | Call `Dispatcher.reconcile()` (exists, `src/fleet/dispatcher.py:520`, tested but unwired) from the Console/Conductor startup path; test the **startup path**, not merely the method; reconcile must respect the "never start a second worker where a live adopted process exists" rule. | Startup-path test passes; slice `DONE`. |
| **H4 — R-07/OQ-11 model attribution** | Adapters record the served model; where genuinely unknown, write an explicit non-empty `["unavailable"]`-style value with a non-`none` source — never `served_models: []` (measured empty at seq 3477). Test: no emitted `MODEL_SERVED` payload/bundle field may carry an empty list. | Test passes; slice `DONE`. |
| **H5 — R-08 env lint coverage** | Extend `tools/check_subprocess_env.py` so any `subprocess` call in `src/fleet` not deriving its environment from `worktree_env()` fails the lint; keep the reviewed-exception list explicit; extend `tests/test_subprocess_env_lint.py`. | Tool exits 0 on the tree (DoD-3); slice `DONE`. |
| **H6 — R-10 gate output in bundles** | `_gate_diagnostics()` (`src/fleet/merge.py`) already captures output; ensure the bundle (`EB-<task>-<fence>/bundle.json`) stores `gate_output` on **failure and success**. Test: simulate a failing gate, assert non-empty `gate_output`. | **DONE (direct implementation)** — `gate_output` is written to the bundle for success, gate failure and launch failure; `test_gate_output_is_persisted_in_the_bundle` covers success and failure. Validated by fresh canary T-0191: `EB-T-0191-158` contains non-empty `gate_output`. |
| **H7 — R-04 prune awareness (tooling only)** | Make `pmk worktree prune` aware of `%TEMP%\pmk-merge-*` entries and callable from the Conductor, **dry-run by default**. Test: discovery logic + dry-run output. **Actual deletion happens only in Phase 7 under CP-3.** | Tests pass; slice `DONE`. |

**Rules.** Keep every existing fleet test passing throughout. If an item reveals deeper structural problems, scope them out record-only (§12) rather than expanding here. Suggested order: H1, H2, H6 first (they unblock DoD-2/5/6); H3, H4, H5, H7 after — order within the set is negotiable once, recorded if changed.

**Gate to Phase 7.** Each H-item `DONE` via its card (or explicitly recorded deferral with reason); focused tests green; full gate green on the branch.

---

### Phase 7 — Worktree census reconciliation (OQ-05, R-04) → DoD-4

**Step 7.1 — Measure the union (B-17):**

```powershell
pmk worktree list > tmp\rb-7-pmk-census.txt
git worktree list > tmp\rb-7-git-census.txt
```

Record both counts and the full set difference (§2.1 measured 29 vs 41: `work/` trees, `%TEMP%/pmk-merge-*` ×10, `.claude` tree, main).

**Step 7.2 — Safety first — capture every dirty tree (N-14, REC-02 before REC-01):**

```powershell
pmk worktree archive --all-dirty --dry-run   # [VERIFY] exact flags
pmk worktree archive --all-dirty
```

Every dirty tree captured with verification; every refusal honoured, never forced.

**Step 7.3 — Take deletion to CP-3.** Present: the union census, the archive evidence, and the census document. If `pilot/repair-worktree-census-v1.md` does not exist, **write it first** — a dated inventory of every extra tree (path, origin, size, dirty/clean, recommendation), including the `%TEMP%/pmk-merge-*` trees (verified to hold no unmerged commits: `git log <tree> --not main`) and the foreign `H1-H4-*` / `gate-*` / `.claude` trees (their disposition is the operator's call; the checklist's standing instruction is *keep until an evidence-based decision*).

**Step 7.4 — Only on CP-3 approval:**

```powershell
pmk worktree prune --archive --dry-run   # [VERIFY]
pmk worktree prune --archive --yes
git worktree prune                        # stale %TEMP% entries after removal
```

Both censuses shrink consistently; recount and record; refusal paths respected.

**Evidence.** Census files + archive outputs + prune records → `tmp\rb-7-*.txt`; feeds DoD-4.

**Gate to Phase 8.** Census difference fully explained; no un-captured deletion; CP-3 disposition recorded.

---

### Phase 8 — Governance records, errata, and inventory (record-only; A-13)

**8.1 Errata for stale claims (R-12).** Append an `## Erratum (<date>)` section to the affected incident report(s) — e.g. the `write_handoff` call-site count (three sites: `src/fleet/harness.py`, `src/fleet/dispatcher.py`, `src/pmk/cli.py`) and the formal-report placement convention (`docs/reports/`). Append, never delete or rewrite history.

**8.2 Record the unrecoverable governance facts as `Unknown` (OQ-07, OQ-08).** Draft decision records (next free ids; **D-70** was next at synthesis — verify) in `pilot/decisions.md` with the full B-12 payload, for: the operator-identity commits `e08fa8d`/`ebe46ce` (actor Unknown; D-67 already records this — reference and confirm it stands), and the `Q-077`/`.pm/policy.toml` edit window. No history rewrite is proposed (CP-5). Ratification at CP-4.

**8.3 Sentinel baseline (R-13).**

```powershell
pmk sentinel   # [VERIFY] exact subcommand
```

Recorded baseline: 5 × I6 + 1 × I13 (checklist item 14: "done (red, recorded)"). Re-measure; if the Phase 6 H-items changed the underlying conditions, record the new state. Draft the disposition for CP-4 — default recommendation: **accepted-red with a named owner and a review date**, never silently described as green.

**8.4 Inventory of what stays uncommitted (OQ-13).** Write `docs/reports/uncommitted-inventory-<date>.md`: every remaining dirty/untracked path with disposition — `retain-untracked` / `operator-to-decide` / `cited-evidence-retain`. Include: root-level reports/assessments (working papers), `tmp\` evidence logs (several are cited by decisions — retain), helper scripts, the foreign-branch material, and this document (disposition at CP-1).

**8.5 Checklist update (evidence cells only).** Update `pilot/repair-resumption-checklist-v1.md` items 13 and 15 **only when their proofs exist** (Phase 5/9 gate log; Phase 11 canary bundle). Tick nothing early — "an unticked box is a blocker, not an oversight."

**Evidence.** Erratum section, decision drafts, sentinel output, inventory doc — referenced in the completion report.

**Gate to Phase 9.** All record-only items drafted and filed; nothing ratified.

---

### Phase 9 — Whole-system verification (DoD-2, DoD-3)

1. Combined collection: `python -m pytest -q --collect-only tests/fleet tests/pmk` → exit 0 (skip if H2 verified it; record the skip).
2. Env invariant: `python tools\check_subprocess_env.py` → exit 0.
3. Full gate, clean base, at the current branch head: repeat Phase 5.2 → exit 0, log `tmp\rb-9-final-gate.log`.
4. Integrity: `pmk pins check` → `ok: true`; `pmk fleet check` → `ok: true`; `pmk status` → chain verifies.

**On any failure.** Return to the owning phase; never proceed with a red check.

---

### Phase 10 — Land on `main` (**CP-1**)

**Present to the operator.** Branch diffstat vs `main`, Phase 9 evidence, the exact commands, and the dispositions for: this document, `.pm/` runtime-state commits, and the deferred/recorded items.

**Only on approval:**

```powershell
git switch main
git merge --ff-only repair/fleet-launcher-<date>
git rev-parse HEAD
```

**Expected.** Fast-forward (if `main` has moved, **stop** — no rebase, no force, report; prefer re-baseline + reconcile). **No push** (A-7). Record the new `main` SHA — it is the canary base.

---

### Phase 11 — Fresh supervised canary to `DONE` (OQ-04, R-14) → DoD-6

**Purpose.** The only thing that proves the system works end-to-end. Everything else was preparation.

**Step 11.1 — Preflight (all must be true; any failure → fix, do not proceed — this is exactly the deviation D-69 recorded):**

| Check | Command | Required |
|---|---|---|
| Project dispatchable for one canary | `pmk status` | `PAUSED` is the standing state; the canary is the single authorized exception (A-9); if in doubt, CP-4/§11 |
| Zero active leases (or only the canary's) | `pmk status` | consistent |
| Fleet + pins valid | `pmk fleet check`, `pmk pins check` | `ok: true` |
| Full gate green | Phase 9.3 | exit 0 |
| Clean-base gate green at the canary base | Phase 5.2 at the Phase 10 SHA | exit 0 |
| Non-disabled profile exists | `pmk fleet check` | at least one eligible profile (A-9) |

**Step 11.2 — Create a fresh canary card through `pmk`.** Reuse the standing design (`pilot/cards/canary-replacement-v1.md`, the `D-69` operator packet, and the measured `T-0189` card structure) — do not improvise a canary design. Requirements: card type `task`; goal `G-001`; exactly one write-scope file (e.g. `docs/reports/dispatch-repair-verification-v2.md`); an acceptance oracle verifying the file records the run's own evidence (`base=`, `corpus=`, `rule_files=`, `gate=` fields — the `T-0189` oracle pattern); **`hint_base_commit` = the Phase 10 `main` SHA**; a hint that asserts nothing else about the tree; `gate_cmd` = `python -m pytest -q`.

**`T-0189` disposition (CP-4 input, not a blocker):** it is `READY` with attempts exhausted (1/1) and a stale hint base (`bcf145c`); the fresh card supersedes it. Recommend `VOID` with a recorded reason naming the successor card — or operator-designated re-use. Either way, no card is left in limbo.

**Step 11.3 — Precheck, admit, dispatch through the real path only:**

```powershell
pmk task precheck <canary-id> --base <phase-10-sha>   # [VERIFY] exact flags
pmk task admit <canary-id>
pmk dispatch run --seconds 900                        # [VERIFY] exact form; supervised
pmk task show <canary-id>
```

The **pipeline** performs every transition. The executor supervises; it does not hand-drive the worker. Observe; do not intervene except to stop a runaway.

**Step 11.4 — Judge only from recorded evidence.** Expected `PASS` ledger path: `CLAIMED → AGENT_STARTED → AGENT_EXITED(OK) → SUBMITTED → ORACLE_RESULT(stage=gate, exit 0) → INTEGRATED → DONE`, bundle `EB-<id>-<fence>` with non-empty `gate_output`. If the worker exits 0 but the gate judges the wrong tree, that is P-01 recurring — **stop** and re-check `worktree_env()` wiring (Phase 6 H5 / Phase 3 slice S1).

**On `FAIL`:** capture the failing test id and full output (N-06); record class; **do not** iterate into a third-and-fourth canary — at most one retry, and only with a diagnosed, fixed cause; otherwise route to §11 (escalation) with dispatch paused.

**Evidence.** Bundle id, gate stdout/stderr at the recorded base, the transition trail via `pmk task show`, run log.

**Gate to Phase 12.** The canary has a terminal state and a bundle. No permissive interpretation: `DONE` is `DONE`, `REWORK` is `REWORK`.

---

### Phase 12 — Draft the decision, update the checklist, hand back (**CP-4**)

1. **Draft the decision record** — next free id (**D-70** was next at synthesis; verify) in `pilot/decisions.md`'s field order (date · who · decision · alternatives · what it leaves untested), full B-12 payload:
   - **If `PASS`:** fresh supervised canary on the repaired base reached `DONE` via the real path; cite task id, fence, bundle, base SHA, gate output; record that `A10`, `project_state`, and push remain reserved to the operator.
   - **If `FAIL`:** the reproduced failure with captured output, its class, and the minimal path forward; dispatch stays paused.
   - Proposer: the executor; ratifier: the operator at CP-4. **Do not ratify** (N-13).
2. **Checklist:** item 13 ← Phase 5/9 gate log; item 15 ← canary evidence; item 16 remains **blocked** with note "A10 is the operator's decision on a recorded PASS."
3. **Completion report** (§10) and **final state capture:**

```powershell
pmk status; git status --short; git log --oneline -10
pmk worktree list; git worktree list
```

→ `tmp\rb-12-final.txt`.

4. **Hand back** with: the DoD matrix (§13) filled from measurements, the CP-4 decision awaiting ratification, and an explicit statement of what is **not** done: dispatch resume, push, any un-ratified drafts.

---

## 8. Evidence requirements across phases

Wherever this document says "record" or "full output":

- **Output, not exit codes** (N-06/B-05): reuse `_gate_diagnostics()` and F-03 conventions wherever the pipeline offers them; ad-hoc evidence captures stdout and stderr separately, with timestamps.
- **Tree and base with every run:** every output file records the commit SHA and worktree path it was produced in. A result without `(tree, base)` is uninterpretable.
- **Claim labels:** every factual claim in the completion report is **Confirmed / Derived / Unknown**.
- **Locations:** scratch evidence under `tmp\<phase-id>\` (protectively hashed); anything that must outlive the session (draft decisions, completion report, errata, inventories) goes to its proper register location (`pilot/decisions.md`, `docs/reports/`) via the normal path. A **new** evidence file under `.pm\evidence\` is acceptable capture; hand-editing Kernel-owned `.pm` files never is.

**Per irreversible action: one decision (before), one evidence artefact (after):**

| Action | Decision (before) | Evidence (after) |
|---|---|---|
| Protective capture (Ph. 1) | note | patch + archive + hashes + restorability record |
| Slice commit (Ph. 3) | note naming the slice | commit SHA + focused-test output |
| Revoke a lease (Ph. 4, CP-2) | CP-2 record + reason | before/after `pmk task show` |
| Clean-base gate (Ph. 5/9) | — | full output + base SHA + import proof |
| H-item card (Ph. 6) | the card itself | harness output, bundle, gate output |
| Prune/delete a tree (Ph. 7, CP-3) | CP-3 record | census + archive/verify proof per tree |
| Canary (Ph. 11) | — | bundle + ledger tail + gate output |
| Land on `main` (Ph. 10, CP-1) | CP-1 record | new `main` SHA, ff-only proof |
| Draft decision (Ph. 12, CP-4) | the draft itself | bundle reference + `pmk status` at stop |

The completeness check (DoD-9): at the end, every row has both — or an explicit `Unknown` / not-applicable note.

---

## 9. Rollback, recovery, and the never-shortcut list

| Risk | Trigger | Response |
|---|---|---|
| A slice commit breaks the suite | focused/clean-base test fails after commit | `git revert <sha>` (never amend); record; fix forward. |
| A slice's tests fail before commit | focused tests red | fix within the slice, or revert that slice only (`git restore --staged --worktree <paths>`); record. |
| Push rejected | n/a — push is prohibited (A-7); if ever authorized later: **stop, investigate, never force**. | — |
| An archive fails verification | `verify_archive()` false | **Do not delete** the tree; investigate; record. |
| Clean-base gate unfixable | Phase 5.2 red after honest attempts | Record `FAIL`; keep dispatch paused; escalate (§11). This is a legitimate outcome, not a process failure. |
| The canary passes but a real card regresses | n/a in this programme — real dispatch is out of scope (A-8); if observed anyway: record an incident; do not intervene. | — |
| Concurrent actor commits over your work | unexpected new commits/leases | Re-baseline; reconcile; **never** `reset`/`checkout` the tree; prefer merge over overwrite; report material drift (§2.3). |
| Session interrupted | executor dies mid-phase | Successor restarts at Phase 0; re-verifies every prior phase's closing evidence (B-20). |

**Never, as a shortcut:** hand-edit `.pm/`; force-push; `reset --hard`; `clean -fdx`; `--no-verify`; delete an uncaptured worktree; commit under the operator's identity; ratify your own decision.

---

## 10. Completion report requirement

One formal report, in `docs/reports/` (B-16), named per register convention (suggested: `docs/reports/fleet-launcher-repair-completion-v2.md`), containing:

1. State at entry vs state at completion (task distribution, leases, both worktree censuses, HEAD, dirty counts) — all claim-labelled.
2. Per phase: what was executed, evidence artefacts, pass/fail.
3. The draft decision and its outcome.
4. The slice + card inventory: card ids, fences, commit SHAs.
5. Every deviation from this document (order changes, deferrals, aborts), each with a reason (B-18).
6. Record-only observations from §12, labelled.
7. A short self-audit if the operating contract was deviated from in any way — the standard set by the source report §9 and upheld by every report since.
8. Provenance: signed with the executor's own `author_llm` name and version; never fabricated or inherited.

If the programme aborted, the report replaces the pass narrative with the abort condition, preserved state, and the exact stopping point.

---

## 11. Aborting, blocking, and escalation

Stop-and-report ≠ fail. These conditions terminate execution with a written report rather than improvisation:

| Condition | Action |
|---|---|
| `pins check` / `fleet check` fails at entry after Phase 1 protected the tree | Stop, report; do not touch leases or cards. |
| Any `pmk` command errors or produces an unexpected ledger state (fence error, unknown id, chain violation) | Stop. No manual recovery. |
| The operator's identity on any intended commit (N-04) | Stop before the commit; report. |
| Clean-base gate fails with a cause outside this document's authorizations | Stop; report with captured output. |
| No viable non-disabled profile for the canary | Stop; report the profile census. |
| Material state drift invalidates an authorization in §3 | Stop; report the drift and the specific authorization affected. |
| Anything tempts a force, a `.pm/` hand-edit, a push, a state flip, or self-ratification | That temptation is itself the abort signal. |

In every case: the Phase 1 capture exists first; keep it intact; describe exactly where you stopped and what is preserved.

---

## 12. Out of scope — record-only backlog

Not to be fixed or implemented by the executor. Observe and document in the completion report:

- **P2 governance items** — R-11 (decision-record template validation), R-12 beyond the §Phase 8 errata, R-13 beyond the CP-4 disposition draft, R-14 beyond what Phase 11 exercises.
- **P-23 / P-24 / OQ-07 / OQ-08** — historical identity anomaly and `Q-077`; record only; no history rewrite (CP-5).
- **OQ-10 documentation drift** beyond the Phase 8.1 errata.
- **The `tmp/` wholesale-cleanup decision** — record findings; never delete evidence you created or inherited (N-12 protects the Phase 1 capture; ordinary `tmp/` hygiene remains reserved).
- **`docs/release-status.md` / `tests/test_release_status.py`** — landed via `T-0182` (DONE); further product work with them is out of scope.
- **Model-quality evaluation, provider billing, and the product goals of `docs/PDD.md`** except where an oracle serves as evidence.
- **Push to origin, dispatch resumption, project unpausing** — operator decisions, explicitly outside this programme (A-7, A-8).

---

## 13. Definition-of-done verification matrix

Fill from measurements, never from memory. Each DoD is machine-checkable.

| DoD | Criterion | Command / proof | Measured | Evidence file |
|---|---|---|---|---|
| **DoD-1** | Gate green in a detached clean worktree at the recorded post-landing base, imports resolving inside it | Phase 5.2/9.3 at the Phase 10 SHA → exit 0 | **PASS at `b2fe947`** (measured 2026-11-11, post-landing — this base *includes* H1 and both gate-fragility fixes): `clean-base gate exit=0 sha=b2fe9478108c9534af0fe96a774d1c8f9ce22053`, imports resolving inside the gate worktree, **1220 tests marked — 1219 pass / 1 skip / 0 fail**. Caveat: the gate log carries no count line (`addopts = -q` in `pytest.ini` **and** `pyproject.toml`, plus the script's own `-q`, runs pytest at `-qq`), so the count was recovered from the progress marks — see the report's §A.11. The earlier PASS at `5267cdb` (pre-H1) also stands. A further PASS at **`a1d301c`** (the §A.14 CP-3 fix): `clean-base gate exit=0 sha=a1d301c8a5d9a3a55d0a5e268e5169ee9633bab6`, imports resolving inside the gate worktree (count line again absent — fragility 4), log `tmp/clean-base-20261111-235639.log` | `tmp/clean-base-20261111-b2fe947.log`, `tmp/clean-base-20261111-235639.log` (and `tmp/clean-base-20261111-094825.log`, `tmp/clean-base-verify-20261111b.log`) — the planned `tmp\rb-9-final-gate.log` was never produced |
| **DoD-2** | `tests/fleet` + `tests/pmk` collect in one command | `python -m pytest -q --collect-only tests/fleet tests/pmk` → exit 0 | **PASS** — exit 0 after the H2 fixture split | `tmp/combined-collection-only.log` |
| **DoD-3** | Env invariant holds for all `src/fleet` subprocess sites | `python tools\check_subprocess_env.py` → exit 0 | **PASS (2026-11-11)** — `python tools\check_subprocess_env.py` → `ok: no unguarded subprocess spawns (7 allowlisted); fleet cwd checks pass`, exit 0 | tool output (report §A.15) |
| **DoD-4** | Censuses reconcile or the difference is fully explained; no un-captured deletion | `pmk worktree list` vs `git worktree list` + archive records | **PASS (2026-11-11)** — reconciled (report §A.15): `git worktree list` **28** = 1 main + **8** `work/` (identical names to `pmk`'s 8) + **6** `tmp/` + **1** `.claude/worktrees/*` + **12** `%TEMP%` (`pmk-merge-*` ×10, `pmk-precheck-dry-*` ×2 — the H7 subject). CP-3 archived every removed tree before deletion (13 removed / 13 archived; `stranded/` holds 97) | report §A.15; `stranded\` archive |
| **DoD-5** | Lease admission check rejects repo-root / pid-less / expiry-less leases; `active_leases: 0` | `tests\pmk\test_lease_admission.py` passes; `pmk status` | **PASS (2026-11-11)** — both halves. H1 landed: `pytest -q tests/pmk/test_lease_admission.py tests/pmk/test_tasks.py` = **35 passed**. And `active_leases: 0`: the two historical invalid leases were revoked by the operator (`REVOKED` seq 3638 `T-0210` fence 162, seq 3639 `T-0211` fence 163; `REVOKED` also pops the lease), so `pmk status` reports 0. H1 refuses that grant shape prospectively and deliberately did not rewrite the historical records — human revocation closed them | `tests/pmk/test_lease_admission.py` output; `pmk status`; report §A.13 (`tmp\rb-4-lease.txt` was never produced, as with DoD-1's planned log) |
| **DoD-6** | Fresh supervised canary reaches `DONE` through the real path; bundle carries non-empty `gate_output` | `pmk task show <canary>` transition trail + `bundle.json` | **PASS** — fresh T-0196 `DONE` at base `9bb0139`, merge `951d1ee`; bundle `EB-T-0196-159` carries non-empty `gate_output` (`pytest -q`, exit 0); events seq 3554–3558. T-0191 remains the original proof (`EB-T-0191-158`) | `.pm/evidence/EB-T-0196-159/bundle.json`; `tests/fleet/test_merge_queue.py` |
| **DoD-7** | Decision drafted with the full payload at the next free id; checklist items 13/15 evidence-linked | `pilot\decisions.md` + checklist | _pending_ | doc sections |
| **DoD-8** | Every in-scope OQ/R item closed or explicitly deferred with reason | §14 matrix filled from measurements | _pending_ | §14 |
| **DoD-9** | Every irreversible action has decision-before + evidence-after | §8 table fully ticked or not-applicable | _pending_ | run log |

**A mediocre outcome is "the suite is green on my dirty tree and I think the canary will pass." A great outcome is: the gate is green in a detached clean worktree, the canary ran through the real path and reached `DONE`, the bundle shows why, and a draft decision records it — reproducible by a fresh agent from the ledger alone.**

**Explicitly not part of done:** `pmk project resume`, `pmk dispatch run` beyond the single canary, and any push — all operator decisions (A-7, A-8).

---

## 14. Traceability matrix (OQ / R / S → phase)

| Item | Source | Location in this document | Status at synthesis |
|---|---|---|---|
| OQ-01 / R-01 | Dangling base file | Phase 5 (5.1 verify-first; 5.2 gate; 5.4 standing check) | base fix landed (`9b3b70d`/`de107f8`, Confirmed) → verify |
| OQ-02 / R-02 | Phantom lease / admission check | Phase 4 (CP-2) + Phase 6 H1 | `active_leases: 0` (Confirmed) → verify + guard |
| OQ-03 / R-03 | Uncommitted repair | Phase 1 (capture) + Phase 3 (slices) + Phase 10 (CP-1) | open — 31 files (+2298/−451, Confirmed) |
| OQ-04 / R-14 | No passing canary; A10 blocked | Phase 11 + Phase 12 (CP-4) | closed — fresh canary T-0191 `DONE` with non-empty `gate_output`; merge `c7fcdf3` |
| OQ-05 / R-04 | Census disagreement; stale merge trees | Phase 7 (CP-3) + Phase 6 H7 | open — 29 vs 41 (Confirmed) |
| OQ-06 / R-05 | conftest collision | Phase 6 H2 → DoD-2 | closed — H2 fixture split landed; combined collection exit 0 |
| OQ-07 | Identity commits Unknown | Phase 8.2 (record Unknown; rewrite banned) | record-only (A-13) |
| OQ-08 / R-11 | `Q-077` / policy window | Phase 8.2 + B-12 payload standard | record-only (A-13) |
| OQ-09 / R-06 | `reconcile()` not wired | Phase 6 H3 | open |
| OQ-10 / R-12 | Documentation drift | Phase 8.1 (errata) | open |
| OQ-11 / R-07 | Model attribution empty | Phase 6 H4 | open — `served_models: []` measured (seq 3477) |
| OQ-12 / R-13 | Sentinel red baseline | Phase 8.3 (CP-4 disposition) | red recorded (checklist item 14) |
| OQ-13 | Author's out-of-band work | Phase 8.4 (inventory) + §12 | inventory-only |
| P-01…P-33 | Problem register | Covered via the rows above; env/hints/shell/evidence causes guarded by B-06/B-08/B-10/B-05 | — |
| F-01…F-19 | Fix register | Landed items verified in Phase 3; new items are Phase 6 cards | verify at Phase 2/3 |
| S-01…S-18 | Safeguards | §5 B-01…B-20 (all embedded) | binding |
| New: `4e72901` base regression | Harness fix uncommitted | Phase 3 slice S1 + Phase 5 | open (Confirmed — seq 3494) |

---

## 15. Assumptions and flagged guesses (author's disclosure)

Where this synthesis had to choose without an explicit operator ruling, the guess is recorded here rather than hidden.

1. **"Does not ask the operator for anything"** was interpreted as *decision-complete between checkpoints* — the five CPs (which you also selected) remain the only asks. If you meant zero checkpoints, edit §6 before execution.
2. **Status wording.** You said "execution-ready now" and that you will sign `assessor_llm` yourself; the frontmatter therefore reads execution-ready with *assessor signature pending*. If signing and execution-ready must coincide, flip the status at signature.
3. **`T-0189` disposition** — you did not rule. The operator's `TASK_READY` (seq 3495) suggests intent to reuse it, but attempts are exhausted (1/1) and its hint base is stale, so the synthesis prefers a **fresh card** and defers `T-0189`'s fate to CP-4. DeepSeek's "dispose explicitly" requirement is honored via that CP-4 decision either way.
4. **Bootstrap-exception framing** — that Phases 1/3/10 are an *enumerated* exception to the two-modes rule (rather than a violation of it) is this author's synthesis of your branch+ff ruling with the project constitution. The framing, the limits, and the no-silent-widening rule are mine.
5. **Sentinel disposition default** (accepted-red with owner + review date) is MiMo's recommendation, adopted as the CP-4 default; not your explicit ruling.
6. **This document's own disposition** (commit with slice S4 vs stay untracked) defaults to commit-with-S4 at CP-1; not explicitly ruled.
7. **Foreign-work overlap (A-14)** — the `h1-h4-deletion-safety-v1` branch appeared after all three sources were written. Whether its patch already implements any Phase 6 H-item is **Unknown** at synthesis; the verify-first rule handles either answer.
8. **Canary dispatch mechanics** (`pmk dispatch run --seconds 900`, `precheck` flags) are tagged `[VERIFY]` — delegated to the recorded canary runbook rather than re-derived.
9. **Every number in §2 ages immediately** — it is a claim with a verify-first gate, per the discipline all three sources agree on.

---

## Appendix A — Required reading order for the executor

1. This document §1–§6 (and §15).
2. `AGENTS.md`, `CLAUDE.md` (the operating contract).
3. `report-freebuff-UMAWS-Fleet-Launcher-repair-v1.md` §1 and §9 (what happened; how the last agent behaved).
4. `pilot/repair-resumption-checklist-v1.md` (done / failed / blocked).
5. `pilot/decisions.md` D-62…D-69 (especially D-69, the ratified FAIL).
6. `docs/PDD.md` (the `gate_cmd` and goals G-001…).
7. Source, last: `src/fleet/runenv.py`, `merge.py`, `harness.py`, `conductor.py`, `src/pmk/worktrees.py` — reading source before the record invites local fixes to systemic problems.

## Appendix B — Slice inventory for Phase 3

Baseline taken from the 31-file dirty set measured at synthesis (§2.1); adjust by the Phase 3.3 classification rule and record deltas. Never `git add -A`.

| Slice | Files (baseline) | Addresses | Tests covering |
|---|---|---|---|
| **S1 — Fleet core** | `src/fleet/conductor.py`, `dispatcher.py`, `harness.py`, `legacy.py`, `merge.py`, `project.py`, `spawn.py` | F-03…F-08, the `4e72901` harness fix | `tests/fleet/test_fleet.py`, `test_conductor_leases.py`, `test_regressions.py`, `test_adapter_paths.py` |
| **S2 — Kernel** | `src/pmk/events.py`, `src/pmk/worktrees.py` | F-09, F-10, F-14 | `tests/pmk/test_worktree_lifecycle.py` |
| **S3 — Tooling** | `tools/check_subprocess_env.py` | F-02 | `tests/test_subprocess_env_lint.py` |
| **S4 — Pilot records + config** | `pilot/**` modifications, `HANDOFF.md`, `agents.toml`, `docs/reports/` report edits; optionally this document (CP-1 default) | F-08, F-16…F-19 | none (documentary) — state so in the commit message |
| **Deferred to cards** | new H-item work | Phase 6 | via cards |

Untracked material (source reports, `assessment-claude-*`, `tmp\` evidence, helper scripts) is **preserved in the Phase 1 capture, not committed**; the completion report lists it with capture-manifest hashes.

## Appendix C — Prohibited / notify-only action summary

| Action | Status |
|---|---|
| Push to origin | **Prohibited** (A-7) |
| Change `project_state` / authorize `A10` / dispatch beyond the single canary | **Prohibited** (A-8, N-10) |
| `.pm/` hand edits | **Prohibited** (N-02) |
| Commit under the operator's identity | **Prohibited** (N-04) |
| Force / reset / rebase / amend / `--no-verify` / guard bypass | **Prohibited** (N-03, N-15) |
| Delete a worktree before capture-and-verify | **Prohibited** (N-14) |
| `git add -A` / `git add .` | **Prohibited** (N-16) |
| Ratify a decision | **Prohibited** (N-13) |
| Spawn on a disabled profile | **Prohibited** (N-09) |
| Main-tree direct edits beyond the enumerated bootstrap | **Prohibited** (N-01) |
| Touch the foreign `h1-h4-deletion-safety-v1` / `H1-H4-*` / `gate-*` trees | **Protect + CP-3 only** (A-14) |
| Material drift invalidating an authorization; certificate/guard surprises | **Notify-only**: record and stop |

## Appendix D — Provenance and change log

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0.0 | 2026-11-09 | GLM-5.3-Flash Free (opencode) | First issue: synthesis of three source proposals under operator adjudication (interview 2026-11-09); fresh read-only baseline at `e7d2725`; hybrid structure; authorizations A-1…A-14; hard constraints N-01…N-16; checkpoints CP-1…CP-5; phases 0–12; DoD-1…DoD-9; source-disposition appendix E |

**Provenance statement.** Authored by GLM-5.3-Flash Free (`opencode/glm-5.3-flash-free`) v1.0.0 on 2026-11-09 from: (a) full reads of the three source proposals; (b) fresh read-only measurements of the live repository (`git rev-parse/log/status/diff`, `git worktree list`, `git var GIT_AUTHOR_IDENT`, `pmk status`, `pmk worktree list`, `pmk fleet check`, `pmk pins check`, `pmk task show T-0189`); (c) targeted checks of `pilot/decisions.md` (next free id D-70), `pilot/repair-resumption-checklist-v1.md`, and `docs/PDD.md` (`gate_cmd`, line 51). No `.pm/` file was read beyond read-only `pmk` output; no task was claimed or transitioned; no file was modified by this author other than this document. Where the record could not establish a fact, it is labelled so (§15) rather than inferred. The operator's adjudications were granted directly, by explicit interview answers on the same date; the resolutions are recorded in Appendix E.

## Appendix E — Source disposition: what was taken from each proposal, and how conflicts were resolved

**Operator rulings (interview, 2026-11-09)** that resolved the three-way conflicts: superseding executor brief; landing = capture → repair branch → reviewable slices → CP-gated `--ff-only`; scope = full engineering, governance record-only; push prohibited; dispatch resumption out of scope; MiMo's five checkpoints; execution-ready status; fresh baseline measured during synthesis.

| Conflict | DeepSeek | GLM-5.3 | MiMo | Resolution and source of the winning mechanism |
|---|---|---|---|---|
| Landing mechanism | direct slices to `main` | via pmk cards only | branch + CP-gated `--ff-only` | **MiMo's mechanism** (operator ruling); GLM's mechanical objection (dirty tree can't enter card worktrees) recorded in §1.3; card ceremony reserved for new work (GLM's discipline, narrowed) |
| Push | yes, ff, recorded | never | never (operator's act) | **Prohibited** (2-of-3 + operator) |
| Dispatch resumption | in scope on PASS | out, operator-reserved | out, operator-only | **Out of scope** (2-of-3 + operator) |
| Engineering scope | full set | narrow: R-02/R-06/R-05 | full set, gov record-only | **MiMo's shape** (operator ruling); GLM's narrow-path discipline preserved via verify-first + deferral rules |
| Checkpoints | none (record before/after) | final ratification only | five mandatory CPs | **MiMo's CP-1…CP-5** (operator ruling); DeepSeek's record-before/after table kept as the evidence discipline (§8) |
| Status claim | candidate | approved, execution-ready | draft, not authorized | **Execution-ready** (operator ruling); assessor signature pending |
| State snapshot | HEAD `06d3e93` | HEAD `de107f8` | HEAD `06d3e93` | **Fresh census at `e7d2725`** (§2.1); all three superseded; verify-first everywhere |
| T-0189 disposal | explicit dispose step | implicit (successor canary) | implicit | **Explicit, at CP-4** (DeepSeek's requirement, MiMo's checkpoint) |

**What was taken from each author (credit where due):**

- **DeepSeek (V4.1 Flash):** the baseline-delta table discipline (§2.2), concurrent-actor detection with the 60-second re-measure (Phase 0.3), the `[VERIFY]` convention, the action→decision→evidence table (§8), the rollback table and never-shortcut list (§9), the OQ→step traceability pattern (§14), the "mediocre vs great" framing (§13).
- **GLM-5.3-Flash Free:** the authorization table A-x (§3), the hard-constraint table N-x (§4), the claim vocabulary Confirmed/Derived/Unknown (§2), "documents inform; the ledger decides", "optimism is not a state transition", draft-don't-ratify (N-13), the abort/escalation table (§11), the completion-report requirement (§10), the profile-restriction rule as measured rather than assumed (A-9).
- **MiMo-V2.6-Flash Free:** verify-first gates and idempotency per phase (§7), the five operator checkpoints with recommended defaults (§6), the DoD verification matrix filled from measurements (§13), the flagged-assumptions section (§15), the enumerated six-slice landing pattern (Appendix B), the reading-order appendix (Appendix A), the single-session/restart model (B-20), the errata and uncommitted-inventory records (Phase 8), the binding-rules S→B mapping (§5).

---

*End of document. The executor stops after Phase 12 and hands back: dispatch resumption, push, and ratification are the operator's.*
