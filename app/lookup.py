"""Everything the show page prints, fetched with SQL.

The app does not compute any finding itself. It opens the same in-memory
SQLite database the SQL analysis uses (sql/run_analysis.py), which builds the
`show_pages` table once, and then reads one show at a time by key. That keeps a
single definition of every number: tests/test_sql_analysis.py checks that
`show_pages` adds back up to the published findings.

This module has no Streamlit import, so it can be tested without a browser.
"""

import sys
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "sql"))

from run_analysis import open_analysis_db  # noqa: E402

AUDIENCE_TIERS = {
    1: "fewer than 5,000 votes",
    2: "5,000 to 50,000 votes",
    3: "50,000 to 500,000 votes",
    4: "500,000 votes or more",
}


class ShowLookup:
    """Read-only queries against the analysis database.

    Streamlit serves each visitor's reruns on worker threads, and one
    connection is shared by all of them, so every query takes a lock. The
    database is read-only after it is built, which is what makes sharing one
    connection safe at all."""

    def __init__(self):
        self._conn = open_analysis_db(shared_across_threads=True)
        self._lock = threading.Lock()

    def _rows(self, sql, params=()):
        # `params` are passed separately and bound by SQLite (the ? marks),
        # never pasted into the SQL string. A value bound this way can only
        # ever be data: a show id containing a quote cannot end the string
        # and start a new statement, which is what SQL injection is.
        with self._lock:
            cursor = self._conn.execute(sql, params)
            names = [column[0] for column in cursor.description]
            return [dict(zip(names, row)) for row in cursor.fetchall()]

    def catalogue(self):
        """Every show, for the search box: id, title and first year."""
        return self._rows(
            """
            SELECT show_tconst, title, start_year
            FROM show_pages
            ORDER BY title COLLATE NOCASE, start_year
            """
        )

    def page(self, show_tconst):
        """One show's row of show_pages, or None for an unknown id."""
        rows = self._rows("SELECT * FROM show_pages WHERE show_tconst = ?", (show_tconst,))
        return rows[0] if rows else None

    def episodes(self, show_tconst):
        """The show's rated episodes, in broadcast order."""
        return self._rows(
            """
            SELECT season_number, episode_number, average_rating, num_votes
            FROM episodes
            WHERE show_tconst = ?
            ORDER BY overall_order
            """,
            (show_tconst,),
        )

    def deal(self, n=6, exclude=()):
        """A random hand of n household names -- shows with 500,000 votes or
        more -- leaving out the ids in `exclude`, so a new hand never repeats
        the one on the table.

        ORDER BY RANDOM() shuffles the matching rows and LIMIT keeps the first
        n. The NOT IN list needs one ? per excluded id; only those placeholder
        marks are built into the SQL text, and the ids themselves are still
        bound as parameters."""
        not_in = f"AND show_tconst NOT IN ({', '.join('?' for _ in exclude)})" if exclude else ""
        return self._rows(
            f"""
            SELECT show_tconst, title, start_year, verdict
            FROM show_pages
            WHERE audience_tier = 4 {not_in}
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (*exclude, n),
        )

    def household_names(self):
        """How many household names there are, and how many clearly declined."""
        return self._rows(
            """
            SELECT COUNT(*)                 AS n_shows,
                   SUM(verdict = 'decline') AS n_declined
            FROM show_pages
            WHERE audience_tier = 4
            """
        )[0]

    def context(self, audience_tier):
        """The numbers a show is placed against: how many shows there are, how
        many are flat, and how common clear decline is in its audience tier."""
        overall = self._rows(
            """
            SELECT COUNT(*)                 AS n_shows,
                   AVG(verdict = 'flat')    AS share_flat
            FROM show_pages
            """
        )[0]
        tier = self._rows(
            """
            SELECT COUNT(*)                 AS n_in_tier,
                   AVG(verdict = 'decline') AS tier_share_declining
            FROM show_pages
            WHERE audience_tier = ?
            """,
            (audience_tier,),
        )[0]
        return {**overall, **tier, "tier_label": AUDIENCE_TIERS[audience_tier]}
