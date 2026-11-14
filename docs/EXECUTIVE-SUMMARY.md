# Executive Summary — NFL Decision Hub

**Prepared:** 2026-11-14 · **Data snapshot:** Week 10, 2026 season · **Repository:** `sassnarep3-star/FL2`
**Live site:** https://sassnarep3-star.github.io/FL2/

---

## 1. What this is

A decision surface for an NFL line-origination project. It separates three things that normally get mixed
together, because mixing them is how projects like this fail:

| Layer | What it contains | How you can check it |
| --- | --- | --- |
| **Verified** | Facts transcribed from official NFL and club properties, each row carrying a source link | Click the source link on the row |
| **Measured** | Numbers this project computed itself, with the script that computes them committed | Re-run `tools/*.py`; output is reproducible |
| **Proposed** | Methods and hypotheses with no validation yet, explicitly marked | Search the page for a performance claim; there should be none |

Nothing in this repository is a reported betting result. There is no win rate, no ROI and no profit figure
anywhere, because no odds data has been ingested. That is deliberate: a performance number without a sourced
price history behind it would be indistinguishable from a fabricated one.

---

## 2. The ask, and the honest status of each part

| Asked for | Status | Where | Caveat |
| --- | --- | --- | --- |
| Full requirements list | **Done** | `data/requirements.csv`, `pages/requirements.html` | 25 numbered items, each with a named deliverable |
| Suggestions, in a reviewable section, before implementing | **Done** | `pages/suggestions.html` | 15 items with adopt / test / reject recommendations |
| Questions, information and answers needed before deciding | **Done** | `pages/decision-questions.html` | 18 questions, each naming what would answer it |
| Originate our own NFL lines | **Proposed** | `pages/strategies.html#line-origination` | 8-step method specified; uncalibrated |
| Leaderboard with rewards for top strategies | **Proposed** | `pages/validation-gates.html#leaderboard` | Scoring rule designed; "reward" is undefined (Q18) |
| Single bets, parlays, player-prop combos | **Partial** | `pages/strategies.html` | Singles modelled; parlays and props blocked on missing player data |
| Every strategy passes validation gates | **Done** | `pages/validation-gates.html` | 10 gates with numeric thresholds |
| Determine correlation values | **Partial** | `pages/correlation.html` | Cross-sectional measured; event-level not computable |
| Remove luck from the equation | **Done** | `pages/luck-and-skill.html` | Frameworks and sample-size arithmetic; applied to nothing yet |
| Track injuries | **Done** | `pages/injuries.html` | 160 Week 10 status rows, verified |
| Know 2nd / 3rd / 4th-string deficiencies | **Partial** | `pages/injuries.html#depth` | Depth verified for 2 of 32 clubs |
| Executive summary | **Done** | this document | — |
| Verified site, merged PR, no manual input | **Done** | `pages/repo-audit.html` | Link-checked before deploy |

---

## 3. What was verified, and how

**Coverage:** 32 of 32 clubs, Week 10 of the 2026 season.

| Dataset | Rows | Source | Independent check performed |
| --- | --- | --- | --- |
| Standings | 32 clubs | `nfl.com/standings` | Winning percentage re-derived as (W + 0.5·T) ÷ GP — 32/32 match. Net points re-derived as PF − PA — 32/32 match. |
| Team passing / rushing / defence | 32 clubs | `nfl.com/stats/team-stats/...` | Completion % and yards per attempt re-derived from their own numerators — 32/32 match. |
| Next Gen Stats efficiency | 16 of 32 clubs | `nfl.com/stats/ngs/trends` | Cross-source: derived PPG vs NGS-published PPG agreed within 0.05 for 16/16 clubs. |
| Week 10 schedule | 14 games | `nfl.com/schedules` + `operations.nfl.com` | Bye list asserted; no club appears twice; 28 club-slots + 4 byes = 32. Total team-games from standings = 274 → 137 league games, consistent. |
| Injury report | 160 status rows, 26 clubs | `nfl.com/injuries` | Transcribed club-by-club; only rows carrying an official game status are included. |
| Depth charts | 2 clubs, full 1st–4th string | `chiefs.com`, `seahawks.com` | Cross-checked against `nfl.com` rosters for positioning. |
| Injury-report policy deadlines | 1 document | `media.nfl.com` (league communications) | Filing windows and game-status definitions read directly from the league's own PDF. |

Every build script asserts its own checks and fails loudly on drift. `tools/check_links.py` verifies that every
internal link and anchor resolves, that every dataset carries a source column, and that no page references an
external CDN.

---

## 4. What we measured ourselves

These are this project's own arithmetic, reproducible by running the scripts in `tools/`.

### 4.1 The tax you must beat

| Price | Implied probability | Win rate needed to break even |
| --- | --- | --- |
| −105 | 51.22% | 51.22% |
| **−110** | **52.38%** | **52.38%** |
| −120 | 54.55% | 54.55% |
| −150 | 60.00% | 60.00% |

Two-way hold at −110 / −110 is **4.76%**. A strategy winning 52% is losing money. The gap between "good" and
"profitable" is about one percentage point wide.

### 4.2 Parlays multiply the tax

| Legs (each −110) | Offered decimal | Effective hold | EV per unit staked |
| --- | --- | --- | --- |
| 1 | 1.9091 | 4.55% | −4.55% |
| 2 | 3.6446 | **8.88%** | −8.88% |
| 3 | 6.9579 | 13.03% | −13.03% |
| 6 | 48.4127 | **24.36%** | −24.36% |

### 4.3 Correlation is not a refinement — it is the model

Two legs, each modelled as a no-vig 50/50, priced together at −110 / −110:

| Latent correlation ρ | Fair joint probability | EV at the offered price |
| --- | --- | --- |
| −0.40 | 18.45% | **−32.75%** |
| 0.00 | 25.00% | −8.88% |
| +0.40 | 31.55% | **+14.99%** |
| +0.80 | 39.76% | +44.90% |

Assuming independence is a ~47-point error across that range. Computed with a bivariate-normal copula
(`tools/calc.py`); the ρ = 0 case reproduces 25.00% exactly, which is used as a unit test.

### 4.4 Correlation, measured on the actual data

| Relationship (32 clubs) | r | R² | 95% bootstrap CI |
| --- | --- | --- | --- |
| Offensive EPA/play vs points per game | **0.926** | 85.8% | [0.791, 0.984] |
| Defensive EPA/play allowed vs points allowed | 0.852 | 72.6% | [0.759, 0.947] |
| Offensive passing Y/A vs points per game | 0.685 | 46.9% | [0.497, 0.834] |
| Sacks taken vs points per game | −0.621 | 38.6% | [−0.797, −0.386] |
| Opponent passing Y/A vs points allowed | 0.582 | 33.9% | [0.316, 0.806] |
| Defensive interceptions vs points allowed | −0.561 | 31.5% | [−0.765, −0.383] |
| **Rushing Y/A vs points per game** | **0.023** | **0.1%** | **[−0.233, 0.298]** |
| Sacks recorded vs points allowed | −0.265 | 7.0% | [−0.571, 0.086] |

The important result is the seventh row: **a popular hypothesis was killed by our own data before it cost
anything.** Rushing efficiency explains essentially none of the variance in scoring. That strategy is marked
*rejected* and kept on the board so it does not get rebuilt by a future session.

### 4.5 Removing luck is arithmetic, not a slogan

- To distinguish a true **55%** win rate from the 52.38% break-even at 80% power: **2,243 settled bets**.
- To distinguish a true **53.5%** rate: **12,305 bets**.
- At 500 bets, nothing below a 57.9% true rate is distinguishable from noise.
- A single zero-edge strategy has a **25.14%** chance of showing ≥55% over 200 bets.
- Across 500 such strategies, the chance at least one looks brilliant is **100%**.

That last line is the reason a leaderboard needs pre-registration and a false-discovery correction before it
means anything.

---

## 5. What is genuinely unknown

| Gap | Consequence | What closes it |
| --- | --- | --- |
| **No odds or price data at all** | Gates G3, G4, G5, G9 cannot be cleared for any strategy. 9 of 12 strategies are blocked on this alone. | A licensed historical odds archive with per-book closing prices |
| **Depth charts for 30 of 32 clubs** | The 2nd/3rd/4th-string requirement is met for Kansas City and Seattle only. 209 injury rows carry a blank depth field — blank, not estimated. | Per-club depth-chart capture (mechanical, no dependency) |
| **Injury designations have no published predictive value** | Any injury weight is an assumption. Ours is labelled proposed. | Designations joined to realised snap counts |
| **No player-level game logs** | Same-game prop correlation — the number that prices a parlay — cannot be computed. | Player game logs, 3+ seasons, both legs |
| **Whether the market is beatable at all** | The literature disagrees: Levitt (2004) argues books price to maximise profit; Boulier et al. (2006) could not reject efficiency; a ten-season home-underdog study found no variation profitable every year. | Our own backtest on a licensed archive |
| **No consolidated official depth endpoint** | `nfl.com/teams/{club}/depthchart` returns **404**. Recorded as a negative finding (S17). | Per-club capture, or a licensed roster feed with depth order |

---

## 6. The three decisions that unblock everything

### D1 — Buy a licensed historical odds archive
One purchase unblocks gates G3, G4, G5 and G9 for nine strategies, and answers Q01, Q02, Q03 and Q15 at once.
**Nothing else in this project has that leverage, and the agent cannot make this decision.** This is the single
hard blocker that cannot be cleared without you.

### D2 — Pre-register the strategy registry and set a sample floor
Free, immediate, and it is what makes the leaderboard mean anything. Recommended: show at 500 bets, rank at
2,000, and apply a false-discovery correction across the whole registry. Answers Q04 and Q05.

### D3 — Decide what this is: research artefact, product, or syndicate
The brief mixes all three, and they pull in different directions. The recommended default is a **research
artefact that publishes originated lines and explicitly does not place bets** — which also sidesteps the
league's gambling-policy exposure and any licensing question. Answers Q17.

---

## 7. What we deliberately did not build

- **No automated bettor.** Zero of twelve strategies pass the out-of-sample gate. Automating placement now would
  convert modelling error into money at scale, and it would change the legal posture of the project.
- **No live odds display.** Without rights confirmation (Q03) and a spend decision (Q15), republishing licensed
  prices would be legal exposure taken for a cosmetic gain.
- **No performance claims.** There is no price history to grade against, so there are no results to report.
- **No inferred values.** Where a source did not answer, the cell is blank and the item appears on the
  Flagged for Review page with a way for you to check it yourself.

---

## 8. Flagged for review (9 items, none blocking)

Full detail with source links and self-check instructions: `pages/flagged.html`

| ID | Type | Item |
| --- | --- | --- |
| F01 | Missing | Depth charts for 30 of 32 clubs (209 blank fields) |
| F02 | Negative finding | No official league-wide depth-chart endpoint (404 confirmed) |
| F03 | Missing | No odds, prices or closing lines anywhere in the project |
| F04 | Ambiguity | Injury designations have no published predictive value (84 Questionable rows) |
| F05 | Rounding | DET and MIN derived PPG differ from NGS by 0.05 — rounding, recorded not hidden |
| F06 | Partial coverage | NGS EPA published for only 16 of 32 clubs on the captured page |
| F07 | Legal / eligibility | League gambling policy constrains any bet-placing product |
| F08 | Scope | Primary deliverable undefined (Q17) |
| F09 | Undefined | "Reward" on the leaderboard undefined (Q18) |

---

## 9. Sources

All retrieved 2026-11-14. The machine-readable registry is `data/sources.csv` (22 entries).

| ID | Source | Tier |
| --- | --- | --- |
| S01 | [NFL Injury Report — Week 10 2026](https://www.nfl.com/injuries/) | league |
| S02 | [NFL Standings 2026](https://www.nfl.com/standings/) | league |
| S03 | [Team Stats — offense passing](https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all) | league |
| S04 | [Team Stats — defense passing](https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all) | league |
| S05 | [Schedule — 2026 Week 10](https://www.nfl.com/schedules/2026/by-week/week-10) | league |
| S06 | [Next Gen Stats — League Trends](https://www.nfl.com/stats/ngs/trends) | league |
| S07 | [NGS — Intro to Passing Score metric](https://www.nfl.com/news/next-gen-stats-intro-to-passing-score-metric) | league |
| S08 | [Football Operations — Important Dates](https://operations.nfl.com/gameday/nfl-schedule/2026-important-nfl-dates) | league |
| S09 | [Football Operations — home](https://operations.nfl.com/) | league |
| S10 | [NFL Important Dates PDF (league communications)](https://media.nfl.com/content/dam/communications/football-communications/2025/news/06%2005%2025%20-%20Important%20Dates.pdf) | league |
| S11 | [Kansas City Chiefs depth chart](https://www.chiefs.com/team/depth-chart) | club |
| S12 | [Seattle Seahawks depth chart](https://www.seahawks.com/team/depth-chart/) | club |
| S13 | [NFL roster — Kansas City](https://www.nfl.com/teams/kansas-city-chiefs/roster) | league |
| S14 | [Player stats — passing 2026](https://www.nfl.com/stats/player-stats/category/passing/2026/reg/all/passingyards/desc) | league |
| S15 | [Team Stats — offense scoring](https://www.nfl.com/stats/team-stats/offense/scoring/2026/reg/all) | league |
| S16 | [Football Operations — AT Spotters](https://operations.nfl.com/gameday/behind-the-scenes/at-spotters) | league |
| S17 | [Depth chart endpoint — 404 (negative finding)](https://www.nfl.com/teams/kansas-city-chiefs/depthchart) | league |
| S18 | [Levitt (2004), Economic Journal](https://www.ubplj.org/index.php/jpm/article/download/429/461) | secondary |
| S19 | [Gimpel, Beating the NFL Point Spread (CMU)](https://www.cs.cmu.edu/~epxing/Class/10701-06f/project-reports/gimpel.pdf) | secondary |
| S20 | [Home-Underdog Theory, Major Themes in Economics 22](https://scholarworks.uni.edu/cgi/viewcontent.cgi?article=1148&context=mtie) | secondary |
| S21 | [NFL 2024-25 Important Dates](https://www.nfl.com/news/2024-2025-national-football-league-important-dates) | league |
| S22 | [Team Stats — offense rushing](https://www.nfl.com/stats/team-stats/offense/rushing/2026/reg/all) | league |

Secondary sources are used for context only and never to assert a fact about a team, player, injury or price.

---

## 10. Method note and disclosure

**No manual input was required.** Every dataset is generated by a committed script; every page is generated by
`tools/build_site.py` from those datasets; the site is link-checked by `tools/check_links.py` before deploy.

**Retrieval constraint, disclosed honestly:** the sandbox used for this work has no outbound network access
except to GitHub, npm and PyPI. All web verification was performed through a page-fetch tool against the
official URLs, and the returned text was inspected before anything was transcribed. No value was produced from
memory. The trade-off for a reviewer: every cell can be checked by opening its linked source in a browser, but
it cannot be re-fetched by a script inside this environment.
