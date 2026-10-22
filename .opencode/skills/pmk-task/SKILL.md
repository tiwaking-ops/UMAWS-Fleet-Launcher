---
name: pmk-task
description: Manages Kernel-lite task cards using the pmk CLI. Use for creating, updating, or querying tasks. Prevents direct file manipulation in .pm/.
---

# PMK Task Management

## Critical
- **I2 (Kernel Only)**: NEVER write directly to `.pm/` files (e.g., manual JSON edits). Always use the `pmk` CLI or `pmk.api`.
- **I5 (Oracles)**: Any task creation must include a valid `goal_ref` that maps to an entry in the system registry.
- **I8 (Pins)**: Ensure `.pm/pins.sha256` is updated if the policy context changes during task creation.

## Instructions

1. **Verify Goal Reference**: Ensure the task `goal_ref` exists in your current workspace context. If adding a new goal, verify it aligns with `.pm/constitution.md`.
   - Validation: Run `python -m pmk.cli goal list` and confirm the `goal_ref` is present.

2. **Execute Task Creation**: Use the `pmk.cli` module to register the task. Do not construct JSON objects manually.
   - Command: `python -m pmk.cli task create --goal-ref <GOAL_ID> --scope <SCOPE_DESCRIPTION> --oracle <ORACLE_NAME>`
   - Note: Use `src/pmk/plat.py` utilities if wrapping this in sub-processes to ensure proper Windows path/process handling.

3. **Post-Creation Validation**: Verify the event was appended to the log.
   - Step: Run `ls .pm/events/` and check the latest file timestamp.
   - Validation: Ensure the output projection for the new task is reflected in `.pm/views/ledger.json`.

## Examples

**User**: "Create a task for the new file integration in `src/fleet` under goal `G-001`."

**Actions taken**:
1. `python -m pmk.cli goal list` (Verify G-001 exists).
2. `python -m pmk.cli task create --goal-ref G-001 --scope "src/fleet/adapters/file_handler.py" --oracle "harness-v1"`
3. `cat .pm/views/ledger.json | grep "file_handler"` (Confirm projection updated).

**Result**: Task registered, event appended, and view projection updated.

## Common Issues

- **'OSError: [Errno 13] Permission denied' on .pm/events/log.jsonl**:
  - Cause: A `.lock` file remains from a crashed process.
  - Fix: Check `src/pmk/plat.py` logic. Manually remove `.pm/.lock` if `pmk` is not running.

- **'PolicyViolationError' during task create**:
  - Cause: The proposed task scope conflicts with `.pm/policy.toml`.
  - Fix: Inspect `.pm/policy.toml`. If the change is intended, you must hash the update: `python -m pmk.cli policy update`.

- **'ModuleNotFoundError: No module named pmk'**:
  - Cause: Running from the wrong directory or virtual environment not activated.
  - Fix: Ensure you have run `.".venv\Scripts\activate"` and that you are in the project root.