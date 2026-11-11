"""The single owner of the dispatch line.

The Console, ``pmk dispatch run``, ``pmk project run`` and the canary runner
all drive the same Dispatcher.  More than one of them at once would race the
claim/lease path and produce duplicate assignments, so they share one
sidecar lock under ``.pm/fleet``.

The lock is held only while a process is actually dispatching.  A Console
that is merely open and paused owns nothing, so it cannot block an explicit
CLI owner.  Conversely, an active Console or CLI owns the line and a second
process is refused with ``dispatch_owner_busy``.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from pmk.api import Kernel, KernelError
from pmk.events import Actor
from pmk.plat import FileLock, LockTimeout, atomic_write_text, read_text

from .state import FleetState

OWNER_LOCK_NAME = "dispatch.owner"
OWNER_INFO_NAME = "dispatch.owner.json"


def owner_lock_path(kernel: Kernel, state_path: Path | None = None) -> Path:
    """The sidecar lock path shared by every dispatch owner.

    The lock normally sits beside the project's ``fleet-state.json``.  A
    caller that deliberately uses another state file passes it here so the
    lock still describes the same dispatch line.
    """
    target = Path(state_path) if state_path else kernel.repo.fleet_state_path
    return target.with_name(OWNER_LOCK_NAME)


def owner_info_path(kernel: Kernel, state_path: Path | None = None) -> Path:
    """The sidecar fact file naming the current lock holder, if any.

    The lock itself is the authority.  This file is diagnostic metadata so a
    status view in another process can name the owner without guessing.
    """
    target = Path(state_path) if state_path else kernel.repo.fleet_state_path
    return target.with_name(OWNER_INFO_NAME)


class DispatchOwner:
    """An exclusive, process-held claim on the dispatch line."""

    def __init__(self, kernel: Kernel, role: str,
                 state_path: Path | None = None):
        self.kernel = kernel
        self.role = role
        self._lock = FileLock(owner_lock_path(kernel, state_path), timeout=0.0)
        self._info_path = owner_info_path(kernel, state_path)
        self._held = False

    @classmethod
    def for_kernel(cls, kernel: Kernel, role: str,
                   state_path: Path | None = None) -> "DispatchOwner":
        return cls(kernel, role, state_path=state_path)

    @property
    def lock_path(self) -> Path:
        return self._lock.lock_path

    @property
    def held(self) -> bool:
        return self._held

    def acquire(self) -> "DispatchOwner":
        if self._held:
            return self
        try:
            self._lock.acquire()
        except LockTimeout as exc:
            raise KernelError(
                "dispatch_owner_busy",
                role=self.role,
                lock=str(self.lock_path),
            ) from exc
        self._held = True
        self._write_info()
        return self

    def _write_info(self) -> None:
        """Record the holder; a failure here never blocks dispatch."""
        payload = {
            "role": self.role,
            "pid": os.getpid(),
            "acquired_at": time.time(),
            "lock": str(self.lock_path),
        }
        try:
            atomic_write_text(
                self._info_path,
                json.dumps(payload, ensure_ascii=False) + "\n",
            )
        except OSError:
            pass

    def release(self) -> None:
        if not self._held:
            return
        # Remove the fact file while the lock still excludes another owner,
        # so a reader cannot mistake a released lock for a live one.
        try:
            self._info_path.unlink()
        except OSError:
            pass
        self._lock.release()
        self._held = False

    def __enter__(self) -> "DispatchOwner":
        return self.acquire()

    def __exit__(self, *exc_info) -> None:
        self.release()


def _lock_held(lock_path: Path) -> bool | None:
    """Probe the dispatch lock without waiting.

    ``None`` means the probe itself failed, so the caller reports ``unknown``
    rather than claiming the line is free.
    """
    probe = FileLock(lock_path, timeout=0.0)
    if not probe.lock_path.exists():
        return False
    try:
        probe.acquire()
    except LockTimeout:
        return True
    except OSError:
        return None
    try:
        probe.release()
    except OSError:
        return None
    return False


def owner_status(kernel: Kernel, state_path: Path | None = None) -> dict:
    """Describe the dispatch lock and its active owner, if any.

    ``state`` is one of ``active`` (held, with owner metadata), ``held``
    (held without usable metadata), ``stale`` (metadata survives a released
    lock), ``free`` or ``unknown`` (the probe failed).
    """
    lock_path = owner_lock_path(kernel, state_path)
    info_path = owner_info_path(kernel, state_path)
    info_exists = info_path.exists()
    owner: dict | None = None
    detail = ""
    if info_exists:
        try:
            raw = json.loads(read_text(info_path))
        except (OSError, ValueError) as exc:
            detail = f"cannot read {info_path}: {exc}"
        else:
            if isinstance(raw, dict):
                owner = raw
            else:
                detail = f"{info_path} is not a JSON object"

    held = _lock_held(lock_path)
    if held is None:
        state = "unknown"
    elif held:
        state = "active" if owner is not None else "held"
    else:
        state = "stale" if info_exists else "free"

    return {
        "state": state,
        "held": held,
        "role": str(owner.get("role", "")) if owner else "",
        "pid": owner.get("pid") if owner else None,
        "acquired_at": owner.get("acquired_at") if owner else None,
        "lock": str(FileLock(lock_path).lock_path),
        "detail": detail,
    }


def clear_stale_owner(kernel: Kernel, state_path: Path | None = None) -> dict:
    """Discard abandoned owner metadata while holding the dispatch lock.

    The lock itself is never removed: it is the exclusion primitive, not the
    owner record.  A live owner makes the acquire fail, so this can never
    erase metadata belonging to a running dispatcher.
    """
    lock = FileLock(owner_lock_path(kernel, state_path), timeout=0.0)
    try:
        lock.acquire()
    except LockTimeout as exc:
        status = owner_status(kernel, state_path)
        raise KernelError(
            "dispatch_owner_busy",
            role=status.get("role") or "",
            lock=str(lock.lock_path),
        ) from exc
    except OSError as exc:
        raise KernelError(
            "dispatch_owner_clear_failed",
            lock=str(lock.lock_path),
            detail=str(exc),
        ) from exc

    info_path = owner_info_path(kernel, state_path)
    cleared = False
    try:
        try:
            info_path.unlink()
        except FileNotFoundError:
            pass
        else:
            cleared = True
    except OSError as exc:
        raise KernelError(
            "dispatch_owner_clear_failed",
            lock=str(lock.lock_path),
            detail=str(exc),
        ) from exc
    finally:
        lock.release()

    result = owner_status(kernel, state_path)
    result["cleared"] = cleared
    return result


def resume_dispatch(kernel: Kernel, fleet_state: FleetState, *,
                    reason: str) -> bool:
    """Persist an explicit resume and record why it happened.

    Returns ``True`` only when a paused state was actually cleared, so a
    caller can avoid writing an event for an already-running dispatcher.
    """
    if not fleet_state.dispatch_paused:
        return False
    fleet_state.dispatch_paused = False
    fleet_state.pause_reason = ""
    fleet_state.paused_at = 0.0
    fleet_state.save()
    kernel.record_event("DISPATCH_RESUMED", actor=Actor.human(),
                        payload={"reason": reason})
    return True
