"""QuotaGate — a quota-aware local LLM gateway (QuotaGate v1.1).

Standard library plus the pinned set.  The quota engine is the heart of
this package; the proxy, the events outbox and the Kernel integration
(milestones M1, M3 and M5) build on it.

Scope note: the gateway is **not required** for Fleet-only operation.  A
profile with ``via_gateway = true`` uses it; a direct-CLI profile does not.
"""

from __future__ import annotations

__all__ = ["config", "engine", "errors", "routing", "main"]

from . import config, engine, errors, main, routing
