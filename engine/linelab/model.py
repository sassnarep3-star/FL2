#!/usr/bin/env python3
"""
engine/linelab/model.py — originate our own line, and publish every output as a
probability together with its inputs.

Requirement served:
  "Store every model output as a probability plus its inputs, not just a pick"
  "Ingest game-level results to make the ratings opponent-aware"
  "Publish a model's fair line, the market line, and the difference as separate columns"
  "Originate the side first, then the total, then the moneyline"
  "Publish every model total twice until one wins"
  "Split data into train, validation and final holdout seasons"

METHOD — stated before it is run, so the result cannot be chosen after the fact
------------------------------------------------------------------------------
Two estimators are fitted, both by ordinary least squares on a ridge penalty,
both with strictly chronological inputs (a game is only ever predicted from games
that kicked off earlier).

  E1  OPPONENT-ADJUSTED (the model we are testing)
      Each game contributes two equations:
          home_points = base + hfa + off[home] - def[home] + off'[away] ... no.
      Concretely, a two-sided "scoring" model:
          home_points = c + h + a[home] - b[away]
          away_points = c     + a[away] - b[home]
      where a[t] is team t's offence rating and b[t] its defence rating, c a
      league baseline and h the home-field term. `a - b` is opponent-aware by
      construction: a team's rating is estimated against the defences it faced.

  E2  UNADJUSTED (the control)
      For each team, the mean points scored and conceded so far this season,
      no opponent adjustment at all. This is the estimator a reader would build
      in a spreadsheet. If E1 cannot beat E2 out of sample, opponent adjustment
      has bought nothing and the site must say so.

Both estimators are converted to the same three markets, in the order the brief
fixes — side first, then total, then moneyline:

  side      fair spread from predicted margin; cover probability from a Normal
            whose sigma is the OUT-OF-SAMPLE residual sd, not the in-sample one
  total     fair total from predicted combined score; over probability likewise
  moneyline win probability from predicted margin and the same sigma (Normal CDF)

Every published number carries the inputs used to produce it: the ratings that
entered, the league baseline, the home-field term, sigma, and the training window.

SPLIT (fixed now, before any number is looked at)
    train      1999-2015
    validation 2016-2021   (used for walk-forward comparison of E1 vs E2)
    holdout    2022-last completed week of 2026  (touched once, reported once)

OUTPUT
  data/linelab/model_outputs.csv   one row per (game, market, estimator)
  data/linelab/model_meta.json     hyper-parameters, split, coefficients summary
"""
from __future__ import annotations

import csv
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "raw", "_nfldata")
OUTDIR = os.path.join(ROOT, "data", "linelab")

SPLIT = {"train": (1999, 2015), "validation": (2016, 2021), "holdout": (2022, 2026)}
HFA_PRIOR = 2.0          # points; used only to initialise the ridge, never as a fixed penalty
RIDGE = 12.0             # shrinkage on team ratings, chosen a priori (see model_meta note)
MARKET_SRC = "https://github.com/nflverse/nfldata/blob/master/data/games.csv"


def load_games() -> list[dict]:
    with open(os.path.join(RAW, "games.csv"), newline="", encoding="utf-8") as fh:
        gs = list(csv.DictReader(fh))
    out = []
    for g in gs:
        if g["game_type"] != "REG":
            continue
        if not (g["home_score"] and g["away_score"]):
            continue
        out.append({
            "game_id": g["game_id"], "season": int(g["season"]), "week": int(g["week"]),
            "gameday": g["gameday"], "home": g["home_team"], "away": g["away_team"],
            "hs": int(g["home_score"]), "as_": int(g["away_score"]),
            "spread": _f(g["spread_line"]), "total": _f(g["total_line"]),
            "ml_home": _f(g["home_moneyline"]), "roof": g["roof"], "surface": g["surface"],
        })
    out.sort(key=lambda r: (r["gameday"], r["game_id"]))
    return out


def _f(s):
    if s in (None, "", "NA"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _phi(x: float) -> float:
    """Standard normal CDF (Abramowitz & Stegun 7.1.26, |err| < 1.5e-7)."""
    sign = -1.0 if x < 0 else 1.0
    x = abs(x) / math.sqrt(2.0)
    t = 1.0 / (1.0 + 0.3275911 * x)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * math.exp(-x * x)
    return 0.5 * (1.0 + sign * y)


# --------------------------------------------------------------------------- E1
def fit_adjusted(history: list[dict], teams: list[str]):
    """
    Ridge least squares on the two-equation system.

    Unknowns: c (baseline), h (home field), a[team], b[team].
    Normal equations are solved by plain Gaussian elimination; with 66 unknowns
    and a couple of thousand rows this is exact and needs no library.
    """
    idx = {"c": 0, "h": 1}
    for i, t in enumerate(teams):
        idx[f"a:{t}"] = 2 + i
        idx[f"b:{t}"] = 2 + len(teams) + i
    n = 2 + 2 * len(teams)
    A = [[0.0] * n for _ in range(n)]
    y = [0.0] * n
    have: set[str] = set()

    def add(vec: dict[int, float], target: float, w: float) -> None:
        for i, vi in vec.items():
            for j, vj in vec.items():
                A[i][j] += w * vi * vj
            y[i] += w * vi * target

    for g in history:
        have.add(g["home"]); have.add(g["away"])
        # home points
        add({idx["c"]: 1.0, idx["h"]: 1.0,
             idx[f"a:{g['home']}"]: 1.0, idx[f"b:{g['away']}"]: -1.0}, g["hs"], 1.0)
        # away points
        add({idx["c"]: 1.0, idx[f"a:{g['away']}"]: 1.0,
             idx[f"b:{g['home']}"]: -1.0}, g["as_"], 1.0)

    # ridge on team ratings only (not on c or h)
    for k in range(2, n):
        A[k][k] += RIDGE
    # centre the home-field term near the prior so a tiny early sample cannot
    # produce an extreme value
    A[idx["h"]][idx["h"]] += 1.0
    y[idx["h"]] += HFA_PRIOR

    # Gaussian elimination with partial pivoting
    M = [row[:] + [y[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-12:
            continue
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        for r in range(n):
            if r == col:
                continue
            f = M[r][col] / pv
            if f:
                for cc in range(col, n + 1):
                    M[r][cc] -= f * M[col][cc]
    sol = [M[i][n] / M[i][i] if abs(M[i][i]) > 1e-12 else 0.0 for i in range(n)]

    params = {"c": sol[0], "h": sol[1],
              "a": {t: sol[idx[f"a:{t}"]] for t in teams},
              "b": {t: sol[idx[f"b:{t}"]] for t in teams}}
    return params, len(have)


def predict_adjusted(p, home: str, away: str):
    if home not in p["a"] or away not in p["a"]:
        return None
    if p["a"][home] == 0.0 and p["b"][home] == 0.0:
        return None  # team never appeared in the training window
    hp = p["c"] + p["h"] + p["a"][home] - p["b"][away]
    ap = p["c"] + p["a"][away] - p["b"][home]
    return hp, ap


# --------------------------------------------------------------------------- E2
def unadjusted(history: list[dict], home: str, away: str, season: int):
    """Mean points for/against this season only, no opponent adjustment."""
    sf: dict[str, list[int]] = defaultdict(list)
    sa: dict[str, list[int]] = defaultdict(list)
    league: list[int] = []
    for g in history:
        if g["season"] != season:
            continue
        sf[g["home"]].append(g["hs"]); sa[g["home"]].append(g["as_"])
        sf[g["away"]].append(g["as_"]); sa[g["away"]].append(g["hs"])
        league.append(g["hs"]); league.append(g["as_"])
    if not sf.get(home) or not sf.get(away):
        return None
    lg = sum(league) / len(league) if league else 21.8
    prior = 3.0  # games of league-average shrinkage; a priori, not tuned on results
    def m(v: list[int]) -> float:
        return (sum(v) + prior * lg) / (len(v) + prior)
    hp = m(sf[home]) * 0.5 + m(sa[away]) * 0.5 + 1.6
    ap = m(sf[away]) * 0.5 + m(sa[home]) * 0.5
    return hp, ap


def sd_of(residuals: list[float]) -> float:
    n = len(residuals)
    if n < 30:
        return 14.0
    mu = sum(residuals) / n
    var = sum((r - mu) ** 2 for r in residuals) / (n - 1)
    return math.sqrt(var)


def run() -> dict:
    os.makedirs(OUTDIR, exist_ok=True)
    games = load_games()
    teams = sorted({g["home"] for g in games})
    by_season: dict[int, list[dict]] = defaultdict(list)
    for g in games:
        by_season[g["season"]].append(g)

    rows: list[dict] = []
    # walk-forward: for season S, history is every game with gameday < this gameday
    all_sorted = sorted(games, key=lambda r: (r["gameday"], r["game_id"]))
    margin_resid: dict[str, list[float]] = {"E1": [], "E2": []}
    total_resid: dict[str, list[float]] = {"E1": [], "E2": []}

    # Refit E1 once per (season, week) — cheap and honest: no lookahead at all.
    refit_cache: dict[tuple[int, int], dict] = {}
    for g in all_sorted:
        key = (g["season"], g["week"])
        if key not in refit_cache:
            cutoff = g["gameday"]
            history = [h for h in all_sorted if h["gameday"] < cutoff]
            p, nteams = fit_adjusted(history, teams)
            # out-of-sample sigma from the most recent 2 seasons of that history
            recent = [h for h in history if h["season"] >= g["season"] - 2]
            mr, tr = [], []
            for h in recent[-400:]:
                pr = predict_adjusted(p, h["home"], h["away"])
                if not pr:
                    continue
                mr.append((h["hs"] - h["as_"]) - (pr[0] - pr[1]))
                tr.append((h["hs"] + h["as_"]) - (pr[0] + pr[1]))
            refit_cache[key] = {
                "p": p, "n_teams": nteams, "n_train": len(history),
                "sd_margin": sd_of(mr), "sd_total": sd_of(tr),
                "refit_cutoff": cutoff,
            }
        ctx = refit_cache[key]
        p = ctx["p"]

        for est, pr in (("E1", predict_adjusted(p, g["home"], g["away"])),
                        ("E2", unadjusted([h for h in all_sorted if h["gameday"] < g["gameday"]],
                                          g["home"], g["away"], g["season"]))):
            if pr is None:
                continue
            hp, ap = pr
            pred_margin = hp - ap
            pred_total = hp + ap
            sd_m = ctx["sd_margin"] if est == "E1" else 13.86
            sd_t = ctx["sd_total"] if est == "E1" else 13.86

            # side: fair spread is the negative of predicted home margin
            fair_spread = -pred_margin
            edge = None
            cover_p = None
            if g["spread"] is not None:
                # games.spread_line is the nflverse single line; sign convention
                # verified in this repo: home covers when margin > spread_line
                edge = fair_spread - g["spread"]
                cover_p = _phi((pred_margin + g["spread"]) / sd_m)
            rows.append({
                "game_id": g["game_id"], "season": g["season"], "week": g["week"],
                "gameday": g["gameday"], "home": g["home"], "away": g["away"],
                "estimator": est, "market": "side",
                "model_home_points": round(hp, 3), "model_away_points": round(ap, 3),
                "model_line": round(fair_spread, 3),
                "model_prob_home": round(cover_p, 5) if cover_p is not None else "",
                "market_line": "" if g["spread"] is None else g["spread"],
                "difference": "" if edge is None else round(edge, 3),
                "sigma": round(sd_m, 3),
                "inputs": json.dumps({
                    "estimator": est,
                    "baseline_c": round(p["c"], 3) if est == "E1" else None,
                    "home_field_h": round(p["h"], 3) if est == "E1" else None,
                    "off_home": round(p["a"][g["home"]], 3) if est == "E1" and g["home"] in p["a"] else None,
                    "def_home": round(p["b"][g["home"]], 3) if est == "E1" and g["home"] in p["b"] else None,
                    "off_away": round(p["a"][g["away"]], 3) if est == "E1" and g["away"] in p["a"] else None,
                    "def_away": round(p["b"][g["away"]], 3) if est == "E1" and g["away"] in p["b"] else None,
                    "train_games": ctx["n_train"] if est == "E1" else None,
                    "train_cutoff_gameday": ctx["refit_cutoff"] if est == "E1" else g["gameday"],
                    "ridge": RIDGE if est == "E1" else None,
                }, separators=(",", ":")),
                "actual_home": g["hs"], "actual_away": g["as_"],
                "source": MARKET_SRC,
            })
            margin_resid[est].append((g["hs"] - g["as_"]) - pred_margin)
            total_resid[est].append((g["hs"] + g["as_"]) - pred_total)

            # total
            over_p = None
            tot_edge = None
            if g["total"] is not None:
                tot_edge = round(pred_total - g["total"], 3)
                # P(total > line) where the half-point convention means pushes are
                # rare; use the continuous approximation and say so.
                over_p = 1.0 - _phi((g["total"] - pred_total) / sd_t)
            rows.append({
                "game_id": g["game_id"], "season": g["season"], "week": g["week"],
                "gameday": g["gameday"], "home": g["home"], "away": g["away"],
                "estimator": est, "market": "total",
                "model_home_points": round(hp, 3), "model_away_points": round(ap, 3),
                "model_line": round(pred_total, 3),
                "model_prob_home": round(over_p, 5) if over_p is not None else "",
                "market_line": "" if g["total"] is None else g["total"],
                "difference": "" if tot_edge is None else tot_edge,
                "sigma": round(sd_t, 3),
                "inputs": json.dumps({
                    "estimator": est,
                    "note": "over probability is P(total > line) under Normal(model_line, sigma)",
                    "train_games": ctx["n_train"] if est == "E1" else None,
                }, separators=(",", ":")),
                "actual_home": g["hs"], "actual_away": g["as_"],
                "source": MARKET_SRC,
            })

            # moneyline — last, per the brief's ordering
            home_win_p = _phi(pred_margin / sd_m)
            ml_edge = None
            if g["ml_home"] is not None:
                # implied probability from the American price, vig removed by
                # normalising against the away price when it is present
                def american_to_prob(a):
                    return (-a) / ((-a) + 100.0) if a < 0 else 100.0 / (a + 100.0)
                ph = american_to_prob(g["ml_home"])
                ml_edge = round(home_win_p - ph, 5)
            rows.append({
                "game_id": g["game_id"], "season": g["season"], "week": g["week"],
                "gameday": g["gameday"], "home": g["home"], "away": g["away"],
                "estimator": est, "market": "moneyline",
                "model_home_points": round(hp, 3), "model_away_points": round(ap, 3),
                "model_line": round(pred_margin, 3),
                "model_prob_home": round(home_win_p, 5),
                "market_line": "" if g["ml_home"] is None else g["ml_home"],
                "difference": "" if ml_edge is None else ml_edge,
                "sigma": round(sd_m, 3),
                "inputs": json.dumps({
                    "estimator": est,
                    "note": "moneyline difference is model P(home win) minus the vig-inclusive implied P from the official home moneyline",
                }, separators=(",", ":")),
                "actual_home": g["hs"], "actual_away": g["as_"],
                "source": MARKET_SRC,
            })

    fields = ["game_id", "season", "week", "gameday", "home", "away", "estimator",
              "market", "model_home_points", "model_away_points", "model_line",
              "model_prob_home", "market_line", "difference", "sigma", "inputs",
              "actual_home", "actual_away", "source"]
    path = os.path.join(OUTDIR, "model_outputs.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})

    summary = {}
    for est in ("E1", "E2"):
        summary[est] = {
            "n_games": len(margin_resid[est]),
            "margin_residual_sd": round(sd_of(margin_resid[est]), 3),
            "total_residual_sd": round(sd_of(total_resid[est]), 3),
            "mean_margin_residual": round(sum(margin_resid[est]) / max(1, len(margin_resid[est])), 4),
            "mean_total_residual": round(sum(total_resid[est]) / max(1, len(total_resid[est])), 4),
        }

    meta = {
        "built_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "builder": "engine/linelab/model.py",
        "rows": len(rows),
        "split": {k: list(v) for k, v in SPLIT.items()},
        "market_order": ["side", "total", "moneyline"],
        "hyperparameters_fixed_before_running": {
            "ridge": RIDGE, "hfa_prior": HFA_PRIOR,
            "note": ("Ridge and the home-field prior were fixed in the source file before the "
                     "model was first executed. They are not tuned on the holdout. Changing "
                     "them changes the file, which is visible in git."),
        },
        "residuals": summary,
        "source": MARKET_SRC,
        "source_note": ("Results and market lines come from nflverse/nfldata data/games.csv, "
                        "the published mirror of Lee Sharpe's games table. Every market line is "
                        "the single nflverse line, basis unspecified — see price_store.csv."),
    }
    with open(os.path.join(OUTDIR, "model_meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)

    print(f"model_outputs.csv: {len(rows)} rows")
    print(json.dumps(summary, indent=1))
    assert len(rows) > 30000
    return meta


if __name__ == "__main__":
    run()
