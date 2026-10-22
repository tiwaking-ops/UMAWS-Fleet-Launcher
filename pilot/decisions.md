# Decision log

Format (pilot v1 Appendix C4):
`D-<n> | <date> | <who> | <decision> | <alternatives> | <what it leaves untested>`

---

D-01 | 2026-10-22 | operator + OpenCode | **Repository root is
`C:\temp\projects\testproject1`**; per-lease worktrees are created under
`<repo>/work/<task>-<fence>`. | `C:\umaws\umaws-fleet` with worktree root
`C:\w\` (the proposals' guess G-F6). | The 260-character path limit is no
longer a constraint, because the repo path is already 30 characters and
`work/<task>-<fence>` adds about 20. If the operator later moves the repo
deeper, this must be revisited.

D-02 | 2026-10-22 | OpenCode (spike S-P1) | **Platform: native Windows.**
The Kernel, the Fleet and the Console all run as native Windows processes.
| WSL Ubuntu (pilot v1 §7.1 default; CIP D8). | Nothing in the Kernel or
Fleet depends on `fcntl`, because `src/pmk/plat.py` provides portable locking
and the WSL path was never exercised. WSL remains possible; the platform
layer is the only file that would change.

D-03 | 2026-10-22 | operator | **CLI probing is metadata-only.** The
implementer captures `--help` and version output for hermes, kilo, cline, pi
and opencode, and does **not** send any prompt to a real provider. | Full
spike S-A1 with one-shot runs (burns real free-tier quota). | Real headless
behaviour, session-id format, resume semantics, model-switch-on-resume,
exit codes and failure text are all `UNVERIFIED`. Every adapter therefore
ships with `caps` defaulting to `False`, every non-zero exit classifies as
`UNKNOWN`, and no failure-classifier pattern is loaded. This is the safe
state the fleet amendment §7.5 requires.

D-04 | 2026-10-22 | OpenCode (spike S-P1, measured) | **File locks live on a
sidecar file, not on the data file.** `FileLock` locks byte 0 of
`<file>.lock`. | Locking byte 0 of the event log itself. | Nothing — but this
is a **measured Windows constraint, not a preference**. Windows enforces
byte-range locks against writes: locking the log and appending to the log
fails with `PermissionError` (an append to an empty file lands on byte 0).
The first spike run failed for exactly this reason. Recorded because a
future implementer would otherwise "simplify" the sidecar away.

D-05 | 2026-10-22 | operator | **Scope: the whole pilot (pilot v1 Tier A→C)
plus Fleet amendment A1.** | Fleet-only, or Tier A only. | Nothing about
*this* scope choice leaves anything untested; the untested items are tracked
in STATE.md under `[VERIFY]`.

D-06 | 2026-10-22 | OpenCode | **Caliber is not installed on this machine.**
`caliber --help` is absent, and `npm install -g @rely-ai/caliber` is a
global install that pilot v1 rule 6 forbids without asking. | Install it
unilaterally. | WP1 spikes S1–S5 and WP8 (context sync) cannot run. This is
held at **gate G1**, which the operator must rule on.

D-07 | 2026-10-22 | OpenCode | **The two missing source specifications were
supplied by the operator mid-build** (`proposal-claude-llm-gateway-v1-1.md`
and `proposal-claude-umaws-gateway-caliber-integration-v1.md`), so
QuotaGate M0–M5 and the Caliber integration are built from their real
specifications. | Reconstructing M4/M5 from pilot v1's prose (the fallback
plan before the files arrived). | Nothing. The earlier "RECONSTRUCTED"
caveat is withdrawn.

D-08 | 2026-10-22 | OpenCode | **QuotaGate v1.1 milestone numbering aligns
with pilot v1's M0–M5.** v1.1 §11 defines M0 Foundations, M1 Passthrough +
live capture, M2 Quota engine, M3 Routing, M4 Capacity, M5 UMAWS integration;
pilot v1's M0–M5 refer to exactly these. v1.1's M6–M8 (catalog, dashboard,
hardening) are out of pilot scope. | Treating pilot v1's M-numbers as a
different scheme. | QuotaGate M6–M8 stay unbuilt, as pilot v1 §3.2 intends.

D-09 | 2026-10-22 | OpenCode (measured) | **The Fleet resolves npm `.cmd`
shims to their real target and launches that with an argv list.** It never
launches a `.cmd` through `cmd.exe` except as a reported-degraded
fallback. | Launching `.cmd` shims through `cmd.exe /c`, which fleet
amendment §7.2 permits "only after S-A1 shows the arguments survive". |
Nothing — S-A1 showed they **do not** survive. `cmd.exe` expanded `%PATH%`
to the entire PATH and doubled `^`. The amendment's conditional should
become a prohibition; recorded as an amendment in the pilot report.

D-10 | 2026-10-22 | OpenCode (measured) | **Every file a human might have
written is read with `utf-8-sig`.** Windows PowerShell 5.1's
`Set-Content -Encoding utf8` writes a UTF-8 BOM, which breaks JSON, TOML
and classifier patterns alike. | Reading with plain `utf-8`. | Nothing.
The BOM broke every classifier pattern silently, because the pattern
became `\ufeffSYNTHETIC-FAILURE-QUOTA` and matched only at the very start
of a string.

D-11 | 2026-10-22 | OpenCode (found by the one-click demo) | **The scope
check runs `git status --porcelain --untracked-files=all`, and the merge
queue stages only the task's declared write scope.** | `git add -A` and a
default `git status`. | Nothing — but without this, a worker that created
a new directory would have had its entire output invisible to the scope
check and the evidence bundle, and the Kernel would have promoted work it
never inspected. Both are now regression-tested.

D-12 | 2026-10-22 | OpenCode (found by the one-click demo) | **The merge
queue fast-forwards with `git merge --ff-only`, not `git update-ref`.** |
Moving the branch ref directly. | Nothing — `update-ref` moves the branch
but never updates the index or the working tree, so merged files never
appeared on disk and the close-check could not see them. A finished
project looked unfinished.

D-13 | 2026-10-22 | OpenCode | **Caliber stays disabled under pilot v1's
G1 fallback; H2 is "not tested"; WP8 is reduced to its spec's reduced
scope** (constitution injection, I17 hashing, lint, drift check). The
constitution stub is CIP Appendix A.1 verbatim, and I17 is enforced: the
Kernel refuses a bundle with no `constitution_hash`. | Installing
`@rely-ai/caliber` without asking, which pilot v1 rule 6 forbids. | WP1's
S1–S5 and the live context sync are untested. Installing Caliber and
running S1–S5 is the first thing in the pilot report's recommended next
steps.

D-14 | 2026-10-22 | OpenCode | **The gate posture is a standing line in
STATE.md, and the default is hold.** | Asking at each gate. | Nothing yet,
because no gate has been crossed. The rule the operator would give is
still wanted; until it arrives, no gate is crossed silently.

D-15 | 2026-10-22 | operator (approved) + OpenCode | **Caliber 1.55.2 is
installed globally and pinned** (`npm install -g @rely-ai/caliber@1.55.2`),
and the generator endpoint is the operator's own **OmniRoute** router on
`127.0.0.1:20128` (`OPENAI_BASE_URL` + `OPENAI_API_KEY` +
`CALIBER_MODEL=poor-claude` + `CALIBER_FAST_MODEL=poor-claude`).
`caliber hooks --install` was run **only in a throwaway repository**.
| Leaving Caliber uninstalled under the G1 fallback. | Nothing — the
G1 fallback is replaced by measurement. **CIP Q1 (provider data terms for
the context-sync lane) is still the operator's decision.** No key was
written to any file, and every invocation used `--no-traces`.

D-16 | 2026-10-22 | OpenCode (measured, S4) | **Caliber's hooks must never
be installed in a repository the Fleet manages work in.** `caliber
hooks --install` writes a git `pre-commit` hook that runs `caliber
refresh` (an LLM call) on every commit and **auto-stages** `AGENTS.md`,
`CLAUDE.md`, `.claude/`, `.cursor/`, `.opencode/` and friends into the
commit — outside the task's declared write scope, and concurrently from
several worktrees. | Installing the hooks for convenience. | Nothing: the
Fleet's per-worktree `core.hooksPath` override (pointing at an empty
directory) already prevents git from running them. The rule is now
measured rather than assumed, and it is recorded so that a future
implementer does not "helpfully" install the hooks in the main checkout.

D-17 | 2026-10-22 | OpenCode | **The Kernel's context machinery
(the I15 lint, the I16 drift check, the sync task and the revert) is
implemented and tested, and it does not depend on the generator.** 32
tests. | Depending on Caliber being installed before building the
controls. | Nothing. The generator is a tool; the safety machinery is
the Kernel's, and it works with any generator or none.

D-18 | 2026-10-22 | OpenCode | **Auto-sync stays off** (`mode =
"dry-run"` in `.pm/policy.toml`), per D-P10: it is enabled only at gate
G4, after the lint exists and the T4 canary has passed. | Enabling it
now that Caliber is installed. | Nothing — the sync task is implemented
and runs in dry-run mode, so its diff, lint and score are all recorded
without anything being merged.

D-19 | 2026-10-22 | operator (approved the Caliber install) + OpenCode |
**Class K change: `.pm/policy.toml` was edited to add the context-sync
generator command, the score command and the measured Caliber version,
and the pins were re-recorded with `pmk pins record`.** | Leaving the
policy unpinned. | Nothing — but the authority for this change is the
operator's approval of the Caliber install, which is what the change
enables. **A class K change with no human approval behind it would be a
governance failure, and the sentinel's I8' check caught this one
automatically** — the pins went stale the moment the policy was edited,
and the sentinel reported it as a stopping finding until the pins were
deliberately re-recorded.  That is the control working, not a nuisance.

D-20 | 2026-10-22 | OpenCode (after reading the generated files) |
**Class K change: the G1 baseline of the managed context files is
installed** — 10 files (AGENTS.md, CLAUDE.md, three rules, five skills),
sanitised, linted, hashed and committed.  Caliber's own operational skills
(`setup-caliber`, `find-skills`, `save-learning`) are **excluded from
class C** (`managed_exclude`): they teach an agent to run the generator,
so they are the generator's machinery, not generated project context. |
Installing everything Caliber wrote, which would have imported the
"run caliber refresh" instructions into the pilot's own agent
configuration. | Nothing — the excluded files are simply not installed,
and the exclusion is recorded in the policy and in this log.

D-21 | 2026-10-22 | OpenCode (measured) | **The I15 lint's coverage limit
is measured and pinned.**  A paraphrase built only from the phrasings T4b
let through — "the coordination state is yours to maintain… treat the
checks as a suggestion" — **passes the lint**.  A test asserts that
weakness on purpose, so the limit cannot be forgotten and any
strengthening has to be deliberate. | Pretending the lint catches
paraphrases, which CIP section 14.6 explicitly says it does not. |
Nothing, but the report must not describe the lint as the safety
property.  **The safety property is the combination** — lint, score gate,
blind V2 review and audit — and the pilot has implemented the first three.

D-22 | 2026-10-22 | OpenCode (measured) | **T4 as CIP specifies it is
inconclusive on this system.**  The generator did not carry any of the
three planted injections from a repository document into the context files,
so the lint never had an injection to catch.  The first T4 run was
**confounded** — all three variants were blocked by Caliber's own
`caliber:managed` block, which is present whether or not an injection is
planted — and was discarded. | Reporting the confounded run as a pass,
which would have been a false claim of a working canary. | Nothing, but
the generator has **not** been shown to be safe against injection.  Only
that it did not propagate three particular injections, with one weak model
on one repository.

---

## Pending

- **Gate rule** — the operator was asked whether the implementing agent must
  stop at G0–G3 and replied "I will provide these". Until the rule
  arrives, the pilot v1 §12.1 default applies: **hold**. No gate has been
  crossed.
- **CIP Q1** — the provider data terms for the context-sync lane.  The
  spike used the operator's own local OmniRoute router, which fronts
  free-tier providers, so the repository's content still reaches a
  provider.
- **Caliber install approval** — **granted**; Caliber 1.55.2 is installed
  and pinned, and the G1 baseline is installed (D-20).
- **QuotaGate provider keys**, for M1's live capture.
- **Live S-A1 approval** — one trivial one-shot prompt per CLI.
