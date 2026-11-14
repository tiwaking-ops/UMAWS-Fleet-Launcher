# Canary results — evidence draft

**Status: DRAFT, under `tmp/` only.** No tracked file was edited, nothing staged, nothing committed.
Prepared for the operator in response to `prompt-canary-process-opencode-to-freebuff-v1.md`.

---

## 0. Which session is answering, and the live-tree question

| Field | Value |
|---|---|
| Session id | `ses_e390b97b1ffejF1UDOSQ7fG137` |
| Title | "Process canary results as draft" |
| Agent / model | `build` / `mimo-v2.6-flash-free` (MiMo-V2.6-Flash Free, provider `opencode`) |
| Directory | `C:/temp/projects/testproject1` |
| Created | `2026-11-10T19:34:29Z` = **2026-11-11 08:34:29 NZ (UTC+13)** |
| First user message | verbatim the operator instruction being answered now |

**This session is not the session that edited the live tree on 2026-11-10.** It did not exist until
2026-11-11 08:34 NZ, which is after both the 17:35 NZ and the 22:49 NZ windows of reviewer item 1.
In this conversation this session has written only these files, all under `tmp/`:

- `tmp/canary-evidence-2026-11-11/probe_session.py`, `probe_session2.py`, `probe_session3.py` (read-only DB probes)
- `tmp/canary-evidence-2026-11-11/0004-rebased.patch` (a `git format-patch` output, **not applied**)
- this file

`git status --porcelain` at the start and the end of this pass is unchanged: 31 modified tracked files,
none of them touched by this session.

**Which session edited the live tree on 2026-11-10: unknown.** Reviewer item 1 is unsettled and this
draft does not attempt to resolve it; resolving it is not a precondition of anything asserted below.

---

## 1. The four supervised canary cards

All timestamps UTC. Seq numbers are from the live chain `.pm/events/*.jsonl`.

| | **T-0189** | **T-0190** | **T-0191** | **T-0196** |
|---|---|---|---|---|
| fence | 156 | 157 | 158 | 159 |
| base_commit | `bcf145c86e483df4d980e03fff8a743076a35571` (seq 3471) | `e302119728dcdf066b7f5555a14df4e5424da1bc` (seq 3509) | `ce22591530ac17fe5f3dda313426d179993ded2c` (seq 3528) | `9bb0139a16bb6fa6d6a2fda2ef29a1a3b653db3b` (seq 3547) |
| agent profile | `kilo-auto` / adapter `kilo` / lease holder `kilo-auto` (seq 3471, 3472, 3476) | same (seq 3509, 3510, 3514) | same (seq 3528, 3529, 3533) | same (seq 3547, 3548, 3552) |
| agent wall time | **81 s** (AGENT_STARTED seq 3472 `06:23:20` → AGENT_EXITED seq 3475 `06:24:41`); lease digest `wall_s=63` (seq 3474) | **120 s** (seq 3510 `17:49:33` → seq 3513 `17:51:33`); digest `wall_s=65` (seq 3512) | **65 s** (seq 3529 `18:28:12` → seq 3532 `18:29:17`); digest `wall_s=64` (seq 3531) | **100 s** (seq 3548 `19:56:31` → seq 3551 `19:58:11`); digest `wall_s=60` (seq 3550) |
| SUBMITTED ts (seq) | `2026-11-09T06:24:41Z` (**3478**) | `2026-11-09T17:51:35Z` (**3516**) | `2026-11-09T18:29:18Z` (**3534**) | `2026-11-09T19:58:12Z` (**3554**) |
| ORACLE_RESULT ts (seq) | `2026-11-09T06:28:54Z` (**3479**) | `2026-11-09T17:58:26Z` (**3518**) | `2026-11-09T18:35:13Z` (**3535**) | `2026-11-09T20:09:33Z` (**3556**) |
| gate cmd | `pytest -q` | `pytest -q` | `pytest -q` | `pytest -q` |
| gate exit | **1** (`exit: 1`, `ok: false`) | **0 implied, not recorded** — payload is `{"cmd","no_ff_fallback","ok":true,"reintegration","stage"}` with **no `exit` key**, and the bundle has no `gate_output` | **0** (bundle `gate_output.exit = 0`) | **0** (bundle `gate_output.exit = 0`) |
| verification result | VERIFIED seq 3480, `class: ORACLE_FAILED`, "the gate command 'pytest -q' exited 1" | INTEGRATING seq 3519 → INTEGRATED seq 3520 | INTEGRATING seq 3536 → INTEGRATED seq 3537 | INTEGRATING seq 3557 → INTEGRATED seq 3558 |
| merge sha | **none** | `0edc0dc0f35b8f48b2f74f4f07f4a09bb087e723` | `c7fcdf39af7beb41c9dc9dcb829fc27310a8fc7a` | `951d1ee5b40aff2d24eb5807195fd4999d33705c` |
| merge author | n/a | `umaws-pilot <umaws-pilot@localhost>` (author and committer) | `umaws-pilot <umaws-pilot@localhost>` | `umaws-pilot <umaws-pilot@localhost>` |
| merge message / date | n/a | "Merge branch 'pmk/T-0190-157' into HEAD", Tue Nov 10 06:51:40 2026 +1300 | "Merge branch 'pmk/T-0191-158'", Tue Nov 10 07:29:23 2026 +1300 | "Merge branch 'pmk/T-0196-159'", Tue Nov 10 08:58:17 2026 +1300 |
| bundle id | `EB-T-0189-156` | `EB-T-0190-157` | `EB-T-0191-158` | `EB-T-0196-159` |
| bundle byte size | **1849** bytes | **1849** bytes | **3566** bytes | **3566** bytes |
| `gate_output` | **absent** | **absent** | **present**, `exit 0`, `ok true`, `failed_tests []`, 17 stdout-tail lines | **present**, `exit 0`, `ok true`, `failed_tests []`, 17 stdout-tail lines |
| final task state | **VOID** (`.pm/views/ledger.md:197`; `TASK_VOIDED` seq 3506 `2026-11-09T17:39:18Z`, reason "Superseded by T-0190 … T-0189 exhausted its 1/1 attempt on stale base bcf145c") | **DONE** (ledger:198) | **DONE** (ledger:199) | **DONE** (ledger:204) |

### 1a. T-0189 is a failure — record it as a failure

- Failing test: **`tests/test_rules_baseline.py::test_coverage_reports_case_statuses_and_evidence`**
  (ORACLE_RESULT seq 3479 `failed_tests`, and VERIFIED seq 3480).
- Base-tree cause, from the recorded traceback: the test asserts `assert (ROOT / test).is_file()` for every
  case's test list, and case `'8.0'` ("LAND MOVEMENT") lists `tests/test_transport.py`, which resolves to
  `C:/Users/Tiwa Pene/AppData/Local/Temp/pmk-merge-h5yyzudd/merge/tests/test_transport.py` — **absent from the
  merge worktree on base `bcf145c`**. The test then fails at `tests\test_rules_baseline.py:124`.
- Disposition: **superseded by T-0190, not exonerated.** `TASK_VOIDED` seq 3506 records the succession; a
  succession record does not turn exit 1 into a pass. Final state is VOID, and D-69 stays the recorded FAIL.
- Two further `ORACLE_RESULT` events exist on fence 156 and must not be confused with the canary gate:
  - seq **3493** `2026-11-09T09:41:36Z`, `python -m pytest -q`, `exit 0`, note "PDD section 6 full gate run at
    the new HEAD; T-0189 remains REWORK and no task state transition was made";
  - seq **3494** `2026-11-09T10:21:44Z`, `python -m pytest -q`, `exit 1`, failing
    `tests/fleet/test_regressions.py::test_a_failed_agent_started_write_kills_the_process_and_gives_up_the_lease`,
    note "… because the matching harness fix is still uncommitted. T-0189 remains REWORK; no task state
    transition was made."
  Neither changed T-0189's state.

### 1b. The three that reached DONE

T-0190 (fence 157), T-0191 (fence 158) and T-0196 (fence 159) each ran `CLAIMED → AGENT_STARTED →
AGENT_EXITED(OK) → SUBMITTED → ORACLE_RESULT(stage=gate, ok:true) → INTEGRATING → INTEGRATED`, merged under
`umaws-pilot <umaws-pilot@localhost>`, and are `DONE` in the ledger. Their acceptance oracles are recorded at
seq 3504 (v2), seq 3524 (v3) and seq 3545 (v4).

---

## 2. DoD-6 is proven twice, not three times — and no live sentence still says otherwise

**Bundle-level proof (read directly from `.pm/evidence/*/bundle.json`):**

- `EB-T-0190-157` — 12 top-level keys, **no `gate_output` key at all**, 1849 bytes.
- `EB-T-0191-158` — `gate_output` present: `cmd "pytest -q"`, `exit 0`, `ok true`, `failed_tests []`,
  `stdout_tail` 17 lines, 3566 bytes.
- `EB-T-0196-159` — `gate_output` present: identical shape, 3566 bytes.

**Corroborating, independent of the bundles:** the cards themselves differ. T-0190's acceptance oracle
(seq 3504) requires `'rule_files=69'`, `'CNA-Rules.adoc'`, `'base='`, `'gate=pytest -q'` — **it does not
require `h6=gate_output`**. T-0191 (seq 3524) and T-0196 (seq 3545) both additionally require `'h6=gate_output'`.
So the three cards were never equivalent tests of DoD-6.

**Every sentence that implied three, and its state today:**

| Where | Text | State |
|---|---|---|
| `HANDOFF.md:191` at commits `eb0c226` / `68907fe` | "**PASS — T-0190, T-0191 and T-0196.**" | **already corrected** by commit `91e5e14` (umaws-pilot, Wed Nov 11 03:13:46 2026 +1300, "Generated with Codebuff") to "**PATH PASS - T-0190, T-0191 and T-0196 reached `DONE` through dispatch; only T-0191 and T-0196 prove DoD-6.**" |
| `HANDOFF.md:10` and `:199` | "the later canary **path** passes (T-0190/T-0191/T-0196; only T-0191 and T-0196 carry `gate_output`)"; "DoD-6's non-empty `gate_output` is proven by T-0191 and T-0196 only" | **already correct** |
| `pilot/repair-resumption-checklist-v1.md:21, :29, :31` | all three as path passes, "DoD-6 proven twice" | **already correct** |
| `docs/reports/fleet-launcher-repair-completion-v2.md:8, :102, :106, :119` | "proven by `T-0191` and re-proven by … `T-0196`" | **already correct** |
| `docs/reports/fleet-launcher-repair-completion-v2-assessment.md:37, :48` | "DoD-6 is now proven twice (T-0191 and T-0196)" | **already correct** |
| `report-freebuff-UMAWS-Fleet-Launcher-repair-v1.md:104` | "so DoD-6 is proven twice … not a third DoD-6 proof" | **already correct** |

A full-text search of every `.md` in the tree (excluding `.git/`, `work/`, `tmp/`) for `all three` +
`gate_output|DoD-6|H6` and `three` + `canar|proof|bundle` returns **no** sentence asserting three DoD-6 proofs.
**Nothing in the live tree needs correcting on this point.**

**What is still missing is a scoping erratum in the decision register** (item 2 of the instruction): the
decision text must not be rewritten, so the scope is recorded as an appended erratum. Proposed text and diff
are in §7. Note that D-73's own wording already says "so DoD-6 is proven twice" (`pilot/decisions.md:783`);
the erratum adds the bundle-level basis and the card-oracle asymmetry so the scope cannot drift later.

---

## 3. `HANDOFF.md` — the premise in item 3 is stale; no diff is needed for that line

The instruction says *HANDOFF.md currently says "Canary PASS — T-0190, T-0191 and T-0196"*. **It does not,
any more.** Checked three ways:

1. `Select-String HANDOFF.md -Pattern 'Canary PASS'` → no match.
2. `git log --all -S'Canary PASS - T-0190'` and `-S'Canary PASS — T-0190'` → **no commit on any ref** ever
   contained that exact phrase; the conflation was written as "**PASS — T-0190, T-0191 and T-0196.**".
3. `git log --format=... -S'PATH PASS' -- HANDOFF.md` → exactly one commit: **`91e5e14`, umaws-pilot,
   2026-11-11 03:13:46 +1300**, message "docs: reconcile the canary handoff and resumption checklist",
   body: "… T-0190, T-0191 and T-0196 as path passes: only T-0191 and T-0196 carry a non-empty gate_output,
   so DoD-6 is proven twice, and T-0189 stays a real gate failure rather than a merely historical one."

The diff that already did the job (reproduced from git, for the record — **not** proposed again):

```diff
--- a/HANDOFF.md (as at eb0c226 / 68907fe)
+++ b/HANDOFF.md (as at 91e5e14, current HEAD)
@@ Canary row
-| Canary | **PASS — T-0190, T-0191 and T-0196.** T-0191 (fence 158): `SUBMITTED` seq 3534 → `INTEGRATED`
- seq 3537 at `c7fcdf3`, bundle `EB-T-0191-158`; T-0196 (fence 159): `SUBMITTED` seq 3554 → `INTEGRATED`
- seq 3558 at `951d1ee`, bundle `EB-T-0196-159`. Both ran under `kilo-auto`/`kilo`, exited 0, and passed the
- gate `pytest -q` (exit 0). T-0190 (fence 157, merge `0edc0dc`, bundle `EB-T-0190-157`) was the first pass;
- T-0189 (fence 156, D-69) remains the historical gate failure. `pmk status` still reports **PAUSED**; no A10
- resume is recorded |
+| Canary | **PATH PASS - T-0190, T-0191 and T-0196 reached `DONE` through dispatch; only T-0191 and T-0196
+ prove DoD-6.** … bundle `EB-T-0190-157` — **no `gate_output`** … T-0189 (fence 156, base `bcf145c`, D-69)
+ remains a real gate failure — superseded by T-0190, not exonerated. … |
```

The wording the instruction asked me to propose is therefore **already the wording in the file**, and it does
exactly what was asked: all three stay path passes; only T-0191 and T-0196 carry `gate_output`.
**No diff for item 3.** The diffs I *do* put up for approval are in §7, and they cover items 4 and 7 plus the
item-2 erratum.

---

## 4. What the canary evidence does NOT show — recorded as unknown

### 4.1 `pmk canary run` has never produced a durable record in the live chain

- `CANARY_STARTED`: **0 occurrences** in the whole chain. `CANARY_FINISHED`: **0 occurrences.** In fact **no
  event type beginning `CANARY` exists at all.** Measured by parsing every line of every `.pm/events/*.jsonl`.
- Chain size while this pass ran: **3631 events** at first read, **3632 events** at second read (seq **3631**
  `SENTINEL_RUN` `2026-11-10T14:51:12Z`, seq **3632** `PINS_CHECKED` `2026-11-10T19:42:49Z` were appended
  during the pass). Seq range 1..3632, no gaps, no duplicates. The documented "3630 events" in `HANDOFF.md:186`
  and `:199` was correct when `91e5e14` was written (2026-11-10 14:13Z, before seq 3631) and is now stale by
  two events — a moving figure, not an error.
- `src/fleet/canary.py` is **untracked**: `git ls-files --error-unmatch src/fleet/canary.py` fails, and
  `git status --porcelain` shows `?? src/fleet/canary.py`. It does contain `run_canary()` (line 39) emitting
  `CANARY_STARTED` (line 93) and `CANARY_FINISHED` (line 134).
- **Therefore: `pmk canary run` has never produced a durable record in the live chain, and the three passes
  above came from `pmk dispatch run` / the Console, not from `run_canary`.** Evidence for the route: D-69
  (`pilot/decisions.md:767`) records T-0189 run "with `pmk dispatch run --seconds 900`; the Console was open
  for observation only"; `docs/reports/fleet-launcher-repair-completion-v2.md:108` records that during T-0191
  "the separate `pmk dispatch run` loop was stopped before the gate started, as in the T-0190 run, so the
  Console Conductor could integrate", and that for T-0196 "the dispatch and Console processes were stopped only
  after `DONE`".
- **The single-owner canary runner is not tested by any of this.** Do not describe it as tested.

**Corollary that must not be lost:** `tmp/canary-base-20261110/.pm/events` **is** a separate chain of 3136
events that *does* contain `CANARY_STARTED` seq 3124 (`2026-11-10T13:28:32Z`) and `CANARY_FINISHED` seq 3136
(`2026-11-10T13:43:33Z`). Those seq numbers collide with the **live** chain, where seq 3124 is `PINS_CHECKED`
(`2026-11-07T19:02:50Z`) and seq 3136 is `FLEET_ASSIGNED T-0148` (`2026-11-07T19:38:38Z`). `HANDOFF.md:195`
cites "`CANARY_FINISHED` seq 3136" without saying which chain; read against the live chain it points at the
wrong event. Proposed fix in §7.

### 4.2 No dispatch resume, no manual launch, no A10

- `DISPATCH_RESUMED`: **0**. `DISPATCH_PAUSED`: **0**. `MANUAL_LAUNCH`: **0** — whole log, every file.
- `.pm/views/status.md:5-7`: **Project state: PAUSED**; 212 tasks (**READY 12**, LEASED 1, VERIFYING 1,
  DONE 43, VOID 155); **Active leases: 2**.
- **Nothing in the canary results authorizes a resume.** A10 remains unauthorized; the three path passes say
  nothing about `resume_dispatch`.

### 4.3 Reviewer item 3 is still open

`src/fleet/owner.py:237` defines `resume_dispatch(...)`, and **line 250** records
`kernel.record_event("DISPATCH_RESUMED", actor=Actor.human(), …)` with no verification of a human identity.
Unchanged in the live tree. Still open.

### 4.4 Gate duration is UNKNOWN

Measured `SUBMITTED → ORACLE_RESULT` spans (recomputed from the log, all match the figures given):

| Card | Span | Result |
|---|---|---|
| T-0189 | `06:24:41` → `06:28:54` = **253 s** | gate fail |
| T-0190 | `17:51:35` → `17:58:26` = **411 s** | pass |
| T-0191 | `18:29:18` → `18:35:13` = **355 s** | pass |
| T-0196 | `19:58:12` → `20:09:33` = **681 s** | pass |
| T-0148 | `2026-11-07T19:39:36` → `19:43:35` = **239 s** | gate fail (seq 3140 → 3141) |
| T-0150 | `2026-11-07T20:18:45` → `20:41:36` = **1371 s** | pass (seq 3155 → 3157) |

- These spans include bundle verification and queue wait, **not only the gate subprocess**.
- **1371 s > 900 s**, and `src/fleet/merge.py:318` hardcodes `capture_output=True, timeout=900`. A span larger
  than the timeout is only possible if the gate subprocess itself finished in under 900 s. So the subprocess
  was shorter than the span, and **the gate's own duration is not recorded anywhere: unknown.**
- The old `## Gate budget` section asserted both "up to about 12.5 minutes" and "at least 15 minutes". Those
  conflict, and **neither bound is reproducible from the event log** — the log records no gate-subprocess
  duration at all. The reviewer's mandated sentence is "the gate ran **between 12.5 and 15 minutes, unknown**";
  the phrase "**too tight**" must not appear. I am recording the mandated phrasing as instructed; I am *not*
  claiming I measured either bound, because I did not.

### 4.5 The `## Gate budget` section: what can and cannot be recorded about its removal

**What is provable:**

- The live `pilot/repair-canary-runbook-v1.md` has **no** `## Gate budget` section, and no `too tight`,
  `12.5` or `15 minutes` string. File is **unmodified against HEAD** (`git status --porcelain` shows nothing
  for it), 4074 bytes, mtime `2026-11-10 00:43:51 +1300`.
- `git log --all -S'Gate budget' -- pilot/repair-canary-runbook-v1.md` returns exactly two commits,
  **`0c5bc77`** and **`3e9c6bcc…`**, both authored `umaws-pilot <umaws-pilot@localhost>` at
  **Wed Nov 11 03:00:33 2026 +1300**, and **neither is an ancestor of HEAD; no branch contains either**
  (`git merge-base --is-ancestor` exits 1 for both; `git branch -a --contains` is empty). Both *add* the
  corrected section; neither removes anything.
- Every reachable revision of the file (`9e4d047`, `98d8b4f`, `9606757`, `a438901`, `HEAD`) has **zero**
  matches for `Gate budget`, `too tight`, `12.5` or `15 minutes`. **The section never entered tracked history.**
- The old, conflicting wording survives only as an untracked working copy:
  `tmp/review-followups/pilot/repair-canary-runbook-v1.md`, 4009 bytes, mtime **2026-11-09 07:49:16 +1300**:
  > Allow at least **15 minutes** for the gate. The 4-minute figure came from the failed T-0148 gate; T-0150's
  > passing gate ran for up to about 12.5 minutes. The old 900-second timeout was therefore too tight; the
  > fleet setting is `canary_gate_timeout_s = 1200`.
- The corrected wording survives in `tmp/canary-process-0004/…` (4369 bytes, mtime `2026-11-11 02:57:13 +1300`)
  and `tmp/canary-process-verify/…` (4369 bytes, mtime `2026-11-11 03:00:46 +1300`), and in the two dangling
  commits above.
- No `.pm/events` record mentions the file except as a path inside `AGENT_STARTED`/`AGENT_EXITED`
  `main_tree_status` snapshots (seq 3472, 3475).

**What I cannot record: who removed it, and when. Unknown.** No commit, no event and no ref records an edit to
that file other than the four reachable commits listed above, none of which touch the section. The mtime
`2026-11-10 00:43:51 +1300` is a filesystem timestamp, not authorship, and it post-dates the `a438901` commit
(`2026-11-10 00:13:07 +1300`) whose content the file still matches. So the honest record is: **the section is
absent from every reachable revision; any working-tree addition and removal of it is unrecorded, actor unknown,
time unknown.** I will not invent a name or a timestamp for it.

**And the claim does not stay silently gone** — the corrected replacement text is proposed in §7.

---

## 5. Reviewer item 5 — confirmed independently, and delivered as `git format-patch`

**Confirmed by me, with `canary_gate_timeout_s` searched across every file in the tree (`.git/`, `work/`,
`.venv/`, `node_modules/` excluded):**

**Not present anywhere in the live tree** — not in `agents.toml`, not in `src/fleet/merge.py`, not in any test.
The live `src/fleet/merge.py:318` still reads `capture_output=True, timeout=900`, and live `agents.toml` has
no gate-timeout key at all.

It exists only in:

| Path | Kind |
|---|---|
| `tmp/reviewer-patches/patches-rebased/0004-rebased.patch` | raw diff (begins `diff --git`, no `From:` line) |
| `tmp/reviewer-patches/patches-filtered/0004-rebased.patch` | second copy of the same raw diff (not named in the review item) |
| `tmp/review-followups/agents.toml`, `src/fleet/merge.py`, `tests/fleet/test_merge_gate_diagnostics.py`, `pilot/repair-canary-runbook-v1.md` | untracked follow-up tree |
| `tmp/review-followups/artifacts/patches/0004-fix-fleet-record-gate-evidence-and-prove-import-orig.patch` | original raw patch |
| `tmp/canary-process/CANARY-PROCESS-DRAFT-2026-11-10.md`, `prompt-canary-process-opencode-to-freebuff-v1.md`, `.pmwork/HANDOFF.md`, `.pm/views/status.md`, `.pm/events/2026-11-10.jsonl` | narrative / relayed reviewer text only |

**Rename applied:** `canary_gate_timeout_s` → **`gate_timeout_s`** (the setting budgets *every* merge gate, not
only canary gates), together with `canary_gate_timeout()` → `gate_timeout()` and `DEFAULT_GATE_TIMEOUT_S = 1200`.

**Delivered as a real `git format-patch`, not a raw diff:**

- File: **`tmp/canary-evidence-2026-11-11/0004-rebased.patch`**, 21 800 bytes.
- Produced by: `git format-patch -1 3e9c6bcc28f1be680731e5373a86402b69ffef23 -o tmp/canary-evidence-2026-11-11`
  (i.e. by `git format-patch` itself, from the commit object that carries the reconciled change), then renamed
  to the requested name. Header verified:
  `From 3e9c6bcc28f1be680731e5373a86402b69ffef23 Mon Sep 17 00:00:00 2001` /
  `From: umaws-pilot <umaws-pilot@localhost>` / `Date: Wed, 11 Nov 2026 03:00:33 +1300` /
  `Subject: [PATCH] fleet: budget every merge gate and record gate evidence`, followed by a diffstat of
  **9 files changed, 268 insertions(+), 21 deletions(-)**.
- Content checks: `canary_gate_timeout` → **0 hits**; `too tight` → **0 hits**; `gate_timeout_s` → **9 hits**;
  the runbook hunk it carries is the corrected "The gate ran between 12.5 and 15 minutes, unknown. …".
- `git apply --check tmp/canary-evidence-2026-11-11/0004-rebased.patch` → **exit 0** (it applies to the live
  tree). **It has not been applied**, and will not be without your clearance of reviewer item 1.

---

## 6. Standing of the decisions — nothing promoted

| Decision | Register line | Standing |
|---|---|---|
| **D-69** | `pilot/decisions.md:767` | **Recorded FAIL** for the T-0189 canary: gate `pytest -q` exit 1, no merge, "remain `PAUSED`; A10 is not authorized". Stands as a failure record. Not superseded into a pass by anything here. |
| **D-72** | `:779` | "**drafted for operator ratification at CP-4**" — not ratified. Already carries its own DoD-2 erratum at `:781`, which explicitly "does not ratify D-72". |
| **D-73** | `:783` | "**drafted for operator ratification at CP-4**" — not ratified. Register section header `:772` reads "Drafts awaiting CP-4 — not ratified (2026-11-09)". |
| **D-74** | `:785` | "**drafted for operator ratification at CP-4**" — not ratified. Its own text says it "does not ratify D-72, D-73, or itself". |

**Which one I am putting forward, and what it would change:** I propose **D-73**, with the two errata in §7 —
not D-72 and not D-74 standing alone.

- **What ratifying D-73 would change:** it would accept the launcher-repair completion record *at its recorded
  scope* — DoD-1, DoD-2 and DoD-6 PASS; H1/H3/H4/H7 deferred, not passed; H5 and DoD-8 partial; no push;
  programme not declared fully complete.
- **Why D-73 and not D-72:** D-72 still carries the stale sentence "DoD-2 remains red", which its own erratum
  and D-74 both supersede; ratifying D-72 would ratify a sentence the record itself already withdraws.
- **Why D-74 does not stand alone:** D-74 is an H2/DoD-2 execution record (513 passed in 273.37 s at `a4cbd0a`).
  It is the evidence D-73 leans on for DoD-2, not an acceptance of the completion record.
- **Two errata must ride with D-73 or it should not be ratified as-is:** (i) DoD-6 scope = two bundles, per §7;
  (ii) D-73's state sentence "the project remains `PAUSED` with 0 active leases and no `READY` cards" is now
  stale — the live view says PAUSED with **2 active leases** and **12 READY** cards, and HEAD has moved from
  `a4cbd0a` to `5267cdb`.

**I am not ratifying anything.** Ratification is yours, at CP-4.

---

## 7. Exact diffs I am asking you to approve — none applied

### 7.1 `pilot/repair-canary-runbook-v1.md` — restore the corrected `## Gate budget`

> Dependency: the last line names `gate_timeout_s`, which only exists if §7.4 (`0004-rebased.patch`) is also
> applied. If you approve this without §7.4, drop that line.

```diff
diff --git a/pilot/repair-canary-runbook-v1.md b/pilot/repair-canary-runbook-v1.md
--- a/pilot/repair-canary-runbook-v1.md
+++ b/pilot/repair-canary-runbook-v1.md
@@ -56,6 +56,13 @@ Sentinel check
    ./.venv/Scripts/pmk.exe sentinel
    ```

+## Gate budget
+
+The gate ran between 12.5 and 15 minutes, unknown. The 4-minute figure came from the
+failed T-0148 gate; measured SUBMITTED->ORACLE_RESULT spans include queue and bundle
+work, so they do not establish the gate subprocess duration. The fleet setting is
+`gate_timeout_s = 1200`.
+
 ## Abort immediately if any of these is true

 - the worktree path is outside `work/`;
```

### 7.2 `pilot/decisions.md` — append-only erratum scoping DoD-6 (D-73's text untouched)

Insert immediately after the D-73 row (`pilot/decisions.md:783`), before the blank lines preceding the D-74
row at `:785`:

```markdown
**Erratum (2026-11-11) - D-73 / DoD-6 scope:** DoD-6's "non-empty `gate_output`" is proven **twice**, not
three times. `.pm/evidence/EB-T-0191-158/bundle.json` and `.pm/evidence/EB-T-0196-159/bundle.json` each carry
a `gate_output` key (`cmd "pytest -q"`, `exit 0`, `ok true`, `failed_tests []`, 17 stdout-tail lines; 3566
bytes each). `.pm/evidence/EB-T-0190-157/bundle.json` (1849 bytes) has **no `gate_output` key at all**, so
T-0190 is a dispatch-**path** pass only: `SUBMITTED` seq 3516 -> `ORACLE_RESULT` seq 3518 (`ok: true`, **no
`exit` key**) -> `INTEGRATED` seq 3520 at `0edc0dc`; T-0190's numeric gate exit is recorded nowhere. The cards
were never equivalent tests of DoD-6: T-0191's and T-0196's acceptance oracles require `h6=gate_output`
(seq 3524, seq 3545), while T-0190's does not (seq 3504). T-0189 (fence 156) remains a gate **failure** -
`tests/test_rules_baseline.py::test_coverage_reports_case_statuses_and_evidence`, case `8.0` referencing
`tests/test_transport.py` absent from base `bcf145c` - superseded by T-0190, not exonerated; its final state
is VOID (seq 3506). The D-73 text above is preserved unchanged; this erratum records scope only, and does not
ratify D-73, which remains drafted for CP-4.
```

```diff
--- a/pilot/decisions.md
+++ b/pilot/decisions.md
@@ -783,6 +783,12 @@ D-73 | 2026-11-10 | Buffy/Codebuff (executor; drafted for operator ratification
  ... unchanged D-73 row body ...
+
+**Erratum (2026-11-11) - D-73 / DoD-6 scope:** DoD-6's "non-empty `gate_output`" is proven **twice**, not
+three times. ... (full text above) ... which remains drafted for CP-4.
```

### 7.3 `HANDOFF.md` — two factual additions (item 3 itself needs no diff)

**(a)** Append to the end of the Canary row (`HANDOFF.md:191`, after "no A10 resume is recorded"):

```markdown
Provenance: none of these three came from `pmk canary run`. `CANARY_STARTED` and `CANARY_FINISHED` occur
**zero** times in the live chain (measured 3,632 events at `2026-11-10T19:47Z`, seq 1..3632 with no gaps) and
`src/fleet/canary.py` is untracked, so `run_canary` has no durable record here; all three ran through
`pmk dispatch run` / the Console Conductor. Gate subprocess duration is **unknown**: the measured
`SUBMITTED` -> `ORACLE_RESULT` spans (253 / 411 / 355 / 681 s for T-0189/0190/0191/0196) include queue and
bundle work, and 1,371 s for T-0150 exceeds the hardcoded `timeout=900` at `src/fleet/merge.py:318`, which is
only possible if the subprocess itself was shorter.
```

**(b)** Correct the chain citation in the isolated-base paragraph (`HANDOFF.md:195`) so the seq number cannot be
read against the wrong chain:

```diff
--- a/HANDOFF.md
+++ b/HANDOFF.md
@@ -195,7 +195,8 @@
-`SUBMITTED` seq 3132, gate `ORACLE_RESULT` seq 3133 exit 0, `INTEGRATED` seq 3135 at `05b54d2`, and
-`CANARY_FINISHED` seq 3136 `ok: true` with state `DONE`.
+`SUBMITTED` seq 3132, gate `ORACLE_RESULT` seq 3133 exit 0, `INTEGRATED` seq 3135 at `05b54d2`, and
+`CANARY_FINISHED` seq 3136 `ok: true` with state `DONE` - **all seq numbers are from the isolated chain
+`tmp/canary-base-20261110/.pm/events` (3,136 events), not the live chain, where seq 3136 is
+`FLEET_ASSIGNED T-0148` (`2026-11-07T19:38:38Z`).**
```

### 7.4 `tmp/canary-evidence-2026-11-11/0004-rebased.patch` — deliverable, not applied

Already produced (§5). 9 files, +268/-21, renamed to `gate_timeout_s`, carries the corrected `## Gate budget`
text, `git apply --check` exit 0. **Waiting on your clearance of reviewer item 1.**

---

## 8. Handback

**Proven:** four supervised canary cards ran in the live kernel at fences 156-159, all under
`kilo-auto`/`kilo`. T-0189 (fence 156, base `bcf145c`) **failed** its `pytest -q` gate with exit 1 at
`tests/test_rules_baseline.py::test_coverage_reports_case_statuses_and_evidence`, because case `8.0` lists
`tests/test_transport.py`, which is absent from that base; it has no merge, its bundle `EB-T-0189-156`
(1849 bytes) has no `gate_output`, and its final state is VOID via `TASK_VOIDED` seq 3506 — superseded by
T-0190, not exonerated, and D-69 stays the recorded FAIL. T-0190, T-0191 and T-0196 reached `DONE` with merges
`0edc0dc`, `c7fcdf3`, `951d1ee`, all authored `umaws-pilot <umaws-pilot@localhost>`, agent wall times
120 s / 65 s / 100 s. DoD-6's non-empty `gate_output` is proven **twice** — `EB-T-0191-158` and `EB-T-0196-159`,
3566 bytes each, `exit 0`, 17 stdout-tail lines — because `EB-T-0190-157` (1849 bytes) has no `gate_output`
key at all, and because T-0190's card oracle never required `h6=` while T-0191's and T-0196's did. No sentence
in the live tree still implies three: the conflation was `HANDOFF.md`'s "**PASS — T-0190, T-0191 and T-0196.**",
already corrected by `91e5e14` (umaws-pilot, 2026-11-11 03:13:46 NZ) to "PATH PASS … only T-0191 and T-0196
prove DoD-6". Reviewer item 5 is confirmed: `canary_gate_timeout_s` exists only under `tmp/` and in narrative
files, never in the live tree, and `0004-rebased.patch` is now a genuine `git format-patch` (21 800 bytes,
9 files, +268/-21, `gate_timeout_s`, zero "too tight", `git apply --check` exit 0), not applied.

**Unknown:** the gate's own subprocess duration — the six spans (253/411/355/681/239/1371 s) include queue and
bundle work, and 1371 s exceeds the hardcoded `timeout=900` at `src/fleet/merge.py:318`, so the subprocess was
shorter than the span and nothing records how long it took; neither "12.5 minutes" nor "15 minutes" is
reproducible from the log, and I am carrying the reviewer's mandated "between 12.5 and 15 minutes, unknown"
without claiming to have measured it. T-0190's numeric gate exit (only `ok: true`, no `exit` key, no
`gate_output`). `pmk canary run` has produced no durable record in the live chain (zero `CANARY_*` events in
3,632; `src/fleet/canary.py` untracked), so `run_canary` is **untested** by this evidence — the three passes
came from `pmk dispatch run` / the Console. `DISPATCH_RESUMED`, `DISPATCH_PAUSED` and `MANUAL_LAUNCH`: zero
occurrences each, so A10 has never been authorized, and the project is PAUSED with 12 READY cards and 2 active
leases. `src/fleet/owner.py:250` still writes `Actor.human()` unverified — reviewer item 3 open. Who removed
the `## Gate budget` section from the live runbook, and when: **unknown** — it is absent from every reachable
revision and never entered tracked history; only untracked `tmp/` copies carry the old conflicting wording
(`tmp/review-followups/…`, mtime 2026-11-09 07:49:16 NZ) and the corrected wording (`tmp/canary-process-0004/…`
and `-verify/…`, 2026-11-11 02:57/03:00 NZ), and the two commits that add it (`0c5bc77`, `3e9c6bc`, umaws-pilot,
2026-11-11 03:00:33 NZ) are dangling — not on any branch, not ancestors of HEAD. Which session edited the live
tree on 2026-11-10: unknown, and reviewer item 1 stays open.

**Needs your decision:** ratify **D-73** at its recorded scope with the two errata in §7 (DoD-6 scoped to two
bundles; its stale "0 active leases / no READY cards" state sentence superseded) — or keep it drafted — plus
clearance on reviewer item 1 so the four items in §7 may proceed. D-69 remains the recorded FAIL and nothing
here authorizes A10.

**The single question:** *may I apply the four items in §7 — `pilot/repair-canary-runbook-v1.md`,
`pilot/decisions.md`, `HANDOFF.md`, and hand over `tmp/canary-evidence-2026-11-11/0004-rebased.patch` — or must
they all wait until reviewer item 1 (the 2026-11-10 live-tree edits) is adjudicated?*
