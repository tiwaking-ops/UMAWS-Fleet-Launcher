# Dispatch resumption checklist — repair v1

Status as of 2026-11-09. Tick only what is verified; an unticked box is a blocker, not an oversight.

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
| 9 | Interactive identity logging enabled | `.githooks/pre-commit` present; `core.hooksPath=.githooks` (A8 applied 2026-11-09) | **done** |
| 10 | Already-satisfied pre-lease guard | `tests/fleet/test_precheck.py`; `agents.toml [fleet] precheck_satisfied = true` | **done** |
| 11 | Decision records drafted and ratified | `pilot/decisions.md` D-62…D-69; `pilot/drafts/decisions-d62-plus.md` (A9, 2026-11-09) | **done** |
| 12 | Decision gap report | `docs/reports/decision-gaps-2026-11-08.md` | **done** |
| 13 | Suite green | Clean-worktree gate exit 0 at `712ca1a` (`tmp/clean-base-1794224200.log`) and again at `09cca85` (`tmp/clean-base-1794225200.log`); `cna.engine.loop`/`pmk` resolve inside the gate worktree | **done** |
| 14 | Sentinel at the recorded baseline | 5 × I6 + 1 × I13, unchanged from before the repair | **done (red, recorded)** |
| 15 | Live canary reaches DONE | No canary run: T-0189 is READY with attempts 1/1 and only the operator can void it, so the Phase 11 preflight (exactly one READY card) cannot pass (D-72) | **blocked — operator action required** |
| 16 | Dispatch resumed | A10 remains the operator's decision; the repaired base has no PASS canary yet; project remains `PAUSED` | **blocked** |

## Order for resuming

1. ~~`git config core.hooksPath .githooks` (A8).~~ **done 2026-11-09.**
2. ~~Run the canary (item 15). Record D-69.~~ **done; T-0189 FAILED at the gate.**
3. ~~Ratify D-62…D-69 (A9).~~ **done 2026-11-09; D-69 is ratified as FAIL.**
4. **Do not resume dispatch.** Repair the committed base (resolve the dangling `tests/test_transport.py` reference), then run a fresh canary; A10 only after a PASS.
5. Keep the extra worktrees until a separate, evidence-based decision; `pilot/repair-worktree-census-v1.md` is the basis.
6. Repair landed at `09cca85` with a green clean-base gate; the canary is blocked on T-0189's operator-only disposition (D-72).
