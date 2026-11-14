---
document:
  title: "Handoff: Claude (Web) reviewer session for the UMAWS Fleet Launcher (v4)"
  type: "Session handoff"
  status: "Advisory; no authority"
  version: "4.0.0"
provenance:
  author_llm: {name: "Claude", version: "Claude Sonnet 5.5 (Anthropic)"}
  created_date: "2026-11-02"
  last_modified_date: "2026-11-02"
  supersedes: "handoff-claude-umaws-fleet-launcher-v3.md (status sections only; the v3 background still applies)"
audience:
  primary: "The next Claude (Web) session acting as reviewer/advisor"
  secondary: "The operator (decision record)"
epistemic_status: "Tags: [OBSERVED] seen by me in a file, diff or junit this session; [STATED] said by the operator or by Claude Code (the implementing LLM) and not independently verified; [INFERRED] my reasoning; [VERIFY] check before relying on it. Some code details are from earlier in a long session and may have drifted; re-check against the repo."
---

# Handoff: UMAWS Fleet Launcher, reviewer session (v4)

## 0. How to use this handoff

Ask the operator to upload these, then read in this order:

1. This file.
2. `handoff-claude-umaws-fleet-launcher-v3.md` (background: architecture, invariants, the Toy3 run, the original findings).
3. `assessment-claude-umaws-fleet-parallel-decomposition-v1.md` (my assessment of DeepSeek's decomposition proposal; contains the Phase 0 census spec).
4. `incident-report-order-path-v1.md` (the order-path incident; written by Hermes Agent).
5. If available: `proposal-deepseek-umaws-fleet-parallel-decomposition-v1.md`.

Do not rely on this file for exact code. It records decisions, state and method. Verify code claims against the diffs or files the operator supplies.

---

## 1. Your role and working agreements

- **You are the reviewer and advisor, not the implementer.** Claude Code (CC) implements. The operator (Tiwa) relays between you and CC, and runs commands on a Windows 10 machine in PowerShell.
- **Relays to CC go in code blocks**, starting with `From: Claude (Claude Sonnet 5.5), reviewer`. Every relay that could change a tree says: no `git add`, `git commit` or `git reset`; do not delete or move files. CC once staged ~70 junk files into the index; that is why the rule exists.
- **Evidence over prose.** Accept nothing from CC's report on its word. Require: a combined patch (against HEAD), a fresh `pytest_junit.xml` from the same tree, and an honest report that says what was run and what was not. Check the diff, the junit counts and timestamps, and whether tests actually exercise the production path.
- **Never ask the operator to run destructive commands without explaining them.** Use `git --no-pager ...` to avoid the pager hang (press `q` to leave a pager). `git reset` only unstages.
- **Formal reports and proposals** are delivered as markdown files with author (Claude) and version fields (operator preference). Handoffs, assessments and similar follow that format.
- Use the repo's epistemic tags when writing for it.
- **Be honest about your own review errors.** In one place (the Hermes `--in {cwd}` flag, section 7) I accepted a change in v6 without testing its premise.

## 2. Operator and environment

- Operator: Tiwa, New Zealand (NZDT, +13), Windows 10, PowerShell. Free-tier models only: Hermes (Nous), Kilo gateway, pi (orcarouter), cline, opencode (poolside, nvidia, ollama-cloud/beam, anyrouter, google).
- Main repo: `C:\temp\projects\testproject1` (branch `main`), venv at `.venv`. Test command: `.venv\Scripts\python.exe -m pytest -q --tb=short` (about 90 to 120 seconds).
- The incident report shows the CFNA project (Campaign for North Africa board game app, built with the Fleet) running in `testproject1`. I had understood CFNA to live in `C:\temp\projects\cfna`. [VERIFY which, and whether CFNA shares the repo with the UMAWS source.]

## 3. System map (compressed)

- **Kernel (`src/pmk/`)**: `api.py` (Kernel: task create/admit/claim/submit/verify/integrate/revoke/void, incidents, `_actor_from_env`), `events.py` (hash-chained event log in `.pm/events/*.jsonl`), `state.py` (reducer; event-sourced), `bundle.py` (evidence bundles, `validation_problems()`), `sentinel.py` (invariants), `store.py`, `cli.py`, `models.py` (`TASK_TYPES`, `scope_overlaps`).
- **Fleet (`src/fleet/`)**: `conductor.py` (drain merge queue, infra retry, incidents), `merge.py` (integrate, gate, pytest.ini cleanup), `spawn.py` (`spawn_slot`), `harness.py`, `dispatcher.py`, `overseer.py` (prompt, spawn), `order.py` (work order), `adapters/` (`base.py`, `generic.py`), `plat.py` (spawn, merges stderr into the stdout log).
- **Config**: `agents.toml` (profiles: hermes-oneshot 4, kilo-auto 3, pi-orca-deepseek 2, cline-mimo 1, opencode-strongest 2, opencode-fallback 1) [OBSERVED 2026-10-28]. Only `.pm/constitution.md` and `.pm/policy.toml` are pinned (class K).
- **Concepts**: leases with fences; evidence bundles with oracles; D-L6 strict disjoint write scopes; sentinel invariants I1 to I16. Sentinel stop list: I1, I3, I6, I8'. I5 (bundle/oracle problems) is report-only; I13 is views drift; I16 is out-of-band file changes.
- **Actor attribution**: `PMK_ACTOR` formats `human:<name>`, `worker:<profile>`, `overseer:<profile>`, `agent:<x>`.

## 4. What was done (reviews of CC's patches v5 to v11)

Reviewed and accepted in the end, committed as **`548885e`** (24 files) and **`9f2dbaa`** (2 files, `merge.py` and its test). Final junit: **303 tests, 0 failures** (2026-10-28).

- `task_void`: human-only, fails closed; CLI reads `PMK_ACTOR` first. Other state-changing commands (`submit`, `verify`, `integrate`, `revoke`) are NOT actor-guarded; only the Overseer prompt forbids them. The docstring was corrected to say so.
- Guards: `submit` needs LEASED; `verify` accepts SUBMITTED or VERIFYING (stops the T-0009 double integrate). Task type is checked at create and admit against `TASK_TYPES` (implement, review, verify, plan, maintain, research); only implement/review/plan have profile roles, so the other three are admitted but never dispatched.
- Conductor: infra retry counted per (task, fence) with backoff; incident ids `I-<task>-<fence>`; timestamps UTC-safe; `clock_parse` failure records at most one event per (task, fence) via an event-log lookup. Merge conflicts are classed GATE_FAILED and go to REWORK, not infra retry.
- Kernel and merge share `Bundle.validation_problems()` as the pre-merge check; `Kernel.integrate` raises `KernelError("invalid_bundle")` for an unreadable bundle.
- Sentinel: bundle looked up from the INTEGRATED event; structural breaches are I6 (stop), oracle/validation problems are I5 (report-only). Run on a copy of testproject1's `.pm`: 10 findings, 0 stops (9 x I16, 1 x I13). Never run on Toy3 (folder not found).
- `spawn_slot`: explicit `actor` parameter (default `worker:<profile>`; the Overseer passes `overseer:<id>`), `PMK_ACTOR` always set last, scrubbed env stays scrubbed, `env=None` inherits `os.environ`. Five tests call `spawn_slot` itself. `_spawn_with_console` takes `env`.
- Hermes: `-Q` writes `session_id: YYYYMMDD_HHMMSS_<hex6>` to STDERR (verified by hand: gone under `2>$null`); plat.spawn merges stderr into the log; regex `\d{8}_\d{6}_[0-9a-f]+`, last match wins. `--provider nous` removed. Real argv verified: `hermes chat -q "hi" -Q --yolo --cli --source tool -m reflection/beam-1.0-501b-a23b:free` works (after Nous re-auth).
- `pmk init` writes a root `pytest.ini`; `merge.integrate` removes an untracked, byte-identical Kernel-default `pytest.ini` only when the committed branch diff adds one (after `commit_worktree`, before the fast-forward). This addresses the T-0009 untracked-file fast-forward block.
- Also: `default_branch()` instead of hard-coded `main`; per-project fleet state; `docs/free-models.md`, fixtures.

## 5. Current repo state (as last known)

- HEAD includes both commits above. Test suite 303 passing.
- **Uncommitted, by design (operator decides):** `.pm/events/*` (incl. untracked `2026-10-26.jsonl` with 39 events, among them the two no-op `TASK_REVOKED` events seq 281/282 written by `tmp/revert_t0003*.py` and the incident at seq 291 recording them), `.pm/views/*`, `.pm/.gitattributes`, `.claude/skills/quotagate-rule/SKILL.md` (173-line hand rewrite), `CLAUDE.md`, `README.md`, `pilot/STATE.md`, `tmp/` (four scratch files; the two `revert_t0003*.py` scripts hard-code the live project path and append raw events; never run them), `CLAUDE.7z`, various `report-*`, `session-report-*`, `*.patch`, `pytest_out*.txt`, `single.txt`, and `pilot/assessment/bundle/fixtures/quota-credits.txt` (purpose unknown).
- **Uncommitted code from the incident fix (Hermes Agent):** `order_prompt()` in `src/fleet/order.py` and four spawn sites in `harness.py` and `dispatcher.py`. [STATED in the incident report; not reviewed by me.]
- The fleet and console must be restarted to load new code. [VERIFY that the operator did.]

## 6. Work since the commits

1. **Combined model names.** `opencode run -m <provider>/<model>` works with no `--provider` (operator-tested; already how the opencode profiles are written). `pi --model <provider>/<model>` works too: tested with `poolside/poolside/laguna-s-2.1` and `orcarouter/deepseek/deepseek-v4-flash-free`. Pending: test the other three orcarouter models (`z-ai/glm-5.3-flash-free`, `tencent/hy3-free`, `tencent/hy4-preview-free`), then edit the pi profile: drop `--provider orcarouter`, use `--model {model}`, and ADD a `model =` line (the profile has none today, so `{model}` would be empty). A relay for that was drafted; its status is unknown.
2. **`family` problem (declared, not verified).** `opencode-strongest` has family "opencode" and `opencode-fallback` "opencode2", yet both run `poolside/poolside/laguna-s-2.1`; `hermes-oneshot` is "anthropic" but runs the reflection beam model. If the independence rule compares family strings (D-L11/D-L12; not seen), same-model profiles could "independently" verify each other. A relay was drafted; status unknown.
3. **Assessment of DeepSeek's decomposition proposal.** File created (see section 0). Verdict: adopt the direction, not the plan as written. Main points: diagnosis unproven (one snapshot); lint checks safety not parallelism; validation happens after cards exist (125 of 130 CFNA cards voided; void is operator-only; voided cards probably count against `max_total_tasks = 500` [VERIFY]); nine possible "gated" causes (G1 to G9); recommended phases: 0 census, 1 unblock (Dispatcher look-ahead, REWORK sweeper, orphan report, low-water-mark replan, capacity fixes), 2 manifest/module-map/lint v2/prompt v2, 3 scheduling and calibration. The operator chose to run the Phase 0 census first, on a copy.
4. **Order-path incident** (section 7).

## 7. The order-path incident

**Report (Hermes Agent, `stepfun/step-3.7-flash:free`, 2026-11-02):** every spawned agent was told to "Read .pmwork/ORDER.md ..."; a stale project-root `.pmwork/ORDER.md` (T-0004, written 2026-10-30) was read instead of the worktree's; the agent claimed to have done T-0004; the harness oracle then failed. Fix: absolute-path `order_prompt(worktree)`. Chain affected: T-0131, T-0132, T-0133, T-0136.

**My assessment: the defect is real and the fix is worthwhile, but "primary stalling mechanism" is not established.**

1. The failures were three 120-minute **lease expiries**, not fast oracle failures. An agent that finished the wrong task and exited would have caused a quick oracle failure and attempt rotation. That points to agents that never exited, or to no supervisor running (the report mentions a manual `dispatch run --seconds 600` loop and dismisses it as secondary without evidence).
2. The timeline contradicts itself: attempt 2 is claimed at 13:58, two hours before attempt 1's expiry at 15:58, yet expires at 21:29, the same instant as attempt 3.
3. Attempts 1 and 2 were **pi** profiles; the report blames Hermes. Only one log is quoted (T-0136, `113-0.log`), and its profile is not stated. If pi also read the root file, the cwd problem is general.
4. Nobody has shown why the child ignored its `cwd`. The harness sets `cwd=slot.worktree`. **My own v6 review accepted CC's removal of `--in {cwd}` from the Hermes argv** (the comment said the harness sets cwd) without testing whether Hermes honours process cwd. The stall started 2026-11-01, after those changes. [INFERRED; verify with `git log -p -- agents.toml`.] It cannot explain pi failures.
5. **Governance:** the recovery used `project_set_state`, `task void`, `queue decide` and `revoke`, which are human-only in our model. If an agent ran them via Python calls, the actor guards were bypassed (this is finding 9 from v3 again). [VERIFY the recorded actors.]
6. The report claims `pytest -q` 100% pass without evidence, was not reviewed for code, and the fix is uncommitted in a dirty tree.

**Operator decisions (via tap questions):**
- Harden further with BOTH: re-add the Hermes working-directory flag (if it exists and a test shows it is needed) AND a per-profile pre-flight canary self-test.
- An agent that exits with no changes in its worktree **fails the attempt immediately**.
- Run the Phase 0 census on a copy first.

**Steps handed to the operator (status: results not yet received):**
- **Step 1 (manual, 5 minutes):** `hermes chat --help` to find a working-directory flag; then a decoy test in `C:\temp\canary` (git repo with a `ROOT-DECOY` order file at the root and a `WORKTREE-REAL` order file in a worktree at `work\wt`; run Hermes, pi and opencode from the worktree with the prompt "Read .pmwork/ORDER.md and reply with only its first line."). Any CLI that prints `ROOT-DECOY` resolves from the repo root.
- **Step 2:** rename (do not delete) the stale root file: `Rename-Item .pmwork\ORDER.md ORDER.md.stale-20261102`.
- **Relay A (read-only evidence for CC):** raw events for T-0131 fences 109 to 111 and T-0136 fences 113 and 114 (including `AGENT_STARTED` argv/cwd/worktree, exits, oracle results); was a dispatcher running during 13:34Z to 22:09Z on 2026-11-01; which profile ran each log; reconcile the timeline; `git log -p -- agents.toml` for `--in {cwd}`; who wrote the root `ORDER.md` (T-0004 fence 5 worktree path); actors on void, queue decide, revoke and `project_set_state` events since 2026-11-01; is `.pmwork/` in `.gitignore`.
- **Relay C (census):** Appendix A of the assessment, run on a COPY of the CFNA `.pm` and `agents.toml`, read-only.
- **Relay B (implementation), to be written after A, C and Step 1 are back:**
  - Hermes working-directory flag if it exists and is needed; keep the absolute path as a second layer (check backslash handling in argv on Windows, consider forward slashes).
  - `pmk fleet selftest [--profile X]`: spawn each enabled profile through the real `spawn_slot` path in a throwaway repo and worktree; decoy at the root, real order in the worktree, the order asks for a random nonce written to a file; pass only if the nonce file is in the worktree and the decoy untouched; record an event; disable a failing profile with a reason. Uses free quota, so on demand and at project start.
  - `NO_CHANGES`: agent exits with no changes outside `.pmwork/`, attempt fails immediately without running the oracle. Apply to `implement` cards; CC must first check what `review`, `plan` and `research` cards legitimately produce.
  - Sentinel check (report-only) for a root `.pmwork/ORDER.md` that matches no active lease; quarantine (rename) on project start.
  - Tests: decoy test with a fake CLI that resolves paths from the repo root; prompt-regression test over all spawn sites; `NO_CHANGES`; stale-file check.

## 8. Open items register

| ID | Item | Owner | Status | Next action |
|---|---|---|---|---|
| H-01 | Manual canary test and `hermes chat --help` | Operator | Pending | Run Step 1; paste results |
| H-02 | Rename stale root `ORDER.md` | Operator | Pending | Step 2 |
| H-03 | Relay A evidence | CC | Issued; results not received | Review against section 7 doubts |
| H-04 | Relay C census | CC | Issued; results not received | Classify idle slots with the decision tree (assessment section 5) |
| H-05 | Relay B hardening | You, then CC | Not written | Write after H-01, H-03, H-04 |
| H-06 | Commit the Hermes-Agent order-path fix with tests | Operator, CC | Undecided | Review the diff first |
| H-07 | pi profile: drop `--provider`, add `model =` | Operator tests, CC edits | Pending tests of three models | See section 6 |
| H-08 | `family` correction and same-model independence test | CC | Relay drafted; status unknown | Confirm |
| H-09 | REWORK tasks never re-dispatched | CC | [VERIFY]; unchanged since v3 | Census will show stuck REWORK cards |
| H-10 | Classify "auth expired" separately from retryable infra failures | CC | Open | Part of assessment R1 |
| H-11 | Actor guards on `submit`/`verify`/`integrate`/`revoke` | Operator decision | Docstring-only today; never explicitly decided | Ask the operator |
| H-12 | `verify`/`maintain`/`research` task types admitted but undispatchable | Operator decision | Never explicitly confirmed as "keep" | Ask the operator |
| H-13 | Leftover untracked files; `.gitignore` for junk | Operator | Open | Offer exact lines |
| H-14 | Minor: stale `_cleanup_default_pytest_ini` docstring, unused `task` param, test docstring says `["config/"]` but code uses `["config/","pytest.ini"]` | CC | Open | Fix next time `merge.py` is touched |
| H-15 | Re-check queue items Q-006 and Q-007 after restart; incident seq 291 | Operator | Open | |
| H-16 | Decomposition programme, assessment phases 1 to 3 | Operator, CC | Gated by the census | Decide after H-04 |
| H-17 | Which repo runs CFNA (`testproject1` or `cfna`)? | Operator | Unknown | Ask |
| H-18 | Real-data sentinel run on Toy3 | Operator | Folder not found | Accept the testproject1 run unless Toy3 turns up |
| H-19 | Restart console and fleet after code changes | Operator | Unknown | Confirm |

## 9. Reviewer playbook (what worked)

For every CC delivery, in this order:

1. **Composition first.** List the files in the patch (`diff --git` lines). Unwanted: `.pm/events/*`, `.pm/views/*`, `SKILL.md`, `CLAUDE.md`, `README.md`, `pilot/STATE.md`, `tmp/*`, `*.patch`, reports, CRLF churn. Required: new files the tests need (a `*.txt` exclude once removed a fixture).
2. **Junit.** Count, failures, errors, skipped, timestamp, and the presence of the new test names.
3. **Read the code against the claim.** Look for dead `try: pass` blocks, comments that contradict code, docstrings that claim guards that do not exist.
4. **Do the tests exercise the production path?** (Example: "end-to-end" env tests once built the env inside the test and never called `spawn_slot`.)
5. **Mutation reasoning:** would the test fail with the old code?
6. **Unbounded events:** any branch that writes an event every tick.
7. **Re-check earlier asks:** CC tends to answer only the latest relay and drop the rest.

**Recurring CC failure modes:** over-claiming ("already fixed", ticks without evidence); answering "not applicable" instead of testing; staging junk into the index; patch generation drifting between rounds; hand-built reports that read as transcripts. Counter: short, numbered relays; demand evidence; ask CC to state what it could not run.

## 10. Operator command cheat sheet (PowerShell, from the project root)

```
git --no-pager status --short
git --no-pager diff --cached --name-status
git reset                      # unstages only; changes no file
.venv\Scripts\python.exe -m pytest -q --tb=short
```

If a command seems hung, a pager is waiting: press `q`.

## 11. Not verified and caveats

- I have not seen the CFNA ledger, event log, `docs/PDD.md`, or the repo after 2026-10-28, except through the documents listed in section 0.
- Several code details (Dispatcher conflict handling, void-dependency semantics, `scope_overlaps` matching, `max_total_tasks` counting, replan trigger) are [VERIFY]; Appendix D of the assessment lists 12 questions for CC.
- The incident report was written by a free-tier model and contains inconsistent timestamps; treat it as a lead, not evidence, until relay A's data confirms it.

## 12. Suggested first moves

1. Read section 0's files. Ask the operator what has come back from H-01 to H-04, and whether the order-path fix has been committed or reviewed.
2. Review any CC reports with the playbook (section 9). Start with the census (H-04) and the evidence (H-03); they decide the hardening design.
3. Write relay B only after those results.
4. Put the open decisions H-06, H-11, H-12 and H-17 to the operator.
5. Keep the operator's three standing preferences: concise relays in code blocks, markdown files for formal documents, and no destructive commands without explanation.
