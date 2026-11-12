---
title: "Fleet scratch leak — root-cause fix report"
version: "1.1.0"
date: "2026-11-12"
author_llm: "Step 5 Preview (stepfun-ai/step-5-preview, nvidia)"
scope: "the fleet's throwaway directories in the global %TEMP% (pmk-merge-*, pmk-precheck-*, pmk-precheck-dry-*): measurement, root cause, fix, the two operator-approved reclaim runs, and what is deliberately left alone"
---

# Fleet scratch leak — root-cause fix report

Operator instruction (next-move items after the scratch-prune run): *"Consider the
root-cause fix for orphan merge dirs: `src/fleet/merge.py` uses
`tempfile.mkdtemp(prefix="pmk-merge-")` instead of a pytest-managed temp dir, so
tests leak trees into the global `%TEMP%`."*  This report records the
measurement, the root cause (which turned out to be **three** defects in one
class, and bigger than the merge one), the fix, and the verification.

No destructive action was taken on the existing leftovers; they are reported in
section 6 with the facts needed to decide.

## 1. What was actually leaking

Measured on 2026-11-12 at ~15:40, while the fleet was running:

| Family | Dirs | Size | What it was |
|---|---|---|---|
| `%TEMP%/pmk-precheck-*` | **412** | ~0 MiB (empty husks) | one per lease admission, oldest 2026-11-08 21:13, newest minutes before the fix |
| `%TEMP%/pmk-merge-*` | 14 (+1 live foreign) | ~16 MiB | 13 orphan/empty shells whose `.git` points at **deleted** pytest basetemps (2026-10-25 → 2026-11-12), plus one live merge of the *other* project |
| `%TEMP%/pmk-precheck-dry-*` | 1 | 29.85 MiB | this repo's stale precheck dry run from 2026-11-10 |
| `tmp/` (repo-local) | 30 | 172.2 MiB | canary/precheck/reviewer trees, 5 tracked files, 6 still-registered worktrees |

The husk family was **live**: fresh `pmk-precheck-*` directories appeared every
few minutes (15:26, 15:31, 15:38 …), because the lease-admission path calls
`precheck.oracles_already_pass` on every claim (`harness.py:315`).

## 2. Root cause — three defects, one class

1. **`precheck.oracles_already_pass` never removed the directory around its
   worktree.** It added `pmk-precheck-<rand>/tree`, ran the oracles, removed the
   *worktree*, and left the parent directory behind forever. That is the 412
   husks: unconditional, one per call, on every lease admission.
2. **`shutil.rmtree(path, ignore_errors=True)` hid real failures.** On Windows it
   fails whenever a file *or a directory* in the tree is read-only, which git
   leaves. Verified on this machine rather than asserted (probe in section 5):
   with the old call, the tree survived in **4 of 4** read-only arrangements.
   This is how a whole `pmk-merge-*` / `pmk-precheck-dry-*` tree survived a run
   that was killed or merely unlucky.
3. **The scratch lived in the global namespace with no owner.** A leftover whose
   repository is gone cannot even be proven to belong to this project —
   `pmk.worktrees.prune_scratch` deliberately refuses a merge tree it cannot
   prove is ours — so every leftover from a run that died was permanent. The
   operator's diagnosis (tests should use a pytest-managed temp dir) addresses
   exactly this.

## 3. The fix

New module **`src/fleet/scratch.py`** owns the class:

* `scratch_dir(prefix, temp_root=None)` — the throwaway directory, under the
  caller's root when one is given (a pytest-managed `tmp_path` in tests), the
  global temp in production;
* `remove_scratch(path)` — clears the write-protect bit on every file *and every
  directory* deepest-first, then removes, and **returns whether anything is
  left** instead of swallowing the outcome.

Call sites:

| File | Change |
|---|---|
| `src/fleet/merge.py` | `integrate()` gains `temp_root`; both `mkdtemp` sites and both `rmtree(ignore_errors=True)` sites go through `scratch` (retry path and outer `finally`) |
| `src/fleet/precheck.py` | `oracles_already_pass()` and `dry_run()` gain `temp_root`; **the missing directory removal is added** (the husk leak); the `finally` now also covers the early "could not add the worktree" return |
| `tests/fleet/conftest.py` | one autouse fixture: a default `scratch_dir` lands under the test's `tmp_path`, never the global temp — so no fleet test, present or future, litters it |
| `tests/fleet/test_scratch.py` | 9 regression tests (new file) |

Production behaviour is unchanged apart from the cleanup: the fleet's merge
scratch still lives in `%TEMP%`, and the sanctioned collector for a leftover is
still `pmk worktree prune --merge-trees`.

## 4. Why one fixture rather than 32 call-site edits

`tests/fleet` has ~32 `integrate()` / `dry_run()` / `oracles_already_pass()`
calls. The autouse fixture covers all of them — and every test written later —
while an explicit `temp_root` parameter still wins when a test wants its own
directory (which is what the regression tests use, so "nothing left behind" is
asserted against a directory the test owns rather than a namespace other
processes are writing to). Autouse fixtures are already house style here.

## 5. Verification

* **Read-only probe** (win32, this machine): `rmtree(ignore_errors=True)` left
  the tree behind for read-only file / read-only subdir / read-only root /
  read-only all; `remove_scratch` returned True and removed it in all four.
* **`tests/fleet/test_scratch.py`**: 9 passed (the four read-only arrangements
  are the parametrised cases).
* **Merge + precheck suites under a private `%TEMP%`**: 39 passed, **0**
  `pmk-*` directories leaked into the private root.
* **All of `tests/fleet` under a private `%TEMP%`**: **302 passed**, **0**
  leaked — the finish line for "tests leak trees into the global `%TEMP%`".
* **Full suite**: **1347 passed, 1 skipped** (`umaws_junit_scratchfix.xml`), the
  gate recorded in the commit message.

## 6. What was deliberately left alone — then what the operator approved

The operator reviewed the residual inventory and approved two of the three
groups:

| Surface | Size | Outcome |
|---|---|---|
| 13 orphan/empty `pmk-merge-*` shells | ~0 bytes | **left alone** — their repositories are gone, so ownership cannot be proven, and one of the family is another project's *live* merge |
| 1 live `pmk-merge-*` (umaws-noscope-toy) | — | **left alone** — another project's in-flight merge; the ownership gate skips it |
| 412 `pmk-precheck-*` husks | ~0 bytes | **left alone** — unprovable by design and now stopped at the source; machine hygiene, not repo work |
| 1 `pmk-precheck-dry-*` (2026-11-10) | 29.85 MiB | **reclaimed** — approved "extend the sanctioned path, then run" (section 7) |
| `tmp/` registered canary worktrees (6) | 97.91 MiB | **reclaimed** — approved "only the 6 registered canary worktrees" (section 8) |
| `tmp/` reviewer trees (3), 5 tracked files, small canary/gate dirs | 60.9 MiB + ~0.5 MiB | **left alone** — other agents' work and repo content |
| `.claude/worktrees/agent-a8ea…` | — | **left alone** — another agent's worktree |

One operational note: the venv is an **editable install** of `src`, so every
newly started `pmk`/pytest process picks this fix up. The two
`umaws-noscope-toy` fleet processes running at the time of the fix hold the old
code in memory and keep making husks until they restart.

## 7. Run one — `pmk worktree prune --precheck-trees --yes`

The dry run listed exactly the two worktrees of the stale directory; the applied
run reclaimed both, capture-first, and the results verified:

| Check | Result |
|---|---|
| `removed` | 2/2 (`base`, `scratch`), 0 skipped |
| `%TEMP%/pmk-precheck-dry-bje5ewal` | gone (29.85 MiB freed) |
| `git worktree list` | 0 registrations left; `git worktree prune -n -v` silent |
| `stranded/` | 115 → 117; both archives `verify_archive` → True |
| `stranded/…-scratch/diff.patch` | 1390 bytes, `src/pmk/worktrees.py` — the one tracked change |
| `stranded/…-scratch/untracked.tar` | `tests/pmk/test_prune_merge_trees.py` — the one untracked file |
| `stranded/…-scratch/ignored.tar` | 25 ignored files packed |

Re-gate after the extension: the full suite is **1353 passed, 1 skipped**
(`umaws_junit_precheck.xml`) — 1347 from the fix's gate plus the six new
precheck cases.

So the two `git status` entries the stale tree carried were captured, not
discarded.

## 8. Run two — the six registered canary worktrees under `tmp/`

A documented one-off through the sanctioned deletion path
(`worktrees.reclaim_after_capture`, deepest-first so the nested
`work/T-0147-120` was captured before the directory containing it).  Scope was
exactly the six registered worktrees; the reviewer trees, the five tracked
files and everything else under `tmp/` were not touched.

| Check | Result |
|---|---|
| `removed` | 6/6, 0 kept |
| `tmp/` | 172.18 → 74.27 MiB (**97.91 MiB freed**), 30 → 25 directories |
| `git worktree list` | 0 `tmp/` registrations; `git worktree prune -n -v` silent |
| `git ls-files tmp` | still 5 tracked files |
| `stranded/` | 117 → 123; all six archives `verify_archive` → True |
| Dirty trees captured | `canary-base-20261110` (1 entry), `clean-head-20261110` (2 entries) |

The other four were clean, so their archives are empty patches by design.

## 7. Provenance

Authored by Step 5 Preview (stepfun-ai/step-5-preview, nvidia) on 2026-11-12.
No other model's work was overwritten; the shared working tree carried other
agents' changes throughout and none were committed here (see the commit's
staging note).
