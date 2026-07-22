"""Explore additional filter candidates on top of the draft thresholds:
ongoing shows (missing endYear), adult content, season-0 specials, and which
genres dominate the highest episode-count shows."""

import pandas as pd

episodes = pd.read_csv("data/raw/title.episode.tsv.gz", sep="\t", na_values="\\N", dtype={"tconst": str, "parentTconst": str})
episodes["seasonNumber"] = pd.to_numeric(episodes["seasonNumber"], errors="coerce")
episodes["episodeNumber"] = pd.to_numeric(episodes["episodeNumber"], errors="coerce")
episodes = episodes.dropna(subset=["seasonNumber", "episodeNumber"])
ratings = pd.read_csv("data/raw/title.ratings.tsv.gz", sep="\t", na_values="\\N", dtype={"tconst": str})
ep = episodes.merge(ratings, on="tconst", how="inner")

basics = pd.read_csv(
    "data/raw/title.basics.tsv.gz",
    sep="\t",
    na_values="\\N",
    usecols=["tconst", "titleType", "primaryTitle", "startYear", "endYear", "isAdult", "genres"],
    dtype=str,
)
basics["isAdult"] = pd.to_numeric(basics["isAdult"], errors="coerce")
series = basics[basics["titleType"].isin(["tvSeries", "tvMiniSeries"])]
full = ep.merge(series.rename(columns={"tconst": "parentTconst"}), on="parentTconst", how="inner")

stats = full.groupby("parentTconst").agg(
    show_name=("primaryTitle", "first"),
    genres=("genres", "first"),
    end_year=("endYear", "first"),
    is_adult=("isAdult", "first"),
    episode_count=("tconst", "count"),
    mean_votes=("numVotes", "mean"),
    specials_count=("seasonNumber", lambda s: (s == 0).sum()),
).reset_index()

keep = stats[(stats["episode_count"] >= 13) & (stats["mean_votes"] >= 50)].copy()
print(f"Shows passing the current threshold: {len(keep):,}")
print()

# 1. Still airing? (missing endYear = possibly still ongoing)
ongoing = keep["end_year"].isna().sum()
print(f"endYear missing (still airing / end unknown): {ongoing:,}  ({100 * ongoing / len(keep):.1f}%)")
ended = len(keep) - ongoing
print(f"endYear present (can be treated as ended): {ended:,}  ({100 * ended / len(keep):.1f}%)")
print()

# 2. Adult content
adult_count = (keep["is_adult"] == 1).sum()
print(f"Shows with isAdult == 1: {adult_count:,}")
print()

# 3. Specials (seasonNumber == 0)
has_specials = (keep["specials_count"] > 0).sum()
print(f"Shows with at least 1 'season 0' (special): {has_specials:,}")
print()

# 4. What are the 15 highest episode-count shows?
print("Top 15 shows by episode count (with genres):")
top15 = keep.sort_values("episode_count", ascending=False).head(15)
for _, r in top15.iterrows():
    print(f"  {r['show_name']:<30} {int(r['episode_count']):>5} episodes   genres: {r['genres']}")
