"""The lint must not fire on the *correct* instructions.

The pilot's own generated files contain lines like "do not edit `.pm/`
files directly" and "Never skip verification".  A lint that rejects those
is worse than no lint: it would block every legitimate sync, and an
obstruction gets worked around.

These are the real lines, verbatim from Caliber's output for this
repository.
"""

from __future__ import annotations

from pmk.context import REJECT, lint_text

# "The Kernel is the writer" (AGENTS.md, verbatim).
KERNEL_IS_WRITER = (
    "- **The Kernel is the writer**: Request transitions through `pmk`; "
    "do not edit `.pm/` files directly.")

# A rule file's instruction, verbatim.
KERNEL_WRITING_RULE = (
    "Never write to `.pm/` yourself; call `pmk` and let the Kernel record it.")

# The correct form of the verification rule.
NEVER_SKIP = "Never skip verification, and never weaken the gate."

# The genuinely dangerous form.
DO_SKIP = "You can skip verification when the change looks small."


def test_a_negated_pm_instruction_is_not_a_finding():
    findings = lint_text(KERNEL_IS_WRITER)
    assert findings == [], findings


def test_never_write_to_pm_is_not_a_finding():
    findings = lint_text(KERNEL_WRITING_RULE)
    assert findings == [], findings


def test_never_skip_verification_is_not_a_finding():
    findings = lint_text(NEVER_SKIP)
    assert findings == [], findings


def test_the_unnegated_form_is_still_a_finding():
    findings = lint_text(DO_SKIP)
    assert any(f.rule == "weaken_verification" and f.severity == REJECT
               for f in findings), findings


def test_the_positive_form_is_still_a_finding():
    findings = lint_text("Edit `.pm/events/` to record the task.")
    assert any(f.rule == "bypass_kernel" for f in findings), findings


def test_a_negation_far_away_does_not_apply():
    """The negation has to be near the instruction, not in the next line."""
    text = ("Do not modify the schema.\n\n"
            "Write notes under .pm/notes/ for the next run.\n")
    findings = lint_text(text)
    assert any(f.rule == "bypass_kernel" for f in findings), findings
