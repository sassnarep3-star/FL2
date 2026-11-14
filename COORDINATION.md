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
| T1 | Repo review (line-by-line) | done | arena-48561869-fl2 | `README.md`, `.git` metadata | Repo contained only `README.md` (`# FL2`) at base commit `0f3d2f9`. Reviewed 2026-11-14. Findings on `repo-review.html`. |
| T2 | Official-source research & verification | done | arena-48561869-fl2 | `data/verified/*.json`, `data/verified/fetch-log.md` | Fetched nfl.com standings/schedules/injuries, Lions depth chart, NFL roster cross-check. 32 standings teams, 14 Week 10 games + 4 byes, 345 injury rows across 28 teams, 28 depth rows. Fetch log records each fetch. |
| T3 | Executive summary | done | arena-48561869-fl2 | `executive-summary.html` | Objective, repo state, verified data, strategy status, decisions needed, flagged summary. |
| T4 | Questions / information / answers register | done | arena-48561869-fl2 | `questions-answers.html` | 6 answered items with official sources; 12 open questions (Q1–Q12) each mapped to a discovery suggestion. |
| T5 | Suggestions section (review before implementation) | done | arena-48561869-fl2 | `suggestions.html` | 12 decision-gating suggestions (S1–S12) + 6 site-improvement suggestions (S13–S18); review process and decision log. |
| T6 | Line-origination strategy research | done | arena-48561869-fl2 | `strategies.html`, `leaderboard.html` | Signal families, single/parlay/prop construction, validation gates G1–G9, correlation methodology (values intentionally blank), luck-removal metrics. No strategies registered (no verified odds feed). |
| T7 | Injury & depth-deficiency tracking design | done | arena-48561869-fl2 | `injuries.html`, `data/verified/injuries-week10.json`, `data/verified/depth-lions-2026.json` | Verified Week 10 injury report for 28 teams; Lions depth chart example; tracking design for starter/backup substitution on offense & defense. |
| T8 | Site build (landing page + category subpages) | done | arena-48561869-fl2 | all site files at repo root | Static HTML/CSS/JS, 12 pages, dashboard style, tables render from verified JSON with per-row official source links. Internal link check passed; all JSON validated. |
| T9 | Flagged for Review page | done | arena-48561869-fl2 | `flagged-review.html` | 5 irregularities (F1–F5), 7 unverified/blank items (U1–U7) with source links. |
| T10 | Final integration, PR, merge, Pages verification | in progress | arena-48561869-fl2 | `COORDINATION.md`, PR | Data re-verified, internal links confirmed, site builds; PR to be merged and Pages confirmed live. |

## Claim history

- 2026-11-14 — Session `arena-48561869-fl2` claimed T1–T9 and reserved T10 (integration)
  for completion in the same session. Claim committed and pushed.

## Handoffs

None.

## Completed task records (sources, verification, irregularities)

**T1 Repo review.** Verified via `git` (log, tree, remotes) and GitHub API. Base commit
`0f3d2f9e87f44409fa02fd94aa5d474f58b300a5` contained exactly `README.md` (`# FL2`).
Pages already enabled at `main / /`. Evidence links on `repo-review.html`.
Irregularity: Pages enabled with no prior content; no license (S16 pending).

**T2 Verification.** Every verified value fetched directly from official pages on 2026-11-14:
- Standings: https://www.nfl.com/standings/ (all 32 teams, verified line by line)
- Schedule: https://www.nfl.com/schedules/ (Week 10, 14 games + 4 bye teams; TNF final: WAS 24 @ NYG 21)
- Injuries: https://www.nfl.com/injuries/ (Week 10; 28 teams; 345 rows; 66 Out; 94 Questionable/Doubtful)
- Roster cross-check: https://www.nfl.com/teams/detroit-lions/roster
- Depth chart: https://www.detroitlions.com/team/depth-chart (28 position rows, offense/defense/ST)
Irregularity F2: per-team injury URL patterns (`/injuries/team/...`, `/injuries/teams/...`) return 404 —
rows cite the main official injury report instead.

**T3–T6 Documentation.** Content is design/documentation; no external facts claimed without a source.
Factual claims link to the official sources above. No strategies registered and no line/odds values
published because no verified odds feed is selected (Q1/Q2 open) — left blank and flagged (U1), not guessed.

**T7 Injury & depth tracking.** Verified Week 10 designations for all 28 playing teams; bye teams
(CHI, DEN, PHI, TB) have no Week 10 report — recorded as "no report," not "healthy" (U3). Lions depth
chart verified as a worked example; teams label their charts "unofficial" (F1). Full 32-team depth
coverage pending Q8/S8 (U4). Historical archive pending Q7/S7 (U5).

**T8 Site build.** 12 HTML pages, shared `assets/style.css` and `assets/app.js`. Tables render from
`data/verified/*.json`; each data row links to its official source. Verified: all JSON files parse;
all internal links resolve across the 12 pages.

**T9 Flagged items.** F1 (team-labeled "unofficial" depth chart), F2 (404 per-team injury URLs),
F3 (third-party aggregator inconsistency — official page used), F4 (Pages enabled pre-content),
F5 (no license). U1–U7 list every intentionally blank item and what would un-flag it.
