#!/usr/bin/env python3
"""Price-snapshot store (append-only).

Implements requirements:
  - "Add a price-snapshot store that records opening and closing numbers for every market we originate"
  - price policy P2/P3/P6 (see ops/price_policy.md)

Rows are appended; nothing is ever overwritten (corrections use `supersedes`).
The store is seeded with the Week 10 2026 closing lines carried by the nflverse
snapshot already in the repo (T3 aggregated market data, labelled per policy).
Opening numbers are blank because that snapshot carries none (P3).
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STORE = os.path.join(HERE, "data", "price_snapshots.csv")
FIELDS = ["ts_utc", "season", "week", "game_id", "market", "tier", "line_open", "line_close",
          "home_team", "away_team", "source_url", "source_sha256", "verified_by_official_source",
          "note"]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def seed_week10_closing() -> int:
    """Append one spread row + one total row per Week 10 game from the nflverse snapshot."""
    src = os.path.join(ROOT, "raw", "games.csv")
    src_sha = sha256_file(src)
    ts = "2026-11-16T01:30:00Z"  # store created; lines are closing-as-of the 2026-11-14 snapshot
    games = [r for r in csv.DictReader(open(src)) if r["season"] == "2026" and r["week"] == "10"]
    appended = 0
    new = not os.path.exists(STORE)
    with open(STORE, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            w.writeheader()
        for g in games:
            base = {
                "ts_utc": ts, "season": "2026", "week": "10",
                "game_id": g["game_id"], "tier": "T3",
                "home_team": g["home_team"], "away_team": g["away_team"],
                "source_url": "https://github.com/nflverse/nfldata/blob/master/data/games.csv",
                "source_sha256": src_sha, "verified_by_official_source": "no",
                "note": "closing line as of nflverse snapshot 2026-11-14; no opening published by this source",
            }
            if g["spread_line"]:
                sign = "home" if float(g["spread_line"]) > 0 else "away"
                w.writerow({**base, "market": f"spread_{sign}_fav",
                            "line_open": "", "line_close": g["spread_line"]})
                appended += 1
            if g["total_line"]:
                w.writerow({**base, "market": "total", "line_open": "", "line_close": g["total_line"]})
                appended += 1
    return appended


def verify() -> list[str]:
    errors = []
    if not os.path.exists(STORE):
        return ["price store does not exist"]
    with open(STORE) as fh:
        rows = list(csv.DictReader(fh))
    seen_superseded = set()
    for r in rows:
        for f in FIELDS:
            if f not in r:
                errors.append(f"row missing field {f}")
        if r["market"] in ("", None) or r["tier"] not in ("T1", "T2", "T3"):
            errors.append(f"bad market/tier in {r['game_id']}")
        if r["tier"] != "T3" and r["verified_by_official_source"] == "no" and r["line_close"]:
            errors.append(f"T1/T2 price row without verification: {r['game_id']}")
        if r.get("supersedes"):
            seen_superseded.add(r["supersedes"])
    return errors


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "seed"
    if cmd == "seed":
        n = seed_week10_closing()
        print(f"appended {n} price-snapshot rows (Week 10 2026, T3 closing, opening blank per P3)")
    elif cmd == "verify":
        errs = verify()
        if errs:
            print("PRICE STORE FAILURES:")
            for e in errs:
                print(" -", e)
            sys.exit(1)
        rows = list(csv.DictReader(open(STORE)))
        games = sorted({r["game_id"] for r in rows})
        print(f"price store OK: {len(rows)} rows, {len(games)} games, all rows tier-labelled")
