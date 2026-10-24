"""Check invariant I13 (views equal projection) by re-rendering views from the
event log and comparing byte-for-byte with the on-disk view files.

Usage:
    python check_views.py [REPO_ROOT]

Run in the clone (or live repo).  Read-only: it renders views in memory and
compares them to the files on disk; it writes nothing.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from pmk.api import Kernel  # noqa: E402


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    k = Kernel(root)
    state = k.state()
    policy = k.policy()

    views_dir = Path(k.repo.views_dir)
    view_fns = {
        "ledger.md": lambda: __import__("pmk.views", fromlist=["render_ledger"]).render_ledger(state),
        "status.md": lambda: __import__("pmk.views", fromlist=["render_status"]).render_status(state, policy),
        "queue.md":  lambda: __import__("pmk.views", fromlist=["render_queue"]).render_queue(state),
    }

    ok = True
    print(f"repo: {k.repo.root}")
    print(f"events: {len(k.events())}")
    print(f"views dir: {views_dir}")
    print()

    for name, fn in view_fns.items():
        on_disk = (views_dir / name).read_text(encoding="utf-8") if (views_dir / name).exists() else None
        projected = fn()
        if on_disk is None:
            print(f"  {name}: MISSING on disk")
            ok = False
        elif on_disk == projected:
            print(f"  {name}: MATCH (I13 holds)")
        else:
            print(f"  {name}: DIVERGES")
            dl = on_disk.splitlines()
            pl = projected.splitlines()
            shown = 0
            for i, (d, p) in enumerate(zip(dl, pl)):
                if d != p and shown < 5:
                    print(f"    line {i+1}: disk={d[:100]!r}")
                    print(f"    line {i+1}: proj={p[:100]!r}")
                    shown += 1
            if len(dl) != len(pl):
                print(f"    line count: disk={len(dl)} proj={len(pl)}")
            ok = False

    print()
    chain = k.log.verify()
    print(f"chain ok: {chain.ok}  repairs: {chain.repairs}")
    print()
    verdict = "I13 VERIFIED" if ok else "I13 DIVERGED"
    print(f"I13 verdict: {verdict}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
