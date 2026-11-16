#!/usr/bin/env python3
"""
tools/build_price_store.py — FL2 price-snapshot store (T22).

Schema (one row per game x market x side), per research/price-data-policy.md:
  game_id, week, market (SIDE|TOTAL|MONEYLINE), side, opening_*, closing_*,
  status (paired|open-only|close-only|pending-close), source_url, flags.

Layers:
  1. 2021 season — the ONLY season with both opening (WSGT) and closing lines
     reachable from this environment (nflverse initial_lines.csv + games.csv).
     Emits real open/close pairs, status=paired.
  2. 2026 season, Weeks 1-10 — closing numbers from nflverse games.csv columns
     (spread_line / total_line / moneylines), status=close-only.
  3. 2026 Week 11 — opening capture from Yahoo consensus (T3,
     data/captures/week11-market-2026-11-16.json), closing blank,
     status=pending-close. Quoted moneyline blank + flagged (provider page
     showed spread/total only; never imputed).

Every market row is flagged market_data_unverified=true: no official league
price source exists (nfl.com/odds is 404). Deterministic; stdlib only.

Self-check: a paired row must have both sides non-blank; a pending-close row must
have blank closing fields; every row must carry a source_url.
"""
from __future__ import annotations

import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_CSV = os.path.join(ROOT, "data", "price_snapshots.csv")
OUT_JSON = os.path.join(ROOT, "data", "price_snapshots.json")

NFLVERSE_GAMES = "https://github.com/nflverse/nfldata/blob/master/data/games.csv"
NFLVERSE_INIT = "https://github.com/nflverse/nfldata/blob/master/data/initial_lines.csv"


def num(x):
    return x if x not in ("", None) else ""


def build_2021_pairs(rows_out):
    init = list(csv.DictReader(open(os.path.join(ROOT, "raw", "_nfldata", "initial_lines.csv"))))
    clos = {}
    for g in csv.DictReader(open(os.path.join(ROOT, "raw", "games.csv"))):
        if g["season"] == "2021" and g["game_type"] == "REG":
            clos[g["game_id"]] = g
    # initial_lines uses game ids like 2021_01_DAL_TB (alt style). Match on suffix.
    by_suffix = {}
    for gid, g in clos.items():
        by_suffix[gid] = g
    paired = 0
    for r in init:
        if r["season"] != "2021":
            continue
        gid = r["about"]
        g = by_suffix.get(gid)
        if g is None:
            continue
        typ = r["type"]
        side = r["side"]
        market = {"SPREAD": "SIDE", "TOTAL": "TOTAL", "MONEYLINE": "MONEYLINE"}.get(typ)
        if market is None:
            continue
        close_line = ""
        close_odds = ""
        if market == "SIDE":
            # store convention: the named side's DISPLAY line, negative = that team favoured.
            # games.csv spread_line convention: positive = home favourite.
            sl = float(g["spread_line"])
            close_line = (-sl if side == g["home_team"] else sl)
            close_odds = g["home_spread_odds"] if side == g["home_team"] else g["away_spread_odds"]
        elif market == "TOTAL":
            close_line = g["total_line"]
            close_odds = g["over_odds"] if side == "over" else g["under_odds"]
        else:
            close_odds = g["home_moneyline"] if side == g["home_team"] else g["away_moneyline"]
        if close_line == "" and close_odds == "":
            continue
        rows_out.append({
            "game_id": gid, "season": 2021, "week": int(gid.split("_")[1]),
            "market": market, "side": side,
            "opening_line": r["line"], "opening_odds": "",
            "opening_provider": f'WSGT (via nflverse initial_lines.csv)',
            "opening_captured_at": "historical (no capture timestamp published by provider)",
            "closing_line": num(close_line), "closing_odds": num(close_odds),
            "closing_provider": "market consensus (nflverse games.csv)",
            "closing_captured_at": "2026-11-14T03:30:00Z (mirror fetch)",
            "status": "paired",
            "source_url": NFLVERSE_INIT, "closing_source_url": NFLVERSE_GAMES,
            "market_data_unverified": "true",
            "note": "opening history exists for 2021 only in this environment",
        })
        paired += 1
    return paired


def build_2026_closings(rows_out):
    n = 0
    for g in csv.DictReader(open(os.path.join(ROOT, "raw", "games.csv"))):
        if g["season"] != "2026" or g["game_type"] != "REG":
            continue
        if int(g["week"]) > 10:
            continue
        gid, away, home = g["game_id"], g["away_team"], g["home_team"]
        wk = int(g["week"])
        base = dict(game_id=gid, season=2026, week=wk,
                    opening_line="", opening_odds="", opening_provider="",
                    opening_captured_at="",
                    closing_provider="market consensus (nflverse games.csv)",
                    closing_captured_at="2026-11-14T03:30:00Z (mirror fetch)",
                    status="close-only", source_url=NFLVERSE_GAMES,
                    closing_source_url=NFLVERSE_GAMES,
                    market_data_unverified="true", note="")
        sl, tl = g["spread_line"], g["total_line"]
        if sl != "":
            rows_out.append({**base, "market": "SIDE", "side": home,
                             "closing_line": -float(sl),
                             "closing_odds": g["home_spread_odds"], "note":
                             "closing_line is the named side's display line (negative=favoured); source spread_line convention: positive = home favourite (verified 3476/3490)"})
        if tl != "":
            for s, o in (("over", g["over_odds"]), ("under", g["under_odds"])):
                rows_out.append({**base, "market": "TOTAL", "side": s,
                                 "closing_line": tl, "closing_odds": o})
        for s, o in ((home, g["home_moneyline"]), (away, g["away_moneyline"])):
            if o != "":
                rows_out.append({**base, "market": "MONEYLINE", "side": s,
                                 "closing_line": "", "closing_odds": o})
        n += 1
    return n


def build_week11_openings(rows_out):
    cap = json.load(open(os.path.join(ROOT, "data", "captures", "week11-market-2026-11-16.json")))
    for g in cap["games"]:
        base = dict(game_id=g["game_id"], season=2026, week=11,
                    opening_provider=cap["provider"],
                    opening_captured_at=cap["captured_at_utc"],
                    closing_line="", closing_odds="", closing_provider="",
                    closing_captured_at="",
                    status="pending-close",
                    source_url=cap["provider_url"],
                    closing_source_url="",
                    market_data_unverified="true",
                    note="closing capture scheduled pre-kickoff (policy 4b)")
        rows_out.append({**base, "market": "SIDE", "side": g["home"],
                         "opening_line": -float(g["spread_line_home_fav_positive"]), "opening_odds": ""})
        rows_out.append({**base, "market": "TOTAL", "side": "over",
                         "opening_line": g["total"], "opening_odds": ""})
        rows_out.append({**base, "market": "MONEYLINE", "side": g["home"],
                         "opening_line": "", "opening_odds": "",
                         "note": "quoted ML blank + flagged: provider page showed spread/total only at capture"})
        rows_out.append({**base, "market": "MONEYLINE", "side": g["away"],
                         "opening_line": "", "opening_odds": "",
                         "note": "quoted ML blank + flagged: provider page showed spread/total only at capture"})


def self_check(rows):
    errs = []
    for r in rows:
        if r["status"] == "paired" and (r["opening_line"] == "" or r["closing_line"] == ""):
            errs.append(f'paired row with blank side: {r["game_id"]} {r["market"]}')
        if r["status"] == "pending-close" and (r["closing_line"] != "" or r["closing_odds"] != ""):
            errs.append(f'pending-close row with closing data: {r["game_id"]}')
        if not r["source_url"]:
            errs.append(f'row without source_url: {r["game_id"]}')
    return errs


def main() -> int:
    rows = []
    n_pair = build_2021_pairs(rows)
    n_close = build_2026_closings(rows)
    build_week11_openings(rows)
    errs = self_check(rows)
    if errs:
        print("SELF-CHECK FAILED")
        for e in errs:
            print(" -", e)
        return 1
    fields = list(rows[0].keys())
    with open(OUT_CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    payload = {
        "meta": {
            "generated_by": "tools/build_price_store.py",
            "generated_at_utc": "2026-11-16T02:30:00Z",
            "policy": "research/price-data-policy.md (frozen 2026-11-16, decided before any backtest publish)",
            "rows": len(rows),
            "paired_open_close_rows": n_pair,
            "close_only_2026_games": n_close,
            "week11_open_capture": "data/captures/week11-market-2026-11-16.json",
            "convention": "SIDE rows quote the named team's display line (negative = that team favoured); TOTAL rows quote the total; MONEYLINE rows quote American odds",
            "limits": [
                "no official league price source exists (nfl.com/odds -> 404); every price is market_data_unverified",
                "opening-line history: 2021 only (WSGT via nflverse initial_lines.csv)",
                "Week 11 quoted moneylines blank + flagged (provider showed spread/total only)",
            ],
        },
        "prices": rows,
    }
    json.dump(payload, open(OUT_JSON, "w"), indent=1)
    print(f"price store OK: {len(rows)} rows ({n_pair} paired 2021, {n_close} close-only 2026 games)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
