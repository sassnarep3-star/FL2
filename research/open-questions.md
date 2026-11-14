# Open Questions — what must be resolved before a decision can reasonably be made

Format per question: **Known now** (verified, linked) · **Missing** · **How to discover it** ·
**What it blocks**.

---

### Q1. What are the market's actual prices?
- **Known:** nothing. No sportsbook, odds-aggregator or exchange host is reachable from this
  environment (see `COORDINATION.md` environment notes).
- **Missing:** closing spreads, totals, moneylines and player-prop lines for 2026 Weeks 1–10.
- **How to discover:** (a) a paid/permitted odds API key added as a repo secret and fetched at
  build time; (b) a CSV of closing lines committed by a human; (c) `https://www.nfl.com/odds/`
  — *not yet attempted this session* and should be tried before declaring it unreachable.
- **Blocks:** every "beat the market" claim, the whole leaderboard, and all Kelly sizing applied to
  real prices. **Without this, only probabilities can be published, never edges.**

### Q2. Is home-field advantage really ≈ 0 in 2026, or is n=137 hiding it?
- **Known:** home margin mean **−0.022 pts**, SD 13.225, n=137; home teams 48.91% / 50.36% / 0.73%
  (W/L/T). Standard error of the mean is **1.13 pts**, so the 95% CI is roughly **[−2.24, +2.20]**.
- **Missing:** whether this is a real 2026 effect or sampling noise. The CI comfortably contains
  the conventional +2 to +2.5, so **this is not evidence that HFA vanished** — only that it cannot
  be measured with 137 games.
- **How to discover:** fetch 2021–2025 seasons from
  `https://www.nfl.com/schedules/2025/by-week/week-1` … `week-18` and pool ~1,400 games per season.
- **Blocks:** any model with a hard-coded home constant. Decision needed: **use 0.0 (sample) or
  ~+2.2 (prior)?** Recommendation: shrink toward the prior, and say so.

### Q3. Are the four published team-stats tables' column headers correct?
- **Known:** `defense_rushing` rendered real headers. The eight passing columns were recovered by
  **arithmetic reconciliation** against the official player-passing leaderboard — Cmp/Att reproduces
  the published Cmp%, Yds/Att reproduces the published Y/A (San Francisco verified exactly:
  163/236 = 69.07 → published 69.1; 1980/236 = 8.39 → published 8.4).
- **Missing:** confirmed headers for **offense/scoring** (4 numeric columns), **defense/scoring**
  (3 columns) and **defense/downs** (9 columns). All three rendered headerless.
- **How to discover:** fetch the same pages with a browser engine that executes scripts, or read
  NFL.com's own glossary for the category, or find the same numbers on a page that does render
  headers and match row-by-row.
- **Blocks:** publishing those three tables at all. **They are currently not published** — see
  Flagged for Review.

### Q4. How many games *should* total 137?
- **Known:** 137 = 16+16+16+16+15+14+14+14+15 (Weeks 1–9) + 1 (Week 10 TNF). Byes ran Weeks 5–9.
- **Missing:** an independent count of completed 2026 games to confirm no game was missed.
- **How to discover:** `https://www.nfl.com/schedules/2026/by-week/week-N` for N=1..9 was the source;
  cross-check by summing each team's games played from the standings (should equal 2 × games).
- **Blocks:** nothing critical — the standings reconciliation already implies the count is right.
  **Resolved pending that cross-check** (see Integration verification in `COORDINATION.md`).

### Q5. Are the 2026 rosters real, or is the data environment synthetic?
- **Known from official pages:** Garrett listed on the Rams, Lawrence on the Bengals, Murray on the
  Vikings, Parsons on the Packers, Nelson on the Seahawks, Donald active, Evans on the 49ers,
  Etienne on the Saints, Montgomery on the Texans, A.J. Brown on the Patriots.
- **Missing:** nothing — these *are* what NFL.com prints. The question is whether the reviewer
  believes the 2026 season data.
- **How to discover:** open any linked player page, e.g.
  `https://www.nfl.com/players/a-j-brown/`.
- **Blocks:** narrative commentary only. All numbers are transcribed from the source regardless.

### Q6. Do club depth charts lag the official injury report, and by how much?
- **Known:** yes, demonstrably. 12 players are listed 1st/2nd string on a club chart while carrying
  Out/Doubtful on the official Week 10 report (e.g. **GB Josh Jacobs — 1st string on
  packers.com, Out on NFL.com**). 3 Out players (DET Kerby Joseph, GB Micah Parsons,
  KC Omarr Norman-Lott) appear **nowhere** on their own club's chart.
- **Missing:** a *fresh* official inactives feed. NFL.com publishes inactives ~90 minutes pre-game,
  which is the only truly authoritative "who is playing" source.
- **How to discover:** fetch each game's official gameday/inactives page on game day.
- **Blocks:** requirement 5's practical usefulness. Charts alone are stale by construction.

### Q7. Can same-game player-prop correlation be estimated at all here?
- **Known:** 6 player logs across 2 clubs (NE: Maye, Henry, A.J. Brown, Stevenson; CIN: Burrow,
  Chase). n=8 or 9 per pair. Example: Maye pass yds vs Henry rec yds **r = 0.5799**,
  95% CI **[−0.088, 0.884]**, p = 0.102. The CI crosses zero — the estimate is uninformative.
- **Missing:** ~30+ clubs of logs for a stable estimate.
- **How to discover:** fetch `https://www.nfl.com/players/<slug>/stats/logs/2026/` per player; the
  URL pattern is verified and each page is one fetch.
- **Blocks:** pricing prop parlays. **Currently published as illustrative only, never as a price.**

### Q8. Is the walk-forward model's failure a modelling failure or a data failure?
- **Known:** straight-up 42.86% (n=105) — *worse than a coin flip*. Brier **0.2519** vs null
  **0.2494**, skill score **−0.0098**. Full-sample fit R² = **0.0177**, p = 0.145.
- **Missing:** an explanation. Note the naive "pick the better point differential" rule scores
  **60.33%** over the same window while the fitted model scores 42.86% — that gap points to a
  **sign/implementation pathology**, not to the sport being unpredictable.
- **How to discover:** re-fit with the sign convention audited; compare against the naive rule on
  identical windows.
- **Blocks:** trusting any model output. **This is the top-priority open question.**

### Q9. What sample size would actually prove skill?
- **Known (computed, in `data/derived/analytics.json` → `skill_gates`):** at −110 the break-even
  win rate is **0.5238**. To detect a 55% hit rate at α=.05 with 80% power you need **2,243 bets**
  (≈11 seasons at 200 bets/season). At 57%: **719 bets** (≈3.6 seasons). At 62%: **164 bets**.
- **Missing:** nothing. This is arithmetic, and it is the answer to "remove luck".
- **Blocks:** the leaderboard design. **A season-long leaderboard of 200 bets cannot distinguish a
  55% bettor from a lucky one.** Reward structure must be sized to this.

### Q10. Where does the correlation that parlay pricing depends on come from?
- **Known:** parlay joint probabilities computed with a Gaussian one-factor copula; at 3 legs and
  ρ = 0.3 the joint probability is **1.52×** the independent value. Prices move materially.
- **Missing:** an *empirically estimated* ρ. The copula is a **sensitivity table**, not a
  measurement.
- **How to discover:** estimate ρ from paired game-level outcomes (see Q7) or from
  betting-market-implied same-game-parlay prices.
- **Blocks:** quoting a single parlay fair price. **Publish the sensitivity grid instead.**

### Q11. Is the "Teams on Bye" record block on NFL.com historical or current?
- **Known:** on `week-N` pages the bye block prints **current** records, not as-of-week records.
  Week 10 byes show CHI 7-2, DEN 7-2, PHI 2-7, TB 3-6 — which are their records *today*.
- **Missing:** confirmation of intent from NFL.com.
- **How to discover:** compare a bye team's record printed on a week-5 page with its record printed
  on a week-9 page; if identical, it is current-state.
- **Blocks:** any historical "record at time of bye" claim. **Flagged; do not use.**
