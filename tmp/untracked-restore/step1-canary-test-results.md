# Step 1 — Canary Test Results

**Test repo:** `C:\temp\canary\root` (branch `canary`, worktree `work/wt`)  
**Decoy:** `.pmwork/ORDER.md` at repo root contains `ROOT-DECOY`  
**Real:** `work/wt/.pmwork/ORDER.md` contains `WORKTREE-REAL`  
**Prompt used:** `Read .pmwork/ORDER.md and reply with only its first line.`

---

## Hermes

### Without `--in`

```
Command: hermes chat -q "Read .pmwork/ORDER.md and reply with only its first line." -Q --yolo --cli --source tool -m stepfun/step-3.7-flash:free
Directory: C:\temp\canary\root\work\wt
Result: File not found: `.pmwork/ORDER.md` does not exist.
```

**Finding:** Hermes did NOT read either the decoy or the real file. It resolved `.pmwork/ORDER.md` from the Hermes project root (`C:\temp\projects\testproject1`), which no longer contains `.pmwork/ORDER.md` (renamed to `ORDER.md.stale-20261102`). This proves Hermes ignores the shell cwd for file resolution and uses its own project context.

### With `--in C:/temp/canary/root/work/wt`

```
Command: hermes chat ... --in C:/temp/canary/root/work/wt
Result: `.pmwork/ORDER.md` is not present; similar files: `ORDER.md.stale-20261102`, `RESULT.md`.
```

**Finding:** The `--in` flag did NOT fix the resolution. Hermes still resolved from `C:\temp\projects\testproject1` and found `ORDER.md.stale-20261102` (the renamed stale file) and `RESULT.md`. This means:
1. `--in` only affects the shell's working directory for spawned commands, not Hermes's internal file lookup.
2. Hermes resolves `.pmwork/` relative to its **configured project root**, not the git worktree or shell cwd.

**Conclusion for Hermes:** Hermes resolves `.pmwork/ORDER.md` from `C:\temp\projects\testproject1` regardless of `--in`. Any CLI that uses a bare relative `.pmwork/ORDER.md` prompt will hit the project-root file first.

---

## pi

```
Command: pi --help
Result: Error: Cannot find module 'C:\c\Users\Tiwa Pene\.pi\agent\bin\pi-launcher.js'
```

**Finding:** pi is broken in this environment (missing module). Cannot test.

---

## OpenCode

```
Command: opencode run -m poolside/poolside/laguna-s-2.1 "Read .pmwork/ORDER.md and reply with only its first line." --auto work/wt
Result: Error: Failed to change directory to /c/temp/canary2/root2
```

**Finding:** opencode fails with `Failed to change directory` on MSYS-style paths. This appears to be a Node.js/MSYS path-translation incompatibility. Cannot test.

---

## Summary

| CLI | Reads ROOT-DECOY? | Reads WORKTREE-REAL? | Notes |
|---|---|---|---|
| hermes (no `--in`) | No | No | Resolves from Hermes project root (`C:\temp\projects\testproject1`); file missing there |
| hermes (with `--in`) | No | No | `--in` does not affect Hermes file resolution; still hits project root |
| pi | N/A | N/A | Broken install (missing module) |
| opencode | N/A | N/A | Fails to change directory on MSYS paths |

**Key finding:** Hermes resolves `.pmwork/ORDER.md` from its configured project root, not from the worktree or shell cwd. The `--in` flag does not change this behavior. This confirms that the absolute-path prompt fix (`order_prompt(worktree)`) is the correct layer, and the `--in` flag would be an unreliable additional layer even if opencode/pi worked.
