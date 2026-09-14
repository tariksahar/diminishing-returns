-- The headline: what share of shows clearly decline, stay flat, or clearly rise.
--
-- README: 16.9% clearly decline, 57.4% are essentially flat, 25.7% clearly rise.
-- A show "clearly" moves when its slope reaches half a rating point across its
-- run in either direction (the 0.5 threshold from docs/decisions.md).
--
-- Also the median slope (+0.109, the essay's "drifts slightly up").
-- SQLite has no MEDIAN() function, so it is built from window functions.

WITH
    classified AS (
        SELECT
            slope,
            -- CASE is SQL's if / else if / else. Conditions are tried top to
            -- bottom and the first true one wins, so the middle branch does
            -- not have to repeat "slope > -0.5".
            CASE
                WHEN slope <= -0.5 THEN 'clear decline'
                WHEN slope <   0.5 THEN 'flat'
                ELSE                    'clear rise'
            END AS trend
        FROM show_slopes
    ),

    split AS (
        SELECT
            COUNT(*) AS shows,
            -- AVG over a 1/0 column is the share of rows where it is 1.
            ROUND(100.0 * AVG(trend = 'clear decline'), 1) AS pct_clear_decline,
            ROUND(100.0 * AVG(trend = 'flat'),          1) AS pct_flat,
            ROUND(100.0 * AVG(trend = 'clear rise'),    1) AS pct_clear_rise,
            SUM(trend = 'clear decline')                   AS n_clear_decline
        FROM classified
    ),

    -- The median is the middle value of the sorted list. Number the slopes in
    -- order and count them; with 3,234 shows (an even count) the median is the
    -- mean of positions 1,617 and 1,618. The two conditions below pick exactly
    -- those two positions when the count is even, and the single middle one
    -- when it is odd.
    ordered AS (
        SELECT
            slope,
            ROW_NUMBER() OVER (ORDER BY slope) AS position,
            COUNT(*)     OVER ()               AS total
        FROM show_slopes
    ),

    median AS (
        SELECT AVG(slope) AS median_slope
        FROM ordered
        WHERE position IN ((total + 1) / 2, (total + 2) / 2)
    )

-- Both CTEs hold one row, so joining them without a condition (CROSS JOIN)
-- just places the columns side by side.
SELECT split.*, ROUND(median.median_slope, 3) AS median_slope
FROM split
CROSS JOIN median;
