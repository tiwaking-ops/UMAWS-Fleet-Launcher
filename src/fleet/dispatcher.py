"""The Fleet Dispatcher (fleet amendment sections 7.3–7.10).

The Dispatcher does what the Overseer used to do by hand: it takes READY
tasks and puts agents on them.  It

* selects a profile for each task (section 7.4) and records the choice and
  the reason with ``FLEET_ASSIGNED``;
* starts leases through the harness, which owns the worktree, the order
  file and the oracles;
* supervises every slot from **one** poller loop, not a thread per slot
  (section 7.9);
* applies the recovery ladder when a worker fails (section 7.6);
* re-adopts workers that are still alive after an app restart (section
  7.10).

It never writes coordination state directly: it goes through
:class:`pmk.api.Kernel`.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from pmk.api import Kernel, KernelError
from pmk.plat import free_ram_mb

from . import order as order_mod
from . import recover
from . import select as select_mod
from . import spawn as spawn_mod
from .harness import Harness, LeaseResult, LeaseRun
from .profiles import Profile, load_profiles
from .state import FleetState


@dataclass
class DispatchReport:
    """What one dispatch tick did."""

    started: list = field(default_factory=list)
    finished: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"started": self.started, "finished": self.finished,
                "skipped": self.skipped, "notes": self.notes}


class Dispatcher:
    """Fills slots and supervises them."""

    def __init__(self, kernel: Kernel, fleet_state: FleetState | None = None,
                 *, policy: dict | None = None,
                 fixture_root: Path | None = None):
        self.kernel = kernel
        self.repo = kernel.repo
        self.policy = policy if policy is not None else kernel.policy()
        self.fleet_state = fleet_state or FleetState.load()
        self.harness = Harness(kernel, self.fleet_state, policy=self.policy,
                               fixture_root=fixture_root)
        self.runs: dict[str, LeaseRun] = {}     # task id -> in-flight lease
        self.failed_profiles: dict[str, set] = {}   # task id -> profile ids
        self._stop = threading.Event()

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    @property
    def fleet_config(self) -> dict:
        """The ``[fleet]`` section of ``agents.toml``."""
        from pmk.policy import load_agents
        return load_agents(self.repo)["fleet"]

    def profiles(self) -> list[Profile]:
        return load_profiles(self.repo)

    def max_total_agents(self) -> int:
        return int(self.fleet_config.get("max_total_agents", 20))

    def min_free_ram_mb(self) -> int:
        return int(self.fleet_config.get("min_free_ram_mb", 2048))

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    def status(self) -> dict:
        """``pmk fleet status``."""
        profiles = self.profiles()
        now = time.time()
        rows = []
        for profile in profiles:
            state = self.fleet_state.profile(profile.id)
            running = len([r for r in self.runs.values()
                           if r.profile.id == profile.id])
            rows.append({
                "id": profile.id,
                "adapter": profile.adapter,
                "family": profile.family,
                "state": ("disabled" if not state.enabled
                          else "cooling" if state.cooling(now) else "ready"),
                "running": running,
                "max_concurrent": profile.max_concurrent,
                "cooldown_remaining_s": state.cooling_remaining(now),
                "last_failure_class": state.last_failure_class,
                "runs": state.runs,
                "failures": state.failures,
                "priority": profile.priority,
            })
        return {
            "profiles": rows,
            "fleet_cap": self.max_total_agents(),
            "slots_in_use": len(self.runs),
            "dispatch_paused": self.fleet_state.dispatch_paused,
            "pause_reason": self.fleet_state.pause_reason,
            "free_ram_mb": free_ram_mb(),
            "min_free_ram_mb": self.min_free_ram_mb(),
        }

    def slots(self) -> list[dict]:
        """The live slot grid."""
        rows = []
        for task_id, run in sorted(self.runs.items()):
            rows.append({
                "task": task_id,
                "profile": run.profile.id,
                "adapter": run.profile.adapter,
                "pid": run.slot.pid,
                "runtime_s": int(time.time() - run.started_at),
                "last_output_age_s": _log_age(run.slot),
                "session": run.session,
                "degraded": run.slot.degraded,
                "log": run.slot.log_path,
                "worktree": str(run.worktree),
            })
        return rows

    # ------------------------------------------------------------------
    # One tick
    # ------------------------------------------------------------------
    def tick(self) -> DispatchReport:
        """One pass: poll the running slots, then fill the empty ones."""
        report = DispatchReport()

        # -- poll ------------------------------------------------------
        for task_id, run in list(self.runs.items()):
            try:
                result = self.harness.poll(run)
            except Exception as exc:                # noqa: BLE001
                report.notes.append(f"poll {task_id} failed: {exc}")
                continue
            if result is None:
                continue
            del self.runs[task_id]
            report.finished.append(result.to_dict())
            if result.outcome in ("recovery", "fix_round"):
                self._handle_recovery(run, result, report)

        # -- fill ------------------------------------------------------
        if not self.fleet_state.dispatch_paused:
            self._fill(report)
        else:
            report.notes.append(
                f"dispatch is paused: {self.fleet_state.pause_reason}")

        return report

    def _fill(self, report: DispatchReport) -> None:
        """Start leases for READY tasks."""
        state = self.kernel.state()
        ready = sorted(state.ready_tasks(),
                       key=lambda t: (t.priority, t.id))
        if not ready:
            return

        cap = self.max_total_agents()
        profiles = self.profiles()
        if not profiles:
            report.notes.append("no profiles are configured")
            return

        running_counts: dict[str, int] = {}
        for run in self.runs.values():
            running_counts[run.profile.id] = \
                running_counts.get(run.profile.id, 0) + 1

        for task in ready:
            if len(self.runs) >= cap:
                report.skipped.append({"task": task.id,
                                       "reason": f"fleet cap {cap} reached"})
                break

            free = free_ram_mb()
            minimum = self.min_free_ram_mb()
            if free is not None and minimum and free < minimum:
                report.skipped.append(
                    {"task": task.id,
                     "reason": f"free RAM {free} MB is below the "
                               f"{minimum} MB guard"})
                break

            excluded = self.failed_profiles.get(task.id, set())
            implementer_family = self._implementer_family(task, state)
            selection = select_mod.select_profile(
                task, profiles, self.fleet_state, running_counts,
                fleet_cap=cap, total_running=len(self.runs),
                implementer_family=implementer_family)

            # Exclude profiles that already failed this task.
            for candidate in selection.candidates:
                if candidate.profile.id in excluded:
                    candidate.eligible = False
                    candidate.reason = "already failed this task"
            eligible = [c for c in selection.candidates if c.eligible]
            if not eligible:
                report.skipped.append({"task": task.id,
                                       "reason": selection.reason})
                continue

            chosen = eligible[0].profile
            self.kernel.record_event(
                "FLEET_ASSIGNED", subject=task.id,
                payload={"profile": chosen.id,
                         "reason": selection.reason,
                         "candidates": [c.to_dict()
                                        for c in selection.candidates]})

            run, failure = self.harness.start(task, chosen)
            if run is None:
                report.skipped.append({"task": task.id,
                                       "reason": failure.error if failure
                                       else "start failed"})
                continue
            self.runs[task.id] = run
            running_counts[chosen.id] = running_counts.get(chosen.id, 0) + 1
            report.started.append({"task": task.id, "profile": chosen.id,
                                   "pid": run.slot.pid})

    def _implementer_family(self, task, state) -> str:
        """The family of the model that implemented the task.

        A verifier must not be from the author's family (D-L12).  When the
        implementer's family is unknown, no verification task can be
        dispatched at all — which is the honest answer, and it is why the
        decision is recorded rather than guessed.
        """
        lease = state.leases.get(task.id)
        if lease and lease.holder:
            for profile in self.profiles():
                if profile.id == lease.holder:
                    return profile.family
        return ""

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------
    def _handle_recovery(self, run: LeaseRun, result: LeaseResult,
                         report: DispatchReport) -> None:
        """Act on the recovery ladder's decision."""
        step = result.decision.get("step")
        if step == recover.L0:
            # Retry the same profile and session after a delay.
            delay = float(result.decision.get("delay_seconds", 30))
            report.notes.append(
                f"{run.task.id}: L0 retry on {run.profile.id} in {int(delay)}s")
            run.network_retries += 1
            self._restart_later(run, delay, report)
            return

        if step in (recover.L1, recover.L2):
            # Select the next profile (excluding the failed one) and either
            # resume the session on it or start a fresh session with a
            # handoff note.
            excluded = self.failed_profiles.setdefault(run.task.id, set())
            excluded.add(run.profile.id)
            next_profile = self._next_profile(run, excluded)
            if next_profile is None:
                report.notes.append(
                    f"{run.task.id}: no other profile qualifies; "
                    f"the task returns to READY")
                self._return_to_ready(run, result)
                return

            if step == recover.L2:
                handoff = order_mod.render_handoff(
                    failure_class=result.failure_class,
                    log_lines=spawn_mod.tail_log(run.slot, 40),
                    git_status=spawn_mod.worktree_status(self.repo,
                                                         run.worktree),
                    git_diff_stat=spawn_mod.worktree_diff_stat(
                        self.repo, run.worktree),
                    previous_profile=run.profile.id)
                order_mod.write_handoff(run.worktree, handoff)

            report.notes.append(
                f"{run.task.id}: {step} onto {next_profile.id}")
            # L1 resumes the session on the next profile; L2 starts a fresh
            # session with a handoff note.  The model's swap is only
            # possible when the profile lists interchangeable models.
            model = ""
            if step == recover.L1:
                model = next_profile.alternative_model(
                    exclude={run.profile.model} if run.profile.model else set())
                if model:
                    report.notes.append(
                        f"{run.task.id}: resuming on model {model}")
            self._restart_on(run, next_profile, report, model=model)
            return

        # L3 / L4: the harness already revoked the lease and quarantined the
        # worktree.  Remember the failed profile so the next attempt does
        # not pick it again.
        self.failed_profiles.setdefault(run.task.id, set()).add(run.profile.id)

    def _next_profile(self, run: LeaseRun, excluded: set) -> Profile | None:
        """The next profile for a recovery step."""
        state = self.kernel.state()
        task = run.task
        profiles = self.profiles()
        running_counts: dict[str, int] = {}
        for other in self.runs.values():
            running_counts[other.profile.id] = \
                running_counts.get(other.profile.id, 0) + 1
        selection = select_mod.select_profile(
            task, profiles, self.fleet_state, running_counts,
            fleet_cap=self.max_total_agents(), total_running=len(self.runs),
            implementer_family=self._implementer_family(task, state))
        for candidate in selection.candidates:
            if candidate.profile.id in excluded:
                continue
            if candidate.eligible:
                return candidate.profile
        return None

    def _restart_later(self, run: LeaseRun, delay: float,
                       report: DispatchReport) -> None:
        """Retry the same profile after a delay."""
        def later():
            time.sleep(delay)
            try:
                new_slot = spawn_mod.spawn_slot(
                    self.repo, task_id=run.task.id, profile_id=run.profile.id,
                    adapter=run.adapter,
                    profile=run.profile.raw or run.profile.to_dict(),
                    prompt=order_mod.FIXED_PROMPT, worktree=run.worktree,
                    fence=run.lease.fence, index=9,
                    env=self.harness._env(run.profile))
            except (OSError, ValueError):
                return
            run.slot = new_slot
            run.last_change = time.time()
            self.runs[run.task.id] = run

        threading.Thread(target=later, daemon=True,
                         name=f"pmk-retry-{run.task.id}").start()

    def _restart_on(self, run: LeaseRun, profile: Profile,
                    report: DispatchReport, model: str = "") -> None:
        """Start the lease again on another profile.

        When the profile has a known interchangeable model, the session is
        **resumed** on that model — the ladder's L1 step, and the one the
        operator's requirement FR3 asks for.  The model list is what makes
        it possible: it was measured (spike S-A1, live) and only **pi** has
        one today.
        """
        adapter = self.harness._adapter(profile)
        run.profile = profile
        run.adapter = adapter

        raw = dict(profile.raw or profile.to_dict())
        if model:
            raw["model"] = model
        resume = bool(profile.supports_resume() and run.session)
        mode = "resume" if resume else "new"
        try:
            new_slot = spawn_mod.spawn_slot(
                self.repo, task_id=run.task.id, profile_id=profile.id,
                adapter=adapter, profile=raw,
                prompt=order_mod.FIXED_PROMPT, worktree=run.worktree,
                fence=run.lease.fence, index=8,
                env=self.harness._env(profile),
                mode=mode, session=run.session or None)
        except (OSError, ValueError) as exc:
            report.notes.append(f"{run.task.id}: restart failed: {exc}")
            return
        run.slot = new_slot
        run.last_change = time.time()
        self.runs[run.task.id] = run
        self.kernel.record_event(
            "AGENT_RESUMED", subject=run.task.id, fence=run.lease.fence,
            payload={"profile": profile.id, "mode": mode,
                     "model": model or profile.model,
                     "previous_profile": run.lease.holder})

    def _return_to_ready(self, run: LeaseRun, result: LeaseResult) -> None:
        """Give the task back to the queue."""
        try:
            self.kernel.revoke(run.task.id, run.lease.fence,
                               reason="no profile qualified for recovery")
        except KernelError:
            pass

    # ------------------------------------------------------------------
    # Restart reconciliation (section 7.10)
    # ------------------------------------------------------------------
    def reconcile(self) -> dict:
        """Re-adopt the workers that are still alive after an app restart.

        For every lease whose recorded pid **and** creation time still match
        a live process, re-adopt it: monitor it, with no exit code
        available.  Otherwise treat the process as ended.

        Either way the normal completion step runs, so **the oracles
        decide** rather than process memory.  A second worker is never
        started in a worktree that has a live adopted process.
        """
        state = self.kernel.state()
        adopted, lost = [], []
        for task_id, lease in state.leases.items():
            if lease.pid is None:
                continue
            alive = spawn_mod.slot_alive(
                spawn_mod.Slot(task_id=task_id, profile_id=lease.holder,
                               adapter=lease.agent, argv=[], pid=lease.pid,
                               creation_time=lease.creation_time,
                               worktree=lease.worktree))
            task = state.tasks.get(task_id)
            profile = next((p for p in self.profiles()
                            if p.id == lease.holder), None)
            if alive and profile is not None and task is not None:
                adapter = self.harness._adapter(profile)
                slot = spawn_mod.Slot(task_id=task_id, profile_id=lease.holder,
                                      adapter=lease.agent, argv=[],
                                      pid=lease.pid,
                                      creation_time=lease.creation_time,
                                      log_path=str(
                                          spawn_mod.log_path(self.repo,
                                                             task_id,
                                                             lease.fence, 0)),
                                      worktree=lease.worktree)
                self.runs[task_id] = LeaseRun(task=task, profile=profile,
                                              lease=lease, adapter=adapter,
                                              slot=slot,
                                              worktree=Path(lease.worktree),
                                              started_at=time.time(),
                                              last_renew=time.time(),
                                              last_change=time.time())
                adopted.append(task_id)
            else:
                lost.append(task_id)

        self.kernel.record_event(
            "RECONCILED", payload={"adopted": adopted, "lost": lost})
        return {"adopted": adopted, "lost": lost}

    # ------------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------------
    def run_forever(self, stop_event: threading.Event | None = None,
                    max_seconds: float | None = None) -> None:
        """The dispatch loop.

        One loop supervises every slot.  It is event-driven in the sense
        that it sleeps on the tick interval rather than spinning, but it
        does not use one thread per slot.
        """
        tick = float(self.fleet_config.get("dispatch_tick_s", 5))
        deadline = None if max_seconds is None else time.time() + max_seconds
        while not self._stop.is_set():
            if stop_event is not None and stop_event.is_set():
                break
            if deadline is not None and time.time() > deadline:
                break
            try:
                self.tick()
            except Exception as exc:                # noqa: BLE001
                print(f"[dispatcher] tick failed: {exc}", flush=True)
            self._stop.wait(tick)

    def stop(self) -> None:
        self._stop.set()

    def kill_all(self) -> list[str]:
        """Kill every worker process tree the Dispatcher owns."""
        killed = []
        for task_id, run in list(self.runs.items()):
            ok, _ = spawn_mod.kill_slot(run.slot)
            if ok:
                killed.append(task_id)
        return killed


def _log_age(slot) -> float:
    """Seconds since the log last grew (0 if it has never grown)."""
    try:
        import os
        return max(0.0, time.time() - os.path.getmtime(slot.log_path))
    except OSError:
        return 0.0
