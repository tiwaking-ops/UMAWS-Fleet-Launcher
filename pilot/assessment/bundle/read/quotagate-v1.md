# Project Proposal: QuotaGate, a Quota-Aware Local LLM Gateway

| Field | Value |
|---|---|
| **Author** | Claude Sonnet 5.5 (Anthropic) |
| **Version** | 1.0 |
| **Date** | 2026-10-21 |
| **Status** | Proposed, ready for review, then hand-off to Claude Code |
| **Working name** | `quotagate` (rename freely) |
| **Implementation language** | Python 3.11+ |

---

## 0. How to read this document (instructions for Claude Code)

You are the implementer. Read this whole document before writing code. Then:

1. **Work milestone by milestone** (Section 12). Do not start a milestone until the previous one's acceptance criteria pass.
2. **Commit after every green milestone.** Keep a `DECISIONS.md` log of any choice this document left open.
3. **Never invent provider behaviour.** Where this document says "verify", look at the provider's official documentation, or capture a real response, before coding against it. If you cannot verify, implement the conservative behaviour and record it in `DECISIONS.md`.
4. **Do not hard-code free-tier limits.** They are user-supplied configuration (Section 7.3).
5. **Do not use undocumented or reverse-engineered endpoints without explicit written authorization from the user.** This applies most to Milestones 6 and 7. Stop and ask.
6. **Stop at the marked gates** (M4, M7). They need the user's real credentials or a decision.
7. **Keep the core small.** Target budget: M0–M4 core code under roughly 2,500 lines excluding tests. This is a design target, not a measured benchmark. If you exceed it, simplify before adding features.
8. Run the full test suite before declaring any milestone done. Report test output honestly, including failures.

---

## 1. Executive summary

The user owns a Gemini free-tier API account that sits mostly unused because each model hits rate limits quickly. They want it used to the absolute limit. They also want one local endpoint that their coding tools (OpenCode, Pi and similar) can point at, which transparently spreads requests across many free sources and moves away from any model or provider that is exhausted.

Two existing tools were evaluated in this conversation: LiteLLM and OmniRoute. LiteLLM is a mature gateway, but its documented quota model is per-minute (RPM/TPM) plus dollar budgets. The research found no per-deployment daily request cap or reset-time concept (absence in the docs, not proof). OmniRoute advertises quota-aware strategies, but the user wants their own system that they fully understand and control.

**QuotaGate** is a single-user, localhost-only, OpenAI-compatible proxy whose core is a **quota engine**: it knows each model's per-minute and per-day limits, tracks usage against them, understands when daily limits reset, classifies upstream 429 errors correctly, and routes so that no free quota is wasted ("use it or lose it").

---

## 2. Goals and non-goals

### 2.1 Goals (in the user's priority order)

1. **Squeeze free-tier quotas.** Per-model RPM, TPM and RPD tracking; reset-aware switching; correct classification of rate-limit failures.
2. **Breadth.** Many provider types behind one endpoint, with automatic model discovery.
3. **Small, readable codebase** that Claude Code can finish reliably.
4. **Dashboard** for live usage, health and cooldowns (lowest priority).

### 2.2 Non-goals for v1

- Multi-user features, teams, billing, virtual keys per team, or public deployment.
- Anthropic Messages (`/v1/messages`) or Gemini-native client protocols. Clients speak OpenAI chat completions only.
- Local models (Ollama, LM Studio). The user did not select them. The adapter design must make them trivial to add later, since they are OpenAI-compatible.
- Multi-process or distributed operation (see Section 6.2).
- Spreading load across *multiple Google Cloud projects to multiply quota* as a built-in feature (see Section 11, R4).

---

## 3. Background and findings that shape the design

These come from research during this conversation. Treat them as hypotheses to verify against real traffic.

- **Gemini free-tier limits apply per Google Cloud project, not per API key.** A second key in the same project shares the same buckets. Each model has its own bucket, so rotating across *models* is what increases total throughput.
- **Limit types:** requests per minute (RPM), tokens per minute (TPM), requests per day (RPD). The daily counter resets at midnight Pacific time. In Invercargill, NZ that is about 8pm local now and about 9pm after US clocks change on 1 November 2026. The implementation must use the IANA zone `America/Los_Angeles`, not a fixed UTC offset.
- **Google does not publish a stable per-model free-tier table.** The numbers are visible in the user's AI Studio rate-limit page, and third-party sources disagree. Which models are free also changes. Therefore limits are *data the user pastes in*, and the engine can also learn from observed 429s.
- **Free-tier prompts may be used for model improvement.** The gateway must let the user keep sensitive requests off such deployments (Section 7.6).
- **A 429 can mean different things:** a per-minute limit (retry shortly), a per-day limit (unavailable until reset), or "this model has no free quota at all" (a limit of 0). Treating all 429s the same, as simple cooldown systems do, either wastes calls or locks out models too long.
- **Prior art in the user's own work:** the Tiwas LLM Router (Node.js + Playwright) already solved several browser-automation problems. Lessons are summarised in Section 8.3.

---

## 4. Users, environment and constraints

| Item | Decision |
|---|---|
| Users | One person; private tool |
| Primary OS | Windows 11 (dev laptop); later a more powerful desktop PC. WSL Ubuntu acceptable |
| Network exposure | Bind to `127.0.0.1` by default; never `0.0.0.0` without an explicit flag |
| Concurrency | At least about 12 concurrent client requests (the user runs multi-agent setups) |
| Dependencies | Few. See Section 6.4 |
| State | SQLite file plus a TOML config file |
| Clients | OpenCode, Pi, curl, any OpenAI-compatible tool |

---

## 5. Requirements

### 5.1 Functional

| ID | Requirement |
|---|---|
| F1 | Expose `POST /v1/chat/completions` (streaming SSE and non-streaming) and `GET /v1/models`, OpenAI-compatible. |
| F2 | Accept a local bearer API key from clients. Reject requests without it. |
| F3 | Define **deployments**: a (provider account × upstream model) pair with its own quota rules. |
| F4 | Track usage per deployment against each quota rule, using the rule's window type (rolling minute, fixed daily reset in a named timezone). |
| F5 | Before dispatch, **reserve** quota (1 request plus estimated tokens). After the response, **reconcile** with actual usage. Refund if the request never reached the provider. |
| F6 | Classify upstream failures (Section 7.4) and apply the matching cooldown. Persist cooldowns across restarts. |
| F7 | **Virtual models ("combos")**: names such as `auto`, `auto/free`, `auto/gemini` that expand to an ordered or strategy-driven set of deployments. |
| F8 | Routing strategies: `priority` (fill-first), `headroom`, `use-it-or-lose-it`, `round-robin` (Section 7.5). |
| F9 | Capability filtering: context window, tool calling, vision, streaming. Never route a request to a deployment that cannot serve it. |
| F10 | **Failover:** if a candidate fails before any response bytes are sent, try the next. If streaming has already begun, surface the error (do not silently splice outputs). |
| F11 | Adapters for three provider tiers: API-key (OpenAI-compatible), subscription/OAuth, browser-automated web chat (Section 8). |
| F12 | **Model discovery:** list upstream models, detect free ones, detect dead ones, keep a catalog (Section 9). |
| F13 | **Privacy tag** per deployment (`trains_on_data`). Requests may carry a header, e.g. `x-quotagate-private: 1`, that excludes tagged deployments. |
| F14 | CLI: `serve`, `status`, `add-provider`, `reset-cooldown`, `refresh-models`, `export-opencode`. |
| F15 | Read-only web dashboard: per-deployment usage bars, next reset time, cooldowns, recent requests. |
| F16 | Structured request log (SQLite): chosen deployment, failover chain, latency, tokens, outcome. Never log API keys or full prompts by default. |

### 5.2 Non-functional

- **Correctness over cleverness.** The quota engine is pure logic with an injectable clock, so tests can simulate days in milliseconds.
- **Observability.** `status` must show, per deployment: used/limit per rule, time to next availability, and last error class.
- **Fail loudly and informatively.** If every deployment is exhausted, return HTTP 429 with a JSON body listing the earliest reset time per deployment.
- **Windows-safe.** No POSIX-only code in the core. Use `zoneinfo` with the `tzdata` package.

---

## 6. Architecture

### 6.1 Component overview

```
 clients (OpenCode, Pi, curl)
        |  OpenAI-compatible HTTP, localhost, bearer key
        v
 +--------------------------- QuotaGate (one process, one asyncio loop) ----------------------+
 |  api/        FastAPI app: /v1/chat/completions, /v1/models, /admin/*, dashboard            |
 |  router/     combos -> candidate list -> strategy pick -> failover loop                    |
 |  quota/      rules, ledger (in-memory authority + SQLite write-behind), reserve/reconcile, |
 |              cooldowns, window math, error classifier                                      |
 |  catalog/    models, capabilities, free/dead detection, discovery jobs                     |
 |  adapters/   base.py, openai_compat.py, (native_gemini.py optional), oauth_*.py, browser_* |
 |  store/      SQLite schema + migrations, config loader (TOML)                              |
 |  cli.py                                                                                    |
 +--------------------------------------------------------------------------------------------+
        |
        v   upstream: Gemini (OpenAI-compat endpoint), OpenRouter, Kilo, kenari, Groq,
            OAuth-backed services, browser-driven web chats
```

### 6.2 Key architectural decision: single process, single event loop

All quota state lives in memory in one asyncio event loop, which makes reserve/reconcile **atomic without locks** (no `await` between check and decrement). SQLite is a write-behind journal so state survives restarts. On startup the ledger is rebuilt from the `usage_events` table.

Consequence: run **one worker only** (no multi-worker uvicorn). Document this in the README. This choice removes the need for Redis, which LiteLLM requires for shared usage state.

### 6.3 Suggested layout

```
quotagate/
  pyproject.toml
  README.md   DECISIONS.md
  config.example.toml
  src/quotagate/
    __main__.py  cli.py  config.py  clock.py
    api/        app.py  openai_schema.py  admin.py  dashboard.html
    router/     combos.py  strategies.py  failover.py
    quota/      rules.py  windows.py  ledger.py  cooldowns.py  classify.py  estimate.py
    catalog/    models.py  discovery.py
    adapters/   base.py  openai_compat.py  browser_generic.py  oauth_base.py  ...
    store/      db.py  schema.sql
  tests/
    fake_upstream.py   (a controllable fake provider server)
    test_windows.py  test_ledger.py  test_classify.py  test_strategies.py
    test_failover.py  test_api.py  test_exhaustion_drill.py  ...
```

### 6.4 Dependencies (target short list)

Required: `fastapi`, `uvicorn`, `httpx`, `tzdata`. Standard library for the rest: `sqlite3`, `tomllib`, `asyncio`, `zoneinfo`, `argparse`, `logging`.
Optional extras: `playwright` (browser adapters), `keyring` and `cryptography` (OAuth token storage), `pytest` and `pytest-asyncio` (dev).
Justify any further dependency in `DECISIONS.md`.

---

## 7. The quota engine (the core of the project)

### 7.1 Entities

- **Provider**: a service (e.g. `gemini`, `openrouter`, `groq`, `kilo`, `kenari`).
- **Account**: credentials for a provider, with a `quota_group` string. Accounts sharing a `quota_group` share counters. For Gemini, the group is the Google Cloud project.
- **Model**: an upstream model ID plus capabilities (context window, tools, vision, streaming).
- **Deployment**: Account × Model. This is the unit that is routed to and rate-limited.
- **QuotaRule**: attached to a deployment (or to a quota group and model). Fields: `metric` (`requests` | `input_tokens` | `output_tokens` | `total_tokens`), `limit`, `window` (see 7.2), and for fixed windows `reset_tz` and `reset_time`.
- **Cooldown**: a deployment unavailable until a timestamp, with a reason class (Section 7.4).

### 7.2 Window types

| Window | Behaviour | Used for |
|---|---|---|
| `rolling_60s` | Count of events in the last 60 seconds | RPM, TPM |
| `fixed_daily` | Counter keyed by the calendar date in `reset_tz` (e.g. `America/Los_Angeles`). Resets at `reset_time` (default `00:00`) | RPD |
| `rolling_24h` | Count in the last 24 hours | Providers that document a rolling day |
| `fixed_monthly` | Optional; same idea as daily | Providers with monthly caps |

Implementation notes:
- Compute `window_key = local_date(now, reset_tz)`; the next reset is the next local midnight converted back to UTC. Use `zoneinfo.ZoneInfo`. Test explicitly across the **DST transition on Sunday 1 November 2026** and the spring transition.
- Store event timestamps in UTC. Never store local times.
- `clock.py` provides `now()`; tests inject a fake clock. No other module may call `datetime.now()`.

### 7.3 Limits are configuration, not code

`config.example.toml` ships with **placeholders**, never real numbers:

```toml
[[providers]]
name = "gemini"
kind = "openai_compat"
base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"   # verify against Google docs
api_key_env = "GEMINI_API_KEY"
quota_group = "gemini-project-1"          # all keys in the same GCP project share this
trains_on_data = true                     # free tier; see F13

  [[providers.models]]
  id = "<model id from AI Studio>"
  priority = 1
  tools = true
  context_window = 0                      # fill in
    [[providers.models.limits]]
    metric = "requests";      window = "rolling_60s"; limit = 0   # <-- paste from AI Studio
    [[providers.models.limits]]
    metric = "total_tokens";  window = "rolling_60s"; limit = 0
    [[providers.models.limits]]
    metric = "requests";      window = "fixed_daily"; limit = 0
    reset_tz = "America/Los_Angeles"
```

Rules:
- A limit of `0` or absent means **unknown**, not zero: the engine relies on reactive 429 handling for that rule and logs a warning at startup.
- The user's AI Studio rate-limit page is the source of truth. Provide `quotagate limits-template` that prints a config skeleton for the user to fill in.
- **Auto-calibration (optional, M4):** when a per-day 429 arrives and the local counter says usage was below the configured limit, log the discrepancy and suggest an adjusted limit. Do not silently rewrite config.

### 7.4 Failure classification

The classifier turns an upstream response or exception into one of these classes. Each has a cooldown rule.

| Class | Typical signal | Cooldown |
|---|---|---|
| `rate_minute` | 429 whose body/headers indicate a per-minute metric; `Retry-After` present | `Retry-After` if given, else until the rolling window frees; cap at about 90 s |
| `rate_day` | 429 indicating a per-day metric | Until the next reset of that rule |
| `no_quota` | 429 or 4xx indicating limit 0 / model not available on this tier | Disable the deployment until manually re-enabled or catalog refresh says otherwise |
| `transient` | 5xx, connection reset, timeout | Exponential backoff 5 s, 15 s, 45 s, up to 5 min; reset on success |
| `auth` | 401/403 | Disable account; surface prominently in `status` |
| `model_gone` | 404 for a model; "deprecated/end of life" text | Mark model dead in catalog; remove from combos |
| `client_error` | 400 caused by the request itself (context too long, bad params) | **No cooldown.** Return the error, or retry only on a deployment with a larger context if the error is a context overflow |
| `unknown_429` | 429 that cannot be classified | Conservative: treat as `rate_minute` with a 60 s cooldown, log the raw body for the user |

**Verify against real traffic:** Google-style 429s are expected to carry structured error details naming the exceeded quota (for example, quota identifiers that include words like "PerMinute" or "PerDay") and possibly a `RetryInfo` delay. The exact shape on the OpenAI-compatibility endpoint versus the native endpoint is **not verified**. Milestone 4 requires capturing real 429 bodies from both endpoints (with the user's key), saving sanitised fixtures under `tests/fixtures/`, and tuning the classifier against them. If the OpenAI-compatible endpoint hides the quota metadata, implement the optional `native_gemini.py` adapter to get it.

For OpenAI-style providers (Groq, OpenRouter and similar), also read `x-ratelimit-*` and `Retry-After` response headers when present and use them to sync the ledger's counters.

### 7.5 Routing strategies

Given the candidate deployments for a request (after capability and privacy filters, minus anything cooling down or with an exhausted rule), the strategy picks the order to try:

- **`priority`**: user-defined `priority` number, lowest first ("fill-first").
- **`headroom`**: highest minimum remaining fraction across the deployment's rules.
- **`use-it-or-lose-it`** (default for free combos): rank by *time until the most constraining daily window resets*, soonest first, among deployments that still have headroom. This spends quota that is about to expire before quota that renews later. Break ties by `priority`. Also keep per-minute headroom above a small safety margin (default 1 request) to avoid self-inflicted 429s.
- **`round-robin`**: rotate to spread load evenly (useful for latency testing).

All strategies must be deterministic given the same ledger state and clock, so tests can assert exact orderings.

### 7.6 Reservation, estimation and reconciliation

1. Estimate input tokens cheaply (for example `ceil(len(text)/4)` plus a margin). This is a heuristic. Do not add a tokenizer dependency in v1.
2. Reserve `1` request and the estimated tokens against every rule on the chosen deployment. If any rule would exceed its limit, skip this deployment.
3. After the response, replace the estimate with the provider's reported `usage` if present. For streaming, request usage in the final chunk where the provider supports it (verify per provider).
4. If the request failed before reaching the provider (connection refused), refund the reservation. If it reached the provider and was rejected with 429, **do not refund**: the provider may count it.
5. Concurrency: a per-deployment `max_concurrency` semaphore (default 4; browser adapters 1).

### 7.7 Privacy-aware routing

Deployments carry `trains_on_data`. If the client sends `x-quotagate-private: 1`, or the combo is configured `private = true`, those deployments are excluded. The dashboard and `status` show the tag.

---

## 8. Provider adapters

All adapters implement the interface in `adapters/base.py`:

```python
class Adapter(Protocol):
    capabilities: Capabilities            # tools, vision, streaming, max_concurrency
    async def chat(self, req: ChatRequest) -> AsyncIterator[Chunk] | ChatResponse: ...
    async def list_models(self) -> list[ModelInfo]: ...
    def classify_error(self, status: int, headers: Mapping, body: bytes | Exception) -> FailureClass: ...
```

### 8.1 Tier A: API-key providers (build first)

One generic `openai_compat` adapter covers OpenRouter, Kilo Gateway, kenari, Groq and Gemini's OpenAI-compatibility endpoint. Per-provider differences (extra headers, model-list shapes, free-model markers) are handled by small config fields, not new classes. Verify each provider's base URL and model-list format from its official docs.

Known free-model markers to support in discovery (verify before relying): OpenRouter's `:free` suffix; Kilo Gateway's free auto model (the user's own notes say the correct ID is `kilo-auto/free`, and that a typo caused HTTP 402); kenari's `:free` models.

### 8.2 Tier B: Subscription / OAuth logins (framework plus one reference)

- Provide `oauth_base.py`: token storage, refresh, expiry handling, and an auth-strategy interface supporting static key, device-code flow and browser-redirect flow. Store tokens via `keyring` where available, else an encrypted file.
- **Risk:** using a subscription's OAuth token outside the vendor's official client may violate that vendor's terms or be technically blocked. This is the user's decision, not the implementer's. Therefore:
  - Build the framework first.
  - **Gate (M7):** ask the user *which* subscription to implement first. Use only officially documented OAuth flows. If a flow requires extracting credentials from another program or an undocumented endpoint, **stop and ask** for authorization.
- Subscription services often have usage windows (for example, a limit that resets every few hours) rather than daily-calendar resets. The `rolling_*` and a new `fixed_interval` window type must be able to express this. Add `fixed_interval` (reset every N hours from an anchor time) if a chosen provider needs it.

### 8.3 Tier C: Browser-automated free web chats

For free web tiers that have no API. Use Python Playwright with a persistent browser profile per provider so logins survive.

Port these lessons from the user's Node-based Tiwas router (they cost real debugging time):

- **Generic, selector-driven adapter** configured from data (URL, composer selector, send-button selector, logged-in indicator, container selector), so the user can add providers without new code.
- **Diff-based completion detection:** snapshot the conversation text before sending, then diff after, instead of trusting a single response-container selector (claude.ai's real DOM did not match the guessed selector).
- **Completion markers:** many UIs print "<Provider> said/responded" before the real answer. Require the marker before accepting text-stability as "done", with a soft fallback after half the timeout so providers without markers do not hang.
- **Baseline message count** before sending, so the adapter never returns a stale previous reply in a continuing thread.
- **Reversed DOM order:** pick the *visually lowest* matching message by bounding-box y, not `.last()`.
- **Overlay dismissal:** promo overlays can intercept the send click. Force-hide known containers, re-check just before sending, force-click as a last resort.
- **Stagger browser launches** (about 1 s apart) and use long navigation timeouts (60 s) when several start at once.
- **Project URL override:** let a provider be pointed at a specific project/chat URL.
- **Distinguish config errors from transient errors:** a missing composer on a project overview page should produce a short `config_error` cooldown, not the full failure cooldown.
- Provide an **import command** that reads the Tiwas router's `custom-providers.json` and `project-urls.json` and converts them to QuotaGate config (verify the file formats from the user's actual files before coding).

Capability limits (set honestly in `capabilities`): no tool calling, no real token streaming (emit the full text as SSE chunks after completion), `max_concurrency = 1` per provider, high latency. The router must never send a tool-calling request to such a deployment. Quota rules still apply (the user can set message limits per window).

**Risk (state in README):** automating free web tiers is generally against those services' terms. The user accepted this in the Tiwas project; keep the browser tier opt-in per provider, off by default.

---

## 9. Model catalog and discovery (priority 2)

- `refresh-models` calls each adapter's `list_models()` and upserts into a `models` table with `first_seen`, `last_seen`, `free` (true/false/unknown), `alive`, capability fields (where the provider exposes them).
- **Free detection:** provider-specific rule: zero pricing fields in the model listing, a `:free` suffix, or a configured allow-list. When unsure, `free = unknown` and the model is **excluded from `auto/free`** until the user confirms. Never route to an unknown-cost model from a free combo.
- **Dead-model handling:** a `model_gone` failure, or a model disappearing from its provider's listing for N consecutive refreshes (default 2), marks it dead and removes it from combos. This addresses the user's recurring problem of end-of-life models lingering in their tools.
- **Auto-combos:** generate `auto/free` and `auto/<provider>` from the catalog. User-defined combos in config override generated ones.
- **`export-opencode`:** emit a ready-to-paste `opencode.jsonc` provider block listing the gateway's models, so OpenCode can use the gateway as one OpenAI-compatible provider. (Verify the current OpenCode config schema before implementing.)
- Context windows and capabilities that a provider does not report are `unknown`; require the user to fill them in rather than guessing.

---

## 10. Data model (SQLite)

Keep it to a handful of tables. Suggested columns, adjust as needed:

| Table | Purpose and key columns |
|---|---|
| `providers` | name, kind, base_url, trains_on_data, enabled |
| `accounts` | provider, label, quota_group, auth_kind, enabled |
| `models` | provider, model_id, free, alive, tools, vision, context_window, first_seen, last_seen |
| `deployments` | account, model, priority, max_concurrency, enabled |
| `quota_rules` | deployment (or quota_group+model), metric, window, limit, reset_tz, reset_time, source (`config`/`observed`) |
| `usage_events` | ts_utc, deployment, requests, input_tokens, output_tokens, estimated (bool) |
| `cooldowns` | deployment, class, until_utc, detail |
| `requests_log` | ts_utc, client_model, chosen_deployment, failover_chain (JSON), outcome, latency_ms, tokens |

Prune `usage_events` older than about 48 hours (keep `requests_log` longer, configurable). Config (TOML) is the source of truth for providers, deployments and limits. SQLite holds runtime state.

---

## 11. Risks and mitigations

| # | Risk | Mitigation |
|---|---|---|
| R1 | Gemini free-tier limits and model availability change, and sources disagree | Limits are config; `limits-template`; reactive 429 handling; auto-calibration warnings |
| R2 | 429 body shape differs between Gemini endpoints or providers, so misclassification | Capture real bodies in M4 as fixtures; `unknown_429` conservative path logs raw bodies; optional native Gemini adapter |
| R3 | Token estimation is inexact, so TPM overshoot or undershoot | Reserve with margin; reconcile with reported usage; rely on reactive 429 as the backstop |
| R4 | Multiple Google projects used to multiply quota may breach Google's terms (not checked) | Not built as a feature. `quota_group` models sharing correctly. The user should read Google's terms before adding accounts from different projects |
| R5 | OAuth reuse and browser automation may breach provider terms or be blocked | Opt-in per provider; documented-flow-only rule; gate M7; user decision |
| R6 | Streaming failure mid-response | Failover only before the first byte; otherwise surface the error; never splice |
| R7 | Free-tier data used for training | `trains_on_data` tag and private-request routing |
| R8 | Windows quirks (asyncio event loop policy, Playwright, Unicode paths) | Test on Windows first; avoid POSIX-only code; document required setup |
| R9 | Single-process design caps throughput | Acceptable for one user. Document the limit. No premature scaling |
| R10 | Supply-chain risk in a tool holding many API keys | Pin exact dependency versions with a lockfile; keep the dependency list short; never log secrets. (LiteLLM itself had a PyPI compromise in March 2026, which is why this matters for a key-holding gateway.) |
| R11 | Scope creep from "breadth" | Milestone order and the line budget in Section 0 |

---

## 12. Milestones and acceptance criteria

Sizes are relative (S/M/L), not calendar estimates.

### M0: Foundations (S)
Project skeleton, `pyproject.toml`, pinned dependencies, `clock.py` with fake clock, config loader (TOML), SQLite schema, pytest setup, `tests/fake_upstream.py` skeleton.
**Accept:** `pytest` runs green on Windows; config example loads; fake clock advances deterministically.

### M1: Passthrough proxy (M)
FastAPI app with `/v1/chat/completions` (stream and non-stream) and `/v1/models`; local bearer auth; `openai_compat` adapter for one configured provider; request log.
**Accept:** a real OpenAI-compatible client (curl and the `openai` Python package, test-only) works against the fake upstream and against one real provider key; SSE streaming verified.

### M2: Quota engine (L), the most important milestone
`rules`, `windows` (rolling_60s, fixed_daily with timezone), `ledger` (reserve/reconcile/refund, write-behind persistence, rebuild on startup), `cooldowns`, `classify`.
**Accept (all as automated tests with the fake clock):**
- A fixed_daily rule in `America/Los_Angeles` resets at local midnight, including across the 1 Nov 2026 DST change.
- Reserve is atomic: 50 concurrent reserves against limit 10 yield exactly 10 successes.
- A restart mid-day rebuilds the same counters from `usage_events`.
- Classifier fixtures: each class in Section 7.4 is produced by a representative response.
- `rate_day` cooldown ends exactly at the next reset; `rate_minute` ends at `Retry-After`.

### M3: Routing and failover (M)
Combos, the four strategies, capability and privacy filters, failover loop, the "all exhausted" 429 response with per-deployment reset times, and the `status` CLI.
**Accept:**
- **Exhaustion drill:** three fake models each with a daily limit of 5. Send 20 requests. Exactly 15 succeed, spread so that no model is called after its daily cap, the 16th returns the structured 429 with earliest reset, and advancing the fake clock past reset restores service.
- Failover on a simulated 5xx tries the next deployment without client-visible error.
- Mid-stream failure does not fail over.
- `use-it-or-lose-it` ordering matches hand-computed expectations in unit tests.

### M4: Gemini live verification and calibration (M), **GATE: needs the user's real key**
Point a Gemini deployment at the real API. Capture sanitised real 429 bodies (per-minute, per-day if reachable) from the OpenAI-compatible endpoint, and from the native endpoint if metadata is missing. Tune the classifier. Implement `limits-template`. Add optional auto-calibration warnings.
**Accept:** a short report in `DECISIONS.md` stating what the real 429s look like and what was verified versus assumed. The user's actual AI Studio limits are in their local config. A real multi-model Gemini run shows the gateway moving between models as limits hit, with no unclassified 429s.

### M5: Catalog, discovery and more API-key providers (M)
`list_models`, free/dead detection, auto-combos, `refresh-models`, `export-opencode`; config entries for OpenRouter, Kilo Gateway, kenari, Groq.
**Accept:** `refresh-models` populates the catalog from at least two real providers; a model removed upstream is marked dead after the configured number of refreshes; `auto/free` never includes `free = unknown` models.

### M6: Browser-automation adapter (L), opt-in
Generic Playwright adapter applying the Section 8.3 lessons; import from the Tiwas router config.
**Accept:** tested against a local fake chat page (controllable DOM, delayed responses, overlay, reversed message order, "<name> said" markers) *and* manually against one real provider chosen by the user. Browser deployments never receive tool-calling requests.

### M7: OAuth / subscription framework plus one reference provider (L), **GATE: needs user decision**
Token storage and refresh, auth-strategy interface. Ask the user which subscription to implement. Official, documented flows only.
**Accept:** the chosen provider works end-to-end through the gateway, tokens are stored outside plaintext config, and `status` shows its usage window.

### M8: Dashboard (S–M)
Single static HTML page polling `/admin/state`: usage bars, next reset, cooldowns, recent requests, privacy tags. Read-only. No JS framework.
**Accept:** loads on `http://127.0.0.1:<port>/`; updates within a few seconds of traffic.

### M9: Hardening and hand-off (S)
README (setup on Windows and WSL, config walkthrough, single-worker note, risks), log redaction audit, lockfile, a "known limitations" section, `DECISIONS.md` finalised.
**Accept:** a fresh clone can be set up from the README alone; grep confirms no secrets in logs or fixtures.

---

## 13. Testing strategy

- **Pure-logic tests first** (windows, ledger, classifier, strategies) with the fake clock: fast and deterministic.
- **`fake_upstream.py`:** a controllable FastAPI server emulating OpenAI-style endpoints, scripted 429s (minute, day, no-quota), 5xx, slow streams, mid-stream disconnects, and Google-style error bodies from M4 fixtures.
- **Contract tests** using the official `openai` Python client as a test-only dependency.
- **Concurrency test:** 12 simultaneous clients against the fake upstream with limits; assert no deployment exceeds its limit.
- **Browser adapter tests** against a local HTML page you control.
- Mark tests that need real keys (`@pytest.mark.live`) and skip them by default.

---

## 14. Success criteria (what "great" looks like)

1. **Quota squeeze works and is provable:** the exhaustion drill passes, and in a real Gemini run (M4) the gateway keeps serving by moving across models as each limit is hit, with daily-exhausted models left alone until their reset.
2. **Honest and observable:** `status` explains for every deployment why it is or is not available; every unverified assumption is recorded in `DECISIONS.md`.
3. **Small and maintainable:** core under the line budget, a short dependency list, and each module readable in one sitting.

---

## 15. Assumptions and open questions (flagged guesses)

| # | Assumption or question | Why it matters |
|---|---|---|
| A1 | Gemini's OpenAI-compatibility endpoint is adequate for v1; a native adapter is only needed if quota metadata is missing | Decides whether `native_gemini.py` is built (M4) |
| A2 | Per-minute and per-day limits are the only Gemini free-tier dimensions that matter; token-per-day limits are possible, so the rule model supports them | Rule model flexibility |
| A3 | Default routing strategy `use-it-or-lose-it` matches the user's intent ("use to the absolute limit") | Could be changed to `priority` per combo |
| A4 | **Which subscription/OAuth service first?** Unknown | Gate M7 |
| A5 | **Which browser providers first?** Assume the user's existing Tiwas set (Claude, ChatGPT, Grok, Gemini web) | M6 reference target |
| A6 | Interface choice: web dashboard plus CLI; no TUI/GUI | User allowed any |
| A7 | Python 3.11+ is available on the target machines | `tomllib`, `zoneinfo` |
| A8 | The 2,500-line budget is a design target, not a measurement | Section 0 |
| A9 | Exact OpenCode config schema, Kilo, kenari and OpenRouter listing formats | Verify in M5 |
| A10 | Name `quotagate` is a placeholder | Cosmetic |

---

## Appendix A: example client and error responses

```bash
curl http://127.0.0.1:8787/v1/chat/completions \
  -H "Authorization: Bearer $QUOTAGATE_KEY" -H "Content-Type: application/json" \
  -d '{"model":"auto/free","messages":[{"role":"user","content":"hello"}],"stream":true}'
```

All deployments exhausted (HTTP 429):

```json
{
  "error": {
    "type": "all_deployments_exhausted",
    "message": "No deployment can serve this request right now.",
    "earliest_available": "2026-10-22T07:00:00Z",
    "deployments": [
      {"id": "gemini/<model-a>", "class": "rate_day", "available_at": "2026-10-22T07:00:00Z"},
      {"id": "groq/<model-b>",   "class": "rate_minute", "available_at": "2026-10-21T08:41:30Z"}
    ]
  }
}
```

(Timestamps illustrative.)

## Appendix B: glossary

- **Deployment:** an account × model pair; the unit that is routed to and rate-limited.
- **Quota group:** accounts that share upstream counters (for Gemini, one Google Cloud project).
- **Combo / virtual model:** a client-visible model name that expands to a set of deployments plus a strategy.
- **Reservation:** provisional quota deduction before a call, reconciled after it.
- **Reset-aware:** aware of when a fixed window (e.g. midnight Pacific) will renew.
