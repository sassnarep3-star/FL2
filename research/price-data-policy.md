# FL2 price-data policy

**Decided:** 2026-11-16 (UTC) · **Owner:** session-65556dd2 · **Status:** frozen
**Rule:** this policy is committed *before* any backtest is published from this
session, as required by the project brief ("Decide the price-data policy before any
backtest is published").

## 1. Why a policy is needed

There is **no official league source for market prices**. `https://www.nfl.com/odds/`
returns 404 (recorded as irregularity #7 by session-1374049c, reproducible). Every
price therefore comes from a commercial aggregator or an open-data mirror, and must
be treated differently from stats.

## 2. Tiering (matches the repo-wide source tiers)

| Tier | What | Permitted use |
|---|---|---|
| **T1** | Official league pages (`nfl.com`, `operations.nfl.com`, official game books) | Any stat value. Never a price — none exists. |
| **T2** | nflverse open-data mirror of NFL-derived data (`nflverse/nfldata` on GitHub) | Stats + **historical closing/initial lines**, always labelled "market data (T2 mirror of commercial consensus)" and never a *model input*. |
| **T3** | Commercial odds aggregators (ESPN consensus, CBS Sports, etc.) captured live via the page-fetch tool | **Prices only.** Each row carries provider URL + capture timestamp. Never a stat value, never a model input. |

## 3. Hard rules

1. **Market prices are never model inputs.** A price may appear only as the *market
   column* beside our originated fair line, in residual (fair − market) accounting,
   and in closing-line-value accounting. The model consumes results and official
   stats only.
2. **Opening and closing are distinct snapshots.** The price store records
   `opening_line` (first capture, with `opening_captured_at`) and `closing_line`
   (last capture before kickoff, with `closing_captured_at`) per game/market/side.
   A missing side of the pair is stored as blank with `status: open-only` /
   `close-only` / `pending-close` — never imputed.
3. **Every price row carries:** provider, provider URL, capture timestamp (UTC),
   and a `market_data_unverified` flag (there is no official source to verify it
   against; the flag is permanent).
4. **Capture schedule (from day one):** a snapshot is recorded (a) when a market is
   first originated for a slate, (b) at the last capture before kickoff (close), and
   (c) after kickoff only for settlement bookkeeping (result feed), never as a price.
5. **Vig handling:** consensus moneylines/spread prices are published de-vigged in a
   separate column (`vig_free_*`) using the standard proportional method; raw and
   de-vigged values are both stored. The residual view ("Vig-Free Market Consensus
   vs. Originated Fair-Line Decomposition") uses the de-vigged consensus.
6. **No backtest may be published** that grades against a price not present in the
   store with both a provider URL and a capture timestamp. Historical backtests
   (pre-2026) use nflverse `closing_lines.csv` (2006–2026) and `initial_lines.csv`
   (2021 only — the only opening-line history reachable from this environment).
   The 2021-only opening history is an explicit, documented limitation.

## 4. Known gaps (flagged, not filled)

* No official price source exists at all (nfl.com/odds 404).
* Opening-line history before 2021 is unreachable from this environment
  (`initial_lines.csv` covers 2021 only).
* Live commercial captures depend on the page-fetch tool; if a provider page is
  unreachable, the row is blank + flagged, and the residual is left blank.
* `closing_lines.csv` prices are a market consensus, not any single book; they are
  labelled as such and cannot support per-book CLV accounting.

## 5. Review trigger

Re-open this policy if (a) an official league price feed appears, (b) a licensed
historical odds archive is purchased (hub Q01/Q02/Q03), or (c) a strategy reaches
the prospective CLV/ROI escrow stage (two-stage skill leaderboard).
