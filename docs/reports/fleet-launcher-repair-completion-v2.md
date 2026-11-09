# Fleet launcher repair — completion report (v2)

**Date:** 2026-11-09
**Executor:** Buffy/Codebuff (implementing the synthesized proposal, executed autonomously under the operator's instruction)
**Branch:** `repair/fleet-launcher-2026-11-09`, fast-forwarded to `main` locally
**Entry base:** `e7d272504f16d6c75a0805b56f01ad5ba7f10be6` (`main`)
**Gated code base:** `09cca8515d6d8dd75f1c412db72a98867e5a6a3d`
**Status:** **repair landed; clean-base gate green; Phase 6 hardening deferred; supervised canary BLOCKED by an operator-only card disposition.** No push. Project remains `PAUSED`.

All claims below are labelled **Confirmed** (measured in this execution), **Derived** (inferred from measurements), or **Unknown**.

## 1. State at entry vs completion

| Measure | Entry | Completion |
|---|---|---|
| `main` HEAD | `e7d2725` (Confirmed) | `09cca85` (Confirmed) |
| Project state | `PAUSED` (Confirmed) | `PAUSED` (Confirmed) |
| Active leases | 0 (Confirmed) | 0 (Confirmed) |
| Chain | verifies, 3,496 events (Confirmed) | verifies, 3,499+ events (Confirmed) |
| Dirty tracked files | 31 files, +2,298/−451 (Confirmed) | 8 files: 4 `.pm/` runtime + 3 CNA files + 1 CNA test (Confirmed) |
| Worktrees | 29 pmk / 41 git at synthesis (Confirmed); 32 pmk / 44 git at re-measure (Confirmed) | 32 pmk / 44 git before the landing; gate worktrees removed (Confirmed) |
| READY cards | T-0189, attempts 1/1 (Confirmed) | T-0189 unchanged (Confirmed) |

The remaining dirty files are exactly the Kernel-written `.pm/` state (never committed, N-02) and the separate CNA work left untouched under A-12. No repair path remains uncommitted.

## 2. Per-phase execution

| Phase | Result | Evidence |
|---|---|---|
| 0 — baseline/drift | **done** | `tmp/entry/<stamp>/`; 60-second concurrent-actor capture showed no second actor |
| 1 — protective capture | **done** | `C:\temp\projects\umaws-repair-archive-2026-11-09`; patch `420b4ff…`, zip `5b98ccd…`; restore proofs in `tmp/capture/README.md` |
| 2 — classification | **done** | gate at `e7d2725` **red**, exactly 1 failure (`test_a_failed_agent_started_write_kills_the_process_and_gives_up_the_lease`, `tests/fleet/test_regressions.py:1583`); combined collection **exit 2**, 9 errors; foreign branch ahead by 1 commit |
| 3 — slice commits | **done** | S1 `c6cc02f`, S2 `e1ed1c3`, S3 `9cb1b98`, S4 `a438901`; focused suites green (S1 after one load flake, see §5) |
| 4 — lease hygiene | **done (skip)** | `active_leases: 0`; no revoke needed; evidence `tmp/rb-4` class |
| 5 — clean-base gate + standing check | **done** | gate **exit 0** at `712ca1a`; `tools/check_clean_base.ps1` committed (`42882d2`, fixed in `59273d3`/`712ca1a`) |
| 6 — hardening H1–H7 | **deferred (verify-first)** | H2 confirmed red; H1/H3/H4/H7 absent; H5 exists and passes; H6 missing; see §4 |
| 7 — worktree census | **done (measure + capture); no deletion** | 32 pmk vs 44 git, difference fully explained; 7 dirty trees archived to `stranded/`; CP-3 not exercised |
| 8 — governance records | **done (drafts)** | erratum in both report copies; D-70/D-71 drafted; census and uncommitted inventory written; sentinel re-measured `ok: true` |
| 9 — whole-system verification | **partial** | final gate **exit 0** at `09cca85`; env lint **exit 0**; pins/fleet **ok**; combined collection still **exit 2** (DoD-2, H2) |
| 10 — land on `main` (CP-1) | **done** | ff-only merge to `09cca85`; no push |
| 11 — supervised canary | **blocked** | T-0189 is the only READY card, attempts 1/1; void is operator-only, so the preflight "exactly one READY card" cannot pass |
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
| H2 conftest collision | `pytest --collect-only tests/fleet tests/pmk` → **exit 2**, 9 errors (bare `from conftest import …`). Confirmed broken. |
| H3 reconcile wiring | `Dispatcher.reconcile()` exists at `src/fleet/dispatcher.py:520`; no startup caller in `src/fleet`. Unwired. |
| H4 model attribution | `provenance.served_models*` can return an empty set and `harness.py:767` writes `sorted(models)`; no non-empty guard. Unimplemented. |
| H5 env lint | `tools/check_subprocess_env.py` exists, 7 allowlisted exceptions, exits 0. Partially satisfied (extension not attempted). |
| H6 gate output in bundles | `_gate_diagnostics()` exists but no `gate_output` field in `src/fleet`; bundle field not confirmed. Unimplemented. |
| H7 prune awareness | `src/pmk/worktrees.py` has `prune`/`archive`, no `%TEMP%/pmk-merge-*` awareness. Unimplemented. |

Deferral reason: these are new work under A-5 and require cards; the project is `PAUSED` and no card was admitted in this programme. Recorded rather than implemented directly.

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

**BLOCKED, not run.** Phase 11's preflight requires `pmk task list --state READY` to be empty before admitting the canary. `T-0189` is still `READY` with `attempts.max = 1` and `attempt = 1`; a claim raises `attempts_exhausted`. The proposal's own disposition is to void it with a recorded successor, but `pmk task void` is operator-only. Creating and admitting a fresh card while T-0189 remains READY would leave two READY cards and violate the preflight. The executor therefore stopped at the documented condition rather than improvising.

Consequence: the merge/identity path with a real agent, the bundle's `gate_output`, and DoD-6 remain unmeasured on the repaired base. This is the single material gap in the programme.

## 7. Definition-of-done matrix

| DoD | Criterion | Measured | Evidence |
|---|---|---|---|
| DoD-1 | Gate green in a detached clean worktree at the recorded base; imports inside | **PASS** — exit 0 at `712ca1a` and `09cca85`; `cna.engine.loop` and `pmk` both inside the worktree | `tmp/clean-base-1794224200.log`, `tmp/clean-base-1794225200.log` |
| DoD-2 | Combined fleet+pmk collection | **FAIL** — exit 2, 9 collection errors (H2) | `tmp/rb-9-collect.log` |
| DoD-3 | Env invariant | **PASS** — exit 0, 7 allowlisted | tool output |
| DoD-4 | Censuses explained; no un-captured deletion | **PASS (measure/capture)** — 32 vs 44, 12-entry difference explained; 7 dirty trees archived; no deletion | `tmp/rb-7-*`, `tmp/capture-pmk-archive.txt` |
| DoD-5 | Lease admission check; `active_leases: 0` | **PARTIAL** — 0 leases confirmed; admission check absent (H1) | `pmk status` |
| DoD-6 | Supervised canary `DONE` with bundle `gate_output` | **BLOCKED** — see §6 | — |
| DoD-7 | Decision drafted; checklist evidence-linked | **PASS (draft)** — D-72 drafted; items 13/15/16 updated | this report, `pilot/decisions.md`, checklist |
| DoD-8 | In-scope items closed or deferred with reason | **PARTIAL** — H1–H7 deferred with measurements; canary blocked | §4, §6 |
| DoD-9 | Decision-before/evidence-after per irreversible action | **PASS except canary/CP-3** — capture, slices, gate, landing evidenced; deletion not attempted | §2, §5 |

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
