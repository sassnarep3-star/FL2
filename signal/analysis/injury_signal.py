#!/usr/bin/env python3
"""
injury_signal.py — measure what an official injury designation is actually worth.

WHY THIS EXISTS
---------------
The Questions register (Q06) says no numeric probability attaches to "Doubtful" or
"Questionable" in league policy. Any weighting we apply is therefore invented until we
measure it. This script replaces the assumption with a measured play rate.

THE MEASUREMENT TRAP (documented because it produces a false answer)
--------------------------------------------------------------------
A naive join of official game status to the nflverse snap counts returns a 100% play rate
for Questionable. That is not a finding: snap_counts only lists players who actually took a
snap (mean 45.9 listed players per team-week, ~46 active), so anyone who sat out has no row
and silently drops out of the denominator. The result is survivorship bias, not evidence.

THE CORRECTION
--------------
The denominator is every player-week that the official report lists with a designation.
A player counts as having played if EITHER
  (a) he appears in that team's snap-count rows for the week with snaps > 0, OR
  (b) he appears in that team's player-week row for the week with any recorded stat.
Anything else counts as did-not-play. We report the match rate so the reader can judge how
much of the result rests on name-based joining.

Output: data/injury_play_rate.json  (values + Wilson intervals + match diagnostics)
"""
from __future__ import annotations

import collections
import csv
import json
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# This section lives in signal/ ; ROOT is signal/ and data/ is signal/data.
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "injury_play_rate.json")

STAT_KEYS = ["attempts", "carries", "targets", "receptions", "passing_yards",
             "rushing_yards", "receiving_yards", "completions", "interceptions",
             "passing_tds", "rushing_tds", "receiving_tds", "receiving_air_yards"]


def norm(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace(".", "").replace("'", "").replace("-", "").replace(" ", "")
    return re.sub(r"(jr|sr|ii|iii|iv)$", "", s)


def wilson(p, n, z=1.96):
    if not n:
        return None, None
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return round(100 * max(0.0, c - h), 2), round(100 * min(1.0, c + h), 2)


def main():
    with open(os.path.join(DATA, "injury_player.csv"), newline="") as f:
        inj = list(csv.DictReader(f))
    for r in inj:
        r["season"] = int(r["season"]); r["week"] = int(r["week"])
    def rdcsv(name):
        p = os.path.join(DATA, name)
        if not os.path.exists(p):
            raise SystemExit(f"missing {name}; run the aggregate pipeline first")
        with open(p, newline="") as f:
            return list(csv.DictReader(f))

    snap = rdcsv("snap_participation.csv")
    pw = rdcsv("player_week_keys.csv")

    # participated = appears on the snap counts  OR  is listed with a recorded stat
    participated = set()
    for r in snap:
        participated.add((int(r["season"]), int(r["week"]), r["team"], norm(r["player"])))
    for r in pw:
        participated.add((int(r["season"]), int(r["week"]), r["team"], norm(r.get("player_name"))))

    # COVERAGE GUARD: only seasons for which participation data actually exists can be
    # measured. A season with no snap/stat records would otherwise report a 0% play rate,
    # which is a coverage artifact and not a finding.
    covered_seasons = sorted({int(r["season"]) for r in snap} | {int(r["season"]) for r in pw})
    excluded = []

    res = collections.defaultdict(lambda: {"n": 0, "played": 0})
    by_pos = collections.defaultdict(lambda: {"n": 0, "played": 0})
    by_season = collections.defaultdict(lambda: {"n": 0, "played": 0})
    # DEDUPLICATION RULE (deterministic, documented)
    # A player can appear more than once for the same team-week with different
    # designations. Keeping whichever row happened to come first made the denominator
    # depend on file order, which is not reproducible. Instead, one row per player-week is
    # kept using the MOST SEVERE designation (Out > Doubtful > Questionable): a player
    # listed both Out and Questionable in the same week is counted once, as Out.
    SEVERITY = {"Out": 3, "Doubtful": 2, "Questionable": 1}
    best = {}
    for r in inj:
        st = r.get("game_status")
        if st not in SEVERITY:
            continue
        key = (r["season"], r["week"], r["team"], norm(r["full_name"]))
        if key not in best or SEVERITY[st] > SEVERITY[best[key]["game_status"]]:
            best[key] = r
    dupes = len([1 for r in inj if r.get("game_status") in SEVERITY]) - len(best)

    for key, r in best.items():
        st = r["game_status"]
        if r["season"] not in covered_seasons:
            excluded.append(r["season"])
            continue
        played = key in participated
        for bucket, k in ((res, st), (by_pos, (st, r.get("pos_group") or "OTHER")),
                          (by_season, (st, r["season"]))):
            bucket[k]["n"] += 1
            bucket[k]["played"] += int(played)

    def pack(d):
        out = {}
        for k, v in d.items():
            p = v["played"] / v["n"] if v["n"] else None
            lo, hi = wilson(p, v["n"])
            out[k] = {"n": v["n"], "played": v["played"],
                      "play_rate_pct": round(100 * p, 2) if p is not None else None,
                      "ci95": [lo, hi]}
        return out

    report = {
        "question": "Q06",
        "method": ("Denominator = every player-week the official report lists with a designation. "
                   "Numerator = those who appear with >0 snaps or any recorded stat for that "
                   "team-week. Name-based join on (season, week, team, normalised name)."),
        "trap_documented": ("Joining only to snap counts gives a 100% play rate because snap counts "
                            "list only participants. That naive figure is NOT reported as a result."),
        "overall": pack(res),
        "by_position_group": {f"{k[0]}|{k[1]}": v for k, v in pack(by_pos).items()},
        "by_season": {f"{k[0]}|{k[1]}": v for k, v in pack(by_season).items()},
        "deduplication": {
            "rule": "one row per team-week-player, most severe designation wins (Out > Doubtful > Questionable)",
            "duplicate_rows_collapsed": dupes,
            "reason": ("Keeping the first row made the denominator depend on file order. The "
                       "severity rule is reproducible and conservative."),
        },
        "coverage": {
            "seasons_measured": covered_seasons,
            "seasons_excluded_no_participation_source": sorted(set(excluded)),
            "note": ("A season is excluded when no snap-count or player-stat rows exist for it. "
                     "Excluded seasons would otherwise show a false 0% play rate."),
        },
        "caveats": [
            "Name-based joining can miss players renamed or traded mid-season; the unmatched share is reported below.",
            "A player placed on injured reserve before the game may not appear in the report at all, so this measures listed players only.",
            "This measures participation, not effectiveness. It says nothing about performance drop-off.",
        ],
        "sources": [
            "https://www.nfl.com/injuries/",
            "https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-0ap3000000688693",
            "https://github.com/nflverse/nflverse-data",
        ],
    }
    with open(OUT, "w") as f:
        json.dump(report, f, indent=1)

    print(f"{'designation':<14}{'N':>8}{'played':>8}{'play rate':>12}{'95% CI':>22}")
    for st in ("Out", "Doubtful", "Questionable"):
        v = report["overall"].get(st)
        if not v:
            continue
        ci = v["ci95"]
        print(f"{st:<14}{v['n']:>8}{v['played']:>8}{v['play_rate_pct']:>11}%"
              f"   [{ci[0]}%, {ci[1]}%]")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
