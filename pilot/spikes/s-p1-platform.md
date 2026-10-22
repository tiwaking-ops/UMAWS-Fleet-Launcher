# S-P1 — Platform spike (Day 1, gate G0)

**Date:** 2026-10-22 · **Verdict:** `works` · **Decides:** platform = native Windows (D-02)

## Question (fleet amendment §5)

Python ≥ 3.11 available? Git for Windows ≥ 2.28? Node present? Is WSL
installed? Can a lock test survive **20 processes appending to one file under
`msvcrt.locking` with retry** with no torn lines? Are long paths enabled?

## Results — all measured on the operator's machine

| Check | Result | Verdict |
|---|---|---|
| `py -0p` | 3.14 (default), 3.12, 3.11 present | pass |
| `python --version` | 3.12.10 | pass |
| `tomllib` import (needs ≥ 3.11) | OK | pass |
| `git --version` | 2.55.0.windows.3 (≥ 2.28) | pass |
| `node --version` | v26.7.0 | pass |
| `npm --version` | 12.0.2 | pass |
| `wsl --status` | installed, **default distribution `docker-desktop`**, default version 2 | no usable Linux dev distro |
| `HKLM\...\FileSystem\LongPathsEnabled` | `1` | pass |
| `git config core.longpaths` | unset globally → set **locally** by this repo | fixed |
| `pwsh` | **absent** | only Windows PowerShell 5.1 |
| `powershell` | `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe` | pass (5.1 only) |
| `caliber` | **absent** | see below |
| `uv` | present | pass |
| `docker` | CLI present | pass |
| `sqlite3` CLI | absent | not needed (Python's `sqlite3` module) |

## Lock test — the interesting part

`pilot/spikes/lock_test.py`, 20 processes × 25 appends = 500 records.

### First run: `does-not-work`

```
actual total lines : 500
unique record ids  : 500
torn/short lines   : 275
worker errors      : 20 × PermissionError
```

**Root cause (measured, not guessed).** The lock was taken on byte 0 of the
event log, and the appends went to the same file. **Windows enforces
byte-range locks against writes**: an append to an empty file lands on byte 0,
which is the locked byte, so the write fails with `PermissionError`.

### Second run: `does-not-work` (bad verdict, working mechanism)

```
actual total lines : 500   unique record ids : 500   missing : 0
torn/mismatched    : 500   worker errors : 0   hanging : 0   elapsed : 3.17s
```

The mechanism was already correct — 500 records, no duplicates, no loss, no
hangs. The *validator* was wrong twice: first it assumed a fixed 4-digit
record id (ids are 1–4 digits), then it used a regex that did not allow for
the payload's `ljust()` trailing spaces. The spike was rewritten to compare
against an exactly-built set of expected records.

### Third run: `works`

```
processes : 20    lines per process : 25    expected : 500
actual    : 500   unique ids : 500   torn : 0   missing : 0
malformed : 0     worker errors : 0  hanging : 0  elapsed : 3.17s
VERDICT: works
```

### Conclusion carried into the code

`src/pmk/plat.py` locks a **sidecar** file (`<file>.lock`), never the data
file. Recorded as decision **D-04** so a later implementer does not
"simplify" the sidecar away.

## Additional finding — npm shims (drives D-L7 and test F11)

The operator's five CLIs are installed as npm shims:

| CLI | `shutil.which` finds | Real target |
|---|---|---|
| hermes | `hermes.EXE` (native) | — |
| kilo | `kilo.CMD` | `node …\@kilocode\cli\bin\kilo` |
| cline | `cline.CMD` | `node …\cline\bin\cline` |
| pi | `pi.CMD` | `node …\pi-launcher.js` |
| opencode | `opencode.CMD` | `…\@opencode\cli\bin\opencode.exe` (native, wrapped) |

`PATHEXT` contains `.CMD` but not `.PS1`, so Python finds the `.cmd` shim.
Its last line is `%*`, which means **cmd.exe re-parses every argument**.

`pilot/spikes/shim_argv_test.py` measured a hostile payload (quotes, `%`,
`&`, `^`, `|`, `;`, `*`, `?`, parens, braces, non-ASCII):

| Launch style | Result |
|---|---|
| `cmd.exe /d /s /c <shim> <args>` | **MANGLED** — `%PATH%` expanded to the entire PATH |
| `cmd.exe /d /c call <shim> <args>` | **MANGLED** — `%PATH%` expanded, `^` became `^^` |
| `node <script> <args>` (bypass) | **INTACT** — 13/13 arguments byte-identical |

All four real CLIs run correctly through the bypass (`kilo` 7.8.12, `cline`
3.0.71, `pi` 1.2.0, `opencode` v2.1.0).

**Therefore the Fleet resolves `.cmd` shims to their underlying node script or
native executable and launches that directly with an argv list**
(`plat.resolve_executable` / `plat.argv_for_executable`). This satisfies fleet
rule 16 ("argv, not shell strings") in the strict sense and is what makes test
F11 pass. The `cmd.exe` path remains only as a degraded fallback and is
reported as degraded in the Console.

## Platform decision

**Native Windows** (decision D-02). Reasons:

1. The operator's four CLIs already run in PowerShell against `C:\` paths.
   Moving to WSL means reinstalling and re-authenticating them in an
   environment the operator does not understand.
2. WSL is installed but its default distribution is `docker-desktop` — there
   is no Ubuntu to develop in.
3. The portability worry that motivated WSL (no `fcntl` on Windows) is
   handled: `plat.py` implements portable locking, and the measured result is
   that it works.

WSL remains possible; `plat.py` is the only file that would change.

## Stop conditions raised

- **Caliber is not installed** (`caliber` absent from PATH). Pilot v1 WP1
  spike S1 cannot run, and `npm install -g @rely-ai/caliber` is a global
  install that pilot v1 rule 6 forbids without asking. → **gate G1**.
- **`pwsh` absent.** The legacy manual-launcher path falls back to Windows
  PowerShell 5.1, which `LLM-Prompt-Launcher-App.py` already handles
  (`shutil.which("pwsh") or shutil.which("powershell")`). Not a blocker.
