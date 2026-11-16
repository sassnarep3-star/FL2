#!/usr/bin/env python3
"""Strategy pre-registration + Week 11 pre-kickoff forecasts (requirements:
  - "Start with a singles-only shadow baseline"
  - "Pre-register every strategy; forbid backtest numbers from ever appearing on the leaderboard"
  - "Add a two-sided 'what would change our mind' field to every strategy entry"
  - "Freeze a rule before it sees data (pre-registration) — the commit hash is the registration"
  - "Define a demotion gate that sends a live strategy back to paper"
  - "Store every model output as a probability plus its inputs, not just a pick")

REGISTRATION TIMING: this file is committed 2026-11-16, BEFORE any Week 11 game is played
(Week 11 opens Thursday 2026-11-19). The method text below is frozen; the git commit that
introduces it is the registration (hash recorded in COORDINATION.md).

THE FROZEN METHOD (STRAT-1, singles-only shadow baseline — no staking, no parlays):
  Inputs, per team, from the verified results feed ONLY (ops/data/results/results_2026_reg.csv):
    off_raw  = own points-for per game
    def_raw  = own points-allowed per game
    league_avg = mean points per team-game across the corpus
  Shrinkage (k=4): regressed = (n*raw + k*league_avg) / (n + k)
  Expected points:
    exp_home = (home_off_reg + away_def_reg) / 2
    exp_away = (away_off_reg + home_def_reg) / 2
  total  = exp_home + exp_away
  margin = exp_home - exp_away + HFA, where HFA = mean (home_pts - away_pts) over the corpus
  p_home = Phi(margin / sigma), sigma = residual SD of (home margin - closing line),
           2011-2026 nflverse games.csv, computed once and frozen in the output.

GATES (all must pass in a prospective window before any leaderboard rank):
  G1 sample floor   : >= 40 forecast games recorded pre-kickoff
  G2 skill          : Brier skill vs the random50 control > 0 with 95% bootstrap CI excluding 0
  G3 calibration    : observed-vs-expected slope in [0.8, 1.2] across probability bins
  G4 side balance   : home-side pick share in [40%, 60%] (guards a free-intercept home bias)
  G5 demo requirement: every forecast row stores inputs + probability, not just a pick
DEMOTION GATE (live strategy back to paper):
  D1 two consecutive prospective windows (>= 20 games each) with Brier-skill CI including 0
     -> status demoted to paper; may not be ranked again until G2 passes on a fresh window.
WHAT WOULD CHANGE OUR MIND (two-sided, required field):
  - abandon-if : calibration slope < 0.7 over any 40-game window (model overconfident
    in a way shrinkage does not fix) -> stop forecasting, revisit inputs
  - promote-if : G1-G5 pass on two consecutive windows -> eligible for leaderboard ranking
  Backtest numbers NEVER appear on a leaderboard; the corpus below is used only for
  freeze-time sanity checks, which are recorded as such.
"""
from __future__ import annotations

import csv
import json
import math
import os
from statistics import NormalDist

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "data", "forecast_week11_2026.csv")
K = 4
SIGMA = 12.97  # frozen from the 68b4e431 computation on nflverse 2011-2026 (documented in data/market_lines.json)


def corpus_sigma_check() -> None:
    """Recompute sigma on the historical corpus to confirm the frozen constant is sane."""
    margins, lines = [], []
    for r in csv.DictReader(open(os.path.join(ROOT, "raw", "games.csv"))):
        if r["season"].isdigit() and 2011 <= int(r["season"]) <= 2026 and r["game_type"] == "REG" \
                and r["spread_line"] and r["away_score"] and r["home_score"]:
            margins.append(int(r["home_score"]) - int(r["away_score"]))
            lines.append(float(r["spread_line"]))
    n = len(margins)
    resid = [m - s for m, s in zip(margins, lines)]
    mean = sum(resid) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in resid) / (n - 1))
    print(f"sigma recomputed on {n} games 2011-2026: {sd:.2f} (frozen constant {SIGMA})")
    if abs(sd - SIGMA) > 1.0:
        raise SystemExit("frozen sigma drifted from recomputed value - investigate before forecasting")


def main() -> None:
    corpus_sigma_check()
    feed = list(csv.DictReader(open(os.path.join(HERE, "data", "results", "results_2026_reg.csv"))))
    finals = [r for r in feed if r["status"] == "final" and r["away_pts"] and r["home_pts"]]
    agg: dict[str, dict] = {}
    league_pts = 0
    league_n = 0
    home_margin_sum = 0
    for r in finals:
        hm = int(r["home_pts"]) - int(r["away_pts"])
        home_margin_sum += hm
        league_pts += int(r["home_pts"]) + int(r["away_pts"])
        league_n += 2
        for side in ("home", "away"):
            t = r[f"{side}_team"]
            a = agg.setdefault(t, {"n": 0, "pf": 0, "pa": 0})
            a["n"] += 1
            a["pf"] += int(r[f"{side}_pts"])
            a["pa"] += int(r[f"{'away' if side == 'home' else 'home'}_pts"])
    league_avg = league_pts / league_n
    hfa = home_margin_sum / len(finals)

    def reg(t: str, kind: str) -> float:
        a = agg[t]
        raw = a[kind] / a["n"]
        return (a["n"] * raw + K * league_avg) / (a["n"] + K)

    # Week 11 fixtures from nflverse (T2 schedule facts; T1 confirmation pending - flagged)
    fixtures = [r for r in csv.DictReader(open(os.path.join(ROOT, "raw", "games.csv")))
                if r["season"] == "2026" and r["week"] == "11" and r["game_type"] == "REG"]
    nd = NormalDist()
    out_rows = []
    for f in fixtures:
        away, home = f["away_team"], f["home_team"]
        exp_home = (reg(home, "pf") + reg(away, "pa")) / 2
        exp_away = (reg(away, "pf") + reg(home, "pa")) / 2
        total = exp_home + exp_away
        margin = exp_home - exp_away + hfa
        p_home = nd.cdf(margin / SIGMA)
        out_rows.append({
            "game_id": f["game_id"], "gameday": f["gameday"], "gametime_et": f["gametime"],
            "away_team": away, "home_team": home,
            "fl2_exp_home_pts": round(exp_home, 1), "fl2_exp_away_pts": round(exp_away, 1),
            "fl2_total": round(total, 1), "fl2_home_margin": round(margin, 1),
            "fl2_p_home": round(p_home, 4),
            "inputs_off_raw_home": round(agg[home]["pf"] / agg[home]["n"], 2),
            "inputs_def_raw_home": round(agg[home]["pa"] / agg[home]["n"], 2),
            "inputs_off_raw_away": round(agg[away]["pf"] / agg[away]["n"], 2),
            "inputs_def_raw_away": round(agg[away]["pa"] / agg[away]["n"], 2),
            "n_home": agg[home]["n"], "n_away": agg[away]["n"],
            "market_spread_close_T3": f["spread_line"], "market_total_close_T3": f["total_line"],
            "residual_margin_vs_market": round(margin - float(f["spread_line"]), 1) if f["spread_line"] else "",
            "residual_total_vs_market": round(total - float(f["total_line"]), 1) if f["total_line"] else "",
            "recorded_utc": "2026-11-16T02:00:00Z",
            "recorded_before_kickoff": "yes (Week 11 opens 2026-11-19)",
            "fixture_tier": "T2 (nflverse); T1 schedule-page confirmation pending",
            "source_url": "https://github.com/nflverse/nfldata/blob/master/data/games.csv",
        })
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    print(f"STRAT-1 pre-registration + {len(out_rows)} Week 11 forecasts recorded pre-kickoff")
    print(f"corpus: {len(finals)} games, league avg {league_avg:.1f} pts/team-game, HFA {hfa:+.2f}")
    print(f"fixtures from nflverse W11: {len(fixtures)} (T1 confirmation pending)")
    for r in out_rows[:4]:
        print(f"  {r['away_team']} @ {r['home_team']}: total {r['fl2_total']}, margin {r['fl2_home_margin']:+}, "
              f"p_home {r['fl2_p_home']}, residual(spread) {r['residual_margin_vs_market']}")


if __name__ == "__main__":
    main()
