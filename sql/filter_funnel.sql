-- The inclusion-filter funnel: how many shows survive each rule in turn.
--
-- src/build.py prints this funnel while it filters. Here it is one query over
-- stg_show_stats. Each column adds one more rule to the previous column's
-- conditions, so the numbers can only shrink from left to right.
--
-- The trick is conditional counting: SUM(CASE WHEN <condition> THEN 1 ELSE 0 END)
-- adds 1 for every show that meets the condition and 0 for the rest, which
-- counts several different subsets in a single pass over the table.

WITH flags AS (
    SELECT
        episode_count >= 13                                  AS r2,
        season_count  >= 2                                   AS r3,
        mean_votes    >= 50                                  AS r4,
        NOT (   ',' || COALESCE(genres, '') || ',' LIKE '%,Game-Show,%'
             OR ',' || COALESCE(genres, '') || ',' LIKE '%,Reality-TV,%'
             OR ',' || COALESCE(genres, '') || ',' LIKE '%,Talk-Show,%'
             OR ',' || COALESCE(genres, '') || ',' LIKE '%,News,%')  AS r5,
        NOT (    ',' || COALESCE(genres, '') || ',' LIKE '%,Documentary,%'
             AND episode_count >= 100)                       AS r6
    FROM stg_show_stats
)
SELECT
    COUNT(*)                                                             AS all_shows,
    SUM(CASE WHEN r2                               THEN 1 ELSE 0 END)    AS after_rule2_episodes,
    SUM(CASE WHEN r2 AND r3                        THEN 1 ELSE 0 END)    AS after_rule3_seasons,
    SUM(CASE WHEN r2 AND r3 AND r4                 THEN 1 ELSE 0 END)    AS after_rule4_votes,
    SUM(CASE WHEN r2 AND r3 AND r4 AND r5          THEN 1 ELSE 0 END)    AS after_rule5_genres,
    SUM(CASE WHEN r2 AND r3 AND r4 AND r5 AND r6   THEN 1 ELSE 0 END)    AS after_rule6_documentary
FROM flags;
