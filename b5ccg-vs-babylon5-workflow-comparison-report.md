---
document:
  title: "Comparative Analysis — Project Management Workflow Systems: b5ccg vs Babylon5CCGGameDesign"
  status: "Report"
provenance:
  author_llm: {name: "Nemotron 3.5 Super VL", version: "nvidia/nemotron-3.5-super-vl:free"}
  created_date: "2026-11-14"
  last_modified_date: "2026-11-14"
  last_modified_by_llm: {name: "Nemotron 3.5 Super VL", version: "nvidia/nemotron-3.5-super-vl:free"}
Author: Nemotron 3.5 Super VL (nvidia/nemotron-3.5-super-vl:free)
---

# Comparative Analysis — Project Management Workflow Systems: b5ccg vs Babylon5CCGGameDesign

## 1. Executive Summary / Conclusion

**No — they are not identical, but they are the same workflow system in origin and core protocol.**

`b5ccg` (`C:\temp\projects\b5ccg`) is an explicit fork of `Babylon5CCGGameDesign` (`C:\temp\projects\Babylon5CCGGameDesign`), forked on 2026-10-16, with the parent repository now in hiatus and left untouched. Both repositories run the same `.agent/`-based autonomous project management workflow, sharing the same claim/heartbeat/ledger/report coordination protocol, the same `B5-NNNN` task ID scheme, the same 30-minute claim TTL, and the same defect history (B5-2400 read-modify-write clobber, hand-stamped clock issues, duplicate-ID races, etc.).

`b5ccg` is described in its own `AGENTS.md` as a "lean reset" fork. It kept the core `.agent/` protocol intact and added several governance layers on top, while changing the build toolchain policy. The differences are therefore **additive governance** (authority designation, proposal markers, data-authority gate, reviewer-family independence, rule-ID citations) plus a **different build gate** (JDK 25 `--release 8` staged move vs. a hard Java 6 rule).

Neither repository uses Kernel-lite / `pmk` (no `.pm/` directory exists in either). The only `.pm/` references anywhere appear inside `Babylon5CCGGameDesign/docs/reports/tiwas-system-comparison-2026-10-06.md`, where the **Tiwas** TTRPG project documentation system is discussed as a separate model from which ideas were considered for borrowing — not as the workflow either repo actually runs.

---

## 2. Scope and Methodology

### 2.1 Repositories compared

| Repository | Path | Relationship |
|---|---|---|
| `b5ccg` | `C:\temp\projects\b5ccg` | Fork of Babylon5CCGGameDesign (2026-10-16, parent in hiatus) |
| `Babylon5CCGGameDesign` | `C:\temp\projects\Babylon5CCGGameDesign` | Parent/origin repository |

### 2.2 Artifacts examined

From `b5ccg`:
- `AGENTS.md` (governance, provenance, build rules, statuses, promotion, shared-files protocol)
- `.agent/00_BOOT.md` (cold-boot sequence)
- `.agent/TASK_LEDGER.md` (live ledger with B5-NNNN rows)
- `.agent/tools/` (72 tools including `new-claim.ps1`, `new-heartbeat.ps1`, `append-ledger.ps1`, `run-dup-census.ps1`, `check-citations.ps1`, `check-data-authority.py`, `check-proposal-markers.ps1`, `build-rule-index.ps1`, `rule-coverage.ps1`, `validate-heartbeats.ps1`, `ledger-query.ps1`, `run-queue.ps1`)
- `.agent/REPORTS/`, `.agent/CLAIMS/`, `.agent/HEARTBEATS/`, `.agent/PATTERNS/`
- `README.md` (fork notice, build quick start, milestone)

From `Babylon5CCGGameDesign`:
- `AGENTS.md` (governance, provenance with compaction convention §1a, hard build rules §2, statuses §3, autonomous promotion §4, shared-files protocol §5, self-seeding §6)
- `AGENTSv2.md` (condensed restatement of the same workflow)
- `.agent/00_BOOT.md` and `.agent/00_BOOTv2.md` (cold-boot sequences, extensively annotated with B5-rules and assessor history)
- `.agent/TASK_LEDGER.md` (large live ledger, hundreds of rows, extensive assessor_llm compaction history)
- `.agent/tools/` (58 tools plus `_retired/` including `new-claim.ps1`, `new-heartbeat.ps1`, `append-ledger.ps1`, `run-dup-census.ps1`, `check-citations.ps1`, `census-b50960.py`, `census-denominator-guard.ps1`, `measure-task-cells.ps1`, `run-verification-battery.ps1`, `scope-collision-census.ps1`, `validate-heartbeats.ps1`, `verify_task.py`, `detect-bare-powershell-cmdlet.ps1`)
- `AGENTSv2.md`, `README.md`, `docs/reports/tiwas-system-comparison-2026-10-06.md`

---

## 3. What Is the Same (Shared Workflow System)

Both repositories implement the identical `.agent/` coordination protocol:

| Element | b5ccg | Babylon5CCGGameDesign |
|---|---|---|
| Task ledger | `.agent/TASK_LEDGER.md` | `.agent/TASK_LEDGER.md` |
| Claims store | `.agent/CLAIMS/*.json` | `.agent/CLAIMS/*.json` |
| Heartbeats | `.agent/HEARTBEATS/*.json` | `.agent/HEARTBEATS/*.json` |
| Reports | `.agent/REPORTS/<date>-<agent-id>-<task>.md` | `.agent/REPORTS/*.md` (also `docs/reports/`) |
| Pattern store | `.agent/PATTERNS/<agent-id>/` | `.agent/PATTERNS/<agent-id>/` |
| Boot sequence | `.agent/00_BOOT.md` | `.agent/00_BOOT.md` / `00_BOOTv2.md` |
| Task ID scheme | `B5-NNNN` | `B5-NNNN` |
| Claim TTL | 30 minutes | 30 minutes |
| Writer scopes | `engine/`, `model/`, `ai/`, `ui/`, `resources/`, `tooling/`, `docs/` | `engine/`, `model/`, `ai/`, `ui/` |
| One writer per scope | Yes | Yes |
| Git role | Change-tracking only, not authority | Change-tracking only, not authority |
| Tooling core | `new-claim.ps1`, `new-heartbeat.ps1`, `append-ledger.ps1`, `run-dup-census.ps1`, `check-citations.ps1`, `ledger-query.ps1`, `run-queue.ps1`, `validate-heartbeats.ps1` | Same core set |
| Claims-first census | `run-queue.ps1 -DryRun` (never hand-grep the ledger) | Same |
| Ledger append rule | `append-ledger.ps1` only, never `Add-Content` (B5-2400) | Same |
| Provenance | `author_llm` / `assessor_llm` front matter on governance docs | Same (with compaction convention) |
| Lifecycle | OPEN → atomic claim → work in scope → verify gate → DONE + report → release claim → refresh heartbeat | Same |

### 3.1 Inherited defect history

`b5ccg` inherited the same documented defect classes from the fork:
- **B5-2400**: `Add-Content` read-modify-write clobber destroys concurrent ledger appends; `append-ledger.ps1` is the sanctioned verified-append path.
- **Hand-stamped `utc` clock issues**: claims stamped ~13 h ahead (UTC+13 host) read as LIVE forever; tool-stamped writers required (B5-1915).
- **Duplicate-ID races**: two agents can both measure an ID free inside the same window; post-write `run-dup-census.ps1` is required; diverge to non-adjacent IDs, never renumber into a vacated slot (B5-0622, B5-0618).
- **B5-1541 / B5-1733**: bare PowerShell cmdlets in instruction position are a finding; `detect-bare-powershell-cmdlet.ps1` enforces this.
- **B5-0657 / B5-0660**: claims-first census; staleness judged on the three-signal rule (claim age, owner heartbeat, report mtime), never timestamp alone.

---

## 4. How They Differ

### 4.1 Build policy (substantive difference)

| Aspect | b5ccg | Babylon5CCGGameDesign |
|---|---|---|
| Java level | stdlib-only Java; staged move to **JDK 25** with `--release 8` (Hop 1), Hop 2 `--release 25` | **Java 6 hard rule**: `javac -source 6 -target 6`, stdlib only |
| `src-java8-archive/` | Not present | Frozen — never edit |
| JDK 8 | Retained as reference only; cannot drive the build (rejects `--release`) | The only toolchain (`1.8.0_292` on this machine) |
| Standing construct census | `.agent/tools/census-b50960.py` (Java 6 census, one sentinel cycle after Hop 1, then retires) | `.agent/tools/census-b50960.py` (standing, on demand, not wired into build) |
| Denominator guard | Not present | `census-denominator-guard.ps1` (four independent counts must agree) |

### 4.2 Governance layers unique to `b5ccg` ("lean reset" additions)

**Authority Designation Rule (AGENTS.md §3):**
- Exactly one authoritative file per data domain.
- Must live at repo root or `docs/` (never `.agent/`, never `docs/proposals/`).
- Must carry `status: "Authoritative"` + provenance `source` (e.g. `HUMAN-SCANNED`).
- Must be referenced by name in `docs/DECISIONS.md` with a rule-ID.
- All other files in the domain must include a `source_of_truth` field pointing to it.
- Enforced, not asserted: `.agent/tools/check-data-authority.py` fails on non-compliant designated files; has a proven red `--self-test` state; runs in the gate every time.

**Proposal Self-Identification (AGENTS.md §3):**
- Every file in `docs/proposals/` (JSON or Markdown) must carry a machine-readable marker:
  ```json
  { "_proposal": true, "_status": "candidate", "_authority": "<path-to-authoritative-file>" }
  ```
- Enforced by `check-proposal-markers.ps1` (fails when marker missing or `_authority` does not name a registered Source of Truth in `docs/AUTHORITY_INDEX.md`) and gate probe `test-proposal-markers.ps1`.

**Data-Authority Gate (AGENTS.md §4):**
- The verification gate additionally checks that, for each data domain with an authoritative source, the deployed file matches the authoritative source on all canonical fields.
- Failure = gate fails with a diff report; runs before promotion.

**Reviewer independence by model family (AGENTS.md §1):**
- The assessing agent must run a *different model family* from the authoring agent (family = model lineage, not provider/vendor/agent id).
- A different agent id is not independence; same family reviewing its own work reproduces blind spots.
- If no different-family agent is available, work is recorded as `unassessed_revision` (author-written, not independently assessed) rather than given a nominal assessor.
- Self-assessment is prohibited; an editorial pass is not an assessment (recorded in `last_modified_by_llm` / `unassessed_revision`, never `assessor_llm`).

**Rule-ID citations (AGENTS.md §5):**
- Rulebook sections cited as `RB:<chapter>/<slug>` with optional paragraph ordinal (`RB:V#7`).
- `docs/RULE_INDEX.md` regenerated from the pinned rulebook by `.agent/tools/build-rule-index.ps1` (refuses to run unless rulebook SHA-256 equals the pin).
- `check-citations.ps1` fails on any cited ID not in the index; legacy `RB:<line>` citations resolve by line range.
- `rule-coverage.ps1` measures coverage against the hand-kept sidecar `docs/RULE_COVERAGE_MAP.md`; `check-citations.ps1` fails on uncited IDs.

**Extra tooling unique to `b5ccg`:** `check-data-authority.py`, `check-proposal-partition.ps1`, `build-rule-index.ps1`, `rule-coverage*.ps1` (debug/fixed variants), `test-citation-ratchet.ps1`, `test-data-alignment.ps1`, `test-proposal-markers.ps1`, `test-proposal-partition.ps1`.

### 4.3 Governance elements more developed in `Babylon5CCGGameDesign`

**`assessor_llm` compaction convention (AGENTS.md §1a, adopted 2026-09-27, B5-0655):**
- One entry per agent per file, carrying a pass count — not one appended line per edit pass.
- Repeat pass: increment `passes`, set `last_pass`; do not append.
- First pass or different version: append new entry with `passes: 1`.
- `note` optional, substantive passes only; entries never deleted/renamed/rewritten beyond `passes`/`last_pass`/`note`; no retro-compaction.

**Standing Java 6 construct census + denominator guard:**
- `census-b50960.py` masks comments and string literals; a hit is code only if it survives the mask.
- Pass condition: `code-lines 0` for every construct family.
- `census-denominator-guard.ps1` requires four independent counts of the Java file set to agree (PowerShell tree walk, `find src -name "*.java"` from `compile.sh` invoked inside bash, census `DENOMINATOR` line from a fresh run, `git ls-files` as tracking signal); asserts `tracked + untracked == on disk`; exit 0 agree / 1 disagreement / 2 unreadable.

**Task-cell budget (00_BOOT.md step 3a, B5-1471/B5-1730):**
- `measure-task-cells.ps1` measures mean <= 764, median <= 479, p90 <= 1879, max <= 4397 characters in the Task cell for rows with id above 1471.

**Verification battery (`.agent/tools/run-verification-battery.ps1`):**
- Chains 7 instruments (including `check-citations.ps1` as instrument 7) into one command.

**Additional tooling:** `census-crosscheck.ps1`, `claim-liveness-report.ps1`, `scope-availability-reporter.ps1`, `scope-collision-census.ps1`, `playable-release-check.ps1`, `promotion-gate.ps1`, `suite-coverage.ps1`, `migrate-heartbeats.ps1`, `repair-heartbeat.ps1`, `audit-heartbeats.ps1`, `heartbeat_files.csv` / `heartbeat_quarantine.csv` / `heartbeat_retired.csv`.

### 4.4 Promotion criteria (substantively the same, different gate)

**`b5ccg` (AGENTS.md §4):**
1. Claimed scope only.
2. Verification gate passes: `RUN_TESTS=1 sh compile.sh` exits 0 (compile + conformance suite + gate probes; needs JDK 9+ `javac` on `PATH`).
3. Change logged in `docs/DECISIONS.md`.
4. Claim released.
- Baseline rule: the gate carries failures that predate the fork and are recorded in `docs/DECISIONS.md` (four named baseline checks: AES losing matchup, AIJ weak target, MINES fleet reactive return damage, MINES round-trip). A plain `compile.bat` is fast compile-only and never sufficient for promotion.
- A task that adds behaviour must also add or extend a probe that fails without the change.
- External libraries and toolchain hops need a DECISIONS entry.
- Data-Authority Gate runs as part of the gate (see §4.2).

**`Babylon5CCGGameDesign` (AGENTS.md §4 / AGENTSv2.md §4):**
1. Claimed scope only.
2. `compile.bat/sh` green on JDK 8 with `-source 6`.
3. Change logged in `docs/DECISIONS.md`.
4. Claim released.
- No human ruling needed except the external-library gate.
- If in doubt, log the ambiguity in the report and STOP that item only — do not block unrelated work.

---

## 5. Neither Project Uses Kernel-lite / pmk

A search of both repositories for `pmk`, `kernel-lite`, and `.pm/` found **no matches** in either repository's governance or tooling. The only `.pm/` references in the entire compared surface are inside `Babylon5CCGGameDesign/docs/reports/tiwas-system-comparison-2026-10-06.md`, which describes the **Tiwas** TTRPG project documentation system as a separate model (single stdlib Python kernel `.pm/kernel/pmk.py`, hash-pinned `.pm/policy.yaml`, `.pm/quarantine/`, `.pm/registry/scopes.yaml`, `pmk sentinel`, `pmk` CLI) and lists it as a source of candidate improvements (B-scored suggestions) for Babylon5CCGGameDesign — not as the workflow either repo runs.

---

## 6. Findings

1. **Common ancestor confirmed.** `b5ccg` README states: "Forked 2026-10-16 from `Babylon5CCGGameDesign` (now in hiatus)." `b5ccg` AGENTS.md states: "Fork of `Babylon5CCGGameDesign` (now in hiatus, left untouched)."
2. **Same daily coordination loop.** Boot → census → claim → work in scope → verify gate → DONE + report → release claim → refresh heartbeat is identical in both.
3. **Same ledger/tool contract.** `append-ledger.ps1` verified-append, `run-dup-census.ps1` post-write duplicate check, `new-claim.ps1` atomic claim, `new-heartbeat.ps1` tool-stamped heartbeat, `check-citations.ps1` citation presence, `validate-heartbeats.ps1` heartbeat store validation — all present in both.
4. **`b5ccg` added governance, not replaced workflow.** The fork kept the `.agent/` protocol and layered on Authority Designation, Proposal Self-Identification, Data-Authority Gate, reviewer-family independence, and Rule-ID citation coverage.
5. **Build policy diverged.** `b5ccg` is moving to JDK 25 `--release 8`; `Babylon5CCGGameDesign` holds a hard Java 6 rule with a frozen Java 8 archive and a standing construct census.
6. **No Kernel-lite/pmk in either repo.** Tiwas is discussed only as an external comparison model.

---

## 7. Decisions / Conclusions

- The two projects share one workflow system family; operational knowledge transfers directly between them (same claim/heartbeat/ledger/report mechanics, same B5-NNNN IDs, same 30-minute TTL, same sanctioned tools).
- The only substantive operational difference a practitioner will encounter daily is the **build gate**: JDK 25 `--release 8` (`RUN_TESTS=1 sh compile.sh`) in `b5ccg` vs. JDK 8 `-source 6 -target 6` (`compile.bat/sh`) in `Babylon5CCGGameDesign`.
- `b5ccg` practitioners must additionally satisfy the Data-Authority Gate and Proposal Self-Identification checks before promotion; `Babylon5CCGGameDesign` practitioners must additionally satisfy the standing Java 6 construct census (on demand) and the assessor_llm compaction convention.
- Neither project should be described as using Kernel-lite or `pmk`; any reference to `.pm/`, `pmk`, or `sentinel` in relation to these repos is incorrect outside the Tiwas comparison report.

---

## 8. Unresolved Issues / Open Questions

The following items were observed in the source material but remain unresolved or are flagged in the projects' own documentation:

- **`b5ccg` snapshot job (B5-0009):** built 2026-10-16 but **not enabled** pending owner review; no snapshot branch exists yet. The planner checks at the start of each session that the newest snapshot is under 24 hours old and records `none found` when there is none.
- **`b5ccg` baseline conformance exceptions:** four named pre-existing failures (AES, AIJ, MINES-fleet, MINES-roundtrip) are carried in `docs/DECISIONS.md`; the repair row B5-0017 is DONE but the baseline exception wording in AGENTS.md §4 and `00_BOOT.md` step 7 was to be replaced with the four exact check names (status per B5-0019 acceptance).
- **`b5ccg` assessor independence:** several `unassessed_revision` entries exist in AGENTS.md provenance (authored but not independently assessed); a different-family assessment is outstanding for some revisions.
- **`Babylon5CCGGameDesign` heartbeat store:** `validate-heartbeats.ps1` is **known-red** (19 non-conforming files as of 2026-10-01); three hand-authored heartbeats carried `utc` values 186–852 min ahead of real UTC.
- **`Babylon5CCGGameDesign` ledger integrity:** the ledger was truncated from 380 rows to 1 at one point (rebuilt from `.agent/TASK_LEDGER.md.bak`); multiple `.bak`, `.tmp`, `.report-temp`, and pre-repair copies of the ledger exist on disk.
- **Stale claims:** `b5ccg` ledger documents reaping of stale claim files (e.g. B5-0007 reaped after 77+ minutes; seven claims held by `claude-code-b5ccg-02` ~31.5 h stale).
- **Tiwas adoption decisions:** The Tiwas comparison report lists candidate improvements (hash-chained append-only stores, scopes as data, human status page, single sanctioned entry point) marked M/S priority; none appear to have been adopted into either repo's workflow as of the examined state.

---

## 9. Recommendations

- Treat `b5ccg` and `Babylon5CCGGameDesign` as interoperable for agent coordination purposes: the same boot/claim/heartbeat/report cycle applies in both.
- When working in `b5ccg`, always run the Data-Authority Gate and verify proposal markers before promotion; when working in `Babylon5CCGGameDesign`, always run the Java 6 construct census and respect `assessor_llm` compaction.
- Do not cite Kernel-lite/pmk as the workflow system for either repository; reference the `.agent/` protocol instead.
- Resolve the open items in Section 8 (snapshot enablement, baseline wording, unassessed revisions, heartbeat store conformity) before treating either repository's governance as fully stable.

---
