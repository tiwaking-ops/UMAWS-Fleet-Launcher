---
document:
  title: "Project Report: Recovery Ladder, QuotaGate M1, Model Limits and Provenance — results of the 2026-10-23 session"
  status: "Report — results and decisions from a supervised session; advisory, no authority to promote"
  version: "1.0.0"
provenance:
  author_llm: {name: "OpenCode", version: "Step 5 Preview (stepfun-ai/step-5-preview)"}
  assessor_llm: []
  last_modified_by_llm: {name: "OpenCode", version: "Step 5 Preview (stepfun-ai/step-5-preview)"}
  created_date: "2026-10-23"
  last_modified_date: "2026-10-23"
audience:
  primary: "The human supervisor (single operator)"
  secondary: "The next implementing agent, continuing from pilot/STATE.md"
  tertiary: "A reviewer assessing whether D-39…D-44 were earned"
pilot:
  decisions_recorded: "D-39, D-40, D-41, D-42, D-43, D-44"
  commits_taken: "53b82b1 … a1b3b43 (eleven)"
  state_after: "pilot/STATE.md as of a1b3b43"
---

# Recovery Ladder, QuotaGate M1, Model Limits and Provenance

**Author:** OpenCode (Step 5 Preview) · **Date:** 2026-10-23
**Session scope:** the recovery ladder with real CLIs; QuotaGate M1; provider and
model limits; provenance.
**Authorisations, in order:** operator — "G3 closed. APPROVED", "2. Ladder.
APPROVED", "#1 Build QuotaGate M1 APPROVED", "We can still test them",
"Narrow the pattern to only treat :free as an alias when the model starts with
openrouter/" APPROVED, "Provenance first. APPROVED".

> This report is graded on honesty, not on completeness. A partial result with
> an accurate report is a successful pilot; a complete-looking result with
> unverified claims is not. Everything that was **not** established is said so
> plainly, and in the same breath as the result it qualifies.

---

## 1. Outcome

Six results, one gate closed by the operator, and three defects found by
testing rather than by reading.

| # | Result | State | Evidence |
|---|---|---|---|
| 1 | A real CLI through a real lease, accepted by the Kernel | **PASS** | `pilot/g3-real-cli.md`, `pilot/spikes/g3/` |
| 2 | G3 | **CLOSED by the operator** | D-40 |
| 3 | The recovery ladder with real CLIs | **L4 and L3 real; real recovery achieved** | `pilot/ladder-real-cli.md` |
| 4 | QuotaGate M1, multi-upstream, with live capture | **BUILT** | `src/quotagate/`, D-38, D-42 |
| 5 | Provider and model limits | **RESEARCHED and CONFIGURED**; Nous limits unverified | `src/quotagate/config.toml` |
| 6 | Provenance — which model actually served | **IMPLEMENTED and MEASURED** | `tests/fleet/test_provenance.py`, D-44 |

Suite green at every commit; `pmk sentinel`, `pmk pins check` and
`pmk context drift` clean throughout. Eleven commits, `53b82b1` … `a1b3b43`,
tree clean at close.

The three defects found by *running* things rather than reading them:

1. A **double `/v1`** in the hermes upstream URL — the base URL carried `/v1`
   and the client's path carried it too. Only caught by resolving the URLs and
   looking at them.
2. The quota ramp reported **"fully served up to 64 rps"** for steps that sent
   *nothing*, because a step that sent zero requests was counted as clean.
3. The **L1 label versus the executed mode** in the recovery ladder (section 3).

All three are recorded below rather than quietly fixed, because each was a
place where the code looked correct and wasn't.

---

## 2. G3 — a real CLI through a real lease (D-39), then closed (D-40)

### 2.1 What was not previously tested

`pilot/demo_one_click.py` runs the entire lifecycle — brief, PDD, task cards,
claim, worktree, order file, spawn, oracles, evidence bundle, submit, merge
queue, close-check — with the **fake** CLI. That proves the plumbing. It does
not prove that a *real agent*, given a real lease and a real worktree, can do
work the Kernel accepts.

### 2.2 The result

`pilot/g3-real-cli.py`, against a scratch repository outside the pilot:

```
[3] task card T-0002 created (READY)
[4] spawned T-0002 on kilo-real pid=10188
[5] finished T-0002: submitted (after 500s)
[7] merge T-0002: ok=True (merged)
[9] close-check: ok=True
    G-001: pass (python check.py)
    gate: pass (python check.py)
[10] src/csv2md.py size after the run: 1512 bytes
```

The evidence bundle is genuine, not asserted:

```json
"outputs": [{"path": "src/csv2md.py", "sha256": "98fba42e0e65…"}],
"diff_scope_check": {"changed": ["src/csv2md.py"], "violations": [], "ok": true},
"oracle_results": [{"cmd": "python check.py", "exit": 0, "ok": true}],
"constitution_hash": "33c8b830d80f…"
```

**The oracle was deliberately harder than the demo's.** The demo only checks
that a file *exists*, so a worker writing an empty file would pass. This oracle
runs the worker's script and parses its output as a Markdown table. The model
produced `pilot/spikes/g3/csv2md.produced.py`, which uses `csv.reader`, escapes
pipes, pads columns and handles errors — a judgement on one sample, not a claim
about model quality.

### 2.3 What this does not establish

- **The recovery ladder was never exercised** — it succeeded on `attempt=1`
  with `restart_count=0`. The failure paths remained fixture-only. (Fixed in
  section 3.)
- **One task, one CLI, one model, one successful attempt.**
- **A small task consumed 500 seconds of a 720-second budget.** Wall-clock is
  the only budget axis the Kernel can see for a direct-CLI profile (`L-F2`), so
  for real tasks this is a live risk rather than a formality.

### 2.4 Closure

The operator closed the gate on their own authority — "G3 closed. APPROVED" —
recorded as D-40. The OpenCode half remains **parked, not satisfied**: the
quota is unpublished, so it stays `UNKNOWN` (D-37) and the test is to be run
together later. **A closed gate is not a satisfied condition**, and the pending
item is carried in `pilot/STATE.md` rather than written off.

---

## 3. The recovery ladder with real CLIs (D-41)

`pilot/ladder-real-cli.py` runs three scenarios against live agents in scratch
repositories. The failure source is real: OpenCode's free tier is exhausted
today, so it fails genuinely, and nothing synthetic is fed to the classifier.

### 3.1 What was exercised

| Step | How | Result |
|---|---|---|
| **L4** | opencode really fails `QUOTA` → `attempt(1) >= attempts_max(1)` | task **BLOCKED**, lease revoked, worktree quarantined, queue item `Q-001` with `safe_default: "escalate to the human"` |
| **L3** | `max_restarts_per_task = 0` | lease revoked, **fence bumped 1→2**, worktree quarantined, task returned **READY**, and **no queue item** (L3 is not terminal) |
| **L1 → real recovery** | opencode fails → next profile → kilo succeeds | work **submitted**, oracles passed, evidence bundle complete |
| **L0** | no live `NETWORK` failure could be produced | **not exercised** |

The L3 fence bump was verified empirically rather than trusted from the code:
the card read back `fence=2` with no open lease. `state.py` bumps it by default
(`card.fence + 1`) without emitting a dedicated event, which is correct but
silent — worth knowing if the log is ever audited for fence progression.

### 3.2 A defect: L1 was chosen and L2 was needed

The recovery scenario produced this in the trace:

```
AGENT_FAILED: profile=oc-live step=L1 reason=QUOTA: resume the session on the next profile
AGENT_RESUMED: profile=kilo-real
```

The receiving agent's order file said:

```
## Handoff
none
```

and `HANDOFF.md` was **absent** from the worktree.

The cause, confirmed in code:

- `recover.decide()` picks the step from `adapter.caps.can_resume`, and
  OpenCode's adapter claims `True`.
- The dispatcher can only actually resume when
  `profile.supports_resume() and run.session` — and the receiving profile had
  `argv_resume = []`.
- So the mode was `"new"` while the step said L1.
- **The handoff note is written only for L2**, so a fresh session started
  *without* the failure context the handoff exists to carry.

Consequences, stated plainly:

- The event is named `AGENT_RESUMED` when nothing was resumed. The log is the
  authority, so an auditor reading it would believe a resume occurred.
- A receiving agent began work with no note explaining that the previous agent
  had exhausted its quota.

This is deferred, not fixed. Changing it alters recovery behaviour and the
meaning of a log event, both of which are the operator's call; the finding is
recorded in D-41 so it cannot quietly lapse.

### 3.3 L0 remains unexercised

The ladder takes L0 only for `NETWORK` failures, and no live CLI on this
machine reliably produces one. The fake CLI has a fixture, so the *branch* is
covered by unit tests; the *real-CLI path* is not. That difference is stated
rather than glossed.

---

## 4. QuotaGate M1 (D-38, D-42)

### 4.1 Two upstreams with opposite path conventions

Measured, not assumed (D-38): the operator's router serves `/models` and
`/chat/completions` but returns **503 on `/v1/models`** and **hangs on
`/v1/chat/completions`**. Hermes' subscription proxy does serve `/v1`. The same
request path therefore needs different rewriting per upstream, so
`path_style` lives on the upstream table:

| Upstream | Base URL | `path_style` | Auth |
|---|---|---|---|
| `omniroute` | `http://127.0.0.1:20128` | `strip` | `Bearer` `OMNIROUTE_API_KEY` |
| `hermes` | `http://127.0.0.1:8645` | `keep` | OAuth, injected by `hermes proxy` |

### 4.2 The credential problem, solved

The Nous Portal is **OAuth, not an API key**, so QuotaGate could never proxy
those models with a stored key. `hermes proxy start` serves an OpenAI-
compatible endpoint on `127.0.0.1:8645/v1` that injects and refreshes the bearer
itself and accepts any bearer from the client. Chaining QuotaGate → hermes
proxy → Portal resolves it, and the gateway holds no credential at all.

### 4.3 Live capture

Built and verified:

- **Usage** — captured from the response body's `usage` block and reconciled
  onto the reservation.
- **Latency** — every response timed, folded into the deployment's min/max pair.
- **Provenance** — section 6.
- **Timeouts** — mandatory, not optional. `auto/cheap` was observed to time out
  at 45 s while `auto/best-free` answered in about 1 s, so a proxy without a
  deadline hangs on bad aliases.

The proxy also **rewrites the client's deployment onto the upstream's model**
(`omniroute/kilo` → `auto/best-coding`), because the two namespaces are
different things.

### 4.4 Response-time fields, with sentinels

`response_time_min_ms` / `response_time_max_ms` on every deployment, in
milliseconds. Both are **sentinels** for "not yet measured", and they mean
opposite things:

| Field | Sentinel | Why |
|---|---|---|
| `response_time_min_ms` | `0` | The floor. No latency can be lower, so `0` naturally means "nothing observed yet". |
| `response_time_max_ms` | `900000` | Fifteen minutes. There is no natural ceiling, so a practical one stands in for "nothing observed yet". |

The first observation sets both. Afterwards the minimum only falls and the
maximum only rises, so the maximum changes rarely — only when something is
genuinely slower than anything seen before:

```
(0, 900000, 938)      -> (938, 938)    first observation replaces both sentinels
(938, 938, 300)       -> (300, 938)    faster: the minimum falls
(300, 938, 4250)      -> (300, 4250)   slower: the maximum rises
(300, 4250, 1200)     -> (300, 4250)   ordinary: neither moves
```

They are **not** used for routing or admission. Latency says whether a
deployment is healthy, not whether it is permitted; quota and cooldowns decide
permission. Readable at `GET /v1/quotagate/availability`, and each response
carries `X-QuotaGate-Latency-Ms`.

### 4.5 Quota discovery by measurement (D-42)

`pilot/quotadiscover.py` fires a controlled ramp and reports where the upstream
starts refusing. Neither upstream publishes limits — the portal page sits
behind a Vercel anti-bot challenge, `hermes portal info` reports auth and
routing but no quotas, and the shipped model catalog carries no pricing data —
so the tool exists precisely to measure rather than declare.

First measurement, `hermes/upstage-solar-mini4`, 90 calls:

| rps | sent | ok | refused | p50 ms | max ms |
|---|---|---|---|---|---|
| 1 | 3 | 3 | 0 | 1734 | 1906 |
| 2 | 6 | 6 | 0 | 1851 | 3889 |
| 4 | 12 | 12 | 0 | 1679 | 3391 |
| 8 | 24 | 24 | 0 | 1585 | 3280 |
| 16 | 45 | 45 | 0 | 1656 | 4250 |

**90 requests, zero refusals.** No ceiling was found — which means the limit is
above what this ramp reached, **not** that there is no limit. The tool writes
that caveat into every report so the number cannot be misread later. The
substantive finding is **latency: 889–4250 ms, p50 ≈ 1.7 s**. The free tier is
slow, not throttled.

---

## 5. Provider and model limits (D-43)

### 5.1 Cohere — published, and therefore citable

Researched from Cohere's own rate-limits documentation:

| Endpoint / model | Trial key | Production key |
|---|---|---|
| Command A / R / R+ / R7B | 20 req/min | 500 req/min |
| Command A+, Reasoning, Translate, Vision | 20 req/min | contact sales |
| Rerank | 10 req/min | 1000 req/min |
| Embed (text) | 2000 inputs/min | 2000 inputs/min |
| Embed (images) | 5 inputs/min | 400 inputs/min |
| EmbedJob | 5 req/min | 50 req/min |
| Tokenize | 100 req/min | 2000 req/min |
| Parse | 500 req/min | 500 req/min |
| Audio Transcriptions | 5 req/min | contact sales |
| **Trial monthly cap** | **1000 calls/month** | unlimited |

Applied to the provider scope with the trial tier assumed, and marked as a
published source rather than a guess.

### 5.2 Nous — not published anywhere reachable

The limits for the Nous deployments are marked **unverified and self-imposed**
in `config.toml`, with the reason written in the file. They protect the
deployment from the gateway's own mistakes; they are **not** a claim about what
Nous permits. `pilot/quotadiscover.py` is the way to replace them with
measurements.

### 5.3 The models, and a naming correction

The operator supplied eight free models reachable only through the Hermes
agent, with `hermes -m <model_id>` and the Nous portal as default provider.
Hermes' own live cache (`~/.hermes/context_length_cache.yaml`) revealed a
detail the list did not show: **the `:free` suffix is required.** The cache holds
both `stepfun/step-3.7-flash` and `stepfun/step-3.7-flash:free` — the suffix is
a *pricing tier*, not a different model. Without it these are paid-tier ids.

Four further models were found in that cache and configured, explicitly marked
*offered, not confirmed*, because a model appearing in a cache is not a model
that still works. Context windows are taken from the cache rather than guessed.

### 5.4 Two providers, two limit shapes — routed differently

The operator's experience, which changes the routing:

- **OpenRouter is ACCOUNT-limited.** The ceiling is on the account, so rotating
  models buys nothing and spends the shared budget faster.
  `kilo/openrouter/free` is therefore **deliberately excluded** from the
  rotation, with the reason written into `agents.toml` so it is not
  re-added by a later agent "helpfully".
- **Kilo Gateway is MODEL-limited**, and `kilo/kilo-auto/free` picks a free
  model from the request type — which makes it the right default, because the
  gateway does the choosing and a per-model ceiling binds rather than the whole
  account stopping.

`kilo-auto` now defaults to `kilo/kilo-auto/free`, with the other live free
models as its `models` list. That list does double duty: it is the recovery
ladder's **L1 swap targets** and the optional extra agents, so an exhausted
model moves to the next instead of cooling the whole profile.

`-m {model}` was added to the argv, and **it must precede `run`**: `-m` is a
global flag, so placing it after the subcommand silently runs the default model
— which would have looked exactly like a working profile while never using the
model asked for.

The free list was verified live with `kilo models` and cross-checked against
`kilo.ai/landing/free-models`.

---

## 6. Provenance (D-44)

### 6.1 The problem

D-L12 stops a verifier being the implementer's *declared family*. That is a
guess about a string, and it fails in both directions:

- `kilo/kilo-auto/free` is an opaque router, so a profile declaring a different
  family can still be the same underlying model checking its own work.
- two genuinely different models in one family are rejected needlessly.

### 6.2 The fact

The gateway is the one component in the request path, and the upstream's own
answer names the model that served. Measured live against hermes' subscription
proxy:

```
upstream answered in 1765 ms
provenance: {"model": "upstage/solar-mini4:free"}
```

Where the body names a router alias, `x-omniroute-decision: … provider=cohere`
names the provider instead.

### 6.3 What was built

| Piece | Role |
|---|---|
| `src/quotagate/provenance.py` | capture from the response, parse, SQLite ledger |
| `GET /v1/quotagate/provenance` | read-back by `?task=` or `?deployment=&start=&end=` |
| `src/fleet/provenance.py` | the Fleet's reader, plus a worktree cache so provenance outlives the gateway |
| `harness.py` | `MODEL_SERVED` recorded at submit |
| `select.py` | served models compared **before** families |

**The query is by window + deployment, not by task header**, because the Fleet
spawns a CLI *process* and cannot put a header on requests the CLI makes. A
lease is exclusive to one worktree and a profile is capped by `max_concurrent`,
so the calls a deployment made inside the window were that lease's. The task
header is still honoured where a client can send it.

**Empty is a real answer, not a failure.** A direct-CLI profile never reaches
the gateway (`L-F2`), so the code returns an empty set and leaves D-L12's
existing veto in force. It does *not* fall back to the profile's declared
`model`, because inventing a name is exactly the failure provenance exists to
remove. A test pins that behaviour.

### 6.4 The honest limitation

Provenance can only **narrow** eligibility today, never widen it. Both rules
apply, because they are different axes: family is about the *lab* (shared blind
spots), provenance about the *model* (same model checking its own work). Every
`agents.toml` profile still declares `family = "unknown"`, so D-L12's
unknown-family veto remains what actually gates verification, regardless of
what the gateway reports. Widening it needs a declared family, which is the
operator's decision (D-43) and not the implementer's.

---

## 7. The `:free` alias correction (D-43)

A finding worth recording because it changes who may verify.

`ALIAS_PATTERNS` treated the `:free` suffix as an alias **because OpenRouter
uses it**. Measured on this machine, the `:free` *colon* suffix is a **Kilo/Nous
pricing-tier convention**, not an OpenRouter one — `openrouter/free` and
`poor-*` are the forms OpenRouter actually uses, and both were already caught
by their own patterns.

The consequence was that `kilo/poolside/laguna-s-2.1:free` and
`upstage/solar-mini4:free` — concrete free-tier models — were read as aliases,
marked `family = "unknown"`, and left unusable as verifiers.

Narrowed to `^openrouter/.*:free$`. Verified against every real model string in
the repository and the live kilo list:

| Model | Family now | Correct? |
|---|---|---|
| `kilo/poolside/laguna-s-2.1:free` | `poolside` | yes |
| `kilo/nvidia/nemotron-3.5-super-vl:free` | `nvidia` | yes |
| `openrouter/anthropic/claude-opus:free` | `unknown` | yes — still an alias there |
| `kilo/kilo-auto/free` | `unknown` | yes — it genuinely is an opaque router |

**A caveat stated plainly when it was offered:** this does not change any
profile in `agents.toml`. `from_dict` takes `family` straight from the table
and never consults the guess, so all six live profiles keep the family they
declare. `guess_family` is consulted by `import_prompts`, which is what this
fixes. Making an `agents.toml` profile verifiable needs an explicit family line
— a human assertion about model lineage.

---

## 8. Verified versus assumed

### Verified by measurement this session

- A real CLI took work through a real lease and the Kernel accepted it, with a
  functional oracle and a genuine evidence bundle.
- L4, L3 and a real recovery, from live failures.
- The recovery ladder's L1 label diverging from the executed mode when
  `argv_resume = []`.
- Both upstreams' path conventions, and the double-`/v1` bug that followed.
- The upstream naming the model that served, live.
- The latency sentinel semantics, against a five-case table.
- Cohere's published limits.
- The `:free` suffix behaviour across every real model string.

### Still open, and *not* claimed

- **L0 with a real CLI.** No live `NETWORK` failure source exists. The branch is
  fixture-covered only.
- **A real L1 resume.** Never observed: the only L1 reachable took mode `"new"`.
  It needs a profile with `argv_resume` populated *and* a live session.
- **Nous limits.** Unverified by declaration.
- **The upstream model strings for the omniroute deployments** are placeholders
  (`auto/best-coding`) needing operator confirmation; OmniRoute resolves
  `auto/*` aliases per call, so which model actually serves is only knowable
  from `x-omniroute-decision`.
- **Model quality.** One sample each; no claim about any model's suitability.
- **Quota ceiling for any free model.** Absence of refusals bounded the test,
  not the provider.

---

## 9. Unresolved, deferred, or blocked — and on whom

| Item | Status | Blocked on |
|---|---|---|
| The L1/L2 mislabel and missing handoff note | **deferred**, recorded in D-41 | operator — changes recovery behaviour and a log event |
| Declaring a family for one verifier profile | **pending**, D-43/D-44 | operator — it is an assertion about model lineage |
| G3's OpenCode handover | **parked**, D-37 | operator — to be run together |
| Nous limits | **unverified** | nobody blocked; `pilot/quotadiscover.py` exists |
| The five cline models | **offered, not working** | operator — needs live-call authorisation |
| S-W1 / F7 capacity run | **not run** | operator — "wait for approval unless simple" |
| G4 / G5 | **held** | operator |
| Upstream model strings for omniroute | **placeholders** | operator — needs confirmation |
| The wall-clock budget risk from 500 s of 720 s | **measured, unmitigated** | design work |

Nothing was fixed unilaterally where the change would have altered recovery
behaviour, verifier eligibility, or the meaning of a log event. Those were
reported instead, which is the only treatment consistent with a pilot graded on
honesty.

---

## 10. Recommended next step

**Declare one verifier profile.** Provenance, the response-time fields, the
quota engine and the discovery harness are all in place to receive it; the
single missing line is what turns this from infrastructure into a working
verification loop:

```toml
[[profile]]
id = "kilo-verify-poolside"
model = "kilo/poolside/laguna-s-2.1:free"
family = "poolside"          # the operator asserting the lineage
roles = ["verify", "review"]
```

After that, in the order I would argue for:

1. **Sweep the remaining free models** with `pilot/quotadiscover.py` — about two
   minutes each, and it replaces declared limits with measured ones.
2. **Fix the L1/L2 defect** — it is small, but it needs a decision first,
   because it changes what `AGENT_RESUMED` means in the log.
3. **Build the remaining QuotaGate milestones** against the now-measured
   upstream behaviour.
4. **Run S-W1/F7** to replace the `max_total_agents = 20` guess.

---

*Author: OpenCode, Step 5 Preview (stepfun-ai/step-5-preview), 2026-10-23.
Advisory record; no authority to promote. Decisions D-39…D-44 in
`pilot/decisions.md`; current state in `pilot/STATE.md`.*