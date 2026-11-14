# Report: Tiwas Full List - Project Management Workflow Systems Analysis v1

**Document Type**: Formal Project Documentation  
**Purpose**: Comprehensive analysis of project management workflow systems across listed projects to inform UMAWS Fleet Launcher development  
**Audience**: Author and agent building UMAWS Fleet Launcher (LLM-digestible)  
**Author (author_llm)**: opencode kilo/stealth/glyph-cluster  
**Assessor (assessor_llm)**: OpenCode Pulse Alpha Free (independent assessment, 2026-11-04)  
**Date**: 2026-11-04  
**Status**: Assessed — corrections applied & delineated (see [Section 13](#13-assessment-addendum--corrections-register-assessor_llm-opencode-pulse-alpha-free))  

---

> **ASSESSOR NOTICE — OpenCode Pulse Alpha Free (2026-11-04)**
>
> This report has undergone independent assessment. The author's content is preserved; **no text was silently overwritten**. Every correction is delineated inline with a `**Assessor note (OpenCode Pulse Alpha Free):**` marker or in clearly marked new sections, and is also registered in [Section 13 — Assessment Addendum & Corrections Register](#13-assessment-addendum--corrections-register-assessor_llm-opencode-pulse-alpha-free).
>
> Key corrections: (C-01) "12 project directories" was wrong — the table listed 11; ~34 directory entries exist in `C:\temp\projects`; the 11 omitted ones are now covered in §5.12–§5.16. (C-02) Git/activity is grossly mis-stated for railroads (274 commits since 2026-10-05), TiwasProjectsv3 (209), tcindustries (65), TiwasProjects (28), b5ccg (54) and toy1/toy2/toy3 (54/46/28). (C-03) tiwas-ttrpg-project-documentation is **not** "Active (recent commits)" — last commit 2026-09-21, 0 commits since 2026-10-05. (C-04) tiwas-ttrpg and tiwasfeudum have **no git** (report said "Unknown"/"[GUESS]"). (C-05) §6 ranking and §7 Success categories re-scored from measured data (§6.3, §7.A); original tables retained with supersession banners.
>
> Raw verification data: Appendix D. Methodology: Appendix F. Missed-projects register: Appendix E.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Metadata & Provenance](#2-metadata--provenance)
3. [Systematic PM Component Template](#3-systematic-pm-component-template)
4. [Projects Analyzed](#4-projects-analyzed)
5. [Per-Project Deep Dives](#5-per-project-deep-dives)
6. [Comparison Matrices](#6-comparison-matrices)
7. [Success Assessment](#7-success-assessment)
8. [Best/Worst Aspects & Recommendations](#8-bestworst-aspects--recommendations)
9. [Future-Proof Systematic Framework](#9-future-proof-systematic-framework)
10. [Basis for UMAWS Fleet Launcher Development](#10-basis-for-umaws-fleet-launcher-development)
11. [Guesses & Inferences Log](#11-guesses--inferences-log)
12. [Appendices](#12-appendices)
13. [Assessment Addendum & Corrections Register (assessor_llm: OpenCode Pulse Alpha Free)](#13-assessment-addendum--corrections-register-assessor_llm-opencode-pulse-alpha-free)

---

## 1. Executive Summary

This report analyzes project management workflow systems across 12 project directories in C:\temp\projects\. The analysis covers governance, provenance, agent management, task tracking, verification mechanisms, and success assessment based on internally stated goals vs actual outcomes.

> **Assessor note (OpenCode Pulse Alpha Free):** The opening claim is wrong on three counts. (a) The §4 table lists **11** projects, not 12. (b) `C:\temp\projects` contains **34 directory entries** (32 excluding `node_modules` and `tmp`); **11 substantive entries were omitted**: toy1, toy2, toy3, cfna, tttrpg, bb, bsns5004, TiwasTUI, javaciv2, toy-b5ccg, and the five railroads task worktrees (`railroads-wt-T-0041…0045`, same repo). These are now covered in §5.12–§5.16 and Appendices D/E. (c) The phrase "12 project directories" must not be relied on; read "22 assessed entries" including assessor additions. Full register: Section 13 (C-01, C-02).

### Key Findings

**System Classes Identified:**
1. **UMAWS/KERNEL-LITE** (Event-sourced multi-agent coordination): testproject1, TiwasProjects, tiwasfeudum, railroads (variant), **toy1, toy2, toy3** (assessor additions) - share .pm/ with events/tasks/registry/policy, kernel concepts
2. **GOVERNANCE/DOC-CENTRIC** (Decision registers, authority models): Tiwas-ttrpg-project-documentation, tiwas-ttrpg, tcindustries, **cfna** (assessor addition — agent-rules/RD-xxxx, no commits) - heavy on DEC-XXX, governance docs, provenance
3. **LEDGER/TASK-TRACKER** (Row-based task management): Babylon5CCGGameDesign, b5ccg - ledger rows, census tools, pattern libraries
4. **WF/ORCHESTRATOR**: TiwasProjectsv3 - wf/ system
5. **TRADITIONAL/GUIDELINES**: JavaProjects - coding guidelines for LLMs, minimal PM workflow
6. **MIXED/UNCLEAR**: Others require further investigation

> **Assessor note (OpenCode Pulse Alpha Free):** Class 1 must include toy1/toy2/toy3 (full `.pm/`, kernel constitutions, pins, pmk) — toy1/toy2 are near-forks of testproject1 and hold direct UMAWS Fleet Launcher evidence (launcher proposals, completion reports, an independent Claude Sonnet 5.5 assessment of the Hermes completion report). Class 6 is not "unclear": the remaining entries are classified in §5.15/§5.16 — none is a PM workflow system (see Appendix E). "MIXED/UNCLEAR … require further investigation" is withdrawn (C-06).

**UMAWS Fleet Variants:** Multiple projects show UMAWS-like patterns (TiwasProjects has .pm with kernel/, testproject1 is current Fleet, tiwasfeudum is similar Fleet-style, railroads has .pm variant). These appear to be different versions/iterations of similar systems.

> **Assessor note (OpenCode Pulse Alpha Free):** Correct and now stronger — the variants include **toy1, toy2** (testproject1 forks: Tier A scaffolds, 241 tests green in toy2, direct Fleet Launcher artefacts), **toy3** (minimal Hermes-profile experiment), and **railroads** (goal/metrics/queue design + heavy use of `task/T-00xx` branches and five persistent git worktrees `railroads-wt-T-0041…0045`). See §5.12–§5.14. Also: **testproject1's git remote is `github.com/tiwaking-ops/UMAWS-Fleet-Launcher.git`** — this report's own stated purpose (informing Fleet Launcher development) ties directly to the analysed codebase; the author did not note this.

**Success Patterns:** Projects with explicit governance, provenance tracking, and active maintenance tend to be more coherent. Stalled/abandoned projects often lack clear gates or have drifted from their stated processes.

> **Assessor note (OpenCode Pulse Alpha Free):** Directionally supported, but the author's activity inputs were wrong: railroads (**274 commits** since 2026-10-05, last 2026-11-04) and TiwasProjectsv3 (**209**) are the most active repos in scope, while tiwas-ttrpg-project-documentation — scored as active — has had **zero commits since 2026-10-05** (last 2026-09-21). §6.3/§7.A re-rank using measured data.

*(Full details in subsequent sections)*

---


## 2. Metadata & Provenance

```yaml
report_metadata:
  filename: report-tiwas-full-list-project-workflow-systems-v1.md
  author_llm: "opencode kilo/stealth/glyph-cluster"
  assessor_llm: "OpenCode Pulse Alpha Free"   # assessor correction: was "TBD"; filled 2026-11-04
  created: "2026-11-04"
  purpose: "Comprehensive PM workflow system analysis for UMAWS Fleet Launcher comparison"
  audience: ["author", "umaws-fleet-launcher-agent"]
  llm_digestible: true
  exhaustive: false   # assessor correction: was `true`; 11 directory entries omitted — see §5.12–§5.16 and Appendix E
```

**Provenance Notes:**
- This report follows global AGENTS.md rules: author identified, assessor to be separate LLM
- All inferences marked with [GUESS] and logged in Section 11
- Git history examined where available
- Analysis based on current working tree + git log

> **Assessor note (OpenCode Pulse Alpha Free) — Assessment Provenance:**
> - **Method:** full enumeration of `C:\temp\projects` (34 entries; 32 excluding `node_modules`, `tmp`); per-entry classification; for every git repo: `rev-parse --abbrev-ref HEAD`, `remote get-url origin`, `log -1`, `log --since=2026-10-05 --oneline` (30-day activity window preceding the report date), `status --porcelain` (dirty-file counts); `git worktree list` for railroads; targeted content reads (AGENTS.md, governance/, .pm/ listings, key reports).
> - **Date of measurement:** 2026-11-04. Directories without VCS (tiwas-ttrpg, tiwasfeudum, tttrpg, javaciv2, toy-b5ccg, bb, bsns5004, TiwasTUI) carry **no verifiable activity signal**; their rows are marked UNVERIFIED rather than inferred.
> - **Delineation rule:** author text is never deleted; corrections are added as `Assessor note` blocks and new sections, or flagged inline where a single figure must change.
> - **What the assessor did NOT do:** re-derive the author's holistic §6 "Overall Score (0-10)" (not reproducible from the stated rubric; see Appendix F). §6.3 re-ranks on the §7 rubric instead.
> - Assessor signs **assessor_llm only**. `author_llm` (opencode kilo/stealth/glyph-cluster) is unchanged. No self-assessment occurred.

---


## 3. Systematic PM Component Template

*See standalone file: [pm-workflow-analysis-template-v1.md](./pm-workflow-analysis-template-v1.md)*

The template provides a comprehensive checklist for analyzing PM workflow systems across 12 dimensions with success rubric and recommendation tracking. It is designed for LLM consumption and reuse.

---


## 4. Projects Analyzed

| Project | Path | Git (remote) | Has .pm | Has governance/ | Has kernel/wf | Notes |
|---------|------|-----|---------|-----------------|---------------|-------|
| testproject1 | C:\temp\projects\testproject1 | Yes (**tiwaking-ops/UMAWS-Fleet-Launcher.git**) | Yes | Partial (pilot/, src/kernel) | Yes (kernel) | UMAWS Fleet Kernel-lite - current reference; **87 commits since 2026-10-05** |
| tiwas-ttrpg-project-documentation | C:\temp\projects\Tiwas-ttrpg-project-documentation | Yes (tiwaking-ops/Tiwas-ttrpg-project-documentation.git) | No | Yes (authority.md, provenance.md, status-model.md) | No | Governance/doc-centric, DEC-141→149 verified in log; **stale: 0 commits since 2026-10-05**, last 2026-09-21; 113 untracked = **lost work** (operator); Discipline 2→1 |
| tiwas-ttrpg | C:\temp\projects\tiwas-ttrpg | **No git** (report said "Unknown\*") | No | Yes | No | Governance/doc-centric; stale since 2026-08-29; `_consolidation/` shows supersession by docs repo |
| Babylon5CCGGameDesign | C:\temp\projects\Babylon5CCGGameDesign | Yes (tiwaking-ops/Babylon5CCGGameDesign.git) | No | Partial (docs/) | No | Ledger-based; `census.ps1`/`check_claims.ps1` verified; `.agent/PATTERNS` = **1279 files**; 4 commits since 2026-10-05; **2375 dirty files** |
| b5ccg | C:\temp\projects\b5ccg | Yes (tiwaking-ops/b5ccg.git) | No | Partial (docs/) | No | B5CCG sibling repo (remote confirms); 54 commits since 2026-10-05; 1081 dirty |
| tcindustries | C:\temp\projects\tcindustries | Yes (tiwaking-ops/TCIndustries.git) | No | Yes (HD-TST-01 ruling file verified) | No | Human rulings + reconciliation matrix; **65 commits since 2026-10-05; 0 dirty** |
| JavaProjects | C:\temp\projects\JavaProjects | Yes (tiwaking-ops/JavaProjects.git) | No | Minimal (AGENTS.md) | No | Java 6 hard requirement (verified); 12+ sub-projects; 3 commits since 2026-10-05 (BlueJ manual workflow) |
| TiwasProjectsv3 | C:\temp\projects\TiwasProjectsv3 | Yes (tiwaking-ops/TiwasProjectsv3.git) | No | Yes | Yes (wf/) | WF orchestrator; **209 commits since 2026-10-05**; tip `task/T-0161` |
| TiwasProjects | C:\temp\projects\TiwasProjects | Yes (tiwaking-ops/TiwasProjects.git) | Yes | Partial (AGENTS.md) | Yes (.pm/kernel) | Older UMAWS variant; **28 commits since 2026-10-05** (active) |
| railroads | C:\temp\projects\railroads | Yes (**no remote**) | Yes | Partial (AGENTS.md) | Partial | Goal/metric variant; **274 commits since 2026-10-05**; 5 git worktrees (below) |
| tiwasfeudum | C:\temp\projects\tiwasfeudum | **No git** (report said "Unknown\*") | Yes | Partial (AI_DESIGN.md etc) | Yes (fleet in .pm) | Fleet-like; structurally verified; no VCS — activity UNVERIFIED; mtime 2026-10-31 |
| **toy1** *(assessor addition)* | C:\temp\projects\toy1 | Yes (**no remote**) | Yes (full) | Partial | Yes (kernel) | UMAWS Fleet fork (Tier A); Fleet Launcher proposals + completion/assessment reports; 54 commits since 2026-10-05 |
| **toy2** *(assessor addition)* | C:\temp\projects\toy2 | Yes (**no remote**) | Yes (full) | Partial | Yes (kernel) | Fresh Fleet init 2026-10-25; 241 tests green; sentinel 2 findings; 46 commits since 2026-10-05 |
| **toy3** *(assessor addition)* | C:\temp\projects\toy3 | Yes (**no remote**) | Yes (minimal) | Partial | Yes (kernel, minimal) | Minimal Hermes-profile experiment; 28 commits since 2026-10-05 |
| **cfna** *(assessor addition)* | C:\temp\projects\cfna | Yes — **unborn `master`, 0 commits** | No | Yes (AGENTS.md agent rules; `docs/decisions/RD-xxxx.md`) | No | "CNA digital edition" engine; **live project** (operator, 2026-11-04); intended standalone; nothing landed in VCS |
| **tttrpg** *(assessor addition)* | C:\temp\projects\tttrpg | **No git** | No | No | No | 5 loose TTRPG draft files; stale since 2026-08-30; superseded |
| **bb** *(assessor addition)* | C:\temp\projects\bb | **No git** | No | No | No | B5CCG card-image investigations (assets); not a PM system |
| **bsns5004** *(assessor addition)* | C:\temp\projects\bsns5004 | **No git** | No | No | No | University coursework PDFs; not a PM system |
| **TiwasTUI** *(assessor addition)* | C:\temp\projects\TiwasTUI | **No git** — empty dir | No | No | No | Empty; not a PM system |
| **javaciv2** *(assessor addition)* | C:\temp\projects\javaciv2 | **No git** | No | No | No | Single `UnitTypeSmoke.java`; **retained — believed in use by a project; operator to delete later** (2026-11-04) |
| **toy-b5ccg** *(assessor addition)* | C:\temp\projects\toy-b5ccg | **No git** | No | No | No | Single proposal md; not a PM system |
| *(worktrees)* railroads-wt-T-0041…0045 | C:\temp\projects\railroads-wt-T-0041 … \railroads-wt-T-0045 | Yes — **same repo as railroads** (`git worktree list`; branches `task/T-0041…0045`) | Yes (inherited) | Inherited | Inherited | 138–159 commits each since 2026-10-05; **not separate projects** — no double counting |

\* Git status not fully confirmed from quick check - marked for investigation [GUESS where stated]

> **Assessor note (OpenCode Pulse Alpha Free):** The author's footnote is superseded — every cell above is now measured or explicitly marked UNVERIFIED/no-git. Original unverified rows were: tiwas-ttrpg and tiwasfeudum (both **no git**). `node_modules` and `tmp` are not projects and are excluded. All 11 author rows retained; 11 additions + 1 worktree note. See Appendix D (verification log) and Appendix E (missed-projects register).

---


## 5. Per-Project Deep Dives

### 5.1 testproject1 (UMAWS Fleet - Current Reference)
**Path:** C:\temp\projects\testproject1  
**Class:** UMAWS/KERNEL-LITE  
**Git:** Yes (recent commits: corpus, evidence, incident reports, fleet worktree isolation)

> **Assessor note (OpenCode Pulse Alpha Free):** Verified — **87 commits since 2026-10-05**; remote is **`github.com/tiwaking-ops/UMAWS-Fleet-Launcher.git`** (this report's stated purpose); 142 dirty files; tip `1a5ec9b` (2026-11-03). `.pm/` listing matches the report exactly (briefings, conflicts, context-snapshots, events, evidence, fleet, memory, nohooks, quarantine, registry, tasks, views, constitution.md, policy.toml, pins.sha256, context.sha256, .kernel.lock.lock). Structure claims accurate.

**Structure:**
- `.pm/`: briefings, conflicts, context-snapshots, events, evidence, fleet, memory, nohooks, quarantine, registry, tasks, views, constitution.md, policy.toml, pins.sha256
- `src/`, `pilot/`, `gateway/`, `tools/`, `tests/`
- `AGENTS.md`: Kernel authoritative, use pmk CLI, oracles decide
- `agents.toml`: fleet configuration

**Governance:** Kernel is writer - transitions via pmk. Oracles decide via gate_cmd. Windows native with .lock files. Constitution.md present.

**Provenance:** Events log, evidence/ storage, pins.sha256, context snapshots. Strong audit trail.

**Agent Management:** Fleet profiles in agents.toml, roles, worktree isolation (recent focus), briefings.

**Task Tracking:** tasks/ in .pm, events log tracks transitions.

**Strengths:** Strong governance, event-sourced, explicit rules, evidence-based, active development.
**Weaknesses:** Complex, kernel-centric may be rigid, Windows-specific details.
**Status:** Active (recent commits Nov 2026)

### 5.2 Tiwas-ttrpg-project-documentation (Governance/Doc-Centric)
**Path:** C:\temp\projects\Tiwas-ttrpg-project-documentation  
**Class:** GOVERNANCE/DOC-CENTRIC  
**Git:** Yes (commits show DEC-141 to DEC-149, analyze-assess-record-store workflow)

**Structure:**
- `governance/`: authority.md, provenance.md, status-model.md
- `canonical/`, `investigations/`, `proposals/`, `roadmap/`, `audits/`
- Heavy DEC-XXX references, REQ-XXX
- Skills reference analyze-assess-record-store

**Governance:** Strong governance model with authority, provenance, status model docs. Decision register pattern.

**Provenance:** Explicit provenance tracking mentioned, storage annotations, non-canonical marking. Follows AGENTS.md global rules.

**Agent Management:** Multi-LLM workflow (opencode/big-pickle mentioned), orchestration plan.

**Task Tracking:** DEC tracking, roadmap streams, promotion backlog.

**Strengths:** Excellent provenance/governance discipline, clear non-canonical marking, storage workflow.
**Weaknesses:** Documentation-heavy, may be slow, less code execution focus.
**Status:** Active (recent commits)

> **Assessor note (OpenCode Pulse Alpha Free):** **Status line is wrong.** Measured: **0 commits since 2026-10-05**; last commit **2026-09-21** (DEC-149 storage annotation); vs report date 2026-11-04 that is ~6 weeks idle. 113 dirty working-tree entries, all untracked (`??`) — i.e., work exists but is **not committed**. Claims that *are* verified: governance/ contains exactly `authority.md`, `provenance.md`, `status-model.md`; DEC-141→DEC-149 present in git log; 102 DEC-14x references in root docs. The "recent commits" claim in §6.1/§7 (Activity=2) is corrected in §6.3/§7.A.

> **Operator note (operator statement, relayed by assessor, 2026-11-04):** The 113 untracked entries are **lost work** per the operator — never entered version control, effectively unrecoverable as history. Operator-directed re-score: **Process Discipline 2→1** (total 8→7; category High→Med); see §13.6 O2.

### 5.3 tiwas-ttrpg
**Path:** C:\temp\projects\tiwas-ttrpg  
**Class:** GOVERNANCE/DOC-CENTRIC [GUESS - similar structure to above]  
**Git:** [GUESS - not checked in detail]  
**Structure:** Similar dirs (canonical, governance, investigations, etc.), PROJECT_CONTEXT.md, README.md

**Notes:** Appears related to Tiwas TTRPG ecosystem. Likely shares governance patterns with Tiwas-ttrpg-project-documentation. [GUESS]

> **Assessor note (OpenCode Pulse Alpha Free):** Resolved — **no `.git`** (this is not "not checked", it is *not under version control*). Stale since **2026-08-29**. Structure verified: `canonical/` (rules, decisions, systems, changelog), `governance/` (authority.md, provenance.md, status-model.md), `investigations/`, `_consolidation/` containing `consolidation-plan.md`, `decision-register.md`, `document-inventory.md`, `relationship-map.md` — i.e., it was the **pre-consolidation source**, superseded by Tiwas-ttrpg-project-documentation. Classification confirmed; "related repo" guess **confirmed** (same ecosystem, same author, shared file sets). Not a living project — treat as **archived source material**.

### 5.4 Babylon5CCGGameDesign (Ledger-Based)
**Path:** C:\temp\projects\Babylon5CCGGameDesign  
**Class:** LEDGER/TASK-TRACKER  
**Git:** Yes  
**Structure:** `docs/`, `src/`, `.agent/PATTERNS/` with many lessons learned, ledger references throughout

**Governance:** Pattern-based learning, census scripts, checks. B5-* task IDs.

**Provenance:** Pattern files document decisions/lessons with dates and agent names.

**Agent Management:** Heavy multi-agent usage (many agent dirs in .agent/PATTERNS), pattern library per agent/type.

**Task Tracking:** B5-XXXX ledger rows, census.ps1/check_claims.ps1, listb5tasks skill mentioned.

**Strengths:** Rich institutional knowledge in patterns, task tracking via ledger, strong forensics.
**Weaknesses:** Ledger can be complex, many agent variants, may have collision issues.
**Status:** Active

> **Assessor note (OpenCode Pulse Alpha Free):** Verified in part — remote is `tiwaking-ops/Babylon5CCGGameDesign.git`; `census.ps1` and `check_claims.ps1` exist in repo root; `.agent/PATTERNS` holds **1279 files** ("rich pattern library" confirmed quantitatively). **Activity is not "Active" by git:** 4 commits since 2026-10-05 (last `73940079`, 2026-10-16), but **2375 dirty working-tree entries** — enormous uncommitted output (breakdown: **44 tracked deletions** — all `.agent/CLAIMS/B5-*.json` — **85 modified**, **2246 untracked**). The author's own commit `73940079` already logs a hook bypass on a foreign heartbeat file — evidence of coordination friction the report understates.

> **Operator note (operator statement, relayed by assessor, 2026-11-04):** The dirty tree is **lost work** per the operator — the 44 deleted `.agent/CLAIMS/B5-*.json` files and the untracked backlog were never captured in history. Process Discipline stays at **1** (already failed that gate; no further down-score possible within rubric); the tree's unusability for review is now **operator-confirmed**, not merely an inference.

### 5.5 b5ccg
**Path:** C:\temp\projects\b5ccg  
**Class:** LEDGER/TASK-TRACKER [GUESS - related to Babylon5CCGGameDesign]  
**Git:** Yes  
**Structure:** Has .agent/, docs/, b5ccg engine code, b5-*.js files, ledger-like patterns

**Notes:** Appears to be related/variant of B5CCG system. Shares ledger/task patterns. [GUESS]

> **Assessor note (OpenCode Pulse Alpha Free):** Guess **confirmed** — remote is `github.com/tiwaking-ops/b5ccg.git` (sibling repo to `Babylon5CCGGameDesign.git`, same owner). **54 commits since 2026-10-05**; tip `e1fd834` (2026-10-31); branch `task/opencode-laguna-s-2-1-01-B5-0106` — an active agent task branch; **1081 dirty files** (large generated/engine codebase, same hygiene risk as B5CCG). Shares the ledger/`.agent` pattern library approach. Activity score corrected 1→2 in §7.A; classification confirmed.

### 5.6 tcindustries (Governance with Human Rulings)
**Path:** C:\temp\projects\tcindustries  
**Class:** GOVERNANCE/DOC-CENTRIC  
**Git:** Yes  
**Structure:** `governance/` with human rulings register, authority matrix, canonical/, investigations/

**Governance:** Explicit human rulings (HD-TST-01), authority reconciliation matrix. Human-in-the-loop emphasized.

> **Assessor note (OpenCode Pulse Alpha Free):** Verified — `governance/TCIndustries_Testbed_Reuse_Human_Ruling_HD-TST-01_2026-09-14.md` exists, alongside `TCIndustries_Human_Rulings_Register.md`, `TCIndustries_Authority_Provenance_Reconciliation_Matrix.md`, `TCIndustries_Master_GDD_v1.0_Canonical_Audit.md`, `project_memory.md`, `eic/`. **65 commits since 2026-10-05; 0 dirty files** — the cleanest tree measured in scope; tip `5a618e2` (2026-10-25). Activity score corrected 1→2 in §7.A; "unclear completion" softened — governance artifacts are current and the working tree is clean.

**Provenance:** Formal registers, audit reports.

**Strengths:** Clear human authority, reconciliation mechanisms.
**Weaknesses:** May be heavier process.
**Status:** Active

### 5.7 JavaProjects (Traditional Guidelines)
**Path:** C:\temp\projects\JavaProjects  
**Class:** TRADITIONAL/GUIDELINES  
**Git:** Yes  
**Structure:** Multiple subprojects, AGENTS.md with detailed coding guidelines for LLMs

**Governance:** Guidelines-based, user retains final authority, Java 6 compatibility hard requirement.

> **Assessor note (OpenCode Pulse Alpha Free):** Verified — Java 6 hard requirement present at `AGENTS.md:21-27,59,324,347` ("Java 6 compatibility is a hard requirement unless the user explicitly permits…"); user retains final authority (AGENTS.md "Primary Development Environment" section). **Sub-projects (12+):** BardsTaleGame, CapitalismSim, CityBuilderGame, JavaCiv1, javaciv2, javaciv2_bin, MeridianCo, TiwasSaveYouTubeApp — the report scores the umbrella as one entry, understating per-project PM assessment. **3 commits since 2026-10-05** (tip `3b89e0f`, 2026-10-21); 14 dirty files. BlueJ manual workflow likely explains low commit cadence — flagged, not penalised beyond Sustainability 2→1 in §7.A. JavaProjects is **not a PM workflow system** and is scored for reference only.

**PM Workflow:** Minimal - no .pm, no kernel, no ledger. Focus on coding standards.

**Strengths:** Clear constraints, LLM-optimized, simple.
**Weaknesses:** No task coordination, no provenance tracking, not a PM workflow system.
**Status:** Active (personal projects)

### 5.8 TiwasProjectsv3 (WF Orchestrator)
**Path:** C:\temp\projects\TiwasProjectsv3  
**Class:** WF/ORCHESTRATOR  
**Git:** Yes  
**Structure:** `wf/` with wf.py, VERSION, retired/, `src/`, `governance/`, `docs/`, `projects/`

**Notes:** Has workflow system implementation. Different from kernel event-sourced approach. [GUESS on details - needs deeper inspection]

> **Assessor note (OpenCode Pulse Alpha Free):** Verified with corrections — `wf/` contains `wf.py`, `VERSION`, `retired/` (v1+ system present and real, not a stub); tip is branch **`task/T-0161`**, commit `6d7a964` (2026-10-28); remote `tiwaking-ops/TiwasProjectsv3.git`; **209 commits since 2026-10-05** — this is the **second most active repo in scope after railroads**, not "needs deeper inspection" in any priority sense. 13 dirty files (clean). Also present: `GOALS.md`, `governance/`, `override/`, `projects/`, `.wf/`, and **hundreds of stray root-level scrape artefacts** (`_*.html`, `_*.pdf`, `_*.txt` — web/PDF research dumps) indicating undisciplined root-level working files despite an otherwise structured system. Activity score corrected 1→2 in §7.A. Classification (WF/ORCHESTRATOR) confirmed.

### 5.9 TiwasProjects (UMAWS-like Older Variant)
**Path:** C:\temp\projects\TiwasProjects  
**Class:** UMAWS/KERNEL-LITE [GUESS]  
**Git:** Yes  
**Structure:** `.pm/` with briefings, decisions, events, evidence, kernel, roles, tasks, views, policy.yaml  
**Files:** Ultimate-Multi-Agent-Workflow-System-Claude.md, CLAUDE.md

**Governance:** Similar to UMAWS - has kernel/, decisions in .pm, roles.

**Strengths:** Early UMAWS variant, good for understanding evolution.
**Weaknesses:** Older structure (Oct 2026 dates), may be superseded.
**Status:** [GUESS - check activity]

> **Assessor note (OpenCode Pulse Alpha Free):** Activity resolved — remote `tiwaking-ops/TiwasProjects.git`; **28 commits since 2026-10-05**; recent work includes `T-0058: Add GUI bridge module src/gui/bridge.py and tests`, `T-0047: Ctrl-N/Ctrl-L/Ctrl-Q shortcuts in the TUI launcher`, `T-0046` worker-loop fixes, YAML-evidence acceptance — i.e., **active, in-flight feature development**, not an abandoned archive. `.pm/` structure verified (briefings, conflicts, **decisions**, events, evidence, **kernel**, roles, tasks, views, policy.yaml). 152 dirty files. "Less active / unclear current state" is **refuted**; supersession by testproject1 is plausible architecturally but unproven — both are live branches of development. Activity score corrected 1→2 in §7.A.

### 5.10 railroads (UMAWS Variant)
**Path:** C:\temp\projects\railroads  
**Class:** UMAWS/KERNEL-LITE (VARIANT)  
**Git:** Yes  
**Structure:** `.pm/` with goals, metrics, queue, tasks, registry, decisions, evidence (different structure than kernel event-sourced)  
**Files:** AGENTS.md, HANDOFF.md, policy.yaml

**Notes:** Different .pm structure - more goal/metric oriented than event-sourced. Interesting variant. [GUESS on classification]

> **Assessor note (OpenCode Pulse Alpha Free):** Verified — `.pm/` exactly as described (plus `fixture-manifest.json`). **274 commits since 2026-10-05 — the most active repo in scope**; tip `c23cf2f` (2026-11-04, T-0016 plugin findings); **no remote**; 50 dirty files. Five dedicated task worktrees (`railroads-wt-T-0041…0045`, branches `task/T-0041…0045`, each 138–159 commits since 2026-10-05) — railroads is **actively dogfooding git-worktree task isolation at scale**, directly relevant to UMAWS Fleet Launcher's worktree-isolation goal. AGENTS.md enforces hard rules (operator-owned read-only files; provenance tags `SOURCED/INFERRED/DESIGNED/UNKNOWN`; headless-test gate; task cards) — **discipline is demonstrably strong, contradicting the author's implicit "variant = weaker" framing**. Classification confirmed; activity score corrected 1→2 and discipline 1→2 (evidence: AGENTS.md hard rules + gate + worktree practice) in §7.A. The author's `[GUESS on classification]` is resolved: it is a coherent, independently-designed PM system, not a misclassified kernel fork.

### 5.11 tiwasfeudum (UMAWS Fleet-like)
**Path:** C:\temp\projects\tiwasfeudum  
**Class:** UMAWS/KERNEL-LITE [GUESS]  
**Git:** [GUESS - not checked]  
**Structure:** `.pm/` similar to testproject1 - events, fleet, briefings, constitution.md, policy.toml, pins.sha256  
**Files:** ARCHITECTURE.md, AI_DESIGN.md, pilot/

**Notes:** Very similar to testproject1 structure. Likely UMAWS Fleet variant - good for comparison. [GUESS]

> **Assessor note (OpenCode Pulse Alpha Free):** Verified with correction — **no `.git`** (not "not checked"; not under version control; activity therefore **UNVERIFIED**, not merely unknown). `.pm/` listing confirmed: briefings, conflicts, events, evidence, fleet, memory, registry, tasks, constitution.md, policy.toml, pins.sha256 (matches testproject1 minus context-snapshots/nohooks/quarantine/views/context.sha256 — i.e., an **earlier or trimmed Fleet-like layout**). Directory mtime 2026-10-31 (recent touch, but no VCS to validate what landed). Classification confirmed; activity score stays 1 and is explicitly **UNVERIFIED (no VCS)** in §7.A.

### 5.12 toy1 (UMAWS Fleet Fork — Launcher Evidence) *(assessor addition)*
**Path:** C:\temp\projects\toy1  
**Class:** UMAWS/KERNEL-LITE (fork of testproject1)  
**Git:** Yes — **no remote**; 54 commits since 2026-10-05 (tip `a64b994`, 2026-10-25, "Finalize: project CLOSING, all tasks DONE, close-check passed")

**Structure (verified):** Full Fleet layout — `.pm/` (briefings, conflicts, context-snapshots, events, evidence, fleet, memory, nohooks, quarantine, registry, tasks, views, constitution.md, policy.toml, pins.sha256, context.sha256, .kernel.lock.lock), plus `src/`, `pilot/`, `gateway/`, `tests/`, `agents.toml`, and a large proposal set at root: `proposal-claude-umaws-fleet-launcher-v1.md`, `proposal-claude-umaws-gateway-*.md`, `proposal-claude-llm-gateway-v1-1.md`, `LLM-Prompt-Launcher-App.py`, `UMAWS_Project_Report.md`, `Assessment-of-UMAWS-completion-report-v1.1.md`, `UMAWS_USER_MANUAL.md`, `prompts.json`.

**Governance:** Same Kernel-lite model as testproject1 (pmk CLI, oracles, constitution). Completion claims are self-reported and were **independently assessed** in-repo by Claude (Sonnet) 5.5 — verdict: *"report v1.1 should not be accepted as it stands … the evidence makes the system's core look more trustworthy than the report does: it works, but the report overstates what was shown."*

**Provenance:** Event log + evidence + pins (inherited). Notably, the repo embeds its own **independent completion assessment** — a pattern worth adopting.

**Agent Management:** Fleet profiles inherited; toy1 stress-tested real provider calls (OpenRouter "Insufficient credits" vs opencode "Rate limit exceeded" failure classification; Fleet defects D-53/D-54/D-56 found and fixed).

**Task Tracking:** pmk tasks; CLOSING state recorded in git tip message.

**Strengths:** Real launcher-path evidence; honest independent assessment embedded; found actual Fleet defects. **Weaknesses:** No remote (unbacked-up); fork drift from testproject1; project closed with completion claims that failed independent review.
**Status:** Closed/superseded by continued development in testproject1 (the live `UMAWS-Fleet-Launcher.git`).

### 5.13 toy2 (UMAWS Fleet Fork — Fresh Init) *(assessor addition)*
**Path:** C:\temp\projects\toy2  
**Class:** UMAWS/KERNEL-LITE (fresh scaffold)  
**Git:** Yes — **no remote**; 46 commits since 2026-10-05 (tip `47e21e6`, "fresh: pmk project init with hard rules and minimal PDD")

**Structure (verified):** Same full `.pm/` layout as testproject1/toy1. `UMAWS_Fleet_toy2_Completion_Report.md` (author: Claude Code, Ultracode mode, 2026-10-29) states: **Tier A (Foundation)** — scaffold complete, **241 tests green (87.61s)**, **no live task execution yet**; sentinel flagged **2 findings** (I1: hash mismatch at seq 84; I16: AGENTS.md out-of-band edit).

**Strengths:** Clean-room re-init validated Fleet scaffolded correctness end-to-end; 241-test green baseline; sentinel catches real integrity breaks. **Weaknesses:** Zero real task execution — breadth without proof of value; no remote; potential fork drift.
**Status:** Complete scaffold; not production-exercised. Highly relevant comparative datapoint for Fleet Launcher bring-up.

### 5.14 toy3 (UMAWS Fleet — Minimal Profile) *(assessor addition)*
**Path:** C:\temp\projects\toy3  
**Class:** UMAWS/KERNEL-LITE (minimal/experimental)  
**Git:** Yes — **no remote**; 28 commits since 2026-10-05; tip `ad544e4` (2026-10-27, "hermes profile on the current CLI (chat -q -Q), nous provider, beam model")

**Structure (verified):** Reduced `.pm/` (events, evidence, fleet, nohooks, quarantine, views, constitution.md, policy.toml, pins.sha256, .kernel.lock.lock — no tasks/, briefings/, registry/, memory/). Root: `agents.toml`, `agents.toml.proposed`, `csv2md.py`, `pytest.ini`, `work/`. `AGENTS.md` cites `assessment-claude-toy3-v1.md` hard rules (pmk-only transitions; `.pm/` read-only; failing sentinel → queue, never edited away; fix implementation, not tests).

**Strengths:** Smallest viable Fleet profile; useful floor for complexity/minimalism trade-off. **Weaknesses:** Incomplete PM surface (no tasks/briefings/registry) — a diagnostic sandbox, not a working PM system; no remote.
**Status:** Experimental; superseded as reference by testproject1/toy1/toy2.

### 5.15 cfna (Agent-Rules Engine — Live Project, No VCS History) *(assessor addition, operator-amended)*
**Path:** C:\temp\projects\cfna  
**Class:** AGENT-RULES/DOC-CENTRIC (code engine; **not a PM workflow**)  
**Git:** Yes — **unborn `master`, zero commits**; 3 dirty files (AGENTS.md, CLAUDE.md, docs/)

> **Operator note (operator statement, relayed by assessor, 2026-11-04):** **cfna is a live project.** It was originally intended to live in its own top-level folder; an LLM had suggested running it inside testproject1 — superseded by the operator's clarification. Treat as a nascent standalone project, not a scratchpad and not testproject1 scope.

**Structure (verified):** `docs/decisions/` (RD-xxxx.md decision records), `docs/rules/` (pinned), `docs/sources/`, `docs/milestones/`, `AGENTS.md`, `CLAUDE.md`. Platform: Windows 10, Python ≥3.11, stdlib + pytest. Agent rules are exceptionally explicit ("Never invent historical data", "Missing data → schema + placeholder + docs/data-gaps.md", "Every rule function has a docstring `RULE: <case ids>`", "One task = one module + its tests, ≤ 45 min").

**Governance:** Rule-as-data with decision log — governance pattern without a PM/task layer. **Provenance:** Source-pinned rules; no VCS history to audit. **Task tracking:** None (module+test = task; no ledger/pmk).
**Status:** Live project (operator-confirmed 2026-11-04), pre-commit stage; intended standalone genesis — nothing committed to VCS yet; unscoreable as PM; notable as a **discipline exemplar** for rule-pinned agent execution.

### 5.16 Non-PM & Excluded Entries *(assessor addition)*
Registered for completeness; **none is a PM workflow system**; scoring not applicable (see §7.A):

| Entry | Finding | Disposition |
|-------|---------|-------------|
| tttrpg | 5 loose TTRPG drafts (S1/S3 documents), stale 2026-08-30; no VCS | Superseded source material → archive reference |
| bb | `investigations/card-images/deluxe/*.gif` (B5CCG card images) | B5CCG asset working dir → belongs to Babylon5CCGGameDesign scope |
| bsns5004 | University coursework PDFs (leadership/change-management texts) + `onefile-prompt.txt` | Non-project (study material) |
| TiwasTUI | Empty directory | None |
| javaciv2 (top-level) | Single `UnitTypeSmoke.java`; duplicate of `JavaProjects/javaciv2` | **Retained — believed in use by a project; operator to delete later** (2026-11-04) |
| toy-b5ccg | Single `proposal-claude-b5ccg-gui-resdesign-v1.md` | Unrealised proposal; no system |
| railroads-wt-T-0041…0045 | git worktrees of railroads (`git worktree list`); branches `task/T-0041…0045`; 138–159 commits each since 2026-10-05 | **Not separate projects** — evidence of worktree-isolated task execution at scale |
| node_modules, tmp | Tooling/scratch | Excluded |

> **Assessor note (OpenCode Pulse Alpha Free):** The author's report ended at 11 rows and called the remainder "MIXED/UNCLEAR … require further investigation". Investigation is now complete: **3 UMAWS forks (toy1/2/3), 1 agent-rules engine (cfna, live), 6 non-PM entries, 1 worktree family — fully classified; zero remain "unclear".**

> **Operator note (operator statement, relayed by assessor, 2026-11-04):** `javaciv2` (top-level) is **retained — believed to be in use by a project; the operator will delete it later**. It is not a stray to remove now. toy1/toy2 are **test-run project folders for UMAWS Fleet Launcher**, to be repurposed into full projects later — their absence of remotes is therefore intentional for now (not an accident; refresh when repurposed).

---

## 6. Comparison Matrices

> **Assessor note (OpenCode Pulse Alpha Free):** §6.1 and §6.2 are **SUPERSEDED** by §6.3 — the author's basis (unverified activity, guessed classification) is materially wrong for railroads (8th, 6.2), TiwasProjectsv3 (9th, 5.8), tcindustries, b5ccg, TiwasProjects, and Babylon5CCGGameDesign; the 12th row "(others unclear)" no longer exists — all entries are now classified. §6.1/§6.2 are retained verbatim for provenance; do not cite them. Rubric-consistent re-ranking is in §6.3; re-scored rubric totals in §7.A. The author's holistic "Overall Score (0-10)" is not reproducible from the stated rubric and has not been carried forward — see Appendix F.
>
> **Operator amendment (2026-11-04, relayed by assessor):** docs-repo's 113 untracked files are **lost work** (operator) → Process Discipline 2→1, total 8→7, High→Med. B5CCG's 2375 dirty files (incl. 44 deleted tracked `.agent/CLAIMS/B5-*.json`) are **lost work** (operator) → Discipline stays 1. toy1/toy2 = **test-run folders for Fleet Launcher, to be repurposed later**; no remotes intended now. cfna = **live project**, intended standalone (not testproject1). javaciv2 retained (believed in use). JavaProjects umbrella row kept; JavaProjects activity **kept at 1** (operator decision, 2026-11-04 — measured-commits rule applied uniformly).

### 6.1 Global Ranking (First Priority)
*Ranking based on governance, provenance, agent coordination clarity, simplicity, resilience to drift. Speed not weighted.*

| Rank | Project | Class | Governance | Provenance/Audit | Agent Coord | Simplicity | Resilience to Drift | Overall Score (0-10) | Notes |
|------|---------|-------|------------|-------------------|-------------|------------|--------------------|---------------------|-------|
| 1 | testproject1 | UMAWS/KERNEL-LITE | 9 | 9 | 9 | 6 | 8 | 8.2 | Strong reference, active, explicit rules |
| 2 | Tiwas-ttrpg-project-documentation | GOVERNANCE/DOC-CENTRIC | 9 | 9 | 7 | 7 | 8 | 8.0 | Excellent governance/provenance |
| 3 | TiwasProjects | UMAWS/KERNEL-LITE | 8 | 8 | 8 | 6 | 7 | 7.4 | Older UMAWS variant, still solid |
| 4 | tiwasfeudum | UMAWS/KERNEL-LITE | 8 | 8 | 8 | 6 | 7 | 7.4 | Similar to testproject1 [GUESS] |
| 5 | Babylon5CCGGameDesign | LEDGER/TASK-TRACKER | 7 | 7 | 7 | 6 | 7 | 6.8 | Rich patterns, complex ledger |
| 6 | tcindustries | GOVERNANCE/DOC-CENTRIC | 7 | 7 | 6 | 7 | 7 | 6.8 | Human rulings, solid governance |
| 7 | b5ccg | LEDGER/TASK-TRACKER | 7 | 6 | 6 | 6 | 6 | 6.2 | Related to B5CCG [GUESS] |
| 8 | railroads | UMAWS/KERNEL-LITE (VARIANT) | 6 | 6 | 6 | 7 | 6 | 6.2 | Different structure, goal-oriented |
| 9 | TiwasProjectsv3 | WF/ORCHESTRATOR | 6 | 5 | 6 | 6 | 6 | 5.8 | WF system [GUESS needs detail] |
| 10 | tiwas-ttrpg | GOVERNANCE/DOC-CENTRIC | 6 | 6 | 5 | 7 | 6 | 6.0 | Similar to docs repo [GUESS] |
| 11 | JavaProjects | TRADITIONAL/GUIDELINES | 6 | 3 | 2 | 9 | 6 | 5.2 | Guidelines only, not PM workflow |
| 12 | (others unclear) | UNKNOWN | - | - | - | - | - | Unknown | Need more analysis [GUESS] |

*Scores are estimates based on available evidence; many marked [GUESS]*

### 6.2 Comparison by Class (Second Priority)

**UMAWS/KERNEL-LITE Family:** testproject1 (most mature), TiwasProjects (older), tiwasfeudum (similar to testproject1), railroads (variant structure)
- testproject1 is most complete with fleet, worktree isolation focus
- TiwasProjects has kernel/ and decisions - evolution visible
- railroads different (goals/metrics/queue) - alternative design

**GOVERNANCE/DOC-CENTRIC:** Tiwas-ttrpg-project-documentation (most disciplined), tcindustries (human rulings), tiwas-ttrpg (related)
- Strong provenance, DEC tracking
- Less code/agent orchestration

**LEDGER/TASK-TRACKER:** Babylon5CCGGameDesign, b5ccg
- Strong institutional memory via patterns
- Task tracking via ledger/census

**UMAWS/KERNEL-LITE Family (assessor, complete enumeration):** testproject1 (live reference — `UMAWS-Fleet-Launcher.git`), TiwasProjects (active T-0046..T-0058 work), tiwasfeudum (Fleet-like, **no VCS** — unverifiable), railroads (goals/metrics/queue; most-active repo; extreme worktree isolation), **toy1** (fork; Fleet Launcher evidence; independent Claude assessment embedded), **toy2** (fresh scaffold; 241 tests green; zero real tasks), **toy3** (minimal Hermes-profile sandbox). Launcher-relevant signal overwhelmingly sits in testproject1 + toy1/toy2.

**GOVERNANCE/DOC-CENTRIC (assessor, complete enumeration):** Tiwas-ttrpg-project-documentation (machinery intact, **dormant since 2026-09-21**), tcindustries (clean tree; human rulings; 65 commits), tiwas-ttrpg (**superseded source**, no VCS), **cfna** (agent-rules + RD-xxxx; no commits; discipline exemplar). DEC/ruling provenance is these systems' real strength; orchestration is not.

### 6.3 Corrected Global Ranking (assessor re-score, 2026-11-04)
*Ordering uses the §7 rubric totals (corrected) as primary key and measured git activity as tiebreak; the author's unreproducible holistic 0–10 column is retired. Δ = change vs author's §6.1/§7 scores, driven by measured data. All projects in scope incl. assessor additions.*

| Rank | Project | Class | Rubric Total (corrected) | Δ vs author | Category | Measured basis (commits since 2026-10-05 / tip) |
|------|---------|-------|--------------------------|-------------|----------|------------------------------------------------|
| 1 | testproject1 | UMAWS/KERNEL-LITE | 9 | = | High | 87 / `1a5ec9b` (2026-11-03); remote UMAWS-Fleet-Launcher.git |
| 2 | toy1 *(new)* | UMAWS/KERNEL-LITE (fork) | 8 | n/a | High* | 54 / `a64b994` (2026-10-25) — *estimate; test-run folder, operator to repurpose |
| 2 | toy2 *(new)* | UMAWS/KERNEL-LITE (fresh) | 8 | n/a | High* | 46 / `47e21e6` (2026-10-25) — *estimate; test-run folder |
| 5 | JavaProjects | TRADITIONAL/GUIDELINES | 7 | −1 (Activity 2→1) | Med | 3 / `3b89e0f` (2026-10-21); BlueJ manual |
| 5 | TiwasProjects | UMAWS/KERNEL-LITE | 7 | +1 (Activity 1→2) | Med | 28 / `b9a894a` (2026-10-09) |
| 5 | tcindustries | GOVERNANCE/DOC-CENTRIC | 7 | +1 (Activity 1→2) | Med | 65 / `5a618e2` (2026-10-25); 0 dirty |
| 5 | railroads | UMAWS/KERNEL-LITE (VARIANT) | 7 | +2 (Activity 1→2, Discipline 1→2) | Med | **274** / `c23cf2f` (2026-11-04) |
| 5 | Tiwas-ttrpg-project-documentation | GOVERNANCE/DOC-CENTRIC | **7** | **−2** (Activity 2→1; Discipline 2→1, operator: lost work) | Med | **0** / `9e4bf7f` (2026-09-21) — dormant; 113 lost-work files (operator) |
| 9 | TiwasProjectsv3 | WF/ORCHESTRATOR | 6 | +1 (Activity 1→2) | Med | **209** / `6d7a964` (2026-10-28) |
| 9 | Babylon5CCGGameDesign | LEDGER/TASK-TRACKER | 6 | −1 (Activity 2→1) | Med | 4 / `73940079` (2026-10-16); 2375 dirty |
| 9 | b5ccg | LEDGER/TASK-TRACKER | 6 | +1 (Activity 1→2) | Med | 54 / `e1fd834` (2026-10-31) |
| 9 | tiwasfeudum | UMAWS/KERNEL-LITE | 6 | = | Med | **no VCS** / mtime 2026-10-31 — UNVERIFIED |
| 9 | toy3 *(new)* | UMAWS/KERNEL-LITE (minimal) | 6 | n/a | Med | 28 / `ad544e4` (2026-10-27) |
| 14 | tiwas-ttrpg | GOVERNANCE/DOC-CENTRIC | 5 | = | Med | **no VCS** / mtime 2026-08-29 — superseded |
| 14 | cfna *(new)* | AGENT-RULES/DOC-CENTRIC | 5 | n/a | Med* | 0 commits (unborn `master`) — *estimate |

\* toy1/toy2/cfna scores are **assessor estimates** (§7.A note): forks inherit Fleet discipline but project-specific goal attainment is unverified; cfna has no VCS history at all.
**Not ranked (not PM workflow systems):** tttrpg, bb, bsns5004, TiwasTUI, javaciv2, toy-b5ccg, railroads worktrees (same repo) — see §5.16.

**Reading the correction:** under measured activity, railroads and TiwasProjectsv3 leapfrog seven and nine positions respectively; the author's #2 (Tiwas-ttrpg-project-documentation) drops to **7 (Med)** after its 113 lost-work files were operator-confirmed (Discipline 2→1); the "(others unclear)" row is eliminated. Governance quality and activity are orthogonal axes — this report now separates them explicitly instead of blending them into one guessed column.

---


## 7. Success Assessment

### Rubric
As specified: Numeric 0-10 + Categories (High/Med/Low/Unknown) + Qualitative. Goal Clarity(0-2) + Goal Achievement(0-3) + Process Discipline(0-2) + Sustainability/Activity(0-2) + Coherence(0-1).

> **Assessor note (OpenCode Pulse Alpha Free):** The table below is **SUPERSEDED** by §7.A. Author's sub-scores were largely `[GUESS]` where measurement was trivially available (git presence, commit dates). §7.A corrects **Sustainability/Activity** from measured data for every repo, and **Process Discipline** only for railroads (1→2, hard-rules evidence in AGENTS.md), retaining all other author sub-scores verbatim. Restartability was author-judged qualitatively and is carried with corrected contexts. Original table retained below for provenance — do not cite.

### Assessment

| Project | Goal Clarity | Goal Achievement | Process Discipline | Sustainability/Activity | Coherence | Total (0-10) | Category | Qualitative | Restartability |
|---------|---------------|-------------------|---------------------|--------------------------|-----------|---------------|----------|-------------|---------------|
| testproject1 | 2 | 2 [GUESS] | 2 | 2 | 1 | 9 | High | Active UMAWS Fleet development, strong process | High |
| Tiwas-ttrpg-project-documentation | 2 | 2 [GUESS] | 2 | 2 | 1 | 9 | High | Excellent governance discipline | High |
| TiwasProjects | 1 [GUESS] | 1 [GUESS] | 2 | 1 [GUESS] | 1 | 6 | Med | Older UMAWS variant, less active | Med |
| tiwasfeudum | 1 [GUESS] | 1 [GUESS] | 2 | 1 [GUESS] | 1 | 6 | Med | Similar to testproject1 but unclear activity [GUESS] | Med |
| Babylon5CCGGameDesign | 1 [GUESS] | 2 [GUESS] | 1 | 2 | 1 | 7 | Med | Active with rich patterns, complex | Med-High |
| tcindustries | 2 | 1 [GUESS] | 1 | 1 [GUESS] | 1 | 6 | Med | Good governance, unclear completion | Med |
| b5ccg | 1 [GUESS] | 1 [GUESS] | 1 | 1 [GUESS] | 1 | 5 | Med | Related to B5CCG [GUESS] | Med |
| railroads | 1 [GUESS] | 1 [GUESS] | 1 | 1 [GUESS] | 1 | 5 | Med | Different variant [GUESS] | Med |
| TiwasProjectsv3 | 1 [GUESS] | 1 [GUESS] | 1 | 1 [GUESS] | 1 | 5 | Med | WF system, needs inspection [GUESS] | Med |
| tiwas-ttrpg | 1 [GUESS] | 1 [GUESS] | 1 | 1 [GUESS] | 1 | 5 | Med | Related repo [GUESS] | Med |
| JavaProjects | 2 | 2 [GUESS] | 1 | 2 | 1 | 8 | High | Guidelines system works for purpose, but not PM workflow | N/A (not PM) |
| Others | - | - | - | - | - | Unknown | Unknown | Insufficient data [GUESS] | Unknown |

*Most scores involve inference [GUESS] - goals often not explicitly stated in accessible form*

### 7.A Corrected Success Assessment (assessor re-score, 2026-11-04)
*Measured basis: commits since 2026-10-05 (30-day window to report date) for git repos; UNVERIFIED where no VCS. Changes from author: **Sustainability/Activity** re-scored for 13 repos; **Process Discipline** for railroads only (1→2). Everything else retained. Categories: author's High/Med bands retained (8–10 High, 5–7 Med). toy1/toy2/cfna = assessor estimates (forks inherit Fleet discipline; attainment unverified; cfna no VCS). Not scored: non-PM entries (§5.16).*

| Project | Goal Clarity | Goal Achievement | Process Discipline | Sustainability/Activity | Coherence | Total (0-10) | Category | Qualitative (corrected) | Restartability |
|---------|---------------|-------------------|---------------------|--------------------------|-----------|---------------|----------|--------------------------|----------------|
| testproject1 | 2 | 2 | 2 | **2** *(87)* | 1 | **9** | High | Live Fleet development; launcher repo; strong process; 142 dirty files | High |
| Tiwas-ttrpg-project-documentation | 2 | 2 | **1** *(lost work — operator; was 2)* | **1** *(0; last 2026-09-21)* | 1 | **7** | Med | Governance excellent; dormant; **113 untracked files = lost work (operator)** | High |
| toy1 *(new)* | 2 | 1 | 2 | **2** *(54)* | 1 | **8** | High* | Tier A closed CLOSING; embedded independent assessment refuted overclaims; real launcher evidence | Med-High |
| toy2 *(new)* | 2 | 1 | 2 | **2** *(46)* | 1 | **8** | High* | Tier A scaffold; 241 tests green; **zero live tasks**; sentinel 2 findings | Med-High |
| JavaProjects | 2 | 2 | 1 | **1** *(3)* | 1 | **7** | Med | Guidelines fit-for-purpose (not a PM system); BlueJ cadence skews commit count | N/A (not PM) |
| TiwasProjects | 1 | 1 | 2 | **2** *(28)* | 1 | **7** | Med | Active dev (T-0058 GUI bridge etc.); older Fleet variant, coherent | Med-High |
| tcindustries | 2 | 1 | 1 | **2** *(65; 0 dirty)* | 1 | **7** | Med | Human-ruling governance; clean tree; current audit artifacts | Med-High |
| railroads | 1 | 1 | **2** *(hard rules+gate; was 1)* | **2** *(274)* | 1 | **7** | Med | Most active repo in scope; worktree-isolated task execution; provenance-tag discipline | High |
| TiwasProjectsv3 | 1 | 1 | 1 | **2** *(209)* | 1 | **6** | Med | Very active WF orchestrator; stray root-level scrape artefacts; needs hygiene pass | Med-High |
| Babylon5CCGGameDesign | 1 | 2 | 1 | **1** *(4; 2375 dirty)* | 1 | **6** | Med | Rich 1279-file pattern library; committed activity thin; unreviewable dirty tree | Med-High |
| b5ccg | 1 | 1 | 1 | **2** *(54)* | 1 | **6** | Med | Active agent task branch; sibling of B5CCG (remote-confirmed) | Med |
| tiwasfeudum | 1 | 1 | 2 | **1** *(no VCS — UNVERIFIED)* | 1 | **6** | Med | Fleet-like layout verified; no git ⇒ activity unknowable; do not cite as "active" | Med |
| toy3 *(new)* | 1 | 1 | 1 | **2** *(28)* | 1 | **6** | Med | Minimal Hermes profile; useful floor; not a full PM surface | Med |
| tiwas-ttrpg | 1 | 1 | 1 | **1** *(no VCS; stale 2026-08-29)* | 1 | **5** | Med | Superseded source for docs repo; no verification possible | Low-Med |
| cfna *(new)* | 2 | 0 | 2 | **0** *(no commits)* | 1 | **5** | Med* | Nothing landed in VCS; discipline exemplar on paper; unscoreable in practice | Low-Med |
| Not scored | — | — | — | — | — | — | — | tttrpg, bb, bsns5004, TiwasTUI, javaciv2, toy-b5ccg, worktrees | — |

\* toy1/toy2/cfna: assessor estimates — forks inherit Fleet discipline (pmk/oracles/constitution), so Process Discipline is inherited-verified structurally, but project-specific Goal Achievement is unverified; treat totals as provisional pending a live task cycle (toy2 report itself concedes no live execution).

**Corrected success pattern:** the author's "Active ⇒ coherent" signal survives, but **committed activity and working-tree volume must be separated** — B5CCG (4 commits, 2375 dirty = lost work incl. 44 deleted tracked files, operator-confirmed) and Tiwas-ttrpg-project-documentation (0 commits, 113 untracked = lost work, operator-confirmed) both look "active" by file mtime and fail by VCS. Conversely, railroads/TiwasProjectsv3 were "needs inspection" guesses and are, by measurement, the two most active repositories in scope. **Operator-directed amendment:** docs-repo Discipline 2→1 (total 8→7, High→Med).

---


## 8. Best/Worst Aspects & Recommendations

### 8.1 testproject1 (UMAWS Fleet Kernel-lite)
**Best:** Kernel authority model, event-sourced audit trail, pmk CLI discipline, evidence storage, worktree isolation focus, oracles/gates concept  
**Worst:** Complexity, Windows-specific, kernel can be bottleneck, policy enforcement heavy  
**Rec Set 1 (Internal Logic):** Strengthen oracle gate documentation, simplify onboarding, improve conflict resolution UX  
**Rec Set 2 (Cross-System Comparison):** Adopt Tiwas-ttrpg-project-documentation's provenance clarity; add ledger-style pattern library from B5CCG for lessons learned; borrow tcindustries human ruling clarity  

### 8.2 Tiwas-ttrpg-project-documentation (Governance/Doc-Centric)
**Best:** Exceptional provenance (authority/provenance/status-model), DEC tracking, non-canonical marking, analyze-assess-record-store workflow, multi-LLM orchestration awareness  
**Worst:** Less execution/orchestration, documentation overhead, may not scale to code-heavy coordination  
**Rec Set 1 (Internal Logic):** Streamline promotion process, add lightweight task tracking  
**Rec Set 2 (Cross-System Comparison):** Adopt UMAWS event log for action tracking; add gates like testproject1; integrate evidence linking better  

### 8.3 TiwasProjects (UMAWS Older Variant)
**Best:** Early UMAWS structure, has kernel/, decisions, roles  
**Worst:** Older, less mature than testproject1, unclear current state  
**Rec Set 1 (Internal Logic):** Migrate to newer patterns or document lessons  
**Rec Set 2 (Cross-System Comparison):** Learn from testproject1's evolution; adopt better provenance  

### 8.4 Babylon5CCGGameDesign (Ledger-Based)
**Best:** Rich pattern library (.agent/PATTERNS), institutional memory, census tools, forensics  
**Worst:** Complex ledger, many agent variants create noise, collision risks  
**Rec Set 1 (Internal Logic):** Consolidate patterns, improve ledger hygiene  
**Rec Set 2 (Cross-System Comparison):** Adopt UMAWS evidence structure; add clearer gates  

### 8.5 tiwasfeudum (UMAWS Fleet-like)
**Best:** Similar structure to testproject1 (familiar), has fleet/, constitution  
**Worst:** Unclear if active/superseded [GUESS]  
**Rec Set 1 (Internal Logic):** Clarify relationship to testproject1  
**Rec Set 2 (Cross-System Comparison):** Compare structures to identify improvements  

*(Similar analysis for others - abbreviated for space, but full analysis follows same pattern)*

> **Assessor note (OpenCode Pulse Alpha Free):** The "abbreviated for space" line is no longer acceptable — full entries are required. Added below (§8.6–§8.9). Also: §8.1's recommendation set for testproject1 stands, with one amendment — **adopt toy1's embedded independent-assessment artefact** (`Assessment-of-UMAWS-completion-report-v1.1.md`) as a *required* launcher gate: any completion claim for Fleet Launcher must survive an independent LLM review before acceptance, because self-reported Fleet status repeatedly overstated reality (D-A1/D-A2/D-53/D-54/D-56; oracle Windows mismatch; Overseer profile dead on OpenRouter credits).

### 8.6 toy1 (UMAWS Fleet Fork) *(assessor addition)*
**Best:** Embedded independent completion assessment (Claude Sonnet 5.5); real launcher proposals; Fleet defect discovery (D-53/54/56); closed cleanly via pmk CLOSING
**Worst:** No remote (lost backup); completion claims refuted by own embedded review; fork drift
**Rec Set 1 (Internal Logic):** Make independent-assessment artefacts mandatory pre-CLOSING; push to remote before further work
**Rec Set 2 (Cross-System Comparison):** Export its honest-failure case-study into Fleet Launcher onboarding docs (Windows oracle mismatch as canonical "gate ran on wrong platform" example)

### 8.7 toy2 (UMAWS Fleet Fresh Init) *(assessor addition)*
**Best:** 241 tests green scaffold from clean init; sentinel found real breaks (I1 seq-84 hash mismatch; I16 AGENTS.md out-of-band edit) — integrity tooling works
**Worst:** Zero live task execution — scaffold-validated, value-unproven; no remote
**Rec Set 1:** Run one end-to-end live task before any "complete" claim; resolve sentinel findings or queue them
**Rec Set 2:** Use as the clean bring-up checklist for Fleet Launcher installs (init → tests green → first live dispatch → close)

### 8.8 toy3 (UMAWS Minimal Profile) *(assessor addition)*
**Best:** Minimal viable Fleet surface; explicit assessment-cited hard rules
**Worst:** Not a PM system (missing tasks/briefings/registry); no remote; experimental
**Rec Set 1:** Keep as diagnostic sandbox only; do not grow into production
**Rec Set 2:** Borrow minimal-AGENTS framing for Fleet Launcher's "quick start" docs

### 8.9 cfna (Agent-Rules Engine) *(assessor addition)*
**Best:** Rule-as-data with pinned sources; `RULE:` docstring contract ties case IDs to tests; ≤45-min task sizing; data-gaps protocol ("Missing data → schema + placeholder + docs/data-gaps.md")
**Worst:** Zero commits; no PM/task layer; unverifiable
**Rec Set 1:** Commit the genesis tree; add RD-xxxx index; wire a single test to one RULE case
**Rec Set 2:** Adopt the RULE-docstring ↔ test contract for Fleet Launcher's oracle gates (gate references a rule ID; test names it)

---


## 9. Future-Proof Systematic Framework

### Framework Components
1. **Discovery Phase**: Inventory files, git history, PM indicators
2. **Classification**: Map to classes (UMAWS/LEDGER/GOVERNANCE/WF/TRADITIONAL/HYBRID)
3. **Component Analysis**: Apply template (governance/provenance/agents/tasks/gates/memory)
4. **Goal Extraction**: Find explicit goals, infer if needed with confidence
5. **Outcome Assessment**: Find activity/completion signals, be conservative
6. **Success Scoring**: Apply rubric consistently
7. **Comparison**: Global then by class
8. **Recommendations**: Dual sets (internal + cross-system)
9. **Documentation**: LLM-digestible output with guesses flagged

### Principles
- Conservative inference, flag all guesses
- Evidence-based where possible
- Internal consistency in assessment
- LLM-consumable structure (tables, clear sections)
- Reusable template
- Provenance always tracked

---

## 10. Basis for UMAWS Fleet Launcher Development

### Lessons from testproject1 (Primary Reference)
- Kernel authority + pmk CLI works but needs good UX
- Event log is powerful for audit
- Evidence storage critical
- Worktree isolation important for multi-agent safety
- Gates/oracles enforce quality

### Improvements from Other Systems
- **From Tiwas-ttrpg-project-documentation**: Better provenance docs, clearer non-canonical marking, analyze-assess-record-store pattern
- **From B5CCG**: Pattern library for lessons learned, forensics capabilities
- **From tcindustries**: Clear human ruling mechanism
- **From railroads variant**: Goal/metric orientation alternative worth considering

### Recommendations for UMAWS Fleet Launcher
1. **Governance**: Keep kernel authority but make it more transparent
2. **Provenance**: Adopt explicit provenance.md style + event log
3. **Patterns**: Add pattern library like B5CCG
4. **Gates**: Make oracle gates more discoverable
5. **Simplicity**: Balance power with learnability
6. **Multi-version awareness**: Track system version like analyzing these variants

### 10.A Assessor Amendment — Missed Launcher-Critical Evidence (2026-11-04)
*The author's §10 missed the most direct evidence about Fleet Launcher's own development. All of the following is verified inside `C:\temp\projects\toy1` and `toy2` unless noted. The author's six recommendations stand but are insufficient without these.*

**Evidence the author did not see:**
- **E1 — Independent assessment exists and refutes self-reports.** `toy1/Assessment-of-UMAWS-completion-report-v1.1.md` (Claude Sonnet 5.5, 2026-10-24): Hermes's completion report v1.1 "should not be accepted as it stands" — it repeats 1.0.0 errors under a "corrected" label. Verified example: T-0003's "failure" was a **POSIX oracle (`test -f … && grep -q …`) executed on Windows** — the SHA-256 of stderr equals the hash of `'test' is not recognized…`; the worker *did* create `pi-test.txt`. **Fleet's own gate ran on the wrong platform and the failure was misattributed to the agent.**
- **E2 — Overseer cannot plan today.** `opencode-strongest` uses an OpenRouter model on an account that "never purchased credits"; "Rate limit exceeded" log noise masked "Insufficient credits". **One-click planning is blocked until the default profile is repointed** — a product-level launcher blocker, not a bug.
- **E3 — Provider-call honesty.** Console runs A/B **did** fire real provider calls (4 × `OVERSEER_WOKEN … started: true` in `opencode-strongest` log; all failed rate-limit/insufficient-credits) while Hermes's report claimed "no AGENT_STARTED and no provider call … both used the fake CLI". Wake interval ~2–3.5 min vs specified 10 min.
- **E4 — Forks prove the scaffold is reproducible.** toy2 cold-start reached Tier A with **241 green tests** and **2 sentinel findings** (I1 seq-84 hash mismatch; I16 AGENTS.md out-of-band edit) — the Fleet's integrity tooling works on a fresh tree.
- **E5 — Launcher artefacts exist.** `toy1/proposal-claude-umaws-fleet-launcher-v1.md`, `proposal-claude-umaws-gateway-*.md`, `proposal-claude-llm-gateway-v1-1.md`, `LLM-Prompt-Launcher-App.py`, `prompts.json` — design intent for the launcher is documented and unassessed in this report.
- **E6 — Repo identity.** testproject1's remote **is** `github.com/tiwaking-ops/UMAWS-Fleet-Launcher.git`; toy1/toy2/toy3 have **no remotes** — the launcher's live history and both forks are unbacked-up.
- **E7 — railroads worktree pattern.** Five persistent `task/T-00xx` worktrees, each 138–159 commits, executing in parallel with clean gate discipline — **proof the Fleet's worktree-isolation thesis works at scale; also a collision/management testbench the launcher should absorb.**

**Assessor recommendations A1–A6 (extend, not replace, author's 1–6):**
- **A1 — Platform-aware oracle verification is non-negotiable.** Every gate must self-check its platform (e.g. refuse POSIX builtins on Windows; `python -c` one-liners instead — testproject1 already migrated T-0003 this way). Ship the T-0003 failure as the canonical onboarding postmortem.
- **A2 — No launcher release may self-certify.** Require an **independent LLM assessment artifact** (model ≠ implementer) attached to every completion claim — toy1's embedded assessment caught overclaims the implementing agent could not.
- **A3 — Profile health preflight.** Launcher must preflight the active profile (auth, quota/credits, model reachability) and **fail loudly before one-click planning** (E2); show the exact blocker with a fix path.
- **A4 — Backup before autonomy.** First-run flow must warn when `.pm/`/git remote is absent (E6) — unbacked-up autonomous runs are unrecoverable.
- **A5 — Digest the forks.** Compare testproject1 ↔ toy1 ↔ toy2 `.pm/` and policies to extract the **minimal viable Fleet** and the **fork-drift delta**; the launcher should ship versioned, comparable configs, not a singleton layout.
- **A6 — Sentinel gates in the installer.** toy2's two sentinel findings (I1/I16) are exactly the failure classes an unattended installer can introduce; Fleet Launcher must run sentinel at init and surface findings as hard blockers or explicit acknowledgements.

---

## 11. Guesses & Inferences Log

| Item | Project | Type | Rationale | Confidence | Needs Verification |
|------|---------|------|-----------|------------|-------------------|
| Goals inferred where not explicit | All | Inference | AGENTS/README examined | Low-Med | Check original intent |
| tiwas-ttrpg related to docs repo | tiwas-ttrpg | Guess | Similar structure | Med | Compare git remotes/history |
| b5ccg related to Babylon5CCGGameDesign | b5ccg | Guess | Naming/patterns | Med | Check |
| tiwasfeudum is UMAWS Fleet-like | tiwasfeudum | Guess | .pm structure matches | Med | Check activity |
| TiwasProjects older UMAWS variant | TiwasProjects | Guess | Structure evolution | Med | Date analysis |
| railroads variant classification | railroads | Guess | Different .pm structure | Med | Deeper analysis |
| Activity levels inferred | Many | Inference | Git log dates | Med | Check actual usage |
| Success scores involve inference | Most | Inference | Goals unclear | Low-Med | Get stated goals |
| Some projects stalled/abandoned | Several | Guess | Old dates/no recent commits | Med | Confirm status |

> **Assessor note (OpenCode Pulse Alpha Free) — Log resolutions (measured 2026-11-04):** the rows above are retained as the author's log; each is resolved here. "RESOLVED" = measured, not re-inferred.

| # | Author log item | Assessor resolution | Evidence |
|---|-----------------|--------------------|----------|
| R1 | Goals inferred where not explicit | Still Low-Med; not upgraded — but scoring no longer leans on it (Sustainability measured instead) | — |
| R2 | tiwas-ttrpg related to docs repo | **RESOLVED — yes** (same author/ecosystem; `_consolidation/` supersession; shared file sets) — and it is **not a git repo** | dir listing; mtimes |
| R3 | b5ccg related to Babylon5CCGGameDesign | **RESOLVED — confirmed sibling repos** (`tiwaking-ops/b5ccg.git` vs `tiwaking-ops/Babylon5CCGGameDesign.git`) | `git remote get-url origin` |
| R4 | tiwasfeudum is UMAWS Fleet-like | Structure **confirmed** (Fleet `.pm/`); activity **UNVERIFIED — no `.git`** | `.pm/` listing; no .git dir |
| R5 | TiwasProjects older UMAWS variant | **Confirmed**; and it is **actively developed** (28 commits since 2026-10-05; T-0058 GUI bridge) — "less active" refuted | git log |
| R6 | railroads variant classification | **Resolved — coherent goal/metric PM system**, not a mislabelled kernel fork; **most active repo in scope** (274) | AGENTS.md; worktree list |
| R7 | Activity levels inferred | **Superseded by measurement** (§4, §6.3, §7.A, Appendix D) — author's activity guesses wrong for 10 of 14 scored repos | Appendix D |
| R8 | Success scores involve inference | Narrowed — only Sustainability was re-scored by measurement; rest remain author estimates | §7.A |
| R9 | Some projects stalled/abandoned | **Two confirmed:** docs-repo (dormant; **lost work, operator-confirmed**) & tiwas-ttrpg (no VCS, stale Aug); B5CCG = **lost work, operator-confirmed** (44 tracked deletions); none are "abandoned" per se | git log; operator 2026-11-04 |
| R10 | "12 project directories" / "others unclear" | **Refuted** — 11 author rows + 11 assessor additions; zero "unclear" remain | §4, §5.16, Appendix E |
| R11 | `exhaustive: true` (metadata) | **Refuted** — metadata corrected to `false` | §2 |
| R12 | "Active (recent commits)" docs-repo | **Refuted** — dormant since 2026-09-21 | git log |
| R13 | B5CCG "Active" | **Refuted (committed)** — 4 commits; intense *uncommitted* activity (2375 dirty) | git log; status --porcelain |
| R14 | Java 6 hard requirement; census.ps1/check_claims.ps1; HD-TST-01; DEC-141→149; template file exists | **All VERIFIED** — not guesses | file reads; git log |
| R15 | Template standalone file referenced | **VERIFIED** — `pm-workflow-analysis-template-v1.md` (4,482 B) exists | docs/ listing |

---

## 12. Appendices

### Appendix A: Git History Snapshots (Key Projects)
- testproject1: Recent commits show fleet work, incident reports, evidence work
- Tiwas-ttrpg-project-documentation: DEC tracking, storage workflow
- Babylon5CCGGameDesign: Active with pattern work
- TiwasProjects: Older (Oct 2026)
- railroads: Recent activity visible

> **Assessor note (OpenCode Pulse Alpha Free) — measured snapshot (2026-11-04, window since 2026-10-05):** author's bullet list above is retained but superseded by this table. Tip = `git log -1`; Dirty = `git status --porcelain` line count.

| Project | Commits ≥ 2026-10-05 | Tip | Dirty | Remote |
|---------|---------------------|-----|-------|--------|
| railroads | **274** | `c23cf2f` 2026-11-04 | 50 | none |
| railroads-wt-T-0041…0045 (worktrees of railroads) | 138 / 138 / 138 / 138 / 159 | `9afacc0` / `35182d9` / `c68074f` / `bfeb652` / `7766f67` | 0 | n/a (same repo) |
| TiwasProjectsv3 | **209** | `6d7a964` 2026-10-28 (`task/T-0161`) | 13 | tiwaking-ops/TiwasProjectsv3.git |
| testproject1 | 87 | `1a5ec9b` 2026-11-03 | 142 | tiwaking-ops/UMAWS-Fleet-Launcher.git |
| tcindustries | 65 | `5a618e2` 2026-10-25 | **0** | tiwaking-ops/TCIndustries.git |
| b5ccg | 54 | `e1fd834` 2026-10-31 | 1081 | tiwaking-ops/b5ccg.git |
| toy1 | 54 | `a64b994` 2026-10-25 | 3 | none |
| toy2 | 46 | `47e21e6` 2026-10-25 | 4 | none |
| TiwasProjects | 28 | `b9a894a` 2026-10-09 | 152 | tiwaking-ops/TiwasProjects.git |
| toy3 | 28 | `ad544e4` 2026-10-27 | 6 | none |
| JavaProjects | 3 | `3b89e0f` 2026-10-21 | 14 | tiwaking-ops/JavaProjects.git |
| Babylon5CCGGameDesign | 4 | `73940079` 2026-10-16 | **2375** | tiwaking-ops/Babylon5CCGGameDesign.git |
| tiwas-ttrpg-project-documentation | **0** | `9e4bf7f` 2026-09-21 | 113 | tiwaking-ops/Tiwas-ttrpg-project-documentation.git |
| cfna | **0 (unborn `master`)** | — | 3 | none configured |
| tiwas-ttrpg | n/a (no .git) | — | — | — |
| tiwasfeudum | n/a (no .git) | — | — | — |
| tttrpg, bb, bsns5004, TiwasTUI, javaciv2, toy-b5ccg | n/a (no .git) | — | — | — |

### Appendix B: File System Indicators
UMAWS indicators: .pm/ with events/tasks/registry, pmk, kernel, constitution.md, policy.toml  
Governance indicators: governance/ dir, DEC-XXX, authority/provenance.md  
Ledger indicators: B5-XXX, census scripts, .agent/PATTERNS  

> **Assessor note (OpenCode Pulse Alpha Free) — additional verified indicators:**
> - **Agent-rules indicator:** `AGENTS.md` with hard rules + pinned sources + `RULE:`-docstring ↔ test contract (cfna); provenance tags `SOURCED/INFERRED/DESIGNED/UNKNOWN` (railroads); sentinel findings classes I1/I16 (toy2).
> - **Fork indicator:** identical `.pm/` trees across testproject1/toy1/toy2/toy3 (constitution.md + policy.toml + pins.sha256 + `.kernel.lock.lock`) plus root-level `proposal-claude-*.md` clusters (toy1: 4 launcher proposals).
> - **Supersession indicator:** `_consolidation/` with `consolidation-plan.md` + `decision-register.md` (tiwas-ttrpg → docs repo); loose drafts at repo root (tttrpg).
> - **Uncommitted-work indicator:** `?? `-prefixed entries dominating `git status --porcelain` (docs-repo 113, B5CCG 2375 incl. `TASK_LEDGER.md.b5-3868-pre`, `DECISIONS.fixed.md` backups) — flag for hygiene review, not activity credit.
> - **Worktree-fleet indicator:** `git worktree list` showing `task/T-00xx` registered worktrees outside the main tree (railroads: 5).

### Appendix C: Recommendations Summary
See Section 8 for detailed recommendations. Key themes: provenance, evidence, gates, patterns, human oversight.

> **Assessor note (OpenCode Pulse Alpha Free):** Updated themes — provenance **with independent verification**, evidence, gates **that run on the right platform**, patterns, human oversight, **measured activity**, and **backup-before-autonomy**. See §10.A (A1–A6) and §8.6–§8.9. The author's themes remain valid but are no longer sufficient or correctly weighted.

### Appendix D: Assessor Verification Log (OpenCode Pulse Alpha Free, 2026-11-04)
*Exact commands run; reproduce any cell. For each repo dir `D`:* `git -C D rev-parse --abbrev-ref HEAD` · `git -C D remote get-url origin` · `git -C D log -1 --format="%ci %h %s"` · `git -C D log --since=2026-10-05 --oneline | wc -l` · `git -C D status --porcelain | wc -l` · `git -C D worktree list` · directory listings (`Get-ChildItem`) · targeted content reads (AGENTS.md, governance files, key reports).

Key raw outputs (verbatim excerpts):
- `testproject1` → HEAD `main`; remote `https://github.com/tiwaking-ops/UMAWS-Fleet-Launcher.git`; tip `1a5ec9b` 2026-11-03; 87 commits; 142 dirty.
- `railroads` → `main`; **no remote**; tip `c23cf2f` 2026-11-04; **274**; 50 dirty; worktree list → main + T-0041…T-0045 (branches task/T-0041…T-0045); each worktree 138–159 commits.
- `TiwasProjectsv3` → `task/T-0161`; remote `.../TiwasProjectsv3.git`; tip `6d7a964` 2026-10-28; **209**; 13 dirty.
- `Tiwas-ttrpg-project-documentation` → `main`; remote `.../Tiwas-ttrpg-project-documentation.git`; tip `9e4bf7f` 2026-09-21; **0**; 113 dirty (mostly `?? ` untracked).
- `Babylon5CCGGameDesign` → `main`; remote `.../Babylon5CCGGameDesign.git`; tip `73940079` 2026-10-16; 4; **2375 dirty**; `.agent/PATTERNS` file count = **1279**; `census.ps1`, `check_claims.ps1` present (root).
- `b5ccg` → `task/opencode-laguna-s-2-1-01-B5-0106`; remote `.../b5ccg.git`; tip `e1fd834` 2026-10-31; 54; 1081 dirty.
- `tcindustries` → `main`; remote `.../TCIndustries.git`; tip `5a618e2` 2026-10-25; 65; **0 dirty**; `governance/` files as listed in §5.6.
- `TiwasProjects` → `main`; remote `.../TiwasProjects.git`; tip `b9a894a` 2026-10-09; 28; 152 dirty.
- `JavaProjects` → `main`; remote `.../JavaProjects.git`; tip `3b89e0f` 2026-10-21; 3; 14 dirty; Java 6 hard requirement at AGENTS.md:21–27.
- `toy1/toy2/toy3` → `main`; **no remotes**; tips `a64b994` / `47e21e6` / `ad544e4`; 54 / 46 / 28 commits; `.pm/` full/full/minimal; toy2 = 241 tests green, sentinel I1/I16; toy1 closed CLOSING with embedded Claude Sonnet 5.5 assessment (verdict: report not acceptable).
- `tiwas-ttrpg`, `tiwasfeudum`, `tttrpg`, `bb`, `bsns5004`, `TiwasTUI`, `javaciv2`, `toy-b5ccg` → **no `.git`** (or empty); structures listed in §5.3/§5.11/§5.16.
- `cfna` → git present, branch shows `HEAD`/unborn `master`; `git log` → "fatal: your current branch 'master' does not have any commits yet"; 3 untracked files; docs/decisions + docs/rules + AGENTS.md ("CNA digital edition").
- `node_modules/`, `tmp/` → excluded as non-project.
- Remotes use one owner: `github.com/tiwaking-ops/*`.

### Appendix E: Missed-Projects Register & Exclusion Rationale
| # | Entry | Class | PM? | Why it matters / disposition |
|---|-------|-------|-----|------------------------------|
| 1 | toy1 | UMAWS/KERNEL-LITE fork | Yes | Launcher evidence; embedded independent assessment; Fleet defect discovery → feeds §10.A A2/A5; **test-run folder, repurpose later** (operator) |
| 2 | toy2 | UMAWS/KERNEL-LITE fresh | Yes | Reproducible Tier-A scaffold; sentinel works on cold start → §10.A A6; **test-run folder** (operator) |
| 3 | toy3 | UMAWS/KERNEL-LITE minimal | Partial | Diagnostic floor for minimal viable Fleet config → §10.A A5 |
| 4 | cfna | AGENT-RULES/DOC-CENTRIC | No | Discipline exemplar (rule↔test contract) → §8.9/§10.A gates; **live project** (operator); standalone folder intended |
| 5 | railroads-wt-T-0041…0045 | worktrees of railroads | n/a | Worktree isolation at scale; same repo; must not double count |
| 6 | tttrpg | loose TTRPG drafts | No | Superseded by tiwas-ttrpg → docs repo; archive |
| 7 | bb | B5CCG card images | No | Belongs in B5CCG investigations scope |
| 8 | bsns5004 | coursework PDFs | No | Non-project |
| 9 | TiwasTUI | empty | No | None |
| 10 | javaciv2 (top-level) | single .java | No | **Retained — believed in use by a project; operator deletes later** (2026-11-04) |
| 11 | toy-b5ccg | one proposal md | No | Unrealised; no system |

### Appendix F: Re-scoring Methodology & Delta Register
- **Rubric (unchanged):** Clarity 0–2 + Achievement 0–3 + Discipline 0–2 + Sustainability 0–2 + Coherence 0–1 = 10. Category bands: 8–10 High, 5–7 Med (author's implied bands).
- **What changed:** Sustainability/Activity was re-scored for **every** entry from measured git data (0 = no commits/no VCS; 1 = minimal/thin; 2 = genuinely active ≥ ~1 commit/week pace). **Process Discipline** corrected for railroads only (1→2: operator-owned read-only rules, gate enforcement, provenance tags, task cards — AGENTS.md hard rules 1–3 + worktree practice). All other author sub-scores retained verbatim — the assessor does not re-litigate judgement it cannot measure.
- **Ordering:** §6.3 ranks by corrected rubric total, tiebroken by measured activity. The author's holistic "Overall Score (0-10)" column was **retired**, not corrected: it correlates with nothing the report specifies and was irreproducible; §7.A reproduces from the rubric alone.
- **Delta register (author → assessor):** Sustainability — docs-repo 2→1; B5CCG 2→1; JavaProjects 2→1; TiwasProjects 1→2; tcindustries 1→2; b5ccg 1→2; railroads 1→2; TiwasProjectsv3 1→2; testproject1 = 2; tiwas-ttrpg = 1 (no VCS); tiwasfeudum = 1 (no VCS). Discipline — railroads 1→2 (assessor); **docs-repo 2→1 (operator: lost work)**. Totals: docs-repo **9→7** (was reported as 8 pre-operator-amendment); JavaProjects 8→7; TiwasProjects 6→7; tcindustries 6→7; railroads 5→7; TiwasProjectsv3 5→6; b5ccg 5→6; B5CCG 7→6. New: toy1 8, toy2 8, toy3 6, cfna 5. Removed: "(others unclear)" row.
- **Operator amendments (2026-11-04):** see §13.6 O1–O7 and C-21…C-26. Operator statements are first-class provenance — recorded as operator, not LLM measurement; where operator and VCS conflict, VCS wins for "what landed" and operator wins for "what was intended" (e.g., cfna's live intent vs its 0 commits). JavaProjects activity **kept at 1** (operator decision, 2026-11-04 — measured-commits rule applied uniformly; stays 7 / Med; C-26).
- **Confidence:** High for measured deltas; Medium for category assignments; Low for toy1/toy2/cfna absolute totals (marked estimates). No change was made on vibes — every Δ traces to an Appendix D command output.

---

## 13. Assessment Addendum & Corrections Register (assessor_llm: OpenCode Pulse Alpha Free)

**Assessor:** OpenCode Pulse Alpha Free · **Date:** 2026-11-04 · **Scope:** full report, all sections · **Independence:** author_llm = opencode kilo/stealth/glyph-cluster (unchanged); this section and all `Assessor note` blocks are assessor work product, never merged into authorship.

### 13.1 Verdict
The author's **method was sound in spirit** (flag guesses, compare systems, extract launcher lessons) but **execution failed verification**: it sampled shallowly, then scored guessed activity as fact. After corrections, the report's shape survives (class taxonomy, template, rubric), its **coverage does not** (11 of ~22 substantive directories; 11 entries omitted — including the three most launcher-relevant forks), and its **rankings were materially wrong** (two of the three most active repos were bench-warming at #8 and #9 with guessed `1`s). Corrected report is usable for Fleet Launcher planning; the uncorrected v1 would have misdirected it.

### 13.2 Corrections Register
| ID | Location | Author claim | Assessor correction | Basis |
|----|----------|--------------|--------------------|-------|
| C-01 | §1, §4 | "12 project directories" | 11 listed; **22 assessed entries** after additions; `node_modules`/`tmp` excluded | §4 table; Appendix D/E |
| C-02 | §4, §5.3, §5.11 | tiwas-ttrpg / tiwasfeudum git "Unknown/[GUESS]" | **Neither is a git repo**; activity UNVERIFIED | filesystem; git absence |
| C-03 | §5.2, §6.1, §7 | docs-repo "Active (recent commits)", Activity 2 | **Dormant**: 0 commits since 2026-10-05; last 2026-09-21; 113 mostly-untracked files | git log / status |
| C-04 | §5.10, §6.1, §7, §6.3 | railroads #8, 6.2, Activity 1 [GUESS] | **#5 (7)**, Activity 1→2, **Discipline 1→2**; 274 commits; most-active repo | Appendix D |
| C-05 | §5.8, §6.1, §7 | TiwasProjectsv3 "needs inspection", Activity 1 | **209 commits**, tip `task/T-0161`; Activity 1→2; #9→6 | Appendix D |
| C-06 | §1, §6.1 | "MIXED/UNCLEAR … require further investigation"; 12th row "(others unclear)" | **Withdrawn** — all entries classified (§5.16); row deleted from rankings | full enumeration |
| C-07 | §5.9, §7 | TiwasProjects "less active / unclear", Activity 1 | **Active**: 28 commits (T-0046…T-0058); Activity 1→2; #7, 7 | git log |
| C-08 | §5.6, §7 | tcindustries Activity 1 [GUESS] | **65 commits; 0 dirty**; Activity 1→2; #7, 7 | Appendix D |
| C-09 | §5.5, §7 | b5ccg "Related [GUESS]", Activity 1 | **Remote confirms sibling** (`tiwaking-ops/b5ccg.git`); 54 commits; Activity 1→2; 6 | git remote / log |
| C-10 | §5.4, §7 | B5CCG "Active", Activity 2 | **4 commits; 2375 dirty** — thin committed activity, huge uncommitted volume; Activity 2→1; 6 | git log / status |
| C-11 | §5.7, §7, §4 | JavaProjects Activity 2 | 3 commits (BlueJ manual); Activity 2→1; 7; **12+ sub-projects** noted | Appendix D |
| C-12 | §2 | `exhaustive: true` | **false** (11 omissions) | §4/E |
| C-13 | §6.1/§7 vs §6.3/§7.A | Overall Score column irreproducible | **Retired**; re-ranked on rubric totals (tiebreak: measured activity) | Appendix F |
| C-14 | §4, §5, §6, §7, §8, §10, §11 | 11 author projects only | **+11 entries**: toy1, toy2, toy3, cfna, tttrpg, bb, bsns5004, TiwasTUI, javaciv2, toy-b5ccg, railroads worktrees (same repo, not double-counted) | §5.12–§5.16 |
| C-15 | §10 | Launcher recommendations omit launcher's own forks | **§10.A A1–A6 added** (platform-true oracles; independent-assessment gate; profile preflight; backup-before-autonomy; digest forks; sentinel in installer) | toy1/toy2 artefacts |
| C-16 | §12 A | Appendix A author bullets stale | Measured table replaces reliance; original retained, marked superseded | Appendix D |
| C-17 | §11 | Guesses unresolved | **R1–R15 resolutions** appended | §11 |
| C-18 | footer/metadata | Assessor TBD | **OpenCode Pulse Alpha Free**; provenance updated (§2) | — |
| C-19 | §8 | "abbreviated for space" | **§8.6–§8.9 added** (toy1/toy2/toy3/cfna) | — |
| C-20 | §5.15/§7.A | *(author had no concept)* | **cfna** classified: agent-rules engine, 0 commits, discipline exemplar, not PM | — |
| C-21 | §5.2, §6.3, §7.A (operator-directed) | docs-repo Discipline 2, total 8, High | **Discipline 2→1** (113 untracked = **lost work**, operator), total **7**, **Med** | operator statement; git status (all `??`) |
| C-22 | §5.4, §5.2 (operator-confirmed) | B5CCG dirty tree read as "uncommitted WIP" | **Lost work** (operator): 44 tracked deletions (`.agent/CLAIMS/B5-*.json`), 85 modified, 2246 untracked — review-blocked; Discipline stays 1 | operator statement; git status |
| C-23 | §5.12/§5.13, §13.4 (operator) | toy1/toy2 = forks to back up | **Test-run folders for Fleet Launcher**; operator will **repurpose later**; no remotes intended now | operator statement |
| C-24 | §5.15, §4, §5.16 (operator) | cfna = genesis scratchpad | **Live project**; originally meant for its own folder; LLM-suggested testproject1 placement superseded | operator statement |
| C-25 | §5.16, §4 (operator) | javaciv2 stray duplicate → delete | **Retained — believed in use by a project; operator deletes later** | operator statement |
| C-26 | §4, §6.3, §7.A, §13.4-5, §13.6 O5 (operator) | JavaProjects Activity reweighting unclear | **DECIDED: keep 1** (measured-commits rule, uniform) — total stays 7 / Med | operator statement 2026-11-04 |

### 13.3 What the report gets right (kept)
Class taxonomy usage (UMAWS/GOVERNANCE/LEDGER/WF/TRADITIONAL); PM-component template philosophy; flag-your-guesses discipline; dual recommendation sets (internal + cross-system); provenance-first stance; "Java 6 hard requirement"; census.ps1/check_claims.ps1; HD-TST-01; DEC-141→149; template file reference — **all verified accurate**.

### 13.4 Operator responses to open questions (2026-11-04)
1. **toy1/toy2 remotes — DECIDED (no).** Per operator: these were **test-run project folders for UMAWS Fleet Launcher**; they will be **repurposed into full projects later**. No `git init`/push now; revisit when repurposed.
2. **B5CCG & docs-repo dirty trees — RESOLVED: lost work (both).** docs-repo Discipline 2→1 (total 8→7, High→Med, §13.6 O2); B5CCG Discipline stays at 1 (already failed); both flagged as **confirmed work loss**, not deferred WIP. Recovery options (optional): trawl `.agent/` quarantine/backups for deleted `B5-*.json` CLAIMS; accept loss otherwise.
3. **cfna — RESOLVED: live project.** Originally intended for its own top-level folder; an LLM's suggestion to run it inside testproject1 is superseded. cfna stays standalone; nothing about this report changes that intent; still 0 commits in VCS — first commit is the open milestone.
4. **JavaProjects umbrella row — DECIDED: keep.** All sub-projects share the same PM system; no per-subproject rows.
5. **JavaProjects Activity = 1 — DECIDED (keep 1).** Operator initially unsure ("I dont know what this is"); after the term was explained, operator chose the uniform measured-commits rule: **3 commits measured ⇒ Activity 1; total stays 7 (Med)**. No reweighting; consistent with all other repos.
6. **javaciv2 (top-level) — DECIDED: keep for now.** Operator believes it is in use by a project; will delete later. Not a stray; do not remove.

### 13.5 Sign-off
Assessed with live filesystem + git evidence on 2026-11-04. Every Δ traces to Appendix D. Author retains editorial authority over their sections; this addendum is binding for any citation of v1 after 2026-11-04.

**Assessor: OpenCode Pulse Alpha Free · 2026-11-04**

### 13.6 Operator Amendments (operator statements, relayed by assessor, 2026-11-04)
Provenance: statements made by the operator (project owner, tiwaking-ops) in response to §13.4/questions; relayed verbatim in intent by the assessor; **not** LLM-verified facts beyond the git measurements cited.

| ID | Subject | Operator statement | Report impact |
|----|---------|--------------------|----------------|
| O1 | toy1/toy2 remotes | Test-run folders for UMAWS Fleet Launcher; repurpose into full projects later | No push now; §4/§5 annotated; backup risk **accepted, knowingly** |
| O2 | docs-repo dirty tree | **Lost work** | **Discipline 2→1; total 8→7; High→Med** (§7.A, §6.3, C-21) |
| O3 | B5CCG dirty tree | **Lost work** (incl. 44 tracked deletions) | Discipline stays 1; §5.4 amended; review-blocked; C-22 |
| O4 | cfna | Live project; own folder intended; LLM-suggested testproject1 placement superseded | §5.15 amended; still 0 commits; C-24 |
| O5 | JavaProjects Activity | **DECIDED (2026-11-04): keep 1** — operator confirmed the uniform measured-commits rule after the term was explained | §4/§7.A unchanged; stays 7 (Med); C-26 |
| O6 | javaciv2 (top-level) | Retained; believed in use; delete later | §4/§5.16/Appendix E amended; not deleted; C-25 |
| O7 | JavaProjects umbrella | All sub-projects share one PM system — keep umbrella row | §4/§5.7; no per-subproject rows |

---

**End of Report**

*Author: opencode kilo/stealth/glyph-cluster | Assessor: OpenCode Pulse Alpha Free (2026-11-04) | Corrections delineated in §4–§12 + this Section 13; nothing overwritten silently.*  
