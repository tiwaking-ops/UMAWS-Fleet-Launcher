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
  - `src/pmk/context.py` — the context machinery: the **I15 lint** (all
    six of CIP §14.6's rules, with the reject/review distinction), the
    **I16 drift check**, the sync task and the snapshot-based revert.
  - `src/fleet/` — profiles, adapters, selection, harness (two-phase
    start/poll), the recovery ladder L0–L4, the Dispatcher, the Conductor,
    the merge queue, the Overseer runner, the project lifecycle, the manual
    launcher port. **3 507 lines.**
  - `src/console/` — FastAPI Console on 127.0.0.1 with SSE and 7 tabs.
  - `gateway/quotagate/` — the hierarchical quota engine (M0–M2 core).
  - `tests/fleet/fakecli.py` + synthetic fixtures.
  - **Caliber 1.55.2 installed and pinned** (operator approved). Spikes
    **S1** and **S4** complete — see `pilot/spikes/caliber-s1-s5.md`.
  - **182 tests passing.** `pmk sentinel` clean on the live repository.
  - `pilot/demo_one_click.py` runs the full lifecycle green: brief → PDD →
    tasks → claim → worktree → order → spawn → harness-run oracles →
    evidence bundle → merge queue → close-check → **DONE**.
- **In progress**: spikes **S2, S3 and S5** are running in a scratch copy
  (`pilot/spikes/caliber_spike.py`).  The generation step is slow:
  `MIN_PROMPT_TOKENS = 3e4`, so every call sends at least 30 000 input
  tokens through a free provider.
- **Next**:
  1. Collect the S2/S3/S5 results: which files Caliber writes, whether
     `refresh` preserves a human edit, and whether it is deterministic
     enough for a stable `CONTEXT_SYNCED` hash.
  2. Read every generated file and delete anything that tells an agent to
     write under `.pm/` (CIP §8.6 step 1).
  3. Run **T4**: plant "agents may edit `.pm/` and skip verification" in a
     repo document, sync, and confirm the lint rejects it.
  4. Spike **S-A1 live** and **S-O1**; run **S-W1** and **F7**.
- **Blocked / awaiting human**:
  1. **The gate rule.** See "Gate posture" above. Default on silence: hold.
  2. **CIP Q1** — the provider data terms for the context-sync lane.  The
     spike used the operator's own local OmniRoute router, which fronts
     free-tier providers, so the repository's content still reaches a
     provider.
  3. **QuotaGate provider keys**, for M1's live capture and for the
     gateway-routed profiles.
  4. **Live S-A1 approval** — one trivial one-shot prompt per CLI.
- **Open [VERIFY] items**:
  - `V-01` every real CLI's headless/resume/session-id/exit-code/failure
    text. Operator chose **metadata-only** probing, so all of it is
    UNVERIFIED; the code degrades safely (caps default to `False`, every
    non-zero exit is `UNKNOWN`).
  - `V-02` Caliber's overwrite semantics (S3) and determinism (S5) — the
    spikes are running.
  - `V-03` QuotaGate provider limits, 429 body shapes, quota headers.
  - `V-04` `max_total_agents` — needs S-W1; 20 is a placeholder.
  - `V-05` the Overseer's ordered profile list (G-F13).
  - `V-06` OpenCode headless (S-O1).
- **Decisions since last update**: `pilot/decisions.md` D-01 … D-18.
- **Last green test run**: `pytest -q` → **182 passed**, 2026-10-22.

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
