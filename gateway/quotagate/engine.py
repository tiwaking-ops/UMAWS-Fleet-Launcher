"""The quota engine (QuotaGate v1.1 section 3, milestone M2).

The most important milestone in the gateway, and the one the pilot's
acceptance tests Q1 (DST) and Q2 (account-wide scopes) exercise.

The rules, in one paragraph:

* A request is admissible only if **every** applicable rule at **every**
  scope has headroom.
* Reservation takes one unit at each applicable scope **atomically**.  The
  engine is a single process with one lock, so atomicity is a property of
  the lock rather than of a distributed protocol.
* Reconciliation and refund apply to **all** scopes.
* The earliest-available time for a deployment is the **latest** of its
  blocking rules' reset times.
* All time goes through an injectable clock.

Windows: ``rolling_60s``, ``rolling_24h``, ``fixed_daily`` (a calendar date
in a named timezone, via ``zoneinfo``), ``fixed_monthly`` and
``fixed_interval``.
"""

from __future__ import annotations

import json
import math
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from pmk.clock import Clock

from .config import (METRIC_REQUESTS, METRIC_TOKENS, SCOPE_DEPLOYMENT,
                     WINDOW_FIXED_DAILY, WINDOW_FIXED_INTERVAL,
                     WINDOW_FIXED_MONTHLY, WINDOW_ROLLING_24H,
                     WINDOW_ROLLING_60S, Deployment, GatewayConfig, QuotaRule)
from .errors import (AUTH, MODEL_GONE, NO_QUOTA, RATE_DAY, RATE_MINUTE,
                     TRANSIENT, TRANSIENT_BACKOFF, UNKNOWN_429)

SCHEMA = """
CREATE TABLE IF NOT EXISTS usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    deployment_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    amount INTEGER NOT NULL,
    at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS usage_scope_at ON usage(scope_key, metric, at);

CREATE TABLE IF NOT EXISTS reservations (
    id TEXT PRIMARY KEY,
    deployment_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    state TEXT NOT NULL,
    tokens_reserved INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cooldowns (
    deployment_id TEXT PRIMARY KEY,
    failure_class TEXT NOT NULL,
    until REAL NOT NULL,
    reason TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS disabled (
    deployment_id TEXT PRIMARY KEY,
    reason TEXT NOT NULL DEFAULT ''
);
"""


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

@dataclass
class Admission:
    """Whether a request may proceed, and why not if it may not."""

    allowed: bool = True
    rule: QuotaRule | None = None
    used: int = 0
    requested: int = 0
    reset_at: float | None = None
    reason: str = ""

    def to_dict(self) -> dict:
        return {"allowed": self.allowed,
                "rule": self.rule.to_dict() if self.rule else None,
                "used": self.used, "requested": self.requested,
                "reset_at": self.reset_at, "reason": self.reason}


@dataclass
class Reservation:
    """A held reservation, across every applicable scope."""

    id: str
    deployment_id: str
    requests: int = 0
    tokens: int = 0
    charges: list = field(default_factory=list)   # (scope_key, metric, amount)
    created_at: float = 0.0
    state: str = "held"

    def to_dict(self) -> dict:
        return {"id": self.id, "deployment": self.deployment_id,
                "requests": self.requests, "tokens": self.tokens,
                "charges": [{"scope_key": s, "metric": m, "amount": a}
                            for s, m, a in self.charges],
                "state": self.state}


class QuotaExceeded(RuntimeError):
    """The request is not admissible."""

    def __init__(self, admission: Admission):
        super().__init__(admission.reason or "quota exceeded")
        self.admission = admission


# ---------------------------------------------------------------------------
# The ledger
# ---------------------------------------------------------------------------

class Ledger:
    """The SQLite ledger (QuotaGate v1.1 milestone M0)."""

    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    # -- usage ---------------------------------------------------------
    def add_usage(self, reservation_id: str, scope_key: str,
                  deployment_id: str, metric: str, amount: int,
                  at: float) -> None:
        self.db.execute(
            "INSERT INTO usage (reservation_id, scope_key, deployment_id, "
            "metric, amount, at) VALUES (?, ?, ?, ?, ?, ?)",
            (reservation_id, scope_key, deployment_id, metric, amount, at))
        self.db.commit()

    def used_since(self, scope_key: str, metric: str, since: float) -> int:
        row = self.db.execute(
            "SELECT COALESCE(SUM(amount), 0) AS used FROM usage "
            "WHERE scope_key = ? AND metric = ? AND at >= ?",
            (scope_key, metric, since)).fetchone()
        return int(row["used"])

    def adjust(self, reservation_id: str, scope_key: str, metric: str,
               delta: int) -> None:
        if delta == 0:
            return
        self.db.execute(
            "UPDATE usage SET amount = amount + ? "
            "WHERE reservation_id = ? AND scope_key = ? AND metric = ?",
            (delta, reservation_id, scope_key, metric))
        self.db.commit()

    # -- reservations --------------------------------------------------
    def open_reservation(self, reservation_id: str, deployment_id: str,
                         created_at: float, tokens: int) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO reservations (id, deployment_id, "
            "created_at, state, tokens_reserved) VALUES (?, ?, ?, 'held', ?)",
            (reservation_id, deployment_id, created_at, tokens))
        self.db.commit()

    def close_reservation(self, reservation_id: str, state: str) -> None:
        self.db.execute("UPDATE reservations SET state = ? WHERE id = ?",
                        (state, reservation_id))
        self.db.commit()

    # -- cooldowns and disables ----------------------------------------
    def set_cooldown(self, deployment_id: str, failure_class: str,
                     until: float, reason: str = "") -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO cooldowns (deployment_id, failure_class, "
            "until, reason) VALUES (?, ?, ?, ?)",
            (deployment_id, failure_class, until, reason))
        self.db.commit()

    def cooldown(self, deployment_id: str) -> dict | None:
        row = self.db.execute(
            "SELECT deployment_id, failure_class, until, reason FROM cooldowns "
            "WHERE deployment_id = ?", (deployment_id,)).fetchone()
        return dict(row) if row else None

    def clear_cooldown(self, deployment_id: str) -> None:
        self.db.execute("DELETE FROM cooldowns WHERE deployment_id = ?",
                        (deployment_id,))
        self.db.commit()

    def disable(self, deployment_id: str, reason: str = "") -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO disabled (deployment_id, reason) "
            "VALUES (?, ?)", (deployment_id, reason))
        self.db.commit()

    def is_disabled(self, deployment_id: str) -> bool:
        row = self.db.execute(
            "SELECT 1 FROM disabled WHERE deployment_id = ?",
            (deployment_id,)).fetchone()
        return row is not None


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------

def window_start(window: str, tz_name: str, now: float,
                interval: int = 0) -> float:
    """The start of the window that *now* falls in.

    ``fixed_daily`` is a calendar date **in the rule's own timezone**, which
    is what makes the DST test meaningful: the local day is 23 or 25 hours
    long twice a year, and the quota must still reset at local midnight.
    """
    if window == WINDOW_ROLLING_60S:
        return now - 60.0
    if window == WINDOW_ROLLING_24H:
        return now - 86400.0
    if window == WINDOW_FIXED_INTERVAL:
        span = max(1, interval)
        return math.floor(now / span) * span
    zone = ZoneInfo(tz_name or "UTC")
    local = datetime.fromtimestamp(now, tz=zone)
    if window == WINDOW_FIXED_MONTHLY:
        start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:                                   # fixed_daily
        start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.timestamp()


def window_reset(window: str, tz_name: str, now: float,
                 interval: int = 0) -> float:
    """When the window that *now* falls in ends."""
    if window == WINDOW_ROLLING_60S:
        return now + 60.0
    if window == WINDOW_ROLLING_24H:
        return now + 86400.0
    if window == WINDOW_FIXED_INTERVAL:
        span = max(1, interval)
        return (math.floor(now / span) + 1) * span
    zone = ZoneInfo(tz_name or "UTC")
    local = datetime.fromtimestamp(now, tz=zone)
    if window == WINDOW_FIXED_MONTHLY:
        if local.month == 12:
            nxt = local.replace(year=local.year + 1, month=1, day=1, hour=0,
                                minute=0, second=0, microsecond=0)
        else:
            nxt = local.replace(month=local.month + 1, day=1, hour=0,
                                minute=0, second=0, microsecond=0)
    else:                                   # fixed_daily
        nxt = (local + timedelta(days=1)).replace(hour=0, minute=0, second=0,
                                                   microsecond=0)
    return nxt.timestamp()


def to_iso(epoch: float | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------

class QuotaEngine:
    """The hierarchical quota engine."""

    def __init__(self, config: GatewayConfig, ledger: Ledger | None = None,
                 clock: Clock | None = None):
        self.config = config
        self.ledger = ledger or Ledger()
        self.clock = clock or Clock()
        self._lock = threading.RLock()

    # -- reading -------------------------------------------------------
    def now(self) -> float:
        return self.clock.now().timestamp()

    def used(self, rule: QuotaRule, deployment: Deployment,
             at: float | None = None) -> int:
        at = self.now() if at is None else at
        scope_key = self.config.scope_key(rule, deployment)
        since = window_start(rule.window, rule.timezone, at,
                             rule.interval_seconds)
        return self.ledger.used_since(scope_key, rule.metric, since)

    def applicable(self, deployment: Deployment,
                   metric: str) -> list[tuple[QuotaRule, str]]:
        """The rules that apply to *deployment* for *metric*, with their keys."""
        out = []
        for rule in self.config.rules_for(deployment):
            if rule.metric != metric:
                continue
            if not rule.known:
                # A limit of 0 or absent means *unknown*, not zero.
                continue
            out.append((rule, self.config.scope_key(rule, deployment)))
        return out

    # -- admission ------------------------------------------------------
    def check(self, deployment: Deployment, metric: str = METRIC_REQUESTS,
              amount: int = 1) -> Admission:
        """Is this request admissible?"""
        for rule, scope_key in self.applicable(deployment, metric):
            used = self.used(rule, deployment)
            if used + amount > rule.limit:
                reset = window_reset(rule.window, rule.timezone, self.now(),
                                     rule.interval_seconds)
                return Admission(
                    allowed=False, rule=rule, used=used, requested=amount,
                    reset_at=reset,
                    reason=(f"{rule.scope} limit {rule.limit} "
                            f"{rule.metric}/{rule.window} reached "
                            f"(used {used})"))
        return Admission(allowed=True)

    def earliest_available(self, deployment: Deployment) -> float | None:
        """When can this deployment take a call again?

        The **latest** of the blocking rules' reset times, because every
        rule must have headroom before the deployment is usable again.
        """
        now = self.now()
        latest: float | None = None
        for metric in (METRIC_REQUESTS, METRIC_TOKENS):
            for rule, _key in self.applicable(deployment, metric):
                used = self.used(rule, deployment)
                if used >= rule.limit:
                    reset = window_reset(rule.window, rule.timezone, now,
                                         rule.interval_seconds)
                    latest = reset if latest is None else max(latest, reset)
        cooldown = self.ledger.cooldown(deployment.id)
        if cooldown and cooldown["until"] > now:
            until = float(cooldown["until"])
            latest = until if latest is None else max(latest, until)
        return latest

    # -- reservation ----------------------------------------------------
    def reserve(self, deployment: Deployment, *, requests: int = 1,
                tokens: int = 0) -> Reservation:
        """Take one unit at every applicable scope, atomically.

        Raises :class:`QuotaExceeded` if any scope lacks headroom.  The
        check and the write happen under one lock, so two concurrent
        callers cannot both pass the check and then both write.
        """
        with self._lock:
            now = self.now()
            for metric, amount in ((METRIC_REQUESTS, requests),
                                   (METRIC_TOKENS, tokens)):
                if amount <= 0:
                    continue
                admission = self.check(deployment, metric, amount)
                if not admission.allowed:
                    raise QuotaExceeded(admission)

            reservation_id = uuid.uuid4().hex
            reservation = Reservation(id=reservation_id,
                                      deployment_id=deployment.id,
                                      requests=requests, tokens=tokens,
                                      created_at=now)
            self.ledger.open_reservation(reservation_id, deployment.id, now,
                                         tokens)
            for metric, amount in ((METRIC_REQUESTS, requests),
                                   (METRIC_TOKENS, tokens)):
                if amount <= 0:
                    continue
                for rule, scope_key in self.applicable(deployment, metric):
                    self.ledger.add_usage(reservation_id, scope_key,
                                          deployment.id, metric, amount, now)
                    reservation.charges.append((scope_key, metric, amount))
            return reservation

    def commit(self, reservation: Reservation, *, tokens: int | None = None) -> None:
        """Reconcile a reservation with the reported usage.

        The token charge is adjusted at every scope; the request charge
        stays as reserved.
        """
        with self._lock:
            if tokens is not None and tokens != reservation.tokens:
                delta = tokens - reservation.tokens
                for scope_key, metric, amount in reservation.charges:
                    if metric == METRIC_TOKENS:
                        self.ledger.adjust(reservation.id, scope_key, metric,
                                           delta)
            self.ledger.close_reservation(reservation.id, "committed")
            reservation.state = "committed"

    def refund(self, reservation: Reservation) -> None:
        """Give the units back at every scope."""
        with self._lock:
            for scope_key, metric, amount in reservation.charges:
                self.ledger.adjust(reservation.id, scope_key, metric, -amount)
            self.ledger.close_reservation(reservation.id, "refunded")
            reservation.state = "refunded"

    # -- cooldowns ------------------------------------------------------
    def apply_failure(self, deployment: Deployment, failure_class: str, *,
                      retry_after: float | None = None,
                      reset_at: float | None = None,
                      reason: str = "") -> float | None:
        """Apply the failure class's consequence.  Returns the cooldown end.

        * ``rate_minute`` — honour ``Retry-After``, capped at about 90 s.
        * ``rate_day`` — cool down until the blocking rule's reset.
        * ``no_quota`` — disable the deployment.
        * ``transient`` — backoff 5 s, 15 s, 45 s, up to 5 minutes.
        * ``auth`` — disable the account (the deployment with it).
        * ``model_gone`` — disable the deployment.
        * ``unknown_429`` — 60 seconds.
        """
        now = self.now()
        until: float | None = None

        if failure_class == RATE_MINUTE:
            until = now + min(retry_after if retry_after is not None else 60.0, 90.0)
        elif failure_class == RATE_DAY:
            earliest = reset_at or self.earliest_available(deployment)
            until = earliest if earliest is not None else now + 86400.0
        elif failure_class == TRANSIENT:
            until = now + TRANSIENT_BACKOFF[0]
        elif failure_class == UNKNOWN_429:
            until = now + 60.0
        elif failure_class == NO_QUOTA:
            self.ledger.disable(deployment.id, reason or "no quota")
            return None
        elif failure_class == AUTH:
            self.ledger.disable(deployment.id, reason or "authentication failed")
            return None
        elif failure_class == MODEL_GONE:
            self.ledger.disable(deployment.id, reason or "model removed")
            return None

        if until is not None:
            self.ledger.set_cooldown(deployment.id, failure_class, until, reason)
        return until

    def is_usable(self, deployment: Deployment) -> tuple[bool, str]:
        """Can this deployment take a call right now?"""
        if self.ledger.is_disabled(deployment.id):
            return False, "disabled"
        cooldown = self.ledger.cooldown(deployment.id)
        if cooldown and float(cooldown["until"]) > self.now():
            remaining = int(float(cooldown["until"]) - self.now())
            return False, f"cooling for {remaining}s ({cooldown['failure_class']})"
        admission = self.check(deployment, METRIC_REQUESTS, 1)
        if not admission.allowed:
            return False, admission.reason
        return True, ""

    def status(self, deployment: Deployment) -> dict:
        """The per-scope remaining units, for the availability endpoint."""
        out = {}
        for metric in (METRIC_REQUESTS, METRIC_TOKENS):
            for rule, scope_key in self.applicable(deployment, metric):
                used = self.used(rule, deployment)
                out[f"{scope_key}:{metric}"] = {
                    "scope": rule.scope,
                    "metric": metric,
                    "window": rule.window,
                    "limit": rule.limit,
                    "used": used,
                    "remaining": max(0, rule.limit - used),
                }
        cooldown = self.ledger.cooldown(deployment.id)
        return {
            "deployment": deployment.id,
            "provider": deployment.provider,
            "model": deployment.model,
            "account": deployment.account,
            "family": deployment.family,
            "state": "disabled" if self.ledger.is_disabled(deployment.id)
                     else "cooling" if cooldown and float(cooldown["until"]) > self.now()
                     else "ready",
            "scopes": out,
            "earliest_available_utc": to_iso(self.earliest_available(deployment)),
        }
