# G3 — the OpenCode half: RESULT

**Date:** 2026-10-23, 19:5x–20:0x local · **Authorised:** operator, 2026-10-23
("Execute G3 if possible") · **Author:** OpenCode.

**Script:** `pilot/g3-opencode-handover.py` · **Captures:**
`pilot/spikes/h6/g3-briefing.txt`, `g3-opencode-run-a.txt`,
`g3-opencode-run-b.txt`.

## What ran

The H6 protocol (`pilot/h6-handover.md`) on the **named CLI** — a scratch
Kernel root, seeded with T-0001 PROPOSED, T-0002 READY (goal `h6`) and one
planted incident, briefed from the log alone, then two **fresh opencode
processes** given only `briefing.txt` and told to modify nothing.

| Run | exit | wall | model seen |
|---|---|---|---|
| A | 0 | 74.2 s | `flint-40b-free` |
| B | 0 | 35.0 s | `flint-40b-free` / `recursive/flint-v1.0:free` |

## Scoring — P1–P5

| # | Criterion | A | B |
|---|---|---|---|
| P1 | names T-0002 / the exact title | ✓ | ✓ |
| P2 | state NEW, 1 ready | ✓ | ✓ |
| P3 | 1 incident | ✓ | ✓ |
| P4 | invents nothing | ✓ | ✓ |
| P5 | fresh sessions agree | ✓ (both: **T-0002 — "H6-BETA: write hello.txt containing hello world"**) | |

**Verdict: PASS.** The condition G3 still owed since D-40 — *an OpenCode
session, restarting from the briefing alone* — is satisfied on the named CLI.
Both runs confirmed they modified no file and ran no `pmk`.

## The scorer was wrong first, and that is recorded

The first scoring pass returned **FAIL** on run A: P2/P3 read as wrong
(ready `0001`, incidents `6`). The capture showed P1–P4 all **correct** —
the agent wrote `1` on the answer line, and my regex was matching
`T-0001` and `2026` off the *explanation* text instead. This is the same
failure mode H6's pair 1 recorded in 2026-10-22 (**the criteria were the
error, not the agent**), and it is repaired the same way: the scorer now
matches the numbered answers only. Run A was re-scored from the preserved
capture: P1–P4 all true. No re-run was needed for that repair.

A second scorer defect is also recorded: in `--reuse` mode with `--runs 1`,
the in-script P5 compared B against itself (vacuous). The genuine P5 was
computed **across the two preserved captures** instead — both name the same
next action — and that is the value reported above.

## Provider note

The earlier NOT RUN (D-37, `free-models-per-day`) was a provider wall, not a
mechanism failure: the free tier had reset by the time of this attempt, and
both sessions ran clean on `flint-40b-free`. This makes two clean
consecutive days on which opencode's free tier refused, and one on which it
worked — the fleet's quota-cooldown path remains the right answer either way.

## What this does not close

The **real-CLI half of G3** — a real agent taking work through a real lease
in a real worktree — was closed by D-39 (kilo, T-0002, functional oracle,
merge green). The G5 run now in progress exercises that same path under
load; its result is separate evidence, not a G3 claim.
