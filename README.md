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
- [`fl2-signals/index.html`](fl2-signals/index.html) — Verified Signals (session 1374049c): 137 verified box scores replayed to an exact 32/32 standings match, the Week 10 injury report, eight validation gates with sample-size arithmetic, a parlay correlation sensitivity grid, and the model-pathology diagnosis behind gate G5.

- [`decision-desk/index.html`](decision-desk/index.html) — Decision Desk (session 3189b65d, 2026-11-17): the review surface the brief asked for. One ranked board merging the six suggestion registers (66 decisions from 68 register entries, with the id collisions and verbatim duplicates between files computed rather than mentioned), a merged question register with the five questions this session could close from the league's own pages, a designation-calibration page, a freshness diff (published standings vs the replay of the results feed vs the official page today), and a dated capture log with every fetch, every failure, and nine flagged irregularities. Rebuilt and re-checked in CI by `.github/workflows/verify-decision-desk.yml`.

The sentence above was written when there were four sections; there are now nine, and
the merge is itself row `hub-SG-11` / `DS-03` on the board at
[`decision-desk/suggestions.html`](decision-desk/suggestions.html).
Consolidating all those structures into one is proposed as a decision — see
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

## Decision readiness (2026-11-16)

The landing page carries a **decision-readiness table** — one row per requirement in the brief,
with the gate that blocks it and the number that would clear it (75 rows). Session
`arena/56a33eb6-fl2` re-verified the combined data against the live official pages on 2026-11-16:
32/32 standings rows reconcile exactly against the official standings once the Week-10 results are
applied, 96 Week-10 injury rows match the live league report exactly (Out 66 / Doubtful 10 /
Questionable 84 / blank 185 over 345 rows), and the two-sided "what would change our mind" field
was added to all 11 strategy entries. See `COORDINATION.md` for the full verification log.

## FL2 Dashboard section (session arena/48561869-fl2)

A second verified-data section lives at [`fl2-dashboard/index.html`](fl2-dashboard/index.html).
It contains its own verified official-source data (2026 standings for all 32 teams, the Week 10
schedule, the full Week 10 injury report with 345 rows, and a verified depth-chart example) rendered
as a clean dashboard with a dedicated suggestions section, a questions/answers register, strategy
design with validation gates and luck-removal scoring, a leaderboard specification, and a Flagged for
Review page. Every data row links to the official source used to verify it; values that could not be
confirmed were left blank and flagged. Its data records live in
[`fl2-dashboard/data/verified/`](fl2-dashboard/data/verified/) with a fetch log.
