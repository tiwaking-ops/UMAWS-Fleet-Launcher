"""Repoint kilo-auto: kilo-auto/free as default, free models as the rotation."""

P = r"C:\temp\projects\testproject1\agents.toml"

OLD_ARGV = ('argv_new = ["kilo", "run", "{prompt}", "--dir", "{cwd}", "--auto"]')
NEW_ARGV = ('argv_new = ["kilo", "-m", "{model}", "run", "{prompt}", '
            '"--dir", "{cwd}", "--auto"]')
OLD_RESUME = ('argv_resume = ["kilo", "run", "{prompt}", "--dir", "{cwd}", '
              '"--auto", "--continue"]')
NEW_RESUME = ('argv_resume = ["kilo", "-m", "{model}", "run", "{prompt}", '
              '"--dir", "{cwd}", "--auto", "--continue"]')

OLD_MODELS = "models = []"

# Default first, then the optional extras.  Verified live with `kilo models`
# on 2026-10-23 and against kilo.ai/landing/free-models.
NEW_MODELS = '''model = "kilo/kilo-auto/free"
# Kilo Gateway is MODEL-limited, not account-limited (operator, 2026-10-23).
# kilo-auto/free picks a free model from the request type, which makes it the
# right default: the gateway does the choosing, and a per-model ceiling binds
# rather than the whole account stopping.
#
# The rest are the free models, callable directly.  In this profile they are
# the L1 swap targets of the recovery ladder and the optional extra agents:
# when one model is exhausted, the ladder moves to the next rather than
# cooling the whole profile.
#
# kilo/openrouter/free is deliberately NOT in this list.  OpenRouter is
# ACCOUNT-limited (same operator), so rotating models buys nothing and merely
# spends the shared ceiling faster.  One model, used well.
models = [
  "kilo/kilo-auto/free",
  "kilo/nvidia/nemotron-3.5-super-vl:free",
  "kilo/poolside/laguna-s-2.1:free",
  "kilo/poolside/laguna-xs-2.1:free",
  "kilo/nvidia/nemotron-3-super-120b-a12b:free",
  "kilo/nvidia/nemotron-3-ultra-550b-a55b:free",
  "kilo/cohere/north-mini-code:free",
  "kilo/dots-studio/dots-3-note-preview:free",
  "kilo/reflection/beam-free",
  "kilo/nvidia/nemotron-3.5-lightning:free",
  "kilo/recursive/flint-v1.0:free",
  "kilo/xingchen-agi/xing4.0-29b-a4b:free",
  "kilo/liquid/lfm-2.5-2.6b:free",
  "kilo/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
]'''

t = open(P, encoding="utf-8").read()

# Scope every edit to kilo-auto's block: `models = []` also appears in
# hermes, opencode-strongest and opencode-fallback, and a global replace
# would silently repoint profiles the operator never asked about.
start = t.index('id = "kilo-auto"')
end = t.index("[[profile]]", start)
block = t[start:end]
for old, new in ((OLD_ARGV, NEW_ARGV), (OLD_RESUME, NEW_RESUME),
                 (OLD_MODELS, NEW_MODELS)):
    assert block.count(old) == 1, \
        f"expected one {old[:40]!r} in kilo-auto, found {block.count(old)}"
    block = block.replace(old, new)
t = t[:start] + block + t[end:]

open(P, "w", encoding="utf-8", newline="\n").write(t)
print("kilo-auto repointed: default kilo/kilo-auto/free, 13 extra free models")
