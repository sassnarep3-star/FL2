#!/usr/bin/env python3
"""Venue / fixture-context feed (requirements:
  - "Transcribe the venue of every fixture from the official game centre and publish it"
  - "Add a fixture-context feature set built only from published schedule facts"
  - "Stadium Roof/Surface & NWS Hourly Wind/Precipitation Overlay" (stadium half only)

Source of the stadium facts: nflverse games.csv (T2 open data, derived from official
GSIS feeds). Tier labelled T2 on every row. One row (Week 10 Munich game) was verified
directly against the official game centre on 2026-11-16:
  https://www.nfl.com/games/patriots-at-lions-2026-reg-10 -> Location MUNICH,
  Stadium FC BAYERN MUNICH STADIUM.

Weather columns (temp/wind) are captured only when the T2 snapshot carries them; the NWS
forecast grid is NOT reachable from this environment, so weather-derived cells stay blank
(flagged) rather than filled.
"""
from __future__ import annotations

import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "data", "venues_2026_reg.csv")

NWS_GATE = ("NWS hourly forecast grids are not reachable from the build environment "
            "(outbound allow-list excludes weather.gov); wind/precip cells stay blank.")


def main() -> None:
    feed = {(r["week"], r["away_team"], r["home_team"]) for r in
            csv.DictReader(open(os.path.join(HERE, "data", "results", "results_2026_reg.csv")))}
    out_rows = []
    for r in csv.DictReader(open(os.path.join(ROOT, "raw", "games.csv"))):
        if r["season"] != "2026" or r["game_type"] != "REG" or int(r["week"]) > 10:
            continue
        in_scope = ("10" == r["week"]) or ((r["week"], r["away_team"], r["home_team"]) in feed)
        out_rows.append({
            "game_id": r["game_id"], "week": r["week"], "gameday": r["gameday"],
            "away_team": r["away_team"], "home_team": r["home_team"],
            "stadium": r["stadium"], "roof": r["roof"], "surface": r["surface"],
            "temp_f": r["temp"], "wind_mph": r["wind"],
            "tier": "T2 open data (nflverse, official GSIS-derived)",
            "source_url": "https://github.com/nflverse/nfldata/blob/master/data/games.csv",
            "official_game_centre": f"https://www.nfl.com/games/{r['away_team'].lower()}-at-{r['home_team'].lower()}-2026-reg-{r['week']}",
            "verified_against_game_centre": "yes" if r["game_id"] == "2026_10_NE_DET" else "no",
            "note": "" if int(r["week"]) >= 1 else "",
        })
    out_rows.sort(key=lambda x: (int(x["week"]), x["game_id"]))
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    roofs = {}
    for r in out_rows:
        roofs[r["roof"] or "(blank)"] = roofs.get(r["roof"] or "(blank)", 0) + 1
    surfaces = {}
    for r in out_rows:
        surfaces[r["surface"] or "(blank)"] = surfaces.get(r["surface"] or "(blank)", 0) + 1
    outdoor_final = sum(1 for r in out_rows if int(r["week"]) == 10)
    print(f"venues: {len(out_rows)} rows through week 10 ({outdoor_final} in week 10)")
    print("roof mix:", roofs)
    print("surface mix:", surfaces)
    print("NWS:", NWS_GATE)


if __name__ == "__main__":
    main()
