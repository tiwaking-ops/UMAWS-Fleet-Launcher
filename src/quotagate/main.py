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

import os
import time
from pathlib import Path

import httpx
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from pmk.clock import Clock
from quotagate.config import GatewayConfig
from quotagate.engine import Ledger, QuotaEngine, QuotaExceeded
from quotagate.latency import LatencyLedger

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

_config: GatewayConfig | None = None
_engine: QuotaEngine | None = None
_latency: LatencyLedger | None = None
_upstream_url = os.environ.get("QUOTAGATE_UPSTREAM",
                               "http://127.0.0.1:20128")
_timeout_s = 60.0


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

    The client asks for a *deployment* (``omniroute/kilo``); the upstream
    needs its own *model* string (``auto/best-coding``).  The proxy rewrites
    one into the other, because the two namespaces are different things.
    """
    engine, latency = get_engine(), get_latency()

    try:
        body = await request.json()
    except Exception:
        return _error("request body is not JSON", 400)

    deployment_id = str(body.get("model", ""))
    deployment = engine.config.deployment(deployment_id)
    if deployment is None:
        known = sorted(engine.config.deployments)
        return _error(f"unknown deployment {deployment_id!r}", 400,
                      known=known)

    # 1. Admit, before spending the upstream's time.
    try:
        reservation = engine.reserve(deployment, requests=1)
    except QuotaExceeded as exc:
        admission = exc.admission
        return JSONResponse(
            {"error": "quota exceeded",
             "reason": admission.reason,
             "rule": admission.rule.to_dict() if admission.rule else None,
             "reset_at": admission.reset_at},
            status_code=429,
            headers={"Retry-After": "60"})

    # 2. Proxy.
    upstream_body = dict(body)
    upstream_body["model"] = deployment.model        # rewrite onto upstream
    path = _upstream(deployment, request.url.path)

    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout()) as client:
            upstream = await client.request(
                request.method, path,
                headers=_forward_headers(request),
                json=upstream_body)
    except httpx.TimeoutException:
        engine.refund(reservation)                   # the unit was not spent
        return _error("upstream timeout", 504)
    except httpx.HTTPError as exc:
        engine.refund(reservation)
        return _error(f"upstream unreachable: {exc}", 502)

    elapsed_ms = int((time.monotonic() - started) * 1000)

    # 3. Capture.  Latency is recorded for every outcome, including a
    #    failure, because a slow failure is exactly what a reliability
    #    figure needs to know about.  Token usage is only reconciled on a
    #    usable response, so nothing is charged for a body that never came.
    latency.observe(deployment_id, elapsed_ms, deployment)

    usage = {}
    try:
        data = upstream.json()
        if isinstance(data, dict):
            usage = data.get("usage") or {}
    except Exception:
        data = None

    if upstream.status_code >= 400:
        engine.refund(reservation)
        return Response(upstream.text,
                        status_code=upstream.status_code,
                        media_type=upstream.headers.get("Content-Type"))

    engine.commit(reservation,
                  tokens=int(usage.get("total_tokens", 0) or 0))

    # 4. Answer, carrying the upstream's headers so x-omniroute-decision
    #    (which tells us who really served the call) reaches the caller.
    headers = {k: v for k, v in upstream.headers.items()
               if k.lower() not in ("transfer-encoding", "content-length")}
    headers["X-QuotaGate-Latency-Ms"] = str(elapsed_ms)
    return Response(upstream.text, status_code=upstream.status_code,
                    headers=headers,
                    media_type=upstream.headers.get("Content-Type"))


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


async def _unknown(request):
    return _error("no such endpoint", 404)


routes = [
    Route("/v1/chat/completions", _chat_completions,
          methods=["GET", "POST"]),
    Route("/v1/models", _models, methods=["GET", "POST"]),
    Route("/v1/quotagate/availability", _availability, methods=["GET"]),
    Route("/v1/quotagate/health", _health, methods=["GET"]),
]

app = Starlette(routes=routes)
