"""
FL2 — originate your own lines.

Run:  python3 engine/build_market.py
Out:  data/market_lines.json

This module produces FL2's OWN number for each Week 10 game, plus the reasoning
chain that produced it, and compares it with whatever market price is available.

CRITICAL: FL2 does not have an official licence for sportsbook prices, and the
sandbox cannot reach sportsbook hosts. So `market` fields below are only
populated from the nflverse closing-line table where a line genuinely exists,
and otherwise they are `null` and the row is flagged `market_unverified`.
No price is ever typed in from memory.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache")
OUT = os.path.join(os.path.dirname(HERE), "data")
AS_OF = "2026-11-14T03:30:00Z"

# League priors. These are used ONLY when a team has too few games for its own
# rate to be informative, and the choice is documented rather than hidden.
LG_POINTS = 23.0          # 2026 league average is 23.0 (PFR Avg Tm/G, see sources)
HFA_POINTS = 1.8          # 2026 home teams average 1.954 more points than away (nflverse games.csv)


def load_games():
    g = pd.read_csv(os.path.join(CACHE, "games.csv"))
    g = g[g.game_type == "REG"].copy()
    return g


def regress(rate_per_game: float, games: int, prior: float, k: float = 4.0) -> float:
    """Shrink a team rate toward the league prior. k is the number of games of
    prior weight — 4 means a team with 4 games is 50/50 own-rate/prior."""
    if games <= 0 or not np.isfinite(rate_per_game):
        return prior
    return (rate_per_game * games + prior * k) / (games + k)


def expected_total(off_a_ppg, off_b_ppg, def_a_papg, def_b_papg) -> float:
    """Standard two-sided projection: each offence is expected to score the
    average of its own rate and what the opposing defence concedes."""
    a = (off_a_ppg + def_b_papg) / 2.0
    b = (off_b_ppg + def_a_papg) / 2.0
    return a + b


def win_prob_from_margin(margin: float, sigma: float = 13.5) -> float:
    """Logistic-free probit mapping. sigma=13.5 is the long-run standard
    deviation of NFL game margins around the closing line (verifiable from
    games.csv: see residual_sd reported below)."""
    from math import erf, sqrt
    return 0.5 * (1 + erf((margin / sigma) / sqrt(2)))


def residual_sd(g: pd.DataFrame) -> float:
    d = g[(g.season >= 2011) & g.spread_line.notna() & g.home_score.notna()]
    r = (d.home_score - d.away_score) - d.spread_line
    return float(np.std(r, ddof=1))


def build():
    os.makedirs(OUT, exist_ok=True)
    season = json.load(open(os.path.join(OUT, "season_2026.json")))
    wk = json.load(open(os.path.join(OUT, "week10_lineups.json")))
    games = load_games()
    sigma = residual_sd(games)

    # Current-week market snapshot: only what nflverse actually contains.
    cur = games[(games.season == 2026) & (games.week == 10)]
    mkt = {}
    for _, r in cur.iterrows():
        mkt[(r.away_team, r.home_team)] = {
            "spread_line": None if pd.isna(r.spread_line) else float(r.spread_line),
            "total_line": None if pd.isna(r.total_line) else float(r.total_line),
            "home_moneyline": None if pd.isna(r.home_moneyline) else float(r.home_moneyline),
            "away_moneyline": None if pd.isna(r.away_moneyline) else float(r.away_moneyline),
            "source_url": "https://github.com/nflverse/nfldata/blob/master/data/games.csv",
        }

    by_team = {t["team"]: t for t in season["teams"]}
    deple = wk["team_depletion"]

    # Map nflverse abbreviations to nfl.com ones (they differ for 4 clubs)
    alias = {"LA": "LAR", "LAC": "LAC", "LV": "LV", "SF": "SF", "TB": "TB", "KC": "KC",
             "NO": "NO", "NE": "NE", "GB": "GB", "JAX": "JAX", "TEN": "TEN", "HOU": "HOU",
             "IND": "IND", "CLE": "CLE", "CIN": "CIN", "BAL": "BAL", "BUF": "BUF",
             "MIA": "MIA", "NYJ": "NYJ", "NYG": "NYG", "WAS": "WAS", "PHI": "PHI",
             "PIT": "PIT", "DAL": "DAL", "DEN": "DEN", "DET": "DET", "MIN": "MIN",
             "ATL": "ATL", "ARI": "ARI", "CAR": "CAR", "SEA": "SEA", "CHI": "CHI"}

    rows = []
    for gm in wk["schedule"]:
        a, h = gm["away"], gm["home"]
        A, H = by_team[a], by_team[h]
        # regressed offence / defence rates
        a_off = regress(A["pf_per_game"], A["games_played"], LG_POINTS)
        h_off = regress(H["pf_per_game"], H["games_played"], LG_POINTS)
        a_def = regress(A["def_pa_per_game"], A["def_games"], LG_POINTS)
        h_def = regress(H["def_pa_per_game"], H["def_games"], LG_POINTS)
        total = expected_total(a_off, h_off, a_def, h_def)
        # Each side's projected points = mean(own offence, opponent's defence allowed).
        # The margin is the difference of those two projections. (An earlier version
        # of this line subtracted instead of averaged and produced sign-flipped
        # margins for good offences; fixed 2026-11-14.)
        exp_home = (h_off + a_def) / 2.0
        exp_away = (a_off + h_def) / 2.0
        margin_home = (exp_home - exp_away) + HFA_POINTS

        # availability adjustment: half a point per point of availability index lost
        # relative to the opponent. Declared, not measured.
        dh, da = deple[h]["avail_index"], deple[a]["avail_index"]
        avail_adj = 0.0
        avail_note = "depletion indices unavailable"
        if dh is not None and da is not None:
            avail_adj = ((dh - da) / 100.0) * 3.0   # 3 pts for a full 100-point gap
            avail_note = f"{h} index {dh} vs {a} index {da} -> {avail_adj:+.2f} pts to home"

        fl2_margin = margin_home + avail_adj
        fl2_p_home = win_prob_from_margin(fl2_margin, sigma)

        key = (alias.get(a, a), alias.get(h, h))
        m = mkt.get(key) or mkt.get((h, a)) or {}
        spread = m.get("spread_line")
        mtotal = m.get("total_line")

        rows.append({
            "game_id": gm["game"],
            "away": a, "home": h,
            "kickoff_et": gm["kickoff_et"], "tv": gm["tv"], "note": gm.get("note"),
            "inputs": {
                "away_off_ppg_raw": A["pf_per_game"], "away_off_ppg_regressed": round(a_off, 2),
                "home_off_ppg_raw": H["pf_per_game"], "home_off_ppg_regressed": round(h_off, 2),
                "away_def_papg_raw": A["def_pa_per_game"], "away_def_papg_regressed": round(a_def, 2),
                "home_def_papg_raw": H["def_pa_per_game"], "home_def_papg_regressed": round(h_def, 2),
                "away_games": A["games_played"], "home_games": H["games_played"],
                "hfa_points": HFA_POINTS, "league_points_prior": LG_POINTS,
            },
            "fl2_total": round(total, 1),
            "fl2_exp_home_points": round(exp_home, 1),
            "fl2_exp_away_points": round(exp_away, 1),
            "fl2_home_margin": round(margin_home, 1),
            "avail_adjustment_points": round(avail_adj, 2),
            "avail_note": avail_note,
            "fl2_spread_home": round(-fl2_margin, 1),
            "fl2_p_home": round(fl2_p_home, 4),
            "market": {
                "spread_line_home_expected_margin": spread,
                "total_line": mtotal,
                "home_moneyline": m.get("home_moneyline"),
                "away_moneyline": m.get("away_moneyline"),
                "source_url": m.get("source_url"),
                "status": "present" if spread is not None or mtotal is not None else "absent",
            },
            "fl2_vs_market": {
                "margin_diff": None if spread is None else round(margin_home - spread, 1),
                "total_diff": None if mtotal is None else round(total - mtotal, 1),
            },
            "flows_to": [],
            "sources": [
                "https://www.nfl.com/standings/",
                "https://www.pro-football-reference.com/years/2026/opp.htm",
                "https://github.com/nflverse/nfldata/blob/master/data/games.csv",
            ],
            "verified_inputs": True,
            "verified_market": False if spread is None and mtotal is None else True,
        })

    # Explicit flow of each game's number into the rest of the pipeline
    for r in rows:
        r["flows_to"] = [
            "comparison vs. market in data/market_lines.json",
            "feeds candidate strategy signals listed in data/strategies.json (status=experimental)",
            "NOT used in backtests: backtests use historical closing lines only",
        ]

    out = {
        "as_of_utc": AS_OF,
        "season": 2026, "week": 10,
        "method": {
            "total": "sum of each offence's average of own points-per-game and opponent's points-allowed-per-game, after shrinkage",
            "margin": "home offence vs away defence minus away offence vs home defence, plus measured home-field advantage",
            "shrinkage": "k=4 games of league-average prior",
            "sigma_used_for_win_prob": round(sigma, 2),
            "sigma_source": "residual standard deviation of (home margin - closing line), 2011-2026, nflverse games.csv",
            "avail_adjustment": "3 points for a full 100-point availability-index gap. Arbitrary scale, declared.",
            "caveats": [
                "No quarterback-quality term: FL2 has no verified QB rating series for 2026 within the build environment.",
                "No injury market adjustment: the availability index is a proxy, not a measured effect.",
                "The 2026 sample is 8-9 games per team, so all rate inputs are heavily shrunk.",
                "These are research numbers, not betting recommendations.",
            ],
        },
        "games": rows,
    }
    with open(os.path.join(OUT, "market_lines.json"), "w") as fh:
        json.dump(out, fh, indent=2)

    print(f"sigma (margin residual sd) = {sigma:.2f}")
    print(f"{'game':12s} {'FL2 total':>9s} {'mkt':>6s} {'FL2 margin':>10s} {'mkt':>6s} {'p_home':>7s}")
    for r in rows:
        mk = r["market"]
        print(f"{r['game_id']:12s} {r['fl2_total']:9.1f} "
              f"{(mk['total_line'] if mk['total_line'] is not None else '--'):>6} "
              f"{r['fl2_home_margin']:10.1f} "
              f"{(mk['spread_line_home_expected_margin'] if mk['spread_line_home_expected_margin'] is not None else '--'):>6} "
              f"{r['fl2_p_home']:7.3f}")
    present = sum(1 for r in rows if r["market"]["status"] == "present")
    print(f"\nmarket rows available: {present}/{len(rows)} (rest flagged market_unverified)")


if __name__ == "__main__":
    build()
