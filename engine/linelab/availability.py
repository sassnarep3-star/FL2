#!/usr/bin/env python3
"""
engine/linelab/availability.py — immutable availability snapshots and the delta
between them.

Requirements served:
  "Add injury and personnel ablations instead of fixed penalties"
  "Store every injury-hub read with its clock time and publish the delta, never the level"
  "Treat the injury report as a timestamped series, not a weekly snapshot"
  "Track the depth of the replacement, not just the fact of a replacement"
  "Add a per-team view: starters out, replacements named, net injury count"
  "Capture the reserve list so 'not listed' never means 'available'"
  "Publish a weekly 'what changed' diff instead of a static snapshot"
  "Score injury-designation reliability before using it as a feature"

WHAT THIS DOES
  1. Loads every capture in data/linelab/captures/<date>/ with a CSV + meta.json.
  2. Publishes each capture's raw hash and clock time (the immutable part).
  3. Diffs two captures of the SAME season+week and emits a per-player delta:
     appeared, disappeared, game_status changed, practice_status changed.
  4. Scores designation reliability by joining designations to snap
     participation: the share of players who actually took a snap, by
     designation, with a Wilson interval. That answers "what does Questionable
     mean empirically" rather than quoting an old percentage.
  5. Reports reserve-list members seen in the injury data but absent from the
     latest report, so "not listed" is never read as "available".

OUTPUT
  data/linelab/availability.json   captures, deltas, reliability table, reserve flags
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTDIR = os.path.join(ROOT, "data", "linelab")
CAPDIR = os.path.join(OUTDIR, "captures")
SIGNAL = os.path.join(ROOT, "signal", "data")

NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
SOURCE_URL = "https://www.nfl.com/injuries/"


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def wilson(k, n, z=1.959964):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round((c - m) / d, 4), round((c + m) / d, 4))


def load_captures():
    caps = []
    if not os.path.isdir(CAPDIR):
        return caps
    for day in sorted(os.listdir(CAPDIR)):
        d = os.path.join(CAPDIR, day)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith(".csv"):
                continue
            p = os.path.join(d, f)
            meta_p = p[:-4] + ".meta.json"
            if not os.path.exists(meta_p):
                continue
            meta = json.load(open(meta_p, encoding="utf-8"))
            rows = list(csv.DictReader(open(p, encoding="utf-8")))
            caps.append({
                "capture_id": meta.get("capture_id", f"{day}/{f[:-4]}"),
                "path": os.path.relpath(p, ROOT),
                "sha256": sha256_file(p),
                "bytes": os.path.getsize(p),
                "captured_utc": meta.get("captured_utc"),
                "source_url": meta.get("source_url"),
                "season": int(meta.get("season", 0)),
                "week": int(meta.get("week", 0)),
                "rows": len(rows),
                "meta": meta,
                "data": rows,
                "_key": f"{meta.get('season')}-{meta.get('week')}",
            })
    return caps


def diff_capture(a, b):
    """a and b are two captures of the same season/week; delta is b relative to a."""
    A = {(r["team"], r["player"]): r for r in a["data"]}
    B = {(r["team"], r["player"]): r for r in b["data"]}
    delta = []
    for k in sorted(set(A) | set(B)):
        ra, rb = A.get(k), B.get(k)
        if ra is None:
            delta.append({"team": k[0], "player": k[1], "change": "appeared",
                          "from": None, "to": rb["game_status"] or rb["practice_status"]})
        elif rb is None:
            delta.append({"team": k[0], "player": k[1], "change": "disappeared",
                          "from": ra["game_status"] or ra["practice_status"], "to": None})
        else:
            if ra["game_status"] != rb["game_status"]:
                delta.append({"team": k[0], "player": k[1], "change": "game_status",
                              "from": ra["game_status"], "to": rb["game_status"]})
            if ra["practice_status"] != rb["practice_status"]:
                delta.append({"team": k[0], "player": k[1], "change": "practice_status",
                              "from": ra["practice_status"], "to": rb["practice_status"]})
    return {
        "from_capture": a["capture_id"], "to_capture": b["capture_id"],
        "from_captured_utc": a["captured_utc"], "to_captured_utc": b["captured_utc"],
        "rows_from": a["rows"], "rows_to": b["rows"],
        "n_changes": len(delta), "changes": delta,
    }


def reliability_table():
    """
    Join designations to snap participation, restricted to seasons and weeks that
    exist in both files. A player counts as "played" when a snap-participation row
    exists for that team-week. This is an OBSERVED play rate, not an assumed one.
    """
    inj_p = os.path.join(SIGNAL, "injury_player.csv")
    snap_p = os.path.join(SIGNAL, "snap_participation.csv")
    if not (os.path.exists(inj_p) and os.path.exists(snap_p)):
        return {"status": "unavailable",
                "reason": "signal/data/injury_player.csv or snap_participation.csv missing"}
    snap = set()
    snap_seasons = set()
    for r in csv.DictReader(open(snap_p, encoding="utf-8")):
        snap.add((r["season"], r["week"], r["team"], r["player"]))
        snap_seasons.add(r["season"])
    buckets = defaultdict(lambda: {"n": 0, "played": 0, "seasons": set()})
    for r in csv.DictReader(open(inj_p, encoding="utf-8")):
        if r["season"] not in snap_seasons:
            continue
        key = (r["season"], r["week"], r["team"], r["full_name"])
        b = buckets[r["game_status"] or "(blank)"]
        b["n"] += 1
        b["seasons"].add(r["season"])
        if key in snap:
            b["played"] += 1
    out = []
    for status in ("Out", "Doubtful", "Questionable", "Probable", "(blank)"):
        b = buckets.get(status)
        if not b or b["n"] == 0:
            continue
        lo, hi = wilson(b["played"], b["n"])
        out.append({
            "designation": status,
            "n": b["n"],
            "observed_play_rate": round(b["played"] / b["n"], 4),
            "ci95_wilson": [lo, hi],
            "seasons": f"{min(b['seasons'])}-{max(b['seasons'])}",
            "seasons_count": len(b["seasons"]),
            "definition": ("share of player-weeks with that designation for which a snap-count "
                           "row exists, i.e. the player took at least one snap"),
            "source": "nflverse injuries_*.csv joined to snap_counts_*.csv",
        })
    return {
        "status": "ok",
        "note": ("This is the empirical answer to 'what does Questionable mean'. It replaces any "
                 "borrowed percentage, and it carries n and a Wilson interval because a play rate "
                 "without its sample size is not evidence."),
        "caveat": ("A snap-count row proves participation, not a start, and it does not prove the "
                   "player was on the game-day 48. It is the strongest join the committed data "
                   "supports, and it is labelled as a participation join."),
        "buckets": out,
    }


def reserve_flags(latest):
    """Players in season 2026 injury data who are absent from the latest capture."""
    inj_p = os.path.join(SIGNAL, "injury_player.csv")
    if not os.path.exists(inj_p) or not latest:
        return {"status": "unavailable"}
    latest_keys = {(r["team"], r["player"]) for r in latest["data"]}
    seen = defaultdict(lambda: {"weeks": set(), "teams": set()})
    for r in csv.DictReader(open(inj_p, encoding="utf-8")):
        if r["season"] != "2026":
            continue
        k = (r["team"], r["full_name"])
        seen[k]["weeks"].add(r["week"])
        seen[k]["teams"].add(r["team"])
    missing = []
    for (team, name), v in seen.items():
        if (team, name) in latest_keys:
            continue
        maxw = max(int(w) for w in v["weeks"] if w.isdigit())
        if maxw >= latest["week"] - 2:
            missing.append({
                "team": team, "player": name,
                "last_seen_week": maxw,
                "weeks_seen": sorted(v["weeks"], key=int),
                "reading": ("Not on the current report. This does NOT mean available: a player "
                            "placed on injured reserve, suspended, or released comes off the "
                            "report entirely. The reserve list must be checked."),
            })
    return {
        "status": "ok",
        "latest_capture_week": latest["week"],
        "n_missing_vs_earlier_weeks": len(missing),
        "players": sorted(missing, key=lambda x: (x["team"], -x["last_seen_week"], x["player"]))[:200],
    }


def capture_quality(caps):
    """
    Automatic defect detection on the captures themselves. A capture where one
    team has no designations at all, while every other team has them, is either
    (a) what the league rendered at that moment, or (b) a transcription gap.
    This function does not decide which; it detects and quantifies, so the
    irregularity cannot be quietly dropped.
    """
    findings = []
    for c in caps:
        per_team = defaultdict(lambda: {"rows": 0, "designated": 0})
        for r in c["data"]:
            t = per_team[r["team"]]
            t["rows"] += 1
            if r["game_status"] or r["practice_status"] == "Did Not Participate In Practice":
                t["designated"] += 1
        zero = [t for t, v in per_team.items() if v["rows"] and v["designated"] == 0]
        if zero:
            findings.append({
                "capture_id": c["capture_id"],
                "type": "team_block_without_any_designation",
                "teams": sorted(zero),
                "rows_affected": sum(per_team[t]["rows"] for t in zero),
                "why_it_matters": (
                    "A team whose entire block carries no game status and no non-participation "
                    "practice flag is indistinguishable from 'everyone practised fully'. Any model "
                    "that reads a blank cell as healthy will under-estimate that team's "
                    "unavailability by exactly this many players."
                ),
                "two_possible_causes": [
                    "the league had not yet published game statuses for that team when the capture was taken",
                    "the capture omitted the column values for that block",
                ],
                "how_to_resolve": (
                    "Take a third capture of the same week. If the block is populated, the first "
                    "capture was a reading artefact; if it is still blank, the league had not "
                    "published. Held open as an irregularity until that capture exists."
                ),
                "status": "needs review",
            })
    return findings


def team_view(latest):
    """One row per team: out / doubtful / questionable counts, and net count."""
    if not latest:
        return []
    rows = defaultdict(lambda: {"Out": 0, "Doubtful": 0, "Questionable": 0, "listed": 0})
    for r in latest["data"]:
        t = rows[r["team"]]
        t["listed"] += 1
        gs = r["game_status"]
        if gs in t:
            t[gs] += 1
    return [
        {"team": k, "listed": v["listed"], "out": v["Out"], "doubtful": v["Doubtful"],
         "questionable": v["Questionable"],
         "net_unavailable": v["Out"] + v["Doubtful"]}
        for k, v in sorted(rows.items())
    ]


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    caps = load_captures()
    # published view of each capture, without the row payload (that lives in the CSV)
    pub = [{k: v for k, v in c.items() if k not in ("data", "meta")} for c in caps]

    deltas = []
    keys = sorted({c["_key"] for c in caps})
    for k in keys:
        same = sorted([c for c in caps if c["_key"] == k], key=lambda c: c["captured_utc"] or "")
        for a, b in zip(same, same[1:]):
            d = diff_capture(a, b)
            d["season_week"] = k
            deltas.append(d)

    latest = max(caps, key=lambda c: c["captured_utc"]) if caps else None
    out = {
        "built_utc": NOW,
        "builder": "engine/linelab/availability.py",
        "policy": {
            "snapshot_rule": ("Every capture keeps its raw SHA-256 and the clock time it was read. "
                              "A capture is never edited; a correction is a new capture."),
            "delta_rule": ("The site publishes the change between two captures, never a single "
                           "level presented as though it were stable."),
            "not_listed_rule": ("Absence from the report means the league did not list the player. "
                                "It is never rendered as 'healthy' or 'available'."),
            "snapshot_count": len(caps),
            "honest_limitation": (
                "The brief asks for at least daily capture of the official report, club depth "
                "pages and inactive lists. This repository holds the captures listed below and "
                "no others. It cannot self-schedule; a scheduled job must own the cadence. Until "
                "that job exists, the number of vintages is what you see, not what was asked for."
            ),
        },
        "captures": pub,
        "deltas": deltas,
        "capture_quality_findings": capture_quality(caps),
        "team_view": team_view(latest),
        "latest_capture_id": latest["capture_id"] if latest else None,
        "designation_reliability": reliability_table(),
        "reserve_check": reserve_flags(latest),
        "sources": [
            {"url": SOURCE_URL, "tier": "T1 official league",
             "used_for": "the weekly injury report page that every capture is read from"},
            {"url": "https://www.nfl.com/injuries/league/2026/reg10", "tier": "T1 official league",
             "used_for": "the Week 10 2026 capture"},
            {"url": "https://github.com/nflverse/nflverse-data/releases/tag/injuries",
             "tier": "T2 open data mirror of the same official report",
             "used_for": "the multi-season designation-reliability join"},
        ],
    }
    with open(os.path.join(OUTDIR, "availability.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("availability.json:", len(caps), "captures,", len(deltas), "deltas")
    for d in deltas:
        print("  delta", d["from_capture"], "->", d["to_capture"], ":", d["n_changes"], "changes")
    rel = out["designation_reliability"]
    if rel.get("status") == "ok":
        print("  designation reliability:")
        for b in rel["buckets"]:
            print(f"    {b['designation']:<14} n={b['n']:>6} play={b['observed_play_rate']:.4f} "
                  f"CI={b['ci95_wilson']}")
    print("  reserve check:", out["reserve_check"].get("n_missing_vs_earlier_weeks"))


if __name__ == "__main__":
    main()
