#!/usr/bin/env python3
"""
tools/calc.py — every number the site presents as "derived" is computed here.

Nothing in this file depends on external data. It is pure arithmetic on
(i) published odds conventions and (ii) parameters that are stated explicitly
in the output so they can be audited or changed.

Run: python3 tools/calc.py
Output: JSON to stdout, also written to data/derived-metrics.json
"""
import json
import math
from statistics import NormalDist

ND = NormalDist()


# ---------------------------------------------------------------- odds basics
def implied_prob_american(odds: int) -> float:
    """Standard American-odds -> implied probability conversion."""
    if odds < 0:
        return (-odds) / ((-odds) + 100.0)
    return 100.0 / (odds + 100.0)


def decimal_from_american(odds: int) -> float:
    if odds < 0:
        return 1.0 + (100.0 / -odds)
    return 1.0 + (odds / 100.0)


def two_way_hold(o1: int, o2: int) -> float:
    p = implied_prob_american(o1) + implied_prob_american(o2)
    return p - 1.0


def no_vig(o1: int, o2: int):
    p1, p2 = implied_prob_american(o1), implied_prob_american(o2)
    s = p1 + p2
    return p1 / s, p2 / s


def breakeven_prob(odds: int) -> float:
    """Win rate required for zero EV at a given price (single bet, no push)."""
    return implied_prob_american(odds)


# ------------------------------------------------------- parlay / correlation
def parlay_price_american(legs):
    d = 1.0
    for o in legs:
        d *= decimal_from_american(o)
    return d


def parlay_hold(legs):
    """Total hold of an n-leg parlay, assuming each leg is an independent
    two-way market priced at the same hold h."""
    h1 = 1.0
    for o in legs:
        h1 *= decimal_from_american(o)
    # fair decimal odds if each leg were priced with zero margin
    fair = 1.0
    for o in legs:
        fair *= (1.0 / implied_prob_american(o)) * 0 + 1.0  # placeholder, replaced below
    return None


def _phi(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def bivariate_joint(p1: float, p2: float, rho: float) -> float:
    """Joint probability under a bivariate-normal (probit) copula.

    Each binary leg becomes a threshold on a standard normal latent variable;
    the two latents are correlated with coefficient rho.

        P(Z1<=z1, Z2<=z2) = INT_{-inf}^{z2} phi(x) * Phi((z1 - rho*x)/sqrt(1-rho^2)) dx

    Evaluated by midpoint quadrature on [-8, z2]. At rho = 0 this returns
    p1 * p2, which is used as a unit test below.
    """
    z1 = ND.inv_cdf(p1)
    z2 = ND.inv_cdf(p2)
    n = 20000
    lo, hi = -8.0, z2
    step = (hi - lo) / n
    total = 0.0
    s = math.sqrt(max(1e-12, 1.0 - rho ** 2))
    for i in range(n):
        x = lo + (i + 0.5) * step
        total += _phi(x) * ND.cdf((z1 - rho * x) / s) * step
    # add the mass below the lower integration bound (negligible but exact-ish)
    total += ND.cdf(-8.0) * ND.cdf(z1 / math.sqrt(max(1e-12, 1.0 - rho ** 2)))
    return total


def main():
    out = {}

    # ---- 1. price -> break-even table
    prices = [-200, -150, -130, -120, -115, -110, -105, 100, 110, 120, 150, 200]
    out["breakeven_table"] = [
        {
            "american": p,
            "decimal": round(decimal_from_american(p), 4),
            "implied_prob_pct": round(100 * implied_prob_american(p), 2),
            "breakeven_win_pct": round(100 * breakeven_prob(p), 2),
        }
        for p in prices
    ]

    # ---- 2. two-way hold
    out["hold_-110_-110_pct"] = round(100 * two_way_hold(-110, -110), 2)
    out["hold_-105_-105_pct"] = round(100 * two_way_hold(-105, -105), 2)
    nv = no_vig(-110, -110)
    out["no_vig_fair_prob_-110_-110"] = [round(100 * nv[0], 2), round(100 * nv[1], 2)]

    # ---- 3. parlay hold compounding
    # A 2-leg parlay at -110/-110 pays +264.46 (decimal 3.6446).
    # Fair probability = 0.5238^2 ... no: fair price uses the NO-VIG leg prob.
    rows = []
    for n in range(1, 7):
        dec_offered = decimal_from_american(-110) ** n
        fair_dec = 2.0 ** n                     # each no-vig leg is 50% -> decimal 2.0
        hold = 1.0 - (dec_offered / fair_dec)   # share of the fair payout kept by the book
        rows.append(
            {
                "legs": n,
                "offered_decimal": round(dec_offered, 4),
                "offered_american": round((dec_offered - 1) * 100),
                "fair_decimal_no_vig": fair_dec,
                "effective_hold_pct": round(100 * hold, 2),
                "breakeven_win_pct": round(100 * (0.5 ** n), 4),
                "ev_per_1_unit_pct": round(100 * ((0.5 ** n) * dec_offered - 1), 2),
            }
        )
    out["parlay_hold_compounding"] = rows

    # ---- 4. correlated parlay: two legs, each priced as a no-vig 50/50,
    #          varying latent correlation rho. Shows how much dependence moves
    #          the fair joint probability away from the independent 25%.
    # unit test of the copula: rho = 0 must reproduce p1 * p2
    assert abs(bivariate_joint(0.5, 0.5, 0.0) - 0.25) < 1e-6, "copula unit test failed"

    corr = []
    for rho in [-0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6, 0.8]:
        j = bivariate_joint(0.5, 0.5, rho)
        # fair decimal odds of the parlay given that joint probability
        fair_dec = 1.0 / j
        offered = decimal_from_american(-110) ** 2
        edge = (j * offered) - 1.0
        corr.append(
            {
                "rho": rho,
                "fair_joint_pct": round(100 * j, 2),
                "independent_reference_pct": 25.0,
                "fair_decimal": round(fair_dec, 4),
                "offered_decimal_-110x2": round(offered, 4),
                "ev_per_1_unit_staked_pct": round(100 * edge, 2),
            }
        )
    out["correlated_parlay_table"] = corr

    # ---- 5. sample size: how many bets to distinguish a true rate from breakeven
    # one-sided alpha 0.05, power 0.80 (z = 1.6449 + 0.8416)
    z_a, z_b = ND.inv_cdf(0.95), ND.inv_cdf(0.80)

    def n_required(p_true, p0, alpha=0.05, power=0.80):
        za = ND.inv_cdf(1 - alpha)
        zb = ND.inv_cdf(power)
        return ((za * math.sqrt(p0 * (1 - p0)) + zb * math.sqrt(p_true * (1 - p_true)))
                / (p_true - p0)) ** 2

    samples = []
    for p_true in [0.525, 0.53, 0.535, 0.55, 0.575, 0.60]:
        samples.append(
            {
                "true_win_pct": round(100 * p_true, 1),
                "edge_vs_-110_breakeven_pp": round(100 * (p_true - 0.52381), 2),
                "bets_required_80pct_power": math.ceil(n_required(p_true, 0.52381)),
            }
        )
    out["sample_size_required"] = samples

    # ---- 6. minimum detectable edge at a given sample size (80% power)
    mde = []
    for n in [100, 250, 500, 1000, 2500, 5000]:
        # solve for p_true that gives required n
        lo, hi = 0.52381, 0.95
        for _ in range(200):
            mid = (lo + hi) / 2
            if n_required(mid, 0.52381) > n:
                lo = mid
            else:
                hi = mid
        mde.append(
            {
                "bets": n,
                "min_detectable_true_win_pct": round(100 * hi, 2),
                "min_detectable_edge_pp": round(100 * (hi - 0.52381), 2),
            }
        )
    out["minimum_detectable_edge"] = mde

    # ---- 7. probability of a false leaderboard crown
    # 500 strategies, all with zero true edge, each with 200 bets at -110.
    # Probability at least one looks >= 55% by luck alone (binomial upper tail).
    def binom_sf(k, n, p):
        # P(X >= k)
        tot = 0.0
        for i in range(k, n + 1):
            tot += math.comb(n, i) * p ** i * (1 - p) ** (n - i)
        return tot

    p_single = binom_sf(int(0.55 * 200), 200, 0.52381)
    out["luck_false_positive"] = {
        "scenario": "200 bets per strategy at -110, zero true edge, 500 strategies tested",
        "prob_single_strategy_at_or_above_55pct_pct": round(100 * p_single, 2),
        "prob_at_least_one_of_500_pct": round(100 * (1 - (1 - p_single) ** 500), 2),
        "prob_any_single_strategy_at_or_above_breakeven_pct": round(
            100 * binom_sf(int(math.ceil(0.52381 * 200)), 200, 0.52381), 2),
    }

    # ---- 8. Kelly staking
    kelly = []
    for p, odds in [(0.53, -110), (0.55, -110), (0.57, -110), (0.55, 100), (0.60, -150)]:
        b = decimal_from_american(odds) - 1.0
        f = (p * b - (1 - p)) / b
        kelly.append(
            {
                "true_win_pct": round(100 * p, 1),
                "american": odds,
                "full_kelly_pct_of_bankroll": round(100 * f, 2),
                "half_kelly_pct": round(100 * f / 2, 2),
                "quarter_kelly_pct": round(100 * f / 4, 2),
            }
        )
    out["kelly_table"] = kelly

    # ---- 9. injury status weighting (PROPOSED, not measured)
    out["injury_status_weights_proposed"] = {
        "note": "Proposed starting weights. Must be calibrated against realised "
                "snap-count drops; not an official NFL construct.",
        "Out": 1.0,
        "Doubtful": 0.75,
        "Questionable": 0.40,
        "no designation / practice-only": 0.15,
    }

    with open("data/derived-metrics.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
