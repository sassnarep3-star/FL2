#!/usr/bin/env python3
"""
tools/run_leaderboard.py — FL2 competition layer (T24).

Hard separation (brief: "Separate 'signal' from 'staking' ... so a lucky staking
run cannot mask a bad signal"):

  * leaderboard rows carry SIGNAL columns (Brier skill + lower bound) and
    STAKING columns (flat-unit ROI) in separate groups, never combined;
  * BACKTEST numbers are FORBIDDEN on the leaderboard (pre-registration rule).
    Development-corpus numbers go to data/development_panel.json with a permanent
    BACKTEST label and are rendered on their own page.

Emits:
  data/leaderboard.json          - divisions, registered strategies, gates,
                                   control baselines, demotion gate, two-sided
                                   "what would change our mind" fields
  data/development_panel.json    - BACKTEST-labelled development corpus numbers
                                   + the removal-of-luck panel (null distributions)

Removal-of-luck panel: exact binomial null for flat 1-unit bets at -110
(break-even 0.5238095) at several n, plus the pre-registered sample floor.
Deterministic; stdlib only.
"""
from __future__ import annotations

import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRATION_COMMIT = "55b94c1"
BREAKEVEN = 0.5238095  # -110


def binom_quantiles(n, p, qs):
    """Exact binomial quantiles for wins in n bets (log-space to avoid overflow)."""
    out = {}
    cdf = 0.0
    qmap = {q: None for q in qs}
    logp, logq = math.log(p), math.log(1 - p)
    for k in range(n + 1):
        logpmf = (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
                  + k * logp + (n - k) * logq)
        cdf += math.exp(logpmf)
        for q in qs:
            if qmap[q] is None and cdf >= q:
                qmap[q] = k
    return {q: k for q, k in qmap.items()}


def roi_band(n):
    """Flat 1-unit bets at -110: profit = wins*0.909091 - losses*1."""
    q = binom_quantiles(n, BREAKEVEN, [0.05, 0.25, 0.5, 0.75, 0.95])
    band = {}
    for label, k in q.items():
        profit = k * (100.0 / 110.0) - (n - k)
        band[f"p{int(label * 100)}"] = {"wins": k, "profit_units": round(profit, 1),
                                        "roi": round(profit / n, 4)}
    return band


def main() -> int:
    bt = json.load(open(os.path.join(ROOT, "data", "backtest_summary.json")))
    strategies = []
    for s in bt.get("strategies", []):
        strategies.append({
            "id": s.get("sid", ""), "name": s.get("name", ""),
            "market": s.get("market", ""),
            "status_dev_backtest": s.get("status", ""),
            "n_dev": s.get("n", None),
            "hit_rate_dev": s.get("hit_rate", None),
            "hit_rate_ci_dev": [s.get("hit_rate_ci_lo"), s.get("hit_rate_ci_hi")],
            "required_hit_rate": s.get("required_hit_rate", None),
            "mean_units_per_bet_dev": s.get("mean_units_per_bet", None),
            "units_ci_dev": [s.get("units_ci_lo"), s.get("units_ci_hi")],
            "note": "development backtest 2011-2026 (session 68b4e431); NEVER leaderboard-eligible as a score",
        })

    divisions = [
        {"division": "Singles", "eligible": "yes", "ranking_metric":
         "benchmark-relative Brier skill (game-cluster 90% lower bound) + multiplicity adjustment",
         "gate": "G1-G8 (research/preregistration.md)", "entries": "SB-1 + controls"},
        {"division": "Game parlays", "eligible": "no — joint-evidence gate", "ranking_metric":
         "proper score on the validated joint probability", "gate":
         "needs a directly validated joint probability (n >= 500 joint outcomes) AND operator void/push rules; "
         "multiplying marginals is invalid under dependence", "entries": "none registered"},
        {"division": "Same-game parlays", "eligible": "no — joint-evidence gate", "ranking_metric":
         "proper score on the validated joint probability", "gate":
         "same as game parlays; dependence is strongest here", "entries": "none registered"},
        {"division": "Prop combos", "eligible": "no — joint-evidence gate", "ranking_metric":
         "proper score on the validated joint probability", "gate":
         "needs player-level joint model + rules; snap-count and inactives feeds first (availability gate)", "entries": "none registered"},
    ]

    controls = [
        {"id": "CTL-RANDOM", "definition": "uniform random side, flat 1 unit, seed 20261116; "
         "the pure-luck distribution is published in the removal-of-luck panel",
         "signal_score": "n/a by construction", "staking": "flat 1 unit",
         "role": "luck floor"},
        {"id": "CTL-FAV", "definition": "always take the closing favourite at the closing price, flat 1 unit",
         "signal_score": "pending prospective grading", "staking": "flat 1 unit",
         "role": "market-strength control"},
        {"id": "CTL-HOME", "definition": "always take the home team at the closing price, flat 1 unit",
         "signal_score": "pending prospective grading", "staking": "flat 1 unit",
         "role": "HFA control (2026 measured HFA is negative: b0 = -0.618)"},
    ]

    what_changed = {
        "SB-1": {
            "up": "Prospective Brier skill > 0 with 90% lower bound > 0 over >= 500 graded forecasts and the side-balance gate holds (0.35-0.65).",
            "down": "Skill point estimate < 0 at the Week-14 checkpoint (n >= 200); any G4/G7 violation; or sigma drifts > 20% from the registered 11.73.",
        }
    }

    demotion = {
        "rule": "live -> paper when any of: (a) trailing 200 graded forecasts with Brier-skill 90% lower bound < 0 at two consecutive weekly checkpoints; "
                "(b) flat-stake drawdown > 25 units; (c) feed-integrity failure in its inputs. Re-promotion needs a fresh 200-forecast run with lower bound > 0.",
        "source": "research/preregistration.md section 5 (frozen at " + REGISTRATION_COMMIT + ")",
    }

    leaderboard = {
        "meta": {
            "generated_by": "tools/run_leaderboard.py",
            "generated_at_utc": "2026-11-16T02:55:00Z",
            "registration_commit": REGISTRATION_COMMIT,
            "rule": "backtest numbers are forbidden here (brief + preregistration section 7); "
                    "signal and staking columns are never combined",
            "prospective_window": "2026 Weeks 11-18, graded at closing prices",
            "window_status": "open at Week 11 kickoff 2026-11-19; no prospective forecast is graded yet",
        },
        "divisions": divisions,
        "entries": [
            {"id": "SB-1.0.0", "name": "Shadow baseline (team strength, singles only)",
             "division": "Singles", "status": "paper (shadow)",
             "registered_at_utc": "2026-11-16T02:45:00Z", "registration_commit": REGISTRATION_COMMIT,
             "definition": "research/preregistration.md (frozen): OLS margin ratings + shrinkage total model + Normal win probability",
             "signal_columns": {"brier_skill": "pending", "lower_bound_90": "pending", "n_graded": 0},
             "staking_columns": {"scheme": "flat 1 unit", "roi": "pending", "max_drawdown": "pending"},
             "what_would_change_our_mind": what_changed["SB-1"],
             "gates": ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"]},
        ],
        "controls": controls,
        "demotion_gate": demotion,
        "divisions_ineligible_note": "Parlay and prop-combo divisions exist but carry no entries; the joint-evidence gate must clear first.",
    }

    dev_backtest = {
        "LABEL": "BACKTEST — development corpus only. These numbers may never appear on the leaderboard.",
        "corpus": "2026 REG Weeks 1-10 finals (n=148) fit window + 2011-2026 out-of-sample runs (session 68b4e431)",
        "elo_vs_market": {"elo_brier": 0.2277, "market_brier": 0.2106, "n": 4041,
                          "source": "data/backtest_summary.json; docs/STRATEGY_VALIDATION.md"},
        "strategies_development": strategies,
        "fdr_note": "all hypotheses in the development run were controlled with Benjamini-Hochberg",
        "quantified_gates": {
            "detect_55pct_at_alpha_05_power_80": 2243,
            "detect_57pct": 719,
            "detect_62pct": 164,
            "source": "session-1374049c quantified skill gates (-110 break-even 0.5238095)",
        },
    }

    luck = {
        "label": "Removal-of-luck panel — pure chance at -110, flat 1 unit, exact binomial",
        "break_even": BREAKEVEN,
        "bands": {str(n): roi_band(n) for n in (50, 100, 250, 500, 1000, 2243)},
        "reading": "A strategy's ROI is only interpretable against this band at its n. At n=100 the 5th-95th percentile "
                   "of pure luck spans roughly -15% to +23% ROI; short-run ROI cannot separate skill from variance.",
        "control_baselines": ["CTL-RANDOM (seed 20261116)", "CTL-FAV", "CTL-HOME"],
    }

    json.dump(leaderboard, open(os.path.join(ROOT, "data", "leaderboard.json"), "w"), indent=1)
    json.dump({"development": dev_backtest, "removal_of_luck": luck},
              open(os.path.join(ROOT, "data", "development_panel.json"), "w"), indent=1)
    print("leaderboard + development panel OK")
    for n in ("50", "100", "250", "2243"):
        b = luck["bands"][n]
        print(f"  luck band n={n}: p5 roi {b['p5']['roi']}, p50 {b['p50']['roi']}, p95 {b['p95']['roi']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
