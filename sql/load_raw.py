r"""Load the three raw IMDb dumps into a local SQLite database.

This is the only step of the SQL pipeline that is Python: SQLite cannot read a
gzipped TSV on its own, so something has to stream the files in. Everything
after this -- joins, filters, ordering -- happens in the .sql files next to it.

The loader deliberately does no analysis. It keeps every row, converts IMDb's
"\N" null marker into a real NULL, and stores numbers as numbers. Only the
columns src/build.py reads from title.basics are loaded, because that file is
12.6 million rows and the unused columns (originalTitle, runtimeMinutes, ...)
would roughly double the database for nothing.

Usage (from the repository root, after the raw files are in data/raw/):
    python sql/load_raw.py
"""

import gzip
import os
import sqlite3
import time

RAW_DIR = "data/raw"
DB_PATH = "data/imdb.sqlite"
BATCH_SIZE = 50_000
NULL_MARKER = r"\N"

# table name -> (source file, [(column, SQL type)], columns to keep from the file)
TABLES = {
    "raw_episode": (
        "title.episode.tsv.gz",
        [("tconst", "TEXT"), ("parentTconst", "TEXT"),
         ("seasonNumber", "INTEGER"), ("episodeNumber", "INTEGER")],
    ),
    "raw_ratings": (
        "title.ratings.tsv.gz",
        [("tconst", "TEXT"), ("averageRating", "REAL"), ("numVotes", "INTEGER")],
    ),
    "raw_basics": (
        "title.basics.tsv.gz",
        [("tconst", "TEXT"), ("titleType", "TEXT"), ("primaryTitle", "TEXT"),
         ("startYear", "INTEGER"), ("endYear", "INTEGER"), ("genres", "TEXT")],
    ),
}

CONVERTERS = {"TEXT": str, "INTEGER": int, "REAL": float}


def read_rows(path, columns):
    """Yield one tuple per data line, holding only `columns`, typed.

    The file is split on tabs by hand instead of with the csv module on
    purpose: IMDb's TSV has no quoting, and 5,465 titles in title.basics begin
    with a literal double quote. A quote-aware parser would treat those as
    quoted fields and strip or merge them."""
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        header = f.readline().rstrip("\n").split("\t")
        positions = [header.index(name) for name, _ in columns]
        convert = [CONVERTERS[sql_type] for _, sql_type in columns]
        for line in f:
            fields = line.rstrip("\n").split("\t")
            yield tuple(
                None if fields[i] == NULL_MARKER else conv(fields[i])
                for i, conv in zip(positions, convert)
            )


def load_table(conn, table, filename, columns):
    started = time.perf_counter()
    column_sql = ", ".join(f"{name} {sql_type}" for name, sql_type in columns)
    conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.execute(f"CREATE TABLE {table} ({column_sql})")

    placeholders = ", ".join("?" for _ in columns)
    insert = f"INSERT INTO {table} VALUES ({placeholders})"
    batch, total = [], 0
    for row in read_rows(os.path.join(RAW_DIR, filename), columns):
        batch.append(row)
        if len(batch) == BATCH_SIZE:
            conn.executemany(insert, batch)
            total += len(batch)
            batch.clear()
    conn.executemany(insert, batch)
    total += len(batch)
    conn.commit()
    print(f"{table:<12} {total:>12,} rows  ({time.perf_counter() - started:.0f}s)")


def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    # A throwaway local build: if the load dies halfway it is simply rerun,
    # so crash-safety journaling is only slowing it down.
    conn.execute("PRAGMA journal_mode = OFF")
    conn.execute("PRAGMA synchronous = OFF")

    for table, (filename, columns) in TABLES.items():
        load_table(conn, table, filename, columns)

    # The joins in build_episodes.sql match on these columns. Building the
    # indexes after the load is much faster than maintaining them per insert.
    conn.execute("CREATE INDEX idx_ratings_tconst ON raw_ratings (tconst)")
    conn.execute("CREATE INDEX idx_basics_tconst ON raw_basics (tconst)")
    conn.commit()
    conn.close()
    print(f"saved {DB_PATH}")


if __name__ == "__main__":
    main()
