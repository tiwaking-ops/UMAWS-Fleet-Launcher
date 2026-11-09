# Replacement card for the supervised canary (T-0146 superseded)

> **Current execution note (2026-11-08):** T-0146 is already `VOID` (seq 3315). Use
> `pilot/drafts/d-69-canary-operator-packet-v1.md` for the corrected, base-neutral
> create/admit commands and the one-task dispatch. §2 below is pinned to `51c657f`
> and says `paths 61/61`; do not use it verbatim at a later HEAD.

**Status:** draft only. Nothing here has been created, admitted, leased or dispatched.
**Base it is pinned to:** `51c657f` (2026-11-08, local `main`) — the repaired tree.
**Why T-0146 cannot be used:** its work is already on main. `python -m cna.tools.coverage --check`
exits 0 and `coverage/rules_coverage.json` reports `rule_files: 69, paths: 61/61`, so with
`agents.toml [fleet] precheck_satisfied = true` the S8 guard refuses the lease as already satisfied.
That refusal is correct; the canary needs an oracle that fails today.

---

## 1. The card

| Field | Value |
|---|---|
| Title | `Record the repaired dispatch verification (supervised canary)` |
| Type | `implement` |
| Goal ref | `G-001` |
| Write scope | `docs/reports/dispatch-repair-verification-v1.md` |
| Read scope | *(none)* |
| Attempts | `1` (a canary must not retry-churn) |
| Priority | `0` (first in the queue) |
| Depends on | *(none)* |
| Oracle | see §1.1 |
| Hint base | pinned automatically at `pmk task create` time (`src/pmk/api.py` sets `hint_base_commit` when a hint is supplied) |

### 1.1 Oracle (single line, ASCII, no `&&`, no shell variables)

```text
python -c "import pathlib; p=pathlib.Path('docs/reports/dispatch-repair-verification-v1.md'); t=p.read_text(encoding='utf-8'); assert 'rule_files=69' in t and 'CNA-Rules.adoc' in t and 'base=' in t and 'gate=pytest -q' in t; print('verified')"
```

It fails on main today (file absent) and demands four facts that can only be written by looking at
the repaired tree. It is one command, so it behaves the same in cmd, PowerShell and the gate.

### 1.2 agent_hint (true at `51c657f`)

```text
Your worktree base is the repaired tree: docs/rules/CNA-Rules.adoc and docs/rules/sections/ (66 files) ARE present, and coverage/rules_coverage.json already reports rule_files=69 with paths 61/61. Copy nothing. Operate only inside your worktree. Write exactly one file, docs/reports/dispatch-repair-verification-v1.md, containing: `base=<the sha printed by git rev-parse HEAD>`, `corpus=docs/rules/CNA-Rules.adoc present`, `rule_files=69`, `gate=pytest -q`. Commit nothing; the harness commits. Then stop.
```

Every claim above is measurable at the pinned base (§3). It contains no "corpus is absent", no
"copy from the main tree", and nothing outside the write scope — the three defects of T-0146's hint.

---

## 2. Create and admit (operator, copy-paste)

Bash (Git Bash), from the repository root:

```bash
ORACLE="python -c \"import pathlib; p=pathlib.Path('docs/reports/dispatch-repair-verification-v1.md'); t=p.read_text(encoding='utf-8'); assert 'rule_files=69' in t and 'CNA-Rules.adoc' in t and 'base=' in t and 'gate=pytest -q' in t; print('verified')\""

HINT="Your worktree base is the repaired tree: docs/rules/CNA-Rules.adoc and docs/rules/sections/ (66 files) ARE present, and coverage/rules_coverage.json already reports rule_files=69 with paths 61/61. Copy nothing. Operate only inside your worktree. Write exactly one file, docs/reports/dispatch-repair-verification-v1.md, containing: base=<the sha printed by git rev-parse HEAD>, corpus=docs/rules/CNA-Rules.adoc present, rule_files=69, gate=pytest -q. Commit nothing; the harness commits. Then stop."

./.venv/Scripts/pmk.exe task create "Record the repaired dispatch verification (supervised canary)" \
  --type implement --goal-ref G-001 \
  --write docs/reports/dispatch-repair-verification-v1.md \
  --oracle "$ORACLE" \
  --agent-hint "$HINT" \
  --attempts 1 --priority 0 --propose
```

The command prints the new id. Inspect before admitting:

```bash
./.venv/Scripts/pmk.exe task show <NEW-ID>
```

Check three things in that output: `state` = `PROPOSED`, `hint_base_commit` is non-empty and equals
`git rev-parse HEAD`, and `acceptance.oracles` is exactly the string above. Then:

```bash
./.venv/Scripts/pmk.exe task admit <NEW-ID>
```

**Create it at the commit you intend to dispatch from.** The hint is pinned to HEAD at creation
time; if HEAD has moved, create the card again rather than leasing a stale hint.

Recommended cleanup (operator decision, not done here): void T-0146 with the reason
`superseded: corrected coverage landed in e08fa8d/9e4d047; S8 refuses the lease`. Leaving it READY
means the dispatcher will keep producing correct-but-noisy `PRECHECK_SATISFIED` refusals.

---

## 3. Dry run — measured, no lease, no dispatch

All four checks were run against `51c657f`. The satisfiability check used a throwaway detached
worktree (`.pmwork/card-dryrun/tree`), removed afterwards; main's `docs/reports` stayed clean.

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Oracle fails on main today | oracle run in repo root | **exit 1** — `FileNotFoundError: docs\reports\dispatch-repair-verification-v1.md` |
| 2 | Oracle is satisfiable by the intended work | oracle run in a throwaway worktree with the file written | **exit 0**, printed `verified` |
| 3 | Negative control: a file without the markers is not enough | same, file replaced with `nothing to see` | **exit 1** — `AssertionError` |
| 4 | R-09 scope is clean, so the lease will not be refused | `git status --porcelain -- docs/reports` | empty |
| 5 | Hint facts hold at base | `coverage --check`; `coverage/rules_coverage.json` | exit 0; `rule_files=69`, `paths=61/61`, `covered=61` |
| 6 | S8 will not refuse | oracle fails on main (check 1) | guard passes the lease through |

The intended file that satisfies the oracle (the worker may write equivalent content):

```markdown
# Dispatch repair verification (supervised canary)

- base=51c657f0507bb0a9287169b8c8531440d17ba962
- corpus=docs/rules/CNA-Rules.adoc present
- rule_files=69
- gate=pytest -q
```

---

## 4. What the supervised run should produce

One task, one attempt, no concurrency:

```powershell
.\start.ps1
.\.venv\Scripts\pmk.exe dispatch run
```

Expected event sequence for `<NEW-ID>` (all at one fence):

| Event | Expected payload |
|---|---|
| `CLAIMED` | `base_commit` = the pinned sha, `attempt: 1` |
| `AGENT_STARTED` | `adapter: kilo`, worktree under `work/`, log under `.pm/fleet/logs/<NEW-ID>/` |
| `AGENT_EXITED` | `class: OK`, `exit_code: 0` |
| `SUBMITTED` | `all_oracles_passed: true`, bundle `EB-<NEW-ID>-<fence>` |
| `ORACLE_RESULT` (gate) | `ok: true`, `exit: 0`, `cmd: pytest -q` |
| `INTEGRATING` → `INTEGRATED` | commit authored `umaws-pilot <umaws-pilot@localhost>` |
| `TASK_DONE` | state `DONE` |

Budget: agent typically 1–3 minutes, gate ≈ 4 minutes (measured 3 m 59 s on the canary of
2026-11-07), merge seconds. If the agent has not exited after 15 minutes the stall bound revokes it.

## 5. Abort immediately if

- the worktree path is outside `work/`, or the agent reports resolving `cna`/`pmk` from the main tree;
- the gate command differs from `pytest -q`, or the gate event carries no `failed_tests`/tails on failure;
- the merge commit is authored by `Tiwa Pene <tiwaking@gmail.com>` (the identity guard should make this impossible);
- `IDENTITY_ANOMALY` or a new `SCOPE_CONFLICT` appears for this task.

Stop the Console; do not edit `.pm/` by hand.

## 6. Record in D-69

Date, profile id, wall time, agent exit code, gate exit code, merge sha, commit author, and whether
any event deviated from §4. If the gate fails, paste `failed_tests` and `stdout_tail` from
`ORACLE_RESULT` — those fields exist because the 2026-11-07 failure could not be diagnosed.
