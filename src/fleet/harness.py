"""The harness: one lease, from claim to submission (fleet amendment 7.3).

The per-lease flow:

1. **claim** (in-process) with the selected profile; create the worktree.
2. Write ``ORDER.md``; spawn the CLI.
3. Poll: process state, log growth, worktree change, wall time.  Renew the
   lease on the heartbeat cadence with a progress digest.
4. On process end (any exit code) **classify the outcome**:

   * **OK or unknown-success** — the harness runs the acceptance commands
     itself, records exit codes and output hashes, builds the bundle and
     calls ``submit``.
   * **Oracles fail** — a **fix round**: resume the same session with the
     failing output as feedback, up to ``fix_rounds``, then submit as
     failed or release.
   * **A failure class** — enter the recovery ladder.

5. Quarantine and keep the worktree on any give-up.

**Oracles decide.**  A process exit code, a CLI's own claim of success, or a
worker's ``RESULT.md`` is never evidence on its own (fleet rule 18).  The
harness runs the commands and records what happened.

The harness is **two-phase** — :meth:`Harness.start` and
:meth:`Harness.poll` — because the Fleet supervises every slot from one
poller loop rather than a thread per slot (fleet amendment section 7.9).
:meth:`Harness.run` is the convenience loop used by tests and by a
single-shot launch.
"""

from __future__ import annotations

import hashlib
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from pmk.api import Kernel, KernelError
from pmk.bundle import Bundle, CommandResult, OracleResult
from pmk.models import Lease

from . import classify as classes
from . import order as order_mod
from . import recover
from . import spawn as spawn_mod
from . import provenance as provenance_mod
from .profiles import Profile
from .state import FleetState


@dataclass
class LeaseResult:
    """What happened to one lease."""

    task_id: str
    profile_id: str
    outcome: str = ""            # submitted | fix_round | recovery | blocked | failed
    failure_class: str = ""
    decision: dict = field(default_factory=dict)
    bundle: dict | None = None
    oracles: list = field(default_factory=list)
    error: str = ""
    exit_code: int | None = None
    session: str = ""
    worktree: str = ""
    fix_rounds: int = 0

    def to_dict(self) -> dict:
        return {
            "task": self.task_id,
            "profile": self.profile_id,
            "outcome": self.outcome,
            "failure_class": self.failure_class,
            "decision": self.decision,
            "oracles": self.oracles,
            "error": self.error,
            "exit_code": self.exit_code,
            "session": self.session,
            "worktree": self.worktree,
            "fix_rounds": self.fix_rounds,
        }


@dataclass
class LeaseRun:
    """A lease in flight."""

    task: object
    profile: Profile
    lease: Lease
    adapter: object
    slot: object
    worktree: Path
    session: str = ""
    started_at: float = 0.0
    last_renew: float = 0.0
    fix_rounds: int = 0
    last_size: int = -1
    last_status: str = ""
    last_change: float = 0.0
    network_retries: int = 0
    unknown_retries: int = 0

    def to_dict(self) -> dict:
        return {"task": self.task.id, "profile": self.profile.id,
                "fence": self.lease.fence, "pid": self.slot.pid,
                "worktree": str(self.worktree),
                "session": self.session,
                "fix_rounds": self.fix_rounds}


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def run_command(command: str, cwd: str | Path, *,
                timeout: int = 600) -> tuple[int, str, str]:
    """Run one acceptance command in the worktree.

    The harness runs the command, not the worker.  A command that the
    worker claims to have run is not evidence (constitution point 3).
    """
    try:
        proc = subprocess.run(
            command, shell=True, cwd=str(cwd), capture_output=True,
            timeout=timeout, text=True, encoding="utf-8", errors="replace")
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except OSError as exc:
        return 127, "", str(exc)


def run_oracles(task, worktree: str | Path, *,
                timeout: int = 600) -> list[OracleResult]:
    """Run the task's acceptance oracles and record the results."""
    results: list[OracleResult] = []
    for oracle in task.oracles:
        exit_code, stdout, stderr = run_command(oracle, worktree, timeout=timeout)
        results.append(OracleResult(
            cmd=oracle, exit=exit_code, ok=(exit_code == 0),
            stdout_hash=_hash_text(stdout), stderr_hash=_hash_text(stderr)))
    return results


def scope_check(task, worktree: str | Path, repo) -> dict:
    """Compare the worktree's changes with the declared write scope."""
    from pmk.models import scope_overlaps

    detail = spawn_mod.worktree_status_detail(repo, worktree)
    status = detail["out"] if detail["code"] == 0 else ""

    changed = []
    for line in status.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip() if len(line) > 3 else line.strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        changed.append(path)

    write_scope = task.write_scope
    violations = []
    for path in changed:
        if path.startswith(".pmwork/") or path.startswith(".fakecli"):
            continue
        if not scope_overlaps([path], write_scope):
            violations.append({"path": path, "reason": "outside the write scope"})
    return {"changed": changed, "violations": violations,
            "ok": not violations,
            "git_code": detail["code"], "git_err": detail["err"][:400]}


class Harness:
    """Starts and supervises leases."""

    def __init__(self, kernel: Kernel, fleet_state: FleetState, *,
                 policy: dict | None = None, fixture_root: Path | None = None):
        self.kernel = kernel
        self.repo = kernel.repo
        self.fleet_state = fleet_state
        self.policy = policy if policy is not None else kernel.policy()
        self.fixture_root = fixture_root

    # ------------------------------------------------------------------
    def _constitution(self) -> str:
        try:
            return self.repo.constitution_path.read_text(encoding="utf-8")
        except OSError:
            return ""

    def _adapter(self, profile: Profile):
        from .adapters import get_adapter
        return get_adapter(profile.adapter, self.fixture_root)

    def _env(self, profile: Profile) -> dict | None:
        """The environment for the worker.

        Fleet amendment D-L3: scrubbing applies **only** to profiles with
        ``via_gateway = true``.  Direct-CLI profiles keep their own
        credentials in their own configuration — the Kernel cannot scrub
        what it does not own, and pretending otherwise would be a lie
        (known limitation L-F4).
        """
        if not profile.via_gateway:
            return None
        from pmk.plat import scrub_environment
        keep = ["PATH", "SystemRoot", "TEMP", "TMP", "HOMEDRIVE", "HOMEPATH",
                "USERPROFILE", "APPDATA", "LOCALAPPDATA", "COMSPEC",
                "PATHEXT", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE"]
        return scrub_environment(keep=keep)

    # ------------------------------------------------------------------
    # Phase 1: start
    # ------------------------------------------------------------------
    def start(self, task, profile: Profile) -> tuple[LeaseRun | None, LeaseResult | None]:
        """Claim the task, make the worktree, write the order, spawn the CLI."""
        result = LeaseResult(task_id=task.id, profile_id=profile.id)
        adapter = self._adapter(profile)

        try:
            lease = self.kernel.claim(task.id, holder=profile.id,
                                      agent=profile.adapter, role=task.type)
        except KernelError as exc:
            result.outcome = "failed"
            result.error = exc.reason
            return None, result

        try:
            worktree = spawn_mod.create_worktree(self.repo, task.id, lease.fence)
        except (RuntimeError, OSError) as exc:
            result.outcome = "failed"
            result.error = f"worktree: {exc}"
            self._give_up(lease, result, "worktree failed")
            return None, result
        lease.worktree = str(worktree)

        order_text = order_mod.render_order(
            task, lease, constitution=self._constitution(),
            attempt=lease.attempt, fence=lease.fence)
        order_mod.write_order(worktree, order_text)

        try:
            slot = spawn_mod.spawn_slot(
                self.repo, task_id=task.id, profile_id=profile.id,
                adapter=adapter, profile=profile.raw or profile.to_dict(),
                prompt=order_mod.FIXED_PROMPT, worktree=worktree,
                fence=lease.fence, index=0, env=self._env(profile))
        except (OSError, ValueError) as exc:
            result.outcome = "failed"
            result.error = f"spawn: {exc}"
            self._give_up(lease, result, "spawn failed")
            return None, result

        state = self.fleet_state.profile(profile.id)
        state.last_used = time.time()
        self.fleet_state.save()

        now = time.time()
        self.kernel.record_event(
            "AGENT_STARTED", subject=task.id, fence=lease.fence,
            payload={"profile": profile.id, "adapter": profile.adapter,
                     "pid": slot.pid, "creation_time": slot.creation_time,
                     "worktree": str(worktree), "log": slot.log_path,
                     "degraded": slot.degraded})

        run = LeaseRun(task=task, profile=profile, lease=lease, adapter=adapter,
                       slot=slot, worktree=worktree, started_at=now,
                       last_renew=now, last_change=now)
        return run, None

    # ------------------------------------------------------------------
    # Phase 2: poll
    # ------------------------------------------------------------------
    def poll(self, run: LeaseRun) -> LeaseResult | None:
        """Check a running lease.  Returns ``None`` while it is still going."""
        policy = self.policy
        renew_every = float(policy.get("lease", {}).get("renew_every", 60))
        stall_minutes = float(policy.get("fleet", {}).get("stall_minutes", 15))

        now = time.time()
        size = spawn_mod.log_growth(run.slot)
        status = spawn_mod.worktree_status(self.repo, run.worktree)
        if size != run.last_size or status != run.last_status:
            run.last_size = size
            run.last_status = status
            run.last_change = now

        if (now - run.last_renew) >= renew_every:
            digest = (f"files_changed={len(status.splitlines())} "
                      f"log_bytes={size} "
                      f"wall_s={int(now - run.started_at)}")
            try:
                self.kernel.renew(run.task.id, run.lease.fence, digest=digest)
            except KernelError:
                pass
            run.last_renew = now

        if spawn_mod.slot_alive(run.slot):
            if stall_minutes > 0 and (now - run.last_change) >= stall_minutes * 60:
                spawn_mod.kill_slot(run.slot)
                return self._finish(run, exit_code=None, stalled=True)
            return None

        exit_code = run.slot.exit_code()
        if exit_code is None:
            exit_code = _windows_exit_code(run.slot.pid)
        return self._finish(run, exit_code=exit_code, stalled=False)

    # ------------------------------------------------------------------
    def _finish(self, run: LeaseRun, exit_code: int | None,
                stalled: bool) -> LeaseResult:
        result = LeaseResult(task_id=run.task.id, profile_id=run.profile.id,
                              worktree=str(run.worktree))
        # The fix-round count accumulates across attempts, so it lives on
        # the run; the result reports the running total.
        result.fix_rounds = run.fix_rounds
        log_tail = "\n".join(spawn_mod.tail_log(run.slot, 60))
        session = _session_from_log(log_tail)
        run.session = session or run.session

        failure_class = run.adapter.classify(exit_code, log_tail)
        if failure_class == classes.OK and stalled:
            failure_class = classes.STALL
        result.exit_code = exit_code
        result.session = run.session

        self.kernel.record_event(
            "AGENT_EXITED", subject=run.task.id, fence=run.lease.fence,
            payload={"profile": run.profile.id, "exit_code": exit_code,
                     "class": failure_class, "log": run.slot.log_path,
                     "session": run.session, "stalled": stalled})

        if failure_class != classes.OK:
            return self._recover(run, result, failure_class, log_tail)

        # -- provenance: which model actually served ----------------------
        # Recorded at submit, before the answer, so the fact outlives the
        # gateway and the run.  Empty is a real answer for a direct-CLI
        # profile, and it leaves D-L12's veto in force rather than guessing.
        served = self._record_provenance(run)

        # -- the oracles decide -------------------------------------------
        oracle_results = run_oracles(run.task, run.worktree)
        result.oracles = [o.to_obj() for o in oracle_results]
        if not oracle_results or all(o.ok for o in oracle_results):
            bundle = self._build_bundle(run, oracle_results)
            try:
                self.kernel.submit(run.task.id, run.lease.fence, bundle)
                result.outcome = "submitted"
                result.bundle = bundle.to_obj()
                self.fleet_state.record_run(run.profile.id)
                self.fleet_state.save()
                return result
            except KernelError as exc:
                result.outcome = "failed"
                result.error = _explain(exc)
                return result

        # -- a fix round ---------------------------------------------------
        max_fix_rounds = int(self.policy.get("recovery", {}).get("fix_rounds", 2))
        if run.fix_rounds >= max_fix_rounds:
            bundle = self._build_bundle(run, oracle_results)
            try:
                self.kernel.submit(run.task.id, run.lease.fence, bundle)
            except KernelError:
                pass
            result.outcome = "failed"
            result.error = "oracles failed after the fix-round budget"
            result.bundle = bundle.to_obj()
            return result

        run.fix_rounds += 1
        result.fix_rounds = run.fix_rounds
        self.kernel.record_event(
            "FIX_ROUND", subject=run.task.id, fence=run.lease.fence,
            payload={"round": run.fix_rounds,
                     "failed_oracles": [o.cmd for o in oracle_results if not o.ok]})
        new_slot = self._fix_round(run, oracle_results)
        if new_slot is None:
            result.outcome = "failed"
            result.error = "the fix round could not start a process"
            return result
        run.slot = new_slot
        run.last_size = -1
        run.last_status = ""
        run.last_change = time.time()
        return None      # still running

    # ------------------------------------------------------------------
    def _build_bundle(self, run: LeaseRun,
                      oracle_results: list) -> Bundle:
        """Assemble the evidence bundle.

        Everything here is measured by the harness.  The worker's own
        account of what it did is not included, because prose is not
        evidence.
        """
        task = run.task
        scope = scope_check(task, run.worktree, self.repo)
        outputs = []
        for path in scope["changed"]:
            if path.startswith(".pmwork/") or path.startswith(".fakecli"):
                continue
            full = Path(run.worktree) / path
            try:
                data = full.read_bytes()
            except OSError:
                continue
            outputs.append({"path": path,
                            "sha256": hashlib.sha256(data).hexdigest()})

        constitution_hash = ""
        try:
            constitution_hash = hashlib.sha256(
                self.repo.constitution_path.read_bytes()).hexdigest()
        except OSError:
            pass

        return Bundle(
            task=task.id,
            fence=run.lease.fence,
            base_commit=self.kernel._head_commit(),
            outputs=outputs,
            diff_scope_check=scope,
            commands=[CommandResult(cmd=o.cmd, cwd=str(run.worktree),
                                    exit=o.exit, stdout_hash=o.stdout_hash,
                                    stderr_hash=o.stderr_hash)
                      for o in oracle_results],
            oracle_results=list(oracle_results),
            premise_check={"refuted": False},
            budget_used={},
            resolved_models=[{"profile": run.lease.holder,
                              "session": run.session, "family": "unknown"}],
            constitution_hash=constitution_hash,
            context_hash="",
        )

    # ------------------------------------------------------------------
    def _fix_round(self, run: LeaseRun, oracle_results: list):
        """Start another attempt after the oracles failed."""
        failing = [o for o in oracle_results if not o.ok]
        feedback = "\n".join(
            f"- oracle {o.cmd!r} exited {o.exit}" for o in failing)
        handoff = order_mod.render_handoff(
            failure_class="ORACLE_FAILED", log_lines=feedback.splitlines(),
            git_status=spawn_mod.worktree_status(self.repo, run.worktree),
            git_diff_stat=spawn_mod.worktree_diff_stat(self.repo, run.worktree),
            previous_profile=run.profile.id)
        order_mod.write_handoff(run.worktree, handoff)

        spawn_mod.kill_slot(run.slot)

        resume = run.adapter.caps.can_resume and bool(run.session)
        try:
            new_slot = spawn_mod.spawn_slot(
                self.repo, task_id=run.task.id, profile_id=run.profile.id,
                adapter=run.adapter,
                profile=run.profile.raw or run.profile.to_dict(),
                prompt=order_mod.FIXED_PROMPT, worktree=run.worktree,
                fence=run.lease.fence, index=run.fix_rounds,
                env=self._env(run.profile))
        except (OSError, ValueError):
            return None

        if resume:
            self.kernel.record_event(
                "AGENT_RESUMED", subject=run.task.id, fence=run.lease.fence,
                payload={"profile": run.profile.id, "mode": "resume",
                         "round": run.fix_rounds})
        return new_slot

    # ------------------------------------------------------------------
    def _record_provenance(self, run: LeaseRun) -> set[str]:
        """Ask the gateway which model served this lease's calls.

        Only gateway-routed profiles can answer.  A direct-CLI profile never
        sends a request through the gateway, so the Kernel cannot know what
        served (``L-F2``) and the honest answer is an empty set - which keeps
        D-L12's unknown-family veto in force instead of inventing a model name
        from the profile's declared ``model``.

        The query is by window, not by task id: the Fleet spawns a CLI
        *process* and so cannot put a header on the CLI's requests.  A lease is
        exclusive to one worktree and a profile is capped by ``max_concurrent``,
        so the calls a deployment made inside the window were this lease's.
        """
        models: set[str] = set()
        if not run.profile.via_gateway:
            deployment = ""
        else:
            gateway = (self.policy.get("gateway") or {}).get("base_url", "")
            deployment = run.profile.model or run.profile.id
            end = time.time()
            start = run.started_at or end
            if gateway:
                models = provenance_mod.served_models_for_run(
                    gateway, deployment, start=start, end=end)

        try:
            provenance_mod.write_cache(run.worktree, deployment, models)
        except OSError:
            pass                         # a cache that cannot be written is not worth failing a run

        self.kernel.record_event(
            "MODEL_SERVED", subject=run.task.id, fence=run.lease.fence,
            payload={"deployment": deployment,
                     "served_models": sorted(models),
                     "profile": run.profile.id,
                     "via_gateway": run.profile.via_gateway,
                     "source": "gateway-window" if models else "none"})
        return models

    def _recover(self, run: LeaseRun, result: LeaseResult,
                 failure_class: str, log_tail: str) -> LeaseResult:
        """Apply the recovery ladder."""
        recovery_policy = self.policy.get("recovery", {}) or {}
        context = recover.RecoveryContext(
            failure_class=failure_class,
            profile_id=run.profile.id,
            adapter_supports_resume=run.adapter.caps.can_resume,
            adapter_supports_model_swap=run.adapter.caps.can_swap_model_on_resume,
            restart_count=int(run.lease.restart_count),
            max_restarts=int(recovery_policy.get("max_restarts_per_task", 5)),
            attempts_max=int(run.task.attempts.get("max", 3)),
            attempt=int(run.lease.attempt),
        )
        decision = recover.decide(
            context,
            network_retry_delays=recovery_policy.get(
                "network_retry_delays_s", [30, 120, 600]),
            max_restarts=int(recovery_policy.get("max_restarts_per_task", 5)),
            attempts_max=int(run.task.attempts.get("max", 3)))
        result.decision = decision.to_dict()
        result.failure_class = failure_class

        penalty = recover.apply_penalty(self.fleet_state, run.profile.id,
                                        failure_class, policy=self.policy)
        result.decision["penalty"] = penalty.to_dict()

        if penalty.pause_dispatch:
            self.kernel.record_event(
                "DISPATCH_PAUSED", subject=run.task.id, fence=run.lease.fence,
                payload={"reason": penalty.reason})
        if penalty.disabled:
            self.kernel.record_event(
                "PROFILE_DISABLED", subject=run.task.id, fence=run.lease.fence,
                payload={"profile": run.profile.id, "reason": penalty.reason})
        if penalty.cooldown_seconds:
            self.kernel.record_event(
                "PROFILE_COOLING", subject=run.task.id, fence=run.lease.fence,
                payload={"profile": run.profile.id,
                         "seconds": penalty.cooldown_seconds,
                         "reason": penalty.reason})

        self.kernel.record_event(
            "AGENT_FAILED", subject=run.task.id, fence=run.lease.fence,
            payload={"class": failure_class, "profile": run.profile.id,
                     "reason": decision.reason, "step": decision.step,
                     "restart_count": run.lease.restart_count + 1})

        if decision.step in (recover.L0, recover.L1, recover.L2):
            # The Dispatcher picks this up on the next tick: the task stays
            # leased and the ladder decides what happens next.
            result.outcome = "recovery"
            return result

        spawn_mod.kill_slot(run.slot)
        self._give_up(run.lease, result, decision.reason)
        if decision.step == recover.L4:
            result.outcome = "blocked"
            self.kernel.queue_add(
                topic=f"Task {run.task.id} is blocked: {decision.reason}",
                options=["re-scope the task", "split the task",
                         "escalate to the human"],
                recommended="re-scope the task",
                safe_default="escalate to the human",
                details=f"failure class {failure_class}")
        else:
            result.outcome = "recovery"
        return result

    def _give_up(self, lease: Lease, result: LeaseResult, reason: str) -> None:
        """Revoke the lease, bump the fence and quarantine the worktree."""
        try:
            self.kernel.revoke(lease.task_id, lease.fence, reason=reason)
        except KernelError:
            pass
        try:
            self.kernel.quarantine(lease.task_id, lease.fence, reason=reason,
                                   failure_class=result.failure_class)
        except KernelError:
            pass

    # ------------------------------------------------------------------
    def _poll_exit_code(self, slot) -> int | None:
        from pmk import plat
        if plat.IS_WINDOWS:
            return _windows_exit_code(slot.pid)
        return None

    # ------------------------------------------------------------------
    def run(self, task, profile: Profile,
            poll_seconds: float = 0.2,
            max_seconds: float = 900.0) -> LeaseResult:
        """Start a lease and supervise it to completion.

        A convenience loop for tests and single-shot launches.  The
        Dispatcher uses :meth:`start` and :meth:`poll` instead.
        """
        run, failure = self.start(task, profile)
        if run is None:
            return failure or LeaseResult(task_id=task.id,
                                          profile_id=profile.id,
                                          outcome="failed")
        deadline = time.time() + max_seconds
        while time.time() < deadline:
            result = self.poll(run)
            if result is not None:
                return result
            time.sleep(poll_seconds)
        return LeaseResult(task_id=task.id, profile_id=profile.id,
                            outcome="timeout",
                            error=f"lease exceeded {max_seconds}s")


def _session_from_log(log_text: str) -> str:
    """Find a session id in the process output."""
    from .adapters.fake import SESSION_PATTERN
    match = SESSION_PATTERN.search(log_text or "")
    return match.group(1) if match else ""


def _explain(exc: KernelError) -> str:
    """Turn a refusal into a sentence an operator can act on."""
    if not exc.details:
        return exc.reason
    parts = []
    for key, value in exc.details.items():
        if isinstance(value, list):
            value = "; ".join(str(v) for v in value)
        parts.append(f"{key}={value}")
    return f"{exc.reason} ({', '.join(parts)})"


def _windows_exit_code(pid: int | None) -> int | None:
    """The exit code of a finished Windows process, if it can be read."""
    if pid is None:
        return None
    import ctypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int,
                                     ctypes.c_uint32]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.GetExitCodeProcess.argtypes = [ctypes.c_void_p,
                                             ctypes.POINTER(ctypes.c_uint32)]
    kernel32.GetExitCodeProcess.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        code = ctypes.c_uint32()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return None
        if code.value == 259:      # STILL_ACTIVE
            return None
        return int(code.value)
    finally:
        kernel32.CloseHandle(handle)
