#!/usr/bin/env python
"""Count events by type in a UMAWS .pm/events directory.

Usage:
    python event_counts.py [REPO_ROOT]

REPO_ROOT defaults to the current directory.  Reads .pm/events/*.jsonl,
prints a per-type count with first/last timestamps, the total, and the
hash-chain verdict.  Read-only; opens the log through the Kernel's own
reader so the chain check is the production one.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from pmk.api import Kernel  # noqa: E402


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    k = Kernel(str(root))
    events = k.events()

    counts: Counter[str] = Counter()
    first: dict[str, str] = {}
    last: dict[str, str] = {}
    for e in events:
        counts[e.type] += 1
        first[e.type] = min(first.get(e.type, e.ts), e.ts)
        last[e.type] = max(last.get(e.type, e.ts), e.ts)

    print(f"repo: {k.repo.root}")
    print(f"total events: {len(events)}")
    print()
    print(f"{'type':<22} {'count':>6}  {'first':<20} {'last':<20}")
    for t, c in sorted(counts.items()):
        print(f"{t:<22} {c:>6}  {first[t]:<20} {last[t]:<20}")
    print()
    chain = k.log.verify()
    print(f"chain ok: {chain.ok}")
    print(f"repairs: {chain.repairs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
