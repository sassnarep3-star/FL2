#!/usr/bin/env python3
"""Validate the captured depth data before it is published.

These are structural checks that a mis-parse cannot pass. They do not check that the
league's numbers are right -- the league is the source and its figures are taken as
given -- only that what we parsed out of the PDFs is internally consistent and
complete enough to be used.

Exit code 0 = all checks pass, 1 = at least one check failed.
"""

from __future__ import annotations

import csv
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "fl2-depth", "data", "verified")
SEASON, WEEK = "2026", "10"

# Offensive snap totals read by hand from the game books during the manual
# verification pass. If the mechanical capture disagrees with these, the parser is
# wrong, not the league.
HAND_READ_OFF_SNAPS = {
    ("2026_10_WAS_NYG", "Washington Commanders"): 69,
    ("2026_10_WAS_NYG", "New York Giants"): 65,
    ("2026_10_NE_DET", "New England Patriots"): 59,
    ("2026_10_NE_DET", "Detroit Lions"): 71,
    ("2026_10_KC_ATL", "Kansas City Chiefs"): 65,
    ("2026_10_KC_ATL", "Atlanta Falcons"): 72,
    ("2026_10_HOU_CLE", "Houston Texans"): 67,
    ("2026_10_HOU_CLE", "Cleveland Browns"): 68,
    ("2026_10_MIN_GB", "Minnesota Vikings"): 69,
    ("2026_10_MIN_GB", "Green Bay Packers"): 55,
}

EXPECTED_STARTERS_PER_UNIT = 11


def read(name: str) -> list:
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    failures, warnings, checks = [], [], 0

    def check(ok: bool, label: str, detail: str = "") -> None:
        nonlocal checks
        checks += 1
        if not ok:
            failures.append(f"{label}{(' -- ' + detail) if detail else ''}")

    gamebooks = read(f"gamebooks-{SEASON}-w{WEEK}.csv")
    starters = read(f"starters-{SEASON}-w{WEEK}.csv")
    playtime = read(f"playtime-{SEASON}-w{WEEK}.csv")
    inactives = read(f"inactives-{SEASON}-w{WEEK}.csv")

    captured = [g for g in gamebooks if g["status"] == "captured"]
    for g in gamebooks:
        if g["status"].startswith("captured") and not int(g.get("playtime_rows") or 0):
            warnings.append("%s: book captured but the playtime table is absent "
                            "(snap counts left blank, not inferred)" % g["game_id"])
        if not sum(1 for r in starters if r["game_id"] == g["game_id"]):
            warnings.append("%s: no starter rows parsed" % g["game_id"])
    check(bool(gamebooks), "the game-book register is not empty")
    check(bool(captured), "at least one game was captured")

    # --- provenance -----------------------------------------------------------
    check(all(r.get("source_url") for r in starters + playtime + inactives),
          "every data row carries the URL of the PDF it came from")
    hashes = Counter(g["pdf_sha256"] for g in captured if g.get("pdf_sha256"))
    dupes = [h for h, n in hashes.items() if n > 1]
    check(not dupes, "no two captured games share a PDF hash", str(dupes)[:120])
    check(all(g.get("pdf_sha256") for g in captured),
          "every captured game records a PDF SHA-256")

    # --- starters -------------------------------------------------------------
    per_unit = Counter((r["game_id"], r["club"], r["unit"]) for r in starters)
    bad = {k: v for k, v in per_unit.items() if v != EXPECTED_STARTERS_PER_UNIT}
    check(not bad, f"every club-game has exactly {EXPECTED_STARTERS_PER_UNIT} starters "
                   "per unit", str(bad)[:200])
    check(all(r.get("player_raw") for r in starters), "no starter row has an empty name")
    check(all(r.get("slot") for r in starters), "no starter row has an empty slot")

    # --- snap counts ----------------------------------------------------------
    check(bool(playtime), "snap-count rows were parsed")
    over = [r for r in playtime
            for k in ("off_pct", "def_pct", "st_pct")
            if r.get(k) and int(r[k]) > 100]
    check(not over, "no player is credited with more than 100% of a unit", str(over[:3]))

    max_off = {}
    for r in playtime:
        if r.get("off_snaps"):
            k = (r["game_id"], r["club"])
            max_off[k] = max(max_off.get(k, 0), int(r["off_snaps"]))
    for k, expected in HAND_READ_OFF_SNAPS.items():
        got = max_off.get(k)
        check(got == expected,
              f"{k[0]} {k[1]}: top offensive snap count matches the hand-read value",
              f"parsed {got}, hand-read {expected}")

    clubs_with_snaps = len({(r["game_id"], r["club"]) for r in playtime})
    check(clubs_with_snaps == 2 * len(captured),
          "both clubs of every captured game have snap rows",
          f"{clubs_with_snaps} club-games vs {2 * len(captured)} expected")

    # --- inactives ------------------------------------------------------------
    check(all(r.get("club") for r in inactives),
          "every inactive row is attributed to a club")
    check({r["list_type"] for r in inactives} <= {"not_active", "did_not_play"},
          "inactive rows use only the two official list types")

    # --- report ---------------------------------------------------------------
    print(f"depth validation: {checks - len(failures)}/{checks} checks passed")
    print(f"  games captured      {len(captured)} of {len(gamebooks)}")
    print(f"  starter rows        {len(starters)}")
    print(f"  snap-count rows     {len(playtime)}")
    print(f"  inactive / DNP rows {len(inactives)}")
    for w in warnings:
        print(f"  WARN: {w}")
    for f in failures:
        print(f"  FAIL: {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
