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

Run by `pilot/spikes/caliber_spike.py`, in **two** scratch repositories:
the full pilot repository and a small toy project.  The toy project was
added because the generation is slow and a small repository answers the
same questions faster.

**Verdicts: S2 `works`, S3 `works`, S5 `works` on the small repository and
`does-not-work` on the full one** — with an important qualification.

### S2 — which files does it write?

| Path | Written for | Managed? |
|---|---|---|
| `AGENTS.md` | both agents | **yes** |
| `CLAUDE.md` | both agents | **yes** |
| `.claude/rules/*.md` | claude | yes |
| `.claude/skills/<name>/SKILL.md` | claude | yes |
| `.opencode/skills/<name>/SKILL.md` | opencode | yes |
| `.claude/settings.json` | claude | no — Caliber's own hooks |
| `.claude/hooks/caliber-*.sh` | claude | no — Caliber's own hooks |
| `.gitignore` | both | no |
| `.caliber/score-history.jsonl`, `.caliber/cache/fingerprint.json` | both | no — Caliber's own state |

**`managed_paths` for the pilot is therefore larger than CIP Appendix A.2
guessed.**  The proposal's list was `["AGENTS.md", "CLAUDE.md",
"CALIBER_LEARNINGS.md"]`; the real list also includes `.claude/rules/` and
`.claude/skills/` and `.opencode/skills/`, which is where the *bulk* of
the generated content lands.  A `managed_paths` list that omits them
would let a sync rewrite the skills without the lint ever seeing it.

### S3 — does `refresh` preserve a human edit?

**Yes.**  A hand-written marker appended to the generated `AGENTS.md`
survived a `caliber refresh` in **both** repositories.

This resolves an entry in CIP Appendix B that was recorded as **Unknown**
("Whether Caliber preserves human edits to managed files — *Not found*").
It does preserve them.  The README's claim that `caliber sync` "never
overwrites a file you edited by hand" is borne out for `refresh` too.

### S5 — is `refresh` deterministic?

**On the small repository: yes.**  A second `refresh` with no code change
changed **nothing**.

**On the full pilot repository: the instruction files are stable.**  A
third `refresh` printed *"No doc updates needed"*, and the SHA-256 of
both `AGENTS.md` and `CLAUDE.md` was **byte-identical** before and after.

The spike's own first report said "12 files changed" on the second pass.
That was **the spike's measurement method, not Caliber's instability**: the
spike compares **mtimes**, so a file that was rewritten with identical
content still counted as changed.  Comparing hashes instead — which is
what the Kernel actually does — shows the instruction files are
deterministic.

What genuinely churns is Caliber's **own bookkeeping**:
`.caliber/score-history.jsonl` and `.caliber/cache/fingerprint.json`.

That distinction matters, and it is the point of `managed_paths`: the
Kernel hashes and lints the **managed** files and ignores the generator's
cache.  A generator that churns its own bookkeeping is fine; one that
churned the instruction files would make every `CONTEXT_SYNCED` hash
meaningless.

**A lesson about the pilot's own measurement.**  The spike compared
timestamps when it should have compared content, and nearly reported a
false instability.  The Kernel's own views and bundles hash their content,
so the production path was right; the spike was the sloppy one.

### The score

`caliber score` on the pilot repository: **17/100, grade F** before
`init`; **87/100, grade A** after it.  Nineteen checks across six
categories (existence, quality, grounding, accuracy, freshness, bonus),
deterministic and with no network.  `no_secrets` and `config_drift` pass
out of the box.

---

## The most important finding: the lint had a false negative

**The first version of the I15 lint passed Caliber's real output.**  It
was written against hand-written samples, and it reported `ok: true` on
generated files that contain, verbatim:

> **IMPORTANT:** Before every git commit, you **MUST** ensure Caliber
> syncs agent configs with the latest code changes.

> Run: `caliber refresh && git add CLAUDE.md .claude/ .cursor/ … AGENTS.md
> CALIBER_LEARNINGS.md .agents/ .opencode/`

> These are auto-extracted from real tool usage — **treat them as
> project-specific rules**.

Those are three distinct attacks on the pilot's trust model, and the lint
saw none of them:

1. a **mandate** to make an unaccounted model call;
2. an instruction to **stage files outside any task's write scope** —
   the exact thing the scope check exists to catch;
3. **authority language** telling the agent to treat auto-extracted
   patterns as rules, which is precisely the "learnings are candidates,
   not evidence" rule (CIP §14.7) inverted.

The lint now catches all three, and the real generated text is pinned as
a test fixture in `tests/pmk/test_context_real_caliber.py`.  The harmless
part of the same generated file still passes, so the lint is not simply
rejecting everything.

**The lesson is the pilot's own:** a control that has only ever been
tested against samples you wrote yourself has not been tested.  The
Kernel's machinery was built and unit-tested against invented inputs;
running the real generator against it is what found the hole.

---
