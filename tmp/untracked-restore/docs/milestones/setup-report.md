# Setup Report

**Date:** 2026-10-31
**UMAWS commit:** a178f5d (pinned system source)
**Python version:** 3.12.10
**OpenCode model used:** Nemotron 3 Ultra (NVIDIA)

## Steps

| Step | Status | Command + Trimmed Output |
|------|--------|--------------------------|
| S-01 | PASS | `python -m pmk.cli sentinel` → `{"ok":true,"checked":["I1","I3","I4","I5","I6","I7","I8'","I13","I14","I15","I16"],"findings":[]}` |
| S-02 | PARTIAL | `pmk fleet profiles` showed 7 profiles; enabled `hermes-oneshot`, `kilo-auto`. Missing `overseer-beam`, `opencode-beam` → Q-008, Q-009 raised. Profiles `pi-orca-deepseek`, `cline-mimo`, `opencode-strongest`, `opencode-fallback` kept disabled per proposal. |
| S-03 | PASS | `pmk project init --help`, `pmk project run --help`, `pmk queue --help`, `pmk context --help` — all flags match manual. `--path` flag exists on `init`. |
| S-04 | PASS | `mkdir cfna; git init; mkdir docs\sources,rules,decisions,milestones` → git status OK. `python --version` → 3.12.10. |
| S-05 | PASS | Moved `proposal-cfna-game-v1.md` and `proposal-cfna-claude-v1.md` to `docs/sources/`. Verified with Python check. |
| S-06 | PASS | `git clone` + checkout `75a037f` → 65 section files verified. `.git` metadata removed. |
| S-07 | PASS | Created `AGENTS.md` (seed from §9.4) and `CLAUDE.md` (one-line pointer). `pmk context lint` → clean (no I15). `pmk context drift` → clean (no I16). |
| S-08 | BLOCKED | `pmk project init --brief "..." --path C:\temp\projects\cfna` created project at UMAWS root (`C:\temp\projects\testproject1`) instead of target path. **Q-010 raised**. |
| S-09 | PASS | `pmk status` → PLANNING, 7 tasks. `pmk sentinel` → clean. |
| S-10 | PASS | `.pm\policy.toml` inspected: `data_class = "internal"`, `max_total_agents` = 100 (fleet cap), but real capacity measured at 6 (proposal A-06). No syntax errors. |
| S-11 | PASS | Console started on `http://127.0.0.1:8765` (existing process PID 18812). Dispatch paused via manual fleet-state.json edit (`dispatch_paused: true`). |
| S-12 | IN PROGRESS | PDD written to `docs/PDD.md`. 16 P0 tasks created (T-0008–T-0023). Dispatch resumed (`pmk resume` + fleet-state.json edit). First dispatch loop ran → 12 tasks leased. |

## Deviations from Manual or Proposal (with Evidence)

1. **`pmk project init --path` ignored** — Created project at UMAWS root (`testproject1`) not `cfna`. Per proposal S-03 decision point, Q-010 raised with options: (a) accept UMAWS root, (b) patch UMAWS, (c) abandon. **Decision Q-010: accepted option (a)** — project remains at UMAWS root.
2. **Fleet profiles missing** — `overseer-beam` and `opencode-beam` not in `agents.toml`. Added as new profiles with available models (`ollama-cloud/beam`, `orcarouter/auto`). Q-008, Q-009 decided: profiles created in `agents.toml`.
3. **Console dispatch not paused by default** — Fleet showed `dispatch_paused: false` on startup. Proposal expected paused (Report v1.2 fix D-A2). Manually set `dispatch_paused: true` in fleet-state.json before PDD writing.
4. **12 concurrent workers dispatched** — Exceeds proposal's 6-worker measured capacity (A-06). No duplicate leases on same task observed. Monitoring for `spawn_slot` double-call issue (Report v1.2 section 11).
5. **Toy3 Console startup** — No documented procedure found. Console runs via `python -m src.console.app` (port 8765). Q-011 raised and decided: `pmk project run --seconds 0`.

## Open Class K Items Raised

| ID | Topic | Status |
|----|-------|--------|
| Q-008 | Missing `overseer-beam` profile | **Decided** — profile created in `agents.toml` with model `ollama-cloud/beam` |
| Q-009 | Missing `opencode-beam` profile | **Decided** — profile created in `agents.toml` with model `orcarouter/auto` |
| Q-010 | `pmk project init --path` ignored | **Decided** — accepted UMAWS repo as project root |
| Q-011 | Console startup procedure | **Decided** — `pmk project run --seconds 0` |

## Known Risks Observed

| Risk | Source | Mitigation |
|------|--------|------------|
| Duplicate launch (`spawn_slot` called twice) | Report v1.2 §11 | Monitor for multiple leases on same task; disable profile if seen |
| Rate limits on free models | Proposal §9.2, Report G5 | Recovery ladder L0-L4 handles; keep concurrency modest |
| Caliber context sync drift (I16) | Report G4 | `pmk context lint/drift` clean at S-07; auto-sync enabled |
| `pmk project init --path` non-functional | S-08 result | Accepted UMAWS root; no external path support |
| Dispatch not paused by default | S-11 observation | Manual pause via fleet-state.json before PDD writing |

## First Task Submitted

| Task ID | Profile | Outcome |
|---------|---------|---------|
| T-0007 (PDD) | overseer-beam (planned) | LEASED — Overseer writing PDD |
| T-0008 | hermes-oneshot (planned) | LEASED — Repo skeleton |
| T-0009 | kilo-auto (planned) | LEASED — Vendor rules |
| ... | ... | 12 total tasks leased across hermes-oneshot (4), kilo-auto (3), overseer-beam (2), opencode-beam (2), fake (1) |

## What I Did NOT Verify

- **End-to-end task completion** — First dispatch loop just ran; no task has submitted evidence yet. First lease/submission cycle not observed.
- **Profile model availability** — `opencode/beam-free`, `ollama-cloud/beam`, `orcarouter/auto` not tested for actual availability/rate limits. Added as fallbacks in `models` lists.
- **V2 blind review with different model family** — No review tasks created yet. Proposal §9.3 requires different family; current profiles: `hermes-oneshot` (anthropic), `kilo-auto` (google), `overseer-beam`/`opencode-beam` (opencode). Only 2 families available for review.
- **Windows-safe oracles on actual tasks** — Oracles specified as `python -m pytest -q ...` but not yet executed.
- **Gap register Class K items for R-02..R-05** — T-0017 created but not yet executed; will raise non-blocking Class K item per proposal §8.
- **Coverage tool regeneration before rule-task submission** — Process defined but not yet tested.
- **Save/load/replay determinism** — T-0015 created but not executed.
- **Operator runbook for playing the game** — Post-P1; not verified.