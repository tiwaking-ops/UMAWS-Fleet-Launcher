import tomllib
with open('agents.toml', 'rb') as f:
    data = tomllib.load(f)
print('Parsed OK')
print('Profiles:', len(data.get('profile', [])))
for p in data.get('profile', []):
    print(p['id'], p['adapter'], p['family'], p['priority'])