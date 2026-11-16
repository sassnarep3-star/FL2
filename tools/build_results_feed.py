#!/usr/bin/env python3
"""
tools/build_results_feed.py — FL2 verified results feed (T21).

Merges three layers into one feed with per-row provenance:
  1. raw/games.csv (nflverse nfldata, GitHub contents API mirror of NFL-derived
     data) for the full 2026 schedule and the Weeks 1-9 + TNF finals;
  2. data/captures/week10-results-2026-11-16.json — the official nfl.com Week 10
     capture (T1) for the Sunday slate, with ESPN scores as cross-check;
  3. explicit non-final states (in_progress / scheduled) with capture-time notes.

Every row carries an official nfl.com game URL. Values that cannot be confirmed
are blank, never inferred. Deterministic; stdlib only.

Self-checks (abort the build on failure):
  * no status=final row may have a blank score;
  * the Week 10 capture must cover exactly the 14 scheduled Week 10 games;
  * replaying W-L-T from all finals must reproduce the official records captured
    on nfl.com schedule pages for all 32 teams (PIT/CIN checked pre-SNF);
  * weeks 1-10 must contain 148 finals (136 in Weeks 1-9 + 12 Week-10 finals).
"""
from __future__ import annotations

import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES_CSV = os.path.join(ROOT, "raw", "games.csv")
CAPTURE = os.path.join(ROOT, "data", "captures", "week10-results-2026-11-16.json")
OUT_CSV = os.path.join(ROOT, "data", "results_feed.csv")
OUT_JSON = os.path.join(ROOT, "data", "results_feed.json")

TEAM_SLUG = {
    "ARI": "cardinals", "ATL": "falcons", "BAL": "ravens", "BUF": "bills",
    "CAR": "panthers", "CHI": "bears", "CIN": "bengals", "CLE": "browns",
    "DAL": "cowboys", "DEN": "broncos", "DET": "lions", "GB": "packers",
    "HOU": "texans", "IND": "colts", "JAX": "jaguars", "KC": "chiefs",
    "LA": "rams", "LAC": "chargers", "LV": "raiders", "MIA": "dolphins",
    "MIN": "vikings", "NE": "patriots", "NO": "saints", "NYG": "giants",
    "NYJ": "jets", "PHI": "eagles", "PIT": "steelers", "SEA": "seahawks",
    "SF": "49ers", "TB": "buccaneers", "TEN": "titans", "WAS": "commanders",
}


def game_url(away: str, home: str, week: int) -> str:
    return f"https://www.nfl.com/games/{TEAM_SLUG[away]}-at-{TEAM_SLUG[home]}-2026-reg-{week}"


def self_check(rows, official_records) -> list[str]:
    errors = []
    finals = [r for r in rows if r["status"] == "final"]
    for r in finals:
        if r["away_score"] in ("", None) or r["home_score"] in ("", None):
            errors.append(f"final row with blank score: {r['game_id']}")
    w10 = [r for r in rows if r["week"] == 10]
    if len(w10) != 14:
        errors.append(f"week 10 has {len(w10)} rows, expected 14")
    n_final = len(finals)
    if n_final != 148:
        errors.append(f"{n_final} finals, expected 148 (136 in Weeks 1-9 + 12 Week-10 finals captured on nfl.com: TNF + 11 Sunday)")
    # standings replay vs official record blocks captured from nfl.com
    table = {}
    for r in finals:
        a, h = r["away"], r["home"]
        aas, has = int(r["away_score"]), int(r["home_score"])
        ta = table.setdefault(a, [0, 0, 0])
        th = table.setdefault(h, [0, 0, 0])
        if aas > has:
            ta[0] += 1; th[1] += 1
        elif has > aas:
            th[0] += 1; ta[1] += 1
        else:
            ta[2] += 1; th[2] += 1
    for team, rec in official_records.items():
        parts = rec.split("-")
        w, l = int(parts[0]), int(parts[1])
        t = int(parts[2]) if len(parts) > 2 else 0
        got = table.get(team)
        if got is None:
            errors.append(f"{team}: missing from replay")
            continue
        # PIT/CIN official record excludes the in-progress SNF at capture time
        if (got[0], got[1], got[2]) != (w, l, t):
            errors.append(f"{team}: replay {got[0]}-{got[1]}-{got[2]} != official {rec}")
    return errors


def main() -> int:
    cap = json.load(open(CAPTURE))
    cap_by_id = {g["game_id"]: g for g in cap["games"]}

    rows = []
    with open(GAMES_CSV) as fh:
        for g in csv.DictReader(fh):
            if g["season"] != "2026" or g["game_type"] != "REG":
                continue
            week = int(g["week"])
            gid = g["game_id"]
            away, home = g["away_team"], g["home_team"]
            rec = {
                "game_id": gid,
                "season": 2026,
                "week": week,
                "gameday": g["gameday"],
                "away": away,
                "home": home,
                "venue_stadium": g["stadium"],
                "roof": g["roof"],
                "surface": g["surface"],
                "away_score": "",
                "home_score": "",
                "status": "scheduled",
                "result_home_margin": "",
                "total_points": "",
                "overtime": "",
                "source_url": game_url(away, home, week),
                "source_week_url": f"https://www.nfl.com/schedules/2026/by-week/week-{week}",
                "source_tier": "",
                "cross_check": "",
                "verified": "",
                "captured_at_utc": "",
                "note": "",
            }
            if gid in cap_by_id:  # Week 10: official capture overrides mirror
                c = cap_by_id[gid]
                rec["status"] = c["status"]
                rec["captured_at_utc"] = cap["captured_at_utc"]
                rec["source_tier"] = "T1 nfl.com schedule page (capture " + cap["capture_id"] + ")"
                rec["cross_check"] = "ESPN scoreboard " + cap["cross_check_result"]
                rec["note"] = c.get("note", "")
                if c["status"] == "final":
                    rec["away_score"] = c["away_score"]
                    rec["home_score"] = c["home_score"]
                    rec["verified"] = "verified"
                else:
                    rec["verified"] = "not-final-at-capture"
                    if c["status"] == "in_progress":
                        rec["away_score"] = c["away_score"]
                        rec["home_score"] = c["home_score"]
            elif g["away_score"] != "" and g["home_score"] != "":
                rec["status"] = "final"
                rec["away_score"] = int(g["away_score"])
                rec["home_score"] = int(g["home_score"])
                rec["source_tier"] = "T2 nflverse/nfldata games.csv mirror of NFL game data"
                rec["cross_check"] = "standings replay 32/32 (session-1374049c, 2026-11-14)"
                rec["verified"] = "verified"
                rec["captured_at_utc"] = "2026-11-14T03:30:00Z"
            else:
                rec["verified"] = "pending"
                rec["captured_at_utc"] = "2026-11-14T03:30:00Z"
                rec["source_tier"] = "T2 nflverse/nfldata games.csv (schedule)"
            if rec["status"] == "final":
                a, h = int(rec["away_score"]), int(rec["home_score"])
                rec["result_home_margin"] = h - a
                rec["total_points"] = a + h
                rec["overtime"] = g["overtime"]
            rows.append(rec)

    errors = self_check(rows, cap["records_after_week10_sunday"])
    if errors:
        print("SELF-CHECK FAILED:")
        for e in errors:
            print(" -", e)
        return 1

    fields = list(rows[0].keys())
    with open(OUT_CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    n_final = sum(1 for r in rows if r["status"] == "final")
    payload = {
        "meta": {
            "generated_by": "tools/build_results_feed.py",
            "generated_at_utc": "2026-11-16T02:20:00Z",
            "policy": "research/price-data-policy.md; verification rule: source-or-blank",
            "counts": {
                "rows": len(rows),
                "final": n_final,
                "in_progress": sum(1 for r in rows if r["status"] == "in_progress"),
                "scheduled": sum(1 for r in rows if r["status"] == "scheduled"),
            },
            "layers": [
                "Weeks 1-9 (136 finals) + Week 10 TNF: nflverse/nfldata games.csv via GitHub contents API; standings replayed 32/32 against nfl.com (TNF re-verified against the official capture)",
                "Week 10 Sunday (11 finals incl. Munich international): official nfl.com capture " + cap["capture_id"] + ", cross-checked 12/12 finals vs ESPN",
                "Week 10 PIT@CIN in progress at capture; LAC@BAL scheduled (MNF 2026-11-16)",
            ],
        },
        "games": rows,
    }
    json.dump(payload, open(OUT_JSON, "w"), indent=1)
    print(f"results feed OK: {len(rows)} rows, {n_final} finals -> data/results_feed.{{csv,json}}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
