# UMAWS Fleet Project Context

Kernel-lite coordination system with a Fleet Dispatcher and FastAPI Console.

## Build & Test
- **Environment**: `py -3.12 -m venv .venv` · `.\.venv\Scripts\python.exe -m pip install -e .` (editable install required for `pmk` CLI)
- **Tests**: `pytest -q` (runs ~150 tests across Kernel, Fleet, and QuotaGate)
- **Console**: `start.ps1` or `python -m console.app` (binds to `127.0.0.1:8765`)
- **Demo**: `python pilot/demo_one_click.py` (E2E lifecycle with fake CLI)

## Architecture
- **Kernel** (`src/pmk/`): Sole writer of state. Manages append-only JSONL event log in `.pm/events/`. Rebuilds `State` and `Views` from the log.
- **Fleet** (`src/fleet/`): Process supervision. `Dispatcher` assigns tasks to `Profiles`; `Harness` manages `Worktree` and `Oracles`.
- **Console** (`src/console/`): FastAPI view layer. Thin wrapper over `pmk.api` and `FleetState`.
- **QuotaGate** (`gateway/quotagate/`): Hierarchical quota engine (RPM, TPM, RPD) with timezone-aware resets.

## Key Invariants
- **I2 (Kernel Only)**: Agents never write to `.pm/` directly; use `pmk` CLI or `pmk.api`.
- **I5 (Oracles Decide)**: No task is promoted to `DONE` without a passing `gate_cmd` and evidence bundle in `.pm/evidence/`.
- **I8 (Pinned Policy)**: `.pm/constitution.md` and `.pm/policy.toml` are hashed in `.pm/pins.sha256`.
- **I13 (Views as Projections)**: `.pm/views/` (ledger, status, queue) must equal the projection of the log.

## Development Patterns
- **Platform**: Native Windows. Use `src/pmk/plat.py` for sidecar locks (`.lock`) and process-tree kills.
- **Spawning**: Always use `argv` lists. Never use shell strings. Use `plat.resolve_executable` to peel npm `.cmd` shims.
- **Errors**: Read all human-written files with `utf-8-sig` to handle PowerShell BOMs.





<!-- caliber:managed:model-config -->
## Model Configuration

Recommended default: `claude-sonnet-4-6` with high effort (stronger reasoning; higher cost and latency than smaller models).
Smaller/faster models trade quality for speed and cost — pick what fits the task.
Pin your choice (`/model` in Claude Code, or `CALIBER_MODEL` when using Caliber with an API provider) so upstream default changes do not silently change behavior.

<!-- /caliber:managed:model-config -->

<!-- caliber:managed:sync -->
## Context Sync

This project uses [Caliber](https://github.com/caliber-ai-org/ai-setup) to keep AI agent configs in sync across Claude Code, Cursor, Copilot, and Codex.
Configs update automatically before each commit via `caliber refresh`.
If the pre-commit hook is not set up, run `/setup-caliber` to configure everything automatically.
<!-- /caliber:managed:sync -->
