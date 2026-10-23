"""G5 -- the live capacity run, on the free tier.

Named consequence (pilot/amendment-gates.md section 4): *spend, and sustained
load on real providers*.  This run spends **free-tier quota only**; it spends
no money and answers no paid-tier question.

Pre-written criteria: pilot/gate-posture-record.md (G5 P1-P5), written before
this run.  Scope stated there too: hermes, kilo (`kilo-auto/free` router) and
pi only; cline excluded (rate-limited until 2026-10-24); opencode excluded
(the G3 handover attempt already spends its quota and it is exhausted).

What this proves: that real workers, on a real lease, in a real worktree,
follow the same mechanism the demo exercises with the fake CLI -- including
the quota cooldown that exists *because* this run will hit limits.

The ceiling question (`max_total_agents`) is answered by F7/S-W1, not here.

Throwaway repository under %TEMP%; delete the directory to undo everything.

Author: OpenCode.  Date: 2026-10-23.  Authorised by the operator 2026-10-23
("Execute G5").
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "pilot"))

from demo_one_click import build_demo_repo, git, oracle_for  # noqa: E402
from fleet.dispatcher import Dispatcher  # noqa: E402
from fleet.merge import integrate  # noqa: E402
from fleet.project import CLOSING, RUNNING, close_check, init_project  # noqa: E402
from fleet.state import FleetState  # noqa: E402
from pmk import plat  # noqa: E402
from pmk.api import Kernel  # noqa: E402
from pmk.clock import FakeClock  # noqa: E402

DEADLINE_S = 1500          # stop after this much wall time, whatever is left
SAMPLE_S = 1.0             # RAM sample period
NWORKERS = 6               # tiny tasks; each is one file with one print

BRIEF = """Tiny hello-printer suite.

Goals: one module per worker prints its own two-letter token, and a checker
proves every module prints it.
"""

AGENTS = """[fleet]
max_total_agents = 8
dispatch_tick_s = 1
stall_minutes = 15
min_free_ram_mb = 2048

[overseer]
profiles = []

[[profile]]
id = "hermes-live"
adapter = "hermes"
family = "unknown"
priority = 10
max_concurrent = 3
via_gateway = false
roles = ["implement"]
argv_new = ["hermes", "chat", "--oneshot", "-q", "{prompt}", "--yolo", "--cli", "--in", "{cwd}"]
argv_resume = []
models = []

[[profile]]
id = "kilo-live"
adapter = "kilo"
family = "unknown"
priority = 20
max_concurrent = 3
via_gateway = false
roles = ["implement"]
argv_new = ["kilo", "-m", "{model}", "run", "{prompt}", "--dir", "{cwd}", "--auto"]
argv_resume = []
model = "kilo/kilo-auto/free"
models = []

[[profile]]
id = "pi-live"
adapter = "pi"
family = "deepseek"
priority = 30
max_concurrent = 2
via_gateway = false
roles = ["implement"]
argv_new = ["pi", "--provider", "orcarouter", "--model", "deepseek/deepseek-v4-flash-free", "-p", "{prompt}"]
argv_resume = []
models = []
"""

#: A *functional* per-task oracle: run ONE module, check its own token.
#: Written as a real file with the token as an argument, because the merge
#: queue is serial: a gate that requires ALL modules can only pass on the
#: last merge.  Each task's own oracle gates its own merge, exactly as the
#: demo does with its single task.
CHECK_ONE = '''"""Functional check: does the module for this token print its token?"""
import pathlib
import subprocess
import sys

token = sys.argv[1].upper()
root = pathlib.Path(__file__).resolve().parent
script = root / "src" / f"hello_{sys.argv[1]}.py"

out = subprocess.run([sys.executable, str(script)],
                     capture_output=True, text=True)
ok = out.returncode == 0 and token in (out.stdout or "")
print(f"ok: {script.name} prints {token}" if ok else f"FAIL: {out.stdout[:120]}")
sys.exit(0 if ok else 1)
'''

CHECK_ALL = '''"""The project gate: every hello module prints its own token."""
import pathlib
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parent
ok = True
for path in sorted((root / "src").glob("hello_*.py")):
    token = path.stem.split("_", 1)[1].upper()
    out = subprocess.run([sys.executable, str(path)],
                         capture_output=True, text=True)
    if out.returncode != 0 or token not in (out.stdout or ""):
        print("FAIL", path.name, out.stdout[:120])
        ok = False
print("all hello modules print their token" if ok else "check failed")
sys.exit(0 if ok else 1)
'''


def sample_ram(stop: threading.Event, samples: list) -> None:
    """Free RAM, in the background, for the whole run."""
    while not stop.is_set():
        free = plat.free_ram_mb()
        if free is not None:
            samples.append((time.time(), free))
        stop.wait(SAMPLE_S)


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="umaws-g5-"))
    root = build_demo_repo(base)
    print(f"scratch: {root}\n  (delete this directory to undo the whole run)")

    (root / "check_one.py").write_text(CHECK_ONE, encoding="utf-8",
                                      newline="\n")
    (root / "check_all.py").write_text(CHECK_ALL, encoding="utf-8",
                                       newline="\n")
    (root / "agents.toml").write_text(AGENTS, encoding="utf-8", newline="\n")
    (root / "src").mkdir(exist_ok=True)
    (root / "src" / "__init__.py").write_text("", encoding="utf-8")
    (root / ".pm").mkdir(parents=True, exist_ok=True)
    (root / ".pm" / "constitution.md").write_text(
        (ROOT / ".pm" / "constitution.md").read_text(encoding="utf-8"),
        encoding="utf-8")
    (root / ".pm" / "policy.toml").write_text(
        'version = "p-g5"\n\n[gate]\ncmd = \'python check_all.py\'\n',
        encoding="utf-8", newline="\n")
    git(root, "add", "-A")
    git(root, "commit", "-m", "inputs: checker, agents, gate")
    # The PDD the close-check needs (its absence failed the first live run's
    # close-check: "no PDD" -- the same omission the F7 drill made).
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "PDD.md").write_text(
        "# PDD: hello suite      version: 1      status: approved\n\n"
        "## 1. Purpose\n"
        "Six modules, each printing its own two-letter token.\n\n"
        "## 2. Goals\n"
        "### G-001 Token a1\n"
        "acceptance:\n- the a1 module prints A1\n"
        "oracle: `python check_one.py a1`\n\n"
        "### G-002 Token a2\n"
        "acceptance:\n- the a2 module prints A2\n"
        "oracle: `python check_one.py a2`\n\n"
        "### G-003 Token b1\n"
        "acceptance:\n- the b1 module prints B1\n"
        "oracle: `python check_one.py b1`\n\n"
        "## 3. Non-goals\nNo shared code; no tests.\n\n"
        "## 4. Constraints\nStandard library; one file per goal.\n\n"
        "## 5. Architecture sketch\nOne module per token.\n\n"
        "## 6. Definition of done\ngate_cmd: `python check_all.py`\n\n"
        "## 7. Open questions\nNone.\n",
        encoding="utf-8", newline="\n")
    git(root, "add", "docs/PDD.md")
    git(root, "commit", "-m", "docs: the PDD")

    clock = FakeClock()
    kernel = Kernel(root=root, clock=clock)
    kernel.init()
    print(f"[1] kernel initialised: {kernel.status()['chain']}")

    result = init_project(kernel, brief=BRIEF)
    print(f"[2] project created: {result['state']} plan={result['plan_task']}")
    kernel.project_set_state(CLOSING, reason="the PDD is the brief itself")

    tokens = [f"{c}{d}" for c in ("a", "b", "c") for d in ("1", "2")]
    for i, token in enumerate(tokens):
        path = f"src/hello_{token}.py"
        kernel.task_create(
            f"Write {path}: a Python module whose print contains "
            f"{token.upper()}",
            type="implement",
            goal_ref=f"G-{(i % 3) + 1}",
            scope={"write": [path], "read": ["check_one.py", "check_all.py"]},
            oracles=[f"python check_one.py {token}"],
            evidence_required=["oracle_results", "diff_scope"],
            budget={"tokens": 40000, "wall_min": 12},
            priority=10 + i,
        )
    plan = kernel.state().tasks[result["plan_task"]]
    kernel.record_event("TASK_VOIDED", subject=plan.id,
                        payload={"reason": "the brief is the PDD here"})
    kernel.project_set_state(RUNNING, reason="task cards exist")
    print(f"[3] {len(tokens)} task cards created: {tokens}")

    fleet_state = FleetState()
    dispatcher = Dispatcher(kernel, fleet_state,
                            fixture_root=ROOT / "tests" / "fleet" / "fixtures")

    samples: list = []
    stop = threading.Event()
    sampler = threading.Thread(target=sample_ram, args=(stop, samples),
                               daemon=True)
    sampler.start()

    peak_concurrent = 0
    started_at = None
    first_done_at = None
    classes = []
    deadline = time.time() + DEADLINE_S
    while time.time() < deadline:
        report = dispatcher.tick()
        peak_concurrent = max(peak_concurrent, len(dispatcher.runs))
        for s in report.started:
            started_at = started_at or time.time()
            print(f"[4] started {s['task']} on {s['profile']} pid={s['pid']}")
        for f in report.finished:
            line = (f"[5] finished {f['task']}: {f['outcome']}"
                    + (f" [{f['failure_class']}]"
                       if f.get("failure_class") else ""))
            if f.get("error"):
                line += f" -- {f['error']}"
            if f.get("failure_class"):
                classes.append((f["failure_class"], f.get("cooldown", "?")))
            print(line)
        if not dispatcher.runs and all(
                t.state in ("SUBMITTED", "VERIFYING", "DONE", "VOID")
                for t in kernel.state().task_list()):
            break
        time.sleep(0.4)
    stop.set()
    sampler.join(timeout=2)

    free_min = min((f for _, f in samples), default=None)
    print(f"[6] peak concurrent real workers: {peak_concurrent}")
    print(f"    min free RAM during the run: {free_min} MB")
    print(f"    failure classes seen: {classes}")

    state = kernel.state()
    print(f"[7] after dispatch: {state.counts()}")

    gate = kernel.policy().get("gate", {}).get("cmd", "")
    for task in kernel.state().task_list():
        if task.state not in ("SUBMITTED", "VERIFYING"):
            continue
        lease = kernel.state().leases.get(task.id)
        if lease is None or not lease.worktree:
            continue
        # Per-task gate: the merge queue is serial, so a gate needing ALL
        # modules could only pass on the last merge.
        task_gate = (task.acceptance.get("oracles") or [gate])[0]
        merged = integrate(kernel, task, lease, lease.worktree,
                           gate_cmd=task_gate)
        print(f"[8] merge {task.id}: ok={merged.ok} ({merged.message})")
        if merged.ok:
            kernel.integrate(task.id, lease.fence, commit=merged.commit)

    print(f"[9] after the merge queue: {kernel.state().counts()}")
    check = close_check(kernel)
    print(f"[10] close-check: ok={check.ok}")
    for goal in check.goals:
        print(f"     {goal['goal']}: {goal['status']} ({goal.get('oracle','')})")
    for failure in check.failures:
        print(f"     FAILURE: {failure}")

    report = kernel.sentinel()
    print(f"[11] sentinel: ok={report['ok']} findings={report['findings']}")
    print(f"     chain: {kernel.log.verify().summary()}")

    done = sum(1 for t in kernel.state().task_list() if t.state == "DONE")
    bundles = list((kernel.repo.evidence_dir).glob("EB-*/bundle.json"))
    summary = {
        "tasks_done": done,
        "peak_concurrent": peak_concurrent,
        "min_free_ram_mb": free_min,
        "failure_classes": classes,
        "sentinel_ok": report["ok"],
        "close_check_ok": check.ok,
        "evidence_bundles": len(bundles),
        "wall_deadline_s": DEADLINE_S,
    }
    out = ROOT / "pilot" / "spikes" / "g5"
    out.mkdir(parents=True, exist_ok=True)
    (out / "g5-summary.json").write_text(json.dumps(summary, indent=2),
                                         encoding="utf-8", newline="\n")
    print(f"[12] summary: {summary}")
    print(f"     scratch kept: {root}")
    return 0 if (report["ok"] and check.ok and done >= 1) else 1


if __name__ == "__main__":
    raise SystemExit(main())
