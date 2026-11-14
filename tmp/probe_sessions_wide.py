"""Read-only probe: most recent Codex threads and opencode sessions.

Widened view for reviewer item 1.  Read-only.
"""
import os
import sqlite3

HOME = os.path.expanduser("~")


def dt(v):
    if v is None:
        return None
    try:
        v = int(v)
    except Exception:                            # noqa: BLE001
        return v
    if v > 10_000_000_000:      # milliseconds
        v //= 1000
    import datetime as _d
    return _d.datetime.fromtimestamp(v).isoformat(sep=" ")


def codex():
    p = os.path.join(HOME, ".codex", "state_5.sqlite")
    con = sqlite3.connect("file:" + p + "?mode=ro", uri=True)
    print("== codex: 12 most recent threads")
    for r in con.execute(
            "select updated_at, cwd, source, model_provider, title "
            "from threads order by updated_at desc limit 12"):
        print("  ", dt(r[0]), "|", r[1], "|", r[2], "|", r[3], "|",
              (r[4] or "")[:60])
    con.close()


def opencode():
    p = os.path.join(HOME, ".local", "share", "opencode", "opencode.db")
    con = sqlite3.connect("file:" + p + "?mode=ro", uri=True)
    print("== opencode: 12 most recent sessions")
    for r in con.execute(
            "select time_created, directory, agent, model, title "
            "from session order by time_created desc limit 12"):
        print("  ", dt(r[0]), "|", r[1], "|", r[2], "|", (r[3] or "")[:24],
              "|", (r[4] or "")[:50])
    con.close()


codex()
opencode()
