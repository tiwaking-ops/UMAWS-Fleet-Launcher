"""The Kernel-lite library API (pilot v1 section 9; fleet amendment D-L4).

**The Kernel is the only writer of coordination state.**  Everything else —
the CLI, the Fleet Dispatcher, the Console — calls this module.  Nothing
else appends to the event log.

Fleet amendment D-L4: the Dispatcher calls this API **in-process** rather
than spawning ``pmk`` subprocesses, because a hundred concurrent leases
would otherwise spawn a large number of short-lived Python processes per
minute on Windows.  The ``pmk`` CLI wraps exactly these functions and uses
the same file lock, so the two paths cannot diverge.

Locking: one exclusive lock (``<repo>/.pm/.kernel.lock``) guards every
mutation.  It is a **sidecar** lock file, not the event log itself — see
:mod:`pmk.plat` and decision D-04 for why that is mandatory on Windows.
"""

from __future__ import annotations

import contextlib
import os
import shutil
from pathlib import Path
from typing import Any, Iterable, Sequence

from . import policy as policy_mod
from .bundle import Bundle, CommandResult, OracleResult
from .clock import Clock, parse_iso, to_iso
from .events import Actor, Event, EventLog
from .models import (ACTIVE_STATES, BLOCKED, DONE, INTEGRATING, LEASED,
                      PROPOSED, READY, REWORK, SUBMITTED, VERIFYING, VOID,
                      Lease, TaskCard, next_task_id, scope_overlaps)
from .plat import FileLock, LockTimeout, atomic_write_text
from .state import State, rebuild


class KernelError(RuntimeError):
    """A refusal.  Carries a machine-readable reason (pilot v1 section 9.3)."""

    def __init__(self, reason: str, **details: Any):
        super().__init__(reason)
        self.reason = reason
        self.details = details

    def to_dict(self) -> dict:
        return {"error": self.reason, **self.details}


class Kernel:
    """The coordination authority for one repository."""

    def __init__(self, root: str | os.PathLike[str] | None = None,
                 clock: Clock | None = None):
        from .store import Repo  # local import keeps the module import-light
        self.repo = Repo.discover(root)
        self.clock = clock or Clock()
        self.log = EventLog(self.repo, self.clock)
        self._views_dirty = True
        self._last_view_render: float = 0.0

    # ------------------------------------------------------------------
    # Locking
    # ------------------------------------------------------------------
    @property
    def lock_path(self) -> Path:
        return self.repo.pm / ".kernel.lock"

    @contextlib.contextmanager
    def _locked(self, timeout: float = 30.0):
        """Hold the Kernel lock for the duration of the block."""
        self.repo.pm.mkdir(parents=True, exist_ok=True)
        lock = FileLock(self.lock_path, timeout=timeout)
        lock.acquire()
        try:
            yield
        finally:
            lock.release()

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------
    def events(self) -> list[Event]:
        events, _ = self.log.read_all(repair=True)
        return events

    def state(self) -> State:
        """Rebuild the whole state from the log."""
        return rebuild(self.events())

    def policy(self) -> dict:
        return policy_mod.load_policy(self.repo)

    def policy_hash(self) -> str:
        return policy_mod.policy_hash(self.policy())

    def stopped(self) -> bool:
        """Is the operator's stop-the-line flag set? (pilot v1 section 12.5)"""
        return self.repo.stop_file.exists()

    def _check_not_stopped(self) -> None:
        if self.stopped():
            raise KernelError("stopped", detail="pilot/STOP is present")

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------
    def _append(self, event_type: str, *, actor: Actor | None = None,
                subject: str | None = None, fence: int | None = None,
                payload: dict | None = None) -> Event:
        """Append an event.  The caller must hold the lock."""
        self._check_not_stopped()
        event = self.log.append(
            event_type,
            actor=actor,
            subject=subject,
            fence=fence,
            payload=payload or {},
            policy_hash=self.policy_hash(),
        )
        self._views_dirty = True
        return event

    def record_event(self, event_type: str, *, actor: Actor | None = None,
                     subject: str | None = None, fence: int | None = None,
                     payload: dict | None = None) -> Event:
        """Append an event and return it.

        The public entry point for components that are part of the app but
        are not the CLI — the Fleet Dispatcher and the Overseer runner use
        this (fleet amendment D-L4).  The caller must hold the lock; the
        Kernel's own mutating commands call :meth:`_append` inside it.
        """
        return self._append(event_type, actor=actor, subject=subject,
                            fence=fence, payload=payload)

    def _next_fence(self, events: Sequence[Event] | None = None) -> int:
        events = list(events if events is not None else self.events())
        highest = 0
        for event in events:
            if event.fence and event.fence > highest:
                highest = event.fence
            fence = (event.payload or {}).get("fence")
            if isinstance(fence, int) and fence > highest:
                highest = fence
        return highest + 1

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def init(self) -> dict:
        """Create the layout, the first event, and the pins."""
        with self._locked():
            self.repo.ensure_layout()
            events, _ = self.log.read_all(repair=True)
            if not events:
                self._append("BOOTSTRAP_IMPORTED", actor=Actor.kernel(),
                             payload={"note": "repository initialised",
                                      "kernel_version": self.log.kernel_version})
            if not Path(self.repo.pins_path).is_file():
                policy_mod.write_pins(self.repo)
            self._render_views(force=True)
        return {"ok": True, "root": str(self.repo.root),
                "events": len(self.events())}

    def status(self) -> dict:
        state = self.state()
        counts = state.counts()
        return {
            "root": str(self.repo.root),
            "project_state": state.project_state,
            "tasks": counts,
            "task_total": len(state.tasks),
            "active_leases": len(state.active_leases()),
            "open_queue_items": len([q for q in state.queue if q["state"] == "open"]),
            "incidents": len(state.incidents),
            "stopped": self.stopped(),
            "chain": self.log.verify().summary(),
        }

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------
    def task_create(self, title: str, *, type: str = "implement",
                    goal_ref: str = "", scope: dict | None = None,
                    oracles: Sequence[str] = (), evidence_required: Sequence[str] = (),
                    premises: Sequence[dict] = (), budget: dict | None = None,
                    depends_on: Sequence[str] = (), attempts_max: int = 3,
                    priority: int = 100, agent_hint: str = "",
                    actor: Actor | None = None,
                    admitted: bool = True) -> TaskCard:
        """Create a task card.

        The Kernel allocates the id.  A card is created in PROPOSED and
        becomes READY only if it passes admission (goal_ref, scope, oracle,
        budget).  A card that fails admission is still recorded — the
        Overseer can see why it was refused.
        """
        with self._locked():
            state = self.state()
            card = TaskCard(
                id=next_task_id(state.tasks.keys()),
                title=title,
                type=type,
                goal_ref=goal_ref,
                scope=scope or {"write": [], "read": []},
                acceptance={"oracles": list(oracles),
                            "evidence_required": list(evidence_required)},
                premises=list(premises),
                budget=budget or {"tokens": 0, "wall_min": 0},
                depends_on=list(depends_on),
                attempts={"max": attempts_max},
                priority=priority,
                agent_hint=agent_hint,
                created_by=(actor or Actor(kind="overseer")).to_dict(),
            )
            problems = card.admission_errors()
            self._append("TASK_CREATED", actor=actor, subject=card.id,
                         payload={"card": card.to_obj(),
                                  "admission_errors": problems})
            if admitted and not problems:
                self._append("TASK_ADMITTED", actor=actor, subject=card.id,
                             payload={})
                card.state = READY
            else:
                card.state = PROPOSED
            return card

    def task_admit(self, task_id: str, *, actor: Actor | None = None) -> TaskCard:
        with self._locked():
            state = self.state()
            card = state.tasks.get(task_id)
            if card is None:
                raise KernelError("unknown_task", task=task_id)
            problems = card.admission_errors()
            if problems:
                raise KernelError("admission_failed", task=task_id,
                                  problems=problems)
            if card.state != PROPOSED:
                raise KernelError("bad_transition", task=task_id,
                                  current=card.state, target=READY)
            self._append("TASK_ADMITTED", actor=actor, subject=task_id, payload={})
            return card

    def task_list(self, state: str | None = None) -> list[TaskCard]:
        return self.state().task_list(state)

    def task_show(self, task_id: str) -> dict:
        state = self.state()
        card = state.tasks.get(task_id)
        if card is None:
            raise KernelError("unknown_task", task=task_id)
        return {
            "task": card.to_obj(),
            "lease": (state.leases[task_id].to_obj()
                      if task_id in state.leases else None),
            "events": [e.to_obj() for e in self.events() if e.subject == task_id],
        }

    def task_block(self, task_id: str, reason: str, *,
                   actor: Actor | None = None) -> None:
        with self._locked():
            if task_id not in self.state().tasks:
                raise KernelError("unknown_task", task=task_id)
            self._append("TASK_BLOCKED", actor=actor, subject=task_id,
                         payload={"reason": reason})

    def task_ready(self, task_id: str, *, actor: Actor | None = None) -> None:
        with self._locked():
            if task_id not in self.state().tasks:
                raise KernelError("unknown_task", task=task_id)
            self._append("TASK_READY", actor=actor, subject=task_id, payload={})

    # ------------------------------------------------------------------
    # Leases
    # ------------------------------------------------------------------
    def _current_fence(self, state: State, task_id: str) -> int:
        """The fence token a submission for *task_id* must carry.

        Invariant I4 is "a stale fence is never merged", and a stale
        submission is exactly the case where the lease was **revoked**
        before the worker finished.  A revoked lease is no longer in
        ``state.leases``, so comparing against the live lease alone would
        report "no lease" instead of "stale fence" — and the late work
        would be neither quarantined nor promoted, which is the wrong
        answer twice over.  The task's own fence is the authority: it is
        bumped on revocation, so a submission carrying the old fence is
        detected as stale.
        """
        lease = state.leases.get(task_id)
        if lease is not None:
            return lease.fence
        card = state.tasks.get(task_id)
        return card.fence if card is not None else 0

    def _scope_conflict(self, card: TaskCard, state: State) -> list[dict]:
        """Write-scope conflicts with tasks that already hold a lease.

        Fleet amendment D-L6: many parallel agents on one repository produce
        merge conflicts by construction unless overlapping write scopes are
        refused at claim time.
        """
        conflicts = []
        for other in state.task_list():
            if other.id == card.id:
                continue
            if other.state not in ACTIVE_STATES:
                continue
            hits = scope_overlaps(card.write_scope, other.write_scope)
            for left, right in hits:
                conflicts.append({"task": other.id, "state": other.state,
                                  "this": left, "other": right})
        return conflicts

    def claim(self, task_id: str, *, holder: str, agent: str = "",
              role: str = "", session: str = "", worktree: str = "",
              pid: int | None = None, creation_time: int | None = None,
              actor: Actor | None = None,
              allow_scope_conflict: bool = False) -> Lease:
        """Claim a task for a lease, with a fencing token.

        Refuses when: the task is not READY, its dependencies are not done,
        its write scope overlaps a task that already holds a lease (D-L6),
        or its attempts are exhausted.
        """
        with self._locked():
            state = self.state()
            card = state.tasks.get(task_id)
            if card is None:
                raise KernelError("unknown_task", task=task_id)
            if card.attempt >= int(card.attempts.get("max", 3)):
                raise KernelError("attempts_exhausted", task=task_id,
                                  attempt=card.attempt,
                                  max_attempts=card.attempts.get("max"))
            if card.state != READY:
                raise KernelError("not_ready", task=task_id, current=card.state)
            unmet = [d for d in card.depends_on
                     if d in state.tasks and state.tasks[d].state != DONE]
            if unmet:
                raise KernelError("dependencies_unmet", task=task_id,
                                  unmet=unmet)
            if not allow_scope_conflict:
                conflicts = self._scope_conflict(card, state)
                if conflicts:
                    raise KernelError("scope_overlap", task=task_id,
                                      conflicts=conflicts)

            fence = self._next_fence()
            attempt = card.attempt + 1
            now = self.clock.now_iso()
            lease = Lease(
                task_id=task_id, fence=fence, holder=holder, agent=agent,
                role=role, session=session, granted_at=now, renewed_at=now,
                pid=pid, creation_time=creation_time, worktree=worktree,
                attempt=attempt,
            )
            self._append("CLAIMED", actor=actor, subject=task_id, fence=fence,
                         payload={"lease": lease.to_obj(), "fence": fence,
                                  "attempt": attempt,
                                  "base_commit": self._head_commit()})
            return lease

    def renew(self, task_id: str, fence: int, *, digest: str = "",
              actor: Actor | None = None) -> Lease:
        """Renew a lease.  A stale fence cannot renew."""
        with self._locked():
            state = self.state()
            lease = state.leases.get(task_id)
            if lease is None and task_id not in state.tasks:
                raise KernelError("unknown_task", task=task_id)
            current = self._current_fence(state, task_id)
            if fence != current:
                raise KernelError("stale_fence", task=task_id, fence=fence,
                                  current=current)
            if lease is None:
                raise KernelError("no_lease", task=task_id)
            ttl = self.policy().get("lease", {}).get("ttl_minutes", 20)
            expires = to_iso(self.clock.now().replace(microsecond=0))
            try:
                expires = to_iso(parse_iso(expires) +
                                 __import__("datetime").timedelta(minutes=int(ttl)))
            except (ValueError, TypeError):
                pass
            self._append("RENEWED", actor=actor, subject=task_id, fence=fence,
                         payload={"ts": self.clock.now_iso(),
                                  "expires_at": expires,
                                  "digest": digest})
            updated = state.leases[task_id]
            updated.renewed_at = self.clock.now_iso()
            updated.expires_at = expires
            return updated

    def revoke(self, task_id: str, fence: int, *, reason: str = "",
               actor: Actor | None = None) -> int:
        """Revoke a lease.  The fence is bumped, so late work is stale.

        Returns the new fence.
        """
        with self._locked():
            state = self.state()
            lease = state.leases.get(task_id)
            if lease is None:
                raise KernelError("no_lease", task=task_id)
            if lease.fence != fence:
                raise KernelError("stale_fence", task=task_id, fence=fence,
                                  current=lease.fence)
            new_fence = self._next_fence()
            self._append("REVOKED", actor=actor, subject=task_id, fence=fence,
                         payload={"reason": reason, "new_fence": new_fence})
            return new_fence

    def submit(self, task_id: str, fence: int, bundle: Bundle | dict, *,
               actor: Actor | None = None) -> dict:
        """Submit work with an evidence bundle.

        A submission with a **stale fence is quarantined, never merged**
        (invariant I4).  A bundle that fails validation is refused.
        """
        if isinstance(bundle, dict):
            bundle = Bundle.from_obj(bundle)
        with self._locked():
            state = self.state()
            card = state.tasks.get(task_id)
            if card is None:
                raise KernelError("unknown_task", task=task_id)
            current = self._current_fence(state, task_id)
            if fence != current:
                # I4: stale fence never merges.  Quarantine it.
                path = self._quarantine(task_id, fence,
                                        f"stale fence {fence} != {current}")
                self._append("QUARANTINED", actor=actor, subject=task_id,
                             fence=fence,
                             payload={"class": "STALE_FENCE", "reason":
                                      "stale fence", "path": str(path)})
                raise KernelError("stale_fence", task=task_id, fence=fence,
                                  current=current, quarantined=str(path))
            lease = state.leases.get(task_id)
            if lease is None:
                raise KernelError("no_lease", task=task_id)
            problems = bundle.validation_errors()
            if problems:
                raise KernelError("invalid_bundle", task=task_id, problems=problems)
            bundle.task = task_id
            bundle.fence = fence
            path = bundle.write(self.repo.evidence_dir)
            self._append("SUBMITTED", actor=actor, subject=task_id, fence=fence,
                         payload={"bundle": f"EB-{task_id}-{fence}",
                                  "bundle_path": str(path),
                                  "pid": lease.pid, "session": lease.session,
                                  "all_oracles_passed":
                                      bundle.all_oracles_passed()})
            return {"ok": True, "bundle": f"EB-{task_id}-{fence}",
                    "path": str(path)}

    def verify(self, task_id: str, fence: int, *, ok: bool,
               reasons: Sequence[str] = (), actor: Actor | None = None) -> dict:
        """Record the outcome of verification (V0/V1).

        The Kernel runs the oracles, so this records a result it computed
        rather than accepting one on trust.
        """
        with self._locked():
            state = self.state()
            current = self._current_fence(state, task_id)
            if fence != current:
                raise KernelError("stale_fence", task=task_id, fence=fence,
                                  current=current)
            self._append("VERIFIED", actor=actor, subject=task_id, fence=fence,
                         payload={"ok": ok, "reasons": list(reasons),
                                  "class": "" if ok else "ORACLE_FAILED"})
            return {"ok": ok, "reasons": list(reasons)}

    def integrate(self, task_id: str, fence: int, *, commit: str = "",
                  actor: Actor | None = None) -> dict:
        """Promote a verified task to DONE (invariant I5)."""
        with self._locked():
            state = self.state()
            card = state.tasks.get(task_id)
            lease = state.leases.get(task_id)
            if card is None:
                raise KernelError("unknown_task", task=task_id)
            current = self._current_fence(state, task_id)
            if fence != current:
                raise KernelError("stale_fence", task=task_id, fence=fence,
                                  current=current)
            if card.state not in (SUBMITTED, VERIFYING, INTEGRATING):
                raise KernelError("bad_transition", task=task_id,
                                  current=card.state, target=DONE)
            self._append("INTEGRATING", actor=actor, subject=task_id, fence=fence,
                         payload={"commit": commit})
            self._append("INTEGRATED", actor=actor, subject=task_id, fence=fence,
                         payload={"commit": commit, "bundle":
                                  f"EB-{task_id}-{fence}"})
            return {"ok": True, "task": task_id, "state": DONE}

    def premise_refuted(self, task_id: str, fence: int, *, reason: str,
                        evidence: str = "", actor: Actor | None = None) -> dict:
        """A worker reports a false premise.  The task is voided, not forced."""
        with self._locked():
            self._append("PREMISE_REFUTED", actor=actor, subject=task_id,
                         fence=fence, payload={"reason": reason,
                                               "evidence": evidence})
            return {"ok": True, "task": task_id, "state": VOID}

    def quarantine(self, task_id: str, fence: int, *, reason: str,
                   failure_class: str = "", actor: Actor | None = None) -> str:
        with self._locked():
            path = self._quarantine(task_id, fence, reason)
            self._append("QUARANTINED", actor=actor, subject=task_id, fence=fence,
                         payload={"class": failure_class, "reason": reason,
                                  "path": str(path)})
            return str(path)

    def _quarantine(self, task_id: str, fence: int, reason: str) -> Path:
        target = self.repo.quarantine_dir / f"{task_id}-{fence}"
        target.mkdir(parents=True, exist_ok=True)
        (target / "reason.txt").write_text(reason + "\n", encoding="utf-8")
        return target

    # ------------------------------------------------------------------
    # Queue and incidents
    # ------------------------------------------------------------------
    def queue_add(self, *, topic: str, options: Sequence[str],
                  recommended: str = "", safe_default: str = "",
                  class_k: bool = False, details: str = "",
                  actor: Actor | None = None) -> str:
        """Put a question to the human (pilot v1 section 23.2 fields)."""
        with self._locked():
            items = [q for q in self.state().queue if q["state"] == "open"]
            item_id = f"Q-{len(items) + 1:03d}"
            self._append("QUEUE_ITEM", actor=actor, subject=item_id,
                         payload={"id": item_id, "topic": topic,
                                  "options": list(options),
                                  "recommended": recommended,
                                  "safe_default": safe_default,
                                  "class_k": class_k, "details": details})
            return item_id

    def queue_list(self) -> list[dict]:
        return self.state().queue

    def queue_decide(self, item_id: str, choice: str, *,
                     actor: Actor | None = None) -> dict:
        with self._locked():
            open_items = [q for q in self.state().queue
                          if q["state"] == "open" and q["id"] == item_id]
            if not open_items:
                raise KernelError("unknown_queue_item", item=item_id)
            self._append("QUEUE_DECIDED", actor=actor, subject=item_id,
                         payload={"id": item_id, "choice": choice})
            return {"ok": True, "item": item_id, "choice": choice}

    def incident(self, subject: str, message: str, *, severity: str = "warn",
                 actor: Actor | None = None) -> dict:
        with self._locked():
            self._append("INCIDENT", actor=actor, subject=subject,
                         payload={"message": message, "severity": severity})
            return {"ok": True, "subject": subject}

    # ------------------------------------------------------------------
    # Project lifecycle (fleet amendment section 10)
    # ------------------------------------------------------------------
    def project_set_state(self, new_state: str, *, reason: str = "",
                          actor: Actor | None = None) -> dict:
        with self._locked():
            self._append("PROJECT_STATE", actor=actor,
                         payload={"state": new_state, "reason": reason})
            return {"ok": True, "state": new_state}

    def project_state(self) -> str:
        return self.state().project_state

    # ------------------------------------------------------------------
    # Pins, views, sentinel, briefing
    # ------------------------------------------------------------------
    def pins_check(self) -> dict:
        result = policy_mod.check_pins(self.repo)
        with self._locked():
            self._append("PINS_CHECKED", actor=Actor.kernel(),
                         payload=result)
        return result

    def render_views(self, *, force: bool = False) -> dict:
        """Regenerate the views, debounced (fleet amendment D-L5).

        Rewriting ``ledger.md`` on every heartbeat does not scale to a
        hundred workers, so views are regenerated at most every
        ``context.views_debounce_s`` seconds.  The sentinel always forces a
        regeneration first, so I13 still holds when it matters.
        """
        from . import views as views_mod
        debounce = float(self.policy().get("context", {})
                         .get("views_debounce_s", 5))
        now = self.clock.monotonic()
        if not force and not self._views_dirty:
            return {"skipped": True, "reason": "not dirty"}
        if not force and (now - self._last_view_render) < debounce:
            return {"skipped": True, "reason": "debounced"}
        with self._locked():
            self._render_views(force=True)
        return {"skipped": False, "rendered": True}

    def _render_views(self, *, force: bool = False) -> dict:
        from . import views as views_mod
        state = self.state()
        rendered = views_mod.render(self.repo, state, self.policy())
        self._views_dirty = False
        self._last_view_render = self.clock.monotonic()
        return rendered

    def sentinel(self) -> dict:
        """Check the pilot invariants (pilot v1 section 9.6)."""
        from . import sentinel as sentinel_mod
        # D-L5: views are always current when the sentinel runs.
        with self._locked():
            self._render_views(force=True)
        report = sentinel_mod.check(self)
        with self._locked():
            self._append("SENTINEL_RUN", actor=Actor.kernel(),
                         payload={"ok": report["ok"],
                                  "findings": report["findings"],
                                  "checked": report["checked"]})
        return report

    def brief(self, role: str = "overseer", *, actor: Actor | None = None) -> str:
        """Produce a briefing from the log alone (hypothesis H6)."""
        from . import briefing as briefing_mod
        return briefing_mod.render(self, role=role)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _head_commit(self) -> str:
        """The current HEAD commit, or ``""`` outside a git repository."""
        return self.repo.head_commit()

    def git(self, *args: str, cwd: Path | None = None,
            timeout: int = 60) -> tuple[int, str, str]:
        """Run a git command in the repository."""
        return self.repo.git(*args, cwd=cwd, timeout=timeout)
