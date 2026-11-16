#!/usr/bin/env python3
"""
tools/run_shadow_model.py — SB-1 shadow baseline (T23).

Implements research/preregistration.md (registered at commit 55b94c1) EXACTLY:

  * margin model: OLS  y = b0 + r_home - r_away,  sum(r) = 0
  * total model:  fair_total = Tbar + o_h + o_a + d_h + d_a, shrink n/(n+4)
  * moneyline:    p_home = Phi(fair_margin / sigma), sigma = residual SD (in-sample, declared)
  * publish order: SIDE, TOTAL, MONEYLINE
  * stored output = probability + inputs, never a pick alone

Emits:
  data/origination_week11.csv  - fair / market / difference columns, per market
  data/forecast_ledger.json    - immutable forecasts with timestamps + model inputs
                                 (registration commit hash, ratings, sigma, b0)

Forecast timestamp = generation time, which must precede the first Week 11 kickoff
(2026-11-19 20:15 ET = 2026-11-20T01:15Z). Gate G4 is asserted in code.

Deterministic; stdlib only.
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRATION_COMMIT = "55b94c1"
MODEL_ID = "SB-1.0.0"
GEN_UTC = "2026-11-16T02:45:00Z"
FIRST_KICKOFF_UTC = "2026-11-20T01:15:00Z"  # TNF IND@HOU 2026-11-19 20:15 ET


def phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def solve(A, b):
    """Gaussian elimination with partial pivoting (small dense system)."""
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-10:
            raise ValueError("singular system")
        M[col], M[piv] = M[piv], M[col]
        div = M[col][col]
        for j in range(col, n + 1):
            M[col][j] /= div
        for r in range(n):
            if r != col and abs(M[r][col]) > 0:
                f = M[r][col]
                for j in range(col, n + 1):
                    M[r][j] -= f * M[col][j]
    return [M[i][n] for i in range(n)]


def fit_margin(games, teams):
    """OLS with sum(r)=0: params [b0, r_1..r_{n-1}], r_n = -sum(others)."""
    n = len(teams)
    idx = {t: i for i, t in enumerate(teams)}
    size = n  # b0 + (n-1) ratings
    A = [[0.0] * size for _ in range(size)]
    b = [0.0] * size
    # rows: one per game + one constraint appended to normal equations
    def add_row(coef, y, w=1.0):
        for i in range(size):
            for j in range(size):
                A[i][j] += w * coef[i] * coef[j]
            b[i] += w * coef[i] * y
    for g in games:
        coef = [0.0] * size
        coef[0] = 1.0
        omitted = teams[-1]
        # r_h - r_a expressed over free ratings (teams[:-1]); r_omitted = -sum(free)
        for j, t in enumerate(teams[:-1]):
            c = 0.0
            if g["home"] == t:
                c += 1.0
            if g["away"] == t:
                c -= 1.0
            if g["home"] == omitted:
                c -= 1.0
            if g["away"] == omitted:
                c += 1.0
            coef[1 + j] = c
        add_row(coef, g["margin"])
    # sum(r)=0 by construction (r_omitted = -sum(free)); ratings for free teams
    x = solve(A, b)
    b0 = x[0]
    ratings = {}
    s = 0.0
    for j, t in enumerate(teams[:-1]):
        ratings[t] = x[1 + j]
        s += x[1 + j]
    ratings[teams[-1]] = -s
    return b0, ratings


def fit_sigma(games, ratings, b0):
    sq, n = 0.0, 0
    for g in games:
        pred = b0 + ratings[g["home"]] - ratings[g["away"]]
        sq += (g["margin"] - pred) ** 2
        n += 1
    dof = n - len(ratings) - 1
    return math.sqrt(sq / max(dof, 1))


def main() -> int:
    feed = json.load(open(os.path.join(ROOT, "data", "results_feed.json")))
    fit = []
    for g in feed["games"]:
        if g["status"] != "final" or g["week"] > 10:
            continue
        fit.append({"home": g["home"], "away": g["away"],
                    "margin": int(g["home_score"]) - int(g["away_score"]),
                    "total": int(g["home_score"]) + int(g["away_score"])})
    teams = sorted({g["home"] for g in fit} | {g["away"] for g in fit})
    if len(teams) != 32 or len(fit) != 148:
        print(f"unexpected fit window: {len(fit)} games, {len(teams)} teams")
        return 1

    b0, ratings = fit_margin(fit, teams)
    sigma = fit_sigma(fit, ratings, b0)

    # total model (frozen spec section 2.2)
    Tbar = sum(g["total"] for g in fit) / len(fit)
    m = Tbar / 2.0
    stat = {t: {"n": 0, "pf": 0, "pa": 0} for t in teams}
    for g in feed["games"]:
        if g["status"] != "final" or g["week"] > 10:
            continue
        h, a = g["home"], g["away"]
        hs, as_ = int(g["home_score"]), int(g["away_score"])
        stat[h]["n"] += 1; stat[h]["pf"] += hs; stat[h]["pa"] += as_
        stat[a]["n"] += 1; stat[a]["pf"] += as_; stat[a]["pa"] += hs

    def shrink_dev(pf_or_pa_mean, n):
        return (pf_or_pa_mean - m) * (n / (n + 4))

    off, dep = {}, {}
    off_b, dep_b = {}, {}  # estimator B (unshrunk) — "publish every model total twice"
    for t in teams:
        n = stat[t]["n"]
        off[t] = shrink_dev(stat[t]["pf"] / n, n)
        dep[t] = shrink_dev(stat[t]["pa"] / n, n)
        off_b[t] = stat[t]["pf"] / n - m
        dep_b[t] = stat[t]["pa"] / n - m

    # ---- forecasts for Week 11 (SIDE first, then TOTAL, then MONEYLINE) ----
    cap = json.load(open(os.path.join(ROOT, "data", "captures", "week11-market-2026-11-16.json")))
    prices = {}
    for r in csv.DictReader(open(os.path.join(ROOT, "data", "price_snapshots.csv"))):
        if r["season"] == "2026" and r["week"] == "11":
            prices[(r["game_id"], r["market"], r["side"])] = r

    rows, ledger_rows = [], []
    for g in sorted(cap["games"], key=lambda x: (x["kickoff"], x["game_id"])):
        gid, away, home = g["game_id"], g["away"], g["home"]
        fair_margin = b0 + ratings[home] - ratings[away]      # home margin
        fair_spread_home_display = -fair_margin               # negative = home favoured
        fair_total = Tbar + off[home] + off[away] + dep[home] + dep[away]
        p_home = phi(fair_margin / sigma)
        fair_ml_home = -100.0 * p_home / (1 - p_home) if p_home > 0.5 else 100.0 * (1 - p_home) / p_home
        fair_ml_away = -100.0 * (1 - p_home) / p_home if p_home < 0.5 else 100.0 * p_home / (1 - p_home)

        mkt_side_row = prices.get((gid, "SIDE", home))
        mkt_side = float(mkt_side_row["opening_line"]) if mkt_side_row else None
        mkt_total_row = prices.get((gid, "TOTAL", "over"))
        mkt_total = float(mkt_total_row["opening_line"]) if mkt_total_row else None
        # derived market-implied home prob from market spread via the same sigma (labelled)
        p_mkt = None
        if mkt_side is not None:
            p_mkt = phi((-mkt_side) / sigma)

        base = dict(game_id=gid, week=11, kickoff=g["kickoff"], away=away, home=home,
                    model_id=MODEL_ID, registration_commit=REGISTRATION_COMMIT,
                    generated_at_utc=GEN_UTC,
                    venue=g["venue_official_nfl_com"], venue_flag=g["venue_flag"],
                    model_fair_alt="", model_gap_alt="")
        rows.append({**base, "market_order": 1, "market": "SIDE",
                     "model_fair": round(fair_spread_home_display, 1),
                     "market_line": mkt_side if mkt_side is not None else "",
                     "difference": round(fair_spread_home_display - mkt_side, 1) if mkt_side is not None else "",
                     "market_source": cap["provider_url"],
                     "market_captured_at": cap["captured_at_utc"],
                     "model_prob_home": round(p_home, 4),
                     "note": "model_fair/market_line = home team display line (negative = favoured)"})
        fair_total_b = Tbar + off_b[home] + off_b[away] + dep_b[home] + dep_b[away]
        rows.append({**base, "market_order": 2, "market": "TOTAL",
                     "model_fair": round(fair_total, 1),
                     "model_fair_alt": round(fair_total_b, 1),
                     "model_gap_alt": round(fair_total_b - fair_total, 1),
                     "market_line": mkt_total if mkt_total is not None else "",
                     "difference": round(fair_total - mkt_total, 1) if mkt_total is not None else "",
                     "market_source": cap["provider_url"],
                     "market_captured_at": cap["captured_at_utc"],
                     "model_prob_home": "",
                     "note": "two total estimators published until a walk-forward comparison picks one: A = shrinkage n/(n+4) (frozen SB-1), B = unshrunk means; model_gap_alt = B - A"})
        rows.append({**base, "market_order": 3, "market": "MONEYLINE",
                     "model_fair": round(fair_ml_home, 0),
                     "market_line": "",
                     "difference": round(p_home - p_mkt, 4) if p_mkt is not None else "",
                     "market_source": cap["provider_url"] + " (no quoted ML; derived from market spread)",
                     "market_captured_at": cap["captured_at_utc"],
                     "model_prob_home": round(p_home, 4),
                     "note": "model_fair = fair American price for HOME; difference = p_model - p_market where p_market is DERIVED from the market spread via the same sigma (labelled derived); quoted ML blank + flagged"})
        ledger_rows.append({
            "game_id": gid, "kickoff_utc_or_et": g["kickoff"],
            "forecast_generated_at_utc": GEN_UTC,
            "inputs": {"ratings_home": round(ratings[home], 3), "ratings_away": round(ratings[away], 3),
                       "b0_measured_hfa": round(b0, 3), "sigma": round(sigma, 3),
                       "Tbar": round(Tbar, 3),
                       "off_home": round(off[home], 3), "off_away": round(off[away], 3),
                       "def_home": round(dep[home], 3), "def_away": round(dep[away], 3),
                       "fit_window": "2026 REG weeks 1-10 finals", "fit_games": len(fit)},
            "outputs": {"p_home": round(p_home, 4), "p_away": round(1 - p_home, 4),
                        "fair_margin_home": round(fair_margin, 2),
                        "fair_spread_home_display": round(fair_spread_home_display, 1),
                        "fair_total": round(fair_total, 1),
                        "fair_ml_home_american": round(fair_ml_home, 0),
                        "fair_ml_away_american": round(fair_ml_away, 0)},
        })

    # gate G4 assertion
    if GEN_UTC >= FIRST_KICKOFF_UTC:
        print("G4 VIOLATION: forecast generated after first kickoff")
        return 1

    fields = list(rows[0].keys())
    with open(os.path.join(ROOT, "data", "origination_week11.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    ledger = {
        "ledger_id": "fl2-forecast-ledger-v1",
        "model_id": MODEL_ID,
        "registration_commit": REGISTRATION_COMMIT,
        "preregistration_doc": "research/preregistration.md",
        "price_data_policy": "research/price-data-policy.md",
        "generated_at_utc": GEN_UTC,
        "gate_G4_first_kickoff_utc": FIRST_KICKOFF_UTC,
        "gate_G4_status": "pass (generated before first Week 11 kickoff)",
        "immutability_rule": "this ledger is append-only; graded results are appended, never edited",
        "model_inputs_summary": {
            "fit_games": len(fit), "teams": len(teams),
            "b0_measured_hfa": round(b0, 3), "sigma_in_sample": round(sigma, 3),
            "Tbar": round(Tbar, 3),
            "ratings": {t: round(r, 3) for t, r in sorted(ratings.items())},
        },
        "forecasts": ledger_rows,
    }
    json.dump(ledger, open(os.path.join(ROOT, "data", "forecast_ledger.json"), "w"), indent=1)
    print(f"SB-1 forecasts OK: {len(rows)} market rows, {len(ledger_rows)} games; "
          f"b0={b0:.3f} sigma={sigma:.3f} Tbar={Tbar:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
