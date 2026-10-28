# v11 Review Response

## Two fixes applied

### 1. merge.py: _cleanup_default_pytest_ini moved AFTER commit_worktree

**Problem**: The cleanup was called BEFORE `commit_worktree()`, so the lease branch
ref didn't exist yet and `git diff --name-only <base>..<branch>` couldn't see the
incoming pytest.ini change. Only the write_scope check could fire — and a glob or
directory scope (e.g. `"config/"`) would miss a pytest.ini added by the worker.

**Fix**:
- Moved `branch = f"pmk/{task.id}-{lease.fence}"` and `main_branch = repo.default_branch()`
  before `commit_worktree()`
- Moved `_cleanup_default_pytest_ini(repo, task, branch)` to AFTER the commit succeeds
  and BEFORE the fast-forward merge
- Removed the duplicate `main_branch = repo.default_branch()` that was inside the
  merge worktree section
- `main_branch` variable is now reused for both the diff check and the
  `git worktree add --detach <main_branch>` call

### 2. New test: scope-gated cleanup via diff, not writescope

`test_merge_cleanups_pytest_ini_via_diff_not_writescope`:
- write_scope is `"config/"` (directory glob, not "pytest.ini")
- worker commits a config file AND a default-content pytest.ini to the lease branch
- After commit, `git diff --name-only main..pmk/<task>-1` shows pytest.ini
- Cleanup fires via the diff path, not the write_scope path
- Merge succeeds, pytest.ini is tracked from the incoming commit

## Test results

```
303 passed in 91.7s
```

JUnit XML: `pytest_junit.xml` (303 tests, 0 failures, 0 errors)

## What was not run / could not be verified

- **tmp/ scripts**: Leave in place, not run (per reviewer instruction in v11)
- **Combined patch**: Not regenerated — only diffs for `merge.py` and `test_regressions.py` sent
