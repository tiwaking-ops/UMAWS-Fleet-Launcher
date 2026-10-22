---
paths:
  - src/fleet/**
---

# Fleet Spawning & Recovery

- **Argv Only**: Every launch must be an `argv` list. Use `plat.resolve_executable` for node/npm shims.
- **Recovery Ladder**: Implement L0-L4 in `src/fleet/recover.py`. 
  - L1: Resume session on next profile.
  - L2: Fresh session + handoff note.
- **Harness Ownership**: The harness owns the `Worktree` and the `.pmwork/ORDER.md` file.
- **Clean Cleanup**: Only kill processes where `pid` AND `creation_time` match (via `plat.process_info`).