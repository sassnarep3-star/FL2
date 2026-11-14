# Fourth & Signal — NFL research dashboard

An evidence-first static research site for planning an NFL line-origination and strategy-validation competition. It is a research scaffold, **not** an NFL product, wagering service, betting recommendation, or claim of predictive edge.

## Site map

- `index.html` — executive summary and evidence snapshot
- `decisions.html` — prioritized decision questions, known/unknown answers, and suggested discovery work
- `strategy.html` — candidate single-bet, player-prop, parlay and prop-combo hypotheses; validation gates and correlation requirements
- `availability.html` — source-backed injury-report fields and a design for offense/defense depth and replacement tracking
- `data.html` — reviewed source inventory, project inspection notes and proposed data model
- `review.html` — open unverified items and their closure evidence

## Verification boundary

Repository inspection began with a 5-byte README and no application, data, odds, player-game records, model or measured results. Official NFL source pages were inspected for schedules, player stats, injuries, players, rules and a hosted gamebook sample. They establish source pathways, not the existence of a usable historical feed, a license, complete coverage, or a profitable signal. The NIST/SEMATECH glossary is used only for general statistical-method terminology. Unknown values are blank; no performance or correlation numbers are fabricated. Details and links are in `data.html` and `COORDINATION.md`.

## Run locally

This is plain static HTML/CSS. Open `index.html` directly, or run a static server such as `python3 -m http.server 8000` from the repository root.

## GitHub Pages

`.github/workflows/pages.yml` validates the static site's local links and publishes the repository root to GitHub Pages on pushes to `main`, using GitHub's Pages Actions deployment. The repository's Pages source must be set to **GitHub Actions** in Settings → Pages. Publication happens once the workflow is run with the required repository permissions. The current working branch is intentionally not the default `main` deployment target.

## Limitations

No automatic NFL data ingestion, odds provider, historical database, forecasts, user accounts, wagering or rewards are implemented. Before those are added, verify data access and reuse terms, time-stamped source integrity, price/settlement definitions, geography and competition rules, and independent time-ordered validation. See `decisions.html` and `review.html`.
