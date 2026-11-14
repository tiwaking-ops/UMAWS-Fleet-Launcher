import sys, re
path = sys.argv[1]
t = open(path, encoding="utf-8").read()
for blk in t.split("[[profile]]")[1:]:
    head = blk.split("\n")[0]
    if 'adapter = "hermes"' in blk:
        body = "[[profile]]" + blk
        body = body.split("model =")[0]
        print(body[:600])
        m = re.search(r'\nmodel = "([^"]+)"', "[[profile]]" + blk)
        print("model =", m.group(1) if m else "?")
        print("-" * 60)
