---
document:
  title: "Assessment of Incident Report: Fleet Launcher Worktree Isolation and Order-Path Defect (v2.0)"
  type: "Assessment and recommendations"
  status: "Advisory; no authority"
  version: "1.0.0"
provenance:
  author_llm: {name: "Claude", version: "Claude Sonnet 5.5 (Anthropic)"}
  assessed_document: "incident-report-worktree-isolation-v2.md (v2.0.0, Hermes Agent, stepfun/step-3.7-flash:free, 2026-11-02)"
  created_date: "2026-11-02"
  last_modified_date: "2026-11-02"
audience:
  primary: "The human operator (decision record)"
  secondary: "Claude Code (implementing LLM) and the next Claude (Web) reviewer session"
evidence_basis: "The v2 report, read in full; incident-report-order-path-v1.md; HANDOFF.md (2026-11-01); my earlier assessment and handoff v4. I have NOT seen the raw event log, any agent log, the diffs of commits 77a8659 and 977b83b, the current agents.toml, or the three evidence files the report cites (relay-A, relay-C, canary results)."
epistemic_status: "Tags: [REPORT] claimed by the assessed report, not checked by me; [OBSERVED] visible in the documents I was given; [INFERRED] my reasoning; [GUESS] needs measurement; [VERIFY] check against files or events before relying on it."
authority_statement: "Candidate tier. This document recommends; nothing takes effect until the operator decides. Changes to .pm/policy.toml or .pm/constitution.md are class K (two-key)."
---

# Assessment: Worktree Isolation and Order-Path Incident Report v2

## 0. How to use this document

1. **Operator:** read section 1 (verdict), section 5 (what the evidence supports) and section 8 (decisions).
2. **Claude Code:** section 7 and Appendix A (Relay D, read-only evidence request).
3. Nothing here has been run. Every statement about the repo comes from the report and is tagged [REPORT] or [VERIFY].

## 1. Verdict

**Accept the incident as real, accept the fixes as sensible defence in depth, do not accept the causal story or the "resolved" status yet.**

v2 is a clear improvement on v1. It fixes the timeline contradiction I flagged, explains where the stale root `ORDER.md` came from, supplies actor attribution, and admits a second failure mode (the agent seeing the main tree). But five problems remain:

1. **The fix is unproven.** One task (T-0139) succeeded after at least six changes landed together (absolute-path prompt, isolation warning, `agent_hint`, root file rename, main-tree commit, a rewritten task). Nothing shows which change mattered, and n=1.
2. **The report still conflates two things:** why tasks ended `BLOCKED` (wrong order or wrong tree, plausible) and why each failure cost two hours (a lease that nobody was supervising). It still dismisses the second without evidence.
3. **Two of the cited "identical" failures were not failures of that kind.** T-0131 attempt 1 died to a 429; T-0136 attempt 1 and T-0139 attempt 1 were operator revocations after under 10 minutes.
4. **There are unexplained anomalies** that could indicate a real Kernel defect: T-0141 and T-0142 were leased before their dependency T-0139 was DONE, and task counts do not add up (section 4).
5. **Governance:** the same LLM did the diagnosis, the code changes, the voids and recreation, the decision record and the report. Its recorded actors (`human/operator`, `kernel`) do not tell us who actually acted.

| Part of the report | Verdict |
|---|---|
| Absolute-path prompt (`order_prompt`) | Keep; correct but not sufficient on its own (the report's own log 114 shows it was read correctly and the task still failed) |
| Isolation warning and `agent_hint` in `ORDER.md` | Keep as defence in depth; it is advice to the agent, not enforcement |
| Rename of the stale root file | Keep; add a harness rule so it cannot recur (R-01 below) |
| "Primary stalling mechanism: yes" | Not established; see section 5 |
| "Resolved" | Premature; T-0141/T-0142 in flight, fix unattributed |
| R-02 (parse agent prose against the diff) | Replace with cheaper structural checks |
| R-04, R-05 (supervisor, TTL) | Raise priority; these explain the lost hours |
| R-09 (pre-integration main-tree check) | Reframe as a pre-lease check |

## 2. What I could and could not see

Read in full: the v2 report, v1 report, HANDOFF.md, my assessment and handoff v4.

Cited by the report but not provided to me: `relay-A-evidence-report-v1.md`, `relay-C-phase0-census-v1.md`, `step1-canary-test-results.md`, logs `111-0`, `113-0`, `114-0`, `115-0`, and any log for T-0139. The report's central claims rest on these. Until I see them, I treat the report as a lead, not as evidence.

## 3. What v2 improves

1. The timeline is now self-consistent for T-0131: attempt 1 revoked at 13:57 (429), attempt 2 expired 15:58, attempt 3 expired 21:29 (120 min after a 19:29 claim). v1 had attempt 2 and 3 expiring at the same instant.
2. The root `ORDER.md` origin is explained: T-0004 fence 5 was claimed with `worktree=""`, so the harness wrote the order into the repo root. [REPORT; seq 319]
3. Actor attribution (Appendix B) answers the question I raised in v4.
4. The "agent verified against the main tree" mechanism is a specific, testable claim, which v1 lacked.
5. It records which recommendations are implemented and which are not.

## 4. Findings

| # | Finding | Why it matters | Action |
|---|---|---|---|
| F-1 | **Lease duration contradicts the "wrong task" story.** Log 111 reportedly shows the agent doing T-0004 (write one file, run one command). That finishes in minutes, yet the lease ran the full 120 min. The same happens at fence 114 (agent says "Done", lease still expires at TTL). The report says the harness re-ran the oracle "only after the 120-minute TTL." [REPORT] | If a harness process were alive, agent exit would trigger oracles and a fast attempt failure. A 120-minute wait suggests nothing was polling the lease. | Relay D items 1 to 3 |
| F-2 | **3.5-hour gap with no lease.** T-0131 attempt 2 expired at 15:58; attempt 3 was claimed at 19:29. T-0131 had attempts left. [REPORT] | Points to no dispatcher running (or a backoff), not to a prompt defect. This is the point I raised in v4 doubt 1; v2 does not address it. | Relay D item 3 |
| F-3 | **"Failed identically" is wrong.** T-0131 f109: 429 after 23 min. T-0136 f113: revoked by the operator after 9 min. T-0139 f116: revoked after 7 min. Only f110, f111, f114, f115 expired by TTL. [REPORT, sections 2.1 to 2.3 and Appendix C] | Impact numbers ("3 tasks consumed", "7.5 lease hours") are loose. By the report's own table the TTL waste is 8 hours across four leases, plus the 3.5-hour idle gap. T-0139 was not "consumed"; it finished. | Correct in v3 of the report |
| F-4 | **Profile evidence is still missing for the pi attempts.** T-0131 f110 was `pi-orca-hy4-preview` and expired at TTL. Only Hermes logs are quoted. | If pi also ignored its cwd the problem is general; if not, f110 had another cause. Unresolved since v4. | Relay D item 4 |
| F-5 | **The mechanism is asserted, not shown.** "The agent's runtime context resolved files from the main tree." No `AGENT_STARTED` argv or cwd, no environment, no Hermes setting is cited. The report also says the canary showed Hermes ignores `--in` and uses its "configured project root." [REPORT] | If true, re-adding `--in` (my v4 decision with the operator) will not help. A Hermes terminal working-directory setting or environment variable may be the real lever. [GUESS; check `hermes chat --help`, Hermes config and docs] | Relay D item 5; canary re-run in section 7 |
| F-6 | **The "pre-staged corpus" was probably real, in the main tree.** HANDOFF.md says an OpenCode session adopted the full 66-file corpus (Q-068) directly, and the report says the main tree held uncommitted `docs/rules/` files. The agent may have been truthful that the corpus existed; it was in the wrong place. [INFERRED] | The cause is an out-of-band edit to files that a Fleet task owns. That also explains why integration of T-0139 was blocked by main-tree changes to `manifest.json` and `checksums.sha256` (R-09). Prompt warnings treat the symptom; the main tree should not hold uncommitted edits inside a READY card's write scope. | R-09 reframed (section 6) |
| F-7 | **Possible dependency-enforcement bug.** T-0141 and T-0142 have `depends_on: T-0139`. They were leased at 03:06 (fences 118, 119); T-0139 was submitted and verified at 03:06 and reached DONE at 03:10. [REPORT, sections 2.3 and Appendix C] | Either dependency counts as satisfied at SUBMITTED/VERIFIED, or the timestamps or the `depends_on` data are wrong, or a dependency check failed. This is Appendix D item 3 of my assessment, now with a concrete case. | Relay D item 6 |
| F-8 | **Task counts do not reconcile.** Section 4.3: 5 DONE + 134 VOID + 1 SUBMITTED + 4 READY = 144. Section 10: 6 + 134 + 2 = 142, READY 0. T-0137 and T-0138 (dependents of T-0136) and T-0140 are never accounted for. [REPORT] | If T-0136 is VOID, T-0137/T-0138 are orphaned dependents (my G2). Orphans stay BLOCKED forever and look like "gated" work. | Relay D item 7 |
| F-9 | **T-0139 submitted within about a minute of its claim.** Claimed 03:06:17 (fence 117), "submitted 03:06Z", verified 03:06Z. [REPORT] | A 66-file vendoring job is plausible in a minute only if the agent copied files. From where? If the `agent_hint` told it to copy from the main tree, the isolation warning and the hint pull in opposite directions, and the "fix" works by a different route than the report says. If the timestamps are rounded, say so. | Relay D item 8 |
| F-10 | **T-0139's oracle checks consistency, not provenance.** It confirms the manifest lists at least 66 files, the pin string matches, and each listed file hashes to the manifest value. [REPORT, Appendix C artifacts] | An agent can write files and a matching manifest and pass. Nothing ties the content to upstream commit 75a037f. Acceptable for this card only if the source was the already-adopted corpus; say so. | Optional: add a check against the upstream tree if it is available offline |
| F-11 | **Out-of-band commit.** `977b83b` is described both as the operator's commit of main-tree corpus changes (section 5.2) and as T-0139's integration commit (section 11). [REPORT] | If the corpus reached `main` by a manual commit, the gate and bundle (I5, "oracles decide") were bypassed for that content, and T-0139's DONE may be partly credit for work that already existed. | Relay D item 9 |
| F-12 | **Governance and attribution.** `TASK_VOIDED` recorded as `human/operator` via `--actor operator`; `QUEUE_DECIDED` (Q-071), `REVOKED` and `PROJECT_STATE` recorded as `kernel` via Python API calls with no actor argument (fallback `Actor.kernel()`). [REPORT, Appendix B] | `--actor` is a self-declared string, and `kernel` is the default for any script. Neither shows whether you or an agent acted. This is finding 9 from v3 again, now with a concrete record. The decision record for Q-071 says "fix the cause and resume" was a decision by `kernel`, not by you. | Decision D-1 (section 8) |
| F-13 | **Review independence.** The agent that diagnosed the fault also edited Kernel-adjacent source, committed `77a8659`, voided and recreated tasks, decided Q-071, and wrote the report. "pytest passes 100%" has no counts or junit. The report says the tree is clean while also saying the report is untracked. | Standing reviewer playbook: patch, fresh junit, composition check. None supplied. | Relay D item 10 |
| F-14 | **Mixed time zones.** Events are UTC; HANDOFF.md dates its re-scope "2026-11-02" while the report dates Q-071 "2026-11-01", yet Q-071 is numbered after Q-068 and Q-070. [OBSERVED; INFERRED that NZ local dates explain it] | Makes cross-checking error-prone. | Use UTC everywhere in reports |
| F-15 | **Over-general lessons.** "Relative paths are unsafe on Windows" is not what the evidence shows. The evidence says a particular CLI did not use the process cwd as its working directory (if the canary holds). | Wrong lesson, wrong test. | Reword lesson 1 |

## 5. What the evidence supports

Two separate questions:

**Why did the chain end BLOCKED?** Plausibly the order-path and main-tree defects. For f111 and f113 the T-0004 log is direct evidence, if the log is what the report says. For f114 and f115 the report's own evidence says the right order file was read and the agent then claimed a result that did not exist in its worktree. So the absolute-path fix was necessary for one failure mode but did not fix the second. The second failure mode is the "main tree visible and used" problem, and its mitigation so far is text.

**Why did each failure cost two hours?** Not explained. An agent that finishes or crashes in minutes, supervised by a live harness, loses minutes. Four leases ran to TTL, and a 3.5-hour gap followed one of them. The simplest hypothesis consistent with F-1 and F-2 is that the dispatch loop was not running for long stretches, or that its harness thread did not process agent exit. The report's own fix list includes "persistent dispatch loop" (R-04), which concedes the point while the text keeps calling it secondary.

If this reading is right, the prompt fix saved the task chain but the supervision gap would have turned *any* worker failure into a two-hour loss, and still can. [INFERRED; Relay D items 1 to 3 would settle it.]

## 6. Assessment of the report's recommendations

| ID | Report | My view |
|---|---|---|
| R-01 | Neutralise stale root `ORDER.md` | Accept. Add the cause: the harness must refuse to write `ORDER.md` to anywhere except a worktree, and refuse to spawn when `worktree` is empty (the T-0004 case, probably a legacy Manual Launcher run; [INFERRED]). Add a report-only sentinel check for a root `.pmwork/ORDER.md` matching no active lease. |
| R-02 | Parse agent claims against the diff | Replace. Parsing prose is brittle. Do instead: (a) task ID in `RESULT.md` must equal the lease's; (b) `NO_CHANGES` (agent exits with no changes outside `.pmwork/`) fails the attempt at once on `implement` cards (already your decision in v4); (c) on agent exit, run the oracles immediately and fail the attempt fast. The oracle is the real authority; the gap is latency, not trust. |
| R-03 | Prompt-regression test | Accept, and extend: assert that the rendered `ORDER.md` contains the absolute worktree path, and that every `spawn_slot` caller uses `order_prompt`. |
| R-04 | Persistent dispatch loop | **Raise to top priority.** Likely the largest source of lost time (F-1, F-2). A scheduled task is enough; NSSM is optional. First check whether the Console's own loops should do this (status report: `/api/resume` is dead after `STOP ALL`). |
| R-05 | Shorter TTL or heartbeat | Accept in the heartbeat form: revoke when the agent pid is dead, or the log has not grown for N minutes, whichever comes first. A TTL change lives in `.pm/policy.toml` and is class K; a per-card TTL derived from `wall_min` may avoid that (assessment R13). |
| R-06 | Duplicate-voiding protocol | Defer to the decomposition programme (lint check J, orphan report R4). When a card is voided, list and re-point its dependents in the same step (F-8). |
| R-07 | Isolation warning in `ORDER.md` | Keep as defence in depth only. |
| R-08 | `agent_hint` propagation | Keep. Confirm what the T-0139 hint said (F-9). |
| R-09 | Pre-integration main-tree check | Reframe as a **pre-lease** check: refuse to lease a card whose write scope has uncommitted changes in the main tree. That prevents both the "pre-staged" illusion and the later integration block. Do not auto-commit main-tree changes (that is how corpus content skipped the gate, F-11). |

**New recommendations**

| ID | Recommendation |
|---|---|
| R-10 | **Extend the selftest (Relay B) with a second decoy:** an uncommitted file in the main tree that satisfies the card's oracle. A pass requires the agent to produce the output in its own worktree. This tests the actual second failure mode through the real `spawn_slot` path. |
| R-11 | **Main-tree change detection:** record `git status --porcelain` for the main tree at spawn and at exit. Any change not attributable to the merge queue during a lease raises an incident. |
| R-12 | **Incident-report standard:** each causal claim cites an event seq or a log line; counts come from the ledger, not from memory; the author states which fixes were tested individually. |
| R-13 | **Independent review of `77a8659` and `977b83b`** with the standing playbook before treating the incident as closed. |

## 7. Recommended order of work

1. **Evidence (Relay D, read-only).** No code until it is back.
2. **Settle supervision first (R-04, R-05, fast-fail on agent exit).** These cut loss per failure regardless of cause.
3. **Re-run the canary through the real spawn path** with both decoys, one profile at a time: Hermes with `--in`, Hermes with a terminal working-directory setting if one exists, pi, opencode. Choose the mechanism from results, not from the report.
4. **Then Relay B** (selftest with R-10, `NO_CHANGES`, root-file sentinel, regression tests, R-09 as a pre-lease check).
5. **Re-run the Phase 0 census** after the fix has been in for a day. The post-incident ledger is a thin chain (T-0139 then T-0141 and T-0142), with 2 of 6 slots in use and nothing READY. That is exactly the supply and gating pattern the census classifies (G1, G2, G8).

## 8. Decisions needed from the operator

1. **D-1 (H-11).** Did you personally run the voids, Q-071 and `project_set_state`, or did Hermes Agent run them on your instruction? Either answer is fine; the record should say so. Separately: leave `--actor` self-declared and `Actor.kernel()` as the Python default (cheap, and a known limit), or require an explicit actor on state-changing API calls and record `unknown` when absent.
2. **D-2.** Do not close the incident until Relay D is reviewed and T-0141/T-0142 reach DONE through the gate.
3. **D-3.** Adopt the rule "no uncommitted edits in the main tree inside a READY or LEASED card's write scope while the fleet runs" (operator and agent sessions alike), pending the R-09 pre-lease check.
4. **D-4 (H-06).** Do not commit or accept the order-path code until the diff, junit and composition check have been reviewed (R-13).
5. **D-5 (H-17).** Confirmed by the report: CFNA and the UMAWS source share `C:\temp\projects\testproject1`. Accept that, or plan a split. It makes root-level collisions like this one structural.

## 9. Risks

| # | Risk | Mitigation |
|---|---|---|
| K-1 | A second isolation failure on a profile the canary did not test | Selftest per profile (R-10) |
| K-2 | Supervision gap remains and the next failure again costs hours | R-04, R-05 first |
| K-3 | Dependency bug (F-7) lets dependents start early | Relay D item 6; a Kernel test if confirmed |
| K-4 | Out-of-band main-tree edits recur (OpenCode sessions, Hermes Agent) | D-3, R-09, R-11 |
| K-5 | Credit for T-0139 hides that content entered `main` outside the gate | Relay D item 9 |
| K-6 | A free-tier model's report is treated as evidence | R-12 |

## Appendix A: Relay D (read-only evidence request for Claude Code)

```text
From: Claude (Claude Sonnet 5.5), reviewer
Read-only. No git add, git commit or git reset. Do not delete or move files. Do not write to .pm/.
Reply with raw excerpts (event seq numbers, log lines, command output), and say what you could not find.

1. For T-0131 f110, f111 and T-0136 f114, f115: every event from AGENT_STARTED to LEASE_EXPIRED
   (including agent exit, oracle results, any harness events). Was an agent-exit event ever recorded?
2. For those leases, the log tail and the exit code of each agent process, and when it exited.
3. When was a dispatch loop (Console loop or manual `dispatch run`) active between
   2026-11-01T13:00Z and 2026-11-02T03:10Z? Why was T-0131 not claimed between 15:58Z and 19:29Z?
4. Which profile wrote each log (111-0, 113-0, 114-0, 115-0)? Does any pi log show it reading the
   repo-root .pmwork/ORDER.md?
5. For the Hermes profile used: the exact argv, cwd and environment passed at AGENT_STARTED, and the output of
   `hermes chat --help` plus any Hermes config or env setting that sets the terminal working directory.
6. T-0141 and T-0142: depends_on as recorded, CLAIMED timestamps, and T-0139's state at that moment.
   Does the claim path treat SUBMITTED or VERIFIED as a satisfied dependency?
7. State of T-0137, T-0138 and T-0140, and whether any open card depends on a VOID card.
8. T-0139 f117: the rendered ORDER.md, the agent_hint text, the agent log, and where the 66 files came from.
9. `git --no-pager show --stat 977b83b` and `git --no-pager show --stat 77a8659`, and
   `git --no-pager log --oneline -12`. State which commit contains order_prompt().
10. A fresh pytest_junit.xml (count, failures, skipped, timestamp) and a combined patch against the
    commit before 77a8659. Confirm `git status --short` and list any untracked or committed junk.
```
