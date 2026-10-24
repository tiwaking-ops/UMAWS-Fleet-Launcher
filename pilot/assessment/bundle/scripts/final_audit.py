"""Final audit of bundle size, report size, and verdict counts."""
import os, re, json

# Bundle audit
bundle = r"C:\temp\projects\testproject1\pilot\assessment\Bundle"
total = 0
count = 0
largest = (0, "")
for dp, dn, fns in os.walk(bundle):
    for fn in fns:
        fp = os.path.join(dp, fn)
        s = os.path.getsize(fp)
        total += s
        count += 1
        if s > largest[0]:
            largest = (s, os.path.relpath(fp, bundle).replace(os.sep, "/"))

print(f"Bundle: {count} files, {total:,} bytes ({total / 1024:.1f} KB)")
print(f"Largest: {largest[1]} ({largest[0]:,} bytes)")
print(f"Under 3MB: {'OK' if total < 3_000_000 else 'OVER'}")
print(f"Under 150KB per file: {'OK' if largest[0] < 150_000 else 'OVER'}")

# Report size
report = r"C:\temp\projects\testproject1\pilot\assessment\report-opencode-umaws-completion-v1.md"
report_size = os.path.getsize(report)
print(f"\nReport: {report_size:,} bytes ({report_size / 1024:.1f} KB)")
print(f"Report size: {'OK (<150KB)' if report_size < 150_000 else 'NOTE (>150KB but report not in bundle)'}")

# Count sections
r = open(report, encoding="utf-8").read()
sections = re.findall(r"^## [0-9]+\.", r, re.M)
print(f"\nReport sections: {len(sections)} (target: 15)")

# Count verdict occurrences in the report (all sections, not just tables)
# We search for the verdict labels as standalone words
for v in ["VERIFIED-NOW", "VERIFIED-EARLIER", "UNVERIFIED", "FAILED", "NOT-BUILT", "DIVERGES", "WRONG-DOC"]:
    n = len(re.findall(rf"\b{v}\b", r))
    print(f"  {v}: {n} occurrences in report")
