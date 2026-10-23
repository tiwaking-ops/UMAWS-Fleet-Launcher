# Pilot P-01 state (update at every checkpoint)

- **Updated**: 2026-10-24 by OpenCode (implementing agent, Phase 1) — the
  two latent defects fixed (D-51); the operator raised `max_total_agents`
  to 100 (D-50, their edit).
- **Phase**: 1 — bootstrap. **Day**: 2. **Tier reached**: A (+ a working
  Fleet). **Projected**: see "Cuts".
- **Gate posture** (the operator's rule, D-25, **amended in force as v2**,
  D-34 — `pilot/amendment-gates.md`; the pilot v1 §12.1 default it replaces
  is recorded as a defect at report §4.4). **Classification is by action,
  not by gate number:**

  | Point | Action | Kind | Status |
  |---|---|---|---|
  | G0 | the platform decision | **authorisation** | **authorised** — operator's instruction, D-02 |
  | G0 | environment metadata | checkpoint | logged (`s-p1-platform.md`) |
  | G1 | measuring Caliber (S1–S5) | checkpoint | logged (`caliber-s1-s5.md`) |
  | G1 | installing Caliber | **authorisation** | **authorised** — D-15…D-19 |
  | G1 | sync sending repo content to providers | **authorisation** | **authorised** — terms accepted, D-23 |
  | G2 | metadata capture | checkpoint | logged (`cli-matrix.md`) |
  | G2 | live S-A1 provider calls | **authorisation** | **authorised with terms** — D-24 |
  | G3 | real CLI through a lease; restart from the briefing alone | **authorisation** | **CLOSED** — real-CLI half passes (D-39); OpenCode handover half **PASSES** on the named CLI 2026-10-23 (D-45, `pilot/g3-opencode-handover.md`) |
  | G4 | Caliber auto-sync on | **authorisation** | **CROSSED 2026-10-23** — operator's instruction, exact diff accepted as Q-004; `mode = "auto"` (D-47); left on per the operator's choice |
  | G5 | live capacity run | **authorisation** | **CROSSED 2026-10-23** — two live runs, 6 concurrent real workers, 6/6 DONE, close-check green, zero failures (D-49) |

  **"Self-crossed" is retired** (D-34): a crossing is either authorised by a
  named decision or logged as a checkpoint. A gate is crossed **once per
  mechanism**, and an approval covers that mechanism and no other.
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
  - **H6 handover evidence** (D-36): four fresh sessions, two seeds, all
    correct from the briefing alone — on **kilo**.  OpenCode could not run
    (`free-models-per-day`), so the gate stays open.
  - **`cline-mimo` repointed** to the operator's five offered free models
    (D-35); none of the five is verified yet.
  - **G3's real-CLI half PASSES** (D-39): kilo took `T-0002` through a real
    lease in a real worktree against a **functional** oracle, merged with the
    gate green.  Evidence in `pilot/spikes/g3/`.
  - **M1's upstream measured** (D-38): usage capturable, **no** quota headers,
    and no `/v1` on the upstream.  Record in `pilot/spikes/m1-upstream.md`.
  - **234 tests passing** (2026-10-24; 227 before, +7 regression tests for
    the D-51 defect fixes). `pmk sentinel` clean on the live repository.
  - `pilot/demo_one_click.py` runs the full lifecycle green: brief → PDD →
    tasks → claim → worktree → order → spawn → harness-run oracles →
    evidence bundle → merge queue → close-check → **DONE**.
  - Every Phase 1 commit is tagged `bootstrap/0` … `bootstrap/16`.
- **In progress**: nothing.  G3's condition, G4, G5, F7 and S-W1 all
  landed 2026-10-23.
- **Next**:
  1. **Sweep the quota bounds** of the remaining hermes free-tier models with
     `pilot/quotadiscover.py` (D-42).  `upstage/solar-mini4` is measured:
     no ceiling found below 45 requests per 3 s, latency 889-4250 ms.  The
     operator said the models may be tested.
  2. **Build QuotaGate M1** (the passthrough proxy).  Its upstream behaviour is
     now measured (D-38, D-42): usage is capturable, quota headers do
     **not** exist, and the two upstreams disagree about `/v1`.  So M1 needs a
     timeout policy and locally declared limits.
  3. **Declare a family for a verifier profile** (D-43/D-44).  Provenance
     is now live (`MODEL_SERVED` at submit, compared by `select.py`),
     but it can only *narrow* eligibility: every `agents.toml` profile
     still declares `family = "unknown"`, so D-L12's unknown-family
     veto is what actually gates verification.  Naming one is the
     operator's call, not the implementer's.
  4. **Verify the five cline models** — offered, not working (D-35).  Costs
     live provider calls, so it is its own authorisation.
  5. ~~Run **S-W1** and test **F7**~~ **DONE (D-48)**: F7 passes 100/100 at
     peak 100 concurrent slots (105 s, RAM 7 491 MB min); S-W1 measured.
           `max_total_agents` raised 20 -> 100 **by the operator's edit**
      (2026-10-23 23:55, D-50; G-F5 satisfied).  The two latent defects
      **FIXED 2026-10-24 (D-51)**: invalid `policy.toml` stops the line
      (`KernelError("policy_invalid")`), and re-integration of an
      already-committed lease runs the gate; 7 regression tests,
      234 passing, sentinel clean.
 - **Blocked / awaiting human**:
  1. **pi live-unrun** — G5 never needed it (hermes+kilo filled all
     six slots); its first live dispatch is still unexercised.
  2. **Verifying the five cline models** — needs an authorisation for live
     calls; the operator reports their rate limit resets 2026-10-24.
  3. ~~**G4/G5**~~ — both **crossed** 2026-10-23 (G4: D-47, Q-004, left on;
      G5: D-49, passed twice).
- **Open [VERIFY] items**:
  - `V-01` **mostly closed**: headless, resume and (for pi) model-switch
    are measured.  **Still open**: hermes, kilo and pi have no captured
    failure text, so their failures are `UNKNOWN`; the exit codes are only
    0 and 1; and no real CLI has been driven end to end through a lease.
    The *briefing handover* half is measured on kilo (D-36) and, since
    2026-10-23, on **opencode itself** (D-45).
  - `V-02` **closed**: Caliber's overwrite semantics (S3) and determinism
    (S5) are measured.
  - `V-07` **new**: the generator has **not** been shown to be safe
    against injection.  T4's premise did not reproduce — three planted
    injections were not copied into the context files — so the generator
    is unproven rather than proven safe.
  - `V-08` **new**: the lint's coverage limit is measured and pinned
    (D-21).  The residual protection is the combination of lint, score
    gate, blind V2 review and audit.
  - `V-09` **partly closed**: the profile is repointed to the operator's
    five offered free models (D-35), so the dead model string is gone.  But
    **none of the five is verified** — that needs live calls — and the Fleet
    still reports a profile as `ready` without testing its model, so the
    first dispatch is where MODEL_GONE gets discovered.
  - `V-03` QuotaGate provider limits, 429 body shapes, quota headers.
  - `V-04` `max_total_agents` — **closed (D-48/D-50)**: S-W1 and
    F7 both pass at 100 slots on this machine; the operator raised
    20 -> 100 in `agents.toml` themselves (2026-10-23 23:55).
  - `V-05` the Overseer's ordered profile list (G-F13).
  - `V-06` OpenCode headless (S-O1) — partly measured.
- **Decisions since last update**: `pilot/decisions.md` D-01 … D-51.
  **D-29** is the D-19/D-20 ratification, recorded as class K queue items
  Q-001 and Q-002 in the event log. **D-32/D-33** are the queue-id collision
  and the projection that let a duplicate overwrite a decision; **D-34** is
  the gate amendment in force (class K item Q-003); **D-35** the cline
  repoint; **D-36** the H6 result; **D-37** the OpenCode quota parked as
  `UNKNOWN`; **D-38** the M1 upstream measurement; **D-39** the real-CLI
  through a real lease, which passes; **D-40** the operator closing G3;
  **D-41** the recovery ladder exercised with real CLIs, L4 and L3 for
  real, real recovery, and the L1-labelled-but-new-mode defect; **D-42**
  quota discovered by stress test, first measurement on solar-mini4;
  **D-43** OpenRouter is account-limited and Kilo Gateway model-limited,
  so `kilo-auto` defaults to `kilo/kilo-auto/free` with the free models as
  its L1 swap targets.
- **Session report (2026-10-23)**: `pilot/report-opencode-2026-10-23.md` — the recovery ladder with
  real CLIs, QuotaGate M1, provider and model limits, and
  provenance.  Advisory record; decisions D-39 … D-44.
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
