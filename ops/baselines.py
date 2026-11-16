#!/usr/bin/env python3
"""Control baselines for every leaderboard run (requirement: 'Add a control baseline
(random picks; favorites only) to every leaderboard run').

Two baselines on the verified results corpus:

1. random50   — seeded pseudo-random side pick per game (seed frozen in the output).
2. favourite  — pick the closing-spread favourite in every game. Closing lines come
                from the nflverse snapshot (T3 aggregated market data, labelled
                market_data_unverified per ops/price_policy.md P2/P4) and are used only
                to define the pick rule and break-even context, never as a statistical
                input to a gate.

Sign convention P4 is asserted: favourite cover rate must sit in a plausible band.
"""
from __future__ import annotations

import csv
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEED = 20261116


def main() -> None:
    feed = list(csv.DictReader(open(os.path.join(HERE, "data", "results", "results_2026_reg.csv"))))
    finals = [r for r in feed if r["status"] == "final" and r["away_pts"] and r["home_pts"]]

    lines = {}
    for r in csv.DictReader(open(os.path.join(ROOT, "raw", "games.csv"))):
        if r["season"] == "2026" and r["game_type"] == "REG" and r["spread_line"]:
            lines[r["game_id"]] = float(r["spread_line"])

    fav_games = [r for r in finals if r["game_id"] in lines]
    if not fav_games:
        raise SystemExit("no games with closing lines")

    # P4 assertion: favourite cover rate must be plausible
    covers = 0.0
    fav_wins = 0
    for r in fav_games:
        s = lines[r["game_id"]]
        hm = int(r["home_pts"]) - int(r["away_pts"])
        fav_is_home = s > 0
        fav_margin = hm if fav_is_home else -hm
        if fav_margin > abs(s):
            covers += 1
        elif fav_margin == abs(s):
            covers += 0.5
        if fav_margin > 0:
            fav_wins += 1
    rate = covers / len(fav_games)
    if not (0.40 < rate < 0.60):
        raise SystemExit(f"favourite cover rate {rate:.3f} outside plausible band - sign convention broken (P4)")

    # favourites-only Brier (pick prob 0.5 = no-skill pricing of the pick itself)
    b = 0.0
    for r in fav_games:
        s = lines[r["game_id"]]
        hm = int(r["home_pts"]) - int(r["away_pts"])
        fav_is_home = s > 0
        fav_margin = hm if fav_is_home else -hm
        won = (fav_margin > 0)
        b += (0.5 - (1.0 if won else 0.0)) ** 2

    # random baseline with frozen seed
    rng = random.Random(SEED)
    rand_correct = 0
    for r in finals:
        pick_home = rng.random() < 0.5
        home_won = int(r["home_pts"]) > int(r["away_pts"])
        rand_correct += int(pick_home == home_won)

    out = {
        "seed": SEED,
        "corpus_n": len(finals),
        "favourite_baseline": {
            "n_games": len(fav_games),
            "market_tier": "T3 (nflverse closing spread; market_data_unverified per price policy P2)",
            "favourite_straight_up_wins": fav_wins,
            "favourite_straight_up_rate": round(fav_wins / len(fav_games), 4),
            "favourite_cover_rate": round(rate, 4),
            "brier_pick_prob_0.5": round(b / len(fav_games), 4),
        },
        "random_baseline": {
            "n_games": len(finals),
            "seed": SEED,
            "picks_correct": rand_correct,
            "rate": round(rand_correct / len(finals), 4),
            "expected_rate": 0.5,
            "note": "coin-flip picks with frozen seed; every leaderboard run must include this control",
        },
    }
    path = os.path.join(HERE, "data", "baselines_2026.json")
    json.dump(out, open(path, "w"), indent=1)
    fb, rb = out["favourite_baseline"], out["random_baseline"]
    print(f"baselines: favourite SU {fb['favourite_straight_up_wins']}/{fb['n_games']} = "
          f"{fb['favourite_straight_up_rate']}, cover {fb['favourite_cover_rate']}, "
          f"Brier {fb['brier_pick_prob_0.5']}")
    print(f"random (seed {SEED}): {rb['picks_correct']}/{rb['n_games']} = {rb['rate']}")
    print("wrote", path)


if __name__ == "__main__":
    main()
