"""Oracle linting (fleet amendment: oracle safety) - thin re-export from pmk.oracle_lint.

The actual implementation is in pmk.oracle_lint. This module exists for
backward compatibility with existing imports.
"""

from pmk.oracle_lint import (
    OracleLintResult,
    SHELL_METACHARS,
    PYTHON_INTERPRETER_RE,
    lint_oracle,
    lint_oracles,
    lint_oracles_at_admission,
)

__all__ = [
    "OracleLintResult",
    "SHELL_METACHARS",
    "PYTHON_INTERPRETER_RE",
    "lint_oracle",
    "lint_oracles",
    "lint_oracles_at_admission",
]
