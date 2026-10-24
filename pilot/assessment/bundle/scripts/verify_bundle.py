"""Verify bundle contents and print file listing."""
import os
import hashlib

bundle = r"C:\temp\projects\testproject1\pilot\assessment\Bundle"
files = []
total = 0
for dirpath, dirnames, filenames in os.walk(bundle):
    dirnames[:] = [d for d in dirnames if d != "__pycache__"]
    for fn in sorted(filenames):
        fp = os.path.join(dirpath, fn)
        size = os.path.getsize(fp)
        rel = os.path.relpath(fp, bundle).replace(os.sep, "/")
        files.append((rel, size))
        total += size

files.sort()
for rel, size in files:
    print(f"  {size:>8,}  {rel}")
print(f"\nTotal: {len(files)} files, {total:,} bytes ({total/1024:.1f} KB)")
over = [f for f in files if f[1] > 150000]
if over:
    print(f"OVER 150KB: {[f[0] for f in over]}")
else:
    print("All files under 150 KB: OK")
if total > 3_000_000:
    print(f"OVER 3MB: bundle too large")
else:
    print(f"Bundle under 3 MB: OK")
