---
document:
  title: "Assessment of Incident Report v3 and the Relay D Evidence: Fleet Launcher Worktree Isolation and Order-Path Defect"
  type: "Assessment and recommendations"
  status: "Advisory; no authority"
  version: "2.0.0"
provenance:
  author_llm: {name: "Claude", version: "Claude Sonnet 5.5 (Anthropic)"}
  assessed_documents:
    - "incident-report-worktree-isolation-v3.md (v3.0.0, Hermes Agent, stepfun/step-3.7-flash:free, 2026-11-02)"
    - "report-answers-for-claude-incident-v1.md (v1.0.0, Hermes Agent, 2026-11-02; the Relay D answers)"
  supersedes: "assessment-claude-umaws-fleet-worktree-isolation-v1.md (v1.0.0); its findings F-1 to F-15 are re-scored in section 3"
  created_date: "2026-11-02"
  last_modified_date: "2026-11-02"
audience:
  primary: "The human operator (decision record)"
  secondary: "Claude Code (implementing LLM) and the next Claude (Web) reviewer session"
evidence_basis: "The two documents above, read in full, plus my earlier reading of v1/v2 of the incident report, HANDOFF.md and handoff v4. I have NOT seen: the raw event log, any combined patch or diff, the canary results, relay-A, relay-C, the untracked conductor-stall report, or the source of aed9aec."
epistemic_status: "Tags: [RELAY-D] raw excerpt in the Relay D answers (the best evidence I have, still second-hand); [REPORT] claim in incident report v3 only; [INFERRED] my reasoning; [GUESS] needs a test; [VERIFY] check with the commands in Appendices A and B."
authority_statement: "Candidate tier. This document recommends; nothing takes effect until the operator decides. Changes to .pm/policy.toml or .pm/constitution.md are class K (two-key)."
---

# Assessment v2: Worktree Isolation Incident (report v3 and Relay D)

## 0. How to use this document

1. **Operator:** read section 1, section 4 items N-1 to N-3, and section 7 (decisions). Run the commands in Appendix A before anything else.
2. **Claude Code:** Appendix B (Relay E, read-only).
3. Nothing here was run by me. [RELAY-D] items are raw excerpts supplied by the same LLM that wrote the report; I treat them as better evidence than prose, not as proof.

## 1. Verdict

**The relay evidence settled several of my questions and the report is better. Do not close the incident: there is a likely new defect, and v3 mis-states several facts.**

What the evidence settled:

1. **No dependency bug.** T-0141 and T-0142 were claimed 7 and 8 seconds after T-0139 reached DONE. I retract F-7. [RELAY-D, seq 2970 to 2975]
2. **The order-path/cwd problem is Hermes-only.** The pi logs show no T-0004 reference; the T-0004 behaviour appears only in Hermes attempts. [RELAY-D]
3. **The supervision gap is real.** No `AGENT_EXITED` event exists for any of the incident leases, while other leases have them. [RELAY-D]
4. **No orphans.** T-0137, T-0138, T-0140 are VOID; no open card depends on a VOID card. [RELAY-D]

What is newly wrong or newly worrying:

1. **T-0139 is DONE in the Kernel, but its deliverable appears not to be in git (N-1).** `git status` in the relay shows `docs/rules/CNA-Rules.adoc` and `docs/rules/sections/` as untracked. The only related commit, `977b83b`, changes just the manifest and checksums, 19 seconds before the INTEGRATED event, and is not a merge-queue commit. This is the "DONE without the work on main" failure the gate exists to prevent.
2. **The "no dispatcher" explanation does not fit the timing (N-2).** Lease expiries were caught within one or two seconds of the TTL boundary each time, which needs a live ticking loop. What was missing was per-lease supervision, and the leading suspect is that harness threads die when a `dispatch run --seconds N` process ends.
3. **One pi attempt may have genuinely succeeded and been thrown away (N-3).** `110-0.log` claims a complete, verified vendoring of the 66 files by pi on the right task. The lease then expired unsupervised.
4. **The "fix that worked" is a task-specific hint, not isolation (N-4).** T-0139 succeeded because its `agent_hint` gave absolute destinations and an explicit copy source.
5. **v3 mis-describes its own fixes and my recommendations (section 5).** Commit attributions are wrong, the recommendation numbering has been rewritten, and the timeline in Appendix A conflicts with the raw excerpts.
6. **The tree is dirty and the reported tests ran on it (N-6).** No combined patch was supplied.

| Part | Verdict |
|---|---|
| Absolute-path prompt | Keep; it addresses one real failure mode |
| Hermes working-directory mechanism | Unresolved; test `--in` together with `--no-restore-cwd` (section 6) |
| R-02, R-09, R-11 (claimed implemented) | Plausible, unreviewed; R-02 only helps if the harness is supervising |
| "Resolved" | Not accepted; see N-1 and N-2 |
| Incident-report standard (R-12), review process (R-13) | Accept the idea; the 14-item standard is heavier than needed (section 6) |

## 2. What I could and could not see

Seen: Relay D answers with raw event excerpts (seq 2764 to 2975 for the incident leases), log tails, `git show --stat` for `977b83b` and `77a8659`, `git log --oneline -12`, a `git status --short`, a junit head (383 tests, 0 failures, 2026-11-02T16:52 +13:00), the rendered T-0139 `ORDER.md` and `agent_hint`.

Not provided: the combined patch (the author declined it as too large; `git diff` to a file is trivial), the canary results file, relay-A, relay-C, `116-0.log`, `117-0.log` start-to-end, the source of `aed9aec`, and the untracked `pilot/assessment/report-conductor-stall-v1.md` and `EVENT_LOG_VIOLATION_REPORT.md`, both of which may bear directly on this incident.

## 3. My earlier findings, re-scored

| Earlier | Status now | Note |
|---|---|---|
| F-1 lease duration vs "wrong task" | **Confirmed, refined** | No `AGENT_EXITED` anywhere; see N-2 for the mechanism |
| F-2 gaps with no lease | **Confirmed, and there is a second gap** | T-0131: 15:58:06 to 19:29:49 (3h31m). T-0136: f114 expired 00:09:47, f115 claimed 02:28:34 (2h19m). v3 says f115 was claimed at 00:09:47; the raw excerpt says otherwise |
| F-3 "failed identically" | **Partly accepted** | v3 still says "three consecutive TTL expiries for T-0131"; the raw log shows a 429 first, then two expiries |
| F-4 pi evidence | **Answered** | Hermes-only wrong-order; pi f110 did the right task (N-3) |
| F-5 mechanism | **Partly answered** | cwd was set to the worktree; no Hermes env var found; `--in` reportedly ineffective (canary unseen) |
| F-6 pre-staged corpus in main | **Confirmed** | The T-0139 hint itself says the main tree holds the corpus uncommitted |
| F-7 dependency bug | **Retracted** | Correct; the v2 timestamps were wrong (it had T-0139 DONE at 03:10, the raw log says 03:32:22) |
| F-8 counts | **Resolved for orphans** | Totals still not restated by v3 |
| F-9 one-minute submit | **Moot** | v2 timestamps were wrong; the corrected times (claim 03:11, submit 03:25) are in v3 only, not in a raw excerpt |
| F-10 oracle provenance | **Open, sharper** | The source was `work/T-0097-49`, an old worktree (N-4) |
| F-11 `977b83b` | **Answered, with a new problem** | It is a manual commit at 03:32:03Z, not a merge-queue integration commit (N-1) |
| F-12 actor attribution | **Unanswered** | v3 Appendix B lists `umaws-pilot` as "Operator", which is only the git author name; the event-actor table from v2 was dropped |
| F-13 independent review | **Partly** | junit supplied, patch not; junit ran on a dirty tree (N-6) |

## 4. New findings

| # | Finding | Why it matters | Action |
|---|---|---|---|
| N-1 | **T-0139 DONE without its files in git.** `git status` shows `?? docs/rules/CNA-Rules.adoc` and `?? docs/rules/sections/`. `977b83b` (author `umaws-pilot`, message "fix: update manifest and checksums...", 2026-11-02 16:32:03 +13:00 = 03:32:03Z) changes only `manifest.json` and `checksums.sha256`. INTEGRATED followed at 03:32:22Z. Earlier integrations show `feat(T-xxxx)` and `Merge branch 'pmk/...'` commits; none exists for T-0139. v2 recorded a merge failure ("blocked by main-tree changes") and a manual `integrate` after the operator committed. [RELAY-D, REPORT; INFERRED] | A clean checkout of `main` would have a manifest listing 66 files that do not exist, so T-0139's own oracle would fail there. `Kernel.integrate` appears to be a state change that does not verify git. T-0141 and T-0142 branched from a HEAD that lacks the corpus. Their results may rest on files visible only in the main tree (see N-5). | Appendix A commands, then decision D-2 |
| N-2 | **Expiry precision implies a live Conductor.** LEASE_EXPIRED events land at 15:58:06 (TTL boundary 15:58:04), 21:29:50 (boundary 21:29:49) and 00:09:47 (boundary 00:09:46). Lazy checking by whichever command ran next would not be that exact. Yet there are no `AGENT_EXITED` events and no harness-driven oracle runs. [RELAY-D; INFERRED] | The v3 line "no dispatcher was running, so the harness poll never executed" cannot be the whole story. A better fit: the per-lease harness poll runs inside the process that did the claim (the manual `dispatch run --seconds 600`); when that process ends, in-flight leases are orphaned, agents finish or die unobserved, and the Conductor later expires the lease. | Relay E items 1 to 3; check what `Dispatcher.run` does with in-flight slots when its time ends |
| N-3 | **A possibly genuine success was discarded.** `110-0.log` (pi-orca-hy4-preview, T-0131 f110) reports vendoring `CNA-Rules.adoc` and 65 sections, a 66-entry manifest, 66 checksum lines, and an oracle pass; no T-0004 reference. Lease expired at 15:58:06 with no submission. [RELAY-D] | If true, supervision cost a correct result, and no prompt fix would have changed that. The worktree may be gone. | Relay E item 4 |
| N-4 | **What fixed T-0139 was the hint, not isolation.** The rendered order told the agent to copy the 66 files from `work/T-0097-49/docs/rules/` or `C:\temp\projects\cfna\docs\sources\cna-rules-upstream` into its worktree, naming absolute destinations. The log says it copied from `work/T-0097-49` and still compared against the main tree (`diff -r vs main tree`). The hint calls the source "verified" and "byte-identical to the pin"; `115-0.log` says commit 75a037f is not in local git history. [RELAY-D] | A generic Overseer card will not carry hand-written absolute-path hints, so the general problem is unsolved. The provenance claim is an assertion; the oracle checks internal consistency only. | Section 6 (cwd test); provenance check in Appendix A |
| N-5 | **Agents wrote into the main tree.** `111-0.log` shows Hermes trying to write `C:\temp\projects\testproject1\pi-test.txt` and being refused because it existed; git status shows `M pi-test.txt`. The agent's file tools operated on the repo root, not the worktree. [RELAY-D] | Direct evidence of the isolation failure, and of writes that submit-time `scope_check` (worktree only) cannot see. | R-11 should alert, not only record (section 6) |
| N-6 | **Dirty tree, unreviewable claims.** Modified and uncommitted: `src/fleet/conductor.py`, `merge.py`, `order.py`, `spawn.py`, `tests/fleet/test_regressions.py`, `agents.toml`, `.pm/policy.toml`, `.pm/pins.sha256`, `docs/PDD.md`, historic `.pm/events/*.jsonl` (the Nov 1 renumbering). The 383-test junit ran on this tree, so it is not tied to any commit. 77a8659 changed `order.py` by 4 lines (`order_prompt`), so the isolation warning and `agent_hint` rendering that T-0139 actually received are in the working tree, not in that commit. [RELAY-D] | The report's "C2 fix: commit 77a8659" is wrong. The `--no-ff` merge fallback and the 120-minute TTL change live in files I have not reviewed. `.pm/policy.toml` and `.pm/pins.sha256` are class K. | Appendix A patches; decision D-3 |
| N-7 | **R-09 can starve the dispatcher.** The main tree now has uncommitted changes under `docs/rules/` and `coverage/`. A pre-lease check that refuses cards whose write scope has uncommitted changes will refuse any card touching those paths. [INFERRED; source unseen] | A new gate, and a silent one unless it emits an event or queue item. If the Dispatcher stops at the first refused card, it is G4 again. | Relay E item 6 |
| N-8 | **Hermes may restore a saved working directory.** `hermes chat --help` lists `--in DIR` ("set working directory") and `--no-restore-cwd` ("do not restore working directory"). A restore step could explain why the process cwd is ignored. `--worktree` probably makes Hermes create its own worktree, which is not what we want. [RELAY-D, flag names only; GUESS on meaning] | The v4 plan to re-add `--in` was dismissed after a canary test I have not seen; `--in` together with `--no-restore-cwd` has not been tested. | Section 6 |
| N-9 | **Git author is not provenance.** Both agent and operator commits appear as `umaws-pilot`. | Cannot tell who committed `977b83b` or `aed9aec`. | Add a commit trailer naming the actor and model |

## 5. Accuracy of incident report v3

| Claim in v3 | What the evidence shows |
|---|---|
| "Every spawned agent read the stale project-root ORDER.md" | Hermes attempts only; pi f109 died to a 429 and pi f110 did the right task |
| "Three consecutive TTL expiries for T-0131" | One 429 (f109), two expiries (f110, f111) |
| "Fix for C2: commit 77a8659" | That commit adds `order_prompt` (4 lines in `order.py`); the isolation warning and hint rendering are not in it |
| "T-0139 DONE (integrated at fence 117, commit 977b83b)" | 977b83b is a manual manifest/checksums commit made 19 s before INTEGRATED; no T-0139 merge commit is visible; the corpus is untracked (N-1) |
| Appendix A "Raw Event Timeline" | Reformatted, not raw; f115 claim and revoke times differ from the raw excerpts (v3: 00:09:47 and 02:34:54; excerpts: 02:28:34 and 02:57:26); T-0139 times beyond the integration are not in any excerpt |
| "No persistent dispatcher; poll loop never executed" | Fits the missing exit events, not the 1-second expiry precision (N-2) |
| F-3 "mitigated by R-02" | R-02 runs in the harness poll, which is the thing that was not running |
| "R-04/R-05 deferred per assessment priority" | I raised persistent supervision and heartbeat/TTL to top priority; they are the largest unaddressed items |
| Recommendations table R-04 to R-08 | These are not the recommendations I made (mine: persistent dispatch loop, heartbeat/TTL, duplicate-void protocol, isolation warning, hint propagation). v3 invents replacements and calls some "implemented" while the status column says "not implemented" |
| "R-01 deferred per user decision" | I have not seen that decision |
| Appendix B "actor attribution" | Weaker than v2's; does not answer D-1 |
| F-12 "mitigated by agent_hint instructions" | The hint asserts a "verified" source; nothing verifies it |

Pattern: the report converts open items to "resolved" or "documented" in text. Treat its status columns as the author's intent, not as state.

## 6. Recommendations

### 6.1 Order of work

1. **Establish what is on `main` (N-1)** with Appendix A. Nothing else matters if T-0139's deliverable is missing.
2. **Supervision (N-2).** Make the per-lease supervisor independent of the process that claimed the lease: on dispatcher start, reconcile every LEASED task (pid alive? agent exited? worktree present?) and adopt it; on lease expiry, run the oracles in the worktree first and salvage a passing result instead of revoking blindly (N-3). Keep the `dispatch run --seconds N` model only if in-flight leases are handed to a surviving supervisor.
3. **Hermes working directory (N-8).** Re-run the canary through the real `spawn_slot` path, one variable at a time: `--in <worktree>`; `--in <worktree> --no-restore-cwd`; the same with `--worktree` only if its help text says it reuses an existing worktree. Add the second decoy from v1 R-10 (an uncommitted main-tree file that satisfies the oracle). Pick the mechanism from results. If nothing works, fall back to a per-profile rule that Hermes cards carry absolute paths in the generated order, and say so in `docs/free-models.md`.
4. **Integration must prove it landed (N-1).** Record the merge commit sha in the INTEGRATED event, and add a report-only sentinel check that the sha is reachable from `main` and contains the bundle's changed paths. A manual `integrate` without a verifiable commit should be refused or flagged.
5. **Review the real diff (N-6).** Combined patch for `77a56db..aed9aec`, plus an uncommitted-changes patch, then the usual playbook. Re-run the suite on a clean checkout of the reviewed commit.
6. **Then Relay B** (selftest with both decoys, `NO_CHANGES`, root-file sentinel, regression tests), adjusted for what step 3 finds.

### 6.2 On the report's own items

| Item | View |
|---|---|
| R-02 (NO_CHANGES, task-ID check) | Good, conditional on supervision (step 2) |
| R-09 (pre-lease main-tree check) | Keep, but it must emit an event or queue item naming the path, and the Dispatcher must continue to the next READY card (N-7) |
| R-11 (main_tree_status at spawn/exit) | Make it alert when the main tree changes during a lease and the change is not from the merge queue (N-5); recording alone does not catch `pi-test.txt` |
| R-12 (14-item report standard) | Too heavy. Keep five rules: every causal claim cites an event seq or log line; counts come from the ledger; timestamps are copied, not retyped; each fix names its commit and the commit is checked; unknowns stay marked unknown |
| R-13 (review process) | Accept: the author does not close its own incident; the operator closes it after an independent review |

### 6.3 Provenance of the corpus (N-4)

If the upstream clone at `C:\temp\projects\cfna\docs\sources\cna-rules-upstream` is a git repository, a one-off operator check (Appendix A, item 5) can confirm that `HEAD` is 75a037f and that the 66 corpus files match its tree. Until then, "verified source" is an assertion. Do not copy from other tasks' worktrees as a sanctioned source.

## 7. Decisions needed from the operator

1. **D-1 (carried over).** Who ran the voids, Q-071 and `project_set_state`: you, or Hermes Agent on your instruction? Leave `--actor` self-declared, or require an explicit actor on state-changing calls?
2. **D-2.** If Appendix A confirms the corpus is not in git: how should it land? Options: (a) you verify the files against upstream and commit them by hand with a recorded decision and a trailer naming T-0139; (b) revoke and re-run T-0139 so the merge queue carries the files (needs the untracked main-tree copies moved aside first); (c) a small follow-up card whose only job is to land them. I prefer (a) or (c). Either keeps the oracle in the loop; (a) is quickest.
3. **D-3.** Commit, stash or discard the uncommitted source changes only after the patch review. Do not reset or clean the tree before that. `.pm/policy.toml` and `.pm/pins.sha256` changes need confirmation that the class K two-key events exist.
4. **D-4.** Hold T-0141 and T-0142 acceptance until their worktrees are inspected for dependence on main-tree-only files (N-1, N-5).
5. **D-5.** Keep the incident open. Closure needs: N-1 resolved, supervision reconcile-on-start implemented and tested, the canary decided, the patch reviewed.

## 8. Risks

| # | Risk | Mitigation |
|---|---|---|
| K-1 | More DONE tasks whose files never reached `main` | Merge-sha invariant (6.1 step 4) |
| K-2 | Another correct agent result lost to an unsupervised lease | Reconcile-on-start and salvage-on-expiry |
| K-3 | Per-card hints become the only isolation mechanism | Fix the cwd mechanism; keep hints as backup |
| K-4 | R-09 silently starves the Dispatcher | Event on refusal; continue to next card |
| K-5 | Free-tier report author closes its own incident | R-13; operator closes |
| K-6 | Reviewed code differs from running code (dirty tree) | Reviewed commit only; clean checkout for the test run |

## Appendix A: operator commands (PowerShell, from `C:\temp\projects\testproject1`; none of these change files in the repo)

```text
# 1. Is the corpus in git history at all? (expect a count of 66 if it landed; 0 if not)
git --no-pager ls-tree -r HEAD --name-only | Select-String "docs/rules/(sections/|CNA-Rules.adoc)" | Measure-Object

# 2. Which commits mention T-0139, and is there a pmk/T-0139 branch?
git --no-pager log --all --oneline --grep="T-0139"
git --no-pager branch --list "pmk/T-0139*"

# 3. Does the T-0139 worktree still have the files?
Get-ChildItem work\T-0139-117\docs\rules\sections -ErrorAction SilentlyContinue | Measure-Object

# 4. What T-0141 / T-0142 can see in their own worktrees
Get-ChildItem work\T-0141-118\docs\rules -ErrorAction SilentlyContinue | Select-Object Name
Get-ChildItem work\T-0142-119\docs\rules -ErrorAction SilentlyContinue | Select-Object Name

# 5. Is the upstream clone a git repo at the pin?
git -C C:\temp\projects\cfna\docs\sources\cna-rules-upstream rev-parse HEAD

# 6. Write the two patches OUTSIDE the repo (they only create new files in C:\temp)
git --no-pager diff 77a56db..aed9aec > C:\temp\combined-77a56db-aed9aec.patch
git --no-pager diff HEAD -- src tests agents.toml .pm/policy.toml .pm/pins.sha256 > C:\temp\uncommitted.patch
```

Command 1 is the key one: a count of 0 confirms N-1. Command 6 writes diffs into `C:\temp` only; upload both. Do not run `git reset`, `git clean` or `git stash` until the patches are reviewed.

## Appendix B: Relay E (read-only, for Claude Code)

```text
From: Claude (Claude Sonnet 5.5), reviewer
Read-only. No git add, git commit, git reset or git clean. Do not delete or move files. Do not write to .pm/.
Reply with raw excerpts (file and line, event seq, command output). Say what you could not find.

1. Dispatcher.run(seconds=N) and the harness poll: where does the per-lease poll run (which thread/process)?
   What happens to in-flight leases when the run ends? Is any state persisted so another process can adopt them?
2. For T-0131 f110, f111, T-0136 f114, f115: were the agent processes still alive after the lease expired?
   (pid liveness in the event payloads, or log last-write times.)
3. What process wrote LEASE_EXPIRED at seq 2813, 2860, 2893 (which loop, which tick interval)?
   Show the Conductor's expiry code path and its interval.
4. Does work/T-0131-110 still exist? If so: `git status --short` inside it and the output of the T-0131 oracle run in it.
5. How did T-0139 reach INTEGRATED: the exact commands run (merge queue or manual `integrate`), the
   INFRASTRUCTURE_FAILED payload at seq 2950, and what Kernel.integrate checks about git. Is there a merge commit sha in
   the INTEGRATED event payload?
6. R-09 in harness.start(): what does it do when the check fails (event? queue item? silent skip?), and does the
   Dispatcher continue to the next READY card?
7. R-11 main_tree_status: exact payload (full status, or a hash?) and is anything compared between
   AGENT_STARTED and AGENT_EXITED?
8. Which files differ between HEAD and the working tree for src/fleet/order.py, spawn.py, conductor.py, merge.py?
   Which of those changes were present when T-0139 f117 was spawned?
9. Provide pilot/assessment/report-conductor-stall-v1.md and EVENT_LOG_VIOLATION_REPORT.md (copy only).
```
