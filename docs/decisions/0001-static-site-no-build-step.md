# 1. Static site published from the repo root, no build step

Date: 2026-11-14 · Status: **accepted** · Session: `arena-be3108f3`

## Context
The brief requires a GitHub Pages dashboard with subpages by category, every table row carrying a source link, and
a reviewable audit trail. The repository was empty (one 5-byte file). A framework would add a build pipeline,
dependencies and a place for data to be transformed invisibly.

## Decision
Plain HTML pages plus one stylesheet and one runtime (`assets/js/app.js`), with data as JS object literals in
`assets/data/*.js`. Markdown registers (`requirements.md`, `questions.md`, `suggestions.md`,
`flagged-for-review.md`, `sources.md`) and `coordination/*.json` are **generated** from those same objects by
`tools/gen_markdown.py`, so the GitHub view and the site view cannot drift.

## Consequences
+ Works offline from a clone; no lockfile, no CDN, no font fetch (the sandbox allowlist makes external assets a
  reliability risk, FL-015).
+ Every rendered value is traceable to a line in a data file that itself carries `{url, captured}`.
− No server-side rendering, so tables are built in the browser; a reviewer who disables JS sees the prose only.
  Accepted: the Markdown registers exist precisely for that reader.
− There is still no build, but there is now a *check* workflow (`.github/workflows/verify.yml`): CI that runs the
  same commands a reviewer can run locally, rather than CI that produces an artefact nobody can reproduce.
− Data files must stay parseable as the restricted JSON subset the generator understands (enforced by
  `tools/check_site.py`, which fails the run otherwise).
