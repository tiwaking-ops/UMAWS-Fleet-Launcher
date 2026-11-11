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

> **Committed later the same day — see §A.11.** The work described below was committed as `b2fe947`, and the clean-base gate has since run green at that base. Every "uncommitted" statement in §A.0–§A.10 is superseded by §A.11.

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

## A.8 Finding — the card and the tree disagree (**resolved — see §A.12**)

H1's work is done and gate-green, and `T-0192` still reads `READY` (attempt 0 of 2). Because resumption is excluded (item 8) and dispatch is `PAUSED`, the card cannot travel claim → submit → verify → integrate, so it cannot reach `DONE`.

**Confirmed** state: `T-0192` `READY`; `tests/pmk/test_lease_admission.py` present and passing; `pmk status` `PAUSED`; `active_leases: 2`.

**Derived.** This is a direct consequence of excluding resumption, not a defect — but it means the ledger currently *understates* the repair. Whoever next reconciles the ledger should not read `T-0192 READY` as "H1 not done".

**Resolved 2026-11-11 — §A.12.** The operator discharged the card the same day; `T-0192` is now `VOID` and this finding is closed.

## A.9 Ordered next steps, with exact commands

Two decisions change the most; everything else follows them.

**Decision A — how `T-0192` is discharged (§A.7).** ***Resolved 2026-11-11 — see §A.12.** The text below was the *pre-decision* framing and its "either … or" is superseded: `supersede` and `void` turned out to be complementary, not alternatives.* Either land directly and record it, or `pmk task void T-0192 --reason "scope too narrow; landed directly"` and recreate with `tests/fleet/test_regressions.py` and `tests/fleet/test_conductor_leases.py` in `write`. `pmk task void` is operator-only.

**Decision B — the Console/TTY question (item 3).** The reviewer requires `PMK_ACTOR=human:<name>` **plus an interactive TTY**, while item 4 says the Console's no-auth design must not change pending your decision — and the Console has no TTY. Either the Console class-K path fails (as the reviewer anticipates) with a per-start token proposed later, or the Console is exempt from the TTY condition. **I did not guess this.** Everything else in item 3 is unambiguous and the reviewer's draft is ready to adopt.

Then, in order:

| # | Step | Exact command |
|---|---|---|
| 1 | Revoke the two invalid leases (human authority) | `pmk revoke T-0210 --fence 162 --reason "H1: repo-root worktree grant; invalid"` · `pmk revoke T-0211 --fence 163 --reason "H1: repo-root worktree grant; invalid"` |
| 2 | CP-3: capture the 7 dirty trees, then prune | `pmk worktree archive --all-dirty` (verifies each capture) → `pmk worktree prune --yes --archive`. **Dry-run first** by omitting `--yes`. Do not prune the foreign `H1-H4-clean-*` trees without an explicit ruling |
| 3 | Re-run the gate at the post-landing base | **Done (§A.11)** — `clean-base gate exit=0` at `b2fe947`. Command: `tools\check_clean_base.ps1 -Python "<absolute path to .venv\Scripts\python.exe>"` |
| 4 | Settle the uncommitted set by provenance (§A.4) | **Done (§A.11)** — committed as `b2fe947`, 24 files, three provenances in one commit. The reviewer's "do not commit group A" was overtaken by the operator's instruction to commit; the wave's authorship is still Unknown |
| 5 | CP-4: ratify D-72 (+ its erratum), not D-73 | Operator act in `pilot/decisions.md`; D-70…D-74 are all still drafts |
| 6 | Record T-0189's final disposition | `T-0189` is **VOID** (attempt 1/1); successor **T-0190** (fence 157, `DONE`, merge `0edc0dc`); phrase it as superseded, not exonerated |
| 7 | Item 8, excluded from "repair" | Resume (A10), dispatch resumption, first push — operator-only; `DISPATCH_RESUMED`/`DISPATCH_PAUSED`/`MANUAL_LAUNCH` are still **0** occurrences in the chain |

**Important limit on DoD-1 — superseded by §A.11.** When this was written, the clean-base gate at `5267cdb` (recorded above, exit 0) predated every change in this addendum and the changes were **uncommitted**; `tools/check_clean_base.ps1` checks out `HEAD` into a detached worktree, so it could not cover uncommitted work at all, and the dirty-tree runs were the only evidence — exactly the limitation B-14/N-05 warn about. **That limit no longer applies:** the work was committed as `b2fe947` and the gate has since run green at that base (§A.11). Two notes still stand: the tool's `-Python` parameter must be an **absolute** path (§7.3 fragility 3, still unfixed), and the gate log does not record pytest's count line (§A.11, fragility 4).

## A.10 Evidence index (addendum)

| Artifact | Path | What it proves |
|---|---|---|
| Full suite, post-fix | `tmp/gate-h1-frag-20261111.log` | exit 0, 1 skipped, under load, with the identity guard green |
| Full suite, mid-fix | `tmp/gate-h1-20261111.log` | the 9 remaining conductor-lease failures + identity guard, before their helpers were updated |
| H1 oracle | `tests/pmk/test_lease_admission.py` (+ `tests/pmk/test_tasks.py`) | 35 passed |
| DoD-1 (pre-addendum base) | `tmp/clean-base-20261111-094825.log`, `tmp/clean-base-verify-20261111b.log` | `clean-base gate exit=0 sha=5267cdb…` — predates this addendum's changes; **superseded by §A.11**, which gates them at `b2fe947` |
| Reviewer's drafts | `tmp/reviewer-kernel/` (separate clone, `M src/pmk/api.py`, `M src/pmk/cli.py`, `?? tests/pmk/test_actor_enforcement.py`), `C:\temp\review-r15\` | item 3's starting material — another actor's work, protected |
| Wave handoff prompt | `prompt-canary-process-opencode-to-freebuff-v1.md` | implicates an opencode-family session; **not proof** |
| Reviewer's relay | event `seq 3630`, `2026-11-10T10:17:19Z`, subject `T-0211` | the six items in §A.6 |
| Live invalid leases | `.pm/views/status.md:29-32` | `T-0210` fence 162, `T-0211` fence 163 — unchanged |

## A.11 Commit and clean-base verification (2026-11-11, later)

**§A.0–§A.10 above were written before the work was committed; their "uncommitted" statements are superseded here.**

**Confirmed — the commit.** The staged 24-file set was committed by the operator as **`b2fe947`** (`fleet/pmk: single-owner dispatch lock, canary runner, H1 lease admission, gate fragility fixes`), parent `5267cdb`, author and committer `umaws-pilot <umaws-pilot@localhost>`, 2026-11-11 17:33:18 +1300, +2185/−27.

| Check | Result |
|---|---|
| Committed tree vs the tree whose index I gated | `77c41560fc314e8cdf3f8036accec9483efcce23` — **byte-identical** to throwaway commit `93acefa`'s tree, so the green run applies to exactly what was committed |
| Protected paths inside the commit | **0** entries from `src/cna/**`, `agents.toml`, `.pm/**`, `tmp/**` |
| Identity-guard hook | wrote no `identity-warnings.log` |

**Confirmed — the clean-base gate now covers the repair.** `tools/check_clean_base.ps1` at `HEAD b2fe947`, absolute `-Python`, log `tmp/clean-base-20261111-b2fe947.log`:

| Observation | Reading |
|---|---|
| `clean-base gate exit=0 sha=b2fe9478108c9534af0fe96a774d1c8f9ce22053` | green |
| Import lines `…\umaws-gate-20261111-b2fe947\src\cna\engine\loop.py` and `…\src\pmk\__init__.py` | both resolve **inside** the gate worktree — no P-01 editable-install shadowing |
| Progress marks in the log | **1220 tests marked: 1219 pass, 1 skip, 0 fail** |
| Gate worktree | removed on success (the script does this); `umaws-gate-20261111-b2fe947` no longer exists |

**Derived — the 1292-vs-1220 gap is fully accounted for, and it is the point of the tool.** The working tree collects **1292**; the clean tree at `b2fe947` collects **1220**. The 72-test difference is **entirely uncommitted test material**, verified by a per-file collection diff:

| Source | Tests | Kind |
|---|---|---|
| `test_data_intake.py` (18), `test_p1b1_land_contracts.py` (12), `test_p1c2_gate.py` (7), `test_data_r05.py` (5), `test_report_reconciliation.py` (5) | **47** | **untracked** CNA test files |
| `test_transport.py` (11), `test_data_r04.py` (7), `test_scenario_loader.py` (6), `test_stage_supply.py` (1) | **25** | tracked, but **modified** by uncommitted CNA work |
| **Total** | **72** | 47 + 25 = 72 ✓ |

All 72 sit in the A-12-protected CNA body, deliberately left uncommitted. The gate therefore measures the committed tree and only the committed tree — which is what DoD-1 asks for.

**Finding — the gate log does not record its own result (new; call it fragility 4).** `check_clean_base.ps1` never gets pytest's terminal count line into its log. Cause, reproducible: `addopts = -q` is set in **both** `pytest.ini` and `pyproject.toml`, and the script adds a further explicit `-q`, so pytest runs at effectively `-qq`, which suppresses the summary line. The 1220 figure above therefore comes from the progress marks, not from the log. **Every** gate log cited in this programme shares the defect — including `tmp/gate-h1-frag-20261111.log`, cited in §A.1, which is why the "1292 collected" in that row actually comes from a separate `--collect-only` run and not from the log it names.

| Capture method | Terminal count line present? |
|---|---|
| `pytest -q … *> file` (config `-q` + explicit `-q`) | **no** — progress line only |
| `pytest -q … \| Out-File` | **no** |
| `cmd /c "… > file 2>&1"` | **no** |
| `Start-Process -RedirectStandardOutput` | **no** |
| `pytest -o addopts="" -q …` (single `-q`) | **yes** — e.g. `4 passed in 2.76s` |

**Suggested fix (not applied — `tools/` is outside this repair's authorized scope):** drop the duplicate `-q`, or pass `-o addopts=""` with a single `-q`, or persist `-rA` so the totals land in the log. Until then, a gate log's exit code and progress marks are its evidence, and the count must be recovered separately.

**Corrections to this addendum's own earlier statements.**

| # | Earlier statement (section) | Correction |
|---|---|---|
| 1 | §A.9 "Important limit on DoD-1": the changes are **uncommitted** … **no clean-base proof of them is possible** | **Superseded.** Committed as `b2fe947`; the gate ran there and exited 0 (above). |
| 2 | §A.10 DoD-1 row: **does not cover this addendum's changes** | **Superseded.** The `b2fe947` gate does cover them. |
| 3 | State/status lines in §A.0, §A.10, §A.4: working tree "**uncommitted**"; "Its code changes are **uncommitted**" | **Corrected.** The repair slice *and* the fleet wave are committed inside `b2fe947`. Still uncommitted: the CNA body (A-12 protected), `agents.toml` (operator), `.pm/**` runtime state, `tmp/**`, and root-level strays. |
| 4 | §A.1 evidence row: "Full suite … 1292 collected (`tmp/gate-h1-frag-20261111.log`)" | **Provenance corrected.** That log has no count line (§A.11 fragility 4); 1292 is a working-tree `--collect-only` figure, and the committed tree's clean-base figure is **1220**. |

**Standing after the commit.** **DoD-1 is now PASS at `b2fe947`**, a base that includes H1 and both fragility fixes. Two of §A.9's steps are discharged: **step 3** (re-run the gate at the post-landing base — clean-base green) and **step 4** (settle the uncommitted set — committed as `b2fe947`). **Steps 1, 2, 5, 6 and 7 remain open**, as do Decisions A and B. DoD-5 remains partial (the leases). Hardening: **3 of 7 items landed** (H1, H2, H6), H5 partial, H3/H4/H7 absent; the human-authority gate and CP-3/CP-4 still open.

## A.12 Decision A resolved — `T-0192` discharged (2026-11-11)

**Confirmed.** The operator closed Decision A with two human-attributed events, in the order §A.9 prescribed:

| seq | type | actor | payload |
|---|---|---|---|
| 3635 | `SUPERSEDED_BY` | `human:operator` | `commit: b2fe947`, `ref: ""`, reason recorded |
| 3636 | `TASK_VOIDED` | `human:operator` | `fence: 0`, reason recorded |

`pmk task show T-0192` → `state: VOID` with its `block_reason` set; the READY queue fell from **12 to 11**; `pmk sentinel` → `ok: true`, `findings: []` across all twelve invariants (I1, I3, I4, I5, I6, I7, I8', I13, I14, I15, I16, I17). Chain verifies at **3,637 events** (the event above 3,636 is the sentinel's own `PINS_CHECKED`).

**Correction — §A.7 and §A.9 framed `supersede` and `void` as alternatives. They are complementary, and only `void` discharges the card.** Reading the implementation afterwards: `record_supersession` (`src/pmk/api.py:942`) appends a `SUPERSEDED_BY` event and nothing else — no reducer reads that type (`src/pmk/state.py` handles `TASK_VOIDED` but has no `SUPERSEDED_BY` branch), and its sole consumer is sentinel I5/R1 (`src/pmk/sentinel.py:170`), which applies only to a task that was `INTEGRATED` with an empty commit — a state `T-0192` never reached (it was never claimed). **Used alone, `supersede` would have left the card `READY`.** `void` is the retirement; `supersede` is the REC-11 traceability annotation recording *where the content landed*. Both were run, in that order.

**Standing.** §A.7's scope defect and §A.8's card/tree disagreement are both closed. `T-0192` is `VOID`; its H1 content is committed and clean-base-proven in `b2fe947`; the ledger no longer understates the repair; and §A.8's caution ("do not read `READY` as 'H1 not done'") is obsolete. Decision B, the two invalid leases, CP-3 and CP-4 remain open.

## A.13 CP-2 executed and CP-3 attempted — a reclamation defect found (2026-11-11)

**CP-2 — closed.** The operator revoked both invalid leases: events `seq 3638` (`T-0210`, fence 162) and `seq 3639` (`T-0211`, fence 163), actor `human:operator`. `pmk status` now reports **`active_leases: 0`**, so `DoD-5`'s second half is satisfied — H1 refuses that grant shape prospectively, and the two historical instances are retired by human action.

**Finding — `new_fence` is not unique (minor).** Both revocations returned `new_fence: 165`. Cause: `_next_fence` (`src/pmk/api.py:192-201`) takes the maximum over `event.fence` and `payload["fence"]`, but a `REVOKED` event records the *new* fence under `payload["new_fence"]`, which is never read. Consecutive revocations therefore hand out the same generation number. **Benign here** — fences are compared per task (`_current_fence`), both cards are now `VOID`, and nothing can race them — but it means `new_fence` is not the global monotonic counter its name implies.

**Views are stale, not wrong.** `.pm/views/status.md:29-32` still lists the `T-0210`/`T-0211` leases although the kernel reports none; views regenerate on a debounce and `pmk views` forces it. No state defect.

**CP-3 — 14 of 27 reclaimed; 13 are stuck, and that is a defect.** The operator ran `worktree archive --all-dirty` (7 captured, including the three foreign `H1-H4-clean-*` / `launcher-repair-clean-*` trees, which `prune` then correctly left in place) and `worktree prune --yes --archive`, which **removed 14** trees and archived each first. **21 remain**: 8 non-lease trees (`gate-*`, `h1-h4-branch-*`, the three foreign ones, `legacy-launcher-cwd-fallback-*`) and **13 that `prune` refused with "an active lease still owns this worktree"** — a message that is false.

| Observation | Confirmed detail |
|---|---|
| `pmk status` | `active_leases: 0` |
| The 13 refused trees | `T-0139-117`, `T-0150-121`, `T-0169-145`–`T-0174-150`, `T-0181-144`, `T-0182-151`, `T-0190-157`, `T-0191-158`, `T-0196-159` |
| Their cards | **all `DONE`** |
| Their lease entries | **still present** in `state.leases`; lease fence equals the worktree-name fence exactly |
| `state.leases` | **38 entries — all 38 stale** (`active_leases()` returns 0) |

**Root cause.** The reducer pops a lease only on `REVOKED` (`src/pmk/state.py:166`); `INTEGRATED` sets the card to `DONE` (`src/pmk/state.py:190-193`) and **retains** the lease entry — deliberately, because `revoke` requires it for a post-integration review (§A.14). The defect is therefore not the retention but the consumer: `worktrees._deletion_refusal` (`src/pmk/worktrees.py:757-759`) read that **unfiltered** table and refused reclamation whenever a leftover entry's fence matched the tree name — precisely the case for every worktree of a completed task.

**Why nothing else clears it.** `pmk sweep` iterates `state.active_leases()` (`src/pmk/cli.py:378`), which filters to `ACTIVE_STATES = (LEASED, SUBMITTED, VERIFYING, INTEGRATING)` (`src/pmk/models.py:34`) — the 38 stale entries are invisible to it. `pmk revoke` would pop one, but it also drags the card out of `DONE` back to `READY`/`BLOCKED` (`src/pmk/state.py:155-165`), resurrecting finished work. **No existing command reclaims these 13 trees without corrupting card state.**

**Derived.** A REC-04 reclamation defect with real operational cost: worktrees of *successfully completed* tasks are permanently unreclaimable, so the census can only grow. It also means §A.9 step 2 cannot be completed as written.

**Two candidate fixes were weighed; only the second is correct.** (The fix as landed, and how the first was falsified, are in §A.14.)
1. ~~Pop the lease on `INTEGRATED` (`src/pmk/state.py:190`).~~ **Rejected.** The retained entry is load-bearing: a post-integration review calls `revoke` on a `DONE` task, and `revoke` raises `no_lease` unless `state.leases` still holds the entry (`src/pmk/api.py:650-652`). Popping it broke two tests that assert exactly that path — `test_sentinel_silent_for_revoked_task_with_failing_bundle` and `test_sentinel_does_not_flag_valid_reintegration` (both in `tests/pmk/test_regression_i5.py`).
2. **Make `_deletion_refusal` consult `active_leases()`** rather than the raw table (`src/pmk/worktrees.py:757`) — the predicate the check actually means ("is this still *held*?"), and robust to every non-active state rather than `DONE` alone.

**Standing.** Chain verifies at **3,639 events**; `pmk sentinel` → `ok: true`, no findings; project `PAUSED`; 21 pmk worktrees. CP-2 closed and `DoD-5` satisfied; CP-3 was blocked by the defect above, **not** by an operator decision — fixed in §A.14.

## A.14 CP-3 defect fixed — the reclamation predicate (2026-11-11)

**Confirmed — the fix is one production change, in the consumer.**

| File | Change |
|---|---|
| `src/pmk/worktrees.py` | `_deletion_refusal` asks **`state.active_leases()`** instead of the raw `state.leases` table. Only a lease that is still *held* may refuse reclamation. |
| `src/pmk/state.py` | No behavioural change; a comment now records that the `INTEGRATED` lease entry is **retained deliberately** (`revoke` needs it) and that "is this still held?" must be asked of `active_leases()`. |
| `tests/pmk/test_worktree_lifecycle.py` | Two regression tests: a `DONE` task's tree must be reclaimable and must be removed by `prune`; and an entry left by `PREMISE_REFUTED` must not refuse reclamation either. |

**A first fix was attempted and falsified — §A.13's recommendation 1 is withdrawn.** Popping the lease on `INTEGRATED` looked like the cause-level fix, and I recommended it. It broke `tests/pmk/test_regression_i5.py::test_sentinel_silent_for_revoked_task_with_failing_bundle` and `::test_sentinel_does_not_flag_valid_reintegration`: **both integrate a task and then `revoke` it for post-integration review**, and `revoke` raises `no_lease` once the entry is gone (`src/pmk/api.py:650-652`). The retention is load-bearing, not a leak. Recorded here because the wrong fix was recommended before it was tested.

**Evidence.**

| Check | Before | After |
|---|---|---|
| `state.leases` / `active_leases()` | 38 / 0 | 38 / 0 — retained by design |
| The 13 refused trees, `_deletion_refusal` | refused | all **13** return `""` |
| `pmk worktree prune` dry-run skips | 8 non-lease + **13 "active lease"** | 8 non-lease only |
| Full gate (`python -m pytest -o addopts="" -q`) | — | **1293 passed, 1 skipped**, exit 0 |
| `test_regression_i5.py` + `test_worktree_lifecycle.py` | — | 83 passed, 1 skipped |
| `pmk sentinel` | — | `ok: true`, no findings |

Read-only probes: `tmp/probe_leases.py`, `tmp/probe_reclaimable.py`.

**Residual observation, recorded as behaviour rather than a defect.** `pmk task show` still displays the retained lease entry for a `DONE` task. That is now understood as intentional — the entry is the fence a post-integration `revoke` needs — so it is left alone.

**Standing.** CP-3 can now be completed: `pmk worktree prune --yes --archive` should remove the 13 previously-refused trees, while the 8 non-lease trees (including the three foreign `H1-H4-clean-*` / `launcher-repair-clean-*` gate trees) remain correctly skipped. Whether to run it is CP-3's operator decision. **Decision B was answered `A`** — the Console refuses class-K decisions and points at the terminal; no per-start token. Chain verifies at **3,640 events**; project `PAUSED`; `active_leases: 0`.

## A.15 Post-commit verification — `a1d301c`, CP-3 completed, and the canary that was not needed (2026-11-11)

**Scope.** This section verifies the operator's own commit and follow-on run of §A.14's steps: the commit `a1d301c`, the clean-base gate at that base, CP-3's completion, `DoD-3` and `DoD-4`. It also corrects advice I gave in §A.9/§A.10 and repeated in `HANDOFF.md`: **the `DoD-6` canary did not need to be re-run, and recommending it was wrong.**

**Confirmed — the commit.**

| Field | Value |
|---|---|
| SHA | `a1d301c8a5d9a3a55d0a5e268e5169ee9633bab6` |
| Tree | `e976189a4d80b118480c303d4d19099c7a44f2f9` |
| Parent | `2a579dd` |
| Author / committer | `umaws-pilot <umaws-pilot@localhost>` |
| Scale | 6 files, +104/−13 |
| Base relationship | 0 behind / **137** ahead of `origin/main` |

The six files are exactly the ones §A.14 staged: `src/pmk/worktrees.py` (the one-line fix), `src/pmk/state.py` (comment only), `tests/pmk/test_worktree_lifecycle.py` (two regression tests), this report, `HANDOFF.md`, and the plan's `DoD-5` row.

**Confirmed — the clean-base gate now covers the fix.** `tools/check_clean_base.ps1 -Python "<absolute path to .venv\Scripts\python.exe>"` at `HEAD a1d301c`, log `tmp/clean-base-20261111-235639.log`:

| Observation | Reading |
|---|---|
| `clean-base gate exit=0 sha=a1d301c8a5d9a3a55d0a5e268e5169ee9633bab6` | green |
| Import lines `…\umaws-gate-20261111-235639\src\cna\engine\loop.py` and `…\src\pmk\__init__.py` | resolve **inside** the gate worktree — no editable-install shadowing |
| Count line | absent again — fragility 4 (§A.11), unchanged |

The gate worktree `C:\temp\projects\umaws-gate-20261111-235639` was removed on success. **`DoD-1` therefore PASSES at a third base**, the first that contains the CP-3 fix.

**Confirmed — CP-3 is complete.** The §A.14 fix made the 13 previously-refused trees reclaimable, and the operator's dry run and real run agree:

| Run | Result |
|---|---|
| `pmk worktree prune` (dry run) | 13 candidates, **0** active-lease skips; the only skips are the **8** non-lease trees (`"not a lease worktree name"`); `recoverable_bytes: 186,472,774` |
| `pmk worktree prune --yes --archive` | **removed 13**, **archived 13** (each to `stranded\<name>`), **skipped 8** |

`work/` now holds **exactly the 8 non-lease trees** — `gate-*` ×3, `h1-h4-branch-*`, the three foreign `H1-H4-clean-*` / `launcher-repair-clean-*` gate trees, and `legacy-launcher-cwd-fallback-*` — all correctly protected. No un-captured deletion: every removed tree was archived first (`stranded/` holds 97 archived trees).

**Confirmed — `DoD-3` passes.** `python tools\check_subprocess_env.py` → `ok: no unguarded subprocess spawns (7 allowlisted); fleet cwd checks pass`, exit 0. The plan row's `_pending_` was stale.

**Confirmed — `DoD-4` reconciles.** `git worktree list` reports **28** entries against `pmk`'s **8**, and the difference is fully attributed:

| Group | Count | Note |
|---|---|---|
| Main checkout | 1 | the repository root |
| `work/` | 8 | **identical names** to `pmk worktree list` — the 8 non-lease trees |
| `tmp/` | 6 | canary/precheck base trees: `canary-base-20261110` and its nested `T-0147-120`, `canary-base-e302119`, `canary-process-0004`, `canary-process-verify`, `clean-head-20261110` |
| `.claude/worktrees/` | 1 | `agent-a8ea164055f940daf` |
| `%TEMP%` | 12 | **10** `pmk-merge-*` merge scratch trees + **2** `pmk-precheck-dry-bje5ewal` base/scratch — the subject of **H7** |
| **Total** | **28** | 1 + 8 + 6 + 1 + 12 = 28 ✓ |

**Correction — the canary was unnecessary, and my earlier advice to run one was wrong.**

§A.9's step list and `HANDOFF.md`'s next-actions said to run a fresh supervised canary "for `DoD-6`". **That is not required.** `DoD-6` has been **PASS** since earlier on 2026-11-11: fresh `T-0196` reached `DONE` at base `9bb0139` (merge `951d1ee`) and its bundle carries a non-empty `gate_output` — verified this session from `.pm/evidence/EB-T-0196-159/bundle.json`: `cmd: pytest -q`, `exit: 0`, `ok: true`, populated `stdout_tail`. The original proof `T-0191` / `EB-T-0191-158` is intact, and `OQ-04`/`R-14` are recorded closed.

The operator did run one, and it **refused — by design, not as a defect**:

```json
{ "error": "canary_requires_exactly_one_ready", "count": 13, "ready": [ "T-0193", "…", "T-0211" ] }
```

`run_canary` (`src/fleet/canary.py:55-60`) requires **exactly one** `READY` card and raises `canary_requires_exactly_one_ready` otherwise; the project has 13. The check runs **before** the dispatch-owner lock is taken and before `CANARY_STARTED`, so the refusal wrote no event and left no partial state. **No canary is owed.**

**Derived — a side effect worth naming.** Revoking a lease returns its card to `READY` (`REVOKED` → `READY`, or `BLOCKED` if attempts are exhausted) — the same semantics that made §A.13's first candidate fix wrong. So CP-2 (revoking `T-0210`/`T-0211`) moved those two cards back into the queue: `READY` went **11 → 13**, now `T-0193`–`T-0195`, `T-0199`, `T-0200`, `T-0202`–`T-0207`, `T-0210`, `T-0211`. Separately, `project resume` (run to clear the way for the canary) set `project_state: RUNNING`; the canary then refused, so the project is now **`RUNNING` with no dispatch owner**. Whether to pause or to dispatch is an operator decision; H1's `lease_incomplete` half is dormant while `RUNNING`, by design.

**Corrections to earlier sections.**

| # | Earlier statement (section) | Correction |
|---|---|---|
| 1 | §A.14 Standing: "CP-3 can now be completed … Chain verifies at 3,640 events; project `PAUSED`" | **Superseded.** CP-3 is complete (above); chain verifies at **3,644 events**; project is **`RUNNING`**; `active_leases: 0`. |
| 2 | §A.9 step list / `HANDOFF.md` next-actions: run a fresh canary for `DoD-6` | **Withdrawn.** `DoD-6` was already PASS (`T-0196`); the canary refused by design. See above. |
| 3 | Body §Verdict point 5 and §9 step 11: "CP-3 … remain unexercised" | **Partly superseded.** CP-3 is exercised and complete; **CP-4** (ratification) alone remains of that pair. |
| 4 | Plan `DoD-3` / `DoD-4` rows: `_pending_` | **Corrected** in the plan. `DoD-3` **PASS** (tool exit 0); `DoD-4` **reconciled** (28 = 1 + 8 + 6 + 1 + 12). |

**Standing after this verification.** HEAD `a1d301c`, 0 behind / **137** ahead of `origin/main`. 212 cards: **156 VOID**, **43 DONE**, **13 READY**; `active_leases: 0`; chain verifies at **3,644 events**; `pmk sentinel` → `ok: true`, no findings; `work/` holds exactly **8** non-lease trees. **`DoD` PASS: DoD-1, DoD-2, DoD-3, DoD-4, DoD-5, DoD-6.** Still open: `DoD-7` (decision at the next free id), `DoD-8` (§14 matrix), `DoD-9` (§8 ticked); the unlanded hardening items **H3/H4/H7** (`T-0193`/`T-0194`/`T-0195` are READY); reviewer items 2–4 (the authority gate, unblocked by Decision **B = A**); and **CP-4** (ratify D-72 + its erratum and D-74; record `T-0189` as superseded by `T-0190`, not exonerated). Push is operator-only.

## A.16 The human-authority gate, and a concurrent writer in the tree (2026-11-12)

**Scope.** This section records the authority-gate work authorised on 2026-11-11 (reviewer items 2–3, plus item 4's answer), and a **concurrent-writer finding** discovered while doing it. The gate is uncommitted when written; the concurrent commits are not mine.

### A.16.1 What was built — one shared gate

`src/pmk/authority.py` (new) provides `require_human_authority(action, *, actor=None)`. It requires **both** a human identity (`PMK_ACTOR=human:<name>`, or an explicit `Actor(kind="human")`) **and** an interactive TTY (`sys.stdin.isatty()`, exposed as the seam `stdin_is_interactive`). Its refusal text does **not** say what to set.

| Requirement (event `seq 3630`, item 2) | Where it is enforced now |
|---|---|
| task void | `cli.cmd_task_void` |
| pins record | `cli.cmd_pins_record` (checked **before** the pins file is written) |
| class-K `queue_decide` | `Kernel.queue_decide` — only when the item is `class_k`; non-class-K keeps the agent path |
| `resume_dispatch` / `--resume` | `fleet.owner.resume_dispatch` (covers `pmk dispatch run --resume`, `pmk project run --resume`, the Console and the canary) |
| `pmk resume` (stop file — §6's "no check at all") | `cli.cmd_resume` |
| profile enable / disable / cooling | `cli.cmd_fleet_enable/disable/cool` |
| `cmd_agent_swap` | `cli.cmd_agent_swap` |
| `MANUAL_LAUNCH` | `console.app.api_launcher_launch` |
| item 3 — canary events | `fleet.canary.run_canary`: `CANARY_STARTED`/`CANARY_FINISHED` now record the **verified human**, or the run refuses |

**Deviation from the reviewer's own draft, recorded deliberately.** `tmp/reviewer-kernel` / `C:\temp\review-r15\kernel-actor-guards.diff` guard void, pins and class-K only, and their refusal text **names `PMK_ACTOR=human:<name>`** — which item 2 forbids ("the error text must not tell the caller what to set"). The requirement was followed, not the draft. The draft's class-K placement in `Kernel.queue_decide` was kept.

**Item 4 — Console.** Under Decision **B = A**, and the operator's follow-on decision of 2026-11-12 (**terminal-only everywhere**), every privileged Console action refuses with HTTP **403** and points at the terminal: `/api/project/run`, `/api/fleet/{enable,disable,cool}`, `/api/launcher/launch` (MANUAL_LAUNCH) and a class-K `/api/queue/decide`. The Console's no-auth monitoring role is unchanged. **This is a governance decision and should be recorded** (next free id `D-75`).

**One canary at a time** is already enforced structurally: `run_canary` takes the shared `DispatchOwner` lock as role `canary`, so a second owner is refused with `dispatch_owner_busy` before any event. No new mechanism was needed.

### A.16.2 Evidence

| Check | Result |
|---|---|
| Full gate (`python -m pytest -o addopts="" -q`) | **1332 passed, 1 skipped, 0 failed** (845.21 s) |
| New gate module | `tests/pmk/test_authority_gate.py` — **18 tests** |
| Existing tests adjusted (guard incidental to what they check) | `test_tasks.py` (2), `test_canary_runner.py` (1 + 2 new), `test_console_dispatch.py` (3 + 2 new), `test_dispatch_owner.py` (1) |
| `python tools\check_subprocess_env.py` | `ok` (7 allowlisted), exit 0 |

The tests drive the TTY seam (`pmk.authority.stdin_is_interactive`), never the live tree. **The gate is a boundary against the path of least resistance, not authentication** — any caller with Kernel access can still construct `Actor.human()` (as `Kernel.task_void`'s docstring already says); what it removes is every CLI/Console route that turned an unset or worker environment into a recorded human act.

### A.16.3 Finding — a concurrent writer advanced HEAD during this work

**Confirmed.** While this section was being written, `HEAD` moved `c8ac36b` → `33b9911` → `772e1bc`, by commits **I did not make**:

| Commit | Contents | Reading |
|---|---|---|
| `33b9911` "overdue commit" (2026-11-12 01:00) | `src/fleet/dispatcher.py`, `src/fleet/harness.py`, `src/console/app.py`, `src/pmk/worktrees.py`; new `tests/fleet/test_reconcile_startup.py`, `tests/fleet/test_model_attribution.py`, `tests/pmk/test_prune_merge_trees.py` | maps onto **H3** (reconcile at startup) and **H4** (model attribution) |
| `772e1bc` "feat(pmk): reclaim non-lease scratch worktrees, capture-first (completes **H7**)" (2026-11-12 09:12) | `src/pmk/cli.py`, `src/pmk/events.py` (`WORKTREE_SCRATCH_PRUNED`), `src/pmk/worktrees.py` (`scratch_records`, `merge_tree_records`, `prune_scratch`), `tests/pmk/test_worktree_lifecycle.py` (`+167`) | **H7** landed directly |

Both are authored `umaws-pilot <umaws-pilot@localhost>`. **This is reviewer item 1's situation recurring**: the live tree is being edited and committed by an actor whose session the log does not identify. It is reported, not judged — the work appears coherent and I did not touch it.

**Consequences for this section's evidence, stated plainly.** The gate run above executed on the working tree that already contained the H3/H4/H7 content now committed as `33b9911`/`772e1bc` (their `worktrees.py` was last written 09:08, before the run; `events.py` 08:56). So the 1332-pass figure covers **HEAD `772e1bc` plus this uncommitted gate change** — not `c8ac36b` alone, and not my change in isolation. `src/pmk/cli.py` is the one file both changes touch; my staged diff there is the nine authority hunks only, and their H7 command survives intact.

### A.16.4 Ruling — reviewer item 1 (2026-11-12)

**Ruling: `Unknown`, with the candidate sessions named as leads. No attribution is claimed.** The reviewer asked which session edited the live tree. The event log cannot answer: the concurrent session's own kernel-visible acts were recorded with `actor.kind = "kernel"` — the two `WORKTREE_SCRATCH_PRUNED` events at seq 3645–3646 — exactly as the CLI and the fleet record their own machine actions. Codex holds **no** thread whose cwd is this project. The only store that names anything is opencode's own `session_v2`:

| session id | created | last active | title | near |
|---|---|---|---|---|
| `ses_e3594395bffeG69voW7h1A7G1z` | 2026-11-12 00:43:43 | 2026-11-12 00:59:38 | "Repair UMAWS Fleet Launcher" | `33b9911` at 01:00:12 |
| `ses_e33d5d742ffeyUXspljUKRJfHd` | 2026-11-12 08:51:17 | 2026-11-12 09:49:53 | "worktree reuse" | `772e1bc` at 09:38:28 |
| `ses_e36a6c389ffeNrqWTGaCBFQv9t` | 2026-11-11 19:43:51 | 2026-11-12 10:48:03 | "No Scope UMAWS Fleet Launcher scope proposal" | — |
| `ses_e3904492dffeW5Kb59Qb82kq2e` | 2026-11-11 08:42:27 | 2026-11-12 10:54:22 | "REPAIR UMAWS Fleet Launcher repair status" | — |

**Derived, not confirmed.** Two sessions are *temporally adjacent* to the commits and are the best available leads; the mapping is not provable (a store row cannot be bound to a commit), and the list does not distinguish the operator's own sessions from the concurrent one. §A.3's correction stands and is now demonstrated twice: an event log records events, not editor sessions, and cannot be made to name one after the fact. Read-only probes: `tmp/probe_sessions_t1.py`, `tmp/probe_sessions_wide.py`, `tmp/probe_codex_threads.py`.

### A.16.5 Standing

The authority gate is **committed as `803feb9`** (12 files, `+586/−42`); the concurrent session's `worktrees.py`/`events.py` were **not** mine and were left alone. Reviewer **items 2 and 3 are implemented** (were *Absent* / *Partial*); item 4 is answered (**Decision B = A**, and the Console is now terminal-only — `D-75`); item 1 is **Unknown (final, with leads)** above; item 5 remains open and item 6 is editorial. `D-75` is drafted, so **`DoD-7` is PASS**; `DoD-8` and `DoD-9` remain.

**Also confirmed.** `T-0193`/`T-0194` (H3/H4) and `T-0195` (H7) are **landed and wired** (`33b9911`; `772e1bc`, refined by `e477c5f`) but their cards still read `READY` — the §A.8 disagreement once more. `T-0195`'s landed diff also touches `cli.py` and `test_worktree_lifecycle.py`, which are that card's **read** scope (§A.7 shape). Dispatch is **unpaused** (`dispatch_paused: false`) with `project_state: RUNNING` and 13 `READY` cards, so the stale cards should be retired before anything takes the dispatch line.

## A.17 Second batch — DoD-8/DoD-9, reviewer item 5, and the two gate fragilities (2026-11-12)

### A.17.1 Gate fragilities 3 and 4 — fixed and proven

| Fragility | Cause | Fix |
|---|---|---|
| **3** — a relative `-Python` is unresolvable | the script `Push-Location`s into the detached worktree before invoking `$Python`, so a relative path (or a bare name) resolved against the wrong directory | `tools/check_clean_base.ps1` now resolves `$Python` with `Get-Command` **before** any location change, and throws a clear message if it cannot |
| **4** — the gate log carried no count line | `addopts = -q` in `pytest.ini` **and** `pyproject.toml`, plus the script's own `-q`, ran pytest at effectively `-qq`, suppressing the summary | the gate now runs `pytest -o addopts="" -q`, clearing the config `addopts` and keeping a single `-q` |

**Confirmed.** Run end-to-end from the repository root with a **relative** `-Python`:

| Observation | Reading |
|---|---|
| `clean-base gate exit=0 sha=35e4bdc7bd791386bca5c8d93337971dca9ba187` | green at HEAD |
| Log line `1261 passed, 1 skipped in 435.58 s` | **the count line is now in the log** — the §A.11 gap is closed |
| Import lines resolving inside `umaws-gate-20261112-113728` | no editable-install shadowing |
| `-Python no-such-python-xyz` | throws `python not found: … pass -Python with an absolute path` and exits 1 without creating a worktree |

The working tree still collects **1333** against the clean tree's **1261**; the 72-test gap is the uncommitted CNA material exactly as §A.11 attributed it. Note the deltas also confirm §A.16's caveat: the clean tree here is `35e4bdc`, which now contains H3/H4/H7.

### A.17.2 `DoD-8` and `DoD-9` — PASS

- **§14 (OQ/R traceability)** now carries a measured **`Status 2026-11-12`** column beside the preserved `Status at synthesis`. Every in-scope item is **CLOSED**, **RECORDED** and deferred to CP-4 with its reason (OQ-07, OQ-08, OQ-12), or marked **n/a** (the P/F/S registers). `OQ-09` (reconcile unwired) and `OQ-11` (empty attribution) closed by `33b9911`; `OQ-05` (census/merge trees) by `35e4bdc`+`e477c5f`; `OQ-10` (documentation drift) is closed **in scope** — the owed errata are written and the residual staleness is named, not silently dropped. → **`DoD-8` PASS.**
- **§8 (irreversible actions)** now carries a measured **`Status 2026-11-12`** column. Six rows are satisfied, one is **not applicable** (the H-items landed directly, so no card bundle exists — recorded as a deviation, §A.16.5), one is an explicit **Unknown** (no CP-1 record was located this session), and one is satisfied as a draft (`D-75`). → **`DoD-9` PASS**, per its own "or an explicit `Unknown` / not-applicable note" clause.

### A.17.3 Reviewer item 5 — already delivered; one presentational gap

A corrected, **genuine `git format-patch`** already exists and meets all four clauses:

| Clause | Status in `tmp/canary-process/0004-gate-timeout-all-gates.patch` |
|---|---|
| (a) deliver as `git format-patch` | **met** — `From 3e9c6bcc… Mon Sep 17 00:00:00 2001`, `Subject: [PATCH] fleet: budget every merge gate and record gate evidence`; `git apply --check` exits 0 against the current tree |
| (b) rename `canary_gate_timeout_s` | **met** — `gate_timeout_s` / `DEFAULT_GATE_TIMEOUT_S`; the old name is **absent from the live tree** entirely (it existed only inside the raw patch and `tmp/review-followups/`) |
| (c) docs say "12.5–15 minutes, unknown" | **met** — the card and runbook hunks read "*the gate ran between 12.5 and 15 minutes, unknown*" |
| (d) remove "too tight" | **met** — **0** occurrences in the corrected patch; in the live tree the phrase survives only in `docs/sources/umaws.md:856`, about *envelopes*, not the gate |

**Two things are not done, and I am not doing them unilaterally.** The reviewer's own `tmp/reviewer-patches/patches-rebased/0004-rebased.patch` is **still the raw diff** — it is another actor's artifact (A-14: cite, do not modify), so I left it; delivering the corrected file under that exact name is a copy the operator should authorise. And the **live** `pilot/cards/canary-replacement-v1.md:139` still asserts "gate ~ 4 minutes (measured 3 m 59 s …)" — the figure the reviewer says was the failed T-0148 gate. Applying `0004` fixes it, so I did **not** pre-empt that hunk; whether to apply `0004` (it also adds the fleet setting) is an operator decision.

### A.17.4 Standing

`DoD` **PASS: DoD-1 … DoD-9** — all nine. Reviewer track: item 1 `Unknown (final, with leads)`; items **2 and 3 implemented**; item 4 answered (`D-75`); item 5's substance delivered (above); item 6 editorial. Open and operator-only: the `T-0193`–`T-0195` discharges, CP-4 ratification, applying `0004`, and the push.

---

**Author:** DeepSeek V4.1 Flash Free — `opencode/deepseek-v4.1-flash-free`. Authored both the report and this addendum, including §A.15, §A.16 and §A.17; no independent assessment of either exists, and no `assessor_llm` is claimed.
**Status of this addendum:** advisory verification record. It grants no authority, ratifies nothing, promotes nothing, and changes no kernel state beyond the code recorded in §A.14 and §A.16 and the two `tools/` fixes in §A.17.1.
**Storage:** the report through §A.16 is committed (`b2fe947`, `afcc0ba`, `2a579dd`, `a1d301c`, `c8ac36b`, `803feb9`); **§A.17 was uncommitted when written** and is staged with the `tools/check_clean_base.ps1` fixes. Folding the report into a decision record remains an operator decision.
