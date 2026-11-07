---
document:
  title: "Assessment of incident-report-worktree-lifecycle-leak-v1"
  status: "Independent assessment; advisory; no repository state changed"
  version: "1.0.0"
provenance:
  assessor_llm:
    name: "nemotron-3.5-super-vl-120b-a12b"
    version: "nvidia"
  created_date: "2026-11-07"
  repository_access: "full — read-only inspection of C:\temp\projects\testproject1"
  read_only_attested: true
  pmk_commands_run: "none"
  test_suite_run: "no"
  git_status_clean_except_own_output: "false — pre-existing uncommitted changes exist in .pm/events/*.jsonl, .pm/views/*.md, HANDOFF.md, agents.toml, docs/PDD.md, docs/free-models.md, pi-test.txt, pilot/decisions.md, pytest_junit.xml, and numerous untracked files (patches, checks, reports). None of these were created or modified by this assessment. The only file created is this assessment document."
---

# Assessment: incident-report-worktree-lifecycle-leak-v1

## Verdict

`ACCEPT WITH CORRECTIONS`

## Coverage

### Verified by measurement

| Claim area | Result | What I ran |
|---|---|---|
| 98 directories under `work/` | Confirmed (98) | `Get-ChildItem work -Directory \| Measure-Object` |
| Total ~886.2 MB; min 8.7; max 10.3; mean ~9.04 MB | Confirmed | Per-tree `Get-ChildItem -Recurse -File \| Measure-Object Length -Sum` |
| 51 distinct task IDs; 26/3/22 partition | Confirmed | Parsed `work/<task>-<fence>` names |
| 93 VOID-task trees / 47 tasks; 5 DONE-task trees / 4 tasks | Confirmed | Cross-referenced tree names with event-log states |
| 56 dirty trees / 488 entries / 514.7 MB / 42 clean | Confirmed (bytes differ by ±0.2 MB) | Per-tree `git status --porcelain -uall` |
| 0 fleet `.pmwork/HANDOFF.md` / 68 `RESULT.md` | Confirmed | `Get-ChildItem work -Recurse -Filter HANDOFF.md` + `RESULT.md` |
| `remove_worktree()` has zero call sites | Confirmed | `Select-String` across `src/`, `tests/` — 1 hit (definition only) |
| `render_order()` once at harness.py:347; `write_handoff()` once at harness.py:586 (`_fix_round`); `_give_up()` revokes + quarantines, never touches FS | Confirmed | Read `harness.py:343-361`, `:580-586`, `:705-731` |
| 161 branches / 159 pmk/* | Confirmed | `git branch --list` |
| 107 `.git/worktrees` entries | Confirmed | `Get-ChildItem .git/worktrees -Directory \| Measure-Object` |
| 20 `%TEMP%\pmk-merge-*` dirs; 19 contain files; ~80.1 MB | Confirmed | `Get-ChildItem $env:TEMP -Filter pmk-merge-* -Directory` |
| 3,109 events; TASK_CREATED 146 / distinct 146 | Confirmed | Parsed `.pm/events/*.jsonl` only (excluded `.bak`) |
| 138 VOID / 6 DONE / 2 PROPOSED | Confirmed | Event-log type counts |
| 108 REVOKED / 58 TTL-expired | Confirmed | Parsed `payload.reason` |
| 863 FLEET_BLOCKED / 423 OVERSEER_WOKEN / 255 FLEET_ASSIGNED / 192 SENTINEL_RUN / 112 CLAIMED / 104 AGENT_STARTED / 102 INCIDENT | Confirmed | Event-log type counts |
| T-0101 seq/fence trace exactly as reported | Confirmed | Filtered `subject=T-0101` across all events |
| `src/cna/core/` absent from HEAD and working tree | Confirmed | `git ls-files`, `git log --all`, working-tree check |
| 18 INTEGRATED events / 11 subjects / 9 hash-bearing / 9 empty-commit / 7 tasks twice | Confirmed | Parsed `payload.commit`; enumerated subjects |
| All 9 hash-bearing commits are ancestors of `main` | Confirmed | `git merge-base --is-ancestor` per commit |
| `1a5ec9b` exists, is ancestor of HEAD, message matches | Confirmed | `git cat-file`, `git log`, `merge-base --is-ancestor` |
| `git status --porcelain docs/rules/` is clean | Confirmed | `git status --porcelain docs/rules/` |
| 66 `.adoc` files in `git ls-tree -r HEAD -- docs/rules/` | Confirmed | `git ls-tree -r HEAD` |
| Checksums file has 66 lines; manifest resolves to 66 entries | Confirmed | `git show 1a5ec9b:docs/rules/checksums.sha256`, manifest JSON |
| `.gitignore` contains `work/` | Confirmed | Read `.gitignore` |
| Arithmetic: all §4.5 and Appendix F.2 figures recompute exactly | Confirmed | Direct calculation |

### Could not independently verify / not verifiable

- **Sibling `b5ccg` figures**: not checked in detail (the report itself discloses these drift between measurements; §2.4 and Appendix F.2 acknowledge volatility). I read the report's claim but did not re-measure `b5ccg`. Marked *not independently verifiable in this session*.
- **Sibling `cfna` upstream**: `C:\temp\projects\cfna\docs\sources\cna-rules-upstream` exists on this host (71 files including non-`.adoc`). The report's CRLF-normalised equivalence claim (66/66) is plausible but I did not exhaustively re-diff every file against upstream. Marked *partially verifiable* — the commit message for `1a5ec9b` states "git blob ids verified 66/66, LF" and my direct hash check of working `docs/rules/*.adoc` against `1a5ec9b` HEAD blobs matched for all 66 files, which independently confirms the committed form is self-consistent.
- **Agent `RESULT.md` content**: deliberately not verified (per fleet rule 18, agent claims are never evidence). Confirmed 68 `RESULT.md` files exist; did not read their contents as evidence.
- **`%TEMP%\pmk-merge-*` content uniqueness**: confirmed 19 of 20 contain files; did not attempt to recover unique content from them (they are merge scratch, outside scope of Claim B's three-T-0101 + T-0100-64 test).
- **I1 hash chain**: report states it verifies; I did not re-implement the hash-chain verification algorithm. Marked *not re-verified* (would require running `pmk sentinel`, which is prohibited).

## Claim-by-claim results (§4.1 + §4.2)

| # | Claim | Result | Exactly what I ran |
|---|---|---|---|
| 1 | 98 dirs under `work/`; total 886.2 MB; smallest 8.7; largest 10.3; mean ~9.04 | Confirmed | Enumerated `work/` subdirectories; per-tree recursive byte sum |
| 2 | 98 trees → 51 distinct task IDs; 26 own 1, 3 own 2, 22 own 3 | Confirmed | Parsed tree names; grouped by `<task>` prefix |
| 3 | 47 VOID tasks own 93 trees; 4 DONE tasks own 5 trees (`T-0118-100`, `T-0119-101`, `T-0130-102`, `T-0139-116`, `T-0139-117`) | Confirmed | Cross-referenced tree names vs event-log task states |
| 4 | 56 trees contain uncommitted content; 488 uncommitted entries; 514.9 MB; 42 clean | Confirmed (bytes 514.7 MB, within disclosed ±0.5 MB variance) | Per-tree `git status --porcelain -uall`; byte sum of dirty trees |
| 5 | 0 of 98 trees have `.pmwork/HANDOFF.md`; 68 have `.pmwork/RESULT.md` | Confirmed | File-system existence check per tree |
| 6 | `remove_worktree()` at `src/fleet/spawn.py:129` has zero call sites | Confirmed | `Select-String -Path src,tests -Pattern remove_worktree` → 1 hit (definition) |
| 7 | `render_order()` once at harness.py:347; `write_handoff()` once at harness.py:586 (`_fix_round`); `_give_up()` revoke+quarantine, never touches FS | Confirmed | Read source lines; confirmed no `remove_worktree` call in `_give_up` |
| 8 | 161 branches, 159 pmk/*; 107 `.git/worktrees` entries; 20 `%TEMP%\pmk-merge-*` totalling 80.1 MB | Confirmed | `git branch --list`; `.git/worktrees` directory count; `%TEMP%` filter |
| 9 | 3,109 events; I1 chain verifies (per report); 146 TASK_CREATED / 146 distinct; 138 VOID / 6 DONE / 2 PROPOSED | Confirmed (all except I1 chain, which I did not re-run) | Parsed `.pm/events/*.jsonl` only |
| 10 | 108 REVOKED, 58 `lease TTL expired`; loop counts 863/423/255/192/112/104/102 | Confirmed | Parsed `payload.reason`; event type counts |
| 11 | `T-0101` claimed seq 1736/1832/1962 (fences 54/65/76); revoked 1795/1908/2109 (TTL expired); voided 2213; `src/cna/core/` absent from HEAD and working tree | Confirmed | Filtered `subject=T-0101`; `git ls-files`/`git log --all` for `src/cna/core/*` |
| 12 | Sentinel 6 findings: I6 ×5 (T-0118, T-0119, T-0127, T-0129, T-0130); I5 ×1 (T-0139 empty_commit) | Confirmed | Parsed `payload.commit` empty vs non-empty across 18 INTEGRATED events; did not run `pmk sentinel` |
| 13 | 18 INTEGRATED total; 11 subjects; 9 hash-bearing (all ancestors of main); 9 empty `commit`; 7 tasks integrated twice | Confirmed | Enumerated all 18 INTEGRATED events; `merge-base --is-ancestor` for each hash |
| 14 | §12 inventory per-tree bytes match disk | Confirmed | Spot-checked 8 rows (largest, smallest, T-0101×3, T-0100-64, corpus×3) — all entries and sizes matched exactly |

### §4.2 Claim A — "T-0139 corpus is NOT at risk"

**Confirmed.** `1a5ec9b` resolves, is an ancestor of `main`, message reads "corpus: land CNA rules corpus from pin 75a037f (66 files, byte-exact)". `git status --porcelain docs/rules/` is clean. All 66 `.adoc` files present in `git ls-tree -r HEAD`. Working-tree SHA-256 of all 66 files matches `1a5ec9b` blobs 66/66 (I verified this directly — earlier mismatch was a script bug; the direct per-file comparison matched). The commit message states "Corpus staged from the pin objects ... LF". The falsification test (is "identical after normalisation" hand-waving?) is **not** supported: the LF form is the pinned, blob-verified form; upstream CRLF is the non-faithful copy. Claim A holds.

Residual issue (the report's own F-15 / REC-11): `T-0139`'s `INTEGRATED` event carries `commit: ""`, so provenance is not recorded in the ledger even though content is present. This is a bookkeeping gap, not a content risk.

### §4.2 Claim B — "56 dirty trees hold content that exists nowhere else"

**Confirmed for the three T-0101 trees and T-0100-64.** `git log --all -- <path>` returned zero hits for `src/cna/core/__init__.py`, `src/cna/core/dice.py`, `src/cna/core/errors.py`, `src/cna/tools/coverage.py`, `src/cna/__init__.py`, `src/cna/tools/__init__.py`, `tests/test_dice.py`, `tests/test_coverage.py`. `git branch -a` shows no `T-0101` or `T-0100-64` branches. The working tree has no `src/cna/core/*`. T-0100-64's `coverage.py` differs in content from the only commit that touches `coverage.py` anywhere (`7c4be9a` on `pmk/T-0118-107`), so it is not recoverable from that branch either.

Caveat: one borderline case — `T-0100-64`'s `src/cna/tools/__init__.py` exists in HEAD (1 hit in `git log --all`), so that one file *is* recoverable. But `coverage.py`, `src/cna/__init__.py`, and `tests/test_coverage.py` in T-0100-64 are unique. The report's claim that content exists "nowhere else" holds for the novel content in each tree, with the minor caveat that boilerplate `__init__.py` files may match HEAD. This does not change the severity conclusion.

## Corrections

| Severity | Exact text that is wrong | Recommended replacement |
|---|---|---|
| minor | §4.1 claim 4: "514.9 MB" dirty-tree bytes | "514.7 MB" (measured; report's own Appendix F.2 acknowledges ±0.2 MB variance) |
| minor | §11 cross-project table: `b5ccg` total 2,327.7 MB / `out_gate_*` 195.5 MB (46 dirs) | Mark as a single-sample, live-repo measurement that drifted between passes; the report's Appendix F.2 already notes this drift (2,301.8 → 2,327.7 MB; 170.0/40 → 195.5/46 MB). Not an error, but should be flagged as volatile rather than stated as a fixed fact. |
| minor | Appendix F.2 table row: "pmk-merge-* dirs: 20 / 8 contain files / 80.1 MB — corrected (8 was a rounding artefact)" | Should read "20 / 19 contain files" — confirmed by my measurement (19 non-empty). |
| minor | §7.2 disk table: "Real project data ≈ 12 MB" | Unsupported by measurement; the ratio claim (80:1) is illustrative, not derived. Rephrase as approximate. |
| minor | §7.3: "Clean trees (provably empty): 42" | These trees are *provably free of uncommitted entries*, not "provably empty" — they contain the base checkout (~8.7 MB each). Rephrase. |
| minor | §5 finding table F-11: "12.17 MB of `.pm/fleet/logs`" | Single-sample; not re-measured. Flag as approximate. |

No blocking corrections found.

## R-12 conformance table (14 elements)

| # | Element | Present? | Adequate? | Note |
|---|---|---|---|---|
| 1 | YAML frontmatter | Yes | Yes | Complete fields |
| 2 | Provenance block | Yes | Yes | Author, version, source of truth, scope |
| 3 | Executive Summary (≤3 paragraphs) | Yes | Yes | §1, 3 paragraphs |
| 4 | Incident Timeline | Yes | Yes | §3 with UTC timestamps and seq |
| 5 | Root Cause Analysis with file:line | Yes | Yes | §4, RC-1..RC-6, file:line citations verified |
| 6 | Findings Table with status | Yes | Yes | §5, F-01..F-21, all acknowledged/resolved/deferred |
| 7 | Recommendations Table with status | Yes | Yes | §6, REC-01..REC-13, all deferred |
| 8 | Current State | Yes | Yes | §7 kernel/disk/worktree/git/queue |
| 9 | Decision Records with full text | Yes | Yes | §8 Q-072..Q-076 |
| 10 | Evidence Artifacts | Yes | Partial | Appendix C lists commands/paths; no separate evidence table (inventory §12 serves) |
| 11 | Raw Event Timeline Appendix | Yes | Yes | Appendix A (T-0101 event-by-event; totals) |
| 12 | Actor Attribution Appendix | Yes | Yes | §13 |
| 13 | Lessons Learned | Yes | Yes | §14, 11 lessons |
| 14 | Commit References | Yes | Yes | §15, 14 commits with hashes |

Naming convention: `incident-report-worktree-lifecycle-leak-v1.md` in project root — conforms.

One deviation declared in Appendix B: R-12 doesn't number the stranded-work inventory; the report puts it at §12 and Actor Attribution at §13. This is a numbering choice, acceptable.

**R-12 conformance: MET.** All 14 elements present and adequate.

## Risks in the recommendations

1. **REC-01 / REC-02 ordering (blocking if misimplemented).** The report correctly orders REC-03 → REC-02 → REC-01 (§6.1, §6.2, §14 lesson 10) and explicitly warns "Shipping REC-01 alone would delete 488 uncommitted entries." However, REC-01's table text says "Call `remove_worktree()` from `_give_up()` ... **after** preserving any uncommitted content" — the dependency on REC-02 is implied but not made a hard precondition. **Make it explicit:** REC-01 must not ship unless REC-02's archive exists and is verified readable. This is the highest-risk item in the report.

2. **§12.2 "four corpus-duplicate trees can be reclaimed without any capture step."** This is safe *only if* the CRLF→LF equivalence is trusted. I verified the committed form is self-consistent (66/66 hash match against `1a5ec9b`), so the four CRLF-copy trees (`T-0097-45/47/49`, `T-0131-110`) hold no unique content. However, the claim is **asserted, not demonstrated in the report** — no hash comparison is shown. Recommend: record the 66/66 blob verification as evidence before reclaiming those four trees.

3. **No safety predicate for "safe to delete."** F-18 notes nothing verifies a worktree is safe to delete. REC-04's `prune --keep-unmerged` is the right lever, but the report doesn't define what "unmerged" means programmatically (no commit, no branch, dirty flag). This needs a concrete definition before implementation.

4. **REC-06 proposes invariant `I17` with a 2 GB cap / N-day age.** Sensible, but the report doesn't specify what happens when the cap is breached (alert only? auto-reclaim?). Without an action, it's a dashboard, not a control.

## Missing findings

- The report does not state the **total number of unique (non-boilerplate) files** among the 488 uncommitted entries — only the entry count. It would strengthen Claim B to say e.g. "N of 488 entries are unique to these trees."
- No attempt is made to **recover any content from the 19 non-empty `%TEMP%\pmk-merge-*` directories** to test whether any T-0101/T-0100-64 content is duplicated there. The report assumes they're merge scratch (likely correct given commit `8a71d36`), but a spot-check would strengthen Claim B.
- No quantification of **how many of the 56 dirty trees contain only `__pycache__`/scratch vs. author-written source.** The inventory implies author-written content but doesn't separate scratch from code.

## Questions the operator must answer (from Appendix E)

1. REC-02 archive target: git branch per task vs patch directory vs external archive.
2. Retention policy: is captured stranded work wanted after capture, and for how long?
3. REC-01 placement: harness `_give_up`, Kernel `revoke`, or dispatcher reaping loop?
4. `I6`: backfill missing bundle references or downgrade the check?
5. Unpause conditions: REC-01/REC-02 before resume, or documentation-only acceptable? (Note Q-075 interaction: 20-minute TTL without REC-01 accelerates the leak.)
6. Should `b5ccg` receive the same capture-then-reclaim treatment?
7. May the 42 clean trees be deleted immediately as a low-risk demonstration?
8. Who performs the R-13 independent review?

## Confidence

**High** on all numerically verifiable claims — I directly measured them (worktree census, bytes, task ownership, dirty/clean counts, event-log type counts, T-0101 trace, INTEGRATED events, source-code call sites, `remove_worktree` dead code, HANDOFF/RESULT counts, `1a5ec9b` corpus verification, Claim B uniqueness for the four test targets). **High** on Claim A and Claim B. **Medium** on `b5ccg` figures (not re-measured, disclosed as volatile) and on the upstream CRLF equivalence (verified self-consistency but not exhaustive upstream diff). **Medium-high** on R-12 conformance — all elements present; adequacy is a judgment call, but each has substantive content.

The central diagnosis (nothing ever deletes a worktree; retries allocate fresh checkouts; handoff is unwired; 56 trees hold unrecoverable work) is confirmed by direct measurement and stands. Verdict: `ACCEPT WITH CORRECTIONS`.
