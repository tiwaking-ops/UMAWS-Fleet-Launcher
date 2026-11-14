"""Read-only probe: are the 13 prune-refused worktrees held by stale leases?"""
import sys

sys.path.insert(0, "src")

from pmk.api import Kernel  # noqa: E402

NAMES = [
    "T-0139-117", "T-0150-121", "T-0169-145", "T-0170-146", "T-0171-147",
    "T-0172-148", "T-0173-149", "T-0174-150", "T-0181-144", "T-0182-151",
    "T-0190-157", "T-0191-158", "T-0196-159",
]

k = Kernel()
s = k.state()
active = s.active_leases()
print(f"leases_total={len(s.leases)}  active_leases={len(active)}")
print()
print(f"{'worktree':<14} {'card state':<12} {'card fence':<11} "
      f"{'lease.fence':<12} {'expires_at':<22} {'pid':<8} active?")
for name in NAMES:
    tid, fence = name.rsplit("-", 1)
    card = s.tasks.get(tid)
    lease = s.leases.get(tid)
    print(
        f"{name:<14} "
        f"{getattr(card, 'state', None)!s:<12} "
        f"{getattr(card, 'fence', None)!s:<11} "
        f"{getattr(lease, 'fence', None)!s:<12} "
        f"{getattr(lease, 'expires_at', None)!s:<22} "
        f"{getattr(lease, 'pid', None)!s:<8} "
        f"{tid in active}"
    )
print()
# Any lease whose card is not in an active state is stale.
stale = sorted(t for t in s.leases if t not in active)
print(f"stale_lease_entries={len(stale)}")
print(stale)
