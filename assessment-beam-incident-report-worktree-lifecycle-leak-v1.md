---
document:
  title: "Assessment of incident-report-worktree-lifecycle-leak-v1"
  status: "Independent assessment; advisory; no repository state changed"
  version: "1.0.0"
provenance:
  assessor_llm:
    name: "Beam"
    version: "ollama/beam"
  created_date: "2026-11-07"
  repository_access: "full (read-only) — filesystem, git object store, event log, siblings cfna/b5ccg"
  read_only_attested: true
  pmk_commands_run: "none"
  test_suite_run: "no"
  git_status_clean_except_own_output: "true — only the assessment file was added; pre-existing modified/untracked files unchanged"
---

# Assessment of `incident-report-worktree-lifecycle-leak-v1.md`

## 1. Verdict

`ACCEPT WITH CORRECTIONS`. The central claims hold (stranded work is real and uncommitted, T-0101 was implemented three times and delivered zero times, the reclamation code is never called on the worker path), the majority of numeric claims reproduce exactly, the recommendations are safely ordered, and R-12 is met. Corrections are minor except one: `write_handoff()` is not called only once — it has three call sites, so the report's "only once" statements must be rewritten.

## 2. Coverage

**Verified by direct measurement.** All 14 §4.1 claims (see table); Claim A corpus equivalence; Claim B uniqueness for T-0101-* and T-0100-64 via `git log --all -- <path>`, `git rev-list --objects --all`, blob-hash presence, and main-tree checks; R-12 14-element conformance; arithmetic; file:line citations for the primary code references; key commit hashes. Logs, event counts and hash-chain linkage independently recomputed (chain linkage 0 breaks, seq 1–3109 contiguous). Commit hashes in §15 all resolve.

**Not independently verified / with caveats.**
- `.pm/fleet/logs` byte total and b5ccg aggregates (measured: 12.16 MB and 2,340.9 MB top level; close to report).
- `b5ccg` figures: the reported dominant classes live one level deeper (`b5ccg/b5ccg/scratch`, `b5ccg/b5ccg/out_gate_*`). Top-level aggregate differs only by drift (+0.6%); qualitative claim (uncollected per-run artefacts) holds.
- Pin `75a037f` is not a present git object in `cfna` (that repo has no commits), so "staged from pin's git objects" could not be object-verified; normalised content equivalence (66/66) was verified.
- Tests were not run (rule followed); report's test counts taken as stated.

## 3. Claim-by-claim results

| Claim | Result | What I ran |
|---|---|---|
| 1 (98 trees, 886.2 MB, 8.7/10.3, mean ~9.04) | confirmed (98, 886.19 MB, 8.72/10.34, 9.0427) | `Get-ChildItem work -Directory` + per-tree recursive byte sum |
| 2 (51 distinct, 26/3/22) | confirmed | grouped `work/<task>-<fence>` names |
| 3 (47 VOID / 93 trees, 4 DONE / 5 trees) | confirmed (47/93, 4/5, named tasks) | KEPT IDs intersected with event-log derived state (138 VOID / 6 DONE / 2 PROPOSED) |
| 4 (56 dirty, 488 entries, 514.9 MB; 42 clean) | confirmed | per-tree `git status --porcelain -uall` + byte sum |
| 5 (0 `.pmwork/HANDOFF.md`; 68 `RESULT.md`) | confirmed | filesystem existence |
| 6 (`remove_worktree()` zero call sites) | confirmed (definition only) | recursive scan of `src/`, `tests/` for `remove_worktree` |
| 7 (render_order one call at 347; write_handoff one call at 586; _give_up no fs) | **partly wrong**: `render_order` once (yes); `_give_up` no filesystem touch (yes); `write_handoff` has 3 call sites, not 1 (see Correction C-1) | grep over `src/` |
| 8 (161 branches, 159 `pmk/*`; 107 `.git/worktrees`; 20 temp, 80.1 MB) | confirmed after correct `+`/`*` prefix handling (159 unique `pmk/*` names) | `git branch --list`, `git worktree list` |
| 9 (3,109 events; I1 chain verifies; 146 `TASK_CREATED` / 146 distinct; 138/6/2) | confirmed (contiguous seq 1–3109, 0 link breaks, 146/146) | parsed `*.jsonl` only, sorted by seq, compared prev_hash linkage |
| 10 (108 REVOKED, 58 TTL; 863/423/255/192/112/104/102) | confirmed (58/108 exactly "lease TTL expired") | event type + payload reason counts |
| 11 (T-0101 seq/fence/void trace; `src/cna/core/` absent) | confirmed (seqs and fences exact; HEAD and working tree both lack `src/cna/core`) | filtered T-0101 events + `git ls-tree` / filesystem |
| 12 (6 sentinel findings; I6×5 + I5 T-0139) | confirmed via `src/pmk/sentinel.py` emulation on DONE tasks (5 empty bundles, 1 empty commit, stops flags match) | code read + latest INTEGRATED payload per DONE task |
| 13 (18 INTEGRATED, 11 subjects, 9 hash-bearing all ancestors, 9 empty, 7 double) | confirmed; all 9 hashes `merge-base --is-ancestor` ancestors of `main` | event log + git |
| 14 (spot-check inventory) | confirmed 7 rows including largest/smallest extremes (bytes and entry counts match report's table) | per-tree bytes + `git status --porcelain -uall` |
| A (corpus committed at `1a5ec9b`; clean status; 66/66 manifest+checksums; normalized-identical to upstream) | confirmed (status clean; 66 verify both; 66/66 equal after CRLF→LF); attempt to falsify by lone-CR/other-byte drift found none | `git status`, sha256 vs both files, byte comparison after normalization |
| B (three T-0101 trees + T-0100-64 unique) | confirmed for T-0101 (0 commits, 0 object-store hits for the path, absent from main tree) and for T-0100-64 (4 file blobs absent from object store; coverage.py differs from HEAD's version) | `git log --all -- <path>`, `git rev-list --objects --all`, `git cat-file -e <blob>`, main-tree checks |

## 4. Corrections

**C-1 (major) — `write_handoff()` call count.**
- *Wrong text:* "write_handoff() is called once, at `harness.py:586`, inside `_fix_round` only" (§4.4 claim 7, §10.1 table) and "RC-4 … `write_handoff()` wired on only one of three paths."
- *Measured:* `src/fleet/dispatcher.py:383` (L2 profile-swap recovery) and `src/pmk/cli.py:617` (`pmk agent send`) also call `write_handoff`. That is three automatic/operator call sites. The forensic count (0 fleet-generated `.pmwork/HANDOFF.md` in 98 trees) is unaffected, but the explanation needs to say why it still yields zero (the surviving paths are rarely reached and none exists on the give-up/TTL-expiry path, which is 53.7% of revocations).
- *Replacement:* "Call sites exist in `harness.py:586` (oracle failure), `dispatcher.py:383` (L2 recovery) and `cli.py:617` (`pmk agent send`); none on the give-up or TTL-expiry path. Count in surviving trees: 0."

**C-2 (minor) — `.git` size drift / commit objects.**
- *Text:* "`.git` real pack 2.67 MB".
- *Measured now:* packs 2.62 MB (2.27 + 0.35). Treat as measurement drift, not an error. (Within the report's own ±0.5 MB volatility caveat.)

**C-3 (minor) — `b5ccg` path labelling in §11.**
- *Text:* describes `scratch/` and `out_gate_*` as top-level dominant consumers.
- *Measured:* they live under `b5ccg/b5ccg/`. Aggregate (2,340.9 MB top level) is within drift of the reported 2,327.7 MB. Relabel paths or state that the dominant classes are nested. No conclusion changes.

**C-4 (minor) — other-dirty-tree byte aggregate in §12.2.**
- *Text:* "476.8 MB" for the remaining 52 dirty trees.
- *Measured now:* 476.9 MB. Within stated ±0.5 MB volatility. The printed sum 371.3 + 38.1 + 476.8 = 886.2 is arithmetically correct as written.

**C-5 (minor) — root `HANDOFF.md` size.**
- *Text:* "4,692 bytes".
- *Measured now:* 6,088 bytes (it is tracked; content moved). Tracked/untracked status unchanged; update the constant.

## 5. R-12 conformance table

| # | R-12 element | Present? | Adequate? | Note |
|---|---|---|---|---|
| 1 | YAML frontmatter (title/status/version/author/created/modified/scope) | yes | yes |  |
| 2 | Provenance block | yes | yes |  |
| 3 | Executive Summary (≤3 paragraphs) | yes | yes |  |
| 4 | Incident Timeline | yes | yes | UTC timestamps, evidence refs |
| 5 | Root Cause Analysis with file:line | yes | yes | RC-1..RC-6 all cite file:line |
| 6 | Findings table with status | yes | yes | F-01..F-21 |
| 7 | Recommendations table with status | yes | yes | REC-01..REC-13 |
| 8 | Current State | yes | yes | §7 + census |
| 9 | Decision Records full text | yes | yes | Q-072..Q-076 |
| 10 | Evidence Artifacts | yes | yes | Appendix C + §7/§12 |
| 11 | Raw Event Timeline Appendix | yes | yes (selected) | Selected T-0101 expanded; others summarised; scope disclosed |
| 12 | Actor Attribution Appendix | yes | yes (relocated) | Lives at §13, not an appendix; deviation declared |
| 13 | Lessons Learned | yes | yes | 11 lessons |
| 14 | Commit References | yes | yes | All quoted hashes verified to resolve |
| — | Naming convention `incident-report-<topic>-v<N>.md` | yes | yes |  |

## 6. Risks in the recommendations

- **REC-01/REC-02 ordering is safe and unambiguous.** §6.1 states REC-03 → REC-02 → REC-01 explicitly and warns that REC-01 alone would delete 488 entries. Implementing REC-01 without REC-02 would destroy the only copies identified in Claim B; the ordering shown is correct.
- **§12.2 "no capture step needed" for four corpus-duplicate trees is defensible** for the 66 corpus `.adoc` files (verified byte-identical after CRLF→LF) but I verified only the corpus payloads; their `manifest.json`/`checksums.sha256` (CRLF vs LF) have not been diff-reviewed even though they are derived artefacts. Safe as written, but I would capture them too (cost: ~38 MB) given the "never delete without a captured copy" rule in REC-02; classifying four trees as exception is a thin margin.
- **REC-07 (temp merge scratch) is safe** to reclaim: 19/20 contain files but the 8 ~10 MB trees are redundant merge checkouts; nothing unique reported and main tree is clean on the relevant corpus.
- `src/pmk/api.py:998` `shutil.rmtree(worktree)` cleans only `work/context-sync` (the context-sync routine), not worker trees — it does not refute Claim B and should not be counted as an existing reclamation path.

## 7. Missing findings

- The handoff channel is not merely "wired on one of three paths" in the static sense (see C-1). In behaviour it is still effectively absent (0/98), but the report's code-level description is incomplete and should cite all three sites plus why none fires during TTL expiry.
- `work/context-sync` is the one directory under `work/` that the Kernel *does* reclaim (context-sync routine). Worth one line so REC-04's `pmk worktree list` spec does not accidentally flag it.
- No measurement or invariant covers worktree *age* today (REC-06 already proposes I17); report's F-18 documents dependency but does not mention the context-sync exception above.

## 8. Questions the operator must answer before closing the report

1. Accept REPAIR of C-1 wording before an R-13 reviewer sees it?
2. For REC-02: are patch-style archives sufficient, or do the potentially valuable trees (T-0101's three `src/cna/core/` variants) require full tree snapshots?
3. Are the four corpus-duplicate trees reclaimed with or without capture (see §6 risk)?
4. Confirm unpause only after REC-01/REC-02 land, per the Q-075 interaction (§8.4 of the report).
5. Who performs R-13 review now that three reviewer agents were unavailable?

## 9. Confidence

Most of the verdict rests on direct measurement (all 14 numeric claims, both central claims, R-12 conformance against the code, arithmetic, commit resolution). Only the qualitative cross-project comparison and the pin provenance story rest partly on reasoning from the document plus directory inspection. Confidence in `ACCEPT WITH CORRECTIONS` is high.
