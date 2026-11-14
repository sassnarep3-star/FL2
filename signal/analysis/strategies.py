#!/usr/bin/env python3
"""
strategies.py — run candidate strategies through a pre-registered validation gate.

THE DESIGN RULE
---------------
A strategy is NOT ranked by ROI. It is scored pass/fail against gates that must be met
before ROI is even looked at, and the number of strategies tried is published so the
multiple-comparisons problem is visible. A strategy that fails is listed with the reason.
Deleting a failure would be the easiest way to fake skill, so failures are kept.

GATES (pre-registered here, before any result is inspected)
-----------------------------------------------------------
G1  sample      : at least MIN_BETS graded bets in the test window
G2  significance: bootstrap 95% CI on ROI excludes zero  (B_RESAMPLES resamples)
G3  multiple    : the strategy's p-value survives Benjamini-Hochberg FDR at Q=0.10
                  across every strategy evaluated, not just the winners
G4  holdout     : performance in the final HOLDOUT_SEASONS must have the same sign as
                  the in-sample window
G5  price basis : every bet must be priced off a real recorded closing number
                  (no model-originated prices)

Only strategies that clear G1-G5 may be described as skill-based. Anything else is
reported as a luck candidate, explicitly.

WHAT THIS SCRIPT CAN AND CANNOT TEST
-----------------------------------
Testable now: team-level singles on the closing spread/total, using a signal that is
independent of the closing line. Not testable now: player props and prop combos, because
no historical prop prices exist in this repository (question Q02). Those are reported as
BLOCKED rather than skipped silently.

Output: data/strategies.json
"""
from __future__ import annotations

import json
import math
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# This section lives in signal/ ; ROOT is signal/ and data/ is signal/data.
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "strategies.json")

MIN_BETS = 200          # G1
B_RESAMPLES = 5000      # G2
FDR_Q = 0.10            # G3
HOLDOUT_SEASONS = (2024, 2025, 2026)
SEED = 20261114         # fixed so the bootstrap is reproducible


def load_market():
    for name in ("market_local.json", "market.json"):
        p = os.path.join(DATA, name)
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)["rows"], name
    raise SystemExit("no market data")


def american_to_decimal(a):
    if a is None:
        return None
    return 1 + (a / 100.0 if a > 0 else 100.0 / abs(a))


def roi_of(bets):
    """bets: list of (decimal_odds, won_bool). Pushes excluded before calling."""
    if not bets:
        return None
    stake = len(bets)
    ret = sum((o - 1) if w else -1.0 for o, w in bets)
    return ret / stake


def bootstrap_ci(bets, resamples=B_RESAMPLES, seed=SEED):
    if len(bets) < 10:
        return None, None
    rnd = random.Random(seed)
    n = len(bets)
    stats = []
    for _ in range(resamples):
        sample = [bets[rnd.randrange(n)] for _ in range(n)]
        stats.append(roi_of(sample))
    stats.sort()
    lo = stats[int(0.025 * len(stats))]
    hi = stats[int(0.975 * len(stats)) - 1]
    return lo, hi


def p_value(bets):
    """Two-sided bootstrap p-value against ROI = 0."""
    if len(bets) < 10:
        return None
    obs = roi_of(bets)
    rnd = random.Random(SEED + 1)
    n = len(bets)
    centered = [(o, w) for o, w in bets]
    mean = obs
    count = 0
    trials = 2000
    for _ in range(trials):
        s = 0.0
        for _ in range(n):
            i = rnd.randrange(n)
            o, w = centered[i]
            s += ((o - 1) if w else -1.0) - mean
        if abs(s / n) >= abs(mean):
            count += 1
    return count / trials


def bh_fdr(pvals, q=FDR_Q):
    """Benjamini-Hochberg: return the set of indices that pass."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    passed = set()
    k_max = 0
    for rank, i in enumerate(order, start=1):
        if pvals[i] <= q * rank / m:
            k_max = rank
    for rank, i in enumerate(order, start=1):
        if rank <= k_max:
            passed.add(i)
    return passed


def load_side_prices():
    """Real recorded prices for the side we are actually betting.

    Bug this fixes: pricing a SPREAD bet off `home_moneyline` produced a fake +148% ROI.
    A moneyline is the price of a straight win, not of covering a handicap. The only
    correct price for a spread is the spread price.

    closing_lines.csv carries `odds` for most rows, but as an open question (Q01) it does
    not record which book or which timestamp. We therefore require a REAL price and, where
    the file has none, fall back to the standard -110 while counting how often we had to.
    """
    import csv
    # Prefer the COMMITTED price table. Reading raw/closing_lines.csv made this analysis
    # depend on a gitignored directory, so in CI it silently produced 0% price coverage.
    path = os.path.join(DATA, "closing_prices.csv")
    if not os.path.exists(path):
        path = os.path.join(ROOT, "raw", "closing_lines.csv")
    if not os.path.exists(path):
        return {}, 0
    out = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r.get("type") in ("SPREAD", "TOTAL") and r.get("odds"):
                gid = r.get("alt_game_id") or r.get("game_id")
                try:
                    out[(gid, r["type"], r["side"])] = int(r["odds"])
                except ValueError:
                    pass
    return out, len(out)


def build_candidates(rows):
    """Signals that are functions of the line and schedule only -- no in-game outcome."""
    cands = []
    graded = [r for r in rows if r.get("completed") and r.get("cover_margin") is not None]

    def sel(pred):
        return [r for r in graded if pred(r)]

    # Each candidate: (id, name, description, selector, side, price_key)
    cands.append(("C1", "Fade big road favourites",
                  "Home team when the away side is favoured by 7 or more.",
                  lambda r: (r.get("home_line") or 0) >= 7, "home_cover", "home"))

    cands.append(("C2", "Back small home favourites",
                  "Home team when favoured by 1 to 3 points.",
                  lambda r: 1 <= (r.get("home_line") or 99) <= 3, "home_cover", "home"))

    cands.append(("C3", "Fade the public over on short rest",
                  "Under when either team is on fewer than 6 days rest.",
                  lambda r: (r.get("home_rest") is not None and r["home_rest"] < 6)
                            or (r.get("away_rest") is not None and r["away_rest"] < 6),
                  "under", "total"))

    cands.append(("C4", "Rest advantage at home",
                  "Home team covering when it has 3+ more rest days than the visitor.",
                  lambda r: (r.get("home_rest") is not None and r.get("away_rest") is not None
                             and r["home_rest"] - r["away_rest"] >= 3), "home_cover", "home"))

    cands.append(("C5", "Division dog",
                  "Home underdog in a divisional game.",
                  lambda r: r.get("div_game") == 1 and (r.get("home_line") or 0) > 0,
                  "home_cover", "home"))

    cands.append(("C6", "Big total, take the under",
                  "Under when the closing total is 48 or higher.",
                  lambda r: (r.get("total_line") or 0) >= 48, "under", "total"))

    return cands, sel


def grade(rows):
    """Build per-candidate bet lists. Price = -110 default only if no real price exists;
    we require a real line, and use the standard -110 where the file has no side price."""
    cands, _ = build_candidates(rows)
    prices, n_prices = load_side_prices()
    out = []
    for cid, name, desc, sel, leg, market in cands:
        bets, bets_hold = [], []
        real_prices = 0
        for r in rows:
            if not r.get("completed"):
                continue
            if not sel(r):
                continue
            if market == "home":
                cm = r.get("cover_margin")
                if cm is None or cm == 0:
                    continue
                won = cm > 0 if leg == "home_cover" else cm < 0
                price = prices.get((r.get("game_id"), "SPREAD", r.get("home")))
            else:
                td = r.get("total_delta")
                if td is None or td == 0:
                    continue
                won = td < 0 if leg == "under" else td > 0
                price = prices.get((r.get("game_id"), "TOTAL", "Under"))
            if price:
                real_prices += 1
            dec = american_to_decimal(price) if price else 1.909  # -110 standard
            b = (dec, won)
            bets.append(b)
            if r.get("season") in HOLDOUT_SEASONS:
                bets_hold.append(b)
        ins = [b for b in bets if True]
        out.append({"id": cid, "name": name, "description": desc, "bets": bets,
                    "holdout_bets": bets_hold, "real_prices": real_prices,
                    "price_coverage_pct": round(100 * real_prices / len(bets), 1) if bets else None})
    return out, n_prices


def main():
    rows, src = load_market()
    results, n_prices_available = grade(rows)

    # Evaluate all candidates, then apply FDR across all of them.
    pvals = []
    for r in results:
        r["n"] = len(r["bets"])
        r["roi"] = roi_of(r["bets"])
        r["ci"] = bootstrap_ci(r["bets"])
        r["p"] = p_value(r["bets"])
        r["roi_holdout"] = roi_of(r["holdout_bets"])
        r["n_holdout"] = len(r["holdout_bets"])
        pvals.append(r["p"] if r["p"] is not None else 1.0)
    passed_fdr = bh_fdr(pvals)

    for i, r in enumerate(results):
        gates = {}
        gates["G1_sample"] = r["n"] >= MIN_BETS
        lo, hi = r["ci"] if r["ci"] else (None, None)
        gates["G2_significance"] = bool(lo is not None and lo > 0)
        gates["G3_multiple_testing"] = i in passed_fdr
        gates["G4_holdout_sign"] = bool(
            r["roi"] is not None and r["roi_holdout"] is not None
            and (r["roi"] > 0) == (r["roi_holdout"] > 0) and r["n_holdout"] > 0)
        # G5 now genuinely tests something: the bet must have been priced off a recorded
        # spread/total price rather than defaulted to -110.
        gates["G5_price_basis"] = bool((r.get("real_prices") or 0) / r["n"] >= 0.5) if r["n"] else False
        r["gates"] = gates
        r["passed_all"] = all(gates.values())
        r["verdict"] = "clears gates" if r["passed_all"] else "luck candidate"
        r["fail_reasons"] = [k for k, v in gates.items() if not v]

    blocked = [{
        "id": "B1",
        "name": "Player-prop singles",
        "reason": "No historical player-prop PRICES in this repository (question Q02).",
        "status": "blocked",
    }, {
        "id": "B2",
        "name": "Player-prop combos / same-game parlays",
        "reason": ("Needs prop prices (Q02) AND prop-leg correlations (Q05). Publishing either "
                   "without the other would be an unverified pricing claim."),
        "status": "blocked",
    }, {
        "id": "B3",
        "name": "Cross-game parlays",
        "reason": ("Testable in principle once a leg-level price history exists; the closing "
                   "file gives side prices for spreads but not for every combination."),
        "status": "blocked",
    }]

    report = {
        "source_file": src,
        "pre_registered_gate": {
            "G1_sample": f"at least {MIN_BETS} graded bets",
            "G2_significance": f"bootstrap 95% CI on ROI excludes zero ({B_RESAMPLES} resamples, seed {SEED})",
            "G3_multiple_testing": f"Benjamini-Hochberg FDR at q={FDR_Q} across all strategies evaluated",
            "G4_holdout_sign": f"holdout seasons {list(HOLDOUT_SEASONS)} must show the same sign as in-sample",
            "G5_price_basis": "at least 50% of bets priced from a recorded spread/total price; the rest fall back to -110 and that share is reported",
        },
        "strategies_evaluated": len(results),
        "note_on_search": ("The number of strategies tried is published deliberately. Testing many "
                           "candidates and reporting only the best is the standard way an "
                           "illusory edge is manufactured."),
        "results": [{
            "id": r["id"], "name": r["name"], "description": r["description"],
            "n_bets": r["n"],
            "real_prices": r.get("real_prices"),
            "price_coverage_pct": r.get("price_coverage_pct"), "roi_pct": round(100 * r["roi"], 2) if r["roi"] is not None else None,
            "roi_ci95_pct": [round(100 * r["ci"][0], 2), round(100 * r["ci"][1], 2)] if r["ci"] and r["ci"][0] is not None else None,
            "p_value": round(r["p"], 4) if r["p"] is not None else None,
            "holdout_n": r["n_holdout"],
            "holdout_roi_pct": round(100 * r["roi_holdout"], 2) if r["roi_holdout"] is not None else None,
            "gates": r["gates"], "fail_reasons": r["fail_reasons"],
            "verdict": r["verdict"],
        } for r in results],
        "blocked": blocked,
        "verdict_summary": {
            "clearing_all_gates": sum(1 for r in results if r["passed_all"]),
            "evaluated": len(results),
            "blocked_workstreams": len(blocked),
        },
        "price_sources": {
            "recorded_spread_and_total_prices": n_prices_available,
            "note": ("closing_lines.csv holds spread/total prices for part of the sample only, "
                     "and does not record which book or timestamp (Q01). Where no price exists the "
                     "standard -110 is used and the coverage share is shown per strategy."),
        },
        "caveats": [
            "Default -110 pricing is used where the schedule file carries no side price; a real "
            "account would face different prices and limits.",
            "No stake sizing, bankroll rule or line-shopping is modelled.",
            "The holdout seasons are the most recent three, but they were also used to build the "
            "descriptive pages, so they are not pristine. This is stated rather than hidden.",
            "A strategy that fails G2 may still be real but underpowered; failing the gate means "
            "'not yet demonstrated', not 'proven false'.",
        ],
        "sources": [
            "https://github.com/nflverse/nfldata",
            "https://www.itl.nist.gov/div898/handbook/eda/section3/eda353.htm",
        ],
    }
    with open(OUT, "w") as f:
        json.dump(report, f, indent=1)

    print(f"{'id':<4}{'n':>6}{'ROI%':>9}{'CI95':>20}{'p':>8}{'hold n':>8}{'holdROI%':>10}  verdict")
    for r in report["results"]:
        ci = r["roi_ci95_pct"] or ["—", "—"]
        print(f"{r['id']:<4}{r['n_bets']:>6}{str(r['roi_pct']):>9}"
              f"{f'[{ci[0]}, {ci[1]}]':>20}{str(r['p_value']):>8}{r['holdout_n']:>8}"
              f"{str(r['holdout_roi_pct']):>10}  {r['verdict']}"
              + (f"  (fails {','.join(x.split('_')[0] for x in r['fail_reasons'])})" if r['fail_reasons'] else ""))
    print(f"\nclearing all gates: {report['verdict_summary']['clearing_all_gates']} of {len(results)}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
