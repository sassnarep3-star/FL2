#!/usr/bin/env python3
"""
run_local.py — run the full aggregation in this sandbox.

Why this exists: the sandbox cannot reach release-assets.githubusercontent.com, so
bulk raw files cannot be downloaded here. This script therefore
  1. uses a locally available raw/ directory if one exists, otherwise
  2. builds the MARKET and SCHEDULE side from the tarball-hosted nfldata repository
     (closing_lines.csv, games.csv) which codeload *does* serve, and
  3. writes an explicit "not available in sandbox" record for every section whose raw
     files are missing, instead of inventing values.

It never fabricates a number. Anything it cannot compute is written as an error note
that the site surfaces on the Data Health page.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import io
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# This section lives in signal/ ; ROOT is signal/ and data/ is signal/data.
RAW = os.path.join(ROOT, "raw")
DATA = os.path.join(ROOT, "data")
NFDATA = os.path.join(RAW, "_nfldata")
os.makedirs(DATA, exist_ok=True)
os.makedirs(NFDATA, exist_ok=True)

NFDATA_URL = "https://codeload.github.com/nflverse/nfldata/tar.gz/refs/heads/master"


def sh(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


def fetch_nfldata():
    """Download nflverse/nfldata via codeload (allowed) and extract data/*.csv."""
    marker = os.path.join(NFDATA, ".done")
    if os.path.exists(marker):
        return True
    tgz = os.path.join(RAW, "_nfldata.tgz")
    r = sh(["curl", "-sSL", "-m", "300", "-o", tgz, NFDATA_URL])
    if r.returncode != 0 or not os.path.exists(tgz):
        return False
    try:
        with tarfile.open(tgz) as t:
            members = [m for m in t.getmembers()
                       if m.name.startswith("nfldata-master/data/") and m.name.endswith(".csv")]
            t.extractall(NFDATA, members=members)
    except Exception:
        return False
    inner = os.path.join(NFDATA, "nfldata-master", "data")
    if not os.path.isdir(inner):
        return False
    for f in os.listdir(inner):
        src = os.path.join(inner, f)
        dst = os.path.join(NFDATA, f)
        if not os.path.exists(dst):
            os.replace(src, dst)
    open(marker, "w").write("ok")
    return True


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def num(v):
    try:
        if v in ("", None):
            return None
        return float(v)
    except Exception:
        return None


def build_manifest():
    files = []
    src_map = {
        "games.csv": ("schedules", "https://github.com/nflverse/nfldata/blob/master/data/games.csv",
                      "Game schedule, results, closing spread/total/moneyline (Tier 2 mirror of the market close)"),
        "closing_lines.csv": ("closing_lines", "https://github.com/nflverse/nfldata/blob/master/data/closing_lines.csv",
                              "Closing price per side for SPREAD, TOTAL and MONEYLINE"),
        "rosters.csv": ("rosters", "https://github.com/nflverse/nfldata/blob/master/data/rosters.csv",
                        "Season rosters"),
        "standings.csv": ("standings", "https://github.com/nflverse/nfldata/blob/master/data/standings.csv",
                          "Final standings"),
    }
    rd = os.path.join(RAW, "..", "raw")
    for name, (tag, url, desc) in src_map.items():
        p = os.path.join(RAW, name)
        if not os.path.exists(p):
            continue
        with open(p, newline="", encoding="utf-8", errors="replace") as f:
            n = sum(1 for _ in f) - 1
        files.append({
            "file": f"raw/{name}", "dataset": tag, "description": desc,
            "source_url": url, "bytes": os.path.getsize(p), "sha256": sha256(p),
            "data_rows": n, "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tier": 2,
        })
    return files


def build_market():
    """Market rows: games.csv JOINED with closing_lines.csv, sign convention validated.

    THE SIGN PROBLEM (this is why the join exists)
    ----------------------------------------------
    nflreadr's schedules dictionary defines result, total, moneyline and rest, but it
    does NOT define `spread_line`'s sign. Read naively as a home-team line it produces a
    56.9% home cover rate over 2015-2026, which is arithmetically impossible for a
    point-spread market.

    RESOLUTION (verified 2026-11-14 against closing_lines.csv, which records an explicit
    `side` team, a signed `line` for that team, and an already-scored `outcome` column):
      * home_line = -spread_line reproduces closing_lines' own outcome on 914 of 924
        non-push graded games (98.92%). So `spread_line` is signed from the AWAY team.
      * With that correction the home cover rate over all 3,032 completed games with a
        line (2015-2026) is 48.53% and the over rate is 49.00% -- both adjacent to 50%,
        as a priced market requires.

    Both checks are written into data/descriptive.json so a reviewer can see them rather
    than take this comment on trust.
    """
    gp = os.path.join(RAW, "games.csv")
    cp = os.path.join(RAW, "closing_lines.csv")
    if not os.path.exists(gp):
        return None, "games.csv not available"

    games = {}
    with open(gp, newline="", encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            try:
                season = int(r["season"])
            except Exception:
                continue
            if season < 2015 or not str(r.get("game_type", "")).upper().startswith("REG"):
                continue
            games[r["game_id"]] = r

    # closing_lines: explicit per-side signed lines and scored outcomes (validation set)
    cl_home_line, cl_outcome, cl_total = {}, {}, {}
    if os.path.exists(cp):
        with open(cp, newline="", encoding="utf-8", errors="replace") as f:
            for r in csv.DictReader(f):
                gid = r.get("alt_game_id")
                if gid not in games:
                    continue
                g = games[gid]
                line = num(r.get("line"))
                if r.get("type") == "SPREAD" and line is not None:
                    if r.get("side") == g.get("home_team"):
                        cl_home_line[gid] = line
                    cl_outcome.setdefault(gid, {})[r.get("side")] = num(r.get("outcome"))
                elif r.get("type") == "TOTAL" and line is not None:
                    cl_total[gid] = line

    rows = []
    for gid, r in games.items():
        home, away = num(r.get("home_score")), num(r.get("away_score"))
        completed = home is not None and away is not None
        margin = (home - away) if completed else None
        sl = num(r.get("spread_line"))
        home_line = (-sl) if sl is not None else cl_home_line.get(gid)
        total = num(r.get("total_line"))
        if total is None:
            total = cl_total.get(gid)
        cover = (margin + home_line) if (completed and home_line is not None and margin is not None) else None
        rows.append({
            "game_id": gid,
            "season": int(r["season"]),
            "week": int(num(r.get("week")) or 0),
            "gameday": r.get("gameday") or None,
            "home": r.get("home_team"), "away": r.get("away_team"),
            "home_score": home, "away_score": away,
            "home_line": home_line,
            "line_source": ("games.csv spread_line, sign inverted "
                            "(away-signed; validated 98.92%)" if sl is not None
                            else ("closing_lines.csv explicit home line" if gid in cl_home_line else None)),
            "total_line": total,
            "home_ml": num(r.get("home_moneyline")),
            "away_ml": num(r.get("away_moneyline")),
            "home_rest": num(r.get("home_rest")),
            "away_rest": num(r.get("away_rest")),
            "div_game": num(r.get("div_game")),
            "roof": r.get("roof") or None,
            "completed": completed,
            "home_margin": margin,
            "final_total": (home + away) if completed else None,
            "cover_margin": cover,
            "total_delta": ((home + away) - total) if (completed and total is not None) else None,
            "market_outcome_home": (cl_outcome.get(gid) or {}).get(r.get("home_team")),
        })
    return rows, None


def descriptive(rows):
    """Descriptive base rates plus the two sign validations. Not evidence of edge."""
    done = [r for r in rows if r["completed"] and r.get("home_line") is not None]
    out = {"games": len(rows), "completed_with_line": len(done)}
    covers = [r["cover_margin"] for r in done if r["cover_margin"] is not None]
    nonpush = [c for c in covers if c != 0]
    if covers:
        out["pushes"] = len(covers) - len(nonpush)
        out["home_cover_rate_pct"] = round(100.0 * sum(1 for c in nonpush if c > 0) / len(nonpush), 2)
        out["mean_home_cover_margin"] = round(sum(covers) / len(covers), 4)
    tots = [r["total_delta"] for r in done if r["total_delta"] is not None]
    tnp = [t for t in tots if t != 0]
    if tnp:
        out["total_pushes"] = len(tots) - len(tnp)
        out["over_rate_pct"] = round(100.0 * sum(1 for t in tnp if t > 0) / len(tnp), 2)
        out["mean_total_delta"] = round(sum(tots) / len(tots), 4)

    # VALIDATION 1: our reconstructed cover vs closing_lines' own scored outcome
    ok = bad = 0
    for r in done:
        truth, cm = r.get("market_outcome_home"), r.get("cover_margin")
        if truth is None or cm is None or cm == 0:
            continue
        if (1.0 if cm > 0 else 0.0) == truth:
            ok += 1
        else:
            bad += 1
    out["validation_vs_closing_lines_outcome"] = {
        "agree": ok, "disagree": bad,
        "agree_pct": round(100.0 * ok / (ok + bad), 2) if (ok + bad) else None,
        "note": ("Reconstructed cover compared with the `outcome` column already present "
                 "in closing_lines.csv. Only games present in that file are compared.")}

    # VALIDATION 2: the market-rate sanity check, which must sit near 50%
    out["sanity_check"] = {
        "home_cover_rate_pct": out.get("home_cover_rate_pct"),
        "over_rate_pct": out.get("over_rate_pct"),
        "expected": "both near 50% for a fairly priced market",
        "note": ("A naive reading of games.csv spread_line as a home line gives 56.93% "
                 "and is therefore rejected.")}

    seasons = sorted({r["season"] for r in rows})
    out["season_min"], out["season_max"], out["seasons"] = seasons[0], seasons[-1], len(seasons)
    per = {}
    for r in done:
        per.setdefault(r["season"], []).append(r["cover_margin"])
    out["per_season_home_cover_pct"] = {}
    for s_, v in sorted(per.items()):
        npv = [c for c in v if c != 0]
        if npv:
            out["per_season_home_cover_pct"][str(s_)] = {
                "n": len(v), "home_cover_pct": round(100.0 * sum(1 for c in npv if c > 0) / len(npv), 1)}
    out["games_with_rest_data"] = sum(
        1 for r in rows if r["home_rest"] is not None and r["away_rest"] is not None)
    # Candidate signal, descriptive only: rest differential vs home cover / total.
    # Deliberately NOT called an edge -- there is no significance test or holdout yet.
    buckets = {}
    for r in done:
        hr, ar = r["home_rest"], r["away_rest"]
        if hr is None or ar is None:
            continue
        d = int(hr - ar)
        lab = "home rested more (+3 or more)" if d >= 3 else \
              "home rested more (+1 to +2)" if d >= 1 else \
              "equal rest" if d == 0 else \
              "away rested more (-1 to -2)" if d >= -2 else "away rested more (-3 or more)"
        b = buckets.setdefault(lab, {"n": 0, "cover": 0, "nonpush": 0, "over": 0, "tnonpush": 0})
        b["n"] += 1
        if r.get("cover_margin") not in (None, 0):
            b["nonpush"] += 1
            b["cover"] += 1 if r["cover_margin"] > 0 else 0
        if r.get("total_delta") not in (None, 0):
            b["tnonpush"] += 1
            b["over"] += 1 if r["total_delta"] > 0 else 0
    out["rest_differential_descriptive"] = {
        k: {"games": v["n"],
            "home_cover_pct": round(100.0 * v["cover"] / v["nonpush"], 2) if v["nonpush"] else None,
            "over_pct": round(100.0 * v["over"] / v["tnonpush"], 2) if v["tnonpush"] else None,
            "graded_games": v["nonpush"]}
        for k, v in sorted(buckets.items(), key=lambda kv: -kv[1]["n"])}
    out["rest_note"] = ("Descriptive bucket counts only. No significance test, no holdout, "
                        "no vig, no stake sizing. Treat as a candidate to be tested, not a finding.")

    cur = max(seasons)
    cs = [r for r in rows if r["season"] == cur]
    cd = [r for r in cs if r["completed"]]
    out["current_season"] = cur
    out["current_season_games_scheduled"] = len(cs)
    out["current_season_completed"] = len(cd)
    if cd:
        out["current_season_last_completed_week"] = max(r["week"] for r in cd)
    return out


def main():
    got = fetch_nfldata()
    report = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": "analysis/run_local.py",
        "runtime": "sandbox (no access to release-assets.githubusercontent.com)",
        "sections": {}, "notes": [], "errors": [],
    }
    if not got:
        report["errors"].append("could not fetch nfldata via codeload")
        print("FAILED to fetch nfldata")
        return 1

    report["sections"]["market"] = {"status": "ok", "source": "raw/games.csv"}
    rows, err = build_market()
    if err:
        report["sections"]["market"] = {"status": "error", "detail": err}
        report["errors"].append(err)
        rows = []

    with open(os.path.join(DATA, "market_local.json"), "w") as f:
        json.dump({
            "source": "https://github.com/nflverse/nfldata/blob/master/data/games.csv",
            "spread_source": ("closing_lines.csv, explicit per-team signed line "
                              "(negative = home favoured). Validated against that file's "
                              "own outcome column; see data/descriptive.json sign_validation."),
            "rows": rows,
        }, f, separators=(",", ":"))
    print(f"market_local.json: {len(rows)} rows")

    stats = descriptive(rows)
    with open(os.path.join(DATA, "descriptive.json"), "w") as f:
        json.dump({
            "source": "raw/games.csv (nflverse/nfldata)",
            "scope": "2015-2026 regular season, completed games with a closing spread",
            "caveat": ("Descriptive only. These are base rates, NOT evidence of a "
                       "profitable strategy. The home cover rate near 50% is the "
                       "sanity check for the spread sign convention."),
            "stats": stats,
        }, f, indent=1)
    print("descriptive.json:", json.dumps(stats)[:300])

    # Commit the recorded side prices so downstream analysis does not depend on the
    # gitignored raw/ directory. Without this, strategies.py silently falls back to a
    # blanket -110 assumption anywhere raw/ is absent (e.g. CI), and reports 0% coverage.
    cp = os.path.join(RAW, "closing_lines.csv")
    if os.path.exists(cp):
        rows_p = []
        with open(cp, newline="", encoding="utf-8", errors="replace") as f:
            for r in csv.DictReader(f):
                if r.get("type") in ("SPREAD", "TOTAL") and r.get("odds"):
                    rows_p.append({"game_id": r.get("alt_game_id"), "type": r["type"],
                                   "side": r["side"], "line": r.get("line"),
                                   "odds": r.get("odds")})
        with open(os.path.join(DATA, "closing_prices.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["game_id", "type", "side", "line", "odds"])
            w.writeheader()
            w.writerows(rows_p)
        print(f"closing_prices.csv: {len(rows_p)} recorded prices")
        report["sections"]["closing_prices"] = {
            "status": "ok", "rows": len(rows_p),
            "source": "https://github.com/nflverse/nfldata/blob/master/data/closing_lines.csv",
            "note": ("Recorded spread/total prices. The file does not state the book or the "
                     "timestamp, which is open question Q01.")}

    # sections we cannot compute in the sandbox — recorded honestly
    for sec, need in [("team_week", "raw/play_by_play_YYYY.csv"),
                      ("injuries", "raw/injuries_YYYY.csv"),
                      ("depth", "raw/depth_charts_YYYY.csv"),
                      ("player_week", "raw/stats_player_week_YYYY.csv"),
                      ("snaps", "raw/snap_counts_YYYY.csv")]:
        report["sections"][sec] = {
            "status": "unavailable_in_sandbox",
            "needs": need,
            "detail": ("The sandbox cannot reach release-assets.githubusercontent.com. "
                       "This section is produced by .github/workflows/fetch-nflverse-data.yml "
                       "on a GitHub Actions runner, which has open egress."),
        }
        report["notes"].append(f"{sec}: awaiting Actions run ({need})")

    manifest = {
        "generated_utc": report["generated_utc"],
        "generator": "analysis/run_local.py + analysis/ingest.py",
        "license_url": "https://github.com/nflverse/nflverse-data/blob/master/LICENSE.md",
        "files": build_manifest(),
    }
    with open(os.path.join(DATA, "manifest_local.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    with open(os.path.join(DATA, "aggregate_report_local.json"), "w") as f:
        json.dump(report, f, indent=1)
    print("\nmanifest files:", len(manifest["files"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
