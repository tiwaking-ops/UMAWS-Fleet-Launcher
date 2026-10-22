# G3 spot-read — the Fleet's spawn/kill code

**For:** the operator's 15–30 minute review.  **Status:** G3 is **HELD**
until this is done and D-19/D-20 are ratified or reverted.

The pilot's own risk register says this is where it matters most
(fleet amendment R-F9: *"Bootstrap fleet code is the most privileged
ungoverned code"*).  These are the functions that can, on this machine,
**start a process, kill a process tree, and write to git**.

There are five places to look.  Each entry says what the function does, what
the dangerous failure mode would be, and where to see that it is handled.

---

## 1. `src/pmk/plat.py` — the process primitives

### `same_process(pid, creation_time)` — line 348

The gate on every kill.  A pid alone is not an identity: Windows recycles
pids, so a stale pid can name a *different* program.

**What to check:** that it refuses when the creation time differs, and
that it refuses when the creation time is unknown (rather than assuming a
match).

### `spawn(argv, cwd, log_path, env)` — line 382

**What to check:** that `argv` is a list and never a shell string; that
`creationflags` is `CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP`; that
stdout and stderr are merged into one log; that the child's `Popen` handle
is kept (the exit code depends on it).

### `kill_tree(pid, creation_time)` — line 433

**What to check:** that it calls `same_process` **first** and refuses on a
mismatch; that it uses `taskkill /PID <pid> /T /F` so children die too;
that it never kills a pid the Dispatcher did not spawn.

---

## 2. `src/fleet/spawn.py` — the Fleet's use of them

### `spawn_slot(...)` — line 180

**What to check:** that the executable is resolved with
`plat.resolve_executable` (so an npm `.cmd` shim is peeled to its real
target and never run through `cmd.exe`, which would re-parse the
arguments); that the cwd is the worktree; that the log path is per
process.

### `kill_slot(slot)` — line 292, `slot_alive(slot)` — line 303

**What to check:** that both go through `plat.kill_tree` / `plat.same_process`
and therefore carry the pid **and** the creation time.

---

## 3. `src/pmk/api.py` — the Kernel's lease rules

### `claim(...)` — line 316

**What to check:** that it refuses a task that is not READY, one whose
dependencies are not DONE, one whose attempts are exhausted, and — the
fleet-specific one — **one whose write scope overlaps a task that already
holds a lease** (D-L6).  That last rule is what stops two agents from
writing the same file.

### `submit(...)` — line 413

**What to check:** that it compares the submitted fence with the **task's**
current fence and **quarantines** a stale submission rather than
rejecting it (invariant I4); that it refuses a bundle with no oracle
results or no `constitution_hash`; that the bundle is written to
`.pm/evidence/EB-<task>-<fence>/bundle.json`.

### `revoke(...)` — line 394, `integrate(...)` — line 474

**What to check:** that revocation **bumps the fence**, so work in flight
against the old lease becomes stale; that `integrate` refuses a fence that
is not current.

---

## 4. `src/fleet/merge.py` — writing to git

### `commit_worktree(...)` — line 51

**What to check:** that it stages **only the declared write scope**, not
`git add -A`.  This was a real bug: `git add -A` staged the harness's own
`.pmwork/ORDER.md`, which made two leases conflict on the order file, and
it would have committed work the scope check had already flagged.

### `integrate(...)` — line 82

**What to check:** that it refuses when the scope check reports a
violation; that it runs the **gate command** on the merged tree before
fast-forwarding `main`; that the fast-forward is `git merge --ff-only`,
which refuses rather than overwriting local changes.

---

## 5. `src/fleet/harness.py` — where oracles decide

### `_finish(...)` — line 312

**What to check:** that the acceptance commands are run **by the harness**,
not believed from the worker; that a non-zero exit does not become a
success; that the fix-round budget is bounded.

### `_recover(...)` — line 469

**What to check:** that a failure enters the ladder rather than being
retried in a loop; that the profile-level consequences (cooldown, disable,
circuit breaker) are applied **fleet-wide**, not per project.

---

## The two questions worth more than the reading

1. **Can anything here run outside the worktree?**  The harness's
   `disable_hooks` points every worktree's `core.hooksPath` at an empty
   directory, so git runs no hook — including Caliber's pre-commit hook,
   which would otherwise make an LLM call and stage context files on every
   commit (measured, spike S4).
2. **Can anything here kill something it should not?**  The chain is
   `kill_slot` → `plat.kill_tree` → `plat.same_process`, and the last one
   compares the pid *and* the process creation time.

---

## After the read

G3 also needs:

* the **handover test** (H6): start an OpenCode session, read
  `pmk brief --role overseer`, kill the session, start a fresh one, and
  confirm it continues from the briefing alone.  The briefing is
  deterministic from the log alone — that part is tested — but the
  end-to-end handover with a real session has **not** been run.
* `pmk sentinel` clean — **yes**, it is.
* every Phase 1 commit tagged `bootstrap/*` — done, see
  `pilot/class-k-ratification.md`.
* the ratification or reversal of D-19 and D-20 — see
  `pilot/class-k-ratification.md`.
