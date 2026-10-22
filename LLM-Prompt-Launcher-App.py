"""
LLM-Prompt-Launcher-App.py

A small Tkinter GUI for storing CLI-agent prompts (hermes, kilo, cline, pi, ...)
and launching one or many of them, each in its own terminal window.

Each saved entry follows the pattern you described:

    <command prefix>  "<prompt>"  <extra args after the prompt>

e.g.  prefix : pi --provider openrouter --model free -p
      prompt : You are working in C:\\temp\\projects\\... (multi-line OK)
      suffix : --yolo --cli --in "C:\\temp\\projects\\TiwasProjectsv3"

Entries are stored in  prompts.json  next to this script (override with the
LLM_PROMPT_LAUNCHER_FILE environment variable).

Run:  python LLM-Prompt-Launcher-App.py        (Python 3.8+, no extra packages)
Built for Windows + PowerShell; other platforms get a best-effort fallback.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_TITLE = "LLM Prompt Launcher"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.environ.get("LLM_PROMPT_LAUNCHER_FILE", os.path.join(HERE, "prompts.json"))

CHECKED = "\u2611"    # ☑
UNCHECKED = "\u2610"  # ☐

DEFAULT_SETTINGS = {"delay_seconds": 1.0, "keep_open": True}


# --------------------------------------------------------------------------
# Data model / storage
# --------------------------------------------------------------------------
def new_entry(**kw):
    e = {"id": uuid.uuid4().hex, "name": "", "group": "", "prefix": "",
         "prompt": "", "suffix": "", "cwd": ""}
    e.update(kw)
    return e


def load_data():
    """Returns (entries, settings). Missing/corrupt file -> empty list."""
    settings = dict(DEFAULT_SETTINGS)
    if not os.path.exists(DATA_FILE):
        return [], settings
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError) as exc:
        # keep a copy of the broken file so nothing is silently lost
        try:
            shutil.copy2(DATA_FILE, DATA_FILE + ".broken")
        except OSError:
            pass
        messagebox.showerror(APP_TITLE, f"Could not read {DATA_FILE}:\n{exc}\n\n"
                                        "A copy was saved as .broken. Starting empty.")
        return [], settings
    if isinstance(raw, list):          # tolerate a bare list
        raw = {"prompts": raw}
    settings.update(raw.get("settings", {}))
    entries = []
    for p in raw.get("prompts", []):
        e = new_entry()
        e.update({k: p[k] for k in e if k in p})
        entries.append(e)
    return entries, settings


def save_data(entries, settings):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"settings": settings, "prompts": entries}, f, indent=2, ensure_ascii=False)
    os.replace(tmp, DATA_FILE)  # atomic


# --------------------------------------------------------------------------
# Command building / launching
# --------------------------------------------------------------------------
def ps_escape(text):
    """Escape text for use inside a PowerShell double-quoted string."""
    return text.replace("`", "``").replace('"', '`"').replace("$", "`$")


def build_command(e):
    prompt = " ".join(e["prompt"].split())  # collapse newlines/extra spaces to one line
    parts = [e["prefix"].strip(), f'"{ps_escape(prompt)}"', e["suffix"].strip()]
    return " ".join(p for p in parts if p)


def find_shell():
    return shutil.which("pwsh") or shutil.which("powershell")


def launch_entry(e, script_dir, keep_open):
    """Open a new terminal window running this entry. Raises on failure."""
    shell = find_shell()
    cwd = e["cwd"].strip()
    if cwd and not os.path.isdir(cwd):
        raise FileNotFoundError(f"Working directory not found: {cwd}")

    if shell is None:
        raise RuntimeError("PowerShell (pwsh / powershell) was not found on PATH.")

    safe_name = (e["name"] or "prompt").replace("'", "''")
    lines = [f"$Host.UI.RawUI.WindowTitle = '{safe_name}'"]
    if cwd:
        lines.append("Set-Location -LiteralPath '" + cwd.replace("'", "''") + "'")
    lines.append(build_command(e))
    script = os.path.join(script_dir, f"launch_{e['id'][:8]}.ps1")
    with open(script, "w", encoding="utf-8-sig") as f:  # BOM so PS 5.1 reads UTF-8
        f.write("\n".join(lines) + "\n")

    args = [shell, "-NoLogo"]
    if keep_open:
        args.append("-NoExit")
    args += ["-ExecutionPolicy", "Bypass", "-File", script]

    flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    subprocess.Popen(args, cwd=cwd or None, creationflags=flags)


# --------------------------------------------------------------------------
# Importing a plain-text list of commands (one per line)
# --------------------------------------------------------------------------
def parse_command_line(line):
    """Split  '<prefix> "<prompt>" <suffix>'  into parts. Returns None if no prompt found."""
    first = line.find('"')
    if first == -1:
        return None
    # closing quote = first quote that ends the line or is followed by " -flag"
    m = re.compile(r'"(?=\s*$|\s+-)').search(line, first + 1)
    if not m:
        return None
    prefix = line[:first].strip()
    prompt = line[first + 1:m.start()]
    suffix = line[m.end():].strip()
    if not prefix or not prompt:
        return None

    tool = prefix.split()[0]
    m = re.search(r"--model\s+(\S+)", prefix)
    model = m.group(1) if m else ""

    cwd = ""
    m = re.search(r'(?:--in|--dir)\s+"?([A-Za-z]:\\[^"\s]+)"?', suffix)
    if m:
        cwd = m.group(1)
    else:
        m = re.search(r'working in ([A-Za-z]:\\[^\s"]+?)\.(?:\s|$)', prompt)
        if m:
            cwd = m.group(1)
    project = re.split(r"[\\/]", cwd.rstrip("\\/"))[-1] if cwd else ""
    if not project:
        m = re.search(r"wf/wf\.py", prompt)
        project = "wf-workflow" if m else "Ungrouped"

    name = " \u00b7 ".join(x for x in (tool, model, project if cwd else "") if x)
    return new_entry(name=name, group=project, prefix=prefix, prompt=prompt,
                     suffix=suffix, cwd=cwd)


# --------------------------------------------------------------------------
# Edit dialog
# --------------------------------------------------------------------------
class EntryDialog(tk.Toplevel):
    def __init__(self, parent, entry, groups, title):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.result = None
        self.entry = entry
        self.resizable(True, True)
        self.minsize(720, 560)

        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)
        frm.rowconfigure(5, weight=1)
        frm.rowconfigure(7, weight=1)

        self.v_name = tk.StringVar(value=entry["name"])
        self.v_group = tk.StringVar(value=entry["group"])
        self.v_prefix = tk.StringVar(value=entry["prefix"])
        self.v_suffix = tk.StringVar(value=entry["suffix"])
        self.v_cwd = tk.StringVar(value=entry["cwd"])

        r = 0
        ttk.Label(frm, text="Name").grid(row=r, column=0, sticky="w", pady=3)
        ttk.Entry(frm, textvariable=self.v_name).grid(row=r, column=1, columnspan=2, sticky="ew", pady=3)
        r += 1
        ttk.Label(frm, text="Group").grid(row=r, column=0, sticky="w", pady=3)
        ttk.Combobox(frm, textvariable=self.v_group, values=groups).grid(
            row=r, column=1, columnspan=2, sticky="ew", pady=3)
        r += 1
        ttk.Label(frm, text="Command prefix").grid(row=r, column=0, sticky="w", pady=3)
        ttk.Entry(frm, textvariable=self.v_prefix).grid(row=r, column=1, columnspan=2, sticky="ew", pady=3)
        r += 1
        ttk.Label(frm, text="(everything before the prompt, e.g.  pi --provider openrouter --model free -p)",
                  foreground="#666").grid(row=r, column=1, columnspan=2, sticky="w")
        r += 1
        ttk.Label(frm, text="Prompt").grid(row=r, column=0, sticky="nw", pady=3)
        r += 1  # row 5 holds the text box
        self.t_prompt = tk.Text(frm, height=8, wrap="word", undo=True)
        self.t_prompt.grid(row=5, column=0, columnspan=3, sticky="nsew")
        self.t_prompt.insert("1.0", entry["prompt"])
        r = 6
        ttk.Label(frm, text="Extra args after prompt").grid(row=r, column=0, sticky="w", pady=3)
        ttk.Entry(frm, textvariable=self.v_suffix).grid(row=r, column=1, columnspan=2, sticky="ew", pady=3)
        r = 7
        # preview goes in row 7 (expandable); working dir row 8
        self.t_preview = tk.Text(frm, height=5, wrap="word", state="disabled", background="#f3f3f3")
        self.t_preview.grid(row=r, column=0, columnspan=3, sticky="nsew", pady=(8, 3))
        r = 8
        ttk.Label(frm, text="Working directory").grid(row=r, column=0, sticky="w", pady=3)
        ttk.Entry(frm, textvariable=self.v_cwd).grid(row=r, column=1, sticky="ew", pady=3)
        ttk.Button(frm, text="Browse\u2026", command=self._browse).grid(row=r, column=2, padx=(6, 0))
        r = 9
        ttk.Label(frm, text="Terminal starts in this folder (optional). The grey box above shows the "
                            "exact command that will run.", foreground="#666").grid(
            row=r, column=0, columnspan=3, sticky="w")

        btns = ttk.Frame(frm)
        btns.grid(row=10, column=0, columnspan=3, sticky="e", pady=(10, 0))
        ttk.Button(btns, text="Save", command=self._save).pack(side="right")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=6)

        for v in (self.v_prefix, self.v_suffix):
            v.trace_add("write", lambda *_: self._refresh_preview())
        self.t_prompt.bind("<<Modified>>", self._on_modified)
        self._refresh_preview()

        self.bind("<Escape>", lambda _e: self.destroy())
        self.grab_set()
        self.t_prompt.focus_set()
        self.wait_window(self)

    def _on_modified(self, _e):
        if self.t_prompt.edit_modified():
            self._refresh_preview()
            self.t_prompt.edit_modified(False)

    def _current(self):
        e = dict(self.entry)
        e.update(name=self.v_name.get().strip(), group=self.v_group.get().strip(),
                 prefix=self.v_prefix.get().strip(),
                 prompt=self.t_prompt.get("1.0", "end").strip(),
                 suffix=self.v_suffix.get().strip(), cwd=self.v_cwd.get().strip())
        return e

    def _refresh_preview(self):
        e = self._current()
        self.t_preview.configure(state="normal")
        self.t_preview.delete("1.0", "end")
        self.t_preview.insert("1.0", build_command(e))
        self.t_preview.configure(state="disabled")

    def _browse(self):
        d = filedialog.askdirectory(parent=self, initialdir=self.v_cwd.get() or None)
        if d:
            self.v_cwd.set(os.path.normpath(d))

    def _save(self):
        e = self._current()
        if not e["prefix"]:
            messagebox.showwarning(APP_TITLE, "Command prefix is required.", parent=self)
            return
        if not e["prompt"]:
            messagebox.showwarning(APP_TITLE, "Prompt text is required.", parent=self)
            return
        if not e["name"]:
            e["name"] = e["prefix"].split()[0]
        self.result = e
        self.destroy()


# --------------------------------------------------------------------------
# Main window
# --------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE}  \u2014  {os.path.basename(DATA_FILE)}")
        self.geometry("1100x620")
        self.minsize(800, 400)

        self.entries, self.settings = load_data()
        self.checked = set()          # ids of ticked entries
        self.sort_col = None      # column currently sorted
        self.sort_rev = False     # True = descending
        self.launch_queue = []

        self.v_filter = tk.StringVar()
        self.v_group = tk.StringVar(value="All groups")
        self.v_delay = tk.DoubleVar(value=float(self.settings.get("delay_seconds", 1.0)))
        self.v_keep = tk.BooleanVar(value=bool(self.settings.get("keep_open", True)))
        self.v_status = tk.StringVar()

        self._build_ui()
        self.refresh()

    # ---- UI -----------------------------------------------------------
    def _build_ui(self):
        top = ttk.Frame(self, padding=(10, 8, 10, 4))
        top.pack(fill="x")
        ttk.Label(top, text="Search").pack(side="left")
        ent = ttk.Entry(top, textvariable=self.v_filter, width=28)
        ent.pack(side="left", padx=(6, 12))
        self.v_filter.trace_add("write", lambda *_: self.refresh())
        ttk.Label(top, text="Group").pack(side="left")
        self.cb_group = ttk.Combobox(top, textvariable=self.v_group, state="readonly", width=24)
        self.cb_group.pack(side="left", padx=6)
        self.cb_group.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        ttk.Button(top, text="Select visible", command=lambda: self.set_visible(True)).pack(side="left", padx=(16, 4))
        ttk.Button(top, text="Clear visible", command=lambda: self.set_visible(False)).pack(side="left")
        ttk.Button(top, text="Clear all", command=self.clear_all).pack(side="left", padx=4)

        mid = ttk.Frame(self, padding=(10, 4))
        mid.pack(fill="both", expand=True)
        cols = ("run", "name", "group", "command", "cwd")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", selectmode="extended")
        heads = {"run": ("Run", 50), "name": ("Name", 250), "group": ("Group", 150),
                 "command": ("Command prefix", 330), "cwd": ("Working dir", 260)}
        self.head_titles = {c: t for c, (t, w) in heads.items()}
        for c, (t, w) in heads.items():
            self.tree.heading(c, text=t, command=lambda col=c: self.sort_by(col))
            self.tree.column(c, width=w, anchor="center" if c == "run" else "w",
                             stretch=(c != "run"))
        vs = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vs.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")
        self.tree.bind("<Button-1>", self.on_click)
        self.tree.bind("<space>", self.on_space)
        self.tree.bind("<Double-1>", self.on_double)
        self.tree.bind("<Delete>", lambda _e: self.delete_selected())

        bar = ttk.Frame(self, padding=(10, 4))
        bar.pack(fill="x")
        ttk.Button(bar, text="New prompt", command=self.new_prompt).pack(side="left")
        ttk.Button(bar, text="Edit", command=self.edit_selected).pack(side="left", padx=4)
        ttk.Button(bar, text="Duplicate", command=self.duplicate_selected).pack(side="left")
        ttk.Button(bar, text="Delete", command=self.delete_selected).pack(side="left", padx=4)
        ttk.Button(bar, text="Import from text file\u2026", command=self.import_file).pack(side="left", padx=(12, 0))

        opts = ttk.Frame(self, padding=(10, 4))
        opts.pack(fill="x")
        ttk.Label(opts, text="Delay between launches (s)").pack(side="left")
        ttk.Spinbox(opts, from_=0, to=60, increment=0.5, width=5, textvariable=self.v_delay,
                    command=self.save_settings).pack(side="left", padx=6)
        ttk.Checkbutton(opts, text="Keep terminal open after the agent exits", variable=self.v_keep,
                        command=self.save_settings).pack(side="left", padx=12)
        self.btn_launch = ttk.Button(opts, text="Launch selected \u25b6", command=self.launch_checked)
        self.btn_launch.pack(side="right")

        ttk.Label(self, textvariable=self.v_status, relief="sunken", anchor="w",
                  padding=(8, 2)).pack(fill="x", side="bottom")

    # ---- list handling -------------------------------------------------
    def groups(self):
        return sorted({e["group"] for e in self.entries if e["group"]})

    def visible_entries(self):
        q = self.v_filter.get().strip().lower()
        g = self.v_group.get()
        out = []
        for e in self.entries:
            if g != "All groups" and e["group"] != g:
                continue
            hay = " ".join((e["name"], e["group"], e["prefix"], e["cwd"], e["prompt"])).lower()
            if q and q not in hay:
                continue
            out.append(e)
        if self.sort_col:
            out.sort(key=self.sort_key, reverse=self.sort_rev)
        return out

    def sort_by(self, col):
        """Click a column header: first click = A-Z, second click = Z-A."""
        if self.sort_col == col:
            self.sort_rev = not self.sort_rev
        else:
            self.sort_col, self.sort_rev = col, False
        for c, title in self.head_titles.items():
            arrow = ""
            if c == self.sort_col:
                arrow = "  \u25bc" if self.sort_rev else "  \u25b2"
            self.tree.heading(c, text=title + arrow)
        self.refresh()

    def sort_key(self, e):
        if self.sort_col == "run":
            return (e["id"] not in self.checked, e["name"].lower())  # ticked rows first
        field = {"name": "name", "group": "group",
                 "command": "prefix", "cwd": "cwd"}[self.sort_col]
        return (e[field].lower(), e["name"].lower())  # ties broken by name

    def refresh(self):
        groups = ["All groups"] + self.groups()
        self.cb_group["values"] = groups
        if self.v_group.get() not in groups:
            self.v_group.set("All groups")
        keep_sel = set(self.tree.selection())
        self.tree.delete(*self.tree.get_children())
        for e in self.visible_entries():
            self.tree.insert("", "end", iid=e["id"], values=(
                CHECKED if e["id"] in self.checked else UNCHECKED,
                e["name"], e["group"], e["prefix"], e["cwd"]))
        for iid in keep_sel:
            if self.tree.exists(iid):
                self.tree.selection_add(iid)
        self.update_status()

    def update_status(self, msg=None):
        n = len(self.checked & {e["id"] for e in self.entries})
        base = f"{len(self.entries)} prompts   |   {n} selected to run"
        self.v_status.set(f"{base}   |   {msg}" if msg else base)

    def toggle(self, iid):
        if iid in self.checked:
            self.checked.discard(iid)
        else:
            self.checked.add(iid)
        if self.tree.exists(iid):
            self.tree.set(iid, "run", CHECKED if iid in self.checked else UNCHECKED)
        self.update_status()

    def on_click(self, event):
        if self.tree.identify_region(event.x, event.y) != "cell":
            return
        if self.tree.identify_column(event.x) == "#1":
            iid = self.tree.identify_row(event.y)
            if iid:
                self.toggle(iid)
                return "break"

    def on_space(self, _event):
        for iid in self.tree.selection():
            self.toggle(iid)
        return "break"

    def on_double(self, event):
        if self.tree.identify_column(event.x) != "#1" and self.tree.identify_row(event.y):
            self.edit_selected()

    def set_visible(self, state):
        for e in self.visible_entries():
            (self.checked.add if state else self.checked.discard)(e["id"])
        self.refresh()

    def clear_all(self):
        self.checked.clear()
        self.refresh()

    # ---- CRUD ----------------------------------------------------------
    def persist(self):
        try:
            save_data(self.entries, self.current_settings())
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Could not save {DATA_FILE}:\n{exc}")

    def current_settings(self):
        try:
            delay = max(0.0, float(self.v_delay.get()))
        except (tk.TclError, ValueError):
            delay = 1.0
        return {"delay_seconds": delay, "keep_open": bool(self.v_keep.get())}

    def save_settings(self):
        self.settings = self.current_settings()
        self.persist()

    def find(self, iid):
        return next((e for e in self.entries if e["id"] == iid), None)

    def new_prompt(self):
        base = new_entry(group=self.v_group.get() if self.v_group.get() != "All groups" else "")
        dlg = EntryDialog(self, base, self.groups(), "New prompt")
        if dlg.result:
            self.entries.append(dlg.result)
            self.persist()
            self.refresh()
            self.update_status("created")

    def edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Select a prompt in the list first.")
            return
        e = self.find(sel[0])
        dlg = EntryDialog(self, dict(e), self.groups(), "Edit prompt")
        if dlg.result:
            e.update(dlg.result)
            self.persist()
            self.refresh()
            self.update_status("saved")

    def duplicate_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        for iid in sel:
            e = self.find(iid)
            c = dict(e, id=uuid.uuid4().hex, name=e["name"] + " (copy)")
            self.entries.insert(self.entries.index(e) + 1, c)
        self.persist()
        self.refresh()

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        if not messagebox.askyesno(APP_TITLE, f"Delete {len(sel)} prompt(s)?"):
            return
        gone = set(sel)
        self.entries = [e for e in self.entries if e["id"] not in gone]
        self.checked -= gone
        self.persist()
        self.refresh()

    def import_file(self):
        path = filedialog.askopenfilename(
            title="Import prompts (one full command per line)",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                lines = [ln.strip() for ln in f if ln.strip()]
        except OSError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        existing = {(e["prefix"], e["prompt"], e["suffix"]) for e in self.entries}
        added = skipped = 0
        for ln in lines:
            e = parse_command_line(ln)
            if not e:
                skipped += 1
                continue
            key = (e["prefix"], e["prompt"], e["suffix"])
            if key in existing:
                skipped += 1
                continue
            existing.add(key)
            self.entries.append(e)
            added += 1
        self.persist()
        self.refresh()
        messagebox.showinfo(APP_TITLE, f"Imported {added} prompt(s); skipped {skipped} "
                                       "(duplicates or lines without a quoted prompt).\n\n"
                                       "Tip: check the Working dir column - lines that named no "
                                       "folder are left blank.")

    # ---- launching -----------------------------------------------------
    def launch_checked(self):
        self.sort_col = None      # column currently sorted
        self.sort_rev = False     # True = descending
        todo = [e for e in self.entries if e["id"] in self.checked]
        if not todo:
            messagebox.showinfo(APP_TITLE, "Tick at least one prompt in the Run column "
                                           "(click the box or press Space).")
            return
        if len(todo) > 5 and not messagebox.askyesno(
                APP_TITLE, f"Launch {len(todo)} terminals at once?"):
            return
        self.save_settings()
        self.launch_dir = tempfile.mkdtemp(prefix="llm_launcher_")
        self.launch_queue = list(todo)
        self.launched = 0
        self.failed = []
        self.btn_launch.state(["disabled"])
        self._launch_next()

    def _launch_next(self):
        if not self.launch_queue:
            self.btn_launch.state(["!disabled"])
            msg = f"launched {self.launched}"
            if self.failed:
                msg += f", {len(self.failed)} failed"
                messagebox.showerror(APP_TITLE, "Some launches failed:\n\n" + "\n".join(self.failed))
            self.update_status(msg)
            return
        e = self.launch_queue.pop(0)
        try:
            launch_entry(e, self.launch_dir, self.v_keep.get())
            self.launched += 1
        except Exception as exc:  # noqa: BLE001 - report every failure to the user
            self.failed.append(f"{e['name']}: {exc}")
        self.update_status(f"launching\u2026 {self.launched} started, {len(self.launch_queue)} to go")
        delay_ms = int(self.current_settings()["delay_seconds"] * 1000)
        self.after(delay_ms if self.launch_queue else 0, self._launch_next)


if __name__ == "__main__":
    if sys.platform != "win32":
        print("Note: this app targets Windows + PowerShell; launching may not work here.")
    App().mainloop()
