-- Phase 1 build, in SQL.
--
-- The same job src/build.py does in pandas: join the three raw IMDb tables into
-- one row per rated episode, apply the six inclusion rules from
-- docs/decisions.md, flag ongoing shows and number each show's episodes. The
-- result should be row-for-row identical to data/processed/episodes.parquet;
-- tests/test_sql_build.py is what verifies that.
--
-- Three tables are written:
--   stg_rated_episodes  every rated, numbered episode of every tvSeries /
--                       tvMiniSeries, before any show-level filter.
--   stg_show_stats      one row per show from that table, with the numbers
--                       the filters test. Kept as a table so the filter
--                       funnel (sql/filter_funnel.sql) can count from it.
--   episodes            the final analysis table.
--
-- Run with:  python sql/run_build.py


-- ---------------------------------------------------------------------------
-- Step 1. Rated episodes of real shows (rule 1: titleType)
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS stg_rated_episodes;

CREATE TABLE stg_rated_episodes AS
WITH
    -- An episode with no season or episode number cannot be placed on a
    -- trajectory, so it is dropped before anything else.
    numbered_episodes AS (
        SELECT tconst, parentTconst, seasonNumber, episodeNumber
        FROM raw_episode
        WHERE seasonNumber IS NOT NULL
          AND episodeNumber IS NOT NULL
    ),

    -- Show-level rows only. title.basics mixes movies, shorts, episodes and
    -- shows in one table; this is inclusion rule 1.
    series AS (
        SELECT tconst, primaryTitle, startYear, endYear, genres
        FROM raw_basics
        WHERE titleType IN ('tvSeries', 'tvMiniSeries')
    )

-- Both joins are INNER on purpose, as in build.py: an episode without a rating
-- has nothing to plot, and an episode whose parent is not a series is out of
-- scope. An inner join drops both kinds of row without a separate filter.
SELECT
    e.tconst          AS episode_tconst,
    e.parentTconst    AS show_tconst,
    s.primaryTitle    AS show_title,
    s.genres          AS genres,
    s.startYear       AS start_year,
    s.endYear         AS end_year,
    e.seasonNumber    AS season_number,
    e.episodeNumber   AS episode_number,
    r.averageRating   AS average_rating,
    r.numVotes        AS num_votes
FROM numbered_episodes AS e
JOIN raw_ratings       AS r ON r.tconst = e.tconst
JOIN series            AS s ON s.tconst = e.parentTconst;


-- ---------------------------------------------------------------------------
-- Step 2. One row per show, holding every number rules 2-6 need
-- ---------------------------------------------------------------------------
-- GROUP BY collapses all of a show's episode rows into one row; each aggregate
-- (COUNT, AVG, ...) is computed over the rows that were collapsed together.
-- genres is the same on every episode row of a show (it comes from the show's
-- own title.basics row), so MAX() simply picks that one value.
DROP TABLE IF EXISTS stg_show_stats;

CREATE TABLE stg_show_stats AS
SELECT
    show_tconst,
    MAX(genres)                   AS genres,
    COUNT(*)                      AS episode_count,
    COUNT(DISTINCT season_number) AS season_count,
    AVG(num_votes)                AS mean_votes
FROM stg_rated_episodes
GROUP BY show_tconst;


-- ---------------------------------------------------------------------------
-- Step 3. Show-level filters (rules 2-6) and the final episode table
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS episodes;

CREATE TABLE episodes AS
WITH
    kept_shows AS (
        SELECT show_tconst
        FROM stg_show_stats
        WHERE episode_count >= 13        -- rule 2
          AND season_count  >= 2         -- rule 3
          AND mean_votes    >= 50        -- rule 4
          -- Rule 5. genres is a comma-separated list such as
          -- 'Comedy,Drama,News'. Wrapping both the list and the genre in
          -- commas makes LIKE match whole genre names only.
          -- COALESCE matters: a NULL genres would make the whole LIKE
          -- expression NULL, NOT NULL is still NULL, and WHERE drops NULL rows.
          -- build.py keeps a show with no genres, so NULL becomes '' here.
          AND NOT (
                ',' || COALESCE(genres, '') || ',' LIKE '%,Game-Show,%'
             OR ',' || COALESCE(genres, '') || ',' LIKE '%,Reality-TV,%'
             OR ',' || COALESCE(genres, '') || ',' LIKE '%,Talk-Show,%'
             OR ',' || COALESCE(genres, '') || ',' LIKE '%,News,%'
          )
          -- Rule 6. Documentaries are kept only below 100 episodes.
          AND NOT (
                ',' || COALESCE(genres, '') || ',' LIKE '%,Documentary,%'
            AND episode_count >= 100
          )
    )

SELECT
    e.episode_tconst,
    e.show_tconst,
    e.show_title,
    e.genres,
    e.start_year,
    e.end_year,
    -- IMDb leaves endYear empty for a show it has not marked finished.
    -- SQLite has no boolean type: this stores 1 or 0.
    e.end_year IS NULL AS ongoing,
    e.season_number,
    e.episode_number,
    -- A window function: number the rows 1, 2, 3 ... separately inside each
    -- show (PARTITION BY), in season-then-episode order (ORDER BY). Unlike
    -- GROUP BY it does not collapse the rows; every episode keeps its own row
    -- and just gains its position in the show.
    ROW_NUMBER() OVER (
        PARTITION BY e.show_tconst
        ORDER BY e.season_number, e.episode_number
    ) AS overall_order,
    e.average_rating,
    e.num_votes
FROM stg_rated_episodes AS e
JOIN kept_shows         AS k ON k.show_tconst = e.show_tconst
ORDER BY e.show_tconst, overall_order;
