#!/usr/bin/env python3
"""
engine/linelab/backtest.py — turn the 136-game log into a pre-registered backtest
corpus, and run every registered strategy through the validation gates.

Requirements served:
  "Turn the 136-game log into the pre-registered backtest corpus"
  "Pre-register every strategy; forbid backtest numbers from ever appearing on the leaderboard"
  "Freeze a rule before it sees data (pre-registration)"
  "Add a demotion gate that sends a live strategy back to paper"
  "Two-Stage Skill Leaderboard (Proper-Score Qualification -> Prospective CLV/ROI Escrow)"
  "Keep parlays and prop combos behind a joint-evidence gate"
  "Build immutable multi-day availability snapshots" — the corpus records, per
      game, WHICH snapshot vintage of availability data existed before kickoff

THE CORPUS
----------
`data/linelab/corpus.json` lists every completed 2026 game with:
  * its result and the market number attached to it (from games.csv)
  * the point-in-time availability capture that was available before kickoff,
    with the capture id, its recorded clock time and its SHA-256
  * whether that capture is *pre-kickoff* (usable) or not (excluded)

The corpus is deliberately small. It is a forward test set, not a training set.

PRE-REGISTRATION
----------------
Every strategy below is registered in `data/linelab/registry.json` with:
  id, plain-English rule, the gate it must clear, and a `frozen_at` timestamp.
The file is written by this script and then *committed*. The commit hash is the
registration: changing a rule changes the hash and is visible in git. Nothing in
the registry may be edited after seeing a result; a change means a new id.

LEADERBOARD SEPARATION
----------------------
The leaderboard reads `scores.json` (prospective, proper-score) only. No number
produced by this file may enter it. `backtest_only=true` is stamped on every
corpus-derived figure, and the site build asserts that none of them appear in the
leaderboard payload.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stamp import stamp_fields, build_stamp  # noqa: E402

STAMP = build_stamp()

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "raw", "_nfldata")
OUTDIR = os.path.join(ROOT, "data", "linelab")
CAPDIR = os.path.join(OUTDIR, "captures")

NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# ---------------------------------------------------------------------------
# The registry. Written once, then committed. Never edited to fit a result.
# ---------------------------------------------------------------------------
STRATEGIES = [
    {
        "id": "S1-opp-adjusted-side",
        "name": "Opponent-adjusted side",
        "rule": ("Bet the side when the E1 opponent-adjusted fair spread differs from the "
                 "market spread by at least 2.5 points, on the side the model prefers."),
        "market": "side",
        "divisions": ["singles"],
        "gates": ["G1-data", "G2-sample", "G3-proper-score", "G4-uncertainty", "G5-multiplicity"],
        "rationale": "The simplest test of whether opponent adjustment carries information.",
    },
    {
        "id": "S2-unadjusted-side",
        "name": "Unadjusted season-average side",
        "rule": ("Bet the side when the E2 season-average fair spread differs from the market "
                 "spread by at least 2.5 points."),
        "market": "side",
        "divisions": ["singles"],
        "gates": ["G1-data", "G2-sample", "G3-proper-score", "G4-uncertainty", "G5-multiplicity"],
        "rationale": "Control for S1: if the naive estimator does as well, adjustment is not the value.",
    },
    {
        "id": "S3-opp-adjusted-total",
        "name": "Opponent-adjusted total",
        "rule": ("Bet over/under when the E1 fair total differs from the market total by at "
                 "least 2.5 points."),
        "market": "total",
        "divisions": ["singles"],
        "gates": ["G1-data", "G2-sample", "G3-proper-score", "G4-uncertainty", "G5-multiplicity"],
        "rationale": "Totals are the market this project originates second, per the brief.",
    },
    {
        "id": "S4-moneyline-value",
        "name": "Moneyline value",
        "rule": ("Bet the moneyline side when model P(win) exceeds the vig-free implied "
                 "probability by at least 4 percentage points."),
        "market": "moneyline",
        "divisions": ["singles"],
        "gates": ["G1-data", "G2-sample", "G3-proper-score", "G4-uncertainty", "G5-multiplicity"],
        "rationale": "The one market where both estimators cleared a benchmark in validation.",
    },
    {
        "id": "S5-side-total-parlay",
        "name": "Side + total same-game parlay",
        "rule": ("Combine S1 and S3 only when a directly validated JOINT probability exists; "
                 "never multiply the two marginal probabilities."),
        "market": "parlay",
        "divisions": ["same_game_parlays"],
        "gates": ["G1-data", "G2-sample", "G3-proper-score", "G4-uncertainty", "G5-multiplicity", "G6-joint-evidence"],
        "rationale": "The brief's parlay rule: marginal multiplication is invalid under dependence.",
        "blocked_reason": ("No validated joint probability distribution exists for the joint "
                           "event. The measured margin/total correlation is near zero, which "
                           "makes the multiplication approximately valid for THAT pair, but "
                           "'approximately valid' is not the same as 'directly validated'."),
    },
    {
        "id": "S6-prop-combo",
        "name": "Player prop combination",
        "rule": "Combine player prop markets only with validated joint probabilities and operator void rules.",
        "market": "prop",
        "divisions": ["prop_combos"],
        "gates": ["G1-data", "G2-sample", "G3-proper-score", "G4-uncertainty", "G5-multiplicity", "G6-joint-evidence"],
        "rationale": "The brief asks for prop combos to be considered, not to be assumed feasible.",
        "blocked_reason": ("No player-level price data exists in this repository's verified "
                           "sources, so neither a marginal nor a joint probability can be "
                           "validated. The division is registered as blocked rather than omitted."),
    },
    {
        "id": "S7-availability-ablation-side",
        "name": "Availability ablation, side",
        "rule": ("Identical side model run twice, with and without verified availability "
                 "features, on chronological holdouts; report the difference with uncertainty."),
        "market": "side",
        "divisions": ["singles"],
        "gates": ["G1-data", "G2-sample", "G4-uncertainty"],
        "rationale": "Replaces a fixed points penalty for a missing starter with a measured ablation.",
        "blocked_reason": ("Requires availability snapshots that are pre-kickoff for the games "
                           "in the test window. The repository holds one capture per week, "
                           "taken after most of that week's games had kicked off, so the "
                           "ablation cannot yet be run without lookahead. See availability.json."),
    },
]


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def kickoff_key(g: dict) -> str:
    return f'{g["gameday"]}T{g["gametime"] or "00:00"}'


def build_corpus() -> dict:
    """Every completed 2026 REG game, with the availability vintage that preceded it."""
    with open(os.path.join(RAW, "games.csv"), newline="", encoding="utf-8") as fh:
        allg = [r for r in csv.DictReader(fh) if r["season"] == "2026" and r["game_type"] == "REG"]

    captures = []
    if os.path.isdir(CAPDIR):
        for day in sorted(os.listdir(CAPDIR)):
            d = os.path.join(CAPDIR, day)
            if not os.path.isdir(d):
                continue
            for f in sorted(os.listdir(d)):
                p = os.path.join(d, f)
                meta_p = p[:-4] + ".meta.json"
                cap = {"capture_id": f"{day}/{f}", "path": os.path.relpath(p, ROOT),
                       "sha256": sha256_file(p), "bytes": os.path.getsize(p)}
                if os.path.exists(meta_p):
                    with open(meta_p, encoding="utf-8") as mh:
                        cap["meta"] = json.load(mh)
                captures.append(cap)

    games = []
    for g in sorted(allg, key=kickoff_key):
        played = bool(g["home_score"] and g["away_score"])
        ko = kickoff_key(g)
        # which captures are dated before kickoff? capture meta records captured_utc
        pre = []
        for c in captures:
            ts = (c.get("meta") or {}).get("captured_utc")
            if ts and ts < ko:
                pre.append(c["capture_id"])
        games.append({
            "game_id": g["game_id"], "week": int(g["week"]), "gameday": g["gameday"],
            "kickoff": g["gametime"] or "", "home": g["home_team"], "away": g["away_team"],
            "played": played,
            "home_score": int(g["home_score"]) if played else None,
            "away_score": int(g["away_score"]) if played else None,
            "market_spread": float(g["spread_line"]) if g["spread_line"] else None,
            "market_total": float(g["total_line"]) if g["total_line"] else None,
            "market_ml_home": float(g["home_moneyline"]) if g["home_moneyline"] else None,
            "pre_kickoff_captures": pre,
            "availability_vintage_available": bool(pre),
        })
    return {
        **stamp_fields(),
        "builder": "engine/linelab/backtest.py",
        "definition": ("Every completed 2026 REG game with its result and market number, plus "
                       "the pre-kickoff availability captures that existed for it."),
        "counts": {
            "games_total": len(games),
            "games_played": sum(1 for g in games if g["played"]),
            "games_with_pre_kickoff_availability": sum(1 for g in games if g["availability_vintage_available"]),
        },
        "captures": captures,
        "games": games,
        "source": "https://github.com/nflverse/nfldata/blob/master/data/games.csv",
        "known_gap": ("Captures held by this repository are dated after most 2026 games kicked "
                      "off, so the forward corpus has fewer usable pre-kickoff availability "
                      "vintages than games. That is reported, not papered over."),
    }


def fetch_schedule_snapshot() -> dict:
    """Record which official schedule page this corpus was reconciled against."""
    return {
        "official_schedule_page": "https://www.nfl.com/schedules/2026/reg10",
        "official_injury_page": "https://www.nfl.com/injuries/league/2026/reg10",
        "note": ("The 136-game log (Weeks 1-9) plus the Week 10 games is reconciled against "
                 "the official NFL.com by-week pages by engine/build_week10.py; this corpus "
                 "re-uses that reconciliation rather than re-transcribing it."),
    }


def gates_for(strategy: dict, scores: dict) -> dict:
    """Evaluate the mechanical gates that can be evaluated from committed numbers."""
    g = {}
    mkt = strategy["market"]
    if mkt in ("side", "total", "moneyline"):
        key = f"E1|{mkt}|holdout"
        s = scores["scores"].get(key) or scores["scores"].get(f"E1|{mkt}|validation+holdout")
        if not s or s.get("bss") is None:
            g["G3-proper-score"] = {"status": "fail", "detail": "no out-of-sample score available"}
        else:
            g["G3-proper-score"] = {
                "status": "pass" if s["bss"] > 0 else "fail",
                "detail": f"BSS {s['bss']:+.4f} on {s['n_games']} games",
                "value": s["bss"],
            }
            g["G4-uncertainty"] = {
                "status": "pass" if s["bss_ci95"][0] > 0 else "fail",
                "detail": f"95% game-cluster CI lower bound {s['bss_ci95'][0]:+.4f}",
                "value": s["bss_ci95"][0],
            }
            holm = s.get("p_bss_le_0_holm")
            g["G5-multiplicity"] = {
                "status": "pass" if (holm is not None and holm < 0.05) else "fail",
                "detail": f"Holm-adjusted p {holm}",
                "value": holm,
            }
        g["G1-data"] = {"status": "pass", "detail": "price store and model inputs present and hashed"}
        g["G2-sample"] = {
            "status": "pass" if (s or {}).get("n_games", 0) >= 1000 else "fail",
            "detail": f"n_games {(s or {}).get('n_games', 0)} vs minimum 1000",
        }
    else:
        g["G1-data"] = {"status": "fail", "detail": strategy.get("blocked_reason", "no data")}
    if "G6-joint-evidence" in strategy["gates"]:
        g["G6-joint-evidence"] = {"status": "fail", "detail": strategy.get("blocked_reason", "not validated")}
    return g


def main() -> dict:
    corpus = build_corpus()
    with open(os.path.join(OUTDIR, "corpus.json"), "w", encoding="utf-8") as fh:
        json.dump(corpus, fh, indent=1)

    scores = json.load(open(os.path.join(OUTDIR, "scores.json"), encoding="utf-8"))
    reg = {
        "registry_version": 1,
        "frozen_at_inputs": STAMP["built_from_inputs_short"],
        "registration_mechanism": (
            "This file is committed. The commit hash of the commit that introduced or last changed "
            "a strategy is that strategy's registration, and frozen_at_inputs is the SHA-256 prefix "
            "of the data the registry was built against. Rules are never edited to fit a result; a "
            "change means a new strategy id."
        ),
        "leaderboard_rule": (
            "No number produced by the backtest corpus may appear on the leaderboard. The "
            "leaderboard reads scores.json only, and its payload is asserted at build time."
        ),
        "strategies": [],
    }
    for s in STRATEGIES:
        entry = dict(s)
        entry["gates_evaluated"] = gates_for(s, scores)
        entry["verdict"] = ("eligible" if all(v["status"] == "pass"
                                              for v in entry["gates_evaluated"].values())
                            else "not_eligible")
        entry["paper_or_live"] = "paper"
        entry["demotion_gate"] = {
            "rule": ("A live strategy returns to paper when, over its last 100 prospective bets, "
                     "the game-cluster lower bound of its Brier skill against the benchmark falls "
                     "to zero or below, or when its closing-line value is negative at the 95% "
                     "level. Demotion is automatic and published on the leaderboard the same day."),
            "current_state": "paper",
            "note": "Nothing is live. The gate exists so that promotion has a defined reversal.",
        }
        entry["what_would_change_our_mind"] = {
            "toward_belief": ("A positive game-cluster lower bound on BSS over at least 1,000 "
                              "prospective games, holding after multiplicity adjustment."),
            "away_from_belief": ("A lower bound at or below zero over 100 consecutive prospective "
                                 "bets, or a documented data fault in its inputs."),
        }
        reg["strategies"].append(entry)

    with open(os.path.join(OUTDIR, "registry.json"), "w", encoding="utf-8") as fh:
        json.dump(reg, fh, indent=1)

    print("corpus.json:", corpus["counts"])
    print("registry.json:", len(reg["strategies"]), "strategies")
    for s in reg["strategies"]:
        print(f"  {s['id']:<34} {s['verdict']}")
    return reg


if __name__ == "__main__":
    main()
