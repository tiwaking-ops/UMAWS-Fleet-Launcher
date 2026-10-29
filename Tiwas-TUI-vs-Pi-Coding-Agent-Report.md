# Tiwas TUI/GUI vs Pi Coding Agent (earendil-works/pi)
## Corrected Feasibility Report & Implementation Proposal

**Date:** 2026-10-29  
**Author:** Claude Code (Opus)  
**Status:** Corrected Research Report — Basis for Implementation Proposal

---

## Executive Summary (Corrected)

I previously conflated **two different products**:
1. **Pi (Inflection AI)** — Personal conversational assistant (cloud, chat, general purpose)
2. **Pi (earendil-works/pi, by Mario Zechner/badlogic)** — **Terminal-based AI coding agent**

This report evaluates replacing **Pi coding agent** with **Tiwas TUI/GUI**.

**Verdict: Both are terminal-based coding agents with similar architectures. Tiwas is earlier-stage; Pi is production-ready with more features.**

| Aspect | Pi (earendil-works/pi) | Tiwas TUI/GUI | Replacement Viability |
|--------|------------------------|---------------|----------------------|
| **Category** | Terminal coding agent | Terminal coding agent | ✅ Same category |
| **Maturity** | Production (7,215+ commits, v1.4.0) | Pre-delivery (34 commits unpublished) | ❌ Pi ahead |
| **Built-in Tools** | read, write, edit, bash, find, grep, ls | Via WorkspaceTools (edit, git, test, bash) | ⚠️ Comparable |
| **Project Context** | AGENTS.md/CLAUDE.md via ResourceLoader | Via CLAUDE.md in working dir | ✅ Similar |
| **Session Mgmt** | Persistent, branching, compaction, export | SQLite, resumable, export/import | ✅ Similar |
| **Multi-Provider** | Unified API (OpenAI/Anthropic/Google/local) | Multi-provider roster via `/login` | ✅ Similar |
| **Extensibility** | Skills (SKILL.md), extensions, themes | Tasks_seed.md (28 tasks), limited | ❌ Pi ahead |
| **Sandboxing** | Gondolin micro-VM, Docker, OpenShell | Worktree isolation, executor jail | ⚠️ Different approaches |
| **Automation** | Print/JSON/RPC/SDK modes | Headless `run_script()` only | ❌ Pi ahead |
| **Language** | TypeScript (Node.js 22+) | Python (stdlib-only) | Different stack |
| **UI** | TUI (differential rendering, pi-tui) | TUI (line-stdio) + Tkinter GUI | ⚠️ Pi TUI more advanced |
| **License** | MIT | Not specified in docs | Different |

**Recommendation:** 
- **If you want a working coding agent NOW** → Use Pi (earendil-works/pi)
- **If you want to build/customize your own** → Continue Tiwas (but expect 6-9 weeks for parity)
- **If you want Python/stdlib-only** → Tiwas is the only option

---

## 1. Pi Coding Agent (earendil-works/pi) — Deep Analysis

### 1.1 What Is It?

**Pi** is a **"minimal, extensible agent harness that you can make your own"** — an MIT-licensed, terminal-based AI coding agent by Mario Zechner (badlogic), hosted at `earendil-works/pi`.

**Core Philosophy:** "Adapt Pi to your workflows rather than the reverse. It ships with strong defaults but intentionally omits features like sub-agents and plan mode — you build or install those yourself."

### 1.2 Architecture (Monorepo)

```
earendil-works/pi (monorepo)
├── packages/
│   ├── pi-ai              # Unified multi-provider LLM API
│   ├── pi-agent-core      # Agent runtime, tool calling, state mgmt
│   ├── pi-coding-agent    # Interactive coding agent CLI (entry: `pi`)
│   ├── pi-tui             # Terminal UI library with differential rendering
│   ├── pi-durable         # Durable conversation/task/document runtime
│   ├── chord              # Hot-reloadable plugins, RPC over JSON
│   └── pi-telemetry       # Vendor-neutral telemetry contracts
└── pi-chat (separate repo) # Slack/chat automation
```

### 1.3 Built-in Tools (Verified from Source)

| Tool | File | Capability |
|------|------|------------|
| **bash** | `bash.ts` | Shell execution, process tree kill, timeout, output truncation |
| **read** | `read.ts` | File read with offset/limit, image support, truncation hints |
| **write** | `write.ts` | Create/overwrite files, recursive dir creation, mutation queue |
| **edit** | `edit.ts` | Exact text replacement, multi-edit batching, diff output |
| **find** | `find.ts` | File search |
| **grep** | `grep.ts` | Content search |
| **ls** | `ls.ts` | Directory listing |

**Execution Layer:** Pluggable `Operations` interfaces allow remote execution (SSH), default uses Node.js `child_process.spawn` / `fs/promises`.

### 1.4 Key Features

| Feature | Details |
|---------|---------|
| **Project Context** | Loads AGENTS.md-style files via `getAgentsFiles()` into system prompt |
| **Sessions** | Persistent (message log), branching, compaction (manual/threshold/overflow), export HTML/JSONL |
| **Skills** | SKILL.md-based, discoverable from user/project/explicit paths, compatible with Claude Code skills |
| **Models** | Unified API: OpenAI, Anthropic, Google, local (Ollama), custom endpoints |
| **Automation** | Print mode, JSON event stream, RPC control, TypeScript SDK |
| **Sandboxing** | No built-in perms; extensions: Gondolin (micro-VM), Docker, OpenShell |
| **Supply Chain** | Exact-pinned deps, `--ignore-scripts`, install lock, audit workflows |
| **Install** | Shell script, PowerShell, npm (`--ignore-scripts`), Nix |
| **Platforms** | macOS, Linux, Windows, tmux, Termux (Android) |

### 1.5 What It Does NOT Have (By Design)

- Sub-agents / plan mode (you build these)
- Built-in permission system (runs with user's full permissions)
- IDE integration (VS Code skill exists in pi-skills but separate)
- Git-specific tools (uses bash for git commands)

---

## 2. Tiwas TUI/GUI — Current State (Recap)

### 2.1 Architecture

```
TiwasProjectsv3/
├── src/tui/           # TUI: TuiApp, AgentLoop, SessionStore, WorkspaceTools
├── src/gui/           # GUI: claude_gui.py (Tkinter), bridge.py
├── src/engine/        # MISSING from this repo (in source project)
├── src/store/         # MISSING from this repo
├── src/tools/         # MISSING from this repo
└── tools/tui_run.py   # Launcher (in source project)
```

### 2.2 Verified State (2026-10-29)

| Component | Status | Evidence |
|-----------|--------|----------|
| **TUI Core** | Functionally complete | 592 tests pass, 17 slash commands |
| **TUI Dependencies** | **MISSING** | `import src.tui.app` fails (no engine/store/tools) |
| **GUI** | Known defects, unpublished | Key-blanking defect, no approval UI, 34 commits behind |
| **Kernel Contracts** | In source project only | Need port from `C:\temp\projects\TiwasProjects\` |

### 2.3 TUI Capabilities (When Kernel Present)

| Feature | Tiwas | Pi |
|---------|-------|-----|
| File read/write/edit | Via WorkspaceTools | Built-in tools |
| Bash execution | Via WorkspaceTools | Built-in bash tool |
| Git operations | Via WorkspaceTools | Via bash tool |
| Test execution | Via WorkspaceTools | Via bash tool |
| Project context | CLAUDE.md in cwd | AGENTS.md/CLAUDE.md via ResourceLoader |
| Sessions | SQLite, resumable | Durable, branching, compaction |
| Multi-provider | `/login` roster | Unified API + `/login` |
| Skills/Extensions | Task seed only | SKILL.md, extensions, themes |
| Automation | `run_script()` headless | Print/JSON/RPC/SDK |
| Sandboxing | Worktree + executor jail | Extensions (Gondolin/Docker) |

---

## 3. Gap Analysis — Pi vs Tiwas (Corrected)

### 3.1 Critical Gaps (Tiwas Behind Pi)

| # | Gap | Severity | Pi Has | Tiwas Status |
|---|-----|----------|--------|--------------|
| 1 | **Working kernel in this repo** | Critical | N/A (self-contained) | **MISSING** — must port engine/store/tools |
| 2 | **Mature TUI rendering** | High | pi-tui (differential, full-screen) | Line-stdio only, no curses |
| 3 | **Automation modes** | High | Print/JSON/RPC/SDK | `run_script()` only |
| 4 | **Skills/Extensions system** | High | SKILL.md, npm packages, themes | 28 seeded tasks only |
| 5 | **Session branching** | Medium | Full branching + summaries | Basic sessions only |
| 6 | **Compaction policies** | Medium | Manual/threshold/overflow | Manual `/compact` + auto threshold |
| 7 | **Sandboxing options** | Medium | Gondolin micro-VM, Docker | Worktree isolation only |
| 8 | **Project trust system** | Medium | Explicit trust prompts | Implicit via CLAUDE.md |
| 9 | **GUI defects** | High | N/A (TUI only) | Key-blanking, no approval UI, unpublished |
| 10 | **7,215+ commits maturity** | High | Production-ready | Pre-delivery |

### 3.2 Areas Where Tiwas Could Exceed Pi

| # | Advantage | Feasibility |
|---|-----------|-------------|
| 1 | **Python/stdlib-only** (no Node.js) | ✅ Core design principle |
| 2 | **Windows-native** (no WSL needed) | ✅ Stdlib-only, plat.py for locks |
| 3 | **Worktree isolation built-in** | ✅ Fleet/Dispatcher architecture |
| 4 | **Kernel separation** (engine/store/tools reusable) | ✅ Clean architecture |
| 5 | **Claude Code compatible skills** | ⚠️ Pi-skills already compatible |
| 6 | **Custom kernel policies** (QuotaGate, etc.) | ✅ Already implemented |

### 3.3 Parity Gaps (Must Match for Viable Replacement)

| # | Feature | Pi | Tiwas Needed |
|---|---------|-----|--------------|
| 1 | Read tool | ✅ | ✅ (via WorkspaceTools) |
| 2 | Write tool | ✅ | ✅ (via WorkspaceTools) |
| 3 | Edit tool | ✅ | ✅ (via WorkspaceTools) |
| 4 | Bash tool | ✅ | ✅ (via WorkspaceTools) |
| 5 | Find/Grep/Ls | ✅ | ✅ (via WorkspaceTools) |
| 6 | AGENTS.md/CLAUDE.md context | ✅ | ⚠️ Partial (only CLAUDE.md) |
| 7 | Session persistence | ✅ | ✅ (SQLite) |
| 8 | Multi-provider | ✅ | ✅ (roster) |
| 9 | Skills system | ✅ | ❌ Need to build |
| 10 | Automation API | ✅ | ❌ Need to build |

---

## 4. Implementation Roadmap (Corrected)

### Phase 0: Make Tiwas Runnable (1-2 weeks) **BLOCKER**

**The Tiwas repo cannot even import `src.tui.app` without the kernel.**

| Task | Description | Source |
|------|-------------|--------|
| 0.1 | Port `src/engine/` from `TiwasProjects\src\engine\` | Core API, Loop, Compaction |
| 0.2 | Port `src/store/sessions.py` from source | SessionStore with SQLite |
| 0.3 | Port `src/tools/` from source | Executor, Schemas, Jail, Policy |
| 0.4 | Port `tools/tui_run.py` launcher | Headless + interactive |
| 0.5 | Land AST gates as tests | Stdlib-only, no-network, no-providers |
| 0.6 | Verify `run_script()` works end-to-end | Scripted turn persists session |

**Source location:** `C:\temp\projects\TiwasProjects\` has all kernel packages.

### Phase 1: Core Tool Parity (2-3 weeks)

| Task | Description | Pi Reference |
|------|-------------|--------------|
| 1.1 | Verify WorkspaceTools covers: read, write, edit, bash, find, grep, ls | Pi tools in `packages/coding-agent/src/core/tools/` |
| 1.2 | Add AGENTS.md loading alongside CLAUDE.md | `ResourceLoader.getAgentsFiles()` |
| 1.3 | Implement session branching | `AgentSession` branching in `agent-session.ts` |
| 1.4 | Add compaction policies (threshold/overflow) | Auto-compaction in `AgentSession` |
| 1.5 | Add project trust prompts | `resolveProjectTrusted()` flow |

### Phase 2: Advanced Features (3-4 weeks)

| Task | Description | Pi Reference |
|------|-------------|--------------|
| 2.1 | Skills system (SKILL.md discovery, loading) | `skills.ts` discovery rules |
| 2.2 | Extensions API (hot-reloadable plugins) | `chord` package |
| 2.3 | Automation modes: print, JSON, RPC | Pi CLI modes |
| 2.4 | TypeScript SDK equivalent (Python SDK) | Pi TypeScript SDK |
| 2.5 | Sandboxing: Gondolin/Docker integration | `containerization.md` patterns |
| 2.6 | Fix GUI defects (T-0143, approval UI) | N/A (Tiwas-specific) |

### Phase 3: Polish & Ecosystem (2-3 weeks)

| Task | Description |
|------|-------------|
| 3.1 | Comprehensive test coverage (>90%) |
| 3.2 | Documentation, onboarding |
| 3.3 | Resolve 34-commit publish backlog |
| 3.4 | Package distribution (pip, standalone) |
| 3.5 | Community: skills registry, themes |

---

## 5. Effort & Cost Summary (Corrected)

### 5.1 Time Estimates (Solo Developer)

| Phase | Weeks | Cumulative | Deliverable |
|-------|-------|------------|-------------|
| 0: Make Runnable | 1-2 | 1-2 | `import src.tui.app` works |
| 1: Core Parity | 2-3 | 3-5 | Feature parity with Pi core |
| 2: Advanced | 3-4 | 6-9 | Skills, automation, sandboxing |
| 3: Polish | 2-3 | 8-12 | Production-ready |

**Total for viable Pi replacement: 8-12 weeks** (vs my previous 6-9 for coding-only)

### 5.2 Ongoing Costs

| Cost | Pi | Tiwas (Phases 0-3) |
|------|-----|-------------------|
| **Runtime** | Node.js 22+ | Python 3.12+ |
| **API Keys** | BYO (same providers) | BYO (same providers) |
| **Maintenance** | Active (7,215+ commits) | Your burden |
| **Ecosystem** | Skills registry, Discord | You build it |

### 5.3 Team Scaling

| Team | Phase 0-1 | Phase 0-3 |
|------|-----------|-----------|
| 1 dev | 3-5 weeks | 8-12 weeks |
| 2 devs | 2-3 weeks | 5-7 weeks |
| 3 devs | 1-2 weeks | 3-5 weeks |

---

## 6. Feasibility Assessment (Corrected)

### 6.1 Verdict Matrix

| Goal | Feasible? | Timeline | Recommendation |
|------|-----------|----------|----------------|
| **Match Pi core features** | ✅ Yes | 3-5 weeks (Ph 0-1) | Do if you need Python/stdlib |
| **Match Pi advanced features** | ✅ Yes | 6-9 weeks (Ph 0-2) | Do if you need skills/automation |
| **Exceed Pi in Python/Windows** | ✅ Yes | 8-12 weeks (Ph 0-3) | Do for stdlib-only constraint |
| **Use Pi as-is** | ✅ Yes | 0 weeks | **Recommended for most** |

### 6.2 Critical Decision Points

1. **Do you need Python/stdlib-only?** 
   - If **YES** → Tiwas is your only option (Pi requires Node.js)
   - If **NO** → Pi is production-ready today

2. **Can you invest 8-12 weeks for parity?**
   - If **NO** → Use Pi, contribute skills/extensions instead
   - If **YES** → Proceed with Phase 0

3. **Do you need automation API (JSON/RPC/SDK)?**
   - If **YES** → Pi has it now; Tiwas needs Phase 2
   - If **NO** → Phase 1 may suffice

4. **Is worktree isolation important?**
   - If **YES** → Tiwas has it built-in (Fleet architecture)
   - If **NO** → Pi's sandboxing extensions are more flexible

5. **Will you maintain this long-term?**
   - If **NO** → Don't build; use Pi
   - If **YES** → Tiwas gives you full control

### 6.3 Risk Assessment (Corrected)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Kernel port drifts from source | High | High | Conformance tests; sync from `TiwasProjects` |
| Solo maintenance vs Pi's team | High | High | Document everything; automate tests |
| Skills ecosystem from scratch | Medium | High | Leverage Claude Code skill compatibility |
| GUI defects block GUI path | High | Medium | Fix T-0143 in Phase 0; approval UI in 2.6 |
| 34-commit backlog blocks CI | Medium | Medium | Resolve in Phase 0 or 3 |
| Pi adds features faster than you catch up | High | Medium | Focus on differentiators (Python, Windows, worktrees) |

---

## 7. Alternative Paths

### 7.1 Use Pi (earendil-works/pi) Directly

```bash
# Install
curl -fsSL https://pi.dev/install.sh | sh  # macOS/Linux
# or PowerShell on Windows

# Configure
pi login  # Choose provider: OpenAI, Anthropic, Google, local

# Use
cd /your/project && pi
```

**Pros:** Working today, mature, active community, skills registry, automation API
**Cons:** Node.js dependency, no built-in sandboxing, no worktree isolation

### 7.2 Use Pi + Contribute

Pi's extension system is designed for this:
- Write **skills** (SKILL.md) — compatible with Claude Code
- Build **extensions** via `chord` — hot-reloadable plugins
- Publish to npm or git

### 7.3 Hybrid: Pi for Now, Tiwas for Custom Needs

Use Pi for daily coding. Build Tiwas only for:
- Python/stdlib-only constraint
- Worktree isolation requirement
- Custom kernel policies (QuotaGate, etc.)
- Learning/education

---

## 8. If You Still Want To Build Tiwas — Start Here

### 8.1 Week 1 Sprint Plan (Phase 0)

```bash
# 1. Copy missing kernel packages from source project
SRC=C:\temp\projects\TiwasProjects
DST=C:\temp\projects\TiwasProjectsv3

cp -r $SRC/src/engine $DST/src/
cp -r $SRC/src/store $DST/src/
cp -r $SRC/src/tools $DST/src/
cp -r $SRC/tools/tui_run.py $DST/tools/

# 2. Verify imports work
cd $DST
python -c "import src.tui.app; print('OK')"

# 3. Create tests/ and land AST gates
mkdir tests
# Add gate tests per Tiwas-TUI-Implementation-Proposal.md

# 4. Run scripted turn test
python -c "
from src.tui.app import TuiApp
from src.engine.core_api import Session, ProviderAdapter
# ... fake provider, run_script test
"
```

### 8.2 Success Criteria for Week 1

- [ ] `import src.tui.app` succeeds
- [ ] `TuiApp.run_script(["hello"])` completes without error
- [ ] Session persists to SQLite
- [ ] AST gate tests pass in `pytest tests/ -q`
- [ ] `tools/tui_run.py --help` shows flags
- [ ] Basic read/write/edit/bash via WorkspaceTools verified

### 8.3 Go/No-Go Decision Point

**After Week 1:** If Foundation phase works, continue to Phase 1. If blocked > 3 days on engine port, **abandon and use Pi (earendil-works/pi)**.

---

## 9. Appendix: Key Source Documents

| Document | Location | Purpose |
|----------|----------|---------|
| Pi README | `github.com/earendil-works/pi` | Main project overview |
| Pi coding agent package | `packages/coding-agent/` | CLI, tools, session mgmt |
| Pi agent core | `packages/pi-agent-core/` | Agent runtime, tool calling |
| Pi tools | `packages/coding-agent/src/core/tools/` | read, write, edit, bash, find, grep, ls |
| Pi skills | `badlogic/pi-skills` | 8 skills, Claude Code compatible |
| Tiwas TUI TDD | `docs/Tiwas-TUI-TDD.md` | Tiwas TUI design |
| Tiwas Implementation Proposal | `docs/Tiwas-TUI-Implementation-Proposal.md` | Phased work plan |
| Tiwas Status Report | `docs/Tiwas-TUI-GUI-status-report-2026-10-29.md` | Current state, blockers |
| Tiwas GUI Work Plan | `docs/Tiwas-GUI-Work-Plan.md` | GUI task breakdown |
| Tiwas Source Project | `C:\temp\projects\TiwasProjects\` | Complete kernel packages |

---

## 10. Conclusion (Corrected)

**Pi (earendil-works/pi) and Tiwas TUI/GUI are the SAME CATEGORY of tool: terminal-based AI coding agents.**

| Factor | Winner | Notes |
|--------|--------|-------|
| **Maturity** | Pi | 7,215+ commits vs pre-delivery |
| **Features** | Pi | Skills, automation, branching, sandboxing options |
| **Python/stdlib-only** | Tiwas | Core design principle; Pi requires Node.js |
| **Windows-native** | Tiwas | No WSL needed; Pi works on Windows but Node-based |
| **Worktree isolation** | Tiwas | Built-in Fleet architecture |
| **Custom kernel policies** | Tiwas | QuotaGate, Constitution, etc. |
| **Time to usable** | Pi | 0 weeks vs 8-12 weeks |

**My honest recommendation:**

1. **For 95% of developers:** Use **Pi (earendil-works/pi)** today. It's production-ready, actively maintained, has a skills ecosystem, and solves the coding agent problem completely.

2. **For the 5% who need:** Python/stdlib-only, Windows-native without WSL, worktree isolation built-in, custom kernel policies — **build Tiwas** but budget 8-12 weeks.

3. **Best of both worlds:** Use Pi for daily coding. Mine its skills/extensions for ideas. Build Tiwas only for the specific constraints Pi cannot satisfy.

The Tiwas codebase is **well-architected and principled** — but it's a **framework awaiting its kernel**, not a product. Pi is the product.

---

*Corrected report generated 2026-10-29. Based on analysis of earendil-works/pi (v1.4.0, 7,215+ commits), Pi source code in packages/coding-agent/src/core/tools/, TiwasProjectsv3 (commit 6d7a964), TiwasProjects source kernel, and Tiwas project documentation.*