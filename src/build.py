"""Phase 1 build script.

Reads the three raw IMDb tables from data/raw/, joins them into one row per
rated episode, applies the six finalized inclusion filters from
docs/decisions.md (in order), flags ongoing shows, and writes the resulting
episode-level table to data/processed/episodes.parquet.

Usage:
    python src/build.py
"""

import os

import pandas as pd

RAW_DIR = "data/raw"
OUTPUT_PATH = "data/processed/episodes.parquet"

EXCLUDED_GENRES = {"Game-Show", "Reality-TV", "Talk-Show", "News"}
MIN_EPISODES = 13
MIN_SEASONS = 2
MIN_MEAN_VOTES = 50
DOCUMENTARY_EPISODE_CAP = 100


def load_episodes():
    """title.episode.tsv.gz: one row per episode, giving its parent show
    (parentTconst) and its position within that show (season/episode
    number). Rows without a usable season/episode number can't be placed on
    a trajectory, so they're dropped here before anything else."""
    episodes = pd.read_csv(
        f"{RAW_DIR}/title.episode.tsv.gz",
        sep="\t",
        na_values="\\N",
        dtype={"tconst": str, "parentTconst": str},
    )
    episodes["seasonNumber"] = pd.to_numeric(episodes["seasonNumber"], errors="coerce")
    episodes["episodeNumber"] = pd.to_numeric(episodes["episodeNumber"], errors="coerce")
    before = len(episodes)
    episodes = episodes.dropna(subset=["seasonNumber", "episodeNumber"])
    print(f"title.episode: {before:,} rows -> {len(episodes):,} with a valid season/episode number")
    return episodes


def load_ratings():
    """title.ratings.tsv.gz: one row per title (movies, shows, episodes all
    mixed together) with its IMDb average rating and vote count."""
    return pd.read_csv(
        f"{RAW_DIR}/title.ratings.tsv.gz",
        sep="\t",
        na_values="\\N",
        dtype={"tconst": str},
    )


def load_series_basics():
    """title.basics.tsv.gz: one row per title of any type (movie, episode,
    short, tvSeries, ...). We only want the show-level rows here, filtered
    to titleType in {tvSeries, tvMiniSeries} -- this is inclusion rule 1.
    Only the columns we actually use are read, since this file is the
    largest of the three (~214MB) and full-width parsing is slow."""
    basics = pd.read_csv(
        f"{RAW_DIR}/title.basics.tsv.gz",
        sep="\t",
        na_values="\\N",
        usecols=["tconst", "titleType", "primaryTitle", "startYear", "endYear", "genres"],
        dtype=str,
    )
    series = basics[basics["titleType"].isin(["tvSeries", "tvMiniSeries"])].copy()
    print(f"title.basics: {len(basics):,} titles total -> {len(series):,} tvSeries/tvMiniSeries (rule 1)")
    return series


def build_episode_table():
    """Join episodes -> ratings -> parent show info into one row per rated
    episode. Both joins are inner joins on purpose: an episode with no
    rating can't be plotted on a trajectory, and an episode whose parent
    show isn't a tvSeries/tvMiniSeries (rule 1) doesn't belong in scope."""
    episodes = load_episodes()
    ratings = load_ratings()
    ep = episodes.merge(ratings, on="tconst", how="inner")
    print(f"episodes with a rating: {len(ep):,}")

    series = load_series_basics()
    full = ep.merge(series.rename(columns={"tconst": "parentTconst"}), on="parentTconst", how="inner")
    print(f"episodes belonging to a tvSeries/tvMiniSeries: {len(full):,}")
    return full


def show_level_stats(full):
    """Collapse to one row per show with the numbers the remaining five
    filters need: how many rated episodes it has, how many distinct
    seasons, and its mean vote count per episode."""
    return full.groupby("parentTconst").agg(
        show_name=("primaryTitle", "first"),
        genres=("genres", "first"),
        end_year=("endYear", "first"),
        episode_count=("tconst", "count"),
        season_count=("seasonNumber", "nunique"),
        mean_votes=("numVotes", "mean"),
    ).reset_index()


def has_excluded_genre(genre_string):
    """True if any of the show's IMDb genres (comma-separated) is one of
    the four non-narrative genres excluded by rule 5."""
    if pd.isna(genre_string):
        return False
    return any(g in EXCLUDED_GENRES for g in genre_string.split(","))


def is_documentary_over_cap(row):
    """True only for Documentary-tagged shows with >= 100 episodes -- rule
    6's special case, separating season-based story documentaries (kept)
    from long-running anthology/magazine strands (dropped)."""
    if pd.isna(row["genres"]):
        return False
    return "Documentary" in row["genres"].split(",") and row["episode_count"] >= DOCUMENTARY_EPISODE_CAP


def apply_inclusion_filters(full):
    """Apply inclusion rules 2-6 from docs/decisions.md in order (rule 1,
    titleType, was already applied while building the joined table), on the
    show-level aggregate, then keep only the episodes whose show survives
    all of them. Printing the funnel makes every rule's individual effect
    visible instead of hiding it inside one combined condition."""
    stats = show_level_stats(full)
    print("\nFILTER FUNNEL (per show)")
    print(f"0. shows with >=1 rated, season/episode-numbered episode: {len(stats):,}")

    stats = stats[stats["episode_count"] >= MIN_EPISODES]
    print(f"2. + episode_count >= {MIN_EPISODES}: {len(stats):,}")

    stats = stats[stats["season_count"] >= MIN_SEASONS]
    print(f"3. + season_count >= {MIN_SEASONS}: {len(stats):,}")

    stats = stats[stats["mean_votes"] >= MIN_MEAN_VOTES]
    print(f"4. + mean votes/episode >= {MIN_MEAN_VOTES}: {len(stats):,}")

    stats = stats[~stats["genres"].apply(has_excluded_genre)]
    print(f"5. - excluded genres {sorted(EXCLUDED_GENRES)}: {len(stats):,}")

    stats = stats[~stats.apply(is_documentary_over_cap, axis=1)]
    print(f"6. - Documentary with >= {DOCUMENTARY_EPISODE_CAP} episodes: {len(stats):,}")

    kept_show_ids = set(stats["parentTconst"])
    result = full[full["parentTconst"].isin(kept_show_ids)].copy()
    print(f"\nFinal shows: {len(stats):,}  |  Final episodes: {len(result):,}")
    return result


def add_ongoing_flag(df):
    """A show is 'ongoing' when IMDb has no endYear for it, meaning IMDb
    hasn't marked it as finished. This is a proxy, not a certainty (see
    deferred item 3 in docs/decisions.md), but a spot-check during Phase 0
    confirmed it's mostly genuinely still-airing shows. Flagged, not
    dropped: kept for descriptive analysis, must be excluded later from the
    'final season curse' analysis where an unfinished show has no real
    final season yet (deferred item 2)."""
    df["ongoing"] = df["endYear"].isna()
    return df


def add_overall_order(df):
    """A 1-based episode index within each show, ordered by season number
    then episode number. This gives every episode a single position on its
    show's trajectory that ignores season boundaries -- needed later to
    plot/regress rating against 'how far into the show' an episode is."""
    df = df.sort_values(["parentTconst", "seasonNumber", "episodeNumber"])
    df["overall_order"] = df.groupby("parentTconst").cumcount() + 1
    return df


def finalize_columns(df):
    """Rename to clear snake_case names, tighten numeric dtypes (year and
    season/episode columns arrive as strings/floats from the raw parse),
    and keep only the columns the processed table needs. numVotes is kept
    per episode on purpose -- deferred item 1 plans to use it as a Phase
    2/3 weighting signal for noisy, low-vote episodes, not to filter here."""
    df = df.rename(columns={
        "tconst": "episode_tconst",
        "parentTconst": "show_tconst",
        "primaryTitle": "show_title",
        "startYear": "start_year",
        "endYear": "end_year",
        "seasonNumber": "season_number",
        "episodeNumber": "episode_number",
        "averageRating": "average_rating",
        "numVotes": "num_votes",
    })
    df["start_year"] = pd.to_numeric(df["start_year"], errors="coerce").astype("Int64")
    df["end_year"] = pd.to_numeric(df["end_year"], errors="coerce").astype("Int64")
    df["season_number"] = df["season_number"].astype("Int64")
    df["episode_number"] = df["episode_number"].astype("Int64")

    columns = [
        "episode_tconst", "show_tconst", "show_title", "genres",
        "start_year", "end_year", "ongoing",
        "season_number", "episode_number", "overall_order",
        "average_rating", "num_votes",
    ]
    return df[columns]


def main():
    full = build_episode_table()
    filtered = apply_inclusion_filters(full)
    filtered = add_ongoing_flag(filtered)
    filtered = add_overall_order(filtered)
    result = finalize_columns(filtered)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    result.to_parquet(OUTPUT_PATH, index=False)
    print(f"\nSaved {len(result):,} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
