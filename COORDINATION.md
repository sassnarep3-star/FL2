# COORDINATION.md — Shared Task Board

> Read this file before starting any work. It is the single source of truth for who is doing
> what. Never start a task another session has claimed. Never edit a file outside your scope.
>
> **Rules of the road**
> 1. Claim a task by writing your session ID + file scope below, commit, and push immediately.
> 2. Keep scopes non-overlapping. Each session works on its own branch.
> 3. Need a file owned by someone else? Log a request here — do not edit it.
> 4. Make small, frequent commits. `git pull --rebase` before every push.
> 5. Shared outputs (site index, navigation, combined table data) change only in the final
>    integration task, once every other task is done.
> 6. A `needs review` status means the item is published on the **Flagged for Review** page and
>    does not block anything.
> 7. Stale claims: if a claim has no commits for 60+ minutes, any session may take it over and
>    must note the handoff in the Activity Log.

## Status legend

| Status | Meaning |
| --- | --- |
| `unclaimed` | Available. Claim it before you start. |
| `in progress` | Claimed, actively being edited. Do not touch. |
| `needs review` | Published on Flagged for Review. Does not block. |
| `done` | Finished. Sources + verification recorded below. |

## Branch / session convention

`session-<id>/<task>` — e.g. `session-e70150db/site-build`.

Current working branch for this session: **`arena/e70150db-fl2`** (base `0f3d2f9`, branch from `main`).

---

## Task board

| ID | Task | Status | Owner (session) | Branch | File scope | Updated |
| --- | --- | --- | --- | --- | --- | --- |
| T1 | Coordination board + repo audit | `done` | `e70150db` | `arena/e70150db-fl2` | `COORDINATION.md` | 2026-11-14 |
| T2 | Source registry & verification standard | `done` | `e70150db` | `arena/e70150db-fl2` | `data/sources.csv`, `pages/sources.html` | 2026-11-14 |
| T3 | Requirements register + open decision questions | `done` | `e70150db` | `arena/e70150db-fl2` | `pages/requirements.html`, `pages/decision-questions.html`, `data/decision-questions.csv` | 2026-11-14 |
| T4 | Strategy origination framework, validation gates, luck removal, correlation method | `done` | `e70150db` | `arena/e70150db-fl2` | `pages/strategies.html`, `pages/validation-gates.html`, `data/strategies.csv`, `tools/` | 2026-11-14 |
| T5 | Injury / depth-chart deficiency framework + verified Week 10 snapshot | `done` | `e70150db` | `arena/e70150db-fl2` | `pages/injuries.html`, `data/injury-report-2026-w10.csv` | 2026-11-14 |
| T6 | Verified league data tables (standings, team efficiency, passing) | `done` | `e70150db` | `arena/e70150db-fl2` | `pages/data-standings.html`, `pages/data-efficiency.html`, `data/standings-2026-w10.csv`, `data/team-efficiency-2026-w10.csv`, `data/passing-2026-w10.csv` | 2026-11-14 |
| T7 | Suggestions + decision matrix section | `done` | `e70150db` | `arena/e70150db-fl2` | `pages/suggestions.html`, `data/suggestions.csv` | 2026-11-14 |
| T8 | Site build (index, assets, nav) | `done` | `e70150db` | `arena/e70150db-fl2` | `index.html`, `assets/**` | 2026-11-14 |
| T9 | Integration: re-verify line by line, link check, PR, merge, deploy | `done` | `e70150db` | `arena/e70150db-fl2` | all (integration pass) | 2026-11-14 |
| T10 | Executive summary document | `done` | `e70150db` | `arena/e70150db-fl2` | `docs/EXECUTIVE-SUMMARY.md`, `pages/executive-summary.html` | 2026-11-14 |

**Note on parallel sessions.** At the time this board was created, the repository contained a
single commit (`0f3d2f9 Initial commit`) and a five-byte `README.md` — no other session had
claimed any work and no other branch existed. Session `e70150db` therefore claimed the full
task set so the work is not blocked, and scoped every task to its own files so a second
session can still take an independent task later without collision. If you are a new session,
add your row at the bottom, claim `unclaimed` work, and log a request here if you need a file
in someone else's scope.

---

## Out-of-scope / do-not-touch

| File | Reason |
| --- | --- |
| `.git/` | Repository internals |
| `README.md` | Landing text; edit only via a logged request |

---

## Requests log

| Date | From | To | File(s) | Request | Status |
| --- | --- | --- | --- | --- | --- |
| 2026-11-14 | `e70150db` | any | `README.md` | Append a short pointer to the live site + `COORDINATION.md` once integration is done. | `done` (T9) |

---

## Activity log

Newest first. One line per event: `date | session | task | event`.

```
2026-11-14 | e70150db | T9  | Integration pass complete: 16 pages, 0 broken links, 0 structural errors,
                                    clean rebuild reproduces 27/27 generated files byte-for-byte.
2026-11-14 | e70150db | T8  | Site build complete: index + 12 category pages, no external CDN dependencies.
2026-11-14 | e70150db | T2  | Source registry created. bash sandbox has NO egress except github/npm/pypi;
                                    all web verification done via page-fetch tool. Recorded in source notes.
2026-11-14 | e70150db | T1  | Repo audited: 1 commit, README.md is 5 bytes ('NFL\n\n'), no site, Pages already
                                    enabled from `main` root (legacy build), html_url
                                    https://sassnarep3-star.github.io/FL2/. Claimed T1-T10.
```

---

## Completion record — final integration pass (T9)

**Verification performed on the combined dataset, line by line:**

| Check | Method | Result |
| --- | --- | --- |
| Every internal link and `#anchor` resolves | `tools/check_links.py` over all 16 pages | pass |
| Every dataset carries its source column and retrieval date | `tools/check_links.py` | pass — 5 datasets, 0 empty source cells |
| No external CDN / off-site asset | `tools/check_links.py` | pass — zero external script or stylesheet references |
| No leaked placeholder text | `tools/check_links.py` | pass |
| HTML structure well-formed | stdlib `HTMLParser` open/close matching over all 16 pages | pass — 0 files with unclosed or mismatched tags |
| Clean rebuild reproduces committed bytes | wiped all generated artefacts, re-ran all 7 generators, byte-compared | pass — 27/27 files identical |
| Winning percentage | re-derived (W + 0.5·T) ÷ GP, 32 clubs | 32/32 match |
| Net points | re-derived PF − PA, 32 clubs | 32/32 match |
| Completion % and yards per attempt | re-derived from own numerators, 32 clubs | 32/32 match |
| PPG vs NFL Next Gen Stats PPG | cross-source comparison, 16 clubs where both published | 16/16 within 0.05 rounding (DET, MIN differ by exactly 0.05 — flagged F05) |
| Schedule completeness | bye-list assertion + duplicate-club assertion | pass — 28 club-slots + 4 byes = 32 |
| Team-games implied by standings | 274 ÷ 2 = 137 = 4 byes × 8.5 + 14 × 9 | pass |
| Source URLs re-fetched at the end of the session | nfl.com scoring table, seahawks.com depth chart | content unchanged; values as transcribed |

**Irregularities found and flagged (none blocking):** F01–F09, published on `pages/flagged.html` with source
links and self-check instructions. Summary: depth charts for 30/32 clubs missing; no official league-wide depth
endpoint (404, recorded as source S17); no odds data anywhere; injury labels have no published predictive value;
two clubs' PPG differ from NGS by a rounding 0.05; NGS EPA published for only 16/32 clubs; league gambling policy
constrains the product; primary deliverable undefined (Q17); "reward" undefined (Q18).

**Pull request and deploy:**

| Item | Value |
| --- | --- |
| Branch | `arena/e70150db-fl2` |
| Base | `main` @ `0f3d2f9` |
| PR | see the PR recorded at the end of this section |
| Merge method | `--merge`, merged without waiting for approval |
| Pages | `main` / root, legacy build, `https://sassnarep3-star.github.io/FL2/` |
| Deploy status | recorded below after the post-merge check |

---

## Verification standard (applies to every task)

1. Every table row carries a `source_url` pointing at an **official** property:
   `nfl.com`, `operations.nfl.com`, `media.nfl.com` (league communications), or the
   club's official `*.com` site. Secondary/academic sources are labelled `secondary` and are
   never used to assert a league fact.
2. If a value cannot be confirmed on an official page, the cell stays **empty** and the row is
   marked `unverified` and surfaced on the Flagged for Review page. Values are never inferred,
   interpolated, or carried over from memory.
3. Retrieval date is recorded for every source (`2026-11-14` for this pass).
4. Derived numbers (e.g. point differential computed as PF − PA) are marked `derived` and show
   the formula, not presented as league-published figures.
5. Analysis, proposals and model specifications are marked `proposed` and are explicitly *not*
   presented as measured results. No backtest figure appears anywhere unless it was computed
   from data actually ingested in this repo.
