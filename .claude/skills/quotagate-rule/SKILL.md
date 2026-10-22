---
name: quotagate-rule
description: Manages hierarchical quota rules (RPM, TPM, RPD) in gateway/quotagate/. Use when adding or modifying limits for deployments, accounts, or providers. Ensures America/Los_Angeles timezone compliance for daily resets. Do NOT use for general fleet orchestration or kernel state changes.
paths:
  - gateway/quotagate/*
  - tests/quotagate/*
---
# QuotaGate Rule Management

## Critical
- **Timezone**: All `RPD` (Requests Per Day) resets MUST be calculated using the `America/Los_Angeles` timezone. Never use UTC or local system time for daily quotas.
- **Hierarchy**: Rules must be applied at the correct scope: `deployment` (most specific), `account`, or `provider` (most general). A more specific rule always overrides a general one.
- **Metrics**: Only use supported metrics: `RPM` (Requests Per Minute), `TPM` (Tokens Per Minute), and `RPD` (Requests Per Day).
- **Validation**: Before applying, run `pytest tests/quotagate/` to ensure no regression in existing limit logic.

## Instructions

1. **Locate Rule Definition**
   - Quota rules are defined in `gateway/quotagate/rules.py` or configured via `gateway/quotagate/config.toml` (verify which one is active in the current environment).
   - Check `gateway/quotagate/models.py` to ensure the rule schema matches `QuotaLimit` or `RateLimit` classes.

2. **Define the Quota Scope**
   - Identify the scope key:
     - Provider: `gemini`, `openai`, `anthropic`
     - Account: The user/service account ID
     - Deployment: The specific model instance (e.g., `gpt-4o-deployment-1`)
   - **Validation**: Verify the scope key exists in the Fleet registry or Provider list before adding the rule.

3. **Apply the Limit**
   - Add the rule entry using the following structure:
     ```python
     # Example for rules.py logic
     QuotaRule(
         scope="provider",
         key="gemini",
         limits=[
             RateLimit(metric="RPM", value=2000),
             RateLimit(metric="RPD", value=100000, reset_tz="America/Los_Angeles")
         ]
     )
     ```
   - **Validation**: If updating `config.toml`, ensure the TOML syntax is valid and metrics are integers.

4. **Verify Timezone Handling**
   - If the rule includes `RPD`, confirm it imports `zoneinfo` or `pytz` and explicitly sets `America/Los_Angeles`.
   - **Validation**: Check `gateway/quotagate/utils.py` for the `get_current_window` function to ensure it respects the rule's timezone.

5. **Test and Verify**
   - Run the specific quota test suite: `pytest tests/quotagate/test_limits.py`.
   - Verify that hitting the limit returns a `429 Too Many Requests` response with the correct `Retry-After` header in the gateway logs.

## Examples

### User says: "Limit Gemini provider to 500 RPM and 10,000 daily requests"

**Actions taken:**
1. Checked `gateway/quotagate/rules.py` for existing `gemini` rules.
2. Updated the `PROVIDER_LIMITS` dictionary.
3. Added `RPD` with `America/Los_Angeles` timezone.
4. Ran `pytest tests/quotagate/`.

**Result:**
```python
# gateway/quotagate/rules.py

"gemini": [
    Limit(metric="RPM", value=500),
    Limit(metric="RPD", value=10000, tz="America/Los_Angeles")
]
```

## Common Issues

- **Error: `InvalidTimezoneError: America/Los_Angeles`**
  - **Fix**: Ensure `tzdata` is installed in the venv (`pip install tzdata`) as Windows does not include the IANA database by default.
- **Error: `Quota leak` (Limits not resetting)**
  - **Fix**: Check `gateway/quotagate/engine.py`. Ensure the redis/in-memory key includes the window timestamp (e.g., `quota:gemini:RPM:202310271201`).
- **Metric Mismatch**: Using `TPD` (Tokens Per Day) when only `TPM` is implemented.
  - **Fix**: Check `models.py` for supported `MetricType` enums and only use `RPM`, `TPM`, or `RPD`.