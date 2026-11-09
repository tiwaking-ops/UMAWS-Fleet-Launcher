# D-69 operator packet — T-0146 disposition and supervised canary

**Status:** DRAFT for operator review. This file executes nothing.
**Drafted:** 2026-11-08T21:52Z (UTC)
**Measured base:** `HEAD` = `7910de5` (2026-11-08)
**Authoritative state:** `pmk` / the hash-chained event log. The notes below were measured at drafting time.

## 0. Current state (do not re-derive by hand)

| Fact | Measured value |
|---|---|
| T-0146 | `VOID`, fence 125, `block_reason = "superseded by T-0159 coverage regeneration"` |
| T-0146 void event | `TASK_VOIDED` at seq 3315, `2026-11-08T12:40:44Z`, actor `operator` / `human` |
| Project | `PAUSED`; 32 `DONE`, 10 `PROPOSED`, 143 `VOID`; 0 `READY`; 0 active leases; 0 open queue items |
| Chain | verifies (3434 events at drafting time) |
| Sentinel | `pmk sentinel` currently `ok: true`, no findings; the red baseline in D-68 is historical |
| Identity guard | `core.hooksPath` is **empty**; A8 is outstanding |
| Fleet | `dispatch_paused: false`, `slots_in_use: 0`, cap 10; `kilo-auto` ready at priority 0 |
| Corpus at HEAD | `docs/rules/CNA-Rules.adoc` + 65 files under `docs/rules/sections/` |
| Coverage at HEAD | `rule_files: 69` (the canary oracle's fact) |
| Canary target | `docs/reports/dispatch-repair-verification-v1.md`; exact path is clean |
| `docs/reports` directory | has unrelated modified/untracked files; do not use a directory-wide cleanliness check |

The covering card is `pilot/cards/canary-replacement-v1.md`. It was dry-run-verified at `51c657f`. Its §2 hint is **stale at later HEADs** because it claims `paths 61/61`; HEAD's report has 82 paths and the working tree has 91. Do not copy that hint verbatim. Use the base-neutral hint in §3 below.

---

## 1. T-0146 — already VOID; the correct action is no action

```bash
cd /c/temp/projects/testproject1
PMK=./.venv/Scripts/pmk.exe
$PMK task show T-0146
```

Expected fields:

```text
"state": "VOID"
"block_reason": "superseded by T-0159 coverage regeneration"
"fence": 125
```

**Do not run `pmk task void T-0146` in the current repository.** It is already retired; a second void is not the recorded transition and may be refused. T-0146 is also **not** the canary: its oracle already passes on main, so S8 correctly refuses it (`pilot/repair-canary-runbook-v1.md`; R-11 requires a canary oracle that fails at its base).

Only if an older snapshot shows T-0146 as `READY`, void it once:

```bash
$PMK task void T-0146 \
  --reason "Superseded by T-0159 coverage regeneration; its oracle already passes on main, so S8 refuses it as a canary." \
  --actor operator
```

Then record the resulting `TASK_VOIDED` event in D-69. In the current repo, record the existing seq 3315 event instead.

---

## 2. Preconditions (stop if any fails)

Run from Git Bash:

```bash
cd /c/temp/projects/testproject1
PMK=./.venv/Scripts/pmk.exe
PY=./.venv/Scripts/python.exe

$PMK status
$PMK project status
$PMK task list --state READY
$PMK fleet status
$PMK pins check
$PMK sentinel
$PY -m pytest -q
git config --get core.hooksPath
test ! -e pilot/STOP && echo "STOP absent"
git status --porcelain -- docs/reports/dispatch-repair-verification-v1.md
```

Expected:

| Check | Expected at drafting time | If it differs |
|---|---|---|
| `pmk status` | `project_state: PAUSED`, `active_leases: 0`, `open_queue_items: 0`, chain verifies | Stop; do not dispatch |
| `pmk task list --state READY` | empty before admission | Stop; another card would compete for the canary slot |
| `pmk fleet status` | `dispatch_paused: false`, `slots_in_use: 0`; `kilo-auto` ready | Stop; do not clear pause by editing state files |
| `pmk pins check` | `ok: true` | Stop |
| `pmk sentinel` | `ok: true`, no findings (measured at drafting time); the D-68 red baseline is historical | Stop if any finding appears; compare it with the D-68 baseline |
| `pytest -q` | green; record the count | Stop if red |
| `core.hooksPath` | `.githooks`; **currently empty**, so A8 is not applied | Run `git config core.hooksPath .githooks`, then re-check; stop while empty |
| `pilot/STOP` | absent | If present, stop; do not delete it silently |
| canary target path | empty `git status` output | Stop if the file already exists or is modified |

**Current blocker:** A8 is not applied in this tree (`core.hooksPath` is empty). Run `git config core.hooksPath .githooks` before creating the canary; D-69's identity-guard precondition is not met until it is set. Re-check with `git config --get core.hooksPath`.

**Do not run `pmk project resume` for the canary.** The project stays `PAUSED`; `pmk dispatch run` is the explicit supervised dispatch action, and the Console's Conductor still drains the merge queue while the project is paused. `pmk project resume` is part of A10, after D-69 passes.

If `pmk fleet status` reports `dispatch_paused: true`, resolve that explicitly with the operator and record the action; do not hand-edit `.pm/fleet/fleet-state.json`.

---

## 3. Create and admit the replacement card

The oracle fails at the base because the report file is absent. The hint below is true at the current HEAD: the corpus is present and `coverage/rules_coverage.json` reports `rule_files: 69`. It deliberately makes no claim about the path count.

```bash
PMK=./.venv/Scripts/pmk.exe
ORACLE="python -c \"import pathlib; p=pathlib.Path('docs/reports/dispatch-repair-verification-v1.md'); t=p.read_text(encoding='utf-8'); assert 'rule_files=69' in t and 'CNA-Rules.adoc' in t and 'base=' in t and 'gate=pytest -q' in t; print('verified')\""

HINT="Your worktree base is the repaired tree at the commit pinned when this card was created. docs/rules/CNA-Rules.adoc and docs/rules/sections/ (66 corpus files) ARE present; copy nothing. Operate only inside your worktree. Read coverage/rules_coverage.json and note rule_files=69. Write exactly one file, docs/reports/dispatch-repair-verification-v1.md, containing: base=<actual sha from git rev-parse HEAD>; corpus=docs/rules/CNA-Rules.adoc present; rule_files=69; gate=pytest -q. Do not edit any other file. Commit nothing; the harness commits. Then stop."

$PMK task create "Record the repaired dispatch verification (supervised canary)" \
  --type implement --goal-ref G-001 \
  --write docs/reports/dispatch-repair-verification-v1.md \
  --oracle "$ORACLE" \
  --agent-hint "$HINT" \
  --attempts 1 --priority 0 --propose
```

Copy the printed id into `NEW_ID`, then inspect before admitting:

```bash
NEW_ID=T-XXXX
$PMK task show "$NEW_ID"
```

Check all five:

- `state` is `PROPOSED`;
- `hint_base_commit` is non-empty and equals `git rev-parse HEAD`;
- `acceptance.oracles` is exactly `$ORACLE`;
- `scope.write` is exactly `docs/reports/dispatch-repair-verification-v1.md`;
- `attempts.max` is 1 and `priority` is 0.

If any check fails, void the miscreated card with a reason and recreate it; do not admit it.

Dry-run the canary rule before admitting:

```bash
BASE=$(git rev-parse HEAD)
$PMK task precheck "$NEW_ID" --base "$BASE" --patch pilot/evidence/canary-replacement-v1.patch
```

Expected: `"canary_valid": true`, with the base oracle exiting 1 (file absent) and the scratch oracle exiting 0 (`verified`). The patch is only a satisfiability fixture; its recorded `base=51c657f...` is irrelevant because the oracle checks only that `base=` is present.

Admit only after that passes:

```bash
$PMK task admit "$NEW_ID"
$PMK task list --state READY
```

Expected: exactly one READY card, `$NEW_ID`. If any other card is READY, stop and do not dispatch.

---

## 4. Run exactly one supervised task

Start the Console in a PowerShell window for observation:

```powershell
cd C:\temp\projects\testproject1
.\start.ps1
```

Do **not** press the Console's Run button. The Console starts its own dispatcher paused by design (D-52); the Conductor loop is what drains the merge queue.

In a second PowerShell window, run the dispatch loop for the full canary window:

```powershell
cd C:\temp\projects\testproject1
.\.venv\Scripts\pmk.exe dispatch run --seconds 900
```

`--seconds` is the only dispatch control. The default is 30 seconds, which returns before the gate finishes and leaves the run unsupervised. 900 seconds covers the 15-minute stall bound. Do not start a second dispatch loop, raise concurrency, or admit another card while this runs.

Expected event sequence for `$NEW_ID`, all at one fence:

| Event | Expected payload |
|---|---|
| `CLAIMED` | `base_commit` = the pinned sha; `attempt: 1` |
| `AGENT_STARTED` | `adapter: kilo`; worktree under `work/`; log under `.pm/fleet/logs/<NEW-ID>/` |
| `AGENT_EXITED` | `class: OK`; `exit_code: 0` |
| `SUBMITTED` | `all_oracles_passed: true`; bundle `EB-<NEW-ID>-<fence>` |
| `ORACLE_RESULT` (gate) | `ok: true`; `exit: 0`; `cmd: pytest -q` |
| `INTEGRATING` → `INTEGRATED` | commit authored `umaws-pilot <umaws-pilot@localhost>` |
| `TASK_DONE` | state `DONE` |

`kilo-auto` is expected because it has priority 0. If a different profile is selected, record it and check that it is not an overseer/verifier profile; do not retry with another profile in the same minute.

### Abort immediately if

- the worktree is outside `work/`, or the agent reports resolving `cna`/`pmk` from the main tree;
- the gate command differs from `pytest -q`, or a failing gate has no `failed_tests` / tails;
- the merge commit is authored by `Tiwa Pene <tiwaking@gmail.com>`;
- `IDENTITY_ANOMALY` or `SCOPE_CONFLICT` appears for this task;
- a second task is claimed, or a second dispatch loop is running.

Abort with the operator stop, then stop the specific worker if it is still alive:

```bash
$PMK stop
$PMK agent stop "$NEW_ID"
```

Do not edit `.pm/` by hand. Record the abort in D-69 and leave dispatch paused.

---

## 5. Capture the evidence

```bash
$PMK task show "$NEW_ID"
$PMK agent list
$PMK sentinel
git log -1 --format='%h %an <%ae> %s'
ls .pm/evidence | rg "$NEW_ID"
rg -n "$NEW_ID" .pm/events/*.jsonl
```

Record, at minimum:

- final task state and fence;
- profile id and adapter;
- agent exit code and wall time;
- gate exit code, duration, and `failed_tests` (empty on pass);
- bundle id/path;
- merge sha and **exact** author identity;
- whether any `IDENTITY_ANOMALY`, `SCOPE_CONFLICT`, or worktree anomaly appeared;
- whether any event deviated from the table in §4.

---

## 6. D-69 record (fill after the run; do not paste a result before it exists)

The canonical draft row remains **PENDING** until the canary has actually run. Fill the D-69 row in `pilot/drafts/decisions-d62-plus.md` after the run; append to `pilot/decisions.md` only when A9 ratifies the D-62…D-69 batch:

```text
**D-69** | <YYYY-MM-DD> | operator (ran the canary) | **Canary result and dispatch resumption: <PASS / FAIL / BLOCKED>.** T-0146 is VOID (`TASK_VOIDED` seq 3315, `2026-11-08T12:40:44Z`; reason: `superseded by T-0159 coverage regeneration`) and was not reused. Replacement card `<NEW-ID>` was created at `<BASE>`, admitted, and run once under `<PROFILE>` with `pmk dispatch run --seconds 900`; the Console was open for observation only. Result: task `<STATE>`; agent exit `<CODE>`; gate exit `<CODE>`; bundle `<EB-NEW-ID-FENCE>`; merge `<SHA>` authored `<AUTHOR>`; deviations `<none / ...>`. Decision: `<resume dispatch (A10) only on PASS; otherwise remain PAUSED>`. | Resume dispatch without a canary; reuse T-0146; run more than one task/profile. | One run cannot prove other adapters/providers, concurrent load, or the full canary programme.
```

### Result block

- Date/time (UTC):
- Card / base:
- Profile / adapter:
- Agent exit / wall time:
- Gate exit / duration / `failed_tests`:
- Bundle:
- Merge sha / author:
- Final task state:
- Deviations:
- Decision:

### Decision rule

**PASS** only when all of these hold: task `DONE`; agent exit 0; gate `pytest -q` exit 0; bundle present and complete; merge author `umaws-pilot <umaws-pilot@localhost>`; no new `IDENTITY_ANOMALY` or `SCOPE_CONFLICT`; worktree under `work/`; no other task claimed.

On PASS, D-69 authorizes A10 (resume dispatch). On FAIL or BLOCKED, dispatch stays `PAUSED`; record the failure class and whether it is a repair regression or a provider/environment issue; do not retry with a different profile in the same minute. If the failure is a repair regression, open an incident before any retry.

---

## 7. References

- `pilot/cards/canary-replacement-v1.md` — card design and expected sequence (its §2 hint is pinned to `51c657f`; do not use it verbatim).
- `pilot/evidence/canary-replacement-v1-precheck.json` — dry-run evidence at `51c657f`.
- `pilot/evidence/canary-replacement-v1.patch` — satisfiability fixture for `pmk task precheck`.
- `docs/reports/dispatch-failure-root-cause-and-remediation-v1.md` — root cause, R-11, and the D-69 status table.
- `pilot/repair-canary-runbook-v1.md` — historical T-0146 runbook; superseded for execution by this packet.
