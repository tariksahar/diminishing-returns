"""Test whether the 'peak season' is really season 2, or whether it moves
toward the MIDDLE as shows get longer (which would show up as season 2 only
because most shows in the dataset are short).

For each season-count group, report where the best season falls both in
ABSOLUTE terms (season number) and NORMALIZED terms (0 = first season,
1 = last). If the middle-peak reading is right, the absolute peak grows with
length while the normalized peak stays near the middle."""

import numpy as np
import pandas as pd

df = pd.read_parquet("data/processed/episodes.parquet")

rows = []
for show_id, g in df.groupby("show_tconst"):
    season_means = g.groupby("season_number")["average_rating"].mean()
    seasons_sorted = sorted(season_means.index)
    n_season = len(seasons_sorted)
    best_season = season_means.idxmax()
    best_rank = seasons_sorted.index(best_season) + 1   # 1..n_season
    best_frac = (best_rank - 1) / (n_season - 1) if n_season > 1 else np.nan
    rows.append({"show_id": show_id, "n_season": n_season,
                 "best_rank": best_rank, "best_frac": best_frac})

bs = pd.DataFrame(rows)

print("=" * 72)
print("PEAK LOCATION BY SEASON COUNT")
print("=" * 72)
print(f"{'seasons':<9}{'shows':<8}{'mean abs':<11}{'mean norm':<12}{'median norm':<14}{'modal peak season'}")
for ns in [2, 3, 4, 5, 6, 7]:
    sub = bs[bs["n_season"] == ns]
    if len(sub) < 10:
        continue
    mode_season = sub["best_rank"].mode().iloc[0]
    print(f"{ns:<9}{len(sub):<8}{sub['best_rank'].mean():<11.2f}"
          f"{sub['best_frac'].mean():<12.3f}{sub['best_frac'].median():<14.3f}S{mode_season}")
longsub = bs[bs["n_season"] >= 8]
print(f"{'8+':<9}{len(longsub):<8}{longsub['best_rank'].mean():<11.2f}"
      f"{longsub['best_frac'].mean():<12.3f}{longsub['best_frac'].median():<14.3f}-")
print()
print("Expectation: if the peak really tracks the middle, 'mean abs' grows with")
print("show length while 'mean norm' stays near 0.5.")
print()

print("=" * 72)
print("CHECK: is the peak CONCENTRATED in the middle, or just averaging there?")
print("(shows with >= 5 seasons only, where 'middle' is meaningful)")
print("=" * 72)
mid = bs[bs["n_season"] >= 5]
print(f"shows: {len(mid)}")
print(f"mean normalized peak position:   {mid['best_frac'].mean():.3f}  (0.5 = exact middle)")
print(f"median normalized peak position: {mid['best_frac'].median():.3f}")
print()
print("Normalized peak position, by quantile:")
for q in [0.1, 0.25, 0.5, 0.75, 0.9]:
    print(f"  p{int(q*100)}: {mid['best_frac'].quantile(q):.3f}")
print()
# How many peak in the first / middle / last third of their run.
first = (mid["best_frac"] <= 1/3).mean()
middle = ((mid["best_frac"] > 1/3) & (mid["best_frac"] < 2/3)).mean()
last = (mid["best_frac"] >= 2/3).mean()
print(f"peaks in the first third:  {100*first:.1f}%")
print(f"peaks in the middle third: {100*middle:.1f}%")
print(f"peaks in the last third:   {100*last:.1f}%")
print()
print("Note: the mean sitting at ~0.5 does NOT mean peaks cluster in the middle --")
print("the middle third is the LEAST common location; the two ends roughly balance.")
