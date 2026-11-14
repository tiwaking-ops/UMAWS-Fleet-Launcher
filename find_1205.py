with open('.pm/events/2026-10-31.jsonl', 'r') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    import json
    e = json.loads(line)
    if e.get('seq') in [1204, 1205, 1206, 1207]:
        print('Line {}: seq={}, type={}, subject={}'.format(i+1, e.get('seq'), e.get('type'), e.get('subject')))