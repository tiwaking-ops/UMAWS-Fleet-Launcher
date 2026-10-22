---
name: sentinel-check
description: Runs Kernel invariant checks to ensure the integrity of the event log, view projections, and security pins. Use when asked to 'check invariants', 'run sentinel', 'verify log chain', or 'is the log consistent?'. Automates 'pmk sentinel' and manual verification of I2, I8, and I13. Do NOT use for standard unit/integration tests (use pytest instead).
paths:
  - src/pmk/**
  - .pm/events/**
  - .pm/views/**
  - .pm/pins.sha256
  - .pm/constitution.md
  - .pm/policy.toml
---
# sentinel-check

## Critical
- **Kernel Exclusivity**: Never attempt to fix invariant violations by writing directly to `.pm/` files. All corrections must be made via `pmk` CLI or by appending a corrective event to the log.
- **Windows Environment**: Always execute via the project's venv. Use `.\.venv\Scripts\python.exe -m pmk.cli sentinel` if the `pmk` alias is not in the path.
- **Encoding**: If manually inspecting log files, they MUST be read with `utf-8-sig` to handle potential PowerShell BOMs.

## Instructions
1. **Environment Validation**: Verify the virtual environment exists and the project is installed in editable mode (`pip install -e .`). 
   - *Validation*: Run `python -c "import pmk; print(pmk.__file__)"` to ensure the kernel source is linked correctly.

2. **Run Sentinel**: Execute the automated invariant check.
   - `pmk sentinel` or `python -m pmk.cli sentinel`
   - *Validation*: Check the exit code. If non-zero, capture the specific invariant ID (e.g., I8, I13) that failed.

3. **Verify Pin Integrity (I8)**: If `pmk sentinel` reports a pin mismatch, manually compare the hashes.
   - Check `.pm/pins.sha256` content against the current SHA256 of `.pm/constitution.md` and `.pm/policy.toml`.
   - *Command*: `Get-FileHash .pm/constitution.md` (Windows PowerShell).
   - *Validation*: If they differ and no recent 'PolicyUpdate' event exists in `.pm/events/`, report a security violation.

4. **Verify View Projection (I13)**: Ensure the ledger and status views match the event log.
   - Run `pmk views rebuild --dry-run` to see if current projections in `.pm/views/*.json` would change.
   - *Validation*: If the dry-run indicates changes, the current views are stale/corrupt.

5. **Check Kernel Log Chain (I1)**: Ensure the event log in `.pm/events/` is strictly append-only and has no gaps in sequence IDs.
   - Inspect the last 5 entries of the latest JSONL file in `.pm/events/`.
   - *Validation*: Verify `seq_id` is strictly increasing by 1.

## Examples
### User says: "Verify if the kernel state is still valid."
1. **Action**: Run `python -m pmk.cli sentinel`.
2. **Action**: Check `.pm/pins.sha256` against `Get-FileHash` for policy files.
3. **Result**: 
   - Sentinel Output: `[PASS] I1: Log Integrity, [PASS] I8: Policy Pins`.
   - Manual Check: `I13 View Projection matches current log head at seq 452`.
   - Response: "Kernel invariants verified. Log chain is intact (seq 452), and policy hashes match pins."

### User says: "I think someone edited the policy file manually."
1. **Action**: Run `pmk sentinel`.
2. **Result**: 
   - Sentinel Output: `[FAIL] I8: Pin mismatch for .pm/policy.toml`.
   - Response: "Invariant I8 Violation detected: The hash for .pm/policy.toml does not match the pinned value in .pm/pins.sha256. This indicates a manual edit outside of the Kernel flow."

## Common Issues
- **ModuleNotFoundError: No module named 'pmk'**: The project is not installed in editable mode. Fix: `.\.venv\Scripts\python.exe -m pip install -e .` from the project root.
- **PermissionError on .lock files**: A sidecar process (Console or Fleet Dispatcher) is currently writing to the kernel. Fix: Stop the `python -m console.app` or any active `pmk` tasks before running sentinel if a hardware lock is held.
- **UnicodeDecodeError**: If reading `.pm/views/status.json` fails, it likely has a UTF-8 BOM. Fix: Use `encoding='utf-8-sig'` in the open() call.