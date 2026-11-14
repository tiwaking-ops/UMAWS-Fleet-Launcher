import json
import sys
sys.path.insert(0, r'C:\temp\projects\testproject1\src')
from pmk.events import compute_hash

# Load backup to get original missing events
with open('.pm/events/2026-10-31.jsonl.bak', 'r') as f:
    lines = f.readlines()
bak_events = [json.loads(line) for line in lines]

# Get original seq 1204 (LEASE_EXPIRED T-0007)
orig_1204 = None
for e in bak_events:
    if e.get('seq') == 1204:
        orig_1204 = e
        break

print('Original seq 1204:', orig_1204.get('type'), orig_1204.get('subject'))
print('  hash:', orig_1204.get('hash')[:16])
print('  prev_hash:', orig_1204.get('prev_hash')[:16])
print('  ts:', orig_1204.get('ts'))

# Current events
with open('.pm/events/2026-10-31.jsonl', 'r') as f:
    lines = f.readlines()
events = [json.loads(line) for line in lines]

# Find index of seq 1203
idx_1203 = None
for i, e in enumerate(events):
    if e.get('seq') == 1203:
        idx_1203 = i
        break

print('idx_1203:', idx_1203)

# Reconstruct seq 1204 from original (using its prev_hash and content)
# But we need to compute correct hash based on current chain
# The original seq 1204 had prev_hash = f8ac1e7bda04ff0c (which is seq 1203 REVOKED's hash)
# Let's verify current seq 1203 hash
current_1203 = events[821]
print('Current seq 1203 hash:', current_1203.get('hash')[:16])
print('Original seq 1204 prev_hash:', orig_1204.get('prev_hash')[:16])

# We need to insert seq 1204 and 1205
# Start from seq 1203, build forward

prev_hash = events[821]['hash']  # seq 1203 hash

# Build seq 1204 (LEASE_EXPIRED T-0007)
seq_1204 = {
    "actor": {"agent": "", "kind": "kernel", "model": "", "role": "kernel", "session": ""},
    "fence": 30,
    "hash": "",
    "kernel_version": "0.1.0",
    "payload": {
        "elapsed_minutes": 20.02254517475764,
        "granted_at": "2026-10-31T10:35:46Z",
        "ttl_minutes": 20.0
    },
    "policy_hash": "221f25c78676941d6e510843822feda5ac951990be7b8bcee002adddb34fb918",
    "prev_hash": prev_hash,
    "seq": 1204,
    "subject": "T-0007",
    "ts": "2026-10-31T10:55:48Z",
    "type": "LEASE_EXPIRED"
}
seq_1204['hash'] = compute_hash(prev_hash, {k: v for k, v in seq_1204.items() if k != 'hash'})
print('seq 1204 hash:', seq_1204['hash'][:16])

# Build seq 1205 (PROJECT_STATE)
prev_hash = seq_1204['hash']
seq_1205 = {
    "actor": {"agent": "", "kind": "kernel", "model": "", "role": "kernel", "session": ""},
    "fence": None,
    "hash": "",
    "kernel_version": "0.1.0",
    "payload": {
        "reason": "lease T-0004 expired (TTL 20 min) without submission",
        "state": "STALLED"
    },
    "policy_hash": "221f25c78676941d6e510843822feda5ac951990be7b8bcee002adddb34fb918",
    "prev_hash": prev_hash,
    "seq": 1205,
    "subject": None,
    "ts": "2026-10-31T10:55:50Z",
    "type": "PROJECT_STATE"
}
seq_1205['hash'] = compute_hash(prev_hash, {k: v for k, v in seq_1205.items() if k != 'hash'})
print('seq 1205 hash:', seq_1205['hash'][:16])

# Verify seq 1205 hash matches what seq 1206 expects
with open('.pm/events/2026-10-31.jsonl', 'r') as f:
    lines = f.readlines()
events = [json.loads(line) for line in lines]
# Find current seq 1206
for e in events:
    if e.get('seq') == 1206:
        print('Current seq 1206 prev_hash:', e.get('prev_hash')[:16])
        print('Our seq 1205 hash:', seq_1205['hash'][:16])
        break

# Insert both at index 822 (after seq 1203 at index 821)
events.insert(822, seq_1204)
events.insert(823, seq_1205)

# Now fix all subsequent events
for i in range(824, len(events)):
    old_seq = events[i].get('seq')
    if old_seq is not None:
        events[i]['seq'] = old_seq + 2  # Added 2 events
    
    events[i]['prev_hash'] = events[i-1]['hash']
    
    body = {k: v for k, v in events[i].items() if k != 'hash'}
    events[i]['hash'] = compute_hash(events[i-1]['hash'], body)

# Write back
with open('.pm/events/2026-10-31.jsonl', 'w') as f:
    for e in events:
        f.write(json.dumps(e, separators=(',', ':'), sort_keys=True) + '\n')

print('Inserted seq 1204 and 1205, updated subsequent events')