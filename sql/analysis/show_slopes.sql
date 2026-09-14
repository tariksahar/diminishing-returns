-- Every show's trend slope: the project's core metric, in pure SQL.
--
-- The Python version (notebooks/phase2_full.py) fits, for each show, a
-- weighted least-squares line through
--     y = average_rating
--     x = (overall_order - 1) / (n - 1)       the episode's position, 0 to 1
--     w = sqrt(num_votes)                     the episode's weight
-- and keeps the slope. A least-squares slope needs no loop and no matrix: it
-- has a closed form made only of sums,
--
--              W * Swxy  -  Swx * Swy
--     slope = ------------------------        W    = sum(w)
--              W * Swxx  -  Swx * Swx         Swx  = sum(w*x),   Swy = sum(w*y)
--                                             Swxy = sum(w*x*y), Swxx = sum(w*x*x)
--
-- and sums are exactly what GROUP BY computes. It is algebraically the same
-- slope as the centred form the Python uses; the two agree to within 1e-9.
--
-- Writes the table show_slopes, which the other analysis queries read.

DROP TABLE IF EXISTS show_slopes;

CREATE TABLE show_slopes AS
WITH
    -- Step 1: each episode's x, y and w. x needs the show's episode count,
    -- which a window function supplies without collapsing the rows.
    points AS (
        SELECT
            show_tconst,
            num_votes,
            -- The 1.0 is not decoration. Both sides of the division are
            -- integers, and SQLite divides integers as integers:
            -- (3 - 1) / (10 - 1) is 0, not 0.222. Multiplying by 1.0 first
            -- makes the arithmetic floating-point.
            (overall_order - 1) * 1.0
                / (COUNT(*) OVER (PARTITION BY show_tconst) - 1) AS x,
            average_rating                                         AS y,
            sqrt(num_votes)                                        AS w
        FROM episodes
    ),

    -- Step 2: collapse each show to the five sums the formula needs.
    sums AS (
        SELECT
            show_tconst,
            COUNT(*)       AS n_episodes,
            SUM(num_votes) AS total_votes,
            SUM(w)         AS W,
            SUM(w * x)     AS Swx,
            SUM(w * y)     AS Swy,
            SUM(w * x * y) AS Swxy,
            SUM(w * x * x) AS Swxx
        FROM points
        GROUP BY show_tconst
    )

-- Step 3: the formula itself. The intercept -- where the line starts, at
-- x = 0 -- follows from the slope: a least-squares line always passes through
-- the weighted means (Swx / W, Swy / W). The app needs it to draw the line.
SELECT
    show_tconst,
    n_episodes,
    total_votes,
    slope,
    (Swy - slope * Swx) / W AS intercept
FROM (
    SELECT sums.*, (W * Swxy - Swx * Swy) / (W * Swxx - Swx * Swx) AS slope
    FROM sums
);
