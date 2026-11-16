#!/usr/bin/env python3
"""Removal-of-luck panel (requirement: 'Compute and publish the "removal of luck" panel').

Method
  Pythagorean expectation with the NFL exponent 2.37 (Pro Football Reference's published
  regression value, https://www.pro-football-reference.com/about/blog.htm):
      pyth_win_pct = PF^2.37 / (PF^2.37 + PA^2.37)
  luck_residual = actual_wins - (pyth_win_pct * games)
  n = games played per team (published with every value; requirement:
      'publish n with each value').

Inputs are the verified results feed only (ops/data/results/results_2026_reg.csv, T1 rows).
No market data, no inference. Standings computed from verified game results are a
re-computation, not a new claim.
"""
from __future__ import annotations

import csv
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "luck_panel_2026.csv")
EXP = 2.37


def main() -> None:
    rows = list(csv.DictReader(open(os.path.join(HERE, "data", "results", "results_2026_reg.csv"))))
    finals = [r for r in rows if r["status"] == "final" and r["away_pts"] and r["home_pts"]]
    agg: dict[str, dict] = {}
    for r in finals:
        for side, opp_side, pts_col, opp_col in (("home", "away", "home_pts", "away_pts"),
                                                 ("away", "home", "away_pts", "home_pts")):
            t = r[f"{side}_team"]
            a = agg.setdefault(t, {"games": 0, "w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0})
            ap, hp = int(r[pts_col]), int(r[opp_col])
            a["games"] += 1
            a["pf"] += ap
            a["pa"] += hp
            if ap > hp:
                a["w"] += 1
            elif ap < hp:
                a["l"] += 1
            else:
                a["t"] += 1
    out_rows = []
    for t, a in sorted(agg.items()):
        pf, pa = a["pf"], a["pa"]
        pyth = (pf ** EXP) / (pf ** EXP + pa ** EXP) if (pf + pa) else 0.0
        expected = pyth * a["games"]
        luck = a["w"] - expected
        out_rows.append({
            "team": t, "games": a["games"], "w": a["w"], "l": a["l"], "t": a["t"],
            "pf": pf, "pa": pa,
            "actual_win_pct": round(a["w"] / a["games"], 3) if a["games"] else "",
            "pyth_win_pct": round(pyth, 3),
            "pyth_expected_wins": round(expected, 1),
            "luck_wins_vs_pyth": round(luck, 1),
            "n_games": a["games"],
        })
    out_rows.sort(key=lambda r: -r["luck_wins_vs_pyth"])
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    luckiest = out_rows[0]
    unluckiest = out_rows[-1]
    over = sum(1 for r in out_rows if r["luck_wins_vs_pyth"] > 0.5)
    under = sum(1 for r in out_rows if r["luck_wins_vs_pyth"] < -0.5)
    print(f"luck panel: {len(out_rows)} teams, n={len(finals)} games")
    print(f"  most fortunate: {luckiest['team']} {luckiest['luck_wins_vs_pyth']:+} wins vs Pythag (n={luckiest['n_games']})")
    print(f"  least fortunate: {unluckiest['team']} {unluckiest['luck_wins_vs_pyth']:+} wins vs Pythag (n={unluckiest['n_games']})")
    print(f"  teams +/-0.5 wins vs Pythag: {over} over, {under} under (of 32)")
    # sanity: teams' games should be near n*2/32
    total_games = sum(r["games"] for r in out_rows)
    assert total_games == 2 * len(finals), "games double-count mismatch"
    # binomial SD of wins for an average team at n games ≈ sqrt(n*0.5*0.5)
    n = len(finals) * 2 / 32
    print(f"  binomial 1-sigma of luck at n={n:.1f} games/team ≈ {math.sqrt(n*0.25):.2f} wins")


if __name__ == "__main__":
    main()
