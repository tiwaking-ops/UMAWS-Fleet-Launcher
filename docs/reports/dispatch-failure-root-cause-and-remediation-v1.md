---
document:
  title: "Project Report: Dispatch Failure of the UMAWS Fleet — Root Cause, Remediation, and Safeguards (T-0145/T-0146/T-0148/T-0150)"
  status: "Open — engineering remediation landed on local main; supervised canary and decision ratification outstanding; dispatch paused"
  version: "1.0.0"
provenance:
  author_llm:
    name: "Buffy"
    version: "Codebuff agent (freebuff-buffy-01); report version 1.0"
  created_date: "2026-11-08"
  last_modified_date: "2026-11-08"
  scope: "C:\\temp\\projects\\testproject1 (branch main, live repo), local commits c3aaca0..9606757 (never pushed), the Kernel ledger .pm/events/2026-11-07.jsonl and 2026-11-08.jsonl, evidence bundles .pm/evidence/EB-T-0148-120 and EB-T-0150-121, fleet agent logs .pm/fleet/logs/**, task cards T-0145/T-0146/T-0148/T-0150, and one throwaway-worktree reproduction run"
  source_of_truth: "Ledger events by sequence number (seq 3135–3160 for the canary window; 3194–3229 for T-0145/T-0146); bundle.json for EB-T-0148-120 and EB-T-0150-121; agent transcripts .pm/fleet/logs/T-0148/120-0.log, T-0150/121-0.log, T-0146/124-0.log, T-0145/122-0.log, 122-1.log, 123-0.log, and the Overseer log .pm/fleet/logs/overseer/0-0.log; source at the cited commits; measured test runs recorded under .pmwork/*.txt"
---

# Dispatch Failure of the UMAWS Fleet — Root Cause, Remediation, and Safeguards

**Author:** Buffy (Codebuff agent), agent id `freebuff-buffy-01` — **version 1.0**
**Report ID:** `dispatch-failure-root-cause-and-remediation-v1`
**Date:** 2026-11-08
**Status:** **Open.** Remediation is implemented and unit-verified on local `main`; the supervised live canary, decision ratification (D-62…D-68) and dispatch resumption are outstanding. Dispatch remains `PAUSED` with zero active leases.
**Repository state at writing:** HEAD `9606757` (local only, never pushed), 542 tests, `pmk pins check` `ok: true`, 150 task cards, 103 incidents, 64 dirty working-tree paths (mostly pre-existing scratch artifacts and live Kernel state), 15 Kernel worktrees / 26 git worktrees.
**Related documents:** `report-umaws-problems-and-issues-v1.md` (pre-repair diagnosis), `proposal-umaws-problems-and-issues-repair-v1.md` (approved plan), `pilot/repair-dispatch-rootcause-v1.md` (working notes), `pilot/repair-canary-runbook-v1.md`, `pilot/cards/canary-replacement-v1.md`, `pilot/drafts/decisions-d62-plus.md`.

---

## 1. Executive summary

Between 2026-11-07T19:38Z and 2026-11-07T23:12Z the fleet failed to carry four cards to `DONE` without operator intervention. Two of those cards had **byte-identical inputs and opposite verdicts** fifty-eight minutes apart. The repair programme fixed the visible symptoms, but the failure of the *canary itself* — the one run intended to prove the repair — remained unexplained. This report closes that gap.

**Root cause (primary).** No component owned the **execution environment**. The gate, the workers and the Overseer all inherited a Python environment whose editable-install hook (`__editable__.umaws_fleet-0.1.0.pth`) hard-codes `C:\temp\projects\testproject1\src` — the main working copy. The gate in particular ran `subprocess.run(gate_cmd, cwd=temp_wt)` with **no `env=` argument** (`13b8959:src/fleet/merge.py`, lines 248–251), so `cwd` was cosmetic: `python -c "import cna"` inside the tree under test loaded `C:\temp\projects\testproject1\src\cna\...`. The gate therefore judged the main working tree, which was being edited out of band, instead of the merged tree it had just built.

**Root cause (contributing, independent).**

1. **Overseer starvation.** All nine `OVERSEER_WOKEN` events in the window recorded `the Overseer profile pi-orca-deepseek is disabled`. `agents.toml` lists that disabled profile first and `OverseerRunner.wake()` took `profiles[0]` and returned on refusal without trying `kilo-auto`, so no session ever ran and no stale hint could be corrected.
2. **False hint with no provenance.** T-0146's `agent_hint` asserts that the 66-file corpus is absent and instructs the worker to copy it from the main tree — while the corpus was already in the worktree and the instruction pointed outside the card's write scope. The card's `hint_base_commit` is empty, and `_stale_hint_reason()` returns `""` when the base is empty, so the REC-13 stale-hint guard could not fire.
3. **Shell dialect.** Kilo's command runner on this machine is PowerShell 5.1; workers and the Overseer issued bash idioms. Measured parser failures: **904** in the Overseer log, 16 in T-0145/122-0, 13 in T-0146/124-0, 0 in the two canary runs that used no shell at all.
4. **Repeated-work loop.** A relative spawn prompt (`Read .pmwork/ORDER.md`) plus a CLI working directory in the main tree made 17 of T-0001's 20 spawn logs fail to find the order; the agents then globbed and found **a sibling attempt's** `work/T-0001-11/.pmwork/ORDER.md` and redid that task. Already-satisfied bases (`pi-test.txt`, `hello.txt` committed before re-dispatch) and the adapter's refusal to overwrite unread files completed the loop.
5. **Evidence loss.** The gate captured its stdout/stderr and recorded only the exit code, so the failing assertion of 2026-11-07 is unrecoverable.

**What was not the cause.** No evidence implicates either model. The record cannot even identify the model that served a run: every `MODEL_SERVED` event is `{"profile":"kilo-auto","served_models":[],"source":"none","via_gateway":false}`, bundles record `"family":"unknown"`, and `kilo-auto` is a router alias. The observed failures are wrong-package imports, lost turns to parser errors, and stale cards — not bad reasoning about the task.

**Remediation (local `main`, never pushed).** One environment rule for every spawned process; gate output recorded; Overseer profile fallback; explicit shell contract in every work order; absolute order paths; already-satisfied pre-lease guard; pinned pipeline identity. Ten new tests, full suite green, and a recorded reproduction proving the 2026-11-07 canary inputs pass (507 passed) once the environment is pinned.

---

## 2. Scope, method, and evidence standard

### 2.1 What this report covers

- The dispatch failures of T-0145, T-0146 and T-0148, and the disagreement between T-0148 and T-0150.
- The environment, hint, Overseer, shell and card-construction defects behind them.
- Corrective actions taken, their verification, and what remains unverified.
- Safeguards and recommendations intended to prevent recurrence.

### 2.2 Out of scope

- Provider billing and capacity policy beyond recording the 429 class as a separate failure mode.
- The product goals in `docs/PDD.md` (G-001…G-006) except where an oracle is used as evidence.
- Model quality evaluation. §7 explains why the record cannot support it.
- Disposal of the eleven extra worktrees and the decision-register duplicates, which are separate recorded issues.

### 2.3 Method

Read-only review of the Kernel ledger, evidence bundles, surviving worktrees and agent transcripts, plus source inspection at the cited commits. **No task was leased and no dispatch was started by the author.** One reproduction was run in a throwaway detached worktree (`git worktree add --detach … HEAD`, removed afterwards); main was not modified by it. That reproduction is the only non-recorded datum and is labelled as such wherever it appears.

### 2.4 Claim classification used throughout

| Label | Meaning |
|---|---|
| **Confirmed** | Directly recorded in the ledger, a bundle, a log or source at a cited commit. |
| **Derived** | Follows from confirmed facts plus code reading; no direct observation of the failing moment. |
| **Unknown** | Not recoverable from the record; stated as unknown rather than guessed. |

---

## 3. System under test

The pipeline for one card is:

```
READY → CLAIMED (lease + fence) → worktree work/T-<id>-<fence>
      → ORDER.md written, CLI spawned with a one-line prompt
      → worker edits, writes .pmwork/RESULT.md, exits
      → harness checks claims, runs acceptance oracles in the worktree
      → SUBMITTED + evidence bundle EB-<id>-<fence>
      → merge into a temporary worktree, run gate_cmd there
      → fast-forward main, INTEGRATED → DONE
```

Three properties are load-bearing and were all violated or unenforced:

1. **The tree under test must be the tree that executes.** Oracles, gate and worker tools must import the worktree's code. This is the invariant the repair added as `src/fleet/runenv.py::worktree_env()`.
2. **A card's instructions must describe the tree the worker will actually see.** `agent_hint` is a claim about a tree at a point in time; it needs a recorded base.
3. **A verdict must be reproducible from recorded evidence.** An exit code without output cannot distinguish a defect from a flake.

---

## 4. Timeline of the failure window (UTC; local = UTC+13)

| Seq | UTC | Event | Significance |
|---|---|---|---|
| 3134 | 19:38:37 | `CLAIMED` T-0148, base `82f6be1` | canary card 1 |
| 3135 | 19:38:37 | `AGENT_STARTED` T-0148 | main tree dirty: 129 paths |
| 3137 | 19:39:32 | `OVERSEER_WOKEN`, error `pi-orca-deepseek is disabled` | no Overseer session |
| 3140 | 19:39:36 | `SUBMITTED` T-0148, own oracle green, scope clean | worker output was correct |
| 3141 | 19:43:35 | `ORACLE_RESULT` stage `gate`, `pytest -q`, **exit 1** | only the exit code was stored |
| 3142 | 19:43:35 | `VERIFIED` class `ORACLE_FAILED` → `REWORK` | genuine gate failure, log lost |
| 3144 | 19:54:23 | `PROJECT_STATE` `PAUSED` by operator | response to the failure |
| 3148 | 20:17:01 | `CLAIMED` T-0150, **same base `82f6be1`** | identical card content |
| 3152 | 20:18:44 | `AGENT_EXITED` `OK`; advisory "RESULT.md does not mention the task id" | non-blocking advisory |
| 3157 | 20:41:36 | `ORACLE_RESULT` gate **exit 0** | the flip |
| 3159 | 20:41:38 | `INTEGRATED` `e31d70a` | T-0150 `DONE` |
| 3197 | 23:06:49 | `AGENT_STARTED` T-0146 attempt 1, base `e08fa8d` | false hint, unpinned env |
| 3199 | 23:07:48 | `OVERSEER_WOKEN` disabled | ninth refusal |
| 3212 | 23:12:04 | `MODEL_SERVED` T-0145, `served_models: []` | attribution gap |
| 3225 | — | T-0145 `VOID` (operator) | card superseded |

---

## 5. Findings

### F-01 — The gate executed the main tree, not the tree under test (**Confirmed**)

**Evidence.**

- Pre-fix gate call at the T-0148 base (`git show 13b8959:src/fleet/merge.py`, lines 248–251):

  ```python
  proc = subprocess.run(gate_cmd, shell=True, cwd=str(temp_wt),
                        capture_output=True, timeout=900,
                        text=True, encoding="utf-8", errors="replace")
  ```

  No `env=`. `cwd` affects where the command runs, not which `cna`/`pmk` Python imports.

- The venv's editable install is a literal path:

  ```
  .venv/Lib/site-packages/__editable__.umaws_fleet-0.1.0.pth
    -> C:\temp\projects\testproject1\src
  ```

- Demonstrated in a throwaway worktree at `82f6be1` with the T-0148 branch merged:

  ```
  cna  -> C:\temp\projects\testproject1\src\cna\tools\coverage.py
  pmk  -> C:\temp\projects\testproject1\src\pmk\__init__.py
  ```

**Impact.** The gate's verdict tracked the main working copy. Main carried 129 dirty paths at spawn and was being edited out of band, so the verdict was not a function of the merged tree. The same mechanism made worker tool calls (T-0146: `python -m cna.tools.coverage` resolved main's file; only `$env:PYTHONPATH=…` fixed it) and Overseer inspections (115 main-tree references in its log) untrustworthy.

**Fix.** `src/fleet/runenv.py::worktree_env()` is now the single environment contract, applied to oracles, gate, workers, retry/restart and the Overseer (`55f3f46`, with the gate half in `ebe46ce`). Six tests in `tests/fleet/test_worktree_env.py`; five failed before the change.

### F-02 — The canary flip is a run property, not a code property (**Confirmed mechanism; Unknown failing test**)

**Evidence.**

| | T-0148 | T-0150 |
|---|---|---|
| bundle `base_commit` | `82f6be16e410…` | `82f6be16e410…` |
| `docs/canary.md` sha256 | `dc943d75a3a2…c93e` | `dc943d75a3a2…c93e` |
| diff scope | clean | clean |
| own oracle | exit 0 | exit 0 |
| gate `pytest -q` | **exit 1** (seq 3141) | **exit 0** (seq 3157) |
| terminal state | `REWORK` | `DONE`, `e31d70a` |

Nothing was committed to main between the two gates. A reproduction of T-0148's exact inputs (base `82f6be1`, `--no-ff` merge of `pmk/T-0148-120`, `pytest -q` with the worktree on `PYTHONPATH`) yields **507 passed, exit 0**.

**Honest limit.** Re-running the old unpinned configuration today also exits 0, because current main is consistent with the old tests. The specific 08:43 divergence required main's `src` to differ from the merged tree at that moment, and that state cannot be reconstructed. Which test failed is **Unknown** — the gate discarded its output (F-08). The mechanism is not in doubt; only the identity of the failure is.

### F-03 — The Overseer could not wake, so stale hints could not be corrected (**Confirmed**)

**Evidence.** Nine `OVERSEER_WOKEN` events, nine identical errors (`seq 3137, 3143, 3160, 3165, 3169, 3192, 3199, …`):

```
the Overseer profile pi-orca-deepseek is disabled
```

`agents.toml`:

```toml
[overseer]
profiles = ["pi-orca-deepseek", "kilo-auto", "opencode-fallback", ...]
```

`src/fleet/overseer.py` took `profiles[0]`, tested it, and returned on refusal. The ordered list exists to degrade gracefully; it did not.

**Impact.** No independent reviewer ran during the entire failure window. A stale hint could not be retracted, and no session could have caught F-01. This also explains why the only Overseer text available was an older session's 9 MB log.

**Fix.** Selection now walks the list and takes the first enabled, non-cooling profile, naming skipped profiles when none is usable (`d605c15`; `tests/fleet/test_overseer_profile_fallback.py`).

### F-04 — T-0146's hint was false and unpinnable (**Confirmed**)

The card's `agent_hint` states the corpus is absent, that it "exist[s] only as untracked files in the MAIN tree", and instructs the worker to copy 66 files — into paths outside the card's write scope (`src/cna/tools/coverage.py`, `coverage/rules_coverage.json`, `tests/test_coverage.py`).

**Evidence the hint was false.** The Overseer's own reasoning (`overseer/0-0.log`, lines 168374–168425) shows the belief it was built on: "Corpus content is still NOT in main HEAD … exist **only as untracked files** in main's working tree", and "Their agent hints authorize copying the corpus into the worktree". By dispatch at `e08fa8d` the corpus was committed; the worker's log records it ignoring the instruction ("The worktree already has CNA-Rules.adoc and sections/").

**Why it survived.** `hint_base_commit` on T-0146 is `""`. `_stale_hint_reason()` returns `""` when the base is empty (`src/pmk/api.py`), so REC-13's stale-hint refusal never evaluated the hint, even though `"corpus"` and `"docs/rules"` are in `_HINT_STALE_TOKENS`.

**Fix.** Hint pinning plus `IDENTITY_ANOMALY` landed in `6f92d31`. Existing cards cannot be amended (`pmk task` exposes only `create/admit/list/show/void`), so T-0146 needs a new card or an operator void; the drafted replacement is `pilot/cards/canary-replacement-v1.md`.

### F-05 — Workers and the Overseer speak bash to PowerShell (**Confirmed**)

Measured `grep -c` per log: Overseer **904**, T-0145/122-0 **16**, T-0145/122-1 **3**, T-0145/123-0 **5**, T-0146/124-0 **13**, T-0150 **0**, T-0148 **0**.

Representative failures from T-0146:

| Issued | PowerShell 5.1 answer |
|---|---|
| `ls -la <dir>` | `A parameter cannot be found that matches parameter name 'la'` |
| `cd <dir> && python …` | `The token '&&' is not a valid statement separator` |
| `cd <dir> & python …` | `The ampersand (&) character is not allowed` |
| `PYTHONPATH=<dir> python …` | `… is not recognized as the name of a cmdlet` |

The dangerous case is not the loud failure but the silent one: a command that returns nothing and is read as evidence of absence — one route by which a model writes "the corpus is not there".

**Fix (mitigation).** `render_order()` emits `## Environment` with the platform and the PowerShell forms (`82d5508`; `tests/fleet/test_order_environment.py`, both platforms). Not yet proven against a live model.

### F-06 — The repeated-task loop came from a relative order path (**Confirmed**)

T-0001, T-0002 and T-0004 each left 18–20 spawn logs while the surviving ledger records only 2–4 `CLAIMED` events.

**17 of T-0001's 20 logs** contain the sequence (`56-0.log`):

```
I'll read the order file and then carry out the task exactly as written.
✗ Read .pmwork/ORDER.md failed
Error: File not found: .pmwork/ORDER.md
✱ Glob "**/ORDER.md" 0 matches
✱ Glob "work/**/*" 0 matches
$ Get-ChildItem work -Recurse -Filter "ORDER.md" -Force
Directory: C:\temp\projects\testproject1\work\T-0001-11\.pmwork
```

The prompt then was relative and the CLI's working directory was the main tree. The only ORDER.md reachable was **another attempt's**, so the agent carried out that order, wrote nothing in its own worktree, and the card returned. The relative string was replaced in `93a3366`; `51c657f` now resolves the path so no caller can reintroduce it (`tests/fleet/test_order_prompt_path.py`).

**Related, distinct loop.** Already-satisfied bases plus empty diffs: `pi-test.txt` was committed at `b0be602`; T-0004's later pass completed as `reintegration: true` (seq 868). The adapter then refused to rewrite an unread file ("Refusing to overwrite pi-test.txt … never read its full current content"), guaranteeing a no-op. T-0002 shows a third pattern: 151 `FLEET_ASSIGNED` with **zero** `CLAIMED` — assignment churn under provider pressure, not repeated work.

### F-07 — The gate verdict was not reconstructable (**Confirmed**)

`integrate()` used `capture_output=True` and recorded only `exit` (seq 3141). The bundle contains `bundle.json` alone; the worktree holds `ORDER.md`, `RESULT.md`, `provenance.json`; `pytest_junit.xml` in main is overwritten by other runs. No copy of the failing assertion exists anywhere under `.pm/`.

**Fix.** `_gate_diagnostics()` now records `failed_tests`, `stdout_tail` and `stderr_tail` in the gate event (`82d5508`; `tests/fleet/test_merge_gate_diagnostics.py`).

### F-08 — Provenance is incomplete, and identity had drifted (**Confirmed**)

- Four commits (`e08fa8d`, `ebe46ce`, `82f6be1`, `9893d94`) are authored `Tiwa Pene <tiwaking@gmail.com>` while neighbouring pipeline commits use `umaws-pilot`. Recorded, not rewritten (D-67).
- `MODEL_SERVED` carries no model identity for any run in the window. The only identity is the CLI header (`> code · kilo-auto/free` for workers; `> build · recursive/flint-v1.0:free` for the Overseer), and `kilo-auto` is a router alias.

**Fix.** Merge path pins `-c user.name=umaws-pilot -c user.email=umaws-pilot@localhost`, records `IDENTITY_ANOMALY` on mismatch, and `.githooks/pre-commit` logs agent-context commits under the human identity (`6f92d31`). **Activation is outstanding:** `core.hooksPath` is unset (A8).

### F-09 — Separate class: provider capacity (**Confirmed, not a fleet defect**)

Many short logs are a single 429, e.g. `T-0002/12-0.log`, `T-0003/3-0.log`, `T-0109/89-0.log`:

```json
{"code":"free_rate_limited","message":"Free model capacity is limited right now…","retry_after_seconds":635}
```

The Overseer log's tail is nothing but 429s. These attempts spent no reasoning and changed no state. They must not be counted as model or fleet failures, and the retry hints range from 25 s to over two hours.

---

## 6. Root-cause statement

> **The fleet had no owner for the execution environment.** Every component assumed that running a command in a directory was the same as testing the code in that directory. It is not, when an editable install puts the main working copy on `sys.path`. The gate therefore graded a moving target, workers judged their own work with main's tools, and the Overseer described main's tree in hints it believed were about a worktree.

Two independent defects amplified it: the Overseer never woke (so nothing refreshed or retracted the false hint), and the gate destroyed the only evidence that would have shown the cause.

Causal chain for the canary:

```
editable .pth → main/src on sys.path
  → gate imports main's cna/pmk (F-01)
  → verdict depends on main's working tree (F-02)
  → T-0148 fails, T-0150 passes, identical inputs
  → gate output discarded (F-07) → cause unrecoverable
  → operator pauses dispatch; overseer disabled (F-03) → hints stay stale (F-04)
```

---

## 7. What was ruled out, and why the model hypothesis fails

**Model hypothesis.** No recorded artefact supports it.

1. The failures reproduce from the environment alone: identical inputs, opposite verdicts; the same inputs pass once the environment is pinned.
2. Both correct worker outputs were produced and then misjudged (T-0148's own oracle and scope check passed; T-0145 attempt 2's content was already merged).
3. The observable defect in Overseer output is **wrong state attribution** — describing main while claiming a worktree — with a mechanical explanation (F-01, F-05). That is a grounding failure, not a reasoning failure that would distinguish one model from another.
4. Attribution is impossible from the record: `served_models: []`, `source: none`, `family: unknown`, router alias. The report therefore states **Unknown**, not "model".

**Also ruled out:** merge conflicts (none recorded for these cards), worktree creation failure (`create_worktree` succeeded; paths under `work/`), test-suite regression from the repair (542 tests green, and the T-0148 inputs pass at their own base), quota exhaustion as the canary cause (no 429 in the T-0148/T-0150 logs).

---

## 8. Corrective actions implemented

All commits are on local `main` and **have not been pushed**. Phase tags `repair-p0`…`repair-p4` mark the earlier series.

| ID | Defect | Change | Commit | Verification |
|---|---|---|---|---|
| C-01 | Environment inheritance | `src/fleet/runenv.py`; harness, merge, project, dispatcher, overseer use it | `55f3f46`, `ebe46ce` | 6 tests, 5 red before; gate repro 507 passed |
| C-02 | Lint against regressions | `tools/check_subprocess_env.py` + allowlist (7 reviewed exceptions) + test | `55f3f46` | `tests/test_subprocess_env_lint.py` |
| C-03 | Index double-count and corpus scope | same-line anchor dedupe; recursive `.md`/`.adoc` coverage | `8e5b0bb` | warnings 428 → 46; `rule_files` 3 → 69; baseline pinned |
| C-04 | Coverage not portable | ignore `*.egg-info` | `9e4d047` | `--check` passes on main and in a worktree |
| C-05 | Already-satisfied re-lease | S8 precheck on a throwaway worktree of the default branch, opt-in fleet config | `6f92d31` | `tests/fleet/test_precheck.py`; refuses T-0146 today |
| C-06 | Hint provenance / identity | `hint_base_commit` pinning, `IDENTITY_ANOMALY`, `.githooks/pre-commit` | `6f92d31` | `tests/fleet/test_identity_guard.py` |
| C-07 | Shell dialect | `## Environment` section in every order | `82d5508` | `tests/fleet/test_order_environment.py` (3) |
| C-08 | Gate evidence loss | `_gate_diagnostics()` records failing ids and tails | `82d5508` | `tests/fleet/test_merge_gate_diagnostics.py` (3) |
| C-09 | Overseer starvation | first enabled, non-cooling profile; skip list reported | `d605c15` | `tests/fleet/test_overseer_profile_fallback.py` (2) |
| C-10 | Relative order path | `Path.resolve()` in `order_prompt()` | `51c657f` | `tests/fleet/test_order_prompt_path.py` (2) |
| C-11 | Canary card unusable | replacement card drafted, dry-run verified | `9606757` | oracle fails on main, passes on intended work, rejects negative control |

**Process incident during the repair (recorded, not hidden).** While adding the Overseer fallback tests, `tests/fleet/test_overseer_wake.py` (187 lines, 9 tests) was overwritten by the new test file. The suite was briefly green *because those tests were missing*. The `45/165` diff stat exposed it; the file was restored byte-for-byte from `9eb39ad` and the new tests moved to `test_overseer_profile_fallback.py`, with the restoration committed separately as `75a2f59`. No history was rewritten. This is itself evidence for R-11 (diff-stat review) and R-12 (test-count invariants).

---

## 9. Verification performed

### 9.1 Unit and suite

- Focused tests for every change: 17 green across the four new/modified test modules.
- Full suite: **542 tests, exit 0** at `51c657f`; the report commit is documentation only.
- `pmk pins check`: `ok: true`, 2 files, 0 mismatches.

### 9.2 Reproduction (agent-run, throwaway worktree, labelled)

| Input | Result |
|---|---|
| Base `82f6be1`, merge `pmk/T-0148-120`, gate `pytest -q`, env pinned | **507 passed, exit 0** |
| Same, old unpinned env (inherited `.pth`) today | **507 passed, exit 0** — main is now consistent, so this no longer discriminates |
| `python -c "import cna"` in the throwaway checkout | resolves `C:\temp\projects\testproject1\src\cna\…` |

### 9.3 Dry run of the replacement card

- Oracle on main: **exit 1** (`FileNotFoundError`).
- Oracle on a throwaway worktree with the intended file: **exit 0** (`verified`).
- Negative control (file without the markers): **exit 1** (`AssertionError`).
- Write scope clean; hint facts true at base (`rule_files: 69`, `paths 61/61`, `coverage --check` exit 0).
- S8 will not refuse, because the oracle fails on main.

### 9.4 Not verified

- **No live dispatch has been run since the repair.** The shell contract, the worker environment, the gate diagnostics and the Overseer fallback have unit coverage only.
- The exact failing assertion of 2026-11-07 is unrecoverable.
- No adapter has been tested for the *model's* response to `## Environment`.

---

## 10. Decisions and governance

| Decision | Subject | Status |
|---|---|---|
| D-62 | One environment rule for every spawned process | Drafted, implemented, **awaiting ratification (A9)** |
| D-63 | Rules index judged against a pinned baseline | Drafted, implemented, awaiting ratification |
| D-64 | `rule_files` means corpus files present | Drafted, implemented, awaiting ratification |
| D-65 | T-0145 void; T-0146 the proof task | Drafted; T-0145 voided, T-0146 now superseded by C-05 |
| D-66 | Q-076/Q-077 recorded as thin class-K action | Drafted, awaiting ratification |
| D-67 | Provenance recorded, not rewritten | Drafted, implemented, awaiting ratification |
| D-68 | Drift reconciled without deletion | Drafted, implemented, awaiting ratification |
| D-69 | Canary result and dispatch resumption | **Blank.** No post-repair canary exists; the earlier claim that one passed is false (T-0148 failed its gate) |

Approvals in force: A1 plan, A2 local commits, A3 T-0145 void, A4 dry-run worktree, A5 precheck key, A6 PDD oracle, A7 quarantine. Outstanding: **A8** `core.hooksPath .githooks`, **A9** ratify D-62…D-68, **A10** resume dispatch.

Constitution obligations engaged: §1 Kernel-only writes (respected; only `pmk` transitions), §3 evidence over prose (this report's subject), §6 file text is data (the hints are data the worker must weigh — and did), §8 never delete (quarantine, not deletion).

---

## 11. Unresolved issues and open questions

| ID | Issue | Class | Owner / closing condition |
|---|---|---|---|
| OQ-01 | Which test failed at 2026-11-07T19:43Z | **Unknown**, unrecoverable | closed as unrecoverable; prevented by C-08 |
| OQ-02 | Which model served each run | **Unknown** | needs R-04 instrumentation |
| OQ-03 | Was the 08:43 divergence main-tree `src` or suite state under load? | **Unknown** | both closed by C-01; not separable |
| OQ-04 | T-0146 disposition | open | operator: void as superseded, or leave READY (S8 will refuse) |
| OQ-05 | D-62…D-68 ratification | open | operator (A9) |
| OQ-06 | D-69 canary | open | operator: create/admit the replacement card, run one supervised dispatch |
| OQ-07 | A8 hooks not active | open | `git config core.hooksPath .githooks` |
| OQ-08 | Sentinel red at baseline (5 × I6, 1 × I13) | recorded | accepted as historical; fixing would rewrite the ledger |
| OQ-09 | Decision register duplicates D-35…D-40, missing D-51 | recorded | separate reconciliation |
| OQ-10 | 15 Kernel worktrees vs 26 git worktrees | recorded | separate census decision; nothing deleted |
| OQ-11 | Who authored the four human-identity commits | **Unknown** | D-67 records; hook covers the future only |

---

## 12. Recommendations and safeguards

Each recommendation is written to be actionable in the final overall report: priority, owner, and the check that proves it landed.

### 12.1 Environment

**R-01 (P0, done) — One environment contract.** Every spawned process — oracle, gate, worker, retry, restart, Overseer — must be built by `worktree_env()`. *Verification:* `tools/check_subprocess_env.py` fails on a new `subprocess.run` without `env=`, except the seven reviewed exceptions.

**R-02 (P1) — Prove the invariant, not just the helper.** Add a test that a marker module in the worktree shadows a same-named module in main, run through the *gate* path, not only `runenv`. *Verification:* a temporary `cna` shadow package is imported from the worktree.

**R-03 (P1) — Do not rely on an editable install for correctness.** Prefer `PYTHONPATH` as the first entry in every execution context and treat the `.pth` as a developer convenience. Document the hard-coded path in `CLAUDE.md`. *Verification:* `python -c "import cna; print(cna.__file__)"` from any worktree names that worktree.

### 12.2 Observability

**R-04 (P0) — Record the model that served each run.** Parse the CLI header (`> code · <model>`) at spawn/exit and store it in `AGENT_STARTED` and in the bundle's `resolved_models`, with `source: cli-header`. Keep `kilo-auto` as an alias field, not as the identity. *Verification:* `pmk task show` shows a non-empty model for a direct-CLI profile; bundles stop saying `family: unknown`.

**R-05 (P1) — Record gate context, not just its verdict.** Add `base_head`, `merged_head` and `duration_s` to the gate `ORACLE_RESULT`. *Verification:* a failing gate event shows all three plus `failed_tests`.

**R-06 (P1) — Fail fast on shell-dialect damage.** Count tool-command failures per run by class (`parser`, `notfound`, `timeout`) and record the count at `AGENT_EXITED`; warn above a threshold, revoke above a higher one. *Verification:* a synthetic run with ten failing commands produces the counter.

**R-07 (P1) — Never call a failure class "model" without evidence.** Adopt the rule that a failure may be attributed to a model only when (a) the served model is recorded and (b) the same card, base and environment passes on another model. Until then the class is `UNKNOWN` with the environment checked first.

### 12.3 Task cards and hints

**R-08 (P0) — A hint must carry its base.** `pmk task create --agent-hint` already pins `hint_base_commit`; extend `_stale_hint_reason()` to refuse an **empty** base when the hint contains any `_HINT_STALE_TOKENS`. *Verification:* a card created by an older path is refused with a clear message; T-0146 becomes a test fixture.

**R-09 (P1) — Re-render hints when HEAD moves.** An Overseer wake after a merge should mark affected hints stale instead of leaving them to be discovered by a worker. *Verification:* a hint-bearing card stops leasing after a main commit until re-rendered.

**R-10 (P0, done) — Absolute order paths.** `order_prompt()` resolves the worktree; no caller may pass a relative path. Extend the same rule to every path in `ORDER.md` (it already prints absolute write-scope destinations).

**R-11 (P1) — Canary protocol.** One canary card per repair; its oracle must **fail** at the base, must be deterministic, and must never reuse a card whose work is already merged. Record the oracle's pre-run exit code in the evidence. *Verification:* S8 refuses an already-satisfied canary, and the drafted card shows exit 1 on main.

### 12.4 Overseer and governance

**R-12 (P0, done) — Fall through disabled profiles.** Selection must degrade to the next configured profile. **R-12a (P1):** raise an incident after two consecutive `OVERSEER_WOKEN` refusals, so silence cannot persist.

**R-13 (P1) — Make S8 default-on.** Keep the opt-in switch for one canary, then default `precheck_satisfied = true` and require a recorded decision to disable it. *Verification:* a card with a passing oracle is refused in a fresh repo without fleet config.

**R-14 (P2) — Supersede satisfied cards.** When S8 refuses a lease as already satisfied, mark the card `SUPERSEDED` (or propose it) rather than leaving it `READY` to be retried forever. *Verification:* the refusal produces one event and a state change, not a loop.

**R-15 (P0, operator) — Activate the identity guard.** `git config core.hooksPath .githooks` (A8). *Verification:* `git config --get core.hooksPath` returns `.githooks`, and a test commit under the human identity produces a log line without blocking.

### 12.5 Process safeguards for future repairs

**R-16 — Evidence before narrative.** Every "fixed" claim in the final report must cite a command with an exit code, a commit, and the test that would fail if the fix regressed. A claim without output is a hypothesis, not a result.

**R-17 — Diff-stat review.** Review `git show --numstat` for every commit that touches tests. A commit that *deletes* test lines while adding features is a red flag (this is how the `test_overseer_wake.py` clobber was caught). *Verification:* a CI check that fails when a commit's test deletions exceed its test insertions without a matching rename.

**R-18 — Test-count invariant.** Record the collected test count in the checkpoint and fail the repair if it drops without an explicit note. *Verification:* `pytest --collect-only -q | grep -c "::"` compared with the recorded number.

**R-19 — Quarantine, never delete.** Scratch artefacts and drift go to `quarantine/<date>/` with a manifest; live Kernel state (`.pm/events`, `.pm/views`) is never committed as part of a repair.

**R-20 — One canary, one claim.** The final report must not say "verified" for anything that has not been run through a real CLI after the fix. Unit tests prove resolution, not adapter behaviour.

---

## 13. Prevention checklist (operational)

**Before any dispatch (5 minutes)**

- [ ] `git status --porcelain -- <write scope>` is empty (R-09 lease refusal).
- [ ] `pytest -q` exit 0; collected count equals the recorded count.
- [ ] `pmk pins check` → `ok: true`.
- [ ] `core.hooksPath` = `.githooks`.
- [ ] The card's oracle **fails** at the current base.
- [ ] `pmk task show <id>` → `hint_base_commit` non-empty and equal to HEAD.
- [ ] The hint contains no claim that can be falsified by `git ls-tree HEAD`.
- [ ] No other card in the same write scope is `READY`.

**During a run**

- [ ] `AGENT_STARTED` records adapter, pid, worktree under `work/`, log path.
- [ ] The first shell command in the log uses PowerShell forms (if Windows).
- [ ] `python -c "import cna; print(cna.__file__)"` names the worktree, not main.
- [ ] No repeated identical tool failure more than three times.

**After the gate**

- [ ] `ORACLE_RESULT` carries `cmd`, `exit`, and — on failure — `failed_tests` + tails.
- [ ] Merge commit author is `umaws-pilot <umaws-pilot@localhost>`.
- [ ] `IDENTITY_ANOMALY` absent; `SCOPE_CONFLICT` absent.
- [ ] `pmk sentinel` unchanged from the recorded baseline.

---

## 14. Residual risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| A shell-contract text is ignored or the adapter uses a different shell | Medium | Turns wasted, not correctness | R-06 counter; per-adapter dialect (future) |
| Another hidden absolute path in an adapter or venv | Medium | Wrong-tree execution again | R-03 audit; R-02 shadow test |
| S8 prevents legitimate re-work | Low | Card refused incorrectly | Opt-in during canary; override is a recorded decision |
| Hints go stale again | Medium | Wasted attempts | R-08/R-09 |
| A gate flakes and is believed | Low | False REWORK/DONE | R-05; replay the gate twice on failure (future) |
| Model attribution remains impossible | High until R-04 | Debate without evidence | R-04, R-07 |
| Sentinel baseline red masks a new finding | Medium | Missed regression | Diff sentinel before/after each run; OQ-08 |

---

## 15. Evidence index

| Artefact | Path / identifier |
|---|---|
| Canary bundles | `.pm/evidence/EB-T-0148-120/bundle.json`, `.pm/evidence/EB-T-0150-121/bundle.json` |
| Gate events | ledger seq 3141 (exit 1), 3142 (`ORACLE_FAILED`), 3157 (exit 0), 3159 (`INTEGRATED` `e31d70a`) |
| Agent logs | `.pm/fleet/logs/T-0148/120-0.log`, `T-0150/121-0.log`, `T-0146/124-0.log`, `T-0145/{122-0,122-1,123-0,123-8}.log` |
| Overseer log | `.pm/fleet/logs/overseer/0-0.log` (9,029,312 bytes; 168,688 lines; 904 parser failures; 115 main-tree references) |
| Repeated-work evidence | `.pm/fleet/logs/T-0001/{1-0,56-0}.log`; 17/20 logs with `Read .pmwork/ORDER.md failed` |
| Editable hook | `.venv/Lib/site-packages/__editable__.umaws_fleet-0.1.0.pth` → `C:\temp\projects\testproject1\src` |
| Pre-fix gate | `git show 13b8959:src/fleet/merge.py`, lines 248–251 (no `env=`) |
| Hint and base | `pmk task show T-0146` → `hint_base_commit: ""`; `.pmwork/ORDER.md` of `work/T-0146-124` |
| Cards | `pmk task show T-0145/T-0146/T-0148/T-0150` |
| Decisions | `pilot/drafts/decisions-d62-plus.md`; `pilot/decisions.md` (D-58…D-61) |
| Reports | `report-umaws-problems-and-issues-v1.md`; `pilot/repair-dispatch-rootcause-v1.md`; `pilot/cards/canary-replacement-v1.md` |

---

## 16. Reproduction appendix

```bash
# 1. Confirm the editable-install hook
cat .venv/Lib/site-packages/__editable__.umaws_fleet-0.1.0.pth

# 2. Confirm the gate imported the main tree at the canary base
git show 13b8959:src/fleet/merge.py | sed -n '244,254p'

# 3. Reproduce T-0148's gate inputs in a throwaway worktree
git worktree add --detach .pmwork/gate-repro 82f6be1
git -C .pmwork/gate-repro merge --no-ff --no-edit pmk/T-0148-120
( cd .pmwork/gate-repro && PYTHONPATH="$PWD/src;$PWD/tests" \
  /c/temp/projects/testproject1/.venv/Scripts/python.exe -m pytest -q )
git worktree remove --force .pmwork/gate-repro

# 4. Show that imports resolve to main without the pin
( cd .pmwork/gate-repro 2>/dev/null || true )

# 5. Ledger facts
./.venv/Scripts/pmk.exe task show T-0148
./.venv/Scripts/pmk.exe task show T-0150
```

---

## 17. Glossary

| Term | Meaning |
|---|---|
| **Gate** | `gate_cmd` (`pytest -q`) run in a temporary worktree after merging the task branch; the promotion decision. |
| **Oracle** | A card's own acceptance command, run in the task worktree before submission. |
| **Fence** | Monotonic lease number; a stale fence is quarantined, never merged. |
| **Hint** | `agent_hint`, free text written by the Overseer into the card; a claim about a tree at a time. |
| **REC-13** | Refusal to lease a card whose hint asserts tree contents and whose recorded base has moved. |
| **S8** | Pre-lease check that refuses a card whose oracles already pass on the default branch. |
| **Unpinned environment** | A subprocess whose `env` is inherited, so imports may resolve outside the tree under test. |

---

## 18. Change history and distribution

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-11-08 | Buffy (Codebuff) | First issue, covering findings F-01…F-09, corrective actions C-01…C-11, verification, OQ-01…OQ-11 and R-01…R-20. |

**For Claude (Web) and other reviewers.** Every factual claim above is traceable through §15. The two claims most worth challenging are (a) F-02's mechanism, because the failing test is unrecoverable, and (b) F-01's completeness, because it is supported by one `.pth` file, one code reading and one import demonstration — not by a captured gate trace. Reproduce §16.3 before accepting §6. Do not treat the model question as settled in either direction; §7 argues only that the record cannot support attribution, which is why R-04 exists.

**Distribution.** This report is written to be merged into the project's final overall report. It deliberately cites sequence numbers, commit hashes and file paths rather than prose summaries, so a reader without repository access can still distinguish confirmed findings from derived ones and unknown ones.
