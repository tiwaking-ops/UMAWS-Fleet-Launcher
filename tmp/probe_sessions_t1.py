"""Read-only probe: opencode sessions in this project with activity windows.

Narrows reviewer item 1.  Read-only.
"""
import datetime as dt
import os
import sqlite3

p = os.path.expanduser("~/.local/share/opencode/opencode.db")
con = sqlite3.connect("file:" + p + "?mode=ro", uri=True)


def when(v):
    if not v:
        return "-"
    v = v / 1000 if v > 10_000_000_000 else v
    return dt.datetime.fromtimestamp(v).strftime("%m-%d %H:%M:%S")


rows = list(con.execute(
    "select id, time_created, time_updated, title, agent, cost, tokens_input,"
    "tokens_output, time_archived from session_v2 "
    "where directory like '%testproject1%' order by time_created desc limit 20"))
print("%-34s %-14s %-14s %-8s %s" % ("id", "created", "updated", "tokens", "title"))
for r in rows:
    tid, tc, tu, title, agent, cost, ti, to, arch = r
    print("%-34s %-14s %-14s %-8s %s%s" % (
        (tid or "")[:34], when(tc), when(tu), (ti or 0) + (to or 0),
        (title or "")[:48], "  [archived]" if arch else ""))
con.close()
