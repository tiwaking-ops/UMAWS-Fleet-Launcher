# Repair checkpoint — proposal-umaws-problems-and-issues-repair-v1

- **Phase:** P4 — verification, task closure, handover
- **Status:** **complete except the operator-run live canary and ratification**
- **HEAD:** see tag `repair-p4`
- **Tags:** `repair-p0` … `repair-p4` (local only, annotated)
- **Approvals in force:** A1 (plan), A2 (local commits), A3 (T-0145 void), A4 (dry-run worktree), A5 (precheck key), A6 (PDD oracle), A7 (quarantine), A8 (hooks path) — A8 applied at resumption, not before
- **Measured now:** tests **532**, exit **0**; index warnings **46** (0 same-line, 31 cross-document, 15 xrefs); `coverage.counts.rule_files` **69** (66 corpus + 3 non-corpus), `rule_files_declaring_paths` **3**; corpus **66** `.adoc`; pins `ok: true`; T-0145 **VOID**
- **Last action:** coverage portability fix (ignores `*.egg-info`, which made `--check` pass on main and fail in a worktree); T-0146 oracle verified in a dry worktree; canary runbook and resumption checklist written
- **Next action:** the operator applies `git config core.hooksPath .githooks`, runs `pilot/repair-canary-runbook-v1.md`, then ratifies D-62…D-68
- **Open decisions:** A9 (ratify drafts), A10 (resume dispatch)
- **Red evidence:** `.pmwork/repair-v1/p1-red.txt` (5 failures on `ebe46ce`), `p1-green.txt`, `p2-green.txt`, `p3-green.txt`
- **Surprises / recorded limits:**
  - `pilot/decisions.md` was CRLF churn **plus** D-58…D-61; normalised, content kept.
  - `pmk sentinel` is red at baseline: 5 × I6 historical, 1 × I13 view mismatch. Unchanged by the repair and not fixable without rewriting the ledger.
  - `git worktree list` knows 26 worktrees; `pmk` state knows 15; none removed.
  - Coverage counted `src/umaws_fleet.egg-info`, so its drift check could never pass in a fresh worktree — caught by the P4 dry run, not by the report.
  - `docs/reports/decision-gaps-2026-11-08.md` finds **duplicate decision ids D-35…D-40** and **missing D-51** in the historical log. Recorded, not rewritten.
- **Constraints still in force:** no push; no `.pm/policy.toml` or pins edits; no queue decisions; no deletions; dispatch remains paused until the operator's canary.
