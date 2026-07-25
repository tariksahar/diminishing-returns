"""Why did the 'flat slope but big final-season crash' set come back empty?
Look at the shows with the biggest final-season drops and see what their
overall slope actually is -- to check whether a late crash mechanically
drags the slope negative too."""

import pandas as pd

fs = pd.read_json("data/processed/_phase2_finalseason_full.json")
slopes = pd.read_json("data/processed/_phase2_slopes_full.json")
m = fs.merge(slopes[["show_id", "slope"]], on="show_id", how="left")
m = m[m["total_votes"] >= 30000]

crash = m[m["delta"] <= -1.0]
print(f"Shows with a big final-season drop (delta <= -1.0, min 30k votes): {len(crash)}")
print("Their slope distribution:")
print(crash["slope"].describe())
print()
print("Least-negative slopes (i.e. the most 'GoT-like' despite the slope):")
for _, r in crash.sort_values("slope", ascending=False).head(10).iterrows():
    print(f"  {r['title']:<30} slope={r['slope']:+.2f}  final-delta={r['delta']:+.2f}")
print()
print("For reference, slope-vs-delta correlation across all analyzed shows:")
full = fs.merge(slopes[["show_id", "slope"]], on="show_id", how="left")
print(f"  r = {full[['slope','delta']].corr().iloc[0,1]:+.3f}")
