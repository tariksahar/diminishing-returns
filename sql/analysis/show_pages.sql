-- One row per show, holding everything the show-lookup app prints about it.
--
-- The published findings are shares across all 3,234 shows. The app turns
-- each of them around and asks the same question of a single show: which side
-- of the 0.5 threshold its slope falls on, how its final season compares with
-- the rest, how many of its season finales beat their season. Every column
-- here uses the same definition as the analysis query it mirrors, so summing
-- this table back up must reproduce the published numbers
-- (tests/test_sql_analysis.py checks that it does).
--
-- A table like this -- wide, one row per thing a page shows, built once and
-- then read by key -- is often called a mart. The app's own queries against it
-- are then a plain SELECT ... WHERE show_tconst = ?.
--
-- Needs show_slopes (show_slopes.sql) to exist first.

DROP TABLE IF EXISTS show_pages;

CREATE TABLE show_pages AS
WITH
    shows AS (
        SELECT
            show_tconst,
            MAX(show_title)               AS title,
            MAX(start_year)               AS start_year,
            MAX(end_year)                 AS end_year,
            MAX(ongoing)                  AS ongoing,
            COUNT(DISTINCT season_number) AS n_seasons,
            MAX(season_number)            AS last_season
        FROM episodes
        GROUP BY show_tconst
    ),

    -- Where each slope sits among all shows. CUME_DIST() is the share of rows
    -- whose slope is at or below this one, so:
    --   share of shows declining less steeply = 1 - cume_dist
    --   share of shows rising less steeply    = cume_dist - 1/N (this row excluded)
    -- No two slopes are equal, so there are no ties to break.
    placed AS (
        SELECT
            show_tconst,
            slope,
            intercept,
            n_episodes,
            total_votes,
            CUME_DIST() OVER (ORDER BY slope) AS cume_dist,
            COUNT(*)    OVER ()               AS n_shows
        FROM show_slopes
    ),

    -- Final season vs the rest, in integer tenths exactly as final_season.sql.
    final_vs_rest AS (
        SELECT
            e.show_tconst,
            SUM(CASE WHEN e.season_number = s.last_season  THEN CAST(ROUND(e.average_rating * 10) AS INTEGER) END) AS final_sum,
            SUM(e.season_number = s.last_season)                                                                    AS final_n,
            SUM(CASE WHEN e.season_number <> s.last_season THEN CAST(ROUND(e.average_rating * 10) AS INTEGER) END) AS rest_sum,
            SUM(e.season_number <> s.last_season)                                                                   AS rest_n
        FROM episodes AS e
        JOIN shows    AS s ON s.show_tconst = e.show_tconst
        GROUP BY e.show_tconst
    ),

    -- Season finales vs the rest of their season, as finales.sql.
    season_episodes AS (
        SELECT
            show_tconst,
            season_number,
            CAST(ROUND(average_rating * 10) AS INTEGER) AS rating_tenths,
            ROW_NUMBER() OVER (PARTITION BY show_tconst, season_number ORDER BY episode_number DESC) AS position_from_end,
            COUNT(*)     OVER (PARTITION BY show_tconst, season_number)                              AS season_episodes
        FROM episodes
    ),
    seasons AS (
        SELECT
            show_tconst,
            season_number,
            SUM(CASE WHEN position_from_end = 1 THEN rating_tenths END) AS finale,
            SUM(CASE WHEN position_from_end > 1 THEN rating_tenths END) AS rest_sum,
            COUNT(*) - 1                                                AS rest_n
        FROM season_episodes
        WHERE season_episodes >= 4
        GROUP BY show_tconst, season_number
    ),
    finale_record AS (
        SELECT
            s.show_tconst,
            COUNT(*)                                            AS finales_counted,
            SUM(s.finale * s.rest_n > s.rest_sum)               AS finales_won,
            -- The show's very last episode, if its last season was long enough
            -- to count: NULL when it was not.
            MAX(CASE WHEN s.season_number = sh.last_season
                     THEN s.finale * s.rest_n > s.rest_sum END) AS series_finale_rose
        FROM seasons AS s
        JOIN shows   AS sh ON sh.show_tconst = s.show_tconst
        GROUP BY s.show_tconst
    )

SELECT
    sh.show_tconst,
    sh.title,
    sh.start_year,
    sh.end_year,
    sh.ongoing,
    sh.n_seasons,
    p.n_episodes,
    p.total_votes,

    p.slope,
    p.intercept,
    CASE
        WHEN p.slope <= -0.5 THEN 'decline'
        WHEN p.slope <   0.5 THEN 'flat'
        ELSE                      'rise'
    END                                               AS verdict,
    1 - p.cume_dist                                   AS share_declining_less,
    p.cume_dist - 1.0 / p.n_shows                     AS share_rising_less,

    CASE
        WHEN p.total_votes <    5000 THEN 1
        WHEN p.total_votes <   50000 THEN 2
        WHEN p.total_votes <  500000 THEN 3
        ELSE                              4
    END                                               AS audience_tier,

    -- Final season, for ended shows only: an ongoing show has no final season
    -- yet, and the analysis leaves those out. Means are real numbers for
    -- display; the sign is decided in integers.
    CASE WHEN NOT sh.ongoing THEN f.final_sum / 10.0 / f.final_n END  AS final_season_mean,
    CASE WHEN NOT sh.ongoing THEN f.rest_sum  / 10.0 / f.rest_n  END  AS rest_mean,
    CASE
        WHEN sh.ongoing                                        THEN NULL
        WHEN f.final_sum * f.rest_n > f.rest_sum * f.final_n   THEN 1
        WHEN f.final_sum * f.rest_n < f.rest_sum * f.final_n   THEN -1
        ELSE                                                        0
    END                                               AS final_season_sign,

    COALESCE(r.finales_counted, 0)                    AS finales_counted,
    COALESCE(r.finales_won, 0)                        AS finales_won,
    r.series_finale_rose
FROM shows              AS sh
JOIN placed             AS p ON p.show_tconst = sh.show_tconst
JOIN final_vs_rest      AS f ON f.show_tconst = sh.show_tconst
LEFT JOIN finale_record AS r ON r.show_tconst = sh.show_tconst;
