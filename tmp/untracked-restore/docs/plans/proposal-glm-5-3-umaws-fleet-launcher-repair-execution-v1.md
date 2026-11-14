---
document:
  title: "Proposal: UMAWS Fleet Launcher — Ordered Repair Execution Programme for a Fixer LLM Agent (narrow path to a passing supervised canary)"
  status: "Approved by operator interview. Ready for a fixer agent to execute. Project remains PAUSED; all project-state and dispatch-resumption decisions are reserved to the operator."
  version: "1.0.0"
provenance:
  author_llm:
    name: "GLM-5.3-Flash Free"
    version: "opencode provider, model opencode/glm-5.3-flash-free; proposal version 1.0.0"
  created_date: "2026-11-09"
  last_modified_date: "2026-11-09"
  scope: "C:\\temp\\projects\\testproject1 (branch main). Influenced by report-freebuff-UMAWS-Fleet-Launcher-repair-v1.md (Buffy's consolidated repair record), pilot/repair-resumption-checklist-v1.md, pilot/decisions.md (D-62…D-69), pilot/cards/canary-replacement-v1.md, docs/PDD.md (gate_cmd, G-001…G-006), AGENTS.md / CLAUDE.md operating contract, and fresh read-only measurements taken 2026-11-09 by this author (see Appendix A)."
  source_of_truth: "The Kernel ledger (.pm/events/*.jsonl) and outputs of pmk status / task show / worktree list / fleet check / pins check as re-measured by the fixer at entry — never this document's stale figures, and never the untracked tmp/ artefacts alone. Documents inform; the ledger decides."
---

# Proposal: UMAWS Fleet Launcher — Ordered Repair Execution Programme for a Fixer LLM Agent

**Proposal ID:** `proposal-umaws-fleet-launcher-repair-execution-v1`
**Author:** GLM-5.3-Flash Free (opencode), proposal v1.0.0
**Date:** 2026-11-09
**Status:** Approved by operator interview; execution-ready. Not a Kernel card and not registered as Kernel work — see the document-control note below.
**Audience:** A fixer LLM agent (agent-neutral: any capable coding agent) executing under this project's operating contract, and the human operator who supervises it.
**Done condition (single sentence):** A fresh supervised canary card reaches **`DONE`** through the real Launcher path — claim → lease → worktree → gate → merge — with a recorded evidence bundle, a clean-base gate verified at a recorded base, and a draft decision record awaiting operator ratification. Nothing more. The fixer then **stops and reports**.

> **Document-control note.** This proposal lives in `docs/reports/` per the project's formal placement convention, per explicit operator instruction. It is authored as a plain file rather than registered as a Kernel card; that is an **operator-authorized exception**, not a precedent. The fixer must register its *execution* work as cards; only the proposal document itself is unregistered.

---

## Contents

1. Purpose and overview
2. State at writing (this author's measurements, and what changed after Buffy's report)
3. Authorizations in force — what the fixer may decide, and what is reserved
4. Hard constraints — never do
5. Phase 0 — Entry: read the contract, measure the world, record drift
6. Phase 1 — Protective capture of the uncommitted working tree
7. Phase 2 — Reconcile the live lease T-0182
8. Phase 3 — Land the uncommitted repair in reviewable slices via pmk cards
9. Phase 4 — Confirm the base fix (tests/test_transport.py) on a clean base
10. Phase 5 — In-scope engineering items (R-02, R-06, R-05/OQ-06)
11. Phase 6 — Clean-base gate verification at a recorded base
12. Phase 7 — Fresh supervised canary to DONE
13. Phase 8 — Record the decision and stop
14. Evidence requirements across phases
15. Completion report requirement
16. Aborting, blocking, and escalation
17. Out of scope — record-only backlog
- Appendix A — State drift measured 2026-11-09 vs. Buffy's report
- Appendix B — Suggested slice inventory for Phase 3
- Appendix C — Prohibited/notify-only action summary table
- Appendix D — Provenance and change log

---

## 1. Purpose and overview

### 1.1 What this document is

A step-by-step, decision-complete instruction programme for one fixer LLM agent to take the UMAWS Fleet Launcher from its current state — repair implemented but largely uncommitted, clean-base gate apparently green but not Kernel-recorded, one phantom lease open, no canary at `DONE` — to a state where the operator can ratify a `PASS` decision and (separately, at operator discretion) resume dispatch.

### 1.2 Why it exists

Buffy's report (`report-freebuff-UMAWS-Fleet-Launcher-repair-v1.md`) diagnosed the system exhaustively (problems P-01…P-33, fixes F-01…F-19) and recorded that its own repair work was not landed and its canary had failed. Subsequent sessions (evidenced by the `assessment-claude-*` patch-review series and `tmp/` verification artefacts) appear to have advanced the work further — two commits landed the formerly-blocking `tests/test_transport.py` and the CNA work; the clean-base gate log reaches 100% pass; a sentinel run reports zero findings — **but none of that is validated against the Kernel's live state**: `T-0182` is still `LEASED` on the repository root, `T-0189` is still `REWORK`, the project is still `PAUSED`, and no new canary has been dispatched through the real path. The gap is no longer primarily engineering; it is **landing, reconciliation, and proof**.

### 1.3 The decisive premise (from Buffy §12, conclusion 9)

There are only two modes of work on this repository:

1. **Card work through the Launcher** — claim a card, lease it, work in `work/<task>-<fence>`, submit, let the oracles decide.
2. **Read-only investigation** — no edits, no transitions.

There is no third mode. Every failure in the record came from inventing a third mode. This proposal is built entirely out of mode 1, staged and ordered so that no step can destroy work another step protects.

### 1.4 How to read this document

Each phase states its **purpose**, its **steps** (with commands), the **evidence** that must exist when the phase completes, and a **pass/fail gate** to the next phase. Phases are ordered by dependency, not by difficulty. Do not reorder them without recording why as a decision note in your completion report. Where a step offers the fixer a genuine choice, the criterion is stated explicitly; where only the operator may decide, the proposal says so and defines the stopping point.

---

## 2. State at writing (this author's measurements, and what changed after Buffy's report)

All figures below were measured read-only on 2026-11-09 by this author, after Buffy's report was written. Treat every figure in *every* document — including this one — as a claim; Appendix A is a snapshot, and Phase 0 exists to supersede it.

### 2.1 What the Kernel reports

| Measure | Value |
|---|---|
| Branch / HEAD | `main` / `de107f8b06d37b44888b1c4872d306ae5e410ae8` |
| Project state | `PAUSED` |
| Tasks | 189 total: 36 `DONE`, 143 `VOID`, 8 `PROPOSED`, 1 `LEASED`, 1 `REWORK` |
| Active leases | 1 — `T-0182`, fence 151, holder `opencode-strongest`, agent `buffy` |
| Incidents | 103 |
| Chain | verifies; 3,486 events |
| Kernel worktrees | 23 |

### 2.2 What changed after Buffy's report (two commits, both correctly identified as `umaws-pilot <umaws-pilot@localhost>`)

| Commit | What it did | What it resolves |
|---|---|---|
| `9b3b70d` | "fix(coverage): track the §8 transport layer its baseline cites" — committed `tests/test_transport.py` | The **blocking base defect** (P-26/OQ-01): coverage case `8.0` cited a file absent from the canary base `bcf145c`. The fix this proposal's Phase 4 requires already exists **if** it verifies on a clean base. |
| `de107f8b` | "fix(cna): commit the transport-dependent rules and data layer" — 14 files, +3026/−97, including the formerly-untracked CNA work Buffy disclosed in §9 | The orphan CNA work on `main` is now committed under the correct repo-local identity. The "protect, don't touch" concern is substantially resolved, **residually**: any *still-untracked* CNA fragments must be captured in Phase 1, not judged. |

### 2.3 What remains uncommitted (the repair itself)

Tracked modified files at writing (28, excluding Kernel-written `.pm/` paths, which are never committed by hand):

- Fleet: `src/fleet/{conductor,dispatcher,harness,legacy,merge,project,spawn}.py`
- Kernel: `src/pmk/{events,worktrees}.py`
- Tooling: `tools/check_subprocess_env.py`
- Tests: `tests/fleet/test_adapter_paths.py`, `tests/fleet/test_conductor_leases.py`, `tests/fleet/test_fleet.py`, `tests/fleet/test_regressions.py`, `tests/pmk/test_worktree_lifecycle.py`, `tests/test_subprocess_env_lint.py`
- Reports/pilot records: `docs/reports/dispatch-failure-root-cause-and-remediation-v1.md`, `pilot/cards/canary-replacement-v1.md`, `pilot/decisions.md`, `pilot/dispatch-failure-root-cause-and-remediation-v1.md`, `pilot/repair-canary-runbook-v1.md`, `pilot/repair-resumption-checklist-v1.md`, `HANDOFF.md`, `agents.toml`

Plus a large volume of **untracked** material: this proposal's contemporaneous reports (`report-freebuff-UMAWS-Fleet-Launcher-repair-v1.md`, the `assessment-claude-*` series), verification artefacts under `tmp/` (bundles, oracle outputs, sentinel runs, `clean-base-gate.log`), and assorted scripts (`create_p0_tasks.py`, `insert_1205.py`, `test_kernel_hash.py`, …). Phase 1 captures it; Phase 3 lands what belongs in slices; most of `tmp/` is **evidence, not product** — it is preserved, not committed wholesale.

### 2.4 The apparent-green/stale-ledger divergence — the core hazard

`tmp/clean-base-gate.log` shows a full dotted pass; `tmp/sentinel-final3.json` reports zero findings across I1…I17; `tmp/close-final3.json` shows G-oracles and gate exiting 0. If accurate, the *code* may already be green on a clean base. But:

- These artefacts are **untracked files with no Kernel guarantee**. They could be from a different tree, a different base, or a different working-copy state.
- The ledger still shows `T-0182` `LEASED` and `T-0189` `REWORK`.
- Neither state has been reconciled through `pmk`.

Therefore: the fixer's job is **not** to rewrite the system. It is to **verify, land, reconcile, and prove** — and to close the loop with a real canary. Optimism is not a state transition.

---

## 3. Authorizations in force — what the fixer may decide, and what is reserved

These authorizations were granted explicitly by the operator on 2026-11-09 (recorded verbatim as decisions in the interview that produced this proposal). They are the fixer's letter of authority. Anything not listed here is **not authorized**.

| # | Authorization | Scope and rules |
|---|---|---|
| **A-1** | **Scope** | Narrow path only: Phases 0–8 of this proposal. The fixed engineering extras in Phase 5 (R-02, R-06, R-05/OQ-06) are the *only* optional engineering items in scope. Everything else is record-only (§17). |
| **A-2** | **Done condition** | A fresh supervised canary reaches `DONE` through the real path with a recorded bundle. Dispatch resumption (`A10`) is **not** part of "done". |
| **A-3** | **Target agent** | The fixer is agent-neutral; instructions must make sense to any capable coding agent. If the fixer is Buffy, it must read its own §9 self-audit first and take S-01…S-18 as binding on itself. |
| **A-4** | **T-0182 lease** | The fixer decides, with criteria (Phase 2): verify the deliverables through the normal pipeline if sound, otherwise revoke via `pmk` with a recorded reason. No `.pm/` hand-edits either way. |
| **A-5** | **tests/test_transport.py (base fix)** | The fixer investigates then decides (Phase 4): the file is already tracked after `9b3b70d`; the fixer confirms or invalidates the fix on a clean base and records either outcome. Committing or reworking the case further is within authority if the clean-base verification fails. |
| **A-6** | **Landing the repair** | Reviewable slices, landed **via pmk cards** (claim → lease → `work/` worktree → commit → submit → merge/gate), with the repo-local `umaws-pilot` identity. Direct-to-main commits without card ceremony are **not** authorized for the fixer. |
| **A-7** | **Push** | **Local only. No push to origin** (`https://github.com/tiwaking-ops/UMAWS-Fleet-Launcher.git`) at any point, no exceptions, and no force/reset/history-rewrite of any kind. |
| **A-8** | **Project state** | Reserved to the operator. The fixer must **never** run a command that changes `project_state`, never authorizes `A10`, and never starts or resumes dispatch outside the single canary of Phase 7. |
| **A-9** | **In-scope engineering extras** | R-02 (lease admission checks), R-06 (wire `Dispatcher.reconcile()` into Console startup, tested at startup path), R-05/OQ-06 (conftest collision fix + combined-collection test). Each must land as its own card via the normal path (Phase 5). |
| **A-10** | **Supervision of the canary** | The fixer runs the canary autonomously and presents the full evidence bundle afterwards; the **operator ratifies** the resulting decision. The fixer records the bundle and drafts the decision; it does not ratify. |
| **A-11** | **Constraints** | No budget/turn cap beyond "stop when done or blocked". Profile restriction: any spawned worker must use a **surviving** (non-disabled) fleet profile — the disabled `pi-orca-deepseek` must never be selected or relied upon; if the only available profile is disabled, stop and report (§16). |
| **A-12** | **CNA work** | Protect, don't touch. Include any still-untracked CNA fragments in the Phase 1 protective capture; never judge it, never commit it as product work, never revert it. It is outside the Launcher's scope (the two existing commits aside). |
| **A-13** | **Governance items (P-23, P-24, OQ-07, OQ-08, sentinel baseline, report placement drift)** | **Record-only.** The fixer documents anything it observes, in its completion report, and takes no remedial action. |

---

## 4. Hard constraints — never do

These are absolute. Violating any of them is grounds to abort the entire programme and report. They distill Buffy's S-01…S-18; the full list remains binding and applies to the fixer.

| # | Never | Why (from the record) |
|---|---|---|
| **N-01** | Never edit `main` directly for task work | Out-of-band main-tree edits are invisible to the Kernel and unprotected by a fence (P-01, Buffy §9). |
| **N-02** | Never hand-edit anything under `.pm/` | The Kernel is the writer (AGENTS.md). Hand edits break provenance and the chain. |
| **N-03** | Never push, never force-push, never `reset --hard`, never rewrite history, never delete a worktree before capture-and-verify | A-7; P-17/P-18; dirty trees are refused, not forced (P-22, REC-02 before REC-01). |
| **N-04** | Never commit as the human operator | P-23. Verify `git var GIT_AUTHOR_IDENT` / `git config user.name` resolves to `umaws-pilot <umaws-pilot@localhost>` before every commit. |
| **N-05** | Never trust a green main tree as proof about a clean base | P-26 caused the T-0189 failure exactly this way (S-14). Proof lives in a clean worktree at a recorded base. |
| **N-06** | Never record or accept a verdict as bare exit code | P-15. Every verdict in an artifact the fixer produces carries captured output. |
| **N-07** | Never choose your own tests for acceptance verification | S-04. Oracles decide; use the card's oracles and the project `gate_cmd` from `docs/PDD.md`. |
| **N-08** | Never copy files from the main tree into a worktree because a hint claims they're missing | P-05/P-06/S-07 — check the worktree first. |
| **N-09** | Never spawn a worker through a disabled profile (`pi-orca-deepseek`) or select a profile that the current `pmk fleet check` marks disabled | P-12/A-11. |
| **N-10** | Never flip `project_state` or authorize `A10` | A-8. Even if every test is green. |
| **N-11** | Never inherit a lease silently — audit any lease before working near it, and resolve yours before stopping | P-20/P-27; T-0182 is the standing counterexample. |
| **N-12** | Never bypass a hooks/guard failure with `--no-verify`, `--force`, or by editing the guard | F-07/F-08 guards exist for exactly this; bypassing recreates P-23. |
| **N-13** | Never delete or overwrite the Phase 1 protective capture, even after slices land | It is the undo path for everything; it stays until the operator says otherwise. |
| **N-14** | Never ratify a decision yourself | A-10. You draft; the operator ratifies. A thin `{"choice":"ratify"}` is not a decision record (P-24). |

---

## 5. Phase 0 — Entry: read the contract, measure the world, record drift

**Purpose:** Anchor everything that follows in measured reality, not in any document's claims — including this one. Buffy's report, this proposal, the checklist, and the `tmp/` artefacts are all claims until re-measured.

### Steps

1. Read `AGENTS.md` and `CLAUDE.md` (the operating contract).
2. Read `pilot/repair-resumption-checklist-v1.md` — it defines the target state you are completing. Record which of its items are marked done/failed/blocked and treat each as a claim.
3. Read Buffy's report §1, §7, §9 (execution summary, measured state, self-audit). If you are Buffy, §9 is about you; take it as binding.
4. Run and record the full read-only entry census, saving raw output to a timestamped file under `tmp/entry/` (this is evidence capture, not `.pm/` editing):

```powershell
pmk status
pmk task list
pmk task show T-0182
pmk task show T-0189
pmk worktree list
pmk fleet check
pmk pins check
git rev-parse HEAD; git branch --show-current
git status --short
git diff --stat
git worktree list
git ls-files --error-unmatch tests/test_transport.py
python -c "import cna, pmk; print(cna.__file__, pmk.__file__)"
git var GIT_AUTHOR_IDENT
```

5. Confirm `project_state == PAUSED` and record it (A-8: you will not change it). Confirm `active_leases` and reconcile expectations against Phase 2.
6. Confirm the import resolution (step 4's `python -c`) points where you expect, and that `GIT_AUTHOR_IDENT` is `umaws-pilot <umaws-pilot@localhost>`. If the identity is the operator's global identity, **stop before any commit** and report (N-04).
7. Diff your census against §2 of this proposal and Appendix A. Any drift is expected and recorded in your entry notes; material drift (different lease set, different `T-0189` state, unexpectedly advanced HEAD) is reported to the operator **before** Phase 3 if it changes the meaning of an authorization in §3.

### Evidence required

`tmp/entry/<timestamp>/*.txt` files for all step-4 commands, plus an entry note listing every drift item versus this proposal and Buffy's report, with each labelled **Confirmed / Derived / Unknown** (the project's claim vocabulary).

### Gate to Phase 1

The census is recorded, the import path verified, and the identity safe. If `pins check` or `fleet check` fails, treat it as a **blocker**, not a warning: proceed to Phase 1 (protection must happen regardless), then stop and report before Phase 2.

---

## 6. Phase 1 — Protective capture of the uncommitted working tree

**Purpose:** Make it impossible for any later step — slice landing, gate runs, canary dispatch — to lose uncommitted work. Buffy's report identifies this as the single most time-critical risk (OQ-03). Everything uncommitted is captured **twice**: as a patch and as a self-contained bundle.

### Steps

1. Record the exact working-tree census again and hash it:

```powershell
git status --short | Out-File -Encoding utf8 tmp\entry\capture-status-before.txt
git diff > tmp\capture\repair-working-tree-timestamped.patch
git diff --stat > tmp\capture\repair-diff-stat.txt
```

2. Archive untracked material. Untracked files include this proposal's records and `tmp/` artefacts; compress rather than selectively judging:

```powershell
git ls-files --others --exclude-standard | Out-File -Encoding utf8 tmp\capture\untracked-list.txt
# Then create a self-contained archive — e.g. a tar/zip of the listed untracked files — under tmp\capture\untracked-<timestamp>.zip
```

3. Record the archive's path, its SHA-256 hash, and the file list, in a small manifest `tmp/capture/README.md`.
4. Verify restorability **without touching the live tree**: on a throwaway temporary clone or detached worktree, apply the patch / expand the archive into a scratch directory and confirm spot files byte-match. Record the verification output. A backup you cannot restore is not a backup.
5. Also verify the dirty `work/` worktrees (currently 3 dirty per `pmk worktree list`): for each dirty Kernel worktree, run the **Kernel's** capture commands (F-09's `archive_tree` → `verify_archive` path; do **not** use ad-hoc copying). If any tree's capture cannot be verified, mark it and do not delete it.

### Evidence required

- One patch file covering all tracked modifications (excluding nothing; `.pm/` Kernel-written files included in capture so the snapshot is whole — but they are **never committed by hand**, see N-02).
- One archive of untracked files, hashed, with a restorability verification record.
- Per-dirty-worktree capture-or-refusal notes.

### Gate to Phase 2

The patch, archive, and restorability verification all exist and are recorded. Note: the Kernel-written `.pm/` paths in the patch are for disaster recovery only; the fixer must never commit them (N-02) — when slices are built in Phase 3, `.pm/` paths are excluded from every slice's file list.

---

## 7. Phase 2 — Reconcile the live lease T-0182

**Purpose:** Close the standing governance defect (OQ-02, P-27): a `LEASED` task (fence 151, agent `buffy`, holder `opencode-strongest`) whose `worktree` is the **repository root**, with no `pid`, no `creation_time`, and no `expires_at`, while deliverables exist untracked and unsubmitted. A phantom lease blocks every later phase's clean-resume guarantee.

### Authorized decision (A-4) and the criteria

The fixer decides between **submit** and **revoke**, strictly through `pmk` (N-02: no hand edits), using these criteria:

1. **Read the card and deliverables.** `pmk task show T-0182`; the card's write scope names `docs/release-status.md` and `tests/test_release_status.py`. Confirm both exist on disk and are untracked (`git status --short docs/release-status.md tests/test_release_status.py`).
2. **Judge soundness, not provenance.** Whether *this* session or another created the work is **Unknown** and irrelevant to the decision (Buffy §9.4); only quality decides. Test the deliverables against the card's acceptance oracles **in a clean base context** — per N-05, run them from a fresh worktree, not the dirty main tree.
3. **If the deliverables pass the card's oracles:** verify the lease's shape is acceptable to submit. Given this lease lacks `pid`/`expires_at` and points at the repo root — both recorded invariants violations (P-20) — and the project is `PAUSED` (A-10: no lease should be active), the expected outcome for a *sound* deliverable set is: capture the deliverables into the protected patch (already done in Phase 1), **revoke the lease via pmk with a recorded reason** ("lease shape invalid: repo-root worktree, no pid, no expiry; deliverables preserved under card or backlog via normal path"), and land the deliverables properly in Phase 3 as their own slice/card, if their card ceremony can be created within the repair's scope. If landing them is outside the narrow path's spirit, record them as preserved backlog instead — **revocation with preserved deliverables is a fully acceptable outcome**.
4. **If the deliverables fail the oracles:** revoke via `pmk` with the recorded reason (failing oracle output attached).
5. Either way, verify the lease closes cleanly: `pmk status` shows `active_leases: 0` afterwards, and the transition is recorded in the ledger by the Kernel (never by you hitting files directly).

### Evidence required

- `pmk task show T-0182` before and after.
- Oracle output (not bare exit codes) for the deliverables, with the tree/base they ran in.
- The recorded revocation/decision reason as emitted by `pmk`.

### Gate to Phase 3

`active_leases: 0` and a recorded reason. If `pmk` cannot revoke cleanly (e.g. fence errors, unknown command), **stop and report** — do not improvise against the ledger (§16).

---

## 8. Phase 3 — Land the uncommitted repair in reviewable slices via pmk cards

**Purpose:** Convert the uncommitted repair (F-02…F-10 and the pilot-record updates in §2.3) into landed, ledger-proven commits — one reviewable slice at a time, each through the sanctioned path (A-6). The code is already written and reviewed (the `assessment-claude-*` patch-review series v1 → v1.2.14 is the review trail); this phase is about provenance, not invention.

### Rules for all slices

- Each slice is one card: propose → card admitted → claimed → leased → work in `work/<task>-<fence>` → commit there with the `umaws-pilot` identity → submit → let the harness/gate decide. Use the normal `pmk` channels and existing conventions; **the card pipeline is the work**.
- Each slice's file list is fixed in advance, taken from Appendix B or your own equivalent, and must **exclude** `.pm/**` (N-02) and `tmp/**` (evidence, not product).
- Include a one-line **slice manifest** in the commit message body: files included, tests covering them, which F-*/OQ-* items the slice addresses.
- If a slice's merge gate fails, fix in the worktree and resubmit; if it keeps failing, capture output (N-06) and route to §16.
- Apparent-green `tmp/` runs are **not** acceptance proof (§2.4); the harness's own gate run on each slice is the proof.

### Suggested slice order (rationale in Appendix B)

1. **S1 — Fleet/Launcher kernel of the repair:** `src/fleet/*.py` + `tests/fleet/*` modifications.
2. **S2 — Kernel worktrees + events:** `src/pmk/*.py` + `tests/pmk/test_worktree_lifecycle.py`.
3. **S3 — Tooling + lint test:** `tools/check_subprocess_env.py` + `tests/test_subprocess_env_lint.py`.
4. **S4 — Pilot records and config:** `pilot/**` modifications, `HANDOFF.md`, `agents.toml`, the dispatched-report edits under `docs/reports/`.

### When slices are blocked or reordered

Order within Phases 3↔5 is negotiable **once and for the whole programme**: if you reorder, record why in the completion report. Phase 4 must precede Phase 6 (it defines the base Phase 6 verifies).

### Evidence required

Per slice: card id, lease/fence, commit hash, harness output and gate output (captured, N-06), `pmk status` deltas. The slice is done when `pmk status` shows it `DONE`.

### Gate to Phase 4

All in-scope F-register slices are `DONE`, or an explicit, recorded remainder (with reasons) awaits the operator. `active_leases: 0`; no dirty tracked product files remain except `.pm/` Kernel-written paths and anything deliberately deferred and recorded.

---

## 9. Phase 4 — Confirm the base fix (tests/test_transport.py) on a clean base

**Purpose:** §2.2's `9b3b70d` committed the formerly-missing file; `de107f8b` landed the code it cites. This phase converts "the fix was committed" into "the fix is verified from a clean base" — the exact distinction that failed `T-0189` (P-26) and made `D-69` `FAIL`.

### Steps

1. Read the coverage case `8.0` in `tests/test_rules_baseline.py` and the now-tracked `tests/test_transport.py`. Confirm the citation is satisfied by the committed tree — the file's content must be what the baseline claims it tests (A-5: investigate, then decide).
2. From a detached clean worktree at the current base:

```powershell
git worktree add --detach <tmp-path>\cleanbase-verify HEAD
# in that worktree, with the environment pinned per src/fleet/runenv.py::worktree_env() semantics:
python -c "import cna, pmk; print(cna.__file__, pmk.__file__)"   # must resolve INSIDE the clean worktree
python -m pytest -q tests/test_rules_baseline.py
python -m cna.tools.coverage --check
python -m cna.tools.rules_index --check
```

3. Record full output (N-06). Any failure here means the base remains broken: under A-5 you may then commit the file (if legitimately baseline) or rework case `8.0` (if the citation is erroneous) **as a card slice**, and re-verify.
4. Remove the detached verification worktree when finished (it is clean and treeless by construction; removing it is safe — record that it contained no work).

### Evidence required

Clean-base outputs with full text, the verified base commit hash, and the import-resolution proof from inside the clean tree.

### Gate to Phase 5

All three clean-base verifications pass, recorded with output.

---

## 10. Phase 5 — In-scope engineering items (R-02, R-06, R-05/OQ-06)

**Purpose:** Close three engineering gaps the operator explicitly brought into scope (A-9). Each is its own card slice, same discipline as Phase 3.

| Item | Content | Done when |
|---|---|---|
| **R-02** | Kernel admission check rejecting a lease whose `worktree` is the repository root, or which carries no `pid`/`expires_at` while the project is paused | Check exists (Kernel, not fleet-side), has tests proving both rejection modes, and is landed `DONE` via a card. Do **not** retrofit T-0182 retroactively — Phase 2 already handled it. |
| **R-06** | `Dispatcher.reconcile()` wired into Console startup, with a test exercising the **startup path** (not merely the method) | Runnable path test passes; slice `DONE`. |
| **R-05/OQ-06** | Resolve the `tests/pmk/conftest.py` vs. fleet conftest collision (`ImportError: cannot import name 'FIXTURE_ROOT'`); add a combined-collection test `pytest tests/fleet tests/pmk/<summary>` that exercises the merged collection | Combined collection succeeds in a clean worktree; slice `DONE`. |

### Rules

- R-02 must prefer refusal with a recorded reason over silent correction — the Kernel refuses invalid states, it does not silently repair them.
- R-05's fixture rename must keep every existing fleet test passing; run the full fleet suite within the clean-base discipline.
- If any item reveals deeper structural problems, scope them out (**record-only**, §17) rather than expanding here.

**Gate to Phase 6:** three slices `DONE` (or explicitly recorded deferrals with reasons).

---

## 11. Phase 6 — Clean-base gate verification at a recorded base

**Purpose:** Establish, as a single recorded artefact, that the *whole* gate passes from a clean base — the condition checklist item 13 requires and that last failed (P-26).

### Steps

1. Choose the base: current `HEAD` **after** Phases 3–5 land. Record its full SHA.
2. Create a detached clean worktree at that SHA; run the environment-pinned gate exactly as `docs/PDD.md` defines `gate_cmd` — in full, not a subset. Record all output (N-06) and the base SHA.

```powershell
git worktree add --detach <tmp-path>\cleanbase-gate <base-sha>
# inside: verify imports resolve inside the tree, then run the full gate_cmd; capture stdout/stderr and exit code
```

3. Cross-check the result against the checklist: item 13 ("suite green") should now be satisfiable **if** the whole suite is collectable; if the R-05 slice hasn't yet resolved the conftest collision, run the gate in the two-part form that works, and record both halves with the same rigour. Do not average two half-runs into one "pass" claim — label halves as halves.
4. Clean up the detached worktree (record: clean, nothing captured).

### Evidence required

Full gate output at a recorded SHA, import-resolution proof, the artefact under `tmp/entry/` or `tmp/verify/`.

### Gate to Phase 7

The gate is green from the clean base, or its failure is diagnosed to a specific, reproduced cause that routes through §16 before any canary.

---

## 12. Phase 7 — Fresh supervised canary to DONE

**Purpose:** The done condition (A-2). One canary card dispatched through the **real** Launcher path on the repaired, landed, clean-base-verified system; it is the first time since `T-0189`'s failure that the pipeline proves itself end-to-end.

### Steps

1. **Restate the design authority.** The canary design and operator packet already exist: `pilot/cards/canary-replacement-v1.md` and `pilot/drafts/d-69-canary-operator-packet-v1.md`. Reuse them; do not improvise a canary (S-16 in Buffy's safeguards; Buffy's F-18). Update both only as needed to reflect the repaired base and the Phase 3–5 landed state.
2. **Create the canary card through `pmk`** in the normal way: card type `task`, title like "Supervised canary: record repaired-dispatch verification (D-69 successor)", a single-file write scope (e.g. `docs/reports/dispatch-repair-verification-v1.md`), acceptance oracle(s) that verify the file records the run's own evidence, and — critically — **`hint_base_commit` set to the recorded Phase 6 base SHA** with a hint that asserts nothing else (P-05/P-06: hints must describe the tree that exists).
3. **Dispatch via the real path only:** the Launcher's own dispatch machinery — `pmk` card lifecycle, worktree, ORDER.md, worker spawn, harness oracles, submit, merge + `gate_cmd`, integrate. The fixer may be the *supervisor* of the run, but the *pipeline* must perform every transition. Outside-pipeline transitions are out of bounds even now (N-01…N-03).
4. **Profile restriction (A-11):** the canary's chosen worker profile must be a surviving, non-disabled profile per the current `pmk fleet check`. `pi-orca-deepseek` and any other disabled profile must never be selected. If the only viable profiles are disabled, stop and report.
5. **Supervision (A-10):** the fixer runs the canary autonomously — it does not wait for the operator — but presents the bundle afterwards for operator ratification. The fixer does **not** ratify the decision (N-14).
6. **Record at every stage** with full output (N-06): card creation, claim, fence, worker start/exit, harness oracle outputs, submit, bundle id, gate output, integrate.
7. Expected outcome is one of:
   - **PASS:** canary reaches `DONE`, bundle recorded → Phase 8 with a draft `PASS` decision.
   - **FAIL:** canary ends `REWORK` with full captured gate output → Phase 8 with a draft `FAIL` decision that names the reproduced cause. A failed canary is a complete, reportable outcome — do not iterate into a third-and-fourth canary within this programme; route to §16.

### Evidence required

Bundle id (`EB-<task>-<fence>`), gate stdout/stderr at the recorded base, task state transition trail from the ledger read via `pmk task show`.

### Gate to Phase 8

The canary has a terminal state and a bundle. No permissive interpretation of "mostly working" is valid here; `DONE` is `DONE`, `REWORK` is `REWORK`.

---

## 13. Phase 8 — Record the decision and stop

**Purpose:** Convert the canary outcome into the record so the operator can act — and relinquish every remaining authority (A-8, N-14).

### Steps

1. Draft the decision record in `pilot/decisions.md`'s established field order (date · who · decision · alternatives · what it leaves untested). Name it the successor to `D-69` (e.g. `D-70`, per the register's next free id — verify against the file).
2. Content:
   - **If `PASS`:** state that a fresh supervised canary on the repaired base reached `DONE` via the real path; cite the task id, fence, bundle, base SHA, and gate output; record that `A10` authorization and any `project_state` change remain reserved to the operator.
   - **If `FAIL`:** state the reproduced failure with captured output, its class (using Buffy's classes A–G), and the minimal path forward; record that dispatch stays paused.
3. Do **not** change `project_state`, do **not** authorize `A10`, do **not** push, do **not** ratify. Draft and stop.

### Evidence required

The draft decision, the canary bundle reference, and `pmk status` at stop time.

---

## 14. Evidence requirements across phases

Wherever this proposal says "record" or "full output", the following minimum applies:

- **Output, not exit codes** (N-06): reuse the existing gate diagnostic convention (`src/fleet/merge.py::_gate_diagnostics()` and Buffy's F-03) wherever the pipeline offers it; for ad-hoc evidence, capture stdout and stderr separately with timestamps.
- **Tree and base with every run:** every output file records the commit SHA and worktree path it was produced in. A result without `(tree, base)` is uninterpretable.
- **Claim labels:** in the completion report, every factual claim is **Confirmed / Derived / Unknown** per the project's standard (Buffy §2.4). This proposal deliberately avoids restating stale numbers; your entries should follow suit.
- **Location:** scratch evidence under `tmp/<phase-id>/`, protectively hashed; anything expected to outlive the session (draft decisions, the completion report) goes to its proper register location via the normal path.

---

## 15. Completion report requirement

When Phase 8 completes (or the programme aborts), the fixer produces one completion report:

1. **Filename/path:** a formal report under `docs/reports/`, named to follow the register convention and to be distinguishable from the pre-repair report. If it is instead placed by operator instruction elsewhere, state the instruction in the report's own document-control note (the way Buffy's report did for its root-level placement).
2. **Required content:**
   - State at entry vs. state at completion (task distribution, leases, worktree census, HEAD, dirty count).
   - Per phase: what was executed, evidence artefacts, pass/fail.
   - The decision (draft) and its outcome.
   - The slice inventory: card ids, fences, commit hashes.
   - Any deviation from this proposal (order changes, deferrals, aborts), each with reason.
   - Record-only observations from §17 (anything the fixer noticed but did not act on), labelled properly.
   - A short self-audit if the fixer deviated from the operating contract in any way — the standard set by Buffy §9 and upheld by every report since.
3. **Provenance:** sign with the fixer's own `author_llm` name and version; never fabricate or inherit authorship.
4. If the programme aborted, the completion report replaces the "pass" narrative with the abort condition, preserved state, and the exact stopping point.

---

## 16. Aborting, blocking, and escalation

Stop-and-report ≠ fail. These conditions terminate execution with a written report rather than improvisation:

| Condition | Action |
|---|---|
| `pmk pins check` or `pmk fleet check` fails at entry after Phase 1 has protected the tree | Stop, report, do not touch leases or cards. |
| Any `pmk` command errors or produces an unexpected ledger state (fence error, unknown id, chain violation) | Stop. Do not attempt manual recovery. |
| The operator identity appears on any intended commit (N-04) | Stop before the commit; report. |
| Clean-base gate verification (Phase 6) fails with a cause outside this proposal's authorizations | Stop; the cause goes to §16's report with captured output. |
| No viable non-disabled profile for the canary (A-11) | Stop; report the profile census. |
| Any authorization in §3 cannot be honoured because repo state has changed materially since this proposal was written | Stop; report the drift and the specific authorization it invalidates. |
| Anything tempts a `--force`, a `.pm/` hand-edit, a push, or a state flip | That is itself the abort signal. |

In every case: Phase 1's capture exists first; keep it intact; describe exactly where you stopped and what is preserved.

---

## 17. Out of scope — record-only backlog

The following are **not** to be fixed or implemented by the fixer. Observation and documentation only, in the completion report:

- **R-04** — merge-tree pruning (`%TEMP%/pmk-merge-*` census; Conductor-driven prune).
- **P2 governance items** — R-11 (decision-record template validation), R-12 (stale incident claims/call-site errata), R-13 (sentinel red baseline explicit acceptance), R-14 beyond what Phase 7 already exercises.
- **P-23 / P-24 / OQ-07 / OQ-08** — historical identity anomaly and `Q-077`; record observations only. Do not rewrite history unilaterally.
- **OQ-05** — dirty `work/` trees beyond what Phase 1's capture already handles.
- **OQ-11** — model attribution (`MODEL_SERVED` empty list) — unless it blocks the canary's bundle, in which case record it as an explicit `Unknown`, it does not block `DONE`.
- **The `tmp/` artefact wholesale-cleanup decision** — record what you find; do not delete evidence you created or inherited (N-13 protects only the Phase 1 capture; ordinary `tmp/` hygiene remains reserved).
- **`docs/release-status.md`** / `tests/test_release_status.py` landing as product work beyond Phase 2's disposition (they are T-0182's deliverables, handled per A-4 criteria).

---

## Appendix A — State drift measured 2026-11-09 vs. Buffy's report

Measured read-only by this author immediately before writing this proposal. Buffy's report is its state of record at *its* writing; this appendix supersedes it only as of 2026-11-09 and Phase 0 supersedes both.

| Measure | Buffy's report | Measured here | Note |
|---|---|---|---|
| HEAD | `c1fac8f1…` | `de107f8b…` | Two commits since the report (see Appendix A table in §2.2) |
| Dirty paths | 257 | 248 | Census changed; capture II resolves it |
| `tests/test_transport.py` | untracked; cited by case `8.0`; absent from `bcf145c` | **tracked** (committed in `9b3b70d`) | The P-26 base defect materially advanced |
| CNA work | uncommitted on main, unowned (Buffy §9) | **committed** in `de107f8b`, 14 files, `umaws-pilot` identity | §9's deviation partly self-healed; residuals go through Phase 1 capture |
| Commits `e08fa8d`/`ebe46ce` attribution | operator's global identity; actor unknown | unchanged | Record-only (§17) |
| `T-0182` | `LEASED`, repo-root worktree, no pid/expiry | unchanged | Phase 2 target |
| `T-0189` | `REWORK`, fence 156, base `bcf145c`; `D-69` = `FAIL` | unchanged | No new canary dispatched via Kernel yet; Phase 7 target |
| Chain length | 3,485 events | 3,486 events | One event added since Buffy's report — a small drift, worth reconciling in Phase 0 entry notes |
| Project state | `PAUSED` | `PAUSED` | Reserved to operator (A-8) |
| Clean-base gate | failed on `bcf145c` at `bcf145c`/base-run | untracked `tmp/clean-base-gate.log` shows a full dotted pass at an unrecorded base | Apparent-green/stale-ledger divergence; Phase 4/6 exist to convert this into recorded proof |
| Sentinel | red baseline 5×I6 + 1×I13 | untracked `tmp/sentinel-final3.json` reports zero findings | Record-only (§17); reconcile claim in entry notes |

---

## Appendix B — Suggested slice inventory for Phase 3

Rationale: ordering by blast radius and by testability. S1 is the largest, most reviewable unit (the launcher's own logic with its dedicated test directory). S2 is the Kernel-side worktree/event lifecycle; landing it after S1 avoids overlapping test files while both are mid-flight. S3 is tiny and standalone — tooling plus its lint test — and can move earlier if S1 is blocked. S4 is documentation/pilot records, the lowest-risk slice, and can be last without delaying verification phases.

| Slice | Files (from `git status` at writing) | F-register items addressed | Tests covering |
|---|---|---|---|
| **S1** | `src/fleet/conductor.py`, `dispatcher.py`, `harness.py`, `merge.py`, `project.py`, `spawn.py`, `legacy.py` + `tests/fleet/test_adapter_paths.py`, `test_conductor_leases.py`, `test_fleet.py`, `test_regressions.py` | F-03 (gate diagnostics), F-04 (overseer fallback), F-05 (order contract), F-06 (precheck), F-07 (identity guard), F-10 (reaper guards) | Fleet test directory, harness/merge/conductor tests, env lint test indirectly |
| **S2** | `src/pmk/worktrees.py`, `src/pmk/events.py` + `tests/pmk/test_worktree_lifecycle.py` | F-09 (capture→verify→reclaim), F-10 (conductor reclaim via kernel), F-14 (kernel state records) | `tests/pmk/test_worktree_lifecycle.py`, pins/sentinel implicitly |
| **S3** | `tools/check_subprocess_env.py` + `tests/test_subprocess_env_lint.py` | F-02 (env invariant guard for new spawn sites) | `tests/test_subprocess_env_lint.py` alone; run it inside the worktree |
| **S4** | `pilot/cards/canary-replacement-v1.md`, `pilot/decisions.md`, `pilot/dispatch-…remediation-v1.md`, `pilot/repair-canary-runbook-v1.md`, `pilot/repair-resumption-checklist-v1.md`, `HANDOFF.md`, `agents.toml`, `docs/reports/dispatch-failure-root-cause-and-remediation-v1.md` | F-08 (recorded config), F-16…F-19 (decision/canary records) | None (documentary); commit message states that |

Additional untracked material (`report-freebuff-…`, `assessment-claude-*`, this proposal, `tmp/` evidence) is **preserved in the Phase 1 capture, not committed in S1–S4**. Landing it as product commits is out of scope for the narrow path unless the operator later chooses otherwise; the completion report should list it all with their SHA-256 hashes from the capture manifest.

---

## Appendix C — Prohibited/notify-only action summary

| Action | Status |
|---|---|
| Push to origin | **Prohibited** (A-7) |
| Change `project_state` or authorize `A10` | **Prohibited** (A-8) |
| `.pm/` hand edits | **Prohibited** (N-02) |
| Commit under the operator's identity | **Prohibited** (N-04) |
| Force/reset/history rewrite | **Prohibited** (N-03) |
| Delete a worktree before capture/verify | **Prohibited** (N-03) |
| Ratify a decision | **Prohibited** (N-14) |
| `--no-verify`/guard bypass | **Prohibited** (N-12) |
| Selecting a disabled profile for any spawn | **Prohibited** (N-09) |
| Main-tree direct edits for task work | **Prohibited** (N-01) |
| Discovery that a certificate needs updating, or material state drift invalidating an authorization | **Notify-only**: record and stop for operator review |

---

## Appendix D — Provenance and change log

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0.0 | 2026-11-09 | GLM-5.3-Flash Free (opencode) | First issue: operator-interview-vetted, ordered execution programme (Phases 0–8), authorizations A-1…A-13, hard constraints N-01…N-14, state-drift appendix, slice inventory, abort rules, completion-report requirement |

**Provenance statement.** This proposal was authored from (a) a full read of `report-freebuff-UMAWS-Fleet-Launcher-repair-v1.md`, and (b) fresh read-only measurements in the live repository on 2026-11-09 (`pmk status`, `git rev-parse/status/log`, targeted inspection of the two post-report commits and the untracked `tmp/` verification artefacts' tails). The operator's authorizations in §3 were granted directly, by explicit interview answers on the same date. No `.pm/` file was read beyond read-only `pmk` command output; no task was leased; no file was modified by this author other than this document itself. Where the record could not establish a fact, it is labelled so rather than inferred. Buffy's report is the register of prior problems and fixes; this proposal deliberately does not re-litigate them — it executes the narrow path that closes them.
