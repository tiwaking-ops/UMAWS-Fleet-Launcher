# Session Report CC-V10

## Summary

Response to reviewer feedback (Claude Web, after v9). Three items implemented:
clock-parse dedup, pytest.ini docstring + merge cleanup, and sentinel-on-real-data.
All 301 tests pass.

## Files in this patch

**Code changes**:
- `src/fleet/conductor.py` — clock_parse MERGE_REFUSED recorded at most once per (task, fence)
- `src/pmk/api.py` — `_write_pytest_config` docstring corrected
- `src/fleet/merge.py` — `_cleanup_default_pytest_ini()` called before commit; deletes untracked byte-identical default pytest.ini
- `tests/fleet/test_regressions.py` — 5 new tests

**New test files** (from v8):
- `tests/pmk/test_regression_i5.py` — I5/I6 sentinel tests
- `tests/fleet/test_hermes_session.py` — env/actor e2e tests
- `tests/fleet/test_reintegration_gate.py` — reintegration gate
- `tests/fleet/fixtures/opencode/quota-credits.txt`
- `docs/free-models.md`

Combined patch: `v8-combined.patch` (3153 lines, 22 files, applies cleanly to HEAD)
JUnit XML: `pytest_junit.xml` (301 tests)

## Reviewer Items Addressed

### 1. clock_parse dedup (conductor.py)

**Problem**: The clock-parse guard recorded `MERGE_REFUSED(reason="clock_parse")`
on every tick while the timestamp stayed malformed — unbounded event growth.

**Fix**: `src/fleet/conductor.py` now queries `kernel.events()` for an existing
`MERGE_REFUSED` with `reason="clock_parse"` for the same `(task, fence)` before
recording a new one. Only the first occurrence is written; subsequent ticks
still skip via `continue` and return the result dict.

**Test**: `test_clock_parse_records_at_most_one_refusal` drains 6 times after
corrupting the INFRA_RETRY timestamp. Asserts `MERGE_REFUSED(clock_parse)`
count == 1 for the (task, fence) pair. Also confirms INFRA_RETRY count stays
flat at 1 (no new retries created).

### 2. pytest.ini (api.py + merge.py)

**2a — Docstring**: `src/pmk/api.py` `_write_pytest_config` docstring corrected:
removed the false T-0009 reference, clarified the file is
`repo.root / "pytest.ini"` (not `.pm/.pytest.ini`).

**2b — Merge cleanup**: `src/fleet/merge.py` adds `_cleanup_default_pytest_ini(repo)`
called before `commit_worktree()` in `integrate()`. Logic:
1. If `repo.root / "pytest.ini"` does not exist → return (no-op).
2. If it IS TRACKED (`git ls-files` returns it) → return (never touch tracked).
3. If it is untracked AND byte-identical to `_DEFAULT_PYTEST_INI` → delete it
   so the incoming commit creates it tracked.
4. If it is untracked and MODIFIED → leave it (the merge will conflict, reported
   as before).

`_DEFAULT_PYTEST_INI` constant matches the exact bytes Kernel.init writes.

**2c — Tests**:
- `test_merge_removes_untracked_default_pytest_ini`: `Kernel.init()` writes
  default pytest.ini (untracked); worker's worktree has the same file tracked.
  After `integrate()`, `git ls-files` shows pytest.ini tracked — the untracked
  duplicate was deleted, the incoming commit's version took over.
- `test_merge_keeps_user_modified_pytest_ini`: user writes a non-default
  pytest.ini at repo root. After merge, the file survives with original content.

### 3. Sentinel on real data

**testproject1 (.pm copy)**:
- 301 total events, 1 INTEGRATED event (T-0003, fence 3, bundle=EB-T-0003-3)
- INTEGRATED event:
```json
{"seq": 265, "ts": "2026-10-26T00:07:48Z", "type": "INTEGRATED",
 "subject": "T-0003", "fence": 3,
 "payload": {"bundle": "EB-T-0003-3",
             "commit": "6764d54977a27e6f139c7c513cf9bc3af82b37cb"}}
```
- Sentinel findings: 10 total, 0 stops
  - 9 × I16 (deleted out-of-band files: AGENTS.md, CLAUDE.md, .claude/rules/*, .claude/skills/*)
  - 1 × I13 (views/ledger.md hash mismatch — views projection drift)
- No I6 stops fired.

**Toy3 (work/T-0003-3/.pm copy)**:
- 63 total events, 0 INTEGRATED events
- No INTEGRATED payload to sample (this is the Toy3 project that never ran)
- Sentinel findings: 12 total
  - 2 × I8' (stops=True): constitution.md and policy.toml hash mismatch
    (expected — the copy uses testproject1's pins against a different git history)
  - 10 × I16 (deleted out-of-band files)
- I8' stops fired because the pin hash doesn't match the copied constitution
  (the worktree's .pm was created from an earlier commit than the live constitution).
  This is expected for a cross-project copy, not a code defect.

### 4. Additional tests

- `test_task_admit_rejects_unknown_type`: creates a PROPOSED card with type
  "bogus" via direct event write, confirms `task_admit` raises
  `KernelError("invalid_task_type")`. (The create-time check already existed;
  this covers the admit path.)
- `test_integrate_rejects_corrupt_bundle`: writes corrupt JSON to bundle.json,
  confirms `Kernel.integrate` raises `KernelError("invalid_bundle")`. Complements
  the existing `test_integrate_refuses_a_promotion_with_a_failing_oracle`
  which tests ok=False (structured) vs. unreadable JSON.

## Test Results

```
301 passed in 113.07s
```

## What was NOT run / could not be verified

- **Toy3 real INTEGRATED payload**: The only Toy3 tree on disk
  (`work/T-0003-3/.pm`) has 0 INTEGRATED events — it never ran. The root
  `.pm` is testproject1's own log with 1 INTEGRATED (T-0003). No separate
  Toy3 project with real data exists on this machine.
- **Pre-patch sentinel comparison**: The I8' findings from the worktree copy
  are environment artifacts (pin hash mismatch from cross-project copy), not
  pre-existing code issues. A true before/after comparison requires a clean
  Toy3 checkout with its own pins, which is not present.

## Decisions

- **clock_parse dedup via event log lookup** (not in-memory set): persists
  across drain_merge_queue calls, survives restarts, and matches the
  append-only log philosophy. Slightly more expensive per-tick but
  correctness-critical.
- **pytest.ini cleanup in merge.integrate**: placed before `commit_worktree`
  so the tracked file from the incoming commit lands cleanly. The alternative
  (cleaning in the main tree after fast-forward) would leave an untracked
  file temporarily.
