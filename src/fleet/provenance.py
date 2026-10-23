"""Provenance on the Fleet side: ask the gateway which model served.

D-L12 stops a verifier from being the implementer's *declared family*.  That is
a guess about a string, and it fails in two directions:

* ``kilo/kilo-auto/free`` is an opaque router, so a different declared family
  can still be the same underlying model checking its own work.
* two genuinely different models in one family are rejected needlessly.

Both come from comparing declarations instead of facts.  This module asks the
gateway - the one component that sits in the request path and sees the
upstream's answer - which models actually served a lease's calls.

**Empty is a real answer, not a failure.**  A direct-CLI profile never touches
the gateway, so the Kernel cannot know what served (``L-F2``).  In that case
the set is empty, and D-L12's existing veto on unknown families stays in force.
Fabricating a model name from the profile's declared ``model`` would be the
exact mistake this whole change exists to remove.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

#: Where a gateway-routed profile's evidence is written by the harness, so the
#: next run of the fleet can read it without the gateway still being up.
CACHE_NAME = "provenance.json"


def served_models_for_run(gateway_url: str, deployment: str, *, start: float,
                          end: float, timeout: float = 10.0) -> set[str]:
    """Ask the gateway which models served *deployment* in ``[start, end]``.

    Returns an empty set when the gateway cannot say - which means unknown,
    and leaves the family-based veto intact rather than guessing.
    """
    if not gateway_url:
        return set()
    query = urllib.parse.urlencode({"deployment": deployment,
                                    "start": f"{start:.3f}",
                                    "end": f"{end:.3f}"})
    url = f"{gateway_url.rstrip('/')}/v1/quotagate/provenance?{query}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return set()                  # unreachable: unknown, never guessed
    models = {str(m) for m in (body.get("served_models") or []) if m}
    return models


def write_cache(worktree: Path, deployment: str, models: set[str]) -> None:
    """Persist what served, so provenance outlives the gateway."""
    target = Path(worktree) / ".pmwork" / CACHE_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"deployment": deployment,
                                  "served_models": sorted(models)},
                                 indent=2) + "\n", encoding="utf-8")


def read_cache(worktree: Path) -> set[str]:
    """The models that served a worktree, as recorded at submit time."""
    target = Path(worktree) / ".pmwork" / CACHE_NAME
    if not target.is_file():
        return set()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return set()
    return {str(m) for m in (data.get("served_models") or []) if m}


def served_models_for_task(task_id: str, gateway_url: str,
                           timeout: float = 10.0) -> set[str]:
    """By task id, when a client could correlate (the header path)."""
    if not gateway_url:
        return set()
    query = urllib.parse.urlencode({"task": task_id})
    url = f"{gateway_url.rstrip('/')}/v1/quotagate/provenance?{query}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return set()
    return {str(m) for m in (body.get("served_models") or []) if m}
