-- Finales: does a season's last episode beat the rest of that season?
--
-- README: season finales beat the rest of their season 72.6% of the time;
-- series finales (the last episode of the last season) rise 71.6% of the time.
-- Only seasons with at least 4 episodes count, so "the rest" has some body.
-- Ratings are compared unweighted, as in notebooks/phase2_finales.py.
--
-- Exact arithmetic. "finale > mean of the rest" is tested without dividing:
--     finale > rest_sum / rest_n    <=>    finale * rest_n > rest_sum
-- and with ratings as whole tenths (7.4 -> 74), both sides are integers. A
-- finale that exactly equals its season's mean is then a tie, never a
-- rounding accident on either side of zero.

WITH
    season_episodes AS (
        SELECT
            show_tconst,
            season_number,
            CAST(ROUND(average_rating * 10) AS INTEGER) AS rating_tenths,
            -- Counting down from the end: the finale is position 1.
            ROW_NUMBER() OVER (
                PARTITION BY show_tconst, season_number
                ORDER BY episode_number DESC
            ) AS position_from_end,
            COUNT(*) OVER (PARTITION BY show_tconst, season_number) AS season_episodes,
            MAX(season_number) OVER (PARTITION BY show_tconst)      AS last_season
        FROM episodes
    ),

    seasons AS (
        SELECT
            show_tconst,
            season_number,
            season_number = last_season AS is_final_season,
            -- Conditional aggregation again: each SUM only adds the rows its
            -- CASE lets through. CASE without ELSE yields NULL, and SUM skips
            -- NULLs, so the finale and "the rest" are split in one pass.
            SUM(CASE WHEN position_from_end = 1 THEN rating_tenths END) AS finale,
            SUM(CASE WHEN position_from_end > 1 THEN rating_tenths END) AS rest_sum,
            COUNT(*) - 1                                                AS rest_n
        FROM season_episodes
        WHERE season_episodes >= 4
        GROUP BY show_tconst, season_number, last_season
    )

SELECT
    COUNT(*)                                                    AS seasons,
    SUM(finale * rest_n > rest_sum)                             AS season_finale_wins,
    SUM(finale * rest_n = rest_sum)                             AS season_finale_ties,
    ROUND(100.0 * AVG(finale * rest_n > rest_sum), 1)           AS pct_season_finale_wins,

    SUM(is_final_season)                                        AS series_finales,
    SUM(is_final_season AND finale * rest_n > rest_sum)         AS series_finale_rises,
    SUM(is_final_season AND finale * rest_n = rest_sum)         AS series_finale_ties,
    -- AVG ignores NULLs, so a CASE with no ELSE restricts it to final seasons.
    ROUND(100.0 * AVG(CASE WHEN is_final_season
                           THEN finale * rest_n > rest_sum END), 1) AS pct_series_finale_rises
FROM seasons;
