# FL2 — NFL line origination workspace

Requirements, **verified data**, method and open questions for collecting, organising and analysing NFL information
in order to originate our own lines. Everything is published as a static site on GitHub Pages and lives in this
repository as plain HTML, JSON-ish JS data files and a small stdlib Python engine — no build step, no
dependencies, no CDN.

**Live site:** https://sassnarep3-star.github.io/FL2/

## The rules this repo is built under

1. **Every stored value carries a source URL and a capture timestamp.** No exceptions.
2. **A value that cannot be confirmed from an official source is left blank and flagged** — never inferred, never
   zero-filled, never "probably". See [`flagged-for-review.md`](flagged-for-review.md).
3. **Sources are tiered:** `official-league` · `official-club` · `official-regulator` · `commercial-operator` ·
   `academic` · `media-of-record` · `secondary-aggregator` · `self-recorded`. Only the first two carry
   official weight, and a row read from a search extract is labelled `snippet`, not `verified`.
4. **Model output is labelled "computed (ours)"** and never presented with the authority of an official number.
5. **[COORDINATION.md](COORDINATION.md) is the shared task board** for parallel agent sessions: claim before you
   work, keep file scopes disjoint, record sources and verification when you finish.

## Layout

| Path | What it is |
| --- | --- |
| `index.html`, `*.html` | the site: dashboard, executive summary, requirements, questions, suggestions, methodology, leaderboard, injuries, availability/depth, markets, data catalogue, verification, review, roadmap |
| `assets/data/*.js` | the data layer: registers, source catalogue, verification log, flags, the verified Week 10 2026 injury/roster snapshots |
| `assets/css/site.css`, `assets/js/app.js` | one stylesheet and one runtime: shared header/nav/footer, table renderer (filter, sort, per-row source links), computed stats |
| `engine/` | pure-stdlib reference implementation: odds/de-vig/Kelly, copula parlay pricing, deflation & luck statistics, the 16 validation gates, the pre-commitment registry |
| `tools/check_site.py` | mechanical audit: internal links, dataset/source coverage, register completeness, publish hygiene |
| `coordination/` | machine-readable copy of the task board + the review register, so data and site never disagree |
| `docs/decisions/` | decision log (ADR-style) — what was decided, what was rejected, and why |

## Verify it yourself

```bash
python3 -m engine.selftest      # 46 assertions: the arithmetic behind every "computed" figure
python3 tools/check_site.py     # link/source/registry audit; exits non-zero on any violation
```

Both must pass before the site is published. Current status is recorded in
[COORDINATION.md](COORDINATION.md#final-integration-record).

## Data snapshot in this repo

`assets/data/injuries.js` holds a transcription of the official **Week 10, 2026** injury report
([nfl.com/injuries](https://www.nfl.com/injuries/), captured 2026-11-14 UTC), cross-checked for two clubs against
the club's own report ([vikings.com](https://www.vikings.com/news/packers-injury-report-week-10-2026-nfl-season)),
plus captured excerpts of the official club roster pages. It is deliberately a *bounded* snapshot: the coverage gaps
are listed inside the file and rendered on the site.

## Not a betting service

This repository is model-development documentation. It publishes no prices, no tips and no solicitation to wager,
and automated bet placement is out of scope until the licensing and jurisdiction questions
([`questions.md`](questions.md) Q-14/Q-15) are answered from primary sources.
