From the operator. Process the canary results. Evidence rules first: report only
what .pm/events and the files actually prove; write "unknown" where you do not
know; never upgrade a draft to a decision.

SCOPE AND SAFETY (do this part first, it constrains everything below)
- Do not edit any tracked file. Do not commit anything. Reviewer item 1 (live-tree
  edits up to 17:35 NZ, and further edits to 22:49 NZ) is still unsettled, and
  group A must not be committed.
- Write your output as a draft under tmp/ only, then hand back. If you believe a
  tracked file must change, list the exact file and the exact diff and stop —
  do not apply it.
- State explicitly which session is answering this, and whether that session is
  the one that edited the live tree on 2026-11-10.

WHAT THE CANARY EVIDENCE ACTUALLY SHOWS
1. Enumerate the four supervised canary cards with, for each: fence, base_commit,
   agent profile, agent wall time, SUBMITTED ts, ORACLE_RESULT ts, gate cmd, gate
   exit, merge sha and merge author, bundle id, bundle byte size, presence or
   absence of gate_output, final task state. Cite seq numbers.
   - T-0189 fence 156: gate FAILED. Record it as a failure. Name the failing test
     and the base-tree cause. Do not describe it as historical in a way that
     softens it — superseded, not exonerated.
   - T-0190 fence 157, T-0191 fence 158, T-0196 fence 159: reached DONE with
     gate exit 0 and merges 0edc0dc / c7fcdf3 / 951d1ee, all authored
     umaws-pilot <umaws-pilot@localhost>.
2. EB-T-0190-157 has NO gate_output key; EB-T-0191-158 and EB-T-0196-159 do.
   Therefore DoD-6 "non-empty gate_output" is proven TWICE, not three times.
   Correct every sentence that implies three. Do not rewrite the historical
   decision text — add an erratum that scopes it.
3. HANDOFF.md currently says "Canary PASS — T-0190, T-0191 and T-0196". That
   conflates "the dispatch path passed" with "H6 gate_output was proven". Propose
   corrected wording that keeps all three as path passes while stating that only
   T-0191 and T-0196 carry gate_output. Give me the diff; do not apply it.

WHAT THE CANARY EVIDENCE DOES NOT SHOW — write these as unknown
4. CANARY_STARTED and CANARY_FINISHED: zero occurrences anywhere in the chain
   (I1 verifies at 3630 events). src/fleet/canary.py is untracked. So
   `pmk canary run` has never produced a durable record, and the three passes
   above came from `pmk dispatch run` / the Console, not from run_canary.
   Say exactly that. Do not describe the single-owner canary runner as tested.
5. DISPATCH_RESUMED, DISPATCH_PAUSED, MANUAL_LAUNCH: zero occurrences in the
   entire log. A10 has never been authorized. Project is PAUSED with 12 READY
   cards and 2 active leases. Nothing in the canary results authorizes a resume.
6. src/fleet/owner.py:250 still writes Actor.human() in resume_dispatch with no
   verification. That is reviewer item 3, still open.
7. Gate duration. Measured SUBMITTED -> ORACLE_RESULT spans are 253 s, 411 s,
   355 s, 681 s for T-0189/0190/0191/0196, plus 239 s (T-0148, fail) and
   1371 s (T-0150, pass). That span includes bundle verification and queue wait,
   not only the gate subprocess — 1371 s is larger than the hardcoded
   timeout=900 at src/fleet/merge.py:318, which is only possible if the gate
   subprocess itself was shorter. The gate's own duration is therefore UNKNOWN.
   The old "## Gate budget" section asserted both "up to about 12.5 minutes" and
   "at least 15 minutes"; those conflict and neither is reproducible from the log.
   Per the reviewer: the docs must say the gate ran "between 12.5 and 15 minutes,
   unknown", and the phrase "too tight" must be removed. Note that section is
   already absent from the live pilot/repair-canary-runbook-v1.md — record that
   the deletion happened, who did it, and when, then propose the corrected
   replacement text rather than leaving the claim silently gone.

REVIEWER ITEM 5, STILL OPEN
8. canary_gate_timeout_s is not in the live tree. It exists only inside
   tmp/reviewer-patches/patches-rebased/0004-rebased.patch and
   tmp/review-followups/ (agents.toml, src/fleet/merge.py, a test). Confirm that
   yourself. Rename it — it applies to all gates, not only canaries. Deliver
   0004-rebased.patch as `git format-patch`, not as a raw diff. Do not apply it.

STANDING OF THE DECISIONS
9. D-72, D-73 and D-74 are all "drafted for operator ratification at CP-4".
   None is ratified. D-69 is the recorded FAIL. Do not promote, merge or
   summarise any of them as accepted. Say which one you are proposing and what
   it would change, and leave the ratification to me.

HAND BACK
10. One paragraph: what is proven, what is unknown, what needs my decision.
    Then the exact diffs you want me to approve, listed per file. Then the single
    question you need answered. No commit, no live edit, until I clear reviewer
    item 1.