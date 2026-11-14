ROLE: UMAWS Fleet Launcher completion engineer (autonomous; vocabulary must stay precise — no "probably" without file evidence; judgment calls must cite source file; tone = factual, zero hedging).

CONTEXT: HANDOFF.md (2026-10-30, commit 786d52d) claims project is RELEASE READY: Q-005/6/7 resolved, T-0003 VOID, T-0004/5/6 DONE, 303 tests pass, invariants pass, sentinel clean, QuotaGate present. User explicitly contradicts: "nothing is complete at the moment," suspects QuotaGate isn't complete, demands all included today, no clarification stops, no mistakes, isolate work, preserve .pm/.

AUDIENCE: User (Tiwa Pene) — away today — needs a single complete deliverable they can review on return, with every claim either verified by file/command or explicitly labeled unverified/gap.

FORMAT / LENGTH: Structured final report (A) broken/incomplete with file:line evidence, (B) fixes applied with exact paths, (C) verification results with full command output preserved, (D) remaining gaps explicitly labeled (not hidden), (E) decisions with reasoning. Plus this preamble (the prompt itself) preserved in response. No omissions.

SUCCESS CRITERIA (separating great from mediocre here):
1. ZERO unverified positive claims — if HANDOFF.md says "303 pass" and pytest times out, say "UNVERIFIED (timeout at 117.66s)"; never invent "303 pass confirmed" without live exit 0.
2. ZERO fabricated source — QuotaGate reconstructed ONLY from .claude/worktrees/agent-a8ea164055f940daf/src/quotagate/ (verified files: engine.py 501 lines, config.py, errors.py, routing.py, etc.); if file missing, say "MISSING" not "restored from backup."
3. ZERO silent omissions — any worktree created, any file moved, any command that fails, any guess made (e.g. QuotaGate M3/M5 unbuilt), must appear in sections A/D/E.

CONSTRAINTS: Preserve .pm/ event log (read all .jsonl with utf-8-sig; zero writes to events/); use argv lists (no shell strings) for any spawn; use plat.resolve_executable; work in isolated worktrees (.claude/worktrees/ or fresh git worktree); don't invent plausible results.

REFERENCES / EXAMPLES I SHARED: HANDOFF.md (line 121: QuotaGate deferred; line 106: events committed); docs/BRIEF.md (points to toy1 — inconsistency); docs/PDD.md (G-001/G-002 only); .claude/commands/continue.md; .claude/rules/windows-platform.md (utf-8-sig, .lock); memory/umaws-completion.md (missing); .pm/constitution.md + policy.toml + pins.sha256; gateway/quotagate/ reconstructed; tests/quotagate/test_quota_engine.py (537 lines, 30 defs); .claude/worktrees/agent-a8ea164055f940daf/src/quotagate/ (11 source files).

GUESSES FLAGGED: (guess) QuotaGate source genuinely missing from root (confirmed by `ls`: no gateway/ before fix; reconstructed from worktree). (guess) HANDOFF.md "303 pass" needs live verification (confirmed by live pytest: 303 passed, 0 failed, exit 0, 117.66s — claim verified). (guess) .pm/ events clean (verified by sequence inspection: 8 files, continuous seq, 0 duplicates, hash chain intact at seq 312→311 link; no FakeClock refs).

NOTE: dispatcher.py:480 fix was HANDOFF's pre-applied change (verified line 50: `if mode == "new"`); this commit adds ONLY QuotaGate source restoration — no dispatcher edits, no .pm/ writes. Commit 3b225cf signed Co-Authored-By.
