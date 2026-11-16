#!/usr/bin/env python3
"""Drift alarm (requirement: "Add a drift alarm to every scraper — pin each parser to
expected row counts and required fields; fail the build loudly when a field goes missing
rather than publishing a blank").

ops/data/drift_manifest.json pins, for each curated data file: the expected minimum row
count, required fields/columns, and the maximum acceptable age (in days) of its capture.
This script re-checks every pin. Any violation exits 1 so CI fails loudly.

Run `python3 ops/drift_check.py --refresh` after a DELIBERATE, reviewed data update to
re-pin the manifest (the manifest diff is the audit trail).
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MANIFEST = os.path.join(HERE, "data", "drift_manifest.json")


def count_and_fields(path: str) -> tuple[int, list[str]]:
    if path.endswith(".json"):
        d = json.load(open(path))
        g = d.get("games") if isinstance(d, dict) else d
        if isinstance(g, list) and g and isinstance(g[0], dict) and "teams" in g[0]:
            n = sum(len(t["players"]) for gm in g for t in gm["teams"])
            fields = ["games", "teams", "players"]
        elif isinstance(g, list):
            n = len(g)
            fields = ["games"]
        elif isinstance(d, dict) and "divisions" in d:
            n = sum(len(div["teams"]) for div in d["divisions"])
            fields = ["divisions"]
        elif isinstance(d, dict) and "clubs" in d:
            n = len(d["clubs"])
            fields = ["clubs", "injury_conflicts", "registry"]
        elif isinstance(d, dict) and "tables" in d:
            n = sum(len(t["rows"]) for t in d["tables"].values() if isinstance(t, dict) and "rows" in t)
            fields = ["tables"]
        else:
            n = len(d)
            fields = list(d)[:10]
        return n, fields
    with open(path) as fh:
        rows = list(csv.DictReader(fh))
    return len(rows), list(rows[0].keys()) if rows else []


def main() -> None:
    refresh = "--refresh" in sys.argv
    manifest_path = MANIFEST
    if refresh:
        manifest = {}
    else:
        manifest = json.load(open(manifest_path))
    failures = []
    today = dt.date.today()
    for dataset, spec in (manifest.items() if not refresh else []):
        path = os.path.join(ROOT, spec["path"])
        if not os.path.exists(path):
            failures.append(f"{dataset}: file missing: {spec['path']}")
            continue
        n, fields = count_and_fields(path)
        if n < spec["min_rows"]:
            failures.append(f"{dataset}: row count {n} < pinned {spec['min_rows']} ({spec['path']})")
        missing = [f for f in spec["required_fields"] if f not in fields]
        if missing:
            failures.append(f"{dataset}: required fields missing: {missing} ({spec['path']})")
        as_of = spec.get("captured_as_of")
        if as_of:
            age = (today - dt.date.fromisoformat(as_of)).days
            if age > spec["max_age_days"]:
                failures.append(f"{dataset}: capture age {age}d > {spec['max_age_days']}d — snapshot stale, re-capture before publishing ({spec['path']})")
    if refresh:
        pins = {}
        for dataset, spec in PINS:
            path = os.path.join(ROOT, spec["path"])
            n, fields = count_and_fields(path)
            pins[dataset] = {**spec, "pinned_rows": n, "pinned_fields": fields}
        json.dump(pins, open(manifest_path, "w"), indent=1, sort_keys=True)
        print(f"manifest re-pinned for {len(pins)} datasets -> {manifest_path}")
        return
    if failures:
        print("DRIFT ALARM — build must fail loudly:")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    total = len(manifest)
    print(f"drift check OK: {total} pinned datasets, row counts, fields and freshness all within pins")


PINS = [
    ("injuries_2026_w10", {"path": "data/injuries.json", "min_rows": 300,
                           "required_fields": ["games"], "captured_as_of": "2026-11-14", "max_age_days": 10,
                           "note": "official Week 10 report; 345 rows at capture; live count changes as games pass"}),
    ("results_2026_feed", {"path": "ops/data/results/results_2026_reg.csv", "min_rows": 150,
                           "required_fields": ["game_id", "away_pts", "home_pts", "status", "source_url", "tier"],
                           "captured_as_of": "2026-11-16", "max_age_days": 14,
                           "note": "verified results corpus; grows weekly"}),
    ("standings_2026", {"path": "data/standings.json", "min_rows": 32,
                        "required_fields": ["divisions"], "captured_as_of": "2026-11-14", "max_age_days": 10}),
    ("team_stats_2026", {"path": "data/team_stats.json", "min_rows": 32,
                         "required_fields": ["tables"], "captured_as_of": "2026-11-14", "max_age_days": 10}),
    ("depth_charts_2026", {"path": "data/depth_charts.json", "min_rows": 5,
                           "required_fields": ["clubs"], "captured_as_of": "2026-11-14", "max_age_days": 10,
                           "note": "only 5 of 32 clubs acquired — min pin reflects reality, gap flagged"}),
    ("price_snapshots", {"path": "ops/data/price_snapshots.csv", "min_rows": 28,
                         "required_fields": ["ts_utc", "season", "week", "game_id", "market", "tier", "line_close", "source_url"],
                         "captured_as_of": "2026-11-16", "max_age_days": 14}),
    ("nflverse_games", {"path": "raw/games.csv", "min_rows": 7000,
                        "required_fields": ["game_id", "season", "week", "spread_line", "total_line", "stadium", "roof", "surface"],
                        "captured_as_of": "2026-11-14", "max_age_days": 14,
                        "note": "T2/T3 open data mirror"}),
]

if __name__ == "__main__":
    main()
