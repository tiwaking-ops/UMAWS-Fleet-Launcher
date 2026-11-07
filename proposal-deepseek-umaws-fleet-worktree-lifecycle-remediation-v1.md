---
document:
  title: "Project Proposal: UMAWS Fleet - Worktree Lifecycle Remediation (response to incident-report-worktree-lifecycle-leak-v1 and six independent assessments)"
  status: "Proposal - APPROVED by the human operator 2026-11-07 (see Sign-off, Section 13); advisory in force until the class-K decision Q-076 is decided and code changes are separately authorised; project remains PAUSED"
  version: "1.0.0"
provenance:
  assessor_llm:
    - {name: "Tiwa Pene (Human)", version: "human operator", date: "2026-11-07", role: "assessor", disposition: "APPROVED"}
  author_llm:
    name: "DeepSeek V4.1 Flash"
    version: "deepseek-ai/deepseek-v4.1-flash (provider: nvidia, via OpenCode)"
  assessed_documents:
    - "incident-report-worktree-lifecycle-leak-v1.md (author: DeepSeek V4.1 Flash Free; the document this proposal remediates)"
    - "assessment-nemotron-incident-report-worktree-lifecycle-leak-v1.md"
    - "assessment-beam-incident-report-worktree-lifecycle-leak-v1.md"
    - "assessment-solar-mini4-incident-report-worktree-lifecycle-leak-v1.md"
    - "assessment-glm-5.3-flash-incident-report-worktree-lifecycle-leak-v1.md"
    - "assessment-glyph-cluster-incident-report-worktree-lifecycle-leak-v1.md"
    - "assessment-solar-incident-report-worktree-lifecycle-leak-v1.md"
  independence_disclosure: "The incident report being remediated was written by DeepSeek V4.1 Flash Free (opencode/deepseek-v4.1-flash-free). This proposal is authored by DeepSeek V4.1 Flash (nvidia) - almost certainly the same model at a different provider tier. My measurements in Section 5 are therefore an AUTHOR ADJUDICATION of reviewer findings, NOT an independent assessment. The six assessment LLMs are the independent reviewers. I must not be recorded as an independent assessor of the incident report."
  created_date: "2026-11-07"
  last_modified_date: "2026-11-07"
  last_modified_by_llm: {name: "DeepSeek V4.1 Flash", version: "deepseek-ai/deepseek-v4.1-flash (nvidia)"}
  operator_signoff:
    signed_by: "Tiwa Pene"
    role: "Human operator / project authority"
    date: "2026-11-07"
    document_assessed: "proposal-deepseek-umaws-fleet-worktree-lifecycle-remediation-v1.md"
    version_assessed: "1.0.0"
    disposition: "APPROVED"
    note: "Approves the proposal document. Does not by itself authorise code changes; those remain gated by class-K Q-076 and the operator's answers in Section 10."
audience:
  primary: "The human operator (decision record for Q-076)"
  secondary: "The implementing LLM(s) (executable brief)"
  tertiary: "The six assessing LLMs and any future R-13 reviewer"
source_documents:
  - "incident-report-worktree-lifecycle-leak-v1.md (the incident report; 834 lines, 15 sections, appendices A-F)"
  - "incident-report-worktree-isolation-v3.md (defines R-12 incident-report standard §8 and R-13 review process §9)"
  - "src/fleet/spawn.py (create_worktree:89, remove_worktree:129), harness.py (docstring:19, render_order:347, write_handoff:586, _give_up:719), recover.py (L0-L4), order.py (HANDOFF_FILE:31, write_handoff:178), dispatcher.py (write_handoff:383), merge.py (integrate:110, cleanup:336-344), src/pmk/cli.py (sweep:350, write_handoff:617), src/pmk/sentinel.py (I5/I6), src/pmk/api.py (fence logic:426, context-sync rmtree:998)"
  - ".pm/events/*.jsonl (3,109 authoritative events), .pm/views/queue.md"
  - "The six assessment documents listed under provenance.assessed_documents"
evidence_basis: "Every claim tagged [STATED] (an assessment said it), [READ] (read from repo files/source), [MEASURED] (my own read-only measurement this session), or [INFERRED]. Section 5 records my independent re-measurement of every claim the six assessments disputed. Nothing here was executed against the live system; no code was changed, no worktree was touched, no pmk command was run."
epistemic_status: "Tags: [STATED] asserted by an assessment or the incident report; [READ] read from a file; [MEASURED] measured by direct read-only command; [INFERRED] my reasoning. Where an assessment and my measurement disagree, the measurement is recorded and the assessment is flagged."
authority_statement: "APPROVED by the human operator on 2026-11-07 (see Sign-off, Section 13). The approval accepts this proposal as the remediation plan of record. It does NOT by itself authorise code changes: those remain gated by the class-K decision Q-076 and the operator's answers in Section 10. Class K items (the reclaim policy and any change to lease TTL) still need a two-key decision. This proposal changes no code, no worktree, and no queue item."
---

# Project Proposal: UMAWS Fleet Worktree Lifecycle Remediation

**Response to** `incident-report-worktree-lifecycle-leak-v1.md` **and six independent assessments.**

**Author:** DeepSeek V4.1 Flash (`deepseek-ai/deepseek-v4.1-flash`, provider: nvidia).
**Date:** 2026-11-07. **Repository:** `C:\temp\projects\testproject1` (Kernel-lite; `pmk` CLI + `.pm/` event log; HEAD `9eb39ad`; project `PAUSED`).

---

## 1. Executive Summary

The incident is real and now independently confirmed. **Six independent LLMs reviewed `incident-report-worktree-lifecycle-leak-v1.md`; all six accepted it** - five "ACCEPT WITH CORRECTIONS", one "ACCEPT" - and none refuted either central claim. The core defect stands: worker worktrees are created per lease (`work/<task>-<fence>`) and never reclaimed (`remove_worktree()` at `src/fleet/spawn.py:129` has zero call sites), leaving **98 trees / 886.2 MiB**, of which **56 hold 488 uncommitted entries (514.9 MiB, ~326 distinct content blobs)** belonging to voided tasks. `T-0101` implemented `src/cna/core/` three times and delivered it zero times.

The assessments also **found defects the report itself missed, and errors it made**. The two that matter are new: (a) **at least seven worker worktrees recorded as started no longer exist on disk** (`T-0001-1/2`, `T-0003-3`, `T-0005-6/7/8`, `T-0006-9`), deleted with no log event - so the report's "nothing ever deletes a worktree" is over-broad and, worse, an unrecorded destructive action has occurred in a system whose log is its source of truth; and (b) the report's handoff finding is **code-wrong**: `write_handoff()` has **three** call sites, not one (`harness.py:586`, `dispatcher.py:383`, `cli.py:617`), which I verified directly. Both are correctable without changing the diagnosis, but both must be corrected before the report is closed.

This proposal does four things: it **collates** the six assessments into one adjudicated register (Section 4), **records my own author-side re-measurement** of every disputed claim (Section 5, disclosing that I wrote the report and am therefore not independent), **proposes the exact correction text** for the report (Section 6), and lays out a **phased, capture-before-reclaim remediation plan** with acceptance criteria (Section 7). The single governing constraint is unchanged and unanimous across all six reviewers: **REC-02 (capture) must exist and be verified before REC-01 (reclaim) ships.** Shipping reclaim without capture converts a storage leak into irreversible data loss.

**Nothing in this proposal has been executed.** No code was changed, no worktree was touched, no queue item was written, no `pmk` command was run. The project remains `PAUSED`.

---

## 2. Purpose, Scope and Non-Actions

### 2.1 What was asked

The operator asked for a formal project proposal to **fix the issues created by the incident**, integrating (a) my assessment and (b) the six independent assessments, saved in the repository, with an author field and a reference list of the other LLM assessments.

### 2.2 Scope

| In scope | Out of scope |
|---|---|
| Collating the six assessments into one adjudicated register | Re-running any assessment |
| Independently re-measuring every disputed claim (Section 5) | Changing `src/` or `tests/` code |
| Proposing correction text for the incident report | Applying those corrections (operator decides) |
| A phased remediation plan for the lifecycle leak, stranded work, handoff, churn, traceability | Deleting, moving, archiving or committing any worktree content |
| Governance linkage to Q-076 and the unpause question | Unpausing the project or deciding Q-076 |

### 2.3 Explicit non-actions (all verified true at time of writing)

- No file under `work/` was deleted, renamed, moved, archived or committed.
- No file under `src/` or `tests/` was edited.
- No `pmk` command was run; no event was written; `.pm/events/` and `.pm/views/` are unchanged by this proposal.
- The incident report `incident-report-worktree-lifecycle-leak-v1.md` was **not** modified. All corrections in Section 6 are proposed text only.
- The project remains `PAUSED`.
- This is advisory (candidate tier). It grants no authority and changes nothing.

---

## 3. The Incident in Brief

| # | Defect | Evidence | Status across assessments |
|---|---|---|---|
| I-1 | Worker worktrees are keyed to the lease fence (`work/<task>-<fence>`); every retry allocates a fresh ~9 MiB checkout | `spawn.py:89`; 98 trees / 51 tasks; 22 tasks own 3 | Confirmed by all six |
| I-2 | `remove_worktree()` (`spawn.py:129`) has **zero** call sites - nothing reclaims a worker worktree | `grep` over `src/`,`tests/` | Confirmed by all six (Beam, GLM note it is not the *only* deletion path; see I-9) |
| I-3 | 56 of 98 trees hold **488 uncommitted entries (514.9 MiB)** from voided tasks; ~326 distinct blobs | per-tree `git status -uall`; my blob census | Confirmed by all six; distinct-blob count is GLM's addition, confirmed by me |
| I-4 | `T-0101` implemented `src/cna/core/` three times (fences 54/65/76), merged zero times; absent from HEAD and working tree | seq 1736-2213 | Confirmed by all six |
| I-5 | Handoff channel effectively absent: 0/98 `.pmwork/HANDOFF.md`; `ORDER.md` `## Handoff` always `none`; `order_prompt` never names it | filesystem; `harness.py:347` | Confirmed by all six; **call-site count wrong** (see I-8) |
| I-6 | Churn/loop saturation: 138/146 cards VOID (94.5%); 58/108 revocations = `lease TTL expired`; 863 `FLEET_BLOCKED` + 423 `OVERSEER_WOKEN` against 112 `CLAIMED` | event log | Confirmed by all six |
| I-7 | Traceability: 9 of 18 `INTEGRATED` events carry empty `commit`; `I5`/`I6` iterate DONE tasks only, so 8 of 9 are invisible to the sentinel; `I6` permanently red for 5 DONE tasks | event log; `sentinel.py:133-166` | Confirmed by all six |

Numbers that **every** assessment reproduced to the digit (my re-measurement agreed): 98 trees; 886.2 MiB; 51 tasks (26/3/22); 47 VOID tasks / 93 trees and 4 DONE tasks / 5 trees; 56 dirty / 488 entries / 42 clean; 0 `.pmwork/HANDOFF.md` / 68 `RESULT.md`; 161 branches / 159 `pmk/*` / 107 `.git/worktrees`; 3,109 events with the I1 chain verifying; 146 `TASK_CREATED` = 146 distinct; 138/6/2 states; 108 `REVOKED` (58 TTL); the loop counts; the `T-0101` seq/fence trace. **The central diagnosis is not in dispute.**

---

## 4. Collation of the Six Independent Assessments

### 4.1 Assessment index and verdicts

| # | Assessment file | Assessor LLM | Version / provider | Date | Verdict | Corrections | R-12 |
|---|---|---|---|---|---|---|---|
| A1 | `assessment-nemotron-...md` | nemotron-3.5-super-vl-120b-a12b | nvidia | 2026-11-07 | ACCEPT WITH CORRECTIONS | 5 minor; 0 blocking | MET |
| A2 | `assessment-beam-...md` | Beam | ollama/beam | 2026-11-07 | ACCEPT WITH CORRECTIONS | 1 major (C-1), 4 minor | met |
| A3 | `assessment-solar-mini4-...md` | solar-mini4 | upstage/solar-mini4:free | 2026-11-07 | ACCEPT WITH CORRECTIONS | 3 minor | certified |
| A4 | `assessment-glyph-cluster-...md` | Glyph Cluster | stealth/glyph-cluster (kilo) | 2026-11-07 | **ACCEPT** | 0 | met |
| A5 | `assessment-glm-5.3-flash-...md` | GLM-5.3-Flash | z-ai/glm-5.3-flash (nvidia) | 2026-11-07 | ACCEPT WITH CORRECTIONS | 2 major (C1, C2), 9 minor | met (1 deviation) |
| A6 | `assessment-solar-...md` | Solar | upstage/solar-22b-instruct-0420 | 2026-11-07 | ACCEPT WITH CORRECTIONS | 4 minor; 1 major risk (R-2) | element 3 not adequate |

**Tally: 6/6 ACCEPT-family; 0 REJECT. No reviewer refuted a central claim, a severity rating, the recommendation ordering, or the R-12 conformance (beyond the Executive-Summary paragraph count).**

### 4.2 Consensus findings (all or nearly all six agree)

| C# | Consensus | Raised by | My verdict |
|---|---|---|---|
| CG-1 | The worktree leak is real; `remove_worktree()` is dead code | A1-A6 | **Upheld** |
| CG-2 | Stranded unique work in the 56 dirty trees is real and must be captured before any deletion | A1-A6 | **Upheld** |
| CG-3 | REC-03 -> REC-02 -> REC-01 ordering is correct and must be preserved; REC-01 alone is destructive | A1-A6 | **Upheld** |
| CG-4 | R-12 is met; all 14 elements present and adequate (with one paragraph-count exception) | A1-A6 | **Upheld** |
| CG-5 | Both central claims (corpus not at risk; stranded content unique) survive adversarial testing | A1-A6 | **Upheld** |
| CG-6 | The `b5ccg` section (§11) is a stale single-sample snapshot of a live repo | A1, A2, A5 | **Upheld** |
| CG-7 | Byte figures are MiB mislabelled "MB" (PowerShell `1MB` = 2^20) | A5 (A1 implicitly) | **Upheld (nominal)** |
| CG-8 | Executive Summary is 4 paragraphs; R-12 requires <=3 | A5, A6 | **Upheld** |

### 4.3 Contested findings, adjudicated (see Section 5 for measurements)

| X# | Contested item | Positions | My adjudication |
|---|---|---|---|
| X-1 | **`write_handoff()` call-site count** | A2, A5: **three** sites (`harness.py:586`, `dispatcher.py:383`, `cli.py:617`) - MAJOR. A1, A3, A4, A6: "once" (agreeing with the report) | **A2/A5 are right; the report is wrong.** Verified 3 sites + definition. See C-1. |
| X-2 | **"Nothing ever deletes a worktree"** | A5: over-broad; >=7 recorded worktrees are gone from disk; MAJOR. Others did not reconcile `AGENT_STARTED` vs disk | **A5 is right.** Verified 7 missing. See C-2 and X-9. |
| X-3 | **`%TEMP%\pmk-merge-*` "no cleanup path"** | A5: wrong - `try/finally` cleanup exists (`merge.py:336-344`). A6: attribution may drift | **A5 is right.** Verified at HEAD and at `8a71d36`. See C-7. |
| X-4 | **§9.2 revocation table does not sum** | A5: last row should be **16** not 26; printed rows sum 118 vs stated 108 | **A5 is right.** Verified 16 singles. See C-3. |
| X-5 | **`INTEGRATED` "7 tasks twice" list** | A3: report lists `T-0005` (8 rows) - should be `T-0006`. A5: list correct, ordering (C9) wrong | **Report's current text is correct** (`T-0004, T-0006, ...`). A3's C-1 does not match the current draft (earlier draft or misquote); A5's ordering nit stands. |
| X-6 | **`%TEMP%` directory count** | A1/A5: 20 dirs, 19 non-empty. A3: "8 registered" (conflates the git registry with `%TEMP%` dirs) | **Both true, different objects.** 20 `%TEMP%` dirs; 8 registered in `git worktree list`. No defect. |
| X-7 | **`work/T-0003-3` cited as live proof** | A5: the tree no longer exists | **A5 is right.** Verified absent. See C-2. |
| X-8 | **T-0131-110 corpus line endings** | A5: LF, byte-identical to `1a5ec9b`; the CRLF trio is only `T-0097-45/47/49` | **A5 is right.** Verified: `T-0131-110` CRLF=0; `T-0097-45` CRLF=178. See C-8. |
| X-9 | **7 worktrees vanished with no log event** | A5 (C2, missing-finding #1): an unrecorded destructive action; possibly its own incident | **Upheld and material.** See X-9 remediation in Section 7. |

### 4.4 What each assessment added beyond the report

- **A1 (nemotron):** quantify distinct vs total files in the 488 entries; spot-check `%TEMP%` residue for duplicates; separate `__pycache__`/scratch from author-written source in the inventory.
- **A2 (Beam):** the `work/context-sync` directory *is* reclaimed by `api.py:998` - `pmk worktree list` (REC-04) must not flag it; all three `write_handoff` sites.
- **A3 (solar-mini4):** re-run the corpus equivalence check at close-out (upstream is live and can drift); note `src/cna/` (engine/tools) *is* committed - only `src/cna/core/` is absent.
- **A4 (glyph-cluster):** no corrections; a clean acceptance.
- **A5 (GLM-5.3-Flash):** the deepest review. Contributed the vanished-worktree finding, the merge-cleanup correction, the distinct-blob count (326), the `%TEMP%` cleanup correction, the Ki/`b5ccg` expiry, the paragraph-count deviation, and 9 minor text corrections. Also independently re-hashed the entire I1 chain and re-derived the sentinel output.
- **A6 (Solar):** the REC-06 archive schema gap is a **major** risk (see RG-1): no format/command/location/event specified means "capture before delete" is an unimplemented promise; the `pmk worktree prune` operator path should be kept as a living option; `%TEMP%` reclamation should be in the same window.

---

## 5. My Author-Side Re-Measurement of the Disputed Claims

**Disclosure.** I wrote the incident report (as DeepSeek V4.1 Flash Free). This section is an **author adjudication**, not an independent review. It exists so that the corrections in Section 6 rest on measurement, not on majority vote. Every command below was read-only; nothing under `work/` was touched.

| Item | Claim under test | Method | Result | Effect |
|---|---|---|---|---|
| X-1 | `write_handoff` call sites | `Select-String write_handoff(` over `src/`,`tests/` | **3 call sites**: `dispatcher.py:383`, `harness.py:586`, `cli.py:617` (+ def `order.py:178`) | Report's "once" is **wrong** -> C-1 (major) |
| — | `render_order` call sites | same | 1 (`harness.py:347`) | report correct |
| — | `remove_worktree` call sites | same | 1 hit = definition (`spawn.py:129`) | report correct |
| X-2, X-9 | Worktrees recorded started vs on disk | `AGENT_STARTED.payload.worktree` vs `Test-Path` | **104 distinct started; 7 absent** (`T-0001-1`,`T-0001-2`,`T-0003-3`,`T-0005-6`,`T-0005-7`,`T-0005-8`,`T-0006-9`). `T-0127-97`,`T-0129-98` also absent (no `AGENT_STARTED` found; integrations `e7cea34`,`0fc8d0c` exist). `T-0004-35` on disk but never started | Report's absolutes **over-broad**; new finding stands -> C-2 |
| X-3 | Merge-scratch cleanup | read `merge.py` at HEAD and at `8a71d36` | `try/finally` + `rmtree(..., ignore_errors=True)` present at both (`merge.py:336-344`) | F-09/REC-07 **misdiagnosed** -> C-7 |
| X-4 | §9.2 reason table sum | group `REVOKED.payload.reason` | singles = **16**; 58+16+3+3+(2x6)+16 = **108**; printed row "26" makes 118 | **wrong** -> C-3 |
| X-5 | `INTEGRATED` twice | group `INTEGRATED.subject` | 2x: `T-0004`,`T-0006`,`T-0118`,`T-0119`,`T-0127`,`T-0129`,`T-0130`; 1x: `T-0003`,`T-0005`,`T-0026`,`T-0139` | current report text **correct**; A3's C-1 not reproducible |
| — | Distinct content among 488 entries | `git hash-object` per entry | **326 distinct blobs** (162 redundant) | strengthens archive scoping -> C-12 |
| X-8 | T-0131-110 line endings | byte scan of first `.adoc` | `T-0131-110` **CRLF=0 (LF)**; `T-0097-45` **CRLF=178** | §12.1(4) mischaracterises -> C-8 |
| X-6 | `%TEMP%` dirs vs registry | `%TEMP%` glob; `.git/worktrees` | 20 dirs, 19 non-empty; 8 registered | no defect |
| CG-8 | Executive Summary length | line count | 4 paragraphs | -> C-10 |
| — | FLEET_BLOCKED seq window | min/max seq | **330-2523** (none after 2523) | §3/§9.5 window wrong -> C-5 |
| CG-7 | Unit label | PowerShell `1MB` = 2^20 | figures are **MiB** | -> C-4 |
| CG-6 | `b5ccg` drift | re-measure | now 2,463.7 MiB top level; `out_gate_*` = **0** dirs at top level; `b5ccg\scratch` still 1,230.1 MiB | §11 is a dated snapshot -> C-15 |
| — | Root `HANDOFF.md` size | filesystem | report says 4,692 B; A2 measured 6,088 B now (content moved) | -> C-16 (trivial) |

**Adjudication summary.** Of the six assessments: **A2 and A5 are correct on every contested item they raised**; A3's one substantive correction (`T-0005`) is not reproducible against the current text; A1, A4, A6 raised no contested item that survives measurement beyond the paragraph count and the shared snapshot/unit caveats. No contested item changes a conclusion, a severity rating, or makes a recommendation unsafe. Two are nonetheless **major** because they are stated code/history facts a reader would rely on (X-1, X-2/X-9).

---

## 6. Proposed Corrections to the Incident Report

These are **proposed only**. Not applied. Operator decides whether the report is patched (recommended) or left as a v1 draft with this proposal as its errata. Severity: **major** = stated fact wrong and load-bearing; **minor** = imprecision; **trivial** = cosmetic.

| ID | Loc | Severity | Wrong text (abridged) | Proposed replacement |
|---|---|---|---|---|
| C-1 | §1, §4.4-2, F-07, §10.1, F.2 | **major** | "`write_handoff()` is called **once**, at `harness.py:586`" | "`write_handoff()` has **three** call sites: `harness.py:586` (`_fix_round`, oracle failure), `dispatcher.py:383` (recovery step L2), and `cli.py:617` (`pmk agent send`). None is on the give-up or TTL-expiry path, and `order_prompt()` never names the file - which is why the measured outcome is still 0 of 98." |
| C-2 | §1, F-02, F-03, §4.2 | **major** | "Not one of those worktrees was ever deleted"; "Nothing in the system ever deletes a worktree"; `work/T-0003-3` as live reuse proof | "The fleet created **105** worker worktrees (104 recorded in `AGENT_STARTED` plus `T-0004-35`, created but never started). **98 survive.** **At least seven recorded worktrees are gone from disk** (`T-0001-1/2`, `T-0003-3`, `T-0005-6/7/8`, `T-0006-9`), plus `T-0127-97`/`T-0129-98` inferred from DONE integrations; no code path removes a worker worktree, so those were deleted **out of band**. Reuse within a fence is proven by the log (`AGENT_RESUMED` x3 at fence 3, integrated as `6764d54`, an ancestor of `main`) - not by the now-absent `work/T-0003-3` directory." |
| C-3 | §9.2 | minor | last row `26` | `16` (58+16+3+3+2x6+16 = 108) |
| C-4 | throughout | minor | "MB" for `1MB`-derived figures | relabel **MiB**, or convert to decimal MB (886.2 MiB = 929.2 MB; 514.9 = 539.9; 80.1 = 84.0; 969 -> 1,016). Percentages unchanged. |
| C-5 | §3, §9.5 | minor | "Between `seq` ~1200 and 3109 ... 863 `FLEET_BLOCKED`" | "Across the log (the `FLEET_BLOCKED` run spans `seq` 330-2523) ... 863 `FLEET_BLOCKED`, 423 `OVERSEER_WOKEN` (seq 2-3093) ..." |
| C-6 | §1, §3, §9.5 | minor | "woke roughly once per minute for five days" / "one wake per 17 minutes" | "423 `OVERSEER_WOKEN` span ~11.6 days (mean ~39 min); the denser signal is `FLEET_BLOCKED`, 863 events over ~2.3 days (~one per 4 min)." |
| C-7 | F-09, REC-07 | minor | "`8a71d36` ... has no cleanup path"; "try/finally around the merge" | "`8a71d36` introduced a `try/finally` cleanup (`merge.py:336-344`), but `rmtree(..., ignore_errors=True)` silently fails on locked files and hard kills bypass it. 20 residue dirs remain (80.1 MiB), 8 registered. REC-07 should **harden the existing finally (fail loudly)**, not add one." |
| C-8 | §12.1(4) | minor | "`T-0097-45/47/49` and `T-0131-110` hold CRLF copies" | "`T-0097-45/47/49` hold byte-identical CRLF copies; **`T-0131-110` holds LF copies byte-identical to `1a5ec9b`**. In all four the 66 documents are equivalent to `main`; only each tree's regenerated `manifest.json`/`checksums.sha256` differ." |
| C-9 | F-15 | minor | "(an empty-commit event followed by a hashed one)" | "(a paired empty/hashed pair - empty first for `T-0004`/`T-0006`, hashed first for the five DONE tasks)" |
| C-10 | §1 | minor | Executive Summary = 4 paragraphs | merge to <=3, **or** declare the deviation in Appendix B |
| C-11 | F-01, §13, misc | trivial | "Mean 9.05 MB"; `api.py:40`; `dispatcher.py:450`; bare `2a0f6fa` | 9.04; `api.py:41`; `dispatcher.py:473-474`; full hash of the `pmk/T-0139-117` tip |
| C-12 | §12, §12.1 | minor | "488 uncommitted file entries" | "488 uncommitted entries = **326 distinct content blobs** (162 redundant copies; the corpus trio alone overlaps heavily)" |
| C-13 | §12.2 | minor | 42 clean trees "provably empty" | "42 clean trees = free of uncommitted entries; each still holds an ~8.7 MiB base checkout" |
| C-14 | §7.2 | minor | "Real project data ~= 12 MB" | mark as approximate/illustrative (the 900:1 ratio is illustrative, not derived) |
| C-15 | §11 | minor | `b5ccg` figures as current | mark §11 explicitly as a **dated snapshot**; re-measure at close-out (see Section 5) |
| C-16 | §10.1, §4.4-3 | trivial | root `HANDOFF.md` "4,692 bytes" | re-measure (6,088 B at last check) |

**Recommended:** apply C-1 and C-2 (major, load-bearing) at minimum, and C-3/C-4/C-7/C-8/C-12 with them; the rest are cosmetic. If corrections are applied, the report version becomes `...-v1.1.md` and Appendix F.1's reviewer checklist is completed against it - which would finally close R-13, since six independent reviews now exist (Section 8.3).

---

## 7. Remediation Plan

The plan fixes the incident's issues and folds in every assessment's additions. Phases are ordered; **each phase gates the next**. The governing rule, unanimous across all six reviewers, is in Phase 1.

### Phase 0 - Governance and containment (do nothing destructive yet)

| Step | Action | Owner | Gate |
|---|---|---|---|
| 0.1 | Operator decides **Q-076** (class K). Safe default remains "document only". | Operator | Two-key |
| 0.2 | **Open a fact-finding item on the vanished worktrees (X-9/C-2):** seven recorded worker trees are gone with no log event, and `work/T-0003-3` (cited as live proof) is among them. Determine who/when; whether content was captured first. Under this repo's own precedents (`EVENT_LOG_VIOLATION_REPORT.md`) an unrecorded destructive action is itself an incident. | Operator + agent | Before any reclaim |
| 0.3 | Decide the **unpause condition** (Appendix E.5): resume only after Phase 1-2 land, or documentation-only for a period. Note: a 20-minute TTL (Q-075) **without** REC-01/02 increases fence-bump frequency and therefore the leak rate. | Operator | Before unpause |
| 0.4 | Decide **REC-01 placement** (harness `_give_up` vs Kernel `revoke` vs dispatcher reaper) and the **archive target** (branch vs patch dir vs external). | Operator | Before Phase 1 |

### Phase 1 - Capture (REC-03 + REC-02). **Capture before reclaim. Non-negotiable.**

| Step | Action | Notes from assessments |
|---|---|---|
| 1.1 | Define the **archive schema explicitly** (A6 R-2, major): format, command, location **outside `work/`**, retention, and whether the archive itself is logged as an event. | Without this, "capture before delete" is an unimplemented promise |
| 1.2 | For **each of the 56 dirty trees**: `git diff --binary` + untracked-file archive + `.pmwork/RESULT.md`, keyed `stranded/<task>/<fence>/`. | A2: patch archives may not suffice for the valuable variants - `T-0101`'s three `src/cna/core/` implementations may warrant full tree snapshots |
| 1.3 | Scope the archive in **content units**: 326 distinct blobs, not 488 entries (C-12). | A5 |
| 1.4 | **Verify** each archive is readable, non-empty, and re-hydrates to the same blob set. Record size + file count per archive. | All six |
| 1.5 | **Do not delete anything in this phase.** | All six |

### Phase 2 - Reclaim (REC-01), only after Phase 1 is verified

| Step | Action | Notes |
|---|---|---|
| 2.1 | Remove the **42 clean trees** first (~371.3 MiB) - free of uncommitted content. | A6 asks whether to demo on these; recommend yes, as a low-risk proof |
| 2.2 | Then the **4 corpus-duplicate trees** (`T-0097-45/47/49`, `T-0131-110`, ~38.1 MiB) - **after** re-running the equivalence check (upstream is live and can drift, A3) and capturing each tree's regenerated `manifest.json`/`checksums.sha256` (C-8; A5). | A2/A3/A5 |
| 2.3 | Then the remaining **52 dirty trees** (~476.8 MiB), one by one, **only** once its Phase-1 archive is verified. | REC-03 |
| 2.4 | Implement **REC-01**: one shared helper `_revoke_and_reclaim` called from every fence bump (harness give-up, TTL reaper, operator revoke), reclaiming **after** the Phase-1 capture. | A5: reconcile with the 3 existing `write_handoff` sites and name the out-of-band deletion channel (X-9) - implementing reclaim while an unrecorded deletion path is active cannot be audited |
| 2.5 | `work/context-sync` must **not** be flagged: it is already reclaimed by `api.py:998`. | A2 |

### Phase 3 - Observability (REC-06, REC-04)

| Step | Action |
|---|---|
| 3.1 | Report `work/` tree count + total bytes in `pmk status`; add non-stopping invariant **`I17`** (cap + age), and **state the action on breach** (A1 risk #4: a dashboard is not a control). |
| 3.2 | Implement **`pmk worktree`** subcommand: `list` (task, fence, state, dirty, bytes, age), `prune --dry-run` (default), `prune --void-older-than`, `prune --keep-unmerged --archive`. Define "unmerged" programmatically (no commit, no branch, dirty) before coding. Keep this operator path even if auto-reclaim lands (A6). |

### Phase 4 - Handoff wiring (REC-05), corrected

| Step | Action |
|---|---|
| 4.1 | Wire the handoff end-to-end, **accounting for the three existing call sites** (C-1): add `write_handoff()` to the give-up/expiry path, re-render `ORDER.md` on tree reuse, and add an explicit "read `.pmwork/HANDOFF.md` first" line to `order_prompt()`. |
| 4.2 | Prompt-regression test: a reused tree's second agent demonstrably reads the handoff (style of R-03 in the v3 report). |

### Phase 5 - Traceability (REC-09, REC-11)

| Step | Action |
|---|---|
| 5.1 | **REC-09:** decide whether the five missing `I6` bundle references are a recording defect (backfill) or a process defect (integration without a bundle) - Appendix E.4 - then backfill or downgrade with a recorded decision. |
| 5.2 | **REC-11:** record `1a5ec9b` against `T-0139` (or a `SUPERSEDED_BY` event linking `pmk/T-0139-117` -> `1a5ec9b`) to clear `I5`/empty-commit. |
| 5.3 | Broaden `I5`/`I6` beyond DONE tasks so the other 8 empty-commit `INTEGRATED` events are visible (F-15). |

### Phase 6 - Churn reduction (REC-10)

| Step | Action |
|---|---|
| 6.1 | Require an explicit `reissue-reason` and attach the predecessor's handoff before re-creating a card for a previously-voided scope; cap same-scope reissue at 2 without a queue decision. |
| 6.2 | Address the root loss mode: 58/108 revocations are TTL expiry - preserving partial work across a timeout addresses more than half of all loss. |

### Phase 7 - Hygiene and prevention (REC-07, REC-08, REC-12, REC-13)

| Step | Action |
|---|---|
| 7.1 | **REC-07 (corrected):** sweep `%TEMP%\pmk-merge-*` and `git worktree prune` stale registry entries; **harden** the existing `finally` rather than adding one (C-7). Bundle this with the same remediation window (A6). |
| 7.2 | **REC-08:** cap/rotate fleet logs (12.17 MiB `.pm/fleet/logs`; one 8.61 MiB overseer log). |
| 7.3 | **REC-12:** retire the "corpus at risk" claim from all briefings. |
| 7.4 | **REC-13:** revalidate `agent_hint` at lease time (store the base commit; refuse to lease if HEAD moved and the hint names now-committed artefacts). F-21 is the task-card analogue of RC-4. |
| 7.5 | **New (A1/A3):** add a periodic "dead public function" check (would have caught `remove_worktree`); separate scratch/`__pycache__` from author-written source in future inventories. |

### Phase 8 - Close the report (optional, operator decides)

| Step | Action |
|---|---|
| 8.1 | Apply the Section 6 corrections; bump the report to `v1.1`. |
| 8.2 | Complete R-13: the report now has **six** independent reviews (Section 8.3). Record the reviewer, close Appendix F.1. |
| 8.3 | Reconcile corrections; if two reviewers disagree on a correction, record the disagreement rather than averaging it. |

### 7.9 Acceptance criteria (from the report §6.2, unchanged and unanimous)

- A lease revoked by TTL expiry leaves **no** `work/<task>-<fence>` directory, and any content it held is retrievable from the archive by task and fence.
- Same outcome for `_give_up()`.
- A tree with uncommitted content is **never** deleted without an archive artefact whose size and file count are recorded in the log.
- `pmk worktree list` reports task, fence, state, dirty flag, bytes, age for every tree (but not `work/context-sync`).
- `order_prompt()` names `HANDOFF.md`; a reused tree's second agent reads it (regression test).
- Regression test: run a task, expire its lease, re-claim; assert the new tree exists **and** the old tree is gone **and** archived.

---

## 8. Governance and Decision Requirements

### 8.1 Open queue item

**Q-076** (open, class K, recorded by the incident report) authorises the worktree-lifecycle remediation. This proposal is the remediation **plan** for that decision; it does not itself decide it. Options remain: implement reclaim-at-fence-bump / document-only (current) / re-scope to `pmk worktree prune` only / stop.

### 8.2 Class K items

The reclaim policy, the archive retention policy, and any change to lease TTL are class K (two-key). Per D-3 in `pilot/decisions.md`, TTL is already restored to 20 minutes; a shorter TTL **worsens** the leak without REC-01/02.

### 8.3 R-13 status - now satisfiable

The report's Appendix F recorded R-13 as blocked (three reviewer agents failed on infrastructure). That is no longer true: **six independent LLM assessments now exist**, none by the report's author, five accepting with corrections and one accepting outright. The report can be closed under R-13 by recording these six as the independent review, **provided** the major corrections (C-1, C-2) are applied first and the reviewer checklist in F.1 is completed against the corrected text.

### 8.4 Provenance and independence (disclosed)

The report's author (DeepSeek V4.1 Flash Free) and this proposal's author (DeepSeek V4.1 Flash, nvidia) are almost certainly the same model at different provider tiers. My Section 5 measurements are therefore an **author adjudication**. I am **not** an independent assessor of the incident report and must not be recorded as one. The six assessment LLMs are the independent reviewers.

---

## 9. Risk Register

| ID | Risk | Severity | Mitigation (phase) |
|---|---|---|---|
| RG-1 | **Archive schema undefined** makes "capture before delete" an unimplemented promise (A6) | major | Specify format/command/location/event before Phase 1 (0.4, 1.1) |
| RG-2 | **REC-01 shipped before REC-02** deletes 488 entries / 326 blobs forever | blocking | Ordering gate; Phase 2 refuses to run without verified Phase 1 archives |
| RG-3 | **Unrecorded deletion path active** (X-9): reclaim cannot be audited while trees vanish silently | major | Fact-find (0.2) before Phase 2; reconcile in 2.4 |
| RG-4 | Patch archives miss full-tree value for `T-0101` variants | moderate | Full snapshot for the `src/cna/core/` trees (1.2) |
| RG-5 | Corpus equivalence trusted on a **live** upstream that can drift | low | Re-run equivalence at close-out (2.2) |
| RG-6 | `I17`/`pmk status` added as dashboards with no action | low | Define breach action (3.1) |
| RG-7 | `pmk worktree list` flags `work/context-sync` | low | Exclude it (2.5) |
| RG-8 | Corrections applied only in this proposal, not the report -> two truths | low | Phase 8 or explicit operator choice to leave v1 + errata |

---

## 10. Open Questions for the Operator

Carried from the report's Appendix E and extended by the assessments:

1. **Q-076** - authorise the reclaim-at-fence-bump fix now, or keep document-only? (Section 8.1)
2. **Vanished worktrees (X-9)** - who deleted the seven (plus two inferred) worker trees, when, and was content captured first? Is this its own incident? (0.2)
3. **Archive target + schema** - branch per task, patch dir, or external; and the exact format/command/location/event (0.4, 1.1, RG-1).
4. **Retention** - is captured stranded work wanted after capture, and for how long?
5. **REC-01 placement** - harness, Kernel `revoke`, or dispatcher reaper?
6. **Unpause condition** - resume only after Phases 1-2, or documentation-only for a period? (0.3)
7. **The 42 clean trees** - delete immediately as a low-risk demonstration (recommended), or one atomic cleanup?
8. **REC-09 `I6`** - recording defect (backfill) or process defect (downgrade)?
9. **Four corpus trees** - reclaim without capture contingent on re-running equivalence + capturing regenerable metadata? (2.2)
10. **`b5ccg`** - same capture-then-reclaim treatment, or out of scope? (Its `scratch/` is still 1,230.1 MiB; `out_gate_*` has moved.)
11. **Report corrections** - apply Section 6 now (report -> v1.1, enables R-13 closure) or leave v1 with this proposal as errata?
12. **R-13** - accept the six assessments as the independent review and close Appendix F.1?

---

## 11. Reference List - Other LLM Assessments

These are the independent assessments collated in Section 4. All are advisory; none changes repository state. Stored unmodified in the project root with their own provenance blocks intact.

1. **nemotron-3.5-super-vl-120b-a12b** (nvidia). `assessment-nemotron-incident-report-worktree-lifecycle-leak-v1.md`. 2026-11-07. Verdict: ACCEPT WITH CORRECTIONS (5 minor, 0 blocking); R-12 MET.
2. **Beam** (ollama/beam). `assessment-beam-incident-report-worktree-lifecycle-leak-v1.md`. 2026-11-07. Verdict: ACCEPT WITH CORRECTIONS (1 major: `write_handoff` has 3 call sites; 4 minor); R-12 met.
3. **solar-mini4** (upstage/solar-mini4:free). `assessment-solar-mini4-incident-report-worktree-lifecycle-leak-v1.md`. 2026-11-07. Verdict: ACCEPT WITH CORRECTIONS (3 minor); R-12 certified. Note: its C-1 (`T-0005`) is not reproducible against the current report text (X-5).
4. **Glyph Cluster** (stealth/glyph-cluster, kilo). `assessment-glyph-cluster-incident-report-worktree-lifecycle-leak-v1.md`. 2026-11-07. Verdict: **ACCEPT** (0 corrections); R-12 met.
5. **GLM-5.3-Flash** (z-ai/glm-5.3-flash, nvidia). `assessment-glm-5.3-flash-incident-report-worktree-lifecycle-leak-v1.md`. 2026-11-07. Verdict: ACCEPT WITH CORRECTIONS (2 major: `write_handoff` call sites, "never deletes" over-broad + vanished worktrees; 9 minor); R-12 met with 1 deviation (Executive Summary paragraph count). The deepest review; source of the vanished-worktree finding, the merge-cleanup correction, the 326-blob census, and the `%TEMP%` cleanup correction.
6. **Solar** (upstage/solar-22b-instruct-0420). `assessment-solar-incident-report-worktree-lifecycle-leak-v1.md`. 2026-11-07. Verdict: ACCEPT WITH CORRECTIONS (4 minor; 1 major risk: REC-06 archive schema unspecified); R-12 element 3 not adequate.

**Document under review (not counted as an independent assessment - author = DeepSeek V4.1 Flash Free):**
- `incident-report-worktree-lifecycle-leak-v1.md` (2026-11-07, 834 lines, 15 sections + appendices A-F).

**Supporting project documents:**
- `incident-report-worktree-isolation-v3.md` - defines the R-12 standard (§8) and R-13 review process (§9).
- `prompt-assess-incident-report-worktree-lifecycle-leak-v1.md` - the repository-access assessment prompt issued to the six assessors.
- `EVENT_LOG_VIOLATION_REPORT.md` - precedent for treating an unrecorded state change as its own incident (relevant to X-9).

---

## 12. Appendices

### Appendix A - Numbers every assessment reproduced (and I re-measured)

98 trees | 886.2 MiB | min 8.7 / max 10.3 / mean 9.04 MiB | 51 tasks (26x1, 3x2, 22x3) | 47 VOID tasks / 93 trees; 4 DONE tasks / 5 trees | 56 dirty / 488 entries / 514.9 MiB / 42 clean | 0 `.pmwork/HANDOFF.md` / 68 `RESULT.md` | 161 branches / 159 `pmk/*` / 107 `.git/worktrees` | 3,109 events, I1 chain verifies | 146 `TASK_CREATED` = 146 distinct | 138 VOID / 6 DONE / 2 PROPOSED | 108 `REVOKED` (58 TTL) | 863 `FLEET_BLOCKED` / 423 `OVERSEER_WOKEN` / 255 `FLEET_ASSIGNED` / 192 `SENTINEL_RUN` / 112 `CLAIMED` / 104 `AGENT_STARTED` / 102 `INCIDENT` | `T-0101` seq 1736/1795/1832/1908/1962/2109/2213.

### Appendix B - New facts established by the assessments (verified by me)

- `write_handoff()` has **3** call sites, not 1 (X-1). [MEASURED]
- **7** recorded worker worktrees are absent from disk (X-2/X-9). [MEASURED]
- `merge.py` has had `try/finally` cleanup since `8a71d36` (X-3). [READ]
- §9.2's last row is **16**, not 26 (X-4). [MEASURED]
- The 488 entries are **326 distinct blobs** (C-12). [MEASURED]
- `T-0131-110` holds **LF**, not CRLF (X-8). [MEASURED]
- `FLEET_BLOCKED` spans seq **330-2523** (C-5). [MEASURED]
- Executive Summary is **4** paragraphs (CG-8). [MEASURED]

### Appendix C - Epistemic tags used

[STATED] an assessment or the report said it; [READ] read from a file; [MEASURED] measured by read-only command this session; [INFERRED] my reasoning. Corrections in Section 6 are proposed, not applied.

---

## 13. Sign-off and Operator Approval

### 13.1 Assessor

| Field | Value |
|---|---|
| Assessor | **Tiwa Pene (Human)** |
| Role | Human operator / project authority |
| Date | 2026-11-07 |
| Document assessed | `proposal-deepseek-umaws-fleet-worktree-lifecycle-remediation-v1.md` |
| Version assessed | 1.0.0 |
| Disposition | **APPROVED** |

### 13.2 Signature

> **APPROVED.**
>
> Signed: **Tiwa Pene** (Human operator)
> Date: **2026-11-07**
> On: `proposal-deepseek-umaws-fleet-worktree-lifecycle-remediation-v1.md` v1.0.0
> Disposition: accept this proposal as the remediation plan of record.

### 13.3 Scope and effect of this approval

- This signature approves **the proposal document** - the collation of the six assessments (Section 4), the author adjudication of the disputed claims (Section 5), the proposed correction set for the incident report (Section 6), and the phased remediation plan (Section 7).
- The operator is recorded as the **assessor** (`provenance.assessor_llm`). The author is DeepSeek V4.1 Flash; the assessor is a human and not the author, so the "author is never their own assessor" rule is satisfied and this review is independent of the author.
- **It does not by itself authorise code changes.** Remediation remains gated by the class-K decision **Q-076** (Section 8.1) and by the operator's answers to the open questions in Section 10. No file under `src/`, `tests/`, or `work/` changes until that authorisation is separately given.
- Applying the Section 6 corrections to `incident-report-worktree-lifecycle-leak-v1.md` (Phase 8) is likewise an operator decision, not implied by this approval.
- The project remains `PAUSED`.

---

*End of proposal. This document is operator-approved (Section 13) but remains advisory in force: it changed no code, touched no worktree, wrote no event, and modified no other document. The project remains `PAUSED`. The author of this proposal is almost certainly the same model that authored the incident report under review, so the measurements in Section 5 are an author adjudication, not an independent assessment; the six assessment LLMs listed in Section 11 are the independent reviewers, and the human operator (Section 13) is the assessor of this proposal.*
