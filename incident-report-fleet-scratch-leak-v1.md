---
document:
  title: "Incident Report: Fleet Scratch-Directory Leak in the Global Temp Namespace (pmk-precheck-*, pmk-merge-*, pmk-precheck-dry-*)"
  status: "Open - remediation complete for this repository and the operator-approved follow-ups implemented (R-08/R-09/R-10/R-12, commit 05864ad); the R-13 first-pass assessment is recorded in Appendix D and the author's re-verification in Appendix E (ACCEPT WITH CORRECTIONS; three corrections applied, four numeric corrections refuted on re-verification); the global %TEMP% husk family was still growing from umaws-noscope-toy at 20:06, and the foreign precheck has now been patched; deferred items in section 10; pending integration into the final system report (not yet published; system incomplete)"
  version: "1.2.1"
provenance:
  author_llm:
    name: "Step 5 Preview"
    version: "stepfun-ai/step-5-preview (nvidia)"
  created_date: "2026-11-12"
  last_modified_date: "2026-11-12"
  scope: "C:\\temp\\projects\\testproject1 (branch main), src/fleet/merge.py, src/fleet/precheck.py, src/fleet/scratch.py (new), src/pmk/worktrees.py, src/pmk/cli.py, tests/fleet/ (conftest and test_scratch.py), tests/pmk/test_worktree_lifecycle.py, the global %TEMP% families pmk-precheck-*, pmk-merge-* and pmk-precheck-dry-*, tmp/ under the repo root, stranded/ captures, the Kernel event log, and the measured test runs recorded below"
  source_of_truth: "The append-only event log at .pm/events/*.jsonl (I1 hash chain verifies, 3655 events at writing; 3657 after the assessment's sentinel/pins runs; the files are tracked as of commit 80223ff) is authoritative for coordination state; git objects at HEAD 05864ad (code) / 9f1a025 (report) are authoritative for code; filesystem measurement is authoritative for disk usage; the captures under stranded/ are authoritative for reclaimed content. Where this report and any briefing disagree, the event log and the git store win."
  related_documents:
    - "incident-report-worktree-lifecycle-leak-v1.1.md (the parent incident: lease worktrees, stranded work, task churn)"
    - "proposal-deepseek-umaws-fleet-worktree-lifecycle-remediation-v1.md (REC-01/02/04/06/11/13 remediation)"
    - "remediation-worktree-scratch-prune-report-v1.md (the operator run that reclaimed work/ and pmk-merge-* scratch)"
    - "remediation-fleet-scratch-leak-report-v1.md (working note; its content is absorbed and superseded by this report)"
    - "remediation-rec02-capture-verification-note-v1.md (REC-02 capture/verify design)"
    - "incident-report-worktree-isolation-v3.md (section 8 - the R-12 report standard this report follows; section 9 - R-13 review process)"
  reviewer: "R-13 first pass: COMPLETED 2026-11-12 by Claude 3 Opus 20240229 (claude-3-opus-20240229; confirmed by the operator — an Orchestrator LLM launched Claude as the assessor in the background), verdict ACCEPT WITH CORRECTIONS — the raw assessment artifact is missing, so the 14 findings are only partly recorded. Its findings, and the author's re-verification of each one (four numeric corrections refuted; three corrections applied: A-5 and A-6 numeric, A-8 non-numeric), are recorded in Appendix D and Appendix E. SECOND PASS COMPLETED 2026-11-12 by ERNIE 5.5 Flash Preview (openrouter/baidu/ernie-5.5-flash-preview:free), verdict ACCEPT WITH CORRECTIONS — see assessment-ernie-5-5-incident-report-fleet-scratch-leak-v1.md."
  assessor_llm:
    name: "Claude 3 Opus 20240229"
    version: "claude-3-opus-20240229"
  assessor_note: "Confirmed by the operator: an Orchestrator LLM launched Claude as the assessor in the background. The raw assessment artifact is still missing; the 14 findings are only partly recorded."
  assessed_date: "2026-11-12"
  editor_llm: "Step 5 Preview (the author) - applied the v1.1 amendments and re-verified the assessment's findings; NOT an independent assessor. The v1.2 factual corrections were applied by ERNIE 5.5 Flash Preview (assessor) with the author's provenance preserved; see assessment-ernie-5-5-incident-report-fleet-scratch-leak-v1.md. v1.2.1 is the author's own label correction only (Appendix D's heading now matches its content); no factual claim changed."
  corrections_applied: "A-5, A-6, A-8 (Appendix D); factual corrections C-1 through C-15 in assessment-ernie-5-5-incident-report-fleet-scratch-leak-v1.md"
  corrected_date: "2026-11-12"
  second_pass: "ERNIE 5.5 Flash Preview (openrouter/baidu/ernie-5.5-flash-preview:free), 2026-11-12"
---

# Incident Report: Fleet Scratch-Directory Leak in the Global Temp Namespace

**Author:** Step 5 Preview (`stepfun-ai/step-5-preview`, nvidia) - **v1.2.1** (v1.1.0 assessed; v1.2.0 factual corrections applied by the second-pass assessor, provenance preserved; v1.2.1 is the author's own label correction)
**Report ID:** `incident-report-fleet-scratch-leak-v1`
**Date:** 2026-11-12
**Status:** **Open.** Remediation is complete **for this repository** — root cause fixed, the sanctioned reclaim surface extended, both operator-approved runs verified — and the follow-ups the first assessment identified are implemented (`05864ad`). The first pass is recorded in Appendix D; the author's re-verification is in Appendix E; the second pass is recorded in `assessment-ernie-5-5-incident-report-fleet-scratch-leak-v1.md`. **The global `%TEMP%/pmk-precheck-*` family was still growing from `umaws-noscope-toy` at 20:06; the foreign precheck is now patched, and existing old-code processes may produce a few more husks until they exit.** Outstanding: the deferred items in section 10.
**Repository state at writing:** HEAD `05864ad` for code (the report was committed as `9f1a025`), event log 3655 events at writing (3657 after the assessment's sentinel/pins runs; I1 chain verifies), `stranded/` 123 captures, `tmp/` 74.27 MiB / 25 directories, `work/` 0 worktrees, full test suite **1360 passed / 1 skipped** (working-tree run, recorded at `.pmwork/umaws-full-suite-2026-11-12.xml`; the clean-base totals are 1276/1282/1289, i.e. 1275/1281/1288 passed with 1 skipped — see §6.2), `sentinel check` ok (0 findings), `pmk pins check` unaffected (only `.pm/constitution.md` and `.pm/policy.toml` are pinned, and neither was modified).
**Timestamps:** all times are UTC unless a local (NZDT, UTC+13) time is named.

---

## 1. Executive Summary

The fleet built every throwaway directory with `tempfile.mkdtemp(prefix=...)` in the **global** temp namespace and leaked them in three distinct ways. The largest was not the one suspected: `precheck.oracles_already_pass()` (called on every lease admission by `src/fleet/harness.py:315`) added a worktree, ran the oracles, removed the *worktree*, and never removed the directory around it — **412 empty `pmk-precheck-*` husks accumulated over four days and were still growing**, one per claim, with nothing in the system able to collect them. Second, `shutil.rmtree(path, ignore_errors=True)` silently fails on Windows whenever a file *or a directory* in the tree is read-only, which git leaves; verified on this machine, the old call left the tree behind in **4 of 4** read-only arrangements, so whole `pmk-merge-*` and `pmk-precheck-dry-*` trees survived a run that was killed or merely unlucky. Third, nothing owns the global namespace: a leftover whose repository is gone cannot be proven to belong to this project — `pmk.worktrees.prune_scratch` deliberately refuses a merge tree it cannot prove is ours — so every leftover from a run that died was permanent.

The fix puts the class in one place. `src/fleet/scratch.py` now owns the fleet's throwaway directories: `scratch_dir(prefix, temp_root)` places them where the caller says (a pytest-managed `tmp_path` in tests, the global temp in production) and `remove_scratch(path)` clears the write-protect bit on every file and directory before removing, and **returns whether anything is left** instead of swallowing the outcome. `integrate()`, `dry_run()` and `oracles_already_pass()` all take `temp_root` and use it, and the precheck's `finally` now also covers its early refusal path. One autouse fixture in `tests/fleet/conftest.py` keeps every fleet test's scratch inside the test's own `tmp_path`, so no test — present or future — litters the global namespace. The sanctioned reclaim surface was extended with `pmk worktree prune --precheck-trees`, gated exactly like the merge class (ownership proven by `belongs_to_repo`, age-gated, capture-first).

Two operator-approved reclaims were then run and verified: the stale `pmk-precheck-dry-*` directory (2/2 worktrees, **29.85 MiB freed**, both archives verify, the modified `src/pmk/worktrees.py` and the untracked `tests/pmk/test_prune_merge_trees.py` captured rather than discarded) and the six registered canary worktrees under `tmp/` (6/6, **97.91 MiB freed**, all six archives verify, the five tracked files and the reviewer-agent trees untouched). This repository's fleet no longer produces husks: no husk is attributable to it after 16:58 local. The global `%TEMP%/pmk-precheck-*` family did **not** stop at 20:06 — it was 467 and still growing from `umaws-noscope-toy`'s pre-fix `src/fleet/precheck.py` — but the foreign precheck has now been patched, so new processes should not add husks; existing old-code processes may add a few more until they exit.

---

## 2. Scope, Method and Non-Actions

### 2.1 Questions this report answers

1. What was leaking, how much, and how fast?
2. What was the root cause of each leak, with file and line?
3. What was changed, and how was each change verified?
4. What is deliberately left alone, and why?
5. What must be done to stop this recurring (safeguards, recommendations, unresolved items)?

### 2.2 Method

* Read-only measurement of the global temp families (`pmk-precheck-*`, `pmk-precheck-dry-*`, `pmk-merge-*`), `tmp/`, `work/` and `stranded/`, with ownership read from each worktree's `.git` file.
* Source reading of `src/fleet/merge.py`, `src/fleet/precheck.py`, `src/pmk/worktrees.py` and their callers (`src/fleet/harness.py:315`, `src/fleet/conductor.py:401`, `src/pmk/cli.py`).
* An **empirical probe** of the cleanup claim rather than an assertion: on this machine, `shutil.rmtree(dir, ignore_errors=True)` versus `fleet.scratch.remove_scratch` across four read-only arrangements (read-only file, read-only subdirectory, read-only root, read-only throughout).
* **Attribution by private temp root**: the merge and precheck suites, and then all of `tests/fleet`, were run with `%TEMP%` redirected to a private directory, so any `pmk-*` directory left in that root is provably from that run and nothing else.
* The event log (I1 chain verifies, 3655 events) for coordination state, and `git worktree list` / `.git/worktrees` for registrations.

### 2.3 Explicit non-actions

* No other project's tree was touched except the operator-authorized fix to `umaws-noscope-toy/src/fleet/precheck.py` (it now removes its `pmk-precheck-*` directory in a `finally`, clearing read-only bits; 10 precheck tests pass, 0 leaked). At report writing one live `pmk-merge-*` directory was attributed to `umaws-noscope-toy`; at assessment the live-looking directory (`pmk-merge-fy5t4h9d`) points at a test repository (`tmpjegemeia/repo`), and the `umaws-noscope-toy` merge was not present. The ownership gate skips any directory it cannot prove is ours.
* The 467 husks at 20:06 local, the 13 orphan/empty `pmk-merge-*` shells, the three reviewer-agent trees under `tmp/`, the five tracked files under `tmp/`, and `.claude/worktrees/agent-a8ea…` were **not** deleted (section 10).
* Other agents' uncommitted work in the shared working tree (`src/cna/**`, `docs/**`, `.pm/views/*`) was not committed by any of the three commits in this report.

### 2.4 Known limitations

* Disk figures are point-in-time; the global families move while other projects run.
* A process that started before the fix keeps the old module in memory (the venv is an editable install), so a small number of husks appeared after the commit until those processes exited. This is stated precisely in the timeline rather than rounded away.
* The one-off `tmp/` reclaim was driven by a script through the sanctioned deletion path; it therefore wrote **no** kernel event (see U-6).

---

## 3. Incident Timeline

| # | When (UTC) | Local | Event | Evidence |
|---|---|---|---|---|
| 1 | 2026-11-08 08:13 | 21:13 | Oldest surviving `pmk-precheck-*` husk — earliest evidence of the leak's start | filesystem (`pmk-precheck-bv22_gmc`) |
| 2 | 2026-11-11 21:03:07 | 10:03 | `WORKTREE_SCRATCH_PRUNED` seq 3645 — 8/8 non-lease `work/` trees reclaimed | event log |
| 3 | 2026-11-11 21:03:39 | 10:03 | seq 3646 — 10/10 `pmk-merge-*` trees reclaimed, 15 skipped (not provably ours) | event log |
| 4 | 2026-11-12 02:30–02:40 | 15:30–15:40 | Measurement discovers the husk class: **412** `pmk-precheck-*` husks (still growing every ~5 min), 14 `pmk-merge-*` dirs, 1 content-bearing `pmk-precheck-dry-*` (29.85 MiB, this repo's) | filesystem, `harness.py:315` |
| 5 | 2026-11-12 02:36 | 15:36 | One `pmk-merge-*` shown to be a **live merge of `umaws-noscope-toy`** — the ownership gate's justification, observed live | `.git` file contents |
| 6 | 2026-11-12 ~03:00–03:30 | 16:00–16:30 | Root cause confirmed by probe and by reading; `src/fleet/scratch.py` written; `merge.py`/`precheck.py` converted | commits below |
| 7 | 2026-11-12 03:31:13 | 16:31 | **`0e51b98`** — root-cause fix committed (6 files, +470/−22) | git |
| 8 | 2026-11-12 03:48 | 16:48 | `tests/fleet` under a private `%TEMP%`: **302 passed, 0 `pmk-*` leaked** | run output |
| 9 | 2026-11-12 04:04:32 | 17:04 | **`307531f`** — `--precheck-trees` extension committed (+236/−22) | git |
| 10 | 2026-11-12 04:04:54 | 17:04 | **seq 3655** `WORKTREE_SCRATCH_PRUNED` — 2/2 precheck worktrees reclaimed, 29.85 MiB freed | event log |
| 11 | 2026-11-12 ~04:10–04:20 | 17:10–17:20 | One-off capture-first reclaim of the six registered `tmp/` canary worktrees — 6/6, 97.91 MiB freed | script output, `stranded/` |
| 12 | 2026-11-12 04:22:54 | 17:22 | **`30d27b1`** — working report v1.1.0 committed | git |
| 13 | 2026-11-12 04:22 | 17:22 | Full suite re-gate: **1353 passed, 1 skipped** (dirty tree; clean-base `307531f` is 1282 total / 1281 passed) | `umaws_junit_precheck.xml` |
| 14 | 2026-11-12 04:30 | 17:30 | Live check: 445 husks total at 17:30; **at 20:06 local the family was 467 and still growing from `umaws-noscope-toy`'s pre-fix code**; no husk is attributable to this repository's fleet after 16:58 local | filesystem, process list |
| 15 | 2026-11-12 ~05:00 | ~18:00 | R-13 first-pass assessment returned (Claude 3 Opus 20240229, confirmed by the operator; orchestrator-launched; raw output missing): ACCEPT WITH CORRECTIONS; three corrections accepted after re-verification (A-5, A-6, A-8), four refuted on primary evidence | Appendix D; author re-verification in Appendix E |
| 16 | 2026-11-12 05:25:55 | 18:25 | **`05864ad`** — the operator-approved follow-ups implemented (R-08 guard, R-09 test-setup sites, R-10 examination recorded, R-12 `pmk worktree reclaim`) | git |
| 17 | 2026-11-12 05:32 | 18:32 | Recorded full-suite run: **1360 passed, 1 skipped, 0 failures** (`tests/fleet` 303, `tests/pmk` 284; working tree — clean-base `05864ad` is 1289 total / 1288 passed) | `.pmwork/umaws-full-suite-2026-11-12.xml` |
| 18 | 2026-11-12 ~05:40 | ~18:40 | This v1.1 amendment: corrections applied, assessment recorded, statuses updated | this file |

---

## 4. Root Cause Analysis

### RC-1 (primary) — the precheck removed the worktree but never its directory

`src/fleet/precheck.py:39` created `Path(tempfile.mkdtemp(prefix="pmk-precheck-"))` and the `finally` at `src/fleet/precheck.py:57-59` (pre-fix) ran only `repo.git("worktree", "remove", "--force", str(worktree))`. `git worktree remove` deletes the worktree directory and its contents, leaving the mkdtemp parent behind — an empty husk. The caller, `src/fleet/harness.py:315` (`precheck_mod.oracles_already_pass(self.kernel, task)`), runs on **every lease admission**, so the husk rate equals the claim rate. **412 husks in four days, ~0 bytes each, uncollectable.** Fixed in `0e51b98`: the `finally` now also runs `scratch.remove_scratch(temp_dir)`, and the `try` was widened so the early "could not add the worktree" refusal is covered too.

### RC-2 (primary) — cleanup that cannot report failure

Both call sites used `shutil.rmtree(path, ignore_errors=True)` (`src/fleet/merge.py:425`, `src/fleet/merge.py:487`, `src/fleet/precheck.py:157` — pre-fix line numbers; the current lines are 430, 492 and 167). On Windows this raises internally and swallows whenever a file **or a directory** in the tree carries the read-only attribute, which git leaves. Probe result on this machine: the tree survived in **4 of 4** arrangements (read-only file / read-only subdir / read-only root / read-only throughout). A killed process cannot run a `finally` at all, which is the other half of the same defect: nothing recovered the leftovers afterwards. Fixed by `fleet.scratch.remove_scratch`, which clears `S_IWRITE` on every file and directory deepest-first (root included) and returns a fact.

### RC-3 (secondary) — the scratch lived in a namespace with no owner

`tempfile.mkdtemp` defaults to the global temp directory, which every project using `pmk` and every concurrent test run shares. Once the repository a leftover belonged to is deleted (a pytest basetemp is garbage-collected), the leftover's ownership becomes **unprovable** — `belongs_to_repo` cannot resolve a common git dir — and the sanctioned collector refuses it. 13 of the 14 `pmk-merge-*` directories were exactly this: orphans pointing at deleted pytest basetemps from 2026-10-25 to 2026-11-12. Fixed for tests by the autouse fixture (scratch lives in the test's `tmp_path`, which pytest removes) and for operators by the ownership-gated collectors (`--merge-trees`, `--precheck-trees`); production behaviour is deliberately unchanged.

### RC-4 (secondary) — no observation covered the `%TEMP%` families

The only worktree invariant, `I17` (`src/pmk/sentinel.py`), observes `work/` alone (size cap and age from `.pm/policy.toml`) and is deliberately report-only. Nothing counted or aged the `%TEMP%` families, so a leak in them was invisible to every gate the project runs. **Not fixed** — carried as recommendation R-07.

### Causal chain

Lease admission → `oracles_already_pass` → mkdtemp in global temp → worktree added, oracles run, worktree removed, **directory left** → husk #N. In parallel: merge/precheck paths whose `rmtree(ignore_errors=True)` fails on read-only files, or whose process is killed, leave whole trees; those trees' repositories eventually disappear; ownership becomes unprovable; the trees are permanent.

---

## 5. Findings Table

| ID | Finding | Status |
|---|---|---|
| F-1 | `oracles_already_pass` never removed the directory around its worktree; 412 husks, one per lease admission, growing at measurement time | **Resolved** (`0e51b98`) |
| F-2 | `shutil.rmtree(..., ignore_errors=True)` hid Windows read-only failures; probe: 4/4 arrangements leaked | **Resolved** (`0e51b98`) |
| F-3 | Fleet scratch lived in the unowned global namespace; leftovers from dead runs became permanently uncollectable | **Resolved for tests** (autouse fixture); **mitigated in production** (ownership-gated collectors) |
| F-4 | A killed process cannot run its `finally`; merge/precheck leftovers survive a kill | **Mitigated** — tests can no longer leak globally; production kill leftovers are reclaimable when ownership is provable |
| F-5 | No sanctioned collector existed for stale `pmk-precheck-dry-*` directories | **Resolved** (`--precheck-trees`, `307531f`) |
| F-6 | One stale dry-run directory (29.85 MiB, two registered worktrees, two modified files) was sitting in `%TEMP%` | **Resolved** — reclaimed 2/2, both archives verify (seq 3655) |
| F-7 | Six stale registered canary worktrees under `tmp/` held 112.64 MiB (97.91 MiB net of the nested tree) | **Resolved** — reclaimed 6/6 capture-first, all archives verify |
| F-8 | Test-setup helpers leak unprefixed global temp directories: `tests/fleet/test_merge_queue.py:32`, `tests/fleet/test_oracle_lint.py:296`, `tests/fleet/test_load_agents.py:16,193,207` | **Resolved** (R-09 follow-up commit) |
| F-9 | `src/fleet/legacy.py:237` creates `llm_launcher_*` directories with the same unowned pattern; never examined | **Resolved - examined** (R-10: a different class, see section 7) |
| F-10 | No invariant or gate observes the `%TEMP%` scratch families (`I17` covers `work/` only) | **Open** — see R-07 |
| F-11 | A scripted one-off reclaim writes no kernel event, so the `tmp/` run is absent from the event log | **Resolved** (R-12: `pmk worktree reclaim <path>` records one) |
| F-12 | The husk and orphan-leftover families have no ownership proof and therefore no sanctioned collector | **Deferred by operator decision** — see U-1/U-2 |

---

## 6. Remediation and Testing

### 6.1 What changed

| File | Change |
|---|---|
| `src/fleet/scratch.py` (new, 83 lines) | `scratch_dir(prefix, temp_root=None)` and `remove_scratch(path)`; module docstring records the defect and the ownership reasoning |
| `src/fleet/merge.py` | `integrate()` gains `temp_root`; both `mkdtemp` sites and both `rmtree(ignore_errors=True)` sites go through `scratch` (retry path and outer `finally`); unused `shutil`/`tempfile` imports removed |
| `src/fleet/precheck.py` | `oracles_already_pass()` and `dry_run()` gain `temp_root`; the missing directory removal is added; the `finally` now covers the early refusal path; local `temp_root` name collision resolved |
| `src/pmk/worktrees.py` | `discover_precheck_trees()`; `prune_scratch()` gains the third class (`include_precheck`, `min_precheck_age_days`), per-worktree ownership and age gates, and `stem`/`worktree` bookkeeping |
| `src/pmk/cli.py` | `pmk worktree prune --precheck-trees`, and `include_precheck` in the `WORKTREE_SCRATCH_PRUNED` payload |
| `tests/fleet/conftest.py` | Autouse fixture `fleet_scratch_stays_in_tmp` — a default `scratch_dir` lands under the test's `tmp_path` |
| `tests/fleet/test_scratch.py` (new, 203 lines) | 9 regression tests |
| `tests/pmk/test_worktree_lifecycle.py` | 6 new cases for the precheck class (discovery, happy reclaim, not-ours refusal, too-recent refusal, no-worktree skip, CLI dry run) |

### 6.2 Test evidence

| Gate | Result |
|---|---|
| `tests/fleet/test_scratch.py` (new) | 9 passed at v1.0, 10 after the R-08 guard — includes the four read-only arrangements as parametrised cases |
| `tests/pmk/test_worktree_lifecycle.py` + `tests/pmk/test_prune_merge_trees.py` | 69 passed, 1 skipped |
| Merge + precheck suites under a **private `%TEMP%`** | 39 passed, **0 `pmk-*` leaked** |
| **All of `tests/fleet` under a private `%TEMP%`** | **302 passed, 0 `pmk-*` leaked** (the suite as it stood then) |
| Follow-up gate: `test_worktree_lifecycle.py` + `test_scratch.py` after R-08/R-12 | 83 passed, 1 skipped (7 new: the guard and 6 reclaim tests) |
| Full suite after the root-cause fix (`0e51b98`) — **clean checkout** | **1275 passed, 1 skipped** (1276 total; `.pmwork/umaws_junit_scratchfix.xml`). The earlier 1347 figure was a **dirty-tree** run that included ~71 untracked/uncommitted CNA tests. |
| Full suite after the `--precheck-trees` extension (`307531f`) — **clean checkout** | **1281 passed, 1 skipped** (1282 total; `.pmwork/umaws_junit_precheck.xml`). The earlier 1353 figure was the same dirty-tree run plus the 6 new precheck tests. |
| Full suite after the follow-ups (`05864ad`) — **working tree** | **1360 passed, 1 skipped, 0 failures** (1361 total) — `tests/fleet` 303, `tests/pmk` 284. The clean-base count is **1289 total** (1288 passed; 1282 + 7 new tests); the 1360 is the working-tree run, which includes ~71 untracked/uncommitted CNA tests. |
| Read-only probe (win32) | old call leaked 4/4; `remove_scratch` removed 4/4 |
| CLI smoke | `pmk worktree prune` default path exit 0; `--scratch --merge-trees --precheck-trees` exit 0, 15 skipped (13 orphan leftovers + 1 empty shell + 1 live test repo); `pmk worktree reclaim` refuses the main checkout and a plain directory with exit 0 |
| Governance | `sentinel check` ok, 0 findings; pins unaffected (only `constitution.md`/`policy.toml` pinned) |

### 6.3 The two operator-approved runs

**Run 1 — `pmk worktree prune --precheck-trees --yes`** (seq 3655): 2/2 reclaimed, 0 skipped. `%TEMP%/pmk-precheck-dry-bje5ewal` gone (29.85 MiB); 0 registrations remain and `git worktree prune -n -v` is silent; `stranded/` 115 → 117 with both archives verifying; the `scratch` capture carries a 1390-byte diff of `src/pmk/worktrees.py`, the untracked `tests/pmk/test_prune_merge_trees.py`, and 25 ignored files.

**Run 2 — the six registered `tmp/` canary worktrees** (scripted one-off through `worktrees.reclaim_after_capture`, deepest-first): 6/6 reclaimed, 0 kept. `tmp/` 172.18 → 74.27 MiB (**97.91 MiB freed**), 30 → 25 directories; 0 `tmp/` registrations remain; the five tracked files are intact; the three reviewer-agent trees and everything else under `tmp/` were not touched; `stranded/` 117 → 123 with all six archives verifying.

---

## 7. Recommendations and Safeguards

Status vocabulary per R-12: **implemented** / **documented** / **deferred**.

| ID | Recommendation | Purpose | Status |
|---|---|---|---|
| R-01 | One owner for fleet throwaway directories (`fleet.scratch`) | prevent a fourth mkdtemp site | **Implemented** (`0e51b98`) |
| R-02 | `temp_root` injection on every scratch-producing entry point | tests never touch the global namespace; callers can own cleanup | **Implemented** |
| R-03 | Cleanup that returns a fact (`remove_scratch`) | a failed cleanup can no longer be silent | **Implemented** |
| R-04 | Autouse fixture pinning fleet-test scratch to `tmp_path` | future tests cannot regress the leak | **Implemented** |
| R-05 | `--precheck-trees` collector, ownership + age gated, capture-first | stale dry-run leftovers are reclaimable, not permanent | **Implemented** (`307531f`) |
| R-06 | Regression tests for the helpers, the fixture, the static guard and both reclaim paths | the defect cannot return unnoticed | **Implemented** (22 tests) |
| R-07 | Extend the sentinel with a report-only observation over the `%TEMP%` `pmk-*` families (count, bytes, ownership-provable vs not), mirroring `I17` | the leak becomes visible to the project's gates | **Documented** (deferred by the operator: it touches invariants and policy keys) |
| R-08 | A mechanical guard that no `src/fleet` module creates or deletes scratch on its own: a test reads the source and fails on any `mkdtemp`/`mktemp`/`rmtree(..., ignore_errors=True)` outside `fleet.scratch` (one documented exception, `legacy.py`) | a new leak site fails the suite, not production | **Implemented** (in `tests/fleet/test_scratch.py`) |
| R-09 | Convert the test-setup `tempfile.mkdtemp()`/`mktemp()` sites to pytest-managed roots | removes the last unprefixed global leak from tests | **Implemented** (7 sites across 3 files) |
| R-10 | Examine `src/fleet/legacy.py:245` (`llm_launcher_*`; the pre-R-08 line was 237) for the same class | unknown until read | **Documented - examined**: a *different* class. The `.ps1` must outlive the call (a spawned console reads it), the rate is human-paced (73 dirs in three weeks), and the caller may pass `script_dir`. The reasoning is recorded in `legacy.launch_legacy`'s docstring so nobody "fixes" it by deleting a live script; the accumulation belongs to the R-13 hygiene policy |
| R-11 | Record in the project guidance that fleet scratch is created only through `fleet.scratch` | makes the rule greppable for future agents | **Documented** (partially enforced by R-08's guard) |
| R-12 | A CLI surface for a capture-first reclaim of an arbitrary path (`pmk worktree reclaim <path>`), so a one-off is an event, not a script | closes traceability gap F-11 | **Implemented** (`worktrees.reclaim_path` + the CLI, 6 tests; applied runs record `WORKTREE_SCRATCH_PRUNED` with `kind: "path"`) |
| R-13 | An operator-run machine-hygiene policy for unprovable leftovers (age-based, outside the repo) | prevents unbounded clutter the repo cannot own | **Documented** |
| R-14 | Treat a husk/orphan count in the pre-merge gate as advisory evidence in the final system report | keeps the residual visible until R-13 lands | **Documented** |

---

## 8. Current State

| Surface | State at writing |
|---|---|
| HEAD | `05864ad` for code (report committed as `9f1a025`; `0e51b98`, `307531f`, `05864ad` are the code commits) |
| Event log | 3655 events at writing; 3657 after the assessment's sentinel/pins runs; I1 chain verifies; 3 `WORKTREE_SCRATCH_PRUNED` (seq 3645, 3646, 3655) |
| `work/` | 0 worktrees |
| `tmp/` | 74.27 MiB, 25 directories (3 reviewer trees 60.9 MiB, 5 tracked files, small canary/gate dirs) |
| `stranded/` | 123 captures (8 from the earlier operator run, 2 from run 1, 6 from run 2, plus the prior corpus) |
| `%TEMP%/pmk-precheck-*` | 467 husks at 20:06 local, 471 at 20:24 (0 bytes total); the foreign precheck is now patched; existing old-code processes may produce a few more until they exit |
| `%TEMP%/pmk-merge-*` | 15 directories at 20:06 local: 13 orphan pytest leftovers (repositories gone), 1 empty shell (`pmk-merge-vzivkoad`), and 1 live-looking merge (`pmk-merge-fy5t4h9d`) whose `.git` points at a test repository (`tmpjegemeia/repo`), not `umaws-noscope-toy`; the `umaws-noscope-toy` merge was not present at assessment |
| Registered git worktrees | 2 (the main checkout and `.claude/worktrees/agent-a8ea…`) |
| Tests | 1360 passed, 1 skipped (working-tree run, recorded at `.pmwork/umaws-full-suite-2026-11-12.xml`; clean-base totals 1276/1282/1289, i.e. 1275/1281/1288 passed — see §6.2) |
| Sentinel / pins | ok / unaffected |
| Affected task cards | none — this defect never failed a task; `T-0195` (H7, "report `%TEMP%/pmk-merge` trees from worktree prune") is `VOID`, its substance having landed in `772e1bc`, `e477c5f` and `307531f` |

---

## 9. Decision Records

**D-1 (2026-11-11, operator, on the residual non-lease cleanup):** *"Extend the sanctioned path, then run it"* — chosen over a one-off `git worktree remove` cleanup, so that `reclaim_after_capture` + `verify_archive` remain the single deletion path. This is the precedent followed for everything below.

**D-2 (2026-11-12, operator, on the stale precheck dry-run directory):** *"Extend prune --precheck-trees, then run (Recommended)"* — add a scoped, capture-first reclaim for `%TEMP%/pmk-precheck-dry-*` rather than deleting it outside the sanctioned path.

**D-3 (2026-11-12, operator, on `tmp/`):** *"Only the 6 registered canary worktrees (Recommended)"* — capture-first reclaim of the six registered worktrees only; the reviewer-agent trees, the five tracked files and the rest of `tmp/` stay.

**D-4 (2026-11-12, operator, on the husks and orphan merge shells):** *"(reported, deliberately left alone)"* — the unprovable families are not deleted; they are reported here.

**D-5 (2026-11-12, operator, on this report):** produce a formal report to the project's existing documentation standard, comprehensive, with an `Author` field, fit for integration into the final system report, and accompanied by a comprehensive set of clarification questions.

**Register note (added by the second-pass assessor):** D-1…D-5 are embedded here for this report; they are now recorded in `pilot/decisions.md` as **D-76…D-80** (the next free global IDs), with the report-local mapping noted there.

Prior records that frame this one: **Q-077** (class-K, ratified by `human:tiwa-pene`) enabled `worktree.reclaim_on_reap` for REC-01; **T-0195/H7** was discharged by voiding the card once the reporting-and-reclaim surface existed.

---

## 10. Unresolved Issues and Deferred Items

| ID | P | Item | Size / exposure | Recommended next step |
|---|---|---|---|---|
| U-1 | P3 | 471 `pmk-precheck-*` husks at 20:24 local (foreign precheck now patched; old-code processes may add a few more) | 0 bytes, ~471 inodes | Machine hygiene (R-13); cannot be reclaimed by the repo — no ownership proof |
| U-2 | P3 | 13 orphan `pmk-merge-*` leftovers + 1 empty shell + 1 live test repo | ~2 KB total | Same as U-1; the live test repo and any foreign merge must continue to be skipped |
| U-3 | P4 | 1 live-looking `pmk-merge-*` (`pmk-merge-fy5t4h9d`, pointing at a test repository) | — | None — the ownership gate protects it; the `umaws-noscope-toy` merge was not present at assessment |
| U-4 | — | Test-setup `mkdtemp()`/`mktemp()` sites (7 across 3 files) | small, unprefixed `tmp*` dirs | **Closed** by R-09 |
| U-5 | — | `src/fleet/legacy.py:245` `llm_launcher_*` (73 dirs, none newer than 2026-11-05) | unowned but human-paced | **Closed** by R-10 — a different class; the hygiene policy owns the accumulation |
| U-6 | — | The `tmp/` one-off wrote no kernel event | traceability gap | **Closed** by R-12 — the surface now exists for the next one |
| U-7 | P2 | No invariant observes `%TEMP%` families | blind spot in every gate | R-07 (deferred by the operator) |
| U-8 | P3 | Reviewer-agent trees (60.9 MiB) and 5 tracked files under `tmp/` | 60.9 MiB | Operator decision when the reviewers' work is retired |
| U-9 | P1 | R-13 independent review of this report | process | First pass **done** by Claude 3 Opus 20240229 (confirmed by the operator; raw output missing); second pass **done** by ERNIE 5.5 Flash Preview (`assessment-ernie-5-5-incident-report-fleet-scratch-leak-v1.md`) |
| U-10 | P3 | Production kill-mode leftovers (a SIGKILL runs no `finally`) | rare, reclaimable when ownership is provable | R-13/R-12; no code fix is possible for SIGKILL |

---

## 11. Lessons Learned

1. **The biggest leak was not the one on the list.** The operator pointed at `pmk-merge-*`; the live, unbounded leak was the precheck's empty husks — 412 of them, one per lease admission, invisible to every existing gate. Measure the whole family before fixing the named one.
2. **`ignore_errors=True` is a decision, not a default.** It converted a Windows read-only attribute into permanent, silent data-left-behind. Probing the claim (4/4 arrangements) took thirty seconds and turned an assumption into evidence.
3. **Global namespaces need an owner or a collector.** `%TEMP%` has neither for this project's scratch; once a leftover's repository is deleted its ownership is unprovable, so the sanctioned path correctly refuses it and the leftover is forever. Putting test scratch under pytest's `tmp_path` removes the class at the source.
4. **One deletion path is worth extending rather than bypassing.** Every removal in this incident went through `reclaim_after_capture`, so every removed tree is captured, verified, restore-proved and re-digested first — and both runs produced archives that verify after the fact.
5. **A running process keeps the old code.** The editable install means a fix protects *future* processes; the last husks attributable to this repository came from processes that started before the commit. The global family continued from `umaws-noscope-toy`, which carried the pre-fix code; its precheck is now patched, but old-code processes may add a few more husks until they exit.

---

## 12. Commit References

| Commit | Date (local) | What it fixed |
|---|---|---|
| `a1d301c` | 2026-11-11 | Predicate rewrite ("only an active lease may refuse reclamation") — context for the reclaim path |
| `772e1bc` | 2026-11-12 09:38 | Scratch-prune feature: `--scratch` / `--merge-trees`, capture-first, `WORKTREE_SCRATCH_PRUNED` |
| `e477c5f` | 2026-11-12 10:02 | Ownership + recency gates (`belongs_to_repo`, `min_merge_age_days`); raw-directory capture removed |
| `35e4bdc` | 2026-11-12 10:06 | Report of that operator run (18/18 reclaimed) and the reaper finding |
| **`0e51b98`** | **2026-11-12 16:31** | **Root-cause fix: `fleet.scratch`, `temp_root` injection, the missing precheck directory removal, the autouse fixture, 9 regression tests (6 files, +470/−22)** |
| **`307531f`** | **2026-11-12 17:04** | **`--precheck-trees` sanctioned collector (+236/−22, 6 tests)** |
| **`30d27b1`** | **2026-11-12 17:22** | **Working report v1.1.0 (absorbed by this document)** |
| **`05864ad`** | **2026-11-12 18:25** | **Follow-ups R-08/R-09/R-10/R-12: the static leak guard, the seven test-setup sites converted, the `legacy.py` examination recorded, and `pmk worktree reclaim <path>` (8 files, +316/−56, 7 tests)** |
| — | — | The six `tmp/` canary worktrees were reclaimed by a scripted one-off (no commit; see U-6) |

---

## 13. Evidence Artifacts

| Artifact | Path | Description |
|---|---|---|
| Captures, run 1 | `stranded/pmk-precheck-dry-bje5ewal-base`, `…-scratch` | diff (1390 B), untracked tar, 25 ignored files; both verify |
| Captures, run 2 | `stranded/tmp-T-0147-120`, `stranded/tmp-canary-base-20261110`, `stranded/tmp-canary-base-e302119`, `stranded/tmp-canary-process-0004`, `stranded/tmp-canary-process-verify`, `stranded/tmp-clean-head-20261110` | six capture-first archives; all verify |
| Event records | `.pm/events/*.jsonl` seq 3645, 3646, 3655 | the three `WORKTREE_SCRATCH_PRUNED` events |
| Event-log tracking | commit `80223ff` | tracks the previously untracked `2026-11-08` … `2026-11-12` event-log files (536 insertions) |
| Test runs | `tests/fleet/test_scratch.py`; `tests/pmk/test_worktree_lifecycle.py` | the regression suites (22 new tests: 10 in `test_scratch.py`, 12 in `test_worktree_lifecycle.py`) |
| Recorded full-suite run | `.pmwork/umaws-full-suite-2026-11-12.xml` | 1360 passed / 1 skipped / 0 failures; `tests/fleet` 303, `tests/pmk` 284 (working-tree run; clean-base `05864ad` is 1289 total / 1288 passed; gitignored local evidence, like the dispatch report's `.pmwork/*.txt`) |
| Full-suite gates | `.pmwork/umaws_junit_scratchfix.xml` (1276 total; 1275 passed / 1 skipped), `.pmwork/umaws_junit_precheck.xml` (1282 total; 1281 passed / 1 skipped) | **regenerated at assessment** from clean checkouts of `0e51b98` and `307531f` (git archive + full suite). The report's earlier 1347/1353 figures were dirty-tree runs; the clean-base totals are 1276/1282. |
| Working note | `remediation-fleet-scratch-leak-report-v1.md` | absorbed by this report |
| Prior report | `remediation-worktree-scratch-prune-report-v1.md` | the 18/18 operator run and the reaper finding |
| Second-pass assessment | `assessment-ernie-5-5-incident-report-fleet-scratch-leak-v1.md` | ERNIE 5.5 Flash Preview; verdict ACCEPT WITH CORRECTIONS; C-1…C-15 applied |

---

## Appendix A — Raw Event Timeline (authoritative)

| seq | ts (UTC) | type | payload summary |
|---|---|---|---|
| 3645 | 2026-11-11T21:03:07Z | `WORKTREE_SCRATCH_PRUNED` | `include_work` — 8 removed, 0 skipped |
| 3646 | 2026-11-11T21:03:39Z | `WORKTREE_SCRATCH_PRUNED` | `include_merge` — 10 removed, 15 skipped (ownership not provable) |
| 3655 | 2026-11-12T04:04:54Z | `WORKTREE_SCRATCH_PRUNED` | `include_precheck` — 2 removed, 0 skipped; archives `stranded/pmk-precheck-dry-bje5ewal-{base,scratch}` |

All three were recorded with `actor.kind = "kernel"`. The `tmp/` reclaim (run 2) produced no event — see F-11/U-6/R-12.

## Appendix B — Actor Attribution

| Actor | Role in this issue |
|---|---|
| `human:tiwa-pene` (operator) | Approved the mechanism (D-1/D-76), the two reclaim runs (D-2/D-77, D-3/D-78), the leave-alone decision (D-4/D-79), this report (D-5/D-80), the foreign precheck update, the event-log commit, and the second-pass assessment |
| Step 5 Preview (author) | Measurement, root cause, the three commits, both runs, this report (v1.2.0 corrections applied by the second-pass assessor, provenance preserved; the v1.2.1 label correction is the author's own) |
| Claude 3 Opus 20240229 (first-pass assessor) | Returned the first-pass assessment (confirmed by the operator; orchestrator-launched; raw output missing) |
| ERNIE 5.5 Flash Preview (second-pass assessor) | Re-measured the report, applied C-1…C-15, patched `umaws-noscope-toy/src/fleet/precheck.py`, recorded D-76…D-80, regenerated the clean-base 1276/1282 totals, committed the event-log files, wrote `assessment-ernie-5-5-incident-report-fleet-scratch-leak-v1.md` |
| Kernel (`actor.kind = "kernel"`) | Recorded seq 3645, 3646, 3655; the assessment's sentinel/pins runs added seq 3656, 3657 |
| `umaws-noscope-toy` fleet/test processes | Created the live `pmk-merge-*` tree observed at report writing, and — before the operator-authorized patch — produced the `pmk-precheck-*` husks at assessment time; its precheck now removes its scratch in a `finally` |
| Concurrent agents in this working tree | Unrelated in-flight work (`src/cna/**`, `docs/**`); none of their changes were committed here |

## Appendix C — R-12 Conformance Map

| R-12 requirement | Location |
|---|---|
| 1. YAML frontmatter | File header |
| 2. Provenance block | Header block |
| 3. Executive Summary (≤3 paragraphs) | §1 |
| 4. Incident Timeline (UTC, evidence refs) | §3 |
| 5. Root Cause Analysis with file:line | §4 |
| 6. Findings Table with status | §5 |
| 7. Recommendations Table with status | §7 |
| 8. Current State | §8 |
| 9. Decision Records with full text | §9 |
| 10. Evidence Artifacts | §13 |
| 11. Raw Event Timeline Appendix | Appendix A |
| 12. Actor Attribution Appendix | Appendix B |
| 13. Lessons Learned | §11 |
| 14. Commit References | §12 |
| Naming convention `incident-report-<topic>-v<N>.md` in the project root | `incident-report-fleet-scratch-leak-v1.md` |

**Deviation declared:** R-12 numbers no "Unresolved Issues" section; §10 carries it because this report feeds a final system report and the deferred items must be traceable. §6 (Remediation and Testing) is likewise an addition, holding the test evidence R-12 does not name explicitly. Appendix D records the R-13 first-pass findings and Appendix E records the author's re-verification; R-13 is a process requirement rather than a document element, so both are additions rather than conformance items. **Additional deviation:** the findings table uses `mitigated` and `open` alongside R-12's `acknowledged / resolved / deferred`; each such row names the residual.

## Appendix D - First-pass R-13 Assessment Record (Claude 3 Opus 20240229), re-verified by the author

**Assessor:** Claude 3 Opus 20240229 (`claude-3-opus-20240229`), said to be independent of the
author; **confirmed by the operator** — an Orchestrator LLM launched Claude as the assessor in the background. The raw assessment artifact is still missing, so the 14 findings are only partly recorded. **Verdict: ACCEPT WITH CORRECTIONS.** No central claim was refuted.

The assessor reportedly returned 14 findings; the table records A-1…A-8 individually and groups A-9…A-14 in one row, so the full list is not recoverable from this appendix. Per the project's correction convention, each
numeric finding was **re-verified by the author against primary evidence before
being applied**; four of the seven proposed corrections did not survive that
check. The assessor's own evidence citations were partly wrong for this
environment (it cited `du -sh`, `pytest --result=`, `dir %TEMP%`, a non-existent
`.pm/events/fleet.jsonl` and `src/cli/cli.py`), which is why nothing was applied
on its authority alone.

| ID | Assessor's finding | Re-verification | Outcome |
|---|---|---|---|
| A-1 | `0e51b98` is +471/−23, not +470/−22 | `git show --stat 0e51b98` → 6 files, **+470/−22** | **Refuted** — report unchanged |
| A-2 | `precheck.py` still uses `mkdtemp` in the dry run | `Select-String mkdtemp\|tempfile src/fleet/precheck.py` → no matches; both sites are `scratch.scratch_dir` | **Refuted** |
| A-3 | `test_scratch.py` has 10 tests, not 9 | `pytest --collect-only tests/fleet/test_scratch.py` → **9** (10 only after the R-08 guard was added, which the assessor could not have seen) | **Refuted at v1.0** |
| A-4 | `git ls-files tmp` shows 3 tracked files, not 5 | `git ls-files tmp` → **5** files, unchanged since the `tmp/` run | **Refuted** |
| A-5 | `%TEMP%/pmk-merge-*` directories are empty | At the author's re-verification: 14 dirs, **1 empty**, 2149 bytes; at my assessment (20:06 local): 15 dirs, 1 empty, 422–2,246 bytes depending on the moment — the orphans are leftover pytest merge worktrees of a few KB, not empty shells | **Partly right** — the report's wording is corrected (§8, U-2, U-3) |
| A-6 | `test_worktree_lifecycle.py` gained 6 precheck tests, not 7 | Diff against `0e51b98`: **6** test functions added (62 → 68) | **Accepted** — §6.1, §7 R-06 and §12 corrected |
| A-7 | `tests/fleet` reports 301 passed, not 302 | The assessor ran it while the author was mid-edit on `test_merge_queue.py` (the R-09 conversion). Settled by the recorded run in `.pmwork/umaws-full-suite-2026-11-12.xml` | **Explained** — the report's figure is the run recorded under §6.2 |
| A-8 | Deferred items lack priority ranking | R-13 checklist item 7 | **Accepted** — §10 now carries a P1–P4 priority column |
| A-9…A-14 | Checklist results, unverifiable capture names | Verified in-session; the two `pmk-precheck-dry-bje5ewal-*` captures exist and verify (`verify_archive` → True) | Verified |

**Assessment-quality note for the final report:** the verdict stands, and **three** corrections were applied (A-5, A-6, A-8; two numeric, one non-numeric). Four of the seven numeric corrections were wrong, and its evidence citations mixed in commands and paths that do not exist on this platform — so the assessment is recorded as *advisory input that was independently re-verified*, not as an authority. This is the same discipline the parent incident report applied to its six assessments. **The assessor's identity is confirmed (Claude 3 Opus 20240229, orchestrator-launched); the raw output is still missing, so its completeness is unverified.**

**Follow-ups from the assessment:** a second R-13 pass over v1.1 is recommended
(U-9), and the assessor could not verify evidence that has since been recorded
under `.pmwork/` — the accessibility gap that the recorded full-suite run
(`.pmwork/umaws-full-suite-2026-11-12.xml`) closes. The second pass is recorded
in `assessment-ernie-5-5-incident-report-fleet-scratch-leak-v1.md`.

## Appendix E — Author's Re-verification of the R-13 First-pass Findings (2026-11-12)

Recorded by the author (Step 5 Preview), not by the first assessor, so the final report can cite how each number was checked, per the project's correction convention. The first assessor's own report is not available; Appendix D is the only record of its findings:

1. **Read-only failure mode — probed, not assumed.** `shutil.rmtree(..., ignore_errors=True)` left the tree in 4/4 read-only arrangements on win32; `remove_scratch` removed 4/4. The first version of `remove_scratch` cleared only *file* bits and failed on a read-only **directory** — the probe caught it before commit.
2. **Registration check — corrected mid-session.** A `Select-String` against backslash paths initially reported the stale precheck worktrees as "not registered"; git prints forward slashes, and `git worktree list` showed both registered. The reclaim was planned on the corrected fact.
3. **Exit-code artifact.** A dry run piped through `Select-Object -First` reported exit code 1; re-run without truncation it was exit 0 — a pipeline artifact, not a defect.
4. **Attribution method.** Leak attribution used private temp roots (`%TEMP%` redirected per run), so "0 leaked" is a statement about that run alone and not confounded by other agents' concurrent runs.
5. **Count drift is expected.** The `pmk-merge-*` family measured 14–15 across the session because a foreign project's merges come and go; the report names the range rather than a single figure.
