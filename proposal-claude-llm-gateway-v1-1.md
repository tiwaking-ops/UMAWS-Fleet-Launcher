---
document:
  title: "QuotaGate: a quota-aware local LLM gateway, integrated with the Ultimate Multi-Agent Workflow System"
  status: "Proposal v1.1 (supersedes v1.0). Not built. Nothing here has been run."
  version: "1.1"
author: "Claude Sonnet 5.5 (claude-sonnet-5-5), Anthropic"
date: "2026-10-22"
audience: "Primary: Claude Code (implementer). Secondary: the user (single operator, Windows laptop with WSL Ubuntu)."
supersedes: "proposal-claude-llm-gateway-v1.md (v1.0)"
companion_documents:
  - "Ultimate-Multi-Agent-Workflow-System.md (v1.0.0), referred to below as UMAWS"
evidence_basis: "Handoff notes from the previous session (research on Gemini, LiteLLM, OmniRoute, OpenRouter), a full read of UMAWS in this session, and the user's answers of 2026-10-22. No code run, no live provider call made."
---

# QuotaGate v1.1

## 1. Summary

QuotaGate is a single-user, localhost-only Python gateway that exposes an OpenAI-compatible `/v1/chat/completions` endpoint and spreads requests across free LLM sources, tracking per-minute and per-day quotas so that no free quota is wasted and exhausted deployments are avoided automatically.

v1.1 changes v1.0 in four ways:

1. **Scope is smaller.** The browser-automation tier and the OAuth/subscription tier are out of v1 (decisions below).
2. **The quota model is hierarchical.** Rules can apply to a deployment, an account, a quota group, or a whole provider, and a request must satisfy all of them. v1.0 could not model OpenRouter-style account-wide limits.
3. **Integration with UMAWS is designed, not an afterthought.** The gateway is the mechanism (where can a call go now); the UMAWS Kernel router is the policy (which kind of model a task deserves).
4. **Capacity is measured before it is promised.** With about 12 permanent free models, real throughput is set by independent quota pools, so a measurement milestone precedes routing sophistication.

## 2. Decisions confirmed by the user

| # | Decision | Effect on this proposal |
|---|---|---|
| D1 | Language: Python. Interface: TUI, GUI or web all acceptable | Web dashboard plus CLI (assumption A1) |
| D2 | Client protocol v1: OpenAI-compatible `/v1/chat/completions` only | No Anthropic Messages endpoint |
| D3 | Claude Code as a worker is not needed | Out of scope |
| D4 | **Drop browser-automation from v1**; Tiwas router stays for manual use | v1.0 Milestone 6 removed |
| D5 | **OAuth/subscription tier deferred to v2** | v1.0 Milestone 7 removed; only an extension point remains |
| D6 | **Gateway limits and combos are pinned policy** (UMAWS invariant I8) | Section 8 |
| D7 | **About 12 permanent free-tier models** (not 300) | Capacity model, Section 9 |
| D8 | **WSL Ubuntu now, Linux later** | Section 10 |
| D9 | Priorities: 1) squeeze free quotas, 2) breadth and discovery, 3) small readable codebase, 4) dashboard | Milestone order |

Interpretation note (A2): I take D7 to mean roughly 12 models have free access that does not expire, and the rest of the "about 300" are temporary, promotional or trial access. If that is wrong, Section 9 still applies, because capacity depends on quota pools, not model count.

## 3. Core concepts (carried from v1.0, with changes marked)

**Entities.** Provider; Account (carries `quota_group`, for example a Google Cloud project, so accounts sharing upstream counters share ours); Model; **Deployment** (account × model, the routed unit); QuotaRule; Cooldown.

**QuotaRule.** `metric` (requests or tokens), `window`, `limit`, reset timezone and time, and, **new in v1.1**, `scope`:

| Scope | Meaning | Example |
|---|---|---|
| `deployment` | This account × model | Per-model RPM/RPD on Gemini (per Google project, per model) |
| `account` | All models on one account | OpenRouter `:free` limits, which OpenRouter documents as account-wide |
| `quota_group` | All accounts sharing an upstream counter | Two Gemini keys in one Google project |
| `provider` | Everything on a provider | A provider-wide abuse ceiling |

**Evaluation.** A request is admissible only if **every** applicable rule at every scope has headroom. Reservation takes one unit at each applicable scope atomically (single asyncio loop, no locks); reconciliation and refund apply to all scopes. The earliest-available time for a deployment is the **latest** of its blocking rules' reset times.

**Window types.** `rolling_60s`, `fixed_daily` (calendar date in a named timezone via `zoneinfo` plus `tzdata`), `rolling_24h`; optional `fixed_monthly`, `fixed_interval`. All time goes through an injectable clock. Test across the US daylight-saving change on 1 November 2026.

**Limits are configuration, not code.** Ship placeholders only. A limit of 0 or absent means *unknown*, not zero. Free-model status is `unknown` until proven, and unknown-cost models are excluded from free combos.

**Failure classes** (unchanged from v1.0): `rate_minute` (honour `Retry-After`, cap about 90 s), `rate_day` (until next reset of the blocking rule), `no_quota` (disable), `transient` (backoff 5 s, 15 s, 45 s, up to 5 min), `auth` (disable account), `model_gone` (mark dead), `client_error` (no cooldown), `unknown_429` (60 s cooldown, log raw body). **Change:** the classifier is designed against captured real responses (Milestone M1), not guesses.

**Strategies:** `priority`, `headroom`, `use-it-or-lose-it` (default for free combos), `round-robin`. Deterministic given ledger state and clock.

**Failover** happens only before the first response byte. Mid-stream failures surface as errors, never spliced.

**All exhausted:** HTTP 429 with a structured body (Section 7.4).

**Privacy:** each deployment carries `data_class` (see 7.5), replacing v1.0's boolean `trains_on_data`.

**Token estimation** is characters ÷ 4 with a configurable safety margin; reconciled with reported usage afterwards. Crude by design in v1.

## 4. What the full read of UMAWS added

The previous session read UMAWS partially. These items are from the full read and are new relative to the handoff:

| UMAWS reference | Gateway consequence |
|---|---|
| §13.3 liveness signal **S4** (token/stream activity), kernel-observed | Gateway emits stream-activity events per lease |
| §28.2 **capability tokens**: Kernel-issued, per-lease, scoped, expiring | Gateway authenticates with these, not a static key |
| I7 Kernel timestamps are the only trusted time | Gateway keeps its own clock for quota resets but labels its event timestamps non-authoritative; Kernel re-stamps on ingest |
| §17.4 canaries, §17.3 verifier selection | Routes that bypass `auto` and exclude model families |
| §29.2 failure fingerprints; "each retry changes one variable" | Every response reports resolved model and failure class |
| §19.2 envelopes (spend, in dollars) | Free quota is an envelope in requests and tokens; expose remaining quota in envelope terms |
| §31.2 `registry/models.yaml` | Catalog can generate fact fields; measured fields stay Kernel-computed |

## 5. Architecture

```
 UMAWS Harness / workers (sandbox: no network except gateway)
        │  OpenAI-compatible requests + x-quotagate-* headers + capability token
        ▼
 ┌─────────────────────────── QuotaGate (one process, one asyncio loop) ───────────┐
 │ auth (token verify) → route (combo/strategy) → quota engine (hierarchical)      │
 │ → upstream adapter (one config-driven OpenAI-compatible adapter)                │
 │ SQLite: ledger, cooldowns, usage log, event outbox   │ config (pinned)          │
 └───────────────┬────────────────────────────────────────────────┬────────────────┘
                 ▼                                                ▼
         free providers (API keys)                      events pulled by Kernel
```

Dependencies kept minimal and pinned by exact version with a lockfile: `fastapi`, `uvicorn`, `httpx`, `tzdata`. Rationale: LiteLLM was compromised on PyPI in March 2026 (per the previous session's sources), and any gateway holds many API keys.

Code budget: about 2,500 lines for the core, a design target, not a measurement. Dropping the browser tier removes the largest source of complexity.

## 6. Routing responsibilities

| Decision | Owner |
|---|---|
| Which class of model a task deserves (from measured oracle pass rates) | UMAWS Kernel router (policy) |
| Which verifier family is independent of the author | UMAWS Kernel |
| Which concrete deployment can take the call right now | QuotaGate (mechanism) |
| Per-deployment outcome statistics | QuotaGate **exposes** facts; Kernel computes measurements |

Rule: `auto` aliases are for ad-hoc and manual use. Harness calls name an explicit **combo** (an ordered or weighted list of deployments chosen by the Kernel's policy). Verifier and canary calls must use explicit combos.

## 7. Integration contract with UMAWS

### 7.1 Request headers (set by the Harness)

| Header | Purpose |
|---|---|
| `Authorization: Bearer <capability token>` | Kernel-issued, per-lease, expiring; carries lease id, task id, allowed combos, allowed data classes, token cap |
| `x-quotagate-combo` | Named combo to use (required for Harness calls) |
| `x-quotagate-exclude-family` | Model families to exclude (verifier independence) |
| `x-quotagate-lease`, `x-quotagate-task`, `x-quotagate-role` | Attribution (also readable from the token; headers are convenience, the token is authoritative) |
| `x-quotagate-private` | Retained from v1.0 as shorthand for "exclude deployments not allowed for the strictest data class" |

### 7.2 Response contract (resolved model)

Every response, including errors, carries headers and a JSON field `quotagate`:

```json
{
  "quotagate": {
    "resolved": {"provider": "...", "model": "...", "account": "label", "deployment": "id"},
    "attempts": [{"deployment": "id", "outcome": "rate_minute", "ms": 412}],
    "failure_class": null,
    "usage": {"prompt": 0, "completion": 0, "estimated": false},
    "request_id": "..."
  }
}
```

Silent failover without this would corrupt the Kernel's per-model statistics (UMAWS A1/A7 warn about silent model replacement).

### 7.3 Events (gateway emits, Kernel ingests)

The gateway never writes coordination state (invariant I2). It keeps an **event outbox** in its own SQLite and exposes `GET /v1/quotagate/events?since=<seq>`; the Kernel pulls and records. Events:

`DEPLOYMENT_EXHAUSTED`, `COOLDOWN_STARTED`, `COOLDOWN_ENDED`, `DEPLOYMENT_DISABLED` (auth/no_quota/model_gone), `NO_ELIGIBLE_DEPLOYMENT` (supports I14, silence is an event), `STREAM_ACTIVITY` (per lease, coalesced, supports S4), `LEASE_TOKEN_CAP_REACHED`, `CONFIG_HASH_MISMATCH`.

Timestamps are marked `non_authoritative`; the Kernel re-stamps on ingest (I7).

### 7.4 Availability and the all-exhausted response

`GET /v1/quotagate/availability?combo=<name>` returns, per deployment: state, remaining units per scope (requests and tokens), and `earliest_available_utc`. The all-exhausted case returns HTTP 429 with the same structure plus `earliest_available_utc` for the combo, so the Kernel scheduler can requeue with a not-before time instead of failing the task (UMAWS §12.2 item 6, §29.2).

### 7.5 Data classes

Replace the boolean with a `data_class` ceiling per deployment, using the same vocabulary as UMAWS `data_classes_allowed` (for example `public`, `internal`). The token lists allowed classes; a deployment whose ceiling is below the task's class is never eligible. **Assumption A3:** the class vocabulary is whatever UMAWS policy defines; the gateway treats class names as opaque strings with a configured ordering.

### 7.6 Lease budgets

The capability token carries a token cap. The gateway counts usage against it and refuses further calls with a structured error once reached, emitting `LEASE_TOKEN_CAP_REACHED`. This enforces UMAWS §10.1 budgets at the egress point.

### 7.7 Capability facts

The gateway catalog holds facts only (context window, tool support, free or not, family). A script may generate the fact fields of `registry/models.yaml`; measured fields (`oracle_pass`, `escape_rate`) are computed by the Kernel and never written by the gateway.

### 7.8 Failure modes

| Failure | Behaviour |
|---|---|
| Gateway down | Harness gets connection refused; tasks stay READY; Kernel records silence (I14). Workers have no other egress |
| Kernel down | Gateway keeps serving; events accumulate in the outbox; Kernel pulls from its last seq on restart |
| Token invalid or expired | 401, event logged; no upstream call |
| Gateway clock wrong | Quota resets mis-timed; mitigation: startup check against system time and a configured tolerance; Kernel times remain authoritative for the log |
| SQLite corrupt | Ledger rebuilt from the usage log if intact; otherwise start with a conservative cool-off window and emit an event. Unknown ledger state must not be treated as full quota |
| Config edited outside change control | Hash mismatch; refuse to start or reload; emit `CONFIG_HASH_MISMATCH` |

## 8. Pinning and change control (D6)

- Pinned artifacts: provider/deployment definitions, quota rules, combos, data-class ceilings, strategy settings. Secrets are **not** part of the pinned file; they live in a separate untracked secrets file or environment.
- The gateway computes a SHA-256 of the canonical pinned config at startup and exposes it at `GET /v1/quotagate/config-hash`.
- UMAWS I8 requires a two-key event to change pinned policy. The gateway verifies the hash against a value the Kernel publishes; **how** that value is delivered is an open point (A4): default is a small signed file the Kernel writes, which the gateway reads at startup and on reload.
- Plain-language meaning: the limits and combos are treated like code. Nobody, including the overseer LLM, can quietly change them mid-run.
- Tension to be aware of: provider limits change without notice. Pinning makes every correction a deliberate, logged change. That is intended, but it slows reaction to a provider tightening limits. The gateway's **learned cooldowns** (from real 429s) are runtime state, not pinned config, so a tightened limit is still respected immediately.

## 9. Capacity model (D7)

**Premise.** Capacity equals the number of independent quota pools times their limits, not the number of models. OpenRouter documents its `:free` limits as account-wide (20 requests per minute; 50 per day under 10 credits purchased, 1000 per day at 10 or more; see https://openrouter.ai/docs/limits). The previous session did not verify how Gemini's OpenAI-compatible endpoint exposes quota details, nor how Kilo, kenari or Groq pool limits.

**Approach.**
1. Enumerate the ~12 permanent free models and, for each, the pool it belongs to (assumed from documentation, then measured).
2. Build a **capacity report** (Milestone M4): a load-test script that drives each pool to its limits under a fake or real clock and records requests per minute and per day actually achieved.
3. Compare with the UMAWS design target of 10 to 30 concurrent workers (UMAWS §29.1). If the achievable throughput is below demand, the honest outcome is that UMAWS runs with fewer workers or slower cadence, not that the gateway should pretend otherwise. The Kernel scheduler already queues rather than fails when a provider is rate-limited (UMAWS §29.2).

**Guess flagged (A5):** with about 12 models in a few pools, free capacity probably supports a handful of workers at low duty, not 30. This is unmeasured.

## 10. Environment (D8)

- Kernel (per UMAWS §31.1: Unix socket and `flock`) runs in WSL Ubuntu. Native Windows Python lacks `fcntl`, so the Kernel does not run there unless it gets portable locking.
- Gateway: runs in WSL too in v1 (assumption A6), so the Harness reaches it on WSL's localhost. If workers run in Windows processes, WSL-to-Windows localhost forwarding must be tested; this is unverified.
- Docker sandboxing of workers with "gateway only" egress needs a verified network route to the gateway; test in M5.
- Linux migration should require no code change; paths and locking use portable calls where possible.

## 11. Milestones

Mapping to v1.0 is given in brackets. Quota engine first; each milestone has an exit test.

| M | Deliverable | Exit test |
|---|---|---|
| **M0** Foundations [v1.0 M0] | Repo, config loader, SQLite schema, injectable clock, logging, lockfile with pinned deps | Unit tests run on WSL; clock fake works |
| **M1** Passthrough + **live capture** [v1.0 M1, with M4's capture pulled forward] | OpenAI-compatible proxy with streaming; a capture tool that stores raw upstream error bodies and headers (secrets redacted) from the user's real keys | Real 429s and quota headers from Gemini (and others) saved as fixtures; classifier designed from them |
| **M2** Quota engine, hierarchical [v1.0 M2] | Scoped rules, windows, atomic multi-scope reservation, reconcile, refund rule, cooldowns | Property tests; DST test across 1 Nov 2026; account-wide rule test |
| **M3** Routing, failover, `status` CLI [v1.0 M3] | Strategies, combos, pre-first-byte failover, structured 429, concurrency semaphores | **Exhaustion drill**: three fake models, daily limit 5, 20 requests: exactly 15 succeed, the 16th returns the structured 429, advancing the clock restores service. **Account-wide drill**: three models sharing an account limit of 5/day behave as one pool of 5 |
| **M4** **Capacity measurement** (new) | Load-test script and capacity report per pool | Report saved; compared to 10–30 worker target |
| **M5** **UMAWS integration** (new) | Capability-token auth, headers, resolved-model contract, events outbox and pull endpoint, availability endpoint, lease token caps, config hash check | Contract tests with a stub Kernel; resolved model present on every response; verifier-exclusion test; Kernel-down and gateway-down tests |
| **M6** Catalog and discovery [v1.0 M5] | Auto-discovery of models for API-key providers; `unknown` free status until proven | New model appears in catalog without code change |
| **M7** Dashboard [v1.0 M8] | Web page: pools, remaining quota, cooldowns, recent calls | Matches `status` CLI output |
| **M8** Hardening [v1.0 M9] | Secret redaction, input limits, log rotation, backup of ledger, docs | Chaos test: kill process mid-stream, restart, ledger consistent |

Removed from v1: browser adapter (D4), OAuth framework (D5). v2 candidates: OAuth for documented flows only, quality-aware ranking fed by Kernel measurements, native Gemini adapter if quota metadata is missing from the compatibility endpoint.

## 12. Acceptance criteria summary

1. No free quota is spent on a deployment already known to be exhausted, in the drills above.
2. Every response names the deployment that actually answered.
3. No provider secret is ever visible to a worker; workers hold only a capability token.
4. Pinned config cannot change without a hash-matching update.
5. A capacity report exists before any claim about worker counts is made.

## 13. Fixes to v1.0 weaknesses: status

| v1.0 weakness | v1.1 status |
|---|---|
| No account-wide rules | Fixed: scopes (Section 3) |
| Resolved model not reported | Fixed: Section 7.2 |
| No integration design | Fixed: Section 7 |
| Browser tier | Removed (D4) |
| OAuth tier under-specified | Deferred to v2 (D5) |
| Capacity untested | M4 |
| Unverified 429 shapes | Live capture moved to M1 |
| No quality-aware routing | Deferred: gateway exposes facts and per-deployment outcomes; Kernel owns ranking |
| Crude token estimate | Kept, stated, margin configurable |
| Pinning story | Section 8 |

## 14. Assumptions register

| ID | Assumption | Basis |
|---|---|---|
| A1 | Web dashboard plus CLI | Not confirmed |
| A2 | "About 12 permanent free models" means non-expiring free access; the rest of the ~300 are temporary | My reading of D7 |
| A3 | Data-class vocabulary comes from UMAWS policy; opaque strings | UMAWS §12.1 names `data_classes_allowed` but not a full class list |
| A4 | Pinned-config hash delivered via a signed file written by the Kernel | Design choice; Kernel mechanism in UMAWS is not specified for this |
| A5 | Free capacity supports a handful of workers, not 30 | Unmeasured guess |
| A6 | Gateway runs in WSL alongside the Kernel | Simplest option |
| A7 | Default strategy `use-it-or-lose-it` | Carried from v1.0, not confirmed |
| A8 | Single process, single asyncio loop, one worker | Atomic reservation without locks |
| A9 | Gemini's OpenAI-compatible endpoint is adequate | Unverified |
| A10 | Pull-based event delivery (Kernel polls) | Keeps I2 intact; alternative is push |

## 15. Verified versus not verified

**Verified in this session:** the UMAWS text (section numbers, invariants I2, I7, I8, I14, S4, capability tokens, `data_classes_allowed`, active-subset guidance, the Unix-socket/`flock` Kernel design) was read in full.

**Carried from the previous session, not re-verified here:** OpenRouter's account-wide `:free` limits (from its documentation as read then), LiteLLM behaviour and its March 2026 PyPI compromise, Gemini limits being per Google Cloud project with a midnight-Pacific daily reset (moderate confidence, third-party).

**Not verified (do not state as fact):** current Gemini free-tier limits and which models are free; Gemini 429 body shapes on either endpoint; pooling of Kilo, kenari and Groq limits; OmniRoute's quota behaviour; WSL-to-Windows localhost forwarding for this setup; terms-of-service positions for any provider; Google's terms on multi-project quota use (this proposal deliberately does not build that).

## 16. Instructions to the implementing agent

1. Build in milestone order; do not start M3 before M2 tests pass.
2. Never hard-code provider limits; ship placeholders and mark unknowns as unknown.
3. Do not add dependencies beyond the pinned set without asking.
4. Keep the core within the line budget; report if it will be exceeded and why.
5. At M1, ask the user to run the capture tool with their real keys; do not invent error bodies.
6. At each milestone, report what was tested and what was only assumed.
