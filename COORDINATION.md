# COORDINATION.md — FL2 Shared Task Board

This is the shared task board for the FL2 project. Multiple agent sessions may work on
this repo at the same time. Read this file before starting any task.

- **Session ID for this session:** `arena-48561869-fl2`
- **Branch policy note:** Arena fixes this session to branch `arena/48561869-fl2`
  (branched from `0f3d2f9e87f44409fa02fd94aa5d474f58b300a5` of `main`, status: active).
  Sessions may not create or switch to other branches in this environment, so the
  `session-<id>/<task>` branch convention is adapted: all work for every task is done
  sequentially on `arena/48561869-fl2` with small, frequent commits. The final
  integration role described below is performed in-session by this same session on this
  branch. Scopes remain non-overlapping by task/file ownership as listed below.
- **Claim rule:** Claim a task by writing your session ID and file scope here, then
  commit and push the claim immediately. Never start a task another session has claimed.
- **Status values:** `unclaimed` | `in progress` | `done` | `needs review`
- `needs review` = published on the Flagged for Review page and does not block anything.
- **Data rule:** Never mark anything verified without checking it against an official
  source, and link that source. If a value cannot be confirmed from an official source,
  leave it blank and flag it as unverified. Never infer or fill in values.
- **Handoff rule:** If a session crashes or its claim is more than 60 minutes old with no
  commits, any other session may take over the task and note the handoff here.

## Sessions

| Session ID | Branch | Role | Active |
| --- | --- | --- | --- |
| `arena-48561869-fl2` | `arena/48561869-fl2` | All tasks below, including final integration | yes |

## Task Board

| # | Task | Status | Owner | File scope | Notes |
| --- | --- | --- | --- | --- | --- |
| T1 | Repo review (line-by-line) | in progress | arena-48561869-fl2 | `README.md`, `.git` metadata | Repo contains only `README.md` (`# FL2`) at base commit `0f3d2f9`. Reviewed 2026-11-14. |
| T2 | Official-source research & verification | in progress | arena-48561869-fl2 | `data/verified/*.json`, `docs/site` (verification pages) | Sources: nfl.com standings/schedules/injuries/rosters. Fetch log kept in `data/verified/fetch-log.md`. |
| T3 | Executive summary | in progress | arena-48561869-fl2 | `docs/site/executive-summary.html` | Key findings, scope, current state. |
| T4 | Questions / information / answers register | in progress | arena-48561869-fl2 | `docs/site/questions-answers.html` | Questions that must be answered before decisions; missing info flagged. |
| T5 | Suggestions section (review before implementation) | in progress | arena-48561869-fl2 | `docs/site/suggestions.html` | Suggestions with pros/cons/effort; a reviewer picks the best path before any change. |
| T6 | Line-origination strategy research (single bet, parlays, player props, leaderboard, validation gates, correlation, luck removal) | in progress | arena-48561869-fl2 | `docs/site/strategies.html`, `docs/site/leaderboard.html` | Methodology documents; no fabricated line values. |
| T7 | Injury & depth-deficiency tracking design | in progress | arena-48561869-fl2 | `docs/site/injuries.html` | Track starters/backups (2nd/3rd/4th string) for offense & defense. |
| T8 | Site build (landing page + category subpages, dashboard, tables) | in progress | arena-48561869-fl2 | `docs/site/*` (all HTML/CSS/JS) | GitHub Pages builds from `main / /`. |
| T9 | Flagged for Review page | in progress | arena-48561869-fl2 | `docs/site/flagged-review.html` | Irregularities + unverified items with source links. |
| T10 | Final integration, PR, merge, Pages verification | pending | arena-48561869-fl2 | `COORDINATION.md`, PR | Re-verify combined data, confirm build/no broken links, merge, confirm Pages live. |

## Claim history

- 2026-11-14 — Session `arena-48561869-fl2` claimed T1–T9 and reserved T10 (integration)
  for completion in the same session. Claim committed and pushed.

## Handoffs

None.

## Completed task records (sources, verification, irregularities)

_Filled in per task when marked done._
