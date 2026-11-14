# PM Workflow Analysis Template v1

**Purpose**: Systematic template for analyzing and evaluating project management workflow systems. Designed for LLM consumption and cross-project comparison.

**Author**: opencode kilo/stealth/glyph-cluster  
**Version**: 1.0  
**Date**: 2026-11-04  

---

## 1. Project Identity & Metadata
- [ ] **Project Name**: (folder name)
- [ ] **Full Path**: 
- [ ] **Git Repo**: (yes/no, remote if any)
- [ ] **First Commit Date** (from git log): 
- [ ] **Last Commit Date** (from git log): 
- [ ] **Total Commits** (approx): 
- [ ] **Primary Language(s)**: 
- [ ] **Project Type/Goal** (from README/AGENTS/docs): 
- [ ] **Stated Goals** (explicit): 
- [ ] **Inferred Goals** (if not explicit, mark as GUESS): 
- [ ] **Status** (Active/Stalled/Abandoned/Unknown) - with rationale
- [ ] **UMAWS-like?** (yes/no/partial, version clues)

## 2. PM System Classification
- [ ] **Primary Class**: (UMAWS/KERNEL-LITE | LEDGER/TASK-TRACKER | GOVERNANCE/DOC-CENTRIC | WF/ORCHESTRATOR | HYBRID | TRADITIONAL/GUIDELINES | OTHER/UNKNOWN)
- [ ] **Sub-class/Variant**: 
- [ ] **Evidence Files/Dirs**: (.pm/, pmk, kernel, ledger, governance/, events/, tasks/, wf/, etc.)
- [ ] **Version Clues** (file dates, git history, naming): 
- [ ] **Maturity** (Experimental/Developing/Mature/Unclear)

## 3. Governance
- [ ] **Authority Model**: (human-override, kernel-authoritative, oracle-driven, consensus, undefined)
- [ ] **Governance Docs**: (AGENTS.md, constitution.md, governance/*.md, etc.)
- [ ] **Rules/Policies**: (policy.yaml/toml/md)
- [ ] **Decision Tracking**: (DEC-XXX, decisions/, ledger rows)
- [ ] **Human Rulings**: (present/absent)
- [ ] **Escalation Mechanism**: 

## 4. Provenance & Auditability
- [ ] **Provenance Tracking**: (explicit mechanism or none)
- [ ] **Author/Assessor Recording**: 
- [ ] **Event Log / Audit Trail**: (immutable log, append-only)
- [ ] **Evidence Storage**: (evidence/ dirs, linked artifacts)
- [ ] **Hashing/Integrity**: (pins.sha256, checksums)
- [ ] **Traceability** (task->evidence->decision): 

## 5. Agent Management
- [ ] **Agent Coordination**: (roles, fleet, registry)
- [ ] **Task Assignment/Claiming**: 
- [ ] **Multi-Agent Support**: 
- [ ] **Agent Instructions/Briefings**: (briefings/)
- [ ] **Worktree/Isolation**: 
- [ ] **Handoffs**: 

## 6. Task/Work Tracking
- [ ] **Task Model**: (tasks/ files, queue, ledger rows, issues)
- [ ] **States/Lifecycle**: 
- [ ] **Dependencies**: 
- [ ] **Prioritization**: 
- [ ] **Completion Tracking**: 
- [ ] **Blocked/Conflicts**: (conflicts/)

## 7. Oracles/Gates/Verification
- [ ] **Gate Mechanism**: (oracles decide, gate_cmd, tests)
- [ ] **Verification Steps**: 
- [ ] **Conformance Checks**: 
- [ ] **Automated Validation**: 

## 8. Artifacts & Memory
- [ ] **Context/Memory**: (memory/, context-snapshots/)
- [ ] **Views/Projections**: 
- [ ] **Canonical Artifacts**: 
- [ ] **Investigations/Proposals**: 
- [ ] **Knowledge Base**: 

## 9. Success Assessment
- [ ] **Rubric Applied**: (see Section 10)
- [ ] **Numeric Score (0-10)**: 
- [ ] **Category**: (High/Med/Low/Unknown)
- [ ] **Qualitative Assessment**: 
- [ ] **Goals Achievement** (vs stated/inferred): 
- [ ] **Activity Level**: (commits/tasks/recent activity)
- [ ] **Completion Indicators**: 
- [ ] **Stalled/Abandoned Evidence**: 
- [ ] **Restartability** (for stalled): (High/Med/Low/Unknown)

## 10. Success Rubric (Standard)
**Scoring 0-10, consider internally stated goals and actual outcomes:**
- **Goal Clarity** (0-2): Are goals explicit? If inferred, how reasonable?
- **Goal Achievement** (0-3): Based on evidence of completion/outcomes
- **Process Discipline** (0-2): Governance/provenance/adherence to stated process
- **Sustainability/Activity** (0-2): Recent activity, not abandoned
- **Coherence** (0-1): Internal consistency

**Categories:** High (8-10), Med (5-7), Low (3-4), Unknown (0-2 or insufficient evidence)

## 11. Analysis Notes
- [ ] **Best Aspects**: 
- [ ] **Weakest Aspects**: 
- [ ] **Recommendations - Set 1 (Internal Logic)**: 
- [ ] **Recommendations - Set 2 (Cross-System Comparison)**: 
- [ ] **Guesses/Inferences** (flag with [GUESS]): 
- [ ] **Unknowns**: 
- [ ] **Similar To** (other projects): 
- [ ] **Comparison Notes**: 
- [ ] **UMAWS Fleet Launcher Insights**: 

## 12. Git History Snapshot
- [ ] **Branches**: 
- [ ] **Recent Commits** (5-10): 
- [ ] **Oldest/Newest**: 
- [ ] **Activity Pattern**: (consistent/sporadic/stopped)
- [ ] **Merge Patterns**: 
