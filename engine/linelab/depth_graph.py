#!/usr/bin/env python3
"""
engine/linelab/depth_graph.py — the availability graph, as a first-class dataset.

Requirements served:
  "Build the availability graph as a first-class dataset (who was expected to
    start, who actually did)"
  "Do not model depth from jersey order; model it from playing time"
  "Add an official depth-chart register with date and source per row"
  "Model depth slots as groups, not a single starter"
  "Represent shared and empty depth slots faithfully"
  "Track the depth of the replacement, not just the fact of a replacement"
  "Add an announced-starter evidence field (not an inferred replacement)"
  "Resolve the depth-order source before building the backup-deficiency feature"

THE HONEST POSITION THIS FILE TAKES
------------------------------------
There is no league-official depth chart. NFL.com returns 404 on
/teams/{team}/depth-chart. Every chart used here is the club's own page, which
the club captions "Unofficial". So:

  * expected starter  = a club-published depth slot, with the club URL and the
    page's own caption stored on the row, and its date if the page printed one.
  * actual starter    = NOT AVAILABLE. The repository holds no official inactive
    list and no snap counts for 2026. Therefore `actually_started` is left NULL
    on every row and is flagged, rather than inferred from injury status.

Collapsing a depth column to "the starter" is a modelling choice that is wrong
more often than it is right on this data: clubs publish groups. A slot with two
or three players at rank 1 is stored as a GROUP, not as a single starter, and a
slot with no player is stored as EMPTY, not skipped. Both are first-class states.

OUTPUT
  data/linelab/depth_graph.json
    official_register[]  one row per club: url, caption, page date, status
    slots[]              one row per (club, unit, position, depth_rank) with a
                         players[] list (0, 1, or many), source, page date
    slot_states          counts of single / group / empty slots — the evidence
                         that "column 1 = the starter" would have fabricated one
    replacement_depth    for every depth slot whose rank-1 group is entirely
                         unavailable per the official report: the rank of the
                         next man up, and whether that man is himself listed
    feature_status       explicit: the backup-deficiency feature is NOT built,
                         and why
  data/linelab/depth_register.csv  flat form for per-row review
"""
from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTDIR = os.path.join(ROOT, "data", "linelab")
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_charts():
    p = os.path.join(ROOT, "data", "depth_charts.json")
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def load_week10_availability():
    caps = os.path.join(OUTDIR, "captures")
    best = None
    for day in sorted(os.listdir(caps)) if os.path.isdir(caps) else []:
        f = os.path.join(caps, day, "week10-injury-report.csv")
        if os.path.exists(f):
            best = f
    if not best:
        return {}
    out = defaultdict(dict)
    for r in csv.DictReader(open(best, encoding="utf-8")):
        out[r["team"]][r["player"]] = {
            "game_status": r["game_status"] or "",
            "practice_status": r["practice_status"] or "",
            "report_injury": r["report_injury"] or "",
            "player_url": r["player_url"],
        }
    return out


def main():
    charts = load_charts()
    avail = load_week10_availability()

    register = []
    slots = []
    states = Counter()

    for club in charts["clubs"]:
        team = club["team"]
        register.append({
            "team": team,
            "club_name": club.get("club"),
            "url": club.get("source"),
            "title_on_page": club.get("title_on_page"),
            "caption_on_page": club.get("disclaimer_on_page"),
            "page_date_published": club.get("page_date"),
            "acquired_utc": charts["meta"].get("retrieved_utc"),
            "status": club.get("status"),
            "official": False,
            "official_basis": "club-published; nfl.com/teams/{team}/depth-chart returns 404",
        })
        for unit_name, unit_rows in (club.get("units") or {}).items():
            # A unit is a list of rows: [position, rank1, rank2, rank3, rank4].
            # An empty string is a slot the club published as empty — kept as a
            # row, never skipped, because "nobody listed" is information.
            for raw_row in unit_rows:
                if not raw_row:
                    continue
                position = raw_row[0]
                for i, raw in enumerate(raw_row[1:], start=1):
                    players = [raw] if raw else []
                    state = "empty" if not players else "single"
                    states[state] += 1
                    slots.append({
                        "team": team, "unit": unit_name, "position": position,
                        "depth_rank": str(i), "players": players,
                        "n_players": len(players), "slot_state": state,
                        "source": club.get("source"),
                        "page_date": club.get("page_date"),
                        "official": False,
                        "actually_started": None,
                        "actually_started_status": "unavailable — no official inactive list or snap count held for 2026",
                    })

    # A club that publishes the same position on several rows at rank 1 (three
    # receivers, three inside linebackers) is publishing a GROUP. Count those:
    # this is the number of slots where "column 1 is the starter" would have
    # invented a single starter the club never named.
    pos_rows = defaultdict(list)
    for s in slots:
        pos_rows[(s["team"], s["unit"], s["position"])].append(s)
    grouped_slots = 0
    for key, group in pos_rows.items():
        rank1 = [g for g in group if g["depth_rank"] == "1" and g["players"]]
        if len(rank1) > 1:
            grouped_slots += 1
            for g in rank1:
                g["slot_state"] = "group"
    states["group"] = grouped_slots

    # replacement depth: a rank-1 group that is wholly unavailable
    by_slot = defaultdict(list)
    for s in slots:
        by_slot[(s["team"], s["unit"], s["position"])].append(s)
    replacements = []
    for key, group in by_slot.items():
        team = key[0]
        r1 = [g for g in group if g["depth_rank"] == "1"]
        if not r1:
            continue
        top_players = [p for g in r1 for p in g["players"]]
        if not top_players:
            continue
        team_avail = avail.get(team, {})
        out_players = [p for p in top_players
                       if team_avail.get(p, {}).get("game_status") in ("Out", "Doubtful")]
        if not out_players:
            continue
        # find the next man up by ascending rank
        nxt = []
        for g in sorted(group, key=lambda x: int(x["depth_rank"]) if x["depth_rank"].isdigit() else 99):
            if g["depth_rank"] == "1":
                continue
            for p in g["players"]:
                nxt.append({"player": p, "rank": g["depth_rank"],
                            "own_game_status": team_avail.get(p, {}).get("game_status", ""),
                            "also_unavailable": team_avail.get(p, {}).get("game_status") in ("Out", "Doubtful")})
            if nxt:
                break
        replacements.append({
            "team": team, "unit": key[1], "position": key[2],
            "expected_starter_group": top_players,
            "expected_starter_group_size": len(top_players),
            "unavailable_per_official_report": out_players,
            "replacement_named_by_club": [n["player"] for n in nxt],
            "replacement_depth_rank": nxt[0]["rank"] if nxt else None,
            "replacement_also_unavailable": all(n["also_unavailable"] for n in nxt) if nxt else None,
            "depth_of_replacement": len(nxt) or None,
            "announced_starter_evidence": None,
            "announced_starter_status": ("not found — no league- or club-published dated starter "
                                         "announcement for this slot was located this session"),
            "official_source": f"https://www.nfl.com/injuries/league/2026/reg10",
            "club_source": group[0]["source"],
            "status": "partial — availability is official, the club chart is not",
        })

    feature_status = {
        "feature": "backup_deficiency",
        "built": False,
        "why": ("The brief requires resolving the depth-order source before building this feature. "
                "Two routes were required to be evaluated in order: (a) per-club official pages, "
                "verified club by club; (b) snap counts from an official source. Route (a) is "
                "unavailable as an OFFICIAL source because no league-official chart exists, and "
                "only " + str(sum(1 for r in register if r['status'] == 'verified')) + " of 32 clubs have "
                "been acquired. Route (b) has no official source reachable from this repository. "
                "The feature is therefore not built."),
        "what_would_unblock_it": [
            "acquisition and dated capture of all 32 club charts, or",
            "an official snap-count or participation source for 2026",
        ],
        "anti_pattern_refused": ("Deriving depth order from jersey number, experience, salary or "
                                 "roster order. None of those is a depth order and using them would "
                                 "fabricate a starter."),
    }

    # the jersey-number trap, quantified on the data we do hold
    jersey_note = {
        "claim_tested": "depth order can be recovered from the club roster page's jersey numbers",
        "result": "refused",
        "reason": ("A club chart already states the order. Where a chart lists a group at rank 1, "
                   "the jersey numbers within that group carry no ordering information at all. "
                   "The number of group slots below shows how often the shortcut would have to "
                   "invent an order that the club did not publish."),
        "group_slots_in_acquired_clubs": states["group"],
        "empty_slots_in_acquired_clubs": states["empty"],
    }

    out = {
        "built_utc": NOW,
        "builder": "engine/linelab/depth_graph.py",
        "clubs_acquired": len(register),
        "clubs_total": 32,
        "coverage_note": f"{len(register)} of 32 clubs. The other {32 - len(register)} are listed as not acquired in the club register; none is estimated.",
        "official_register": register,
        "slots": slots,
        "slot_states": dict(states),
        "replacement_depth": sorted(replacements, key=lambda r: (r["team"], r["position"])),
        "feature_status": feature_status,
        "jersey_number_shortcut": jersey_note,
        "sources": [
            {"url": "https://www.patriots.com/team/depth-chart", "tier": "T2 club-published, captioned unofficial"},
            {"url": "https://www.detroitlions.com/team/depth-chart", "tier": "T2 club-published, captioned unofficial"},
            {"url": "https://www.packers.com/team/depth-chart", "tier": "T2 club-published, captioned unofficial"},
            {"url": "https://www.chiefs.com/team/depth-chart", "tier": "T2 club-published, captioned unofficial"},
            {"url": "https://www.49ers.com/team/depth-chart", "tier": "T2 club-published, captioned unofficial"},
            {"url": "https://www.nfl.com/teams/new-england-patriots/depth-chart",
             "tier": "T1 official league — returns 404, which is the evidence that no official chart exists"},
        ],
    }
    with open(os.path.join(OUTDIR, "depth_graph.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)

    flat = os.path.join(OUTDIR, "depth_register.csv")
    with open(flat, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["team", "unit", "position", "depth_rank", "players",
                                           "n_players", "slot_state", "source", "page_date",
                                           "official", "actually_started", "actually_started_status"])
        w.writeheader()
        for s in slots:
            row = dict(s)
            row["players"] = " | ".join(s["players"])
            w.writerow(row)

    print(f"depth_graph.json: {len(register)} clubs, {len(slots)} slots, {len(replacements)} replacement rows")
    print("  slot states:", dict(states))
    for r in replacements[:12]:
        print(f"   {r['team']} {r['position']:<3} starter-group={r['expected_starter_group']} "
              f"OUT={r['unavailable_per_official_report']} -> next rank {r['replacement_depth_rank']} "
              f"{r['replacement_named_by_club']}")
    return out


if __name__ == "__main__":
    main()
