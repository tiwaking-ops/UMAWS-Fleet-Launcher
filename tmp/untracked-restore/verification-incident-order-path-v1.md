---
document:
  title: "Verification Annex: Incident Report order-path v1 (T-0131/T-0136 chain)"
  status: "Advisory verification record; read-only reconstruction from the event log, fleet logs and git history; does not supersede the incident report"
  version: "1.0.0"
provenance:
  author_llm:
    name: "DeepSeek V4.1 Flash Free"
    version: "opencode/deepseek-v4.1-flash-free"
  assessor_llm:
    name: "DeepSeek V4.1 Flash Free"
    version: "opencode/deepseek-v4.1-flash-free"
    assessor_of: "incident-report-order-path-v1.md (Hermes Agent, stepfun/step-3.7-flash:free)"
  created_date: "2026-11-02"
  last_modified_date: "2026-11-02"
  scope: "C:\\temp\\projects\\testproject1: .pm/events 2026-10-29..2026-11-02, .pm/fleet/logs, worktrees, src/fleet, src/pmk, agents.toml history, pytest run"
---

# Verification Annex: Incident Report `order-path-v1`

**Author:** DeepSeek V4.1 Flash Free (opencode) — independent assessor of the Hermes Agent report
**Date:** 2026-11-02 · **Repository:** `C:\temp\projects\testproject1` · branch `main` @ `77a8659`
**Method:** read-only. Event log replay, fleet log inspection, worktree filesystem inspection, `git log`/`git show`, `hermes chat --help`, `pytest -q`.

All timestamps below are **UTC**. Local file timestamps in this repo are UTC+13 (NZDT).

---

## 1. Verdict

The critique is substantially correct. The report identifies a real defect and applies a real (partial) fix, but it mis-attributes the timeline, overstates the causal claim, and attributes to the harness a behaviour it never exhibited.

| Report claim | Verdict | Basis |
|---|---|---|
| Two ORDER.md files differ; a stale root file contains T-0004 | **True** | `.pmwork/ORDER.md` (root) vs `work/T-0136-114/.pmwork/ORDER.md` |
| Absolute-path prompt is a good defensive fix | **True** | `src/fleet/order.py:39-40`; 4 call sites updated |
| Defect was the **primary** stalling mechanism 13:34Z–22:09Z | **Not supported** | 5/5 leases in that window died with **no** observed exit; 2 of 5 did the right task |
| Attempt 1 (fence 109) expired at TTL 15:58:06Z | **False** | Revoked 13:57:37Z, reason "worker died … 429 rate limit"; no `LEASE_EXPIRED` for 109 |
| "Every lease failed identically — agent did T-0004" | **False** | 109 = 429, no work at all; 110 = correct task, correct worktree, 66 files |
| "The harness re-ran the actual oracle … it failed" | **False** | Zero `ORACLE_RESULT` and zero `AGENT_EXITED` events for 109/110/111/113/114 |
| Hermes resolved `.pmwork` from repo root | **True** | Root `.pmwork/RESULT.md` written 19:32:22Z, inside 111's lease only |
| "By then 120 minutes had passed and the lease expired" | **False** | The 120-minute expiry is the *symptom of no supervision*, not of an oracle failure |
| Fix is uncommitted | **Stale** | Committed as `77a8659` at 2026-11-02T01:37:50Z; no regression test added |
| §8 current state: T-0136 `LEASED`, PID 5232 | **Stale** | `pmk status`: `STALLED`, 0 active leases, 2 open queue items |

---

## 2. Corrected timeline (raw events)

| seq | ts (UTC) | type | subj | fence | detail |
|---|---|---|---|---|---|
| 2764 | 11-01T13:34:12Z | CLAIMED | T-0131 | 109 | `pi-orca-glm-5-3-flash`, pid 4916 |
| 2765 | 13:34:13Z | AGENT_STARTED | T-0131 | 109 | worktree `work\T-0131-109` |
| — | 13:34:33Z | (log) | | 109 | last byte of `109-0.log`: `429 free_rate_limited` |
| 2788 | **13:57:37Z** | REVOKED | T-0131 | 109 | reason: *"worker died; stale lease cleanup after orcarouter free-tier 429 rate limit"* |
| 2790 | 13:58:04Z | CLAIMED | T-0131 | 110 | `pi-orca-hy4-preview`, pid 3332 |
| 2791 | 13:58:05Z | AGENT_STARTED | T-0131 | 110 | worktree `work\T-0131-110` |
| — | 14:10:27Z | (file) | | 110 | `work/T-0131-110/.pmwork/RESULT.md` written; 66 corpus files present |
| 2812/2813 | **15:58:06Z** | REVOKED / LEASE_EXPIRED | T-0131 | 110 | elapsed **120.03 min** |
| 2841 | 19:29:49Z | CLAIMED | T-0131 | 111 | `hermes-solar-mini4`, pid 7936 |
| — | **19:32:22Z** | (file) | | 111 | **root** `.pmwork/RESULT.md` written — outside the worktree |
| 2859/2860 | **21:29:50Z** | REVOKED / LEASE_EXPIRED | T-0131 | 111 | elapsed **120.02 min** |
| 2861-2863 | 21:58:57-59Z | TASK_VOIDED | T-0131/2/3 | — | actor `human/operator` |
| 2864-2869 | 21:59:24-42Z | TASK_CREATED/ADMITTED | T-0136/7/8 | — | fresh chain |
| 2871 | 22:00:39Z | CLAIMED | T-0136 | 113 | `hermes-solar-mini4`, pid 6424 |
| — | 22:02:06Z | (log) | | 113 | *"Done. Task T-0004 carried out"* |
| 2874 | **22:09:24Z** | REVOKED | T-0136 | 113 | reason: prompt fix — manual, not TTL |
| 2875 | 22:09:46Z | CLAIMED | T-0136 | 114 | `hermes-solar-mini4`, pid 5232 |
| — | 22:17:18Z | (file) | | 114 | worktree `RESULT.md`; log claims 66/66 verified |
| 2892/2893 | **11-02T00:09:47Z** | REVOKED / LEASE_EXPIRED | T-0136 | 114 | elapsed **120.02 min** |
| 2890 | 00:09:46Z | PROJECT_STATE | — | — | `STALLED` |
| 2903 | 00:33:38Z | INCIDENT (overseer) | T-0136 | — | *"attempt2 verified-main-only, worktree empty, no bundle"* |

No `AGENT_EXITED`, no `ORACLE_RESULT`, no `SUBMITTED` exists for any of fences 109–114.

---

## 3. Two independent failure modes

### 3.1 Mode A — orphaned leases (explains all five expiries)

`Harness.poll()` (`src/fleet/harness.py:277-310`) is correct: it detects exit, re-runs oracles, submits. But it only runs from `Dispatcher.tick()`, over `self.runs` — **an in-memory dict** (`src/fleet/dispatcher.py:191-208`). A dispatcher process that exits (`dispatch run --seconds`, default 30 s; the operator was running 600 s windows) loses every handle. On restart it can neither poll nor adopt the existing lease, so the lease can only end one way: TTL expiry.

Evidence that no poller was ticking:

- `RENEWED` events stop at **2026-11-01T07:07:34Z** — no lease was renewed for the rest of the day. `renew_every = 60`, and `poll()` renews unconditionally every 60 s, so any live ticker would have produced renewals every minute for a 120-minute lease.
- `stall_minutes = 15`: a live poller would have killed a silent agent at 15 minutes and recorded `AGENT_EXITED` with class `STALL`. Nothing was killed; all five ran to the full 120.02–120.03 min.
- `ttl_minutes` is **120 only in the dirty working tree** (`.pm/policy.toml:71`); `HEAD` has 20. This uncommitted change is what turned a 20-minute annoyance into a 2-hour dead zone.

This mode alone explains 109, 110, 111, 113 and 114 never producing evidence bundles — including 110, which had done the work correctly, and 114, which read the correct order.

### 3.2 Mode B — Hermes does not honour the process working directory (explains the wrong task)

The harness is not at fault here: `spawn_slot` passes `cwd=target` (`src/fleet/spawn.py:240`), `plat.spawn` forwards it, `hermes` has `headless=True` (so the console fallback, which also sets `Set-Location`, is not in play), and `AGENT_STARTED` records the correct worktree.

Hard evidence that the hermes child's effective cwd was the repo root:

- Root `.pmwork/RESULT.md` was created at **19:32:22Z**, i.e. inside fence 111's lease (19:29:49–21:29:50) and no other. Its content is the T-0004 result. `work/T-0131-111/.pmwork/` contains only `ORDER.md`.
- Fence 114 read the *correct* order (the absolute-path fix worked) but verified `docs/rules` **against the main tree** — `work/T-0136-114/docs/rules` still holds the base-commit 3-file manifest (`pinned 95ee479`), zero `sections/`, clean `git status`, while main's working tree holds the untracked 66-file corpus.
- `hermes chat --help` (local install): `--in DIR  Change into DIR before starting or resuming`, and `--no-restore-cwd  Don't cd into a resumed session's recorded working directory`.

The regression dates from **`548885e` (2026-10-28, "Fleet hardening v5-v11")**, which replaced

```
argv_new = ["hermes", "chat", "--oneshot", "-q", "{prompt}", "--yolo", "--cli", "--in", "{cwd}"]
```

with an argv containing no `--in`, plus the comment `# --in flag is needed.` — and a later commit (`786d52d`) rewrote that comment to "no --in flag is needed". The `--in` key existed in `agents.toml` from `787b855` (10-25) and earlier; it has been absent ever since 10-28.

`pi` is not affected: fence 110 vendored the corpus into the correct worktree, and `T-0106/69-0.log` shows pi issuing `git -C C:\temp\projects\testproject1\work\T-0106-69 …`.

### 3.3 Why the fix is partial

`order_prompt(worktree)` makes the *order file* absolute. It does not change the child's working directory, so every **relative path in the order** (write scope `docs/rules/…`, oracle commands, premises) still resolves wherever hermes feels like resolving them. Fence 114 is the proof: right order, wrong tree, "done", no bundle.

---

## 4. Answers to the fifteen questions

**1. Raw events for T-0131 fences 109–111 and T-0136 fences 113–114.**
Reproduced in §2 (seq 2764–2893). Key correction: 109 was revoked at 13:57:37Z for a 429 worker death; the 15:58:06Z expiry belongs to fence 110. `AGENT_EXITED`: none. `ORACLE_RESULT`: none. `SUBMITTED`: none.

**2. Did the dispatcher run continuously 13:34Z–22:09Z?**
No. No `RENEWED` after 07:07:34Z; no stall-kill after 15 min; five leases each ran the full 120.02–120.03 min. It ran in operator-started bursts, and each burst's in-memory run table died with the process.

**3. Which profile ran 113? Do the pi logs show T-0004?**
113 = `hermes-solar-mini4` (pid 6424). No. `109-0.log` is a single 429 line (447 bytes) — no task was attempted. `110-0.log` shows the **correct** task completed in the correct worktree. Only the two hermes logs (`111-0`, `113-0`) show T-0004.

**4. Exit codes and durations.**
No exit codes exist — the harness never observed an exit, so none were recorded. Last-output times: 109 → +21 s (429); 110 → +12.6 min; 111 → +2.8 min; 113 → +1.4 min; 114 → +7.5 min. Then silence until TTL. That pattern is "process ended or hung, nobody watching", not "oracle failed in minutes".

**5. Did the Hermes argv contain `--in {cwd}`?**
No — neither in the original profile at the incident commit (`77a56db`) nor in `HEAD`. It was removed at `548885e` (2026-10-28). Last revision that had it: `787b855` (2026-10-25).

**6. Was the bug reproduced by hand?**
No. Nothing in the repo documents a spawn of hermes/pi in a decoy worktree. Everything in §3.2 is inference from artefacts, though the root `RESULT.md` timestamp is close to a direct observation.

**7. Who wrote the root `.pmwork/ORDER.md`?**
Rendered at **2026-10-30T00:18:35Z**, two minutes after T-0004 fence 5 was claimed (00:16:35Z, worker `opencode-strongest`), submitted 00:20:40Z and integrated 00:21:44Z. There is **no `AGENT_STARTED` for fence 5**, so it was not a harness spawn — it was an out-of-band run whose "worktree" was the repo root. Its text says *"the harness will run these himself"*; no committed revision of `order.py` contains that wording (current says "itself"), so it came from a locally modified renderer.

**8. Does anything legitimately write root `.pmwork`? Is it ignored?**
Nothing legitimate: `write_order()` is only called with a worktree. `.pmwork/` **is** in `.gitignore` (line 10), so the stale file is invisible to `git status` and was never reviewed.

**9. Is CFNA running in `C:\temp\projects\testproject1`?**
`C:\temp\projects\cfna` exists as a separate git repo (`docs/`, `AGENTS.md`, `CLAUDE.md`), with **no `.pm`**. The CNA content work is nevertheless being executed *inside* testproject1: `docs/rules/CNA-Rules.adoc` and `docs/rules/sections/` are untracked in testproject1's working tree, and T-0136's oracle asserts against them. So yes — fleet source and CNA deliverables share one tree, which is exactly why an escaped cwd can "verify" against the wrong project's content.

**10. Who applied the fix, and who authorised editing `src/fleet/*`?**
`77a8659` was authored and committed by `umaws-pilot <umaws-pilot@localhost>` (the local git identity the Hermes Agent commits under) at 2026-11-02T01:37:50Z. There is no authorisation record: no queue decision, no `INCIDENT` acknowledgement, no human-actor event authorising edits to `src/fleet/`.

**11. Which actor is recorded on void / decide / revoke?**
- `TASK_VOIDED` T-0131/32/33: `human` / `operator` — but `task_void()`'s human check is documented as *advisory, not a security boundary* (`src/pmk/api.py:367`), spoofable via `PMK_ACTOR`.
- `QUEUE_DECIDED` Q-071 ("fix the cause and resume", 21:13:24Z): `kernel` / empty agent — **unattributed**, cannot distinguish human from agent.
- `REVOKED` 109/110/111/113/114: `kernel` / empty agent. `revoke()` and `queue_decide()` have **no** actor guard at all; `project_set_state()` likewise.

**12. Is the fix committed, with a test?**
Committed (`77a8659`, includes the report). **No test**: `grep order_prompt|order_path tests/` returns nothing. `pytest -q` does pass (exit 0, ~380 tests), so the existing suite is green but silent on this regression.

**13. Other projects on a hermes profile without `--in` since 10-28?**
None has actually run hermes. `toy1` — `--in` present, last event 10-25. `toy2` — `--in` present, last fleet spawn 10-23. `toy3` — **no `--in` in argv**, but last event 10-26 (before the change), so it is latent exposure, not a past incident. testproject1 is the only project that both dropped `--in` and dispatched afterwards.

**14. Sentinel since the fix?**
No. Last `SENTINEL_RUN` is seq 2838 at 2026-11-01T19:28:52Z — before the 22:09 fix and the 01:37 commit — and it returned `stops: true` findings (I6: `INTEGRATED` events with no bundle reference for T-0118/T-0119).

**15. Other anomalies?**
Yes, one material to the report: fence 114 is a *third* failure mode — correct task, correct order, wrong tree, self-declared done. The overseer captured it at 00:33:38Z. Additionally the uncommitted 66-file corpus in main's working tree is itself a trap: it lets any escaped agent pass an oracle it should fail. No other instances of agents doing a *different* task were found; the T-0004 mentions in older logs are order-text echoes, and `T-0106/69` shows pi using absolute worktree paths correctly.

---

## 5. Corrected causal model

1. **Root cause of the stalls (all five leases):** dispatch is not a supervised service. Run handles live only in memory; when the operator's `dispatch run --seconds 600` window ends, every lease becomes unobservable and dies at TTL. The uncommitted 20→120 min TTL change hid this for two hours per attempt.
2. **Root cause of the wrong-task executions (111, 113):** Hermes does not resolve relative paths from the process cwd, and `--in {cwd}` was deleted on 2026-10-28 on the untested assumption that `cwd=` suffices.
3. **Aggravating factor:** a stale root `.pmwork/ORDER.md` from an out-of-band T-0004 run made the wrong task concrete and harmless-looking ("done, oracle exit 0").
4. **The applied fix addresses (3) and the order-file half of (2), but not (2) itself, and not (1).**

Fence 114 is the demonstration: with the fix in place the agent read the right order, worked in the wrong tree, reported success, and the lease still expired unsubmitted.

---

## 6. Recommended actions (priority order)

1. **Restore `--in {cwd}`** in every hermes profile (and `--no-restore-cwd` on resume paths, or pass `--in` there too). Then run the canary test: spawn each profile in a throwaway worktree containing `.pmwork/ORDER.md` with a unique nonce, place a decoy at the project root, and assert the nonce in the child's output. Make it a test, not a manual check.
2. **Persist dispatcher runs** (lease adoption on start) or run dispatch as a supervised service. An attempt whose process is gone but whose lease is live must be reaped on the next tick, and an agent that exits with an unchanged worktree must fail immediately rather than wait for TTL.
3. **Delete `.pmwork/` at the project root** and add an invariant: root `.pmwork` must never exist; any harness write outside `work/<task>-<fence>` is a hard error.
4. **Add the prompt/cwd regression test** (assert absolute order path *and* assert the child's reported cwd equals its worktree).
5. **Commit the TTL change or revert it.** A 120-minute TTL that is only in a dirty working tree is invisible to every future audit — this report is evidence of that.
6. **Attribute governance operations.** Require `PMK_ACTOR` for `queue_decide`, `revoke` and `project_set_state`; today Q-071 is recorded as `kernel`, so "who decided to resume" is unanswerable.
7. **Stop leaving uncommitted deliverables in the main working tree** while dispatching worktrees. Commit or stash the corpus before dispatch; otherwise an escaped agent's oracle can pass on someone else's work.
8. **Re-run the sentinel** and carry over the outstanding I6 findings, which the current report does not mention.
9. **Correct the incident report** (§2.1 rows, §3.3 "harness ran the oracle", §4.2 "every lease failed identically", §8 state, provenance of the fix).

---

## 7. Provenance statement

Assessment authored by DeepSeek V4.1 Flash Free from read-only evidence. It does not promote, reclassify or supersede `incident-report-order-path-v1.md`, which remains the record of the Hermes Agent. Where this annex contradicts the report, the event log is cited so a reader can check it directly.
