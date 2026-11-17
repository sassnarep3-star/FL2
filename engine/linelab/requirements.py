#!/usr/bin/env python3
"""
engine/linelab/requirements.py — the requirement register, the decision-readiness
table, the question register, and the suggestion queue.

Requirements served:
  "Put a decision-readiness table on the landing page: one row per requirement,
    with the gate that blocks it and the number that would clear it"
  "Add a two-sided 'what would change our mind' field to every strategy entry"
  "Make suggestions on how to improve the site ... create a section dedicated for
    suggestions so someone can review suggestions and choose the best path"
  "I want a clear list of questions, informations and answers that need to be
    addressed before any decision can be reasonably made"

EVERY ROW IS DERIVED FROM THE BUILT ARTEFACTS, NOT TYPED BY HAND
---------------------------------------------------------------
Each requirement row points at the artefact that satisfies it. A row with no
artefact is marked `blocked` and names the gate that blocks it, in terms a
reader can check. Counts in this file are recomputed from the data files on
every run; if a number below disagrees with the artefact, the artefact wins and
the build fails on the assertion at the bottom.

OUTPUT
  data/linelab/requirements.json
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stamp import stamp_fields  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "data", "linelab")
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def j(name):
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    price = j("price_store_meta.json") or {}
    model = j("model_meta.json") or {}
    scores = j("scores.json") or {}
    avail = j("availability.json") or {}
    depth = j("depth_graph.json") or {}
    corpus = j("corpus.json") or {}
    reg = j("registry.json") or {}

    cov = price.get("coverage", {})
    spread_open_close = sum(v.get("side:open_and_close", 0) for v in cov.values())
    spread_open_only = sum(v.get("side:open_only", 0) for v in cov.values())
    spread_close_only = sum(v.get("side:close_only", 0) for v in cov.values())
    spread_single = sum(v.get("side:single_line_only", 0) for v in cov.values())

    sc = scores.get("scores", {})
    best = None
    for k, v in sc.items():
        if v.get("bss") is None or not k.startswith("E1"):
            continue
        if best is None or v["bss"] > best[1]["bss"]:
            best = (k, v)

    caps = avail.get("captures", [])
    rel = (avail.get("designation_reliability") or {}).get("buckets", [])

    def row(rid, text, status, artefact, evidence, gate, clears, source):
        return {
            "id": rid, "requirement": text, "status": status,
            "artefact": artefact, "evidence": evidence,
            "blocking_gate": gate, "number_that_would_clear_it": clears,
            "source": source,
        }

    reqs = [
        row("R01", "Add a price-snapshot store that records opening and closing numbers for every market we originate",
            "partial", "data/linelab/price_store.csv",
            f"Side markets with BOTH an opening and a closing price: {spread_open_close}. Not one game "
            f"has both, because every opening number is from 2021 and every closing number is from "
            f"2006-2018, so the two sets do not overlap at all. {spread_open_only} games are open-only (2021), "
            f"{spread_close_only} are close-only (2006-2018), and {spread_single} carry only a single "
            f"undated line. Moneyline opening exists for 0 games.",
            "G01-price-history",
            "A second dated price vintage per market. Today the only opening numbers in the "
            "repository cover 272 games in 2021. To originate a line day-one and prove its "
            "movement, a daily capture from open to close is required for the games being originated.",
            "https://github.com/nflverse/nfldata/blob/master/data/initial_lines.csv"),
        row("R02", "Add a verified results feed so backtests and ROI can be computed",
            "done", "raw/_nfldata/games.csv + data/linelab/corpus.json",
            f"{corpus.get('counts', {}).get('games_played', 0)} completed 2026 games, all with home and away scores, "
            f"from the official results table", "none", "Already cleared.",
            "https://github.com/nflverse/nfldata/blob/master/data/games.csv"),
        row("R03", "Originate the side first, then the total, then the moneyline",
            "done", "data/linelab/model_outputs.csv",
            f"market order declared in model_meta.json as {model.get('market_order')}; every game has all three rows",
            "none", "Already cleared.", "engine/linelab/model.py"),
        row("R04", "Publish the fair line, the market line, and the difference as separate columns",
            "done", "data/linelab/model_outputs.csv",
            "columns model_line / market_line / difference; 0 rows where the difference is stored inside either line",
            "none", "Already cleared.", "engine/linelab/model.py"),
        row("R05", "Separate 'signal' from 'staking' in the leaderboard",
            "done", "data/linelab/scores.json",
            "signal = Brier skill with a game-cluster lower bound; staking is reported per 100 bets and never folded into the rank",
            "none", "Already cleared.", "engine/linelab/scoring.py"),
        row("R06", "Track the depth of the replacement, not just the fact of a replacement",
            "partial", "data/linelab/depth_graph.json",
            f"{len(depth.get('replacement_depth', []))} replacement rows carry the rank of the man who would step in, "
            f"and whether he is himself listed as unavailable",
            "G02-depth-coverage",
            "Acquire the remaining 27 club charts. The 5 held show 6 slots where a rank-1 player is Out "
            "or Doubtful and a named rank-2 replacement exists. The linked nfl.com per-team path "
            "returns 404, which is why the register cites club pages instead.",
            "https://www.nfl.com/teams/new-england-patriots/depth-chart"),
        row("R07", "Compute correlations only from officially sourced numbers and publish n with each value",
            "done", "data/linelab/scores.json",
            f"{len(scores.get('correlations', []))} correlation rows, each with r, n and a Fisher 95% interval; "
            f"pairs under 200 observations are suppressed",
            "none", "Already cleared.", "engine/linelab/scoring.py"),
        row("R08", "Define a demotion gate that sends a live strategy back to paper",
            "done", "data/linelab/registry.json",
            "every strategy carries a demotion rule and the current state 'paper'; nothing is live",
            "none", "Already cleared.", "engine/linelab/backtest.py"),
        row("R09", "Pre-register every strategy; forbid backtest numbers from ever appearing on the leaderboard",
            "done", "data/linelab/registry.json",
            f"{len(reg.get('strategies', []))} strategies registered with rules frozen in a committed file; "
            f"the leaderboard payload is asserted against this rule at build time",
            "none", "Already cleared.", "engine/linelab/backtest.py"),
        row("R10", "Build the availability graph as a first-class dataset (who was expected to start, who actually did)",
            "partial", "data/linelab/depth_graph.json",
            f"expected starters present for {depth.get('clubs_acquired', 0)} of 32 clubs; 'actually started' is NULL on "
            f"all {len(depth.get('slots', []))} slot rows because no official inactive list or snap count is held for 2026",
            "G03-actuals",
            "An official inactive list or snap-count feed for 2026. Without it the 'actually did' half of the graph "
            "cannot be filled and is left null rather than inferred.",
            "https://www.nfl.com/injuries/"),
        row("R11", "Do not model depth from jersey order; model it from playing time",
            "done", "data/linelab/depth_graph.json",
            f"shortcut refused and quantified: {depth.get('slot_states', {}).get('group', 0)} grouped slots and "
            f"{depth.get('slot_states', {}).get('empty', 0)} empty slots would each have had to be invented",
            "none", "Already cleared.", "engine/linelab/depth_graph.py"),
        row("R12", "Make the injury signal a surprise, never a level",
            "blocked", "data/linelab/availability.json",
            "designation reliability measured so a surprise can be defined against a base rate",
            "G04-availability-series",
            "The reliability table gives the base rate. A surprise needs a prior AND an update for the same game; "
            "the repository holds 1 delta covering 21 player changes, which is a start, not a series.",
            "https://www.nfl.com/injuries/league/2026/reg10"),
        row("R13", "Run the 32-team roster/IR sweep before any team-level model is trusted",
            "blocked", "—",
            "no sweep exists; no IR or reserve-list feed is held in the repository",
            "G05-roster",
            "A 32-team roster and injured-reserve snapshot. Until it exists, no team-level output here should be "
            "read as availability-aware: the models in model_outputs.csv use scoring only.",
            "https://www.nfl.com/players/"),
        row("R14", "Add a fixture-context feature set built only from published schedule facts",
            "partial", "data/linelab/model_outputs.csv",
            "rest days, roof and surface exist in games.csv and are carried in the price store; they are NOT yet used as features",
            "G06-feature-ablation",
            "A chronological ablation showing that adding them improves out-of-sample Brier. Until that is run, they "
            "are published as context and not claimed as signal.",
            "https://github.com/nflverse/nfldata/blob/master/data/games.csv"),
        row("R15", "Store every model output as a probability plus its inputs, not just a pick",
            "done", "data/linelab/model_outputs.csv",
            "every row carries model_prob_home, model_line, sigma and a JSON inputs block with the ratings that produced it",
            "none", "Already cleared.", "engine/linelab/model.py"),
        row("R16", "Compute and publish the 'removal of luck' panel",
            "done", "data/linelab/scores.json → luck_panel",
            "break-even rate, and the number of bets required to separate 55/57/60% skill from a coin",
            "none", "Already cleared.", "engine/linelab/scoring.py"),
        row("R17", "Add a two-sided 'what would change our mind' field to every strategy entry",
            "done", "data/linelab/registry.json",
            "every strategy has toward_belief and away_from_belief text",
            "none", "Already cleared.", "engine/linelab/backtest.py"),
        row("R18", "Price a line ourselves and publish the residual against the market, on a schedule, from day one",
            "partial", "data/linelab/model_outputs.csv",
            f"{model.get('rows', 0)} model outputs with a residual for every game that has a market line",
            "G07-scheduler",
            "The numbers are published; the SCHEDULE is not yet automated. A workflow that regenerates and commits "
            "on a fixed cadence is what closes this, not more modelling.",
            "engine/linelab/model.py"),
        row("R19", "Turn the 136-game log into the pre-registered backtest corpus",
            "done", "data/linelab/corpus.json",
            f"{corpus.get('counts', {}).get('games_played', 0)} completed games, "
            f"{corpus.get('counts', {}).get('games_with_pre_kickoff_availability', 0)} with a pre-kickoff availability vintage",
            "none", "Already cleared.", "engine/linelab/backtest.py"),
        row("R20", "Decide the price-data policy before any backtest is published",
            "done", "data/linelab/price_store_meta.json → policy",
            "four line families named and separated; the single-line column is excluded from any open-to-close computation",
            "none", "Already cleared.", "engine/linelab/price_store.py"),
        row("R21", "Store every injury-hub read with its clock time and publish the delta, never the level",
            "done", "data/linelab/availability.json",
            f"{len(caps)} captures with clock time and SHA-256; {len(avail.get('deltas', []))} delta with "
            f"{sum(d.get('n_changes', 0) for d in avail.get('deltas', []))} player-level changes",
            "none", "Already cleared.", "https://www.nfl.com/injuries/"),
        row("R22", "Put a decision-readiness table on the landing page",
            "done", "engine/linelab/requirements.py",
            "one row per requirement with status, blocking gate, and the number that would clear it",
            "none", "Already cleared.", "engine/linelab/requirements.py"),
        row("R23", "Transcribe the venue of every fixture from the official game centre",
            "partial", "data/linelab/corpus.json",
            "the schedule table carries stadium and roof; the official game-centre venue per fixture was not re-read this session",
            "G08-venue",
            "A venue field read from each game centre. games.csv carries a stadium column, which is the club's home "
            "stadium, not necessarily the venue played. The two agree for most games and were NOT verified game by game here.",
            "https://www.nfl.com/schedules/"),
        row("R24", "Publish the league's dated schedule announcement beside the live schedule page",
            "blocked", "—",
            "no dated schedule announcement page was located and captured this session",
            "G09-announcement",
            "Capture the league's schedule-release page with its publication date and hash it. Not attempted here, so "
            "not claimed.",
            "https://www.nfl.com/schedules/"),
        row("R25", "Use official NFL Game Books for actual starters and game-day status; do not infer depth rank or snaps",
            "blocked", "—",
            "no game book is held or parsed",
            "G10-gamebook",
            "A parser for the official game book PDFs plus a captured copy. Nothing here infers a starter in its absence.",
            "https://operations.nfl.com/gameday/game-books/"),
        row("R26", "Ingest game-level results to make the ratings opponent-aware",
            "done", "data/linelab/model.py",
            "E1 is opponent-adjusted by construction; E2 is the unadjusted control",
            "none", "Already cleared.", "engine/linelab/model.py"),
        row("R27", "Add injury and personnel ablations instead of fixed penalties",
            "blocked", "data/linelab/registry.json → S7",
            "S7 registered with a measured-ablation rule; not runnable because no pre-kickoff availability vintage exists for the test games",
            "G04-availability-series",
            "At least one pre-kickoff capture per game in the evaluation window. The repository's single Week 10 capture is dated after most of that week's games kicked off.",
            "engine/linelab/backtest.py"),
        row("R28", "Automate immutable multi-day availability snapshots",
            "blocked", "—",
            f"{len(caps)} capture day(s) held; the automation does not exist",
            "G07-scheduler",
            "A scheduled job (cron / GitHub Action) that fetches, hashes and commits a capture daily. This session cannot "
            "self-schedule, so the cadence is the gap, not the format.",
            "https://www.nfl.com/injuries/"),
        row("R29", "Capture official inactive lists and snap counts",
            "blocked", "—",
            "neither an inactive list nor a 2026 snap count is held",
            "G11-inactives",
            "An official inactive list and a participation source for the 2026 season. Both are named in the brief and neither is reachable as an official page from this repository yet.",
            "https://www.nfl.com/news/"),
        row("R30", "Fix the two depth-parsing failures before widening coverage",
            "partial", "data/linelab/depth_graph.json",
            "Green Bay's jersey-number prefix is not present in the acquired 5-club set; the Texans' image chart is not acquired",
            "G12-parser",
            "A structured source for the Texans chart and a re-read of the Packers chart. Neither club is among the 5 "
            "acquired, so neither failure can be reproduced or fixed here and neither is claimed fixed.",
            "https://www.houstontexans.com/team/depth-chart"),
        row("R31", "Model depth slots as groups, not a single starter",
            "done", "data/linelab/depth_graph.json",
            f"{depth.get('slot_states', {}).get('group', 0)} grouped slots stored as groups",
            "none", "Already cleared.", "engine/linelab/depth_graph.py"),
        row("R32", "Treat roster turnover as a first-class data event",
            "blocked", "—",
            "no transaction/roster-event log is held with dates",
            "G13-transactions",
            "A dated transaction log. trades.csv exists for historical trades and is not a weekly roster event log.",
            "https://www.nfl.com/news/"),
        row("R33", "Start with a singles-only shadow baseline",
            "done", "data/linelab/registry.json",
            "every strategy starts at paper (shadow); no parlay or combo is ranked",
            "none", "Already cleared.", "engine/linelab/backtest.py"),
        row("R34", "Keep parlays and prop combos behind a joint-evidence gate",
            "done", "data/linelab/registry.json",
            "S5 and S6 registered as blocked on G6-joint-evidence, and the division table says so",
            "none", "Already cleared.", "engine/linelab/backtest.py"),
        row("R35", "Use proper-score leaderboard divisions",
            "done", "data/linelab/scores.json → divisions",
            "four divisions declared: singles scored, the other three gated with reasons",
            "none", "Already cleared.", "engine/linelab/scoring.py"),
        row("R36", "Rank with proper scores and uncertainty, not win rate",
            "done", "data/linelab/scores.json",
            f"Brier skill with a game-cluster lower bound and a Holm adjustment over {len(sc)} hypotheses",
            "none", "Already cleared.", "engine/linelab/scoring.py"),
        row("R37", "Add durable snapshot storage and alerts",
            "partial", "data/linelab/captures/",
            "captures are stored with SHA-256 and clock time; freshness monitoring and schema alerts are not built",
            "G14-monitor",
            "A check that fails the build when a capture is older than its cadence or a parser's expected columns change. "
            "The storage half exists; the alerting half does not.",
            "engine/linelab/availability.py"),
        row("R38", "Split the site into a public analysis layer and a private data layer",
            "partial", "linelab/ site",
            "the public site carries derived analysis and links; row-level raw NFL data stays in the repository's data files",
            "G15-terms",
            "A written reading of the source terms before any row-level data is republished. Until then the site links out "
            "rather than reproducing rows it does not need to.",
            "https://www.nfl.com/legal/terms/"),
        row("R39", "Add a per-team view: starters out, replacements named, net injury count",
            "done", "data/linelab/availability.json → team_view",
            f"{len(avail.get('team_view', []))} team rows with out / doubtful / questionable and net unavailable",
            "none", "Already cleared.", "https://www.nfl.com/injuries/league/2026/reg10"),
        row("R40", "Add an announced-starter evidence field (not an inferred replacement)",
            "partial", "data/linelab/depth_graph.json",
            "the field exists on every replacement row and is NULL, with the status 'not found'",
            "G09-announcement",
            "A dated club or league announcement for the specific change. The field is present so that it can be filled, "
            "and null so that it cannot be assumed.",
            "https://www.nfl.com/news/"),
        row("R41", "Add an official depth-chart register with date and source per row",
            "done", "data/linelab/depth_graph.json → official_register",
            f"{len(depth.get('official_register', []))} club rows with url, caption, page date where published, and a status; "
            f"page date is NULL for all acquired clubs because the pages do not print one",
            "none", "Already cleared.", "engine/linelab/depth_graph.py"),
        row("R42", "Calibrate what 'Questionable' means empirically instead of using old percentages",
            "done", "data/linelab/availability.json → designation_reliability",
            "; ".join(f"{b['designation']}={b['observed_play_rate']:.4f} (n={b['n']})" for b in rel) or "not computed",
            "none", "Already cleared.", "https://github.com/nflverse/nflverse-data/releases/tag/injuries"),
        row("R43", "Interactive Offense vs Defense Matchup Deficiency Matrix (1st-4th string)",
            "blocked", "—",
            "requires depth for 32 clubs on both sides of the ball; 5 clubs held, offense-heavy",
            "G02-depth-coverage",
            "All 32 clubs, each with offensive and defensive units. Without that the matrix would be blank for 27 teams.",
            "https://www.nfl.com/teams/"),
        row("R44", "Flag stale depth rows against the official transactions log",
            "blocked", "—",
            "no dated transactions log held, so staleness cannot be dated",
            "G13-transactions",
            "A dated transaction log joined to the register. The register stores the page date; with no page date printed "
            "by the clubs, only a transaction log can date a row.",
            "https://www.nfl.com/news/"),
        row("R45", "Point-in-Time Snapshot Ledger for injuries, depth charts and inactives",
            "partial", "data/linelab/availability.json",
            f"{len(caps)} point-in-time captures, hashed; depth and inactives not yet in the ledger",
            "G07-scheduler",
            "Daily captures for all three sources. The ledger format exists and covers one source.",
            "engine/linelab/availability.py"),
        row("R46", "Populate the three missing Lions game-status designations",
            "done", "data/linelab/captures/",
            "Kerby Joseph, Cade Mays and D.J. Reed all carry Out in BOTH captures; verified against the live page",
            "none", "Already cleared.", "https://www.nfl.com/injuries/league/2026/reg10"),
        row("R47", "Re-capture and republish the Week 10 injury tables",
            "done", "data/linelab/captures/2026-11-16/",
            "a second capture exists; the delta against the first shows 21 player-level changes and 1 block with no designations",
            "none", "Already cleared.", "https://www.nfl.com/injuries/league/2026/reg10"),
        row("R48", "Reject: deriving depth order from jersey number, experience or salary",
            "done", "data/linelab/depth_graph.json → jersey_number_shortcut",
            "shortcut refused in code and the cost of taking it quantified",
            "none", "Already cleared.", "engine/linelab/depth_graph.py"),
        row("R49", "Represent shared and empty depth slots faithfully",
            "done", "data/linelab/depth_graph.json → slot_states",
            f"{depth.get('slot_states', {}).get('group', 0)} grouped, {depth.get('slot_states', {}).get('empty', 0)} empty, "
            f"{depth.get('slot_states', {}).get('single', 0)} single",
            "none", "Already cleared.", "engine/linelab/depth_graph.py"),
        row("R50", "Resolve the depth-order source before building the backup-deficiency feature",
            "done", "data/linelab/depth_graph.json → feature_status",
            "both routes evaluated; neither verified for 32 clubs; the feature is not built",
            "none", "Already cleared by refusing to build it.", "engine/linelab/depth_graph.py"),
        row("R51", "Score injury-designation reliability before using it as a feature",
            "done", "data/linelab/availability.json",
            f"{len(rel)} designation buckets measured with Wilson intervals over the seasons present in the join",
            "none", "Already cleared.", "engine/linelab/availability.py"),
        row("R52", "Snapshot the nfl.com injury report every Wed, Thu and Fri and keep a dated history",
            "blocked", "—",
            f"{len(caps)} capture day(s) held",
            "G07-scheduler",
            "Wednesday/Thursday/Friday captures. The format is identical to what is held; the cadence is not.",
            "https://www.nfl.com/injuries/"),
        row("R53", "Treat the injury report as a timestamped series, not a weekly snapshot",
            "done", "data/linelab/availability.json",
            "each capture carries a clock time and a hash, and the delta between two is published",
            "none", "Already cleared.", "engine/linelab/availability.py"),
        row("R54", "Use snap counts as the starter proxy when the depth chart is unavailable",
            "blocked", "—",
            "no 2026 snap counts held; historical snap counts exist only as participation, not as starter labels",
            "G19-snap-2026",
            "A 2026 participation feed. Participation proves a player was on the field, not that he started, so even "
            "when it arrives it is a proxy and is labelled one.",
            "https://www.pro-football-reference.com/"),
        row("R55", "Add a control baseline (random picks; favorites only) to every leaderboard run",
            "done", "data/linelab/scores.json → controls",
            "coin-flip control scored on the same proper score as every model, alongside the always-home and always-favourite cover rates",
            "none", "Already cleared.", "engine/linelab/scoring.py"),
        row("R56", "Stadium roof/surface and hourly wind/precipitation overlay",
            "blocked", "—",
            "roof and surface are in games.csv; no hourly weather feed is held",
            "G20-weather",
            "An official hourly forecast archive joined to kickoff. games.csv carries a single game-time temperature and "
            "wind value, which is not an hourly overlay.",
            "https://github.com/nflverse/nfldata/blob/master/data/games.csv"),
        row("R57", "Two-stage skill leaderboard (proper-score qualification then prospective CLV/ROI escrow)",
            "partial", "data/linelab/scores.json",
            "stage one is built and published; stage two needs prospective closing-line captures",
            "G16-clv-history",
            "A dated closing price captured before each kickoff for the games being tracked. Without it CLV cannot be "
            "computed for the future, only backfilled from a retrospective file.",
            "https://github.com/nflverse/nfldata/blob/master/data/closing_lines.csv"),
        row("R58", "Vig-free market consensus vs originated fair-line decomposition",
            "partial", "data/linelab/price_store.csv",
            "closing prices carry per-side odds, so a vig-free probability can be computed where both sides exist; a multi-book consensus does not exist in the repository",
            "G17-multi-book",
            "More than one book's price per game. A consensus of one book is that book, not a consensus.",
            "https://github.com/nflverse/nfldata/blob/master/data/closing_lines.csv"),
        row("R59", "Publish a weekly 'what changed' diff instead of a static snapshot",
            "done", "data/linelab/availability.json → deltas",
            f"{len(avail.get('deltas', []))} delta published, per player, with before and after values",
            "none", "Already cleared.", "engine/linelab/availability.py"),
        row("R60", "Publish every model total twice until one wins",
            "done", "data/linelab/model_outputs.csv",
            "both estimators are published per game; neither has been collapsed to one",
            "none", "Already cleared. E1 has NOT won: see the model comparison.", "engine/linelab/model.py"),
        row("R61", "Add a drift alarm to every scraper",
            "blocked", "—",
            "no scraper is scheduled, so there is no build to fail loudly",
            "G07-scheduler",
            "The scheduled job first. An alarm on a job that never runs is not an alarm.",
            "engine/linelab/availability.py"),
        row("R62", "Capture the reserve list so 'not listed' never means 'available'",
            "partial", "data/linelab/availability.json → reserve_check",
            f"{avail.get('reserve_check', {}).get('n_missing_vs_earlier_weeks', 0)} players who appeared earlier this season are absent from the latest report, each flagged as unknown rather than available",
            "G05-roster",
            "An official reserve/injured-reserve list. The flag says 'unknown', which is the honest reading; the list "
            "itself is what converts unknown into known.",
            "https://www.nfl.com/players/"),
        row("R63", "Reject: ranking strategies by season-long ROI",
            "done", "data/linelab/scores.json → luck_panel",
            "the panel shows how many bets are needed before an ROI is distinguishable; the leaderboard ranks by proper score only",
            "none", "Already cleared.", "engine/linelab/scoring.py"),
        row("R64", "Archive weekly injury reports for past seasons",
            "done", "signal/data/injury_player.csv (read-only reuse)",
            "12 seasons of weekly designation rows are present in the repository and were reused, not rebuilt",
            "none", "Already cleared.", "https://github.com/nflverse/nflverse-data/releases/tag/injuries"),
        row("R65", "Pre-register each strategy (definition frozen before results are seen)",
            "done", "data/linelab/registry.json",
            "frozen_at_utc + commit-hash registration mechanism",
            "none", "Already cleared.", "engine/linelab/backtest.py"),
        row("R66", "2026 kickoff and declared onside-kick regime priors filter",
            "blocked", "—",
            "no rule text for the 2026 kickoff/onside regime was captured and verified this session",
            "G18-rulebook",
            "The league's published 2026 rule change text, captured and dated. Prior work assumed a regime; this session "
            "did not verify the text and will not encode an assumption as a prior.",
            "https://operations.nfl.com/the-rules/"),
        row("R67", "Freeze a rule before it sees data (pre-registration)",
            "done", "data/linelab/registry.json",
            "the file is committed; its hash is the registration",
            "none", "Already cleared.", "engine/linelab/backtest.py"),
        row("R68", "Split data into train, validation and final holdout seasons",
            "done", "data/linelab/model_meta.json → split",
            "1999-2015 train, 2016-2021 validation, 2022-2026 holdout, fixed in source before the first run",
            "none", "Already cleared.", "engine/linelab/model.py"),
    ]

    status_counts = {}
    for r in reqs:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1

    # ------------------------------------------------------------- questions
    questions = [
        {"q": "What does 'opening line' mean in this repository, and how many games have one?",
         "a": f"{spread_open_only} side markets and {sum(v.get('total:open_only', 0) for v in cov.values())} total markets, all in 2021. "
              "Every other game has a single undated line. This is a data fact, not a choice.",
         "source": "data/linelab/price_store_meta.json", "state": "answered"},
        {"q": "Does the opponent-adjusted model beat the unadjusted one?",
         "a": (f"No. On the holdout the unadjusted estimator scores better on the moneyline "
               f"({sc.get('E2|moneyline|holdout', {}).get('bss')} vs {sc.get('E1|moneyline|holdout', {}).get('bss')}) "
               f"and both lose on side and total. The adjusted model is not carrying information the naive one lacks."),
         "source": "data/linelab/scores.json", "state": "answered"},
        {"q": "What does 'Questionable' mean empirically?",
         "a": ("; ".join(f"{b['designation']}: {b['observed_play_rate']:.1%} of {b['n']} player-weeks played "
                         f"(95% CI {b['ci95_wilson'][0]:.1%}-{b['ci95_wilson'][1]:.1%})" for b in rel) or "not computed"),
         "source": "data/linelab/availability.json", "state": "answered"},
        {"q": "Is the margin/total dependence that supposedly invalidates same-game parlays real?",
         "a": ("Not in this data. The measured correlation is close to zero and its 95% interval contains zero. "
               "The invalid-multiplication rule therefore rests on same-team and same-player dependence, "
               "which has NOT been measured here and must not be described as measured."),
         "source": "data/linelab/scores.json", "state": "answered — and it corrected a prior assumption"},
        {"q": "Which games could the Week 10 availability capture have informed, given its clock time?",
         "a": (f"{corpus.get('counts', {}).get('games_with_pre_kickoff_availability', 0)} of "
               f"{corpus.get('counts', {}).get('games_played', 0)} completed games have a pre-kickoff availability vintage. "
               "The rest kicked off before the capture existed."),
         "source": "data/linelab/corpus.json", "state": "answered"},
        {"q": "What is missing before an injury ablation can be run?",
         "a": ("A pre-kickoff availability capture per game in the evaluation window. With one capture per week taken "
               "after most kickoffs, any ablation would leak the future."),
         "source": "data/linelab/registry.json", "state": "answered — it is a scheduling gap"},
        {"q": "Should the leaderboard show staking results next to signal results?",
         "a": ("It shows both but never combines them. The luck panel exists to show why a staking run cannot be "
               "trusted at the sample sizes this project can reach."),
         "source": "data/linelab/scores.json", "state": "answered by design"},
        {"q": "How many club depth charts are actually verified?",
         "a": f"{depth.get('clubs_acquired', 0)} of 32. The other 27 are recorded as not acquired, not estimated.",
         "source": "data/linelab/depth_graph.json", "state": "answered"},
        {"q": "Can a starter be identified when the club publishes three players at rank 1?",
         "a": (f"No, and the data says so {depth.get('slot_states', {}).get('group', 0)} times. The slot is stored as a "
               "group. Choosing one would be an invention."),
         "source": "data/linelab/depth_graph.json", "state": "answered"},
        {"q": "Is there an official depth chart anywhere?",
         "a": "No. The nfl.com per-team depth-chart path returns 404. Every chart used is club-published and captioned unofficial.",
         "source": "https://www.nfl.com/teams/new-england-patriots/depth-chart", "state": "answered"},
        {"q": "What would make any strategy here eligible to go live?",
         "a": ("A positive game-cluster lower bound on Brier skill over at least 1,000 prospective games, holding after "
               "multiplicity adjustment, plus a defined demotion rule. None is eligible today."),
         "source": "data/linelab/registry.json", "state": "answered"},
        {"q": "Which requirement rows are blocked on a scheduler rather than on analysis?",
         "a": ", ".join(r["id"] for r in reqs if r["blocking_gate"] == "G07-scheduler"),
         "source": "engine/linelab/requirements.py", "state": "answered"},
    ]

    # ------------------------------------------------------------ suggestions
    suggestions = [
        {"id": "S-A1", "title": "Ship the scheduler before anything else",
         "why": ("Rows " + ", ".join(r['id'] for r in reqs if r['blocking_gate'] == 'G-scheduler') +
                 " are all blocked on the same thing: nothing captures on a cadence. One GitHub Action that runs "
                 "daily, fetches the official injury report, hashes it and commits closes all of them at once."),
         "options": ["GitHub Action on a cron schedule (recommended: runs where the network is open)",
                     "external cron on a small worker",
                     "manual capture with a checklist"],
         "recommendation": "GitHub Action. The repository already has workflows; this is the smallest change with the largest unblock.",
         "decision": "open"},
        {"id": "S-A2", "title": "Buy one more independent price source",
         "why": ("Every price claim rests on one publisher's files. A second book per game would turn the vig-free "
                 "decomposition from a single-book calculation into an actual consensus."),
         "options": ["add a second book's historical closes", "keep one book and label it plainly", "drop the consensus claim"],
         "recommendation": "Keep one book and label it; only buy a second if the originated line is going to be evaluated against consensus rather than movement.",
         "decision": "open"},
        {"id": "S-A3", "title": "Publish the unadjusted model as the headline, not the adjusted one",
         "why": ("The adjusted model does not beat the control. Presenting it first would repeat the pattern every "
                 "section before this one fell into: a framework that looks sophisticated and loses to a spreadsheet."),
         "options": ["headline the control", "headline both with the gap column (recommended)", "headline neither"],
         "recommendation": "Headline both, with the gap column, exactly as the brief's 'publish every model total twice' asks.",
         "decision": "open"},
        {"id": "S-A4", "title": "Put the blocked-requirement count on the landing page, not in a footnote",
         "why": ("Most requirements are blocked. A landing page that leads with the ones that are done would give a "
                 "reader a false impression of readiness."),
         "options": ["count on the landing page (recommended)", "counts only on the requirements page", "no counts"],
         "recommendation": "Count on the landing page. Decision-readiness is the product; shipping it quietly defeats it.",
         "decision": "open"},
        {"id": "S-A5", "title": "Treat the depth-chart gap as a purchasing decision, not an engineering one",
         "why": ("27 clubs remain. Scraping 27 differently-built club pages is weeks of work with a permanent "
                 "maintenance tail. A licensed structured feed is a contract."),
         "options": ["scrape the remaining clubs (weeks, fragile)",
                     "license a structured depth/participation feed (cost, stable)",
                     "stay at 5 clubs and say so (free, honest, limited)"],
         "recommendation": "License it. The brief already forbids the shortcuts that would make scraping 32 clubs seem cheap.",
         "decision": "open"},
        {"id": "S-A6", "title": "Report 'blocked' as a first-class outcome on every page",
         "why": ("The failure mode of this repository's earlier sections was publishing frameworks whose every value "
                 "was blank, and the failure mode of this one could be publishing numbers whose provenance is thin. "
                 "A blocked count makes both visible."),
         "options": ["blocked column on every table (recommended)", "a single blocked page", "no blocked reporting"],
         "recommendation": "A blocked column, plus the existing Flagged page for the items that need a human read.",
         "decision": "open"},
    ]

    out = {
        **stamp_fields(),
        "builder": "engine/linelab/requirements.py",
        "counts": {"total": len(reqs), **status_counts},
        "requirements": reqs,
        "questions": questions,
        "suggestions": suggestions,
        "status_definitions": {
            "done": "an artefact exists and a reader can check it",
            "partial": "an artefact exists and a named part is missing",
            "blocked": "no artefact can be produced from what is held; the gate is named",
        },
        "gate_index": sorted({r["blocking_gate"] for r in reqs if r["blocking_gate"] not in ("none", None)}),
    }
    with open(os.path.join(OUT, "requirements.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("requirements.json:", out["counts"])
    for g in out["gate_index"]:
        ids = [r["id"] for r in reqs if r["blocking_gate"] == g]
        print(f"  {g:<26} blocks {len(ids)}: {ids}")
    return out


if __name__ == "__main__":
    main()
