# Project State Report — UMAWS Fleet

**Author:** DeepSeek (coding agent)
**Version:** v1
**Date:** 2026-10-26
**Repository:** `C:\temp\projects\testproject1`
**Branch:** `main` (commit `6764d54`, plus uncommitted working-tree changes)

---

## 1. Purpose and Scope

This report assesses the current state of the UMAWS Fleet repository: what it is
meant to do, which parts are working, which are broken, and what should be
improved. It is based on repository inspection (README, AGENTS/CLAUDE context,
pilot STATE, source/test layout, git history) and an attempted full test run.

## 2. What the Project Is Meant to Do

UMAWS Fleet is a **Kernel-lite multi-agent coordination system**. A single
Kernel (`src/pmk/`) is the sole writer of state via an append-only JSONL event
log (`.pm/events/`); it rebuilds State and Views from that log. A Fleet layer
(`src/fleet/`) supervises CLI agent processes: a Dispatcher assigns tasks to
Profiles, a Harness manages worktrees, order files, oracles and evidence. A
FastAPI Console (`src/console/`) provides a browser view, and a QuotaGate
(`gateway/quotagate/`) provides hierarchical quota (RPM/TPM/RPD) with
timezone-aware resets.

Core invariants: Kernel-only writes (I2), oracles decide (I5), pinned policy
(I8), views are projections (I13). The pilot P-01 lifecycle runs a brief →
PDD → task cards → claim → worktree → order → spawn → oracles → evidence
bundle → merge queue → close-check → DONE, demonstrated on a fake CLI.

## 3. Architecture Summary

- `src/pmk/` — Kernel: events, tasks, leases/fencing, views, briefing,
  sentinel, PDD lint, API, CLI. Stdlib only. ~3,773 lines.
- `src/pmk/plat.py` — sidecar locks, spawn, tree kill, pid+creation-time
  identity, npm `.cmd` shim peeling, BOM-tolerant reads.
- `src/fleet/` — profiles, adapters, selection, harness (two-phase
  start/poll), recovery ladder L0–L4, dispatcher, conductor, merge queue,
  overseer runner, project lifecycle, manual launcher port. ~3,507 lines.
- `src/console/` — FastAPI Console on 127.0.0.1 with SSE, 7 tabs.
- `gateway/quotagate/` — hierarchical quota engine (M0–M2 core).
- `tests/` — ~150 tests across Kernel, Fleet, QuotaGate.
- `pilot/` — STATE.md, decisions, spikes, pilot report, demo script.
- `.pm/` — coordination state: event log, views, task cards, evidence, pins.

## 4. What Is Working

- Source tree and editable install present (`.venv`, `pmk` CLI entry point).
- Git history shows a sustained repair trajectory (D-51 defect fixes, D-A1
  backoff, D-A2 dispatch-paused gate, regression tests added).
- Pilot STATE reports G3 real-CLI half passes, G4/G5 crossed, 234 tests
  passing as of 2026-10-24, sentinel clean, demo one-click green.
- README documents full quick start, CLI, layout and invariants.
- 142 source files and 72 test files present; test infrastructure intact.

## 5. What Is Not Working / Issues Identified

1. **Test suite cannot run in this sandbox.** All tests error with
   `PermissionError: [WinError 5] Access is denied` against the pytest temp
   directory (`C:\Users\Tiwa Pene\AppData\Local\Temp\...pytest-of-Tiwa Pene`)
   and even against in-workspace basetemp dirs. The sandbox's file-access
   policy blocks directory creation/scandir in these locations. This is an
   environment/sandbox constraint rather than a product defect, but it means
   the suite cannot be re-verified here; the claimed "234 passing" cannot be
   re-confirmed in this session.

2. **Uncommitted working-tree drift.** `git status` shows modified
   `.pm/events/2026-10-25.jsonl`, `.pm/views/ledger.md`, `.pm/views/status.md`,
   `agents.toml`, plus untracked `2026-10-26.jsonl`, assessment docs, and
   `docs/free-models.md`. The Kernel's I13 (views are projections) and I8
   (pinned policy) invariants require these be reconciled; an uncommitted
   event-log mutation without a corresponding view regeneration is a
   potential invariant violation.

3. **Hash-chain integrity risk.** Commit `7c3ff46` repaired a seq-84 event
   line (hash chain) and kept an edited copy in `pilot/assessment/forensics`.
   This indicates a prior chain tampering/incident; sentinel cleanliness must
   be re-verified after any further edits.

4. **Environment sensitivity.** README quick start uses `py -3.12`; venv is
   3.12.10. Tests depend on temp-dir writability, which fails under the
   current sandbox; CI/local runs on a normal Windows host should be fine,
   but this blocks in-sandbox verification.

5. **Docs/assessment sprawl.** Numerous ad-hoc assessment/proposal markdown
   files at repo root; risk of stale guidance. Consolidation recommended.

6. **Model routing volatility.** Recent commits repoint free models
   (kilo-auto/free, poolside/laguna-s-2-1:free, cline-mimo to five offered
   free models, none verified). Live capacity depends on unverified free
   endpoints — a reliability risk.

## 6. Recommendations

- Re-run the full suite on a host with normal temp-dir permissions
  (`pytest -q`) and record the count; keep `--basetemp` pointing at a
  writable path in CI.
- Run `pmk sentinel` and `pmk status` after committing/normalizing the
  working-tree changes; regenerate views from the log to satisfy I13.
- Re-verify the hash chain (`sentinel`) after the seq-84 forensic repair
  and any view regeneration.
- Consolidate root-level assessment/proposal docs into `docs/` with an
  index; mark superseded ones.
- Add a CI job that runs `pytest -q` plus `pmk sentinel` on every commit.
- Verify the five cline-mimo free models end-to-end before relying on them
  in dispatch.
- Keep the dispatcher's `dispatch_paused` default (no dispatch on start)
  and backoff behaviour; add a documented runbook for unpausing.

## 7. Conclusion

The project is a substantial, well-documented coordination system with a clear
architecture and a strong invariant model. Its core implementation appears
complete per the pilot record, but in this sandbox the test suite cannot be
executed due to filesystem permission restrictions, and the working tree
contains uncommitted state that should be reconciled and verified against the
Kernel invariants before further changes.

---

*End of report.*
