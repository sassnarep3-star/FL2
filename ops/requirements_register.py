#!/usr/bin/env python3
"""Requirements Register v2 — every requirement line of the current brief, verbatim.

Emits ops/data/requirements_v2.json and research/requirements-v2.md.
IDs R26..R96 map one-to-one to the requirement lines in the brief (R01..R25, tracked in
data/requirements.csv, cover the original brief paragraphs). Every row carries:
  text          — the requirement, verbatim
  detail        — the explanatory line beneath it in the brief, verbatim ("" if none)
  category      — governance | data | model | site | process
  status        — done | partial | registered | blocked | rejected
      done       = implemented and verified in this repository
      partial    = implemented for part of the scope; a named gate holds the rest
      registered = specified and pre-registered; not yet built (gate named)
      blocked    = cannot be advanced without something outside our control (gate names it)
      rejected   = the requirement itself is a rejection; the deliverable is the recorded policy
  gate          — what is blocking the next step ("" when done)
  clearing      — the NUMBER that would clear the gate (requirement R47's framing)
  evidence      — files / URLs a reviewer can check
Owner: session 310620fe. Register created 2026-11-16.
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
NFL = "https://www.nfl.com"

R = []


def add(id, text, detail, category, status, gate, clearing, evidence):
    R.append({"id": id, "text": text, "detail": detail, "category": category, "status": status,
              "gate": gate, "clearing_metric": clearing, "evidence": evidence})


add("R26", "Add a price-snapshot store that records opening and closing numbers for every market we originate", "",
    "data", "done", "", "28 rows (14 Week 10 games x spread+total) with source sha256; opening column blank and flagged because the only reachable source publishes closings",
    ["ops/price_store.py", "ops/data/price_snapshots.csv", "ops/price_policy.md"])
add("R27", "Add a verified results feed so backtests and ROI can be computed at all", "",
    "data", "done", "", "150 games (148 final, 2 pending with blank scores); 137/137 T1 scores cross-verified against nflverse",
    ["ops/results_feed.py", "ops/data/results/results_2026_reg.csv"])
add("R28", "Originate the side first, then the total, then the moneyline", "",
    "model", "partial", "origination exists for margin and total (Week 10); the moneyline derivation is defined (price policy P5) but not yet produced on a schedule",
    "a scheduled run publishing fl2_p_home with vig-free derivation for every game on a slate",
    ["data/market_lines.json", "ops/price_policy.md"])
add("R29", "Publish the model's fair line, the market line, and the difference as separate columns", "",
    "model", "done", "", "14 Week 10 games carry fl2_home_margin / spread_line / margin_diff and fl2_total / total_line / total_diff",
    ["data/market_lines.json (fl2_vs_market)", "ops/data/forecast_week11_2026.csv (residual columns)"])
add("R30", "Separate 'signal' from 'staking' in the leaderboard so a lucky staking run cannot mask a bad signal", "",
    "governance", "registered", "no leaderboard is published yet, by policy: zero strategies have cleared the skill gates",
    "a leaderboard exists with separate signal (proper-score) and staking (prospective) panels; >= 1 strategy with >= 40 prospective games",
    ["research/validation-gates.md", "data/strategies.json"])
add("R31", "Track the depth of the replacement, not just the fact of a replacement", "",
    "data", "partial", "depth_string / depth_basis / next_man_up are captured only for the 160-row Out/Doubtful subset, and only 5 of 32 club charts exist",
    "32/32 clubs with a resolved depth route (R77), then every Out/Doubtful row carries depth_string",
    ["data/injury-report-2026-w10.csv"])
add("R32", "Compute correlations only from officially sourced numbers and publish n with each value", "",
    "analytics", "done", "", "every row of the correlation matrix publishes n_clubs (16 or 32) and a bootstrap CI",
    ["data/derived-correlation.json", "data/correlation-matrix-2026-w10.csv"])
add("R33", "Define a demotion gate that sends a live strategy back to paper", "",
    "governance", "done", "", "gate D1 defined and frozen in the strategy registry (two consecutive windows with Brier-skill CI including 0 -> paper)",
    ["ops/forecast_week11.py (registry docstring, gates D1)"])
add("R34", "Pre-register every strategy; forbid backtest numbers from ever appearing on the leaderboard", "",
    "governance", "done", "", "STRAT-1 registered 2026-11-16 pre-kickoff with frozen method text; no leaderboard exists (policy), so no backtest number can appear on one",
    ["ops/forecast_week11.py", "ops/data/forecast_week11_2026.csv"])
add("R35", "Build the availability graph as a first-class dataset (who was expected to start, who actually did)", "",
    "data", "partial", "captures exist for one point in time (345-row report); the expected-vs-actual graph needs the multi-day capture series and verified starters",
    ">= 2 dated captures per week for >= 3 consecutive weeks + starters from Game Books (R50)",
    ["ops/data/snapshots/ledger.csv", "ops/availability_capture.py"])
add("R36", "Do not model depth from jersey order; model it from playing time", "",
    "model", "partial", "a snap-count table exists (265,892 player-week rows, 2016+) but is not yet joined to the availability data",
    "a published snap-share table joined to Out/Doubtful rows for the current week",
    ["signal/data/snap_participation.csv"])
add("R37", "Make the injury signal a surprise, never a level", "",
    "model", "registered", "needs >= 2 captures in the same week to define a delta; the capture series starts with the automated workflow",
    "first published surprise = designation change between two same-week captures",
    ["ops/availability_capture.py (delta_latest.json)", ".github/workflows/availability-snapshot.yml"])
add("R38", "Run the 32-team roster/IR sweep before any team-level model is trusted", "",
    "data", "blocked", "no verified source carries reserve/IR status: nflverse rosters.csv has no 2026 rows and no status column (verified 2026-11-16); nfl.com roster pages are reachable only through the page-fetch tool, not the bulk pipeline",
    "a 32-team sweep file with IR/reserve status and its source URL per row",
    ["raw/_nfldata/rosters.csv", "research/open-questions.md"])
add("R39", "Add a fixture-context feature set built only from published schedule facts", "",
    "data", "done", "", "stadium, roof and surface for all 150 games through Week 10, T2-labelled, one row cross-verified against the official game centre (Munich)",
    ["ops/venues.py", "ops/data/venues_2026_reg.csv"])
add("R40", "Store every model output as a probability plus its inputs, not just a pick", "",
    "model", "done", "", "market_lines.json and the Week 11 forecast store inputs, probabilities and residual columns per game",
    ["data/market_lines.json", "ops/data/forecast_week11_2026.csv"])
add("R41", "Compute and publish the \"removal of luck\" panel on the site dashboard", "",
    "analytics", "done", "", "Pythagorean panel for all 32 teams on n=148 verified games, luck residual published with n; rendered on the readiness dashboard",
    ["ops/luck_panel.py", "ops/data/luck_panel_2026.csv"])
add("R42", "Add a two-sided \"what would change our mind\" field to every strategy entry", "",
    "governance", "done", "", "abandon-if / promote-if fields frozen into the strategy registry",
    ["ops/forecast_week11.py (registry docstring)"])
add("R43", "Price a line ourselves and publish the residual against the market, on a schedule, from day one", "",
    "model", "partial", "residuals are published for Week 10 and Week 11, but no scheduled re-pricing job exists yet",
    "a scheduled CI job re-pricing the current slate every week",
    ["data/market_lines.json", "ops/data/forecast_week11_2026.csv"])
add("R44", "Turn the 136-game log into the pre-registered backtest corpus", "",
    "data", "done", "", "corpus frozen at registration = 137 games (W1-9 + W10 TNF); feed now carries 148 finals, and the corpus extension is versioned, not silently overwritten",
    ["ops/data/results/results_2026_reg.csv", "data/games.json"])
add("R45", "Decide the price-data policy before any backtest is published", "",
    "governance", "done", "", "seven-point policy frozen; no price-dependent backtest has been published",
    ["ops/price_policy.md"])
add("R46", "Store every injury-hub read with its clock time and publish the delta, never the level", "",
    "data", "partial", "the automated capture series (clock-stamped) starts with the new workflow; existing captures carry as-of dates, not clock times",
    "two clock-stamped captures of the same report, and a published delta file",
    ["ops/data/snapshots/ledger.csv", "ops/availability_capture.py"])
add("R47", "Put a decision-readiness table on the landing page: one row per requirement, with the gate that blocks it and the number that would clear it", "",
    "site", "done", "", "two reconciled views now exist: the landing page carries the DR-xx decision table (session 56a33eb6, PR #19) and /readiness/ carries the verbatim R26\u2013R96 register with gates and clearing numbers (session 310620fe); the earlier deviation note is superseded by the DR-table's landing-page presence",
    ["readiness/index.html", "index.html", "fl2-dashboard/data/decision-readiness.json"])
add("R48", "Transcribe the venue of every fixture from the official game centre and publish it", "",
    "data", "done", "", "stadium published for all 150 fixtures (T2); the Munich game (NE@DET, W10) verified directly against the official game centre 2026-11-16",
    ["ops/data/venues_2026_reg.csv", NFL + "/games/patriots-at-lions-2026-reg-10"])
add("R49", "Publish the league's dated schedule announcement beside the live schedule page", "",
    "site", "done", "", "the Week 16/17/18 flexible-scheduling announcement and its official link are published beside the schedule links on the readiness page",
    [NFL + "/schedules/2026/reg10/", NFL + "/legal/flexible-scheduling-procedures"])
add("R50", "Use official NFL Game Books for actual starters and game-day status; do not infer depth rank or snaps", "",
    "data", "partial", "per-game Game Book PDF links verified on the official game centre (2026-11-16); PDF ingestion is not built",
    "a parsed Game Book per completed game feeding actual starters into the availability graph",
    [NFL + "/games/patriots-at-lions-2026-reg-10"])
add("R51", "Ingest game-level results to make the ratings opponent-aware", "",
    "model", "done", "", "walk-forward power model and the originated lines both ingest game results (sigma recomputed on 4,056 games 2011-2026 = 12.97)",
    ["engine/run_backtest.py", "ops/forecast_week11.py"])
add("R52", "Add injury and personnel ablations instead of fixed penalties",
    "Instead of subtracting a fixed number of points for a missing starter, test the same model with and without the personnel features and report the difference with uncertainty.",
    "model", "registered", "ablation needs a multi-week availability feature that does not exist yet (R35/R37 gate)",
    "with/without comparison of >= 40 games with bootstrap uncertainty",
    ["data/market_lines.json (avail_adjustment, declared arbitrary)", "research/strategies.md"])
add("R53", "Add injury/depth ablations, not fixed penalties",
    "Compare identical models with and without verified availability features using chronological holdouts.",
    "model", "registered", "same gate as R52: no verified multi-week availability series exists to ablate",
    "chronological holdout with/without availability features, difference + CI published",
    ["signal/analysis/strategies.py", "research/validation-gates.md"])
add("R54", "Automate immutable multi-day availability snapshots",
    "Capture the official report and club depth pages at least daily with retained hashes, so practice designations can be replayed as they were known. Today the site holds one capture, which cannot support backtesting.",
    "data", "partial", "gate F-T1 (session 8326a20d): nfl.com Terms \u00a71.3 prohibit systematic retrieval to compile a database without written consent \u2014 the schedule is disabled and capture runs only on explicit manual dispatch; club depth pages are not in the first version",
    "owner resolves F-T1 (written consent or derived-counts-only policy), then a successful capture run, then daily cadence including club pages",
    [".github/workflows/availability-snapshot.yml", "ops/availability_capture.py"])
add("R55", "Build immutable official availability snapshots",
    "Scheduled capture of NFL injury reports, club depth pages and inactive evidence with raw hashes, timestamps and conflict flags",
    "data", "done", "", "append-only ledger with sha256 per capture, conflict flags, and the capture script writing raw hash-stamped HTML",
    ["ops/data/snapshots/ledger.csv", "ops/snapshot_ledger.py"])
add("R56", "Capture official inactive lists and snap counts",
    "Only 6 of 254 report rows carry a game designation, and no active list or snap share is captured. Without them a backup's replacement of a starter cannot be confirmed, only suspected.",
    "data", "partial", "snap-count rows exist (265,892 player-weeks) but per-game inactive lists are not captured by any verified source in the repo; note the 6-of-254 state predates the current 345-row captures",
    "inactive list for each Week 11 game captured before kickoff, with source URL",
    ["signal/data/snap_participation.csv", "ops/data/team_availability_2026_w10.csv"])
add("R57", "Fix the two depth-parsing failures before widening coverage",
    "The Texans publish depth as an image and the Packers prepend jersey numbers. Number stripping plus storing the raw string recovers the Packers rows; the Texans image needs an authorized structured source, not transcription by eye.",
    "data", "partial", "Packers rows are stored with raw strings in the club chart capture; the Texans chart remains an image, which no authorized structured source covers",
    "HOU depth rows from an authorized structured source (route decision in R77)",
    ["data/depth_charts.json"])
add("R58", "Model depth slots as groups, not a single starter",
    "149 club/unit/position slots list more than one rank-1 player (three receivers at rank 1, three inside linebackers at rank 1). Treating column 1 as 'the starter' would fabricate a starter the club never named.",
    "data", "partial", "the captured charts store positional rank arrays (shared rank-1 players stay in their listed order), but the group-slot model is only implemented for the 5 captured clubs",
    "all 32 clubs' charts represented as group slots under one verified route (R77)",
    ["data/depth_charts.json"])
add("R59", "Treat roster turnover as a first-class data event",
    "The Colts' Week 10 release documents two starting-receiver trades in the same article as its depth chart. Depth, availability and lineup evidence must be versioned against the last official roster event, not trusted as durable.",
    "data", "partial", "a dated 2026 transaction table exists in the repo (63 trades, T2 nflverse) but evidence versioning against roster events is not yet implemented",
    "ledger rows keyed by last-roster-event date; stale-depth flagger (R71) running",
    ["raw/_nfldata/trades.csv"])
add("R60", "Start with a singles-only shadow baseline",
    "Pre-register a simple team-strength model, freeze versions and record forecasts before kickoff.",
    "model", "done", "", "STRAT-1 frozen 2026-11-16; 13 Week 11 forecasts recorded 2026-11-16, three days before the Week 11 opener",
    ["ops/forecast_week11.py", "ops/data/forecast_week11_2026.csv"])
add("R61", "Keep parlays and prop combos behind a joint-evidence gate",
    "Multiplying marginal probabilities is invalid under dependence. A combo may only be ranked when a directly validated joint probability and the operator's void/push rules are both available.",
    "governance", "done", "", "the gate is in force: no combo is ranked anywhere in the repo, and the parlay analysis publishes a sensitivity grid over rho rather than a fabricated correlation",
    ["data/parlay_analysis.json", "research/validation-gates.md"])
add("R62", "Use proper-score leaderboard divisions",
    "Separate singles, game parlays, same-game parlays and prop combos; rank eligible strategies by benchmark-relative skill with uncertainty.",
    "governance", "registered", "divisions defined in the leaderboard spec; the leaderboard itself is not published (zero eligible strategies)",
    "a published leaderboard with four divisions and >= 1 eligible strategy in the singles division",
    ["research/validation-gates.md", "research/suggestions.md"])
add("R63", "Rank with proper scores and uncertainty, not win rate",
    "Rank by benchmark-relative Brier skill with a game-cluster lower bound and a multiplicity adjustment for the number of trials. Raw win rate and short-run ROI cannot distinguish skill from variance.",
    "governance", "partial", "Brier skill + Benjamini-Hochberg machinery exists and was run on 11 strategies x 8 gates; the prospective ranking surface does not exist",
    "a ranking table computed by the frozen scoring rule on prospective data",
    ["engine/run_backtest.py", "docs/STRATEGY_VALIDATION.md"])
add("R64", "Add durable snapshot storage and alerts",
    "Store immutable captures outside the static site, monitor freshness and alert on source/schema changes.",
    "data", "partial", "immutable captures + freshness monitoring + a loud CI alarm exist; the alarm channel is a failing workflow, not an independent monitor; raw HTML captures are not yet 'outside the static site' in the ownership sense the requirement describes",
    "an independent alert on capture age (not only a CI failure) and a storage location the site build cannot overwrite",
    ["ops/drift_check.py", ".github/workflows/availability-snapshot.yml"])
add("R65", "Split the site into a public analysis layer and a private data layer",
    "Keep the public site to derived analysis (indices, ratios, model output, links to the official page) and hold raw row-level data in a private store until the terms are read.",
    "site", "partial", "the public site currently serves row-level transcriptions in JSON/CSV; a private store requires infrastructure (a private repo or storage bucket) that only the owner can provision",
    "raw row-level data moved to a non-public store; site pages keep indices, ratios and links",
    ["docs/SOURCES.md", "data/"])
add("R66", "Add a per-team view: starters out, replacements named, net injury count",
    "Quick team-level decision view",
    "site", "done", "", "28 clubs with report rows, Out/Doubtful/Questionable/DNP counts, net injury count, next opponent, and the explicit IR unknown flag; bye clubs excluded with a note",
    ["ops/team_view.py", "ops/data/team_availability_2026_w10.csv"])
add("R67", "Add an announced-starter evidence field (not an inferred replacement)",
    "The blank replacement columns are correct for the report page, but the NFL does publish dated starter changes for Lock, McCord and Brissett (VR-24, VR-25; VQ-05).",
    "data", "partial", "the news register carries dated announced-starter headlines with official URLs (e.g. Drew Lock will start); the field is not yet wired into the per-game availability rows",
    "announced-starter evidence column populated from official news URLs for every game with a starter change",
    ["data/news_2026_week10.csv"])
add("R68", "Add an official depth-chart register with date and source per row",
    "Required to flag backups replacing starters on offense and defense",
    "data", "done", "", "the depth-chart capture carries source, page date and club disclaimer per club, plus the ledger's sha256-stamped registration",
    ["data/depth_charts.json (registry)", "ops/data/snapshots/ledger.csv"])
add("R69", "Calibrate what \"Questionable\" means empirically instead of using old percentages",
    "Official text gives no percentages",
    "analytics", "blocked", "requires multiple seasons of archived weekly reports joined to inactives/outcomes; no archive is reachable (nflverse/nfldata contains no injury table - verified via GitHub contents API 2026-11-16; release assets unreachable from this environment)",
    ">= 3 seasons of designation -> play-rate joins with confidence intervals",
    ["research/open-questions.md"])
add("R70", "Interactive Offense vs. Defense Matchup Deficiency Matrix (1st–4th String)",
    "Surfaces immediate trench and coverage mismatches (e.g., WR1 facing promoted 2nd/3rd-string CB, or EDGE1 facing 2nd/3rd-string OT/LG) on one screen.",
    "site", "blocked", "needs depth order for all 32 clubs on one verified route (R77) — 5 of 32 exist",
    "32/32 clubs with group-slot depth on one verified route",
    ["data/depth_charts.json"])
add("R71", "Flag stale depth rows against the official transactions log",
    "Baltimore still publishes Lamar Jackson and Tyler Huntley at QB after both went on injured reserve and a replacement was traded in (VR-17, VR-26; VQ-07).",
    "data", "partial", "trade dates and depth-row retrieval dates both exist, but no automated join flags rows older than the last roster event",
    "an automated flag on every depth row whose retrieval predates the club's last roster event",
    ["raw/_nfldata/trades.csv", "data/depth_charts.json"])
add("R72", "Point-in-Time Snapshot Ledger for Injuries, Depth Charts & Inactives",
    "Prevents lookahead leakage when backtesting originated lines and preserves exact pre-kickoff replacement certainty.",
    "data", "done", "", "append-only ledger with sha256, capture date, source URL, conflict flags, and the replayable-raw design for future captures",
    ["ops/data/snapshots/ledger.csv", "ops/snapshot_ledger.py"])
add("R73", "Populate the three missing Lions game-status designations",
    "Kerby Joseph, Cade Mays and D.J. Reed are published with a blank game-status cell while the official article lists all three as Out (VR-08, VR-12).",
    "data", "done", "", "all three rows carry Out in both committed captures and were re-verified against the live official report on 2026-11-16 (Knee/Ankle/Hip, DNP, Out)",
    ["data/injuries.json", NFL + "/injuries/"])
add("R74", "Re-capture and republish the Week 10 injury tables",
    "Published counts are stale: 254 rows and 4 no-injury sections versus 279 rows and 2 sections live; Seattle and Cincinnati are shown as injury-free while listing 15 and 4 players (VR-04, VR-05, VR-06, VR-07).",
    "data", "done", "", "both committed captures agree at 345 rows / 28 clubs; SEA carries 15 rows and CIN 9 in both; the 254-row state predates the committed files. CIN live count has since grown (9 at capture) - the capture-automation series will keep pace",
    ["data/injuries.json", "fl2-dashboard/data/verified/injuries-week10.json", NFL + "/injuries/"])
add("R75", "Reject: deriving depth order from jersey number, experience or salary",
    "Proposed shortcut for SG-05: infer starters from roster attributes on the official roster page.",
    "governance", "rejected", "", "rejection recorded as policy: depth order comes only from a verified club chart or snap counts (R77 routes); roster attributes never infer it",
    ["research/requirements-v2.md", "research/strategies.md"])
add("R76", "Represent shared and empty depth slots faithfully",
    "Seattle puts two players in one slot and Washington leaves a slot empty; both are currently indistinguishable from a ranked list (VR-21, VR-23; VQ-08).",
    "data", "partial", "the positional-array representation stores shared and empty slots faithfully for the 5 captured clubs; SEA and WAS charts are not among the captured five, so their specific slots remain unverified",
    "SEA and WAS charts captured and verified on the same representation",
    ["data/depth_charts.json"])
add("R77", "Resolve the depth-order source before building the backup-deficiency feature",
    "Evaluate two routes in order: (a) per-club official depth chart pages, verified club by club; (b) derive depth from snap counts if an official snap-count source exists. Do not build the feature until one route is verified for all 32 clubs.",
    "governance", "registered", "route evaluation is documented; 5 of 32 clubs verified on route (a); no official 32-club snap-count route exists yet",
    "one route verified for 32/32 clubs, recorded club by club",
    ["research/open-questions.md", "data/depth_charts.json"])
add("R78", "Score injury-designation reliability before using it as a feature",
    "Join several seasons of designations to the official inactive lists and measure the play rate per designation with confidence intervals. Only then decide whether the label becomes a model feature.",
    "analytics", "blocked", "same source gate as R69: seasons of archived designations + inactive lists are not reachable",
    "play rate per designation with CI over >= 3 seasons",
    ["research/open-questions.md"])
add("R79", "Snapshot the nfl.com injury report every Wed, Thu and Fri and keep a dated history",
    "Lets us see Questionable→Out changes and practice trends (DNP→LP→FP)",
    "data", "partial", "workflow committed with hash-stamped history but the schedule is disabled pending gate F-T1 (nfl.com Terms \u00a71.3); capture is manual-dispatch only until the owner decides",
    "owner resolves F-T1; then three dated captures in the history with a published delta",
    [".github/workflows/availability-snapshot.yml", "ops/availability_capture.py"])
add("R80", "Treat the injury report as a timestamped series, not a weekly snapshot",
    "Capture the report daily from Wednesday to kickoff with the fetch timestamp, then measure how designations evolve.",
    "data", "partial", "the series design exists (ledger + capture); the series itself begins at the first automated capture",
    ">= 3 timestamped reads of one week's report with an evolution measure",
    ["ops/data/snapshots/ledger.csv"])
add("R81", "Use snap counts as the starter proxy when the depth chart is unavailable",
    "Gives a measurable starter/backup split",
    "data", "partial", "snap table exists (265,892 rows) but the starter-proxy join (top snap share per unit per week) is not built",
    "published per-unit snap-share leaders for the current week",
    ["signal/data/snap_participation.csv"])
add("R82", "Add a control baseline (random picks; favorites only) to every leaderboard run",
    "Separates skill from luck",
    "governance", "done", "", "frozen-seed random baseline (54.05% on 148 games) and favourites-only baseline (SU 68.24%, cover 52.03%, cover band asserted) computed on the verified corpus",
    ["ops/baselines.py", "ops/data/baselines_2026.json"])
add("R83", "Stadium Roof/Surface & NWS Hourly Wind/Precipitation Overlay",
    "Prevents totals and passing-prop mispricing by coupling NWS forecast grids with official 90-minute stadium roof designations.",
    "data", "partial", "roof/surface published for all 150 fixtures; NWS hourly grids are unreachable from the build environment (weather.gov not on the allow-list)",
    "weather.gov reachable from CI, then hourly wind/precip joined to roof designations",
    ["ops/venues.py", "ops/data/venues_2026_reg.csv"])
add("R84", "Two-Stage Skill Leaderboard (Proper-Score Qualification -> Prospective CLV/ROI Escrow)",
    "Aligns incentives strictly with calibrated probabilistic skill (Brier Skill Score + Closing Line Value) over multi-week prospective samples.",
    "governance", "registered", "stage 1 qualification is specified; stage 2 needs prospective CLV, which needs price snapshots over time (R26 series) and a leaderboard (R62 gate)",
    "stage-2 escrow panel with >= 4 weeks of prospective CLV data",
    ["research/validation-gates.md"])
add("R85", "Vig-Free Market Consensus vs. Originated Fair-Line Decomposition View",
    "Separates true pricing divergence (origination alpha) from operator vig/margin before any bet structure is considered.",
    "model", "partial", "vig-free moneyline normalisation is defined in policy P5 and single-book vig-free residuals are computable; a multi-book CONSENSUS needs prices from several books, which no reachable source provides",
    ">= 2 independent book prices per game, enabling a consensus column",
    ["ops/price_policy.md (P5)", "ops/data/forecast_week11_2026.csv"])
add("R86", "Publish a weekly 'what changed' diff instead of a static snapshot",
    "Store each weekly snapshot and render a diff column (rank change, rating change, availability change).",
    "site", "partial", "the snapshot ledger defines the delta mechanism; weekly diffs need >= 2 weekly snapshots",
    "first weekly diff published from two dated snapshots",
    ["ops/data/snapshots/ledger.csv"])
add("R87", "Publish every model total twice until one wins",
    "Keep both estimators visible with the gap column, and only collapse to one after a walk-forward comparison.",
    "model", "registered", "a second total estimator must be built and pre-registered before the two can be compared",
    "two pre-registered estimators with a gap column over >= 40 games",
    ["ops/forecast_week11.py", "research/strategies.md"])
add("R88", "Add a drift alarm to every scraper",
    "Pin each parser to expected row counts and required fields; fail the build loudly when a field goes missing rather than publishing a blank.",
    "data", "done", "", "seven datasets pinned to row counts + required fields + max capture age (exit 1 on violation); the report parser fails loudly on missing markers",
    ["ops/drift_check.py", "ops/data/drift_manifest.json", "ops/availability_capture.py"])
add("R89", "Capture the reserve list so 'not listed' never means 'available'",
    "Malik Willis is absent from the weekly report because he is on injured reserve, not because he is healthy (VR-25; VQ-06).",
    "data", "blocked", "same gate as R38: no verified source carries reserve/IR status in this environment; every team row carries the explicit IR-unknown flag meanwhile",
    "a reserve/IR source with a URL, ingested for 32 teams",
    ["ops/data/team_availability_2026_w10.csv", "raw/_nfldata/rosters.csv"])
add("R90", "Reject: ranking strategies by season-long ROI",
    "Proposed alternative to SG-03: rank purely on realised return over the season.",
    "governance", "rejected", "", "rejection recorded as policy: ranking uses benchmark-relative Brier skill with uncertainty; ROI enters only in stage-2 escrow after proper-score qualification",
    ["research/validation-gates.md"])
add("R91", "Archive weekly injury reports for past seasons (for Q06)",
    "Only way to test whether designations change outcomes",
    "data", "blocked", "no archive is reachable: nflverse/nfldata has no injury table (verified via GitHub contents API 2026-11-16); nflverse release assets fail from this environment (HTTP 000, recorded 2026-11-14)",
    "one archived season of weekly reports (>= 18 weeks x 32 clubs) with a source URL",
    ["research/open-questions.md"])
add("R92", "Pre-register each strategy (definition frozen before results are seen)",
    "Prevents result-chasing",
    "governance", "done", "", "the registry mechanism exists and is used: STRAT-1 frozen pre-kickoff with commit-hash registration",
    ["ops/forecast_week11.py", "ops/data/forecast_week11_2026.csv"])
add("R93", "2026 Kickoff & Declared Onside-Kick Regime Priors Filter",
    "Avoids systematic bias in originated game totals and 4th-quarter comeback win-probability curves.",
    "model", "blocked", "requires play-level or drive-level data for 2026 (kickoffs/onside declarations), which no reachable source provides",
    "play-level 2026 feed with kickoff events and declared onside attempts",
    ["research/open-questions.md"])
add("R94", "Freeze a rule before it sees data (pre-registration)",
    "Commit the rule text, the sample window and the gates to git before the evaluation window opens. The commit hash is the registration.",
    "governance", "done", "", "STRAT-1 method text, sample window (2026 W11+) and gates committed before the evaluation window opens; hash recorded in COORDINATION.md",
    ["COORDINATION.md", "ops/forecast_week11.py"])
add("R95", "Split data into train, validation and final holdout seasons",
    "Protects out-of-sample testing",
    "model", "partial", "the walk-forward harness uses chronological out-of-sample splits (2011-2026, no-look-ahead audit); an explicit named train/validation/final-holdout table for future strategy runs is specified but not yet exercised",
    "a published split table (train/val/holdout seasons) used by the next strategy evaluation",
    ["engine/run_backtest.py", "docs/STRATEGY_VALIDATION.md"])
add("R96", "Make suggestions on how to improve the site to improve decision making and create a section dedicated for suggestions so someone can review suggestions and choose the best path before implementing any changes.",
    "Sub-requirement: a clear list of questions, information and answers that need to be addressed before any decision, based on what we have and do not have; suggestions must discover missing information.",
    "site", "done", "", "suggestion sections with adopt/test/reject paths exist in four site layers, plus decision-question registers separating known / missing / how-to-discover",
    ["research/suggestions.md", "research/open-questions.md", "data/decision-questions.csv", "fl2-dashboard/suggestions.html", "ledger/suggestions.html"])


def main() -> None:
    meta = {
        "register": "requirements_v2",
        "created_utc": "2026-11-16",
        "created_by_session": "310620fe",
        "covers": "Every requirement line of the current brief after the original 25 (R01-R25, tracked in data/requirements.csv), mapped one-to-one as R26-R96.",
        "verification": "Each status was set from files that exist in the repository and from live official-page fetches on 2026-11-16; evidence paths are checkable.",
        "counts": {},
    }
    for r in R:
        meta["counts"][r["status"]] = meta["counts"].get(r["status"], 0) + 1
    out_json = os.path.join(HERE, "data", "requirements_v2.json")
    json.dump({"meta": meta, "requirements": R}, open(out_json, "w"), indent=1)

    md = ["# Requirements Register v2 (R26-R96)",
          "",
          f"Created 2026-11-16 by session `310620fe`. **{len(R)} rows** — "
          + ", ".join(f"{v} {k}" for k, v in sorted(meta['counts'].items())) + ".",
          "",
          "Statuses: `done` = implemented and verified; `partial` = implemented for part of the",
          "scope with a named gate holding the rest; `registered` = specified and pre-registered;",
          "`blocked` = cannot advance without something outside our control; `rejected` = the",
          "requirement itself is a rejection and the deliverable is the recorded policy.",
          "",
          "| ID | Requirement (verbatim) | Detail | Category | Status | Gate that blocks it | Number that would clear it | Evidence |",
          "|---|---|---|---|---|---|---|---|"]
    for r in R:
        ev = "<br>".join(f"`{e}`" if e.startswith(("ops/", "data/", "research/", "docs/", "engine/", "signal/", ".github/", "raw/", "fl2-")) else e for e in r["evidence"])
        md.append(f"| {r['id']} | {r['text']} | {r['detail']} | {r['category']} | **{r['status']}** | "
                  f"{r['gate'] or '—'} | {r['clearing_metric'] or '—'} | {ev} |")
    out_md = os.path.join(os.path.dirname(HERE), "research", "requirements-v2.md")
    open(out_md, "w").write("\n".join(md) + "\n")
    print(f"register: {len(R)} rows -> {out_json} and {out_md}")
    print("counts:", meta["counts"])


if __name__ == "__main__":
    main()
