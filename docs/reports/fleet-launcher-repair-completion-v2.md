# Fleet launcher repair — completion report (v2)

**Date:** 2026-11-09
**Executor:** Buffy/Codebuff (implementing the synthesized proposal, executed autonomously under the operator's instruction)
**Branch:** `repair/fleet-launcher-2026-11-09`, fast-forwarded to `main` locally
**Entry base:** `e7d272504f16d6c75a0805b56f01ad5ba7f10be6` (`main`)
**Gated code base:** `09cca8515d6d8dd75f1c412db72a98867e5a6a3d`
**Status:** **repair landed; clean-base gate green; H2 conftest split fixed; H6 gate-output persistence is implemented and proven by the fresh supervised canary `T-0191` (`DONE`, merge `c7fcdf3`, bundle `EB-T-0191-158` with non-empty `gate_output`); H1/H3/H4/H7 are captured as prechecked `PROPOSED` cards `T-0192`–`T-0195`; Phase 6 hardening remains deferred.** No push. Project remains `PAUSED`.

All claims below are labelled **Confirmed** (measured in this execution), **Derived** (inferred from measurements), or **Unknown**.

## 1. State at entry vs completion

| Measure | Entry | Completion |
|---|---|---|
| `main` HEAD | `e7d2725` (Confirmed) | `c7fcdf3` after the H6 canary (Confirmed; H6 base `ce22591`) |
| Project state | `PAUSED` (Confirmed) | `PAUSED` (Confirmed) |
| Active leases | 0 (Confirmed) | 0 (Confirmed) |
| Chain | verifies, 3,496 events (Confirmed) | verifies, 3,537 events (Confirmed) |
| Dirty tracked files | 31 files, +2,298/−451 (Confirmed) | 8 pre-canary files: 4 `.pm/` runtime + 3 CNA files + 1 CNA test, plus the 2 canary-record docs (Confirmed) |
| Worktrees | 29 pmk / 41 git at synthesis (Confirmed); 32 pmk / 44 git at re-measure (Confirmed) | 32 pmk / 44 git before the landing; gate worktrees removed (Confirmed) |
| READY cards | T-0189, attempts 1/1 (Confirmed) | T-0189 `VOID`; successors T-0190 and T-0191 `DONE` (Confirmed) |

Before this canary record, the remaining dirty files were exactly the Kernel-written `.pm/` state (never committed, N-02) and the separate CNA work left untouched under A-12; this report and the plan table add the two documentation edits. No repair path remains uncommitted.

## 2. Per-phase execution

| Phase | Result | Evidence |
|---|---|---|
| 0 — baseline/drift | **done** | `tmp/entry/<stamp>/`; 60-second concurrent-actor capture showed no second actor |
| 1 — protective capture | **done** | `C:\temp\projects\umaws-repair-archive-2026-11-09`; patch `420b4ff…`, zip `5b98ccd…`; restore proofs in `tmp/capture/README.md` |
| 2 — classification | **done** | gate at `e7d2725` **red**, exactly 1 failure (`test_a_failed_agent_started_write_kills_the_process_and_gives_up_the_lease`, `tests/fleet/test_regressions.py:1583`); combined collection **exit 2**, 9 errors; foreign branch ahead by 1 commit |
| 3 — slice commits | **done** | S1 `c6cc02f`, S2 `e1ed1c3`, S3 `9cb1b98`, S4 `a438901`; focused suites green (S1 after one load flake, see §5) |
| 4 — lease hygiene | **done (skip)** | `active_leases: 0`; no revoke needed; evidence `tmp/rb-4` class |
| 5 — clean-base gate + standing check | **done** | gate **exit 0** at `712ca1a`; `tools/check_clean_base.ps1` committed (`42882d2`, fixed in `59273d3`/`712ca1a`) |
| 6 — hardening H1–H7 | **partial — H2/H6 fixed; H1/H3/H4/H7 carded** | H2 fixture split landed; H6 persists gate output on success/failure, has a regression test, and is proven by T-0191; H1/H3/H4/H7 are absent from the implementation but captured as prechecked `PROPOSED` cards T-0192–T-0195; H5 exists and passes; see §4 |
| 7 — worktree census | **done (measure + capture); no deletion** | 32 pmk vs 44 git, difference fully explained; 7 dirty trees archived to `stranded/`; CP-3 not exercised |
| 8 — governance records | **done (drafts)** | erratum in both report copies; D-70/D-71 drafted; census and uncommitted inventory written; sentinel re-measured `ok: true` |
| 9 — whole-system verification | **partial** | final gate **exit 0** at `09cca85`; env lint **exit 0**; pins/fleet **ok**; combined collection **exit 0** after the H2 fixture split (DoD-2) |
| 10 — land on `main` (CP-1) | **done** | ff-only merge to `09cca85`; no push |
| 11 — supervised canary | **done** | T-0189 voided with successor T-0190; T-0190 landed the repair. Fresh H6 canary T-0191: fence 158, gate `ok: true` (seq 3535), merged `c7fcdf3`; bundle `EB-T-0191-158` carries non-empty `gate_output` |
| 12 — decision/checklist/handback | **drafted** | D-72 below; checklist items 13/15/16 updated; this report |

## 3. Slice and commit inventory

| Commit | Content | Focused evidence |
|---|---|---|
| `c6cc02f` | S1 fleet core (7 src files, 3 fleet tests), including the `AGENT_STARTED` fail-closed fix | `tmp/rb-3-s1-rerun.log` (green) |
| `e1ed1c3` | S2 Kernel worktree/event lifecycle + test | `tmp/rb-3-s2.log` (green) |
| `9cb1b98` | S3 subprocess-env tool + test | `tmp/rb-3-s3.log` (green) |
| `a438901` | S4 pilot records/config/report edits + this proposal (CP-1 default) | documentary |
| `42882d2` | S5 `tools/check_clean_base.ps1` | gate runs below |
| `59273d3` | S5 fix: resolve repo root after param binding | gate attempt 1 exposed the defect |
| `712ca1a` | S5 fix: verify loaded module files (cna is a namespace package) | gate **exit 0** |
| `f5f414c` | Phase 8 records (census, inventory, erratum, D-70/D-71) | documentary |
| `09cca85` | LF restoration for `pilot/decisions.md` | documentary |

## 4. Phase 6 verify-first measurements (deferred)

| Item | Measured state |
|---|---|
| H1 lease admission | `tests/pmk/test_lease_admission.py` **absent**; no Kernel admission check found. Not implemented. |
| H2 conftest collision | **Resolved** — shared helpers moved to `tests/fleet/_fleet_fixtures.py` and `tests/pmk/_pmk_fixtures.py`; `pytest --collect-only tests/fleet tests/pmk` → **exit 0**. |
| H3 reconcile wiring | `Dispatcher.reconcile()` exists at `src/fleet/dispatcher.py:520`; no startup caller in `src/fleet`. Unwired. |
| H4 model attribution | `provenance.served_models*` can return an empty set and `harness.py:767` writes `sorted(models)`; no non-empty guard. Unimplemented. |
| H5 env lint | `tools/check_subprocess_env.py` exists, 7 allowlisted exceptions, exits 0. Partially satisfied (extension not attempted). |
| H6 gate output in bundles | **Resolved and proven** — `merge.integrate()` builds `gate_output` from `_gate_diagnostics()` and writes it to `Bundle.gate_output` on success, gate failure, and launch failure. Regression: `tests/fleet/test_merge_queue.py::test_gate_output_is_persisted_in_the_bundle` covers both outcomes. Fresh canary T-0191 produced `EB-T-0191-158` with a non-empty `gate_output`; the historical T-0190 bundle remains unchanged. |
| H7 prune awareness | `src/pmk/worktrees.py` has `prune`/`archive`, no `%TEMP%/pmk-merge-*` awareness. Unimplemented. |

Deferral reason: H1/H3/H4/H7 remain new work under A-5; they are now captured as focused `PROPOSED` cards T-0192–T-0195 and prechecked at base `9b92c936`, but none was admitted in this programme. H2 was fixed in the repair; H6 was implemented directly for the operator's requested hardening and is covered by a focused regression.

### Post-report update — prechecked H-item cards (2026-11-10)

The four remaining deferrals were converted to focused cards at hint base `9b92c936` (priorities 10/20/30/40, attempts max 2). All remain `PROPOSED`; none was admitted or dispatched. Each oracle failed at the base because its new focused test file was absent, then passed on the scratch fixture; Kernel precheck reports `canary_valid: true` for all four.

| Card | Item | Write scope | Oracle | Precheck result |
|---|---|---|---|---|
| `T-0192` | H1 — Kernel worktree-lease admission | `src/pmk/api.py`; `tests/pmk/test_lease_admission.py` | `python -m pytest -q tests/pmk/test_lease_admission.py tests/pmk/test_tasks.py` | base exit 4 → scratch exit 0, 36 passed; valid; `tmp/precheck-h1.json`, `tmp/h1.patch` |
| `T-0193` | H3 — Console startup reconciliation | `src/console/app.py`; `tests/fleet/test_reconcile_startup.py` | `python -m pytest -q tests/fleet/test_reconcile_startup.py tests/fleet/test_console_dispatch.py` | base exit 4 → scratch exit 0, 10 passed; valid; `tmp/precheck-h3.json`, `tmp/h3.patch` |
| `T-0194` | H4 — non-empty model attribution | `src/fleet/harness.py`; `tests/fleet/test_model_attribution.py` | `python -m pytest -q tests/fleet/test_model_attribution.py tests/fleet/test_fleet.py tests/fleet/test_provenance.py` | base exit 4 → scratch exit 0, 69 passed; valid; `tmp/precheck-h4.json`, `tmp/h4.patch` |
| `T-0195` | H7 — `%TEMP%/pmk-merge-*` prune discovery | `src/pmk/worktrees.py`; `tests/pmk/test_prune_merge_trees.py` | `python -m pytest -q tests/pmk/test_prune_merge_trees.py tests/pmk/test_worktree_lifecycle.py` | base exit 4 → scratch exit 0, 47 passed; valid; `tmp/precheck-h7.json`, `tmp/h7.patch` |

No source or documentation changes are associated with the cards themselves; they are prechecked backlog items, not completed H-items. The project remains `PAUSED` with 0 active leases, and there are no `READY` cards.

## 5. Deviations (B-18)

1. **D-P1 — archive format.** `tar` could not write through Git Bash (`Cannot execute remote shell`); the untracked set was archived with Python `zipfile`. Restore verified 298/299 files byte-identical (the one mismatch is the live gate log appended after the snapshot).
2. **D-P2 — gate script defects.** PowerShell 5.1 left `$PSScriptRoot` empty in a `param` default, and the guard rejected `cna` because it is a namespace package (`__file__` is `None`). Both fixed forward in separate commits; no amend.
3. **D-P3 — S1 flake.** `test_the_recorded_process_is_stopped_before_the_revoke` failed once under concurrent load (`stage: kill`), then passed three isolated runs and the full `tests/fleet` rerun. Classified as a load flake, not a slice regression.
4. **D-P4 — decisions line endings.** The Phase 8 append rewrote all 767 existing lines as CRLF; commit `09cca85` restores LF. Content unchanged apart from the D-70/D-71 block.
5. **D-P5 — H-item deferral** (§4).
6. **D-P6 — canary blocked** (§6).
7. **D-P7 — CP-1 exercised under the autonomous instruction; CP-3/CP-4 not.** The fast-forward is local only and reversible; deletion was not performed; D-72 is a draft, not a ratification.
8. **D-P8 — `.pm/` runtime state** remains uncommitted by design.
9. **D-P9 — foreign branches** `h1-h4-deletion-safety-v1` and `legacy-launcher-cwd-fallback` remain unmerged; the S1 `legacy.py` change overlaps the latter and is recorded for CP-3 coordination.

## 6. Canary disposition (DoD-6)

**DONE — closed by a fresh H6 canary.** The H6 implementation landed as `ce22591` and a full clean-base gate at that commit exited 0. `T-0191` was created with hint base `ce22591`, prechecked (base oracle exit 1 because the report was absent; scratch oracle exit 0 with `verified`), admitted as the only READY card, and claimed at fence 158 under `kilo-auto`/`kilo`. The agent exited 0, its acceptance oracle passed, and `SUBMITTED` was recorded at seq 3534. The Console Conductor ran the merge gate (`pytest -q`) in the merge worktree; `ORACLE_RESULT` (stage `gate`) was `ok: true`, exit 0; `INTEGRATING` and `INTEGRATED` were recorded at seq 3536 and 3537; the merge landed as `c7fcdf39af7beb41c9dc9dcb829fc27310a8fc7a` (`umaws-pilot <umaws-pilot@localhost>`), and task state is `DONE`.

The bundle `.pm/evidence/EB-T-0191-158/bundle.json` carries non-empty `gate_output` with `cmd: "pytest -q"`, `exit: 0`, `ok: true`, `failed_tests: []`, 17 stdout-tail lines ending at `[100%]`, and an empty stderr tail. The historical T-0190 bundle remains unchanged and lacks `gate_output`; it is superseded for DoD-6, not retrofitted.

Deviation: after submission, the separate `pmk dispatch run` loop was stopped before the gate started, as in the T-0190 run, so the Console Conductor could integrate. No second dispatch or card was admitted; project state remains `PAUSED` with 0 active leases.

## 7. Definition-of-done matrix

| DoD | Criterion | Measured | Evidence |
|---|---|---|---|
| DoD-1 | Gate green in a detached clean worktree at the recorded base; imports inside | **PASS** — exit 0 at `712ca1a` and `09cca85`; `cna.engine.loop` and `pmk` both inside the worktree | `tmp/clean-base-1794224200.log`, `tmp/clean-base-1794225200.log` |
| DoD-2 | Combined fleet+pmk collection | **PASS** — exit 0 after the H2 fixture split | `tmp/combined-collection-only.log` |
| DoD-3 | Env invariant | **PASS** — exit 0, 7 allowlisted | tool output |
| DoD-4 | Censuses explained; no un-captured deletion | **PASS (measure/capture)** — 32 vs 44, 12-entry difference explained; 7 dirty trees archived; no deletion | `tmp/rb-7-*`, `tmp/capture-pmk-archive.txt` |
| DoD-5 | Lease admission check; `active_leases: 0` | **PARTIAL** — 0 leases confirmed; admission check absent (H1) | `pmk status` |
| DoD-6 | Supervised canary `DONE` with bundle `gate_output` | **PASS** — T-0191 `DONE`, merge `c7fcdf3`; bundle `EB-T-0191-158` carries non-empty `gate_output` (`pytest -q`, exit 0); events seq 3534–3537 | `.pm/evidence/EB-T-0191-158/bundle.json`; `tests/fleet/test_merge_queue.py` |
| DoD-7 | Decision drafted; checklist evidence-linked | **PASS (draft)** — D-72 drafted; items 13/15/16 updated | this report, `pilot/decisions.md`, checklist |
| DoD-8 | In-scope items closed or deferred with reason | **PARTIAL** — H1/H3/H4/H7 deferred; H6 implemented and regression-tested; fresh canary T-0191 proves gate-output persistence | §4, §6 |
| DoD-9 | Decision-before/evidence-after per irreversible action | **PASS except CP-3** — capture, slices, gate, landing, canary evidenced; deletion not attempted | §2, §5, §6 |

## 8. Record-only observations

- `pmk sentinel` now reports `ok: true` with no findings; the historical 5 × I6 + 1 × I13 baseline did not reproduce (Confirmed).
- The dirty-tracked set fell from 31 files to 8; the residual is `.pm/` runtime state plus the separate CNA work (Confirmed).
- The two remediation-report copies remain byte-identical after the erratum (Confirmed).
- Model quality, provider billing, and push remain outside this programme (A-7/A-8).

## 9. Self-audit

- No `.pm/` file was hand-edited; the only `.pm/` changes are Kernel-written runtime state.
- No push, no force, no reset, no `git add -A`, no amend, no test weakened to pass.
- Every commit used `umaws-pilot <umaws-pilot@localhost>`.
- CP-3 deletion was not exercised; CP-4 is a draft awaiting operator ratification, not a self-ratified decision.
- The canary was not simulated or described as passing.

## 10. Provenance

Authored by **Buffy/Codebuff** as the executing agent, from measurements taken in this session. It cites commit SHAs, log paths, and ledger counts rather than prose summaries. The operator remains the ratifier for D-72 and the owner of A10.
