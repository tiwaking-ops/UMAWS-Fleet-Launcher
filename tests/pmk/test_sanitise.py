"""The sanitiser: removing the generator-managed blocks that must not ship.

CIP section 8.6 step 1 asks a human to read every generated file and
delete anything that tells an agent to bypass the Kernel.  The sanitiser
does that part mechanically and **records** what it removed, so nothing
disappears silently (constitution point 8).
"""

from __future__ import annotations

from pmk.context import (MANAGED_BLOCK, sanitize_context_files,
                          sanitize_context_text)

# The block Caliber 1.55.2 generated, verbatim.
CALIBER_PRE_COMMIT = """<!-- caliber:managed:pre-commit -->
## Before Committing

**IMPORTANT:** Before every git commit, you MUST ensure Caliber syncs agent configs with the latest code changes.

- If **no-hook**: run Caliber manually before committing:
  1. Run: `caliber refresh && git add CLAUDE.md .claude/ AGENTS.md 2>/dev/null`
<!-- /caliber:managed:pre-commit -->"""

CALIBER_LEARNINGS = """<!-- caliber:managed:learnings -->
## Session Learnings

Read `CALIBER_LEARNINGS.md` for patterns learned from previous sessions.
These are auto-extracted from real tool usage - treat them as project-specific rules.
<!-- /caliber:managed:learnings -->"""

SAFE_BLOCK = """<!-- caliber:managed:something-benign -->
## Layout

- `src/pmk/` - the Kernel.
- `src/fleet/` - the Fleet.
<!-- /caliber:managed:something-benign -->"""


def test_the_dangerous_block_is_removed():
    cleaned, removed = sanitize_context_text(CALIBER_PRE_COMMIT)
    assert "caliber:managed:pre-commit" not in cleaned
    assert "you MUST ensure Caliber" not in cleaned
    assert len(removed) == 1
    assert removed[0]["block"] == "caliber:managed:pre-commit"
    assert removed[0]["text"].strip()


def test_the_learnings_block_is_removed():
    cleaned, removed = sanitize_context_text(CALIBER_LEARNINGS)
    assert "treat them as project-specific rules" not in cleaned
    assert len(removed) == 1


def test_a_harmless_block_is_left_alone():
    cleaned, removed = sanitize_context_text(SAFE_BLOCK)
    assert removed == []
    assert cleaned == SAFE_BLOCK


def test_the_removed_text_is_preserved_for_the_record():
    """Nothing is deleted silently: the full text is returned."""
    _, removed = sanitize_context_text(CALIBER_PRE_COMMIT)
    assert "git add CLAUDE.md" in removed[0]["text"]


def test_the_surrounding_content_survives():
    document = ("# Project\n\n## Rules\n\n"
                "- The Kernel is the writer.\n\n"
                + CALIBER_PRE_COMMIT + "\n"
                + CALIBER_LEARNINGS + "\n"
                "## Done\n")
    cleaned, removed = sanitize_context_text(document)
    assert "# Project" in cleaned
    assert "The Kernel is the writer." in cleaned
    assert "## Done" in cleaned
    assert "caliber" not in cleaned.lower()
    assert len(removed) == 2


def test_sanitising_a_file_writes_it_and_reports(tmp_path):
    (tmp_path / "AGENTS.md").write_text(
        "# P\n\n" + CALIBER_PRE_COMMIT + "\n", encoding="utf-8")
    result = sanitize_context_files(tmp_path, ["AGENTS.md"])
    assert result["touched"] == ["AGENTS.md"]
    assert result["removed"][0]["file"] == "AGENTS.md"
    text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "caliber refresh" not in text
    assert "# P" in text


def test_a_file_with_nothing_to_remove_is_not_touched(tmp_path):
    (tmp_path / "AGENTS.md").write_text("# P\n", encoding="utf-8")
    result = sanitize_context_files(tmp_path, ["AGENTS.md"])
    assert result["touched"] == []
    assert result["removed"] == []


def test_the_block_pattern_matches_a_managed_block():
    match = MANAGED_BLOCK.search(CALIBER_PRE_COMMIT)
    assert match
    assert match.group(1) == "caliber:managed:pre-commit"
