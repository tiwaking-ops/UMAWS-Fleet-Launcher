---
paths:
  - src/pmk/**
  - .pm/**
---

# Kernel Writing & State Invariants

- **Event Authority**: Every state change must be an event append in `src/pmk/events.py`. 
- **No Direct Writes**: Never write to `.pm/tasks/` or `.pm/views/` directly. Use `Kernel.record_event()`.
- **Hash Chain**: Maintain the I1 hash chain in `EventLog`. Verify with `pmk sentinel`.
- **Standard Library Only**: `src/pmk/` must not have external dependencies (no `FastAPI`, `pydantic` here).
- **Serialization**: Use `pmk.events.canonical_json` for hashing and storage.