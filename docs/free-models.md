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

## AnyRouter provider — ANYROUTER_API_KEY

```json
"anyrouter": {
  "baseUrl": "https://anyrouter.win/v1",
  "api": "openai-completions",
  "apiKey": "{env:ANYROUTER_API_KEY}",
  "models": [
    {
      "id": "anyrouter/free",
      "name": "AnyRouter Free",
      "contextWindow": null,
      "maxTokens": null
    },
    {
      "id": "apple/foundation-model",
      "name": "Apple Foundation Model",
      "contextWindow": 4000,
      "maxTokens": null
    },
    {
      "id": "cohere/north-mini-code",
      "name": "North Mini Code",
      "contextWindow": 256000,
      "maxTokens": null
    },
    {
      "id": "deepseek/deepseek-v4-flash",
      "name": "DeepSeek-V4-Flash",
      "contextWindow": 128000,
      "maxTokens": null
    },
    {
      "id": "dots-studio/dots-3-note-preview",
      "name": "Dots3-Note Preview",
      "contextWindow": 512000,
      "maxTokens": null
    },
    {
      "id": "hal-x/thx-01",
      "name": "THX-01",
      "contextWindow": 1000,
      "maxTokens": null
    },
    {
      "id": "liquid/lfm-2.5-2.6b",
      "name": "LFM 2.5 2.6B",
      "contextWindow": 66000,
      "maxTokens": null
    },
    {
      "id": "meta/muse-glimmer-30b",
      "name": "Muse Glimmer 30B",
      "contextWindow": 131000,
      "maxTokens": null
    },
    {
      "id": "minimax/minimax-m3.1-flash",
      "name": "MiniMax M3.1 Flash",
      "contextWindow": 1000000,
      "maxTokens": null
    },
    {
      "id": "nvidia/nemotron-3-embed-1b",
      "name": "Nemotron 3 Embed 1B",
      "contextWindow": 33000,
      "maxTokens": null
    },
    {
      "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
      "name": "Nemotron-3 Nano Omni 30B-A3B (Reasoning)",
      "contextWindow": 256000,
      "maxTokens": null
    },
    {
      "id": "nvidia/nemotron-3-ultra-550b-a55b",
      "name": "Nemotron 3 Ultra 550B",
      "contextWindow": 1000000,
      "maxTokens": null
    },
    {
      "id": "nvidia/nemotron-3.5-bolt-e4b",
      "name": "Nemotron 3.5 Bolt E4B",
      "contextWindow": 66000,
      "maxTokens": null
    },
    {
      "id": "nvidia/nemotron-3.5-content-safety",
      "name": "Nemotron 3.5 Content Safety",
      "contextWindow": 128000,
      "maxTokens": null
    },
    {
      "id": "nvidia/nemotron-3.5-embed-1b",
      "name": "Nemotron 3.5 Embed 1B",
      "contextWindow": 33000,
      "maxTokens": null
    },
    {
      "id": "nvidia/nemotron-3.5-embed-8b",
      "name": "Nemotron 3.5 Embed 8B",
      "contextWindow": 33000,
      "maxTokens": null
    },
    {
      "id": "nvidia/nemotron-3.5-lightning-30b-a3b",
      "name": "Nemotron 3.5 Lightning 30B A3B",
      "contextWindow": 1000000,
      "maxTokens": null
    },
    {
      "id": "nvidia/nemotron-3.5-super-vl-120b-a12b",
      "name": "Nemotron 3.5 Super VL 120B A12B",
      "contextWindow": 1000000,
      "maxTokens": null
    },
    {
      "id": "nvidia/nemotron-parse-2.0",
      "name": "Nemotron Parse 2.0",
      "contextWindow": 8000,
      "maxTokens": null
    },
    {
      "id": "nvidia/riva-translate-4b-instruct-v2",
      "name": "Riva Translate 4B Instruct v2",
      "contextWindow": 4000,
      "maxTokens": null
    },
    {
      "id": "openai/gpt-oss-20b",
      "name": "GPT-OSS 20B",
      "contextWindow": 131000,
      "maxTokens": null
    },
    {
      "id": "poolside/laguna-s-2.1",
      "name": "Laguna S 2.1",
      "contextWindow": 262000,
      "maxTokens": null
    },
    {
      "id": "poolside/laguna-xs-2.1",
      "name": "Laguna XS 2.1",
      "contextWindow": 262000,
      "maxTokens": null
    },
    {
      "id": "qwen/qwen3-8b",
      "name": "Qwen3-8B",
      "contextWindow": 128000,
      "maxTokens": null
    },
    {
      "id": "recursive/flint-v1.0",
      "name": "Flint",
      "contextWindow": 262000,
      "maxTokens": null
    },
    {
      "id": "reflection/beam-1.0",
      "name": "Beam 1.0",
      "contextWindow": 262000,
      "maxTokens": null
    },
    {
      "id": "scira/amos-1-large",
      "name": "Amos 1 Large",
      "contextWindow": 131000,
      "maxTokens": null
    },
    {
      "id": "scira/amos-1-mini",
      "name": "Amos 1 Mini",
      "contextWindow": 9000,
      "maxTokens": null
    },
    {
      "id": "scira/amos-1-small",
      "name": "Amos 1 Small",
      "contextWindow": 262000,
      "maxTokens": null
    },
    {
      "id": "stealth/glyph-cluster",
      "name": "Glyph Cluster",
      "contextWindow": 256000,
      "maxTokens": null
    },
    {
      "id": "xingchen-agi/xing4.0-29b-a4b",
      "name": "Xing4.0 29B A4B",
      "contextWindow": 262000,
      "maxTokens": null
    }
  ]
}
```

Requires `ANYROUTER_API_KEY` env var.

## OpenCode provider

Run a model directly:
```
opencode run -m opencode/big-pickle "Review this project for bugs"
```

| Model name | Full OpenCode model ID |
|------------|------------------------|
| Big Pickle | `opencode/big-pickle` |
| Beam Free | `opencode/beam-free` |
| DeepSeek V4.1 Flash Free | `opencode/deepseek-v4.1-flash-free` |
| GLM 5.3 Flash Free | `opencode/glm-5.3-flash-free` |
| Flint 40B Free | `opencode/flint-40b-free` |
| MiMo V2.6 Flash Free | `opencode/mimo-v2.6-flash-free` |
| Nemotron 3.5 Lightning Free | `opencode/nemotron-3.5-lightning-free` |
| Nemotron 3.5 Super VL Free | `opencode/nemotron-3.5-super-vl-free` |

## OpenRouter provider — OPENROUTER_API_KEY

```json
"openrouter": {
  "package": "@opencode/ai/providers/openrouter",
  "models": {
    "openrouter/free": {
      "name": "OpenRouter Free Router",
      "modelID": "openrouter/free"
    },
    "nvidia/nemotron-3-ultra:free": {
      "name": "NVIDIA Nemotron 3 Ultra (free)",
      "modelID": "nvidia/nemotron-3-ultra:free",
      "limit": { "context": 1000000 }
    },
    "nvidia/nemotron-3.5-super-vl:free": {
      "name": "NVIDIA Nemotron 3.5 Super VL (free)",
      "modelID": "nvidia/nemotron-3.5-super-vl:free",
      "limit": { "context": 1000000 }
    },
    "nvidia/nemotron-3.5-lightning:free": {
      "name": "NVIDIA Nemotron 3.5 Lightning (free)",
      "modelID": "nvidia/nemotron-3.5-lightning:free",
      "limit": { "context": 1000000 }
    },
    "poolside/laguna-s-2.1:free": {
      "name": "Poolside Laguna S 2.1 (free)",
      "modelID": "poolside/laguna-s-2.1:free",
      "limit": { "context": 262000 }
    },
    "dots-studio/dots-3-note-preview:free": {
      "name": "Dots Studio Dots3-Note Preview (free)",
      "modelID": "dots-studio/dots-3-note-preview:free",
      "limit": { "context": 512000 }
    },
    "thinkingmachines/inkling:free": {
      "name": "Thinking Machines Inkling (free)",
      "modelID": "thinkingmachines/inkling:free",
      "limit": { "context": 1050000 }
    },
    "thinkingmachines/inkling-small:free": {
      "name": "Thinking Machines Inkling Small (free)",
      "modelID": "thinkingmachines/inkling-small:free",
      "limit": { "context": 1050000 }
    },
    "recursive/flint:free": {
      "name": "Recursive Flint (free)",
      "modelID": "recursive/flint:free",
      "limit": { "context": 262000 }
    },
    "cohere/north-mini-code:free": {
      "name": "Cohere North Mini Code (free)",
      "modelID": "cohere/north-mini-code:free",
      "limit": { "context": 256000, "output": 64000 }
    },
    "poolside/laguna-xs-2.1:free": {
      "name": "Poolside Laguna XS 2.1 (free)",
      "modelID": "poolside/laguna-xs-2.1:free",
      "limit": { "context": 262000, "output": 32000 }
    },
    "xingchen-agi/xing4.0-29b-a4b:free": {
      "name": "XingChen Xing4.0 29B A4B (free)",
      "modelID": "xingchen-agi/xing4.0-29b-a4b:free",
      "limit": { "context": 262000 }
    },
    "nvidia/nemotron-3-nano-omni:free": {
      "name": "NVIDIA Nemotron 3 Nano Omni (free)",
      "modelID": "nvidia/nemotron-3-nano-omni:free",
      "limit": { "context": 300000 }
    },
    "liquid/lfm2.5-2.6b:free": {
      "name": "LiquidAI LFM2.5-2.6B (free)",
      "modelID": "liquid/lfm2.5-2.6b:free",
      "limit": { "context": 66000 }
    },
    "nvidia/llama-nemotron-rerank-vl-1b-v2:free": {
      "name": "NVIDIA Llama Nemotron Rerank VL 1B V2 (free)",
      "modelID": "nvidia/llama-nemotron-rerank-vl-1b-v2:free"
    },
    "nvidia/nemotron-3.5-content-safety:free": {
      "name": "NVIDIA Nemotron 3.5 Content Safety (free)",
      "modelID": "nvidia/nemotron-3.5-content-safety:free",
      "limit": { "context": 128000 }
    }
  }
}
```

Requires `OPENROUTER_API_KEY` env var.

## Note

Kenari rate limit is account-wide (50 req/day), so prefer the single
nemotron-3-ultra model there. Hermes (Nous) free models are not account-limited
in the same way; see agents.toml for which profiles use them.
