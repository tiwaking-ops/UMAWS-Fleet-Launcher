# Assessment — fleet-launcher-repair-completion-v2.md

**Date:** 2026-11-10
**Subject:** `docs/reports/fleet-launcher-repair-completion-v2.md` (report mtime 2026-11-10 08:46:49)
**author_llm (subject):** Buffy/Codebuff — executor of record for the repair programme
**assessor_llm:** MiMo-V2.6-Flash Free (opencode) — independent assessment; authored none of the content under assessment (no self-assessment)
**Method:** every testable claim re-measured directly from git, the `pmk` kernel, the event log, evidence bundles, and live tool runs — not taken from the report's account
**State as of assessment:** HEAD `951d1ee`, chain verifies 3,558 events, project `PAUSED`, leases 0, push 0 ahead / 121 local, dirty 14 modified + 337 untracked, 51 git worktrees, sentinel `ok=true` findings 0

## Verdict

**VERIFIED WITH CORRECTIONS.** Every hard claim the assessor tested reproduced exactly. Defects: one documentation gap (§3 inventory omits the commits carrying the report's headline fixes), snapshot staleness (a fourth canary landed after the report was written), and one honestly-labelled item (H4) whose live failure the report under-cross-references. Accept as the record of its snapshot, subject to the addendum listed below.

## Confirmed — re-measured independently

| Claim | Measurement |
|---|---|
| T-0191 canary DONE, fence 158 | `state=DONE attempt=1 fence=158` ✓ |
| Events seq 3534–3537 | `SUBMITTED → ORACLE_RESULT → INTEGRATING → INTEGRATED`, all fence 158 ✓ |
| Merge `c7fcdf3` | parents `ce22591` + `e1b5da7`, author `umaws-pilot` ✓; delta `ce22591..c7fcdf3` = 1 file, 5 insertions only — no scope leakage ✓ |
| H6 implementation | `src/fleet/merge.py`: `_gate_output()` + `_persist_gate_output()` write `bundle.gate_output` on success **and** failure paths (exit-127 exception included); 10 hits across src+tests ✓ |
| H6 regression test | `tests/fleet/test_merge_queue.py:149 test_gate_output_is_persisted_in_the_bundle`, parametrized over both outcomes ✓ |
| Bundle `EB-T-0191-158` non-empty `gate_output` | `cmd=pytest -q`, `exit=0`, `ok=True`, no failed tests, 17 stdout-tail lines ending `[100%]`, empty stderr — matches report §6 line for line ✓ |
| H1 absent | `tests/pmk/test_lease_admission.py` → False ✓ |
| H3 unwired | `def reconcile` at `src/fleet/dispatcher.py:520`, 0 callers in `src/fleet` + `src/console` ✓ |
| H4 unimplemented | `src/fleet/harness.py:767` writes `sorted(models)` with no non-empty guard ✓ |
| H7 unimplemented | `pmk-merge-` → 0 hits in `src/pmk` ✓ |
| H5 partial/pass | live run of `tools/check_subprocess_env.py`: exit 0, "7 allowlisted" ✓ |
| Cards T-0192–T-0195 | all `PROPOSED`, priorities 10/20/30/40, created seq 3538–3541; all 4 precheck JSONs and 4 patch artifacts present ✓ |
| DoD-1 / DoD-2 evidence | `tmp/clean-base-1794224200.log` and `tmp/clean-base-1794225200.log` present; combined-collection log fresh (07:41), exit 0 independently re-measured ✓ |
| PAUSED; no READY cards; no push; sentinel | all confirmed ✓ |
| §8 remediation copies byte-identical | `docs/reports/` vs `pilot/` copies → identical ✓ |

## Corrections

1. **§3 commit inventory is incomplete; `e302119` is never cited.** The status line and §4 headline "H2 conftest split fixed" rest on commit `e302119`, which appears nowhere in the report (grep: NOT CITED). §3 stops at `09cca85`, omitting both headline fixes (`e302119` H2, `ce22591` H6) and the merge commits. The table is a slice inventory, not the inventory its title claims. This is the one substantive record-keeping defect.
2. **A fourth canary landed after the report was written and is not in it.** During assessment: `T-0196` created → claimed at fence 159 → gate `ORACLE_RESULT` ok → INTEGRATED seq 3558 → DONE, merge `951d1ee`. DoD-6 is now proven twice (T-0191 and T-0196); the report claims only one. Its success is under-reported, not over-reported.
3. **Snapshot figures have moved** (no "as of" timestamp in the report): chain 3,537 → 3,558; completion HEAD `c7fcdf3` → `951d1ee`; dirty tracked 8+2 → 14 modified (351 total); worktrees 44 → 51; local commits 114 → 121, still 0 pushed. §1's "active leases 0" was briefly false mid-assessment (T-0196's lease).
4. **H4 re-proven live a third time, by the evidence canary itself.** T-0196 seq 3552: `{"served_models":[],"source":"none","profile":"kilo-auto"}`. The report labels H4 *Unimplemented* honestly, but both canaries it cites as DoD-6 proof emitted broken provenance on the way; §6 should cross-reference this explicitly.

## On §9 Self-audit

Consistent with independent verification: no push/force/reset in history, all merges two-parent with `umaws-pilot` identity, CP-4 still a draft (D-72 not ratified), canary claims are event-backed rather than prose. No claim in the report was contradicted on substance — only the omissions and staleness above.

## Required addendum to the subject report

1. Cite `e302119` (H2) and `ce22591` (H6) in §3.
2. Add T-0196 (`951d1ee`) as second DoD-6 proof.
3. Add an "as of" timestamp, or re-measure chain / dirty / worktree figures.
4. Cross-reference H4's live failure (seq 3552) in §6 alongside the canary success it accompanied.

---
*assessor_llm: MiMo-V2.6-Flash Free (opencode). Author of record for the subject report remains Buffy/Codebuff. This assessment is independent of the author and based solely on re-measured git, ledger, bundle, and tool state. Stored uncommitted; promotion/commit is an operator decision.*
