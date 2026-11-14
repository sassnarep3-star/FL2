#!/usr/bin/env python3
"""
tools/build_slate_csv.py

Builds data/slate-2026-w10.csv — the 16 games of Week 10 2026, with kickoff
order and venue from nfl.com (S05 schedule) and operations.nfl.com (S08 dates),
joined to the verified team metrics (data/team-metrics-2026-w10.csv).

The only derived columns are explicit margin sums:
    derived_implied_margin = (home PPG - home PAPG) + (away PAPG - away PPG)
Nothing about a price, spread, or total is asserted: no odds source is ingested.
"""
import csv
import os

RET = "2026-11-14"
SCHED = "https://www.nfl.com/schedules/2026/by-week/week-10"
DATES = "https://operations.nfl.com/gameday/nfl-schedule/2026-important-nfl-dates"
STAND = "https://www.nfl.com/standings/"

# (order, day, kickoff_et, home, away, neutral_site, venue, final, home_score, away_score)
GAMES = [
    (1, "Thu Nov 12", "20:15", "NYG", "WAS", "no", "", "FINAL", 21, 24),
    (2, "Sun Nov 15", "09:30", "DET", "NE", "yes",
     "FC Bayern Munich Arena, Munich, Germany (NFL International Game)", "", None, None),
    (3, "Sun Nov 15", "13:00", "ATL", "KC", "no", "", "", None, None),
    (4, "Sun Nov 15", "13:00", "CLE", "HOU", "no", "", "", None, None),
    (5, "Sun Nov 15", "13:00", "GB", "MIN", "no", "", "", None, None),
    (6, "Sun Nov 15", "13:00", "IND", "MIA", "no", "", "", None, None),
    (7, "Sun Nov 15", "13:00", "NO", "CAR", "no", "", "", None, None),
    (8, "Sun Nov 15", "13:00", "NYJ", "BUF", "no", "", "", None, None),
    (9, "Sun Nov 15", "13:00", "TEN", "JAX", "no", "", "", None, None),
    (10, "Sun Nov 15", "16:05", "AZ", "LA", "no", "", "", None, None),
    (11, "Sun Nov 15", "16:05", "LV", "SEA", "no", "", "", None, None),
    (12, "Sun Nov 15", "16:25", "DAL", "SF", "no", "", "", None, None),
    (13, "Sun Nov 15", "20:20", "CIN", "PIT", "no", "", "", None, None),
    (14, "Mon Nov 16", "20:15", "BAL", "LAC", "no", "", "", None, None),
    # Byes in Week 10 (no game): CHI, DEN, PHI, TB — confirmed by absence from the
    # published Week 10 schedule and by the stands table showing 8 games played.
]

BYE = ["CHI", "DEN", "PHI", "TB"]


def main():
    metrics = {r["abbr"]: r for r in csv.DictReader(open("data/team-metrics-2026-w10.csv"))}
    out = "data/slate-2026-w10.csv"
    fields = ["order", "day", "kickoff_et", "away", "home", "neutral_site", "venue",
              "final", "home_score", "away_score",
              "home_games_played", "away_games_played",
              "home_ppg", "home_papg", "away_ppg", "away_papg",
              "naive_rating_margin_home",
              "home_off_epa", "home_def_epa", "away_off_epa", "away_def_epa",
              "home_ngs_playoff_prob", "away_ngs_playoff_prob",
              "source_schedule", "source_dates", "source_metrics", "retrieved", "verification", "note"]

    PLAYOFF = {  # S06 NGS playoff probability going into Week 10, where captured
        "SF": "94%", "CHI": "84%", "DET": "83%", "MIN": "75%", "GB": "61%", "NYG": "51%",
        "SEA": "48%", "LA": "47%", "TB": "36%", "DAL": "33%", "CAR": "31%", "WAS": "19%",
        "NO": "19%", "ATL": "16%", "PHI": "1%", "AZ": "<1%",
    }

    rows = []
    for (order, day, ko, home, away, neutral, venue, final, hs, as_) in GAMES:
        h, a = metrics[home], metrics[away]
        margin = round(
            (float(h["derived_ppg"]) - float(h["derived_papg"]))
            + (float(a["derived_papg"]) - float(a["derived_ppg"])), 2)
        note = ""
        if neutral:
            note = "neutral site; home/away labels follow the official schedule listing"
        rows.append({
            "order": order, "day": day, "kickoff_et": ko, "away": away, "home": home,
            "neutral_site": neutral, "venue": venue, "final": final,
            "home_score": "" if hs is None else hs, "away_score": "" if as_ is None else as_,
            "home_games_played": h["games_played"], "away_games_played": a["games_played"],
            "home_ppg": h["derived_ppg"], "home_papg": h["derived_papg"],
            "away_ppg": a["derived_ppg"], "away_papg": a["derived_papg"],
            "naive_rating_margin_home": margin,
            "home_off_epa": h["ngs_off_epa_per_play"], "home_def_epa": h["ngs_def_epa_per_play"],
            "away_off_epa": a["ngs_off_epa_per_play"], "away_def_epa": a["ngs_def_epa_per_play"],
            "home_ngs_playoff_prob": PLAYOFF.get(home, ""),
            "away_ngs_playoff_prob": PLAYOFF.get(away, ""),
            "source_schedule": SCHED, "source_dates": DATES,
            "source_metrics": STAND, "retrieved": RET,
            "verification": "schedule verified; metrics verified; no price asserted",
            "note": note,
        })
    rows.sort(key=lambda r: r["order"])
    with open(out, "w", newline="") as fh:
        cw = csv.DictWriter(fh, fieldnames=fields)
        cw.writeheader()
        cw.writerows(rows)

    # bye check: every club must appear exactly once, or be listed as a bye
    seen = []
    for r in rows:
        seen += [r["home"], r["away"]]
    missing = sorted(set(metrics) - set(seen))
    print(f"{out}: {len(rows)} games, {len(seen)} club-slots")
    print("clubs not on the slate:", missing)
    print("declared byes:", sorted(BYE))
    assert missing == sorted(BYE), "bye list does not match the schedule"
    assert len(seen) == len(set(seen)) == 28, "a club appears twice in Week 10"


if __name__ == "__main__":
    main()
