# Pre-registration — SB-1 "Shadow Baseline" (frozen rule text)

**Registered:** 2026-11-16 UTC by session-65556dd2
**Registration commit:** the git commit that adds this file to `main`-bound history
(`arena/65556dd2-fl2`); the forecast ledger records its hash. Rule text below is
frozen at that commit. Any change = a new registration (new id, new commit).
**Evaluation window (prospective):** 2026 NFL regular season Weeks 11–18, graded at
**closing** prices. The window had not opened when this was registered (Week 11
kickoff 2026-11-19 20:15 ET).
**Id:** SB-1.0.0 · **Division:** singles only · **Stakes:** flat 1 unit, recorded
separately from signal quality.

## 0. Why a shadow baseline

Brief: "Start with a singles-only shadow baseline. Pre-register a simple
team-strength model, freeze versions and record forecasts before kickoff." SB-1 is
that model. It is intentionally simple: it exists to be beaten by later strategies,
and it is the control that separates signal from staking.

## 1. Data inputs (frozen)

* FL2 verified results feed (`data/results_feed.{csv,json}`), 2026 REG Weeks 1–10,
  rows with `status=final` only (148 rows at registration; the feed grows as games
  finish — the *fit window* is frozen as Weeks 1–10 regardless).
* **No market price is ever a model input** (price-data-policy.md rule 3.1).
* **No injury, depth or personnel input.** SB-1 is team-strength only. Injury
  effects are tested later as pre-registered **ablations** (identical model with and
  without availability features, chronological holdouts), never as fixed penalties.

## 2. Model (frozen)

1. **Margin model.** Least squares on home margin
   `y_i = β0 + r_home − r_away + ε_i`, constraint `Σ_t r_t = 0` over the 32 clubs.
   `β0` is the measured home-field advantage (no prior). Exact solution of the
   normal equations (33 parameters).
2. **Total model.** Let `T̄` = mean total points over the fit window and `m = T̄/2`.
   For team t with n_t games: `o_t = (mean points scored by t − m) · n_t/(n_t+4)`
   and `d_t = (mean points allowed by t − m) · n_t/(n_t+4)` (shrinkage k=4,
   declared). `fair_total = T̄ + o_home + o_away + d_home + d_away`.
3. **Moneyline.** `p_home = Φ(fair_margin / σ)` where `fair_margin = β0 + r_home −
   r_away` and `σ` = residual standard deviation of the margin regression
   (in-sample, declared). Fair American price: `−100·p/(1−p)` when p>0.5, else
   `+100·(1−p)/p`.
4. **Publication order:** SIDE first, then TOTAL, then MONEYLINE (brief).
5. **Stored output:** every forecast is stored as a **probability plus its inputs**
   (ratings, β0, σ, window, code version), never as a pick alone.

## 3. Market residual (published beside, never fed in)

`difference = model_fair − market` in display convention (negative = favoured).
Market column = the price store row (opening capture for Week 11, closing when
captured). For moneyline the market column shows the **derived** implied
probability from the market spread via the same Normal model — labelled
"derived from market spread", because no provider quoted a moneyline at capture.
The quoted-ML fields in the store stay blank + flagged.

## 4. Pre-registered gates (singles; evaluated at window close or n floor)

| Gate | Rule | Number that clears it |
|---|---|---|
| G1 proper score | Brier skill vs closing-market benchmark on prospective forecasts | 90% lower bound > −0.02 (non-inferiority); "validated" requires lower bound > 0 |
| G2 calibration | \|mean p − outcome rate\| | ≤ 0.03 with n ≥ 200 |
| G3 sample floor | significance claims | n ≥ 2,243 graded singles (55% detection, α=.05, 80% power) |
| G4 no-look-ahead | every forecast committed before kickoff | 0 violations (ledger timestamps) |
| G5 side balance | share of picks on one side | within [0.35, 0.65] |
| G6 division | SB-1 plays singles only | parlays/SGP/props stay behind the joint-evidence gate |
| G7 price policy | every graded price in the store with provider + timestamp | 0 missing |
| G8 registration | registration commit precedes first forecast commit | 0 violations |

**Control baselines** run with every leaderboard evaluation (same window): random
picks (seed 20261116), favourites-only at closing prices, home-team-only. Raw win
rate and short-run ROI are never ranked on (brief: "Rank with proper scores and
uncertainty, not win rate").

## 5. Demotion gate (live → paper)

A live strategy returns to paper when any of: (a) trailing 200 graded forecasts
with Brier-skill 90% lower bound < 0 at two consecutive weekly checkpoints;
(b) flat-stake drawdown > 25 units; (c) any feed-integrity failure in its inputs.
Re-promotion requires a fresh 200-forecast run with lower bound > 0.

## 6. What would change our mind (two-sided)

* **Up:** prospective Brier skill > 0 with 90% lower bound > 0 over ≥ 500 graded
  forecasts, and the side-balance gate holds.
* **Down:** skill point estimate < 0 at the Week-14 checkpoint (n ≥ 200); or a
  G4/G7 violation; or σ drifts > 20% from the registered value (model break).

## 7. Explicit rejections (frozen)

* No strategy is ranked on season-long ROI (rejected in the brief).
* No depth order from jersey number, experience or salary (rejected in the brief).
* No fixed injury penalties — ablations only (brief).
* Backtest numbers never appear on the leaderboard (pre-registration rule); the
  2026 Weeks 1–10 fit window is a backtest corpus for *development*, and its numbers
  are labelled `backtest` wherever shown.
