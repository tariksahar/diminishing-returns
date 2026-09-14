-- "But my shows declined": clear decline by audience size.
--
-- README: clear decline climbs from about 15% among obscure shows to 43% among
-- the 60 household names. Audience size is a show's total votes across all its
-- episodes, cut into four tiers.

WITH tiered AS (
    SELECT
        slope,
        CASE
            WHEN total_votes <     5000 THEN 1
            WHEN total_votes <    50000 THEN 2
            WHEN total_votes <   500000 THEN 3
            ELSE                             4
        END AS tier
    FROM show_slopes
)

SELECT
    tier,
    CASE tier
        WHEN 1 THEN 'under 5k votes'
        WHEN 2 THEN '5k to 50k'
        WHEN 3 THEN '50k to 500k'
        ELSE        '500k and over'
    END                                          AS audience,
    COUNT(*)                                     AS shows,
    ROUND(100.0 * AVG(slope <= -0.5), 1)         AS pct_clear_decline
FROM tiered
GROUP BY tier
ORDER BY tier;
