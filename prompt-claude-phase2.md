Two-part task. Do Part A, then Part B, in that order. No provider calls anywhere. Do not start the Console or the Dispatcher with real profiles (hold agents.toml aside or use only the fake CLI profile). Read-only for everything not named below. Commit each change separately and record it in decisions.md (next free D numbers) and STATE.md.

PART A: fix two defects found in the completion report (commit a93da888)

A1. D-A2: the dispatcher ignores pilot/STOP and the Console auto-starts dispatch.
- Dispatcher.tick() must check pilot/STOP and dispatch_paused before any claim, assignment or spawn. With STOP present: zero FLEET_ASSIGNED and zero AGENT_STARTED events.
- The Console must start with dispatch PAUSED by default. Dispatch begins only on an explicit action (the Run button, `pmk dispatch run`, or a clearly named config flag set by the operator). Say in decisions.md that this default is a proposal for the operator to confirm.
- Regression tests (fake CLI only): STOP present means nothing is dispatched; removing STOP resumes dispatch; Console startup with READY tasks and an enabled fake profile produces no events until Run.

A2. D-A1: FLEET_ASSIGNED is recorded before the claim and there is no backoff.
- Record FLEET_ASSIGNED only after a successful claim. When a claim is refused (for example a write-scope overlap), do not log per tick: apply exponential backoff (start 5 s, cap 5 min) and emit at most one FLEET_BLOCKED event per (task, blocker) change.
- Regression test using the fake clock: a task blocked by an overlap for 10 simulated minutes produces no more than 5 events in total.

A3. Investigate only, do not change. Class K items (classifier patterns, ladder constants, policy) need a two-key queue item with the exact diff.
- T-0003: opencode exited 1 with a quota-like failure but was classified UNKNOWN although opencode-patterns.toml has a quota pattern. Show the raw log tail, the pattern, and why it did not match.
- T-0003: AGENT_RESUMED events go pi to opencode to hermes with model="". Sessions are per-CLI and only pi swaps model on resume, so a move to another CLI should be a fresh session with a handoff note (L2), not a resume. Show the exact event fields and the code path. State whether the label or the behaviour is wrong.
- T-0003: was the pi dispatch real or fake? Cite the pid, log file and agent type.
- File the findings in decisions.md. If a fix is warranted, create a queue item with its exact diff and stop.

Then: run the full test suite and `pmk sentinel` in a fresh clone, capture raw output with real timestamps, and confirm the live .pm state is untouched.

PART B: issue report v1.1

Write `pilot/assessment/report-opencode-umaws-completion-v1.1.md` (version 1.1.0). Open with a "Changes from 1.0.0" table listing every correction with the original text. Do not silently edit. Keep the 1.0.0 findings as assessed at a93da888 and show post-fix status separately. Make these corrections:

1. Verdict counts: keep claims in one structured file (CSV or YAML), generate every table and Appendix D from it with a script, count each claim once, and reconcile. 1.0.0 Appendix D does not match the section 3 tables (section 3 alone shows 16 verified-now and 10 wrong-doc, not 31 and 6) and mislabels D-L9.
2. Hypotheses: quote the exact text of H1–H7 from pilot v1 §2 and H8–H12 from the Fleet amendment §14.1, with measure, evidence and grade. Your 1.0.0 table used other statements, so move those into "additional observations".
3. Tiers: grade each item of the amendment's tiers A, B and C (§9.2) separately, and show v1's tiers in a second column.
4. pi: reconcile section 8 (pi dispatched in T-0003) with section 13 ("never dispatched live") using your Part A3 finding.
5. Section 14: state that STOP does not stop dispatch at a93da888 (and whether it does now); fix the toy-run steps to use `pmk project init` and `pmk project run`; replace POSIX `test -f` oracles with Windows-safe ones; list the real profile count (1.0.0 says 5 and names 6).
6. State whether any AGENT_STARTED event or provider call occurred during your console runs A and B. Give event counts before and after, and say plainly if any real CLI started.
7. Reconcile "16 invariants" with the 11 listed.
8. Appendix B: real timestamps from the raw output, with no placeholders.
9. Extract every checkable statement from the manual (thresholds, numbered steps, tables, command examples), not just 22.
10. Add an evidence-strength column: raw artefact, agent-authored summary, or code read. Downgrade items resting only on decision-log prose. Specifically: F3 is fake-CLI only (T-0003 failures were all UNKNOWN), and FR9 is mechanism-only (real concurrency reached 6).
11. Add an "Operator-reported tests" section: the 100-agent test, the quota stress test, and the 400+ model census. For each give what was reported, what artefact exists, and the verdict. Keep them UNVERIFIED unless an artefact is supplied.
12. Fix the "WRIGHT-DOC" typo and list every wrong-doc manual item with the correct value.

Also create `pilot/assessment/upload/` containing only these files (under 300 KB total, with a manifest and SHA-256 hashes): console-side-effects-ran-now.txt, event-counts-ran-now.txt, the T-0003 lifecycle extract, EB-T-0003-3/bundle.json, MANIFEST.md, cli-matrix.md, the opencode fixtures and patterns file, g5-summary.json, scale-f7.json, and decisions.md D-41 to D-end.

Do not fix the manual in this task. Finish by replying with only: commit hashes for A1 and A2, test and sentinel results (pass counts and raw-output file names), the v1.1 report path, the upload folder path and size, the corrected verdict counts, and any step you could not complete and why.