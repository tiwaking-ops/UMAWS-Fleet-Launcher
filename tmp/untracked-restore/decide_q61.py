import sys
sys.path.insert(0, r'C:\temp\projects\testproject1\src')
from pmk.api import Kernel
k = Kernel(root=r'C:\temp\projects\testproject1')
k.init()
result = k.queue_decide("Q-061", "Focus on G-001 only (rules implemented, cited, covered) — create clean tasks for docs/rules/, docs/rules/index.json, coverage/rules_coverage.json, core engine module")
print(result)