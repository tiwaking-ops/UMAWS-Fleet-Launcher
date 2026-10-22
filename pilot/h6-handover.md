# H6 — the handover test (G3's remaining condition)

**Status:** criteria written **before** the run, as the amendment requires
(`pilot/amendment-gates.md` §2). Authorised by the operator on 2026-10-23
("1. APPROVED") — G3 is an **authorisation** action, not a checkpoint, so it
did not need pre-written criteria to be taken; they are written down so the
result cannot be read into the run afterwards.

**Author:** OpenCode. **Date:** 2026-10-23.

## The hypothesis

**H6:** *a fresh session can continue from a Kernel briefing alone.*

The briefing is already deterministic from the log alone — that part is
tested (`pmk brief` is a pure projection). What has **not** been run is the
end-to-end handover: an agent that has no memory of the previous session,
given only the briefing, arrives at the same next action.

## Method

A **separate Kernel root** outside the repository, so the live log is not
polluted and the test is reversible by deleting a directory:

```
C:\Users\Tiwa Pene\AppData\Local\Temp\opencode\h6-scratch
```

Seeded with a known state — one READY task and one incident — so that the
correct answer is not "there is nothing to do", which would pass trivially:

| Fact | Value |
|---|---|
| project state | `NEW` |
| tasks | 1 |
| ready to dispatch | 1 |
| the next action | `T-0001` — *H6-ALPHA: create greeting.txt containing the word hello* |
| incidents | 1 |

Two **fresh processes**, run one after the other, each given only
`briefing.txt` and told to modify nothing. "Killing the session" is
represented by the process ending: nothing is carried between run A and run
B except the file on disk.

## Pass criteria

| # | Criterion | Pass looks like |
|---|---|---|
| **P1** | Identifies the next action | names **`T-0001`**, or the exact title *H6-ALPHA: create greeting.txt containing the word hello* |
| **P2** | States the project state and task counts | project state `NEW`; **1** task ready to dispatch |
| **P3** | Reports the incident count truthfully | exactly **1** incident; none invented |
| **P4** | Invents nothing | no task id other than `T-0001`; no claim about work that is not in the briefing |
| **P5** | Agreement across fresh sessions | run A and run B name the **same** next action |

**The test fails if any of P1–P5 fails in either run.**

**The test is NOT RUN** (neither pass nor fail) if a run fails for
infrastructure reasons — a provider rate limit, a missing credential, a
timeout. A quota error is evidence about the provider, not about the
handover, and must not be scored as a failure of the mechanism. Any such
outcome is recorded in `pilot/spikes/h6/` with the raw output.

## What this does *not* test

A real CLI **taking work** through a real lease, in a real worktree. That is
the other half of G3, and the one-click demo exercises it with the **fake**
CLI (`tests/fleet/fakecli.py`), not a real one. Passing H6 does not close
that half, and this document does not claim it does.

## Results

Raw captures: `pilot/spikes/h6/` — `briefing-live-repo.txt`,
`briefing-seed2.txt`, `pair1-run-*.txt`, `pair2-run-*.txt`.

### H6 as specified (OpenCode): **NOT RUN**

Opencode exited **1** after 88 s with:

```
Error: Rate limit exceeded: free-models-per-day. Add 10 credits to unlock
1000 free model requests per day
```

The same failure as spike S-A1 (2026-10-22). Under the criteria above this is
**NOT RUN**, not a failure: it is evidence about a provider's free tier, not
about the handover mechanism. It is also the **second** time this CLI has been
unavailable on its free tier, which is worth recording on its own.

The invocation was **not** at fault, and that was checked rather than assumed:
`opencode v2.1.3`, `opencode run [flags] [<message...>]`, so the argv used
(`opencode run "<prompt>"`) is valid. The capture shows the CLI actually
running — `> build · recursive/flint-v1.0:free` ten times — before the refusal.
The `opencode.ps1 … NativeCommandError` banner above it is npm's `.ps1` shim
writing to stderr, not a failure of the run.

**Evidence-chain correction.** The first opencode capture was written into the
scratch root and **deleted with it**, before being copied out — a real slip in
this pass: the kilo captures were preserved and that one was not. It was
regenerated afterwards into `pilot/spikes/h6/opencode-attempt.raw.txt` with the
same argv shape and the same result. The original is gone; this document does
not pretend otherwise, and the identical failure text from the earlier run is
independently preserved in `tests/fleet/fixtures/opencode/quota.txt` (spike
S-A1, 2026-10-22).

### Variant V1 — the same mechanism on **kilo**: **PASS**

Because the gate's *mechanism* is "a fresh session continues from the briefing
alone", the test was re-run on a CLI whose quota was not spent. Four fresh
processes, two seeds.

**Pair 1 — a PROPOSED task, i.e. no dispatchable work.** Expected: state
`NEW`, 0 ready, `T-0001` PROPOSED, 1 incident.

| Run | 1 state | 2 ready | 3 next action | 4 incidents |
|---|---|---|---|---|
| A | NEW ✓ | 0 ✓ | "no single next action… the only task T-0001 is **PROPOSED**" ✓ | 1 ✓ |
| B | NEW ✓ | 0 ✓ | "N/A — no ready tasks; the first PROPOSED task is T-0001…" ✓ | 1 ✓ |

**Pair 2 — one genuinely READY task.** Expected: state `NEW`, 1 ready,
**`T-0002`**, 1 incident — written down before the runs.

| Run | 1 state | 2 ready | 3 next action | 4 incidents |
|---|---|---|---|---|
| C | NEW ✓ | 1 ✓ | `T-0002` — H6-BETA: write hello.txt containing hello world ✓ | 1 ✓ |
| D | NEW ✓ | 1 ✓ | `T-0002` — H6-BETA: write hello.txt containing hello world ✓ | 1 ✓ |

**P1–P5 pass. All four sessions agree.** The two sessions in each pair are
independent processes with nothing carried between them but a file on disk.

### The criteria were wrong, and that is the point

Pair 1 was seeded with `pmk task create`, and I wrote the ground truth as
"1 ready, next action `T-0001`". **That was wrong.** A task needs a
`goal_ref` to be admitted, so `T-0001` was `PROPOSED` and the briefing
correctly reported `Ready to dispatch: 0`. Both runs read the briefing
correctly; **the expectation was the error, not the agent.**

This is recorded rather than quietly amended. Writing the criteria down
before the run is what made the error visible: had the expectation stayed in
my head, a *correct* answer would have looked like a failure — or, worse, a
wrong one could have been read as a pass. Pair 2 exists because the error was
caught, and it is the stronger test, because distinguishing "a task exists"
from "a task is ready" is exactly where a shallow reader fails.

### Verdict, and what it does not close

The **mechanism** is demonstrated: a fresh session reaches the same next
action from the briefing alone, four times, on two different seeds.

**G3 is not closed by this**, on two counts:

1. **The named CLI was not exercised.** The gate says *an OpenCode session*.
   A kilo run tests the mechanism, not that OpenCode works. Whether a variant
   satisfies the gate's wording is the **operator's** call, not mine — it is
   their gate.
2. **The other half of G3 is untouched.** A real CLI **taking work through a
   real lease**, in a real worktree, with oracles. The one-click demo runs
   that path with `tests/fleet/fakecli.py`, not with a real CLI.

Neither of those is claimed here.
