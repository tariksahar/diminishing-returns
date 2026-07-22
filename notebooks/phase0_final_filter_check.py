"""Apply ALL six finalized inclusion rules together and report the funnel:
how many shows/episodes survive each step, plus sanity checks (ongoing count,
missing-genres count, example shows, season distribution). This is the shape
the processed table will have, verified before writing src/build.py."""

import pandas as pd

# --- Load and base-join (same as build will do) ---
episodes = pd.read_csv("data/raw/title.episode.tsv.gz", sep="\t", na_values="\\N", dtype={"tconst": str, "parentTconst": str})
episodes["seasonNumber"] = pd.to_numeric(episodes["seasonNumber"], errors="coerce")
episodes["episodeNumber"] = pd.to_numeric(episodes["episodeNumber"], errors="coerce")
episodes = episodes.dropna(subset=["seasonNumber", "episodeNumber"])
ratings = pd.read_csv("data/raw/title.ratings.tsv.gz", sep="\t", na_values="\\N", dtype={"tconst": str})
ep = episodes.merge(ratings, on="tconst", how="inner")
basics = pd.read_csv(
    "data/raw/title.basics.tsv.gz", sep="\t", na_values="\\N",
    usecols=["tconst", "titleType", "primaryTitle", "startYear", "endYear", "genres"], dtype=str,
)
series = basics[basics["titleType"].isin(["tvSeries", "tvMiniSeries"])]
full = ep.merge(series.rename(columns={"tconst": "parentTconst"}), on="parentTconst", how="inner")

# --- Per-show aggregate to evaluate the rules ---
stats = full.groupby("parentTconst").agg(
    show_name=("primaryTitle", "first"),
    genres=("genres", "first"),
    end_year=("endYear", "first"),
    episode_count=("tconst", "count"),
    season_count=("seasonNumber", "nunique"),
    mean_votes=("numVotes", "mean"),
).reset_index()

EXCLUDED = ["Game-Show", "Reality-TV", "Talk-Show", "News"]

def excluded_genre(g):
    if pd.isna(g):
        return False
    parts = g.split(",")
    return any(x in parts for x in EXCLUDED)

def documentary_over_100(row):
    g = row["genres"]
    if pd.isna(g):
        return False
    return ("Documentary" in g.split(",")) and (row["episode_count"] >= 100)

print("=" * 60)
print("FILTER FUNNEL (per show)")
print("=" * 60)
n0 = len(stats)
print(f"0. all shows with >=1 rated, ordered episode: {n0:,}")

s1 = stats[stats["episode_count"] >= 13]
print(f"1. + episode_count >= 13:                    {len(s1):,}")

s2 = s1[s1["season_count"] >= 2]
print(f"2. + season_count >= 2:                       {len(s2):,}")

s3 = s2[s2["mean_votes"] >= 50]
print(f"3. + mean_votes/episode >= 50:                {len(s3):,}")

s4 = s3[~s3["genres"].apply(excluded_genre)]
print(f"4. - excluded genres (GameShow/Reality/Talk/News): {len(s4):,}")

s5 = s4[~s4.apply(documentary_over_100, axis=1)]
print(f"5. - Documentary with >=100 episodes:         {len(s5):,}")

final = s5
print()
print(f"FINAL show count:    {len(final):,}")
final_episodes = full[full["parentTconst"].isin(final["parentTconst"])]
print(f"FINAL episode count: {len(final_episodes):,}")

print()
print("=" * 60)
print("SANITY CHECKS")
print("=" * 60)
ongoing = final["end_year"].isna().sum()
print(f"ongoing (endYear missing): {ongoing:,}  ({100*ongoing/len(final):.1f}%)")
missing_genres = final["genres"].isna().sum()
print(f"missing genres: {missing_genres:,}")

print()
print("season_count distribution among final shows:")
print(final["season_count"].describe())

print()
print("episode_count distribution among final shows:")
print(final["episode_count"].describe())

print()
print("Example shows still present:")
for name in ["Friends", "Game of Thrones", "The Sopranos"]:
    rows = final[final["show_name"] == name]
    if len(rows):
        r = rows.sort_values("episode_count", ascending=False).iloc[0]
        print(f"  {name}: {int(r['episode_count'])} episodes, {int(r['season_count'])} seasons -> IN")
    else:
        print(f"  {name}: NOT IN final set")

print()
print("10 shows with missing genres (edge case, if any):")
mg = final[final["genres"].isna()].head(10)
for _, r in mg.iterrows():
    print(f"  {r['show_name']} ({int(r['episode_count'])} ep)")
