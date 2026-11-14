# Coordination board

This repository had no coordination board or existing task claims when session `arena/4a77261b-fl2` began.

> **Branch constraint:** Arena requires this session to remain on `arena/4a77261b-fl2`; this session cannot create or switch to the requested `session-<id>/<task>` worktree/branch. No other task claims or active sessions are visible in the checkout. Scope below is therefore kept to this current branch.

| Task | Status | Owner | Files in scope |
|---|---|---|---|
| Inspect repository; establish evidence-led NFL research/dashboard structure and publish a GitHub Pages site with verified-source tables, decision questions, strategy validation, injury/lineup tracking, and flagged unknowns | done | arena/4a77261b-fl2 | `COORDINATION.md`, `README.md`, `index.html`, `*.html`, `assets/*`, `.github/workflows/*`, `scripts/check_site.py`, `.nojekyll` |

## Log

- 2026-11-14 — Initial inspection: repository contains only a five-byte `README.md`; no existing app, data, coordination board, or other claims. Current branch is `arena/4a77261b-fl2` at base `0f3d2f9`.
- 2026-11-14 — Claimed the single-session site/research scope. Evidence will be restricted to linked primary/official sources; items that cannot be confirmed from such sources will be blank and flagged, not estimated.

## Source and verification record

- Official NFL pages inspected using the web fetch tool on 2026-11-14 UTC: [player stats](https://www.nfl.com/stats/player-stats/), [injury reports](https://www.nfl.com/injuries/), [schedules/game pages](https://www.nfl.com/schedules/), [player directory](https://www.nfl.com/players/), and the [2026 Football Operations rulebook](https://operations.nfl.com/rules-officiating/2026-nfl-rulebook). These are dynamic official pages; we verified the existence and displayed categories, not a durable API, historical completeness, values copied into the site, or reuse rights.
- Inspected one [NFL-hosted official gamebook sample](https://static.www.nfl.com/image/upload/v1766722063/gamecenter/f91b71fe-311e-11f0-b670-ae1250fadad1.pdf). It contains game statistics/play-by-play and an explicit copyright notice: use is for assisting media coverage; other use is prohibited without written NFL permission. Flagged this reuse requirement in `data.html` and `review.html`; no NFL gamebook values were copied into the dashboard.
- Inspected NIST/SEMATECH [statistical glossary](https://www.itl.nist.gov/div898/handbook/glossary.htm) for correlation and cross-validation definitions. This is a general methods source, not NFL evidence and not proof that any strategy works.
- Inspected [GitHub Pages official documentation](https://docs.github.com/en/pages) and [Pages site](https://pages.github.com/) for a static site / Actions deployment path.
- Added only source pathway descriptions and research/validation proposals. All live player/injury/market/performance/correlation values remain blank and are flagged; no picks or ROI claims were produced.
- Local verification: `python3 scripts/check_site.py` passed across all seven top-level HTML pages (68 linked table rows including strategy conversion methods). It checks local links and requires each data row in an HTML table to have a link on an NFL, NIST, or GitHub official host. It does not claim external links are permanently available or check provider reuse terms.
- Local HTTP smoke test returned HTTP 200 for the overview, all five category pages, and the stylesheet. `git diff --check` passed. No numeric NFL performance values were copied into project tables.
- 2026-11-14 — Completed site/research framework and flagged review ledger. Pull request [#1](https://github.com/sassnarep3-star/FL2/pull/1) merged to `main` at `da97a35109dace3a6034445cf117771beafa9fd2` on 2026-11-14 02:58:54 UTC. Validation and Pages deploy workflow run [43549190344](https://github.com/sassnarep3-star/FL2/actions/runs/43549190344) passed; GitHub Pages reports `built` at `https://sassnarep3-star.github.io/FL2/` for the merge commit. The final deployed artifact and local link checks passed.

## Irregularities / handoffs

- The user requested multiple `session-<id>/<task>` branches/worktrees and a final integration branch; Arena's active-branch restriction prevents branch switching or creation. Work remained on the assigned branch. No concurrent claims were present at inspection.
- The repo initially contained no NFL data, source records, build tooling, or Pages configuration; these were added as a static evidence dashboard and Pages workflow.
- NFL's inspected gamebook sample has a restrictive copyright/use notice. Bulk/republication/analytical reuse permission is not established and is a blocking open item before data ingestion or redistribution.
- GitHub Pages must be configured for **GitHub Actions** in repository settings; automated deployment runs on `main`, not on this session branch. A pull request will run structural validation but not publish the draft branch.

---

# Session d263eab0 - NFL dashboard (Week 10 data) - added after merge conflict

> **Parallel-session note:** this session (`arena/d263eab0-fl2`) started from the same base (`0f3d2f9`) as session `arena/4a77261b-fl2`. Both sessions built a Pages site, so scope overlapped. Both sites are kept: the root site (Fourth & Signal, session 4a77261b) is unchanged, and this session's dashboard is published under `docs/`. Consolidation is logged as a decision for the user (see `docs/suggestions.html` SG-11).


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

### Integration log (d263eab0)

- **Merge conflict (handled):** `COORDINATION.md` and `README.md` were add/add conflicts with `main` (commits from PRs #1, #2, #4 by session `arena/4a77261b-fl2`). Resolved by keeping that session's content in full and appending this session's sections. Nothing was discarded. Merge commit `bd7c0de`, then a second merge of `main` at `2c7b915` (clean).
- **Overlapping sites (logged):** session `4a77261b` published a root site (Fourth & Signal). This session published a data dashboard in `docs/`. Both are kept and cross-linked from the nav. Consolidation is suggestion SG-11 for your decision.
- **Shared-file edits made in integration:** added a "Week 10 data" link to the nav of the six root pages; added a build step to `.github/workflows/pages.yml` (validate job). No other root content changed.
- **Parallel activity seen:** a third session `arena/d10a1d25-fl2` (fetch-nflverse-data) was running CI on GitHub during this session. Its scope is not in this branch and was not touched. Its results, if merged, may affect the lines and historical-data gaps (F-11, F-12).
- **Pages config:** before this merge the repo's Pages build was `legacy` from `main /`. The workflow deploys with GitHub Actions. Check after merge (see below).
- **PR:** https://github.com/sassnarep3-star/FL2/pull/3 (validate job passed on the PR: `pass`).
