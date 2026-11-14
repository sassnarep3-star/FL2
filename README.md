# FL2 — NFL research & decision ledger

A verified 2026-season NFL snapshot, a line model, and a validation harness that
rejects strategies instead of promoting them.

**Live site:** https://sassnarep3-star.github.io/FL2/

## The headline

Ten single-bet strategies were tested against 16 seasons of closing lines with
eight validation gates each. **None passed.** A transparent Elo model scores
Brier 0.2277 versus the market's 0.2106 (−8.1% skill) over 4,041 games — so the
negative result is exactly what the model quality predicts. What this project
delivers is the machinery that proves that quickly, plus a fully sourced dataset.

## What is verified, and what is not

| Area | Status | Detail |
|---|---|---|
| Team offense/defense, standings, injury report | ✅ verified | linked to nfl.com and Pro-Football-Reference |
| Week 10 quarterback availability | ⚠️ partial | 5 teams confirmed, 2 left blank (BAL, LAC) |
| Player-level statistics | ❌ unavailable | release assets unreachable from the build environment |
| Market prices | ⚠️ not citable | no official publisher; aggregated file only, always labelled |
| Validated strategy | ❌ none | 11 tested, 0 passed 8/8 gates |

Every table row carries a source link. Values that could not be confirmed are
**blank and flagged** — never estimated. See the *Flagged for Review* page.

## Pages

`index` overview · `suggestions` proposals to accept/reject/defer ·
`decisions` 20 open questions · `strategies` leaderboard and gates ·
`injuries` availability · `lines` our own numbers · `verification` sources ·
`flagged` what to check · `summary` executive summary · `method` methodology

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
