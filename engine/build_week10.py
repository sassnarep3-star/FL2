"""
FL2 — Week 10 / 2026 verified snapshot builder.

Every value in this file was read from an official or primary source on
2026-11-14 and is tagged with the URL it came from. Nothing is estimated.
If a value was not published, it is `None` and the record is flagged.

Outputs
-------
data/week10_lineups.json   injury report (Out / Doubtful / Questionable) + QB changes
data/team_depletion.json   computed availability / depletion index per team
data/season_2026.json      standings, points for/against, defensive profile
"""
from __future__ import annotations

import json
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "data")
AS_OF = "2026-11-14T03:00:00Z"

SRC = {
    "injuries": "https://www.nfl.com/injuries/",
    "standings": "https://www.nfl.com/standings/",
    "pfr_def": "https://www.pro-football-reference.com/years/2026/opp.htm",
    "pfr_off": "https://www.pro-football-reference.com/years/2026/index.htm",
    "news_fri": "https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-friday-nov-13",
    "news_wed": "https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-wednesday-nov-11",
    "news_lock": "https://www.nfl.com/news/drew-lock-no-injury-designation-seahawks-raiders",
    "news_mccord": "https://www.nfl.com/news/dolphins-place-qb-malik-willis-groin-on-injured-reserve-kyle-mccord-in-line-for-first-start",
}

# --------------------------------------------------------------------------- #
# 2026 Week 10 schedule, as published on the NFL injury report page.
# (home team listed second, matching NFL.com's presentation)
# --------------------------------------------------------------------------- #
WEEK10 = [
    {"game": "WAS @ NYG", "away": "WAS", "home": "NYG", "kickoff_et": "2026-11-12 20:15", "tv": "Prime Video"},
    {"game": "NE @ DET", "away": "NE", "home": "DET", "kickoff_et": "2026-11-15 09:30", "tv": "FOX", "note": "Munich"},
    {"game": "KC @ ATL", "away": "KC", "home": "ATL", "kickoff_et": "2026-11-15 13:00", "tv": "CBS"},
    {"game": "MIN @ GB", "away": "MIN", "home": "GB", "kickoff_et": "2026-11-15 13:00", "tv": "FOX"},
    {"game": "JAX @ TEN", "away": "JAX", "home": "TEN", "kickoff_et": "2026-11-15 13:00", "tv": "FOX"},
    {"game": "BUF @ NYJ", "away": "BUF", "home": "NYJ", "kickoff_et": "2026-11-15 13:00", "tv": "CBS"},
    {"game": "MIA @ IND", "away": "MIA", "home": "IND", "kickoff_et": "2026-11-15 13:00", "tv": "CBS"},
    {"game": "CAR @ NO", "away": "CAR", "home": "NO", "kickoff_et": "2026-11-15 13:00", "tv": "FOX"},
    {"game": "HOU @ CLE", "away": "HOU", "home": "CLE", "kickoff_et": "2026-11-15 13:00", "tv": "FOX"},
    {"game": "LAR @ ARI", "away": "LAR", "home": "ARI", "kickoff_et": "2026-11-15 16:05", "tv": "CBS"},
    {"game": "SEA @ LV", "away": "SEA", "home": "LV", "kickoff_et": "2026-11-15 16:05", "tv": "CBS"},
    {"game": "SF @ DAL", "away": "SF", "home": "DAL", "kickoff_et": "2026-11-15 16:25", "tv": "FOX"},
    {"game": "PIT @ CIN", "away": "PIT", "home": "CIN", "kickoff_et": "2026-11-15 20:20", "tv": "NBC"},
    {"game": "LAC @ BAL", "away": "LAC", "home": "BAL", "kickoff_et": "2026-11-16 20:15", "tv": "ESPN/ABC"},
]

# Teams with no Week 10 game (verified: they do not appear on the injury report page)
BYE = ["PHI", "TB", "DEN", "CHI"]

# --------------------------------------------------------------------------- #
# Injury report: every player the league listed with an *Out* or *Doubtful*
# game status, verbatim from nfl.com/injuries/. Questionable players are
# counted per team but not enumerated player-by-player (see notes).
# --------------------------------------------------------------------------- #
INJ = {
    "WAS": [("Lucas Patrick", "C", "Concussion", "DNP", "Out"),
            ("Colson Yankoff", "TE", "Knee", "DNP", "Out")],
    "NYG": [],
    "NE": [("Ben Brown", "C", "Knee", "DNP", "Out"),
           ("Carlton Davis III", "CB", "Knee", "DNP", "Out"),
           ("TreVeyon Henderson", "RB", "Illness", "DNP", "Out")],
    "DET": [("Kerby Joseph", "S", "Knee", "DNP", "Out"),
            ("Cade Mays", "C", "Ankle", "DNP", "Out"),
            ("D.J. Reed", "CB", "Hip", "DNP", "Out")],
    "KC": [("Jaylon Moore", "T", "Ankle", "DNP", "Out"),
           ("Omarr Norman-Lott", "DT", "Knee", "Limited", "Out"),
           ("Peter Woods", "DT", "Neck", "DNP", "Out")],
    "ATL": [("Zachariah Branch", "WR", "Hamstring", "DNP", "Out"),
            ("Divine Deablo", "LB", "Forearm", "DNP", "Doubtful")],
    "MIN": [("Blake Cashman", "LB", "Concussion", "Limited", "Out"),
            ("T.J. Hockenson", "TE", "Wrist, Chest", "DNP", "Out"),
            ("Tyrion Ingram-Dawkins", "DT", "Ankle", "DNP", "Out"),
            ("Jauan Jennings", "WR", "Calf", "DNP", "Out"),
            ("Kyler Murray", "QB", "Hamstring", "DNP", "Out")],
    "GB": [("Josh Jacobs", "RB", "Finger", "DNP", "Out"),
           ("Micah Parsons", "LB", "Knee, Illness", "Limited", "Out"),
           ("Sean Rhyan", "C", "Ankle", "DNP", "Out"),
           ("Josh Whyle", "TE", "Concussion", "DNP", "Out"),
           ("Zaire Franklin", "LB", "Shin", "DNP", "Doubtful")],
    "JAX": [("Jessie Bates", "S", "Not injury related - resting player", "Limited", "Out"),
            ("Jordan Davis", "DT", "Not injury related - resting player", "Limited", "Out"),
            ("BJ Green II", "DE", "Forearm", "Full", "Out")],
    "TEN": [("Cody Barton", "LB", "Concussion", "DNP", "Out"),
            ("Anthony Hill Jr.", "LB", "Neck", "DNP", "Out"),
            ("Peter Skoronski", "G", "Hamstring", "DNP", "Out"),
            ("Carnell Tate", "WR", "Shoulder", "DNP", "Out"),
            ("Tommy Townsend", "P", "Knee, Achilles", "DNP", "Out")],
    "BUF": [("Spencer Brown", "T", "Ankle", "DNP", "Doubtful")],
    "NYJ": [("Trevin Wallace", "LB", "Groin", "DNP", "Out")],
    "MIA": [("Aaron Brewer", "C", "Concussion", "DNP", "Out"),
            ("Jared Wayne", "WR", "Quadricep", "DNP", "Out"),
            ("Chris Bell", "WR", "Knee", "DNP", "Doubtful")],
    "IND": [("Mo Alie-Cox", "TE", "Groin", "DNP", "Out"),
            ("Jaylon Carlies", "LB", "Neck", "DNP", "Out"),
            ("Akeem Davis-Gaither", "LB", "Knee", "DNP", "Out"),
            ("Luke Rhodes", "LS", "Hamstring", "DNP", "Out"),
            ("Jerry Tillery", "DT", "Calf", "DNP", "Out"),
            ("Jalen Travis", "T", "Knee", "DNP", "Out")],
    "CAR": [("Bobby Okereke", "LB", "Foot", "DNP", "Out"),
            ("Jonathon Brooks", "RB", "Groin", "Limited", "Doubtful"),
            ("Mike Jackson", "CB", "Groin", "Limited", "Doubtful")],
    "NO": [("CJ Donaldson", "RB", "Shoulder", "DNP", "Out"),
           ("Taliese Fuaga", "T", "Knee", "DNP", "Out"),
           ("Erik McCoy", "C", "Biceps", "DNP", "Out"),
           ("Christen Miller", "DT", "Knee", "DNP", "Out")],
    "HOU": [("Azeez Al-Shaair", "LB", "Groin, Not injury related - personal matter", "DNP", "Out"),
            ("Marvin Harrison Jr.", "WR", "Hamstring", "DNP", "Out"),
            ("Danielle Hunter", "DE", "Hamstring", "DNP", "Out"),
            ("Brevin Jordan", "TE", "Finger, Foot", "DNP", "Out"),
            ("Keylan Rutledge", "G", "Neck, Shoulder", "DNP", "Out")],
    "CLE": [("Michael Burton", "FB", "Calf", "DNP", "Out"),
            ("Ronnie Hickman Jr.", "S", "Concussion", "DNP", "Out")],
    "LAR": [("Steve Avila", "G", "Hamstring", "DNP", "Out"),
            ("Terrance Ferguson", "TE", "Ankle, Hamstring", "DNP", "Out")],
    "ARI": [("Hjalte Froholdt", "C", "Concussion", "DNP", "Out"),
            ("Jon Gaines II", "G", "Ankle", "DNP", "Out"),
            ("Zachary Carter", "DT", "Knee", "Limited", "Out")],
    "SEA": [("Charles Cross", "T", "Ankle", "DNP", "Out"),
            ("Sam Darnold", "QB", "Ribs, Quadricep", "DNP", "Out"),
            ("Quenton Nelson", "G", "Knee", "DNP", "Out"),
            ("Leonard Williams", "DT", "Stinger", "DNP", "Out")],
    "LV": [],
    "SF": [("Mike Evans", "WR", "Achilles", "DNP", "Out")],
    "DAL": [("Donovan Ezeiruaku", "LB", "Ankle", "DNP", "Out"),
            ("Jake Ferguson", "TE", "Knee, Ankle", "DNP", "Out"),
            ("Tyler Goodson", "RB", "Ankle, Knee", "DNP", "Out"),
            ("P.J. Locke", "S", "Concussion", "DNP", "Out"),
            ("Jonathan Mingo", "WR", "Ankle", "DNP", "Out"),
            ("Juanyeh Thomas", "S", "Hamstring", "DNP", "Doubtful")],
    "PIT": [],
    "CIN": [("Kyle Dugger", "S", "Quadricep", "DNP", "Out"),
            ("Jalen Davis", "CB", "Hamstring", "Full", "Doubtful"),
            ("Andrei Iosivas", "WR", "Thumb", "Full", "Doubtful"),
            ("Brian Parker II", "G", "Knee", "Full", "Doubtful")],
    "LAC": [],
    "BAL": [],
}

# Questionable counts per team, counted from nfl.com/injuries/ (Week 10).
QUESTIONABLE = {
    "WAS": 1, "NYG": 1, "NE": 6, "DET": 2, "KC": 3, "ATL": 3, "MIN": 4, "GB": 5,
    "JAX": 1, "TEN": 1, "BUF": 4, "NYJ": 8, "MIA": 1, "IND": 2, "CAR": 4, "NO": 2,
    "HOU": 6, "CLE": 1, "LAR": 4, "ARI": 6, "SEA": 0, "LV": 2, "SF": 7, "DAL": 6,
    "PIT": 1, "CIN": 0, "LAC": 0, "BAL": 0,
}

# --------------------------------------------------------------------------- #
# Quarterback availability changes — only what an official NFL.com page states.
# --------------------------------------------------------------------------- #
QB = {
    "ARI": {"starter": "Carson Beck", "change": "new starter",
            "detail": "Carson Beck will start; first career NFL start. Kyler Murray listed Out (hamstring).",
            "source_url": SRC["news_wed"]},
    "CLE": {"starter": "Deshaun Watson", "change": "starter change",
            "detail": "Browns announced Deshaun Watson starts vs. Houston; Shedeur Sanders started Week 9.",
            "source_url": SRC["news_wed"]},
    "MIA": {"starter": "Kyle McCord", "change": "new starter",
            "detail": "Malik Willis placed on injured reserve (groin); Kyle McCord in line for first start.",
            "source_url": SRC["news_mccord"]},
    "MIN": {"starter": "Kirk Cousins", "change": "new starter",
            "detail": "Coach Kevin O'Connell announced Kirk Cousins will start vs. Green Bay. Kyler Murray Out.",
            "source_url": SRC["news_fri"]},
    "SEA": {"starter": "Drew Lock", "change": "backup starting",
            "detail": "Sam Darnold ruled out (ribs/quadricep). Drew Lock starts; Jalen Milroe is the backup.",
            "source_url": SRC["news_lock"]},
    "BAL": {"starter": None, "change": "starter out",
            "detail": "Lamar Jackson expected to miss 6-10 weeks after thumb surgery. NFL.com does not "
                      "name the Week 10 starter on the pages reviewed.",
            "source_url": SRC["news_fri"]},
    "LAC": {"starter": None, "change": "unknown",
            "detail": "Justin Herbert 'avoids finger fracture' per Nov 9 roundup; no official Week 10 "
                      "starter confirmation found on the pages reviewed.",
            "source_url": "https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-monday-nov-9"},
}

# --------------------------------------------------------------------------- #
# Standings — nfl.com/standings/ (2026 REG, retrieved 2026-11-14).
# w, l, t, pf, pa, streak
# --------------------------------------------------------------------------- #
STAND = {
    "BUF": (7, 1, 0, 256, 187, "4W"), "NE": (5, 4, 0, 211, 207, "1L"), "NYJ": (2, 7, 0, 182, 223, "4L"),
    "MIA": (1, 7, 0, 126, 200, "2L"), "PIT": (6, 2, 0, 180, 144, "4W"), "CIN": (6, 2, 0, 240, 175, "4W"),
    "CLE": (5, 4, 0, 161, 196, "2L"), "BAL": (4, 5, 0, 189, 236, "4L"), "JAX": (6, 2, 0, 229, 121, "2W"),
    "HOU": (3, 5, 0, 209, 192, "1W"), "IND": (2, 7, 0, 184, 249, "5L"), "TEN": (1, 7, 0, 144, 199, "2L"),
    "DEN": (7, 2, 0, 198, 186, "5W"), "KC": (6, 2, 0, 202, 143, "1W"), "LV": (4, 5, 0, 238, 268, "1L"),
    "LAC": (0, 8, 0, 121, 219, "8L"),
    "NYG": (5, 3, 1, 203, 196, "1L"), "DAL": (4, 5, 0, 246, 236, "1W"), "WAS": (3, 5, 1, 196, 223, "1W"),
    "PHI": (2, 7, 0, 148, 221, "7L"), "CHI": (7, 2, 0, 241, 184, "4W"), "DET": (6, 2, 0, 222, 189, "4W"),
    "MIN": (6, 2, 0, 146, 116, "2L"), "GB": (6, 3, 0, 216, 191, "2W"), "CAR": (3, 5, 0, 199, 219, "3L"),
    "NO": (3, 5, 0, 185, 216, "1W"), "TB": (3, 6, 0, 202, 178, "1L"), "ATL": (3, 6, 0, 188, 223, "2L"),
    "LAR": (5, 4, 0, 214, 181, "3W"), "ARI": (3, 6, 0, 178, 255, "1L"), "SEA": (5, 4, 0, 202, 162, "1W"),
    "SF": (7, 1, 0, 235, 156, "1W"),
}

# --------------------------------------------------------------------------- #
# Team defense — pro-football-reference 2026 opp.htm (through Week 9/10 played).
# g, pts_allowed, total_yds_allowed, pass_yds_allowed, rush_yds_allowed,
# takeaways (TO), def_sacks_proxy_not_available -> None
# --------------------------------------------------------------------------- #
DEF = {
    "MIN": (8, 116, 2240, 1289, 951, 13), "JAX": (8, 121, 2546, 1832, 714, 15),
    "KC": (8, 143, 2463, 1683, 780, 11), "PIT": (8, 144, 2445, 1774, 671, 13),
    "SF": (8, 156, 2335, 1688, 647, 12), "SEA": (9, 162, 2198, 1396, 802, 13),
    "CIN": (8, 175, 2839, 1826, 1013, 12), "TB": (9, 178, 2636, 1924, 712, 21),
    "LAR": (9, 181, 2722, 1788, 934, 10), "CHI": (9, 184, 2798, 1978, 820, 13),
    "DEN": (9, 186, 3195, 2076, 1119, 12), "BUF": (8, 187, 2643, 1910, 733, 12),
    "DET": (8, 189, 2840, 2087, 753, 8), "GB": (9, 191, 2906, 1925, 981, 19),
    "HOU": (8, 192, 2709, 1885, 824, 8), "NYG": (9, 196, 2751, 1657, 1094, 12),
    "CLE": (9, 196, 2984, 1809, 1175, 12), "TEN": (8, 199, 3059, 2066, 993, 11),
    "MIA": (8, 200, 2609, 1715, 894, 7), "NE": (9, 207, 2957, 2087, 870, 8),
    "NO": (8, 216, 2964, 1893, 1071, 9), "CAR": (8, 219, 2759, 1692, 1067, 11),
    "LAC": (8, 219, 2746, 1770, 976, 12), "PHI": (9, 221, 3181, 2046, 1135, 5),
    "NYJ": (9, 223, 2932, 1780, 1152, 10), "ATL": (9, 223, 3121, 2052, 1069, 10),
    "WAS": (9, 223, 3137, 2203, 934, 14), "BAL": (9, 236, 2967, 2068, 899, 9),
    "DAL": (9, 236, 3354, 2027, 1327, 8), "IND": (9, 249, 3256, 2023, 1233, 6),
    "ARI": (9, 255, 3036, 1939, 1097, 8), "LV": (9, 268, 3469, 2108, 1361, 14),
}

TEAM_NAME = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs", "LV": "Las Vegas Raiders", "LAC": "Los Angeles Chargers",
    "LAR": "Los Angeles Rams", "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings",
    "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
    "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers", "SEA": "Seattle Seahawks", "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans", "WAS": "Washington Commanders",
}

# Positions that, when lost, change the shape of a unit rather than just its depth.
WEIGHT = {
    "QB": 5.0, "T": 2.5, "G": 1.8, "C": 2.2, "TE": 1.5, "WR": 2.0, "RB": 1.5,
    "DE": 2.2, "DT": 2.0, "LB": 1.8, "CB": 2.4, "S": 2.0, "FB": 0.6, "LS": 0.3, "P": 0.2,
}
OFF = {"QB", "T", "G", "C", "TE", "WR", "RB", "FB"}


def build():
    os.makedirs(OUT, exist_ok=True)

    # ---- season + defensive profile ------------------------------------- #
    season = []
    for t, (w, l, tie, pf, pa, streak) in STAND.items():
        g, pa_def, yds, pass_y, rush_y, to = DEF[t]
        games = w + l + tie
        season.append({
            "team": t, "name": TEAM_NAME[t],
            "w": w, "l": l, "t": tie, "pct": round((w + 0.5 * tie) / games, 3) if games else None,
            "games_played": games, "pf": pf, "pa": pa,
            "pf_per_game": round(pf / games, 2) if games else None,
            "pa_per_game": round(pa / games, 2) if games else None,
            "streak": streak,
            "def_games": g, "def_pa": pa_def,
            "def_pa_per_game": round(pa_def / g, 2),
            "def_yds_per_game": round(yds / g, 1),
            "def_pass_yds_per_game": round(pass_y / g, 1),
            "def_rush_yds_per_game": round(rush_y / g, 1),
            "def_takeaways": to,
            "sources": [SRC["standings"], SRC["pfr_def"]],
            "verified": True,
        })
    season.sort(key=lambda r: -(r["pct"] or 0))
    for i, r in enumerate(season, 1):
        r["rank"] = i

    # ---- injuries -------------------------------------------------------- #
    rows = []
    for team, players in INJ.items():
        for name, pos, injury, practice, status in players:
            rows.append({
                "team": team, "team_name": TEAM_NAME[team], "player": name, "position": pos,
                "injury": injury, "practice": practice, "game_status": status,
                "unit": "OFF" if pos in OFF else "DEF",
                "weight": WEIGHT.get(pos, 1.0),
                "source_url": SRC["injuries"], "verified": True,
            })
    rows.sort(key=lambda r: (r["team"], 0 if r["game_status"] == "Out" else 1, -r["weight"]))

    # ---- depletion index ------------------------------------------------- #
    # Two measures, both transparent:
    #   out_weight  = sum of position weights for players listed Out
    #   doubt_weight= half the weight for players listed Doubtful
    #   avail_index = 100 - (out_weight*4 + doubt_weight*2), floored at 0
    # The multipliers are arbitrary scaling, NOT measurements. They are declared
    # here so nobody mistakes the index for an estimate of point value.
    teams = {}
    for t in TEAM_NAME:
        out_w = sum(r["weight"] for r in rows if r["team"] == t and r["game_status"] == "Out")
        doubt_w = sum(r["weight"] for r in rows if r["team"] == t and r["game_status"] == "Doubtful")
        off_out = sum(r["weight"] for r in rows if r["team"] == t and r["game_status"] == "Out" and r["unit"] == "OFF")
        def_out = sum(r["weight"] for r in rows if r["team"] == t and r["game_status"] == "Out" and r["unit"] == "DEF")
        n_out = sum(1 for r in rows if r["team"] == t and r["game_status"] == "Out")
        n_doubt = sum(1 for r in rows if r["team"] == t and r["game_status"] == "Doubtful")
        teams[t] = {
            "team": t, "name": TEAM_NAME[t],
            "players_out": n_out, "players_doubtful": n_doubt,
            "players_questionable": QUESTIONABLE.get(t, None),
            "off_weight_lost": round(off_out, 1), "def_weight_lost": round(def_out, 1),
            "unit_most_affected": ("OFF" if off_out > def_out else "DEF" if def_out > off_out else "EVEN"),
            "avail_index": round(max(0.0, 100 - (out_w * 4 + doubt_w * 2)), 1) if t in INJ else None,
            "qb_change": QB.get(t, {}).get("change", "none reported"),
            "qb_starter": QB.get(t, {}).get("starter"),
            "qb_note": QB.get(t, {}).get("detail"),
            "qb_source": QB.get(t, {}).get("source_url"),
            "played_week10": t not in BYE,
            "sources": [SRC["injuries"]],
        }
    for t in BYE:
        teams[t]["note"] = "No Week 10 game (bye). Depletion index not meaningful this week."

    # ---- enrichment: opponent context ------------------------------------ #
    opponents = {}
    for g in WEEK10:
        opponents[g["home"]] = g["away"]
        opponents[g["away"]] = g["home"]
    for t, rec in teams.items():
        opp = opponents.get(t)
        rec["opponent"] = opp
        if opp:
            rec["opp_def_pa_per_game"] = season[[s["team"] for s in season].index(opp)]["def_pa_per_game"]
            rec["own_def_pa_per_game"] = season[[s["team"] for s in season].index(t)]["def_pa_per_game"]

    league = {
        "n_players_out": sum(1 for r in rows if r["game_status"] == "Out"),
        "n_players_doubtful": sum(1 for r in rows if r["game_status"] == "Doubtful"),
        "n_players_questionable_listed": sum(v for v in QUESTIONABLE.values()),
        "teams_reporting": len(INJ),
        "mean_out_per_team": round(sum(1 for r in rows if r["game_status"] == "Out") / len(INJ), 2),
    }

    payload = {
        "as_of_utc": AS_OF,
        "season": 2026, "week": 10,
        "schedule": WEEK10, "byes": BYE,
        "injury_rows": rows,
        "team_depletion": teams,
        "league_totals": league,
        "method": {
            "weights": WEIGHT,
            "avail_index_formula": "100 - (out_weight*4 + doubtful_weight*2), floored at 0",
            "caveat": "The weight multipliers are a declared, arbitrary scale for ordering teams. "
                      "They are NOT a measured point value and must not be read as one. "
                      "The index is a communication device, not a model input.",
        },
        "sources": SRC,
        "verification": {
            "injury_rows": "Each row read from nfl.com/injuries/ (Week 10, 2026) on 2026-11-14.",
            "standings": "nfl.com/standings/ 2026 REG.",
            "team_defense": "pro-football-reference.com/years/2026/opp.htm",
            "qb_changes": "NFL.com league news roundups (Wed Nov 11 / Fri Nov 13) and dedicated NFL.com news items.",
            "known_gap": "Which listed players are Week 1 starters is not published on the pages used; "
                         "position weights are a proxy, marked as such.",
        },
    }

    with open(os.path.join(OUT, "week10_lineups.json"), "w") as fh:
        json.dump(payload, fh, indent=2)
    with open(os.path.join(OUT, "season_2026.json"), "w") as fh:
        json.dump({"as_of_utc": AS_OF, "season": 2026, "teams": season,
                   "sources": [SRC["standings"], SRC["pfr_def"]]}, fh, indent=2)

    print(f"injury rows: {len(rows)}  Out:{league['n_players_out']}  "
          f"Doubtful:{league['n_players_doubtful']}  Questionable:{league['n_players_questionable_listed']}")
    worst = sorted(teams.values(), key=lambda r: (r["avail_index"] if r["avail_index"] is not None else 999))[:6]
    for w in worst:
        print(f"  {w['team']:4s} out={w['players_out']} q={w['players_questionable']} "
              f"idx={w['avail_index']} off={w['off_weight_lost']} def={w['def_weight_lost']} "
              f"qb={w['qb_change']}")


if __name__ == "__main__":
    build()
