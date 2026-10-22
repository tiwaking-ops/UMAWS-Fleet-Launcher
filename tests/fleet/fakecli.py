"""A scriptable fake CLI, so the Fleet can be tested without LLMs or quota.

Fleet amendment section 12.E.  Rule 19 of the fleet's rules of engagement
is "fake first": every Fleet behaviour is tested on this before any real CLI
or real quota is used.

Usage::

    python fakecli.py --scenario ok --cwd <worktree>

Scenarios
---------

``ok``
    Do the work and exit 0.
``quota`` / ``auth`` / ``network`` / ``model-gone``
    Print **synthetic** failure text and exit non-zero.  The text says
    nothing about any real provider; it is a fixed string so that the
    classifier fixtures can match it.
``crash``
    Die without printing a recognised failure.
``hang``
    Sleep forever.  Used to test stall detection.
``slow``
    Work slowly, for tests that need the poller to observe progress.
``oracle-fail-then-ok``
    Fail the oracle on the first attempt and pass it on the next, so the
    fix-round path can be exercised.  The attempt counter lives in
    ``.fakecli-fix-round`` in the worktree.

The fake reads ``.pmwork/ORDER.md`` (the work order the Dispatcher wrote),
writes a deterministic file change, prints a fake session id, and supports
resume by reading ``.fakecli-session.json`` in the worktree.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

SESSION_FILE = ".fakecli-session.json"
FIX_ROUND_FILE = ".fakecli-fix-round"
OUTPUT_FILE = "fake-output.txt"

#: Synthetic failure text.  These strings are what the fake CLI's own
#: fixtures match.  They are deliberately labelled so that nobody can
#: mistake a captured fake failure for a captured provider failure.
SYNTHETIC_FAILURES = {
    "quota": ("SYNTHETIC-FAILURE-QUOTA: quota exhausted for this fake "
              "deployment (fake CLI; not a real provider)"),
    "auth": ("SYNTHETIC-FAILURE-AUTH: credentials rejected by the fake "
             "provider (fake CLI; not a real provider)"),
    "network": ("SYNTHETIC-FAILURE-NETWORK: connection to the fake provider "
                "failed (fake CLI; not a real provider)"),
    "model-gone": ("SYNTHETIC-FAILURE-MODEL-GONE: the fake model no longer "
                   "exists (fake CLI; not a real provider)"),
}

EXIT_CODES = {
    "quota": 2,
    "auth": 3,
    "network": 4,
    "model-gone": 5,
    "crash": 139,
}


def log(message: str) -> None:
    print(message, flush=True)


def read_order(cwd: Path) -> str:
    """Read the work order the Dispatcher wrote."""
    order = cwd / ".pmwork" / "ORDER.md"
    try:
        return order.read_text(encoding="utf-8")
    except OSError:
        return ""


def write_scope_from_order(order: str) -> list[str]:
    """Extract the declared write scope from the order.

    The fake behaves like a well-mannered worker: it writes **inside** the
    scope the order gives it.  That keeps the harness's scope check
    meaningful — a real out-of-scope write is still detected, because the
    fake only writes where it was told to.
    """
    for line in order.splitlines():
        if not line.startswith("## Scope"):
            continue
        if "Write only:" not in line:
            continue
        tail = line.split("Write only:", 1)[1]
        scope_text = tail.split("Read:", 1)[0]
        return [part.strip() for part in scope_text.split(",") if part.strip()]
    return []


def session_path(cwd: Path) -> Path:
    return cwd / SESSION_FILE


def load_session(cwd: Path) -> dict:
    try:
        return json.loads(session_path(cwd).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_session(cwd: Path, data: dict) -> None:
    try:
        session_path(cwd).write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
    except OSError:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fake CLI for Fleet tests")
    parser.add_argument("--scenario", default="ok",
                        choices=["ok", "quota", "auth", "network",
                                 "model-gone", "crash", "hang", "slow",
                                 "oracle-fail-then-ok"])
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--cwd", default=None)
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--work-file", default="fake-work.txt")
    args = parser.parse_args(argv)

    cwd = Path(args.cwd).resolve() if args.cwd else Path.cwd()
    if not cwd.is_dir():
        log(f"fakecli: worktree does not exist: {cwd}")
        return 66

    # -- resume ------------------------------------------------------------
    stored = load_session(cwd)
    if args.resume:
        session_id = args.session_id or stored.get("session_id") or "fake-0001"
        attempts = int(stored.get("attempts", 1)) + 1
        log(f"fakecli: resumed session {session_id} (attempt {attempts})")
    else:
        session_id = args.session_id or "fake-0001"
        attempts = 1
        log(f"fakecli: new session {session_id}")

    save_session(cwd, {"session_id": session_id, "attempts": attempts,
                       "scenario": args.scenario})

    # -- the work order ----------------------------------------------------
    order = read_order(cwd)
    scope = write_scope_from_order(order)
    if order:
        first_line = order.splitlines()[0] if order.splitlines() else ""
        log(f"fakecli: read order ({first_line})")
    else:
        log("fakecli: no .pmwork/ORDER.md found")

    # Write inside the declared write scope, like a worker that respects
    # its order.  Exactly one file, so that the harness's scope check has
    # nothing to complain about.  Fall back to the worktree root when no
    # scope is declared.
    target_rel = scope[0] if scope else args.work_file

    # -- scenarios ---------------------------------------------------------
    if args.scenario in SYNTHETIC_FAILURES:
        log(SYNTHETIC_FAILURES[args.scenario])
        return EXIT_CODES[args.scenario]

    if args.scenario == "crash":
        log("fakecli: crashing without a recognised failure")
        os._exit(EXIT_CODES["crash"])

    if args.scenario == "hang":
        log("fakecli: hanging (stall test)")
        while True:
            time.sleep(1.0)

    if args.scenario == "slow":
        for index in range(3):
            log(f"fakecli: working ({index + 1}/3)")
            time.sleep(args.sleep or 1.0)

    if args.scenario == "oracle-fail-then-ok":
        marker = cwd / FIX_ROUND_FILE
        if not marker.exists():
            marker.write_text("attempt 1\n", encoding="utf-8")
            log("fakecli: first attempt — deliberately NOT writing "
                f"{target_rel}")
            log("fakecli: done (oracle will fail)")
            return 0
        log(f"fakecli: fix round — writing {target_rel}")

    # Write inside the declared write scope, like a worker that respects
    # its order.  Exactly one file, so that the harness's scope check has
    # nothing to complain about.
    target_path = cwd / target_rel
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(
            f"fakecli deterministic output\nsession={session_id}\n"
            f"attempts={attempts}\norder_bytes={len(order)}\n",
            encoding="utf-8")
    except OSError as exc:
        log(f"fakecli: cannot write: {exc}")
        return 73

    log(f"fakecli: wrote {target_rel}")
    log("fakecli: done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
