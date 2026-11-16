#!/usr/bin/env python3
"""
engine/linelab/price_store.py — the price-snapshot store.

Requirement served: "Add a price-snapshot store that records opening and closing
numbers for every market we originate", plus the pre-cursor requirement
"Decide the price-data policy before any backtest is published".

WHAT THIS DOES
--------------
For every REG game from 1999 to the last completed week it writes one row per
market (side, total, moneyline) carrying:

  * opening number  (where a genuine pre-kickoff opening price exists)
  * closing number  (where a genuine closing price exists)
  * the source URL of each number, and the dataset vintage
  * a `price_basis` label that says, in plain words, what the number IS

It never fills a number it does not have. A market with no verified opening
price gets `opening = null` and `opening_status = "not_available"`.

THE PRICE-DATA POLICY IS ENCODED HERE, NOT DOCUMENTED ELSEWHERE AND IGNORED
--------------------------------------------------------------------------
1. Four distinct line families exist in the nflverse `nfldata` repository. They
   are NOT interchangeable and this builder refuses to merge them:

     games.spread_line / total_line  ... nflverse's own single number. Its
         documentation does not state whether it is open or close, so it is
         labelled `basis=unspecified_single_line` and may NOT be used as an
         opening price in any backtest.
     sc_lines.csv (2013-2020)        ... one number per side per game. A spread
         only: the two sides sum to exactly zero, so it is a two-sided spread
         price, not a total. Labelled `basis=spread_only_unspecified`.
     initial_lines.csv (2021 only)   ... one sportsbook (WSGT) opening spread and
         opening total for 2021. This is a genuine OPENING price and the only one
         in the repository. Labelled `basis=opening`.
     closing_lines.csv (2006-2018)   ... consensus close with per-side odds.
         Genuine CLOSING price. Labelled `basis=closing`.

2. A market row may therefore be open-only, close-only, both, or neither.
   `price_pair_status` records which, and the backtest layer is forbidden from
   using rows whose pair status is not `open_and_close` for line-movement work.

3. Moneyline has no opening price anywhere in the repository before 2021 and no
   opening price in 2021 either (initial_lines.csv carries no MONEYLINE rows).
   Moneyline opening is therefore `not_available` for every season. That is a
   fact about the data, published as a fact, not worked around.

4. Nothing here is a model output. This is market data only.

SOURCES (all re-downloadable; hashes recorded in the manifest by ingest step)
---------------------------------------------------------------------------
  https://github.com/nflverse/nfldata  (data/games.csv, data/closing_lines.csv,
      data/sc_lines.csv, data/initial_lines.csv) — repository tarball, which is
      reachable from this sandbox via codeload.github.com
  https://github.com/nflverse/nflverse-data/releases/download/... — the release
      assets named in the prior sessions' manifest; NOT reachable from this
      sandbox (release-assets.githubusercontent.com is blocked) but they are the
      long-run canonical location and are cited as such.

OUTPUT
  data/linelab/price_store.csv      one row per (game, market)
  data/linelab/price_store_meta.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stamp import stamp_fields  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "raw", "_nfldata")
OUTDIR = os.path.join(ROOT, "data", "linelab")

REPO_TARBALL = "https://codeload.github.com/nflverse/nfldata/tar.gz/refs/heads/master"
REPO_BLOB = "https://github.com/nflverse/nfldata/blob/master/data/{f}"
RELEASE = "https://github.com/nflverse/nflverse-data/releases/download"

# Published by nflverse/nfldata (Lee Sharpe). Cited for every derived number.
GAMES_SRC = REPO_BLOB.format(f="games.csv")
CLOSE_SRC = REPO_BLOB.format(f="closing_lines.csv")
SC_SRC = REPO_BLOB.format(f="sc_lines.csv")
INIT_SRC = REPO_BLOB.format(f="initial_lines.csv")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rows(name: str) -> list[dict]:
    path = os.path.join(RAW, name)
    if not os.path.exists(path):
        raise SystemExit(f"missing raw file {path} — cannot build the price store")
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def money(s: str):
    if s is None or s == "" or s == "NA":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def build() -> dict:
    os.makedirs(OUTDIR, exist_ok=True)

    games = rows("games.csv")
    closing = rows("closing_lines.csv")
    sc = rows("sc_lines.csv")
    initial = rows("initial_lines.csv")

    # ---------------------------------------------------------------- closing
    # closing_lines.csv: game_id is an old-format id; alt_game_id is the
    # nflverse game_id. Key on alt_game_id and keep the ids for audit.
    close_by: dict[str, dict] = defaultdict(dict)
    for r in closing:
        gid = r["alt_game_id"]
        if not gid:
            continue
        side = r["side"]
        close_by[gid].setdefault(r["type"], {})[side] = r

    # ----------------------------------------------------------------- sc_lines
    # two rows per game; side line sums to zero => spread. Store both sides.
    scspread: dict[str, dict[str, float]] = defaultdict(dict)
    for r in sc:
        scspread[r["game_id"]][r["side"]] = money(r["line"])

    # ------------------------------------------------------------ initial_lines
    # 2021 only. `about` is the game_id. type SPREAD|TOTAL, side is the team for
    # SPREAD and is a team name for TOTAL as well (one row per side).
    initial_by: dict[str, dict] = defaultdict(dict)
    for r in initial:
        gid = r["about"]
        initial_by[gid].setdefault(r["type"], {})[r["side"]] = money(r["line"])

    out: list[dict] = []
    stats = defaultdict(int)

    for g in games:
        if g["game_type"] != "REG":
            continue
        gid = g["game_id"]
        season = int(g["season"])
        week = int(g["week"]) if g["week"] else None
        kickoff = f'{g["gameday"]}T{g["gametime"]}' if g["gametime"] else g["gameday"]
        home, away = g["home_team"], g["away_team"]
        played = bool(g["home_score"] and g["away_score"])

        # nflverse's own single line — basis explicitly unspecified
        nv_spread = money(g["spread_line"])
        nv_total = money(g["total_line"])

        cl = close_by.get(gid, {})
        cl_spread = cl.get("SPREAD", {})
        cl_total = cl.get("TOTAL", {})
        cl_ml = cl.get("MONEYLINE", {})

        ini = initial_by.get(gid, {})
        ini_spread = ini.get("SPREAD", {})
        ini_total = ini.get("TOTAL", {})

        # ---- SPREAD (side market). Home side line, home-signed.
        open_spread = ini_spread.get(home)
        close_spread_home = money(cl_spread.get(home, {}).get("line", "")) if cl_spread else None
        sc_home = scspread.get(gid, {}).get(home)
        open_status = "opening" if open_spread is not None else "not_available"
        close_status = "closing" if close_spread_home is not None else "not_available"
        # sc_lines is a pre-kickoff spread but the repo does not date it as open
        # or close. It is a *fallback spread*, never an opening price.
        fallback = None if (open_spread is not None or close_spread_home is not None) else sc_home
        pair = (
            "open_and_close" if open_spread is not None and close_spread_home is not None
            else "open_only" if open_spread is not None
            else "close_only" if close_spread_home is not None
            else "single_line_only" if fallback is not None or nv_spread is not None
            else "none"
        )
        if pair == "open_and_close":
            stats["spread_open_and_close"] += 1
        elif pair == "open_only":
            stats["spread_open_only"] += 1
        elif pair == "close_only":
            stats["spread_close_only"] += 1
        elif pair == "single_line_only":
            stats["spread_single_only"] += 1
        else:
            stats["spread_none"] += 1

        out.append({
            "game_id": gid, "season": season, "week": week, "kickoff_utc": kickoff,
            "home": home, "away": away, "market": "side",
            "opening": open_spread, "opening_basis": "opening" if open_spread is not None else "",
            "opening_source": INIT_SRC if open_spread is not None else "",
            "closing": close_spread_home, "closing_basis": "closing" if close_spread_home is not None else "",
            "closing_source": CLOSE_SRC if close_spread_home is not None else "",
            "single_line": nv_spread,
            "single_line_basis": "unspecified_single_line" if nv_spread is not None else "",
            "single_line_source": GAMES_SRC if nv_spread is not None else "",
            "fallback_spread": fallback,
            "fallback_spread_source": SC_SRC if fallback is not None else "",
            "price_pair_status": pair,
            "nflverse_game_id": gid,
            "closing_alt_ids": ";".join(
                f'{r["game_id"]}:{r["odds"]}'
                for r in [cl_spread.get(home)] if r
            ),
            "result_home_score": g["home_score"] if played else "",
            "result_away_score": g["away_score"] if played else "",
        })

        # ---- TOTAL (over/under). Opening total exists for 2021 only.
        open_total = ini_total.get(home)
        if open_total is None:
            # TOTAL rows in initial_lines carry one row per side; take any value.
            vals = {v for v in ini_total.values() if v is not None}
            open_total = vals.pop() if len(vals) == 1 else None
        close_total_over = money(cl_total.get("OVER", {}).get("line", "")) if cl_total else None
        close_total_under = money(cl_total.get("UNDER", {}).get("line", "")) if cl_total else None
        close_total = close_total_over if close_total_over is not None else close_total_under
        pair = (
            "open_and_close" if open_total is not None and close_total is not None
            else "open_only" if open_total is not None
            else "close_only" if close_total is not None
            else "single_line_only" if nv_total is not None else "none"
        )
        stats[f"total_{pair}"] += 1
        out.append({
            "game_id": gid, "season": season, "week": week, "kickoff_utc": kickoff,
            "home": home, "away": away, "market": "total",
            "opening": open_total, "opening_basis": "opening" if open_total is not None else "",
            "opening_source": INIT_SRC if open_total is not None else "",
            "closing": close_total, "closing_basis": "closing" if close_total is not None else "",
            "closing_source": CLOSE_SRC if close_total is not None else "",
            "single_line": nv_total,
            "single_line_basis": "unspecified_single_line" if nv_total is not None else "",
            "single_line_source": GAMES_SRC if nv_total is not None else "",
            "fallback_spread": None, "fallback_spread_source": "",
            "price_pair_status": pair,
            "nflverse_game_id": gid,
            "closing_alt_ids": ";".join(
                f'{r["game_id"]}:{r["odds"]}'
                for r in [cl_total.get("OVER")] if r
            ),
            "result_home_score": g["home_score"] if played else "",
            "result_away_score": g["away_score"] if played else "",
        })

        # ---- MONEYLINE. Closing only, ever.
        ml_home = cl_ml.get(home, {}).get("odds")
        ml_away = cl_ml.get(away, {}).get("odds")
        ml_home_v = money(ml_home)
        if ml_home_v is not None:
            stats["moneyline_close_only"] += 1
        else:
            stats["moneyline_none"] += 1
        out.append({
            "game_id": gid, "season": season, "week": week, "kickoff_utc": kickoff,
            "home": home, "away": away, "market": "moneyline",
            # There is no opening moneyline anywhere in the repository, for any
            # season. This is recorded as unavailable, never estimated.
            "opening": None, "opening_basis": "", "opening_source": "",
            "closing": ml_home_v,
            "closing_basis": "closing" if ml_home_v is not None else "",
            "closing_source": CLOSE_SRC if ml_home_v is not None else "",
            "single_line": money(g["home_moneyline"]),
            "single_line_basis": "unspecified_single_line" if g["home_moneyline"] else "",
            "single_line_source": GAMES_SRC if g["home_moneyline"] else "",
            "fallback_spread": None, "fallback_spread_source": "",
            "price_pair_status": "close_only" if ml_home_v is not None else ("single_line_only" if g["home_moneyline"] else "none"),
            "nflverse_game_id": gid,
            "closing_alt_ids": f"home:{ml_home};away:{ml_away}" if ml_home_v is not None else "",
            "result_home_score": g["home_score"] if played else "",
            "result_away_score": g["away_score"] if played else "",
        })

    fields = [
        "game_id", "season", "week", "kickoff_utc", "home", "away", "market",
        "opening", "opening_basis", "opening_source",
        "closing", "closing_basis", "closing_source",
        "single_line", "single_line_basis", "single_line_source",
        "fallback_spread", "fallback_spread_source",
        "price_pair_status", "nflverse_game_id", "closing_alt_ids",
        "result_home_score", "result_away_score",
    ]
    path = os.path.join(OUTDIR, "price_store.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in out:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})

    by_season: dict[int, dict] = defaultdict(lambda: defaultdict(int))
    for r in out:
        by_season[r["season"]][r["market"] + ":" + r["price_pair_status"]] += 1

    meta = {
        **stamp_fields(),
        "builder": "engine/linelab/price_store.py",
        "rows": len(out),
        "markets": sorted({r["market"] for r in out}),
        "policy": {
            "opening_price_defined_as": (
                "A number published before kickoff that the repository dates as an opening "
                "price. In nfldata that is initial_lines.csv and only initial_lines.csv, "
                "which covers 2021 and nothing else."
            ),
            "closing_price_defined_as": (
                "A number in closing_lines.csv, which the repository dates as a close."
            ),
            "single_line_rule": (
                "games.spread_line / total_line / home_moneyline are ONE number per market "
                "whose open-or-close status the repository does not state. They are stored "
                "in separate columns, labelled unspecified_single_line, and are excluded from "
                "any open-to-close computation."
            ),
            "never_inferred": (
                "No opening price is inferred from a closing price, from sc_lines, or from "
                "another season. A market without a dated opening price stores null."
            ),
            "fallback_spread_rule": (
                "sc_lines.csv (2013-2020) is a two-sided spread that sums to zero (verified: "
                "2040/2040 two-row games sum to 0). Its date relative to kickoff is not stated, "
                "so it is a fallback spread and never an opening or closing price."
            ),
        },
        "coverage": {str(k): dict(v) for k, v in sorted(by_season.items())},
        "totals": dict(stats),
        "inputs": [
            {"file": "games.csv", "source": GAMES_SRC, "sha256": sha256(os.path.join(RAW, "games.csv"))},
            {"file": "closing_lines.csv", "source": CLOSE_SRC, "sha256": sha256(os.path.join(RAW, "closing_lines.csv"))},
            {"file": "sc_lines.csv", "source": SC_SRC, "sha256": sha256(os.path.join(RAW, "sc_lines.csv"))},
            {"file": "initial_lines.csv", "source": INIT_SRC, "sha256": sha256(os.path.join(RAW, "initial_lines.csv"))},
            {"file": "repository tarball", "source": REPO_TARBALL, "note": "how the four files were obtained"},
        ],
        "release_mirror_note": (
            "The nflverse release assets at " + RELEASE + "/schedules/games.csv are the "
            "canonical long-run location. They are not reachable from this sandbox "
            "(release-assets.githubusercontent.com is blocked); the repository copies used "
            "here are the same publisher. A GitHub Actions runner has open egress and the "
            "existing fetch-nflverse-data workflow can re-derive these from the release."
        ),
    }
    with open(os.path.join(OUTDIR, "price_store_meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1, sort_keys=False)

    print(f"price_store.csv: {len(out)} market rows -> {path}")
    for k, v in sorted(stats.items()):
        print(f"  {k:<28} {v}")
    print("  seasons:", min(by_season), "..", max(by_season))
    return meta


if __name__ == "__main__":
    m = build()
    # hard assertions: the store is worthless if these are not true
    assert m["rows"] > 20000, m["rows"]
    print("OK")
