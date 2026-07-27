# Do Television Series Decline Over Their Run? Evidence from 192,720 IMDb Episode Ratings

**Tarık Şahar** · Istanbul Technical University, Data Science and Analytics
Data snapshot: 22 July 2026 · Companion to the narrative essay in
[`report_draft.md`](report_draft.md); all design decisions are logged in
[`decisions.md`](decisions.md).

---

## Abstract

The belief that television series decline over their run is widely held and
rarely measured. Using the complete IMDb episode-rating corpus, we construct a
panel of 192,720 rated episodes from 3,234 series and estimate a per-show
quality trajectory as the slope of a vote-weighted least-squares fit of episode
rating on normalised episode order. We find the folk belief is false for the
typical series: only 16.9% of shows decline by at least half a rating point
across their entire run, 57.4% are essentially flat, and 25.7% clearly rise.
A coupling-free test — regressing each show's second-half mean on its
separately measured first-half mean — yields a correlation of +0.793 and a
slope of 0.886 against a noise-only expectation of 0.983, implying a real but
negligible extra decline of 0.07 rating points for the strongest starters.
Season finales exceed the remainder of their own season 72.6% of the time, and
series finales exceed their final season 71.6% of the time, so the moment the
belief expects collapse is typically a local maximum. Among ended series the
final season is weaker than the rest of the run in 50.6% of cases with a median
change of -0.006, and only 12.6% lose half a point or more; this conclusion is
insensitive to the threshold chosen. Decline is concentrated rather than
general: show length (-0.026 per season, t = -6.8) and premiere year (+0.048
per decade, t = +4.8) each survive mutual adjustment, whereas genre is largely
uninformative once age and length are controlled. The model explains only 6.0%
of between-show variance, so these are reliable but small effects. We argue the
persistence of the belief is consistent with availability bias: the minority of
genuine collapses is disproportionately composed of highly-viewed series.

**Keywords:** television ratings, quality trajectories, regression to the mean,
availability bias, IMDb

---

## 1. Introduction

That television series deteriorate over time is close to received wisdom. The
claim is specific enough to be testable — it asserts that a show's quality
declines monotonically or near-monotonically with time on air — yet it is
usually supported by enumeration of memorable cases rather than by measurement.

This report tests the claim directly. We ask five questions:

1. What is the distribution of per-show quality trajectories?
2. Is a show's later quality predictable from its earlier quality, and does
   high early quality decay?
3. Do finales — season and series — underperform, as the belief implies?
4. Is there a "final-season curse"?
5. If decline exists, which show characteristics predict it?

Our contribution is not a new method but a disciplined application of standard
ones to a question usually argued anecdotally, with explicit attention to the
artefacts that make naive versions of this analysis produce the opposite
answer. Section 5 documents four such artefacts, one of which produced an
apparently strong effect that survived neither reformulation nor replication.

---

## 2. Data

### 2.1 Source

All ratings come from the IMDb public datasets [1], downloaded on
**22 July 2026**. IMDb republishes these files daily; counts drift as new
episodes accumulate ratings and borderline series cross inclusion thresholds,
so the exact figures below are reproducible only against the committed
snapshot in `data/processed/`.

Three tables are used:

| Table | Role |
|---|---|
| `title.episode` | maps each episode to its parent series, season and episode number |
| `title.ratings` | mean rating and vote count per title |
| `title.basics` | title type, primary title, start year, end year, genres |

### 2.2 Construction

Episodes with a missing season or episode number are dropped, since ordering
within a series is required. The episode table is inner-joined to ratings — so
only episodes carrying at least one vote survive — and then to the series rows
of `title.basics` restricted to `tvSeries` and `tvMiniSeries`. Episodes are
ordered by season then episode number, and a within-show sequential index
`overall_order` is assigned. Series with an empty `endYear` are flagged
`ongoing` rather than dropped. The result is one row per rated episode
(`src/build.py` → `data/processed/episodes.parquet`).

### 2.3 Inclusion criteria

Six filters define the analysis population:

| Criterion | Threshold | Rationale |
|---|---|---|
| Title type | `tvSeries` or `tvMiniSeries` | excludes films, specials, episodes as titles |
| Rated episodes | ≥ 13 | a trajectory requires enough observations to estimate |
| Seasons | ≥ 2 | "decline across seasons" is undefined for one season |
| Mean votes per episode | ≥ 50 | limits measurement noise from thinly-rated series |
| Genre exclusions | not Game-Show, Reality-TV, Talk-Show, News | non-narrative formats have no season arc to decline |
| Documentary cap | Documentary-tagged kept only if < 100 episodes | separates season-based documentary series from magazine strands |

The documentary rule is platform-independent, since the data carry no channel
or platform field. Full rationale for each threshold is in `decisions.md`.

### 2.4 Sample

| Property | Value |
|---|---|
| Series | 3,234 |
| Rated episodes | 192,720 |
| Total votes represented | 160,926,754 |
| Premiere years | 1949–2026 |
| Ongoing at snapshot | 524 (16.2%) |
| Episodes per series | median 36 (IQR 22–69, max 1,234) |
| Seasons per series | median 3 (IQR 2–5, max 70) |
| Mean rating per series | median 7.72 (IQR 7.39–8.03) |
| Votes per episode | median 190 |

The sample is right-skewed in length: 485 series exceed 100 episodes and 127
exceed 200. These were retained rather than trimmed; the trajectory metric
normalises episode order to [0, 1] so that run length cannot mechanically
inflate a slope, and length is analysed as an explanatory variable in its own
right (§4.5).

---

## 3. Methods

### 3.1 Per-show trajectory

For each series, let $x_i \in [0,1]$ be the normalised position of episode $i$
in the run and $y_i$ its mean rating. We fit

$$y_i = a + b x_i + \varepsilon_i$$

by weighted least squares with weights $w_i = \sqrt{v_i}$, where $v_i$ is the
episode's vote count.

![Example fitted trajectories](../figures/fig08_example_trajectories.png)

**Figure 1.** Three fitted trajectories, one from each outcome band defined
below. Points are episode means sized by vote count; the straight line is the
estimate $\hat{b}$, the grey curve the quadratic of §3.3.

The estimate $\hat{b}$ is the show's **trend**: the
rating points gained or lost between first and last episode. A show is
classified as *clearly declining* if $\hat{b} \le -0.5$, *clearly rising* if
$\hat{b} \ge +0.5$, and *essentially flat* otherwise. The half-point cut is a
perceptibility convention, not a statistical one; §5.3 reports its sensitivity.

**Choice of weights.** Vote counts vary substantially within a series (median
max/min ratio 3.5, exceeding 10 for a tenth of series), so an unweighted fit
lets a 51-vote episode influence the trend as much as a 500,000-vote one.
Weighting by $v_i$ directly is optimal under an i.i.d.-votes noise model, but
IMDb vote counts violate it: notorious episodes attract votes for reasons
unrelated to measurement precision. In *Game of Thrones*, four of the six
most-voted episodes belong to the final season and all are rated far below the
series mean; linear weighting nearly doubles the fitted slope relative to an
unweighted fit (-2.206 vs -1.024), while $\sqrt{v_i}$ gives -1.546.
Log-weighting was also examined and is nearly indistinguishable from unweighted
in practice. We therefore use $\sqrt{v_i}$ throughout.

![Three weighting schemes on Game of Thrones](../figures/fig09_weighting_choice.png)

**Figure 2.** The same 73 episodes under three weighting schemes. Raw vote
weighting lets the heavily-voted final-season cluster set the trend for the
whole run; the single most-voted episode is in fact a mid-run 9.9.

### 3.2 Final-season effect

The slope in §3.1 answers "does this series decline at a roughly constant
rate", which is *not* the final-season question: a straight line fitted across
all episodes is anchored by the majority and understates a late, sharp drop.
For *Game of Thrones* the true season-8 mean is 6.40 against 8.95 for seasons
1–7, yet the fitted line predicts 7.6–8.3 in that range under every weighting
scheme. We therefore define, for ended series only,

$$\Delta = \bar{y}_{\text{final season}} - \bar{y}_{\text{all earlier episodes}}$$

and use $\Delta$ for all final-season claims. A series is termed *clearly
cursed* if $\Delta \le -0.5$.

### 3.3 Trajectory shape

A weighted quadratic $y = a + bx + cx^2$ is fitted per series with the same
weights. Where the vertex $-b/2c$ lies inside $[0.15, 0.85]$ and $|c| > 0.05$,
the series is labelled **jumped-the-shark** ($c<0$: interior maximum) or
**found-itself** ($c>0$: interior minimum); otherwise **straight line**, meaning
the fitted curve has no turning point inside the observed run and is monotone
over it. Note this last class is not "flat": it contains steep monotone
decliners and risers alike. Volatility is the weighted RMSE of the linear fit's
residuals.

### 3.4 Peak location

For each series we take the argmax of season means, reported both as an
absolute season number and as a normalised rank $(\text{rank}-1)/(n_{\text{seasons}}-1)$.
Because the sample is dominated by short series, aggregate statements about the
peak are reported stratified by season count (§4.6).

### 3.5 Cross-sectional model

To separate era, length and genre we estimate by OLS

$$\hat{b}_j = \beta_0 + \beta_1 \text{year}_j + \beta_2 \text{seasons}_j + \beta_3 \text{ongoing}_j + \sum_g \gamma_g \, \mathbb{1}[g \in \text{genres}_j] + u_j$$

over all $n = 3{,}234$ series, with premiere year centred and genres entered as
16 non-exclusive indicators. Classical standard errors are reported; given the
sample size and the magnitude of the leading $t$-statistics, robust
alternatives would not change any conclusion drawn here.

---

## 4. Results

### 4.1 The distribution of trajectories

![Distribution of per-show trends](../figures/fig01_slope_distribution.png)

**Figure 3.** Distribution of the per-show trend $\hat{b}$.

The trend distribution is centred slightly above zero (mean +0.073, median
+0.109, SD 0.778, IQR -0.296 to +0.515). By sign, 57.4% of series trend upward
and 42.6% downward. By magnitude, **16.9% decline clearly, 57.4% are
essentially flat, and 25.7% rise clearly**. Under the folk belief we would
expect a distribution massed below zero; we observe a distribution massed *at*
zero with a mild positive tilt.

### 4.2 Stability across a series' run

![First half versus second half](../figures/fig02_halves_stability.png)

**Figure 4.** Each series' first-half mean against its separately measured
second-half mean.

Splitting each series into disjoint halves, first-half and second-half means
correlate **+0.793**. Regressing second on first yields a slope of **0.886**,
below unity and therefore consistent with some regression to the mean. The
relevant benchmark is not 1 but the reliability of a half-mean: an odd/even
split-half correlation with the Spearman–Brown correction [2, 3] gives
**0.983**, which is what a pure "stable quality plus measurement noise" process
would produce. The observed 0.886 falls modestly below this, so a genuine extra
decline of strong starters exists — but it is very small. In levels,
top-quartile starters (first-half mean 8.32) lose **0.07** rating points in
their second half, and bottom-quartile starters (6.94) gain 0.07.

### 4.3 Finale structure

![Finale premium](../figures/fig03_finale_premium.png)

**Figure 5.** Finale and premiere premia relative to the rest of the season.

Restricting to seasons of at least four rated episodes (n = 12,931 seasons):

| Contrast | Mean | Share above baseline |
|---|---|---|
| Season finale vs rest of its season | **+0.253** | **72.6%** |
| Season premiere vs rest of its season | -0.040 | 43.3% |
| Series finale vs its final season body (n = 3,082) | **+0.256** | **71.6%** |

Finales are systematically the strongest episode of their season, premieres are
mildly below average, and the asymmetry is large. Only **9.4%** of series
finales fall 0.5 points or more below their final season — the memorable
"finale flop" is a one-in-ten event.

### 4.4 The final-season effect

![Final-season delta and threshold sweep](../figures/fig04_final_season_curse.png)

**Figure 6.** Distribution of $\Delta$ for ended series, with a sensitivity
sweep over the "cursed" threshold.

Across 2,710 ended series, 50.6% have a weaker final season and 49.4% a
stronger one, with median $\Delta = -0.006$ and mean $-0.049$. **12.6%** are
clearly cursed at the -0.5 cut. The cursed minority is dominated by
well-known series (*House of Cards* -4.24, *Game of Thrones* -2.55, *Master of
None* -2.54, *The Promised Neverland* -2.28), which we read as the mechanism
sustaining the belief: the observable instances are disproportionately the
famous ones. This interpretation is not established by our data; it is
consistent with them.

$\Delta$ and $\hat{b}$ correlate +0.80, so roughly a third of their variation
is independent and they are not interchangeable. Notably, the pure "flat then
cliff" case is essentially absent: all 32 series with $\Delta \le -1.0$ and at
least 30,000 votes also have a negative overall slope, which is mechanical — a
late crash necessarily tilts a fitted line downward.

### 4.5 Era, length and genre

![Coefficient plot](../figures/fig05_era_length_genre.png)

**Figure 7.** OLS coefficients with 95% confidence intervals.

Raw cross-sectional cuts are heavily confounded: median seasons per series
falls from 5 in the 1950s to 2 in the 2020s while the ongoing share rises from
3% to 41%. After mutual adjustment (full table in Appendix A):

- **Length**: $-0.0261$ per season ($t = -6.78$). Ended 2–3-season series
  average $+0.217$; ended 6+-season series $-0.120$, with 60.8% of 6+-season
  series declining.
- **Era**: $+0.0048$ per year, i.e. $+0.048$ per decade ($t = +4.81$). The
  effect survives restriction to ended series and to fixed length bands, so it
  is not a length or ongoing-status artefact. 59.3% of pre-2000 series decline
  against 38.6% of later ones.
- **Genre**: only Animation ($+0.233$, $t = 5.57$), Documentary ($-0.235$,
  $t = -2.73$), Biography ($-0.244$, $t = -2.25$), Adventure ($-0.165$),
  Thriller ($-0.153$) and Romance ($-0.143$) reach significance. Drama, Comedy,
  Crime and Action — the bulk of the sample — are indistinguishable from zero.

**The model explains 6.0% of between-show variance** ($R^2 = 0.0603$, residual
SD 0.756). The effects are estimated precisely but are small relative to the
idiosyncratic differences between series; no combination of a show's age,
length and genre comes close to determining its trajectory.

### 4.6 Shape and peak location

![Trajectory shapes](../figures/fig06_trajectory_shapes.png)

**Figure 8.** Share of series by trajectory shape and the mean fitted arc of
each class.

The rise-then-fall arc is the single most common shape (**44.6%**), against
35.2% straight-line and 20.3% found-itself. Within the jumped-the-shark class
the vertex sits at a median normalised position of 0.50, with only 6.2% of
peaks in the 0.15–0.25 band, so the label describes a genuine interior maximum
rather than a decline from the outset. The arc is nonetheless shallow: median
rise to the peak is 0.37 rating points and median fall from it 0.33. The
classification is insensitive to the curvature cut-off — class shares move from
44.6/35.1/20.3 at a threshold of 0 to 43.7/36.6/19.8 at 0.20 — because the
binding condition is the location of the vertex, not the size of $c$.

![Peak location](../figures/fig07_peak_location.png)

**Figure 9.** Location of the best season by series length.

The mean best season rises with run length (1.6 at two seasons, 2.5 at four,
3.1 at five, 3.8 at seven, 5.8 at eight or more) while its normalised position
remains near the middle (0.46–0.59 across all lengths). An earlier cut on
three-season series alone suggested a "sophomore surge"; that is an aggregation
artefact of a sample dominated by short series, in which season 2 *is* the
middle. Importantly, the mean masks the distribution: among series with at
least five seasons (n = 915), the peak falls in the first third 41.7% of the
time, the middle third 24.9%, and the last third 33.3% — the middle is the
*least* likely location, and the mean sits at 0.5 only because the ends
balance. Finally, the last season is the single best season **37.2%** of the
time against **27.1%** for the first, contradicting the "first season is
always best" claim in aggregate.

---

## 5. Robustness and threats to validity

### 5.1 Mathematical coupling

An early formulation correlated each show's slope with its own fitted
intercept, producing $r = -0.373$ and the apparent finding that high-quality
series decline hardest. This is an artefact: both quantities are estimated from
the same episodes and share noise, so the correlation is partly manufactured
[4]. The disjoint-halves design in §4.2 removes the shared-noise channel
entirely and reduces the effect to 0.07 rating points. We report the clean
estimate and retain the biased one only as a documented negative result.

### 5.2 Metric–question mismatch

As shown in §3.2, a single linear slope cannot represent a flat-then-cliff
trajectory and understates late crashes. Using the slope as a proxy for the
final-season question would have understated *Game of Thrones*' season-8 drop
by roughly 1.2–1.9 rating points. All final-season claims therefore use the
direct season contrast.

### 5.3 Threshold sensitivity

The "clearly cursed" share is 29.2% at $\Delta \le -0.2$, 22.4% at $-0.3$,
12.6% at $-0.5$, 6.8% at $-0.75$ and 3.7% at $-1.0$: the conclusion that
cursed final seasons are a minority holds at every reasonable cut. As a
scale-free check we also computed $\Delta$ divided by the SD of the series' own
non-final-season episode ratings; 23% of ended series reach a "large" effect in
Cohen's conventional sense [5], and 98% of series flagged by the raw -0.5 rule
also clear the large-effect bar, so the intuitive and principled criteria
select nearly the same set.

### 5.4 Low-vote tails

Within a series, episode position correlates $-0.74$ with log vote count:
later episodes are systematically less voted. Any late-leaning result is
therefore on weaker ground than an early-leaning one. This matters most for the
found-itself class: the median last-third episode carries only ~132 votes and
39.7% of found-itself series have a last third averaging under 100 votes.
Re-fitting after dropping sub-100-vote episodes, 56.5% of found-itself series
retain the label, 20.2% revert to decline or flat, and 23.4% become untestable.
The label is not a weighting artefact (94.5% survive an unweighted refit) but
roughly a fifth of it is a thin-data artefact, and we treat it accordingly.

### 5.5 Confounding

"Newer series rise", "shorter series rise" and "older series decline" are not
three findings: newer series are shorter. The §3.5 specification holds each
fixed, and both era and length survive. We additionally verified the era effect
within ended series and within a fixed 2–3-season band, where it does not fade.

---

## 6. Limitations

**Ratings are not quality.** IMDb scores are contributed by self-selected
voters, not a representative audience panel. Some low outliers reflect
coordinated review-bombing rather than dispersed judgement; vote weighting
dampens but does not remove this.

**Ratings are a present-day snapshot.** Each rating is the value standing today,
not the reception recorded at broadcast. A series that ended in 2010 is scored
in 2026 largely by viewers who arrived later and already knew its ending. The
finale premium in §4.3 may therefore partly reflect retrospective softening.
The dataset carries no time dimension with which to test this.

**Causes are unobserved.** The design measures where ratings move, never why.
Off-screen shocks are indistinguishable from creative decline: *House of Cards*
lost its lead actor amid scandal and had its final season cut from thirteen
episodes to eight; *Top Gear* lost its presenting team; *Scrubs* became a
different programme in its ninth season. All three appear in the data simply as
"decline".

**Format leakage.** The genre filters remove the main non-narrative categories,
but sketch and review programmes tagged only as Comedy survive — most
consequentially *Saturday Night Live* (1,010 episodes). A curated blacklist was
rejected as unreproducible; the affected count is too small to move any
reported figure, and we disclose it rather than patch it.

**Survivorship in the vote threshold.** Requiring ≥ 50 mean votes per episode
excludes obscure series, so results generalise to series with a measurable
audience rather than to all television.

---

## 7. Conclusion

The proposition that television series decline over their run is not supported
for the typical series. Most series are close to flat across their entire run,
more rise than fall, later quality is strongly predictable from earlier quality,
and the extra decline of strong starters is an order of magnitude smaller than
the belief implies. Where the belief predicts collapse most confidently — the
finale — the data show a local maximum in roughly seven cases out of ten.

Decline is nonetheless real in identifiable subsets: long-running series, older
series, and a 12.6% minority of ended series whose final season drops
materially. That minority is composed disproportionately of widely-watched
titles, which offers a parsimonious account of how a belief this durable
survives evidence this consistent — the counterexamples are, by construction,
the ones nobody talks about.

The effects we can identify are precisely estimated but jointly explain 6% of
the variation between series. Whatever determines a show's trajectory is mostly
not its age, its length, or its genre.

---

## References

[1] IMDb. *IMDb Non-Commercial Datasets.* <https://datasets.imdbws.com/>
Accessed 22 July 2026.

[2] Spearman, C. (1910). Correlation calculated from faulty data.
*British Journal of Psychology*, 3(3), 271–295.

[3] Brown, W. (1910). Some experimental results in the correlation of mental
abilities. *British Journal of Psychology*, 3(3), 296–322.

[4] Barnett, A. G., van der Pols, J. C., & Dobson, A. J. (2005). Regression to
the mean: what it is and how to deal with it. *International Journal of
Epidemiology*, 34(1), 215–220.

[5] Cohen, J. (1988). *Statistical Power Analysis for the Behavioral Sciences*
(2nd ed.). Lawrence Erlbaum Associates.

[6] Machado, G. M., Oliveira, M. M., & Fernandes, L. A. F. (2009). A
physiologically-based model for simulation of color vision deficiency.
*IEEE Transactions on Visualization and Computer Graphics*, 15(6), 1291–1298.
(Used to validate the figure palette for colour-vision deficiency.)

---

## Appendix A. Full cross-sectional model

OLS of the per-show trend on era, length, ongoing status and 16 non-exclusive
genre indicators. $n = 3{,}234$, $R^2 = 0.0603$, residual SD 0.756. Premiere
year is centred; the genre reference category is "not carrying that genre".

| Variable | Coefficient | Std. error | *t* | Series |
|---|---:|---:|---:|---:|
| Intercept | 0.2541 | 0.0537 | 4.73 | — |
| Premiere year (per year) | 0.0048 | 0.0010 | 4.81 | — |
| Seasons | −0.0261 | 0.0038 | −6.78 | — |
| Ongoing | −0.0422 | 0.0387 | −1.09 | 524 |
| Animation | 0.2332 | 0.0418 | 5.57 | 680 |
| Action | 0.0414 | 0.0413 | 1.00 | 821 |
| Family | 0.0254 | 0.0617 | 0.41 | 172 |
| Comedy | −0.0231 | 0.0389 | −0.60 | 1,365 |
| Drama | −0.0297 | 0.0359 | −0.83 | 1,733 |
| Crime | −0.0446 | 0.0381 | −1.17 | 788 |
| History | −0.0506 | 0.0810 | −0.62 | 101 |
| Mystery | −0.0552 | 0.0467 | −1.18 | 405 |
| Sci-Fi | −0.0726 | 0.0745 | −0.97 | 114 |
| Horror | −0.1064 | 0.0733 | −1.45 | 125 |
| Fantasy | −0.1086 | 0.0566 | −1.92 | 214 |
| Romance | −0.1428 | 0.0531 | −2.69 | 254 |
| Thriller | −0.1529 | 0.0615 | −2.49 | 186 |
| Adventure | −0.1651 | 0.0440 | −3.75 | 716 |
| Documentary | −0.2345 | 0.0858 | −2.73 | 101 |
| Biography | −0.2436 | 0.1083 | −2.25 | 53 |

## Appendix B. Reproduction

See the [repository README](../README.md). Briefly: download the three IMDb
tables into `data/raw/`, run `python src/build.py` to construct
`data/processed/episodes.parquet`, run the `notebooks/phase2_*.py` scripts to
regenerate the analysis exports, and `python notebooks/phase3_figures.py` to
redraw all nine figures. Every figure recomputes its own inputs and prints the
values it annotates, so figures and text cannot diverge silently.
