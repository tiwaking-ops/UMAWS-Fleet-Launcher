---
document:
  title: "Incident Report: Worker Worktree Lifecycle Leak, Stranded Unmerged Work, and Task Re-issue Churn (T-0096–T-0142 fleet run)"
  status: "Formal incident report; findings produced by read-only inspection of the live repository, authoritative event log, worktrees, git object store and source code; advisory document, no state changes made"
  version: "1.1.0"
provenance:
  author_llm:
    name: "DeepSeek V4.1 Flash Free"
    version: "opencode/deepseek-v4.1-flash-free"
  created_date: "2026-11-07"
  last_modified_date: "2026-11-07"
  scope: "C:\\temp\\projects\\testproject1 (branch main, HEAD 9eb39ad), .pm/ event log (3,109 events), work/ (98 worktrees), .git/worktrees metadata, %TEMP% pmk-merge-* trees, src/fleet and src/pmk source, and a cross-reference read of C:\\temp\\projects\\b5ccg"
  source_of_truth: "The append-only event log at .pm/events/*.jsonl (I1 hash chain verifies, 3,109 events) is authoritative for all coordination state. Git objects at HEAD 9eb39ad are authoritative for committed content. Filesystem measurements are authoritative for disk usage. Where this report and the Overseer briefing disagree, the event log and git store win; see Appendix D."
  related_documents:
    - "incident-report-worktree-isolation-v3.md (R-12, R-13 — the standard this report follows)"
    - "EVENT_LOG_VIOLATION_REPORT.md (prior governance-violation precedent)"
    - "docs/pm-workflow-analysis-template-v1.md (cross-project analysis template, not used here)"
  reviewer: "R-13 independent review COMPLETED 2026-11-07 across six independent LLM assessments (five ACCEPT WITH CORRECTIONS, one ACCEPT; none refuted a central claim). Their findings are collated and adjudicated in proposal-deepseek-umaws-fleet-worktree-lifecycle-remediation-v1.md; the accepted corrections are applied in this v1.1. See Appendix F (updated) and Appendix G."
  editor_llm: "DeepSeek V4.1 Flash (deepseek-ai/deepseek-v4.1-flash, nvidia) — applied the v1.1 corrections; NOT an independent assessor of this report"
  corrections_applied: "C-1 through C-16 (see Appendix G)"
  corrected_date: "2026-11-07"
---

# Incident Report: Worker Worktree Lifecycle Leak, Stranded Unmerged Work, and Task Re-issue Churn

**Author:** DeepSeek V4.1 Flash Free (`opencode/deepseek-v4.1-flash-free`)
**Version:** 1.1 (`incident-report-worktree-lifecycle-leak-v1.1`) — corrected per six independent assessments; see Appendix G
**Date:** 2026-11-07 (v1.0); corrected 2026-11-07 (v1.1)
**Editor (v1.1 corrections):** DeepSeek V4.1 Flash (`deepseek-ai/deepseek-v4.1-flash`) — applying reviewer corrections, not reassessing
**Repository:** `C:\temp\projects\testproject1`
**Branch / HEAD:** `main` @ `9eb39ad6a775c075d6c01e7a22b3f990a953a8fa` (2026-11-05)
**Project state:** `PAUSED` (operator decision; this report does not change it)
**Status:** Findings and recommendations only. No worktree was deleted. No stranded work was moved, committed or removed. No source file was edited. Nothing under `.pm/` was written by this report.

---

## 1. Executive Summary

The UMAWS Fleet allocated **98 worker worktrees** across **51 distinct task IDs**, permanently retaining **886.2 MiB** of a **969 MiB** repository. No worker worktree is reclaimed by the fleet: the function that deletes one — `remove_worktree()` at `src/fleet/spawn.py:129` — has **no call sites anywhere in the repository**, so it is dead code. (Separately, **at least seven recorded worktrees are missing from disk** — F-22 — but those were removed out of band, not by the fleet.) The harness's own module docstring (`src/fleet/harness.py:19`) states the intended policy: *"Quarantine and keep the worktree on any give-up."* The keep-half of that policy was implemented; the collect-half never was. Every fence bump therefore leaves a ~9 MiB checkout on disk forever.

The space leak is not the most serious finding. **56 of the 98 worktrees contain 488 uncommitted file entries (514.9 MiB) belonging to tasks that were voided before submission.** Because a worktree path is derived from the lease fence (`work/<task>-<fence>`) and every revocation bumps the fence, a retried task receives a brand-new empty checkout. The replacement agent cannot see its predecessor's work, restarts from `HEAD`, and the predecessor's output is abandoned in place. The clearest case is **T-0101**, which ran three times across fences 54, 65 and 76 — three different agents each independently implemented and tested `src/cna/core/` (dice, ids, errors, seeded RNG), each wrote a `RESULT.md` claiming passing tests, and none of the three was merged. `src/cna/core/` exists in neither `main` HEAD nor the working tree. The module was written three times and delivered zero times.

Two further structural defects compound the loss. First, the handoff mechanism is effectively absent on the failure paths: `write_handoff()` has **three** call sites — `harness.py:586` (`_fix_round`, oracle failure during an active lease), `dispatcher.py:383` (recovery step L2) and `cli.py:617` (`pmk agent send`) — but **none** is on the give-up or TTL-expiry path, and `ORDER.md` — the document the agent prompt actually points at — always renders `## Handoff` as `none` because `render_order()` is called exactly once (`harness.py:347`), before any handoff can exist. Across all 98 surviving worktrees there are **zero** fleet-generated `.pmwork/HANDOFF.md` files. Second, the work has no diagnostic surface: `work/` is gitignored (`.gitignore:12`), so 91% of the repository's disk is invisible to `git status`, and the only invariant that could notice a problem (`I6`, every DONE task has a bundle) fails for five unrelated tasks and has been failing continuously, with `863 FLEET_BLOCKED` and `423 OVERSEER_WOKEN` events recording a loop that re-detected the same conditions without changing anything (the 863 `FLEET_BLOCKED` span `seq` 330–2523, about one per 4 minutes over its dense window).
 No task record has been lost. `TASK_CREATED` count is 146 and distinct task ID count is 146; the I1 hash chain verifies over 3,109 events; all nine hash-bearing `INTEGRATED` commits were individually confirmed reachable from `main`. The loss is at the artefact layer, not the ledger layer: uncommitted, unmerged agent output inside a gitignored directory that no automated process will ever read again. Separately, a widely repeated claim that the T-0139 corpus was at risk is **incorrect** — the corpus was committed to `main` on 2026-11-03 as `1a5ec9b` with all 66 files verified byte-exact against pin `75a037f`; only a bookkeeping gap remains (`INTEGRATED` recorded `commit: ""`). This report corrects that claim explicitly (Appendix D) because it has been circulating as an open blocker and it distorted the risk picture.

---

## 2. Scope, Method and Non-Actions

### 2.1 Questions this report answers

| # | Question | Answer location |
|---|---|---|
| Q1 | Is each task completed in its own worktree? | §4.1, §9.1 — no: worktrees are per-**lease**, not per-task |
| Q2 | Has any work or task been lost or permanently lost? | §5 F-05, F-06, F-07 — no ledger loss; artefact loss is real and quantified |
| Q3 | Is the ~1 GB disk consumption justified by the work delivered? | §5 F-01, §7, §9 — no; ratio is approximately 900:1 |
| Q4 | Does the workflow reuse worktrees across agents? | §4.2 — yes, within one fence; no, across a fence bump |
| Q5 | What must change to stop recurrence? | §6 |

### 2.2 Method

1. **Ledger.** Read every `.pm/events/*.jsonl` file (filtering `*.jsonl` only — a stale `2026-10-31.jsonl.bak` duplicate exists and double-counts events if included). Parsed 3,109 events. Verified the I1 chain via `pmk status`.
2. **Git.** `git ls-tree`, `git log`, `git show --stat`, `git merge-base --is-ancestor` for every hash-bearing `INTEGRATED` commit; `git worktree list`; `git branch --list`.
3. **Filesystem.** Per-worktree `git status --porcelain -uall`, per-worktree byte accounting, `.pmwork/RESULT.md` extraction.
4. **Source.** Read `src/fleet/spawn.py`, `harness.py`, `recover.py`, `dispatcher.py`, `order.py`, and `src/pmk/api.py`, `cli.py`, `sentinel.py`.
5. **Sentinel.** Ran `pmk.sentinel.check(kernel)` and recorded its output verbatim (§9.4).

### 2.3 Explicit non-actions

- No file under `work/` was deleted, renamed or modified.
- No stranded patch was exported, no branch was created, no commit was made from stranded work.
- No file under `src/` or `tests/` was edited.
- The project was **not** unpaused.
- Kernel state changes were limited to the three governance actions the operator authorised (§8): deciding Q-072, deciding Q-073, and recording Q-076.

### 2.4 Known limitations

- Disk figures are single-sample measurements on a Windows/NTFS volume. Repeated measurement in this session varied by up to ±0.5 MiB per aggregate (e.g. the dirty-tree total measured 514.7 MiB on the first pass and 514.9 MiB on the verification pass) because agent runs continue to write `__pycache__` directories and scratch files inside the trees. Byte totals are therefore stated to one decimal place and should be read as approximate. The `%TEMP%\pmk-merge-*` figure and the `b5ccg` figures are also volatile: `b5ccg` is a live repository and its numbers moved measurably between the two passes (§11).
- The 56-tree inventory (§12) records each agent's **own claim** in `RESULT.md`. Those claims are not verified — under fleet rule 18 an agent's `RESULT.md` is never evidence on its own. They are reproduced to document what was abandoned, not to assert that it worked.
- Content of stranded files was sampled, not exhaustively diffed against `HEAD`. The one exception is `src/cna/core/`, which was positively confirmed absent from both `HEAD` and the working tree.

---

## 3. Incident Timeline

All timestamps UTC. "seq" is the authoritative event-log sequence number.

| When | seq | Event | Significance |
|---|---|---|---|
| 2026-10-22T05:56:24Z | 1 | first event in log | Fleet run begins |
| 2026-10-31T11:35:42Z | — | `work/T-0004-28` worktree created | Earliest surviving worktree on disk |
| 2026-10-31T20:59:46Z | 1736 | `CLAIMED` T-0101 fence 54 | First of three independent attempts at `src/cna/core/` |
| 2026-10-31T21:19:48Z | 1795 | `REVOKED` T-0101 fence 54 — "lease TTL expired" | Fence 54 → 65; `work/T-0101-54` orphaned with 6 uncommitted files |
| 2026-10-31T21:20:54Z | 1832 | `CLAIMED` T-0101 fence 65 | Fresh empty checkout; predecessor's code invisible |
| 2026-10-31T21:40:56Z | 1908 | `REVOKED` T-0101 fence 65 — "lease TTL expired" | Fence 65 → 76; second orphan, 10 uncommitted files |
| 2026-10-31T22:07:38Z | 1962 | `CLAIMED` T-0101 fence 76 | Third independent implementation |
| 2026-11-01T00:07:39Z | 2109 | `REVOKED` T-0101 fence 76 — "lease TTL expired" | Third orphan, 3 uncommitted files |
| 2026-11-01T05:35:19Z | 2213 | `TASK_VOIDED` T-0101 fence 85 — "reset attempts exhausted" | Task closed; all three implementations abandoned |
| 2026-11-01T21:29:50Z | — | Q-072 raised — lease T-0131 expired | Stall record #1 |
| 2026-11-02T00:09:47Z | — | Q-073 raised — lease T-0136 expired | Stall record #2 |
| 2026-11-02T20:54:21Z | — | **Q-074 decided** — land corpus from pin objects, supersede `pmk/T-0139-117` | Class K; resolves the corpus integration block |
| 2026-11-03T10:05:57Z (+13) | — | **Commit `1a5ec9b`** — "corpus: land CNA rules corpus from pin 75a037f (66 files, byte-exact)" | Corpus committed; CRLF copy on the T-0139 branch deliberately superseded |
| 2026-11-05T19:14:52Z | — | **Commit `9eb39ad`** — "fleet: edge-triggered, PAUSED-aware Overseer wakes" | Current HEAD |
| 2026-11-06T01:09:54Z | — | **Q-075 decided** — restore `ttl_minutes = 20` | Reduces (does not remove) the TTL-expiry revoke rate |
| 2026-11-06T12:31:25Z | 3107–3108 | **Q-072, Q-073 decided** — "fix the cause and resume" | Operator closes both stall records (this report's authorised action) |
| 2026-11-06T12:32:21Z | 3109 | **Q-076 created** — class K remediation authorisation | Records the decision this report asks the operator to make |

**Loop signature (not a single event but the dominant pattern).** Across the whole log the record shows `863 FLEET_BLOCKED` (spanning `seq` 330–2523), `423 OVERSEER_WOKEN` (`seq` 2–3093), `255 FLEET_ASSIGNED` and `102 INCIDENT` events against only `112 CLAIMED` and `104 AGENT_STARTED` — about 7.7 blocking events per claim. The Overseer re-detected the same blocked conditions and recorded them again.

---

## 4. Root Cause Analysis

### 4.1 RC-1 (primary) — Worktree paths are keyed to the lease fence, and the fence changes on every retry

`create_worktree(repo, task_id, fence, ...)` (`src/fleet/spawn.py:89`) builds the path `work/<task_id>-<fence>`. The fence is allocated at claim time (`src/pmk/api.py:497`) and **bumped by every revocation** (`src/pmk/api.py` `_current_fence` / stale-fence logic at 426). Therefore:

- One task can own several worktrees: `T-0101` owns 3, `T-0100` 3, `T-0102` 3, `T-0104` 3, `T-0103` 3, and 22 tasks in total own 3 each.
- The relationship is **per-lease, not per-task**. The premise "each task is completed in its own worktree" is false in the retry case and true only for a task that succeeds on its first lease.

This design is defensible for isolation (`I4`: a stale-fence submission must never merge), but it makes retries expensive by construction: every retry pays a full ~9 MiB checkout and forfeits all uncommitted progress.

### 4.2 RC-2 (primary) — Reuse within a fence works; reuse across a fence is impossible

`src/fleet/recover.py` (lines 1–42) documents a recovery ladder. Levels `L0`–`L2` preserve the fence and therefore pass `worktree=run.worktree, fence=run.lease.fence` straight through (`src/fleet/dispatcher.py:473-474`), so the replacement agent receives the **same** checkout. `L3` bumps the fence, which allocates a new empty checkout. `L4` blocks.

Live proof that reuse works: `T-0003` ran three different profiles — `pi-orca-deepseek`, then `opencode-strongest`, then `hermes-oneshot` — all at fence 3, and the result integrated as `6764d54` (verified ancestor of `main`); the `AGENT_RESUMED` events record the same-fence reuse directly. (The directory `work/T-0003-3` itself no longer exists — see F-22.) The mechanism is sound. It simply is not reached in the dominant failure mode.

**The dominant failure mode is not `L3`.** Of 108 `REVOKED` events, **58 (53.7%)** carry the reason `lease TTL expired`. A lease expiring is a *time* failure, not a *recovery-class* failure: the harness never gets to run the ladder, because the lease is reaped elsewhere and the next claim simply allocates the next fence. `pmk sweep` (`src/pmk/cli.py:350`) does exactly that — it expires leases and returns; it does not touch the filesystem.

### 4.3 RC-3 (primary) — The reclaim function exists and is never called

```
src/fleet/spawn.py:129  def remove_worktree(repo, path: str | Path) -> bool:
```

`grep` across `src/` and `tests/` returns exactly one match: the definition itself. Zero call sites. Nothing in `pmk`, nothing in the dispatcher, nothing in the harness.

The give-up path confirms the omission:

```
src/fleet/harness.py:719  def _give_up(self, lease, result, reason):
src/fleet/harness.py:720      """Revoke the lease, bump the fence and quarantine the worktree."""
src/fleet/harness.py:722      self.kernel.revoke(lease.task_id, lease.fence, reason=reason)
src/fleet/harness.py:726      self.kernel.quarantine(lease.task_id, lease.fence, reason=...)
```

`revoke` bumps the fence; `quarantine` writes `.pm/quarantine/<task>/<fence>/reason.txt` — metadata only. The method's own docstring says it quarantines "the worktree", but the filesystem is never touched. The module docstring (`harness.py:19`) makes the intent explicit: *"Quarantine and keep the worktree on any give-up."* Keeping was deliberate; collecting was forgotten.

**Note (v1.1).** "Nothing ever deletes a worktree" describes the *code*: no code path removes a worker worktree. It is not a statement about the disk state — at least seven recorded worktrees have been removed out of band (F-22). Both are true: the leak is real, and something unrecorded deleted some trees.

### 4.4 RC-4 (secondary) — The handoff channel is absent on the failure paths

Three facts combine:

1. `render_order()` is called **once**, at `harness.py:347`, at spawn time. The `## Handoff` section in the generated `ORDER.md` therefore always reads `none` (verified on `work/T-0004-28/.pmwork/ORDER.md`).
2. `write_handoff()` has **three** call sites: `harness.py:586`, inside `_fix_round` (oracle failure during an active lease); `dispatcher.py:383`, on recovery-ladder step `L2` (a fresh session in the same worktree, a path `recover.py` itself documents as "with a handoff note"); and `cli.py:617` (`pmk agent send`, an operator message). It is never called from `_give_up` and never called when a lease expires — and the two in-lease paths evidently never fired in this run (0 of 98 trees carry a handoff).
3. `order_prompt()` (`src/fleet/order.py`) instructs the agent to read `ORDER.md`. It never mentions `HANDOFF.md`. The file `src/fleet/order.py:31 HANDOFF_FILE = "HANDOFF.md"` is written to `.pmwork/HANDOFF.md` (`handoff_path`, line 43) and then not referenced by the prompt.

Verified outcome: `.pmwork/HANDOFF.md` exists in **0 of 98** worktrees. Note the distinction — a *repository* file named `HANDOFF.md` (4,692 bytes at report time; re-measured ~6,088 bytes on 2026-11-07 — the tracked file's content has changed; tracked, dated 2026-10-30) is present in every checkout as ordinary content. It is not the fleet mechanism and does not carry per-lease state. Conflating the two produces a false "196 handoff files exist" reading; the fleet-generated count is zero.

### 4.5 RC-5 (secondary) — No observation surface, and the only relevant invariant is permanently red

- `work/` is gitignored (`.gitignore:12`). 886.2 MiB — 91.5% of the repository — is invisible to `git status`, `git diff` and every review habit built on them.
- `.git` real pack is 2.67 MiB. The stranded work is not recoverable from git; it exists only as loose files in ignored directories.
- `work/` has no size baseline, no growth alarm and no reported metric anywhere in `pmk status`.
- `I6` ("every DONE task has a matching bundle") is currently failing for T-0118, T-0119, T-0127, T-0129 and T-0130, all `stops: true`. A stop-invariant that is permanently red trains operators to ignore the sentinel — and it is unrelated to this leak anyway (§9.4).

### 4.6 RC-6 (tertiary) — Task cards were reissued instead of repaired

138 of 146 cards (**94.5%**) ended `VOID`. The same work was described again and again rather than the failing attempt being repaired: "Vendor rules at pinned commit" appears 13 times, "Coverage tool…" 9 times, several 6–7 times. Reissue is the cheap path for an agent and the expensive path for the repository — each card costs a worktree, an agent run, and a new opportunity to lose uncommitted output. §9.2 quantifies the churn.

### 4.7 Causal chain

```
lease expires (58 of 108 revocations)
        │
        ├─► revoke() bumps fence ─────────────► new worktree path by design (RC-1)
        │                                        previous worktree becomes unreachable
        │                                        by any future attempt (RC-2)
        │
        ├─► no handoff written (RC-4) ────────► replacement agent starts from HEAD,
        │                                        re-does the same work
        │
        └─► remove_worktree() never called ───► previous worktree stays forever (RC-3)
                                                 │
                                                 ├─► 886 MiB on disk, gitignored (RC-5)
                                                 └─► 488 uncommitted entries, unreachable
```

---

## 5. Findings

Severity: **S1** = loss of work or safety property; **S2** = large cost or degraded assurance; **S3** = hygiene / traceability. Status per R-12: *acknowledged*, *resolved*, *deferred*.

| ID | Sev | Finding | Evidence | Status |
|---|---|---|---|---|
| F-01 | S2 | 98 worker worktrees retained, 886.2 MiB, 91.5% of a 969 MiB repository. Mean 9.04 MiB, range 8.7–10.3 MiB. | `work/` measurement; §7 | acknowledged |
| F-02 | S1 | `remove_worktree()` (`src/fleet/spawn.py:129`) has zero call sites. Dead code. Nothing in the system ever deletes a worktree. | `grep` across `src/`, `tests/` | acknowledged |
| F-03 | S1 | Worktree identity is per-lease (`work/<task>-<fence>`), so every retry allocates a new checkout and abandons the prior one. 98 trees serve only 51 tasks; 22 tasks own 3 trees each. | `spawn.py:89`; §12 | acknowledged |
| F-04 | S1 | 56 of 98 trees hold **488 uncommitted file entries** (514.9 MiB) belonging to VOID tasks. Nothing will ever read them again. | per-tree `git status -uall`; §12 | acknowledged |
| F-05 | S1 | **T-0101** implemented `src/cna/core/` three times (fences 54, 65, 76) with three `RESULT.md` success claims; `src/cna/core/` is absent from `main` HEAD and from the working tree. Three passing implementations, zero delivered. | seq 1736–2213; §12 | acknowledged |
| F-06 | S1 | Same-class re-implementation triples: `src/cna/state/` (T-0014, T-0102), `src/cna/tools/coverage.py` (T-0100 ×3), `src/cna/tools/show_rule.py` (T-0011, T-0099 ×2), repo skeleton (T-0024, T-0024, T-0096 ×3), rules corpus vendor (T-0097 ×3, T-0131). | §12 | acknowledged |
| F-07 | S2 | The handoff channel is effectively absent: `write_handoff` is called from three code sites (`harness.py:586`, `dispatcher.py:383`, `cli.py:617`) but none on the give-up or TTL-expiry path; `render_order` runs once so `## Handoff` is always `none`; `order_prompt` never mentions `HANDOFF.md`; **0** fleet-generated `.pmwork/HANDOFF.md` exist. | `harness.py:347,586`; `order.py:31,43` | acknowledged |
| F-08 | S2 | `pmk sweep` (`src/pmk/cli.py:350`) expires leases without any filesystem action, and `pmk` has no `worktree` subcommand (verified against `pmk --help`). There is no operator path to reclaim space. | `cli.py:350`; `pmk --help` | acknowledged |
| F-09 | S2 | 20 `pmk-merge-*` directories remain in `%TEMP%`, totalling **80.1 MiB**; 19 still contain files, eight of which hold ~10 MiB each and account for essentially the whole 80.1 MiB. Registered in `git worktree list` as live worktrees. `8a71d36` introduced the temporary merge worktree **with** a `try/finally` cleanup (`merge.py:336-344`), but the cleanup is not durable: `rmtree(..., ignore_errors=True)` fails silently on locked files and hard process kills bypass it. | `git worktree list`; §7.4 | acknowledged |
| F-10 | S2 | 161 branches retained (159 `pmk/*`) and 107 entries in `.git/worktrees` (≈4.6 MiB) for worktrees that no longer function as checkouts. | `git branch --list`; `.git/worktrees` | acknowledged |
| F-11 | S3 | Fleet logs unbounded: 12.17 MiB of `.pm/fleet/logs`, of which `overseer/0-0.log` alone is 8.61 MiB. No rotation, no cap. | `.pm/fleet/logs` measurement | acknowledged |
| F-12 | S2 | 138 of 146 task cards (94.5%) were `VOID`; only 6 reached `DONE`. Same work re-described up to 13 times. | event log; `pmk status` | acknowledged |
| F-13 | S2 | The control loop is saturated: `863 FLEET_BLOCKED` + `423 OVERSEER_WOKEN` + `102 INCIDENT` against `112 CLAIMED`. Roughly one wake per minute for five days produced no state change. | event-log type counts | acknowledged |
| F-14 | S2 | `I6` is permanently failing for 5 DONE tasks (`T-0118`, `T-0119`, `T-0127`, `T-0129`, `T-0130` — "INTEGRATED event has no bundle reference"), all `stops: true`. A stop-invariant that never clears is a stop-invariant that gets ignored. | `pmk.sentinel.check` | acknowledged |
| F-15 | S2 | **9 of 18 `INTEGRATED` events carry an empty `commit` field**, and **7 tasks record `INTEGRATED` twice** (a paired empty/hashed event — empty first for T-0004/T-0006, hashed first for the five DONE tasks): T-0004, T-0006, T-0118, T-0119, T-0127, T-0129, T-0130. Only one of the nine empties (`T-0139`) is visible to the sentinel, because `I5`/`I6` iterate **DONE** tasks only — the other eight belong to tasks now `VOID` (T-0004, T-0005, T-0006) or are duplicate events on a DONE task. Promotion provenance is therefore incomplete across the whole run, not just for `T-0139`. | event-log `INTEGRATED` sweep; `src/pmk/sentinel.py:133-166` | acknowledged |
| F-16 | — | **Correction:** the T-0139 corpus is **not** at risk. 66 files are committed at `1a5ec9b`; `git status` clean; HEAD `manifest.json` and `checksums.sha256` verify 66/66; CRLF-normalised content identical to upstream 66/66. | §8 Q-074; Appendix D | resolved |
| F-17 | S3 | `work/` being gitignored means the largest and least durable data in the repository is the least visible. No metric, alarm or report mentions it. | `.gitignore:12` | acknowledged |
| F-18 | S3 | Nothing verifies that a worktree is safe to delete. Any future cleanup implemented naively will destroy F-04/F-05 content. The current safety depends entirely on the leak itself. | §4.7 | acknowledged |
| F-19 | S3 | No `TASK_CREATED`, task row or hash-chain event was lost: 146 created = 146 distinct; chain verifies over 3,109 events. The 18 `INTEGRATED` events resolve to 11 distinct subjects (T-0003, T-0004, T-0005, T-0006, T-0026, T-0118, T-0119, T-0127, T-0129, T-0130, T-0139); the 9 hash-bearing ones (`6764d54`, `aa49678`, `484ab5c`, `95ee479`, `e7cea34`, `0fc8d0c`, `ad525d4`, `3e57580`, `77a56db`) are **all** confirmed ancestors of `main`. | `pmk status`; `merge-base --is-ancestor` per commit | resolved |
| F-20 | S3 | `.pm/views/queue.md` was stale (listed Q-074 as open after it was decided) — an `I13` projection drift. Regenerated during this report's governance step. | `.pm/views/queue.md` before/after | resolved |
| F-21 | S2 | Task-card `agent_hint` text is frozen at creation and never revalidated against current HEAD. `T-0145` and `T-0146` both instruct the agent to copy the 66-file corpus into its worktree because "main HEAD `977b83b` does NOT contain the CNA corpus" — but the corpus was committed at `1a5ec9b` and `main` is now `9eb39ad`. Executing the hint as written would overwrite correct LF files with CRLF copies or produce a large no-op diff. | `pmk task show T-0145` / `T-0146`; §7.6 | acknowledged |
| F-22 | S1 | **At least seven worker worktrees recorded as started are absent from disk** (`T-0001-1`, `T-0001-2`, `T-0003-3`, `T-0005-6`, `T-0005-7`, `T-0005-8`, `T-0006-9`), plus `T-0127-97`/`T-0129-98` inferred from DONE-task integrations. No code path removes a worker worktree, so these were deleted **out of band**, with no log event. An unrecorded destructive action in a system whose log is its source of truth is itself a governance concern (cf. `EVENT_LOG_VIOLATION_REPORT.md`). | `AGENT_STARTED` worktree payloads (104 distinct) vs `Test-Path` on `work/`; the seven recorded absences; `git rev-parse` for the two inferred fences | acknowledged |

---

## 6. Recommendations

Status vocabulary per R-12: *implemented* (present in `main`), *documented* (specified, not coded), *deferred* (operator decision pending). Per the operator's instruction, **none of these are implemented by this report**; all are deferred.

| ID | Addresses | Recommendation | Effort | Impact | Status |
|---|---|---|---|---|---|
| REC-01 | F-02, F-03, F-04, F-18 | **Reclaim at the fence bump.** Call `remove_worktree()` from `_give_up()` (`harness.py:719`) and from the lease-expiry path, **after** preserving any uncommitted content. Implement as one shared helper (`_revoke_and_reclaim`) so every fence bump — harness give-up, TTL reaper, operator `revoke` — takes the same path. | M | Removes the root cause | deferred |
| REC-02 | F-04, F-18 | **Preserve before deleting.** The helper must, before removal: (a) write `git diff --binary` plus untracked files into a durable store (a `stranded/<task>/<fence>.patch` directory or a dedicated branch), and (b) copy `.pmwork/RESULT.md`. **Never delete a tree with uncommitted content without a captured copy.** | M | Turns silent loss into recoverable archaeology | deferred |
| REC-03 | F-04 | **Do not bulk-delete existing trees.** The 56 dirty trees are the only copy of F-04/F-05 content. Any reclamation of the existing 886 MiB must be preceded by REC-02's capture step, tree by tree. | S per tree | Prevents making the incident worse | deferred |
| REC-04 | F-08 | **`pmk worktree` subcommand**: `list` (task, fence, size, dirty?, age), `prune --dry-run`, `prune --void-older-than <duration>`, `prune --keep-unmerged`. Dry-run default. Refuses to prune a dirty tree unless `--archive` is given. | M | Gives the operator a safe manual lever | deferred |
| REC-05 | F-07 | **Wire the handoff end-to-end.** Call `write_handoff()` on the give-up/expiry path; re-render `ORDER.md` (or emit a second `ORDER.md` with the handoff inlined) when a tree is reused; add an explicit line to `order_prompt()` telling the agent to read `.pmwork/HANDOFF.md` first if present. | S | Removes duplicated work on every retry | deferred |
| REC-06 | F-01, F-17 | **Make the leak observable.** Report `work/` tree count and total bytes in `pmk status`, and add a non-stopping invariant (`I17`) that flags `work/` above a configurable cap (suggest 2 GB) or any tree older than N days belonging to a settled task. | S | Detects recurrence even if REC-01 regresses | deferred |
| REC-07 | F-09, F-10 | **Sweep the merge scratch space.** Remove the residual `%TEMP%\pmk-merge-*` directories and `git worktree prune` the stale `.git/worktrees` entries. Harden the existing `try/finally` (`merge.py:336-344`) so `rmtree` failures are reported rather than silently ignored. | S | Recovers 80.1 MiB + ~4.6 MiB immediately | deferred |
| REC-08 | F-11 | **Cap fleet logs.** Rotate at a fixed size or age; cap retained files. 8.61 MiB from a single overseer with no rotation is a leak of a second kind. | S | Bounds a second unbounded growth | deferred |
| REC-09 | F-14 | **Fix or retire `I6`.** Five permanent `stops: true` failures mean the invariant is either mis-specified (bundles not recorded at integration time) or the integrations were improper. Decide which, then either backfill bundle references or downgrade the check with a recorded decision. | M | Restores the sentinel's signal value | deferred |
| REC-10 | F-12, F-13 | **Prefer repair to reissue.** Before creating a new card for a previously-voided scope, require an explicit `reissue-reason` on the card and attach the predecessor's handoff (REC-05). Add a cap: the same scope may not be reissued more than twice without a recorded queue decision. | M | Attacks the 94.5% void rate at source | deferred |
| REC-11 | F-15 | **Traceability backfill.** Record the `1a5ec9b` commit against `T-0139` so `INTEGRATED` is no longer empty-commit; or record an explicit `SUPERSEDED_BY` event linking `pmk/T-0139-117` to `1a5ec9b`. | S | Clears sentinel `I5` and closes the audit gap | deferred |
| REC-12 | F-16 | **Retire the "corpus at risk" claim** from all future briefings. It is resolved. Retain only the bookkeeping item (REC-11). | S | Prevents repeated false blockers | deferred |
| REC-13 | F-21 | **Revalidate `agent_hint` at lease time.** Hints describe the world as it was at card creation. At claim, either re-render the hint from current HEAD or reject it as stale when the referenced commit is not the base commit. Minimum viable: store the base commit the hint was written against and refuse to lease if `HEAD` has moved and the hint names the corpus or other now-committed artefacts. | S | Stops cards from instructing agents to undo completed work | deferred |

### 6.1 Priority

1. **REC-03 first.** Any action that deletes trees before REC-02 exists converts a storage leak into data loss.
2. **REC-02 then REC-01** — capture, then reclaim. Shipping REC-01 alone would delete 488 uncommitted entries on the next lease expiry.
3. **REC-07 and REC-08** — cheap, independent, recover ~93 MiB immediately with no risk.
4. **REC-05** — highest value per line changed; stops the duplication that produces the stranded work in the first place.
5. **REC-04, REC-06, REC-09, REC-10, REC-11** — durability and assurance.

### 6.2 Acceptance criteria for the fix

- A lease revoked by TTL expiry leaves **no** `work/<task>-<fence>` directory, and any content it held is retrievable from the archive by task and fence.
- A lease revoked by `_give_up()` produces the same outcome.
- A tree containing uncommitted content is **never** deleted without an archive artefact whose size and file count are recorded in the log.
- `pmk worktree list` reports, for every tree: task, fence, task state, dirty flag, bytes, age.
- `order_prompt()` output names `HANDOFF.md`; a reused tree's second agent demonstrably reads it (prompt-regression test, in the style of R-03 in the v3 report).
- Regression test: run a task, expire its lease, re-claim, assert the new tree exists **and** the old tree (a) is gone and (b) is archived.

---

## 7. Current State

### 7.1 Kernel

```json
{
  "project_state": "PAUSED",
  "tasks": { "VOID": 138, "DONE": 6, "PROPOSED": 2 },
  "task_total": 146,
  "active_leases": 0,
  "open_queue_items": 1,
  "incidents": 102,
  "stopped": false,
  "chain": "I1 chain verifies (3109 events)"
}
```

### 7.2 Disk

| Component | Size | Note |
|---|---:|---|
| `work/` | **886.2 MiB** | 98 worktrees, gitignored |
| `.venv/` | 43.6 MiB | environment |
| `.pm/` | 15.5 MiB | of which fleet logs 12.17 MiB; `overseer/0-0.log` 8.61 MiB |
| `.git/` | 7.4 MiB | real pack 2.67 MiB |
| `.claude/` | 6.0 MiB | includes one registered worktree |
| `pilot/` | 4.2 MiB | duplicated into every checkout ≈ 411 MiB inside `work/` |
| `src/` | 2.3 MiB | |
| `tests/` | 1.9 MiB | |
| `docs/` | 1.3 MiB | includes the 66-file corpus |
| **Total** | **≈ 969 MiB** | |

**Delivered project data ≈ 12 MiB (approximate, illustrative).** The ratio of retained disk to delivered project content is roughly **80:1** against the non-`work` tree; the figure is a guide, not a derived measurement, and the delivered source is smaller still.

### 7.3 Worktree census

| Metric | Value |
|---|---:|
| Worktrees | 98 |
| Distinct tasks owning a tree | 51 |
| Tasks with 1 tree | 26 |
| Tasks with 2 trees | 3 |
| Tasks with 3 trees | 22 |
| Trees owned by `VOID` tasks | 93 (47 tasks) |
| Trees owned by `DONE` tasks | 5 (4 tasks: `T-0118-100`, `T-0119-101`, `T-0130-102`, `T-0139-116`, `T-0139-117`) |
| Trees with uncommitted content | **56** |
| Uncommitted file entries | **488** (326 distinct content blobs) |
| Bytes in dirty trees | **514.9 MiB** |
| Trees containing `.pmwork/RESULT.md` | 68 |
| Trees containing `.pmwork/HANDOFF.md` | **0** |
| Clean trees (no uncommitted entries) | 42 |
| Active worktrees | 0 |

### 7.4 Git / scratch

| Metric | Value |
|---|---:|
| Branches | 161 |
| `pmk/*` branches | 159 |
| `.git/worktrees` entries | 107 |
| `git worktree list` entries | 108 (incl. `main` and one `.claude` worktree) |
| `%TEMP%\pmk-merge-*` directories | 20 |
| — still containing files | 19 |
| — of which hold ~10 MiB each | 8 (≈ whole 80.1 MiB) |
| — bytes | **80.1 MiB** |

### 7.5 Queue

| ID | State | Subject |
|---|---|---|
| Q-072 | decided 2026-11-06T12:31:25Z | T-0131 lease expired stall — closed "fix the cause and resume" |
| Q-073 | decided 2026-11-06T12:31:25Z | T-0136 lease expired stall — closed "fix the cause and resume" |
| Q-074 | decided 2026-11-02T20:54:21Z | T-0139 corpus integration — land from pin objects (executed as `1a5ec9b`) |
| Q-075 | decided 2026-11-06T01:09:54Z | restore `ttl_minutes = 20` |
| **Q-076** | **open (class K)** | **authorise the worktree-lifecycle remediation** |

### 7.6 Proposed tasks, and a stale `agent_hint` defect

`T-0145` and `T-0146` remain `PROPOSED` with `attempt: 0`, `fence: 0` and no lease. Verified cause: **not** an R-09 write-scope conflict. `docs/rules/index.json` and `coverage/rules_coverage.json` are clean in the main tree, and no file in either task's write scope appears in `git status`. They are simply unclaimed because the project is `PAUSED` and no dispatcher is leasing.

However, both cards carry an `agent_hint` that is now **stale and actively misleading**. It states:

> "Your worktree base (main HEAD 977b83b) does NOT contain the CNA corpus: docs/rules/CNA-Rules.adoc and docs/rules/sections/ are absent (they exist only as untracked files in the MAIN tree…). BEFORE running anything, copy the 66-file corpus … into YOUR worktree docs/rules/"

Three problems: (a) the hint is pinned to HEAD `977b83b`, but `main` is now `9eb39ad`; (b) the corpus *is* committed in `main` as of `1a5ec9b`, so it will be present in any worktree branched from current HEAD; (c) following the instruction would have the agent copy 66 files over identical files, then report a large no-op diff — or, worse, copy the CRLF variants from `work/T-0097-49` over the correct LF files.

This is recorded as **F-21** (§5): agent hints are frozen at card-creation time and are never revalidated against current HEAD, so a card can instruct an agent to undo a completed integration. It is the task-card analogue of RC-4 (a channel written once and never refreshed).

---

## 8. Decision Records

### 8.1 Q-072 — decided 2026-11-06T12:31:25Z

> **Topic:** The project stalled: lease T-0131 expired (TTL 120 min) without submission.
> **Options:** fix the cause and resume / re-scope the project / stop the project.
> **Recommended:** fix the cause and resume. **Safe default:** stop the project.
> **Choice:** "fix the cause and resume - the stall cause was the relative-path order defect and the worktree-isolation gap (fixed in 77a8659, hardened in aed9aec); successor task T-0139 completed and the corpus landed in main at 1a5ec9b. Recorded by the operator on 2026-11-07. The project remains PAUSED by a separate operator decision; this decision does not unpause it."

### 8.2 Q-073 — decided 2026-11-06T12:31:25Z

> **Topic:** The project stalled: lease T-0136 expired (TTL 120 min) without submission.
> **Options:** fix the cause and resume / re-scope the project / stop the project.
> **Recommended:** fix the cause and resume. **Safe default:** stop the project.
> **Choice:** "fix the cause and resume - the stall cause was the same relative-path order defect and worktree-isolation gap (fixed in 77a8659, hardened in aed9aec); successor task T-0139 completed and the corpus landed in main at 1a5ec9b. Recorded by the operator on 2026-11-07. The project remains PAUSED by a separate operator decision; this decision does not unpause it."

### 8.3 Q-074 — decided 2026-11-02T20:54:21Z (class K, pre-existing)

> **Topic:** T-0139 integration blocked: main's `docs/rules/` held an UNCOMMITTED pre-staged corpus (`M manifest.json`, `M checksums.sha256`, `?? CNA-Rules.adoc`, `?? sections/` 65 files). T-0139's completed branch (`pmk/T-0139-117`, 66/66 sha256 vs pin `75a037f`) could not merge over uncommitted work; harness failed 3 times.
> **Choice:** "Neither option 1 nor 2. Main's uncommitted corpus is off-pin (CRLF; CNA-Rules.adoc sha256 e585... vs pin 5654...). Land the corpus from the pin objects instead (tcanf-clone@75a037f, 66 files staged byte-exact at `C:\temp\corpus-staging-75a037f`, 66/66 git blob ids verified): back up main's docs/rules and coverage, replace with the staged files, regenerate manifest, checksums, index and coverage, add `docs/rules/** -text` to `.gitattributes`, commit once citing this decision. Branch `pmk/T-0139-117` is superseded and stays unmerged."

**Execution status: complete.** Commit `1a5ec9b` (2026-11-03) implements exactly this choice. This report verified the result independently: `git status --porcelain docs/rules/` is empty; HEAD `manifest.json` and `checksums.sha256` verify 66/66 against the working files; all 66 files are present in `git ls-tree -r HEAD`; and CRLF-normalised comparison against the upstream export at `C:\temp\projects\cfna\docs\sources\cna-rules-upstream` is identical for 66/66 (upstream is CRLF with 17,040 CRLF lines; `main` is LF; content is the same).

### 8.4 Q-075 — decided 2026-11-06T01:09:54Z

> **Choice:** "approve: restore `ttl_minutes = 20` in `.pm/policy.toml` and re-record the policy pin. Per the operator's standing decision D-3 (`pilot/decisions.md`: revert TTL to 20, one decision id covering policy, pin and conductor change), conditional on the orphan-only lease reaper being landed and reviewed. Condition met 2026-11-06: commits `62af455` (lease reap) and `9eb39ad` (edge-triggered wakes) applied to the live repo; 463 tests pass in the live tree."

Relevance here: TTL was 120 minutes during the period that produced 58 TTL-expiry revocations. Reducing it to 20 minutes shortens the exposure window per lease but **does not address RC-1/REC-03** — a shorter TTL produces *more* fence bumps per unit work, so without REC-01/REC-02 it would increase the leak rate, not decrease it. This interaction should be considered before the fleet is unpaused.

### 8.5 Q-076 — open, class K (recorded by this report)

> **Topic:** Worktree lifecycle defect: 98 worker worktrees (886 MiB) are never reclaimed, and 56 of them hold uncommitted work that was never merged. Authorise a fix at the point the lease fence bumps.
> **Options:** implement the reclaim-at-fence-bump fix now / document only — no code change (current position) / re-scope: add a `pmk worktree prune` command instead of an automatic reclaim / stop and close the project.
> **Recommended:** implement the reclaim-at-fence-bump fix now.
> **Safe default:** document only — no code change; `work/` grows by roughly 9 MiB per lease give-up and stranded unmerged work continues to accumulate.
> **Details:** this report. Per-tree inventory at §12.

---

## 9. Task Churn and Loop Volume

### 9.1 Leases vs tasks

| Metric | Value |
|---|---:|
| Task cards created | 146 |
| Distinct task IDs | 146 |
| Cards voided | 138 (94.5%) |
| Cards done | 6 (4.1%) |
| Cards proposed | 2 |
| Claims | 112 |
| Revocations | 108 |
| Agent starts | 104 |
| Worktrees | 98 |
| Distinct tasks with a worktree | 51 |

A task that is voided without ever being claimed still has no worktree — which is why 146 cards produced 98 trees across 51 tasks, not 146 trees. 95 of 146 cards never produced a checkout at all; those failed at admission or on scope conflict.

### 9.2 Revocation reasons (108 total)

| Count | Reason |
|---:|---|
| **58** | lease TTL expired |
| 16 | voided: malformed write scope (comma-joined); recreated per Q-013 |
| 3 | release completed lease |
| 3 | orcarouter free tier rate limited; re-dispatch to cline |
| 2 | pi-orca still higher priority; re-dispatch to cline |
| 2 | scope overlap with T-0026 |
| 2 | attempts exhausted (3/3) |
| 2 | scope overlap blocking all P0 tasks |
| 2 | voided: scope overlap with other READY tasks |
| 2 | stale lease, agent too slow |
| 16 | various single occurrences (dead pid, oracle failure, prompt fix, stale dispatch, doomed work, superseded) |

**The single largest cause is a timeout, not a fault** (53.7%). That is the diagnostic that matters: the dominant loss mechanism is not "the agent did bad work", it is "the agent ran out of time and its work was discarded". Anything that preserves partial work across a timeout eliminates more than half of all loss.

### 9.3 Duplicated work (reissue clusters)

| Work described | Times issued |
|---|---:|
| Vendor rules at pinned commit into `docs/rules/` | 13 |
| Coverage tool (`src/cna/tools/coverage.py`) | 9 |
| `src/cna/core/` primitives | 5 |
| Repo skeleton (`pyproject.toml`, `pytest.ini`, `AGENTS.md`, `CLAUDE.md`) | 6 |
| `src/cna/tools/show_rule.py` | 4 |
| `src/cna/engine/` core | 4 |
| PDD (`docs/PDD.md`) | 3 |
| `src/cna/state/` | 3 |
| `src/cna/engine/rulesets.py` | 3 |
| `src/cna/tools/rules_index.py` | 3 |

Each row is a scope that was re-derived from scratch at least twice.

### 9.4 Sentinel output (verbatim)

`ok: False`; checked `['I1','I3','I4','I5','I6','I7',"I8'",'I13','I14','I15','I16']`; 6 findings:

```
I6  task T-0118 INTEGRATED event has no bundle reference   stops=true
I6  task T-0119 INTEGRATED event has no bundle reference   stops=true
I6  task T-0127 INTEGRATED event has no bundle reference   stops=true
I6  task T-0129 INTEGRATED event has no bundle reference   stops=true
I6  task T-0130 INTEGRATED event has no bundle reference   stops=true
I5  empty_commit_in_integrated  commit=""  subject=T-0139   stops=false
```

No invariant in the current set detects worktree accumulation, tree age, or total bytes in `work/`. `I6` does not cover it. `I13` (views current) does not cover it. This is why REC-06 proposes a new observation rather than relying on the existing set.

### 9.5 Loop character

`863 FLEET_BLOCKED` against `112 CLAIMED` is a ratio of 7.7 blocking events per unit of work started. The 423 `OVERSEER_WOKEN` span ~11.6 days (mean ~one per 39 minutes); the denser signal is `FLEET_BLOCKED`, 863 events over ~2.3 days (mean ~one per 4 minutes). The Overseer was not malfunctioning — it was correctly reporting that the same class-K item was undecided. The cost is that a genuine new finding (this one) competes with 863 repetitions of a known one for operator attention.

---

## 10. Handoff and Traceability Defects

### 10.1 The handoff channel

| Element | Exists | Called | Reachable by agent |
|---|---|---|---|
| `HANDOFF_FILE = "HANDOFF.md"` (`order.py:31`) | yes | — | — |
| `handoff_path()` (`order.py:43`) → `.pmwork/HANDOFF.md` | yes | — | — |
| `write_handoff()` (`order.py:178`) | yes | `harness.py:586`, `dispatcher.py:383`, `cli.py:617` | none on give-up/expiry |
| `render_handoff()` | yes | `harness.py:581` | — |
| `ORDER.md` `## Handoff` section | yes | `render_order` once at `harness.py:347` | always reads `none` |
| `order_prompt()` mention of `HANDOFF.md` | **no** | — | agent never told it exists |

**Consequence.** A replacement agent in a reused worktree (RC-2, `L0`–`L2`) receives a correct checkout but no instruction to look for prior context, and the `ORDER.md` it *is* told to read says there is no handoff. The agent therefore re-derives scope from the card. This is the mechanism behind §9.3: the reissue clusters are not merely wasteful re-descriptions by the Overseer, they are re-*implementations* by agents that were never told what the previous agent did.

**Verified count.** `.pmwork/HANDOFF.md` exists in 0 of 98 worktrees. Root `HANDOFF.md` (4,692 bytes at report time; ~6,088 bytes re-measured 2026-11-07; tracked) is unrelated repository content and must not be counted as evidence of the mechanism working.

### 10.2 The T-0139 traceability gap

`T-0139` is `DONE`. Its `INTEGRATED` event carries `commit: ""`. The branch `pmk/T-0139-117` was **deliberately** superseded (Q-074) and its tip `2a0f6fa` (`2a0f6fa2fa371d93e6a0112f9016c1643dcc1d18`) is not an ancestor of `main` — by decision, not by accident. The content that task was responsible for is in `main` at `1a5ec9b`.

So the state is: correct outcome, untraceable provenance. `I5` reports it non-stopping; the audit trail cannot connect "task T-0139 delivered the corpus" to "commit `1a5ec9b`" without reading the queue decision and commit message together. REC-11 closes this.

### 10.3 Why this matters more than it looks

An empty `commit` in `INTEGRATED` is the exact shape a genuinely lost integration would also take. The system cannot currently distinguish "superseded out of band, content verified present" from "reported success, content never landed". `T-0139` is the first case. `T-0101`'s three abandoned implementations are, in effect, the second case operating in the opposite direction — work done, never integrated, never reported as lost. Closing the traceability gap is what makes the two distinguishable at scale.

---

## 11. Cross-Project Comparison (`b5ccg`)

The comparison that motivated the original question was disk size: `testproject1` ≈ 969 MiB, `b5ccg` ≈ 2.3 GB. Size alone does not indicate which workflow works better, because the two grow for different reasons.

Both columns are a **dated snapshot measured 2026-11-07** — not current fact; `b5ccg` is a live repository and has since moved again. The values below are from the second (later) pass and differ from the first pass (`out_gate_*` grew 170.0 MiB/40 dirs → 195.5 MiB/46 dirs in the interval).

| Metric | `testproject1` (UMAWS fleet + `pmk`) | `b5ccg` |
|---|---:|---:|
| Total | 969 MiB | 2,327.7 MiB |
| Dominant consumer | `work/` 886.2 MiB (91.5%) | `scratch/` 1,230.1 MiB (34 dirs) |
| Second consumer | `.venv/` 43.6 MiB | `.agent/` 313.8 MiB |
| Third | `.pm/` 15.5 MiB | `.git/` 236.9 MiB |
| Generated gate trees | — | `out_gate_*` 195.5 MiB (46 dirs) |
| Combine two largest generated classes | — | `scratch/` + `out_gate_*` = **61.2%** |
| Kernel / worktree system | yes (`.pm/`, 98 worktrees) | **no** — no `.pm/`, no `pmk` |

**Interpretation.** `b5ccg` does not use the `pmk` worktree workflow at all, and its `work/` equivalent is empty (`.pm/` is absent). It reaches 2.3 GB by a *different* leak of the *same class*: generated per-run directories (`scratch/`, `out_gate_*`) that are never collected. `scratch/` and `out_gate_*` together are 61.2% of that repository, and `out_gate_*` is itself growing between measurements. Both projects exhibit **uncollected per-run artefacts**. Neither is evidence that the other is better; both are evidence that "create a directory per attempt" without "collect the directory when the attempt ends" produces unbounded growth.

The difference that matters is not the size. It is that `testproject1`'s leak is **invisible** (gitignored, unmeasured), whereas `b5ccg`'s `scratch/` is at least visible to a directory listing in the repo root. Visibility is what determines whether the leak is found by a human or by a 1 GB surprise.

---

## 12. Stranded Work Inventory (56 trees, 488 uncommitted entries / 326 distinct content blobs, 514.9 MiB)

Every tree below belongs to a task whose state is `VOID`. The 488 entries resolve to **326 distinct git blobs** (162 are redundant copies; the corpus trio alone overlaps heavily). Nothing in this table has been moved, archived or deleted. "Agent's stated result" is quoted from that tree's `.pmwork/RESULT.md` where one exists; it is the agent's own claim and is **not verified** (fleet rule 18).

| Worktree | State | Entries | MiB | Uncommitted content | Agent's stated result |
|---|---|---:|---:|---|---|
| `T-0004-35` | VOID | 1 | 8.7 | `pi-test.txt` | Checked premises: none listed, nothing to verify. |
| `T-0006-29` | VOID | 1 | 8.7 | `hello.txt` | Wrote `hello.txt` at worktree root, file scope only. |
| `T-0007-10` | VOID | 2 | 10.0 | `docs/PDD.md`, `tests/fleet/_fake_hermes_cli.py` | Wrote PDD with seven required sections, two sequential goals, acceptance criteria, gate_cmd; `pmk pdd lint` exit 0. |
| `T-0007-27` | VOID | 1 | 8.7 | `docs/PDD.md` | PDD for "CNA digital edition" (Python, Windows 10), Phase P0. |
| `T-0007-30` | VOID | 1 | 8.7 | `docs/PDD.md` | PDD derived from `proposal-cfna-game-v1.md` and `proposal-cfna-claude-v1.md`; six goals G-001..G-006. |
| `T-0008-11` | VOID | 6 | 8.7 | `.gitattributes`, `AGENTS.md`, `CLAUDE.md` (+3) | T-0008 implementation complete. |
| `T-0009-12` | VOID | 5 | 8.7 | `docs/rules/{checksums.sha256,fleet-spawning.md,kernel-writing.md}` (+2) | Vendored `.claude/rules/*` into `docs/rules/` at pin `09df0f6`, added checksums. |
| `T-0010-13` | VOID | 2 | 10.2 | `src/cna/tools/rules_index.py`, `tests/test_rules_index.py` | (header only) Type: implement, Goal: G-001 |
| `T-0011-14` | VOID | 2 | 8.7 | `src/cna/tools/__init__.py`, `src/cna/tools/show_rule.py` | Implemented `show_rule(case, cross_references=None)` and `ShowRuleTool.run`; no spec/tests available. |
| `T-0013-16` | VOID | 6 | 10.0 | `src/cna/__init__.py`, `src/cna/core/{__init__,dice}.py` (+3) | Implemented `src/cna/core/` ids, errors, dice (d6, 2d6, sequential 11-66), seeded RNG. |
| `T-0014-17` | VOID | 3 | 8.7 | `src/cna/__init__.py`, `src/cna/state/{__init__,state}.py` | Implemented CNA state model, JSON serialisation, schema v1, sha256 state hash. |
| `T-0015-18` | VOID | 2 | 8.7 | `src/cna/__init__.py`, `src/cna/core/__init__.py` | (no result text) |
| `T-0017-20` | VOID | 3 | 8.7 | `docs/data-gaps.md`, `src/cna/__init__.py`, `src/cna/tools/__init__.py` | Implemented `data_gaps.py` gap-register generator for R-02..R-05. |
| `T-0018-21` | VOID | 2 | 8.7 | `.fakecli-session.json`, `src/cna/engine/` | (no result text) |
| `T-0019-22` | VOID | 2 | 8.8 | `src/cna/rules/sec05_sequence.py`, `tests/test_sequence.py` | (task-card restatement) |
| `T-0020-23` | VOID | 4 | 10.0 | `src/cna/rules/{sec07_initiative,sec29_weather}.py`, `tests/conftest.py` (+1) | Implemented section 7 (initiative) and section 29 (weather) rule modules. |
| `T-0021-24` | VOID | 7 | 8.8 | `src/cna/__init__.py`, `src/cna/engine/{__init__,sealed}.py` (+4) | Implemented hidden information: `view()`, sealed commits. |
| `T-0022-25` | VOID | 28 | 8.8 | `cna/__init__.py`, `sitecustomize.py`, `src/cna/__init__.py` (+25) | Implemented P1a walking skeleton subset needed for the soak oracle. |
| `T-0023-26` | VOID | 3 | 8.8 | `docs/decisions/RD-0001.md`, `src/cna/engine/rulesets.py`, `tests/test_rulesets.py` | Rulesets module (LAND_ABSTRACT only) and section 2.0 combination check. |
| `T-0024-31` | VOID | 3 | 8.8 | `.gitattributes`, `pytest.ini`, `tests/test_smoke.py` | Created three missing skeleton files. |
| `T-0024-37` | VOID | 4 | 9.5 | `pyproject.toml`, `src/quotagate/__main__.py`, `pytest.ini` (+1) | Repo skeleton: `pyproject.toml`, `.gitattributes`, `AGENTS.md`, `CLAUDE.md`. |
| `T-0024-39` | VOID | 8 | 10.0 | `.gitattributes`, `pyproject.toml`, `src/console/__init__.py` (+5) | Verified skeleton files present within scope. |
| `T-0025-32` | VOID | 9 | 8.7 | `docs/rules/CHECKSUMS`, `PINNED_COMMIT`, `checksums.json` (+6) | Vendored `.claude/rules/*` at pin `09df0f6c`. |
| `T-0025-38` | VOID | 5 | 8.7 | `docs/rules/CHECKSUMS.sha256`, `MANIFEST.md`, `fleet-spawning.md` (+2) | Vendor rules at pinned commit with checksums manifest. |
| `T-0025-40` | VOID | 4 | 8.7 | `docs/rules/CHECKSUMS.sha256`, `fleet-spawning.md`, `kernel-writing.md` (+1) | author_llm: Laguna S 2.1 (poolside) |
| `T-0026-43` | VOID | 1 | 8.9 | `src/cna/tools/rules_index.py` | Task completed within write scope. |
| `T-0046-33` | VOID | 2 | 8.7 | `a.py`, `b.py` | Created `a.py` and `b.py` as minimal valid modules. |
| `T-0048-34` | VOID | 2 | 8.7 | `hello.txt`, `foo.py` | author_llm: Laguna S 2.1 (poolside) |
| `T-0096-44` | VOID | 4 | 8.8 | `pytest.ini`, `src/cna/__init__.py`, `src/cna/tools/__init__.py` (+1) | Repo skeleton: `pyproject.toml`, `.gitattributes`, `AGENTS.md`, `CLAUDE.md`, `pytest.ini`, `src/`, `tests/test_smoke.py`. |
| `T-0096-46` | VOID | 6 | 10.1 | `.gitattributes`, `pyproject.toml`, `pytest.ini` (+3) | Same repo-skeleton scope (second attempt). |
| `T-0096-48` | VOID | 6 | 9.4 | `.gitattributes`, `pyproject.toml`, `pytest.ini` (+3) | Created repository skeleton for `cna` package (third attempt). |
| `T-0097-45` | VOID | 68 | 9.5 | 66 corpus files + `manifest.json` + `checksums.sha256` | Vendored 66 rules files from pin `75a037f`, preserved CRLF. |
| `T-0097-47` | VOID | 68 | 9.5 | 66 corpus files + `manifest.json` + `checksums.sha256` | Vendored CNA rules at pin `75a037f` (second attempt). |
| `T-0097-49` | VOID | 68 | 9.5 | 66 corpus files + `manifest.json` + `checksums.sha256` | Vendored 66 rules files preserving original bytes (third attempt). |
| `T-0099-52` | VOID | 2 | 8.9 | `src/cna/tools/show_rule.py`, `tests/test_show_rule.py` | Implemented `show_rule.py` and its tests. |
| `T-0099-63` | VOID | 2 | 8.9 | `src/cna/tools/show_rule.py`, `tests/test_show_rule.py` | Implemented `show_rule.py`: loads/builds index, resolves targets, returns cross-references. |
| `T-0100-53` | VOID | 2 | 8.9 | `src/cna/tools/coverage.py`, `tests/test_coverage.py` | Wrote two files within declared write scope. |
| `T-0100-64` | VOID | 4 | 10.2 | `src/cna/__init__.py`, `src/cna/tools/__init__.py`, `coverage.py` (+1) | Implemented CNA coverage analyser and its tests. |
| `T-0100-75` | VOID | 3 | 10.2 | `coverage/rules_coverage.json`, `src/cna/tools/coverage.py`, `tests/test_coverage.py` | (no result text) |
| **`T-0101-54`** | VOID | 6 | 8.8 | `src/cna/core/{__init__,dice,errors}.py` (+3) | Implemented CNA core primitives; `pytest tests/test_dice.py` passed, 11 tests. |
| **`T-0101-65`** | VOID | 10 | 9.4 | `src/cna/core/{__init__,dice,dice_roller}.py` (+7) | Implemented CNA core package; ids, errors, dice, seeded RNG; 11 tests pass. |
| **`T-0101-76`** | VOID | 3 | 10.2 | `src/cna/core/{__init__,dice}.py`, `tests/test_dice.py` | Implemented core dice/id/RNG module; richer variant with `roll_11_66`; 27 passed. |
| `T-0102-66` | VOID | 7 | 10.3 | `src/cna/state/{__init__,codec,digest}.py` (+4) | Implemented; no premise refuted. |
| `T-0102-77` | VOID | 1 | 8.8 | `src/cna/state/__init__.py` | Implemented `State` dataclass: JSON serialisation, schema_version 1, sha256 state hash, round-trip. |
| `T-0103-91` | VOID | 3 | 10.3 | `src/cna/core/events.py`, `src/cna/tools/replay.py`, `tests/test_replay.py` | Implemented "event log and replay" feature. |
| `T-0104-56` | VOID | 7 | 8.8 | `data/.gitkeep`, `src/cna/data/{__init__,provenance}.py` (+4) | Created `src/cna/data/` package with schema/validators/provenance/status; import verified. |
| `T-0104-67` | VOID | 5 | 8.9 | `src/cna/__init__.py`, `src/cna/data/{__init__,schemas}.py` (+2) | Implemented data schemas, validators, provenance/status under G-001. |
| `T-0105-57` | VOID | 3 | 8.8 | `docs/data-gaps.md`, `src/cna/tools/data_gaps.py`, `tests/test_data_gaps.py` | Created data-gaps tool and tests; 2/2 pass. |
| `T-0106-58` | VOID | 7 | 9.0 | `src/cna/engine/{__init__,actions,engine}.py` (+4) | Decision-point model: `Decision`, `Action`, `pending`, `legal_actions`, `apply`. |
| `T-0106-69` | VOID | 4 | 10.3 | `src/cna/engine/{__init__,errors,model}.py` (+1) | Implemented; `pytest tests/test_engine_contract.py` 29 passed, exit 0. |
| `T-0107-59` | VOID | 2 | 8.8 | `src/cna/rules/sec05_sequence.py`, `tests/test_sequence.py` | Implemented sequence-of-play state machine data (§5.2, Appendix B). |
| `T-0109-92` | VOID | 3 | 10.3 | `src/cna/engine/sealed.py`, `src/cna/state/views.py`, `tests/test_views.py` | No premises listed, so no premise-refuted path applies. |
| `T-0110-61` | VOID | 2 | 8.8 | `src/cna/__init__.py`, `src/cna/tools/_ns_probe.py` | (no result text) |
| `T-0111-87` | VOID | 3 | 9.0 | `docs/decisions/RD-0001.md`, `src/cna/engine/rulesets.py`, `tests/test_rulesets.py` | Rulesets module and section 2.0 combination check; copied files into place. |
| `T-0131-110` | VOID | 68 | 9.6 | 66 corpus files + `manifest.json` + `checksums.sha256` | Vendor the full 66-file CNA corpus at pin `75a037f` with checksums manifest. |
| `T-0142-119` | VOID | 2 | 8.9 | `coverage/rules_coverage.json`, `src/cna/tools/coverage.py` | Extended coverage discovery to walk recursively, include `*.md` and `*.adoc`; regenerated coverage. |

### 12.1 What this inventory establishes

1. **The content is unique.** Spot-checked confirmations: `src/cna/core/` (three variants, 19 files across the three trees) exists in neither `HEAD` nor the working tree; `src/cna/state/`, `src/cna/engine/`, `src/cna/data/`, `src/cna/tools/show_rule.py`, `src/cna/tools/data_gaps.py`, `src/cna/tools/rules_index.py` are all listed as untracked in their trees.
2. **The content is not reachable.** No branch contains it — these are uncommitted working-tree changes; the branches `pmk/<task>-<fence>` point at the base commit the tree was created from.
3. **Deleting these trees destroys it.** There is no archive, no patch, no bundle.
4. **Four trees are corpus duplicates, not losses.** `T-0097-45/47/49` hold byte-identical CRLF copies of the corpus, and `T-0131-110` holds LF copies byte-identical to `1a5ec9b`; the content is committed at `1a5ec9b` in LF form and verified equivalent after normalisation. These four can be reclaimed without any capture step, provided the equivalence check in §8.3 is trusted. They account for ~38 MiB.
5. **`T-0101` is the archetype.** Three trees, three implementations, one module, zero deliveries. It is the single clearest justification for REC-02 preceding REC-01.

### 12.2 Suggested handling (not performed)

Ordered, reversible first:

1. Capture every dirty tree per REC-02 (`git diff --binary` + untracked-file archive + `.pmwork/RESULT.md`) into a durable location **outside** `work/`.
2. Verify each archive is readable and non-empty.
3. Only then reclaim. First the 42 clean trees (~371.3 MiB), then the 4 corpus-duplicate trees (~38.1 MiB), then the remaining 52 dirty trees (~476.8 MiB) once archived. (Check: 371.3 + 38.1 + 476.8 = 886.2 MiB = the whole of `work/`.)
4. Reclaim `%TEMP%\pmk-merge-*` (80.1 MiB) independently — these are merge scratch and contain no unique content.
5. `git worktree prune` for the 107 stale `.git/worktrees` entries.

Expected recovery: ~966 MiB of the ~969 MiB total, leaving roughly 83 MiB (source, docs, kernel, `.git`, virtualenv).

---

## 13. Actor Attribution

The Kernel records an advisory `actor` on each state-changing event (`PMK_ACTOR`, `src/pmk/api.py:41`). It is explicitly **not** an authentication boundary; any caller can set it.

| Actor | Kind | Events / role | Notes |
|---|---|---|---|
| `human:tiwa-pene` | human | Q-072, Q-073 decisions; Q-076 creation (seq 3107–3109) | Operator. Also author of `1a5ec9b`, `977b83b`, `9eb39ad`, `62af455`, `93a3366`, `8a71d36`, `19dc337`, `5b21024` |
| `overseer:*` | overseer | 423 `OVERSEER_WOKEN`, 863 `FLEET_BLOCKED`, 102 `INCIDENT` | Re-detected blocked conditions repeatedly; no independent write authority |
| `worker:<profile>` | worker | 112 `CLAIMED`, 104 `AGENT_STARTED`, 108 `REVOKED` | Fleet-spawned agents across profiles (pi-orca, opencode-strongest, hermes-oneshot, cline, poolside, orcarouter, etc.) |
| `kernel` / system | kernel | `TASK_CREATED` 146, `TASK_VOIDED` 138, `INTEGRATED`, `PROJECT_STATE` 81 | Deterministic Kernel writes |
| `umaws-pilot` | agent | `977b83b` (manifest fix) | Commit author; `umaws-pilot@localhost` |
| `DeepSeek V4.1 Flash Free` | author of this report | none — read-only | Made no state change except the three authorised queue actions above, recorded under `human:tiwa-pene` |

**Attribution note.** The three governance events in seq 3107–3109 were issued by this agent on the operator's explicit instruction, and were recorded under the operator's actor identity because a class-K decision is an operator decision. This is disclosed rather than concealed: the agent executed the mechanics, the operator supplied the decision. Under R-13 step 1, this report must be reviewed by an LLM that did not write it.

---

## 14. Lessons Learned

1. **A "keep on failure" policy without a "collect on completion" policy is not a retention policy, it is a leak.** `harness.py:19` documents only the keep half. Any intentional retention needs a stated lifetime and an owner.

2. **Code that exists and is never called is worse than code that does not exist,** because its presence makes the gap invisible to review. `remove_worktree()` reads as though deletion is handled. A periodic "dead public function" check would have caught this.

3. **Deriving a resource path from a safety token makes every safety event expensive.** The fence must bump for `I4` correctness; tying the worktree name to it converts a correctness requirement into a storage cost. The path should be stable per task; the *permission* to merge should be fenced.

4. **Timeouts are the dominant loss mode, not bad work.** 58 of 108 revocations were TTL expiry. Preserving partial output across a timeout addresses more than half of all loss.

5. **A half-wired channel is indistinguishable from a missing one.** Writing `HANDOFF.md` into a directory the prompt never mentions produces exactly zero behaviour change, at the cost of looking implemented.

6. **Gitignored means unmeasured, not unimportant.** The largest data in the repository was the least visible. `pmk status` reporting task counts but not `work/` bytes is a dashboard that cannot see its own cost.

7. **A permanently red stop-invariant trains operators to ignore the sentinel.** Five sustained `I6` failures have made "sentinel not ok" the normal state.

8. **Reissue is cheap locally and expensive globally.** 94.5% void with 13 re-descriptions of one scope is a workflow that measures task creation, not work delivered.

9. **Verify before repeating a briefing.** The "corpus at risk" claim was five days stale and would have sent this investigation down the wrong path; the event log and git store settled it in minutes. Briefings are derived views; the log is the source of truth.

10. **Leave the door open for the operator.** The leak cannot be fixed by deleting, because the leak is currently the only backup. Sequencing — capture, verify, reclaim — matters more than the reclaim itself.

11. **A card is a snapshot; the repository is not.** `agent_hint` is written once and read days later against a different HEAD. Any hint that asserts what a file or directory *contains* is a claim with an expiry date. Either revalidate at lease time or state facts that cannot rot ("read `docs/rules/README.md`") instead of facts that can ("the corpus is absent").

---

## 15. Commit References

Verified against `git log` on `main` at `HEAD 9eb39ad`.

| Commit | Date | Subject | Relevance |
|---|---|---|---|
| `9eb39ad` | 2026-11-05 | fleet: edge-triggered, PAUSED-aware Overseer wakes | Current HEAD; reduces redundant wakes |
| `62af455` | 2026-11-05 | fleet: reap expired, orphaned leases in the Conductor | Reaps leases; **does not** reclaim worktrees (RC-3) |
| `5b21024` | 2026-11-04 | tests: reach the NO_CHANGES branch through a real fake-CLI run | Harness test coverage |
| `19dc337` | 2026-11-04 | fleet: refuse to start on agents.toml errors; add pmk fleet check | Admission hardening |
| `8a71d36` | 2026-11-04 | fleet: merge through a temporary worktree and fast-forward only | Origin of the `%TEMP%\pmk-merge-*` trees (F-09) |
| `93a3366` | 2026-11-04 | pmk, fleet: verify integrate commits; fix NO_CHANGES and R-09; oracle lint at admission | Integration verification; empty-commit case remains (F-15) |
| **`1a5ec9b`** | 2026-11-03 | **corpus: land CNA rules corpus from pin 75a037f (66 files, byte-exact)** | **Resolves Q-074; F-16** |
| `393d0ea` | 2026-11-02 | evidence: add Relay D evidence report for assessment findings | Prior evidence bundle |
| `6e3afaf` | 2026-11-02 | docs: add incident report v3 (R-02–R-11 implemented, R-12–R-13 documented) | **Defines the R-12 standard used here** |
| `aed9aec` | 2026-11-02 | feat(fleet): implement R-02/R-03/R-09/R-10/R-11 worktree isolation hardening | Isolation hardening; no lifecycle reclamation added |
| `aaa76fb` | 2026-11-02 | docs: add comprehensive incident report v2 | Predecessor report |
| `977b83b` | 2026-11-02 | fix: update manifest and checksums to 66-file corpus (pin 75a037f) | Pre-`1a5ec9b` manifest correction |
| `77a8659` | 2026-11-02 | fix(fleet): use absolute worktree order path in agent prompt; add incident report | The relative-path defect fix cited in Q-072/Q-073 |
| `6764d54` | — | T-0003 integration (same-fence reuse at fence 3; the `work/T-0003-3` directory no longer exists — F-22) | Proof of same-fence worktree reuse (by log, not by the absent directory) |

**No commit in this report was made by the author.** No code was changed.

---

## Appendix A — Raw Event Timeline (selected, authoritative)

Events below are reproduced from `.pm/events/*.jsonl`; `seq` values are authoritative. Only T-0101 is shown event-by-event; other sequences are summarised in §3 and §9.2.

```
seq 1736  2026-10-31T20:59:46Z  CLAIMED        T-0101  fence=54
seq 1737  2026-10-31T20:59:48Z  AGENT_STARTED  T-0101  fence=54
seq 1795  2026-10-31T21:19:48Z  REVOKED        T-0101  fence=54  "lease TTL expired"
seq 1832  2026-10-31T21:20:54Z  CLAIMED        T-0101  fence=65
seq 1833  2026-10-31T21:20:57Z  AGENT_STARTED  T-0101  fence=65
seq 1908  2026-10-31T21:40:56Z  REVOKED        T-0101  fence=65  "lease TTL expired"
seq 1962  2026-10-31T22:07:38Z  CLAIMED        T-0101  fence=76
seq 1963  2026-10-31T22:07:44Z  AGENT_STARTED  T-0101  fence=76
seq 2109  2026-11-01T00:07:39Z  REVOKED        T-0101  fence=76  "lease TTL expired"
seq 2213  2026-11-01T05:35:19Z  TASK_VOIDED    T-0101  fence=85  "reset attempts exhausted"
```

Totals: 3,109 events, first `2026-10-22T05:56:24Z`, last `2026-11-06T12:32:21Z` (seq 3109). I1 chain verifies.

---

## Appendix B — R-12 Conformance Map

| R-12 requirement | Location in this report |
|---|---|
| 1. YAML frontmatter | File header |
| 2. Provenance block | Header block (§ frontmatter + metadata) |
| 3. Executive Summary | §1 |
| 4. Incident Timeline | §3 |
| 5. Root Cause Analysis with file:line | §4 |
| 6. Findings Table with status | §5 |
| 7. Recommendations Table with status | §6 |
| 8. Current State | §7 |
| 9. Decision Records with full text | §8 |
| 10. Evidence Artifacts | §7 (measured artefacts), §12 (inventory), Appendix C |
| 11. Raw Event Timeline Appendix | Appendix A |
| 12. Actor Attribution Appendix | §13 (numbered per Q-076's cross-reference; §12 is the per-tree inventory) |
| 13. Lessons Learned | §14 |
| 14. Commit References | §15 |
| Naming convention `incident-report-<topic>-v<N>.md` | `incident-report-worktree-lifecycle-leak-v1.md` in project root ✔ |

**Deviation declared:** R-12 numbers the stranded-work inventory nowhere; the open queue item Q-076 refers to it as "section 12". §12 is therefore the inventory and the Actor Attribution appears at §13. This is a numbering choice, not a missing element.

---

## Appendix C — Evidence and Reproducibility

| Evidence | Command / path |
|---|---|
| Event totals and types | `Get-ChildItem .pm/events -Filter *.jsonl` → parse JSON → `Group-Object type` (filter `*.jsonl` only; `2026-10-31.jsonl.bak` double-counts) |
| T-0101 lifecycle | filter `subject -eq 'T-0101'` over event types `CLAIMED/AGENT_STARTED/REVOKED/TASK_VOIDED` |
| Worktree census | `Get-ChildItem work -Directory`; per-tree `git -C <tree> status --porcelain -uall` |
| Per-tree bytes | `Get-ChildItem <tree> -Recurse -Force -File \| Measure-Object Length -Sum` |
| Dead code proof | `Select-String -Path src,tests -Recurse -Pattern remove_worktree` → one hit (the definition) |
| Handoff absence | `Get-ChildItem work -Recurse -Filter HANDOFF.md \| ? FullName -match '\\\.pmwork\\'` → 0 |
| Corpus verification | `git ls-tree -r HEAD`, `git status --porcelain docs/rules/`, sha256 of all 66 files vs `HEAD:docs/rules/manifest.json` and `checksums.sha256`, CRLF-normalised comparison vs `C:\temp\projects\cfna\docs\sources\cna-rules-upstream` |
| Sentinel | `pmk.sentinel.check(Kernel(Path('.')))` → 6 findings (§9.4) |
| Branches / worktrees | `git branch --list`, `git worktree list`, `Get-ChildItem .git/worktrees -Directory` |
| Temp merge trees | `Get-ChildItem $env:TEMP -Directory -Filter pmk-merge-*` |
| b5ccg comparison | recursive byte measurement of `C:\temp\projects\b5ccg`, `scratch/`, `out_gate_*`, `.git`, `.agent`, `node_modules` |

---

## Appendix D — Corrections to Prior Claims

This appendix exists because a previous statement in this investigation was wrong and has been repeated as an open blocker. Recording it is part of the provenance obligation.

### D.1 The T-0139 corpus is not at risk (corrected)

**Prior claim:** "The 66-file CNA corpus survives only in `work/T-0139-117`, `work/T-0097-49`, and untracked files in the main tree. Pruning `work/` would destroy it. This is open queue item Q-074."

**Corrected finding:** The corpus is committed to `main` at `1a5ec9b` (2026-11-03). Verified this session: `git status --porcelain docs/rules/` is empty; 66 `.adoc` files are present in `git ls-tree -r HEAD`; `HEAD:docs/rules/manifest.json` and `checksums.sha256` both verify 66/66 against the working files; the working copy matches upstream content 66/66 after CRLF→LF normalisation (upstream is CRLF, `main` is LF, `docs/rules/** -text` in `.gitattributes` protects the bytes). Q-074 is `decided` (2026-11-02), not open, and its chosen option was executed by `1a5ec9b`.

**Cause of the error:** the Overseer briefing's 2026-11-02 narrative was taken as current state without independent verification against `git ls-tree HEAD` and `git status`. The briefing was accurate on 2026-11-02; it was resolved the following day.

**Residual issue:** only the traceability gap (F-15 / REC-11) remains. No content is at risk.

### D.2 "Zero HANDOFF.md exist" (clarified)

**Prior phrasing:** "zero `HANDOFF.md` exist in any of the 98 worktrees."

**Corrected finding:** A recursive search returns 196 hits, because a *tracked repository file* named `HANDOFF.md` (4,692 bytes, dated 2026-10-30) is present in every checkout, alongside `.claude/commands/handoff.md`. Neither is the fleet mechanism. The fleet-generated handoff is `.pmwork/HANDOFF.md`, and **that** count is 0. The finding (F-07) stands; the phrasing was imprecise.

### D.3 Which tasks own worktrees (corrected)

Earlier working notes said "98 worktrees for 51 distinct task IDs; 93 owned by VOID tasks, 5 by DONE tasks". Verified: 98 trees, 51 distinct tasks; 47 VOID tasks own 93 trees, 4 DONE tasks own 5 trees (`T-0118-100`, `T-0119-101`, `T-0130-102`, `T-0139-116`, `T-0139-117`). The tree-level counts were right; the task-level counts (47/4, not 93/5) are the correct framing.

---

## Appendix E — Open Questions for the Operator

These require operator input and are **not** resolved by the evidence:

1. **REC-02 archive target.** Where should captured stranded work go — a git branch per task (`pmk/stranded/<task>/<fence>`), a patch directory outside `work/`, or an external archive? A branch is durable and diffable; a patch directory is simpler and cannot be accidentally merged.
2. **Retention policy.** Is any stranded work wanted after capture, or is "captured then deleted" sufficient? If wanted, for how long?
3. **REC-01 placement.** Should reclamation happen inside the harness (`_give_up`), inside the Kernel's `revoke`, or in the dispatcher's reaping loop? Kernel-side is the only place that catches *every* fence bump, but the Kernel currently has no filesystem responsibility for worktrees.
4. **REC-09 `I6`.** Are the five missing bundle references a recording defect (bundles exist but were not recorded) or a process defect (integration happened without a bundle)? The answer determines whether backfill or downgrade is correct.
5. **Unpause conditions.** Should the fleet resume only after REC-01 and REC-02 land, or is documentation-only acceptable for a period? Note the Q-075 interaction in §8.4: a 20-minute TTL without REC-01 accelerates the leak.
6. **`b5ccg`.** Given that project shows the same class of uncollected per-run artefact (1,230 MiB `scratch/`, 195 MiB `out_gate_*`, still growing), should the same capture-then-reclaim treatment be specified for it, or is it out of scope for this repository's governance?
7. **The 42 clean trees.** Their content is provably empty (no uncommitted entries). May they be deleted immediately as a low-risk demonstration, or does the operator prefer a single atomic cleanup after REC-02?
8. **R-13 review.** Who should perform the independent review — the `verifier` agent, or an external model? This report was not self-assessed.

---

## Appendix F — R-13 Review Status and Author Self-Verification Pass

### F.1 R-13 independent review — COMPLETED 2026-11-07 (six independent assessments)

**Update (v1.1).** The initial R-13 attempts were blocked (three reviewer agents failed on infrastructure, below). The review was subsequently **completed**: six independent LLMs assessed this report on 2026-11-07 — five `ACCEPT WITH CORRECTIONS` and one `ACCEPT`; none refuted a central claim. Their findings are collated and adjudicated in `proposal-deepseek-umaws-fleet-worktree-lifecycle-remediation-v1.md` (Section 11 lists them), and the accepted corrections are applied in this v1.1 (Appendix G). The blocked-attempt record below is retained for provenance.

R-13 step 2 requires an assessment LLM that did not write this report to review it. Three reviewers were attempted on 2026-11-07 and all failed for infrastructure reasons, not for reasons relating to this document:

| Attempt | Reviewer | Failure |
|---|---|---|
| 1 | `verifier` (project's designated adversarial reviewer) | "Model version … is deactivated. It needs to be activated before running predictions." |
| 2 | `general` | "Free usage limit reached." |
| 3 | `claude-3-opus-20240229` | "ECONNREFUSED: Unable to connect." |

**Historical consequence (superseded by the v1.1 update above).** At the time of writing the report had **not** been independently reviewed. The R-13 reviewer checklist was previously open on: findings addressed, timestamps verified by a second party, commit hashes verified by a second party, file paths verified by a second party, actor attribution completeness, and test coverage of any new fixes. The frontmatter `reviewer` field records this. Treat the report as a v1 draft of record, not as a closed incident.

**Reviewer checklist for whoever completes it** (adapted from R-13):

- [ ] Every claim in §5 confirmed or corrected against the log, the filesystem and git.
- [ ] All 14 numbers in §12 checked against the trees themselves.
- [ ] `1a5ec9b` verified to contain the 66-file corpus (F-16).
- [ ] The three `T-0101` trees and `T-0100-64` confirmed unique (no branch, no commit, not in the working tree).
- [ ] Commit hashes in §15 verified to resolve and to be ancestors of `main` where claimed.
- [ ] REC-01/REC-02 ordering reviewed for safety.
- [ ] §12.2's "no capture step needed" claim for the four corpus trees reviewed.

### F.2 Author self-verification pass (explicitly NOT an independent review)

Because R-13 was blocked, the author re-derived every numeric claim mechanically in a second pass, using only read-only commands. This is a **self-check and carries no independence**. It is recorded so that a future reviewer has a known-good baseline to attack.

Results and corrections produced by the pass:

| Claim | First-pass value | Verification-pass value | Outcome |
|---|---|---|---|
| Worktrees | 98 | 98 | confirmed |
| `work/` total / min / max | 886.2 / 8.7 / 10.3 MiB | 886.2 / 8.7 / 10.3 MiB (mean 9.04) | confirmed |
| Distinct tasks owning trees | 51 | 51 | confirmed |
| Distribution 1/2/3 trees | 26 / 3 / 22 | 26 / 3 / 22 | confirmed |
| VOID vs DONE tree ownership | 47 tasks / 93 trees; 4 tasks / 5 trees | same | confirmed |
| Dirty trees / entries / bytes | 56 / 488 / 514.7 MiB | 56 / 488 / **514.9 MiB** | **corrected** (±0.2 MiB variance) |
| Clean trees | 42 | 42 | confirmed |
| `.pmwork/HANDOFF.md` / `RESULT.md` | 0 / 68 | 0 / 68 | confirmed |
| `remove_worktree` call sites | 0 | 0 (1 hit = the definition) | confirmed |
| Branches / `pmk/*` / `.git/worktrees` | 161 / 159 / 107 | 161 / 159 / 107 | confirmed |
| `pmk-merge-*` dirs / non-empty / bytes | 20 / 8 / 80.1 MiB | 20 / **19 contain files** / 80.1 MiB | **corrected** (8 was a rounding artefact) |
| Events / `TASK_CREATED` / distinct | 3,109 / 146 / 146 | same | confirmed |
| VOID / DONE / PROPOSED | 138 / 6 / 2 | 138 / 6 / 2 | confirmed |
| REVOKED / TTL-expired | 108 / 58 | 108 / 58 | confirmed |
| Loop counts | 863 / 423 / 255 / 192 / 112 / 104 / 102 | identical | confirmed |
| `T-0101` seq/fence trace | 1736/1795/1832/1908/1962/2109/2213 | identical | confirmed |
| `src/cna/core/` in HEAD / on disk | absent / absent | 0 hits / `False` | confirmed |
| `INTEGRATED` events | "9 hash-bearing" | **18 events, 11 subjects, 9 hash-bearing (all ancestors of `main`), 9 empty-commit, 7 tasks integrated twice** | **extended** (F-15 broadened, F-19 refined) |
| `b5ccg` total / `scratch/` / `out_gate_*` | 2,301.8 MiB / 1,230.1 MiB / 170.0 MiB (40 dirs) | **2,327.7 MiB / 1,230.1 MiB / 195.5 MiB (46 dirs)** | **corrected** (live repo, moved between passes) |
| `b5ccg` has `.pm/` | no | no | confirmed |

**Unchanged conclusion.** None of the corrections alters the diagnosis, the root causes or the recommendations. All three corrections are measurement-precision or live-drift issues; the `INTEGRATED` extension strengthens F-15 rather than changing it. The central claims — RC-1/REC-3 (nothing ever deletes a worktree), RC-2 (retries allocate fresh checkouts), RC-4 (handoff unwired), F-04/F-05 (stranded unique work) — are confirmed.

### F.3 Recommended sequence for closure

1. Operator reviews this report and answers Appendix E.
2. An R-13 reviewer becomes available; the checklist in F.1 is completed.
3. Operator decides Q-076.
4. Only then, and only in the order REC-03 → REC-02 → REC-01, is any code changed or any tree touched.

---

## Appendix G — v1.1 Correction Log

Every change in v1.1, each traced to a collated reviewer correction (`proposal-deepseek-umaws-fleet-worktree-lifecycle-remediation-v1.md` §6). The v1.0 file is retained unmodified.

| ID | Severity | Change in v1.1 |
|---|---|---|
| C-1 | major | `write_handoff()` corrected from "called once" to **three call sites** (`harness.py:586`, `dispatcher.py:383`, `cli.py:617`) in §1, §4.4, F-07 and §10.1; RC-4 retitled. |
| C-2 | major | "Nothing ever deletes a worktree" re-scoped to the *code*; added **F-22** (≥7 recorded worktrees missing from disk, deleted out of band); removed the absent `work/T-0003-3` as "live proof" (§4.2, §15). |
| C-3 | minor | §9.2 last row `26` → `16`; the table now sums to 108. |
| C-4 | minor | All byte figures relabelled **MiB** (86 replacements); note retained in §2.4. |
| C-5 | minor | §3 loop-signature seq window corrected to the true span (`FLEET_BLOCKED` 330–2523). |
| C-6 | minor | Overseer cadence corrected: 423 wakes over ~11.6 days (~39 min mean); `FLEET_BLOCKED` ~one per 4 min. |
| C-7 | minor | F-09/REC-07 corrected: the merge cleanup **exists** (`merge.py:336-344`); it is non-durable, not absent. |
| C-8 | minor | §12.1(4): `T-0131-110` holds **LF**, not CRLF. |
| C-9 | minor | F-15 ordering clarified (empty-first only for T-0004/T-0006). |
| C-10 | minor | §1 Executive Summary merged from 4 paragraphs to **3** (R-12 element 3 now adequate). |
| C-11 | trivial | F-01 mean 9.05 → 9.04; `api.py:40` → 41; `dispatcher.py:450` → 473-474; `2a0f6fa` full hash given. |
| C-12 | minor | §7.3/§12: 488 entries = **326 distinct content blobs**. |
| C-13 | minor | §7.3 "provably empty" → "no uncommitted entries". |
| C-14 | minor | §7.2 "Real project data" marked approximate/illustrative. |
| C-15 | minor | §11 marked a dated 2026-11-07 snapshot. |
| C-16 | trivial | §4.4/§10.1 root `HANDOFF.md` size re-dated (~6,088 B). |

**Unchanged conclusions.** No correction alters RC-1–RC-6, any severity rating, the recommendation ordering, or either central claim. C-1 and C-2 correct stated facts; C-2 additionally records a new governance concern (an unrecorded out-of-band deletion) as F-22.

**R-13 status.** Independent review is **complete**: six independent LLM assessments (see `proposal-deepseek-umaws-fleet-worktree-lifecycle-remediation-v1.md`, Section 11). The report is no longer unreviewed.

---

*End of report. No worktree was deleted. No stranded work was moved or committed. No source file was edited. The project remains `PAUSED`. This v1.1 is editor-corrected from v1.0 per six independent assessments (Appendices F and G); the corrections were applied by DeepSeek V4.1 Flash, which is not an independent assessor of this report.*
