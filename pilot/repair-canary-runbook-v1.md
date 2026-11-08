# Live canary runbook — T-0146 (operator-executed)

**Purpose:** prove the repaired path with one real agent: claim → worktree → oracles → evidence bundle → merge → gate → DONE, and confirm the merge commit is authored by `umaws-pilot`.
**Why T-0146:** its oracle is deterministic and now satisfiable on main. T-0145 is void (`e08fa8d` already contains its change).
**Cost:** one task on a free-tier profile. No paid calls.

## Preconditions (all measured before this document was written)

| Check | Command | Expected |
|---|---|---|
| Suite | `./.venv/Scripts/python.exe -m pytest -q` | 532 passed, exit 0 |
| Pins | `./.venv/Scripts/pmk.exe pins check` | `ok: true`, 2 checked |
| Dispatch | `./.venv/Scripts/pmk.exe status` | `project_state: PAUSED`, `active_leases: 0` |
| Identity guard | `git config --get core.hooksPath` | `.githooks` (after A8 is applied) |
| Precheck | `grep precheck_satisfied agents.toml` | `true` |

## Procedure

1. **Pick the profile.** Use a free-tier profile already present; `kilo-auto` is the conservative choice. Record its id here: `________________`.
2. **Start the Console and note the time.**
   ```powershell
   .\start.ps1
   ```
3. **Dispatch exactly one task, supervised.**
   ```powershell
   .\.venv\Scripts\pmk.exe dispatch run
   ```
   Do not raise concurrency. Do not start a second run.
4. **Capture as it happens:**
   - `AGENT_STARTED` payload (pid, creation time, worktree, profile);
   - transcript under `.pm/fleet/logs/T-0146/`;
   - `ORACLE_RESULT` events and their exit codes;
   - the bundle under `.pm/evidence/`;
   - the merge commit and **its author identity**;
   - the final task state.
5. **Verify afterwards:**
   ```bash
   ./.venv/Scripts/pmk.exe task show T-0146
   git log -1 --format='%h %an <%ae> %s'
   ./.venv/Scripts/pmk.exe sentinel
   ```

## Abort immediately if any of these is true

- the worktree path is outside `work/`;
- the gate command differs from the recorded `gate_cmd`;
- the merge commit is authored by `Tiwa Pene <tiwaking@gmail.com>` (the guard should make this impossible);
- the same failure class repeats twice within one minute;
- the agent reports resolving `cna`/`pmk` from anywhere other than its own worktree.

Abort by stopping the Console; do not edit `.pm/` by hand.

## Success

- task `DONE`;
- oracle exit codes 0;
- bundle present and complete;
- merge commit author `umaws-pilot <umaws-pilot@localhost>`;
- no new `IDENTITY_ANOMALY`;
- sentinel **unchanged** from the recorded baseline (five I6 findings on T-0118/0119/0127/0129/0130 plus the I13 `status.md` view mismatch — these predate the repair and are not a canary failure).

## Record the result in D-69

Replace the PENDING line with: date, profile id, wall time, exit codes, merge sha, author identity, and any deviation from the expectations above. If it fails, record the failure class and whether it is a repair regression or a provider/environment issue — do not retry with a different profile in the same minute.
