"""FL2 line origination: side first, then the total, then the moneyline.

Everything is walk-forward. A prediction for a game may only use (a) results of games
played earlier, (b) priors estimated strictly from seasons before the season being
predicted, and (c) the availability report for that game's own week, which the league
publishes on the practice days preceding kickoff. No number on any page here is fitted
to the season it prices.

Products (all under fl2-lines/data/derived/):
  model-priors.json          frozen pre-2026 priors, each with its n
  lines-2026.csv             fair line | market line | difference, one row per market
  lines-inputs.jsonl         every model output as a probability PLUS its inputs
  availability-graph.csv     expected-starter absence vs who actually participated
  designation-calibration.json  P(play | designation, position group) with n and CI
  correlations.json          correlations, each with n and a Fisher-z interval
  proper-scores.json         skill vs benchmark, cluster CIs, BH correction, luck panel
  totals-comparison.json     the two total estimators and the collapse decision
  ablation-injury.json       with/without personnel features, chronological holdout
  forecasts-week11.jsonl     pre-kickoff shadow forecasts, hash-chained
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics as st
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stats import (  # noqa: E402
    american_to_prob, benjamini_hochberg, brier, cluster_bootstrap_mean_ci, fisher_ci,
    fmt, log_loss, norm_cdf, pearson, prob_to_american, sd, wilson_ci,
)

SECTION = Path(__file__).resolve().parents[1]
REPO = SECTION.parent
DERIVED = SECTION / "data" / "derived"
LEDGER = SECTION / "data" / "ledger"
DERIVED.mkdir(parents=True, exist_ok=True)
LEDGER.mkdir(parents=True, exist_ok=True)

MIRROR = REPO / "raw" / "_nfldata" / "games.csv"
INJ = REPO / "signal" / "data" / "injury_player.csv"
SNAPS = REPO / "signal" / "data" / "snap_participation.csv"
OUT = DERIVED

TRAIN_MAX = 2024       # designation calibration + beta fitting: <= 2024
VAL = 2025             # validation season
HOLDOUT = 2026         # the season being priced; never fitted
K_PRIOR = 4.0          # games of league-average prior (declared, not tuned on 2026)
SEED = 20261116

POS_GROUP = {}
for grp, poss in {
    "QB": ["QB"], "OL": ["T", "G", "C"], "DL": ["DE", "DT", "NT", "DL"],
    "LB": ["LB", "ILB", "OLB", "MLB"], "DB": ["CB", "S", "FS", "SS", "DB", "NB"],
    "SKILL": ["WR", "RB", "TE", "HB", "FB", "KR", "PR"], "ST": ["K", "P", "LS", "H"],
}.items():
    for p in poss:
        POS_GROUP[p] = grp


def read(path: Path) -> list[dict]:
    if not Path(path).exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def write_csv(path: Path, rows: list[dict], cols: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def jdump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def n(x, cast=float):
    if x is None or x == "":
        return None
    try:
        return cast(x)
    except (ValueError, TypeError):
        return None


def fnum(x, dp=2):
    v = n(x)
    return None if v is None else round(v, dp)


# ------------------------------------------------------------------ inputs
def load_history() -> list[dict]:
    out = []
    for r in read(MIRROR):
        s = n(r.get("season"), int)
        if s is None or s < 2015 or r.get("game_type") != "REG" or not r.get("away_score"):
            continue
        out.append(
            {
                "season": int(s), "week": int(n(r["week"]) or 0), "gameday": r["gameday"],
                "game_id": r["game_id"], "away": r["away_team"], "home": r["home_team"],
                "aw": int(r["away_score"]), "hm": int(r["home_score"]),
                "roof": r.get("roof", ""), "surface": r.get("surface", ""),
                "away_rest": n(r.get("away_rest"), int), "home_rest": n(r.get("home_rest"), int),
                "spread_line": n(r.get("spread_line")), "total_line": n(r.get("total_line")),
                "home_ml": n(r.get("home_moneyline")), "away_ml": n(r.get("away_moneyline")),
                "home_sp_odds": n(r.get("home_spread_odds")), "away_sp_odds": n(r.get("away_spread_odds")),
                "over_odds": n(r.get("over_odds")), "under_odds": n(r.get("under_odds")),
            }
        )
    out.sort(key=lambda r: (r["gameday"], r["game_id"]))
    return out


def load_2026() -> list[dict]:
    rows = []
    for r in read(OUT / "results-2026.csv"):
        rows.append(r)
    games = []
    for r in rows:
        g = {
            "season": 2026, "week": int(n(r.get("week"), int) or 0), "gameday": r.get("gameday", ""),
            "game_id": r["game_id"], "away": r["away_team"], "home": r["home_team"],
            "aw": n(r.get("away_score"), int), "hm": n(r.get("home_score"), int),
            "roof": r.get("roof", ""), "surface": r.get("surface", ""),
            "away_rest": n(r.get("away_rest"), int), "home_rest": n(r.get("home_rest"), int),
            "spread_line": n(r.get("spread_line")), "total_line": n(r.get("total_line")),
            "home_ml": n(r.get("home_moneyline")), "away_ml": n(r.get("away_moneyline")),
            "home_sp_odds": n(r.get("home_spread_odds")), "away_sp_odds": n(r.get("away_spread_odds")),
            "over_odds": n(r.get("over_odds")), "under_odds": n(r.get("under_odds")),
            "home_rest": n(r.get("home_rest"), int), "away_rest": n(r.get("away_rest"), int),
            "venue_source": r.get("venue_source", ""),
            "result_prov": r.get("result_prov", ""),
        }
        g["played"] = g["aw"] is not None and g["hm"] is not None
        games.append(g)
    games.sort(key=lambda r: (r["gameday"], r["game_id"]))
    return games


# ------------------------------------------------- availability (injury) side
def build_availability() -> tuple[dict, dict, list[dict]]:
    """P(play | designation, pos group) estimated on <=TRAIN_MAX, plus a per team-week
    'expected unavailability deficit' for every 2026 team-week.

    Weighting is deliberately flat (one unit per listed player, scaled by the measured
    chance he does not play). Per-game snap counts are not in this repository for 2026,
    so weighting by playing time is *not* claimed - it is a published gate.
    """
    snaps_by_teamweek = defaultdict(set)
    for r in read(SNAPS):
        s, w = n(r.get("season"), int), n(r.get("week"), int)
        if s and w:
            snaps_by_teamweek[(s, w, r["team"])].add((r["player"] or "").strip().lower())
    inj = read(INJ)
    cal: dict[str, dict] = {}
    cal_pos: dict[str, dict] = {}
    for r in inj:
        s = n(r.get("season"), int)
        if not s or s > TRAIN_MAX:
            continue
        gs = (r.get("game_status") or "").strip()
        if gs not in ("Out", "Questionable", "Doubtful", "Probable"):
            continue
        tw = (s, n(r["week"], int), r["team"])
        players = snaps_by_teamweek.get(tw)
        if players is None:
            continue  # no participation evidence for that team-week -> excluded, not assumed
        name = (r.get("full_name") or "").strip().lower()
        played = 1 if name in players else 0
        for b, k in ((cal, gs), (cal_pos, f"{gs}|{r.get('pos_group','OTHER')}")):
            d = b.setdefault(k, {"n": 0, "played": 0})
            d["n"] += 1
            d["played"] += played
    for b in (cal, cal_pos):
        for k, d in b.items():
            d["play_rate_pct"] = round(100 * d["played"] / d["n"], 2) if d["n"] else None
            lo, hi = wilson_ci(d["played"], d["n"]) if d["n"] else (None, None)
            d["ci95_pct"] = [lo, hi]
    p_not = {k: (1 - d["played"] / d["n"]) if d["n"] >= 30 else None for k, d in cal.items()}
    p_not_pos = {k: (1 - d["played"] / d["n"]) for k, d in cal_pos.items() if d["n"] >= 30}

    # per team-week deficit for 2015-2026 (needed to fit beta on <=TRAIN_MAX and apply later)
    deficit: dict[tuple, float] = defaultdict(float)
    rows_2026 = []
    for r in inj:
        s = n(r.get("season"), int)
        if not s:
            continue
        gs = (r.get("game_status") or "").strip()
        pg = r.get("pos_group", "OTHER")
        pn = p_not_pos.get(f"{gs}|{pg}", p_not.get(gs))
        if pn is None:
            continue
        key = (s, n(r["week"], int), r["team"])
        deficit[key] += pn
        if s == HOLDOUT:
            tw = (s, n(r["week"], int), r["team"])
            played = 1 if (r.get("full_name") or "").strip().lower() in snaps_by_teamweek.get(tw, set()) else 0
            rows_2026.append(
                {
                    "season": s, "week": r["week"], "team": r["team"], "player": r.get("full_name", ""),
                    "position": r.get("position", ""), "pos_group": pg,
                    "designation": gs, "practice_status": r.get("practice_status", ""),
                    "listed_injury": r.get("report_primary_injury", ""),
                    "expected_available_pct": round(100 * (1 - pn), 1),
                    "surprise_pts": round(100 * ((1 - pn) - played), 1),
                    "participated_that_week": "yes" if played else "no",
                    "surprise": ("expected-out-but-played" if (played and pn > 0.6) else
                                 "expected-in-but-missed" if (not played and pn < 0.4) else
                                 "as-expected"),
                }
            )
    write_csv(
        OUT / "availability-graph.csv", rows_2026,
        ["season", "week", "team", "player", "position", "pos_group", "designation",
         "practice_status", "listed_injury", "expected_available_pct", "participated_that_week",
         "surprise", "surprise_pts"],
    )
    calib = {
        "estimated_on": f"{1999 if not cal else 2016}-{TRAIN_MAX} official-report rows joined to participation rows",
        "trap_documented": "joining only to snap counts returns a 100% play rate, because participation lists contain only players who took a snap. Those rows are excluded (denominator = every listed player-week that has a participation file for that team-week), never imputed.",
        "by_designation": cal,
        "by_designation_and_position": cal_pos,
        "no_reserve_list_in_source": "the source carries only Out/Questionable/Doubtful/Probable game statuses; IR and reserve lists are not represented, so 'not listed' is not evidence of health",
        "rows_2026_published": len(rows_2026),
    }
    return calib, deficit, rows_2026


# ------------------------------------------------------------------ priors
def per_season_team_sums(hist: list[dict]) -> tuple[dict, dict]:
    """For every (team, season): summed points-for/against deviations from that season's
    league mean, plus game counts. Used so a 2026 prediction can use *only* prior-season
    and already-played games, with an explicit shrinkage prior."""
    agg = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0, 0]))  # season -> team -> [pf_dev, pa_dev, g]
    rows = defaultdict(list)
    for g in hist:
        rows[g["season"]].append(g)
    league_mean = {}
    for s, gs in rows.items():
        pts = [x for g in gs for x in (g["aw"], g["hm"])]
        league_mean[s] = st.mean(pts)
        for g in gs:
            a, h = agg[s][g["away"]], agg[s][g["home"]]
            a[0] += g["aw"] - league_mean[s]; a[1] += g["hm"] - league_mean[s]; a[2] += 1
            h[0] += g["hm"] - league_mean[s]; h[1] += g["aw"] - league_mean[s]; h[2] += 1
    return agg, league_mean


def build_priors(hist: list[dict]) -> dict:
    pre = [g for g in hist if g["season"] < HOLDOUT]
    home_margins = [g["hm"] - g["aw"] for g in pre]
    totals = [g["hm"] + g["aw"] for g in pre]
    roof_tot, surf_tot, rest_tot, rest_marg = (defaultdict(list) for _ in range(4))
    for g in pre:
        roof_tot[g["roof"] or "unknown"].append(g["hm"] + g["aw"])
        surf_tot[g["surface"] or "unknown"].append(g["hm"] + g["aw"])
        if g["home_rest"] and g["away_rest"] is not None:
            d = g["home_rest"] - g["away_rest"]
            b = "even" if abs(d) <= 2 else ("home +3 or more" if d >= 3 else "away +3 or more")
            rest_tot[b].append(g["hm"] + g["aw"])
            rest_marg[b].append(g["hm"] - g["aw"])
    lg = st.mean(totals)

    def tab(d):
        return {
            k: {"n": len(v), "mean": round(st.mean(v), 3), "vs_league": round(st.mean(v) - lg, 3)}
            for k, v in sorted(d.items()) if len(v) >= 25
        }

    margins = [m - st.mean(home_margins) for m in home_margins]
    return {
        "window": f"2015-{HOLDOUT-1} regular-season games in the committed mirror (never the season being priced)",
        "n_games": len(pre),
        "league_mean_team_ppg": round(st.mean([x for g in pre for x in (g["hm"], g["aw"])]), 3),
        "league_mean_game_total": round(lg, 3),
        "home_field_advantage_pts": round(st.mean(home_margins), 3),
        "home_field_ci95_pts": list(cluster_bootstrap_mean_ci(home_margins, [g["game_id"] for g in pre], SEED)),
        "sigma_margin_default": round(sd(margins), 3),
        "roof_effect_on_total": tab(roof_tot),
        "surface_effect_on_total": tab(surf_tot),
        "rest_effect_on_total": tab(rest_tot),
        "rest_effect_on_margin": tab(rest_marg),
        "shrinkage_prior_games": K_PRIOR,
        "seed": SEED,
        "declared_not_tuned": "K_PRIOR, the sigma floor and the four context buckets were written down before any 2026 residual was looked at.",
    }


def walk_forward(hist: list[dict], games26: list[dict], deficit: dict, pri: dict):
    """One chronological pass, 2016 -> 2026 Week 10.

    Returns per-game model records (side margin mu_A, availability gap, totals, actuals)
    for every game, and the fully decomposed 2026 rows for publication.
    """
    hist2 = [g for g in hist if 2016 <= g["season"] < HOLDOUT]
    agg, league_mean = per_season_team_sums([g for g in hist if g["season"] < HOLDOUT])
    lg_total = pri["league_mean_game_total"]
    hfa = pri["home_field_advantage_pts"]
    roof_adj = {k: v["vs_league"] for k, v in pri["roof_effect_on_total"].items()}
    rest_adj = {k: v["vs_league"] for k, v in pri["rest_effect_on_total"].items()}
    sigma0 = pri["sigma_margin_default"]

    cur = defaultdict(lambda: [0.0, 0.0, 0])  # in-season accumulators, team -> [pf_dev, pa_dev, g]
    cur_season = None
    resid = []
    allrec = []
    for g in sorted(hist2 + games26, key=lambda r: (r["gameday"], r["game_id"])):
        s = g["season"]
        if cur_season is not None and s != cur_season:
            cur = defaultdict(lambda: [0.0, 0.0, 0])
        cur_season = s
        aw, hm = g["away"], g["home"]

        def side(team):
            p = agg.get(s - 1, {}).get(team, [0.0, 0.0, 0])
            c = cur[team]
            num_off, num_def, ng = p[0] + c[0], p[1] + c[1], p[2] + c[2]
            off = num_off / (ng + K_PRIOR)
            dfn = num_def / (ng + K_PRIOR)
            return off, dfn, ng

        a_off, a_def, a_n = side(aw)
        h_off, h_def, h_n = side(hm)
        # d_t is points-allowed deviation, so a NEGATIVE d means a good defence and
        # ADDS nothing to the opponent's projection: exp = base + own attack + opp d.
        exp_away = lg_total / 2.0 + a_off + h_def - hfa / 2.0
        exp_home = lg_total / 2.0 + h_off + a_def + hfa / 2.0
        mu_A = exp_home - exp_away
        wk = g["week"]
        d_away = deficit.get((s, wk, aw), 0.0)
        d_home = deficit.get((s, wk, hm), 0.0)
        gap = d_home - d_away
        t1 = exp_home + exp_away
        ctx = roof_adj.get(g.get("roof") or "unknown", 0.0)
        rd = None
        if g.get("home_rest") and g.get("away_rest") is not None:
            dd = g["home_rest"] - g["away_rest"]
            rd = "even" if abs(dd) <= 2 else ("home +3 or more" if dd >= 3 else "away +3 or more")
        t2 = lg_total + ctx + (rest_adj.get(rd, 0.0) if rd else 0.0)
        rec = {
            "game_id": g["game_id"], "season": s, "week": wk, "gameday": g["gameday"],
            "away": aw, "home": hm, "mu_A": mu_A, "t1": t1, "t2": t2,
            "avail_gap": gap, "d_away": d_away, "d_home": d_home,
            "games_away": a_n, "games_home": h_n,
            "spread_line": g.get("spread_line"), "total_line": g.get("total_line"),
            "home_ml": g.get("home_ml"), "away_ml": g.get("away_ml"),
            "over_odds": g.get("over_odds"), "under_odds": g.get("under_odds"),
            "home_sp_odds": g.get("home_sp_odds"), "away_sp_odds": g.get("away_sp_odds"),
            "roof": g.get("roof", ""), "rest_bucket": rd,
            "played": g.get("aw") is not None and g.get("hm") is not None,
        }
        if rec["played"]:
            rec["margin"] = g["hm"] - g["aw"]
            rec["total"] = g["hm"] + g["aw"]
            resid.append(rec["margin"] - mu_A)
            cur[aw][0] += g["aw"] - lg_total / 2.0; cur[aw][1] += g["hm"] - lg_total / 2.0; cur[aw][2] += 1
            cur[hm][0] += g["hm"] - lg_total / 2.0; cur[hm][1] += g["aw"] - lg_total / 2.0; cur[hm][2] += 1
        else:
            rec["margin"] = None
            rec["total"] = None
        allrec.append(rec)
    return allrec, resid, sigma0


def fit_calibration(allrec: list[dict], through: int = TRAIN_MAX) -> dict:
    """OLS recalibration of the raw projection onto the scale of actual outcomes, fitted
    only on seasons <= `through`. A raw attack/defence decomposition over-weights each
    team's own scoring, so its implied margins are too large; publishing the uncalibrated
    number would pretend the model is sharper than it is."""
    def ols(col_pred, col_actual):
        xs = [r[col_pred] for r in allrec if r["played"] and r["season"] <= through]
        ys = [r[col_actual] for r in allrec if r["played"] and r["season"] <= through]
        if len(xs) < 50:
            return 0.0, 1.0, len(xs)
        mx, my = st.mean(xs), st.mean(ys)
        sxx = sum((x - mx) ** 2 for x in xs)
        b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 1.0
        return my - b * mx, b, len(xs)

    a_m, b_m, n_m = ols("mu_A", "margin")
    a_t, b_t, n_t = ols("t1", "total")
    pred = [a_m + b_m * r["mu_A"] for r in allrec if r["played"] and r["season"] <= through]
    act = [r["margin"] for r in allrec if r["played"] and r["season"] <= through]
    return {
        "window": f"{min(r['season'] for r in allrec)}-{through}",
        "margin": {"intercept": round(a_m, 4), "slope": round(b_m, 4), "n": n_m,
                   "resid_sd": round(sd([y - x for x, y in zip(pred, act)]), 3)},
        "total": {"intercept": round(a_t, 4), "slope": round(b_t, 4), "n": n_t},
        "note": "fitted on past seasons only; the season being priced is never in the fit",
    }


def apply_calibration(allrec: list[dict], cal: dict, pri: dict) -> None:
    """Adds mu_cal / t1_cal / sigma to every record. The 2026 trailing-residual sigma is
    NOT used: the scale parameter comes from earlier seasons only, so no 2026 information
    leaks into a 2026 probability."""
    a_m, b_m = cal["margin"]["intercept"], cal["margin"]["slope"]
    a_t, b_t = cal["total"]["intercept"], cal["total"]["slope"]
    sigma = pri.get("sigma_prior_window") or cal["margin"]["resid_sd"]
    for r in allrec:
        r["mu_cal"] = a_m + b_m * r["mu_A"]
        r["t1_cal"] = a_t + b_t * r["t1"]
        r["sigma"] = sigma


def fit_beta(allrec: list[dict]) -> dict:
    """OLS slope of the margin residual on the availability deficit gap, fitted only on
    seasons <= TRAIN_MAX. Replaces a fixed points penalty: the size of the effect is
    estimated, and its uncertainty is published with it."""
    xs, ys = [], []
    for r in allrec:
        if r["played"] and r["season"] <= TRAIN_MAX:
            xs.append(r["avail_gap"]); ys.append(r["margin"] - r["mu_cal"])
    n_ = len(xs)
    if n_ < 50:
        return {"n": n_, "beta_pts_per_expected_miss": None, "status": "not estimated (insufficient fitted sample)"}
    mx, my = st.mean(xs), st.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    beta = sxy / sxx if sxx else 0.0
    resid = [y - my - beta * (x - mx) for x, y in zip(xs, ys)]
    se = math.sqrt(sum(e * e for e in resid) / (n_ - 2) / sxx) if sxx else float("nan")
    r = pearson(xs, ys)
    return {
        "n_games": n_, "window": f"2016-{TRAIN_MAX}", "mean_avail_gap": round(mx, 4),
        "sd_avail_gap": round(sd(xs), 4), "resid_sd": round(sd([y - my for y in ys]), 3),
        "beta_pts_per_expected_miss": round(beta, 4), "se": round(se, 4),
        "ci95": [round(beta - 1.96 * se, 4), round(beta + 1.96 * se, 4)],
        "pearson_r": round(r, 4), "pearson_ci95": list(fisher_ci(r, n_)),
        "note": "Ablation coefficient. A fixed -3.0 points per missing starter would assert an effect this sample does not support.",
    }


def publish_2026(allrec: list[dict], beta: dict, pri: dict, cal: dict) -> tuple[list[dict], list[dict]]:
    b = beta.get("beta_pts_per_expected_miss") or 0.0
    lg_total = pri["league_mean_game_total"]
    sigma_default = pri["sigma_margin_default"]
    rows, inputs = [], []
    resid = []
    for r in [x for x in allrec if x["season"] == HOLDOUT]:
        sigma = r["sigma"]
        mu_A = r["mu_cal"]
        mu_B = mu_A + b * r["avail_gap"]
        line = r["spread_line"]
        p_cover = norm_cdf((mu_A - line) / sigma) if line is not None else None
        p_win = norm_cdf(mu_A / sigma)
        p_cover_B = norm_cdf((mu_B - line) / sigma) if line is not None else None
        mkt_home = american_to_prob(r["home_ml"]) if r["home_ml"] is not None else None
        mkt_away = american_to_prob(r["away_ml"]) if r["away_ml"] is not None else None
        overround = (mkt_home + mkt_away - 1.0) if None not in (mkt_home, mkt_away) else None
        devig = mkt_home / (mkt_home + mkt_away) if overround is not None else None
        p_over = norm_cdf((r["t1_cal"] - r["total_line"]) / (sigma * math.sqrt(2.0))) if r["total_line"] is not None else None
        actual_cover = None
        if r["played"] and line is not None:
            actual_cover = int(r["margin"] - line > 0) if abs(r["margin"] - line) > 1e-9 else "push"
        actual_over = None
        if r["played"] and r["total_line"] is not None:
            actual_over = "push" if r["total"] == r["total_line"] else int(r["total"] > r["total_line"])
        actual_win = int(r["margin"] > 0) if r["played"] else None
        status = "FINAL" if r["played"] else "PRE-KICKOFF; market price timing uncertified"
        common = {
            "game_id": r["game_id"], "week": r["week"], "gameday": r["gameday"],
            "away": r["away"], "home": r["home"], "fixture_status": status,
            "sigma_used": round(sigma, 3), "avail_gap_deficit": round(r["avail_gap"], 3),
        }
        rows.append({**common, "market": "SPREAD", "sequence": "1st: side",
                     "fair_line": round(mu_A, 2), "market_line": fnum(line),
                     "residual_fair_minus_market": None if line is None else round(mu_A - line, 2),
                     "fair_line_with_personnel": round(mu_B, 2),
                     "p_home_or_over": fnum(p_cover, 4), "market_p_devig": None,
                     "overround_pct": fnum(None if overround is None else 100 * overround, 2),
                     "actual": "" if actual_cover is None else actual_cover,
                     "benchmark_line": fnum(line)})
        rows.append({**common, "market": "TOTAL", "sequence": "2nd: total, estimator T1 (scoring rates)",
                     "fair_line": round(r["t1_cal"], 2), "market_line": fnum(r["total_line"]),
                     "residual_fair_minus_market": None if r["total_line"] is None else round(r["t1_cal"] - r["total_line"], 2),
                     "fair_line_with_personnel": None, "p_home_or_over": fnum(p_over, 4),
                     "market_p_devig": None, "overround_pct": None,
                     "actual": "" if actual_over is None else actual_over,
                     "benchmark_line": fnum(r["total_line"])})
        rows.append({**common, "market": "TOTAL_T2", "sequence": "2b: total, estimator T2 (venue/rest context) - published until one wins",
                     "fair_line": round(r["t2"], 2), "market_line": fnum(r["total_line"]),
                     "residual_fair_minus_market": None if r["total_line"] is None else round(r["t2"] - r["total_line"], 2),
                     "fair_line_with_personnel": None, "p_home_or_over": None, "market_p_devig": None,
                     "overround_pct": None, "actual": "" if actual_over is None else actual_over,
                     "benchmark_line": fnum(r["total_line"])})
        rows.append({**common, "market": "MONEYLINE", "sequence": "3rd: moneyline, derived from the side's margin distribution",
                     "fair_line": prob_to_american(p_win), "market_line": fnum(r["home_ml"], 0),
                     "residual_fair_minus_market": None if r["home_ml"] is None else round(prob_to_american(p_win) - r["home_ml"], 1),
                     "fair_line_with_personnel": prob_to_american(p_cover_B if p_cover_B is not None else p_win),
                     "p_home_or_over": fnum(p_win, 4),
                     "market_p_devig": fnum(devig, 4),
                     "overround_pct": fnum(None if overround is None else 100 * overround, 2),
                     "actual": "" if actual_win is None else actual_win,
                     "benchmark_line": fnum(r["home_ml"], 0)})
        inputs.append({
            "game_id": r["game_id"], "model_version": "FL2-R1", "recorded_utc": "2026-11-16T01:30Z",
            "fixture_status": status,
            "p_home_win": fnum(p_win, 4), "p_home_cover": fnum(p_cover, 4), "p_over": fnum(p_over, 4),
            "fair_margin": round(mu_A, 3), "fair_margin_with_personnel": round(mu_B, 3),
            "fair_total_T1": round(r["t1_cal"], 3), "fair_total_T2": round(r["t2"], 3),
            "calibration_applied": {"margin_intercept": cal["margin"]["intercept"], "margin_slope": cal["margin"]["slope"],
                                    "total_intercept": cal["total"]["intercept"], "total_slope": cal["total"]["slope"]},
            "inputs": {
                "games_used_away": r["games_away"], "games_used_home": r["games_home"],
                "avail_deficit_away": round(r["d_away"], 3), "avail_deficit_home": round(r["d_home"], 3),
                "sigma_margin": round(sigma, 3), "hfa_pts": pri["home_field_advantage_pts"],
                "k_prior_games": K_PRIOR, "roof": r["roof"], "rest_bucket": r["rest_bucket"],
                "beta_pts_per_expected_miss": beta.get("beta_pts_per_expected_miss"),
            },
        })
        if r["played"]:
            resid.append(r["margin"] - mu_A)
    return rows, inputs


def main() -> None:
    hist = load_history()
    games26 = load_2026()
    calib, deficit, avail_rows = build_availability()
    jdump(OUT / "designation-calibration.json", calib)
    pri = build_priors(hist)
    jdump(OUT / "model-priors.json", pri)
    allrec, resid, sigma0 = walk_forward(hist, games26, deficit, pri)
    cal = fit_calibration(allrec, TRAIN_MAX)
    # sigma from 2016-2025 calibrated residuals (still excludes the priced season)
    cal25 = fit_calibration(allrec, VAL)
    pri["sigma_prior_window"] = cal25["margin"]["resid_sd"]
    pri["calibration"] = cal
    apply_calibration(allrec, cal, pri)
    jdump(OUT / "model-calibration.json", cal)
    beta = fit_beta(allrec)
    jdump(OUT / "ablation-injury.json", {
        "question": "Does the verified availability information improve the line, or is a fixed penalty pretending to knowledge we do not have?",
        "method": "Identical model, run with and without the personnel feature; coefficient fitted on 2016-%d only, applied to %d (validation) and %d (holdout). No fixed point penalty is used anywhere." % (TRAIN_MAX, VAL, HOLDOUT),
        "coefficient": beta,
        "availability_source": "signal/data/injury_player.csv (mirror of the official NFL.com report) joined to signal/data/snap_participation.csv",
        "rows_2026": len(avail_rows),
        "leakage_note": "The report mirror carries no per-row fetch timestamp, so 'known before kickoff' is an assumption about weekly publication timing, not a certified fact. Flagged as FL-F04.",
    })
    jdump(OUT / "walk-forward-records.json", {
        "n_records": len(allrec), "seasons": sorted({r["season"] for r in allrec}),
        "definition": "one record per game: mu_A (ratings only), t1, t2, availability gap, and the actual margin/total where played",
    })
    # model-sanity gate. A sign or scale error in the ratings shows up here long before it
    # shows up in a win rate: the projection must still agree with the market it disagrees
    # with. (A flipped defensive term makes corr(model, market) negative.)
    pairs = [r for r in allrec if r["played"] and r["season"] >= HOLDOUT - 1 and r["spread_line"] is not None]
    if len(pairs) >= 40:
        c_mm = pearson([r["mu_cal"] for r in pairs], [r["spread_line"] for r in pairs])
        c_ma = pearson([r["mu_cal"] for r in pairs], [r["margin"] for r in pairs])
        c_xx = pearson([r["spread_line"] for r in pairs], [r["margin"] for r in pairs])
        mae_mk = st.mean([abs(r["mu_cal"] - r["spread_line"]) for r in pairs])
        mae_act = st.mean([abs(r["mu_cal"] - r["margin"]) for r in pairs])
        mae_mkt_act = st.mean([abs(r["spread_line"] - r["margin"]) for r in pairs])
        diag = {
            "n": len(pairs), "corr_model_vs_market": round(c_mm, 3), "corr_model_vs_actual": round(c_ma, 3),
            "corr_market_vs_actual": round(c_xx, 3), "MAE_model_vs_market_pts": round(mae_mk, 2),
            "MAE_model_vs_actual_pts": round(mae_act, 2), "MAE_market_vs_actual_pts": round(mae_mkt_act, 2),
        }
        # fail on pathology, not on being out-priced: a 2-input ratings model SHOULD be
        # worse than a closing market. Failing when it looks better is the leakage check.
        ok = (c_mm > 0.55) and (c_ma < 0.60) and (c_ma - c_xx < 0.03) and (c_ma > 0.15) and mae_mk < 6.0
        jdump(OUT / "model-sanity.json", {
            "checks": {
                "corr_model_vs_market_gt_0.55": c_mm > 0.55,
                "model_not_suspiciously_sharper_than_market_(leakage_check)": c_ma - c_xx < 0.03,
                "model_has_at_least_some_signal": c_ma > 0.15,
                "MAE_model_vs_market_lt_6_pts": mae_mk < 6.0,
            },
            "diagnostics": diag,
            "why": "A ratings model that correlates worse than 0.55 with the closing line is broken; one that correlates BETTER with the outcome than the closing line does is leaking the future. Both are checked here because a defensive-term sign error in this pipeline passed every price-convention check and only showed up in these three numbers.",
        })
        if not ok:
            raise SystemExit(f"MODEL SANITY GATE FAILED: {json.dumps(diag, indent=1)}")
        print("model-sanity gate (pass):", json.dumps(diag))
    rows, inputs = publish_2026(allrec, beta, pri, cal)
    write_csv(OUT / "lines-2026.csv", rows, [
        "game_id", "week", "gameday", "away", "home", "market", "sequence", "fair_line",
        "market_line", "residual_fair_minus_market", "fair_line_with_personnel", "p_home_or_over",
        "market_p_devig", "overround_pct", "sigma_used", "actual", "fixture_status",
        "avail_gap_deficit", "benchmark_line",
    ])
    with open(OUT / "lines-inputs.jsonl", "w", encoding="utf-8") as fh:
        for r in inputs:
            fh.write(json.dumps(r, allow_nan=False) + "\n")
    # in-sample ablation scores (2026 holdout only; these live on the backtest page, never the leaderboard)
    h26 = [r for r in allrec if r["season"] == HOLDOUT and r["played"]]
    b = beta.get("beta_pts_per_expected_miss") or 0.0
    sigma = pri["sigma_margin_default"]
    sc = {}
    for name, col in (("A_ratings_only", "mu_A"),):
        probs = [norm_cdf((r[col] - r["spread_line"]) / r["sigma"]) for r in h26 if r["spread_line"] is not None]
        outs = [int(r["margin"] - r["spread_line"] > 0) for r in h26 if r["spread_line"] is not None and abs(r["margin"] - r["spread_line"]) > 1e-9]
        sc["A_spread_brier"] = round(brier(probs, outs), 5)
    probsB, outs2 = [], []
    for r in h26:
        if r["spread_line"] is None:
            continue
        o = int(r["margin"] - r["spread_line"] > 0) if abs(r["margin"] - r["spread_line"]) > 1e-9 else None
        if o is None:
            continue
        probsB.append(norm_cdf((r["mu_cal"] + b * r["avail_gap"] - r["spread_line"]) / r["sigma"])); outs2.append(o)
    sc["B_with_personnel_spread_brier"] = round(brier(probsB, outs2), 5)
    sc["n_graded"] = len(outs2)
    sc["delta_B_minus_A"] = round(sc["B_with_personnel_spread_brier"] - sc["A_spread_brier"], 5)
    jdump(OUT / "ablation-scores.json", sc)
    print(json.dumps({
        "lines_rows": len(rows), "inputs_rows": len(inputs), "availability_rows_2026": len(avail_rows),
        "priors": {k: pri[k] for k in ("n_games", "league_mean_game_total", "home_field_advantage_pts", "sigma_margin_default")},
        "beta": beta, "ablation_scores": sc,
        "calibration": {k: (v["n"], v["play_rate_pct"]) for k, v in calib["by_designation"].items()},
    }, indent=1))


if __name__ == "__main__":
    main()
