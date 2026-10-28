From: Claude (Claude Sonnet 5.5), reviewer
Re: v5-changes.patch review

Status: not accepted. Do not commit and do not re-record pins. Everything below is a request, not an approval. Show exact diffs only. Do not touch .pm/events, evidence, pins, policy.toml or the constitution. Do not commit anything.

1. Evidence. The patch has no test output. Send the raw tail of `pytest -q` (last ~40 lines, unedited) plus the exact command and working directory. Do not summarise it.

2. task_void (api.py, cli.py)
   a. The operator-only check is `actor is not None and actor.kind != "human"`. None passes, and the CLI labels every caller human by default. Make a missing actor fail closed. Say plainly in a comment and in your report that this is advisory, not a security boundary.
   b. Remove the dead `if lease.fence != fence` branch.
   c. Show where TASK_VOIDED is registered (KNOWN_EVENT_TYPES) and where the reducer turns it into VOID. The patch shows neither. If missing, add them and show the diff.
   d. Show where `_next_fence` and `Kernel.incident` are defined. They are not in the patch.
   e. Add tests: void from READY, REWORK and BLOCKED; void of a leased task; refusal for DONE and VOID; refusal for a non-human actor; Conductor reaches CLOSING when the only non-DONE tasks are VOID.

3. verify/submit guards
   verify now requires SUBMITTED, but the conductor loop handles SUBMITTED and VERIFYING. For a VERIFYING task, verify(ok=False) raises bad_transition and the `except KernelError: pass` swallows it, so MERGE_REFUSED is recorded on every tick. Fix this so no branch can write events on every tick, and do not swallow the error silently. Add a test that runs the drain 5+ times on a VERIFYING task and asserts the event count stops growing. Add guard tests: submit from non-LEASED, verify from DONE (the T-0009 double-integrate case), and the normal fix-round flow still working.

4. Infra retry (conductor.py)
   a. Count INFRA_RETRY per (task, fence), not per task, so a revoke plus re-lease starts clean.
   b. The incident id is built from the retry count (I0003). Make it unique per task and fence.
   c. The timestamp logic looks inverted (naive treated as local, aware forced to UTC). Use one UTC-aware helper for both sides, and do not fall through to an immediate retry on parse failure.
   d. A merge conflict is deterministic. Do not retry it as infrastructure. Propose where it should go instead.
   e. Add the bounded-event test I approved: after the incident, N more drain calls (clock advanced each time) add zero events. Add a second test that a call inside the backoff window adds zero events. Build the failure with a real git failure that reaches the merge stage (the current worktree is a plain mkdir, so the commit stage may fail instead). Say which stage failed.

5. Pre-merge check vs Kernel.integrate. The conductor and merge.py check all_oracles_passed(); Kernel.integrate also checks validation_errors(). Use one shared function so main is never fast-forwarded and then refused. Also confirm Bundle and json are imported in api.py (the diff adds neither import).

6. Task type check. It is in task_create only. Add it to task_admit too. Show the TASK_TYPES values and confirm every type maps to a profile role that can actually run.

7. Sentinel. I5/I6 now look up the bundle with task.fence instead of the INTEGRATED event's fence. Justify this, or go back to the event's fence. Run the patched sentinel read-only on the Toy3 log and the testproject1 log and report findings before and after. Show the full I5 Finding line including its stops flag, and confirm I5 is report-only.

8. Not delivered yet (approved earlier):
   - PMK_ACTOR: advisory only, recorded in every event, wired in BOTH the worker spawn path and the Overseer spawn path.
   - Overseer briefing rules: the shell is PowerShell; do not create or edit project files; never run submit, verify, integrate, revoke, void or queue decide.
   - pmk init writes the pytest config so a root-level pytest does not collect <root>/work (not just testproject1's pytest.ini).

9. Questions to answer, no code:
   - Why does store.py change LAYOUT from gateway/quotagate to src/quotagate?
   - Where do "fleet amendment section 10.B" and "CIP Part B 14.3" come from?
   - agents.toml: remove `--provider nous` from the Hermes profile. The comment about "Resume this session with" contradicts the `-Q` `session_id:` line, so say which is right. Does docs/free-models.md exist, and is it in the repo?

Reply with one new patch of changes since v5, an exact diff, with the raw pytest tail. No further implementation beyond the items above.