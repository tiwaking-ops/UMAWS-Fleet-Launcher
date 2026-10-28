---
document:
  title: "Project state report — UMAWS Fleet (testproject1)"
  status: "Formal assessment report (advisory): evidence gathered by direct execution, not a governance record of this repository"
provenance:
  author_llm: {name: "freebuff-buffy-01 (Buffy, Codebuff)", version: "1.0.0"}
  created_date: "2026-10-26"
  scope: "C:/temp/projects/testproject1 (branch main), read-only assessment plus temporary probe processes that were shut down"
---

**Author:** Buffy (Codebuff agent), agent id `freebuff-buffy-01`
**Version:** 1.0 (`report-codebuff-project-state-v1`)
**Date:** 2026-10-26 (assessed 12:50–13:35 local / 23:50Z 2026-10-25 – 00:35Z 2026-10-26)
**Repository:** `C:\temp\projects\testproject1` · HEAD moved during the assessment: `7c3ff46` → `6764d54`

---

## 1. Executive summary

The **core mechanism of this project is healthy**: 242/242 tests pass, the Kernel's
sentinel reports zero findings, the hash-chain verifies, the one-click demo completes
the full lifecycle to `DONE`, and the Console serves every route. The system does what
its specification says at the mechanism level.

The "not working correctly" symptoms are real but they are **not in the engine** —
they cluster in four places:

1. **The virtual environment is wired to a different repository.** The editable
   install inside this repo's `.venv` points at `C:\temp\projects\toy1`, so the
   `pmk` CLI, the `quotagate` CLI and the documented `start.ps1` console all execute
   *toy1's* source against *this* repo's state (verified by import resolution). The
   tests are unaffected; every documented manual path is.
2. **The project's own governance documents are broken or missing.**
   `docs/BRIEF.md` is a one-line stub containing a path into toy1, `docs/PDD.md`
   (the oracle AGENTS.md designates for verifying work) does not exist, and the
   brief fails `pmk pdd lint` with 8 errors.
3. **The live coordination state is stale/stuck.** Task `T-0001` is `LEASED` against
   a dead pid (16380, confirmed not running) with no exit event, the Fleet still
   lists it as an agent, three worktrees remain registered, and `project_state` is
   `NEW` even though tasks were created, dispatched and one was integrated.
4. **Three known defects sit queued with exact diffs but are unapplied**
   (D-53 event mislabel, D-55 pins break in any clone, D-56 failure-classifier
   gap), and the documentation has drifted from the code (empty `gateway/quotagate/`,
   stale test counts, STATE contradicting its own decisions).

Additionally, the repository was **actively modified by other sessions throughout
this assessment** (HEAD moved, the event log grew 262 → 272 events, a second
agent's report file appeared), so every state reading below is point-in-time.

---

## 2. What this project is meant to do

**UMAWS Fleet** is a Kernel-lite multi-agent coordination system: it runs CLI
coding agents (hermes, kilo, cline, pi, opencode, or a fake CLI) *unattended* on
task cards, and refuses to trust them — **oracles decide**, not the worker's claim.

| Component | Path | Role |
|---|---|---|
| Kernel (`pmk`) | `src/pmk/` | The **only writer** of coordination state: append-only hash-chained event log, task cards, leases with fencing, projections (views), briefing, sentinel (invariants I1–I16), PDD lint, library API and the `pmk` CLI. Standard library only. |
| Fleet | `src/fleet/` | Dispatcher, profile selection, adapters (real + fake CLI), harness (worktree, order file, evidence bundle), recovery ladder L0–L4, Conductor, merge queue, Overseer runner, project lifecycle, manual launcher. |
| Console | `src/console/` | FastAPI view layer on `127.0.0.1:8765`, one HTML page, 7 tabs, SSE live updates. |
| QuotaGate | `src/quotagate/` | Hierarchical quota engine (RPM/TPM/RPD, DST-aware resets) — **M0–M2 core only** (see §6). |
| Tests | `tests/` | 17 files, 242 tests, incl. `tests/fleet/fakecli.py` — every Fleet behaviour is exercised against a scriptable fake CLI first. |
| Pilot record | `pilot/` | STATE.md, decisions.md (D-01…D-56), pilot-report.md, spikes, logs. |
| Coordination state | `.pm/` | Event log, views, tasks, evidence, pinned constitution/policy. Agents never write here directly. |

**Spec sources:** `docs/sources/pilot-proposal.md`, `fleet-launcher-proposal.md`,
`umaws.md`, `quotagate-v1-1.md`, `caliber-integration.md`.

**Key invariants:** I2 (Kernel is the only writer), I5 (oracles decide — no task
reaches `DONE` without a passing `gate_cmd` and an evidence bundle),
I8′ (pinned constitution/policy hashes), I13 (views must equal the projection of
the log), I15/I16 (context lint and drift).

**Documented workflows:** `pmk init/status/brief/sentinel/fleet/agent/project/pdd`
CLI · `start.ps1` → Console · `pilot/demo_one_click.py` → full lifecycle demo ·
`pytest -q` → tests.

---

## 3. How this assessment was performed

All commands ran from `C:\temp\projects\testproject1` on 2026-10-26 with the
project's own venv (`Python 3.12.10`, `pip 26.2.2`). Read-only against `.pm/`
and the pool of project state, except:

* temporary Console/CLI probe processes (documented PIDs, ports 8765/8766) —
  all shut down afterwards; both ports confirmed free and no stray probe
  processes remain;
* the one-click demo — runs only in its own scratch repository under
  `pilot/demo/` and temp, by design.

**Commands run (evidence):** `pytest` (two runs, exit status captured directly,
not through a pipe) · `pmk sentinel` (3×) · `pmk status` (both via this repo's
source and via the venv console script, A/B) · `pmk brief --role overseer` ·
`pmk fleet status` · `pmk agent list` · `pmk pdd lint docs/BRIEF.md` ·
`python -m quotagate --help` · `python -m console.app` + HTTP probes of all 11
GET routes · `pip install --dry-run --no-index -r requirements.lock` ·
`git log/status/worktree list` · event-log parsing · Windows process/ports
inspection (`Win32_Process`, `Get-NetTCPConnection`).

**Concurrency caveat:** other sessions were writing during the assessment
(see §5, P10). Where a reading changed between two moments (e.g. task states
`SUBMITTED` → `DONE`), the event log was re-read to confirm an actual merge
happened (`INTEGRATED 6764d54` at 00:07:48Z) rather than a projection bug.

---

## 4. What is working (verified today)

| # | Check | Command | Result |
|---|---|---|---|
| W1 | Test suite | `python -m pytest` | **242 passed, 0 failed** (72.91s), exit 0; **0** skips/xfails; 0 warnings |
| W2 | Invariant sentinel | `pmk sentinel` | **`ok: true`, `findings: []`** across I1, I3–I8′, I13–I14, I15, I16 — run 3×, including immediately after a concurrent merge |
| W3 | Hash chain | part of `pmk status`/`sentinel` | `I1 chain verifies` — held while the log grew 262 → 272 events under live writes |
| W4 | One-click demo | `python pilot/demo_one_click.py` | **exit 0**; full lifecycle brief → PDD → tasks → claim → worktree → spawn → oracles → evidence → merge → close-check → **`DONE`**; 2 evidence bundles; sentinel clean; chain verifies (32 events) |
| W5 | Console, this repo's source | `PYTHONPATH=src python -m console.app` | Boots; `/` → 200 with `<title>UMAWS Fleet</title>`; **all 11 GET routes → 200** (`/api/project/status`, `/api/fleet`, `/api/agent/list`, `/api/agent/T-0001/log`, `/api/tasks`, `/api/queue`, `/api/overseer`, `/api/metrics`, `/api/launcher`, `/api/events`) |
| W6 | CLI surface | `pmk status` / `brief` / `fleet status` / `agent list` | All exit 0 with correct structured output; `brief --role overseer` renders constitution, policy hash, project state |
| W7 | PDD linter | `pmk pdd lint docs/BRIEF.md` | Tool works correctly: exit 1 with 8 precise, actionable errors against the (broken) brief |
| W8 | Dependency lock | `pip install --dry-run --no-index -r requirements.lock` | Parses (pip tolerates the BOM), every pin satisfied, exit 0 |
| W9 | Live gating, observed mid-assessment | event log | A concurrent session took `T-0003` through the real path: `ORACLE_RESULT {cmd: "pytest -q", ok: true, stage: "gate"}` → `INTEGRATING` → `INTEGRATED` commit `6764d54`, evidence `EB-T-0003-3` — the oracle gate works on the live repo, not just in the demo |
| W10 | Environment basics | `py -V`, git | venv Python 3.12.10 satisfies `requires-python >= 3.11`; git operations healthy (no index.lock contention observed) |

---

## 5. Problems and issues

Severity: **H** = high (silent wrong behaviour / stuck state), **M** = medium,
**L** = low.

### P1 — H — The venv's editable install points at a *different repository* (`toy1`)

**Evidence:**
* `pip show umaws-fleet` → `Editable project location: C:\temp\projects\toy1`
* `.venv/Lib/site-packages/__editable__.umaws_fleet-0.1.0.pth` contains `C:\temp\projects\toy1\src`
* Without `PYTHONPATH`: `import pmk.cli` → `C:\temp\projects\toy1\src\pmk\cli.py`;
  `import console.app, pmk.api` → `...\toy1\src\console\app.py`, `...\toy1\src\pmk\api.py`

**Impact:**
* The `pmk` and `quotagate` console scripts (`.venv\Scripts\*.exe`) run **toy1's code**.
* `start.ps1` (`& $Python -m console.app ...`, no `PYTHONPATH`) launches **toy1's
  console and kernel against this repo's `.pm` state** — the documented way to open
  the Console executes the wrong tree.
* Today the two copies happen to agree (A/B `pmk status` output was byte-identical),
  which is exactly what makes this dangerous: any divergence in toy1 silently
  changes this project's behaviour with no error.
* Tests and the demo are **not** affected (they insert `ROOT/src` at `sys.path[0]`
  themselves — verified in `tests/*/conftest.py` and the demo bootstrap).

**Fix:** from the repo root, `.venv\Scripts\python.exe -m pip install -e .`, then
verify `python -c "import pmk.cli; print(pmk.cli.__file__)"` lands inside
`testproject1`. Re-test `start.ps1` afterwards.

### P2 — H — The brief/PDD governance chain has no real documents

* `docs/BRIEF.md` contains exactly one line: `C:/temp/projects/toy1/docs/BRIEF.md`
  — a pointer into the other repo, not a brief. The Console's
  `/api/project/status` reports this file as the project's `brief`.
* `docs/PDD.md` — the file AGENTS.md names as the verification oracle
  ("Use `gate_cmd` in `docs/PDD.md` to verify work") and README's
  `pmk pdd lint docs/PDD.md` — **does not exist**; no PDD is tracked in git
  anywhere (only the module `src/pmk/pdd.py`).
* `pmk pdd lint docs/BRIEF.md` → 8 errors: missing Purpose, Goals, Non-goals,
  Constraints, Architecture sketch, Definition of done, Open questions; no
  `### G-001`-style goals; missing `gate_cmd`.

**Impact:** the invariant chain brief → PDD → goals → `gate_cmd` → close-check
cannot be exercised at repository level; a fresh reader cannot tell what "done"
means for this project. (The *demo* builds its own brief/PDD in scratch, which
is why W4 still passes.)

### P3 — H — Live Kernel state is stale and stuck

* `T-0001` is **LEASED with pid 16380 — the process is not running** (checked
  via `Win32_Process`). No `AGENT_EXITED`/`REVOKED` event exists for it;
  `pmk agent list` still presents it as a live agent in `work/T-0001-2`.
  The recovery ladder never fired because no Dispatcher/Conductor is running.
  (A second dead-pid lease on `T-0003`/pid 10948 was cleared during the
  assessment by the concurrent merge.)
* **`project_state: NEW`** in both `status` and `/api/project/status`, despite
  3 tasks (1 DONE), 2 leases having run, and 1 incident — the project lifecycle
  was never initialised for this work, so close-check/goals (`goals_total: 0`)
  have nothing to act on.
* **Three worktrees remain registered:** `work/T-0001-1`, `work/T-0001-2`,
  `work/T-0003-3` (branches `pmk/…`); `T-0003-3` was just merged, `T-0001-*` are
  orphaned with a dead lease.

**Impact:** the Fleet believes it has workers; tasks can sit `LEASED` forever;
the status screen cannot be trusted without checking pids.

**Fix path:** run the documented recovery (or revoke the stale lease through
`pmk`), then either initialise a project properly or void the stray test tasks,
then retire the merged/orphaned worktrees.

### P4 — M — Three known defects are recorded with exact diffs but NOT applied

| Ref | Defect | State |
|---|---|---|
| **D-53 / open queue item Q-005** | `AGENT_RESUMED` is emitted with `mode:"new"` when a fresh session starts (label wrong; behaviour correct — should be `AGENT_RESTARTED`) | Queued with exact diff; **not applied** |
| **D-55** | Pins are line-ending dependent: with `core.autocrlf=true`, **a fresh clone fails sentinel I8′** (constitution/policy hashes mismatch) | `.gitattributes` diff queued; class-K two-key change; **not applied** |
| **D-56** | Failure classifier misses OpenRouter `Insufficient credits` text → tasks classified `UNKNOWN` | Pattern diff queued; class-K; **not applied** |

**Impact:** any clone/CI of this repo is red at I8′ until D-55 lands; event
records mislead until D-53 lands; quota failures stay `UNKNOWN` until D-56 lands.
These are deliberate "queue, don't edit" decisions — they now need their gates.

### P5 — M — The `quotagate` CLI silently starts a server instead of answering `--help`

`python -m quotagate --help` ignores `--help`, boots Uvicorn on
`http://127.0.0.1:8766` (observed: `Uvicorn running on http://127.0.0.1:8766`)
and never exits — killed only by an external timeout (exit 124). An operator
probing the CLI gets a background HTTP service with no usage text.

**Fix:** argparse with `--help`/`--port`/`serve` subcommand; never bind a port
as the response to `--help`.

### P6 — M — Documentation drift (architecture, metrics, cross-references)

1. **`gateway/quotagate/` is an empty directory.** README, CLAUDE.md, STATE.md
   and the pilot report all locate QuotaGate there; the real code is
   `src/quotagate/` (2,112 lines) and `pyproject.toml` only packages `src/`.
2. **Test counts stale everywhere:** README "~150", pilot-report 188 (10-22),
   STATE 234 (10-24) — **actual 242**. LOC claims stale (pmk 3,773 → 5,772;
   fleet 3,507 → 4,653; console 375 → 478; quotagate 903 → 2,112).
3. **STATE.md contradicts its own decisions:** Blocked list says "pi live-unrun",
   while D-54 records a real pi dispatch (`p_id=10948`, openrouter 429 → UNKNOWN).
4. **Pilot report vs STATE conflict on Caliber:** the report (10-22) says
   "Caliber not installed / context sync not built"; STATE (10-24) says Caliber
   1.55.2 installed, spikes S1–S5 complete, G1 baseline installed, G4 auto-sync
   ON. The report is explicitly candidate-tier, but a reader hitting §1's table
   first gets the wrong picture.

### P7 — L — `requirements.lock` encoding and content

* The file is **UTF-16LE** (PowerShell `Out-File` artefact). pip 26 tolerates the
  BOM (verified), but a plain UTF-8 read fails (`UnicodeDecodeError` at `0xFF`),
  and most lock-file tooling/editors/CI will not decode it.
* It pins `openelemeter-api`, which is **not** in `pyproject.toml` dependencies
  and is not referenced anywhere under `src/`, `tests/`, `gateway/` or `pilot/`.

**Fix:** re-save as UTF-8/LF; drop or justify the stray pin.

### P8 — L — The pytest summary line is suppressed by default

`pyproject.toml` sets `addopts = "-q"`, and README says run `pytest -q` →
double-quiet → **no "N passed" line** (dots only, exit code still correct). CI
logs and humans get no visible pass count. (Measured: the summary
"242 passed in 72.91s" only appeared with `-o addopts=…`.)

**Fix:** drop the `-q` from `addopts` (or from the README) so one quiet level
remains and the summary prints.

### P9 — L — Working-tree hygiene

Uncommitted/untracked at report time: `M agents.toml` (2 comment lines),
`M .pm/events/2026-10-25.jsonl`, `M .pm/views/*` (tracked Kernel output — the
tree stays permanently dirty under live use), `?? .pm/events/2026-10-26.jsonl`,
`?? assesment-claude-toy3-v1.md`, `?? docs/free-models.md`,
`?? prompt-claude-to-hermes-toy3-instructions.md`, `?? pytest_out.txt`,
`?? pytest_out2.txt`, `?? single.txt` (scratch files, not from this assessment —
this assessment wrote only to `/tmp`), `?? report-deepseek-project-state-v1.md`
(a concurrent analysis session's report). Nothing here was touched by this
assessment.

### P10 — Observation (risk) — The repo was written by other sessions throughout

* HEAD moved mid-assessment `7c3ff46` → `6764d54` (the T-0003 merge).
* Event log grew 262 → 272, including **six `OVERSEER_WOKEN` events at a 60s
  cadence (00:07:48Z–00:12:53Z), all `reason: "incident"`, all
  `started: true`** — each spawning an Overseer session. The repository's only
  recorded incident is the historical Q-001 duplicate-id (fixed, D-32). If a
  Conductor runs while that incident can never clear, this is a **spurious
  wake loop** worth verifying.
* Another agent's report file appeared in the repo root during the assessment.

**Impact:** findings are point-in-time; concurrent dispatchers/analysts reading
and writing the same checkout is itself a hazard (the Kernel serialises `.pm`
writes, but git HEAD, worktrees and untracked files are not so protected).
Assessments and dispatch runs should be scheduled one at a time.

---

## 6. What is not working, not built, or not verified

From the project's own records (pilot-report §1/§7, STATE.md, decisions.md),
corroborated by today's checks:

| Item | State | Note |
|---|---|---|
| QuotaGate **M1 passthrough proxy, M3 failover, M5 Kernel contract** | **Not built** | Only the M0–M2 engine exists (`src/quotagate`). Upstream behaviour measured (D-38/D-42); M1 still owed. |
| `docs/PDD.md` + repository-level gate chain | **Missing** | P2 above. |
| Five cline models (`cline-mimo`) | **Offered, not verified** | Needs live provider calls — its own authorisation (D-35). |
| Real-CLI failure classification | **Partial** | cline MODEL_GONE and opencode QUOTA captured; **hermes/kilo/pi have no patterns** → `UNKNOWN`; only exit codes 0/1 observed. (D-56 would add the OpenRouter-credit pattern.) |
| `V-07` generator injection safety | **Unproven** | T4's premise did not reproduce — "unproven rather than proven safe". |
| `V-03` provider 429 shapes / quota headers | **Unverified** | Classifier falls back to `unknown_429` + 60s cooldown (tested fallback). |
| `V-05` Overseer ordered profile list | **Placeholder** | Needs the operator's input. |
| `V-06` OpenCode Overseer session-resume path | **Partly measured** | Headless ran; resume untested. |
| pi live dispatch | **Ran once, failed on quota** | D-54 (openrouter 429); STATE still lists it as unrun — reconcile (P6.3). |
| Acceptance tests F1/F4/F9/F14 | **Not run** | Need real LLMs / ≥3 profiles (operator chose metadata-only probing). F7 scale drill **passed** 100/100 (D-48). |
| H2/H7/H11/H12 hypotheses | **Untested / since partly superseded** | 10-22 report; F7/S-W1 closed H11 per STATE. |
| Live state recovery (T-0001, worktrees, project_state) | **Not performed** | P3. |
| Console authentication | **None — by design** | Loopback-only bind; `start.ps1` documents the rationale. Fine for a local tool; do not expose the port. |

---

## 7. Recommendations

**Do first (small, removes the worst risks):**

1. **Repoint the editable install** at this repo and verify `pmk.cli` resolves
   inside `testproject1` (P1). Then re-run `start.ps1` and confirm the Console
   imports from this repo's `src/`.
2. **Write a real `docs/BRIEF.md`** — the sections `pmk pdd lint` demands
   (Purpose, Goals with `### G-001`, Non-goals, Constraints, Architecture sketch,
   Definition of done **with `gate_cmd`**, Open questions) — and settle whether
   `docs/PDD.md` is the oracle document AGENTS.md refers to; generate it and lint
   it (P2).
3. **Recover the live state** (P3): revoke/reap the dead `T-0001` lease through
   `pmk`, decide the fate of the stray test tasks and `project_state`, retire the
   three registered worktrees once their branches are merged or abandoned.
4. **Fix the `quotagate` CLI** so `--help` prints help and never binds a port (P5).

**Then, through the project's own gates:**

5. **Apply the queued diffs** in their required order of ceremony: **D-55**
   (`.gitattributes` eol=lf + `pmk pins record` — class K, two-key, *before* the
   change), **D-53/Q-005**, **D-56** (P4). After D-55, prove it by running
   `pmk sentinel` in a fresh clone — that is the regression test for this defect.
6. **Correct the documentation** (P6): `gateway/quotagate` → `src/quotagate`
   everywhere; refresh test/LOC counts (or quote them as dated); reconcile STATE
   vs pilot-report on Caliber and on pi (D-54).
7. **Re-save `requirements.lock` as UTF-8** and drop/justify `openelemeter-api` (P7).
8. **Restore the pytest summary** by removing the stacked `-q` (P8).
9. **Repository hygiene** (P9): commit or discard the operator docs, move scratch
   files out of the repo root, and decide whether daily event-log files belong in
   git at all (the tree is permanently dirty under live use).

**Process:**

10. **One writer at a time.** During this assessment the HEAD, the event log and
    the untracked file set all changed underfoot (P10). Schedule dispatch runs and
    deep assessments separately.
11. **Investigate the `OVERSEER_WOKEN reason="incident"` 60s loop** (P10): confirm
    a long-running Conductor cannot wake the Overseer forever against a
    historical, already-voided incident.

**Medium term (project's own backlog, unchanged):** QuotaGate M1 proxy with
timeout policy and locally declared limits; declare a verifier profile family
(D-43/D-44); verify the five cline models (needs authorisation); close V-03/V-05/
V-06/V-07 as listed in §6.

---

## 8. Bottom line

* **Working:** the engine — tests (242/242), sentinel (0 findings), hash chain,
  the one-click lifecycle, the Console's full read surface, the CLI, the oracle
  gate observed on a live integration. The architecture's central promise
  ("oracles decide, the Kernel is the only writer") is demonstrably in force.
* **Not working:** the *environment and paperwork around* the engine — the venv
  executes a sibling repo's source, the brief/PDD documents are stubs or absent,
  the live state holds a dead-pid lease and an uninitialised project, three known
  fixes sit unapplied, and the docs describe an older layout than the code.
* None of the failures found are data loss or corruption: the chain verifies and
  the sentinel is clean. They are miswiring, stale state, and unapplied fixes —
  all addressable in the order given in §7.

---

*End of report — `report-codebuff-project-state-v1.md`, author `freebuff-buffy-01`
(Buffy, Codebuff), version 1.0, 2026-10-26. All claims above were executed and
observed in this repository on the stated date; items taken from the project's
own records are attributed to those records.*
