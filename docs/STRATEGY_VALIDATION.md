# Strategy validation protocol

**Purpose.** Make it expensive for a bad strategy to look good. Every strategy in
this project must clear eight gates on out-of-sample data before it may be
labelled anything other than `rejected`. As of 2026-11-14 **no strategy has
cleared all eight** — that is the honest headline, and it is the most useful
result in the project.

---

## 1. The protocol is fixed before results are seen

Protocol-shopping (trying variants until something works, then reporting the
protocol that produced it) is the main reason betting research does not
replicate. So the following are constants at the top of `engine/run_backtest.py`
and are recorded in `data/backtest_summary.json → protocol`:

| Constant | Value | Meaning |
|---|---|---|
| `TRAIN_START` | 2006 | first season with usable closing lines |
| `CALIB_END` | 2010 | seasons used **only** to calibrate Elo → points |
| `EVAL_START` | 2011 | first out-of-sample season |
| `MIN_SAMPLE` | 150 bets | sample required before judging |
| `BREAKEVEN_HIT` | 0.5238 | break-even win rate at −110 |
| `FDR_Q` | 0.10 | Benjamini–Hochberg false-discovery rate |
| `ELO_POINTS_PER_RATING` | 25 | 25 Elo points ≈ 1 point of expected margin |
| `MIN_EDGE_PTS` | 2.0 | minimum model-vs-line disagreement to place a bet |

Changing any of these is a *new hypothesis*, and the number of hypotheses tried
must be reported alongside it.

---

## 2. The eight gates

| Gate | Requirement | Why it exists |
|---|---|---|
| **G1 sample** | ≥ 150 settled bets | Below this, a 55% hit rate is indistinguishable from 50%. |
| **G2 hit rate** | Bootstrap 95% **lower** bound on hit rate > 52.38% | Uses the lower bound, not the point estimate. |
| **G3 profit** | Block-bootstrap 95% CI of mean return/bet excludes 0 | Blocks of 16 games, because bets are serially dependent. |
| **G4 model quality** | Model Brier score beats the de-vigged closing line | A strategy whose model is worse than the market is fitting noise. |
| **G5 stability** | Profitable in ≥ 60% of evaluated seasons | Kills one-lucky-season results. |
| **G6 luck** | Luck fraction < 0.50 | See §4. |
| **G7 multiplicity** | Survives Benjamini–Hochberg at q = 0.10 across all tested strategies | With 11 hypotheses, one p < 0.05 is expected by chance. |
| **G8 no leakage** | Features provably pre-kickoff | See §3. |

A strategy's `status` derives mechanically:
`validated` = 8/8 · `promising` = 5–7 / 8 · `rejected` = ≤ 4 / 8 ·
`untestable` = 0 bets, with a documented data gap.

---

## 3. Leakage controls (Gate 8)

Every feature is built in one chronological pass over the games table, and for
game *i* may only read games that finished before *i* kicked off:

| Feature | Construction | Leakage risk | Control |
|---|---|---|---|
| `elo_margin` | Elo rating state *before* the game | Rating updated with the game's own result | `elo.expected_home()` is called, stored, **then** `elo.update()` |
| `home_pf6`, `home_pa6` | mean of last 6 games | including the current game | `hist[team]` is appended only after the record is written |
| `last_margin_home` | previous game's margin | using this week's margin | read from `last[team]`, written after |
| `home_rest` | supplied by nflverse, computed from schedule | none | schedule-only |
| `wind`, `roof` | game-day weather | none | forecast/pre-game value |
| `mkt_p_home` | de-vigged **closing** moneyline | closing lines are *later* than some bet timings | documented risk: this is a closing-line backtest, not a beat-the-open backtest. It makes results **conservative** for a bettor who bets early and **optimistic** for one who can only bet after close. |
| `elo_margin_cal` coefficients | fit on 2006–2010 only | fit on evaluation data | explicit `CALIB_END` split |

Two further controls:
* `self_check()` **asserts** the dataset's sign conventions before anything runs
  (see `docs/SOURCES.md` §3) and aborts the build if they are violated.
* Pushes are removed from settlement (`np.nan`), never silently counted as wins.

---

## 4. Removing luck

### 4.1 Variance decomposition (`stats_core.luck_share`)

For a record of n bets with mean return μ and standard deviation σ:

```
SE(μ)      = σ/√n
t          = μ / SE(μ)
luck_share = 1 − (max(SE(μ)² − 1/n, 0) / SE(μ)²)
```

The `1/n` term is the variance of the mean return under a *fair-coin* null
(each bet ±1 unit with zero edge). If the observed variance of the mean is no
bigger than the coin-flip variance, the record is fully explainable by luck and
`luck_share = 1`. `luck_share < 0.50` means more than half of the spread in
outcomes is *not* coin-flip noise.

This is a screen, not a proof: it identifies records that are **definitely**
luck. Clearing it does not prove skill.

### 4.2 Effective sample size (`stats_core.effective_sample_size`)

Correlated bets (parlays, same-game combos, repeated bets on one team) do not
give n independent observations. Using the lag-1 autocorrelation ρ:

```
n_eff = n (1 − ρ) / (1 + ρ)
```

Every strategy that bets the same team repeatedly in a season has n_eff well
below n. Reported so nobody reads 900 bets as 900 independent trials.

### 4.3 Block bootstrap (`stats_core.block_bootstrap_ci`)

Season-long bet sequences are serially dependent, so the CI uses blocks of 16
bets resampled with replacement rather than iid resampling. iid CIs on this data
are roughly 15–25% too narrow.

---

## 5. Correlation values (parlays, SGPs, prop combos)

Binary legs use the **phi coefficient**, bootstrapped (2,000 resamples):

```
phi = (n11·n00 − n10·n01) / √((n11+n10)(n01+n00)(n11+n01)(n10+n00))
```

Results from settled games, 2011–2026 (`data/parlay_analysis.json`):

| Leg pair | phi | 95% CI | n | Significant? |
|---|---|---|---|---|
| home win + home cover | **+0.676** | [+0.653, +0.698] | 3,900 | **yes** |
| home cover + over | +0.008 | [−0.023, +0.040] | 3,913 | no |
| big home fav + over | +0.028 | [−0.003, +0.059] | 3,913 | no |
| big posted total + over | +0.010 | [−0.023, +0.041] | 3,913 | no |
| divisional game + home cover | −0.005 | [−0.035, +0.027] | 3,913 | no |

**Interpretation, stated plainly:** the only correlation that survives a
confidence interval in this data is the mechanical one between *winning* and
*covering*. The widely repeated claim that spread and total legs are correlated
is **not supported here** — the observed joint rate (24.20%) is within 0.2 points
of the independence prediction (24.00%). For a two-leg spread+total SGP that
means the "correlation" pricing adjustment many books apply is, in this sample,
close to noise.

For continuous pairs (Pearson): `spread_line ↔ home margin`, `total_line ↔ total
points`, `wind ↔ total points` — see `data/parlay_analysis.json`.

---

## 6. Vig compounding — why leg count matters more than pick quality

At a standard −110 two-way price, each leg carries 4.55% margin. Because the
margins multiply, the fair price and offered price diverge geometrically
(`data/parlay_analysis.json → vig_cost_by_leg_count`):

| Legs | Fair multiple | Book multiple | Edge surrendered |
|---|---|---|---|
| 1 | 2.000 | 1.909 | **4.55%** |
| 2 | 4.000 | 3.645 | **8.88%** |
| 3 | 8.000 | 6.958 | **13.03%** |
| 4 | 16.000 | 13.283 | **16.98%** |
| 6 | 64.000 | 48.413 | **24.36%** |
| 10 | 1024.000 | 643.082 | **37.20%** |

To break even on a 3-leg ticket at −110 you need each leg to win at **52.38%**
*simultaneously*, i.e. a genuine per-leg edge greater than the same 52.38%
threshold a single bet needs — but applied three times, with three chances to be
wrong. This is the arithmetic case against parlays as a skill vehicle, and it is
why the leaderboard scores singles first.

---

## 7. What would be required to call something `validated`

All of the following, together:

1. 8/8 gates on data the model has never seen.
2. A pre-registered protocol (this file) that was not modified after seeing results.
3. The live record continuing to meet the gates over a **forward** sample of at
   least 150 bets — backtests do not survive alone.
4. An explanation of *why* the edge should exist, consistent with the measured
   correlations in §5.
5. The market price taken is recorded at bet time with a source, so the claim is
   auditable (`verified_market: true`).

Until then every strategy stays `experimental` and appears as such on the site.

---

## 8. Results as of 2026-11-14

Out-of-sample 2011–2026, closing lines, no pushes, block-bootstrapped.

| Strategy | Market | n | Hit rate | ROI/bet | Gates | Status |
|---|---|---|---|---|---|---|
| S1 calibrated Elo vs. spread | SPREAD | 2,086 | 51.7% | +0.47% | 3/8 | rejected |
| S2 fade 17+ point winner | SPREAD | 825 | 50.5% | −1.82% | 2/8 | rejected |
| S3 rest differential (3+ days) | SPREAD | 874 | 50.7% | −1.42% | 2/8 | rejected |
| S4 pace vs. posted total | TOTAL | 722 | 47.6% | −7.40% | 2/8 | rejected |
| S5 divisional home underdog | SPREAD | 551 | 50.1% | −2.79% | 2/8 | rejected |
| S6 moneyline underdog value | ML | 841 | 36.7% | −4.20% | 2/8 | rejected |
| S7 high total + calm weather | TOTAL | 374 | 50.0% | −2.79% | 2/8 | rejected |
| S8 team off a bye | SPREAD | 413 | 49.6% | −3.58% | 2/8 | rejected |
| S9 short-week unders | TOTAL | 246 | 50.0% | −2.68% | 2/8 | rejected |
| S10 high-wind unders | TOTAL | 156 | 55.1% | +7.39% | 2/8 | rejected |
| S11 fade large line moves | SPREAD | 0 | — | — | — | **untestable** |

Baseline model quality on the same games (n = 4,041): Elo Brier **0.2277** vs
market **0.2106**, i.e. **Brier skill −8.1%** against the closing line. A model
that is 8% worse than the market on probability scoring cannot be expected to
find value against it, and S1's +0.47% ROI with a CI spanning zero is exactly
what that predicts.

**S10 is the instructive case:** 55.1% hit rate over 156 bets looks like an edge
and is why people believe in weather angles. It fails G1 (sample), G3 (CI spans
zero), G5 (stability) and G7 (multiplicity). It is a coin landing heads 86 times
instead of 78.

---

## 9. Reproducing all of this

```bash
python3 engine/fetch_data.py       # downloads + hashes datasets (needs network)
python3 engine/run_backtest.py     # validates conventions, writes backtest_summary.json
python3 engine/run_parlays.py      # writes parlay_analysis.json
python3 engine/build_week10.py     # writes week10_lineups.json, season_2026.json
python3 engine/build_market.py     # writes market_lines.json
python3 engine/build_site_data.py  # writes site_data.json (what the site renders)
```

Determinism: every bootstrap uses a fixed seed (`20261114` in `stats_core`, `7` in
`run_backtest`), so re-running reproduces the reported intervals exactly.
