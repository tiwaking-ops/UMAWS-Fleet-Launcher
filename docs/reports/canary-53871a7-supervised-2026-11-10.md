# Supervised base canary at `53871a7` — 2026-11-10

**Result: PASS.**

This records the isolated, self-contained base canary at
`53871a7a13e2d000b1b6a6231568a653a9c3334f`. It is **not** a live-kernel
canary: the run used a separate `.pm` snapshot and a separate branch, and the
live project remains `PAUSED`. It does not authorize dispatch resumption.

## Why the run was isolated

The live kernel cannot satisfy `pmk canary run`'s preflight. At the time of the
run it had 12 READY cards and 2 active leases; the runner requires exactly one
READY card and zero active leases. No live cards, leases, or `.pm` events were
changed for this canary.

The recorded run used:

| Field | Value |
|---|---|
| Root | `tmp/canary-base-20261110` |
| Branch | `canary-base-53871a7` |
| Base commit | `53871a7a13e2d000b1b6a6231568a653a9c3334f` |
| Command | `pmk --root "$(pwd)/tmp/canary-base-20261110" canary run --seconds 900` |
| Card | isolated-base `T-0147` (not the live `T-0147`) |
| Target | `docs/reports/canary-53871a7.md` |
| Profile / adapter | `kilo-auto` / `kilo` |
| Attempt / fence | 1 / 120 |

The base is self-contained: `docs/rules/CNA-Rules.adoc` and the 66 corpus files
are present, `rule_files=69`, and the full clean-worktree `pytest -q` was
already green at `53871a7` (`tmp/clean-head-full2.log`).

## Preflight

`T-0147` was created at `13:28:00Z` and admitted at `13:28:03Z` as the only
READY card. Before the run the base reported 147 tasks, 1 READY, 0 active
leases, and a verified chain of 3,123 events.

The canary precheck produced:

| Check | Result |
|---|---|
| Base oracle | exit 1 — `FileNotFoundError: docs\reports\canary-53871a7.md` |
| Scratch oracle | exit 0 — `verified` |
| `canary_valid` | `true` |
| Reason | oracle fails at the base and passes on the scratch implementation |

## Event record

All timestamps are UTC on 2026-11-10.

| Seq | Time | Event | Evidence |
|---:|---|---|---|
| 3124 | 13:28:32 | `CANARY_STARTED` | task `T-0147`, project `PAUSED`, 900 s window |
| 3125 | 13:28:34 | `CLAIMED` | base `53871a7…`; fence 120; `kilo-auto` / `kilo` |
| 3126 | 13:28:36 | `AGENT_STARTED` | pid 9744; worktree `tmp/canary-base-20261110/work/T-0147-120` |
| 3129 | 13:30:10 | `AGENT_EXITED` | class `OK`; exit 0 |
| 3131 | 13:30:10 | `AGENT_ADVISORY` | `RESULT.md does not mention the task id T-0147` (non-blocking) |
| 3132 | 13:30:11 | `SUBMITTED` | all oracles passed; bundle `EB-T-0147-120` |
| 3133 | 13:35:11 | `ORACLE_RESULT` | stage `gate`; `ok: true`; `cmd: pytest -q` |
| 3134 | 13:35:12 | `INTEGRATING` | commit `05b54d217902bdb41a751c2991c6b542a9f3100a` |
| 3135 | 13:35:12 | `INTEGRATED` | same commit; bundle `EB-T-0147-120` |
| 3136 | 13:43:33 | `CANARY_FINISHED` | state `DONE`; `ok: true`; 328 ticks; 900.61 s |

Task state is `DONE`; there is no separate `TASK_DONE` event in this chain.
The final run result was:

```json
{
  "task": "T-0147",
  "state": "DONE",
  "ok": true,
  "ticks": 328,
  "elapsed_s": 900.688,
  "started_seq": 3124,
  "finished_seq": 3136
}
```

## Merge and evidence

| Item | Evidence |
|---|---|
| Merge commit | `05b54d217902bdb41a751c2991c6b542a9f3100a` |
| Parents | `53871a7…` (base) and `e5fa289…` (worker commit) |
| Author / committer | `umaws-pilot <umaws-pilot@localhost>` |
| Diff | `docs/reports/canary-53871a7.md`, 1 insertion |
| Bundle | `.pm/evidence/EB-T-0147-120/bundle.json` |
| Output SHA-256 | `2d4f3e835e6cd9c6266adf44e5e8dd6f45b94c60ce5ad8ff532edcf19a70adaa` |
| Gate output | `cmd: pytest -q`; `exit: 0`; `ok: true`; 17 stdout-tail lines ending `[100%]`; `failed_tests: []`; empty stderr |
| Task state | `DONE`; attempt 1; fence 120 |
| Base status after | 147 tasks (138 VOID, 7 DONE, 2 PROPOSED); 0 READY; 0 active leases; 0 queue items; 102 incidents (unchanged; none added by this run); chain 3,136 events |

The merge is on the isolated `canary-base-53871a7` branch. It is not a commit
on live `main`; at the time of the run live `main` was `eb0c226`. The live
status after the run was still `PAUSED` with 212 cards (155 VOID, 43 DONE, 12 READY, 1 VERIFYING,
1 LEASED), 2 active leases, 35 worktrees, and a verified chain of 3,630 events.

## Negative checks

- `diff_scope_check`: only `docs/reports/canary-53871a7.md` changed;
  `violations: []`; `ok: true`.
- No `IDENTITY_ANOMALY` was recorded. The merge is authored by the pinned
  pipeline identity.
- No `SCOPE_CONFLICT` was recorded; the worker worktree is clean.
- No `INFRA_RETRY` was recorded; the merge queue did not need a retry.
- No additional claim, lease, or card was created beyond the canary card.
- The target file contains the required facts:
  `base=53871a7…; corpus=docs/rules/CNA-Rules.adoc present; rule_files=69;
  gate=pytest -q`.

## Deviations and limits

- `MODEL_SERVED` (seq 3130) has `served_models: []` and `source: "none"`.
  This is the known H4 provenance limitation also seen in T-0191/T-0196; it
  does not affect acceptance.
- `AGENT_ADVISORY` (seq 3131) notes that `RESULT.md` did not mention the task
  id. The worker wrote the required target file and the advisory is
  non-blocking.
- This is an isolated base canary. It proves the real claim → lease → worktree
  → agent → acceptance → gate → merge path at `53871a7`, not the live kernel's
  current queue, and it does not authorize A10.
- No push was performed. No live `.pm` state, lease, card, or project state was
  changed by this run.

## Setup note: discarded first attempt

An earlier attempt used the detached worktree `tmp/clean-head-20261110` at
`53871a7`. Its worker produced commit `d185c8b`, but the merge queue resolves
the repository default branch and therefore targeted live `main` at `eb0c226`,
not the detached base. The attempt was stopped before any gate result was
recorded and is not counted. The worker commit is preserved as the local tag
`aborted-canary-T-0147-120`. The recorded run above uses a branch checked out at
`53871a7`, so its merge parent is the base under test.
