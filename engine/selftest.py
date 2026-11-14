"""Self-tests + the numbers the site publishes as "computed (ours)".

Run:  python3 -m engine.selftest
Every assertion below is either (a) an identity a reader can check with a
calculator, or (b) a property of our own code. Nothing here asserts anything about
the betting market — no prices, no holds, no results.
"""
from __future__ import annotations

import math
from statistics import NormalDist

from . import config, gates, odds, parlay, registry, stats

_N = NormalDist()
FAILURES: list[str] = []


def check(name: str, got, want, tol=1e-9) -> None:
    ok = (abs(got - want) <= tol) if isinstance(want, float) else (got == want)
    if not ok:
        FAILURES.append(f"{name}: got {got!r}, expected {want!r}")
    print(f"  [{'ok' if ok else 'FAIL'}] {name}: {got}")


def close(name: str, got: float, pred: float, tol=1e-6) -> None:
    ok = abs(got - pred) <= tol
    if not ok:
        FAILURES.append(f"{name}: got {got!r}, predicted {pred!r} (±{tol})")
    print(f"  [{'ok' if ok else 'FAIL'}] {name}: {got:.6f} (predicted {pred:.6f})")


def test_odds():
    print("\n1. odds, vig and break-even")
    check("decimal(-110)", round(odds.american_to_decimal(-110), 9), 1.909090909, 1e-9)
    check("implied(-110)", round(odds.american_to_implied(-110), 9), 0.523809524, 1e-9)
    check("round-trip price +150", odds.prob_to_american(1 / odds.american_to_decimal(150)), 150)
    check("break-even(-110)", round(odds.break_even(-110), 9), 0.523809524, 1e-9)
    check("break-even(+120)", round(odds.break_even(120), 9), 0.454545455, 1e-9)
    dv = odds.devig_multiplicative([-110, -110])
    check("de-vig of a -110/-110 market[0]", round(dv[0], 9), 0.5, 1e-9)
    close("market vig on -110/-110", odds.vig_share([-110, -110]) * 100, 4.5454545, 1e-5)
    close("sum of de-vigged probs", sum(dv), 1.0, 1e-12)
    close("EV/unit at p=0.55 vs -110", odds.expected_value(0.55, -110), 0.05, 1e-12)
    close("full Kelly at p=0.55 vs -110", (0.909090909 * 0.55 - 0.45) / 0.909090909, 0.055, 1e-6)
    close("quarter Kelly stake", odds.kelly_fraction(0.55, -110, 0.25), 0.01375, 1e-5)
    check("price we would quote for p=0.55", odds.prob_to_american(0.55), -122)


def test_ci_and_sample():
    print("\n2. confidence intervals and the sample size luck demands")
    lo, hi = odds.wilson_interval(58, 100, 0.90)
    print(f"  58% on 100 bets -> 90% Wilson [{lo:.4f}, {hi:.4f}]; break-even 0.5238")
    check("58% on 100 bets fails the break-even test", lo < 0.523809524, True)
    lo200, _ = odds.wilson_interval(116, 200, 0.90)
    print(f"  58% on 200 bets -> [{lo200:.4f}, …] (still short)")
    n2 = odds.min_bets_to_beat_break_even(0.55, 0.523809524, 0.90)
    n3 = odds.min_bets_to_beat_break_even(0.58, 0.523809524, 0.90)
    n4 = odds.min_bets_to_beat_break_even(0.60, 0.523809524, 0.90)
    n1 = odds.min_bets_to_beat_break_even(0.53, 0.523809524, 0.90)
    print(f"  bets needed to *prove* it (lower 90% bound clears -110 break-even): "
          f"53%→{n1}, 55%→{n2}, 58%→{n3}, 60%→{n4}")
    for name, val in (("53%", n1), ("55%", n2), ("58%", n3), ("60%", n4)):
        if val is None:
            FAILURES.append(f"min bets for {name} unreachable")
    check("ordering of required sample sizes", (n1 > n2 > n3 > n4), True)


def test_copula():
    print("\n3. parlay pricing under dependence")
    p = 0.55
    ind = parlay.joint_all_win([p, p], 0.0)
    close("independent 2-leg joint", ind, p * p, 1e-12)
    pos = parlay.joint_all_win([p, p], 0.5)
    neg = parlay.joint_all_win([p, p], -0.5)
    check("positive rho raises the joint", pos > ind, True)
    check("negative rho lowers it", neg < ind, True)
    check("monotone in rho", all(
        parlay.joint_all_win([p, p], r) < parlay.joint_all_win([p, p], r + 0.1)
        for r in [-0.8, -0.4, 0.0, 0.4, 0.7]), True)
    hi = parlay.joint_all_win([p, p], 0.999)
    lo = parlay.joint_all_win([0.55, 0.45], -0.999)
    # convergence to the Frechet bounds is O(sqrt(1-rho)), so test the bracket, not equality
    check("never above the Frechet upper bound min(p1,p2)", hi <= p + 1e-9, True)
    check("rho=0.999 sits just under the upper bound", p - 0.02 < hi <= p, True)
    check("never below the Frechet lower bound max(0,p1+p2-1)", lo >= 0.0 - 1e-12, True)
    check("rho=-0.999 sits just above the lower bound", 0.0 <= lo < 0.02, True)
    print(f"  bounds check at rho=±0.999: upper {hi:.6f} (cap {p}), lower {lo:.6f} (floor 0)")
    lose0 = parlay.joint_all_lose([p, p], 0.0)
    close("independent joint loss", lose0, (1 - p) ** 2, 1e-12)
    check("dependence raises joint loss too", parlay.joint_all_lose([p, p], 0.6) > lose0, True)
    three = parlay.joint_all_win([p, p, p], 0.3)
    check("3-leg joint between independent and perfect", p ** 3 < three < p, True)
    for rho in (0.0, 0.2, 0.45, 0.7):
        dec = 1.0 / parlay.joint_all_win([p, 0.52], rho)
        back = parlay.implied_rho_from_parlay([p, 0.52], dec)
        close(f"implied-rho round trip at rho={rho}", back, rho, 2e-3)
    eff = parlay.correlation_effect(p, 0.52, 0.4)
    print(f"  illustration: 0.55 & 0.52 legs, rho=0.4 → joint {eff['prob_correlated']:.4f} "
          f"vs naive {eff['prob_independent']:.4f} "
          f"(book-equivalent multiplier {eff['book_equivalent_multiplier']:.4f})")


def test_stats():
    print("\n4. deflation and the luck tests")
    xs = [0.06 if i % 2 == 0 else -0.04 for i in range(200)]   # mean +0.01: real (small) skill
    d = stats.deflated_sharpe(xs, n_variants=1, sr_variance=0.0)
    check("SR* is 0 with a single trial and zero dispersion", d["sr_star"] == 0.0, True)
    d2 = stats.deflated_sharpe(xs, n_variants=100, sr_variance=0.04)
    trl = "not attainable at this SR" if math.isinf(d2["min_trl_periods"]) else f"{d2['min_trl_periods']:.0f} periods ({d2['min_trl_multiple_of_sample']:.1f}x the sample we have)"
    print(f"  SR {d2['sharpe']:.4f} vs SR*(100 variants, sd 0.2) {d2['sr_star']:.4f} "
          f"→ DSR {d2['dsr']:.4f}, MinTRL {trl}")
    check("a coin-flip-looking series is deflated away", d2["dsr"] < 0.05, True)
    d3 = stats.deflated_sharpe(xs, n_variants=1, sr_variance=0.0)
    check("with no multiple testing the same SR is significant-ish", d3["dsr"] > 0.5, True)
    b = stats.moving_block_bootstrap_p([0.2 * ((-1) ** i) + 0.9 for i in range(120)], block=1)
    print(f"  clearly-positive series → block-bootstrap p = {b['p']:.4f}")
    check("positive series passes the luck test", b["p"] <= 0.05, True)
    b2 = stats.moving_block_bootstrap_p([1.0 if i % 2 else -0.99 for i in range(60)], block=1)
    print(f"  near-random series  → block-bootstrap p = {b2['p']:.4f}")
    check("random-looking series is not promoted", b2["p"] <= 0.05, False)
    sfp = stats.sign_flip_permutation_p([0.9, 0.9, 0.9, -0.1, -0.1, -0.1, -0.1, -0.1])
    print(f"  sign-flip exact p on 8 bets = {sfp['p']:.4f} (method {sfp['method']})")
    check("8 bets can never clear 5%", sfp["p"] <= 0.05, False)


def test_gates():
    print("\n5. gate battery")
    weak = {"name": "weak", "n_bets": 40, "n_wins": 24, "odds_line": -110}
    v = gates.evaluate(weak)
    print(f"  weak record → {v['summary']}")
    check("underpowered record is blocked", v["promotable"], False)
    check("G-01 fails first", v["gates"]["G-01"]["state"], gates.FAIL)
    check("G-02 cannot clear break-even", v["gates"]["G-02"]["state"], gates.FAIL)
    check("G-03 is unknown, not passed (no CLV data)", v["gates"]["G-03"]["state"], gates.UNKNOWN)

    # a -110 market: +0.909091 on a win, -1.000 on a loss, 232 wins in 400 bets (58.0%)
    rng_series = [-1.0] * 400
    for _j in range(232):
        rng_series[(_j * 137) % 400] = 0.909090909
    strong = dict(
        n_bets=400, n_wins=232, odds_line=-110, p_market_novig=None,
        clv_mean=0.012, clv_ci_low=0.004, share_beat_close=0.58,
        returns=rng_series, n_variants=1, sr_variance=0.0, free_params=1,
        fold_edge_signs=[1, 1, 1, 1], p_model=0.58,
        recent_edge=0.05, rolling_edges=[0.06, 0.05, 0.07, 0.04, 0.06, 0.05, 0.08, 0.05, 0.06, 0.04],
        qualifying_bets_per_week=40, handleable_multiple=60,
        kelly_fraction_used=0.02, cluster_units_exposure=1.0,
        cluster_leg_probs=[0.58, 0.55], cluster_rho=0.2,
        drawdown_prob=0.02, push_handling_modelled=True,
        feature_max_age_hours_at_decision=3.0,
        brier_delta_vs_baseline=-0.004, mae_delta_vs_baseline=-0.35, tail_degradation_share=0.02,
        revision_sign_flip_share=0.05, max_bets_per_cluster=1,
    )
    v2 = gates.evaluate(strong)
    print(f"  strong synthetic record → {v2['summary']}")
    for gid in ("G-01", "G-02", "G-03", "G-04", "G-06", "G-09", "G-11", "G-14", "G-16"):
        print(f"    {gid}: {v2['gates'][gid]['state']} — {v2['gates'][gid]['detail']}")
    check("a fully-evidenced synthetic record is promotable", v2["promotable"], True)
    print(f"  skill score: {gates.skill_score({**strong, 'edge_after_cost': 0.031}, v2, 400, 1.0):.4f}")

    par = {"n_bets": 1, "legs": [{"event": "A", "same_event": True}, {"event": "A", "same_event": True}],
           "sgp_ticket": False, "push_handling_modelled": True}
    v3 = gates.evaluate(par, applicable=["G-12"])
    check("two legs from one event outside an SGP are refused", v3["gates"]["G-12"]["state"], gates.FAIL)
    par2 = dict(par, sgp_ticket=True)
    check("the same ticket inside an SGP is allowed", gates.evaluate(par2, ["G-12"])["gates"]["G-12"]["state"], gates.PASS)
    dup = {"legs": [{"event": "A"}, {"event": "B"}], "sgp_ticket": False,
           "duplicate_market": True, "push_handling_modelled": True}
    check("duplicate-market parlays refused (house rules)", gates.evaluate(dup, ["G-12"])["gates"]["G-12"]["state"], gates.FAIL)


def test_registry(tmp: str = "/tmp/fl2-registry.jsonl"):
    print("\n6. pre-commitment registry")
    import os
    if os.path.exists(tmp):
        os.remove(tmp)
    spec = {"id": "SIG-02-v1", "family": "availability", "params": {"leverage": {"C": 1.4}}}
    e = registry.register(spec, path=tmp)
    check("entry verifies", registry.verify(e), True)
    e["spec"]["params"]["leverage"]["C"] = 9.9
    check("post-hoc edit is detected", registry.verify(e), False)
    registry.register({"id": "SIG-02-v2", "family": "availability"}, path=tmp)
    check("variant count for the family", registry.variant_count("availability", path=tmp), 2)


def report():
    print("\n" + "=" * 78)
    print("REPORT — values used by the site (all computed here, none of them market data)")
    print("=" * 78)
    be = odds.break_even(-110)
    print(f"break-even at -110 (the hurdle before costs): {be:.6f}")
    print("\nA. bets required before a hit rate is evidence (lower 90% Wilson bound > break-even)")
    for hr in (0.53, 0.55, 0.56, 0.58, 0.60, 0.65):
        n = odds.min_bets_to_beat_break_even(hr, be, 0.90)
        print(f"   hit {hr:.0%} → n = {n}")
    print("\nB. parlay joint probability vs dependence (two legs at 0.55 and 0.52)")
    for rho in (0.0, 0.2, 0.4, 0.6, 0.8):
        j = parlay.joint_all_win([0.55, 0.52], rho)
        naive = 0.55 * 0.52
        print(f"   rho {rho:+.1f}: joint {j:.4f}  naive {naive:.4f}  ratio {j / naive:.4f}"
              f"  fair decimal {1 / j:.3f} vs {1 / naive:.3f}")
    print("\nC. what a book's parlay multiplier is really saying (two 0.55 legs)")
    for mult in (0.90, 0.95, 1.00, 1.05):
        naive = 1 / (0.55 * 0.55)
        dec = naive * mult
        rho = parlay.implied_rho_from_parlay([0.55, 0.55], dec)
        print(f"   multiplier {mult:.2f} → decimal {dec:.3f} → implied rho {rho:+.3f}")
    print("\nD. deflation: SR* a luck-driven search produces (dispersion of trial SRs = 0.04)")
    for nv in (1, 10, 50, 100, 500, 2000):
        print(f"   {nv:>5} variants → SR* {stats.expected_max_sharpe(nv, 0.04):.4f} per period")
    print("\nE. sample-size floor in weeks (G-01 = 150 bets; 30 qualifying bets/week)")
    print(f"   150 / 30 = {150 / 30:.1f} weeks of live evidence minimum")


def main() -> int:
    print("=" * 78)
    print("FL2 engine self-test")
    print("=" * 78)
    test_odds()
    test_ci_and_sample()
    test_copula()
    test_stats()
    test_gates()
    test_registry()
    report()
    print("\n" + "=" * 78)
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S):")
        for f in FAILURES:
            print("  - " + f)
        return 1
    print("all assertions passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
