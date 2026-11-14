#!/usr/bin/env python3
"""
aggregate.py — condense raw nflverse files into small, auditable JSON tables.

Runs on the GitHub Actions runner (where raw/ was downloaded) and, if raw/ is
present, locally. Each builder is isolated: a failure in one is captured as a
traceback in data/aggregate_report.json and never silently swallowed, so the
failure is visible in the repo (CI job logs are not readable from the dev sandbox).

Outputs (all under data/):
  market.json           one row per completed game: closing numbers + result
  team_week.json        team-week EPA/success from play-by-play (no betting inputs)
  injury_week.json      team-week official game-status counts by position group
  injury_player.json    player-level official game status records
  depth_week.json       team-week depth-chart starter counts
  depth_player.json     player-level depth-chart ordering
  player_week.json      player-week box score for prop modelling
  snap_week.json        player-game snap counts
  aggregate_report.json inputs, outputs, per-section status, errors

HARD RULE: never infer or impute a value. Missing -> null, and say so.
"""
from __future__ import annotations

import glob
import json
import re
import os
import sys
import traceback

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# This section lives in signal/ ; ROOT is signal/ and data/ is signal/data.
RAW = os.path.join(ROOT, "raw")
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)

REPORT = {"generated_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
          "inputs": {}, "outputs": {}, "sections": {}, "notes": [], "errors": []}


def js(v):
    """Make a value JSON-safe without inventing anything."""
    if v is None:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if (np.isnan(v) or np.isinf(v)) else float(v)
    if isinstance(v, float):
        return None if (np.isnan(v) or np.isinf(v)) else v
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    return v


def dump(name, obj):
    p = os.path.join(DATA, name)
    with open(p, "w") as f:
        json.dump(obj, f, separators=(",", ":"), default=js)
    REPORT["outputs"][name] = {"bytes": os.path.getsize(p)}
    print(f"  wrote {name:24s} {os.path.getsize(p):>12,} B")


def recs(df):
    out = []
    for r in df.to_dict("records"):
        out.append({k: js(v) for k, v in r.items()})
    return out


def rd(fname):
    p = os.path.join(RAW, fname)
    if not os.path.exists(p):
        REPORT["inputs"][fname] = "missing"
        return None
    try:
        df = pd.read_csv(p, low_memory=False)
        REPORT["inputs"][fname] = {"rows": int(len(df)), "cols": int(df.shape[1])}
        return df
    except Exception as e:
        REPORT["inputs"][fname] = f"parse error: {e}"
        return None


def seasons_of(pattern):
    out = set()
    for p in glob.glob(os.path.join(RAW, pattern)):
        digits = "".join(ch for ch in os.path.basename(p) if ch.isdigit())
        if len(digits) >= 4:
            out.add(int(digits[:4]))
    return sorted(out)


def section(fn):
    """Run a builder, recording success or the full traceback."""
    name = fn.__name__
    try:
        info = fn()
        REPORT["sections"][name] = {"status": "ok", "detail": info or {}}
    except Exception:
        REPORT["sections"][name] = {"status": "error",
                                    "traceback": traceback.format_exc().splitlines()[-6:]}
        REPORT["errors"].append(f"{name}: {traceback.format_exc().splitlines()[-1]}")
        print(f"  ERROR in {name}:\n{traceback.format_exc()}")
    return REPORT["sections"][name]["status"]


POS_GROUP = {
    "QB": "QB", "RB": "SKILL", "FB": "SKILL", "WR": "SKILL", "TE": "SKILL",
    "T": "OL", "G": "OL", "C": "OL", "OT": "OL", "OG": "OL", "OL": "OL",
    "DE": "DL", "DT": "DL", "NT": "DL", "EDGE": "DL", "DL": "DL",
    "LB": "LB", "ILB": "LB", "OLB": "LB", "MLB": "LB",
    "CB": "DB", "S": "DB", "FS": "DB", "SS": "DB", "DB": "DB",
    "K": "ST", "P": "ST", "LS": "ST", "KR": "ST", "PR": "ST",
}
GROUPS = ["QB", "SKILL", "OL", "DL", "LB", "DB", "ST", "OTHER"]
STATUS_WEIGHT = {"Out": 1.0, "Doubtful": 0.75, "Questionable": 0.35, "Probable": 0.1}


# ---------------------------------------------------------------- market ----
def market():
    g = rd("games.csv")
    if g is None:
        return {"skipped": "games.csv missing"}
    cols = ["game_id", "season", "game_type", "week", "gameday", "gametime",
            "away_team", "home_team", "away_score", "home_score",
            "spread_line", "total_line", "away_moneyline", "home_moneyline",
            "away_rest", "home_rest", "div_game", "roof", "surface", "temp", "wind"]
    g = g[[c for c in cols if c in g.columns]].copy()
    g["season"] = pd.to_numeric(g["season"], errors="coerce")
    g["week"] = pd.to_numeric(g["week"], errors="coerce")
    g = g[g["season"] >= 2015]
    g = g[g["game_type"].astype(str).str.upper().str.startswith("REG")]
    for c in ["away_score", "home_score", "spread_line", "total_line",
              "away_moneyline", "home_moneyline", "away_rest", "home_rest", "temp", "wind"]:
        if c in g.columns:
            g[c] = pd.to_numeric(g[c], errors="coerce")
    g["final_total"] = g["away_score"] + g["home_score"]
    g["home_margin"] = g["home_score"] - g["away_score"]
    # SIGN CONVENTION (validated 2026-11-14): games.csv `spread_line` is signed from the
    # AWAY team, so the home line is its negation. Read naively as a home line it yields a
    # 56.93% home cover rate, which is impossible; inverted, the home cover rate is 48.53%
    # and the over rate 49.00% over 3,032 graded games, and it reproduces the
    # closing_lines.csv `outcome` column on 98.92% of graded games.
    g["home_line"] = -g["spread_line"]
    edge = g["home_margin"] + g["home_line"]
    g["home_cover_margin"] = edge
    g["home_covered"] = np.select([edge > 0, edge < 0, edge == 0], [1.0, 0.0, 0.5], np.nan)
    g["total_delta"] = g["final_total"] - g["total_line"]
    g["completed"] = g["home_score"].notna() & g["away_score"].notna()
    g["has_line"] = g["spread_line"].notna()
    g = g.drop(columns=["away_score", "home_score"])
    dump("market.json", {"source": "raw/games.csv",
                         "home_line": ("-spread_line; spread_line is away-signed. Validated "
                                       "against closing_lines.csv outcome (98.92%) and by the "
                                       "market-rate check (home cover 48.53%, over 49.00%)."),
                         "rows": recs(g)})
    done = g[g["completed"]]
    mx = g["season"].max()
    return {"games": len(g), "completed": len(done),
            "with_spread": int(g["has_line"].sum()),
            "max_season": int(mx),
            "max_completed_week_this_season": int(done[done.season == mx]["week"].max())
            if len(done[done.season == mx]) else None}


# ------------------------------------------------------------- team_week ----
PBP_KEEP = ["season", "week", "posteam", "defteam", "play_type", "epa", "success"]


def team_week():
    have = seasons_of("play_by_play_*.csv")
    if not have:
        return {"skipped": "no play-by-play files"}
    frames = []
    for y in have:
        df = rd(f"play_by_play_{y}.csv")
        if df is None:
            continue
        keep = [c for c in PBP_KEEP if c in df.columns]
        frames.append(df[keep].copy())
        del df
    if not frames:
        return {"skipped": "no readable play-by-play"}
    pbp = pd.concat(frames, ignore_index=True)
    del frames
    pbp["epa"] = pd.to_numeric(pbp["epa"], errors="coerce")
    pbp["success"] = pd.to_numeric(pbp["success"], errors="coerce")
    pbp = pbp[pbp["play_type"].isin(["pass", "run", "sack"])].copy()
    pbp["is_pass"] = pbp["play_type"].isin(["pass", "sack"]).astype(int)
    pbp["is_sack"] = (pbp["play_type"] == "sack").astype(int)
    pbp = pbp.dropna(subset=["epa"])

    long = pbp.melt(id_vars=["season", "week", "epa", "success", "is_pass", "is_sack"],
                    value_vars=["posteam", "defteam"],
                    var_name="side", value_name="team")
    long = long.dropna(subset=["team"])
    g = long.groupby(["season", "week", "team", "side"], as_index=False).agg(
        plays=("epa", "size"), epa_sum=("epa", "sum"),
        succ_sum=("success", "sum"), pass_plays=("is_pass", "sum"))
    pe = (long[long.is_pass == 1].groupby(["season", "week", "team", "side"], as_index=False)
          .agg(pass_epa=("epa", "sum")))
    g = g.merge(pe, on=["season", "week", "team", "side"], how="left")
    g["pass_epa"] = g["pass_epa"].fillna(0.0)

    w = g.pivot_table(index=["season", "week", "team"], columns="side",
                      values=["plays", "epa_sum", "succ_sum", "pass_plays", "pass_epa"],
                      aggfunc="sum").reset_index()
    w.columns = [f"{a}_{b}" if b else a for a, b in w.columns]

    def col(k):
        return w[k] if k in w.columns else pd.Series([np.nan] * len(w))

    out = pd.DataFrame({
        "season": w["season"].astype(int), "week": w["week"].astype(int),
        "team": w["team"],
        "off_plays": col("plays_off"), "off_epa_sum": col("epa_sum_off"),
        "off_success_sum": col("succ_sum_off"),
        "off_pass_plays": col("pass_plays_off"), "off_pass_epa_sum": col("pass_epa_off"),
        "def_plays": col("plays_def"), "def_epa_sum": col("epa_sum_def"),
        "def_success_sum": col("succ_sum_def"),
        "def_pass_plays": col("pass_plays_def"), "def_pass_epa_sum": col("pass_epa_def"),
    })
    out["off_epa_play"] = out["off_epa_sum"] / out["off_plays"]
    out["def_epa_play"] = out["def_epa_sum"] / out["def_plays"]
    out["off_success_rate"] = out["off_success_sum"] / out["off_plays"]
    out["def_success_rate"] = out["def_success_sum"] / out["def_plays"]
    out["off_pass_rate"] = out["off_pass_plays"] / out["off_plays"]
    out["off_pass_epa_play"] = out["off_pass_epa_sum"] / out["off_pass_plays"]
    out["def_pass_epa_play"] = out["def_pass_epa_sum"] / out["def_pass_plays"]
    out = out.replace([np.inf, -np.inf], np.nan)
    for c in out.columns:
        if out[c].dtype.kind == "f":
            out[c] = out[c].round(5)
    dump("team_week.json", {
        "source": "raw/play_by_play_YYYY.csv",
        "definition": ("One row per team-week. EPA and success rate from nflfastR "
                       "play-by-play; pass plays include sacks. Contains no betting "
                       "inputs, so it can be used as a pre-game feature."),
        "rows": recs(out)})
    return {"team_weeks": len(out), "seasons": [int(out.season.min()), int(out.season.max())]}


# -------------------------------------------------------------- injuries ----
def injuries():
    have = seasons_of("injuries_*.csv")
    if not have:
        return {"skipped": "no injury files"}
    frames = []
    for y in have:
        df = rd(f"injuries_{y}.csv")
        if df is not None:
            frames.append(df)
    if not frames:
        return {"skipped": "no readable injury files"}
    inj = pd.concat(frames, ignore_index=True)
    inj["season"] = pd.to_numeric(inj["season"], errors="coerce")
    inj["week"] = pd.to_numeric(inj["week"], errors="coerce")
    inj = inj[inj["game_type"].astype(str).str.upper().str.startswith("REG")]
    inj["pos_group"] = inj["position"].map(POS_GROUP).fillna("OTHER")
    st = inj["report_status"].astype(str).str.strip()
    inj["game_status"] = st.where(st.isin(["Out", "Doubtful", "Questionable", "Probable"]), None)
    inj["weight"] = inj["game_status"].map(STATUS_WEIGHT).fillna(0.0)

    rows = []
    for (season, week, team), g in inj.groupby(["season", "week", "team"], dropna=True):
        r = {"season": int(season), "week": int(week), "team": team, "listed": int(len(g))}
        for grp in GROUPS:
            s = g[g["pos_group"] == grp]
            r[f"out_{grp}"] = int((s["game_status"] == "Out").sum())
            r[f"doubt_{grp}"] = int((s["game_status"] == "Doubtful").sum())
            r[f"quest_{grp}"] = int((s["game_status"] == "Questionable").sum())
            r[f"burden_{grp}"] = round(float(s["weight"].sum()), 3)
        rows.append(r)

    det = inj[["season", "week", "team", "gsis_id", "position", "pos_group",
               "full_name", "game_status", "practice_status",
               "report_primary_injury"]].copy()
    det = det[det["game_status"].notna()]
    det["season"] = det["season"].astype(int)
    det["week"] = det["week"].astype(int)

    dump("injury_week.json", {
        "source": "raw/injuries_YYYY.csv",
        "status_weights": STATUS_WEIGHT,
        "weight_note": ("burden_* applies a transparent LINEAR weight to official "
                        "game status. It is a modelling choice, NOT a measured value, "
                        "and is unvalidated. See the Questions register."),
        "team_weeks": rows})
    det.to_csv(os.path.join(DATA, "injury_player.csv"), index=False)
    REPORT["outputs"]["injury_player.csv"] = {"bytes": os.path.getsize(os.path.join(DATA, "injury_player.csv"))}
    return {"report_lines": len(inj),
            "seasons": [int(inj.season.min()), int(inj.season.max())],
            "statuses": sorted([str(s) for s in inj["game_status"].dropna().unique()])}


# ----------------------------------------------------------------- depth ----
def depth():
    have = seasons_of("depth_charts_*.csv")
    if not have:
        return {"skipped": "no depth chart files"}
    frames = []
    for y in have:
        df = rd(f"depth_charts_{y}.csv")
        if df is not None:
            frames.append(df)
    if not frames:
        return {"skipped": "no readable depth charts"}
    dc = pd.concat(frames, ignore_index=True)
    dc["season"] = pd.to_numeric(dc.get("season"), errors="coerce")
    dc["week"] = pd.to_numeric(dc.get("week"), errors="coerce")
    if "game_type" in dc.columns:
        dc = dc[dc["game_type"].astype(str).str.upper().str.startswith("REG")]
    dc["depth_team"] = pd.to_numeric(dc.get("depth_team"), errors="coerce")
    poscol = "position" if "position" in dc.columns else "depth_position"
    dc["position"] = dc.get(poscol)
    dc["pos_group"] = dc["position"].map(POS_GROUP).fillna("OTHER")
    club = "club_code" if "club_code" in dc.columns else "team"
    dc["team"] = dc.get(club)

    st = dc[dc["depth_team"] == 1]
    rows = []
    for (season, week, team), g in st.groupby(["season", "week", "team"], dropna=True):
        r = {"season": int(season), "week": int(week), "team": team,
             "listed_starters": int(len(g))}
        for grp in GROUPS:
            r[f"starters_{grp}"] = int((g["pos_group"] == grp).sum())
        rows.append(r)

    keep = [c for c in ["season", "week", "team", "position", "pos_group",
                        "depth_team", "full_name", "gsis_id"] if c in dc.columns]
    per = dc[keep].copy()
    per["season"] = per["season"].astype("Int64")
    per["week"] = per["week"].astype("Int64")
    # Keep only the ordering we actually validate (1st and 2nd string) to stay compact.
    per = per[per["depth_team"].isin([1, 2])]
    # VERIFIED against data/schema_samples.json (2026-11-14): the release depth-chart files
    # carry BOTH `football_name` (given name only, e.g. "Brian") and `full_name` (the real
    # full name). Only `full_name` can be joined to participation data. `gsis_id` is kept
    # for an exact join where both sides carry it.
    per.to_csv(os.path.join(DATA, "depth_player.csv"), index=False)
    REPORT["outputs"]["depth_player.csv"] = {
        "bytes": os.path.getsize(os.path.join(DATA, "depth_player.csv")),
        "definition": ("One row per player listed 1st or 2nd string on the club depth chart for "
                       "a team-week. Used to test whether the published chart predicts who plays.")}

    dump("depth_week.json", {
        "source": "raw/depth_charts_YYYY.csv",
        "caveat": ("Depth charts are the club's own published ordering, not an "
                   "official league record, and may be stale or wrong. Proxy only."),
        "team_weeks": rows})
    dump("depth_player.json", {"source": "raw/depth_charts_YYYY.csv", "rows": recs(per)})
    return {"entries": len(dc), "seasons": [int(dc.season.min()), int(dc.season.max())]}


# ----------------------------------------------------------- player_week ----
def player_week():
    have = seasons_of("stats_player_week_*.csv")
    if not have:
        return {"skipped": "no player stat files"}
    frames = []
    for y in have:
        df = rd(f"stats_player_week_{y}.csv")
        if df is not None:
            frames.append(df)
    if not frames:
        return {"skipped": "no readable player stats"}
    ps = pd.concat(frames, ignore_index=True)
    cols = [c for c in ["player_id", "player_name", "player_display_name", "position",
                        "position_group", "season", "week", "season_type", "team",
                        "opponent_team", "completions", "attempts", "passing_yards",
                        "passing_tds", "interceptions", "carries", "rushing_yards",
                        "rushing_tds", "receptions", "targets", "receiving_yards",
                        "receiving_tds", "receiving_air_yards", "target_share",
                        "air_yards_share", "wopr", "fantasy_points",
                        "fantasy_points_ppr"] if c in ps.columns]
    ps = ps[cols].copy()
    # Full player-week rows are ~62 MB as JSON. Commit (a) participation keys and
    # (b) a weekly roll-up, and keep the raw detail in the Actions artifact.
    for c in ["season", "week"]:
        ps[c] = pd.to_numeric(ps[c], errors="coerce")
    ps = ps.dropna(subset=["season", "week"])
    key = ps[["season", "week", "team", "player_name"]].drop_duplicates()
    dump("player_week_keys.json", {
        "source": "raw/stats_player_week_YYYY.csv",
        "definition": ("One row per player-team-week listed with any recorded statistic. "
                       "Absence does not by itself prove the player was inactive."),
        "rows": recs(key)})

    for c in ["attempts", "carries", "targets", "receptions", "passing_yards",
              "rushing_yards", "receiving_yards", "passing_tds", "rushing_tds",
              "receiving_tds"]:
        if c in ps.columns:
            ps[c] = pd.to_numeric(ps[c], errors="coerce")
    team = ps.groupby(["season", "week", "team"], dropna=True).agg(
        pass_att=("attempts", "sum"), pass_yds=("passing_yards", "sum"),
        pass_td=("passing_tds", "sum"), rush_att=("carries", "sum"),
        rush_yds=("rushing_yards", "sum"), rush_td=("rushing_tds", "sum"),
        targets=("targets", "sum"), rec=("receptions", "sum"),
        rec_yds=("receiving_yards", "sum"), rec_td=("receiving_tds", "sum"),
    ).reset_index()
    dump("team_offense_week.json", {"source": "raw/stats_player_week_YYYY.csv",
                                    "definition": "Team-week offensive totals summed from player rows.",
                                    "rows": recs(team)})
    return {"player_weeks": len(ps)}


# ---------------------------------------------------------------- snaps ----
def snaps():
    have = seasons_of("snap_counts_*.csv")
    if not have:
        return {"skipped": "no snap count files"}
    frames = []
    for y in have:
        df = rd(f"snap_counts_{y}.csv")
        if df is not None:
            frames.append(df)
    if not frames:
        return {"skipped": "no readable snap counts"}
    sc = pd.concat(frames, ignore_index=True)
    sc.columns = [c.strip().lower().replace(" ", "_") for c in sc.columns]
    # Weekly per-player participation is needed for the injury measurement but is far too
    # large to commit as JSON. Commit the participation KEYS (season, week, team, player)
    # plus a compact season workload roll-up; the raw file stays in the Actions artifact.
    keys = sc[["season", "week", "team", "player"]].copy()
    keys["season"] = pd.to_numeric(keys["season"], errors="coerce")
    keys["week"] = pd.to_numeric(keys["week"], errors="coerce")
    keys = keys.dropna(subset=["season", "week"])
    # collapse to one row per player-week: participation, not per-snap detail
    keys = keys.drop_duplicates()
    keys["played"] = 1
    dump("snap_participation.json", {
        "source": "raw/snap_counts_YYYY.csv",
        "definition": ("One row per player-team-week that appears in the snap counts. "
                       "Appearance means he took at least one snap; non-appearance means no row."),
        "cols": ["season", "week", "team", "player"],
        "rows": recs(keys.drop(columns=["played"]))})

    for c in ["offense_snaps", "defense_snaps", "st_snaps"]:
        if c in sc.columns:
            sc[c] = pd.to_numeric(sc[c], errors="coerce")
    if "season" in sc.columns:
        sc["season"] = pd.to_numeric(sc["season"], errors="coerce")
    roll = sc.groupby(["season", "team", "player"], dropna=True).agg(
        games=("week", "nunique"),
        off_snaps=("offense_snaps", "sum"),
        def_snaps=("defense_snaps", "sum"),
        st_snaps=("st_snaps", "sum"),
    ).reset_index()
    roll = roll.sort_values(["season", "off_snaps"], ascending=[True, False]).head(4000)
    dump("snap_season.json", {"source": "raw/snap_counts_YYYY.csv",
                              "definition": "Season workload roll-up, largest 4,000 rows only.",
                              "rows": recs(roll)})
    return {"records": len(sc), "participation_rows": len(keys)}


def schema_samples():
    """Record the ACTUAL column list and a few raw rows of every input file.

    This exists because the officially documented schema is not always the schema in the
    file. nflreadr's depth-chart dictionary documents `dt, team, player_name, pos_rank`;
    the historical files in the release use `club_code, depth_team, football_name`. Rather
    than assume which applies, the pipeline records what it actually received so a join can
    be written against evidence.
    """
    out = {}
    for p in sorted(glob.glob(os.path.join(RAW, "*.csv"))):
        name = os.path.basename(p)
        ds = re.sub(r"_\d{4}\.csv$", "", name).replace(".csv", "")
        if ds in out:
            continue
        try:
            df = pd.read_csv(p, nrows=3, low_memory=False)
            with open(p, encoding="utf-8", errors="replace") as f:
                header = f.readline().strip().split(",")
            out[ds] = {"example_file": name, "columns": header,
                       "sample_rows": recs(df)}
        except Exception as e:
            out[ds] = {"example_file": name, "error": str(e)}
    dump("schema_samples.json", {
        "purpose": ("Exact column names and sample rows per input dataset, recorded from the "
                    "files actually downloaded. Use this before writing any join."),
        "documented_vs_actual_warning": (
            "nflreadr's depth-chart dictionary documents dt/team/player_name/pos_rank, but the "
            "historical release files use club_code/depth_team/football_name. The injuries "
            "dictionary documents season_type, while older files carry game_type. Verify here."),
        "datasets": out})
    return {"datasets": len(out)}


def player_bridge():
    """Emit the id crosswalk needed for exact joins.

    snap_counts carries pfr_player_id only. depth_charts and injuries carry gsis_id only.
    players.csv carries both, so it is the bridge. Name joins are a fallback, not a plan.
    """
    pl = rd("players.csv")
    if pl is None:
        return {"skipped": "players.csv missing"}
    keep = [c for c in ["gsis_id", "pfr_id", "pff_id", "espn_id", "display_name",
                        "football_name", "position", "position_group"] if c in pl.columns]
    pl = pl[keep].dropna(subset=[c for c in ["gsis_id"] if c in pl.columns])
    pl.to_csv(os.path.join(DATA, "player_bridge.csv"), index=False)
    REPORT["outputs"]["player_bridge.csv"] = {
        "bytes": os.path.getsize(os.path.join(DATA, "player_bridge.csv")),
        "purpose": "gsis_id <-> pfr_id crosswalk for exact joins between datasets."}
    return {"players": len(pl)}


def main():
    if not os.path.isdir(RAW):
        print(f"FATAL: no raw/ at {RAW}")
        return 1
    print(f"raw/ file count: {len(os.listdir(RAW))}")
    for fn in [schema_samples, player_bridge, market, team_week, injuries, depth, player_week, snaps]:
        print(f"[{fn.__name__}]")
        print(f"  -> {section(fn)}")
    dump("aggregate_report.json", REPORT)
    print("\nnotes:")
    for n in REPORT["notes"]:
        print("  ", n)
    if REPORT["errors"]:
        print("\nERRORS:")
        for e in REPORT["errors"]:
            print("  ", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
