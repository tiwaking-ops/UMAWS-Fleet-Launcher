"""Convert a CSV file into a Markdown table.

Usage:
    python src/csv2md.py data.csv
"""
import csv
import sys


def escape(cell):
    """Make a cell safe to embed in a Markdown table row."""
    return (cell.replace("|", "\\|")
                .replace("\r\n", " ")
                .replace("\n", " ")
                .replace("\r", " "))


def convert(rows):
    """Return a Markdown table for the given rows of cells."""
    rows = [[cell for cell in row] for row in rows if any(cell.strip() for cell in row)]
    if not rows:
        return ""

    ncols = max(len(row) for row in rows)
    header = rows[0] + [""] * (ncols - len(rows[0]))
    body = [row + [""] * (ncols - len(row)) for row in rows[1:]]

    lines = ["| " + " | ".join(escape(cell) for cell in header) + " |"]
    lines.append("| " + " | ".join("---" for _ in range(ncols)) + " |")
    for row in body:
        lines.append("| " + " | ".join(escape(cell) for cell in row) + " |")
    return "\n".join(lines)


def main(argv):
    if len(argv) != 2:
        print("usage: csv2md.py <file.csv>", file=sys.stderr)
        return 2
    try:
        with open(argv[1], newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.reader(handle))
    except OSError as exc:
        print("csv2md: {}".format(exc), file=sys.stderr)
        return 1
    table = convert(rows)
    if table:
        print(table)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
