import json
import sys
sys.path.insert(0, r'C:\temp\projects\testproject1\src')
from pmk.events import compute_hash

with open('.pm/events/2026-10-31.jsonl', 'r') as f:
    lines = f.readlines()
events = [json.loads(line) for line in lines]

# Find seq 1203, 1206
for i, e in enumerate(events):
    if e.get('seq') in [1203, 1204, 1205, 1206, 1207]:
        print('Index {}: seq={}, type={}, subject={}'.format(i, e.get('seq'), e.get('type'), e.get('subject')))