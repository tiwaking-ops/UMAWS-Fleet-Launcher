# Recovery Ladder with Real CLIs — Results

**Status:** **L4 exercised** (real failure), **L3 exercised** (tight threshold), **L2, L1, L0 observed but not excercised on real CLI** (see Defect).

**Author:** OpenCode (via `pilot/ladder-real-cli.py`). **Date:** 2026-10-23.  
**Authorised:** operator, "2. Ladder. APPROVED".

---

## Summary of what was run

Three scenarios in a scratch repository (outside the pilot) against real agents:

| Scenario | Profile(s) | What happened | Ladder step exercised |
|---|---|---|---|
| **l4** | opencode | QUOTA failure, 3600 s cooldown, `attempt=1 >= attempts_max=1` | **L4: BLOCKED** + queue item `Q-001` |
| **l3** | opencode | QUOTA failure, `max_restarts_per_task=0`, first failure triggers L3 | **L3: revocable**, fence bumped 1→2, task returned READY |
| **recover** | opencode → kilo | opencode fails QUOTA → escalation → kilo real success, work submitted | **L1 chosen**, but see Defect below |

---

## Artifact observations

### l4: L4 — attempts_exhausted

The failure path with a real agent that really fails is correct and clean:

- Real QUOTA failure from opencode's live free-tier exhaustion.
- `PROFILE_COOLING: profile=oc-live reason=quota exhausted: cooling for 3600s`.
- `step=L4 reason=attempts exhausted (1/1)`.
- Lease revoked, worktree quarantined.
- Task went **BLOCKED** with a queue item `Q-001` → `'recommended': 're-scope the task', 'safe_default': 'escalate to the human'`.
- **No** fence bump (L3 does that; L4 revokes instead).

### l3: L3 — revoke/bump/quarantine

- `max_restarts_per_task=0` → the failure immediately hit L3.
- Event trace shows `REVOKED`, `QUARANTINED`, `agent_failed step=L3`.
- **Fence was bumped** `1→2` (verified in state after the run).
- Task returned to **READY**; the lease field `restart_count=0` per spec.
- **No queue item** (L3 is not terminal).

### recover: real recovery (the surprising defect)

The recovery path worked end-to-end: a real agent failed, and work moved to another real agent without human intervention. But

❗ **Defect found**: the ladder chose **L1** and emitted `AGENT_RESUMED`, yet the receiving agent got *no handoff note* (`## Handoff none`), and the event labelled it `resume`.

**Why**:  
`recover.decide()` uses `adapter.caps.can_resume` (opencode can resume → L1 chosen).  
`harness.py:377`: `resume = bool(profile.supports_resume() and run.session)`.  
The opencode profile has `argv_resume=["opencode", "run", "{prompt}", "--continue"]` **in my test**, but for kilo I set `argv_resume=[]` — checking that case:

The receive profile in my ladder test was **kilo-real** which has `argv_resume = []`. Let me check the actual test I wrote:

```toml
argv_resume = []
```

Yes — kilo had **no** `argv_resume`. So:

1. The opencode failure → L1.
2. `_restart_on` is called with profile `kilo-real`.
3. `_restart_on` tries to resume → `resume = profile.supports_resume() and run.session`.
4. `profile.supports_resume()` is `bool([])` = **False**.
5. Mode = `"new"` (not `"resume"`), but the event still says `AGENT_RESUMED` with `mode="new"`.
6. `spawn_slot` is called with `mode="new"` and **no code writes the handoff note** (only L2 does).
7. The second agent receives `## Handoff none` in its order file.

**The ladder chose L1 (based on adapter caps) to satisfy the operator's requirement FR3 ("resume on a different model")**, but **because the receiving profile had no `argv_resume`, that resume was impossible and degraded to a fresh start without a handoff note**. The event `AGENT_RESUMED` is misleading; the worker did **not** resume a session.

**This is a genuine defect**: the step chosen by the ladder does not necessarily match what is executed.

---

## L0 — Network only, unexercised on real CLI

The ladder only takes L0 for `NETWORK` class failures. There is no live CLI that reliably produces a `NETWORK` failure (connection refused, timeout). The fake CLI fixture has a network pattern, but that's a fixture.  
**L0 remains unexercised on a real CLI.**

---

## What this does not establish

1. **Multiple attempts** — I set `attempts_max=3` for the recover scenario but the failure was permanent (QUOTA), so it never needed retries.
2. **All profiles** — only opencode and kilo were tested. Cline, hermes, pi are untouched by this battery.
3. **No resume within L1** — when `argv_resume` is empty, L1 goes to `"new"` mode without a handoff. Whether that's acceptable is a question, but it's not the operator's intent when they say "resume on a different model".

---

## Recommendation

1. The recovery ladder with a real CLI **can close** — it successfully re-routed work from a real, permanently failing agent to a working agent via a real lease in a real worktree. That path is proven.
2. The **missing handoff note** when `argv_resume` is empty (even though L1 was chosen) should be fixed: either (a) the ladder should choose L2 when `argv_resume` is absent, or (b) `_restart_on` should write a handoff note when mode is "new".

**Which fix?** — This is a consequential change to recovery behaviour. This document records the finding; the fix is **parked pending human adjudication**.

---

## Evidence bundles

Each scenario leaves its evidence in the scratch repository:

| Scenario | Evidence path |
|---|---|
| recover | `scratch/.pm/evidence/EB-T-0002-1/bundle.json` |
| l3 | `scratch/.pm/evidence/EB-T-0002-1/bundle.json` |
| l4 | `scratch/.pm/evidence/EB-T-0002-1/bundle.json` |

The scratch directories may be re-run; bundles will differ only in timestamps and sha256, not in structure. Bundle schema:

```json
{
  "task": "T-0002",
  "fence": 1,
  "base_commit": "...",
  "outputs": [{"path": "src/greet.py", "sha256": "..."}],
  "diff_scope_check": {"changed": ["src/greet.py"], "violations": [], "ok": true},
  "oracle_results": [{"cmd": "python check.py", "exit": 0, "ok": true}],
  "constitution_hash": "..."
}
```

---

## Decision D-41

See appended to `pilot/decisions.md`.