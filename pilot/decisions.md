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

## The gate rule (operator, 2026-10-22)

**The rule, as given:**

> G0–G2: proceed, log each crossing in `pilot/decisions.md` with evidence
> and mark it "self-crossed, pending review". G3: HOLD until I've
> spot-read `fleet/` spawn/kill code and ratified or reverted D-19.
> Class-K changes need two-key regardless of any earlier approval.
> G4/G5: hold.

**Standing posture** (the structural fix the pilot report asked for in §6):
**G0–G2 are self-crossed and pending review.  G3, G4 and G5 hold.  Class K
is always two-key.**

### Gate crossings

| Gate | Status | Evidence |
|---|---|---|
| **G0** — environment, platform decision | **self-crossed, pending review** | `pilot/spikes/s-p1-platform.md`; D-02; no `sudo` was needed or used; the environment checks are recorded in §3 of that spike |
| **G1** — Caliber go/fallback | **self-crossed in part, pending review** | `pilot/spikes/caliber-s1-s5.md` (S1–S5, all `works`); the baseline diff is the 10 sanitised class C files; the score moved 17/100 (F) → 87/100 (A).  The provider-terms element is now answered — D-23 |
| **G2** — live capture | **self-crossed in part, pending review** | the metadata capture (five `--help`s, five versions, the `.cmd`-shim measurement) is in `pilot/spikes/cli-matrix.md` and `pilot/spikes/caliber-help/`; the fixtures are in `tests/fleet/fixtures/`.  The **live provider-failure capture is deferred** to the operator's own decision — D-24 |
| **G3** — handover | **HELD** | the operator's spot-read is outstanding; the read list is `pilot/g3-spot-read.md` |
| **G4** — Caliber auto-sync | **HELD** | the policy stays `mode = "dry-run"` |
| **G5** — live capacity | **HELD** | no live capacity run has been made |

**G0 evidence, in short.**  Python 3.12.10, Git 2.55.0, Node 26.7.0,
`LongPathsEnabled=1`, WSL present but with `docker-desktop` as its default
distribution, `pwsh` absent.  The lock test and the npm-shim measurement
are in the spike record.  The platform decision is native Windows (D-02).

**G1 evidence, in short.**  Caliber 1.55.2 installed and pinned; S1 (it can
be pointed at an OpenAI-compatible endpoint, and it needs *two* environment
settings), S2 (which files it writes — the `managed_paths` list was wrong),
S3 (`refresh` preserves human edits), S4 (the hook hazard, measured), S5
(the instruction files are deterministic).  The baseline was installed
through the Kernel's own diff/lint/sanitise/merge machinery, and the lint
rejects Caliber's raw output — which is why the baseline is the *sanitised*
content.

**G2 evidence, in short.**  The metadata capture is complete.  What is
still `UNVERIFIED` is the *failure text* of the real CLIs, so **no
classifier pattern is loaded for any real adapter** and every non-zero exit
is `UNKNOWN`.  That is the safe state, and the operator's S-A1 approval
(D-24) is what will change it.

---

D-23 | 2026-10-22 | operator | **CIP Q1 is answered: the context-sync
lane uses OmniRoute, and the operator accepts the terms.**  QuotaGate's
provider allowlist is the *later* destination, not the current one.
| Leaving the lane disabled; using a local model only (Ollama is running
but has no model pulled). | Nothing for the terms.  But the repository's
content reaches third-party free providers, so the pilot's data-egress
exposure is real and is recorded here rather than buried.  **The
`context-sync` lane stays `providers_allow = []` and `mode = "dry-run"`
until G4**, so nothing egresses on its own.

D-24 | 2026-10-22 | operator | **Live S-A1 is approved, with terms:** a
throwaway repository per CLI, the prompt *"print the word ok and exit"*,
and three modes per CLI — new, resume (same model), resume (different
model).  If a profile is **already** rate-limited, send **one** request to
capture a QUOTA fixture; do not otherwise provoke failures. | Continuing
with metadata-only probing, which leaves every real adapter with
`headless = False`, `can_resume = False` and no classifier patterns at
all. | Nothing — the terms are the ones the pilot already follows (capture,
don't guess; never invent flags; never provoke a failure).

D-25 | 2026-10-22 | operator | **The pilot's supervision model is
ambiguous, and the operator will write a clarifying amendment.**  Pilot v1
rule 14 ("ask only when blocked, state your default") conflicts with §12.1
("the default on silence is hold").  The operator's gate rule resolves it
for this pilot: *G0–G2 proceed and are logged for later review; G3, G4 and
G5 hold; class K is always two-key.* | Leaving the contradiction in the
proposal. | Nothing — but the ambiguity is a defect in the proposal, and it
is now recorded in the pilot report as a finding rather than being quietly
worked around.

D-26 | 2026-10-23 | OpenCode (spike S-A1, live) | **The real adapters'
capabilities are now measured, and they are mostly positive.**  All five
CLIs run **headless**; hermes, kilo, pi and opencode **resume**; pi resumes
on a **different model**; hermes **prints its session id**.  The measured
values replace the all-`False` defaults in `src/fleet/adapters/generic.py`,
and the resume syntax and the interchangeable-model lists are now in
`agents.toml`. | Leaving the defaults, which would have kept the Fleet on
the console-window path, kept the L1 ladder step unreachable, and kept
every failure classified `UNKNOWN`. | **hermes, kilo and pi still have no
captured failure text**, so their failures remain `UNKNOWN` — no failure
was provoked, per the operator's terms and pilot v1 rule 20.  And the
model swap is available **only for pi**, because only pi has a second model
string known to be servable; the others need the operator's `prompts.json`
lists.

D-27 | 2026-10-23 | OpenCode | **A classifier pattern is only loaded if it
matches the capture it was derived from.**  The loader reads
`patterns.toml` beside the evidence and refuses a pattern whose source
file it does not match. | Loading a pattern from a hand-written list,
which is what the first implementation did. | Nothing.  This is the
mechanical form of fleet rule 15, and it means a classifier cannot grow
without evidence behind it.

D-28 | 2026-10-23 | OpenCode | **The operator's `cline-mimo` profile names
a model whose free promotion has ended** (measured: "The free promotion
for this model has ended and it is no longer available").  The profile is
left as it is, and the Fleet's `MODEL_GONE` handler disables it when it
sees that failure. | Disabling or repointing the profile by hand. |
Nothing — but repointing it is a **class K** change (the profile schema),
so it is the operator's call, and the profile's `models` list already
names three alternatives.

---

D-29 | 2026-10-23 | operator | **D-19 and D-20 are RATIFIED.**  The
operator was presented with both class K changes, their exact diffs and
their hashes in `pilot/class-k-ratification.md`, with the question "ratify
or revert"; the answer was "RATIFIED".  Both are now recorded in the
Kernel's own decision queue as class K items (Q-001, Q-002, both decided
`ratify`), so the ratification is an event in the hash-chained log rather
than only a note in this file. | Reverting both: `pmk context sync` would
have no command and `managed_paths` would name three files Caliber does not
write; the repository's agent instructions would lose their generated
context. | **A weakness in how the key was obtained, and it is recorded
rather than quietly fixed.**  The two changes were made on 2026-10-22 and
the queue items were raised on 2026-10-23 — *after* the changes were
already in the tree.  A two-key rule applied after the fact is an audit,
not a gate: it cannot prevent the change, only reverse it.  The rule is
satisfied in substance (the operator saw the diff, and could have reverted)
but not in timing, and timing is the part that makes a key a key.  The
correct sequence for the next class K change is: present the diff, take the
queue item, **then** make the change.

D-30 | 2026-10-23 | operator | **The ratification closes the class K half
of G3, and does not close G3.**  G3's remaining condition is the
end-to-end handover test: a real CLI driven through a real lease, with an
OpenCode session restarting from the briefing alone (H6).  That test hands
real work to a real agent, so it is itself an authorisation — it needs its
own go-ahead and is not covered by this ratification. | Treating "ratified"
as "G3 closed", which would let the end-to-end test slip in under a
decision that was only about two files. | Nothing.  The gate stays at
*ratification complete, handover test outstanding*.

D-31 | 2026-10-23 | OpenCode | **`pmk queue add` now exists.**  The human
decision queue is the Kernel's two-key mechanism (`queue_add(class_k=True)`
then `queue_decide`), but the CLI exposed only `list` and `decide` — so the
queue could be decided from the command line and never *populated* from it.
A two-key mechanism whose first key has no interface is a mechanism that
depends on someone writing Python. | Raising class K items by hand-editing
this file, which is not an event and has no hash chain. | Nothing.

D-32 | 2026-10-23 | OpenCode | **The decision queue issued duplicate
ids.**  `queue_add` numbered items by counting *open* ones, so deciding
Q-001 and then raising another question produced a **second Q-001**.  Found
while raising the amendment's ratification item — the first attempt at
that item was recorded as Q-001 and had to be voided.  Fixed: the id is now
derived from the highest existing id, and a duplicate raises
`duplicate_queue_id` instead of being written. | Leaving it: two different
class K questions sharing one id in the log that records their
ratification, which is ambiguous exactly where the record has to be
unambiguous. | Nothing.  The fix is covered by a regression test
(`test_queue_ids_do_not_collide_after_a_decision`).  **The duplicate Q-001
is voided in the queue, not deleted** — the event log is append-only, and
pretending an id was never issued would be the same kind of dishonest
tidying the pilot is trying to avoid.

D-33 | 2026-10-23 | OpenCode | **A duplicate queue id let one decision
overwrite another — including a class K ratification.**  Voiding the
duplicate Q-001 (D-32) rewrote the *original* Q-001's recorded choice from
`ratify` to `VOID` in the queue view, because the `QUEUE_DECIDED`
projection applied the choice to **every** item matching the id.  Found by
reading the queue list after the void, not by a test.  Fixed at both ends:
the projection now resolves exactly one item (the earliest still-open match,
then stops), and `queue_decide` refuses with `ambiguous_queue_id` when more
than one open item shares an id.  Replaying the log now restores Q-001 to
`ratify` and leaves the duplicate as `VOID`. | Leaving it: the queue — the
record of what the operator actually approved — could show a decision the
operator never made, and would do so silently. | **The authoritative record
was never actually lost**: the event log is append-only and `QUEUE_DECIDED
Q-001 ratify` is still at seq 31.  What was corrupted was the *view*.  That
distinction is the whole argument for an append-only log, and it is worth
stating plainly that the log held while the projection failed.

---

## Pending

- **G3's end-to-end handover test (H6).**  A real CLI, a real lease, an
  OpenCode session restarting from the briefing alone.  Needs its own
  go-ahead (D-30).
- **The `models` lists** for hermes, kilo, cline and opencode, so the
  ladder's L1 step is available for all of them and not only pi.
- **The `cline-mimo` profile** names a model whose free promotion has
  ended (D-28).  Repointing it is class K.
- **QuotaGate provider keys**, for M1's live capture.
- **G4/G5** — held.
- **The amendment draft** at `pilot/amendment-gates.md` — awaiting the
  operator's accept / edit / discard.

## Resolved since the last update

- **CIP Q1** — answered: OmniRoute, terms accepted (D-23).
- **Caliber install** — approved and done; the G1 baseline is installed.
- **Live S-A1** — approved with terms (D-24) and **run**; 13 requests, no
  failure provoked (D-26).
- **The gate rule** — given, and recorded as a standing posture above
  (D-25).
- **D-19 and D-20** — **ratified** (D-29), as class K queue items Q-001 and
  Q-002 in the event log.
