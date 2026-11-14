#!/usr/bin/env python3
"""
ingest.py — build a provenance manifest for every raw data file.

Every raw file is recorded with:
  - the exact official/primary SOURCE URL it was downloaded from
  - SHA-256 so a reviewer can confirm the bytes
  - row counts and the season it covers

Run:  python3 analysis/ingest.py
Out:  data/manifest.json
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# This section lives in signal/ ; ROOT is signal/ and data/ is signal/data.
RAW = os.path.join(ROOT, "raw")
OUT = os.path.join(ROOT, "data", "manifest.json")

BASE = "https://github.com/nflverse/nflverse-data/releases/download"

# (regex on filename) -> (release tag, url template, human description)
PATTERNS = [
    (r"^injuries_(\d{4})\.csv$", "injuries",
     lambda m: f"{BASE}/injuries/injuries_{m.group(1)}.csv",
     "Weekly practice/game status injury report"),
    (r"^depth_charts_(\d{4})\.csv$", "depth_charts",
     lambda m: f"{BASE}/depth_charts/depth_charts_{m.group(1)}.csv",
     "Weekly depth chart (starter / 2nd / 3rd string)"),
    (r"^snap_counts_(\d{4})\.csv$", "snap_counts",
     lambda m: f"{BASE}/snap_counts/snap_counts_{m.group(1)}.csv",
     "Per-game offensive/defensive snap counts by player"),
    (r"^stats_player_week_(\d{4})\.csv$", "stats_player",
     lambda m: f"{BASE}/stats_player/stats_player_week_{m.group(1)}.csv",
     "Weekly player statistics"),
    (r"^play_by_play_(\d{4})\.csv$", "pbp",
     lambda m: f"{BASE}/pbp/play_by_play_{m.group(1)}.csv",
     "Play-by-play"),
    (r"^games\.csv$", "schedules",
     lambda m: f"{BASE}/schedules/games.csv",
     "Game schedule + results + closing spread/total/moneyline"),
    (r"^players\.csv$", "players",
     lambda m: f"{BASE}/players/players.csv",
     "Player master (ids, birth dates, positions)"),
    (r"^teams\.csv$", "teams",
     lambda m: f"{BASE}/teams/teams.csv",
     "Team master"),
]

# Upstream project that produces/maintains each dataset — the primary source to cite.
UPSTREAM = {
    "injuries": {
        "publisher": "nflverse (primary source: NFL.com official injury report)",
        "primary": "https://www.nfl.com/injuries/",
        "docs": "https://nflreadr.nflverse.com/articles/dictionary_injuries.html",
        "loader": "https://github.com/nflverse/nflreadr/blob/main/R/load_injuries.R",
    },
    "depth_charts": {
        "publisher": "nflverse (scraped from club/league depth charts)",
        "primary": "https://www.nfl.com/players/",
        "docs": "https://nflreadr.nflverse.com/articles/dictionary_depth_charts.html",
        "loader": "https://github.com/nflverse/nflreadr/blob/main/R/load_depth_charts.R",
    },
    "snap_counts": {
        "publisher": "nflverse / Pro Football Reference",
        "primary": "https://www.pro-football-reference.com/",
        "docs": "https://nflreadr.nflverse.com/articles/dictionary_snap_counts.html",
        "loader": "https://github.com/nflverse/nflreadr/blob/main/R/load_snap_counts.R",
    },
    "stats_player": {
        "publisher": "nflverse (built from NFL play-by-play via nflfastR)",
        "primary": "https://www.nfl.com/scores/",
        "docs": "https://nflreadr.nflverse.com/articles/dictionary_player_stats.html",
        "loader": "https://github.com/nflverse/nflreadr/blob/main/R/load_player_stats.R",
    },
    "pbp": {
        "publisher": "nflverse (nflfastR build of NFL Game Center play-by-play)",
        "primary": "https://www.nfl.com/scores/",
        "docs": "https://nflreadr.nflverse.com/articles/dictionary_pbp.html",
        "loader": "https://github.com/nflverse/nflreadr/blob/main/R/load_pbp.R",
    },
    "schedules": {
        "publisher": "nflverse / Lee Sharpe (nfldata)",
        "primary": "https://www.nfl.com/schedules/",
        "docs": "https://nflreadr.nflverse.com/articles/dictionary_schedules.html",
        "loader": "https://github.com/nflverse/nflreadr/blob/main/R/load_schedules.R",
    },
    "players": {
        "publisher": "nflverse",
        "primary": "https://www.nfl.com/players/",
        "docs": "https://nflreadr.nflverse.com/articles/dictionary_players.html",
        "loader": "https://github.com/nflverse/nflreadr/blob/main/R/load_players.R",
    },
    "teams": {
        "publisher": "nflverse",
        "primary": "https://www.nfl.com/teams/",
        "docs": "https://nflreadr.nflverse.com/articles/dictionary_teams.html",
        "loader": "https://github.com/nflverse/nflreadr/blob/main/R/load_teams.R",
    },
}


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_rows(path: str):
    """Return (data_rows, columns) counting CSV records, not physical lines."""
    import csv
    try:
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            r = csv.reader(f)
            header = next(r)
            n = sum(1 for _ in r)
        return n, len(header)
    except Exception as e:  # pragma: no cover
        return None, str(e)


def main() -> int:
    if not os.path.isdir(RAW):
        print(f"no raw/ directory at {RAW}", file=sys.stderr)
        return 1
    entries = []
    for name in sorted(os.listdir(RAW)):
        path = os.path.join(RAW, name)
        if not os.path.isfile(path):
            continue
        matched = False
        for rx, tag, urlfn, desc in PATTERNS:
            m = re.match(rx, name)
            if not m:
                continue
            matched = True
            rows, cols = count_rows(path)
            season = int(m.group(1)) if m.groups() else None
            entries.append({
                "file": f"raw/{name}",
                "dataset": tag,
                "description": desc,
                "season": season,
                "source_url": urlfn(m),
                "bytes": os.path.getsize(path),
                "sha256": sha256(path),
                "data_rows": rows,
                "columns": cols,
                "upstream": UPSTREAM.get(tag, {}),
                "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
            print(f"{name:34s} {tag:13s} rows={rows!s:>9} {os.path.getsize(path):>11,} B")
        if not matched:
            print(f"SKIP (no pattern) {name}")

    manifest = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": "analysis/ingest.py",
        "license_note": (
            "nflverse data is published under CC-BY-4.0 by the nflverse project. "
            "Football statistics themselves are facts; see the nflverse license."
        ),
        "license_url": "https://github.com/nflverse/nflverse-data/blob/master/LICENSE.md",
        "nflverse_readme": "https://github.com/nflverse/nflverse-data/blob/master/README.md",
        "file_count": len(entries),
        "files": entries,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nwrote {OUT}  ({len(entries)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
