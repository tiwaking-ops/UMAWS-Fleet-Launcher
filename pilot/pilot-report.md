# Pilot P-01 (with Fleet amendment A1) — pilot report

**Date:** 2026-10-22 · **Author:** OpenCode (implementing agent, Phase 1)
**Sources:** `docs/sources/pilot-proposal.md`, `docs/sources/fleet-launcher-proposal.md`,
`docs/sources/umaws.md`, `docs/sources/quotagate-v1-1.md`,
`docs/sources/caliber-integration.md`

> This report is graded on honesty, not on completeness.  A partial result
> with an accurate report is a successful pilot; a complete-looking result
> with unverified claims is not (pilot v1 section 1).  Section 1 says plainly
> what is **not** done.

---

## 1. Outcome and tier reached

**Tier reached: A (Foundation) with a working Fleet, not B or C.**

The pilot's own tier definitions assume a supervised week.  What was built
here is a **complete, working, tested vertical slice** of the system with
the Fleet — not the whole pilot.  Stated plainly:

### Built and tested

| Area | State | Evidence |
|---|---|---|
| Kernel-lite (pilot v1 §9) | **complete** | 150 tests; `pmk sentinel` clean on the live repository |
| Platform layer (`plat.py`) | **complete** | spike S-P1; measured, not assumed |
| Fleet Dispatcher, selection, harness, recovery ladder | **complete** | `tests/fleet/` — 41 tests |
| Fake CLI (fleet §12.E) | **complete** | `tests/fleet/fakecli.py` + synthetic fixtures |
| One-click project lifecycle (fleet §10) | **complete** | `pilot/demo_one_click.py` runs green end to end |
| Console (fleet §8) | **complete** | FastAPI on 127.0.0.1; 7 tabs; SSE live updates |
| Manual launcher port (fleet §8.3) | **complete** | the operator's `prompts.json` loads unchanged |
| Overseer runner (fleet §7.8) | **complete** (mechanism) | wakes are event-driven, debounced, bounded |
| Merge queue | **complete** | serial; the gate runs on the tree that becomes canonical |
| QuotaGate quota engine (M0–M2 core) | **complete** | Q1 (DST) and Q2 (account-wide) pass |
| QuotaGate M1 passthrough proxy, M3 failover, M5 Kernel contract | **not built** | see below |
| Caliber context sync (WP1, WP8) | **not built** | Caliber is not installed; see section 5 |
| Real-CLI adapters verified | **not done** | metadata-only probing was the operator's choice |
| Acceptance tests F1, F4, F7, F9, F14 | **not run** | they need real LLMs or 100 slots |

### The headline evidence

`pilot/demo_one_click.py` runs the whole lifecycle against the fake CLI and
finishes with **state `DONE`**, a clean sentinel, and a verifying chain:

```
[1] initialised the Kernel: I1 chain verifies (1 events)
[2] project created: state=PLANNING plan task=T-0001
[3] PDD written and committed
[4] decomposed into 2 task cards: T-0002, T-0003
    started T-0002 on fake-worker (pid 7816)
    started T-0003 on fake-worker (pid 6064)
    finished T-0002: submitted
    finished T-0003: submitted
[5] after dispatch: {'VOID': 1, 'SUBMITTED': 2}
    merged T-0002: ok=True (merged)
    merged T-0003: ok=True (merged)
[6] after the merge queue: {'VOID': 1, 'DONE': 2}
[7] close-check: ok=True
    G-001: pass    G-002: pass    gate: pass
[8] final state: DONE

evidence bundles written: 2
    EB-T-0002-1: commands=1 oracles=1 outputs=1 scope_ok=True constitution_hash=33c8b830d80f…
    EB-T-0003-2: commands=1 oracles=1 outputs=1 scope_ok=True constitution_hash=33c8b830d80f…

sentinel: ok=True  findings=[]
chain: I1 chain verifies (30 events)
```

This is **F1-shaped but not F1**.  F1 requires real LLMs and ≥ 3 different
profiles; the operator chose metadata-only probing, so no real provider was
ever called.  What the demo proves is that the *mechanism* works end to end
and that **the oracles decide**, not the worker's claim.

---

## 2. Hypotheses

| ID | Hypothesis | Result | Evidence | Confidence |
|---|---|---|---|---|
| H1 | A small Kernel removes the claim/state failure classes | **supported** | stale-fence submission is quarantined (test), duplicate IDs impossible (Kernel allocates), chain verifies after a torn tail (test) | high |
| H2 | Caliber context sync runs unattended without harmful output | **not tested** | Caliber is not installed on this machine | n/a |
| H3 | The quota-aware gateway sustains multi-model access | **partially** | the quota engine's scopes, windows and DST handling are tested; no live provider was ever called | low |
| H4 | Verifier independence is enforced | **supported in the Fleet** | D-L12 family exclusion is implemented and tested; the gateway's `exclude_families` refuses rather than falling back | medium (gateway side untested live) |
| H5 | Human load is manageable and measurable | **partially** | the interrupt log records 5 interactions; no daily routine has been sustained long enough to measure | low |
| H6 | A fresh Overseer session can continue from a Kernel briefing alone | **mechanism only** | `pmk brief --role overseer` is deterministic from the log alone (test); the *handover* test with a real OpenCode session was not run | medium |
| H7 | Bootstrap work can be imported without losing auditability | **not implemented** | `BOOTSTRAP_IMPORTED` exists as an event type; the import tool was not built | n/a |
| H8 | Automated recovery lets a project finish through agent exhaustion | **mechanism only** | the L0–L4 ladder and the profile penalties are tested; no real exhaustion was provoked | medium |
| H9 | Priority-then-utilisation selection keeps free-tier capacity used | **mechanism only** | selection is deterministic and tested; no real capacity was measured | medium |
| H10 | One-click run reaches done unattended | **partially** | the demo reaches `DONE` with the fake CLI; not with real LLMs | medium |
| H11 | The mechanism scales to 100 slots | **not tested** | the scale drill F7 was not run; `max_total_agents` is still 20 | n/a |
| H12 | A strong Overseer model plus Kernel briefings is enough | **not tested** | needs real LLMs | n/a |

---

## 3. Metrics

| Metric | Value |
|---|---|
| Tests | **150 passing** (`pytest -q`) |
| Code | `src/pmk` 3 773 · `src/fleet` 3 507 · `gateway/quotagate` 903 · `src/console` 375 lines |
| Tests | 1 823 lines across 12 files |
| Kernel size | 3 773 lines, **standard library only** (the pilot's rule) |
| Commits | 6, tagged `bootstrap/0` at the scaffold |
| Events in the pilot's own log | 3 (the pilot repository is not itself a Fleet project) |
| Interruptions | 5 (see section 6) |
| Live provider calls | **0** |
| Quota burned | **0** |
| Real-CLI invocations | `--help` and `--version` only |
| Defects found by the demo and fixed | **3** (section 4) |

---

## 4. What failed and why

### 4.1 The three defects the one-click demo found

These are the most valuable results in the pilot.  Each was a defect that
would have let the system **do the wrong thing quietly**, and each is now
pinned by a regression test in `tests/fleet/test_regressions.py`.

**Defect 1 — git collapsed an untracked directory.**
`git status --porcelain` reports a new directory as a single `dir/` entry
rather than listing the files inside it.  The scope check therefore saw an
empty change list, and the evidence bundle recorded **zero output files**.
A worker that created a new module in a new directory would have had its
entire work invisible to verification, and the Kernel would have promoted
work it never inspected.  Fixed with `--untracked-files=all`.

**Defect 2 — the merge queue staged the harness's own artefacts.**
`git add -A` staged `.pmwork/ORDER.md` and the agent's session file.  Two
leases then conflicted on the order file when their branches merged, and
out-of-scope work was committed rather than quarantined.  Fixed: the harness
stages **only the task's declared write scope**, and a scope violation is a
refusal to promote.

**Defect 3 — the merge moved the ref but not the working tree.**
`git update-ref refs/heads/main <commit>` moves the branch and leaves the
index and the working tree alone.  The merged files were never checked out,
so the close-check — which runs in the main tree — could not see them and a
finished project looked unfinished.  Fixed with `git merge --ff-only`, which
updates both and refuses rather than overwriting local changes.

### 4.2 Kernel-caused incidents

| Incident | Cause | Fix |
|---|---|---|
| The lock test hung for 120 s | The lock was taken on byte 0 of the file being appended to.  **Windows enforces byte-range locks against writes**, so an append to an empty file lands on the locked byte and fails with `PermissionError`. | The lock moved to a sidecar `<file>.lock`.  Recorded as decision D-04, because a later implementer would otherwise "simplify" it away. |
| The lock test reported a false negative twice | The *validator* assumed a fixed-width record id and then a regex that ignored `ljust()` padding.  The mechanism was already correct. | The spike now compares against an exactly-built set of expected records. |
| Every classifier pattern failed to match | **Windows PowerShell 5.1's `Set-Content -Encoding utf8` writes a UTF-8 BOM.**  The fixture was read as `\ufeffSYNTHETIC-FAILURE-QUOTA`, so the pattern matched only at the very start of a string. | `plat.read_text` reads with `utf-8-sig`.  Applied to every file a human might have written: policy, agents, fixtures, prompts.json. |
| The scope check silently reported "no changes" | See defect 1 above. | `--untracked-files=all`, plus the git exit code and stderr are now recorded in the bundle. |
| The sentinel passed a repository with no pins file | The I8' check only turned *mismatches* into findings, and a missing file has no mismatches. | A missing pins file is now an I8' breach. |
| The merge queue conflicted on the order file | See defect 2 above. | Only the declared scope is staged. |

### 4.3 Windows findings that shaped the design

| Finding | Consequence |
|---|---|
| `cmd.exe` re-parses the command line: `%PATH%` **expanded to the entire PATH**, `^` became `^^` | The Fleet resolves npm `.cmd` shims to their real target (a node script or a native exe) and launches that with an argv list.  `cmd.exe` remains only as a degraded fallback, reported as degraded. |
| Windows byte-range locks are enforced against writes | Locks live on sidecar files. |
| `shutil.which` finds `.CMD` but not `.PS1` (PATHEXT) | All five of the operator's CLIs resolve to `.cmd` shims; each was peeled to its real target and verified. |
| `pwsh` is absent; only Windows PowerShell 5.1 | The legacy launcher path falls back to 5.1, which it already handled. |
| `LongPathsEnabled=1` in the registry; `git core.longpaths` unset | Set locally by the repository. |

---

## 5. Caliber findings

**Caliber was not built, and the reason is a specified path, not a shortcut.**

`caliber` is not installed on this machine (`caliber` is absent from PATH;
`npm install -g @rely-ai/caliber` is a global install that pilot v1 rule 6
forbids without asking).  Pilot v1's own **G1 fallback** covers exactly this
case:

> *"if Caliber cannot run, writes outside predicted paths, or overwrites
> human edits destructively → Caliber disabled for the pilot. H2 is marked
> 'not tested' in the report."*

So:

* **H2 is "not tested".**
* WP1's spikes S1–S5 cannot run and are recorded as blocked, not as passed.
* WP8 shrinks to the spec's own reduced scope: constitution injection, I17
  hashing of hand-authored context files, lint (I15) and a drift check.

**What was built anyway, because it does not depend on Caliber:**

* The **constitution stub** is the real CIP Appendix A.1 text, verbatim.
* **I17 is live**: every evidence bundle records `constitution_hash` and
  the Kernel **refuses** a bundle without it.  This was observed, not
  assumed — the first demo run failed with
  `invalid_bundle (problems=bundle.constitution_hash is required (I17))`.
* The **PDD lint** (`pmk pdd lint`) is the spec's lint, implemented and
  tested: seven sections, sequential unique goal ids, exactly one of
  `oracle` or `manual-check`, `gate_cmd` present.
* The **context file classes** (K / C / H) and the lint rules are specified
  in CIP Part B §14.6 and are ready to be implemented against a real
  Caliber.

**Recommended next step:** install Caliber (`npm i -g @rely-ai/caliber`,
pinned to an exact version) and run S1–S5.  The G1 fallback stays in force
until then.  This needs the operator's approval.

---

## 6. Human-load findings

Five interactions are recorded in `pilot/interrupt-log.md`: four were
preference questions (scope, location, CLI probing depth, source
documents) and one was avoidable.

| # | Topic | Minutes | Avoidable |
|---|---|---|---|
| 1 | scope: whole pilot vs Fleet-only | 3 | n |
| 2 | repository location | 1 | n |
| 3 | CLI probing depth | 2 | n |
| 4 | gate behaviour (stop at G0–G3?) | 2 | **y** |
| 5 | missing source specifications | 2 | n |

**The avoidable one.** The gate rule was asked for and the answer was "I
will provide these", which never arrived.  The agent continued under pilot
v1's default (hold) and **crossed no gate silently**, but it also could not
proceed confidently.  The structural fix is a **standing gate posture** in
`pilot/STATE.md` — one line saying whether the agent holds or proceeds —
instead of a per-gate question.  This is a defect in the pilot's own
supervision design, not in the agent.

**What is not yet measured:** daily interrupt counts over a sustained week,
and the ~15-minute daily routine (read STATE, check the queue, spot-read
one evidence bundle).  One day is not enough to measure human load, and
this report does not claim it is.

---

## 7. Verified versus assumed

### Verified by measurement

* Platform: Python 3.12.10, Git 2.55.0, Node 26.7.0, `LongPathsEnabled=1`,
  WSL present but with `docker-desktop` as its default distribution, `pwsh`
  absent.
* The lock constraint, the npm-shim argument mangling and the BOM hazard
  (all three measured, with the artefacts in `pilot/spikes/`).
* All five CLIs resolve to their real executables and run through the
  node-direct bypass.
* The quota engine's four scopes, its atomic multi-scope reservation, its
  reconcile and refund, the DST behaviour on 1 November 2026 (the local day
  is 25 hours long and the quota still resets at local midnight) and the
  account-wide rule.
* The full one-click lifecycle, with the sentinel clean and the chain
  verifying.

### Still open — and what is *not* claimed

| Item | State | Consequence in the code |
|---|---|---|
| Real CLIs' headless behaviour | **UNVERIFIED** | every real adapter's `caps.headless` is `False`, so the Fleet uses the console fallback and marks it `degraded` |
| Real CLIs' resume and model-switch | **UNVERIFIED** | `can_resume = False`, so the ladder falls from L1 to L2 (a fresh session with a handoff note) and then L3 |
| Real CLIs' session ids | **UNVERIFIED** | `reports_session_id = False`; no session is extracted |
| Real CLIs' failure text | **UNVERIFIED** | **no classifier pattern is loaded for any real adapter**, so every non-zero exit is `UNKNOWN` |
| QuotaGate provider limits and 429 shapes | **UNVERIFIED** | the classifier is conservative: an unrecognised body is `unknown_429` with a 60-second cooldown |
| OpenCode headless (spike S-O1) | **not run** | the Overseer runner starts a session through the same unverified path and reports that it is degraded |
| `max_total_agents` | **placeholder (20)** | needs spike S-W1; the scale drill F7 was not run |
| The Overseer's profile list (G-F13) | **placeholder** | needs the operator's input |

**The safety property this creates:** with no fixtures, every failure is
`UNKNOWN`, and the `UNKNOWN` path (retry once, cool after two within ten
minutes) is the only path that has to be safe — and it is tested
(F12).

---

## 8. Proposed amendments

To **pilot v1**:

1. **The lock rule needs a platform note.** Pilot v1 assumes `flock` on a
   Linux filesystem.  On Windows the lock must be on a sidecar file, because
   byte-range locks are enforced against writes.  This is not a preference;
   it is a measured constraint, and the spec should say so.
2. **The gate rule should be a standing posture, not a per-gate question.**
   See section 6.
3. **`pyproject.toml` needs an editable install step.** The `src/` layout
   means `pmk` is not on PATH until `pip install -e .` runs.  Pilot v1's
   §7.5 does not mention it.

To **the Fleet amendment A1**:

4. **The `.cmd` shim rule should be normative, not conditional.** Section 7.2
   says a `.cmd` shim "is launched through `cmd.exe /c` only after S-A1
   shows the arguments survive".  S-A1 showed they do **not** survive, so
   the amendment should say: resolve npm shims to their real target and
   launch that with an argv list.
5. **The scope check needs `--untracked-files=all`.** This was not in the
   amendment, and its absence is a silent-failure hazard.
6. **The merge queue must update the working tree, not just the ref.** Also
   not in the amendment.

---

## 9. Recommended next step

**In order:**

1. **Decide the gate rule** (the one open question from section 6) and
   write it into `pilot/STATE.md` as a standing posture.
2. **Run spike S-A1 live** — one trivial one-shot prompt per CLI, with the
   operator's explicit approval, to capture headless behaviour, session-id
   format, resume semantics, exit codes and failure text.  This is what
   unblocks the real adapters, the classifier, and the L1 resume step.  It
   costs a little free quota and is worth it.
3. **Install Caliber** (pinned) and run S1–S5, so G1 can be decided on
   evidence rather than on the fallback.
4. **Run F7** (the scale drill) with the fake CLI at 100 workers, and S-W1
   (worktree cost), so `max_total_agents` stops being a guess.
5. **Build QuotaGate M1/M3/M5** — the proxy, the failover, and the Kernel
   contract — which needs provider keys and therefore a gate.

---

*Status: candidate-tier pilot report by OpenCode, 2026-10-22.  Everything
marked "tested" was run in this repository; everything marked "not tested"
was not run, and no claim is made about it.*
