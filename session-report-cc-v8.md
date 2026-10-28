# Session Report v8 — Hermes session-id parsing fix + v7 feedback item 6c

**Date**: 2026-10-28
**Status**: Complete

## Summary

Processed mid-turn Hermes feedback (item 9) and v7 reviewer feedback item 6c.
All changes are in `v8-fix.patch` (git diff for tracked files + new test file
as a no-index diff). JUnit XML is in `pytest_junit.xml`.

## Changes by Reviewer Item

### Reviewer Item 1 (Evidence) ✓
Raw pytest output (with JUnit XML):
```
$ python -m pytest tests/ --junit-xml=pytest_junit.xml -q
288 passed in 96.01s
```

### Reviewer Item 2 (plat.spawn env handling) ✓
**Bug found and fixed**: `spawn_slot` in `src/fleet/spawn.py` previously did:
```python
actor_env = dict(env) if env is not None else {}
```
When `env=None` (which `_env()` returns for `via_gateway=false` profiles),
`actor_env` started as an empty `{}`, so `plat.spawn` received
`env={"PMK_ACTOR": "..."}` — the child lost PATH, USERPROFILE, APPDATA, etc.
and could not find executables on PATH.

**Fix**: Always start from `os.environ`, then apply any scrubbed env from
`_env()`, then set `PMK_ACTOR` last:
```python
actor_env = dict(os.environ)
if env is not None:
    actor_env.update(env)
actor_env["PMK_ACTOR"] = f"worker:{profile_id}"
```
`plat.spawn` was already correct: `stderr=subprocess.STDOUT` merges stderr
into stdout (line 400), and `env=dict(env)` passes the merged env through.

### Reviewer Item 3 (End-to-end tests) ✓
Two new end-to-end tests in `tests/fleet/test_hermes_session.py`:
- `test_end_to_end_session_id_from_merged_stdout_stderr`: A fake CLI prints
  "Hi Tiwa..." to stdout and `session_id: <id>` to stderr. Spawned via
  `plat.spawn`, the merged log contains both lines, and the Hermes adapter
  parses the id correctly.
- `test_end_to_end_env_inheritance`: Verifies PATH is inherited and PMK_ACTOR
  is set to `overseer:hermes-oneshot`.
- `test_end_to_end_env_none_inherits_parent`: When `env=None`,
  `plat.spawn` still inherits PATH from the parent environment.

### Reviewer Item 4 (Tighten regex) ✓
`HERMES_SESSION_PATTERN` in `src/fleet/adapters/base.py` tightened from
`r"session_id:\s*(\S+)"` to `r"session_id:\s*(\d{8}_\d{6}_[0-9a-f]+)"` —
matches the known `YYYYMMDD_HHMMSS_<hex6>` format so a stray "session_id:"
line from a different process cannot inject a bogus id.

### Reviewer Item 5 (_actor_from_env docstring + overseer prefix) ✓
**Docstring fixed**: Removed the false claim that `submit`, `verify`,
`integrate`, and `revoke` have human-only guards — only `task_void` does.

**Overseer prefix**: `src/fleet/overseer.py` line 221 was changed from
`PMK_ACTOR=f"worker:{profile.id}"` to `PMK_ACTOR=f"overseer:{profile.id}"`.
`_actor_from_env` now documents the `overseer:<profile>` format (accepted
as the catch-all `return Actor(kind=kind, ...)` branch, setting
`kind="overseer"`).

### Reviewer Item 6c (Task type check comment) ✓
Fixed both comments in `src/pmk/api.py`:
- Line 284-286 (task_admit): Replaced "Reject unknown task types: only types
  that map to a profile role can be dispatched. (CIP Part B 14.3)" with a
  self-documenting comment listing the six types and noting it's a structural
  check, not access control.
- Line 308-309 (task_admit): Same fix. The decision is "keep as is" — the
  check accepts any of TASK_TYPES regardless of profile roles, which is
  correct because the Kernel doesn't gate by profile roles (the Dispatcher
  does that at selection time).

### Reviewer Item 8 (Session report) ✓
This document.

## Files Changed

| File | Change |
|------|--------|
| `agents.toml` | Hermes comment: real capture vs "Resume this session" trailer |
| `src/fleet/adapters/base.py` | `HERMES_SESSION_PATTERN` (tightened regex); `parse_session_id` implementation |
| `src/fleet/adapters/generic.py` | `TemplateAdapter.parse_session_id` override (uses self.caps, not _base.caps) |
| `src/fleet/harness.py` | `_session_from_log` takes adapter arg, delegates to `parse_session_id` |
| `src/fleet/spawn.py` | env handling: start from `os.environ`, not `{}` |
| `src/fleet/overseer.py` | PMK_ACTOR prefix: `worker:` → `overseer:` |
| `src/pmk/api.py` | `_actor_from_env` docstring (overseer format, guard accuracy); type-check comments |
| `tests/fleet/test_fleet.py` | Comment fix on hermes caps test |
| `tests/fleet/test_hermes_session.py` | New file: 11 tests (8 unit + 3 e2e) |

## Decisions

1. **Regex tightened to `\d{8}_\d{6}_[0-9a-f]+`** — prevents false positives from
   unrelated "session_id:" lines. The pattern matches the operator-verified format.
2. **env starts from `os.environ`** — the child must inherit PATH/USERPROFILE/
   APPDATA. The bug (empty dict when env=None) would have silently broken all
   real CLI spawns.
3. **`overseer:<profile>` prefix** — uses `overseer:` to distinguish overseer-
   triggered runs from fleet-spawned workers. `_actor_from_env` accepts it via
   the catch-all `return Actor(kind=kind, ...)` branch.
4. **Type check kept structural** — the reviewer confirmed "keep as is" for the
   access-control decision. The comment now accurately says it's structural
   (is-the-type-known?) not an access-control gate.
