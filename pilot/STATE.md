# Pilot P-01 state (update at every checkpoint)

- **Updated**: 2026-10-22T18:20Z by OpenCode (implementing agent, Phase 1)
- **Phase**: 1 — bootstrap. **Day**: 1. **Tier target**: A.
  **Projected**: at risk (see "Cuts")
- **Scope decision**: whole pilot v1 + Fleet amendment A1, Tier A → C
  (operator choice). Source specs all present: pilot v1, fleet A1, UMAWS,
  QuotaGate v1.1, CIP.
- **Done**:
  - Repo initialised at `C:\temp\projects\testproject1`; venv `.venv` (Python
    3.12.10); pinned deps in `requirements.lock`.
  - `src/pmk/plat.py` — platform layer: sidecar file lock, atomic write,
    spawn, tree kill, pid+creation-time identity, RAM guard, executable
    resolution for `.ps1`/`.cmd` shims, redaction.
  - Spike **S-P1** run: platform decision, lock test, CLI resolution.
    Record: `pilot/spikes/s-p1-platform.md`.
  - Seeds written: `.pm/constitution.md` (CIP App. A.1 verbatim),
    `.pm/policy.toml` (CIP App. A.2 translated to TOML per D-P3 + fleet
    recovery constants), `agents.toml` (fleet §12.A), `pyproject.toml`.
- **In progress**: WP2 — Kernel-lite core.
- **Next**:
  1. `src/pmk/events.py` — hash-chained append-only log, torn-tail repair.
  2. `src/pmk/state.py` — rebuild state from the log; `tasks.py`, `leases.py`.
  3. `src/pmk/views.py`, `briefing.py`, `sentinel.py`.
- **Blocked / awaiting human**: **gate behaviour** — the operator was asked
  whether to stop at G0–G3 and said they would supply the rule. Until it
  arrives, gates are treated as **hold** (pilot v1 §12.1 default) and no gate
  is silently crossed.
- **Open [VERIFY] items**:
  - `V-01` every real CLI's headless/resume/session-id/exit-code behaviour.
    Operator chose **metadata-only** probing, so adapters ship with caps
    defaulting to `False` and the classifier `UNVERIFIED`.
  - `V-02` Caliber is not installed on this machine; `npm i -g
    @rely-ai/caliber` needs operator approval (pilot v1 rule 6).
  - `V-03` QuotaGate provider limits, 429 body shapes, quota headers.
  - `V-04` `max_total_agents` — needs spike S-W1 (20 vs 100 worktrees).
  - `V-05` Overseer profile list contents (G-F13).
- **Decisions since last update**: see `pilot/decisions.md` D-01 … D-08.
- **Last green test run**: spike S-P1 lock test, 2026-10-22 —
  20 processes × 25 appends = 500/500 records, 0 torn, 0 missing, 0 errors.

## Cuts / risks carried

- `R-F2` Windows spawn quirks: `.ps1` npm shims, quoting, orphan processes.
  Mitigation: argv lists (never shell strings), order file for the prompt,
  `taskkill /T`, test F11.
- `R-F9` the Fleet spawn/kill code is the most privileged ungoverned code.
  Mitigation: human spot-read at G3 (fleet §11).
- `L-F2` direct-CLI token usage is not measurable by the Kernel; budgets for
  those profiles are wall time and restarts only.
