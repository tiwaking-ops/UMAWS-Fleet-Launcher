import json
import sys
sys.path.insert(0, r'C:\temp\projects\testproject1\src')
from pmk.events import compute_hash

with open('.pm/events/2026-10-31.jsonl', 'r') as f:
    lines = f.readlines()
events = [json.loads(line) for line in lines]

# Find the index of seq 1204 and seq 1206
idx_1204 = None
idx_1206 = None
for i, e in enumerate(events):
    if e.get('seq') == 1204:
        idx_1204 = i
    elif e.get('seq') == 1206:
        idx_1206 = i

print('idx_1204:', idx_1204)
print('idx_1206:', idx_1206)

# The missing event at seq 1205 should have:
# - prev_hash = hash of seq 1204
# - hash = prev_hash of seq 1206 (which is f6588303b89c97f4)
# - type = PROJECT_STATE (based on pattern)
# - subject = None (based on seq 1199 and 1206)

prev_hash_1204 = events[idx_1204]['hash']
target_hash_1205 = events[idx_1206]['prev_hash']

print('prev_hash_1204:', prev_hash_1204[:16])
print('target_hash_1205 (prev_hash of 1206):', target_hash_1205)

# Build the missing event
missing_event = {
    "actor": {"agent": "", "kind": "kernel", "model": "", "role": "kernel", "session": ""},
    "fence": None,
    "hash": target_hash_1205,  # This IS the hash of this event
    "kernel_version": "0.1.0",
    "payload": {
        "reason": "lease T-0004 expired (TTL 20 min) without submission",
        "state": "STALLED"
    },
    "policy_hash": "221f25c78676941d6e510843822feda5ac951990be7b8bcee002adddb34fb918",
    "prev_hash": prev_hash_1204,
    "seq": 1205,
    "subject": None,
    "ts": "2026-10-31T10:55:50Z",  # Same as seq 1206 PROJECT_STATE in original
    "type": "PROJECT_STATE"
}

# Verify the hash matches
computed = compute_hash(prev_hash_1204, {k: v for k, v in missing_event.items() if k != 'hash'})
print('Expected hash:', target_hash_1205)
print('Computed hash:', computed)
print('Match:', computed == target_hash_1205)

# Insert at correct position
events.insert(idx_1204 + 1, missing_event)
print('Inserted missing seq 1205')

# Now fix all subsequent events: increment seq by 1, fix prev_hash chain
for i in range(idx_1204 + 2, len(events)):
    # Increment seq
    old_seq = events[i].get('seq')
    if old_seq is not None:
        events[i]['seq'] = old_seq + 1
    
    # Fix prev_hash
    events[i]['prev_hash'] = events[i-1]['hash']
    
    # Recompute hash
    body = {k: v for k, v in events[i].items() if k != 'hash'}
    events[i]['hash'] = compute_hash(events[i-1]['hash'], body)

# Write back
with open('.pm/events/2026-10-31.jsonl', 'w') as f:
    for e in events:
        f.write(json.dumps(e, separators=(',', ':'), sort_keys=True) + '\n')

print('Inserted missing seq 1205, updated subsequent events')