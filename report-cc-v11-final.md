# v11 Review Response — Final

## Two fixes applied

### 1. merge.py: `_cleanup_default_pytest_ini` moved AFTER `commit_worktree`

**Problem**: The cleanup was called BEFORE `commit_worktree()`, so the lease branch
ref didn't exist yet and `git diff --name-only <base>..<branch>` couldn't see the
incoming pytest.ini change. Only the write_scope check could fire — and a glob or
directory scope (e.g. `"config/"`) would miss a pytest.ini added by the worker.

**Fix**:
- Moved `_cleanup_default_pytest_ini(repo, task, branch)` call to AFTER the commit succeeds
  and BEFORE the merge worktree setup
- The `branch` and `main_branch` variables are computed before `commit_worktree` (already correct)
- Removed the stale pre-commit comment block
- The `_cleanup_default_pytest_ini` function now relies solely on the git diff check
  (the write_scope shortcut was removed — the diff check covers all cases since
  pytest.ini in write_scope → commit_worktree commits it → diff sees it)

### 2. New test: `test_merge_cleanups_pytest_ini_via_diff_not_writescope`

- write_scope is `["config/", "pytest.ini"]` (includes pytest.ini so scope_check passes)
- worker writes a config file AND a default-content pytest.ini in the worktree (uncommitted)
- `integrate()`'s `commit_worktree()` commits both to the lease branch
- The cleanup runs AFTER the commit, so `git diff --name-only main..pmk/<task>-1` shows pytest.ini
- Merge succeeds, pytest.ini is tracked from the incoming commit

## Diff of `_cleanup_default_pytest_ini`

The key change — the function now ONLY uses the git diff check (no write_scope shortcut):

```python
def _cleanup_default_pytest_ini(repo, task, branch: str) -> None:
    """Remove an untracked, default pytest.ini from the repo root."""
    from pathlib import Path

    # Only proceed if the incoming branch adds or modifies pytest.ini.
    base = repo.default_branch()
    code, changed, _ = repo.git("diff", "--name-only", f"{base}..{branch}")
    if code != 0 or "pytest.ini" not in changed.split():
        return  # unrelated merge -- leave the root pytest.ini alone
    # ... (tracks check and byte-identical deletion unchanged)
```

## Test results

```
303 passed in 116.31s
```

JUnit XML: `pytest_junit.xml` (303 tests, 0 failures, 0 errors, 0 skipped)

## Files changed (in this round)

Only two files, per reviewer instruction:

- `src/fleet/merge.py` — moved `_cleanup_default_pytest_ini` call to after `commit_worktree`
- `tests/fleet/test_regressions.py` — updated `test_merge_cleanups_pytest_ini_via_diff_not_writescope`

## Ordering verification

With the OLD ordering (cleanup before commit):
- `commit_worktree` hasn't run yet, so no commit on the lease branch
- `git diff --name-only main..pmk/<task>-1` returns empty (branch ref doesn't exist yet, or exists with no new commit)
- Cleanup returns without deleting the root pytest.ini
- The untracked default root pytest.ini collides with the fast-forward
- Merge fails → test asserts `result.ok` → **FAILS**

With the NEW ordering (cleanup after commit):
- `commit_worktree` commits pytest.ini to the lease branch
- `git diff --name-only main..pmk/<task>-1` shows `pytest.ini`
- Cleanup fires, deletes the untracked default root file
- Fast-forward succeeds → test passes → **PASSES**
