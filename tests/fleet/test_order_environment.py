"""The order must not leave the worker guessing which shell it is in.

T-0146's agent spent its turns on `ls -la`, `&&` and `NAME=value cmd` inside
PowerShell 5.1.  These tests pin the dialect statement so a future edit cannot
quietly drop it.
"""

from types import SimpleNamespace

from fleet import order


def _task(**overrides):
    fields = dict(
        id="T-0000",
        title="do the thing",
        type="implement",
        goal_ref="G-001",
        write_scope=["docs/x.md"],
        read_scope=[],
        agent_hint="",
        premises=[],
        oracles=['python -c "print(1)"'],
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def test_windows_order_states_the_powershell_dialect():
    text = order.render_order(_task(), worktree="C:/w", platform_name="win32")
    assert "## Environment" in text
    assert "PowerShell 5.1" in text
    assert '$env:NAME="value"' in text
    assert "NOT  &&" in text
    assert "Get-ChildItem" in text


def test_posix_order_does_not_claim_powershell():
    text = order.render_order(_task(), worktree="/w", platform_name="linux")
    assert "## Environment" in text
    assert "POSIX shell" in text
    assert "PowerShell" not in text


def test_environment_section_precedes_the_agent_hint():
    text = order.render_order(
        _task(agent_hint="copy the corpus first"), worktree="C:/w",
        platform_name="win32")
    assert text.index("## Environment") < text.index("agent_hint")
