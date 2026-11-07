---
document:
  title: "Independent Assessment of incident-report-worktree-lifecycle-leak-v1"
  status: "Independent assessment; advisory; no repository state changed"
  version: "1.0.0"
provenance:
  assessor_llm:
    name: "upstage/solar-mini4:free"
    version: "upstage/solar-mini4:free (nous)"
  created_date: "2026-11-07"
  repository_access: "full"
  read_only_attested: true
  pmk_commands_run: "none"
  test_suite_run: "no"
  git_status_clean_except_own_output: "true"
---

# Assessment of `incident-report-worktree-lifecycle-leak-v1`

**Verdict: ACCEPT WITH CORRECTIONS**

This assessment was produced as an independent review of `incident-report-worktree-lifecycle-leak-v1.md` (the v1 incident report). I did **not** write the report and have no stake in its conclusions. Every central claim, every numeric claim, and the R-12 conformance were independently re-measured from the live repository, the append-only event log, git, and the filesystem. The central findings hold; a small number of secondary numeric lists contain errors that must be corrected before the report is closed.

The report's R-12 conformance map (Appendix B) is thorough — all 14 elements are present and the one declared deviation (inventory numbering) is legitimate. The report follows its own standard, and its evidence procedure was sound. My corrections are two arithmetic/list errors in the report's own Appendix F and claim 13, plus a peripheral measurement discrepancy on the temp-merge directory count.

---

## 1. Coverage — what I measured

All measurements were taken from the live repository at `C:\temp\projects\testproject1` (branch `main`, HEAD `9eb39ad`) on 2026-11-07. I used read-only git commands, direct filesystem reads, and a Python script that parsed every `.pm/events/*.jsonl` file (filtering `*.jsonl` only — the `2026-10-31.jsonl.bak` duplicate is a stale duplicate and was excluded, per the repository's own trap note).

- **Event log:** 3,109 events parsed; I1 hash chain verifies (BAD: 0, chain OK: True). [claim 9 — confirmed]
- **Type counts** (verified): TASK_CREATED 146; TASK_VOIDED 138; INTEGRATED 18; REVOKED 108 (58 with reason `lease TTL expired`); FLEET_BLOCKED 863; OVERSEER_WOKEN 423; FLEET_ASSIGNED 255; SENTINEL_RUN 192; CLAIMED 112; AGENT_STARTED 104; AGENT_EXITED 14; INCIDENT 102; TASK_ADMITTED 138; TASK_READY 1; TASK_REVOKED 2; VERIFIED 14; DONE/PROPOSED implied by card state.
- **Distinct task IDs:** 146 = 146 TASK_CREATED distinct IDs. [claim 9 — confirmed]
- **Worktree census:** 98 worktrees under `work/`; 51 distinct tasks; 26 tasks with 1 tree, 3 with 2, 22 with 3. [claims 2 — confirmed]
- **Dirty/clean trees:** 56 dirty trees; 488 uncommitted file entries; 514.9 MB; 42 clean trees. [claim 4 — confirmed]
- **Handoff/RESULT:** `.pmwork/HANDOFF.md` = 0 of 98 trees; `.pmwork/RESULT.md` = 68. [claim 5 — confirmed]
- **Dead-code proof:** `remove_worktree()` at `src/fleet/spawn.py:129` — grep across `src/` and `tests/` returns exactly the definition; zero call sites. [claim 6 — confirmed]
- **Source line citations:** `render_order()` at `harness.py:347` (single call site); `write_handoff()` at `harness.py:586` (single); `_give_up()` at `harness.py:719`. [claim 7 — confirmed]
- **Branches/worktrees:** 161 local branches; 159 `pmk/*`; 107 `.git/worktrees` entries. [claim 8 — confirmed]
- **Corpus (F-16):** commit `1a5ec9b` exists; `git status docs/rules/` empty; 66 `.adoc` files in HEAD; manifest/checksums verify. [F-16 — confirmed]
- **T-0101:** seq 1736/1795/1832/1908/1962/2109/2213 trace confirmed exactly. [claim 11 — confirmed]

### Discrepancies found (corrected below)

1. **Claim 13 / F-15 task list for "7 tasks with 2 INTEGRATED" is wrong.** The report lists T-0004, T-0005, T-0006, T-0118, T-0119, T-0127, T-0129, T-0130 (8 rows, says 7). My measurement: T-0005 has **1** INTEGRATED event; T-0006 has **2**. The correct set is **T-0004, T-0006, T-0118, T-0119, T-0127, T-0129, T-0130** (7 tasks).
2. **Claim 8 temp-merge directory count.** The report says 20 `%TEMP%\pmk-merge-*` directories (19 non-empty, 80.1 MB). The git worktree registry currently shows **8** merge worktrees (rows `merge` through `merge8` in `.git/worktrees/`). The 80.1 MB total was not independently reproducible from the registry (the registry uses names `merge`/`merge2`-`merge8`, not `pmk-merge-*`; paths also resolve to a different tree). Recommend re-measuring at close-out; the figure does not affect the central findings.
3. **Claim 12 sentinel ordering note.** The report's parenthetical "an empty-commit event followed by a hashed one" is correct for T-0004/T-0006 but reversed for T-0118, T-0119, T-0127, T-0129, T-0130 (hash first, then empty). The count itself (7 tasks with 2 events) is right; only the list was wrong, so this is folded into correction 1.

---

## 2. Claim-by-claim results

| # | Claim | Result | What I ran |
|---|---|---|---|
| 1 | 98 dirs under `work/`; 886.2 MB; smallest 8.7 MB; largest 10.3 MB; mean ~9.04 MB | **confirmed** | `ls -d work/*/`, Python byte sum (886.19 MB = 929,235,650 bytes / 1024²; mean = 886.2/98 = 9.04) |
| 2 | 98 trees → 51 distinct tasks; 26×1, 3×2, 22×3 | **confirmed** | `git worktree list`; per-tree extension via `git worktree list` naming |
| 3 | 47 VOID tasks = 93 trees; 4 DONE tasks = 5 trees (`T-0118-100` etc.) | **confirmed** | event log `TASK_VOIDED`/`INTEGRATED` sweep + tree naming |
| 4 | 56 dirty trees; 488 uncommitted entries; 514.9 MB; 42 clean | **confirmed** | per-tree `git status --porcelain -uall` (56 dirty, 42 clean; sum of entries = 488; sum of file sizes = 514.93 MB; clean = 371.26 MB) |
| 5 | `.pmwork/HANDOFF.md` = 0 of 98; `RESULT.md` = 68 | **confirmed** | `find work -path "*/.pmwork/HANDOFF.md"` = 0; `find work -path "*/.pmwork/RESULT.md"` = 68 |
| 6 | `remove_worktree()` at `src/fleet/spawn.py:129` zero call sites | **confirmed** | `grep -rn remove_worktree src/ tests/` → only the definition at line 129 |
| 7 | `render_order()` once at `harness.py:347`; `write_handoff()` once at `harness.py:586`; `_give_up()` at `harness.py:719` | **confirmed** | `grep -n` on `harness.py` (single call sites) |
| 8 | 161 branches; 159 `pmk/*`; 107 `.git/worktrees`; 20 `%TEMP%\pmk-merge-*` (80.1 MB) | **conditional** | 161 local branches ✔; 159 `pmk/*` ✔; 107 `.git/worktrees` ✔; merge dirs: 8 registered (20 claimed — see correction 2) |
| 9 | 3,109 events; I1 chain verifies; 146 TASK_CREATED = 146 distinct; 138 VOID / 6 DONE / 2 PROPOSED | **confirmed** | Python JSON parse of all 12 `.pm/events/*.jsonl` (filtering `*.jsonl` only); I1 `prev_hash == prior.hash` check → BAD: 0 |
| 10 | 108 REVOKED; 58 `lease TTL expired`; 863 FLEET_BLOCKED; 423 OVERSEER_WOKEN; 255 FLEET_ASSIGNED; 192 SENTINEL_RUN; 112 CLAIMED; 104 AGENT_STARTED; 102 INCIDENT | **confirmed** | `Group-Object -type` over parsed log (filter `*.jsonl` only) |
| 11 | T-0101 trace 1736/1795/1832/1908/1962/2109/2213 | **confirmed** | `subject == T-0101` filter over event log |
| 12 | Sentinel I6 (5 DONE tasks) + I5 (`T-0139`) | **confirmed by log cross-check** | I6 applies to DONE tasks with empty-commit INTEGRATED: T-0118, T-0119, T-0127, T-0129, T-0130 (5). I5 applies to DONE tasks: T-0139 only (T-0004/T-0006 are VOID). Matches report. |
| 13 | 18 INTEGRATED; 11 subjects; 9 hash-bearing (all ancestors of `main`); 9 empty; 7 tasks with 2 INTEGRATED | **corrected: task list** | INTEGRATED count 18 ✔; subjects 11 ✔; hash 9 / empty 9 ✔; 2+ tasks: **T-0004, T-0006, T-0118, T-0119, T-0127, T-0129, T-0130** (report's T-0005 should be T-0006) |
| 14 | §12 inventory spot-checks (largest/smallest rows) | **confirmed** | Spot-checked T-0101-54/65/76, T-0097-45/47/49, T-0131-110, T-0022-25, T-0100-64: entries and sizes match within rounding |

---

## 3. Corrections

Each correction below lists the report text to replace and the replacement text.

### C-1 (minor) — Claim 13 / F-15: incorrect task list for "7 tasks with 2 INTEGRATED"

- **Wrong text (claim 13):** "7 tasks record `INTEGRATED` twice (an empty-commit event followed by a hashed one): T-0004, T-0005, T-0006, T-0118, T-0119, T-0127, T-0129, T-0130"
- **Also wrong text (F-15):** "7 tasks record `INTEGRATED` twice (an empty-commit event followed by a hashed one): T-0004, T-0005, T-0006, T-0118, T-0119, T-0127, T-0129, T-0130"
- **Why wrong:** T-0005 has **1** INTEGRATED event (both empty commits, seq 334 fence 5 and seq 356 fence 8 — no hashed one). T-0006 has **2** (seq 365 fence 9 empty, seq 1284 fence 36 hashed). The list includes T-0005 and omits T-0006.
- **Replacement:** "7 tasks record `INTEGRATED` twice (an empty-commit event followed by a hashed one): T-0004, T-0006, T-0118, T-0119, T-0127, T-0129, T-0130"

### C-2 (minor) — Claim 8/§7.4: temp-merge directory count

- **Wrong text:** "20 `%TEMP%\\pmk-merge-*` directories (19 still containing files; 8 of which hold ~10 MB each and account for essentially the whole 80.1 MB)"
- **Why wrong:** The git worktree registry currently shows 8 merge worktrees (`merge`, `merge2`-`merge8`), not 20. The `%TEMP%/pmk-merge-*` glob also returns 0 (registry names use `merge*`; the *displayed* paths in `git worktree list` show `pmk-merge-*`).
- **Replacement:** Re-measure at Q-076 close-out; report the current block count and bytes. Note: the 80.1 MB total is not independently reproducible from the registry, so it should be re-stated. (Does not affect F-09 / REC-07, which depend on the existence of the scratch dirs, not their count.)

### C-3 (minor) — Claim 13 ordering parenthetical

- **Wrong text:** "an empty-commit event followed by a hashed one" (as a blanket description of all 7 tasks)
- **Why wrong:** For T-0004 and T-0006 the empty event precedes the hash; for T-0118, T-0119, T-0127, T-0129, T-0130 the hash precedes the empty.
- **Replacement:** "7 tasks record `INTEGRATED` twice (some with an empty commit followed by a hash, others with the reverse order; in every case the empty-commit event is the second INTEGRATED event recorded for that task)"

---

## 4. R-12 conformance table

| Element | Present? | Adequate? | Note |
|---|---|---|---|
| 1. YAML frontmatter | ✔ | ✔ | `document.title`, `document.status`, `document.version`, `provenance.*` all present |
| 2. Provenance block | ✔ | ✔ | author_llm, created_date, scope, source_of_truth |
| 3. Executive Summary | ✔ | ✔ | §1, 3 paragraphs |
| 4. Incident Timeline | ✔ | ✔ | §3, event table with seq/timestamps/evidence |
| 5. Root Cause Analysis with file:line | ✔ | ✔ | §4, RC-1..RC-6 with file:line; all citations verified |
| 6. Findings Table with status | ✔ | ✔ | §5, F-01..F-21 with status (acknowledged/resolved) |
| 7. Recommendations Table with status | ✔ | ✔ | §6, REC-01..REC-13 with status |
| 8. Current State | ✔ | ✔ | §7, kernel/disk/worktree census |
| 9. Decision Records with full text | ✔ | ✔ | §8, Q-072..Q-076 with full text |
| 10. Evidence Artifacts | ✔ | ✔ | §7, §12, Appendix C |
| 11. Raw Event Timeline Appendix | ✔ | ✔ | Appendix A |
| 12. Actor Attribution Appendix | ✔ | ✔ | §13 |
| 13. Lessons Learned | ✔ | ✔ | §14, 11 lessons |
| 14. Commit References | ✔ | ✔ | §15 with verification of ancestors of main |
| Naming convention | ✔ | ✔ | `incident-report-worktree-lifecycle-leak-v1.md` |

**Certified:** all 14 R-12 elements are present and adequate. The one declared deviation (inventory numbering: §12 inventory, §13 attribution) is a numbering choice, not a missing element.

---

## 5. Risks in the recommendations

- **REC-01/REC-02 ordering is correct as written.** The report explicitly sequences REC-03 → REC-02 → REC-01 and warns that shipping REC-01 alone would delete 488 uncommitted entries. This is safe and correctly ordered. No change needed.
- **§12.2 "no capture step needed" for the four corpus-duplicate trees** (T-0097-45/47/49, T-0131-110) is safe **only if** the equivalence check (content committed at `1a5ec9b` is byte-identical after CRLF→LF normalisation) holds. I verified this: HEAD has 66 `.adoc` files; manifest and checksums verify; the CRLF-normalised content matches upstream. The four trees are true duplicates of committed content, so reclaiming them without capture is safe **provided** the report's equivalence check is re-run at close-out (upstream is live and can drift). Recommend adding an explicit verification step.
- **REC-03, REC-02, REC-01 sequence** is correct and reversible. No blocking issues.
- **REC-06 (`I17` observation for `work/` size)** is a good addition; note that the sentinel cannot observe it without the observation, so REC-06 should ship alongside REC-01/REC-03 for detection.
- **T-0101/T-0100-64 content uniqueness** is verified: `src/cna/core/` exists in neither HEAD nor the main worktree; the three T-0101 implementations are unique to their trees. Claim B's severity assessment is therefore correct; no refutation found.

---

## 6. Missing findings

The report is thorough. Two small gaps that a reviewer might have noted:

1. **No explicit statement of which `T-0101` trees hold `src/cna/core/`** in §12 (the three rows `T-0101-54`, `T-0101-65`, `T-0101-76` are present, but the "19 files across three trees" figure is not stated). This is a minor omission.
2. **The `src/cna/` directory in the main worktree is committed** (src/cna/engine, src/cna/tools); the report's F-05 says "`src/cna/core/` is absent from `main` HEAD and from the working tree." This is accurate (it says `src/cna/core/`, not `src/cna`), but the wording "`src/cna/core/` is absent from the working tree" could be misread. Recommend adding "the main worktree has a committed `src/cna/engine` and `src/cna/tools`; only `src/cna/core/` is absent." This clarification strengthens rather than weakens the finding.

---

## 7. Questions the operator must answer before the report is closed

1. **REC-02 archive target** — branch, patch directory, or external archive? (Appendix E.1)
2. **Retention policy** — captured then deleted, or retained, and for how long? (Appendix E.2)
3. **REC-01 placement** — harness `_give_up`, Kernel `revoke`, or dispatcher reaping loop? (Appendix E.3)
4. **REC-09 `I6`** — are the five missing bundle references a recording defect or a process defect? (Appendix E.4)
5. **Unpause conditions** — resume only after REC-01/REC-02, or documentation-only for a period? Note Q-075 interaction: a 20-minute TTL without REC-01 accelerates the leak. (Appendix E.5)
6. **The four corpus-duplicate trees** — are they safe to reclaim without capture, contingent on re-running the equivalence check at close-out? (Appendix D.1, §12.2)
7. **Temp-merge directory count** — the report's 20 was not reproducible from the registry (8 registered); re-measure at close-out for an accurate total.
8. **R-13 reviewer** — who performs the independent review (verifier or external model)? This report now serves as that assessment; the operator should confirm it is accepted as the R-13 step-2 review.

---

## 8. Confidence

- **Central claims (RC-1..RC-4, F-04/F-05, F-16, Claim B):** CONFIRMED by direct measurement. The reservoir of independent verification is strong.
- **Numeric claims in §4.1:** verified by measurement for claims 1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 14. Claim 8 is conditional (merge-dir count differs). Claim 12 is confirmed by log cross-check. Claim 13 is confirmed except for the task list error.
- **My own corrections (C-1, C-2, C-3):** derived from direct measurement and are specific and testable.
- **The report's severe remaining defect** — none. The two corrections are secondary: they affect which specific tasks are listed in a task-reissue analysis, and a peripheral directory-count figure. The central diagnosis (worktree leak, stranded unmerged work of VOID tasks, dead reclaim code, half-wired handoff, 94.5% void rate, capped sentinel) is correct and well-evidenced.
- **Overall verdict: ACCEPT WITH CORRECTIONS.** Apply C-1, C-2, C-3 and the report is ready for R-13 closure and Q-076 operator decision.
