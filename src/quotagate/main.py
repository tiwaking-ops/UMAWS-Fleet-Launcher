"""QuotaGate M1: Passthrough proxy with live capture.

This is the milestone M1: the gateway can now forward requests to an
upstream, capture usage, and enforce locally-declared limits.

Key design choices:
- Path translation: OpenAI clients assume `/v1/*` prefix. OmniRoute has no
  `/v1` prefix, so the proxy removes it from incoming paths.
- Auth: passes through the bearer token to the upstream.
- Timeout: 60 s per request (observed `auto/cheap` timed out at 45s).
- Usage: captured from the response body's `usage` field.
- Rate-limit headers: NOT provided by upstream, so the proxy does not
  forward them; clients must rely on local limits.

Author: OpenCode.  Date: 2026-10-23.  Authorised: operator (M1 approved).
"""

from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from pmk.clock import Clock
from quotagate.config import GatewayConfig
from quotagate.engine import Ledger, QuotaEngine


# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

_config: GatewayConfig | None = None
_engine: QuotaEngine | None = None
_clock: Clock | None = None
_upstream_url = "http://127.0.0.1:20128"


def get_config() -> GatewayConfig:
    global _config
    if _config is None:
        config_path = Path(__file__).with_name("config.toml")
        _config = GatewayConfig.load(config_path)
    return _config


def get_engine() -> QuotaEngine:
    global _engine, _clock
    if _engine is None:
        _clock = Clock()
        _engine = QuotaEngine(get_config(), ledger=Ledger(), clock=_clock)
    return _engine


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

async def _models(request):
    """GET /v1/models -> proxy to upstream /models."""
    engine = get_engine()
    start = time.time()

    try:
        resp = await _proxy_request(request, "POST", "/models", {"id": "omniroute/test"})
        return resp
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


async def _chat_completions(request):
    """
    Forward chat completion request.

    The client's model ID maps to our internal deployment ID via a
    simple rule: "omniroute/<profile>" -> deployment "omniroute/<profile>".
    This is where we'd need a mapping table; for now we just treat the
    model as the deployment.
    """
    engine = get_engine()
    body = await request.json()
    model_id = body.get("model", "omniroute/opencode")

    # Deployment lookup: model_id is taken as the deployment ID.
    deployment = engine.config.deployment(model_id)
    if deployment is None:
        return JSONResponse(
            {"error": f"deployment not found: {model_id}"},
            status_code=400
        )

    start = time.time()

    # Check quota before proxying.
    try:
        reservation = engine.reserve(deployment, requests=1)
    except Exception as exc:
        return JSONResponse(
            {"error": "quota exceeded", "details": str(exc)},
            status_code=429,
            headers={"Retry-After": "60"}
        )

    # Proxy with timeout.
    headers = dict(request.headers)
    headers.pop("Host", None)
    headers.pop("Content-Length", None)

    # Remove /v1 prefix for upstream.
    upstream_path = request.url.path
    if upstream_path.startswith("/v1/"):
        upstream_path = upstream_path[3:]

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            upstream_resp = await client.request(
                request.method,
                f"{_upstream_url}{upstream_path}",
                headers=headers,
                json=body if request.method in ("GET", "POST") else None,
                content=await request.body() if request.method not in ("GET", "POST", "HEAD") else None,
            )
        except httpx.TimeoutException:
            engine.refund(reservation)
            return JSONResponse(
                {"error": "upstream timeout"},
                status_code=504
            )

    # Extract usage from response.
    usage = {}
    data = upstream_resp.json()
    if "usage" in data:
        usage = data["usage"]

    # Commit reservation with tokens used.
    total_tokens = usage.get("total_tokens", 0)
    engine.commit(reservation, tokens=total_tokens)

    # TODO: classify failures and apply cooldowns via engine.apply_failure()

    # Build response.
    resp_body = upstream_resp.text
    headers_to_send = dict(upstream_resp.headers)
    headers_to_send.pop("Transfer-Encoding", None)

    return Response(
        resp_body,
        status_code=upstream_resp.status_code,
        headers=headers_to_send,
        media_type=upstream_resp.headers.get("Content-Type", "application/json"),
    )


async def _availability(request):
    """GET /v1/quotagate/availability - current quota status."""
    engine = get_engine()
    status = {}
    for dep_id, dep in engine.config.deployments.items():
        status[dep_id] = engine.status(dep)
    return JSONResponse(status)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

routes = [
    Route("/v1/models", _models, methods=["GET", "POST"]),
    Route("/v1/chat/completions", _chat_completions, methods=["GET", "POST"]),
    Route("/v1/quotagate/availability", _availability, methods=["GET"]),
]

app = Starlette(routes=routes, debug=True)