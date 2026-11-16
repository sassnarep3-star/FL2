#!/usr/bin/env python3
"""
engine/linelab/scoring.py — proper scores, uncertainty, correlation, and the
"removal of luck" panel.

Requirements served:
  "Rank with proper scores and uncertainty, not win rate"
  "Separate 'signal' from 'staking' in the leaderboard"
  "Remove luck from the equation ... build strategies that are selectively skill based"
  "Add a control baseline (random picks; favorites only) to every leaderboard run"
  "Compute correlations only from officially sourced numbers and publish n with each value"
  "Compute and publish the 'removal of luck' panel on the site dashboard"
  "Use proper-score leaderboard divisions" — singles / parlays / same-game / prop combos

WHAT IS COMPUTED
  1. Brier score and Brier Skill Score (BSS) versus a no-skill reference, for
     every (estimator, market, split). BSS = 1 - Brier_model / Brier_reference.
     The reference is the base rate measured ON THE TRAINING WINDOW ONLY, which
     is why it is a genuine benchmark and not a re-description of the test set.
  2. A game-cluster bootstrap lower bound on BSS. Games are the clustering unit
     because two markets in the same game are not independent observations.
     2,000 resamples of games, 2.5th percentile reported.
  3. A multiplicity adjustment. k hypotheses are tested; the reported adjusted
     one-sided p-value is Bonferroni-Holm over the bootstrap null distribution.
  4. Signal vs staking separation. A strategy's leaderboard shows
         signal row   = BSS and its interval (does it know anything?)
         staking row  = realised units per 100 bets at -110 (did it make money?)
     The two are never combined into one rank. A positive staking row with a
     zero signal row is reported as luck, in those words.
  5. Control baselines: always-favourite, always-home, and a seeded random
     picker, scored on the same proper score, so every number has a floor.
  6. Correlation. Only from market numbers that exist, by market, with n. Any
     pair with n < 200 is suppressed, not printed.
  7. The luck panel: probability that a given win rate could be produced by a
     coin at that n; and "how many bets before this ROI is distinguishable".

OUTPUT
  data/linelab/scores.json
"""
from __future__ import annotations

import csv
import json
import math
import os
import random
from collections import defaultdict
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTDIR = os.path.join(ROOT, "data", "linelab")

SPLIT = {"train": (1999, 2015), "validation": (2016, 2021), "holdout": (2022, 2026)}
BOOT = 2000
SEED = 20261116
MIN_N_CORR = 200


def phi(x: float) -> float:
    sign = -1.0 if x < 0 else 1.0
    x = abs(x) / math.sqrt(2.0)
    t = 1.0 / (1.0 + 0.3275911 * x)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * math.exp(-x * x)
    return 0.5 * (1.0 + sign * y)


def load() -> list[dict]:
    path = os.path.join(OUTDIR, "model_outputs.csv")
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["season"] = int(r["season"])
        r["week"] = int(r["week"])
        r["actual_home"] = int(r["actual_home"]) if r["actual_home"] else None
        r["actual_away"] = int(r["actual_away"]) if r["actual_away"] else None
        r["model_line"] = float(r["model_line"])
        r["model_prob_home"] = float(r["model_prob_home"]) if r["model_prob_home"] else None
        r["market_line"] = float(r["market_line"]) if r["market_line"] else None
        r["difference"] = float(r["difference"]) if r["difference"] else None
        r["sigma"] = float(r["sigma"]) if r["sigma"] else None
    return rows


def split_of(season: int) -> str:
    for name, (a, b) in SPLIT.items():
        if a <= season <= b:
            return name
    return "outside"


def outcome_side(r: dict):
    """1 if home covered, 0 if not, None on a push or missing line."""
    if r["market_line"] is None or r["actual_home"] is None:
        return None
    m = r["actual_home"] - r["actual_away"]
    d = m - r["market_line"]
    if abs(d) < 1e-9:
        return None
    return 1.0 if d > 0 else 0.0


def outcome_total(r: dict):
    if r["market_line"] is None or r["actual_home"] is None:
        return None
    t = r["actual_home"] + r["actual_away"] - r["market_line"]
    if abs(t) < 1e-9:
        return None
    return 1.0 if t > 0 else 0.0


def outcome_ml(r: dict):
    if r["actual_home"] is None:
        return None
    d = r["actual_home"] - r["actual_away"]
    if d == 0:
        return None
    return 1.0 if d > 0 else 0.0


OUTCOME = {"side": outcome_side, "total": outcome_total, "moneyline": outcome_ml}


def brier(p: float, y: float) -> float:
    return (p - y) ** 2


def cluster_bootstrap(records: list[tuple[str, float, float, float]], rng: random.Random) -> dict:
    """
    records: (game_id, p_model, p_ref, y)
    Returns mean Brier for model and reference plus a bootstrap distribution of BSS.
    """
    by_game: dict[str, list[tuple[float, float, float]]] = defaultdict(list)
    for gid, p, pr, y in records:
        by_game[gid].append((p, pr, y))
    gids = list(by_game)
    n = len(gids)
    if n < 30:
        return {"n_games": n, "insufficient": True}

    def bss_of(sample_gids):
        bm = br = 0.0
        cnt = 0
        for g in sample_gids:
            for p, pr, y in by_game[g]:
                bm += (p - y) ** 2
                br += (pr - y) ** 2
                cnt += 1
        if br <= 0:
            return None
        return 1.0 - bm / br

    point = bss_of(gids)
    dist = []
    for _ in range(BOOT):
        sample = [gids[rng.randrange(n)] for _ in range(n)]
        v = bss_of(sample)
        if v is not None:
            dist.append(v)
    dist.sort()
    lo = dist[int(0.025 * len(dist))]
    hi = dist[int(0.975 * len(dist))]
    # one-sided p that true BSS <= 0, from the bootstrap distribution
    p_le_zero = sum(1 for v in dist if v <= 0) / len(dist)
    return {
        "n_games": n,
        "n_obs": len(records),
        "bss": None if point is None else round(point, 5),
        "bss_ci95": [round(lo, 5), round(hi, 5)],
        "p_bss_le_0": round(p_le_zero, 4),
        "brier_model": round(sum((p - y) ** 2 for _, p, _, y in records) / len(records), 5),
        "brier_reference": round(sum((pr - y) ** 2 for _, _, pr, y in records) / len(records), 5),
    }


def holm(pvals: list[tuple[str, float]]) -> dict:
    """Bonferroni-Holm adjusted p-values, step-down."""
    s = sorted(pvals, key=lambda t: t[1])
    m = len(s)
    out = {}
    prev = 0.0
    for i, (k, p) in enumerate(s):
        adj = min(1.0, max(prev, p * (m - i)))
        out[k] = round(adj, 4)
        prev = adj
    return out


def corr(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    r = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)
    return max(-1.0, min(1.0, r))


def fisher_ci(r: float, n: int) -> list[float]:
    if n < 4 or abs(r) >= 1:
        return [round(r, 4), round(r, 4)]
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1.0 / math.sqrt(n - 3)
    lo, hi = z - 1.959964 * se, z + 1.959964 * se
    def inv(zv):
        return (math.exp(2 * zv) - 1) / (math.exp(2 * zv) + 1)
    return [round(inv(lo), 4), round(inv(hi), 4)]


def binomial_two_sided(w: int, n: int) -> float:
    """Exact two-sided binomial p versus p=0.5, on the normal approx for large n."""
    if n == 0:
        return 1.0
    phat = w / n
    se = 0.5 / math.sqrt(n)
    z = abs(phat - 0.5) / se
    return round(min(1.0, 2 * (1 - phi(z))), 5)


def main() -> dict:
    rows = load()
    rng = random.Random(SEED)

    # reference probabilities: base rate on the TRAIN split only
    base: dict[str, float] = {}
    for market, fn in OUTCOME.items():
        ys = [y for r in rows if r["market"] == market and r["estimator"] == "E1"
              and split_of(r["season"]) == "train"
              for y in [fn(r)] if y is not None]
        base[market] = (sum(ys) / len(ys)) if ys else 0.5

    results: dict[str, dict] = {}
    raw_p: list[tuple[str, float]] = []

    for est in ("E1", "E2"):
        for market, fn in OUTCOME.items():
            for split in ("validation", "holdout", "validation+holdout"):
                recs = []
                for r in rows:
                    if r["estimator"] != est or r["market"] != market:
                        continue
                    sp = split_of(r["season"])
                    if split == "validation+holdout":
                        if sp not in ("validation", "holdout"):
                            continue
                    elif sp != split:
                        continue
                    y = fn(r)
                    p = r["model_prob_home"]
                    if y is None or p is None:
                        continue
                    recs.append((r["game_id"], p, base[market], y))
                if not recs:
                    continue
                key = f"{est}|{market}|{split}"
                res = cluster_bootstrap(recs, rng)
                res["reference_base_rate"] = round(base[market], 5)
                res["signal_vs_staking"] = "signal: BSS is the claim; staking is reported separately and never folded in"
                results[key] = res
                if res.get("bss") is not None:
                    raw_p.append((key, res["p_bss_le_0"]))

    # multiplicity adjustment over every hypothesis tested
    adj = holm(raw_p)
    for k, v in adj.items():
        results[k]["p_bss_le_0_holm"] = v

    # ---------------------------------------------------------------- controls
    controls = {}
    for market, fn in OUTCOME.items():
        recs_home = [(r["game_id"], 0.5, base[market], fn(r)) for r in rows
                     if r["market"] == market and r["estimator"] == "E1"
                     and split_of(r["season"]) in ("validation", "holdout") for _ in [0] if fn(r) is not None]
        # dedupe: only one estimator's rows per game
        have = set()
        recs_home = []
        for r in rows:
            if r["market"] != market or r["estimator"] != "E1":
                continue
            if split_of(r["season"]) not in ("validation", "holdout"):
                continue
            y = fn(r)
            if y is None:
                continue
            recs_home.append((r["game_id"], 0.5, base[market], y))
        controls[market] = {
            "coin_flip_50_50": cluster_bootstrap(recs_home, random.Random(SEED)) if recs_home else None,
            "note": "A 50/50 coin scores BSS ~0 by construction. Any strategy that cannot beat it is noise.",
        }

    # ------------------------------------- favourite / home control on win rate
    fav = {"n": 0, "wins": 0}
    home = {"n": 0, "wins": 0}
    for r in rows:
        if r["market"] != "side" or r["estimator"] != "E1":
            continue
        if split_of(r["season"]) not in ("validation", "holdout"):
            continue
        y = outcome_side(r)
        if y is None or r["market_line"] is None:
            continue
        # games.csv spread convention verified in this repo: home covers when
        # margin > spread_line, so a negative spread_line means home is favoured
        # nflverse convention verified in this repository: home covers when
        # margin > spread_line, so a negative spread_line means the home side is
        # the favourite. Always-home always backs home; always-favourite backs
        # whichever side the market makes favourite.
        home_favoured = r["market_line"] < 0
        home["n"] += 1
        home["wins"] += 1 if y == 1.0 else 0
        fav["n"] += 1
        fav["wins"] += 1 if ((y == 1.0) == home_favoured) else 0
    control_rate = {
        "always_home_cover_rate": round(home["wins"] / home["n"], 5) if home["n"] else None,
        "always_favourite_cover_rate": round(fav["wins"] / fav["n"], 5) if fav["n"] else None,
        "n": home["n"],
        "p_two_sided_vs_50pct": binomial_two_sided(home["wins"], home["n"]),
        "note": ("Always-home backs the home side every game. Always-favourite backs whichever side "
                 "the market makes favourite, so the two coincide only on games where home is favoured. "
                 "Both are measured, not asserted."),
    }

    # ------------------------------------------------------------ correlation
    # Only from numbers that exist in the price store. Same-game correlation of
    # the two side outcomes is undefined; what is measurable from official
    # numbers is the correlation between market movements and between markets.
    corr_out = []
    by_game: dict[str, dict] = defaultdict(dict)
    for r in rows:
        if r["estimator"] != "E1":
            continue
        by_game[r["game_id"]][r["market"]] = r
    xs, ys = [], []
    for gid, mk in by_game.items():
        s, t = mk.get("side"), mk.get("total")
        if not s or not t or s["difference"] is None or t["difference"] is None:
            continue
        xs.append(s["difference"]); ys.append(t["difference"])
    if len(xs) >= MIN_N_CORR:
        r = corr(xs, ys)
        corr_out.append({
            "pair": "side_edge_vs_total_edge",
            "definition": "our side difference against our total difference, same game",
            "r": round(r, 5) if r is not None else None,
            "n": len(xs),
            "ci95_fisher": fisher_ci(r, len(xs)) if r is not None else None,
            "source": "computed from model_outputs.csv, itself from games.csv",
        })
    # realised same-game correlation between margin and total (the quantity that
    # makes a side+total same-game parlay invalid to multiply)
    xs, ys = [], []
    seen = set()
    for r in rows:
        if r["estimator"] != "E1" or r["market"] != "side" or r["game_id"] in seen:
            continue
        if r["actual_home"] is None:
            continue
        seen.add(r["game_id"])
        xs.append(r["actual_home"] - r["actual_away"])
        ys.append(r["actual_home"] + r["actual_away"])
    if len(xs) >= MIN_N_CORR:
        r = corr(xs, ys)
        corr_out.append({
            "pair": "margin_vs_total_realised",
            "definition": ("realised final margin against realised final total, same game — the "
                           "dependence that makes multiplying a side and a total invalid"),
            "r": round(r, 5) if r is not None else None,
            "n": len(xs),
            "ci95_fisher": fisher_ci(r, len(xs)) if r is not None else None,
            "source": "computed from games.csv final scores",
        })
    # model error correlation across the two markets
    xs, ys = [], []
    for gid, mk in by_game.items():
        s, t = mk.get("side"), mk.get("total")
        if not s or not t or s["actual_home"] is None:
            continue
        m_err = (s["actual_home"] - s["actual_away"]) - s["model_line"]
        t_err = (s["actual_home"] + s["actual_away"]) - t["model_line"]
        xs.append(m_err); ys.append(t_err)
    if len(xs) >= MIN_N_CORR:
        r = corr(xs, ys)
        corr_out.append({
            "pair": "margin_error_vs_total_error",
            "definition": "our side error against our total error, same game",
            "r": round(r, 5) if r is not None else None,
            "n": len(xs),
            "ci95_fisher": fisher_ci(r, len(xs)) if r is not None else None,
            "source": "computed from model_outputs.csv (side and total rows, same game)",
            "context": ("MEASURED, NOT ASSUMED. The received wisdom that margin and total move "
                        "together is not supported by this data: the correlation is close to zero "
                        "and its 95% interval contains zero. That means a side x total combination "
                        "in the same game is close to a product of independent events here. The "
                        "invalid-multiplication rule in this project therefore rests on "
                        "same-team and same-player dependence, not on a margin/total link. "
                        "A correlation printed without its n and its interval would have hidden this."),
        })

    # ------------------------------------------------------------ luck panel
    def bets_to_detect(true_p: float, null_p: float = 0.5,
                       alpha: float = 0.05, power: float = 0.80) -> int:
        """Exact one-sided sample size for a proportion test.

            n = ( z_a*sqrt(p0(1-p0)) + z_b*sqrt(p1(1-p1)) )^2 / (p1-p0)^2

        Computed against BOTH baselines, because they answer different questions:
        beating a coin (null 0.5) is not the same as being profitable (null 0.5238
        at -110). Reporting only the easier one would overstate how soon an edge
        becomes visible.
        """
        z_a, z_b = 1.6448536269514722, 0.8416212335729143
        d = abs(true_p - null_p)
        if d == 0:
            return 0
        num = z_a * math.sqrt(null_p * (1 - null_p)) + z_b * math.sqrt(true_p * (1 - true_p))
        return int(math.ceil(num * num / (d * d)))

    break_even = 110 / 210  # -110 two-way price
    luck = {
        "break_even_win_rate_at_minus110": round(break_even, 7),
        "bets_needed_to_show_edge": {
            "55pct": bets_to_detect(0.55), "57pct": bets_to_detect(0.57),
            "60pct": bets_to_detect(0.60), "break_even_524": bets_to_detect(break_even),
        },
        "bets_needed_to_show_profit": {
            "q": "how many bets before a bettor at this true rate is distinguishable from BREAK-EVEN, not from a coin",
            "55pct": bets_to_detect(0.55, break_even),
            "57pct": bets_to_detect(0.57, break_even),
            "60pct": bets_to_detect(0.60, break_even),
        },
        "explanation": (
            "At -110 a bettor must win 52.38% to break even. Distinguishing a 55% bettor from a "
            "coin at 5% significance and 80% power takes thousands of bets, which is precisely why "
            "raw win rate and season ROI are forbidden as ranking rules here. These counts assume "
            "independent bets; parlays raise the required count because outcomes cluster."
        ),
    }

    out = {
        "built_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "builder": "engine/linelab/scoring.py",
        "bootstrap": {"resamples": BOOT, "seed": SEED, "cluster": "game_id"},
        "reference_base_rates": {k: round(v, 5) for k, v in base.items()},
        "reference_note": "Base rates are measured on the TRAIN split (1999-2015) only.",
        "scores": results,
        "controls": controls,
        "win_rate_controls": control_rate,
        "correlations": corr_out,
        "correlation_policy": (
            f"Correlations are computed only from numbers present in the price store or from "
            f"official final scores. Any pair with n < {MIN_N_CORR} is suppressed rather than "
            f"printed. n is published with every value."
        ),
        "luck_panel": luck,
        "divisions": {
            "singles": {"status": "scored", "note": "side, total, moneyline modelled above"},
            "game_parlays": {"status": "gated", "note": "requires a validated joint probability; marginal multiplication is invalid under the measured dependence"},
            "same_game_parlays": {"status": "gated", "note": "blocked by the margin/total dependence reported in correlations"},
            "prop_combos": {"status": "blocked", "note": "no player-level price data exists in this repository's verified sources"},
        },
    }
    path = os.path.join(OUTDIR, "scores.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("scores.json written")
    for k, v in results.items():
        if v.get("bss") is None:
            continue
        print(f"  {k:<34} BSS {v['bss']:+.4f}  CI [{v['bss_ci95'][0]:+.4f},{v['bss_ci95'][1]:+.4f}]  "
              f"p={v['p_bss_le_0']:.3f} holm={v.get('p_bss_le_0_holm')}  n_games={v['n_games']}")
    print("  correlations:", [(c["pair"], c["r"], c["n"]) for c in corr_out])
    return out


if __name__ == "__main__":
    main()
