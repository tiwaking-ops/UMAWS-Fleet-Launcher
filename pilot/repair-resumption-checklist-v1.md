# Dispatch resumption checklist — repair v1

Status as of 2026-11-10. Tick only what is verified; an unticked box is a blocker, not an oversight.

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
| 13 | Suite green | Clean-worktree gate exit 0 at `712ca1a` and `09cca85`; the current self-contained base `53871a7` runs the full `python -m pytest -q` to exit 0 in a detached worktree (`tmp/clean-head-full2.log`); `cna.engine.loop`/`pmk` resolve inside the gate worktree | **done** |
| 14 | Sentinel at the recorded baseline | 5 × I6 + 1 × I13, unchanged from before the repair | **done (red, recorded)** |
| 15 | Live canary reaches DONE | **PASS — T-0190, T-0191 and T-0196.** Each ran under `kilo-auto`/`kilo`, exited 0, passed the gate `pytest -q`, and integrated: T-0190 fence 157 → merge `0edc0dc` (`EB-T-0190-157`), T-0191 fence 158 → `c7fcdf3` (`EB-T-0191-158`), T-0196 fence 159 → `951d1ee` (`EB-T-0196-159`). T-0189 remains the historical gate failure recorded by D-69 | **done** |
| 16 | Dispatch resumed | A10 remains the operator's decision; no `pmk project resume` is recorded and the project remains `PAUSED` | **blocked — operator decision (A10)** |

**Current state (2026-11-10, HEAD `53871a7`).** `pmk status`: project `PAUSED`; 212 cards — 155 VOID, 43 DONE, 12 READY, 1 VERIFYING, 1 LEASED; 2 active leases; 0 open queue items; chain 3630 events. Task state: T-0208, T-0209 and T-0212 `DONE`; T-0210 `VERIFYING` (fence 162); T-0211 `LEASED` (fence 163); 12 READY cards.

## Order for resuming

1. ~~`git config core.hooksPath .githooks` (A8).~~ **done 2026-11-09.**
2. ~~Run the canary (item 15). Record D-69.~~ **T-0189 failed at the gate; later canaries T-0190, T-0191 and T-0196 all reached DONE.**
3. ~~Ratify D-62…D-69 (A9).~~ **done 2026-11-09; D-69 is ratified as FAIL.**
4. **Do not resume dispatch.** The committed base was repaired and made self-contained at `53871a7` (full clean-worktree `pytest -q` exit 0), and the fresh canaries passed. A10 remains the operator's decision; no resume is recorded.
5. Keep the extra worktrees until a separate, evidence-based decision; `pilot/repair-worktree-census-v1.md` is the basis.
6. Current state: HEAD `53871a7`; T-0208/T-0209/T-0212 DONE, T-0210 VERIFYING, T-0211 LEASED; project `PAUSED` with 2 active leases. T-0189's operator-only disposition (D-72) is historical and no longer blocks the canary.
