"""The sentinel — invariant checks (pilot v1 section 9.6).

Sentinel-triggered stop is limited to **I1, I3, I6 and I8'**.  The other
invariants (I4, I5, I7, I13, I14, I15, I16) are reported as findings but do
not stop the pilot.  I5 is a report-only finding: a failing-oracle promotion
is visible but does not halt the pilot, per the pinned policy.toml stop_on
list.

| Invariant | Statement |
|---|---|
| I1 | the hash chain verifies |
| I3 | every task is in exactly one state (conservation) |
| I4 | a stale fence is never merged |
| I5 | nothing is promoted without a promotion event and a passing bundle |
| I6 | every DONE task has a matching bundle |
| I7 | only Kernel timestamps are trusted |
| I8' | pinned files match ``pins.sha256`` |
| I13 | the views equal the projection |
| I14 | silence is recorded |
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .bundle import Bundle
from .clock import parse_iso
from .models import DONE
from .policy import check_pins
from .views import render_ledger, render_queue, render_status

#: Invariants whose breach stops the pilot.
STOP_INVARIANTS = ("I1", "I3", "I6", "I8'")


@dataclass
class Finding:
    invariant: str
    detail: str
    stops: bool = False
    subject: str = ""

    def to_dict(self) -> dict:
        return {"invariant": self.invariant, "detail": self.detail,
                "stops": self.stops, "subject": self.subject}


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(f.stops for f in self.findings)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "checked": self.checked,
            "findings": [f.to_dict() for f in self.findings],
        }


def check(kernel) -> dict:
    """Run every pilot invariant against the current state."""
    report = Report()
    state = kernel.state()
    events = kernel.events()

    # -- I1: the chain verifies -------------------------------------------
    report.checked.append("I1")
    chain = kernel.log.verify()
    if not chain.ok:
        report.findings.append(Finding(
            "I1", chain.summary(), stops=True,
            subject=str(chain.first_break_seq or "")))
    for repair in chain.repairs:
        report.findings.append(Finding("I1", f"tail repaired: {repair}"))

    # -- I3: conservation -------------------------------------------------
    report.checked.append("I3")
    ok, detail = state.conservation_ok()
    if not ok:
        report.findings.append(Finding("I3", detail, stops=True))

    # -- I4: a stale fence is never merged --------------------------------
    # In-order replay: track each task's *current* fence as CLAIMED events
    # set it and REVOKED events advance it (via the new_fence payload).
    # An INTEGRATED with a fence that is not the current one at that moment
    # means a stale fence was merged.
    report.checked.append("I4")
    current_fences: dict[str, int] = {}
    for event in events:
        if event.subject is None:
            continue
        task_id = event.subject
        if event.type == "CLAIMED":
            f = event.fence
            if f is not None:
                current_fences[task_id] = int(f)
        elif event.type == "REVOKED":
            payload = event.payload or {}
            new_fence = payload.get("new_fence")
            if new_fence is not None:
                current_fences[task_id] = int(new_fence)
        elif event.type == "INTEGRATED":
            f = event.fence
            if f is not None:
                current = current_fences.get(task_id)
                if current is not None and int(f) != current:
                    # This fence is stale at this moment in the log.
                    report.findings.append(Finding(
                        "I4", f"task {task_id} was integrated with stale "
                              f"fence {f} (current fence was {current})",
                        stops=False, subject=task_id))

    # -- I5 / I6: promotion requires a passing bundle ---------------------
    # I5 (report-only): a DONE task whose bundle has validation problems or
    # failing oracles.  The state machine should have refused the promotion,
    # so this finding is visible but does not halt the pilot.
    #
    # I6 (stops): every DONE task must have an INTEGRATED event with a
    # resolvable, readable bundle file.  Missing INTEGRATED, missing bundle
    # reference, missing file, or unreadable file are all I6 breaches
    # because a DONE task with no bundle is a structural impossibility.
    #
    # I5 applies only to tasks that are *currently* DONE, not to every
    # INTEGRATED event in the historical log.  A task that was promoted and
    # then revoked (like T-0003) is no longer DONE and should not trigger
    # I5.  I6 (every DONE task has a bundle) likewise checks the live state.
    report.checked.extend(["I5", "I6"])

    for task_id, task in state.tasks.items():
        if task.state != DONE:
            continue
        # Look up the bundle path recorded in the INTEGRATED event, not
        # task.fence (which may have advanced past the integration fence if
        # the task was re-leased after promotion).  The INTEGRATED event's
        # payload carries the exact bundle path used at promotion time.
        integrated = None
        for ev in reversed(events):
            if ev.type == "INTEGRATED" and ev.subject == task_id:
                integrated = ev
                break
        if integrated is None:
            # DONE without an INTEGRATED event — a structural breach of I6.
            report.findings.append(Finding(
                "I6", f"task {task_id} is DONE but has no INTEGRATED event",
                stops=True, subject=task_id))
            continue
        bundle_path_str = integrated.payload.get("bundle", "")
        if not bundle_path_str:
            # INTEGRATED present but no bundle reference — an I6 breach.
            report.findings.append(Finding(
                "I6", f"task {task_id} INTEGRATED event has no bundle reference",
                stops=True, subject=task_id))
            continue
        path = kernel.repo.evidence_dir / bundle_path_str / "bundle.json"
        if not path.is_file():
            report.findings.append(Finding(
                "I6", f"task {task_id} was promoted without a bundle at {path}",
                stops=True, subject=task_id))
            continue
        try:
            import json
            bundle = Bundle.from_obj(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            report.findings.append(Finding(
                "I6", f"task {task_id} has an unreadable bundle: {exc}",
                stops=True, subject=task_id))
            continue
        problems = bundle.validation_problems()
        if not bundle.all_oracles_passed():
            problems.append("one or more acceptance oracles failed")
        if problems:
            # Bundle exists but has validation problems or failing oracles —
            # the task was promoted against policy.  Report-only (I5).
            report.findings.append(Finding(
                "I5", f"task {task_id} was promoted with an invalid bundle: "
                      f"{'; '.join(problems)}", stops=False, subject=task_id))

    # -- I7: only Kernel timestamps are trusted ---------------------------
    report.checked.append("I7")
    previous = None
    for event in events:
        try:
            moment = parse_iso(event.ts)
        except (ValueError, TypeError):
            report.findings.append(Finding(
                "I7", f"event {event.seq} has an unparseable timestamp "
                      f"{event.ts!r}", subject=str(event.seq)))
            continue
        if previous is not None and moment < previous:
            report.findings.append(Finding(
                "I7", f"event {event.seq} goes backwards in Kernel time",
                subject=str(event.seq)))
        previous = moment

    # -- I8': pinned files match ------------------------------------------
    report.checked.append("I8'")
    pins = check_pins(kernel.repo)
    if not pins["ok"]:
        if pins.get("reason") == "pins file missing":
            # A missing pins file is a breach, not an absence of one.
            report.findings.append(Finding(
                "I8'", "the pins file is missing, so nothing is pinned",
                stops=True, subject=".pm/pins.sha256"))
        for mismatch in pins["mismatches"]:
            report.findings.append(Finding(
                "I8'", f"pinned file {mismatch['file']} does not match "
                       f"({mismatch.get('reason', 'hash differs')})",
                stops=True, subject=mismatch["file"]))

    # -- I13: the views equal the projection ------------------------------
    report.checked.append("I13")
    policy = kernel.policy()
    expected = {
        "ledger.md": render_ledger(state),
        "status.md": render_status(state, policy),
        "queue.md": render_queue(state),
    }
    for name, text in expected.items():
        path = kernel.repo.views_dir / name
        try:
            actual = path.read_text(encoding="utf-8")
        except OSError:
            report.findings.append(Finding(
                "I13", f"view {name} is missing", subject=name))
            continue
        if actual != text:
            report.findings.append(Finding(
                "I13", f"view {name} does not equal the projection",
                subject=name))

    # -- I14: silence is recorded -----------------------------------------
    report.checked.append("I14")
    for task in state.task_list():
        if task.state == "LEASED" and task.fence == 0:
            report.findings.append(Finding(
                "I14", f"task {task.id} is leased without a fence", subject=task.id))

    # -- I15: the context lint (CIP Part B section 14.6) -----------------
    report.checked.append("I15")
    managed = kernel.context_managed_paths()
    if managed:
        lint = kernel.context_lint()
        for finding in lint.get("findings", []):
            if finding.get("severity") != "reject":
                continue
            report.findings.append(Finding(
                "I15", f"{finding.get('file')}: {finding.get('detail')}",
                stops=False, subject=finding.get("file", "")))
        if lint.get("needs_review"):
            report.findings.append(Finding(
                "I15", "a managed context file has a URL on a domain that is "
                       "not allowlisted: it needs blind V2 review"))

    # -- I16: no out-of-band edit to a managed context file --------------
    report.checked.append("I16")
    recorded = kernel.context_recorded_hashes()
    if recorded:
        drift = kernel.context_drift()
        for change in drift.get("changed", []):
            report.findings.append(Finding(
                "I16", f"{change['file']} was edited out of band "
                       f"(recorded {change['recorded'][:12]}…, "
                       f"now {change['current'][:12]}…)",
                stops=False, subject=change["file"]))
        for path in drift.get("removed", []):
            report.findings.append(Finding(
                "I16", f"{path} was deleted out of band", stops=False,
                subject=path))

    return report.to_dict()
