# S-A1 — CLI matrix (metadata only)

**Date:** 2026-10-22 · **Verdict:** `unknown` for behaviour, `works` for invocation

> **Scope limit (operator decision D-03).** The operator chose **metadata-only**
> probing: `--help` and `--version` are captured, and **no prompt is ever sent
> to a real provider**, so no free-tier quota is burned. Every behavioural
> column below is therefore `UNVERIFIED`, and the code is written to degrade
> safely on that basis.

## Versions (captured)

| CLI | Version | Installed as | `--version` exit |
|---|---|---|---|
| hermes | `Hermes Agent v0.22.2 (2026.9.24) · stable · local d923a5eb487a` | `hermes.exe` (native) | 0 |
| kilo | `7.8.12` | `kilo.cmd` → node script | 0 |
| cline | `3.0.71` | `cline.cmd` → node script | 0 |
| pi | `1.2.0` | `pi.cmd` → `pi-launcher.js` | 0 |
| opencode | `opencode v2.1.0` | `opencode.cmd` → `opencode.exe` | 0 |

## Invocation path (measured — this part is solid)

| CLI | Resolved by `plat` | Launch argv |
|---|---|---|
| hermes | `native` | `hermes.exe <args>` |
| kilo | `node` | `node …\@kilocode\cli\bin\kilo <args>` |
| cline | `node` | `node …\cline\bin\cline <args>` |
| pi | `node` | `node …\pi-launcher.js <args>` |
| opencode | `native` (peeled from `.cmd`) | `…\@opencode\cli\bin\opencode.exe <args>` |

Arguments survive intact (13/13 hostile-payload arguments byte-identical) —
see `pilot/spikes/s-p1-platform.md` and `pilot/spikes/shim_argv_test.py`.

## Behavioural matrix — all UNVERIFIED

| Question | hermes | kilo | cline | pi | opencode |
|---|---|---|---|---|---|
| Headless (no TTY) possible? | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| TTY required? | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| Session id shown or stored? | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| Resume command? | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| Model change on resume? | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| Exit codes on failure? | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| Quota failure text? | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| Auth failure text? | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| Network failure text? | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| Dead-model text? | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| Prompt from file or stdin? | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |

## Consequences written into the code

1. **Adapter caps default to `False`** (fleet §12.B): `headless`,
   `can_resume`, `can_swap_model_on_resume`, `reports_session_id` are all
   `False` until a real capture says otherwise.
2. **No classifier pattern is loaded.** Per fleet §7.5, a pattern may only be
   added from a captured fixture. With no fixtures, **every non-zero exit is
   `UNKNOWN`**, and the `UNKNOWN` path (retry once, cool after two in ten
   minutes) is the only path that has to be safe.
3. **Recovery ladder L1/L2 are unreachable in practice.** L1 needs a resume
   with a model change; L2 needs a fresh session with a handoff note. Both
   are implemented, but with `can_resume = False` the ladder falls to L3
   (revoke, bump fence, quarantine, return to READY) — which is the correct
   and safe outcome.
4. **The prompt is a fixed ASCII sentence.** D-L7's order file carries the
   real instructions; the CLI receives
   `Read .pmwork/ORDER.md and carry out the task exactly as written.` This is
   also what makes F11 pass regardless of the CLI's own quoting behaviour.
5. **`--help` output captured** to `pilot/spikes/cli-help/<cli>-help.txt`.
   Only `hermes` produced output through the naive `Start-Process` route
   (14 216 bytes); the `.cmd` shims cannot be started that way at all
   ("%1 is not a valid Win32 application"), which is itself the evidence for
   the node-direct bypass.

## Fixtures

`tests/fleet/fixtures/<adapter>/` will contain fixtures **only** for the fake
CLI until real captures exist. Real adapters never reuse the fake's fixtures
(fleet §12.E).
