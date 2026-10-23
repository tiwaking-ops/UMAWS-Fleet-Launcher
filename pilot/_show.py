"""Verify kilo-auto parses and the ladder's L1 swap can actually pick a model."""
import sys
from pathlib import Path
sys.path.insert(0, "src")
from fleet.profiles import load_profiles
from pmk.store import Repo

profiles = {p.id: p for p in load_profiles(Repo(Path(".")))}
p = profiles["kilo-auto"]
print(f"kilo-auto: adapter={p.adapter} model={p.model}")
print(f"  models ({len(p.models)}): {p.models[:3]} ...")
print(f"  supports_resume: {p.supports_resume()}")
print(f"  argv_new: {p.argv_new}")
print()
print("L1 swap progression (what the ladder would do as each model fails):")
used = []
for i in range(len(p.models)):
    nxt = p.alternative_model(used)
    if nxt is None:
        print(f"  {i}: none left")
        break
    used.append(nxt)
    print(f"  {i}: {nxt}")
print()
print("after exhausting the list:")
print("  alternative_model ->", p.alternative_model(used))
print()
for name, prof in sorted(profiles.items()):
    print(f"  {name:<20} model={prof.model or '(none)':<38} "
          f"models={len(prof.models)}")