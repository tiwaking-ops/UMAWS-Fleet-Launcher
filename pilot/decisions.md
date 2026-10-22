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

---

## Pending

- **Gate rule** — the operator was asked whether the implementing agent must
  stop at G0–G3 and replied "I will provide these". Until the rule arrives,
  the pilot v1 §12.1 default applies: **hold**. No gate is crossed silently.
