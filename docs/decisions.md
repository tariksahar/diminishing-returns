# Decision & Deferred-Task Log

A running record of the design decisions we've locked in and the things we've
consciously postponed. Update this whenever a decision is made or a deferred
item is resolved, so nothing gets lost between phases.

## Finalized inclusion filters

A show is included in the analysis dataset if **all** of the following hold:

| Rule | Value |
|------|-------|
| `titleType` | `tvSeries` or `tvMiniSeries` |
| Minimum episodes (with a rating) | >= 13 |
| Minimum seasons | >= 2 |
| Minimum mean votes per episode | >= 50 |
| Excluded genres | any of Game-Show, Reality-TV, Talk-Show, News |
| Documentary special case | Documentary-tagged is kept only if episode count < 100 |

Rationale, in short:
- **>= 13 episodes**: enough length to talk about a trajectory.
- **>= 2 seasons**: a decline "across seasons" needs at least two seasons to
  compare (e.g. Sherlock has only 15 episodes but 4 seasons, so it stays; the
  single-season anime giants like One Piece / Naruto are dropped).
- **mean votes/episode >= 50**: cuts statistical noise from barely-voted shows
  without narrowing all the way down to only the mega-popular ones.
- **Genre exclusions**: "decline" is a narrative concept; game shows, reality
  TV, talk shows and news have no season-to-season story arc to decline.
- **Documentary < 100 episodes**: separates season-based story documentaries
  (Chef's Table, Drive to Survive, Cheer) from anthology/magazine strands
  (Nova, Frontline, Biography). Platform-independent — we have no channel/
  platform field in the data, so the rule applies equally to every documentary.

## Deferred tasks (do not forget)

1. **Per-episode vote noise → handled at ANALYSIS stage, not in build. RESOLVED.**
   Kept `numVotes` per episode in the processed table; episodes are weighted
   by `sqrt(numVotes)` when fitting each show's trend slope. Full rationale
   and comparison of weighting schemes logged under "Phase 2 decisions"
   below.

2. **Ongoing shows (`endYear` empty) → flag, don't drop. RESOLVED.**
   `ongoing` boolean added in build. Ongoing shows are excluded from the
   final-season-curse analysis (`data/processed/_phase2_finalseason_full.json`,
   2,710 ended shows only). Finding: no systematic curse — 50.6% of ended
   shows have a lower-than-usual final season, 49.4% higher, median delta
   ≈ 0.00. Only 12.6% show a clear curse (final season ≥0.5 points below the
   rest), and those are disproportionately well-known flops (House of Cards
   -4.24, Game of Thrones -2.55, Master of None -2.54) — likely why the
   "final season curse" feels universal (availability bias) even though it
   isn't the norm. Correlation between this delta and the overall trend
   slope is +0.80 — related but not the same metric, confirming they answer
   different questions (see "Overall trend slope is NOT a valid proxy..."
   below).

3. **Episode-level air-year precision (optional refinement).**
   For a more precise "still active" signal we could pull each show's latest
   episode air year from the `tvEpisode` rows in title.basics (currently unused;
   we only use the tvSeries rows). Deferred; only do it if the endYear proxy
   proves insufficient.

4. **Shows with missing `genres` — RESOLVED.**
   Verified in phase0_final_filter_check.py: 0 shows in the final set have
   missing genres, so this edge case does not occur. No action needed.

5. **Very-long-running shows kept, handled at analysis stage. RESOLVED.**
   Extreme outliers (Pokémon 1234 ep / 25 seasons, Detective Conan 1211 / 54,
   The Simpsons 806 / 37, etc.) stay in the dataset; they were NOT capped in
   build. As planned, Phase 2 normalizes every trajectory to a 0-1 episode
   axis so length can't distort the fit, reports medians alongside means
   throughout, and analyses length explicitly as its own factor (see the
   cross-sectional section) rather than treating long shows as contamination.
   485 shows have >100 episodes, 127 have >200.

6. **Non-narrative formats leaking through the genre filter — STILL OPEN,
   consciously not fixed.** Some sketch/variety/web-review shows tagged only
   as Comedy/Music (not Talk-Show/Reality-TV) survive the genre exclusions —
   notably Saturday Night Live (1010 ep) and The Nostalgia Critic (935 ep).
   Phase 2 decision: no manual blacklist was added. A hand-curated exclusion
   list is a judgement call that would be hard to justify or reproduce, and
   the affected shows are few enough not to move any headline figure. Instead
   this is disclosed as a stated limitation in the report. Revisit only if a
   future analysis turns out to be sensitive to them.

## Phase 2 decisions

### Per-show trend slope: weighting scheme

To measure whether a show "declines", each show's episodes are fit with a
weighted least-squares trend line: `average_rating ~ normalized_episode_order`
(episode order scaled 0-1 within the show). The slope of that line is the
show's decline/rise metric.

Episodes are weighted by **`sqrt(num_votes)`**, not raw `num_votes` and not
unweighted.

Rationale:
- Vote counts vary a lot *within* a single show (median max/min ratio 3.5x,
  up to 10x+ for 10% of shows) — an unweighted fit lets a 51-vote episode
  pull the trend line as hard as a 500,000-vote episode, which is
  statistically wrong (a low-vote average is a noisier estimate).
- Weighting directly by `num_votes` is the textbook-correct choice under a
  simple i.i.d.-votes noise model, but IMDb vote counts are not i.i.d. —
  finale/viral episodes get inflated vote counts for reasons unrelated to
  measurement reliability (rewatching, backlash, discourse). Verified on
  Game of Thrones: four of its six most-voted episodes are final-season ones
  (S8E6 305k/4.0, S8E3 255k/7.5, S8E5 227k/5.9, S8E4 195k/5.5), all clustered
  at the very end of the normalized x-range and all rated far below the show's
  8.95 pre-final-season average, so linear weighting nearly doubled the fitted
  slope (-1.02 unweighted -> -2.21 linear) on the strength of a handful of
  episodes. Note the driver is that END-OF-RUN CLUSTER, not a single viral
  episode: the single most-voted episode is actually a mid-run 9.9 (S6E9,
  311k). An earlier version of this note claimed the two most-voted episodes
  were the last two, which is wrong -- corrected here.
- `log(num_votes)` barely differs from unweighted in practice (verified
  in phase2_weight_compare.py across Friends, Game of Thrones, Breaking Bad,
  The Sopranos and Dexter), so it doesn't meaningfully address the noise
  problem.
- `sqrt(num_votes)` was verified as the middle ground: it visibly dampens
  low-vote noise while not letting a single viral episode dominate the fit
  (phase2_export_5shows.py, compared interactively across Game of Thrones,
  Lost, Chuck, Breaking Bad and Monk).

### Overall trend slope is NOT a valid proxy for "final season curse"

Verified on Game of Thrones: season 8's true mean rating is 6.40 (6
episodes), vs 8.95 for seasons 1-7 (67 episodes). But the fitted trend
line's value in the season-8 x-range is 7.6-8.3 depending on weighting
scheme — all well above the true 6.40.

Cause: a straight line minimizes total squared error across *all* episodes.
When ~92% of a show's episodes sit at a consistently high rating and only
the last few crash, the line stays anchored near the majority and
understates the size of a late, sharp drop — a single linear slope cannot
represent "flat-then-cliff" as accurately as "steady decline".

Consequence: the per-show slope answers "does this show decline at a
roughly constant rate overall" — a different question from "did the final
season specifically tank". The final-season-curse analysis (deferred item 2
above) must use a direct comparison instead: `final_season_mean -
rest_of_show_mean` (ended shows only), not the overall slope.

### Final-season-curse threshold: headline -0.5, plus a robustness check

The "clear curse" cutoff of `delta <= -0.5` rating points is an intuitive,
lay-readable choice (a half-point drop is human-perceptible), not a
statistically-derived one. Decision: **keep -0.5 as the headline number**
(it's in the same units readers care about) **but always report it
alongside a robustness check** so the conclusion doesn't hinge on an
arbitrary cutoff:
- Raw-threshold sweep: cursed share is 29% at -0.2, 22% at -0.3, 12.6% at
  -0.5, 6.8% at -0.75, 3.7% at -1.0 — the "most shows are not cursed"
  conclusion holds at every reasonable cutoff.
- Noise-relative effect size: `delta / (std of the show's non-final-season
  episode ratings)` — how many of the show's own normal episode wobbles the
  final season sits below its baseline (Cohen-style: 0.5 medium, 0.8 large).
  23% reach a "large" drop; and 98% of the raw `delta <= -0.5` shows also
  clear the "large" effect-size bar, so the intuitive cut and the principled
  one flag nearly the same shows.

### Slope vs final-season-delta: correlated (+0.80) but not redundant

The overall slope and the final-season delta correlate +0.80 (r^2 ~ 0.64),
so ~36% of the variation is independent — they answer different questions.
Concretely: "gradual decliners" exist (steep negative slope, delta ~0 — e.g.
The Walking Dead slope -1.19 / delta -0.23; Fargo -1.27 / -0.12), but the
pure "flat overall, only the finale crashes" case is essentially absent —
all 32 big final-season crashers (delta <= -1.0, >=30k votes) also have a
negative slope (least-negative is Scrubs at -0.57). Reason is mechanical: a
final season sits at the end of the x-axis, so a late crash necessarily
tilts the fitted line down. (Corrects an earlier loose description of Game
of Thrones as "flat then cliff" — its slope is clearly negative too.)

### Trajectory shape (C): peak location, curvature, volatility

Three shape measures beyond the single linear slope, all using
`sqrt(num_votes)` weighting where a fit is involved.

**1. Peak-season location — reported as "mid-run, scaling with length", NOT
"season 2".** An initial cut on 3-season shows alone made season 2 look like
the modal best season ("sophomore surge"). That was an aggregation artifact:
the dataset is dominated by short shows (1,101 two-season, 780 three-season),
and in a short show the middle *is* season 2. Stratifying by season count
shows the peak's ABSOLUTE season number grows with length (mean best season:
1.6 at 2 seasons, 2.5 at 4, 3.1 at 5, 3.8 at 7, 5.8 at 8+) while its
NORMALIZED position stays near the middle (~0.46-0.59 across all lengths).
So the peak is emphatically not "season 2" — where it lands scales with how
long the show runs. Phrase the positive claim carefully, per the caveat below.
  - Important honesty caveat, do not overstate: mean/median normalized peak
    is ~0.50, but the peak is NOT concentrated in the middle. For shows with
    >=5 seasons the peak lands in the first third 41.7% of the time, middle
    third only 24.9%, last third 33.3%. The average is 0.5 because the two
    ends roughly balance out (flaw of averages), with a mild lean toward the
    first third. Report it as "on average mid-run, but highly variable across
    shows, slightly favoring the first third", not "shows peak in the middle".
  - Also note (consistent with the finale findings): the LAST season is the
    single best season 37.2% of the time vs the FIRST season only 27.1% —
    the folk belief "the first season is always the best" is false in the
    aggregate.

**2. Curvature ("jumped the shark") — a per-show weighted quadratic fit**
(`rating ~ a + b*x + c*x^2`, x = normalized 0-1 episode order). A show is
labelled by the sign of `c` when the parabola's vertex is interior
(0.15 <= vertex <= 0.85) and |c| > 0.05: `c<0` = "jumped the shark"
(rises then falls, peak in the middle), `c>0` = "found itself" (dips then
recovers), otherwise "linear/flat". Result over 3,234 shows: 44.6%
jumped-the-shark, 35.2% linear/flat, 20.3% found-itself. The peak-then-fall
shape is the single most common trajectory. Clearest jumped-the-shark cases
(>=20k votes): Top Gear, House of Cards, Game of Thrones, Master of None
(vertices ~0.30-0.42). Clearest found-itself: SpongeBob SquarePants, Star
Trek: Picard, Spy x Family.
  - Reconciliation with (1): curvature measures the smooth arc fitted across
    ALL episodes (∩ peaks mid-run); best-season is a single argmax POINT that
    noise can pull to an end season even when the overall arc is ∩. Different
    lenses, both valid, not contradictory.
  - Robustness of "found itself" against a low-vote-tail artifact (checked
    because early episodes are the well-voted ones — within-show position vs
    log(votes) correlates -0.74, so a show's late/"recovery" episodes are its
    LOW-vote ones). Verdict: the label is NOT a weighting artifact (94.5% of
    sqrt-weighted found-itself stay found-itself unweighted) and isn't
    concentrated in short shows. BUT the recovery region is often thinly
    voted: median last-third vote count is only ~132, and 39.7% of
    found-itself shows have a last-third averaging <100 votes. Re-fitting
    after dropping <100-vote episodes: of 655, 370 stay found-itself (56.5%),
    132 flip to plain decline/flat (20.2% — the recovery was propped up by a
    low-vote tail; e.g. Detective Conan, low-vote documentaries/reality), 153
    become untestable (23.4%). Clean cases survive (Picard, SpongeBob, Spy x
    Family). Report guidance: treat "found itself" as real for ~57% but
    caveat that ~20% is a low-vote-tail artifact; restrict to adequately-voted
    recoveries when making strong claims.
  - GENERAL takeaway to carry forward: because low-vote episodes sit
    systematically at the END of a show, any late-leaning analysis
    (found-itself recovery, final-season signals) rests on shakier ground
    than early-episode analysis. Keep this in mind for all remaining phases.

**3. Volatility — weighted RMSE of the linear fit's residuals** (how bumpy a
show is around its own trend). Median 0.35 rating points. Most volatile
(>=20k votes): Thomas & Friends (1.70), One Punch Man (1.54), Top Gear
(1.40), House of Cards (1.22), Game of Thrones (1.10) — long-running
animation plus hard-finale-crash shows. Most consistent: Shahmaran (0.09),
Warrior Nun (0.10), Kim's Convenience (0.19) — mostly short, even shows.

### Cross-sectional cuts (A): era, length, genre — with confound controls

Raw cuts on the sqrt(votes)-weighted slope all look striking but are heavily
confounded (newer shows are shorter and more often ongoing; the composition
table: median seasons 5 in the 1950s -> 2 in the 2020s, ongoing 3% -> 41%).
Disentangled results:
- **Era effect is real.** Newer shows trend up, older down, and it SURVIVES
  restricting to ended shows and holding length fixed (2-3 season ended
  shows: pre-2000 slightly negative, 2000s-2020s +0.26 to +0.31). In the
  genre OLS below, start_year is +0.0048/yr (t=4.8). Plausible mechanism
  (interpretation, not proven): modern pre-planned serialized short-season
  shows build toward climaxes; older episodic network shows plateau/decline.
- **Length effect is real and independent.** Ended 2-3 season shows +0.217
  vs ended 6+ season shows -0.120; OLS n_season coefficient -0.026/season
  (t=-6.8). Longer shows genuinely wear down, net of era.
- **Genre net of era+length (OLS, multi-hot genre dummies + start_year +
  n_season + ongoing, n=3234):** Animation is genuinely up (+0.233, t=5.6),
  Documentary (-0.235, t=-2.7) and Biography (-0.244, t=-2.2, the weakest of
  the three) down, Romance/Adventure/Thriller mildly down; mainstream
  Drama/Comedy/Crime/Action are
  ~0 and not significant. So genre matters much less than a show's age and
  length. (OLS uses classical SEs — fine given the large t-stats.)

### Regression to the mean, done properly — the "high shows decline" effect is TINY

The earlier -0.373 correlation (slope vs its own fitted intercept) is
inflated by mathematical coupling (shared noise). Clean test: split each
show's episodes into disjoint first/second halves.
- First-half mean vs second-half mean correlate +0.793 — shows are largely
  STABLE across their run.
- Regression of second-half on first-half has slope 0.886 (<1, so some
  regression to the mean exists), but the reliability of a half-mean is 0.983
  (Spearman-Brown), i.e. under "stable quality + noise only" we'd expect
  ~0.983. Observed 0.886 is only slightly below, so there is a small REAL
  extra decline of high starters — but it is tiny: top-quartile starters
  (~8.32) fall just -0.07 in the second half, bottom-quartile (~6.94) rise
  +0.07.
- Consequence for the thesis: the "shows decline" folk belief is largely
  FALSE for the average show (second half within ~0.07 of the first half).
  Decline is real only in specific subsets (long-running shows, pre-2000
  shows, the ~12.6% final-season-curse minority). Do NOT lean on regression
  to the mean as a big explanation — properly measured it is nearly
  negligible.

## Phase 3 decisions (figures)

### Colour is computed, not eyeballed

Figure colours come from a validated categorical palette rather than
matplotlib's defaults. The checks (lightness band, chroma floor, Machado-2009
protan/deutan colour-blind separation, normal-vision floor, WCAG contrast
against the chart surface) were run rather than reasoned about — the reference
checker is a Node script and Node isn't installed here, so it was ported to
Python and confirmed against the reference palette's published numbers
(worst adjacent CVD ΔE 9.1, normal-vision 19.6) before being trusted.

Results for what the report actually uses:
- categorical trio `#2a78d6 / #eb6834 / #1baf7a` — passes all-pairs
  (worst CVD ΔE 9.2, worst normal-vision ΔE 24.0)
- diverging poles `#2a78d6` (rise) / `#e34948` (decline) — passes cleanly

Two conscious deviations, both allowed by the palette's own rules and recorded
in `notebooks/figstyle.py`: the aqua slot sits at 2.74:1 contrast (below 3:1),
so every aqua mark carries a visible direct label; and grey is used as a
de-emphasis ink (the flat middle of a diverging scale, insignificant
coefficients), which fails the categorical chroma floor by construction because
it is not a series colour.

**A real defect the check caught: orange and red cannot share a figure.**
`#eb6834` and `#e34948` separate by only ΔE 5.6 under simulated deutan vision
(floor 6.0) and — worse — ΔE 7.1 under *normal* vision against a floor of 15.
Full-colour readers cannot reliably tell them apart either. The first version
of fig02 used both (orange fitted line, red/blue quartile bars). Fixed by
making the quartile bars a single colour, which is independently the right
call: the quartiles are nominal categories and the sign is already carried by
the bar's direction and its signed label. Every other pair in use clears both
floors. The rule is now written into `figstyle.py` so it is not re-broken.

Roles, assigned so that orange and red never meet:

| Colour | Role |
|---|---|
| blue `#2a78d6` | data points / single series, and the "rise" pole |
| red `#e34948` | the "decline" pole — only in figures with no orange |
| orange `#eb6834` | the fitted trend the analysis actually uses (fig02, fig08, fig09) |
| aqua `#1baf7a` | a rejected alternative or third class — always directly labelled |
| grey `#898781` | de-emphasis: reference lines, the flat middle, insignificant estimates |

Consistency this buys: the sqrt-weighted trend line is orange in every figure
it appears in. An earlier version drew that same estimator orange in fig08 but
blue in fig09, which would have made the two figures hard to read together.

### Dark mode — DEFERRED to packaging, not dropped

The figures are drawn on a light surface (`#fcfcfb`). Both primary deliverables
are documents (the essay and an arXiv-style technical report), where light is
the convention, so this is right for the deliverable. The open question is
GitHub: the repo is public, most people browse it in dark mode, and a
light-background figure reads as a bright block there.

Decision: **keep light only for now, revisit at packaging.** It is an aesthetic
mismatch, not a functional one — the figures stay perfectly legible on a dark
page because they are opaque. (Transparent backgrounds are the case that
actually breaks, since dark text lands on a dark page; `savefig.facecolor` in
`figstyle.py` is what keeps us out of that.) Figures will keep changing through
the prose passes, and maintaining two sets now would double that churn for a
surface that is not the deliverable.

The deferral was de-risked by validating the dark palette up front, so this
cannot fail later:
- dark trio blue/orange/aqua `#3987e5 / #d95926 / #199e70` — passes all-pairs
  (CVD ΔE 9.4, normal-vision 20.9, all >= 3:1 on the dark surface)
- dark poles blue/red `#3987e5 / #e66767` — passes (ΔE 19.2 / 29.0)
- orange vs red still fails in dark mode too (normal-vision ΔE 7.1), so the
  "never in the same figure" rule is mode-independent and carries over unchanged

When it is done: add a theme parameter to `figstyle.py` (all colours already
route through it, so this is one switch plus a re-run), write the dark set to
`figures/dark/`, and reference both from GitHub-facing markdown with a
`<picture>` element keyed on `prefers-color-scheme`.

### Uniform figure width

All nine figures are drawn at the same width (12 in / 2400 px), varying only in
height. Widths previously ranged from 9.5 to 13.5 in; since every figure is
scaled to the same column in the report, that made identical 9.5pt labels
render visibly larger in some figures than others. Same width = same apparent
text size throughout.

### Two silent clipping bugs, found by checking every hard-coded axis limit

Manually set axis limits hide anything outside them. Checked all of them
against the data they must contain:
- **fig02 was dropping 16 shows.** Its scatter box was fixed at (4.2, 9.8)
  while half-means actually run from 1.70 to 9.86 — the lowest-rated shows sat
  off the corner of the plot with nothing to indicate it. Limits are now
  derived from the data, so nothing is hidden.
- **fig04 clipped 6 shows (0.22%) without saying so**, where fig01 disclosed
  the same thing. Now disclosed in the footnote too.

Both were invisible in the rendered image — the figure looked fine, which is
exactly why the limits had to be checked against the data rather than by eye.

### Shape classification audited (fig06) — it holds up

The `jumped_the_shark` / `found_itself` / `linear/flat` split was re-derived
from `episodes.parquet` and checked against the stored
`_phase2_shape_full.json`: **0 label mismatches across all 3,234 shows**, max
curvature difference 5e-11. The file and the code agree.

Three things the audit settled:

1. **The label "climbs, then falls" is earned.** Within the jumped_the_shark
   class the vertex (the peak) sits at a median of 0.50 of the run; only 6.2%
   peak in the first 0.15-0.25 stretch, while 41.9% peak in the middle fifth.
   The class is not "declines from the start" wearing an arc's name. Median
   rise to the peak is 0.37 rating points and median fall from it 0.33 — a
   real but small arc, which is what licenses the "it is gentle" headline.
   (13.6% climb by less than 0.1 points, so a minority barely rise at all.)
2. **The +/-0.05 curvature cut-off does almost no work.** Shares are 44.6 /
   35.1 / 20.3 at a threshold of 0, and 43.7 / 36.6 / 19.8 even at 0.20. The
   binding condition is whether the vertex falls inside the run, not the
   curvature size — so the result is not an artifact of an arbitrary cut.
3. **"linear/flat" was a misleading name and the figure no longer uses it.**
   The class means "no turning point inside the run", i.e. monotone over the
   show's own length — it includes steep straight-line decliners (The Walking
   Dead, slope -1.19) and steep risers alike. The figure now labels it
   "Straight line (no turn mid-run)" and states that the class holds both
   directions, so its average arc is a net of the two.

fig06 also now carries the `found_itself` caveat that was already logged above
(about a fifth of those recoveries rest on thinly-voted late episodes), which
the first version of the figure omitted.

### fig08 reframed: direction, not curvature class

fig08 originally showed one show per *curvature class* (∩ / straight / ∪).
That framing kept producing trios where two of the three declined, which
required a "not a representative sample" disclaimer to stop the figure
contradicting the report's own headline. A disclaimer that has to argue with
its own figure is a sign the figure is wrong, not the reader.

Reframed to **direction**, matching the three groups fig01 already
establishes — clearly declining, essentially flat, clearly rising. Now the
figure illustrates the headline instead of fighting it, and no disclaimer is
needed:

| Show | Group | Slope | Votes |
|---|---|---|---|
| Stranger Things (2016-2025) | clearly declining | -0.87 | 2.6M |
| Friends (1994-2004) | essentially flat | +0.12 | 1.4M |
| Breaking Bad (2008-2013) | clearly rising | +0.99 | 4.5M |

They also span 1994-2025 and 42-234 episodes, which incidentally shows the
method working across eras and very different show lengths.

Rejected along the way: **The Office (US)**, the outline's original pick,
classifies as jumped_the_shark (slope -0.64) — the same class as Game of
Thrones, so the panel label would have contradicted the data. **M\*A\*S\*H**
was genuinely flat but too old and US-centric to pull a reader in. **The
Walking Dead** is a vivid straight-line decliner but made the trio two-thirds
declining. **Game of Thrones** is deliberately not reused here because it
already anchors fig09.

### Figure numbers are recomputed, not transcribed

Every figure recomputes its inputs from `data/processed/` and prints the values
it annotates. All nine reproduce the Phase 2 findings exactly — GoT sqrt slope
-1.55 and the -2.21 / -1.55 / -1.02 weighting spread, OLS -0.0261 (t = -6.8),
peak-season means 1.6 / 2.5 / 3.1 / 3.8 / 5.8, the threshold sweep
29.2 / 22.4 / 12.6 / 6.8 / 3.7 — so the plots and the prose cannot drift apart.

Incidental confirmation: §2's "57.4% rise" and "57.4% essentially flat" are two
genuinely different quantities that round to the same number. It looks like a
copy-paste error in the outline and is not one.

## Phase 3b decisions (prose ↔ figure pass)

### Figures go where their numbers are, not at the end of a section

Two figures had been parked after their section's closing line, which deflated
the closing. Rule adopted: a figure follows the paragraph that states its
numbers; a section's last line is its last line. §6 was re-ordered for the same
reason — the two myths were swapped so each figure sits beside the claim it
supports, which also gave the section a better progression (shape → where the
peak is → which season wins).

### The inclusion criteria were missing from the essay entirely

§8 referred to "our filters" and no earlier section had ever described them —
the reader was told what leaked through a net they'd never been shown. §7 now
opens with **What counts as a show** (the joins, ≥13 episodes, ≥2 seasons, ≥50
mean votes, genre exclusions, and the resulting 3,234 / 192,720). This was in
the outline's plan for §7 and had simply never been drafted.

### House of Cards restored to §8

The outline deliberately held House of Cards back from the §1 hook — its −4.24
crash is a lead actor written out amid scandal, not a show losing its way — and
assigned it to §8 as the flagship off-screen-shock example. The draft had
dropped it, so §8 was making its argument without its strongest case. Restored,
with the season-length detail verified against the data (final season cut from
13 episodes to 8; season mean 4.19 against ~8.4 for seasons 1–5).

### Claims about named shows are verified, not remembered

Every named-show claim in the essay was re-checked against the parquet rather
than trusted: the finale flops and saves, HIMYM's 7.56 → 5.5, GoT's 6.40 vs
8.95, Scrubs' season 9 at 6.21 against ~8.1, SNL's 1,010 episodes. All held.
Two claims did not survive contact and were changed:
- "walking off at the top of their game" implied the whole final *season* was
  strong; those four shows' final seasons are all slightly *below* their own
  average. Only the last episode spikes. Rewritten to say exactly that (each
  closes a full two points above the season around it).
- *Top Gear*'s "finale drawing a fraction of the old audience" was a viewership
  claim, and we have votes, not viewership. Replaced with the drop we actually
  measured.
- "nearly twice the fall of Game of Thrones" for House of Cards was loose
  (4.24 vs 2.55 is 1.7×, not 2×). Replaced with both numbers.

### Typography and terminology match the prose

Figure text now uses real em dashes rather than `--`, so figures and prose look
like one document. Jargon that had leaked into figure labels was replaced with
the words the essay itself uses: `r = +0.79` → "correlation +0.79",
`By sqrt(votes)` → "By the square root of votes". `|t| > 2` stays in fig05's
footnote because a plain-language gloss sits right beside it.

## Language convention

All code, comments, function/variable names, filenames and figure labels are in
**English**. Turkish is used only for discussion and (optionally) the final blog
narrative.
