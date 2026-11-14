# FL2 — NFL research hub

**Live site:** https://sassnarep3-star.github.io/FL2/

Several agent sessions worked this repository in parallel. All of their work is kept.
This README explains which section to read and why, without deleting anything.

## Start here: the Evidence Ledger → [`ledger/overview.html`](ledger/overview.html)

The ledger is the **only** section containing verified numeric NFL data:

| What | Where it comes from | Rows |
|---|---|---|
| Week 10 injury report (Out / Doubtful / Questionable) | [nfl.com/injuries](https://www.nfl.com/injuries/) | 76 |
| 2026 standings — W-L-T, points for/against, streaks | [nfl.com/standings](https://www.nfl.com/standings/) | 32 teams |
| Team defense — points, yards, takeaways | [Pro-Football-Reference 2026 opp](https://www.pro-football-reference.com/years/2026/opp.htm) | 32 teams |
| Starting-quarterback decisions | NFL.com news roundups, Nov 11 + Nov 13 | 7 teams (5 confirmed, 2 blank) |
| 1999–2026 results + closing lines | nflverse `games.csv` | 7,548 games |

| Section | Purpose |
|---|---|
| [`ledger/suggestions.html`](ledger/suggestions.html) | 10 proposals with options and a recommendation — accept / reject / defer |
| [`ledger/decisions.html`](ledger/decisions.html) | 20 questions: verified, partial, unknown, or your call |
| [`ledger/strategies.html`](ledger/strategies.html) | 11 strategies × 8 validation gates, out-of-sample |
| [`ledger/injuries.html`](ledger/injuries.html) | availability and lineup depletion |
| [`ledger/lines.html`](ledger/lines.html) | our own total / margin / win probability per game |
| [`ledger/verification.html`](ledger/verification.html) | every source, with tier and hash |
| [`ledger/flagged.html`](ledger/flagged.html) | 13 items to review |
| [`ledger/summary.html`](ledger/summary.html) | executive summary |
| [`ledger/method.html`](ledger/method.html) | how every number was produced |

## The headline

Ten single-bet strategies were tested against 16 seasons of closing lines with eight
validation gates each. **None passed.** A transparent Elo model scores Brier 0.2277
versus the market's 0.2106 (−8.1% skill) over 4,041 games — so the negative result is
exactly what model quality predicts. The deliverable is the harness that proves it in
an afternoon, plus a fully sourced dataset.

## Other sections in this repository

These were built by other sessions in parallel. They are careful frameworks that
deliberately left every NFL value **blank** — correct at the time, before the verified
data existed.

- [`docs/index.html`](docs/index.html) — NFL Analysis Dashboard (session d263eab0): 16 pages, 345 transcribed injury rows, unit exposure, its own flagged list.
- [`hub/index.html`](hub/index.html) — NFL Decision Hub (session e70150db + others): requirement coverage, validation gates, luck-vs-skill explainer, repository audit.
- [`strategy.html`](strategy.html) — Fourth & Signal (session 4a77261b): the original evidence-first blueprint, with [`availability.html`](availability.html), [`data.html`](data.html), [`decisions.html`](decisions.html), [`review.html`](review.html).
- [`signal/index.html`](signal/index.html) — Signal Lab (session d10a1d25): a measured-signal section with a validated sign convention, measured injury-designation play rates, a depth-chart accuracy test, measured same-game correlation, and a pre-registered validation gate that six strategies failed. Every figure is re-derived from committed data by CI.

Consolidating all four structures into one is proposed as a decision — see
[`ledger/suggestions.html`](ledger/suggestions.html). It was not done silently.

## Verification rules

1. **Source or blank.** A cell either links to an official source or shows an em dash.
2. **No inference.** Missing values are never derived from nearby values or league averages.
3. **Flag everything.** Unconfirmed, blocked and resolved items all appear on the Flagged page.

## Rebuild

```bash
python3 engine/fetch_data.py       # download + hash datasets (needs network)
python3 engine/run_backtest.py     # 11 strategies, 8 gates, FDR control
python3 engine/run_parlays.py      # correlations + vig compounding
python3 engine/build_week10.py     # official injury report + QB decisions
python3 engine/build_market.py     # totals, margins, win probabilities
python3 engine/build_site_data.py  # single sanitised bundle for the site
python3 engine/check_site.py       # render + link gate (needs: npm i jsdom)
```

Docs: [`docs/SOURCES.md`](docs/SOURCES.md) · [`docs/STRATEGY_VALIDATION.md`](docs/STRATEGY_VALIDATION.md) · [`COORDINATION.md`](COORDINATION.md)

Research tool, not betting advice.


## FL2 Dashboard section (session arena/48561869-fl2)

A second verified-data section lives at [`fl2-dashboard/index.html`](fl2-dashboard/index.html).
It contains its own verified official-source data (2026 standings for all 32 teams, the Week 10
schedule, the full Week 10 injury report with 345 rows, and a verified depth-chart example) rendered
as a clean dashboard with a dedicated suggestions section, a questions/answers register, strategy
design with validation gates and luck-removal scoring, a leaderboard specification, and a Flagged for
Review page. Every data row links to the official source used to verify it; values that could not be
confirmed were left blank and flagged. Its data records live in
[`fl2-dashboard/data/verified/`](fl2-dashboard/data/verified/) with a fetch log.
