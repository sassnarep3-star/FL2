#!/usr/bin/env python3
"""Requirement 5: locate starters who are Out/Doubtful and identify the backup
who is next on the club's published depth chart.

Rules that keep this honest
---------------------------
* Depth charts are club-published and captioned "unofficial". Every row says so.
* Only clubs whose chart was actually fetched appear. The other 27 say
  "not acquired". Nothing is guessed.
* The "replacement" column is literally the next name printed to the right of
  the injured player on the club chart. It is NOT a prediction of who will play.
* No numeric "how much worse is the backup" value is produced. That number
  cannot be derived from any official source, so publishing one would be a
  hallucination.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DERIVED = os.path.join(DATA, "derived")

OUT_STATUSES = {"Out", "Doubtful"}


def norm(name):
    """Club charts print jersey numbers ('8 Josh Jacobs'); injury reports do not."""
    parts = (name or "").split()
    while parts and parts[0].isdigit():
        parts = parts[1:]
    return " ".join(parts).strip()


def load(name):
    with open(os.path.join(DATA, name)) as fh:
        return json.load(fh)


def main():
    inj = load("injuries.json")
    dc = load("depth_charts.json")

    # ---- flatten the official injury report: team -> player -> row
    status_by_team = {}
    for g in inj["games"]:
        for t in g["teams"]:
            m = status_by_team.setdefault(t["team"], {})
            for row in t["players"]:
                name, pos, injury, practice, status, url = row
                if name:
                    m[norm(name)] = {
                        "pos": pos, "injury": injury,
                        "practice": practice, "status": status, "url": url,
                        "game": "%s@%s" % (g["away"], g["home"]),
                    }

    rows = []
    for club in dc["clubs"]:
        if club["status"] != "verified":
            continue
        team = club["team"]
        injuries = status_by_team.get(team, {})
        for unit, table in club["units"].items():
            for line in table:
                pos = line[0]
                strings = line[1:5]
                for depth_i, player in enumerate(strings):
                    if not player:
                        continue
                    info = injuries.get(norm(player))
                    if not info or info["status"] not in OUT_STATUSES:
                        continue
                    # next non-empty name to the right = the club's listed backup
                    replacement, repl_depth = "", ""
                    for j in range(depth_i + 1, 4):
                        if strings[j]:
                            replacement = strings[j]
                            repl_depth = ["1st", "2nd", "3rd", "4th"][j]
                            break
                    rows.append({
                        "team": team,
                        "injured_player_display": player,
                        "club": club["club"],
                        "unit": unit,
                        "position": pos,
                        "injured_player": player,
                        "injured_depth": ["1st", "2nd", "3rd", "4th"][depth_i],
                        "game_status": info["status"],
                        "injury": info["injury"],
                        "week10_game": info["game"],
                        "listed_backup": replacement or "",
                        "backup_depth": repl_depth,
                        "backup_note": ("No deeper player published at this position"
                                        if not replacement else
                                        "Next name printed on the club chart; not a prediction of who plays"),
                        "depth_chart_source": club["source"],
                        "injury_source": "https://www.nfl.com/injuries/league/2026/reg10",
                        "player_source": info["url"],
                        "official_status": False,
                        "caveat": "Depth chart is club-published and UNofficial (see source). Backup name is the club's printed ordering only.",
                    })

    # ---- Out/Doubtful players who are not on their own club's chart at all
    missing = []
    for club in dc["clubs"]:
        if club["status"] != "verified":
            continue
        team = club["team"]
        names = set()
        for table in club["units"].values():
            for line in table:
                for nm in line[1:5]:
                    if nm:
                        names.add(norm(nm))
        for pname, info in status_by_team.get(team, {}).items():
            if info["status"] in OUT_STATUSES and pname not in names:
                missing.append({
                    "team": team, "player": pname, "pos_on_report": info["pos"],
                    "game_status": info["status"], "injury": info["injury"],
                    "week10_game": info["game"],
                    "issue": "Carries an Out/Doubtful status on the official NFL Week 10 injury report but appears nowhere on this club's published depth chart.",
                    "injury_source": "https://www.nfl.com/injuries/league/2026/reg10",
                    "player_source": info["url"],
                    "chart_source": club["source"],
                })
    missing.sort(key=lambda r: (r["team"], r["player"]))

    rows.sort(key=lambda r: (r["team"], r["unit"], r["position"], r["injured_depth"]))

    starters_out = [r for r in rows if r["injured_depth"] == "1st"]

    rows = [dict(r, injured_player=r.get("injured_player_display", r["injured_player"])) for r in rows]

    out = {
        "meta": {
            "season": 2026,
            "week": 10,
            "generated_utc": "2026-11-14",
            "method": "Intersect the official NFL Week 10 injury report (status Out or Doubtful) with every club depth chart that was actually fetched. The backup is the next non-empty name to the right of the injured player on that club's published chart.",
            "HARD_LIMIT": "The NFL publishes no official depth chart, so no row here can be called official. Club charts lag the injury report; a player ruled Out may still be printed as the starter (see depth_charts.json -> injury_conflicts).",
            "NO_QUANTIFICATION": "No 'points per game lost' or similar number is published. That quantity cannot be derived from any official source and estimating it would be a fabrication. This table identifies WHO is affected and WHO is next, and stops there.",
            "coverage": "5 of 32 clubs (NE, DET, GB, KC, SF). The other 27 clubs' charts were not acquired this session.",
            "sources": [
                "https://www.nfl.com/injuries/league/2026/reg10",
                "https://www.patriots.com/team/depth-chart",
                "https://www.detroitlions.com/team/depth-chart",
                "https://www.packers.com/team/depth-chart",
                "https://www.chiefs.com/team/depth-chart",
                "https://www.49ers.com/team/depth-chart",
            ],
        },
        "n_rows": len(rows),
        "n_starters_out": len(starters_out),
        "starters_out": starters_out,
        "n_on_report_not_on_chart": len(missing),
        "on_report_not_on_chart": missing,
        "all_affected": rows,
        "clubs_not_acquired": [
            {"team": r["team"], "club": r["club"], "status": r["status"]}
            for r in dc["registry"] if r.get("status") != "verified"
        ] if isinstance(dc.get("registry"), list) else dc.get("registry"),
    }

    os.makedirs(DERIVED, exist_ok=True)
    with open(os.path.join(DERIVED, "backup_impact.json"), "w") as fh:
        json.dump(out, fh, indent=2)

    print("rows:", len(rows), " 1st-stringers out/doubtful:", len(starters_out),
          " on report but absent from chart:", len(missing))
    for r in missing:
        print("  MISSING %s %s %s (%s)" % (r["team"], r["pos_on_report"], r["player"], r["game_status"]))
    for r in starters_out[:20]:
        print("  %s %s %s (%s, %s) -> %s" % (r["team"], r["position"], r["injured_player"],
                                             r["game_status"], r["injury"], r["listed_backup"] or "none published"))


if __name__ == "__main__":
    main()
