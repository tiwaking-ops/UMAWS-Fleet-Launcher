"""Tests for R3: Oracle lint (B9)"""

from __future__ import annotations

import pytest

from fleet.oracle_lint import lint_oracle, lint_oracles, lint_oracles_at_admission


# Oracle strings from T-0141, T-0142 (FAILING - nested double quotes)
# These are the exact strings from the ledger
T0141_ORACLE = 'python -m cna.tools.rules_index --check && python -c "import json; d=json.load(open("docs/rules/index.json")); assert d["stats"]["documents"] >= 66, d["stats"]"'
T0142_ORACLE = 'python -m cna.tools.coverage --check && python -c "import json; c=json.load(open("coverage/rules_coverage.json")); assert c["counts"]["rule_files"] >= 66, c["counts"]"'

# Oracle strings from T-0145, T-0146 (PASSING - double quotes with single quotes inside)
T0145_ORACLE = "python -m cna.tools.rules_index --check && python -c \"import json; d=json.load(open('docs/rules/index.json')); assert d['stats']['documents'] >= 66, d['stats']\""
T0146_ORACLE = "python -m cna.tools.coverage --check && python -c \"import json; c=json.load(open('coverage/rules_coverage.json')); assert c['counts']['rule_files'] >= 66, c['counts']\""

# Single-quoted payloads (should FAIL on Windows)
SINGLE_QUOTED_ORACLE = "python -c 'print(\"hello\")'"
SINGLE_QUOTED_WITH_DOUBLE_INSIDE = "python -c 'print(\"hello world\")'"

# Valid double-quoted payloads (inner quotes must be escaped or use single quotes)
VALID_DOUBLE_QUOTED = 'python -c "print(\\"hello\\")"'
VALID_DOUBLE_QUOTED_COMPLEX = 'python -c "import json; d=json.load(open(\'file.json\')); print(d)"'

# Syntax error in python code
SYNTAX_ERROR_ORACLE = 'python -c "import json; d=json.load(open(\'file.json\'); print(d)"'  # missing )

# Backslash-escaped quote followed by metacharacter (should FAIL)
BACKSLASH_QUOTE_METACHAR = r'python -c "print(\"a&b\")"'

# Percent sign in payload (should FAIL)
PERCENT_IN_PAYLOAD = 'python -c "print(100%)"'

# Various interpreter forms
PY312_ORACLE = 'python3.12 -c "print(\'ok\')"'
PYTHON_EXE_ORACLE = 'python.exe -c "print(\'ok\')"'
PY_ORACLE = 'py -c "print(\'ok\')"'
PATH_PYTHON_ORACLE = 'C:\\Python312\\python.exe -c "print(\'ok\')"'


def test_lint_t0141_fails_nested_double_quotes():
    """T-0141 oracle has nested double quotes that will fail under cmd.exe."""
    result = lint_oracle(T0141_ORACLE)
    assert result.ok is False
    assert "unescaped nested double quote" in result.error
    assert result.python_code != ""


def test_lint_t0142_fails_nested_double_quotes():
    """T-0142 oracle has nested double quotes that will fail under cmd.exe."""
    result = lint_oracle(T0142_ORACLE)
    assert result.ok is False
    assert "unescaped nested double quote" in result.error


def test_lint_t0145_passes():
    """T-0145 oracle uses double quotes with single quotes inside - valid."""
    result = lint_oracle(T0145_ORACLE)
    assert result.ok is True, f"Expected pass, got: {result.error}"


def test_lint_t0146_passes():
    """T-0146 oracle uses double quotes with single quotes inside - valid."""
    result = lint_oracle(T0146_ORACLE)
    assert result.ok is True, f"Expected pass, got: {result.error}"


def test_lint_rejects_single_quoted_payload():
    """Single-quoted python -c payloads are rejected on Windows."""
    result = lint_oracle(SINGLE_QUOTED_ORACLE)
    assert result.ok is False
    assert "single quotes" in result.error


def test_lint_rejects_single_quoted_with_double_inside():
    """Single-quoted python -c with double quotes inside is rejected."""
    result = lint_oracle(SINGLE_QUOTED_WITH_DOUBLE_INSIDE)
    assert result.ok is False
    assert "single quotes" in result.error


def test_lint_accepts_valid_double_quoted():
    """Valid double-quoted python -c payloads are accepted."""
    result = lint_oracle(VALID_DOUBLE_QUOTED)
    assert result.ok is True


def test_lint_accepts_valid_double_quoted_complex():
    """Complex but valid double-quoted python -c payloads are accepted."""
    result = lint_oracle(VALID_DOUBLE_QUOTED_COMPLEX)
    assert result.ok is True


def test_lint_rejects_syntax_error():
    """Python syntax errors in payload are caught."""
    result = lint_oracle(SYNTAX_ERROR_ORACLE)
    assert result.ok is False
    assert "syntax error" in result.error


def test_lint_oracles_list():
    """lint_oracles raises ValueError if any oracle fails."""
    with pytest.raises(ValueError) as exc:
        lint_oracles([VALID_DOUBLE_QUOTED, T0141_ORACLE])
    assert "Oracle lint failed" in str(exc.value)
    assert "unescaped nested double quote" in str(exc.value)


def test_lint_oracles_at_admission():
    """lint_oracles_at_admission returns list of error messages."""
    errors = lint_oracles_at_admission([T0141_ORACLE, T0142_ORACLE])
    assert len(errors) == 1
    assert "Oracle lint failed" in errors[0]
    assert "unescaped nested double quote" in errors[0]

    errors = lint_oracles_at_admission([T0145_ORACLE, T0146_ORACLE])
    assert errors == []

    errors = lint_oracles_at_admission([SINGLE_QUOTED_ORACLE])
    assert len(errors) == 1
    assert "single quotes" in errors[0]


def test_lint_empty_oracle():
    """Empty oracle is rejected."""
    result = lint_oracle("")
    assert result.ok is False
    assert "empty" in result.error

    result = lint_oracle("   ")
    assert result.ok is False
    assert "empty" in result.error


def test_lint_non_python_command():
    """Non-python commands pass basic validation."""
    result = lint_oracle("pytest -q tests/")
    assert result.ok is True

    result = lint_oracle("echo hello")
    assert result.ok is True

    result = lint_oracle("python -m pytest")
    assert result.ok is True


def test_lint_multiple_python_c_in_one_oracle():
    """Multiple python -c in one oracle (e.g., with &&) - ALL are checked."""
    # This oracle has two python -c commands joined by &&
    oracle = 'python -c "print(1)" && python -c "print(2)"'
    result = lint_oracle(oracle)
    # Both python -c commands are now checked
    assert result.ok is True

    # If second has an error (backslash-escaped quote + metacharacter), it should be caught
    # Use raw string so the backslash is preserved in the oracle
    oracle_bad = r'python -c "print(1)" && python -c "print(\"a&b\")"'
    result = lint_oracle(oracle_bad)
    assert result.ok is False
    assert "backslash-escaped quote" in result.error
    assert "metacharacter" in result.error


def test_lint_backslash_quote_metachar():
    """Backslash-escaped quote followed by metacharacter (&|<>^%) is rejected."""
    result = lint_oracle(BACKSLASH_QUOTE_METACHAR)
    assert result.ok is False
    assert "backslash-escaped quote" in result.error
    assert "metacharacter" in result.error


def test_lint_percent_in_payload():
    """Percent sign inside python -c payload is rejected (cmd.exe expands %var%)."""
    result = lint_oracle(PERCENT_IN_PAYLOAD)
    assert result.ok is False
    assert "percent sign" in result.error


def test_lint_various_interpreters():
    """Various Python interpreter invocations are detected."""
    result = lint_oracle(PY312_ORACLE)
    assert result.ok is True

    result = lint_oracle(PYTHON_EXE_ORACLE)
    assert result.ok is True

    result = lint_oracle(PY_ORACLE)
    assert result.ok is True

    result = lint_oracle(PATH_PYTHON_ORACLE)
    assert result.ok is True

    # Bad oracle with python3.12 (nested unescaped quotes, not backslash-escaped)
    # Use raw string to get actual nested unescaped quotes
    result = lint_oracle(r'python3.12 -c "print("a&b")"')
    assert result.ok is False
    assert "unescaped nested double quote" in result.error


def test_lint_and_chains():
    """&& chains are linted segment by segment."""
    # Both T-0145 and T-0146 use && chains and should pass
    result = lint_oracle(T0145_ORACLE)
    assert result.ok is True

    result = lint_oracle(T0146_ORACLE)
    assert result.ok is True

    # Chain with one bad segment (backslash-escaped quote + metacharacter)
    # Use raw string so the backslash is preserved
    bad_chain = r'python -c "print(1)" && python -c "print(\"a&b\")"'
    result = lint_oracle(bad_chain)
    assert result.ok is False
    assert "backslash-escaped quote" in result.error
    assert "metacharacter" in result.error


def test_lint_interpreter_flags_single_quoted_payload_rejected():
    """Interpreter flags between the interpreter and -c are recognized.

    A single-quoted payload in those forms must still be rejected.
    """
    for oracle in [
        "python -u -c 'print(\"hi\")'",
        "python -B -c 'print(\"hi\")'",
        "python -u -B -c 'print(\"hi\")'",
        "py -3 -c 'print(\"hi\")'",
        "py -3.12 -c 'print(\"hi\")'",
        "python -X utf8 -c 'print(\"hi\")'",
        "python3.12 -u -c 'print(\"hi\")'",
        "python.exe -u -c 'print(\"hi\")'",
    ]:
        result = lint_oracle(oracle)
        assert result.ok is False, f"Expected rejection for: {oracle}"
        assert "single quotes" in result.error, f"Expected single-quote error for: {oracle}"


def test_lint_interpreter_flags_valid_payload_passes():
    """Interpreter flags with a valid double-quoted payload pass."""
    for oracle in [
        'python -u -c "print(\'ok\')"',
        'python -B -c "print(\'ok\')"',
        'py -3 -c "print(\'ok\')"',
        'python -X utf8 -c "print(\'ok\')"',
        'python3.12 -u -B -X utf8 -c "print(\'ok\')"',
    ]:
        result = lint_oracle(oracle)
        assert result.ok is True, f"Expected pass for: {oracle}, got: {result.error}"


def test_lint_quoted_interpreter_path_with_spaces():
    """A double-quoted interpreter path containing spaces is recognized."""
    # Single-quoted payload after a quoted path with spaces -> rejected
    result = lint_oracle('"C:\\Program Files\\Python\\python.exe" -c \'print("hi")\'')
    assert result.ok is False
    assert "single quotes" in result.error

    result = lint_oracle('"C:\\Program Files\\Python\\python.exe" -u -c \'print("hi")\'')
    assert result.ok is False
    assert "single quotes" in result.error

    # Valid double-quoted payload after a quoted path with spaces -> passes
    result = lint_oracle('"C:\\Program Files\\Python\\python.exe" -c "print(\'ok\')"')
    assert result.ok is True, f"Expected pass, got: {result.error}"

    result = lint_oracle('"C:\\Program Files\\Python\\python.exe" -u -X utf8 -c "print(\'ok\')"')
    assert result.ok is True, f"Expected pass, got: {result.error}"


def test_lint_interpreter_flags_backslash_quote_still_caught():
    """Backslash-quoted metacharacters are caught through the flags path too."""
    result = lint_oracle(r'python -u -c "print(\"a&b\")"')
    assert result.ok is False
    assert "backslash-escaped quote" in result.error
    assert "metacharacter" in result.error


def test_lint_percent_modulo_rejected():
    """A % that would only be a Python modulo operator is still rejected."""
    result = lint_oracle('python -c "print(100 % 7)"')
    assert result.ok is False
    assert "percent sign" in result.error


def test_task_admit_refuses_bad_oracle(tmp_path):
    """task_admit refuses a card with a bad oracle."""
    import subprocess
    from pathlib import Path
    from pmk.api import Kernel, KernelError
    from pmk.clock import FakeClock
    from pmk.store import Repo

    r = Repo(tmp_path / 'repo')
    r.ensure_layout()

    subprocess.run(['git', 'init'], cwd=r.root, capture_output=True)
    subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=r.root, capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=r.root, capture_output=True)
    (r.root / 'README.md').write_text('# Test Repo\n', encoding='utf-8')
    subprocess.run(['git', 'add', 'README.md'], cwd=r.root, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=r.root, capture_output=True)

    clock = FakeClock()
    k = Kernel(root=r.root, clock=clock)
    k.init()

    # Bad oracle (backslash-quote + metacharacter) - create with admitted=False, then admit
    card = k.task_create(
        title="Bad oracle task",
        type="implement",
        goal_ref="G-001",
        scope={"write": ["src/thing.py"], "read": ["src/"]},
        oracles=[BACKSLASH_QUOTE_METACHAR],
        budget={"tokens": 10000, "wall_min": 10},
        admitted=False,
    )
    assert card.state == "PROPOSED"
    with pytest.raises(KernelError) as exc:
        k.task_admit(card.id)
    assert exc.value.reason == "admission_failed"
    assert "backslash-escaped quote" in str(exc.value.details["problems"])

    # Good oracle (should be admitted)
    card = k.task_create(
        title="Good oracle task",
        type="implement",
        goal_ref="G-001",
        scope={"write": ["src/thing.py"], "read": ["src/"]},
        oracles=[T0145_ORACLE],
        budget={"tokens": 10000, "wall_min": 10},
    )
    assert card.state == "READY"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
