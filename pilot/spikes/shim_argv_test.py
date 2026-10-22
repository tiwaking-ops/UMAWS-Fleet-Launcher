"""S-A1 / F11 spike: do arguments survive a Windows ``.cmd`` shim?

npm installs each CLI as three files: a POSIX ``sh`` shim, a ``.cmd`` shim and
a ``.ps1`` shim.  Python's ``shutil.which`` finds the ``.cmd`` one (PATHEXT
contains ``.CMD``), so every managed launch on this machine would go through
``cmd.exe``.

``cmd.exe`` re-parses the command line, so ``%VAR%`` expands, ``&`` splits
commands and ``^`` escapes.  The Fleet's rule 16 is "argv, not shell strings",
and the Fleet's acceptance test F11 requires a prompt-bearing argument
containing quotes, ``%``, ``&``, ``^`` and non-ASCII text to reach the
adapter intact.

This spike answers that with three invocations of the *same* payload through
three launch styles, plus a check that the real CLIs can be run with the
bypass.

Run:  py -3.12 pilot/spikes/shim_argv_test.py

Verdict printed as: works | does-not-work | unknown
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# The Windows console default is cp1252 and cannot print the unicode payload.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# A payload that exercises every character class F11 names, plus a couple
# that Windows cmd.exe is notorious for.
PAYLOAD = [
    'plain',
    'has "double quotes" inside',
    "has 'single quotes' inside",
    "100% of the time",
    "echo INJECTED & whoami",
    "caret ^ escape",
    "pipe | redirect > file",
    "semi ; colon",
    "unicode ünïcödé 中文",
    "percent %PATH% literal",
    "ampersand & more",
    "star * glob ?",
    "paren ( ) brace { }",
]

# npm's exact .cmd shape, reproduced faithfully.
NPM_SHIM = """@ECHO off
GOTO start
:find_dp0
SET dp0=%~dp0
EXIT /b
:start
SETLOCAL
CALL :find_dp0

IF EXIST "%dp0%\\node.exe" (
  SET "_prog=%dp0%\\node.exe"
) ELSE (
  SET "_prog=node"
)

endLocal & goto #_undefined_# 2>NUL || title %COMSPEC% & set PATHEXT=%PATHEXT:;.JS;=;% & "%_prog%"  "%dp0%\\fake.js" %*
"""

FAKE_JS = """
const args = process.argv.slice(2);
process.stdout.write(JSON.stringify(args));
"""


def run(argv: list[str], cwd: str | None = None,
        timeout: int = 60) -> tuple[int, str, str]:
    """Run *argv*, decoding stdout and stderr as UTF-8.

    Decoding matters: the Windows default locale encoding is cp1252, and
    decoding UTF-8 bytes as cp1252 turns "ünïcödé" into mojibake.  That is a
    measurement artefact, not a transport fault, and it would hide the real
    question (does the argument arrive intact?).
    """
    try:
        proc = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=timeout)
        return (proc.returncode,
                proc.stdout.decode("utf-8", errors="replace"),
                proc.stderr.decode("utf-8", errors="replace"))
    except (OSError, subprocess.SubprocessError) as exc:
        return -1, "", f"{type(exc).__name__}: {exc}"


def parse_echoed(out: str) -> list[str] | None:
    """The fake prints JSON.  cmd.exe may interleave its own noise."""
    start = out.find("[")
    end = out.rfind("]")
    if start == -1 or end == -1:
        return None
    try:
        parsed = json.loads(out[start:end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, list) else None


def build_fixture(tmpdir: str) -> tuple[str, str]:
    d = Path(tmpdir)
    (d / "fake.cmd").write_text(NPM_SHIM, encoding="utf-8")
    (d / "fake.js").write_text(FAKE_JS, encoding="utf-8")
    return str(d / "fake.cmd"), str(d / "fake.js")


def compare(label: str, got: list[str] | None) -> bool:
    if got is None:
        print(f"  {label:<28} UNPARSEABLE (cmd.exe noise or failure)")
        return False
    if got == PAYLOAD:
        print(f"  {label:<28} INTACT ({len(got)} args)")
        return True
    print(f"  {label:<28} MANGLED")
    for i, (want, have) in enumerate(zip(PAYLOAD, got)):
        if want != have:
            print(f"      arg[{i}]: want {want!r}")
            print(f"              got  {have!r}")
    if len(got) != len(PAYLOAD):
        print(f"      arg count: want {len(PAYLOAD)}, got {len(got)}")
    return False


def main() -> int:
    tmpdir = tempfile.mkdtemp(prefix="umaws-shim-spike-")
    shim, js = build_fixture(tmpdir)
    results: dict[str, bool] = {}

    print("=== argument survival, three launch styles ===")

    # (a) The naive cmd.exe form, as written in many tools.
    code, out, err = run(["cmd.exe", "/d", "/s", "/c", shim, *PAYLOAD])
    print(f"  [a] cmd.exe /d /s /c <shim>  exit={code}")
    results["cmd /d /s /c"] = compare("cmd.exe /d /s /c <shim>", parse_echoed(out))

    # (b) cmd.exe with `call`, the other common form.
    code, out, err = run(["cmd.exe", "/d", "/c", "call", shim, *PAYLOAD])
    print(f"  [b] cmd.exe /d /c call <shim> exit={code}")
    results["cmd /d /c call"] = compare("cmd.exe /d /c call <shim>", parse_echoed(out))

    # (c) The bypass: run the node script directly, never cmd.exe.
    code, out, err = run(["node", js, *PAYLOAD])
    print(f"  [c] node <script>             exit={code}")
    results["node direct"] = compare("node <script> (bypass)", parse_echoed(out))

    print()
    print("=== the real CLIs through the bypass ===")
    real = {
        "kilo": (r"C:\Users\Tiwa Pene\AppData\Roaming\npm\node_modules\@kilocode\cli\bin\kilo", "node"),
        "cline": (r"C:\Users\Tiwa Pene\AppData\Roaming\npm\node_modules\cline\bin\cline", "node"),
        "pi": (r"C:\Users\Tiwa Pene\.pi\agent\bin\pi-launcher.js", "node"),
        "opencode": (r"C:\Users\Tiwa Pene\AppData\Roaming\npm\node_modules\@opencode\cli\bin\opencode.exe", None),
    }
    bypass_ok = True
    for name, (target, runner) in real.items():
        if not Path(target).exists():
            print(f"  {name:<10} target missing: {target}")
            bypass_ok = False
            continue
        argv = ([runner, target] if runner else [target]) + ["--version"]
        code, out, err = run(argv, timeout=90)
        first = (out or err).strip().splitlines()[0] if (out or err).strip() else ""
        ok = code == 0
        bypass_ok = bypass_ok and ok
        print(f"  {name:<10} exit={code}  {first[:70]}")

    print()
    verdict_ok = results["node direct"] and bypass_ok
    print("results:", json.dumps(results, indent=2))
    print()
    print("VERDICT:", "works" if verdict_ok else "does-not-work")
    print()
    print("Conclusion: the Fleet MUST resolve npm .cmd shims to their")
    print("underlying node script or native executable and launch that")
    print("directly with an argv list.  Going through cmd.exe mangles")
    print("arguments, which would break Fleet rule 16 and test F11.")
    return 0 if verdict_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
