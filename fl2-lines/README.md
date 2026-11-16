# fl2-lines — originated lines, price store and decision readiness

Session `arena/39dd0836-fl2`. This directory is self-contained: a published section
(`/fl2-lines/`), the code that generates every number on it, and the artefacts it reads.

## Regenerate everything

```bash
python3 fl2-lines/engine/compute_results.py   # verified results feed + price store + reconciliation
python3 fl2-lines/engine/compute_lines.py     # priors, calibration, ablation, originated lines (side -> total -> moneyline)
python3 fl2-lines/engine/compute_scores.py    # proper scores, controls, luck panel, correlations, ledger, leaderboard
python3 fl2-lines/engine/build_site.py        # render the 16 pages from those artefacts
python3 fl2-lines/engine/check.py             # fail if anything above is inconsistent or unsourced
```

Nothing in `*.html` is hand-typed: a number appears on a page because a CSV or JSON produced it.
`check.py` exits non-zero if a register row loses its clearing number, a link points at nothing,
a table renders the literal word `None`, or the results feed stops reproducing the official standings.

Optional, needs `npm install --no-save jsdom`:

```bash
node fl2-lines/engine/check_render.js   # every page parsed, script executed, sort+filter exercised
```

## Layout

| path | what it is | published? |
|---|---|---|
| `*.html`, `assets/` | the section's pages and stylesheet | yes |
| `data/derived/` | computed, regenerable, no row-level third-party payload | yes |
| `data/registers/` | readiness, pre-registration, suggestions, questions, flags, sources | yes (CSV copies) |
| `data/prices/` | the price-snapshot store, its policy and its hash manifest | yes |
| `data/official/` | transcriptions from official pages, with clock times and defects noted | yes |
| `data/ledger/` | hash-chained pre-kickoff forecast records | yes |
| `data/snapshots/` | raw dated captures of official pages | **no** — git-ignored, stored on branch `fl2-snapshots` and as Actions artefacts |
| `engine/` | the five scripts above plus the capture tool | no (source) |

The public/private split is deliberate: derived figures, intervals and hashes are published;
row-level third-party mirrors are not, because their redistribution terms were never read.

## The three rules this section obeys

1. **A value is either sourced or blank.** Every table row carries a link and, where the page
   prints one, a clock time. Unconfirmed finals are carried blank with a status, never guessed.
2. **A number needs its uncertainty.** Correlations publish `n`; skills publish a game-cluster
   bootstrap interval; ablations publish a confidence interval instead of a chosen penalty.
3. **A claim needs a gate that can fail.** The model-sanity gate aborts the build if the ratings
   stop tracking the market (that correlation collapsing was the only signal a sign error gave,
   so the gate now watches it); the totals collapse gate keeps
   two estimators published until 300 paired games pick one; the pre-registration rule keeps every
   backtest figure off the leaderboard, which is why that page shows an empty escrow.

## What is still blocked, and why

`data/registers/readiness.csv` is the authoritative list — one row per requirement line of the
brief with the gate that blocks it and the number that clears it. The recurring cause is not
modelling, it is capture: no official league depth chart exists, no source carries a 2026 opening
price, no per-game snap counts for 2026 are in the repository, and the mirror's depth extraction
writes zero rows for 2025–2026 (see `data/official/depth-defects.md`).
