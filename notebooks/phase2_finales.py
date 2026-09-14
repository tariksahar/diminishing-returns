"""Phase 2 -- season/finale structure patterns:
  - season finale premium (finale vs the rest of its season)
  - season premiere premium (premiere vs rest of its season)
  - series finale effect (last episode vs the final season's body)
  - named examples of finale flops and finale saves
Uses raw episode ratings (unweighted) since these are per-episode contrasts,
not trajectory fits. Only seasons with >= 4 episodes are used so 'body' is
meaningful."""

import json

import numpy as np
import pandas as pd

df = pd.read_parquet("data/processed/episodes.parquet")

# Per-show total votes, used as a recognizability filter on the examples.
show_votes = df.groupby("show_tconst")["num_votes"].sum()

MIN_SEASON_EP = 4

# Every "beats", "rises" and "+/- 0.5" below is compared against a tolerance,
# for the reason notebooks/phase2_finalseason.py gives: a premium is a rating
# minus a mean of one-decimal ratings, and when the two are equal as rationals
# float arithmetic leaves +/-1e-15 instead of 0.0. 91 season finales sit exactly
# on their season's mean; `> 0` counted the 23 that landed on +1e-15 as wins,
# which is how the published 72.6% and 71.6% came to be 0.1 and 0.3 points too
# high. The same applies at the 0.5 boundaries. The smallest real non-zero
# premium is 0.1 / (episodes - 1), far above this tolerance.
TIE_TOL = 1e-9

season_finale_premiums = []    # finale - mean(rest of season)
season_premiere_premiums = []  # premiere - mean(rest of season)
series_records = []

for show_id, g in df.groupby("show_tconst"):
    g = g.sort_values(["season_number", "episode_number"])
    final_season = g["season_number"].max()

    for season, s in g.groupby("season_number"):
        s = s.sort_values("episode_number")
        if len(s) < MIN_SEASON_EP:
            continue
        ratings = s["average_rating"].to_numpy(dtype=float)
        finale = ratings[-1]
        premiere = ratings[0]
        rest_for_finale = ratings[:-1].mean()
        rest_for_premiere = ratings[1:].mean()
        season_finale_premiums.append(finale - rest_for_finale)
        season_premiere_premiums.append(premiere - rest_for_premiere)

    # Series finale effect: last episode vs final-season body (excluding it).
    fs = g[g["season_number"] == final_season].sort_values("episode_number")
    if len(fs) >= MIN_SEASON_EP:
        r = fs["average_rating"].to_numpy(dtype=float)
        last_ep = r[-1]
        body = r[:-1].mean()
        series_records.append({
            "show_id": show_id,
            "title": g["show_title"].iloc[0],
            "final_season": int(final_season),
            "final_season_body": float(body),
            "last_ep": float(last_ep),
            "finale_effect": float(last_ep - body),
            "total_votes": int(show_votes[show_id]),
            "ongoing": bool(g["ongoing"].iloc[0]),
        })

sfp = np.array(season_finale_premiums)
spp = np.array(season_premiere_premiums)

print("=" * 60)
print("SEASON FINALE PREMIUM (finale - rest of its season)")
print("=" * 60)
print(f"  sample size (seasons): {len(sfp):,}")
print(f"  mean premium:   {sfp.mean():+.3f} rating points")
print(f"  median premium: {np.median(sfp):+.3f} rating points")
print(f"  finale beats its season body: {100*(sfp>TIE_TOL).mean():.1f}%")
print(f"  finale exactly level with it: {int((np.abs(sfp)<=TIE_TOL).sum()):,} seasons")
print(f"  finale peaks by >= +0.5:      {100*(sfp>=0.5-TIE_TOL).mean():.1f}%")
print()
print("=" * 60)
print("SEASON PREMIERE PREMIUM (premiere - rest of its season)")
print("=" * 60)
print(f"  mean premium:   {spp.mean():+.3f} rating points")
print(f"  median premium: {np.median(spp):+.3f} rating points")
print(f"  premiere beats its season body: {100*(spp>TIE_TOL).mean():.1f}%")
print()

sr = pd.DataFrame(series_records)
print("=" * 60)
print("SERIES FINALE EFFECT (last episode - final-season body)")
print("=" * 60)
print(f"  shows (final season >= {MIN_SEASON_EP} episodes): {len(sr):,}")
print(f"  mean effect:   {sr['finale_effect'].mean():+.3f} rating points")
print(f"  median effect: {sr['finale_effect'].median():+.3f} rating points")
print(f"  last episode rises:        {100*(sr['finale_effect']>TIE_TOL).mean():.1f}%")
print(f"  last episode gains >= 0.5: {100*(sr['finale_effect']>=0.5-TIE_TOL).mean():.1f}%")
print(f"  last episode drops <= 0.5: {100*(sr['finale_effect']<=-0.5+TIE_TOL).mean():.1f}%")
print()

pop = sr[sr["total_votes"] >= 20000]
print("=" * 60)
print("FINALE FLOPS (strong final season, collapsing last episode)")
print("min 20k votes, final-season body >= 7.5, steepest drops")
print("=" * 60)
flops = pop[pop["final_season_body"] >= 7.5].sort_values("finale_effect")
for _, r in flops.head(12).iterrows():
    print(f"  {r['title']:<32} body={r['final_season_body']:.2f} -> last ep={r['last_ep']:.1f}  ({r['finale_effect']:+.2f})")
print()
print("=" * 60)
print("FINALE SAVES (last episode far above its season body)")
print("min 20k votes, biggest jumps")
print("=" * 60)
saves = pop.sort_values("finale_effect", ascending=False)
for _, r in saves.head(12).iterrows():
    print(f"  {r['title']:<32} body={r['final_season_body']:.2f} -> last ep={r['last_ep']:.1f}  ({r['finale_effect']:+.2f})")

# Save the summary distributions for a figure.
out = {
    "season_finale_premium": {"mean": round(float(sfp.mean()), 3), "median": round(float(np.median(sfp)), 3),
                              "pct_above": round(100*float((sfp > TIE_TOL).mean()), 1)},
    "season_premiere_premium": {"mean": round(float(spp.mean()), 3), "pct_above": round(100*float((spp > TIE_TOL).mean()), 1)},
    "series_finale_effect": {"mean": round(float(sr["finale_effect"].mean()), 3),
                             "pct_up": round(100*float((sr["finale_effect"] > TIE_TOL).mean()), 1),
                             "pct_flop": round(100*float((sr["finale_effect"] <= -0.5 + TIE_TOL).mean()), 1)},
}
with open("data/processed/_phase2_finales.json", "w", encoding="utf-8") as f:
    json.dump(out, f)
print()
print("Saved: data/processed/_phase2_finales.json")
