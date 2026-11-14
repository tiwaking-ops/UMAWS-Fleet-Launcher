"""Read-only proof: are the 13 previously-refused trees reclaimable now?"""
import sys

sys.path.insert(0, "src")

from pmk.api import Kernel  # noqa: E402
from pmk import worktrees  # noqa: E402

NAMES = [
    "T-0139-117", "T-0150-121", "T-0169-145", "T-0170-146", "T-0171-147",
    "T-0172-148", "T-0173-149", "T-0174-150", "T-0181-144", "T-0182-151",
    "T-0190-157", "T-0191-158", "T-0196-159",
]

k = Kernel()
state = k.state()
repo = k.repo
root = worktrees.worktree_root(repo)
print(f"state.leases={len(state.leases)}  active_leases={len(state.active_leases())}")
print()
blocked = 0
for name in NAMES:
    path = root / name
    exists = path.is_dir()
    reason = worktrees._deletion_refusal(repo, state, path) if exists else "missing"
    if reason:
        blocked += 1
    print(f"{name:<14} exists={exists!s:<6} refusal={reason!r}")
print()
print(f"still_refused={blocked} of {len(NAMES)}")
