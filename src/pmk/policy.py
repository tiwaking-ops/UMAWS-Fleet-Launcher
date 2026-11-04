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


class PolicyError(RuntimeError):
    """``.pm/policy.toml`` exists but cannot be read or parsed.

    Policy decides *what the gate is* and what every lane may do, so a
    file the Kernel cannot read must stop the line: quietly substituting
    the defaults would run an enforcement regime the operator never
    approved -- the recorded defect ("invalid policy.toml falls back to
    defaults silently", surfaced by the F7 drill; a typo'd policy
    silently changed the merge gate to ``pytest -q``).  Fixed 2026-10-24:
    present-but-unreadable now raises; the file *absent* still loads the
    defaults, as first-boot behaviour.  The Kernel wraps this in
    ``KernelError("policy_invalid")`` so every surface -- CLI, brief,
    sentinel, any event append -- refuses loudly.
    """


def load_policy(repo) -> dict:
    """Load ``.pm/policy.toml``, falling back to the defaults.

    Read with ``utf-8-sig``: the operator edits files with Windows
    PowerShell, whose ``Set-Content -Encoding utf8`` writes a BOM, and
    ``tomllib`` rejects one.

    The fallback applies **only** while the file is absent (first boot).
    A file that exists but cannot be read or parsed raises
    :class:`PolicyError` -- a policy the Kernel cannot read must never
    be silently replaced by a different one.
    """
    path = Path(repo.policy_path)
    if not path.is_file():
        return json.loads(json.dumps(DEFAULT_POLICY))
    try:
        data = tomllib.loads(read_text(path))
    except tomllib.TOMLDecodeError as exc:
        raise PolicyError(f"{path}: invalid TOML: {exc}") from exc
    except OSError as exc:
        raise PolicyError(f"{path}: unreadable: {exc}") from exc
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
    """Load ``agents.toml`` — the Fleet profiles (fleet amendment 12.A).

    Returns ``{"fleet": {...}, "overseer": {...}, "profiles": [...], "errors": [...], "cap_keys": [...]}``.
    An unreadable file yields an empty profile list rather than an
    exception: a broken profile file must not take the Kernel down.

    Validates (collects errors, does not raise):
    - No duplicate profile ids
    - Overseer profile names must match existing profile ids
    - Reports which key enforces the concurrency cap (fleet.max_total_agents vs fleet.fleet_cap)
    """
    path = Path(repo.agents_path)
    if not path.is_file():
        return {"fleet": {}, "overseer": {}, "profiles": [], "errors": ["agents.toml: file not found"], "cap_keys": []}
    try:
        text = read_text(path)
        data = tomllib.loads(text)
    except OSError as exc:
        return {"fleet": {}, "overseer": {}, "profiles": [], "errors": [f"agents.toml: read error: {exc}"], "cap_keys": []}
    except tomllib.TOMLDecodeError as exc:
        # tomllib.TOMLDecodeError has .lineno and .colno attributes (Python 3.11+)
        line_info = ""
        if hasattr(exc, 'lineno') and exc.lineno:
            line_info = f" at line {exc.lineno}"
            if hasattr(exc, 'colno') and exc.colno:
                line_info += f", column {exc.colno}"
        return {"fleet": {}, "overseer": {}, "profiles": [], "errors": [f"agents.toml: TOML parse error{line_info}: {exc}"], "cap_keys": []}

    profiles = list(data.get("profile", []) or [])
    fleet = data.get("fleet", {}) or {}
    overseer = data.get("overseer", {}) or {}

    errors: list[str] = []

    # R4: Validate no duplicate profile ids
    seen_ids = set()
    duplicate_ids = []
    for profile in profiles:
        pid = profile.get("id")
        if pid:
            if pid in seen_ids:
                duplicate_ids.append(pid)
            else:
                seen_ids.add(pid)
    if duplicate_ids:
        errors.append(f"agents.toml: duplicate profile ids: {', '.join(duplicate_ids)}")

    # R4: Validate overseer profile names exist
    overseer_profiles = overseer.get("profiles", []) if isinstance(overseer, dict) else []
    if not isinstance(overseer_profiles, list):
        overseer_profiles = []
    unknown_overseer = [name for name in overseer_profiles if name not in seen_ids]
    if unknown_overseer:
        errors.append(f"agents.toml: overseer profiles not found in profiles: {', '.join(unknown_overseer)}")

    # R4: Report which key enforces concurrency cap
    cap_keys = []
    if "max_total_agents" in fleet:
        cap_keys.append("fleet.max_total_agents")
    if "fleet_cap" in fleet:
        cap_keys.append("fleet.fleet_cap")

    return {
        "fleet": fleet,
        "overseer": overseer,
        "profiles": profiles,
        "errors": errors,
        "cap_keys": cap_keys,
    }


def enforce_fleet_config(kernel, agents: dict | None = None) -> tuple[bool, list[str]]:
    """Enforce fleet configuration errors at runtime.

    Called by dispatcher, overseer, and console at startup. On errors:
    - Records ONE FLEET_CONFIG_ERRORS event (deduplicated by hash of error list)
    - Refuses leases from profiles named in errors (all profiles on file-level error)
    - Returns (False, errors) if there are errors, (True, []) otherwise.

    The dispatcher/overseer/console should check the return value and refuse
    to start if there are errors.

    Note: Uses kernel.events() (normal read path) rather than read_all(repair=True)
    to avoid torn-tail repair on a read path. The repair=True path is intended
    for recovery scenarios (e.g., sentinel checking a potentially corrupted log)
    and may truncate a partially-written event. Using the normal read path
    ensures we don't accidentally truncate a partially-written event during
    normal startup.
    """
    from pmk.events import Actor
    import hashlib

    if agents is None:
        agents = load_agents(kernel.repo)

    errors = agents.get("errors", [])
    if not errors:
        return True, []

    # Deduplicate: compute hash of sorted error list
    error_hash = hashlib.sha256("\n".join(sorted(errors)).encode("utf-8")).hexdigest()[:16]

    # Check if we already recorded this exact error set
    events = kernel.events()
    for ev in reversed(events):
        if ev.type == "FLEET_CONFIG_ERRORS":
            payload_hash = ev.payload.get("error_hash", "")
            if payload_hash == error_hash:
                # Already recorded this error set
                return False, errors

    # Record the error event
    kernel.record_event("FLEET_CONFIG_ERRORS", actor=Actor.kernel(),
                        payload={"errors": errors, "error_hash": error_hash})

    return False, errors


def get_profiles_with_errors(agents: dict) -> set[str]:
    """Return the set of profile ids that should be refused due to config errors.

    - On file-level errors (TOML parse, missing file, read error), refuse ALL profiles.
    - On duplicate id errors, refuse the duplicate profiles.
    - On unknown overseer profile errors, refuse the unknown profiles.
    """
    refused = set()
    errors = agents.get("errors", [])

    if not errors:
        return refused

    profiles = agents.get("profiles", [])

    # Check for file-level errors (these affect all profiles)
    for err in errors:
        if err.startswith("agents.toml: file not found") or \
           err.startswith("agents.toml: read error:") or \
           err.startswith("agents.toml: TOML parse error"):
            # File-level error - refuse all profiles
            refused.update(p.get("id") for p in profiles if p.get("id"))
            return refused

    for err in errors:
        if "duplicate profile ids:" in err:
            # Extract duplicate ids
            dup_part = err.split("duplicate profile ids:", 1)[1].strip()
            for pid in [p.strip() for p in dup_part.split(",")]:
                refused.add(pid)
        elif "overseer profiles not found in profiles:" in err:
            # Extract unknown overseer profiles
            unk_part = err.split("overseer profiles not found in profiles:", 1)[1].strip()
            for name in [n.strip() for n in unk_part.split(",")]:
                refused.add(name)

    return refused


def profile_by_id(repo, profile_id: str) -> dict | None:
    for profile in load_agents(repo)["profiles"]:
        if profile.get("id") == profile_id:
            return profile
    return None
