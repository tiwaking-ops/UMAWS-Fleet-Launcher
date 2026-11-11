# Fleet Launcher repair — verification report, 2026-11-11

**Date:** 2026-11-11
**Subject:** whether the UMAWS Fleet Launcher repair is complete, measured against `docs/plans/proposal-synthesized-umaws-fleet-launcher-repair-v1.md` (DoD-1…DoD-9, H1–H7, CP-3/CP-4) and against the claims carried in `docs/reports/fleet-launcher-repair-completion-v2.md`
**Author / author_llm:** DeepSeek V4.1 Flash Free — `opencode/deepseek-v4.1-flash-free`
**assessor_llm:** none — first-party report; no independent assessment of this document exists and none is claimed
**Method:** every claim marked *Confirmed* below was re-measured in this session from git, the `pmk` kernel and its projections, the event log, evidence bundles, and fresh tool runs. Figures inherited from earlier reports are labelled as inherited and were not re-derived unless stated.
**State as of:** HEAD `5267cdb` on `main`; 0 behind / 133 ahead of `origin/main`; chain verifies (I1, 3,634 events); `pmk sentinel` `ok=true` with 0 findings; project `PAUSED`; 212 cards (VOID 155, DONE 43, READY 12, VERIFYING 1, LEASED 1); `active_leases: 2`; queue 0; incidents 104; dirty tracked 30 files (+2630/−291); 487 untracked entries; worktrees 35 pmk / 55 git.

**Claim vocabulary.** *Confirmed* — reproduced directly from a named artifact in this session. *Derived* — follows from confirmed items by stated reasoning, not measured directly. *Unknown* — not measured, or not determinable from available evidence.

> **Superseded in part — see the Addendum at the end of this document.** Everything below §1–§12 is preserved unchanged as the measurement taken earlier on 2026-11-11. Later the same day, **H1 landed and both gate fragilities were fixed**; §3 (H1 "Absent"), §2 row 5, and §7.3 fragilities 1–2 are therefore out of date — and §12's fragility entries with them, though its clean-base row remains valid for the base it names. The Addendum records what changed, corrects three of my own earlier claims, and replaces the verdict. The remaining findings — H3/H4/H7 unlanded, the live invalid leases, the uncommitted wave, CP-3/CP-4 open — still stand.

## Verdict

**PARTIAL — dispatch path repaired and proven; programme incomplete.**

The dispatch failure that the plan exists to repair is **fixed and demonstrated on the real path three times** (`T-0190`, `T-0191`, `T-0196` all reached `DONE` through a gated merge, and two of those bundles carry non-empty `gate_output`). Two of the seven hardening items (H2, H6) are landed and proven. The gate passes on the current working tree.

The programme is nevertheless **not complete**, and cannot honestly be reported as complete:

1. Four hardening items — **H1, H3, H4, H7** — are unlanded. Their cards (`T-0192`–`T-0195`) are `READY`, prechecked, and have never been admitted.
2. The **H1 defect is live in project state**, not merely in code: two leases exist right now in exactly the shape H1 is meant to reject (§4).
3. A **second, uncommitted wave** of changes (single-owner dispatch lock, canary runner, CLI/Console/Harness hardening) sits in the working tree and is not atomic with HEAD (§5).
4. **No definition-of-done row describes the current tree.** `DoD-1` now passes at `5267cdb` (§7.2), but that base predates the four H items and the uncommitted wave, so the clean-base gate must be re-run after they land. Read against the plan's own closure table, 7 of 9 DoD rows are still `_pending`.
5. **CP-3** (worktree deletion) and **CP-4** (canary ratification) remain unexercised, and the reviewer's six-item hardening track (§6) is largely open.

## 1. Scope of this report

This report answers two questions asked in chat:

- *Is the UMAWS Fleet Launcher repaired now?*
- *What is required to complete the repair?*

It is a verification record, not a repair: no source, kernel state, card, or decision was changed by producing it. It reports only what the event log, the files, and fresh runs prove, and writes `Unknown` where something was not measured.

## 2. Confirmed results — what is actually repaired

| # | Claim | Evidence | Status |
|---|---|---|---|
| 1 | Dispatch → gate → merge → `DONE` works end-to-end on the real kernel path | `T-0190`, `T-0191` (merge `c7fcdf3`), `T-0196` (merge `951d1ee`) all recorded `DONE`; both merge commits present in `git log --all` | Confirmed |
| 2 | H6 (merge gate output persisted in the bundle) is fixed | `ce22591` *fix(fleet): persist merge gate output in evidence bundles*; `EB-T-0196-159/bundle.json` carries `gate_output` with `cmd: pytest -q`, `exit: 0`, `ok: true`, populated `stdout_tail` | Confirmed |
| 3 | H6 fix is proven against the pre-fix shape, same task family | `EB-T-0191-158` and `EB-T-0196-159` both carry a non-empty `gate_output`; the earlier `EB-T-0190-157` bundle has no `gate_output` key value at all | Confirmed |
| 4 | H2 (combined `tests/fleet` + `tests/pmk` collection) is fixed | `e302119` *test(fleet): split shared fixtures for combined collection*; plan records DoD-2 `PASS` | Confirmed |
| 5 | The full gate is green **on the current working tree** | `tmp/gate-head-5267cdb.xml`: `<testsuite tests="1288" errors="0" failures="0" skipped="1" time="393.197">`, timestamp `2026-11-11T09:37:00+13:00`; `tmp/gate-head-5267cdb.txt` is the console log | Confirmed |
| 6 | The event chain is intact | `pmk status`: `I1 chain verifies (3634 events)` at the closing measurement (3,632 at first measurement in this session; the gate run itself appended events) | Confirmed |
| 7 | Sentinel reports no findings | `pmk sentinel` → `ok: true`, `findings: []`, checked `I1, I3, I4, I5, I6, I7, I8', I13, I14, I15, I16, I17` | Confirmed |
| 8 | Fleet configuration is admissible | `pmk fleet check` `ok: true` (18 profiles, cap 10); `pmk pins check` `ok: true` (2 checked) | Confirmed |
| 9 | HEAD is self-consistent | `src/fleet/dispatcher.py` at HEAD contains no `owner` reference and HEAD has no `src/fleet/owner.py` — the committed tree does not depend on untracked modules | Confirmed |
| 10 | The clean-base gate (DoD-1) passes at HEAD | `tools/check_clean_base.ps1` → `clean-base gate exit=0 sha=5267cdb467957c0173663dcd41e892c5b8363b9c`, after proving `cna`/`pmk` resolve inside the detached worktree (§7.2) | Confirmed |

**Derived.** The repair that mattered — the launcher can dispatch a card, run a real gate in the merge worktree, record the evidence, merge, and close the card — is working. That is a genuine, demonstrated outcome, not a documentation claim.

## 3. Open hardening items (H1, H3, H4, H7)

| Item | Plan requirement (abbreviated) | Measurement in this session | Status |
|---|---|---|---|
| **H1** — Kernel lease admission | Reject a lease whose `worktree` resolves to the repo root; reject a grant with no `pid`/`expires_at` while project ≠ `RUNNING`; test `tests/pmk/test_lease_admission.py` | `tests/pmk/test_lease_admission.py` **does not exist** (`Test-Path` → `False`) | **Absent** — Confirmed |
| **H3** — reconcile at Console startup | Call `Dispatcher.reconcile()` exactly once in `Console.__init__` | `def reconcile` at `src/fleet/dispatcher.py:524`; the only call sites anywhere are `tests/fleet/test_fleet.py:588` and `:602` — **no production caller** | **Absent** — Confirmed |
| **H4** — non-empty model attribution | Every `MODEL_SERVED` payload must carry a non-empty model list with a non-`none` source | `src/fleet/harness.py:776` emits `"served_models": sorted(models)` with **no non-empty guard** in the surrounding block | **Absent** — Confirmed |
| **H7** — prune awareness of `%TEMP%\pmk-merge-*` | Read-only discovery, dry-run default, report under `merge_trees` | `src/pmk/worktrees.py` has **0** occurrences of `pmk-merge`; the string appears only at `src/fleet/merge.py:255` and `:366` | **Absent** — Confirmed |

All four have `READY` cards, prechecked at base `9b92c936`, and never admitted:

| Card | Item | Priority |
|---|---|---|
| `T-0192` | H1 — Kernel lease admission | 10 |
| `T-0193` | H3 — reconcile during Console startup | 20 |
| `T-0194` | H4 — non-empty model attribution | 30 |
| `T-0195` | H7 — prune reports `%TEMP%/pmk-merge-*` | 40 |

**Derived.** `DoD-5` cannot pass without H1, because its stated oracle *is* `tests/pmk/test_lease_admission.py` plus `active_leases: 0` — and both halves currently fail (§4). H3/H4/H7 are not gated by a DoD row of their own, but the plan requires each to land via a card and reach `DONE`.

## 4. Live finding — the H1 hole is open in project state

Two leases are currently held in precisely the shape H1 exists to reject:

| Task | Fence | Holder / profile | `worktree` | `pid` | `expires_at` | Granted |
|---|---|---|---|---|---|---|
| `T-0210` | 162 | `buffy` / `buffy` | `"."` | `None` | `""` | 2026-11-10T07:53:15Z |
| `T-0211` | 163 | `buffy` / `buffy` | `"."` | `None` | `""` | 2026-11-10T09:01:23Z |

Source: `.pm/views/status.md:29-32` (the active-lease table) cross-checked against the reconstructed lease records in kernel state.

| Observation | Status |
|---|---|
| Both leases carry a repo-root worktree (`"."`) | Confirmed |
| Both carry no `pid` and no `expires_at` | Confirmed |
| They are held while the project is `PAUSED` | Confirmed |
| `pmk status` still reports `active_leases: 2` | Confirmed |
| Nothing released them during this session | Confirmed |

**Derived.** Two consequences follow, and they are the reason this report does not call the repair complete:

1. `DoD-5`'s second condition (`active_leases: 0`) is false, and will stay false until these are revoked under human authority.
2. The defect H1 describes is not hypothetical — the state already contains invalid leases produced through the unguarded path. Any admission check added later must **not** retroactively rewrite these records (the plan forbids that), so they need explicit operator revocation, not a code fix.

## 5. The uncommitted second wave

The working tree carries a substantial body of work that is not in HEAD and that is **coupled**: committing part of it breaks the tree.

| Artifact | Path | State |
|---|---|---|
| Single-owner dispatch lock | `src/fleet/owner.py` | untracked (new) |
| Canary runner | `src/fleet/canary.py` | untracked (new) |
| Coupled caller | `src/fleet/dispatcher.py:36` → `from .owner import owner_status` | modified |
| CLI hardening | `src/pmk/cli.py` | modified |
| Console hardening | `src/console/app.py`, `src/console/static/index.html` | modified |
| Harness hardening | `src/fleet/harness.py` | modified |
| Coverage for the new modules | `tests/fleet/test_dispatch_owner.py`, `tests/fleet/test_canary_runner.py` | present |
| Event/ledger bookkeeping | `src/pmk/events.py`, `.pm/events/2026-11-07.jsonl`, `.pm/views/*` | modified |

Scale: **30 tracked files modified, +2630/−291**, plus 487 untracked entries.

**Derived — atomicity risk.** `dispatcher.py` in the working tree imports `src/fleet/owner.py`, which is untracked. HEAD is clean of that dependency (item 9 of §2), so the wave must land **as a unit**: `owner.py` + `canary.py` + `dispatcher.py` + `cli.py` + `console/app.py` + `harness.py` + the two new test modules, or not at all. A partial commit — for example committing `dispatcher.py` alone — produces an `ImportError` at HEAD. This is a packaging hazard for whoever commits, not a defect in the code.

**Unknown.** Whether the wave is intended for this repair at all. It implements single-owner dispatch and a canary runner, which map onto the plan's Phase 11 supervision intent, but no card in the ledger was found admitting it, and the plan does not name `owner.py`/`canary.py`.

## 6. The reviewer's six-item track (incident seq 3630)

Incident seq 3630 (`2026-11-10T10:17:19Z`, subject `T-0211`, actor `kernel`, severity `info`) relays a reviewer message with six required items. Status of each, measured:

| # | Reviewer requirement | Measurement | Status |
|---|---|---|---|
| 1 | Identify which session edited the live tree today; no further live edits; do not commit group A | not determinable from the log alone | **Unknown** |
| 2 | One shared `require_human_authority()` helper covering void, pins record, class-K `queue_decide`, `resume_dispatch`, profile enable/disable/cooling, `cmd_agent_swap`, `MANUAL_LAUNCH`; requires `PMK_ACTOR=human:<name>` plus an interactive TTY; error text must not name what to set | `require_human_authority` occurs **0** times in `src/` | **Absent** |
| 3 | `resume_dispatch` / `--resume` use that helper; `CANARY_STARTED`/`CANARY_FINISHED` record a verified human identity or refuse; propose one canary at a time | both events **exist** (`src/fleet/canary.py:93,134`) but are emitted with `actor=Actor.kernel()`, so they record the kernel rather than a verified human; `pmk resume` (`src/pmk/cli.py:353-357`) deletes the stop file with **no authority check at all** | **Partial / non-compliant** |
| 4 | Console `/api/queue/decide` fails for class K under the kernel patch; propose a fix without changing the Console's no-auth design | not measured in this session | **Unknown** |
| 5 | Deliver `0004-rebased.patch` as `git format-patch`; rename `canary_gate_timeout_s`; docs must say the gate ran between 12.5 and 15 minutes, unknown; remove the phrase "too tight" | patches `0001`–`0003` in `tmp/reviewer-patches/patches-rebased/` **are** genuine `git format-patch` output (`From 8943a595…`, `Subject: [PATCH 1/4]`), but `0004-rebased.patch` is still a **raw diff** (`diff --git …`, no `From <sha>` header); `canary_gate_timeout_s` has **0** occurrences in the live tree — it exists only inside that patch and `tmp/review-followups/` | **Partial — rename and 0004 conversion still open** |
| 6 | Stop calling the checker the reviewer's tool | documentation convention; not machine-checkable | **Unknown** |

Authority today is **advisory and scattered**, not centralised:

| Location | What it does | Status |
|---|---|---|
| `src/pmk/api.py:408-426` | policy check for `task_void`; its own docstring says the check is "*advisory*, not a security boundary — any caller with access to the Kernel can pass `actor=Actor.human()`" | Confirmed |
| `src/pmk/cli.py:109-115` | parallel `task_void` authority handling in the CLI | Confirmed |
| `src/pmk/cli.py:353-357` | `pmk resume` deletes the stop file and reports `stopped: False` — **no actor check of any kind** | Confirmed |
| `src/pmk/cli.py:280, 577, 590, 605, 746` | hard-coded `Actor.human()` at `PINS_CHECKED`, `PROFILE_ENABLED`, `PROFILE_DISABLED`, `PROFILE_COOLING`, `AGENT_RESUMED` | Confirmed |
| `src/console/app.py:261, 265, 269, 456` | hard-coded `Actor.human()` at the same profile events plus `MANUAL_LAUNCH` | Confirmed |

**Derived.** Item 2 is absent and item 3 is partial: the canary events exist but attribute the kernel, and `pmk resume` has no check at all. Until a single helper exists, the project's human-authority boundary is a convention that any Kernel caller can bypass by constructing `Actor.human()` — the code says so itself at `api.py:408-410`.

## 7. Gate evidence and gate fragility

### 7.1 Dirty-tree gate (green)

| Field | Value |
|---|---|
| Command | `python -m pytest -q` on the working tree at HEAD `5267cdb` |
| Result | **1288 tests, 0 failures, 0 errors, 1 skipped** in 393.197 s |
| Artifact | `tmp/gate-head-5267cdb.xml` (JUnit), `tmp/gate-head-5267cdb.txt` (console) |
| Timestamp | 2026-11-11T09:37:00+13:00 |
| Caveat | this is **not** DoD-1 evidence — DoD-1 requires a detached clean worktree at the recorded base with imports resolving inside it (B-14/N-05 forbid presenting a dirty-tree run as clean-base proof) |

### 7.2 Clean-base gate (DoD-1)

| Field | Value |
|---|---|
| Tool | `tools/check_clean_base.ps1` (detached worktree at HEAD, `PYTHONPATH` pinned, import-resolution asserted before pytest) |
| Invocation | `tools\check_clean_base.ps1 -Python "C:\temp\projects\testproject1\.venv\Scripts\python.exe"` with `C:\Program Files\Git\usr\bin` prepended to `PATH` |
| Worktree | `C:\temp\projects\umaws-gate-20261111-094825` at `5267cdb` |
| Import resolution | **passed** — `cna.engine.loop` → `…\umaws-gate-20261111-094825\src\cna\engine\loop.py`; `pmk` → `…\umaws-gate-20261111-094825\src\pmk\__init__.py` |
| pytest | **PASS** — script reported `clean-base gate exit=0 sha=5267cdb467957c0173663dcd41e892c5b8363b9c`; progress reached 100 % with no `F`/`E` lines |
| Result line | `clean-base gate exit=0 sha=5267cdb467957c0173663dcd41e892c5b8363b9c` |
| Worktree disposition | removed on success — `C:\temp\projects\umaws-gate-20261111-094825` no longer exists; `git worktree list` back to 55 entries |
| Evidence | `tmp/clean-base-20261111-094825.log`; runner transcript `tmp/clean-base-verify-20261111b.log` |
| DoD-1 status | **PASS at `5267cdb`** — the plan's expected evidence filename is `tmp\rb-9-final-gate.log`; the actual artifact is the `tmp/clean-base-*` pair |

**Evidence-completeness caveat.** The clean-base log is 2,756 bytes and records progress plus `[100%]` but **no pytest summary line** (no `passed`/`skipped` counts), because of how `pytest -q *> $log` captures output in this script. The gate's verdict is therefore carried by the script's own `exit=0` line and the absence of failure markers, not by a test-count summary. The dirty-tree run (§7.1) supplies the counts (1,288 tests, 1 skipped). Anyone auditing DoD-1 should read both artifacts together.

**Correction discipline.** An earlier draft of this section asserted `clean-base gate exit=0 sha=5267cdb` before that line existed. That draft assertion was withdrawn and then re-established only once the run printed its own result line — a clean-base pass is evidence only when the run says so, not when the report expects it.

### 7.3 Three gate fragilities found while producing this evidence

These are properties of the **gate and its tooling**, not of the code under test. They matter because they make a red gate ambiguous.

| # | Fragility | Evidence | Status |
|---|---|---|---|
| 1 | `tests/fleet/test_identity_guard.py::test_pre_commit_hook_logs_without_blocking` invokes a bare `sh` (`subprocess.run(["sh", str(hook)], …)`, no `shell=True`), so it fails with `[WinError 2]` on Windows whenever `C:\Program Files\Git\usr\bin` is not on `PATH` — a PATH property, not a code property | reproduced in this session before `PATH` was pinned; `tools/check_clean_base.ps1` sets `PYTHONPATH` but **not** `PATH` | Confirmed |
| 2 | `tests/fleet/test_conductor_leases.py::test_every_recorded_process_is_stopped_before_the_revoke` failed under concurrent load — `assert results[0]["reaped"] is True` → `assert False is True` at `tests/fleet/test_conductor_leases.py:398` — then passed on the quiet run | `tmp/gate-shpath-20261111-093515.log`; same failure class as deviation D-P3 | Confirmed |
| 3 | `tools/check_clean_base.ps1 -Python <relative path>` cannot work: the script `Push-Location`s into the gate worktree before invoking the interpreter, so a relative `-Python` resolves inside the gate tree and fails with *"The module '.venv' could not be loaded"*. Only an absolute path is usable | first invocation failed exactly this way in this session (`tmp/clean-base-verify-20261111.log`); second invocation with an absolute path succeeded | Confirmed — **newly found, not previously recorded** |

Fragility 3 is a small, self-contained tooling defect with an obvious fix: resolve `-Python` against `$RepoRoot` before the `Push-Location`, or document that the parameter must be absolute.

## 8. Corrections to `fleet-launcher-repair-completion-v2.md`

The v2 report was accurate at its own snapshot; the following figures are now superseded. Its qualitative conclusions (dispatch repaired, H6 closed) still hold.

| v2 claim | v2 value | Measured 2026-11-11 | Note |
|---|---|---|---|
| `main` HEAD | `c7fcdf3` | `5267cdb` | 5 commits later: `951d1ee`, `eb0c226`, `68907fe`, `91e5e14`, `5267cdb` |
| Chain length | 3,537 events | 3,634 events | grew with the later waves |
| Dirty tracked files | "fell from 31 files to 8" | **30 files**, +2630/−291 | the residual is not just `.pm/` runtime state and CNA work; it includes `src/pmk/cli.py`, `src/console/app.py`, `src/fleet/dispatcher.py`, `src/fleet/harness.py` and six test modules |
| Active leases | 0 | **2** (`T-0210`, `T-0211`) | both invalid in the H1 shape (§4) |
| Worktrees | 32 pmk / 44 git | 35 pmk / 55 git (56 while the transient gate worktree existed) | census still unreconciled — DoD-4 remains open |
| "No repair path remains uncommitted" | asserted | **contradicted** | an uncommitted wave exists and is coupled (§5) |

Correction on `DoD-4`: the v2 report marked it `PASS (measure/capture)` on a 32-vs-44 census with a 12-entry difference explained. That census has since moved to 35 vs 55 and was **not** re-reconciled in this session. DoD-4 should be treated as **open pending a fresh census**, not as closed.

## 9. What is required to complete the repair

Ordered, with the smallest defensible first step.

| # | Requirement | Why it is required | Blocking? |
|---|---|---|---|
| 1 | Revoke the two invalid leases (`T-0210` fence 162, `T-0211` fence 163) under explicit human authority | they are invalid under H1's own rule; `DoD-5` requires `active_leases: 0`; the plan forbids retroactive rewriting, so revocation is the only correct remedy | **yes** |
| 2 | Decide and record what the uncommitted wave is (admit it as a card, or park it) | it is coupled and cannot be partially committed; leaving it undecided keeps HEAD and the working tree divergent | **yes** |
| 3 | Commit the wave atomically, or revert it | a partial commit breaks imports at HEAD (§5) | **yes**, once #2 is decided |
| 4 | Admit and land `T-0192` (H1 — lease admission) with `tests/pmk/test_lease_admission.py` | closes the defect that produced §4; closes `DoD-5` | **yes** for "complete" |
| 5 | Admit and land `T-0193` (H3 — reconcile at Console startup) | restart currently neither adopts live workers nor marks lost ones | yes for "complete" |
| 6 | Admit and land `T-0194` (H4 — non-empty model attribution) | `MODEL_SERVED` can carry `served_models: []` today | yes for "complete" |
| 7 | Admit and land `T-0195` (H7 — prune reports `%TEMP%/pmk-merge-*`) | prune currently cannot see merge scratch trees | yes for "complete" |
| 8 | Re-run the full gate and the clean-base gate at the post-landing base | `DoD-1` is per-base; `5267cdb` no longer describes the tree after #3–#7 | **yes** |
| 9 | Re-run the pmk-vs-git worktree census | `DoD-4` is open and the counts have drifted 32/44 → 35/55 | **yes** for DoD-4 |
| 10 | Deliver the reviewer's items 2–5: one `require_human_authority()` helper, its use in `resume_dispatch`/canary events, a class-K Console fix proposal, and the `0004` patch as `git format-patch` with the timeout rename | the human-authority boundary is currently bypassable by construction (§6) | **yes** for the reviewer track |
| 11 | Exercise CP-3 (worktree deletion) and CP-4 (canary ratification) with the operator | both are unexercised; neither can be self-certified by an agent | **yes** for programme closure |
| 12 | Fix gate fragility 3 (`-Python` relative path); decide a policy for fragilities 1 and 2 | otherwise a red gate cannot be distinguished from an environment defect | recommended |
| 13 | Update `HANDOFF.md` (its latest-evidence section was measured at `53871a7` and is now 4 commits stale) and the plan's `DoD-1` evidence pointer | stale navigation documents cause repeated re-measurement | recommended |

### Ordered minimal path to "complete"

Steps 1 → 2 → 3 → 4 are the minimum that changes the verdict from `PARTIAL` to something stronger. Steps 5–7 are the remainder of the hardening set. Steps 8–9 re-establish evidence at the new base. Steps 10–11 are the governance remainder.

## 10. Unknowns — not measured or not determinable

| Item | Why unknown |
|---|---|
| Which session made the live-tree edits the reviewer asked about (item 1) | the event log records events, not editor sessions; no session-to-file mapping was found |
| Whether the uncommitted wave was ever admitted as work | no card in the ledger references `owner.py` or `canary.py` |
| Console `/api/queue/decide` class-K behaviour (item 4) | not exercised in this session |
| The pmk-vs-git worktree difference (20 entries at the closing measurement: 35 vs 55) | not re-reconciled; includes the foreign `H1-H4-*` / `gate-*` trees the plan says to protect |
| Whether `T-0212` (`DONE`, fence 164) changed the repair surface | recorded `DONE` after the last gate run but not inspected in this session |
| Push state of `origin/main` | measured as 0 behind / 133 ahead, but no push was performed in this session |

## 11. Recommendation

**Report only.** This document records the state; it does not change it.

- The repair should **not** be declared complete. `PARTIAL — dispatch path repaired and proven; programme incomplete` is the defensible verdict.
- A decision record is **warranted** — the next free id is likely `D-75`, covering (a) lease revocation for `T-0210`/`T-0211`, (b) disposition of the uncommitted wave, and (c) the `PARTIAL` verdict itself — but it is **not written here**. Decision records belong in `pilot/decisions.md`, ratification belongs at CP-4, and drafting it is an operator choice.
- `HANDOFF.md` and the plan's `DoD-1` evidence pointer should be reconciled to this report once the operator accepts it.

## 12. Evidence index

| Artifact | Path | What it proves |
|---|---|---|
| Working-tree gate (JUnit + console) | `tmp/gate-head-5267cdb.xml`, `tmp/gate-head-5267cdb.txt` | 1288 tests / 0 failures / 1 skip at HEAD `5267cdb`, dirty tree |
| Clean-base gate (pytest log + runner transcript) | `tmp/clean-base-20261111-094825.log`, `tmp/clean-base-verify-20261111b.log` | DoD-1 **PASS**: `exit=0` at `5267cdb` in a detached worktree, with `cna`/`pmk` imports resolving inside that worktree |
| Failed clean-base invocation | `tmp/clean-base-verify-20261111.log` | gate fragility 3 (relative `-Python` unresolvable) |
| Concurrency flake | `tmp/gate-shpath-20261111-093515.log` | gate fragility 2 |
| H6 proof (post-fix) | `.pm/evidence/EB-T-0191-158/bundle.json`, `.pm/evidence/EB-T-0196-159/bundle.json` | non-empty `gate_output`, `ok: true`, `exit: 0` |
| H6 pre-fix shape | `.pm/evidence/EB-T-0190-157/bundle.json` | `gate_output` absent before `ce22591` |
| Live invalid leases | `.pm/views/status.md:29-32` | `T-0210` fence 162, `T-0211` fence 163, both `worktree: "."`, no pid, no expiry |
| Reviewer requirements | event `seq 3630`, `2026-11-10T10:17:19Z`, subject `T-0211` | the six-item hardening track quoted in §6 |
| Plan definition-of-done | `docs/plans/proposal-synthesized-umaws-fleet-launcher-repair-v1.md:742-751` | DoD-1…DoD-9 with DoD-2/DoD-6 `PASS`, the rest `_pending` |
| Prior report under correction | `docs/reports/fleet-launcher-repair-completion-v2.md` | the superseded figures in §8 |
| Subject modules | `src/fleet/owner.py`, `src/fleet/canary.py`, `src/pmk/cli.py`, `src/console/app.py`, `src/fleet/harness.py`, `src/fleet/dispatcher.py` | the uncommitted wave in §5 |
| Gate tool | `tools/check_clean_base.ps1` | the DoD-1 implementation and fragilities 1/3 |

---

**Author:** DeepSeek V4.1 Flash Free — `opencode/deepseek-v4.1-flash-free`. Authored this report; no independent assessment of it exists, and no `assessor_llm` is claimed.
**Status of this document:** advisory verification record. It grants no authority, ratifies no decision, and promotes nothing. Claims marked *Unknown* remain unknown until measured.
**Storage:** stored uncommitted in `docs/reports/`. Committing it, referencing it from `HANDOFF.md`, or converting it into a decision record are operator decisions.

---

# Addendum — 2026-11-11 (later the same day)

**Date:** 2026-11-11
**Author / author_llm:** DeepSeek V4.1 Flash Free — `opencode/deepseek-v4.1-flash-free`
**assessor_llm:** none — still first-party; no independent assessment of this document exists and none is claimed
**Method:** as in the header above. Every claim marked *Confirmed* below was reproduced in this session from the files, the kernel, the event log, and fresh test runs.
**State as of this addendum:** HEAD `5267cdb` on `main` (0 behind / 133 ahead of `origin/main`); chain verifies (I1, 3,634 events); project `PAUSED`; `active_leases: 2`; 35 pmk worktrees; working tree still dirty and **uncommitted**.

## A.0 Addendum verdict

**PARTIAL — engine hardening advanced; programme incomplete.**

What changed since the measurement above:

| Item | Before | Now |
|---|---|---|
| **H1** — Kernel lease admission | Absent — `tests/pmk/test_lease_admission.py` missing | **Landed and proven**; oracle passes |
| **Gate fragility 1** — bare `sh`/PATH | Present | **Fixed**; passes with Git's `usr\bin` off `PATH` |
| **Gate fragility 2** — reap-test load flake | Present | **Fixed at the cause**; 12/12 under the load that produced 2/12 |
| **H5** — env lint coverage | Partial (tool exits 0; extension not attempted) | Unchanged — partial |
| **H3, H4, H7** | Absent | Absent — unchanged |
| Authority gate, uncommitted wave, CP-3, CP-4 | Open | Open — unchanged |

**3 of 7 hardening items are now landed and proven** (H1, H2, H6); **H5 is partial**; **H3, H4 and H7 are absent**. The programme is still not complete, and the two decisions that unblock the most are named in §A.9.

## A.1 H1 — Kernel lease admission (landed)

| File | Confirmed change |
|---|---|
| `src/pmk/api.py` | `claim()` gains an `expires_at` parameter and an admission block for **worktree-bearing** grants. A worktree resolving to the repository root raises `KernelError("invalid_worktree")`. A grant that would carry no `pid` or no `expires_at` while `project_state() != "RUNNING"` raises `KernelError("lease_incomplete")`. Each refusal appends a `LEASE_REFUSED` event **before** raising; nothing is silently corrected (N-15). Historical leases are not revisited. |
| `src/pmk/events.py` | `"LEASE_REFUSED"` added to the known-event tuple. Before this, the chain had **0** occurrences of that type. |
| `tests/pmk/test_lease_admission.py` | **New.** Covers the repo-root refusal (absolute and `"."`), the three `lease_incomplete` shapes, the legitimate `pid` + future `expires_at` grant while not `RUNNING`, a `RUNNING` grant, and the unchanged worktree-less claim. |

**Derived — production dispatch is unaffected.** `src/fleet/harness.py:441` claims *without* a worktree (`claim(task.id, holder=…, agent=…, role=…)`) and creates the tree afterwards at `spawn_mod.create_worktree`. H1 therefore governs direct `--worktree` grants — `pmk claim --worktree`, and test setup — not the ordinary dispatch path.

**Evidence.**

| Check | Command | Result |
|---|---|---|
| T-0192 oracle | `python -m pytest -q tests/pmk/test_lease_admission.py tests/pmk/test_tasks.py` | **35 passed, exit 0** |
| Full suite | `python -m pytest -q` | **exit 0**, 1 skipped, 1292 collected (`tmp/gate-h1-frag-20261111.log`) |
| Fleet + PMK | `python -m pytest -q tests/pmk tests/fleet -o addopts="" -q` | **517 passed, 1 skipped** in 284.20 s |
| Full-suite collection | `python -m pytest -o addopts="" --collect-only -q` | 1292 tests collected |

**Confirmed — the live defect is still present in state.** The two leases that motivated H1 are unchanged: `T-0210` fence 162 and `T-0211` fence 163, both with `worktree: "."`, no `pid`, no `expires_at`. H1 refuses *future* grants of that shape; it deliberately does not rewrite them. They still falsify `DoD-5`'s `active_leases: 0` condition.

## A.2 The two gate fragilities (fixed)

### A.2.1 Fragility 1 — `sh` lookup

`tests/fleet/test_identity_guard.py` invoked a bare `["sh", str(hook)]`, so the test measured the caller's `PATH`, not the hook. It now resolves the shell deterministically: `shutil.which("sh")` → Git's own `usr/bin/sh.exe` (derived from `git --exec-path` and `shutil.which("git")`) → the two standard Program Files locations → a loud `RuntimeError` explaining what is missing.

**Confirmed:** 4 passed with `Git\usr\bin` removed from `PATH`.

### A.2.2 Fragility 2 — reap-test load flake

Root cause, in `src/pmk/plat.py`: `kill_tree()` reported **failure** whenever `taskkill` returned non-zero, even when the target process was already gone — and `OpenProcess` failures were read as "process gone", so a single transient probe could decide a lease's fate under load.

| Change | Effect |
|---|---|
| `kill_tree()` now returns `(True, …)` when the identified process is **not running** on return, including a non-zero `taskkill` that raced with the process's own exit | "the goal is met" is no longer reported as an error |
| New `_liveness(pid, seconds=2.0)` polls before concluding "not running" | a single failed `OpenProcess` probe cannot be read as "gone" |
| Explicit `creation_time is None` guard before any kill | rule 17 preserved: no identity ⇒ never kill, and never claim "gone" |

**Rule 17 is preserved and slightly strengthened** — a live process whose creation time does not match still returns `(False, "…refused to kill")`, and a missing creation time still refuses. Existing assertions in `tests/pmk/test_plat.py` were verified against the new semantics.

| Verification | Result |
|---|---|
| `pytest tests/fleet/test_conductor_leases.py::test_every_recorded_process_is_stopped_before_the_revoke`, 12 runs, 4 CPU hogs, **before** the fix | **2 failed / 10 passed** |
| Same test, same load, **after** the fix | **12 passed / 0 failed** |
| `tests/pmk/test_plat.py`, `test_conductor_leases.py`, `test_fleet.py`, `test_hermes_session.py` | 111 passed |

**Honest limitation.** The failing run's `LEASE_REAP_FAILED` payload was never captured (the flake would not reproduce on request), so the diagnosis is inferred from the code path and the 12/12 recovery rather than from a captured stage/error pair. The fix is principled and verified, but the flake's specific trigger is *Derived*, not *Confirmed*.

## A.3 Forensics — who edited the live tree (reviewer item 1)

**Answer: Unknown by direct evidence.** No kernel, git, or session record attributes the 2026-11-10 live-tree edits. What is provable:

| Local time, 2026-11-10 | Artifact | Reading |
|---|---|---|
| 09:24:55 | `tests/fleet/test_canary_runner.py` | canary-runner test |
| 09:50:08 | `src/fleet/canary.py` | canary runner |
| **17:07:36–38** | `src/fleet/owner.py` (created), `console/app.py`, `index.html`, `test_dispatch_owner.py`, `test_console_dispatch.py`; pytest ran 17:08:02 | one coherent unit: the single-owner dispatch lock + Console wiring |
| **17:35:00–01** | `tests/fleet/test_conductor_leases.py`, `test_fleet.py` | second, smaller unit |
| 17:19 / 17:25 | `tmp/reviewer-kernel`, `tmp/reviewer-patches` | the reviewer's isolated clones |
| 17:43 | `C:\temp\review-r15\` | the reviewer's evidence export (HEAD `a4cbd0a`) |
| **2026-11-11 10:09** | `agents.toml` | **the operator** (see §A.4) |

Negative results, which is why the answer is `Unknown`:
- `.pm/events/2026-11-10.jsonl` **begins at `05:20:01Z` (18:20 local)** — the live kernel recorded nothing covering 04:07/04:35 UTC, so there is no ledger record of the edits.
- `src/fleet/owner.py` exists on **no ref, no branch, and in no worktree** — git cannot attribute it.
- `git reflog` shows no reset or amend in that window; `git stash list` is empty.
- Global session stores (`.claude`, `.codex`, `~/.local/share/opencode/opencode.db`) contain no sessions in the window; the shell history shows the reviewer *investigating* those files, not creating them.

**Candidate family — explicitly not proven.** `prompt-canary-process-opencode-to-freebuff-v1.md` (written 2026-11-11 02:22) is a handoff **from an opencode session to freebuff** that cites `src/fleet/owner.py:250`'s internals precisely and states that the live-tree edits are unsettled. That implicates an **opencode-family session** as author or inheritor of the wave. It is not proof: no session record, no card, and no commit binds the work to that session. Recorded as *Derived-candidate*, **not** as Confirmed.

## A.4 Provenance of the uncommitted set (three authors, not one)

| Provenance | Files | Author |
|---|---|---|
| Single-owner wave | `src/fleet/owner.py`, `canary.py`, `dispatcher.py`, `console/app.py`, `index.html`, `harness.py`, and their tests | **Unknown session(s)** — no record; opencode-family *implicated*, unproven |
| Concurrency cap | `agents.toml` — `max_concurrent` 2 → 1 on several opencode/inkling/orca-auto profiles | **Operator** (confirmed by the operator in this session; the rationale given is that those models cannot hold more than one connection) |
| H1 + fragility fixes | `src/pmk/api.py`, `events.py`, `plat.py`, `tests/pmk/test_lease_admission.py`, three fleet test helpers | **DeepSeek V4.1 Flash Free — `opencode/deepseek-v4.1-flash-free`** |
| Pre-existing, untouched | `docs/`, `.pm/views/*`, `src/cna/*`, and the remaining CNA test edits | other sessions, outside this repair |

**Derived.** No single "group A" exists. Any commit must therefore be sliced by provenance, not by directory — and the reviewer's instruction not to commit the wave is a decision about the first row only.

## A.5 Corrections to my own earlier claims in this document

| # | Earlier claim (section) | Correction |
|---|---|---|
| 1 | §3, §2 row 5: H1 "Absent"; the full gate green implies H1 unlanded | **Superseded.** H1 landed later the same day; see §A.1. The gate runs above are the post-change ones. |
| 2 | §7.3 fragility 1 and 2 recorded as open | **Superseded.** Both fixed; see §A.2. |
| 3 | §6 row 5: "`0004-rebased.patch` exists only at `…/patches-filtered/0004-rebased.patch`, not as a formatted patch series" | **Partly wrong.** A series *does* exist at `tmp/reviewer-patches/patches-rebased/`: `0001`–`0003` **are** genuine `git format-patch` output (`From 8943a595…`, `Subject: [PATCH 1/4]`). Only `0004-rebased.patch` is a raw diff. |
| 4 | §6 row 5 implied the patch might be corrupt (the reviewer's checker reports "NUL bytes or not an mbox patch (UTF-16?)") | **Refined.** I verified the file: **0 NUL bytes**, valid UTF-8, LF endings. The checker's trigger is the *"not an mbox patch"* branch — the message text is the tool's combined wording, not a finding of corruption. |
| 5 | §6 row 5: `canary_gate_timeout_s` "rename not applied, or never present there" | **Refined.** The name is absent from the live tree; it exists only inside `0004-rebased.patch` and `tmp/review-followups/` (`agents.toml`, `src/fleet/merge.py`, a test). The rename is still outstanding. |
| 6 | This session: `agents.toml` "modified at 10:09 today — **and not by me** … investigating" | **Corrected.** It was the **operator's** deliberate edit. My "unknown concurrent writer" concern is withdrawn. |

Correction 6 is recorded because I stated the mis-attribution before it was resolved; the operator's clarification is the source of truth. Also noted from §7.2: my withdrawal of an *asserted clean-base pass* before the run printed its result line — that correction stands as written.

## A.6 The reviewer's six items — status by number

| # | Requirement | Status now | What would close it |
|---|---|---|---|
| 1 | Name the session that edited the live tree; no further live edits; do not commit group A | **Unknown**, candidate family named (§A.3). The freeze has in practice been lifted by the operator's instruction to complete the repair | An operator statement, or a ruling that `Unknown` is the final answer |
| 2 | One shared `require_human_authority()` + `PMK_ACTOR=human:<name>` + interactive TTY, covering void / pins / class-K queue-decide / resume / profiles / swap / manual launch; silent error text | **Absent.** `require_human_authority` has **0** occurrences in `src/` | Implement the helper (§A.9 decision B) |
| 3 | `resume_dispatch`/`--resume` use the helper; `CANARY_STARTED`/`CANARY_FINISHED` record a verified human or refuse; one canary at a time | **Partial.** The events exist (`src/fleet/canary.py:93,134`) but emit `actor=Actor.kernel()`. `pmk resume` (`src/pmk/cli.py:353-357`) deletes the stop file with **no authority check at all** | Same as #2 |
| 4 | Console `/api/queue/decide` fails for class K; propose a fix (e.g. a per-start token) without changing the Console's no-auth design | **Open**, and blocked on a design question (§A.9 decision B) | The Console/TTY ruling |
| 5 | Deliver `0004-rebased.patch` as `git format-patch`; rename `canary_gate_timeout_s`; docs say the gate ran "between 12.5 and 15 minutes, unknown"; remove "too tight" | **Partial.** `0001`–`0003` formatted; `0004` still a raw diff (§A.5). The rename is outstanding; the name is absent from the live tree | Convert `0004`, rename, publish the corrected wording |
| 6 | Stop calling the checker the reviewer's tool | Not machine-checkable; unchanged | Editorial |

**Note on the reviewer's own drafts — protected, not mine.** `tmp/reviewer-kernel` is a **separate clone** (its `.git` is a directory, not a linked-worktree file) sitting at the reviewer's base `a4cbd0a`, with uncommitted work: `M src/pmk/api.py`, `M src/pmk/cli.py`, `?? tests/pmk/test_actor_enforcement.py`. The export `C:\temp\review-r15\` holds `kernel-actor-guards.diff`, `test_actor_enforcement.py`, `dirty-control.diff`, `head.txt`, `dirty-file-times.txt`. Under A-14 this is another actor's work: cited as evidence, **not modified**. It already implements item 2's class-K / pins / void portion and should be the base for item 3 rather than a rewrite.

## A.7 Finding — T-0192's declared write scope is too narrow

`T-0192` declares `write: [src/pmk/api.py, tests/pmk/test_lease_admission.py]`. H1's admission rule invalidates the setup of two **out-of-scope** fleet test helpers that lease a worktree directly:

- `tests/fleet/test_regressions.py` — `_submit_task(...)` and one direct claim site
- `tests/fleet/test_conductor_leases.py` — `_orphan_with_worktree(...)`

| Observation | Status |
|---|---|
| The first post-change `tests/pmk + tests/fleet` run reported **25 failed** | Confirmed |
| A subsequent full-suite run, after the first helper was fixed, still reported **9 failed** in `tests/fleet/test_conductor_leases.py`, plus the PATH-dependent identity-guard failure | Confirmed |
| After both helpers were updated (each claim now passes `pid=os.getpid()` and a far-future `expires_at`), the suites are green: 517 passed / 1 skipped, full suite exit 0 | Confirmed |

**Derived.** Two consequences:

1. If `T-0192` is run through the harness, `diff_scope_check` will refuse the merge — the change legitimately spans files the card does not own.
2. `pmk supersede` (`--commit`, `--ref`, `--reason`) marks a task superseded by a commit; it does **not** amend a card's scope, and no command does. So the remedies are: **void `T-0192` (operator-only) and create a corrected-scope replacement**, or **land the work directly and record that `T-0192` is discharged outside the harness.**

## A.8 Finding — the card and the tree disagree

H1's work is done and gate-green, and `T-0192` still reads `READY` (attempt 0 of 2). Because resumption is excluded (item 8) and dispatch is `PAUSED`, the card cannot travel claim → submit → verify → integrate, so it cannot reach `DONE`.

**Confirmed** state: `T-0192` `READY`; `tests/pmk/test_lease_admission.py` present and passing; `pmk status` `PAUSED`; `active_leases: 2`.

**Derived.** This is a direct consequence of excluding resumption, not a defect — but it means the ledger currently *understates* the repair. Whoever next reconciles the ledger should not read `T-0192 READY` as "H1 not done".

## A.9 Ordered next steps, with exact commands

Two decisions change the most; everything else follows them.

**Decision A — how `T-0192` is discharged (§A.7).** Either land directly and record it, or `pmk task void T-0192 --reason "scope too narrow; landed directly"` and recreate with `tests/fleet/test_regressions.py` and `tests/fleet/test_conductor_leases.py` in `write`. `pmk task void` is operator-only.

**Decision B — the Console/TTY question (item 3).** The reviewer requires `PMK_ACTOR=human:<name>` **plus an interactive TTY**, while item 4 says the Console's no-auth design must not change pending your decision — and the Console has no TTY. Either the Console class-K path fails (as the reviewer anticipates) with a per-start token proposed later, or the Console is exempt from the TTY condition. **I did not guess this.** Everything else in item 3 is unambiguous and the reviewer's draft is ready to adopt.

Then, in order:

| # | Step | Exact command |
|---|---|---|
| 1 | Revoke the two invalid leases (human authority) | `pmk revoke T-0210 --fence 162 --reason "H1: repo-root worktree grant; invalid"` · `pmk revoke T-0211 --fence 163 --reason "H1: repo-root worktree grant; invalid"` |
| 2 | CP-3: capture the 7 dirty trees, then prune | `pmk worktree archive --all-dirty` (verifies each capture) → `pmk worktree prune --yes --archive`. **Dry-run first** by omitting `--yes`. Do not prune the foreign `H1-H4-clean-*` trees without an explicit ruling |
| 3 | Re-run the gate at the post-landing base | `python -m pytest -q`, then `tools\check_clean_base.ps1 -Python "<absolute path to .venv\Scripts\python.exe>"` — see the note below |
| 4 | Settle the uncommitted set by provenance (§A.4) | Commit decision; the reviewer's "do not commit group A" applies to the **Unknown-provenance wave** only |
| 5 | CP-4: ratify D-72 (+ its erratum), not D-73 | Operator act in `pilot/decisions.md`; D-70…D-74 are all still drafts |
| 6 | Record T-0189's final disposition | `T-0189` is **VOID** (attempt 1/1); successor **T-0190** (fence 157, `DONE`, merge `0edc0dc`); phrase it as superseded, not exonerated |
| 7 | Item 8, excluded from "repair" | Resume (A10), dispatch resumption, first push — operator-only; `DISPATCH_RESUMED`/`DISPATCH_PAUSED`/`MANUAL_LAUNCH` are still **0** occurrences in the chain |

**Important limit on DoD-1.** The clean-base gate at `5267cdb` (recorded above, exit 0) predates every change in this addendum, and the changes are **uncommitted**. `tools/check_clean_base.ps1` checks out `HEAD` into a detached worktree, so it cannot cover uncommitted work at all. Until the changes are committed, **no clean-base proof of them is possible** — the dirty-tree runs above are the only evidence, which is exactly the limitation B-14/N-05 warn about. Also note the tool's `-Python` parameter must be an **absolute** path (§7.3 fragility 3, still unfixed).

## A.10 Evidence index (addendum)

| Artifact | Path | What it proves |
|---|---|---|
| Full suite, post-fix | `tmp/gate-h1-frag-20261111.log` | exit 0, 1 skipped, under load, with the identity guard green |
| Full suite, mid-fix | `tmp/gate-h1-20261111.log` | the 9 remaining conductor-lease failures + identity guard, before their helpers were updated |
| H1 oracle | `tests/pmk/test_lease_admission.py` (+ `tests/pmk/test_tasks.py`) | 35 passed |
| DoD-1 (pre-addendum base) | `tmp/clean-base-20261111-094825.log`, `tmp/clean-base-verify-20261111b.log` | `clean-base gate exit=0 sha=5267cdb…` — **does not cover this addendum's changes** |
| Reviewer's drafts | `tmp/reviewer-kernel/` (separate clone, `M src/pmk/api.py`, `M src/pmk/cli.py`, `?? tests/pmk/test_actor_enforcement.py`), `C:\temp\review-r15\` | item 3's starting material — another actor's work, protected |
| Wave handoff prompt | `prompt-canary-process-opencode-to-freebuff-v1.md` | implicates an opencode-family session; **not proof** |
| Reviewer's relay | event `seq 3630`, `2026-11-10T10:17:19Z`, subject `T-0211` | the six items in §A.6 |
| Live invalid leases | `.pm/views/status.md:29-32` | `T-0210` fence 162, `T-0211` fence 163 — unchanged |

---

**Author:** DeepSeek V4.1 Flash Free — `opencode/deepseek-v4.1-flash-free`. Authored both the report and this addendum; no independent assessment of either exists, and no `assessor_llm` is claimed.
**Status of this addendum:** advisory verification record. It grants no authority, ratifies nothing, promotes nothing, and changes no kernel state. Its code changes are **uncommitted**.
**Storage:** uncommitted in `docs/reports/`. Committing it, citing it from `HANDOFF.md`, or folding it into a decision record are operator decisions.
