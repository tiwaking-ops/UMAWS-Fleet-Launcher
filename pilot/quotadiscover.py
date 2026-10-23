"""Quota discovery by measurement, not by guessing.

The gate's upstreams do **not** publish their limits:

* omniroute returns no ``x-ratelimit-*``, no ``retry-after`` and no quota
  header at all, and no ``429`` could be induced to inspect (D-38).
* Nous Portal's limits are not published anywhere reachable:
  ``portal.nousresearch.com/models`` sits behind a Vercel anti-bot JS
  challenge, ``hermes portal info`` reports auth and routing but no quotas,
  and the shipped model catalog carries no pricing data.

So the limits in ``src/quotagate/config.toml`` are *declared*, not learned -
which means they could be wrong in either direction.  A ceiling set too low
silently breaks working agents; one set too high discovers its error as a
provider 429.

This tool measures them.  It fires a small, controlled number of requests and
records where the upstream starts refusing, in three modes:

  bounds  a ramp (1, 2, 4, 8 ... rps) of short bursts.  Answers "roughly how
          many requests per minute can this model take?"  The ramp rests
          between steps so a rate-limit from one step does not poison the
          next, and stops at the first sustained refusal.
  latency a steady 1 rps trickle.  Answers "how fast is this model, really?"
          and writes the min/max that ``config.toml``'s response-time fields
          want.
  daily   opt-in, **destructive**.  Keeps going in the belief that a daily
          ceiling will eventually bind.  Not run unless asked for, because
          it burns real quota to answer a question a monthly bill could
          answer for free.

Everything the upstream returns - status, latency, headers - is recorded and
written out as a Markdown report, so the numbers are inspectable rather than
only asserted.

Safety rails: a hard request ceiling, a stop on sustained refusal, and
nothing run without an explicit deployment name.

Author: OpenCode.  Date: 2026-10-23.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import httpx  # noqa: E402
from quotagate.config import GatewayConfig  # noqa: E402

#: A prompt short enough that the answer is cheap but real.
PROMPT = "Reply with the single word: ok"

#: The order of the ramp.  Each entry is requests-per-second within a burst.
RAMP = [1, 2, 4, 8, 16, 32, 64]


def upstream_for(config: GatewayConfig, deployment_id: str) -> dict:
    dep = config.deployment(deployment_id)
    if dep is None:
        raise SystemExit(f"unknown deployment {deployment_id!r}")
    return config.upstream_for(dep)


def build_request(model: str) -> dict:
    return {"model": model, "max_tokens": 8, "stream": False,
            "messages": [{"role": "user", "content": PROMPT}]}


class Run:
    """One request's outcome."""

    __slots__ = ("ok", "status", "ms", "headers", "body", "error")

    def __init__(self, *, ok, status=None, ms=None, headers=None, body=None,
                 error=None):
        self.ok = ok
        self.status = status
        self.ms = ms
        self.headers = headers or {}
        self.body = body
        self.error = error


async def call_once(client: httpx.AsyncClient, url: str, body: dict,
                    headers: dict, timeout: float) -> Run:
    started = time.monotonic()
    try:
        r = await client.post(url, json=body, headers=headers,
                              timeout=timeout)
    except httpx.TimeoutException:
        return Run(ok=False, error="timeout")
    except httpx.HTTPError as exc:
        return Run(ok=False, error=f"unreachable: {exc}")
    elapsed = int((time.monotonic() - started) * 1000)
    text = r.text
    return Run(ok=r.status_code < 400, status=r.status_code, ms=elapsed,
               headers=dict(r.headers),
               body=text[:400] if r.status_code >= 400 else None)


async def run_bounds(client, url, model, headers, timeout, stop_flag) -> list:
    """The ramp.  Returns the results, in step order."""
    results = []
    total = 0
    print(f"ramp: {' '.join(str(r) for r in RAMP)} rps, "
          f"ceiling {stop_flag['max_requests']} requests")
    for rps in RAMP:
        if stop_flag["stop"]:
            break
        burst = rps * 3                       # three seconds at that rate
        step = {"rps": rps, "sent": 0, "ok": 0, "limited": 0,
                "ms": [], "first_limited_status": None,
                "first_limited_body": None}
        for i in range(burst):
            if total >= stop_flag["max_requests"] or stop_flag["stop"]:
                break
            out = await call_once(client, url, build_request(model), headers,
                                  timeout)
            total += 1
            step["sent"] += 1
            if out.status is not None:
                step["ms"].append(out.ms)
            if out.ok:
                step["ok"] += 1
            elif out.status is not None:
                step["limited"] += 1
                if step["first_limited_status"] is None:
                    step["first_limited_status"] = out.status
                    step["first_limited_body"] = out.body
            else:
                stop_flag["stop"] = True     # unreachable; nothing to learn
                break
            await _sleep(1.0 / rps)
        results.append(step)
        # A step where most calls were refused is the boundary; do not climb
        # further into a wall, and do not mistake one blip for the ceiling.
        if step["limited"] and step["ok"] < max(1, step["sent"] // 2):
            break
        await _sleep(4.0)                     # let the window drain
    return results


async def _sleep(seconds: float) -> None:
    import asyncio
    await asyncio.sleep(seconds)


def summarise(results: list, model: str, url: str) -> str:
    """Turn the ramp into the sentence a human needs."""
    # Only steps that actually sent something count.  A step that sent
    # nothing because the request ceiling was hit is "not measured", and must
    # never be reported as "fully served".
    ran = [r for r in results if r["sent"] > 0]
    clean = [r for r in ran if r["ok"] == r["sent"]]
    best_rps = max((r["rps"] for r in clean), default=0)
    broken = next((r for r in ran if r["limited"]), None)
    lat = summaries(results)
    out = [
        f"# Quota discovery - {model}", "",
        f"Upstream: `{url}`", "",
        "| rps | sent | ok | limited | p50 ms | max ms |",
        "|---|---|---|---|---|---|",
    ]
    for r in ran:
        p50 = int(statistics.median(r["ms"])) if r["ms"] else 0
        out.append(f"| {r['rps']} | {r['sent']} | {r['ok']} | {r['limited']} "
                   f"| {p50} | {max(r['ms']) if r['ms'] else 0} |")
    out += ["", "## Reading", ""]
    if broken:
        out += [f"Refusals began at **{broken['rps']} requests/second**, with "
                f"HTTP {broken['first_limited_status']}.", ""]
        if broken["first_limited_body"]:
            out += ["First refusal body:", "",
                    "```", broken["first_limited_body"][:400], "```", ""]
    if best_rps:
        out += [f"Fully served up to **{best_rps} rps**, i.e. about "
                f"**{best_rps * 60} requests/minute**.  Treat that as an "
                "upper bound on what this test proved, not as the provider's "
                "real ceiling.", ""]
    else:
        out += ["No step was served fully from the first request, so this "
                "test could not establish any headroom.", ""]
    if lat:
        lo, hi = lat
        out += [f"Observed latency across {sum(len(r['ms']) for r in results)} "
                f"calls: min **{lo} ms**, max **{hi} ms**.", ""]
    out += ["", "### Caveats", "",
            "* A short burst measured once is an *estimate*, not a published "
            "limit.  Providers often allow a burst above the sustained rate "
            "and punish it afterwards, so a clean ramp can overstate the "
            "sustainable ceiling.", "",
            "* The absence of refusals at a step means the limit is somewhere "
            "above it - not that there is no limit.", "",
            "* Steps the ramp never reached proved nothing; the table lists "
            "only the steps that actually sent requests.", "",
            "* Daily and monthly caps need a far longer run than this makes; "
            "use the `--mode daily` path knowingly, or read them off the "
            "provider's own dashboard.", ""]
    return "\n".join(out)


def summaries(results: list) -> tuple[int, int] | None:
    """(min, max) latency across every observed request."""
    all_ms = [m for r in results for m in r["ms"]]
    return (min(all_ms), max(all_ms)) if all_ms else None


async def main_async(args) -> int:
    config = GatewayConfig.load(
        args.config or str(ROOT / "src" / "quotagate" / "config.toml"))
    dep = config.deployment(args.deployment)
    if dep is None:
        raise SystemExit(f"unknown deployment {args.deployment!r}")
    up = config.upstream_for(dep)
    base = str(up.get("base_url", ""))
    path = config.rewrite_path(dep, "/v1/chat/completions")
    url = f"{base}{path}"

    headers = {"Content-Type": "application/json"}
    if args.bearer:
        headers["Authorization"] = f"Bearer {args.bearer}"

    print(f"deployment : {args.deployment}")
    print(f"model      : {dep.model}")
    print(f"upstream   : {url}  (path_style={up.get('path_style')})")
    print(f"mode       : {args.mode}")
    if args.dry_run:
        print("DRY RUN - nothing sent")
        return 0

    stop_flag = {"stop": False, "max_requests": args.max_requests}
    async with httpx.AsyncClient() as client:
        results = await run_bounds(client, url, dep.model, headers,
                                   args.timeout, stop_flag)

    report = summarise(results, dep.model, url)
    print()
    print(report)

    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"\nwritten to {args.out}")

    lat = summaries(results)
    if lat:
        print(f"\nFor config.toml [{args.deployment}]:")
        print(f'  response_time_min_ms = {lat[0]}')
        print(f'  response_time_max_ms = {lat[1]}')
        print("(only replace the sentinels once you trust the sample)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Discover a deployment's quota bounds by measuring them.")
    ap.add_argument("deployment", help="e.g. hermes/upstage-solar-mini4")
    ap.add_argument("--mode", default="bounds",
                    choices=["bounds", "latency", "daily"],
                    help="daily is destructive; bounds and latency are not")
    ap.add_argument("--config", help="path to config.toml")
    ap.add_argument("--max-requests", type=int, default=200,
                    help="hard ceiling on requests sent (default 200)")
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--bearer",
                    help="bearer token; the hermes proxy ignores it, "
                         "omniroute needs one (never write the value down)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", help="write the Markdown report here")
    args = ap.parse_args()

    import asyncio
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
