# Assessment Prompt — `incident-report-worktree-lifecycle-leak-v1.md`

**Purpose:** hand this to an independent LLM to adversarially assess the incident report.
**Prerequisite:** the reviewer has read access to `C:\temp\projects\testproject1`.
**Expected output:** an assessment document, in the format given in section 7.

---

## THE PROMPT (copy everything between the markers)

<!-- BEGIN PROMPT -->

You are an **independent assessment LLM**. You did **not** write the document you are about to review and you have no stake in its conclusions. Your job is to establish whether it is **correct**, not whether it is persuasive. You are expected to disagree wherever the evidence does not support it.

You have read access to the repository, so **measuring is mandatory, not optional**. A claim you could have measured and did not is a claim you did not verify.

### 1. Your task

Independently assess this document:

```
C:\temp\projects\testproject1\incident-report-worktree-lifecycle-leak-v1.md
```

The repository is `C:\temp\projects\testproject1`, a "Kernel-lite" multi-agent coordination system: a `pmk` CLI over an append-only event log in `.pm/`, which dispatches worker agents into git worktrees under `work/`. The report alleges a worktree-lifecycle defect — worker worktrees are created per lease and never deleted, 56 of them hold uncommitted work that will never be merged, and the task cards that produced them were 94.5% voided.

The report claims to follow the repository's own **Incident-Report Standard (R-12)** and to be subject to its **Independent Review Process (R-13)**, both defined in:

```
C:\temp\projects\testproject1\incident-report-worktree-isolation-v3.md   (§8 = R-12, §9 = R-13)
```

Read that standard before assessing conformance to it.

The report's author has declared it **unreviewed** (its Appendix F). Your assessment is what converts it into a reviewed document. Assume nothing is correct until you have checked it.

### 2. Ground rules — MANDATORY

This repository is live and its filesystem state is evidence. A previous report in this same repository (`EVENT_LOG_VIOLATION_REPORT.md`) records an agent corrupting the audit trail by running a command that wrote to the event log. Do not repeat that.

- **READ-ONLY. Do not create, modify, rename or delete any file in the repository, except your single assessment output file.**
- **Do not delete, move, rename or otherwise "clean up" anything under `work/`.** The report's central finding is that this content exists nowhere else. Deleting it destroys the evidence you are assessing and is the exact harm the report warns about.
- **Do not commit, branch, stage, push, or run `git worktree prune`.**
- **Do not run `pmk`.** Several `pmk` commands append events to the append-only log (`pmk sentinel`, `pmk views`, `pmk queue add`, `pmk queue decide`, `pmk incident`, `pmk claim`, `pmk revoke`, and others), which alters the very artefact under review. Derive Kernel state from `.pm/events/*.jsonl` and `.pm/views/*` directly. If you believe a `pmk` command is unavoidable, record the event count before and after, and report any increase.
- **Do not run the test suite** (`pytest` writes `pytest_junit.xml` and cache directories into the live tree). If you judge it necessary, disclose that you ran it.
- **Permitted:** file reads; byte/line/hash counting; and `git` read-only commands — `git ls-tree`, `git log`, `git show`, `git cat-file`, `git branch`, `git worktree list`, `git status`, `git rev-list`, `git merge-base --is-ancestor`, `git rev-parse`.
- **Sibling directories** referenced by the report — `C:\temp\projects\cfna` and `C:\temp\projects\b5ccg` — may or may not exist on your host. Use them if present; if absent, mark the affected claims as not independently verifiable and say so.
- **Control check, required.** At the end, run `git status --porcelain` and confirm that the only difference you caused is your own assessment file. Record the result in your provenance block.

### 3. Traps that have already caused wrong conclusions in this repository

These are real. An unwary reviewer will fall into them and will produce a false error report.

1. **`.pm/events/2026-10-31.jsonl.bak`** is a stale duplicate sitting beside the live log. Counting events with a glob that includes it over-counts. **Filter to `*.jsonl` only.**
2. **`HANDOFF.md`** exists at the root of every checkout as a *tracked repository file* (~4,692 bytes). It is **not** the fleet handoff mechanism. The fleet handoff is **`.pmwork/HANDOFF.md`**. Conflating them yields a false "196 handoff files exist" reading. Count them separately.
3. **`work/` is gitignored.** `git status` will not show the 886 MB and `git diff` cannot recover it. Absence from git is not absence from disk — measure the filesystem.
4. **`.git`'s real pack is only ~2.7 MB.** The stranded work is not in the object store, so a `git log --all` that finds nothing does not prove the content exists elsewhere. Check each worktree's working tree as well.
5. **Agent `RESULT.md` files are claims, not evidence.** The repository's own rule is that a worker's statement of success is never evidence on its own. The report quotes them to record what was abandoned, not to assert it worked. If the report treats one as proof, that is a defect — flag it.
6. **`b5ccg` is a live repository.** Its figures drift between measurements. If you re-measure and get different numbers than the report, that may be drift rather than error — check whether the report discloses the volatility (its §2.4 does).

### 4. What to verify

#### 4.1 Numeric claims — measure every one

These are the report's claims. Independently measure each and report **your own** value. Agreement is not proof that you measured correctly; disagreement is proof that something is wrong.

| # | Claim to test |
|---|---|
| 1 | 98 directories under `work/`; total 886.2 MB; smallest 8.7 MB; largest 10.3 MB; mean ~9.04 MB |
| 2 | Those 98 trees belong to 51 distinct task IDs; 26 tasks own 1 tree, 3 own 2, 22 own 3 |
| 3 | 47 `VOID` tasks own 93 trees; 4 `DONE` tasks own 5 trees: `T-0118-100`, `T-0119-101`, `T-0130-102`, `T-0139-116`, `T-0139-117` |
| 4 | 56 trees contain uncommitted content; 488 uncommitted file entries; 514.9 MB; 42 trees are clean |
| 5 | `.pmwork/HANDOFF.md` exists in 0 of 98 trees; `.pmwork/RESULT.md` exists in 68 |
| 6 | `remove_worktree()` at `src/fleet/spawn.py:129` has **zero** call sites in `src/` and `tests/` |
| 7 | `render_order()` is called once, at `src/fleet/harness.py:347`; `write_handoff()` once, at `harness.py:586`, inside `_fix_round` only; `_give_up()` at `harness.py:719` calls `revoke` + `quarantine` and never touches the worktree filesystem |
| 8 | 161 git branches, 159 matching `pmk/*`; 107 entries in `.git/worktrees`; 20 `%TEMP%\pmk-merge-*` directories totalling 80.1 MB |
| 9 | 3,109 events in the log; the I1 hash chain verifies; 146 `TASK_CREATED` against 146 distinct task IDs; 138 `VOID` / 6 `DONE` / 2 `PROPOSED` |
| 10 | 108 `REVOKED` events, of which 58 carry reason `lease TTL expired`; 863 `FLEET_BLOCKED`, 423 `OVERSEER_WOKEN`, 255 `FLEET_ASSIGNED`, 192 `SENTINEL_RUN`, 112 `CLAIMED`, 104 `AGENT_STARTED`, 102 `INCIDENT` |
| 11 | `T-0101` claimed at seq 1736 (fence 54), 1832 (fence 65), 1962 (fence 76); revoked at seq 1795 / 1908 / 2109 with reason `lease TTL expired`; voided at seq 2213. `src/cna/core/` exists in neither `HEAD` nor the working tree |
| 12 | The sentinel reports 6 findings: `I6` "INTEGRATED event has no bundle reference" for `T-0118`, `T-0119`, `T-0127`, `T-0129`, `T-0130`; and `I5` `empty_commit_in_integrated` for `T-0139`. Re-derive this from `src/pmk/sentinel.py` and the log — do **not** run `pmk sentinel` |
| 13 | 18 `INTEGRATED` events in total, resolving to 11 distinct subjects; 9 carry a commit hash (all ancestors of `main`) and 9 carry an empty `commit`; 7 tasks record `INTEGRATED` twice |
| 14 | Per-tree bytes in the report's §12 inventory match the trees on disk (spot-check at least six rows, chosen deliberately to include the largest and the smallest) |

#### 4.2 The two central claims — attack these hardest

**Claim A — "the T-0139 corpus is NOT at risk."** The report says: the 66-file CNA rules corpus is committed to `main` at `1a5ec9b`; `git status` for `docs/rules/` is clean; all 66 files verify against both `HEAD:docs/rules/manifest.json` and `HEAD:docs/rules/checksums.sha256`; and the content is identical to the upstream export at `C:\temp\projects\cfna\docs\sources\cna-rules-upstream` after normalising CRLF to LF (upstream CRLF, `main` LF).

Verify it, and specifically try to **falsify** it. Is "identical after normalisation" a true equivalence, or a way of explaining away a real content difference? `1a5ec9b`'s message claims the corpus was staged from the pin's *git objects*, which would make the LF form the faithful one — test that claim rather than accepting it.

**Claim B — "the 56 dirty trees hold content that exists nowhere else."** The report says this content is in no branch, no commit, and not in the main working tree. Attempt the strongest refutation available: for the three `T-0101` trees and for `T-0100-64`, search the entire object store for their uncommitted paths (`git log --all -- <path>`, `git cat-file`, `git branch -a`, `git rev-list --all`) and also check the main working tree. Report, for each, whether it is genuinely unique. If even one is recoverable elsewhere, the report's severity rating is wrong and its recommendations are over-scoped.

#### 4.3 R-12 conformance

Check all 14 elements R-12 requires (§8 of `incident-report-worktree-isolation-v3.md`). For each, state whether it is **present** and whether it is **adequate** — a section titled "Root Cause Analysis" containing no demonstration is not adequate. Verify that every `file:line` citation resolves to the code claimed, and that every commit hash in the report resolves and is what the report says it is.

#### 4.4 Logic and method

Find any of the following, and say so if you find none:

- **Overclaiming** — a statement stronger than its evidence.
- **Asserted causality** — a causal link stated but not demonstrated.
- **Unverified testimony presented as fact** — especially agent `RESULT.md` claims.
- **Recommendations that would cause harm if implemented as written.** Examine the ordering of REC-01 (reclaim worktrees automatically) against REC-02 (archive before deleting). Does the report make it unambiguous that REC-02 must exist *before* REC-01 ships? If not, that is **blocking**, because implementing REC-01 alone would delete the content described in Claim B. Separately, examine §12.2's claim that four "corpus-duplicate" trees can be reclaimed **without any capture step** — is that safe, and is it *proven*, or only asserted?
- **Bucketing or survivorship errors** — a number inflated or deflated by how items were classified, or the same metric counted two ways in two places.
- **Missing findings** — anything a report of this scope should contain and does not.

#### 4.5 Arithmetic

Recompute independently: 886.2 ÷ 969 as a percentage; 138 ÷ 146; 58 ÷ 108; 514.9 ÷ 886.2; the tree partition 42 + 4 + 52 = 98; 371.3 + 38.1 + 476.8 = 886.2; the inference "98 trees for 51 tasks, therefore 146 − 51 = 95 cards produced no checkout"; and every figure in the report's own Appendix F.2 table.

### 5. Grounds for rejection

State plainly if you find any of these:

- a central factual claim is false;
- a number is wrong in a way that changes a conclusion;
- a recommendation is unsafe as written;
- the severity ratings are unjustified by the report's own evidence;
- the report does not actually meet R-12 despite claiming to.

### 6. Grounds for acceptance

State plainly, and do not manufacture objections in order to appear rigorous. If the central claims hold, the numbers check out, the recommendations are safe and correctly ordered, and R-12 is met, the correct verdict is `ACCEPT`, and your output should say so.

### 7. Required output format

Produce a **single Markdown document**. Begin with this provenance block, completed honestly:

```yaml
---
document:
  title: "Assessment of incident-report-worktree-lifecycle-leak-v1"
  status: "Independent assessment; advisory; no repository state changed"
  version: "1.0.0"
provenance:
  assessor_llm:
    name: "<your model name>"
    version: "<your model version / provider>"
  created_date: "<YYYY-MM-DD>"
  repository_access: "full | partial (describe)"
  read_only_attested: true
  pmk_commands_run: "none | <list>"
  test_suite_run: "no | yes (explain why)"
  git_status_clean_except_own_output: "true | false — explain"
---
```

You are the **assessor**, not the author. Never record yourself as author of the report.

Then, in this order:

1. **Verdict** — one line: `ACCEPT` / `ACCEPT WITH CORRECTIONS` / `REJECT`.
2. **Coverage** — what you verified by measurement, and anything you could not verify and why. This is what lets the operator weigh your assessment.
3. **Claim-by-claim results** — a table: `claim | result (confirmed / corrected: <true value> / refuted / not verifiable) | exactly what you ran`. Cover all of §4.1, plus §4.2A and §4.2B.
4. **Corrections** — each with **severity** (blocking / major / minor), the exact text that is wrong, and the exact replacement text you recommend.
5. **R-12 conformance table** — all 14 elements: `element | present? | adequate? | note`.
6. **Risks in the recommendations** — anything unsafe, mis-ordered, or unproven.
7. **Missing findings** — what the report should also have said, if anything.
8. **Questions the operator must answer before the report is closed.**
9. **Confidence** — state honestly how much of your verdict rests on direct measurement versus reasoning from the document alone.

Be concise in prose and complete in coverage. Quote the report's own words when you dispute them. Do not soften a real defect, and do not invent one.

<!-- END PROMPT -->

---

## Notes for the operator

- **Do not summarise the report for the reviewer, and do not tell them the verdict you expect.** Hand over the prompt and the path. The value of this assessment is its independence; priming it destroys that.
- **What "good" looks like.** The highest-value reviews will attack Claim B (§4.2) and the REC-01/REC-02 ordering (§4.4). Those are the two places where being wrong costs the most — one destroys evidence, the other understates it.
- **Newly added to this prompt since the first draft:** claim 13 (the `INTEGRATED`-event counts), claim 14 (spot-check the §12 inventory against disk), and the "do not run the test suite" rule.
- **Storing the result.** Per the repository's conventions, save each assessment unmodified in the project root as `assessment-<model>-incident-report-worktree-lifecycle-leak-v1.md`, with its own provenance block intact. An assessment is **advisory**: it does not itself change the report, the decision queue, or any worktree.
- **Nothing in this prompt authorises a reviewer to change anything.** A reviewer proposes correction text; it does not apply it.
- **Getting several.** Different models fail in different ways. Two or three independent assessments that agree on a correction are worth far more than one, and a disagreement between two reviewers is itself a finding worth recording.
