#!/usr/bin/env python3
"""Point-in-time snapshot ledger (requirements:
  - "Point-in-Time Snapshot Ledger for Injuries, Depth Charts & Inactives"
  - "Build immutable official availability snapshots ... with raw hashes, timestamps and conflict flags"
  - "Store every injury-hub read with its clock time and publish the delta, never the level"
  - "Treat roster turnover as a first-class data event")

The ledger is append-only. Every existing capture in the repository is registered here
with: the capture's own as_of stamp, the sha256 of the file as committed, its official
source URL, and any conflict/supersession flags. Future captures append rows; nothing
is edited or removed.

Schema: ops/data/snapshots/ledger.csv
"""
from __future__ import annotations

import csv
import hashlib
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LEDGER = os.path.join(HERE, "data", "snapshots", "ledger.csv")
FIELDS = ["entry_id", "captured_as_of", "registered_utc", "dataset", "path", "sha256", "row_count",
          "source_url", "conflicts", "superseded_by", "note"]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def count_rows(path: str) -> str:
    if path.endswith(".json"):
        import json
        d = json.load(open(path))
        if isinstance(d, dict):
            g = d.get("games")
            if isinstance(g, list) and g and isinstance(g[0], dict):
                if "teams" in g[0] and "players" in g[0]["teams"][0]:  # injury report
                    return str(sum(len(t["players"]) for gm in g for t in gm["teams"]))
                return str(len(g))  # schedule / results
            if "teams" in d and isinstance(d["teams"], list):  # fl2-dashboard capture
                return str(sum(len(t.get("rows", [])) for t in d["teams"]))
            if "divisions" in d:
                return str(sum(len(div["teams"]) for div in d["divisions"]))
            if "clubs" in d:
                return str(len(d["clubs"]))
            return str(len(d))
        return str(len(d))
    if path.endswith(".csv"):
        with open(path) as fh:
            return str(sum(1 for _ in fh) - 1)
    return ""


# The captures that already exist in the repository, with the as_of each one claims for itself.
EXISTING = [
    # (dataset, path, captured_as_of, source_url, conflicts, superseded_by, note)
    ("injury_report_w10_2026", "data/injuries.json", "2026-11-14",
     "https://www.nfl.com/injuries/league/2026/reg10", "", "",
     "fl2-signals capture: 345 rows, 28 clubs; SEA/CIN sections present; Lions designations populated"),
    ("injury_report_w10_2026", "fl2-dashboard/data/verified/injuries-week10.json", "2026-11-14",
     "https://www.nfl.com/injuries/", "", "",
     "fl2-dashboard capture: 345 rows, 28 clubs (earlier 254-row state described in requirement re-capture item predates this committed file)"),
    ("injury_report_w10_2026_csv", "data/injuries_2026_week10.csv", "2026-11-14",
     "https://www.nfl.com/injuries/league/2026/reg10", "", "", "fl2-signals CSV export of the same capture"),
    ("injury_report_w10_2026_depthcsv", "data/injury-report-2026-w10.csv", "2026-11-14",
     "https://www.nfl.com/injuries/", "", "",
     "160-row depth-annotated subset (Out/Doubtful rows only) with depth_string/depth_basis/next_man_up columns"),
    ("standings_2026", "data/standings.json", "2026-11-14", "https://www.nfl.com/standings/",
     "", "", "T1 transcription; 32/32 rows reproduce from the game replay"),
    ("schedule_w10_2026", "data/schedule_week10.json", "2026-11-14", "https://www.nfl.com/schedules/2026/reg10",
     "", "", "14-game slate; only TNF had kicked off at retrieval"),
    ("depth_charts_2026", "data/depth_charts.json", "2026-11-14",
     "https://www.nfl.com/teams/", "club charts captioned unofficial by clubs; 27 of 32 clubs not acquired",
     "", "5 clubs captured (NE, DET, GB, KC, SF)"),
    ("games_2026_w1_10", "data/games.json", "2026-11-14",
     "https://www.nfl.com/schedules/2026/by-week/week-{1..10}", "", "", "137 games through W10 TNF"),
    ("market_lines_w10_2026", "data/market_lines.json", "2026-11-14",
     "https://github.com/nflverse/nfldata/blob/master/data/games.csv", "market prices are T3, unverified by any official source",
     "", "originated fair lines for the Week 10 slate"),
    ("nflverse_games_2026", "raw/games.csv", "2026-11-14 snapshot",
     "https://github.com/nflverse/nfldata/blob/master/data/games.csv", "", "",
     "T2/T3 open data; used for cross-checks and closing lines only"),
]

REGISTERED_UTC = "2026-11-16T01:45:00Z"


def main() -> None:
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    exists = os.path.exists(LEDGER)
    existing_keys = set()
    if exists:
        with open(LEDGER) as fh:
            for r in csv.DictReader(fh):
                existing_keys.add((r["dataset"], r["path"], r["captured_as_of"]))
    with open(LEDGER, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if not exists:
            w.writeheader()
        n = 0
        eid = sum(1 for _ in open(LEDGER)) if exists else 0
        for dataset, path, as_of, src, conflicts, sup, note in EXISTING:
            key = (dataset, path, as_of)
            if key in existing_keys:
                continue
            full = os.path.join(ROOT, path)
            if not os.path.exists(full):
                raise SystemExit(f"ledger references missing file: {path}")
            eid += 1
            w.writerow({
                "entry_id": f"SNAP-{eid:04d}", "captured_as_of": as_of, "registered_utc": REGISTERED_UTC,
                "dataset": dataset, "path": path, "sha256": sha256_file(full),
                "row_count": count_rows(full), "source_url": src, "conflicts": conflicts,
                "superseded_by": sup, "note": note,
            })
            n += 1
    rows = list(csv.DictReader(open(LEDGER)))
    print(f"snapshot ledger: {len(rows)} entries ({n} newly registered), all sha256-stamped")
    if not exists:
        print("delta policy: future reads of the same dataset append a new row; the DELTA between rows is what gets published, never a silently-updated level")


if __name__ == "__main__":
    main()
