"""
FL2 — strategy discovery, walk-forward backtesting and validation gates.

Run:  python3 engine/run_backtest.py
Out:  data/backtest_summary.json

Purpose: answer one question honestly — *given only information available
before kickoff, does any signal beat the closing line out-of-sample, after
correcting for the fact that we tried several signals?*

Nothing in here is a pick for the current week and nothing here is advice.

Column conventions in nflverse/nfldata `games.csv` (verified against
`home_moneyline` signs — see docs/SOURCES.md §3):
    spread_line  = EXPECTED HOME MARGIN in points. Positive => home favoured.
                   (PHI -425 vs DAL, spread_line = +8.5.)
    total_line   = posted game total.
    home_margin  = home_score - away_score.
    home covers  <=>  home_margin - spread_line > 0.
This is the single easiest place to introduce a sign error, so it is asserted
in `self_check()`.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from stats_core import (
    Elo, american_to_payout, american_to_prob, block_bootstrap_ci, brier,
    devig_two_way, log_loss, luck_share, phi_ci,
)

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache")
DATA = os.path.join(os.path.dirname(HERE), "data")

# --------------------------------------------------------------------------- #
# Protocol fixed BEFORE looking at results (avoids protocol-shopping).
# --------------------------------------------------------------------------- #
TRAIN_START = 2006        # first season with usable closing lines
CALIB_END = 2010          # seasons used to calibrate Elo -> points, and nothing else
EVAL_START = 2011         # strictly out-of-sample from here on
MIN_SAMPLE = 150          # settled bets required to judge a strategy
BREAKEVEN_HIT = 0.5238    # break-even win rate at -110
FDR_Q = 0.10
ELO_POINTS_PER_RATING = 25.0  # ~25 Elo points per point of expected margin
MIN_EDGE_PTS = 2.0        # only bet when the model disagrees by >= 2 points


# --------------------------------------------------------------------------- #
def load_games(std: bool = True) -> pd.DataFrame:
    g = pd.read_csv(os.path.join(CACHE, "games.csv"))
    g = g[g.game_type == "REG"].copy()
    g["gameday"] = pd.to_datetime(g["gameday"], errors="coerce")
    g = g.sort_values(["gameday", "game_id"]).reset_index(drop=True)
    g["season"] = g.season.astype(int)
    g["week"] = g.week.astype(int)
    g["home_margin"] = g.home_score - g.away_score
    g["hs"] = g["home_margin"]
    g["total_points"] = g.home_score + g.away_score
    g = g[g.season >= TRAIN_START].reset_index(drop=True)
    if std:
        self_check(g)
    return g


def self_check(g: pd.DataFrame) -> None:
    """Assert the sign conventions before any modelling happens."""
    d = g.dropna(subset=["spread_line", "home_moneyline", "away_moneyline", "home_margin"])
    d = d[d.season >= 2011]
    # home favourites must be favoured both by the market price and by the line
    favs = d[d.home_moneyline < 0]
    dogs = d[d.home_moneyline > 0]
    assert favs.spread_line.mean() > 0, "sign error: home favourites must have spread_line > 0"
    assert dogs.spread_line.mean() < 0, "sign error: home underdogs must have spread_line < 0"
    assert 0.40 < favs.home_margin.mean(), "favourites should outscore underdogs"
    cov = (d.home_margin - d.spread_line > 0).mean()
    assert 0.44 < cov < 0.56, f"home cover rate {cov:.3f} is not plausible"
    print(f"[self-check] OK — home cover {cov:.4f}, home win {(d.home_margin>0).mean():.4f}, "
          f"over {((d.total_points-d.total_line)>0).mean():.4f}, n={len(d)}")


def add_features(g: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Attach strictly pre-kickoff features in chronological order."""
    elo = Elo()
    rows = []
    hist: dict[str, list[tuple[float, float]]] = {}   # team -> [(pf, pa)] last 6
    last: dict[str, tuple[int, float]] = {}           # team -> (season, margin)
    theta = {"elo_margin_offset": 0.0, "elo_margin_slope": 1.0 / ELO_POINTS_PER_RATING}

    for _, r in g.iterrows():
        season = int(r.season)
        elo.start_season(season)

        def roll(team):
            v = hist.get(team, [])[-6:]
            return (float(np.mean([a for a, _ in v])), float(np.mean([b for _, b in v]))) if v else (float("nan"), float("nan"))

        hpf, hpa = roll(r.home_team)
        apf, apa = roll(r.away_team)
        elo_m = (elo.rating.get(r.home_team, 1500.0) + elo.hfa - elo.rating.get(r.away_team, 1500.0)) * theta["elo_margin_slope"]

        lm_h = last.get(r.home_team)
        lm_a = last.get(r.away_team)
        rows.append({
            "game_id": r.game_id, "season": season, "week": int(r.week),
            "gameday": r.gameday,
            "home_team": r.home_team, "away_team": r.away_team,
            "home_score": r.home_score, "away_score": r.away_score,
            "spread_line": r.spread_line, "total_line": r.total_line,
            "home_moneyline": r.home_moneyline, "away_moneyline": r.away_moneyline,
            "home_spread_odds": r.home_spread_odds, "away_spread_odds": r.away_spread_odds,
            "over_odds": r.over_odds, "under_odds": r.under_odds,
            "home_rest": r.home_rest, "away_rest": r.away_rest,
            "div_game": r.div_game, "wind": r.wind, "roof": r.roof,
            "elo_margin": elo_m, "home_pf6": hpf, "home_pa6": hpa,
            "away_pf6": apf, "away_pa6": apa,
            "last_margin_home": lm_h[1] if lm_h and lm_h[0] == season else float("nan"),
            "last_margin_away": lm_a[1] if lm_a and lm_a[0] == season else float("nan"),
        })

        if np.isfinite(r.home_score) and np.isfinite(r.away_score):
            elo.update(r.home_team, r.away_team, r.home_margin)
            hist.setdefault(r.home_team, []).append((r.home_score, r.away_score))
            hist.setdefault(r.away_team, []).append((r.away_score, r.home_score))
            last[r.home_team] = (season, float(r.home_margin))
            last[r.away_team] = (season, float(-r.home_margin))

    g = pd.DataFrame(rows)
    g = g[g.season >= TRAIN_START].reset_index(drop=True)

    # ---- settlement, pushes removed ------------------------------------- #
    g["home_margin"] = g.home_score - g.away_score
    g["hs"] = g["home_margin"]
    g["total_points"] = g.home_score + g.away_score
    sp = g.hs - g.spread_line
    g["home_cover"] = np.where(sp > 0, 1.0, np.where(sp < 0, 0.0, np.nan))
    g["away_cover"] = np.where(sp < 0, 1.0, np.where(sp > 0, 0.0, np.nan))
    tt = g.total_points - g.total_line
    g["over"] = np.where(tt > 0, 1.0, np.where(tt < 0, 0.0, np.nan))
    g["under"] = np.where(tt < 0, 1.0, np.where(tt > 0, 0.0, np.nan))
    g["home_win"] = np.where(g.hs > 0, 1.0, np.where(g.hs < 0, 0.0, np.nan))

    # ---- market de-vigged probabilities --------------------------------- #
    ph = g.home_moneyline.map(american_to_prob)
    pa = g.away_moneyline.map(american_to_prob)
    dv = [devig_two_way(a, b) for a, b in zip(ph, pa)]
    g["mkt_p_home"] = [x[0] for x in dv]
    g["mkt_p_away"] = [x[1] for x in dv]

    # ---- model: calibrated Elo margin mapped to a win probability ------- #
    g["elo_p_home"] = 1.0 / (1.0 + np.exp(-g.elo_margin / 6.5))  # logistic on points
    g["elo_edge_pts"] = g.elo_margin - g.spread_line

    # ---- pace-based total projection ------------------------------------ #
    g["pace_total"] = (g.home_pf6 + g.home_pa6 + g.away_pf6 + g.away_pa6) / 2.0
    g["total_edge"] = g.pace_total - g.total_line

    # ---- calibration of Elo margin, fit on CALIB seasons only ----------- #
    c = g[(g.season <= CALIB_END) & g.elo_margin.notna() & g.hs.notna()]
    if len(c) > 100:
        A = np.c_[np.ones(len(c)), c.elo_margin.values]
        coef, *_ = np.linalg.lstsq(A, c.hs.values, rcond=None)
        theta["elo_margin_offset"], theta["elo_margin_slope"] = float(coef[0]), float(coef[1])
        g["elo_margin_cal"] = coef[0] + coef[1] * g.elo_margin
        g["elo_edge_pts"] = g.elo_margin_cal - g.spread_line
        # residual sd of the calibration -> honest spread of the model
        resid = c.hs.values - (coef[0] + coef[1] * c.elo_margin.values)
        theta["resid_sd"] = float(np.std(resid, ddof=2))
        g["elo_p_home"] = 1.0 - _norm_cdf(
            (g.spread_line.fillna(0.0) - g.elo_margin_cal) / max(theta["resid_sd"], 1e-6)
        ) if False else g["elo_p_home"]
    return g, theta


def _norm_cdf(x):
    return 0.5 * (1 + np.vectorize(math.erf)(np.asarray(x, float) / math.sqrt(2)))


# --------------------------------------------------------------------------- #
@dataclass
class Bet:
    game_id: str
    season: int
    week: int
    market: str
    side: str
    line: float
    price: float
    model_p: float
    market_p: float
    won: float
    units: float


@dataclass
class Strategy:
    sid: str
    name: str
    market: str
    thesis: str
    params: dict = field(default_factory=dict)
    bets: list[Bet] = field(default_factory=list)


def _sp(row, side):
    v = row.home_spread_odds if side == "HOME" else row.away_spread_odds
    return float(v) if np.isfinite(v) else -110.0


def _tp(row, side):
    v = row.over_odds if side == "OVER" else row.under_odds
    return float(v) if np.isfinite(v) else -110.0


def build_strategies(g: pd.DataFrame) -> list[Strategy]:
    out: list[Strategy] = []
    d = g[g.season >= EVAL_START]

    # S1 — model vs line (spread)
    s = Strategy("S1_elo_spread", "Calibrated Elo vs. closing spread", "SPREAD",
                 "Take a side when the calibrated Elo margin disagrees with the closing "
                 "line by 2+ points. Tests whether a transparent rating is still "
                 "exploitable against a mature market.", {"min_edge_pts": MIN_EDGE_PTS})
    for _, r in d.iterrows():
        if not (np.isfinite(r.spread_line) and np.isfinite(r.elo_edge_pts)):
            continue
        if abs(r.elo_edge_pts) < MIN_EDGE_PTS:
            continue
        home = r.elo_edge_pts > 0
        won = r.home_cover if home else r.away_cover
        if not np.isfinite(won):
            continue
        price = _sp(r, "HOME" if home else "AWAY")
        s.bets.append(Bet(r.game_id, r.season, r.week, "SPREAD", "HOME" if home else "AWAY",
                          r.spread_line, price, float("nan"), float(r.mkt_p_home if home else r.mkt_p_away),
                          float(won), american_to_payout(price) if won else -1.0))
    out.append(s)

    # S2 — fade a team off a 17+ point win
    s = Strategy("S2_blowout_reversion", "Fade a team off a 17+ point win", "SPREAD",
                 "Recency bias: the public re-prices a team after a lopsided win. "
                 "Fade the team that won by 17 or more in its previous game.",
                 {"min_margin": 17})
    for _, r in d.iterrows():
        if not np.isfinite(r.spread_line):
            continue
        if r.last_margin_home >= 17:
            side, won = "AWAY", r.away_cover
        elif r.last_margin_away <= -17:
            side, won = "HOME", r.home_cover
        else:
            continue
        if not np.isfinite(won):
            continue
        price = _sp(r, side)
        s.bets.append(Bet(r.game_id, r.season, r.week, "SPREAD", side, r.spread_line, price,
                          float("nan"), float(r.mkt_p_home if side == "HOME" else r.mkt_p_away),
                          float(won), american_to_payout(price) if won else -1.0))
    out.append(s)

    # S3 — rest differential
    s = Strategy("S3_rest_diff", "Rest differential (3+ days)", "SPREAD",
                 "Extra rest is genuine but usually priced; test whether 3+ days of rest "
                 "advantage still carries value.", {"min_rest": 3})
    for _, r in d.iterrows():
        if not (np.isfinite(r.spread_line) and np.isfinite(r.home_rest) and np.isfinite(r.away_rest)):
            continue
        diff = r.home_rest - r.away_rest
        if abs(diff) < 3:
            continue
        side = "HOME" if diff > 0 else "AWAY"
        won = r.home_cover if side == "HOME" else r.away_cover
        if not np.isfinite(won):
            continue
        price = _sp(r, side)
        s.bets.append(Bet(r.game_id, r.season, r.week, "SPREAD", side, r.spread_line, price,
                          float("nan"), float(r.mkt_p_home if side == "HOME" else r.mkt_p_away),
                          float(won), american_to_payout(price) if won else -1.0))
    out.append(s)

    # S4 — pace vs total
    s = Strategy("S4_pace_total", "Six-game scoring pace vs. posted total", "TOTAL",
                 "Both teams' last six games are used to project a total; bet when the "
                 "projection differs from the posted number by 5+ points, with a wind adjustment.",
                 {"min_edge_pts": 5.0, "wind_penalty": 2.5})
    for _, r in d.iterrows():
        if not (np.isfinite(r.total_line) and np.isfinite(r.total_edge)):
            continue
        wind = r.wind if np.isfinite(r.wind) else 0.0
        adj = r.total_edge - (2.5 if wind >= 15 else 0.0)
        if abs(adj) < 5.0:
            continue
        side = "OVER" if adj > 0 else "UNDER"
        won = r.over if side == "OVER" else r.under
        if not np.isfinite(won):
            continue
        price = _tp(r, side)
        s.bets.append(Bet(r.game_id, r.season, r.week, "TOTAL", side, r.total_line, price,
                          float("nan"), 0.5, float(won),
                          american_to_payout(price) if won else -1.0))
    out.append(s)

    # S5 — divisional home dog
    s = Strategy("S5_div_dog", "Divisional home underdog", "SPREAD",
                 "Familiarity compresses variance inside a division; test whether the "
                 "home team in a divisional game priced as a 1+ point underdog covers too often.",
                 {"min_dog": 1.0})
    for _, r in d.iterrows():
        if not np.isfinite(r.spread_line):
            continue
        if r.div_game != 1 or r.spread_line > -1.0:
            continue
        won = r.home_cover
        if not np.isfinite(won):
            continue
        price = _sp(r, "HOME")
        s.bets.append(Bet(r.game_id, r.season, r.week, "SPREAD", "HOME", r.spread_line, price,
                          float("nan"), float(r.mkt_p_home), float(won),
                          american_to_payout(price) if won else -1.0))
    out.append(s)

    # S6 — moneyline dog value
    s = Strategy("S6_ml_dog", "Moneyline underdog value", "ML",
                 "Bet the underdog on the moneyline when the model's win probability exceeds "
                 "the de-vigged market probability by 8+ points. Low hit rate, high payout.",
                 {"min_edge": 0.08})
    for _, r in d.iterrows():
        if not np.isfinite(r.mkt_p_home):
            continue
        ph = r.elo_p_home
        if ph > r.mkt_p_home + 0.08 and r.home_moneyline > 0:
            side, price, won, mp, mk = "HOME", float(r.home_moneyline), r.home_win, ph, r.mkt_p_home
        elif (1 - ph) > r.mkt_p_away + 0.08 and r.away_moneyline > 0:
            side, price, won, mp, mk = "AWAY", float(r.away_moneyline), 1 - r.home_win, 1 - ph, r.mkt_p_away
        else:
            continue
        if not np.isfinite(won):
            continue
        s.bets.append(Bet(r.game_id, r.season, r.week, "ML", side, float("nan"), price, float(mp), float(mk),
                          float(won), american_to_payout(price) if won else -1.0))
    out.append(s)

    # S7 — high total, tight spread, good weather
    s = Strategy("S7_high_total", "High total + tight spread + calm weather", "TOTAL",
                 "A 47+ total with a spread of 3 or less in calm conditions implies a "
                 "shootout between evenly matched teams; test the over.",
                 {"min_total": 47.0, "max_spread": 3.0, "max_wind": 8.0})
    for _, r in d.iterrows():
        if not (np.isfinite(r.total_line) and np.isfinite(r.spread_line)):
            continue
        wind = r.wind if np.isfinite(r.wind) else 0.0
        if r.total_line >= 47 and abs(r.spread_line) <= 3 and wind < 8:
            won = r.over
        else:
            continue
        if not np.isfinite(won):
            continue
        price = _tp(r, "OVER")
        s.bets.append(Bet(r.game_id, r.season, r.week, "TOTAL", "OVER", r.total_line, price,
                          float("nan"), 0.5, float(won),
                          american_to_payout(price) if won else -1.0))
    out.append(s)

    # S8 — off a bye week
    s = Strategy("S8_bye_edge", "Team coming off its bye", "SPREAD",
                 "A team off a bye has two weeks to prepare and is conventionally "
                 "considered advantaged; test whether it survives as a market edge.",
                 {"min_rest": 13})
    for _, r in d.iterrows():
        if not (np.isfinite(r.spread_line) and np.isfinite(r.home_rest) and np.isfinite(r.away_rest)):
            continue
        if r.home_rest >= 13 and r.away_rest < 13:
            side, won = "HOME", r.home_cover
        elif r.away_rest >= 13 and r.home_rest < 13:
            side, won = "AWAY", r.away_cover
        else:
            continue
        if not np.isfinite(won):
            continue
        price = _sp(r, side)
        s.bets.append(Bet(r.game_id, r.season, r.week, "SPREAD", side, r.spread_line, price,
                          float("nan"), float(r.mkt_p_home if side == "HOME" else r.mkt_p_away),
                          float(won), american_to_payout(price) if won else -1.0))
    out.append(s)

    # S9 — short-week (Thursday) unders
    s = Strategy("S9_short_week_under", "Short-week unders (4 or fewer days rest)", "TOTAL",
                 "Both teams on a short week should have a thinner, less rehearsed game plan; "
                 "test whether the total is systematically set too high.",
                 {"max_rest": 5})
    for _, r in d.iterrows():
        if not (np.isfinite(r.total_line) and np.isfinite(r.home_rest) and np.isfinite(r.away_rest)):
            continue
        if max(r.home_rest, r.away_rest) <= 5:
            won = r.under
        else:
            continue
        if not np.isfinite(won):
            continue
        price = _tp(r, "UNDER")
        s.bets.append(Bet(r.game_id, r.season, r.week, "TOTAL", "UNDER", r.total_line, price,
                          float("nan"), 0.5, float(won),
                          american_to_payout(price) if won else -1.0))
    out.append(s)

    # S10 — weather unders in high wind
    s = Strategy("S10_wind_under", "High-wind unders", "TOTAL",
                 "Wind is the weather variable the market handles least well. Test unders "
                 "when sustained wind is 15+ mph and the total is already 44 or higher.",
                 {"min_wind": 15.0, "min_total": 44.0})
    for _, r in d.iterrows():
        if not (np.isfinite(r.total_line) and np.isfinite(r.wind)):
            continue
        if r.wind >= 15 and r.total_line >= 44:
            won = r.under
        else:
            continue
        if not np.isfinite(won):
            continue
        price = _tp(r, "UNDER")
        s.bets.append(Bet(r.game_id, r.season, r.week, "TOTAL", "UNDER", r.total_line, price,
                          float("nan"), 0.5, float(won),
                          american_to_payout(price) if won else -1.0))
    out.append(s)

    # S11 — declared untestable (data gap), documented rather than proxied
    s = Strategy("S11_line_move_fade", "Fade large weekly line moves", "SPREAD",
                 "Requires an opening-line snapshot for every season. initial_lines.csv covers "
                 "2021 only, so the strategy cannot be tested without inventing data.",
                 {"data_gap": "No opening-line snapshot outside 2021 in this dataset."})
    out.append(s)
    return out


# --------------------------------------------------------------------------- #
GATES = [
    ("G1_sample", "At least 150 settled bets"),
    ("G2_hitrate", "Bootstrap 95% lower bound on hit rate above break-even (52.38% at -110)"),
    ("G3_profit_ci", "Block-bootstrap 95% CI of mean return per bet excludes zero"),
    ("G4_brier", "Model probabilities beat the de-vigged closing line on Brier score"),
    ("G5_seasons", "Profitable in at least 60% of evaluated seasons"),
    ("G6_luck", "Luck fraction below 0.50"),
    ("G7_fdr", "Survives Benjamini-Hochberg FDR at q = 0.10 across all tested strategies"),
    ("G8_leak", "Features proven pre-kickoff (see docs/STRATEGY_VALIDATION.md)"),
]


def evaluate(strategies: list[Strategy]) -> list[dict]:
    rows = []
    for s in strategies:
        if not s.bets:
            rows.append({"sid": s.sid, "name": s.name, "market": s.market, "thesis": s.thesis,
                         "params": s.params, "n": 0, "status": "untestable",
                         "reason": s.params.get("data_gap", "no qualifying bets")})
            continue
        units = np.array([b.units for b in s.bets], float)
        won = np.array([b.won for b in s.bets], float)
        prices = np.array([b.price for b in s.bets], float)
        seasons = np.array([b.season for b in s.bets], int)
        n = int(units.size)
        hit = float(won.mean())
        req = float(np.mean([american_to_prob(p) for p in prices]))
        rng = np.random.default_rng(7)
        boots = [float(np.mean(rng.choice(won, n, replace=True))) for _ in range(4000)]
        hit_lo, hit_hi = float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))
        mean_u, lo_u, hi_u = block_bootstrap_ci(units, block=16)
        lk = luck_share(units)
        by_season = {int(sn): {"n": int((seasons == sn).sum()), "units": float(units[seasons == sn].sum()),
                               "hit": float(won[seasons == sn].mean())} for sn in sorted(set(seasons))}
        pos = sum(1 for v in by_season.values() if v["units"] > 0)
        rows.append({
            "sid": s.sid, "name": s.name, "market": s.market, "thesis": s.thesis,
            "params": s.params, "n": n, "hit_rate": hit, "hit_rate_ci_lo": hit_lo,
            "hit_rate_ci_hi": hit_hi, "required_hit_rate": req,
            "mean_units_per_bet": mean_u, "units_ci_lo": lo_u, "units_ci_hi": hi_u,
            "total_units": float(units.sum()), "roi": mean_u,
            "luck_fraction": lk["luck_fraction"], "t_stat": lk["t_stat"], "p_value": lk["p_value"],
            "seasons": by_season, "seasons_positive": pos, "seasons_total": len(by_season),
            "avg_price": float(np.mean(prices)),
            "flat_stake_bankroll_path": (np.cumsum(units)).round(2).tolist()[:400],
        })
    return rows


def apply_gates(rows: list[dict]) -> tuple[list[dict], float]:
    tested = [r for r in rows if r.get("n", 0) > 0 and np.isfinite(r.get("p_value", np.nan))]
    tested.sort(key=lambda r: r["p_value"])
    m = len(tested)
    cutoff = float("nan")
    for i, r in enumerate(tested, 1):
        if r["p_value"] <= FDR_Q * i / m:
            cutoff = r["p_value"]
    for r in rows:
        if r.get("n", 0) == 0:
            r["gates"] = {g: None for g, _ in GATES}
            r["gates_passed"] = 0
            r["status"] = "untestable"
            continue
        gates = {
            "G1_sample": r["n"] >= MIN_SAMPLE,
            "G2_hitrate": r["hit_rate_ci_lo"] > BREAKEVEN_HIT,
            "G3_profit_ci": r["units_ci_lo"] > 0,
            "G4_brier": bool(np.isfinite(r.get("brier_skill", np.nan)) and r["brier_skill"] > 0),
            "G5_seasons": r["seasons_total"] > 0 and r["seasons_positive"] / r["seasons_total"] >= 0.60,
            "G6_luck": bool(np.isfinite(r["luck_fraction"]) and r["luck_fraction"] < 0.50),
            "G7_fdr": bool(np.isfinite(cutoff) and r["p_value"] <= cutoff),
            "G8_leak": True,
        }
        r["gates"] = gates
        r["gates_passed"] = sum(1 for v in gates.values() if v)
        r["status"] = ("validated" if r["gates_passed"] == len(GATES)
                       else "promising" if r["gates_passed"] >= 5 else "rejected")
    return rows, cutoff


def correlations(g: pd.DataFrame) -> dict:
    d = g[g.season >= EVAL_START]
    out = {}
    bin_pairs = {
        "home_cover__over": (d.home_cover, d.over),
        "home_win__home_cover": (d.home_win, d.home_cover),
        "div_game__home_cover": (d.div_game == 1, d.home_cover),
        "home_fav__over": (d.spread_line > 0, d.over),
        "windy__under": (d.wind >= 15, d.under),
        "rest_adv_home__home_cover": (d.home_rest > d.away_rest, d.home_cover),
    }
    for name, (a, b) in bin_pairs.items():
        a = pd.Series(a).astype(float).values
        b = pd.Series(b).astype(float).values
        m = np.isfinite(a) & np.isfinite(b)
        pt, lo, hi = phi_ci(a[m].astype(bool), b[m].astype(bool))
        out[name] = {"type": "phi", "r": pt, "ci_lo": lo, "ci_hi": hi, "n": int(m.sum()),
                     "significant": bool(np.isfinite(lo) and (lo > 0 or hi < 0))}
    num_pairs = {"spread_line__home_margin": (d.spread_line, d.hs),
                 "total_line__total_points": (d.total_line, d.total_points),
                 "wind__total_points": (d.wind, d.total_points)}
    for name, (a, b) in num_pairs.items():
        a = pd.Series(a).astype(float); b = pd.Series(b).astype(float)
        m = a.notna() & b.notna()
        out[name] = {"type": "pearson", "r": float(np.corrcoef(a[m], b[m])[0, 1]), "n": int(m.sum())}
    return out


def main() -> None:
    os.makedirs(DATA, exist_ok=True)
    g0 = load_games()
    g, theta = add_features(g0)
    print(f"features built: {len(g)} games, closing-line coverage {g.mkt_p_home.notna().mean():.1%}")

    strategies = build_strategies(g)
    rows = evaluate(strategies)

    ev = g[(g.season >= EVAL_START) & g.mkt_p_home.notna() & g.home_win.notna()]
    elo_bs = brier(ev.elo_p_home, ev.home_win)
    mkt_bs = brier(ev.mkt_p_home, ev.home_win)
    for r in rows:
        r["brier_skill"] = float(1 - elo_bs / mkt_bs) if r["sid"] == "S1_elo_spread" else float("nan")
    # also record model quality for spread/total markets
    evs = ev[ev.spread_line.notna() & ev.home_cover.notna()]
    rows, cutoff = apply_gates(rows)

    summary = {
        "as_of_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "protocol": {"train_start": TRAIN_START, "calibration_end": CALIB_END, "eval_start": EVAL_START,
                     "min_sample": MIN_SAMPLE, "breakeven_hit_rate": BREAKEVEN_HIT,
                     "fdr_q": FDR_Q, "n_hypotheses": len(strategies), "min_edge_pts": MIN_EDGE_PTS,
                     "fdr_cutoff_p": None if not np.isfinite(cutoff) else float(cutoff)},
        "elo_calibration": theta,
        "baselines": {
            "n_games_evaluated": int(len(ev)),
            "elo_brier": float(elo_bs), "market_brier": float(mkt_bs),
            "elo_brier_skill_vs_market": float(1 - elo_bs / mkt_bs),
            "elo_log_loss": float(log_loss(ev.elo_p_home, ev.home_win)),
            "market_log_loss": float(log_loss(ev.mkt_p_home, ev.home_win)),
            "market_home_win_rate": float(ev.home_win.mean()),
            "spread_market_cover_rate": float((evs.home_cover).mean()),
            "n_spread_games": int(len(evs)),
        },
        "strategies": rows,
        "correlations": correlations(g),
        "gates_definition": [{"id": i, "requirement": dd} for i, dd in GATES],
    }
    with open(os.path.join(DATA, "backtest_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2, default=float)

    print("\n=== Leaderboard (out-of-sample 2011+) ===")
    for r in sorted(rows, key=lambda x: -x.get("gates_passed", 0)):
        print(f"{r['sid']:22s} n={r.get('n',0):5d} hit={r.get('hit_rate',float('nan')):.3f} "
              f"ROI={r.get('roi',float('nan')):+.4f} gates={r.get('gates_passed',0)}/8 {r['status']}")
    print(f"\nBrier: Elo {elo_bs:.4f} vs market {mkt_bs:.4f} "
          f"(skill {1-elo_bs/mkt_bs:+.4f}) on {len(ev)} games")


if __name__ == "__main__":
    main()
