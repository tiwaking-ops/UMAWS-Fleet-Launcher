"""A one-click end-to-end demonstration of the Fleet.

This is the pilot's **F1-shaped** run, but with the **fake CLI** as the
worker.  It exercises the whole mechanism end to end:

    brief -> PDD -> task cards -> claim -> worktree -> order file -> spawn
          -> oracles run by the harness -> evidence bundle -> submit
          -> merge queue -> close-check -> DONE

F1 itself (acceptance test F1) requires **real LLMs** and is therefore not
run here; the operator chose metadata-only CLI probing, so no real provider
was ever called.  What this script demonstrates is that the *mechanism*
works: that the oracles decide, that the fence protects a stale
submission, that the merge queue gates the promotion, and that the
close-check is what says "done".

Run::

    .\\.venv\\Scripts\\python.exe pilot\\demo_one_click.py

It uses a scratch git repository under ``pilot/demo/`` so it touches
nothing in the pilot's own tree.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fleet.dispatcher import Dispatcher  # noqa: E402
from fleet.merge import integrate  # noqa: E402
from fleet.project import (CLOSING, DONE, PLANNING, RUNNING, close_check,  # noqa: E402
                           init_project, set_state)
from fleet.state import FleetState, state_path  # noqa: E402
from pmk.api import Kernel  # noqa: E402
from pmk.clock import FakeClock  # noqa: E402

BRIEF = """Build a tiny CSV-to-Markdown converter.

Goals:
  G-001  A script converts a CSV file into a Markdown table.
  G-002  A test proves the conversion works.
"""


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True, text=True)


def build_demo_repo(base: Path) -> Path:
    """A scratch git repository with a toy project in it."""
    root = base / "toy"
    (root / "docs").mkdir(parents=True)
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "README.md").write_text("# CSV to Markdown\n", encoding="utf-8")
    (root / "src" / "csv2md.py").write_text(
        "def convert(rows):\n    return '\\n'.join(rows)\n", encoding="utf-8")
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "umaws-pilot")
    git(root, "config", "user.email", "umaws-pilot@localhost")
    git(root, "config", "extensions.worktreeConfig", "true")
    # The harness's own artefacts are not the worker's work.
    (root / ".gitignore").write_text(".pmwork/\n.fakecli-session.json\n",
                                     encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-m", "initial")
    return root


def seed_constitution(root: Path) -> None:
    """Seed the constitution and a gate command that fits the toy project.

    Without the constitution the evidence bundle has no
    ``constitution_hash`` and the Kernel refuses the submission (invariant
    I17).  That refusal is correct: the constitution is what reaches the
    worker, and its hash is what proves which rules were in force.

    The pilot's own gate command is ``pytest -q``; the toy project has no
    test suite for pytest to collect, so the demo uses the same
    existence check as the goal oracles.
    """
    (root / ".pm").mkdir(parents=True, exist_ok=True)
    source = ROOT / ".pm" / "constitution.md"
    (root / ".pm" / "constitution.md").write_text(
        source.read_text(encoding="utf-8"), encoding="utf-8")
    (root / ".pm" / "policy.toml").write_text(
        "version = \"p-demo\"\n\n"
        "[gate]\n"
        # A TOML *literal* string (single quotes) so the double quotes
        # inside the command need no escaping.
        "cmd = '" + oracle_for("src/csv2md.py") + "'\n",
        encoding="utf-8", newline="\n")


def write_agents(root: Path, profile_id: str, scenario: str = "ok") -> None:
    (root / "agents.toml").write_text(
        f"""[fleet]
max_total_agents = 4
dispatch_tick_s = 1
stall_minutes = 15
min_free_ram_mb = 0

[overseer]
profiles = []

[[profile]]
id = "{profile_id}"
adapter = "fake"
family = "unknown"
priority = 10
max_concurrent = 2
via_gateway = false
roles = ["implement", "review", "plan", "verify"]
argv_new = []
argv_resume = []
scenario = "{scenario}"
""", encoding="utf-8", newline="\n")


PDD = """# PDD: csv2md      version: 1      status: approved

## 1. Purpose
Convert a CSV file into a Markdown table.

## 2. Goals
### G-001 Converter script
acceptance:
- the script exists
oracle: `python -c "import os,sys; sys.exit(0 if os.path.exists(sys.argv[1]) else 1)" src/csv2md.py`

### G-002 Test
acceptance:
- the test exists
oracle: `python -c "import os,sys; sys.exit(0 if os.path.exists(sys.argv[1]) else 1)" tests/test_csv2md.py`

## 3. Non-goals
Nothing else.

## 4. Constraints
Python 3.11 or later.

## 5. Architecture sketch
One module and one test.

## 6. Definition of done
gate_cmd: `python -c "import os,sys; sys.exit(0 if os.path.exists(sys.argv[1]) else 1)" src/csv2md.py`

## 7. Open questions
None.
"""


def oracle_for(path: str) -> str:
    """A portable "does this file exist" oracle.

    ``test -f`` is a POSIX shell builtin and does not exist in Windows
    ``cmd.exe``, where the harness runs the oracle.  A Python one-liner
    works on both.  The path is passed as an argument rather than quoted
    inside the code, so the whole thing can also be written into a TOML
    file without any escaping.
    """
    return ("python -c \"import os,sys; "
            "sys.exit(0 if os.path.exists(sys.argv[1]) else 1)\" " + path)


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="umaws-demo-"))
    print(f"scratch repository: {base}\n")
    root = build_demo_repo(base)
    write_agents(root, "fake-worker")
    seed_constitution(root)

    clock = FakeClock()
    kernel = Kernel(root=root, clock=clock)
    kernel.init()
    print(f"[1] initialised the Kernel: {kernel.status()['chain']}")

    # -- step 1: the brief ------------------------------------------------
    result = init_project(kernel, brief=BRIEF)
    print(f"[2] project created: state={result['state']} "
          f"plan task={result['plan_task']}")
    print(f"    brief committed to {result['brief']}")

    # -- step 2: the PDD (hand-written here; the Overseer would write it) --
    pdd_path = root / "docs" / "PDD.md"
    pdd_path.write_text(PDD, encoding="utf-8", newline="\n")
    git(root, "add", "docs/PDD.md")
    git(root, "commit", "-m", "docs: the PDD")
    kernel.project_set_state(CLOSING, reason="the PDD is in place")
    print("[3] PDD written and committed")

    # -- step 3: decomposition -------------------------------------------
    tasks = []
    for goal, path in (("G-001", "src/csv2md.py"),
                       ("G-002", "tests/test_csv2md.py")):
        card = kernel.task_create(
            f"Produce {path} for {goal}",
            type="implement",
            goal_ref=goal,
            scope={"write": [path], "read": ["src/", "tests/"]},
            oracles=[oracle_for(path)],
            evidence_required=["oracle_results", "diff_scope"],
            budget={"tokens": 5000, "wall_min": 5},
            priority=10,
        )
        tasks.append(card)
    print(f"[4] decomposed into {len(tasks)} task cards: "
          f"{', '.join(t.id for t in tasks)}")

    # The plan task is voided: in this demo the PDD was written by hand
    # rather than by the Overseer, so the plan task has nothing left to do.
    plan = kernel.state().tasks[result["plan_task"]]
    kernel.record_event("TASK_VOIDED", subject=plan.id,
                        payload={"reason": "the PDD was written by hand in "
                                           "this demo"})
    print(f"    voided the plan task {plan.id} (the PDD was hand-written here)")

    # -- step 4: run them --------------------------------------------------
    # Use a temp fleet-state.json so we don't pollute the shared %LOCALAPPDATA%\umaws\fleet-state.json
    demo_fleet_state_path = base / "fleet-state.json"
    fleet_state = FleetState(path=demo_fleet_state_path)
    dispatcher = Dispatcher(kernel, fleet_state,
                            fixture_root=ROOT / "tests" / "fleet" / "fixtures")
    kernel.project_set_state(RUNNING, reason="task cards exist")

    deadline = time.time() + 120
    while time.time() < deadline:
        report = dispatcher.tick()
        for started in report.started:
            print(f"    started {started['task']} on {started['profile']} "
                  f"(pid {started['pid']})")
        for finished in report.finished:
            line = (f"    finished {finished['task']}: {finished['outcome']}"
                    + (f" [{finished['failure_class']}]"
                       if finished.get("failure_class") else ""))
            if finished.get("error"):
                line += f" -- {finished['error']}"
            print(line)
        if not dispatcher.runs and not any(
                t.state not in ("DONE", "VOID") for t in kernel.state().task_list()):
            break
        time.sleep(0.4)

    state = kernel.state()
    print(f"[5] after dispatch: {state.counts()}")

    # -- step 5: the merge queue ------------------------------------------
    gate = kernel.policy().get("gate", {}).get("cmd", "")
    for task in kernel.state().task_list():
        if task.state not in ("SUBMITTED", "VERIFYING"):
            continue
        lease = kernel.state().leases.get(task.id)
        if lease is None or not lease.worktree:
            continue
        merged = integrate(kernel, task, lease, lease.worktree, gate_cmd=gate)
        print(f"    merged {task.id}: ok={merged.ok} "
              f"({merged.message})")
        if merged.ok:
            kernel.integrate(task.id, lease.fence, commit=merged.commit)
    print(f"[6] after the merge queue: {kernel.state().counts()}")

    # -- step 6: the close-check -------------------------------------------
    check = close_check(kernel)
    print(f"[7] close-check: ok={check.ok}")
    for goal in check.goals:
        print(f"    {goal['goal']}: {goal['status']} "
              f"({goal.get('oracle', '')})")
    print(f"    gate: {check.gate.get('status')} ({check.gate.get('cmd')})")
    if check.failures:
        for failure in check.failures:
            print(f"    FAILURE: {failure}")

    if check.ok:
        set_state(kernel, DONE, reason="the close-check is green")
    print(f"[8] final state: {kernel.project_state()}")

    # -- the evidence ------------------------------------------------------
    bundles = list((kernel.repo.evidence_dir).glob("EB-*/bundle.json"))
    print(f"\nevidence bundles written: {len(bundles)}")
    for path in bundles:
        data = json.loads(path.read_text(encoding="utf-8"))
        print('        scope:', json.dumps(data['diff_scope_check'])[:300])
        print(f"    {path.parent.name}: "
              f"commands={len(data['commands'])} "
              f"oracles={len(data['oracle_results'])} "
              f"outputs={len(data['outputs'])} "
              f"scope_ok={data['diff_scope_check']['ok']} "
              f"constitution_hash={data['constitution_hash'][:12]}â€¦")

    report = kernel.sentinel()
    print(f"\nsentinel: ok={report['ok']}  findings={report['findings']}")
    print(f"chain: {kernel.log.verify().summary()}")
    print(f"total events: {len(kernel.events())}")

    if report["ok"] and check.ok:
        shutil.rmtree(base, ignore_errors=True)
    else:
        print(f"\nscratch repository kept for inspection: {root}")
    return 0 if report["ok"] and check.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
