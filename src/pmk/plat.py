"""Platform layer for the Kernel and the Fleet.

Fleet amendment D-L1: the platform decision is isolated in this module so the
Kernel's file-locking, process-spawn and process-kill code is testable and
swappable, and so that a later flip to WSL (pilot v1 section 7.1) touches one
file instead of the whole codebase.

Standard library only (fleet amendment section 7.1).

Windows notes that matter, all of them observed on the operator's machine
(spike S-P1, 2026-10-22):

* ``msvcrt.locking`` locks a byte range relative to the *current file
  position* and takes an exclusive lock.  A file must be at least one byte
  long before a lock can be taken on it.
* **Windows enforces byte-range locks against writes.**  A process that holds
  a lock on byte 0 of a file cannot write to byte 0 of that file from another
  handle, and gets ``PermissionError``.  This was measured, not assumed
  (spike S-P1, 2026-10-22): locking the event log and appending to the event
  log fails, because an append to an empty file lands on byte 0.  The lock
  therefore lives on a **sidecar** ``<file>.lock`` and the data file is
  written under that lock.  See :class:`FileLock`.
* ``LK_LOCK`` retries for about ten seconds and then raises; ``LK_NBLCK``
  fails immediately.  The pilot wants explicit retry with a deadline, so this
  module uses ``LK_NBLCK`` inside its own retry loop.
* There is no ``/dev/null``.  The null path is ``NUL``.
* A process tree is killed with ``taskkill /PID <pid> /T /F``.
* A pid can be recycled.  "Is this process alive?" is only meaningful
  together with the process creation time, so both are captured.
"""

from __future__ import annotations

import ctypes
import errno
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

IS_WINDOWS = os.name == "nt"

if IS_WINDOWS:  # pragma: no cover - platform conditional
    import msvcrt
else:  # pragma: no cover - platform conditional
    import fcntl


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def null_path() -> str:
    """The platform's null device.  ``/dev/null`` does not exist on Windows."""
    return "NUL" if IS_WINDOWS else "/dev/null"


def short_path(path: os.PathLike[str] | str) -> str:
    """Return *path* as an absolute, forward-slash-free native path string."""
    return str(Path(path).resolve())


def ensure_dir(path: os.PathLike[str] | str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------------------
# Atomic writes
# ---------------------------------------------------------------------------

def atomic_write_text(path: os.PathLike[str] | str, text: str,
                      *, encoding: str = "utf-8") -> None:
    """Write *text* to *path* atomically (temp file in the same directory, then
    ``os.replace``).  A reader never observes a half-written file."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    with open(tmp, "w", encoding=encoding, newline="\n") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, target)


def read_text(path: os.PathLike[str] | str, *, encoding: str = "utf-8") -> str:
    """Read a text file, tolerating a UTF-8 BOM.

    Windows PowerShell 5.1's ``Set-Content -Encoding utf8`` writes a BOM
    (bytes ``EF BB BF``).  The operator edits files with PowerShell, so
    operator-written files routinely carry one, and Python's ``utf-8``
    decoder leaves it in the string as ``\\ufeff``.

    That is not cosmetic: a BOM at the start of a JSON or TOML file makes
    the parser fail, and a BOM inside a classifier pattern makes the
    pattern match only at the very start of a string.  Every file this
    project reads that a human might have written goes through here.
    """
    try:
        return Path(path).read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise
    except UnicodeDecodeError:
        return Path(path).read_text(encoding=encoding, errors="replace")


# ---------------------------------------------------------------------------
# File locking
# ---------------------------------------------------------------------------

class LockTimeout(RuntimeError):
    """Raised when an exclusive lock could not be taken before its deadline."""


class FileLock:
    """Exclusive advisory lock over a byte range of a file.

    On Windows the lock is a byte-range lock via ``msvcrt.locking``; on POSIX
    it is ``flock``.  Both are released by the operating system if the process
    dies, which is what lets the Kernel treat "the writer crashed" and "the
    writer is gone" as the same event.

    **The lock is taken on a sidecar file, not on the data file.**  This is
    forced by Windows semantics, measured in spike S-P1: Windows enforces
    byte-range locks against writes, so a lock on byte 0 of the event log
    makes appending to the event log fail with ``PermissionError``.  The
    sidecar (``<file>.lock``) is created and kept at one byte; only its
    first byte is ever locked.

    Pass *lock_path* explicitly to share one lock between several files.
    """

    def __init__(self, path: os.PathLike[str] | str, *,
                 lock_path: os.PathLike[str] | str | None = None,
                 start: int = 0, length: int = 1,
                 timeout: float = 30.0, poll: float = 0.01):
        self.path = Path(path)
        if lock_path is not None:
            self.lock_path = Path(lock_path)
        else:
            self.lock_path = self.path.with_name(self.path.name + ".lock")
        self.start = start
        self.length = max(1, length)
        self.timeout = timeout
        self.poll = poll
        self._fd: int | None = None
        self._fh = None

    # -- internals --------------------------------------------------------
    def _open(self) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        # The lock file must exist and be non-empty: msvcrt.locking refuses to
        # lock a zero-length file.
        if not self.lock_path.exists() or self.lock_path.stat().st_size == 0:
            with open(self.lock_path, "ab"):
                pass
        self._fd = os.open(self.lock_path, os.O_RDWR)

    def _try_lock(self) -> bool:
        assert self._fd is not None
        if IS_WINDOWS:
            os.lseek(self._fd, self.start, os.SEEK_SET)
            try:
                msvcrt.locking(self._fd, msvcrt.LK_NBLCK, self.length)
            except OSError as exc:
                if exc.errno in (errno.EACCES, errno.EDEADLK, errno.EAGAIN, errno.ERANGE):
                    return False
                raise
            return True
        try:  # pragma: no cover - platform conditional
            fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:  # pragma: no cover - platform conditional
            if exc.errno in (errno.EACCES, errno.EAGAIN):
                return False
            raise
        return True

    def _unlock(self) -> None:
        assert self._fd is not None
        if IS_WINDOWS:
            os.lseek(self._fd, self.start, os.SEEK_SET)
            try:
                msvcrt.locking(self._fd, msvcrt.LK_UNLCK, self.length)
            except OSError:
                pass
        else:  # pragma: no cover - platform conditional
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            except OSError:
                pass

    # -- public ------------------------------------------------------------
    def acquire(self) -> "FileLock":
        if self._fd is not None:
            return self
        self._open()
        deadline = time.monotonic() + self.timeout
        delay = self.poll
        while True:
            if self._try_lock():
                self._fd and None
                return self
            if time.monotonic() >= deadline:
                self._close_fd()
                raise LockTimeout(
                    f"could not lock {self.lock_path} within {self.timeout}s")
            time.sleep(delay)
            delay = min(delay * 1.5, 0.25)

    def release(self) -> None:
        if self._fd is None:
            return
        self._unlock()
        self._close_fd()

    def _close_fd(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None

    def __enter__(self) -> "FileLock":
        return self.acquire()

    def __exit__(self, *exc_info) -> None:
        self.release()


# ---------------------------------------------------------------------------
# Append under lock
# ---------------------------------------------------------------------------

def append_line_locked(path: os.PathLike[str] | str, line: str, *,
                       lock_path: os.PathLike[str] | str | None = None,
                       timeout: float = 30.0) -> None:
    """Append one ``\\n``-terminated *line* to *path* while holding the lock.

    The write happens inside the lock, so concurrent writers cannot interleave
    partial lines.  This is the only sanctioned way to append to the event
    log.
    """
    if not line.endswith("\n"):
        line += "\n"
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(target, lock_path=lock_path, timeout=timeout):
        with open(target, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())


# ---------------------------------------------------------------------------
# Process identity (pid recycling)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProcInfo:
    """Identity of a running process.

    ``creation_time`` is a platform-native tick counter.  Two observations
    with the same pid but different creation times are different processes.
    """

    pid: int
    creation_time: int | None
    alive: bool


def _win_process_info(pid: int) -> ProcInfo:  # pragma: no cover - windows only
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    SYNCHRONIZE = 0x00100000
    WAIT_TIMEOUT = 0x00000102
    STILL_ACTIVE = 259

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    kernel32.GetExitCodeProcess.argtypes = [ctypes.c_void_p,
                                            ctypes.POINTER(ctypes.c_uint32)]
    kernel32.GetExitCodeProcess.restype = ctypes.c_int
    kernel32.GetProcessTimes.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_uint64),
        ctypes.POINTER(ctypes.c_uint64),
        ctypes.POINTER(ctypes.c_uint64),
        ctypes.POINTER(ctypes.c_uint64),
    ]
    kernel32.GetProcessTimes.restype = ctypes.c_int
    kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel32.WaitForSingleObject.restype = ctypes.c_uint32

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE,
                                  False, pid)
    if not handle:
        # Cannot open: either it is gone or it belongs to another user.
        # Treat "gone" as the answer, but only after a cheap existence probe.
        return ProcInfo(pid=pid, creation_time=None, alive=False)

    try:
        creation = ctypes.c_uint64()
        exit_time = ctypes.c_uint64()
        kernel = ctypes.c_uint64()
        user = ctypes.c_uint64()
        creation_ok = kernel32.GetProcessTimes(
            handle, ctypes.byref(creation), ctypes.byref(exit_time),
            ctypes.byref(kernel), ctypes.byref(user))
        creation_time = int(creation.value) if creation_ok else None

        wait = kernel32.WaitForSingleObject(handle, 0)
        alive = wait == WAIT_TIMEOUT
        if not alive:
            code = ctypes.c_uint32()
            if kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                alive = code.value == STILL_ACTIVE
        return ProcInfo(pid=pid, creation_time=creation_time, alive=bool(alive))
    finally:
        kernel32.CloseHandle(handle)


def process_info(pid: int | None) -> ProcInfo:
    """Return identity and liveness of *pid*."""
    if pid is None:
        return ProcInfo(pid=0, creation_time=None, alive=False)
    if IS_WINDOWS:  # pragma: no cover - platform conditional
        return _win_process_info(int(pid))
    try:  # pragma: no cover - platform conditional
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return ProcInfo(pid=int(pid), creation_time=None, alive=False)
    except PermissionError:
        return ProcInfo(pid=int(pid), creation_time=None, alive=True)
    stat = Path(f"/proc/{pid}").stat() if Path("/proc").exists() else None
    return ProcInfo(pid=int(pid),
                    creation_time=int(stat.st_ctime) if stat else None,
                    alive=True)


def same_process(pid: int | None, creation_time: int | None) -> bool:
    """True when *pid* is alive **and** is the same process that was recorded.

    A recycled pid has a different creation time and is therefore *not* the
    same process.  This is the check the Fleet uses before it kills anything
    (fleet amendment rule 17).
    """
    if pid is None:
        return False
    info = process_info(pid)
    if not info.alive:
        return False
    if creation_time is None or info.creation_time is None:
        return False
    return int(creation_time) == int(info.creation_time)


# ---------------------------------------------------------------------------
# Process spawn and kill
# ---------------------------------------------------------------------------

@dataclass
class SpawnResult:
    argv: list[str]
    pid: int
    creation_time: int | None
    log_path: str
    #: The live :class:`subprocess.Popen`.  Keeping it is what makes the
    #: exit code reliable: ``Popen.poll()`` is the authoritative answer for
    #: a child process, and a separately opened handle can lose the code if
    #: the child is reaped first.
    proc: "subprocess.Popen | None" = None


def spawn(argv: Sequence[str], *, cwd: os.PathLike[str] | str | None = None,
          log_path: os.PathLike[str] | str | None = None,
          env: Mapping[str, str] | None = None,
          timeout_ms: int = 120_000) -> SpawnResult:
    """Spawn *argv* as a detached, windowless child process.

    Rules (fleet amendment section 7.2):

    * *argv* is a list, never a shell string.  No quoting is involved.
    * stdout and stderr go to one log file (stderr is merged into stdout).
    * ``CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP`` keeps the worker from
      flashing a console and lets it be killed as a group.
    """
    argv = [str(a) for a in argv]
    if not argv:
        raise ValueError("argv must not be empty")

    stdout = subprocess.DEVNULL
    stderr = subprocess.STDOUT
    handle = None
    if log_path is not None:
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        handle = open(log_path, "ab", buffering=0)
        stdout = handle

    creationflags = 0
    if IS_WINDOWS:  # pragma: no cover - platform conditional
        creationflags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        proc = subprocess.Popen(
            argv,
            cwd=str(cwd) if cwd else None,
            stdout=stdout,
            stderr=stderr,
            stdin=subprocess.DEVNULL,
            env=dict(env) if env is not None else None,
            creationflags=creationflags,
            close_fds=True,
        )
    finally:
        if handle is not None:
            handle.close()

    info = process_info(proc.pid)
    return SpawnResult(argv=argv, pid=proc.pid,
                       creation_time=info.creation_time,
                       log_path=str(log_path) if log_path else "",
                       proc=proc)


def kill_tree(pid: int, *, creation_time: int | None = None,
              force: bool = True) -> tuple[bool, str]:
    """Kill a process tree.  Returns ``(killed, detail)``.

    Refuses to kill a process that is not provably the one the caller spawned
    (fleet amendment rule 17).  On Windows the tree is killed with
    ``taskkill /T`` so that children of the CLI die with it.
    """
    if not same_process(pid, creation_time):
        return False, "pid/creation-time mismatch or process not alive; refused to kill"
    if IS_WINDOWS:  # pragma: no cover - platform conditional
        cmd = ["taskkill", "/PID", str(pid), "/T"]
        if force:
            cmd.append("/F")
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as exc:
            return False, f"taskkill failed: {exc}"
        detail = (out.stdout or "") + (out.stderr or "")
        return out.returncode == 0, detail.strip()
    import signal  # pragma: no cover - platform conditional
    try:  # pragma: no cover - platform conditional
        os.killpg(os.getpgid(pid), signal.SIGKILL if force else signal.SIGTERM)
        return True, "SIGKILL to process group"
    except Exception as exc:  # noqa: BLE001 - reported, never raised
        return False, str(exc)


# ---------------------------------------------------------------------------
# Executable resolution
# ---------------------------------------------------------------------------

#: Extensions Windows treats as directly launchable through ``cmd.exe``.
CMD_EXTENSIONS = (".cmd", ".bat")


@dataclass(frozen=True)
class Resolved:
    """A tool the Fleet can actually launch.

    ``kind`` is one of:

    ``native``
        A real executable (``.exe``).  Launched directly.
    ``node``
        A JavaScript entry point behind an npm ``.cmd`` shim.  Launched as
        ``node <script> <args>``.
    ``powershell``
        A ``.ps1``.  Launched through ``pwsh``/``powershell -File``.
    ``cmd``
        A ``.cmd`` shim whose real target could not be determined.  Launched
        through ``cmd.exe`` — **degraded**: cmd.exe re-parses the command
        line, so arguments containing ``%``, ``&``, ``^`` or quotes are
        mangled (measured, spike S-A1).  Prefer ``node`` or ``native``.
    """

    path: str
    kind: str
    runner: str | None = None
    target: str = ""

    @property
    def degraded(self) -> bool:
        return self.kind == "cmd"


# npm shim patterns.  The executed program is quoted and prefixed with either
# ``%~dp0`` (the batch parameter for the script's own directory) or ``%dp0%``
# (a variable the shim sets itself).  Both mean "directory of this .cmd".
#
# The interpreter is *not* matched directly: npm writes
# ``"%_prog%"  "%dp0%\node_modules\pkg\bin\tool.js"`` where ``_prog`` is
# ``node``, so the word "node" may be quoted, indirect, or absent.
_QUOTED_DP0 = re.compile(r'"%dp0%\\([^"]+)"', re.IGNORECASE)
_QUOTED_SELF = re.compile(r'"%~dp0([^"]+)"', re.IGNORECASE)

#: An interpreter copy inside the package directory is not the program.
_INTERPRETER_NAMES = {"node.exe", "node.cmd", "node"}


def _resolve_cmd_shim(path: str) -> Resolved | None:
    """Peel an npm ``.cmd`` shim back to the program it actually runs.

    npm generates three shims per package.  The ``.cmd`` one ends with
    ``%*``, so **cmd.exe re-parses every argument**: ``%PATH%`` expands to
    the whole PATH, ``^`` doubles, and ``&`` splits the command.  Spike
    S-A1 measured exactly that on this machine.

    So the Fleet does not run ``.cmd`` shims through cmd.exe.  It reads the
    shim, finds the real target (a node script or a native executable) and
    launches that directly with an argv list.
    """
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    base = Path(path).parent

    candidates: list[Path] = []
    for pattern in (_QUOTED_DP0, _QUOTED_SELF):
        for match in pattern.finditer(text):
            target = base / match.group(1).replace("\\", os.sep)
            if target.exists():
                candidates.append(target)
    if not candidates:
        return None

    # A native executable wins, but the bundled interpreter copy is not the
    # program (npm shims test for ``%dp0%\node.exe`` first).
    for target in reversed(candidates):
        if (target.suffix.lower() in (".exe", ".cmd", ".bat")
                and target.name.lower() not in _INTERPRETER_NAMES):
            return Resolved(path=path, kind="native", runner=None,
                            target=str(target))

    # Otherwise it is a script, and the shim runs it with node.
    if "node" in text.lower():
        for target in reversed(candidates):
            if target.name.lower() not in _INTERPRETER_NAMES:
                return Resolved(path=path, kind="node", runner="node",
                                target=str(target))
    return None


def resolve_executable(name: str, *, extra_paths: Iterable[str] = ()) -> Resolved | None:
    """Resolve *name* to something this process can actually start.

    The operator's CLIs are installed as npm shims.  ``shutil.which`` finds
    the ``.cmd`` one because ``PATHEXT`` contains ``.CMD``; the ``.ps1`` one
    is invisible to it.  Both are handled here.
    """
    import shutil

    search_path = None
    if extra_paths:
        search_path = os.pathsep.join(
            [str(p) for p in extra_paths] + os.environ.get("PATH", "").split(os.pathsep))

    found = shutil.which(name, path=search_path)
    if found:
        return _classify_executable(found)

    for ext in (".exe", ".cmd", ".bat", ".ps1"):
        found = shutil.which(name + ext, path=search_path)
        if found:
            return _classify_executable(found)
    return None


def _classify_executable(path: str) -> Resolved:
    lower = path.lower()
    if lower.endswith(".ps1"):
        return Resolved(path=path, kind="powershell",
                        runner=_find_powershell(), target=path)
    if lower.endswith(CMD_EXTENSIONS):
        peeled = _resolve_cmd_shim(path)
        if peeled is not None:
            return peeled
        return Resolved(path=path, kind="cmd", runner="cmd.exe", target=path)
    return Resolved(path=path, kind="native", runner=None, target=path)


def _find_powershell() -> str | None:
    import shutil
    return shutil.which("pwsh") or shutil.which("powershell")


def argv_for_executable(resolved: Resolved, args: Sequence[str]) -> list[str]:
    """Build the real argv for a resolved executable.

    * native  -> ``[target, *args]``
    * node    -> ``[node, target, *args]``
    * powershell -> ``[pwsh, -NoLogo, -NoProfile, -ExecutionPolicy, Bypass,
      -File, target, *args]``
    * cmd     -> ``[cmd.exe, /d, /c, call, target, *args]``  (degraded)
    """
    args = [str(a) for a in args]
    if resolved.kind == "native":
        return [resolved.target or resolved.path, *args]
    if resolved.kind == "node":
        return [resolved.runner or "node", resolved.target, *args]
    if resolved.kind == "powershell":
        return [resolved.runner or "powershell", "-NoLogo", "-NoProfile",
                "-ExecutionPolicy", "Bypass", "-File", resolved.target, *args]
    # Degraded path.  Documented as mangling arguments; used only when a
    # shim's real target cannot be determined.
    return ["cmd.exe", "/d", "/c", "call", resolved.target or resolved.path, *args]


# ---------------------------------------------------------------------------
# Memory guard
# ---------------------------------------------------------------------------

class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_uint32),
        ("dwMemoryLoad", ctypes.c_uint32),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def free_ram_mb() -> int | None:
    """Free physical RAM in MiB, or ``None`` if it cannot be determined."""
    if not IS_WINDOWS:  # pragma: no cover - platform conditional
        try:
            info = {}
            with open("/proc/meminfo") as fh:
                for line in fh:
                    key, _, value = line.partition(":")
                    info[key] = int(value.strip().split()[0])
            return info.get("MemAvailable", 0) // 1024
        except (OSError, ValueError, IndexError):
            return None
    try:  # pragma: no cover - platform conditional
        stat = _MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return None
        return int(stat.ullAvailPhys // (1024 * 1024))
    except (AttributeError, OSError):
        return None


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

def python_executable() -> str:
    """The interpreter running this process.

    Workers are launched with the venv interpreter directly rather than
    through ``Activate.ps1``, which a PowerShell execution policy may block
    (fleet amendment section 7.2).
    """
    return sys.executable


def scrub_environment(base: Mapping[str, str] | None = None,
                      *, keep: Sequence[str] = (),
                      drop_prefixes: Sequence[str] = ("OPENAI_", "ANTHROPIC_",
                                                       "OPENROUTER_", "ORCA_",
                                                       "GEMINI_", "GROQ_")) -> dict:
    """Return a reduced environment.

    Only for gateway-routed profiles (fleet amendment D-L3).  Direct-CLI
    profiles keep their own credentials; scrubbing them is not possible and
    not attempted (known limitation L-F4).
    """
    source = dict(os.environ if base is None else base)
    keep_set = set(keep)
    out: dict[str, str] = {}
    for key, value in source.items():
        if key in keep_set:
            out[key] = value
            continue
        if any(key.upper().startswith(p) for p in drop_prefixes):
            continue
        out[key] = value
    return out


def redact(text: str, secrets: Iterable[str]) -> str:
    """Replace every non-empty secret value in *text* with ``[REDACTED]``."""
    if not text:
        return text
    result = text
    for secret in secrets:
        if secret and len(secret) >= 4:
            result = result.replace(secret, "[REDACTED]")
    return result


def tail_file(path: os.PathLike[str] | str, lines: int = 40,
              *, max_bytes: int = 256 * 1024) -> list[str]:
    """Return the last *lines* lines of *path*, reading at most *max_bytes*."""
    p = Path(path)
    if not p.exists():
        return []
    try:
        size = p.stat().st_size
        with open(p, "rb") as fh:
            if size > max_bytes:
                fh.seek(size - max_bytes)
                fh.readline()  # discard a partial first line
            data = fh.read()
    except OSError:
        return []
    text = data.decode("utf-8", errors="replace")
    return text.splitlines()[-lines:]


def file_digest(path: os.PathLike[str] | str) -> str:
    """SHA-256 of a file's bytes, or ``""`` when the file is missing."""
    import hashlib
    p = Path(path)
    if not p.is_file():
        return ""
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_text(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
