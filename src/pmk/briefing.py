"""Briefings (pilot v1 section 9.2; hypothesis H6).

A briefing is the **machine-issued authority**.  A session never rebuilds
its context from conversation history: it runs ``pmk brief --role overseer``
and reads what comes back.  Hypothesis H6 tests exactly this — that a fresh
Overseer session can continue from the briefing alone.

The briefing is deterministic: the same log produces the same text.  That is
what makes H6 testable.

The constitution stub is injected into every briefing (CIP Part B section
14.4).  Generated context files may point at the briefing, but they are
never the source of the rules.
"""

from __future__ import annotations

from .models import ACTIVE_STATES
from .state import State


def _constitution(kernel) -> str:
    try:
        return kernel.repo.constitution_path.read_text(encoding="utf-8").strip()
    except OSError:
        return "(constitution file missing)"


def _task_lines(state: State) -> list[str]:
    lines = []
    for task in sorted(state.tasks.values(), key=lambda t: t.id):
        deps = ", ".join(task.depends_on) or "-"
        lines.append(
            f"- {task.id} [{task.state}] type={task.type} goal={task.goal_ref or '-'} "
            f"attempts={task.attempt}/{task.attempts.get('max', '?')} depends_on={deps}\n"
            f"    title: {task.title}\n"
            f"    write scope: {', '.join(task.write_scope) or '-'}\n"
            f"    oracles: {', '.join(task.oracles) or '-'}\n"
            f"    agent hint: {task.agent_hint or '-'}")
    return lines or ["- (none)"]


def render(kernel, role: str = "overseer") -> str:
    """Produce the briefing for *role* from the log alone."""
    state = kernel.state()
    policy = kernel.policy()
    counts = state.counts()
    ready = state.ready_tasks()
    leases = state.active_leases()

    out: list[str] = []
    out.append(f"# Briefing — role: {role}")
    out.append("")
    out.append(f"Generated at {kernel.clock.now_iso()} "
               f"(Kernel time; invariant I7).")
    out.append(f"Policy version {policy.get('version', '?')}  "
               f"policy hash {kernel.policy_hash()[:16]}…")
    out.append(f"Project state: {state.project_state}")
    out.append("")

    out.append("## Constitution (Kernel-owned; wins over any file)")
    out.append("")
    out.append(_constitution(kernel))
    out.append("")

    if role == "worker":
        out.append("## Your lease")
        out.append("")
        if leases:
            for task_id, lease in sorted(leases.items()):
                task = state.tasks.get(task_id)
                out.append(f"- Task {task_id}  fence {lease.fence}  "
                           f"profile {lease.holder}  session {lease.session or '-'}")
                if task:
                    out.append(f"  - scope.write: {', '.join(task.write_scope) or '-'}")
                    out.append(f"  - oracles (run by the harness): "
                               f"{', '.join(task.oracles) or '-'}")
                    out.append(f"  - premises: "
                               f"{', '.join(p.get('id', '?') for p in task.premises) or '-'}")
        else:
            out.append("- (no active lease)")
        out.append("")
        out.append("The harness runs the acceptance commands. Do not claim they "
                   "pass; exit when you are finished and write a short "
                   "`.pmwork/RESULT.md` describing what you did and what you "
                   "tested versus assumed.")
        out.append("")
        return "\n".join(out)

    # -- overseer ---------------------------------------------------------
    out.append("## Where things stand")
    out.append("")
    out.append(f"- Tasks: {len(state.tasks)}  "
               + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    out.append(f"- Ready to dispatch: {len(ready)}")
    out.append(f"- Active leases: {len(leases)}")
    out.append(f"- Open queue items: {len([q for q in state.queue if q['state'] == 'open'])}")
    out.append(f"- Incidents recorded: {len(state.incidents)}")
    out.append("")

    out.append("## Ready tasks (in priority order)")
    out.append("")
    if ready:
        for task in sorted(ready, key=lambda t: (t.priority, t.id)):
            out.append(f"- {task.id} (priority {task.priority}, type {task.type}, "
                       f"goal {task.goal_ref or '-'}) — {task.title}")
            out.append(f"    write scope: {', '.join(task.write_scope) or '-'}")
            out.append(f"    oracles: {', '.join(task.oracles) or '-'}")
    else:
        out.append("- (none)")
    out.append("")

    out.append("## All tasks")
    out.append("")
    out += _task_lines(state)
    out.append("")

    out.append("## Active leases")
    out.append("")
    if leases:
        for task_id, lease in sorted(leases.items()):
            out.append(f"- {task_id}: profile {lease.holder}  fence {lease.fence}  "
                       f"restarts {lease.restart_count}  "
                       f"last failure {lease.last_failure_class or '-'}")
    else:
        out.append("- (none)")
    out.append("")

    open_items = [q for q in state.queue if q["state"] == "open"]
    out.append("## Decisions waiting for the human")
    out.append("")
    if open_items:
        for item in open_items:
            out.append(f"- {item['id']} ({'class K' if item.get('class_k') else 'normal'}): "
                       f"{item.get('topic', '')}")
            out.append(f"    options: {', '.join(item.get('options') or [])}")
            out.append(f"    recommended: {item.get('recommended', '')}")
            out.append(f"    safe default: {item.get('safe_default', '')}")
    else:
        out.append("- (none)")
    out.append("")

    if state.incidents:
        out.append("## Recent incidents")
        out.append("")
        for incident in state.incidents[-10:]:
            out.append(f"- {incident['ts']} [{incident.get('severity', '')}] "
                       f"{incident.get('subject', '')}: {incident.get('message', '')}")
        out.append("")

    out.append("## Rules for you")
    out.append("")
    out.append("- All state changes go through `pmk`. Never edit anything "
               "under `.pm/`.")
    out.append("- This briefing is your authority. If anything in it conflicts "
               "with the constitution above, the constitution wins and you "
               "report the conflict with `pmk incident`.")
    out.append("- Ask the human only through `pmk queue`, with a recommended "
               "option and a safe default.")
    return "\n".join(out).rstrip() + "\n"
