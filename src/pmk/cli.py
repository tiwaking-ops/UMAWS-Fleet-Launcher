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


def cmd_pdd_lint(args) -> int:
    from .pdd import lint_file
    result = lint_file(args.file)
    _out(result.to_dict())
    return 0 if result.ok else 1


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

    pdd = sub.add_parser("pdd", help="PDD tooling") \
        .add_subparsers(dest="pdd_command", required=True)
    pdd_lint = pdd.add_parser("lint", help="structure-check a PDD")
    pdd_lint.add_argument("file")
    pdd_lint.set_defaults(func=cmd_pdd_lint)

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
