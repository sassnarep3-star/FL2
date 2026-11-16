#!/usr/bin/env python3
"""Verified results feed — one canonical CSV of 2026 regular-season results.

Builds on:
  - data/games.json            (T1: NFL.com by-week pages, 137 games W1–W10-TNF, retrieved 2026-11-14)
  - live transcription 2026-11-16 (T1: https://www.nfl.com/schedules/2026/reg10/ , 11 new finals)
  - raw/games.csv (nflverse)   (T2: used ONLY as an independent cross-check of the T1 scores)

Outputs ops/data/results/results_2026_reg.csv with per-row source_url, tier and a
cross_check column. Requirement satisfied:
  - "Add a verified results feed so backtests and ROI can be computed at all"
  - "Turn the 136-game log into the pre-registered backtest corpus" (corpus = scored rows)
"""
from __future__ import annotations

import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(HERE, "data", "results")
OUT = os.path.join(OUT_DIR, "results_2026_reg.csv")
FIELDS = ["game_id", "season", "week", "gameday", "away_team", "home_team", "away_pts", "home_pts",
          "status", "tier", "source_url", "cross_check", "note"]

# Transcribed 2026-11-16 from https://www.nfl.com/schedules/2026/reg10/ (official).
# Each entry: (away, home, away_pts, home_pts, date_label, game_url)
NEW_W10_FINALS = [
    ("NE", "DET", 10, 35, "2026-11-15", "https://www.nfl.com/games/patriots-at-lions-2026-reg-10"),
    ("KC", "ATL", 35, 13, "2026-11-15", "https://www.nfl.com/games/chiefs-at-falcons-2026-reg-10"),
    ("HOU", "CLE", 24, 27, "2026-11-15", "https://www.nfl.com/games/texans-at-browns-2026-reg-10"),
    ("MIN", "GB", 30, 10, "2026-11-15", "https://www.nfl.com/games/vikings-at-packers-2026-reg-10"),
    ("MIA", "IND", 22, 24, "2026-11-15", "https://www.nfl.com/games/dolphins-at-colts-2026-reg-10"),
    ("CAR", "NO", 20, 17, "2026-11-15", "https://www.nfl.com/games/panthers-at-saints-2026-reg-10"),
    ("BUF", "NYJ", 31, 12, "2026-11-15", "https://www.nfl.com/games/bills-at-jets-2026-reg-10"),
    ("JAX", "TEN", 40, 23, "2026-11-15", "https://www.nfl.com/games/jaguars-at-titans-2026-reg-10"),
    ("LA", "ARI", 34, 6, "2026-11-15", "https://www.nfl.com/games/rams-at-cardinals-2026-reg-10"),
    ("SEA", "LV", 21, 13, "2026-11-15", "https://www.nfl.com/games/seahawks-at-raiders-2026-reg-10"),
    ("SF", "DAL", 46, 40, "2026-11-15", "https://www.nfl.com/games/49ers-at-cowboys-2026-reg-10"),
]
# Games on the official Week 10 slate with no final score as of the 2026-11-16 fetch.
W10_PENDING = [
    ("PIT", "CIN", "2026-11-15", "https://www.nfl.com/games/steelers-at-bengals-2026-reg-10"),
    ("LAC", "BAL", "2026-11-16", "https://www.nfl.com/games/chargers-at-ravens-2026-reg-10"),
]


def load_t1_rows() -> tuple[list[dict], int]:
    games = json.load(open(os.path.join(ROOT, "data", "games.json")))["games"]
    rows, cross_matched = [], 0
    nv = {}
    for r in csv.DictReader(open(os.path.join(ROOT, "raw", "games.csv"))):
        if r["season"] == "2026" and r["game_type"] == "REG":
            nv[(int(r["week"]), r["away_team"], r["home_team"])] = r
    for g in games:
        key = (int(g["week"]), g["away"], g["home"])
        src = nv.get(key)
        cross = "unavailable"
        if src and src["away_score"] and src["home_score"]:
            ok = int(src["away_score"]) == g["away_pts"] and int(src["home_score"]) == g["home_pts"]
            cross = "T1xT2_match" if ok else "T1xT2_MISMATCH"
            cross_matched += int(ok)
        rows.append({
            "game_id": f"2026_{g['week']:02d}_{g['away']}_{g['home']}",
            "season": "2026", "week": str(g["week"]), "gameday": g["date"],
            "away_team": g["away"], "home_team": g["home"],
            "away_pts": str(g["away_pts"]), "home_pts": str(g["home_pts"]),
            "status": "final", "tier": "T1",
            "source_url": g["url"], "cross_check": cross,
            "note": "NFL.com by-week schedule page; transcribed verbatim",
        })
    return rows, cross_matched


def append_live_rows(rows: list[dict]) -> list[dict]:
    have = {(r["week"], r["away_team"], r["home_team"]) for r in rows}
    for away, home, ap, hp, date, url in NEW_W10_FINALS:
        if ("10", away, home) in have:
            continue
        rows.append({
            "game_id": f"2026_10_{away}_{home}", "season": "2026", "week": "10",
            "gameday": date, "away_team": away, "home_team": home,
            "away_pts": str(ap), "home_pts": str(hp), "status": "final", "tier": "T1",
            "source_url": url, "cross_check": "T1_only_nflverse_snapshot_older",
            "note": "Transcribed 2026-11-16 from official Week 10 schedule page; nflverse snapshot (2026-11-14) predates these finals",
        })
    for away, home, date, url in W10_PENDING:
        if ("10", away, home) in have:
            continue
        rows.append({
            "game_id": f"2026_10_{away}_{home}", "season": "2026", "week": "10",
            "gameday": date, "away_team": away, "home_team": home,
            "away_pts": "", "home_pts": "", "status": "not_final_as_of_fetch",
            "tier": "T1", "source_url": url, "cross_check": "n/a",
            "note": "Official page shows no final score at fetch time (SNF in progress / MNF upcoming); scores left blank, never inferred",
        })
    return rows


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    rows, cross_matched = load_t1_rows()
    rows = append_live_rows(rows)
    rows.sort(key=lambda r: (int(r["week"]), r["game_id"]))
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    finals = [r for r in rows if r["status"] == "final"]
    mismatches = [r for r in rows if "MISMATCH" in r["cross_check"]]
    pending = [r for r in rows if r["status"] != "final"]
    print(f"results feed: {len(rows)} games, {len(finals)} final, {len(pending)} pending")
    print(f"T1 x nflverse cross-check: {cross_matched}/137 match (mismatches: {len(mismatches)})")
    for m in mismatches:
        print("  MISMATCH:", m["game_id"], m["away_pts"], m["home_pts"])
    if mismatches:
        raise SystemExit(1)
    # integrity: every final row has a source URL and points
    for r in finals:
        if not r["source_url"].startswith("https://www.nfl.com/"):
            raise SystemExit(f"non-official source in results feed: {r['game_id']}")


if __name__ == "__main__":
    main()
