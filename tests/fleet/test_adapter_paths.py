"""Every adapter hand-off must name one absolute worktree.

A relative cwd resolves against the directory of whoever called, not against
the lease.  These tests pin the boundary at each layer: the worktree helper,
the spawn chokepoint, the argv template, the order file, the legacy launcher,
the oracle runner and the process layer itself.
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

from fleet import harness, legacy, order, runenv, spawn
from fleet.adapters.generic import TemplateAdapter
from pmk import plat


def _repo(tmp_path):
    return SimpleNamespace(fleet_dir=tmp_path / ".pm" / "fleet")


class _RecordingAdapter:
    name = "recording"
    caps = SimpleNamespace(headless=True)

    def __init__(self):
        self.cwd = ""

    def build_argv(self, profile, mode, prompt, cwd, session):
        self.cwd = cwd
        return ["python", "-c", "pass"]


def test_worktree_path_resolves_against_the_repo_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    repo = SimpleNamespace(worktree_root=lambda: "work")
    assert spawn.worktree_path(repo, "T-1", 2) == \
        (tmp_path / "work" / "T-1-2").resolve()


def test_spawn_slot_hands_the_adapter_an_absolute_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wt = tmp_path / "work" / "T-1-1"
    wt.mkdir(parents=True)
    adapter = _RecordingAdapter()
    seen = {}

    def fake_spawn(argv, **kwargs):
        seen.update(kwargs)
        return SimpleNamespace(pid=4242, creation_time=7, proc=None)

    monkeypatch.setattr(spawn.plat, "spawn", fake_spawn)
    slot = spawn.spawn_slot(_repo(tmp_path), task_id="T-1", profile_id="p",
                            adapter=adapter, profile={}, prompt="go",
                            worktree="work/T-1-1", fence=1, env={})
    assert adapter.cwd == str(wt.resolve())
    assert slot.worktree == str(wt.resolve())
    assert Path(seen["cwd"]) == wt.resolve()


def test_adapter_template_receives_an_absolute_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    adapter = TemplateAdapter("generic")
    argv = adapter.build_argv({"argv_new": ["cli", "--dir", "{cwd}"]},
                              "new", "prompt", "work/T-1-1", None)
    assert argv == ["cli", "--dir",
                    str((tmp_path / "work" / "T-1-1").resolve())]


def test_order_paths_and_rendering_are_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wt = (tmp_path / "work" / "T-1-1").resolve()
    task = SimpleNamespace(id="T-1", title="do", type="implement",
                           goal_ref="G-1", write_scope=["src/a.py"],
                           read_scope=[], agent_hint="", premises=[],
                           oracles=["true"])
    assert order.order_path("work/T-1-1") == wt / ".pmwork" / "ORDER.md"
    text = order.render_order(task, worktree="work/T-1-1")
    assert str(wt) in text
    target = order.write_order("work/T-1-1", text)
    assert target.is_file() and target.is_absolute()


def test_legacy_launch_resolves_a_stored_relative_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wt = tmp_path / "work" / "T-1-1"
    wt.mkdir(parents=True)
    seen = {}

    monkeypatch.setattr(legacy, "find_shell", lambda: "pwsh")
    monkeypatch.setattr(
        legacy.subprocess, "Popen",
        lambda args, **kw: seen.update(kw) or SimpleNamespace(pid=1))
    entry = legacy.LauncherEntry(prefix="cli", prompt="hi", cwd="work/T-1-1")
    legacy.launch_legacy(entry, keep_open=False,
                         script_dir=str(tmp_path / "scripts"))
    assert Path(seen["cwd"]) == wt.resolve()
    script = next((tmp_path / "scripts").glob("*.ps1")).read_text(
        encoding="utf-8-sig")
    assert str(wt.resolve()) in script


def test_legacy_launch_falls_back_to_an_explicit_resolved_cwd(
        tmp_path, monkeypatch):
    """An entry with no cwd still hands Popen one absolute, resolved dir.

    The launcher used to let the child inherit whatever directory the
    Console happened to have.  The fallback must be the Console's own
    directory, resolved, and it must still be passed explicitly - the
    no-cwd case is exactly where an omitted ``cwd=`` would slip back in.
    """
    console_dir = tmp_path / "console"
    console_dir.mkdir()
    monkeypatch.chdir(console_dir)
    seen = {}

    monkeypatch.setattr(legacy, "find_shell", lambda: "pwsh")
    monkeypatch.setattr(
        legacy.subprocess, "Popen",
        lambda args, **kw: seen.update(kw) or SimpleNamespace(pid=1))
    entry = legacy.LauncherEntry(prefix="cli", prompt="hi")
    assert entry.cwd == ""

    legacy.launch_legacy(entry, keep_open=False,
                         script_dir=str(tmp_path / "scripts"))

    assert "cwd" in seen
    assert Path(seen["cwd"]) == console_dir.resolve()
    assert Path(seen["cwd"]).is_absolute()
    script = next((tmp_path / "scripts").glob("*.ps1")).read_text(
        encoding="utf-8-sig")
    # No stored cwd, so no Set-Location: the explicit Popen cwd is the
    # only thing that fixes the child's directory.
    assert "Set-Location" not in script


def test_run_command_resolves_the_oracle_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sub = tmp_path / "sub"
    sub.mkdir()
    seen = {}

    def fake_run(command, **kwargs):
        seen.update(kwargs)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(harness.subprocess, "run", fake_run)
    harness.run_command("echo hi", "sub")
    assert Path(seen["cwd"]) == sub.resolve()
    assert seen["env"]["PYTHONPATH"].split(os.pathsep)[0] == \
        str(sub.resolve() / "src")


def test_runenv_resolves_a_relative_worktree(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = runenv.worktree_env("sub")
    assert env["PYTHONPATH"].split(os.pathsep)[0] == \
        str((tmp_path / "sub" / "src").resolve())


def test_plat_spawn_makes_the_cwd_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sub").mkdir()
    seen = {}
    monkeypatch.setattr(
        plat.subprocess, "Popen",
        lambda argv, **kw: seen.update(kw) or SimpleNamespace(pid=1))
    monkeypatch.setattr(plat, "process_info",
                        lambda pid: SimpleNamespace(creation_time=1))
    plat.spawn(["python", "-c", "pass"], cwd="sub")
    assert Path(seen["cwd"]) == (tmp_path / "sub").resolve()
