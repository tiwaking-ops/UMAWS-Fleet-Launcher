"""Read-only: validate the operator-edited agents.toml through the real loader."""
import sys

sys.path.insert(0, "src")

from pmk.api import Kernel                     # noqa: E402
from pmk.policy import load_agents             # noqa: E402
from fleet.profiles import load_profiles       # noqa: E402

kernel = Kernel()
result = load_agents(kernel.repo)
print("loader errors :", result["errors"] or "none")
print("profile count :", len(result["profiles"]))
print("cap keys      :", result["cap_keys"])

profiles = load_profiles(kernel.repo)
ids = sorted(p.id for p in profiles)
print("loaded ids    :", ids)
print("cline-beam present:", "cline-beam" in ids)
print("overseer block:", result["overseer"])
