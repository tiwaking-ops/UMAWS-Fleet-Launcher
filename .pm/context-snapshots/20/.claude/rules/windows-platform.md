---
paths:
  - "**/*"
---

# Windows Platform Constraints

- **Sidecar Locking**: Always use `<file>.lock` for file locks. Windows forbids appending to locked data bytes.
- **UTF-8-SIG**: Read JSON/TOML with `utf-8-sig` to ignore PowerShell UTF-8 BOMs.
- **Path Limits**: Repo is at `C:\temp\projects\`. Keep worktree paths shallow under `work/`.
- **PowerShell**: Use `-NoProfile -ExecutionPolicy Bypass` when spawning shells for legacy paths.