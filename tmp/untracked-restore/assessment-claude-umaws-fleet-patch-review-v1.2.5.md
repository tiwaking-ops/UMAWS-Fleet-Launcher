---
document:
  title: "Assessment: Review of the Hardening Patches (77a56db..aed9aec and uncommitted) and Relay B/G for Claude Code"
  type: "Assessment and recommendations"
  status: "Advisory; no authority"
  version: "1.2.5"
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

---

## 10. Addendum v1.2: review of the working-tree source changes (`wip-src-tests.patch`, `oracle_lint.py`, `selftest.py`)

**Evidence:** the patch (16 modified files under `src/` and `tests/`), the two new files, and the post-landing checks. Read as diffs only; none of it was run by me. The full test suite has not been run on this tree (no `pytest-wip.txt` or junit exists). Base for the patch is commit `393d0ea`; the corpus commit `1a5ec9b` does not touch `src/` or `tests/`.

### 10.1 Landing check (accepted)

Commit `1a5ec9b` is authored by Tiwa Pene; `docs/rules/CNA-Rules.adoc` has blob id `e493691...` (the pin's); the manifest carries the pin's hashes; `docs/rules`, `coverage/` and `.gitattributes` are clean. Open points: the Q-074 `QUEUE_DECIDED` event (seq 3094) is attributed to `kernel`, not a human (D-1 again), and no ledger event records the commit sha. T-0139's INTEGRATED event still says `commit: ""` (B17).

### 10.2 Verdict

**Do not commit the working-tree source changes as they stand.** About a third is correct. Several items are harmful if run: one can leave an untested merge in main, one can stop the Fleet from loading `agents.toml`, and one repeats the lease leak that R-09 had. B4, B13 to B16 and B17 to B19 are not in the patch at all, and the conductor and merge hunks are the old uncommitted ones unchanged.

| ID | Item | Verdict | Finding |
|---|---|---|---|
| F-20 | B1 NO_CHANGES | Partly correct | `-z` parsing, `r.stdout` and untracked files are right. But: the "advisory" RESULT.md mismatch still lands in `claim_errors`, so it fails the attempt as UNKNOWN; a git failure still yields empty output and is reported as NO_CHANGES (printed, not recorded as an event); `-z` rename records and `text=True` decoding are mishandled; the existing test runs in a non-repo `tmp_path` and passes for the wrong reason; no real-git tests were added. How `recover.py` treats the new class is unverified. |
| F-21 | B2 R-09 before claim | Partly correct | Reordering is right. But `SCOPE_CONFLICT` is recorded on every attempt (fence 0, no de-duplication; the dispatcher ticks every 5 s), the outcome `blocked` may not be handled by the dispatcher [VERIFY], there is no test that no CLAIMED event exists and no attempt is burned, and `scope_overlaps` semantics are still unverified. The main tree is also dirty with Fleet's own `src/` and `tests/` changes, so any card whose scope covers those directories is refused until they are committed. |
| F-22 | B3 integrate | **Wrong** | The check is `merge-base --is-ancestor HEAD <commit>`, which is inverted: it asks whether HEAD is an ancestor of the commit. It passes only when commit equals HEAD. It would reject every integration through the `--no-ff` path and any integration after main has moved. The tests pass because they use `commit=HEAD`. No negative tests; no sentinel check for an empty commit. |
| F-23 | The 7 test failures | Explained | [INFERRED] The `kernel` fixture repo has no commit, so `_head_commit` returns an empty string and the new check refuses. The fix is a fixture that makes an initial commit, not more helper code. |
| F-24 | B5 `--no-ff` gate | **Harmful** | `merge --abort` runs with `cwd=target` (the temp worktree) while the merge ran in the main tree, so it aborts nothing. After a successful `--no-ff` merge a commit already exists, so `--abort` is a no-op even in the right directory. On a failed gate the untested merge commit stays in main while the task is reported failed. The re-run gate also uses `cwd=target`, the pre-merge tree, so it re-tests the same content. `result.commit` is the pre-merge sha, not main's new HEAD. |
| F-25 | B6 absolute paths | Accept | `worktree` is passed in and absolute destination paths are rendered. No test; other `render_order` callers unchecked. |
| F-26 | B7 `FIXED_PROMPT` | Weak | A sentinel object that raises on use fails at runtime in the middle of a lease. Delete the constant. The required test that every spawn site uses `order_prompt` is still missing. |
| F-27 | B8 main-tree diff | Unreliable | The exit-time diff compares the 20-path sample only. The tree currently has 127 dirty entries, so new in-scope changes can fall outside the sample. Keep the full set in memory; record only the new in-scope paths. |
| F-28 | B9 oracle lint | **Defective** | It runs after `kernel.claim()` and returns on failure without releasing the lease (the R-09 leak again). The unescaped-quote count is dead code, because the regex stops at the first unescaped `"`; nested quotes are caught only by the incidental `compile()` failure. Single-quoted payloads are accepted, but under cmd.exe single quotes do not group arguments, so the oracle is split at spaces and cannot pass [VERIFY `run_command`]. (Correction in v1.2.1: T-0145 and T-0146 do not have this problem. Their `python -c` payloads are double-quoted with single quotes inside, which is the safe form. They chain with `&&`, which needs a shell [VERIFY `run_command`].) The cmd.exe block is a no-op. The lint is not applied at admission. |
| F-29 | B10 `load_agents` | **Harmful** | It raises `ValueError`, although its docstring says a broken profile file must not take the Kernel down. The agents.toml overseer list named profiles that, by the earlier id list, do not exist (`cline-mimo`, `hermes-oneshot`, `overseer-beam`, `opencode-beam`) [VERIFY against the current file]. If so, the console and dispatcher will fail to load. It also prints on every load and does not report where the cap is enforced. |
| F-30 | B11 reconcile | Half done | Dead leases are failed (good). "Adopted" only records an event; nothing supervises the process, so its result is lost again. `run_forever` then refuses to start while such a lease is live, and nothing harvests it. Reconcile runs only in the Console, not in `pmk dispatch run`. `revoke` and `quarantine` errors are swallowed. |
| F-31 | B12 self-test | **Vacuous** | The pass conditions are strings that appear in the prompt itself (the worktree path, "NOT FOUND", the marker name), so an agent that echoes the prompt passes. The multi-line, quoted prompt is not the production single-line `order_prompt`, so it does not exercise the real path and can be mangled by `.cmd` shims. It writes decoys into the main tree. `dispatch selftest` runs live provider calls for every enabled profile, which the agents.toml notes call an authorisation action. Verification must be filesystem-based: the agent creates a probe file by relative path and the harness checks where it landed. |
| F-32 | Not in the patch | Open | B4 (heartbeat-aware stall, terminal-task skip), B13, B14 (wake loop), B15, B16, B17 and B18. |
| F-33 | Tests | Thin | Five test files were edited only for B2, B3 and B7. There are no new tests for B1 (real git), B5, B6, B9, B10, B11 or B12. |

### 10.3 Operational hazards while this tree is uncommitted

1. **Do not restart the console** with this tree until `agents.toml` is checked against F-29 (or B10 is reverted). The console is currently stopped.
2. **Dispatch stays paused.** F-24 and F-28 can damage main or leak leases.
3. **Commit nothing from `src/` or `tests/`** until the second round passes review.
4. The relay to Claude Code (Relay B/G v2) was given in chat; it supersedes section 7 for these items.

### 10.4 Addendum v1.2.1: results after the full test run

1. **Tests:** 376 passed, 7 failed (383 collected, the same count as the earlier baseline). All 7 fail at `integrate()` on the empty commit, which is consistent with F-23 (the `kernel` fixture repo has no commit).
2. **agents.toml overseer list [OBSERVED]:** `cline-mimo`, `overseer-beam`, `opencode-beam` and `hermes-oneshot` are still named and are not in the profile id list. With B10 as written, `load_agents` raises and the console will not start. The list must be fixed before any restart, or B10 must stop raising (R4).
3. **T-0145 and T-0146 oracles:** both are `python -m cna.tools.<tool> --check && python -c "<payload with single quotes>"`. They are well formed (see the correction in F-28). They check `docs/rules/index.json` (`stats.documents >= 66`) and `coverage/rules_coverage.json` (`counts.rule_files >= 66`), which the landing commit already regenerated. [INFERRED] The cards may already be satisfied by HEAD; an implement card with nothing to change would now fail NO_CHANGES. Check by running the two oracles on main, then decide whether to void them.
4. **Q-074 actor:** the CLI path `pmk queue decide` records actor `kernel`. D-58 in `pilot/decisions.md` records the gap. The fix belongs with D-1 (R11: CLI commands run by a human default to a human actor; assistant sessions set `PMK_ACTOR`).

### 10.5 Addendum v1.2.2: correction to my own R2 (merge gate)

My Relay B/G v2 item R2 told the implementer to run the gate with the main tree as the working directory. That design is flawed while main carries uncommitted changes (127 dirty entries at last count): the gate would test the merge plus unrelated dirt, results would depend on what the operator happens to have edited, and `git merge --no-commit` into a dirty tree can leave main in a mixed state. The better design keeps the gate on a clean tree:

1. Build the merge in a temporary worktree based on **current** main HEAD (`--no-ff`).
2. Run the gate there.
3. Fast-forward main with `git merge --ff-only <merge commit>`. If main has moved since step 1, rebuild from the new HEAD and re-run the gate (bounded retries), or requeue.
4. If main's dirt blocks the fast-forward (the T-0139 case), refuse with a clear queue item; that is H-31.

Under this design an untested commit never enters main, and nothing needs `merge --abort` in main at all. R2 as implemented (merge and gate in the main tree) should be reviewed against this before it is accepted.

### 10.6 Review status of R1 to R4

Reported as implemented by the implementer: R1 (ancestry check, fixture with an initial commit, sentinel findings), R2 (merge in main tree), R3 (oracle lint moved to admission), R4 (`load_agents` no longer raises; `pmk fleet check`). Not yet reviewed: no patch, no full-suite result and no clean-checkout junit have been supplied (84 selected tests only). Expected side effect of R1: the sentinel will now flag the live ledger's empty-commit INTEGRATED events (T-0139, the T-0127 repair event); that is correct until B17 provides a typed repair event.

### 10.7 Addendum v1.2.3: Relay 9 results (R1 to R4 as reported; the patch itself not yet received)

**Evidence:** the Relay 9 report only. `wip2-src-tests.patch` (72,303 bytes) and four new files exist on the operator's disk but have not been uploaded, so R1, R3 and R4 are reviewed from the report, not from code.

| ID | Finding | Evidence |
|---|---|---|
| F-34 | **R2 as built puts the merge and the gate in the main tree** (`merge --no-ff --no-commit` at line 155, gate at line 183 with `cwd=repo.root`), per my flawed instruction. Main is dirty and a gate run takes minutes, so main sits half-merged for that time; a crash leaves `MERGE_HEAD` behind; `git merge --abort` can fail to restore changes that were uncommitted when the merge began (git documents this). Replace with the temporary-worktree design in 10.5 (R2b). | Relay 9, section 4 |
| F-35 | **R4 does not enforce the errors at runtime.** Callers use `["fleet"]`, `["profiles"]` or the full dict; only `pmk fleet check` reads `["errors"]`. A duplicate id or unknown overseer name, which previously raised, is now silently accepted by the dispatcher. | Relay 9, section 3 |
| F-36 | **The one failing test is not shown to be pre-existing.** `test_briefing_contains_the_constitution` fails in the clean checkout. In the earlier working-tree run, the 7 failures were the empty-commit ones, so this test then passed. [INFERRED] it depends on a file that exists in the working tree but not in a clean `git archive` of HEAD (for example `.pm/constitution.md`). That is exactly the class of defect the clean-checkout rule exists to catch. | Relay 9, section 5 vs the earlier 376/7 run |
| F-37 | **Lint and `\"`.** `run_command` uses `shell=True` (cmd.exe), which confirms the lint's single-quote rule. But cmd.exe toggles quote state on every `"` regardless of a backslash, so an unescaped-looking `\"` inside a payload can expose `&`, `\|`, `<`, `>` or `^` to cmd.exe's own parser. The lint "unescapes `\"` before the syntax check", which may accept such payloads. [VERIFY with the code] | Relay 9, section 2 and the R3 summary |
| F-38 | **Correction of my own inference:** T-0145 and T-0146 are real work, not already satisfied. Their oracles fail on main (`documents` is 3, `rule_files` is 3, because the tools index only the three `.md` rules files, not the 66 `.adoc` files). They stay PROPOSED until dispatch resumes. | Relay 9, section 6 |

**Good news:** the clean-checkout suite ran with `pmk.__file__` under the clean directory: 414 passed, 1 failed, 1 skipped (416 tests, up from 383). `agents.toml` passes the unknown-name and duplicate-id checks. Dispatch, console and TTL are unchanged.

**Next:** Relay 10 (given in chat): R2b (temporary-worktree merge), R4b (enforce `errors` at runtime), R3b (reject `\"` in payloads with cmd metacharacters), and a read-only investigation of F-36.

### 10.8 Addendum v1.2.4: review of the Relay 10 delivery (`relay10.patch`, new files, junit)

**Evidence:** `relay10.patch` (converted from UTF-16 for reading), `wip2-src-tests.patch`, the new files, `junit-pmk.xml`, `junit-fleet.xml`, `junit-other.xml` and `RELAY10_SUMMARY.md`. Read as diffs and XML; nothing was run by me.

**Verdict:** R1 is accepted. R2b and R3 have the right structure but lack the tests that were required. R4b does not meet its requirement. Several items from the deferred list (R5 to R10) are in the patch in partial form and are not accepted. No commit yet.

| ID | Item | Verdict | Finding |
|---|---|---|---|
| F-39 | Test evidence | Not accepted | The junit files total 311 tests (pmk 182, fleet 129) with 0 failures and 0 skipped; `junit-other.xml` ran **0 tests** (shell globs such as `tests/test_*.py` are not expanded by PowerShell). The summary's counts (86, 56, 14) do not match the XML, and its "1 skipped" does not match `skipped="0"`. About 105 tests (quotagate, rules index, coverage, engine contract, smoke) were not run. The XML timestamps (19:48 to 19:51 NZDT) precede the patch file (19:55), and no `pmk.__file__` proof is in the delivery. |
| F-40 | Patch file | Not usable | `relay10.patch` is UTF-16LE with CRLF (PowerShell redirection), so it will not apply with `git apply` and its text is re-encoded. The earlier `--output=` patches were fine. Regenerate with `git --no-pager diff --output=`. |
| F-41 | R1 (integrate ancestry) | **Accept** | Correct direction (`is-ancestor <commit> HEAD`) after `rev-parse --verify`; real-git tests for empty, unknown, unreachable, descendant-not-in-main and HEAD; sentinel findings with `stops: false`; the `repo` fixture now makes an initial commit. Small points: add a test with an older ancestor (`HEAD~1`); the Kernel appends a `SENTINEL_FINDING` event before raising, so repeated attempts add events. |
| F-42 | R2b (merge in a temporary worktree) | Structure accepted; **tests missing** | The design matches 10.5: temporary worktree from main HEAD, `--no-ff` merge and gate there, retry if main moved, `--ff-only` in main, cleanup. But no test covers the required cases (gate fails with an unrelated dirty file in main; main moves mid-run; overlapping dirt; conflict). The three existing reintegration tests are the only ones. Long rationale comments (I5 pre-merge, the 2026-10-24 re-integration defect) were deleted and should be restored. How the conductor treats `INFRASTRUCTURE_FAILED` at the fast-forward stage (a deterministic refusal) is unverified, and T-0139 shows the risk of retry loops. |
| F-43 | R3 (oracle lint at admission) | Accept with changes | Lint now runs in `task_admit`, before any claim, and all `python -c` occurrences are checked. Defects: no tests for the backslash-quote plus metacharacter rule or for `&&` chains (the test file is the old 14-test file; its multi-`python -c` test still says "only first is checked"); the guard `"python -c" in oracle` and the regex miss `python.exe -c`, `py -c`, `python3.12 -c` and full paths; `%` (expanded by cmd.exe even inside quotes) is only checked in the escaped-quote case; `pmk.api` imports `fleet.oracle_lint`, which inverts the layering (the Kernel is stdlib-only; the lint belongs in `pmk`); no test that `task_admit` actually refuses a bad oracle. |
| F-44 | R4b (enforce config errors) | **Not met** | `test_load_agents_invalid_toml` asserts `errors == []`, so a broken `agents.toml` yields no error and zero profiles, silently; I asked for a file-level error. `enforce_fleet_config` reads the whole log with `read_all(repair=True)` (torn-tail repair on a read path, with no lock, while another process may be appending) [VERIFY what repair does]. `get_profiles_with_errors` has dead code (an unused list and a branch that always returns an empty set). The cap-key question (D9) is answered only as "which keys exist", not which one the code enforces. No test goes through the real dispatcher or console path. Starting the console or dispatcher raises on any error, which is stricter than asked and acceptable. |
| F-45 | `console/app.py` | Defect | The patch deletes the `/api/project/status` route, which is unrelated to any item. Restore it (and the trailing newline). |
| F-46 | R8 reconcile | Still half done | "Adopted" still only records an event; nothing supervises the process. Dead leases are failed (revoke plus quarantine, errors swallowed). `kernel.quarantine` and `spawn_mod.worktree_path` are unverified [VERIFY]. Reconcile runs only in the Console constructor, not in `pmk dispatch run`. |
| F-47 | R9 self-test | Unchanged, and runnable | `selftest.py` is byte-identical to the earlier version (F-31 stands), yet `pmk dispatch selftest` now exists and runs live agents for every enabled profile, with decoys written into the main tree and no quota confirmation. **Do not run it.** |
| F-48 | B1 follow-ups | Open | The RESULT.md "advisory" mismatch still fails the attempt (any claim error goes to recovery as UNKNOWN); a git failure is printed and then classified NO_CHANGES; the exit-time diff compares only the 20-path sample; `SCOPE_CONFLICT` is recorded on every attempt with `fence=0` although the comment says once per task; the `blocked` outcome's handling by the dispatcher is unverified. |
| F-49 | B7 | Not done | `FIXED_PROMPT` is still a sentinel that raises on any attribute access, including by introspection tools; delete the name and add a test that every spawn site uses `order_prompt`. |
| F-50 | B4 | Absent | The conductor hunks are the old auto-revoke code unchanged (granted_at only, no terminal-task skip, `except KernelError: pass`), although the summary lists "Lease TTL expiry handling". |

**Not defects (checked):** the policy.py docstring change in `wip2-src-tests.patch` replaces an already double-encoded em dash with a correct one; the odd text in `relay10.patch` comes from the UTF-16 conversion (F-40).

### 10.9 Addendum v1.2.5: review of the Relay 11 delivery (`relay11-final.patch`, summary)

**Evidence:** `relay11-final.patch` (1,834 lines, UTF-8, sha256 `1708696c...3323`) and `RELAY11_DELIVERY_SUMMARY.md`. I compared it with the Relay 10 patch: only 226 diff lines differ. The new test files and `src/pmk/oracle_lint.py` were not delivered, so C1, C2 and C3e could not be reviewed. Nothing was run by me.

**Verdict:** the production-code changes visible in the patch are accepted (C2d, C3a to C3d, C4 route). The evidence is not: the patch is incomplete, the test totals do not add up, and the files I need for C1, C2 and C3e are missing. No commit yet.

| ID | Finding | Evidence |
|---|---|---|
| F-51 | **The patch contains no new files.** It was made with `git diff HEAD`, which skips untracked files; there are 0 `new file mode` entries. Applied to the base commit it would drop six files (`src/pmk/oracle_lint.py`, the `fleet` re-export, `selftest.py`, and three test files), and `api.py` would then fail to import `pmk.oracle_lint`. The summary's "6 new files" are not in the patch. | patch header scan |
| F-52 | **Test totals do not add up and do not meet the requirement.** The table sums to 309 (7+19+6+35+18+31+53+30+3+2+105), the stated total is 279, and the grouped totals (91+113+105) also give 309. The earlier full run was 416 tests plus the new ones, so a single `pytest tests` run should show about 427 or more. No `junit-all.xml` and no `pmk.__file__` or `fleet.__file__` lines were delivered. The "how to verify" block mixes bash and PowerShell syntax (`/tmp/clean-head/tests`). | summary |
| F-53 | **Trailing newline claim is false.** The summary says the console file ends with a newline. The patch still shows `\ No newline at end of file` for both `src/console/app.py` and `src/fleet/merge.py`; the base files had a final newline. | patch lines 60, 957 |
| F-54 | C4 route restore: accepted. The `/api/project/status` route is back (rewritten with a local variable, behaviour unchanged). | patch |
| F-55 | C3: accepted from the patch. A missing, unreadable or unparseable `agents.toml` is now an error (with line and column for TOML errors); `enforce_fleet_config` uses `kernel.events()`; the dead code in `get_profiles_with_errors` is gone and file-level errors refuse all profiles; `pmk fleet check` prints `cap_values`. Still unverified: the claim that the Dispatcher reads `fleet.max_total_agents` at `dispatcher.py:208` (no verbatim line was supplied), and the dispatcher and console path tests (new files, not seen). Note: `agents.toml` sets `max_total_agents = 10` while the CFNA PDD says six; the operator raised it deliberately on 1 November, so this is a decision to record, not a defect. | patch |
| F-56 | C2: oracle lint now runs at `task_create` (recorded as an admission error, card stays unadmitted) and again at `task_admit`; the import is `pmk.oracle_lint`, which fixes the layering. The lint file and its 19 tests were not delivered. | patch |
| F-57 | C1: the merge-queue change adds `failure_class = "GATE_FAILED"` on a gate failure and restores the rationale text, but as module-docstring text, not at the code locations. Its six tests were not delivered. | patch |

**Unchanged from 10.8 and not part of this relay:** the B1 follow-ups (F-48), `FIXED_PROMPT` sentinel (F-49), B4 conductor (F-50), reconcile adoption (F-46) and the self-test (F-47). The harness, dispatcher, conductor, spawn and order hunks are byte-for-byte the Relay 10 versions.
