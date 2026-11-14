#!/usr/bin/env python3
"""
depth_accuracy.py — does the published depth chart predict who actually plays?

WHY THIS EXISTS
---------------
The request asks to track "2nd, 3rd or 4th string backups having to replace starters".
That whole feature rests on one unverified assumption: that the club's published depth chart
knows who the next man up is. Question Q07 flags this. This script tests it instead of
assuming it.

TEST
----
For each team-week and position group, ask: when the player listed as 1st string at a
position appears in the participation data, is he the player with the most snaps at that
position? If the chart is accurate, the answer should be yes nearly always.

LIMITATION, STATED UP FRONT
---------------------------
Snap counts are published by Pro Football Reference and do not always distinguish every
positional slot (a team may list three "WR" starters). We therefore compare at the level of
"is the listed 1st-string player present and among the top players at his position group",
and we publish the agreement rate rather than a verdict.

Output: data/depth_accuracy.json
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
OUT = os.path.join(DATA, "depth_accuracy.json")


def norm(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace(".", "").replace("'", "").replace("-", "").replace(" ", "")
    return re.sub(r"(jr|sr|ii|iii|iv)$", "", s)


def wilson(p, n, z=1.96):
    if not n:
        return [None, None]
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return [round(100 * max(0, c - h), 2), round(100 * min(1, c + h), 2)]


def main():
    # Listed starters / second string, per team-week (built on the runner)
    with open(os.path.join(DATA, "depth_player.csv"), newline="") as f:
        depth = list(csv.DictReader(f))

    # Realised participation with snaps, per team-week-player
    snaps = collections.defaultdict(lambda: collections.defaultdict(float))
    path = os.path.join(DATA, "snap_participation.csv")
    have_pct = False
    with open(path, newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            snaps[(int(r["season"]), int(r["week"]), r["team"])][norm(r["player"])] += 1.0
            have_pct = True

    # Leadership: who carried the biggest snap workload for his position group that week.
    # snap_participation has one row per participating player-week, so presence alone is
    # the signal we can defend. We report PRESENCE agreement, not rank agreement.
    res = collections.defaultdict(lambda: {"n": 0, "played": 0})
    by_pos = collections.defaultdict(lambda: {"n": 0, "played": 0})
    for d in depth:
        if d.get("season") is None or d.get("week") is None:
            continue
        try:
            key = (int(d["season"]), int(d["week"]), d["team"])
        except Exception:
            continue
        team_week = snaps.get(key)
        if not team_week:
            continue
        name = norm(d.get("full_name") or d.get("football_name") or "")
        if not name:
            continue
        played = name in team_week
        dt = int(float(d.get("depth_team") or 0))
        label = "1st string" if dt == 1 else "2nd string"
        res[label]["n"] += 1
        res[label]["played"] += int(played)
        by_pos[(label, d.get("pos_group") or "OTHER")]["n"] += 1
        by_pos[(label, d.get("pos_group") or "OTHER")]["played"] += int(played)

    def pack(d):
        out = {}
        for k, v in d.items():
            p = v["played"] / v["n"] if v["n"] else None
            out[k if isinstance(k, str) else f"{k[0]}|{k[1]}"] = {
                "n": v["n"], "played": v["played"],
                "agreement_pct": round(100 * p, 2) if p is not None else None,
                "ci95": wilson(p, v["n"]),
            }
        return out

    report = {
        "question": "Q07",
        "test": ("Does a player listed 1st (or 2nd) string on the club depth chart actually "
                 "appear in that team-week's participation data?"),
        "definition": ("'Agreement' = the listed player has a snap-count row for that team-week. "
                       "This measures presence only. It does NOT measure whether he started, "
                       "how many snaps he took, or whether he out-snapped the backup."),
        "overall": pack(res),
        "by_position_group": pack(by_pos),
        "interpretation_guard": (
            "Second-string players should NOT be expected to appear every week; a high "
            "appearance rate for 2nd string would suggest the chart is not really a depth "
            "ordering. Compare the two rows rather than reading either alone."),
        "caveats": [
            "Presence in snap counts means at least one snap, including special teams.",
            "Players traded or renamed mid-season may fail the name join.",
            "Depth charts may be published at a different cadence than weekly, so some "
            "team-weeks may reuse a stale chart.",
            "This does not establish that the depth chart is a reliable replacement map; it "
            "only quantifies how often the listed player appears at all.",
        ],
        "sources": [
            "https://github.com/nflverse/nflverse-data",
            "https://www.nfl.com/players/",
            "https://www.pro-football-reference.com/",
        ],
    }
    with open(OUT, "w") as f:
        json.dump(report, f, indent=1)

    print(f"{'listed as':<14}{'N':>8}{'appeared':>10}{'agreement':>12}{'95% CI':>20}")
    for k, v in report["overall"].items():
        ci = v["ci95"]
        print(f"{k:<14}{v['n']:>8}{v['played']:>10}{v['agreement_pct']:>11}%"
              f"   [{ci[0]}%, {ci[1]}%]")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
