"""Phase 0 feasibility check: download-free join of the three IMDb TSV files,
plot three example show trajectories, and inspect the distribution of episodes
and votes per show to derive draft inclusion thresholds."""

import pandas as pd
import matplotlib.pyplot as plt

RAW = "data/raw"

# 1. Episode -> show mapping: each episode carries which show (parentTconst)
#    it belongs to and its season/episode number within that show.
episodes = pd.read_csv(
    f"{RAW}/title.episode.tsv.gz",
    sep="\t",
    na_values="\\N",
    dtype={"tconst": str, "parentTconst": str},
)
episodes["seasonNumber"] = pd.to_numeric(episodes["seasonNumber"], errors="coerce")
episodes["episodeNumber"] = pd.to_numeric(episodes["episodeNumber"], errors="coerce")
episodes_clean = episodes.dropna(subset=["seasonNumber", "episodeNumber"])
print(f"title.episode total rows: {len(episodes):,}")
print(f"rows with complete season/episode numbers: {len(episodes_clean):,}")

# 2. Ratings: average rating and vote count for every title (episodes included).
ratings = pd.read_csv(
    f"{RAW}/title.ratings.tsv.gz",
    sep="\t",
    na_values="\\N",
    dtype={"tconst": str},
)

# 3. Episode + rating join (inner): only episodes with at least 1 vote survive.
ep_ratings = episodes_clean.merge(ratings, on="tconst", how="inner")
print(f"episodes with a rating (after join): {len(ep_ratings):,}")

# 4. Show identity: from title.basics keep only tvSeries / tvMiniSeries.
basics = pd.read_csv(
    f"{RAW}/title.basics.tsv.gz",
    sep="\t",
    na_values="\\N",
    usecols=["tconst", "titleType", "primaryTitle", "startYear", "genres"],
    dtype=str,
)
series = basics[basics["titleType"].isin(["tvSeries", "tvMiniSeries"])].copy()
print(f"total tvSeries/tvMiniSeries: {len(series):,}")

# 5. Attach show info to the episode+rating table (parentTconst = the show's tconst).
full = ep_ratings.merge(
    series.rename(columns={"tconst": "parentTconst"}),
    on="parentTconst",
    how="inner",
)
print(f"final (rated + show-labelled) episode count: {len(full):,}")

# 6. Overall order: a 1-based episode index within each show, by season then episode.
full = full.sort_values(["parentTconst", "seasonNumber", "episodeNumber"])
full["overall_order"] = full.groupby("parentTconst").cumcount() + 1

# 7. Locate and plot the three example shows.
examples = [("Friends", "1994"), ("Game of Thrones", "2011"), ("The Sopranos", "1999")]

fig, axes = plt.subplots(len(examples), 1, figsize=(9, 10), sharex=False)

for ax, (name, year) in zip(axes, examples):
    subset = full[(full["primaryTitle"] == name) & (full["startYear"] == year)]
    subset = subset.sort_values("overall_order")
    print(f"{name} ({year}) -> episodes found: {len(subset)}")
    ax.plot(subset["overall_order"], subset["averageRating"], marker="o", markersize=2, linewidth=0.8)
    ax.set_title(f"{name} ({year}) - rating per episode")
    ax.set_xlabel("Overall episode order")
    ax.set_ylabel("Rating (averageRating)")
    ax.set_ylim(0, 10)
    ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig("figures/phase0_example_curves.png", dpi=150)
print("Saved figure: figures/phase0_example_curves.png")

# 8. Per-show distribution: how many episodes, and how many votes per episode on average.
show_stats = full.groupby("parentTconst").agg(
    show_name=("primaryTitle", "first"),
    genres=("genres", "first"),
    start_year=("startYear", "first"),
    episode_count=("tconst", "count"),
    total_votes=("numVotes", "sum"),
    mean_votes=("numVotes", "mean"),
    median_votes=("numVotes", "median"),
).reset_index()

print()
print(f"Distinct shows with at least 1 rated episode: {len(show_stats):,}")
print()
print("Episode-count distribution:")
print(show_stats["episode_count"].describe())
print()
for n in [1, 2, 3, 5, 8, 10, 13, 20, 30]:
    count = (show_stats["episode_count"] >= n).sum()
    pct = 100 * count / len(show_stats)
    print(f"  >= {n} episodes: {count:,} shows ({pct:.1f}%)")

print()
print("Mean-votes-per-episode distribution:")
print(show_stats["mean_votes"].describe())
print()
for v in [10, 25, 50, 100, 500, 1000]:
    count = (show_stats["mean_votes"] >= v).sum()
    pct = 100 * count / len(show_stats)
    print(f"  mean votes/episode >= {v}: {count:,} shows ({pct:.1f}%)")

# Applying both conditions together (rough draft).
combo = show_stats[(show_stats["episode_count"] >= 8) & (show_stats["mean_votes"] >= 100)]
print()
print(f"Draft: >=8 episodes AND mean votes/episode >=100 -> {len(combo):,} shows")

fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
ax1.hist(show_stats["episode_count"].clip(upper=100), bins=50)
ax1.set_xlabel("Episode count (clipped at 100)")
ax1.set_ylabel("Number of shows")
ax1.set_title("Episodes per show")

ax2.hist(show_stats["mean_votes"].clip(upper=2000), bins=50)
ax2.set_xlabel("Mean votes per episode (clipped at 2000)")
ax2.set_ylabel("Number of shows")
ax2.set_title("Mean votes per show")

plt.tight_layout()
plt.savefig("figures/phase0_threshold_distribution.png", dpi=150)
print("Saved figure: figures/phase0_threshold_distribution.png")
