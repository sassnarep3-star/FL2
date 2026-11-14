"use strict";
/* FL2 — decision register data.
 *
 * Every item is a question that must be answered before a decision about the
 * project can be made responsibly. `basis` records whether the answer comes from
 * evidence in this repo, from an external source, or is still unknown.
 *
 * No answer here is a guess. `answer: null` means the question is open.
 */
window.FL2_DECISIONS = [
  {
    id: "D01",
    group: "Data foundation",
    question: "Which statistics can this project verify against an official source without a paid feed?",
    answer: "Team-level offense (points for/against), team defense (points, yards, takeaways), standings, the official weekly injury report, and 1999-2026 game results with closing lines. Player-level box scores could not be obtained in this environment.",
    basis: "verified",
    evidence: "docs/SOURCES.md §2-§9; every team-level table was read from nfl.com or pro-football-reference.com",
    sources: ["https://www.nfl.com/standings/", "https://www.pro-football-reference.com/years/2026/opp.htm", "https://www.nfl.com/injuries/"],
    impact: "Sets the ceiling on which strategies can be tested at all.",
    recommendation: "Treat the project as a team-level model until a licensed player feed is added. Do not claim player-prop edges.",
    risk: "low"
  },
  {
    id: "D02",
    group: "Data foundation",
    question: "Do we have player-level data (targets, routes, snap counts) needed to price player props?",
    answer: null,
    basis: "unknown",
    evidence: "nflverse publishes these as GitHub *release assets*, which redirect to objects.githubusercontent.com — blocked from the build environment. Nothing was substituted.",
    sources: ["https://github.com/nflverse/nflverse-data/releases/tag/player_stats", "https://github.com/nflverse/nflverse-data/releases/tag/snap_counts"],
    impact: "Blocks every player-prop and player-combo strategy. 5 of 5 prop combos stay unverified.",
    recommendation: "Decide whether to (a) obtain a licensed data feed, (b) run the engine where the release assets are reachable, or (c) drop player props from scope. Record the choice in COORDINATION.md.",
    risk: "high"
  },
  {
    id: "D03",
    group: "Data foundation",
    question: "Is there any official publisher of sportsbook prices we can cite?",
    answer: "No. Market prices have no official publisher; only licensed commercial feeds. The only prices in this project come from the nflverse closing-line aggregation (2006-2013 seasons populated) and are labelled as aggregated, not official.",
    basis: "verified",
    evidence: "docs/SOURCES.md §1 table; `verified_market` flag in data/market_lines.json",
    impact: "Any 'edge' claim depends on a price we cannot independently verify.",
    recommendation: "Before any strategy is called actionable, record the actual price taken at bet time with a screenshot or API payload. Until then every strategy stays `experimental`.",
    risk: "high"
  },
  {
    id: "D04",
    group: "Data foundation",
    question: "Which field convention is `spread_line` in the dataset — handicap or expected home margin?",
    answer: "Expected home margin. A home favourite has spread_line > 0. Verified three ways against the moneyline sign and enforced by an assertion.",
    basis: "verified",
    evidence: "docs/SOURCES.md §3; `self_check()` in engine/run_backtest.py asserts it on every build",
    sources: ["https://github.com/nflverse/nfldata/blob/master/data/games.csv"],
    impact: "An inverted convention would silently flip every result. It did during development.",
    recommendation: "Keep the assertion. Any new data source must pass the same three checks before use.",
    risk: "low"
  },
  {
    id: "D05",
    group: "Model quality",
    question: "Is our model better than the closing line at predicting winners?",
    answer: "No. Out-of-sample 2011-2026, n=4,041: Elo Brier 0.2277 vs closing line 0.2106 — a Brier skill of -8.1% against the market.",
    basis: "verified",
    evidence: "data/backtest_summary.json → baselines",
    impact: "A model worse than the market cannot be assumed to find value against it.",
    recommendation: "Improve the model before expanding strategy count. The highest-leverage additions are a QB-quality term and opponent-adjusted efficiency, not more hypotheses.",
    risk: "high"
  },
  {
    id: "D06",
    group: "Model quality",
    question: "Do any of the tested single-bet strategies beat the market after correcting for multiple testing?",
    answer: "No. 0 of 10 testable strategies cleared the gates; 1 was untestable for lack of opening-line data. Best was S1 at +0.47% ROI with a CI spanning zero.",
    basis: "verified",
    evidence: "data/backtest_summary.json → strategies; docs/STRATEGY_VALIDATION.md §8",
    impact: "Nothing may be presented as a profitable system.",
    recommendation: "Publish the negative result. It is the most defensible finding in the project and it saves money.",
    risk: "high"
  },
  {
    id: "D07",
    group: "Model quality",
    question: "Are spread and total legs correlated enough for same-game parlays to be mispriced?",
    answer: "In this data, essentially not: phi = +0.008 [-0.023, +0.040], n=3,913. Joint observed 24.20% vs independence 24.00%.",
    basis: "verified",
    evidence: "data/parlay_analysis.json → same_game_correlations",
    impact: "The claim that spread+total SGPs need a correlation adjustment is not supported here.",
    recommendation: "Do not build a correlation-adjusted SGP product on this pair. The one real dependence (win + cover, phi=0.68) is mechanical and already priced.",
    risk: "medium"
  },
  {
    id: "D08",
    group: "Model quality",
    question: "What per-leg edge does a 3-leg parlay require to break even?",
    answer: "13.03% of the fair payout is surrendered at -110, so each leg must clear 52.38% simultaneously and three times over.",
    basis: "verified",
    evidence: "data/parlay_analysis.json → vig_cost_by_leg_count; arithmetic in docs/STRATEGY_VALIDATION.md §6",
    impact: "Parlays are the worst vehicle for a thin edge.",
    recommendation: "Rank strategies on singles performance first; only show parlays as a calculated consequence of validated singles.",
    risk: "medium"
  },
  {
    id: "D09",
    group: "Injuries and lineups",
    question: "Can we tell whether a team is starting a 2nd/3rd/4th-string player?",
    answer: "Partially. We can state exactly who the league lists as Out/Doubtful/Questionable, and NFL.com confirms named starting-quarterback changes for 5 teams. We cannot confirm depth-chart rank for non-QB positions from the pages used.",
    basis: "partially verified",
    evidence: "docs/SOURCES.md §4-§5; data/week10_lineups.json → team_depletion",
    impact: "The depletion index is a position-weight proxy, not a verified starter/backup measure.",
    recommendation: "Either obtain official depth charts, or keep the index labelled a proxy and never present it as a measured effect. Currently priced at 3 points for a full 100-point index gap — an arbitrary, declared scale.",
    risk: "high"
  },
  {
    id: "D10",
    group: "Injuries and lineups",
    question: "Does losing personnel actually move the line, and by how much?",
    answer: null,
    basis: "unknown",
    evidence: "No dataset in this environment links injury reports to line movement. Testing it needs a pre/post-report line snapshot.",
    impact: "We adjust our own number for availability but cannot claim the market misprices it.",
    recommendation: "Capture weekly line snapshots from Week 1 next season; that single dataset unlocks the whole injury-angle programme.",
    risk: "high"
  },
  {
    id: "D11",
    group: "Injuries and lineups",
    question: "Who is starting at quarterback for every team in Week 10?",
    answer: "Confirmed for 5 teams with changes (ARI Carson Beck, CLE Deshaun Watson, MIA Kyle McCord, MIN Kirk Cousins, SEA Drew Lock). Baltimore and the LA Chargers are left blank because no reviewed official page names their starter.",
    basis: "partially verified",
    evidence: "docs/SOURCES.md §5",
    impact: "QB is the largest single driver of a game number; two unknown starters materially widen uncertainty on those games.",
    recommendation: "Do not publish a number for BAL or LAC as if it were complete. Flag them until confirmed.",
    risk: "medium"
  },
  {
    id: "D12",
    group: "Competition design",
    question: "How should a leaderboard rank strategies without rewarding luck?",
    answer: "Rank by gates passed first, then by lower confidence bound of ROI — never by raw ROI or win rate. Require a pre-registered protocol and count every hypothesis tried.",
    basis: "verified",
    evidence: "docs/STRATEGY_VALIDATION.md §2-§4; S10 demonstrates a 55.1% hit rate that is pure noise",
    impact: "Raw-ROI leaderboards select for luck by construction.",
    recommendation: "Ship the leaderboard exactly this way and show the uncertainty next to every score.",
    risk: "medium"
  },
  {
    id: "D13",
    group: "Competition design",
    question: "What should a strategy reward be tied to?",
    answer: null,
    basis: "policy decision",
    evidence: "Requires the owner's decision; not a data question.",
    impact: "Reward design determines whether participants optimise for real edge or for variance.",
    recommendation: "Tie rewards to forward-validated performance with a minimum sample, not to backtest performance. Consider a penalty for strategies that fail G5 (season-to-season stability).",
    risk: "medium"
  },
  {
    id: "D14",
    group: "Competition design",
    question: "How many hypotheses may be tested before the results stop being evidence?",
    answer: "Under Benjamini-Hochberg at q=0.10 with m hypotheses, the smallest surviving p is roughly 0.1/m. With 11 hypotheses a p of 0.009 is needed. More hypotheses shrink the discovery threshold.",
    basis: "verified",
    evidence: "data/backtest_summary.json → protocol.fdr_cutoff_p; `apply_gates` in engine/run_backtest.py",
    impact: "Unlimited hypothesis mining guarantees false discoveries.",
    recommendation: "Cap the tested-hypothesis count per cycle and publish m alongside every p-value.",
    risk: "high"
  },
  {
    id: "D15",
    group: "Operations",
    question: "How stale is the site's data allowed to get before it must be labelled stale?",
    answer: "Injury and lineup state changes hourly. A 24-hour threshold is proposed: any table without an `as_of` inside 24h is rendered with a stale badge.",
    basis: "policy decision",
    evidence: "AS_OF timestamps in every data/*.json",
    impact: "A stale injury table is worse than no table, because it looks authoritative.",
    recommendation: "Enforce the badge in the site build; fail the build if a data file has no `as_of`.",
    risk: "medium"
  },
  {
    id: "D16",
    group: "Operations",
    question: "Can two agent sessions publish to the same GitHub Pages site without clobbering each other?",
    answer: "Not automatically. Pages builds from `main:/` with `build_type: legacy`, so concurrent pushes race.",
    basis: "verified",
    evidence: "gh api repos/sassnarep3-star/FL2/pages → build_type legacy, source main:/",
    impact: "A race can publish a half-merged site.",
    recommendation: "Serialise publishing: one integration branch, `git pull --rebase` before every push, and a link-check gate that must pass before the Pages build is trusted.",
    risk: "medium"
  },
  {
    id: "D17",
    group: "Operations",
    question: "Should the project keep the repository's single-branch working model or move to per-task branches?",
    answer: null,
    basis: "policy decision",
    evidence: "Arena pins each session to its launch branch; the brief asks for session-<id>/<task> branches. The two cannot both be satisfied.",
    impact: "Determines how parallel work is coordinated going forward.",
    recommendation: "Keep Arena branches and non-overlapping file scopes (as COORDINATION.md now does); log the deviation rather than pretending it was followed.",
    risk: "low"
  },
  {
    id: "D18",
    group: "Verification",
    question: "What is the standard for a value appearing on the site?",
    answer: "A row is published only with a `source_url` to a T1/T2 source and `verified: true`. If a value cannot be confirmed it is left blank, `verified: false`, and listed on the Flagged for Review page.",
    basis: "verified",
    evidence: "Every data/*.json record carries these fields; docs/SOURCES.md opens with the rule",
    impact: "Prevents the most common failure mode of sports dashboards: plausible-looking invented numbers.",
    recommendation: "Keep the blank-and-flag rule absolute. A blank cell is information; an invented cell is a liability.",
    risk: "low"
  },
  {
    id: "D19",
    group: "Verification",
    question: "Which claims in this project are unverified right now?",
    answer: "Baltimore and LA Chargers Week 10 starting QBs; the starter/backup rank of every non-QB listed on the injury report; all player-prop correlations; every market price for Week 10 except the 13 games present in the nflverse closing-line file.",
    basis: "verified",
    evidence: "Flagged for Review page, generated from data/*.json where verified=false or value is null",
    impact: "These are the items a human should check first.",
    recommendation: "Review them in the order listed. The QB blanks are the cheapest to close.",
    risk: "high"
  },
  {
    id: "D20",
    group: "Verification",
    question: "Is 'no published edge' a failure of the project?",
    answer: "No. The market is efficient enough that a team-level model built on public data should not beat it, and measuring that honestly is the result. The project's value is the validation harness that will reject bad ideas before they cost money.",
    basis: "verified",
    evidence: "docs/STRATEGY_VALIDATION.md §8; Brier skill -8.1%",
    impact: "Reframes success: the deliverable is a rejection machine plus a verified dataset, not a list of winners.",
    recommendation: "Keep the leaderboard even though it is empty. An empty leaderboard that is honest is worth more than a full one that is not.",
    risk: "low"
  }
];
