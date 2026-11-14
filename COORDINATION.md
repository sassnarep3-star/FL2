# COORDINATION.md — Shared Task Board

Repo: `sassnarep3-star/FL2`
Base commit: `0f3d2f9e87f44409fa02fd94aa5d474f58b300a5` (main)
Session branch: `arena/1374049c-fl2`
Session ID: **session-1374049c**

> Protocol: claim a task by writing your session ID + file scope here, then commit and push that
> claim immediately. Never start a task another session has claimed. Keep scopes non-overlapping.
> Small frequent commits; `git pull --rebase` before every push. If a claim is >60 minutes old with
> no commits, another session may take it over and log the handoff.
>
> **Status rule:** a task is `done` only if every file it names exists in the repository. Statuses
> are checked against `git ls-files`, never against intention.

## Environment notes (read before starting)

* **Bash/sandbox network is restricted** to `github.com`, `codeload.github.com`, `api.github.com`,
  `registry.npmjs.org`, `pypi.org`, `files.pythonhosted.org`. `curl https://www.nfl.com` fails with
  `SSL_ERROR_SYSCALL`.
* **Official pages were fetched with the `fetch_page` / `web_search` tools**, which do have general
  web access.
* **There is no `data/raw/` directory.** Fetched page text is not persisted to disk by the fetch
  tool, so every fetch was transcribed into `data/*.json` in the same session, with a `meta` block
  recording the source URL and retrieval date. Anything not written in-session was lost; that
  happened once and the pages had to be re-fetched. Do not plan around a raw cache.
* Publication target: GitHub Pages from `/docs`.

## Task board

| # | Task | Status | Owner | Files in scope | Sources used | Verification |
|---|------|--------|-------|----------------|--------------|--------------|
| T01 | Repo review (line by line) | **done** | session-1374049c | `README.md`, `COORDINATION.md`, `research/method.md` | repo git history | Base commit contained exactly one file, `README.md` (`# FL2`) |
| T02 | Requirements register | **done** | session-1374049c | `research/requirements.md` → `docs/requirements.html` | user brief | each row links a file that `git ls-files` confirms |
| T03 | Open questions / known-unknowns | **done** | session-1374049c | `research/open-questions.md` → `docs/open-questions.html` | official sources where an answer exists | each answered row carries an official link; unresolved rows say how to resolve them |
| T04 | Suggestions backlog (reviewer chooses path) | **done** | session-1374049c | `research/suggestions.md` → `docs/suggestions.html` | — | 8 suggestions × Path A/B/C + recommendation; **none implemented**, decision table at the bottom |
| T05 | Standings (official) | **done** | session-1374049c | `data/standings.json` | https://www.nfl.com/standings/division/2026/REG | replayed from box scores: **32/32 teams match exactly** |
| T06 | Week 10 injury report (official) | **done** | session-1374049c | `data/injuries.json` | https://www.nfl.com/injuries/league/2026/reg10 | 345 player rows, 28 team entries, 14 games; each row carries a player URL |
| T07 | Game results, Weeks 1–10 | **done** | session-1374049c | `data/games.json`, `data/schedule_week10.json` | https://www.nfl.com/schedules/2026/by-week/week-N (N=1..9), https://www.nfl.com/schedules/2026/reg10 | 137 games = 136 (Wk 1–9) + 1 (Wk 10 TNF). Count reconciles with standings |
| T08 | Team stats (official) | **done — partial by design** | session-1374049c | `data/team_stats.json` | https://www.nfl.com/stats/team-stats/ | 4 tables published, 3 withheld (no headers), 7 of 15 passing columns withheld — see Flagged page |
| T09 | Depth charts | **done — 5 of 32 clubs** | session-1374049c | `data/depth_charts.json` | patriots/detroitlions/packers/chiefs/49ers `.com/team/depth-chart` | all 5 captioned "unofficial" by the club; 27 registered `not acquired`; **not claimed complete** |
| T10 | Player game logs | **done — 6 players, 2 clubs** | session-1374049c | `data/player_logs.json` | https://www.nfl.com/players/{slug}/stats/logs/2026/ | Maye's log sums match his leaderboard row exactly (178/272, 2,282 yds, 18 TD, 11 INT) |
| T11 | Analytics engine | **done** | session-1374049c | `tools/analytics.py`, `data/derived/analytics.json` | computed from T05–T10 | stdlib only, deterministic, re-runnable |
| T12 | Backup-impact analysis (requirement 5) | **done — 5 clubs** | session-1374049c | `tools/backup_impact.py`, `data/derived/backup_impact.json`, `research/injury-backup-analysis.md` | official injury report × club charts | 9 first-stringers Out/Doubtful located; 3 Out players missing from their own chart |
| T13 | Strategy catalogue + validation gates | **done** | session-1374049c | `research/strategies.md`, `research/validation-gates.md` | arithmetic on official data | 6 candidates scored; **0 pass G3** |
| T14 | Leaderboard / rewards design | **blocked, documented** | session-1374049c | `research/suggestions.md` (S6) | — | Not built: a leaderboard of zero passing strategies is theatre, and season-long win rate cannot separate skill from luck at n=200. Design is written, awaiting S5/S6 decision |
| T15 | Site build | **done** | session-1374049c | `tools/build_site.py`, `docs/` (18 pages) | data files above | `tools/check_links.py`: all internal links resolve; every data table has a Source column |
| T16 | Final integration: re-verify, PR, merge, Pages | **in progress** | session-1374049c | `COORDINATION.md`, `docs/**` | — | see Integration record below |

### Withdrawn tasks

Two earlier board rows claimed files that were never created and are **withdrawn** rather than
renumbered, so the history stays auditable:

* *"T13 Leaderboard / rewards"* as originally claimed (`docs/pages/leaderboard.html`,
  `data/leaderboard.json`) — **no such files exist and none were created**; a leaderboard is
  deliberately not published (see T14).
* *"T12 validation"* as originally claimed (`docs/pages/validation.html`, `data/strategies.json`) —
  the gates live in `research/validation-gates.md` instead.

## Claims

| Session | Files claimed | Claimed (UTC) | Released |
|---|---|---|---|
| session-1374049c | entire repository (single-session run; no other session ever claimed a scope) | 2026-11-14 | — |

No other session ID appears in the git history, so no cross-session conflict arose and no conflict
resolution was required. If a second session starts, it must claim a non-overlapping file scope here
and rebase before pushing.

## Cross-scope change requests

None. (Single session.)

## Irregularities found (all reproduced on the site's Flagged-for-Review page)

| # | Irregularity | Evidence |
|---|---|---|
| 1 | The NFL publishes **no official depth chart** | https://www.nfl.com/teams/new-england-patriots/depth-chart → "404 - Flag on the Play." Every club chart used is captioned unofficial by the club |
| 2 | Club charts lag the official injury report | 12 players are 1st/2nd string on a club chart while Out/Doubtful on nfl.com (e.g. GB Josh Jacobs) |
| 3 | 3 Out players absent from their own club chart | DET Kerby Joseph, GB Micah Parsons, KC Omarr Norman-Lott |
| 4 | Three official stat tables render with no header row | offense/scoring, defense/scoring, defense/downs — withheld, not guessed |
| 5 | Passing tables render 15 columns; only 8 confirmable | reconciliation with the player leaderboard confirms Att/Cmp/Cmp%/Y/A/Yds/TD/INT/Rating only |
| 6 | "Teams on Bye" panels print **current** records, not as-of-week | week-10 page shows CHI 7-2 etc. |
| 7 | NFL.com hosts **no odds page** | https://www.nfl.com/odds/ → 404. No market prices were obtainable |
| 8 | 2026 rosters differ from recent history (Garrett→Rams, Lawrence→Bengals, Murray→Vikings, Parsons→Packers, Nelson→Seahawks, Evans→49ers, A.J. Brown→Patriots, Donald active) | as printed on official 2026 pages; flagged for the reviewer to sanity-check the data environment |
| 9 | A.J. Brown's official game log shows 5 rows with a Wk 2–Wk 5 gap | https://www.nfl.com/players/a-j-brown/stats/logs/2026/ |
| 10 | Home teams won only 48.91% of 137 games (mean home margin −0.022 pts) | replay of the official by-week pages; SE 1.13 so the CI still contains conventional HFA |

## Sources used

Official only. Full list with what each page provided: `docs/sources.html`.

* https://www.nfl.com/standings/division/2026/REG
* https://www.nfl.com/schedules/2026/by-week/week-N (N = 1..9) and https://www.nfl.com/schedules/2026/reg10
* https://www.nfl.com/injuries/league/2026/reg10
* https://www.nfl.com/stats/team-stats/{offense,defense}/{passing,rushing}/2026/reg/all
* https://www.nfl.com/stats/player-stats/category/passing/2026/reg/all/passingyards/desc
* https://www.nfl.com/players/{drake-maye,hunter-henry,a-j-brown,rhamondre-stevenson,joe-burrow,ja-marr-chase}/stats/logs/2026/
* https://www.{patriots,detroitlions,packers,chiefs,49ers}.com/team/depth-chart (club-published, unofficial)
* https://www.nfl.com/legal/flexible-scheduling-procedures

## Verification performed

1. **Standings replay** — all 137 games replayed; W-L-T, PF, PA match the official standings for
   **32/32 teams**.
2. **Game-log reconciliation** — Drake Maye's per-game log sums to his official leaderboard row.
3. **Column reconciliation** — Cmp÷Att and Yds÷Att per team reproduce the published Cmp% and Y/A.
4. **No-look-ahead audit** — the walk-forward harness excludes 32 week-1/week-2 games; the training
   buffer is appended after each prediction.
5. **Cross-source injury check** — Out/Doubtful statuses intersected with club depth charts.
6. **Site link check** — `python3 tools/check_links.py`: internal links, Source-column presence and
   row cell counts all pass; external URLs enumerated (they cannot be validated from this sandbox).

## Integration record

* Re-verification: performed, see above.
* Site build: `python3 tools/build_site.py` → 18 pages; `python3 tools/check_links.py` → OK.
* PR: _pending_
* Merge: _pending_
* Pages deploy: _pending_
