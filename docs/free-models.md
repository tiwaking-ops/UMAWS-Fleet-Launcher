# Free LLM Models (UMAWS Fleet reference)

Last updated: 2026-10-26 (operator Tiwa Pene).

## Hermes CLI — Nous portal (access via `hermes -m <model_id>`)

- upstage/solar-mini4:free
- meituan/longcat-2.5-preview:free
- poolside/laguna-xs-2.1:free
- poolside/laguna-s-2.1:free
- stepfun/step-3.7-flash:free
- reflection/beam-1.0-501b-a23b:free
- ornith/ornith-1.5-122b:free

## Kenari provider — 50 requests/day, account-wide

Use only `kenari/nemotron-3-ultra-550b-a55b:free` to stay within the shared
account ceiling. Other Kenari free models (listed for reference only):

- agnes-2-5-flash:free
- agnes-3-0-flash:free
- beam-1-0:free
- dots-3-note-preview:free
- glm-4-7-flash:free
- hy3:free
- laguna-s-2-1:free
- laguna-xs-2-1:free
- longcat-2-5-preview:free
- mimo-v2-6-flash:free
- muse-spark-1-3-contributor:free
- nemotron-3-5-super-vl:free
- nemotron-3-nano-omni-30b-a3b-reasoning:free
- nemotron-3-super-120b-a12b:free
- nemotron-3-ultra-550b-a55b:free
- ornith-1-5-122b:free
- qwen3-8-omni-flash:free
- solar-mini4:free

## Hermes Agent — Ollama (local/cloud launch)

- beam:cloud (launch via `ollama launch hermes --model beam:cloud`)

### pi provider config (Ollama)

```json
"ollama": {
  "baseUrl": "https://ollama.com/v1",
  "api": "openai-completions",
  "apiKey": "${OLLAMA_API_KEY}",
  "models": [
    {
      "id": "beam:cloud",
      "name": "beam:cloud",
      "reasoning": true,
      "input": ["text"],
      "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
      "contextWindow": 1048576,
      "maxTokens": 128000
    }
  ]
}
```

Requires `OLLAMA_API_KEY` env var.

## OrcaRouter provider (pi) — ORCAROUTER_API_KEY

- deepseek/deepseek-v4-flash-free
- z-ai/glm-5.3-flash-free
- tencent/hy4-preview-free
- tencent/hy3-free

Requires `ORCAROUTER_API_KEY` env var.

## ZAI provider — ZAI_API_KEY

- glm-4.5-flash
- glm-4.6v-flash
- glm-4.7-flash

Rate limited but rates are unknown; reset unknown, possibly every 5 hours.
Limits are per account and per model, based on concurrency (typically 1 concurrent request for free Flash models). Official numbers shown only in the Z.ai console (z.ai/manage-apikey/rate-limits). 429/1302 = rate limit reached; 429/1305 = service overloaded.

Requires `ZAI_API_KEY` env var.

## Zyphra provider — ZYPHRA_API_KEY

```json
"zyphra-gateway": {
    "baseUrl": "https://api.zyphracloud.com/api/v1",
    "api": "openai-completions",
    "apiKey": "ZYPHRA_API_KEY",
    "models": [
      {
        "id": "zyphra/ZAYA1-8B",
        "name": "ZAYA1-8B Reasoning",
        "contextWindow": 131072,
        "maxTokens": 4096
      }
    ]
  }
```

Requires `ZYPHRA_API_KEY` env var.

## Note (opencode)

OpenCode's model list (via its config or `opencode models`) shows the Ollama cloud beam model as `ollama-cloud/beam`, not `beam:cloud`. This is the identifier to use in profiles and adapter configs for opencode.

## Note

Kenari rate limit is account-wide (50 req/day), so prefer the single
nemotron-3-ultra model there. Hermes (Nous) free models are not account-limited
in the same way; see agents.toml for which profiles use them.
