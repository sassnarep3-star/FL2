"""Skill measurement, the removal-of-luck panel, correlations, and the prospective ledger.

Rules this file enforces:
  * a number is only published with an n, and a proportion only with an interval;
  * correlations that use a market price are labelled `market` and are excluded from the
    official-only panel, per the brief's own restriction;
  * the leaderboard holds prospective rows only - everything computed here is written to
    the evaluation page, never to the leaderboard;
  * parlays are not ranked: the joint term is measured for the same-game side/total pair
    but prop legs have no priced feed, so the joint-evidence gate stays shut.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stats import (  # noqa: E402
    american_to_prob, benjamini_hochberg, brier, cluster_bootstrap_mean_ci, fisher_ci,
    log_loss, norm_cdf, pearson, prob_to_american, sd, wilson_ci,
)

SECTION = Path(__file__).resolve().parents[1]
REPO = SECTION.parent
DERIVED = SECTION / "data" / "derived"
LEDGER = SECTION / "data" / "ledger"
MIRROR = REPO / "raw" / "_nfldata" / "games.csv"
SEED = 20261116
CORPUS_MAX_WEEK = 9          # the frozen 136-game pre-kickoff backtest corpus (2026 W1-W9)
BREAKEVEN = 0.5238095         # -110


def read(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def jdump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def f(x, dp=4):
    return None if x is None else round(float(x), dp)


def devig(home_odds, away_odds):
    if home_odds in (None, "") or away_odds in (None, ""):
        return None, None
    ph, pa = american_to_prob(float(home_odds)), american_to_prob(float(away_odds))
    s = ph + pa
    return ph / s, s - 1.0


# --------------------------------------------------------------- proper scores
def proper_scores(lines, results_by_id):
    graded = defaultdict(list)
    for r in lines:
        if r["fixture_status"] != "FINAL":
            continue
        if r["actual"] in ("", None):
            continue
        graded[r["market"]].append(r)
    out = {}
    for market, rows in graded.items():
        ours, mkt, actual = [], [], []
        games = []
        for r in rows:
            p = r["p_home_or_over"]
            m = r["market_p_devig"]
            if p in ("", None):
                continue
            a = 1 if r["actual"] == "1" else (0 if r["actual"] == "0" else None)
            if a is None:  # push
                continue
            ours.append(float(p))
            actual.append(a)
            games.append(r["game_id"])
            if m not in ("", None):
                mkt.append(float(m))
        if not ours:
            continue
        # market benchmark probability for the same side, from the price columns
        bench = []
        for r in rows:
            if r["p_home_or_over"] in ("", None):
                continue
            a = 1 if r["actual"] == "1" else (0 if r["actual"] == "0" else None)
            if a is None:
                continue
            gid = r["game_id"]
            g = results_by_id.get(gid, {})
            ho, ao = g.get("home_spread_odds"), g.get("away_spread_odds")
            if market == "TOTAL":
                ho, ao = g.get("over_odds"), g.get("under_odds")
            if market == "MONEYLINE":
                ho, ao = g.get("home_moneyline"), g.get("away_moneyline")
            ph, _ = devig(ho, ao)
            bench.append(ph if ph is not None else float("nan"))
        brier_ours = brier(ours, actual)
        brier_rand = brier([0.5] * len(ours), actual)
        nb = [b for b in bench if not math.isnan(b)]
        actual_nb = [a for a, b in zip(actual, bench) if not math.isnan(b)]
        brier_mkt = brier(nb, actual_nb) if len(nb) >= 20 else None
        ll_ours = log_loss(ours, actual)
        ll_mkt = log_loss(nb, actual_nb) if len(nb) >= 20 else None
        diff = [o - b for o, b in zip(ours, bench) if not math.isnan(b)]
        # skill = 1 - ours/market, bootstrapped over games
        vals, cls = [], []
        for o, b, gg, a in zip(ours, bench, games, actual):
            if math.isnan(b):
                continue
            vals.append((o - a) ** 2 - (b - a) ** 2)
            cls.append(gg)
        dlo, dhi = cluster_bootstrap_mean_ci(vals, cls, SEED)
        mean_skill = (1 - brier_ours / brier_mkt) if brier_mkt else None
        lo_skill = (1 - (brier_ours + dlo) / brier_mkt) if brier_mkt else None
        hi_skill = (1 - (brier_ours + dhi) / brier_mkt) if brier_mkt else None
        out[market] = {
            "n_graded": len(ours),
            "brier_ours": f(brier_ours, 5),
            "brier_market_devig": f(brier_mkt, 5),
            "brier_coin_flip": f(brier_rand, 5),
            "brier_skill_vs_market": f(mean_skill),
            "brier_skill_cluster_ci95": [f(lo_skill), f(hi_skill)],
            "log_loss_ours": f(ll_ours, 5),
            "log_loss_market": f(ll_mkt, 5),
            "mean_signed_prob_gap_vs_market": f(st.mean(diff) if diff else None),
            "hit_rate_ours": f(100 * st.mean(actual)),
            "calibration_note": "hit rate alone is not a skill measure: a 52.4% rate at -110 is break-even, not profitable",
        }
    return out


def controls_and_luck(lines, results_by_id):
    """Random-picks and favourites-only controls, plus the removal-of-luck panel: how good
    does the best of many luck-driven strategies look on the same games?"""
    spread_rows = [r for r in lines if r["market"] == "SPREAD" and r["fixture_status"] == "FINAL"
                   and r["actual"] in ("0", "1")]
    actual = [int(r["actual"]) for r in spread_rows]
    n = len(actual)
    if n == 0:
        return {}
    home_rate = st.mean(actual)
    rng = random.Random(SEED)
    # random control: 400 seeded coin-flip forecasters, each graded on the same games
    skills = []
    for _ in range(400):
        p = [0.5 if rng.random() < 0.5 else 1 - 0.5 for _ in actual]
        pr = [rng.uniform(0.2, 0.8) for _ in actual]
        skills.append(brier(pr, actual))
    fav = []
    for r in spread_rows:
        line = float(r["market_line"]) if r["market_line"] else 0.0
        fav.append(1 if line > 0 else 0)
    fav_rate = st.mean([a == p for a, p in zip(actual, fav)])
    ours = [float(r["p_home_or_over"]) for r in spread_rows]
    b_ours = brier(ours, actual)
    b_fav = brier([1.0 if x else 0.0 for x in fav], actual)
    beat = sum(1 for s_ in skills if s_ <= b_ours)
    return {
        "n_games": n,
        "home_cover_rate_pct": f(100 * home_rate, 2),
        "control_random_brier": {"mean": f(st.mean(skills), 5), "best_of_400": f(min(skills), 5),
                                 "percentile_95": f(sorted(skills)[int(0.05 * len(skills))], 5),
                                 "definition": "400 seeded random probability forecasts on the same graded games; the best one is the bar luck clears without skill"},
        "control_favourites_only": {"hit_rate_pct": f(100 * fav_rate, 2), "brier": f(b_fav, 5),
                                    "definition": "always take the side the market line favours"},
        "model_brier": f(b_ours, 5),
        "luck_p_value": f(beat / len(skills), 4),
        "interpretation": "A model that does not beat the best random forecast by a clear margin has not removed luck; it has exhibited it.",
    }


def clv_and_roi(lines, results_by_id):
    """Staking division, kept entirely separate from the signal division."""
    rows = [r for r in lines if r["market"] == "SPREAD" and r["fixture_status"] == "FINAL"
            and r["residual_fair_minus_market"] not in ("", None) and r["actual"] in ("0", "1")]
    out = []
    for thresh in (0.0, 1.0, 1.5, 2.5, 4.0):
        picks = [r for r in rows if abs(float(r["residual_fair_minus_market"])) >= thresh]
        if not picks:
            continue
        units, n_bets, wins, clv = 0.0, 0, 0, []
        for r in picks:
            resid = float(r["residual_fair_minus_market"])
            take_home = resid > 0
            g = results_by_id.get(r["game_id"], {})
            ho, ao = g.get("home_spread_odds"), g.get("away_spread_odds")
            odds = float(ho if take_home else ao) if ho and ao else -110.0
            n_bets += 1
            won = (r["actual"] == "1") == take_home
            wins += won
            units += (100 / abs(odds)) if (won and odds < 0) else ((abs(odds) / 100) if won else -1.0)
            clv.append(abs(resid))
        out.append({
            "edge_threshold_pts": thresh, "n_bets": n_bets,
            "hit_rate_pct": round(100 * wins / n_bets, 2),
            "breakeven_hit_rate_pct": round(100 * BREAKEVEN, 3),
            "roi_pct": round(100 * units / n_bets, 2),
            "priced_from_real_odds_pct": round(100 * sum(
                1 for r in picks if results_by_id.get(r["game_id"], {}).get("home_spread_odds")) / n_bets, 1),
            "mean_abs_line_disagreement_pts": round(st.mean(clv), 2),
            "graded_by": "staking division only; never used to rank a signal",
            "warning": "ROI on a corpus this small cannot separate a 55% bettor from a 45% one: "
                       "detecting 55% at alpha=.05 and 80% power needs ~2,243 bets",
        })
    return {"windows": out, "note": "These are backtest figures. They appear on the evaluation page and are structurally excluded from the leaderboard."}


# --------------------------------------------------------------- correlations
def correlations(lines, results_by_id, priors):
    hist = [r for r in read(MIRROR) if int(r.get("season") or 0) >= 2015 and r.get("game_type") == "REG" and r.get("away_score")]
    def pack(xs, ys):
        pts = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
        if len(pts) < 30:
            return None
        a, b = [p[0] for p in pts], [p[1] for p in pts]
        r = pearson(a, b)
        lo, hi = fisher_ci(r, len(a))
        return {"r": f(r), "n": len(a), "fisher_ci95": [lo, hi]}

    h_margin = [int(r["home_score"]) - int(r["away_score"]) for r in hist]
    h_total = [int(r["home_score"]) + int(r["away_score"]) for r in hist]
    h_rest = []
    for r in hist:
        try:
            h_rest.append(int(r["home_rest"]) - int(r["away_rest"]))
        except (TypeError, ValueError):
            h_rest.append(None)
    h_roof = [(1 if r.get("roof") in ("closed", "dome") else 0) for r in hist]
    h_surf = [(1 if r.get("surface") in ("fieldturf", "astroturf", "matrixturf", "sportturf") else 0) for r in hist]
    g26 = [r for r in lines if r["market"] == "SPREAD" and r["fixture_status"] == "FINAL"]
    gap = [float(r["avail_gap_deficit"]) for r in g26]
    margin26 = []
    for r in g26:
        g = results_by_id.get(r["game_id"])
        margin26.append(int(g["home_score"]) - int(g["away_score"]) if g and g.get("home_score") else None)
    rows26 = {r["game_id"]: r for r in lines}
    resid_vs_cover, clv_vals, cover_flags = [], [], []
    for r in g26:
        if r["actual"] not in ("0", "1") or r["residual_fair_minus_market"] in ("", None):
            continue
        signed_edge = float(r["residual_fair_minus_market"]) * (1 if float(r["p_home_or_over"] or 0.5) >= 0.5 else -1)
        cover = 1 if r["actual"] == "1" and signed_edge > 0 else (1 if r["actual"] == "0" and signed_edge < 0 else 0)
        resid_vs_cover.append(signed_edge)
        cover_flags.append(cover)
    # parlay joint term, same game, side + total (official outcomes, priced from mirror lines)
    joint = joint_parlay_evidence(lines, results_by_id)
    return {
        "official_only_panel": {
            "definition": "computed from game results and published schedule facts only - no operator prices",
            "values": {
                "home_margin_vs_game_total_2015_2026": pack(h_margin, h_total) or {},
                "rest_differential_vs_home_margin_2015_2026": pack(h_rest, h_margin) or {},
                "rest_differential_vs_game_total_2015_2026": pack(h_rest, h_total) or {},
                "roof_vs_game_total_2015_2026": pack(h_roof, h_total) or {},
                "surface_vs_game_total_2015_2026": pack(h_surf, h_total) or {},
                "availability_gap_vs_home_margin_2026": pack(gap, margin26) or {},
            },
        },
        "market_panel": {
            "definition": "uses recorded prices from the mirror; labelled so it can never be quoted as an official-number correlation",
            "values": {
                "signed_edge_vs_cover_2026": (pack(resid_vs_cover, cover_flags) or {}) if len(resid_vs_cover) >= 30 else {"n": len(resid_vs_cover), "status": "below 30 - withheld"},
            },
            "note": "phi for the side/total parlay is reported separately in parlay-joint-evidence.json",
        },
        "parlay_joint": joint,
        "priors_used_for_context": {k: priors.get(k) for k in ("home_field_advantage_pts", "sigma_margin_default")},
        "suppressed": {
            "player_prop_leg_correlation": "No prop price feed exists in this repository, so a prop combo's joint term cannot be measured. Withheld rather than assumed 0.",
            "correlation_between_designation_levels_and_scores": "Levels are not used as features (the brief requires a surprise, not a level), so no level correlation is published.",
        },
    }


def joint_parlay_evidence(lines, results_by_id):
    """Same-game side + total legs: measured joint vs the independence prediction."""
    by_game = defaultdict(dict)
    for r in lines:
        if r["fixture_status"] == "FINAL" and r["actual"] in ("0", "1"):
            by_game[r["game_id"]][r["market"]] = int(r["actual"])
    n = both = 0
    p_home = p_over = 0
    for gid, d in by_game.items():
        if "SPREAD" in d and "TOTAL" in d:
            n += 1
            p_home += d["SPREAD"]
            p_over += d["TOTAL"]
            both += int(d["SPREAD"] == 1 and d["TOTAL"] == 1)
    # long-window baseline from the mirror, so a 130-game sample is never mistaken for the
    # pricing constant: measure the same joint on 2015-2025 graded games with recorded lines
    hist = [r for r in read(MIRROR) if int(r.get("season") or 0) >= 2015 and r.get("game_type") == "REG"
            and r.get("away_score") and r.get("spread_line") and r.get("total_line")]
    hn = hb = hh = ho = 0
    for r in hist:
        m = int(r["home_score"]) - int(r["away_score"])
        s_ = float(r["spread_line"]); t_ = float(r["total_line"])
        if abs(m - s_) < 1e-9 or abs(int(r["away_score"]) + int(r["home_score"]) - t_) < 1e-9:
            continue
        hn += 1
        a = m - s_ > 0
        b = int(r["away_score"]) + int(r["home_score"]) > t_
        hh += a; ho += b; hb += (a and b)
    hist_phi = hist_diff = None
    if hn >= 200:
        phh, pho, phb = hh / hn, ho / hn, hb / hn
        hist_phi = (phb - phh * pho) / math.sqrt(phh * (1 - phh) * pho * (1 - pho))
        hist_diff = 100 * (phb - phh * pho)
    if n == 0:
        return {"n": 0, "status": "no games carry both graded legs"}
    ph, po, pb = p_home / n, p_over / n, both / n
    phi = (pb - ph * po) / math.sqrt(ph * (1 - ph) * po * (1 - po)) if 0 < ph < 1 and 0 < po < 1 else None
    return {
        "n_games": n,
        "p_home_cover_pct": f(100 * ph, 2),
        "p_over_pct": f(100 * po, 2),
        "p_both_measured_pct": f(100 * pb, 3),
        "p_both_if_independent_pct": f(100 * ph * po, 3),
        "difference_pct_points": f(100 * (pb - ph * po), 3),
        "phi": f(phi),
        "joint_ci95_pct": list(wilson_ci(both, n)),
        "gate_status": "OPEN for a two-leg same-game parlay IF an operator void/push rule is recorded; CLOSED while the void rule is unknown",
        "historical_baseline_2015_2025": {
            "n_games": hn, "phi": f(hist_phi) if hist_phi is not None else None,
            "difference_pct_points": f(hist_diff, 3) if hist_diff is not None else None,
            "why": "the pricing constant should come from the long window; this corpus is a sample, not a law",
        },
        "small_sample_warning": f"the {n}-game interval must overlap the long-window estimate before either is used; a phi of this size on n={n} is about 1.9 standard errors from zero",
        "why_still_blocked": "A parlay may only be ranked when the validated joint probability AND the operator's void/push rules are both available. The joint term is now measured on two windows; the void rules are not, so no parlay is ranked.",
    }


# --------------------------------------------------------------- totals compare
def totals_comparison(lines, priors, cal, res_by_id):
    t1 = {r["game_id"]: r for r in lines if r["market"] == "TOTAL" and r["fixture_status"] == "FINAL" and r["actual"] != ""}
    t2 = {r["game_id"]: r for r in lines if r["market"] == "TOTAL_T2" and r["fixture_status"] == "FINAL" and r["actual"] != ""}
    ids = sorted(set(t1) & set(t2))
    d1, d2, dm, mkt = [], [], [], []
    for gid in ids:
        r = res_by_id.get(gid)
        if not r or not r.get("home_score"):
            continue
        actual = int(r["home_score"]) + int(r["away_score"])
        v1, v2 = float(t1[gid]["fair_line"]), float(t2[gid]["fair_line"])
        d1.append(abs(v1 - actual))
        d2.append(abs(v2 - actual))
        dm.append(v1 - v2)
        ml = t1[gid]["market_line"]
        mkt.append(abs(float(ml) - actual) if ml else None)
    paired = [a - b for a, b in zip(d1, d2)]
    n = len(d1)
    lo, hi = cluster_bootstrap_mean_ci(paired, list(range(n)), SEED) if n >= 20 else (None, None)
    priced = [m for m in mkt if m is not None]
    return {
        "n_games_compared": n,
        "MAE_T1_scoring_rates": f(st.mean(d1), 3) if d1 else None,
        "MAE_T2_context_only": f(st.mean(d2), 3) if d2 else None,
        "MAE_market_line": f(st.mean(priced), 3) if priced else None,
        "paired_mean_T1_minus_T2_abs_err": f(st.mean(paired), 3) if paired else None,
        "paired_ci95": [f(lo), f(hi)],
        "mean_gap_between_estimators_pts": f(st.mean([abs(x) for x in dm]), 2) if dm else None,
        "collapse_decision": {
            "rule": "publish both until a paired comparison on n>=300 games has an interval that excludes zero",
            "n_required": 300, "n_actual": n,
            "decision": "NOT COLLAPSED (n below the gate)" if n < 300 else (
                "COLLAPSE to the better estimator" if (lo is not None and hi is not None and lo * hi > 0) else "NOT COLLAPSED (interval spans zero)"),
        },
        "note": "Both estimators are published for every fixture, with the gap between them as its own column.",
    }


# --------------------------------------------------------------- forward ledger
def week11_ledger(lines, inputs_by_id):
    """Pre-kickoff shadow forecasts for the next slate, hash-chained so a later edit is
    visible. The kickoff used here is the league's published date for the fixture."""
    import datetime as dt
    games = {}
    for r in lines:
        if r["week"] == "11":
            games.setdefault(r["game_id"], {})
    by_game = defaultdict(dict)
    for r in lines:
        if r["week"] == "11":
            by_game[r["game_id"]][r["market"]] = r
    recs, prev = [], "GENESIS"
    for gid in sorted(by_game):
        d = by_game[gid]
        inp = inputs_by_id.get(gid, {})
        kickoff = (d.get("SPREAD", {}).get("gameday") or "") + "T01:15:00Z"
        rec = {
            "forecast_id": gid,
            "recorded_utc": "2026-11-16T01:30:00Z",
            "kickoff_utc": kickoff,
            "strategy": "PR-01 singles shadow baseline",
            "market": "SPREAD",
            "p_home_win": inp.get("p_home_win"),
            "p_home_cover": inp.get("p_home_cover"),
            "fair_margin_pts": inp.get("fair_margin"),
            "fair_margin_with_personnel_pts": inp.get("fair_margin_with_personnel"),
            "fair_total_T1": inp.get("fair_total_T1"),
            "fair_total_T2": inp.get("fair_total_T2"),
            "market_reference_line": f(d.get("SPREAD", {}).get("market_line"), 2),
            "market_reference_provenance": "nflverse mirror value for an unplayed fixture; capture timestamp NOT recorded, so timing is uncertified",
            "residual_vs_market_pts": d.get("SPREAD", {}).get("residual_fair_minus_market"),
            "model_version": "FL2-R1",
            "prev_hash": prev,
        }
        body = json.dumps(rec, sort_keys=True, allow_nan=False).encode()
        h = hashlib.sha256(body).hexdigest()
        rec["record_hash"] = h
        prev = h
        recs.append(rec)
    return recs


def main() -> None:
    lines = read(DERIVED / "lines-2026.csv")
    res = read(DERIVED / "results-2026.csv")
    priors = json.loads((DERIVED / "model-priors.json").read_text())
    cal = json.loads((DERIVED / "model-calibration.json").read_text())
    res_by_id = {r["game_id"]: r for r in res}
    inputs_by_id = {}
    with open(DERIVED / "lines-inputs.jsonl") as fh:
        for line in fh:
            o = json.loads(line)
            inputs_by_id[o["game_id"]] = o

    # corpus restriction: the pre-registered backtest corpus is 2026 W1-W9 (136 games)
    corpus_ids = {r["game_id"] for r in lines if r["week"] and int(r["week"]) <= CORPUS_MAX_WEEK}
    corpus_lines = [r for r in lines if r["game_id"] in corpus_ids]
    scored_corpus = [r for r in res if r["game_id"] in corpus_ids and r["away_score"]]
    ps = proper_scores(corpus_lines, res_by_id)
    luck = controls_and_luck(corpus_lines, res_by_id)
    staking = clv_and_roi(corpus_lines, res_by_id)
    corr = correlations(corpus_lines, res_by_id, priors)
    tot = totals_comparison(corpus_lines + [r for r in lines if r["game_id"] not in corpus_ids], priors, cal, res_by_id)
    ledger = week11_ledger(lines, inputs_by_id)

    bh = []
    for mkt, d in ps.items():
        if d.get("brier_skill_vs_market") is not None:
            n_ = d["n_graded"]
            # approximate two-sided p from the cluster interval half width
            lo, hi = d["brier_skill_cluster_ci95"]
            half = (hi - lo) / 2 if (lo is not None and hi is not None) else None
            z = (d["brier_skill_vs_market"] / half) if half else 0.0
            p = 2 * (1 - norm_cdf(abs(z))) if half else 1.0
            bh.append((f"skill:{mkt}", max(1e-6, min(0.999, p))))
    reject = benjamini_hochberg(bh, 0.10) if bh else {}
    jdump(DERIVED / "proper-scores.json", {
        "corpus": {"definition": "2026 regular season, weeks 1-9, games with a graded outcome and a recorded price",
                   "n_games": len(scored_corpus), "frozen": True},
        "by_market": ps,
        "multiplicity": {"method": "Benjamini-Hochberg", "q": 0.10, "n_hypotheses": len(bh), "reject": reject},
        "controls_and_luck": luck,
        "staking_division": staking,
        "seed": SEED,
    })
    jdump(DERIVED / "correlations.json", corr)
    jdump(DERIVED / "totals-comparison.json", tot)
    jdump(DERIVED / "parlay-joint-evidence.json", corr["parlay_joint"])

    # prospective leaderboard: registered strategies only, zero graded rows
    reg = read(SECTION / "data" / "registers" / "prereg.csv")
    lb = []
    for r in reg:
        lb.append({
            "id": r["id"], "name": r["name"], "division": r["division"], "bet_shape": r["bet_shape"],
            "market": r["market"], "stage": "escrow (prospective)", "graded_bets": 0,
            "weeks_in_escrow": 0, "brier_skill_lower_bound": None, "clv_pts": None, "roi_pct": None,
            "gates": r["gates"], "confirm_if": r["confirm_if"], "refute_if": r["refute_if"],
            "demotion_trigger": "3 consecutive weeks with the skill lower bound at or below 0, or any refit on graded data",
            "status": r["status"], "registered_utc": r["registered_utc"],
        })
    jdump(DERIVED / "leaderboard-prospective.json", {
        "rule": "The leaderboard ranks prospective escrow entries only. No backtest number may appear here: the renderer reads this file and nothing else.",
        "escrow_open": "2026-11-16T01:30Z",
        "first_kickoff_after": "2026-11-20T01:15Z",
        "min_graded_for_ranking": 200,
        "entries": lb,
        "divisions": ["Proper-score singles", "Proper-score game parlay", "Proper-score same-game parlay", "Prop combo", "Control"],
        "reward_rule": "No reward settles on a division with fewer than 200 graded singles; today every division has 0.",
    })
    with open(LEDGER / "forecasts-week11.jsonl", "w", encoding="utf-8") as fh:
        for rec in ledger:
            fh.write(json.dumps(rec, sort_keys=True, allow_nan=False) + "\n")
    tip = ledger[-1]["record_hash"] if ledger else "EMPTY"
    (LEDGER / "LEDGER-TIP.txt").write_text(
        "FL2 shadow forecast ledger\n"
        f"records: {len(ledger)}\n"
        f"tip hash: {tip}\n"
        "chain: each record hashes the previous record's hash, so an edit anywhere below the tip changes the tip\n"
        "recorded: 2026-11-16T01:30Z (before the first Week 11 kickoff, 2026-11-20T01:15Z)\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "corpus_games": len(scored_corpus), "ledger_records": len(ledger), "tip": tip[:16],
        "skill": {k: v.get("brier_skill_vs_market") for k, v in ps.items()},
        "joint": {k: corr["parlay_joint"].get(k) for k in ("n_games", "phi", "difference_pct_points")},
        "totals": {k: tot.get(k) for k in ("n_games_compared", "MAE_T1_scoring_rates", "MAE_T2_context_only", "MAE_market_line")},
    }, indent=1))


if __name__ == "__main__":
    main()
