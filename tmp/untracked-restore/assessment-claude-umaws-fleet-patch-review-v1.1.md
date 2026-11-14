---
document:
  title: "Assessment: Review of the Hardening Patches (77a56db..aed9aec and uncommitted) and Relay B/G for Claude Code"
  type: "Assessment and recommendations"
  status: "Advisory; no authority"
  version: "1.1.0"
provenance:
  author_llm: {name: "Claude", version: "Claude Sonnet 5.5 (Anthropic)"}
  created_date: "2026-11-02"
  last_modified_date: "2026-11-02"
  builds_on: "handoff-claude-umaws-fleet-launcher-v5.md; assessment-claude-umaws-fleet-worktree-isolation-v3.md"
audience:
  primary: "The human operator (decision record)"
  secondary: "Claude Code (implementer; section 7 is the executable brief)"
evidence_basis: "code-77a56db-aed9aec.patch and uncommitted.patch, read in full as diffs; relay-A, relay-C and step1-canary reports; OpenCode's read-only check results (subprocess unpack test, agents.toml id list, git log, ledger query for T-0139 fence 117). I have NOT seen the full source files, the ledger itself, a clean-checkout junit, or the results of the corpus-pin / console-process / snapshot-freshness / queue relay."
epistemic_status: "Tags: [OBSERVED] seen in a diff or in a command result reported to me; [INFERRED] my reasoning from the diff; [VERIFY] needs a check in the full source or ledger; [STATED] said by the operator; [GUESS]. Nothing here was run by me."
authority_statement: "Candidate tier. This document recommends; nothing takes effect until the operator decides. Changes to .pm/policy.toml or .pm/constitution.md are class K (two-key)."
---

# Assessment: Patch Review and Relay B/G

## 1. Verdict

**Do not commit or ship the current hardening as it stands.** The order-path fix (`order_prompt`) is correct and should stay. Several of the new guards are broken or harmful, and one of them (NO_CHANGES) is confirmed to misfire on every real implement card. A small, reviewed code round (section 7) should replace them before dispatch is resumed.

| Item | Verdict |
|---|---|
| `order_prompt(worktree)` and the 4 spawn-site changes | Accept |
| R-02 `_validate_agent_claims` | Reject as written (F-1 to F-4) |
| R-09 main-tree check | Reject as written (F-5, F-6) |
| R-11 main-tree status in events | Rework (F-10) |
| Isolation warning in `render_order` | Unproven; rework (F-7) |
| Conductor lease auto-revoke (uncommitted) | Reject as written (F-11) |
| `merge.py` `--no-ff` fallback (uncommitted) | Reject as written (F-12) |
| `agents.toml` (uncommitted) | Fix before use (F-13) |
| TTL 20 to 120 (uncommitted) | Prefer revert plus heartbeat-aware stall (D-3) |

## 2. Findings: `code-77a56db-aed9aec.patch`

| # | Finding | Evidence | Fix |
|---|---|---|---|
| F-1 | **NO_CHANGES fires on every real implement card.** `code, out, _ = subprocess.run(...)` tries to unpack a `CompletedProcess`; that raises `TypeError`, the bare `except Exception` swallows it, `out` stays `""`, so `changed` is empty. | [OBSERVED] diff; unpack `TypeError` reproduced by OpenCode | Use `r = subprocess.run(...)`; read `r.stdout`; never swallow the error silently (record an event) |
| F-2 | **New-file work counts as "no changes".** The filter drops lines starting with `??`, which is how untracked files appear. A card that only creates files (the corpus vendoring) would fail. | [OBSERVED] diff | Parse `git status --porcelain -z --untracked-files=all`; count `??`; exclude only `.pmwork/` |
| F-3 | **The failure does not "fail the attempt immediately"** as decided. It sets `outcome="failed"` and returns, without `_recover` or `_give_up`. | [OBSERVED] diff; caller behaviour [VERIFY] | Route through the same path as a non-OK exit class, with a new failure class `NO_CHANGES` |
| F-4 | **RESULT.md id check is weak.** `f"T-{task.id}"` yields `T-T-0136`; only the second clause can match. Substring match is easy to satisfy and a correct RESULT.md that omits its own id is rejected. | [OBSERVED] diff | Make it advisory (event, not failure) or require a `Task:` header written by the order template |
| F-5 | **R-09 leaks the lease it just claimed.** The check runs after `kernel.claim()`, worktree creation and order writing, then returns `None, result` without releasing. It also burns an attempt. | [OBSERVED] diff (the order text above it already uses `lease.attempt`) | Run the check before `kernel.claim()` so refusal has no side effects |
| F-6 | R-09 detail defects: dead variable `scope_conflict`; naive porcelain parsing (renames, quoted paths); `line[3:]` breaks if `repo.git` strips the first line's leading space; and the main tree is **permanently dirty** now (untracked corpus, modified `docs/rules/index.json`), so any card writing under `docs/rules/` would be refused every time. | [OBSERVED] diff; HANDOFF state | `-z` parsing; component-wise `scope_overlaps`; refuse with a clear queue item rather than looping; operator decision H-31 |
| F-7 | **The isolation warning may never render.** It reads `getattr(lease, "worktree", "")`, but the worktree lives on `LeaseRun`, and CLAIMED recorded `worktree=""`. No test covers it. | [OBSERVED] diff; [VERIFY] attribute | Pass the worktree into `render_order` explicitly; add a test asserting the text appears |
| F-8 | **The absolute prompt fixes only the reading of the order.** Relay A shows a Hermes agent modified `pi-test.txt` in the main tree, and the f114 log claims "pre-staged and verified" against an empty worktree. [INFERRED] relative write paths in ORDER.md resolve against the main tree. | Relay A, section 3; T-0139 hint precedent | Render **absolute destination paths** for every `scope.write` path in ORDER.md |
| F-9 | **The canary contradicts re-adding `--in`.** `--in` did not change where Hermes resolves paths. | step1 canary results | Drop "re-add `--in`" as a primary fix; rely on absolute paths, a spawn self-test and a main-tree diff guard |
| F-10 | **R-11 bloats events and acts on nothing.** The full porcelain output goes into every AGENT_STARTED and AGENT_EXITED; with about 65 untracked corpus files and several slots this is large, and nothing compares the two snapshots. | [OBSERVED] diff | Record a hash plus a count plus up to 20 paths; at exit, flag **new** main-tree changes inside the write scope |
| F-10b | The prompt-regression test asked for in R-03 is missing; `FIXED_PROMPT` still exists. | [OBSERVED] diff | Test all spawn sites; make `FIXED_PROMPT` unusable |

## 3. Findings: `uncommitted.patch`

| # | Finding | Evidence | Fix |
|---|---|---|---|
| F-11 | **Conductor auto-revoke is unsafe.** It iterates every lease with no check that the task is non-terminal, so a stale lease on a DONE task is revoked (the T-0003 precedent says that can reopen it). It uses `granted_at` only (ignores `renewed_at`). `except KernelError: pass` hides failures, so the project can re-stall every tick. A revoke does not obviously kill the agent process. The same logic is duplicated in `check_stall` and `tick`. | [OBSERVED] diff; process kill [VERIFY] | Skip terminal tasks; use the later of `granted_at` and `renewed_at`; record failures as events; one shared helper |
| F-12 | **The `--no-ff` fallback weakens the merge gate.** The gate tested the temp-worktree commit; after divergence, main receives a merge commit that was never tested. On conflict it never runs `git merge --abort`, so main can be left mid-merge. | [OBSERVED] diff | After a `--no-ff` merge, re-run the gate on the result, or refuse and requeue; always abort on failure; do not land this change until then |
| F-13 | **`agents.toml` defects.** `hermes-beam` is defined twice (priorities 80 and 2). The overseer list names `cline-mimo`, `hermes-oneshot`, `overseer-beam` and `opencode-beam`, which are absent from the id list OpenCode printed. `pi-orca-deepseek` is first in the overseer list but its roles are only implement and review. The cap is `max_total_agents = 10` while the CFNA PDD says 6 [VERIFY which key is enforced]. | [OBSERVED] diff and id list | Loader must reject duplicate ids and unknown overseer names; fix the file; confirm the cap |
| F-14 | **TTL 20 to 120** is a wall-clock cap on healthy tasks, and a dead supervisor then costs 2 hours. | Assessment v3, section 6 item 7 | See D-3 |

## 4. Corrections to the handoff and to Relay A/C

1. **Handoff v5 said T-0139 f117's lease appears never released.** The ledger query shows no REVOKED or LEASE_EXPIRED for f117, but `pmk status` now shows only 2 active leases (T-0141, T-0142). [OBSERVED] So the stale lease is not currently active. Why is unknown; it may have been released at INTEGRATED, so my "needs a code fix" reading is unproven. [VERIFY in the ledger]
2. **HEAD is `393d0ea`**, not `786d52d` (Relay A) [OBSERVED].
3. **Relay A, section 7** supports D-1: Python API calls are recorded as `kernel`, CLI commands as `operator`.
4. **Relay C is not a usable census.** It attributes `max_total_tasks = 10` to `agents.toml` (that key is a policy default), its D3 answer rests on cards that were BLOCKED, not on a VOID dependency, and the idle-class entries carry no numbers. Phase 0 remains open.
5. **The corpus line-ending claim is still not established.** Two differing blob ids for two copies prove only that those copies differ. The pin comparison (`75a037f` blob versus each copy, plus CR/LF counts) has not been reported.

## 5. Open facts still needed (first relay, not yet reported)

Corpus bytes against the pin; what PIDs 4160 and 5864 each run (two `console.app` processes on the same root may mean two Conductor/Dispatcher loops, and the system-python one may import a different install); whether the event snapshot is older than the live files; the 3 open queue items; who set PAUSED and who moved T-0145/T-0146 from READY to PROPOSED.

## 6. Decisions needed from the operator

| ID | Plain-language question | Recommendation |
|---|---|---|
| D-1 | Interactive assistants act under your identity or as `kernel`, so the ledger cannot tell who did what. Launch them with `PMK_ACTOR=agent:<tool>` and run human-only commands in your own shell? | Yes |
| D-2 | How the corpus lands | Derive all 66 files binary-safely from `C:\temp\tcanf-clone` at `75a037f`, check blob ids, regenerate manifest and checksums, add `docs/rules/** -text` in `.gitattributes`, commit with a recorded decision naming T-0139. Do not merge `pmk/T-0139-117` or copy the main-tree files. Wait for the pin comparison first |
| D-3 | TTL and pins | Revert TTL to 20, make heartbeats count (later of `granted_at` and `renewed_at`); one decision id covering policy, pin and conductor change |
| D-4 | T-0141, T-0142, T-0145, T-0146 | Keep dispatch paused; land the corpus; then void 141 and 142 and re-check 145 and 146 |
| D-5 | Incident closure | Keep open; closure list in assessment v3 section 7 |
| H-12 | Keep the `verify`/`maintain`/`research` task types although they are undispatchable? | Needs your explicit answer |
| H-31 | Adopt the rule "no uncommitted edits inside a READY or LEASED card's write scope"? | Yes; it makes R-09 meaningful |
| New | Pause the two consoles' dispatch loops until we know whether both tick the ledger | Yes, but do not kill either until the process check is back |

## 7. Relay B/G for Claude Code (executable brief)

Paste the block below to Claude Code. Do not start until the operator has answered D-3 (it changes item 4).

```text
From: Claude (Claude Sonnet 5.5), reviewer

CONSTRAINTS (every item): no git add, git commit, git reset or git clean. Do not delete or move files.
Do not write to .pm/. Do not edit .pm/policy.toml, .pm/constitution.md or .pm/pins.sha256 (class K).
Work against base commit 393d0ea. Deliver a patch (git --no-pager diff --output=<file>), a fresh
pytest_junit.xml from a CLEAN CHECKOUT of that commit plus your patch, and an honest list of what you
ran and did not run. Do not claim "implemented" for anything without a test that fails before the fix.

B1  harness._validate_agent_claims: use r = subprocess.run(...); read r.stdout; on exception record an
    event, never swallow. Parse `git status --porcelain -z --untracked-files=all`; untracked files count
    as changes; ignore only .pmwork/. Failure must go through the same path as a non-OK exit class
    (new class NO_CHANGES), consuming one attempt immediately. RESULT.md id check: advisory event only.
    Tests with REAL git in a tmp repo: new-file only (pass), modified only (pass), nothing (fail), and a
    test that fails if the subprocess result is unpacked as a tuple.

B2  R-09: move the main-tree check BEFORE kernel.claim(); refusal must create no CLAIMED event and burn
    no attempt. Use -z parsing and component-wise scope_overlaps. Remove the dead variable. On refusal
    raise one queue item per task (not per tick). Test: claim count unchanged after refusal.

B3  Kernel.integrate: require a non-empty commit sha reachable from main (git merge-base --is-ancestor),
    recorded in the INTEGRATED payload; sentinel check for INTEGRATED with empty commit.

B4  Stall/lease logic (pending D-3): one shared helper; skip leases of tasks in terminal states; use the
    later of granted_at and renewed_at; never `except: pass`, record failures as events; do not revoke a
    DONE task. Confirm in code whether revoke stops the agent process and report.

B5  merge.py: after a --no-ff fallback, re-run the gate on the merged result or refuse and requeue; on any
    failure run `git merge --abort`. Test the diverged-main case end to end. Do not land the fallback
    without this.

B6  Order rendering: pass the worktree into render_order explicitly; list the ABSOLUTE destination path
    for every scope.write entry; test that the isolation warning and absolute paths appear.

B7  Prompt regression: test every spawn_slot call site uses order_prompt(worktree); make FIXED_PROMPT
    raise or remove it.

B8  R-11: record only a hash, a count and at most 20 paths of main-tree status in AGENT_STARTED/EXITED;
    at exit, flag NEW main-tree changes inside the task's write scope as an event.

B9  Oracle lint: parse each oracle exactly as the harness will run it (cmd.exe on Windows); compile any
    `python -c` payload; reject nested double quotes that close the argument early, or ban inline -c
    in favour of committed scripts. Error, not warning.

B10 agents.toml loader: reject duplicate profile ids and overseer names that match no profile; report
    which key enforces the concurrency cap (max_total_agents vs fleet_cap) with file and line. Do not
    edit agents.toml itself; list the exact corrections needed.

B11 Reconcile-on-start: at dispatcher start, adopt or fail leases of LEASED tasks with no live process;
    run --seconds N must refuse (or hand off) when leases are in flight. Test with the fake CLI.

B12 Per-profile spawn self-test (decoy ORDER.md at the repo root AND an uncommitted main-tree decoy; the
    agent must report the worktree path and file contents). Hermes via the real spawn_slot path.

Report per item: files and lines changed, the test that fails without the change, and anything you could
not do. Stop after B1 to B3 if any of them needs a Kernel decision I have not made.
```

## 8. Risks

| # | Risk | Mitigation |
|---|---|---|
| K-1 | Dispatch resumed before B1: every implement card fails NO_CHANGES | Keep paused; B1 first |
| K-2 | Dispatch resumed before B2: each refusal leaks a lease and an attempt | Keep paused; B2 before resume |
| K-3 | Two console processes both tick the ledger | Process check before any resume |
| K-4 | Uncommitted merge fallback lands an untested merge into main | Hold until B5 |
| K-5 | Free-tier implementer over-claims | Require a failing-before test per item and a clean-checkout junit |

---

## 9. Addendum v1.1: evidence from relays 2 to 4

### 9.1 Corrections to v1.0 and to my earlier replies

1. The venv editable install is fine: the `.pth` points to `testproject1\src` and `pmk`, `fleet` and `console` import from the repo. Only the pip metadata names `T-0096-48`. Withdrawn as an alarm.
2. PIDs 4160 and 5864 are one console (venv launcher plus child; the child holds port 8765), not two loops.
3. T-0145 and T-0146 were created directly as PROPOSED by the Overseer (seq 2977/2978); they were never READY. The Overseer's claim that R-09 is why they are not admitted is doubtful, because R-09 acts at lease time. [VERIFY who admits PROPOSED cards]
4. The Overseer wake cap (6 per hour, 60 s debounce) is enforced. The defect is that `should_wake()` ignores PAUSED and an Overseer-filed incident re-wakes the Overseer: 84 wakes since seq 2992, all with reason `incident`.
5. H-30 is explained: an Overseer session ran `pmk incident list`, which has no such subcommand, and logged "list" as an incident (seq 3017).

### 9.2 Established [OBSERVED]

- **Corpus source.** The pin (`tcanf-clone@75a037f`) has 71 files; 66 are in scope (`CNA-Rules.adoc` plus 65 sections). `C:\temp\corpus-staging-75a037f` holds those 66 files: 66/66 git blob ids verified, 0 CR bytes, identical to the `work/T-0131-110` copy.
- **CRLF origin.** The clone's working tree is CRLF (system `core.autocrlf=true`, `CNA-Rules.adoc` CR=178) while its blobs are LF. Every CRLF copy (main, T-0139, T-0097) derives from that working tree. The repo's local `autocrlf=false` committed those bytes unchanged, so branch `2a0f6fa` matches the pin in 0 of 66 blobs.
- **False attestation.** `manifest.json` and `checksums.sha256` at HEAD and on `2a0f6fa` attest the CRLF hash (`e585...`), not the pin's (`5654...`).
- **Repair event.** T-0127 has a second INTEGRATED event (seq 2689, fence 103) with `commit: ""` and the note "restore DONE after expired-lease auto-revoke". This confirms F-11: the existing auto-revoke reopened a DONE task and a hand-written repair event restored it. The sentinel reads the latest INTEGRATED event, which has no bundle, so T-0127 is flagged. [INFERRED] the other four I6 findings (T-0118, T-0119, T-0129, T-0130) have the same cause. [VERIFY]
- **STOP findings do nothing.** Only `sentinel.py` reads `stops`; it sets `Report.ok = False` but nothing in the code read so far stops the project. [VERIFY callers of the sentinel result]
- **T-0139** has a bundle but an empty commit, so the sentinel does not flag it (B3 covers this).

### 9.3 Additions to Relay B/G

- B13: sentinel finding when the editable metadata and the `.pth` disagree; oracle lint rejects `pip install -e` inside worktrees.
- B14: `should_wake()` returns false while PAUSED; an Overseer-filed incident must not wake the Overseer; incident wakes require a new incident from another actor.
- B15: a `stops: true` finding must set a stopped state or be recorded as acknowledged; first find every caller of the sentinel result.
- B16: corpus extraction uses `git cat-file blob` or `git archive` from the pin, never a working tree; the oracle compares blob ids to the pin.
- B17: a typed repair event that carries a bundle reference and a decision id; the sentinel treats it as valid. This is also the answer to H-27.
- B18: `pmk incident` rejects unknown subcommand-like messages (`list`) or implements `list`.

### 9.4 Recommended Q-074 decision (class K; operator's own shell)

Neither option 1 nor 2. Suggested custom wording, for the operator to edit:

> Neither. Main's uncommitted docs/rules content is off-pin (CRLF; CNA-Rules.adoc sha256 e585... vs pin blob 5654...) and T-0139's branch copy is the same. Land the corpus from the pin objects instead: 66 files from tcanf-clone@75a037f, staged byte-exact at C:\temp\corpus-staging-75a037f (66/66 git blob ids verified, 0 CR bytes). Back up main's uncommitted docs/rules and coverage files, replace them with the staged files, regenerate manifest, checksums, index and coverage with the existing tools, add `docs/rules/** -text` to .gitattributes, and commit once, citing this decision. Branch pmk/T-0139-117 is superseded and stays unmerged.

### 9.5 D-2 landing procedure

1. Stop the console from its own terminal (it must be restarted after code changes anyway); take a fresh events snapshot.
2. Decide Q-074 as above.
3. Preparation relay (Relay 5): backup copies, byte-exact copy of the 66 staged files, blob-id verification, regeneration of manifest, checksums, index and coverage with the existing tools, `.gitattributes` line, `pytest -q`. No git add or commit.
4. Operator reviews `git status` and `git diff --stat`, then commits once with the decision id.
5. Then D-4: void T-0141 and T-0142, re-check T-0145 and T-0146, and keep dispatch paused until B1 to B3 and B14 are in.
