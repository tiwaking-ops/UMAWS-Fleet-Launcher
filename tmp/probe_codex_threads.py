"""Read-only probe: Codex threads and opencode sessions near the window.

Narrows reviewer item 1 ("which session edited the live tree"): list the
local agent threads/sessions whose cwd is this project, with timestamps.
Read-only.
"""
import os
import sqlite3

HOME = os.path.expanduser("~")
PROJECT = "testproject1"


def _fmt(v):
    return v


def codex() -> None:
    p = os.path.join(HOME, ".codex", "state_5.sqlite")
    con = sqlite3.connect("file:" + p + "?mode=ro", uri=True)
    print("== codex threads (sample columns)")
    row = con.execute("select * from threads limit 1").fetchone()
    cols = [c[1] for c in con.execute('pragma table_info("threads")')]
    if row:
        print("   sample:", dict(zip(cols, row)))
    print("== codex threads with cwd like project")
    for r in con.execute(
            "select id, created_at, updated_at, cwd, source, model_provider, "
            "title from threads where cwd like ? order by updated_at desc",
            ("%" + PROJECT + "%",)):
        print("   ", r)
    con.close()


def opencode() -> None:
    p = os.path.join(HOME, ".local", "share", "opencode", "opencode.db")
    con = sqlite3.connect("file:" + p + "?mode=ro", uri=True)
    print("== opencode project_directory for this project")
    cols = [c[1] for c in con.execute(
        'pragma table_info("project_directory")')]
    print("   cols:", cols)
    for r in con.execute(
            "select * from project_directory where directory like ?",
            ("%" + PROJECT + "%",)):
        print("   ", r)
    print("== opencode session table cols + recent")
    scols = [c[1] for c in con.execute('pragma table_info("session")')]
    print("   session cols:", scols)
    con.close()


codex()
opencode()
