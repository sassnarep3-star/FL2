# FL2 — NFL research hub

**Live site:** https://sassnarep3-star.github.io/FL2/

Several agent sessions worked this repository in parallel. All of their work is kept.
This README explains which section to read and why, without deleting anything.

## Start here: the Evidence Ledger → [`ledger/overview.html`](ledger/overview.html)

The Evidence Ledger is a central, high-density view of data and methods—not proof that every value in the repository is verified. Other sections also contain populated numeric artifacts from separate pipelines; their scopes and provenance differ. Use the [landing-page readiness register](index.html#decision-readiness) for current blockers, source state, and freshness limitations.

| What | Where it comes from | Rows / scope |
|---|---|---|
| Historical Week 10 injury statuses | [NFL Week 10 report](https://www.nfl.com/injuries/league/2026/reg10) | Snapshot counts differ by schema; see REQ-049 |
| 2026 standings — W-L-T, points for/against, streaks | [nfl.com/standings](https://www.nfl.com/standings/) | 32 teams |
| Team defense — points, yards, takeaways | [Pro-Football-Reference 2026 opp](https://www.pro-football-reference.com/years/2026/opp.htm) | 32 teams |
| Starting-quarterback decisions | NFL.com news roundups, Nov 11 + Nov 13 | 7-team historical repository claim (source recheck pending) |
| 1999–2026 results + closing lines | nflverse `games.csv` | 7,548 games |

| Section | Purpose |
|---|---|
| [`ledger/suggestions.html`](ledger/suggestions.html) | 10 proposals with options and a recommendation — accept / reject / defer |
| [`ledger/decisions.html`](ledger/decisions.html) | 20 questions: verified, partial, unknown, or your call |
| [`ledger/strategies.html`](ledger/strategies.html) | 11 strategies × 8 section-specific gates, historical backtests—not a prospective leaderboard |
| [`ledger/injuries.html`](ledger/injuries.html) | availability and lineup depletion |
| [`ledger/lines.html`](ledger/lines.html) | our own total / margin / win probability per game |
| [`ledger/verification.html`](ledger/verification.html) | source-tier and provenance notes; hashes exist for some committed datasets |
| [`ledger/flagged.html`](ledger/flagged.html) | 13 items to review |
| [`ledger/summary.html`](ledger/summary.html) | executive summary |
| [`ledger/method.html`](ledger/method.html) | how every number was produced |

## Current decision-readiness register

The root landing page now includes a searchable, 81-row operational readiness register with status, current evidence, blockers, explicit clearance measures, source-state labels, repository evidence, and a **Flagged for Review** route. The linked JSON is `data/decision-readiness.json`; the review page is `readiness-review.html`.

**Freshness warning:** the local Week 10 files are dated 2026-11-14. Selected dynamic official NFL pages were read on 2026-11-16, but their responses were not persisted or hashed. Those reads do not refresh the older files or establish current player availability. Clearance measures are proposed targets, not NFL standards or observed model results.

The 81 rows are an operational decomposition, not a one-to-one rewrite of the older inventories. [`data/requirements-crosswalk.csv`](data/requirements-crosswalk.csv) traces all 25 CSV requirements and all 10 grouped rows in [`research/requirements.md`](research/requirements.md) to the readiness IDs, with current status summaries. The old CSV's trailing date is now named `recorded_date`; original status/note claims are preserved, while a `current_evidence` column points to checked repository artifacts. Historical `done` labels are not carried forward as proof that every finer-grained gate is clear. See the [reconciliation and source audit](research/readiness-reconciliation-2026-11-16.md) for the path, source-scope, and freshness findings.

## Current read

Several strategy/backtest artifacts are populated, but their counts, market-price coverage, and method claims are not uniform across the repository. No backtest-only result should be read as a prospective leaderboard entry or staking recommendation. The price-source/rights policy, point-in-time evidence, full source-content audit, and reconciliation of populated artifacts across the parallel sections remain open; see the row-level register and [reconciliation note](research/readiness-reconciliation-2026-11-16.md) before relying on a reported performance metric.

## Other sections in this repository

These were built by different sessions in parallel. Several contain historical or derived numeric data; others are design frameworks. Their source coverage and validation scopes differ, and local structural checks do not recertify external claims. The readiness register records the current known limitations without silently overwriting those sections.

- [`docs/index.html`](docs/index.html) — NFL Analysis Dashboard (session d263eab0): 16 pages, 345 transcribed injury rows, unit exposure, its own flagged list.
- [`hub/index.html`](hub/index.html) — NFL Decision Hub (session e70150db + others): requirement coverage, validation gates, luck-vs-skill explainer, repository audit.
- [`strategy.html`](strategy.html) — Fourth & Signal (session 4a77261b): the original evidence-first blueprint, with [`availability.html`](availability.html), [`data.html`](data.html), [`decisions.html`](decisions.html), [`review.html`](review.html).
- [`signal/index.html`](signal/index.html) — Signal Lab (session d10a1d25): multi-season market, injury, depth, and correlation analyses plus a local rebuild workflow. The Nov 16 reproducibility audit recorded a rebuild failure after zero market rows; treat derived figures and reproducibility claims as under review until the owning pipeline is repaired.

Consolidating all four structures into one is proposed as a decision — see
[`ledger/suggestions.html`](ledger/suggestions.html). It was not done silently.

## Verification rules

1. **Official source, or blank and flagged.** For factual NFL values, a link must support the stated fact and scope; an official source route is not proof of local coverage. If no applicable source exists, the value remains blank and the row says so.
2. **No inference.** Missing values are never derived from jersey number, experience, nearby values, or league averages.
3. **Keep status and provenance separate.** A completed page or passing structural check does not validate external content, methodology, pricing rights, or freshness. See the Flagged for Review route for unresolved items.

## Rebuild

```bash
python3 scripts/check_readiness.py # 81 rows, sources, legacy inventories and crosswalk
python3 scripts/check_readiness.py --write # regenerate landing/review static shells after edits
node --check assets/readiness.js
npm install --no-save --package-lock=false jsdom@26.1.0
node scripts/test_readiness_ui.js
python3 scripts/check_site.py
python3 engine/check_site.py        # rendered DOM, links and tables (needs jsdom above)
```

The data/research build commands remain available in their section-specific scripts. None of these local checks fetches or certifies the live content of external source pages.

Docs: [`docs/SOURCES.md`](docs/SOURCES.md) · [`docs/STRATEGY_VALIDATION.md`](docs/STRATEGY_VALIDATION.md) · [`COORDINATION.md`](COORDINATION.md)

Research tool, not betting advice.


## FL2 Dashboard section (session arena-48561869-fl2)

The historical dashboard lives at [`fl2-dashboard/index.html`](fl2-dashboard/index.html). It includes 2026 standings, a Week 10 schedule and injury report, a club depth-chart example, a questions/answers register, strategy gates, and a Flagged for Review page. Its data records and fetch log remain available in [`fl2-dashboard/data/verified/`](fl2-dashboard/data/verified/). These are dated snapshots: the readiness audit did not independently re-check every row, and current official pages may have changed. Follow each row's source note and do not infer current availability or depth from the snapshot.
