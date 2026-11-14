---
document:
  title: "Assessment v3: Review of the Verification Report (Appendix A results) and Revised Priorities for the Worktree-Isolation Incident"
  type: "Assessment and recommendations"
  status: "Advisory; no authority"
  version: "3.0.0"
provenance:
  author_llm: {name: "Claude", version: "Claude Sonnet 5.5 (Anthropic)"}
  assessed_document: "verification-assessment-v2-command-results-v1.md (v1.0.0, DeepSeek V4.1 Flash Free via opencode, 2026-11-02) and its cover message"
  supersedes: "assessment-claude-umaws-fleet-worktree-isolation-v2.md (v2.0.0), for the findings re-scored in sections 3 and 4"
  created_date: "2026-11-02"
  last_modified_date: "2026-11-02"
audience:
  primary: "The human operator (decision record)"
  secondary: "Claude Code and the next Claude (Web) reviewer session"
evidence_basis: "The verification report and cover message, read in full, plus the earlier incident reports, Relay D answers and my two earlier assessments. I have NOT seen the two patch files the report wrote to C:\\temp, the source files it quotes, or the ledger itself."
epistemic_status: "Tags: [VERIFIER] stated in the verification report as read or reproduced; [INFERRED] my reasoning; [GUESS] needs a test; [CHECK] a command in Appendix A settles it. Nothing here was run by me."
authority_statement: "Candidate tier. This document recommends; nothing takes effect until the operator decides. Changes to .pm/policy.toml or .pm/constitution.md are class K (two-key)."
---

# Assessment v3: Verification Report Review

## 0. How to use this document

1. **Operator:** read section 1 and section 6, then run Appendix A. Do the "now" items before anything else; they are time-sensitive.
2. **Next reviewer session:** section 3 is the claim-by-claim scoring; section 4 lists my own errors.
3. Upload the two patches (Appendix A, item 7) so the code claims can be checked.

## 1. Verdict

**This is the best-grounded report in the incident so far. Accept its corrections, check its three load-bearing new claims, and change the order of work.**

It reads code and ledger instead of reasoning from prose, answers D-3 and most of Relay E, and corrects two of my own findings. Its most important results are:

1. **N-15: `integrate` can record success with an empty commit.** T-0139's work is committed (`2a0f6fa` on `pmk/T-0139-117`) but never merged, while INTEGRATING and INTEGRATED both carry `commit: ""` after three failed merges. This replaces my "DONE without the work in git" framing with a sharper one.
2. **N-2 is now read from code.** `Dispatcher.run_forever(max_seconds=N)` just breaks at the deadline, with no handoff of in-flight leases. The Conductor, not the harness, produces the 1 to 2 second expiry lag (5 s tick).
3. **N-10: the new R-09 check leaks the lease it just claimed.** It runs after `kernel.claim()`, worktree creation and order writing, and returns without releasing anything.
4. **The delivered corpus does not match the pin it claims.** 66 of 66 files are CRLF; the pinned blobs are LF; no oracle compares against the pin.

**The incident has also just reproduced itself.** The report finds that T-0141's agent is dead and T-0142's has exited, with neither result processed for over 55 minutes and no `AGENT_EXITED` event. That happened after the "fixes". Unsupervised leases are not solved, whatever v3 of the incident report says.

| Part | Verdict |
|---|---|
| N-1 reframed (unmerged, not missing) | Accept |
| N-2 mechanism | Accept; strong evidence |
| N-10, N-11, N-15 | Accept as probable; confirm from the patch before fixing |
| N-12 (heartbeat ignored) | Accept as a defect; the claim that it explains f110 is overstated (section 5) |
| N-13 (`--no-ff` can't fix "would be overwritten") | Accept |
| Corpus off-pin (66/66) | Accept as a provenance defect; not an emergency in content terms |
| D-3 "no two-key events" | Partly overstated (section 5) |
| Proposed order of work | Reorder (section 6) |

## 2. What I could and could not see

Seen: the report's tables, code excerpts, seq numbers and hash lines. Not seen: the patches (`C:\temp\combined-77a56db-aed9aec.patch`, 136,710 bytes; `C:\temp\uncommitted.patch`, 49,608 bytes), the source, the ledger. The report is by a free-tier model and I cannot confirm any of it independently, but each load-bearing claim has a cheap check in Appendix A.

## 3. Scoring the new claims

| # | Claim | My view | Check |
|---|---|---|---|
| 1 | Corpus is committed at `2a0f6fa`, never merged; INTEGRATED has `commit: ""` | Consistent with the merge errors (seq 2947, 2950, 2960) and with my v2 N-1 | Report's own `merge-base` result; ledger seq 2969/2970 |
| 2 | `cna-rules-upstream` is a folder in a repo with no commits; the real pin is `C:\temp\tcanf-clone` at 75a037f with 66 files | Credible; it closes the provenance source question | Appendix A item 3 |
| 3 | Delivered corpus is CRLF; pin blobs are LF; manifest attests the CRLF hashes | Plausible; the hint's "byte-identical to the pin" was never tested. Pi f110 avoided this by using `git show HEAD:path` | Appendix A item 3 (blob ids, no redirects) |
| 4 | `Dispatcher.run_forever(max_seconds=N)` breaks with no cleanup; Conductor (uncommitted patch) emits LEASE_EXPIRED every 5 s | Fits every timing observation | Patch review; `Get-CimInstance` check (item 1) |
| 5 | R-09 runs after claim and leaks the lease; `FLEET_BLOCKED` mislabels it "claim refused" | Plausible and serious; I had asked what R-09 does on refusal and the answer was missing | Patch review (item 7) |
| 6 | T-0139 f117 lease still LEASED after INTEGRATED; expiry around 05:06Z | Plausible: integration by hand skipped whatever the merge queue does to release leases | `pmk status` (item 2) |
| 7 | `check_stall()` uses `granted_at` only and ignores renewals | Plausible; from the stall report's own design | Patch review |
| 8 | Pins re-recorded (seq 2272) before the ratifying decision (Q-059, seq 2284) | Ledger-checkable; see section 5 for how I read it | Ledger |
| 9 | T-0141/T-0142 oracles use nested `"` inside `python -c "..."` and cannot pass on cmd.exe | Plausible: the quotes close the argument early | Print the oracle commands from seq 2932 and 2934 |
| 10 | T-0141/T-0142 bases lack the corpus; T-0142 output shows `rule_files: 3` | Consistent with the corpus being unmerged | Appendix A item 4 |
| 11 | Ledger: I1 failures, deleted SENTINEL_RUN events, repair scripts in the repo root | Consistent with HANDOFF.md's hand renumbering (which I flagged in my first reply) | Report file `EVENT_LOG_VIOLATION_REPORT.md` |

## 4. Corrections to my own earlier assessment

1. **N-6 was wrong on two files.** I said `order.py` and `spawn.py` were uncommitted. They are in `aed9aec`; only `conductor.py` and `merge.py` are dirty under `src/`. My narrower point stands: the isolation warning is not in `77a8659`.
2. **N-8 was a bad guess.** `--no-restore-cwd` applies only to resumed sessions, and every incident lease had an empty session. Withdrawn. The revised canary in the report (`--in` alone; print `os.getcwd()` before any tool call) is better than mine.
3. **N-1 was incomplete.** I said the deliverable appeared not to be in git; it is on a branch. The defect is the empty-commit integration.
4. **F-9 (one-minute submit).** The ledger gives T-0139 f117's claim as 03:06:17Z, so the v2 incident report had that right and v3 (03:11:27) had it wrong. My statement that the v2 timestamps were wrong applied to the integration time only. The submit time is still not in a raw excerpt.
5. I recommended `--no-restore-cwd` testing and a main-tree "alert" in R-11 without having seen the code; the report shows R-11 only records status text.

## 5. Where the verification report overstates or errs

1. **`--in` is not only a session scoper.** The help text it quotes begins "Change into DIR before starting or resuming". It is still unproven that this changes where Hermes' file tools are rooted, so the test stands; the reading is selective.
2. **N-12 does not "explain" f110.** The pi log claims completion, and nobody polled the agent, so nothing submitted the result. Ignoring `renewed_at` would only kill a healthy task still running at 120 minutes. Supervision explains f110; N-12 is a separate defect that will bite long tasks.
3. **D-3 is stated too strongly.** There is a ratifying decision (Q-059) and a re-record after it (seq 2285, 8 seconds later); `class-k-ratification.md` already records that keys were taken after the change. The real defects are narrower and still serious: no typed policy-change event, a TTL change that triggered an I8' STOP for hours, and a `PINS_CHECKED` that can clear its own failure.
4. **"Outranks the line-ending trivia."** The CRLF/LF mismatch is a false provenance attestation, which matters here because the pin is the authority for the rules. But the rule text is identical modulo line endings, so fix it when the corpus lands; do not treat it as an emergency.
5. **Order of work.** The report puts D-1 first and says everything else is provisional. D-1 matters, but nothing in it is time-sensitive, and several other items are.
6. **The proposed re-derivation hazard.** `git show HEAD:<path>` piped or redirected in Windows PowerShell can re-encode or alter bytes. Use a binary-safe route (a short Python script reading the git output as bytes) and verify blob ids.
7. **Scope of D-4.** T-0145 and T-0146 depend on T-0139 and also run on a corpus-less base unless the corpus lands first. The report holds only T-0141 and T-0142.
8. **"Malformed INCIDENT payloads" (`{"message":"list"}`).** Likely a CLI that took the word `list` as an incident message. A small CLI defect, not evidence about governance.
9. **Ledger integrity (N-14) as an incident closure condition.** Real, but a separate track; it should not hold this incident open indefinitely.

## 6. Revised order of work

**Now (time-sensitive, reversible, read-only except the pause):**

1. **Find out whether a dispatch process is alive** (Appendix A item 1). T-0141/T-0142 show the unsupervised-lease pattern again, and a live loop that is not supervising would mean the problem is wider than `--seconds N`.
2. **Stop new leases** (use the Console pause control, or ask what the supported pause is). Reasons: N-10 will leak a lease on every refusal; T-0145 and T-0146 would start on a corpus-less base; and a stale lease on T-0139 may raise a false STALLED. Do not Ctrl+C the dispatcher until you have looked at what agents are running.
3. **Do not run `pmk revoke` on T-0139.** In this system a revoke on a DONE task has sent it back to READY before (T-0003, status report of 2026-10-26). The stale lease should be cleared by code (item 6 below), not by revoke. [INFERRED from that precedent; check with `pmk status` first.]
4. **Check the project state and queue** (Appendix A item 2). If it is past about 18:06 NZDT on 2 Nov (05:06Z), the false STALLED may already have fired.
5. **Snapshot the event log** (Appendix A item 6) before any further repair.

**Then, in order:**

6. **One small, reviewed code round** (after I read the patches): (a) move the R-09 check before `kernel.claim()` so refusal has no side effects; releasing the lease instead would also consume an attempt; (b) `integrate` requires a non-empty commit reachable from `main`, recorded in the payload; (c) lease release at INTEGRATED, or `check_stall` ignoring leases of terminal tasks; (d) `check_stall` uses the later of `granted_at` and `renewed_at`; (e) oracle lint that parses the command exactly as the harness will and compiles any `python -c` payload, or bans inline `python -c` oracles in favour of committed scripts.
7. **Decide the TTL policy as one act with the conductor patch** (the Kernel itself said they are coupled, seq 1948). I prefer reverting TTL to 20 minutes and making heartbeats count: with `renewed_at` honoured, TTL becomes a liveness timeout instead of a wall-clock cap. A dead supervisor then costs 20 minutes instead of 2 hours (my earlier R-05), and no class K change is needed. This requires that harness renewals demonstrably occur (check the ledger for renewal events). The alternative is to ratify 120 minutes properly, with a typed event, and accept that any task over 120 minutes is killed while healthy.
8. **Land the corpus pin-faithfully** (D-2 below), once the tree is otherwise settled, with the attribute rule and a recorded decision. Then release and void T-0141, T-0142 (and check 145, 146).
9. **Supervision reconcile-on-start** and a refusal (or handoff) when `run --seconds N` ends with leases in flight. Until then, no `--seconds N` runs.
10. **Hermes canary** as the report revised it, with `--in <worktree>` first and a `cwd` print before any tool call. Look at Hermes' own configuration for a terminal-directory setting. [GUESS]
11. **Review both patches properly on a clean checkout**, then re-run the suite there; the 383-test run was on a dirty tree.
12. **Ledger integrity (N-14)** as its own item: accept or reject the hand repair as a recorded decision, keep the `.bak` files, add a repair event type so future repairs are legitimate and visible, and move the `fix_chain*.py` and `renumber*.py` scripts out of the repo root.

## 7. Decisions needed from the operator

1. **D-1 (still open).** Interactive assistants (Hermes Agent, OpenCode, Claude Code) act with your identity, so the ledger cannot tell you from them. A cheap, existing mechanism: launch those sessions with `PMK_ACTOR=agent:<tool>` so their actions are attributed to the agent and human-only guards refuse them, and run human-only commands (void, queue decide, state changes) in your own plain shell. Do you want that?
2. **D-2 (corpus).** Option (a) as amended: derive all 66 files binary-safely from `C:\temp\tcanf-clone` at 75a037f, confirm each file's blob id equals the pin's, regenerate `manifest.json` and `checksums.sha256` (manifest-relative paths), add a `.gitattributes` rule so checkout cannot re-mangle them (`docs/rules/** -text` keeps bytes exactly; `text eol=lf` also works but normalises on add), then commit with a recorded decision naming T-0139. Do not merge `pmk/T-0139-117` or copy the main-tree files; both are CRLF. Keep the branch and worktree until the new commit is verified.
3. **D-3 (policy and pins).** Choose between: (i) revert TTL to 20 and fix heartbeat handling (my preference), or (ii) ratify 120 properly. Either way, make the policy change and the conductor patch one commit with a decision id.
4. **D-4.** Hold T-0141 and T-0142, and also T-0145 and T-0146 until the corpus has landed.
5. **D-5.** Keep the incident open. My closure list: corpus landed pin-faithfully; `integrate` proves the merge; R-09 side-effect-free; stale-lease and heartbeat handling fixed; reconcile-on-start in place; canary decided; patches reviewed on a clean checkout.
6. **D-6 (new).** Do you want a handoff v5 now? A lot has changed (seven new findings, a revised order of work, open decisions), and the current handoff v4 is out of date.

## 8. Risks

| # | Risk | Mitigation |
|---|---|---|
| K-1 | Dispatch keeps leaking leases and starting cards on a corpus-less base | Pause now (6.2) |
| K-2 | A revoke on T-0139 reopens a DONE task | Do not revoke; fix in code (6.3) |
| K-3 | Corpus re-derivation corrupts bytes in PowerShell | Binary-safe script; blob-id check |
| K-4 | Patch promoted with N-10 to N-12 defects inside | Review first; one reviewed round (6.6) |
| K-5 | The TTL/pin loop is closed retroactively again | One decision id covering policy, pin and patch |
| K-6 | The ledger is later found unreliable for this incident's timeline | Snapshot now; treat every timestamp as provisional until the repair is accepted |

## Appendix A: operator commands (PowerShell, from `C:\temp\projects\testproject1`)

Items 1 to 6 do not change repository files. Item 7 writes files into `C:\temp` only.

```text
# 1. Is any dispatcher, conductor or console process alive?
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "dispatch|fleet|console" } | Select-Object ProcessId, Name, CommandLine

# 2. Project state, leases, queue
.venv\Scripts\python.exe -m pmk.cli status

# 3. Is the delivered corpus on the pin? Compare git blob ids (no redirects, no filters).
#    Pin blob id vs T-0139 branch copy vs pi f110 copy.
git -C C:\temp\tcanf-clone rev-parse HEAD:CNA-Rules.adoc
git hash-object --no-filters work\T-0139-117\docs\rules\CNA-Rules.adoc
git hash-object --no-filters work\T-0131-110\docs\rules\CNA-Rules.adoc

# 4. Do T-0145 / T-0146 worktrees exist, and what is in their docs\rules?
Get-ChildItem work -Directory | Where-Object Name -match "T-014[5-6]" | Select-Object Name

# 5. Is T-0139 reachable from main? (expect False; this was already shown)
git merge-base --is-ancestor 2a0f6fa HEAD; $LASTEXITCODE

# 6. Snapshot the event log outside the repo
Copy-Item -Recurse .pm\events C:\temp\events-snapshot-20261102

# 7. Code-only patch for review (git writes the file itself, so no PowerShell re-encoding)
git --no-pager diff --output=C:\temp\code-77a56db-aed9aec.patch 77a56db..aed9aec -- src tests
```

Upload `C:\temp\code-77a56db-aed9aec.patch` and `C:\temp\uncommitted.patch`. If either shows garbled text when I read it, regenerate with `git diff --output=`. If the first blob id equals the third and differs from the second, the pin claim is confirmed.
