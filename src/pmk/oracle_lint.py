"""Oracle linting (fleet amendment: oracle safety).

Parses each oracle exactly as the harness will run it (shell=True on Windows,
which invokes cmd.exe). Compiles any `python -c` payload and rejects:
- single-quoted `python -c` payloads (cmd.exe does not treat single quotes as quoting)
- nested double quotes that close the outer string early
- backslash-escaped quotes (`\"`) inside `python -c` when the payload or the
  rest of the command contains shell metacharacters (& | < > ^ %)
  because cmd.exe toggles quote state on EVERY `"`, escaped or not.
- percent signs (`%`) inside `python -c` payload (cmd.exe expands %var% even inside quotes),
  even when the `%` would only be a Python modulo operator in the payload code
- syntax errors in the python code

Python interpreter invocations are recognized with or without a path prefix:
unquoted (C:\\Python\\python.exe, /usr/bin/python3) or quoted to allow spaces
("C:\\Program Files\\Python\\python.exe"), with optional interpreter flags
between the interpreter and -c (for example -u, -B, -3, -X utf8).

Errors are raised, not warnings. This runs at task creation/admission, BEFORE any claim.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass


@dataclass
class OracleLintResult:
    oracle: str
    ok: bool
    error: str = ""
    parsed_cmd: str = ""
    python_code: str = ""


# Shell metacharacters that cmd.exe interprets even inside quoted strings
# when a backslash-escaped quote precedes them.
SHELL_METACHARS = set("&|<>^%")

# Regex to detect Python interpreter invocations followed by -c.
# Matches:
#   python, python3, python3.12, python.exe, py, py.exe
#   with optional path prefix, either unquoted (C:\Python\python.exe, /usr/bin/python3)
#   or quoted to allow spaces ("C:\Program Files\Python\python.exe"); single-quoted
#   paths are matched too, and their payload is linted as well.
#   and optional interpreter flags between the interpreter and -c
#   (for example -u, -B, -3, -q, -E, -I, -s, -X utf8).
# The start anchor matches: beginning, ||, &&, ;, |, & (not &&).
PYTHON_INTERPRETER_RE = re.compile(
    r'(?:^|\|\||&&|[;&|]|&(?!&))\s*'   # Start: beginning, ||, &&, ;, |, & (not &&)
    r'(?:'
    r'"[^"]*(?:python(?:3(?:\.\d+)?)?|py)(?:\.exe)?"'   # double-quoted path, interpreter at end
    r'|'
    r"'[^']*(?:python(?:3(?:\.\d+)?)?|py)(?:\.exe)?'"   # single-quoted path, interpreter at end
    r'|'
    r'(?:[a-zA-Z]:[\\/])?(?:[^\\/\s;&|;"\']+[\\/])*(?:python(?:3(?:\.\d+)?)?|py)(?:\.exe)?'  # unquoted path
    r')'
    r'(?:\s+-(?:X\s+[A-Za-z0-9_.-]+|[A-Za-z0-9][A-Za-z0-9_.-]*))*' # interpreter flags: -u, -B, -3, -3.12, -X utf8, ...
    r'\s+-c\s+',
    re.IGNORECASE
)


def lint_oracle(oracle: str) -> OracleLintResult:
    """Lint a single oracle command as it would run under shell=True on Windows.

    The harness runs commands with:
        subprocess.run(command, shell=True, cwd=worktree, ...)

    On Windows, shell=True invokes cmd.exe /c. The command parsing follows
    cmd.exe rules: double quotes are used for quoting, single quotes are literal.

    Returns OracleLintResult with ok=True if the oracle is safe, False otherwise.
    """
    # Check for python -c payloads (using general interpreter detection)
    # Check ALL python -c occurrences in the oracle
    for match in PYTHON_INTERPRETER_RE.finditer(oracle):
        result = _lint_python_c_single(oracle, match)
        if not result.ok:
            return result

    # Basic validation: the command should not be empty
    if not oracle.strip():
        return OracleLintResult(
            oracle=oracle,
            ok=False,
            error="oracle command is empty",
            parsed_cmd=oracle
        )

    return OracleLintResult(oracle=oracle, ok=True, parsed_cmd=oracle)


def _lint_python_c_single(oracle: str, match: re.Match) -> OracleLintResult:
    """Lint a single python -c occurrence in the oracle."""
    prefix_end = match.end()
    if prefix_end >= len(oracle):
        return OracleLintResult(oracle=oracle, ok=True, parsed_cmd=oracle)
    
    quote_char = oracle[prefix_end]
    if quote_char not in ('"', "'"):
        return OracleLintResult(oracle=oracle, ok=True, parsed_cmd=oracle)
    
    # Parse the quoted string properly, handling escaped quotes
    inner_start = prefix_end + 1
    inner_end = None
    i = inner_start
    while i < len(oracle):
        if oracle[i] == quote_char:
            # Check if escaped
            if i == 0 or oracle[i-1] != '\\':
                inner_end = i
                break
        i += 1
    
    if inner_end is None:
        return OracleLintResult(
            oracle=oracle,
            ok=False,
            error=f"python -c payload has no closing {quote_char} quote",
            parsed_cmd=oracle,
            python_code=oracle[inner_start:]
        )
    
    inner = oracle[inner_start:inner_end]
    
    # Reject single-quoted payloads on Windows
    if quote_char == "'":
        return OracleLintResult(
            oracle=oracle,
            ok=False,
            error=("python -c payload uses single quotes; "
                   "cmd.exe on Windows does not treat single quotes as quoting. "
                   "Use double quotes instead."),
            parsed_cmd=oracle,
            python_code=inner
        )
    
    # Reject percent signs inside the payload (cmd.exe expands %var% even inside quotes)
    if '%' in inner:
        return OracleLintResult(
            oracle=oracle,
            ok=False,
            error=("python -c payload contains a percent sign (%). "
                   "cmd.exe expands %var% even inside double quotes. "
                   "Use a committed script file instead."),
            parsed_cmd=oracle,
            python_code=inner
        )
    
    # B-R3b: Check for backslash-escaped quotes followed by shell metacharacters
    # cmd.exe toggles quote state on EVERY ", even \". So if the payload
    # contains \" and then a shell metacharacter (& | < > ^ %), the metacharacter
    # will be interpreted by cmd.exe as an operator.
    backslash_quote = '\\"'  # backslash followed by double quote
    if backslash_quote in inner:
        # Check the inner payload for shell metacharacters after \"
        parts = inner.split(backslash_quote)
        for part in parts[1:]:  # parts after each \"
            if any(ch in part for ch in SHELL_METACHARS):
                return OracleLintResult(
                    oracle=oracle,
                    ok=False,
                    error=(
                        r"python -c payload contains a backslash-escaped quote (\") "
                        "followed by a shell metacharacter (& | < > ^ %). "
                        "cmd.exe toggles quote state on every \" (even escaped), "
                        "so the metacharacter will be interpreted outside the string. "
                        "Use a committed script file instead, or avoid shell metacharacters "
                        "after escaped quotes."
                    ),
                    parsed_cmd=oracle,
                    python_code=inner
                )
        # Also check the rest of the command after the closing quote
        after_closing = inner_end + 1
        # Check the entire rest of the oracle for shell metacharacters
        # (don't truncate at command separators, as they may appear inside strings)
        trailing = oracle[after_closing:]
        if any(ch in trailing for ch in SHELL_METACHARS):
            return OracleLintResult(
                oracle=oracle,
                ok=False,
                error=(
                    r"python -c payload contains a backslash-escaped quote (\") "
                    "and the rest of the command contains shell metacharacters "
                    "(& | < > ^ %). cmd.exe will interpret these outside the string. "
                    "Use a committed script file instead."
                ),
                parsed_cmd=oracle,
                python_code=inner
            )
    
    # For double-quoted, check for unescaped nested double quotes
    # in the ORIGINAL oracle string after the opening quote
    # Look at the region from inner_start to inner_end in the original oracle
    # If there are unescaped double quotes in this region, it's a nested quote error
    # (The parser above would have stopped at the FIRST unescaped quote, so if
    # inner_end is not the true closing quote, there will be more quotes after)
    
    # Check if there are more unescaped double quotes after the closing quote
    # up to the next command separator or end of string
    after_closing = inner_end + 1
    separators = ['&&', '||', ';', '|', '\n', '\r']
    cmd_end = len(oracle)
    for sep in separators:
        pos = oracle.find(sep, after_closing)
        if pos != -1 and pos < cmd_end:
            cmd_end = pos
    
    # Check the region after the closing quote for unescaped double quotes
    # Only up to the next command separator (don't include other commands)
    trailing = oracle[after_closing:cmd_end]
    unescaped_trailing = 0
    j = 0
    while j < len(trailing):
        if trailing[j] == '"' and (j == 0 or trailing[j-1] != '\\'):
            unescaped_trailing += 1
        j += 1
    
    if unescaped_trailing > 0:
        return OracleLintResult(
            oracle=oracle,
            ok=False,
            error=(f"python -c payload contains {unescaped_trailing} "
                   f"unescaped nested double quote(s) after the apparent "
                   f"closing quote. This indicates the quotes are not properly "
                   f"escaped and will break under cmd.exe."),
            parsed_cmd=oracle,
            python_code=inner
        )
    
    # Also check the inner code itself for unescaped quotes (should be 0 if properly escaped)
    unescaped_inner = 0
    k = 0
    while k < len(inner):
        if inner[k] == '"' and (k == 0 or inner[k-1] != '\\'):
            unescaped_inner += 1
        k += 1
    
    if unescaped_inner > 0:
        return OracleLintResult(
            oracle=oracle,
            ok=False,
            error=(f"python -c payload contains {unescaped_inner} "
                   f"unescaped nested double quote(s) inside the argument. "
                   f"These must be escaped with backslash to work under cmd.exe."),
            parsed_cmd=oracle,
            python_code=inner
        )

    # Try to compile the python code to catch syntax errors
    # Unescape cmd.exe-style escapes (\" -> ", \\ -> \) before compiling
    try:
        inner_unescaped = inner.replace('\\"', '"').replace('\\\\', '\\')
        compile(inner_unescaped, "<oracle>", "exec")
    except SyntaxError as exc:
        return OracleLintResult(
            oracle=oracle,
            ok=False,
            error=f"python -c payload has syntax error: {exc}",
            parsed_cmd=oracle,
            python_code=inner
        )

    return OracleLintResult(oracle=oracle, ok=True, parsed_cmd=oracle)


def lint_oracles(oracles: list[str]) -> list[OracleLintResult]:
    """Lint a list of oracles. Raises ValueError if any oracle fails."""
    results = [lint_oracle(o) for o in oracles]
    failures = [r for r in results if not r.ok]
    if failures:
        error_msgs = [f"  {r.oracle}: {r.error}" for r in failures]
        raise ValueError("Oracle lint failed:\n" + "\n".join(error_msgs))
    return results


def lint_oracles_at_admission(oracles: list[str]) -> list[str]:
    """Lint oracles at task admission time. Returns list of error messages (empty if all ok).

    This is called at task creation/admission, NOT after claim.
    """
    try:
        lint_oracles(oracles)
        return []
    except ValueError as exc:
        return [str(exc)]


if __name__ == "__main__":
    # CLI for testing
    if len(sys.argv) < 2:
        print("Usage: python -m pmk.oracle_lint 'oracle command'")
        sys.exit(1)
    oracle = " ".join(sys.argv[1:])
    result = lint_oracle(oracle)
    if result.ok:
        print(f"OK: {oracle}")
    else:
        print(f"FAIL: {result.error}")
        sys.exit(1)
