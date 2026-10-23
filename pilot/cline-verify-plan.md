# Plan — verify the five cline models (when the rate limit resets)

**Why this exists:** the operator offered five free models (D-35); the
`cline-mimo` profile carries them as *offered*, never *verified*. The
operator notes their rate limit resets **2026-10-24**. Verifying them costs
live provider calls — an **authorisation action** (amendment §2) — so this
file is the plan, and the run waits for the operator's go-ahead.

## The only cline command ever run (the record, corrected)

One, on 2026-10-22, against the **old dead model** — raw capture
`pilot/spikes/s1-live-results.json`:

```
node C:\Users\Tiwa Pene\AppData\Roaming\npm\node_modules\cline\bin\cline \
  --provider cline --model cline-free/mimo-v2.6-flash "print the word ok and exit"
```

Result: `MODEL_GONE` — *"Free model promotion ended."* No cline session was
ever obtained, so resume was never attempted. **The five new models have
never been called, through the client or any other way** — the operator's
correction stands, and `agents.toml` says so.

## Terms to confirm with the operator (the D-24 shape)

1. Throwaway repository per model (not the pilot tree).
2. Fixed prompt — proposed: `"print the word ok and exit"` (the S-A1 prompt).
3. One request per model; **no failure provoked** (the operator's standing
   terms from D-24).
4. Record for each: exit code, latency, stdout/stderr, and the exact argv.
5. A model that fails is a fixture, not a retry — no second request.

## The proposed command (headless, via the profile's measured argv)

Per `agents.toml` `cline-mimo.argv_new` template
(`cline --provider cline --model <model> {prompt}`), resolved through
`plat.resolve_executable` so the npm `.cmd` shim is peeled (the S-A1 way):

```powershell
# per model M in the five below, in a throwaway repo:
& (cli exe) --provider cline --model M "print the word ok and exit"
```

Models (from `agents.toml` `cline-mimo.models`, primary first):

1. `cline-free/minimax-m3.1-flash`  (primary)
2. `cline-free/solar-mini4`
3. `cline-free/nemotron-3.5-super-vl`
4. `nvidia/nemotron-3.5-lightning-free`
5. `poolside/laguna-s-2.1:free`

Note the operator's constraint: **these models are only available through
the Cline client directly** — so the verification *is* the Cline CLI call,
and no gateway/passthrough path may be substituted for it (that substitution
would test the wrong thing).

## What a pass changes

The first working string becomes the `cline-mimo` primary model and the L1
swap target; failures are recorded as `MODEL_GONE`/`QUOTA` fixtures with the
raw text, and the profile keeps `family = "unknown"` (D-L12) until the
operator declares a family. The change to `agents.toml` afterwards is the
operator's edit (human-edited file, D-P3; not class K, D-28).
