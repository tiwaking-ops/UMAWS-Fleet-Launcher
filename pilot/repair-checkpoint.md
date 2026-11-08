# Repair checkpoint — proposal-umaws-problems-and-issues-repair-v1

- **Phase:** P0 — freeze, baseline, tree reconciliation
- **Status:** done (awaiting G-B review)
- **HEAD:** `ebe46ce` · **Tag:** none yet
- **Approvals in force:** A1 (plan approved 2026-11-08)
- **Measured baseline:** tests **507**, exit **0**; index warnings **428** (413 duplicate: 382 same-line, 31 cross-document; 15 unresolved xrefs); `coverage.counts.rule_files` **3**; corpus **66** `.adoc`; worktrees `pmk` **15** vs git **27**; untracked **121**
- **Last action:** baseline captured in `.pmwork/repair-v1/`; drift classified and quarantined; `pilot/decisions.md` normalised to LF with D-58…D-61 preserved; worktree census written
- **Next action:** commit P0, then P1.1 — create `src/fleet/runenv.py` and the six tests, run them red:

```
./.venv/Scripts/python.exe -m pytest -q tests/fleet/test_worktree_env.py
```

- **Open decisions:** A3 (`pmk task void T-0145`), A4 (dry-run worktree), A9 (ratify D-62+)
- **Red evidence:** none yet (P1 writes `.pmwork/repair-v1/p1-red.txt`)
- **Surprises:**
  - `pilot/decisions.md` was CRLF churn **plus 11 real lines** (D-58…D-61 uncommitted); normalised, content kept.
  - `pmk sentinel` is red at baseline: I6 on five historical tasks, I13 on `status.md`. Recorded, not fixed (would require rewriting the ledger).
  - `git worktree list` knows 26 worktrees; `pmk` state knows 15.
- **Constraints still in force:** no push; no `.pm/policy.toml` or pins edits; no queue decisions; no deletions; no dispatch start.
