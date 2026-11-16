#!/usr/bin/env python3
"""Automated immutable availability snapshot capture (requirements:
  - "Automate immutable multi-day availability snapshots"
  - "Build immutable official availability snapshots ... with raw hashes, timestamps and conflict flags"
  - "Snapshot the nfl.com injury report every Wed, Thu and Fri and keep a dated history"
  - "Store every injury-hub read with its clock time and publish the delta, never the level"
  - "Add a drift alarm to every scraper ... fail the build loudly when a field goes missing"

Runs in GitHub Actions (which CAN reach nfl.com; the local sandbox cannot).
Scheduled Wed/Thu/Fri 21:15 UTC (reports publish ~16:00 ET) plus manual dispatch.

Behaviour:
  1. GET the official injury report page, save the raw HTML with a UTC-stamped immutable
     filename, sha256 it.
  2. Extract structural counts (team sections, player rows, designations) — these are the
     parser's expected fields (drift alarm).
  3. Append one ledger row: clock time, hash, counts, conflict flag.
  4. DELTA PUBLICATION: compare with the previous capture; emit
     ops/data/availability_snapshots/delta_latest.json containing per-player designation
     changes (e.g. Questionable -> Out) and practice-status trends (DNP -> LP -> FP).
     The LEVEL is the raw capture; the DELTA is what gets published to the site.
  5. Exit 1 (loud failure) if the page structure is missing expected markers.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html.parser
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP_DIR = os.path.join(HERE, "data", "availability_snapshots")
REPORT_URL = "https://www.nfl.com/injuries/"
REQUIRED_MARKERS = ["Player", "Position", "Practice Status"]  # table headers of the report


class ReportParser(html.parser.HTMLParser):
    """Counts player rows in the report tables and flags structural drift."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_td = False
        self.cells: list[str] = []
        self.row: list[str] = []
        self.rows: list[list[str]] = []
        self.team_sections = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("td", "th"):
            self.in_td = True
            self.row = []
        elif tag == "tr":
            self.cells = []

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self.in_td = False
            self.cells.append(" ".join("".join(self.row).split()))
        elif tag == "tr" and self.cells:
            self.rows.append(self.cells)
            self.cells = []

    def handle_data(self, data):
        if self.in_td:
            self.row.append(data)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "FL2-availability-capture/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def main() -> None:
    os.makedirs(SNAP_DIR, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%MZ")
    raw = fetch(REPORT_URL)
    raw_path = os.path.join(SNAP_DIR, f"{stamp}-injuries.html")
    with open(raw_path, "wb") as fh:
        fh.write(raw)
    sha = hashlib.sha256(raw).hexdigest()

    text = raw.decode("utf-8", "ignore")
    missing = [m for m in REQUIRED_MARKERS if m not in text]
    if missing:
        # loud failure: schema change on the source (drift alarm requirement)
        print(f"DRIFT ALARM: injury report page missing expected markers {missing}")
        sys.exit(1)

    p = ReportParser()
    p.feed(text)
    player_rows = [r for r in p.rows if len(r) >= 5]
    counts = {
        "captured_utc": now.isoformat(timespec="seconds"),
        "source_url": REPORT_URL,
        "sha256": sha,
        "team_sections_seen": text.count("Practice Status"),
        "player_rows_seen": len(player_rows),
        "game_status_designated": sum(1 for r in player_rows if len(r) >= 5 and r[4].strip()),
        "required_markers": REQUIRED_MARKERS,
    }

    # ledger append
    ledger = os.path.join(SNAP_DIR, "index.csv")
    new = not os.path.exists(ledger)
    with open(ledger, "a", newline="") as fh:
        import csv
        w = csv.writer(fh)
        if new:
            w.writerow(["captured_utc", "sha256", "team_sections_seen", "player_rows_seen",
                        "game_status_designated", "raw_file", "conflict_flag"])
        conflict = "" if not missing else f"missing markers: {missing}"
        w.writerow([counts["captured_utc"], sha, counts["team_sections_seen"],
                    counts["player_rows_seen"], counts["game_status_designated"],
                    os.path.basename(raw_path), conflict])

    # delta vs previous capture (delta, never the level)
    htmls = sorted(f for f in os.listdir(SNAP_DIR) if f.endswith(".html"))
    if len(htmls) >= 2:
        prev = htmls[-2]
        q = ReportParser()
        q.feed(open(os.path.join(SNAP_DIR, prev)).read().decode("utf-8", "ignore"))
        prev_rows = [r for r in q.rows if len(r) >= 5]
        prev_map = {(r[0].strip(), r[1].strip()): r for r in prev_rows}
        changes = []
        for r in player_rows:
            key = (r[0].strip(), r[1].strip())
            old = prev_map.get(key)
            if old and (old[3].strip() != r[3].strip() or old[4].strip() != r[4].strip()):
                changes.append({
                    "player": r[0].strip(), "position": r[1].strip(),
                    "practice_prev": old[3].strip(), "practice_now": r[3].strip(),
                    "game_status_prev": old[4].strip(), "game_status_now": r[4].strip(),
                })
        delta = {
            "as_of": counts["captured_utc"],
            "previous_capture_utc": prev,
            "n_player_rows_now": counts["player_rows_seen"],
            "n_player_rows_prev": len(prev_rows),
            "designations_changed": changes,
            "level_note": "levels live in the immutable raw captures; only this delta is published",
        }
        with open(os.path.join(SNAP_DIR, "delta_latest.json"), "w") as fh:
            json.dump(delta, fh, indent=1)
        counts["delta_changes_vs_previous"] = len(changes)

    print(json.dumps(counts, indent=1))


if __name__ == "__main__":
    main()
