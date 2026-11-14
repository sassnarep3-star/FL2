# 4. Correlation register: mechanism documented, values left unmeasured

Date: 2026-11-14 · Status: **accepted** · Session: `arena-be3108f3`

## Context
Parlays and same-game prop combos are where availability data is most valuable and where books most easily misprice,
because correlated legs are priced by multiplying marginals and applying a multiplier. The brief asks to "determine
correlation values". No data source in this repo can estimate a single ρ.

## Decision
Maintain a register of leg-pairs (CR-01…CR-12) recording the *structural* claim — mechanism, expected sign,
whether the legs share a driver, and the measurement plan (simulation window, shrinkage toward 0, per-season
stability) — with the measured value left blank. Pricing uses a Gaussian copula over one shared latent game state
(`engine/parlay.py`), and a book's multiplier is inverted into an *implied* ρ to be compared with ours. Refusal
rule: no same-game combo whose legs share a driver may be quoted while its ρ is unmeasured.

## Consequences
+ Correlation becomes a measurable object with a plan, instead of a vibe that quietly enters a parlay model.
+ The copula handles negative ρ (via the bivariate conditional integral) where the one-factor form cannot, and
  approaches the Fréchet bounds at the tested O(√(1−ρ)) rate rather than the assumed faster one.
− Combo quoting is blocked until market data exists (Q-12, FL-014), so the SGP side of the brief is specification,
  not results.
