# Tiwas TUI as Pi Coding Agent Replacement — Implementation Roadmap

| Field | Value |
|---|---|
| **Title** | Comprehensive Analysis: Replacing Pi Coding Agent with Tiwas TUI |
| **Date** | 2026-10-29 |
| **Status** | Research report — advisory; confers no authority |
| **Sources** | `C:\temp\projects\TiwasProjectsv3\docs\Tiwas-TUI-GUI-status-report-2026-10-29.md`, `docs/Tiwas-TUI-TDD.md`, `docs/Tiwas-TUI-Implementation-Proposal.md`, `docs/Tiwas-GUI-Work-Plan.md`, `docs/Tiwas-TUI-GUI-report1.md`, `src/tui/`, `src/gui/`, `tools/` on `wf/integration` branch |

---

## Executive Summary

**Tiwas TUI is functionally complete for its accepted scope** (TUI: W-1..W-5, S1..S4, P1-G1..G3; GUI: GUI-01..GUI-10, T-0026..T-0032, promotion T-0086..T-0096, T-0137) and **passes all 592 tests** (30 test modules). The engineering is done; what remains is release engineering, defect closure, and bookkeeping.

However, **neither TUI nor GUI is "delivered"**: 34 commits are unpublished (on `wf/integration`, behind `main` by governance rule), the GUI has a key-blanking defect (G-1), an orphaned approval surface (G-2), and no manual acceptance sign-off.

**Verdict:** Tiwas TUI *can* replace Pi as a lightweight coding agent, but requires **19–24 weeks of focused work** across 6 phases to reach parity with Pi's "always available" experience and IDE integration. The core harness works today; the gaps are in daemonization, hotkey access, local LLM support, and IDE plugins.

---

## Current State Analysis

### What Tiwas TUI Has Today (Verified Working)

| Capability | Status | Evidence |
|---|---|---|
| **Line-oriented TUI harness** (`TuiApp`) | ✅ Complete | `src/tui/app.py` 617 lines; drives `AgentLoop` via injected provider |
| **Slash commands** (17 commands) | ✅ Complete | `commands.py`: login, model, sessions, compact, search, export, import, etc. |
| **Provider roster** (`/login` wizard) | ✅ Complete | `config.py` + `registry.py`: secret hygiene, `env:` pointers, redaction |
| **Session persistence** (SQLite + memory) | ✅ Complete | `SessionStore`: save/load/list/delete/export/import round-trip |
| **Approval flow** (y/n on same stream) | ✅ Complete | `ToolPane` batch + timeout-denial; injected approver for tests |
| **Status line** (5-field context meter) | ✅ Complete | `status.py`: provider, model, max-ctx, used, remaining; 80% warn |
| **Transcript views** (throttled, capped) | ✅ Complete | `views.py`: `TranscriptView`, `ToolPane`, `Spinner`, search |
| **Headless launcher** (`tools/tui_run.py`) | ✅ Complete | `--script`, `--workspace`, `--session-db`, `--session-id`, `--registry`, `--chain` |
| **Resilient chains** (fallback + cooldown) | ✅ Complete | `provider_factory.py`: `ResilientAdapter`, `CooldownStore` |
| **GUI bridge** (drives TUI via CLI lines) | ✅ Complete | `src/gui/bridge.py`: `GuiSession`, `LoginBuilder`, `GuiInput` |
| **GUI state store** (models, projects) | ✅ Complete | `src/gui/state.py`: `StateStore` via `LoginRegistry` + `.projects.json` |
| **GUI main window** (tkinter, lazy widgets) | ✅ Complete | `src/gui/claude_gui.py`: provider/model/project forms, send path |
| **GUI launcher** (`tools/gui_run.py`) | ✅ Complete | `--check` (headless), `--send`, `--provider/--model`, `--config` |

### Known Defects Blocking "Delivered" Status

| ID | Defect | Impact | Location |
|---|---|---|---|
| **G-1** | Reopening "Add Provider" blanks API key | Next send fails "missing key source" | `src/gui/claude_gui.py` `AddProviderWindow.save_provider()` |
| **G-2** | No tool-approval surface in GUI | Mutating tools auto-denied (timeout) | `src/gui/approval.py` built but **unused** (no imports) |
| **G-3** | EOF denial labeled as timeout | Misleading diagnostic | `TuiApp._ensure_approver()` |
| **G-4** | Manual acceptance unsigned | Cannot claim "accepted" on worker evidence | Operator-only per governance 0003 |
| **G-5** | `approval.py` is dead code | Ambiguity: shipped feature or not? | No imports under `src/`, `tools/`, `tests/` |

### Architecture Constraints (Non-Negotiable)

From `docs/Tiwas-TUI-TDD.md` §3 and §4:
- **C1**: Stdlib only in `src/tui/` and `src/gui/` (AST gate enforced)
- **C2**: No network imports in UI packages
- **C3**: `src/tui` and `src/gui` must never import `src.providers`
- **C4**: Line-oriented stdio; no curses/Textual (Windows-compatible)
- **C5**: Slash parser never raises
- **C6**: Secrets never rendered (`direct:` → `<redacted>`)
- **C7**: Exit path never traps user (fail-open save; `shutdown()` always flushes)

---

## Gap Analysis: Tiwas TUI vs. Pi Coding Agent

Based on user's stated Pi attributes: **lightweight**, **agentic**, **terminal-based**, **no headless mode**, **most lightweight client available**.

| Dimension | Pi (User Description) | Tiwas TUI (Current) | Gap |
|---|---|---|---|
| **Weight** | "Most lightweight" | Stdlib-only, ~2K LOC TUI + ~1K GUI | Comparable |
| **Mode** | TUI only, no headless | TUI + GUI + headless (`--script`, `--check`) | Tiwas **ahead** |
| **Availability** | Always running? | Manual launch; no daemon/hotkey | **Major gap** |
| **Local LLMs** | Unknown | Echo only; no llama.cpp/Ollama | **Major gap** |
| **IDE Integration** | Unknown | None | **Major gap** |
| **Multi-session** | Unknown | `TabbedTuiApp` stub only (T-0024) | **Gap** |
| **Session Resume** | Unknown | Full persist/resume (`--session-id`) | Tiwas **ahead** |
| **Model Roster** | Unknown | `/login` wizard, `/model` switch, chains | Tiwas **ahead** |
| **Approval UX** | Unknown | TUI: inline y/n; GUI: **broken** | **Gap (GUI)** |
| **Cloud Sync** | Unknown | None | **Gap** |

---

## Implementation Roadmap (19–24 Weeks)

### PHASE 1: Foundation (Prerequisites — 2–3 Weeks)

**Objective:** Unblock all downstream work by landing missing engine/store/tools contracts and hardening the test harness.

| Task | Description | Dependencies | Acceptance Criteria | Effort |
|---|---|---|---|---|
| **F-1** | Port `src/engine/` (`core_api`, `loop`, `compaction`) | — | `python -c "import src.tui.app"` succeeds | 3 days |
| **F-2** | Port `src/store/sessions.py` (`SessionStore`) | — | File-backed + `:memory:` store; export/import round-trip | 2 days |
| **F-3** | Port `src/tools/` (`executor.WorkspaceTools`, `schemas.TOOL_SCHEMAS`) | F-1 | Tool approval hook works; schemas enrich `ToolPane` labels | 2 days |
| **F-4** | Land AST gates as repo tests (stdlib-only, no-network, no-providers) | — | `pytest tests/test_gates.py` green; runs in CI | 2 days |
| **F-5** | Verify `tools/tui_run.py` launcher imports and runs headless | F-1..F-3 | `python tools/tui_run.py --script demo.txt` exits 0 | 1 day |
| **F-6** | Consolidate live-provider evidence (T-0142) into project records | — | Evidence bundle linked in `GOALS.md` / TDD status table | 2 days |

**Total Phase 1:** ~12 days (2.5 weeks)

---

### PHASE 2: Core UX Parity (4–6 Weeks)

**Objective:** Achieve feature parity with a polished single-session TUI/GUI experience.

| Task | Description | Dependencies | Acceptance Criteria | Effort |
|---|---|---|---|---|
| **U-1** | Implement `TabbedTuiApp` (T-0024) for multi-session | F-1..F-5 | Ctrl-N/L/Q shortcuts work; tabs persist across restarts | 10 days |
| **U-2** | Expand `help_full.md` to document all 17 commands | F-5 | `/help` output covers every `KNOWN_COMMANDS` entry | 3 days |
| **U-3** | Configurable compact threshold (env `TUI_COMPACT_THRESHOLD`) | F-1 | Threshold override respected by `needs_compact()` path | 2 days |
| **U-4** | Keyboard shortcuts: Ctrl-N (new), Ctrl-L (login), Ctrl-Q (quit) | F-5, U-1 | Shortcuts translate to `/new`, `/login`, `/quit` before dispatch | 2 days |
| **U-5** | Export/import edge-case tests (empty, corrupted, large) | F-3 | Round-trip verified for all edge cases | 3 days |
| **U-6** | Fix GUI key-blanking defect (G-1, T-0143) | F-5 | Prefill `key_v` from existing row; preserve on blank save | 3 days |
| **U-7** | Wire GUI approval surface (`src/gui/approval.py`) into send path | F-5 | Mutating tools show modal dialog; approve/deny respected | 5 days |
| **U-8** | Fix EOF denial mislabeled as timeout (G-3) | F-1 | Distinct "denied (EOF)" vs "denied (timeout)" messages | 1 day |
| **U-9** | Manual acceptance sign-off + secret rotation (R-7, R-8) | U-6, U-7 | Operator ticks checklist; legacy key rotated | 2 days (operator) |

**Total Phase 2:** ~31 days (6 weeks)

---

### PHASE 3: "Always Available" Experience (3–4 Weeks)

**Objective:** Transform Tiwas from "launch manually" to "always there" — the core Pi replacement value.

| Task | Description | Dependencies | Acceptance Criteria | Effort |
|---|---|---|---|---|
| **A-1** | Daemon mode: background TUI process with IPC (named pipe/Unix socket) | U-1, U-4 | `tiwas-daemon start|stop|status`; survives terminal close | 10 days |
| **A-2** | Global hotkey (Win+Alt+T / Cmd+Option+T) to show/hide daemon window | A-1 | Hotkey registered at OS level; toggles window visibility | 5 days |
| **A-3** | Session auto-save/resume on startup | U-1 | Last session restored automatically; `--session-id` optional | 3 days |
| **A-4** | Default model bootstrap without `/login` wizard | F-1 | `DEFAULT_MODEL` env var → working session on first run | 2 days |
| **A-5** | Local LLM support: llama.cpp adapter (stdio) | F-1 | `--provider llama-cpp --model <path>` runs without network | 5 days |
| **A-6** | Local LLM support: Ollama adapter (HTTP localhost) | A-5 | `--provider ollama --model <name>` works; no API key needed | 3 days |

**Total Phase 3:** ~28 days (5.5 weeks)

---

### PHASE 4: IDE Integration (3–4 Weeks)

**Objective:** Embed Tiwas in the developer's primary workspace.

| Task | Description | Dependencies | Acceptance Criteria | Effort |
|---|---|---|---|---|
| **I-1** | VS Code extension: inline chat panel + terminal integration | A-1 | `Tiwas: Chat` command opens pane; sends to daemon via IPC | 10 days |
| **I-2** | VS Code extension: context injection (open files, selection, diagnostics) | I-1 | `@file`, `@selection`, `@errors` references work in prompt | 5 days |
| **I-3** | JetBrains plugin (IntelliJ/PyCharm): tool window + terminal | A-1 | Same features as VS Code; uses same IPC protocol | 8 days |
| **I-4** | LSP bridge: expose Tiwas as language server for context | I-1 | `textDocument/completion` → Tiwas; `workspace/symbol` → repo map | 5 days |

**Total Phase 4:** ~28 days (5.5 weeks)

---

### PHASE 5: Cloud Sync / Multi-device (2–3 Weeks)

**Objective:** Optional encrypted sync for users who want it.

| Task | Description | Dependencies | Acceptance Criteria | Effort |
|---|---|---|---|---|
| **C-1** | Encrypted session sync (optional, user-enabled) | A-3 | AES-256-GCM; passphrase-derived key; sync to configurable backend | 8 days |
| **C-2** | Web companion: read-only transcript view (static HTML export) | A-3 | `tiwas export --web` → `index.html` with search/filter | 5 days |
| **C-3** | Mobile-friendly responsive GUI (Tauri/WebView2) | C-2 | `tauri build` → mobile APK/IPA; touch-optimized layout | 8 days |

**Total Phase 5:** ~21 days (4 weeks)

---

### PHASE 6: Polish & Hardening (2–3 Weeks)

**Objective:** Production readiness.

| Task | Description | Dependencies | Acceptance Criteria | Effort |
|---|---|---|---|---|
| **P-1** | Performance optimization (startup < 500ms, memory < 50MB) | All | Benchmarks in CI; regression gate | 5 days |
| **P-2** | Comprehensive test coverage (≥90% on `src/tui`, `src/gui`, `tools/`) | All | `pytest --cov=src/tui --cov=src/gui --cov=tools` ≥ 90% | 5 days |
| **P-3** | Documentation: onboarding wizard, architecture guide, FAQ | All | `/wizard` command; `docs/architecture.md`; `docs/faq.md` | 3 days |
| **P-4** | Publish to `main` (resolve 34-commit backlog) | All | Governance 0003 satisfied; `main` = `wf/integration` | 2 days (operator) |

**Total Phase 6:** ~15 days (3 weeks)

---

## Dependency Graph

```
F-1 → F-2 → F-3 → F-4 → F-5 → F-6
                                    ↓
U-1 → U-2 → U-3 → U-4 → U-5 → U-6 → U-7 → U-8 → U-9
                                    ↓
A-1 → A-2 → A-3 → A-4 → A-5 → A-6
                                    ↓
I-1 → I-2 → I-3 → I-4
                                    ↓
C-1 → C-2 → C-3
                                    ↓
P-1 → P-2 → P-3 → P-4
```

**Critical Path:** F-1→F-5 → U-1→U-7 → A-1→A-6 → I-1→I-4 → P-1→P-4  
**Estimated Critical Path Duration:** 19–24 weeks

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Daemon IPC design complexity** | Medium | High | Start with simple named pipes; use `multiprocessing.connection` |
| **Global hotkey on Windows** | Medium | Medium | Use `pynput` or `keyboard` (stdlib alternative: `ctypes` + `RegisterHotKey`) |
| **llama.cpp integration stability** | Medium | Medium | Pin llama.cpp version; vendor `llama-cpp-python` wheel |
| **VS Code extension API changes** | Low | Medium | Use stable extension API; test on insiders |
| **Governance 0003 blocks publish** | High | High | Operator must approve; schedule R-7/R-8 early |
| **Scope creep into transports/streaming** | Medium | Medium | Enforce §3.3 out-of-scope list via gate tests |
| **Local LLM performance on CPU** | High | Medium | Document hardware requirements; offer quantized models |

---

## Resource Requirements

| Role | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Phase 6 |
|---|---|---|---|---|---|---|
| **Backend Engineer** (Python, TUI) | 1.0 | 1.0 | 1.0 | 0.5 | 0.0 | 0.5 |
| **Frontend Engineer** (tkinter, Tauri) | 0.0 | 0.5 | 0.0 | 0.0 | 1.0 | 0.5 |
| **IDE Extension Engineer** (VS Code, JetBrains) | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 | 0.0 |
| **DevOps/Release** | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.5 |
| **Operator** (governance, keys) | 0.0 | 0.2 | 0.0 | 0.0 | 0.0 | 0.2 |

---

## Decision Points (Require User Confirmation)

1. **Daemon IPC mechanism**: Named pipes (Windows) vs Unix sockets (cross-platform via `socketpair`) vs HTTP localhost?
2. **Global hotkey library**: Accept `pynput`/`keyboard` dependency (not stdlib) or implement via `ctypes`?
3. **Local LLM priority**: llama.cpp first (broader model support) or Ollama first (easier UX)?
4. **IDE integration priority**: VS Code first (market share) or JetBrains (user preference)?
5. **Cloud sync backend**: User-hosted (S3-compatible) vs managed (Firebase/Supabase) vs peer-to-peer (Syncthing)?
6. **Tauri vs WebView2**: Tauri (Rust, smaller) vs WebView2 (Windows native, larger)?

---

## Conclusion

**Tiwas TUI is a viable Pi replacement candidate.** The core harness is complete, tested, and architecturally sound. The remaining work is **not feature construction** but **productization**: daemonization, hotkey access, local LLM support, and IDE integration.

**Recommendation:** Proceed with Phase 1 immediately (unblocks everything). Phases 2–3 deliver the "always available" experience that matches Pi's lightweight terminal advantage. Phases 4–5 are differentiators Pi lacks. Phase 6 is mandatory for any production release.

**Go/No-Go Criteria for Phase 1 Start:**
- [ ] User confirms daemon IPC mechanism choice
- [ ] User confirms local LLM priority (llama.cpp vs Ollama)
- [ ] Operator acknowledges governance 0003 publish requirement
- [ ] Resource allocation approved for 1.0 backend engineer for 19+ weeks

---

## Appendix: File Map (Integration Branch)

```
src/
├── engine/
│   ├── __init__.py
│   ├── core_api.py      # Session, Message, ProviderAdapter, Usage
│   ├── loop.py          # AgentLoop, LoopConfig
│   └── compaction.py    # compact_messages
├── store/
│   ├── __init__.py
│   └── sessions.py      # SessionStore (SQLite + memory)
├── tools/
│   ├── __init__.py
│   ├── executor.py      # WorkspaceTools + .approver hook
│   ├── jail.py
│   ├── policy.py
│   └── schemas.py       # TOOL_SCHEMAS
├── tui/
│   ├── __init__.py
│   ├── app.py           # TuiApp + TabbedTuiApp stub
│   ├── commands.py      # 17 slash commands
│   ├── config.py        # LoginConfig, wizard, secret hygiene
│   ├── registry.py      # LoginRegistry (JSON + demo encryption)
│   ├── status.py        # 5-field status line, 80% trigger
│   ├── views.py         # TranscriptView, ToolPane, ThrottledRenderer
│   ├── theme.py         # ANSI / high-contrast / NO_COLOR
│   ├── help_full.md     # 4-line stub → needs expansion
│   ├── tasks_seed.md    # 28 seeded follow-up tasks
│   └── router.py / roster.py / naming.py / sessionmeta.py
└── gui/
    ├── __init__.py
    ├── bridge.py        # GuiSession, LoginBuilder, GuiInput
    ├── state.py         # StateStore (models, projects)
    ├── approval.py      # ApprovalDialog, make_gui_approver (ORPHANED)
    ├── claude_gui.py    # MainWindow, provider/model/project forms
    └── send.py

tools/
├── __init__.py
├── tui_run.py           # Headless + interactive launcher
├── gui_run.py           # GUI launcher (--check, --send)
├── provider_factory.py  # create_provider, ResilientAdapter
├── registry_maintenance.py
└── wfchecks/            # Workflow gate tests

tests/                   # 30 modules, 592 tests
├── test_gates.py        # AST gates (stdlib, no-net, no-providers)
├── test_tui_app.py      # TUI harness coverage
├── test_claude_gui.py   # 25 GUI tests
├── test_gui_bridge.py   # 23 bridge tests
├── test_gui_launch.py   # 19 launcher tests
└── ...
```

---

*This report records research findings; it does not authorize work. Implementation requires explicit user confirmation on decision points above and operator approval for governance-gated steps (publish, key rotation).*