---
document: "OpenCode prompt: UMAWS completion report and assessment bundle"
version: "1.0.0"
author: "Claude (Claude Sonnet 5.5)"
date: "2026-10-24"
use: "Save as pilot/assessment/PROMPT.md in the pilot repo. Tell OpenCode: Read pilot/assessment/PROMPT.md and follow it exactly."
---

# Task: produce the UMAWS completion report and an assessment bundle

## 1. Your role

You are an **evidence compiler and a witness, not an advocate.** You built or maintained this system, and an independent reviewer (Claude) will now assess it. The reviewer sees only what you hand over and cannot ask you questions. Your job is to make every claim **checkable**, not to make the project look finished. Adverse findings (failures, gaps, unverified items, divergences from the spec) are the most valuable content you can produce. Placing them first is correct.

## 2. Context

The UMAWS Fleet / QuotaGate pilot (P-01) is reported complete. `UMAWS_USER_MANUAL.md` says "Tier C achieved, Sentinel clean" and "production-ready for supervised use". The operator also states that: the 100-agent test is complete; the quota-limit tests are complete; and all models (400+) were tested and work. **Treat all of these as claims to verify, not facts.**

The yardstick, in this order:

1. Pilot v1 (`docs/sources/pilot-proposal.md`): hypotheses H1–H7, acceptance tests, gates G0–G6, rules of engagement, tiers.
2. The user manual: every checkable statement in it is a claim.
3. The Fleet Launcher amendment (`docs/sources/fleet-launcher-proposal.md`): requirements FR1–FR15, deviations D-L1–D-L14, spikes, hypotheses H8–H12, acceptance tests F1–F14.
4. The gates amendment (`amendment-gates.md`) and its current status.

The operator has just stress-tested provider quotas, so **quota is likely exhausted. Do not use any.**

## 3. Hard rules

1. **The repo is read-only.** Do not fix, edit, refactor, re-configure, commit or clean up anything. If you find a bug, report it and do not fix it: a fix made before reporting makes the report describe a system the operator does not have. Write only under `pilot/assessment/`.
2. **Run everything in a clone.** Make a fresh `git clone` (or worktree) of the repo into a temporary directory and run all tests, the sentinel and the console there, so the live `.pm/` state is never touched. Read the live event log only from a **copy**.
3. **No provider calls.** Do not call any LLM, provider, router or proxy upstream. Do not run the Dispatcher against real profiles or launch real CLIs. Offline work only: tests, sentinel, the fake CLI, file reads, git, hashing, a local console smoke test. If a claim can only be verified by a live call, mark it `UNVERIFIED` and list it in section 12 ("Optional live checks") with the cheapest check (at most one trivial call). The operator will approve any such call item by item.
4. **Three evidence labels, used on every claim:**
   - `RAN-NOW`: you executed it in this session; the raw output is attached with its command, exit code and timestamp.
   - `READ`: taken from an existing file; cite the path, the commit and the section or line. State the file's timestamp.
   - `RECALLED`: from your own memory of earlier work. This is **not evidence**. Use it only to say where to look, and never count it toward a verdict.
5. **Never write "passes", "works", "clean" or "complete"** without attached `RAN-NOW` output or a cited `READ` artefact. Prefer `UNVERIFIED` to a guess. Never invent a number: compute every metric from the event log with a script you include in the bundle.
6. **Do not soften.** If the manual says something the code does not do, say so plainly. Do not use marketing language ("production-ready", "comprehensive", "robust") unless you define it and attach evidence.
7. **No secrets.** Scan everything you place in the bundle (keys, tokens, bearer strings, `sk-`-style strings, URLs with credentials, `.env` contents, values of any environment variable named in a config's `secret_env`). Redact, and report what categories were redacted. Never print a key value.
8. **Only the pilot repo.** Include nothing from other repositories (for example other game or project folders) or personal files.
9. Do not ask the operator questions unless you are blocked; state your default and continue.

## 4. Procedure

**Step 0: snapshot.** Record commit hash, `git status --porcelain` (dirty or clean), date and time, OS, Python, Git and Node versions, and each CLI's version (hermes, kilo, cline, pi, opencode). Version checks only.

**Step 1: claim inventory.** Extract and number every checkable claim: manual claims `M-001…`, each v1 acceptance test (T1–T6, Q1–Q5, H6, C1), each amendment item (FR1–FR15, D-L1–D-L14, F1–F14, H8–H12), each v1 hypothesis (H1–H7). Do not skip an item because it is awkward.

**Step 2: offline retest (in the clone).** Record raw output for each:
- The full test suite, using the project's configured test command.
- The sentinel (`pmk sentinel`), run against a copy of live state.
- Every fake-CLI scenario test (kill mid-task, quota, auth, network, model-gone, crash, hang, slow, oracle-fail-then-ok, unknown-classifier, overlap, restart/reconcile, selection and family exclusion).
- Event-log integrity: verify the hash chain end to end, report the first break if any, and report event counts by type.
- Views versus projection (invariant I13).
- **Doc-test the manual:** run every command in the manual with `--help` only (or its dry-run form if it has one) and record whether it exists and its flags match. List every manual statement that is false, aspirational or inconsistent, including ports and console tabs (manual says 8080 and lists Overview, Tasks, Leases, Profiles, Events, Gateway, Sentinel; the amendment specified port 8765 with Projects, Fleet, Tasks, Queue, Overseer, Manual launcher, Metrics).
- Console smoke test on localhost: start it in the clone, list the tabs and endpoints that actually respond, stop it. No provider calls.
- If you run the 100-worker scale test, use fake workers only, run it for at most 15 minutes wall time, and state the duration actually run. Otherwise reduce it and say so.

**Step 3: evidence from earlier runs (READ only).** For each of the following, locate the raw artefacts and state **exactly what the test was**: the 100-agent test; the quota-limit tests (Q3, Q4 and any others); the all-models census; the spikes (S-P1, S-A1, S-O1, S-W1, S-L1, Caliber S1–S5); any real project runs. For each give: date, who ran it, **fake or real workers**, counts, duration, latency figures, errors, and what raw artefact proves it. If an artefact is missing, say `ARTEFACT MISSING` and do not reconstruct it.

For the model census specifically: what was the call, what counts as "working", how many models were attempted, how many succeeded, which failed and why, on what date, and whether any result has expired (daily limits, dead models).

**Step 4: gate and decision audit.** For G0–G6 give: kind (evidence or authorisation), the named consequence, who authorised the crossing and when (cite the operator's words in `decisions.md` or `STATE.md`), and current status. List every item in `decisions.md`. Report the status of the gates amendment (accepted, edited, discarded, pending), the D-19 policy change (ratified, reverted, pending), and the rule 14 versus 12.1 finding.

**Step 5: compile.** Write the report and bundle as specified below.

## 5. Report

File: `pilot/assessment/report-opencode-umaws-completion-v1.md`.

**Front matter:** author (OpenCode and the exact model), version `1.0.0`, date, commit hash, dirty flag, scope, prompt version `1.0.0`.

**Verdict vocabulary** (use exactly these): `VERIFIED-NOW`, `VERIFIED-EARLIER` (READ, with artefact), `UNVERIFIED`, `FAILED`, `NOT-BUILT`, `DIVERGES` (built differently from the spec; say how), `WRONG-DOC` (manual says X, reality is Y).

**Sections, in this order:**

1. **Executive summary (at most one page).** Lead with what failed, diverged, was not built or is unverified. Then what is verified now. Then a plain statement of how this differs from "Tier C achieved, Sentinel clean". Counts per verdict.
2. **Method and limits.** What you ran, what you only read, the clone, what you could not do and why. State that you are also the system's author and what bias that implies.
3. **Claims versus evidence.** One table covering every claim from step 1. Columns: `ID | Claim | Source (doc, section) | Evidence label | Evidence (file or command) | Verdict | Notes`.
4. **Requirement coverage.** FR1–FR15 and D-L1–D-L14: implemented, where, evidence, divergence.
5. **Acceptance tests.** T1–T6, Q1–Q5, H6, C1, F1–F14: last recorded result, retest result now, verdict.
6. **Hypotheses H1–H12.** For each: the measure, the measured value, evidence, and a grade (supported, not supported, inconclusive) using v1's grading rules. State where a hypothesis was never measured.
7. **Spikes and fixtures.** What S-A1 actually captured per CLI (headless, session id, resume, model swap on resume, exit codes). Classifier fixture coverage per adapter, naming each failure class that is still `UNVERIFIED`. The real 429 body shape and rate-limit header names (V-03): captured or still open. The S-W1 and S-L1 numbers.
8. **Fleet findings.** The recovery ladder's behaviour (counts of each ladder step in real runs versus fake runs), selection behaviour, the 100-agent test (what it really was), the model census, observed scale limits.
9. **QuotaGate.** M0–M5 status, what M1 can and cannot measure (it only sees proxied traffic), and Q1–Q5.
10. **Manual versus reality.** The doc-test results; every `WRONG-DOC` item.
11. **Gates, decisions and deviations.** The audit from step 4.
12. **Defects, limitations, risks.** Known defects (with how to reproduce), limitations L-F1–L-F5 and v1's L-P series (still true?), the no-sandbox exposure, key and secret handling, anything the secret scan found. Include **Optional live checks** here, each with its cost and the single claim it would settle.
13. **What was cut or not done.** Against the tier contents and the cut order. State plainly which tier was actually achieved by the evidence (A, B, C or none), item by item.
14. **Readiness for a toy-project run (not executed).** Read-only pre-flight: which commands exist and what they do (from `--help`), which profiles are enabled or cooling now, whether any dispatch could happen today, and the exact steps you propose. Do **not** run it.
15. **Appendices.** Environment; every command run, verbatim, with exit code and timestamp; the manifest.

No length limit. Be comprehensive without padding: use tables for claims, and prose only where reasoning is needed.

## 6. Bundle

Directory `pilot/assessment/bundle/` containing:

- `MANIFEST.md`: one row per file: path, size, SHA-256, label (`RAN-NOW` or `READ`), and what it proves.
- `raw/`: the raw output of every command you ran, each with command line, exit code and timestamp.
- Existing records (READ): `pilot-report.md`, `decisions.md`, `STATE.md`, the spike tables (`cli-matrix.md`, `scale.md` and the others), `agents.toml` (redacted), `policy.toml`, the QuotaGate config (redacted), the gates amendment, the user manual, `git log --oneline` for the last 100 commits, and a file tree with line counts.
- Fixtures: the list of fixture files per adapter, with at most two sample files per adapter.
- Evidence bundles: at least three real ones if they exist (one passed, one failed or quarantined, one recovered through the ladder), or an explicit statement that none exists.
- Event log: the first 50 and last 50 lines, one complete task lifecycle, and counts by type.
- Raw artefacts of the 100-agent test, the quota tests and the model census, or `ARTEFACT MISSING` in the manifest.
- `scripts/`: every script used to compute a metric.

**Size:** no file over about 150 KB and the bundle under about 3 MB. For larger logs include the head, the tail, the line count and the SHA-256 of the full file, and say what was cut.

## 7. What makes this great versus mediocre

1. **Traceable.** Every claim maps to labelled evidence, and a reviewer can recompute any number from the manifest, commands and hashes.
2. **Honest.** Failures, gaps and divergences lead the report. `UNVERIFIED` is used freely. Nothing is described as working without proof.
3. **Self-contained.** The reviewer never needs to ask you anything. Anything that cannot be shown is listed as missing, not paraphrased.

A mediocre answer is a confident summary that repeats the manual's claims.

## 8. Finish

When done, reply with only: the report path, the bundle path, the total bundle size, the counts of `FAILED`, `UNVERIFIED`, `NOT-BUILT`, `DIVERGES` and `WRONG-DOC`, and any step you could not complete and why. Do not summarise the findings in the reply; they belong in the report.
