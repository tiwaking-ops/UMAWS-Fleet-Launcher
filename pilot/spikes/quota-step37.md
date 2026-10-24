# Quota discovery - stepfun/step-3.7-flash:free

Upstream: `http://127.0.0.1:8645/v1/chat/completions`

| rps | sent | ok | limited | p50 ms | max ms |
|---|---|---|---|---|---|
| 1 | 3 | 3 | 0 | 3016 | 8125 |
| 2 | 6 | 6 | 0 | 4452 | 8437 |
| 4 | 8 | 7 | 0 | 2859 | 4765 |

## Reading

Fully served up to **2 rps**, i.e. about **120 requests/minute**.  Treat that as an upper bound on what this test proved, not as the provider's real ceiling.

Observed latency across 16 calls: min **2312 ms**, max **8437 ms**.


### Caveats

* A short burst measured once is an *estimate*, not a published limit.  Providers often allow a burst above the sustained rate and punish it afterwards, so a clean ramp can overstate the sustainable ceiling.

* The absence of refusals at a step means the limit is somewhere above it - not that there is no limit.

* Steps the ramp never reached proved nothing; the table lists only the steps that actually sent requests.

* Daily and monthly caps need a far longer run than this makes; use the `--mode daily` path knowingly, or read them off the provider's own dashboard.
