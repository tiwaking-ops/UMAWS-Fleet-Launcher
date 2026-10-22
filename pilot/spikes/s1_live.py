"""S-A1, live — the CLI matrix, measured against the real CLIs.

The operator approved this on 2026-10-22 with these terms:

* a **throwaway repository per CLI**;
* the prompt **"print the word ok and exit"**;
* three modes per CLI: **new**, **resume (same model)** and **resume
  (different model)**;
* if a profile is **already rate-limited**, send **ONE** request to it to
  capture a QUOTA fixture, and do **not otherwise provoke failures**.

Three rules from the Fleet amendment are honoured throughout:

* **Never invent CLI flags.**  The resume syntax is *discovered* from
  ``--help`` and from the output of the "new" run.  If it cannot be found,
  it is recorded as ``UNVERIFIED`` — not guessed.  Pilot v1 rule 5.
* **No quota hammering.**  One prompt per mode, per CLI.  The only extra
  request is the single one the operator authorised for an
  already-rate-limited profile.
* **Capture, don't guess.**  Every fact this script records is copied from
  real output.

What it produces
----------------

* ``pilot/spikes/s1-live-results.json`` — the matrix.
* ``tests/fleet/fixtures/<adapter>/<class>.txt`` — failure fixtures, with a
  provenance header naming the CLI, the version and the date.  These are the
  only fixtures that may be loaded by a real adapter's classifier.

Run:  py -3.12 pilot/spikes/s1_live.py
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pmk import plat  # noqa: E402
from pmk.policy import load_agents  # noqa: E402

PROMPT = "print the word ok and exit"
TIMEOUT = 240
FIXTURE_ROOT = ROOT / "tests" / "fleet" / "fixtures"

#: Words that suggest a quota or rate limit, used only to *recognise* a
#: failure that happened on its own.  They are never used to provoke one.
QUOTA_WORDS = ("quota", "rate limit", "rate_limit", "too many requests",
               "insufficient_quota", "exceeded your current quota",
               "resource_exhausted", "429")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_throwaway(name: str) -> Path:
    """A throwaway git repository for one CLI."""
    root = Path(os.environ.get("TEMP", "/tmp")) / f"s1-live-{name}-{int(time.time())}"
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# throwaway\n", encoding="utf-8")
    (root / "notes.txt").write_text("scratch\n", encoding="utf-8")
    for args in (["init", "-b", "main"],
                 ["config", "user.name", "s1-live"],
                 ["config", "user.email", "s1-live@localhost"],
                 ["add", "-A"],
                 ["commit", "-m", "throwaway"]):
        subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                       text=True)
    return root


def build_argv(template: list[str], prompt: str, cwd: Path) -> list[str]:
    out = []
    for token in template:
        out.append(token.replace("{prompt}", prompt)
                        .replace("{cwd}", str(cwd))
                        .replace("{session}", "")
                        .replace("{model}", ""))
    return out


def run(argv: list[str], cwd: Path, timeout: int = TIMEOUT) -> dict:
    """Run a CLI once, safely."""
    resolved = plat.resolve_executable(argv[0])
    real = plat.argv_for_executable(resolved, argv[1:]) if resolved else argv
    started = time.time()
    try:
        proc = subprocess.run(real, cwd=str(cwd), capture_output=True,
                              timeout=timeout, text=True, encoding="utf-8",
                              errors="replace")
        return {"argv": real, "exit": proc.returncode,
                "stdout": proc.stdout or "", "stderr": proc.stderr or "",
                "seconds": round(time.time() - started, 1),
                "timed_out": False}
    except subprocess.TimeoutExpired:
        return {"argv": real, "exit": None, "stdout": "", "stderr": "",
                "seconds": round(time.time() - started, 1), "timed_out": True}
    except OSError as exc:
        return {"argv": real, "exit": -1, "stdout": "",
                "stderr": f"{type(exc).__name__}: {exc}",
                "seconds": 0, "timed_out": False}


def help_text(cli: str) -> str:
    """The CLI's own help, captured verbatim."""
    resolved = plat.resolve_executable(cli)
    if resolved is None:
        return ""
    argv = plat.argv_for_executable(resolved, ["--help"])
    try:
        proc = subprocess.run(argv, capture_output=True, timeout=90, text=True,
                              encoding="utf-8", errors="replace")
        return (proc.stdout or "") + (proc.stderr or "")
    except (OSError, subprocess.SubprocessError):
        return ""


#: Where a session id might be printed.  These are *search* patterns, not
#: claims: the spike records where it found one, or that it found none.
SESSION_PATTERNS = (
    re.compile(r"session[\s_-]?id[:\s=]+([A-Za-z0-9._:-]{4,})", re.IGNORECASE),
    re.compile(r"session[:\s=]+([A-Za-z0-9._:-]{4,})", re.IGNORECASE),
    re.compile(r"conversation[\s_-]?id[:\s=]+([A-Za-z0-9._:-]{4,})", re.IGNORECASE),
    re.compile(r"^\s*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\s*$",
               re.IGNORECASE | re.MULTILINE),
    re.compile(r"resuming\s+([A-Za-z0-9._:-]{4,})", re.IGNORECASE),
)


def find_session_id(text: str) -> str | None:
    for pattern in SESSION_PATTERNS:
        match = pattern.search(text or "")
        if match:
            return match.group(1).strip()
    return None


#: Candidate resume flags, found in the help text.
RESUME_FLAG = re.compile(
    r"(--[a-z][a-z0-9-]*(?:resume|session|conversation|continue)[a-z0-9-]*"
    r"|--(?:r|c|s)\b)", re.IGNORECASE)
MODEL_FLAG = re.compile(
    r"(--[a-z][a-z0-9-]*(?:model|provider)[a-z0-9-]*)", re.IGNORECASE)


def find_flag(help_text_: str, pattern: re.Pattern) -> str | None:
    match = pattern.search(help_text_ or "")
    return match.group(1) if match else None


def looks_quota(text: str) -> bool:
    lowered = (text or "").lower()
    return any(word in lowered for word in QUOTA_WORDS)


def write_fixture(adapter: str, failure_class: str, text: str,
                  provenance: dict) -> Path:
    """Record a captured failure body as a fixture, with its provenance."""
    directory = FIXTURE_ROOT / adapter
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{failure_class.lower()}.txt"
    header = [
        f"# Captured from {adapter} on {provenance['date']}.",
        f"# CLI: {provenance['cli']} {provenance['version']}",
        f"# Invocation: {provenance['argv']}",
        f"# Exit code: {provenance['exit']}",
        "#",
        "# This is a real captured body.  The classifier pattern below is the",
        "# only thing that may be loaded by this adapter's classifier.",
        "",
    ]
    path.write_text("\n".join(header) + text.strip() + "\n", encoding="utf-8")
    return path


def probe_cli(profile: dict, cli: str, version: str) -> dict:
    """Probe one CLI: new, resume (same model), resume (different model)."""
    record: dict = {"cli": cli, "version": version, "date": now_iso(),
                    "adapter": profile.get("adapter"),
                    "profile": profile.get("id")}

    # -- the help, captured verbatim ----------------------------------
    help_text_ = help_text(cli)
    record["help_bytes"] = len(help_text_)
    resume_flag = find_flag(help_text_, RESUME_FLAG)
    model_flag = find_flag(help_text_, MODEL_FLAG)
    record["resume_flag_in_help"] = resume_flag
    record["model_flag_in_help"] = model_flag
    (ROOT / "pilot" / "spikes" / "s1-live-help").mkdir(parents=True,
                                                         exist_ok=True)
    (ROOT / "pilot" / "spikes" / "s1-live-help" / f"{cli}.txt").write_text(
        help_text_, encoding="utf-8")

    # -- 1. the "new" run ---------------------------------------------
    workdir = make_throwaway(cli)
    template = list(profile.get("argv_new") or [])
    record["argv_new"] = template
    result = run(build_argv(template, PROMPT, workdir), workdir)
    record["new"] = {k: v for k, v in result.items() if k != "argv"}
    record["new"]["argv"] = result["argv"]
    print(f"  {cli}: new -> exit={result['exit']} in {result['seconds']}s",
          flush=True)

    # -- did it already hit a quota? the operator authorised exactly one
    #    further request for a profile that is already rate-limited ----
    combined = (result["stdout"] or "") + (result["stderr"] or "")
    if result["exit"] not in (0, None) and looks_quota(combined):
        record["already_rate_limited"] = True
        print(f"  {cli}: already rate-limited; capturing the QUOTA fixture",
              flush=True)
        path = write_fixture(record["adapter"] or cli, "quota", combined,
                             {"date": record["date"], "cli": cli,
                              "version": version,
                              "argv": " ".join(result["argv"]),
                              "exit": result["exit"]})
        record["quota_fixture"] = str(path)
        record["quota_fixture_body"] = combined[:2000]
        return record
    record["already_rate_limited"] = False

    # -- 2. a session id? ---------------------------------------------
    session_id = find_session_id(combined)
    record["session_id"] = session_id
    record["session_id_found"] = bool(session_id)
    print(f"  {cli}: session id -> {session_id!r}", flush=True)

    # -- 3. resume ------------------------------------------------------
    if not session_id or not resume_flag:
        record["resume"] = {
            "attempted": False,
            "reason": ("no session id was printed"
                       if not session_id else
                       "no resume flag appears in --help"),
        }
        print(f"  {cli}: resume -> {record['resume']['reason']}", flush=True)
        return record

    # Resume, same model.
    resume_argv = list(template)
    resume_argv.append(resume_flag)
    resume_argv.append(session_id)
    resumed = run(build_argv(resume_argv, PROMPT, workdir), workdir)
    record["resume_same_model"] = {
        "attempted": True, "argv": resumed["argv"], "exit": resumed["exit"],
        "seconds": resumed["seconds"],
        "stdout": (resumed["stdout"] or "")[:1500],
        "stderr": (resumed["stderr"] or "")[:1500],
        "ok": resumed["exit"] == 0,
    }
    print(f"  {cli}: resume (same model) -> exit={resumed['exit']}", flush=True)

    # Resume, different model -- only if the CLI has a model flag.
    if model_flag:
        model_argv = list(template)
        model_argv.append(resume_flag)
        model_argv.append(session_id)
        model_argv.append(model_flag)
        model_argv.append("gpt-4o-mini")
        swapped = run(build_argv(model_argv, PROMPT, workdir), workdir)
        record["resume_different_model"] = {
            "attempted": True, "argv": swapped["argv"],
            "exit": swapped["exit"], "seconds": swapped["seconds"],
            "stdout": (swapped["stdout"] or "")[:1500],
            "stderr": (swapped["stderr"] or "")[:1500],
            "ok": swapped["exit"] == 0,
            "note": "the model name used is a guess at the CLI's syntax; "
                    "the exit code and output are the evidence",
        }
        print(f"  {cli}: resume (different model) -> exit={swapped['exit']}",
              flush=True)
    else:
        record["resume_different_model"] = {
            "attempted": False,
            "reason": "no model flag appears in --help",
        }

    return record


def main() -> int:
    from pmk.store import Repo
    repo = Repo.discover(ROOT)
    agents = load_agents(repo)
    profiles = {p.get("adapter"): p for p in agents["profiles"]
                 if p.get("adapter") in ("hermes", "kilo", "cline", "pi",
                                         "opencode")}
    # The CLI to run is argv_new[0].
    targets = []
    for adapter, profile in profiles.items():
        argv_new = profile.get("argv_new") or []
        if argv_new:
            targets.append((argv_new[0], profile))

    print(f"probing {len(targets)} CLI(s): "
          f"{', '.join(c for c, _ in targets)}\n", flush=True)

    results = []
    for cli, profile in targets:
        print(f"=== {cli} ===", flush=True)
        version = ""
        try:
            proc = subprocess.run(
                plat.argv_for_executable(plat.resolve_executable(cli),
                                         ["--version"]),
                capture_output=True, timeout=60, text=True,
                encoding="utf-8", errors="replace")
            version = (proc.stdout or proc.stderr or "").strip().splitlines()
            version = version[0] if version else ""
        except (OSError, subprocess.SubprocessError, AttributeError):
            version = "unknown"
        try:
            results.append(probe_cli(profile, cli, version))
        except Exception as exc:                   # noqa: BLE001
            results.append({"cli": cli, "error": f"{type(exc).__name__}: {exc}"})

    out = ROOT / "pilot" / "spikes" / "s1-live-results.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    print(f"\nresults written to {out}", flush=True)
    for record in results:
        print(f"  {record.get('cli'):<10} session_id="
              f"{record.get('session_id_found')} "
              f"resume={record.get('resume_same_model', {}).get('ok') if isinstance(record.get('resume_same_model'), dict) else '?'} "
              f"quota_fixture={bool(record.get('quota_fixture'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
