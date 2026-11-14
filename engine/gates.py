"""The gate battery. A strategy must clear every applicable gate to be promoted.

Contract: a gate never returns "pass" on missing evidence. It returns
``unknown`` and the strategy stays unpromotable — which is the same rule the site
uses for table cells (blank + flag, never inferred).
"""
from __future__ import annotations

import math
from typing import Any

from . import config, odds, parlay, stats

PASS, FAIL, UNKNOWN = "pass", "fail", "unknown"


def _res(ok: bool | None, detail: str) -> dict:
    state = UNKNOWN if ok is None else (PASS if ok else FAIL)
    return {"state": state, "detail": detail}


# --------------------------------------------------------------------------- gates
def g01_sample(r: dict) -> dict:
    c = config.GATES["G-01"]
    n = r.get("n_bets")
    if n is None:
        return _res(None, "no graded bet count supplied")
    if n >= c["min_bets"]:
        return _res(True, f"{n} graded bets ≥ {c['min_bets']}")
    seasons = r.get("seasons_observed")
    if seasons is not None and seasons >= c["min_seasons"]:
        return _res(True, f"origination model with {seasons} seasons ≥ {c['min_seasons']}")
    return _res(False, f"{n} graded bets < {c['min_bets']} (seasons observed: {seasons or 'n/a'})")


def g02_edge_over_breakeven(r: dict) -> dict:
    conf = config.GATES["G-02"]["confidence"]
    n, k = r.get("n_bets"), r.get("n_wins")
    be = r.get("p_market_novig")
    if be is None and r.get("odds_line") is not None:
        be = odds.break_even(r["odds_line"])
    if None in (n, k) or be is None:
        return _res(None, "needs n_bets, n_wins and either a de-vigged market prob or a price")
    lo, hi = odds.wilson_interval(k, n, conf)
    rate = k / n
    ok = lo > be
    return _res(ok, f"hit {rate:.4f} [{lo:.4f}, {hi:.4f}] vs break-even {be:.4f} "
                    f"@ {conf:.0%} — {'clears' if ok else 'does not clear'}")


def g03_clv(r: dict) -> dict:
    need = config.GATES["G-03"]["min_share_beat_close"]
    mean, ci_lo, share = r.get("clv_mean"), r.get("clv_ci_low"), r.get("share_beat_close")
    if mean is None or ci_lo is None or share is None:
        return _res(None, "no closing-line-value series (blocked by the missing odds source, FL-014)")
    ok = mean > 0 and ci_lo > 0 and share >= need
    return _res(ok, f"mean CLV {mean:+.4f}, CI lower {ci_lo:+.4f}, beat-close share "
                    f"{share:.1%} (need ≥ {need:.0%})")


def g04_deflation(r: dict) -> dict:
    c = config.GATES["G-04"]
    rets, n_var, var_sr = r.get("returns"), r.get("n_variants"), r.get("sr_variance")
    if not rets or n_var is None or var_sr is None:
        return _res(None, "needs the per-period return series, the variant count from the "
                          "pre-commitment registry, and the dispersion of trial Sharpes")
    d = stats.deflated_sharpe(rets, n_var, var_sr)
    if math.isnan(d["dsr"]):
        return _res(False, d.get("note", "not estimable"))
    ok = d["dsr"] >= c["min_dsr"]
    return _res(ok, f"SR {d['sharpe']:.3f} vs SR* {d['sr_star']:.3f} over {n_var} variants "
                    f"→ DSR {d['dsr']:.3f} (need ≥ {c['min_dsr']})"
                    + (f"; MinTRL {d['min_trl_periods']:.0f} periods = "
                       f"{d['min_trl_multiple_of_sample']:.1f}x the sample we have"
                       if math.isfinite(d["min_trl_periods"]) else
                       "; MinTRL unattainable — the observed SR does not exceed SR*"))


def g05_parsimony(r: dict) -> dict:
    lim = config.GATES["G-05"]["max_free_params"]
    p = r.get("free_params")
    if p is None:
        return _res(None, "free-parameter count not declared")
    if p <= lim:
        return _res(True, f"{p} free parameters ≤ {lim}")
    hold = r.get("holdout_dlogloss_ci_excludes_zero")
    if hold is True:
        return _res(True, f"{p} parameters, every excess justified by a holdout Δlog-loss with CI excluding 0")
    return _res(False, f"{p} free parameters > {lim} and no justified holdout gain")


def g06_walk_forward(r: dict) -> dict:
    c = config.GATES["G-06"]
    folds = r.get("fold_edge_signs")
    if not folds:
        return _res(None, "no fold results")
    agree = sum(1 for s in folds if s > 0)
    ok = agree >= min(c["min_folds_agreeing"], len(folds)) and len(folds) >= c["n_folds"] - 1
    return _res(ok, f"{agree}/{len(folds)} folds positive (need {c['min_folds_agreeing']} of {c['n_folds']})")


def g07_costs(r: dict) -> dict:
    """Cost stress. Default assumes a symmetric two-sided market (both sides at the
    same price), which is the assumption a book's own vig makes for us; pass
    `p_market_novig` when a real multi-book de-vigged price is available."""
    c = config.GATES["G-07"]
    p, line = r.get("p_model"), r.get("odds_line")
    if p is None or line is None:
        return _res(None, "needs our probability and a price to stress")
    be = odds.break_even(line)
    vig = max(0.0, 2.0 * be - 1.0)                      # whole-market overround
    fair = r.get("p_market_novig")                       # the no-vig probability, if we hold one
    if fair is None:
        fair = be - vig / 2.0
    stressed_be = fair + c["vig_multiplier"] * vig / 2.0 + c["slippage_prob"]
    stressed_price = odds.prob_to_american(stressed_be - c["slippage_prob"])
    ev = odds.expected_value(p, stressed_price)
    ok = p > stressed_be and ev > 0
    return _res(ok, f"p_model {p:.4f} vs stressed break-even {stressed_be:.4f} "
                    f"(no-vig {fair:.4f}, {c['vig_multiplier']}× vig "
                    f"{vig / 2:.4f}/side, slippage {c['slippage_prob']:.2f}); "
                    f"EV/unit at the stressed price {stressed_price:+d} = {ev:+.4f}")


def g08_decay(r: dict) -> dict:
    c = config.GATES["G-08"]
    recent, hist = r.get("recent_edge"), r.get("rolling_edges")
    if recent is None or not hist:
        return _res(None, "needs the recent-window edge and the rolling edge history")
    s = sorted(hist)
    idx = max(0, min(len(s) - 1, int(round(c["percentile"] / 100.0 * (len(s) - 1)))))
    floor = s[idx]
    ok = recent >= floor
    return _res(ok, f"last {c['recent_weeks']}w edge {recent:+.4f} vs p{c['percentile']} of history "
                    f"{floor:+.4f} — {'stable' if ok else 'decayed below its own floor'}")


def g09_luck(r: dict) -> dict:
    c = config.GATES["G-09"]
    rets = r.get("returns")
    if not rets:
        return _res(None, "needs the per-period return series")
    b = stats.moving_block_bootstrap_p(rets, block=r.get("block", c["block_size"]),
                                       resamples=c["resamples"], seed=c["seed"])
    perm = stats.sign_flip_permutation_p(rets)
    ok = (not math.isnan(b["p"])) and b["p"] <= c["max_p_null"] and perm["p"] <= c["max_p_null"]
    return _res(ok, f"block-bootstrap p {b['p']:.4f} (block {b.get('block')}, "
                    f"{b['resamples']} resamples); sign-flip p {perm['p']:.4f} [{perm['method']}]; "
                    f"need ≤ {c['max_p_null']}")


def g10_capacity(r: dict) -> dict:
    c = config.GATES["G-10"]
    per_week, mult = r.get("qualifying_bets_per_week"), r.get("handleable_multiple")
    if per_week is None or mult is None:
        return _res(None, "needs the qualifying bet rate and the holdable-stake multiple")
    ok = per_week >= c["min_bets_per_week"] and mult >= c["capacity_multiple"]
    return _res(ok, f"{per_week} qualifying bets/week (need {c['min_bets_per_week']}); "
                    f"handleable stake {mult}× target (need {c['capacity_multiple']}×)")


def g11_exposure(r: dict) -> dict:
    c = config.GATES["G-11"]
    kf, cluster, probs = r.get("kelly_fraction_used"), r.get("cluster_units_exposure"), r.get("cluster_leg_probs")
    if kf is None or cluster is None:
        return _res(None, "needs the Kelly fraction actually used and per-cluster exposure")
    if kf > c["max_kelly_fraction"] or cluster > c["max_cluster_units"]:
        return _res(False, f"Kelly {kf:.3f} (cap {c['max_kelly_fraction']}), cluster {cluster:.2f}u "
                           f"(cap {c['max_cluster_units']}u)")
    dd = stats.p_dd if hasattr(stats, "p_dd") else r.get("drawdown_prob")
    if dd is None and probs:
        dd = parlay.joint_all_lose(probs, r.get("cluster_rho", 0.0))
    if dd is None:
        return _res(None, f"caps respected (Kelly {kf:.3f}, cluster {cluster:.2f}u); no simulated "
                          f"{c['dd_units']}-unit drawdown probability — G-11 cannot be closed")
    return _res(dd <= c["max_dd_prob"], f"p(simultaneous cluster loss) {dd:.3f} vs cap "
                                        f"{c['max_dd_prob']:.0%}")


def g12_book_rules(r: dict) -> dict:
    legs = r.get("legs")
    if not legs:
        return _res(True, "single-leg strategy — no parlay rule applies")
    if any(l.get("same_event") for l in legs) and not r.get("sgp_ticket"):
        return _res(False, "multiple legs from one event outside an SGP-type ticket")
    if not r.get("sgp_ticket") and len({l.get("event") for l in legs}) < len(legs):
        return _res(False, "legs share an event but the ticket is not an SGP")
    if r.get("duplicate_market"):
        return _res(False, "two legs on the same market offered twice — voided by house rules")
    if r.get("correlated_cross_game"):
        return _res(False, "correlated cross-game legs are voided outside SGP/progressive products")
    if not r.get("push_handling_modelled"):
        return _res(None, "push/void handling not modelled; quote is not yet a price")
    return _res(True, f"{len(legs)} legs pass the rule register as quoted "
                      f"({r.get('book_rules_version', 'rules version unrecorded')})")


def g13_asof(r: dict) -> dict:
    c = config.GATES["G-13"]
    ages = r.get("feature_max_age_hours_at_decision")
    if ages is None:
        return _res(None, "no as-of timestamps recorded for the features")
    ok = ages <= c["max_feature_age_hours"]
    return _res(ok, f"oldest feature {ages:.1f}h old at decision time (cap {c['max_feature_age_hours']}h)")


def g14_origination(r: dict) -> dict:
    db, dmae, tail = r.get("brier_delta_vs_baseline"), r.get("mae_delta_vs_baseline"), r.get("tail_degradation_share")
    if db is None:
        return _res(None, "no Brier/log-loss comparison against the frozen baseline v0")
    ok = db < 0 and (dmae is None or dmae < 0) and (tail is None or tail <= 0.05)
    return _res(ok, f"ΔBrier {db:+.5f}, ΔMAE {('n/a' if dmae is None else f'{dmae:+.3f}')} pts, "
                    f"tail degradation {('n/a' if tail is None else f'{tail:.1%}')} (cap 5%)")


def g15_revisions(r: dict) -> dict:
    c = config.GATES["G-15"]
    flip = r.get("revision_sign_flip_share")
    if flip is None:
        return _res(None, "no re-pricing test against post-deadline designations/roster changes")
    ok = flip <= c["max_sign_flip_share"]
    return _res(ok, f"{flip:.1%} of bets change sign when a designation is revised (cap "
                    f"{c['max_sign_flip_share']:.0%})")


def g16_cluster(r: dict) -> dict:
    c = config.GATES["G-16"]
    per = r.get("max_bets_per_cluster")
    if per is None:
        return _res(None, "bets are not stamped with a correlation-cluster id")
    ok = per <= c["max_bets_per_cluster"]
    return _res(ok, f"max {per} simultaneous bets per correlation cluster (cap {c['max_bets_per_cluster']})")


GATE_FUNCS = {
    "G-01": g01_sample, "G-02": g02_edge_over_breakeven, "G-03": g03_clv,
    "G-04": g04_deflation, "G-05": g05_parsimony, "G-06": g06_walk_forward,
    "G-07": g07_costs, "G-08": g08_decay, "G-09": g09_luck, "G-10": g10_capacity,
    "G-11": g11_exposure, "G-12": g12_book_rules, "G-13": g13_asof,
    "G-14": g14_origination, "G-15": g15_revisions, "G-16": g16_cluster,
}


def evaluate(record: dict, applicable: list[str] | None = None) -> dict[str, Any]:
    keys = applicable or list(GATE_FUNCS)
    out = {k: GATE_FUNCS[k](record) for k in keys}
    passed = [k for k, v in out.items() if v["state"] == PASS]
    failed = [k for k, v in out.items() if v["state"] == FAIL]
    unknown = [k for k, v in out.items() if v["state"] == UNKNOWN]
    return {
        "gates": out,
        "passed": passed, "failed": failed, "unknown": unknown,
        "coverage": len(passed) / max(1, len(keys)),
        "promotable": bool(keys) and not failed and not unknown,
        "summary": (f"{len(passed)}/{len(keys)} passed, {len(failed)} failed, "
                    f"{len(unknown)} unknown → "
                    + ("PROMOTABLE" if (keys and not failed and not unknown) else "NOT PROMOTABLE")),
    }


def skill_score(record: dict, verdict: dict, n_bets: int, max_dd_units: float = 0.0) -> float:
    """Leaderboard skill score: validated edge × evidence weight, minus ruin penalty.
    PnL alone never appears — that is the point of the board."""
    unit_edge = record.get("edge_after_cost", 0.0)
    weight = math.log10(max(1, n_bets))
    deflation = verdict["gates"]["G-04"]["state"] == PASS
    penalty = 0.5 * max(0.0, max_dd_units - config.GATES["G-11"]["max_cluster_units"])
    return (unit_edge * weight * verdict["coverage"] * (1.0 if deflation else 0.5)) - penalty
