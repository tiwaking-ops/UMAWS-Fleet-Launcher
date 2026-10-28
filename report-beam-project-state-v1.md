# Project State Report — UMAWS Fleet (C:\temp\projects\testproject1)

**Author (author_llm):** Beam 1.0 501B A23B  
**Report version:** v1  
**Date:** 2026-10-26  
**Repository:** C:\temp\projects\testproject1  
**Git HEAD:** `6764d54` (Merge branch 'pmk/T-0003-3')  
**Working state:** dirty (modified `.pm/events`, `.pm/views`, `agents.toml`; untracked event/assessment files)

---

## 1. Executive summary

UMAWS Fleet is a **Kernel-lite coordination runtime for running CLI coding agents unattended**. It is not a normal application server: its central invariant is that **the Kernel (`pmk`) is the only writer of coordination state**, while a Fleet Dispatcher supervises CLI profiles, Harnesses record evidence bundles, and a FastAPI Console is only a view. The project is built as pilot P-01 plus the Fleet amendment A1, with roughly 10.9 kLOC in `src/` and 2.9 kLOC in `tests/`.

In the state examined here, **the codebase itself passes its own test contract** (`242/242` passed when imported from `src/`), the Kernel sentinel is clean, and the Console answers HTTP/JSON. However, **the project is not operationally coherent**:

- the virtual environment's editable install points **not at this repository** but at a sibling copy (`C:\temp\projects\toy1`), so installed commands run a different code state;
- the Kernel project is still in state `NEW`, with **no PDD committed**, a brief that points to that sibling copy, a stale live lease, and an open Class K queue decision;
- at least one task (`T-0003`) is marked `DONE` while its recorded evidence bundle shows a failing oracle, and its provenance record is inconsistent;
- several known-platform defects remain unresolved (Windows-incompatible oracles, OpenCode session/resume claims, unverified Cline models, unknown model families, missing QuotaGate M1 proxy).

In short: **the repository is a healthy but incomplete pilot**. Its Kernel/findings tests pass; its project run state and environment binding do not. Real end-to-end multi-agent dispatch should not be attempted until the items in §5 are closed.

---

## 2. What the project is meant to do

### 2.1 High-level purpose

From `README.md`, `CLAUDE.md`, `AGENTS.md`, and the pilot record:

- Provide a **Kernel** (`src/pmk/`, standard library only) with an append-only JSONL event log, task cards, leases with fencing, views, briefings, PDD lint, sentinel invariant checks, and a CLI/API.
- Provide a **Fleet** (`src/fleet/`) that supervises CLI agent profiles through adapters (`hermes`, `kilo`, `cline`, `pi`, `opencode`, `fake`), claims tasks, starts them in worktrees, runs oracles, collects evidence, and performs recovery (L0–L4).
- Provide a **Console** (`src/console/`, FastAPI, port 8765) with seven tabs (Projects, Fleet, Tasks, Queue, Overseer, Manual launcher, Metrics) over `pmk.api` and Fleet state.
- Provide **QuotaGate** (`src/quotagate/`) — a hierarchical quota engine (RPM/TPM/RPD, rolling and fixed windows, timezone-aware resets) used to gate gateway-routed model calls.
- Support a "fake first" workflow: every Fleet behaviour is tested against `tests/fleet/fakecli.py` before any real CLI or quota is used.

### 2.2 Governing rules (relevant to the report)

- **I2 (Kernel only):** nothing edits `.pm/` except `pmk`.
- **I5 (Oracles decide):** no task reaches `DONE` without a passing `gate_cmd` and an evidence bundle.
- **I8 (Pinned policy):** constitution and policy are hashed in `.pm/pins.sha256`.
- **I13 (Views are projections):** views must equal the projection of the log.
- **I15 (Context lint)** and **I16 (Drift check)** govern generated agent context.
- Windows-native: sidecar locks, ASCII prompts, BOM-tolerant reads.

### 2.3 Intended operator flow

1. `pmk init` creates the layout, first event, pins.
2. `pmk project init` + write `docs/PDD.md` define goals, tasks, oracles.
3. `pmk brief --role overseer` is the authority for the current state.
4. Dispatcher assigns a task/profile; Harness runs in a worktree and records an evidence bundle in `.pm/evidence/`.
5. A passing oracle gates `DONE`; merge queue closes the project; `close-check` verifies.
6. Console shows state and lets the operator run/pause/cool/disable profiles.

---

## 3. Repository inventory and measured state

### 3.1 Source / test scale (measured, 2026-10-26)

| Area | Python files | Lines |
|---|---:|---:|
| `src/` (pmk, fleet, console, quotagate) | 47 | 10,982 |
| `tests/` | 22 | 2,945 |
| `src/console/static/index.html` | 1 | (single-page Console) |

Key environment:

- `.venv`: Python 3.12.x (claimed by the project; README prescribes 3.12).
- Installed packages observed: `fastapi`, `uvicorn`, `httpx`, `tzdata`, `pytest`.
- `agents.toml`: 6 profiles (`hermes-oneshot`, `kilo-auto`, `pi-orca-deepseek`, `cline-mimo`, `opencode-strongest`, `opencode-fallback`), fleet cap 100, dispatch state currently paused by default.
- `.pm/events/`: 5 JSONL day files; Kernel chain reports **273 events, I1 verifies**.
- `.pm/evidence/`: 1 bundle (`EB-T-0003-3`).
- `.pm` state: `project_state = NEW`, `tasks = 3` (`DONE=1`, `LEASED=1`, `READY=1`), `active_leases = 1`, `open_queue_items = 1`, `incidents = 1`.

### 3.2 Git state (measured)

- HEAD: `6764d54 Merge branch 'pmk/T-0003-3' into HEAD`.
- Uncommitted modifications:
  - `.pm/events/2026-10-25.jsonl` (one appended `SENTINEL_RUN`)
  - `.pm/views/ledger.md`, `.pm/views/status.md`
  - `agents.toml` (comment-only addition: free-model reference)
- Untracked:
  - `.pm/events/2026-10-26.jsonl`
  - assessment / prompt files and `pytest_out.txt`.

### 3.3 Verification commands actually run during this assessment

| Command / evidence | Result |
|---|---|
| `pytest` under `PYTHONPATH=C:\temp\projects\testproject1\src` | **242 passed in 104.95s** |
| `pmk sentinel` under testproject1 `src` | clean — findings `[]` |
| `pmk context drift` | clean — no changed/added/removed managed files |
| `pmk status` | I1 chain verifies (273 events); project `NEW` |
| `pmk fleet status` | 6 ready profiles, 100-slot cap, `dispatch_paused=true` |
| Console `http://127.0.0.1:8765/` | HTTP 200; `/api/fleet`, `/api/tasks` (etc.) respond |
| `pmk` as currently installed (editable) | imports code from `C:\temp\projects\toy1`, not this repo |

### 3.4 What is demonstrably working

- **Kernel invariant machinery**: sentinel clean, drift clean, hash chain intact.
- **Task/event substrate**: events are hash-chained, leases are tracked, views rebuild from the log.
- **Test contract**: 242 tests pass on the testproject1 source under an explicit `PYTHONPATH`.
- **Fleet model**: profiles, slots, cap, adapter registry, and manual-launcher port are defined and loadable.
- **Console**: process currently (PID 1384) answers on loopback and renders its page; dispatch/conductor loops are running.
- **QuotaGate core tests**: included in the 242 passed.
- **Recovery / two-phase design**: `Dispatcher._restart_on` correctly distinguishes resume vs. restart modes; L1 recovery intent is visible.

---

## 4. Evidence for the known-good parts

The clean results above are meaningful, but should be read with the packaging caveat in §5.1. On the testproject1 source forced via `PYTHONPATH`:

- `pmk` does **not** need the editable install to resolve this repository;
- the 242 tests include Kernel (events, leasing, locks, views, safety), Fleet (selection, provenance, recovery, harness, merge, conductor, Overseer, project lifecycle), and QuotaGate;
- the Console's `/api/project/status`, `/api/fleet`, `/api/tasks`, `/api/queue`, `/api/metrics` endpoints return structured JSON.

---

## 5. Issues, defects, and open risks

### Severity legend

- **Critical** — prevents or misrepresents real runs.
- **High** — breaks intended guarantees (e.g. I5).
- **Medium** — correctness/audit defect.
- **Low** — hygiene or documentation defect.

### 5.1 [Critical] Editable install points at the wrong tree

Observed:

```
pip show umaws-fleet
Editable project location: C:\temp\projects\toy1
python -c "import pmk, quotagate; print(...)"
# -> C:\temp\projects\toy1\src\...
```

Consequences:

- `pmk`, `quotagate`, and `import pmk/fleet` resolve to the **sibling `toy1`**, not to `testproject1`.
- The Console process on port 8765 (PID 1384) is therefore almost certainly running `toy1` code, not this repository's code.
- `quotagate.exe --help` fails with `ImportError: cannot import name 'main' from 'quotagate.__main__'` because that sibling tree lacks/exports a different `__main__`.
- Any measurement attributed to "testproject1" through installed commands is suspect until reinstalled.

Recommended fix: reinstall editable from this repository, then verify import paths (§7).

### 5.2 [High] Project is still in state `NEW` and has no PDD

- `pmk project status` returns `"state": "NEW"`, `"pdd": null`, `"report": null`.
- `docs/BRIEF.md` contains only a path to `C:/temp/projects/toy1/docs/BRIEF.md`, not a project definition.
- `docs/PDD.md` does not exist.
- 3 task cards were admitted (`G-TEST-PI`) before the project's design document existed.

This violates the intended lifecycle in §2.3 and means the brief passed to any Overseer/agent is a cross-pointer into another repository's scratch state. The Console's "Projects" workflow cannot be considered exercised.

### 5.3 [High] Stale lease and unfinished rework task

- `T-0001` remains `LEASED` after 2 attempts of a maximum of 3.
- Its active lease holder is `opencode-strongest`, fence 2, with no successful completion recorded.
- `T-0002` is `READY` for the same title and scope but has never been dispatched.
- `T-0003` is `DONE` after 4 `UNKNOWN` failures and 4 restarts.

This is an unhealthy admission: two of three tasks for the same goal are unproductive (one leased, one ready) while one is closed. The project currently has no clean "all tasks done / close-check passed" state.

### 5.4 [High] `T-0003` is `DONE` with a failing evidence bundle

`EB-T-0003-3/bundle.json` records:

- oracle command exited `1` (`ok: false`);
- the bundle's stated oracle was not the task card's Windows-incompatible one (`test -f pi-test.txt && grep -q pi pi-test.txt`) but a Python variant, which still failed;
- `resolved_models` records `{"profile": "pi-orca-deepseek", "model": "", "family": "hermes"}`, even though the task's holder was `pi-orca-deepseek` and the resolution family is a CLI name, not a model family;
- `context_hash` is empty.

Together with failure class `UNKNOWN` (no captured failure text) and 4 restarts, this means **invariant I5 cannot be considered actually satisfied for `T-0003`**, even though the Kernel state says `DONE`. The acceptance criterion needs an audit before this task is trusted (and before `pi` is relied on for anything).

### 5.5 [High] Windows-incompatible oracle language in task cards

The task cards use POSIX shell expressions:

- `test -f hello.txt && grep -q hello hello.txt`
- `test -f pi-test.txt && grep -q pi pi-test.txt`

On native Windows, `test` and `grep` are not guaranteed available; the stderr recorded in historical bundles is exactly `'test' is not recognized as an internal or external command`. The ingestion/handoff path also let a POSIX oracle reach the harness. `pmk pdd lint` and the task admission process do not reject platform-incompatible gates. This is a permanent source of false failures and must be made an admission error.

### 5.6 [Medium] `AGENT_RESUMED` vs. `AGENT_RESTARTED` mislabel (open queue Q-005)

- 4 event-log entries record `AGENT_RESUMED` with `payload.mode = "new"`, even though the code comment at `dispatcher.py` says the type should be `AGENT_RESTARTED` when `mode != "resume"`.
- `cli.py` still records `AGENT_RESUMED` unconditionally for `cmd_agent_swap` (operator swap), where the correct type is arguably `AGENT_RESTARTED`.
- Queue item **Q-005 is open** and awaiting a decision; no resolution was applied.

The log therefore contains semantic labels that disagree with their payloads, which corrupts any later audit, replay, or provenance query.

### 5.7 [Medium] OpenCode adapter claims (resume / model) are overstated

- `agents.toml` itself notes that OpenCode had no `--model` flag and previously used an unpaid OpenRouter account; although the profile is now repointed to `poolside/laguna-s-2-1:free`, there is little direct evidence that the adapter behaves correctly against that model.
- Family is reported as `opencode` rather than `poolside`, so D-L12's model-based verification narrowing is not effective for this profile.
- Pi's resume path for `--continue` and its failure-class text are not captured (failures remain `UNKNOWN`).

These profiles should be treated as **unverified** until their model calls are observed end to end.

### 5.8 [Medium] Cline models are unverified

- `agents.toml` documents that `cline-mimo` was repointed to five offered free models and that **none of the five has been verified**.
- The Fleet still reports such a profile as `ready` without testing the model, so `MODEL_GONE` would only be discovered at first dispatch.
- Open item V-09 remains open.

### 5.9 [Medium] Provenance / family data are not yet meaningful

- Every profile in the current `agents.toml` exports a **family that is effectively a vendor/CLI label** (e.g. `opencode`, `deepseek`, `minimax`, `google`), not a resolved model family.
- `resolved_models` does not carry a model id for direct-CLI profiles (correctly empty per `L-F2`), but the side-effect is that D-L12's unknown-family veto remains the dominant gating factor.
- Evidence bundles inherit the same incomplete identifiers (see §5.4).

The provenance machinery exists and is tested, but its **data** are currently too coarse to perform the independence check it was designed for.

### 5.10 [Medium] QuotaGate is split across two locations with a broken CLI shim

- The project documentation and `CLAUDE.md` refer to `gateway/quotagate/`, but that directory is empty.
- The actual implementation lives in `src/quotagate/`.
- The installed `quotagate` entrypoint resolves to the sibling `toy1` tree and fails to import `main`.
- Core logic is present and tested, but there is **no M1 passthrough proxy** despite extensive configuration for `omniroute` and `hermes` upstreams. The current system is a quota *engine plus config*, not a functioning proxy.

### 5.11 [Low] Cross-references point outside this repository

- `docs/BRIEF.md` points to `C:/temp/projects/toy1/docs/BRIEF.md`.
- The editable installation and other "scratch" artifacts direct work toward the sibling project.
- Worktree `work/T-0003-3/` and its test copy exist, but no clear policy says which is canonical.

This repository is not a self-contained object right now.

### 5.12 [Low] Context drift is clean, but the drift system does not cover project state

- `pmk context drift` is clean for `AGENTS.md`, `CLAUDE.md`, rules, and skills.
- It does **not** catch the things that actually matter here: project state `NEW`, no PDD, stale lease, open queue, failing evidence bundle.
- Passing the drift check should therefore not be reported to the user as "the project is healthy".

### 5.13 [Low] Test suite is slow relative to its size

- Full run: ~105–110 s for 242 tests.
- No per-module parallelism or focused integration profile is evident.
- This slows the "real-run" feedback loop and makes environment regressions (like §5.1) harder to notice.

---

## 6. Recommendations

### Priority 0 (fix before any real run)

1. **Rebind the environment to this repository.**
   - Uninstall/reinstall `pip install -e C:\temp\projects\testproject1 --no-deps`.
   - Verify:
     - `pmk` resolves to `C:\temp\projects\testproject1\src\pmk`,
     - `python -c "import pmk, fleet, quotagate"` paths are correct,
     - `quotagate --help` works.
2. **Audit and, if necessary, de-close `T-0003`.**
   - Either re-run the oracle with a Windows-native command and record a passing bundle, or submit `premise-refuted` / `rework` with evidence.
   - Do not count `T-0003` toward completion for pricing/grading until I5 is genuinely satisfied.
3. **Resolve Q-005** and re-label misrecorded `AGENT_RESUMED` events as `AGENT_RESTARTED` (`mode=new`) or refactor operator swaps (`cmd_agent_swap`) to use `AGENT_RESTARTED`. Add a regression test asserting no `AGENT_RESUMED` event exists with `mode=new`.
4. **Define a real project in this repository:** write `docs/BRIEF.md` and `docs/PDD.md` (goal refs `G-…`), then run `pmk pdd lint docs/PDD.md` and `pmk project init`. Ensure `project status` shows `PDD` and a non-`NEW` state.
5. **Kill or complete the stale lease on `T-0001`** after a `pmk brief`, then either dispatch `T-0002` or close both tasks as superseded with evidence.
6. **Make oracle admission Windows-aware.** Reject tasks whose `oracles` contain POSIX-only commands (`test`, `grep`, `&&` shells where absent) unless the profile declares a POSIX environment. Accept only `cmd /c` or Python/Powershell oracles by default on this platform. This is the direct root cause behind §5.4/§5.5.

### Priority 1 (restore intended capabilities)

7. **Reconcile the QuotaGate location.** Either move `gateway/` content into documentation or move the implementation under `gateway/quotagate/` and update imports and tests; document the canonical path in `README/CLAUDE`. (Current state: code in `src/quotagate`, empty `gateway/quotagate`.)
8. **Build QuotaGate M1** (passthrough proxy using `config.toml` upstreams) or remove that config-driven promise from docs. Until M1 exists, profiles with `via_gateway=false` cannot be budgeted centrally, and gateway-routed budgets remain theoretical.
9. **Verify OpenCode and Pi end to end.** Replace `UNKNOWN` failure classes with captured stderr/exit codes; record actual session resume behaviour; assert the `pi` model id appears in `resolved_models` after `MODEL_SERVED` events. Update safety claims in docs to match measured results.
10. **Verify (or prune) Cline models.** Either authorise the small number of live calls needed or remove unverified profiles from `ready` state and mark them `unverified`. A `ready` profile that has never succeeded is a false assurance.
11. **Populate model family data** so `resolved_models` and selection can actually narrow by family. Today families are vendor/CLI labels, which makes D-L12's veto mostly constant rather than informative.

### Priority 2 (engineering quality and measurement)

12. **Reduce test runtime.** Targeted markers (`kernel`, `fleet`, `quotagate`) and a `-x -q` "fast gate" subset would make the environment much cheaper to validate; perhaps start with the context and pmk tests (sub-second) and keep full Fleet tests for nightlies.
13. **Make the Console project-state surface honest.** It should show "project not initialized" prominently and avoid auto-reporting dispatch as healthy while `project_state=NEW`.
14. **Record timestamps in verification JSON** (sentinel results, context drift) so reports like this one can distinguish a re-run from a cached file. One prior assessment (`assesment-claude-toy3-v1.md`) notes this specific gap.
15. **Ensure `docs/BRIEF.md` is part of the repository**, not a pointer to another project directory; the same applies to any scratch worktree references.

### Priority 3 (governance)

16. Reconcile the extensive historical pilot record (`pilot/decisions.md`, `pilot/pilot-report.md`, `Assessment-of-UMAWS-completion-report-v1.1.md`) against the current state before the next gate-crossing: some statuses in those documents (e.g. T-0003 "failed", successful OpenCode calls) do not match the bundle/state/Jobs evidence in §5.
17. Treat the sibling `toy1` as what it is (an evaluation copy) and never as part of this repository's source; consider moving it out of `C:\temp\projects` if it is going to keep being referenced.

---

## 7. Suggested stabilization sequence (PowerShell)

```powershell
cd C:\temp\projects\testproject1
py -3.12 -m pip uninstall -y umaws-fleet
py -3.12 -m pip install -e . --no-deps
python -c "import pmk, fleet, quotagate; print(pmk.__file__); print(fleet.__file__); print(quotagate.__file__)"
.\.venv\Scripts\python.exe -m pmk.cli sentinel
.\.venv\Scripts\pmk.exe brief --role overseer
```

Then, only after the report matches expectations:

```powershell
# author docs/PDD.md with G-xxx sections
.\.venv\Scripts\pmk.exe pdd lint docs/PDD.md
# pmk project init --brief docs/BRIEF.md   (arguments per your pmk help)
.\.venv\Scripts\pmk.exe status
```

---

## 8. Verdict

The UMAWS Fleet repository is **functional at the level of tests, sentinel, drift, and static console delivery**, and **dysfunctional at the levels that make it a *project***: environment binding, project state, task closure, and honest acceptance evidence. The central Kernel invariant is not being violated by the code itself in a detectable way; rather, the coordination artifacts it produces (bundles, labels, provenance) contain internal contradictions that a later audit will read as untrustworthy.

Recommendation: **do not run real multi-agent dispatch from this state**. Stabilize the environment (§5.1), audit `T-0003`, close Q-005, and re-create a PDD-backed project before any provider spend. After that, this codebase has a legitimate chance of delivering the pilot it documents.

---

## Appendix A — Selected raw observations

- `pip show umaws-fleet`: `Editable project location: C:\temp\projects\toy1`.
- `python -c "import pmk..." from the live Python`: `pmk ... C:\temp\projects\toy1\src\pmk\__init__.py`.
- `quotagate --help`: `ImportError: cannot import name 'main' from 'quotagate.__main__' (C:\temp\projects\toy1\src\quotagate\__main__.py)`.
- `pmk status`: `project_state=NEW`, `tasks DONE=1/LEASED=1/READY=1`, `active_leases=1`, `open_queue_items=1`, chain length 273.
- `EB-T-0003-3/bundle.json`: `oracle_results[0].ok = false`, `exit=1`, provenance `profile=pi-orca-deepseek`, `model=""`, `family="hermes"`, `context_hash=""`.
- `grep "AGENT_RESUMED mode=new"` equivalent: 4 event entries observed; Q-005 `state=open`.
- `pytest` on testproject1 source via `PYTHONPATH`: `242 passed in 104.95s`; sentinel clean.

## Appendix B — Files referenced

- `README.md`, `CLAUDE.md`, `AGENTS.md` (project rules).
- `pilot/STATE.md`, `pilot/decisions.md`, `pilot/pilot-report.md`, `pilot/report-opencode-2026-10-23.md`.
- `Assessment-of-UMAWS-completion-report-v1.1.md`, `assesment-claude-toy3-v1.md`.
- `docs/BRIEF.md`, `docs/ (no PDD.md present)`, `docs/sources/*`.
- `src/pmk/*`, `src/fleet/*`, `src/console/app.py`, `src/quotagate/*`.
- `tests/*`, `tests/fleet/fakecli.py`.
- `agents.toml`, `pyproject.toml`, `.pm/pins.sha256`, `.pm/views/status.md`, `.pm/evidence/EB-T-0003-3/bundle.json`.
- `work/T-0003-3/...`.

---

*End of report.*
