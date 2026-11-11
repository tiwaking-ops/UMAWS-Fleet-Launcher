---
title: "Worktree scratch prune — operator run report"
version: "1.0.0"
date: "2026-11-12"
author_llm: "DeepSeek V4.1 Flash (deepseek-ai/deepseek-v4.1-flash, nvidia)"
scope: "the residual, non-lease worktree scratch left after the REC-01/02 remediation"
---

# Worktree scratch prune — operator run report

Operator instruction: *"enable reclaim and watch the first few reaps"*, then, for
the cleanup, **(a) APPROVED — reason: project repo repair and pruning required**,
and on the mechanism question, **"extend the sanctioned path, then run it"**.

## 1. The honest finding first: the reaper never fired

REC-01 (`worktree.reclaim_on_reap`) is **enabled and green** — class-K item
**Q-077**, pins re-recorded (I8'), views regenerated (I13), 494 tests at the
time. But it has **never reclaimed anything on the live repo**:

| Signal | Count in the live log |
|---|---|
| `WORKTREE_RECLAIMED` / `WORKTREE_RECLAIM` | **0 / 0** |
| `LEASE_REAPED` (the reaper's own event) | **0** |
| `LEASE_EXPIRED` (emitted by code *not in this tree*) | 58 |
| `REVOKED` (operator revokes) | 115 |

The earlier 98 → 8 drop in `work/` came from a **manual `pmk worktree prune`**,
which emits no reclaim event — not from the reaper. The reclaim predicate was
also independently rewritten by the fleet (`a1d301c`, "only an active lease may
refuse"); my REC-01 commit stays an ancestor and wired, but the code that ran
the pruning was a different path.

## 2. Why there was nothing for the reaper to reap

`Conductor.expired_leases()` is empty: the project is `RUNNING` with **0 active
leases**. And the residual trees were **not lease worktrees at all**:

* eight `work/` trees with canary/gate names (`gate-*`, `H1-H4-*`,
  `launcher-repair-*`, `legacy-launcher-cwd-fallback-*`);
* the `%TEMP%/pmk-merge-*` trees.

`pmk worktree prune` refuses the first class by name ("not a lease worktree
name"), and merge trees were "reported for visibility but never removed"
(the H7 defect, card **T-0195**). So "repo repair and pruning" was **not
reachable through the sanctioned path** — that is why the operator chose to
extend it rather than bypass it.

## 3. The change (two commits)

**`772e1bc` — reclaim non-lease scratch worktrees, capture-first.** Extends the
one deletion path instead of bypassing it: `reclaim_after_capture` gains
`allow_scratch/root/stem/remove_parent`; `_deletion_refusal` permits a non-lease
name only under an explicit root and only with `allow_scratch` (protected names,
symlinks and out-of-root paths are still refused); `prune_scratch` drives both
classes, dry-run by default; the CLI exposes
`pmk worktree prune --scratch --merge-trees`; an applied run records
`WORKTREE_SCRATCH_PRUNED`.

**`e477c5f` — scope to this repo, and never race a merge.** `%TEMP%/pmk-merge-*`
is a **global** namespace: a live `pytest` and a separate `pmk ... project run`
on another repository (`umaws-noscope-toy`) were both creating trees in it while
this work was being written. So a merge tree is now a candidate only when
`belongs_to_repo` proves its worktree's common git dir is **this** repo's
`.git`, **and** it is at least `min_merge_age_days` old (default 1). A directory
with no merge worktree cannot be proven ours, so it is left alone. This also
dropped the raw-directory capture: a scratch reclaim now always goes through a
git worktree this repository owns, so REC-02 and `verify_restore` always apply.

## 4. The run

Applied with `pmk worktree prune --scratch --yes` and
`pmk worktree prune --merge-trees --yes`. **18 trees reclaimed, 18 archives,
all verified; nothing deleted whose capture did not verify.**

| Class | candidates | reclaimed | skipped |
|---|---|---|---|
| `work/` scratch (canary/gate) | 8 | **8** | 0 |
| `%TEMP%/pmk-merge-*` (this repo's) | 10 | **10** | 15 |

The 15 skips are **foreign or unprovable**, and are deliberately kept — 14 are
another repository's / a test run's merge scratch, 1 has no merge worktree.

Reclaimed: `gate-1794216849`, `gate-1794219368`, `gate-e7d2725-1794222600`,
`h1-h4-branch-1794218000`, `H1-H4-clean-1794215552`, `H1-H4-clean-1794218904`,
`launcher-repair-clean-1794220000`, `legacy-launcher-cwd-fallback-1794222000`,
and merge trees `3osjhcw2`, `cvq31iha`, `dciu4suz`, `e0p8986h`, `gku44cl4`,
`hbl3vdbg`, `k6ls53bl`, `m2sanimo`, `oo2s1qwx`, `poc6l9gt`.

Each archive is under `stranded/<name>/` (`diff.patch`, `untracked.tar`,
`manifest.json`), verified by `verify_archive`. Two log records:

* `WORKTREE_SCRATCH_PRUNED` seq 3645 — `{candidates: 8, removed: 8, skipped: 0}`
* `WORKTREE_SCRATCH_PRUNED` seq 3646 — `{candidates: 10, removed: 10, skipped: 15}`

## 5. Verification

| Check | Result |
|---|---|
| `work/` after | **0 trees** (was 8 / 137.6 MiB) |
| this repo's `%TEMP%/pmk-merge-*` after | **0** (~107.8 MiB freed) |
| `git worktree list` | the 10 temp merge trees are gone |
| `git worktree prune -n -v` | silent — admin entries consistent |
| `stranded/` | 115 archives, 65 MiB (was 97 / 27 MiB) |
| archive spot-check (`verify_archive`) | all OK |
| chain | `I1 chain verifies (3646 events)` |
| sentinel (read-only) | `ok=True`, **no findings** |
| full suite (pre-run) | **1332 passed, 1 skipped** |

The shared working tree also carried **another agent's uncommitted work**
(`src/cna/*`, `src/console/app.py`, and, at the time, `cli.py`). The `cli.py`
change was staged **hunk-by-hunk** (`git apply --cached` on a filtered patch) so
that none of it entered these commits; it is still present, untouched. The
`work/` and merge trees reclaimed here are separate worktrees — the main
checkout and every other agent's files were not affected.

## 6. Out of scope / still open

* `tmp/` (172 MiB of repo-local canary/precheck/reviewer scratch) and
  `.claude/worktrees/agent-a8ea…` were **not** touched.
* `%TEMP%/pmk-precheck-dry-*` and the foreign/orphan `%TEMP%/pmk-merge-*` dirs
  were reported and left alone.
* The root cause of the *orphan* merge dirs is test hygiene: `fleet/merge.py`
  uses `tempfile.mkdtemp(prefix="pmk-merge-")` rather than a pytest-managed
  temp dir, so a test that does not reach its cleanup leaks a tree into the
  global `%TEMP%`. Worth a separate fix.
* The reaper itself still only acts on expired **leases**; that is unchanged and
  correct.

---

*Provenance: authored by DeepSeek V4.1 Flash (`deepseek-ai/deepseek-v4.1-flash`,
nvidia). Not an independent assessment — the author also wrote the code and ran
the prune. No promotion or reclassification is made or implied.*
