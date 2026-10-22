# Caliber spikes S1–S5 (CIP section 10)

**Date:** 2026-10-22 · **Caliber version:** 1.55.2 (`@rely-ai/caliber`,
pinned with `npm install -g @rely-ai/caliber@1.55.2`) · **Node:** v26.7.0
(package requires `>=20`)

The raw `--help` output for every command is in `pilot/spikes/caliber-help/`.

---

## S1 — the command inventory, and can it use an OpenAI-compatible URL?

**Verdict: `works`.**

### The commands exist, and there are more than CIP §2.2 predicted

CIP §2.2 listed `bootstrap`, `init`, `refresh`, `hooks --install`,
`learn install` / `learn remove`, and a read-only score audit.  All of
those exist.  The actual command list is larger:

| Command | Purpose | CIP knew about it? |
|---|---|---|
| `init` | Initialize the project | yes |
| `bootstrap` | Install the agent skills | yes |
| `refresh` | Update docs based on recent code changes | yes |
| `score` | Score the config — **deterministic, no network** | "command name unconfirmed" |
| `hooks` | Manage auto-refresh hooks | yes |
| `learn` | Session learning | yes |
| `config` | **Configure LLM provider, API key and model** | no |
| `regen` / `regenerate` | Re-analyse the project and regenerate config | no |
| `sync` | Mirror skills, rules and plugins across agents — **deterministic, no LLM** | no |
| `status` | Show the current Caliber config status | no |
| `undo` | Revert all config changes made by Caliber | no |
| `uninstall` | Remove all Caliber resources from the project | no |
| `skills`, `plugin`, `compact`, `insights`, `sources`, `publish` | skills / plugins / Jev compaction / insights / external sources / a machine-readable summary | no |

Two of these matter a lot to the pilot:

* **`score` is deterministic and takes no network**, and it has
  `--json`, `--quiet` and `--compare <ref>`.  That is exactly what the
  policy's *score non-regression* gate needs, with no LLM in the loop.
* **`undo`** exists, which is a second route to a revert besides the
  Kernel's own snapshot-based revert.

### Corrections to CIP's guesses

| CIP said | Actually |
|---|---|
| `caliber init --agent claude-code` | `--agent <type>`, comma-separated: `claude, cursor, codex, opencode, github-copilot`. **There is no `claude-code`.** |
| "a read-only scoring audit exists; command name unconfirmed" | **`caliber score`**, confirmed, and deterministic |
| "hooks --install and learn install" | both confirmed; `learn install` writes to **`.claude/settings.json`**, not to git hooks |
| `caliber config --show` (used by Caliber's own skill text) | **does not exist in 1.55.2** — `error: unknown option '--show'`. Caliber's shipped skill prompt is out of date. `caliber status` is the read-only way. |

### The OpenAI-compatible base URL: **yes**

`src` of the installed package shows the configuration is read from the
environment when no config file is present:

```js
if (process.env.OPENAI_API_KEY) {
  return { provider: "openai",
           apiKey: process.env.OPENAI_API_KEY,
           model: process.env.CALIBER_MODEL || DEFAULT_MODELS.openai,
           baseUrl: process.env.OPENAI_BASE_URL };
}
```

So **Caliber can be pointed at any OpenAI-compatible endpoint**, which
includes the pilot's own QuotaGate gateway (QuotaGate v1.1 section 7).

**Two environment variables are needed, not one.**  `CALIBER_MODEL` sets
the generation model, but the *scan* model comes from `CALIBER_FAST_MODEL`
and defaults to `gpt-5.4-mini`.  Without it Caliber refuses to start:

```
Model "gpt-5.4-mini" is not available. Run `caliber config` to select a different model.
400 Model 'gpt-5.4-mini' is not available in the active live catalog for provider 'orcarouter'.
```

That is a **calibration defect in the pilot's plan**: the spec assumed one
model setting would do.  It does not.

### The endpoint used for the spike

The operator's own **OmniRoute** router, already running on
`127.0.0.1:20128`, is OpenAI-compatible:

* `GET /v1/models` → 401 (the endpoint exists, wants a token) and then
  **times out** — OmniRoute does not implement the model catalogue.
* `GET /api/health` → `{"status":"ok"}`
* `POST /v1/chat/completions` → **200**, served by `deepseek-v4-flash:free`.

Caliber needs a **live model catalogue** to validate against, and
OmniRoute's is not usable, so the model must be one Caliber accepts by
name.  `poor-claude` works; `deepseek/deepseek-v4-flash-free` and
`z-ai/glm-5.3-flash-free` returned **401 from the upstream provider**.

Settings used:

```
OPENAI_BASE_URL=http://127.0.0.1:20128/v1
OPENAI_API_KEY=<the operator's existing OMNIROUTE_API_KEY>
CALIBER_MODEL=poor-claude
CALIBER_FAST_MODEL=poor-claude
```

**No key was written to any file, and every invocation used
`--no-traces`** (Caliber's anonymous-telemetry switch).

### A note on the minimum prompt size

`MIN_PROMPT_TOKENS = 3e4`: every call sends **at least 30 000 input
tokens**.  On a free provider that is slow, and it is why the generation
step took minutes rather than seconds.  Worth knowing before the context
sync is scheduled.

---

## S4 — what do the hooks install, and where?

**Verdict: `works` — and the answer is the strongest confirmation of
CIP §2.4's hazard that this pilot has produced.**

Run in a **throwaway repository**, never in the pilot's.

`caliber hooks --install` reported:

```
✓ Claude Code SessionEnd enabled
✓ Git pre-commit enabled
✓ Claude Code SessionStart enabled
✓ Agent sync (SessionStart) enabled
✓ Agent sync (on edit) enabled
✓ Claude Code Notification enabled
✓ Claude Code learning hooks enabled
```

It creates:

| What | Where |
|---|---|
| a **git `pre-commit` hook** | `.git/hooks/pre-commit` |
| seven Claude Code hooks | `.claude/settings.json` (SessionEnd ×2, SessionStart ×2, PostToolUse ×2, Notification, PostToolUseFailure, UserPromptSubmit) |
| four shell scripts | `.claude/hooks/caliber-*.sh` |
| three agent skills | `.claude/skills/{setup-caliber,find-skills,save-learning}/SKILL.md` |
| Caliber's own state | `.caliber/score-history.jsonl`, `.caliber/cache/fingerprint.json` |

The `pre-commit` hook, verbatim:

```sh
"…/node.exe" "…/@rely-ai/caliber/dist/bin.js" refresh --quiet … || echo "caliber: refresh skipped"
"…/node.exe" "…/@rely-ai/caliber/dist/bin.js" learn finalize … || true
if [ "$(git config --get caliber.autostage 2>/dev/null)" != "false" ]; then
  git diff --name-only -- CLAUDE.md .claude/ .cursor/ AGENTS.md CALIBER_LEARNINGS.md \
    .github/ .agents/ .opencode/ 2>/dev/null | xargs git add 2>/dev/null || true
fi
```

### Why this is dangerous in the pilot, and what contains it

In a **worker worktree** this hook would, on every commit:

1. make an **LLM call** (`caliber refresh`) — spend that the Kernel's
   lease, budget and quota accounting never see;
2. run `caliber learn finalize` — more model work;
3. **auto-stage** `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.cursor/`,
   `.opencode/` and friends **into the worker's commit** — files outside
   the task's declared write scope, which the scope check would then flag
   as a violation, or worse, which would rewrite the class C files
   concurrently from several worktrees at once.

That is exactly CIP §2.4: *"A hook meant for the operator's checkout
would fire in every worker worktree and rewrite context files
concurrently."*  It is now **measured**, not assumed.

**The pilot already contains the mitigation.**  `src/fleet/spawn.py`
points every worktree's `core.hooksPath` at an empty directory
(`.pm/nohooks/`), so git never runs the hook at all.  The Fleet's
`disable_hooks` is therefore not a nicety — it is the control that keeps
Caliber's hooks out of the fleet.

**The safe placement rule (S4's answer):**

* `hooks --install` may run in the **operator's own checkout** only, and
  only with `git config caliber.autostage false`, so refreshed files are
  left unstaged for review.
* It must **never** be installed in a repository the Fleet manages work
  in, and the per-worktree `core.hooksPath` override is what enforces
  that.
* `learn install` writes to `.claude/settings.json`, which is a
  **per-user-agent** file rather than a shared git file, so it is less
  dangerous — but the `learn observe` / `learn finalize` hooks it installs
  still make model calls, so the same rule applies.

---

## S2, S3, S5 — the remaining spikes

`pilot/spikes/caliber_spike.py` runs them: the files written, whether
`refresh` preserves a human edit, and whether `refresh` is deterministic
enough for a stable `CONTEXT_SYNCED` hash.

The results are in `pilot/spikes/caliber-spike-results.json` and
`pilot/spikes/caliber-s2-init.txt`.

**Note on cost.**  The generation step sends at least 30 000 input tokens
per call through a free provider, so it takes minutes.  It was run
**once**, in a scratch copy, and the pilot's rule 20 (no quota hammering)
was respected: one run, no retries, no deliberate exhaustion.
