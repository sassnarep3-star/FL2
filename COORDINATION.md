# COORDINATION - shared task board

Repo: `sassnarep3-star/FL2` · Session: `d263eab0` · Branch: `arena/d263eab0-fl2` (fixed for this session; see F-03 in flags)
Base: `main` @ `0f3d2f9`

Status values: `unclaimed` · `in progress` · `done` · `needs review` (published on the Flagged for Review page; does not block anything)

Rule used: one session owns each file scope below. Logged handoffs and conflicts appear in the Log section.

## Task board

| ID | Task | Status | Owner (session) | File scope | Sources | Verification | Irregularities |
|---|---|---|---|---|---|---|---|
| T1 | Repo review, line by line | done | d263eab0 | `README.md`, repo structure | Repo on GitHub (`main`, commit 0f3d2f9) | Read every tracked file (only `README.md`). Checked remote, branches, auth. | F-01, F-03, F-04 |
| T2 | Injury tracking - NFL.com Week 10 report | done (needs second pass) | d263eab0 | `data/injuries_2026_week10.csv`, `data/news_2026_week10.csv` | [NFL.com injury report](https://www.nfl.com/injuries/) (8 pages); profile spot-checks: [Kam Curl](https://www.nfl.com/players/kamren-curl/), [Jacob Hummel](https://www.nfl.com/players/jake-hummel/) | Per-team counts match page sections (28 teams, 345 rows). One transcription pass. 2 of 345 profile links spot-checked (both match). | F-05, F-06, F-07, F-08, F-09, F-13 |
| T3 | Schedule & game list - Week 10 | done | d263eab0 | `data/games_2026_week10.csv` | [NFL.com schedule](https://www.nfl.com/schedules/2026/REG10) (3 pages) | 14 games, away/home from official game URLs, bye teams listed on page. | F-05 |
| T4 | Starter/backup (depth chart) tracking | needs review | d263eab0 | (none yet) | Roster page sampled: [BUF roster](https://www.nfl.com/teams/buffalo-bills/roster) | Depth chart URL NOT yet confirmed. Unit exposure shows counts only. | F-10, Q6 |
| T5 | Unit exposure (offense/defense counts) | done (descriptive) | d263eab0 | `docs/unit-exposure.html`, generated JSON | Derived from T2 | Counts recomputed by build script; no starter inference. | F-10 |
| T6 | Lines origination and strategy research | needs review (blocked) | d263eab0 | `data/strategies.json`, `docs/strategies.html` | None verified | No historical odds or outcomes available. Framework and gates written; zero strategies evaluated; correlation not computed. | F-11, F-12 |
| T7 | Suggestions section (no changes implemented) | done | d263eab0 | `data/suggestions.json`, `docs/suggestions.html` | Derived from T1-T6 | Each suggestion lists needed data and risk. | - |
| T8 | Open questions & information gaps | done | d263eab0 | `data/questions.json`, `docs/questions.html` | - | Each question shows verified / missing / how to close. | Q1 legal status unverified (F-14) |
| T9 | Executive summary | done | d263eab0 | `docs/executive-summary.html` | Links in the page | Every number checked against the build meta (345 / 28 / 66 / 10 / 84 / 14). | F-05, F-08, F-06 |
| T10 | Source register | done | d263eab0 | `data/sources.json`, `docs/sources.html` | S1-S7 | Each source records how it was accessed and its verification level. | S7 unusable (TLS) |
| T11 | Static site (landing + category pages) | done | d263eab0 | `docs/**`, `scripts/make_pages.py`, `scripts/build_site.py` | Built from data files | Build validates row counts, nfl.com URLs, source IDs, internal links. jsdom run: all 11 pages execute with no errors. | - |
| T12 | Flagged for Review page | done | d263eab0 | `data/flags.json`, `docs/flagged.html` | Links on the page | Lists 15 flags with source links. | F-01 ... F-15 |
| T13 | Integration: build, PR, merge, GitHub Pages | in progress (PR next) | d263eab0 | `.github/` (none), repo settings | - | See Log. | - |

## Sources used (all accessed 2026-11-14)

- [NFL.com - 2026 Injury Report, Week 10](https://www.nfl.com/injuries/) - official
- [NFL.com - 2026 Schedule, Week 10](https://www.nfl.com/schedules/2026/REG10) - official
- [NFL.com - Notable injuries, Week 9 games](https://www.nfl.com/news/notable-injuries-news-sunday-week-9-games-2026) - official
- [NFL.com - Buffalo Bills roster (sample)](https://www.nfl.com/teams/buffalo-bills/roster) - official, sample only
- [NFL Football Operations](https://operations.nfl.com/) - official, homepage only
- [nflverse-data releases](https://github.com/nflverse/nflverse-data/releases) - community, NOT used (download blocked)

## Log

- **Claim (d263eab0)**: T1-T13 claimed by this session. Branch is fixed to `arena/d263eab0-fl2`; no other branch used.
- **Handoffs / conflicts**: none. No other session was active on this repo at the time of claiming; `main` had only the initial commit.
- **Blocked by environment**: `nflverse-data` asset download failed (TLS error, curl exit 35) from the sandbox. Only `api.github.com` metadata was readable. Lines and historical data are therefore not in the repo (F-11, F-12).
- **Profile spot-check**: two player links flagged in F-09 were opened on NFL.com; both resolve to the named player (Kam Curl, LAR SAF; Jacob Hummel, LB). Flag kept at Low for the team of Hummel.
- **Sandbox browser**: Chromium download for end-to-end testing was blocked; page scripts were verified with jsdom instead (all 11 pages, no script errors).

## Pull request and merge

- PR: _(to be filled after creation)_
- Merge result: _(to be filled)_
- GitHub Pages deploy: _(to be filled)_
