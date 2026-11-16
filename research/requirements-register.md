# Requirements register — method and reading guide

**Session:** session-65556dd2 · **Date:** 2026-11-16 · **Rows:** 72 (37 done, 29 partial, 6 blocked)
**Machine-readable source:** `data/decision_readiness.json` · **Rendered:** the decision-readiness
table on the landing page (`index.html`) and `origination/decision-readiness.html`.

## How status is decided

* **done** — the artifact exists in this repository and was checked against its source
  (official page, or deterministic build from committed data). Every row names the artifact.
* **partial** — the design is frozen or a first slice exists, but a named gate blocks completion.
* **blocked** — a gate outside this session's control (NFL terms §1.3, missing permission,
  or an unreachable source) prevents even the first slice.

Nothing is marked done without an artifact. Review findings from the owner brief (VR-xx / VQ-xx
style claims) are preserved verbatim where they cannot be reproduced in-repo — they are listed
as findings with the reproduction status, never silently corrected or dropped.

## The gates that block the most rows

| Gate | Rows blocked/partial | What would clear it |
|---|---|---|
| **F-T1 — NFL terms §1.3** (systematic database compilation needs written consent) | DR-10, DR-12, DR-21, DR-29, DR-30, DR-31, DR-39, DR-47, DR-54, DR-55 | Written NFL consent, or an owner-approved manual capture cadence within the terms |
| **F-D1 — no verified depth-order source for 32 clubs** (Texans publish depth as an image; Packers prepend jersey numbers) | DR-06, DR-32, DR-33, DR-43, DR-45, DR-51, DR-52 | 32/32 clubs by one verified route: club pages (5/32 today) or the snap-count starter proxy (32/32 coverage in `signal/data/snap_participation.csv`) |
| **DR-31 — game-day inactives not captured** | DR-44, DR-53 (calibration joins) | 272 game-day inactive lists per season captured at publication time |
| **Market prices have no official source** (`nfl.com/odds` → 404) | DR-60 (quoted moneyline) | A provider quoting moneylines at open and close (policy-compliant T3 capture) |

## Rejections recorded permanently (from the brief)

1. Deriving depth order from jersey number, experience or salary (DR-50).
2. Ranking strategies by season-long ROI (DR-65).
3. Fixed injury penalties — ablations only (DR-27/DR-28).
4. Multiplying marginal probabilities for combos without a validated joint probability (DR-36).

## Where the numbers come from

* Week 10 results and records: official nfl.com capture `data/captures/week10-results-2026-11-16.json`
  (cross-checked 12/12 finals vs ESPN; standings replayed 32/32 by `tools/build_results_feed.py`).
* Week 11 market prices: Yahoo consensus capture `data/captures/week11-market-2026-11-16.json`
  (T3, `market_data_unverified` permanently — `research/price-data-policy.md`).
* Week 10 official injury re-capture: 347 rows / 28 clubs / 14 games, structure errors 0
  (session 8326a20d, `tools/official_injury_capture.py`; team counts published, rows kept private).
* SB-1 forecasts: `data/forecast_ledger.json` (probability + inputs per game; registration
  commit `55b94c1`; gate G4 pass — generated before the first Week 11 kickoff).
* Luck bands: exact binomial at −110 break-even (`tools/run_leaderboard.py`).

## Review findings that could NOT be reproduced in-repo (kept verbatim, flagged)

| Finding (owner brief) | Reproduction status |
|---|---|
| "254 rows and 4 no-injury sections versus 279 rows and 2 sections live" (Week 10 injury tables) | Not reproducible: the repo holds 76 (README label), 160 (CSV), 345 (JSON, 2026-11-14), 347 (official capture, 2026-11-16). See `fl2-dashboard/flagged-review.html` F-I3 |
| Lions game-status cells "published blank" | Withdrawn as false: all three read **Out** on the official page (F-L1) |
| "149 club/unit/position slots list more than one rank-1 player" | Not verifiable from committed data (the 2026 depth capture covers 5 clubs); design rule adopted regardless (DR-33) |
| Baltimore depth still lists Lamar Jackson + Tyler Huntley after IR | Huntley out-for-season confirmed via dated nfl.com news link; the Jackson IR claim needs a source — kept flagged (DR-46) |
| Lock / McCord / Brissett dated starter changes (VR-24/25) | McCord in-line-for-start confirmed (nfl.com news link in `data/news_2026_week10.csv`); Lock/Brissett items need their specific article URLs — kept flagged |
