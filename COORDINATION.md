# COORDINATION.md — Shared Task Board

**Purpose:** this file is the coordination point for all agent sessions working on `sassnarep3-star/FL2`.
Read it before starting. Claim work here, commit the claim, and record sources + verification when done.

Rules (agreed baseline for all sessions):

1. Never start a task another session has claimed.
2. Work only inside your claimed file scope. If you need to touch another session's file, log a request in **Change Requests** instead of editing it.
3. Small, frequent commits. `git pull --rebase` before every push.
4. Never mark a row "verified" without opening the official source and reading it. Link the source in the row.
5. If a value cannot be confirmed from an official source: leave it blank and add it to **Flagged for Review** (both here and in `flagged-for-review.json`).
6. A claim older than 60 minutes with no commits may be taken over by another session — note the handoff in **Handoffs / Log**.
7. Shared outputs (site index, navigation, `assets/data/*`, merged table data) are changed by the **final integration session** only.
8. An item marked `needs review` is published on the *Flagged for Review* page and **does not block** other work or the merge.

---

## Session registry

| Session ID | Branch | Started (UTC) | Role | Notes |
| --- | --- | --- | --- | --- |
| `arena-be3108f3` | `arena/be3108f3-fl2` | 2026-11-14 02:55 | build + final integration | Repo found empty except a 5-byte `README.md`. This session performs the greenfield build (docs + site) and then acts as the integration session, because it is the only active claimant at start time. |

> Repo state at first look: single commit `0f3d2f9 "Initial commit"`, one file (`README.md`, 5 bytes, content `# FL2`). No data, no code, no CI, no Pages config, no `.nojekyll`. **Irregularity IR-001** — a project described as "collect, organize, analyze" has zero collected data in-repo; all datasets in this build are freshly sourced snapshots, not pre-existing project data.

---

## Task board

Statuses: `unclaimed` · `in progress` · `done` · `needs review`

| ID | Task | Status | Owner | File scope | Sources / verification recorded |
| --- | --- | --- | --- | --- | --- |
| T01 | Repo review + baseline snapshot | done | `arena-be3108f3` | `COORDINATION.md` | `git log`, `git show --stat 0f3d2f9`, file inventory (1 file, 5 bytes) |
| T02 | Full requirements catalogue (R-IDs, acceptance criteria) | in progress | `arena-be3108f3` | `requirements.html` | Derived from user brief; no external source needed |
| T03 | Open questions / information gaps register | in progress | `arena-be3108f3` | `questions.html` | Derived from T02 + data-availability probes |
| T04 | Suggestions register (ranked, decision-ready) | in progress | `arena-be3108f3` | `suggestions.html` | Derived from T02/T03 |
| T05 | Executive summary | in progress | `arena-be3108f3` | `index.html`, `executive-summary.html` | Summarises T06–T12 outputs |
| T06 | Data-source catalogue + access probes | in progress | `arena-be3108f3` | `data-catalog.html` | Each row probed by direct fetch on 2026-11-14; official vs trusted-vs-commercial labelled |
| T07 | Official injury report snapshot, NFL Week 10 2026 | in progress | `arena-be3108f3` | `assets/data/injuries-w10.js`, `injuries.html` | `https://www.nfl.com/injuries/` (official) + club site cross-check `vikings.com` |
| T08 | Availability-adjusted depth analysis (2nd/3rd/4th string) | in progress | `arena-be3108f3` | `availability.html`, `assets/data/depth.js` | `https://www.nfl.com/teams/<club>/depth-chart/` (official) |
| T09 | Line-origination methodology: signals, validation gates, correlation | in progress | `arena-be3108f3` | `methodology.html`, `assets/data/signals.js` | Spec; math refs cited, no live data claims |
| T10 | Leaderboard + rewards design (strategy competition) | in progress | `arena-be3108f3` | `leaderboard.html` | Spec; scoring rubric defined in-repo |
| T11 | Markets page: instrument structure, vig, parlay/prop combo math, compliance | in progress | `arena-be3108f3` | `markets.html` | Sportsbook/legal sources cited; unverified values left blank |
| T12 | Verification log + Flagged for Review page | in progress | `arena-be3108f3` | `verification.html`, `flagged-for-review.html`, `assets/data/flags.js` | Row-level source links |
| T13 | Site scaffold + GitHub Pages publish | in progress | `arena-be3108f3` | `index.html`, `assets/css/*`, `assets/js/*`, `.nojekyll`, `README.md` | Pages API call recorded in log |
| T14 | PR → `main`, merge, deploy confirmation | unclaimed | — | repo-wide | blocked on T02–T13 |

---

## Change requests

_None yet. Sessions that need a shared file (`index.html`, nav, `assets/data/*`) edited: add a row here with the exact diff you want and the reason._

| # | Requested by | File | Request | Status |
| --- | --- | --- | --- | --- |
| — | — | — | no open requests | — |

---

## Handoffs / Log

| When (UTC) | Session | Event |
| --- | --- | --- |
| 2026-11-14 02:55 | `arena-be3108f3` | Board created (file did not exist). Claimed T01–T13. No other claimants found — no `session-*` branches on origin, single commit history. |
| 2026-11-14 02:56 | `arena-be3108f3` | Access probe: sandbox `curl` is restricted to github/npm/pypi hosts, so all live data must come through the fetch/search tools, not shell HTTP. Recorded because it constrains any "auto-refresh at page load" design: the published site cannot depend on sandbox-only credentials. |

---

## Findings worth sharing (read before duplicating work)

- **F-1** `nfl.com/injuries/` is server-rendered and fetchable as markdown tables — this is the official Week-by-Week report (per-club submitted data). Use `?season=2026&week=N` style navigation via the page's year/week selectors; the fetched page title confirms "Week 10 of the 2026 Season".
- **F-2** Club sites (e.g. `vikings.com`) publish the same report with Wed/Thu/Fri participation detail + `NIR - Rest` / `NIR - Personal` designations that the league page collapses. Cross-check both; they disagree on granularity, not on facts.
- **F-3** The league page's `Game Status` column is **empty for most rows** — it is only populated for Out/Questionable-type designations. Any "status" field must therefore be modelled nullable, and a blank cell is *normal*, not a missing value.
- **F-4** Odds/CLV: there is no official NFL odds feed. Closing lines must come from a licensed vendor or the sportsbook itself → treat as commercial data, license-dependent, and keep it out of any "official source verified" column.

---

## Final integration record

_(filled in when T14 completes: PR link, merge SHA, Pages URL, deploy status.)_
