# Repository verification note — 2026-11-16

## Scope and standard

This is a local repository/build audit, not a fresh verification of live NFL facts. The sandbox can access GitHub hosts and npm/Python registries, but the tests below do not fetch or authenticate NFL.com pages. No current injury, lineup, schedule, market-price, or result claim was re-certified against an official live source in this pass. Treat the date-stamped 2026 Week 10 values and any source-verification statements elsewhere as their authors' historical claims until rechecked against the linked official page.

## Reproduced checks

| Check | Result | What it establishes / does not establish |
|---|---|---|
| `python3 scripts/check_site.py` | Pass: 7 top-level pages | Local source-link structure on those pages; not external URL availability or claim truth. |
| `python3 tools/check_links.py` | Pass: 18 pages, 101 tables, 1,305 rows, internal links and source columns | Structural integrity for the pages/data it scans; it enumerates external links but does not fetch/verify them. |
| `python3 tools/check_signals_links.py` | Pass: 16 pages, 22 sources | Local Signal section links/data-source metadata; not source-content validation. |
| `python3 engine/check_site.py` (after installing jsdom without saving package metadata) | Pass: 17 pages, 55 rendered tables, 562 links | DOM/script render and local link checks for root and `ledger/`; not all repository sub-sites and not external HTTP status. |
| `python3 -m compileall -q engine scripts tools signal/analysis` | Pass | Python syntax compilation only. |
| `git diff --check` | Pass | Whitespace check only. |
| `python3 signal/analysis/run_local.py` | **Fail** | It writes a zero-row `signal/data/market_local.json`, then `descriptive()` indexes `seasons[0]` and raises `IndexError`. The run also downloads data under `signal/raw/`; those generated changes were removed/restored after reproducing the failure. |

## Irregularities requiring review

1. **Signal rebuild failure:** `signal/analysis/run_local.py` does not stop when `build_market()` returns an empty row set; it writes that set and calls `descriptive(rows)`, which assumes at least one season. Add a fail-closed empty-data guard and a test using an empty fixture before treating the Signal analysis as reproducible. This finding is based on the local traceback, not an NFL source.
2. **Validation coverage is not repository-wide:** the passing `engine/check_site.py` covers the root and `ledger/`; `scripts/check_site.py` covers only seven root pages. `tools/check_links.py` checks more pages, but none of these runs verifies external links or whether claims still match current source content. Keep those limitations visible.
3. **Historical status / current state can be confused:** `COORDINATION.md` preserves earlier task boards, including stale claims such as “Pages not enabled yet” and an old pending PR record. Later sections report subsequent merges and deployments. Readers must use the latest dated integration record, not treat archived sections as current status.
4. **Pricing provenance and rights remain a separate gate:** local tests cannot validate a market-price feed, timestamp, sportsbook, permission/terms, or whether closing prices were available at the decision time. Do not represent historical prices as an official NFL feed; require the source policy and point-in-time provenance before publishing a backtest.
5. **No current NFL proposition established in this audit:** 2026 roster, game, injury, and outcome content was not independently checked against current NFL official pages here. Preserve blank/flagged status for any value that lacks a contemporaneous official source and capture timestamp.

## Recommended next actions

| Priority | Action | Evidence needed to clear |
|---|---|---|
| P0 | Fix and test the empty-data failure in `signal/analysis/run_local.py` (owner of that scope should implement) | A repeatable local/CI test where unavailable or empty input exits nonzero without overwriting committed data; successful populated-data rebuild with clean diff. |
| P0 | Revalidate currently published 2026 values against official NFL schedule, game centre, injury-report, transactions and game-book pages | Per-row official URL, capture time, source artifact/hash, reconciliation result, and explicit unresolved conflicts. |
| P1 | Add external-link/source freshness checks and run them for every sub-site | Report separating reachable URL from verified content; avoid treating a 200 response as validation. |
| P1 | Decide price-source policy and legal/reuse basis before publishing or updating any price backtest | Named provider/book, market and timestamp definitions, push/void rules, retained sample provenance, and documented permission/terms review. |
| P1 | Keep pre-registered hypotheses and prospective leaderboard entries distinct from historical backtests | Immutable registration commit before evaluation; no backtest-only record on the prospective leaderboard. |

## Reproduction environment notes

`engine/check_site.py` requires `jsdom`; it was installed with `npm install --no-save --package-lock=false jsdom`. No package manifest or lockfile was added. Python compilation, link checks, and DOM checks did not alter tracked files. The failed Signal rebuild's generated local artifacts were removed/restored; the working tree was clean at the end of the audit.
