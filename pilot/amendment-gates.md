# Draft amendment — gates, checkpoints, and the class K rule

**Version:** v2 — the operator's edits of 2026-10-23 applied.
**Status:** **IN FORCE** from 2026-10-23. Approved as class K queue item
**Q-003** (`approve`), recorded at **D-34**. The consequences are applied:
the gate record and `STATE.md` use the action-based classification, the
report's §4.4 and §8 adopt this text, and "self-crossed" is retired.
**Author:** OpenCode. **Edits:** operator, 2026-10-23.
**Supersedes:** v1 of this file.

> **What changed from v1, and why it was wrong.** v1 classified G0–G2 as
> "evidence gates" *by gate number*, and labelled their crossings
> "self-crossed". Both were errors. A gate's kind is a property of **what
> the action does**, not of which number it carries: G2 contains both a
> metadata check (evidence) and live provider calls (authorisation), and
> G1 contains both a measurement of Caliber (evidence) and the act of
> sending repository content to third parties (authorisation). And the
> G0–G2 crossings were **not** self-crossed — they were authorised by the
> operator. Both corrections are applied below.

---

## 1. The defect this amendment fixes

Two rules in pilot v1 give **opposite instructions for the same situation**.

**§13 rule 14:**

> Ask only when blocked. State your default and what you will do on silence.

**§12.1:**

> The default on silence is hold: the LLM continues unblocked work and does
> not cross the gate.

Neither rule says **what a gate is**, so "do not cross" cannot be applied:
nobody can say what crossing consists of. In this pilot that ambiguity was
live — the implementer asked for the gate rule, was told *"I will provide
these"*, and continued building while the boundary stayed undefined. That
it did not go wrong is luck, not governance.

The fix is not to choose between rule 14 and §12.1. It is to define the
thing they both refer to.

---

## 2. The rule (v2)

> ### §12.1 Gates and checkpoints
>
> **Classification is by action, not by gate number.** A gate number names
> a *point in the plan*; it does not determine whether the action at that
> point needs the human. Two actions at the same gate number can have
> different kinds, and when they do, they are recorded separately.
>
> **An authorisation action is one that:**
>
> * makes a **live call to a provider**, or spends a provider's quota;
> * **sends repository content to a third party**, including a model
>   provider, an aggregator, or a router that fronts one;
> * **hands work to a real agent**, in a real repository;
> * **turns on a mechanism that can write instructions an agent will
>   follow**;
> * makes a **decision with lasting consequence that a later reader cannot
>   undo by reverting a commit** — including the platform decision.
>
> An authorisation action requires a **gate**: the implementer stops, names
> the consequence, and waits for the human. Silence is not consent.
>
> **An evidence action is a checkpoint.** A checkpoint must satisfy both of
> these, and an action that fails either one is treated as an
> authorisation action:
>
> 1. **Its pass criteria are written down before the check runs.** Criteria
>    invented after the result are not criteria; they are a description of
>    what happened.
> 2. **It is reversible by reverting a commit or deleting scratch files.**
>    If undoing it needs anything else — a provider to forget something, an
>    agent to un-learn something, a decision to be unmade — it was not a
>    checkpoint.
>
> A checkpoint is **logged**, not asked about: the criteria, the result,
> and the artefacts, in the decision log, for review after the fact.
>
> **A gate with no nameable consequence is not a gate.** If the consequence
> cannot be written in one sentence, either name it or call the point a
> **checkpoint** — and if it is a checkpoint, the two tests above decide
> whether that is honest.
>
> **If the kind cannot be determined, hold and report it.** Ambiguity
> resolves to *authorisation*, never to *proceed*. An implementer who
> cannot classify an action has not established that it is safe to take.
>
> **A gate is crossed once per mechanism, not once per task or dispatch.**
> Approving a mechanism approves that mechanism until it is withdrawn; it
> is not re-asked on every dispatch, which would make the gate noise. The
> converse is the important half: **an approval covers the mechanism it
> named and no other.** A different mechanism is a different gate.
>
> **Class K is always two-key**, regardless of any earlier approval. The
> two keys are: (1) the change is presented with its exact diff, and (2)
> the human accepts *that* change. **The key is taken before the change**,
> not after: a key applied afterwards is an audit, not a gate. Approving an
> install is not approving the configuration that install implies.
>
> **Rule 14's "state your default" applies to unblocked work between
> gates, not to the gates themselves.** Where rule 14 and this section
> disagree, this section governs.

---

## 3. Consequential edits

1. **Delete** *"The default on silence is hold"* as a general rule. Replace
   with the action-based classification above: silence is not consent at an
   authorisation action; a checkpoint is logged rather than asked about.
2. **§13 rule 14** becomes: *"Ask at an authorisation action, or when the
   kind of an action cannot be determined. Between gates, state your
   default and proceed."*
3. **The gate list gains a column**: the named consequence, and the kind
   (authorisation or checkpoint) of each action at that point.
4. **Replace "self-crossed"** wherever the record uses it. A crossing is
   either *authorised by* a named decision, or *logged as a checkpoint*
   against pre-written criteria. There is no third state.

---

## 4. Applied — the pilot's gate list, classified by action

This is the test of the rule: does it produce a classification anyone can
check?

| Point | Action | Kind | Named consequence | Authority / criteria |
|---|---|---|---|---|
| **G0** | The platform decision (native Windows, no WSL/Docker) | **authorisation** | the whole system is built on Windows-native assumptions for its lifetime | **the operator's instruction**; D-02 |
| **G0** | Environment metadata (versions, paths, lock test) | checkpoint | — | logged; artefacts in `pilot/spikes/s-p1-platform.md` |
| **G1** | Measuring Caliber's behaviour (S1–S5: endpoints, files written, overwrite semantics, hook behaviour) | checkpoint | — | logged; artefacts in `pilot/spikes/caliber-s1-s5.md` |
| **G1** | **Installing Caliber** | authorisation | a third-party generator runs in this repository | **operator approved the install** (D-15…D-19) |
| **G1** | **The sync sending repository content to providers** | **authorisation** | the repository's content reaches third-party free providers | **the operator accepted the terms** — OmniRoute, D-23 |
| **G2** | Metadata capture (five `--help`s, five versions, shim measurement) | checkpoint | — | logged; artefacts in `pilot/spikes/cli-matrix.md` |
| **G2** | **Live S-A1 provider calls** | **authorisation** | real requests to real providers, consuming their quota | **the operator approved it with terms** — D-24: throwaway repo, fixed prompt, three modes, one authorised QUOTA capture |
| **G3** | A real CLI through a real lease; an OpenCode session restarting from the briefing alone | **authorisation** | real agents take real work in a real repository | **ratification of D-19/D-20 done** (D-29); **the handover test itself is outstanding and needs its own go-ahead** (D-30) |
| **G4** | Turning Caliber auto-sync on | **authorisation** | the generator writes instructions agents will follow, on every commit | **HELD** — `mode = "dry-run"` |
| **G5** | Live capacity run | **authorisation** | spend, and sustained load on real providers | **HELD** |

**Nothing in G0–G2 was self-crossed.** The authorisation actions inside
them were authorised: the platform decision, the Caliber install, the
provider terms, and the live calls were each a named decision by the
operator (D-02, D-15…D-19, D-23, D-24). The evidence actions were
checkpoints, logged with their artefacts.

**One honest gap, recorded rather than papered over.** Under the
pre-written-criteria test in §2, the G0–G2 checkpoints are **imperfect**:
their criteria were implied by each spike's question rather than written
down as pass/fail before the run. They are recorded here as *logged
checkpoints with a known weakness*, not as clean ones. This changes no
outcome — nothing irreversible was done on the strength of them, because
the consequential actions at G0–G2 were authorised by name — but a future
checkpoint must state its pass criteria **before** it runs, and that is now
part of the rule rather than a lesson learned too late.

---

## 5. Outcome — the second key

**Approved** (operator, 2026-10-23), recorded as class K queue item
**Q-003** with choice `approve`, and at **D-34**. The consequences have
landed:

* the gate record in `decisions.md` classifies by action and no longer uses
  "self-crossed";
* `STATE.md` carries the same table;
* the report's §4.4 and §8 adopt this text;
* `decisions.md` records the amendment in force (D-34).

The sequence was: draft → exact diff presented → class K item raised →
approval → *then* the consequences applied. That is the order the pilot
requires, and the D-19/D-20 timing weakness (D-29) is why it was followed
explicitly here rather than assumed.
