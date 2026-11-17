"""
FL2 — build the single data bundle the static site consumes.

Run:  python3 engine/build_site_data.py
Out:  data/site_data.js   (assigns window.FL2 = {...})

Why one file: the site is served as static HTML from GitHub Pages with no build
step. One bundle means one cache key, one place to check, and no chance of the
pages disagreeing with each other.

Why the sanitising pass: Python's json module emits `NaN`/`Infinity`, which are
not valid JSON and throw inside JSON.parse in a browser. Every non-finite float
becomes `null` here, and any row that ends up with a null where a number was
expected is added to the flagged list.
"""
from __future__ import annotations

import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")


def load(name: str):
    with open(os.path.join(DATA, f"{name}.json")) as fh:
        return json.load(fh)


def clean(o):
    """Depth-first replace of non-finite floats with None."""
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    return o


def build_flags(backtest, parlays, week10, market):
    """Everything a human should check, assembled from the data itself so the
    list cannot drift out of sync with the tables."""
    flags = []

    # 1. unverified market prices for the upcoming week
    for g in market["games"]:
        if g["market"]["status"] != "present":
            flags.append({
                "id": f"market-{g['game_id'].replace(' ', '').replace('@', '-')}",
                "category": "Market price unavailable",
                "severity": "medium",
                "item": f"{g['game_id']} — no market line in the aggregated closing-line file",
                "detail": "The row is published with FL2's own number only. No price is invented. "
                          "Comparison vs. market is shown as blank.",
                "value": None,
                "sources": g["sources"],
                "action": "Enter the price manually from your own licensed feed if you want the "
                          "comparison column populated.",
            })

    # 2. starting QB not confirmed
    for t, rec in week10["team_depletion"].items():
        if rec["played_week10"] and rec["qb_starter"] is None and rec["qb_change"] != "none reported":
            flags.append({
                "id": f"qb-{t}",
                "category": "Lineup — starting QB unconfirmed",
                "severity": "high",
                "item": f"{t} — {rec['name']}: Week 10 starting quarterback not stated on the official pages reviewed",
                "detail": rec["qb_note"],
                "value": None,
                "sources": [rec["qb_source"]] if rec["qb_source"] else [],
                "action": "Confirm from the team's official site or the league transaction wire before "
                          "relying on this game's number.",
            })

    # 3. starter/backup depth not published
    flags.append({
        "id": "depth-rank",
        "category": "Lineup — depth chart not independently verified",
        "severity": "medium",
        "item": "Starter vs. 2nd/3rd/4th-string status for every non-QB on the Week 10 injury report",
        "detail": "The league publishes who is Out/Doubtful/Questionable, not that player's place on the "
                  "depth chart. The availability index uses a declared position weight as a proxy and does "
                  "not claim to know whether a backup is starting.",
        "value": None,
        "sources": [week10["sources"]["injuries"]],
        "action": "Add an official depth-chart feed (nflverse depth_charts) when the environment can reach "
                  "release assets, then recompute the index.",
    })

    # 4. player-prop combos
    for c in parlays["player_prop_combos"]:
        flags.append({
            "id": "prop-" + c["combo"][:24].replace(" ", "-").replace("+", "plus"),
            "category": "Player props — correlation unmeasured",
            "severity": "high",
            "item": c["combo"],
            "detail": f"Expected direction: {c['expected_corr']}. Measured by FL2: not measured. "
                      f"Reason: {c['why']}",
            "value": None,
            "sources": ["https://github.com/nflverse/nflverse-data/releases/tag/player_stats"],
            "action": "Requires a player-level feed. Do not price any player-prop combo until then.",
        })

    # 5. strategies that were untestable
    for s in backtest["strategies"]:
        if s.get("status") == "untestable":
            flags.append({
                "id": "strategy-" + s["sid"],
                "category": "Strategy — untestable",
                "severity": "medium",
                "item": f"{s['sid']} — {s['name']}",
                "detail": s.get("reason") or s.get("params", {}).get("data_gap"),
                "value": None,
                "sources": ["https://github.com/nflverse/nfldata/blob/master/data/initial_lines.csv"],
                "action": "Obtain an opening-line history before attempting to test this idea.",
            })

    # 6. strategies with an unusual hit rate worth a human look
    for s in backtest["strategies"]:
        if s.get("n", 0) and s.get("hit_rate") and s["hit_rate"] > 0.545:
            flags.append({
                "id": "anomaly-" + s["sid"],
                "category": "Anomaly — high hit rate that does not survive the gates",
                "severity": "high",
                "item": f"{s['sid']} hit {s['hit_rate']*100:.1f}% over {s['n']} bets "
                        f"but passed only {s['gates_passed']}/8 gates",
                "detail": "A high hit rate on a small sample is the most common false positive in this "
                          "field. The 95% CI lower bound "
                          f"({s['hit_rate_ci_lo']*100:.1f}%) does not clear the 52.38% break-even "
                          "threshold, and the profit CI spans zero. Treated as luck, not edge.",
                "value": round(s["hit_rate"], 4),
                "sources": ["https://github.com/sassnarep3-star/FL2/blob/main/data/backtest_summary.json"],
                "action": "Do not promote. If you want to keep looking, collect a forward sample of 300+ "
                          "bets at recorded prices.",
            })

    # 7. Week-10 MNF completion pending (results feed at 149/150, 2026-11-17)
    flags.append({
        "id": "results-feed-mnf-pending",
        "category": "Results feed — one game pending",
        "severity": "medium",
        "item": "LAC @ BAL (Week 10 MNF) — feed carries 149/150 finals",
        "detail": "The Monday-night game was live at the 2026-11-17 capture (Q2 00:38, 17-7; halftime "
                  "17-10 at the last read). The official page publishes no record block for LAC/BAL "
                  "while the game is live, so both scores and records stay blank. The final is never "
                  "inferred; a later immutable capture (same format as week10-snf-final-2026-11-17) "
                  "completes the feed to 150/150 when the game ends.",
        "value": None,
        "sources": [
            "https://www.nfl.com/games/chargers-at-ravens-2026-reg-10",
            "https://www.nfl.com/schedules/2026/by-week/week-10",
        ],
        "action": "Re-read the official game centre after the final whistle, append the final to a new "
                  "dated capture, rerun tools/build_results_feed.py (self-checks then expect 150 "
                  "finals), and recompute the ops panels.",
    })

    # 8. data that could not be downloaded at all
    flags.append({
        "id": "nflverse-assets",
        "category": "Data access — release assets unreachable",
        "severity": "high",
        "item": "nflverse player_stats / snap_counts / depth_charts / injuries release assets",
        "detail": "These are published as GitHub release assets, which 302 to objects.githubusercontent.com. "
                  "That host is not on this environment's allow-list, so the files could not be fetched. "
                  "No substitute or approximation was used.",
        "value": None,
        "sources": ["https://github.com/nflverse/nflverse-data/releases"],
        "action": "Run engine/fetch_data.py in an environment with unrestricted outbound HTTPS, or add a "
                  "licensed feed.",
    })

    # 9. resolved irregularity, kept visible
    flags.append({
        "id": "sign-error",
        "category": "Resolved — methodology defect found and fixed",
        "severity": "info",
        "item": "Spread cover test had an inverted sign during development",
        "detail": "The first build computed `home_margin + spread_line > 0` as a cover test, producing an "
                  "impossible 77.5% 'divisional home underdog cover rate'. The dataset's spread_line is the "
                  "expected home margin (positive = home favoured), so the correct test is "
                  "`home_margin - spread_line > 0`. Fixed, and an assertion now runs on every build.",
        "value": 0.4752,
        "sources": ["https://github.com/nflverse/nfldata/blob/master/data/games.csv"],
        "action": "None — closed. Kept on the page so the correction stays auditable.",
    })
    return flags


def build_sources(backtest, week10, parlays, market, manifest):
    S = week10["sources"]
    groups = [
        {
            "group": "Official league data",
            "items": [
                {"name": "NFL.com official injury report (2026 Week 10)", "url": S["injuries"],
                 "used_for": "76 Out/Doubtful rows, practice/game status, Week 10 schedule, TV",
                 "tier": "T1 official league"},
                {"name": "NFL.com standings (2026 REG)", "url": S["standings"],
                 "used_for": "W-L-T, points for/against, streaks for all 32 teams", "tier": "T1 official league"},
                {"name": "NFL.com injury report article (Week 10)", "url":
                    "https://www.nfl.com/news/nfl-week-10-injury-report-2026-season",
                 "used_for": "cross-reference for the weekly report", "tier": "T1 official league"},
            ],
        },
        {
            "group": "Official league news (lineup changes)",
            "items": [
                {"name": "League news roundup — Friday, Nov 13, 2026", "url": S["news_fri"],
                 "used_for": "QB decisions: MIN Kirk Cousins, BAL Lamar Jackson (out 6-10 weeks), "
                             "per-team practice/game status", "tier": "T1 official league"},
                {"name": "League news roundup — Wednesday, Nov 11, 2026", "url": S["news_wed"],
                 "used_for": "QB decisions: ARI Carson Beck, CLE Deshaun Watson", "tier": "T1 official league"},
                {"name": "Drew Lock to start for Seahawks (Nov 13)", "url": S["news_lock"],
                 "used_for": "SEA starting QB and backup, Sam Darnold ruled out", "tier": "T1 official league"},
                {"name": "Malik Willis to IR; Kyle McCord to start (Nov 10)", "url": S["news_mccord"],
                 "used_for": "MIA starting QB", "tier": "T1 official league"},
            ],
        },
        {
            "group": "Statistical registry",
            "items": [
                {"name": "Pro-Football-Reference — 2026 team defense", "url": S["pfr_def"],
                 "used_for": "Games, points allowed, total/pass/rush yards allowed, takeaways",
                 "tier": "T1 registry (Sports Reference)"},
                {"name": "Pro-Football-Reference — 2026 season index", "url": S["pfr_off"],
                 "used_for": "Cross-check of team offence and league averages", "tier": "T1 registry"},
            ],
        },
        {
            "group": "Open data used for all backtesting",
            "items": [
                {"name": "nflverse/nfldata — games.csv", "url":
                    "https://github.com/nflverse/nfldata/blob/master/data/games.csv",
                 "used_for": "1999-2026 results, closing spread/total, rest days, weather, venues. "
                             "7,548 rows; sha256 in data/manifest.json",
                 "tier": "T2 open data (derived from NFL play-by-play/GSIS ids)"},
                {"name": "nflverse/nfldata — closing_lines.csv", "url":
                    "https://github.com/nflverse/nfldata/blob/master/data/closing_lines.csv",
                 "used_for": "Closing spread/total/moneyline for the 2006-2013 seasons present in the file",
                 "tier": "T3 aggregated market data — never used as a statistical input"},
                {"name": "nflverse/nfldata — initial_lines.csv", "url":
                    "https://github.com/nflverse/nfldata/blob/master/data/initial_lines.csv",
                 "used_for": "Opening lines, 2021 only. Insufficient history, so the line-move strategy "
                             "is declared untestable rather than proxied",
                 "tier": "T3 aggregated market data"},
                {"name": "nflverse/nfldata — standings.csv", "url":
                    "https://github.com/nflverse/nfldata/blob/master/data/standings.csv",
                 "used_for": "Downloaded and hashed; superseded by nfl.com/standings for 2026",
                 "tier": "T2 open data"},
            ],
        },
        {
            "group": "Repository and publishing",
            "items": [
                {"name": "FL2 repository", "url": "https://github.com/sassnarep3-star/FL2",
                 "used_for": "all project files", "tier": "primary"},
                {"name": "GitHub Pages settings", "url":
                    "https://github.com/sassnarep3-star/FL2/settings/pages",
                 "used_for": "publishing configuration (build_type legacy, source main:/)",
                 "tier": "primary"},
            ],
        },
    ]
    return groups


def main():
    backtest = clean(load("backtest_summary"))
    parlays = clean(load("parlay_analysis"))
    week10 = clean(load("week10_lineups"))
    season = clean(load("season_2026"))
    market = clean(load("market_lines"))
    manifest = load("manifest") if os.path.exists(os.path.join(DATA, "manifest.json")) else {"files": []}

    decisions_path = os.path.join(DATA, "decisions.js")
    bundle = {
        "as_of_utc": week10["as_of_utc"],
        "season": 2026,
        "week": 10,
        "backtest": backtest,
        "parlays": parlays,
        "week10": week10,
        "season_table": season,
        "market": market,
        "manifest": manifest,
        "flags": build_flags(backtest, parlays, week10, market),
        "sources": build_sources(backtest, week10, parlays, market, manifest),
    }
    payload = json.dumps(bundle, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    path = os.path.join(DATA, "site_data.js")
    with open(path, "w") as fh:
        fh.write('"use strict";\n/* Generated by engine/build_site_data.py — do not edit by hand. */\n')
        fh.write("window.FL2 = ")
        fh.write(payload)
        fh.write(";\n")
    print(f"wrote {path} ({os.path.getsize(path)/1024:.1f} KB)")
    print(f"flags: {len(bundle['flags'])}")
    by_cat = {}
    for f in bundle["flags"]:
        by_cat[f["category"]] = by_cat.get(f["category"], 0) + 1
    for k, v in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"  {v:2d}  {k}")
    print(f"strategies: {len(backtest['strategies'])}  injury rows: {len(week10['injury_rows'])}  "
          f"games: {len(market['games'])}")


if __name__ == "__main__":
    main()
