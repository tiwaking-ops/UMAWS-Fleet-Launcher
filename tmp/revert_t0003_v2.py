import sys
from pathlib import Path
from pmk.api import Kernel
from pmk.models import READY

# Load Kernel
root = Path("C:/temp/projects/testproject1")
kernel = Kernel(root=root)

# Record revert event
kernel.record_event("TASK_REVOKED", subject="T-0003", payload={"reason": "Oracle failure detected in EB-T-0003-3; moving from DONE to READY for rework."})

# Manually set state back to READY
# The Kernel's project_set_state seems to be limited to higher level actions,
# but we can simulate the state transition by appending an event if needed
# or finding the correct method.
# Since project_set_state failed on 'subject', let's just append the event
# which I1 (sentinel) should use to update the ledger.
# Actually, the 'record_event' doesn't update the state card itself in the projection.
# Let's inspect the Kernel for a direct task state update.

print("Manually revoking T-0003...")
# The dispatcher usually handles this via revoke() but that requires a fence.
# I already have the fence 3 from the status.
kernel.revoke("T-0003", 3, reason="Oracle failure; rework required")
print("T-0003 reverted to READY.")
