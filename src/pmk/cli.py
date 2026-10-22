"""``pmk`` — the command-line surface (pilot v1 section 9.3).

The CLI is a **thin wrapper** over :mod:`pmk.api`.  It contains no
coordination logic: every command parses arguments, calls the API, and
prints the result.  Fleet amendment D-L4 makes this explicit — the
Dispatcher calls the API in-process, and the CLI calls exactly the same
functions under exactly the same lock, so the two paths cannot diverge.

All mutating commands exit non-zero with a machine-readable reason on
refusal (pilot v1 section 9.3).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .api import Kernel, KernelError
from .bundle import Bundle
from .clock import Clock

#: The console's default encoding on Windows is cp1252 and cannot print
#: the non-ASCII text that agents produce.  Force UTF-8 on the streams.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def _out(payload) -> None:
    if isinstance(payload, str):
        print(payload)
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))


def _kernel(args) -> Kernel:
    return Kernel(root=args.root or None, clock=Clock())


def _fail(exc: KernelError) -> int:
    print(json.dumps(exc.to_dict(), indent=2, ensure_ascii=False, default=str),
          file=sys.stderr)
    return 2


def _load_scope(args) -> dict:
    scope = {"write": list(args.write or []), "read": list(args.read or [])}
    return scope


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------

def cmd_init(args) -> int:
    kernel = _kernel(args)
    _out(kernel.init())
    return 0


def cmd_status(args) -> int:
    kernel = _kernel(args)
    _out(kernel.status())
    return 0


def cmd_task_create(args) -> int:
    kernel = _kernel(args)
    card = kernel.task_create(
        args.title,
        type=args.type,
        goal_ref=args.goal_ref or "",
        scope=_load_scope(args),
        oracles=args.oracle or [],
        evidence_required=args.evidence or [],
        depends_on=args.depends_on or [],
        attempts_max=args.attempts,
        priority=args.priority,
        agent_hint=args.agent_hint or "",
        budget={"tokens": args.budget_tokens, "wall_min": args.budget_minutes},
        admitted=not args.propose,
    )
    _out(card.to_obj())
    return 0


def cmd_task_admit(args) -> int:
    kernel = _kernel(args)
    card = kernel.task_admit(args.task_id)
    _out(card.to_obj())
    return 0


def cmd_task_list(args) -> int:
    kernel = _kernel(args)
    tasks = kernel.task_list(args.state)
    if args.json:
        _out([t.to_obj() for t in tasks])
        return 0
    for task in tasks:
        _out(f"{task.id}  {task.state:<11} {task.type:<10} {task.title}")
    return 0


def cmd_task_show(args) -> int:
    kernel = _kernel(args)
    _out(kernel.task_show(args.task_id))
    return 0


def cmd_claim(args) -> int:
    kernel = _kernel(args)
    lease = kernel.claim(args.task_id, holder=args.profile, agent=args.agent or "",
                         role=args.role or "", worktree=args.worktree or "")
    _out(lease.to_obj())
    return 0


def cmd_renew(args) -> int:
    kernel = _kernel(args)
    lease = kernel.renew(args.task_id, args.fence, digest=args.digest or "")
    _out(lease.to_obj())
    return 0


def cmd_revoke(args) -> int:
    kernel = _kernel(args)
    new_fence = kernel.revoke(args.task_id, args.fence, reason=args.reason or "")
    _out({"task": args.task_id, "new_fence": new_fence})
    return 0


def cmd_submit(args) -> int:
    kernel = _kernel(args)
    bundle = Bundle.from_obj(json.loads(Path(args.bundle).read_text(encoding="utf-8")))
    _out(kernel.submit(args.task_id, args.fence, bundle))
    return 0


def cmd_verify(args) -> int:
    kernel = _kernel(args)
    _out(kernel.verify(args.task_id, args.fence, ok=not args.failed,
                       reasons=args.reason or []))
    return 0


def cmd_integrate(args) -> int:
    kernel = _kernel(args)
    _out(kernel.integrate(args.task_id, args.fence, commit=args.commit or ""))
    return 0


def cmd_brief(args) -> int:
    kernel = _kernel(args)
    print(kernel.brief(args.role))
    return 0


def cmd_sentinel(args) -> int:
    kernel = _kernel(args)
    report = kernel.sentinel()
    _out(report)
    return 0 if report["ok"] else 1


def cmd_views(args) -> int:
    kernel = _kernel(args)
    _out(kernel.render_views(force=True))
    return 0


def cmd_queue_add(args) -> int:
    kernel = _kernel(args)
    item_id = kernel.queue_add(
        topic=args.topic,
        options=args.options,
        recommended=args.recommended or "",
        safe_default=args.safe_default or "",
        class_k=bool(args.class_k),
        details=args.details or "")
    _out({"ok": True, "id": item_id})
    return 0


def cmd_queue_list(args) -> int:
    kernel = _kernel(args)
    _out(kernel.queue_list())
    return 0


def cmd_queue_decide(args) -> int:
    kernel = _kernel(args)
    _out(kernel.queue_decide(args.item_id, args.choice))
    return 0


def cmd_incident(args) -> int:
    kernel = _kernel(args)
    _out(kernel.incident(args.subject or "", args.message,
                         severity=args.severity))
    return 0


def cmd_pins_check(args) -> int:
    kernel = _kernel(args)
    result = kernel.pins_check()
    _out(result)
    return 0 if result["ok"] else 1


def cmd_pins_record(args) -> int:
    """Re-record the pins after a deliberate class K change.

    This is the *only* way the pins should ever change.  A mismatch is an
    I8' breach, so re-recording is an explicit, recorded act, not a
    side-effect of editing a file.
    """
    from pmk.events import Actor
    from pmk.policy import write_pins
    kernel = _kernel(args)
    path = write_pins(kernel.repo)
    kernel.record_event("PINS_CHECKED", actor=Actor.human(),
                        payload={"recorded": str(path),
                                 "note": "the pins were re-recorded"})
    _out({"ok": True, "pins": str(path)})
    return 0


def cmd_pdd_lint(args) -> int:
    from .pdd import lint_file
    result = lint_file(args.file)
    _out(result.to_dict())
    return 0 if result.ok else 1


# ---------------------------------------------------------------------------
# Context commands (CIP Part B section 14)
# ---------------------------------------------------------------------------

def cmd_context_lint(args) -> int:
    kernel = _kernel(args)
    result = kernel.context_lint()
    _out(result)
    return 0 if result["ok"] else 1


def cmd_context_score(args) -> int:
    kernel = _kernel(args)
    _out(kernel.context_score())
    return 0


def cmd_context_sync(args) -> int:
    kernel = _kernel(args)
    result = kernel.context_sync(dry_run=args.dry_run)
    _out(result)
    return 0 if result.get("ok") else 1


def cmd_context_install(args) -> int:
    """Install a reviewed baseline of the managed context files.

    CIP section 8.6 step 1: the files have been generated and read; this
    is the deliberate class K act that puts them in place.  They go through
    the same diff, lint, sanitise and merge machinery as a generated sync.
    """
    kernel = _kernel(args)
    result = kernel.context_sync(source_dir=args.source, commit=args.commit)
    _out(result)
    return 0 if result.get("ok") else 1


def cmd_context_revert(args) -> int:
    kernel = _kernel(args)
    _out(kernel.context_revert(args.seq))
    return 0


def cmd_context_drift(args) -> int:
    kernel = _kernel(args)
    result = kernel.context_drift()
    _out(result)
    return 0 if result["ok"] else 1


def cmd_stop(args) -> int:
    kernel = _kernel(args)
    kernel.repo.stop_file.parent.mkdir(parents=True, exist_ok=True)
    kernel.repo.stop_file.write_text(
        f"stopped at {kernel.clock.now_iso()}\n", encoding="utf-8")
    _out({"ok": True, "stopped": True})
    return 0


def cmd_resume(args) -> int:
    kernel = _kernel(args)
    if kernel.repo.stop_file.exists():
        kernel.repo.stop_file.unlink()
    _out({"ok": True, "stopped": False})
    return 0


def cmd_heartbeat(args) -> int:
    """Record a heartbeat.  With no lease, this reports the current state."""
    kernel = _kernel(args)
    state = kernel.state()
    _out({"tasks": state.counts(),
          "active_leases": len(state.active_leases()),
          "queue": len([q for q in state.queue if q["state"] == "open"])})
    return 0


def cmd_sweep(args) -> int:
    """Expire leases whose TTL has passed."""
    from .clock import parse_iso
    kernel = _kernel(args)
    state = kernel.state()
    expired = []
    now = kernel.clock.now()
    for task_id, lease in state.active_leases().items():
        if not lease.expires_at:
            continue
        try:
            if parse_iso(lease.expires_at) < now:
                expired.append(task_id)
        except (ValueError, TypeError):
            continue
    for task_id in expired:
        try:
            kernel.revoke(task_id, state.leases[task_id].fence,
                          reason="lease TTL expired")
        except KernelError:
            continue
    _out({"expired": expired})
    return 0


# ---------------------------------------------------------------------------
# Fleet commands (fleet amendment section 7.7)
# ---------------------------------------------------------------------------

def _fleet_state(kernel, path=None):
    from fleet.state import FleetState
    return FleetState.load(Path(path) if path else None)


def cmd_fleet_status(args) -> int:
    from fleet.dispatcher import Dispatcher
    kernel = _kernel(args)
    dispatcher = Dispatcher(kernel, _fleet_state(kernel),
                            fixture_root=_fixture_root(kernel))
    _out(dispatcher.status())
    return 0


def cmd_fleet_profiles(args) -> int:
    from fleet.profiles import load_profiles
    kernel = _kernel(args)
    state = _fleet_state(kernel)
    now = time.time()
    rows = []
    for profile in load_profiles(kernel.repo):
        pstate = state.profile(profile.id)
        rows.append({
            "id": profile.id, "adapter": profile.adapter,
            "family": profile.family, "priority": profile.priority,
            "max_concurrent": profile.max_concurrent,
            "roles": profile.roles,
            "enabled": pstate.enabled,
            "cooling_remaining_s": pstate.cooling_remaining(now),
            "last_failure_class": pstate.last_failure_class,
            "runs": pstate.runs, "failures": pstate.failures,
        })
    _out(rows)
    return 0


def cmd_fleet_enable(args) -> int:
    from pmk.events import Actor
    kernel = _kernel(args)
    state = _fleet_state(kernel)
    state.enable(args.profile_id, note="enabled by the operator")
    state.save()
    kernel.record_event("PROFILE_ENABLED", actor=Actor.human(),
                        subject=args.profile_id,
                        payload={"profile": args.profile_id})
    _out({"profile": args.profile_id, "enabled": True})
    return 0


def cmd_fleet_disable(args) -> int:
    from pmk.events import Actor
    kernel = _kernel(args)
    state = _fleet_state(kernel)
    state.disable(args.profile_id, note=args.reason or "disabled by the operator")
    state.save()
    kernel.record_event("PROFILE_DISABLED", actor=Actor.human(),
                        subject=args.profile_id,
                        payload={"profile": args.profile_id,
                                 "reason": args.reason or ""})
    _out({"profile": args.profile_id, "enabled": False})
    return 0


def cmd_fleet_cool(args) -> int:
    from pmk.events import Actor
    kernel = _kernel(args)
    state = _fleet_state(kernel)
    state.cool(args.profile_id, args.minutes * 60,
               note=f"cooled for {args.minutes} minutes")
    state.save()
    kernel.record_event("PROFILE_COOLING", actor=Actor.human(),
                        subject=args.profile_id,
                        payload={"profile": args.profile_id,
                                 "seconds": args.minutes * 60})
    _out({"profile": args.profile_id, "minutes": args.minutes})
    return 0


def cmd_fleet_import_prompts(args) -> int:
    from fleet.profiles import import_prompts, load_profiles, render_agents_toml
    kernel = _kernel(args)
    try:
        profiles = import_prompts(args.file, existing=load_profiles(kernel.repo))
    except ValueError as exc:
        raise KernelError("import_failed", detail=str(exc)) from exc
    if args.dry_run:
        _out([p.to_dict() for p in profiles])
        return 0
    text = render_agents_toml(profiles)
    target = Path(args.file).with_name("agents.imported.toml")
    target.write_text(text, encoding="utf-8", newline="\n")
    _out({"profiles": len(profiles), "written": str(target),
          "note": "merge this into agents.toml by hand: the profile schema is "
                  "a class K change"})
    return 0


def cmd_dispatch_run(args) -> int:
    """Run the dispatch loop for a while (useful without the Console)."""
    from fleet.dispatcher import Dispatcher
    kernel = _kernel(args)
    dispatcher = Dispatcher(kernel, _fleet_state(kernel),
                            fixture_root=_fixture_root(kernel))
    dispatcher.run_forever(max_seconds=args.seconds)
    _out(dispatcher.status())
    return 0


# ---------------------------------------------------------------------------
# Agent commands (fleet amendment section 7.7)
# ---------------------------------------------------------------------------

def _lease_log_path(kernel, task_id: str) -> str:
    for event in reversed(kernel.events()):
        if event.type == "AGENT_STARTED" and event.subject == task_id:
            return str(event.payload.get("log", ""))
    return ""


def cmd_agent_list(args) -> int:
    kernel = _kernel(args)
    state = kernel.state()
    rows = []
    for task_id, lease in sorted(state.active_leases().items()):
        task = state.tasks.get(task_id)
        rows.append({
            "task": task_id,
            "profile": lease.holder,
            "agent": lease.agent,
            "fence": lease.fence,
            "pid": lease.pid,
            "session": lease.session,
            "restarts": lease.restart_count,
            "last_failure_class": lease.last_failure_class,
            "worktree": lease.worktree,
            "title": task.title if task else "",
        })
    _out(rows)
    return 0


def cmd_agent_show(args) -> int:
    kernel = _kernel(args)
    state = kernel.state()
    lease = state.leases.get(args.task)
    task = state.tasks.get(args.task)
    _out({
        "task": args.task,
        "state": task.state if task else None,
        "attempt": task.attempt if task else None,
        "lease": lease.to_obj() if lease else None,
        "failure_history": lease.failure_history if lease else [],
        "log": _lease_log_path(kernel, args.task),
    })
    return 0


def cmd_agent_tail(args) -> int:
    from pmk.plat import tail_file
    kernel = _kernel(args)
    path = _lease_log_path(kernel, args.task)
    if not path:
        raise KernelError("no_log", task=args.task)
    lines = tail_file(path, args.lines)
    _out("\n".join(lines))
    return 0


def cmd_agent_stop(args) -> int:
    from pmk import plat
    kernel = _kernel(args)
    state = kernel.state()
    lease = state.leases.get(args.task)
    if lease is None:
        raise KernelError("no_lease", task=args.task)
    killed, detail = plat.kill_tree(lease.pid,
                                    creation_time=lease.creation_time)
    _out({"task": args.task, "killed": killed, "detail": detail})
    return 0 if killed else 1


def cmd_agent_swap(args) -> int:
    from pmk.events import Actor
    kernel = _kernel(args)
    state = kernel.state()
    if args.task not in state.leases:
        raise KernelError("no_lease", task=args.task)
    kernel.record_event("AGENT_RESUMED", actor=Actor.human(), subject=args.task,
                        fence=state.leases[args.task].fence,
                        payload={"profile": args.profile, "mode": "swap",
                                 "requested_by": "operator"})
    _out({"task": args.task, "profile": args.profile,
          "note": "the Dispatcher picks the profile up on its next tick"})
    return 0


def cmd_agent_send(args) -> int:
    from fleet.order import write_handoff
    kernel = _kernel(args)
    state = kernel.state()
    lease = state.leases.get(args.task)
    if lease is None:
        raise KernelError("no_lease", task=args.task)
    text = ("# Handoff — operator message\n\n"
            + args.text + "\n")
    path = write_handoff(lease.worktree, text) if lease.worktree else None
    kernel.record_event("INCIDENT", subject=args.task,
                        payload={"message": f"operator message: {args.text}",
                                 "severity": "info"})
    _out({"task": args.task, "handoff": str(path) if path else None,
          "note": "headless one-shot CLIs generally do not accept input "
                  "mid-run, so this is delivered as a handoff note"})
    return 0


# ---------------------------------------------------------------------------
# Project commands (fleet amendment section 10)
# ---------------------------------------------------------------------------

def cmd_project_init(args) -> int:
    from fleet.project import init_project
    kernel = _kernel(args)
    _out(init_project(kernel, brief=args.brief, target=args.path))
    return 0


def cmd_project_status(args) -> int:
    from fleet.project import project_status
    kernel = _kernel(args)
    _out(project_status(kernel))
    return 0


def cmd_project_close_check(args) -> int:
    from fleet.project import close_check
    kernel = _kernel(args)
    result = close_check(kernel, pdd_path=args.pdd)
    _out(result.to_dict())
    return 0 if result.ok else 1


def cmd_project_pause(args) -> int:
    from fleet.project import set_state, PAUSED
    kernel = _kernel(args)
    _out(set_state(kernel, PAUSED, reason=args.reason or "paused by the operator"))
    return 0


def cmd_project_resume(args) -> int:
    from fleet.project import RUNNING, set_state
    kernel = _kernel(args)
    current = kernel.project_state()
    target = RUNNING if current == "PAUSED" else current
    _out(set_state(kernel, target, reason=args.reason or "resumed"))
    return 0


def cmd_project_run(args) -> int:
    """Run the Conductor and the Dispatcher for a while."""
    from fleet.conductor import Conductor
    from fleet.dispatcher import Dispatcher
    from fleet.overseer import OverseerRunner
    kernel = _kernel(args)
    fleet_state = _fleet_state(kernel)
    dispatcher = Dispatcher(kernel, fleet_state,
                            fixture_root=_fixture_root(kernel))
    overseer = OverseerRunner(kernel, fleet_state)
    conductor = Conductor(kernel, dispatcher, overseer)
    deadline = time.time() + args.seconds
    while time.time() < deadline:
        conductor.tick()
        dispatcher.tick()
        time.sleep(1)
    _out(project_status(kernel))
    return 0


def _fixture_root(kernel):
    return Path(kernel.repo.root) / "tests" / "fleet" / "fixtures"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pmk",
        description="pmk — the UMAWS Kernel-lite command line. "
                    "The Kernel is the only writer of coordination state.")
    parser.add_argument("--root", help="repository root (default: discovered)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create the layout, first event and pins") \
        .set_defaults(func=cmd_init)
    sub.add_parser("status", help="one-screen status").set_defaults(func=cmd_status)

    task = sub.add_parser("task", help="task cards").add_subparsers(
        dest="task_command", required=True)

    create = task.add_parser("create", help="create a task card")
    create.add_argument("title")
    create.add_argument("--type", default="implement")
    create.add_argument("--goal-ref", dest="goal_ref")
    create.add_argument("--write", action="append", help="write scope (repeatable)")
    create.add_argument("--read", action="append", help="read scope (repeatable)")
    create.add_argument("--oracle", action="append", help="acceptance command")
    create.add_argument("--evidence", action="append")
    create.add_argument("--depends-on", dest="depends_on", action="append")
    create.add_argument("--attempts", type=int, default=3)
    create.add_argument("--priority", type=int, default=100)
    create.add_argument("--agent-hint", dest="agent_hint")
    create.add_argument("--budget-tokens", dest="budget_tokens", type=int, default=0)
    create.add_argument("--budget-minutes", dest="budget_minutes", type=int, default=0)
    create.add_argument("--propose", action="store_true",
                        help="create in PROPOSED (do not admit)")
    create.set_defaults(func=cmd_task_create)

    admit = task.add_parser("admit", help="admit a proposed task")
    admit.add_argument("task_id")
    admit.set_defaults(func=cmd_task_admit)

    lst = task.add_parser("list", help="list tasks")
    lst.add_argument("--state")
    lst.add_argument("--json", action="store_true")
    lst.set_defaults(func=cmd_task_list)

    show = task.add_parser("show", help="show one task")
    show.add_argument("task_id")
    show.set_defaults(func=cmd_task_show)

    claim = sub.add_parser("claim", help="claim a task for a lease")
    claim.add_argument("task_id")
    claim.add_argument("--profile", required=True)
    claim.add_argument("--agent")
    claim.add_argument("--role")
    claim.add_argument("--worktree")
    claim.set_defaults(func=cmd_claim)

    renew = sub.add_parser("renew", help="renew a lease")
    renew.add_argument("task_id")
    renew.add_argument("--fence", type=int, required=True)
    renew.add_argument("--digest")
    renew.set_defaults(func=cmd_renew)

    revoke = sub.add_parser("revoke", help="revoke a lease and bump the fence")
    revoke.add_argument("task_id")
    revoke.add_argument("--fence", type=int, required=True)
    revoke.add_argument("--reason")
    revoke.set_defaults(func=cmd_revoke)

    submit = sub.add_parser("submit", help="submit work with an evidence bundle")
    submit.add_argument("task_id")
    submit.add_argument("--fence", type=int, required=True)
    submit.add_argument("--bundle", required=True, help="path to bundle.json")
    submit.set_defaults(func=cmd_submit)

    verify = sub.add_parser("verify", help="record a verification result")
    verify.add_argument("task_id")
    verify.add_argument("--fence", type=int, required=True)
    verify.add_argument("--failed", action="store_true")
    verify.add_argument("--reason", action="append")
    verify.set_defaults(func=cmd_verify)

    integrate = sub.add_parser("integrate", help="promote a verified task")
    integrate.add_argument("task_id")
    integrate.add_argument("--fence", type=int, required=True)
    integrate.add_argument("--commit")
    integrate.set_defaults(func=cmd_integrate)

    brief = sub.add_parser("brief", help="print a briefing from the log alone")
    brief.add_argument("--role", default="overseer",
                       choices=["overseer", "worker"])
    brief.set_defaults(func=cmd_brief)

    sub.add_parser("sentinel", help="check the pilot invariants") \
        .set_defaults(func=cmd_sentinel)
    sub.add_parser("views", help="regenerate the views") \
        .set_defaults(func=cmd_views)
    sub.add_parser("heartbeat", help="report the current state") \
        .set_defaults(func=cmd_heartbeat)
    sub.add_parser("sweep", help="expire leases past their TTL") \
        .set_defaults(func=cmd_sweep)

    queue = sub.add_parser("queue", help="human decision queue") \
        .add_subparsers(dest="queue_command", required=True)
    queue_add = queue.add_parser("add", help="raise a question for the human")
    queue_add.add_argument("--topic", required=True)
    queue_add.add_argument("--option", dest="options", action="append",
                           default=[], help="repeat for each option")
    queue_add.add_argument("--recommended", help="the agent's recommendation")
    queue_add.add_argument("--safe-default",
                           help="what happens if the human says nothing")
    queue_add.add_argument("--class-k", action="store_true",
                           help="class K: needs the human, two-key")
    queue_add.add_argument("--details", help="the full context, for the human")
    queue_add.set_defaults(func=cmd_queue_add)
    queue.add_parser("list", help="list queue items") \
        .set_defaults(func=cmd_queue_list)
    decide = queue.add_parser("decide", help="decide a queue item")
    decide.add_argument("item_id")
    decide.add_argument("choice")
    decide.set_defaults(func=cmd_queue_decide)

    incident = sub.add_parser("incident", help="record an incident")
    incident.add_argument("message")
    incident.add_argument("--subject")
    incident.add_argument("--severity", default="warn")
    incident.set_defaults(func=cmd_incident)

    pins = sub.add_parser("pins", help="pinned files") \
        .add_subparsers(dest="pins_command", required=True)
    pins.add_parser("check", help="verify the pins") \
        .set_defaults(func=cmd_pins_check)
    pins.add_parser("record", help="re-record the pins after a class K change") \
        .set_defaults(func=cmd_pins_record)

    pdd = sub.add_parser("pdd", help="PDD tooling") \
        .add_subparsers(dest="pdd_command", required=True)
    pdd_lint = pdd.add_parser("lint", help="structure-check a PDD")
    pdd_lint.add_argument("file")
    pdd_lint.set_defaults(func=cmd_pdd_lint)

    # -- context (CIP Part B section 14) ---------------------------------
    context = sub.add_parser("context", help="the generated context files") \
        .add_subparsers(dest="context_command", required=True)
    context.add_parser("lint", help="lint the managed context files (I15)") \
        .set_defaults(func=cmd_context_lint)
    context.add_parser("score", help="the generator's read-only score") \
        .set_defaults(func=cmd_context_score)
    context.add_parser("drift", help="check for out-of-band edits (I16)") \
        .set_defaults(func=cmd_context_drift)

    context_sync = context.add_parser("sync", help="run the context-sync task")
    context_sync.add_argument("--dry-run", dest="dry_run", action="store_true",
                              default=None,
                              help="preview without merging (the default "
                                   "until gate G4)")
    context_sync.set_defaults(func=cmd_context_sync)

    context_install = context.add_parser(
        "install", help="install a reviewed baseline of the context files")
    context_install.add_argument("--from", dest="source", required=True,
                                 help="a directory holding the generated files")
    context_install.add_argument("--commit", action="store_true",
                                  help="merge them (a deliberate class K act)")
    context_install.set_defaults(func=cmd_context_install)

    context_revert = context.add_parser("revert", help="revert a context sync")
    context_revert.add_argument("seq", type=int)
    context_revert.set_defaults(func=cmd_context_revert)

    # -- fleet (fleet amendment section 7.7) ----------------------------
    fleet = sub.add_parser("fleet", help="the fleet and its profiles") \
        .add_subparsers(dest="fleet_command", required=True)
    fleet.add_parser("status", help="profiles, slots, cap, dispatch state") \
        .set_defaults(func=cmd_fleet_status)
    fleet.add_parser("profiles", help="list the profiles") \
        .set_defaults(func=cmd_fleet_profiles)

    enable = fleet.add_parser("enable", help="enable a profile")
    enable.add_argument("profile_id")
    enable.set_defaults(func=cmd_fleet_enable)

    disable = fleet.add_parser("disable", help="disable a profile")
    disable.add_argument("profile_id")
    disable.add_argument("--reason")
    disable.set_defaults(func=cmd_fleet_disable)

    cool = fleet.add_parser("cool", help="cool a profile for N minutes")
    cool.add_argument("profile_id")
    cool.add_argument("--minutes", type=int, required=True)
    cool.set_defaults(func=cmd_fleet_cool)

    import_prompts = fleet.add_parser(
        "import-prompts", help="generate profiles from prompts.json")
    import_prompts.add_argument("file")
    import_prompts.add_argument("--dry-run", dest="dry_run",
                                action="store_true")
    import_prompts.set_defaults(func=cmd_fleet_import_prompts)

    dispatch = sub.add_parser("dispatch", help="the dispatch loop") \
        .add_subparsers(dest="dispatch_command", required=True)
    dispatch_run = dispatch.add_parser("run", help="run the dispatch loop")
    dispatch_run.add_argument("--seconds", type=float, default=30)
    dispatch_run.set_defaults(func=cmd_dispatch_run)

    # -- agents (fleet amendment section 7.7) ---------------------------
    agent = sub.add_parser("agent", help="the running agents") \
        .add_subparsers(dest="agent_command", required=True)
    agent.add_parser("list", help="the running slots") \
        .set_defaults(func=cmd_agent_list)

    agent_show = agent.add_parser("show", help="one agent")
    agent_show.add_argument("task")
    agent_show.set_defaults(func=cmd_agent_show)

    agent_tail = agent.add_parser("tail", help="the tail of an agent's log")
    agent_tail.add_argument("task")
    agent_tail.add_argument("-n", "--lines", type=int, default=40)
    agent_tail.set_defaults(func=cmd_agent_tail)

    agent_stop = agent.add_parser("stop", help="stop an agent's process")
    agent_stop.add_argument("task")
    agent_stop.set_defaults(func=cmd_agent_stop)

    agent_swap = agent.add_parser("swap", help="force a profile for an agent")
    agent_swap.add_argument("task")
    agent_swap.add_argument("--profile", required=True)
    agent_swap.set_defaults(func=cmd_agent_swap)

    agent_send = agent.add_parser("send", help="send a follow-up")
    agent_send.add_argument("task")
    agent_send.add_argument("text")
    agent_send.set_defaults(func=cmd_agent_send)

    # -- project (fleet amendment section 10) ---------------------------
    project = sub.add_parser("project", help="the project lifecycle") \
        .add_subparsers(dest="project_command", required=True)

    project_init = project.add_parser("init", help="create a project")
    project_init.add_argument("--brief", required=True)
    project_init.add_argument("--path")
    project_init.set_defaults(func=cmd_project_init)

    project.add_parser("status", help="the project status") \
        .set_defaults(func=cmd_project_status)

    project_close = project.add_parser("close-check",
                                       help="run the goal oracles and the gate")
    project_close.add_argument("--pdd")
    project_close.set_defaults(func=cmd_project_close_check)

    project_pause = project.add_parser("pause", help="pause the project")
    project_pause.add_argument("--reason")
    project_pause.set_defaults(func=cmd_project_pause)

    project_resume = project.add_parser("resume", help="resume the project")
    project_resume.add_argument("--reason")
    project_resume.set_defaults(func=cmd_project_resume)

    project_run = project.add_parser("run", help="run the project unattended")
    project_run.add_argument("--seconds", type=float, default=60)
    project_run.set_defaults(func=cmd_project_run)

    sub.add_parser("stop", help="stop-the-line: freeze promotion and leases") \
        .set_defaults(func=cmd_stop)
    sub.add_parser("resume", help="lift the stop-the-line flag") \
        .set_defaults(func=cmd_resume)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except KernelError as exc:
        return _fail(exc)
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
