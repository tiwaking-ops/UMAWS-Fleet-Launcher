"""Fleet-wide state (fleet amendment D-L13).

Profile cooling and enable/disable state is **fleet-wide**, not per-project:
an exhausted model is exhausted for every project.  It is stored in the
application state directory, not in the repository, so it survives across
projects and is never committed.

On Windows the state directory is ``%LOCALAPPDATA%\\umaws``; elsewhere it
is ``~/.local/state/umaws``.

The state is written atomically.  A crash mid-write leaves the previous
state intact rather than a truncated file.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from pmk.plat import atomic_write_text

STATE_VERSION = 1


def state_dir() -> Path:
    """The application state directory."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / "umaws"
        return Path.home() / "AppData" / "Local" / "umaws"
    base = os.environ.get("XDG_STATE_HOME")
    if base:
        return Path(base) / "umaws"
    return Path.home() / ".local" / "state" / "umaws"


def state_path() -> Path:
    return state_dir() / "fleet-state.json"


@dataclass
class ProfileState:
    """The mutable state of one profile."""

    profile_id: str
    enabled: bool = True
    cooling_until: float = 0.0        # epoch seconds
    cooldown_count: int = 0
    last_failure_class: str = ""
    last_failure_at: float = 0.0
    probe_pending: bool = False
    runs: int = 0
    failures: int = 0
    last_used: float = 0.0
    failure_counts: dict = field(default_factory=dict)
    note: str = ""

    def cooling(self, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        return self.cooling_until > now

    def cooling_remaining(self, now: float | None = None) -> int:
        now = time.time() if now is None else now
        return max(0, int(self.cooling_until - now))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, obj: dict) -> "ProfileState":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in obj.items() if k in known})


@dataclass
class FleetState:
    """Everything the Fleet remembers between runs."""

    version: int = STATE_VERSION
    profiles: dict = field(default_factory=dict)     # id -> ProfileState
    dispatch_paused: bool = False
    pause_reason: str = ""
    paused_at: float = 0.0
    network_failures: list = field(default_factory=list)   # provider names
    path: Path | None = None

    # -- persistence ------------------------------------------------------
    @classmethod
    def load(cls, path: Path | None = None) -> "FleetState":
        target = Path(path) if path else state_path()
        state = cls(path=target)
        try:
            raw = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return state
        state.version = int(raw.get("version", STATE_VERSION))
        state.dispatch_paused = bool(raw.get("dispatch_paused", False))
        state.pause_reason = str(raw.get("pause_reason", ""))
        state.paused_at = float(raw.get("paused_at", 0.0))
        state.network_failures = list(raw.get("network_failures", []))
        for profile_id, obj in (raw.get("profiles") or {}).items():
            state.profiles[profile_id] = ProfileState.from_dict(obj)
        return state

    def save(self) -> Path:
        target = Path(self.path) if self.path else state_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self.version,
            "dispatch_paused": self.dispatch_paused,
            "pause_reason": self.pause_reason,
            "paused_at": self.paused_at,
            "network_failures": self.network_failures,
            "profiles": {k: v.to_dict() for k, v in self.profiles.items()},
        }
        atomic_write_text(target, json.dumps(payload, indent=2,
                                             ensure_ascii=False) + "\n")
        return target

    # -- profile access ---------------------------------------------------
    def profile(self, profile_id: str) -> ProfileState:
        if profile_id not in self.profiles:
            self.profiles[profile_id] = ProfileState(profile_id=profile_id)
        return self.profiles[profile_id]

    def enable(self, profile_id: str, note: str = "") -> ProfileState:
        state = self.profile(profile_id)
        state.enabled = True
        state.cooling_until = 0.0
        state.cooldown_count = 0
        state.probe_pending = False
        state.note = note
        return state

    def disable(self, profile_id: str, note: str = "") -> ProfileState:
        state = self.profile(profile_id)
        state.enabled = False
        state.note = note
        return state

    def cool(self, profile_id: str, seconds: float, note: str = "") -> ProfileState:
        state = self.profile(profile_id)
        state.cooling_until = time.time() + float(seconds)
        state.cooldown_count += 1
        state.note = note
        return state

    def record_failure(self, profile_id: str, failure_class: str,
                       provider: str = "") -> ProfileState:
        state = self.profile(profile_id)
        state.failures += 1
        state.last_failure_class = failure_class
        state.last_failure_at = time.time()
        state.failure_counts[failure_class] = (
            state.failure_counts.get(failure_class, 0) + 1)
        if provider and provider not in self.network_failures:
            self.network_failures.append(provider)
        return state

    def record_run(self, profile_id: str) -> ProfileState:
        state = self.profile(profile_id)
        state.runs += 1
        return state
