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

- PR #3: https://github.com/sassnarep3-star/FL2/pull/3 (branch `arena/d263eab0-fl2` into `main`). Validate job passed on the PR.
- Merge result: merged with a merge commit at `baf52ad7d1072a1f5501e9278e523d19f84f54a5` on 2026-11-14 03:02:41 UTC (`gh pr merge 3 --merge`).
- GitHub Pages deploy: workflow `Validate and publish site` run 43549532304 on `main` (validate + deploy jobs) succeeded; `pages-build-deployment` run 43549531557 succeeded; Pages build status `built` for commit `baf52ad`. Live: https://sassnarep3-star.github.io/FL2/docs/ (fetched and rendered 345 injury rows).
- Follow-up: label fix for the injuries Category column, PR opened from the same branch (see Log).

### Integration log (d263eab0)

- **Merge conflict (handled):** `COORDINATION.md` and `README.md` were add/add conflicts with `main` (commits from PRs #1, #2, #4 by session `arena/4a77261b-fl2`). Resolved by keeping that session's content in full and appending this session's sections. Nothing was discarded. Merge commit `bd7c0de`, then a second merge of `main` at `2c7b915` (clean).
- **Overlapping sites (logged):** session `4a77261b` published a root site (Fourth & Signal). This session published a data dashboard in `docs/`. Both are kept and cross-linked from the nav. Consolidation is suggestion SG-11 for your decision.
- **Shared-file edits made in integration:** added a "Week 10 data" link to the nav of the six root pages; added a build step to `.github/workflows/pages.yml` (validate job). No other root content changed.
- **Parallel activity seen:** a third session `arena/d10a1d25-fl2` (fetch-nflverse-data) was running CI on GitHub during this session. Its scope is not in this branch and was not touched. Its results, if merged, may affect the lines and historical-data gaps (F-11, F-12).
- **Pages config:** before this merge the repo's Pages build was `legacy` from `main /`. The workflow deploys with GitHub Actions. Check after merge (see below).
- **PR:** https://github.com/sassnarep3-star/FL2/pull/3 (validate job passed on the PR: `pass`).
- **Follow-up after merge**: the Injuries page labelled every row without a designation as 'Injury'. Fixed to 'Injury listed' / 'No injury listed' / 'Not injury related' (commit `9803c79`), delivered as a second PR from the same branch (no change to any other branch).

### Final record (d263eab0)

- **PR #3** (`arena/d263eab0-fl2` to `main`, full dashboard): merged, commit `baf52ad`. Pages deploy run 43549532304 succeeded.
- **PR #5** (label fix, same branch): merged, commit `708601d`. Validate + deploy runs succeeded; Pages status `built` for `708601d`.
- **Live check (fetched 2026-11-14):** https://sassnarep3-star.github.io/FL2/docs/injuries.html shows 345 entries, with Category labels "Injury listed / No injury listed / Not injury related". Root site https://sassnarep3-star.github.io/FL2/ also renders.
- **Pages config:** the repo's Pages build type is `legacy` (from `main /`); the deployment that runs is the Actions workflow. Both report `built`. Not changed, to avoid disturbing the other session's site.
- **Open items:** F-06 to F-14 remain open for your review (Flagged for review page). Starter/backup status, betting lines and strategy results remain blank pending verified sources.
- **Not done:** no strategy was evaluated and no lines were originated; no verified odds or historical data was accessible from this sandbox.


---

# Session e70150db — NFL Decision Hub (merged `main` at `c2ed442`)

> **What happened here, plainly.** This session started from base `0f3d2f9`, the same base as sessions
> `4a77261b` and `d263eab0`. By the time this session pushed, both had already merged their own sites to `main`
> (PR #1–#6): a research framework at `/` ("Fourth & Signal") and a data dashboard at `/docs/`. **Nothing of theirs
> was discarded.** This session's work was re-namespaced into `/hub/` so all three sites coexist, and cross-links
> were added in both directions. That was the right call rather than a merge race: three independent takes on the
> same brief are more useful side by side than one averaged take.

## What this session owns

| Path | Contents |
| --- | --- |
| `hub/` | 16-page Decision Hub site (this session only) |
| `tools/` | 8 generator scripts (this session only) |
| `data/*.csv`, `data/*.json` (the files listed below) | Verified datasets (this session only) |
| `docs/EXECUTIVE-SUMMARY.md` | Executive summary (this session only) |

**Explicitly not owned and not edited in substance:** `index.html`, `decisions.html`, `strategy.html`,
`availability.html`, `data.html`, `review.html`, `404.html`, `assets/site.css`, `scripts/`, `.github/workflows/`,
`docs/*.html`, `docs/data/`, `data/injuries_2026_week10.csv`, `data/games_2026_week10.csv`, `data/news_*.csv`,
`data/flags.json`, `data/questions.json`, `data/sources.json`, `data/strategies.json`, `data/suggestions.json`.
The only change made to those was appending a single navigation link to `hub/index.html` in each nav bar
(7 root pages + 11 dashboard pages), so the three sites are reachable from one another. No other content was touched.

## Cross-verification with session d263eab0 — the strongest check in this project

Two sessions independently transcribed the **same** source (the NFL Week 10 injury report) at different row
granularities: `data/injuries_2026_week10.csv` (345 rows, all listed players) and
`data/injury-report-2026-w10.csv` (160 rows, only those carrying an official game status). Comparing them:

| Comparison | Result |
| --- | --- |
| Rows carrying a game status in their file | 160 |
| Rows in this session's file | 160 |
| Matched on club + player | **160 / 160** |
| Agreement on **game_status** | **160 / 160 (100%)** |
| Agreement on **practice_status** | **160 / 160 (100%)** |

That is two independent transcription passes of an official source agreeing completely on every field that matters
for availability. It is far stronger evidence than a single pass, and it is the reason the injury dataset in `hub/`
is presented as verified rather than merely transcribed. The comparison used a club-abbreviation map
(`LA`→`LAR`, `WAS`→`WSH`, `JAX`→`JAC`) and a practice-status normalisation; both were cosmetic only.

## Sites now published (all from `main`)

| Path | Site | Session |
| --- | --- | --- |
| `/` | Fourth & Signal — research framework, decision brief, flagged review | `4a77261b` |
| `/docs/` | Week 10 data dashboard — 345 injury rows, unit exposure, games, news | `d263eab0` |
| `/hub/` | Decision Hub — verified datasets, requirements, decision questions, strategies, gates, correlation, depth | `e70150db` |

## Verification performed on the merged tree

| Check | Command | Result |
| --- | --- | --- |
| This session's site: links, anchors, sources, no CDN, no placeholder leaks | `python3 tools/check_links.py` | pass — 16 pages, 22 sources |
| Previous session's site: structure + sourced rows | `python3 scripts/check_site.py` | pass — 7 pages |
| Data reproducibility from a clean tree | wipe generated artefacts, re-run 7 generators, byte-compare | pass — 27/27 files identical |
| HTML structure | stdlib `HTMLParser` open/close matching, all 16 hub pages | pass — 0 errors |
| Injury cross-transcription | 160/160 agreement against `data/injuries_2026_week10.csv` | pass |
| Arithmetic cross-checks | win pct, net points, pass %, Y/A, PPG vs NGS, bye list | pass — all asserted in the build scripts |

## Irregularities introduced and then fixed during this integration

- While re-namespacing, `assets/` was moved to `hub/assets/`, which temporarily broke the root site's stylesheet
  link. **Fixed immediately** by restoring `assets/` from `origin/main` and scoping this session's link checker to
  `hub/` only. Both checkers pass on the final tree; this is logged because a reviewer should know it happened.

## Flagged items (unchanged, all published on `hub/pages/flagged.html`)

F01 depth charts missing for 30/32 clubs · F02 no league-wide official depth endpoint (404, recorded as S17) ·
F03 no odds data anywhere · F04 injury labels have no published predictive value · F05 DET/MIN 0.05 rounding ·
F06 NGS EPA published for 16/32 clubs · F07 league gambling policy constrains the product · F08 primary
deliverable undefined · F09 "reward" undefined. **None of these block the merge.**

## Open decisions for the owner (cannot be made by an agent)

1. **Consolidate the three sites?** Three sites on one repo is honest but not tidy. Recommendation: keep them —
   `/` for the framework, `/docs/` for the raw Week 10 data, `/hub/` for the verified decision layer — and add a
   single chooser at `/` later. This is the same conclusion session `d263eab0` reached as its suggestion SG-11.
2. **Buy a licensed historical odds archive** (hub Q01/Q02/Q03/Q15). Unblocks 9 of 12 strategies.
3. **Pre-register the strategy registry and set a sample floor** (hub Q04/Q05). Free, immediate.
4. **Decide what this is: research artefact, product, or syndicated betting operation** (hub Q17).
   Recommended default: research artefact that publishes lines and does not place bets.

## Pull request and merge result

| Item | Value |
| --- | --- |
| PR | https://github.com/sassnarep3-star/FL2/pull/7 |
| Branch | `arena/e70150db-fl2` → `main` |
| Base seen at open | `c2ed442` (two other sessions' merges already on `main`) |
| Conflicts | `COORDINATION.md`, `README.md`, `index.html` — all add/add or content, all resolved without discarding either side |
| Merge method | `--merge`, merged without waiting for approval |
| Merge result | **merged** 2026-11-14 03:09:22 UTC, merge commit `027a8bc0a2ee0db36a5b90953cda2a56e2c0e00e` |
| CI on the PR | `validate` job **pass** (run 43550102630); `deploy` skipped on PR as designed |
| CI on `main` after merge | `Validate and publish site` **success**; `pages build and deployment` **success**, both on `027a8bc` |
| Pages API | `status: built`, `build_type: legacy`, `source: main /`, `https://sassnarep3-star.github.io/FL2/` |
| Live verification | Fetched and rendered post-deploy: `/hub/index.html` (KPIs, correlation table, source table), `/hub/pages/flagged.html` (all 9 flags), `/docs/injuries.html` (345 rows, filters intact) |
