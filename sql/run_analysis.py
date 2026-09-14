"""Run the SQL analysis queries and print the published numbers they produce.

The analysis reads the committed episode table (data/processed/episodes.parquet),
copied into an in-memory SQLite database. It does not need data/imdb.sqlite or
the raw IMDb dumps: tests/test_sql_build.py already shows the SQL build
produces that same table row for row, so starting from the parquet loses
nothing and lets the analysis run anywhere, CI included.

Usage (from the repository root):
    python sql/run_analysis.py
"""

import math
import sqlite3

import pandas as pd

PARQUET_PATH = "data/processed/episodes.parquet"

# Files that build a table the queries read. Run first, in this order.
TABLE_FILES = ["show_slopes.sql"]

# Files holding exactly one SELECT, whose result is a finding.
QUERY_FILES = [
    "slope_split.sql",
    "finales.sql",
    "final_season.sql",
    "best_season.sql",
    "popularity.sql",
]


def read_sql(name):
    with open(f"sql/analysis/{name}", encoding="utf-8") as f:
        return f.read()


def open_analysis_db():
    """An in-memory SQLite database holding `episodes` and the derived tables."""
    conn = sqlite3.connect(":memory:")
    episodes = pd.read_parquet(PARQUET_PATH)
    # SQLite stores booleans as integers; convert explicitly rather than rely
    # on the driver's choice.
    episodes["ongoing"] = episodes["ongoing"].astype(int)
    episodes.to_sql("episodes", conn, index=False)

    # sqrt() is an optional SQLite build feature. Most builds include it, but
    # not all, so fall back to Python's own when it is missing.
    try:
        conn.execute("SELECT sqrt(4)")
    except sqlite3.OperationalError:
        conn.create_function("sqrt", 1, math.sqrt, deterministic=True)

    for name in TABLE_FILES:
        conn.executescript(read_sql(name))
    return conn


def query(conn, name):
    return pd.read_sql(read_sql(name), conn)


def main():
    conn = open_analysis_db()
    for name in QUERY_FILES:
        print(f"\n=== {name} ===")
        print(query(conn, name).T.to_string(header=False))
    conn.close()


if __name__ == "__main__":
    main()
