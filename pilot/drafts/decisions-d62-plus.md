# DRAFT decision records D-62 … D-69

> **DRAFT — not ratified. Do not cite as a decision.**
> Drafted under P3.2 of `proposal-umaws-problems-and-issues-repair-v1` from evidence measured
> on 2026-11-08. The operator ratifies these into `pilot/decisions.md` (approval A9); this file is
> the review copy. D-69 stays blank until the live canary has actually run.

Format: `D-<n> | <date> | <who> | <decision> | <alternatives> | <what it leaves untested>`

---

**D-62** | 2026-11-08 | operator (approved the plan) + Buffy/Codebuff (implemented) | **Environment isolation is one rule for every spawned process: the worktree under test goes first on `PYTHONPATH`.** `src/fleet/runenv.py` builds the environment; `harness.run_command` (oracles), `merge.integrate` (gate), `Harness._env` (workers, retry, restart) and the Overseer all use it. The gate's inline copy was removed. Six tests in `tests/fleet/test_worktree_env.py`; the oracle and worker tests failed on `ebe46ce` before the change. | (a) Oracle-only, as the scratch patch had it — leaves agents judging their own tooling by main's code; (b) scrubbing `PYTHONPATH` entirely — breaks genuinely external packages; (c) document-only — the trap stays. | Real-CLI behaviour under the new worker environment: unit tests prove resolution and credential preservation, not that every adapter is happy. That is the live canary (D-69).

**D-63** | 2026-11-08 | Buffy/Codebuff (diagnosed and implemented) | **The rules index is judged against a pinned baseline, not a count.** `docs/rules/index.baseline.json` pins: 0 within-document duplicate warnings, the exact 17 anchor ids behind the 31 legitimate cross-document collisions, the exact 15 unresolved `case-N.M` xrefs, and the documented `tables: 0` scope limit. `tests/test_rules_baseline.py` asserts set equality, so adding or removing a warning both require a reviewed baseline update. Surplus warning, since the report quoted 413/15: **428 total = 413 duplicate + 15 xrefs**, of which **382 were one anchor registered twice on one line** — a generator defect, now fixed. | Keep `documents >= 66` only (report F4's minimum); or hard-fail on 31 headings that legitimately repeat; or edit the corpus to remove real headings. | The 31 cross-document anchors remain "first wins"; a consumer that needs the second definition gets the first. The AsciiDoc table limitation is unchanged.

**D-64** | 2026-11-08 | Buffy/Codebuff (implemented) | **`counts.rule_files` means "corpus files present", and declarations are reported separately.** `rule_files` now scans `.md` and `.adoc` recursively (69 files: 66 corpus + 3 non-corpus), with `rule_files_declaring_paths: 3` and `rule_files_matching: 3`. This is what makes T-0146's oracle (`rule_files >= 66`) satisfiable at all; before the change the tool reported 3 because it scanned only top-level `.md`. | Redefine the oracle instead (task cards are Kernel-owned, so that needs a new card); or count only files that declare `paths:` and accept that T-0146 can never pass. | Coverage of *paths* is unchanged (66/66 covered, 0 uncovered). The three declaring files are the only ones that constrain paths; 66 files are present but silent about scope — a real corpus gap now visible instead of hidden.

**D-65** | 2026-11-08 | Buffy/Codebuff (executed under authority A3) | **T-0145 is voided; T-0146 is the proof task.** T-0145's change was integrated manually as `e08fa8d`, so an implement card on that base fails `NO_CHANGES`. T-0146's oracle now passes on main after D-64, so it is the task that can demonstrate the repaired path end to end. | Re-dispatch T-0145 (fails NO_CHANGES); void both (loses the end-to-end proof); complete T-0146 without a dispatch (does not exercise the harness). | T-0145's attempt history keeps its original failure record; voiding does not exonerate the harness retroactively. T-0146's live run remains the canary.

**D-66** | 2026-11-08 | operator (confirmed) + Buffy/Codebuff (recorded) | **Q-076/Q-077/REC-01/REC-02 are recorded as a thin but authorised class-K action.** The operator confirms they made the `.pm/policy.toml` edit at `2026-11-07T18:38:48Z`, one second before the mismatched `PINS_CHECKED`. The record remains thin: key 1 carried no diff, key 2 carried only `{"choice":"ratify"}`, the pin re-record followed within a second, and the human actor labels differ between seq 3116 and 3117. `pmk pins check` is `ok: true` and `worktree.reclaim_on_reap = true` is in force. | Treat Q-077 as invalid and require a full re-decision (F8); or leave it unrecorded (the state this repair found). | Whether Q-077 satisfies the project's own class-K standard is now a judgement for the operator, not an open evidence question. The T-0150 canary verdict (OQ-6) is still `unknown`.

**D-67** | 2026-11-08 | Buffy/Codebuff (recorded, implemented) | **Provenance is recorded, not rewritten.** Four commits (`e08fa8d`, `ebe46ce`, `82f6be1`, `9893d94`) carry `Tiwa Pene <tiwaking@gmail.com>` while neighbouring commits use `umaws-pilot`. No history is amended. The pipeline now commits with an explicit `-c user.name=umaws-pilot -c user.email=umaws-pilot@localhost` and records `IDENTITY_ANOMALY` when the effective identity differs; `.githooks/pre-commit` logs (never blocks) an agent-context commit under the human identity when `UMAWS_PIPELINE=1`. | Rewrite the four commits (violates the no-amend constraint and destroys the evidence); block every human commit (obstructs the operator); log only (does not prevent recurrence). | Which session produced those four commits remains **unknown**; the hook covers the future and the pipeline, not attribution of the past.

**D-68** | 2026-11-08 | Buffy/Codebuff (classified) + operator (approved the classification) | **Working-tree drift is reconciled without deletion.** `pilot/decisions.md` was CRLF churn hiding four real records (D-58…D-61); it is normalised to LF and those records are committed. `agents.toml` carries the operator's 100 → 10 concurrency change and new `pi-orca` profiles. 59 scratch artifacts moved to `quarantine/2026-11-08/` with a manifest; `pytest_junit.xml` and `pi-test.txt` restored to committed bytes. `.pm/events/2026-11-07.jsonl` and `.pm/views/*` are deliberately **not** committed: they are live Kernel state. `pmk sentinel` is red at baseline (I6 on T-0118/0119/0127/0129/0130, I13 on `status.md`) and that is recorded, not repaired — fixing I6 would require rewriting the ledger. | Commit everything in one cleanup commit (mixes evidence with WIP); `git checkout` the drift (loses D-58…D-61 and the concurrency change); delete the scratch files (destroys evidence). | The eleven extra worktrees git knows and `pmk` does not are still present. Disposition is deferred; `pilot/repair-worktree-census-v1.md` is the basis for a separate decision.

**D-69** | 2026-11-08 | _to be completed by the operator after the live canary_ | **Canary result and dispatch resumption: PENDING.** Preconditions: suite green, identity guard active, precheck enabled, pins `ok`. Procedure: `pilot/repair-canary-runbook-v1.md`. | Resume dispatch without a canary (the previous week's failure mode: the pipeline was declared fixed twice without a live run). | Everything the canary has not yet measured: real adapters under the pinned environment, provider behaviour, and the merge path with a real agent's output.

---

## Ratification checklist for the operator

- [ ] D-62 accepted (environment rule)
- [ ] D-63 accepted (index baseline)
- [ ] D-64 accepted (coverage semantics)
- [ ] D-65 accepted (T-0145 void / T-0146 proof)
- [ ] D-66 accepted (Q-077 recorded as thin)
- [ ] D-67 accepted (provenance recorded, guard added)
- [ ] D-68 accepted (drift reconciliation)
- [ ] D-69 left open until the canary
