---
document:
  title: "Response to Assessment v3: Live-Hazard Containment, Appendix A Results, and Answers to D-1 to D-6"
  type: "Verification report and decision response"
  status: "Advisory; no authority. Records one state-changing action already taken (project pause)."
  version: "1.0.0"
provenance:
  author_llm: {name: "DeepSeek", version: "DeepSeek V4.1 Flash Free (via opencode)"}
  assessed_document: "assessment-claude-umaws-fleet-worktree-isolation-v3.md (v3.0.0, Claude Sonnet 5.5, 2026-11-02)"
  supersedes: "verification-assessment-v2-command-results-v1.md (v1.0.0), for the readings corrected in section 5"
  created_date: "2026-11-02"
  last_modified_date: "2026-11-02"
audience:
  primary: "The human operator (decision record)"
  secondary: "Claude (Web), Claude Code, and the next reviewer session"
evidence_basis: "Every command in Appendix A was executed against the live repository and the live Console. The four check_stall probes in section 3 call the real Conductor.check_stall() with a stubbed dispatcher and a deep-copied state object; nothing was written. Event log snapshot taken at C:\\temp\\events-snapshot-20261102 before any further repair. I have not seen the two patch files' review, since that is Claude (Web)'s task."
---

# Response to Assessment v3

## 1. Headline

v3 is correct on its three new claims, and correct about the ranking. One of its
predictions had a clock on it that the report did not know about, and that clock
had already run down by the time the report was read.

**The live Console's Conductor would have fired a false `STALLED` at
05:06:17Z against a task in `DONE`.** The project was paused at 05:05:08Z
(seq 2992), 69 seconds ahead of that boundary. The boundary has since passed
with no event, and T-0139 is still `DONE`, fence 117, attempt 2.

The pause is a fence, not a fix. Its only load-bearing property is that
`check_stall()` returns `""` when `project_state` is `PAUSED`. That property
breaks the instant anyone resumes. Section 6.7 lists the two commands that
would break it.

**The finding v3 missed is larger than the one it made.** The stale lease on a
`DONE` task is not a T-0139 accident. `state.leases` is only ever popped on
`REVOKED` (`src/pmk/state.py:166`); `SUBMITTED`, `VERIFIED`, `INTEGRATING`,
`INTEGRATED` and `QUARANTINED` annotate the lease and leave it in place. A task
that succeeds on its first attempt keeps its lease permanently, and
`check_stall()` iterates the full lease dict rather than `active_leases()`.
Every clean first-attempt success therefore arms a false `STALLED` at
`granted_at + ttl`. T-0139 is simply the first task in this log to reach `DONE`
without an intervening revoke, so it is the first to be exposed.

## 2. Appendix A, item by item

| # | Command | Result | v3 verdict |
|---|---|---|---|
| 1 | process census | Console alive: pids 4160 (`.venv` wrapper) and 5864 (child), `python -m console.app --port 8765`. **No dispatcher process, no `dispatch run` process.** | confirmed: nothing is spawning |
| 2 | pause | `POST /api/project/pause` → `{"ok": true, "state": "PAUSED"}`, seq 2992 `PROJECT_STATE` `05:05:08Z` | done, ahead of the deadline |
| 3 | blob ids | pin `75a037f:CNA-Rules.adoc` = `e4936918…`; pi f110 worktree = `e4936918…`; **T-0139 branch = `16615112…`; main working tree = `16615112…`** | off-pin **confirmed** |
| 4 | T-0145/T-0146 worktrees | none exist | consistent with `PROPOSED` |
| 5 | `2a0f6fa` ancestor of HEAD | `git merge-base --is-ancestor` exit 1 | not merged, **confirmed** |
| 6 | event-log snapshot | `C:\temp\events-snapshot-20261102`, 12 files including `2026-10-31.jsonl.bak` | done |
| 7 | code-only patch | `C:\temp\code-77a56db-aed9aec.patch`, 13,921 bytes | written, awaiting Claude's read |

Item 3 also closes an argument: main's untracked working-tree copy hashes
`16615112…`, **the same byte stream as the T-0139 branch**. "Merge the branch"
and "copy main's files" are not two wrong options; they are the same wrong
bytes. Neither may land.

Two patches are ready for review, as requested:

- `C:\temp\code-77a56db-aed9aec.patch` — `src` and `tests` only, 13,921 bytes, written with `git diff --output=` so PowerShell never touches the encoding.
- `C:\temp\uncommitted.patch` — the dirty tree, 49,608 bytes.

## 3. What the pause actually prevented

Four probes against the real `Conductor.check_stall()`, with a stubbed
dispatcher (no profiles) and a deep copy of the live state. Nothing was
written.

| Probe | State fed to `check_stall()` | Return |
|---|---|---|
| A | the log as it stands (`PAUSED`, three leases) | `''` |
| B | the same state with `project_state` set to `RUNNING` | **`'lease T-0139 expired (TTL 120 min) without submission'`** |
| C | `RUNNING`, T-0139's lease removed, T-0141/T-0142 kept | `''` |
| D | `RUNNING`, all three leases removed | `''` |

Probe B is the incident that did not happen. A `STALLED` transition would have
been written against `DONE` fence 117, queued a topic, and woken the overseer —
on a two-second loop, so it would have repeated. Probe C shows why the two dead
agents did not trip it earlier: their leases are 94.8 and 94.7 minutes old
against a 120-minute TTL, so they expire at `05:32:29Z` and `05:32:30Z`. Probe
C also shows the ordering hazard: T-0139 is the *first* expired lease in
dict order only by coincidence; the check returns on the first hit, so the
reported reason is whichever task sorts first, not the most serious one.

Lease ages at the time of measurement:

```
T-0139  state DONE    granted 2026-11-02T03:06:17Z  age 121.0 min  TTL 120  EXPIRED
T-0141  state LEASED  granted 2026-11-02T03:32:29Z  age  94.8 min  TTL 120  expires 05:32:29Z
T-0142  state LEASED  granted 2026-11-02T03:32:30Z  age  94.7 min  TTL 120  expires 05:32:30Z
```

## 4. New finding: leases are never released when work ends

Code:

- `src/pmk/api.py` `revoke()` writes `REVOKED`; that is the only event that pops a lease.
- `src/pmk/state.py:142` — `CLAIMED` overwrites the lease entry. It never removes one.
- `src/pmk/state.py:168-198` — `SUBMITTED`, `VERIFIED`, `INTEGRATING`, `INTEGRATED` and `QUARANTINED` only annotate `pid`, `session`, `last_failure_class`. **`INTEGRATED` sets `DONE` and leaves the lease.**
- `src/pmk/state.py:166` — `REVOKED` is the sole `leases.pop`.
- `src/fleet/conductor.py` `check_stall()` — `for task_id, lease in state.leases.items()`, not `active_leases()`.

Evidence across all six `DONE` tasks:

| Task | Last events | Retains lease? |
|---|---|---|
| T-0118 | `INTEGRATED` 2716 → **`REVOKED` 2731** → `INTEGRATED` 2732 | no |
| T-0119 | `INTEGRATED` 2681 → **`REVOKED` 2691** → `INTEGRATED` 2692 | no |
| T-0127 | `INTEGRATED` 2599 → **`REVOKED` 2684** → `INTEGRATED` 2689 | no |
| T-0129 | `INTEGRATED` 2604 → **`REVOKED` 2686** → `INTEGRATED` 2690 | no |
| T-0130 | `INTEGRATED` 2675 → **`REVOKED` 2693** → `INTEGRATED` 2694 | no |
| **T-0139** | `INTEGRATED` 2970, no revoke after | **yes** |

Five of six `DONE` tasks are lease-free only because they were revoked *after*
they had already integrated, and then re-integrated at a higher fence. That
sweep is itself the T-0003 defect — a revoke on a `DONE` task returning it to
`READY` — running in bulk at seq 2677–2695. T-0139 is the first task to reach
`DONE` without that repair, and it is therefore the first to be caught by the
stale lease.

Consequence, stated plainly: **the instrument that would detect a dead agent is
the same instrument that fires on a task that finished successfully.** Until
leases are released at terminal transitions, any resume of this project is a
coin-flip between "correctly detects the two dead agents" and "declares the
project stalled because a task succeeded".

## 5. Corrections conceded

I accept these without argument, all of which overturn something I wrote in v2:

1. The `--in` reading was selective. The help text does change into DIR.
2. Lack of supervision, not the heartbeat bug, explains the lost pi f110 result.
3. "No two-key events" was overstated. Q-059 exists, retroactively, and
   `pilot/class-k-ratification.md` already records the same
   "key applied after the fact is an audit, not a gate" weakness for Q-001/Q-002.
4. CRLF is a provenance defect, not an emergency. It does not justify urgency;
   it justifies the binary-safe derivation in D-2.
5. I missed that T-0145 and T-0146 also start on a corpus-less base.
6. My own retraction: the Console's Conductor ticks every **2 s**
   (`_conductor_loop` → `self._stop.wait(2.0)`), not 5 s. The dispatch loop is
   1 s. The expiry lag v3 attributes to the tick is therefore 0–2 s, not 0–5 s.

## 6. Decisions

### 6.1 D-1 — tagged actors

**Yes, but it is labelling, not a gate.** Adopt `PMK_ACTOR=agent:<tool>` for
every assistant launch, and keep a dedicated plain shell with
`PMK_ACTOR=operator` for `void`, `queue decide`, and project state changes.
That much is cheap and makes the log legible.

The limit has to be stated at the same time: the actor field is self-asserted.
Any writer can export a different value, and interactive assistants inherit your
shell. This is the Q-001/Q-002 weakness again in a new place — a key applied by
convention survives only while everyone honours it. If you want a real gate, the
kernel has to refuse rather than label: reject `TASK_VOIDED`, `QUEUE_DECIDED` and
`PROJECT_STATE` when `actor.kind != "human"`, with an explicit override flag.
That is a code change and belongs in the same reviewed round as section 7,
not in a shell convention.

### 6.2 D-2 — derive the corpus binary-safely

**Agreed, with two additions.**

- `git show > file` in PowerShell is the failure mode that produced the CRLF
  copy. Use `git cat-file blob <oid> >` only with `$OutputEncoding` and
  `[Console]::OutputEncoding` pinned to UTF-8 with no BOM, or — better, and
  the way I would do it — materialise through `git worktree add` /
  `git checkout-index --prefix` at `75a037f`, which never round-trips through a
  shell stream. Then verify with `git hash-object --no-filters` against
  `e4936918…` for `CNA-Rules.adoc` and against the full 66-file manifest.
- A `.gitattributes` rule is itself a governance change. It does not retro-fix
  the bytes already in `aed9aec` or in the T-0139 branch, and it will silently
  mask future damage if it is added without a `text=auto` / `*.adoc
  text eol=lf` decision recorded. Bundle it with the corpus commit and one
  decision id.

Sequencing constraint: the corpus must land **before** any resume. D-4's four
tasks and the whole `docs/rules/` tree depend on it, and R-09 refuses leases
while main is dirty.

### 6.3 D-3 — **pushback on option (i) as framed**

Option (i) is "revert the TTL to 20 minutes and make heartbeats count". As
stated, it cannot work, for a reason that is visible in this ledger:

**The renewer lives inside the process that dies.** `src/fleet/harness.py:349`
calls `self.kernel.renew(...)` from `Harness.poll()`, in the harness process,
every `renew_every = 60 s`. When the harness dies the renewals stop. That is
exactly what the log shows: 19 `RENEWED` events in the entire history, the last
at fence 96, and all three current leases with `renewed_at == granted_at`.
Honouring `renewed_at` would therefore change nothing for the failure mode that
actually occurred — a dead agent cannot send its own heartbeat, so the timestamp
it would have refreshed is the one already frozen.

Second, with the arithmetic as it stands (`check_stall()` reads `granted_at`
only, and ignores `expires_at`), dropping the TTL to 20 minutes converts a
late-detection bug into a guaranteed false positive: T-0139 would have tripped
at 03:26:17Z, forty minutes into a legitimate run, and every run longer than
20 minutes would do the same.

**Three defects, and the TTL is not one of them:**

1. `check_stall()` iterates `state.leases` instead of `state.active_leases()`.
   A `DONE` task cannot stall a project. One-line fix, no policy change.
2. Leases are released only on `REVOKED`. Terminal transitions must drop them —
   on `INTEGRATED`, on `PREMISE_REFUTED`, and on `TASK_VOIDED`. One-line fix
   per handler, no policy change.
3. The heartbeat has no supervisor. Renewal must be emitted by the component
   that survives the agent — the dispatcher, on behalf of a live slot — so that
   a frozen `renewed_at` means what the TTL assumes it means.

**Recommendation:** one commit, one decision id, in this order: fix 1, fix 2,
add supervisor-side renewal, *then* set the TTL. Once 1 and 2 are fixed and
renewal is emitted by a survivor, the TTL value is a free choice and I would take
20 minutes, because with a real heartbeat the TTL stops meaning "took too long"
and starts meaning "made no progress". Reverting to 20 minutes *before* those
three fixes is the one option I would refuse.

R-09's leak belongs in the same commit: `start()` claims, creates the worktree
and writes the order before R-09 can refuse at `src/fleet/harness.py:292`, and
returns without `_give_up()`. The lease it took is never released — a fourth
path into defect 2.

### 6.4 D-4 — hold the four tasks

**Agreed, all four.** Two things to add.

- Holding is not only prudent, it is enforced: R-09 will refuse T-0141 and
  T-0145 on `M docs/rules/index.json`, and T-0142 and T-0146 on
  `M coverage/rules_coverage.json`, for as long as main is dirty. The corpus
  commit is the unblock for all four.
- Two of the four need work beyond the corpus. T-0141/T-0142's oracles carry
  nested double quotes and die in `cmd.exe` with a `NameError` before they test
  anything; T-0145/T-0146's single-quote oracles are correct. Landing the corpus
  fixes the base, not the T-0141/T-0142 oracle.

### 6.5 D-5 — keep the incident open

**Agreed.** Do not close it until all of the following are true, and record them
as the closure criteria so the bar does not drift:

1. The corpus is in main HEAD, derived binary-safely, and
   `git hash-object --no-filters` matches `e4936918…` on a fresh checkout.
2. Leases are released at terminal transitions, and `check_stall()` reads
   `active_leases()`.
3. R-09 releases the lease it claimed on its own failure path.
4. One supervised run completes end to end with `AGENT_EXITED` recorded.
5. The I1 hand-repair at seq 2280 has a repair event, or the absence is recorded
   as permanent debt. The chain currently verifies, but it was repaired without
   an event and three `SENTINEL_RUN` events were deleted without a tombstone per
   `EVENT_LOG_VIOLATION_REPORT.md`. A ledger that verifies after a silent repair
   is a verified file, not a verified history.

### 6.6 D-6 — handoff v5

**Yes, and write it now rather than after the fixes.** A stale handoff is
actively dangerous here, because the next agent to read it may act on it, and
every action it would suggest is now behind a pause. v5's first section should
be: *the project is `PAUSED`, seq 2992, for a reason; do not resume until
section X is satisfied.* Then the fences, the three leases, the corpus pin and
the off-pin hash, and the resume preconditions below. Waiting until the fixes
land means the document that describes the danger is written after the danger.

### 6.7 Resume preconditions

The pause holds because `check_stall()` early-returns on `PAUSED`. Two commands
break it:

- `POST /api/project/resume` on the live Console
- `pmk project resume`

On either, the live Console's Conductor fires within two seconds and writes
`STALLED` against T-0139, a `DONE` task (probe B). A Console *restart* is safe —
`PAUSED` is durable in the event log, and `start_loops()` running unconditionally
at `src/console/app.py:465` only restarts the loops; it does not change project
state. So containment is exactly one condition: **do not resume.**

Resume only when:

1. T-0139's lease and the T-0141/T-0142 leases are removed, or the fixes in 6.3
   are in the tree so that `DONE` cannot trip the check. Note that T-0141 and
   T-0142 cross their own TTL at `05:32:29Z` and `05:32:30Z`, so after that
   point removing only T-0139's lease is not enough.
2. The corpus has landed and main is clean, so R-09 will not refuse.
3. `dispatch_paused` is understood to be in-memory only: on disk,
   `.pm/fleet/fleet-state.json` says `dispatch_paused: false`, so a fresh
   `pmk dispatch run` starts unpaused regardless of what the Console believes.

One reassurance, checked rather than assumed: `/api/project/pause` calls
`set_state()` only and does **not** set `fleet_state.paused_at`. The
`DISPATCH_PAUSE_LIMIT_S = 1800` branch in `check_stall()` is guarded by
`dispatch_paused and paused_at`, and `paused_at` is still `0.0`. There is no
30-minute resume trap waiting on the other side of this pause.

## 7. Suggested order of work

Unchanged in substance from v3, with the containment step made explicit and the
D-3 items reordered so the policy change comes last:

1. **Hold.** No resume. No `pmk revoke` on T-0139. No merge of `pmk/T-0139-117`.
2. **Review round** on the two patches — Claude (Web)'s turn.
3. **One commit, one decision id:** `check_stall()` → `active_leases()`; lease
   release on `INTEGRATED` / `TASK_VOIDED` / `PREMISE_REFUTED`; R-09 before
   `claim`; `integrate` requiring a reachable commit; supervisor-side renewal;
   oracle lint for nested double quotes; then the TTL decision.
4. **Corpus** derived binary-safely from `75a037f`, `.gitattributes`, one
   decision id, verified against the pin.
5. **Clear the three stale leases** through the fixed code, not by hand and not
   by `revoke`.
6. **Resume**, then the four held tasks, then supervised runs.
7. **Handoff v5** — actually step 0, since it is a warning, not a summary.

Steps 3 and 4 are independent and can be reviewed in parallel. Neither may be
applied to the live ledger until the pause is lifted, and the pause may not be
lifted until step 5.
