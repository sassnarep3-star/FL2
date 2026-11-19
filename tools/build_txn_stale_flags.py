#!/usr/bin/env python3
"""Join official NFL transaction rows to club depth rows and flag stale depth.

Inputs:
  private/transactions-2026-oct-nov.csv   official nfl.com transaction rows (PRIVATE: row-level
                                          NFL.com content, terms s.1.3 gate F-T1; never committed)
  data/depth_charts.json                  club-published depth charts (5 of 32 clubs)

Output:
  private/stale-depth-flags.csv           (PRIVATE, never committed)

Classification of every (depth row, player, official event) match:
  STALE-AFTER-CAPTURE  event date is later than the depth capture date -> the depth row
                       cannot reflect the event. Counted as a stale flag.
  SAME-DAY-UNRESOLVED  event date equals the capture date -> ordering unknown, not counted.
  PRE-CAPTURE-UNCLEARED event date is before the capture date. The page's own date is not
                       published (page_date is null), so this is NOT cleared as current.

A roster event never clears a depth row; it only versions it. The script never edits
depth data and never infers a replacement: it reports the name match and the date order.
"""
import csv
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
TXN = ROOT / "private/transactions-2026-oct-nov.csv"
DEPTH = ROOT / "data/depth_charts.json"
OUT = ROOT / "private/stale-depth-flags.csv"


def norm(name: str) -> str:
    return re.sub(r"[^a-z]", "", name.lower())


def main() -> None:
    depth = json.loads(DEPTH.read_text(encoding="utf-8"))
    captured = depth["meta"]["retrieved_utc"]  # e.g. 2026-11-14
    events = list(csv.DictReader(TXN.open(encoding="utf-8")))

    rows_out = []
    for club in depth["clubs"]:
        if club.get("status") != "verified":
            continue
        team = club["team"]
        for unit, rows in club["units"].items():
            for row in rows:
                pos, slots = row[0], row[1:]
                for rank, player in enumerate(slots, start=1):
                    if not player:
                        continue
                    for ev in events:
                        if norm(ev["player"]) != norm(player):
                            continue
                        if team not in (ev["team_from"], ev["team_to"]):
                            continue
                        d = ev["event_date"]
                        if d > captured:
                            status = "STALE-AFTER-CAPTURE"
                        elif d == captured:
                            status = "SAME-DAY-UNRESOLVED"
                        else:
                            status = "PRE-CAPTURE-UNCLEARED"
                        rows_out.append({
                            "club": team,
                            "unit": unit,
                            "position_row": pos,
                            "depth_rank": rank,
                            "player_on_depth_chart": player,
                            "depth_captured_utc": captured,
                            "event_date": d,
                            "transaction_type": ev["transaction_type"],
                            "team_from": ev["team_from"],
                            "team_to": ev["team_to"],
                            "flag_status": status,
                            "official_source_url": ev["official_source_url"],
                            "depth_source_url": club["source"],
                        })

    fields = list(rows_out[0].keys()) if rows_out else ["club"]
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows_out)

    counts = {}
    for r in rows_out:
        counts[r["flag_status"]] = counts.get(r["flag_status"], 0) + 1
    print(f"matches: {len(rows_out)} {counts}")


if __name__ == "__main__":
    main()
