# UMAWS Fleet

A Kernel-lite coordination system with a Fleet Dispatcher that runs CLI
agents unattended, and a browser Console to watch it.

Built from `docs/sources/pilot-proposal.md` (pilot P-01) as amended by
`docs/sources/fleet-launcher-proposal.md` (amendment A1).

```
Operator ── browser ──► Console (FastAPI, 127.0.0.1 only)
                          │
                          ▼
                    umaws app process
                      Conductor   lifecycle, wakes the Overseer
                      Dispatcher  selects a profile, claims a task
                      Adapters    hermes | kilo | cline | pi | opencode | fake
                      Harness     worktree, order file, oracles, evidence
                      pmk.api     the Kernel: the only writer of state
```

## Quick start

```powershell
# 1. the environment (once)
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe -m pip install fastapi uvicorn httpx tzdata pytest

# 2. the Console — double-click start.cmd, or:
.\start.ps1
```

The Console opens on <http://127.0.0.1:8765> with seven tabs: Projects,
Fleet, Tasks, Queue, Overseer, Manual launcher, Metrics.

## The command line

```powershell
pmk init                              # create the layout, the first event, the pins
pmk status                            # one-screen status
pmk task create "title" --goal-ref G-001 --write src/x.py --oracle "pytest -q"
pmk brief --role overseer             # the briefing, from the log alone
pmk sentinel                          # check the invariants
pmk fleet status                      # profiles, slots, cap, dispatch state
pmk agent list                        # the running workers
pmk project init --brief "..."        # start a project
pmk project run --seconds 60         # run the Conductor and the Dispatcher
pmk pdd lint docs/PDD.md
```

## Layout

| Path | What |
|---|---|
| `src/pmk/` | the Kernel: events, tasks, leases, views, briefing, sentinel, the API and the CLI. **Standard library only.** |
| `src/fleet/` | profiles, adapters, selection, the harness, the recovery ladder, the Dispatcher, the Conductor, the merge queue, the Overseer runner, the project lifecycle, the manual-launcher port |
| `src/console/` | the FastAPI Console and its one HTML page |
| `gateway/quotagate/` | the hierarchical quota engine (QuotaGate M0–M2 core) |
| `tests/` | 150 tests: Kernel, Fleet, QuotaGate |
| `tests/fleet/fakecli.py` | the scriptable fake CLI every Fleet test runs against |
| `pilot/` | STATE.md (the memory), decisions.md, the daily and interrupt logs, the spikes, the **pilot report** |
| `.pm/` | the coordination state: the event log, the views, the task cards, the evidence, the pinned constitution and policy |

## The rules that matter

1. **The Kernel is the only writer.**  Agents request transitions through
   `pmk`; nothing edits `.pm/`.
2. **Oracles decide.**  A worker's claim that its tests pass is not
   evidence.  The harness runs the acceptance commands and records the
   exit codes.
3. **Argv, not shell strings.**  Every managed launch is an argv list.
4. **Only kill what you spawned**, verified by pid *and* process creation
   time.
5. **Fake first.**  Every Fleet behaviour is tested on the fake CLI before
   any real CLI or real quota is used.
6. **No quota hammering.**  Never retry a failing profile without a
   backoff and a cooldown rule.

## Reading the pilot's own record

* `pilot/pilot-report.md` — what was built, what was measured, what is
  still `UNVERIFIED`, and what failed.
* `pilot/STATE.md` — the current state and the next steps.
* `pilot/decisions.md` — every decision, its alternatives, and what it
  leaves untested.
* `pilot/spikes/` — the raw measurements behind the platform decisions.

## Running the demonstration

```powershell
.\.venv\Scripts\python.exe pilot\demo_one_click.py
```

Runs the whole lifecycle — brief, PDD, task cards, claim, worktree, order
file, spawn, oracles, evidence bundle, merge queue, close-check — against
the fake CLI, in a scratch repository.  It finishes `DONE` with a clean
sentinel and a verifying chain.
