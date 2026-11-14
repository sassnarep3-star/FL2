#!/usr/bin/env python3
"""
tools/analyze_correlation.py

Computes Pearson correlations and bootstrap confidence intervals across the 32
clubs in data/team-metrics-2026-w10.csv.

IMPORTANT SCOPE NOTE
This is CROSS-SECTIONAL correlation (32 clubs, one snapshot). It answers
"when a team is better at X, is it also better at Y?" It does NOT answer
"if I bet X, how does it move the probability of Y?" — that needs time-series
play-level data this repository has not ingested yet. The two are not
interchangeable and the site says so on the Correlation page.

Run: python3 tools/analyze_correlation.py
Writes: data/correlation-matrix-2026-w10.csv, data/derived-correlation.json
"""
import csv
import json
import math
import random

SRC = "https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all"
RET = "2026-11-14"

PAIRS = [
    ("ngs_off_epa_per_play", "derived_ppg",
     "Offensive EPA per play vs points per game",
     "Does the league's own efficiency metric track scoring? if not, EPA alone is a weak signal."),
    ("ngs_def_epa_per_play", "derived_papg",
     "Defensive EPA per play allowed vs points allowed per game",
     "Same test on the defensive side."),
    ("pass_ypa", "derived_ppg",
     "Offensive passing yards per attempt vs points per game",
     "How much of scoring is explained by pass efficiency alone."),
    ("def_pass_ypa", "derived_papg",
     "Opponent passing yards per attempt vs points allowed per game",
     "Defensive mirror of the row above."),
    ("rush_avg", "derived_ppg",
     "Offensive rushing yards per attempt vs points per game",
     "Run efficiency vs scoring — the classic 'run game does not travel' question."),
    ("pass_yds", "derived_ppg",
     "Total passing yards vs points per game",
     "Volume vs efficiency: volume alone is a trap."),
    ("pass_att_share", "pass_ypa",
     "Pass-attempt share vs passing yards per attempt",
     "Are pass-heavy teams more efficient, or just more voluminous?"),
    ("def_pass_int", "derived_papg",
     "Defensive interceptions vs points allowed per game",
     "Turnover dependence — a known luck engine."),
    ("pass_sacks", "derived_ppg",
     "Sacks taken vs points per game",
     "Protection quality vs scoring."),
    ("def_pass_sacks", "derived_papg",
     "Sacks recorded vs points allowed per game",
     "Pass rush vs scoring defence."),
]


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def boot_ci(xs, ys, iters=4000, seed=7):
    rnd = random.Random(seed)
    n = len(xs)
    vals = []
    for _ in range(iters):
        idx = [rnd.randrange(n) for _ in range(n)]
        r = pearson([xs[i] for i in idx], [ys[i] for i in idx])
        if r is not None:
            vals.append(r)
    vals.sort()
    return vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals))]


def main():
    rows = list(csv.DictReader(open("data/team-metrics-2026-w10.csv")))
    out_rows, out_json = [], []
    for a, b, label, why in PAIRS:
        pairs = [(float(r[a]), float(r[b])) for r in rows if r[a] != "" and r[b] != ""]
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        r = pearson(xs, ys)
        lo, hi = boot_ci(xs, ys)
        r2 = r * r
        crosses_zero = lo <= 0 <= hi
        out_rows.append({
            "metric_a": a, "metric_b": b, "label": label, "n_clubs": len(pairs),
            "pearson_r": round(r, 3), "r_squared": round(r2, 3),
            "r2_pct_variance_explained": round(100 * r2, 1),
            "boot_ci_95_low": round(lo, 3), "boot_ci_95_high": round(hi, 3),
            "ci_excludes_zero": "no" if crosses_zero else "yes",
            "interpretation": why,
            "scope": "cross-sectional, 32 clubs, Week 10 2026 snapshot",
            "source_url": SRC, "retrieved": RET,
        })
        out_json.append(out_rows[-1])

    with open("data/correlation-matrix-2026-w10.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)

    with open("data/derived-correlation.json", "w") as fh:
        json.dump(out_json, fh, indent=2)

    for r in out_rows:
        print(f"{r['label'][:62]:62s} r={r['pearson_r']:>6}  "
              f"r2={r['r2_pct_variance_explained']:>5}%  "
              f"CI[{r['boot_ci_95_low']:>6},{r['boot_ci_95_high']:>6}] "
              f"{'CI includes 0' if r['ci_excludes_zero']=='no' else 'CI excludes 0'}")


if __name__ == "__main__":
    main()
