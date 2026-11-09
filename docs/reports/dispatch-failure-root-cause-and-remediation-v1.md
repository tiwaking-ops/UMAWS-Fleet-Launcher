---
document:
  title: "Project Report: Dispatch Failure of the UMAWS Fleet — Root Cause, Remediation, and Safeguards (T-0145/T-0146/T-0148/T-0150)"
  status: "Open — engineering remediation landed on local main; supervised canary and decision ratification outstanding; dispatch paused"
  version: "1.2.0"
provenance:
  author_llm:
    name: "Buffy"
    version: "Codebuff agent (freebuff-buffy-01); report version 1.2"
  created_date: "2026-11-08"
  last_modified_date: "2026-11-08"
  scope: "C:\\temp\\projects\\testproject1 (branch main, live repo), local commits c3aaca0..9606757 (never pushed), the Kernel ledger .pm/events/2026-11-07.jsonl and 2026-11-08.jsonl, evidence bundles .pm/evidence/EB-T-0148-120 and EB-T-0150-121, fleet agent logs .pm/fleet/logs/**, task cards T-0145/T-0146/T-0148/T-0150, and one throwaway-worktree reproduction run"
  source_of_truth: "Ledger events by sequence number (seq 3135–3160 for the canary window; 3194–3229 for T-0145/T-0146); bundle.json for EB-T-0148-120 and EB-T-0150-121; agent transcripts .pm/fleet/logs/T-0148/120-0.log, T-0150/121-0.log, T-0146/124-0.log, T-0145/122-0.log, 122-1.log, 123-0.log, and the Overseer log .pm/fleet/logs/overseer/0-0.log; source at the cited commits; measured test runs recorded under .pmwork/*.txt"
---

# Dispatch Failure of the UMAWS Fleet — Root Cause, Remediation, and Safeguards

**Author:** Buffy (Codebuff agent), `freebuff-buffy-01` — **v1.2**
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
| 3212 | 23:10:45 | `MODEL_SERVED` T-0145, `served_models: []` | attribution gap |
| 3225 | 2026-11-08 08:21 | T-0145 `VOID` — actor **unknown** (ledger records `human/operator`) | card superseded |

**Seq 3225 actor.** The ledger actor field says `human/operator`, but the operator has not confirmed typing the command; the draft D-65 claim that Buffy executed it is not evidence. The actor is recorded as **unknown** here.

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

### F-02 — The canary flip is a run property, not a code property (**Derived — mechanism Confirmed, failing test Unknown**)

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

**Honest limit.** Re-running the old unpinned configuration today also exits 0, because current main is consistent with the old tests. The specific 08:43 divergence required main's `src` to differ from the merged tree at that moment, and that state cannot be reconstructed. Which test failed is **Unknown** — the gate discarded its output (F-08). **Confidence.** The mechanism is **Confirmed** by code inspection: the gate had no `env=`. That this mechanism produced the 08:43 flip is **Derived**: the failing output is gone, an unpinned rerun today passes, and a load-dependent flake cannot be excluded (OQ-03). C-08 settles the next occurrence by recording the output.

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

**Fix.** Hint pinning plus `IDENTITY_ANOMALY` landed in `6f92d31`. Existing cards cannot be amended (`pmk task` exposes only `create/admit/list/show/void`); T-0146 remains `READY`, and S8 refuses it because its oracle already passes on main. A replacement canary card was drafted as `pilot/cards/canary-replacement-v1.md`. The card's disposition is left to the operator (OQ-04); this report makes no recommendation on it.

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

- Four commits (`e08fa8d`, `ebe46ce`, `82f6be1`, `9893d94`) carry the operator's human git identity while neighbouring pipeline commits use `umaws-pilot`. The email address is redacted in this report and remains only in the commit objects. Recorded, not rewritten (D-67).
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

1. The recorded failure is consistent with the environment alone: T-0148 and T-0150 carried identical inputs and opposite gate verdicts, and a pinned rerun of T-0148's inputs passes. The reconstruction is **Derived**, not a reproduction — the failing run's output is gone and its precise trigger cannot be recreated (OQ-03).
2. Both correct worker outputs were produced and then misjudged (T-0148's own oracle and scope check passed; T-0145 attempt 2's content was already merged).
3. The observable defect in Overseer output is **wrong state attribution** — describing main while claiming a worktree — with a mechanical explanation (F-01, F-05). That is a grounding failure, not a reasoning failure that would distinguish one model from another.

The only model identities anywhere in the record are the CLI headers: workers `> code · kilo-auto/free` (a router alias, not a model), the Overseer `> build · recursive/flint-v1.0:free`. They are reported as observations only. Nothing found here links either to the failure, and the argument above does not depend on which model served a run — which is precisely the gap R-04 closes.
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

Every entry below is a **DRAFT** record from `pilot/drafts/decisions-d62-plus.md`; none is ratified until A9. D-69 stays blank until a real canary has run.

| Decision | Subject | Status (all DRAFT) |
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
| OQ-04 | T-0146 disposition | open | operator decision; F-04 records the constraints and the options, without recommending one |
| OQ-05 | D-62…D-68 ratification | open | operator (A9) |
| OQ-06 | D-69 canary | open | operator: create/admit the replacement card, run one supervised dispatch |
| OQ-07 | A8 hooks not active | open | `git config core.hooksPath .githooks` |
| OQ-08 | Sentinel red at baseline (5 × I6, 1 × I13) | recorded | accepted as historical; fixing would rewrite the ledger |
| OQ-09 | Decision register duplicates D-35…D-40, missing D-51 | recorded | separate reconciliation |
| OQ-10 | 15 Kernel worktrees vs 26 git worktrees | recorded | separate census decision; nothing deleted |
| OQ-11 | Who authored the four human-identity commits | **Unknown** | D-67 records; hook covers the future only |

**Coverage gaps (review round 11; recorded, not assessed here).** Three subjects sit outside this report's evidence. (a) The REC deletion-safety holes H1–H4 are not analysed; they belong to a REC review. (b) The ledger actor is not analysed: the new hook covers git authorship and only logs, while the `human:tiwa-pene` label on ledger events is untouched. (c) The Overseer resume path is a behaviour change, not a verified repair: its first live session will run on the `kilo-auto` fallback, and its hourly cap still resets on restart. (a) and (b) need their own reviews; (c) needs an operator-supervised run.

---

## 12. Recommendations and safeguards

All recommendations carry the **same priority**; the order below groups them by subject, not by ranking. Items marked *(landed)* are implemented on local `main`; the rest are open. Each names the check that proves it landed.

### 12.1 Environment

**R-01 (landed) — One environment contract.** Every spawned process — oracle, gate, worker, retry, restart, Overseer — must be built by `worktree_env()`. *Verification:* `tools/check_subprocess_env.py` fails on a new `subprocess.run` without `env=`, except the seven reviewed exceptions.

**R-02 — Prove the invariant, not just the helper.** Add a test that a marker module in the worktree shadows a same-named module in main, run through the *gate* path, not only `runenv`. *Verification:* a temporary `cna` shadow package is imported from the worktree.

**R-03 — Do not rely on an editable install for correctness.** Prefer `PYTHONPATH` as the first entry in every execution context and treat the `.pth` as a developer convenience. Document the hard-coded path in `CLAUDE.md`. *Verification:* `python -c "import cna; print(cna.__file__)"` from any worktree names that worktree.

### 12.2 Observability

**R-04 — Record the model that served each run.** Parse the CLI header (`> code · <model>`) at spawn/exit and store it in `AGENT_STARTED` and in the bundle's `resolved_models`, with `source: cli-header`. Keep `kilo-auto` as an alias field, not as the identity. *Verification:* `pmk task show` shows a non-empty model for a direct-CLI profile; bundles stop saying `family: unknown`.

**R-05 — Record gate context, not just its verdict.** Add `base_head`, `merged_head` and `duration_s` to the gate `ORACLE_RESULT`. *Verification:* a failing gate event shows all three plus `failed_tests`.

**R-06 — Fail fast on shell-dialect damage.** Count tool-command failures per run by class (`parser`, `notfound`, `timeout`) and record the count at `AGENT_EXITED`; warn above a threshold, revoke above a higher one. *Verification:* a synthetic run with ten failing commands produces the counter.

**R-07 — Never call a failure class "model" without evidence.** Adopt the rule that a failure may be attributed to a model only when (a) the served model is recorded and (b) the same card, base and environment passes on another model. Until then the class is `UNKNOWN` with the environment checked first.

### 12.3 Task cards and hints

**R-08 — A hint must carry its base.** `pmk task create --agent-hint` already pins `hint_base_commit`; extend `_stale_hint_reason()` to refuse an **empty** base when the hint contains any `_HINT_STALE_TOKENS`. *Verification:* a card created by an older path is refused with a clear message; T-0146 becomes a test fixture.

**R-09 — Re-render hints when HEAD moves.** An Overseer wake after a merge should mark affected hints stale instead of leaving them to be discovered by a worker. *Verification:* a hint-bearing card stops leasing after a main commit until re-rendered.

**R-10 (landed) — Absolute order paths.** `order_prompt()` resolves the worktree; no caller may pass a relative path. Extend the same rule to every path in `ORDER.md` (it already prints absolute write-scope destinations).

**R-11 — Canary protocol.** One canary card per repair; its oracle must **fail** at the base, must be deterministic, and must never reuse a card whose work is already merged. Record the oracle's pre-run exit code in the evidence. *Verification:* S8 refuses an already-satisfied canary, and the drafted card shows exit 1 on main.

### 12.4 Overseer and governance

**R-12 (landed) — Fall through disabled profiles.** Selection must degrade to the next configured profile. **R-12a:** raise an incident after two consecutive `OVERSEER_WOKEN` refusals, so silence cannot persist.

**R-13 — Make S8 default-on.** Keep the opt-in switch for one canary, then default `precheck_satisfied = true` and require a recorded decision to disable it. *Verification:* a card with a passing oracle is refused in a fresh repo without fleet config.

**R-14 — Record why a refused card stays in the queue.** A card that S8 refuses as already satisfied should carry the refusal reason on the card, so the queue reflects reality. Whether it is then voided, superseded or amended stays an operator decision. *Verification:* the refusal produces one recorded reason, not an anonymous retry loop.

**R-15 (operator action) — Activate the identity guard.** `git config core.hooksPath .githooks` (A8). *Verification:* `git config --get core.hooksPath` returns `.githooks`, and a test commit under the human identity produces a log line without blocking.

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

# 4. Show that imports resolve to main, not the tree under test
#    (works from any cwd; the .pth points at the main src; `cna` is a
#     namespace package, so import a module that has a file)
( cd "$(mktemp -d)" && /c/temp/projects/testproject1/.venv/Scripts/python.exe -c "import cna.tools.coverage as m; print(m.__file__)" )
# expect C:/temp/projects/testproject1/src/cna/tools/coverage.py, not the cwd

# 5. Ledger facts
./.venv/Scripts/pmk.exe task show T-0148
./.venv/Scripts/pmk.exe task show T-0150
```

---

## 17. Transcript appendix (verbatim evidence)

The six fleet agent logs cited in §15 are reproduced in full, exactly as written apart from ANSI colour escapes removed. Line and byte counts are stated so a reader can confirm nothing was elided. The Overseer log is 9,028,312 bytes and 168,688 lines; reproducing it whole would swamp the report, so A.7 gives two labelled extracts with their line numbers. The rest of that log is homogeneous 429 retry output.

**Reading note.** These transcripts contain the agents' own conclusions, including statements that are false about the repository (for example that the 66-file corpus existed only as untracked files). They are evidence of what each agent believed and did, not of the repository state; §5 and §15 give the verified state.

### A.1 `.pm/fleet/logs/T-0148/120-0.log` — 20 lines, 799 bytes

```text

> code · kilo-auto/free

→ Read .pmwork/ORDER.md
✗ Read .pmwork/HANDOFF.md failed
Error: File not found: C:\temp\projects\testproject1\work\T-0148-120\.pmwork\HANDOFF.md

$ Test-Path "C:\temp\projects\testproject1\work\T-0148-120\docs"
True

← Write docs/canary.md
Wrote file successfully.

$ python -c "import pathlib; p = pathlib.Path('docs/canary.md'); assert p.is_file() and 'CANARY_PASS' in p.read_text(); print('canary-pass')"
canary-pass

← Write .pmwork/RESULT.md
Wrote file successfully.

Done. Created `docs/canary.md` with `CANARY_PASS`, verified with the harness check command (printed `canary-pass`), and wrote `.pmwork/RESULT.md`. No other files touched, no commit.
```

### A.2 `.pm/fleet/logs/T-0150/121-0.log` — 14 lines, 530 bytes

```text

> code · kilo-auto/free

→ Read .pmwork/ORDER.md
✗ Read .pmwork/HANDOFF.md failed
Error: File not found: C:\temp\projects\testproject1\work\T-0150-121\.pmwork\HANDOFF.md

← Write docs/canary.md
Wrote file successfully.

← Write .pmwork/RESULT.md
Wrote file successfully.

Done. docs/canary.md contains exactly one line: `CANARY_PASS`. No other files touched, nothing committed. `.pmwork/RESULT.md` written with what was done and test notes.
```

### A.3 `.pm/fleet/logs/T-0146/124-0.log` — 355 lines, 21203 bytes

```text

> code · kilo-auto/free

→ Read .pmwork/ORDER.md
✗ Read .pmwork/HANDOFF.md failed
Error: File not found: C:\temp\projects\testproject1\work\T-0146-124\.pmwork\HANDOFF.md

$ ls -la C:\temp\projects\testproject1\work\T-0146-124
Get-ChildItem : A parameter cannot be found that matches parameter name 'la'.
At line:4 char:4
+ ls -la C:\temp\projects\testproject1\work\T-0146-124
+    ~~~
    + CategoryInfo          : InvalidArgument: (:) [Get-ChildItem], ParameterBindingException
    + FullyQualifiedErrorId : NamedParameterNotFound,Microsoft.PowerShell.Commands.GetChildItemCommand

I'll start by exploring the worktree structure and understanding the current state.
$ ls -la C:\temp\projects\testproject1\work\T-0146-124\docs 2>/dev/null; echo "---"; ls -la C:\temp\projects\testproject1\work\T-0146-124\docs\rules 2>/dev/null
Get-ChildItem : A parameter cannot be found that matches parameter name 'la'.
At line:4 char:4
+ ls -la C:\temp\projects\testproject1\work\T-0146-124\docs 2>/dev/null ...
+    ~~~
    + CategoryInfo          : InvalidArgument: (:) [Get-ChildItem], ParameterBindingException
    + FullyQualifiedErrorId : NamedParameterNotFound,Microsoft.PowerShell.Commands.GetChildItemCommand
 
---
Get-ChildItem : A parameter cannot be found that matches parameter name 'la'.
At line:4 char:87
+ ... project1\work\T-0146-124\docs 2>/dev/null; echo "---"; ls -la C:\temp ...
+                                                               ~~~
    + CategoryInfo          : InvalidArgument: (:) [Get-ChildItem], ParameterBindingException
    + FullyQualifiedErrorId : NamedParameterNotFound,Microsoft.PowerShell.Commands.GetChildItemCommand

$ ls -la C:\temp\projects\testproject1\work\T-0146-124\src\cna\tools 2>/dev/null; echo "---"; ls -la C:\temp\projects\testproject1\work\T-0146-124\coverage 2>/dev/null; echo "---"; ls -la C:\temp\projects\testproject1\work\T-0146-124\tests 2>/dev/null
Get-ChildItem : A parameter cannot be found that matches parameter name 'la'.
---
---
At line:4 char:4
+ ls -la C:\temp\projects\testproject1\work\T-0146-124\src\cna\tools 2> ...
+    ~~~
    + CategoryInfo          : InvalidArgument: (:) [Get-ChildItem], ParameterBindingException
    + FullyQualifiedErrorId : NamedParameterNotFound,Microsoft.PowerShell.Commands.GetChildItemCommand
 
Get-ChildItem : A parameter cannot be found that matches parameter name 'la'.
At line:4 char:96
+ ... work\T-0146-124\src\cna\tools 2>/dev/null; echo "---"; ls -la C:\temp ...
+                                                               ~~~
    + CategoryInfo          : InvalidArgument: (:) [Get-ChildItem], ParameterBindingException
    + FullyQualifiedErrorId : NamedParameterNotFound,Microsoft.PowerShell.Commands.GetChildItemCommand
 
Get-ChildItem : A parameter cannot be found that matches parameter name 'la'.
At line:4 char:183
+ ... ect1\work\T-0146-124\coverage 2>/dev/null; echo "---"; ls -la C:\temp ...
+                                                               ~~~
    + CategoryInfo          : InvalidArgument: (:) [Get-ChildItem], ParameterBindingException
    + FullyQualifiedErrorId : NamedParameterNotFound,Microsoft.PowerShell.Commands.GetChildItemCommand

→ Read .
→ Read src/cna/tools
PowerShell shell — `ls -la` isn't valid. Let me use the Read tool for directories instead.
→ Read src/cna/tools/coverage.py
→ Read HANDOFF.md
→ Read docs/rules
→ Read docs/rules/sections
→ Read coverage
→ Read tests
The worktree already has CNA-Rules.adoc and sections/. Let me verify the corpus is complete and check the sources mentioned in the order.
→ Read coverage/rules_coverage.json

$ ls "C:/temp/projects/testproject1/work/T-0097-49/docs/rules" 2>/dev/null; echo "=== main tree ==="; ls "C:/temp/projects/testproject1/docs/rules" 2>/dev/null; echo "=== upstream ==="; ls "C:/temp/projects/cfna/docs/sources/cna-rules-upstream" 2>/dev/null
=== main tree ===


    Directory: C:\temp\projects\testproject1\docs\rules


Mode                 LastWriteTime         Length Name                                                                               
----                 -------------         ------ ----                                                                               
d-----         2/11/2026  12:28 am                sections                                                                           
-a----         3/11/2026   9:54 am           5996 checksums.sha256                                                                   
-a----         3/11/2026   9:24 am           5881 CNA-Rules.adoc                                                                     
-a----         1/11/2026   9:53 pm            506 fleet-spawning.md                                                                  
-a----         8/11/2026  12:05 pm         638735 index.json                                                                         
-a----         1/11/2026   9:53 pm            551 kernel-writing.md                                                                  
-a----         3/11/2026   9:54 am           6673 manifest.json                                                                      
-a----         1/11/2026   9:53 pm            444 windows-platform.md                                                                
=== upstream ===


    Directory: C:\temp\projects\cfna\docs\sources\cna-rules-upstream


Mode                 LastWriteTime         Length Name                                                                               
----                 -------------         ------ ----                                                                               
d-----        31/10/2026   7:09 pm                .github                                                                            
d-----        31/10/2026   7:09 pm                images                                                                             
d-----        31/10/2026   7:09 pm                sections                                                                           
-a----        31/10/2026   7:09 pm             47 .gitignore                                                                         
-a----        31/10/2026   7:09 pm           6059 CNA-Rules.adoc                                                                     
-a----        31/10/2026   7:09 pm           1448 README.md

→ Read tests/test_coverage.py
The corpus is present (66 files). Let me verify it against a verified source and examine the current coverage state.
Let me verify the worktree corpus matches a verified source, then examine the current coverage tool behavior.

$ $wt="C:\temp\projects\testproject1\work\T-0146-124"; $main="C:\temp\projects\testproject1"; $ok=$true; $diffs=@(); $n=0; (Get-ChildItem -Path "$wt\docs\rules" -Recurse -File) | ForEach-Object { $rel = $_.FullName.Replace("$wt\docs\rules\", ""); $mp = Join-Path $main "docs/rules/$rel"; $n++; if (-not (Test-Path $mp)) { $diffs += "MISSING-MAIN: $rel"; $ok=$false; return }; $a=(Get-FileHash -Path $_.FullName -Algorithm SHA256).Hash; $b=(Get-FileHash -Path $mp -Algorithm SHA256).Hash; if ($a -ne $b) { $diffs += "DIFF: $rel ($a vs $b)"; $ok=$false } }; Write-Host "worktree files: $n"; Write-Host "main files: $((Get-ChildItem -Path '$main\docs\rules' -Recurse -File).Count)"; if ($diffs.Count -gt 0) { Write-Host "DIFFERENCES:"; $diffs | ForEach-Object { Write-Host "  $_" } } else { Write-Host "CORPUS BYTE-IDENTICAL TO MAIN TREE" }
worktree files: 72
Get-ChildItem : Cannot find path 'C:\temp\projects\testproject1\work\T-0146-124\$main\docs\' because it does not exist.
main files: 0
At line:4 char:615
+ ... n files: $((Get-ChildItem -Path '$main\docs\rules' -Recurse -File).Co ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:\temp\project...124\$main\docs\:String) [Get-ChildItem], ItemNotFoundException
    + FullyQualifiedErrorId : PathNotFound,Microsoft.PowerShell.Commands.GetChildItemCommand
 
CORPUS BYTE-IDENTICAL TO MAIN TREE

← Write C:/Users/Tiwa Pene/AppData/Local/Temp/kilo/verify_corpus.ps1
Wrote file successfully.

I'll write a verification script to avoid shell quoting issues.
$ & "C:\Users\Tiwa Pene\AppData\Local\Temp\kilo\verify_corpus.ps1"
worktree files: 72
main files: 72
DONE

→ Read docs/rules/CNA-Rules.adoc [limit=40]
→ Read docs/rules/sections/section-01.adoc [limit=40]
→ Read docs/rules/manifest.json
The corpus is byte-identical. Now let me examine the corpus files and understand the frontmatter format.
✗ Read src/cna/__init__.py failed
Error: File not found: C:\temp\projects\testproject1\work\T-0146-124\src\cna\__init__.py

$ cd "C:/temp/projects/testproject1/work/T-0146-124" && python -m cna.tools.coverage --check; echo "EXIT=$?"
At line:4 char:52
+ cd "C:/temp/projects/testproject1/work/T-0146-124" && python -m cna.t ...
+                                                    ~~
The token '&&' is not a valid statement separator in this version.
    + CategoryInfo          : ParserError: (:) [], ParentContainsErrorRecordException
    + FullyQualifiedErrorId : InvalidEndOfLine

The corpus is byte-identical to the main tree. Now let me run the current coverage tool to see its behavior, then check the test file and how the package is structured.
→ Read src/cna
→ Read pyproject.toml

$ cd "C:/temp/projects/testproject1/work/T-0146-124" & python -m cna.tools.coverage --check
At line:4 char:52
+ cd "C:/temp/projects/testproject1/work/T-0146-124" & python -m cna.to ...
+                                                    ~
The ampersand (&) character is not allowed. The & operator is reserved for future use; wrap an ampersand in double quotation marks 
("&") to pass it as part of a string.
    + CategoryInfo          : ParserError: (:) [], ParentContainsErrorRecordException
    + FullyQualifiedErrorId : AmpersandNotAllowed

$ python -m cna.tools.coverage --check
rules-coverage: coverage\rules_coverage.json is stale; rebuild it

← Edit src/cna/tools/coverage.py
Index: C:\temp\projects\testproject1\work\T-0146-124\src\cna\tools\coverage.py
===================================================================
--- C:\temp\projects\testproject1\work\T-0146-124\src\cna\tools\coverage.py
+++ C:\temp\projects\testproject1\work\T-0146-124\src\cna\tools\coverage.py
@@ -1,7 +1,7 @@
 """Rules-coverage tool for the CNA digital edition.
 
-Every vendored rules file (``docs/rules/`` by default) declares, in its YAML
+Every vendored rules file (``docs/rules/`` by default) declares, in its
 frontmatter, which parts of the repository it governs::
 
     ---
     paths:
@@ -17,8 +17,13 @@
 * **rules** — each rule file, its declared globs, and the paths it matches;
 * **uncovered_paths** — every scanned path that no rule file claims;
 * **counts** — the headline numbers (paths, covered, uncovered, rule files).
 
+The rules corpus is a flat directory of Markdown (``*.md``) platform rules
+plus a large AsciiDoc (``*.adoc``) edition (a top-level ``CNA-Rules.adoc``
+and ``sections/section-01..65.adoc``).  Rule files are therefore discovered
+**recursively** under the rules root, and both suffixes are accepted.
+
 Design notes
 ------------
 * Standard library only; Windows-native (BOM-tolerant reads, atomic replace).
 * Deterministic: the same inputs always yield byte-identical JSON, so the
@@ -27,9 +32,10 @@
   ``src/pmk/**`` does *not* match ``src/pmk`` itself); ``*`` and ``?`` stay
   within a single segment; ``[...]`` is a character class.  Paths are compared
   in POSIX form (forward slashes) and case-sensitively.
 * Frontmatter is parsed leniently: a rule file with no usable ``paths`` block
-  is reported as matching nothing rather than failing the run.
+  (including AsciiDoc files that carry no frontmatter at all) is reported as
+  matching nothing rather than failing the run.
 * Text in the corpus is data.  Nothing here executes, imports or follows
   instructions found in the rules files.
 
 Usage::


The current report is stale (built against only 3 `.md` files). The corpus is byte-identical to the verified main tree. Now let me implement the recursive discovery change in `coverage.py`.
← Edit src/cna/tools/coverage.py
Index: C:\temp\projects\testproject1\work\T-0146-124\src\cna\tools\coverage.py
===================================================================
--- C:\temp\projects\testproject1\work\T-0146-124\src\cna\tools\coverage.py
+++ C:\temp\projects\testproject1\work\T-0146-124\src\cna\tools\coverage.py
@@ -81,9 +81,15 @@
 
 #: Suffixes that are never source files worth reporting on.
 SKIP_SUFFIXES = {".pyc", ".pyo", ".lock"}
 
+#: Suffixes that identify a vendored rules file.  The corpus is a flat set of
+#: Markdown platform rules (``*.md``) plus a large AsciiDoc edition (a
+#: top-level ``CNA-Rules.adoc`` and ``sections/section-01..65.adoc``), so
+#: discovery walks the rules root recursively and accepts both.
+RULE_SUFFIXES = {".md", ".adoc"}
 
+
 class RulesCoverageError(RuntimeError):
     """Raised for operator errors: a missing rules dir, an unreadable output."""
 
 


Now let me update the discovery logic to walk recursively and accept both `.md` and `.adoc` suffixes:
← Edit src/cna/tools/coverage.py
Index: C:\temp\projects\testproject1\work\T-0146-124\src\cna\tools\coverage.py
===================================================================
--- C:\temp\projects\testproject1\work\T-0146-124\src\cna\tools\coverage.py
+++ C:\temp\projects\testproject1\work\T-0146-124\src\cna\tools\coverage.py
@@ -257,18 +257,16 @@
 scanned = sorted(set(str(p).replace("\\", "/").lstrip("/") for p in paths))
 covered: set[str] = set()
 rules: list[dict[str, Any]] = []
 
-for path in sorted(directory.iterdir()):
-    if not path.is_file() or path.suffix.lower() != ".md":
-        continue
+for path in sorted(_iter_rule_files(directory)):
     text = read_text(path)
     globs, _has = _frontmatter_paths(text)
     matched = sorted(p for p in scanned if any(glob_matches(g, p) for g in globs))
     covered.update(matched)
     rules.append(
         {
-            "file": path.name,
+            "file": path.relative_to(directory).as_posix(),
             "globs": globs,
             "match_count": len(matched),
             "matching": bool(matched),
             "matched_paths": matched,


← Edit src/cna/tools/coverage.py
Index: C:\temp\projects\testproject1\work\T-0146-124\src\cna\tools\coverage.py
===================================================================
--- C:\temp\projects\testproject1\work\T-0146-124\src\cna\tools\coverage.py
+++ C:\temp\projects\testproject1\work\T-0146-124\src\cna\tools\coverage.py
@@ -335,13 +335,24 @@
 # small shared helpers
 # --------------------------------------------------------------------------
 
 
-def read_text(path: Path) -> str:
-    """Read a text file BOM-tolerantly (PowerShell writes ``utf-8-sig``)."""
-    return path.read_text(encoding="utf-8-sig", errors="replace")
+def _iter_rule_files(directory: Path) -> list[Path]:
+    """Yield every vendored rules file under ``directory``, recursively.
 
+    Discovery is stdlib-only (``os.walk``) and accepts both Markdown
+    (``*.md``) platform rules and AsciiDoc (``*.adoc``) edition files.  The
+    result is sorted for determinism.
+    """
+    found: list[Path] = []
+    for dirpath, dirnames, filenames in os.walk(directory):
+        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
+        for filename in sorted(filenames):
+            if Path(filename).suffix.lower() in RULE_SUFFIXES:
+                found.append(Path(dirpath) / filename)
+    return sorted(found)
 
+
 # --------------------------------------------------------------------------
 # command line
 # --------------------------------------------------------------------------
 


Now I'll add the `_iter_rule_files` helper function. Let me place it near the other scanning primitives:
← Edit src/cna/tools/coverage.py
Index: C:\temp\projects\testproject1\work\T-0146-124\src\cna\tools\coverage.py
===================================================================
--- C:\temp\projects\testproject1\work\T-0146-124\src\cna\tools\coverage.py
+++ C:\temp\projects\testproject1\work\T-0146-124\src\cna\tools\coverage.py
@@ -351,8 +351,13 @@
                 found.append(Path(dirpath) / filename)
     return sorted(found)
 
 
+def read_text(path: Path) -> str:
+    """Read a text file BOM-tolerantly (PowerShell writes ``utf-8-sig``)."""
+    return path.read_text(encoding="utf-8-sig", errors="replace")
+
+
 # --------------------------------------------------------------------------
 # command line
 # --------------------------------------------------------------------------
 


I accidentally replaced `read_text`. Let me fix that:
→ Read src/cna/tools/coverage.py [offset=315, limit=60]
→ Read src/cna/tools/coverage.py [limit=35, offset=245]

$ python -c "import cna.tools.coverage as c; print(len(c._iter_rule_files(__import__('pathlib').Path('docs/rules'))))"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
AttributeError: module 'cna.tools.coverage' has no attribute '_iter_rule_files'

$ python -c "import cna.tools.coverage as c; print([n for n in dir(c) if 'iter' in n.lower() or 'rule' in n.lower()])"
['DEFAULT_RULES_DIRNAME', 'Iterable', 'RulesCoverageError', 'iter_source_paths']

→ Read src/cna/tools/coverage.py [limit=25, offset=80]

$ python -c "import cna.tools.coverage as c; print(c.__file__)"
C:\temp\projects\testproject1\src\cna\tools\coverage.py

$ python -c "import sys; print([p for p in sys.path if 'testproject1' in p])"; echo "---"; python -c "import cna; print(cna.__path__)"
['C:\\temp\\projects\\testproject1\\src']
---
_NamespacePath(['C:\\temp\\projects\\testproject1\\src\\cna'])

→ Read tests/test_coverage.py [limit=12]
The installed `cna` package shadows my worktree. I need to use `PYTHONPATH` pointing to the worktree `src`. Let me check how the tests handle this:

$ python -c "import site; print(site.getsitepackages())"; echo "---pth---"; python -c "import sys; print([p for p in sys.path])"
['C:\\Users\\Tiwa Pene\\AppData\\Local\\Programs\\Python\\Python312', 'C:\\Users\\Tiwa Pene\\AppData\\Local\\Programs\\Python\\Python312\\Lib\\site-packages']
---pth---
['', 'C:\\Users\\Tiwa Pene\\AppData\\Local\\Programs\\Python\\Python312\\python312.zip', 'C:\\Users\\Tiwa Pene\\AppData\\Local\\Programs\\Python\\Python312\\DLLs', 'C:\\Users\\Tiwa Pene\\AppData\\Local\\Programs\\Python\\Python312\\Lib', 'C:\\Users\\Tiwa Pene\\AppData\\Local\\Programs\\Python\\Python312', 'C:\\Users\\Tiwa Pene\\AppData\\Roaming\\Python\\Python312\\site-packages', 'C:\\Users\\Tiwa Pene\\AppData\\Local\\Programs\\Python\\Python312\\Lib\\site-packages', 'C:\\temp\\projects\\testproject1\\src', 'C:\\Users\\Tiwa Pene\\AppData\\Local\\Programs\\Python\\Python312\\Lib\\site-packages\\win32', 'C:\\Users\\Tiwa Pene\\AppData\\Local\\Programs\\Python\\Python312\\Lib\\site-packages\\win32\\lib', 'C:\\Users\\Tiwa Pene\\AppData\\Local\\Programs\\Python\\Python312\\Lib\\site-packages\\pythonwin']

$ python -c "import cna.tools.coverage as c; print(c.__file__)"
C:\temp\projects\testproject1\src\cna\tools\coverage.py

$ PYTHONPATH="C:/temp/projects/testproject1/work/T-0146-124/src" python -c "import cna.tools.coverage as c; print(c.__file__); print(len(c._iter_rule_files(__import__('pathlib').Path('docs/rules'))))"
PYTHONPATH=C:/temp/projects/testproject1/work/T-0146-124/src : The term 
'PYTHONPATH=C:/temp/projects/testproject1/work/T-0146-124/src' is not recognized as the name of a cmdlet, function, script file, or 
operable program. Check the spelling of the name, or if a path was included, verify that the path is correct and try again.
At line:4 char:1
+ PYTHONPATH="C:/temp/projects/testproject1/work/T-0146-124/src" python ...
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (PYTHONPATH=C:/t.../T-0146-124/src:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException

$ $env:PYTHONPATH="C:\temp\projects\testproject1\work\T-0146-124\src"; python -c "import cna.tools.coverage as c; print(c.__file__); print(len(c._iter_rule_files(__import__('pathlib').Path('docs/rules'))))"
C:\temp\projects\testproject1\work\T-0146-124\src\cna\tools\coverage.py
69

```

### A.4 `.pm/fleet/logs/T-0145/122-0.log` — 314 lines, 19313 bytes

```text

> code · kilo-auto/free

✗ Read .pmwork/HANDOFF.md failed
Error: File not found: C:\temp\projects\testproject1\work\T-0145-122\.pmwork\HANDOFF.md
→ Read .pmwork/ORDER.md

$ ls "C:/temp/projects/testproject1/docs/rules" | head; echo "---"; ls "C:/temp/projects/testproject1/docs/rules/sections" 2>/dev/null | head; echo "count:"; ls "C:/temp/projects/testproject1/docs/rules/sections" 2>/dev/null | wc -l; echo "worktree rules:"; ls "C:/temp/projects/testproject1/work/T-0145-122/docs/rules" 2>/dev/null
head : The term 'head' is not recognized as the name of a cmdlet, function, script file, or operable program. Check the spelling of 
the name, or if a path was included, verify that the path is correct and try again.
At line:4 char:49
+ ls "C:/temp/projects/testproject1/docs/rules" | head; echo "---"; ls  ...
+                                                 ~~~~
    + CategoryInfo          : ObjectNotFound: (head:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
---
head : The term 'head' is not recognized as the name of a cmdlet, function, script file, or operable program. Check the spelling of 
count:
the name, or if a path was included, verify that the path is correct and try again.
At line:4 char:136
+ ... projects/testproject1/docs/rules/sections" 2>/dev/null | head; echo " ...
+                                                              ~~~~
    + CategoryInfo          : ObjectNotFound: (head:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
wc : The term 'wc' is not recognized as the name of a cmdlet, function, script file, or operable program. Check the spelling of the 
name, or if a path was included, verify that the path is correct and try again.
At line:4 char:226
+ ... p/projects/testproject1/docs/rules/sections" 2>/dev/null | wc -l; ech ...
+                                                                ~~
    + CategoryInfo          : ObjectNotFound: (wc:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
worktree rules:


    Directory: C:\temp\projects\testproject1\work\T-0145-122\docs\rules


Mode                 LastWriteTime         Length Name                                                                               
----                 -------------         ------ ----                                                                               
d-----         8/11/2026   9:43 am                sections                                                                           
-a----         8/11/2026   9:43 am           5996 checksums.sha256                                                                   
-a----         8/11/2026   9:43 am           5881 CNA-Rules.adoc                                                                     
-a----         8/11/2026   9:43 am            506 fleet-spawning.md                                                                  
-a----         8/11/2026   9:43 am           4394 index.json                                                                         
-a----         8/11/2026   9:43 am            551 kernel-writing.md                                                                  
-a----         8/11/2026   9:43 am           6673 manifest.json                                                                      
-a----         8/11/2026   9:43 am            444 windows-platform.md

$ Get-ChildItem "C:/temp/projects/testproject1/work/T-0145-122/docs/rules/sections" | Measure-Object; echo "---"; Get-ChildItem "C:/temp/projects/testproject1/work/T-0145-122/docs/rules/sections" | Select-Object -First 3
Count    : 65
Average  : 
Sum      : 
Maximum  : 
Minimum  : 
Property : 

---
LastWriteTime : 8/11/2026 9:43:49 am
Length        : 1698
Name          : section-01.adoc

LastWriteTime : 8/11/2026 9:43:49 am
Length        : 5148
Name          : section-02.adoc

LastWriteTime : 8/11/2026 9:43:49 am
Length        : 18471
Name          : section-03.adoc

→ Read src/cna/tools/rules_index.py

$ grep -r "^=\{1,3\} " "C:/temp/projects/testproject1/work/T-0145-122/docs/rules" -m 10 | head -20; echo "anchor attr sample:"; grep -rn "^\[#.*\]" "C:/temp/projects/testproject1/work/T-0145-122/docs/rules" | head -10
grep : The term 'grep' is not recognized as the name of a cmdlet, function, script file, or operable program. Check the spelling of 
the name, or if a path was included, verify that the path is correct and try again.
At line:4 char:1
+ grep -r "^=\{1,3\} " "C:/temp/projects/testproject1/work/T-0145-122/d ...
+ ~~~~
    + CategoryInfo          : ObjectNotFound: (grep:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
anchor attr sample:
grep : The term 'grep' is not recognized as the name of a cmdlet, function, script file, or operable program. Check the spelling of 
the name, or if a path was included, verify that the path is correct and try again.
At line:4 char:127
+ ... ocs/rules" -m 10 | head -20; echo "anchor attr sample:"; grep -rn "^\ ...
+                                                              ~~~~
    + CategoryInfo          : ObjectNotFound: (grep:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException

$ Select-String -Path "C:/temp/projects/testproject1/work/T-0145-122/docs/rules/CNA-Rules.adoc" -Pattern "^={1,3} " | Select-Object -First 10; echo "---attr---"; Select-String -Path "C:/temp/projects/testproject1/work/T-0145-122/docs/rules/sections/section-01.adoc" -Pattern "^\[" | Select-Object -First 10
docs\rules\CNA-Rules.adoc:7:= The Campaign for North Africa : The dessert war 1940-43
---attr---
docs\rules\sections\section-01.adoc:3:[#1_0]

$ Get-Content "C:/temp/projects/testproject1/work/T-0145-122/docs/rules/sections/section-01.adoc" | Select-Object -First 20
= The Land Game

[#1_0]
== Introduction

*The Campaign for North Africa* (CNA) is a simulation of actual operations in Libya and Egypt from 1940 through early 1943. CNA was designed as a definitive simulation intended for the sophisticated wargamer and the serious student of history. As such, CNA is the most logistically oriented game ever designed and may be considered by some to be overly complex.

In fact, the game system itself is quickly absorbed, and most experienced players will have little problem understanding how to play the game. At the same time, there is a ferocious amount of information for the players to digest and use. The assimilation and coordination of all this information is what makes CNA so formative, challenging, and (hopefully) enlightening. Very little has been abstracted; CNA contains more hard information on the subject than any other single source encountered by the SPI design staff.

CNA is not a game for one, two, or even three players. This is a multi-player game in the true sense of the word. For maximum playability and efficiency, it is recommended that, on each side, one person be assigned to Logistics, one person to Air Forces command, and at least three players to Land Forces command (again, per side). It is also strongly suggested that at least one calculator be available.

Although the rules are quite long, CNA is relatively easy to explain. Someone familiar with the rules can tell other players how to play with remarkable ease.

Each hex represents approximately eight kilometers; each Game-Turn represents one week of â€œreal" time. Units range in size from companies (approximately 100 men) to divisions (approximately 15,000 men).

← Edit src/cna/tools/rules_index.py
Index: C:\temp\projects\testproject1\work\T-0145-122\src\cna\tools\rules_index.py
===================================================================
--- C:\temp\projects\testproject1\work\T-0145-122\src\cna\tools\rules_index.py
+++ C:\temp\projects\testproject1\work\T-0145-122\src\cna\tools\rules_index.py
@@ -75,9 +75,10 @@
 # --------------------------------------------------------------------------
 
 _FENCE_RE = re.compile(r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
 _ATX_RE = re.compile(r"^(?P<hashes>#{1,6})[ \t]+(?P<text>.+?)[ \t]*#*[ \t]*$")
-_OUTLINE_RE = re.compile(r"^(?P<num>\d+(?:\.\d+)*)[.)]?[ \t]+(?P<rest>.*)$")
+_ADOC_HEADING_RE = re.compile(r"^(?P<hashes>={1,6})[ \t]+(?P<text>.+?)\s*$")
+_ADOC_ANCHOR_ATTR_RE = re.compile(r"^\[#(?P<id>[^\]]+)\]\s*$")_OUTLINE_RE = re.compile(r"^(?P<num>\d+(?:\.\d+)*)[.)]?[ \t]+(?P<rest>.*)$")
 _SEP_RE = re.compile(r"^[ \t]*\|?[ \t]*:?-{1,}:?[ \t]*(?:\|[ \t]*:?-{1,}:?[ \t]*)*\|?[ \t]*$")
 _HTML_ANCHOR_RE = re.compile(r"""<a\s+(?:id|name)\s*=\s*(?P<q>["'])(?P<id>[^"']+)(?P=q)\s*>""", re.I)
 _PANDOC_ANCHOR_RE = re.compile(r"\{#(?P<id>[A-Za-z0-9_.:\-]+)\}\s*$")
 _RULE_ID_RE = re.compile(r"(?<![\w/.-])R-(?P<num>\d{1,4})(?!\.?\d)(?![\w-])")


← Edit src/cna/tools/rules_index.py
Index: C:\temp\projects\testproject1\work\T-0145-122\src\cna\tools\rules_index.py
===================================================================
--- C:\temp\projects\testproject1\work\T-0145-122\src\cna\tools\rules_index.py
+++ C:\temp\projects\testproject1\work\T-0145-122\src\cna\tools\rules_index.py
@@ -226,16 +226,29 @@
 line = lines[index]
 if number in code:
     continue
 
+adoc_anchor = _ADOC_ANCHOR_ATTR_RE.match(line)
+if adoc_anchor:
+    pending_adoc_anchor = adoc_anchor.group("id")
+    continue
+
 heading = _ATX_RE.match(line)
-if heading:
-    level = len(heading.group("hashes"))
-    title = heading.group("text").strip()
-    pandoc = _PANDOC_ANCHOR_RE.search(title)
-    explicit_slug = pandoc.group("id") if pandoc else None
-    if pandoc:
-        title = title[: pandoc.start()].strip()
+adoc_heading = _ADOC_HEADING_RE.match(line)
+if heading or adoc_heading:
+    if adoc_heading and not heading:
+        level = len(adoc_heading.group("hashes"))
+        title = adoc_heading.group("text").strip()
+        pandoc = None
+        explicit_slug = pending_adoc_anchor
+    else:
+        level = len(heading.group("hashes"))
+        title = heading.group("text").strip()
+        pandoc = _PANDOC_ANCHOR_RE.search(title)
+        explicit_slug = pandoc.group("id") if pandoc else None
+        if pandoc:
+            title = title[: pandoc.start()].strip()
+    pending_adoc_anchor = None
     counters[level] = counters.get(level, 0) + 1
     for deeper in list(counters):
         if deeper > level:
             counters.pop(deeper)


← Edit src/cna/tools/rules_index.py
Index: C:\temp\projects\testproject1\work\T-0145-122\src\cna\tools\rules_index.py
===================================================================
--- C:\temp\projects\testproject1\work\T-0145-122\src\cna\tools\rules_index.py
+++ C:\temp\projects\testproject1\work\T-0145-122\src\cna\tools\rules_index.py
@@ -212,8 +212,9 @@
 counters: dict[int, int] = {}
 stack: list[dict[str, Any]] = []  # open sections, outermost first
 current: dict[str, Any] | None = None
 warnings: list[str] = []
+pending_adoc_anchor: str | None = None
 
 number = 0
 index = -1
 while True:


← Edit src/cna/tools/rules_index.py
Index: C:\temp\projects\testproject1\work\T-0145-122\src\cna\tools\rules_index.py
===================================================================
--- C:\temp\projects\testproject1\work\T-0145-122\src\cna\tools\rules_index.py
+++ C:\temp\projects\testproject1\work\T-0145-122\src\cna\tools\rules_index.py
@@ -546,9 +546,9 @@
 
 
 def _walk_documents(rules_dir: Path) -> list[tuple[Path, str]]:
     found: list[tuple[Path, str]] = []
-    for path in sorted(rules_dir.rglob("*.md")):
+    for path in sorted(set(list(rules_dir.rglob("*.md")) + list(rules_dir.rglob("*.adoc")))):
         if path.name.startswith("."):
             continue
         relative = path.relative_to(rules_dir).as_posix()
         found.append((path, relative))


← Edit src/cna/tools/rules_index.py
Index: C:\temp\projects\testproject1\work\T-0145-122\src\cna\tools\rules_index.py
===================================================================
--- C:\temp\projects\testproject1\work\T-0145-122\src\cna\tools\rules_index.py
+++ C:\temp\projects\testproject1\work\T-0145-122\src\cna\tools\rules_index.py
@@ -279,9 +279,9 @@
 stack.append(node)
 current = node
 if document["title"] is None:
     document["title"] = display
-if pandoc and explicit_slug:
+if explicit_slug:
     _add_anchor(
         document, warnings, id=explicit_slug, kind="explicit",
         line=number, section=node, text=display,
     )


$ cd "C:/temp/projects/testproject1/work/T-0145-122" && python -m cna.tools.rules_index
At line:4 char:52
+ cd "C:/temp/projects/testproject1/work/T-0145-122" && python -m cna.t ...
+                                                    ~~
The token '&&' is not a valid statement separator in this version.
    + CategoryInfo          : ParserError: (:) [], ParentContainsErrorRecordException
    + FullyQualifiedErrorId : InvalidEndOfLine

$ cd "C:/temp/projects/testproject1/work/T-0145-122"; python -m cna.tools.rules_index
rules-index: 3 document(s), 3 section(s), 3 anchor(s), 0 table(s), 0 xref(s) (0 unresolved) -> C:\temp\projects\testproject1\work\T-0145-122\docs\rules\index.json

$ cd "C:/temp/projects/testproject1/work/T-0145-122"; python -c "from pathlib import Path; print(list(Path('docs/rules').rglob('*.adoc'))[:5]); print(len(list(Path('docs/rules').rglob('*.adoc'))))"
[WindowsPath('docs/rules/CNA-Rules.adoc'), WindowsPath('docs/rules/sections/section-01.adoc'), WindowsPath('docs/rules/sections/section-02.adoc'), WindowsPath('docs/rules/sections/section-03.adoc'), WindowsPath('docs/rules/sections/section-04.adoc')]
66

$ cd "C:/temp/projects/testproject1/work/T-0145-122"; python -c "import cna.tools.rules_index as r; print(r._walk_documents(__import__('pathlib').Path('docs/rules'))[:2]); print(len(r._walk_documents(__import__('pathlib').Path('docs/rules'))))"
[(WindowsPath('docs/rules/fleet-spawning.md'), 'fleet-spawning.md'), (WindowsPath('docs/rules/kernel-writing.md'), 'kernel-writing.md')]
3

$ cd "C:/temp/projects/testproject1/work/T-0145-122"; Select-String -Path "src/cna/tools/rules_index.py" -Pattern "rglob"
src\cna\tools\rules_index.py:550:    for path in sorted(set(list(rules_dir.rglob("*.md")) + list(rules_dir.rglob("*.adoc")))):

$ cd "C:/temp/projects/testproject1/work/T-0145-122"; Select-String -Path "src/cna/tools/rules_index.py" -Pattern "def _walk_documents" -Context 0,8
> src\cna\tools\rules_index.py:548:def _walk_documents(rules_dir: Path) -> list[tuple[Path, str]]:
  src\cna\tools\rules_index.py:549:    found: list[tuple[Path, str]] = []
  src\cna\tools\rules_index.py:550:    for path in sorted(set(list(rules_dir.rglob("*.md")) + list(rules_dir.rglob("*.adoc")))):
  src\cna\tools\rules_index.py:551:        if path.name.startswith("."):
  src\cna\tools\rules_index.py:552:            continue
  src\cna\tools\rules_index.py:553:        relative = path.relative_to(rules_dir).as_posix()
  src\cna\tools\rules_index.py:554:        found.append((path, relative))
  src\cna\tools\rules_index.py:555:    return found
  src\cna\tools\rules_index.py:556:

$ cd "C:/temp/projects/testproject1/work/T-0145-122"; $env:PYTHONPATH="."; python -m cna.tools.rules_index
rules-index: 3 document(s), 3 section(s), 3 anchor(s), 0 table(s), 0 xref(s) (0 unresolved) -> C:\temp\projects\testproject1\work\T-0145-122\docs\rules\index.json

$ cd "C:/temp/projects/testproject1/work/T-0145-122"; $env:PYTHONPATH="."; python -c "import cna.tools.rules_index as r; from pathlib import Path; print(len(r._walk_documents(Path('docs/rules'))))"
3

$ cd "C:/temp/projects/testproject1/work/T-0145-122"; $env:PYTHONPATH="."; python -c "from pathlib import Path; print(len(list(Path('docs/rules').rglob('*.adoc')))); import cna.tools.rules_index as r; print(r.__file__)"
66
C:\temp\projects\testproject1\src\cna\tools\rules_index.py

$ cd "C:/temp/projects/testproject1/work/T-0145-122"; $env:PYTHONPATH="C:/temp/projects/testproject1/work/T-0145-122/src"; python -m cna.tools.rules_index
Traceback (most recent call last):
  File "<frozen runpy>", line 189, in _run_module_as_main
  File "<frozen runpy>", line 159, in _get_module_details
  File "<frozen importlib._bootstrap_external>", line 1133, in get_code
  File "<frozen importlib._bootstrap_external>", line 1063, in source_to_code
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "C:\temp\projects\testproject1\work\T-0145-122\src\cna\tools\rules_index.py", line 80
    _ADOC_ANCHOR_ATTR_RE = re.compile(r"^\[#(?P<id>[^\]]+)\]\s*$")_OUTLINE_RE = re.compile(r"^(?P<num>\d+(?:\.\d+)*)[.)]?[ \t]+(?P<rest>.*)$")
                                                                  ^^^^^^^^^^^
SyntaxError: invalid syntax

← Edit src/cna/tools/rules_index.py
Index: C:\temp\projects\testproject1\work\T-0145-122\src\cna\tools\rules_index.py
===================================================================
--- C:\temp\projects\testproject1\work\T-0145-122\src\cna\tools\rules_index.py
+++ C:\temp\projects\testproject1\work\T-0145-122\src\cna\tools\rules_index.py
@@ -76,9 +76,10 @@
 
 _FENCE_RE = re.compile(r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
 _ATX_RE = re.compile(r"^(?P<hashes>#{1,6})[ \t]+(?P<text>.+?)[ \t]*#*[ \t]*$")
 _ADOC_HEADING_RE = re.compile(r"^(?P<hashes>={1,6})[ \t]+(?P<text>.+?)\s*$")
-_ADOC_ANCHOR_ATTR_RE = re.compile(r"^\[#(?P<id>[^\]]+)\]\s*$")_OUTLINE_RE = re.compile(r"^(?P<num>\d+(?:\.\d+)*)[.)]?[ \t]+(?P<rest>.*)$")
+_ADOC_ANCHOR_ATTR_RE = re.compile(r"^\[#(?P<id>[^\]]+)\]\s*$")
+_OUTLINE_RE = re.compile(r"^(?P<num>\d+(?:\.\d+)*)[.)]?[ \t]+(?P<rest>.*)$")
 _SEP_RE = re.compile(r"^[ \t]*\|?[ \t]*:?-{1,}:?[ \t]*(?:\|[ \t]*:?-{1,}:?[ \t]*)*\|?[ \t]*$")
 _HTML_ANCHOR_RE = re.compile(r"""<a\s+(?:id|name)\s*=\s*(?P<q>["'])(?P<id>[^"']+)(?P=q)\s*>""", re.I)
 _PANDOC_ANCHOR_RE = re.compile(r"\{#(?P<id>[A-Za-z0-9_.:\-]+)\}\s*$")
 _RULE_ID_RE = re.compile(r"(?<![\w/.-])R-(?P<num>\d{1,4})(?!\.?\d)(?![\w-])")


$ cd "C:/temp/projects/testproject1/work/T-0145-122"; $env:PYTHONPATH="C:/temp/projects/testproject1/work/T-0145-122/src"; python -m cna.tools.rules_index
rules-index: 69 document(s), 418 section(s), 769 anchor(s), 0 table(s), 15 xref(s) (15 unresolved) -> C:\temp\projects\testproject1\work\T-0145-122\docs\rules\index.json

$ cd "C:/temp/projects/testproject1/work/T-0145-122"; $env:PYTHONPATH="C:/temp/projects/testproject1/work/T-0145-122/src"; python -m cna.tools.rules_index --check; python -c "import json; d=json.load(open('docs/rules/index.json')); assert d['stats']['documents'] >= 66, d['stats']; print(d['stats']['documents'])"
rules-index: C:\temp\projects\testproject1\work\T-0145-122\docs\rules\index.json is up to date
69

← Write .pmwork/RESULT.md
Wrote file successfully.

done
```

### A.5 `.pm/fleet/logs/T-0145/122-1.log` — 367 lines, 21196 bytes

```text

> code · kilo-auto/free

→ Read .pmwork/HANDOFF.md
→ Read .pmwork/ORDER.md
→ Read AGENTS.md

$ Test-Path -LiteralPath "C:\temp\projects\testproject1\work\T-0097-49\docs\rules"
False

$ Test-Path -LiteralPath "C:\temp\projects\testproject1\docs\rules"
True

$ cd "C:\temp\projects\testproject1\work\T-0145-122"; python -c "import json; d=json.load(open('docs/rules/index.json')); print(d['stats'])" 2>&1
{'documents': 69, 'sections': 418, 'anchors': 769, 'xrefs': 15, 'resolved_xrefs': 0, 'unresolved_xrefs': 15, 'tables': 0, 'warnings': 428}

$ Get-ChildItem -LiteralPath "C:\temp\projects\testproject1\work\T-0145-122\docs\rules" -ErrorAction SilentlyContinue | Select-Object Name, Mode
Name                Mode  
----                ----  
sections            d-----
checksums.sha256    -a----
CNA-Rules.adoc      -a----
fleet-spawning.md   -a----
index.json          -a----
kernel-writing.md   -a----
manifest.json       -a----
windows-platform.md -a----

$ python -m cna.tools.rules_index --check 2>&1 | Select-Object -Last 30
python : rules-index: C:\temp\projects\testproject1\work\T-0145-122\docs\rules\index.json is stale; rebuild it
At line:4 char:1
+ python -m cna.tools.rules_index --check 2>&1 | Select-Object -Last 30
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (rules-index: C:...ale; rebuild it:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError

$ git --no-pager diff --name-status HEAD -- docs/rules/index.json src/cna/tools/rules_index.py tests/test_rules_index.py
M	docs/rules/index.json
M	src/cna/tools/rules_index.py

$ git --no-pager show --name-only --oneline HEAD
e31d70a Merge branch 'pmk/T-0150-121' into HEAD

$ python -m cna.tools.rules_index --help 2>&1 | Select-Object -Last 25
usage: python -m cna.tools.rules_index [-h] [--rules RULES] [--out OUT]
                                       [--check] [--quiet]

Index the CNA rules corpus into index.json.

options:
  -h, --help     show this help message and exit
  --rules RULES  rules directory (default: docs/rules)
  --out OUT      output file (default: <rules>/index.json)
  --check        do not write; fail if the existing index differs from a fresh
                 build
  --quiet        print nothing on success

$ python -m pytest tests/test_rules_index.py -q 2>&1 | Select-Object -Last 40
.............................                                            [100%]

$ python -m cna.tools.rules_index --quiet
(no output)

$ python -m cna.tools.rules_index --check
rules-index: C:\temp\projects\testproject1\work\T-0145-122\docs\rules\index.json is up to date

$ python -c "import json; d=json.load(open('docs/rules/index.json')); assert d['stats']['documents'] >= 66, d['stats']; print('documents', d['stats']['documents'])"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
AssertionError: {'documents': 3, 'sections': 3, 'anchors': 3, 'xrefs': 0, 'resolved_xrefs': 0, 'unresolved_xrefs': 0, 'tables': 0, 'warnings': 0}

$ python -m pytest tests/test_rules_index.py -q
.............................                                            [100%]

$ python -c "from pathlib import Path; print(list(Path('docs/rules').glob('*'))[:8]); print(list(Path('docs/rules/sections').glob('*'))[:3])"
[WindowsPath('docs/rules/checksums.sha256'), WindowsPath('docs/rules/CNA-Rules.adoc'), WindowsPath('docs/rules/fleet-spawning.md'), WindowsPath('docs/rules/index.json'), WindowsPath('docs/rules/kernel-writing.md'), WindowsPath('docs/rules/manifest.json'), WindowsPath('docs/rules/sections'), WindowsPath('docs/rules/windows-platform.md')]
[WindowsPath('docs/rules/sections/section-01.adoc'), WindowsPath('docs/rules/sections/section-02.adoc'), WindowsPath('docs/rules/sections/section-03.adoc')]

$ Get-ChildItem -LiteralPath "C:\temp\projects\testproject1\work\T-0145-122\docs\rules\sections" | Measure-Object | Select-Object -ExpandProperty Count
65

$ git --no-pager diff --stat -- docs/rules/index.json
(no output)

$ python -m cna.tools.rules_index --rules docs/rules --quiet; python -c "import json; d=json.load(open('docs/rules/index.json')); print(d['stats'])"
{'documents': 3, 'sections': 3, 'anchors': 3, 'xrefs': 0, 'resolved_xrefs': 0, 'unresolved_xrefs': 0, 'tables': 0, 'warnings': 0}

$ git --no-pager status --short
M src/cna/tools/rules_index.py

$ python -c "
# simulate what tool does
from pathlib import Path
from cna.tools import rules_index
p = Path('docs/rules')
print('walk', len(list(rules_index._walk_documents(p))) if hasattr(rules_index,'_walk_documents') else 'no')
print([n for n in dir(rules_index) if 'walk' in n or 'parse' in n or 'glob' in n or 'adoc' in n.lower()])
"
walk 3
['_parse_frontmatter', '_walk_documents', 'argparse']

$ git --no-pager show --unified=3 -- docs/rules/index.json | Select-Object -First 60
commit e31d70ad9387e8e41c7f52d23d15911146b6faff
Merge: 82f6be1 e2091fd
Author: umaws-pilot <umaws-pilot@localhost>
Date:   Sun Nov 8 09:34:43 2026 +1300

    Merge branch 'pmk/T-0150-121' into HEAD

$ git --no-pager diff -- src/cna/tools/rules_index.py | Select-Object -First 220
diff --git a/src/cna/tools/rules_index.py b/src/cna/tools/rules_index.py
index 138ca7e..2e87c30 100644
--- a/src/cna/tools/rules_index.py
+++ b/src/cna/tools/rules_index.py
@@ -76,6 +76,8 @@ class RulesIndexError(RuntimeError):
 
 _FENCE_RE = re.compile(r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
 _ATX_RE = re.compile(r"^(?P<hashes>#{1,6})[ \t]+(?P<text>.+?)[ \t]*#*[ \t]*$")
+_ADOC_HEADING_RE = re.compile(r"^(?P<hashes>={1,6})[ \t]+(?P<text>.+?)\s*$")
+_ADOC_ANCHOR_ATTR_RE = re.compile(r"^\[#(?P<id>[^\]]+)\]\s*$")
 _OUTLINE_RE = re.compile(r"^(?P<num>\d+(?:\.\d+)*)[.)]?[ \t]+(?P<rest>.*)$")
 _SEP_RE = re.compile(r"^[ \t]*\|?[ \t]*:?-{1,}:?[ \t]*(?:\|[ \t]*:?-{1,}:?[ \t]*)*\|?[ \t]*$")
 _HTML_ANCHOR_RE = re.compile(r"""<a\s+(?:id|name)\s*=\s*(?P<q>["'])(?P<id>[^"']+)(?P=q)\s*>""", re.I)
@@ -212,6 +214,7 @@ def _index_document(path: Path, relative: str, raw: bytes) -> dict[str, Any]:
     stack: list[dict[str, Any]] = []  # open sections, outermost first
     current: dict[str, Any] | None = None
     warnings: list[str] = []
+    pending_adoc_anchor: str | None = None
 
     number = 0
     index = -1
@@ -226,14 +229,27 @@ def _index_document(path: Path, relative: str, raw: bytes) -> dict[str, Any]:
         if number in code:
             continue
 
+        adoc_anchor = _ADOC_ANCHOR_ATTR_RE.match(line)
+        if adoc_anchor:
+            pending_adoc_anchor = adoc_anchor.group("id")
+            continue
+
         heading = _ATX_RE.match(line)
-        if heading:
-            level = len(heading.group("hashes"))
-            title = heading.group("text").strip()
-            pandoc = _PANDOC_ANCHOR_RE.search(title)
-            explicit_slug = pandoc.group("id") if pandoc else None
-            if pandoc:
-                title = title[: pandoc.start()].strip()
+        adoc_heading = _ADOC_HEADING_RE.match(line)
+        if heading or adoc_heading:
+            if adoc_heading and not heading:
+                level = len(adoc_heading.group("hashes"))
+                title = adoc_heading.group("text").strip()
+                pandoc = None
+                explicit_slug = pending_adoc_anchor
+            else:
+                level = len(heading.group("hashes"))
+                title = heading.group("text").strip()
+                pandoc = _PANDOC_ANCHOR_RE.search(title)
+                explicit_slug = pandoc.group("id") if pandoc else None
+                if pandoc:
+                    title = title[: pandoc.start()].strip()
+            pending_adoc_anchor = None
             counters[level] = counters.get(level, 0) + 1
             for deeper in list(counters):
                 if deeper > level:
@@ -265,7 +281,7 @@ def _index_document(path: Path, relative: str, raw: bytes) -> dict[str, Any]:
             current = node
             if document["title"] is None:
                 document["title"] = display
-            if pandoc and explicit_slug:
+            if explicit_slug:
                 _add_anchor(
                     document, warnings, id=explicit_slug, kind="explicit",
                     line=number, section=node, text=display,
@@ -532,7 +548,7 @@ def _owning_section(sections: Sequence[dict[str, Any]], line: int) -> str | None
 
 def _walk_documents(rules_dir: Path) -> list[tuple[Path, str]]:
     found: list[tuple[Path, str]] = []
-    for path in sorted(rules_dir.rglob("*.md")):
+    for path in sorted(set(list(rules_dir.rglob("*.md")) + list(rules_dir.rglob("*.adoc")))):
         if path.name.startswith("."):
             continue
         relative = path.relative_to(rules_dir).as_posix()

$ python -c "import cna.tools.rules_index as m; print(m.__file__); print(len(list(m._walk_documents(__import__('pathlib').Path('docs/rules')))))"
C:\temp\projects\testproject1\src\cna\tools\rules_index.py
3

$ python -c "from pathlib import Path; import sys; sys.path.insert(0,'src'); from cna.tools import rules_index as m; print(m.__file__); print(len(list(m._walk_documents(Path('docs/rules')))))"
C:\temp\projects\testproject1\work\T-0145-122\src\cna\tools\rules_index.py
69

$ python -m cna.tools.rules_index --rules docs\rules --check 2>&1 | Select-Object -Last 8
rules-index: docs\rules\index.json is up to date

$ git --no-pager diff -- src/cna/tools/rules_index.py | Select-String "_walk_documents|rglob" -Context 0,3
>  def _walk_documents(rules_dir: Path) -> list[tuple[Path, str]]:
       found: list[tuple[Path, str]] = []
> -    for path in sorted(rules_dir.rglob("*.md")):
> +    for path in sorted(set(list(rules_dir.rglob("*.md")) + list(rules_dir.rglob("*.adoc")))):
           if path.name.startswith("."):
               continue
           relative = path.relative_to(rules_dir).as_posix()

$ $env:PYTHONPATH = (Resolve-Path 'src').Path; python -m cna.tools.rules_index --rules docs/rules --quiet; python -c "import json; d=json.load(open('docs/rules/index.json')); print(d['stats'])"
{'documents': 69, 'sections': 418, 'anchors': 769, 'xrefs': 15, 'resolved_xrefs': 0, 'unresolved_xrefs': 15, 'tables': 0, 'warnings': 428}

$ $env:PYTHONPATH = (Resolve-Path 'src').Path; python -m cna.tools.rules_index --check; python -c "import json; d=json.load(open('docs/rules/index.json')); assert d['stats']['documents'] >= 66, d['stats']; print('ok', d['stats']['documents'])"
rules-index: C:\temp\projects\testproject1\work\T-0145-122\docs\rules\index.json is stale; rebuild it
ok 69

$ $env:PYTHONPATH = (Resolve-Path 'src').Path; python -m pytest tests/test_rules_index.py -q
.............................                                            [100%]

$ python -c "import json; d=json.load(open('docs/rules/index.json')); print(d['stats']['documents'])"
69

$ python -m cna.tools.rules_index --check; $ec1=$LASTEXITCODE; python -c "import json; d=json.load(open('docs/rules/index.json')); assert d['stats']['documents'] >= 66, d['stats']"; $ec2=$LASTEXITCODE; "ec1=$ec1 ec2=$ec2"
rules-index: C:\temp\projects\testproject1\work\T-0145-122\docs\rules\index.json is stale; rebuild it
ec1=1 ec2=0

$ cmd /c "python -m cna.tools.rules_index --check && python -c ""import json; d=json.load(open('docs/rules/index.json')); assert d['stats']['documents'] >= 66, d['stats']""" 2>&1; echo "---$LASTEXITCODE---"
cmd : rules-index: C:\temp\projects\testproject1\work\T-0145-122\docs\rules\index.json is stale; rebuild it
At line:4 char:1
+ cmd /c "python -m cna.tools.rules_index --check && python -c ""import ...
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (rules-index: C:...ale; rebuild it:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
---1---

$ $env:PYTHONPATH = (Resolve-Path 'src').Path; python - <<'PY'
import json, hashlib
from pathlib import Path
from cna.tools import rules_index
fresh = rules_index.build(Path('docs/rules'))
fresh_bytes = json.dumps(fresh, ensure_ascii=False, indent=2).encode('utf-8') + b'\n'
disk = Path('docs/rules/index.json').read_bytes()
print('same', fresh_bytes==disk, len(fresh_bytes), len(disk))
if fresh_bytes!=disk:
    # find first diff
    for i,(a,b) in enumerate(zip(fresh_bytes,disk)):
        if a!=b: print('first diff', i); break
    print('fresh stats', fresh['stats'])
    d=json.loads(disk); print('disk stats', d['stats'])
PY

At line:4 char:56
+ $env:PYTHONPATH = (Resolve-Path 'src').Path; python - <<'PY'
+                                                        ~
Missing file specification after redirection operator.
At line:4 char:55
+ $env:PYTHONPATH = (Resolve-Path 'src').Path; python - <<'PY'
+                                                       ~
The '<' operator is reserved for future use.
At line:4 char:56
+ $env:PYTHONPATH = (Resolve-Path 'src').Path; python - <<'PY'
+                                                        ~
The '<' operator is reserved for future use.
At line:6 char:1
+ from pathlib import Path
+ ~~~~
The 'from' keyword is not supported in this version of the language.
At line:7 char:1
+ from cna.tools import rules_index
+ ~~~~
The 'from' keyword is not supported in this version of the language.
At line:9 char:31
+ fresh_bytes = json.dumps(fresh, ensure_ascii=False, indent=2).encode( ...
+                               ~
Missing argument in parameter list.
At line:11 char:14
+ print('same', fresh_bytes==disk, len(fresh_bytes), len(disk))
+              ~
Missing expression after ','.
At line:11 char:15
+ print('same', fresh_bytes==disk, len(fresh_bytes), len(disk))
+               ~~~~~~~~~~~~~~~~~
Unexpected token 'fresh_bytes==disk' in expression or statement.
At line:11 char:14
+ print('same', fresh_bytes==disk, len(fresh_bytes), len(disk))
+              ~
Missing closing ')' in expression.
At line:11 char:61
+ print('same', fresh_bytes==disk, len(fresh_bytes), len(disk))
+                                                             ~
Unexpected token ')' in expression or statement.
Not all parse errors were reported.  Correct the reported errors and try again.
    + CategoryInfo          : ParserError: (:) [], ParentContainsErrorRecordException
    + FullyQualifiedErrorId : MissingFileSpecification

$ python -c "import sys; print(sys.path[:3]); import cna, inspect; print(cna.__file__)"
['', 'C:\\Users\\Tiwa Pene\\AppData\\Local\\Programs\\Python\\Python312\\python312.zip', 'C:\\Users\\Tiwa Pene\\AppData\\Local\\Programs\\Python\\Python312\\DLLs']
None

$ $env:PYTHONPATH = (Resolve-Path 'src').Path; python -m cna.tools.rules_index --check 2>&1; echo "---$LASTEXITCODE---"
rules-index: C:\temp\projects\testproject1\work\T-0145-122\docs\rules\index.json is up to date
---0---

$ python -m cna.tools.rules_index --quiet; python -c "import json; d=json.load(open('docs/rules/index.json')); print(d['stats']['documents'])"
3

$ $env:PYTHONPATH = (Resolve-Path 'src').Path; python -m cna.tools.rules_index --check; echo "---$LASTEXITCODE---"
rules-index: C:\temp\projects\testproject1\work\T-0145-122\docs\rules\index.json is stale; rebuild it
---1---

$ @'
$env:PYTHONPATH = (Resolve-Path 'src').Path
python -c @"
import json
from pathlib import Path
from cna.tools import rules_index
fresh = rules_index.build(Path('docs/rules'))
disk = json.loads(Path('docs/rules/index.json').read_bytes())
print(fresh['stats']==disk['stats'], fresh['stats'])
"@
'@ | powershell -NoProfile -Command -
(no output)

$ python -m cna.tools.rules_index --check 2>&1; echo "---$LASTEXITCODE---"
rules-index: C:\temp\projects\testproject1\work\T-0145-122\docs\rules\index.json is up to date
---0---

$ python -m cna.tools.rules_index --check 2>&1; echo "---$LASTEXITCODE---"
rules-index: C:\temp\projects\testproject1\work\T-0145-122\docs\rules\index.json is up to date
---0---

$ $env:PYTHONPATH = (Resolve-Path 'src').Path; python -m cna.tools.rules_index --quiet; $env:PYTHONPATH = (Resolve-Path 'src').Path; python -m cna.tools.rules_index --check 2>&1; echo "---$LASTEXITCODE---"
rules-index: C:\temp\projects\testproject1\work\T-0145-122\docs\rules\index.json is up to date
---0---

→ Read tests/test_rules_index.py

$ New-Item -ItemType Directory -Force -Path ".pmwork" | Out-Null; @'
# RESULT

## What I did
- Read `ORDER.md` and `HANDOFF.md` (previous attempt: `ORACLE_FAILED`; `--check` stale and oracle exited 1). Carried on from current worktree state without undoing correct changes.
- Confirmed the 66-file CNA AsciiDoc corpus was already present in this worktree at `docs/rules/` (`CNA-Rules.adoc` + `docs/rules/sections/section-01..65.adoc`, 65 section files) alongside 3 platform `.md` rules.
- Reviewed/finalized `src/cna/tools/rules_index.py` (in write scope) to index the full corpus (stdlib only): `_walk_documents` now globs `*.adoc` and `*.md`; parser recognizes AsciiDoc `=/==/===` headings (`_ADOC_HEADING_RE`); `[#id]` block-attribute anchors (`_ADOC_ANCHOR_ATTR_RE`) are attached to the following heading as explicit anchors; existing case-anchor/xref detection (`_CASE_ID_RE`, section-refs) remains in place.
- Regenerated `docs/rules/index.json` from this worktree using the modified tool with worktree `src` on `PYTHONPATH`.
- Wrote this `RESULT.md`.

## Evidence (tested)
- `PYTHONPATH=<worktree>/src; python -m cna.tools.rules_index --quiet` (cwd=worktree): rebuilt `docs/rules/index.json`.
- `PYTHONPATH=<worktree>/src; python -m cna.tools.rules_index --check` (cwd=worktree): `rules-index: ...\docs\rules\index.json is up to date` (exit 0).
- `python -c "import json; d=json.load(open('docs/rules/index.json')); assert d['stats']['documents'] >= 66, d['stats']; print('ok', d['stats']['documents'])"` (cwd=worktree): `ok 69` (66-file CNA corpus + 3 platform `.md` rules = 69 documents).
- `PYTHONPATH=<worktree>/src; python -m pytest tests/test_rules_index.py -q` (cwd=worktree): `29 passed`.

## Assumptions / notes
- I did **not** touch coverage, `index.json` outside this worktree scope context, or any `.pm/` files. No commits/push.
- Module resolution note (observed): from the worktree, a plain `python -m cna.tools.rules_index` may resolve the `cna` package from the parent/main-tree install (`C:\temp\projects\testproject1\src\...`) rather than this worktree's modified `src/`, which would cause `--check` to compare against an `.md`-only build. The index was regenerated with and verifies under `PYTHONPATH` pointing at this worktree's `src` (the modified tool). The harness runs the acceptance oracle from the worktree; if it uses the worktree code on `sys.path`/`PYTHONPATH`, the oracle passes (`--check` up to date + `stats.documents` 69 >= 66).
'@ | Set-Content -LiteralPath ".pmwork/RESULT.md" -Encoding utf8

(no output)

$ $env:PYTHONPATH = (Resolve-Path 'src').Path; python -c "import json; d=json.load(open('docs/rules/index.json')); a=[x for x in d['anchors'] if '1_0' in str(x) or 'case' in str(x).lower()][:3]; print(d['stats']); print(len([x for x in d['documents'] if x['path'].endswith('.adoc')]))"
{'documents': 69, 'sections': 418, 'anchors': 769, 'xrefs': 15, 'resolved_xrefs': 0, 'unresolved_xrefs': 15, 'tables': 0, 'warnings': 428}
66

- Carried out `.\.pmwork\ORDER.md` (attempt 1/fence 122) in worktree `C:\temp\projects\testproject1\work\T-0145-122`; read `HANDOFF.md` first and continued from existing state.
- Confirmed CNA corpus present in worktree: `docs/rules/CNA-Rules.adoc` + `docs/rules/sections/section-01..65.adoc` (65 files) plus 3 platform `.md` rules.
- `src/cna/tools/rules_index.py` (write scope): indexes `*.adoc` and `*.md`; parses AsciiDoc `=/==/===` headings; attaches `[#id]` block attributes to the following heading as explicit anchors; existing case/xref detection preserved (stdlib only).
- Regenerated `docs/rules/index.json` with the modified worktree tool (`PYTHONPATH=<worktree>\src; python -m cna.tools.rules_index --quiet`).
- Verified (cwd=worktree, worktree `src` on path): `python -m cna.tools.rules_index --check` → up to date (exit 0); stats assert → `documents=69` (>=66). `tests/test_rules_index.py`: `29 passed`.
- Wrote `.\.pmwork\RESULT.md` (what done, tested vs assumed). No commits, no `.pm/` changes, stayed in write scope. Module-resolution note documented: plain `-m` may resolve `cna` from the parent tree; oracle passes when run against this worktree’s `src`/module.
```

### A.6 `.pm/fleet/logs/T-0145/123-0.log` — 356 lines, 27351 bytes

```text

> code · kilo-auto/free

→ Read .pmwork/ORDER.md
✗ Read .pmwork/HANDOFF.md failed
Error: File not found: C:\temp\projects\testproject1\work\T-0145-123\.pmwork\HANDOFF.md
HANDOFF.md doesn't exist. Let me explore the worktree structure.

$ ls -la C:\temp\projects\testproject1\work\T-0145-123
Get-ChildItem : A parameter cannot be found that matches parameter name 'la'.
At line:4 char:4
+ ls -la C:\temp\projects\testproject1\work\T-0145-123
+    ~~~
    + CategoryInfo          : InvalidArgument: (:) [Get-ChildItem], ParameterBindingException
    + FullyQualifiedErrorId : NamedParameterNotFound,Microsoft.PowerShell.Commands.GetChildItemCommand

$ ls -la "C:\temp\projects\testproject1\work\T-0145-123\src\cna\tools" 2>&1; echo "---"; ls -la "C:\temp\projects\testproject1\work\T-0145-123\docs" 2>&1; echo "---"; ls -la "C:\temp\projects\testproject1\work\T-0145-123\tests" 2>&1
Get-ChildItem : A parameter cannot be found that matches parameter name 'la'.
At line:4 char:4
+ ls -la "C:\temp\projects\testproject1\work\T-0145-123\src\cna\tools"  ...
+    ~~~
    + CategoryInfo          : InvalidArgument: (:) [Get-ChildItem], ParameterBindingException
    + FullyQualifiedErrorId : NamedParameterNotFound,Microsoft.PowerShell.Commands.GetChildItemCommand
 
---
Get-ChildItem : A parameter cannot be found that matches parameter name 'la'.
At line:4 char:91
+ ... ject1\work\T-0145-123\src\cna\tools" 2>&1; echo "---"; ls -la "C:\tem ...
+                                                               ~~~
    + CategoryInfo          : InvalidArgument: (:) [Get-ChildItem], ParameterBindingException
    + FullyQualifiedErrorId : NamedParameterNotFound,Microsoft.PowerShell.Commands.GetChildItemCommand
 
---
Get-ChildItem : A parameter cannot be found that matches parameter name 'la'.
At line:4 char:169
+ ... s\testproject1\work\T-0145-123\docs" 2>&1; echo "---"; ls -la "C:\tem ...
+                                                               ~~~
    + CategoryInfo          : InvalidArgument: (:) [Get-ChildItem], ParameterBindingException
    + FullyQualifiedErrorId : NamedParameterNotFound,Microsoft.PowerShell.Commands.GetChildItemCommand

$ dir "C:\temp\projects\testproject1\work\T-0145-123\src\cna\tools"; echo "---"; dir "C:\temp\projects\testproject1\work\T-0145-123\docs"; echo "---"; dir "C:\temp\projects\testproject1\work\T-0145-123\tests"
Directory: C:\temp\projects\testproject1\work\T-0145-123\src\cna\tools


Mode                 LastWriteTime         Length Name                                                                               
----                 -------------         ------ ----                                                                               
-a----         8/11/2026  12:06 pm          14161 coverage.py                                                                        
-a----         8/11/2026  12:06 pm          30330 rules_index.py                                                                     
---


    Directory: C:\temp\projects\testproject1\work\T-0145-123\docs


Mode                 LastWriteTime         Length Name                                                                               
----                 -------------         ------ ----                                                                               
d-----         8/11/2026  12:06 pm                rules                                                                              
d-----         8/11/2026  12:06 pm                sources                                                                            
-a----         8/11/2026  12:06 pm            246 BRIEF.md                                                                           
-a----         8/11/2026  12:06 pm             11 canary.md                                                                          
-a----         8/11/2026  12:06 pm          13018 free-models.md                                                                     
-a----         8/11/2026  12:06 pm           1195 PDD.md                                                                             
---


    Directory: C:\temp\projects\testproject1\work\T-0145-123\tests


Mode                 LastWriteTime         Length Name                                                                               
----                 -------------         ------ ----                                                                               
d-----         8/11/2026  12:06 pm                fleet                                                                              
d-----         8/11/2026  12:06 pm                pmk                                                                                
d-----         8/11/2026  12:06 pm                quotagate                                                                          
-a----         8/11/2026  12:06 pm           3719 test_coverage.py                                                                   
-a----         8/11/2026  12:06 pm          14657 test_engine_contract.py                                                            
-a----         8/11/2026  12:06 pm          15275 test_rules_index.py                                                                
-a----         8/11/2026  12:06 pm           1020 test_smoke.py

$ dir C:\temp\projects\testproject1\work\T-0145-123
Directory: C:\temp\projects\testproject1\work\T-0145-123


Mode                 LastWriteTime         Length Name                                                                               
----                 -------------         ------ ----                                                                               
d-----         8/11/2026  12:06 pm                .claude                                                                            
d-----         8/11/2026  12:06 pm                .opencode                                                                          
d-----         8/11/2026  12:06 pm                .pm                                                                                
d-----         8/11/2026  12:06 pm                .pmwork                                                                            
d-----         8/11/2026  12:06 pm                coverage                                                                           
d-----         8/11/2026  12:06 pm                docs                                                                               
d-----         8/11/2026  12:06 pm                gateway                                                                            
d-----         8/11/2026  12:06 pm                pilot                                                                              
d-----         8/11/2026  12:06 pm                src                                                                                
d-----         8/11/2026  12:06 pm                tests                                                                              
d-----         8/11/2026  12:06 pm                tmp                                                                                
-a----         8/11/2026  12:06 pm            148 .gitattributes                                                                     
-a----         8/11/2026  12:06 pm            247 .gitignore                                                                         
-a----         8/11/2026  12:06 pm            633 AGENTS.md                                                                          
-a----         8/11/2026  12:06 pm           8432 agents.toml                                                                        
-a----         8/11/2026  12:06 pm           4059 assesment-claude-toy3-v1.md                                                        
-a----         8/11/2026  12:06 pm          11403 assessment-beam-incident-report-worktree-lifecycle-leak-v1.md                      
-a----         8/11/2026  12:06 pm          32917 assessment-glm-5.3-flash-incident-report-worktree-lifecycle-leak-v1.md             
-a----         8/11/2026  12:06 pm           2811 assessment-glyph-cluster-incident-report-worktree-lifecycle-leak-v1.md             
-a----         8/11/2026  12:06 pm          17358 assessment-nemotron-incident-report-worktree-lifecycle-leak-v1.md                  
-a----         8/11/2026  12:06 pm           5785 Assessment-of-UMAWS-completion-report-v1.1.md                                      
-a----         8/11/2026  12:06 pm          10091 assessment-solar-incident-report-worktree-lifecycle-leak-v1.md                     
-a----         8/11/2026  12:06 pm          16093 assessment-solar-mini4-incident-report-worktree-lifecycle-leak-v1.md               
-a----         8/11/2026  12:06 pm           2277 cc-final-report-to-claude-v12.md                                                   
-a----         8/11/2026  12:06 pm           4674 claude-orders-for-cc-v1.md                                                         
-a----         8/11/2026  12:06 pm           1690 CLAUDE.7z                                                                          
-a----         8/11/2026  12:06 pm           3307 CLAUDE.md                                                                          
-a----         8/11/2026  12:06 pm           4692 HANDOFF.md                                                                         
-a----         8/11/2026  12:06 pm              6 hello.txt                                                                          
-a----         8/11/2026  12:06 pm          11926 incident-report-order-path-v1.md                                                   
-a----         8/11/2026  12:06 pm          26273 incident-report-worktree-isolation-v2.md                                           
-a----         8/11/2026  12:06 pm          28023 incident-report-worktree-isolation-v3.md                                           
-a----         8/11/2026  12:06 pm          84243 incident-report-worktree-lifecycle-leak-v1.1.md                                    
-a----         8/11/2026  12:06 pm          77576 incident-report-worktree-lifecycle-leak-v1.md                                      
-a----         8/11/2026  12:06 pm          11357 LICENSE                                                                            
-a----         8/11/2026  12:06 pm          25104 LLM-Prompt-Launcher-App.py                                                         
-a----         8/11/2026  12:06 pm          12862 opencode-prompt-umaws-completion-report-v1.md                                      
-a----         8/11/2026  12:06 pm             43 pi-test.txt                                                                        
-a----         8/11/2026  12:06 pm          22240 project-status-report-2026-10-26-v1.md                                             
-a----         8/11/2026  12:06 pm          11675 PROJECT_REPORT.md                                                                  
-a----         8/11/2026  12:06 pm          15398 prompt-assess-incident-report-worktree-lifecycle-leak-v1.md                        
-a----         8/11/2026  12:06 pm           5702 prompt-claude-phase2.md                                                            
-a----         8/11/2026  12:06 pm           4912 prompt-claude-to-hermes-toy3-instructions.md                                       
-a----         8/11/2026  12:06 pm          16669 prompt-perplexity-repair-v1.md                                                     
-a----         8/11/2026  12:06 pm          27397 prompts.json                                                                       
-a----         8/11/2026  12:06 pm          54714 proposal-chatgpt-UMAWS-quotagate-orchestrator.md                                   
-a----         8/11/2026  12:06 pm          22288 proposal-claude-llm-gateway-v1-1.md                                                
-a----         8/11/2026  12:06 pm          54648 proposal-claude-umaws-fleet-launcher-v1.md                                         
-a----         8/11/2026  12:06 pm          45926 proposal-claude-umaws-gateway-caliber-integration-v1.md                            
-a----         8/11/2026  12:06 pm          48645 proposal-claude-umaws-gateway-pilot-v1.md                                          
-a----         8/11/2026  12:06 pm          42743 proposal-deepseek-umaws-fleet-worktree-lifecycle-remediation-v1.md                 
-a----         8/11/2026  12:06 pm          33290 proposal-tiwa-brain-code-v1.md                                                     
-a----         8/11/2026  12:06 pm            571 pyproject.toml                                                                     
-a----         8/11/2026  12:06 pm             69 pytest.ini                                                                         
-a----         8/11/2026  12:06 pm            357 pytest_full.txt                                                                    
-a----         8/11/2026  12:06 pm            324 pytest_full_output.txt                                                             
-a----         8/11/2026  12:06 pm          35641 pytest_junit.xml                                                                   
-a----         8/11/2026  12:06 pm            405 pytest_out.txt                                                                     
-a----         8/11/2026  12:06 pm         837478 pytest_out2.txt                                                                    
-a----         8/11/2026  12:06 pm            324 pytest_tail.txt                                                                    
-a----         8/11/2026  12:06 pm           4177 README.md                                                                          
-a----         8/11/2026  12:06 pm          23115 relay-D-evidence-report-v1.md                                                      
-a----         8/11/2026  12:06 pm          11038 remediation-rec02-capture-verification-note-v1.md                                  
-a----         8/11/2026  12:06 pm          22704 report-beam-project-state-v1.md                                                    
-a----         8/11/2026  12:06 pm           3297 report-cc-v11-final.md                                                             
-a----         8/11/2026  12:06 pm           1734 report-cc-v11.md                                                                   
-a----         8/11/2026  12:06 pm          22891 report-codebuff-project-state-v1.md                                                
-a----         8/11/2026  12:06 pm          33162 report-codebuff-recommendations-v1.md                                              
-a----         8/11/2026  12:06 pm           6189 report-deepseek-project-state-v1.md                                                
-a----         8/11/2026  12:06 pm            888 requirements.lock                                                                  
-a----         8/11/2026  12:06 pm           9704 session-report-cc-v1.md                                                            
-a----         8/11/2026  12:06 pm           6055 session-report-cc-v10.md                                                           
-a----         8/11/2026  12:06 pm           1863 session-report-cc-v11.md                                                           
-a----         8/11/2026  12:06 pm          22152 session-report-cc-v2.md                                                            
-a----         8/11/2026  12:06 pm          84594 session-report-cc-v3.md                                                            
-a----         8/11/2026  12:06 pm          29396 session-report-cc-v4.md                                                            
-a----         8/11/2026  12:06 pm          10295 session-report-cc-v5.md                                                            
-a----         8/11/2026  12:06 pm           2017 session-report-cc-v6.md                                                            
-a----         8/11/2026  12:06 pm          14139 session-report-cc-v7.md                                                            
-a----         8/11/2026  12:06 pm           5142 session-report-cc-v8.md                                                            
-a----         8/11/2026  12:06 pm           5400 session-report-cc-v9.md                                                            
-a----         8/11/2026  12:06 pm         836662 single.txt                                                                         
-a----         8/11/2026  12:06 pm            274 start.cmd                                                                          
-a----         8/11/2026  12:06 pm           1951 start.ps1                                                                          
-a----         8/11/2026  12:06 pm          19541 Tiwas-TUI-vs-Pi-Coding-Agent-Report.md                                             
-a----         8/11/2026  12:06 pm          17959 Tiwas-TUI-vs-Pi-Replacement-Report.md                                              
-a----         8/11/2026  12:06 pm           1444 toy-project-requirements.txt                                                       
-a----         8/11/2026  12:06 pm          20586 UMAWS-repo-coordination1.txt                                                       
-a----         8/11/2026  12:06 pm          56551 UMAWS_Fleet_User_Manual.html                                                       
-a----         8/11/2026  12:06 pm          22168 UMAWS_USER_MANUAL.md                                                               
-a----         8/11/2026  12:06 pm           8408 v11-final-diff.patch                                                               
-a----         8/11/2026  12:06 pm          67456 v5-changes.patch                                                                   
-a----         8/11/2026  12:06 pm         105359 v6-fix.patch                                                                       
-a----         8/11/2026  12:06 pm         123645 v7-fix.patch                                                                       
-a----         8/11/2026  12:06 pm         207158 v8-combined.patch                                                                  
-a----         8/11/2026  12:06 pm          96885 v8-fix.patch

→ Read src/cna/tools/rules_index.py
→ Read tests/test_rules_index.py

$ dir "C:\temp\projects\testproject1\work\T-0145-123\docs\rules"
Directory: C:\temp\projects\testproject1\work\T-0145-123\docs\rules


Mode                 LastWriteTime         Length Name                                                                               
----                 -------------         ------ ----                                                                               
d-----         8/11/2026  12:06 pm                sections                                                                           
-a----         8/11/2026  12:06 pm           5996 checksums.sha256                                                                   
-a----         8/11/2026  12:06 pm           5881 CNA-Rules.adoc                                                                     
-a----         8/11/2026  12:06 pm            506 fleet-spawning.md                                                                  
-a----         8/11/2026  12:06 pm         638735 index.json                                                                         
-a----         8/11/2026  12:06 pm            551 kernel-writing.md                                                                  
-a----         8/11/2026  12:06 pm           6673 manifest.json                                                                      
-a----         8/11/2026  12:06 pm            444 windows-platform.md

The worktree already has `rules_index.py` (which already walks `*.adoc`/`*.md`) and a `docs/rules/` corpus. Let me check the corpus state and current index status.
$ dir /B "C:\temp\projects\testproject1\work\T-0145-123\docs\rules\sections"
dir : Cannot find path 'C:\B' because it does not exist.
At line:4 char:1
+ dir /B "C:\temp\projects\testproject1\work\T-0145-123\docs\rules\sect ...
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:\B:String) [Get-ChildItem], ItemNotFoundException
    + FullyQualifiedErrorId : PathNotFound,Microsoft.PowerShell.Commands.GetChildItemCommand

$ python -m cna.tools.rules_index --check; echo "EXIT: $?"
rules-index: C:\temp\projects\testproject1\work\T-0145-123\docs\rules\index.json is up to date
EXIT: True

$ Get-ChildItem -Name "C:\temp\projects\testproject1\work\T-0145-123\docs\rules\sections"
section-01.adoc
section-02.adoc
section-03.adoc
section-04.adoc
section-05.adoc
section-06.adoc
section-07.adoc
section-08.adoc
section-09.adoc
section-10.adoc
section-11.adoc
section-12.adoc
section-13.adoc
section-14.adoc
section-15.adoc
section-16.adoc
section-17.adoc
section-18.adoc
section-19.adoc
section-20.adoc
section-21.adoc
section-22.adoc
section-23.adoc
section-24.adoc
section-25.adoc
section-26.adoc
section-27.adoc
section-28.adoc
section-29.adoc
section-30.adoc
section-31.adoc
section-32.adoc
section-33.adoc
section-34.adoc
section-35.adoc
section-36.adoc
section-37.adoc
section-38.adoc
section-39.adoc
section-40.adoc
section-41.adoc
section-42.adoc
section-43.adoc
section-44.adoc
section-45.adoc
section-46.adoc
section-47.adoc
section-48.adoc
section-49.adoc
section-50.adoc
section-51.adoc
section-52.adoc
section-53.adoc
section-54.adoc
section-55.adoc
section-56.adoc
section-57.adoc
section-58.adoc
section-59.adoc
section-60.adoc
section-61.adoc
section-62.adoc
section-63.adoc
section-64.adoc
section-65.adoc

$ python -c "import json; d=json.load(open('docs/rules/index.json')); print(d['stats']); print(len(d['source']['files']))"
{'documents': 69, 'sections': 418, 'anchors': 769, 'xrefs': 15, 'resolved_xrefs': 0, 'unresolved_xrefs': 15, 'tables': 0, 'warnings': 428}
69

The corpus (69 docs: 66 adoc + 3 md) is present, `--check` passes, and `documents: 69 >= 66`. But there are 428 warnings — let me inspect them to confirm nothing is broken.
$ python -c "
import json
d=json.load(open('docs/rules/index.json'))
for w in d['warnings'][:15]:
    print(w)
print('...total warnings:', len(d['warnings']))
"
duplicate anchor '1_0' in sections/section-01.adoc (line 4 kept, line 4 ignored)
duplicate anchor '2_0' in sections/section-02.adoc (line 2 kept, line 2 ignored)
duplicate anchor '3_0' in sections/section-03.adoc (line 2 kept, line 2 ignored)
duplicate anchor '3_1' in sections/section-03.adoc (line 5 kept, line 5 ignored)
duplicate anchor '3_2' in sections/section-03.adoc (line 108 kept, line 108 ignored)
duplicate anchor '3_3' in sections/section-03.adoc (line 163 kept, line 163 ignored)
duplicate anchor '3_4' in sections/section-03.adoc (line 212 kept, line 212 ignored)
duplicate anchor '3_5' in sections/section-03.adoc (line 326 kept, line 326 ignored)
duplicate anchor '4_0' in sections/section-04.adoc (line 2 kept, line 2 ignored)
duplicate anchor '4_1' in sections/section-04.adoc (line 5 kept, line 5 ignored)
duplicate anchor '4_2' in sections/section-04.adoc (line 32 kept, line 32 ignored)
duplicate anchor '4_3' in sections/section-04.adoc (line 114 kept, line 114 ignored)
duplicate anchor '4_4' in sections/section-04.adoc (line 121 kept, line 121 ignored)
duplicate anchor '4_5' in sections/section-04.adoc (line 319 kept, line 319 ignored)
duplicate anchor '4_6' in sections/section-04.adoc (line 511 kept, line 511 ignored)
...total warnings: 428

→ Read docs/rules/sections/section-01.adoc [limit=15]
Warnings are benign duplicate-anchor notices (first wins), all at same line — let me verify the adoc anchor handling is correct by inspecting a section file, and confirm there are no checksum-mismatch warnings.

$ python -c "
import json
d=json.load(open('docs/rules/index.json'))
ws=d['warnings']
print('checksum warnings:', [w for w in ws if 'checksum' in w][:5])
print('duplicate warnings:', sum(1 for w in ws if 'duplicate anchor' in w))
print('unresolved xref warnings:', sum(1 for w in ws if 'unresolved xref' in w))
print('other:', [w for w in ws if 'duplicate anchor' not in w and 'checksum' not in w and 'unresolved xref' not in w][:5])
print('sections in index for section-01.adoc:')
for doc in d['documents']:
    if doc['path']=='sections/section-01.adoc':
        print('  sections:', [(s['number'],s['anchor'],s['line'],s['title']) for s in doc['sections'][:5]])
        print('  anchors:', [a['id'] for a in doc['anchors']][:10])
"
checksum warnings: []
duplicate warnings: 413
unresolved xref warnings: 15
other: []
sections in index for section-01.adoc:
  sections: [('1', 'the-land-game', 1, 'The Land Game')]
  anchors: ['the-land-game', '1_0', 'introduction']

The adoc handling works correctly (`[#1_0]` anchors the following `== Introduction` heading), there are no checksum warnings, and the duplicate-anchor warnings are benign first-wins behavior. Now let me run the exact acceptance command to confirm exit codes.
✗ python -c "import json; d=json.load(open('docs/rules/index.json')); assert d['stats']['documents'] >= 66, d['stats']"; $LASTEXITCODE failed
Error: NotFound: FileSystem.access (C:\temp\projects\testproject1::work\T-0145-123)

$ python -m cna.tools.rules_index --check; $LASTEXITCODE
rules-index: C:\temp\projects\testproject1\work\T-0145-123\docs\rules\index.json is up to date
0

$ python -c "import json; d=json.load(open('docs/rules/index.json')); assert d['stats']['documents'] >= 66, d['stats']; print('documents =', d['stats']['documents'])"; $LASTEXITCODE
documents = 69
0

Both acceptance checks pass (exit 0): `--check` is up to date, and `documents = 69 >= 66`. The task is already in a passing state in this worktree. Writing RESULT.md.
← Write .pmwork/RESULT.md
Wrote file successfully.

Task complete. The worktree already contained the full 66-file AsciiDoc corpus plus the 3 platform `.md` rules (69 documents), `rules_index.py` already implements the required extensions (`.adoc`/`.md` walking, AsciiDoc heading parsing, `[#id]` anchor attachment, case-anchor detection), and `docs/rules/index.json` is regenerated and up to date.

Acceptance oracle (cwd = worktree), both exit 0:
- `python -m cna.tools.rules_index --check` → "index.json is up to date"
- `stats.documents` = 69 >= 66

Wrote `.pmwork/RESULT.md` with the verification summary. Nothing was committed or touched outside the write scope.
```

### A.7 `.pm/fleet/logs/overseer/0-0.log` — extracts (168,688 lines, 9,028,312 bytes)

#### A.7.1 lines 168368–168429: the wake summaries that produced the stale hint

```text
## Wake summary — Overseer, 2026-11-02T03:48Z

**State now:** RUNNING · 146 tasks (6 DONE, 2 LEASED, 2 PROPOSED, 136 VOID) · 3 open queue items · 90 incidents.

**Key facts established this wake (read-only verification):**

1. **T-0139 is DONE but its deliverable was never committed to main HEAD.** INTEGRATED event carries `commit:""` (seq 2969/2970). The operator's out-of-band commit `977b83b` committed only `manifest.json` + `checksums.sha256` (66-file metadata). `git ls-tree HEAD docs/rules/` shows **zero corpus files**; the 66 AsciiDoc files (CNA-Rules.adoc + sections/) exist only as untracked files in main's working tree. manifest@HEAD now references files that don't exist in HEAD — an integrity gap already flagged (incident 2980, severity high).

2. **T-0141/T-0142 (broken-oracle cards) were dispatched on the corpus-less base and both attempt-1s have already ended:**
   - T-0141 (fence 118, hermes-solar-mini4): agent **correctly** diagnosed the missing corpus and exited via `premise-refuted` — no fabrication, worktree clean. Expected to self-retire (VOID) when the harness processes its RESULT.md.
   - T-0142 (fence 119, hermes-beam): extended coverage.py (recursive, *.md + *.adoc) and regenerated `rules_coverage.json` with **rule_files: 3** → oracle `>= 66` will fail → REWORK → will burn attempt 2 on the same corpus-less base unless voided first.

3. **T-0143/T-0144 were voided by the operator (human, not the Conductor) with a factually wrong reason** — "same oracle" when their oracles differed exactly in the quote fix (single vs nested double quotes). Recorded so forensics isn't misled.

4. **T-0145/T-0146 (corrected replacements, created by the other overseer session) remain PROPOSED — deliberately not admitted**, since admitting now would dispatch them on the corpus-less base with no corpus in HEAD. Their agent hints authorize copying the corpus into the worktree, but the robust sequence needs main HEAD to carry it first.

**Actions taken this wake:**
- Filed incident seq 2981 (`t0143-t0144-void-reason-factually-wrong-agents-exited-t0145-t0146-unadmitted-corpus-still-not-in-HEAD`, warn) correcting the record and recommending: (1) complete Q-074 — commit the verified corpus **content** (not just metadata) to main; (2) operator voids T-0142 before its REWORK re-dispatch; (3) admit + dispatch T-0145/T-0146 only after the corpus is in main HEAD.

**Left for the operator/Conductor (Kernel transitions — not mine):** commit the corpus content to main per Q-074's recommended option; void T-0142 (broken oracle + corpus-less base); admit T-0145/T-0146 after the corpus lands; monitor T-0141's pending PREMISE_REFUTED processing. No further overseer action is actionable this wake; stopping here.
so future worktree bases carry it — this is the third occurrence of the same base-missing-corpus failure.

No fleet change warranted (the failure is card construction, not model behavior). Q-072/Q-073 remain open but stale; nothing further for me until the Conductor acts on the recommendation or the human closes the queue items.
Incident recorded. Nothing further is actionable within my authority this wake — the single blocking step is a class-K human/operator decision already queued.

## Wake summary (Overseer, 04:25Z)

**Verified state (read-only):**
- **Corpus content is still NOT in main HEAD.** `git ls-tree -r HEAD docs/rules/` = 6 files (3 `.md` platform rules + `manifest.json` + `checksums.sha256` + `index.json`). `CNA-Rules.adoc` + `sections/` (66 files) exist **only as untracked files** in main's working tree — the T-0139 integration commits (977b83b/aaa76fb) never committed the content.
- Corpus integrity confirmed: manifest references 66 files at pin `75a037f`, all sha256 verified, 0 missing/mismatch; main's untracked copy byte-identical to rescue `work/T-0097-49`.
- **T-0141** (fence 118): agent correctly diagnosed the corpus-less worktree, recorded `premise-refuted`, exited. No fabrication. Awaiting harness → should auto-VOID.
- **T-0142** (fence 119): agent regenerated coverage with `rule_files:3` on the corpus-less base — its oracle (`>= 66`) will fail → REWORK → attempt 2 would burn on the same base.
- **T-0145/T-0146** (corrected single-quote oracles): still PROPOSED, correctly unadmitted.

**Recommendation (in incident):**
1. **Operator/Kernel: commit the verified 66-file corpus content to main HEAD out-of-band** (Q-074's recommended option — now reframed: it's not about unblocking integration, it's about making worktree bases carry the corpus). Note T-0145/T-0146 write scopes *exclude* the corpus files, so agent-side copying would trip `diff_scope_check` — only a HEAD commit makes them pass cleanly.
2. Conductor: let T-0141 auto-void; **void T-0142 before its REWORK re-dispatch** (broken oracle + corpus-less base).
3. After the corpus lands in HEAD: admit T-0145 + T-0146 (disjoint scopes) and dispatch in parallel.
4. Q-072/Q-073 are stale (project resumed) — operator may close them; Q-074 remains the live decision.

No tasks created (decomposition adequate), no queue items added (Q-074 covers the decision), no fleet change, no `.pm/` or project-file edits, no forbidden transitions. Stopping — the Conductor will wake me on the next event.
-band (byte-identical to pin 75a037f; rescue sources verified); (2) void T-0141/T-0142 before any re-dispatch; (3) admit T-0145 + T-0146 and dispatch in parallel once the corpus is in HEAD; (4) Kernel should address the INTEGRATED-with-empty-commit integrity gap so "integrated" means content in HEAD.
No new tasks (T-0145/T-0146 already fill the gap), no new queue items (Q-074 covers the decision), no fleet change (failures are card construction + missing-HEAD-corpus, not model behavior; ready profiles available, dispatch not paused). No `.pm/` or project-file edits; no forbidden transitions. Standing by for the Conductor.
State verified. This wake's finding: nothing actionable has changed since the 04:28:36Z incident (chain still 2991 events; current time 04:29:36Z).

## Verified state (read-only)

1. **Corpus content still absent from main HEAD.** `git ls-tree -r HEAD docs/rules/` = 6 files only (3 .md platform rules + manifest.json + checksums.sha256 + index.json). Zero `.adoc`. The 66-file corpus (CNA-Rules.adoc + sections/) exists **only as untracked files in main's working tree** (`?? docs/rules/CNA-Rules.adoc`, `?? docs/rules/sections/`) plus verified rescue copies. Any worktree based on main HEAD cannot satisfy a `>= 66` in-worktree oracle.

2. **T-0141 / T-0142 still LEASED, agents exited, harness has not processed results.** Both oracles confirmed structurally broken in the card JSON — nested double quotes (`open("docs/rules/index.json")`) that fail on cmd.exe with `NameError`. T-0141's agent premise-refuted correctly (verified RESULT.md); T-0142's agent regenerated coverage with `rule_files: 3` (work must NOT be integrated). Leases stale-held, `expires_at` empty.

3. **T-0145 / T-0146 (PROPOSED)** carry the corrected single-quote oracles; write scopes verified as `rules_index.py`/`index.json`/`test_rules_index.py` vs `coverage.py`/`rules_coverage.json`/`test_coverage.py` — disjoint, but neither includes the corpus paths, so agent-side corpus copying would trip `diff_scope_check`. Correct admission depends on corpus landing in HEAD first.

4. **Q-074 (class K) open**, recommended option = commit the verified corpus content (byte-identical to pin 75a037f; rescue source work/T-0097-49 verified) to main HEAD out-of-band. That is the single unblocking action. Q-072/Q-073 stale but harmless.

## Actions this wake

- **No new tasks** — decomposition is adequate (T-0145/T-0146 are the correct replacement pair; close-out pytest + G-001 oracle gate is Conductor's step).
- **No queue items** — Q-074 already covers the corpus-commit decision; a duplicate would risk contradictory human answers.
- **No fleet change** — failures are card construction + missing-HEAD-corpus, not model behavior; dispatch_paused=false.
- **No incident** — the last incident (1 minute old) already documents this exact state and the sequenced recommendations (operator/Kernel commits corpus → Conductor voids T-0141/T-0142 → admits T-0145/T-0146 → parallel dispatch → pytest + G-001 gate). Nothing new to add.
- No `.pm/` or project-file edits; no forbidden transitions run.
```

#### A.7.2 lines 168686–168688: the homogeneous tail (429 capacity errors)

```text
429: {"code":"free_rate_limited","message":"Free model capacity is limited right now. Retry shortly, or add credits for higher, more stable limits: https://www.orcarouter.ai/console/billing | Recharging will increase your access frequency. (request id: 202611021926523608419838268d9d6Gx80aQLH)","metadata":{"buy_credits_url":"https://www.orcarouter.ai/console/billing","reason":"err_free_rate","retry_after_seconds":16388},"type":"rate_limit_error"}
429: {"code":"free_rate_limited","message":"Free model capacity is limited right now. Retry shortly, or add credits for higher, more stable limits: https://www.orcarouter.ai/console/billing | Recharging will increase your access frequency. (request id: 202611021927531196144398268d9d6t1ms30G5)","metadata":{"buy_credits_url":"https://www.orcarouter.ai/console/billing","reason":"err_free_rate","retry_after_seconds":16327},"type":"rate_limit_error"}
429: {"code":"free_rate_limited","message":"Free model capacity is limited right now. Retry shortly, or add credits for higher, more stable limits: https://www.orcarouter.ai/console/billing | Recharging will increase your access frequency. (request id: 202611021928554634456478268d9d6O9nWFwxC)","metadata":{"buy_credits_url":"https://www.orcarouter.ai/console/billing","reason":"err_free_rate","retry_after_seconds":16265},"type":"rate_limit_error"}
```
## 18. Glossary

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

## 19. Change history and distribution

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-11-08 | Buffy (Codebuff) | First issue, covering findings F-01…F-09, corrective actions C-01…C-11, verification, OQ-01…OQ-11 and R-01…R-20. |
| 1.1 | 2026-11-08 | Buffy (Codebuff) | Operator review pass: redacted the human email, added the verbatim transcript appendix, gave every recommendation equal priority, removed the T-0146 disposition recommendation, named the observed models as observations only, and recorded the duplicate pilot copy and verbatim-appendix intent. |
| 1.2 | 2026-11-08 | Buffy (Codebuff) | Review round 11 corrections: F-02 relabelled **Derived** with the mechanism separately **Confirmed** and §7 reworded; §16.4 replaced with a working import check that needs no worktree; §11 records the coverage gaps (REC H1–H4, ledger actor, Overseer resume). |

**For Claude (Web) and other reviewers.** Every factual claim above is traceable through §15. The two claims most worth challenging are (a) F-02's mechanism, because the failing test is unrecoverable, and (b) F-01's completeness, because it is supported by one `.pth` file, one code reading and one import demonstration — not by a captured gate trace. Reproduce §16.3 before accepting §6. Do not treat the model question as settled in either direction; §7 argues only that the record cannot support attribution, which is why R-04 exists.

**Distribution.** Canonical copy: `docs/reports/dispatch-failure-root-cause-and-remediation-v1.md`. A full duplicate for fleet-side readers is kept at `pilot/dispatch-failure-root-cause-and-remediation-v1.md`; the two are byte-identical and must be updated together. This report is intended to enter the project's final overall report as a **verbatim appendix**, keeping its own section and recommendation ids so cross-references stay valid. It deliberately cites sequence numbers, commit hashes and file paths rather than prose summaries, so a reader without repository access can still distinguish confirmed findings from derived ones and unknown ones.
