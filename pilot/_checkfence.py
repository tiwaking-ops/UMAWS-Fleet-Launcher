"""Read the fence/attempt state out of a finished scratch Kernel."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pmk.api import Kernel  # noqa: E402

for root in sys.argv[1:]:
    kernel = Kernel(root=root)
    state = kernel.state()
    print(f"scratch: {root}")
    for tid, card in state.tasks.items():
        print(f"  {tid}  state={card.state}  "
              f"fence={getattr(card, 'fence', None)}  "
              f"attempt={getattr(card, 'attempt', None)}")
    print(f"  open leases: {len(state.leases)}")
