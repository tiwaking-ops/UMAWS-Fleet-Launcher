"""Policy, pins, and the policy hash (pilot v1 sections 9.6, D-P3, D-L3).

Policy is human-edited TOML.  It is **class K**: hash-pinned, and changing
it needs a two-key event.  The policy hash is stamped on every event, so
the log records which policy was in force when each decision was made.

The fleet amendment D-L3 changes one thing: environment scrubbing applies
**only** to profiles with ``via_gateway = true``.  Direct-CLI profiles keep
their own credentials in their own configuration.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

from .events import canonical_json
from .plat import read_text

#: Files that are hash-pinned and protected by invariant I8'.
PINNED_FILES = (".pm/constitution.md", ".pm/policy.toml")

#: The default policy, used when the file is absent.
DEFAULT_POLICY: dict = {
    "version": "p-unset",
    "project": {"name": "umaws-fleet", "data_class": "internal"},
    "envelopes": {"autonomy_ceiling": "R2", "external_effects": "none",
                  "spend": {"per_day": 0, "per_task": 0}},
    "gateway": {"base_url": "http://127.0.0.1:8766/v1", "enabled": False,
                "lanes": []},
    "context_sync": {"mode": "dry-run", "managed_paths": [], "lint": True,
                     "score_non_regression_tolerance": 1, "max_diff_lines": 400,
                     "max_agents_md_tokens": 3000, "on_violation": "auto_revert",
                     "hooks_in_worker_worktrees": False, "providers_allow": []},
    "gate": {"cmd": "pytest -q"},
    "lease": {"heartbeat_seconds": 60, "ttl_minutes": 20, "renew_every": 60},
    "worktree": {"root": "work", "short_root": False},
    "harness": {"poll_seconds": 2, "renew_digest": True},
    "recovery": {
        "network_retry_delays_s": [30, 120, 600],
        "quota_cooldown_s": 3600, "quota_cooldown_max_s": 86400,
        "quota_cooldown_probe": True,
        "unknown_retry_once": True, "unknown_cooldown_s": 900,
        "unknown_cooldown_after": 2, "unknown_cooldown_window_s": 600,
        "stall_cooldown_s": 1800, "stall_window_s": 3600, "stall_after": 2,
        "network_circuit_breaker_providers": 3,
        "network_circuit_breaker_window_s": 120,
        "dispatch_paused_resume_urls": [],
        "fix_rounds": 2, "max_restarts_per_task": 5,
        "max_tasks_created_per_wake": 50, "max_replan_rounds": 3,
        "max_total_tasks": 500, "no_profile_minutes": 30,
    },
    "context": {"max_free_ram_mb": 2048, "views_debounce_s": 5},
    "sentinel": {"stop_on": ["I1", "I3", "I6", "I8'"]},
}


def load_policy(repo) -> dict:
    """Load ``.pm/policy.toml``, falling back to the defaults.

    Read with ``utf-8-sig``: the operator edits files with Windows
    PowerShell, whose ``Set-Content -Encoding utf8`` writes a BOM, and
    ``tomllib`` rejects one.
    """
    path = Path(repo.policy_path)
    if not path.is_file():
        return json.loads(json.dumps(DEFAULT_POLICY))
    try:
        data = tomllib.loads(read_text(path))
    except (OSError, tomllib.TOMLDecodeError):
        return json.loads(json.dumps(DEFAULT_POLICY))
    merged = json.loads(json.dumps(DEFAULT_POLICY))
    merged.update(data)
    return merged


def policy_hash(policy: dict) -> str:
    """SHA-256 of the canonical policy document."""
    return hashlib.sha256(canonical_json(policy).encode("utf-8")).hexdigest()


def write_pins(repo) -> Path:
    """Write ``.pm/pins.sha256`` for the pinned files (pilot v1 section 7.6).

    The fleet amendment section 9.3 replaces ``sha256sum`` with Python's
    ``hashlib`` because the operator is on Windows and ``sha256sum`` is not
    reliably present.
    """
    lines = []
    for relative in PINNED_FILES:
        path = Path(repo.root) / relative
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {relative}")
    target = Path(repo.pins_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return target


def check_pins(repo) -> dict:
    """Invariant I8': pinned files match their recorded hashes."""
    pins_path = Path(repo.pins_path)
    if not pins_path.is_file():
        return {"ok": False, "reason": "pins file missing",
                "mismatches": [], "checked": 0}
    mismatches = []
    checked = 0
    for line in read_text(pins_path).splitlines():
        line = line.strip()
        if not line:
            continue
        expected, _, relative = line.partition("  ")
        if not relative:
            expected, _, relative = line.partition(" ")
        path = Path(repo.root) / relative.strip()
        checked += 1
        if not path.is_file():
            mismatches.append({"file": relative.strip(), "reason": "missing"})
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected.strip():
            mismatches.append({"file": relative.strip(),
                               "expected": expected.strip(), "actual": actual})
    return {"ok": not mismatches, "mismatches": mismatches, "checked": checked}


def load_agents(repo) -> dict:
    """Load ``agents.toml`` â€” the Fleet profiles (fleet amendment 12.A).

    Returns ``{"fleet": {...}, "overseer": {...}, "profiles": [...]}``.
    An unreadable file yields an empty profile list rather than an
    exception: a broken profile file must not take the Kernel down.
    """
    path = Path(repo.agents_path)
    if not path.is_file():
        return {"fleet": {}, "overseer": {}, "profiles": []}
    try:
        data = tomllib.loads(read_text(path))
    except (OSError, tomllib.TOMLDecodeError):
        return {"fleet": {}, "overseer": {}, "profiles": []}
    return {
        "fleet": data.get("fleet", {}) or {},
        "overseer": data.get("overseer", {}) or {},
        "profiles": list(data.get("profile", []) or []),
    }


def profile_by_id(repo, profile_id: str) -> dict | None:
    for profile in load_agents(repo)["profiles"]:
        if profile.get("id") == profile_id:
            return profile
    return None
