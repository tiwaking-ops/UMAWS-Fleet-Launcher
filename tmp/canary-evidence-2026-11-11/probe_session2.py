"""Read-only: list recent opencode sessions for this project directory."""
import sqlite3
import datetime

p = r"C:\Users\Tiwa Pene\.local\share\opencode\opencode.db"
con = sqlite3.connect("file:" + p.replace("\\", "/") + "?mode=ro", uri=True)
cur = con.cursor()


def iso(ms):
    if ms is None:
        return None
    try:
        return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).isoformat()
    except Exception:
        return repr(ms)


for tbl in ("session_v2", "session"):
    try:
        cur.execute(
            "select id, title, agent, model, directory, time_created, time_updated "
            f"from {tbl} where directory like ? order by time_updated desc limit 12",
            ("%testproject1%",),
        )
        rows = cur.fetchall()
    except Exception as e:  # pragma: no cover
        print(tbl, "ERR", e)
        continue
    print("====", tbl, len(rows))
    for r in rows:
        print(r[0], "|", (r[1] or "")[:70], "|", r[2], "|", r[3], "| created", iso(r[5]), "| updated", iso(r[6]))
