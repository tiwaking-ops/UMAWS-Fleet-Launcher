# UMAWS Fleet - OpenCode Context

This project is a Kernel-lite multi-agent coordination system.

## Quick Actions
- **Briefing**: `pmk brief --role overseer` is your primary authority for tasks.
- **Status**: `pmk status` or `pmk fleet status` for current coordination state.
- **Tasks**: Claim tasks via `CLAIMED` events in the log (or `pmk` CLI).

## Rules
- **The Kernel is the writer**: Request transitions through `pmk`; do not edit `.pm/` files directly.
- **Oracles Decide**: Use `gate_cmd` in `docs/PDD.md` to verify work.
- **Windows native**: Use sidecar `.lock` files for atomic ops.

@./CLAUDE.md
@./pilot/STATE.md





