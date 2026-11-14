with open('.pm/events/2026-10-31.jsonl', 'r') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'seq":1479' in line or 'seq": 1479' in line:
        print(f'Line {i+1}: {line[:200]}')