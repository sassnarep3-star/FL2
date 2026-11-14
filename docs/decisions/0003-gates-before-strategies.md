# 3. Gate battery first; strategies earn their way onto the board

Date: 2026-11-14 · Status: **accepted** · Session: `arena-be3108f3`

## Context
The brief asks for a leaderboard competition with rewards for top strategies, "removing luck" so that selection is
skill-based, across singles, parlays and prop combos. A leaderboard over small samples selects for variance: the
strategy with the luckiest 60 bets wins, and the reward then buys more of that noise.

## Decision
Sixteen gates (G-01…G-16) are implemented in code before any strategy is ranked, and promotion requires all
applicable gates to pass:

- sample floor and a Wilson lower bound above the de-vigged break-even (G-01, G-02);
- closing-line value as the primary skill statistic (G-03);
- deflated Sharpe with the variant count taken from a pre-commitment registry, plus MinTRL (G-04);
- parameter cap, walk-forward sign agreement, vig/slippage stress, recent-decay check (G-05…G-08);
- block-bootstrap and sign-flip tests so "could be luck" is answered numerically (G-09);
- capacity, book-rule legality of combo structures, feature staleness, forecast-quality vs the frozen baseline,
  revision robustness, and one-bet-per-correlation-cluster (G-10…G-16).

Rewards are **capital allocation** (0 → 0.5u → 1.0u → 2.0u by tier), forfeited on post-hoc gate violations or an
unregistered variant. Standings are published empty until graded bets exist.

## Consequences
+ Skill is defined as a computation, not a claim; a strategy cannot argue its way past a gate.
+ Arithmetic the site can defend today: at −110, a 55% hit rate needs ~961 bets for the lower 90% bound to clear
  break-even, 53% needs ~17,467, and 8 bets can never clear a 5% sign-flip test.
− Almost nothing is promotable now, which is the honest state of a project with no market data.
