# Pilot P-01 state (update at every checkpoint)

- **Updated**: 2026-10-23 by OpenCode (implementing agent, Phase 1)
- **Phase**: 1 — bootstrap. **Day**: 2. **Tier reached**: A (+ a working
  Fleet). **Projected**: see "Cuts".
- **Gate posture** (the operator's rule, D-25; the pilot v1 §12.1 default
  it replaces is recorded as a defect at report §4.4):

  | Gate | Kind | Status |
  |---|---|---|
  | G0 environment | evidence | **crossed**, recorded with evidence |
  | G1 Caliber go/fallback | evidence | **crossed**, recorded with evidence |
  | G2 live capture | evidence | **crossed**, recorded with evidence |
  | G3 handover | authorisation | **ratification complete** (D-19/D-20 ratified, D-29); **end-to-end handover test outstanding** (D-30) |
  | G4 auto-sync | authorisation | **HELD** — `mode = "dry-run"` |
  | G5 live capacity | authorisation | **HELD** |

  **Class K is two-key, always**, regardless of any earlier approval — and
  the key is taken *before* the change, not after (the D-19/D-20 timing
  weakness is recorded at D-29).
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
    **S1, S2, S3, S4 and S5 complete** — see
    `pilot/spikes/caliber-s1-s5.md`.
  - **The G1 baseline is installed**: 10 generated context files, sanitised,
    linted, hashed and committed; the pins re-recorded; the sentinel clean.
  - **T4 and T4b complete** — see `pilot/spikes/t4-canary.md`.
  - **S-A1 run LIVE** (operator approved, D-24) — see
    `pilot/spikes/cli-matrix.md`.  All five CLIs run **headless**; hermes,
    kilo, pi and opencode **resume**; pi resumes on a **different model**;
    cline's MODEL_GONE and opencode's QUOTA are captured as fixtures.
  - **209 tests passing.** `pmk sentinel` clean on the live repository.
  - `pilot/demo_one_click.py` runs the full lifecycle green: brief → PDD →
    tasks → claim → worktree → order → spawn → harness-run oracles →
    evidence bundle → merge queue → close-check → **DONE**.
  - Every Phase 1 commit is tagged `bootstrap/0` … `bootstrap/16`.
- **In progress**: nothing.
- **Next**:
  1. **G3's end-to-end handover test (H6)** — a real CLI driven through a
     real lease, and an OpenCode session restarting from the briefing
     alone.  **Needs its own go-ahead** (D-30: it hands real work to a real
     agent, so it is not covered by the D-19/D-20 ratification).
  2. **Fill in the `models` lists** for hermes, kilo, cline and opencode
     from the operator's `prompts.json`, so the ladder's L1 step (resume on
     a different model) is available for all of them and not only pi.
  3. **Repoint `cline-mimo`** — its model's free promotion has ended (D-28).
  4. Run **S-W1** and test **F7** (100 fake workers) to replace the
     `max_total_agents = 20` guess.
  5. Build QuotaGate **M1** (the passthrough proxy) so that the gateway
     can serve the `context-sync` lane as CIP §7.3 describes, and so the
     provider allowlist becomes the destination.
- **Blocked / awaiting human**:
  1. **G3's handover test** — needs a go-ahead (D-30).
  2. **The amendment draft** `pilot/amendment-gates.md` — accept / edit /
     discard.
  3. **QuotaGate provider keys**, for M1's live capture.
  4. **G4/G5** — held.
- **Open [VERIFY] items**:
  - `V-01` **mostly closed**: headless, resume and (for pi) model-switch
    are measured.  **Still open**: hermes, kilo and pi have no captured
    failure text, so their failures are `UNKNOWN`; the exit codes are only
    0 and 1; and no real CLI has been driven end to end through a lease.
  - `V-02` **closed**: Caliber's overwrite semantics (S3) and determinism
    (S5) are measured.
  - `V-07` **new**: the generator has **not** been shown to be safe
    against injection.  T4's premise did not reproduce — three planted
    injections were not copied into the context files — so the generator
    is unproven rather than proven safe.
  - `V-08` **new**: the lint's coverage limit is measured and pinned
    (D-21).  The residual protection is the combination of lint, score
    gate, blind V2 review and audit.
  - `V-09` **new**: the operator's `cline-mimo` profile names a model
    whose free promotion has **ended** (measured).  The Fleet's MODEL_GONE
    handler disables it; repointing it is class K, so it is the operator's
    call.
  - `V-03` QuotaGate provider limits, 429 body shapes, quota headers.
  - `V-04` `max_total_agents` — needs S-W1; 20 is a placeholder.
  - `V-05` the Overseer's ordered profile list (G-F13).
  - `V-06` OpenCode headless (S-O1) — partly measured.
- **Decisions since last update**: `pilot/decisions.md` D-01 … D-31.
  **D-29** is the D-19/D-20 ratification, recorded as class K queue items
  Q-001 and Q-002 in the event log.
- **Last green test run**: `pytest -q` → see the commit; `pmk sentinel`
  clean and `pmk context drift` clean on 2026-10-23.

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
