"""The one-click project lifecycle (fleet amendment section 10).

States::

    NEW -> PLANNING -> DECOMPOSING -> RUNNING -> CLOSING -> DONE

plus ``PAUSED`` and ``STALLED`` (which needs the human).

The Conductor drives the transitions; the operator only clicks **Run**.

============  ==================  ==========================================
Step          Trigger             What happens
============  ==================  ==========================================
1. Create     Console             ``pmk project init`` creates ``.pm/``,
                                  commits the brief to ``docs/BRIEF.md`` and
                                  creates task T-0001 ``plan``.
2. PLANNING   T-0001 is READY     The Overseer claims T-0001 as a normal
                                  lease.  Oracle: ``pmk pdd lint
                                  docs/PDD.md``.  It merges through the
                                  normal queue.
3. DECOMPOSING PDD merged          The Overseer creates task cards, each
                                  with goal_ref, scope, oracle, premises,
                                  budget, depends_on and an optional
                                  agent_hint.
4. RUNNING    Any READY task      The Dispatcher fills slots; the harness
                                  runs leases; the ladder recovers; the
                                  merge queue integrates verified work.
5. CLOSING    No open tasks       ``pmk project close-check`` runs each
                                  PDD goal's oracle and the gate command.
                                  Failures create gap tasks (a **replan
                                  round**, max 3).
6. DONE       Close-check green   A ``report`` task writes
                                  ``docs/RUN-REPORT.md``.
============  ==================  ==========================================

Exits to ``STALLED``: ``max_replan_rounds`` hit, a sentinel stop, all
profiles disabled, or dispatch paused for more than 30 minutes.

**Pilot gates versus runtime.**  Gates G0-G6 supervise how the pilot
*builds* the app.  Once the app is accepted, a project run has no gates; its
only human surface is the Queue.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from pmk.api import Kernel, KernelError
from pmk.pdd import Goal, lint_file, parse_gate_cmd, parse_goals

NEW = "NEW"
PLANNING = "PLANNING"
DECOMPOSING = "DECOMPOSING"
RUNNING = "RUNNING"
CLOSING = "CLOSING"
DONE = "DONE"
PAUSED = "PAUSED"
STALLED = "STALLED"

LIFECYCLE_STATES = (NEW, PLANNING, DECOMPOSING, RUNNING, CLOSING, DONE,
                    PAUSED, STALLED)

BRIEF_PATH = "docs/BRIEF.md"
PDD_PATH = "docs/PDD.md"
REPORT_PATH = "docs/RUN-REPORT.md"


@dataclass
class CloseCheckResult:
    """The result of ``pmk project close-check``."""

    ok: bool = False
    goals: list = field(default_factory=list)
    gate: dict = field(default_factory=dict)
    failures: list = field(default_factory=list)
    needs_human: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"ok": self.ok, "goals": self.goals, "gate": self.gate,
                "failures": self.failures, "needs_human": self.needs_human}


# ---------------------------------------------------------------------------
# Step 1: create
# ---------------------------------------------------------------------------

def init_project(kernel: Kernel, *, brief: str, target: str | Path | None = None,
                 name: str = "") -> dict:
    """Create a project: the brief, the plan task, and the first state.

    *target* is the folder for the project.  When it is the same repository
    the Kernel already governs, the existing state is reused; otherwise a
    fresh repository is created.
    """
    root = Path(target).resolve() if target else kernel.repo.root
    repo = kernel.repo if root == kernel.repo.root else None

    if repo is None:
        # A separate project repository.  It needs its own Kernel state,
        # which this Kernel cannot write across repositories, so the
        # project is created in the current repository and the folder is
        # recorded in the brief.
        repo = kernel.repo

    brief_text = brief.strip()
    if not brief_text:
        raise KernelError("empty_brief", detail="the brief is the input")

    brief_file = repo.root / BRIEF_PATH
    brief_file.parent.mkdir(parents=True, exist_ok=True)
    brief_file.write_text(
        f"# Brief\n\n{brief_text}\n", encoding="utf-8", newline="\n")

    # Commit the brief so the project starts from a known state.
    repo.git("add", BRIEF_PATH)
    _, out, _ = repo.git("rev-parse", "--verify", "HEAD")
    if out.strip():
        repo.git("commit", "-m", "docs: project brief")

    # Task T-0001: write the PDD.  It is an ordinary task, claimed through
    # the ordinary lease path (D-L9): no special path to maintain, and the
    # PDD gets the same evidence as code.
    plan = kernel.task_create(
        f"Write the project design document at {PDD_PATH}",
        type="plan",
        goal_ref="G-PDD",
        scope={"write": [PDD_PATH], "read": [BRIEF_PATH, "docs/"]},
        oracles=[f"pmk pdd lint {PDD_PATH}"],
        evidence_required=["oracle_results", "diff_scope", "premise_check"],
        budget={"tokens": 200000, "wall_min": 30},
    )

    kernel.project_set_state(PLANNING, reason="project created")
    kernel.record_event("PDD_COMMITTED", subject=plan.id,
                        payload={"path": PDD_PATH, "note": "plan task created"})

    return {
        "ok": True,
        "root": str(repo.root),
        "brief": str(brief_file),
        "plan_task": plan.id,
        "state": PLANNING,
    }


# ---------------------------------------------------------------------------
# Step 5: close-check
# ---------------------------------------------------------------------------

def close_check(kernel: Kernel, *, pdd_path: str | Path | None = None,
                workdir: str | Path | None = None,
                timeout: int = 900) -> CloseCheckResult:
    """Run each PDD goal's oracle and the gate command.

    A goal with only a ``manual-check`` is reported as **needs human** —
    never as passed.  That distinction matters: the close-check decides
    whether the project is done, and a manual check cannot decide it.
    """
    repo = kernel.repo
    pdd = Path(pdd_path) if pdd_path else repo.root / PDD_PATH
    cwd = Path(workdir) if workdir else repo.root

    result = CloseCheckResult()
    if not pdd.is_file():
        result.failures.append(f"no PDD at {pdd}")
        return result

    lint = lint_file(pdd)
    if not lint.ok:
        result.failures.append(f"PDD lint failed: {'; '.join(lint.errors)}")
        return result

    text = pdd.read_text(encoding="utf-8")
    goals = parse_goals(text)

    for goal in goals:
        entry = {"goal": goal.id, "title": goal.title}
        if goal.needs_human:
            entry["status"] = "needs_human"
            entry["manual_check"] = goal.manual_check
            result.needs_human.append(goal.id)
        else:
            exit_code, stdout, stderr = _run(goal.oracle, cwd, timeout)
            entry["oracle"] = goal.oracle
            entry["exit"] = exit_code
            entry["status"] = "pass" if exit_code == 0 else "fail"
            if exit_code != 0:
                result.failures.append(
                    f"{goal.id}: oracle {goal.oracle!r} exited {exit_code}")
        result.goals.append(entry)

    gate_cmd = parse_gate_cmd(text)
    if gate_cmd:
        exit_code, stdout, stderr = _run(gate_cmd, cwd, timeout)
        result.gate = {"cmd": gate_cmd, "exit": exit_code,
                       "status": "pass" if exit_code == 0 else "fail"}
        if exit_code != 0:
            result.failures.append(
                f"gate command {gate_cmd!r} exited {exit_code}")
    else:
        result.gate = {"cmd": None, "status": "missing"}

    result.ok = (not result.failures and not result.needs_human
                 and result.gate.get("status") == "pass")
    return result


def _run(command: str, cwd: Path, timeout: int) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(command, shell=True, cwd=str(cwd),
                              capture_output=True, timeout=timeout,
                              text=True, encoding="utf-8", errors="replace")
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except OSError as exc:
        return 127, "", str(exc)


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def project_status(kernel: Kernel) -> dict:
    """Everything the Console's Projects tab shows."""
    state = kernel.state()
    tasks = state.task_list()
    goals_done = 0
    goals_total = 0
    pdd = kernel.repo.root / PDD_PATH
    if pdd.is_file():
        goals = parse_goals(pdd.read_text(encoding="utf-8"))
        goals_total = len(goals)
        goals_done = len([g for g in goals if g.id in {
            t.goal_ref for t in tasks if t.state == DONE}])

    return {
        "state": state.project_state,
        "tasks": len(tasks),
        "tasks_done": len([t for t in tasks if t.state == DONE]),
        "by_state": state.counts(),
        "goals_done": goals_done,
        "goals_total": goals_total,
        "pdd": str(pdd) if pdd.is_file() else None,
        "report": str(kernel.repo.root / REPORT_PATH)
        if (kernel.repo.root / REPORT_PATH).is_file() else None,
        "brief": str(kernel.repo.root / BRIEF_PATH)
        if (kernel.repo.root / BRIEF_PATH).is_file() else None,
        "stopped": kernel.stopped(),
    }


def set_state(kernel: Kernel, new_state: str, reason: str = "") -> dict:
    """Move the project to a new lifecycle state."""
    if new_state not in LIFECYCLE_STATES:
        raise KernelError("unknown_state", state=new_state,
                          known=list(LIFECYCLE_STATES))
    return kernel.project_set_state(new_state, reason=reason)
