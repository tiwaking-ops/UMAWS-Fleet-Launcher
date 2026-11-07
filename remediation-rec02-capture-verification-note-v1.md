---
document:
  title: "Remediation Note: REC-02 Worktree Capture — Implementation and Single-Tree Verification"
  status: "Advisory implementation and verification record. Records what was built and proved; makes no governance decision, promotes nothing, reclaims nothing."
  version: "1.2.0"
provenance:
  author_llm:
    name: "DeepSeek V4.1 Flash"
    version: "deepseek-ai/deepseek-v4.1-flash (nvidia)"
  created_date: "2026-11-08"
  last_modified_date: "2026-11-08"
  scope: "src/pmk/worktrees.py, src/pmk/store.py, src/pmk/cli.py, src/pmk/api.py, tests/pmk/test_worktree_lifecycle.py; one capture of work/T-0131-110 into stranded/T-0131-110/; the live event log (.pm/events/*.jsonl, 3,111 events) read only."
  source_of_truth: "The append-only event log at .pm/events/*.jsonl (I1 hash chain verifies) is authoritative for coordination state; git objects are authoritative for committed content. This note is a filesystem-and-code record and does not override either."
  related_documents:
    - "incident-report-worktree-lifecycle-leak-v1.1.md (the formal incident report this remediates)"
    - "proposal-deepseek-umaws-fleet-worktree-lifecycle-remediation-v1.md (operator-approved remediation plan; REC-02 is Phase 1)"
  model_identity_note: "This author is the same model family as the incident report's author (DeepSeek V4.1 Flash Free). This note is self-reported implementation/verification, NOT an independent assessment; it must not be cited as one."
  authority: "Operator (Tiwa Pene, Human) approved action (a) — 'run the capture on one dirty tree, inspect it, confirm it reads back' — on 2026-11-08. No other authority is claimed."
---

# Remediation Note: REC-02 Worktree Capture — Implementation and Single-Tree Verification

**Author:** DeepSeek V4.1 Flash (`deepseek-ai/deepseek-v4.1-flash`, nvidia)
**Date:** 2026-11-08
**Repository:** `C:\temp\projects\testproject1`
**HEAD at time of writing:** `ee960c2`
**Project state:** `PAUSED` (unchanged)
**Status:** Advisory. One worktree was **captured** (read-only copy). **No worktree was deleted.** `work/` remains 98 trees / 56 dirty. Nothing under `.pm/` was written by this note.

---

## 1. What was approved and done

The operator approved action **(a)**: run the REC-02 capture on **one** dirty
tree, inspect the output, and confirm it reads back, before any reclaim
(REC-01) is enabled.

Done:

1. Implemented REC-02 capture (commits `b08ca64`, `dcb24df`, `ee960c2`).
2. Selected the most representative dirty tree, **`work/T-0131-110`**, and
   captured it into **`stranded/T-0131-110/`** (additive copy only).
3. Verified the capture independently (Section 4).
4. Found and fixed **two newline-fidelity defects** in the first REC-02 code
   that made the captured patch non-applicable (Section 3). These would not
   have been visible from `verify_archive()` alone.

## 2. The captured tree and archive

`work/T-0131-110` is a real git worktree (branch `pmk/T-0131-110` @
`77a56db`), state `VOID`, and was the richest dirty tree: **2 tracked
modifications + 66 untracked files** — it exercises every path of the
capture code.

| Archive file | Size | Content |
|---|---:|---|
| `diff.patch` | 14,840 B | `git diff HEAD --binary` (tracked changes: `docs/rules/checksums.sha256`, `docs/rules/manifest.json`) |
| `untracked.tar` | 870,400 B | 66 untracked files (the CNA rules corpus, `docs/rules/**`) |
| `RESULT.md` | 3,657 B | copy of the agent's `.pmwork/RESULT.md` |
| `manifest.json` | 3,382 B | task, fence, base commit `77a56db`, counts and SHA-256s |

The capture **only copied**: the source worktree's `git status` fingerprint was
**identical before and after** (`a79a904a51e209cbbee2e0888f67ea02eb271ab3`).

## 3. Defects found and fixed (in the REC-02 code)

Both were silent: the archive looked correct and `verify_archive()` passed,
because it only hashes *what was written* — it does not check that the patch
*applies*.

- **D-1 — text-mode write corrupted the patch.** `Path.write_text()`
  translated `"\n"` to the platform separator, inflating the LF diff to CRLF
  on Windows (14,994 → +165 bytes; one per line).
- **D-2 — text-mode read stripped CRs.** `Repo.git()` decodes git stdout in
  Python text mode, which applies universal-newline translation and *silently
  strips the CR from CRLF*. `docs/rules/**` is stored with CRLF
  (`.gitattributes` marks it `-text`), so the captured pre-image lost **11
  CRs** and no longer matched its base. For `work/T-0131-110`, git's raw diff
  is 14,840 bytes with 11 CRLF lines; the capture was 14,829 bytes with 0.

Fix: added `Repo.git_bytes()` (raw stdout/stderr bytes) and made
`archive_tree()` read the diff/base/untracked list through it and write
`diff.patch` / `manifest.json` with `write_bytes()`. Regression tests assert
byte-identity against git's own `git diff` and a CRLF round-trip.

## 4. Verification of `stranded/T-0131-110/`

| # | Check | Result |
|---|---|---|
| 1 | `verify_archive()` SHA-256s vs `manifest.json` | OK |
| 2 | Independent SHA-256 recompute (both files) | OK |
| 3 | Every one of the 66 untracked members byte-matches the live file | OK (0 missing, 0 mismatch) |
| 4 | `RESULT.md` copy matches the live `.pmwork/RESULT.md` | OK |
| 5 | Patch reverse-applies to its own worktree | OK |
| 6 | **Forward round-trip**: fresh checkout of base `77a56db` + `diff.patch` reproduces the live tracked files | **OK** |
| 7 | Source worktree still registered and unchanged | OK |

Checks 5–6 fail on the pre-fix capture (D-1/D-2) and pass after the fix.

## 5. Safety state (unchanged)

- `work/` = **98 trees / 56 dirty**; `work/T-0131-110` byte-unchanged.
- Project **`PAUSED`**; no `.pm/` event was written by this work.
- Sentinel unchanged: `ok=False`, five `I6` findings; `I5` empty-commit still
  cleared; `I17` silent (886 MiB < 2048 MiB cap).

## 6. Open items and recommendations

1. **REC-01 (reclaim) remains gated.** It should not ship until this capture
   path is confirmed by the operator against `stranded/T-0131-110/` and the
   `git apply` round-trip.
2. **Broader finding (advisory, out of scope):** `Repo.git()` strips CRs for
   *all* callers. Any other consumer that hashes or reproduces git stdout
   byte-for-byte (for example evidence-bundle stdout hashes) may be affected
   by the same translation. This was **not** changed — doing so would alter
   recorded hashes — but it is recommended for a separate review.
3. **`stranded/` was only validated on one tree.** A capture sweep of the
   remaining 55 dirty trees should be verified (dry run first, then capture)
   before any reclaim.
4. The incident report / proposal were **not edited** by this note; a status
   update to them is at the operator's discretion.

---

## Addendum (2026-11-08): REC-01 implemented, off by default

With the capture gate confirmed above, REC-01 (reclaim a bumped lease's
worktree) was implemented in commit `866a166`:

- `worktrees.reclaim_after_capture()` is the single deletion path: it
  archives the tree (REC-02), **verifies the archive**, and only then runs
  `git worktree remove --force`. A tree whose capture does not verify is
  **kept**.
- The reaper (`Conductor._reap_one`) calls it after a successful revoke and
  records `WORKTREE_RECLAIMED`. It never raises, so a reclaim failure
  cannot undo the revoke.
- It is gated by policy `worktree.reclaim_on_reap`, **default `false`**, and
  in this repository it is **off** (the pinned `policy.toml` `[worktree]`
  table does not set it). **No worktree was removed by this commit.**

Scope: the give-up/quarantine path still keeps its worktree on purpose
(the harness docstring and the incident report both say so); REC-01 here
targets the dominant TTL-expiry reclaim. Give-up trees remain covered by
the manual `pmk worktree prune --archive --yes`.

To enable it, an operator edits `[worktree]` in the pinned `policy.toml`
(a class-K, two-key change) and sets `reclaim_on_reap = true`.

---

## Addendum 2 (2026-11-08): capture sweep of every dirty tree

Operator approved action (a): a **capture sweep, no reclaim**.

- **Dry run** listed **56** targets — every dirty tree.
- **Capture**: `pmk worktree archive --all-dirty` archived **56 / 56**
  (`count: 56`, no failures).
- **Verification** of every archive (read-only): **56 / 56 fully verified**
  — `verify_archive()` SHA-256s, `diff.patch` **byte-identical** to
  `git diff HEAD` for its own tree, and **every** untracked member
  byte-matches the live file. **460** untracked files captured.
- **`stranded/`** now holds **56 trees, 4.82 MiB** total.
- **`work/` unchanged**: the global status fingerprint is identical before
  and after (`876f521335dca4f4c6a77d1019e1c18402d9fe04c0dc6a339d2562ee0ff98c31`),
  98 trees / 56 dirty, **nothing reclaimed**.
- State: project `PAUSED`; `worktree.reclaim_on_reap` still `false`.

Every dirty tree's uncommitted work is now captured and independently
verifiable. REC-01 may now be enabled by the operator without further
capture work (the archives are retained indefinitely).

---

*Provenance: authored by DeepSeek V4.1 Flash (`deepseek-ai/deepseek-v4.1-flash`, nvidia). Not an independent assessment — the author also implemented the code described. No promotion or reclassification is made or implied.*
