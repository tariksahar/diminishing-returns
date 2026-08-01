---
title: Report Outline
description: The structure of the report, with each finding's reliability tier.
---

# Report Outline — "Do TV Shows Really Decline?"

Working skeleton for the final write-up. This is a plan, not the prose: it
places each Phase 2 finding into a section with its reliability tier. Full
technical rationale for every point lives in `docs/decisions.md`; this file
is the narrative structure.

Reliability tiers (from the Phase 2 review):
- 🟢 rock-solid: survived confound controls / artifact checks
- 🟡 real but conditional: state with an explicit caveat
- 🔵 methodological: belongs in the "how we know this is trustworthy" section

Language: English (decided). **Deliverables: TWO** — (1) this engaging essay
(`essay.md`), the public-facing hook; (2) a formal technical report
(abstract / data & methods / results / figures / references), to demonstrate
rigor. This outline drives the essay.

**Both now exist.** The technical report is written (`technical_report.md`):
Markdown rather than LaTeX, because no TeX toolchain is available here and
shipping an uncompiled `.tex` would mean publishing something we had never
seen rendered. It numbers its own figures in order of appearance — the two
methods figures (fig08, fig09) come first there, so its Figure 3 is the
essay's Figure 1. Both documents draw on the same nine image files.

---

## Thesis (the spine)

**Mostly no.** The average show is remarkably stable across its run. The
"decline" belief is fed by (a) a memorable minority of famous final-season
collapses and (b) specific subsets — long-running shows, older shows, a few
genres. And where the belief most expects a collapse (the finale), shows
usually *peak* instead.

One-line version: *"A few famous shows falling apart doesn't mean every show
declines."*

---

## 1. Hook — the folk belief
- Open on the shows everyone remembers collapsing (Game of Thrones S8,
  Dexter, The Walking Dead). State the question the project tests.
- NOTE: deliberately avoid House of Cards as a headline example. Its crash
  is real in the data (-4.24) but was caused by the lead actor being written
  out amid scandal, so it illustrates an off-screen shock rather than a show
  losing its way. It belongs in §8 (limitations), not the hook.

## 2. Headline — shows are mostly stable  [🟢]
- Clean regression-to-the-mean test: a show's second half lands within ~0.07
  rating points of its first half even at the extremes; the two halves
  correlate +0.79. Quality persists. (finding #1)
- Overall decline/rise split across all 3,234 shows (sqrt-votes slope):
  only 42.6% trend down vs 57.4% up; clear decline (≤ -0.5 start→end) just
  16.9%, roughly flat (±0.5) 57.4%, clear rise (≥ +0.5) 25.7%; median slope
  +0.109 (slightly positive). Fewer than 1 in 6 shows clearly declines.
  (Cross-checked: fresh recompute matched the prior slopes file to 0.000000,
  retroactively validating every analysis that used it.)

## 3. The finale surprise  [🟢]
- Season finales are typically a show's *peak*: 72.6% beat their own season
  (avg +0.25); premieres are unremarkable. (finding #2)
- Series finales usually rise too (71.6% up); the "finale flop" is the
  memorable exception (~9% drop hard). (finding #3)
- Named examples both directions (flops: Dexter, HIMYM, Power; saves: The
  Office, Brooklyn 99, TNG).

## 4. The "final season curse" — mostly a myth  [🟢 + 🟡 caveat]
- Ended shows split 50.5% down / 49.2% up (10 exactly level), median ≈ 0;
  only 12.6% a clear
  curse. Robust to threshold sweep and effect-size. (finding #4)
- The cursed minority is dominated by very famous shows (GoT -2.55, Master
  of None -2.54, The Promised Neverland -2.28). House of Cards is the single
  largest drop (-4.24) but is held back for §8 — see the note in §1.
- 🟢 **Availability bias, upgraded from interpretation to measurement**
  (`phase2_popularity.py`, added after the first draft). Clear decline rises
  monotonically with audience size: 14.8% / 15.1% / 24.7% / **43.3%** across
  vote tiers, against a 16.9% base rate. Survives precision, length-band and
  era+length checks. The final-season delta cut the same way is monotone too
  (11.6% / 12.5% / 14.4% / 23.8%) but 🟡 — only 42 series in the top tier,
  95% CI 13.5-38.5, so it is the weaker of the two and must be described as
  such. (finding #10)
- 🟡 Caveat that travels with both: vote count is endogenous (a bad ending
  draws voters), so this is descriptive only — no causal claim that fame
  causes decline.
- Consistency note: this reframing invalidated §9's "the odds are against
  it", written when 16.9% was the only rate available. §9 now names both.

## 5. Where decline IS real — age, length, genre  [🟢]
- Older and longer shows genuinely decline; newer and shorter ones rise.
  Both effects hold up net of each other (era +0.0048/yr, length
  -0.026/season, both highly significant). (finding #7)
- Genre net of era+length: Animation genuinely up (+0.23), Adventure down;
  mainstream Drama/Comedy/Crime/Action ~neutral. Genre matters less than a
  show's age and length. (finding #8)
- 🟡 Multiplicity: 16 genre dummies are tested at once, so ~1 raw flag is
  expected by chance. Only Animation and Adventure survive Bonferroni;
  Documentary, Romance and Thriller survive Benjamini-Hochberg; **Biography
  survives neither and was dropped from the prose**, having been reported as
  a real effect in the first draft. (finding #11)

## 6. Trajectory shapes  [🟢]
- "Jumped the shark" (rise-then-fall, peak mid-run) is the single most common
  shape (44.6%). (finding #9)
- The peak sits mid-run and scales with show length (NOT "season 2", which
  was a short-show aggregation artifact); highly variable, slight first-third
  lean. "The first season is always best" is false — the last season is the
  single best more often (37% vs 27%). (findings #5, #6)
- (The ∪ "found itself" shape is handled in the methodology section as an
  artifact worked-example — see §7.)

## 7. How we made sure this is trustworthy — methodology & reliability  [🔵]
The credibility section. Not "what we found" but "why you can trust it."
- **Data & inclusion.** Three IMDb tables joined to one row per rated
  episode; six inclusion filters (≥13 episodes, ≥2 seasons, ≥50 mean
  votes/episode, genre exclusions, documentary cap). 3,234 shows / 192,720
  episodes.
- **Weighting.** Episodes weighted by sqrt(num_votes) — dampens low-vote
  noise without letting a single viral episode dominate. Why not raw votes
  (finale/backlash spikes) or log (≈ unweighted).
- **Traps we caught and defused (the heart of this section):**
  - Mathematical coupling: the naive "high shows decline" correlation (-0.37)
    was inflated by correlating a slope with its own intercept; the clean
    disjoint-halves test showed the real effect is tiny (~0.07).
  - Confounding: era / length / ongoing are tangled; used OLS controls to
    show era and length each hold up independently.
  - Low-vote tails: the ∪ "found itself" pattern looked real, but ~20% of it
    is propped up by low-vote late episodes (worked example of an artifact
    check; ~57% survives, e.g. Star Trek: Picard).
  - Right metric for the right question: the overall slope understates late
    sharp crashes (GoT), so the final-season question needs a direct
    season-mean comparison, not the slope. Slope vs final-season-delta
    correlate +0.80 — related but not interchangeable.
  - Late episodes are systematically low-vote (within-show position vs votes
    correlates -0.74), so any late-leaning analysis is treated as more
    fragile.

## 8. Limitations & deferred
- Non-narrative formats leaking the genre filter (SNL, The Nostalgia Critic).
- Very-long-running outliers kept, handled by normalization.
- IMDb ratings reflect who bothers to vote, not a representative audience.
- Our decline metric can't separate organic quality decay from exogenous
  shocks: e.g. House of Cards' final-season crash was driven by its lead being
  written out amid scandal, not by the writing. Some "curses" are off-screen
  events, and we don't distinguish cause — only that the ratings fell.
- (See `docs/decisions.md` deferred list for the full record.)

---

## Figures — DONE (Phase 3)

All nine are produced by `notebooks/phase3_figures.py` (style constants in
`notebooks/figstyle.py`) and land in `figures/`. Each recomputes its own
numbers from `data/processed/` rather than hard-coding them, and prints what
it annotated so every label can be checked against `decisions.md`.

| Figure | File | Section |
|---|---|---|
| Slope distribution — the headline | `fig01_slope_distribution.png` | §2 |
| First half vs second half (stability) | `fig02_halves_stability.png` | §2 |
| Finale premium (finale / premiere / series finale) | `fig03_finale_premium.png` | §3 |
| Final-season delta + threshold sweep | `fig04_final_season_curse.png` | §4 |
| Era / length / genre coefficient plot | `fig05_era_length_genre.png` | §5 |
| Trajectory-shape breakdown + average arcs | `fig06_trajectory_shapes.png` | §6 |
| Peak-season location (3 panels) | `fig07_peak_location.png` | §6 |
| Example trajectories (Stranger Things / Friends / Breaking Bad) | `fig08_example_trajectories.png` | §1, §7 |
| Vote-weighting comparison on GoT | `fig09_weighting_choice.png` | §7 |

Four beyond the original five-figure sketch: the headline slope distribution
and the halves-stability scatter carry §2's central claim and were missing;
peak location was split out of the shape figure (three panels of its own); and
the weighting comparison was added because §7's "whose votes count" argument
is hard to follow without seeing the three fitted lines.

## Open to-compute items (before drafting prose)
1. ~~Overall decline/rise headline %~~ DONE — see §2 (42.6% down / 57.4% up;
   16.9% clear decline). Prior slopes file confirmed sqrt-weighted.
2. ~~Decide final-narrative language~~ DONE — English (repo standard;
   international-employer reach). It lives in `docs/essay.md`, titled
   *Your Favourite Show Probably Didn't Decline*.
3. ~~Decide which figures become final (polish pass)~~ DONE — see the table
   above.
4. ~~Place figure callouts in the essay's prose~~ DONE — all nine
   embedded with numbered captions. Reading order matches the file numbering
   (fig01…fig09), so no renumbering is needed as the prose moves around;
   fig08 sits in §7 rather than §1 to keep that alignment.
5. Dark-mode figure set for GitHub — deferred to packaging, palette already
   validated. See `docs/decisions.md`.
