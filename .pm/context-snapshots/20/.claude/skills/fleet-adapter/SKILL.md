---
name: fleet-adapter
description: Adds or modifies Fleet profiles and adapters in agents.toml. Handles argv_new, argv_resume, and capability flags. Use when user says 'add profile', 'new model adapter', or 'update hermes config'. Ensures family hints match guess_family logic. Do NOT use for modifying Kernel event logs or QuotaGate rules.
paths:
  - agents.toml
  - src/fleet/adapters/*.py
  - src/fleet/config.py
---
# fleet-adapter

## Critical
- **Argv as Lists**: `argv_new` and `argv_resume` MUST be lists of strings. Never use a single shell string. This is required for `subprocess.run` safety on Windows.
- **UTF-8-SIG**: Always read/write `agents.toml` using `utf-8-sig` encoding to preserve or handle PowerShell BOMs correctly.
- **No Direct .pm/ Writes**: Modifications should only happen in `agents.toml` or `src/fleet/adapters/`. Do not touch the `.pm/` state directory.
- **Path Resolution**: Use `pmk.plat.resolve_executable` if referencing an npm-based CLI (like `npx` or `cline`) to ensure the correct `.cmd` shim is found on Windows.

## Instructions

1. **Locate and Parse `agents.toml`**
   - Find `agents.toml` in the project root or `src/fleet/`.
   - Verify it exists before proceeding. If missing, check `src/fleet/defaults.toml` for a template.

2. **Identify or Create the Adapter**
   - Check `src/fleet/adapters/` for existing implementations (e.g., `openai.py`, `llama_cpp.py`).
   - If creating a new adapter, inherit from the base adapter class in `src/fleet/adapters/base.py`.
   - Validation: Ensure the adapter class implements `format_request` and `parse_response`.

3. **Define the Profile in `agents.toml`**
   - Add a new `[[profile]]` entry with these required fields:
     - `name`: Kebab-case string (e.g., `hermes-3-local`).
     - `adapter`: Matching the filename in `src/fleet/adapters/` without `.py`.
     - `family`: Must match `guess_family()` logic (usually `openai`, `anthropic`, or `llama`).
     - `argv_new`: List starting with the executable, e.g., `["python", "-m", "adapter.module"]`.
     - `argv_resume`: List for continuing interrupted tasks.
   - Validation: Verify `argv_new` contains the placeholder `{{worktree}}` if the process requires a workspace path.

4. **Map Capability Flags**
   - Set `capabilities = ["tool_use", "vision"]` based on what the model/adapter supports.
   - Ensure `gate_cmd` is defined if the profile requires an Oracle check before completion (I5 Invariant).

5. **Verify Family Hints**
   - Check `src/fleet/logic.py` (or equivalent) to see how `family` strings are mapped to internal behavior.
   - Validation: Run `python -m fleet.check_config` (if available) to verify the new profile is reachable.

6. **Test the Profile**
   - Run a smoke test using the fleet CLI: `pmk fleet spawn --profile <new-profile-name> --task "hello world"`.
   - Verify logs in `.pm/events/` show the `TASK_ASSIGNED` event with the correct profile metadata.

## Examples

**User says**: "Add a profile for llama-3-8b running via llama-server on port 8080"

**Actions taken**:
1. Open `agents.toml` with `utf-8-sig`.
2. Add the following block:
```toml
[[profile]]
name = "llama-3-8b-local"
adapter = "llama_cpp"
family = "llama"
capabilities = ["tool_use"]
argv_new = ["curl", "-X", "POST", "http://localhost:8080/v1/chat/completions"]
argv_resume = ["curl", "-X", "POST", "http://localhost:8080/v1/chat/completions"]
```
3. Verify `src/fleet/adapters/llama_cpp.py` exists.
4. Run `pytest tests/fleet/test_config.py` to ensure no syntax errors in TOML.

**Result**: New profile available for `pmk fleet` commands.

## Common Issues

- **Error: 'The system cannot find the file specified'**: 
  - **Fix**: The first element in `argv_new` is likely a script/shim. Wrap it in `pmk.plat.resolve_executable()` or ensure it's in the PATH. Use `["cmd", "/c", "... "]` only as a last resort.
- **Error: 'Family mismatch in guess_family'**: 
  - **Fix**: Check `src/fleet/adapters/factory.py`. Ensure the `family` string in `agents.toml` matches one of the recognized keys in the model factory mapping.
- **Error: 'UnicodeDecodeError' when reading agents.toml**:
  - **Fix**: Use `encoding='utf-8-sig'` in the `open()` call to handle the Byte Order Mark often added by Windows tools.