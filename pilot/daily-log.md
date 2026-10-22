# Daily log (pilot v1 Appendix C3)

## Day 1 — 2026-10-22

**Planned:** WP0 environment and scaffold; spike S-P1 (platform); read all four
source specifications; begin WP2 Kernel-lite core.

**Actual:** WP0 complete. S-P1 run with two real findings (the sidecar lock
constraint and the npm-shim argument mangling). S-A1 metadata-only capture.
All four source specifications obtained from the operator mid-build, so
QuotaGate and the Caliber integration are built from their real specs rather
than reconstructed.

**Tested:**
- `py -3.12 pilot/spikes/lock_test.py` → `works`; 20 processes × 25 appends =
  500/500 records, 0 torn, 0 missing, 0 errors, 0 hangs, 3.17 s.
- `py -3.12 pilot/spikes/shim_argv_test.py` → `works`; hostile payload intact
  13/13 through the node-direct bypass, mangled through both `cmd.exe` forms;
  all four real CLIs verified through the bypass.
- `python -c "import tomllib"` → OK (Python 3.12.10).
- Pinned deps installed and frozen to `requirements.lock`.

**Assumed (not tested):**
- Every CLI's headless / resume / session-id / model-switch / failure-text
  behaviour. Operator chose metadata-only probing, so all of it is UNVERIFIED.
- That `~/.pi`, npm global prefix and the CLIs' own credentials keep working
  when a worker runs with a scrubbed environment. Direct profiles keep their
  own credentials (D-L3); gateway profiles are scrubbed.
- The `max_total_agents` value. S-W1 has not run; 20 is a placeholder.

**Incidents:**
- **Lock test hung** on the first run (120 s timeout). Cause: the lock was
  taken on byte 0 of the file being appended to, and Windows enforces
  byte-range locks against writes → `PermissionError`. Fixed by moving the
  lock to a sidecar file. Recorded as D-04.
- **Lock test reported a false negative twice** because the *validator* was
  wrong (fixed-width id assumption, then a regex that ignored `ljust()`
  padding). The mechanism was correct on the second run. Worth recording
  because a spike that only reports a verdict can hide a working mechanism
  behind a broken test.
- **Unicode mojibake in the shim spike** was a measurement artefact: stdout
  was decoded with the console's cp1252 instead of UTF-8. Fixed.

**Cuts:** none yet. WP2 is in progress.

**Tomorrow:** WP2 Kernel-lite core (events, state, tasks, leases, views,
briefing, sentinel, api), test-first, then WP4/WP11 Fleet runner v0 on the
fake CLI.
