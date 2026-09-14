"""Phase 2 -- D: final-season-curse analysis.
For ENDED shows only (ongoing == False), compute:
    final_season_mean - rest_of_show_mean
using plain (unweighted) episode-rating means, exactly as decisions.md
specifies. This is a different, more direct metric than the overall trend
slope -- see the documented reasoning (a straight line understates a late,
sharp crash when most episodes sit at a high level)."""

import json

import pandas as pd

df = pd.read_parquet("data/processed/episodes.parquet")
ended = df[~df["ongoing"]]
print(f"Ended shows (ongoing = False): {ended['show_tconst'].nunique():,}")
print()

show_votes = df.groupby("show_tconst")["num_votes"].sum()

records = []
for show_id, g in ended.groupby("show_tconst"):
    final_season = g["season_number"].max()
    fs = g[g["season_number"] == final_season]
    rest = g[g["season_number"] != final_season]
    if len(rest) == 0:
        continue  # shouldn't happen (>=2 seasons guaranteed by build filters) but be safe
    fs_mean = fs["average_rating"].mean()
    rest_mean = rest["average_rating"].mean()
    records.append({
        "show_id": show_id,
        "title": g["show_title"].iloc[0],
        "final_season": int(final_season),
        "final_season_n_ep": len(fs),
        "final_season_mean": float(fs_mean),
        "rest_mean": float(rest_mean),
        "delta": float(fs_mean - rest_mean),
        "total_votes": int(show_votes[show_id]),
        "n_season": int(g["season_number"].nunique()),
    })

res = pd.DataFrame(records)
print(f"Shows analyzed: {len(res):,}")
print()

print("=== OVERALL PICTURE (final-season mean - rest-of-show mean) ===")
print(f"mean delta:   {res['delta'].mean():+.3f}")
print(f"median delta: {res['delta'].median():+.3f}")
print()
# Count each direction directly. Deriving "higher" as len(res) - declining
# silently folds exact ties into the risers, which is how the published 49.4%
# came to be 0.2 points too high.
#
# And compare against a TOLERANCE, not against exact zero. A tie means two
# means of one-decimal ratings are equal as rationals, which float arithmetic
# often cannot represent: four such series land on +/-1e-15 instead of 0.0.
# Testing `== 0` counted 6 ties when there are 10, and `to_json`'s default
# 10-decimal rounding then reported 8 to anything reading the exported file --
# three different answers to one question, all of them artifacts of how zero
# was compared. Anything below this tolerance is zero at the data's precision.
LEVEL_TOL = 1e-9
declining = (res["delta"] < -LEVEL_TOL).sum()
rising = (res["delta"] > LEVEL_TOL).sum()
level = (res["delta"].abs() <= LEVEL_TOL).sum()
print(f"final season LOWER than the rest:  {declining:,}  ({100*declining/len(res):.1f}%)")
print(f"final season HIGHER than the rest: {rising:,}  ({100*rising/len(res):.1f}%)")
print(f"exactly level:                     {level:,}  ({100*level/len(res):.1f}%)")
print()
# The same tolerance at the 0.5 boundary. One ended series lands exactly on
# -0.5, and without it three exact ties were counted as mild drops.
strong_curse = (res["delta"] <= -0.5 + LEVEL_TOL).sum()
mild_curse = ((res["delta"] < -LEVEL_TOL) & (res["delta"] > -0.5 + LEVEL_TOL)).sum()
print(f"clear curse (delta <= -0.5):  {strong_curse:,}  ({100*strong_curse/len(res):.1f}%)")
print(f"mild drop (-0.5 < delta < 0): {mild_curse:,}  ({100*mild_curse/len(res):.1f}%)")
print()
print("Percentiles:")
print(res["delta"].quantile([0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]))
print()

# Compare against the slope metric to show where the two disagree.
slopes = pd.read_json("data/processed/_phase2_slopes_full.json")
merged = res.merge(slopes[["show_id", "slope"]], on="show_id", how="left")
corr = merged[["delta", "slope"]].corr().iloc[0, 1]
print(f"correlation between delta and slope: {corr:+.3f}  (1.0 would mean they measure the same thing)")
print()
# Sanity check against the hand-computed Game of Thrones figures.
got = res[res["title"] == "Game of Thrones"]
print("Game of Thrones row (sanity check):")
print(got.to_string(index=False))
print()

print("=" * 60)
print("15 MOST CURSED SHOWS (min 20k votes)")
print("=" * 60)
pop = res[res["total_votes"] >= 20000].sort_values("delta")
for _, r in pop.head(15).iterrows():
    print(f"  {r['title']:<32} final S{r['final_season']}={r['final_season_mean']:.2f}  "
          f"rest={r['rest_mean']:.2f}  delta={r['delta']:+.2f}")
print()

print("=" * 60)
print("15 STRONGEST FINISHERS (min 20k votes)")
print("=" * 60)
for _, r in pop.sort_values("delta", ascending=False).head(15).iterrows():
    print(f"  {r['title']:<32} final S{r['final_season']}={r['final_season_mean']:.2f}  "
          f"rest={r['rest_mean']:.2f}  delta={r['delta']:+.2f}")

res.to_json("data/processed/_phase2_finalseason_full.json", orient="records")
out = {
    "n": len(res),
    "mean_delta": round(float(res["delta"].mean()), 3),
    "median_delta": round(float(res["delta"].median()), 3),
    "pct_declining": round(100*declining/len(res), 1),
    "pct_strong_curse": round(100*strong_curse/len(res), 1),
    "corr_with_slope": round(float(corr), 3),
}
with open("data/processed/_phase2_finalseason_summary.json", "w", encoding="utf-8") as f:
    json.dump(out, f)
print()
print("Saved: _phase2_finalseason_full.json, _phase2_finalseason_summary.json")
