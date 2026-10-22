"""The lint, run against **real** Caliber output.

These fixtures are the files Caliber 1.55.2 actually generated in spike S2
on 2026-10-22.  They are the most valuable test data in the project,
because they contain the dangerous content that a hand-written test would
never have thought of.

The first version of the lint passed these files.  That was a false
negative, and it is why these are pinned here: a lint that has only ever
seen hand-written samples is not tested.
"""

from __future__ import annotations

import pytest

from pmk.context import REJECT, lint_text

# The generated block, verbatim from Caliber's output.  It tells the agent
# to make an unaccounted model call and to stage files that the Kernel's
# scope check governs.
CALIBER_PRE_COMMIT_BLOCK = """<!-- caliber:managed:pre-commit -->
## Before Committing

**IMPORTANT:** Before every git commit, you MUST ensure Caliber syncs agent configs with the latest code changes.

First, check if the pre-commit hook is already installed:
```bash
grep -q "caliber" .git/hooks/pre-commit 2>/dev/null && echo "hook-active" || echo "no-hook"
```

- If **hook-active**: the hook handles sync automatically - just commit normally.
- If **no-hook**: run Caliber manually before committing:
  1. Tell the user: "Caliber: Syncing agent configs with your latest changes..."
  2. Run: `caliber refresh && git add CLAUDE.md .claude/ .cursor/ .cursorrules .github/copilot-instructions.md .github/instructions/ AGENTS.md CALIBER_LEARNINGS.md .agents/ .opencode/ 2>/dev/null`
  3. After it completes, briefly tell the user what Caliber updated.
<!-- /caliber:managed:pre-commit -->
"""

# The generated learnings block.  It tells the agent to treat
# auto-extracted patterns as project rules, which is exactly the
# "learnings are candidates, not evidence" rule (CIP Part B 14.7) inverted.
CALIBER_LEARNINGS_BLOCK = """<!-- caliber:managed:learnings -->
## Session Learnings

Read `CALIBER_LEARNINGS.md` for patterns and anti-patterns learned from previous sessions.
These are auto-extracted from real tool usage - treat them as project-specific rules.
<!-- /caliber:managed:learnings -->
"""


def test_the_real_caliber_pre_commit_block_is_rejected():
    findings = lint_text(CALIBER_PRE_COMMIT_BLOCK)
    assert any(f.severity == REJECT for f in findings), findings


def test_the_generated_git_add_of_managed_files_is_caught():
    findings = lint_text(CALIBER_PRE_COMMIT_BLOCK)
    assert any("git add" in f.detail or "stage the managed context files" in f.detail
               for f in findings), findings


def test_the_generated_run_of_the_generator_is_caught():
    findings = lint_text(CALIBER_PRE_COMMIT_BLOCK)
    assert any("context generator" in f.detail for f in findings), findings


def test_the_real_caliber_learnings_block_is_rejected():
    findings = lint_text(CALIBER_LEARNINGS_BLOCK)
    assert any(f.severity == REJECT for f in findings), findings
    assert any("treat generated content as project rules" in f.detail
               for f in findings), findings


def test_the_whole_generated_file_is_rejected():
    """The two blocks together, as they appear in the generated file."""
    generated = ("# OpenCode Configuration: csv2md\n\n"
                 "## Overview\nThis project converts CSV files to Markdown tables.\n\n"
                 "## Project Structure\n- `csv2md.py`: Core logic.\n\n"
                 + CALIBER_PRE_COMMIT_BLOCK + "\n" + CALIBER_LEARNINGS_BLOCK)
    findings = lint_text(generated)
    assert not [f for f in findings if f.severity == REJECT] == []
    assert any(f.severity == REJECT for f in findings), findings


def test_a_harmless_generated_file_still_passes():
    """The lint must not reject everything: the good part of Caliber's
    output is genuinely good and has to be allowed through."""
    harmless = """# OpenCode Configuration: csv2md

## Overview
This project converts CSV files to Markdown tables.

## Project Structure
- `csv2md.py`: Core logic for the `convert()` function.
- `tests/test_csv2md.py`: Unit tests using `pytest`.

## Workflow
1. Always run `pytest` before committing changes.
2. Keep the conversion function pure.
"""
    findings = lint_text(harmless)
    assert findings == [], findings
