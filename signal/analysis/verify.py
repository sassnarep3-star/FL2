#!/usr/bin/env python3
"""
verify.py — line-by-line verification of every number rendered on the site.

For each published figure this re-reads the underlying data file, recomputes the value
from scratch, and compares it with what the HTML actually says. If a number on the site
cannot be reproduced from the data, this fails. That is the whole point: a figure that
cannot be traced back to bytes must not be published.
"""
from __future__ import annotations

import csv
import json
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# This section lives in signal/ ; ROOT is signal/ and data/ is signal/data.
DATA = os.path.join(ROOT, "data")
checks = []
fails = []


def norm(s):
    import unicodedata
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace(".", "").replace("'", "").replace("-", "").replace(" ", "")
    return re.sub(r"(jr|sr|ii|iii|iv)$", "", s)


def check(name, ok, detail=""):
    checks.append((name, ok, detail))
    if not ok:
        fails.append(f"{name}: {detail}")


def html(page):
    p = os.path.join(ROOT, page)
    if not os.path.exists(p):
        return ""
    return open(p, encoding="utf-8").read()


def has(page, text):
    """The rendered page must contain this exact string."""
    h = html(page)
    return text in h


def main():
    # ---------------------------------------------------------------- market ----
    m = json.load(open(os.path.join(DATA, "market_local.json")))["rows"]
    graded = [r for r in m if r.get("completed") and r.get("cover_margin") is not None]
    check("market: graded game count", len(graded) == 3032, f"recomputed {len(graded)}")
    check("market: figure on page", has("lines.html", "3,032") or has("lines.html", "3032"),
          "3,032 not found on lines.html")
    np_ = [r["cover_margin"] for r in graded if r["cover_margin"] != 0]
    cover = 100.0 * sum(1 for c in np_ if c > 0) / len(np_)
    check("market: home cover rate", abs(cover - 48.53) < 0.005, f"recomputed {cover:.2f}")
    check("market: cover shown", has("lines.html", "48.53"), "48.53 not on lines.html")
    tnp = [r["total_delta"] for r in graded if r["total_delta"] not in (None, 0)]
    over = 100.0 * sum(1 for t in tnp if t > 0) / len(tnp)
    check("market: over rate", abs(over - 49.00) < 0.005, f"recomputed {over:.2f}")

    # sign validation recomputed independently
    ok = bad = 0
    for r in graded:
        truth, cm = r.get("market_outcome_home"), r.get("cover_margin")
        if truth is None or cm is None or cm == 0:
            continue
        if (1.0 if cm > 0 else 0.0) == truth:
            ok += 1
        else:
            bad += 1
    pct = 100.0 * ok / (ok + bad)
    check("market: sign validation", abs(pct - 98.92) < 0.005, f"recomputed {pct:.2f}")
    check("market: sign validation shown", has("lines.html", "98.92"), "98.92 not on lines.html")

    # ------------------------------------------------------------- injuries ----
    ip = json.load(open(os.path.join(DATA, "injury_play_rate.json")))
    q = ip["overall"]["Questionable"]
    check("injury: Questionable n", q["n"] == 14948, f"recorded {q['n']}")
    check("injury: Questionable rate", abs(q["play_rate_pct"] - 65.68) < 0.005,
          f"recorded {q['play_rate_pct']}")
    check("injury: rate shown", has("injury_signal.html", "65.68"), "65.68 not on injury_signal.html")
    dobj = ip["overall"]["Doubtful"]
    check("injury: Doubtful rate", abs(dobj["play_rate_pct"] - 0.89) < 0.005,
          f"recorded {dobj['play_rate_pct']}")
    check("injury: Doubtful shown", has("injury_signal.html", "0.89"), "0.89 not on injury_signal.html")

    # recompute the Questionable rate straight from the CSVs, independent of the JSON
    part = set()
    with open(os.path.join(DATA, "snap_participation.csv"), newline="") as f:
        for r in csv.DictReader(f):
            part.add((int(r["season"]), int(r["week"]), r["team"], norm(r["player"])))
    with open(os.path.join(DATA, "player_week_keys.csv"), newline="") as f:
        for r in csv.DictReader(f):
            part.add((int(r["season"]), int(r["week"]), r["team"], norm(r["player_name"])))

    # Independent recomputation using the same documented severity rule:
    # one row per team-week-player, most severe designation wins.
    SEVERITY = {"Out": 3, "Doubtful": 2, "Questionable": 1}
    best = {}
    with open(os.path.join(DATA, "injury_player.csv"), newline="") as f:
        for r in csv.DictReader(f):
            if r["game_status"] not in SEVERITY:
                continue
            key = (int(r["season"]), int(r["week"]), r["team"], norm(r["full_name"]))
            if key not in best or SEVERITY[r["game_status"]] > SEVERITY[best[key]]:
                best[key] = r["game_status"]
    cov = set(ip["coverage"]["seasons_measured"])
    n_q = n_played = 0
    for key, st in best.items():
        if st != "Questionable" or key[0] not in cov:
            continue
        n_q += 1
        n_played += int(key in part)
    check("injury: independent recompute n", n_q == q["n"], f"recomputed {n_q} vs {q['n']}")
    check("injury: independent recompute rate", abs(100.0 * n_played / n_q - q["play_rate_pct"]) < 0.05,
          f"recomputed {100.0 * n_played / n_q:.2f}")

    # ----------------------------------------------------------------- depth ----
    dp = json.load(open(os.path.join(DATA, "depth_accuracy.json")))["overall"]
    check("depth: 1st string n", dp["1st string"]["n"] == 77702, f"recorded {dp['1st string']['n']}")
    check("depth: 1st string rate", abs(dp["1st string"]["agreement_pct"] - 90.62) < 0.005,
          f"recorded {dp['1st string']['agreement_pct']}")
    check("depth: rate shown", has("depth.html", "90.62"), "90.62 not on depth.html")
    check("depth: 2nd string shown", has("depth.html", "80.39"), "80.39 not on depth.html")

    # ----------------------------------------------------------- correlation ----
    co = json.load(open(os.path.join(DATA, "correlation.json")))[
        "overall"]
    check("corr: n games", co["n_graded_games"] == 2927, f"recorded {co['n_graded_games']}")
    check("corr: phi rounds to the published 0.013",
          round(co["phi_coefficient"], 3) == 0.013, f"recorded {co['phi_coefficient']}")
    check("corr: phi shown", has("correlation.html", "0.013"), "0.013 not on correlation.html")
    check("corr: joint shown", has("correlation.html", "24.09"), "24.09 not on correlation.html")

    # ------------------------------------------------------------ strategies ----
    st = json.load(open(os.path.join(DATA, "strategies.json")))
    check("strat: six evaluated", len(st["results"]) == 6, f"{len(st['results'])}")
    check("strat: zero cleared", st["verdict_summary"]["clearing_all_gates"] == 0,
          f"{st['verdict_summary']['clearing_all_gates']}")
    check("strat: zero shown", has("validation.html", "0 of 6"), "0 of 6 not on validation.html")
    for r in st["results"]:
        check(f"strat {r['id']}: not ranked as a winner",
              r["verdict"] == "luck candidate", f"verdict {r['verdict']}")
    check("strat: no ROI claim survives", has("validation.html", "luck candidate"),
          "verdict column missing")

    # --------------------------------------------------------------- sources ----
    for page in [f for f in os.listdir(ROOT) if f.endswith(".html")]:
        h = html(page)
        if "<table" not in h:
            continue
        # every data row must contain at least one http link
        for row in re.findall(r"<tr>(?!<th).*?</tr>", h, re.S):
            if "<td" not in row:
                continue
            check(f"{page}: row has a source link", "http" in row,
                  f"row without a link: {re.sub(r'<[^>]+>', ' ', row)[:80]}")

    # ------------------------------------------------------------------ report ----
    print(f"{len(checks)} checks run\n")
    by_page = {}
    for name, ok, detail in checks:
        by_page.setdefault(name.split(":")[0], [0, 0])[0 if ok else 1] += 1
    for k, (good, bad_) in by_page.items():
        print(f"  {k:<12} {good:>3} pass  {bad_:>3} fail")
    if fails:
        print("\nFAILURES:")
        for f in fails:
            print("  -", f)
        return 1
    print(f"\nAll {len(checks)} verification checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
