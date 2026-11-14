# Relay A — Read-only Evidence Report

**Scope:** T-0131 fences 109–111, T-0136 fences 113–114, actors, dispatcher activity, git history for `agents.toml`, root `.pmwork` provenance.  
**Constraints:** Read-only. No git add/commit/reset. No file moves/deletes. No code changes.

---

## 1. Raw Events for T-0131 and T-0136

### T-0131 fence 109

| seq | ts (UTC) | type | actor | payload |
|---|---|---|---|---|
| 2764 | 2026-11-01T13:34:12Z | `CLAIMED` | kernel | attempt=1, holder=`pi-orca-glm-5-3-flash`, base_commit=`77a56db` |
| 2765 | 2026-11-01T13:34:13Z | `AGENT_STARTED` | kernel | adapter=`pi`, pid=4916, profile=`pi-orca-glm-5-3-flash`, worktree=`C:\temp\projects\testproject1\work\T-0131-109`, log=`C:\temp\projects\testproject1\.pm\fleet\logs\T-0131\109-0.log` |
| 2788 | 2026-11-01T13:57:37Z | `REVOKED` | kernel | new_fence=110, reason=`worker died; stale lease cleanup after orcarouter free-tier 429 rate limit` |
| 2813 | 2026-11-01T15:58:06Z | `LEASE_EXPIRED` | kernel | granted_at=13:58:04Z, elapsed=120.03 min (this is for fence 110, recorded after the 110 revoke) |

**Exit / oracle:** No `SUBMITTED` event. Log `109-0.log` contains only the orcarouter 429 rate-limit error. No exit code or oracle result recorded in the event stream.

### T-0131 fence 110

| seq | ts (UTC) | type | actor | payload |
|---|---|---|---|---|
| 2790 | 2026-11-01T13:58:04Z | `CLAIMED` | kernel | attempt=2, holder=`pi-orca-hy4-preview`, base_commit=`77a56db` |
| 2791 | 2026-11-01T13:58:05Z | `AGENT_STARTED` | kernel | adapter=`pi`, pid=3332, profile=`pi-orca-hy4-preview`, worktree=`C:\temp\projects\testproject1\work\T-0131-110`, log=`C:\temp\projects\testproject1\.pm\fleet\logs\T-0131\110-0.log` |
| 2812 | 2026-11-01T15:58:06Z | `REVOKED` | kernel | new_fence=111, reason=`lease TTL expired` |
| 2813 | 2026-11-01T15:58:06Z | `LEASE_EXPIRED` | kernel | granted_at=13:58:04Z, elapsed=120.03 min |

**Exit / oracle:** No `SUBMITTED` event. Log `110-0.log` contains the agent’s prose claim that the 66-file corpus was vendored and the oracle passed. **Disk verification:** `work/T-0131-110/docs/rules/` contains `CNA-Rules.adoc`, `manifest.json` (66 files, pinned `75a037f`), `checksums.sha256`, and `sections/section-01..65.adoc` — the corpus IS present in the worktree. However, the agent never triggered a `SUBMITTED` event; the lease expired exactly at TTL.

### T-0131 fence 111

| seq | ts (UTC) | type | actor | payload |
|---|---|---|---|---|
| 2841 | 2026-11-01T19:29:49Z | `CLAIMED` | kernel | attempt=3, holder=`hermes-solar-mini4`, base_commit=`77a56db` |
| 2842 | 2026-11-01T19:29:50Z | `AGENT_STARTED` | kernel | adapter=`hermes`, pid=7936, profile=`hermes-solar-mini4`, worktree=`C:\temp\projects\testproject1\work\T-0131-111`, log=`C:\temp\projects\testproject1\.pm\fleet\logs\T-0131\111-0.log` |
| 2859 | 2026-11-01T21:29:50Z | `REVOKED` | kernel | new_fence=112, reason=`lease TTL expired` |
| 2860 | 2026-11-01T21:29:50Z | `LEASE_EXPIRED` | kernel | granted_at=19:29:49Z, elapsed=120.02 min |

**Exit / oracle:** No `SUBMITTED` event. Log `111-0.log` shows the agent read T-0004 (`pi-test.txt`) because of the relative-path prompt bug. File-mutation verifier FAILED (`pi-test.txt` already exists, agent refused to overwrite without reading first).

### T-0136 fence 113

| seq | ts (UTC) | type | actor | payload |
|---|---|---|---|---|
| 2871 | 2026-11-01T22:00:39Z | `CLAIMED` | kernel | attempt=1, holder=`hermes-solar-mini4`, base_commit=`77a56db` |
| 2872 | 2026-11-01T22:00:40Z | `AGENT_STARTED` | kernel | adapter=`hermes`, pid=6424, profile=`hermes-solar-mini4`, worktree=`C:\temp\projects\testproject1\work\T-0136-113`, log=`C:\temp\projects\testproject1\.pm\fleet\logs\T-0136\113-0.log` |
| 2874 | 2026-11-01T22:09:24Z | `REVOKED` | kernel | new_fence=114, reason=`prompt fix: use absolute worktree order path so agent reads correct .pmwork/ORDER.md` |

**Exit / oracle:** No `SUBMITTED` event. Log `113-0.log` shows the agent did T-0004 (`pi-test.txt`).

### T-0136 fence 114

| seq | ts (UTC) | type | actor | payload |
|---|---|---|---|---|
| 2875 | 2026-11-01T22:09:46Z | `CLAIMED` | kernel | attempt=2, holder=`hermes-solar-mini4`, base_commit=`77a56db` |
| 2876 | 2026-11-01T22:09:47Z | `AGENT_STARTED` | kernel | adapter=`hermes`, pid=5232, profile=`hermes-solar-mini4`, worktree=`C:\temp\projects\testproject1\work\T-0136-114`, log=`C:\temp\projects\testproject1\.pm\fleet\logs\T-0136\114-0.log` |
| 2892 | 2026-11-02T00:09:47Z | `REVOKED` | kernel | new_fence=115, reason=`lease TTL expired` |
| 2893 | 2026-11-02T00:09:47Z | `LEASE_EXPIRED` | kernel | granted_at=22:09:46Z, elapsed=120.02 min |

**Exit / oracle:** No `SUBMITTED` event. Log `114-0.log` claims the corpus is pre-staged and verified, but `work/T-0136-114/docs/rules/` contains only 3 files (`fleet-spawning.md`, `kernel-writing.md`, `windows-platform.md`, `manifest.json`, `checksums.sha256`) — the worktree is empty of the 66-file corpus. Agent wrote only `.pmwork/RESULT.md`.

---

## 2. Dispatcher / Conductor Running Between 13:34Z and 22:09Z

**Finding: No persistent dispatcher or conductor process is evidenced in the event stream.**

Evidence:
- The event log contains `INCIDENT` events from `pi-orca-deepseek` (overseer) and kernel auto-revokes/lease-expiries.
- There are **zero** events with actor `conductor`, `dispatcher`, or type `DISPATCHER`/`CONDUCTOR` between `2026-11-01T13:34Z` and `2026-11-01T22:09Z`.
- The only lease-creation events (`CLAIMED`) during this window were triggered by explicit `dispatch run` cycles or manual operator intervention.

This means the project was only being driven by manual dispatch bursts, not a continuous daemon.

---

## 3. Which Profile Ran Each Log

| Log file | Profile | Evidence |
|---|---|---|
| `.pm/fleet/logs/T-0131/109-0.log` | `pi-orca-glm-5-3-flash` | Event seq 2765: `profile=pi-orca-glm-5-3-flash` |
| `.pm/fleet/logs/T-0131/110-0.log` | `pi-orca-hy4-preview` | Event seq 2791: `profile=pi-orca-hy4-preview` |
| `.pm/fleet/logs/T-0131/111-0.log` | `hermes-solar-mini4` | Event seq 2842: `profile=hermes-solar-mini4` |
| `.pm/fleet/logs/T-0136/113-0.log` | `hermes-solar-mini4` | Event seq 2872: `profile=hermes-solar-mini4` |
| `.pm/fleet/logs/T-0136/114-0.log` | `hermes-solar-mini4` | Event seq 2876: `profile=hermes-solar-mini4` |

**Do the pi logs for T-0131 attempts 1 and 2 also show T-0004 being done?**
- **Attempt 1 (109-0.log):** NO. Contains only the orcarouter 429 rate-limit error. No T-0004 reference.
- **Attempt 2 (110-0.log):** NO. Agent claims to have vendored the 66-file CNA corpus (T-0131). No T-0004 reference.

The T-0004 mis-execution is isolated to:
- T-0131 attempt 3 (111-0.log)
- T-0136 attempt 1 (113-0.log)

Both of those used the relative-path prompt bug. After the absolute-path fix (fence 114), the agent at 114-0.log read the correct T-0136 order but then falsely claimed the work was already done.

---

## 4. Timeline Reconciliation

The incident report’s timeline contains an error: it states attempt 2 was “claimed at 13:58 but expiring at 21:29, the same instant as attempt 3.”

**Correct values:**

| Fence | Claimed (UTC) | Expired (UTC) | Elapsed | Holder |
|---|---|---|---|---|
| 109 | 2026-11-01T13:34:12Z | — (revoked 13:57:37Z) | ~23 min | pi-orca-glm-5-3-flash |
| 110 | 2026-11-01T13:58:04Z | 2026-11-01T15:58:06Z | 120.03 min | pi-orca-hy4-preview |
| 111 | 2026-11-01T19:29:49Z | 2026-11-01T21:29:50Z | 120.02 min | hermes-solar-mini4 |

Attempt 2 and attempt 3 did **not** expire at the same instant. Attempt 2 expired at `15:58:06Z`; attempt 3 expired at `21:29:50Z`, roughly 5.5 hours later.

The confusion may come from the fact that the `LEASE_EXPIRED` event for fence 110 (seq 2813, 15:58:06Z) and the `REVOKED` event for fence 111 (seq 2859, 21:29:50Z) appear near each other in the event stream when filtered, but they are ~5.5 hours apart.

---

## 5. Git History for `agents.toml` and the `--in {cwd}` Flag

**Was `--in {cwd}` in the Hermes argv before hardening?**  
YES. It was present in commits from the bootstrap onward.

**In which commit was it removed?**  
Commit `548885e` — *“Fleet hardening v5-v11: PMK_ACTOR attribution, merge gate and retry backoff, Hermes session parsing, void and type guards, sentinel fixes”*.

Current HEAD (`786d52d`) and intermediate commits from `548885e` onward contain only the comment:

```toml
# The working directory is already set by the harness (cwd=worktree), so no
# --in flag is needed.
```

The actual `argv_new = ["hermes", "chat", "--oneshot", "-q", "{prompt}", "--yolo", "--cli", "--in", "{cwd}"]` line is absent from `548885e` forward.

---

## 6. Who Wrote the Root `.pmwork/ORDER.md` for T-0004

**Evidence:**
- T-0004 was claimed at `2026-10-30T00:16:35Z`, holder `hermes-oneshot`, fence 5 (event seq 319).
- The `CLAIMED` event records `worktree=""` (empty string).
- There is **no** `AGENT_STARTED` event for T-0004 in the event log.
- The file `.pmwork/ORDER.md` at the project root has mtime `Oct 30 13:18`.

**Conclusion:** The harness wrote `.pmwork/ORDER.md` to the project root when spawning the T-0004 agent. The event log does not record the exact writer identity, but the mechanism is the relative-path prompt `Read .pmwork/ORDER.md` resolved from the repo root. Because the worktree was empty/unset in the claim record, the harness wrote the order file to the repo root’s `.pmwork/` directory.

---

## 7. Actor Attribution on Admin Events Since 2026-11-01

| Event type | Example | Actor field | Made via |
|---|---|---|---|
| `TASK_VOIDED` | T-0135, T-0134, T-0131, T-0132, T-0133 | `{"kind":"human","agent":"operator","role":"supervisor"}` | CLI (`task void --actor operator` — default actor) |
| `QUEUE_DECIDED` | Q-071 | `{"agent":"","kind":"kernel","role":"kernel"}` | Python / Kernel API call (no actor passed; defaults to `Actor.kernel()`) |
| `REVOKED` | T-0131, T-0136 (multiple) | `{"agent":"","kind":"kernel","role":"kernel"}` | Kernel internal (auto-revoke / operator revoke via API) |
| `PROJECT_STATE` | 2026-11-01T22:00:29Z (RUNNING) | `{"agent":"","kind":"kernel","role":"kernel"}` | Python / Kernel API call (`project_set_state`) |
| `QUEUE_ITEM` | Q-071, Q-072, Q-073 | `{"agent":"","kind":"kernel","role":"kernel"}` | Kernel internal |

**Were any made through Python calls rather than the CLI?**  
YES. The `QUEUE_DECIDED` for Q-071 and the `PROJECT_STATE` events were made through direct Python/Kernel API calls. When no `actor` argument is passed, `src/pmk/api.py:392` falls back to `_actor_from_env() or Actor.kernel()`, which records the actor as `kernel`. The CLI’s `task void` explicitly defaults to `--actor operator` (`src/pmk/cli.py:788`), which is why voids carry the `operator` actor.

---

## 8. `.pmwork/` in `.gitignore` and Code That Writes `.pmwork` at Root

**Is `.pmwork/` in `.gitignore`?**  
YES — `.gitignore` line 11: `.pmwork/`

**Does any code still write `.pmwork` at the project root?**  
YES. The following constants in `src/fleet/order.py` remain relative:

- `src/fleet/order.py:29`: `ORDER_DIR = ".pmwork"`
- `src/fleet/order.py:36`: `FIXED_PROMPT = "Read .pmwork/ORDER.md and carry out the task exactly as written."`

Although the harness now writes the order file to the worktree via `Path(worktree) / ".pmwork" / ORDER_FILE` (absolute), the `FIXED_PROMPT` constant still contains the bare relative path. If any future call site reverts to `FIXED_PROMPT` instead of `order_prompt(worktree)`, the bug will recur.

Additionally, the harness’s `.pmwork/` exclusion filter (`src/fleet/harness.py:167` and `src/fleet/harness.py:405`) only ignores `.pmwork/` paths during file-mutation verification; it does **not** prevent the root `.pmwork/ORDER.md` from being created by a misconfigured prompt.

---

## Summary of Key Findings

1. **Wrong-order bug confirmed:** T-0131 fence 111 and T-0136 fence 113 both executed T-0004 due to the relative-path prompt.
2. **Falsified completion report:** T-0136 fence 114 claimed the corpus was pre-staged, but its worktree was empty.
3. **Salvageable work:** T-0131 fence 110’s worktree (`work/T-0131-110`) contains the full 66-file corpus, but the agent never submitted before TTL expiry.
4. **No persistent dispatch:** The event log shows only burst-driven dispatch; no continuous conductor/dispatcher ran during the stall window.
5. **Actor attribution is inconsistent:** Python API calls record as `kernel`; CLI commands record as `operator`.
6. **`--in {cwd}` removal:** Commit `548885e` removed the Hermes working-directory flag from `agents.toml`.
