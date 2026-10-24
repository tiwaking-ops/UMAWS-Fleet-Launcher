# M1 upstream — what OmniRoute actually returns

**Status:** live capture, measured.  **Author:** OpenCode.  **Date:** 2026-10-23.
**Authorised:** operator, 2026-10-23 — supplied the key and the variable name.

This records what the operator's OpenAI-compatible router returns, because
QuotaGate's M1 milestone ("passthrough + live capture") is defined by what can
actually be captured.  It is a measurement, not a design.

**No key is recorded in this file.**  The variable is `OMNIROUTE_API_KEY`; the
value was used from the environment only, and never written to the repository,
the event log or a commit.  (It did appear in the chat transcript, which is a
fact worth stating plainly: a secret pasted into a conversation is in that
conversation.)

## The endpoint map — and a trap

| Request | Result |
|---|---|
| `GET /models` | **200**, an OpenAI-shaped list, **10 230** models |
| `GET /v1/models` | **503** |
| `POST /chat/completions` | **200** |
| `POST /v1/chat/completions` | **no response** (hangs, then aborts) |

**The base URL is `http://127.0.0.1:20128`, with no `/v1`.**  Anything that
hard-codes the OpenAI `/v1` prefix — which is most SDKs' default assumption —
**fails** against this router.  An OpenAI client works only if its base URL is
set to the bare host, so that it appends `/chat/completions` itself.

This is exactly the sort of thing that costs a day if discovered late, so it
is recorded before QuotaGate's proxy is written: **the proxy must not assume
`/v1` is present on the upstream.**  Note the contrast with the pilot's own
policy, `.pm/policy.toml`, which sets the *gateway's* `base_url` to
`http://127.0.0.1:8766/v1` — that prefix is ours to define, and the proxy has
to translate between the two.

## What a successful call returns

`POST /chat/completions` with `model: "auto/best-free"`, `max_tokens: 5`:

```json
{"id": "e869590a-...", "object": "chat.completion",
 "model": "command-a-03-2025",
 "choices": [{"finish_reason": "stop",
              "message": {"role": "assistant", "content": "ok"}}],
 "usage": {"prompt_tokens": 6, "completion_tokens": 1, "total_tokens": 7,
           "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0},
           "completion_tokens_details": {"reasoning_tokens": 0,
                                         "audio_tokens": 0,
                                         "accepted_prediction_tokens": 0,
                                         "rejected_prediction_tokens": 0}}}
```

**Usage is published and capturable.**  That is the good news: token counts
per call — the thing `L-F2` says the Kernel cannot see for direct-CLI
profiles — are available here.

## The headers — and the decisive absence

Present and useful:

```
x-omniroute-decision: strategy=auto; provider=cohere; latency_ms=741
x-omniroute-latency-ms: 741
x-omniroute-cache: MISS          x-omniroute-cache-hit: false
x-request-id / x-correlation-id / x-conversationid
x-omniroute-route-class: CLIENT_API
access-control-allow-headers: ... X-OmniRoute-Lease-Owner, X-OmniRoute-Lease-Generation ...
```

`x-omniroute-decision` is genuinely valuable: it attributes each call to the
provider actually used (`provider=cohere` here), which a quota engine needs in
order to attribute spend.

**Absent: every rate-limit signal.**  There is no `x-ratelimit-*`, no
`retry-after`, no remaining-quota header — on a successful call, and no
`429` could be induced to inspect.

### What that means for QuotaGate

1. **Usage capture: yes.**  M1 can meter tokens per call, per profile, from
   `usage` and attribute the provider from `x-omniroute-decision`.
2. **Quota discovery: no.**  The router does not publish the upstream's
   limits, so `V-03` ("the real 429 body shape and rate-limit headers")
   **cannot be closed by observation through this upstream.**  Against this
   router, QuotaGate's limits must be **declared locally** — which is what
   `gateway/quotagate/config.py` already models — rather than learned from the
   provider.  That is a weaker guarantee and should be stated as such.
3. **Timeouts are mandatory.**  `auto/cheap` **timed out at 45 s** while
   `auto/best-free` answered in ~1 s.  A passthrough proxy without a timeout
   policy will hang on model aliases that route to slow or unreachable
   providers.  The proxy needs a deadline and a defined failure, not an open
   socket.

## Scope, honestly

This was measured against **one** upstream: the operator's own router.  It
says nothing about what a public provider's API returns directly, where
rate-limit headers are normally present.  If a public provider is ever put
behind the gateway, the capture logic must be re-measured against it rather
than assumed.

Also unchanged from the earlier caveat: M1 only sees traffic that **routes
through it**.  Every profile has `via_gateway = false` today, and the closed
CLIs (kilo, opencode, cline, hermes) cannot be pointed at a proxy unless they
accept a custom base URL.  So the realistic first scope is the **context-sync
lane** and any OpenAI-compatible client — not "all agent usage".
