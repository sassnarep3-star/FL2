#!/usr/bin/env python3
"""
tools/official_injury_capture.py

Reads the pipe-delimited transcription of the OFFICIAL NFL.com 2026 Week 10 injury
report (private/official/nfl-injury-report-w10-2026-capture.psv), validates it, and:

  * writes the full row-level capture to private/ (git-ignored, see Flagged F-T1);
  * writes a PUBLIC team-level summary to fl2-dashboard/data/official/ containing
    counts only: no player names, no row-level designations;
  * diffs the capture against the 2026-11-14 stored file and reports, per club,
    how many players disagree. The diff is a finding, not an automatic repair.

Exit status is non-zero only if the structure check fails.
"""
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PSV = os.path.join(ROOT, "private/official/nfl-injury-report-w10-2026-capture.psv")
PRIVATE_OUT = os.path.join(ROOT, "private/official/injuries-w10-2026-official-capture.json")
PUBLIC_OUT = os.path.join(ROOT, "fl2-dashboard/data/official/injuries-w10-team-summary.json")
STORED = os.path.join(ROOT, "fl2-dashboard/data/verified/injuries-week10.json")
SOURCE = "https://www.nfl.com/injuries/"
CAPTURED = "2026-11-16"

PRACTICE_OK = {
    "Full Participation in Practice",
    "Limited Participation in Practice",
    "Did Not Participate In Practice",
    "",
}
GAME_OK = {"", "Out", "Doubtful", "Questionable"}


def parse():
    games, teams, rows, errors = {}, {}, [], []
    cur_team = None
    with open(PSV, encoding="utf-8") as fh:
        for n, raw in enumerate(fh, 1):
            line = raw.rstrip("\n")
            if not line or line.startswith("#") and not (line.startswith("#GAME|") or line.startswith("#TEAM|")):
                continue
            if line.startswith("#GAME|"):
                _, gid, kick, net, a, b = line.split("|")
                games[gid] = {"id": gid, "kickoff_et": kick, "network": net, "teams": [a, b]}
                continue
            if line.startswith("#TEAM|"):
                _, abbr, name, record, gid = line.split("|")
                if abbr in teams:
                    errors.append(f"line {n}: team {abbr} appears twice")
                teams[abbr] = {"abbr": abbr, "name": name, "record": record, "game_id": gid, "rows": []}
                cur_team = abbr
                continue
            if "|" not in line:
                continue  # free-text note inside the file
            parts = line.split("|")
            if len(parts) != 6:
                errors.append(f"line {n}: expected 6 fields, got {len(parts)}")
                continue
            abbr, player, pos, inj, prac, gs = parts
            if abbr != cur_team:
                errors.append(f"line {n}: row for {abbr} sits inside the {cur_team} block")
            if prac not in PRACTICE_OK:
                errors.append(f"line {n}: unknown practice status {prac!r}")
            if gs not in GAME_OK:
                errors.append(f"line {n}: unknown game status {gs!r}")
            if not player.strip():
                errors.append(f"line {n}: empty player name")
            row = {"team": abbr, "player": player, "pos": pos, "injuries": inj,
                   "practice_status": prac, "game_status": gs, "source": SOURCE}
            teams[abbr]["rows"].append(row)
            rows.append(row)
    return games, teams, rows, errors


def structure_checks(games, teams, errors):
    if len(games) != 14:
        errors.append(f"expected 14 games, found {len(games)}")
    if len(teams) != 28:
        errors.append(f"expected 28 teams, found {len(teams)}")
    seen = collections.Counter(t for g in games.values() for t in g["teams"])
    for t, c in seen.items():
        if c != 1:
            errors.append(f"team {t} appears in {c} games")
    for t in teams:
        if t not in seen:
            errors.append(f"team {t} is not in any game")
    for g in games.values():
        for t in g["teams"]:
            if t not in teams:
                errors.append(f"game {g['id']} names unknown team {t}")
    for t in teams.values():
        if not t["rows"]:
            errors.append(f"team {t['abbr']} has zero rows (the official report lists every playing club)")
    return errors


def load_stored():
    with open(STORED, encoding="utf-8") as fh:
        d = json.load(fh)
    return {t["team"]: t["rows"] for t in d["teams"]}


def diff_by_team(teams):
    """Return {club name: {'stored_rows', 'official_rows', 'players_differing', 'detail'}}.
    detail is kept in the PRIVATE file only."""
    stored = load_stored()
    result = {}
    names = {t["name"]: a for a, t in teams.items()}
    for name in sorted(set(names) | set(stored)):
        off_rows = teams[names[name]]["rows"] if name in names else []
        sto_rows = stored.get(name, [])
        detail = []
        off_by = {r["player"]: r for r in off_rows}
        sto_by = {r.get("player"): r for r in sto_rows}
        for p in sorted(set(off_by) - set(sto_by)):
            detail.append({"player": p, "issue": "on official report, missing from stored"})
        for p in sorted(set(sto_by) - set(off_by)):
            detail.append({"player": p, "issue": "in stored file, not on official report"})
        for p in sorted(set(off_by) & set(sto_by)):
            o, s = off_by[p], sto_by[p]
            diffs = []
            if (s.get("inj") or "") != o["injuries"]:
                diffs.append(f"injury: official={o['injuries']!r} stored={s.get('inj')!r}")
            if (s.get("gs") or "") != o["game_status"]:
                diffs.append(f"game status: official={o['game_status']!r} stored={s.get('gs')!r}")
            if (s.get("prac") or "") != o["practice_status"]:
                diffs.append(f"practice: official={o['practice_status']!r} stored={s.get('prac')!r}")
            for d in diffs:
                detail.append({"player": p, "issue": d})
        players = {d["player"] for d in detail}
        result[name] = {"stored_rows": len(sto_rows), "official_rows": len(off_rows),
                        "players_differing": len(players), "detail": detail}
    return result


def main():
    games, teams, rows, errors = parse()
    errors = structure_checks(games, teams, errors)
    diffs = diff_by_team(teams)


    game_of = {}
    for g in games.values():
        a, b = g["teams"]
        game_of[a] = (b, g, "listed first")
        game_of[b] = (a, g, "listed second")

    public_teams = []
    for abbr, t in sorted(teams.items()):
        opp, g, _ = game_of[abbr]
        rs = t["rows"]
        d = diffs.get(t["name"], {"stored_rows": None, "official_rows": len(rs), "players_differing": None})
        public_teams.append({
            "abbr": abbr,
            "club": t["name"],
            "record_on_report": t["record"],
            "opponent_abbr": opp,
            "kickoff_et": g["kickoff_et"],
            "network": g["network"],
            "official_report_url": SOURCE,
            "players_listed": len(rs),
            "with_injury_designation": sum(1 for r in rs if r["injuries"]),
            "out": sum(1 for r in rs if r["game_status"] == "Out"),
            "doubtful": sum(1 for r in rs if r["game_status"] == "Doubtful"),
            "questionable": sum(1 for r in rs if r["game_status"] == "Questionable"),
            "did_not_participate": sum(1 for r in rs if r["practice_status"] == "Did Not Participate In Practice"),
            "stored_capture_rows_2026_11_14": d["stored_rows"],
            "players_differing_from_stored": d["players_differing"],
        })

    summary = {
        "rows": len(rows),
        "clubs": len(teams),
        "games": len(games),
        "rows_with_injury_designation": sum(1 for r in rows if r["injuries"]),
        "game_status_out": sum(1 for r in rows if r["game_status"] == "Out"),
        "game_status_doubtful": sum(1 for r in rows if r["game_status"] == "Doubtful"),
        "game_status_questionable": sum(1 for r in rows if r["game_status"] == "Questionable"),
        "clubs_with_zero_injury_designations": [t["name"] for t in teams.values()
                                                if not any(r["injuries"] for r in t["rows"])],
        "clubs_where_stored_row_count_differs": [
            {"club": k, "stored": v["stored_rows"], "official": v["official_rows"]}
            for k, v in diffs.items() if v["stored_rows"] != v["official_rows"]],
        "clubs_with_any_stored_difference": sum(1 for v in diffs.values() if v["players_differing"]),
        "players_differing_from_stored": sum(v["players_differing"] for v in diffs.values()),
    }

    private = {
        "title": "PRIVATE row-level capture - NFL.com 2026 Week 10 injury report",
        "source": SOURCE,
        "captured": CAPTURED,
        "note": "Not for publication. See Flagged F-T1 (nfl.com terms s.1.3).",
        "summary": summary,
        "games": list(games.values()),
        "rows": rows,
        "diff_vs_stored_2026_11_14": diffs,
        "structure_errors": errors,
    }
    os.makedirs(os.path.dirname(PRIVATE_OUT), exist_ok=True)
    with open(PRIVATE_OUT, "w", encoding="utf-8") as fh:
        json.dump(private, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    public = {
        "title": "Official NFL 2026 Week 10 injury report - team-level summary",
        "source": SOURCE,
        "captured": CAPTURED,
        "method": ("Counts are computed from a row-by-row transcription of the official report "
                   "(fetch_page, all 8 chunks, 2026-11-16 UTC). No player names are published here. "
                   "The fetch tool returns page text, not HTML, so no byte hash exists for this capture."),
        "stored_comparison": "Stored file = fl2-dashboard/data/verified/injuries-week10.json (2026-11-14 capture).",
        "summary": {k: v for k, v in summary.items() if k != "clubs_where_stored_row_count_differs"} | {
            "clubs_where_stored_row_count_differs": len(summary["clubs_where_stored_row_count_differs"])},
        "clubs": public_teams,
        "structure_errors": errors,
    }
    with open(PUBLIC_OUT, "w", encoding="utf-8") as fh:
        json.dump(public, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(json.dumps({"summary": summary, "structure_errors": errors}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
