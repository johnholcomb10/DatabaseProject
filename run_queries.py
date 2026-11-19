"""Run the five test queries in test_queries.sql and print each result as a table.

Usage:
    python run_queries.py              # uses project.db
    python run_queries.py --db other.db
"""

import argparse
import os
import re
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))


def load_queries(path=os.path.join(HERE, "test_queries.sql")):
    """Return [(title, sql), ...] split on '-- Q<n>:' header lines."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    parts = re.split(r"^-- (Q\d+:.*)$", text, flags=re.M)
    return [(parts[i].strip(), parts[i + 1].strip()) for i in range(1, len(parts), 2)]


def format_table(headers, rows, max_rows=None):
    shown = rows if max_rows is None else rows[:max_rows]
    cells = [[("" if v is None else str(v)) for v in r] for r in shown]
    widths = [max([len(h)] + [len(r[i]) for r in cells]) for i, h in enumerate(headers)]
    line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    out = [line, "  ".join("-" * w for w in widths)]
    out += ["  ".join(c.ljust(w) for c, w in zip(r, widths)) for r in cells]
    if max_rows is not None and len(rows) > max_rows:
        out.append(f"... ({len(rows) - max_rows} more rows)")
    out.append(f"({len(rows)} row{'s' if len(rows) != 1 else ''})")
    return "\n".join(out)


def run_all(conn, max_rows=None):
    """Yield (title, headers, rows) for each test query."""
    for title, sql in load_queries():
        cur = conn.execute(sql)
        yield title, [d[0] for d in cur.description], cur.fetchall()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=os.path.join(HERE, "project.db"))
    ap.add_argument("--max-rows", type=int, default=20, help="rows to print per query (0 = all)")
    args = ap.parse_args()
    if not os.path.exists(args.db):
        raise SystemExit(f"{args.db} not found. Run: python generate_data.py")
    conn = sqlite3.connect(args.db)
    for title, headers, rows in run_all(conn):
        print(f"\n=== {title} ===")
        print(format_table(headers, rows, args.max_rows or None))
    conn.close()


if __name__ == "__main__":
    main()
