"""S2/S3/S5 — run Caliber in a scratch copy and capture what it does.

This is spike code.  It never touches the pilot repository: it works on a
scratch copy, because a context-sync generator that writes instruction
files is exactly the thing the pilot's trust model is about.

    py -3.12 pilot/spikes/caliber_spike.py

Stages
------

``S2``
    Which files does Caliber write for ``claude`` and ``opencode``?  The
    answer becomes ``policy.context_sync.managed_paths``.
``S3``
    Does ``refresh`` preserve a human edit to a managed file?
``S5``
    Is ``refresh`` deterministic enough for a stable ``CONTEXT_SYNCED``
    hash?  Two refreshes with no code change, then the diff.

The LLM endpoint comes from the environment:

``OPENAI_BASE_URL``
    The OpenAI-compatible base URL (the operator's OmniRoute router).
``OPENAI_API_KEY``
    The key for it.
``CALIBER_MODEL`` / ``CALIBER_FAST_MODEL``
    The generation and scan models.  **Both** are needed: the scan model
    defaults to ``gpt-5.4-mini``, which is not in the operator's catalog,
    and Caliber refuses to start when the scan model is unavailable.

Every Caliber invocation uses ``--no-traces``: the pilot does not send
anonymous telemetry.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_SCRATCH_DEFAULT = Path(os.environ.get("TEMP", "/tmp")) / "caliber-s2-scratch"
SCRATCH = Path(os.environ.get("CALIBER_SPIKE_SCRATCH", str(_SCRATCH_DEFAULT)))


def sh(*args: str, cwd: Path | None = None, timeout: int = 1800) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(args, cwd=str(cwd) if cwd else None,
                              capture_output=True, text=True, timeout=timeout,
                              encoding="utf-8", errors="replace")
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"


def caliber(*args: str, cwd: Path | None = None,
            timeout: int = 1800) -> tuple[int, str, str]:
    return sh("caliber.cmd", "--no-traces", *args, cwd=cwd, timeout=timeout)


def snapshot(root: Path) -> dict[str, float]:
    """Every file's path and mtime, for detecting what changed."""
    out = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root))
        if rel.startswith(".git" + os.sep) or rel.startswith("work" + os.sep):
            continue
        try:
            out[rel] = path.stat().st_mtime
        except OSError:
            continue
    return out


def diff_snapshots(before: dict[str, float], after: dict[str, float]) -> dict:
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(p for p in set(before) & set(after)
                     if before[p] != after[p])
    return {"added": added, "removed": removed, "changed": changed}


def main() -> int:
    results: dict = {}
    out_dir = ROOT / "pilot" / "spikes"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not SCRATCH.is_dir():
        print(f"scratch repository missing: {SCRATCH}", file=sys.stderr)
        print("create it first (see the module docstring)", file=sys.stderr)
        return 2

    # -- S2: which files are written ---------------------------------
    before = snapshot(SCRATCH)
    code, out, err = caliber("init", "--agent", "claude,opencode",
                              "--auto-approve", "--force", cwd=SCRATCH)
    (out_dir / "caliber-s2-init.txt").write_text(
        out + "\n--- stderr ---\n" + err, encoding="utf-8")
    after = snapshot(SCRATCH)
    s2 = diff_snapshots(before, after)
    results["S2"] = {"exit": code, **s2}
    print(f"S2: exit={code}")
    print(f"    added   : {len(s2['added'])}")
    for path in s2["added"][:40]:
        print(f"      + {path}")
    print(f"    changed : {len(s2['changed'])}")
    for path in s2["changed"][:20]:
        print(f"      ~ {path}")

    managed = [p for p in s2["added"]
               if p.split(os.sep)[0] in ("AGENTS.md", "CLAUDE.md",
                                         "CALIBER_LEARNINGS.md", ".claude",
                                         ".cursor", ".github", ".agents",
                                         ".opencode", ".codex")]
    results["S2"]["managed_paths"] = managed

    # -- S3: does refresh preserve a human edit? ---------------------
    target = SCRATCH / "AGENTS.md"
    if not target.is_file():
        target = SCRATCH / "CLAUDE.md"
    s3: dict = {"skipped": "no managed file to edit"}
    if target.is_file():
        original = target.read_text(encoding="utf-8")
        marker = "\n<!-- pilot-spike: a hand-written note -->\nHUMAN EDIT\n"
        target.write_text(original + marker, encoding="utf-8")
        code, out, err = caliber("refresh", cwd=SCRATCH)
        (out_dir / "caliber-s3-refresh.txt").write_text(
            out + "\n--- stderr ---\n" + err, encoding="utf-8")
        after_text = target.read_text(encoding="utf-8") if target.is_file() else ""
        s3 = {
            "exit": code,
            "file": str(target.relative_to(SCRATCH)),
            "edit_preserved": "HUMAN EDIT" in after_text,
            "changed": after_text != original + marker,
        }
        results["S3"] = s3
        print(f"S3: edit_preserved={s3['edit_preserved']} "
              f"file={s3['file']}")
    else:
        results["S3"] = s3

    # -- S5: is refresh deterministic? -------------------------------
    before5 = snapshot(SCRATCH)
    code, out, err = caliber("refresh", cwd=SCRATCH)
    (out_dir / "caliber-s5-refresh-1.txt").write_text(
        out + "\n--- stderr ---\n" + err, encoding="utf-8")
    mid = snapshot(SCRATCH)
    code, out, err = caliber("refresh", cwd=SCRATCH)
    (out_dir / "caliber-s5-refresh-2.txt").write_text(
        out + "\n--- stderr ---\n" + err, encoding="utf-8")
    after5 = snapshot(SCRATCH)
    s5 = {
        "first_pass": diff_snapshots(before5, mid),
        "second_pass": diff_snapshots(mid, after5),
    }
    s5["stable"] = not s5["second_pass"]["changed"]
    results["S5"] = s5
    print(f"S5: stable={s5['stable']} "
          f"(second pass changed {len(s5['second_pass']['changed'])})")

    # -- the score, for the non-regression gate -----------------------
    code, out, err = caliber("score", "--json", cwd=SCRATCH)
    (out_dir / "caliber-score.json").write_text(out, encoding="utf-8")
    try:
        score = json.loads(out)
        results["score"] = {"score": score.get("score"),
                            "max": score.get("maxScore"),
                            "grade": score.get("grade"),
                            "checks": len(score.get("checks") or [])}
        print(f"score: {score.get('score')}/{score.get('maxScore')} "
              f"grade {score.get('grade')}")
    except (ValueError, AttributeError):
        results["score"] = {"raw": out[:400]}

    (out_dir / "caliber-spike-results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nresults written to {out_dir / 'caliber-spike-results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
