"""G3's other half: a REAL CLI, through a REAL lease, in a REAL worktree.

The one-click demo exercises the whole lifecycle with the **fake** CLI
(``tests/fleet/fakecli.py``).  That proves the plumbing but not that a real
agent, given a real lease and a real worktree, can do the work and have it
accepted.

This runs the same lifecycle with **kilo** — a real CLI, a real model, real
file writes, and a *functional* oracle (the output must be a correct Markdown
table, not merely an existing file).

Every gate is what the Kernel already enforces; nothing here is relaxed:

* the worker runs in a git worktree under a lease with a fence;
* the oracle is run by the harness, not by the worker;
* the evidence bundle carries the constitution hash;
* the merge queue runs the project gate before integrating.

Scratch repository, so a real agent's file writes cannot touch the pilot.
Delete the directory to undo everything.

Author: OpenCode.  Date: 2026-10-23.  Authorised by the operator 2026-10-23
("2. APPROVED").
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "pilot"))

from demo_one_click import build_demo_repo, git, seed_constitution  # noqa: E402
from fleet.dispatcher import Dispatcher  # noqa: E402
from fleet.merge import integrate  # noqa: E402
from fleet.project import CLOSING, RUNNING, close_check, init_project  # noqa: E402
from fleet.state import FleetState  # noqa: E402
from pmk.api import Kernel  # noqa: E402
from pmk.clock import FakeClock  # noqa: E402

BRIEF = """Build a tiny CSV-to-Markdown converter.

Goals:
  G-001  src/csv2md.py converts a CSV file into a Markdown table.
"""

PDD = """# PDD: csv2md      version: 1      status: approved

## 1. Purpose
Convert a CSV file into a Markdown table.

## 2. Goals
### G-001 Converter script
acceptance:
- `python src/csv2md.py data.csv` prints a Markdown table of the CSV's rows
oracle: `python check.py`

## 3. Non-goals
Nothing else.

## 4. Constraints
Python 3.11 or later.  Standard library only.

## 5. Architecture sketch
One module, invoked as a script with the CSV path as its only argument.

## 6. Definition of done
gate_cmd: `python check.py`

## 7. Open questions
None.
"""

#: A *functional* oracle.  It runs the worker's script and parses its output as
#: a Markdown table.  A file that merely exists passes nothing.
CHECK = '''"""Functional check: does src/csv2md.py actually convert CSV to Markdown?"""
import pathlib
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parent
csv = root / "data.csv"
script = root / "src" / "csv2md.py"

if not script.exists():
    print("src/csv2md.py does not exist")
    sys.exit(1)

out = subprocess.run([sys.executable, str(script), str(csv)],
                     capture_output=True, text=True)
if out.returncode != 0:
    print("script exited", out.returncode)
    print((out.stderr or out.stdout)[:600])
    sys.exit(1)

rows = []
for line in out.stdout.splitlines():
    line = line.strip()
    if not line.startswith("|"):
        continue
    cells = [c.strip() for c in line.strip("|").split("|")]
    if all(set(c) <= set("-: ") for c in cells):
        continue                      # the |---|---| separator row
    rows.append(cells)

expected = [["name", "qty"], ["alpha", "1"], ["beta", "2"]]
if rows != expected:
    print("table is wrong")
    print("expected:", expected)
    print("got     :", rows)
    print("raw     :")
    print(out.stdout[:600])
    sys.exit(1)

print("ok: correct markdown table")
sys.exit(0)
'''

DATA = "name,qty\nalpha,1\nbeta,2\n"

AGENTS = """[fleet]
max_total_agents = 4
dispatch_tick_s = 1
stall_minutes = 15
min_free_ram_mb = 0

[overseer]
profiles = []

[[profile]]
id = "kilo-real"
adapter = "kilo"
family = "unknown"
priority = 10
max_concurrent = 1
via_gateway = false
roles = ["implement", "review", "plan", "verify"]
argv_new = ["kilo", "run", "{prompt}", "--dir", "{cwd}", "--auto"]
# No resume: the adapter declares no resume capability, so the recovery
# ladder takes its L2 step (a fresh session) rather than pretending to
# resume.  That is the same honest state as the empty models lists.
argv_resume = []
models = []
"""


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="umaws-g3-real-"))
    root = build_demo_repo(base)
    print(f"scratch repository: {root}")
    print(f"  (delete this directory to undo the whole test)")

    # seed the inputs the worker must satisfy, but NOT the answer
    (root / "data.csv").write_text(DATA, encoding="utf-8", newline="\n")
    (root / "check.py").write_text(CHECK, encoding="utf-8", newline="\n")
    (root / "agents.toml").write_text(AGENTS, encoding="utf-8", newline="\n")
    seed_constitution(root)
    # the toy gate is the functional check, not an existence test
    (root / ".pm" / "policy.toml").write_text(
        'version = "p-g3"\n\n[gate]\ncmd = \'python check.py\'\n',
        encoding="utf-8", newline="\n")
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "PDD.md").write_text(PDD, encoding="utf-8", newline="\n")
    git(root, "add", "-A")
    git(root, "commit", "-m", "inputs: csv, PDD, functional check")

    clock = FakeClock()
    kernel = Kernel(root=root, clock=clock)
    kernel.init()
    print(f"[1] kernel initialised: {kernel.status()['chain']}")

    result = init_project(kernel, brief=BRIEF)
    print(f"[2] project created: state={result['state']} "
          f"plan task={result['plan_task']}")
    kernel.project_set_state(CLOSING, reason="the PDD is in place")

    card = kernel.task_create(
        "Make `python src/csv2md.py data.csv` print a Markdown table of data.csv",
        type="implement",
        goal_ref="G-001",
        scope={"write": ["src/csv2md.py"], "read": ["data.csv", "check.py"]},
        oracles=["python check.py"],
        evidence_required=["oracle_results", "diff_scope"],
        budget={"tokens": 50000, "wall_min": 12},
        priority=10,
    )
    print(f"[3] task card {card.id} created (READY)")

    plan = kernel.state().tasks[result["plan_task"]]
    kernel.record_event("TASK_VOIDED", subject=plan.id,
                        payload={"reason": "the PDD was written by hand"})
    kernel.project_set_state(RUNNING, reason="a task card exists")

    # -- dispatch: a REAL cli, a REAL worktree, a REAL lease ----------------
    fleet_state = FleetState()
    dispatcher = Dispatcher(kernel, fleet_state,
                            fixture_root=ROOT / "tests" / "fleet" / "fixtures")

    deadline = time.time() + 600
    started_at = None
    while time.time() < deadline:
        report = dispatcher.tick()
        for s in report.started:
            started_at = time.time()
            print(f"[4] spawned {s['task']} on {s['profile']} pid={s['pid']}")
        for f in report.finished:
            el = f"{time.time() - started_at:.0f}s" if started_at else "?"
            line = f"[5] finished {f['task']}: {f['outcome']} (after {el})"
            if f.get("failure_class"):
                line += f" [{f['failure_class']}]"
            if f.get("error"):
                line += f" -- {f['error']}"
            print(line)
        done = not dispatcher.runs and not any(
            t.state not in ("DONE", "VOID") for t in kernel.state().task_list())
        if done:
            break
        time.sleep(1.0)

    state = kernel.state()
    print(f"[6] after dispatch: {state.counts()}")

    task = state.tasks[card.id]
    print(f"    {task.id} state: {task.state}")
    lease = state.leases.get(card.id)
    print(f"    lease: {lease}")

    # -- the merge queue runs the project gate ------------------------------
    gate = kernel.policy().get("gate", {}).get("cmd", "")
    for t in kernel.state().task_list():
        if t.state not in ("SUBMITTED", "VERIFYING"):
            continue
        lease = kernel.state().leases.get(t.id)
        if lease is None or not lease.worktree:
            print(f"    {t.id}: no worktree to merge")
            continue
        merged = integrate(kernel, t, lease, lease.worktree, gate_cmd=gate)
        print(f"[7] merge {t.id}: ok={merged.ok} ({merged.message})")
        if merged.ok:
            kernel.integrate(t.id, lease.fence, commit=merged.commit)

    print(f"[8] after the merge queue: {kernel.state().counts()}")
    check = close_check(kernel)
    print(f"[9] close-check: ok={check.ok}")
    for goal in check.goals:
        print(f"    {goal['goal']}: {goal['status']} ({goal.get('oracle', '')})")
    print(f"    gate: {check.gate.get('status')} ({check.gate.get('cmd')})")
    for failure in check.failures:
        print(f"    FAILURE: {failure}")

    # -- did the real CLI's work actually land in the tree? -----------------
    final = root / "src" / "csv2md.py"
    print(f"[10] src/csv2md.py size after the run: "
          f"{final.stat().st_size if final.exists() else 'MISSING'} bytes")
    print(f"     scratch repository kept at: {root}")
    return 0 if check.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
