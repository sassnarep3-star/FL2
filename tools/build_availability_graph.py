#!/usr/bin/env python3
"""
tools/build_availability_graph.py — availability graph (T25).

First-class dataset: who was EXPECTED to start (club chart rows as captured, never
re-ranked), who is OUT (official report designations), which replacement is
ANNOUNCED by a dated official source, and who ACTUALLY played (blank + flagged
without a game-day source — never inferred).

Sources (source-or-blank):
  * data/injuries.json — nfl.com Week 10 report transcription (345 rows, 2026-11-14),
    every player row carries its nfl.com player URL.
  * data/depth_charts.json — 5 captured club depth pages with date + source per club,
    plus its injury_conflicts block (stale/contradicted depth rows).
  * data/news_2026_week10.csv — dated nfl.com news rows (pipe-delimited).
  * official recount 2026-11-16 (347 rows) via session 8326a20d team summary.

Emits data/availability_graph.json. Deterministic; stdlib only.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_pipe_news():
    rows = []
    with open(os.path.join(ROOT, "data", "news_2026_week10.csv")) as fh:
        header = fh.readline()
        for line in fh:
            line = line.strip("\n")
            if not line:
                continue
            parts = line.split("|")
            if len(parts) < 3:
                continue
            rows.append({"date": parts[0], "headline": parts[1],
                         "source_url": parts[2], "listed_on_page": parts[3] if len(parts) > 3 else ""})
    return rows


def main() -> int:
    inj = json.load(open(os.path.join(ROOT, "data", "injuries.json")))
    feed = json.load(open(os.path.join(ROOT, "data", "results_feed.json")))
    depth = json.load(open(os.path.join(ROOT, "data", "depth_charts.json")))
    news = read_pipe_news()

    w10_by_team = {}
    for g in feed["games"]:
        if g["week"] == 10:
            w10_by_team.setdefault(g["home"], []).append(g)
            w10_by_team.setdefault(g["away"], []).append(g)

    designations = {}
    for game in inj["games"]:
        for t in game["teams"]:
            rows = designations.setdefault(t["team"], [])
            for p in t["players"]:
                name, pos, injury, practice, status, url = (list(p) + [""] * 6)[:6]
                rows.append({"player": name, "position": pos, "injury": injury,
                             "practice_status": practice, "game_status": status,
                             "source_url": url})

    chart = {}
    for club in depth.get("clubs", []):
        if club.get("status") != "verified":
            continue
        slots = []
        units = club.get("units", {})
        for unit in ("offense", "defense", "special", "special_teams"):
            for row in units.get(unit, []):
                if not row:
                    continue
                names = [n for n in row[1:] if n]
                slots.append({"unit": unit, "position": row[0],
                              "chart_row_names_published_order": names,
                              "shared_slot": len(names) > 1,
                              "note": "club-published order preserved verbatim; rank groups not re-derived (DR-50 rejection)"})
        chart[club["team"]] = {"slots": slots, "source": club.get("source", ""),
                               "page_date": club.get("page_date", ""),
                               "disclaimer": club.get("disclaimer_on_page", "")}

    all_teams = set()
    for g in feed["games"]:
        all_teams.add(g["home"]); all_teams.add(g["away"])
    teams = sorted(all_teams | set(designations) | set(chart))
    per_team = []
    for t in teams:
        games = w10_by_team.get(t, [])
        g = games[0] if games else None
        rows = designations.get(t, [])
        out = [r for r in rows if r["game_status"] == "Out"]
        doubtful = [r for r in rows if r["game_status"] == "Doubtful"]
        questionable = [r for r in rows if r["game_status"] == "Questionable"]
        per_team.append({
            "team": t,
            "week": 10,
            "opponent": (g["away"] if g and g["home"] == t else g["home"]) if g else "",
            "game_id": g["game_id"] if g else "",
            "week10_state": "played" if g else "bye — no Week 10 report exists; absence of rows is NOT a health claim",
            "chart": chart.get(t),
            "chart_flag": "" if t in chart else "no verified club depth page captured (F-D1) — chart layer blank, NOT inferred",
            "out": out, "doubtful": doubtful, "questionable": questionable,
            "net_injury_count_out_doubtful": len(out) + len(doubtful),
            "announced_replacements": [],
            "actually_played": "",
            "actually_played_flag": "blank: game-day inactive/actives list not captured (DR-31) — never inferred",
        })

    ABBR = {"Colts": "IND", "Dolphins": "MIA", "Ravens": "BAL", "Lions": "DET",
            "Packers": "GB", "Seahawks": "SEA", "Commanders": "WAS", "Giants": "NYG",
            "Jets": "NYJ", "Broncos": "DEN", "Raiders": "LV", "Bengals": "CIN",
            "Vikings": "MIN", "Bears": "CHI", "Chiefs": "KC", "Bills": "BUF"}
    for e in news:
        for name, abbr in ABBR.items():
            if name.lower() in (e["headline"] or "").lower():
                for row in per_team:
                    if row["team"] == abbr:
                        row["announced_replacements"].append(e)

    payload = {
        "meta": {
            "generated_by": "tools/build_availability_graph.py",
            "generated_at_utc": "2026-11-16T03:15:00Z",
            "schema": "chart (club pages, verbatim) | out/doubtful/questionable (official report) | "
                      "announced_replacements (dated official news only) | actually_played (game-day source only)",
            "rule": "replacements are names announced by a dated official source, never inferred; "
                    "actually_played stays blank without a game-day source; not-listed never means available",
            "coverage": "Week 10, 32 teams; chart layer 5/32 clubs (F-D1); actually_played 0/32 (DR-31)",
            "official_recount_2026_11_16": {
                "rows": 347, "clubs": 28, "games": 14, "structure_errors": 0,
                "designations": {"Out": 70, "Doubtful": 11, "Questionable": 90},
                "source": "fl2-dashboard/data/official/injuries-w10-team-summary.json (session 8326a20d capture)",
            },
        },
        "snapshot_ledger": [
            {"capture_id": "w10-report-2026-11-14", "captured_at_utc": "2026-11-14T03:30:00Z",
             "what": "nfl.com Week 10 injury report transcription (345 rows, 28 teams)",
             "retained": True, "source": "https://www.nfl.com/injuries/"},
            {"capture_id": "w10-report-2026-11-16", "captured_at_utc": "2026-11-16T01:00:00Z",
             "what": "official recount (347 rows; team counts public, rows kept in git-ignored private/)",
             "retained": True, "source": "https://www.nfl.com/injuries/"},
        ],
        "snapshot_gap": "Two dated captures exist now (the brief's 'one capture' finding predates the 2026-11-16 "
                        "recount). The designations series needs >= 5 captures per club-week (Wed-kickoff daily) "
                        "before deltas can be replayed; blocked on gate F-T1 (NFL terms section 1.3).",
        "depth_conflicts_stale_rows": depth.get("injury_conflicts", []),
        "reserve_registry": [e for e in news if "injured reserve" in (e["headline"] or "").lower()],
        "roster_events": news,
        "teams": per_team,
    }
    json.dump(payload, open(os.path.join(ROOT, "data", "availability_graph.json"), "w"), indent=1)
    n_chart = sum(1 for r in per_team if r["chart"])
    n_events = sum(len(r["announced_replacements"]) for r in per_team)
    print(f"availability graph OK: {len(per_team)} teams, chart layer {n_chart}/32, "
          f"{len(news)} dated news rows, {n_events} team-attached events")
    return 0


if __name__ == "__main__":
    sys.exit(main())
