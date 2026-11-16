#!/usr/bin/env python3
"""Per-team availability view (requirement: 'Add a per-team view: starters out,
replacements named, net injury count — quick team-level decision view').

Input: the verified Week 10 official injury report capture (data/injuries.json, T1,
transcribed from https://www.nfl.com/injuries/league/2026/reg10, retrieved 2026-11-14)
plus the 32-team results feed for each club's next opponent.

Published per team (all values transcribed or counted — never inferred):
  report_rows        — players listed on the official report (any status)
  out                — game_status == Out
  doubtful           — game_status == Doubtful
  questionable       — game_status == Questionable
  dnp                — practice status Did Not Participate
  designation_blank  — rows with a blank game-status cell (flagged, not guessed)
  net_injury_count   — out + doubtful (the hard designations)
  ir_unknown         — reserve/IR list is NOT captured by any verified source yet, so
                       'not listed' cannot be equated with 'available' (requirement:
                       "Capture the reserve list so 'not listed' never means 'available'")
"""
from __future__ import annotations

import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "data", "team_availability_2026_w10.csv")


def main() -> None:
    inj = json.load(open(os.path.join(ROOT, "data", "injuries.json")))
    teams: dict[str, dict] = {}
    next_opp = {}
    feed = list(csv.DictReader(open(os.path.join(HERE, "data", "results", "results_2026_reg.csv"))))
    for r in feed:
        if r["week"] == "10" and r["away_pts"] and r["home_pts"]:
            next_opp[r["away_team"]] = f"@ {r['home_team']}"
            next_opp[r["home_team"]] = f"vs {r['away_team']}"

    for g in inj["games"]:
        for tm in g["teams"]:
            t = tm["team"]
            row = teams.setdefault(t, {
                "team": t, "report_rows": 0, "out": 0, "doubtful": 0, "questionable": 0,
                "dnp": 0, "designation_blank": 0, "net_injury_count": 0,
            })
            for p in tm["players"]:
                name, pos, inj_col, prac, game_status, url = p
                row["report_rows"] += 1
                gs = (game_status or "").strip()
                prac_s = (prac or "").strip()
                if gs == "Out":
                    row["out"] += 1
                elif gs == "Doubtful":
                    row["doubtful"] += 1
                elif gs == "Questionable":
                    row["questionable"] += 1
                elif gs == "":
                    row["designation_blank"] += 1
                if prac_s.startswith("Did Not Participate"):
                    row["dnp"] += 1
            row["net_injury_count"] = row["out"] + row["doubtful"]

    out_rows = sorted(teams.values(), key=lambda r: (-r["net_injury_count"], -r["out"], r["team"]))
    for r in out_rows:
        r["next_opponent"] = next_opp.get(r["team"], "played / pending")
        r["reserve_ir_captured"] = "no — no verified source carries the reserve list yet"
        r["not_listed_means"] = "unknown (IR status not captured); cannot treat 'not listed' as available"
        r["source_url"] = inj["meta"]["source"]
        r["retrieved"] = inj["meta"]["retrieved_utc"]
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    total_rows = sum(r["report_rows"] for r in out_rows)
    hard = sum(r["net_injury_count"] for r in out_rows)
    blanks = sum(r["designation_blank"] for r in out_rows)
    q = sum(r["questionable"] for r in out_rows)
    print(f"team availability view: {len(out_rows)} clubs, {total_rows} report rows, "
          f"hard designations (Out+Doubtful) {hard}, Questionable {q}, blank designations {blanks}")
    for r in out_rows[:5]:
        print(f"  {r['team']}: rows {r['report_rows']}, out {r['out']}, doubtful {r['doubtful']}, "
              f"Q {r['questionable']}, DNP {r['dnp']}")


if __name__ == "__main__":
    main()
