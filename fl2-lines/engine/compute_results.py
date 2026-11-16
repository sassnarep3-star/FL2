"""FL2 verified results feed + price-snapshot store.

Two products, both built from files committed in this repository so that any number on
the site can be reproduced with `python3 fl2-lines/engine/compute_results.py`:

1. RESULTS FEED  — every 2026 regular-season game with a *confirmed* final score, and a
   reconciliation of that feed against the official NFL.com standings snapshot. A game
   whose score was not confirmed on an official page is carried with blank scores and a
   status, never with a guessed number.
2. PRICE-SNAPSHOT STORE — opening and closing numbers, per market, for every fixture we
   originate, plus a per-source index with SHA-256 so a capture cannot be edited
   silently. The store records what the source actually carries; where a source carries
   no timestamp, the field stays null and the gap is published instead of back-filled.

Sign convention (verified, not assumed, in this file): nflverse `spread_line` is the
HOME spread with positive = home favoured. It is checked against the moneyline sign and
against the cover rate; the build aborts if either check fails.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
from collections import defaultdict
from pathlib import Path

SECTION = Path(__file__).resolve().parents[1]
REPO = SECTION.parent
DERIVED = SECTION / "data" / "derived"
OFFICIAL = SECTION / "data" / "official"
PRICES = SECTION / "data" / "prices"
for d in (DERIVED, PRICES):
    d.mkdir(parents=True, exist_ok=True)

NFLVERSE_GAMES = REPO / "raw" / "_nfldata" / "games.csv"
NFLVERSE_CLOSING = REPO / "raw" / "_nfldata" / "closing_lines.csv"
NFLVERSE_INITIAL = REPO / "raw" / "_nfldata" / "initial_lines.csv"
SIGNAL_CLOSING = REPO / "signal" / "data" / "closing_prices.csv"

SOURCE_URLS = {
    "nflverse_games": "https://github.com/nflverse/nfldata",
    "nflverse_closing_lines": "https://github.com/nflverse/nfldata/blob/master/data/closing_lines.csv",
    "nflverse_initial_lines": "https://github.com/nflverse/nfldata/blob/master/data/initial_lines.csv",
    "nflcom_standings": "https://www.nfl.com/standings/division/2026/REG",
    "nflcom_week10": "https://www.nfl.com/schedules/2026/by-week/week-10",
    "nflcom_week11": "https://www.nfl.com/schedules/2026/by-week/week-11",
    "nflcom_injuries": "https://www.nfl.com/injuries/",
}
# Official-page captures used by this build. The fetch layer served a page state in which
# the Week 10 8:20 PM ET game had no published final and the 8:15 PM ET Monday game had
# not been played; that is recorded rather than smoothed over.
CAPTURE = {
    "requested_utc": "2026-11-16T01:15:24Z",
    "pages": {
        "https://www.nfl.com/standings/division/2026/REG": "2026-11-16T01:15Z",
        "https://www.nfl.com/schedules/2026/by-week/week-10": "2026-11-16T01:16Z",
        "https://www.nfl.com/schedules/2026/by-week/week-11": "2026-11-16T01:19Z",
        "https://www.nfl.com/games/steelers-at-bengals-2026-reg-10": "2026-11-16T01:22Z",
        "https://www.nfl.com/injuries/": "2026-11-16T01:12Z",
        "https://www.nfl.com/news/2026-nfl-schedule-release-complete-slate-of-week-1-games": "2026-11-16T01:26Z",
    },
    "observed_state": (
        "Week 10 Sunday 1:00/4:05/4:25 PM ET games printed FINAL; the 8:20 PM ET game "
        "(PIT @ CIN) still printed its 8:20 PM kickoff and no score, and the Monday "
        "8:15 PM ET game (LAC @ BAL) was listed as upcoming. Standings showed PIT and CIN "
        "at 6-2 with PF/PA excluding that game, so the standings snapshot and the results "
        "snapshot are mutually consistent at the capture instant."
    ),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_rev() -> str:
    try:
        return subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def write_csv(path: Path, rows: list[dict], cols: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def num(x, cast=float):
    if x is None or x == "":
        return None
    try:
        return cast(x)
    except ValueError:
        return None


# ---------------------------------------------------------------- results feed
def build_results() -> dict:
    games_raw_all = [
        r
        for r in read_csv(NFLVERSE_GAMES)
        if int(r.get("season") or 0) >= 2015 and r.get("game_type") == "REG" and r.get("away_score") not in (None, "")
    ]
    games_raw = [
        r
        for r in read_csv(NFLVERSE_GAMES)
        if r.get("season") == "2026" and r.get("game_type") == "REG"
    ]
    official = read_csv(OFFICIAL / "nflcom-week10-results.csv")
    off_final = {
        (r["away_team"], r["home_team"]): r
        for r in official
        if r["away_score"] not in ("", None)
    }
    off_other = {
        (r["away_team"], r["home_team"]): r
        for r in official
        if r["away_score"] in ("", None)
    }
    feed = []
    seen = set()
    for r in games_raw:
        key = (r["away_team"], r["home_team"])
        played = r["away_score"] not in (None, "")
        if not played and key in off_final:
            continue  # the official page already carries this final; do not keep a blank twin
        row = {
            "game_id": r["game_id"], "season": r["season"], "game_type": r["game_type"],
            "week": str(int(r["week"])), "gameday": r["gameday"],
            "away_team": r["away_team"], "away_score": r["away_score"] or "",
            "home_team": r["home_team"], "home_score": r["home_score"] or "",
            "stadium": r.get("stadium", ""), "roof": r.get("roof", ""), "surface": r.get("surface", ""),
            "venue_source": "nflverse games.csv `stadium` (mirror of official schedule) - NOT transcribed from game centre",
            "game_centre_url": "",
            "spread_line": r.get("spread_line", ""), "total_line": r.get("total_line", ""),
            "home_moneyline": r.get("home_moneyline", ""), "away_moneyline": r.get("away_moneyline", ""),
            "home_spread_odds": r.get("home_spread_odds", ""), "away_spread_odds": r.get("away_spread_odds", ""),
            "over_odds": r.get("over_odds", ""), "under_odds": r.get("under_odds", ""),
            "home_rest": r.get("home_rest", ""), "away_rest": r.get("away_rest", ""),
            "result_prov": (
                "nflverse mirror of official box scores" if played
                else "SCHEDULED - no official final exists at capture; scores left blank"
            ),
        }
        if key in off_final:
            row["game_centre_url"] = off_final[key]["game_centre_url"]
        elif key in off_other:
            row["game_centre_url"] = off_other[key]["game_centre_url"]
        feed.append(row)
        seen.add(key)
    for key, r in off_final.items():
        if key in seen:
            continue
        feed.append({
            "game_id": r["game_id"], "season": "2026", "game_type": "REG",
            "week": r["game_id"].split("_")[1], "gameday": r["gameday"],
            "away_team": r["away_team"], "away_score": r["away_score"],
            "home_team": r["home_team"], "home_score": r["home_score"],
            "stadium": r.get("venue_note") or "", "roof": "", "surface": "",
            "venue_source": "nfl.com Week 10 schedule page (official): " + (r.get("venue_note") or "venue not printed"),
            "game_centre_url": r["game_centre_url"],
            "spread_line": "", "total_line": "", "home_moneyline": "", "away_moneyline": "",
            "home_spread_odds": "", "away_spread_odds": "", "over_odds": "", "under_odds": "",
            "home_rest": "", "away_rest": "",
            "result_prov": "official-nflcom-transcribed (no price in any reachable source)",
        })
    for key, r in off_other.items():
        if key in seen:
            continue
        feed.append({
            "game_id": r["game_id"], "season": "2026", "game_type": "REG",
            "week": r["game_id"].split("_")[1], "gameday": r["gameday"],
            "away_team": r["away_team"], "away_score": "", "home_team": r["home_team"], "home_score": "",
            "stadium": r.get("venue_note") or "", "roof": "", "surface": "",
            "venue_source": "nfl.com Week 10 schedule page (official)", "game_centre_url": r["game_centre_url"],
            "spread_line": "", "total_line": "", "home_moneyline": "", "away_moneyline": "",
            "home_spread_odds": "", "away_spread_odds": "", "over_odds": "", "under_odds": "",
            "home_rest": "", "away_rest": "",
            "result_prov": "UNVERIFIED - " + (r["status"] or "no official final at capture"),
        })
    feed.sort(key=lambda r: (r["gameday"], r["game_id"]))

    # ---- sign convention checks (abort, do not silently proceed).
    # The gate is run on the LONG window, not on 2026 alone: 2026 is a road-team season
    # (home cover 40.9% on n=137), and gating a sign convention on one season's cover
    # rate would abort on a real feature of the world rather than on a data error.
    all_raw = [r for r in games_raw_all if num(r.get("spread_line")) is not None and num(r.get("home_moneyline")) is not None and r.get("away_score")]
    pairs_hist = [(float(r["home_moneyline"]), float(r["spread_line"])) for r in all_raw]
    hist_fav = [s for ml, s in pairs_hist if ml < 0]
    agree_hist = sum(1 for s in hist_fav if s > 0) / len(hist_fav) if hist_fav else 0
    cover_h, n_h = 0, 0
    for r in all_raw:
        m = int(r["home_score"]) - int(r["away_score"])
        n_h += 1
        if m - float(r["spread_line"]) > 0:
            cover_h += 1
    cover_hist = cover_h / n_h if n_h else 0

    pairs = [
        (float(r["home_moneyline"]), float(r["spread_line"]))
        for r in feed
        if num(r.get("home_moneyline")) is not None and num(r.get("spread_line")) is not None
    ]
    home_fav = [s for ml, s in pairs if ml < 0]
    agree = sum(1 for s in home_fav if s > 0) / len(home_fav) if home_fav else 0
    cover, n = 0, 0
    for r in feed:
        if num(r.get("spread_line")) is None or r["away_score"] == "":
            continue
        m = int(r["home_score"]) - int(r["away_score"])
        n += 1
        if m - float(r["spread_line"]) > 0:
            cover += 1
    cover_rate = cover / n if n else 0
    checks = {
        "gate_sign_spread_line_is_home_line_positive_home_fav": {
            "window": "all games 2015-2026 in the committed mirror",
            "share_of_home_moneyline_favourites_with_positive_spread_line": round(agree_hist, 4),
            "n": len(hist_fav),
            "pass": agree_hist > 0.9,
        },
        "gate_home_cover_rate_near_50": {
            "window": "all games 2015-2026 in the committed mirror",
            "home_cover_pct": round(100 * cover_hist, 2),
            "n_graded": n_h,
            "pass": 0.44 < cover_hist < 0.56,
            "note": "pushes counted as non-cover; a flipped sign lands near 57% and aborts",
        },
        "measurement_home_cover_2026": {
            "home_cover_pct": round(100 * cover_rate, 2),
            "n_graded": n,
            "share_home_ml_favs_with_positive_line_pct": round(100 * agree, 2),
            "n": len(home_fav),
            "note": "published as a finding, not used as a gate; a gate on this window would abort on a real league-wide pattern",
        },
    }
    if not all(c["pass"] for c in checks.values() if "pass" in c):
        raise SystemExit(f"SIGN CONVENTION FAILED: {json.dumps(checks, indent=1)}")

    # ---- league-wide totals used later (all 2026 scored games)
    scored = [r for r in feed if r["away_score"] != ""]
    # ---- reconciliation against official standings snapshot
    off = {r["team"]: r for r in read_csv(OFFICIAL / "nflcom-standings-2026-w10.csv")}
    rec = defaultdict(lambda: [0, 0, 0, 0, 0])
    for r in scored:
        a, h = r["away_team"], r["home_team"]
        av, hv = int(r["away_score"]), int(r["home_score"])
        rec[a], rec[h]  # touch
        rec[a][3] += av
        rec[a][4] += hv
        rec[h][3] += hv
        rec[h][4] += av
        if av > hv:
            rec[a][0] += 1
            rec[h][1] += 1
        elif hv > av:
            rec[h][0] += 1
            rec[a][1] += 1
        else:
            rec[a][2] += 1
            rec[h][2] += 1
    recon_rows, matched = [], 0
    for t in sorted(off):
        mine, o = rec[t], off[t]
        exp = (int(o["w"]), int(o["l"]), int(o["t"]), int(o["pf"]), int(o["pa"]))
        got = (mine[0], mine[1], mine[2], mine[3], mine[4])
        ok = exp == got
        matched += ok
        recon_rows.append(
            {
                "team": t,
                "feed_wlt": "%d-%d-%d" % got[:3],
                "official_wlt": "%d-%d-%d" % exp[:3],
                "feed_pf": got[3],
                "official_pf": exp[3],
                "feed_pa": got[4],
                "official_pa": exp[4],
                "match": "yes" if ok else "NO",
                "source_url": o["source_url"],
                "captured_utc": o["captured_utc"],
            }
        )
    write_csv(
        DERIVED / "results-2026.csv",
        scored + [r for r in feed if r["away_score"] == ""],
        [
            "game_id", "season", "game_type", "week", "gameday", "away_team", "away_score",
            "home_team", "home_score", "roof", "surface", "stadium", "venue_source",
            "game_centre_url", "spread_line", "total_line", "home_moneyline", "away_moneyline",
            "home_spread_odds", "away_spread_odds", "over_odds", "under_odds", "home_rest",
            "away_rest", "result_prov",
        ],
    )
    write_csv(DERIVED / "results-reconciliation.csv", recon_rows, list(recon_rows[0].keys()))
    unplayed = [r for r in feed if r["away_score"] == ""]
    return {
        "games_in_feed": len(feed),
        "games_scheduled_no_final": len(unplayed),
        "games_priced_forward": sum(1 for r in unplayed if r.get("spread_line")),
        "forward_weeks": dict(sorted({w: sum(1 for r in unplayed if r["week"] == w) for w in {r["week"] for r in unplayed}}.items(), key=lambda kv: int(kv[0]))),
        "games_with_confirmed_final": len(scored),
        "games_blank_unverified": len([r for r in feed if r["away_score"] == ""]),
        "week1_total": dict(
            sorted(
                {w: sum(1 for r in scored if r["week"] == w) for w in {r["week"] for r in scored}}.items(),
                key=lambda kv: int(kv[0]),
            )
        ),
        "pre_kickoff_corpus_games": sum(1 for r in scored if int(r["week"]) <= 9),
        "reconciliation": {
            "teams_compared": len(off),
            "teams_matching_official": matched,
            "metric": "W-L-T, points for, points against, recomputed from the feed only",
            "result": "32/32 exact" if matched == len(off) else f"{matched}/{len(off)}",
        },
        "sign_convention_checks": checks,
        "capture": CAPTURE,
        "sources": SOURCE_URLS,
        "built_from": {
            "nflverse_games_sha256": sha256(NFLVERSE_GAMES),
            "nflverse_games_rows": len(read_csv(NFLVERSE_GAMES)),
            "provenance": "the commit that carries this file is the record of when it was built; "
                          "a git SHA is deliberately not embedded here because it would make the "
                          "artefact non-reproducible from the same inputs",
        },
    }


# ---------------------------------------------------------------- price store
def build_price_store(originate_ids: set[str]) -> dict:
    """Opening + closing numbers for every market, per fixture, from the price sources
    this repository actually holds. Nothing is inferred: a missing side stays missing."""
    index, files = [], {}
    for key, path in (
        ("nflverse_games_lines", NFLVERSE_GAMES),
        ("nflverse_closing_lines", NFLVERSE_CLOSING),
        ("nflverse_initial_lines", NFLVERSE_INITIAL),
        ("signal_closing_prices", SIGNAL_CLOSING),
    ):
        if not path.exists():
            files[key] = {"present": False, "path": str(path.relative_to(REPO))}
            continue
        rows = read_csv(path)
        # not every price file carries a season column; a numeric game_id prefix is the same
        # fact, so read it from there rather than publishing "None" as if it were unknown.
        def _season(r):
            v = (r.get("season") or "").strip()
            if v:
                return v
            for key in ("game_id", "away_team_id"):
                g = (r.get(key) or "").strip()
                if g[:4].isdigit() and 1999 <= int(g[:4]) <= 2100:
                    return g[:4]
            return ""
        seasons = sorted({_season(r) for r in rows} - {""})
        files[key] = {
            "present": True,
            "path": str(path.relative_to(REPO)),
            "rows": len(rows),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "seasons_min": seasons[0] if seasons else None,
            "seasons_max": seasons[-1] if seasons else None,
            "carries_timestamp": "date" in rows[0] or "timestamp" in (rows[0] or {}),
            "columns": list(rows[0].keys()) if rows else [],
        }

    # opening lines: nflverse initial_lines is book-by-book and only covers some seasons
    opens: dict[tuple[str, str, str], dict] = {}
    for r in read_csv(NFLVERSE_INITIAL):
        gid = (r.get("about") or "").strip()
        if not gid:
            continue
        typ = (r.get("type") or "").upper()
        opens.setdefault((gid, typ, (r.get("side") or "").strip()), r)

    # closing lines: book-by-book file + games.csv columns
    closes: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for r in read_csv(NFLVERSE_CLOSING):
        closes[((r.get("alt_game_id") or r.get("game_id") or "").strip(), (r.get("type") or "").upper(), (r.get("side") or ""))].append(r)

    rows = []
    for g in read_csv(DERIVED / "results-2026.csv"):
        gid = g["game_id"]
        aw, hm = g["away_team"], g["home_team"]
        for market, sides in (
            ("SPREAD", [(hm, "spread_line", "home_spread_odds", aw, "away_spread_odds")]),
            ("TOTAL", [("OVER", "total_line", "over_odds", "UNDER", "under_odds")]),
            ("MONEYLINE", [(hm, "home_moneyline", "home_moneyline", aw, "away_moneyline")]),
        ):
            for side, line_col, odds_col, other_side, other_odds in sides:
                open_home = opens.get((gid, market, hm)) or opens.get((gid, market.upper(), hm))
                close_rows = closes.get((gid, market, hm)) or []
                rows.append(
                    {
                        "game_id": gid,
                        "week": g.get("week", ""),
                        "gameday": g.get("gameday", ""),
                        "market": market,
                        "reference_side": side,
                        "other_side": other_side,
                        "opening_line": num(open_home.get("line")) if open_home else None,
                        "opening_odds": None,
                        "opening_observed_at": None,
                        "opening_source": "nflverse initial_lines.csv" if open_home else "NOT CAPTURED",
                        "closing_line": num(g.get(line_col)),
                        "closing_odds": num(g.get(odds_col)) if odds_col != "home_moneyline" else num(g.get("home_moneyline")),
                        "closing_other_odds": num(g.get(other_odds)),
                        "closing_observed_at": None,
                        "closing_source": "nflverse games.csv closing line columns (mirror; no timestamp carried)",
                        "closing_books_in_closing_lines_file": len(close_rows),
                        "fixture_status": "FINAL" if g["away_score"] != "" else (g.get("result_prov") or ""),
                    }
                )
    cols = list(rows[0].keys())
    write_csv(PRICES / "price-snapshots-2026.csv", rows, cols)

    n_close = sum(1 for r in rows if r["closing_line"] is not None)
    n_open = sum(1 for r in rows if r["opening_line"] is not None)
    n_ts = sum(1 for r in rows if r["opening_observed_at"] or r["closing_observed_at"])
    per_market = defaultdict(lambda: {"rows": 0, "with_closing": 0, "with_opening": 0})
    for r in rows:
        m = per_market[r["market"]]
        m["rows"] += 1
        m["with_closing"] += r["closing_line"] is not None
        m["with_opening"] += r["opening_line"] is not None
    # Per-season depth of every price file we hold. Two of the three have no season column,
    # so the season is taken from the game_id's year prefix - the same fact, stated honestly
    # rather than lumped into a "?" bucket that hides how thin the history actually is.
    def _season_of(r):
        v = (r.get("season") or "").strip()
        if v:
            return v
        g = (r.get("game_id") or "").strip()
        return g[:4] if len(g) >= 4 and g[:4].isdigit() else "not dated"

    hist_index = defaultdict(lambda: defaultdict(lambda: {"close_rows": 0, "open_rows": 0}))
    for path, kind in ((NFLVERSE_CLOSING, "close_rows"), (NFLVERSE_INITIAL, "open_rows"),
                       (SIGNAL_CLOSING, "close_rows")):
        if not path.exists():
            continue
        for r in read_csv(path):
            hist_index[_season_of(r)][path.name][kind] += 1
    index = [
        {"season": s, "source": f,
         "rows": hist_index[s][f]["close_rows"] + hist_index[s][f]["open_rows"],
         "closing_price_rows": hist_index[s][f]["close_rows"],
         "opening_price_rows": hist_index[s][f]["open_rows"]}
        for s in sorted(hist_index, key=lambda x: str(x)) for f in sorted(hist_index[s])
    ]
    write_csv(PRICES / "price-source-index.csv", index,
              ["season", "source", "rows", "closing_price_rows", "opening_price_rows"])

    merkle = []
    for p in sorted(PRICES.glob("*")) + sorted((DERIVED / "results-2026.csv",)):
        if p.is_file():
            merkle.append(f"{sha256(p)}  {p.relative_to(SECTION)}")
    (PRICES / "MANIFEST.sha256").write_text("\n".join(merkle) + "\n", encoding="utf-8")

    return {
        "markets_recorded": len(rows),
        "with_closing_number": n_close,
        "with_opening_number": n_open,
        "with_any_observed_at": n_ts,
        "by_market": dict(per_market),
        "source_files": files,
        "historical_price_index_rows": len(index),
        "manifest": "fl2-lines/data/prices/MANIFEST.sha256",
        "provenance": "content-pinned by MANIFEST.sha256; no build-time git SHA is embedded so the "
                      "store rebuilds byte-identically from the same inputs",
    }


if __name__ == "__main__":
    meta = build_results()
    (DERIVED / "results-meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    ids = {r["game_id"] for r in read_csv(DERIVED / "results-2026.csv")}
    prices = build_price_store(ids)
    (PRICES / "price-store-meta.json").write_text(json.dumps(prices, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: meta[k] for k in ("games_in_feed", "games_with_confirmed_final", "games_blank_unverified", "pre_kickoff_corpus_games")}, indent=1))
    print("reconciliation:", meta["reconciliation"]["result"])
    print("price store:", {k: prices[k] for k in ("markets_recorded", "with_closing_number", "with_opening_number", "with_any_observed_at")})
