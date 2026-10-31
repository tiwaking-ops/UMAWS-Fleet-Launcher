# Response-Time Tracking

**Status: live.** Every proxied request is timed and folded into the
deployment's `response_time_min_ms` / `response_time_max_ms` pair.

## The two fields

Both sit on a deployment in `src/quotagate/config.toml`, in milliseconds:

```toml
response_time_min_ms = 0        # or a measured value
response_time_max_ms = 900000   # or a measured value
```

They are **sentinels** for "not yet measured", and they mean opposite things:

| Field | Sentinel | Why |
|---|---|---|
| `response_time_min_ms` | `0` | The floor. No latency can be lower, so `0` is the natural "nothing observed yet". |
| `response_time_max_ms` | `900000` | 15 minutes. There is no natural ceiling, so a practical one stands in for "nothing observed yet". |

**The first observation sets both.** After that the minimum can only fall and
the maximum can only rise, so the maximum changes rarely — only when something
is genuinely slower than anything seen before. That is the behaviour wanted:
the field answers "what is the worst this has ever been", not "what was the
last call".

```python
>>> from quotagate.latency import update, MAX_UNSET
>>> update(0, MAX_UNSET, 938)      # first observation replaces both sentinels
(938, 938)
>>> update(938, 938, 300)          # faster: the minimum falls
(300, 938)
>>> update(300, 938, 4250)         # slower: the maximum rises
(300, 4250)
>>> update(300, 4250, 1200)        # ordinary: neither moves
(300, 4250)
```

## Where they are recorded

`src/quotagate/latency.py`:

- `update(min_ms, max_ms, elapsed_ms)` — pure, testable, the whole rule.
- `LatencyCursor` — the mutable pair for one deployment. A deployment's
  config entry is a **frozen dataclass shared by every request**, so the
  observed pair cannot live on it; this is the per-deployment mutable slice.
- `LatencyLedger` — every deployment's cursor, thread-safe.

The proxy calls `ledger.observe(deployment_id, elapsed_ms, deployment)` in
`src/quotagate/main.py` **for every outcome, including failures**. A slow
failure is exactly what a reliability figure needs to know about.

Read the current values at `GET /v1/quotagate/availability`, which reports
each deployment's limits, usage, cooldown state and observed latency:

```json
{
  "hermes/upstage-solar-mini4": {
    "latency": {"response_time_min_ms": 889, "response_time_max_ms": 4250},
    ...
  }
}
```

Each response also carries `X-QuotaGate-Latency-Ms` for the call just served.

## How the values get into config.toml

Two ways:

1. **Measured, then written by hand** — run
   `pilot/quotadiscover.py <deployment>` (Milestone: quota discovery), which
   reports the observed min/max at the end. Write them into the deployment's
   block *once you trust the sample*. This is how `solar-mini4`'s values
   (`889` / `4250`, 90 calls, 2026-10-23) got in.

2. **Live forever, written by nothing** — the in-memory ledger keeps them
   current for the life of the process without touching the file. If a
   persisted history is ever wanted, that is a new milestone, not a change to
   this design: it needs a decision about whether config.toml is allowed to
   be rewritten by the gateway at all, and right now it is not.

## What the numbers are for

Reliability judgement. A deployment that used to answer in 200 ms and now
takes 8 s is sick, and the fastest and slowest observations show it without a
time-series database.

They are **not** used for routing or admission decisions, and should not be:
latency says whether a deployment is healthy, not whether it is permitted.
Quota and cooldowns decide permission (`engine.py`); these two numbers
describe experience.

## Related

- `latency.py` — the implementation
- `pilot/quotadiscover.py` — measures both quota bounds and latency
- `pilot/spikes/quota-solar-mini4.md` — the first recorded measurement
