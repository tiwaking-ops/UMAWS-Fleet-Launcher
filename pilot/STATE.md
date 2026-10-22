# Pilot P-01 state (update at every checkpoint)

- **Updated**: 2026-10-22T22:40Z by OpenCode (implementing agent, Phase 1)
- **Phase**: 1 — bootstrap. **Day**: 1. **Tier reached**: A (+ a working
  Fleet). **Projected**: see "Cuts".
- **Gate posture**: the operator was asked how to behave at G0–G3 and said
  "I will provide these", which has not arrived. Until it does, the
  pilot v1 §12.1 default applies — **hold**: no gate is crossed silently.
  No gate has been crossed in this session. **This is the one open
  question.**
- **Scope decision**: whole pilot v1 + Fleet amendment A1, Tier A → C
  (operator choice). All five source specifications are present.
- **Done**:
  - Repo at `C:\temp\projects\testproject1`; venv `.venv` (Python 3.12.10);
    pinned deps in `requirements.lock`; `pip install -e .` so `pmk` is on
    PATH.
  - `src/pmk/` — Kernel-lite: event log (hash chain, torn-tail repair),
    task cards, leases with fencing, views, briefing, sentinel, PDD lint,
    the library API and the `pmk` CLI. **3 773 lines, standard library only.**
  - `src/pmk/plat.py` — portable sidecar file lock, spawn, tree kill,
    pid+creation-time identity, npm `.cmd` shim peeling, BOM-tolerant
    reads, RAM guard.
  - `src/fleet/` — profiles, adapters, selection, harness (two-phase
    start/poll), the recovery ladder L0–L4, the Dispatcher, the Conductor,
    the merge queue, the Overseer runner, the project lifecycle, the manual
    launcher port. **3 507 lines.**
  - `src/console/` — FastAPI Console on 127.0.0.1 with SSE and 7 tabs.
  - `gateway/quotagate/` — the hierarchical quota engine (M0–M2 core).
  - `tests/fleet/fakecli.py` + synthetic fixtures.
  - **150 tests passing.** `pmk sentinel` clean on the live repository.
  - `pilot/demo_one_click.py` runs the full lifecycle green: brief → PDD →
    tasks → claim → worktree → order → spawn → harness-run oracles →
    evidence bundle → merge queue → close-check → **DONE**.
- **In progress**: nothing. The next work needs a decision from the human
  (see "Blocked").
- **Next**:
  1. Read `pilot/pilot-report.md` §9.
  2. Spike **S-A1 live**: one trivial one-shot prompt per CLI, with the
     operator's approval, to capture headless/resume/session-id/exit-code
     behaviour. This unblocks the real adapters and the classifier.
  3. Spike **S-O1**: OpenCode headless, for the Overseer runner.
  4. Spike **S-W1** and test **F7** (100 fake workers) to replace the
     `max_total_agents = 20` guess.
- **Blocked / awaiting human**:
  1. **The gate rule.** See "Gate posture" above. Default on silence: hold.
  2. **Caliber install.** `npm i -g @rely-ai/caliber` is a global install;
     pilot v1 rule 6 forbids it without asking. Until it is approved, the
     G1 fallback stands and H2 is "not tested".
  3. **QuotaGate provider keys**, for M1's live capture and for the
     gateway-routed profiles.
- **Open [VERIFY] items**:
  - `V-01` every real CLI's headless/resume/session-id/exit-code/failure
    text. Operator chose **metadata-only** probing, so all of it is
    UNVERIFIED; the code degrades safely (caps default to `False`, every
    non-zero exit is `UNKNOWN`).
  - `V-02` Caliber is not installed.
  - `V-03` QuotaGate provider limits, 429 body shapes, quota headers.
  - `V-04` `max_total_agents` — needs S-W1; 20 is a placeholder.
  - `V-05` the Overseer's ordered profile list (G-F13).
  - `V-06` OpenCode headless (S-O1).
- **Decisions since last update**: `pilot/decisions.md` D-01 … D-12.
- **Last green test run**: `pytest -q` → **150 passed**, 2026-10-22.

## Cuts / risks carried

- `R-F2` Windows spawn quirks. **Measured and handled**: `cmd.exe` mangles
  arguments, so npm shims are peeled to their real target. The prompt is a
  fixed ASCII sentence and the instructions live in a file.
- `R-F9` the Fleet spawn/kill code is the most privileged ungoverned code.
  Still owed: the human's spot-read at G3.
- `L-F2` direct-CLI token usage is not measurable by the Kernel; budgets for
  those profiles are wall time and restarts only.
- `L-F4` direct CLIs keep their own credentials, so the Kernel cannot scrub
  them (D-L3). Gateway-routed profiles are scrubbed.
