# QuotaGate Response Time Tracking

**Status:** not yet automated — fields must be populated manually or by a future monitoring service.

## Why track response time?

- **Reliability monitoring:** min/max latency helps judge if a provider or model is becoming sluggish or unstable.
- **Capacity planning:** slow models can become bottlenecks in high-throughput scenarios.
- **SLA detection:** consistent latency spikes may indicate upstream degradation.

## How to populate the fields

### Method 1: Manual entry (current)

Edit `src/quotagate/config.toml` for each deployment:

```toml
[deployment.omniroute.kilo]
account = 'omniroute'
model = 'omniroute/kilo'
family = 'cohere'
response_time_min_ms = 300   # example: 300ms observed minimum
response_time_max_ms = 1500  # example: 1.5s observed maximum
```

**Values are in milliseconds.** Set to `0` if no data is available.

### Method 2: Future automated tracking (planned)

A monitoring service could:

1. **Measure latency per request** from the proxy to the upstream.
2. **Aggregate per deployment** (e.g., per 24 hours).
3. **Update config.toml** automatically (e.g., via a webhook or periodic sync).

Example design:
- A separate `quotagate/monitor.py` that runs as a cron job.
- It queries the gateway's `/v1/quotagate/availability` endpoint.
- It updates `config.toml` with rolling min/max values.
- It commits the updated config to git (with review).

## How to compute min/max

Run a load test against a deployment and record the `x-omniroute-latency-ms` header:

```bash
curl -H "Authorization: Bearer $OMNIROUTE_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"auto/best-free","messages":[{"role":"user","content":"ok"}],"max_tokens":5}' \
     http://127.0.0.1:20128/chat/completions
```

The header `x-omniroute-latency-ms` gives the upstream's measured latency. Collect many samples and compute min/max.

## Example values (Cohere Command)

Based on S-A1 runs (2026-10-22):
- **kilo (laguna-s-2.1):** min ~25ms, max ~120ms (local router overhead)
- **pi (command-r):** min ~40ms, max ~150ms

These are **router-side**, not provider-side. To get provider-side latency, you'd need to measure against Cohere's API directly.

## Default behavior

If `response_time_min_ms` or `response_time_max_ms` are `0`, the gateway treats them as **unknown** and does not use them for any decisions.

## Future enhancements

- Add `response_time_p50_ms`, `response_time_p95_ms`, `response_time_p99_ms` for percentile tracking.
- Add a `latency_budget_ms` field to trigger alerts when latency exceeds a threshold.
- Integrate with Prometheus/Grafana for real-time dashboards.
