# Fetch / Verification Log

All data on the FL2 site was fetched and verified line by line from the official sources listed below.
Verification date: **2026-11-14**. Tool: `fetch_page` (direct retrieval of the official page) and
`web_search` (cross-check). No values were inferred. Anything not confirmable from an official
source was left blank and flagged on the Flagged for Review page.

| # | Official source URL | What was verified | Result |
| --- | --- | --- | --- |
| 1 | https://www.nfl.com/standings/ | 2026 Regular-season standings, all 32 teams: W-L-T, PCT, PF, PA, Net Pts, Home/Road/Div/Conf/NonConf, Streak, Last 5 | Verified. Recorded in `standings-2026-reg.json`. |
| 2 | https://www.nfl.com/schedules/ | 2026 Week 10 schedule: all 14 games (dates, times, networks, matchups), Week 10 final result (WAS 24 @ NYG 21), Week 10 bye teams (CHI, DEN, PHI, TB) | Verified. Recorded in `schedule-week10.json`. |
| 3 | https://www.nfl.com/injuries/ | 2026 Week 10 injury report for all 28 teams playing in Week 10: every listed player, position, injury, practice status, game status | Verified. Recorded in `injuries-week10.json`. Bye teams have no Week 10 report. |
| 4 | https://www.nfl.com/teams/detroit-lions/roster | Lions official 2026 roster (player names, positions, status) — cross-check for depth chart | Verified. |
| 5 | https://www.detroitlions.com/team/depth-chart | Lions official 2026 depth chart (offense/defense/special teams, 1st/2nd/3rd/4th string) — worked example for the depth-deficiency tracker. Page is labeled "2026 Unofficial Depth Chart Compiled by Lions Football Communications." | Verified. Recorded in `depth-lions.json`. Flagged: team-labeled "unofficial". |
| 6 | https://www.nfl.com/injuries/team/detroit-lions/ | Test of per-team injury URL pattern | 404 — pattern does not exist. Per-team rows cite the main official injury report instead. |
| 7 | https://www.nfl.com/injuries/teams/detroit-lions/ | Test of alternative per-team injury URL pattern | 404 — pattern does not exist. Flagged as irregularity. |
| 8 | https://www.nfl.com/news/... (multiple, surfaced on the injury page) | Official NFL news: Lamar Jackson on IR (thumb, 6-10 weeks), Drew Lock starting for Seahawks, Malik Willis IR / Kyle McCord first start, Puka Nacua IR (turf toe/MCL/PCL), Josh Jacobs finger surgery, Deshaun Watson concussion protocol, Tyler Huntley out for season | Verified via official NFL.com news links listed on the injuries page. Used for context rows on the injuries page. |

## Data rules applied

- Every table row on the site carries a source link to the official page where the value was verified.
- A blank cell means the official source did not provide a value. It is NOT inferred.
- Design/methodology content (strategy design, validation gates, correlation framework, questions and
  suggestions) is labeled as a proposed design by the FL2 project and is not a claim of external fact;
  where it references a factual claim, a source link is provided.
