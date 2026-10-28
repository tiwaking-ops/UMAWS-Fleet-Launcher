---
name: quotagate-rule
description: Manages hierarchical quota rules (RPM, TPM, RPD) in src/quotagate/. Use when adding or modifying limits for deployments, accounts, or providers. Ensures America/Los_Angeles timezone compliance for daily resets. Do NOT use for general fleet orchestration or kernel state changes.
paths:
  - src/quotagate/*
  - tests/quotagate/*
---
# QuotaGate Rule Management

## Critical
- **Location**: the QuotaGate implementation lives in `src/quotagate/`. The old
  `gateway/quotagate/` path is empty and is **not** where the code is.
- **Timezone**: All `fixed_daily` / `fixed_monthly` resets MUST be calculated
  using an explicit IANA timezone (`zoneinfo.ZoneInfo`), never the machine's
  local time. `America/Los_Angeles` is the operator's default for daily quotas.
- **Hierarchy**: Rules are applied at the correct scope: `deployment` (most
  specific), `account`, `quota_group`, `provider` (most general). A more
  specific rule always overrides a general one.
- **Metrics**: Only two metrics exist: `requests` and `tokens`. Windows are
  `rolling_60s`, `rolling_24h`, `fixed_daily`, `fixed_monthly`,
  `fixed_interval`. There is no `RPD`/`TPM`/`RPM` vocabulary in the code.
- **Unknown ≠ zero**: `QuotaRule.limit == 0` means *unknown*, not *no
  requests*. A rule is only enforced when `limit > 0`.
- **Validation**: Before applying, run `pytest tests/quotagate/` to ensure no
  regression in existing limit logic.

## Instructions

1. **Locate the rule definition**
   - Rules are declared in `src/quotagate/config.toml` under `[[quota_rule]]`.
   - The schema is `QuotaRule` in `src/quotagate/config.py`:
     `scope`, `metric`, `window`, `limit`, `target`, `timezone`,
     `interval_seconds`, `reset_at`.
   - Engine behaviour is in `src/quotagate/engine.py`; the window/timezone
     maths is in `window_start` / `window_reset`.

2. **Define the quota scope**
   - Identify the scope key:
     - Provider: `cohere`, `nous` (as configured in `[provider.*]`)
     - Account: the `[account.*]` id (e.g. `omniroute`, `nous-portal`)
     - Deployment: the `[deployment."provider/model"]` id
   - **Validation**: the `target` must match an id that already exists in the
     corresponding section of `config.toml`.

3. **Apply the limit**
   - Add a `[[quota_rule]]` block:
     ```toml
     [[quota_rule]]
     scope = "provider"
     metric = "requests"
     window = "rolling_60s"
     limit = 500
     target = "gemini"

     [[quota_rule]]
     scope = "provider"
     metric = "requests"
     window = "fixed_daily"
     limit = 10000
     target = "gemini"
     timezone = "America/Los_Angeles"
     ```
   - **Validation**: TOML syntax valid; `limit` a positive integer; `metric`
     one of `requests` / `tokens`; `window` one of the five window constants.

4. **Verify timezone handling**
   - If the rule uses `fixed_daily` or `fixed_monthly`, set `timezone`
     explicitly. The engine calls `ZoneInfo(rule.timezone)`; the default is
     `UTC`.
   - **Validation**: check `window_start` / `window_reset` in
     `src/quotagate/engine.py` for the timezone-aware path.

5. **Test and verify**
   - Run the quota test suite: `pytest tests/quotagate/`.
   - Verify that hitting the limit returns a `429 Too Many Requests` response
     with the correct `Retry-After` header.

## Examples

### User says: "Limit the Gemini provider to 500 requests/min and 10,000 daily requests"

**Actions taken:**
1. Checked `src/quotagate/config.toml` for existing `gemini` rules.
2. Added two `[[quota_rule]]` blocks scoped to `provider` / `gemini`.
3. Set `timezone = "America/Los_Angeles"` on the `fixed_daily` rule.
4. Ran `pytest tests/quotagate/`.

**Result:**
```toml
[[quota_rule]]
scope = "provider"
metric = "requests"
window = "rolling_60s"
limit = 500
target = "gemini"

[[quota_rule]]
scope = "provider"
metric = "requests"
window = "fixed_daily"
limit = 10000
target = "gemini"
timezone = "America/Los_Angeles"
```

## Common Issues

- **Error: `InvalidTimezoneError: America/Los_Angeles`**
  - **Fix**: Ensure `tzdata` is installed in the venv (`pip install tzdata`) as
    Windows does not include the IANA database by default.
- **Error: `Quota leak` (Limits not resetting)**
  - **Fix**: Check `src/quotagate/engine.py`. Ensure the in-memory key includes
    the window timestamp (e.g. `quota:gemini:RPM:202310271201`).
- **Metric Mismatch**: Using `RPD` / `TPM` / `RPM` instead of the code's
  `requests` / `tokens` metrics.
  - **Fix**: Check `METRICS` in `src/quotagate/config.py` and use only those
    values, pairing them with the right `window`.
- **Rule silently ignored**
  - **Fix**: `limit` must be > 0 (0 means unknown, so the rule is not
    enforced), and `target` must exactly match an id in the matching section.
