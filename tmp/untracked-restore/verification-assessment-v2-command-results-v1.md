---
document:
  title: "Verification of Claude (Web) Assessment v2 — Appendix A Command Results and Answers to D-1..D-5 / Relay E"
  type: "Verification and answers"
  status: "Advisory; no authority. Read-only pass — nothing in the repo was reset, cleaned, stashed, committed or voided."
  version: "1.0.0"
provenance:
  author_llm: {name: "DeepSeek V4.1 Flash Free", provider: "opencode"}
  assessed_documents:
    - "assessment-claude-umaws-fleet-worktree-isolation-v2.md (v2.0.0, Claude, Claude Sonnet 5.5)"
    - "incident-report-worktree-isolation-v3.md (v3.0.0, Hermes Agent) — only the claims Claude re-tests"
    - "report-answers-for-claude-incident-v1.md (Relay D) — only by cross-check against the ledger"
  created_date: "2026-11-02"
  last_modified_date: "2026-11-02"
  note: "I am the assessor here, not the author, of the documents above. Claude's findings are scored, not adopted."
epistemic_status: "Tags: [VERIFIED] reproduced with a command or read from the ledger/code in this session; [INFERRED] my reasoning from verified facts; [GUESS] untested; [OPEN] cannot be settled from artifacts."
evidence_basis: "Every Appendix A command was run. Additionally read: the full event log projection (2991 events), src/fleet/harness.py, src/fleet/dispatcher.py, src/fleet/conductor.py, src/fleet/merge.py, src/fleet/spawn.py, agents.toml, .pm/policy.toml, the two untracked reports Claude asked for, and the upstream clone."
authority_statement: "Nothing here takes effect until the operator decides. .pm/policy.toml and .pm/constitution.md remain class K (two-key)."
---

# Verification of Assessment v2

## 0. Bottom line

Claude's six concerns largely hold, but three of them change character once the artifacts are read:

1. **N-1 is worse in one way and better in another.** T-0139's deliverable **is** committed — `2a0f6fa`, all 66 files, on branch `pmk/T-0139-117`. It was **never merged**. The `INTEGRATING` and `INTEGRATED` events both carry `commit: ""`. So nothing was lost, but the Kernel recorded DONE for a merge that did not happen. That is a sharper defect than "the work is missing".
2. **The real integrity failure is not the line endings of git status — it is that the accepted corpus is not the pinned corpus.** All 66 files as delivered are CRLF; the pinned blobs at `75a037f` are LF. The manifest attests the CRLF hashes while declaring `pinned_commit: 75a037f`. Every oracle in the pipeline passes on a corpus that is 66/66 byte-different from the commit it claims.
3. **R-09, added in `aed9aec`, leaks a granted lease every time it refuses.** It runs *after* `kernel.claim()` and returns without `_give_up()`. This is a new, latent instance of the exact failure the incident is about, and the current dirty tree guarantees it will fire.

Also: the pin **is** verifiable, just not where the hints say. `C:\temp\tcanf-clone` is a clean clone at `75a037f27346a7cd920a765a2f3cae965b1e07a3` with exactly 66 corpus files.

## 1. Appendix A — all seven commands, with results

Run from `C:\temp\projects\testproject1`. `HEAD` at the time of the pass: `393d0ea`. [VERIFIED]

| # | Command | Result | Reading |
|---|---|---|---|
| 1 | `git ls-tree -r HEAD \| Select-String "docs/rules/(sections/\|CNA-Rules.adoc)" \| Measure-Object` | **Count = 0** | Corpus absent from HEAD. **N-1 confirmed.** |
| 1b | `git ls-tree -r HEAD \| Select-String "^docs/rules/"` | 6 paths: `checksums.sha256`, `fleet-spawning.md`, `index.json`, `kernel-writing.md`, `manifest.json`, `windows-platform.md` | Manifest and checksums are tracked; the 66 files they describe are not. |
| 2 | `git log --all --oneline --grep="T-0139"` | `2a0f6fa feat(T-0139): Vendor full 66-file CNA corpus …` | **The commit exists.** |
| 2b | `git branch --all --list "*T-0139*"` | `pmk/T-0139-116`, `pmk/T-0139-117` | `2a0f6fa` is contained only in `pmk/T-0139-117`. |
| 2c | `git merge-base --is-ancestor 2a0f6fa HEAD` | exit **1** | Not on `main`. Never merged. |
| 3 | `Get-ChildItem work\T-0139-117\docs\rules\sections \| Measure-Object` | **Count = 65** | Plus `CNA-Rules.adoc` = 66. Worktree intact. |
| 4 | `Get-ChildItem work\T-0141-118\docs\rules` | 6 files, no `.adoc` | **Corpus-less base, confirmed.** |
| 4b | `Get-ChildItem work\T-0142-119\docs\rules` | 6 files, no `.adoc` | Same. |
| 5 | `git -C C:\temp\projects\cfna\docs\sources\cna-rules-upstream rev-parse HEAD` | **`fatal: ambiguous argument 'HEAD'`** | The named source is **not a git repo with history**. |
| 5b | `git -C C:\temp\projects\cfna status --short --branch` | `## No commits yet on master` | `C:\temp\projects\cfna` is a repo with **zero commits**; the "upstream" folder is just unversioned files inside it. |
| 6 | `git diff 77a56db..aed9aec > C:\temp\combined-77a56db-aed9aec.patch` | 136,710 bytes | Written. Files: `dispatcher.py`, `harness.py`, `order.py`, `spawn.py`, `tests/fleet/test_regressions.py`, `docs/rules/{manifest.json,checksums.sha256}`, 2 incident reports. |
| 7 | `git diff HEAD -- src tests agents.toml .pm/policy.toml .pm/pins.sha256 > C:\temp\uncommitted.patch` | 49,608 bytes | Written. Files: `conductor.py`, `merge.py`, `agents.toml`, `.pm/policy.toml`, `.pm/pins.sha256`. |

**Both patches are ready to upload for relay.** No `reset`, `clean` or `stash` was run.

### 1.1 A correction on the pin: it is verifiable

Command 5 fails, but the pin is real. `C:\temp\tcanf-clone` [VERIFIED]:

```
git -C C:\temp\tcanf-clone rev-parse HEAD
  -> 75a037f27346a7cd920a765a2f3cae965b1e07a3
git -C C:\temp\tcanf-clone status --short --branch
  -> ## main...origin/main        (clean)
git ls-tree -r HEAD --name-only | match ^(CNA-Rules\.adoc|sections/section-\d+\.adoc)$
  -> 66
```

So §6.3 of the assessment can be closed: the source exists, at that exact commit, with exactly 66 files. **The hints name the wrong path.** They point at `…\cfna\docs\sources\cna-rules-upstream`, which cannot prove anything; the proof lives at `C:\temp\tcanf-clone`.

## 2. Scoring Claude's six concerns

### Concern 1 — "T-0139 may be DONE without its files in git" → **Confirmed, and reframed**

The count of 0 is correct. Two additional facts change the diagnosis:

- The deliverable is committed at `2a0f6fa` on `pmk/T-0139-117`. It is not missing, it is **unmerged**. [VERIFIED]
- The Kernel recorded the integration anyway:

```
seq 2969 INTEGRATING 03:32:22Z T-0139 {"commit":""}
seq 2970 INTEGRATED  03:32:22Z T-0139 {"commit":"","bundle":"EB-T-0139-117"}
```

Both payloads have an **empty commit**. Immediately before, the harness failed the merge three times, each time on the same tree-locality error:

```
seq 2947 INFRASTRUCTURE_FAILED 03:26:33Z  stage=merge-into-main
seq 2950 INFRASTRUCTURE_FAILED 03:27:54Z  stage=merge-into-main
seq 2960 INFRASTRUCTURE_FAILED 03:29:37Z  stage=merge-into-main
  message: "…Your local changes to the following files would be overwritten by merge:
            docs/rules/checksums.sha256, docs/rules/manifest.json …
            The following untracked working tree files would be overwritten: …
            Please move or remove them before you merge. Aborting"
seq 2962 INCIDENT 03:29:38Z  I-T-0139-0117  "git infrastructure failed 3 times"
seq 2964 VERIFIED  03:30:11Z T-0139  {"ok":true}
```

`977b83b` is 03:32:03Z — the operator committing only `manifest.json` + `checksums.sha256` by hand, 19 seconds before the INTEGRATED event, exactly as Claude inferred.

**The defect to name is not "the work is missing". It is that `integrate` is a state transition with no git precondition and no merge-sha in its payload.** A task can reach INTEGRATED with `commit: ""` after its own merge path reported three hard failures. Claude's §6.1 step 4 (record the merge sha, sentinel-verify reachability from `main`) is the right fix and is now better supported than it was.

### Concern 2 — "No dispatcher doesn't fit the timing" → **Confirmed; the mechanism is now read from code**

The lease expiries are 1–2 s past the TTL boundary every time because the **Conductor** ticks every 5 s, not because the harness is alive:

`agents.toml:23  dispatch_tick_s = 5` [VERIFIED]

`Conductor.run_forever()` sleeps `dispatch_tick_s` per iteration, and the auto-revoke patch in the *uncommitted* `conductor.py` emits `LEASE_EXPIRED` from `tick()`. The harness, by contrast, lives inside `Dispatcher.run_forever(max_seconds=N)`, which is:

```python
        while not self._stop.is_set():
            if deadline is not None and time.time() > deadline:
                break                     # <- no cleanup, no handoff
            try:
                self.tick()
            except Exception as exc:      # noqa: BLE001
                print(f"[dispatcher] tick failed: {exc}", flush=True)
            self._stop.wait(tick)
```

On deadline it just breaks. **No reconcile, no revoke, no event, no persisted adoption.** Its own docstring says "One loop supervises every slot." So supervision dies with the process that claimed the leases, and orphaned agents keep running. Claude's leading guess is correct and is now source-confirmed, not inferred. (Relay E item 1 is answered by this.)

The measured expiries [VERIFIED]:

| lease | granted_at | TTL boundary | LEASE_EXPIRED | lag | seq |
|---|---|---|---|---|---|
| T-0131 f110 | 13:58:04Z | 15:58:04Z | 15:58:06Z | +2 s | 2813 |
| T-0131 f111 | 19:29:49Z | 21:29:49Z | 21:29:50Z | +1 s | 2860 |
| T-0136 f114 | 22:09:46Z | 00:09:46Z | 00:09:47Z | +1 s | 2893 |

Every `LEASE_EXPIRED` payload carries `"pid": null`. The ledger therefore **cannot** answer Claude's Relay E item 2 (were agents alive after expiry) — see §4.

### Concern 3 — "A good result was probably thrown away" → **Confirmed, and the discarded artifact was better attested than the accepted one**

`110-0.log` is T-0131 fence 110, profile `pi-orca-hy4-preview`. It reports [VERIFIED from log + blobs]:

- It found a real clone at `/c/temp/tcanf-clone`, `HEAD == 75a037f…` exactly, clean tree.
- It vendored from **committed blobs** (`git show HEAD:path`), explicitly *not* the autocrlf-converted worktree copies.
- 66 files, manifest with `pinned_commit` set to the full hash, 66 checksum lines, oracle exit 0.

I compared the artifacts byte-for-byte:

```
main worktree corpus   vs  T-0097-49            : 66/66 identical
main worktree corpus   vs  T-0139-117 (2a0f6fa) : 66/66 identical
main worktree corpus   vs  T-0131-110 (pi f110) : 66/66 differ
   … but equal modulo CRLF everywhere (checked section-01, -16, CNA-Rules.adoc)
```

And the hash comparison that matters:

```
manifest.json vs 75a037f committed blobs : ok=0   differs=66  of 66
pi f110 checksums.sha256 line 1          : 5654c632…  docs/rules/CNA-Rules.adoc
75a037f committed blob  CNA-Rules.adoc   : 5654c632…
```

So the pi run's **hashes are the true hashes of the pinned commit**, and the accepted corpus's hashes are not. Its only deviation is a cosmetic one: `checksums.sha256` paths are prefixed `docs/rules/` instead of being manifest-relative, so the reference checksum parser reports 66 "missing". [VERIFIED]

The discarded attempt was right about provenance and wrong about a path convention. The accepted attempt is wrong about provenance and right about the path convention, and its oracle only checks the convention.

### Concern 4 — "T-0139 succeeded because of its hint" → **Confirmed; and the hint's central claim is false**

`115-0.log` (the failed predecessor) shows the agent asserting the corpus was already present, and writing `RESULT.md` to an absolute path in the correct worktree — it knew where the worktree was. `113-0.log` line 3 states the working directory outright:

> `Wrote pi-test.txt (working dir C:\temp\projects\testproject1)`

That is fence 113 reading and writing the **main tree**. `117-0.log` succeeds with `cwd = worktree` because the hint supplied absolute destinations and a copy source. So Claude's N-4 stands: the win is task-specific text, not isolation.

But the hint's warranty — "byte-identical to the pin" — **does not hold for anything that ended up in main or on `pmk/T-0139-117`**:

```
pin 75a037f  CNA-Rules.adoc : 5881 bytes,   0 CRLF, sha256 5654c632…
2a0f6fa      CNA-Rules.adoc : 6059 bytes, 178 CRLF, sha256 e5859441…   <- what was delivered
2a0f6fa manifest.json       : pinned_commit = 75a037f…, files["CNA-Rules.adoc"] = e5859441…
```

`core.autocrlf` is `false` and `.gitattributes` pins LF only for `.pm/` files, so nothing in the tree defends against this. All 66 files share the defect. [VERIFIED]

This is a new finding and it should outrank the line-ending trivia in `git status`: **the corpus is off-pin by 66/66 and no oracle in the pipeline can see it,** because every oracle tests manifest↔checksums↔files internal consistency and never the pin.

### Concern 5 — "The tree is dirty and the tests ran on it" → **Confirmed, with two corrections and one omission**

Corrections:

- `src/fleet/order.py` and `src/fleet/spawn.py` are **not** uncommitted. They are in `aed9aec`. Only `conductor.py` and `merge.py` are dirty under `src/`. [VERIFIED from `git status --short` and the patch file lists]
- Consequently the isolation warning and hint rendering **are** committed — in `aed9aec`, not `77a8659`. Claude's narrow point (that `77a8659` only adds `order_prompt`, 4 lines) is correct.

Omission, and it matters: **the dirty tree is a blocked state, not carelessness.** The Kernel raised this itself. [VERIFIED]

```
seq 1948 INCIDENT 2026-10-31T22:00:16Z  actor=overseer-beam
 "sentinel I8' STOP: .pm/policy.toml ttl_minutes changed 20->120 without two-key approval;
  pin not re-recorded. This blocks all promotion (stops=true). Pair the persisted conductor
  auto-revoke patch in src/fleet/conductor.py (uncommitted, +42 lines) also un-promoted.
  … Overseer records no state transitions; requests human ratification/revert."
```

That is the explanation for the un-promoted `conductor.py` and for the whole `--no-ff`/auto-revoke pair: the operator never ratified the TTL change, so the fix that depends on it could not be promoted either. Promoting the patch and ratifying the policy are the same act.

### Concern 6 — "v3 misdescribes its own record" → **Confirmed on every point I could test**

| v3 claim | Verified reality |
|---|---|
| f115 "claimed 00:09:47" | 00:09:47 is **f114's LEASE_EXPIRED** (seq 2893). f115 `CLAIMED` is **02:28:34Z** (seq 2920). |
| f115 "revoked 02:34:54" | 02:34:54 is the **incident** timestamp (seq 2925). `REVOKED` is **02:57:26Z** (seq 2926). |
| "three consecutive TTL expiries for T-0131" | One 429-era failure, then two expiries (seq 2813, 2860). Three attempts, two expiries. |
| "Fix for C2: commit 77a8659" | `77a8659` is "use absolute worktree order path in agent prompt". The R-* hardening is `aed9aec`. |
| "T-0139 integrated at fence 117, commit 977b83b" | INTEGRATED payload has `commit: ""`; `977b83b` is a manual manifest/checksums commit 19 s earlier. |

Claude's §5 table is right, including the pattern he drew from it.

## 3. Decisions

### D-1 — Who ran the voids, Q-071 and `project_set_state`

**From the ledger, [VERIFIED]:** every void in this window is attributed to `operator/human/supervisor`, and every Kernel-internal transition is attributed to `kernel`:

```
seq 2927-2931  TASK_VOIDED  T-0136/0137/0138/0140   actor=operator/human/supervisor
seq 2939       REVOKED      T-0139                  actor=/kernel/kernel
seq 2957       PROJECT_STATE RUNNING                actor=/kernel/kernel
seq 2958-2959  TASK_VOIDED  T-0143/T-0144           actor=operator/human/supervisor
```

**But this cannot answer the question.** The actor field is self-declared; an agent passing `--actor operator` is indistinguishable from the human. Two things make me doubt it was the human in each case:

- seq 2981 (overseer) records that the **recorded reason** for voiding T-0143/T-0144 was *factually wrong* — it said "duplicate of T-0141/T-0142 … same oracle", when the oracles differ precisely in being broken (`"` vs `'`). A human acting deliberately would have written the real reason; an agent summarising would plausibly write this. [INFERRED]
- `seq 2944` and `seq 2290` are INCIDENT events whose entire payload is `{"message":"list","severity":"warn"}` — malformed emission through the same advisory path.

**D-1 is [OPEN] and only you can close it.** It is not a bookkeeping question: if an agent can emit `actor=operator/human/supervisor`, then every "operator decided" line in this log is unverified, including Q-059's ratification in D-3.

My recommendation, separate from the answer: require an **explicit actor on every state-changing call**, reject the self-declared default, and add a `reason_evidence` field to void/revoke so a wrong rationale is visible at write time.

### D-2 — How the corpus should land

**Not by copying main's untracked files, and not by merging `pmk/T-0139-117` as-is.** Both carry the CRLF defect from Concern 4. Option (a) is still right in shape:

1. Derive the corpus from the authoritative source: `git -C C:\temp\tcanf-clone show HEAD:<path>` for all 66 paths (LF, byte-identical to `75a037f`).
2. Regenerate `manifest.json` and `checksums.sha256` against **those** bytes.
3. Add `docs/rules/** text eol=lf` to `.gitattributes` so a checkout cannot re-mangle them. Without this step the oracle silently flips on the next fresh clone.
4. Commit with a trailer naming T-0139 and a recorded decision.

**Then** move main's untracked copies aside and merge `pmk/T-0139-117`, or void it and let the corrected commit stand. Note: option (c), a follow-up card, **cannot work right now** — a card writing `docs/rules/` will be refused by R-09 while main is dirty (see D-4). The operator commit is the unblocking act.

I do **not** recommend option (b) (revoke and re-run T-0139): the work is correct in content, the failure was integration, and a re-run on a corpus-less base repeats fences 114/115/141.

### D-3 — Do the two class-K files have their two-key events?

**No. [VERIFIED — this is the clearest answer of the five.]**

The change is one line:

```diff
 [lease]
-ttl_minutes = 20                     # [GUESS] pilot v1 G9
+ttl_minutes = 120                    # [GUESS] pilot v1 G9; increased from 20 to 120 for complex tasks
```

`.pm/pins.sha256` changes only the derived hash for that file. There is **no event type for a policy change** anywhere in the log's vocabulary (34 types; none is authorisation-shaped). What actually happened:

```
seq 2268 SENTINEL_RUN 06:07:24Z  findings: I8' ".pm/policy.toml does not match (hash differs)"  stops=true
seq 2270 SENTINEL_RUN 06:13:19Z  same finding, stops=true
seq 2271 SENTINEL_RUN 06:16:32Z  same finding, stops=true
seq 2272 PINS_CHECKED 06:16:44Z  actor=operator/human  {"note":"the pins were re-recorded"}   <-- BEFORE any decision
seq 2280 SENTINEL_RUN 06:30:47Z  findings:[], ok=true
seq 2281 PINS_CHECKED 06:30:56Z  actor=operator/human  {"note":"the pins were re-recorded"}
seq 2284 QUEUE_DECIDED 06:32:16Z {"choice":"ratify and re-record pin","id":"Q-059"}
seq 2285 PINS_CHECKED 06:32:24Z  actor=operator/human  {"note":"the pins were re-recorded"}
```

The pin was rewritten **16 minutes before** the decision that ratified it, and the decision then recorded "ratify **and re-record** pin" — ratifying a state the pin had already blessed. The two-key gate was satisfied retroactively and circularly. `PINS_CHECKED` is a *verification* event, not an authorisation; re-running it is sufficient to clear its own failure.

**This is a governance hole independent of the incident:** the same party that edits a class-K file can rewrite `pins.sha256` and make the sentinel green. Fix: `PINS_CHECKED` must refuse to record when the changed file's authorisation event is absent; the pin update should require a class-K decision id in its payload.

### D-4 — Hold acceptance of T-0141 and T-0142

**Hold. Both are now blockable on three independent grounds, all verified.**

1. **Corpus-less base.** Their worktrees contain 6 files and no `.adoc`. `T-0142`'s own output proves the consequence: `coverage/rules_coverage.json` → `{'paths':56,'covered':56,'uncovered':0,'rule_files':3,'rule_files_matching':3}`. Its oracle needs `>= 66`. Unsatisfiable regardless of work quality.
2. **Structurally broken oracles.** Read from the cards at seq 2932 / 2934:

```
T-0141: python -c "import json; d=json.load(open("docs/rules/index.json")); …"
T-0142: python -c "import json; c=json.load(open("coverage/rules_coverage.json")); …"
```

Nested unescaped `"` inside a `python -c "…"` run through `shell=True` under cmd.exe. These cannot pass on any shell. `T-0145`/`T-0146` (seq 2977/2978) use `'` and are correct.
3. **Stale leases with no supervision.**
```
open leases: T-0139 f117, T-0141 f118, T-0142 f119
T-0141 agent pid dead; T-0142 agent exited; neither result processed for >55 min
no AGENT_EXITED event exists for either
```

Do not void them yet — voiding is state-changing and the leases are still held. **Release the leases, then void**, per Claude's caution and the operator-only rule.

### D-5 — Keep the incident open

**Agree, and it should be broader than v2's closure list.** Add N-10 and N-11 below; both are new and both are live. Recommended closure conditions:

1. N-1 resolved with *pin-faithful* content (§D-2), not just "files present in HEAD".
2. `integrate` refuses to record INTEGRATED without a non-empty commit reachable from `main`.
3. Supervision reconcile-on-start implemented and tested; `Dispatcher.run(max_seconds=N)` either hands off in-flight leases or refuses to start with any.
4. R-09 moved before `claim`, or lease released on refusal (N-10).
5. `check_stall` uses `renewed_at` (N-12).
6. Policy-pin loop closed so `PINS_CHECKED` cannot clear its own failure (D-3).
7. `hermes` cwd mechanism decided by canary (§5).
8. Ledger integrity: I1 repaired legitimately, deletions tombstoned (N-14).

## 4. Relay E answers (read-only, what the artifacts can and cannot say)

**1. Where does the per-lease poll run; what happens to in-flight leases at end?**
`Dispatcher.run_forever(max_seconds=N)` owns it. On deadline it `break`s out of the loop with no cleanup, no revoke, no event, no persistence. Nothing can adopt the leases. See §2 Concern 2 for the code.

**2. Were the agent processes alive after expiry?**
**Not answerable from the ledger.** Every incident `CLAIMED` payload carries `"pid": null` and `"worktree": ""`; no `AGENT_EXITED` exists for any T-0131/0136/0139/0141/0142 lease. The only evidence is log last-write times, which the log does not record. Treat the ledger as silent here, not as evidence of death.

**3. What wrote LEASE_EXPIRED, from which loop, at what interval?**
`Conductor.tick()` → the **uncommitted** auto-revoke block in `src/fleet/conductor.py` (part of `C:\temp\uncommitted.patch`). Interval: `dispatch_tick_s = 5`. Payloads match that block exactly (`granted_at`, `ttl_minutes`, `elapsed_minutes`).

**4. Does `work/T-0131-110` still exist?**
**Yes.** 66 files present, clean. Its checksums hash the true pinned blobs but use a `docs/rules/`-prefixed path convention. Content is byte-identical to `75a037f`; content-identical to main modulo CRLF. It is a recoverable, and arguably better, artifact.

**5. How did T-0139 reach INTEGRATED?**
Not through the merge queue. Three `INFRASTRUCTURE_FAILED` merges (seq 2947/2950/2960), one incident (2962), then `INTEGRATING` + `INTEGRATED` at 03:32:22 with `commit: ""` (seq 2969/2970). `Kernel.integrate` checks **nothing** about git — no sha, no reachability, no path check. There is no merge sha in the payload.

**6. What does R-09 do on failure — event, queue item, or silent skip; does the Dispatcher continue?**
Neither silent nor correct. `Harness.start()` sets `result.error`, returns `None`, and records **no event of its own**. The Dispatcher then does:

```python
            run, failure = self.harness.start(task, chosen)
            if run is None:
                self._start_backoff(task.id, failure.error or "claim refused")
                self._emit_blocked(task.id, failure.error or "claim refused", report)
                continue
```

So it **continues to the next card** (K-4 starvation avoided), and a `FLEET_BLOCKED` *is* emitted — but it is labelled "claim refused" when the claim **succeeded**, and the lease is never released. See N-10.

**7. R-11 `main_tree_status` payload and comparison?**
Records the full `git status` text into the `AGENT_STARTED` payload (`"main_tree_status": main_status`), and again into the exit event. Nothing compares the two — there is no delta logic, so it is a record, not an alert. Claude's N-5 conclusion holds.

**8. Which of `order.py`/`spawn.py`/`conductor.py`/`merge.py` differ from HEAD, and which were present when T-0139 f117 spawned?**
`order.py` and `spawn.py`: clean, fully committed in `aed9aec`. `conductor.py`: +42 lines (auto-revoke). `merge.py`: `--ff-only` → `--no-ff` fallback. Both uncommitted, therefore **both were live in the working tree** when f117 spawned at 03:06:17Z and when the merges failed.

**9. The two untracked reports.** Both supplied. `EVENT_LOG_VIOLATION_REPORT.md`: three `SENTINEL_RUN` events (seq 382–384) were created and then **deleted at filesystem level with no Kernel tombstone**; hashes preserved only in the report. `pilot/assessment/report-conductor-stall-v1.md`: the origin of the auto-revoke patch Claude is now reviewing, and it confirms the design intent was TTL-only, which is where N-12 comes from.

## 5. The Hermes cwd lead — the flags exist, but the mechanism is probably not the one Claude named

`hermes chat --help` on this machine [VERIFIED]:

```
  --no-restore-cwd      Don't cd into a resumed session's recorded working
                        [directory]
  --in DIR              Change into DIR before starting or resuming (scopes '
                        --resume latest' / -c lookups to DIR's workspace).
  --worktree, -w        Run in an isolated git worktree (for parallel agents …)
```

Three points:

- **Claude is right about `--worktree`**: it makes Hermes create its own worktree. Do not use it.
- **`--no-restore-cwd` only applies to a *resumed* session.** Every incident lease carried `"session": ""` and `"restart_count": 0` — these were fresh invocations. On a fresh run the flag is a no-op, so it cannot be the fix even though the names match.
- **`--in` is documented as a session-lookup scoper**, not a guaranteed chdir for file tools ("scopes '--resume latest'/`-c` lookups to DIR's workspace"). Adding it is worth testing, but the help text does not promise what we need it to promise.

Current adapter config (`agents.toml`, `hermes-beam` and siblings) has no `--in` at all, and says why:

> `# The working directory is already set by the harness (cwd=worktree), so no --in flag is needed.`

That comment is the failed assumption. `spawn.py` does set `cwd=target` at line 246 and in the `_spawn_with_console` path via `Set-Location`, so the harness side is correct — the break is inside Hermes.

**Proposed canary, revised** (this is the one thing here that genuinely needs a test, and I did not run it):

1. `--in <worktree>` alone on a fresh run, through the real `spawn_slot` path.
2. `--in <worktree> --no-restore-cwd` together — cheap, but expect no change on a fresh session.
3. If neither works, test whether Hermes honours `cwd` at all by having it print `os.getcwd()` before any tool call; that distinguishes "Hermes ignores cwd" from "Hermes' file tools are rooted elsewhere".
4. Until decided, the per-profile rule (absolute paths in the generated order) is the only mechanism with a demonstrated success, and it should be labelled as such in `docs/free-models.md` rather than treated as a fix.

## 6. New findings this pass

| # | Finding | Evidence | Why it matters |
|---|---|---|---|
| **N-10** | **R-09 leaks the lease it just claimed.** In `Harness.start()`, order is: `kernel.claim()` (L256) → `create_worktree()` (L264) → `write_order()` (L272) → **R-09 check** (L277) → `spawn_slot()` (L295). The refusal returns `None, result` at L292 **without `_give_up()`**. No revoke, no quarantine, no event. | [VERIFIED] read of `harness.py:250-304` and `_give_up` at L646 | Each refusal leaves: a permanently LEASED lease, an orphaned worktree with an ORDER.md, and a `FLEET_BLOCKED` that reports "claim refused" when the claim succeeded. **Guaranteed to fire now**: `M docs/rules/index.json` is in T-0141/T-0145's write scope and `M coverage/rules_coverage.json` is in T-0142/T-0146's. |
| **N-11** | **T-0139's lease f117 was never released.** INTEGRATED at 03:32:22; lease still `LEASED`, `granted_at 03:06:17Z`, no `REVOKED`, no `LEASE_EXPIRED`. | [VERIFIED] ledger projection | TTL is 120 min, so at ~**05:06Z** the Conductor will emit `LEASE_EXPIRED` for a DONE task. The uncommitted `check_stall()` returns a stall for *any* expired lease regardless of task state, so this will set the project **STALLED** and add a queue item — a false alarm with a real signature. |
| **N-12** | **`check_stall()` ignores `renewed_at`.** It compares only `granted_at` to `now`. | [VERIFIED] uncommitted `conductor.py` hunk | Heartbeat renewal (`renew_every = 60`) cannot protect a long task. Any task exceeding 120 min is force-revoked while healthy. This is a sufficient explanation for N-3's loss and it will recur. The original stall report designed it this way (§5.2 of `report-conductor-stall-v1.md`), so the defect is inherited, not introduced. |
| **N-13** | **The `--no-ff` fallback cannot fix the failure it was added for.** | [VERIFIED] `merge.py` hunk + seq 2947/2950/2960 text | `--no-ff` converts a *diverged branch* into a merge commit. T-0139's blocker was "local changes would be overwritten" / "untracked working tree files", which `--no-ff` does not address — and indeed all three failures recurred identically. Reasonable hardening, wrong diagnosis; it should not be credited with unblocking anything. |
| **N-14** | **The ledger's own integrity is not established.** | [VERIFIED] sentinel findings + the violation report | I1 (`stops:true`) at seq 18, 50, 382, 385, 1206, 1208, 2089; then `ok:true` at seq 2280 with **no repair event**; three SENTINEL_RUN events deleted with no tombstone (`EVENT_LOG_VIOLATION_REPORT.md`); `fix_chain.py`, `fix_chain_full.py`, `fix_chain_v2.py`, `fix_chain_v3.py`, `renumber.py`, `renumber_01.py`, `reset_blocked.py` all sitting in the repo root. Every timestamp argument in this incident — mine included — rests on this log. Two INCIDENT events are literally `{"message":"list"}` (seq 2290, 2944). |
| **N-15** | **`INTEGRATED` is reachable with an empty commit.** | [VERIFIED] seq 2969/2970 | See Concern 1. This is the highest-severity structural defect after R-09, because it silently converts an infrastructure failure into task completion and cascades to every downstream card. |

## 7. Recommended order of work

1. **Decide D-1.** Everything else is provisional while "who acted" is unverified. [OPEN]
2. **Ratify or revert the TTL change, and promote or discard the auto-revoke patch** — as one act, since they are coupled (seq 1948 says so explicitly). Reverting the policy without the patch restores the original silent-stall defect; promoting the patch without a `renewed_at` fix introduces N-12.
3. **Close N-10 before promoting anything else.** One `_give_up()` call, or move the R-09 block above `kernel.claim()`. It is a four-line fix and it is currently the cheapest way to manufacture the incident's own signature.
4. **Land the corpus pin-faithfully** (§D-2), with the `.gitattributes` rule. Then release the T-0141/T-0142 leases and void them.
5. **Make `integrate` prove it landed** (N-15) — merge sha in the payload, report-only sentinel reachability check.
6. **Release T-0139's f117 lease and handle the 05:06Z expiry** (N-11) before it generates a spurious STALLED.
7. Reconcile-on-start for leases; handoff or refusal for `run --seconds N`.
8. Hermes canary (§5). Keep the hint rule as a declared fallback meanwhile.
9. Then review the two patches properly, on a clean checkout, and re-run the suite there.

## 8. What I did not do

Nothing was reset, cleaned, stashed, committed, voided, revoked or re-recorded. No agent was spawned. The only files written were the two patch files in `C:\temp` (as instructed) and this report. Two `.py` helper scripts used for the hash comparisons were created in `C:\temp` and deleted afterwards.

I have not reviewed the two patches line by line — that is the next pass, and `C:\temp\combined-77a56db-aed9aec.patch` plus `C:\temp\uncommitted.patch` are the inputs.
