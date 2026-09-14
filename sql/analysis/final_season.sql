-- The final-season curse: is a show's last season worse than the rest of it?
--
-- README: almost a coin flip -- 50.5% of ended shows have a lower final season,
-- 49.2% a higher one, and only 12.6% lose half a point or more. Ten shows are
-- exactly level. Ongoing shows are left out: they have no final season yet.
--
-- The comparison is between two means, final_sum / final_n and
-- rest_sum / rest_n. Cross-multiplying removes the division:
--     delta = final_sum/final_n - rest_sum/rest_n
--     sign(delta) = sign(final_sum * rest_n - rest_sum * final_n)
-- With ratings in whole tenths that difference is an integer, so the ten ties
-- come out as exactly zero. tests/test_headline_numbers.py explains why that
-- matters: in floating point the same ties show up as 6, 8 or 10 depending on
-- how they were computed.
--
-- "Loses half a point or more" (delta <= -0.5) in the same integer terms:
-- multiply both sides by final_n * rest_n, and 0.5 points is 5 tenths.

WITH
    marked AS (
        SELECT
            show_tconst,
            CAST(ROUND(average_rating * 10) AS INTEGER)       AS rating_tenths,
            season_number = MAX(season_number) OVER (PARTITION BY show_tconst)
                                                              AS in_final_season
        FROM episodes
        WHERE ongoing = 0
    ),

    per_show AS (
        SELECT
            show_tconst,
            SUM(CASE WHEN in_final_season     THEN rating_tenths END) AS final_sum,
            SUM(in_final_season)                                      AS final_n,
            SUM(CASE WHEN NOT in_final_season THEN rating_tenths END) AS rest_sum,
            SUM(NOT in_final_season)                                  AS rest_n
        FROM marked
        GROUP BY show_tconst
        -- Every show here has >= 2 seasons, so this never removes one. It is
        -- stated anyway: the comparison is undefined without a "rest".
        HAVING SUM(NOT in_final_season) > 0
    ),

    compared AS (
        SELECT
            final_sum * rest_n - rest_sum * final_n AS scaled_delta,
            final_n * rest_n                        AS scale
        FROM per_show
    )

SELECT
    COUNT(*)                                                     AS ended_shows,
    ROUND(100.0 * AVG(scaled_delta < 0), 1)                      AS pct_final_season_lower,
    ROUND(100.0 * AVG(scaled_delta > 0), 1)                      AS pct_final_season_higher,
    SUM(scaled_delta = 0)                                        AS exactly_level,
    ROUND(100.0 * AVG(scaled_delta <= -5 * scale), 1)            AS pct_loses_half_a_point
FROM compared;
