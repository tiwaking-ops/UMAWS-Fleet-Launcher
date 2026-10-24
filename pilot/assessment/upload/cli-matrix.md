# S-A1 — the CLI matrix

**Date:** 2026-10-23 · **Run:** live, with the operator's approval
(decision D-24) · **Scripts:** `pilot/spikes/s1_live.py`,
`pilot/spikes/s1_live_resume.py` · **Raw:**
`pilot/spikes/s1-live-results.json`, `pilot/spikes/s1-live-resume.json`,
`pilot/spikes/s1-live-help/`

**Terms of the approval (D-24).**  A throwaway repository per CLI; the
prompt *"print the word ok and exit"*; three modes per CLI (new, resume
same model, resume different model); and if a profile was **already**
rate-limited, **one** request to capture a QUOTA fixture — no other failure
was provoked.

**Requests used: 13** (five "new", seven resume, one authorised QUOTA
capture).  No failure was deliberately induced.

---

## The matrix

| CLI | version | headless | session id | resume (same) | resume (diff model) | classifier |
|---|---|---|---|---|---|---|
| **hermes** | 0.22.2 | **yes** (exit 0, 40.6 s) | **yes** — `20261022_235546_f8f570`, printed as *"Resume this session with: `hermes --resume <id>`"* | **yes** (exit 0, 60.6 s) | **not tested** | — |
| **kilo** | 7.8.15 | **yes** (exit 0, 75.7 s) | no — `--continue` needs none | **yes** (exit 0, 86.9 s) | **not tested** | — |
| **pi** | 1.2.0 | **yes** (exit 0, 10.9 s) | no — `--continue` needs none | **yes** (exit 0, 7.2 s) | **yes (exit 0, 10.6 s)** | — |
| **cline** | 3.0.73 | **yes** (clean error, 17.6 s) | — needs `--id` | **not tested** — no session obtained | **not tested** | **MODEL_GONE** |
| **opencode** | 2.1.0 | **yes** (rate limit, 96.4 s) | no — `--continue` needs none | **failed** (exit 1 — still rate limited) | **not tested** | **QUOTA** |

**"not tested"** means *no second model string is known for that tool*.
Inventing one would be a guess, not a measurement, so the probe was skipped
and recorded.  This is the honest state, and it has a concrete consequence
below.

## The syntax, copied from each CLI's own `--help`

| CLI | Resume | Model override |
|---|---|---|
| hermes | `--resume, -r SESSION` | `-m, --model MODEL`, `--provider PROVIDER` |
| kilo | `-c, --continue`, `-s, --session` | `-m, --model` (`provider/model`) |
| pi | `--continue, -c`, `--resume, -r`, `--session <path\|id>` | `--model <pattern>`, `--provider <name>` |
| cline | `--id <session-id>` | `-m, --model <model-id>`, `-P, --provider <id>` |
| opencode | `--continue, -c`, `--session, -s string` | **none in `--help`** |

> **A correction to my own first pass.**  The first version of the spike
> found the resume flags with a regex, and it produced three false
> positives: `--pass-session-id` (hermes), `--no-session` (pi) and
> `--list-models` (pi).  The first hermes resume attempt used the wrong
> flag and exited 2.  The flags above are copied from the captured help
> output, and the spike now matches them explicitly.

## What changed in the code

Before the live spike, every real adapter's capabilities were `False` and
the consequences were severe:

* the Fleet opened a **console window per worker** and marked the profile
  `degraded` — unusable at 100 slots;
* the recovery ladder could **never** take its **L1** step (resume the
  session on a different model), so FR3's headline behaviour was
  unreachable;
* **no adapter had a single classifier pattern**, so every non-zero exit
  was `UNKNOWN` and every failure cooled the profile at random.

Now (`src/fleet/adapters/generic.py`):

```
hermes    headless=True resume=True swap=False sessionid=True
kilo      headless=True resume=True swap=False sessionid=False
pi        headless=True resume=True swap=True  sessionid=False
cline     headless=True resume=False swap=False sessionid=False
opencode  headless=True resume=True  swap=False sessionid=False
```

**A pattern must match the capture it comes from.**  The loader reads
`patterns.toml` beside the evidence and **refuses to load a pattern that
does not match its source file**, which is the mechanical form of fleet
rule 15 (*"a classifier pattern may only be added from a captured
fixture"*).  A pattern with no evidence behind it cannot exist.

## The two real failures, captured

### cline — MODEL_GONE

```
error: Free model promotion ended
The free promotion for this model has ended and it is no longer available.
Select another model to continue.
Open the model selector with /model.
```

**The operator's `cline-mimo` profile is broken**: its model
`cline-free/mimo-v2.6-flash` no longer has a free promotion.  The Fleet's
`MODEL_GONE` handler disables the profile when it sees this.  Repointing it
is the operator's call, because the profile schema is class K.

### opencode — QUOTA

```
> build · recursive/flint-v1.0:free        (eleven times)
Error: Rate limit exceeded: free-models-pe...
```

The authorised single request captured this.  The opencode profile was
**already rate limited** at the time of the probe, which is why its resume
also failed with exit 1.

## The finding that matters most for the Fleet

**"Resume on a different model" needs a per-profile list of interchangeable
models, and only `pi` has one.**

The L1 step — resume the session on a *different* model — is what FR3 asks
for, and it needs two things: a resume command (four of five CLIs have one)
and a **second model string the tool can actually serve** (only `pi` does).
`agents.toml` now carries a `models` list per profile, and the ladder's L1
step picks the next one.  For hermes, kilo, cline and opencode the list has
one entry, so L1 is unavailable and the ladder correctly falls to L2 (a
fresh session with a handoff note).

**This is a configuration requirement, not a code gap** — and the operator
can fill it in from their own `prompts.json`, which already lists several
models per tool.

## Still UNVERIFIED

* **The failure text of hermes, kilo and pi.**  No failure occurred
  naturally, and the operator's terms forbid provoking one, so those three
  adapters still have **no** classifier patterns and classify every
  non-zero exit as `UNKNOWN`.
* **The exit codes.**  Only 0 and 1 were observed (plus cline's 1 and
  opencode's 1).  Nothing distinguishes a crash from a refusal.
* **A headless run under the harness** — every probe here ran the CLI
  directly.  The Fleet's own path (worktree, order file, lease, oracles) is
  exercised by the fake CLI, and by the demo, but not yet with a real CLI
  end to end.  That is the G3 handover test.
