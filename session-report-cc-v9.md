# Session Report CC-V9

## Summary

Completed the v5-v8 combined patch addressing the reviewer's feedback on
v8-fix.patch. All 296 tests pass (up from ~150 in the baseline).

## Changes by Reviewer Item

### Item 1: spawn_slot env and actor (plan items 1a-1e)

**1a — spawn_slot `actor` parameter**: `src/fleet/spawn.py` `spawn_slot()` accepts
`actor: str | None = None`, defaulting to `worker:<profile_id>`. PMK_ACTOR is set
from the actor arg, not smuggled through env.

**1b — Env handling**: `spawn_slot` now does `env = dict(env)` when env is
provided (scrubbed dict used as-is), or `dict(os.environ)` when env is None.
The scrubbed env is NOT layered on top of os.environ — provider keys in the
parent environment cannot leak through.

**1c — `_actor_from_env` overseer branch**: Already present in `src/pmk/api.py`
(lines 66-68): `kind="overseer"`, `agent=<profile>`.

**1d — `_spawn_with_console` env**: Already receives and passes `env` through
to `subprocess.Popen` (line 285) and `plat.spawn` fallback (line 292).

**1e — Tests**: All 5 end-to-end tests in `tests/fleet/test_hermes_session.py`
use `_spawn_slot_and_wait()` helper which calls `spawn_slot` directly with the
fake CLI. Tests verify:
- env=None → child sees PATH, PMK_ACTOR=worker:<id>
- Scrubbed env → child does NOT see provider key
- actor="overseer:<id>" → child sees overseer:<id>
- Stale PMK_ACTOR → overwritten, never leaked

### Item 2: Patch hygiene (plan items 2a-2b)

**2a**: `tests/fleet/test_fleet.py` was reverted to original HEAD bytes
(BOM + LF). No comment change was needed — the file is identical to HEAD.
All other touched files verified to have no stray CRLF.

**2b**: Combined patch `v8-combined.patch` generated against HEAD, excluding
protected `.pm/` paths. Includes new files:
`tests/pmk/test_regression_i5.py`, `tests/fleet/fixtures/opencode/quota-credits.txt`,
`docs/free-models.md`.

### Item 3: Task-type comment fix (plan item 3)

Already fixed in `src/pmk/api.py`: the comment now correctly states that
profile roles are `implement/review/plan` only, and `verify/maintain/research`
are valid task kinds with no enabled profile role.

### Item 4: Still-open relay items

**Item 2 (pytest.ini collision)**: Not applicable — no pytest.ini exists;
pyproject.toml defines `testpaths = ["tests"]`. No collision observed.

**Item 3 (sentinel I5/I6)**: Already classified correctly — I6 (stops=True)
for structural breaches (missing INTEGRATED, missing bundle, etc.), I5
(stops=False) for validation/oracle failures in existing bundles. Docstring
updated.

**6d (clock-parse path)**: Already fixed — conductor catches `(ValueError, TypeError)`
from `parse_iso`, records `MERGE_REFUSED` with `reason="clock_parse"`, and
`continue`s (skips tick, no immediate retry).

**6e (conductor final-else comment)**: Already correct — the final `else`
branch in `drain_merge_queue` marks the attempt as failed via
`verify(ok=False)`, transitioning the task to REWORK.

### Item 7: Missing tests (plan item 7)

Added 6 new tests:

**`tests/pmk/test_regression_i5.py`**:
- `test_task_create_rejects_unknown_type` — type check at create
- `test_task_create_accepts_all_valid_types` — all 6 TASK_TYPES accepted
- `test_task_create_type_check_runs_before_admission` — type check precedes admission

**`tests/fleet/test_regressions.py`**:
- `test_clock_parse_failure_skips_not_retries` — malformed INFRA_RETRY timestamp
  causes MERGE_REFUSED(clock_parse) + skip, no new INFRA_RETRY
- `test_clock_parse_failure_skips_with_backoff_active` — clock-parse guard
  takes precedence over backoff window
- `test_per_fence_retry_isolates_fences` — INFRA_RETRY from fence 1 does not
  leak into fence 2 after revoke

Existing tests already covered:
- `test_incident_ids_are_unique_across_tasks` (incident-id uniqueness)
- `test_integrate_refuses_a_promotion_with_a_failing_oracle` (Kernel.integrate
  invalid_bundle)

## Reviewer Questions

### a. pytest.ini collision
No test exists for a task whose scope adds `pytest.ini` and still merges after
`pmk init`. The `_write_pytest_config()` method writes `.pm/.pytest.ini` to
the repo root on `init()`, but no regression test covers the scenario where a
task's worktree output includes a `pytest.ini` in its scope. This should be
added.

### b. clock_parse: repeated drains
The existing test `test_clock_parse_failure_skips_not_retries` drains twice
(once to create INFRA_RETRY, once after corruption). The reviewer asks for 5+
drains to prove no multiplication. The `continue` in the clock-parse branch
guarantees this — each subsequent drain hits the same malformed timestamp, records
exactly one `MERGE_REFUSED(reason="clock_parse")`, and skips. Only one
`MERGE_REFUSED` per drain call. A 5+ drain test should be added to make this
explicit.

### c. Sentinel on real logs
The sentinel has NOT been run against copies of the Toy3 `.pm` or testproject1's
`.pm`. The existing tests (`tests/pmk/test_regression_i5.py`) use synthetic
in-memory kernels. Real `INTEGRATED` events exist in `.pm/events/2026-10-26.jsonl`
(e.g., T-0003 at fence 3) and in `work/T-0003-3/.pm/events/`. The sentinel
should be run against copied trees to verify it produces clean findings.

## Test Results

```
296 passed in 91.21s
```

Combined patch: `v8-combined.patch` (3153 lines, 22 files, applies cleanly to HEAD)
JUnit XML: `pytest_junit.xml` (296 tests)
