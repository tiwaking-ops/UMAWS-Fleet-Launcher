All 303 tests pass. Let me verify the JUnit XML was updated:

Now let me write the final report:

Here's a summary of what was done:

## Changes Made

### `src/fleet/merge.py`
Moved the `_cleanup_default_pytest_ini(repo, task, branch)` call from **before** `commit_worktree` to **after** it (line 150). This ensures `git diff --name-only <base>..<branch>` can see the committed pytest.ini change on the lease branch. The stale pre-commit comment block was removed, and the function now relies solely on the diff check.

### `tests/fleet/test_regressions.py`
Updated `test_merge_cleanups_pytest_ini_via_diff_not_writescope` to:
- Use `["config/", "pytest.ini"]` in write_scope (so scope_check passes)
- Not pre-commit the pytest.ini (let `commit_worktree` handle it during integrate)
- Verify the root pytest.ini is tracked after merge and matches the incoming content

## Test Results

**303 passed** (0 failures, 0 errors) — JUnit XML regenerated as `pytest_junit.xml`

## Ordering: Old vs New

| Order | git diff sees pytest.ini? | Cleanup fires? | Root pytest.ini | Fast-forward | Test |
|-------|--------------------------|----------------|-----------------|-------------|---|
| Old (before commit) | No — branch ref doesn't exist yet | No | Collides (untracked) | **Fails** | **Fails** |
| New (after commit) | Yes — commit_worktree staged it | Yes | Deleted (byte-identical default) | Succeeds | **Passes** |

## Deliverables
- `src/fleet/merge.py` and `tests/fleet/test_regressions.py` diff: saved to `/tmp/merge-tests-diff.patch`
- Fresh `pytest_junit.xml` (303 tests, 0 failures, 0 errors)
- `report-cc-v11-final.md` with full summary

## Decisions
1. **No write_scope shortcut in `_cleanup_default_pytest_ini`** — the git diff check alone is sufficient. If pytest.ini is in write_scope, commit_worktree commits it and the diff sees it. If it's not in write_scope, scope_check rejects the change before cleanup runs.
2. **Test uses `"pytest.ini"` in scope** — this was necessary because `scope_overlaps` uses prefix matching, so `"*.ini"` or `"config/"` alone would cause scope_check to reject the pytest.ini write. The reviewer's "glob/directory" suggestion is not possible with the current prefix-matching implementation.