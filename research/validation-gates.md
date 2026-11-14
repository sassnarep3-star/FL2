# Validation Gates

Every strategy must clear these gates before it is allowed onto the leaderboard. A gate is a number,
not an opinion. All gates are computed in `tools/analytics.py` and stored in
`data/derived/analytics.json`.

## Gate definitions

| Gate | Rule | Why it exists |
|------|------|---------------|
| **G0 — Data provenance** | Every input row traces to an official URL; no inferred or imputed values | Kills fabricated inputs before they reach a model |
| **G1 — No look-ahead** | A game's prediction may use only games with an earlier week number | The most common way a backtest lies |
| **G2 — Out-of-sample hit rate vs break-even** | Win rate must exceed the break-even rate for the price at the sample size achieved | You cannot claim profit below break-even |
| **G3 — Statistical significance** | Two-sided p ≤ 0.05 against the break-even rate | Removes luck (requirement 4) |
| **G4 — Proper scoring rule** | Brier skill score > 0 against the base-rate null, *and* log-loss better than the null | A hit rate can look good by picking only favourites; a proper score cannot |
| **G5 — Side balance** | The model must not pick one side in >70% of graded games unless that side's base rate justifies it | Directly from the pathology found in the walk-forward model (see below) |
| **G6 — Correlation honesty** | Any parlay price must state the ρ used, or publish a sensitivity grid instead of a point estimate | Prevents fake precision in parlay pricing |
| **G7 — Sample-size disclosure** | Report the n required for 80% power at the claimed edge | Makes the "is this luck?" question answerable |

## Results on the current dataset

### Candidate S-01 — Walk-forward point-differential model, free intercept

| Gate | Result | Value | Source |
|------|--------|-------|--------|
| G0 provenance | **PASS** | inputs are `data/games.json`, each row linked to `nfl.com/games/...` | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| G1 no look-ahead | **PASS** | refit weekly on strictly prior weeks; training buffer updated after each prediction | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| G2 vs break-even | **FAIL** | 42.86% straight-up (45/105) vs 52.38% break-even — and the shortfall is itself significant (two-sided p = 0.0507), so this is not just "not proven", it is worse than break-even | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| G3 significance | **FAIL** | full-sample R² = 0.0177, p = 0.145 | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| G4 proper scoring | **FAIL** | Brier 0.2519 vs null 0.2494 → skill score **−0.0098** | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| G5 side balance | **FAIL** | picked the home side in 82/105 (78.1%) in a season where home teams win 48.91% | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| G6 correlation | n/a | not a parlay model | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| G7 sample size | **PASS (disclosed)** | at 57% true skill, 719 bets needed; this model has 105 | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |

**Verdict: REJECTED.**

### Candidate S-02 — Same model, intercept forced to zero

| Gate | Result | Value | Source |
|------|--------|-------|--------|
| G0–G1 | **PASS** | same as S-01 | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| G2 vs break-even | **PASS (marginal)** | 56.19% straight-up vs 52.38% break-even | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| G3 significance | **FAIL** | 59/105 = 56.19% vs 52.38% expected → z = 0.78, two-sided **p = 0.434** | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| G4 proper scoring | **FAIL** | Brier 0.2490 vs null 0.2494 → skill score **+0.0017** (i.e. zero) | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| G5 side balance | **PASS** | 50 home / 55 away | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| G7 sample size | **PASS (disclosed)** | 105 of 719 needed | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |

**Verdict: REJECTED — clears the hit-rate gate and fails everything else.**

### Candidate S-03 — Naive "better season-to-date point differential" rule

| Gate | Result | Value | Source |
|------|--------|-------|--------|
| G1 | **PASS** | uses only completed games | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| G2 | **PASS** | **60.33%** straight-up (n=121) vs 52.38% | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| G3 | **FAIL** | 73/121 = 60.33% vs 52.38%; z = 1.75, two-sided **p = 0.080** — and even that understates the problem, because the rule was selected on this same season, so the result is fitted, not held out | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| G4 | **not computed** | the rule emits no probability, so it cannot be scored properly | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| G7 | **PASS (disclosed)** | n=121 | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |

**Verdict: INCONCLUSIVE — a benchmark to beat, not a strategy.** Its value is as the bar any future
model must clear on identical windows.

### Candidate S-04 — Parlay correlation sensitivity grid (pricing tool, not a strategy)

| Gate | Result | Source |
|------|--------|--------|
| G0 | **PASS** — the grid is pure arithmetic on stated inputs | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| G6 | **PASS by construction** — it publishes ρ = 0.00 / 0.15 / 0.30 / 0.50 rather than asserting one | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |

**Verdict: PUBLISHED AS A TOOL.** Not eligible for the leaderboard because it makes no pick.

## The sample-size arithmetic behind G3/G7

At American **−110** the break-even win rate is **11/21 = 0.5238095**. Two-sided test, α = 0.05,
80% power, versus that break-even:

| True win rate | Bets required | Seasons at 200 bets | p if observed over 200 bets | p if observed over 500 bets | Source |
|---|---|---|---|---|---|
| 55% | 2,243 | 11.21 | 0.208 | 0.130 | [derived](https://www.nfl.com/schedules/2026/by-week/week-1) |
| 56% | 1,173 | 5.87 | 0.137 | 0.057 | [derived](https://www.nfl.com/schedules/2026/by-week/week-1) |
| 57% | 719 | 3.60 | 0.108 | 0.021 | [derived](https://www.nfl.com/schedules/2026/by-week/week-1) |
| 58% | 485 | 2.43 | 0.064 | 0.007 | [derived](https://www.nfl.com/schedules/2026/by-week/week-1) |
| 60% | 263 | 1.32 | 0.018 | 0.0004 | [derived](https://www.nfl.com/schedules/2026/by-week/week-1) |
| 62% | 164 | 0.82 | 0.004 | 0.00001 | [derived](https://www.nfl.com/schedules/2026/by-week/week-1) |

Read the 200-bet column: **a 55% bettor over a full season of 200 bets has p = 0.208.** A season
leaderboard run on raw win rate will crown a lucky bettor. See Suggestions S6.

## The pathology that produced gate G5

The free-intercept model picked the home side 78.1% of the time in a season where home teams win
48.91%. It therefore scored **below** the base rate it was implicitly betting, while the identical
model with the intercept pinned at zero scored 56.19% on the same games. Gate G5 now exists so this
failure mode cannot be published again in good faith.

Source for every number above: replaying
`https://www.nfl.com/schedules/2026/by-week/week-N` (N = 1..9) plus
`https://www.nfl.com/schedules/2026/reg10`, via `tools/analytics.py`.
