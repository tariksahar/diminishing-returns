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
from pathlib import Path

import pandas as pd

# Paths are anchored to this file rather than the working directory, so the
# show-lookup app (app/) can open the same database from wherever it is run.
REPO = Path(__file__).resolve().parent.parent
PARQUET_PATH = REPO / "data" / "processed" / "episodes.parquet"
ANALYSIS_DIR = REPO / "sql" / "analysis"

# Files that build a table the queries read. Run first, in this order:
# show_pages.sql reads the table show_slopes.sql writes.
TABLE_FILES = ["show_slopes.sql", "show_pages.sql"]

# Files holding exactly one SELECT, whose result is a finding.
QUERY_FILES = [
    "slope_split.sql",
    "finales.sql",
    "final_season.sql",
    "best_season.sql",
    "popularity.sql",
]


def read_sql(name):
    return (ANALYSIS_DIR / name).read_text(encoding="utf-8")


def open_analysis_db(shared_across_threads=False):
    """An in-memory SQLite database holding `episodes` and the derived tables.

    A sqlite3 connection refuses by default to be used from any thread but the
    one that opened it. The app serves every visitor from one cached connection
    on Streamlit's worker threads, so it passes shared_across_threads=True and
    serialises access itself."""
    conn = sqlite3.connect(":memory:", check_same_thread=not shared_across_threads)
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
