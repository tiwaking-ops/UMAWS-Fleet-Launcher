# G3 — a real CLI through a real lease

**Status:** **PASS** for the real-CLI half.  The gate's *OpenCode* half is
parked at the operator's instruction (see "What is still open").

**Author:** OpenCode.  **Date:** 2026-10-23.
**Authorised:** operator, 2026-10-23 ("2. APPROVED").
**Harness:** `pilot/g3-real-cli.py`.  **Evidence:** `pilot/spikes/g3/`.

## What had not been tested

The one-click demo (`pilot/demo_one_click.py`) runs the entire lifecycle —
brief, PDD, task cards, claim, worktree, order file, spawn, oracles, evidence
bundle, submit, merge queue, close-check — but it does so with the **fake**
CLI (`tests/fleet/fakecli.py`).  That proves the plumbing.  It does not prove
that a *real agent*, given a real lease and a real worktree, can do work that
the Kernel will accept.

That is what this test covers.

## Design

A **scratch git repository** outside the pilot (`%TEMP%\umaws-g3-real-*`), so
a real agent's file writes cannot touch this project.  Deleting the directory
undoes everything.  Proved by: the pilot's own tree is clean afterwards.

Nothing in the safety path was relaxed:

| Element | How it was real |
|---|---|
| the CLI | **kilo**, a real CLI with a real model |
| the lease | granted by the Kernel, with fence `1` |
| the worktree | a real git worktree, `work/T-0002-1` on branch `pmk/T-0002-1` |
| the oracle | `python check.py` — **functional**, run by the harness |
| the evidence | bundle with output hashes, diff scope, constitution hash |
| the merge | the merge queue ran the project gate before integrating |

**The oracle matters.**  The demo's oracle only checks that a file *exists*, so
a worker that writes an empty file would pass.  This test's oracle runs the
worker's script and parses its output as a Markdown table, comparing it to the
expected rows.  A file that merely exists passes nothing.

The task card was created with a `goal_ref`, so it was admitted **READY** and
was genuinely dispatchable.

## Result

```
[3] task card T-0002 created (READY)
[4] spawned T-0002 on kilo-real pid=10188
[5] finished T-0002: submitted (after 500s)
[6] after dispatch: {'VOID': 1, 'SUBMITTED': 1}
    T-0002 state: SUBMITTED
    lease: fence=1 holder='kilo-real' role='implement' attempt=1 restart_count=0
[7] merge T-0002: ok=True (merged)
[8] after the merge queue: {'VOID': 1, 'DONE': 1}
[9] close-check: ok=True
    G-001: pass (python check.py)
    gate: pass (python check.py)
[10] src/csv2md.py size after the run: 1512 bytes
```

The scratch repository's history:

```
623e015 Merge branch 'pmk/T-0002-1' into HEAD
1a421ad feat(T-0002): Make `python src/csv2md.py data.csv` print a Markdown table of data.csv
bd00c2f docs: project brief
a014814 inputs: csv, PDD, functional check
b487acf initial
```

The evidence bundle (`pilot/spikes/g3/evidence-bundle.json`), abridged:

```json
{
  "task": "T-0002", "fence": 1,
  "base_commit": "bd00c2f00edc...",
  "outputs": [{"path": "src/csv2md.py", "sha256": "98fba42e0e65..."}],
  "diff_scope_check": {"changed": ["src/csv2md.py"], "violations": [], "ok": true},
  "oracle_results": [{"cmd": "python check.py", "exit": 0, "ok": true}],
  "premise_check": {"refuted": false},
  "constitution_hash": "33c8b830d80f..."
}
```

The work is real, not a stub — `pilot/spikes/g3/csv2md.produced.py` is the
file the model wrote: proper `csv.reader` use, pipe escaping, a separator row,
column padding, and error handling.  That is a judgement on one sample, not a
claim about model quality.

## What this does **not** establish

1. **The recovery ladder.**  The run succeeded on `attempt=1` with
   `restart_count=0`.  L0–L4 were therefore **not exercised** with a real CLI.
   The failure paths are still measured only against the fake CLI and the
   synthetic fixtures.  A real CLI that dies mid-task — the case the ladder
   exists for — remains untested.
2. **One task, one CLI, one model.**  Only kilo, only `implement`, only one
   successful attempt.  The profile does not pin a model, so the model served
   is whatever kilo's default is this week; the bundle records
   `family: unknown`, and this document does not name a model it cannot prove.
3. **Latency risk, measured.**  A small task took **500 seconds** against a
   `wall_min = 12` (720 s) budget.  It fit, but only just.  For real tasks the
   wall-clock budget is a live risk, and it is a *guess* — the Kernel cannot
   see this CLI's token use (`L-F2`), so time is the only measurable axis.

## Verdict

**A real CLI, under a real lease, in a real worktree, did work that a
functional oracle accepted and the merge queue integrated.**  That is the
condition the gate names, and it is met.

## What is still open

- **The OpenCode handover.**  The gate's wording names *an OpenCode session*.
  OpenCode's free tier is exhausted and its quota is not published, so the
  operator's instruction is to **leave the quota `UNKNOWN` and test it
  together later** (D-37).  That condition is therefore **parked, not
  satisfied** — and it is the only outstanding item on G3.
- Whether the gate is **closed** is the operator's call, not the
  implementer's.
