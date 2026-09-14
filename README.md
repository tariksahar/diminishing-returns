# Do TV Shows Really Decline?

[![tests](https://github.com/tariksahar/diminishing-returns/actions/workflows/tests.yml/badge.svg)](https://github.com/tariksahar/diminishing-returns/actions/workflows/tests.yml)
[![read the essay](https://img.shields.io/badge/read-the%20essay-2a78d6)](https://tariksahar.github.io/diminishing-returns/docs/essay.html)

Everyone knows television declines: shows arrive full of promise, spend their
best ideas early, and coast downhill to a finish nobody asked for.

I tested that belief against **192,720 episode ratings from 3,234 shows**.

**It's mostly false.** Only about one in six shows clearly declines. The largest
group barely moves at all, more shows rise than fall, and the moment the belief
expects a collapse — the finale — is usually a show's *peak*.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/dark/fig01_slope_distribution.png">
  <img alt="Distribution of every show's overall rating trend" src="figures/fig01_slope_distribution.png">
</picture>

## What the data says

| Claim | Finding |
|---|---|
| "Shows decline over time" | Only **16.9%** clearly decline. **57.4%** are essentially flat, **25.7%** clearly rise. |
| "A show's quality drains away" | A show's second half lands within **0.07** of a rating point of its first half, even for the strongest starters. |
| "Finales ruin everything" | Season finales beat the rest of their season **72.5%** of the time. Series finales rise **71.3%** of the time. |
| "The final season is cursed" | Almost a coin flip: **50.5%** down, **49.2%** up. Only **12.6%** lose half a point or more. |
| "It depends on the genre" | Genre barely matters. **Age and length** do: every extra season costs **0.026** of a rating point, every decade newer adds **0.048**. |
| "The first season is always best" | The **last** season is the single best more often (**37%**) than the first (**27%**). |
| "But *my* shows declined" | Fair. Clear decline climbs with audience size, from **15%** among obscure shows to **43%** among the 60 household names. The belief fits the shows it's drawn from. |

Decline is real — it just lives somewhere other than where the belief puts it:
in shows that ran too long, in shows that are simply old, and in the handful of
shows famous enough for everyone to have an opinion about.

## Read it

Everything below also reads on the web at
**[tariksahar.github.io/diminishing-returns](https://tariksahar.github.io/diminishing-returns/)**,
which is the better place for the essay.

- **[The essay](docs/essay.md)** — *Your Favourite Show Probably Didn't
  Decline*: the full argument in plain language, with all nine figures. Start
  here.
- **[The technical report](docs/technical_report.pdf)** (PDF, 16 pages) — the
  same findings in formal form: abstract, data, methods, results with
  confidence intervals, robustness checks, limitations, references and the full
  regression table. Source in [LaTeX](docs/technical_report.tex) and
  [Markdown](docs/technical_report.md).
- **[Decision log](docs/decisions.md)** — every methodological choice, why it
  was made, and the traps that were caught along the way. This is the honest
  record: the mistakes are in here too.
- **[Report outline](docs/report_outline.md)** — the structure, with each
  finding's reliability tier.

## How the answer was reached

Each show's episodes are fitted with a weighted least-squares trend line
(`average_rating ~ normalized_episode_order`), and the slope of that line is the
show's decline-or-rise metric. Episodes are weighted by `sqrt(num_votes)` — enough
to trust well-voted episodes more, not so much that one viral backlash episode
sets the whole trend.

A few things this project deliberately did the harder way:

- **The naive result was wrong, and the clean test said so.** Correlating a
  show's trend with its own starting point produced a strong -0.37 "high shows
  decline" effect. That number is manufactured by shared noise. Splitting each
  show into two disjoint halves — nothing compared with itself — shrank the real
  effect to 0.07.
- **The right metric for the right question.** A single straight line cannot
  represent "flat, then a cliff", so it understates a late crash. The
  final-season question therefore uses a direct season-vs-rest comparison, not
  the slope.
- **Confounds were separated, not assumed apart.** Newer shows *are* shorter, so
  "newer shows rise" and "shorter shows rise" might have been one finding in two
  costumes. An OLS holding each fixed shows both survive independently.
- **The headline was checked against its own measurement error.** Each show's
  trend is an estimate, so shows near the ±0.5 cut can land on the wrong side by
  luck. Only a tenth of the spread between shows turns out to be noise, and it
  inflates the apparent decline share by roughly a point rather than hiding it.
  Getting that right meant discarding two standard corrections that give the
  wrong answer here for reasons worth reading about.
- **Colour was computed, not eyeballed.** The figure palette was validated for
  colour-blind separation and contrast (Machado-2009 simulation, OKLab ΔE). That
  check caught a pair of hues that were genuinely too close and would otherwise
  have shipped.
- **The conventions are enforced, not just stated.** Every published number is
  recomputed from the data by a [test suite](tests/) that runs on each push, and
  the rules that only existed as comments — never put these two colours in one
  chart, never derive a share as `100 - other` — are now tests that fail. Each
  of those guards exists because the mistake it catches had already happened
  once.

## Reproducing it

Built with Python 3.14 on Windows. The raw IMDb dumps are not committed
(~274 MB, and freely re-downloadable), so step 1 fetches them.

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows — on macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

1. **Get the data.** Download `title.basics.tsv.gz`, `title.episode.tsv.gz` and
   `title.ratings.tsv.gz` from <https://datasets.imdbws.com/> into `data/raw/`.
2. **Build the episode table.** `python src/build.py` — joins the three tables,
   applies the six inclusion filters, and writes
   `data/processed/episodes.parquet` (3,234 shows / 192,720 episodes).
3. **Run the analysis.** One script per question in `notebooks/`, named by
   phase. Seven of them export results to `data/processed/_phase2_*.json`; the
   rest are checks and counter-tests that print their findings.
4. **Draw the figures.** `python notebooks/phase3_figures.py` regenerates all
   nine figures into `figures/`.

Every script is run from the repository root.

**Checking it.** The published numbers are covered by a test suite that
recomputes them from `data/processed/` — the population and the inclusion
filters, every figure in the findings table above, and the palette rule that
keeps two indistinguishable colours out of the same chart. It runs against the
committed processed data, so it works on a fresh clone without the raw dumps:

```bash
pip install -r requirements-dev.txt
pytest
```

**One caveat on exact reproduction.** IMDb republishes these files daily, and
every number here comes from the snapshot downloaded on **22 July 2026**.
Re-running against a fresh download will shift the counts a little — new
episodes get rated, borderline shows cross the inclusion thresholds — so expect
the same conclusions rather than the same digits. The committed
`data/processed/` files are that original snapshot, so the figures and the
essay can always be rebuilt exactly as published.

## What's in here

```
data/processed/   the built episode table + one JSON per analysis
docs/             the essay, the technical report, the decision log, the outline
figures/          the nine report figures (fig01 … fig09), in three renderings
notebooks/        one script per question, named by phase
src/build.py      raw IMDb tables -> the analysis dataset
tests/            recomputes every published number from data/processed/
index.md          landing page for the GitHub Pages site (_config.yml, _layouts/)
```

Figures are produced by `notebooks/phase3_figures.py`, styled from
`notebooks/figstyle.py`. Each one recomputes its own inputs from
`data/processed/` and prints the values it annotates, so a figure cannot quietly
drift away from the numbers in the text.

## What counts as a show

A show is in the dataset if it is a `tvSeries` or `tvMiniSeries` with at least
13 rated episodes, at least 2 seasons, and an average of at least 50 votes per
episode. Game shows, reality TV, talk shows and news are excluded — "decline" is
a claim about a story, and those formats aren't telling one. Documentaries are
kept only under 100 episodes, which separates season-based series from
magazine strands. Full reasoning in the
[decision log](docs/decisions.md).

## Data and limitations

Ratings come from the [IMDb public datasets](https://datasets.imdbws.com/),
which are free for personal and non-commercial use. They reflect whoever chose
to vote, not a representative audience, and they are a present-day snapshot
rather than a record of how a show was received at the time. The analysis can
measure *where* ratings move and *how much* — never *why*.

## Licence

The code and the written analysis are [MIT licensed](LICENSE) — use them freely
with attribution. **The data is not mine to license:** IMDb's datasets remain
IMDb's, offered for personal and non-commercial use, and the derived tables in
`data/processed/` inherit those terms. [`DATA_LICENSE.md`](DATA_LICENSE.md)
spells out which files fall under which.

---

*A data analysis project by [tariksahar](https://github.com/tariksahar).*
