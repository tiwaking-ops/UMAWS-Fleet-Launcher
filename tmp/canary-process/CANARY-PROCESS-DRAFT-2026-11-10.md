# Canary evidence processing — draft for operator approval

**Prepared:** 2026-11-11 03:05 +1300 (2026-11-10 UTC) by Buffy/Codebuff.
**Status:** draft only. No tracked file edited in this pass; no commit; no push.

## 0. Which session is answering, and what it touched

This is **Buffy / Codebuff** (Freebuff desktop agent) working in `C:\temp\projects\testproject1`.

**Did this session edit the live tree on 2026-11-10?** Yes. Two commits on `main` predate this prompt and were made by this session:

- `eb0c226` `docs(pilot): reconcile handoff with canary results and counts` — 2026-11-11 02:14:50 +1300
- `68907fe` `docs(pilot): record supervised base canary result` — 2026-11-11 02:46:50 +1300 (current HEAD; parent `eb0c226`, whose parent is `53871a7`)

Those commits are later than the edits reviewer item 1 names (17:35 and 22:49 NZ) and are part of what item 1 has to settle. **After reading this prompt, this session made no tracked edit and no commit.**

The live working tree was already dirty when this pass began: 31 modified tracked files plus a large untracked backlog (including `src/fleet/owner.py` and `src/fleet/canary.py`). This pass did not create those modifications, and the session that did is **unknown** here.

Evidence base: `.pm/events/*.jsonl` (3,630 events read; `HANDOFF.md` records I1 verifying at that count — `pmk sentinel` was not re-run in this pass), the `.pm/evidence/` bundles, and git objects at `68907fe`.

## 1. The four supervised canary cards

| Card | Fence | base_commit | Profile | Agent wall | SUBMITTED | ORACLE_RESULT (span) | Gate cmd / exit | Merge / author | Bundle (bytes) | gate_output | Final state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **T-0189** | 156 | `bcf145c86e483df4d980e03fff8a743076a35571` | `kilo-auto` / `kilo` | 81 s (`AGENT_STARTED` seq 3472 `06:23:20Z` → `AGENT_EXITED` seq 3475 `06:24:41Z`; D-69 says "about 82 s") | seq 3478 `06:24:41Z` | seq 3479 `06:28:54Z` (253 s) | `pytest -q` / **exit 1** (recorded) | **none** — no merge commit | `EB-T-0189-156`, 1,849 | **absent** | **VOID** — `REVOKED` seq 3505, `TASK_VOIDED` seq 3506, reason `Superseded by T-0190`; current fence 157 |
| **T-0190** | 157 | `e302119728dcdf066b7f5555a14df4e5424da1bc` | `kilo-auto` / `kilo` | 120 s (seq 3510 `17:49:33Z` → seq 3513 `17:51:33Z`) | seq 3516 `17:51:35Z` | seq 3518 `17:58:26Z` (411 s) | `pytest -q` / `ok: true`, **no `exit` key** | `0edc0dc0f35b8f48b2f74f4f07f4a09bb087e723` / `umaws-pilot <umaws-pilot@localhost>` | `EB-T-0190-157`, 1,849 | **absent** | `DONE` (`INTEGRATED` seq 3520) |
| **T-0191** | 158 | `ce22591530ac17fe5f3dda313426d179993ded2c` | `kilo-auto` / `kilo` | 65 s (seq 3529 `18:28:12Z` → seq 3532 `18:29:17Z`) | seq 3534 `18:29:18Z` | seq 3535 `18:35:13Z` (355 s) | `pytest -q` / `ok: true`, no `exit` key; bundle `gate_output` records exit 0 | `c7fcdf39af7beb41c9dc9dcb829fc27310a8fc7a` / `umaws-pilot <umaws-pilot@localhost>` | `EB-T-0191-158`, 3,566 | **present** — dict `{cmd: pytest -q, exit: 0, ok: true, failed_tests: []}` plus stdout/stderr tails | `DONE` (`INTEGRATED` seq 3537) |
| **T-0196** | 159 | `9bb0139a16bb6fa6d6a2fda2ef29a1a3b653db3b` | `kilo-auto` / `kilo` | 100 s (seq 3548 `19:56:31Z` → seq 3551 `19:58:11Z`) | seq 3554 `19:58:12Z` | seq 3556 `20:09:33Z` (681 s) | `pytest -q` / `ok: true`, no `exit` key; bundle `gate_output` records exit 0 | `951d1ee5b40aff2d24eb5807195fd4999d33705c` / `umaws-pilot <umaws-pilot@localhost>` | `EB-T-0196-159`, 3,566 | **present** — same shape as T-0191 | `DONE` (`INTEGRATED` seq 3558) |

Notes that matter for the record:

- The chain contains **zero `TASK_DONE` events**. `DONE` is the kernel projection after `INTEGRATED`; the state is reported by `pmk task show` / the task view, not by an event of its own.
- The pre-0004 event schema records `exit` only on failure. A *passing* gate is represented by `ok: true` alone, so no pass in this table carries a numeric exit in `.pm/events`. For T-0191 and T-0196 the `0` survives only inside the bundle's `gate_output`; for T-0190 it survives nowhere.
- All four cards were created, admitted and dispatched in the **live** kernel. `pmk canary run` is not the recorded dispatcher for any of them (see §4).
- Bundle sizes are exact byte sizes of `.pm/evidence/<id>/bundle.json`.

## 2. T-0189 is a real gate failure

**Recorded FAIL, not history to be waved away.** `ORACLE_RESULT` seq 3479 at `06:28:54Z`: `cmd: pytest -q`, `exit: 1`, `ok: false`, `stage: gate`, with `failed_tests: ["FAILED tests/test_rules_baseline.py::test_coverage_reports_case_statuses_and_evidence"]`. The captured stdout tail shows the test body failing inside its per-case assertions.

**Cause (base tree, not the dispatch repair):** the test iterates the generated coverage cases and requires each referenced test file to exist; case `8.0` references `tests/test_transport.py`, which is absent from committed base `bcf145c`. `tests/test_transport.py` is tracked at current HEAD (added by `9b3b70d`), and the self-contained base `53871a7` passes a full clean-worktree `pytest -q` (`tmp/clean-head-full2.log`, exit 0).

**What happened next, in order:** operator re-checks at seq 3493 (`exit 0` at `06d3e93`) and seq 3494 (`exit 1` at `4e72901`); `TASK_READY` seq 3495 at `10:31:51Z`; then `REVOKED` seq 3505 and `TASK_VOIDED` seq 3506 at `17:39:18Z` — reason `Superseded by T-0190: fresh canary card created at e302119 after T-0189 exhausted its 1/1 attempt on stale base bcf145c`.

The correct word is **superseded**, and it is not a synonym for exonerated. The gate failed on a real base-tree defect; later passes do not make T-0189 green, and D-69 remains the recorded FAIL.

## 3. DoD-6 is proven twice, not three times

`EB-T-0191-158` and `EB-T-0196-159` both carry a non-empty `gate_output` object (`cmd: pytest -q`, `exit: 0`, `ok: true`, `failed_tests: []`, stdout/stderr tails). Both bundles are 3,566 bytes.

`EB-T-0190-157` is 1,849 bytes — byte-identical in size to `EB-T-0189-156` — and its top-level keys stop at `context_hash`; **there is no `gate_output` key**. Its `ORACLE_RESULT` (seq 3518) is `{cmd: pytest -q, ok: true, stage: gate, reintegration: false, no_ff_fallback: false}`. It is a **dispatch-path pass**, not a DoD-6 proof.

Therefore:

- DoD-6 "non-empty `gate_output`" is proven **twice** (`T-0191`, `T-0196`).
- DoD-1/DoD-2 are untouched by this pass.
- No decision text is rewritten; §6 carries an appended erratum that scopes D-69 and D-73.

## 4. What the log does not show — unknowns

**4.1 Canary runner.** The live chain (3,630 events) contains **zero** `CANARY_STARTED`, `CANARY_FINISHED` — in fact zero event types beginning `CANARY`. `src/fleet/canary.py` is untracked. So `pmk canary run` has never produced a durable record **in the live chain**, and the three passes above came from `pmk dispatch run` / the Console, not from `run_canary`. The single-owner canary runner is **not tested** by this evidence.

*Correction to the absolute form of that claim:* the isolated-base worktree `tmp/canary-base-20261110` **does** contain a durable canary record — `CANARY_STARTED` seq 3124 `2026-11-10T13:28:32Z` and `CANARY_FINISHED` seq 3136 `13:43:33Z` (`ok: true`, `state: DONE`, `elapsed_s: 900.61`, `ticks: 328`) on a 3,136-event chain, for card T-0147 at fence 120 (merge `05b54d2`). "Never produced a durable record" is true of the live chain only, not globally.

**4.2 Resume / pause / manual launch.** `DISPATCH_RESUMED`, `DISPATCH_PAUSED` and `MANUAL_LAUNCH` each occur **zero** times in the entire live log. A10 has never been authorized. The project is `PAUSED`; the generated `status.md` view records 12 READY cards and 3 active leases, and `HANDOFF.md` recorded 12 READY and 2 active leases at `53871a7`. The two disagree on the rest (210 vs 212 cards; 40 vs 43 DONE), so **the exact current count is unknown** here — no kernel read was performed in this pass. Either reading contradicts "0 active leases / no READY cards". Nothing in the canary results authorizes a resume.

**4.3 Dispatch-owner identity hole.** `src/fleet/owner.py:250` still writes `kernel.record_event("DISPATCH_RESUMED", actor=Actor.human(), ...)` inside `resume_dispatch()` with no verification. Reviewer item 3 is **still open**.

**4.4 Gate duration is unknown.** Measured `SUBMITTED → ORACLE_RESULT` spans: 253 s (T-0189, fail), 411 s (T-0190, pass), 355 s (T-0191, pass), 681 s (T-0196, pass), 239 s (T-0148, fail), 1,371 s (T-0150, pass). Those spans include bundle verification and queue wait, not only the gate subprocess. 1,371 s is larger than the hardcoded `timeout=900` at `src/fleet/merge.py:318`, which is only possible if the gate subprocess itself was shorter than 900 s. **The gate's own duration is unknown.** The correct sentence for the docs is "the gate ran between 12.5 and 15 minutes, unknown", and the phrase "too tight" must not appear.

**4.5 The missing `## Gate budget` section.** The live `pilot/repair-canary-runbook-v1.md` has no such section. `git log --all -S"## Gate budget"` finds **no commit on `main`**; the only hits are the two throwaway commits this pass created inside `tmp/` worktrees (`3e9c6bc`, `0c5bc77`) to carry the proposed replacement. The section therefore never entered tracked history: it exists only in the uncommitted follow-up copy `tmp/review-followups/pilot/repair-canary-runbook-v1.md`. Who removed it and when is **unknown**; the live file's mtime `2026-11-10 00:43:51 +1300` is a filesystem timestamp, not authorship. The replacement text is delivered in the 0004 patch (§7) so the claim does not stay silently absent.

**4.6 T-0190's gate exit code.** Not recorded anywhere. `ok: true` implies `returncode == 0` under `merge.py`, but the value itself is not in the log or the bundle.

## 5. `HANDOFF.md` — proposed correction (not applied)

Path: `HANDOFF.md`. Diff file: `tmp/canary-process/diffs/HANDOFF.md.diff` (verified with `git apply --check`). It changes four places: the 2026-11-10 pointer, the Canary row, the Canary gate history row, and the closing "Current state" paragraph. All three cards stay **path** passes; only T-0191/T-0196 are DoD-6 proofs; T-0189 stays a real failure.

```diff
--- a/HANDOFF.md
+++ b/HANDOFF.md
@@ -7,7 +7,7 @@
 **I1 chain:** Verifies (3630 events)
 **Kernel:** pmk v0.1.0
 
-> **Current evidence:** the 2026-11-01/02 sections below are historical. See **Latest evidence (2026-11-10)** at the end for the current state, the later canary passes (T-0190/T-0191/T-0196) and the A8 activation.
+> **Current evidence:** the 2026-11-01/02 sections below are historical. See **Latest evidence (2026-11-10)** at the end for the current state, the later canary **path** passes (T-0190/T-0191/T-0196; only T-0191 and T-0196 carry `gate_output`) and the A8 activation.
 
 ---
 
@@ -188,12 +188,12 @@
 | Ready queue | 12 cards: T-0192–T-0195, T-0199, T-0200, T-0202–T-0207; T-0201 is VOID |
 | Sentinel | `pmk sentinel` returns `ok: true` with no findings (I1, I3, I4, I5, I6, I7, I8', I13, I14, I15, I16, I17). The red baseline in D-68 is historical, not current |
 | Identity guard | **A8 applied 2026-11-09:** `git config core.hooksPath` returns `.githooks` (D-69) |
-| Canary | **PASS — T-0190, T-0191 and T-0196.** T-0191 (fence 158): `SUBMITTED` seq 3534 → `INTEGRATED` seq 3537 at `c7fcdf3`, bundle `EB-T-0191-158`; T-0196 (fence 159): `SUBMITTED` seq 3554 → `INTEGRATED` seq 3558 at `951d1ee`, bundle `EB-T-0196-159`. Both ran under `kilo-auto`/`kilo`, exited 0, and passed the gate `pytest -q` (exit 0). T-0190 (fence 157, merge `0edc0dc`, bundle `EB-T-0190-157`) was the first pass; T-0189 (fence 156, D-69) remains the historical gate failure. `pmk status` still reports **PAUSED**; no A10 resume is recorded |
-| Canary gate history | The T-0189 gate failed at `tests/test_rules_baseline.py::test_coverage_reports_case_statuses_and_evidence`: case `8.0` referenced `tests/test_transport.py`, absent from base `bcf145c`. `tests/test_transport.py` is tracked at current HEAD (added by `9b3b70d`), and the self-contained base `53871a7` passes the full clean-worktree `pytest -q` (exit 0; `tmp/clean-head-full2.log`). T-0191 and T-0196 also passed their `pytest -q` gates |
+| Canary | **PATH PASS — T-0190, T-0191 and T-0196 reached `DONE` through dispatch; only T-0191 and T-0196 prove DoD-6.** T-0190 (fence 157, base `e302119`): `SUBMITTED` seq 3516 → `ORACLE_RESULT` seq 3518 (`pytest -q`, `ok: true`, no `exit` key) → `INTEGRATED` seq 3520 at `0edc0dc`, bundle `EB-T-0190-157` — **no `gate_output`**. T-0191 (fence 158, base `ce22591`): `SUBMITTED` seq 3534 → `INTEGRATED` seq 3537 at `c7fcdf3`, bundle `EB-T-0191-158`, `gate_output` present (`pytest -q`, exit 0). T-0196 (fence 159, base `9bb0139`): `SUBMITTED` seq 3554 → `INTEGRATED` seq 3558 at `951d1ee`, bundle `EB-T-0196-159`, `gate_output` present (`pytest -q`, exit 0). All three ran under `kilo-auto`/`kilo`; all three merges are authored `umaws-pilot <umaws-pilot@localhost>`. T-0189 (fence 156, base `bcf145c`, D-69) remains a real gate failure — superseded by T-0190, not exonerated. `pmk status` still reports **PAUSED**; no A10 resume is recorded |
+| Canary gate history | The T-0189 gate failed at `tests/test_rules_baseline.py::test_coverage_reports_case_statuses_and_evidence`: case `8.0` referenced `tests/test_transport.py`, absent from base `bcf145c`. `tests/test_transport.py` is tracked at current HEAD (added by `9b3b70d`), and the self-contained base `53871a7` passes the full clean-worktree `pytest -q` (exit 0; `tmp/clean-head-full2.log`). T-0191 and T-0196 also passed their `pytest -q` gates and persisted `gate_output`; T-0190 recorded `ok: true` without an `exit` value and has no `gate_output` |
 | Report copies | `docs/reports/dispatch-failure-root-cause-and-remediation-v1.md` and `pilot/dispatch-failure-root-cause-and-remediation-v1.md` are byte-identical after correction: seq 3212 is **23:10:45**; seq 3225 is **2026-11-08 08:21** and its actor is recorded as **unknown** |
 
 **Isolated base canary (2026-11-10).** Because the live kernel had 12 READY cards and 2 active leases, `pmk canary run` could not satisfy its one-READY/zero-lease preflight there. A separate worktree on branch `canary-base-53871a7` at `53871a7` was used instead; the run did not write to the live kernel. Isolated-base card T-0147 (fence 120, one attempt, `kilo-auto`/`kilo`) wrote `docs/reports/canary-53871a7.md`; `SUBMITTED` seq 3132, gate `ORACLE_RESULT` seq 3133 exit 0, `INTEGRATED` seq 3135 at `05b54d2`, and `CANARY_FINISHED` seq 3136 `ok: true` with state `DONE`. Bundle `EB-T-0147-120` has non-empty gate output, and the merge is authored `umaws-pilot`. This is an isolated base result, not the live-kernel canary, and it does not authorize A10. Details: `docs/reports/canary-53871a7-supervised-2026-11-10.md`.
 
 **Report reconciliation (2026-11-09).** The dispatch-report copies now record T-0146 as `VOID` in F-04 and OQ-04 (`TASK_VOIDED` seq 3315, `2026-11-08T12:40:44Z`; reason `superseded by T-0159 coverage regeneration`). The historical `READY` state is retained as writing-point narrative; T-0146 must not be reused. Their OQ-08 sentinel-red baseline is historical; the current sentinel is green.
 
-**Current state and next action.** A8 is applied (`core.hooksPath=.githooks`); T-0191 and T-0196 passed their gates and integrated at `c7fcdf3` and `951d1ee`, following T-0190 at `0edc0dc`. D-69's T-0189 failure is historical. At HEAD `53871a7`, `pmk status` reports `PAUSED`: 212 cards (155 VOID, 43 DONE, 12 READY, 1 VERIFYING, 1 LEASED), 2 active leases, and a verified chain of 3630 events. T-0208, T-0209 and T-0212 are DONE and integrated; T-0210 is VERIFYING at fence 162 (re-verified at seq 3629); T-0211 is LEASED at fence 163; 12 cards are READY. Next: integrate T-0210, complete T-0211, and drain the READY queue; resuming dispatch remains the operator's A10 decision.
+**Current state and next action.** A8 is applied (`core.hooksPath=.githooks`); T-0190, T-0191 and T-0196 passed the dispatch path and integrated at `0edc0dc`, `c7fcdf3` and `951d1ee`; DoD-6's non-empty `gate_output` is proven by T-0191 and T-0196 only. T-0189's gate failure is superseded, not exonerated. At HEAD `53871a7`, `pmk status` reports `PAUSED`: 212 cards (155 VOID, 43 DONE, 12 READY, 1 VERIFYING, 1 LEASED), 2 active leases, and a verified chain of 3630 events. T-0208, T-0209 and T-0212 are DONE and integrated; T-0210 is VERIFYING at fence 162 (re-verified at seq 3629); T-0211 is LEASED at fence 163; 12 cards are READY. Next: integrate T-0210, complete T-0211, and drain the READY queue; resuming dispatch remains the operator's A10 decision.
```

## 6. `pilot/decisions.md` — proposed erratum (not applied)

Path: `pilot/decisions.md`. Diff file: `tmp/canary-process/diffs/decisions.md.diff` (verified with `git apply --check`). It appends one block after D-74 and rewrites nothing.

```diff
--- a/pilot/decisions.md
+++ b/pilot/decisions.md
@@ -783,3 +783,5 @@
 D-73 | 2026-11-10 | Buffy/Codebuff (executor; drafted for operator ratification at CP-4) | **The launcher-repair completion record is corrected and proposed for acceptance at the recorded scope: DoD-1, DoD-2 and DoD-6 are PASS, and H1/H3/H4/H7 are deferred, not passed.** Current HEAD `a4cbd0a`; repair slices through `09cca85`; H2 fixture split `e302119`; H6 gate-output persistence `ce22591`. Corrected PASS evidence: the clean-base gate recorded exit 0 at `712ca1a` and `09cca85` (DoD-1); `python -m pytest -q --collect-only tests/fleet tests/pmk` exits 0 with 500 tests collected — 268 fleet + 232 pmk — and `python -m pytest -q tests/fleet tests/pmk` exits 0, re-measured on the current tree on 2026-11-10 (DoD-2; logs `tmp/dod2-collection-reverify.log`, `tmp/dod2-combined-reverify.log`, with the earlier `tmp/dod2-collection-20261110-113301.log`); supervised canaries `T-0191` (fence 158, merge `c7fcdf3`, bundle `EB-T-0191-158`) and `T-0196` (fence 159, merge `951d1ee`, bundle `EB-T-0196-159`) both reached `DONE` with non-empty `gate_output` (`pytest -q`, exit 0), so DoD-6 is proven twice. No push was made; the project remains `PAUSED` with 0 active leases and no `READY` cards. **This supersedes D-72's "DoD-2 remains red" sentence and its single-canary account; D-72 stays unratified and its erratum remains the narrower correction.** | Ratify D-72 plus its erratum instead of issuing D-73 — leaves the stale red DoD-2 and the omitted H2/H6 commits in the primary decision record; declare the programme fully complete and close H1/H3/H4/H7 without cards — overclaims unimplemented hardening; hold completion until the H-items land — delays the operator decision while the measured evidence is stable. | **Unknown / not passed:** H1 lease admission is absent (`tests/pmk/test_lease_admission.py` missing) and DoD-5 is therefore partial despite the confirmed 0 leases; H3 `Dispatcher.reconcile()` is unwired; H4 model attribution can emit an empty served-model set, re-proven live at T-0196 seq 3552 (`served_models: []`, `source: none`); H7 has no `%TEMP%/pmk-merge-*` prune awareness. All four are captured as prechecked `PROPOSED` cards `T-0192`–`T-0195`; none was admitted. H5 is partial (env lint exit 0, 7 allowlisted; extension not attempted), and DoD-8 is partial by the same deferrals. CP-3 deletion was never exercised, and CP-4 is this draft — not a ratification. The completion report's §1 figures (chain 3,537, HEAD `c7fcdf3`) predate T-0196 and the independent assessment (chain 3,558, HEAD `951d1ee`); the assessment also found §3 omitted `e302119` and `ce22591` and under-reported the fourth canary. Those documents are not rewritten here. Real-agent behaviour beyond the two supervised canaries, other adapters/providers, concurrent load, and any remote push remain outside this decision. |
 
 D-74 | 2026-11-10 | Buffy/Codebuff (executor; drafted for operator ratification at CP-4) | **H2 is resolved and DoD-2 is resolved by execution, not only by collection: the combined Fleet+PMK suite runs to completion on the current tree.** H2's fixture split landed as `e302119` and remains an ancestor of HEAD `a4cbd0a`; no test module in `tests/fleet` or `tests/pmk` imports a bare `conftest` module (only explanatory docstrings mention the pattern). DoD-2's exact documented command, `.venv/Scripts/python.exe -m pytest -q tests/fleet tests/pmk`, exited `0` on 2026-11-10. Because `pytest.ini` already supplies `-q`, a summary-enabled rerun of the identical selection (`-o addopts="" -q`) reported **513 passed, 0 failed, 0 errors, 0 skipped in 273.37 s (0:04:33)**, with one unrelated Starlette/httpx deprecation warning; the JUnit record confirms 513/0/0/0 (`tests="513" failures="0" errors="0" skipped="0"`; logs `tmp/fleet-pmk-suite.log`, `tmp/fleet-pmk-suite-summary.log`, `tmp/fleet-pmk-suite.xml`). The 500-test figure in D-73 was collect-only, not an execution count. D-72's historical text is preserved unchanged, including its "DoD-2 remains red (combined fleet+pmk collection, H2 unimplemented)" sentence; that sentence is superseded by the 2026-11-10 erratum and by this record, not rewritten. This record adds evidence and does not ratify D-72, D-73, or itself. | Rewrite D-72 in place to remove the stale sentence (destroys the historical decision text the register is meant to preserve); treat the 2026-11-10 erratum as sufficient without an execution record (the erratum proves collection only); keep H2/DoD-2 open (contradicted by the passing combined run at `a4cbd0a`). | H1/H3/H4/H7 remain deferred on `PROPOSED` cards T-0192–T-0195; H5 and DoD-8 remain partial; CP-3 deletion was not exercised; CP-4 has not ratified D-72, D-73, or D-74. Real-agent behaviour beyond the two supervised canaries, other adapters/providers, concurrent load, and any remote push remain outside this decision. |
+
+**Erratum (2026-11-10) — D-69 / D-73 scope, DoD-6 count and live snapshot:** D-69's gate FAIL stands and is not withdrawn: `T-0189`'s gate exited `1` at `tests/test_rules_baseline.py::test_coverage_reports_case_statuses_and_evidence` (seq 3479) on base `bcf145c`; the card was later revoked and voided (`REVOKED` seq 3505, `TASK_VOIDED` seq 3506, reason `Superseded by T-0190`). It is superseded, not exonerated. DoD-6's non-empty `gate_output` is proven **twice**, by `EB-T-0191-158` and `EB-T-0196-159` (both record `pytest -q`, exit 0 inside `gate_output`); `EB-T-0190-157` reached `DONE` at merge `0edc0dc` but its bundle has no `gate_output` key and its `ORACLE_RESULT` (seq 3518) records `ok: true` with no `exit`, so it is a dispatch-path pass, not a third DoD-6 proof. D-73's closing snapshot — "0 active leases and no READY cards" at HEAD `a4cbd0a` — is stale at HEAD `68907fe`: `.pm/views/status.md` records 12 READY cards with 3 active leases, and `HANDOFF.md` recorded 12 READY with 2 active leases at `53871a7`; the two disagree on the rest, so no exact current count is asserted here. This erratum scopes D-69 and D-73 only; it ratifies neither, and D-72, D-73 and D-74 remain drafted for CP-4.
```

**Standing:** D-69 is the recorded FAIL. D-72, D-73 and D-74 are all "drafted for operator ratification at CP-4"; **none is ratified**. Nothing here promotes them. The decision being proposed is **D-73** (completion record: DoD-1, DoD-2, DoD-6 at the recorded scope; H1/H3/H4/H7 deferred), supported by **D-74** as the H2 execution evidence, with the erratum above scoping DoD-6 to two bundles and correcting D-73's stale zero-lease/zero-READY snapshot. Ratifying D-73 would move completion to PASS at that scope; it would not close H1/H3/H4/H7 and would not authorize A10. D-72 stays unratified.

## 7. Reviewer item 5 — gate-wide timeout, delivered as `git format-patch`

**Audit (working tree, tracked files, `tmp/` excluded):** `grep`/`git grep` finds **no** `canary_gate_timeout` anywhere in the live tree. It exists only under `tmp/`:

- `tmp/reviewer-patches/patches-rebased/0004-rebased.patch`
- `tmp/reviewer-patches/patches-filtered/0004-rebased.patch` (second copy, not named in the review item)
- `tmp/review-followups/agents.toml`, `src/fleet/merge.py`, `tests/fleet/test_merge_gate_diagnostics.py`, `pilot/repair-canary-runbook-v1.md`, and `artifacts/patches/0004-fix-fleet-record-gate-evidence-and-prove-import-orig.patch`

**Rename (gate-wide, not canary-only):** `canary_gate_timeout_s` → `gate_timeout_s`; `canary_gate_timeout()` → `gate_timeout()`; module default `DEFAULT_GATE_TIMEOUT_S = 1200`; tests → `test_gate_timeout_reads_fleet_config`, `test_gate_timeout_defaults_to_twenty_minutes`. The setting now budgets every merge gate, and the comment/docs no longer mention canaries or "too tight".

**Delivery:** `tmp/canary-process/0004-gate-timeout-all-gates.patch` — a real `git format-patch` (21,800 bytes, `From 3e9c6bc...` header, subject `fleet: budget every merge gate and record gate evidence`, commit authored `umaws-pilot <umaws-pilot@localhost>` per the pipeline convention). The raw reviewer patch was not a format-patch — it began at `diff --git` with no `From:` line — and it did not apply to `68907fe`: its `src/fleet/merge.py` and `src/fleet/precheck.py` hunks were based on blobs that no longer exist. Those two hunks were reconciled by hand; the other six files applied cleanly.

Patch contents: 9 files, +268/−21 — `agents.toml`, `pilot/cards/canary-replacement-v1.md`, `pilot/repair-canary-runbook-v1.md`, `src/fleet/merge.py`, `src/fleet/precheck.py`, `src/fleet/runenv.py`, `tests/fleet/test_merge_gate_diagnostics.py`, `tests/fleet/test_merge_queue.py`, `tests/fleet/test_worktree_env.py`.

Verification actually run:

- `git apply --check` in a fresh worktree at `68907fe` → clean.
- `git am` of the formatted patch in `tmp/canary-process-verify` → commit `0c5bc77`, clean.
- `py_compile` on the six touched Python files → OK.
- `pytest -q tests/fleet/test_merge_gate_diagnostics.py tests/fleet/test_worktree_env.py tests/fleet/test_merge_queue.py` in that worktree → **22 passed, exit 0** (includes `test_gate_event_records_duration_and_both_heads`).

The runbook replacement carried by the patch (the missing section, corrected wording):

```markdown
## Gate budget

The gate ran between 12.5 and 15 minutes, unknown. The 4-minute figure came from the
failed T-0148 gate; measured SUBMITTED→ORACLE_RESULT spans include queue and bundle
work, so they do not establish the gate subprocess duration. The fleet setting is
`gate_timeout_s = 1200`.
```

The card wording in the same patch says "the gate ran between 12.5 and 15 minutes, unknown" and drops "too tight".

## 8. Files produced (all under `tmp/`)

| Path | What it is |
|---|---|
| `tmp/canary-process/CANARY-PROCESS-DRAFT-2026-11-10.md` | this draft |
| `tmp/canary-process/diffs/HANDOFF.md.diff` | proposed `HANDOFF.md` correction (applies cleanly) |
| `tmp/canary-process/diffs/decisions.md.diff` | proposed `pilot/decisions.md` erratum (applies cleanly) |
| `tmp/canary-process/proposed/HANDOFF.md`, `proposed/decisions.md` | full proposed file contents, for reading |
| `tmp/canary-process/0004-gate-timeout-all-gates.patch` | `git format-patch` of the renamed, rebased 0004 |
| `tmp/canary-process-0004/` | patch worktree, commit `3e9c6bc` |
| `tmp/canary-process-verify/` | clean verification worktree at `68907fe` + `git am` → `0c5bc77` |

No tracked file was modified and no commit was made on `main`.

## 9. Handback

**Proven:** four supervised cards ran in the live kernel at fences 156–159 — T-0189 failed its `pytest -q` gate (exit 1, `tests/test_rules_baseline.py::test_coverage_reports_case_statuses_and_evidence`, case `8.0` referencing `tests/test_transport.py`, absent from base `bcf145c`) and was voided as superseded; T-0190, T-0191 and T-0196 reached `DONE` with merges `0edc0dc`, `c7fcdf3`, `951d1ee`, all authored `umaws-pilot`; DoD-6 is proven by exactly two bundles, `EB-T-0191-158` and `EB-T-0196-159`, because `EB-T-0190-157` has no `gate_output`. **Unknown:** the gate's own duration (spans only; 1,371 s exceeds the 900 s hardcoded timeout, so the subprocess was shorter); any durable record from `pmk canary run` in the live chain (zero `CANARY_*` events; the isolated-base worktree is the only place one exists); who removed the `## Gate budget` section and when (it never entered tracked history); T-0190's numeric gate exit; and the exact current task/lease counts (the status view and `HANDOFF.md` disagree). **Needs your decision:** ratify D-73 at its recorded scope with the appended erratum (D-74 as H2 evidence), or keep it drafted; and clear reviewer item 1 so the two document diffs and the 0004 format-patch may proceed. A10 is not authorized by anything here.

**The one question:** does reviewer item 1 clear the handback — may I apply the `HANDOFF.md` and `pilot/decisions.md` diffs and submit `0004-gate-timeout-all-gates.patch` to the pipeline, or must all three wait until the 17:35/22:49 NZ live-tree edits (and this session's `eb0c226`/`68907fe`) are adjudicated?
