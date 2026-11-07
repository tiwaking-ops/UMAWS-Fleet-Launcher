---
document:
  title: "Assessment of incident-report-worktree-lifecycle-leak-v1"
  status: "Independent assessment; advisory; no repository state changed"
  version: "1.0.0"
provenance:
  assessor_llm:
    name: "GLM-5.3-Flash"
    version: "z-ai/glm-5.3-flash (provider: nvidia), via OpenCode"
  created_date: "2026-11-07"
  repository_access: "full — C:\\temp\\projects\\testproject1; sibling dirs C:\\temp\\projects\\cfna, C:\\temp\\projects\\b5ccg, C:\\temp\\tcanf-clone and C:\\temp\\corpus-staging-75a037f all present and used"
  read_only_attested: true
  pmk_commands_run: "none"
  test_suite_run: "no"
  git_status_clean_except_own_output: "true in the sense attested — the working tree was already dirty before this assessment began (17 modified tracked files, ~100 untracked; all pre-existing, see §10 mtime evidence); the ONLY change this assessment made to the repository is its own output file. All git invocations were run with GIT_OPTIONAL_LOCKS=0 so git could not write index files; no file under work/, .pm/, src/ or tests/ was created, modified or deleted."
---

# Assessment of `incident-report-worktree-lifecycle-leak-v1.md`

Assessor: **GLM-5.3-Flash** (`z-ai/glm-5.3-flash`). I did not write the report under review and I had no part in its conclusions. Everything below labelled *measured* was measured by me in this session, read-only.

---

## 1. Verdict

**ACCEPT WITH CORRECTIONS.**

The report's two central claims both survive adversarial verification by measurement, its event-log and worktree numbers are reproducing to the digit, its R-12 conformance is real, and its recommendation ordering (REC-03 → REC-02 → REC-01) is unambiguous and safe. The corrections required are real but minor: they concern unit labels (MB vs MiB), three imprecise code-behaviour claims (`write_handoff` call sites, the `pmk-merge-*` "no cleanup path" claim, the "never deleted" absolute), one table that does not sum (§9.2), and two overstated cadence figures. None of them changes a conclusion, a severity rating, or makes any recommendation unsafe as written.

---

## 2. Coverage

**Verified by direct measurement (read-only):**

- Re-parsed all 12 `.pm/events/*.jsonl` files (excluding `2026-10-31.jsonl.bak`) and **re-implemented the I1 hash chain independently** from `src/pmk/events.py::compute_hash` (sha256 over `prev_hash + "\n" + canonical_json(body)`), verifying all 3,109 events.
- Replayed the task state machine (mirroring `src/pmk/state.py::rebuild`) to derive per-task final states.
- Full census of `work/` twice: per-tree byte totals (recursive, hidden files included), per-tree `git status --porcelain -uall` (98 worktrees, `GIT_OPTIONAL_LOCKS=0`), `.pmwork/HANDOFF.md` / `RESULT.md` presence, task↔tree mapping.
- Independent blob-level (git blob sha1) analysis of all 488 uncommitted entries; `git log --all`, `git log --all --find-object=<sha>`, `git cat-file -e HEAD:<path>` per path for the four focus trees; main-working-tree presence checks.
- Claim A end-to-end: `git status --porcelain docs/rules/`; sha256 of working files vs `HEAD:docs/rules/manifest.json` and `HEAD:docs/rules/checksums.sha256`; CRLF→LF-normalised comparison vs `C:\temp\projects\cfna\docs\sources\cna-rules-upstream`; **and the pin chain**: `C:\temp\corpus-staging-75a037f` (66/66 blob-identical to `1a5ec9b`) and `tcanf-clone@75a037f` (66/66 blob-identical to `1a5ec9b`).
- Sentinel re-derivation from `src/pmk/sentinel.py` logic + log + `.pm/evidence/*/bundle.json` — without running `pmk sentinel`.
- Every `file:line` citation in §4/§10 and every commit hash in §15 (`git show -s`, `git merge-base --is-ancestor`).
- Spot-check of **22 of the 56** §12 rows against disk, deliberately including the three largest (10.3), several smallest (8.7), the three corpus trees and all three T-0101 trees.
- Disk component sizes for every row of §7.2; `.pm/fleet/logs`, `.git/worktrees`, `%TEMP%\pmk-merge-*` (all 20 sized individually).
- Arithmetic in §4.5 of my brief, recomputed independently.

**Not verifiable / not done:**

- **§11 (`b5ccg`) could not be reproduced.** The repository moved materially since the report's pass: `scratch/` is now 1.6 MiB (17 files) — the report measured 1,230.1 MB — and **no `out_gate_*` directories exist** (report: 195.5 MB, 46 dirs). `.agent` (314.0 vs 313.8) and `.git` (236.9 vs 236.9) match to the decimal, so the movement is specific to the generated dirs. The report discloses this volatility (§2.4, §11), but as of this assessment the "61.2%" figure describes a state that no longer exists. Treat §11 as a historical snapshot, not current fact.
- §9.3's reissue-cluster counts (13/9/5/6/…) are fuzzy card-text classifications; I could only approximate them by keyword counting (e.g. 14 cards contain "vendor rules"). Directionally consistent; neither confirmed nor refuted.
- I did not read the pre-existing `assessment-nemotron-incident-report-worktree-lifecycle-leak-v1.md`, to keep this assessment independent.
- Per the brief: no `pmk` command, no test run, nothing under `work/` touched.

---

## 3. Claim-by-claim results

Every "measured" value below is my own. **Unit note:** the report's disk figures are **MiB** mislabelled as MB (PowerShell's `1MB` constant = 2²⁰). I give both: `dec MB / MiB`. Under the MiB reading the report's numbers reproduce exactly; this is Correction C2, not a refutation.

| # | Claim (report) | Result | What I ran |
|---|---|---|---|
| 1 | 98 trees; 886.2 MB; min 8.7; max 10.3; mean ~9.04 | **Confirmed** (as MiB): 98 trees; 929.2 dec MB = **886.2 MiB**; min 9.14 dec = 8.72 MiB; max 10.84 dec = 10.34 MiB; mean 9.482 dec = **9.043 MiB** | Python `os.walk` byte sums over all 98 trees, two passes |
| 2 | 51 tasks; 26×1, 3×2, 22×3 | **Confirmed**: 51 tasks; distribution 26/3/22 | group tree names by task prefix |
| 3 | 47 VOID tasks → 93 trees; 4 DONE tasks → 5 trees (`T-0118-100`, `T-0119-101`, `T-0130-102`, `T-0139-116`, `T-0139-117`) | **Confirmed** exactly, incl. the five named trees; all 5 DONE trees are clean (0 entries) | state replay from log × tree map |
| 4 | 56 dirty trees; 488 entries; 514.9 MB; 42 clean | **Confirmed**: 56; **488**; 539.9 dec = **514.9 MiB**; 42 | per-tree `git status --porcelain -uall` + sums |
| 5 | `.pmwork/HANDOFF.md` in 0/98; `.pmwork/RESULT.md` in 68 | **Confirmed**: 0 and 68 | `Test-Path` per tree |
| 6 | `remove_worktree()` at `spawn.py:129`, zero call sites in `src/`+`tests/` | **Confirmed**: exactly 1 hit = the definition (`spawn.py:129`); zero call sites | recursive grep `remove_worktree(` over `src/`, `tests/` |
| 7 | `render_order()` once (harness:347); `write_handoff()` once (harness:586, `_fix_round` only); `_give_up()` (harness:719) = revoke+quarantine, never touches fs | **Corrected**: `render_order` once ✓ (harness.py:347); `_give_up` ✓ (revoke at 722, quarantine at 726, no fs calls); **`write_handoff` has three call sites**: harness.py:586 (`_fix_round`), **dispatcher.py:383 (L2 recovery)**, **cli.py:617 (`pmk agent send`)** | grep `render_order(`, `write_handoff(` over `src/`+`tests/`; read harness.py 575–590, 719–727; dispatcher.py 355–399; cli.py 605–620 |
| 8 | 161 branches; 159 `pmk/*`; 107 `.git/worktrees`; 20 `pmk-merge-*` = 80.1 MB | **Confirmed**: 161 / 159 / 107 / 20 dirs, 84.0 dec = **80.1 MiB**, 19 non-empty, 8 registered in `git worktree list`, 7 of them ≈10.1–10.3 MiB + one 8.7 MiB | `git branch --format=…`; `ls .git/worktrees`; `%TEMP%` glob + walk |
| 9 | 3,109 events; I1 verifies; 146 `TASK_CREATED` = 146 distinct; 138 VOID / 6 DONE / 2 PROPOSED | **Confirmed** — including an independent re-hash of the full chain (genesis `000…0`, `sha256(prev+"\n"+canonical_json(body))` per `events.py:81-84`) | parse 12 `*.jsonl` (excl. `.bak`); re-implement `compute_hash` |
| 10 | 108 REVOKED (58 TTL); 863 FLEET_BLOCKED; 423 OVERSEER_WOKEN; 255 FLEET_ASSIGNED; 192 SENTINEL_RUN; 112 CLAIMED; 104 AGENT_STARTED; 102 INCIDENT | **Confirmed** — all eight counts exact | type counts from parsed log |
| 11 | T-0101: CLAIMED 1736/f54, 1832/f65, 1962/f76; REVOKED 1795/1908/2109 "lease TTL expired"; VOIDED 2213; `src/cna/core/` absent from HEAD and working tree | **Confirmed** exactly (REVOKED payloads carry `new_fence` 62/73/85; next claims take 65/76 — consistent with the fence-bump mechanism). `src/cna/core/`: 0 paths in `git ls-tree -r HEAD`, not on disk | subject-filtered log; `git ls-tree -r HEAD --name-only`; `Test-Path` |
| 12 | Sentinel = 6 findings (I6 ×5: T-0118/119/127/129/130 no bundle ref, stops; I5 T-0139 empty commit, non-stopping) | **Confirmed** — re-derived without running pmk: for each of the 6 DONE tasks, last INTEGRATED payload has `bundle:""` (×5 → I6) / `commit:""` with resolvable bundle (T-0139 → I5) | read `sentinel.py:118-201`; log replay; read `.pm/evidence/EB-T-0139-117/bundle.json` |
| 13 | 18 INTEGRATED; 11 subjects; 9 hash-bearing (all ancestors of main); 9 empty commit; 7 tasks twice | **Confirmed**: 18 / 11 / 9 (all `merge-base --is-ancestor` = true) / 9 / 7. The 9 hashes match F-19's list exactly. Order wording corrected (C9) | INTEGRATED sweep; `git merge-base --is-ancestor` ×9 (+ `2a0f6fa` → **not** an ancestor ✓) |
| 14 | §12 per-tree entries/bytes match disk | **Confirmed** — 22 rows spot-checked incl. largest (T-0102-66, T-0103-91, T-0109-92) and smallest (T-0004-35, T-0006-29): all 22 entries-counts exact, all bytes within 0.05 MiB (MiB reading). The 56-row dirty-name set matches my set exactly | compare §12 rows vs my per-tree census |
| A | T-0139 corpus safe: committed at `1a5ec9b`; status clean; 66/66 vs manifest + checksums; identical to upstream after CRLF→LF | **Confirmed — and strengthened.** status empty; manifest 66/66; checksums 66/66; upstream 66/66 after normalisation (upstream 17,040 CRLF lines, main 0 — matching the report's figure). **The pin chain verifies end-to-end**: `tcanf-clone@75a037f` → staging dir → `1a5ec9b` are blob-identical 66/66, so the LF form in `main` *is* the pin's git-object form. "Identical after normalisation" is a true equivalence, not an explanation of a real difference | `git status --porcelain docs/rules/`; sha256 vs `HEAD:docs/rules/{manifest.json,checksums.sha256}`; normalised byte compare vs cfna export; `git ls-tree -r 1a5ec9b` vs `git -C tcanf-clone ls-tree -r 75a037f` vs staging-dir blob sha1s |
| B | 56 dirty trees hold content that exists nowhere else | **Confirmed in the byte sense, with two nuances.** For all uncommitted paths of `T-0101-54/65/76` and `T-0100-64`: absent from HEAD (`git cat-file -e`), absent from main working tree, no commit on any ref touches the paths (`git log --all -- <path>` empty), and **no commit in the object store contains the exact blobs** (`git log --all --find-object=<sha1>` empty for every file). Nuances: (1) `T-0100-64`'s *paths* exist in main via a different implementation committed by T-0118 (`7c4be9a`); the stranded variants are genuinely different content (coverage.py similarity 0.26; test file 15.8 KB vs 3.7 KB). (2) `T-0101-54`'s 6 files are byte-identical to 6 of `T-0101-65`'s 10 — "19 files across three trees" counts entries; 13 distinct variants | per-path: `Test-Path`, `git cat-file -e HEAD:<p>`, `git log --all -- <p>`, python git-blob-sha1 + `git log --all --find-object=`; cross-tree path and blob comparison; difflib similarity vs main |

---

## 4. Corrections

Severity: **major** = a stated fact about code or history is wrong and a reader would rely on it; **minor** = imprecision that does not change conclusions.

### C1 (major) — `write_handoff()` is called from three places, not one

**Wrong text** (§4.4 item 2): *"`write_handoff()` is called **once**, at `harness.py:586`, inside `_fix_round` — i.e. only when oracles fail *during an active lease*. It is never called from `_give_up` and never called when a lease expires."* Also §10.1 table ("Called: **only** `harness.py:586`") and F-07 ("called only on the oracle-failure path").

**Replacement text:** *"`write_handoff()` has three call sites: `harness.py:586` inside `_fix_round` (oracle failure during an active lease), `dispatcher.py:383` on recovery-ladder step L2 (fresh session in the same worktree — a path `recover.py:13-15` itself documents as 'with a handoff note'), and `cli.py:617` (`pmk agent send`, an operator message). It is never called from `_give_up`, never called when a lease expires, and `order_prompt()` never mentions the file. Measured outcome: 0 of 98 worktrees contain `.pmwork/HANDOFF.md` — so the two in-lease paths never fired in this run, which is itself evidence for §4.2's finding that the dominant failure mode bypasses the recovery ladder entirely."*

Measured basis: grep over `src/`+`tests/` returns exactly three call sites plus the definition; `recover.py:13-15` documents L2's handoff. The empirical claim (0 handoffs; give-up/expiry gap) is confirmed and unchanged.

### C2 (major) — "Not one of those worktrees was ever deleted" / "Nothing in the system ever deletes a worktree" is over-broad, and §9.1's checkout arithmetic is wrong at the edges

**Wrong text** (§1): *"The UMAWS Fleet allocated **98 worker worktrees** … Not one of those worktrees was ever deleted…"*; (F-02): *"Nothing in the system ever deletes a worktree."*; (§9.1): *"95 of 146 cards never produced a checkout at all; those failed at admission or on scope conflict."*; (§4.2): *"...all at fence 3, in `work/T-0003-3`..."*

**Measured basis:** the log records **104 distinct worker worktrees** via `AGENT_STARTED` payloads (plus `T-0004-35`, created but never started). **Seven of those recorded trees are absent from disk**: `T-0001-1`, `T-0001-2`, `T-0003-3`, `T-0005-6`, `T-0005-7`, `T-0005-8`, `T-0006-9`. Two further DONE tasks (`T-0127` fence 97, `T-0129` fence 98) have integration commits (`e7cea34`, `0fc8d0c`) that can only have come from lease worktrees (`work/T-0127-97`, `work/T-0129-98`) which also no longer exist on disk. No code path removes worker worktrees (the only other `git worktree remove` calls are `api.py:1178`, which removes the *context-sync temp* worktree, and `merge.py:282,339`, which remove merge-scratch temps) — so at least nine worker worktrees were removed **out of band**, by something the log does not record. 90 of 146 cards were never claimed; the remaining 5 "missing" tasks (`T-0001`, `T-0003`, `T-0005`, `T-0127`, `T-0129`) *were* claimed and their checkouts are gone.

**Replacement text:** *"The fleet created at least 105 worker worktrees over the run (104 recorded as AGENT_STARTED plus T-0004-35, created but never started). 98 survive. At least nine worker worktrees no longer exist on disk — seven recorded in the log (`T-0001-1/2`, `T-0003-3`, `T-0005-6/7/8`, `T-0006-9`) and two inferred from DONE integrations (`T-0127-97`, `T-0129-98`); no code path removes a worker worktree (`remove_worktree` at `spawn.py:129` has zero call sites; `api.py:1178` and `merge.py` remove only non-worker temp worktrees), so those nine were deleted out of band by an unrecorded actor. 90 of 146 cards were never claimed (admission/scope failures); 5 claimed tasks' checkouts have been removed out of band."* §4.2's reuse proof stands on the log (`AGENT_RESUMED` ×3 at fence 3, profiles pi-orca-deepseek → opencode-strongest → hermes-oneshot, integrated as `6764d54`, confirmed ancestor of `main`) but should not cite the no-longer-existing directory as "live proof". Note: the out-of-band deletions do not weaken the leak finding — they strengthen the governance concern (unrecorded destructive action in a system whose log is supposed to be the source of truth).

### C3 (minor) — §9.2's revocation-reason table does not sum to 108

**Wrong text** (§9.2 last row): *"26 | various single occurrences (dead pid, oracle failure, prompt fix, stale dispatch, doomed work, superseded)"*. The listed rows sum to **118**, not the stated 108.

**Measured basis:** exact reason-string counts: 58 + 16 + 3 + 3 + 2+2+2+2+2+2 + **16 singles** = 108. Every named row is correct; only "26" is wrong.

**Replacement text:** *"16 | various single occurrences (dead pid, oracle failure, prompt fix, stale dispatch, doomed work, superseded)"*.

### C4 (minor) — all disk figures are MiB labelled "MB"

**Wrong text:** every byte figure in §1, §5 (F-01, F-09, F-11), §7.2, §7.3, §7.4, §11, §12, Q-076 (e.g. *"886.2 MB of a 969 MB repository"*, *"80.1 MB"*, *"12.17 MB"*).

**Measured basis:** `work/` = 929.24 ×10⁶ bytes = 886.2 ×2²⁰. Every component of §7.2 reproduces exactly under the MiB reading (`.venv` 43.58, `.pm` 15.48, `.git` 8.26, `.claude` 5.99, `pilot` 4.16, `src` 2.25, `tests` 1.86, `docs` 1.26 MiB; fleet logs 12.16 MiB; overseer log 8.61 MiB; pmk-merge 80.1 MiB), and every §12 row matches within 0.05 MiB. The defect is the unit label, not the numbers.

**Replacement text:** either relabel all figures "MiB", or convert to decimal MB (886.2 MiB → 929.2 MB; 969 → 1,016 MB; 80.1 → 84.0; 514.9 → 539.9; percentages unchanged: 929.2/1,016 = 91.5%). The percentage claims (91.5%, 94.5%, 53.7%) are correct as stated.

### C5 (minor) — the §3 "Loop signature" seq window is wrong

**Wrong text** (§3): *"Between `seq` ~1200 and 3109 the log records `863 FLEET_BLOCKED`, `423 OVERSEER_WOKEN`, …"*

**Measured basis:** the 863 `FLEET_BLOCKED` events span **seq 330–2523**; only 460 of them are ≥1200 and **none** occur after 2523. The quoted counts are log totals, not window totals.

**Replacement text:** *"Across the log (the FLEET_BLOCKED run spans seq 330–2523) the log records 863 FLEET_BLOCKED, 423 OVERSEER_WOKEN (seq 2–3093), 255 FLEET_ASSIGNED and 102 INCIDENT against 112 CLAIMED and 104 AGENT_STARTED."*

### C6 (minor) — the Overseer cadence is overstated ~2–40×

**Wrong text:** §1 *"…a loop that raised the alarm roughly every 60 seconds without changing anything"*; §3 *"The Overseer woke roughly once per minute for five days"*; §9.5 *"423 OVERSEER_WOKEN over roughly five days is approximately one wake per 17 minutes sustained"*.

**Measured basis:** 423 `OVERSEER_WOKEN` span **277.5 hours** (≈11.6 days), mean interval **≈39.5 minutes**. The 17-min figure comes from dividing an assumed 5-day span by 423. The denser signal is `FLEET_BLOCKED`: 863 events over 2.33 days ≈ one per 3.9 minutes. The conclusion (saturated loop, 7.7 blocks per claim) is unaffected.

**Replacement text (§9.5):** *"423 OVERSEER_WOKEN span 11.6 days (mean one per ~39 minutes), with FLEET_BLOCKED bursts averaging one per ~4 minutes over its 2.3-day dense window."*

### C7 (minor) — the `pmk-merge-*` residue is not caused by a missing cleanup path

**Wrong text** (F-09): *"`8a71d36` introduced the temporary merge worktree; it has no cleanup path."* and REC-07: *"Remove `%TEMP%\pmk-merge-*` after a merge completes (try/finally around the merge)…"*

**Measured basis:** `8a71d36`'s own version of `src/fleet/merge.py` already contains `shutil.rmtree(merge_dir, ignore_errors=True)` and `git worktree remove --force` of the temp; at HEAD the cleanup is a `try/finally` (merge.py:336–344). The 20 residual dirs decompose as 7×~10.2 MiB + 1×8.7 MiB (the 8 registered in `git worktree list`; together ≈80.1 MiB — the report's "eight of which hold ~10 MB each" is fair) plus 12 near-empty dirs of 1–4 files (0.0 MiB) — the signature of ignored rmtree errors on locked files and hard process kills, not of an absent cleanup path.

**Replacement text (F-09):** *"`8a71d36` introduced the temporary merge worktree with a `try/finally` cleanup (merge.py:336–344), but the cleanup is not durable: `rmtree(…, ignore_errors=True)` silently fails on locked files and hard kills bypass it. 20 residue dirs remain (84.0 MB dec / 80.1 MiB), 8 of them registered in `git worktree list`."* REC-07 remains valid for sweeping the residue; its "add try/finally" clause should become "harden the existing finally (fail loudly on rmtree errors)".

### C8 (minor) — §12.1(4) mischaracterises T-0131-110, and the "no capture step" claim is very slightly overbroad

**Wrong text** (§12.1 item 4): *"Four trees are corpus duplicates … `T-0097-45/47/49` and `T-0131-110` hold CRLF copies of the corpus; the content is committed at `1a5ec9b` in LF form and verified identical after normalisation. These four can be reclaimed without any capture step…"*

**Measured basis:** `T-0097-45/47/49` are mutually byte-identical CRLF copies (68/68 files) and match `main` 66/68 after normalisation (the 2 exceptions are the regenerated `manifest.json`/`checksums.sha256`). **`T-0131-110` holds LF copies: its 66 corpus documents are byte-identical to `main` (66/68 raw)**, with only its regenerated `manifest.json`/`checksums.sha256` differing. So the no-capture conclusion is *proven* for the 66 corpus documents in all four trees (I re-verified the equivalence independently, §3 row A), but each tree's `manifest.json`/`checksums.sha256` variants are unique (trivially regenerable) bytes.

**Replacement text:** *"`T-0097-45/47/49` hold byte-identical CRLF copies; `T-0131-110` holds LF copies byte-identical to `1a5ec9b`. In all four, the 66 corpus documents are equivalent to `main` (normalised for the T-0097 trio, byte-exact for T-0131-110); only each tree's regenerated `manifest.json`/`checksums.sha256` differ from main's. These four can be reclaimed without capturing the corpus; optionally capture or note the regenerability of the two metadata files per tree."*

### C9 (minor) — F-15's "empty-commit event followed by a hashed one" is reversed for five of the seven tasks

**Wrong text** (F-15): *"**7 tasks record `INTEGRATED` twice** (an empty-commit event followed by a hashed one): T-0004, T-0006, T-0118, T-0119, T-0127, T-0129, T-0130."*

**Measured basis:** true for T-0004 (334→870) and T-0006 (365→1284). For the five DONE tasks the order is **hashed first, empty after**: T-0127 2599→2689, T-0129 2604→2690, T-0130 2675→2694, T-0119 2681→2692, T-0118 2716→2732.

**Replacement text:** *"(an empty-commit event paired with a hashed one — before it for T-0004/T-0006, after it for the five DONE tasks)"*.

### C10 (minor) — R-12 element 3 requires the Executive Summary to be ≤ 3 paragraphs; §1 has 4

Not a numbering deviation of the kind Appendix B declares; either merge paragraphs 3–4 or declare the deviation explicitly in Appendix B.

### C11 (trivial) — small citation/rounding nits

F-01 says "Mean 9.05 MB" while §F.2 and claim 1 say 9.04 (measured 9.043 — F-01 should say 9.04). `api.py:40` for `PMK_ACTOR` resolves at line 41. `dispatcher.py:450` is the `def _restart_on` whose pass-through kwargs sit at 473–474 — the citation is fair but line-imprecise. §10.2's `2a0f6fa` resolves as the tip of `pmk/T-0139-117` (verified with `git branch --points-at`) but bare `rev-parse 2a0f6fa^{commit}` reports ambiguity — worth the full hash in a future revision.

---

## 5. R-12 conformance table

Standard: §8 of `incident-report-worktree-isolation-v3.md` (R-12). I verified the citations the report claims, not just their presence.

| Element | Present? | Adequate? | Note |
|---|---|---|---|
| 1. YAML frontmatter (all named fields) | yes | yes | all required fields present incl. `scope`, `last_modified_date` |
| 2. Provenance block | yes | yes | author, version, source-of-truth precedence stated |
| 3. Executive Summary ≤3 paragraphs | yes | **no** | **4 paragraphs** (C10) |
| 4. Incident Timeline | yes | yes | UTC timestamps + seq; T-0101 rows verified against log to the digit |
| 5. Root Cause Analysis w/ file:line | yes | yes | 6 numbered RCs; **every `file:line` I checked resolves** (spawn.py:89/129, harness.py:19/347/586/719/722/726, order.py:31/43/178, cli.py:350, api.py:426/497, .gitignore:12, sentinel.py:133–166, recover.py:1–42, dispatcher.py:450); C1/C7 correct two behavioural details |
| 6. Findings table w/ status | yes | yes | 21 findings, each with R-12 status; F-16/F-19/F-20 marked resolved |
| 7. Recommendations table w/ status | yes | yes | 13 recs, all honestly `deferred`; effort/impact columns present |
| 8. Current State | yes | yes | §7.1 kernel JSON verified (PAUSED, 0 leases, 1 open queue item, 102 incidents); affected tasks covered via §7.1 + §12 |
| 9. Decision Records w/ full text | yes | yes | Q-072/Q-073/Q-074/Q-075/Q-076 quote-verified against event payloads (seq 3101, 3107, 3108, 3109) |
| 10. Evidence Artifacts | yes | yes | Appendix C gives command-level reproducibility |
| 11. Raw Event Timeline Appendix | yes | yes | Appendix A T-0101 trace matches log exactly |
| 12. Actor Attribution Appendix | yes | yes | §13; the operator-identity disclosure for seq 3107–3109 is explicit |
| 13. Lessons Learned | yes | yes | 11 actionable lessons |
| 14. Commit References | yes | yes | **all 14 hashes in §15 resolve** with the exact subjects claimed; the 9 INTEGRATED hashes are ancestors of `main`; `2a0f6fa` correctly reported not-ancestor |
| Naming convention | yes | yes | `incident-report-<topic>-v<N>.md` in project root |

**Result: R-12 is met** (one paragraph-count deviation, C10). The report's claim to follow R-12 is genuine.

---

## 6. Risks in the recommendations

1. **REC-01/REC-02/REC-03 ordering is safe and unambiguous.** §6.1 puts REC-03 first ("Any action that deletes trees before REC-02 exists converts a storage leak into data loss"), REC-01's own text says "after preserving any uncommitted content", and REC-02 defines the capture. Implementing REC-01 alone is explicitly called out as destructive. No blocking finding.
2. **§12.2's "corpus duplicates need no capture" is proven, not merely asserted** — with the C8 nuance (two regenerable metadata files per tree). Recommend the optional capture noted in C8; not blocking.
3. **REC-07 mis-diagnoses its target** (C7): the try/finally it proposes already exists at merge.py:336–344. As written it would add dead code; the residue sweep itself is safe and recovers the stated bytes.
4. **REC-01 should also name the out-of-band deletion channel** (C2): seven worker trees were already deleted by an unknown actor. A reclaim helper implemented while an unrecorded deletion path is active cannot be audited; the report's own actor-attribution discipline argues for closing that hole first.
5. **Q-075 interaction (§8.4) is correctly flagged**: a 20-minute TTL without REC-01/REC-02 increases fence-bump frequency and therefore the leak rate. The report's warning is sound.
6. Minor: REC-06's suggested 2 GB cap is calibrated to a repo whose `work/` is 0.9 GiB — fine, but state it in the same unit convention as the rest of the report (C4).

---

## 7. Missing findings

1. **The nine vanished worktrees (C2).** A report whose thesis is "nothing ever deletes a worktree" should have reconciled the 104 `AGENT_STARTED` worktree records against the 98 directories and noticed that seven recorded trees — including one it cites (`work/T-0003-3`) — plus two DONE-task integration worktrees are gone. Whoever deleted them did so without a log event; under this repository's own governance precedents that is itself an incident.
2. **The second and third `write_handoff` call sites** (C1), and the fact that `recover.py` *documents* the L2 handoff that evidently never fired — direct corroborating evidence for §4.2's "the dominant failure mode bypasses the ladder" that the report leaves on the table.
3. **The 488-entry figure double-counts identical bytes.** Across the 488 uncommitted entries there are **326 distinct git blobs** (162 redundant copies). The four corpus trees alone contribute 4×68 entries that are largely the same bytes (C8). The report discloses the corpus duplicates but the headline "488 uncommitted file entries" would better read "~326 distinct content units (488 entries)". Likewise T-0101's "19 files across three trees" is 13 distinct variants (T-0101-54 ⊂ T-0101-65 byte-wise; `identifier.py` ≡ `identifiers.py`).
4. **§9.2's table does not sum** (C3) — an arithmetic self-check the report's own F.2 pass should have caught.
5. **§11's b5ccg snapshot has already expired** (see §2 Coverage): `scratch/` 1.6 MiB, `out_gate_*` gone, and the dominant consumer is now a nested `b5ccg/` directory (≈1,593 MiB). The report's own volatility disclosure covers this, but the 61.2% claim should be marked as-of-date or dropped at closure.

---

## 8. Questions the operator must answer before the report is closed

1. **Who deleted the worker worktrees that are gone from disk** — the seven recorded in `AGENT_STARTED` (`T-0001-1/2`, `T-0003-3`, `T-0005-6/7/8`, `T-0006-9`) and the two inferred from DONE integrations (`T-0127-97`, `T-0129-98`) — when, and was their content captured first? This is an unrecorded destructive action and may constitute its own event-log/governance incident (cf. `EVENT_LOG_VIOLATION_REPORT.md`).
2. Do you want the report's figures **relabelled MiB or converted to decimal MB** (C4) before Q-076 is decided? Q-076's own text repeats the "886.2 MB of a 969 MB repository" phrasing.
3. Should the §12 inventory be **regenerated with distinct-blob counts** before any reclamation, so the archive scope is stated in content units rather than entries?
4. For the four corpus-duplicate trees: capture the per-tree `manifest.json`/`checksums.sha256` variants, or accept regenerability and skip capture (C8)?
5. §11's `b5ccg` numbers: re-measure and re-date, or mark the section as a dated snapshot at closure?
6. The five `PROPOSED` cards' stale `agent_hint` (F-21) is confirmed verbatim from the card payloads. Do you want the hints re-rendered now (before any unpause) or only at lease time per REC-13?

---

## 9. Confidence

**High.** Nearly the entire verdict rests on direct measurement, not on reasoning from the document: an independent re-hash of all 3,109 chain events; a two-pass census of all 98 trees including 98×2 `git status -uall` runs; object-store-wide blob searches (`--find-object`) for every uncommitted path in the four focus trees; an end-to-end pin→staging→`1a5ec9b` blob comparison; and a from-source re-derivation of the sentinel output that reproduced all six findings exactly.

The parts of my verdict **not** resting on direct measurement: §9.3's cluster counts (approximation only), the identity of the actor who deleted the seven worktrees (unrecorded anywhere I could read), and §11's `b5ccg` figures (superseded by live drift). None of these is load-bearing for the verdict.

I found no ground for rejection under §5 of my brief: no central factual claim is false (both central claims were attacked and held), no wrong number changes a conclusion, no recommendation is unsafe as written, the severity ratings are proportionate to the evidence, and the report does meet R-12.

---

## 10. Control check

`git status --porcelain` at the end of this assessment returns a **pre-existing dirty tree**, not a clean one: 17 modified tracked files (`.pm/events/*.jsonl` ×9 — the live log is not fully committed, `.pm/views/*` ×3, `HANDOFF.md`, `agents.toml`, `docs/PDD.md`, `docs/free-models.md`, `pi-test.txt`, `pilot/decisions.md`, `pytest_junit.xml`) and ~100 untracked files. **None of these was caused by this assessment.** Filesystem mtimes establish this:

- every modified tracked file was last written 2026-11-02 16:29 – 2026-11-03 10:39 (before the report under review was even authored at 08:02 today);
- `.pm/views/*` were regenerated 2026-11-07 01:32:59 — the report's own F-20 governance step, ~7 hours before this session began (the prompt file was created 08:30:23 today);
- three sibling assessments (`assessment-nemotron-…` 08:43, `assessment-beam-…` 08:52, `assessment-solar-mini4-…` 09:12) were written **during** my session by parallel reviewers, as the operator's notes anticipate; I did not read or write them;
- the only file this assessment created in the repository is `assessment-glm-5.3-flash-incident-report-worktree-lifecycle-leak-v1.md` (mtime 09:27:33, untracked).

Two observations from the same output that independently confirm the report: `work/` and `src/cna/core/` appear nowhere in `git status` (gitignored / nonexistent — the report's RC-5 and F-05), and `docs/rules/` does not appear either (clean — Claim A).

All git commands were read-only plumbing (`ls-tree`, `log`, `show`, `cat-file`, `branch`, `worktree list`, `status`, `merge-base --is-ancestor`, `rev-parse`) executed with `GIT_OPTIONAL_LOCKS=0`; measurement scripts and their JSON outputs were written to the harness temp directory outside the repository. No `pmk` command was run; the test suite was not run; no worktree was pruned; nothing under `work/` was touched.

*Assessment is advisory. It does not change the report, the decision queue, or any worktree. Correction text above is proposed, not applied.*
