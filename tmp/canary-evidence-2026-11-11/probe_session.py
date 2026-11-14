"""Read-only probe of the opencode session DB to identify this session."""
import sqlite3

p = r"C:\Users\Tiwa Pene\.local\share\opencode\opencode.db"
con = sqlite3.connect("file:" + p.replace("\\", "/") + "?mode=ro", uri=True)
cur = con.cursor()
cur.execute("select name from sqlite_master where type='table'")
tables = [r[0] for r in cur.fetchall()]
print("tables:", tables)
for t in tables:
    cur.execute(f"pragma table_info({t})")
    cols = [r[1] for r in cur.fetchall()]
    print(t, cols)
