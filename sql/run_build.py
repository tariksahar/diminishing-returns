"""Run the SQL build against data/imdb.sqlite and print the filter funnel.

Python here only hands the .sql files to SQLite and prints what comes back;
the logic lives in the SQL.

Usage (from the repository root, after python sql/load_raw.py):
    python sql/run_build.py
"""

import sqlite3
import time

DB_PATH = "data/imdb.sqlite"


def read_sql(name):
    with open(f"sql/{name}", encoding="utf-8") as f:
        return f.read()


def main():
    conn = sqlite3.connect(DB_PATH)

    started = time.perf_counter()
    # executescript runs a file of several ;-separated statements in order.
    conn.executescript(read_sql("build_episodes.sql"))
    print(f"build_episodes.sql ran in {time.perf_counter() - started:.0f}s")

    funnel = conn.execute(read_sql("filter_funnel.sql"))
    names = [column[0] for column in funnel.description]
    print("\nFILTER FUNNEL (per show)")
    for name, value in zip(names, funnel.fetchone()):
        print(f"  {name:<26} {value:>8,}")

    shows, rows = conn.execute(
        "SELECT COUNT(DISTINCT show_tconst), COUNT(*) FROM episodes"
    ).fetchone()
    print(f"\nFinal shows: {shows:,}  |  Final episodes: {rows:,}")
    conn.close()


if __name__ == "__main__":
    main()
