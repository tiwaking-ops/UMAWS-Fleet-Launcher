"""The UMAWS Fleet Console (fleet amendment section 8).

One FastAPI process serving one HTML page on ``http://127.0.0.1:<port>``,
live-updated through server-sent events.  Started by ``start.ps1``.

**Every endpoint is a thin wrapper** over :mod:`pmk.api` or the Fleet.  There
is no business logic in the page, and none here either: the Console is a
view, not a second authority.

No authentication, and it binds to localhost only.  The operator asked for
no restrictions (FR12), but a LAN-exposed control surface is not "no
restrictions", it is an open door — so the bind address is fixed at
``127.0.0.1`` and is not configurable from the browser.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from pmk.api import Kernel, KernelError
from pmk.events import Actor
from fleet.conductor import Conductor
from fleet.dispatcher import Dispatcher
from fleet.overseer import OverseerRunner
from fleet.project import project_status
from fleet.state import FleetState

DEFAULT_PORT = 8765
LOOPBACK = "127.0.0.1"


class Console:
    """The app process's state: one Kernel, one Dispatcher, one Conductor."""

    def __init__(self, root: str | Path | None = None, port: int = DEFAULT_PORT):
        self.kernel = Kernel(root=root)
        self.repo = self.kernel.repo
        # Make sure the repository exists and is pinned before anything
        # else touches it.  Without this the Console would start on an
        # unpinned repository, and the sentinel's I8' check would have
        # nothing to check.
        self.kernel.init()
        self.fleet_state = FleetState.load()
        self.fixture_root = self.repo.root / "tests" / "fleet" / "fixtures"
        self.dispatcher = Dispatcher(self.kernel, self.fleet_state,
                                    fixture_root=self.fixture_root)
        self.overseer = OverseerRunner(self.kernel, self.fleet_state)
        self.conductor = Conductor(self.kernel, self.dispatcher, self.overseer)
        self.port = port
        self.launcher_path = self.repo.root / "prompts.json"
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self.started_at = time.time()

    # -- background loops -------------------------------------------------
    def start_loops(self) -> None:
        """Run the dispatch and conductor loops in the background."""
        if self._threads:
            return
        for name, target in (("dispatch", self._dispatch_loop),
                             ("conductor", self._conductor_loop)):
            thread = threading.Thread(target=target, daemon=True,
                                      name=f"pmk-{name}")
            thread.start()
            self._threads.append(thread)

    def stop_loops(self) -> None:
        self._stop.set()
        self.dispatcher.stop()
        self.conductor.stop()

    def _dispatch_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.dispatcher.tick()
            except Exception as exc:                # noqa: BLE001
                print(f"[console] dispatch: {exc}", flush=True)
            self._stop.wait(1.0)

    def _conductor_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.conductor.tick()
            except Exception as exc:                # noqa: BLE001
                print(f"[console] conductor: {exc}", flush=True)
            self._stop.wait(2.0)


console: Console | None = None


def get_console() -> Console:
    if console is None:
        raise HTTPException(status_code=503, detail="the console is not ready")
    return console


@contextlib.asynccontextmanager
async def _lifespan(_app: "FastAPI"):
    """Start and stop the background loops with the app."""
    global console
    if console is None:
        console = Console()
        console.start_loops()
    try:
        yield
    finally:
        if console is not None:
            console.stop_loops()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="UMAWS Fleet Console", docs_url=None, redoc_url=None,
              lifespan=_lifespan)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    page = Path(__file__).resolve().parent / "static" / "index.html"
    return page.read_text(encoding="utf-8")


# -- projects ---------------------------------------------------------------

@app.get("/api/project/status")
def api_project_status():
    return project_status(get_console().kernel)


@app.post("/api/project/init")
def api_project_init(brief: str = "", path: str | None = None):
    from fleet.project import init_project
    c = get_console()
    try:
        return init_project(c.kernel, brief=brief, target=path)
    except KernelError as exc:
        raise HTTPException(status_code=400, detail=exc.to_dict()) from exc


@app.post("/api/project/{action}")
def api_project_action(action: str):
    from fleet.project import PAUSED, RUNNING, set_state
    c = get_console()
    kernel = c.kernel
    if action == "pause":
        return set_state(kernel, PAUSED, reason="paused from the Console")
    if action == "resume":
        current = kernel.project_state()
        return set_state(kernel, RUNNING if current == PAUSED else current,
                         reason="resumed from the Console")
    if action == "run":
        c.dispatcher.tick()
        c.conductor.tick()
        return project_status(kernel)
    raise HTTPException(status_code=400, detail=f"unknown action {action!r}")


@app.post("/api/project/close-check")
def api_project_close_check():
    from fleet.project import close_check
    result = close_check(get_console().kernel)
    return result.to_dict()


# -- fleet ------------------------------------------------------------------

@app.get("/api/fleet")
def api_fleet():
    c = get_console()
    return {"status": c.dispatcher.status(), "slots": c.dispatcher.slots()}


@app.post("/api/fleet/{action}")
def api_fleet_action(action: str, profile: str = "", minutes: int = 0):
    c = get_console()
    state = c.fleet_state
    kernel = c.kernel
    if action == "enable":
        state.enable(profile, note="enabled from the Console")
        kernel.record_event("PROFILE_ENABLED", actor=Actor.human(),
                            subject=profile, payload={"profile": profile})
    elif action == "disable":
        state.disable(profile, note="disabled from the Console")
        kernel.record_event("PROFILE_DISABLED", actor=Actor.human(),
                            subject=profile, payload={"profile": profile})
    elif action == "cool":
        state.cool(profile, minutes * 60, note="cooled from the Console")
        kernel.record_event("PROFILE_COOLING", actor=Actor.human(),
                            subject=profile,
                            payload={"profile": profile, "seconds": minutes * 60})
    else:
        raise HTTPException(status_code=400, detail=f"unknown action {action!r}")
    state.save()
    return c.dispatcher.status()


@app.get("/api/agent/list")
def api_agent_list():
    c = get_console()
    return c.dispatcher.slots()


@app.get("/api/agent/{task}/log")
def api_agent_log(task: str, lines: int = 60):
    from pmk.plat import tail_file
    c = get_console()
    path = ""
    for event in reversed(c.kernel.events()):
        if event.type == "AGENT_STARTED" and event.subject == task:
            path = str(event.payload.get("log", ""))
            break
    if not path:
        raise HTTPException(status_code=404, detail="no log for that task")
    return {"task": task, "log": tail_file(path, lines)}


@app.post("/api/agent/{task}/stop")
def api_agent_stop(task: str):
    c = get_console()
    killed = c.dispatcher.kill_all()
    return {"killed": killed}


# -- tasks, queue -----------------------------------------------------------

@app.get("/api/tasks")
def api_tasks():
    c = get_console()
    state = c.kernel.state()
    return [t.to_obj() for t in state.task_list()]


@app.get("/api/queue")
def api_queue():
    return get_console().kernel.queue_list()


@app.post("/api/queue/decide")
def api_queue_decide(item_id: str, choice: str):
    c = get_console()
    try:
        return c.kernel.queue_decide(item_id, choice)
    except KernelError as exc:
        raise HTTPException(status_code=400, detail=exc.to_dict()) from exc


# -- overseer and metrics ---------------------------------------------------

@app.get("/api/overseer")
def api_overseer():
    c = get_console()
    return {"status": c.overseer.status(),
            "wake_reason": c.conductor.last_wake_reason}


@app.get("/api/metrics")
def api_metrics():
    c = get_console()
    kernel = c.kernel
    state = kernel.state()
    fleet_status = c.dispatcher.status()
    per_profile = []
    for profile in fleet_status["profiles"]:
        per_profile.append({
            "id": profile["id"], "runs": profile["runs"],
            "failures": profile["failures"],
            "last_failure_class": profile["last_failure_class"],
            "state": profile["state"],
        })
    return {
        "uptime_s": int(time.time() - c.started_at),
        "tasks": state.counts(),
        "task_total": len(state.tasks),
        "active_leases": len(state.active_leases()),
        "incidents": len(state.incidents),
        "queue_open": len([q for q in state.queue if q["state"] == "open"]),
        "slots_in_use": fleet_status["slots_in_use"],
        "fleet_cap": fleet_status["fleet_cap"],
        "dispatch_paused": fleet_status["dispatch_paused"],
        "pause_reason": fleet_status["pause_reason"],
        "per_profile": per_profile,
        "replan_rounds": c.conductor.replan_rounds,
        "wakes": len(c.overseer.wakes),
    }


# -- stop the line ----------------------------------------------------------

@app.post("/api/stop-all")
def api_stop_all():
    """STOP ALL: stop dispatching and leave running processes to finish."""
    c = get_console()
    c.repo.stop_file.parent.mkdir(parents=True, exist_ok=True)
    c.repo.stop_file.write_text(f"stopped at {c.kernel.clock.now_iso()}\n",
                                encoding="utf-8")
    c.dispatcher.stop()
    return {"stopped": True, "note": "running processes are left to finish"}


@app.post("/api/kill-all")
def api_kill_all():
    """KILL ALL: stop dispatching and kill every worker process tree."""
    c = get_console()
    c.repo.stop_file.parent.mkdir(parents=True, exist_ok=True)
    c.repo.stop_file.write_text(f"killed at {c.kernel.clock.now_iso()}\n",
                                encoding="utf-8")
    killed = c.dispatcher.kill_all()
    c.dispatcher.stop()
    return {"killed": killed}


@app.post("/api/resume")
def api_resume():
    c = get_console()
    if c.repo.stop_file.exists():
        c.repo.stop_file.unlink()
    c._stop.clear()
    c.dispatcher._stop.clear()
    c.conductor._stop.clear()
    c.start_loops()
    return {"stopped": False}


# -- manual launcher --------------------------------------------------------

@app.get("/api/launcher")
def api_launcher():
    from fleet.legacy import load_entries
    c = get_console()
    entries, settings = load_entries(c.launcher_path)
    return {"entries": [e.to_dict() for e in entries], "settings": settings,
            "path": str(c.launcher_path)}


@app.post("/api/launcher/save")
def api_launcher_save(entries: list[dict], settings: dict | None = None):
    from fleet.legacy import LauncherEntry, save_entries
    c = get_console()
    save_entries(c.launcher_path,
                 [LauncherEntry.from_dict(e) for e in entries], settings or {})
    return {"ok": True, "count": len(entries)}


@app.post("/api/launcher/import")
def api_launcher_import(path: str):
    from fleet.legacy import import_from_text, load_entries, save_entries
    c = get_console()
    entries, settings = load_entries(c.launcher_path)
    added, skipped = import_from_text(path, entries)
    save_entries(c.launcher_path, entries, settings)
    return {"added": added, "skipped": skipped}


@app.post("/api/launcher/launch")
def api_launcher_launch(entry_id: str, mode: str = "legacy",
                        keep_open: bool = True, task: str = "",
                        profile: str = ""):
    from fleet.legacy import launch_legacy, load_entries
    c = get_console()
    entries, _ = load_entries(c.launcher_path)
    entry = next((e for e in entries if e.id == entry_id), None)
    if entry is None:
        raise HTTPException(status_code=404, detail="no such entry")

    c.kernel.record_event("MANUAL_LAUNCH", actor=Actor.human(),
                          subject=entry.name or entry_id,
                          payload={"entry": entry_id, "mode": mode,
                                   "profile": profile})
    if mode == "managed":
        if not task or not profile:
            raise HTTPException(status_code=400,
                                detail="a managed launch needs a task and a profile")
        state = c.kernel.state()
        card = state.tasks.get(task)
        if card is None:
            raise HTTPException(status_code=404, detail="no such task")
        from fleet.profiles import Profile
        chosen = next((p for p in c.dispatcher.profiles()
                       if p.id == profile), None)
        if chosen is None:
            raise HTTPException(status_code=404, detail="no such profile")
        run, failure = c.dispatcher.harness.start(card, chosen)
        if run is None:
            raise HTTPException(status_code=400,
                                detail=failure.error if failure else "start failed")
        c.dispatcher.runs[task] = run
        return {"ok": True, "mode": "managed", "task": task,
                "profile": profile, "pid": run.slot.pid}
    try:
        result = launch_legacy(entry, keep_open=keep_open)
    except (RuntimeError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "mode": "legacy", **result}


# -- live updates -----------------------------------------------------------

@app.get("/api/events")
async def api_events():
    """A server-sent-event stream of the live state."""
    async def stream():
        while True:
            c = get_console()
            try:
                payload = {
                    "status": project_status(c.kernel),
                    "fleet": c.dispatcher.status(),
                    "slots": c.dispatcher.slots(),
                    "queue": c.kernel.queue_list(),
                }
                data = json.dumps(payload, default=str)
            except Exception as exc:                # noqa: BLE001
                data = json.dumps({"error": str(exc)})
            yield f"data: {data}\n\n"
            await asyncio.sleep(1.5)

    return StreamingResponse(stream(),
                             media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


def main() -> int:
    """Run the Console."""
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="UMAWS Fleet Console")
    parser.add_argument("--root", default=None)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default=LOOPBACK,
                        help="the bind address; the default is loopback only")
    args = parser.parse_args()

    global console
    console = Console(root=args.root, port=args.port)
    console.start_loops()
    print(f"UMAWS Fleet Console on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
