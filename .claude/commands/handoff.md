# /handoff — Generate a handoff document for this project

## Purpose

Whenever you type `/handoff` (or just `handoff`), this command writes a `HANDOFF.md` file in the repo root that captures the current state of the work so another session (or you) can pick up exactly where this one left off.

## Instructions

1. **Determine context availability.**
   - If this session has prior conversation context (i.e., you can see the conversation above this point), use it as a primary source.
   - If this is a fresh session with no prior conversation context, say this explicitly in the first line of your response to the user, then fall back to repo state only (git log, git status, file contents). Label the handoff as "repo-only" in that case.

2. **Write `HANDOFF.md` in the repo root.**
   - Overwrite it if it already exists.
   - The file must contain these sections, in this order:

     ### Goal of the work
     One sentence describing what this session is trying to accomplish. If the work was completed, state that explicitly.

     ### What is DONE
     - Bullet list of completed items.
     - Include the commit hash(es) for each. Use `git log --oneline -10` to find them.
     - Include file paths that were created or modified.

     ### What is IN PROGRESS
     - If nothing is in progress, write "Nothing — all items are complete or blocked."
     - Otherwise, list each in-progress item with a brief description and which file(s) it touches.

     ### What is NEXT
     - List the next steps that should be taken if this session were to continue.

     ### Decisions made
     - List each decision with a one-line rationale. These are points the user may want to override.
     - Format: `- **Decision:** <what> — <why>`

     ### Known problems
     - List any issues, blockers, or caveats. Include error messages or file/line references where possible.

     ### Key file paths
     - A short table of the most important files for this work, with their relative paths from the repo root.

     ### Commands to verify the current state
     - A code block with the exact commands someone should run to confirm the state described in this document.
     - E.g., `git log --oneline -3`, `pytest -q`, `pmk sentinel`, etc.

3. **Verify the file was written.**
   - Run `ls HANDOFF.md` to confirm it exists on disk.
   - Print its full path (absolute) and its full contents to the user.

4. **If you do not understand a command or are blocked**, ask the user. Never invent a plausible-sounding reply.

5. **Never say "handoff noted" or claim completion without evidence.**
   - You must show the file path, confirm it exists with `ls`, and display its contents.
