"""Exercise the recovery ladder (L0-L4) with **real** CLIs.

 Every unit test for the ladder uses the **fake** CLI and synthetic fixtures.
 This runs it against live failures from real agents, in real worktrees, under
 real leases, and records what the ladder actually decided - not what the
 docstring says it should decide.

 Scenarios (chosen by argv[1]):

 recover  A real CLI fails, and the ladder moves the work to a second real
          CLI which then does it successfully.  This is the path that
          matters: not failing, but recovering.
 l4       attempts are exhausted -> L4: task BLOCKED plus a queue item.
 l3       max_restarts_per_task = 0 -> L3: revoke the lease, bump the fence,
          quarantine the worktree, return the task to READY.

 The failure source is a real agent failing for real.  Nothing synthetic is
 fed to the classifier: whatever the CLI prints is what gets classified.

 Scratch repositories, so live agents cannot touch the pilot.

 Author: OpenCode.  Date: 2026-10-23.  Authorised 2026-10-23 ("2. Ladder.
 APPROVED").
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "pilot"))

from demo_one_click import build_demo_repo, git, seed_constitution  # noqa: E402
from fleet.dispatcher import Dispatcher  # noqa: E402
from fleet.project import RUNNING, init_project  # noqa: E402
from fleet.state import FleetState  # noqa: E402
from pmk.api import Kernel  # noqa: E402
from pmk.clock import FakeClock  # noqa: E402

BRIEF = """Build a script that prints hello.

Goals:
  G-001  src/greet.py prints a greeting containing the word hello.
"""

PDD = """# PDD: greet      version: 1      status: approved

## 1. Purpose
Print a greeting.

## 2. Goals
### G-001 Greeting script
acceptance:
- `python src/greet.py` prints something containing the word hello
oracle: `python check.py`

## 3. Non-goals
Nothing else.

## 4. Constraints
Python 3.11 or later.  Standard library only.

## 5. Architecture sketch
One module that prints when run as a script.

## 6. Definition of done
gate_cmd: `python check.py`

## 7. Open questions
None.
"""

#: A *functional* oracle - it runs the worker's script, and greps its stdout.
#: Cheap enough to run inside many ladder iterations, real enough that a
#: worker writing nothing still fails.
CHECK = '''"""Functional check: does src/greet.py print a greeting?"""
import pathlib
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parent
script = root / "src" / "greet.py"

if not script.exists():
    print("src/greet.py does not exist")
    sys.exit(1)

out = subprocess.run([sys.executable, str(script)],
                     capture_output=True, text=True)
if out.returncode != 0:
    print("script exited", out.returncode)
    print((out.stderr or out.stdout)[:400])
    sys.exit(1)
if "hello" not in out.stdout.lower():
    print("no greeting in stdout:", out.stdout[:400])
    sys.exit(1)

print("ok: greeting printed")
sys.exit(0)
'''

#: OpenCode's free tier is exhausted today, so it fails with a genuine quota
#: error.  Nothing here arranges that failure - it simply uses the failure
#: that is really happening.
OPENCODE_PROFILE = """
[[profile]]
id = "oc-live"
adapter = "opencode"
family = "unknown"
priority = 10
max_concurrent = 1
via_gateway = false
roles = ["implement"]
argv_new = ["opencode", "run", "{prompt}"]
argv_resume = ["opencode", "run", "{prompt}", "--continue"]
models = []
"""

KILO_PROFILE = """
[[profile]]
id = "kilo-real"
adapter = "kilo"
family = "unknown"
priority = 20
max_concurrent = 1
via_gateway = false
roles = ["implement"]
argv_new = ["kilo", "run", "{prompt}", "--dir", "{cwd}", "--auto"]
argv_resume = []
models = []
"""

FLEET = """[fleet]
max_total_agents = 4
dispatch_tick_s = 1
stall_minutes = 15
min_free_ram_mb = 0

[overseer]
profiles = []
"""

# scenario -> (profiles, attempts_max, max_restarts, deadline)
SCENARIOS = {
    "recover": (OPENCODE_PROFILE + KILO_PROFILE, 3, 5, 900),
    "l4": (OPENCODE_PROFILE, 1, 5, 240),
    "l3": (OPENCODE_PROFILE, 3, 0, 240),
}


def read_events(root: Path) -> list[dict]:
    """Every event in the log, in order."""
    events = []
    for path in sorted((root / ".pm" / "events").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return events


def summarise(event: dict) -> str:
    """One compact line for an event, keeping the fields a ladder cares about."""
    payload = event.get("payload") or {}
    keys = ("task", "task_id", "profile", "profile_id", "failure_class",
            "step", "attempt", "fence", "reason", "state", "queue_id",
            "cooldown_s", "delay_seconds", "note")
    bits = [f"{k}={payload[k]}" for k in keys if k in payload]
    if not bits:
        bits = [f"{k}={v}" for k, v in list(payload.items())[:3]]
    return f"  {event.get('type', '?')}: " + " ".join(bits)


def run(scenario: str) -> int:
    profiles, attempts_max, max_restarts, deadline = SCENARIOS[scenario]

    base = Path(tempfile.mkdtemp(prefix=f"umaws-ladder-{scenario}-"))
    root = build_demo_repo(base)
    print(f"scenario: {scenario}")
    print(f"scratch repository: {root}")

    (root / "check.py").write_text(CHECK, encoding="utf-8", newline="\n")
    (root / "agents.toml").write_text(FLEET + profiles, encoding="utf-8",
                                      newline="\n")
    seed_constitution(root)
    (root / ".pm" / "policy.toml").write_text(
        f'version = "p-{scenario}"\n\n'
        f'[gate]\ncmd = \'python check.py\'\n\n'
        f'[recovery]\n'
        f'max_restarts_per_task = {max_restarts}\n'
        f'network_retry_delays_s = [30, 120, 600]\n'
        f'no_profile_minutes = 15\n',
        encoding="utf-8", newline="\n")
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "PDD.md").write_text(PDD, encoding="utf-8", newline="\n")
    git(root, "add", "-A")
    git(root, "commit", "-m", "inputs: PDD, functional check, profiles")

    kernel = Kernel(root=root, clock=FakeClock())
    kernel.init()

    result = init_project(kernel, brief=BRIEF)
    from fleet.project import CLOSING
    kernel.project_set_state(CLOSING, reason="the PDD is in place")

    card = kernel.task_create(
        "Write src/greet.py so that running it prints hello",
        type="implement", goal_ref="G-001",
        scope={"write": ["src/greet.py"], "read": ["check.py"]},
        oracles=["python check.py"],
        evidence_required=["oracle_results", "diff_scope"],
        budget={"tokens": 20000, "wall_min": 12},
        attempts_max=attempts_max,
        priority=10,
    )
    plan = kernel.state().tasks[result["plan_task"]]
    kernel.record_event("TASK_VOIDED", subject=plan.id,
                        payload={"reason": "the PDD was written by hand"})
    kernel.project_set_state(RUNNING, reason="a task card exists")
    print(f"task {card.id}: attempts_max={attempts_max} "
          f"max_restarts_per_task={max_restarts}")

    before = len(read_events(root))

    fleet_state = FleetState()
    dispatcher = Dispatcher(kernel, fleet_state,
                            fixture_root=ROOT / "tests" / "fleet" / "fixtures")

    end = time.time() + deadline
    first_fail = None
    while time.time() < end:
        report = dispatcher.tick()
        for note in report.notes:
            print(f"  NOTE {note}")
        for f in report.finished:
            line = f"  FINISHED {f['task']}: {f['outcome']}"
            if f.get("failure_class"):
                line += f" [{f['failure_class']}]"
            if f.get("error"):
                line += f" -- {f['error']}"
            print(line)
            if first_fail is None and f["outcome"] != "submitted":
                first_fail = time.time()
        state = kernel.state()
        if card.id in state.tasks:
            now = state.tasks[card.id].state
            if now in ("BLOCKED", "FAILED"):
                print(f"  task reached {now}")
                break
        if first_fail and scenario in ("l4", "l3"):
            # give the ladder a few seconds to act, then stop watching
            if time.time() - first_fail > 20:
                break
        if (scenario == "recover"
                and card.id in state.tasks
                and state.tasks[card.id].state in ("DONE", "SUBMITTED",
                                                   "VERIFYING")):
            break
        time.sleep(1.0)

    print(f"final counts: {kernel.state().counts()}")
    if card.id in kernel.state().tasks:
        print(f"task {card.id} state: {kernel.state().tasks[card.id].state}")

    print("event trace (ladder decisions and their consequences):")
    for event in read_events(root)[before:]:
        print(summarise(event))

    #  What happened to the lease, the fence and the worktree?
    lease = kernel.state().leases.get(card.id)
    print(f"lease: {lease}")

    queue = getattr(kernel.state(), "queue", None)
    if queue is not None:
        items = list(queue) if hasattr(queue, "__iter__") else []
        if items:
            print("queue items:")
            for item in items:
                print(f"  {item}")
        else:
            print("queue items: none")

    print(f"scratch repository kept at: {root}")
    return 0


def main() -> int:
    scenario = sys.argv[1] if len(sys.argv) > 1 else "recover"
    if scenario not in SCENARIOS:
        print(f"usage: {Path(sys.argv[0]).name} "
              f"{{{', '.join(SCENARIOS)}}}")
        return 2
    return run(scenario)


if __name__ == "__main__":
    raise SystemExit(main())
