"""S-A1, live, pass 2 — the resume modes, with the *real* syntax.

Pass 1 discovered the resume and model syntax from the CLIs' own ``--help``
(the first pass's regexes produced false positives: ``--pass-session-id``,
``--no-session`` and ``--list-models`` are not resume flags).  This pass
runs the two remaining modes the operator approved:

* **resume (same model)**
* **resume (different model)**

The flags below are **copied from the captured help output**, not invented.
Where no second model string is known for a tool, the probe is recorded as
``UNVERIFIED`` rather than guessed — pilot v1 rule 5, and fleet rule 15
("capture, don't guess").

The session id for hermes comes from the *saved output of pass 1*, so no
extra "new" request is needed.  kilo, pi and opencode can continue without
an id.

Run:  py -3.12 pilot/spikes/s1_live_resume.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pmk import plat  # noqa: E402
from pmk.policy import load_agents  # noqa: E402
from pmk.store import Repo  # noqa: E402

PROMPT = "print the word ok and exit"
TIMEOUT = 300
RESULTS = ROOT / "pilot" / "spikes" / "s1-live-results.json"

#: The resume syntax, copied from each CLI's captured --help.
RESUME = {
    "hermes":   {"flag": "--resume", "needs_id": True,
                 "help": "--resume, -r SESSION  Resume a previous session by ID or title"},
    "kilo":     {"flag": "--continue", "needs_id": False,
                 "help": "-c, --continue  continue the last session"},
    "pi":       {"flag": "--continue", "needs_id": False,
                 "help": "--continue, -c  Continue previous session"},
    "cline":    {"flag": "--id", "needs_id": True,
                 "help": "--id <session-id>  Resume an existing session by ID"},
    "opencode": {"flag": "--continue", "needs_id": False,
                 "help": "--continue, -c  Continue the last session"},
}

#: The model-override syntax, copied from the captured --help.
MODEL_FLAG = {
    "hermes":   "-m",
    "kilo":     "-m",
    "pi":       "--model",
    "cline":    "-m",
    "opencode": None,
}

#: A second model string, taken from the operator's own prompts.json, so
#: that it is a model the tool is known to be able to serve.  ``None``
#: means no second model string is known, and the probe is skipped rather
#: than guessed.
SECOND_MODEL = {
    "pi": ("--provider", "orcarouter",
           "--model", "z-ai/glm-5.3-flash-free"),
    "cline": ("--provider", "cline",
              "--model", "cline-free/solar-mini4"),
    "hermes": None,
    "kilo": None,
    "opencode": None,
}


def now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_throwaway(name: str) -> Path:
    root = Path(os.environ.get("TEMP", "/tmp")) / f"s1-resume-{name}-{int(time.time())}"
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# throwaway\n", encoding="utf-8")
    for args in (["init", "-b", "main"],
                 ["config", "user.name", "s1-resume"],
                 ["config", "user.email", "s1-resume@localhost"],
                 ["add", "-A"],
                 ["commit", "-m", "throwaway"]):
        subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                       text=True)
    return root


def build_argv(template: list[str], prompt: str, cwd: Path) -> list[str]:
    return [token.replace("{prompt}", prompt).replace("{cwd}", str(cwd))
            .replace("{session}", "").replace("{model}", "")
            for token in template]


def run(argv: list[str], cwd: Path, timeout: int = TIMEOUT) -> dict:
    resolved = plat.resolve_executable(argv[0])
    real = plat.argv_for_executable(resolved, argv[1:]) if resolved else argv
    started = time.time()
    try:
        proc = subprocess.run(real, cwd=str(cwd), capture_output=True,
                              timeout=timeout, text=True, encoding="utf-8",
                              errors="replace")
        return {"argv": real, "exit": proc.returncode,
                "stdout": proc.stdout or "", "stderr": proc.stderr or "",
                "seconds": round(time.time() - started, 1)}
    except subprocess.TimeoutExpired:
        return {"argv": real, "exit": None, "stdout": "", "stderr": "",
                "seconds": round(time.time() - started, 1), "timed_out": True}
    except OSError as exc:
        return {"argv": real, "exit": -1, "stdout": "",
                "stderr": f"{type(exc).__name__}: {exc}", "seconds": 0}


def hermes_session_id(stdout: str) -> str | None:
    """The id from hermes's own trailer: 'Resume this session with: hermes --resume 20261022_23'."""
    match = re.search(r"Resume this session with:\s*\n?\s*hermes\s+--resume\s+(\S+)",
                      stdout or "")
    return match.group(1) if match else None


def list_models(cli: str) -> list[str]:
    """Ask a CLI to list its models, if it has such a command.  Free of quota."""
    for args in (["models", "list"], ["models"], ["model", "list"]):
        resolved = plat.resolve_executable(cli)
        if resolved is None:
            return []
        try:
            proc = subprocess.run(
                plat.argv_for_executable(resolved, args), capture_output=True,
                timeout=90, text=True, encoding="utf-8", errors="replace")
        except (OSError, subprocess.SubprocessError):
            return []
        text = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode == 0 and text.strip():
            names = [line.strip() for line in text.splitlines()
                     if line.strip() and not line.strip().startswith(("#", "Usage", "Commands:"))]
            if names:
                return names[:20]
    return []


def main() -> int:
    repo = Repo.discover(ROOT)
    agents = load_agents(repo)
    profiles = {p.get("adapter"): p for p in agents["profiles"]
                 if p.get("adapter") in RESUME}

    saved = {}
    if RESULTS.is_file():
        for record in json.loads(RESULTS.read_text(encoding="utf-8")):
            saved[record.get("cli")] = record

    out: list[dict] = []
    for cli, profile in profiles.items():
        template = list(profile.get("argv_new") or [])
        if not template:
            continue
        spec = RESUME[cli]
        record = {"cli": cli, "adapter": profile.get("adapter"),
                  "date": now_iso(),
                  "resume_syntax": spec["help"],
                  "model_syntax": MODEL_FLAG.get(cli)}

        print(f"=== {cli} ===", flush=True)

        # -- the session id, if the tool needs one ---------------------
        session_id = None
        if spec["needs_id"]:
            previous = saved.get(cli) or {}
            session_id = hermes_session_id((previous.get("new") or {}).get("stdout", ""))
            if not session_id:
                record["resume_same_model"] = {
                    "attempted": False,
                    "reason": ("the tool needs a session id and none could be "
                               "obtained from the earlier run"),
                }
                print("  no session id available", flush=True)
                out.append(record)
                continue
        record["session_id"] = session_id

        workdir = make_throwaway(cli)

        # -- resume, same model -----------------------------------------
        same = list(template)
        same.append(spec["flag"])
        if session_id:
            same.append(session_id)
        result = run(build_argv(same, PROMPT, workdir), workdir)
        record["resume_same_model"] = {
            "attempted": True, "argv": result["argv"], "exit": result["exit"],
            "seconds": result["seconds"],
            "stdout": (result["stdout"] or "")[:1200],
            "stderr": (result["stderr"] or "")[:1200],
            "ok": result["exit"] == 0,
        }
        print(f"  resume (same model) -> exit={result['exit']} "
              f"in {result['seconds']}s", flush=True)

        # -- resume, different model ------------------------------------
        model_args = SECOND_MODEL.get(cli)
        if not model_args or not MODEL_FLAG.get(cli):
            record["resume_different_model"] = {
                "attempted": False,
                "reason": ("no second model string is known for this tool, and "
                           "inventing one would be a guess rather than a "
                           "measurement"),
            }
            print("  resume (different model) -> UNVERIFIED "
                  "(no known second model string)", flush=True)
        else:
            different = list(template)
            different.append(spec["flag"])
            if session_id:
                different.append(session_id)
            different.extend(model_args)
            swapped = run(build_argv(different, PROMPT, workdir), workdir)
            record["resume_different_model"] = {
                "attempted": True, "argv": swapped["argv"],
                "exit": swapped["exit"], "seconds": swapped["seconds"],
                "stdout": (swapped["stdout"] or "")[:1200],
                "stderr": (swapped["stderr"] or "")[:1200],
                "ok": swapped["exit"] == 0,
                "model": " ".join(model_args),
            }
            print(f"  resume (different model) -> exit={swapped['exit']} "
                  f"in {swapped['seconds']}s", flush=True)

        out.append(record)

    path = ROOT / "pilot" / "spikes" / "s1-live-resume.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    print(f"\nwritten to {path}")
    for record in out:
        same = record.get("resume_same_model") or {}
        diff = record.get("resume_different_model") or {}
        print(f"  {record['cli']:<10} same={same.get('ok', same.get('reason'))}  "
              f"different={diff.get('ok', diff.get('reason'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
