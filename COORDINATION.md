# COORDINATION.md — Shared Task Board

**Purpose:** this file is the coordination point for all agent sessions working on `sassnarep3-star/FL2`.
Read it before starting. Claim work here, commit the claim, and record sources + verification when done.

Rules (agreed baseline for all sessions):

1. Never start a task another session has claimed.
2. Work only inside your claimed file scope. If you need to touch another session's file, log a request in **Change Requests** instead of editing it.
3. Small, frequent commits. `git pull --rebase` before every push.
4. Never mark a row "verified" without opening the official source and reading it. Link the source in the row.
5. If a value cannot be confirmed from an official source: leave it blank and add it to the review register (`assets/data/review.js` → *Flagged for Review* page and `flagged-for-review.md`).
6. A claim older than 60 minutes with no commits may be taken over by another session — note the handoff in **Handoffs / Log**.
7. Shared outputs (site index, navigation, `assets/data/*`, merged table data) are changed by the **final integration session** only.
8. An item marked `needs review` is published on the *Flagged for Review* page and **does not block** other work or the merge.
9. Machine-readable copies of this board and of the review register live in `coordination/` and are **generated** — edit `COORDINATION.md` / `assets/data/review.js`, then run `python3 tools/gen_markdown.py`.

---

## Session registry

| Session ID | Branch | Started (UTC) | Role | Notes |
| --- | --- | --- | --- | --- |
| `arena-be3108f3` | `arena/be3108f3-fl2` | 2026-11-14 02:55 | build + final integration | Repo found empty except a 5-byte `README.md`. This session performs the greenfield build (docs + site) and then acts as the integration session, because it is the only active claimant at start time. |

> Repo state at first look: single commit `0f3d2f9 "Initial commit"`, one file (`README.md`, 5 bytes, content `# FL2`). No data, no code, no CI, no Pages config, no `.nojekyll`. **Flag FL-001** — a project described as "collect, organize, analyze" has zero collected data in-repo; all datasets in this build are freshly sourced snapshots, not pre-existing project data.

---

## Task board

Statuses: `unclaimed` · `in progress` · `done` · `needs review`

| ID | Task | Status | Owner | File scope | Sources / verification recorded |
| --- | --- | --- | --- | --- | --- |
| T01 | Repo review + baseline snapshot | done | `arena-be3108f3` | `COORDINATION.md` | `git log`, `git show --stat 0f3d2f9`, file inventory (1 file, 5 bytes) |
| T02 | Full requirements catalogue (R-IDs, acceptance criteria) | done | `arena-be3108f3` | `assets/data/requirements.js`, `requirements.html` | Derived from the user brief; no external source needed. 42 rows R-01…R-42 with acceptance criteria + dependencies |
| T03 | Open questions / information gaps register | done | `arena-be3108f3` | `assets/data/questions.js`, `questions.html` | Derived from T02 + live availability probes (S-06/S-07 dead ends, S-19/S-20 planned) |
| T04 | Suggestions register (ranked, decision-ready) | done | `arena-be3108f3` | `assets/data/suggestions.js`, `suggestions.html` | 30 rows, I/C/E/R scored; priority computed by `assets/js/app.js`; dispositions left for the owner except the 6 the brief mandated |
| T05 | Executive summary | done | `arena-be3108f3` | `index.html`, `executive-summary.html` | Summarises T06–T12; every number is a `data-stat` counter or a computed figure from `engine/selftest` |
| T06 | Data-source catalogue + access probes | done | `arena-be3108f3` | `assets/data/sources.js`, `data-catalog.html` | 20 sources, tiered; 5 read directly, 5 snippet-only, 4 planned, 2 confirmed dead ends |
| T07 | Official injury report snapshot, NFL Week 10 2026 | done | `arena-be3108f3` | `assets/data/injuries.js`, `injuries.html` | `https://www.nfl.com/injuries/` (official, chunks 0–4 of 8) + `vikings.com` club cross-check; coverage bounded in `meta_gaps` |
| T08 | Availability-adjusted depth analysis (2nd/3rd/4th string) | needs review | `arena-be3108f3` | `availability.html`, `assets/data/injuries.js` (`rostersW10`) | Official depth chart **not found** (FL-013); roster pages used instead; ordering labelled a projection |
| T09 | Line-origination methodology: signals, validation gates, correlation | done | `arena-be3108f3` | `assets/data/strategy.js`, `methodology.html`, `engine/` | 22 signals, 16 gates, 12 correlation pairs; math implemented in `engine/`, 46/46 self-test assertions pass |
| T10 | Leaderboard + rewards design (strategy competition) | done | `arena-be3108f3` | `assets/data/strategy.js` (`leaderboard`), `leaderboard.html` | Spec only; standings intentionally empty pending T09 data inputs (FL-014) |
| T11 | Markets page: instrument structure, vig, parlay/prop combo math, compliance | done | `arena-be3108f3` | `markets.html`, `assets/data/strategy.js` | Operator house rules + policy sources cited; all vig/hold/CLV cells blank by rule (no market source) |
| T12 | Verification log + Flagged for Review page | done | `arena-be3108f3` | `assets/data/{review,sources}.js`, `verification.html`, `review.html` | 12 checks logged with level; 18 flags each with evidence + next action; `tools/check_site.py` enforces the source rule mechanically |
| T13 | Site scaffold + GitHub Pages publish | done | `arena-be3108f3` | `*.html`, `assets/css/*`, `assets/js/*`, `.nojekyll`, `README.md`, `tools/`, `coordination/`, `docs/` | Pages API call recorded in the integration record below |
| T14 | PR → `main`, merge, deploy confirmation | in progress | `arena-be3108f3` | repo-wide | see **Final integration record** |

**Not yet started by any session (candidate work for a fresh claim — keep scopes disjoint):**

| ID | Task | Suggested file scope | Depends on |
| --- | --- | --- | --- |
| T15 | Ingestion automation: crawler that reproduces `assets/data/injuries.js` for Week 10 2026 exactly, then extends to 32 clubs / 3 practice days / all roster status segments | `tools/ingest/*`, `assets/data/injuries.js` | T07, Q-01 (licensing) |
| T16 | Market snapshot recorder (T-48h/T-24h/T-2h/close) — closes FL-014, unblocks G-03/G-07 and the leaderboard | `tools/quotes/*`, `data/quotes/*` | Q-10, Q-11 |
| T17 | Weekly "what changed" diff report (designations, roster moves) | `tools/diff/*`, `assets/data/*.js` | T15 |
| T18 | Second-pass verification of 10% of published rows against their sources (Q-19) | `assets/data/sources.js` verification log | T12 |
| T19 | Primary-text legal pass: regulator registers + gazette; replace FL-010/FL-011 aggregator claims | `assets/data/sources.js`, `markets.html` compliance block | Q-14, Q-15 |

---

## Change requests

_None open._

| # | Requested by | File | Request | Status |
| --- | --- | --- | --- | --- |
| — | — | — | no open requests | — |

---

## Handoffs / Log

| When (UTC) | Session | Event |
| --- | --- | --- |
| 2026-11-14 02:55 | `arena-be3108f3` | Board created (file did not exist). Claimed T01–T13. No other claimants found — no `session-*` branches on origin, single commit history. |
| 2026-11-14 02:56 | `arena-be3108f3` | Access probe: sandbox `curl` is restricted to github/npm/pypi hosts, so all live data must come through the fetch/search tools, not shell HTTP. Recorded because it constrains any "auto-refresh at page load" design: the published site cannot depend on sandbox-only credentials. |
| 2026-11-14 03:05–03:20 | `arena-be3108f3` | T07 capture: `nfl.com/injuries/` read via chunks 0–4 of 8 (through the SF@DAL table); chunks 5–7 deliberately not re-fetched, gap recorded as FL-005 rather than presented as a complete slate. Club cross-check `vikings.com` + roster excerpts for MIN/GB captured. Two guessed official depth-chart paths failed → FL-013, sources S-06/S-07 marked `failed`. |
| 2026-11-14 03:25 | `arena-be3108f3` | Engine written (`engine/`, stdlib only — `numpy` is not installable in this sandbox). Self-test green: 46 assertions, exit 0. Numbers published on the site are transcribed from that report into `assets/data/computed.js`; if `engine/config.py` changes, regenerate with `python3 -m engine.selftest` and re-copy. |
| 2026-11-14 03:40 | `arena-be3108f3` | Site built (15 pages + shared chrome + generic table renderer). `.nojekyll`, `tools/check_site.py`, `tools/gen_markdown.py`, generated Markdown registers and `coordination/*.json` added. T02–T13 marked done; T08 marked `needs review` (depth source). |

---

## Findings worth sharing (read before duplicating work)

- **F-1** `nfl.com/injuries/` is server-rendered and fetchable as markdown tables — this is the official Week-by-Week report (per-club submitted data). Use `?season=2026&week=N` style navigation via the page's year/week selectors; the fetched page title confirms "Week 10 of the 2026 Season". The page also **keeps stale headings for already-played games** (WAS@NYG still headed "Thursday, November 12th"), which is why every table on the site carries an as-of stamp.
- **F-2** Club sites (e.g. `vikings.com`) publish the same report with Wed/Thu/Fri participation detail + `NIR - Rest` / `NIR - Personal` designations that the league page collapses. Cross-check both; they disagree on granularity, not on facts (statuses agreed 13/13 MIN and 17/17 GB).
- **F-3** The league page's `Game Status` column is **empty for most rows** — it is only populated for players who did not practise fully. Any "status" field must therefore be modelled nullable, and a blank cell is *normal*, not a missing value.
- **F-4** Odds/CLV: there is no official NFL odds feed. Closing lines must come from a licensed vendor or the sportsbook itself → treat as commercial data, license-dependent, and keep it out of any "official source verified" column. Consequence: **no edge/ROI/hold number may be published** (FL-014).
- **F-5** "Not injury related – resting player" appears inside the official *injury* column. Injury-text parsing must separate rest / personal / illness / structural or the availability model will penalise clubs for resting healthy veterans (SIG-06).
- **F-6** `nfl.com/teams/<club>/roster` (no trailing slash — the trailing-slash variant 404s) is the working substitute for a depth chart: number, position, status, ht/wt, years of experience, college. It is **paginated by status**; the active segment was captured and the IR/PUP/PS segments were not, so "no players on IR" is a capture artefact, never a conclusion (FL-002).
- **F-7** Position vocabulary differs between the two official feeds (`S`/`T`/`LB`/`DE` on reports vs `SAF`/`OT`/`OLB`/`DB`/`DL` on rosters). Every join must pass through a crosswalk or it silently drops rows (FL-003).
- **F-8** Never fetch through a proxy/CDN copy of a page: an OSS-signed mirror returned `SignatureDoesNotMatch` every time. Pass the canonical public URL.
- **F-9** Do not re-fetch the Week 10 snapshot to "complete" it — the gaps are intentional and recorded (`meta_gaps` in `assets/data/injuries.js`). Extending coverage is T15's job (a crawler), not a manual second pass.
- **F-10** Sandbox Python has no third-party packages that persist; the engine is stdlib-only on purpose (`statistics.NormalDist` is the only quantile helper). Keep it that way or the self-test stops being reproducible for reviewers.

---

## Decisions log (this session)

| # | Decision | Rejected alternative | Why |
| --- | --- | --- | --- |
| D1 | Static, dependency-free site from the repo root | Astro/Next dashboard with a build step | The audit trail must be openable offline from a clone; a build step is another way to be silently wrong |
| D2 | Publish the Week 10 snapshot as *partial*, with gaps inline | Wait for a full 32-club capture | Bounded-and-honest beats complete-looking (R-05) |
| D3 | Depth ordering rendered as a labelled projection | Infer "2nd string" from number/contract | No official ordering source exists (FL-013); inventing one corrupts every downstream feature |
| D4 | Leaderboard ships empty + one synthetic benchmark row | Seed with illustrative results | Ranks from no data reward noise — the opposite of the brief |
| D5 | Edge/ROI/hold cells blank everywhere | "≈4.5% vig" estimates | No licensed or self-recorded odds source (FL-014, Q-10) |
| D6 | DSR/MinTRL as the multiple-testing control, thresholds in `engine/config.py` | Bespoke "hit 55% for 4 weeks" rule | A published, citable correction (S-10) beats an invented one |
| D7 | Rule numbers (IR 4 games, 8 returns, 21-day window, 53-man) stored in config flagged `secondary source` | Omit them, or quote them as official | Only media/aggregator text was reachable (FL-012); a one-line edit fixes it when the primary document is read |
| D8 | Registers are JS data files + generated Markdown, not hand-written Markdown tables | Markdown tables as the source of truth | One source of truth; the site and the GitHub view cannot drift |

---

## Final integration record

_(filled in when T14 completes: PR link, merge SHA, Pages URL, deploy status.)_
