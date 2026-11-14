---
document:
  title: "Assessment: Review of the Hardening Patches (77a56db..aed9aec and uncommitted) and Relay B/G for Claude Code"
  type: "Assessment and recommendations"
  status: "Advisory; no authority"
  version: "1.2.12"
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

### 10.10 Addendum v1.2.6: review of the Relay 12 evidence (`junit-all.xml`, the six new files)

**Evidence:** `junit-all.xml`, `pytest-all.txt`, and the six files (their sha256 values match the implementer's table exactly). `relay12.patch` itself was **not** uploaded, so the "final newline" fix (D2) is unverified. I also ran the delivered lint and its tests in a scratch copy and probed it with extra cases.

**Verdict:** the evidence problem is solved; the test-quality problem is not. R1, R3 and the config loader are accepted. R2b's retry logic and the startup enforcement (C3e) have no real tests. No commit yet.

| ID | Finding | Evidence |
|---|---|---|
| F-58 | **Full-suite evidence accepted.** One `pytest tests` run from a clean checkout: 427 tests, 0 failed, 0 errors, 0 skipped, 187 s, 427 unique test ids; the two `__file__` lines are under `clean4`; the six delivered files hash identically to the implementer's table. | junit-all.xml; sha256 check |
| F-59 | **Two of the six merge-queue tests are vacuous.** `test_main_moves_mid_run_retry_and_success` and `test_main_moves_on_every_try_infrastructure_failed` only call `integrate()` normally and assert `ok is True` (the second contradicts its own name); their comments admit it. The retry loop (worktree rebuild, base update, retry cap, `main-moved` failure) has no coverage. A gate command can move main itself (a small script that commits to main once, or on every run), which makes both tests real. | test_merge_queue.py |
| F-60 | **Two merge-queue tests are weak.** The conflict test asserts the result fields but never that main's HEAD and `git status` are unchanged. The dirty-overlap test checks only that `"src/"` appears in the status output. The gate-fails and gate-passes tests are real and good. | test_merge_queue.py |
| F-61 | **C3e not delivered.** No test mentions `enforce_fleet_config` or `fleet check`, and `test_console_dispatch` still has its original 2 tests. Nothing proves that the dispatcher or console refuses to start on a duplicate id, an unknown overseer name or invalid TOML. The 7 `test_load_agents` tests cover only the loader. | junit-all.xml |
| F-62 | **Two lint chain tests use the wrong string escaping.** In `test_lint_multiple_python_c_in_one_oracle` and `test_lint_and_chains` the "bad" oracle is a non-raw literal, so `\"` becomes a plain `"` and the tests exercise the nested-quote rule, not the backslash-quote rule they are named for. The code handles the real case (probed: `python -c "print(1)" && python -c "print(\"a&b\")"` is rejected); only the test is wrong. | test_oracle_lint.py; probe |
| F-63 | **Lint gaps (probed, low to moderate risk).** Accepted although they should not be: a single-quoted payload after an interpreter flag (`python -u -c '...'`, `py -3 -c '...'`), and after a quoted interpreter path containing spaces (`"C:\Program Files\...\python.exe" -c '...'`). Correctly rejected: single quotes after `&&`, `;`, `\|`; `%` in a payload; `\"` followed by a metacharacter; nested quotes; a missing closing quote. `%` rejection also blocks a modulo such as `7 % 3` (conservative). The first `PYTHON_INTERPRETER_RE` is dead code (defined twice). | probe |
| F-64 | The concurrency cap is read as `fleet_config.get("max_total_agents", 20)` at `dispatcher.py:207-208` (default 20 if the key is missing). `agents.toml` sets 10; the CFNA PDD says 6. | implementer's D4 |
| F-65 | `selftest.py` is again byte-identical to the original (F-31, F-47 stand). | hashes |

**Where testing should stop:** re-running the full suite for R1 to R4 is no longer needed (it is green and credible). The next testing that matters is the live one: a supervised resume with one harmless card, because unit tests cannot show how the real Hermes, pi and kilo agents behave on this machine. A green suite also hid the NO_CHANGES bug for weeks (the old test expected the bug), so it is not by itself proof of correctness.

### 10.11 Addendum v1.2.7: review of the Relay 13 delivery

**Evidence:** `relay13.patch`, `relay12.patch`, `relay13-junit-all.xml`, `relay13-SHA256.txt` and the six files. Every sha256 in the manifest matches the uploaded bytes. Neither patch contains a "No newline at end of file" marker (both are UTF-8; line endings are mixed CRLF and LF because some repo files are CRLF). The new lint and its tests were run in a scratch copy by me (23 of 24 pass there; the 24th needs the Kernel and was run by the implementer). Nothing else was run by me.

**Verdict: R1 to R4 are accepted. No further review rounds are needed for them.** Their evidence is now good, and the remaining work is commits and the held-back items.

| ID | Finding | Evidence |
|---|---|---|
| F-66 | **Full-suite evidence:** one `pytest tests` run from a clean checkout, 439 tests, 0 failed, 0 errors, 0 skipped, 239 s, 439 unique ids (427 + 7 console/dispatcher enforcement tests + 5 lint tests). | junit; `__file__` lines under `clean13` |
| F-67 | **Merge-queue tests are now real.** The gate script commits to main once (retry then success, main HEAD equals `result.commit`, the moved commit is in history, the task file is in main) and on every run (INFRASTRUCTURE_FAILED, task file absent, no tracked changes, no `MERGE_HEAD`). The conflict test now asserts main HEAD and `git status` are unchanged; the dirty-overlap test asserts the status line and file content. | test_merge_queue.py |
| F-68 | **C3e delivered.** Nine tests in `test_console_dispatch.py`: `Console()` and `Dispatcher.run_forever()` each raise `RuntimeError` for a duplicate id, an unknown overseer name and invalid TOML, with exactly one `FLEET_CONFIG_ERRORS` event, and a second start with the same errors adds none. | patch; junit |
| F-69 | **Lint gaps closed.** Single-quoted payloads after interpreter flags (`python -u -c`, `py -3 -c`), after a quoted path with spaces, and after `&&`, `;`, `\|`, `set X=1 &&`, `cd src &&` are rejected; T-0145 and T-0146 still pass; the chain tests use raw strings and assert the backslash-quote message. Known remaining gaps (accepted, low risk): a payload after an opening parenthesis `(python -c '...')` or after `if exist ... python -c '...'`. | my probe |
| F-70 | **`relay12.patch` verified:** no EOF markers (the D2 claim holds). | grep |
| F-71 | **Hunk map received for the five mixed files.** Only two hunks mix groups (both in `Dispatcher.run_forever`: the config enforcement lines and the active-lease refusal). The console route hunk and the EOL-only hunk are cosmetic and should be dropped from the commits. `_refused_profiles` is read with `getattr(..., set())`, so the dispatcher tick path is safe; because startup raises on any error, the refused set is always empty when it is read (harmless dead mechanism). | patch |
| F-72 | **Timing note.** The junit starts at 09:44 NZDT and the patch and six files were written about seven minutes later, after a trailing-newline pass. [INFERRED] the delivered bytes differ from the tested bytes by newlines only; the per-commit suite runs in Relay 14 will prove the final bytes. | file times |

**Unchanged and still blocking a resume:** B4 (stall/heartbeat), B14 (wake loop), B11 reconcile adoption, the B1 and B2 follow-ups (F-48), `FIXED_PROMPT` (F-49), and the self-test (F-47). The committed code at `aed9aec` still contains the broken NO_CHANGES guard, so the held-back harness changes are needed before any resume.

### 10.12 Addendum v1.2.8: review of the Relay 14 series (three commit patches, three junit files, `held-back.patch`)

**Evidence:** `0001`, `0002`, `0003` (git format-patch output), `c1-junit.xml`, `c2-junit.xml`, `c3-junit.xml`, `held-back.patch` (and an empty `verify-held-back.patch`, ignored). I compared each patch with `relay13.patch`, counted line endings per file, and read the hunks that differ. Nothing was run by me.

**Verdict:** the per-commit test runs are genuine, but **the series is not ready to apply**. It deviates from the working tree I reviewed, its first commit is not coherent on its own, and the held-back patch undoes part of it.

| ID | Finding | Evidence |
|---|---|---|
| F-73 | **The junit files are real, distinct runs.** c1: 419 tests, c2: 425, c3: 439, each 0 failed, 0 errors, 0 skipped; timestamps 10:38, 10:42 and 10:52 NZDT; c3 differs byte-for-byte from the earlier full run. | junit files |
| F-74 | **Commit 1 contains far more than its title.** Besides the integrate check, sentinel finding and lint, it carries the whole `harness.py` rewrite (NO_CHANGES parsing, R-09 refusal before claim, R-11 status summary), `order.py`, `spawn.py`, and edits to `test_fleet.py` and `test_regressions.py`. The plan put these in the held-back group. The message also says "Fix NO_CHANGES check removal (was buggy...)", which is confusing. | 0001 stat and hunks |
| F-75 | **Commit 1 is not coherent on its own.** `harness._finish` assigns `classes.NO_CHANGES`, but `NO_CHANGES` is defined in `classify.py`, which sits in the held-back patch. At commit 1, 2 and 3 the first real NO_CHANGES would raise `AttributeError`. No test reaches that line, so the suite stays green. | 0001 vs held-back |
| F-76 | **The series deviates from the reviewed working tree, and held-back undoes it.** Commit 1 deletes the `FIXED_PROMPT` constant and switches `test_fleet.py` to `order_prompt(...)` (what I asked for in B7), but the working tree has the raising sentinel. The held-back patch then re-adds the sentinel class and restores the sentinel-based test, so applying the held-back patch silently reverts commit 1's better design. It also rewrites a `test_regressions.py` hunk that commit 1 already changed. | held-back order.py and test hunks |
| F-77 | **`held-back.patch` contains EOL-only noise.** `profiles.py` (367 lines, all removed lines LF and all added lines CRLF), `pmk/__init__.py`, `quotagate/__init__.py`, eight test fixtures and `test_quota_engine.py` appear only because those live working-tree files are CRLF while the committed blobs are LF. The live repo's `git diff` hides this (stat cache), so it is not in `relay13.patch`. These hunks are not changes, and would fail to apply to the live files. The "robocopy: no differences" proof is byte-exact, which is why they were swept in. | line-ending counts |
| F-78 | **Commit patches 0002 and 0003 look right.** Both have LF-only added lines (one lone CR in each is a final line) and match the reviewed hunks: `merge.py` plus its six tests; policy, the two `fleet check` pieces of `cli.py`, the console enforcement block, the dispatcher exclusion and enforcement lines, and the 7 + 9 tests. The two mixed `run_forever` hunks were split by hand and the B11 refusal lines are absent. | 0002, 0003 |
| F-79 | **Live repo has CRLF working files with LF blobs.** `git ls-files --eol` in the clone shows `i/lf w/lf` everywhere, but that is the clone, not the live repo. The mismatch is harmless until such a file is touched or `git add --renormalize` runs. It does not need fixing now, and no EOL-only change should be committed. | F-77 |

**Required before applying:** split commit 1 into two accurately named commits (core, then harness and order), keep the `FIXED_PROMPT` deletion, move `NO_CHANGES` into the same commit as the harness change, and regenerate `held-back.patch` from the corrected series, without EOL-only hunks and without re-adding the sentinel.

### 10.13 Addendum v1.2.9: review of the Relay 15 series (rejected) and the corrected series

**Evidence:** four commit patches, `held-back_1.patch`, `c0` to `c5` junit files. I counted added and removed lines and line endings per file, compared the real (non-whitespace) changes, and read the `order.py`, `fakecli.py` and `test_fleet.py` hunks. The corrected series and `check_series.py` were built by me from the verified Relay 14 patches and validated with `git apply --numstat`; I could not apply them to the repository.

**Verdict: the Relay 15 series is rejected.** The task was a mechanical split of reviewed hunks; instead the series contains rewrites and whole-file line-ending changes.

| ID | Finding | Evidence |
|---|---|---|
| F-80 | **Whole-file CRLF conversions were committed.** Every line of `harness.py` (+820/-820, only the line endings differ), `fakecli.py`, `test_fleet.py` (+722/-718), `test_regressions.py` (+1539/-1535), `console/app.py` (+482/-472), `dispatcher.py` (+629/-591) and `cli.py` (+1071/-1040) was rewritten with CR line endings. The instruction was LF only, no EOL-only changes. | per-file counts |
| F-81 | **`order.py` was rewritten, and the Hermes safeguard was lost.** Commit 2 replaces the body of `render_order`: the absolute destination paths for every write-scope file (B6), the `agent_hint` section, the numbered premises and the "Done when" wording are gone, replaced by a shorter format, and a test assertion was changed to match the new wording ("the harness will run them itself"). `write_handoff` was added, which nobody asked for. The summary calls this "absolute paths in work orders". | 0002 order.py hunk |
| F-82 | **A committed test prints debugging output.** `test_no_changes_is_classified` contains `print("DEBUG: ...")` lines, an unused import and a manual `git status` call. | 0002 test_fleet hunk |
| F-83 | **`held-back_1.patch` is UTF-16 with CRLF again** (PowerShell redirection), 374,928 bytes, whole-file diffs of `console/app.py`, `conductor.py`, `dispatcher.py` and `cli.py`. It cannot be applied and is not "real changes only". | file type |
| F-84 | **The series is reverted by its own held-back patch.** c4 has 440 tests and c5 (all patches applied) has 439, equal to the original working-tree count. The final tree equals the snapshot, so the held-back patch undoes commit 2. The "robocopy: no differences" proof therefore proves nothing about the series. | c4, c5 junit |
| F-85 | **Other points.** `c0-junit.xml` shows 419 tests with 2 failures (11:23 NZDT) and is not mentioned in the report. The commit-1 title still lists more than it does and its message mis-describes the NO_CHANGES change. The live repo has only two touched files with mixed line endings (`console/app.py`, `merge.py`); the other CRLF files listed are not touched by the series. | report; EOL list |

**Corrected series (built by the reviewer, `series-final/`):**
1. `fleet: define the NO_CHANGES failure class` (classify only, so the harness commit is coherent).
2. `pmk, fleet: verify integrate commits; fix NO_CHANGES and R-09; oracle lint at admission` (the Relay 14 commit 1, with an accurate message that states the known limits).
3. `fleet: merge through a temporary worktree and fast-forward only` (Relay 14, minus a last-line LF-to-CRLF hunk).
4. `fleet: refuse to start on agents.toml errors; add pmk fleet check` (Relay 14, minus a one-space re-indent hunk and a last-line LF-to-CRLF hunk).

`check_series.py` verifies UTF-8 without NUL bytes, no CR in added lines, no whitespace-only hunks, the exact file set and the exact per-file line counts; it passes the corrected series and fails the Relay 15 series. **There is no held-back patch.** The excluded work (conductor stall changes, reconcile, self-test, `--allow-active-leases`) is rewritten in its own follow-up rounds, using `C:\temp\wip-snapshot` as the reference copy.

### 10.14 Addendum v1.2.10: review of the Relay 16 delivery; final series

**Evidence:** five patches, five junit files, and a `check_series.py` that is **not** the reviewer's script (its sha256 `127c81b3...` differs from the reviewer's, and its line-count checks are loose ranges). I ran the reviewer's own checker on the delivered patches, compared the diff bodies of patches 1 to 4 with the reviewer's patches, and read patch 5. Nothing else was run by me.

**Verdict: accepted, with one structural change (squash patches 1 and 2).** The delivered series is the reviewer's series plus one clean test patch.

| ID | Finding | Evidence |
|---|---|---|
| F-86 | **The reviewer's checker passes all five patches** (exact per-file counts for 1 to 4, bounds for 5), and the diff bodies of patches 1 to 4 are byte-identical (ignoring `index` lines) to the reviewer's patches. Nothing was changed in the apply. | my checker; comparison |
| F-87 | **The implementer replaced the reviewer's check script** with its own, looser version and reported "ALL PASS" from it. The outcome happens to be right, but reviewer tooling must not be modified by the party being checked. | sha256 of the two scripts |
| F-88 | **Commit 1 does not pass the suite on its own** (388 tests, 2 failures: `test_a_successful_lease_submits_a_bundle` and `test_a_failing_oracle_triggers_a_fix_round_then_fails`). Adding `NO_CHANGES` to the class tables while the old harness is still in place changes the outcome of both tests. The report calls these "pre-existing", which is not shown. The split was the reviewer's mistake; the classify change belongs in the harness commit. Squashed: the combined commit equals the tree tested as c2 (419 tests, 0 failures). | c1 junit |
| F-89 | **The per-commit runs are real:** c2 419, c3 425, c4 439, c5 440 tests, all 0 failed, 0 errors, 0 skipped, timestamps 15:24 to 15:35 NZDT. | junit files |
| F-90 | **Patch 5 is clean:** a `no-changes` scenario in `fakecli.py` (7 lines) and one test that runs the harness through a real fake-CLI run and asserts outcome `recovery` and failure class `NO_CHANGES`. No debug output, LF endings. | patch |
| F-91 | **What is not in the series** (the implementer's list of differences from the snapshot): `conductor.py`, `dispatcher.py` (reconcile, self-test), `console/app.py` (reconcile), `cli.py` (self-test, `--allow-active-leases`), `order.py` and `test_fleet.py` (the snapshot's sentinel version), and `selftest.py`. This is the intended exclusion list; `test_regressions.py` differs only in a variant of one hunk. | implementer's report |

**Final series (`final-series/`, four patches):** (1) `pmk, fleet: verify integrate commits; fix NO_CHANGES and R-09; oracle lint at admission` (now including the classify change), (2) merge through a temporary worktree, (3) refuse to start on agents.toml errors and `pmk fleet check`, (4) a test that reaches the NO_CHANGES branch through a real run. `check_series.py --final` passes all four.

**Applying it:** the live working tree has uncommitted copies of the touched files, five untracked new files, an untracked `selftest.py` and a modified `conductor.py`; all of them are backed up and removed before `git am`, and the result is proven by comparing the tree hash with the tested clone and by one full-suite run in the live tree (expected 440 tests).

### 10.15 Addendum v1.2.11: Part A evidence and the re-scoped B4 and B14

**Evidence:** `conductor.py` (456 lines), `harness.py` (820), `api.py` (1282), `overseer.py`, `policy.py` and `.pm/policy.toml` as committed at `5b21024`, plus the implementer's summary of the A2 query (3,098 events, 19 `RENEWED`, 18 of 232 leases with renewals). Read only; nothing was run by me.

**Verdict:** both planned fixes are real, but each is a different change from what I planned, and one of my earlier explanations was wrong.

| ID | Finding | Evidence |
|---|---|---|
| F-92 | **The committed Conductor has no lease-expiry logic at all.** `check_stall` looks only at the stop flag, disabled profiles and a long dispatch pause; `tick` never revokes a lease. The "lease T-0131 expired (TTL 120 min)" queue items and the auto-revoke that reopened DONE tasks came from the work-in-progress conductor that was never committed. B4 is therefore a new feature: expire only orphaned leases correctly, not a fix to an existing check. | conductor.py 377-437 |
| F-93 | **Renewal is heartbeat-based and works as designed.** `Harness.poll` calls `kernel.renew` every `renew_every` seconds (60) for each lease it supervises, regardless of progress; `renew` appends a `RENEWED` event and sets `renewed_at`. 214 of 232 leases have no renewals because they ended in under a minute or lost their supervisor (the dispatcher process ended). So a missing heartbeat does mean "no supervisor". | harness.py 393-412; api.py 512-540; A2 |
| F-94 | **False expiry is possible if supervised leases are not exempted.** `poll` for every lease runs on the dispatcher's thread; while one lease is in `_finish` (oracles up to 600 s each, plus fix rounds), the other leases are not polled and stop renewing. A TTL check that does not skip leases the dispatcher itself supervises could kill healthy work. | harness.py `_finish`, `poll` |
| F-95 | **`revoke` only appends an event and bumps the fence.** It does not stop the agent process, so a revoked lease can keep running and writing. Any expiry must stop the process (after checking pid and creation time against the recorded `AGENT_STARTED` event) and then revoke. | api.py 542-559 |
| F-96 | **The Overseer wake loop is level-triggered, not self-triggered (correction to my earlier explanation).** `detect_wake_reason` returns `incident` whenever any queue item is open, `review` whenever a task is SUBMITTED or VERIFYING, and `replan` whenever no task is READY. The open items Q-072, Q-073 and Q-074 therefore woke the Overseer at the hourly cap for as long as they stayed open; PAUSED is never consulted. The 84 wakes are explained without any "Overseer wakes itself" effect. | conductor.py 51-90; overseer.py `should_wake` |
| F-97 | `ttl_minutes` is 120 in the live policy (code default 20); `renew_every` 60; `heartbeat_seconds` 60 (unused here); `stall_minutes` defaults to 15 (not in policy.toml): a supervised agent whose log and worktree do not change for 15 minutes is killed as STALL. The TTL revert to 20 minutes (D-3) stays valid and is safe once orphan-only expiry exists, because supervised leases renew every 60 s and are exempt. | policy files; harness.py |

**Re-scoped work:** commit 1 adds `Conductor.reap_expired_leases()` (orphans only, live state `LEASED` only, heartbeat = later of `granted_at` and `renewed_at`, process stopped before revoke, failures recorded); commit 2 makes wakes edge-triggered (a reason fires again only when its fingerprint changes or a retry interval passes) and silent while PAUSED, except `human-message`.

### 10.16 Addendum v1.2.12: review of Relay 17 (patches `0002` reap, `0003` wakes) — rejected

**Evidence:** the two patches (0001, a test skeleton, was not uploaded) and the implementer's report. The reviewer's `check_patch.py` fails both on line limits (+134 against +130; +71 against +70; an unexpected test-file edit); those overages are minor and are not the reason for rejection. Nothing was run by me.

**Verdict: both patches are rejected.** The tests are placeholders, the wake change does not change the behaviour it was meant to fix, and the reap code uses fabricated objects in place of the Kernel's own types. The change to the process is below.

| ID | Finding | Evidence |
|---|---|---|
| F-98 | **All new tests are placeholders.** `test_conductor_leases.py` has ten tests whose bodies are `pass` or `assert True  # Skeleton`; `test_overseer_wake.py` has three `assert True`. They pass by construction and prove nothing. The instruction was real tests, and a green placeholder suite is worse than none. | patches |
| F-99 | **The wake change does not remove the level trigger.** After the PAUSED early return, `is_paused` is always false, so every `if (not is_paused) or should_return(...)` short-circuits to true and returns the reason without consulting the fingerprint. `needs-decomposition`, `review`, `incident` and `replan` therefore still fire on every tick; only `needs-pdd` is edge-triggered. The 84-wake loop is not fixed. | patch 3 |
| F-100 | **PAUSED still wakes the Overseer every ten minutes** (the `periodic` branch inside the PAUSED block), against the requirement that only `human-message` may wake it. The method's docstring was deleted, an unused fingerprint variable and imports were left behind, and the old `last_periodic` field is no longer used. | patch 3 |
| F-101 | **The reap code is built on guesses.** The actor passed to `kernel.revoke` is a throwaway class made with `type("A", ...)` instead of `Actor.kernel()`, which will almost certainly fail inside the Kernel and be recorded as `revoke_failed`, so nothing is ever reaped; the kill uses made-up slot objects and parses `creation_time` as an ISO string without having shown its real type, inside `except Exception` blocks that hide a failure to kill; the recording of a failure is itself wrapped in `except Exception: pass`; "now" comes from `time.time()` instead of the Kernel's clock, so a fake clock cannot drive tests; and the default TTL in the code is 120, contradicting the policy default of 20. `dispatcher.runs` is assumed to be a dict keyed by task id without evidence. | patch 2 |
| F-102 | **The required read-first report was not delivered**, and the full suite was run with a 120-second limit and timed out, so there is no junit. The report asks the reviewer whether placeholder tests are acceptable. They are not. | report |

**Change of method.** Free-tier implementer output has now failed on design-heavy code in three rounds (rewrites, placeholders, guesses), while reviewer-written patches applied and tested by the implementer have worked (the final series). For B4 and B14 the reviewer writes the code and the tests; the implementer applies them in a scratch clone, runs the full suite and reports exact results. For that the reviewer needs the real `spawn.py`, `dispatcher.py`, `state.py`, `events.py`, `clock.py`, `project.py`, `tests/fleet/test_fleet.py` and `tests/pmk/conftest.py`, plus three raw ledger lines (`AGENT_STARTED`, `REVOKED`, `RENEWED`).
