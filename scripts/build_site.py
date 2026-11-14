#!/usr/bin/env python3
"""Build the static GitHub Pages site in docs/ from the verified data in data/.

Steps
1. Parse CSV source files (pipe-delimited) into JSON.
2. Compute descriptive unit-exposure counts (no starter/backup inference).
3. Copy qualitative JSON (sources, flags, questions, suggestions, strategies).
4. Validate: row counts, official-URL rules, source-ID references, internal links.
Exit code is non-zero if any validation fails, so a broken site is never published.
"""
import csv
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"
OUT = DOCS / "data"

EXPECTED_INJURY_ROWS = 345
EXPECTED_TEAMS = 28
EXPECTED_GAMES = 14
EXPECTED_NEWS = 21
REPORT_URL = "https://www.nfl.com/injuries/"

UNIT_OF = {
    "QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE",
    "T": "OL", "G": "OL", "C": "OL",
    "DE": "DL", "DT": "DL", "LB": "LB",
    "CB": "DB", "S": "DB",
    "K": "ST", "P": "ST", "LS": "ST",
}
UNITS = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB", "ST"]

errors = []


def fail(msg):
    errors.append(msg)


def read_psv(name):
    with open(DATA / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="|"))


def load_json(name):
    with open(DATA / name, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # 1. Games
    games = read_psv("games_2026_week10.csv")
    game_by_team = {}
    for g in games:
        label = f"{g['away_team']} at {g['home_team']}"
        for t in (g["away_team"], g["home_team"]):
            if t in game_by_team:
                fail(f"team {t} appears in more than one game")
            game_by_team[t] = {"game_id": g["game_id"], "label": label}
        if not g["nfl_game_url"].startswith("https://www.nfl.com/games/"):
            fail(f"game {g['game_id']} has non-NFL.com URL")
    if len(games) != EXPECTED_GAMES:
        fail(f"expected {EXPECTED_GAMES} games, found {len(games)}")

    # 2. Injuries
    injuries = read_psv("injuries_2026_week10.csv")
    if len(injuries) != EXPECTED_INJURY_ROWS:
        fail(f"expected {EXPECTED_INJURY_ROWS} injury rows, found {len(injuries)}")
    teams = Counter(r["team"] for r in injuries)
    if len(teams) != EXPECTED_TEAMS:
        fail(f"expected {EXPECTED_TEAMS} teams with injury rows, found {len(teams)}")
    for t in teams:
        if t not in game_by_team:
            fail(f"injury team {t} is not in any scheduled game")

    slug_re = re.compile(r"^[a-z0-9-]+$")
    rows_out = []
    for r in injuries:
        slug = r["nfl_profile_slug"]
        if not slug_re.match(slug):
            fail(f"bad slug for {r['player']}: {slug}")
        pos = r["position"]
        if pos not in UNIT_OF:
            fail(f"unmapped position {pos} for {r['player']}")
        not_injury = "Not injury related" in r["injury"]
        g = game_by_team.get(r["team"], {})
        rows_out.append({
            "team": r["team"],
            "game": g.get("label", ""),
            "game_id": g.get("game_id", ""),
            "player": r["player"],
            "position": pos,
            "unit": UNIT_OF.get(pos, ""),
            "injury": r["injury"],
            "not_injury_related": not_injury,
            "practice_status": r["practice_status"],
            "game_status": r["game_status"],
            "final_game_flag": g.get("game_id") == "WAS-NYG-W10",
            "source_url": f"https://www.nfl.com/players/{slug}/",
            "report_url": REPORT_URL,
            "source_id": "S1",
            "verification": "Transcribed from NFL.com Week 10 report (fetched 2026-11-14)",
        })

    # 3. Unit exposure (descriptive counts only)
    exposure = defaultdict(lambda: {u: Counter() for u in UNITS})
    for r in rows_out:
        c = exposure[r["team"]][r["unit"]]
        c["listed"] += 1
        if r["not_injury_related"]:
            c["not_injury_related"] += 1
            continue
        if r["game_status"] == "Out":
            c["out"] += 1
        elif r["game_status"] == "Doubtful":
            c["doubtful"] += 1
        elif r["game_status"] == "Questionable":
            c["questionable"] += 1
        if r["practice_status"].startswith("Did Not"):
            c["dnp"] += 1
    unit_rows = []
    for team in sorted(exposure):
        for unit in UNITS:
            c = exposure[team][unit]
            if c["listed"] == 0:
                continue
            ob = c["out"] + c["doubtful"]
            unit_rows.append({
                "team": team,
                "game": game_by_team[team]["label"],
                "unit": unit,
                "listed": c["listed"],
                "out": c["out"],
                "doubtful": c["doubtful"],
                "questionable": c["questionable"],
                "dnp": c["dnp"],
                "not_injury_related": c["not_injury_related"],
                "flag": (
                    "Review: QB Out/Doubtful" if unit == "QB" and ob > 0 else
                    "Review: 2+ Out/Doubtful in unit" if ob >= 2 else ""
                ),
                "note": "Counts from NFL.com report only. Starter/backup status NOT verified.",
                "source_url": REPORT_URL,
                "source_id": "S1",
            })

    # 4. News
    news = read_psv("news_2026_week10.csv")
    if len(news) != EXPECTED_NEWS:
        fail(f"expected {EXPECTED_NEWS} news rows, found {len(news)}")
    news_out = []
    for n in news:
        if not n["nfl_url"].startswith("https://www.nfl.com/"):
            fail(f"news URL not on nfl.com: {n['nfl_url']}")
        news_out.append({
            "date_stated": n["date_stated_in_title_or_url"],
            "headline": n["headline_as_listed"],
            "source_url": n["nfl_url"],
            "source_id": "S1",
            "listed_on": n["listed_on_page"],
        })

    games_out = []
    for g in games:
        games_out.append({
            "game_id": g["game_id"],
            "label": f"{g['away_team']} at {g['home_team']}",
            "away": g["away_team"],
            "home": g["home_team"],
            "date_et": g["date_et"],
            "time_et": g["time_et"],
            "network": g["network"],
            "status": g["status_per_nfl_com"],
            "source_url": g["nfl_game_url"],
            "source_id": "S2",
        })

    # 5. Write outputs
    def dump(name, obj):
        with open(OUT / name, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=1)
            fh.write("\n")

    dump("injuries.json", rows_out)
    dump("unit_exposure.json", unit_rows)
    dump("games.json", games_out)
    dump("news.json", news_out)
    for name in ("sources.json", "flags.json", "questions.json",
                 "suggestions.json", "strategies.json"):
        shutil.copyfile(DATA / name, OUT / name)

    sources = load_json("sources.json")["sources"]
    source_ids = {s["id"] for s in sources}
    for s in sources:
        if not s["url"].startswith("https://"):
            fail(f"source {s['id']} URL not https")
    for r in rows_out + news_out + games_out + unit_rows:
        if r.get("source_id") and r["source_id"] not in source_ids:
            fail(f"unknown source id {r['source_id']}")

    dump("meta.json", {
        "built_from": "data/*.csv and data/*.json",
        "data_fetched_on": "2026-11-14",
        "injury_rows": len(rows_out),
        "injury_teams": len(teams),
        "games": len(games_out),
        "news_items": len(news_out),
        "status_counts": {
            "Out": sum(1 for r in rows_out if r["game_status"] == "Out"),
            "Doubtful": sum(1 for r in rows_out if r["game_status"] == "Doubtful"),
            "Questionable": sum(1 for r in rows_out if r["game_status"] == "Questionable"),
        },
        "not_injury_related": sum(1 for r in rows_out if r["not_injury_related"]),
    })

    # 6. Internal link check for HTML pages
    html_files = sorted(DOCS.glob("*.html"))
    if not html_files:
        fail("no HTML pages found in docs/")
    href_re = re.compile(r'(?:href|src)="([^"#?]+)')
    for page in html_files:
        text = page.read_text(encoding="utf-8")
        for target in href_re.findall(text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (DOCS / target).exists():
                fail(f"{page.name} links to missing file {target}")

    # 7. JSON parse check for every data file in docs/data
    for jf in OUT.glob("*.json"):
        try:
            json.loads(jf.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(f"{jf.name} is not valid JSON: {exc}")

    if errors:
        print("BUILD FAILED:")
        for e in errors:
            print(" -", e)
        return 1
    print("Build OK")
    print(json.dumps(json.loads((OUT / "meta.json").read_text()), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
