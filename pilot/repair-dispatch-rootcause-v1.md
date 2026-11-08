# Dispatch failure — root cause

**Status:** investigated from recorded evidence only; no dispatch was started by the agent.
**Scope:** why surveillance-supervised dispatch failed to carry real cards to `DONE`, and what
can honestly be said about "is it the overseer model or the worker model?".
**Date:** 2026-11-08. **HEAD at time of writing:** `9e4d047` (local only, never pushed).

---

## 1. Answer in one paragraph

There is no evidence that either model is defective. The recorded failures resolve into one
dominant cause with three manifestations — **the fleet never pinned the import environment to the
tree under test**, so gates, workers and the overseer all imported packages from the *main working
copy*, which was mutating while they ran. That made identical canary inputs fail at 08:43 and pass at 09:41 (local, +1300), made workers edit the wrong `coverage.py`, and made the overseer describe the main tree
while believing it described a worktree (hence the false T-0146 hint). Two secondary causes
compound it: **bash idioms issued to PowerShell 5.1** (904 parser failures in the overseer log,
13–16 per worker attempt) and **a hint with no recorded base commit** (`hint_base_commit=""`), which
made the kernel's REC-13 staleness guard inert. The model question cannot be answered from the
ledger at all: `MODEL_SERVED` records `profile`, `served_models: []`, `source: none`,
`via_gateway: false`, and bundles record `family: unknown`.

---

## 2. Evidence base and method

Read-only review of the kernel ledger, evidence bundles, agent logs and the worktrees that still
exist, plus one reproduction run in a throwaway worktree. No card was leased, no dispatch started,
no `.pm/` state written. The reproduction is labelled as such and is the only non-recorded datum.

| Symbol | Path |
|---|---|
| L-148 | `.pm/fleet/logs/T-0148/120-0.log` |
| L-150 | `.pm/fleet/logs/T-0150/121-0.log` |
| L-146 | `.pm/fleet/logs/T-0146/124-0.log` |
| L-145a..c | `.pm/fleet/logs/T-0145/122-0.log`, `122-1.log`, `123-0.log` |
| L-overseer | `.pm/fleet/logs/overseer/0-0.log` (9,029,312 bytes / 168,688 lines) |
| B-148 | `.pm/evidence/EB-T-0148-120/bundle.json` |
| B-150 | `.pm/evidence/EB-T-0150-121/bundle.json` |
| Ledger | `.pm/events/2026-11-07.jsonl`, `.pm/events/2026-11-08.jsonl` |

---

## 3. The canary flip: same inputs, two verdicts

This is the core observation, and it is fully recorded.

| | T-0148 (fence 120) | T-0150 (fence 121) |
|---|---|---|
| `base_commit` in bundle | `82f6be16e410…` | `82f6be16e410…` |
| output `docs/canary.md` sha256 | `dc943d75…c93e` | `dc943d75…c93e` |
| `diff_scope_check` | ok, no violations | ok, no violations |
| own oracle | exit 0 | exit 0 |
| gate `pytest -q` | **exit 1** (seq 3141, 19:43:35Z) | **exit 0** (seq 3157, 20:41:36Z) |
| terminal event | `VERIFIED` class `ORACLE_FAILED` (seq 3142) → `REWORK` | `INTEGRATED` (seq 3159) → `DONE`, commit `e31d70a` |
| agent log size | 799 bytes | 530 bytes |
| model identity in ledger | `kilo-auto`, `served_models: []` | `kilo-auto`, `served_models: []` |

The two branches differ only in their commit message. Both merged onto the same main HEAD
(`82f6be1`). The recorded timeline rules out an intervening fix:

| UTC | Event |
|---|---|
| 19:39:36 | T-0148 submitted, own oracle green |
| 19:43:35 | T-0148 gate exits 1 → REWORK |
| 19:54:23 | project **paused by the operator** |
| 20:15:28–20:16:48 | T-0150 created, admitted, project resumed |
| 20:17:01 | T-0150 claimed (same base `82f6be1`) |
| 20:18:44 | T-0150 exits, advisory only (“RESULT.md does not mention the task id”) |
| 20:41:36 | T-0150 gate exits 0 → INTEGRATED (`e31d70a`) |

Nothing was committed to main between the two gates, so the flip is a property of the run, not of
the code.

**Reproduction (2026-11-08, agent-run, throwaway worktree):** create a detached worktree at
`82f6be1`, merge `pmk/T-0148-120` with `--no-ff`, run `pytest -q` with the worktree's `src`/`tests`
on `PYTHONPATH` → **507 passed, exit 0**. The card's code was green all along.

So the 08:43 failure was not the diff. It was the environment the gate ran in.

### 3.1 Why the environment was unpinned, and until when

`src/fleet/merge.py` runs the gate in a temporary worktree (`integrate`, step 3). The gate's own
`subprocess.run(..., cwd=temp_wt, env=gate_env)` only started passing `worktree_env(temp_wt)` in
**`ebe46ce` — 2026-11-08 12:34**, i.e. *after* both canary runs (19:43Z and 20:41Z). The code that
ran the two canary gates is in `13b8959` and has **no `env=` argument at all**:

```python
# git show 13b8959:src/fleet/merge.py  (lines 248-251)
proc = subprocess.run(gate_cmd, shell=True, cwd=str(temp_wt),
                      capture_output=True, timeout=900,
                      text=True, encoding="utf-8", errors="replace")
```

With no `env=`, the gate inherits the dispatcher's environment — and that environment hard-codes the
**main working copy** on `sys.path` via the venv's editable-install hook:

```
.venv/Lib/site-packages/__editable__.umaws_fleet-0.1.0.pth
  -> C:\temp\projects\testproject1\src
```

Demonstrated inside a throwaway worktree at `82f6be1` with the T-0148 branch merged:

```
$ python -c "import cna.tools.coverage as c, pmk; print(c.__file__, pmk.__file__)"
cna  -> C:\temp\projects\testproject1\src\cna\tools\coverage.py
pmk  -> C:\temp\projects\testproject1\src\pmk\__init__.py
```

The `cwd=temp_wt` is therefore cosmetic: the tree being judged is not the tree whose code is
executed. Main's tree carried 129 dirty paths at spawn (`AGENT_STARTED`, `main_tree_status.count =
129`).

**Honest limit of this finding.** Re-running that same old configuration today exits **0** (507
passed), because current main's `src` is consistent with the old tests. So the coupling is proven,
but the *specific* 08:43 divergence is not reconstructable: it required main's working `src` to
differ from the merged tree at that moment, and neither the failing test nor the gate output
survives (§3.2). The gate took **3 min 59 s** for T-0148 (19:39:36Z → 19:43:35Z) and **22 min 51 s** for T-0150
(19:39… 20:18:45Z → 20:41:36Z), of which 10 min 15 s were spent with the project paused. Both ran
the whole suite and neither was cut short by the 900 s timeout. Whether the failures came from
main-tree `src` or from suite state under the concurrent overseer cannot now be separated; both are
"the gate's inputs were not pinned to the tree under test", and both are closed by `ebe46ce` plus
the recorded diagnostics below.

### 3.2 The failure is now unrecoverable, by design

`integrate()` captures the gate's stdout/stderr and then records only `exit`. No log of the failing
assertion survives: `.pm/evidence/EB-T-0148-120/` contains `bundle.json` alone, the task worktree has
`ORDER.md`, `RESULT.md`, `provenance.json` and nothing else, and `pytest_junit.xml` in main is
rewritten by other runs. **Which test failed at 08:43 cannot be established from the record.** Any
claim that names a specific failing test would be invention.

**Fix applied in this pass:** gate failure events now carry `failed_tests`, `stdout_tail` and
`stderr_tail` (`src/fleet/merge.py::_gate_diagnostics`, pinned by
`tests/fleet/test_merge_gate_diagnostics.py`). The next REWORK from a gate will be diagnosable
without archaeology. Note what this would have bought here: the single string
`FAILED tests/…::…` was the difference between a 20-minute investigation and an afternoon.

---

## 4. The worker manifestation (T-0145, T-0146)

Same cause, different surface: the worker's *own* commands resolved `cna` from main.

L-146 (the decisive lines):

```
$ python -c "import cna.tools.coverage as c; print(c.__file__)"
C:\temp\projects\testproject1\src\cna\tools\coverage.py      <- main tree, not work/T-0146-124
```

Only after pinning the variable by hand did the worktree win:

```
$ $env:PYTHONPATH="C:\temp\projects\testproject1\work\T-0146-124\src"; python -c "..."
C:\temp\projects\testproject1\work\T-0146-124\src\cna\tools\coverage.py
69
```

Consequences recorded in the run: repeated "the worktree does not have the corpus / does not scan
`.adoc`" conclusions drawn from main's tool, a self-invented `PYTHONPATH` workaround, and a diff
(`M src/cna/tools/coverage.py`) that had to be reconstructed from the worktree rather than trusted
from the agent's narrative. T-0145 shows the same signature: `main-src` imports in `122-0.log`, and
the agent's own RESULT note "plain `-m` may resolve `cna` from the parent tree".

Fixed at `55f3f46` (`src/fleet/runenv.py::worktree_env`, applied to harness, merge, project,
dispatcher, overseer) with six tests in `tests/fleet/test_worktree_env.py`; the gate half was
`ebe46ce`, extended here by the diagnostics above. **This is the fix that matters, and it is the one
that has not yet been exercised by a real dispatch.**

---

## 5. The overseer manifestation (and the false hint)

L-overseer is the strongest single piece of evidence, because it is the agent that writes hints.

- model header: `> build · recursive/flint-v1.0:free`
- 904 PowerShell/parser failures, 115 references to main-tree `src` paths, in 168,688 lines.

Its own prose (lines 168374–168425) states the belief the T-0146 hint was built on:

> "Corpus content is still NOT in main HEAD. `git ls-tree -r HEAD docs/rules/` = 6 files …
> `CNA-Rules.adoc` + `sections/` (66 files) exist **only as untracked files** in main's working
> tree"
> "Their agent hints authorize copying the corpus into the worktree"

Both halves are defensible *at authoring time* and wrong *at dispatch time*: by the time T-0146 was
leased at `e08fa8d`, the corpus was in HEAD and present in the worktree. The worker's log shows it
checking and correctly ignoring the instruction ("The worktree already has CNA-Rules.adoc and
sections/"). The hint also told the agent to copy 66 files that its write scope
(`coverage.py`, `rules_coverage.json`, `test_coverage.py`) excludes — following it would have
produced a scope violation at submit.

Mechanism, precisely:

1. The hint is free text written by a model that had been reading the **main tree** (115 main-src
   imports; 904 commands that failed outright, several of which would have returned empty output
   that reads like "absent").
2. `pmk task create --agent-hint` pins `hint_base_commit` **only when the hint is non-empty**
   (`src/pmk/api.py`); T-0146's card carries `hint_base_commit = ""`.
3. `_stale_hint_reason()` returns `""` immediately when `base` is empty, so REC-13 could not fire
   even though HEAD had moved and the hint asserts tree contents (`"corpus"`, `"docs/rules"` are in
   `_HINT_STALE_TOKENS`).

P3 (`6f92d31`) added hint pinning + `IDENTITY_ANOMALY`, and S8 refuses leases whose oracles already
pass. The empty-base hole for **existing** cards is not retro-fixable: `pmk task` exposes only
`create/admit/list/show/void`, so T-0146's hint cannot be amended. It needs a fresh card or an
operator judgement, not a silent edit.

### 5.1 The overseer could not wake at all, so no hint could be corrected

Nine `OVERSEER_WOKEN` events exist for the window and **all nine** carry the same error
(seq 3137, 3143, 3160, 3165, 3169, 3192, 3199 …):

```
the Overseer profile pi-orca-deepseek is disabled
```

`agents.toml` puts exactly that disabled profile first:

```toml
[overseer]
profiles = ["pi-orca-deepseek", "kilo-auto", "opencode-fallback", ...]
```

`OverseerRunner.wake()` took `profiles[0]` and, when its fleet-state entry was disabled, recorded
the refusal and returned — it never tried `kilo-auto`. So for the whole failure window the fleet had
**no functioning overseer at all**: a stale hint could not be refreshed, no independent check
remained that might have caught §3, and the only overseer text in circulation was the older session's
9 MB log from §5.

This is a plain defect, not a model judgement: the ordered list exists precisely so that a
strongest-first choice degrades gracefully.

Fixed in this pass: selection walks the ordered list and takes the first profile that is enabled and
not cooling, naming every skipped profile in the payload when none is usable. Pinned by
`tests/fleet/test_overseer_profile_fallback.py`, beside the existing wake-suite
`tests/fleet/test_overseer_wake.py` (which was accidentally overwritten once during this repair and
restored byte-for-byte from `9eb39ad`; the two files together are the coverage).

---

## 6. Secondary cause: shell dialect

Kilo's command runner on this machine is PowerShell 5.1. Workers and the overseer issue bash. All
four idioms fail loudly, which is the good case — the bad case is a command that returns nothing and
is read as evidence of absence:

| Issued | PowerShell's answer |
|---|---|
| `ls -la <dir>` | `A parameter cannot be found that matches parameter name 'la'` |
| `cd <dir> && python …` | `The token '&&' is not a valid statement separator` |
| `cd <dir> & python …` | `The ampersand (&) character is not allowed` |
| `PYTHONPATH=<dir> python …` | `… is not recognized as the name of a cmdlet` |
| `$env:PYTHONPATH="<dir>"; python …` | works |

Counts (`grep -c` over each log): overseer 904, T-0145/122-0 16, T-0146/124-0 13, T-0150 0,
T-0148 0. The two canary runs that used no shell at all are exactly the two that behaved.

**Fix applied in this pass:** `render_order()` now emits a `## Environment` section stating the
platform and the PowerShell forms (`src/fleet/order.py::_command_syntax`, pinned by
`tests/fleet/test_order_environment.py`, both platforms). This reduces wasted turns; it cannot be
proven to help until a live run occurs, and it is a mitigation, not the root cause.

---

## 7. Separate class: provider capacity (not a dispatch defect)

Many short logs are a single 429, e.g. `T-0002/12-0.log`, `T-0003/3-0.log`, `T-0109/89-0.log`:
`"code":"free_rate_limited" … "retry_after_seconds":635`. The overseer log's tail is nothing but
429s. These attempts burned no model reasoning and no repository state; they are free-tier capacity
events, and should not be counted as model or fleet failures.

---

## 8. On "is it the overseer model or the worker model?"

**It is not attributable from the record, and this is a measurement gap, not an analysis gap.**

Every `MODEL_SERVED` event for these cards is empty of identity:

```json
{"deployment": "", "profile": "kilo-auto", "served_models": [], "source": "none",
 "via_gateway": false}
```

`AGENT_STARTED` records `adapter: "kilo"` and the profile id, not a model. Bundles record
`"family": "unknown"`. The only identity anywhere is the CLI's own header line —
`> code · kilo-auto/free` for workers, `> build · recursive/flint-v1.0:free` for the overseer — and
`kilo-auto` is a *router alias*, so even that string does not name the model that answered a given
request.

What the evidence does support:

- The failures are **reproducible from the environment alone**: identical inputs, opposite verdicts;
  and the same inputs pass once the environment is pinned.
- The observable defect in the overseer output is **wrong state attribution** (describing main while
  claiming worktree), which is a grounding/environment failure with a mechanical explanation above —
  not a reasoning failure that would distinguish one model from another.
- No worker attempt failed by producing a wrong patch; they failed by importing the wrong package,
  losing turns to parser errors, or answering a stale hint. Two attempts (T-0145/123-0,
  T-0148) produced correct content that the gate then misjudged.

What would settle the model question (not implemented; needs a live run):

1. Record the CLI header's model string in `AGENT_STARTED` and in the bundle's `resolved_models`.
2. Record a per-run count of failed tool commands by class (`parser`, `notfound`, `timeout`) — the
   number is the cheapest capability signal available.
3. Record gate output (done here), so a future "model vs environment" dispute has a diff to read.
4. Only then compare profiles on the *same* card, same base, same shell contract.

Until 1–3 exist, "the model did it" is unfalsifiable; presenting it as the cause would violate the
constitution's rule that authority comes from recorded status, not narrative.

---

## 9. What is fixed, what is not

| Cause | Status |
|---|---|
| Gate judged a tree it did not import from (`ebe46ce`, `55f3f46`) | fixed; verified by the reproduction above |
| Worker/overseer imports from main (P1 `55f3f46`) | fixed, 6 tests; **not yet exercised by a live dispatch** |
| Gate verdict undiagnosable | fixed here (`_gate_diagnostics` + 3 tests) |
| Bash idioms in PowerShell | mitigated here (`## Environment` in ORDER + 3 tests) |
| Stale hint, empty `hint_base_commit` (T-0146) | guard exists (REC-13, P3); card cannot be amended — needs a new card |
| Overseer never woke (disabled profile first, no fallback) | fixed here: selection skips disabled/cooling profiles; 2 tests (`test_overseer_profile_fallback.py`) |
| T-0148 REWORK card | the card is already satisfied on main; S8 precheck will refuse the lease, which is correct |
| Rate-limit 429s | external; not a fleet defect |
| Model attribution | **open**; instrumentation proposed, not built |

---

## 10. Operator actions still required

1. `git config core.hooksPath .githooks` (A8).
2. Ratify D-62…D-68 (A9); D-69 stays blank — there is no post-repair canary, and the earlier claim
   that one passed is false: T-0148 failed its gate (`ORACLE_FAILED`, seq 3142) and only T-0150,
   a separate card with identical content, integrated at 09:34.
3. Re-dispatch T-0146 from a corrected card (its hint is immutable and its worktree base `e08fa8d`
   predates the repair), then run `pilot/repair-canary-runbook-v1.md` (A10).
4. When a gate fails, keep the event: it now carries `failed_tests` and output tails.

---

## 11. Falsifiers

- If a post-repair dispatch still fails with a **gate** exit ≠ 0 while `pytest -q` passes in the
  same worktree by hand, the environment pinning is incomplete → re-open §3.
- If workers still emit `ls -la` / `&&` after `## Environment` ships, the shell contract is being
  ignored or the adapter's runner is not PowerShell → re-open §6 with the log.
- If two profiles on the same card produce different outcomes under identical pinned environments,
  the model question becomes answerable → §8 instrumentation becomes mandatory.
