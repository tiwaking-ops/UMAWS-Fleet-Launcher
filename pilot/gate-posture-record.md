# Pre-written criteria: G4, G5, F7 and S-W1

**Status:** written **before** the runs, as `pilot/amendment-gates.md` §2 requires.
**Date:** 2026-10-23, 19:5x local. **Authorised by:** operator, 2026-10-23
("Execute G4 / Execute G5").

---

## G5 — live capacity run

**Named consequence (amendment §4):** spend, and sustained load on real
providers. G5 is the **live** half of the capacity question.

**Scope, stated before the run:**

* Providers in scope: the free-tier CLIs only — `hermes`, `kilo` (the
  `kilo-auto/free` router), and `pi` (`deepseek/deepseek-v4-flash-free`).
  `cline` excluded (its five free models are rate-limited until 2026-10-24
  per the operator); `opencode` excluded (its free tier is exhausted and is
  the subject of the G3 attempt instead).
* Money spent: **$0**. Only free-tier quota is spent. The paid-tier question
  is *not* answered by this run and is not claimed.
* Real work: real CLIs on a real lease in a real worktree, in a **throwaway
  repository under `%TEMP%`**, deleted to undo.

**Pass criteria:**

| # | Criterion | Pass looks like |
|---|---|---|
| **P1** | The fleet drives ≥3 concurrent real workers | `dispatcher.runs` reaches ≥3 simultaneously at least once |
| **P2** | A real worker's task reaches `DONE` through the harness | ≥1 task DONE with an evidence bundle (oracles, scope, constitution hash) |
| **P3** | Cooldown fires under load, not after a crash | at least one `QUOTA` failure with `cooldown_remaining_s > 0`, **or** zero failures (no ceiling hit) |
| **P4** | The RAM guard holds | free RAM never drops below `min_free_ram_mb` during the run |
| **P5** | Every failure is classified | no `UNKNOWN` failure class for any real worker |

**Recorded, not scored:** concurrency actually reached and when; wall time to
first `DONE`; whether the ramp was cut short by quota. **The ceiling question
(`max_total_agents`) is answered by F7/S-W1 below, not by this run** — G5
proves *real* workers follow the mechanism; F7 proves the *mechanism* scales.

---

## F7 — the scale drill (100 fake workers, fake CLI)

**What it tests:** the mechanism at operator-ceiling scale (100 concurrent
slots). The proposal (fleet-launcher §G-F5): `max_total_agents` is raised to
100 **only** after F7 passes.

**Pass criteria:**

| # | Criterion | Pass looks like |
|---|---|---|
| **F1** | 100 tasks complete | 100 × `DONE`, 0 failed |
| **F2** | Simultaneous slots actually used | `len(dispatcher.runs)` peaks ≥50 (i.e. the parallel path, not a serialised queue) |
| **F3** | Chain and sentinel survive | `pmk sentinel` clean, I1 chain verifies, 0 torn writes |
| **F4** | The RAM guard holds | free RAM never below `min_free_ram_mb` |

---

## S-W1 — worktree cost

**What it measures:** the cost of creating 20 and 100 worktrees on this
machine (time per batch, disk, time for the first and last worktree), so
`max_total_agents` stops being a guess.

**Recorded, not scored:** worktree count, wall seconds, peak disk MB,
wall seconds of the last worktree (path-limit evidence). Delete the scratch
directory to undo.

---

## G4 — turn Caliber auto-sync on

**Named consequence (amendment §4):** the generator writes instructions
agents will follow, on every commit.

**The exact change (presented before the change — the two-key rule):**

`.pm/policy.toml`, line 36, in `[context_sync]`:

```toml
mode = "dry-run"                  # D-P10: auto-sync is enabled only at gate G4
```
becomes
```toml
mode = "auto"                     # G4 crossed 2026-10-23, operator: "Execute G4"
```

`.pm/policy.toml` is **pinned and class K**; after the change the pins are
re-recorded with `pmk pins record`.

**Rollback, stated before the change:** revert the line to `dry-run` and
`pmk pins record` again; nothing outside `.pm/` changes.

**Verification, before the change is left in place:**

| # | Criterion | Pass looks like |
|---|---|---|
| **V1** | The diff is the pre-written one | `git diff .pm/policy.toml` shows exactly the one-line change above |
| **V2** | The sync runs live and records it | `pmk context sync` records a `CONTEXT_SYNC` event with `dry_run: false` |
| **V3** | The lint still gates | I15 lint findings force review/exactly as in dry-run (no silent accept) |
| **V4** | It reverts cleanly | mode back to `dry-run`, `pmk pins record`, sentinel clean, repo unchanged |
