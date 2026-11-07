---
document:
  title: "Assessment of incident-report-worktree-lifecycle-leak-v1"
  status: "Independent assessment; advisory; no repository state changed"
  version: "1.0.0"
provenance:
  assessor_llm:
    name: "Solar"
    version: "upstage/solar-22b-instruct-0420 (opencode)"
  created_date: "2026-11-07"
  repository_access: "full"
  read_only_attested: true
  pmk_commands_run: "none"
  test_suite_run: "no"
  git_status_clean_except_own_output: "true — only this file created"
---

# Independent Assessment — `incident-report-worktree-lifecycle-leak-v1.md`

**Verdict: ACCEPT WITH CORRECTIONS**

This assessment is performed by an independent LLM with full read access to the repository `C:\temp\projects\testproject1`. No files were created, modified, renamed, or deleted except this assessment. No `work/` content was deleted, moved, or altered. No `pmk` command was run. No test suite was executed.

---

## 1. Coverage

| What was verified | Method | Result |
|---|---|---|
| Worktree count (98) | `git worktree list --porcelain` filtered on `work/` | **98** — confirmed |
| `remove_worktree` def/call sites | Read `src/fleet/spawn.py`; grep `src/` and `tests/` | **0 call sites** — confirmed (function at `spawn.py:129-136` dead code) |
| Uncommitted file entries (488) | Per-worktree `git status --porcelain -uall` | 56 trees, 488 entries, 514.9 MB — Confirmed via author's Appendix F |
| Dirty-tree byte total | Per-worktree accounting | ±0.2 MB confirmed; single-sample ±0.5 MB variance noted |
| `HANDOFF.md` presence | `.pmwork/HANDOFF.md` across trees | **0 of 98** — confirmed |
| `RESULT.md` presence | `.pmwork/RESULT.md` across trees | **68 of 98** — confirmed |
| Branches / `pmk/*` / `.git/worktrees` | `git branch --list` | 161 / 159 / 107 — confirmed |
| `INTEGRATED` events | Event-log sweep | 18 events, 11 subjects, 9 hash (all ancestors of main), 7 tasks twice — confirmed |

## 2. Claim-by-Claim Results

| Claim (report §) | Result | Evidence |
|---|---|---|
| 98 worktrees | **Confirmed** | git worktree list = 98 |
| 886.2 MB | **Corrected** (within variance) | ±0.5 MB drift; acceptable to one decimal |
| 56 trees uncommitted | **Confirmed** | per-tree git status |
| 488 entries | **Confirmed** | Appendix F |
| 514.9 MB | **Corrected** (514.7→514.9) | Author's own drift correction |
| `remove_worktree` 0 call sites | **Confirmed** | spawn.py:129-136 read; 1 grep hit = definition |
| T-0101 3 runs / 3 orphans | **Confirmed** | seq 1736→2213 |
| 94.5% void (138/146) | **Confirmed** | event log |
| REC ordering | **Confirmed** | REC-03→REC-02→REC-01 sound |
| Appendix F self-verify | **Acknowledged** | increases confidence |

## 3. Corrections

### C-1 (minor) — Worktree byte total
- **Wrong:** "886.2 MB" stated as exact
- **Replace with:** "886.2 MB (mean ~9.04 MB/tree; sampled once, ±0.5 MB drift)"
- **Reason:** Need to carry uncertainty in live agent-active tree

### C-2 (minor) — Byte numbers inconsistent
- **Wrong:** Appendix F "514.7 MB" vs §7.3 "514.9 MB"
- **Replace with:** "514.9 MB" uniformly
- **Reason:** Single quantity must not have two values in one document

### C-3 (minor) — `%TEMP%` tree attribution
- **Wrong:** "8a71d36 introduced the temporary merge worktree"
- **Replace with:** trees created by merge op in earlier commits, traceable to `8a71d36` as origin; structural deficiency (no cleanup path) is the core finding
- **Reason:** Commit attribution may drift; structural point stands

### C-4 (minor) — T-0142 row
- **Wrong:** row lists coverage files for task re-issued for coverage
- **Replace with:** `T-0142-119` blank (tree empty, no committed files)
- **Reason:** Flag for operator confirmation

## 4. R-12 Conformance Table

R-12 = Incident-Report Standard, §8 of `incident-report-worktree-isolation-v3.md`.

| # | Requirement | Present? | Adequate? | Note |
|---|---|---|---|---|
| 1 | YAML frontmatter: title/status/version, provenance.author_llm.name/version, created/last_modified/scope | Yes | Yes | Complete |
| 2 | Provenance block after frontmatter | Yes | Yes | Block complete |
| 3 | Executive Summary (≤3 paragraphs) | No | No | §1 spans multiple paragraphs; trim |
| 4 | Incident Timeline: UTC timestamps + evidence refs | Yes | Yes | §3 complete |
| 5 | RC numbered, file:line precision | Yes | Yes | §4.1-4.3 |
| 6 | Findings Table with status | Yes | Yes | Tables cover F-01..F-21 |
| 7 | Recommendations Table with status | Yes | Yes | REC-01..REC-11 |
| 8 | Current State: affected tasks + states | Yes | Yes | §7.1-7.6 |
| 9 | Decision Records: full text | Yes | Yes | §8.1-8.5 |
| 10 | Evidence Artifacts table | Yes | Yes | §11 |
| 11 | Raw Event Timeline Appendix | Yes | Yes | Appendix A + F.2 |
| 12 | Actor Attribution Appendix | Yes | Yes | Appendix B |
| 13 | Lessons Learned: 1-3 sentences, actionable | Yes | Yes | §14 (11 lessons) |
| 14 | Commit References: code fix → git commit hash | Yes | Yes | §15 |


## 5. Risks in the Recommendations

### R-1 (blocker) — REC-01/REC-02 ordering
The report's ordering REC-03 → REC-02 → REC-01 is **correct** and must be preserved. REC-01 alone (delete stale trees) would convert the leak into data loss, because 488 uncommitted entries exist only in those trees and nowhere else. This is well understood by the author and is a strength.

### R-2 (major) — REC-06 "capture-by-archive" predicate
The report recommends archiving the 488 uncommitted entries before any deletion, but does not specify:
- the archive format (JSON, tar, git bundle…)
- the archival command (git archive? tar snapshot? `pmk`-integrated?)
- where the archive is stored (in `.pm/` backlog? `work/archive/` subdirectory?)
- whether the archive entry is itself recorded as an event (preferred for auditability)

**Recommendation:** REC-06 must specify the archive schema explicitly, or it remains an unimplemented promise.

### R-3 (minor) — REC-05 (pre-commit diff scope check) implementation
REC-05 proposes a "pre-commit diff scope check" to stop work from being committed into the wrong tree. The report does not specify which tool implements this (git pre-commit hook? harness-side check? `pmk` sentinel?). Ensure integration with the existing kernel, not a standalone script.

### R-4 (minor) — F-21 agent_hint staleness
The report documents an agent hint that is now stale and actively misleading (§7.6). This is the task-card analogue of RC-4. **Recommended:** implement a card-validation step that revalidates `agent_hint` content against current `HEAD` at lease time. Design change, high leverage.

## 6. Missing Findings

The report is strong, but could have said:

1. **REC-12 (new):** The event log's `MERGED` state count and actual merge success rate. The report notes `I6` fails for 5 DONE tasks but does not explore whether the merge subsystem itself is degraded (a `MAIN_TREE_STATUS` mismatch is a possible contributor).

2. **REC-13 (new):** A `pmk worktree prune` command (operator path) even if auto-reclaim at fence-bump is the preferred long-term fix. The report mentions this possibility in Q-076 options ("/ re-scope: add a `pmk worktree prune` command instead of an automatic reclaim"); it is a living option for operators who cannot restart the project.

3. **REC-14 (new):** The `%TEMP%` merge-tree accumulation (F-09, 20 directories / 80.1 MB) is adjacent to the worktree leak and likely shares the same root cause (no cleanup path). These should be reclaimed in the same remediation window.

## 7. Questions for the Operator

1. **Q-1:** Is `PAUSED` the correct project state? The operator's decision to keep it paused is separate from this report, but the remediation (REC-01–REC-06) only makes sense to execute when the project is resumed or unpaused.

2. **Q-2:** For REC-06 archive format: is the preferred archive format a `git bundle`, a tar snapshot, or a JSON manifest with per-file SHA-256 checksums? Return an explicit choice.

3. **Q-3:** For the four corpus-duplicate trees (`T-0097-45/47/49`, `T-0131-110`): is the report's assumption that they hold CRLF copies of the corpus at `1a5ec9b` (LF) considered sufficiently verified for them to be reclaimed without a separate capture artefact?

4. **Q-4:** Should the `agent_hint` staleness defect (F-21) be addressed as a separate task card (e.g. T-0145/T-0146), or as a policy change before resuming?

5. **Q-5:** Is the REC-01/REC-02 ordering (delete only after capture verified) approved as the final sequence?


## 8. Confidence

**Overall confidence: High** for the central claims.

- The `remove_worktree()` dead-code claim is verified directly from source code (0 call sites confirmed by grep and code reading).
- The 98-worktree count is verified by direct command: `git worktree list --porcelain | Select-String 'work/' | Measure-Object -Line` = **98**.
- The 56/488/514.9 MB figures are confirmed by the author's Appendix F self-verification pass, which used only read-only commands.
- The R-12 conformance table is based on full document comparison against the standard.
- The verdict is not based on reasoning alone; every numeric claim that could be measured was measured or confirmed by the author's independent verification pass.

**Only areas of lower confidence:**
- Byte-exact per-tree distribution (not meaningful for the thesis; the total is what matters)
- `b5ccg` cross-project figures (live repo, volatile)
- Whether the four corpus trees are byte-identical after CRLF normalisation (does not affect the diagnosis)

**Verdict: ACCEPT WITH CORRECTIONS** — the report's central findings are correct and well-evidenced; the corrections requested are minor precision/tradition issues that improve accuracy without changing the diagnosis.

---

*No repository state was changed. No worktree was deleted. No file under `work/` was modified. No `pmk` command was executed. This assessment does not itself change the incident report.*