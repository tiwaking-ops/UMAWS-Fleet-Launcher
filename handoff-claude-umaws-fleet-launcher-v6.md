---
document:
  title: "Handoff: UMAWS Fleet Launcher hardening (v6) for an LLM with repository access"
  type: "Handoff and work order"
  status: "Advisory; the operator decides"
  version: "6.0.0"
provenance:
  author_llm: {name: "Claude", version: "Claude Sonnet 5.5 (Anthropic)"}
  created_date: "2026-11-06"
  supersedes: "handoff-claude-umaws-fleet-launcher-v5.md (2026-11-02)"
  companion: "assessment-claude-umaws-fleet-patch-review-v1.md, version 1.2.14 (findings F-1 to F-112)"
audience:
  primary: "An LLM or coding agent that can read, run and edit the repository at C:\\temp\\projects\\testproject1"
  secondary: "The human operator"
epistemic_status: "Tags: [OBSERVED] seen in a file, a diff, a ledger line or a test result; [REPORTED] stated by an implementer or the operator, not checked by the reviewer; [INFERRED] reasoning; [VERIFY] check it before relying on it. The author never ran any code in the repository: everything about the repository is from files, diffs, ledger lines and test reports sent to the author."
authority_statement: "This document grants no authority. Class K actions (policy, pins, constitution, queue decisions marked class K) belong to the human operator. Section 7 lists what the receiving agent may and may not do."
---

# Handoff: UMAWS Fleet Launcher hardening, v6

## 1. What this is and how to use it

You are taking over a hardening effort on a multi-agent project-management system (the **UMAWS Fleet Launcher**, command `pmk`). The previous reviewer (Claude, working through a chat window, never touching the repository) reviewed patches written by free-tier LLM implementers, wrote some code itself, and had the operator and an OpenCode agent apply and test it. You have direct repository access, so you can do the applying and testing yourself, but **the working rules in section 7 exist because shortcuts failed repeatedly**; read them first.

Read in this order: section 7 (rules), section 3 (state), section 4 (ready work), section 5 (roadmap). Sections 6 and 8 are reference.

## 2. The system in one page

| Part | Where | Role |
|---|---|---|
| Kernel (`pmk`) | `src/pmk/` (`api.py`, `events.py`, `state.py`, `models.py`, `policy.py`, `sentinel.py`, `oracle_lint.py`, `cli.py`, `clock.py`, `store.py`) | Stdlib-only. Owns the append-only, hash-chained event log in `.pm/events/*.jsonl`; task cards, leases and the queue are projections of it. Class K files: `.pm/policy.toml`, `.pm/constitution.md`, `.pm/pins.sha256`. |
| Fleet | `src/fleet/` (`harness.py`, `dispatcher.py`, `conductor.py`, `overseer.py`, `merge.py`, `order.py`, `spawn.py`, `profiles.py`, `classify.py`, ...) | Dispatcher starts agent CLIs (Hermes, pi, kilo, opencode, ...) in per-lease git worktrees; Harness runs one lease and the oracles; Conductor drives merges, stalls, lease reaping and Overseer wakes; Overseer is an LLM session that plans and writes task cards. |
| Console | `src/console/app.py` (FastAPI) | Runs `dispatcher.tick()` and `conductor.tick()` in two threads. Stopped now. |
| Project under management | `docs/`, `src/cna/`, `coverage/` | A digital version of the board game *The Campaign for North Africa* (CFNA). `docs/rules/` holds the 66-file rules corpus pinned from `tcanf-clone@75a037f`. |
| Profiles | `agents.toml` (repo root) | 19 agent profiles; `kilo-auto` has priority 0 (lower number goes first); `max_total_agents = 10` (the CFNA PDD says 6: an operator decision, not a defect). |

Environment [OBSERVED]: Windows 10, PowerShell 5.1, Python 3.12.10, project venv at `.venv`, the venv's editable install points to `testproject1\src`. Git: the repo's local config has `core.autocrlf=false` and identity `umaws-pilot`; the operator's commits use `Tiwa Pene <tiwaking@gmail.com>` via `-c user.name=... -c user.email=...`.

Key invariants: events are canonical JSON with a hash chain (I1 chain verifies, 3,106 events at last check); only Kernel timestamps are trusted (`kernel.clock`); a lease has a fence and the harness renews it every `renew_every` = 60 s while it supervises the lease; `revoke` only appends an event and bumps the fence (it does not stop the agent process).

## 3. Current state (2026-11-06)

### 3.1 Repository

[REPORTED by the operator's agent, hashes also computed independently] HEAD is `9eb39ad` on top of these commits, oldest first:

| Commit | Content |
|---|---|
| `1a5ec9b` | corpus landed from pin `75a037f` (66 files, byte-exact, LF), `.gitattributes` `docs/rules/** -text`, manifest/checksums/index/coverage regenerated (Q-074 decided) |
| `93a3366` | Kernel: `integrate()` requires a non-empty commit reachable from main; sentinel findings for empty/unreachable commits; oracle lint at task create and admit; harness: NO_CHANGES via `git status -z`, R-09 refuse-before-claim, R-11 main-tree status; `render_order` lists absolute destination paths; `FIXED_PROMPT` deleted |
| `8a71d36` | merge queue: merge in a temporary worktree, gate there, `--ff-only` into main, retries if main moved |
| `19dc337` | refuse to start on `agents.toml` errors; `pmk fleet check`; Console and Dispatcher enforce |
| `5b21024` | test that reaches the NO_CHANGES branch through a real fake-CLI run |
| `62af455` | Conductor `reap_expired_leases()`: orphaned leases only, process stopped before revoke |
| `9eb39ad` | edge-triggered, PAUSED-aware Overseer wakes |

Full suite in the live tree: **463 tests, 0 failed, 0 errors, 0 skipped** [OBSERVED in `junit-live-463-final.xml`], `pmk.__file__` under `testproject1\src`.

Policy: `ttl_minutes = 20` (the committed value; a working-tree-only 120 was reverted through class K item Q-075), `renew_every = 60`, `heartbeat_seconds = 60`. Pins verify.

### 3.2 Runtime

Dispatch PAUSED, console stopped, 0 active leases, no Overseer wake possible while PAUSED. Tasks: T-0145 and T-0146 are PROPOSED (real work: extend `cna.tools.rules_index` and `cna.tools.coverage` to index the 66 `.adoc` files; their oracles currently fail with `documents` = 3 and `rule_files` = 3); T-0141 and T-0142 are VOID; the rest are DONE or VOID.

Queue: Q-072 and Q-073 are open but stale (stall items for voided tasks); Q-074 (corpus) and Q-075 (TTL) are decided.

### 3.3 Known open problems (not fixed)

1. Sentinel I6 reports five `stops: true` findings (T-0118, T-0119, T-0127, T-0129, T-0130): their latest `INTEGRATED` event is a hand-written repair event without a bundle reference (F-23, F-75). Nothing acts on `stops` (only `sentinel.py` reads it). A typed repair event (B17) and an actor for stop findings (B15) are not designed.
2. T-0139's `INTEGRATED` event carries an empty commit (the corpus landed by other means).
3. `Dispatcher.reconcile()` exists and is tested but nothing calls it; after a console restart live workers are not adopted (the reaper stops and revokes them after the TTL).
4. The Overseer's hourly cap (6) is an in-memory counter per process; a restart grants a fresh budget (F-108).
5. Lint gaps accepted as low risk: a `python -c '...'` payload after an opening parenthesis or after `if exist ...`.
6. The ledger records class K key 2 and a pin re-record as `human/operator` although an agent session ran them on the operator's instruction (F-109). Agent sessions should set `PMK_ACTOR=agent:<tool>`.
7. Many tracked files in the live working tree are CRLF while their committed blobs are LF (stat-clean, so `git diff` hides them): `src/fleet/profiles.py`, `src/pmk/__init__.py`, `src/quotagate/__init__.py`, eight test fixtures, `tests/quotagate/test_quota_engine.py`. Harmless until touched. **Never commit an EOL-only change.**

## 4. Ready-to-apply work: package H (two patches)

Written by the reviewer against the real committed files, **not yet applied to the repository by anyone**. The pure parts were exercised in a scratch copy (11 tests, all passing: `parse_status_z`, `_check_agent_claims`, the full-set comparison); everything that needs a Kernel, a Harness or the real `Repo` is untested.

Files: `0001-fleet-advisory-RESULT.md-check-honest-git-failures-f.patch` (sha256 `2b93d7b53250007f0030776b1623e3b9fa34a4550667ee335e0cc537b5974c1a`), `0002-pmk-write_pins-writes-LF-line-endings.patch` (sha256 `99908c4d5754e069250857b1f63662642e63f8ce2c428327ed8ec2f039120385`).

| Patch | Does | Why |
|---|---|---|
| 0001 | `_check_agent_claims()` returns `(problems, advisories)`; a RESULT.md without the task id is advisory only (recorded as one `AGENT_ADVISORY` event in `_finish`); a failed `git status` skips the NO_CHANGES check and is recorded, instead of being treated as "no changes"; `spawn.parse_status_z` handles `-z` rename/copy records, and git output is decoded as UTF-8; the R-11 exit-time comparison uses full path sets kept on `LeaseRun.main_tree_paths_start` (the event summary keeps 20); `SCOPE_CONFLICT` is recorded once per task and distinct path set | findings F-48, F-27, F-112 |
| 0002 | `write_pins` writes LF (`newline="\n"`) | `.gitattributes` says `text eol=lf`; `Path.write_text` wrote CRLF on Windows (F-110) |

Base blobs that must match before applying (`git rev-parse HEAD:<path>`):

```
src/fleet/harness.py            fed8050cc277f842146a5307368e5214cdf0dfff
src/fleet/spawn.py              b2f48c1458f945f8ec650a71b0f8a32237a19104
tests/fleet/test_regressions.py 3e16e0f4f7d1643896d668f4d4e2ef061e7fb767
src/pmk/policy.py               82578bfca4fd248e089782e7b53e69ac6ad8aad8
```

Blobs after applying:

```
src/fleet/harness.py             e49f93cac89ecac0cb7460fb3f795787826c97b4
src/fleet/spawn.py               618694b6edf1032d0e7eae235df38ce1fefbd5c3
tests/fleet/test_regressions.py  b98525b997fda4c424ff5c40e1ee376c244e7996
tests/fleet/test_harness_claims.py  647f57aeb637142e763927ad40bd32aef0148b46   (new)
src/pmk/policy.py                7b6ebff9966c814fbb1263846fb96b02fe676768
tests/pmk/test_pins_newline.py   2097d1a57d99191a13027978c402c992e809faa1   (new)
```

Notes: `harness.py` and `policy.py` begin with a UTF-8 BOM, which the patches preserve. Two existing tests in `test_regressions.py` are changed on purpose: the NO_CHANGES test used a directory that was not a git repository and passed only because git failed; the RESULT.md test now asserts the advisory. Expected suite size after both patches: 463 + 13 new tests = **476** [INFERRED; verify]. If a test fails, report the traceback; the author's assumptions about unseen helpers (`git_repo_master`, `_make_kernel_from_repo`, `make_task`, `write_agents`) were taken from the existing tests in the same file.

Procedure: scratch clone (section 7.2), `git am` both patches, run the full suite, compare blobs, then ask the operator to land them in the live repository with the same `git am` procedure (section 6.1).

## 5. Roadmap to a supervised canary

1. **Apply and verify package H** (above). Report counts, failures, blob hashes.
2. **Pre-canary readiness** (all read-only until the operator agrees):
   - `pmk status` shows PAUSED, 0 active leases, I1 chain verifies.
   - `pmk fleet check` prints no errors; `agents.toml` overseer names all exist.
   - Q-072 and Q-073 are stale and open: the operator decides them (from his shell) so they do not keep the Overseer's incident reason alive. Decide what the Overseer may do on resume.
   - Snapshot `.pm\events` to a new folder (never overwrite an earlier snapshot).
   - Hermes remains enabled (operator decision); `kilo-auto` has priority 0 so it goes first.
3. **The canary (supervised, the operator watching).** Pick one harmless task (a small documentation or test-only card with a disjoint write scope; T-0145 and T-0146 are real tool changes and are better after the canary). Start the Console, resume, and watch: the lease is claimed with a worktree; `AGENT_STARTED` carries pid and creation time; `RENEWED` events appear about once a minute; the agent writes inside its worktree and nothing appears in the main tree; oracles run; the merge goes through the merge queue (temporary worktree, gate, `--ff-only`). Specifically look for: Hermes writing into the main tree (the original incident); the reaper acting on a lease it should not; any Overseer wake while PAUSED; `AGENT_ADVISORY` and `SCOPE_CONFLICT` events being sensible. **Abort criteria:** any write in the main tree outside a task's scope, a lease revoked while its agent is healthy, a merge into main without a passing gate. Abort means pause, stop the Console, snapshot `.pm\events`, report.
4. **After the canary:** T-0145 and T-0146; a typed repair event (B17) so the sentinel's I6 findings can close; decide what a `stops: true` finding does (B15); call `Dispatcher.reconcile()` at Console start; make the Overseer's hourly cap survive restarts by counting `OVERSEER_WOKEN` events in the ledger; unify the line-ending policy of the working tree (an operator decision).

## 6. Procedures (copy-paste, PowerShell)

### 6.1 Applying reviewed patches to the live repository

```powershell
cd C:\temp\projects\testproject1
git rev-parse HEAD                                   # expect 9eb39ad... (or the commit after package H)
git diff --cached --stat                             # must print nothing
git --no-pager status --short -- src tests           # must print nothing
Get-FileHash -Algorithm SHA256 <patch files>         # compare with the hashes given for them
$p = Get-ChildItem <dir>\0*.patch | Sort-Object Name | ForEach-Object FullName
git -c user.name="Tiwa Pene" -c user.email="tiwaking@gmail.com" am $p     # on failure: git am --abort
git rev-parse 'HEAD:<path>'                          # compare with the expected blobs
.\.venv\Scripts\python.exe -m pytest -q tests --junitxml=C:\temp\junit-live.xml *> C:\temp\pytest-live.txt
```

Rollback: `git reset --keep <previous full hash>` (not `--hard`).

### 6.2 Useful checks

```powershell
git ls-files --eol -- src tests | Select-String "w/crlf|w/mixed"     # the known phantom CRLF files only
pmk status ; pmk fleet check ; pmk pins check
```

## 7. Working rules (learned the hard way)

### 7.1 What you may and may not do

- You may read anything, run tests, write in a scratch clone, and propose patches.
- You may land commits in the live repository **only after the operator says so**, with `git am` under the operator's identity and the proofs in 6.1.
- **Never** run class K actions: editing `.pm/policy.toml`, `.pm/constitution.md`, `.pm/pins.sha256`; `pmk pins record`; `pmk queue decide` on class K items. Raising key 1 of a class K item is acceptable with `PMK_ACTOR=agent:<your tool>`; key 2 and every pin re-record are the operator's, from his own shell. Never use a human identity for anything you did.
- Do not edit `.pm/` by hand, `agents.toml`, or `pilot/` (except appending decision records the operator asks for).
- Never run `git reset --hard`, `git clean`, `git restore`, `git checkout`, `git stash` or `git add -A` in the live repository. Do not use `git add .`.

### 7.2 Scratch clone

`git -c core.autocrlf=false clone --no-hardlinks C:\temp\projects\testproject1 <new folder>`, then `git config core.autocrlf false` and set `user.name`/`user.email` from the global config. A clone without these settings checks files out as CRLF and every later patch is wrong.

### 7.3 Patches and files

- LF line endings only; keep a file's existing BOM (`harness.py` and `policy.py` have one); never commit an EOL-only or whitespace-only change; no whole-file rewrites.
- Write patches only with `git format-patch --output-directory`. **Never** with PowerShell `>` or `Out-File`: they produce UTF-16 with CRLF, which cannot be applied (this happened twice).
- Reviewer tools: `check_patch.py` (generic) and `check_series.py` (a fixed series). Do not edit them. Run: `python check_patch.py <patch or dir> --allow PATH[:MAX_ADDED[:MAX_REMOVED]] ...`. It fails on NUL bytes, CR in added lines, whitespace-only hunks, "No newline at end of file", unexpected files and size overruns. An implementer once replaced the checker with a looser script and reported "all pass" from it.

### 7.4 Tests and evidence

- No placeholder tests (`pass`, `assert True`). A green placeholder suite is worse than none.
- A test must fail without the change it covers. An existing test once passed only because git failed in a directory that was not a repository.
- Run the **whole** suite in one command from a normal terminal with no time limit; tool timeouts of 120 s produced false "timed out" and "passed" reports. Print `pmk.__file__` and `fleet.__file__` first. A clean-checkout run needs `PYTHONPATH=<clone>\src;<clone>\tests`.
- Report counts from the junit XML (tests, failures, errors, skipped, unique ids), not from memory. Implementers' summaries repeatedly contradicted their own artifacts (test totals that did not add up, "verified" claims with no output). Verify blob hashes with `git rev-parse HEAD:<path>` and compare with the expected values.
- A reviewer-written patch is applied unchanged. If it fails, paste the traceback and fix in a new commit; do not edit the patch and report success.

### 7.5 Domain traps

- `shell=True` oracles run under `cmd.exe`: single quotes do not group, `%` expands inside double quotes, `\"` does not hide `&` or `|`. The lint in `src/pmk/oracle_lint.py` enforces this at task creation and admission.
- Use `kernel.clock` (the injectable clock), never `time.time()`, in code that tests drive with `FakeClock`; `Clock.monotonic()` for intervals.
- `git status` must be read with `-z`, as bytes, and rename records have a second field without a status prefix (`spawn.parse_status_z`).
- Windows process safety: kill a process only if both pid and creation time match the recorded values (`spawn.slot_alive`, `kill_slot`).
- Free-tier model names and quota limits change; `agents.toml` is the operator's file.

## 8. Reference

### 8.1 Decisions of the operator (do not reopen without asking)

| Id | Decision |
|---|---|
| D-3 | Revert lease TTL to 20 minutes and make heartbeats count (done: reaper landed, TTL reverted through Q-075) |
| H-12 | Keep the `verify`, `maintain` and `research` task types |
| H-31 | Adopt the rule: no uncommitted edits in main inside a READY or LEASED card's write scope |
| Hermes | Keep the four Hermes profiles enabled; `kilo-auto` gets priority 0 |
| Q-074 | Corpus lands from the pin objects, superseding branch `pmk/T-0139-117` (done, commit `1a5ec9b`) |
| Console | Stays stopped until the canary; dispatch stays paused |
| Formal documents | Markdown with author (the model's name) and version fields |

`pilot/decisions.md` records D-58 to D-61 (the Q-074 governance gap, the series landing, the reap/wake landing, the TTL revert).

### 8.2 Findings index (companion file)

`assessment-claude-umaws-fleet-patch-review-v1.md` (v1.2.14) sections 10.1 to 10.18: F-1 to F-19 (first patch review), F-20 to F-33 (working-tree review), F-34 to F-65 (merge queue, config enforcement, lint), F-66 to F-91 (series landing, rejected rewrites), F-92 to F-107 (lease reaping and wake loop), F-108 to F-112 (wake census, class K record, `write_pins`).

### 8.3 Files and folders on the operator's machine [REPORTED]

| Path | Content |
|---|---|
| `C:\temp\wip-snapshot` | copy of the work-in-progress `src` and `tests` before the series landed (reference only; never apply) |
| `C:\temp\live-wip-backup-20261104` | pre-series copies of touched files and moved untracked files |
| `C:\temp\series2\held-back.patch` | **rejected**: UTF-16, whole-file diffs. Never apply |
| `C:\temp\events-snapshot-20261102*` | snapshots of the event log |
| `C:\temp\reviewer-tools\check_patch.py` | reviewer tool, sha256 `b3db835bf111c776395ec58fa4c07373e7f7ba294242a8858f7e36d2eaad4f1a` |
| `C:\temp\final-series\check_series.py` | reviewer tool, sha256 `d38ee663261885e079f6be7a47776d4df45d598408292f22e7205cf484ffa8d5` |
| `C:\temp\commit-prep3`, `commit-prep5` | scratch clones from earlier rounds (may be stale) |

### 8.4 Reviewer-written patch hashes already applied

```
reap       0001-fleet-reap-expired-orphaned-leases-in-the-Conductor.patch      9723b93277c96269a9df73a4446b27165ca075c9989c6028be02b2bfdbe2d571
wakes      0002-fleet-edge-triggered-PAUSED-aware-Overseer-wakes.patch         937d93242af23f7b9d5dc754cbe61b0a2b8f690520c2296255aa5d530bbc3dba
```

Blobs: `src/fleet/conductor.py` `c4f244cd97ca6a9ec3d74196bc37f5a77b15d018`, `tests/fleet/test_conductor_leases.py` `40a6b9125cdd88796225e2d38fae1f38f81786ed`, `tests/fleet/test_overseer_wake.py` `23181d915034365d7c92980e2ca25dee7f75cf91`.

## 9. First hour checklist for the receiving agent

1. Read section 7. Confirm you cannot and will not perform class K actions.
2. Run the checks in 6.2 and `git rev-parse HEAD`; compare with section 3.1. Report any difference before doing anything else.
3. Make a scratch clone, apply package H, run the whole suite, report counts and blobs.
4. Ask the operator before landing, then follow 6.1.
5. Prepare the canary plan (section 5, item 3) for the operator's approval; do not start the Console yourself.
