# Draft amendment — §12.1, §13 rule 14, and the class K rule

**Status:** DRAFT, for the operator to accept, edit or discard. Not in force.
**Author:** OpenCode, from the defect recorded at `pilot/pilot-report.md` §4.4.
**Supersedes:** nothing. It adds text; it deletes one sentence.

---

## 1. The defect

Two rules in pilot v1 give **opposite instructions for the same situation**.

**§13 rule 14:**

> Ask only when blocked. State your default and what you will do on silence.

**§12.1:**

> The default on silence is hold: the LLM continues unblocked work and does
> not cross the gate.

Read together, an agent that is neither blocked nor at a gate — with no
human answer pending — is told by rule 14 to *proceed with its stated
default*, and told by §12.1 to *not cross the gate*. Both readings are
defensible. Which one an agent adopts silently changes what the gates
**mean**, which is the one thing a gate cannot survive.

This is not hypothetical: it is what happened in this pilot. The
implementer asked for the gate rule, was told *"I will provide these"*, and
then continued building under the §12.1 reading while the boundary stayed
undefined. Nothing broke, by luck. A different implementer reading rule 14
would have self-crossed G3 and handed work to real agents.

**The defect is not that one rule is wrong. It is that neither rule says
what a gate *is*.** Without that, "do not cross" is unenforceable, because
nobody can say what crossing consists of.

---

## 2. Proposed replacement text

> ### §12.1 Gates
>
> **A gate is a point at which the human is asked to accept a specific,
> named consequence.** If the consequence cannot be named, it is not a
> gate, and it does not belong in the gate list.
>
> **Gates are of two kinds.**
>
> An **evidence gate** (G0–G2) is one whose artefacts can be reviewed after
> the fact. The implementer **proceeds**, and records, in the decision log:
> the crossing, the evidence for it, and the reasoning that the evidence is
> sufficient. The artefacts are then reviewed asynchronously and the
> crossing is confirmed or reversed. An evidence gate that is waiting for a
> human is a gate that has been confused with an authorisation gate.
>
> An **authorisation gate** (G3–G6) is one that does any of the following:
>
> * changes the system's behaviour in a way a later observer cannot undo by
>   reverting a commit;
> * hands work to a real agent, in a real repository;
> * spends a provider's quota, or sends project content to a third party;
> * turns on a mechanism that can write instructions to agents.
>
> At an authorisation gate the implementer **stops and waits for the
> human**, and the gate is not crossed until the human says so in their own
> words. Silence is not consent at an authorisation gate.
>
> **Class K is always two-key**, regardless of any earlier approval. The
> two keys are: (1) the change is presented with its exact diff, and (2) the
> human accepts *that* change. An approval of one thing is never authority
> for a different class K change — in particular, **approving an install is
> not approving the configuration that install implies.**
>
> **Rule 14's "state your default" applies to unblocked work between
> gates, not to the gates themselves.** Where rule 14 and this section
> disagree, this section governs.
>
> **A gate the implementer cannot apply is a defect in the plan, not in the
> implementer.** If an implementer cannot say whether a situation is at a
> gate, that ambiguity is reported as a finding and escalated, rather than
> resolved by choosing a reading.

---

## 3. Consequential edits

1. **Delete** the sentence *"The default on silence is hold"* as a general
   rule. Replace it with the two-kind distinction above; "silence is not
   consent" applies only to authorisation gates, and "proceed and record"
   applies to evidence gates.
2. **§13 rule 14** becomes: *"Ask only at an authorisation gate, or when a
   gate's definition is unclear. Between gates, state your default and
   proceed."*
3. **Add to the gate list**: for each gate, the *named consequence* the
   human is accepting. A gate whose consequence cannot be written in one
   sentence should be split or dropped.

---

## 4. Worked example — this pilot's gates

The two-kind distinction is not abstract. Applied to this pilot:

| Gate | Kind | The named consequence | Status |
|---|---|---|---|
| G0 environment | evidence | none — a fact about the machine | self-crossed, recorded |
| G1 Caliber go/fallback | evidence | none — a measurement | self-crossed, recorded |
| G2 live capture | evidence | none — a measurement | self-crossed, recorded |
| G3 handover | authorisation | real agents take real work in a real repo | ratification done; **end-to-end test outstanding** |
| G4 auto-sync on | authorisation | the generator writes instructions agents will follow | **held** |
| G5 live capacity | authorisation | spend, and load on real providers | **held** |

G0–G2 were crossed without asking, because crossing them **cannot hurt
anyone** — they are measurements, and their evidence is now in
`pilot/decisions.md` for review. G3–G5 were not crossed, because each of
them can hand control of something real to something that will act on it.

That is the whole point of the distinction: **the gate list stops being a
list of things to ask about, and becomes a list of things that can go
wrong.**

---

## 5. What the operator does with this

Read it, then one of:

* **accept as written** — I apply it to the pilot report's §8 and treat it
  as the standing rule;
* **accept with edits** — send the edited text, I apply that;
* **discard** — say so, and the finding stays a finding with no proposed
  remedy, which is an honest outcome and better than a rule nobody means.

The finding itself (`pilot/pilot-report.md` §4.4) stands regardless. This
draft is only the proposed remedy.
