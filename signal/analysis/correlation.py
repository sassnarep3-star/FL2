#!/usr/bin/env python3
"""
correlation.py — measure, do not assume, same-game leg correlations.

Parlay pricing assumes independence: the joint probability is taken as the product of the
leg probabilities. That is only correct if the legs are independent. This script measures
the ACTUAL joint frequency of two legs landing in the same game and compares it with the
independent prediction, so the size and sign of the error are visible.

What is measurable from data we actually hold
---------------------------------------------
Team legs only, because we hold verified closing spreads and totals:
  * home team covers the spread
  * the game goes over the total
These two are the classic positively correlated pair: a comfortable home win tends to be
high-scoring for the home side.

What is NOT measurable yet
--------------------------
Player-prop leg correlations. They need the joint outcome of two players in the same game,
which we can compute, but pricing a combo needs prop PRICES, which we do not have (Q02).
No prop correlation is published here.

Output: data/correlation.json
"""
from __future__ import annotations

import collections
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# This section lives in signal/ ; ROOT is signal/ and data/ is signal/data.
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "correlation.json")


def wilson(p, n, z=1.96):
    if not n:
        return [None, None]
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(100 * max(0.0, c - h), 2), round(100 * min(1.0, c + h), 2)]


def load_market():
    """Prefer the sandbox-built file whose sign convention was validated against
    closing_lines.csv's own outcome column (98.92%), and report which file was used."""
    for name in ("market_local.json", "market.json"):
        p = os.path.join(DATA, name)
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)["rows"], name
    raise SystemExit("no market data; run the pipeline first")


def leg_defs(r):
    """Return dict of leg -> bool or None (None = not gradable).

    Two market schemas exist upstream: the Actions runner writes home_cover_margin /
    home_covered, and the sandbox builder writes cover_margin. Accept either rather than
    silently producing an empty result.
    """
    cm = r.get("cover_margin")
    if cm is None:
        cm = r.get("home_cover_margin")
    td = r.get("total_delta")
    out = {}
    if cm is not None:
        out["home_cover"] = None if cm == 0 else cm > 0
    if td is not None:
        out["over"] = None if td == 0 else td > 0
    return out


def measure(rows, label):
    pair = collections.defaultdict(int)
    for r in rows:
        l = leg_defs(r)
        if l.get("home_cover") is None or l.get("over") is None:
            continue
        pair[(bool(l["home_cover"]), bool(l["over"]))] += 1
    n = sum(pair.values())
    if not n:
        return None
    a = pair.get((True, True), 0) + pair.get((True, False), 0)   # home covers
    b = pair.get((True, True), 0) + pair.get((False, True), 0)   # over
    both = pair.get((True, True), 0)
    pa, pb, pab = a / n, b / n, both / n
    indep = pa * pb
    # phi coefficient for 2x2
    c_ = pair.get((False, False), 0)
    denom = a * b * (n - a) * (n - b)
    phi = ((both * c_ - (a - both) * (b - both)) / math.sqrt(denom)) if denom > 0 else None
    return {
        "bucket": label,
        "n_graded_games": n,
        "p_home_cover_pct": round(100 * pa, 2),
        "p_over_pct": round(100 * pb, 2),
        "p_both_pct_measured": round(100 * pab, 4),
        "p_both_pct_if_independent": round(100 * indep, 4),
        "difference_pct_points": round(100 * (pab - indep), 4),
        "joint_ci95": wilson(pab, n),
        "phi_coefficient": round(phi, 4) if phi is not None else None,
        "payout_ratio_measured_vs_independent": round(pab / indep, 4) if indep else None,
    }


def main():
    rows, src_name = load_market()
    done = [r for r in rows
            if r.get("completed")
            and (r.get("cover_margin") is not None or r.get("home_cover_margin") is not None)
            and r.get("total_delta") is not None]
    overall = measure(done, "all graded games 2015-2026")

    # Does the correlation depend on how big the spread is? A big favourite covering
    # usually means a blowout, which pushes the total.
    buckets = {"spread <= 3": [], "spread 3.5-6.5": [], "spread >= 7": []}
    for r in done:
        hl = r.get("home_line")
        if hl is None and r.get("spread_line") is not None:
            hl = -r["spread_line"]
        if hl is None:
            continue
        a = abs(hl)
        k = "spread <= 3" if a <= 3 else ("spread 3.5-6.5" if a <= 6.5 else "spread >= 7")
        buckets[k].append(r)
    by_spread = [measure(v, k) for k, v in buckets.items() if v]

    report = {
        "question": "Q05",
        "source_file": src_name,
        "definition": ("Same-game correlation between two team legs: home-cover and over. "
                       "phi is the 2x2 correlation coefficient; difference_pct_points is the "
                       "measured joint probability minus the independent prediction."),
        "why_it_matters": ("A parlay priced as if the legs were independent is mispriced by exactly "
                           "this difference. Multiplying probabilities is only valid at phi = 0."),
        "overall": overall,
        "by_spread_size": by_spread,
        "not_measured": {
            "player_prop_leg_correlations": ("Needs prop PRICES to value a combo. We hold outcomes "
                                             "but not prop prices, so no prop correlation is "
                                             "published. See question Q02."),
        },
        "caveats": [
            "This is a historical base rate, not a forecast and not an edge.",
            "Pushes are excluded from both legs rather than treated as losses.",
            "A fair market should show a small positive correlation here; a large one would suggest a data error.",
            "The vig is not applied; a parlay's true cost also depends on the book's correlation adjustment.",
        ],
        "sources": [
            "https://github.com/nflverse/nfldata",
            "https://nflreadr.nflverse.com/articles/dictionary_schedules.html",
            "https://www.itl.nist.gov/div898/handbook/eda/section3/eda353.htm",
        ],
    }
    with open(OUT, "w") as f:
        json.dump(report, f, indent=1)

    print(f"{'bucket':<28}{'n':>7}{'P(cover)':>10}{'P(over)':>10}{'measured':>11}"
          f"{'indep':>9}{'diff':>9}{'phi':>9}")
    for m in [overall] + by_spread:
        if not m:
            continue
        print(f"{m['bucket']:<28}{m['n_graded_games']:>7}"
              f"{m['p_home_cover_pct']:>9.2f}%{m['p_over_pct']:>9.2f}%"
              f"{m['p_both_pct_measured']:>10.2f}%{m['p_both_pct_if_independent']:>8.2f}%"
              f"{m['difference_pct_points']:>+8.2f}{m['phi_coefficient']:>9.3f}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
