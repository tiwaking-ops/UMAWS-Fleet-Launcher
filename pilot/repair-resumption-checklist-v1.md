# Dispatch resumption checklist — repair v1

Status as of 2026-11-08. Tick only what is verified; an unticked box is a blocker, not an oversight.

| # | Item | Evidence | Status |
|---|---|---|---|
| 1 | Environment isolation landed for oracle, gate, worker, retry, Overseer | `55f3f46`; 6 tests in `tests/fleet/test_worktree_env.py`; 5 failed before the change | **done** |
| 2 | Env invariant enforced for new spawns | `tools/check_subprocess_env.py`; 7 reviewed exceptions | **done** |
| 3 | Rules index reports the truth about the corpus | warnings 428 → 46; 0 same-line duplicates; 31 cross-doc + 15 xrefs pinned | **done** |
| 4 | Coverage accounts for all 66 corpus files | `rule_files: 69` (66 + 3); `--check` passes on main and in a worktree | **done** |
| 5 | G-001 oracle strengthened | `docs/PDD.md`; `tests/test_rules_baseline.py` | **done** |
| 6 | T-0145 voided with a reason | `pmk task show T-0145` → `VOID` | **done** |
| 7 | T-0146 oracle satisfiable on main and in a worktree | dry-run worktree: index 0, coverage 0, both payloads ok | **done** |
| 8 | Pipeline commit identity pinned | `tests/fleet/test_identity_guard.py`; merge path `-c user.name=umaws-pilot` | **done** |
| 9 | Interactive identity logging enabled | `.githooks/pre-commit` present; **`core.hooksPath` not yet set** (needs A8) | **pending** |
| 10 | Already-satisfied pre-lease guard | `tests/fleet/test_precheck.py`; `agents.toml [fleet] precheck_satisfied = true` | **done** |
| 11 | Decision records drafted | `pilot/drafts/decisions-d62-plus.md`; **ratification (A9) outstanding** | **pending** |
| 12 | Decision gap report | `docs/reports/decision-gaps-2026-11-08.md` | **done** |
| 13 | Suite green | 532 passed, exit 0 | **done** |
| 14 | Sentinel at the recorded baseline | 5 × I6 + 1 × I13, unchanged from before the repair | **done (red, recorded)** |
| 15 | Live canary reaches DONE | `pilot/repair-canary-runbook-v1.md` | **pending — operator** |
| 16 | Dispatch resumed | operator action after 15 | **pending — operator** |

## Order for resuming

1. `git config core.hooksPath .githooks` (A8).
2. Run the canary (item 15). Record D-69.
3. Ratify D-62…D-68 (A9); leave D-69 as completed by the canary.
4. Start the Console and resume dispatch. Record the start time in the checkpoint.
5. Keep the eleven extra worktrees until a separate, evidence-based decision; `pilot/repair-worktree-census-v1.md` is the basis.
