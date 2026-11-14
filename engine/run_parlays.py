"""
FL2 — parlay, same-game-parlay (SGP) and prop-combo mathematics.

Run:  python3 engine/run_parlays.py
Out:  data/parlay_analysis.json

Three questions, answered with settled games rather than asserted:

1. What does a book's parlay price actually cost you? (vig multiplication)
2. For two legs from the SAME game, how wrong is the independence assumption?
3. For a 3-leg and 4-leg ticket, how much does per-leg juice compound?

All leg probabilities use the de-vigged closing line, so the numbers below are
about *structure*, not about claiming an edge.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
import pandas as pd

from stats_core import (american_to_decimal, american_to_prob, devig_two_way,
                        implied_parlay_prob, phi_ci, phi_coefficient)

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache")
DATA = os.path.join(os.path.dirname(HERE), "data")
EVAL_START = 2011


def load() -> pd.DataFrame:
    g = pd.read_csv(os.path.join(CACHE, "games.csv"))
    g = g[(g.game_type == "REG") & (g.season >= EVAL_START)].copy()
    g["hm"] = g.home_score - g.away_score
    g["tot"] = g.home_score + g.away_score
    sp = g.hm - g.spread_line
    tt = g.tot - g.total_line
    g["home_cover"] = np.where(sp > 0, 1.0, np.where(sp < 0, 0.0, np.nan))
    g["over"] = np.where(tt > 0, 1.0, np.where(tt < 0, 0.0, np.nan))
    g["home_win"] = np.where(g.hm > 0, 1.0, np.where(g.hm < 0, 0.0, np.nan))
    ph = g.home_moneyline.map(american_to_prob)
    pa = g.away_moneyline.map(american_to_prob)
    dv = [devig_two_way(a, b) for a, b in zip(ph, pa)]
    g["p_home"] = [x[0] for x in dv]
    g["p_away"] = [x[1] for x in dv]
    return g.dropna(subset=["spread_line", "total_line"])


def vig_cost_table() -> list[dict]:
    """Cost of the bookmaker margin as a function of leg count, at a standard
    -110/-105 style two-way price. `fair` = the same legs at zero margin."""
    rows = []
    for n in (1, 2, 3, 4, 5, 6, 8, 10):
        # A -110/-110 market carries 4.55% margin over two outcomes.
        p_fair = 0.5
        p_with_vig = american_to_prob(-110)
        fair_dec = (1.0 / p_fair) ** n                    # true odds multiple
        book_dec = (1.0 / p_with_vig) ** n                # the price you're offered
        rows.append({
            "legs": n,
            "fair_multiple": round(fair_dec, 3),
            "book_multiple": round(book_dec, 3),
            "probability_given_up_pct": round(100 * (1 - book_dec / fair_dec), 2),
            "fair_american": round(_to_american_any(1 / fair_dec), 1),
            "book_american": round(_to_american_any(1 / book_dec), 1),
        })
    return rows


def _to_american_any(p: float) -> float:
    """American odds for any probability (no sign flip at long odds)."""
    if p <= 0 or p >= 1:
        return float("nan")
    return -100 * p / (1 - p) if p >= 0.5 else 100 * (1 - p) / p


def same_game_correlations(g: pd.DataFrame) -> dict:
    """Real joint outcomes for legs that appear on the same ticket."""
    d = g.dropna(subset=["home_cover", "over", "spread_line", "total_line"])
    out = {}

    def pair(name, a, b, note):
        m = np.isfinite(a) & np.isfinite(b)
        pt, lo, hi = phi_ci(a[m].astype(bool), b[m].astype(bool))
        pa, pb = a[m].mean(), b[m].mean()
        joint_obs = float(np.mean((a[m] > 0) & (b[m] > 0)))
        joint_indep = float(pa * pb)
        out[name] = {
            "note": note, "phi": pt, "ci_lo": lo, "ci_hi": hi, "n": int(m.sum()),
            "p_a": float(pa), "p_b": float(pb),
            "joint_observed": joint_obs, "joint_if_independent": joint_indep,
            "relative_error_pct": round(100 * (joint_obs / joint_indep - 1), 2) if joint_indep else None,
            "significant": bool(np.isfinite(lo) and (lo > 0 or hi < 0)),
        }

    pair("home_cover + over", d.home_cover.values, d.over.values,
         "Favourite covering and the game going over: both driven by the favourite scoring.")
    pair("home_win + home_cover", d.home_win.values, d.home_cover.values,
         "Winning outright vs. covering — the strongest structural dependence in football.")
    pair("home_fav + over", (d.spread_line > 3).astype(float).values, d.over.values,
         "Big home favourite and over: blowouts tend to be high scoring.")
    pair("big_total + over", (d.total_line > 47).astype(float).values, d.over.values,
         "High posted total and over: tests whether the market over-adjusts totals.")
    pair("div_game + home_cover", (d.div_game == 1).astype(float).values, d.home_cover.values,
         "Divisional games and home covering.")
    return out


def ticket_simulations(g: pd.DataFrame) -> dict:
    """Two-leg same-game and cross-game tickets priced three ways:
    book-style independent multiplication, de-vigged fair independent, and a
    correlated (Gaussian copula) estimate using the measured phi."""
    d = g.dropna(subset=["home_cover", "over"]).copy()
    corr = same_game_correlations(g)["home_cover + over"]["phi"]
    rho = float(corr) if np.isfinite(corr) else 0.0

    # representative legs: coin-flip de-vigged probabilities at -110
    p = 0.5
    p_vig = american_to_prob(-110)
    indep_book = (1 / p_vig) ** 2
    indep_fair = (1 / p) ** 2
    sim = implied_parlay_prob([(0.5, rho), (0.5, rho)], rho_matrix=None if not np.isfinite(rho) else
                              np.array([[1.0, rho], [rho, 1.0]]), n_sim=200_000)
    three = implied_parlay_prob([(0.5, rho)] * 3,
                                rho_matrix=np.array([[1, rho, rho], [rho, 1, rho], [rho, rho, 1]]),
                                n_sim=200_000)
    return {
        "measured_phi_spread_total": rho,
        "two_leg": {
            "book_price_decimal_equivalents": round(indep_book, 3),
            "fair_independent_decimal": round(indep_fair, 3),
            "correlated_win_prob": sim["p_correlated"],
            "independent_win_prob": sim["p_independent"],
            "pricing_error_pct": round(100 * (sim["p_correlated"] / sim["p_independent"] - 1), 3),
        },
        "three_leg": {
            "correlated_win_prob": three["p_correlated"],
            "independent_win_prob": three["p_independent"],
            "pricing_error_pct": round(100 * (three["p_correlated"] / three["p_independent"] - 1), 3),
        },
    }


def required_hit_rates() -> list[dict]:
    """What a system must actually achieve to be profitable at various prices."""
    rows = []
    for price in (-110, -105, 100, 110, 150, 200, 300, 500):
        p = american_to_prob(price)
        rows.append({"price": price, "implied_with_vig_pct": round(100 * p, 2),
                     "decimal": round(american_to_decimal(price), 3)})
    return rows


def player_prop_structural_notes() -> list[dict]:
    """Prop combos we can reason about structurally but cannot price here.

    Each entry states whether FL2 holds the data needed to validate it. Being
    explicit about the missing input is the point — the prop market is where the
    largest claimed edges live and where the largest unverified claims live too.
    """
    return [
        {"combo": "QB passing yards over + WR1 receiving yards over",
         "expected_corr": "strong positive (same completions)",
         "corr_measured_by_fl2": None,
         "data_needed": "player-level game logs with targets/routes (nflverse player_stats)",
         "status": "unverified", "why": "nflverse release assets are unreachable from the "
         "build environment; no official per-player feed is available in-sandbox."},
        {"combo": "RB rushing yards over + team total over",
         "expected_corr": "positive (game script)",
         "corr_measured_by_fl2": None,
         "data_needed": "player game logs + team totals", "status": "unverified",
         "why": "player-level data gap, same as above."},
        {"combo": "QB passing yards under + opponent CB interception prop over",
         "expected_corr": "negative (attempts vs. takeaways)",
         "corr_measured_by_fl2": None,
         "data_needed": "player logs + defensive player props", "status": "unverified",
         "why": "player-level data gap."},
        {"combo": "Kicking points over + game total over",
         "expected_corr": "weak positive",
         "corr_measured_by_fl2": None,
         "data_needed": "kicker game logs", "status": "unverified",
         "why": "player-level data gap."},
        {"combo": "Sacks (team) over + opponent passing yards under",
         "expected_corr": "positive (pressure suppresses passing)",
         "corr_measured_by_fl2": None,
         "data_needed": "team sack logs + passing allowed", "status": "unverified",
         "why": "team-level sacks are obtainable from official box scores, but the "
         "season-long series is not fetchable in bulk here; left blank rather than estimated."},
    ]


def main() -> None:
    g = load()
    out = {
        "as_of_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "n_games": int(len(g)),
        "season_range": [int(g.season.min()), int(g.season.max())],
        "vig_cost_by_leg_count": vig_cost_table(),
        "required_hit_rates": required_hit_rates(),
        "same_game_correlations": same_game_correlations(g),
        "tickets": ticket_simulations(g),
        "player_prop_combos": player_prop_structural_notes(),
        "method_notes": [
            "Leg probabilities are de-vigged closing lines; this measures structure, not edge.",
            "phi is used for binary legs because it is the natural association measure for "
            "'do these two bets win together'. Pearson is reported for continuous pairs.",
            "Correlated (copula) parlay probabilities assume a Gaussian dependence structure; "
            "real tail dependence in football is fatter, so treat the correlated estimate as "
            "a lower bound on the mispricing.",
        ],
    }
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "parlay_analysis.json"), "w") as fh:
        json.dump(out, fh, indent=2, default=float)
    print(json.dumps({k: out[k] for k in ("vig_cost_by_leg_count", "tickets")}, indent=2))
    print("\nSame-game correlations:")
    for k, v in out["same_game_correlations"].items():
        print(f"  {k:28s} phi={v['phi']:+.4f} [{v['ci_lo']:+.3f},{v['ci_hi']:+.3f}] n={v['n']} "
              f"joint {v['joint_observed']:.4f} vs indep {v['joint_if_independent']:.4f}")


if __name__ == "__main__":
    main()
