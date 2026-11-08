---
document:
  title: "Repair Proposal: Fleet Environment Isolation, Oracle Integrity, and Governance Records (UMAWS Fleet)"
  status: "PROPOSED — awaiting operator approval. No source file has been changed by this document."
  version: "1.0.0"
  proposal_id: "proposal-umaws-problems-and-issues-repair-v1"
  responds_to: "report-umaws-problems-and-issues-v1.md (GLM-5.3-Flash Free, 2026-11-08)"
provenance:
  author_llm:
    name: "Buffy (Codebuff coding agent)"
    version: "Codebuff, local desktop target"
  created_date: "2026-11-08"
  last_modified_date: "2026-11-08"
  scope: "C:\\temp\\projects\\testproject1 — branch main, HEAD ebe46ce. All baseline numbers in §2 were measured on this machine on 2026-11-08, not copied from the report."
  evidence_base:
    head: "ebe46ce"
    working_tree: "dirty (10 tracked files modified, 121 untracked paths) — classified in §2.5 and P0"
    test_suite: "507 collected, pytest exit 0"
  reviewer: "operator (human)"
  authorisation_state: "None granted yet. Approvals requested in §10; every phase is gated on the approvals it names."
---

# Repair Proposal — UMAWS Fleet Problems and Issues v1

**Answers:** `report-umaws-problems-and-issues-v1.md`
**Repository:** `C:\temp\projects\testproject1` · branch `main` · base `ebe46ce`
**Author:** Buffy (Codebuff) · **Date:** 2026-11-08 · **Status:** **PROPOSED — not executed**
**Execution authority requested:** commits to **local** `main` only; never push, never touch `.pm/policy.toml` or the pins, never decide a queue item, never start dispatch unattended.

---

## 0. How to read this, and what approving it means

This document is a **plan for approval**, not a record of work done. Nothing in the repository has been modified except the creation of this file and the report it answers.

Three things are separated throughout, because conflating them is how the last week was lost:

| Category | Meaning | Where |
|---|---|---|
| **Measured fact** | I ran the command on this machine today and recorded the output | §2, Appendix A |
| **Diagnosis** | An explanation that fits the measured facts and the transcripts | §3 |
| **Plan** | A step I propose to take, with a gate and a rollback | §6 |

Anything I could not verify is flagged `[ASSUMPTION]` inline and collected in §11. Anything that requires a human key is marked **[HUMAN]** and collected in §10.

**Approving this document approves the plan and the specific authorities in §10 — not the individual code changes.** Each code phase still ends at a gate whose result you see before the next phase starts (§0.1).

### 0.1 The approval gates at a glance

| Gate | After | You are shown | You decide |
|---|---|---|---|
| **G-A** | this document | the plan, the risk register, the authority list | approve / amend / reject |
| **G-B** | P0 | drift classification table, quarantine manifest, baseline artifact | proceed to code, or stop |
| **G-C** | P1 | isolation tests red-before/green-after, full suite result, diff stat | proceed to tooling repair |
| **G-D** | P2 | regenerated index/coverage deltas, baseline file, suite result | proceed to governance |
| **G-E** | P3 | identity guard tests, evidence findings, D-62+ drafts | ratify drafts |
| **G-F** | P4 | dry-run dispatch evidence, canary runbook | run the live canary yourself |

---

## 1. Executive summary

### 1.1 The defect in one paragraph

Every subprocess the Fleet spawns inherits the host environment unchanged. On this machine Python resolves `cna` and `pmk` from **main's** `src` through the editable install, so an agent working in `work/T-0145-<fence>` — and the oracle that judges that worktree — imports main's code instead. The agent's work can be correct and still be marked wrong, because the judge and the judged are running different code. The report proved this from transcripts; I re-verified the mechanism in the source and in the interpreter today.

### 1.2 What is genuinely fixed, what is not

| Item | Report's claim | My measurement | Verdict |
|---|---|---|---|
| `harness.py::run_command` has no `env=` | broken | confirmed at `src/fleet/harness.py:189` | **still broken** |
| `merge.py` gate passes worktree `PYTHONPATH` | fixed by `ebe46ce` | confirmed at `src/fleet/merge.py:248-260` | fixed, **no test** |
| Worker agents inherit the host env | exposed | confirmed: `_env()` returns `None` for `worktree_env`-unaware direct-CLI profiles | **still broken** |
| Oracle only asserts `documents >= 66` | weak | confirmed in `tests/fleet/test_oracle_lint.py:16` and the task card | **still weak** |
| `docs/rules/index.json` has 413 duplicate anchors, 15 unresolved xrefs | 413 / 15 | **413 duplicate, 15 unresolved, 428 warnings total** | reproduced exactly |
| The suite is 509 tests after the scratch patch | 509 | **507 collected on live HEAD** (509 = 507 + the 2 patch tests) | reconciled |
| `pilot/decisions.md` ends at D-61 | D-61 | confirmed; file is 731 lines and also **CRLF-drift damaged** | reproduced |

Two findings that are **new in this proposal** and change the plan:

1. **382 of the 413 duplicate-anchor warnings are the generator registering the same anchor twice on the same line** (`line 4 kept, line 4 ignored`). That is a code defect in `_add_anchor`, not corpus damage. Fixing it is a few lines and removes 92% of the noise before any oracle can be trusted.
2. **`coverage/rules_coverage.json` reports `rule_files: 3` for a 66-file corpus, and `docs/rules/index.json` reports `tables: 0` for a wargame rulebook.** Both are structural defects in the tools, not missing work by the agents. T-0146's oracle is failing for the same reason T-0145's did: the tool is wrong, not the tree.

### 1.3 What the repair is

Five phases, each independently verifiable and reversible:

- **P0 — Freeze and baseline.** No code. Classify the 131 dirty paths, quarantine the scratch artifacts (never delete), capture reproducible baseline artifacts, write the checkpoint file.
- **P1 — Environment isolation.** One helper, three call sites, six tests. This is the actual fix for the week-long failure.
- **P2 — Tool integrity.** Fix the duplicate-anchor registration, diagnose and pin the xref baseline, repair the coverage counter, strengthen the G-001 oracle, regenerate artifacts.
- **P3 — Governance and prevention.** Evidence steps for OQ-1/2/4 (OQ-1 is already answered: you made the edit), D-62+ drafts, commit-identity guard, already-satisfied pre-lease check, decision-record reconciliation.
- **P4 — Verification and closure.** Full suite, void T-0145, re-dispatch T-0146 against a real worktree, hand you a live-canary runbook, then the resumption checklist.

### 1.4 What "done" means

Your definition, adopted verbatim: **full suite green + the two blocked oracles satisfiable on main + one supervised real-CLI dispatch that runs claim → worktree → oracles → gate → merge → DONE with the fix in place.** Everything before that is preparation; that run is the proof.

---

## 2. Measured baseline (2026-11-08, this machine)

Every number below was produced by a command in Appendix A. Where the report differs, the measured value is used and the difference is explained.

### 2.1 Repository and process state

| Fact | Measured value |
|---|---|
| Branch / HEAD | `main` / `ebe46ce` |
| Repo-local identity | `umaws-pilot <umaws-pilot@localhost>` |
| Global identity | `Tiwa Pene <tiwaking@gmail.com>` |
| `pmk status` project state | `PAUSED` |
| Active leases | `0` |
| Tasks | 150 total: 138 VOID, 7 DONE, 2 READY, 2 PROPOSED, 1 REWORK |
| Open queue items | `0` |
| Incidents recorded | `102` |
| Event chain | `I1 chain verifies (3219 events)` |
| Pins | `ok: true`, 2 checked, 0 mismatches |
| `pmk` reported worktrees | 15, 162,196,098 bytes |
| `git worktree list` | **27 entries** (26 additional worktrees) — **11 more than `pmk` state believes it owns** |
| `du -sh work` | 170 MB |
| Untracked paths | 121 |
| Test suite | **507 collected, exit 0** |

The worktree discrepancy is a real finding, not a typo: the Kernel's `State` counts 15 worktrees while git knows 26, so eleven directories under `work/` are outside the Kernel's bookkeeping. This is the same class of leak that REC-01/REC-02 were written for, and it is why P0 includes a read-only census before any cleanup. Deleting them is explicitly out of scope (§4.3).

### 2.2 The identity anomaly is broader than the report says

The report names `e08fa8d` and `ebe46ce` as committed under the human identity. The measured log shows **four** such commits in the last six:

```
ebe46ce | Tiwa Pene <tiwaking@gmail.com>       | merge: run the gate with the temp worktree on PYTHONPATH
e08fa8d | Tiwa Pene <tiwaking@gmail.com>       | cna: extend rules_index to the 66-file corpus (T-0145, agent work)
e31d70a | umaws-pilot <umaws-pilot@localhost>  | Merge branch 'pmk/T-0150-121' into HEAD
e2091fd | umaws-pilot <umaws-pilot@localhost>  | feat(T-0150): Canary tiny harmless documentation card
82f6be1 | Tiwa Pene <tiwaking@gmail.com>       | pmk: test write_pins writes LF line endings
9893d94 | Tiwa Pene <tiwaking@gmail.com>       | fleet: advisory RESULT.md check, honest git failures
```

Any identity enforcement must therefore be retro-compatible with commits that were made from a human shell and *are* legitimate. This is why the guard in P3 blocks only the **pipeline** path and merely logs the interactive one (design in §5.8).

### 2.3 The CNA artifacts, measured

`docs/rules/index.json` (69 documents, 66 `.adoc` files on disk):

| Metric | Value |
|---|---|
| `stats.documents` | 69 |
| `stats.sections` | 418 |
| `stats.anchors` | 769 |
| `stats.xrefs` | **15** |
| `stats.resolved_xrefs` | **0** |
| `stats.unresolved_xrefs` | 15 |
| `stats.tables` | **0** |
| `stats.warnings` | 428 |
| duplicate-anchor warnings | 413 |
| — same-line (self-referential) | **382** |
| — cross-document (first wins) | **31** |
| unresolved-xref warnings | 15 |

`coverage/rules_coverage.json`:

| Metric | Value |
|---|---|
| `counts.paths` | 64 |
| `counts.covered` | 64 |
| `counts.uncovered` | 0 |
| `counts.rule_files` | **3** |
| `counts.rule_files_matching` | 3 |
| `uncovered_paths` | `[]` |

T-0146's oracle is:

```
python -m cna.tools.coverage --check && python -c "import json; c=json.load(open('coverage/rules_coverage.json')); assert c['counts']['rule_files'] >= 66, c['counts']"
```

With `rule_files = 3` this can never pass, no matter what the agent writes, unless the tool's definition of a rule file changes. That is a tool defect, and it is the second half of the same story: the harness blamed the workers for what the tools could not see.

### 2.4 The two blocked tasks, measured

| Task | State | Oracle | Why it cannot pass today |
|---|---|---|---|
| `T-0145` | READY, no lease | `rules_index --check` + `documents >= 66` | The change is already in main (`e08fa8d`), so an implement card has nothing to change and fails `NO_CHANGES`. The oracle itself would pass on main. |
| `T-0146` | READY, no lease | `coverage --check` + `rule_files >= 66` | `rule_files` is 3; fails on main and in any worktree. |

So the report's F5 ("void T-0145, relaunch T-0146") is right, but T-0146 cannot be relaunched successfully until P2 changes what `rule_files` counts. That is why P2 precedes P4.

### 2.5 Working-tree drift, measured

```
 .pm/events/2026-11-07.jsonl |   97 +++++
 .pm/views/ledger.md         |    6 +-
 .pm/views/status.md         |    6 +-
 HANDOFF.md                  |  224 ++++---
 agents.toml                 |  325 ++++++++--
 docs/PDD.md                 |   54 +-
 docs/free-models.md         |   37 +-
 pi-test.txt                 |    2 +-
 pilot/decisions.md          | 1451 +++++++++++++++++++---------------------
 pytest_junit.xml            |    2 +-
 10 files changed, 1303 insertions(+), 901 deletions(-)
```

Two things stand out:

- `agents.toml` is a **real operator change**: `max_total_agents` 100 → 10 (with your comment "free models too slow at high concurrency"), a new overseer profile order, and new `pi-orca-*` profiles. That belongs in a commit, after `pmk fleet check`.
- `pilot/decisions.md` shows 1,451 changed lines while its content still ends at D-61. A content diff that large on a file whose entries did not grow is almost certainly **line-ending normalisation (CRLF → LF)**, not authorship. Committing it blindly would rewrite the entire decision log in one unreviewable diff. `[ASSUMPTION]` — P0 verifies with `git diff --ignore-cr-at-eol -- pilot/decisions.md` before deciding.

---

## 3. Root-cause analysis

### 3.1 Primary cause: the environment is never pinned

`src/fleet/harness.py`:

```python
def run_command(command: str, cwd: str | Path, *, timeout: int = 600) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            command, shell=True, cwd=str(cwd), capture_output=True,
            timeout=timeout, text=True, encoding="utf-8", errors="replace")
```

No `env=`. Python therefore resolves imports through the environment that launched the harness: `sys.path` seeded by the editable install, whose `.pth` points at `<repo>/src`. `cwd=` does **not** add the worktree to `sys.path` for `python -m` executions of an installed package — the installed location wins. I confirmed the mechanism directly:

```
import pmk -> C:\temp\projects\testproject1\src\pmk\__init__.py
import cna -> None   (namespace package resolved from the same src)
```

The transcript evidence in the report is consistent with this and needs no reinterpretation: the T-0145 agent's own correct run required putting the worktree's `src` first, and the harness, running the same oracle, saw 3 documents.

`cwd=` *is* enough for `pytest` to pick up `rootdir` and `conftest.py`, which is why the suite runs green in worktrees and hid the problem for so long.

### 3.2 Second instance: the merge gate, fixed but untested

`src/fleet/merge.py:248-260` constructs the gate environment correctly:

```python
gate_env = os.environ.copy()
src_path = str(Path(temp_wt) / "src")
tests_path = str(Path(temp_wt) / "tests")
pythonpath = os.path.pathsep.join([src_path, tests_path, gate_env.get("PYTHONPATH", "")])
gate_env["PYTHONPATH"] = pythonpath.strip(os.path.pathsep)
proc = subprocess.run(gate_cmd, shell=True, cwd=str(temp_wt), ..., env=gate_env)
```

It is the same logic that P1 will factor into one helper — currently duplicated, which is exactly how the harness path got missed. There is no test: remove those five lines and the suite still passes. P1 adds a behavioural test through `integrate()`.

### 3.3 Third instance: the workers themselves

`Harness._env`:

```python
if not profile.via_gateway:
    return None
```

For every direct-CLI profile — which is every `pi`, `kilo`, `opencode` and `hermes` profile on this machine — the agent process inherits the full host environment, including the editable-install `PYTHONPATH`. Both failing agents documented the trap in their own transcripts. Patching only the oracle leaves the worker importing main's code while editing the worktree, which produces a class of confusion no oracle can catch.

You chose (interview Q4): **inject worktree `src`/`tests` first for all profiles**, while preserving everything else the profile currently sees. For gateway profiles this composes with the existing scrub: scrub first, then prepend the worktree entries. That keeps credentials out of gateway-routed processes and keeps direct-CLI credentials intact.

### 3.4 Why the false alarm happened, mechanically

1. Harness spawns oracle with host env.
2. Oracle runs `python -m cna.tools.rules_index --check` inside the worktree.
3. Installed `cna` resolves to **main's** `src`; `--check` compares main's committed index against a worktree whose corpus main does not yet index.
4. `--check` exits 1; `FIX_ROUND` fires 2 seconds after the agent exits.
5. The agent is asked to fix work that was already correct; it re-runs, sees "already passing", and the attempt is burned.

The verdict and the reality differed **only** in module resolution. Nothing about the agent's output was wrong.

### 3.5 The generator defect behind 413 warnings

`src/cna/tools/rules_index.py::_add_anchor`:

```python
for existing in document["anchors"]:
    if existing["id"].lower() == id.lower():
        warnings.append(
            f"duplicate anchor '{id}' in {document['path']} "
            f"(line {existing['line']} kept, line {line} ignored)")
        return
document["anchors"].append(anchor)
```

The warning text interpolates **two different lines**. 382 of the 413 warnings read `line N kept, line N ignored` — the same anchor id presented twice at the same line. That is the same anchor being registered twice by two scanners (an explicit `[[anchor]]` and a heading-derived anchor on the same source line), not a genuine collision. The function's job is to prevent duplicates; the duplicate is created by the double call, and the warning is the only visible symptom.

Separately, 31 warnings are genuinely cross-document, and they are **legitimate**: `initiative` appears in section-07 and section-61; `general-description` in section-60 and section-61; `supply-expenditures` in section-32 and section-47. A book with repeating headings has repeating anchors. "First wins" is the correct policy; the warning is informational. Treating these as defects would force corpus edits that fight the source material.

### 3.6 The xref and table results are probably a second tool defect

`stats.xrefs = 15` and `stats.resolved_xrefs = 0` in a corpus with 769 anchors. Fifteen xrefs total across 66 AsciiDoc files is implausible; all fifteen failing to resolve, while every target is of the form `case-N.M`, suggests the resolver is comparing `case-15.8` against anchor ids that do not carry the `case-` prefix, rather than fifteen genuine holes in the corpus. Likewise `stats.tables = 0` in a wargame rulebook containing CRT and supply tables.

`[ASSUMPTION]` — P2 step 2 diagnoses both before writing any baseline. The plan handles either outcome:
- if resolution is a bug, fix `_key_candidates`/`_resolve_xref` and the baseline shrinks to the genuine gaps;
- if they are genuine gaps, pin the exact 15 in `docs/rules/index.baseline.json` and assert set equality, so any change forces review.

Do not let an oracle assert "zero unresolved xrefs" before this is settled: it would either fail forever or be quietly weakened.

### 3.7 Re-lease waste is unguarded

T-0145 attempt 2 ran on a base that already contained the change. Nothing in `Harness.start` asks "do this task's oracles already pass on main?" before `kernel.claim`. The cheapest honest guard is to run the task's oracles in a throwaway worktree of main and, if they all pass, emit `PRECHECK_SATISFIED` and refuse the lease (S8). That is not a heuristic; it is the same command the harness would run, just earlier.

### 3.8 Governance records

- `pilot/decisions.md` ends at D-61; six events in the incident window have no record (Q-076, Q-077, REC-01, REC-02, the T-0150 canary, `e08fa8d`/`ebe46ce`).
- Q-077's record is thin (no diff on key 1, `{"choice":"ratify"}` on key 2, pin re-record one second later under a different human identity).
- **OQ-1 is now answered by you:** you made the `policy.toml` edit at 2026-11-07T18:38:48Z. That resolves the "unknown actor" question. It does **not** by itself make Q-077 well-recorded, but it downgrades it from "possible unauthorised edit" to "thinly recorded authorised action". P3 records exactly that.
- `.pm/policy.toml` currently has `worktree.reclaim_on_reap = true` and pins are clean.

None of this is a code defect. It is a **record defect**, and it is why the same incident took a week: each round re-litigated facts that were never written down in the place a later reader would look.

---

## 4. Goals, non-goals, success criteria

### 4.1 Goal

Make the Fleet's judgement of work match the work, in every path that judges it, and leave behind tests and records that keep it that way.

### 4.2 Success criteria (binary, all must hold)

| # | Criterion | Proof |
|---|---|---|
| **SC-1** | Every harness-spawned process that executes Python resolves imports from the worktree under test first | 6 tests in `tests/fleet/test_worktree_env.py`; the oracle and worker tests fail on `ebe46ce` and pass after P1 |
| **SC-2** | The merge gate's environment is behaviourally covered | `test_merge_gate_resolves_worktree_module` through `integrate()`, not a source-text assertion |
| **SC-3** | The full suite is green and larger than the 507-test baseline | `pytest -q` exit 0; count recorded and explained per phase |
| **SC-4** | T-0145 is voided with a reason and a decision reference; T-0146's oracle passes on main | `pmk task show` output + oracle exit 0 |
| **SC-5** | The rules index has zero same-line duplicate warnings, an exact pinned cross-document allowlist, and an exact pinned xref baseline | `tests/test_rules_baseline.py` |
| **SC-6** | The coverage tool accounts for all 66 corpus files and its `--check` is clean | regenerated `coverage/rules_coverage.json`, oracle exit 0 |
| **SC-7** | One real-CLI dispatch reaches DONE end-to-end with the fix in place, on the operator's run | evidence bundle in `.pm/evidence/`, green gate, `DONE` state, transcript |
| **SC-8** | Pipeline commits are authored `umaws-pilot`; a foreign identity is recorded as an anomaly | `test_identity_guard.py` (unit) + the canary's merge commit |
| **SC-9** | The working tree is reconciled: legitimate work committed, artifacts quarantined, nothing deleted | classification table + clean `git status` except `quarantine/` |
| **SC-10** | D-62+ drafts exist and a reconciliation report lists remaining unrecorded integrations | `pilot/drafts/decisions-d62-plus.md`, `tools/decision_reconcile.py` output |

### 4.3 Non-goals (explicitly not in this plan)

1. **No CNA game feature work.** No opponent AI, no engine rules, no G-002. The corpus and tools are repaired because they are the workload that exposed the Fleet defect, not because the game is in scope.
2. **No `.pm/policy.toml` or pins edit.** If a policy change proves necessary (e.g. gate command), it is proposed as a class-K item and decided by you — not executed here.
3. **No Q-077 re-decision.** OQ-3 remains yours. P3 records evidence and drafts; it does not decide.
4. **No queue decisions, no task completion other than the T-0145 void you authorise, no admits.**
5. **No worktree deletion and no event-file deletion**, even the eleven orphaned directories and the `.bak` file. Census and report only.
6. **No remote push.**
7. **No 100-agent concurrency work**, no Console feature work, no Overseer redesign.
8. **No rewriting history**: no amend or rebase of `e08fa8d` or `ebe46ce`. Their provenance is recorded, not erased.

---

## 5. Design

### 5.1 One environment contract, one implementation

New module `src/fleet/runenv.py`:

```python
"""Pin a subprocess's Python resolution to the worktree it is judging.

The Fleet runs oracles, gates and workers all inside a worktree.  On this
machine the editable install puts <repo>/src on sys.path, which shadows the
worktree.  Every spawn must therefore prepend the worktree's src and tests.
"""
from __future__ import annotations

import os
from pathlib import Path

WORKTREE_PATH_ENTRIES = ("src", "tests")


def worktree_env(worktree: str | Path,
                 *, base: dict[str, str] | None = None,
                 drop_pythonpath: bool = False) -> dict[str, str]:
    env = dict(os.environ if base is None else base)
    prior = "" if drop_pythonpath else env.get("PYTHONPATH", "")
    entries = [str(Path(worktree) / name) for name in WORKTREE_PATH_ENTRIES]
    if prior:
        entries.append(prior)
    env["PYTHONPATH"] = os.pathsep.join(entries)
    env["PYTHONIOENCODING"] = "utf-8"
    return env
```

Properties, each of which becomes a test:

1. worktree `src` is **first**, worktree `tests` second;
2. any pre-existing `PYTHONPATH` is retained **after** them, so genuinely external packages still import;
3. the caller's own environment is not mutated (a copy is returned);
4. with `base=` a scrubbed environment, the worktree entries are added **after** scrubbing, so credentials stay scrubbed;
5. `os.pathsep` is used, so the same code is correct on Windows and POSIX;
6. no `sys.path` hacks, no `sitecustomize`, no `.pth` edits — the fix travels with the spawn, not with the machine.

### 5.2 Call sites

| Site | Change |
|---|---|
| `harness.run_command` (oracle) | pass `env=worktree_env(cwd)` |
| `harness.run_oracles` | unchanged (inherits from `run_command`); add a docstring line stating the contract |
| `merge.integrate` (gate) | replace the inline construction with `worktree_env(temp_wt, base=os.environ)` |
| `Harness._env` (worker, both start and fix round) | signature becomes `_env(profile, worktree)`; direct-CLI: `worktree_env(worktree, base=os.environ.copy())`; gateway: `worktree_env(worktree, base=scrub_environment(keep=...))` |
| `Harness._fix_round` | pass `run.worktree` to `_env` |

`_env` is called in exactly two places (`harness.py` start and `_fix_round`); the signature change is mechanical and type-checked by the tests.

### 5.3 What the fix deliberately does *not* do

- It does not remove main's `src` from `sys.path`; it only puts the worktree in front. Removing it would break tools that legitimately import the installed package.
- It does not `chdir` differently, set `PYTHONHOME`, disable site-packages, or set `PYTHONNOUSERSITE`. Those break agent CLIs and their own tooling.
- It does not touch the eleven orphaned worktrees or the Kernel's worktree bookkeeping. That is a separate, evidence-first job (P0 census; cleanup later, with your approval).

### 5.4 Test design (the six tests)

All in `tests/fleet/test_worktree_env.py`, using the existing `conftest.py` fixtures (`git_repo`, `make_task`) and `tests/fleet/fakecli.py` as the model for a controlled subprocess.

| Test | Setup | Asserts | Fails on `ebe46ce`? |
|---|---|---|---|
| `test_oracle_resolves_worktree_module` | host dir on `PYTHONPATH` with `probe.py` printing `HOST`; worktree `src/probe.py` printing `WORKTREE`; oracle `python -c "import probe; print(probe.WHERE)"` | stdout hash corresponds to `WORKTREE`; exit 0 | **yes** |
| `test_oracle_keeps_existing_pythonpath_after_worktree` | same, plus a second module only on the host path | both import; worktree wins on the shadowed name | **yes** (second half) |
| `test_merge_gate_resolves_worktree_module` | real `integrate()` with `gate_cmd` writing `probe.WHERE` to a file inside the temp worktree | file contains `WORKTREE`; `gate_exit == 0` | no — covers `ebe46ce`; proven by reverting its five lines in a scratch clone |
| `test_worker_env_resolves_worktree_module` | a `[[profile]]` with a fake adapter script that writes `sys.path[0]` resolution to `.pmwork/probe.txt` | worktree module wins | **yes** |
| `test_worker_env_preserves_direct_cli_environment` | env var `FAKE_TOKEN=abc` in the parent | `FAKE_TOKEN` still visible to a direct-CLI worker | **yes** (currently passes only because env is `None`/inherited — the test pins the contract) |
| `test_worker_env_scrubs_gateway_profile_then_prepends` | `via_gateway = true` profile | a seeded `SECRET_TOKEN` is absent; `PYTHONPATH` begins with the worktree `src` | partially (scrub exists; ordering is new) |

Reds are proven, not asserted: P1 step 2 runs the two oracle tests plus the worker test **before** the fix and records the failure output in the checkpoint. The gate test's red is proven by a scratch clone with `ebe46ce`'s env block removed.

### 5.5 Oracle strengthening without a self-defeating gate

Two layers:

1. **Task-level oracle (T-0146)** stays as the card has it, because the Kernel owns task cards; it passes once `rule_files` counts 66.
2. **Project-level oracle (G-001)** in `docs/PDD.md` is strengthened to assert the artifact contract:

```
python -m cna.tools.rules_index --check
  && python -m cna.tools.coverage --check
  && python -m pytest -q tests/test_rules_baseline.py
```

`tests/test_rules_baseline.py` loads `docs/rules/index.json` and `docs/rules/index.baseline.json` and asserts:

- `stats.documents == 69` (66 corpus files + 3 index artifacts — recorded explicitly so a change is a decision);
- same-line duplicate-anchor warnings `== 0`;
- the **set** of cross-document duplicate anchor ids equals the baseline set exactly (not a count: a rename must force review);
- the **set** of `(target, document, line)` unresolved xrefs equals the baseline set exactly;
- `stats.tables` equals the baseline value after the table diagnosis (either a real count or a documented zero with the reason in the baseline file's `note`).

Set equality is deliberate: adding a warning fails, and removing one also fails until the baseline is updated in the same commit — the pair is the record.

### 5.6 Generator repair

Two changes in `src/cna/tools/rules_index.py`:

1. `_add_anchor`: if an existing anchor has the same `id` (casefold) **and the same line**, return silently — it is the same anchor seen twice. Warn only when the line differs (a genuine second definition).
2. Find and remove the double registration at the call site(s) that index the same line twice, so the silent path is not load-bearing. A test asserts one anchor per line for a fixture containing both an explicit anchor and a heading on the same line.

Expected delta after regeneration: warnings 428 → 46 (0 same-line + 31 cross-document allowlisted + 15 xrefs), `stats.warnings` drops correspondingly. The 31 stay, deliberately, and are pinned.

Second repair, after diagnosis: `_index_tables` and `_resolve_xref`. Handle each on evidence. If the table scanner is wrong, fix it and record the new count; if the corpus genuinely has no pipe tables, record that in the baseline note rather than pretending.

### 5.7 Coverage counter repair

The measured `rule_files: 3` against 66 on disk means the counter is counting something else — most likely only files that declare a `paths:` frontmatter block. The fix separates the two facts that were conflated:

```json
"counts": {
  "rule_files": 66,
  "rule_files_declaring_paths": <n>,
  "rule_files_matching": <n>,
  "paths": 64, "covered": 64, "uncovered": 0
}
```

`rule_files` becomes "corpus files present" (the thing T-0146's oracle asks about), while declaration coverage stays visible and honest. `--check` output is regenerated in the same commit so the drift check stays red-free. A fixture-based test creates 66 tiny `.adoc` files, 3 with `paths:` blocks, and asserts `66 / 3 / 3`.

### 5.8 Commit-identity guard (blocking pipeline, logging interactive)

Two layers, because the four anomalous commits include both pipeline and interactive origins:

1. **Pipeline (blocking).** `merge.commit_worktree` already runs in agent context. It passes an explicit identity:

```python
["git", "-c", "user.name=umaws-pilot", "-c", "user.email=umaws-pilot@localhost", "commit", ...]
```

and, before committing, compares the effective identity with the expected one; on mismatch it records `IDENTITY_ANOMALY` and refuses the commit. This cannot block a human working in a shell, because it only covers the pipeline's own commit path.

2. **Interactive (logging).** `.githooks/pre-commit` warns and appends to `.pm/fleet/identity-warnings.log` when `GIT_AUTHOR_IDENT` names the human identity **and** the process tree looks agent-driven (`UMAWS_PIPELINE=1` in the environment). It exits 0 for ordinary human commits, so your own work is never blocked. Enabled with repo-local `git config core.hooksPath .githooks` — reversible with one command.

The rule the guard encodes: *the identity is a property of who is acting, not of whose machine it is.*

### 5.9 Already-satisfied pre-lease guard (S8)

New `src/fleet/precheck.py`:

```python
def oracles_already_pass(kernel, task, *, timeout: int = 600) -> tuple[bool, list[dict]]:
    """Run the task's oracles on main HEAD in a throwaway worktree."""
```

`Harness.start`, before `kernel.claim`:

- only when `agents.toml [fleet] precheck_satisfied = true` (agents.toml is **not** pinned — `pmk pins check` covers 2 files, constitution and policy — so this is a fleet-config key, not a class-K change);
- if every oracle passes: record `PRECHECK_SATISFIED` with the oracle outputs, return `blocked` with a message naming the likely integration, and do **not** claim. No attempt is burned, no worktree is created.
- if any oracle fails: proceed normally. A precheck that cannot run (git error, timeout) is advisory and never blocks.

This is what would have saved T-0145 attempt 2, and it will save the next re-lease.

### 5.10 Decision-record reconciliation (S4)

`tools/decision_reconcile.py` (read-only) emits a table of:

- tasks in `DONE` whose integration commit has no `D-<n>` reference in `pilot/decisions.md`;
- `QUEUE_DECIDED` events with no matching D-record (matched by queue id string);
- commits touching `.pm/policy.toml` or `pilot/decisions.md` with no adjacent D-record.

It never edits. Output goes to `docs/reports/decision-gaps-<date>.md`, and the P3 gate is "the report exists and every row is either recorded or explicitly deferred in D-62+". A unit test covers the parser and the matcher, not the live repository.

### 5.11 Subprocess audit (S1)

All call sites found by `code_search`, with the disposition each will get in P1:

| File:line | What it runs | Disposition |
|---|---|---|
| `src/fleet/harness.py:189` | oracle command in worktree | **fix** (P1) |
| `src/fleet/merge.py:255` | gate in temp worktree | **fix** (refactor to helper) |
| `src/fleet/spawn.py:320` | worker CLI | already `env=`; caller now supplies the pinned env |
| `src/fleet/project.py:213` | project lifecycle command (`shell=True`) | **audit**; fix if it can execute in a worktree |
| `src/pmk/api.py:1121` | argv in worktree | **audit**; likely an oracle-adjacent path — fix if so |
| `src/pmk/oracle_lint.py:70` | docstring example with literal `...` | allowlist (not executable) — verify |
| `src/pmk/context.py:472` | Caliber score, `cwd=root` | allowlist: repo root is intended, not a worktree |
| `src/pmk/store.py:214,235` | git plumbing | allowlist |
| `src/pmk/plat.py:412,448` | process spawn / OS query | allowlist |
| `src/fleet/legacy.py:245` | legacy launcher | allowlist (unused path) |

`tools/check_subprocess_env.py` enforces the invariant: every `subprocess.run/Popen/check_output/call` under `src/` must pass `env=` or appear in `tools/subprocess_env_allowlist.txt` with a one-line reason. `tests/test_subprocess_env_lint.py` runs it, so a new unguarded spawn fails the suite rather than costing another week. The allowlist is small, reviewed, and its entries state *why* inheritance is correct there.

---

## 6. Phase plan

Each phase: objective → steps → expected output → gate → rollback → checkpoint. Phases are ordered by dependency, not importance. A phase may be **stopped** at its gate and resumed later from the checkpoint file (Appendix D).

Estimates are working time on this machine, not elapsed calendar time.

### P0 — Freeze, baseline, and tree reconciliation

**Objective:** make the starting point reproducible and stop the drift from contaminating later diffs.
**Estimated effort:** 45–60 minutes. **Code changes:** none.

#### P0.1 Freeze declaration
- Confirm dispatch is paused and the Console is stopped (`pmk status` → `project_state: PAUSED`; `pmk fleet status`).
- Record in the checkpoint: `[HOLD] no policy/pins/queue/task writes; no push; no deletions`.
- Do not stop anything that is running: 0 active leases measured.

#### P0.2 Baseline artifacts
```bash
mkdir -p .pmwork/repair-v1
./.venv/Scripts/python.exe -m pytest -q > .pmwork/repair-v1/pytest-baseline.txt 2>&1; echo $?
./.venv/Scripts/pmk.exe status          > .pmwork/repair-v1/pmk-status.json
./.venv/Scripts/pmk.exe fleet status    > .pmwork/repair-v1/fleet-status.json
./.venv/Scripts/pmk.exe pins check      > .pmwork/repair-v1/pins.json
git status --porcelain=v1               > .pmwork/repair-v1/git-status.txt
git worktree list --porcelain           > .pmwork/repair-v1/worktrees.txt
git log --format='%h|%an <%ae>|%cn <%ce>|%s' -40 > .pmwork/repair-v1/authors.txt
```
`.pmwork/` is already excluded from harness change detection (`_worktree_changes` skips it), so these artifacts do not pollute scope checks.

#### P0.3 Drift classification
Produce `pilot/repair-drift-classification-v1.md` with one row per path:

| Path | Diff | Class | Action |
|---|---|---|---|
| `.pm/events/2026-11-07.jsonl` | +97 | Kernel ledger, real | commit **after** `pmk views` + `pmk sentinel` |
| `.pm/views/ledger.md`, `status.md` | ±6 | projection | regenerate, then commit with the ledger |
| `HANDOFF.md` | 224 | session memory, real | commit |
| `agents.toml` | 325 | operator config, real | `pmk fleet check`, then commit |
| `docs/PDD.md` | 54 | re-scoped PDD, real | commit with D-record draft |
| `docs/free-models.md` | 37 | reference, real | commit |
| `pilot/decisions.md` | 1451 | **suspect line-ending churn** | `git diff --ignore-cr-at-eol`; if empty → restore committed bytes, do **not** commit |
| `pi-test.txt` | 2 | scratch | quarantine |
| `pytest_junit.xml` | 2 | generated | restore to committed bytes |
| 121 untracked | — | mixed | triage below |

Untracked triage, as one reviewed pass:
- **Keep and commit:** this proposal, `report-umaws-problems-and-issues-v1.md`, the assessments that D-records cite.
- **Quarantine (move, never delete):** the 13 `*.patch` files, `check_*.py`, `fix_*.py`, `renumber*.py`, `collect*.txt`, `pytest_*.txt`, `cc_out.txt`, `cc_err.txt`, `agents-bak.toml`, `.pm/events/2026-10-31.jsonl.bak` → `quarantine/2026-11-08/` preserving relative paths, with a manifest listing every moved file and its original path.
- **Leave alone:** `.pm/events/2026-11-08.jsonl` (live ledger, Kernel-owned).

Add `quarantine/` to `.gitignore` in the same commit so the move is visible but the directory is not tracked.

#### P0.4 Worktree census (read-only)
Compare `pmk status` (15) with `git worktree list` (27). Write `pilot/repair-worktree-census-v1.md`: task id, fence, path, size, whether the Kernel knows it, whether its branch is merged, whether it contains unmerged commits. **No removals.** This gives you the evidence to decide REC-01 cleanup later, and it explains the 170 MB.

#### P0.5 Checkpoint
Create `pilot/repair-checkpoint.md` (template in Appendix D) with P0 marked complete, the measured numbers, and the next action.

**Gate G-B:** you review the classification table and the quarantine manifest before anything is moved or committed. Rollback: nothing has changed yet.

---

### P1 — Environment isolation (the actual fix)

**Objective:** no harness-spawned process can judge a worktree with main's code.
**Estimated effort:** 2–3 hours. **Code changes:** 1 new module, 3 files touched, 1 new test file.

#### P1.1 Add the helper
Create `src/fleet/runenv.py` exactly as §5.1. No behaviour change yet, so the suite stays 507/0.

#### P1.2 Write the tests first, and prove they are red
Create `tests/fleet/test_worktree_env.py` with the six tests of §5.4, then:
```bash
./.venv/Scripts/python.exe -m pytest -q tests/fleet/test_worktree_env.py
```
Expected **before** the fix:
```
3 failed, 2 passed, 1 error-or-pass   # exact set recorded in the checkpoint
  FAILED test_oracle_resolves_worktree_module
  FAILED test_oracle_keeps_existing_pythonpath_after_worktree
  FAILED test_worker_env_resolves_worktree_module
```
If a test expected red comes back green, stop and re-read it: a green "red" test is not evidence.

Store the red output at `.pmwork/repair-v1/p1-red.txt`.

#### P1.3 Fix the oracle path
`harness.run_command` gains `env=runenv.worktree_env(cwd)`. `run_oracles` gets a one-line contract comment.

#### P1.4 Fix the gate path (refactor, no behaviour change)
`merge.integrate` replaces its inline construction with `runenv.worktree_env(temp_wt, base=os.environ)`. The existing `test_reintegration_gate.py` must stay green; the new gate test becomes its behavioural cover.

#### P1.5 Fix the worker path
`Harness._env(profile, worktree)`:
```python
def _env(self, profile: Profile, worktree: str | Path) -> dict:
    if profile.via_gateway:
        from pmk.plat import scrub_environment
        base = scrub_environment(keep=[...])          # unchanged list
    else:
        base = os.environ.copy()
    return runenv.worktree_env(worktree, base=base)
```
Update both call sites (`start`, `_fix_round`). Record the design consequence in the checkpoint: an agent that previously inherited the host `PYTHONPATH` now sees the worktree first, which is the intended contract and is what the transcripts show the agents doing manually.

#### P1.6 Audit the remaining call sites
Run the audit of §5.11. For `project.py:213` and `pmk/api.py:1121`, either fix with the helper or add an allowlist entry with a reason and a test that the allowlist entry is still needed. Add `tools/check_subprocess_env.py`, its allowlist file, and `tests/test_subprocess_env_lint.py`.

#### P1.7 Full suite and diff review
```bash
./.venv/Scripts/python.exe -m pytest -q > .pmwork/repair-v1/p1-green.txt 2>&1; echo $?
git diff --stat
```
Expected: exit 0; **507 + 6 + 1 = 514** tests, 0 failures. (If the lint test adds more, record the count and why — SC-3 requires the explanation, not a bare number.)

Commit as **one** commit, identity `umaws-pilot`:
```
fleet: pin every spawned process to the worktree under test

The harness ran oracles with the host environment, so on this machine the
editable install's <repo>/src shadowed the worktree and a correct agent was
judged by main's code (T-0145, T-0146).  One helper now builds the env for the
oracle, the merge gate and the worker; the gate's inline copy is removed.

Refs: report-umaws-problems-and-issues-v1 §4.1, §6.3; D-62 (draft)
```

**Gate G-C:** red-then-green output and the full-suite result shown to you. Rollback: `git revert <sha>` — one commit, no data migration.

---

### P2 — Tool integrity: index, xrefs, coverage, oracle

**Objective:** make the tools' output tell the truth about the 66-file corpus, and make the oracle strong enough to notice.
**Estimated effort:** 2–4 hours. **Code changes:** 2 tools, 1 new baseline test, 1 baseline data file, PDD oracle.

#### P2.1 Diagnose before asserting
Run and record:
```bash
./.venv/Scripts/python.exe -c "import json;d=json.load(open('docs/rules/index.json'));print(d['stats'])"
./.venv/Scripts/python.exe -m cna.tools.rules_index --rules docs/rules --out /tmp/idx.json
```
Then, for the xref and table questions specifically, inspect `_key_candidates`, `_resolve_xref`, `_index_tables`, and hand-check three concrete cases (`case-15.8` at section-15:436; a document known to contain a pipe table). Write the finding in `pilot/repair-findings-index-v1.md` — one of:
- **(a) resolver/scanner bug** → fix, add unit test, regenerate;
- **(b) genuine corpus gap** → keep the value, pin it;
- **(c) corpus has no pipe tables** → record the reason in the baseline `note`, do not invent a scanner.

No baseline file is written until this is recorded.

#### P2.2 Fix duplicate-anchor registration
Implement §5.6. Add unit tests:
- `test_same_line_registration_does_not_warn` (fixture with an explicit anchor and a heading on one line);
- `test_distinct_line_duplicate_still_warns` (two real definitions on different lines).

#### P2.3 Fix the coverage counter
Implement §5.7. Add fixture test `test_rule_file_count_includes_every_corpus_file` (66 files, 3 declaring paths → `66/3/3`). Regenerate `coverage/rules_coverage.json` in the same commit.

#### P2.4 Regenerate and pin the baseline
```bash
./.venv/Scripts/python.exe -m cna.tools.rules_index
./.venv/Scripts/python.exe -m cna.tools.coverage
```
Write `docs/rules/index.baseline.json` with the exact sets (§5.5) and a `note` recording (i) why 31 cross-document anchors are accepted, (ii) the xref finding from P2.1, (iii) the table finding. Add `tests/test_rules_baseline.py`.

**Expected deltas, to be confirmed not assumed:**

| Metric | Before | Expected after |
|---|---|---|
| warnings | 428 | 46 (31 cross-doc + 15 xref) ± the xref finding |
| duplicate anchors | 413 | 31 |
| same-line duplicates | 382 | 0 |
| unresolved xrefs | 15 | 15 or fewer, pinned exactly |
| `coverage.counts.rule_files` | 3 | 66 |

If a number differs from this table, the plan is not wrong — the expectation is. Record the actual and update this proposal's delta table in the checkpoint, so the canary evidence and the proposal agree.

#### P2.5 Strengthen the G-001 oracle
Edit `docs/PDD.md` §2 G-001 oracle to the three-command form of §5.5. `docs/PDD.md` is not pinned; the change is recorded in the D-63 draft. Verify:
```bash
./.venv/Scripts/python.exe -m cna.tools.rules_index --check
./.venv/Scripts/python.exe -m cna.tools.coverage --check
./.venv/Scripts/python.exe -m pytest -q tests/test_rules_baseline.py
```
All three exit 0.

#### P2.6 Full suite
Expected: 514 + ~5 = ~519, exit 0. Commit as one commit:
```
cna: stop the indexer double-registering anchors; count the whole corpus

382 of 413 duplicate-anchor warnings were the same anchor registered twice on
the same line.  Coverage reported 3 rule files for a 66-file corpus, so the
T-0146 oracle could never pass.  The index baseline now pins the 31 genuine
cross-document collisions and the unresolved xrefs by set, not by count.

Refs: report §6.1, §4.3; D-63 (draft)
```

**Gate G-D:** before/after artifact deltas and the baseline file shown to you. Rollback: `git revert <sha>`; artifacts regenerate from the tool.

---

### P3 — Governance, identity, and prevention

**Objective:** close the record gap, prevent the two recurrences that cost the week (wrong identity, re-lease of integrated work), and make decision gaps visible.
**Estimated effort:** 2–3 hours. **Code changes:** merge identity guard, precheck module, reconcile tool, hooks.

#### P3.1 Evidence steps (read-only)
- **OQ-1:** answered — you made the `policy.toml` edit at `2026-11-07T18:38:48Z`. Record the plain answer and its consequence (Q-077 is authorised-but-thinly-recorded).
- **OQ-2:** read the full JSON of ledger seqs 3116/3117 from `.pm/events/2026-11-07.jsonl` and record actor, payload, and timestamp verbatim. Do not infer beyond the bytes.
- **OQ-4:** attempt to establish which session made `e08fa8d`/`ebe46ce`; if not establishable, write `unknown` and the steps tried. `unknown` is an acceptable, recorded outcome.
- **OQ-5:** the drift classification from P0 is the answer; link it.
- **OQ-6:** the T-0150 canary verdict — read `/docs/canary.md` criteria against `e2091fd`/`e31d70a` artifacts; record pass/fail/unknown; no decision.
- **OQ-8:** answered by the §5.11 audit; link the allowlist.

#### P3.2 D-62+ drafts
Create `pilot/drafts/decisions-d62-plus.md`. Header in every entry: `DRAFT — not ratified; do not cite as a decision`. Entries, in the standard format:

| Draft | Subject |
|---|---|
| D-62 | Environment isolation: worktree-first `PYTHONPATH` for oracle, gate and worker (the P1 change; alternatives: oracle-only, document-only; leaves untested: real-CLI behaviour until the canary) |
| D-63 | Rules-index baseline and the strengthened G-001 oracle (the 31 accepted collisions, the xref policy, the table finding) |
| D-64 | Coverage semantics: `rule_files` = corpus files present; declarations reported separately |
| D-65 | T-0145 voided (change integrated as `e08fa8d`); T-0146 re-dispatched as the proof |
| D-66 | Q-076/Q-077/REC-01/REC-02 recorded: thin class-K record, operator confirms the `policy.toml` edit, pins clean |
| D-67 | Provenance: four commits under the human identity; identity guard introduced; no history rewrite |
| D-68 | Working-tree reconciliation and quarantine (nothing deleted) |
| D-69 | Canary result and dispatch resumption decision (left blank until the canary runs) |

Drafts are **not** appended to `pilot/decisions.md` in this phase. Ratification is yours (G-E).

#### P3.3 Identity guard
Implement §5.8. Tests:
- `test_pipeline_commit_uses_umaws_pilot_identity` — set global config to the human identity in a fixture repo, run `integrate()`, assert the merge commit's author and committer are `umaws-pilot`.
- `test_foreign_identity_records_an_anomaly` — point the pipeline at a repo configured as the human, assert `IDENTITY_ANOMALY` is recorded and the commit is refused.
- `test_pre_commit_hook_allows_human_commits` — run the hook with no `UMAWS_PIPELINE`; exit 0.

Enable with repo-local `git config core.hooksPath .githooks` (one command; revert with `--unset`).

#### P3.4 Pre-lease guard
Implement §5.9. Add `[fleet] precheck_satisfied = true` to `agents.toml` (fleet config, not pinned) and document it in `README.md`'s command table only if it is user-facing — otherwise leave the README alone. Tests:
- `test_precheck_blocks_release_of_already_satisfied_task` — an oracle that passes on main; assert no `CLAIMED` event, one `PRECHECK_SATISFIED`, `blocked` outcome.
- `test_precheck_allows_a_task_whose_oracle_fails_on_main`.
- `test_precheck_failure_is_advisory` — git error → proceeds to claim.

#### P3.5 Decision reconciliation
Implement §5.10, run it, and attach the output as part of the G-E package. Unit tests for the parser and matcher.

#### P3.6 Full suite and commit
Expected ~526, exit 0. Commit:
```
fleet: guard commit identity and refuse already-satisfied leases

Four commits in this window were authored as the human, and T-0145 attempt 2
re-leased work that main already contained.  The merge path now pins the
pipeline identity and records an anomaly; a pre-lease precheck runs the task's
own oracles on main first.  Decision drafts and a gap report accompany it.

Refs: report §7.4, §6.2, F9, F7; D-66/D-67 (drafts)
```

**Gate G-E:** evidence findings, guard tests, and the D-62+ drafts shown to you. Rollback: `git revert <sha>`; the hook config is one unset away.

---

### P4 — Verification, task closure, and handover to the live canary

**Objective:** prove the repair in the path that failed, close the two tasks, and hand you a runbook you control.
**Estimated effort:** 1–2 hours of my work; the canary is yours.

#### P4.1 Full-suite verification
```bash
./.venv/Scripts/python.exe -m pytest -q > .pmwork/repair-v1/p4-final.txt 2>&1; echo $?
./.venv/Scripts/pmk.exe sentinel
./.venv/Scripts/pmk.exe views
```
Expected: exit 0, sentinel clean, views regenerate without diff beyond the committed projections.

#### P4.2 Void T-0145 **[HUMAN — or explicit authority]**
```bash
./.venv/Scripts/pmk.exe task void T-0145 \
  --reason "Change integrated manually as e08fa8d; re-dispatch would fail NO_CHANGES. See D-65." \
  --actor operator
```
`--help` confirms this exact form (`task_id`, required `--reason`, optional `--actor`). The alternative — you run it — is equally acceptable and is the default if you do not grant the authority.

#### P4.3 Dry-run T-0146 against a real worktree, fake CLI
Prove the whole path without spending quota:
```bash
./.venv/Scripts/pmk.exe fleet check
./.venv/Scripts/python.exe pilot/demo_one_click.py
```
The demo runs brief → tasks → claim → worktree → order → spawn → oracles → bundle → merge → close-check against the fake CLI in a scratch repo. Expected: `DONE`, clean sentinel. Then run T-0146's actual oracle inside a manually created worktree of main:

```bash
git worktree add -B pmk/T-0146-dry work/T-0146-dry HEAD
cd work/T-0146-dry
PYTHONPATH="$(pwd)/src;$(pwd)/tests" ../../.venv/Scripts/python.exe -m cna.tools.coverage --check
PYTHONPATH="$(pwd)/src;$(pwd)/tests" ../../.venv/Scripts/python.exe -c "import json;c=json.load(open('coverage/rules_coverage.json'));assert c['counts']['rule_files']>=66,c['counts']"
```
Expected: both exit 0. Remove the dry worktree afterwards (`git worktree remove`) — this one **you** created, so removing it is not the forbidden cleanup of orphaned trees. **[HUMAN]** if you would rather not have me create/remove it.

#### P4.4 Live canary runbook (yours)
Appendix E is the exact procedure: profile choice, command, expected evidence, abort conditions, cost, and what to capture. I will not run it (your answer, interview Q8).

#### P4.5 Resumption checklist
A one-page `pilot/repair-resumption-checklist-v1.md`:
- [ ] suite green at the recorded count
- [ ] sentinel clean; pins `ok`
- [ ] identity guard active (`core.hooksPath`)
- [ ] precheck enabled
- [ ] canary DONE with a green gate and a bundle
- [ ] D-62…D-69 ratified (D-69 completed by the canary result)
- [ ] quarantine manifest reviewed; orphaned worktrees still pending a separate decision
- [ ] dispatch resumed **by you**, with the Console start time recorded

**Gate G-F:** the dry-run evidence and the runbook. After that, the remaining risk is real-CLI behaviour, which only the canary can measure.

---

## 7. Task register: report items, plan steps, acceptance

| Report item | This plan | Phase | Acceptance test | Effort | Risk |
|---|---|---|---|---|---|
| **F1** land oracle env isolation | §5.1–5.4, P1.1–P1.3 | P1 | `test_oracle_resolves_worktree_module` red→green | S | low |
| **F2** behavioural merge-gate test | §5.4, P1.4 | P1 | `test_merge_gate_resolves_worktree_module` | S | low |
| **F3** worker env isolation | §5.1, §5.4, P1.5 | P1 | `test_worker_env_resolves_worktree_module` + credential/scrub tests | M | **medium** (changes what agents see) |
| **F4** stronger rules oracle | §5.5, P2.1–P2.5 | P2 | `tests/test_rules_baseline.py` | M | medium (baseline must be honest) |
| **F5** resolve T-0145 / relaunch T-0146 | P4.2–P4.3 | P4 | oracle exit 0; task state | S | low |
| **F6** policy editor / Q-077 identity | P3.1 | P3 | recorded finding, `unknown` allowed | S | low |
| **F7** draft D-62+ | P3.2 | P3 | drafts exist, clearly marked | S | low |
| **F8** operator re-decision Q-077 | **out of scope** (§4.3) | — | — | — | — |
| **F9** commit identity discipline | §5.8, P3.3 | P3 | 3 identity tests | M | medium (hooks) |
| **F10** drift reconciliation | §2.5, P0.3–P0.4 | P0 | classification table + manifest | M | low (no deletions) |
| **S1** env invariant lint | §5.11, P1.6 | P1 | `test_subprocess_env_lint.py` | S | low |
| **S4** decision-record reconciliation | §5.10, P3.5 | P3 | gap report + parser tests | S | low |
| **S8** re-lease guard | §5.9, P3.4 | P3 | 3 precheck tests | M | medium (could block legitimate rework; mitigated by advisory failure mode) |

Not adopted (recorded, not silently dropped): **S2** beyond F4, **S3** class-K cool-down automation, **S5** policy-change detection, **S6** beyond F9, **S7** (already practised), **S9** suite ledger beyond the checkpoint, **S10** (replaced by the explicit canary gate).

---

## 8. Verification matrix

| Claim | Command | Expected | Recorded in |
|---|---|---|---|
| Suite green, baseline | `python -m pytest -q` | exit 0, 507 | `.pmwork/repair-v1/pytest-baseline.txt` |
| Oracle path is broken today | `pytest -q tests/fleet/test_worktree_env.py` before P1.3 | 3 failures | `p1-red.txt` |
| Oracle path is fixed | same after P1.3 | all pass | `p1-green.txt` |
| Gate is behaviourally covered | `pytest -q tests/fleet/test_reintegration_gate.py tests/fleet/test_worktree_env.py` | all pass | CI/log |
| Worker env contract | `pytest -q tests/fleet/test_worktree_env.py -k worker` | 3 pass | log |
| No unguarded spawn remains | `pytest -q tests/test_subprocess_env_lint.py` | pass | log |
| Index contract | `pytest -q tests/test_rules_baseline.py` | pass | log |
| Coverage accounts for corpus | `python -m cna.tools.coverage --check` | exit 0 | log |
| T-0146 oracle satisfiable | the card's oracle on main | exit 0 | P4.3 |
| Identity guard | `pytest -q tests/fleet/test_identity_guard.py` | pass | log |
| Precheck guard | `pytest -q tests/fleet/test_precheck.py` | pass | log |
| Sentinel / pins | `pmk sentinel`, `pmk pins check` | clean / ok | checkpoint |
| Real dispatch works | canary runbook | `DONE`, green gate, bundle | `.pm/evidence/` |

---

## 9. Risk register and rollback

| # | Risk | Likelihood | Impact | Mitigation | Rollback |
|---|---|---|---|---|---|
| R1 | Worktree-first `PYTHONPATH` confuses an agent CLI that expects the installed package | medium | one failed attempt | Host path retained after the worktree entries; one canary; transcript inspected | `git revert` the P1 commit |
| R2 | Deduplicating anchors hides a genuine duplicate | low | wrong index | Dedupe only when id **and** line match; distinct-line test still warns | revert P2 commit; regenerate |
| R3 | Coverage redefinition looks like moving the goalposts | medium | trust | Two explicit counters (present vs declaring paths); oracle text unchanged; D-64 records the semantics | revert P2 commit |
| R4 | Identity hook blocks your own commits | low | annoyance | Hook exits 0 unless `UMAWS_PIPELINE=1`; pipeline path blocks only itself | `git config --unset core.hooksPath` |
| R5 | Precheck blocks legitimate rework | medium | stuck task | Only when all oracles pass; run errors are advisory; `precheck_satisfied = false` disables it | edit `agents.toml` |
| R6 | Committing `.pm/events` drift masks an invariant violation | low | audit trail | `pmk sentinel` + `pmk views` before the commit; diff reviewed | revert P0 commit; ledger is append-only |
| R7 | `pmk task void` semantics differ from the help text | low | wrong state | `--help` verified today; use `--reason`; record output | supersede/re-admit under operator authority |
| R8 | Canary fails for a provider reason unrelated to the fix | medium | schedule | Failure class recorded; retry with backoff, not a second profile in the same minute | none needed |
| R9 | Baseline numbers drift between planning and execution | medium | confusion | Every phase re-measures and records actuals; the checkpoint is authoritative | — |
| R10 | Quarantine move breaks a document that references a moved path | low | broken links | Manifest keeps original paths; nothing deleted; move in one commit | move back |

**Global rollback:** each phase is one commit on local `main`, tagged `repair-p0` … `repair-p4`. `git revert <tag>` or `git reset --hard repair-p<n-1>` restores the phase boundary. No phase mutates remote state, `.pm/policy.toml`, the pins, or the event log by hand.

---

## 10. Approvals required

Tick what you authorise. Anything unticked is simply not done; no default is assumed.

| # | Authority | Scope | If declined |
|---|---|---|---|
| **A1** | Approve this plan | entire document | nothing proceeds |
| **A2** | Commit to **local** `main`, never push | P0–P3 commits, tags `repair-p*` | I produce patches instead; slower, more error-prone |
| **A3** | `pmk task void T-0145 --actor operator` on your behalf | one task, one reason string | you run it in P4 |
| **A4** | Create and remove **one** dry-run worktree for T-0146 oracle verification | `work/T-0146-dry` only | you run the two oracle commands yourself |
| **A5** | Add `[fleet] precheck_satisfied = true` to `agents.toml` | fleet config (not pinned) | guard implemented but disabled |
| **A6** | Edit `docs/PDD.md` G-001 oracle; draft D-63 | not pinned | oracle strengthening moves to a test only |
| **A7** | Move (not delete) untracked artifacts to `quarantine/`, add it to `.gitignore` | 121 paths triaged | tree stays noisy; SC-9 unmet |
| **A8** | `git config core.hooksPath .githooks` (repo-local) | one key | interactive logging disabled; pipeline block still active |
| **A9** | Ratify D-62…D-69 after G-E | `pilot/decisions.md` append | drafts stay drafts |
| **A10** | Resume dispatch after a green canary | operational | project stays PAUSED |

**Never requested, never done by me:** push, policy/pins edit, queue decision, Q-077 re-decision, worktree deletion, event-file deletion, amend/rebase of `e08fa8d`/`ebe46ce`, dispatch start.

---

## 11. Assumptions and guesses (flagged)

| # | Item | Basis | How it is resolved |
|---|---|---|---|
| A-1 | `pilot/decisions.md` drift is line-ending churn | 1,451-line diff with no new entries; `.gitattributes` normalisation suspected | P0.3 `git diff --ignore-cr-at-eol` |
| A-2 | The 15 xrefs fail because of prefix mismatch, not 15 corpus holes | 0/15 resolved, all `case-N.M`, 769 anchors | P2.1 diagnosis |
| A-3 | `stats.tables = 0` is a scanner defect | a 66-file wargame rulebook with CRT tables | P2.1 diagnosis |
| A-4 | `coverage.rule_files` counts files declaring `paths:`, not corpus files | 3/66 with `rule_files_matching == 3` | P2.1 read of `coverage.py` discovery |
| A-5 | `docs/PDD.md` is not pinned | `pmk pins check` reports 2 files | verified: constitution + policy only |
| A-6 | `agents.toml` is not pinned, so `precheck_satisfied` is fleet config | same pins result | verified |
| A-7 | The eleven extra worktrees are orphans, not live leases | 0 active leases; `pmk` state 15 vs git 27 | P0.4 census; no removal either way |
| A-8 | `pmk task show` emits `{"task": {...}}`, so my first parse returned nulls | observed output shape | P4 commands use the CLI directly |
| A-9 | 507 + 6 tests + 1 lint test = 514 after P1 | arithmetic from the measured 507 | P1.7 records the actual |
| A-10 | The canary will use a free-tier profile already in `agents.toml` | `agents.toml` drift shows `pi-orca-*` and `kilo-auto` | you choose the profile in Appendix E |

---

## 12. Checkpoint protocol (resumability)

`pilot/repair-checkpoint.md` is the single source of truth for "where were we". It is updated at the **end of every phase and at every stop**, and it is committed with that phase.

```markdown
# Repair checkpoint — proposal-umaws-problems-and-issues-repair-v1

- Phase: P<n> — <name>
- Status: not-started | in-progress | blocked | done
- HEAD: <sha>  Tag: repair-p<n-1>
- Approvals in force: A1, A2, ...
- Measured: tests=<n> exit=<0/1>; warnings=<n>; rule_files=<n>
- Last action: <one line>
- Next action: <one line, with the exact command>
- Open decisions: <A-numbers or none>
- Red evidence: <path>
- Anything surprising: <one line or none>
```

Resuming in a new session requires only: read this proposal, read the checkpoint, run the two commands in "Next action". No re-diagnosis, no transcript archaeology.

---

## Appendix A — Commands behind §2 (reproducible)

```bash
git log --oneline -12
git log -6 --format='%h|%an <%ae>|%cn <%ce>|%s'
git status --porcelain=v1 | wc -l            # 121 untracked
git worktree list | wc -l                    # 27
./.venv/Scripts/python.exe -m pytest -q; echo $?          # 507 collected, exit 0
./.venv/Scripts/python.exe -m pytest --collect-only -q | awk -F': ' '/: [0-9]+$/{s+=$2} END{print s}'
./.venv/Scripts/pmk.exe status
./.venv/Scripts/pmk.exe fleet status
./.venv/Scripts/pmk.exe pins check
./.venv/Scripts/python.exe -c "import pmk;print(pmk.__file__)"
./.venv/Scripts/python.exe -c "import cna;print(cna.__file__)"      # None (namespace pkg)
find docs/rules -name '*.adoc' | wc -l                             # 66
./.venv/Scripts/python.exe -c "import json;d=json.load(open('docs/rules/index.json'));print(d['stats'])"
./.venv/Scripts/python.exe -c "import json;d=json.load(open('coverage/rules_coverage.json'));print(d['counts'])"
```

Recorded results are quoted in §2. If any of these differ when you run them, the checkpoint records the new value and the plan adapts — the plan is not a licence to ignore new evidence.

---

## Appendix B — File-level change manifest

| Phase | File | Change | Why |
|---|---|---|---|
| P0 | `pilot/repair-drift-classification-v1.md` | new | the F10 record |
| P0 | `pilot/repair-worktree-census-v1.md` | new | the 15-vs-27 discrepancy |
| P0 | `pilot/repair-checkpoint.md` | new | resumability |
| P0 | `.gitignore` | add `quarantine/` | visible, untracked artifacts |
| P1 | `src/fleet/runenv.py` | new | the single env contract |
| P1 | `src/fleet/harness.py` | edit `run_command`, `_env`, `_fix_round`, call sites | oracle + worker |
| P1 | `src/fleet/merge.py` | replace inline env with helper | one implementation |
| P1 | `tests/fleet/test_worktree_env.py` | new, 6 tests | the proof |
| P1 | `tools/check_subprocess_env.py` | new | S1 lint |
| P1 | `tools/subprocess_env_allowlist.txt` | new | reviewed exceptions |
| P1 | `tests/test_subprocess_env_lint.py` | new | enforce S1 |
| P2 | `src/cna/tools/rules_index.py` | dedupe registration; xref/table fix per diagnosis | 382 false warnings |
| P2 | `src/cna/tools/coverage.py` | separate counters | 3-vs-66 |
| P2 | `docs/rules/index.baseline.json` | new | pinned sets |
| P2 | `docs/rules/index.json` | regenerate | artifact truth |
| P2 | `coverage/rules_coverage.json` | regenerate | artifact truth |
| P2 | `tests/test_rules_baseline.py` | new | the stronger oracle |
| P2 | `tests/test_rules_index.py` | add 2 unit tests | same-line vs distinct-line |
| P2 | `docs/PDD.md` | strengthen G-001 oracle | F4 |
| P3 | `src/fleet/merge.py` | explicit pipeline identity + anomaly | F9 |
| P3 | `.githooks/pre-commit` | new | interactive logging |
| P3 | `src/fleet/precheck.py` | new | S8 |
| P3 | `src/fleet/harness.py` | call precheck before claim | S8 |
| P3 | `agents.toml` | `precheck_satisfied = true` | S8 enable |
| P3 | `tools/decision_reconcile.py` | new | S4 |
| P3 | `pilot/drafts/decisions-d62-plus.md` | new | F7 |
| P3 | `docs/reports/decision-gaps-*.md` | new (generated) | S4 evidence |
| P3 | `tests/fleet/test_identity_guard.py`, `tests/fleet/test_precheck.py`, `tests/test_decision_reconcile.py` | new | regression cover |
| P4 | `pilot/repair-resumption-checklist-v1.md` | new | handover |
| P4 | `pilot/repair-canary-runbook-v1.md` | new | Appendix E, operator-owned |

---

## Appendix C — What the transcripts established (short form)

Quoted from the report's evidence, not re-derived here:

- T-0145 attempt 1: the agent ran the oracle with the worktree first and got **69 documents**; `--check` reported "up to date"; the harness's own run saw **3**.
- T-0145 attempt 2: both agents reported the task "already passing" — main already contained `e08fa8d`.
- T-0146 attempt 1: the agent wrote, in its own words, that the installed `cna` package shadowed its worktree; the log ends mid-edit, so no submission was made.

The significance is not that the agents were right. It is that **the harness could not tell**, and had no test that would have told it. P1 exists to make that impossible to repeat.

---

## Appendix D — Checkpoint and phase tag convention

- Tags: `repair-p0` … `repair-p4`, annotated, local only.
- Each phase = exactly one commit (P0 may be two: classification, then the reconciliation commit).
- Each commit message ends with the report reference and the draft D-number it belongs to, so `git log` and `pilot/decisions.md` can be reconciled by script (S4).
- A phase is **done** only when its gate evidence exists at a recorded path, not when the code "looks right".

---

## Appendix E — Live canary runbook (operator-executed)

**Preconditions:** P1–P3 landed; suite green; sentinel clean; pins `ok`; dispatch still PAUSED; Console stopped; no other leases.

1. Choose the profile. Prefer a free-tier profile already present and recently exercised; `kilo-auto` is the conservative choice. Record the profile id in the checkpoint.
2. Choose the task. **T-0146** after P2, because its oracle is deterministic and now satisfiable. Do not use T-0145 — it is void.
3. Start the Console (`.\start.ps1`) and note the time.
4. Dispatch exactly one task, supervised:
   ```powershell
   .\.venv\Scripts\pmk.exe dispatch run
   ```
   Watch the Fleet tab. Do not raise concurrency.
5. Capture, as evidence:
   - the `AGENT_STARTED` payload (pid, creation time, worktree);
   - the agent transcript under `.pm/fleet/logs/T-0146/`;
   - the `ORACLE_RESULT` events with exit codes;
   - the bundle under `.pm/evidence/`;
   - the merge commit, and **its author identity** (must be `umaws-pilot`);
   - the final task state.
6. **Abort immediately** if: the worktree path is outside `work/`, the gate command differs from the recorded one, the merge commit is authored by the human identity, or the same failure class repeats twice within a minute.
7. Record the outcome in D-69, complete the resumption checklist, and only then resume dispatch.

**Cost:** one task's provider usage. Free profiles only. If the profile returns QUOTA, stop; do not swap profiles in the same minute (rule 6 of the README).

---

## Appendix F — The brief this proposal answers

The prompt I was given, reproduced so the document is self-contained:

- **Role:** repair lead with direct repository access; the reviewer without access (Claude Web) is unavailable.
- **Context:** a week-long failure in a Kernel-lite multi-agent fleet; a report identifies environment shadowing, weak oracles, and governance gaps; a tested-but-unlanded patch exists.
- **Audience:** the operator, who must approve and execute the human-key steps.
- **Format:** phased plan P0–P4, exhaustive, each phase with exact commands, expected output, gate and rollback.
- **Success criteria:** (1) every judging path resolves the worktree under test; (2) the suite is green and measurably larger; (3) one real dispatch reaches DONE with the fix in place, run by the operator.
- **Constraints:** local commits only, never push; no policy/pins/queue writes; no deletions; no CNA feature work; free/local verification only; governance evidence and drafts, not decisions.
- **Examples:** the report's §8 patch (harness-only), `ebe46ce` (gate-only), and the two agent transcripts.

---

*End of proposal. Status: PROPOSED. Author: Buffy (Codebuff), 2026-11-08. Nothing was implemented to produce this document beyond reading, measuring, and writing this file.*
