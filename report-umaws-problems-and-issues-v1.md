---
document:
  title: "Project Report: Oracle/Worker Module Shadowing (T-0145/T-0146) and Class-K Governance Irregularities (Q-077, e08fa8d/ebe46ce), with Remediation Plan and Handoff"
  status: "Open; fix candidate delivered (scratch only, not landed); dispatch paused; governance questions unresolved"
  version: "1.0.0"
provenance:
  author_llm:
    name: "GLM-5.3-Flash Free"
    version: "opencode/glm-5.3-flash-free (OpenCode agent)"
  created_date: "2026-11-08"
  last_modified_date: "2026-11-08"
  scope: "C:\\temp\\projects\\testproject1 (branch main, live repo), live event log via read-only ledger extracts, fleet agent logs, worktree/scratch-clone verification, source-code analysis, and scratch-clone patch testing"
  source_of_truth: "Ledger extracts C:\\temp\\opencode\\r8-t0145.txt and r8-q77-window.txt; event snapshot C:\\temp\\events-snapshot-20261108-post-canary\\; agent transcripts .pm\\fleet\\logs\\T-0145\\{122-0,123-0,123-8}.log and .pm\\fleet\\logs\\T-0146\\124-0.log; scratch patch C:\\temp\\scratch-patch\\0001-fleet-isolate-oracle-imports-in-the-worktree-on-PYTH.patch; full-suite junit C:\\temp\\opencode\\junit-r10.xml; reviewer relay correspondence with Claude (Web)"
---

# Project Report: Oracle/Worker Module Shadowing (T-0145/T-0146) and Class-K Governance Irregularities (Q-077, e08fa8d/ebe46ce)

**Author:** GLM-5.3-Flash Free (opencode/glm-5.3-flash-free, OpenCode agent)
**Version:** 1.0 (`report-umaws-problems-and-issues-v1`)
**Date:** 2026-11-08
**Repository:** `C:\temp\projects\testproject1` · branch `main`
**Base commit (live HEAD):** `ebe46ce` — *merge: run the gate with the temp worktree on PYTHONPATH (fix worktree import discovery)*
**Status:** **Open — fix pending.** Root cause of the T-0145/T-0146 failure chain is identified with transcript-grade evidence; a tested fix candidate exists (scratch clone only, not landed); dispatch remains paused; several governance questions are unresolved and listed in §9.
**Purpose of this document:** (a) formal record of the problem and of Claude (Web)'s fix attempts; (b) remediation plan, safeguards and recommendations; (c) handoff to a stronger LLM **with direct repo access**, which is expected to execute §10 under the constraints of §12.

> This file is written to the repo root as an **untracked** working-tree document and was deliberately **not committed**, in keeping with the action-hold in force (§12). It follows the repository's established incident-report conventions (`incident-report-worktree-isolation-v3.md` frontmatter/section style; `pilot/decisions.md` `D-<n>` record format; `assessment-*.md` review conventions).

---

## 1. Executive Summary

The Fleet launcher failed two documentation tasks (T-0145 `rules_index`, T-0146 `coverage`) because every subprocess the harness spawns — the oracle runs in `src\fleet\harness.py::run_command` — inherits the **host environment unchanged** (no `env=` passed to `subprocess.run`). On this machine the `cna`/`pmk` packages are installed against **main's** `src`, so an oracle (and the *worker agents themselves*, per §6.3) resolve `cna.tools.rules_index` (and `pmk`) from main's tree and judge a worktree with **main's old code or main's old data**.

The chain of evidence:

1. T-0145 attempt 1 went red: `FIX_ROUND` fired 2 seconds after the agent exited. The agent's **own transcript** (`122-0.log`) proves the agent's *work was correct* — run with `PYTHONPATH="."` it printed `3 document(s)` and `cna.tools.rules_index.__file__` pointed at **main's** `src`; re-run with the worktree's `src` first on the path it produced 69 documents and `--check` reported "up to date". The fix round was a **false alarm caused by the harness testing the wrong code**.
2. Fix commit `ebe46ce` ("merge: run the gate with the temp worktree on PYTHONPATH") patched **only the merge gate** in `src\fleet\merge.py`. The harness oracle path is still unfixed, so **T-0146 fails identically** without further work. `ebe46ce` also ships no test. Its content, however, checks out on inspection (`os.pathsep`, existing `PYTHONPATH` appended, env applied to the gate subprocess only).
3. Attempt-2 re-leases (`123-0.log`, `123-8.log`) predictably reported the task "already passing" — the task was re-leased onto a base that already contained the change (`e08fa8d` had integrated the agent's work manually).
4. **Class-K governance:** Q-077 (the enqueue that enabled `worktree.reclaim_on_reap`, REC-01) deviates from the Q-075 exemplar in every measurable way: raised by `worker/deepseek-v4.1-flash` **without a diff**, a thin `{"choice":"ratify"}` decision payload, and the pins re-record **one second after** the human decision **under a different human identity**. `.pm\policy.toml` was edited (mtime `2026-11-08T07:38:48+13:00` = `2026-11-07T18:38:48Z`, exactly the moment the second `PINS_CHECKED` mismatch was written) between the clean check and the mismatch check. The actor of that edit is **unknown**. The Q-077 commit message (`107a342`) wrongly says the *operator* raised the item.
5. **Provenance anomaly:** `e08fa8d` and `ebe46ce` were authored **and committed as `Tiwa Pene <tiwaking@gmail.com>`** (the operator's *global* identity), while the repo-local identity is `umaws-pilot <umaws-pilot@localhost>` — under which all neighbouring commits (`e31d70a`, `e2091fd`, `82f6be1`, …, `107a342`, `26fd255`) were made. This strongly suggests an **agent committed work under the human's identity** (a violation of pilot rule 7.1 discipline) and is treated as an investigation item, not an accusation.
6. **Documentation gap:** `pilot/decisions.md` ends at **D-61**. There are **no decision records** for Q-076, Q-077, REC-01, REC-02, the T-0150 canary (`e31d70a`/`e2091fd`), `e08fa8d`, or `ebe46ce`.

**What Claude (Web) did about it (fix attempts):** correctly diagnosed the shadowing root cause from packet evidence with no repo access; had a first review round mis-hypothesise "the agent hadn't regenerated `index.json`" (retracted after the transcripts arrived); authorised `ebe46ce` (merge-gate-only fix — right six lines, wrong file); requested and received from this agent (OpenCode, GLM-5.3-Flash Free) a **scratch-clone patch** that fixes the *harness* oracle path with two regression tests, plus the corrected class-K analysis that allowed the `ResumeUnsupported` claim to be retracted. All Claude-suggested remediations so far are captured in §10. Claude's structural limitation — **no repo access** — is the reason the remediation is now handed to a stronger LLM that has direct access.

**Verdict:** No code in the live repo has been changed by this report. The fix candidate is verified (§8: 509/0/0/0 full suite in a scratch clone; `check_patch.py` PASS with the reviewer's allow-list) and recommended for landing under operator approval (§10 F1).

---

## 2. Environment and Standing Conventions

| Item | Value |
|---|---|
| Repo root | `C:\temp\projects\testproject1` (per D-01) |
| Worktrees | `<repo>\work\<task>-<fence>` |
| Identity (repo-local) | `umaws-pilot <umaws-pilot@localhost>` via `git var GIT_AUTHOR_IDENT` / `GIT_COMMITTER_IDENT` |
| Identity (global) | `Tiwa Pene <tiwaking@gmail.com>` |
| Policy | `.pm\policy.toml`, pinned by `.pm\pins.sha256`; two files checked, currently `ok: true, 0 mismatches` |
| Dispatch | **Paused** (operator hold); Console stopped |
| Kernel | pmk v0.1.0; `pmk task show` / ledger JSONL under `.pm\events\` |
| Decision log | `pilot/decisions.md`, format `D-<n> \| date \| who \| decision \| alternatives \| what it leaves untested`; ends at **D-61** |
| Incident-report convention | Root-level `incident-report-<topic>-v<NN>.md` with frontmatter `document:` + `provenance: author_llm` |
| Oracle rule | "Oracles Decide" — `gate_cmd` acceptance per `docs/PDD.md`; AGENTS.md forbids editing `.pm/` directly; the Kernel (`pmk`) is the writer |

---

## 3. Incident Timeline (fence-by-fence, evidence-cited)

All timestamps UTC unless marked +13:00 (NZDT = UTC+13).

### 3.1 T-0145 — *Extend `rules_index` to the full 66-file AsciiDoc corpus and regenerate `docs/rules/index.json`*

Current live state: **READY, attempt 2, no lease** (`pmk task show T-0145`). Full ledger extract: `C:\temp\opencode\r8-t0145.txt` (sha256 `a940b9626389af167b910859cbc73ba2f14c08809c9ed7bedfa3dbba2aea734e`), covering ledger seqs 2977–3217 incl. the T-0145/T-0146 admit/claim/failure events.

| Event | Seq / Timestamp | Detail |
|---|---|---|
| admit (attempt 1) | 2977 | T-0145 admitted; worktree `work/T-0145-<fence>` |
| claim (attempt 1) | 2977 block | agent lease taken |
| agent attempt 1 | `.{fence}-0.log` = `122-0.log` | work correct (see §6.1); agent's run reproduced the shadowing trap |
| `FIX_ROUND` | 2 s after agent exit | harness oracle failed — **false alarm**: oracle resolved `cna` from main's tree |
| claim (attempt 2) | 3193 / 3196 | re-lease on a base that already contained the change |
| agent transcripts | `123-0.log`, `123-8.log` | attempt-2 agents report the task **"already passing"** |

**Transcript evidence (attempt 1, `122-0.log`):**

- The agent ran the oracle with `PYTHONPATH="."`; output printed `3 document(s)`.
- It printed `cna.tools.rules_index.__file__`, which pointed into **main's** `src` (e.g. `C:\temp\projects\testproject1\src\...`), proving the installed package **shadowed the worktree**.
- It then fixed a one-line syntax error it had itself introduced, reordered the path to put the worktree's `src` first, re-ran: **69 documents**, and `--check` reported *"up to date"*.
- Conclusion: **the agent's work was correct; the harness judged it with main's old tool.**

**Attempt 2, `123-0.log` / `123-8.log`:** both transcripts confirm the re-lease; the agents found the task "already passing" — consistent with §6.2 (the base already had the change from `e08fa8d`).

### 3.2 T-0146 — *Extend `coverage` tool to account for the full 66-file corpus and regenerate `coverage/rules_coverage.json`*

Current live state: **READY, attempt 1, no lease**; `depends_on: ["T-0139"]` (T-0139 is DONE). Transcript: `.pm\fleet\logs\T-0146\124-0.log`.

| Event | Detail |
|---|---|
| claim (attempt 1) | ledger seqs 3216 / 3217 |
| agent attempt 1 | `124-0.log`: the agent **independently hit the same trap**, noting in its own words *"the installed `cna` package shadows my worktree"* |
| transcript end | log **ends mid-edit** — no finished work, no submission |

Because the harness oracle path is unfixed, `ebe46ce` does **not** prevent T-0146 from failing exactly the way T-0145 failed.

### 3.3 The integration and the merge-gate patch (`e08fa8d`, `ebe46ce`)

| Commit | Date (+13:00) | Author/Committer | Subject |
|---|---|---|---|
| `e08fa8d` | 2026-11-08 12:06:19 | **Tiwa Pene** \<tiwaking@gmail.com\> | *cna: extend rules_index to the 66-file AsciiDoc corpus (T-0145, agent work integrated)* |
| `ebe46ce` | 2026-11-08 12:34:27 | **Tiwa Pene** \<tiwaking@gmail.com\> | *merge: run the gate with the temp worktree on PYTHONPATH (fix worktree import discovery)* |

- `e08fa8d` is the manual integration of the T-0145 agent's work (parent `e31d70a`).
- `ebe46ce` narrowly changes `src\fleet\merge.py`: the gate subprocess now runs with `PYTHONPATH` = `<worktree>\src` joined with `os.pathsep`, the pre-existing `PYTHONPATH` appended, the env dict applied **only** to the gate subprocess. **No test accompanies it.**
- Both commits' content has been diff-verified as benign and hash-equal to the agent's output where applicable; the question is not content but **provenance and scope** (§7.3).

### 3.4 REC-01 / REC-02 and the T-0150 canary (context between the failures)

| Commit | Date (+13:00) | Author/Committer | Subject |
|---|---|---|---|
| `2517be3` | 07:29:39 | umaws-pilot | *docs(pmk): record the REC-02 capture sweep (56/56 trees captured and verified)* |
| `107a342` | 07:45:24 | umaws-pilot | *policy(pmk): enable worktree.reclaim_on_reap (REC-01), ratified as Q-077* |
| `26fd255` | 07:52:44 | umaws-pilot | *fix(pmk): write .pm/pins.sha256 with LF (text eol=lf), and record Q-077 enablement* |
| `e2091fd` | 09:32:36 | umaws-pilot | *feat(T-0150): Canary tiny harmless documentation card … (attempt 2, 15-minute gate budget)* |
| `e31d70a` | 09:34:43 | umaws-pilot | *Merge branch 'pmk/T-0150-121' into HEAD* |
| `9893d94` / `82f6be1` | 07:59 / 08:04 | **Tiwa Pene** | *fleet: advisory RESULT.md check…* / *pmk: test write_pins writes LF… (package H remainder)* |

Suite-count reconciliation (verified): 463 (D-60 baseline) → 494 (commit message on `26fd255`) → 507; the REC work added 31 tests; package H added 13. The full scratch-clone suite after the §8 patch counts **509** (507 + the patch's two new tests) — consistent.

### 3.5 Q-077 window (class-K path)

Ledger window extract: `C:\temp\opencode\r8-q77-window.txt` (sha256 `2ae85b02cbcaae606ebb6d21fe8386cc647d747058d061409c1823dda955f15f`), seqs 3113–3117.

| Seq | Event | Actor | Detail |
|---|---|---|---|
| 3113 | `QUEUE_ITEM` | `worker/deepseek-v4.1-flash` | claims *"Operator instruction 2026-11-08"*; **no diff attached** |
| 3114 | `PINS_CHECKED` | — | clean (18:37:48Z) |
| 3115 | `PINS_CHECKED` | — | **mismatch** — written at 18:38:48Z; `.pm\policy.toml` mtime is exactly `2026-11-08T07:38:48.1042831+13:00` = `18:38:48Z` |
| 3116 | `QUEUE_DECIDED` | `human/tiwa-pene` | payload is only `{"choice":"ratify"}` — **no justification** |
| 3117 | `PINS_CHECKED` | `human/operator` | *"the pins were re-recorded"* — **1 second after** the decision |

Then `107a342` / `26fd255` landed under `umaws-pilot`. The `107a342` commit message says the **operator raised** the item; the ledger says a **worker** raised it.

---

## 4. What the Problem Actually Is (root cause)

### 4.1 The defect

`src\fleet\harness.py::run_command` (lines ~195–207 at base) calls:

```python
proc = subprocess.run(
    command, shell=True, cwd=str(cwd), capture_output=True,
    timeout=timeout, text=True, encoding="utf-8", errors="replace")
```

with **no `env=`**. Every spawned subprocess therefore inherits the harness process's full environment, and Python import resolution is decided by the **host** `PYTHONPATH` / installed packages. On this machine an editable/installed `cna` package points at **main's** `src`, so:

- an **oracle** run inside a worktree imports main's code and judges the worktree with the wrong logic,
- a **worker agent** (see §6.3) imports main's code and even *its own tooling* can disagree with the worktree under test.

This is a class of defect, not a single bug: **any harness-spawned subprocess path that does not pin module resolution to the worktree is exposed.** Two such paths are known: `run_command`/`run_oracles` in `harness.py` (unfixed) and the merge gate in `merge.py` (fixed by `ebe46ce`, untested).

### 4.2 Why the fix round was a false alarm

The FIX_ROUND on T-0145 fired because the *oracle* resolved main's version of `cna.tools.rules_index` (3 documents against a 66-file corpus expectation). The agent's work, verified inside its own worktree, produced 69 documents and a passing `--check`. Harness verdict and agent reality diverged **only** because they ran different code.

### 4.3 Why `ebe46ce` is insufficient

It patches the merge gate only; the harness oracle path remains host-environment-dependent. It also ships no regression test, so nothing prevents future regressions of the gate. A missing quality safeguard: `e08fa8d`'s generated `index.json` carries **413 duplicate-anchor warnings and 15 unresolved xrefs**, which the shipped oracle cannot see because it only asserts `documents >= 66`.

### 4.4 Defunct-claim retraction

Claude's earlier claim that a `ResumeUnsupported` traceback "killed the dispatcher" on T-0145/T-0146 is **retracted**. Proof: the `ResumeUnsupported` search artifact `resume-unsupported-hits.txt` is **empty**, and a ledger sweep found **0 hits**. No file under `.pm` records such a traceback.

---

## 5. What Claude (Web) Did — the Fix Attempts, Chronologically

Claude (Web) is the reviewer in this workflow; it has **no repo access** and works from evidence packets relayed by the operator. Its attempts, in order:

1. **Hypothesis round 1 (later corrected):** on packet evidence alone, it offered a competing explanation for the T-0145 red result — that the agent "hadn't regenerated `index.json` yet". The agent transcripts delivered later **refuted** this; Claude retracted it explicitly and in plain terms once `122-0.log` arrived.
2. **Authorised fix `ebe46ce`:** from the same diagnosis round it directed a merge-gate env fix. The fix is correct for `merge.py` but was (correctly for what was known, insufficiently for what the transcripts later showed) scoped only to the gate; it left the harness oracle path exposed. Claude then re-derived, from `124-0.log`, that T-0146 "will fail the same way", and flagged that `ebe46ce` has no test.
3. **Requested and reviewed the scratch patch (§8):** it specified the exact patch requirements (failing test first; worktree `src` + `tests` first on `PYTHONPATH` via `os.pathsep`; existing `PYTHONPATH` appended; env applied to the subprocess only; preserve BOM/LF), plus a second test that fails without the `ebe46ce` change. The delivered patch initially included such a merge-gate test; it was **removed** in the delivered version to keep the patch scoped to the harness only (see §8 caveat C2), and the gate remains verified **by inspection only**.
4. **Corrected the class-K picture:** its first reading of Q-077 changed after the ledger window arrived; it produced the Q-075-vs-Q-077 contrast (§7), posited the `policy.toml` edit window, and asked for the decisive `LastWriteTime` check — which this report's §1.5 confirmed at `18:38:48Z` exactly.
5. **Enforced correction discipline:** it forced the retraction of the `ResumeUnsupported` claim (§4.4) and of several pipeline artifacts from earlier rounds ("private git refs", "39 seconds after", a `pmk context sync` nightly reference, "D3"/"decision QR" — retracted where unverifiable).
6. **Suggested operator remedies** (still pending, restated in §10): void T-0145; re-decide Q-077 from the operator's own shell if its validity cannot be established; record `e08fa8d`/`ebe46ce` in `pilot/decisions.md` (D-62 onward); run the PSReadLine history export to try to settle who edited `policy.toml` and who ran Q-077 key 2.

**Claude's structural limitation:** it cannot read the repo, run the tests, or inspect the live tree; everything it produced is advice. That limitation is the reason for this handoff.

---

## 6. Additional Findings

### 6.1 Oracles are too weak for the corpus they now judge

`e08fa8d`'s `docs\rules\index.json` carries **413 duplicate-anchor warnings and 15 unresolved xrefs**. The shipped oracle checks only `documents >= 66`. Consequence: integration can be "green" while the artifact is objectively degraded. (F4 in §10.)

### 6.2 Re-lease on an already-integrated base wastes attempts

T-0145 attempt 2 ran on a base that already contained the change (`e08fa8d`), so its agents reported "already passing" and burned lease time. There is no pre-lease check comparing a task's change set against the base. (F5 in §10.)

### 6.3 The worker agents are exposed too (design question, unresolved)

`harness.py::_env` returns `None` for direct-CLI profiles (`via_gateway = false`), so **workers inherit the host environment just as oracles do**. Both agents' transcripts show them tripping over the shadowing: `122-0.log` describes the discovery process; `124-0.log` states *"the installed `cna` package shadows my worktree"*. Claude explicitly asked whether the agent process itself should get the same `PYTHONPATH` discipline. This is an open design question (F3 in §10) — auto-injecting a worktree path into an agent's environment changes what the agent sees of its own installed tooling and needs a deliberate decision, not a drive-by fix.

### 6.4 Quality-of-life: no `tail` / `rm` misuse in evidence rounds

No project defect here; noted only because evidence-gathering rounds repeatedly mistook POSIX idioms for PowerShell. Not actionable for the Kernel.

---

## 7. Class-K Governance Findings

### 7.1 The correct exemplar: Q-075

Raised properly as class K: an agent session (`relay19`) **raised key 1 with the exact diff attached**; a human actor decided **with a full justification**; the pins were re-recorded **2.5 minutes later**; `pmk pins check` then returned `ok: true`. Record: D-61.

### 7.2 The deviation: Q-077

Measured against Q-075, Q-077 fails four checks:

| Check | Q-075 | Q-077 |
|---|---|---|
| Key 1 raised by | agent `relay19` | `worker/deepseek-v4.1-flash` — acceptable in principle, **but no diff attached** |
| Decision payload | full justification | `{"choice":"ratify"}` only |
| Decision actor | `human/operator` | `human/tiwa-pene` |
| Pin re-record | 2.5 min later, same posture | **1 s later, different human identity** (`tiwa-pene` → `operator`) |

Regardless of whether an operator-in-chat instruction did occur (making it a valid but **thinly recorded** two-key action), the record itself is inadequate (D-13 / class-K discipline: the record must let a later reader reconstruct the decision). If validity cannot be established, the remedy is Claude's: **the operator re-decides the item from their own shell**, creating a clean record. This is a pending decision for the operator, restated in §10 F6/F8.

### 7.3 The `policy.toml` edit window

Between the clean `PINS_CHECKED` (18:37:48Z) and the mismatch (18:38:48Z), a **class K file was edited**. The working-file mtime (read 2026-11-08) is exactly `2026-11-08T07:38:48.1042831+13:00` — the mismatch moment — so the edit is dated with precision to the second; the **actor is unknown**. Claude asked the operator to answer plainly whether they made the edit; the operator's PSReadLine history could not settle it (the export covers key-raising commands but the decisive `git -c user.name=…` line pattern was not matched; `Get-PSReadLineOption` history export is listed as an open question). The commit message on `107a342`, which says the *operator raised* the item, is **contradicted by the ledger** (a worker raised it).

### 7.4 The identity anomaly (`e08fa8d`, `ebe46ce`)

Both commits carry author **and** committer `Tiwa Pene <tiwaking@gmail.com>` — the *global* identity — while the repo-local identity is `umaws-pilot <umaws-pilot@localhost>` (verified via `git var` inside the repo), under which every neighbouring commit was made. The most plausible explanation is that **an agent invoked git with an explicit human identity override** (or ran from a clone configured as the human), which is a 7.1-discipline violation for agent-authored commits. It is **not** explained by any documented synchronisation path. Investigation item (F9 in §10); the actor behind the identity is not asserted here, only the identity mismatch itself.

### 7.5 The decisions.md backlog

`pilot/decisions.md` ends at **D-61** (verified; the working copy has no later entries). The following events of this incident window therefore have **no decision record**:

- Q-076 and Q-077 (both decided; only Q-075's decision is recorded, as D-61)
- REC-01 and REC-02 (implemented and landed, `866a166`…`2517be3`, `107a342`)
- The T-0150 supervised canary (`e2091fd`, merged `e31d70a`)
- `e08fa8d` (manual integration of T-0145's agent work)
- `ebe46ce` (merge-gate fix)

Per the project's own governance, integrations and class-K ratifications require co-located decision records. Gap to be closed by **drafting** D-62+ (operator-ratified), not by retroactive silent edits (F7 in §10).

---

## 8. The Delivered Fix Candidate (scratch clone only — not landed)

**Patch:** `C:\temp\scratch-patch\0001-fleet-isolate-oracle-imports-in-the-worktree-on-PYTH.patch`
**sha256:** `01BB36F8439F4DD552C7F6B12162F804D8204A7354DC23AA6D29FC573F2FCFAA`
**Stat:** 2 files changed, **+63 / −1** (`src\fleet\harness.py` +9/−1 incl. `import os`; `tests\fleet\test_oracle_env.py` +54, new file)
**Scratch commit:** `d884338` "fleet: isolate oracle imports in the worktree on PYTHONPATH" (scratch clone; scratch-local identity `OpenCode Reviewer`)

### 8.1 Behaviour of the fix

`run_command` (used by the oracle path) now, at the moment of the subprocess spawn only:

```python
env = os.environ.copy()
src_path   = str(Path(cwd) / "src")
tests_path = str(Path(cwd) / "tests")
env["PYTHONPATH"] = os.pathsep.join(
    [src_path, tests_path, env.get("PYTHONPATH", "")]).strip(os.pathsep)
proc = subprocess.run(..., env=env)
```

BOM and LF handling of the source file preserved; no other behaviour touched; the worker spawn path (`_env`) is untouched.

### 8.2 Tests delivered

`tests\fleet\test_oracle_env.py`:

1. `test_oracle_env_isolates_worktree_pythonpath` — a host `pkg` that prints `HOST_TOKEN` vs a worktree `pkg` printing `WORKTREE_TOKEN`; an oracle run against the worktree must resolve the worktree module. **Fails on the unpatched harness** (proven in clone `C:\temp\scratch-clean`, which reproduced both failures).
2. `test_oracle_env_appends_existing_pythonpath` — the pre-existing host `PYTHONPATH` must still be present *after* the worktree entries (no information loss for genuinely external packages).

### 8.3 Verification results

| Check | Result |
|---|---|
| Failing-first proof (unpatched clone `C:\temp\scratch-clean`) | both isolation tests fail on base `e31d70a` |
| `check_patch.py` (allow-list `src/fleet/harness.py`, `tests/fleet/test_oracle_env.py`) | `PASS … RESULT: ALL PASS` |
| Full suite in patched clone `C:\temp\scratch-r10` | **509 passed, 0 failures, 0 errors** in 194.77 s (`C:\temp\opencode\junit-r10.xml`, sha256 `2E750DF4F80D85E24E856E45177F932CE3C8B88C9F583C3719C98BF7E95FD205`) |
| Live repo | **untouched** (patch and tests exist only in scratch) |

### 8.4 Caveats to carry into remediation

- **C1 (scope):** the patch fixes only the harness oracle path. It deliberately does **not** touch the worker env (`_env`), merging Claude's open question of §6.3 into a separate decision.
- **C2 (merge-gate test):** the version delivered contains **no** `ebe46ce` coverage test; an earlier draft had a source-inspection test asserting `os.pathsep` usage in `merge.py`, which was removed as brittle. The merge gate remains **verified by inspection only**. §10 F2 asks for a behavioural (not textual) gate test.
- **C3 (real-dispatch):** the patch was verified in scratch clones, never against a live dispatch; the supervised end-to-end run remains gated on operator approval.
- **C4 (both agents also tripped):** patching the oracle alone does not prevent the *worker-agent* trap; expect worker-side friction to persist until F3 is decided.

---

## 9. Open Questions (dedicated section — for the stronger LLM and the operator)

Each item lists the evidence source that can settle it.

| # | Question | How to settle |
|---|---|---|
| OQ-1 | Who edited `.pm\policy.toml` at `2026-11-07T18:38:48Z`? | Export PSReadLine history (`(Get-PSReadLineOption).HistorySavePath` → `Select-String 'policy|pins|Q-07'`); compare with `QUEUE_*` actor fields; operator's plain answer also suffices |
| OQ-2 | Who recorded the Q-077 key-2 decision (`human/tiwa-pene` in the payload vs `human/operator` in 3117)? | Read full JSON of seqs 3116/3117 from `.pm\events\2026-11-07.jsonl` (working copy is **modified**, see OQ-5 — capture both committed and working bytes) |
| OQ-3 | Does Q-077 stand, or must it be re-decided by the operator from their own shell? | Operator decision after OQ-1/OQ-2 (Claude's suggested remedy stands) |
| OQ-4 | Which shell/session performed the `e08fa8d`/`ebe46ce` commits under the human identity? | Diff `.pm` logs around 12:06–12:35 +13:00 on 2026-11-08; interrogate session managers; PSReadLine history |
| OQ-5 | The live working tree carries **~130 lines of drift** (modified: `.pm\events\2026-11-07.jsonl`, `.pm\views\*`, `HANDOFF.md`, `agents.toml`, `docs\PDD.md`, `docs\free-models.md`, `pi-test.txt`, `pilot\decisions.md`, `pytest_junit.xml`; untracked incl. `.pm\events\2026-11-08.jsonl`, `.pm\events\2026-10-31.jsonl.bak`, and others). Which of these are legitimate work-in-progress vs accidental? | Ledger replay against commit history; `git diff` per file; classify and record before any landing |
| OQ-6 | Is the T-0150 canary formally accepted? | `/docs/canary.md` criteria vs the actual run artifacts; record the verdict in D-62+ (§7.5) |
| OQ-7 | Should the worker agent process also get worktree-first `PYTHONPATH` (F3)? | Design decision by operator; agent transcripts (`122-0.log`, `124-0.log`) show the friction is real |
| OQ-8 | Which untried tasks (beyond T-0145/T-0146) are exposed to the same oracle-env defect? | Grep `src\fleet\harness.py` for **all** `subprocess.run`/`Popen` call sites lacking `env=`; audit each |

---

## 10. Remediation Plan (for the stronger LLM — repo access assumed)

Fixes are numbered F1…; safeguards S1… in §11. Nothing in this section is authorised to land **without operator approval**; see §12.

### F1 — Land the harness oracle env isolation (the §8 patch)

- Apply `0001-fleet-isolate-oracle-imports-in-the-worktree-on-PYTH.patch` (or re-derive the identical change) on top of live `ebe46ce`.
- Keep the two tests; keep BOM/LF; keep the change scoped to `run_command`/`run_oracles`.
- Verify: `check_patch.py` allow-list result, full suite (expect **509** at minimum going forward), failing-first proof against the unpatched clone.
- Commit identity: **repo-local `umaws-pilot`** (see F9). Do not amend or rebase `ebe46ce`/`e08fa8d`.

### F2 — Add a behavioural merge-gate regression test

- Test `merge.py`'s gate subprocess receives `PYTHONPATH` styled on worktree `src` first, existing host `PYTHONPATH` appended, via real invocation of the merge path (fixture-based fake CLI is fine), not source-text assertions.
- Must fail without `ebe46ce`'s env construction.

### F3 — Decide and (if approved) implement worker-env isolation

- Requires operator sign-off (OQ-7). Options: (a) inject worktree `src` first into the worker's `PYTHONPATH` exactly as for oracles; (b) scrub `PYTHONPATH` for direct-CLI profiles; (c) document the behavioural contract and leave workers as-is with a lint warning. Any of a/b must come with a transcript-based test.

### F4 — Strengthen the `rules_index` oracle

- Replace/augment `documents >= 66` with: duplicate-anchor count == 0; unresolved-xref count == 0; each as hard assertions with explicit failure messages, matching the warnings `e08fa8d`'s index currently exhibits (413 / 15). Consider the same discipline for the coverage tool's oracle before relanding T-0146.

### F5 — Resolve T-0145 and relaunch T-0146

- T-0145: after F1, void or re-dispatch per operator decision (Claude's suggested command: `pmk task void T-0145 --reason "Change integrated manually as e08fa8d; see decision record"` — **check `pmk task void --help` first**, OpenCode has printed two different usage lines for it).
- T-0146: re-dispatch only on a base that includes F1; verify the coverage oracle is inside the isolation patch's scope.

### F6 — Investigate the `policy.toml` editor and Q-077 identity (OQ-1/OQ-2/OQ-4)

- Run the evidence steps of OQ-1/OQ-2/OQ-4 and record the outcome (or `unknown`, plainly) in D-62+.

### F7 — Draft D-62+ records

- Draft (never land directly into `pilot/decisions.md` without operator ratification): decisions covering Q-076, Q-077, REC-01, REC-02, the canary, `e08fa8d`, `ebe46ce` — in the standard `D-<n> | date | who | decision | alternatives | what it leaves untested` format.

### F8 — Operator re-decision of Q-077 (conditional)

- If OQ-3 resolves to "cannot be established", the operator re-decides the item from their own shell (the sanctioned two-key path), and the new record supersedes the thin one.

### F9 — Enforce commit identity discipline

- Add a pre-commit/verify-integrate assertion that committer identity matches the repo-local `umaws-pilot` for pipeline-landed commits; any use of the human identity from agent context raises and records an anomaly. Investigate OQ-4 first to know whether the enforcement should *block*, *annotate*, or merely *log*.

### F10 — Working-tree drift reconciliation (OQ-5)

- Classify the 130 uncommitted lines file by file (legitimate WIP vs accident), record the classification, and either commit, stash or restore each — **no silent checkout/restore** without an operator-visible record.

---

## 11. Safeguards, Recommendations, Improvements

| # | Safeguard | Rationale (this incident) |
|---|---|---|
| S1 | **Env-isolation invariant:** every subprocess the harness spawns (worker, oracle, merge gate, any future path) must pin module resolution to the worktree, with a regression test per path. New `subprocess` call sites fail review without `env=` | `run_command` inherited the host env and judged a worktree with main's code |
| S2 | **Oracles must judge the artifact under test, not a proxy for it**; oracle strength must match artifact complexity (S1 + F4) | `documents >= 66` missed 413 duplicate anchors / 15 unresolved xrefs |
| S3 | **Class-K two-key discipline:** key 1 must carry the exact diff; key 2 must carry a justification payload; a pin re-record must not follow a decision by less than a configurable cool-down without an explicit reason field | Q-077's thin/one-second/different-identity sequence |
| S4 | **Decision-record completeness gate:** a ratification or integration without a co-located `pilot/decisions.md` record is a process failure; add a reconciliation check (test count, queue items, landed commits vs D-entries) to the gate | six events, two commits, one canary, no D-records |
| S5 | **Policy-change detection:** a `PINS_CHECKED` mismatch must trigger stop-and-record (who, when, what), not a silent edit + re-record; `QUEUE_DECIDED` must reference the diff | the 18:38:48Z edit with no actor record |
| S6 | **Commit-identity pinning** (F9) | human identity used on commits plausibly by an agent |
| S7 | **Transcript-based verification:** keep agent logs authoritative; whenever a harness verdict and agent transcript disagree, resolve in favour of neither without reading both | FIX_ROUND false alarm on a correct agent |
| S8 | **Re-lease guard:** before re-attempting a task, verify the base does not already contain the change; "already passing" attempts waste leases | T-0145 attempt 2 |
| S9 | **Suite-count ledger:** test counts must be explained at every integration (463 → 494 → 507 → 509 reconciles; keep the explanatory note) | reconciliation currently relied on commit messages |
| S10 | **Dispatch pause discipline:** keep dispatch paused and Console stopped until F1–F3 are verified and the operator approves the resumption; supervised canary only after | current hold |

---

## 12. Permissions and Hold (what the fixing LLM may and may not do)

**Current hold state (unchanged by this report):**

- dispatch **paused**; Console **stopped**;
- **no** commits, admits, resumes, worktree removals, or queue decisions on the live repo without the operator's explicit go-ahead;
- **no** class K actions (no policy edits, no `pins record`, no queue adds/decides) by the fixing LLM — these remain human keys;
- read-only access to `.pm\` (via `pmk` commands or `git diff`); `pilot/` treated as read-only for drafting purposes (drafts to scratch first, F7).

**What the fixing LLM MAY do with direct repo access:**

- reproduce, verify and extend everything in §§3–8 (run tests, read logs, recompute hashes);
- prepare patches in scratch clones, run full suites, produce junit + `check_patch.py` artifacts;
- write **proposals** and **draft decision records** (F7) as reviewable files for the operator;
- perform the OQ-1/OQ-2/OQ-4 evidence steps and record outcomes (including plain `unknown`s);
- fix code under F1–F4/F9 on the live working tree **only after** the operator approves each fix individually, or in scratch first and then present for landing — which the fix itself must record.

**What it may NOT do without explicit operator instruction:**

- land anything to `main`; amend/rebase `e08fa8d`/`ebe46ce`; touch `.pm\policy.toml` or pins; decide any queue item; void/complete any task other than the operator executing F5 themselves; start the Console or unpause dispatch; delete worktrees or stray event files; commit as `Tiwa Pene`.

---

## Appendix A — Evidence manifest

| Artifact | Path | sha256 / content |
|---|---|---|
| T-0145/T-0146 ledger extract (66 lines) | `C:\temp\opencode\r8-t0145.txt` | `a940b9626389af167b910859cbc73ba2f14c08809c9ed7bedfa3dbba2aea734e` |
| Q-077 window extract (26 lines) | `C:\temp\opencode\r8-q77-window.txt` | `2ae85b02cbcaae606ebb6d21fe8386cc647d747058d061409c1823dda955f15f` |
| Event snapshot | `C:\temp\events-snapshot-20261108-post-canary\` | full JSONL snapshot of the incident window |
| Attempt-1 transcript (T-0145) | `.pm\fleet\logs\T-0145\122-0.log` | quotes transcribed §3.1 |
| Attempt-2 transcripts (T-0145) | `.pm\fleet\logs\T-0145\123-0.log`, `123-8.log` | "already passing" |
| Attempt-1 transcript (T-0146) | `.pm\fleet\logs\T-0146\124-0.log` | "the installed `cna` package shadows my worktree"; ends mid-edit |
| `ResumeUnsupported` sweep | `resume-unsupported-hits.txt` | empty — 0 ledger hits |
| Fix candidate patch | `C:\temp\scratch-patch\0001-fleet-isolate-oracle-imports-in-the-worktree-on-PYTH.patch` | `01BB36F8439F4DD552C7F6B12162F804D8204A7354DC23AA6D29FC573F2FCFAA` |
| Full-suite junit (patched clone) | `C:\temp\opencode\junit-r10.xml` | `2E750DF4F80D85E24E856E45177F932CE3C8B88C9F583C3719C98BF7E95FD205`; 509/0/0/0 |
| Prior review exports | `C:\temp\review-r7\` (commits `9eb39ad..HEAD`); rejected series record in D-59 | reference only |
| `policy.toml` mtime (observed 2026-11-08) | `.pm\policy.toml` | `2026-11-08T07:38:48.1042831+13:00` |
| Pins state (observed 2026-11-08) | `pmk pins check` | `ok: true`, 2 checked, 0 mismatches |
| Repo-local identity | `git var GIT_AUTHOR_IDENT` / `GIT_COMMITTER_IDENT` | `umaws-pilot <umaws-pilot@localhost>` |

*End of report. Author: GLM-5.3-Flash Free (opencode/glm-5.3-flash-free), 2026-11-08.*
