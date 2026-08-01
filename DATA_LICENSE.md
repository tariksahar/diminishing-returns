# What the MIT licence does and does not cover

[`LICENSE`](LICENSE) is a plain MIT licence, and it covers **the code and the
written analysis in this repository**: everything under `src/`, `notebooks/`,
`tests/`, the documents in `docs/`, and the figures in `figures/`.

It does **not** cover the underlying data, which is not mine to license.

## The data

Ratings, titles and episode structure come from the
[IMDb public datasets](https://datasets.imdbws.com/). Those files remain IMDb's
property and are offered under IMDb's own terms, which permit **personal and
non-commercial use only**. Nothing in this repository grants any right to the
data beyond what IMDb already grants.

The raw dumps are not committed here — `data/raw/` is git-ignored and step 1 of
the reproduction instructions fetches them from IMDb directly.

## Derived tables

`data/processed/` is committed so that the figures, the numbers and the test
suite can be reproduced on a fresh clone without a 274 MB download. Those files
are derived from the IMDb dumps and **inherit IMDb's terms**: personal and
non-commercial use. The MIT licence applies to the code that produced them, not
to their contents.

## In short

| Thing | Licence |
|---|---|
| `src/`, `notebooks/`, `tests/`, `docs/`, `figures/` | MIT — use freely with attribution |
| `data/processed/` | IMDb's terms — personal and non-commercial use |
| `data/raw/` (not committed) | IMDb's terms — fetch it from IMDb yourself |

If you want to build something commercial on this analysis, the code is yours
to take; the data is not, and you will need to source it elsewhere.
