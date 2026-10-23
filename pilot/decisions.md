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

## The gate rule (operator, 2026-10-22; amended in force 2026-10-23)

**The rule, as given:**

> G0–G2: proceed, log each crossing in `pilot/decisions.md` with evidence.
> G3: HOLD until I've spot-read `fleet/` spawn/kill code and ratified or
> reverted D-19.  Class-K changes need two-key regardless of any earlier
> approval.  G4/G5: hold.

**Amended in force** — `pilot/amendment-gates.md` v2, approved as class K
queue item **Q-003**, recorded at **D-34**.  The amendment's central change:
**classification is by action, not by gate number.**  A gate number names a
point in the plan; it does not decide whether the action there needs the
human.

An action is an **authorisation** — it needs a named decision, and silence
is not consent — if it:

* makes a live call to a provider, or spends a provider's quota;
* sends repository content to a third party, including a router that fronts
  one;
* hands work to a real agent, in a real repository;
* turns on a mechanism that can write instructions an agent will follow;
* makes a decision with lasting consequence that reverting a commit cannot
  undo — including the platform decision.

Otherwise it is a **checkpoint**: logged with its pass criteria written
**before** the check ran, and reversible by reverting a commit or deleting
scratch files.  An action that fails either of those tests is an
authorisation.  Ambiguity resolves to **authorisation**, never to proceed.
And **a gate is crossed once per mechanism**, not once per task or dispatch
— while an approval covers the mechanism it named and no other.

**"Self-crossed" is retired.**  A crossing is either *authorised by* a named
decision, or *logged as a checkpoint* against pre-written criteria.  There
is no third state.

### Gate crossings, classified by action

| Point | Action | Kind | Named consequence | Authority / criteria |
|---|---|---|---|---|
| **G0** | The platform decision (native Windows, no WSL/Docker) | **authorisation** | the system is built on Windows-native assumptions for its lifetime | **the operator's instruction**; D-02 |
| **G0** | Environment metadata (versions, paths, lock test, shim measurement) | checkpoint | — | logged; `pilot/spikes/s-p1-platform.md` |
| **G1** | Measuring Caliber's behaviour (S1–S5) | checkpoint | — | logged; `pilot/spikes/caliber-s1-s5.md` |
| **G1** | Installing Caliber | **authorisation** | a third-party generator runs in this repository | **operator approved the install** — D-15…D-19 |
| **G1** | The sync sending repository content to providers | **authorisation** | the repository's content reaches third-party free providers | **the operator accepted the terms** — OmniRoute, D-23 |
| **G2** | Metadata capture (five `--help`s, five versions, shim measurement) | checkpoint | — | logged; `pilot/spikes/cli-matrix.md`, `pilot/spikes/s1-live-help/` |
| **G2** | **Live S-A1 provider calls** | **authorisation** | real requests to real providers, consuming their quota | **the operator approved it with terms** — D-24 |
| **G3** | A real CLI through a real lease; an OpenCode session restarting from the briefing alone | **authorisation** | real agents take real work in a real repository | ratification of D-19/D-20 done (D-29); **the handover test itself is outstanding and needs its own go-ahead** (D-30) |
| **G4** | Turning Caliber auto-sync on | **authorisation** | the generator writes instructions agents will follow, on every commit | **HELD** — `mode = "dry-run"` |
| **G5** | Live capacity run | **authorisation** | spend, and sustained load on real providers | **HELD** |

**A known weakness, recorded.**  The G0–G2 *checkpoints* were logged before
this rule existed, so their pass criteria were implied by each spike's
question rather than written down as pass/fail beforehand.  Under the
amendment they are **checkpoints with a known weakness**, not clean ones.
No outcome changes — the consequential actions at G0–G2 were authorised by
name, so nothing irreversible rested on those checkpoints — but a future
checkpoint must state its criteria before it runs.


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
Nothing irreversible.  **Correction, same day:** this entry first called
repointing a **class K** change, "because it touches the profile schema".
That was wrong.  Only `.pm/constitution.md` and `.pm/policy.toml` are
pinned, so `agents.toml` is **not** class K by artefact; under the amendment
in force (D-34) repointing is an **authorisation** action — it selects a
different model, provider terms and quota — which needs the operator's
approval but not a class K second key.  Also noted: all three models on the
profile are `cline-free/*`, and the operator reports that free models were
removed platform-wide this week, so the "three alternatives" this entry
relied on may themselves be unavailable; the operator is reviewing which
remain.

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

D-34 | 2026-10-23 | operator | **Amendment v2 is IN FORCE** (class K,
Q-003 approved).  The gate rule now classifies **by action, not by gate
number**: an action that makes a live provider call, sends repository
content to a third party, hands work to a real agent, turns on a mechanism
that can write instructions agents follow, or makes a decision a commit
cannot undo, is an **authorisation** and needs a named decision.  Everything
else is a **checkpoint**, logged against pass criteria written *before* the
check runs and reversible by reverting a commit or deleting scratch files.
Ambiguity resolves to authorisation.  A gate is crossed **once per
mechanism**, and an approval covers that mechanism and no other.
Consequences applied: "self-crossed" is retired from this record and from
`STATE.md`; each G0–G2 crossing now cites the decision that authorised it
(D-02, D-15…D-19, D-23, D-24) or is logged as a checkpoint; report §4.4 and
§8 adopt the text. | Leaving the v1 rule, which classified by gate number
and described the crossings as "self-crossed" — an inaccurate account of
what actually happened, and one that hid the fact that the operator had
authorised each consequential action. | **A weakness that the amendment
itself exposes.**  The G0–G2 checkpoints predate the rule, so their pass
criteria were not written before the checks ran.  They are recorded as
checkpoints with a known weakness.  No outcome changes — nothing
irreversible rested on them — but this is the first thing a future
checkpoint must get right.

D-35 | 2026-10-23 | operator | **`cline-mimo` repointed to the operator's
list of currently-free models.**  `argv_new` now names
`cline-free/minimax-m3.1-flash`; the `models` list carries all five strings
the operator supplied.  **None of the five has been exercised.**  Verifying
them costs live provider calls, which is a separate authorisation, so they
are recorded as *offered*, not as *working*.  Also recorded here: the
operator confirmed the `models` lists for hermes, kilo and opencode are fine
as they are -- all three are empty, which means the ladder's L1 step (resume
on a different model) is **unavailable** for them and the ladder falls
through to L2.  That is the honest state, not a defect, and it is why only pi
currently has a verified swap. | Leaving the profile pointing at a model
whose free promotion has ended, where the Fleet's MODEL_GONE handler would
discover it only on first dispatch. | Nothing.  **Classification:** an
**authorisation** action, not class K -- `agents.toml` is not pinned.  D-28's
"class K" was wrong and is corrected there.

D-36 | 2026-10-23 | OpenCode | **H6: the handover mechanism is
demonstrated; the gate as worded is not closed.**  Opencode could not run --
exit 1 after 88 s on `free-models-per-day`, the same limit as S-A1 -- so H6
as specified is **NOT RUN**, which is not a failure: it is evidence about a
free tier.  The same mechanism was then run on **kilo**: four fresh
processes, two seeds (a PROPOSED task; then a single READY task), all four
correct on project state, ready count, task id and title, and incident
count, with no disagreement between independent sessions.  **My
pre-written ground truth for the first seed was wrong**: a task needs a
`goal_ref` to be admitted, so `T-0001` was PROPOSED and "ready to dispatch"
was 0, not 1.  Both runs were right and the *expectation* was wrong.  It is
recorded rather than amended, because writing it down before the run is
exactly what exposed it. | Letting the kilo variant stand as closure of G3,
which would be claiming a gate on a CLI it does not name. | **G3 remains
open on two counts**: the gate names an *OpenCode* session and that CLI never
ran, and a real CLI taking work through a real lease is still untested --
the one-click demo uses the fake CLI.  Whether a variant satisfies the gate's
wording is the operator's call, not the implementer's.

D-37 | 2026-10-23 | operator | **OpenCode's quota is `UNKNOWN` and stays
unknown.**  OpenCode does not publish its free-tier limits, so no amount of
probing would establish them; the operator's instruction is to leave it as
unknown and to **test it together later**.  H6 as worded — an *OpenCode*
session restarting from the briefing alone — is therefore **parked, not
satisfied**, and it is the only outstanding item on G3. | Recording the
OpenCode quota as "measured" from a single rate-limit error, which would be
inventing a number.  Or quietly dropping the condition. | G3's real-CLI half
was closed separately the same day (D-39).  Whether the gate as a whole is
closed is the operator's call.

D-38 | 2026-10-23 | OpenCode (measured, M1) | **The upstream the gateway will
use publishes usage but not quota.**  Measured against the operator's own
OpenAI-compatible router on `127.0.0.1:20128`, keyed by `OMNIROUTE_API_KEY`
(no key written to any file, log or commit):
`GET /models` 200 with 10 230 models but `GET /v1/models` **503**, and
`POST /chat/completions` 200 while `POST /v1/chat/completions` **hangs** — so
**the base URL has no `/v1`**, which breaks any client that assumes it.  A
successful call returns a full `usage` block and an
`x-omniroute-decision: ... provider=cohere; latency_ms=741` header, so token
usage and provider attribution **are** capturable.  But there is **no
`x-ratelimit-*`, no `retry-after`, and no quota header at all**, and no `429`
could be induced to inspect. | Assuming the proxy can learn the provider's
limits.  It cannot through this upstream, so `V-03` **cannot be closed by
observation** here: QuotaGate's limits must be **declared locally**.  That is
a weaker guarantee than "we measured the provider" and is stated as such.
Full record: `pilot/spikes/m1-upstream.md`. | A timeout policy is **required**,
not optional: the alias `auto/cheap` timed out at 45 s while `auto/best-free`
answered in ~1 s.  M1 still only sees traffic that routes through it, and every
profile is currently `via_gateway = false`.

D-39 | 2026-10-23 | operator (approved) + OpenCode | **G3's real-CLI half
PASSES: a real CLI took work through a real lease and the Kernel accepted it.**
Run with **kilo** against a scratch repository, with a **functional** oracle
(`python check.py` parses the worker's output as a Markdown table) rather than
the demo's file-exists check.  Task `T-0002` was admitted READY, spawned on
`pid=10188` under fence 1 in a real git worktree, submitted after **500 s**,
merged with the project gate green, and the close-check passed
(`G-001: pass`, `gate: pass`).  The evidence bundle carries the output's
sha256, a clean diff-scope check (`changed: [src/csv2md.py]`, no violations),
oracle exit 0 and the constitution hash.  Full record:
`pilot/g3-real-cli.md`; evidence in `pilot/spikes/g3/`. | Treating the demo's
fake-CLI run as if it proved a real agent could do this.  It never did. | What
this does **not** establish: the **recovery ladder was never exercised**
(`attempt=1`, `restart_count=0`), so L0-L4 remain untested with a real CLI; it
is one task, one CLI, one successful attempt; and a small task consumed **500 s
of a 720 s wall budget**, which is a live latency risk because the Kernel
cannot see this CLI's token use (`L-F2`).

---

D-40 | 2026-10-23 | operator | **G3 is CLOSED.**  Decision input: the
operator's own words, "G3 closed. APPROVED", given after D-39 (the real-CLI
half passes: a real CLI took work through a real lease and the Kernel accepted
it) and after D-37 (the OpenCode half parked as `UNKNOWN`, to be run together
later).  The gate is closed **by the operator**, not by the implementer -
closing a gate is not something the implementer can do for itself. | Letting
the gate quietly lapse because its hard half passed, without the record
showing who closed it and on what basis. | The OpenCode half remains parked
(D-37) and is **still owed**: a closed gate is not the same as a satisfied
condition.  It is recorded here as outstanding work, not as debt written off.

---

D-41 | 2026-10-23 | OpenCode (measured) | **Recovery ladder with real CLIs exercised.**  

**L4** `1`/`1` attempts → real QUOTA failure from opencode (live, free-tier), ladder chose L4 → task BLOCKED with queue item `Q-001`, no fence bump.

**L3** with `max_restarts_per_task = 0` → real QUOTA failure, ladder chose L3 → lease revoked, fence **bumped 1→2**, worktree quarantined, task returned READY. No queue item (L3 is not terminal).

**Real recovery** — opencode fails QUOTA → L1 → **kilo-real**. Work submitted, oracle passed, evidence bundle complete. **However, a defect was found**:

*L1* was chosen by the ladder (because opencode's adapter claims `can_resume = True`), but the receiving profile `kilo-real` had `argv_resume = []` — meaning `profile.supports_resume()` is `False`. The dispatcher mode became `"new"`, no handoff note was written, and the order file said `## Handoff none`. The event `AGENT_RESUMED` is misleading; no session was resumed. This needs a fix (write handoff when mode is `"new"`, or choose L2 when resume is impossible), but that decision is deferred.

**L0** remains unexercised — no live CLI reliably produces a `NETWORK` failure. | Treating the ladder as "complete" without noting that L1's label diverges from its actual mode when the receiving profile has no `argv_resume`. Not reporting the defect means it stays latent. | The defect is documented; whether to fix it is operator-decision. |

---

D-42 | 2026-10-23 | OpenCode (measured, live) | **Quota is discoverable by stress test, and the first measurement changes the plan.**  Run `pilot/quotadiscover.py` against `hermes/upstage-solar-mini4` through hermes' own subscription proxy (`hermes proxy start --provider nous`, `127.0.0.1:8645/v1`): **90 requests, zero refusals**, up to 45 requests inside a 3-second burst.  No provider ceiling was found, which is not the same as there being none - it means the limit is above what this ramp reached.  Latency is the real finding: **min 889 ms, max 4250 ms, p50 about 1.7 s**.  The free tier is slow, not throttled.  Full record: `pilot/spikes/quota-solar-mini4.md`. | Reading "no 429s" as "no limit" - the absence of refusals is an upper bound on the test, not a property of the provider.  This is written into the caveats the tool emits. | Two upstreams now configured and they disagree about `/v1`: omniroute 503s on it, hermes' proxy serves it, so path rewriting is per-upstream (`path_style` on the upstream table).  The proxy also removes a Nous credential problem - the Portal is OAuth, so the gateway cannot hold a key; `hermes proxy` injects and refreshes it instead.  Limits for Nous deployments remain **unverified and self-imposed** until swept.

---

D-43 | 2026-10-23 | operator (observed behaviour) + OpenCode | **The two providers limit differently, so they must be routed differently.**  The operator's experience: **OpenRouter is ACCOUNT-limited** - the ceiling is on the account, not the model, so rotating models buys nothing and merely spends the shared budget faster; **Kilo Gateway is MODEL-limited**, and `kilo/kilo-auto/free` picks a free model from the request type, which makes it the right default.  `kilo-auto` is repointed accordingly: `model = "kilo/kilo-auto/free"`, with the 13 other live free models as the `models` list, which doubles as the recovery ladder's L1 swap targets and as optional extra agents.  `-m {model}` was added to the argv because kilo's `-m` is a global flag that must precede `run`.  Verified live with `kilo models` on 2026-10-23; cross-checked against kilo.ai/landing/free-models (5 free models, plus `kilo models`' fuller live list of 15 `kilo/*:free`). | Assuming `:free` meant the same thing everywhere, or that rotating free models is free.  It is not on an account-limited provider, and the rotation is deliberately left out of `kilo/openrouter/free` for that reason. | **Open consequence, needs an operator decision:** `ALIAS_PATTERNS` in `src/fleet/profiles.py` treats the `:free` suffix as an alias because OpenRouter uses it, but Kilo uses the identical `:free` convention for concrete free-tier models.  `guess_family` therefore returns `unknown` for all of them, and fleet amendment D-L12 says an unknown family can never serve as an independent verifier.  That is safe but lossy - the fleet's best free models cannot verify work.  Narrowing the pattern is a change to a verifier-independence rule, so it is the operator's call, not an implementer's.

---

D-44 | 2026-10-23 | operator (approved) + OpenCode | **Provenance first: APPROVED and built.**  D-L12 stopped a verifier being the implementer's *declared family*, which is a guess about a string and fails both ways - an opaque router (`kilo/kilo-auto/free`) can be the same model as the verifier while declaring a different family, and two genuinely different models in one family are rejected needlessly.  Provenance answers with a fact: the gateway is the one component in the request path, and the upstream's own answer names the model that served.  Measured live against hermes' subscription proxy: a real call returns `"model": "upstage/solar-mini4:free"`, and `x-omniroute-decision: ... provider=cohere` names the provider where the body names a router alias.  Implemented as `src/quotagate/provenance.py` (capture + ledger, keyed by task header **or** window+deployment, because the Fleet spawns a CLI *process* and so cannot put a header on the CLI's requests), `GET /v1/quotagate/provenance`, `MODEL_SERVED` recorded at submit, and `select.py` now compares served models before families. | Fabricating a model name from the profile's declared `model` when the gateway could not say.  A direct-CLI profile never reaches the gateway (`L-F2`), so the honest answer is an empty set, which leaves D-L12's existing veto in force.  That is what the code does, and a test pins it. | **Provenance can only narrow eligibility today, never widen it** - and this needs saying plainly.  Both rules now apply, because they are different axes: family is about the *lab* (shared blind spots), provenance about the *model* (same model checking its own work).  Every `agents.toml` profile still declares `family = "unknown"`, so nothing is eligible to verify regardless of what the gateway reports.  Widening that needs a declared family, which is the pending D-43 decision and the operator's call.

---

D-45 | 2026-10-23 | operator (authorised "Execute G3 if possible") + OpenCode (measured, live) | **G3's remaining condition is satisfied: the H6 handover test PASSES on the named CLI.**  Two fresh opencode processes (74.2 s and 35.0 s, exit 0), each given only `briefing.txt`, seeded with T-0001 PROPOSED / T-0002 READY / 1 incident: both named state NEW, 1 ready, next action **T-0002 - "H6-BETA: write hello.txt containing hello world"**, 1 incident, modified nothing, invented nothing (P1-P5; script `pilot/g3-opencode-handover.py`, captures `pilot/spikes/h6/g3-opencode-run-{a,b}.txt`).  The earlier NOT RUN (D-37) was the provider's daily wall, and it had reset by the time of this attempt. | A scorer defect, recorded not hidden: the first scoring pass returned FAIL on a *correct* run - the regexes matched `T-0001` and `2026` off the agent's explanation text instead of its numbered answers.  Same failure mode as H6's pair 1 (the criteria were the error, not the agent).  Repaired, run A re-scored from the preserved capture, no re-run needed.  A second defect noted: in `--reuse --runs 1` mode the in-script P5 compares one run against itself; the genuine P5 was computed across the two preserved captures. | The real-CLI half of G3 remains closed by D-39.  A G5 live run adds load evidence, not a G3 claim.

---

D-46 | 2026-10-23 | OpenCode (measured) | **S-W1 measured: worktree cost on this machine is time-only.**  20 worktrees in 2.0 s (0.10 s each), 100 more in 15.5 s (0.16 s each), ~0.0 MB of extra disk for the checkouts themselves (worktrees share the object store), free RAM 7988 -> 7903 MB.  Script `pilot/f7-scale-drill.py` (S-W1 part), results `pilot/spikes/scale-f7.json`. | Measuring the checkout and missing the shared object store would overstate disk; the number reported is the working-tree cost, and it is negligible for this repo.  Path length, not disk, is the real R-F3 risk on Windows - the 0.16 s figures include the deepest paths created. | F7 (100 fake workers) is the other half of the ceiling evidence; until it passes, `max_total_agents = 20` stands (fleet-launcher G-F5).

---

D-47 | 2026-10-23 | operator (approved exact diff, Q-004, decided "apply the diff above") + OpenCode | **G4 crossed: Caliber auto-sync is ON (`mode = "auto"`), left on per the operator's choice.**  The pinned class-K change was applied exactly as presented (two lines in `.pm/policy.toml`: `[context_sync] mode`, and the policy `version`), pins re-recorded (`pmk pins record`, `pins check` green), and one live `pmk context sync` ran: Caliber 1.55.2 executed in a Kernel worktree, hashes compared, **the generator changed nothing** - `CONTEXT_SYNC_NOOP` recorded (seq 57, 2026-10-23T08:42:22Z), nothing merged, sentinel clean.  The operator chose to leave auto-sync on rather than verify-and-revert. | The lint-reject path (recorded at the G1 baseline: the lint rejects Caliber's raw output) was not exercised by this run, because the generator produced no diff to reject.  That is stated rather than glossed: the gate is proven *from* by the G1 measurement, not by this noop.  A noop is also the correct outcome given the installed baseline - it is evidence the mechanism runs, not that it would merge. | `providers_allow = []` stays empty, so auto-sync sends nothing to any provider; G1's content-send authorisation is separate and unchanged.  V-07 (generator injection safety) is still unproven and is now load-bearing, because the next real diff will merge uncritically past dry-run - the lint and the drift check are the remaining guards.

---

D-48 | 2026-10-23 | OpenCode (measured, fake CLI - no provider calls) | **F7 PASSES and S-W1 is measured: the 100-slot ceiling is now evidence, not a guess.**  F7 (script `pilot/f7-scale-drill.py`, results `pilot/spikes/scale-f7.json`): **100/100 tasks DONE in 105 s**, 100/100 merged, **peak 100 concurrent slots**, min free RAM 7 491 MB (guard floor 2 048), sentinel clean, I1 chain verifies at 1 163 events, close-check green.  S-W1: 20 worktrees in 2.0 s (0.10 s each), 100 more in 15.5 s (0.16 s each), ~0 MB extra disk (worktrees share the object store), free RAM flat. | The first F7 attempts failed **three times on the tester's own bugs**, each recorded rather than skipped: (1) the project gate was written as a python one-liner with single quotes inside a TOML *literal* string - **invalid TOML, so `load_policy` silently fell back to defaults and the gate became `pytest -q`**, which exits 5 with no tests to collect - every merge was refused, which is I5 working exactly as designed; (2) the merge loop then spun for the full deadline because `SUBMITTED` is not in `(DONE, VOID)`; (3) the close-check failed with "no PDD" and then on PDD-lint sections/goal-heading format.  Re-run with a valid file-based gate, per-task gates (the merge queue is serial - a gate needing all 100 files can only pass on the last merge), and a full-format PDD: pass. | **`max_total_agents` may be raised 20 -> 100** under fleet-launcher G-F5 ("raised only after F7 passes"), and the operator asked to make that change themselves - `agents.toml` is human-edited (D-P3, and not class K per D-28), so the implementer does not edit it.  The measurement is the operator's to act on; the number is now theirs to set.  Two latent defects surfaced and are **recorded, not fixed** (no code change was in scope): (a) an invalid `policy.toml` is silently replaced by defaults - a typo'd policy changes the gate with no warning; (b) re-integrating a lease whose work is already committed reports "the worker changed nothing" as **ok**, skipping the gate. | The empty `src/console`-style directories seen in the first scratch were a PowerShell listing artifact of my own inspection, not harness writes; and no worktree in the live repository was ever touched by these drills.

---

D-49 | 2026-10-23 | operator (authorised "Execute G5") + OpenCode (measured, live) | **G5 crossed: the live capacity run passes, twice.**  Six real workers (3 hermes + 3 kilo, `kilo-auto/free` router) through the full mechanism in a throwaway repo: **6/6 tasks DONE, 6/6 merged through functional oracles, 6 evidence bundles, zero failures, zero UNKNOWN classes, close-check green (run 2), sentinel clean, min free RAM 5 162 MB against a 2 048 MB guard.**  Script `pilot/g5-live-capacity.py`; criteria `pilot/gate-posture-record.md` (P1–P5, all pass); record `pilot/g5-live-capacity.md`.  Free-tier only — **$0 spent**; cline excluded (rate-limited until 2026-10-24), opencode excluded (spent by the G3 attempt). | The first run's close-check failed with "no PDD" — the drill's own omission, recorded and fixed, not the mechanism.  The quota **cooldown was never exercised** (no failure occurred), so it stays synthetic-fixture-tested only; and **pi never worked** — hermes+kilo filled all six slots, so pi remains live-unrun.  Reading "zero failures" as "the cooldown works" would be exactly the overclaim the amendment's action rule exists to stop. | A real project run now reaches DONE with real agents doing real work — the F1-shaped evidence the fake-CLI demo could not give.  Combined with D-48 (F7/S-W1: 100 slots pass), the capacity story is complete on both axes: *scale* (100 fake workers) and *reality* (6 real workers).  The remaining live unknowns are narrow and named: pi, the five cline models, and any paid tier.

---

D-50 | 2026-10-24 | operator (edited `agents.toml` themselves, 2026-10-23 23:55; provenance comment in the file) + OpenCode (recorded) | **`max_total_agents` is raised 20 -> 100, by the operator's own edit.**  `agents.toml` line 20 now reads `max_total_agents = 100` with the human's in-file provenance comment; the edit carries D-P3 (human-edited file) and is not class K (D-28).  It is the change D-48 said was permitted (fleet-launcher G-F5, "raised only after F7 passes" — F7 passed), delivered by the hand the measurement belonged to. | The fleet's *mechanism* is now at 100 slots, but real-agent concurrency stays bound by the free-tier limits and by the guards (RAM floor 2 048 MB in `.pm/policy.toml` and `agents.toml`); the 100-slot number was measured on the fake CLI.  No test, pin or sentinel state changed with the edit. | Dispatcher, harness and merge queue are untouched by the edit — no code change was needed to realise it.

---

D-51 | 2026-10-24 | operator (put the two fixes in scope: "fix the following") + OpenCode (authored the fixes, tests written and run) | **Both latent defects are FIXED, with regression tests pinning each.**  (a) **Invalid policy no longer silently becomes the defaults** (`src/pmk/policy.py`): a `policy.toml` that exists but cannot be read or parsed raises `PolicyError`, surfaced through `Kernel.policy()` as `KernelError("policy_invalid")` — so the CLI, the brief, the sentinel and every event append (each is stamped with the policy hash) refuse loudly; `pmk init` under a broken policy exits 2 with a machine-readable JSON error naming the file and the TOML line (live-verified in a throwaway root).  The file-*absent* first-boot default is retained and pinned by test.  (b) **Re-integration runs the gate** (`src/fleet/merge.py`): the "the worker changed nothing" early return that reported `ok` for an already-committed lease without running the gate is gone; every path now merges the lease branch (a structural no-op when it is already in main, detected by HEAD not moving — locale-proof) and runs the gate on the tree that would become canonical, so I5's promise ("nothing is promoted without a passing gate") holds on re-runs too; the already-merged case no longer misattributes the previous merge's files, and the `ORACLE_RESULT` record now carries `reintegration: true` when a promotion passes with no fresh work. | Two adjacent surfaces were deliberately **not** changed and are recorded rather than glossed: `load_agents` keeps its documented empty-profile fallback (a stated fleet posture, "must not take the Kernel down", not an accident — if the operator wants a warning event there, that is their call); and the *first-boot* default policy stays.  Gate green paths incl. `gate_cmd=""` behave as before. | **7 new regression tests** (`tests/pmk/test_policy_invalid.py` ×4, `tests/fleet/test_reintegration_gate.py` ×3): 234 pass, 0 fail; sentinel clean (I1–I16, incl. I5); pins green (source is not pinned; `.pm/` untouched — `mode = "auto"` stands from D-47).  Committed and tagged `bootstrap/18`.

---

## Pending

- ~~**G5's live run**~~ — **CROSSED (D-49)**: two live runs, six
  concurrent real workers, 6/6 DONE, zero failures, close-check green.
  pi never worked (hermes+kilo filled the slots) - pi is still live-unrun.
- ~~**F7/S-W1**~~ — **PASSED (D-48)**: 100/100 DONE at peak 100 slots
  in 105 s; ~~`max_total_agents` may be raised 20 -> 100 (operator's edit)~~
  **DONE (D-50)**: the operator raised it themselves, 2026-10-23 23:55.
- **The two latent defects recorded at F7/G5** ~~considered as future
  work~~ — **FIXED (D-51)**, 2026-10-24: invalid `policy.toml` now
  stops the line instead of silently becoming the defaults; re-integration
  of an already-committed lease now runs the gate.  7 regression tests.
- **QuotaGate M1** — the capture behaviour is now measured (D-38): usage yes,
  quota headers no, and the upstream has **no `/v1`**.  Still to build: the
  proxy itself, its timeout policy, and local limit declaration.
- **The recovery ladder with a real CLI** — L0-L4 have never been exercised
  against a live agent; only the fake CLI and the synthetic fixtures.
- **Verifying the five cline models** — costs live provider calls, so it is
  a separate authorisation.  The operator notes their rate limit resets
  2026-10-24.  Until then they are offered, not working.
- **V-07 generator injection safety** is now load-bearing: with auto-sync on
  (D-47), the next real generated diff merges past dry-run, guarded only by
  the lint and the drift check.

## Resolved since the last update

- **`max_total_agents` 20 -> 100** — the operator's edit, recorded (D-50).
- **The two latent defects** — fixed with regression tests (D-51).
- **CIP Q1** — answered: OmniRoute, terms accepted (D-23).
- **Caliber install** — approved and done; the G1 baseline is installed.
- **Live S-A1** — approved with terms (D-24) and **run**; 13 requests, no
  failure provoked (D-26).
- **The gate rule** — given (D-25), then **amended in force** as v2
  (D-34), approved as class K item Q-003.
- **D-19 and D-20** — **ratified** (D-29), as class K queue items Q-001 and
  Q-002 in the event log.
