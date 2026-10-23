# G5 — the live capacity run: RESULT

**Date:** 2026-10-23, ~21:0x–21:5x local · **Authorised:** operator, 2026-10-23
("Execute G5") · **Author:** OpenCode.

**Script:** `pilot/g5-live-capacity.py` · **Criteria (pre-written):**
`pilot/gate-posture-record.md` (G5 P1–P5). · **Summary JSON:**
`pilot/spikes/g5/g5-summary.json`.

## Scope, as stated before the run

Free-tier only — hermes, kilo (`kilo-auto/free` router) and pi; cline
excluded (its free models are rate-limited until 2026-10-24); opencode
excluded (its free tier was spent by the G3 attempt minutes earlier). **$0
spent**; only free quota. Real CLIs on real leases in real worktrees, in a
throwaway repo under `%TEMP%`.

## Run 1 (live)

| # | Criterion | Result |
|---|---|---|
| P1 | ≥3 concurrent real workers | **6** — 3 × hermes, 3 × kilo simultaneously |
| P2 | ≥1 task DONE with evidence | **6 DONE, 6 evidence bundles** |
| P3 | quota cooldown fires *or* zero failures | **zero failures, no ceiling hit** |
| P4 | the RAM guard holds | min free RAM **4 965 MB** (floor 2 048) |
| P5 | every failure classified | **no failures at all** |

All six tasks merged through functional per-task oracles (each module runs
and prints its own token), sentinel clean, I1 chain verifies (89 events).
**P1–P5 pass.** The only red mark was `close-check: no PDD` — the drill's own
omission, fixed and re-run below.

## Run 2 (live, PDD added) — the complete pass

Second live run, identical shape, with the PDD in place so the project can
reach **DONE through the close-check**, the way F1 demands:

| Measure | Run 1 | Run 2 |
|---|---|---|
| concurrent real workers (peak) | 6 | **6** (3 hermes + 3 kilo) |
| tasks DONE | 6 | **6** |
| evidence bundles | 6 | **6** |
| merged through the functional gate | 6/6 | **6/6** |
| close-check | *no PDD (drill defect)* | **ok=True** — G-001/G-002/G-003 pass |
| sentinel / chain | clean / 89 events | **clean / 86 events** |
| min free RAM (floor 2 048) | 4 965 MB | **5 162 MB** |
| failures / UNKNOWN classes | 0 | **0** |

**Verdict: P1–P5 all pass, across two independent live runs.** The project
lifecycle reached DONE with real CLIs doing real work — the run F1-shaped
evidence that only fake-CLI runs had previously provided.

## Reading

- **Real workers follow the same mechanism the fake CLI exercises.** The
  dispatch → lease → worktree → order → oracles → evidence → merge path that
  held for the fake held for hermes and kilo unchanged, in one run, with six
  parallel workers.
- **The quota cooldown never fired** because the ceiling was never reached —
  P3's alternative branch, and the honest reading is "no ceiling hit", not
  "the cooldown works". The cooldown remains unexercised against a real
  provider; it is synthetic-fixture-tested only.
- **pi never worked.** priority 30 behind hermes(3) + kilo(3) filled all six
  slots; pi stays live-unrun, and its cline sibling is excluded until
  2026-10-24.
- **`max_total_agents` is not answered here** — by design. G5 is 6 real
  workers; the ceiling question is F7/S-W1 (D-48), which passed at 100
  slots. G5's job was to prove real agents survive the mechanism under
  load; it did.
