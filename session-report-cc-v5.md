Good, I already added `task_void` in both `api.py` and `cli.py`. Now let me check the state guards I added in `submit`, `verify`, and `integrate`:

Good. Now let me check the conductor.py changes and the sentinel.py changes:

Good. Now let me check the store.py for the `fleet_state_path` and `default_branch`:

Now let me check `models.py` for `TASK_TYPES`:

Now let me check the `cli.py` for the `--actor` parameter handling:

Now let me check how the conftest for fleet tests sets up `fake_kernel`:

Now I have a comprehensive picture of the current state. Let me also check if there's a `state.py` that has the VERIFIED reducer that I need to guard:

Good. Now I have a complete picture of what's already implemented and what's still needed. Let me now write out my proposal for the remaining items.

Here's my proposal for fixing list v5:

---

## Proposal for Fix List v5

### Already Implemented (from the earlier turn)

1. **I5 enforcement in `integrate()`** — The Kernel now reads the bundle from disk and refuses promotion if any oracle failed. ✅ Done in `api.py`.
2. **Pre-merge I5 check in `drain_merge_queue()`** — The conductor checks the bundle before `merge_mod.integrate()` is called. ✅ Done in `conductor.py`.
3. **Sentinel I5 fix** — Now checks `all_oracles_passed()` on DONE tasks, only on live state (not historical log). ✅ Done in `sentinel.py`.
4. **Sentinel I4 fix** — Uses in-order replay tracking current fence per task; detects stale-fence integrations. ✅ Done.
5. **Task type validation** in `task_create()` — Rejects types not in `TASK_TYPES`. ✅ Done in `api.py`.
6. **`task_void()` method + `pmk task void` CLI** — Operator-only void, revokes lease first. ✅ Done in `api.py` + `cli.py`.
7. **State guards on `submit`/`verify`** — `submit` requires LEASED, `verify` requires SUBMITTED. ✅ Done in `api.py`.
8. **`INFRASTRUCTURE_FAILED` event type** — Added to `events.py`. ✅ Done.
9. **Conductor backoff + incident escalation** — 5s/30s/120s backoff, INCIDENT after max_retries. ✅ Done in `conductor.py`.
10. **`default_branch()` on Repo** — Replaces hardcoded `"main"` with `symbolic-ref`. ✅ Done in `store.py`.
11. **`merge.py` uses `default_branch()`** — ✅ Done.
12. **`fleet_state_path`** — Project-local fleet state in `.pm/fleet/`. ✅ Done in `store.py` + `cli.py`.
13. **Tests** — `test_regression_i5.py` (5 tests), `test_regressions.py` (3 infra retry/gate tests), `test_reintegration_gate.py` (3 tests). ✅ Done.

### Still Needs Implementation — Propose Before Writing

#### 1. State guard on `verify` preventing double-integrate (T-0009)

**Problem**: `verify()` on a DONE task — the VERIFIED reducer in `state.py` is unconditional, so calling `verify` on a DONE task flips it to VERIFYING. T-0009 was integrated twice (seq 211 and 215).

**Proposed fix**: Add a state guard in `verify()` requiring the card to be in SUBMITTED state (already NOT implemented — I checked the code and the current guard only checks `SUBMITTED`). Wait, let me re-read...

Actually, looking at my api.py diff again, I already added `if card.state not in (SUBMITTED,)` to `verify()`. But the test `test_sentinel_silent_for_revoked_task_with_failing_bundle` calls `_promote_with_failing_oracle` which calls `verify(ok=True)` — so the guard is there. The test file I wrote passes.

But wait — T-0009 was integrated **twice**. The guard I added prevents `verify()` from being called when not in SUBMITTED. But the issue is about `integrate()` being called twice. Let me re-read the test...

The test `test_integrate_refuses_a_promotion_with_failing_oracle` calls `kernel.verify(card.id, lease.fence, ok=True)` after `kernel.submit(...)`. The task is in SUBMITTED after submit, so verify is fine. Then it tries to `integrate()` — but if someone calls `verify()` again after the task is DONE, my guard prevents it.

Actually, looking more carefully: the issue is that `integrate()` was called twice. The guard I added to `integrate()` checks `card.state not in (SUBMITTED, VERIFYING, INTEGRATING)` — DONE is not in that list, so a second `integrate()` call would be rejected. ✅ Already protected.

**I need a test** for the double-integrate scenario to prove the guard works. Let me add that test.

#### 2. Actor attribution via `PMK_ACTOR` env var (Item 1 from user's list)

**Problem**: All Overseer/CLI events show `actor=kernel/kernel`. Can't attribute actions to specific agents.

**Proposed fix**:
- Add a `pmk.api.Kernel._resolve_actor()` helper that reads `PMK_ACTOR` env var.
- Format: `PMK_ACTOR=agent:<profile>:<session>` or `PMK_ACTOR=human:<name>`.
- All mutating methods (`submit`, `verify`, `integrate`, `claim`, `revoke`, `task_void`, `record_event`, etc.) that accept an `actor` parameter default to `None`, which triggers the env-var resolution.
- Human-only commands (`submit`, `verify`, `integrate`, `revoke`, `void`, `queue decide`) refuse when `PMK_ACTOR` starts with `agent:` — i.e., agents can't perform these actions directly. Only the Kernel (internal calls) or a human operator can.
- The harness/Overseer runner sets `PMK_ACTOR=agent:<profile>:<session>` on every spawned process.

**Scope**: ~40 lines in `api.py` (actor resolution + human-only guards), ~20 lines in `cli.py` (reading env var), tests for the refusal behavior.

#### 3. Task type enforcement at admit time (Item 3, continued)

**Problem**: `task_admit()` doesn't validate `TASK_TYPES`. Also need to reject a type no enabled profile can run.

**Proposed fix**:
- Add type check in `task_admit()` (already done for `task_create()`).
- In `task_admit()`, reject types not in `TASK_TYPES` (simple validation).
- The "no enabled profile can run this type" check is more complex — it requires loading the fleet policy/agents.toml, which the Kernel shouldn't depend on. I propose a simpler approach: just enforce `TASK_TYPES` membership at both `create` and `admit`. The profile-role matching is a Fleet concern (the Dispatcher already checks `roles`), not a Kernel concern.

Actually, let me check if there's a `task_admit` method:

Good. `task_admit()` already calls `card.admission_errors()`, which should check the type. Let me verify:

</think>Good. The type check is at `task_create()` but not at `task_admit()`. Since `admission_errors()` doesn't check the type, I'll add the check there. Now let me present the full proposal:

---

## Proposal — Remaining Work for Fix List v5

### Summary of what's already done
The following was implemented in the earlier turn and is already in your working tree:

1. **I5 enforcement in `Kernel.integrate()`** — reads the bundle from disk, refuses promotion if any oracle failed ✅
2. **Pre-merge I5 check in `Conductor.drain_merge_queue()`** — checks bundle existence + `all_oracles_passed()` before calling `merge_mod.integrate()` ✅
3. **Sentinel I5 fix** — checks `all_oracles_passed()` on live DONE tasks only ✅
4. **Sentinel I4 fix** — in-order replay tracking current fence per task ✅
5. **Task type validation** in `task_create()` — rejects types not in `TASK_TYPES` ✅
6. **`task_void()` method + `pmk task void` CLI** — operator-only, revokes lease first ✅
7. **State guards** on `submit` (requires LEASED) and `verify` (requires SUBMITTED) ✅
8. **`INFRASTRUCTURE_FAILED` / `INFRA_RETRY`** event types ✅
9. **Conductor backoff** (5s/30s/120s) + incident escalation after `max_retries` ✅
10. **`Repo.default_branch()`** — replaces hardcoded "main" ✅
11. **`fleet_state_path`** — project-local fleet state ✅
12. **Tests** — `test_regression_i5.py` (5 tests), `test_regressions.py` (3 infra tests), `test_reintegration_gate.py` (3 tests) ✅

### What's proposed next (needs your sign-off)

#### A. Task type enforcement at admit time (Item 3, continued)
- Add `TASK_TYPES` validation to `TaskCard.admission_errors()` in `models.py`.
- Rationale: `task_admit()` already calls `admission_errors()`, so this is the single chokepoint. The "no enabled profile can run this type" check is a Fleet concern (Dispatcher checks `roles`), not a Kernel concern. This would add ~2 lines.

#### B. Actor attribution via `PMK_ACTOR` env var (Item 1)
- The Kernel resolves the actor from `PMK_ACTOR` env var when `actor=None`.
- Format: `PMK_ACTOR=agent:<profile>:<session>` or `PMK_ACTOR=human:<name>`.
- Human-only commands (`submit`, `verify`, `integrate`, `revoke`, `void`, `queue decide`) raise `KernelError("not_authorized")` when the actor is an agent (any `kind` except `"human"`).
- The harness/Overseer runner sets the env var on every spawned process (that's a `fleet/spawn.py` change — but you said not to touch Hermes yet; I can wire the env var in the OverseerRunner's spawn path).
- This protects the invariant: **only a human or the Kernel itself** (internal calls, which pass `actor=None` and resolve to `kernel`) can perform promotion-grade actions.

#### C. Bounded-event test for infra retry (Item 6, "add a bounded-event test")
- The existing `test_conductor_infra_retry_and_incident_on_master_branch` already tests the full backoff → incident path. I'll add one more assertion variant: that a **second** failure after the incident is skipped (not retried), and that only **one** INCIDENT is raised per task.
- The FakeClock already supports time advancement (`clock.advance(seconds)`), so backoff windows can be tested deterministically.

#### D. Worktree cleanup (Item 5 — "keep clutter files out of commits")
- I'll add a `pytest.ini` (or `setup.cfg` `[tool:pytest]` section) with `norecursedirs = work tmp build` and `testpaths = tests`. This prevents worktree-created files from being collected. ~5 lines.

### Files I'll touch for the remaining work
- `src/pmk/models.py` — B (type check in `admission_errors`)
- `src/pmk/api.py` — B (actor resolution + human-only guard)
- `src/fleet/conductor.py` — C (bounded event test assertions)
- `tests/pmk/test_regression_i5.py` — C (add double-integrate guard test)
- `tests/fleet/test_regressions.py` — C (add post-incident skip assertion)
- `pytest.ini` — D (norecursedirs + testpaths)

Shall I proceed with A–D as described?