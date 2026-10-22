"""The manual launcher, ported (fleet amendment section 8.3).

This is the operator's existing ``LLM-Prompt-Launcher-App.py`` ported into
the Console, with the same ``prompts.json`` schema so the operator's file
loads unchanged:

    {"settings": {...}, "prompts": [{id, name, group, prefix, prompt,
                                     suffix, cwd}, ...]}

Every feature of the Tk application is here: search, group filter,
select-visible, clear-visible, clear-all, New, Edit, Duplicate, Delete,
sortable columns, command preview, import-from-text-file, delay between
launches, keep-open, and Launch selected.

Two launch modes per click:

**Legacy (unmanaged)**
    Exactly the current behaviour — a PowerShell window running the
    assembled command.  It logs a ``MANUAL_LAUNCH`` event, counts against
    the fleet cap, and touches no task state.

**Managed**
    Choose a READY task and a profile; the Dispatcher runs the normal flow
    (claim, worktree, order file, oracles).

The ``ps_escape`` / ``build_command`` helpers are kept here **only** for the
legacy path (fleet amendment section 7.2).  Managed launches never use
them: they use argv lists (fleet rule 16).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_SETTINGS = {"delay_seconds": 1.0, "keep_open": True}

ENTRY_KEYS = ("id", "name", "group", "prefix", "prompt", "suffix", "cwd")


@dataclass
class LauncherEntry:
    """One saved launch entry."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    group: str = ""
    prefix: str = ""
    prompt: str = ""
    suffix: str = ""
    cwd: str = ""

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "group": self.group,
                "prefix": self.prefix, "prompt": self.prompt,
                "suffix": self.suffix, "cwd": self.cwd}

    @classmethod
    def from_dict(cls, obj: dict) -> "LauncherEntry":
        entry = cls()
        for key in ENTRY_KEYS:
            if key in obj:
                setattr(entry, key, str(obj[key]))
        return entry


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def load_entries(path: str | Path) -> tuple[list[LauncherEntry], dict]:
    """Load ``prompts.json``.  A missing or broken file yields empty lists.

    A broken file is copied aside first, so nothing is silently lost — the
    Tk application did the same.
    """
    from pmk.plat import read_text

    target = Path(path)
    settings = dict(DEFAULT_SETTINGS)
    if not target.exists():
        return [], settings
    try:
        raw = json.loads(read_text(target))
    except (OSError, ValueError):
        try:
            import shutil
            shutil.copy2(target, target.with_suffix(target.suffix + ".broken"))
        except OSError:
            pass
        return [], settings
    if isinstance(raw, list):
        raw = {"prompts": raw}
    settings.update(raw.get("settings") or {})
    entries = [LauncherEntry.from_dict(p) for p in (raw.get("prompts") or [])]
    return entries, settings


def save_entries(path: str | Path, entries: list[LauncherEntry],
                 settings: dict) -> None:
    """Write ``prompts.json`` atomically, in the operator's schema."""
    from pmk.plat import atomic_write_text
    payload = {
        "settings": {**DEFAULT_SETTINGS, **(settings or {})},
        "prompts": [e.to_dict() for e in entries],
    }
    atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# The legacy command path (unmanaged launches only)
# ---------------------------------------------------------------------------

def ps_escape(text: str) -> str:
    """Escape text for use inside a PowerShell double-quoted string."""
    return text.replace("`", "``").replace('"', '`"').replace("$", "`$")


def build_command(entry: LauncherEntry) -> str:
    """The legacy command line for one entry.

    **Legacy path only.**  Managed launches build argv lists instead; see
    fleet amendment section 7.2 and rule 16.
    """
    prompt = " ".join(entry.prompt.split())     # collapse newlines to one line
    parts = [entry.prefix.strip(), f'"{ps_escape(prompt)}"', entry.suffix.strip()]
    return " ".join(p for p in parts if p)


def parse_command_line(line: str) -> LauncherEntry | None:
    """Split ``<prefix> "<prompt>" <suffix>`` into its parts.

    Ported from the Tk application so that *import from text file* behaves
    identically.
    """
    first = line.find('"')
    if first == -1:
        return None
    # The closing quote ends the line or is followed by " -flag".
    match = re.compile(r'"(?=\s*$|\s+-)').search(line, first + 1)
    if not match:
        return None
    prefix = line[:first].strip()
    prompt = line[first + 1:match.start()]
    suffix = line[match.end():].strip()
    if not prefix or not prompt:
        return None

    tool = prefix.split()[0]
    model_match = re.search(r"--model\s+(\S+)", prefix)
    model = model_match.group(1) if model_match else ""

    cwd = ""
    cwd_match = re.search(r'(?:--in|--dir)\s+"?([A-Za-z]:\\[^"\s]+)"?', suffix)
    if cwd_match:
        cwd = cwd_match.group(1)
    else:
        cwd_match = re.search(r'working in ([A-Za-z]:\\[^\s"]+?)\.(?:\s|$)', prompt)
        if cwd_match:
            cwd = cwd_match.group(1)
    project = re.split(r"[\\/]", cwd.rstrip("\\/"))[-1] if cwd else ""
    if not project:
        project = "wf-workflow" if re.search(r"wf/wf\.py", prompt) else "Ungrouped"

    name = " \u00b7 ".join(x for x in (tool, model, project if cwd else "")
                           if x)
    return LauncherEntry(name=name, group=project, prefix=prefix, prompt=prompt,
                          suffix=suffix, cwd=cwd)


def import_from_text(path: str | Path,
                     entries: list[LauncherEntry]) -> tuple[int, int]:
    """Import a text file of command lines.  Returns ``(added, skipped)``."""
    from pmk.plat import read_text

    target = Path(path)
    try:
        lines = [ln.strip() for ln in read_text(target).splitlines() if ln.strip()]
    except OSError:
        return (0, 0)
    existing = {(e.prefix, e.prompt, e.suffix) for e in entries}
    added = skipped = 0
    for line in lines:
        entry = parse_command_line(line)
        if not entry:
            skipped += 1
            continue
        key = (entry.prefix, entry.prompt, entry.suffix)
        if key in existing:
            skipped += 1
            continue
        existing.add(key)
        entries.append(entry)
        added += 1
    return added, skipped


# ---------------------------------------------------------------------------
# Launching
# ---------------------------------------------------------------------------

def find_shell() -> str | None:
    import shutil
    return shutil.which("pwsh") or shutil.which("powershell")


def launch_legacy(entry: LauncherEntry, *, keep_open: bool = True,
                   script_dir: str | None = None) -> dict:
    """Launch an entry the way the operator's launcher does today.

    Opens a PowerShell window.  This is the *unmanaged* path: it touches
    no task state.
    """
    shell = find_shell()
    if shell is None:
        raise RuntimeError("PowerShell (pwsh / powershell) was not found on PATH.")
    cwd = entry.cwd.strip()
    if cwd and not os.path.isdir(cwd):
        raise FileNotFoundError(f"Working directory not found: {cwd}")

    script_dir = script_dir or tempfile.mkdtemp(prefix="llm_launcher_")
    os.makedirs(script_dir, exist_ok=True)
    safe_name = (entry.name or "prompt").replace("'", "''")
    lines = [f"$Host.UI.RawUI.WindowTitle = '{safe_name}'"]
    if cwd:
        lines.append("Set-Location -LiteralPath '" + cwd.replace("'", "''") + "'")
    lines.append(build_command(entry))
    script = os.path.join(script_dir, f"launch_{entry.id[:8]}.ps1")
    # utf-8-sig: Windows PowerShell 5.1 needs the BOM to read UTF-8.
    with open(script, "w", encoding="utf-8-sig") as fh:
        fh.write("\n".join(lines) + "\n")

    args = [shell, "-NoLogo"]
    if keep_open:
        args.append("-NoExit")
    args += ["-ExecutionPolicy", "Bypass", "-File", script]

    flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    proc = subprocess.Popen(args, cwd=cwd or None, creationflags=flags)
    return {"pid": proc.pid, "script": script, "command": build_command(entry)}


# ---------------------------------------------------------------------------
# Filtering, grouping and sorting (the Console's manual-launcher tab)
# ---------------------------------------------------------------------------

def groups_of(entries: list[LauncherEntry]) -> list[str]:
    return sorted({e.group for e in entries if e.group})


def visible_entries(entries: list[LauncherEntry], *, search: str = "",
                    group: str = "All groups",
                    sort_col: str = "", descending: bool = False,
                    checked: set | None = None) -> list[LauncherEntry]:
    """The filtered, sorted list the table shows."""
    needle = (search or "").strip().lower()
    out = []
    for entry in entries:
        if group and group != "All groups" and entry.group != group:
            continue
        haystack = " ".join((entry.name, entry.group, entry.prefix, entry.cwd,
                             entry.prompt)).lower()
        if needle and needle not in haystack:
            continue
        out.append(entry)
    if sort_col:
        checked = checked or set()
        if sort_col == "run":
            out.sort(key=lambda e: (e.id not in checked, e.name.lower()),
                     reverse=descending)
        else:
            field = {"name": "name", "group": "group", "command": "prefix",
                     "cwd": "cwd"}.get(sort_col, "name")
            out.sort(key=lambda e: (getattr(e, field).lower(), e.name.lower()),
                     reverse=descending)
    return out
