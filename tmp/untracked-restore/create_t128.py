import sys
sys.path.insert(0, r'C:\temp\projects\testproject1\src')
from pmk.api import Kernel

k = Kernel(root=r'C:\temp\projects\testproject1')
k.init()

# Create T-0128 with proper oracle
result = k.task_create(
    title="Vendor rules at pinned commit into docs/rules/ with checksums manifest",
    type="implement",
    goal_ref="G-001",
    scope={"write": ["docs/rules/"], "read": []},
    oracles=["python -c \"import json; m=json.load(open('docs/rules/manifest.json')); assert len(m['files'])>=3\""],
    evidence_required=[],
    attempts_max=3
)
print('T-0128 created:', result)