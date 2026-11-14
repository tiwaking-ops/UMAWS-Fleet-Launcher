"""Read-only probe: opencode session_v2 rows for this project.  Read-only."""
import datetime as dt
import os
import sqlite3

p = os.path.expanduser("~/.local/share/opencode/opencode.db")
con = sqlite3.connect("file:" + p + "?mode=ro", uri=True)
cols = [c[1] for c in con.execute('pragma table_info("session_v2")')]
print("session_v2 cols:", cols)
print("session_v2 rows:", con.execute("select count(*) from session_v2").fetchone()[0])

time_col = None
for cand in ("time_created", "created", "time_updated", "updated"):
    if cand in cols:
        time_col = cand
        break
dir_col = "directory" if "directory" in cols else None
sel = "select * from session_v2"
if time_col:
    sel += " order by %s desc" % time_col
sel += " limit 15"
print("== session_v2, 15 most recent")
for r in con.execute(sel):
    d = dict(zip(cols, r))
    tc = d.get(time_col) if time_col else None
    when = None
    if isinstance(tc, (int, float)) and tc:
        v = tc / 1000 if tc > 10_000_000_000 else tc
        when = dt.datetime.fromtimestamp(v).isoformat(sep=" ")
    print("  ", when, "|", (d.get(dir_col) if dir_col else ""), "|",
          str(d.get("title"))[:60], "|", d.get("agent"))
con.close()
