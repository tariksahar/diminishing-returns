-- Where is a show's single best season?
--
-- README: the last season is the best one more often (37%) than the first (27%).
-- "Best" is the season with the highest mean episode rating. When two seasons
-- tie for the top, the earlier one counts, which is what pandas' idxmax() did
-- in notebooks/phase2_shape.py.
--
-- Season means are computed as SUM(tenths) * 1.0 / COUNT(*): one division of
-- two integers. Two seasons whose means are equal as fractions then get the
-- identical floating-point value, so ties are real ties. (Averaging the
-- decimal ratings directly can leave two equal means 1e-15 apart, and the
-- tie-break then depends on rounding instead of on the rule.)

WITH
    season_means AS (
        SELECT
            show_tconst,
            season_number,
            SUM(CAST(ROUND(average_rating * 10) AS INTEGER)) * 1.0 / COUNT(*) AS mean_tenths
        FROM episodes
        GROUP BY show_tconst, season_number
    ),

    ranked AS (
        SELECT
            show_tconst,
            season_number,
            -- Rank 1 = best mean; among equal means, the lower season number.
            ROW_NUMBER() OVER (
                PARTITION BY show_tconst
                ORDER BY mean_tenths DESC, season_number ASC
            ) AS quality_rank,
            MIN(season_number) OVER (PARTITION BY show_tconst) AS first_season,
            MAX(season_number) OVER (PARTITION BY show_tconst) AS last_season
        FROM season_means
    )

-- Keep only each show's best season, then ask whether it is the first or last.
SELECT
    COUNT(*)                                                AS shows,
    ROUND(100.0 * AVG(season_number = first_season), 1)     AS pct_first_season_best,
    ROUND(100.0 * AVG(season_number = last_season), 1)      AS pct_last_season_best
FROM ranked
WHERE quality_rank = 1;
