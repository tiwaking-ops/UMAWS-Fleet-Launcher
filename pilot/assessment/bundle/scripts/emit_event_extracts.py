"""Emit event-log extracts for the bundle (RAN-NOW evidence)."""
import json
import os
import sys
from collections import Counter

events_dir = os.environ.get("UMAWS_EVENTS_DIR", ".pm/events")
if len(sys.argv) > 1:
    events_dir = sys.argv[1]

all_events = []
for fn in sorted(os.listdir(events_dir)):
    if not fn.endswith(".jsonl"):
        continue
    with open(os.path.join(events_dir, fn), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                all_events.append(json.loads(line))

all_events.sort(key=lambda e: e.get("seq", 0))

print(f"Total events: {len(all_events)}")
print()

# per-type counts
counts = Counter(e["type"] for e in all_events)
print("=== COUNTS BY TYPE ===")
for t, c in sorted(counts.items()):
    print(f"  {t:<22} {c:>6}")
print()

# head 50
print("=== FIRST 50 EVENTS ===")
for e in all_events[:50]:
    p = dict(e.get("payload", {}))
    p.pop("candidates", None)
    ps = json.dumps(p, ensure_ascii=False)
    if len(ps) > 100:
        ps = ps[:100] + "..."
    subj = e.get('subject') or '-'
    print(f"{e.get('seq','-'):>4} | {e['ts']} | {e['type']:<20} | "
          f"{subj:<12} | {ps}")
print()

# tail 50
print("=== LAST 50 EVENTS ===")
for e in all_events[-50:]:
    p = dict(e.get("payload", {}))
    p.pop("candidates", None)
    ps = json.dumps(p, ensure_ascii=False)
    if len(ps) > 100:
        ps = ps[:100] + "..."
    subj = e.get('subject') or '-'
    print(f"{e.get('seq','-'):>4} | {e['ts']} | {e['type']:<20} | "
          f"{subj:<12} | {ps}")
print()

# one complete task lifecycle — pick T-0001
print("=== T-0001 LIFECYCLE (all events for this task) ===")
for e in all_events:
    if e.get("subject") == "T-0001" or "T-0001" in json.dumps(e.get("payload", {})):
        p = dict(e.get("payload", {}))
        p.pop("candidates", None)
        print(f"{e.get('seq','-'):>4} | {e['ts']} | {e['type']:<20} | "
              f"payload={json.dumps(p, ensure_ascii=False)[:200]}")
print()

print("=== T-0002 LIFECYCLE (all events for this task) ===")
for e in all_events:
    if e.get("subject") == "T-0002" or "T-0002" in json.dumps(e.get("payload", {})):
        p = dict(e.get("payload", {}))
        p.pop("candidates", None)
        print(f"{e.get('seq','-'):>4} | {e['ts']} | {e['type']:<20} | "
              f"payload={json.dumps(p, ensure_ascii=False)[:200]}")
print()

print("=== T-0003 LIFECYCLE (all events for this task) ===")
for e in all_events:
    if e.get("subject") == "T-0003" or "T-0003" in json.dumps(e.get("payload", {})):
        p = dict(e.get("payload", {}))
        p.pop("candidates", None)
        print(f"{e.get('seq','-'):>4} | {e['ts']} | {e['type']:<20} | "
              f"payload={json.dumps(p, ensure_ascii=False)[:200]}")
