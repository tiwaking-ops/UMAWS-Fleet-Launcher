"""Read-only probe: which session (if any) left records for 2026-11-12?

Looks at the local Codex and opencode stores for anything timestamped in the
window of the concurrent commits.  Read-only; no store is modified.
"""
import os
import sqlite3

HOME = os.path.expanduser("~")
CANDIDATES = [
    os.path.join(HOME, ".codex", "logs_2.sqlite"),
    os.path.join(HOME, ".codex", "state_5.sqlite"),
    os.path.join(HOME, ".codex", "memories_1.sqlite"),
    os.path.join(HOME, ".local", "share", "opencode", "opencode.db"),
]


def probe(path: str) -> None:
    print("==", path)
    if not os.path.exists(path):
        print("   absent")
        return
    try:
        con = sqlite3.connect("file:" + path + "?mode=ro", uri=True)
    except Exception as exc:                     # noqa: BLE001
        print("   open failed:", exc)
        return
    try:
        tables = [r[0] for r in con.execute(
            "select name from sqlite_master where type='table'")]
        print("   tables:", tables)
        for t in tables:
            try:
                n = con.execute('select count(*) from "%s"' % t).fetchone()[0]
            except Exception as exc:             # noqa: BLE001
                print("   ", t, "count err", exc)
                continue
            cols = [c[1] for c in con.execute('pragma table_info("%s")' % t)]
            print("   ", t, "rows=", n, "cols=", cols[:12])
    finally:
        con.close()


for c in CANDIDATES:
    probe(c)
