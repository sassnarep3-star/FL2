# FL2 — NFL decision research hub

**Live site:** <https://sassnarep3-star.github.io/FL2/>

**Evidence cutoff:** committed captures are dated individually; the latest central readiness bundle is **2026-11-16**. Official injury, schedule and standings spot-checks performed by parallel sessions on 2026-11-17 are recorded in `COORDINATION.md`; this cross-section audit reran local checks but did not fetch live NFL pages.

FL2 is a research dashboard for originating NFL lines and testing signals. It keeps model fair lines, market inputs, results, availability evidence, uncertainty, and blockers separate. It is **not betting advice**. No strategy is currently promoted to live rewards.

## Start here

- [Overview and integrated decision-readiness table](index.html) — summary, source/gate snapshot, and the landing table with the gate and clearing metric for each integrated requirement.
- [Executive summary](ledger/summary.html) — headline findings and limitations.
- [Cross-section integrity audit / Flagged for Review](review/integration-audit-2026-11-17.html) — concrete inconsistencies, unresolved source/rights gates, questions, and proposed next steps.
- [Suggestions and decision paths](fl2-lines/suggestions.html) — adopt/test/reject/defer proposals, including the information needed to choose.
- [Questions and answers](fl2-lines/questions.html) — current answers, unknowns, and what would close them.
- [Decision desk — the review surface](decision-desk/index.html) — one ranked board holding 68 decisions (57 merged from 68 register entries across 11 registers, 11 raised by this session), the 55 open questions, and the 12 dated captures behind every claim made about them.

## Current decision status (as of the committed artifacts)

1. **No live strategy is eligible.** The Line Lab registry lists seven registered strategies as `not_eligible` and paper-only. Originated Lines also keeps its prospective leaderboard empty until its escrow gates are met. These are FL2 model-governance results, not NFL facts; see the [registry](data/linelab/registry.json), [strategy gates](linelab/strategies.html), and [prospective leaderboard](fl2-lines/leaderboard.html).
2. **Results are available, but their cutoff matters.** The 2026 regular-season feed captured on 2026-11-16 has 148 final scores out of 150 listed fixtures; the other two were left blank/non-final. The feed includes a 32-team standings reconciliation. Check the [results feed](ops/data/results/results_2026_reg.csv), [ops report](readiness/ops.html), and the [official NFL standings](https://www.nfl.com/standings/division/2026/REG).
3. **Availability and depth remain incomplete.** Two dated Week 10 report captures (2026-11-14 and 2026-11-16) have parsed row counts of 345 and 347; the difference is +2 Baltimore rows between the two reads,
 these counts describe the saved captures, not an official NFL total. The Line Lab depth graph contains five clubs, not a verified 32-club source. Actual starters, inactive lists, and per-game snap-based replacement depth still block team-level conclusions. See [availability](linelab/availability.html), [depth](linelab/depth.html), and the [official NFL injury report](https://www.nfl.com/injuries/).
4. **Price provenance is a gating issue.** Opening and closing market coverage varies by source and season; no official NFL odds feed is recorded. Price-dependent claims must retain their source tier, timestamp, and price-data policy. See [Originated Lines prices](fl2-lines/prices.html), [Line Lab prices](linelab/prices.html), and the [price policy](research/price-data-policy.md).
5. **Automated NFL-page capture is not treated as authorized.** A prior reading of NFL.com Terms §1.3 recorded a restriction on systematic retrieval to compile a database without express prior written consent. The repository currently has conflicting scheduled/manual-only workflow configurations. This needs written permission or a licensed source, and a consistent public/private data policy. See [Flagged F-AUD-01](review/integration-audit-2026-11-17.html#F-AUD-01) and the [official NFL terms](https://www.nfl.com/legal/terms/).
6. **Independent sections use different data vintages and definitions.** For example, the 148-final results feed and the Line Lab corpus' 137-game 2026 count are not the same evaluation set. Do not compare scores across sections until their input manifests and cutoffs are aligned. The [integrity audit](review/integration-audit-2026-11-17.html#F-AUD-03) records the discrepancy.

## Site map

| Decision area | Page | What it contains |
|---|---|---|
| Integrated overview | [Home](index.html) | Executive snapshot, source/gate table, and 75-row integrated decision-readiness view (generated 2026-11-16). |
| Requirements | [Originated Lines](fl2-lines/index.html) · [Readiness register](readiness/index.html) · [Line Lab requirements](linelab/requirements.html) | Separate requirement registers with blockers and clearing metrics. They have different scopes/status rules; the audit identifies disagreements instead of hiding them. |
| Line origination | [Originated lines](fl2-lines/lines.html) · [Evidence Ledger lines](ledger/lines.html) · [Line Lab models](linelab/models.html) | Side → total → moneyline; fair line, market line, residual, probabilities, inputs, and estimator comparisons. These are separate model implementations. |
| Results and prices | [Verified results](fl2-lines/results.html) · [Price store](fl2-lines/prices.html) · [Ops dashboard](readiness/ops.html) | Captured result feeds, price provenance, opening/closing limitations, and reconciliation. Secondary market data is labelled; it is not an NFL-official odds feed. |
| Strategy competition | [Strategy evaluation](linelab/strategies.html) · [Prospective leaderboard](fl2-lines/leaderboard.html) · [Pre-registration](fl2-lines/prereg.html) | Proper scores, uncertainty, controls, eligibility gates, signal/staking separation, and prospective escrow. Backtests are not presented as live leaderboard rewards. |
| Availability and personnel | [Availability graph](fl2-lines/availability.html) · [Injuries](ledger/injuries.html) · [Depth graph](linelab/depth.html) · [Matchup matrix](fl2-lines/matrix.html) | Timestamped injury captures, designation reliability, partial depth evidence, and explicit gaps for starters, inactives, IR, transactions, and snaps. |
| Decision support | [Questions](fl2-lines/questions.html) · [Suggestions](fl2-lines/suggestions.html) · [Flagged review](review/integration-audit-2026-11-17.html) | Questions answered from existing evidence, missing information, paths to discover it, and unresolved irregularities. |
| Decision desk | [Board](decision-desk/suggestions.html) · [Questions](decision-desk/questions.html) · [Calibration](decision-desk/calibration.html) · [Freshness](decision-desk/freshness.html) · [Verification log](decision-desk/sources.html) | Merged suggestion registers with id collisions and duplicated registers computed rather than asserted; merged question register; designation calibration with position groups, official-only correlations and the parlay joint test; freshness diff; 10 flagged irregularities. Rebuilt by `tools/build_decision_desk.py`. |
| Provenance | [Verification and sources](ledger/verification.html) · [Coordination board](COORDINATION.md) | Source tiers, capture history, reproducibility checks, task ownership, and verification records. |

## Source and uncertainty rules

- **NFL official pages** are the primary references for league schedule, standings, injury-report and terms facts. A capture is always tied to its recorded date/time; a link is not proof that the same page still displays the same value today.
- **Official club pages** may be used for club-published information, but a club depth chart is not a league-verified starter list. The available charts are partial and may contain shared or empty slots.
- **Secondary datasets and market mirrors** are labelled as such. They do not become official because they are hosted on GitHub or reproduce an NFL field.
- **Model output is a research result, not an official fact.** It must carry the model definition, input cutoff, probability, score, sample size and uncertainty. Missing official evidence stays blank and flagged.
- **No result-chasing.** Strategy text, windows and gates are pre-registered; proper-score qualification precedes prospective CLV/ROI escrow; raw win rate or short-run ROI does not establish skill.

## Rebuild and verify

The core site is static HTML and the verification scripts use the Python standard library unless noted. From the repository root:

```bash
python3 scripts/check_site.py
python3 tools/check_links.py
python3 tools/check_signals_links.py
python3 engine/linelab/check_site.py
./engine/linelab/build_all.sh
python3 fl2-lines/engine/check.py
python3 ops/check_readiness.py
python3 signal/analysis/verify.py
python3 tools/check_integrated_site.py
python3 tools/check_decision_desk.py
```

The Pages workflow also rebuilds the `docs/` dashboard with `scripts/make_pages.py` and `scripts/build_site.py`. Live NFL fetching is intentionally not part of these local checks. Do not enable or run an automated NFL-page capture until the terms/permission and private-storage gates in the [integrity audit](review/integration-audit-2026-11-17.html) are resolved.

Research record only; not betting advice.
