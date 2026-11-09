# PDD: Digital Edition of The Campaign for North Africa (CNA) — version: 1 — status: released (G-001/G-002); full product in progress

## 1. Purpose

Build a single-player, Windows-only digital version of SPI's 1979 board wargame *The Campaign for North Africa* (CNA), played by one human against one computer opponent, using Python 3.11+ with Tkinter UI, built by the UMAWS Fleet with minimal operator supervision.

## 2. Goals (re-scoped 2026-11-02 per Q-060/Q-069/Q-070)

Re-scope: keep only the automated/oracle goals that are delivered and verified.
G-001 and G-002 are the release goals for this close. G-004, G-005, and G-006
are accepted as incomplete/manual-check goals out of scope for this close and
are not tracked as release blockers.

### G-001 Rules implemented, cited, and covered

acceptance:
- every implemented rule cites its case number (e.g. `6.13`)
- a generated coverage report shows, per case, whether it is unimplemented, partial, implemented, or deliberately skipped
- no silent claims are made about implemented rules
oracle: `python -m cna.tools.rules_index --check && python -m cna.tools.coverage --check && python -m pytest -q tests/test_rules_baseline.py`

### G-002 Computer opponent chooses only legal actions (formerly G-003)

acceptance:
- `RandomLegalPlayer` selects uniformly among legal actions from a seeded RNG
- the AI never makes an illegal action across many seeded AI-vs-AI games
- smarter opponents replace it without changes to engine code
oracle: `python -m pytest -q tests/test_engine_contract.py`

## 3. Non-goals

- A strong or "historical" AI; network play; more than two players; Linux or macOS; unofficial or house rules; polished graphics; a distributable installer; mobile.
- Delegating to automated sub-commanders (designed for, not built).

## 4. Constraints

- Windows 10 native only. No WSL.
- Python 3.11+, standard library plus `pytest` only (additional packages require a recorded decision, `RD-xxxx`).
- Official sources only. No fabricated data presented as real.
- Work only inside the live project root `C:\temp\projects\testproject1` (the former `C:\temp\projects\cfna` path is retired).
- No `@`-imports of proposals or rules into `CLAUDE.md` or `AGENTS.md`.
- Oracles must be Windows-safe: `python -m pytest -q` or `python -c "..."`.
- Max six concurrent workers.

## 5. Architecture sketch

Engine is pure and deterministic (`apply(state, action, rng)` returns a new state plus events); everything goes through one action API (`legal_actions` / `apply`); rules are modules citing cases; data drives statistics (no unit numbers in code); state is serialisable JSON with schema version and state hash; illegal is impossible via `legal_actions`; hidden information uses `view()` and sealed commitments; dice/RNG is seeded; persistence supports save/load/replay; rulesets combine modules with validation (LAND_ABSTRACT first); AI uses view(state, side) only.

## 6. Definition of done

gate_cmd: `python -m pytest -q`

## 7. Open questions

None.
PY