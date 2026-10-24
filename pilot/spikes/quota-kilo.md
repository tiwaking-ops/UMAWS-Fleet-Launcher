# Quota discovery - auto/best-coding

Upstream: `http://127.0.0.1:20128/chat/completions`

| rps | sent | ok | limited | p50 ms | max ms |
|---|---|---|---|---|---|
| 1 | 1 | 0 | 0 | 0 | 0 |

## Reading

No step was served fully from the first request, so this test could not establish any headroom.


### Caveats

* A short burst measured once is an *estimate*, not a published limit.  Providers often allow a burst above the sustained rate and punish it afterwards, so a clean ramp can overstate the sustainable ceiling.

* The absence of refusals at a step means the limit is somewhere above it - not that there is no limit.

* Steps the ramp never reached proved nothing; the table lists only the steps that actually sent requests.

* Daily and monthly caps need a far longer run than this makes; use the `--mode daily` path knowingly, or read them off the provider's own dashboard.
