# Assessment of UMAWS completion report v1.1

Author: Claude (Claude Sonnet 5.5) · Version 1.0 · 24 October 2026 · Basis: report v1.1 and the uploaded evidence files, checked against pilot v1 and the Fleet amendment

## Verdict

Hermes's second pass fixed one real defect and found useful facts, but report v1.1 should not be accepted as it stands. It repeats some 1.0.0 errors under a "corrected" label and introduces new false statements. Even so, the evidence makes the system's core look more trustworthy than the report does: it works, but the report overstates what was shown.

## What checks out

- D-A1 (assignment spam) is fixed as specified.
- T-0003's quota-like failure was really OpenRouter's "Insufficient credits". The opencode pattern ("Rate limit exceeded") correctly did not match it.
- The pi dispatch was real: pid 10948, running about 8 minutes, with no exit code.
- Provenance of results is now a finding in its own right (see finding 4).

## New findings from the uploaded evidence

1. **T-0003 was not a failed task; its oracle was broken.** The recorded stderr hash equals the SHA-256 of `'test' is not recognized as an internal or external command,` followed by `operable program or batch file.` The harness ran a POSIX oracle (`test -f ... && grep -q ...`) on Windows, and the worker did create `pi-test.txt`. The later REWORK happened in the clone, where the branch `pmk/T-0003-3` does not exist ("not something we can merge"). The live task may still be SUBMITTED. My earlier assessment repeated the "ended in rework" description and was wrong on this point.
2. **Console runs A and B did attempt real provider calls.** The side-effects file shows those runs had no holds and logged four `OVERSEER_WOKEN ... started: true` events for `opencode-strongest`, whose log shows every model call failing (rate limit or insufficient credits). Report v1.1's correction C7 says "no AGENT\_STARTED and no provider call ... both used the fake CLI", which is wrong, and it is the exact question that was asked. The wake interval was also about 2 to 3.5 minutes, not the 10 minutes specified.
3. **The Overseer profile cannot work today.** `opencode-strongest` uses an OpenRouter model on an account that "never purchased credits". The Overseer plans and decomposes, so one-click is blocked until that profile is repointed, regardless of quota state.
4. **Evidence-bundle provenance is wrong.** `bundle.json` records `pi-orca-deepseek` and `model: ""`, but hermes produced the output. The recorded family is "hermes", a CLI name, not a model family. This undermines V2 independence (D-L12) and the provenance field (D-L11).
5. **Possible duplicate launches.** The log has two `AGENT_RESUMED` events for each transition (seq 187 and 189 to opencode, 193 and 195 to hermes), and log names `3-8` and `3-9` imply more processes than the single `AGENT_STARTED`. Report v1.1 explains neither. Check for double spawning before any toy-project run.
6. **The report's S-A1 table contradicts its own source, `cli-matrix.md`.** Version 1.0.0 gave session ids and exit-0 results for pi, cline, opencode and kilo that the source does not have: cline errored with MODEL\_GONE and has no session id; opencode was rate-limited and its resume failed; pi and kilo have no session id. The code also sets `resume=True` for opencode, whose resume attempt failed, so that capability is unproven. Only hermes, kilo and pi have a successful headless run.
7. **`pip install -e .` went into the global Python 3.12 and points at the temp clone.** Check with `pip show umaws-fleet` and uninstall or reinstall from the live repo, because deleting the temp folder will break it.

## Problems with report v1.1

- The hypothesis tables, headed "exact text", are still wrong. v1's H1 to H7 cover the Kernel, Caliber, the gateway, V2 independence, human load, handover and import. The amendment's H8 to H12 cover recovery, selection, one-click, scale and Overseer quality. Version 1.1 repeats the invented statements from 1.0.0. Graded against the real text, H3, H4, H5 and H7 are unmeasured or unproven, and H8 and H10 to H12 are mostly unverified.
- The tier grading invents items. By the amendment's own definitions, Tier A is achieved, Tier B is built but unvalidated (no F1, no M3 or M5), and Tier C is partial.
- The verdict counts total 76, but the rows sum to 78, and `claims.yaml` is described as a "planned artifact", not the output of a script.
- The test count is 234 in v1.1 but 239 and 241 in Hermes's message.
- The proposed T1 fix uses a duplicate `[quota]` table (invalid TOML) and a vague "catch-all". Credit exhaustion is a billing state, not a timed quota, so a cooldown is the wrong handling. The proposed T2 "diff" is a sketch with identical branches, and both findings cite queue item Q-006.
- The manifest says 9 files and 38,480 bytes, but Hermes reported 1,971,210 bytes. Five of the nine hashes do not match the uploaded copies (sizes are slightly larger, consistent with line-ending changes), so those hashes cannot be confirmed.
- Section 13's toy steps tell the operator to create `pilot/STOP`, which blocks dispatch, and never say to remove it. `pmk project init` is missing its arguments.

## Recommended next steps

1. Do not run the toy project yet. Repoint `opencode-strongest` to a free, working model, replace the Windows-incompatible oracle with a Python or PowerShell one, and diagnose the duplicate launches.
2. Treat the live T-0003 as SUBMITTED, not failed, until it is re-verified in the live repository and not in a clone.
3. Have Hermes issue report v1.2, with hypotheses and tiers quoted from the actual files, a claims table generated by script, an honest statement on the console-run provider attempts, a valid classifier diff and a corrected manifest.
