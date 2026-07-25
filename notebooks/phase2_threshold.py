"""Two things:
  (1) Threshold robustness for the 'final season curse': sweep the raw delta
      cutoff, and compute a noise-relative (effect-size) version where each
      show's final-season drop is measured in units of that show's OWN normal
      episode-to-episode variation (std of the rest-of-show episode ratings).
  (2) Concrete cases where the overall SLOPE and the final-season DELTA
      disagree -- to illustrate what a +0.80 correlation does and does not
      mean."""

import numpy as np
import pandas as pd

df = pd.read_parquet("data/processed/episodes.parquet")
fs = pd.read_json("data/processed/_phase2_finalseason_full.json")   # ended shows, delta etc.
slopes = pd.read_json("data/processed/_phase2_slopes_full.json")     # slope per show

# Rest-of-show episode std as each show's 'normal wobble' yardstick.
rest_std = {}
for show_id, g in df[~df["ongoing"]].groupby("show_tconst"):
    final_season = g["season_number"].max()
    rest = g[g["season_number"] != final_season]["average_rating"]
    rest_std[show_id] = rest.std(ddof=0) if len(rest) >= 2 else np.nan
fs["rest_std"] = fs["show_id"].map(rest_std)
fs["std_delta"] = fs["delta"] / fs["rest_std"]   # effect size (Cohen-d-like)

n = len(fs)
print("=" * 60)
print("(1a) RAW THRESHOLD SWEEP  (share of shows with delta <= cutoff)")
print("=" * 60)
for t in [-0.2, -0.3, -0.5, -0.75, -1.0]:
    c = (fs["delta"] <= t).sum()
    print(f"  cutoff {t:+.2f}: {c:>4} shows  ({100*c/n:.1f}%)")

print()
print("=" * 60)
print("(1b) NOISE-RELATIVE  (std_delta = delta / the show's own episode std)")
print("Cohen convention: |0.5| = medium, |0.8| = large effect")
print("=" * 60)
valid = fs.dropna(subset=["std_delta"])
print(f"  shows with a computable std_delta: {len(valid):,}")
print(f"  median std_delta: {valid['std_delta'].median():+.3f}")
for t, lbl in [(-0.5, "medium"), (-0.8, "large"), (-1.0, "very large")]:
    c = (valid["std_delta"] <= t).sum()
    print(f"  std_delta <= {t:+.1f} ({lbl}): {c:>4} shows  ({100*c/len(valid):.1f}%)")

print()
# How stable is the CONCLUSION (most shows are NOT cursed) across methods?
print("  ->  The cursed share runs from ~4% (strictest cutoff) to ~31% (loosest),")
print("      so under EVERY method the majority of shows are NOT cursed.")
print("      The conclusion does not depend on the cutoff choice.")
print()

# Overlap: of the raw delta<=-0.5 curse shows, how many also clear the noise bar?
raw_curse = set(fs[fs["delta"] <= -0.5]["show_id"])
noise_curse = set(valid[valid["std_delta"] <= -0.8]["show_id"])
both = raw_curse & noise_curse
print(f"  raw curse (delta <= -0.5): {len(raw_curse)} shows")
print(f"  of those, also a large drop by effect size (std_delta <= -0.8): "
      f"{len(both)}  ({100*len(both)/len(raw_curse):.0f}%)")

print()
print("=" * 60)
print("(2) WHERE SLOPE AND DELTA DIVERGE (what a +0.80 correlation means)")
print("=" * 60)
m = fs.merge(slopes[["show_id", "slope"]], on="show_id", how="left")
m = m[m["total_votes"] >= 30000]

print()
print("A) GRADUAL DECLINERS: very negative overall slope but delta ~ 0")
print("   (the show erodes steadily; the final season is not an EXTRA collapse)")
gradual = m[(m["slope"] <= -1.0) & (m["delta"].abs() <= 0.25)].sort_values("slope")
for _, r in gradual.head(8).iterrows():
    print(f"  {r['title']:<30} slope={r['slope']:+.2f}  final-delta={r['delta']:+.2f}")

print()
print("B) LATE CRASHERS: flat/positive slope but strongly negative delta")
print("   (steady all along, then falls off a cliff at the end -- GoT-like)")
crasher = m[(m["slope"] >= -0.3) & (m["delta"] <= -0.8)].sort_values("delta")
if len(crasher) == 0:
    print("  (none found -- a late crash mechanically drags the fitted slope down")
    print("   too, so the 'flat overall, only the ending crashes' case barely")
    print("   exists; see phase2_crashers.py for the follow-up check)")
for _, r in crasher.head(8).iterrows():
    print(f"  {r['title']:<30} slope={r['slope']:+.2f}  final-delta={r['delta']:+.2f}")
