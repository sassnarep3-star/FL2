# Price-data policy — FL2 (session 310620fe)

Frozen before any backtest or leaderboard result that depends on price data is published
(requirement: "Decide the price-data policy before any backtest is published").

## Facts verified in this environment

| Fact | Evidence |
|---|---|
| NFL.com hosts **no odds page** — `https://www.nfl.com/odds/` returns 404 | session 1374049c verification, reproduced in COORDINATION.md |
| No T1/T2 source carries bookmaker prices | nfl.com has no odds page; operations.nfl.com publishes no market data |
| nflverse `games.csv` carries `spread_line`, `total_line`, `away_moneyline`, `home_moneyline` per game | `raw/games.csv` (local copy, sha256 recorded in the snapshot ledger) |

## Policy

1. **P1 — No invented prices.** A price cell is either filled from a cited source or left
   blank. Interpolating, averaging "typical" values, or carrying a price forward is forbidden.
2. **P2 — Tier labelling.** Every price row carries `tier`: `T1 official league`, `T2 open data
   (official-derived)`, or `T3 aggregated market`. T3 rows are labelled
   `market_data_unverified_by_official_source` and **must never** be used as a statistical input
   to a strategy's validation gate. T3 prices are used only to (a) define break-even rates and
   (b) compute residuals/CLV against our originated lines.
3. **P3 — Opening vs closing.** Opening numbers are captured only when a source publishes them.
   nflverse publishes closing lines only; where an opening number is unavailable the cell stays
   blank and the row is flagged `opening_unavailable`.
4. **P4 — Sign convention (asserted everywhere).** `spread_line > 0` means the **home** team is
   favoured by that margin; `spread_line < 0` means the away team is favoured. Any consumer that
   violates this must abort (the baselines script asserts it).
5. **P5 — Vig handling.** Moneyline-implied probabilities are published only as
   **vig-free** (two-outcome multiplicative normalisation): `p_i = (1/odds_i) / Σ (1/odds_j)`.
   Raw implied probabilities with vig are never published.
6. **P6 — Snapshot rule.** Every price read is appended to `ops/data/price_snapshots.csv` with a
   UTC timestamp, the source URL, and the sha256 of the source snapshot it came from. Nothing
   overwrites an existing row; corrections are appended with `supersedes`.
7. **P7 — Backtest gate.** A backtest may use price data only from the corpus window
   (2011–2026 nflverse closing lines) and must state the window. No 2026 post-snapshot price is
   treated as "closing" until the game has been played.
