# Price-data policy — decided before any backtest is published

Written 2026-11-16T01:30Z, before the Week 10 close, and pinned by the commit that first
contains this file. Any change is a new version of this file plus a new commit; the backtest
corpus records which version it was run under.

1. **No official price exists.** The league publishes no odds page. Every price in this
   repository is a third-party mirror of sportsbook data (`nflverse/nfldata`), tier **T3**.
   No price is ever described as official, and no correlation panel mixes prices with
   official numbers (see `analytics.html`).
2. **What T3 may be used for.** Calibration of the residual against the market; measuring
   vig/overround; grading a line we originated. What it may **not** be used for: being the
   sole evidence for a strategy's skill, or appearing on any page as a fact about a game.
3. **Opening and closing are separate fields, and both carry a source and a timestamp.**
   Today the mirror carries a closing number for 456 of 816 market rows and an opening
   number for **0**, with **no timestamp on any row**. Therefore:
   * the opening-to-close *move* is not computed for 2026 and is not modelled;
   * 2021 (the only season with opening rows: 1,088) is the only season where a move exists,
     and it is used only to sanity-check the direction of a move, never to price 2026.
4. **Unplayed fixtures may not borrow a price as if it were timed.** The mirror carries
   prices for 15 unplayed 2026 fixtures (8 of 13 Week 11 games disagree with our line by
   more than 8 points). Those rows are published with
   `market_reference_provenance = timing uncertified` and are **excluded from every gate**.
5. **Storage.** The snapshot store keeps line, odds, market, side, source, capture time and
   SHA-256 of the file it came from (`data/prices/MANIFEST.sha256`). Raw bodies are not
   copied into the published site; only counts, hashes and aggregates are (public analysis
   layer vs private data layer).
6. **CLV.** Closing-line value may only be computed against a close whose timestamp is
   recorded and is after our own recorded forecast time. That condition is not met today,
   so the escrow ledger records our line only; CLV becomes computable when capture #2 exists.
