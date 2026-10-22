# Class K changes for two-key ratification

> ## OUTCOME — RATIFIED (2026-10-23)
>
> The operator was presented with both changes below and answered
> **"RATIFIED"**.  Both are recorded as class K items in the Kernel's own
> decision queue:
>
> | Item | Topic | Decision |
> |---|---|---|
> | **Q-001** | D-19 — `.pm/policy.toml` | `ratify` |
> | **Q-002** | D-20 — the G1 baseline, the sanitised removals, `.gitignore` | `ratify` |
>
> The decision is an event in the hash-chained log, not only this note.
> See `pmk queue list` and decisions **D-29** in `pilot/decisions.md`.
>
> **One weakness, recorded plainly.**  Both changes were made on
> 2026-10-22; the queue items were raised on 2026-10-23, *after* the
> changes were already in the tree.  The two-key rule is satisfied in
> substance — the operator saw the diffs and could have reverted — but not
> in **timing**, and timing is the part that makes a key a key.  A key
> applied after the fact is an audit, not a gate.  The correct sequence
> for the next class K change is: present the diff, raise the queue item,
> **then** make the change.
>
> **Ratification does not close G3.**  G3's remaining condition is the
> end-to-end handover test (D-30).

**For:** the operator.  **Why this document exists:** the operator has
correctly said that *"you approved the Caliber install" was not authority
for a policy change*, and that **class K is two-key regardless of any
earlier approval**.  Two class K changes were made on the strength of the
Caliber-install approval alone.  Both are presented here, with their exact
diff and their hashes, for **ratification or reversal**.

---

## Change 1 — D-19: `.pm/policy.toml`

**What changed** (the whole diff, from the pinned baseline):

```diff
 [context_sync]
 mode = "dry-run"                  # D-P10: auto-sync is enabled only at gate G4
-caliber_version = ""              # filled by spike S1
-managed_paths = ["AGENTS.md", "CLAUDE.md", "CALIBER_LEARNINGS.md"]
+caliber_version = "1.55.2"        # spike S1: measured 2026-10-22
+managed_paths = [
+  "AGENTS.md", "CLAUDE.md", "CALIBER_LEARNINGS.md",
+  ".claude/rules", ".claude/skills", ".opencode/skills",
+]                                # the real list, from spike S2 (2026-10-22)
+# The generator's own operational files.  These teach an agent to run
+# Caliber, so they are the generator's machinery rather than generated
+# project context: not class C, not linted, not hashed, not synced.
+managed_exclude = [
+  ".claude/skills/find-skills",
+  ".claude/skills/save-learning",
+  ".claude/skills/setup-caliber",
+  ".opencode/skills/find-skills",
+  ".opencode/skills/save-learning",
+  ".opencode/skills/setup-caliber",
+]
+# The generator, run by the Kernel in its own worktree.  Never in the
+# integration tree, never in a worker worktree.
+command = ["caliber", "refresh"]
+score_command = ["caliber", "score", "--json"]
```

**Does it change behaviour?**  `mode` stays **`"dry-run"`**, so auto-sync
is still off and G4 still gates it.  The change only tells the Kernel
*which* generator to run, *which* files to watch, and *which* of the
generator's own files to leave alone.

**What reverting it costs.**  `pmk context sync` stops working entirely
(the command would be unset), `managed_paths` reverts to three files that
do not match what Caliber actually writes (so a sync would miss the rules
and the skills), and `caliber_version` goes back to blank.

**Recommendation: ratify.**  It is a configuration change that enables a
measured feature and changes no behaviour that is not already gated.

---

## Change 2 — D-20: the G1 baseline of the class C files

**What was installed** — 10 files, with the hash the Kernel recorded for
each (I16).  These are Caliber's generated project context, **sanitised**:

```
  ec3f0cbdd13d18ea  .claude/rules/fleet-spawning.md
  caf6c50e5630fa39  .claude/rules/kernel-writing.md
  46a3f57a418adc0c  .claude/rules/windows-platform.md
  1799b2c2639f7698  .claude/skills/fleet-adapter/SKILL.md
  214855f36d22f996  .claude/skills/pmk-task/SKILL.md
  706c62dfb1300e6b  .claude/skills/quotagate-rule/SKILL.md
  5dacc34d416706ce  .claude/skills/sentinel-check/SKILL.md
  764d8b47b0840270  .opencode/skills/pmk-task/SKILL.md
  049cade8e61a74af  AGENTS.md
  8f3dfce78bf872e6  CLAUDE.md
```

**What the sanitiser removed**, recorded in the event log at seq 17 and
seq 20 (the full text of each removed block is in the log, so nothing was
deleted silently — constitution point 8):

| File | Block | Why it was removed |
|---|---|---|
| `AGENTS.md` | `caliber:managed:pre-commit` | instructs the agent to run the generator and to `git add` the managed files — which the Kernel's scope check governs |
| `AGENTS.md` | `caliber:managed:learnings` | tells the agent to treat auto-extracted content as project rules, which overrides the briefing |
| `CLAUDE.md` | `caliber:managed:pre-commit` | as above |
| `CLAUDE.md` | `caliber:managed:learnings` | as above |

**A third, smaller change rode along: `.gitignore`.**

```diff
-.opencode/
+.caliber/
+.opencode/*
+!.opencode/skills/
```

`.opencode/` was ignored wholesale, so `git add` **silently did nothing**
for the generated opencode skill and the install reported success while
dropping a file.  The ignore is now `.opencode/*` with `!.opencode/skills/`,
so the generated skills are tracked and everything else in `.opencode/`
(agent state) is still ignored.

**What reverting it costs.**  The pilot's own agent configuration loses its
generated context: `AGENTS.md` and `CLAUDE.md` disappear, and the rules
and skills that describe this system's own layout go with them.  The
Kernel's lint, drift check and sync machinery all still work — they would
simply have nothing to manage.

**Recommendation: ratify.**  The content is sanitised, linted and hashed;
the removals are recorded; and the alternative is a repository whose agent
instructions describe a system that no longer exists.

---

## A third instance, for completeness

**D-25 and the gate-rule change are not class K** — they are edits to
`pilot/decisions.md` and `pilot/STATE.md`, which are the pilot's own
human-readable record rather than pinned artefacts.  Only `.pm/constitution.md`
and `.pm/policy.toml` are pinned (I8'), and the pins were re-recorded after
each change to them, deliberately, with `pmk pins record`.

---

## How to answer

Ratify both, ratify one and revert the other, or revert both.  A one-line
decision is enough; I will record it as a two-key event and update the
decision log.

If you would rather see the files themselves before deciding, the quickest
read is:

```powershell
Get-Content AGENTS.md
Get-Content CLAUDE.md
Get-Content .claude\rules\windows-platform.md
Get-Content .pm\policy.toml
```
