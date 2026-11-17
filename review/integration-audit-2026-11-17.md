# FL2 cross-section integration audit — 2026-11-17

**State audited:** commit `56453a0a` (PR #31 merge) plus this session's root-page integration edits.

**Live NFL fetch:** none during this pass. Official source pages are linked below; values remain as-of their committed capture timestamps.
**Purpose:** expose data and policy conflicts before an NFL line, injury feature, strategy score, or reward is treated as decision-grade.

## Executive result

- **No live/reward strategy is supported by the current registry.** Line Lab records seven pre-registered strategies, all `not_eligible` and paper-only. Historical scores are not the live leaderboard. This is an internal research result, not an NFL fact.
- **The inputs are not one consistent data vintage.** The ops result feed records 148 final games out of 150 Week 1–10 fixtures at its 2026-11-16 capture; the Line Lab corpus metadata says 137 2026 games played. The sections need a shared immutable game-ID manifest before cross-section model comparisons.
- **Availability is not a complete starter/active/depth dataset.** Two Week 10 report captures have 345 and 347 parsed rows, respectively; those are repository capture counts, not an NFL-published total. The Line Lab depth graph has five clubs. Full 32-club depth, actual starters, official inactives and 2026 per-game snap shares remain incomplete or gated.
- **A capture policy conflict is open.** The repo's terms note says NFL.com Terms §1.3 restricts systematic retrieval to compile a database absent express prior written consent. The note also says the full terms review was not completed. `fl2-lines-snapshot.yml` has scheduled fetches; `availability-snapshot.yml` explicitly disables its schedule pending that gate. The scheduler was not edited in this integration task because it belongs to a prior session's claimed file scope; a request is recorded in `COORDINATION.md`.
- **The public/private data boundary is unresolved.** The Pages workflow uploads `.` and the repository tracks row-level injury transcriptions. A `.gitignore` rule for future files does not remove already-tracked data.
- The README was stale; the latest root landing page already reflects the merged sections, sourced snapshot and one-row-per-requirement view. This integration preserves that landing page and adds only an audit link; the README is rewritten to match.
- A literal merge-conflict marker set was present in `.gitignore` at the initial base commit `56453a0a`; concurrent session `d81dd61b` fixed it in PR #32. The rebased main copy retains both ignore patterns without markers.

## Official sources for manual review

| Official source | What it can verify | Capture / limitation in this audit |
|---|---|---|
| [NFL.com Terms](https://www.nfl.com/legal/terms/) | The terms that govern use of NFL.com services and content | Prior repository notes quote §1.3 but say only the first page/chunk was read. Re-read the complete current terms and obtain written permission/licensing; this audit is not legal advice. |
| [NFL injury report](https://www.nfl.com/injuries/) | Current report presentation and listed injury/practice/game statuses | The saved Week 10 snapshots are dated 2026-11-14 and 2026-11-16. This page was not fetched live on 2026-11-17; parsed row counts are not represented as an official total. |
| [NFL 2026 standings](https://www.nfl.com/standings/division/2026/REG) | Official team records and points-for/against reconciliation target | Prior verification is recorded in the repository; no new live standings check was made in this pass. |
| [NFL Week 10 schedule](https://www.nfl.com/schedules/2026/by-week/week-10) | Published fixture/time facts for the recorded week | Use the game-centre record for venue where schedule widgets conflict; no new live fetch was made. |
| [NFL teams](https://www.nfl.com/teams/) | Official league team directory | It does not establish that a complete 32-club depth-chart or snap-count route is available. |
| [NFL odds path](https://www.nfl.com/odds/) | The endpoint previously checked for a league odds page | Repo notes record it as unavailable on 2026-11-16. It was not rechecked live; do not treat the old response as current. |

## Findings and decision gates

| ID | State | Finding | Evidence / gate | Clearing evidence |
|---|---|---|---|---|
| F-AUD-01 | Needs review | Scheduled NFL-page collection conflicts with the documented F-T1 terms gate. One workflow schedules Wed/Thu/Fri injury/schedule fetches; another comments out its schedule pending terms review. The run-history query returned no executions for the scheduled workflow, so configuration is verified, execution is not. | [Scheduled workflow](../.github/workflows/fl2-lines-snapshot.yml) · [manual-only workflow](../.github/workflows/availability-snapshot.yml) · [NFL Terms](https://www.nfl.com/legal/terms/) · [prior F-T1](../fl2-dashboard/flagged-review.html#F-T1) | Complete review of the current terms plus written permission or a licensed source; make both workflow files and the public/private retention policy consistent. Until then, do not treat scheduled retrieval as authorized. |
| F-AUD-02 | Needs review | The public/private layer is not enforced: Pages publishes the repo root and tracked row-level injury files are in that tree. | [Pages workflow](../.github/workflows/pages.yml) · [tracked injury rows](../data/injuries_2026_week10.csv) · [NFL Terms](https://www.nfl.com/legal/terms/) · [prior F-P2](../fl2-dashboard/flagged-review.html#F-P2) | Written permission/licensing and an explicit private store with access control; otherwise publish only permitted derived analysis and official-page links. |
| F-AUD-03 | Reconcile | The 2026 results feed and Line Lab corpus have different game cutoffs: 148 finals versus 137 games played. These are different committed vintages, not a common evaluation set. | [Ops results feed](../ops/data/results/results_2026_reg.csv) · [Line Lab corpus manifest](../data/linelab/corpus.json) · [NFL standings](https://www.nfl.com/standings/division/2026/REG) | Rebuild all comparison outputs from the same immutable manifest; match the exact eligible game-ID set, scores, capture cutoff and model code version. |
| F-AUD-04 | Incomplete | Two dated injury-report artifacts (2026-11-14 and 2026-11-16) contain 345 and 347 parsed rows. They do not provide a daily Wed-to-kickoff history, verified inactive list or complete actual-starter graph. | [Capture metadata 11-14](../data/linelab/captures/2026-11-14/week10-injury-report.meta.json) · [capture metadata 11-16](../data/linelab/captures/2026-11-16/week10-injury-report.meta.json) · [NFL injury report](https://www.nfl.com/injuries/) | Permitted dated snapshots with clock/hash/conflict flags, plus official game-day inactive/starter evidence and verified playing-time records. |
| F-AUD-05 | Blocked | The stored depth graph represents five clubs; it is not a verified all-32-club starter/replacement source. | [Depth graph](../data/linelab/depth_graph.json) · [NFL team directory](https://www.nfl.com/teams/) · [NFL injury report](https://www.nfl.com/injuries/) | Verify one official route across 32 clubs or use a verified per-game snap-count source; do not infer rank from jersey number, experience, salary, or a single shared rank-1 slot. |
| F-AUD-06 | Unverified | No official NFL odds feed is recorded for a full opening/closing history. A previous check of the NFL odds path was recorded as unavailable, not rechecked now. | [NFL odds path](https://www.nfl.com/odds/) · [price-data policy](../research/price-data-policy.md) · [price store](../fl2-lines/prices.html) | Select a permitted timestamped/licensed price source; keep opening and closing values distinct, and leave unavailable markets blank. |
| F-AUD-07 | No promotion | Seven Line Lab strategies are registered; all are `not_eligible` and paper-only. Parlays and prop combos remain behind joint-evidence and operator-rule gates. | [Strategy registry](../data/linelab/registry.json) · [Line Lab methods](../linelab/strategies.html) · [prospective leaderboard](../fl2-lines/leaderboard.html) | Continue pre-registered singles-only shadow records. Require benchmark-relative proper-score skill, game-cluster uncertainty, multiplicity control and the prospective escrow before any reward. |
| F-AUD-08 | Resolved upstream | The initial base `56453a0a` contained literal `.gitignore` conflict markers; session `d81dd61b` removed them in PR #32 while preserving both intended ignore patterns. | [current `.gitignore`](../.gitignore) · [coordination history](../COORDINATION.md) · [PR #32](https://github.com/sassnarep3-star/FL2/pull/32) | No further action. Preserve `fl2-lines/data/snapshots/` and `private/` if the ignore file is edited again. |
| F-AUD-09 | Preserved / reconciled | The latest root landing already reflects merged data sections and the one-row-per-requirement table; this task preserves it and adds an audit link. The stale README is rewritten to match. | [Preserved home](../index.html) · [updated README](../README.md) | Keep as-of dates and distinguish NFL facts, secondary data, and FL2 model output on future edits. |
| F-AUD-10 | Needs reconciliation | Readiness presentations differ in scope: 75 integrated landing rows, 71 R26–R96 rows at `/readiness/`, 74 R01–R74 rows in `fl2-lines`, and 68 Line Lab requirement rows. | [Landing data](../data/landing_readiness.js) · [R26–R96](../ops/data/requirements_v2.json) · [R01–R74](../fl2-lines/data/registers/readiness.csv) · [Line Lab register](../data/linelab/requirements.json) | Keep historical registers, add a generated crosswalk with canonical IDs, evidence/source tier, status date and explicit disagreement handling. |
| F-AUD-11 | Cutoff warning | The 148-final result feed and 137-game Line Lab corpus are not aligned; landing summaries now show the cutoff and direct users to the audit. | [Ops feed](../ops/data/results/results_2026_reg.csv) · [Line Lab corpus](../data/linelab/corpus.json) · [NFL standings](https://www.nfl.com/standings/division/2026/REG) | Publish a shared immutable manifest and rebuild before cross-section comparisons. |

## Questions to answer before choosing a path

| Question | Current answer | Information still needed | Discovery path |
|---|---|---|---|
| Is scheduled scraping/republication permitted? | Unresolved; prior notes identify a terms gate and incomplete terms review. | Full operative terms, written permission or license, retention and republication scope. | Review [NFL Terms](https://www.nfl.com/legal/terms/) end to end; record written authorization or choose a licensed feed. |
| Does “not listed” mean active/available? | No. The injury report alone is not a reserve, inactive or active-player dataset. | Reserve/IR, roster transactions, official inactives, actual starters and snaps as-of kickoff. | Use permitted official team/league reports and Game Books; reconcile against the [NFL injury page](https://www.nfl.com/injuries/) without inferring missing rows. |
| Can any strategy receive a reward now? | No. Current internal registry has zero eligible entries. | Prospective singles sample, benchmark provenance, calibrated proper score, uncertainty and control comparisons. | Continue frozen forecasts and review the [pre-registration ledger](../fl2-lines/prereg.html) and [escrow rules](../fl2-lines/leaderboard.html). |
| Are model sections comparable? | Not yet; the 2026 game counts differ. | Same game IDs, results snapshot, rating cutoff and model version. | Rebuild from a shared manifest and compare row-by-row to [official standings](https://www.nfl.com/standings/division/2026/REG). |
| Which price benchmark is allowed? | Unresolved; the available market data are secondary and source terms are not settled. | Provider, opening/closing timestamps, storage and redistribution permission. | Decide the [price-data policy](../research/price-data-policy.md) before any CLV/ROI publication. |
| Can backups be ranked 1st–4th string today? | No. Five club charts and partial participation history do not establish 32-team snap-based depth. | Verified all-club depth or official per-game snap data and inactive evidence. | Verify source coverage before building the feature; otherwise show “unavailable” rather than infer. |

## Suggested path

1. **Resolve content rights and the public/private store first.** Obtain written permission or a licensed source; otherwise keep only permitted derived analysis and source links. Align the scheduled and manual-only workflows after the gate is closed.
2. **Freeze a single cross-section data manifest.** For each input, store source URL, source tier, retrieval time, SHA-256, included game/player IDs, parser version and rights status. Rebuild all public derivatives from it.
3. **Keep the 32-team personnel feature blocked until a route is verified.** Use official inactive/starter evidence and playing-time data, preserve shared/empty slots, and model injury changes as a surprise/delta only after the snapshot series is complete.
4. **Maintain singles-only prospective evaluation.** Publish fair line, market line and residual separately; rank by benchmark-relative proper-score skill with uncertainty and multiplicity control. Keep staking/ROI in a later escrow. Parlays/props need directly validated joint probabilities and operator push/void rules.
5. **Keep the suggestion register a review queue.** Each proposal names the missing evidence, a test or gate, risk, and a clear adopt/reject/defer state; do not implement a choice that requires an unresolved rights or source decision.

## Checks performed

The following checks ran against committed files on 2026-11-17; they do not establish that an external URL is live today or that its content can be redistributed.

- `python3 scripts/check_site.py` — 7 top-level pages passed.
- `python3 tools/check_links.py` — 16 hub pages, 22 registered sources passed.
- `./engine/linelab/build_all.sh` — deterministic rebuild; 12 Line Lab pages passed row-source/link checks; 7 strategies remain not eligible.
- `python3 fl2-lines/engine/check.py` — 16 pages, 74 requirements; zero failures.
- `python3 tools/check_signals_links.py` — 18 pages, 101 tables, 1,305 rows and 352 internal links passed.
- `python3 ops/check_readiness.py` — 3 readiness pages passed.
- `python3 signal/analysis/verify.py` — 216 checks passed.
- `python3 engine/linelab/check_site.py` — 12 pages passed.
- `python3 tools/check_integrated_site.py` — see the live output for page/link counts and any remaining broken local links.

## Ownership requests

Per the repository's parallel-work rules, this session did not edit files claimed by completed prior sections. Requests recorded in `COORDINATION.md`:

- **F-AUD-01:** reconcile the scheduled fetch in `.github/workflows/fl2-lines-snapshot.yml` with F-T1 in `fl2-dashboard/flagged-review.html`; do not collect until rights are resolved.
- **F-AUD-08:** resolved upstream in PR #32; preserve both ignore patterns on future edits.
- The conflicting readiness registers and corpus vintages should be resolved through a generated crosswalk/shared manifest rather than silently rewriting another section's data.
