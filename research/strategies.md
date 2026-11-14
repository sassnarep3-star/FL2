# Strategy Register

Requirement 4 asks for proprietary lines, singles, parlays, player-prop combos, correlation values,
and "remove luck, build selectively skill-based strategies". Here is exactly what exists, what
failed, and what the numbers say.

## Status board

| ID | Strategy | Type | Gates | Verdict |
|----|----------|------|-------|---------|
| S-01 | Walk-forward point-differential model (free intercept) | Single / side | G0,G1,G7 pass; G2,G3,G4,G5 fail | **REJECTED** |
| S-02 | Same model, intercept pinned at zero | Single / side | G0,G1,G2,G5,G7 pass; G3,G4 fail | **REJECTED** |
| S-03 | Naive "better point differential" rule | Single / side | G0,G1,G2,G7 pass; G3 fail; G4 not computable | **BENCHMARK — not a strategy** |
| S-04 | Gaussian one-factor copula parlay grid | Parlay pricing tool | G0,G6 pass | **PUBLISHED AS A TOOL** |
| S-05 | Player-prop pair correlation study | Prop combos | G0 pass; G3 fails (all CIs cross zero) | **ILLUSTRATIVE ONLY** |
| S-06 | Defensive-deficiency correlation study | Single / total inputs | G0 pass; 3 of 4 pairs significant | **PUBLISHED AS INPUTS** |

**Leaderboard: empty.** Zero strategies pass G3. Publishing a leaderboard with zero qualifying
entries would be theatre; see Suggestions S6 for how the leaderboard should be built once S5 is
resolved.

---

## S-01 / S-02 — Walk-forward power model

`home_margin = a + b × (home point-differential per game − away point-differential per game)`,
refit at the start of every week using only games from strictly earlier weeks.

| Metric | Free intercept (S-01) | Intercept = 0 (S-02) | Source |
|---|---|---|---|
| Graded games | 105 | 105 | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| Straight-up | **42.86%** | **56.19%** | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| Picks: home / away | 82 / 23 | 50 / 55 | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| Accuracy on home picks | 43.9% | 54.0% | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| Accuracy on away picks | 39.1% | 58.2% | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| RMSE (points) | 12.763 | 12.666 | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| MAE (points) | 10.063 | 9.980 | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| Brier | 0.2519 | 0.2490 | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| Brier null | 0.2494 | 0.2494 | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| **Brier skill score** | **−0.0098** | **+0.0017** | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |
| Final fitted slope | 0.1361 | 0.1361 | [box scores](https://www.nfl.com/schedules/2026/by-week/week-1) |

**Read this as:** the free-intercept version inherits a home-team bias that does not exist in 2026
data (home teams: 48.91% wins, mean margin −0.022 pts), so it bets the home side 78% of the time and
loses. Pin the intercept and it behaves sensibly — but its probability accuracy is then
indistinguishable from a coin-flip base rate. **Do not bet either.**

---

## S-04 — Parlay pricing: the correlation grid

Gaussian one-factor copula: each leg `i` is `√ρ·Z + √(1−ρ)·εᵢ`. The joint probability is
`∫ φ(u) · Φ((z_p − √ρ·u)/√(1−ρ))ⁿ du`, evaluated by 2,001-point Gauss–Hermite quadrature.

`correlation_multiplier` = correlated joint probability ÷ independent joint probability. At p = 0.5238
per leg:

| Legs | ρ = 0.00 | ρ = 0.15 | ρ = 0.30 | ρ = 0.50 | Source |
|---|---|---|---|---|---|
| 2 | 1.000× (0.2744) | 1.087× (0.2983) | 1.176× (0.3227) | 1.303× (0.3575) | [derived arithmetic](https://www.nfl.com/schedules/2026/by-week/week-1) |
| 3 | 1.000× (0.1437) | 1.260× (0.1810) | 1.523× (0.2189) | 1.894× (0.2722) | [derived arithmetic](https://www.nfl.com/schedules/2026/by-week/week-1) |
| 4 | see `data/derived/analytics.json` | | | | [derived arithmetic](https://www.nfl.com/schedules/2026/by-week/week-1) |
| 5 | see `data/derived/analytics.json` | | | | [derived arithmetic](https://www.nfl.com/schedules/2026/by-week/week-1) |

**Why a grid and not a number:** ρ has not been estimated from data (see Open Questions Q10).
At 3 legs, moving ρ from 0.00 to 0.30 changes the fair price by **52%**. Quoting one number would be
fake precision, so the whole grid is published and the reader supplies their own ρ.

---

## S-05 — Player-prop pair correlations (illustrative, n = 8–9)

| Pair | n | Pearson r | 95% CI | p | Source |
|---|---|---|---|---|---|
| Maye pass yds vs Henry rec yds | 9 | **+0.5799** | [−0.088, +0.884] | 0.102  [Maye](https://www.nfl.com/players/drake-maye/stats/logs/2026/) · [Henry](https://www.nfl.com/players/hunter-henry/stats/logs/2026/) |
| Burrow pass yds vs Chase rec yds | 8 | +0.1371 | [−0.635, +0.774] | 0.746  [Burrow](https://www.nfl.com/players/joe-burrow/stats/logs/2026/) · [Chase](https://www.nfl.com/players/ja-marr-chase/stats/logs/2026/) |
| Maye pass yds vs Stevenson rush yds | 9 | −0.0748 | [−0.702, +0.598] | 0.848  [Maye](https://www.nfl.com/players/drake-maye/stats/logs/2026/) · [Stevenson](https://www.nfl.com/players/rhamondre-stevenson/stats/logs/2026/) |
| Maye pass yds vs Stevenson rec yds | 8 | +0.4138 | [−0.402, +0.842] | 0.308  [Maye](https://www.nfl.com/players/drake-maye/stats/logs/2026/) · [Stevenson](https://www.nfl.com/players/rhamondre-stevenson/stats/logs/2026/) |

**Every confidence interval crosses zero.** The largest point estimate (+0.58) is the one that would
tempt a parlay, and it is also the one whose CI spans from "no relationship" to "near-perfect". This
is what a small sample looks like and it is published as the warning it is. Sample: 2 clubs,
5 players. Source per player: `https://www.nfl.com/players/<slug>/stats/logs/2026/`.

---

## S-06 — Defensive-deficiency correlations (n = 32, all teams, official)

| Pair | n | Pearson r | 95% CI | p | Source |
|---|---|---|---|---|---|
| Pass yards allowed vs points allowed/game | 32 | **+0.5070** | [0.191, 0.727] | 0.0031  [defense passing](https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all) · [standings](https://www.nfl.com/standings/) |
| Rush yards allowed vs points allowed/game | 32 | **+0.6122** | [0.333, 0.784] | 0.0002  [defense rushing](https://www.nfl.com/stats/team-stats/defense/rushing/2026/reg/all) · [standings](https://www.nfl.com/standings/) |
| Defensive yards/attempt allowed vs points allowed/game | 32 | **+0.5820** | [0.291, 0.767] | 0.0005  [defense passing](https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all) · [standings](https://www.nfl.com/standings/) |
| Points allowed/game vs win percentage | 32 | **−0.6640** | [−0.822, −0.415] | 0.00003  [standings](https://www.nfl.com/standings/) |

These four are the only correlations in the project that clear significance, and they are
**descriptive, not predictive** — they say what has already happened across 32 teams this season.
Note that *volume* allowed (rush yards, r = 0.61) tracks points allowed better than *efficiency*
allowed (yards per attempt, r = 0.58), and neither exceeds ~37% of the variance. Sources:
`https://www.nfl.com/stats/team-stats/defense/rushing/2026/reg/all`,
`https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all`,
`https://www.nfl.com/standings/`.

---

## Bankroll sizing (published, not a strategy)

Kelly table for prices −110 … +500, full and quarter Kelly. Full Kelly `f* = (p·b − q)/b`; negative
means **no bet**. At −110, break-even is p = 0.5238 and a model that is merely 55% confident earns
**0.0138 units at quarter Kelly** — a useful reminder of how thin real edges are. Source: arithmetic
on the break-even identity, `data/derived/analytics.json → kelly`.
