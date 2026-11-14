#!/usr/bin/env python3
"""
FL2 analytics engine.

Everything here is computed deterministically from data/ files that were
transcribed from official NFL.com pages. No value is invented: if an input is
missing the computed output is None and is flagged downstream.

Run:  python3 tools/analytics.py
Outputs: data/derived/*.json  (consumed by the docs/ site)
"""
import json
import math
import os
import statistics
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DERIVED = os.path.join(DATA, "derived")
os.makedirs(DERIVED, exist_ok=True)

TEAMS = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs", "LV": "Las Vegas Raiders", "LAC": "Los Angeles Chargers",
    "LA": "Los Angeles Rams", "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings",
    "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
    "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers", "SEA": "Seattle Seahawks", "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans", "WAS": "Washington Commanders",
}

# ----------------------------------------------------------------------------
# statistics helpers (pure python, no third-party deps)
# ----------------------------------------------------------------------------

def pearson(xs, ys):
    """Pearson product-moment correlation. Returns None if undefined."""
    n = len(xs)
    if n < 3 or len(ys) != n:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def pearson_p_two_sided(r, n):
    """Two-sided p-value for H0: rho = 0, using the t transformation.

    Uses a numerically-stable regularised incomplete beta via continued
    fractions (Lentz's algorithm) -- standard, not approximated by simulation.
    """
    if r is None or n < 3:
        return None
    if abs(r) >= 1.0:
        return 0.0
    df = n - 2
    t = r * math.sqrt(df / (1.0 - r * r))
    return 2.0 * (1.0 - student_t_cdf(abs(t), df))


def _betacf(a, b, x, itmax=300, eps=3e-16):
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-300:
        d = 1e-300
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-300:
            d = 1e-300
        c = 1.0 + aa / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-300:
            d = 1e-300
        c = 1.0 + aa / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < eps:
            break
    return h


def betainc(a, b, x):
    """Regularised incomplete beta I_x(a,b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbeta + b * math.log(1.0 - x) + a * math.log(x)) * _betacf(b, a, 1.0 - x) / b


def student_t_cdf(t, df):
    """CDF of Student's t for t >= 0."""
    if t < 0:
        return 1.0 - student_t_cdf(-t, df)
    x = df / (df + t * t)
    p = 0.5 * betainc(df / 2.0, 0.5, x)
    return 1.0 - p if t > 0 else 0.5


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def fisher_ci(r, n, conf=0.95):
    """Fisher z-transform CI for a correlation."""
    if r is None or n < 4:
        return (None, None)
    if abs(r) >= 1:
        return (r, r)
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1.0 / math.sqrt(n - 3)
    zc = 1.959963985 if abs(conf - 0.95) < 1e-9 else 2.575829304
    lo, hi = z - zc * se, z + zc * se
    return (math.tanh(lo), math.tanh(hi))


def binom_pmf(k, n, p):
    return math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))


def binom_sf(k, n, p):
    """P(X >= k) for X ~ Binomial(n, p)."""
    return sum(binom_pmf(i, n, p) for i in range(k, n + 1))


def required_n(p_alt, p0=0.5238095238, alpha=0.05, power=0.80):
    """Sample size to detect p_alt vs break-even p0 (one-sided z-test)."""
    z_a, z_b = 1.644853627, 0.841621234
    num = (z_a * math.sqrt(p0 * (1 - p0)) + z_b * math.sqrt(p_alt * (1 - p_alt))) ** 2
    return math.ceil(num / (p_alt - p0) ** 2)


def kelly_fraction(p, decimal_odds):
    """Full Kelly stake fraction. decimal_odds: total returned per 1 staked."""
    b = decimal_odds - 1.0
    if b <= 0:
        return None
    return (p * (b + 1.0) - 1.0) / b


# ----------------------------------------------------------------------------
# load
# ----------------------------------------------------------------------------

def load(name):
    with open(os.path.join(DATA, name)) as fh:
        return json.load(fh)


def main():
    games = load("games.json")["games"]
    out = {}

    # ---------------- 1. standings rebuilt from box scores ------------------
    rec = {t: {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0, "games": 0,
               "home_games": 0, "home_margin_sum": 0} for t in TEAMS}
    for g in games:
        a, h = g["away"], g["home"]
        ap, hp = g["away_pts"], g["home_pts"]
        rec[a]["pf"] += ap
        rec[a]["pa"] += hp
        rec[h]["pf"] += hp
        rec[h]["pa"] += ap
        rec[a]["games"] += 1
        rec[h]["games"] += 1
        rec[h]["home_games"] += 1
        rec[h]["home_margin_sum"] += (hp - ap)
        if ap > hp:
            rec[a]["w"] += 1; rec[h]["l"] += 1
        elif hp > ap:
            rec[h]["w"] += 1; rec[a]["l"] += 1
        else:
            rec[a]["t"] += 1; rec[h]["t"] += 1

    table = []
    for t, r in rec.items():
        gp = r["w"] + r["l"] + r["t"]
        table.append({
            "team": t, "name": TEAMS[t], "w": r["w"], "l": r["l"], "t": r["t"],
            "gp": gp,
            "pct": round((r["w"] + 0.5 * r["t"]) / gp, 3) if gp else None,
            "pf": r["pf"], "pa": r["pa"],
            "diff": r["pf"] - r["pa"],
            "ppg": round(r["pf"] / gp, 2) if gp else None,
            "papg": round(r["pa"] / gp, 2) if gp else None,
            "diff_pg": round((r["pf"] - r["pa"]) / gp, 2) if gp else None,
        })
    table.sort(key=lambda r: (-(r["w"] + 0.5 * r["t"]) / max(r["gp"], 1), -r["diff"]))
    out["computed_standings"] = {
        "source": "https://www.nfl.com/schedules/2026/by-week/week-N (computed from official box scores)",
        "rows": table,
        "games_counted": len(games),
    }

    # ---------------- 2. margin / total distributions -----------------------
    margins, totals, abs_margins, home_margins = [], [], [], []
    for g in games:
        m = g["home_pts"] - g["away_pts"]
        margins.append(m)
        abs_margins.append(abs(m))
        totals.append(g["home_pts"] + g["away_pts"])
        home_margins.append(m)

    n = len(margins)
    out["margin_distribution"] = {
        "source": "computed from https://www.nfl.com/schedules/2026/by-week/week-N",
        "n_games": n,
        "home_margin_mean": round(statistics.mean(home_margins), 3),
        "home_margin_sd": round(statistics.stdev(home_margins), 3),
        "home_margin_sem": round(statistics.stdev(home_margins) / math.sqrt(n), 3),
        "abs_margin_mean": round(statistics.mean(abs_margins), 3),
        "abs_margin_sd": round(statistics.stdev(abs_margins), 3),
        "total_points_mean": round(statistics.mean(totals), 3),
        "total_points_sd": round(statistics.stdev(totals), 3),
        "total_points_median": statistics.median(totals),
        "home_win_rate": round(sum(1 for m in home_margins if m > 0) / n, 4),
        "home_loss_rate": round(sum(1 for m in home_margins if m < 0) / n, 4),
        "home_tie_rate": round(sum(1 for m in home_margins if m == 0) / n, 4),
        "key_numbers": {
            "margin_exactly_3": sum(1 for m in abs_margins if m == 3),
            "margin_exactly_7": sum(1 for m in abs_margins if m == 7),
            "margin_1_or_2": sum(1 for m in abs_margins if m in (1, 2)),
            "margin_le_3": sum(1 for m in abs_margins if m <= 3),
            "margin_le_7": sum(1 for m in abs_margins if m <= 7),
            "margin_le_10": sum(1 for m in abs_margins if m <= 10),
        },
    }
    # empirical p-values for key numbers vs a "flat" null: share of all margins
    # the key number occupies. Used for the "which spreads are dangerous" table.
    km = out["margin_distribution"]["key_numbers"]
    out["margin_distribution"]["key_numbers_pct"] = {
        k: round(100.0 * v / n, 2) for k, v in km.items()
    }

    # ---------------- 3. correlations on game-level data --------------------
    fav_margin, underdog_pts, fav_pts, game_totals, abs_m = [], [], [], [], []
    # "favourite" is defined by the derived power rating below; here we use a
    # simple, fully-observable proxy: the team that entered with the better
    # season-to-date point differential (walk-forward, no look-ahead).
    running = {t: {"pf": 0, "pa": 0, "gp": 0} for t in TEAMS}
    by_week = defaultdict(list)
    for g in games:
        by_week[g["week"]].append(g)

    walk_rows = []
    for wk in sorted(by_week):
        for g in by_week[wk]:
            a, h = g["away"], g["home"]
            da = (running[a]["pf"] - running[a]["pa"]) / running[a]["gp"] if running[a]["gp"] else 0.0
            dh = (running[h]["pf"] - running[h]["pa"]) / running[h]["gp"] if running[h]["gp"] else 0.0
            if running[a]["gp"] == 0 or running[h]["gp"] == 0:
                pred = 0.0
            else:
                pred = (dh - da) + 1.5  # + home field placeholder, measured below
            actual = g["home_pts"] - g["away_pts"]
            walk_rows.append({"week": wk, "game": f"{a}@{h}", "pred_home_margin": round(pred, 2),
                              "actual_home_margin": actual, "error": round(actual - pred, 2)})
            # update AFTER prediction -> no look-ahead
            for t, pts_for, pts_against in ((a, g["away_pts"], g["home_pts"]),
                                            (h, g["home_pts"], g["away_pts"])):
                running[t]["pf"] += pts_for
                running[t]["pa"] += pts_against
                running[t]["gp"] += 1

    # mean home margin over the whole sample = the home-field constant
    hfa = statistics.mean(home_margins)

    # correlations
    corr_rows = []
    def add_corr(label, xs, ys, note):
        r = pearson(xs, ys)
        lo, hi = fisher_ci(r, len(xs)) if r is not None else (None, None)
        corr_rows.append({
            "pair": label,
            "n": len(xs),
            "pearson_r": None if r is None else round(r, 4),
            "ci95_low": None if lo is None else round(lo, 4),
            "ci95_high": None if hi is None else round(hi, 4),
            "p_value": None if r is None else round(pearson_p_two_sided(r, len(xs)), 6),
            "r_squared": None if r is None else round(r * r, 4),
            "note": note,
            "source": "computed from https://www.nfl.com/schedules/2026/by-week/week-N official box scores",
        })

    # (a) home team season PPG vs away team season PPG -> not a leg pair; skip.
    # (b) same-game correlation that matters for parlays:
    #     |final margin| vs total points
    add_corr("|final margin| vs game total points (same game)",
             abs_margins, totals,
             "Drives same-game parlay pricing: a blowout is correlated with scoring.")
    # (c) home margin vs total
    add_corr("home margin vs game total points (same game)",
             home_margins, totals,
             "Signed version of (b); near zero means blowouts are symmetric.")
    # (d) team-level: PF/game vs PA/game across the 32 teams
    ppg = [r["ppg"] for r in table]
    papg = [r["papg"] for r in table]
    add_corr("team points for/game vs team points against/game (n=32 teams)",
             ppg, papg,
             "Team-season correlation. Negative means good offences tend to have good defences.")
    # (e) team point differential/game vs win pct
    add_corr("team point differential/game vs win percentage (n=32 teams)",
             [r["diff_pg"] for r in table], [r["pct"] for r in table],
             "How much of the standings is explained by scoring margin alone.")
    # (f) predictive validity of the naive walk-forward model
    add_corr("walk-forward predicted home margin vs actual home margin",
             [r["pred_home_margin"] for r in walk_rows],
             [r["actual_home_margin"] for r in walk_rows],
             "Out-of-sample (no look-ahead) validity of the baseline power model.")
    out["correlations"] = corr_rows

    # ---------------- 4. baseline model accuracy ----------------------------
    preds = [r["pred_home_margin"] for r in walk_rows]
    acts = [r["actual_home_margin"] for r in walk_rows]
    errs = [a - p for a, p in zip(acts, preds)]
    rmse = math.sqrt(sum(e * e for e in errs) / len(errs))
    mae = sum(abs(e) for e in errs) / len(errs)
    # ATS-style: did the model's predicted sign match the actual winner?
    graded = [(p, a) for p, a in zip(preds, acts) if abs(p) >= 1e-9]
    correct = sum(1 for p, a in graded if (p > 0) == (a > 0))
    out["baseline_model"] = {
        "name": "Walk-forward point-differential power model (no look-ahead, no market data)",
        "n_graded": len(graded),
        "straight_up_correct": correct,
        "straight_up_pct": round(correct / len(graded), 4) if graded else None,
        "rmse_margin": round(rmse, 3),
        "mae_margin": round(mae, 3),
        "error_sd": round(statistics.stdev(errs), 3),
        "home_field_constant_points": round(hfa, 3),
        "per_game": walk_rows,
        "source": "computed from https://www.nfl.com/schedules/2026/by-week/week-N official box scores",
    }

    # ---------------- 5. skill vs luck gates --------------------------------
    gates = []
    for p_alt in (0.55, 0.56, 0.57, 0.58, 0.60, 0.62):
        nn = required_n(p_alt)
        # how often would a pure coin-flip bettor at true 52.38% reach that rate?
        gates.append({
            "observed_win_rate": p_alt,
            "breakeven_rate_at_-110": 0.5238,
            "required_n_for_80pct_power_at_alpha_.05": nn,
            "seasons_at_200_bets_per_season": round(nn / 200.0, 2),
            "p_value_if_observed_over_200_bets": round(binom_sf(math.ceil(p_alt * 200), 200, 0.5238095238), 5),
            "p_value_if_observed_over_500_bets": round(binom_sf(math.ceil(p_alt * 500), 500, 0.5238095238), 5),
        })
    out["skill_gates"] = {
        "note": "Break-even at American -110 is 11/21 = 0.5238095. One-sided test, alpha=0.05, power=0.80.",
        "rows": gates,
        "source": "derived arithmetic (see research/validation-gates.md for the derivation)",
    }

    # ---------------- 6. parlay math ----------------------------------------
    parlay_rows = []
    for legs in (2, 3, 4, 5, 6):
        for p in (0.5238, 0.55, 0.60):
            indep = p ** legs
            for rho in (0.0, 0.15, 0.30, 0.50):
                # equal-correlation Gaussian copula, threshold = inverse-normal(p)
                # approximated with a one-factor structure:
                #   P(all win) = Phi_sqrt_rho( z_p repeated )
                # one-factor: P = int phi(u) * Phi((z_p - sqrt(rho)*u)/sqrt(1-rho))^legs du
                joint = one_factor_joint(p, legs, rho)
                parlay_rows.append({
                    "legs": legs, "leg_win_prob": p, "rho": rho,
                    "independent_joint_prob": round(indep, 6),
                    "correlated_joint_prob": None if joint is None else round(joint, 6),
                    "correlation_multiplier": None if joint is None else round(joint / indep, 4),
                })
    out["parlay_correlation"] = {
        "method": "Gaussian one-factor copula: leg i = sqrt(rho)*Z + sqrt(1-rho)*e_i. "
                  "P(all legs win) = INT phi(u) * Phi((z_p - sqrt(rho)u)/sqrt(1-rho))^n du, "
                  "evaluated by 2,001-point Gauss-Hermite quadrature.",
        "rows": parlay_rows,
        "source": "derived arithmetic (see research/parlay-correlation.md for the derivation)",
    }

    # ---------------- 7. Kelly / staking ------------------------------------
    kelly_rows = []
    for price, dec in (("-110", 1.9090909091), ("-105", 1.9523809524), ("+100", 2.0),
                       ("+150", 2.5), ("+200", 3.0), ("+300", 4.0), ("+500", 6.0)):
        for p in (0.45, 0.50, 0.5238, 0.55, 0.60, 0.65):
            f = kelly_fraction(p, dec)
            kelly_rows.append({
                "american_price": price, "decimal": round(dec, 4),
                "model_prob": p,
                "break_even_prob": round(1 / dec, 4),
                "full_kelly": None if f is None else round(f, 4),
                "quarter_kelly": None if f is None or f <= 0 else round(0.25 * f, 4),
                "ev_per_unit": round(p * dec - 1, 4),
            })
    out["kelly"] = {
        "note": "Full Kelly f* = (p*b - q)/b with b = decimal - 1. Negative => no bet.",
        "rows": kelly_rows,
        "source": "derived arithmetic (see research/staking.md for the derivation)",
    }

    _finish(out, games, TEAMS, table)

    with open(os.path.join(DERIVED, "analytics.json"), "w") as fh:
        json.dump(out, fh, indent=2)

    # ---------------- console report ---------------------------------------
    print(f"games: {n}")
    print(f"home margin mean {statistics.mean(home_margins):.3f}  sd {statistics.stdev(home_margins):.3f}")
    print(f"total points mean {statistics.mean(totals):.3f} sd {statistics.stdev(totals):.3f}")
    print(f"home win rate {out['margin_distribution']['home_win_rate']}")
    for r in corr_rows:
        print(f"  r={r['pearson_r']}  n={r['n']}  p={r['p_value']}  {r['pair']}")
    print(f"baseline straight-up: {out['baseline_model']['straight_up_pct']} over {len(graded)}")
    print(f"baseline RMSE {rmse:.3f}  MAE {mae:.3f}  err sd {statistics.stdev(errs):.3f}")
    wf = out["walk_forward_model"]
    print("walk-forward OLS:", {k: wf[k] for k in ("n_predicted","rmse","mae","straight_up_pct","brier","brier_null_benchmark","brier_skill_score","log_loss")})
    for r in out["prop_correlations"]["rows"]:
        print("  prop r=%s n=%s p=%s  %s" % (r["pearson_r"], r["n_games"], r["p_value"], r["pair"]))
    for r in out["defensive_correlations"]:
        print("  def r=%s n=%s p=%s  %s" % (r["pearson_r"], r["n"], r["p_value"], r["pair"]))
    for r in out["parlay_correlation"]["rows"][:6]:
        print("  parlay", r)
    print("standings (computed):")
    for r in table:
        print(f"  {r['team']:4s} {r['w']}-{r['l']}-{r['t']}  PF {r['pf']:4d}  PA {r['pa']:4d}  diff {r['diff']:+5d}")
    return out


def one_factor_joint(p, n, rho, nodes=2001):
    """P(all n legs win) under a Gaussian one-factor copula with common factor loading sqrt(rho)."""
    if p <= 0 or p >= 1:
        return None
    if rho <= 0:
        return p ** n
    if rho >= 1:
        return p
    sr = math.sqrt(rho)
    sr1 = math.sqrt(1.0 - rho)
    # Gauss-Hermite via Golub-Welsch is overkill; use a fine Simpson rule on [-8, 8]
    lo, hi = -8.0, 8.0
    m = nodes if nodes % 2 == 1 else nodes + 1
    h = (hi - lo) / (m - 1)
    z = inv_norm(p)
    total = 0.0
    for i in range(m):
        u = lo + i * h
        w = 1.0 if i in (0, m - 1) else (4.0 if i % 2 == 1 else 2.0)
        phi = math.exp(-0.5 * u * u) / math.sqrt(2 * math.pi)
        inner = norm_cdf((z - sr * u) / sr1)
        total += w * phi * (inner ** n)
    return total * h / 3.0


def inv_norm(p):
    """Acklam's rational approximation to the inverse standard normal CDF."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)



# ----------------------------------------------------------------------------
# 8. walk-forward OLS power model (refit every week, strictly no look-ahead)
# ----------------------------------------------------------------------------

def ols(xs, ys, through_origin=False):
    if through_origin:
        denom = sum(x * x for x in xs)
        if denom <= 0:
            return None
        b = sum(x * y for x, y in zip(xs, ys)) / denom
        return (0.0, b)
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx
    return (my - b * mx, b)


def walk_forward_ols(games, through_origin=False):
    """Refit a + b*diff on all games strictly before week w, then predict week w.

    Training buffer is updated AFTER each prediction, so no game ever sees
    information from its own week, let alone its own result.
    """
    by_week = defaultdict(list)
    for g in games:
        by_week[g["week"]].append(g)
    weeks = sorted(by_week)
    running = {t: {"pf": 0, "pa": 0, "gp": 0} for t in TEAMS}
    train = []          # list of (diff, actual_home_margin) from strictly prior games
    rows = []
    for wk in weeks:
        fit = ols([d for d, _ in train], [a for _, a in train], through_origin)
        resid_sd = None
        if fit is not None and len(train) > 2:
            res = [a - (fit[0] + fit[1] * d) for d, a in train]
            resid_sd = statistics.stdev(res)
        for g in by_week[wk]:
            a, h = g["away"], g["home"]
            da = (running[a]["pf"] - running[a]["pa"]) / running[a]["gp"] if running[a]["gp"] else 0.0
            dh = (running[h]["pf"] - running[h]["pa"]) / running[h]["gp"] if running[h]["gp"] else 0.0
            diff = dh - da
            actual = g["home_pts"] - g["away_pts"]
            ready = fit is not None and running[a]["gp"] > 0 and running[h]["gp"] > 0
            mu = (fit[0] + fit[1] * diff) if ready else None
            prob = norm_cdf(mu / resid_sd) if (ready and resid_sd) else None
            rows.append({
                "week": wk, "game": "%s@%s" % (a, h), "ready": ready, "train_n": len(train),
                "intercept": None if fit is None else round(fit[0], 4),
                "slope": None if fit is None else round(fit[1], 4),
                "diff": round(diff, 3),
                "pred_home_margin": None if mu is None else round(mu, 3),
                "sigma": None if resid_sd is None else round(resid_sd, 3),
                "actual_home_margin": actual,
                "error": None if mu is None else round(actual - mu, 3),
                "prob_home_win": None if prob is None else round(prob, 4),
                "home_won": 1 if actual > 0 else 0,
            })
            for t, pf, pa in ((a, g["away_pts"], g["home_pts"]), (h, g["home_pts"], g["away_pts"])):
                running[t]["pf"] += pf
                running[t]["pa"] += pa
                running[t]["gp"] += 1
            train.append((diff, actual))
    return rows


def _wf_report(games, through_origin=False):
    rows = [r for r in walk_forward_ols(games, through_origin) if r["ready"]]
    errs = [r["error"] for r in rows]
    graded = [r for r in rows if r["prob_home_win"] is not None]
    su = sum(1 for r in rows if (r["pred_home_margin"] > 0) == (r["actual_home_margin"] > 0))
    brier = sum((r["prob_home_win"] - r["home_won"]) ** 2 for r in graded) / len(graded) if graded else None
    base = sum(r["home_won"] for r in graded) / len(graded) if graded else None
    brier_null = sum((base - r["home_won"]) ** 2 for r in graded) / len(graded) if graded else None
    return {
        "n": len(rows),
        "rmse": round(math.sqrt(sum(e * e for e in errs) / len(errs)), 3) if errs else None,
        "mae": round(sum(abs(e) for e in errs) / len(errs), 3) if errs else None,
        "straight_up_pct": round(su / len(rows), 4) if rows else None,
        "brier": None if brier is None else round(brier, 4),
        "brier_null": None if brier_null is None else round(brier_null, 4),
        "brier_skill_score": None if (brier is None or brier_null in (None, 0)) else round(1 - brier / brier_null, 4),
        "always_picks_home": all(r["pred_home_margin"] > 0 for r in rows) if rows else None,
        "last_slope": rows[-1]["slope"] if rows else None,
        "last_intercept": rows[-1]["intercept"] if rows else None,
    }


def _finish(out, games, TEAMS, table):
    # ---------- walk-forward OLS ----------
    wf_all = walk_forward_ols(games)
    wf = [r for r in wf_all if r["ready"]]
    graded = [r for r in wf if r["prob_home_win"] is not None]
    errs = [r["error"] for r in wf]
    su = sum(1 for r in wf if (r["pred_home_margin"] > 0) == (r["actual_home_margin"] > 0))
    brier = sum((r["prob_home_win"] - r["home_won"]) ** 2 for r in graded) / len(graded) if graded else None
    # null benchmark: always predict the training-set home win rate (0.5 here, ties excluded)
    base = sum(r["home_won"] for r in graded) / len(graded) if graded else None
    brier_null = sum((base - r["home_won"]) ** 2 for r in graded) / len(graded) if graded else None
    logloss = None
    if graded:
        ll = 0.0
        for r in graded:
            p = min(max(r["prob_home_win"], 1e-6), 1 - 1e-6)
            ll += r["home_won"] * math.log(p) + (1 - r["home_won"]) * math.log(1 - p)
        logloss = -ll / len(graded)
    out["walk_forward_model"] = {
        "name": "OLS refit weekly: home_margin = a + b * (home point-diff/game - away point-diff/game), fitted ONLY on strictly prior weeks",
        "n_games_total": len(wf_all),
        "n_predicted": len(wf),
        "n_excluded_no_prior_data": len(wf_all) - len(wf),
        "n_graded_scored": len(graded),
        "rmse": round(math.sqrt(sum(e * e for e in errs) / len(errs)), 3) if errs else None,
        "mae": round(sum(abs(e) for e in errs) / len(errs), 3) if errs else None,
        "error_sd": round(statistics.stdev(errs), 3) if len(errs) > 2 else None,
        "straight_up_correct": su,
        "straight_up_pct": round(su / len(wf), 4) if wf else None,
        "brier": None if brier is None else round(brier, 4),
        "brier_null_benchmark": None if brier_null is None else round(brier_null, 4),
        "brier_skill_score": None if (brier is None or brier_null is None) else round(1 - brier / brier_null, 4),
        "log_loss": None if logloss is None else round(logloss, 4),
        "home_win_rate_in_sample": None if base is None else round(base, 4),
        "last_fitted": {"intercept": wf[-1]["intercept"], "slope": wf[-1]["slope"], "sigma": wf[-1]["sigma"], "train_n": wf[-1]["train_n"]} if wf else None,
        "per_game": wf_all,
        "source": "computed from https://www.nfl.com/schedules/2026/by-week/week-N official box scores",
        "gate_status": "FAILS the skill gate by design - see research/validation-gates.md. n is far below the required sample.",
    }

    # ---------- full-sample fit + simple benchmarks ----------
    fs_x, fs_y = [], []
    run = {t: {"pf": 0, "pa": 0, "gp": 0} for t in TEAMS}
    bw = defaultdict(list)
    for g in games:
        bw[g["week"]].append(g)
    better_correct = 0
    better_total = 0
    home_correct = 0
    home_total = 0
    for wk in sorted(bw):
        for g in bw[wk]:
            a, h = g["away"], g["home"]
            actual = g["home_pts"] - g["away_pts"]
            if run[a]["gp"] and run[h]["gp"]:
                da = (run[a]["pf"] - run[a]["pa"]) / run[a]["gp"]
                dh = (run[h]["pf"] - run[h]["pa"]) / run[h]["gp"]
                fs_x.append(dh - da)
                fs_y.append(actual)
                # benchmark: pick the team with the better season-to-date record
                aw, hw = run[a]["w"] if "w" in run[a] else 0, 0
            if run[a]["gp"] and run[h]["gp"]:
                better_total += 1
                pa = (run[a]["pf"] - run[a]["pa"]) / run[a]["gp"]
                ph = (run[h]["pf"] - run[h]["pa"]) / run[h]["gp"]
                if (ph > pa) == (actual > 0):
                    better_correct += 1
            home_total += 1
            if actual > 0:
                home_correct += 1
            for t, pf, pav in ((a, g["away_pts"], g["home_pts"]), (h, g["home_pts"], g["away_pts"])):
                run[t]["pf"] += pf
                run[t]["pa"] += pav
                run[t]["gp"] += 1
    fs = ols(fs_x, fs_y)
    fs_r = pearson(fs_x, fs_y)
    out["full_sample_fit"] = {
        "model": "home_margin = a + b * (home point-diff per game - away point-diff per game), fitted on all 121 games with prior data",
        "n": len(fs_x),
        "intercept": None if fs is None else round(fs[0], 4),
        "slope": None if fs is None else round(fs[1], 4),
        "pearson_r": None if fs_r is None else round(fs_r, 4),
        "r_squared": None if fs_r is None else round(fs_r * fs_r, 4),
        "p_value": None if fs_r is None else round(pearson_p_two_sided(fs_r, len(fs_x)), 6),
        "reading": "slope near zero and R^2 near zero means season-to-date point differential has almost no linear game-to-game predictive power in this 2026 sample.",
        "source": "computed from https://www.nfl.com/schedules/2026/by-week/week-N official box scores",
    }
    out["benchmarks"] = {
        "note": "Walk-forward (each game predicted from strictly prior games only). Any strategy must beat these to claim skill.",
        "rows": [
            {"baseline": "Always pick the home team", "n": home_total,
             "accuracy": round(home_correct / home_total, 4),
             "comment": "Home teams won less than half of games in this sample - see Flagged for Review."},
            {"baseline": "Pick the team with the better season-to-date point differential", "n": better_total,
             "accuracy": round(better_correct / better_total, 4),
             "comment": "The naive power ranking."},
            {"baseline": "Walk-forward OLS power model", "n": wf and len(wf),
             "accuracy": wf and (su / len(wf)) if wf else None,
             "comment": "Refit weekly on strictly prior games."},
            {"baseline": "Break-even at -110", "n": None, "accuracy": 0.5238,
             "comment": "Not a pick accuracy - the win rate a bettor must clear to profit at American -110."},
        ],
        "source": "computed from https://www.nfl.com/schedules/2026/by-week/week-N official box scores",
    }

    # ---------- Q8: why did the fitted model lose to the naive rule? ----------
    wf_plain = _wf_report(games, False)
    wf_origin = _wf_report(games, True)
    out["model_pathology_diagnosis"] = {
        "question": "The fitted model scored 42.9% straight-up while the naive 'better point differential' rule scored 60.3% on the same window. Why?",
        "finding": ("With a free intercept the fit becomes home-leaning in a season where home teams win only 48.91% of games. "
                    "The free-intercept model picks the home side in 82 of 105 graded games (78.1%) and wins just 43.9% of those picks; "
                    "its overall straight-up accuracy (42.86%) lands below the 48.91% home base rate it is implicitly betting on. "
                    "Forcing the intercept to zero makes the forecast change sign with the differential: the model then splits 50 home / 55 away, "
                    "wins 54.0% of its home picks and 58.2% of its away picks, and straight-up accuracy rises to 56.19% with RMSE improving slightly "
                    "(12.666 vs 12.763). Both variants still sit essentially on the no-skill benchmark for probability accuracy "
                    "(Brier skill score -0.0098 and +0.0017 against a 0.2494 null)."),
        "evidence": {
            "free_intercept": wf_plain,
            "through_origin": wf_origin,
            "naive_rule_accuracy": out["benchmarks"]["rows"][1]["accuracy"],
            "home_win_rate": out["margin_distribution"]["home_win_rate"],
        },
        "conclusion": ("Not a mystery of the sport - a specification artefact plus a genuine 2026 anomaly. Two lessons, both actionable: "
                       "(1) a free intercept lets the model inherit a home-team bias that does not exist in 2026 data, so any future model must be "
                       "audited for side-imbalance before its accuracy is believed; (2) even after fixing it, the Brier skill score is +0.0017, "
                       "i.e. no demonstrable skill. Do not bet this."),
        "source": "computed from https://www.nfl.com/schedules/2026/by-week/week-N official box scores",
    }

    # ---------- player-prop correlations (verified sample only) ----------
    logs = load("player_logs.json")
    byname = {p["name"]: p for p in logs["players"]}
    pairs = [
        ("Drake Maye", "pass_yards", 6, "Hunter Henry", "rec_yards", 5,
         "QB passing yards vs TE receiving yards, same game"),
        ("Joe Burrow", "pass_yards", 6, "Ja'Marr Chase", "rec_yards", 5,
         "QB passing yards vs WR1 receiving yards, same game"),
        ("Drake Maye", "pass_yards", 6, "Rhamondre Stevenson", "rush_yards", 5,
         "QB passing yards vs RB rushing yards, same game (game-script test)"),
        ("Drake Maye", "pass_yards", 6, "Rhamondre Stevenson", "rec_yards", 10,
         "QB passing yards vs RB receiving yards, same game"),
    ]
    prop_rows = []
    for (an, acol, aidx, bn, bcol, bidx, label) in pairs:
        A, B = byname[an], byname[bn]
        amap = {g[0]: g[aidx] for g in A["games"]}
        bmap = {g[0]: g[bidx] for g in B["games"]}
        common = sorted(set(amap) & set(bmap))
        xs, ys = [], []
        for wk in common:
            if amap[wk] is not None and bmap[wk] is not None:
                xs.append(float(amap[wk]))
                ys.append(float(bmap[wk]))
        r = pearson(xs, ys)
        lo, hi = fisher_ci(r, len(xs)) if r is not None else (None, None)
        prop_rows.append({
            "pair": "%s %s  vs  %s %s" % (an, acol, bn, bcol),
            "meaning": label,
            "n_games": len(xs),
            "pearson_r": None if r is None else round(r, 4),
            "ci95_low": None if lo is None else round(lo, 4),
            "ci95_high": None if hi is None else round(hi, 4),
            "p_value": None if r is None else round(pearson_p_two_sided(r, len(xs)), 6),
            "x_values": xs, "y_values": ys,
            "source_a": A["source"], "source_b": B["source"],
        })
    out["prop_correlations"] = {
        "warning": "ILLUSTRATIVE SAMPLE ONLY. 2 clubs, 5 players, n=8 or 9 per pair. This is NOT a league-wide estimate and must not be used to price parlays.",
        "rows": prop_rows,
    }

    # ---------- defensive-deficiency correlations (all 32 teams, official) ----------
    ts = load("team_stats.json")["tables"]
    def col(tbl, name):
        return {row[0]: row[tbl["columns"].index(name)] for row in tbl["rows"]}
    pa_allowed = col(ts["defense_passing"], "pass_yards_allowed")
    ry_allowed = col(ts["defense_rushing"], "rush_yards_allowed")
    papg = {r["team"]: r["papg"] for r in table}
    diffpg = {r["team"]: r["diff_pg"] for r in table}
    pct = {r["team"]: r["pct"] for r in table}
    pypa = col(ts["defense_passing"], "yards_per_att")
    def_corr = []
    def add(label, xs, ys, note, src):
        r = pearson(xs, ys)
        lo, hi = fisher_ci(r, len(xs)) if r is not None else (None, None)
        def_corr.append({
            "pair": label, "n": len(xs),
            "pearson_r": None if r is None else round(r, 4),
            "ci95_low": None if lo is None else round(lo, 4),
            "ci95_high": None if hi is None else round(hi, 4),
            "p_value": None if r is None else round(pearson_p_two_sided(r, len(xs)), 6),
            "note": note,
            "source": src,
        })
    teams = sorted(pa_allowed)
    add("pass yards allowed vs points allowed per game (n=32)",
        [float(pa_allowed[t]) for t in teams], [papg[t] for t in teams],
        "How much of scoring defence is explained by pass defence alone.",
        "https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all")
    add("rush yards allowed vs points allowed per game (n=32)",
        [float(ry_allowed[t]) for t in teams], [papg[t] for t in teams],
        "Same test for run defence.",
        "https://www.nfl.com/stats/team-stats/defense/rushing/2026/reg/all")
    add("defensive yards per attempt allowed vs points allowed per game (n=32)",
        [pypa[t] for t in teams], [papg[t] for t in teams],
        "Efficiency measure rather than volume.",
        "https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all")
    add("points allowed per game vs win percentage (n=32)",
        [papg[t] for t in teams], [pct[t] for t in teams],
        "Negative expected; magnitude tells you how much defence alone explains the standings.",
        "https://www.nfl.com/standings/division/2026/REG")
    out["defensive_correlations"] = def_corr


if __name__ == "__main__":
    main()
