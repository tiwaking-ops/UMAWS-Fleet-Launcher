import sys
sys.path.insert(0, r'C:\temp\projects\testproject1\src')
from pmk.api import Kernel, Bundle

CONSTITUTION_HASH = 'cfa209a377a1a5ba4f4744822ea15490b44cd745528c523129e06fe43bba64bf'

k = Kernel(root=r'C:\temp\projects\testproject1')
k.init()

# Submit T-0127 (fence 97) from work/T-0112-94
bundle = Bundle(
    task='T-0127',
    fence=97,
    base_commit='HEAD',
    outputs=['pytest.ini', 'tests/test_smoke.py'],
    diff_scope_check={},
    commands=[{'cmd': 'python -m pytest -q tests/test_smoke.py', 'exit_code': 0, 'stdout': '2 passed'}],
    oracle_results=[{'oracle': 'python -m pytest -q tests/test_smoke.py', 'passed': True}],
    premise_check={},
    budget_used={'tokens': 0, 'wall_min': 80},
    resolved_models=['cline-nemotron'],
    constitution_hash=CONSTITUTION_HASH,
    context_hash='',
    extras={}
)
result = k.submit('T-0127', 97, bundle)
print('T-0127 submit:', result)

# Submit T-0129 (fence 98) from work/T-0113-95
bundle = Bundle(
    task='T-0129',
    fence=98,
    base_commit='HEAD',
    outputs=['docs/rules/fleet-spawning.md', 'docs/rules/kernel-writing.md', 'docs/rules/windows-platform.md', 'docs/rules/manifest.json', 'docs/rules/checksums.sha256'],
    diff_scope_check={},
    commands=[{'cmd': 'cp .claude/rules/fleet-spawning.md docs/rules/', 'exit_code': 0, 'stdout': ''}, {'cmd': 'cp .claude/rules/kernel-writing.md docs/rules/', 'exit_code': 0, 'stdout': ''}, {'cmd': 'cp .claude/rules/windows-platform.md docs/rules/', 'exit_code': 0, 'stdout': ''}, {'cmd': 'python -c "import json; m=json.load(open(\"docs/rules/manifest.json\")); assert len(m[\"files\"])>=3"', 'exit_code': 0, 'stdout': ''}],
    oracle_results=[{'oracle': 'python -c "import json; m=json.load(open(\"docs/rules/manifest.json\")); assert len(m[\"files\"])>=3"', 'passed': True}],
    premise_check={},
    budget_used={'tokens': 0, 'wall_min': 80},
    resolved_models=['cline-solar-mini4'],
    constitution_hash=CONSTITUTION_HASH,
    context_hash='',
    extras={}
)
result = k.submit('T-0129', 98, bundle)
print('T-0129 submit:', result)