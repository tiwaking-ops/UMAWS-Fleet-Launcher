---
document:
  title: "tiwa-brain-code: A Single Lightweight Orchestrator Replacing Five Agentic Coding Tools"
  status: "Proposal v1.0 — architecture and implementation plan (candidate tier; no authority)"
  version: "1.0.0"
author: "Claude Sonnet 5.5 (claude-sonnet-5-5), Anthropic"
date: "2026-10-28"
license: "Apache 2.0"
audience:
  primary: "The project creator (single operator, Windows + WSL Ubuntu)"
  secondary: "Potential open-source contributors"
source_documents:
  - "testproject1 codebase and docs (reference only — tiwa-brain-code is a new project)"
  - "docs/free-models.md (provider and free-model inventory)"
  - "proposal-claude-llm-gateway-v1-1.md (QuotaGate v1.1 — OpenAI-compatible API, 12 free models)"
  - "src/fleet/adapters/generic.py and base.py (measured adapter capabilities pattern)"
  - "Ultimate-Multi-Agent-Workflow-System.md (UMAWS — Kernel/Fleet split, event-log authority)"
evidence_basis: "Full read of testproject1 codebase and docs in this session. No code run, no live provider call made. All provider capabilities are inherited from the existing free-models.md inventory; CLI capabilities are inherited from the measured adapter table in generic.py."
epistemic_status: "All decisions here are [SPECULATIVE] until validated by implementation. Provider capabilities are [OBSERVED] from the existing docs. CLI behaviors marked 'measured' in the adapter table remain [OBSERVED*]; behaviors marked 'not tested' remain [GUESS] — they must be re-measured against the actual CLIs tiwa-brain-code targets."
---

# tiwa-brain-code v1.0

## Contents

1. [Summary](#1-summary)
2. [Problem Statement](#2-problem-statement)
3. [Goals and Non-Goals](#3-goals-and-non-goals)
4. [Architecture Overview](#4-architecture-overview)
5. [Component Design](#5-component-design)
6. [MVP Scope](#6-mvp-scope)
7. [Implementation Roadmap](#7-implementation-roadmap)
8. [Context and Memory Model](#8-context-and-memory-model)
9. [Provider Integration](#9-provider-integration)
10. [Open Questions](#10-open-questions)
11. [Risks and Mitigations](#11-risks-and-mitigations)

---

## 1. Summary

**tiwa-brain-code** is a single, lightweight agentic coding orchestrator that replaces five separate applications — OpenCode, Claude Code, Hermes, Kilo Code, and CodeBuff — with one unified entry point. Its distinguishing feature is a **permanent LLM "brain"** that runs continuously in the cloud (via Claude API or OpenRouter) and handles context management, memory, and provider/model routing, but does **not** answer questions directly. Instead, it dispatches work to one of the five target applications via their CLIs, selecting the best available free model at each moment based on measured capacity, capability needs, and cost.

The system is built in Python 3.12, runs on Windows with WSL Ubuntu, and follows a Kernel-lite coordination pattern inherited from the testproject1 architecture: a deterministic, non-LLM Kernel owns the coordination state (event log, leases, queues), while the permanent LLM brain handles planning, decomposition, and routing decisions.

```
           ┌─────────────────────────────────────────────────────────┐
           │                    tiwa-brain-code                      │
           │                                                         │
           │  ┌──────────┐    ┌──────────┐    ┌──────────┐          │
           │  │  Kernel  │◄──►│Brain LLM │◄──►│  Router  │          │
           │  │(event log)│    │(permanent)│    │(quota/capacity)│      │
           │  └──────────┘    └──────────┘    └──────────┘          │
           │         │             │                 │                │
           │         ▼             ▼                 ▼                │
           │  ┌──────────┐  ┌──────────┐    ┌──────────────┐        │
           │  │Adapters  │  │Workspace │    │Provider Pool │        │
           │  │(hermes)  │  │(files)   │    │(12+ free     │        │
           │  │(kilo)    │  │          │    │models)       │        │
           │  │(opencode)│  │          │    │              │        │
           │  │(cline)   │  │          │    │              │        │
           │  │(codemuff)│  │          │    │              │        │
           │  └──────────┘  └──────────┘    └──────────────┘        │
           └─────────────────────────────────────────────────────────┘
```

---

## 2. Problem Statement

The operator currently uses five separate agentic coding applications:

| Tool | Primary Use | Free Model Access |
|------|-------------|-------------------|
| **Claude Code** | General-purpose coding, deep reasoning | No (paid only) |
| **OpenCode** | Free-model coding, OpenRouter integration | Yes (OpenRouter) |
| **Hermes** | Free-model coding, Nous portal | Yes (Nous portal) |
| **Kilo Code** | Local/edge coding, Ollama | Yes (Kilo Gateway) |
| **CodeBuff** | Code review, refactoring | Variable |

Each tool has its own:
- CLI syntax and flags
- Session management (resume, continue, session IDs)
- Model selection mechanism
- Quota model and free-tier limits
- Failure modes and error messages
- Configuration files and auth flows

The operator spends cognitive overhead switching contexts, managing credentials across five apps, and deciding which tool + model combination to use for each task. Free model quotas are wasted because no single application tracks capacity across all providers. Recovery from failures (rate limits, model exhaustion) requires manual intervention.

**The core insight from testproject1**: A deterministic Kernel that owns coordination state, plus adapters that encapsulate per-tool CLI behavior, plus a quota-aware router that tracks provider capacity, eliminates almost all of this overhead. The permanent LLM brain adds the missing piece: context persistence and intelligent routing across all five tools simultaneously.

---

## 3. Goals and Non-Goals

### Goals

| # | Goal | Priority |
|---|------|----------|
| G1 | Unify all five coding tools behind a single CLI entry point | Must |
| G2 | Maximize utilization of free-tier LLM quotas across all providers | Must |
| G3 | Preserve context and conversation history across tool switches | Must |
| G4 | Automatically recover from model exhaustion and rate limits | Must |
| G5 | Run a permanent LLM brain for planning and routing decisions | Must |
| G6 | Be buildable in 2–4 weeks by a single developer | Must |

### Non-Goals

| # | Non-goal | Rationale |
|---|----------|-----------|
| NG1 | Replace the underlying CLIs | The five tools handle the heavy lifting (file editing, tool use, agentic loops); tiwa-brain-code orchestrates them |
| NG2 | Build a GUI dashboard | The MVP is CLI-first; a web dashboard is a future phase |
| NG3 | Support multi-user collaboration | Single operator only (like testproject1's "one human operator" model) |
| NG4 | Achieve zero cost | Free models have limits; the system optimizes within them, not eliminates cost |
| NG5 | Be IDE-agnostic at the plugin level | Integration is via CLI invocation, not IDE extensions |
| NG6 | Store all conversation history indefinitely | Memory is compacted; old context is summarized and pruned |

---

## 4. Architecture Overview

### 4.1 The Three-Layer Split

```
┌─────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                        │
│  CLI: `brain <prompt>` | `brain resume <session>`          │
│  Future: Web dashboard, API server (Phase 2)                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                        BRAIN LAYER                          │
│  Permanent LLM (Claude/OpenRouter) — context manager        │
│  • Holds conversation state in memory                        │
│  • Decides which tool + model to dispatch to                │
│  • Requests compaction when context exceeds threshold       │
│  • Never edits project files directly (routes through CLI)  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      ORCHESTRATION LAYER                    │
│  Kernel (deterministic, non-LLM)                            │
│  • Owns the append-only event log                          │
│  • Manages leases, session state, worktree assignments      │
│  • Enforces invariants (no direct file writes by the brain) │
│                                                             │
│  Router (quota-aware)                                       │
│  • Queries all provider APIs for current free capacity      │
│  • Routes requests to the best available deployment         │
│  • Tracks per-model, per-account, per-provider quotas       │
│                                                             │
│  Adapters (one per CLI tool)                                │
│  • Build argv lists from templates                          │
│  • Parse session IDs from output                            │
│  • Classify failures (rate limit, model gone, crash)        │
│  • Measure and record capabilities (resumption, model swap) │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Key Design Principles (Inherited from testproject1)

**P1 — Kernel owns state.** The permanent LLM brain never writes to the coordination store directly. It requests state transitions through the Kernel API. The Kernel writes an append-only event log. This survives crashes and provides full auditability.

**P2 — Adapters are data-driven.** Each CLI tool has an adapter whose behavior is defined by argv templates and a measured capability table (like testproject1's `MEASURED_CAPS` in `generic.py`). Adding a new tool requires no code change — only a new profile in the config.

**P3 — Capabilities are measured, not assumed.** Every CLI capability (`headless`, `can_resume`, `can_swap_model_on_resume`, `reports_session_id`) starts as `False` and is only flipped to `True` after a live observation run. This prevents the system from promising features it can't deliver.

**P4 — Quota drives routing.** Provider free-quota pools are measured before routing. The router never sends a request to a model whose quota is exhausted or near its limit.

**P5 — Failures are classifiable.** Every CLI failure is classified into one of: rate-limited, model-unavailable, authentication-failed, crashed, or unknown. Each class has a prescribed recovery action (different model, different tool, cooldown, manual intervention).

### 4.3 State Model

The Kernel maintains three stores:

| Store | Format | Ownership | Purpose |
|-------|--------|-----------|---------|
| **Event log** | Append-only JSONL in `~/.tiwa/events/` | Kernel only | All state transitions, immutable, hash-chained |
| **Views** | Generated Markdown in `~/.tiwa/views/` | Kernel (read-only from brain) | Human-readable ledger, queue, status |
| **Workspaces** | Git worktrees under `~/tiwa-work/` | Adapters + Harness | Isolated per-task file trees |

---

## 5. Component Design

### 5.1 The Brain LLM

**Role:** Permanent, always-running context manager and routing decider.

**Model:** Claude 3.5 Sonnet (via Anthropic API) as primary. OpenRouter as fallback for redundancy. Runs in a persistent Python async process (or a lightweight VM socket that reconnects on disconnect).

**Responsibilities:**
- Maintain a rolling window of the conversation history (pruned via summarization when it exceeds 80% of the model's context window)
- When the user issues a request, decompose it into sub-tasks and decide which tool+model combination to dispatch each to
- Monitor adapter feedback (quota status, failure classification) and adjust routing accordingly
- Never directly invoke file writes — all changes go through CLI tool dispatch

**Non-responsibilities:**
- Does not answer questions (the brain is an orchestrator, not a chatbot)
- Does not make HTTP API calls directly (uses provider API only for quota checks)
- Does not manage the event log (the Kernel does)

**Context compaction:** When the conversation history exceeds 80% of the context window, the brain requests the Kernel to summarize the oldest portion into a "memory file" and prune it from the active context. The memory file is indexed by a simple keyword vector for potential RAG retrieval.

### 5.2 The Kernel

A small, deterministic, non-LLM Python module (`brain/kernel/`) that:

- **Event log:** Appends JSONL entries to `~/.tiwa/events/YYYY-MM-DD.jsonl`. Each entry is a typed state transition: `REQUEST_RECEIVED`, `DISPATCH_STARTED`, `DISPATCH_SUCCEEDED`, `DISPATCH_FAILED`, `SESSION_CREATED`, `SESSION_RESUMED`, `ROUTING_DECISION`, `CONTEXT_COMPACTED`, `MEMORY_CREATED`.
- **Lease management:** Issues time-limited leases to adapters so two don't claim the same task simultaneously. Uses `.lock` sidecar files (per Windows platform rules from testproject1).
- **Session registry:** Tracks active sessions across all five tools, their last-known state, and resume tokens.
- **Views:** Generates `ledger.md`, `queue.md`, `status.md` from the event log on every write (maintaining I13 invariant: views ≡ projection of log).

### 5.3 The Router

A quota-aware routing module (`brain/router/`) that:

1. **Queries provider APIs** (OpenRouter, Nous, OrcaRouter, ZAI, Zyphra, Ollama) for current free-tier status. Uses the OpenAI-compatible `/v1/chat/completions` surface (per QuotaGate decision D2).
2. **Maintains a capacity model:** Each model has a `requests_remaining` counter, a `reset_time`, and a `last_checked` timestamp. Counters are decayed by actual usage (each dispatch decrements the counter; a refresh fetches the actual value from the provider).
3. **Selects deployments** based on: required capability (does the tool support session resumption? model swapping?), current capacity (which models still have quota?), and priority (which provider/tool is preferred for this task type?).
4. **Handles exhaustion:** When all candidate models for a task are exhausted, falls back to the next provider tier, and eventually to a cooldown queue that waits for reset.

### 5.4 The Adapters

Implements the same `BaseAdapter` protocol from testproject1's `src/fleet/adapters/base.py`, specialized for each of the five target CLIs.

#### 5.4.1 Capability Table

Adapted from `src/fleet/adapters/generic.py:MEASURED_CAPS`, extended for tiwa-brain-code's five targets. **All values are [GUESS] until re-measured against the actual CLIs.**

| CLI | headless | can_resume | can_swap_model_on_resume | reports_session_id | Notes |
|-----|----------|------------|--------------------------|---------------------|-------|
| hermes | True | True | **?** | True | Prints "Resume this session with: hermes --resume \<id\>" |
| kilo | True | True | **?** | False | Uses `--continue` flag; no session ID |
| opencode | True | True | **?** | False | Uses `--continue` flag; no session ID |
| cline | True | **?** | **?** | **?** | Uses `--id \<session-id\>`; resume untested |
| codemuff | True | **?** | **?** | **?** | To be measured |

**Status legend:**
- **True** = Measured in testproject1's live spike S-A1 (2026-10-22)
- **False** = Default; no measurement available
- **?** = To be measured as part of tiwa-brain-code implementation Milestone 1

#### 5.4.2 Adapter Protocol

Each adapter implements:

```python
class Adapter:
    name: str                    # e.g., "hermes", "kilo", "opencode", "cline", "codemuff"

    @property
    def caps(self) -> Caps:     # Measured capabilities
        ...

    def build_argv(self, profile: dict, mode: "new" | "resume",
                   prompt: str, cwd: str, session: str | None) -> list[str]:
        """Build the argv list for spawning this CLI."""
        ...

    def parse_session_id(self, log_text: str) -> str | None:
        """Extract a session ID from the CLI's output, if it reports one."""
        ...

    def classify(self, exit_code: int | None, log_tail: str) -> str:
        """Classify a failure: 'rate_limited', 'model_gone', 'auth_failed', 'crashed', 'ok', 'unknown'."""
        ...
```

#### 5.4.3 Profiles

Profiles live in `~/.tiwa/profiles.toml`, modeled on testproject1's `agents.toml`:

```toml
[profiles.hermes-free]
adapter = "hermes"
model = "upstage/solar-mini4:free"
priority = 10
roles = ["implement", "review", "plan"]
argv_new = ["hermes", "chat", "--oneshot", "-q", "{prompt}", "--yolo", "--cli", "--in", "{cwd}"]
argv_resume = ["hermes", "chat", "--oneshot", "-q", "{prompt}", "--resume", "{session}", "--yolo", "--cli", "--in", "{cwd}"]

[profiles.kilo-auto]
adapter = "kilo"
model = "kilo/kilo-auto/free"
priority = 20
roles = ["implement", "review"]
argv_new = ["kilo", "-m", "{model}", "run", "{prompt}", "--dir", "{cwd}", "--auto"]
argv_resume = ["kilo", "-m", "{model}", "run", "{prompt}", "--dir", "{cwd}", "--auto", "--continue"]
```

### 5.5 The Harness

The Harness manages the lifecycle of a dispatched task:

1. **Create worktree:** Clone or create a shallow Git worktree for the task (isolated file tree, per testproject1's P3 principle).
2. **Build argv:** Ask the adapter to build the argv list from the profile template.
3. **Spawn process:** Use `subprocess.Popen` with the argv list (never `shell=True`). Use `plat.resolve_executable` to peel npm `.cmd` shims (Windows platform constraint from testproject1).
4. **Monitor:** Stream stdout/stderr, watch for session IDs, classify exit codes.
5. **Lease:** Hold a Kernel lease while the task runs; renew every 30 seconds.
6. **Cleanup:** On completion (success or failure), kill the process tree (using `plat.process_info` for PID + creation time matching, per testproject1's fleet-spawning rules) and release the lease.

---

## 6. MVP Scope

The MVP (`tiwa-brain-code v1.0`) delivers a single CLI entry point that:

1. Accepts a prompt from the user: `brain <prompt>`
2. The brain LLM decomposes the prompt into 1–N sub-tasks (for v1, assume 1 sub-task — the brain decides which tool+model to use)
3. The router queries all configured provider APIs for current free capacity
4. The router selects the best available deployment (tool + model combination with remaining quota and required capabilities)
5. The harness dispatches the task to the selected CLI via argv, in an isolated worktree
6. Results stream back to the terminal; the brain observes the output and classifies the outcome
7. If the task succeeds, the session is persisted (session ID or `--continue` token stored in the Kernel)
8. If the task fails with a recoverable error (rate limit, model gone), the router picks the next best deployment and retries (up to 3 retries, then cooldown)
9. All interactions are logged to the event log; views are generated for human inspection

**Out of MVP:**
- Multi-tool pipeline (one task split across multiple tools in sequence) — v1.1
- Web dashboard — v1.2
- RAG-based memory retrieval — v1.2
- Local model support (Ollama-only deployments) — v1.3

---

## 7. Implementation Roadmap

### Milestone 1: Core Infrastructure (Week 1)

| Task | Description | Deliverable |
|------|-------------|-------------|
| M1.1 | Kernel: event log writer | Append-only JSONL writer with hash chaining |
| M1.2 | Kernel: view generator | Generated `ledger.md`, `status.md`, `queue.md` |
| M1.3 | Adapter base: Capability system | `Caps` dataclass + `BaseAdapter` protocol (ported from testproject1) |
| M1.4 | Adapter: Hermes CLI | argv templates + session ID parsing + failure classification |
| M1.5 | Adapter: OpenCode CLI | argv templates + model selection + failure classification |
| M1.6 | Adapter: Kilo CLI | argv templates + `--continue` parsing + failure classification |
| M1.7 | Adapter: Cline CLI | argv templates + session ID parsing + failure classification |
| M1.8 | Adapter: CodeBuff CLI | argv templates + failure classification |

**Acceptance test:** `brain "print the word ok and exit"` dispatches to each of the five tools successfully and logs the result. Capabilities are observed (not assumed) for all five.

### Milestone 2: Router and Quota Tracking (Week 2)

| Task | Description | Deliverable |
|------|-------------|-------------|
| M2.1 | Provider API clients | Thin wrappers for OpenRouter, Nous, OrcaRouter, ZAI, Zyphra |
| M2.2 | Capacity model | Per-model quota counters with decay and refresh |
| M2.3 | Routing logic | Selects best deployment based on capability + capacity + priority |
| M2.4 | Retry logic | Recovery ladder: L0 retry, L1 model swap, L2 tool switch, L3 cooldown |
| M2.5 | Lease system | Time-limited leases via `.lock` sidecar files |
| M2.6 | Worktree manager | Shallow Git worktree creation and teardown |

**Acceptance test:** `brain "print the word ok and exit"` succeeds even when the primary model is rate-limited — the router automatically falls back to the next available deployment.

### Milestone 3: Brain LLM Integration (Week 3)

| Task | Description | Deliverable |
|------|-------------|-------------|
| M3.1 | Brain process | Persistent async process (or VM socket) hosting the LLM |
| M3.2 | Context window management | Rolling window with summarization trigger at 80% |
| M3.3 | Sub-task decomposition | LLM prompts to split user requests into routed sub-tasks |
| M3.4 | Session persistence | Resume tokens stored in Kernel, retrievable across invocations |
| M3.5 | Failure classification relay | Brain observes adapter classification and adjusts routing |

**Acceptance test:** `brain "explain the git history of this repo"` runs end-to-end — the brain decomposes, the router selects, the harness dispatches, results return, and the session is persisted. A subsequent `brain resume` continues the session.

### Milestone 4: Polish and Hardening (Week 4)

| Task | Description | Deliverable |
|------|-------------|-------------|
| M4.1 | Config management | TOML config file + CLI flags |
| M4.2 | Logging and observability | Structured logs to `~/.tiwa/events/` |
| M4.3 | Error handling | Graceful degradation when a provider API is unreachable |
| M4.4 | Documentation | README, quickstart, architecture guide |
| M4.5 | Test suite | pytest suite covering Kernel, Router, Adapters |

**Acceptance test:** Full regression suite passes. README has a working quickstart.

---

## 8. Context and Memory Model

### 8.1 Active Context

The brain LLM maintains a rolling window of the conversation history in memory (a Python `list` of message dicts in the persistent process). When the window exceeds 80% of the model's context limit (200K tokens for Claude 3.5 Sonnet), the brain requests the Kernel to:

1. **Summarize** the oldest 25% of messages into a condensed memory block
2. **Store** the memory block as a file in `~/.tiwa/memory/` with a timestamp and keyword tags
3. **Prune** those messages from the active window

### 8.2 Memory Files

Each memory file is a Markdown document:

```markdown
---
task: "explain the git history of this repo"
timestamp: "2026-10-28T14:32:00Z"
tags: [git, history, explanation]
---

## Summary

The repo has 37 commits across 3 branches. The main branch tracks upstream/main.
Key decisions: D-28 (reprioritize cline profile), D-24 (enable capabilities).
```

### 8.3 Retrieval (Phase 2)

In v1.2, a simple keyword-based retrieval is added: when the user's new prompt contains tags that match a memory file, that file is included in the brain's context as a "relevant prior context" note. RAG is not needed for v1.

### 8.4 Context Isolation

Each dispatched task runs in its own Git worktree. The brain's active context is tied to the user's session ID — switching to a different project or task creates a new context window. This prevents cross-contamination.

---

## 9. Provider Integration

### 9.1 Provider Inventory

From `docs/free-models.md`, adapted for tiwa-brain-code's routing needs.

#### Tier 1: Hermes (Nous Portal) — 50 requests/day per key

| Model ID | Context Window | Notes |
|----------|---------------|-------|
| `upstage/solar-mini4:free` | 32K | Fastest, sufficient for most tasks |
| `meituan/longcat-2.5-preview:free` | 64K | Strong reasoning, good for planning |
| `poolside/laguna-xs-2.1:free` | 32K | Lightweight, fast | 
| `poolside/laguna-s-2.1:free` | 64K | Balanced speed/reasoning |
| `stepfun/step-3.7-flash:free` | 128K | Long-context capable |
| `reflection/beam-1.0-501b-a23b:free` | 128K | Strongest free model |
| `ornith/ornith-1.5-122b:free` | 128K | Good for complex tasks |

**Auth:** `HERMES_API_KEY` env var. No account-wide rate limit (per operator observation).

#### Tier 2: OrcaRouter (via `pi` CLI) — 50 requests/day per key

| Model ID | Context Window | Notes |
|----------|---------------|-------|
| `deepseek/deepseek-v4-flash-free` | 64K | Primary model |
| `z-ai/glm-5.3-flash-free` | 128K | Swap target (measured resume+swap capability) |
| `tencent/hy4-preview-free` | 64K | Swap target |
| `tencent/hy3-free` | 32K | Swap target |

**Auth:** `ORCAROUTER_API_KEY` env var. Account-wide 50 req/day ceiling.

#### Tier 3: ZAI (Zhiping) — 10 requests/day per key, per model

| Model ID | Context Window | Notes |
|----------|---------------|-------|
| `glm-4.5-flash` | 128K | Primary, rate-limited |
| `glm-4.6v-flash` | 128K | Variant |
| `glm-4.7-flash` | 256K | New model, untested |

**Auth:** `ZAI_API_KEY` env var. **Note:** Concurrency is typically 1 request. Must serialize.

#### Tier 4: Kenari — 50 requests/day account-wide

| Model ID | Context Window | Notes |
|----------|---------------|-------|
| `kenari/nemotron-3-ultra-550b-a55b:free` | 128K | Only model to use (shared account ceiling) |

**Auth:** `KENARI_API_KEY` env var. Account-wide 50 req/day — do not mix models.

#### Tier 5: Ollama (local/cloud)

| Model ID | Context Window | Notes |
|----------|---------------|-------|
| `beam:cloud` / `ollama-cloud/beam` | 1M | Requires `OLLAMA_API_KEY` env var |

**Auth:** `OLLAMA_API_KEY` env var. Billed per-token with generous free tier (128K output limit).

### 9.2 Routing Strategy

The router uses a **capability-weighted capacity model**:

1. **Capability filter:** If the task requires session resumption (brain decided to continue a session), only deployments where `caps.can_resume == True` are candidates. If model swapping is needed (recovery L1), only deployments where `caps.can_swap_model_on_resume == True` are candidates.
2. **Capacity filter:** Among candidates, exclude any model that has been observed to be exhausted (quota == 0 or rate-limited within the last 60 seconds).
3. **Priority sort:** Sort remaining candidates by `profile.priority` (lower is better). The first candidate is selected.
4. **Cooldown:** If no candidates survive the filter, the task enters a cooldown queue. It is retried when the next quota reset occurs (the router polls for resets every 30 seconds).

### 9.3 Quota Refresh Strategy

| Provider | Refresh Method | Frequency |
|----------|---------------|-----------|
| Hermes | API `/v1/models` + usage header | Every 60s per active session |
| OrcaRouter | Polling `GET /v1/models` with auth | Every 30s |
| ZAI | No quota API; estimate from 429 responses | Reactive (observe rate limits) |
| Kenari | No quota API; estimate from 429 responses | Reactive |
| Ollama | No quota API; estimate from 429 responses | Reactive |

**Note [GUESS]:** Some providers (ZAI, Kenari) do not expose quota APIs. The router must react to 429 responses with `429/1302` (rate limit) or `429/1305` (service overloaded) codes and apply exponential backoff. This is a best-effort model, not a hard guarantee.

---

## 10. Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| Q1 | Does `hermes chat` support `--resume` with a session ID across different models? | Determines if L1 recovery (model swap) works for Hermes | [GUESS] — spike result says "not tested" |
| Q2 | Does `kilo` expose a model flag (`-m`) for model swapping on resume? | Determines if L1 recovery works for Kilo | [GUESS] — adapter table says `can_swap_model_on_resume: False` |
| Q3 | Does `cline` support `--continue` / `--id`? | Determines if Cline can resume at all | [GUESS] — table says `can_resume: False` |
| Q4 | Does `codemuff` (CodeBuff) have a CLI mode with model selection? | Need to verify the tool exists and what its CLI looks like | [UNKNOWN] — needs research |
| Q5 | Can OpenRouter route to local Ollama models? | Determines if one key manages both cloud + local routing | [UNKNOWN] — needs testing |

---

## 11. Risks and Mitigations

### R1: The five CLIs are not designed for programmatic orchestration

**Risk:** Each CLI was designed for interactive use. Their output may not be machine-parseable, their exit codes may be unreliable, and their session management may not support non-interactive resume.

**Mitigation:** The capability measurement system (adapted from testproject1) means we discover these limitations empirically, not by assumption. The adapter's `classify()` function catches failures and routes them through the recovery ladder. Worst case, a task falls back to the human-in-the-loop path (cooldown queue + notification).

### R2: Free quotas change or disappear without notice

**Risk:** A provider could end a free promotion, reduce daily quotas, or change their API surface at any time (as documented in `agents.toml:142` — "The free promotion for this model has ended").

**Mitigation:** The router's capacity model is reactive — it observes 429s and rate-limit headers in real-time. When a model is exhausted, it moves to the next. The operator is alerted via the status view when a provider's capacity drops below a threshold. No single provider is a hard dependency.

### R3: The brain LLM's cost grows unbounded

**Risk:** A permanent LLM brain that maintains context and makes routing decisions could accumulate significant cost over time, especially as conversation history grows.

**Mitigation:** The context compaction model summarizes old context into memory files, capping the active window at ~200K tokens. The brain only makes routing decisions (not file edits), so its output is bounded. Costs are tracked per-session in the event log. For the single-operator use case, expected cost is < $5/month.

### R4: Cross-tool session continuity is fragile

**Risk:** When the brain routes a sub-task to Tool A but the follow-up requires Tool B (different session ID format, no resume capability), context is lost.

**Mitigation:** The adapter capability table records which tools support resume and model-swap. If a tool doesn't support resume, the brain injects the prior context as prompt text (a brief summary) rather than relying on native session continuation. This is slower but always works.

### R5: Provider APIs are unreliable or rate-limited

**Risk:** The router's quota-check polling could itself be rate-limited by providers, creating a feedback loop where the system can't tell if it has quota.

**Mitigation:** The router caches capacity data for 60–120 seconds and degrades gracefully: if the quota API is unreachable, it uses the last-known values and falls back to reactive rate-limit detection (429 response handling). Provider-specific backoff strategies are configured per-provider.

---

*Status: candidate-tier proposal. Nothing here has been run. Provider capabilities are [OBSERVED] from existing docs; CLI behaviors marked "not tested" remain [GUESS] — they must be re-measured against the actual CLIs during Milestone 1. To adopt any element, promote it through the target project's own governance, gate and decision record.*
