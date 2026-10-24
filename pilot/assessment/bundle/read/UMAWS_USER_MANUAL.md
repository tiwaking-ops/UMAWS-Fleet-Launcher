---
title: "UMAWS Fleet / QuotaGate — User Manual"
version: "1.0.0"
author: "OpenCode (Nemotron 3 Ultra)"
date: "2026-10-24"
status: "Pilot P-01 — production-ready for supervised use"
---

# UMAWS Fleet / QuotaGate User Manual

A comprehensive guide to operating the **Ultimate Multi-Agent Workflow System (UMAWS) Fleet** with the **QuotaGate** quota-aware LLM gateway.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Kernel (`pmk`) Command Reference](#kernel-pmk-command-reference)
5. [QuotaGate Gateway](#quotagate-gateway)
6. [Fleet Dispatcher & Profiles](#fleet-dispatcher--profiles)
6. [Projects & Tasks](#projects--tasks)
7. [Context Sync (Caliber)](#context-sync-caliber)
8. [Monitoring & Debugging](#monitoring--debugging)
9. [Configuration](#configuration)
10. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HUMAN OPERATOR                               │
│  (goals · envelopes · queue approvals · stop-the-line)             │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   LLM OVERSEER (OpenCode)│
                    │  plans, adjudicates,      │
                    │  reviews, creates tasks   │
                    └────────────┬────────────┘
                                 │ requests via pmk
                    ┌────────────▼────────────┐
                    │      KERNEL (pmk)       │
                    │  event log · leases ·     │
                    │  merge queue · sentinel  │
                    │  briefing generator      │
                    └────────────┬────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
┌───────▼────────┐     ┌────────▼────────┐     ┌────────▼────────┐
│    HARNESS     │     │    CALIBER      │     │   QUOTAGATE     │
│  worktrees     │     │  context sync   │     │  quota gateway  │
│  leases        │     │  lint + revert  │     │  HMAC auth      │
│  oracles       │     │  I15–I17        │     │  events outbox  │
└────────────────┘     └─────────────────┘     └─────────────────┘
```

**Key Components**

| Component | Purpose | Location |
|-----------|---------|----------|
| **Kernel (`pmk`)** | Single-writer coordination state (event log, leases, tasks, merge queue) | `src/pmk/` |
| **Fleet Dispatcher** | Assigns tasks to profiles, runs recovery ladder, manages concurrency | `src/fleet/` |
| **QuotaGate** | Quota-aware OpenAI-compatible proxy with HMAC auth, events outbox | `src/quotagate/` |
| **Caliber Context Sync** | Generates/refreshes `AGENTS.md`, `CLAUDE.md`; lint (I15), drift (I16), revert (I17) | `src/pmk/context.py` |
| **Console** | FastAPI dashboard (7 tabs) for live monitoring | `src/console/` |

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| **WSL2 (Ubuntu)** | — | Repository **must** live on Linux filesystem (`~/projects/...`), not `/mnt/c/` |
| **Python** | ≥ 3.11 | `tomllib` required (stdlib in 3.11+) |
| **Node.js** | LTS | For Caliber (`npm install -g @rely-ai/caliber`) |
| **Git** | ≥ 2.28 | `extensions.worktreeConfig = true` |
| **OpenCode** | Latest | Overseer + workers |
| **Caliber** | 1.55.2 (pinned) | `npm install -g @rely-ai/caliber@1.55.2` |
| **Upstream proxies** | — | `hermes proxy start` (port 8645), `omniroute serve` (port 20128) |

**Python dependencies** (pinned in `requirements.lock`):

```bash
fastapi uvicorn httpx tzdata pytest
```

---

## Quick Start

### 1. Clone / Open Repository

```bash
cd ~/projects/umaws-gateway-pilot   # or your repo path
```

### 2. Activate Virtual Environment

```bash
. .venv/bin/activate   # Linux/WSL
# or
.venv\Scripts\activate # Windows PowerShell
```

### 3. Start Upstream Proxies (two terminals)

**Terminal 1 — Hermes (Nous Portal)**
```bash
hermes proxy start
# Listens on http://127.0.0.1:8645
```

**Terminal 2 — OmniRoute (Cohere)**
```bash
export OMNIROUTE_API_KEY="your-key"
omniroute serve
# Listens on http://127.0.0.1:20128
```

### 4. Start QuotaGate Gateway

```bash
export QUOTAGATE_CONFIG=src/quotagate/config.toml
export PYTHONPATH=src
python -m uvicorn quotagate.main:app --host 127.0.0.1 --port 8000 --log-level info
```

Verify:
```bash
curl http://127.0.0.1:8000/v1/quotagate/health
# {"ok": true, "service": "quotagate", "milestone": "m1"}
```

### 5. Run Kernel Sentinel (sanity check)

```bash
python -m pmk.cli sentinel
# All invariants I1, I3, I4, I5, I6, I7, I8′, I13, I14, I15, I16 → ok
```

### 6. Launch Overseer (OpenCode)

```bash
opencode
# Overseer prompt loads from pilot/g3-opencode-handover.md
# Loop: pmk brief → create tasks → dispatcher fills slots → harvest
```

---

## Kernel (`pmk`) Command Reference

### Core Commands

| Command | Description |
|---------|-------------|
| `pmk init` | Create layout, first event, pins |
| `pmk status` | One-screen status (tasks, leases, pins) |
| `pmk brief --role overseer\|worker` | Deterministic briefing from log alone |
| `pmk sentinel` | Check all invariants (I1, I3, I4, I5, I6, I7, I8′, I13, I14, I15, I16) |
| `pmk views` | Regenerate `ledger.md`, `status.md`, `queue.md` |
| `pmk sweep` | Expire leases past TTL |
| `pmk stop` / `pmk resume` | Stop-the-line (freeze promotions + new leases) |

### Task Commands

```bash
# Create & admit a task
pmk task create "Implement feature X" \
  --type implement \
  --goal-ref G-QG-M3 \
  --write "gateway/quotagate/strategies.py" \
  --read "gateway/" \
  --oracle "pytest -q tests/quotagate/test_strategies.py" \
  --evidence oracle_results diff_scope premise_check \
  --budget-tokens 120000 --budget-minutes 45

# List tasks
pmk task list [--state READY|LEASED|SUBMITTED...]

# Show task detail
pmk task show T-0007
```

### Lease Commands (used by Harness)

```bash
pmk claim T-0007 --profile hermes-oneshot --role implement
pmk renew T-0007 --fence 3 --digest "files_changed=5 log_bytes=1234 wall_s=120"
pmk submit T-0007 --fence 3 --bundle path/to/bundle.json
pmk verify T-0007 --fence 3 [--failed --reason "..."]
pmk integrate T-0007 --fence 3 [--commit <sha>]
pmk revoke T-0007 --fence 3 --reason "timeout"
```

### Context Sync (Caliber)

```bash
pmk context sync --dry-run   # preview diff, lint, score
pmk context sync             # full: lint → score → merge queue → CONTEXT_SYNCED
pmk context revert <seq>     # one-command rollback
pmk context drift            # check for out-of-band edits (I16)
pmk context lint             # run I15 deterministic lint
pmk context score            # read-only generator score
```

### Gateway Integration (M5)

```bash
# Pull events from gateway into Kernel log
pmk gateway ingest --since 0 --url http://127.0.0.1:8000

# Verify gateway config hash matches pinned config.toml
pmk gateway config-hash --url http://127.0.0.1:8000
```

### Human Queue (Class K Decisions)

```bash
pmk queue add --topic "Enable Caliber auto-sync" \
  --option "Enable now" --option "Stay dry-run" \
  --recommended "Enable now" --safe-default "Stay dry-run" \
  --class-k --details "See pilot/g4-auto-sync.md"

pmk queue list
pmk queue decide Q-004 "Enable now"
```

### Project Lifecycle

```bash
pmk project init --brief "Build a CSV→Markdown converter" --path .
pmk project status
pmk project run --seconds 300   # run Conductor+Dispatcher for 5 min
pmk project close-check
pmk project pause --reason "awaiting human"
pmk project resume
```

---

## QuotaGate Gateway

### Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/v1/chat/completions` | POST | **HMAC** | Main proxy — enforces quota, records usage/latency/provenance |
| `/v1/models` | GET | **HMAC** | Lists available deployments (rewrites `/v1/` prefix) |
| `/v1/quotagate/availability` | GET | — | Per-deployment limits, usage, latency, `earliest_available_utc` |
| `/v1/quotagate/provenance` | GET | — | Served models per task or time window |
| `/v1/quotagate/events` | GET | — | Events outbox: `?since=<seq>` |
| `/v1/quotagate/config-hash` | GET | — | SHA-256 of pinned `config.toml` |
| `/v1/quotagate/health` | GET | — | Liveness check |

### Capability Token (HMAC)

**Header:** `x-quotagate-capability-token: <base64(payload)>.<base64(sig)>`

**Payload (JSON):**
```json
{
  "lease_id": "T-0007-3",
  "fence": 3,
  "task_id": "T-0007",
  "role": "implement",
  "exp": 1792795000
}
```

**Secret:** Loaded from `~/.config/umaws/quotagate.key` or env `QUOTAGATE_HMAC_SECRET`.

**Generate a token (Python):**
```python
import hmac, hashlib, base64, json, time
secret = b"your-32-byte-secret"
payload = {"lease_id": "T-0007-3", "fence": 3, "task_id": "T-0007", "role": "implement", "exp": time.time()+3600}
payload_bytes = json.dumps(payload, separators=(',',':')).encode()
payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode().rstrip('=')
sig = hmac.new(secret, payload_bytes, hashlib.sha256).digest()
sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip('=')
token = f"{payload_b64}.{sig_b64}"
```

### Request Headers (Harness → Gateway)

| Header | Purpose |
|--------|---------|
| `x-quotagate-combo` | Combo name (e.g., `free-coding`) |
| `x-quotagate-profile` | Profile ID (e.g., `hermes-oneshot`) |
| `x-quotagate-task` | Task ID (e.g., `T-0007`) |
| `x-quotagate-fence` | Lease fence |
| `x-quotagate-lease` | Lease ID |
| `x-quotagate-role` | `implement` / `verify` / `plan` |
| `x-quotagate-exclude-family` | Verifier independence (e.g., `anthropic`) |
| `x-quotagate-capability-token` | **HMAC token** (required) |

### Response Headers (Gateway → Harness)

| Header | Meaning |
|--------|---------|
| `X-QuotaGate-Deployment` | Deployment that served the request |
| `X-QuotaGate-Strategy` | Routing strategy used |
| `X-QuotaGate-Attempt` | Failover attempt number (1-based) |
| `X-QuotaGate-Latency-Ms` | Round-trip latency |
| `x-omniroute-decision` | Upstream routing decision (provider) |

---

## Fleet Dispatcher & Profiles

### Profiles (`agents.toml`)

Each profile defines a CLI agent the Fleet can dispatch.

```toml
[[profile]]
id = "hermes-oneshot"
adapter = "hermes"
family = "anthropic"
priority = 10
max_concurrent = 4
via_gateway = false
roles = ["implement"]
argv_new = ["hermes", "chat", "--oneshot", "-q", "{prompt}", "--yolo", "--cli", "--in", "{cwd}"]
```

**Key fields**

| Field | Meaning |
|-------|---------|
| `adapter` | One of `hermes`, `kilo`, `pi`, `cline`, `opencode` |
| `family` | Model family for verifier independence (D-L12) |
| `priority` | Lower = higher priority |
| `max_concurrent` | Concurrency cap per profile |
| `via_gateway` | `true` = scrub env, route through QuotaGate; `false` = direct CLI |
| `argv_new` / `argv_resume` | Command templates with `{prompt}`, `{cwd}`, `{session}`, `{model}` |
| `models` | Interchangeable models for L1 recovery (only `pi` has this today) |

### Dispatcher Commands

```bash
# Status grid
pmk fleet status

# List profiles
pmk fleet profiles

# Enable / disable / cool a profile
pmk fleet enable hermes-oneshot
pmk fleet disable pi-orca-deepseek --reason "rate limited"
pmk fleet cool hermes-oneshot --minutes 60

# Run dispatch loop manually
pmk dispatch run --seconds 60
```

### Recovery Ladder (Automatic)

| Step | Trigger | Action |
|------|---------|--------|
| **L0** | `NETWORK` (first 3) | Retry same profile after 30s / 2m / 10m |
| **L1** | Profile supports resume | Resume session on **next eligible profile** (model swap if `can_swap_model_on_resume`) |
| **L2** | Profile cannot resume | Fresh session in same worktree with handoff note |
| **L3** | `max_restarts_per_task` reached | Revoke lease, bump fence, quarantine worktree, task → READY |
| **L4** | `attempts.max` reached | Task → BLOCKED, queue item for Overseer |

---

## Projects & Tasks

### Task Card (JSON in `.pm/tasks/T-####.json`)

```json
{
  "id": "T-0007",
  "title": "Implement priority strategy",
  "type": "implement",
  "goal_ref": "G-QG-M3",
  "risk_floor": "R2",
  "scope": { "write": ["gateway/quotagate/strategies.py"], "read": ["gateway/"] },
  "acceptance": {
    "oracles": ["pytest -q tests/quotagate/test_strategies.py"],
    "evidence_required": ["oracle_results", "diff_scope", "premise_check"]
  },
  "premises": [{ "id": "P1", "statement": "quota engine reservation API exists", "check": "grep -q 'def reserve' gateway/quotagate/quota.py" }],
  "budget": { "tokens": 120000, "wall_min": 45 },
  "depends_on": ["T-0005"],
  "attempts": { "max": 3 },
  "created_by": { "kind": "overseer", "session": "s-17" }
}
```

### Evidence Bundle (`.pm/evidence/EB-<task>-<fence>/bundle.json`)

Recorded **by the Harness**, never the worker:
- `outputs[]` — changed files with SHA-256
- `commands[]` — oracle commands with exit codes, stdout/stderr hashes
- `oracle_results[]` — pass/fail per oracle
- `premise_check` — `{refuted: bool}`
- `resolved_models[]` — gateway-stamped model per request
- `constitution_hash`, `context_hash` (I17)

### Verification Levels (V0–V2)

| Level | Who Runs | Independence |
|-------|----------|--------------|
| **V0** | Harness (mechanical) | — |
| **V1** | Kernel (oracles) | — |
| **V2** | Blind review via gateway | **Family exclusion enforced** (`x-quotagate-exclude-family`) |

**V2 Rule:** If only author's family has quota → gateway returns **429**, never same-family fallback.

---

## Context Sync (Caliber)

### File Classes

| Class | Files | Authority |
|-------|-------|-----------|
| **K** (Kernel-pinned) | `.pm/constitution.md`, `.pm/policy.toml`, Kernel code, gates | Hash-pinned, two-key |
| **C** (Caliber-managed) | `AGENTS.md`, `CLAUDE.md`, `CALIBER_LEARNINGS.md`, generated skills/rules | Auto-synced, linted (I15), recorded hash (I16), reversible |
| **H** (Human/agent guidance) | `docs/`, `.pm/memory/` | Normal artifact rules |

### Sync Flow

```
nightly timer / after N promotions / manual
        │
        ▼
Kernel creates worktree (fence = kernel.next_fence())
        │
        ▼
Caliber runs in worktree (model calls via gateway lane "context-sync")
        │
        ▼
Diff → Lint (I15) → Score (non-regression) → [>400 lines → blind V2] → Merge queue
        │
        ▼
CONTEXT_SYNCED event (before/after hashes, score, generator version, lane provider)
```

### Safety Controls (CIP Part B)

| Control | Purpose |
|---------|---------|
| **Constitution stub injection** | Harness injects `.pm/constitution.md` into every briefing; overrides generated files |
| **I15 Deterministic Lint** | Rejects: writes to `.pm/`, skip verification, authority override, credentials, off-allowlist URLs, token budget |
| **I16 Drift Check** | Sentinel hashes live C files; mismatch → finding |
| **I17 Bundle Hashes** | Every evidence bundle records `constitution_hash` + `context_hash` |
| **T4 Canary** | Planted injection + paraphrases → must be blocked/reverted |
| **Auto-revert** | Sentinel I15 violation → Kernel reverts to last clean `CONTEXT_SYNCED` |
| **Learning Ingestion** | `CALIBER_LEARNINGS.md` → `.pm/memory/patterns/` as **candidates only** (report §25.2) |

---

## Monitoring & Debugging

### Console Dashboard

Start:
```bash
python -m uvicorn console.main:app --host 127.0.0.1 --port 8080
```
Tabs: **Overview**, **Tasks**, **Leases**, **Profiles**, **Events**, **Gateway**, **Sentinel**.

### Key Logs

| Log | Location |
|-----|----------|
| Kernel event log | `.pm/events/YYYY-MM-DD.jsonl` (hash-chained, one JSON/line) |
| Pilot daily log | `pilot/daily-log.md` |
| Interrupt log | `pilot/interrupt-log.md` |
| Decisions log | `pilot/decisions.md` |
| Gateway events | `GET /v1/quotagate/events?since=<seq>` |
| Agent logs | `.pm/fleet/logs/<TASK>/<fence>-<index>.log` |
| Worktree order | `work/<TASK>-<fence>/.pmwork/ORDER.md` |

### Sentinel Invariants (checked by `pmk sentinel`)

| ID | Invariant |
|----|-----------|
| I1 | Hash chain verifies |
| I3 | Conservation (every task in exactly one state) |
| I4 | Stale fence never merged |
| I5 | Nothing promoted without promotion event + passing bundle |
| I6 | Every DONE task has matching bundle |
| I7 | Only Kernel timestamps trusted |
| I8′ | Pinned files match `pins.sha256` |
| I13 | Views equal projection |
| I14 | Silence recorded |
| I15 | No C-class file passes context lint |
| I16 | Hash mismatch on C-class = sentinel finding |
| I17 | Evidence bundles record `constitution_hash` + `context_hash` |

---

## Configuration

### Kernel Policy (`.pm/policy.toml`)

```toml
version = "p-2026-10-22"
project = { data_class = "internal" }

envelopes = { autonomy_ceiling = "R2", external_effects = "none", spend = { per_day = 0, per_task = 0 } }

gateway = {
  base_url = "http://127.0.0.1:8000/v1",
  lanes = {
    work         = { priority = "normal" },
    verify       = { priority = "normal", exclude_author_family = true, allow_family_fallback = false },
    "context-sync" = { priority = "low", providers_allow = [] },
    overseer     = { priority = "high", reserved_quota = true }
  }
}

context_sync = {
  mode = "auto",                     # G4 gate
  caliber_version = "1.55.2",
  managed_paths = ["AGENTS.md", "CLAUDE.md", "CALIBER_LEARNINGS.md"],
  triggers = { nightly = "03:00", after_promotions = 20 },
  gates = { lint = true, score_non_regression = { tolerance = 1 }, max_diff_lines = 400 },
  on_violation = "auto_revert",
  hooks_in_worker_worktrees = false
}

fleet = {
  max_total_agents = 100,
  min_free_ram_mb = 2048,
  stall_minutes = 15,
  quota_cooldown_s = 3600,
  quota_cooldown_max_s = 86400,
  unknown_cooldown_after = 2,
  unknown_cooldown_window_s = 600,
  unknown_cooldown_s = 900
}

[lease]
renew_every = 60
ttl_minutes = 20
```

### QuotaGate Config (`src/quotagate/config.toml`)

Key sections:
- **Upstreams** — `omniroute` (strip `/v1`), `hermes` (keep `/v1`)
- **Deployments** — model ID, family, upstream, context_window, measured latency
- **Quota Rules** — hierarchical: provider → deployment → daily, with `rolling_60s`, `rolling_24h`, `fixed_daily` (tz-aware)
- **Combos** — `free-coding` (use-it-or-lose-it), `cohere` (priority), `all-free` (headroom)

### Agents (`agents.toml`)

Profiles for Fleet dispatch. Edit `family` to enable verifier independence.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `pmk sentinel` fails I1 | Torn event log tail | `pmk` auto-repairs on restart; check disk space |
| `pmk sentinel` fails I8′ | Pinned file modified | `sha256sum -c .pm/pins.sha256` → restore or `pmk pins record` (class K) |
| Worker exits immediately | CLI not in PATH / auth missing | Verify `argv_new` resolves; check adapter credentials |
| Gateway 401 on `/chat/completions` | Missing/invalid capability token | Generate HMAC token; ensure `x-quotagate-capability-token` header sent |
| Gateway 429 structured | Quota exhausted at some scope | Check `/v1/quotagate/availability`; wait for `earliest_available_utc` or advance `FakeClock` in tests |
| `pmk gateway ingest` connection refused | Gateway not running | Start `uvicorn quotagate.main:app --port 8000` |
| `pmk gateway config-hash` MISMATCH | `config.toml` edited without pin update | `sha256sum src/quotagate/config.toml` → update `.pm/pins.sha256` (class K) |
| Caliber overwrites human edits | `managed_paths` includes file you edit | Move guidance to `docs/` or `.pm/memory/` (class H) |
| OpenCode worker fails with `free-models-per-day` | OpenCode daily limit hit | Use different profile or wait for reset |

### Reset Procedures

**Stop-the-line (human):**
```bash
touch pilot/STOP          # Phase 1: every agent checks at checkpoint
pmk stop                  # Phase 2: freezes promotions + new leases
# Investigate → fix → log in pilot/decisions.md
pmk resume                # or rm pilot/STOP
```

**Full Kernel Reset (dev only):**
```bash
rm -rf .pm/events .pm/views .pm/tasks .pm/evidence .pm/briefings .pm/registry .pm/memory
pmk init
```

---

## Appendix: Acceptance Tests (Pilot)

| ID | Test | Tier |
|----|------|------|
| T1 | Full task lifecycle (claim → worktree → submit → V0/V1 → merge → DONE) | A/B |
| T2 | Stale-fence submission quarantined | A |
| T3 | Context sync → `CONTEXT_SYNCED` with hashes, revert works | B |
| T4 | Planted injection + paraphrases blocked/reverted | B |
| T5 | V2 with excluded family + only that family → 429, no fallback | B |
| T6 | Out-of-band edit of managed file → sentinel finding (I16) | B |
| Q1 | DST test across 1 Nov 2026 | A |
| Q2 | Account-wide rule (quota_group) | A |
| Q3 | Exhaustion drill (3 models × 5/day, 20 reqs → 15 OK, 16th 429) | B |
| Q4 | Account-wide drill (3 models share 5/day pool) | B |
| Q5 | Kernel-down / gateway-down → tasks stay READY, no reap | B |
| H6 | Fresh Overseer resumes from briefing alone | A |
| C1 | Capacity report per pool vs 10–30 worker target | C |

---

*End of Manual — Pilot P-01, Tier C achieved, Sentinel clean.*