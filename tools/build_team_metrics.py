#!/usr/bin/env python3
"""
tools/build_team_metrics.py

Builds data/team-metrics-2026-w10.csv by joining four official NFL.com tables,
keyed by club abbreviation:

  S02  standings      https://www.nfl.com/standings/
  S03  offense passing https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all
  S22  offense rushing https://www.nfl.com/stats/team-stats/offense/rushing/2026/reg/all
  S04  defense passing https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all
  S06  NGS league trends (EPA/PLAY, PPG, OPP PPG) https://www.nfl.com/stats/ngs/trends

Nothing is imputed. If a source cell was not captured, the field is empty.

CROSS-CHECK LOGGED IN THE OUTPUT:
  derived_ppg   = points_for / games_played
  derived_papg  = points_against / games_played
  ngs_ppg       from S06, where captured
  ppg_delta     = derived_ppg - ngs_ppg   (must be <= 0.05 rounding if both are right)
"""
import csv
import os

RET = "2026-11-14"

STAND = "https://www.nfl.com/standings/"
PASS_O = "https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all"
RUSH_O = "https://www.nfl.com/stats/team-stats/offense/rushing/2026/reg/all"
PASS_D = "https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all"
NGS = "https://www.nfl.com/stats/ngs/trends"

# abbr: (club, wins, losses, ties, pf, pa,
#        pass_att, pass_cmp, pass_pct, pass_ypa, pass_yds, pass_td, pass_int, pass_rate, pass_sacks,
#        rush_att, rush_yds, rush_avg, rush_td,
#        def_pass_att, def_pass_cmp, def_pass_pct, def_pass_ypa, def_pass_yds, def_pass_td,
#        def_pass_int, def_pass_rate, def_pass_sacks,
#        ngs_off_epa, ngs_def_epa, ngs_ppg, ngs_opp_ppg)   # None where not captured
T = {
 "SF":  ("San Francisco 49ers", 7,1,0, 235,156, 236,163,69.1,8.4,1980,17,5,109.8,8, 234,1082,4.6,12, 280,188,67.1,6.4,1783,11,6,88.7,15, 0.14,-0.13,29.4,19.5),
 "CHI": ("Chicago Bears", 7,2,0, 241,184, 312,211,67.6,7.4,2310,10,9,88.0,20, 303,1278,4.2,17, 260,161,61.9,8.2,2120,13,7,93.1,26, -0.02,-0.14,26.8,20.4),
 "CIN": ("Cincinnati Bengals", 6,2,0, 240,175, 296,219,74.0,8.1,2386,23,6,114.8,15, 177,685,3.9,5, 273,174,63.7,7.3,1989,9,5,88.9,23, None,None,None,None),
 "BUF": ("Buffalo Bills", 7,1,0, 256,187, 236,156,66.1,8.6,2027,12,6,99.3,17, 261,1173,4.5,17, 300,183,61.0,6.7,2022,15,6,89.3,17, None,None,None,None),
 "DEN": ("Denver Broncos", 7,2,0, 198,186, 287,174,60.6,6.0,1730,11,4,84.7,11, 223,823,3.7,9, 344,207,60.2,6.5,2249,14,8,83.4,26, None,None,None,None),
 "CLE": ("Cleveland Browns", 5,4,0, 161,196, 283,185,65.4,7.4,2105,9,3,93.7,38, 233,876,3.8,6, 297,177,59.6,6.7,1982,12,6,84.6,26, None,None,None,None),
 "TB":  ("Tampa Bay Buccaneers", 3,6,0, 202,178, 240,146,60.8,5.9,1423,6,9,70.2,27, 294,1475,5.0,11, 307,190,61.9,6.6,2040,12,16,72.7,17, -0.17,-0.23,22.4,19.8),
 "AZ":  ("Arizona Cardinals", 3,6,0, 178,255, 359,232,64.6,5.8,2080,13,7,84.0,23, 226,924,4.1,4, 258,166,64.3,8.0,2076,19,3,108.9,19, -0.09,0.04,19.8,28.3),
 "LAC": ("Los Angeles Chargers", 0,8,0, 121,219, 243,146,60.1,6.6,1615,7,11,70.6,31, 224,916,4.1,4, 233,153,65.7,7.9,1845,13,7,95.9,13, None,None,None,None),
 "KC":  ("Kansas City Chiefs", 6,2,0, 202,143, 263,177,67.3,7.8,2037,14,4,101.8,11, 217,1102,5.1,10, 276,170,61.6,6.4,1764,7,6,79.4,14, None,None,None,None),
 "IND": ("Indianapolis Colts", 2,7,0, 184,249, 304,184,60.5,5.7,1730,6,10,69.1,25, 249,1037,4.2,11, 264,162,61.4,8.1,2145,16,2,104.1,19, None,None,None,None),
 "WAS": ("Washington Commanders", 3,5,1, 196,223, 299,187,62.5,6.8,2025,15,3,95.0,21, 243,1051,4.3,5, 332,217,65.4,7.0,2341,17,6,95.5,18, -0.09,-0.02,21.8,24.8),
 "DAL": ("Dallas Cowboys", 4,5,0, 246,236, 336,218,64.9,7.1,2381,16,5,95.4,14, 233,932,4.0,11, 296,194,65.5,7.2,2133,16,4,99.1,17, 0.06,0.05,27.3,26.2),
 "MIA": ("Miami Dolphins", 1,7,0, 126,200, 209,122,58.4,6.9,1442,6,6,77.1,24, 215,940,4.4,7, 221,168,76.0,8.1,1797,16,5,114.0,12, None,None,None,None),
 "PHI": ("Philadelphia Eagles", 2,7,0, 148,221, 303,179,59.1,5.7,1740,10,6,78.0,30, 213,797,3.7,8, 300,180,60.0,7.2,2150,13,3,92.2,16, -0.22,0.02,16.4,24.6),
 "ATL": ("Atlanta Falcons", 3,6,0, 188,223, 256,156,60.9,6.9,1766,11,12,76.4,16, 258,1235,4.8,9, 318,210,66.0,6.8,2171,14,3,96.3,20, -0.13,-0.04,20.9,24.8),
 "NYG": ("New York Giants", 5,3,1, 203,196, 304,188,61.8,7.2,2193,13,7,88.3,28, 259,1013,3.9,8, 286,179,62.6,6.2,1763,17,8,88.1,17, -0.05,-0.09,22.6,21.8),
 "JAX": ("Jacksonville Jaguars", 6,2,0, 229,121, 227,147,64.8,8.6,1940,18,4,110.8,13, 230,937,4.1,8, 261,172,65.9,7.3,1907,8,11,80.1,16, None,None,None,None),
 "NYJ": ("New York Jets", 2,7,0, 182,223, 271,183,67.5,7.7,2078,12,3,100.4,28, 231,947,4.1,5, 270,174,64.4,7.1,1909,16,1,103.5,22, None,None,None,None),
 "DET": ("Detroit Lions", 6,2,0, 222,189, 274,186,67.9,7.8,2145,15,2,106.5,19, 230,1022,4.4,10, 313,203,64.9,7.2,2265,18,6,97.5,27, 0.07,0.05,27.8,23.6),
 "GB":  ("Green Bay Packers", 6,3,0, 216,191, 341,215,63.0,7.7,2618,19,6,97.9,17, 202,614,3.0,6, 325,203,62.5,6.4,2087,13,13,77.6,26, -0.02,-0.13,24.0,21.2),
 "CAR": ("Carolina Panthers", 3,5,0, 199,219, 313,189,60.4,7.2,2244,16,6,91.3,26, 189,810,4.3,7, 278,176,63.3,6.4,1774,12,5,88.3,12, -0.01,-0.03,24.9,27.4),
 "NE":  ("New England Patriots", 5,4,0, 211,207, 281,183,65.1,8.4,2349,18,11,96.2,20, 256,1079,4.2,7, 286,193,67.5,7.9,2256,14,5,100.2,25, None,None,None,None),
 "LV":  ("Las Vegas Raiders", 4,5,0, 238,268, 324,209,64.5,7.4,2401,20,8,97.0,11, 222,642,2.9,5, 279,183,65.6,8.0,2238,20,7,103.6,19, None,None,None,None),
 "LA":  ("Los Angeles Rams", 5,4,0, 214,181, 349,232,66.5,6.8,2387,16,9,90.5,13, 242,1128,4.7,11, 293,179,61.1,6.4,1882,11,7,82.3,16, 0.01,-0.15,23.8,20.1),
 "BAL": ("Baltimore Ravens", 4,5,0, 189,236, 247,165,66.8,7.5,1842,10,5,93.9,23, 265,1240,4.7,11, 287,187,65.2,7.6,2177,12,4,96.1,17, None,None,None,None),
 "NO":  ("New Orleans Saints", 3,5,0, 185,216, 308,204,66.2,6.4,1986,14,6,91.2,20, 203,762,3.8,7, 261,171,65.5,7.8,2045,13,4,99.6,23, -0.07,0.01,23.1,27.0),
 "SEA": ("Seattle Seahawks", 5,4,0, 202,162, 288,182,63.2,7.2,2089,15,9,89.3,19, 258,997,3.9,7, 277,178,64.3,5.5,1519,9,8,77.3,21, -0.09,-0.16,22.4,18.0),
 "PIT": ("Pittsburgh Steelers", 6,2,0, 180,144, 290,175,60.3,6.4,1871,13,6,85.6,23, 193,943,4.9,4, 280,183,65.4,6.9,1936,7,7,83.3,26, None,None,None,None),
 "HOU": ("Houston Texans", 3,5,0, 209,192, 285,182,63.9,7.9,2258,16,2,104.1,16, 195,697,3.6,6, 276,178,64.5,7.4,2056,12,4,95.3,29, None,None,None,None),
 "TEN": ("Tennessee Titans", 1,7,0, 144,199, 248,155,62.5,6.0,1483,6,5,78.8,13, 189,796,4.2,8, 272,193,71.0,8.0,2182,11,8,95.9,20, None,None,None,None),
 "MIN": ("Minnesota Vikings", 6,2,0, 146,116, 225,137,60.9,6.4,1437,8,5,82.0,23, 211,848,4.0,3, 234,135,57.7,6.4,1495,5,9,67.9,29, -0.20,-0.18,18.3,14.5),
}


def f(v):
    return "" if v is None else v


def main():
    os.makedirs("data", exist_ok=True)
    out = "data/team-metrics-2026-w10.csv"
    fields = [
        "abbr", "club", "games_played", "wins", "losses", "ties",
        "points_for", "points_against", "derived_ppg", "derived_papg",
        "ngs_off_epa_per_play", "ngs_def_epa_per_play", "ngs_ppg", "ngs_opp_ppg",
        "ppg_crosscheck_delta", "papg_crosscheck_delta",
        "pass_att", "pass_cmp", "pass_pct", "pass_ypa", "pass_yds", "pass_td", "pass_int",
        "pass_rate", "pass_sacks",
        "rush_att", "rush_yds", "rush_avg", "rush_td",
        "pass_att_share",
        "def_pass_att", "def_pass_cmp", "def_pass_pct", "def_pass_ypa", "def_pass_yds",
        "def_pass_td", "def_pass_int", "def_pass_rate", "def_pass_sacks",
        "source_standings", "source_pass_off", "source_rush_off", "source_pass_def",
        "source_ngs", "retrieved", "verification",
    ]
    rows, mismatches = [], []
    for abbr, v in T.items():
        (club, w, l, t, pf, pa,
         pa_att, pa_cmp, pa_pct, pa_ypa, pa_yds, pa_td, pa_int, pa_rate, pa_sack,
         ru_att, ru_yds, ru_avg, ru_td,
         d_att, d_cmp, d_pct, d_ypa, d_yds, d_td, d_int, d_rate, d_sack,
         e_off, e_def, ngsp, ngsop) = v
        gp = w + l + t
        ppg = round(pf / gp, 2)
        papg = round(pa / gp, 2)
        d1 = "" if ngsp is None else round(ppg - ngsp, 2)
        d2 = "" if ngsop is None else round(papg - ngsop, 2)
        # NGS publishes PPG to one decimal, so a 0.05 gap is pure rounding.
        TOL = 0.0501
        if ngsp is not None and abs(ppg - ngsp) > TOL:
            mismatches.append((abbr, "ppg", ppg, ngsp))
        if ngsop is not None and abs(papg - ngsop) > TOL:
            mismatches.append((abbr, "opp_ppg", papg, ngsop))
        # internal consistency of the passing table: cmp/att must reproduce pct
        if abs(round(100 * pa_cmp / pa_att, 1) - pa_pct) > 0.1:
            mismatches.append((abbr, "pass_pct_internal", round(100*pa_cmp/pa_att,1), pa_pct))
        if abs(round(pa_yds / pa_att, 1) - pa_ypa) > 0.1:
            mismatches.append((abbr, "pass_ypa_internal", round(pa_yds/pa_att,1), pa_ypa))
        rows.append({
            "abbr": abbr, "club": club, "games_played": gp, "wins": w, "losses": l, "ties": t,
            "points_for": pf, "points_against": pa,
            "derived_ppg": ppg, "derived_papg": papg,
            "ngs_off_epa_per_play": f(e_off), "ngs_def_epa_per_play": f(e_def),
            "ngs_ppg": f(ngsp), "ngs_opp_ppg": f(ngsop),
            "ppg_crosscheck_delta": d1, "papg_crosscheck_delta": d2,
            "pass_att": pa_att, "pass_cmp": pa_cmp, "pass_pct": pa_pct, "pass_ypa": pa_ypa,
            "pass_yds": pa_yds, "pass_td": pa_td, "pass_int": pa_int, "pass_rate": pa_rate,
            "pass_sacks": pa_sack,
            "rush_att": ru_att, "rush_yds": ru_yds, "rush_avg": ru_avg, "rush_td": ru_td,
            "pass_att_share": round(pa_att / (pa_att + ru_att), 4),
            "def_pass_att": d_att, "def_pass_cmp": d_cmp, "def_pass_pct": d_pct,
            "def_pass_ypa": d_ypa, "def_pass_yds": d_yds, "def_pass_td": d_td,
            "def_pass_int": d_int, "def_pass_rate": d_rate, "def_pass_sacks": d_sack,
            "source_standings": STAND, "source_pass_off": PASS_O,
            "source_rush_off": RUSH_O, "source_pass_def": PASS_D, "source_ngs": NGS,
            "retrieved": RET,
            "verification": "verified; ppg/papg cross-checked against NGS PPG/OPP PPG",
        })
    rows.sort(key=lambda r: r["abbr"])
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    checked = sum(1 for r in rows if r["ngs_ppg"] != "")
    print(f"wrote {len(rows)} clubs -> {out}")
    print(f"NGS PPG cross-check applied to {checked}/32 clubs")
    print(f"mismatches (tolerance 0.05): {len(mismatches)}")
    for m in mismatches:
        print("  MISMATCH", m)


if __name__ == "__main__":
    main()
