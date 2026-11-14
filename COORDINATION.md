# COORDINATION.md — Shared Task Board

Repo: `sassnarep3-star/FL2`
Base commit: `0f3d2f9e87f44409fa02fd94aa5d474f58b300a5` (main)
Session branch: `arena/1374049c-fl2`
Session ID: **session-1374049c**

> Protocol: claim a task by writing your session ID + file scope here, then commit and push
> that claim immediately. Never start a task another session has claimed. Keep scopes
> non-overlapping. Small frequent commits; `git pull --rebase` before every push.
> If a claim is >60 minutes old with no commits, another session may take it over and log the handoff.

## Environment notes (read before starting)

* **Bash/sandbox network is restricted** to `github.com`, `codeload.github.com`, `api.github.com`,
  `registry.npmjs.org`, `pypi.org`, `files.pythonhosted.org`. `curl https://www.nfl.com` fails (SSL_ERROR_SYSCALL).
* **Official pages must be fetched with the `fetch_page` / `web_search` tools**, which do have general
  web access. All data collection goes through those tools and is cached to `data/raw/`.
* Publication target: GitHub Pages from `/docs` on `main`.

## Task board

| # | Task | Status | Owner | Files in scope | Sources used | Verification |
|---|------|--------|-------|----------------|--------------|--------------|
| T01 | Repo review (line by line) | **done** | session-1374049c | `research/repo-review.md`, `docs/pages/repo-review.html` | repo git history | See file; repo had exactly 1 file (`README.md`, 5 bytes) at base commit |
| T02 | Requirements register | **done** | session-1374049c | `docs/pages/requirements.html`, `data/requirements.json` | Derived from the user's brief | Each requirement traced to a verbatim quote from the brief |
| T03 | Open questions / known-unknowns | **done** | session-1374049c | `docs/pages/questions.html`, `data/questions.json` | Official sources where an answer exists | Answered rows carry an official link; unanswered rows are blank + flagged |
| T04 | Suggestions backlog (review & choose path) | **done** | session-1374049c | `docs/pages/suggestions.html`, `data/suggestions.json` | — | Each suggestion has explicit accept/defer decision slots |
| T05 | Official data acquisition: standings | **done** | session-1374049c | `data/raw/standings.md`, `data/standings.json` | https://www.nfl.com/standings/ | Hand-checked vs. live page |
| T06 | Official data acquisition: Week 10 injury report | **done** | session-1374049c | `data/raw/injuries-reg10.md`, `data/injuries.json` | https://www.nfl.com/injuries/league/2026/reg10 | Row-by-row vs. live page |
| T07 | Official data acquisition: game results reg1–reg10 | **done** | session-1374049c | `data/raw/week-*.md`, `data/games.json` | https://www.nfl.com/schedules/2026/by-week/week-N | Cross-checked against team records on standings page |
| T08 | Official data acquisition: team offense/defense stats | **in progress** | session-1374049c | `data/raw/teamstats-*.md`, `data/team_stats.json` | https://www.nfl.com/stats/team-stats/ | vs. live page |
| T09 | Depth-chart acquisition (all 32 clubs) | **done** | session-1374049c | `data/depth_charts.json` | `{club}.com/team/depth-chart` | **IRREGULARITY: club depth charts are labelled "Unofficial" by the clubs themselves. Flagged on Flagged-for-Review page.** |
| T10 | Player game logs (prop-correlation sample) | **done** | session-1374049c | `data/player_logs.json` | https://www.nfl.com/players/{slug}/stats/logs/2026/ | vs. live page |
| T11 | Analytics engine: power ratings, margins, correlations | **done** | session-1374049c | `tools/analytics.py` | computed from T05–T10 | Deterministic; re-runnable; outputs `data/derived/*.json` |
| T12 | Strategy catalogue + validation gates | **done** | session-1374049c | `docs/pages/strategies.html`, `docs/pages/validation.html`, `data/strategies.json` | math derived in-repo | Formulas shown in-repo, not copied from any unverified source |
| T13 | Leaderboard / rewards design | **done** | session-1374049c | `docs/pages/leaderboard.html`, `data/leaderboard.json` | — | No performance claims fabricated; all rows blank until strategies run |
| T14 | Site build (landing + subpages by category) | **done** | session-1374049c | `docs/**` | — | Link checker in `tools/check_links.py` |
| T15 | Final integration, link check, PR + merge, Pages deploy | **in progress** | session-1374049c | `COORDINATION.md`, `docs/**` | — | Deploy status recorded below |

## Handoff log

| Timestamp (UTC) | Session | Event |
|-----------------|---------|-------|
| 2026-11-14 | session-1374049c | Repo inspected at base commit; only `README.md` (5 bytes) present. No other sessions active. Claimed T01–T15. |

## Irregularities / things a human must look at

See `docs/pages/flagged.html` for the full, source-linked list. Summary:

1. **NFL does not publish official depth charts.** The only depth charts available are on club
   websites and are explicitly captioned "Unofficial … reflects the opinions of the [club].com writers".
   Any "1st/2nd/3rd/4th string" column in this project inherits that caveat.
2. **No official NFL source publishes betting lines/odds.** Every market price on this site is blank
   until a licensed feed is connected. Nothing has been estimated.
3. **Club-site depth charts lag injuries.** A player listed as `Out` on the official NFL injury report
   may still appear at the top of the club depth chart, because the club page is not updated daily.
4. **`Ben Brown` appears twice** on the Patriots depth chart (LG #1 and C #2) — normal, but it means
   "starter counts" per team cannot be summed from the depth-chart rows alone.
