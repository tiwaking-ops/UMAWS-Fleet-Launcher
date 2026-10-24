"""QuotaGate M1: Passthrough proxy with live capture.

This is milestone M1: the gateway forwards to an upstream, enforces
locally-declared limits, and captures usage and latency.

What the upstream turned out to be (measured, not assumed - see
``pilot/spikes/m1-upstream.md``):

* It serves ``/models`` and ``/chat/completions``, but **``/v1/*`` returns
  503 or hangs**.  So the proxy strips the ``/v1`` prefix an OpenAI client
  assumes is there.
* It publishes a full ``usage`` block and an ``x-omniroute-decision``
  header naming the provider actually used, so usage *is* capturable.
* It publishes **no rate-limit headers at all** - no ``x-ratelimit-*``, no
  ``retry-after``.  So limits are declared locally, not learned.
* The alias ``auto/cheap`` timed out at 45 s while ``auto/best-free``
  answered in about 1 s, so a deadline per request is mandatory.

Author: OpenCode.  Date: 2026-10-23.  Authorised: operator (M1 approved).
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import sqlite3
import time
from pathlib import Path

import httpx
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from pmk.clock import Clock
from quotagate.config import GatewayConfig
from quotagate.engine import Ledger, QuotaEngine, QuotaExceeded
from quotagate.latency import LatencyLedger
from quotagate.provenance import (TASK_HEADER, ProvenanceLedger,
                                  served_from_response)
from quotagate.routing import (HEADROOM, USE_IT_OR_LOSE_IT, ROUND_ROBIN,
                                PRIORITY, _remaining, route)

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

_config: GatewayConfig | None = None
_engine: QuotaEngine | None = None
_latency: LatencyLedger | None = None
_provenance: ProvenanceLedger | None = None
_upstream_url = os.environ.get("QUOTAGATE_UPSTREAM",
                               "http://127.0.0.1:20128")
_timeout_s = 60.0

# M5: Events outbox, capability tokens, config hash
_events_db_path = os.environ.get("QUOTAGATE_EVENTS_DB", ":memory:")
_config_hash_cached: str | None = None
_hmac_secret: bytes | None = None


def get_provenance() -> ProvenanceLedger:
    global _provenance
    if _provenance is None:
        _provenance = ProvenanceLedger()
    return _provenance


def get_config() -> GatewayConfig:
    global _config, _timeout_s
    if _config is None:
        path = os.environ.get("QUOTAGATE_CONFIG")
        _config = GatewayConfig.load(path or Path(__file__).with_name("config.toml"))
        _timeout_s = float(_config.providers.get("_gate", {}).get("timeout_s", 60))
    return _config


def get_engine() -> QuotaEngine:
    global _engine
    if _engine is None:
        _engine = QuotaEngine(get_config(), ledger=Ledger(), clock=Clock())
    return _engine


def get_latency() -> LatencyLedger:
    global _latency
    if _latency is None:
        _latency = LatencyLedger()
    return _latency


def timeout() -> float:
    get_config()             # ensures _timeout_s is populated
    return _timeout_s


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_v1(path: str) -> str:
    """Remove the ``/v1`` prefix an OpenAI client assumes is present.

    The upstream returns 503 on ``/v1/models`` and hangs on
    ``/v1/chat/completions``, so a proxy that forwards the path untouched
    breaks every standard OpenAI SDK.
    """
    return path[3:] if path.startswith("/v1/") else path


def _forward_headers(request) -> dict:
    """The upstream-safe copy of the client's headers.

    ``Host`` and ``Content-Length`` describe the *client's* connection and
    would corrupt the proxied one, so they are dropped.
    """
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in ("host", "content-length")}
    headers["X-QuotaGate-Proxy"] = "m1"
    return headers


def _upstream(deployment, path: str) -> str:
    """Build the upstream URL, rewriting the path for that upstream's style."""
    config = get_config()
    return f"{config.upstream_url(deployment)}{config.rewrite_path(deployment, path)}"


def _error(message: str, status: int, **extra):
    return JSONResponse({"error": message, **extra}, status_code=status)


def _earliest_available_all(engine: QuotaEngine, combo) -> str | None:
    """Earliest available time across all deployments in a combo."""
    from quotagate.engine import to_iso
    earliest: float | None = None
    for dep_id in combo.deployments:
        dep = engine.config.deployment(dep_id)
        if dep:
            avail = engine.earliest_available(dep)
            if avail:
                earliest = avail if earliest is None else min(earliest, avail)
    return to_iso(earliest) if earliest else None


def _structured_429(admission, combo, requested, strategy) -> JSONResponse:
    """Return a structured 429 with earliest_available_utc."""
    from quotagate.errors import all_exhausted
    from quotagate.engine import to_iso
    earliest = admission.reset_at
    if combo and hasattr(combo, 'deployments'):
        for dep_id in combo.deployments:
            dep = get_engine().config.deployment(dep_id)
            if dep:
                avail = get_engine().earliest_available(dep)
                if avail:
                    earliest = min(earliest, avail) if earliest else avail
    earliest_iso = to_iso(earliest) if earliest else None
    error = all_exhausted(requested if not combo else combo.name, earliest_available_utc=earliest_iso)
    return JSONResponse(error.to_obj(), status_code=429, headers={"Retry-After": "60"})


# ---------------------------------------------------------------------------
# Concurrency semaphores (per deployment)
# ---------------------------------------------------------------------------

_semaphores: dict[str, asyncio.Semaphore] = {}

def _get_semaphore(deployment_id: str, max_concurrent: int = 10) -> asyncio.Semaphore:
    if deployment_id not in _semaphores:
        _semaphores[deployment_id] = asyncio.Semaphore(max_concurrent)
    return _semaphores[deployment_id]


# ---------------------------------------------------------------------------
# M5: Capability token auth (HMAC)
# ---------------------------------------------------------------------------

def _load_hmac_secret() -> bytes:
    """Load HMAC secret from ~/.config/umaws/quotagate.key or env."""
    global _hmac_secret
    if _hmac_secret is not None:
        return _hmac_secret
    # Try env first
    env_secret = os.environ.get("QUOTAGATE_HMAC_SECRET")
    if env_secret:
        _hmac_secret = env_secret.encode("utf-8")
        return _hmac_secret
    # Try file
    key_path = Path.home() / ".config" / "umaws" / "quotagate.key"
    if key_path.is_file():
        _hmac_secret = key_path.read_bytes().strip()
        return _hmac_secret
    # Generate a random one for development (not for production!)
    import secrets
    _hmac_secret = secrets.token_bytes(32)
    return _hmac_secret


def _verify_capability_token(request: Request) -> tuple[bool, dict | None]:
    """Verify the x-quotagate-capability-token header.
    
    Returns (ok, payload). Payload contains lease_id, fence, task_id, role, exp.
    """
    secret = _load_hmac_secret()
    token = request.headers.get("x-quotagate-capability-token", "")
    if not token:
        return False, None
    try:
        # Format: base64(payload).base64(sig)
        payload_b64, sig_b64 = token.rsplit(".", 1)
        import base64
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + "==")
        sig_bytes = base64.urlsafe_b64decode(sig_b64 + "==")
        expected_sig = hmac.new(secret, payload_bytes, hashlib.sha256).digest()
        if not hmac.compare_digest(sig_bytes, expected_sig):
            return False, None
        payload = json.loads(payload_bytes.decode("utf-8"))
        # Check expiry
        import time
        if payload.get("exp", 0) < time.time():
            return False, None
        return True, payload
    except Exception:
        return False, None


class CapabilityTokenMiddleware(BaseHTTPMiddleware):
    """Middleware to verify capability tokens on protected routes."""
    
    # Routes that require a valid capability token
    PROTECTED_PATHS = {
        "/v1/chat/completions",
        "/v1/models",
    }
    
    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.PROTECTED_PATHS:
            ok, payload = _verify_capability_token(request)
            if not ok:
                return JSONResponse(
                    {"error": "invalid or missing capability token"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer realm=\"quotagate\""}
                )
            # Store payload in request state for downstream use
            request.state.capability = payload
        return await call_next(request)


# ---------------------------------------------------------------------------
# M5: Events outbox
# ---------------------------------------------------------------------------

def _init_events_db() -> sqlite3.Connection:
    """Initialize the events database."""
    conn = sqlite3.connect(_events_db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            type TEXT NOT NULL,
            deployment_id TEXT,
            account_id TEXT,
            profile_id TEXT,
            task_id TEXT,
            fence INTEGER,
            payload TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
        CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id);
        CREATE INDEX IF NOT EXISTS idx_events_deployment ON events(deployment_id);
    """)
    conn.commit()
    return conn


def _record_event(event_type: str, deployment_id: str = "", account_id: str = "",
                  profile_id: str = "", task_id: str = "", fence: int | None = None,
                  payload: dict | None = None) -> int:
    """Record an event to the outbox. Returns the sequence number."""
    conn = _init_events_db()
    now = time.time()
    cursor = conn.execute(
        """INSERT INTO events (ts, type, deployment_id, account_id, profile_id,
                               task_id, fence, payload, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (now, event_type, deployment_id or None, account_id or None,
         profile_id or None, task_id or None, fence,
         json.dumps(payload or {}), now))
    conn.commit()
    seq = cursor.lastrowid
    conn.close()
    return seq


# ---------------------------------------------------------------------------
# M5: Config hash
# ---------------------------------------------------------------------------

def _compute_config_hash() -> str:
    """Compute SHA-256 of the canonical config.toml."""
    global _config_hash_cached
    if _config_hash_cached is not None:
        return _config_hash_cached
    config_path = Path(__file__).with_name("config.toml")
    content = config_path.read_bytes()
    _config_hash_cached = hashlib.sha256(content).hexdigest()
    return _config_hash_cached


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

async def _health(request):
    """GET /v1/quotagate/health - is the gateway up, and can it see truth?"""
    return JSONResponse({"ok": True, "service": "quotagate",
                         "milestone": "m1"})


async def _models(request):
    """GET /v1/models -> upstream /models."""
    try:
        async with httpx.AsyncClient(timeout=timeout()) as client:
            upstream = await client.request(
                request.method, _upstream(None, request.url.path),
                headers=_forward_headers(request))
    except httpx.TimeoutException:
        return _error("upstream timeout", 504)
    except httpx.HTTPError as exc:
        return _error(f"upstream unreachable: {exc}", 502)
    return Response(upstream.text,
                    status_code=upstream.status_code,
                    media_type=upstream.headers.get("Content-Type"))


async def _chat_completions(request):
    """POST /v1/chat/completions -> upstream /chat/completions.

    The client asks for a *deployment* or *combo*; the upstream needs its own
    *model* string.  The proxy rewrites one into the other, because the two
    namespaces are different things.

    If a combo is requested, the gateway routes to an eligible deployment
    using the combo's strategy.  On pre-first-byte failure (5xx, timeout),
    it fails over to the next eligible deployment in the combo.
    """
    engine, latency = get_engine(), get_latency()

    try:
        body = await request.json()
    except Exception:
        return _error("request body is not JSON", 400)

    requested = str(body.get("model", ""))
    if not requested:
        return _error("missing model", 400)

    config = engine.config

    # Resolve: is this a combo or a deployment?
    combo = config.combo(requested)
    if combo is None:
        # Single deployment (legacy)
        deployment = config.deployment(requested)
        if deployment is None:
            known = sorted(config.deployments)
            return _error(f"unknown model or combo {requested!r}", 400,
                          known=known)
        deployments_to_try = [deployment]
        strategy_used = "single"
    else:
        # Combo: route to eligible deployments, ordered by strategy
        deployments_to_try = []
        candidates = []
        for dep in config.deployments_in_combo(combo):
            usable, reason = engine.is_usable(dep)
            candidates.append({"deployment": dep.id, "eligible": usable, "reason": reason})
            if usable:
                deployments_to_try.append(dep)
        if not deployments_to_try:
            return _error(f"no eligible deployment in combo {requested!r}", 429,
                          candidates=candidates,
                          earliest_available_utc=_earliest_available_all(engine, combo))

        # Apply strategy ordering
        if combo.strategy == HEADROOM:
            deployments_to_try.sort(key=lambda d: (-_remaining(engine, d), combo.deployments.index(d.id)))
        elif combo.strategy == USE_IT_OR_LOSE_IT:
            deployments_to_try.sort(key=lambda d: (_remaining(engine, d), combo.deployments.index(d.id)))
        elif combo.strategy == ROUND_ROBIN:
            deployments_to_try.sort(key=lambda d: ((combo.deployments.index(d.id) + int(engine.now())) % len(deployments_to_try), combo.deployments.index(d.id)))
        # priority = as listed (already in combo order)
        strategy_used = combo.strategy

    # Try each deployment in order (pre-first-byte failover)
    last_error = None
    for attempt, deployment in enumerate(deployments_to_try):
        deployment_id = deployment.id

        # 1. Admit at this deployment's scopes
        try:
            reservation = engine.reserve(deployment, requests=1)
        except QuotaExceeded as exc:
            admission = exc.admission
            _record_event("QUOTA_EXCEEDED", deployment_id=deployment_id,
                          account_id=deployment.account, profile_id=request.headers.get("x-quotagate-profile", ""),
                          task_id=request.headers.get(TASK_HEADER, ""),
                          fence=int(request.headers.get("x-quotagate-fence", "0") or 0),
                          payload={"rule": admission.rule.to_dict() if admission.rule else None,
                                   "reset_at": admission.reset_at,
                                   "strategy": strategy_used, "attempt": attempt + 1})
            # Try next deployment in combo
            if attempt < len(deployments_to_try) - 1:
                continue
            return _structured_429(admission, combo, requested, strategy_used)

        # Acquire concurrency semaphore for this deployment
        sem = _get_semaphore(deployment_id, max_concurrent=10)
        acquired = await sem.acquire()
        try:
            # 2. Proxy with streaming-first-byte detection
            upstream_body = dict(body)
            upstream_body["model"] = deployment.model
            path = _upstream(deployment, request.url.path)

            started = time.monotonic()
            try:
                async with httpx.AsyncClient(timeout=timeout()) as client:
                    upstream = await client.request(
                        request.method, path,
                        headers=_forward_headers(request),
                        json=upstream_body)
            except httpx.TimeoutException:
                engine.refund(reservation)
                _record_event("REQUEST_TIMEOUT", deployment_id=deployment_id,
                              account_id=deployment.account, profile_id=request.headers.get("x-quotagate-profile", ""),
                              task_id=request.headers.get(TASK_HEADER, ""),
                              fence=int(request.headers.get("x-quotagate-fence", "0") or 0),
                              payload={"latency_ms": int((time.monotonic() - started) * 1000)})
                last_error = "upstream timeout"
                if attempt < len(deployments_to_try) - 1:
                    continue
                return _error("upstream timeout", 504)
            except httpx.HTTPError as exc:
                engine.refund(reservation)
                _record_event("REQUEST_ERROR", deployment_id=deployment_id,
                              account_id=deployment.account, profile_id=request.headers.get("x-quotagate-profile", ""),
                              task_id=request.headers.get(TASK_HEADER, ""),
                              fence=int(request.headers.get("x-quotagate-fence", "0") or 0),
                              payload={"error": str(exc)})
                last_error = f"upstream unreachable: {exc}"
                if attempt < len(deployments_to_try) - 1:
                    continue
                return _error(f"upstream unreachable: {exc}", 502)

            elapsed_ms = int((time.monotonic() - started) * 1000)

            # 3. Capture latency for every outcome
            latency.observe(deployment_id, elapsed_ms, deployment)

            usage = {}
            try:
                data = upstream.json()
                if isinstance(data, dict):
                    usage = data.get("usage") or {}
            except Exception:
                data = None

            # Pre-first-byte failover: 5xx or network error -> try next deployment
            if upstream.status_code >= 500:
                engine.refund(reservation)
                _record_event("UPSTREAM_5XX", deployment_id=deployment_id,
                              account_id=deployment.account, profile_id=request.headers.get("x-quotagate-profile", ""),
                              task_id=request.headers.get(TASK_HEADER, ""),
                              fence=int(request.headers.get("x-quotagate-fence", "0") or 0),
                              payload={"status_code": upstream.status_code, "latency_ms": elapsed_ms})
                last_error = f"upstream {upstream.status_code}"
                if attempt < len(deployments_to_try) - 1:
                    continue
                return _error("upstream error", 502, detail=last_error)

            if upstream.status_code >= 400:
                engine.refund(reservation)
                _record_event("UPSTREAM_4XX", deployment_id=deployment_id,
                              account_id=deployment.account, profile_id=request.headers.get("x-quotagate-profile", ""),
                              task_id=request.headers.get(TASK_HEADER, ""),
                              fence=int(request.headers.get("x-quotagate-fence", "0") or 0),
                              payload={"status_code": upstream.status_code, "latency_ms": elapsed_ms})
                return Response(upstream.text,
                                status_code=upstream.status_code,
                                media_type=upstream.headers.get("Content-Type"))

            # 4. Success: commit usage, record provenance, return
            engine.commit(reservation, tokens=int(usage.get("total_tokens", 0) or 0))
            # Record success event
            _record_event("REQUEST_SUCCESS", deployment_id=deployment_id,
                          account_id=deployment.account, profile_id=request.headers.get("x-quotagate-profile", ""),
                          task_id=request.headers.get(TASK_HEADER, ""),
                          fence=int(request.headers.get("x-quotagate-fence", "0") or 0),
                          payload={"latency_ms": elapsed_ms, "tokens": usage.get("total_tokens", 0),
                                   "strategy": strategy_used, "attempt": attempt + 1})
        finally:
            if acquired:
                sem.release()

        task_key = request.headers.get(TASK_HEADER, "")
        if task_key and data is not None:
            served = served_from_response(data, dict(upstream.headers))
            if served.get("model"):
                get_provenance().record(
                    task_key, str(request.headers.get("x-quotagate-profile", "unknown")),
                    deployment_id, served["model"],
                    served_provider=served.get("provider", ""),
                    decision=served.get("decision", ""),
                    request_id=str(upstream.headers.get("x-request-id", "")),
                    latency_ms=elapsed_ms)

        headers = {k: v for k, v in upstream.headers.items()
                   if k.lower() not in ("transfer-encoding", "content-length")}
        headers["X-QuotaGate-Latency-Ms"] = str(elapsed_ms)
        headers["X-QuotaGate-Deployment"] = deployment_id
        headers["X-QuotaGate-Strategy"] = strategy_used
        headers["X-QuotaGate-Attempt"] = str(attempt + 1)
        return Response(upstream.text, status_code=upstream.status_code,
                        headers=headers, media_type=upstream.headers.get("Content-Type"))

    # All deployments exhausted
    if last_error:
        return _error("all deployments failed", 502, detail=last_error)
    return _error("no eligible deployment", 429)


def _structured_429(admission, combo, requested, strategy):
    """Return a structured 429 with earliest_available_utc."""
    from quotagate.errors import all_exhausted
    earliest = admission.reset_at
    if combo:
        # Check all deployments in combo for earliest available
        for dep_id in combo.deployments:
            dep = combo.deployments.get(dep_id) if hasattr(combo, 'deployments') else None
            # Note: config.deployments lookup needed
            pass
    error = all_exhausted(requested if not combo else combo.name, earliest_available_utc=earliest)
    return error


async def _provenance(request):
    """GET /v1/quotagate/provenance - which models actually served.

    Two shapes, because the two callers have different knowledge:

    * ``?task=T-0002``       - a client that could correlate (the header path).
    * ``?deployment=X&start=S&end=E`` - the Fleet, which spawns a CLI **process**
      and so cannot put a header on the requests the CLI makes.  A lease is
      exclusive to one worktree and a profile is capped by ``max_concurrent``,
      so a window on a deployment is attributable.
    """
    task = request.query_params.get("task", "")
    deployment = request.query_params.get("deployment", "")
    try:
        start = float(request.query_params.get("start", "0") or 0)
        end = float(request.query_params.get("end", "0") or 0)
    except ValueError:
        return _error("start and end must be numbers", 400)

    if task:
        rows = get_provenance().for_task(task)
    elif deployment and end > start:
        rows = get_provenance().for_window(deployment, start, end)
    else:
        return _error("give ?task=T-0002, or ?deployment=X&start=S&end=E", 400)

    served = sorted({r["served_model"] for r in rows if r["served_model"]})
    return JSONResponse({
        "task": task or None,
        "deployment": deployment or None,
        "window": [start, end] if deployment else None,
        "served_models": served,
        "unknown": not served,
        "calls": rows,
    })


async def _availability(request):
    """GET /v1/quotagate/availability - limits, usage and observed latency."""
    engine, latency = get_engine(), get_latency()
    out = {}
    for deployment_id, deployment in engine.config.deployments.items():
        status = engine.status(deployment)
        status["latency"] = latency.to_dict().get(
            deployment_id, {"response_time_min_ms": 0,
                            "response_time_max_ms": 0})
        status["latest_ms"] = status["latency"].get("response_time_min_ms", 0)
        out[deployment_id] = status
    return JSONResponse(out)


async def _events(request):
    """GET /v1/quotagate/events?since=<seq> - events outbox for Kernel ingestion."""
    try:
        since = int(request.query_params.get("since", "0") or 0)
    except ValueError:
        return _error("since must be an integer", 400)
    conn = _init_events_db()
    cursor = conn.execute(
        "SELECT seq, ts, type, deployment_id, account_id, profile_id, "
        "task_id, fence, payload FROM events WHERE seq > ? ORDER BY seq",
        (since,))
    rows = []
    for row in cursor.fetchall():
        rows.append({
            "seq": row["seq"],
            "ts": row["ts"],
            "type": row["type"],
            "deployment_id": row["deployment_id"],
            "account_id": row["account_id"],
            "profile_id": row["profile_id"],
            "task_id": row["task_id"],
            "fence": row["fence"],
            "payload": json.loads(row["payload"]) if row["payload"] else {},
        })
    conn.close()
    return JSONResponse({"events": rows, "since": since})


async def _config_hash_endpoint(request):
    """GET /v1/quotagate/config-hash - SHA-256 of the pinned config.toml."""
    return JSONResponse({"config_hash": _compute_config_hash()})


async def _unknown(request):
    return _error("no such endpoint", 404)


routes = [
    Route("/v1/chat/completions", _chat_completions,
          methods=["GET", "POST"]),
    Route("/v1/models", _models, methods=["GET", "POST"]),
    Route("/v1/quotagate/availability", _availability, methods=["GET"]),
    Route("/v1/quotagate/provenance", _provenance, methods=["GET"]),
    Route("/v1/quotagate/health", _health, methods=["GET"]),
    # M5 endpoints
    Route("/v1/quotagate/events", _events, methods=["GET"]),
    Route("/v1/quotagate/config-hash", _config_hash_endpoint, methods=["GET"]),
]

app = Starlette(routes=routes, middleware=[Middleware(CapabilityTokenMiddleware)])
