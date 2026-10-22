"""Spawning workers (fleet amendment section 7.2).

The Windows rules, all of them learned the hard way:

* Build **argv lists**, never shell strings.  ``ps_escape`` and
  ``build_command`` from the legacy launcher are *not* ported here; they
  survive only in the manual legacy path.
* Resolve the executable with :func:`pmk.plat.resolve_executable`.  A
  ``.cmd`` shim is peeled to its real target and launched directly, because
  ``cmd.exe`` re-parses arguments and mangles them (spike S-A1).
* Headless: ``subprocess.Popen`` with stdout and stderr merged into one log
  file, and ``CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP``.
* One log per process: ``.pm/fleet/logs/<task>/<fence>-<n>.log``.
* Kill a process tree with ``taskkill /PID <pid> /T /F``.  Never kill a
  process the Dispatcher did not spawn: the pid **and** the process creation
  time are recorded, and both must match.
* Disable hooks per worktree by pointing ``core.hooksPath`` at an empty
  directory, not ``/dev/null`` (``NUL`` is not a directory).
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from pmk import plat


@dataclass
class Slot:
    """One running CLI process for one lease."""

    task_id: str
    profile_id: str
    adapter: str
    argv: list
    pid: int | None = None
    creation_time: int | None = None
    log_path: str = ""
    worktree: str = ""
    started_at: float = 0.0
    session: str = ""
    degraded: bool = False
    #: The live Popen, when the adapter is headless.  Its ``poll()`` is the
    #: authoritative exit code.
    proc: object = None

    def exit_code(self) -> int | None:
        """The exit code of the finished process, or ``None`` if it is running.

        For a headless slot the Popen object is authoritative.  For the
        console fallback the code is read from the ``<log>.exit`` file that
        the wrapper writes.
        """
        if self.proc is not None:
            try:
                return self.proc.poll()
            except Exception:                       # noqa: BLE001
                return None
        return read_exit_code(self.log_path)

    def to_dict(self) -> dict:
        return {
            "task": self.task_id,
            "profile": self.profile_id,
            "adapter": self.adapter,
            "pid": self.pid,
            "creation_time": self.creation_time,
            "log_path": self.log_path,
            "worktree": self.worktree,
            "started_at": self.started_at,
            "session": self.session,
            "degraded": self.degraded,
        }


# ---------------------------------------------------------------------------
# Worktrees
# ---------------------------------------------------------------------------

def worktree_path(repo, task_id: str, fence: int) -> Path:
    """Where a lease's worktree lives."""
    root = Path(repo.worktree_root())
    return root / f"{task_id}-{fence}"


def create_worktree(repo, task_id: str, fence: int, *,
                    base: str = "HEAD", branch: str | None = None) -> Path:
    """Create a per-lease git worktree.

    The branch is ``pmk/<task>-<fence>``.  Worktrees are how two agents can
    work on one repository without sharing a working tree.
    """
    target = worktree_path(repo, task_id, fence)
    target.parent.mkdir(parents=True, exist_ok=True)
    branch = branch or f"pmk/{task_id}-{fence}"
    code, out, err = repo.git("worktree", "add", "-B", branch, str(target), base)
    if code != 0:
        raise RuntimeError(f"git worktree add failed ({code}): {err or out}")
    disable_hooks(repo, target)
    return target


def disable_hooks(repo, worktree: str | Path) -> None:
    """Point ``core.hooksPath`` at an empty directory.

    Git hooks in ``.git/hooks`` are **shared by every worktree**, so a hook
    installed for the operator's checkout would fire in every worker
    worktree and rewrite context files concurrently (CIP section 2.4).

    The path must be an existing empty *directory*: ``/dev/null`` does not
    exist on Windows and ``NUL`` is not a directory, so git would refuse it.
    """
    hooks_dir = Path(repo.nohooks_dir)
    hooks_dir.mkdir(parents=True, exist_ok=True)
    for stray in hooks_dir.iterdir():
        if stray.is_file():
            stray.unlink()
    code, out, err = repo.git("config", "--worktree", "core.hooksPath",
                              str(hooks_dir), cwd=Path(worktree))
    if code != 0:
        # A repository without extensions.worktreeConfig cannot take a
        # per-worktree config; fall back to the repository config.
        repo.git("config", "core.hooksPath", str(hooks_dir))


def remove_worktree(repo, path: str | Path) -> bool:
    """Remove a worktree.  Never destructive to the main tree."""
    target = Path(path)
    code, out, err = repo.git("worktree", "remove", "--force", str(target))
    if code != 0:
        return False
    repo.git("worktree", "prune")
    return True


def worktree_status(repo, worktree: str | Path) -> str:
    """``git status --porcelain`` listing **every** changed file.

    ``--untracked-files=all`` is essential.  Without it git collapses a
    whole untracked *directory* into a single ``dir/`` entry, so a worker
    that created a new module in a new directory would have had its work
    invisible to the scope check, and the evidence bundle would have
    recorded no output files at all.  That was measured, not assumed
    (pilot demo, 2026-10-22).
    """
    code, out, err = repo.git("status", "--porcelain", "--untracked-files=all",
                              cwd=Path(worktree))
    return out if code == 0 else ""


def worktree_status_detail(repo, worktree: str | Path) -> dict:
    """``git status --porcelain`` with the exit code and stderr.

    A scope check that reports "no changes" when a worker clearly wrote
    something is a silent failure, so the evidence bundle keeps the git
    exit code and stderr alongside the file list.
    """
    code, out, err = repo.git("status", "--porcelain", "--untracked-files=all",
                              cwd=Path(worktree))
    return {"code": code, "out": out, "err": err}


def worktree_diff_stat(repo, worktree: str | Path) -> str:
    code, out, err = repo.git("diff", "--stat", cwd=Path(worktree))
    return out if code == 0 else ""


# ---------------------------------------------------------------------------
# Spawning
# ---------------------------------------------------------------------------

def log_path(repo, task_id: str, fence: int, index: int) -> Path:
    """One log file per process."""
    return Path(repo.fleet_dir) / "logs" / task_id / f"{fence}-{index}.log"


def spawn_slot(repo, *, task_id: str, profile_id: str, adapter,
               profile: dict, prompt: str, worktree: str | Path,
               fence: int, index: int = 0,
               env: dict | None = None) -> Slot:
    """Spawn one worker.

    A headless adapter runs without a console.  An adapter whose
    ``caps.headless`` is False (every unobserved real CLI) gets a console
    window and is marked ``degraded``: its output capture is best-effort.
    """
    import time

    target = Path(worktree)
    log_file = log_path(repo, task_id, fence, index)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    argv = adapter.build_argv(profile, "new", prompt, str(target), None)

    resolved = plat.resolve_executable(argv[0])
    if resolved is not None:
        real_argv = plat.argv_for_executable(resolved, argv[1:])
    else:
        real_argv = argv

    headless = adapter.caps.headless
    slot = Slot(task_id=task_id, profile_id=profile_id,
                adapter=getattr(adapter, "name", "?"),
                argv=real_argv, log_path=str(log_file),
                worktree=str(target), started_at=time.time(),
                degraded=not headless)

    if headless:
        result = plat.spawn(real_argv, cwd=target, log_path=log_file,
                            env=env)
        slot.pid = result.pid
        slot.creation_time = result.creation_time
        slot.proc = result.proc
        return slot

    # Terminal fallback: a console window that writes its exit code to
    # "<log>.exit" when it finishes.  Output capture is best-effort.
    return _spawn_with_console(repo, slot, real_argv, log_file)


def _spawn_with_console(repo, slot: Slot, argv: list[str],
                         log_file: Path) -> Slot:
    """Launch in a console window, recording the exit code afterwards.

    This is the degraded path for an adapter whose headless behaviour has
    not been observed.  It is honest about being degraded: the Console
    shows it, and the slot's output is not reliably captured.
    """
    import time

    exit_file = Path(str(log_file) + ".exit")
    if exit_file.exists():
        exit_file.unlink()

    script = Path(str(log_file) + ".ps1")
    quoted = " ".join(_ps_quote(a) for a in argv)
    script.write_text(
        "$ErrorActionPreference = 'Continue'\n"
        f"Set-Location -LiteralPath '{_ps_quote(str(slot.worktree))}'\n"
        f"& {quoted} *> '{_ps_quote(str(log_file))}'\n"
        f"$LASTEXITCODE | Out-File -FilePath '{_ps_quote(str(exit_file))}' "
        "-Encoding ascii\n",
        encoding="utf-8-sig")

    shell = plat.resolve_executable("pwsh") or plat.resolve_executable("powershell")
    shell_path = shell.target if shell else "powershell.exe"
    creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    try:
        proc = subprocess.Popen(
            [shell_path, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", str(script)],
            cwd=slot.worktree, creationflags=creationflags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        # No console available (a service session, or Windows blocked it).
        # Fall back to a headless launch so the task still runs.
        result = plat.spawn(argv, cwd=slot.worktree, log_path=log_file)
        slot.pid = result.pid
        slot.creation_time = result.creation_time
        return slot

    info = plat.process_info(proc.pid)
    slot.pid = proc.pid
    slot.creation_time = info.creation_time
    return slot


def _ps_quote(text: str) -> str:
    """Quote one argument for a PowerShell single-quoted string."""
    return "'" + str(text).replace("'", "''") + "'"


def read_exit_code(log_file: str | Path) -> int | None:
    """Read the exit code the console fallback wrote, if it is there."""
    exit_file = Path(str(log_file) + ".exit")
    try:
        text = exit_file.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    if not text:
        return None
    try:
        return int(text.splitlines()[0].strip())
    except (ValueError, IndexError):
        return None


def kill_slot(slot: Slot) -> tuple[bool, str]:
    """Kill a slot's process tree.

    Refuses unless the pid **and** the creation time still match, so a
    recycled pid is never killed (fleet amendment rule 17).
    """
    if slot.pid is None:
        return False, "no pid"
    return plat.kill_tree(slot.pid, creation_time=slot.creation_time)


def slot_alive(slot: Slot) -> bool:
    """Is the slot's process still running?"""
    if slot.pid is None:
        return False
    return plat.same_process(slot.pid, slot.creation_time)


def log_growth(slot: Slot) -> int:
    """Size of the slot's log file, in bytes."""
    try:
        return Path(slot.log_path).stat().st_size
    except OSError:
        return 0


def tail_log(slot: Slot, lines: int = 40) -> list[str]:
    return plat.tail_file(slot.log_path, lines)
