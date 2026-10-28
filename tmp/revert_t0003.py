# Revert T-0003
import sys
from pathlib import Path
from pmk.api import Kernel
from pmk.models import READY

# Load Kernel
root = Path("C:/temp/projects/testproject1")
kernel = Kernel(root=root)

# Record revert event
kernel.record_event("TASK_REVOKED", subject="T-0003", payload={"reason": "Oracle failure detected in EB-T-0003-3; moving from DONE to READY for rework."})
# Manually reset state (the kernel handles this if we call project_set_state/task actions)
# But here we just append the event to trigger the projection update.
# The kernel project_set_state(READY, ...) logic is best
kernel.project_set_state(READY, reason="Reworking T-0003 due to oracle failure", subject="T-0003")
