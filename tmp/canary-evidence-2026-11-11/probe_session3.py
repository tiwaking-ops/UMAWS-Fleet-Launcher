"""Read-only: confirm which session this conversation is, and its first user message."""
import sqlite3
import datetime
import json

p = r"C:\Users\Tiwa Pene\.local\share\opencode\opencode.db"
con = sqlite3.connect("file:" + p.replace("\\", "/") + "?mode=ro", uri=True)
cur = con.cursor()

print("now utc:", datetime.datetime.now(datetime.timezone.utc).isoformat())

sid = "ses_e390b97b1ffejF1UDOSQ7fG137"
cur.execute(
    "select id, title, directory, time_created, time_updated, metadata from session_v2 where id=?",
    (sid,),
)
row = cur.fetchone()
print("session:", row[:5])
print("metadata:", (row[5] or "")[:400])

cur.execute(
    "select id, type, seq, time_created, substr(data,1,300) from session_message "
    "where session_id=? order by seq asc limit 6",
    (sid,),
)
for r in cur.fetchall():
    print("MSG", r[1], "seq", r[2], datetime.datetime.fromtimestamp(r[3] / 1000, datetime.timezone.utc).isoformat(), (r[4] or "")[:280])

cur.execute(
    "select seq, time_created, substr(data,1,200) from session_message "
    "where session_id=? order by seq desc limit 3",
    (sid,),
)
for r in cur.fetchall():
    print("LASTMSG seq", r[0], datetime.datetime.fromtimestamp(r[1] / 1000, datetime.timezone.utc).isoformat(), (r[2] or "")[:200])
