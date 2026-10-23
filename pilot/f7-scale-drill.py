"""F7 and S-W1 -- the scale evidence for `max_total_agents`.

Two parts, both on the **fake** CLI (no provider calls, no quota):

1. **S-W1** -- worktree cost: the wall time, disk and RAM of creating 20 and
   then 100 git worktrees on this machine.  The proposal (fleet-launcher
   section 12/13, R-F3): 100 worktrees cost disk, time and RAM, and this
   measurement -- not a guess -- is what sets `max_total_agents`.
2. **F7** -- the scale drill: 100 tasks dispatched at once, one fake profile
   with 100 slots.  fleet-launcher section G-F5: `max_total_agents` is raised
   from 20 to the operator ceiling 100 **only** after F7 passes.

Pre-written criteria: pilot/gate-posture-record.md (F7 F1-F4), written before
the run.

Throwaway repositories under %TEMP%; delete the directories to undo.

Author: OpenCode.  Date: 2026-10-23.  F7 and S-W1 are **checkpoint** actions
(no provider is called); logged, not asked about.
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
from fleet.project import close_check, set_state, DONE  # noqa: E402
from fleet.state import FleetState  # noqa: E402
from pmk import plat  # noqa: E402
from pmk.api import Kernel  # noqa: E402
from pmk.clock import FakeClock  # noqa: E402

NTASKS = 100
DEADLINE_S = 1800


def dir_size_mb(path: Path) -> float:
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total / (1024 * 1024)


# ---------------------------------------------------------------- S-W1
def s_w1(base: Path) -> dict:
    """Worktree cost: 20, then 100 more."""
    root = base / "sw1"
    root.mkdir(parents=True)
    (root / "README.md").write_text("worktree cost\n", encoding="utf-8")
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "umaws-pilot")
    git(root, "config", "user.email", "umaws-pilot@localhost")
    git(root, "add", "-A")
    git(root, "commit", "-m", "initial")

    work = root / "work"
    work.mkdir()
    out = {}

    ram_before = plat.free_ram_mb()
    for label, count in (("worktrees_20", 20), ("worktrees_100", 100)):
        started = time.time()
        for i in range(count):
            git(work if False else root, "worktree", "add", "--detach",
                str(work / f"{label}-{i:03d}"))
        elapsed = time.time() - started
        out[label] = {"count": count, "wall_s": round(elapsed, 1),
                      "per_worktree_s": round(elapsed / count, 2)}
        print(f"[S-W1] {label}: {count} worktrees in {elapsed:.1f}s "
              f"({elapsed / count:.2f}s each)")

    out["disk_mb"] = round(dir_size_mb(work), 1)
    out["free_ram_before_mb"] = ram_before
    out["free_ram_after_mb"] = plat.free_ram_mb()
    print(f"[S-W1] disk: {out['disk_mb']} MB for 120 worktrees; "
          f"free RAM {ram_before} -> {out['free_ram_after_mb']} MB")
    return out


# ---------------------------------------------------------------- F7
def f7(base: Path) -> dict:
    """100 tasks, one fake profile, 100 slots."""
    root = build_demo_repo(base / "f7root")
    (root / "agents.toml").write_text(f"""[fleet]
max_total_agents = 100
dispatch_tick_s = 1
stall_minutes = 15
min_free_ram_mb = 2048

[overseer]
profiles = []

[[profile]]
id = "fake-100"
adapter = "fake"
family = "unknown"
priority = 10
max_concurrent = 100
via_gateway = false
roles = ["implement"]
argv_new = []
argv_resume = []
scenario = "ok"
""", encoding="utf-8", newline="\n")

    (root / "src").mkdir(exist_ok=True)
    (root / ".pm").mkdir(parents=True, exist_ok=True)
    (root / ".pm" / "constitution.md").write_text(
        (ROOT / ".pm" / "constitution.md").read_text(encoding="utf-8"),
        encoding="utf-8")
    # The project gate, as a real file: the previous run inlined a python
    # one-liner with single quotes inside a TOML *literal* string, which is
    # invalid TOML -- the policy silently fell back to defaults and the gate
    # became "pytest -q", which exits 5 with no tests to collect.  Every
    # merge was then refused (I5 held; the run failed).  Written as a file so
    # the TOML needs no escaping at all.
    (root / "check_all.py").write_text(
        'import pathlib, sys\n'
        'ok = all(pathlib.Path("src", f"f7_{i:03d}.py").exists()\n'
        '         for i in range(100))\n'
        'print("all 100 markers present" if ok else "markers missing")\n'
        'sys.exit(0 if ok else 1)\n', encoding="utf-8", newline="\n")
    (root / ".pm" / "policy.toml").write_text(
        'version = "p-f7"\n\n[gate]\ncmd = \'python check_all.py\'\n',
        encoding="utf-8", newline="\n")
    git(root, "add", "-A")
    git(root, "commit", "-m", "inputs: fake profile, gate")
    # A PDD, so the close-check has goals to check (the first re-run scored
    # 100/100 DONE but its close-check failed with "no PDD" - the drill had
    # created task cards directly, without the project lifecycle).
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "PDD.md").write_text(
        "# PDD: f7 scale drill      version: 1      status: approved\n\n"
        "## 1. Purpose\nProve 100 concurrent slots complete and merge.\n\n"
        "## 2. Goals\n"
        "### G-001 All hundred markers\n"
        "acceptance:\n"
        "- 100 modules exist and print their own token\n"
        "oracle: `python check_all.py`\n\n"
        "## 3. Non-goals\nNothing else.\n\n"
        "## 4. Constraints\nFake CLI only; no provider is called.\n\n"
        "## 5. Architecture sketch\nOne module per task; the harness runs the oracles.\n\n"
        "## 6. Definition of done\n"
        "gate_cmd: `python check_all.py`\n\n"
        "## 7. Open questions\nNone.\n",
        encoding="utf-8", newline="\n")
    git(root, "add", "docs/PDD.md")
    git(root, "commit", "-m", "docs: the f7 PDD")

    kernel = Kernel(root=root, clock=FakeClock())
    kernel.init()
    for i in range(NTASKS):
        path = f"src/f7_{i:03d}.py"
        kernel.task_create(
            f"Write {path} (marker {i:03d})",
            type="implement",
            goal_ref="G-001",
            scope={"write": [path], "read": []},
            oracles=[oracle_for(path)],
            evidence_required=["oracle_results", "diff_scope"],
            budget={"tokens": 1000, "wall_min": 5},
            priority=10,
        )
    print(f"[F7] {NTASKS} task cards created")

    dispatcher = Dispatcher(kernel, FleetState(),
                            fixture_root=ROOT / "tests" / "fleet" / "fixtures")

    samples: list = []
    stop = threading.Event()

    def sampler():
        while not stop.is_set():
            free = plat.free_ram_mb()
            if free is not None:
                samples.append(free)
            stop.wait(1.0)

    thread = threading.Thread(target=sampler, daemon=True)
    thread.start()

    peak = 0
    deadline = time.time() + DEADLINE_S
    t0 = time.time()
    while time.time() < deadline:
        report = dispatcher.tick()
        peak = max(peak, len(dispatcher.runs))
        for f in report.finished:
            if f.get("failure_class"):
                print(f"     FAILURE {f['task']}: {f['failure_class']}")
        # Break when nothing is running and every task has reached the merge
        # queue (SUBMITTED) or a terminal state.  The previous version waited
        # for DONE/VOID -- and SUBMITTED tasks are neither -- so it spun for
        # the whole deadline after the work was done.
        if not dispatcher.runs and all(
                t.state in ("SUBMITTED", "VERIFYING", "DONE", "VOID")
                for t in kernel.state().task_list()):
            break
        time.sleep(0.2)
    stop.set()
    thread.join(timeout=2)
    wall = time.time() - t0

    state = kernel.state()
    counts = state.counts()
    print(f"[F7] after dispatch: {counts} in {wall:.0f}s; "
          f"peak concurrent slots: {peak}; min free RAM: {min(samples)} MB")

    # Per-task gate: the merge queue is serial and merges one task at a
    # time, so a gate that requires ALL 100 files can only pass on the last
    # merge.  Each task's own acceptance oracle is the gate for its merge,
    # exactly as the demo does with its single task.
    gate = kernel.policy().get("gate", {}).get("cmd", "")
    merged = 0
    rejected = 0
    for task in kernel.state().task_list():
        if task.state not in ("SUBMITTED", "VERIFYING"):
            continue
        lease = kernel.state().leases.get(task.id)
        if lease is None or not lease.worktree:
            continue
        task_gate = (task.acceptance.get("oracles") or [gate])[0]
        result = integrate(kernel, task, lease, lease.worktree,
                           gate_cmd=task_gate)
        if result.ok:
            kernel.integrate(task.id, lease.fence, commit=result.commit)
            merged += 1
        else:
            rejected += 1
            print(f"     merge {task.id} REJECTED: {result.message[:120]}")
    print(f"[F7] merges: {merged} ok, {rejected} rejected")
    check = close_check(kernel)
    report = kernel.sentinel()
    done = sum(1 for t in kernel.state().task_list() if t.state == "DONE")

    out = {"tasks": NTASKS, "done": done, "merged": merged,
           "peak_concurrent_slots": peak, "wall_s": round(wall, 1),
           "min_free_ram_mb": min(samples), "sentinel_ok": report["ok"],
           "close_check_ok": check.ok, "counts": counts,
           "chain": kernel.log.verify().summary()}
    print(f"[F7] merged {merged}; sentinel ok={report['ok']}; "
          f"chain {out['chain']}")
    print(f"[F7] close-check: ok={check.ok}")
    return out


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="umaws-scale-"))
    print(f"scratch base: {base}\n")
    sw1 = {} if "--skip-sw1" in sys.argv else s_w1(base)
    drill = f7(base)
    summary = {"s_w1": sw1, "f7": drill}
    out = ROOT / "pilot" / "spikes"
    (out / "scale-f7.json").write_text(json.dumps(summary, indent=2),
                                       encoding="utf-8", newline="\n")
    print(f"\n[summary] {json.dumps(summary, indent=2)}")
    print(f"[summary] written to {out / 'scale-f7.json'}")

    passed = (drill["done"] == NTASKS and drill["sentinel_ok"]
              and drill["close_check_ok"])
    print(f"\nF7 VERDICT: {'PASS' if passed else 'FAIL'} "
          f"(done={drill['done']}/{NTASKS}, "
          f"peak slots={drill['peak_concurrent_slots']})")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
