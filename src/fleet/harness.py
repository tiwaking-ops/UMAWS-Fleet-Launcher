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
from . import runenv
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
    main_tree_status_start: dict | None = None
    #: Every main-tree path that was dirty at spawn (the summary keeps only 20).
    main_tree_paths_start: frozenset = frozenset()
    served_models: list[str] = field(default_factory=lambda: ["unavailable"])
    provenance_source: str = "unavailable"

    def to_dict(self) -> dict:
        return {"task": self.task.id, "profile": self.profile.id,
                "fence": self.lease.fence, "pid": self.slot.pid,
                "worktree": str(self.worktree),
                "session": self.session,
                "fix_rounds": self.fix_rounds}


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _worktree_changes(worktree: str | Path) -> tuple[list[str], str]:
    """Paths changed in *worktree* outside ``.pmwork/``, and an error text.

    Returns ``(paths, "")`` on success and ``([], reason)`` when git could not
    report the status.  An error is not the same as "no changes".
    """
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain", "-z", "--untracked-files=all"],
            cwd=str(Path(worktree).resolve()), capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        return [], f"{type(exc).__name__}: {exc}"
    if r.returncode != 0:
        detail = r.stderr.decode("utf-8", errors="replace").strip()[:300]
        return [], f"git status exited {r.returncode}: {detail}"
    entries = spawn_mod.parse_status_z(r.stdout.decode("utf-8", errors="replace"))
    return [path for _, path in entries if not path.startswith(".pmwork/")], ""


def _check_agent_claims(task, worktree: str | Path,
                        log_tail: str) -> tuple[list[str], list[str]]:
    """R-02: structural checks on agent claims before the oracles run.

    Returns ``(problems, advisories)``.  A *problem* fails the attempt; an
    *advisory* is recorded and does not.  The oracles, which the harness runs
    itself, are the evidence; these checks only fail fast on what is
    certain.
    """
    problems: list[str] = []
    advisories: list[str] = []
    wt = Path(worktree)

    # 1. RESULT.md should mention the leased task id (advisory only).
    result_path = wt / ".pmwork" / "RESULT.md"
    if result_path.is_file():
        try:
            text = result_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            advisories.append(f"RESULT.md unreadable: {exc}")
        else:
            if str(task.id) not in text:
                advisories.append(f"RESULT.md does not mention the task id {task.id}")

    # 2. NO_CHANGES fast-fail for implement cards with an empty worktree diff.
    #    If git cannot say, the check is skipped and recorded; the oracles decide.
    if task.type == "implement":
        changed, error = _worktree_changes(wt)
        if error:
            advisories.append(f"NO_CHANGES check skipped: {error}")
        elif not changed:
            problems.append("NO_CHANGES: implement card exited with no changes outside .pmwork/")

    return problems, advisories


def _validate_agent_claims(task, worktree: str | Path, log_tail: str) -> list[str]:
    """The blocking problems of :func:`_check_agent_claims`."""
    return _check_agent_claims(task, worktree, log_tail)[0]


def run_command(command: str, cwd: str | Path, *,
                timeout: int = 600) -> tuple[int, str, str]:
    """Run one acceptance command in the worktree.

    The harness runs the command, not the worker.  A command that the
    worker claims to have run is not evidence (constitution point 3).
    """
    cwd = Path(cwd).resolve()
    try:
        proc = subprocess.run(
            command, shell=True, cwd=str(cwd), capture_output=True,
            timeout=timeout, text=True, encoding="utf-8", errors="replace",
            env=runenv.worktree_env(cwd))
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

    @staticmethod
    def _read_handoff(worktree: str | Path) -> str:
        """An existing handoff note, so a reused tree's order carries it."""
        try:
            return order_mod.handoff_path(worktree).read_text(encoding="utf-8")
        except OSError:
            return ""

    def _adapter(self, profile: Profile):
        from .adapters import get_adapter
        return get_adapter(profile.adapter, self.fixture_root)

    def _env(self, profile: Profile, worktree: str | Path) -> dict:
        """The environment for the worker.

        Fleet amendment D-L3: scrubbing applies **only** to profiles with
        ``via_gateway = true``.  Direct-CLI profiles keep their own
        credentials in their own configuration — the Kernel cannot scrub
        what it does not own, and pretending otherwise would be a lie
        (known limitation L-F4).

        Both cases then pin the worktree first on ``PYTHONPATH`` (runenv).
        Without it a worker imports the installed copy of ``cna``/``pmk``
        instead of the code it is editing — the trap both T-0145 and T-0146
        agents hit in their own transcripts.
        """
        if profile.via_gateway:
            from pmk.plat import scrub_environment
            keep = ["PATH", "SystemRoot", "TEMP", "TMP", "HOMEDRIVE", "HOMEPATH",
                    "USERPROFILE", "APPDATA", "LOCALAPPDATA", "COMSPEC",
                    "PATHEXT", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE"]
            base = scrub_environment(keep=keep)
        else:
            import os
            base = os.environ.copy()
        return runenv.worktree_env(worktree, base=base)

    # ------------------------------------------------------------------
    def _precheck_enabled(self) -> bool:
        """S8 is opt-in fleet config, not pinned policy."""
        from pmk.policy import load_agents
        try:
            config = load_agents(self.repo)
        except Exception:
            return False
        fleet = config.get("fleet") if isinstance(config, dict) else None
        return bool((fleet or {}).get("precheck_satisfied", False))

    def _precheck(self, task) -> dict | None:
        """Return the oracle evidence when the base already satisfies *task*."""
        if not self._precheck_enabled():
            return None
        from . import precheck as precheck_mod
        satisfied, results = precheck_mod.oracles_already_pass(self.kernel, task)
        return {"satisfied": satisfied, "results": results} if satisfied else None

    def _summarize_main_tree_status(self, entries: list[tuple[str, str]]) -> dict:
        """Summarize main tree status for event payload: hash, count, <=20 paths."""
        import hashlib
        paths = [path for _, path in entries]
        # Hash of all paths for change detection
        hash_input = "\0".join(sorted(paths)).encode("utf-8")
        status_hash = hashlib.sha256(hash_input).hexdigest()[:16]
        # Up to 20 paths
        sample_paths = paths[:20]
        return {
            "hash": status_hash,
            "count": len(paths),
            "paths": sample_paths
        }

    def _new_changes_in_scope(self, before_paths, after_paths,
                              write_scope: list[str]) -> list[str]:
        """NEW main-tree paths inside the task's write scope.

        Takes the full path sets: the event summary keeps only 20 paths, which
        misses a new in-scope change when main is dirty in many places.
        """
        from pmk.models import scope_overlaps
        new_paths = sorted(set(after_paths) - set(before_paths))
        return [p for p in new_paths if scope_overlaps([p], write_scope)]

    def _diff_main_tree_status(self, before: dict, after: dict, write_scope: list[str]) -> list[str]:
        """The same from two event summaries (at most 20 paths each); the
        harness itself uses :meth:`_new_changes_in_scope` with the full sets."""
        return self._new_changes_in_scope(before.get("paths", []),
                                          after.get("paths", []), write_scope)

    # ------------------------------------------------------------------
    # Process records
    # ------------------------------------------------------------------
    def _record_started(self, task_id: str, lease, profile: Profile,
                        adapter, slot, worktree, *,
                        extra: dict | None = None) -> str:
        """Record one spawn as ``AGENT_STARTED``.

        ``pmk.worktrees.recorded_processes`` reads **only** this event, and
        the reaper refuses to delete a worktree while a recorded process is
        still alive.  So every process that writes in a worktree - the
        first, a fix round and a restart on another profile - must leave
        one, with its pid, creation time and worktree.

        Returns ``""`` when the record was written, else the failure text.
        A spawn whose record cannot be written is killed before returning:
        a live writer the log cannot see is exactly what lets the reaper
        delete a worktree underneath it.
        """
        payload = {
            "profile": profile.id,
            "adapter": getattr(adapter, "name", "") or profile.adapter,
            "pid": slot.pid,
            "creation_time": slot.creation_time,
            "worktree": str(worktree),
            "log": slot.log_path,
        }
        if extra:
            payload.update(extra)
        try:
            self.kernel.record_event(
                "AGENT_STARTED", subject=task_id, fence=lease.fence,
                payload=payload)
        except Exception as exc:                # noqa: BLE001
            try:
                spawn_mod.kill_slot(slot)
            except Exception:                   # noqa: BLE001
                pass
            return f"{type(exc).__name__}: {exc}"
        return ""

    # ------------------------------------------------------------------
    # Phase 1: start
    # ------------------------------------------------------------------
    def start(self, task, profile: Profile) -> tuple[LeaseRun | None, LeaseResult | None]:
        """Claim the task, make the worktree, write the order, spawn the CLI."""
        result = LeaseResult(task_id=task.id, profile_id=profile.id)
        adapter = self._adapter(profile)

        # R-09: refuse to lease if main tree has uncommitted changes in write scope
        # Run BEFORE kernel.claim() so refusal has no side effects (no CLAIMED event, no attempt burned)
        main_tree_changes = spawn_mod.main_tree_status_z(self.repo)
        seen = self.__dict__.setdefault("_scope_conflicts", {})
        overlapping = []
        if main_tree_changes and task.write_scope:
            from pmk.models import scope_overlaps
            for entry in main_tree_changes:
                # entry is (status_xy, path)
                if scope_overlaps([entry[1]], task.write_scope):
                    overlapping.append(entry[1])
        if overlapping:
            result.outcome = "blocked"
            result.error = (f"main tree has uncommitted changes in write scope: "
                            f"{', '.join(overlapping)}")
            # One SCOPE_CONFLICT event per task and distinct set of paths: the
            # Dispatcher retries with backoff, and a retry must not repeat the record.
            cause = tuple(sorted(overlapping))
            if seen.get(task.id) != cause:
                seen[task.id] = cause
                self.kernel.record_event(
                    "SCOPE_CONFLICT", subject=task.id, fence=0,
                    payload={"message": result.error,
                             "conflicting_paths": overlapping,
                             "write_scope": list(task.write_scope)})
            return None, result
        seen.pop(task.id, None)

        # S8: refuse a lease whose own oracles already pass on the base.  This
        # is exactly what T-0145 attempt 2 spent: re-leased work that main
        # already contained, then reported "already passing".
        precheck_note = self._precheck(task)
        if precheck_note is not None:
            result.outcome = "blocked"
            result.error = (
                "already satisfied on " + self.repo.default_branch() + ": "
                + "; ".join(o["cmd"] for o in precheck_note["results"]))
            self.kernel.record_event(
                "PRECHECK_SATISFIED", subject=task.id, fence=0,
                payload={"message": result.error,
                         "oracles": precheck_note["results"]})
            return None, result

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
            handoff=self._read_handoff(worktree),
            attempt=lease.attempt, fence=lease.fence, worktree=str(worktree))
        order_mod.write_order(worktree, order_text)

        try:
            slot = spawn_mod.spawn_slot(
                self.repo, task_id=task.id, profile_id=profile.id,
                adapter=adapter, profile=profile.raw or profile.to_dict(),
                prompt=order_mod.order_prompt(worktree), worktree=worktree,
                fence=lease.fence, index=0, env=self._env(profile, worktree))
        except (OSError, ValueError) as exc:
            result.outcome = "failed"
            result.error = f"spawn: {exc}"
            self._give_up(lease, result, "spawn failed")
            return None, result

        # R-11: record main-tree git status summary at spawn (hash, count, <=20 paths)
        main_status_entries = spawn_mod.main_tree_status_z(self.repo)
        main_status_summary = self._summarize_main_tree_status(main_status_entries)

        state = self.fleet_state.profile(profile.id)
        state.last_used = time.time()
        self.fleet_state.save()

        now = time.time()
        record_error = self._record_started(
            task.id, lease, profile, adapter, slot, worktree,
            extra={"degraded": slot.degraded,
                   "main_tree_status": main_status_summary})
        if record_error:
            result.outcome = "failed"
            result.error = f"start record: {record_error}"
            self._give_up(lease, result, "could not record the started process")
            return None, result

        run = LeaseRun(task=task, profile=profile, lease=lease, adapter=adapter,
                       slot=slot, worktree=worktree, started_at=now,
                       last_renew=now, last_change=now,
                       main_tree_status_start=main_status_summary,
                       main_tree_paths_start=frozenset(
                           path for _, path in main_status_entries))
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
        session = _session_from_log(run.adapter, log_tail)
        run.session = session or run.session

        failure_class = run.adapter.classify(exit_code, log_tail)
        if failure_class == classes.OK and stalled:
            failure_class = classes.STALL
        result.exit_code = exit_code
        result.session = run.session

        # R-11: compute main tree status diff at exit
        main_status_entries = spawn_mod.main_tree_status_z(self.repo)
        main_status_summary = self._summarize_main_tree_status(main_status_entries)
        new_changes_in_scope = []
        if run.main_tree_status_start is not None:
            new_changes_in_scope = self._new_changes_in_scope(
                run.main_tree_paths_start,
                frozenset(path for _, path in main_status_entries),
                list(run.task.write_scope))

        self.kernel.record_event(
            "AGENT_EXITED", subject=run.task.id, fence=run.lease.fence,
            payload={"profile": run.profile.id, "exit_code": exit_code,
                     "class": failure_class, "log": run.slot.log_path,
                     "session": run.session, "stalled": stalled,
                     "main_tree_status": main_status_summary,
                     "main_tree_new_changes_in_scope": new_changes_in_scope[:20],
                     "main_tree_new_changes_count": len(new_changes_in_scope)})

        if failure_class != classes.OK:
            return self._recover(run, result, failure_class, log_tail)

        # -- provenance: which model actually served ----------------------
        # Recorded at submit, before the answer, so the fact outlives the
        # gateway and the run.  Empty is a real answer for a direct-CLI
        # profile, and it leaves D-L12's veto in force rather than guessing.
        self._record_provenance(run)

        # -- the oracles decide -------------------------------------------
        # R-02: validate agent claims before trusting oracles
        claim_errors, claim_advisories = _check_agent_claims(
            run.task, run.worktree, log_tail)
        if claim_advisories:
            self.kernel.record_event(
                "AGENT_ADVISORY", subject=run.task.id, fence=run.lease.fence,
                payload={"profile": run.profile.id, "advisories": claim_advisories})
        if claim_errors:
            # Route through the same path as a non-OK exit class
            # Check if NO_CHANGES is in the errors
            if any("NO_CHANGES" in e for e in claim_errors):
                failure_class = classes.NO_CHANGES
            else:
                failure_class = classes.UNKNOWN
            return self._recover(run, result, failure_class, log_tail)

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
                              "session": run.session, "family": "unknown",
                              "served_models": list(run.served_models),
                              "source": run.provenance_source}],
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
                prompt=order_mod.order_prompt(run.worktree), worktree=run.worktree,
                fence=run.lease.fence, index=run.fix_rounds,
                env=self._env(run.profile, run.worktree))
        except (OSError, ValueError):
            return None

        # H4: a fix round is a new writer.  Record it before it can do any
        # work: the reaper reads AGENT_STARTED to decide whether this
        # worktree may be reclaimed.  A process whose record could not be
        # written has already been killed by the helper.
        if self._record_started(
                run.task.id, run.lease, run.profile, run.adapter, new_slot,
                run.worktree, extra={"round": run.fix_rounds}):
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

        if models:
            served_models = sorted(models)
            source = "gateway-window"
        else:
            served_models = ["unavailable"]
            source = "unavailable"

        run.served_models = list(served_models)
        run.provenance_source = source

        self.kernel.record_event(
            "MODEL_SERVED", subject=run.task.id, fence=run.lease.fence,
            payload={"deployment": deployment,
                     "served_models": served_models,
                     "profile": run.profile.id,
                     "via_gateway": run.profile.via_gateway,
                     "source": source})
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
        # REC-05: write a handoff before the lease is revoked, so that a
        # later attempt in a reused worktree is told what this one did.
        self._write_giveup_handoff(lease, result, reason)
        try:
            self.kernel.revoke(lease.task_id, lease.fence, reason=reason)
        except KernelError:
            pass
        try:
            self.kernel.quarantine(lease.task_id, lease.fence, reason=reason,
                                   failure_class=result.failure_class)
        except KernelError:
            pass

    def _write_giveup_handoff(self, lease, result, reason: str) -> None:
        """Best-effort handoff note for a worktree whose lease gave up.

        REC-05: the give-up path previously wrote nothing a replacement
        agent could read.  This is best-effort; a failure to write must not
        break the revoke/quarantine that follows.
        """
        worktree = getattr(lease, "worktree", "") or ""
        if not worktree:
            return
        try:
            if not Path(worktree).is_dir():
                return
            failure_class = getattr(result, "failure_class", "") or "give_up"
            text = (
                f"# Handoff - previous attempt gave up ({failure_class})\n\n"
                f"Reason: {reason}\n\n"
                f"Before starting, check `git status` for uncommitted work "
                f"left by the previous attempt. The lease fence was bumped, "
                f"so this worktree is a fresh checkout unless it was reused.\n")
            order_mod.write_handoff(worktree, text)
        except Exception:
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


def _session_from_log(adapter, log_text: str) -> str:
    """Find a session id in the process output.

    Delegates to the adapter's ``parse_session_id`` so each CLI's
    capture format is honoured.  Returns an empty string when no
    session id is present (the caller treats that as "no session id").
    """
    if adapter and getattr(adapter, "caps", None).reports_session_id:
        result = adapter.parse_session_id(log_text or "")
        return result or ""
    # Fall back to the fake pattern for backward compatibility with
    # fakes that pre-date the adapter dispatch.
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
