# Executive summary

**Fourth & Signal — NFL line-origination research record**
Session `arena/d10a1d25-fl2` · 14 November 2026 · live site: https://sassnarep3-star.github.io/FL2/

Every number below is measured and reproducible from committed files. Where a value could not be
confirmed it is blank and flagged, never estimated. Nothing here is a betting recommendation, and
no profit claim is made.

---

## 1. What was asked, and what exists now

| Ask | Status | Where it lives |
|---|---|---|
| Collect and organise a full NFL data set | **Done** | 6 pipeline sections, 100+ source files, every one with a URL and SHA-256 |
| Suggestions section you can review before implementing | **Done** | `suggestions.html` — 16 proposals, each with evidence, cost, benefit, a recommended decision, and rejected alternatives |
| A clear list of questions, knowns, unknowns and how to close the gaps | **Done** | `questions.html` — 14 questions separating what we know (sourced) from what we do not |
| Originate own lines | **Baseline only, deliberately** | `lines.html` — the closing market we must beat, with two independent sign validations |
| Research signals, leaderboard with rewards, gate validation, remove luck | **Gates specified; leaderboard blocked** | `strategy.html` + `suggestions.html`. Blocked on Q02/Q03/Q05 — see §5 |
| Correlation values | **Measured for team legs** | `correlation.html` — phi 0.013 overall, 0.058 for spreads ≥ 7 |
| Track injuries plus 2nd/3rd/4th string replacements | **Injuries measured; replacement map shown to be unreliable** | `injury_signal.html`, `depth.html` |
| Executive summary | **This document** and the site overview | — |

## 2. Four measured findings

### 2.1 A live sign bug, found and fixed
The schedules file's `spread_line` is signed from the **away** team. Read naively as a home-team line
it reports a **56.93 %** home cover rate over 3,032 games — arithmetically impossible for a priced
market. Inverted, the rate is **48.53 %** (over rate 49.00 %), and the reconstruction then reproduces
the scored `outcome` column shipped inside the closing-lines file on **914 of 924 graded games
(98.92 %)**.

Any strategy built on the naive reading would have been measuring its own arithmetic error. Caught by
a sanity check, not by inspection. Both checks are published so a reviewer can reproduce them.

### 2.2 What an injury designation is actually worth
League policy attaches **no numeric probability** to Doubtful or Questionable, so every weighting was
invented. Measured against realised participation, 2016–2026:

| Official designation | Listed player-weeks | Actually participated | Play rate | 95 % CI |
|---|---|---|---|---|
| Out | 10,674 | 3 | **0.03 %** | 0.01–0.08 % |
| Doubtful | 1,684 | 15 | **0.89 %** | 0.54–1.46 % |
| Questionable | 14,948 | 9,818 | **65.68 %** | 64.92–66.44 % |

Stable across all 11 measured seasons (62.5 %–72.7 %) and materially different by position:
**QB 42.3 %**, DB 58.0 %, OL 58.2 %, skill 61.7 %, LB 65.1 %, DL 66.2 %. A quarterback listed
Questionable is ~24 points less likely to play than a defensive lineman listed the same way.

**The trap, published on purpose:** joining status only to snap counts returns a 100 % play rate.
That is survivorship bias — the snap-count file lists only players who took a snap, so anyone who sat
out leaves the denominator. Both figures appear on the site so the wrong one can be recognised.

### 2.3 The published depth chart is a weak replacement map
Listed **1st-string** players appear in that week's participation data **90.62 %** of the time
(n = 77,702); listed **2nd-string** players appear **80.39 %** (n = 59,646). A gap of only ~10 points
means the chart does not sharply separate starters from backups. It should not be used as a reliable
"next man up" map without the stronger out-snapped-the-backup test, which remains open (Q07).

The measurement also surfaced a real data trap: an initial join on the `football_name` column returned
**0 %** because that column contains only the given name ("Brian"), not a full name. Fixed only after
verifying the true schema from the downloaded files.

### 2.4 Same-game leg correlation is close to zero — except at big spreads
| Bucket | Games | Measured joint | If independent | Difference | phi |
|---|---|---|---|---|---|
| All graded games | 2,927 | 24.09 % | 23.75 % | **+0.33 pts** | 0.013 |
| Spread ≤ 3 | 1,085 | 22.30 % | 22.57 % | −0.26 pts | −0.011 |
| Spread 3.5–6.5 | 1,019 | 23.95 % | 23.85 % | +0.09 pts | 0.004 |
| Spread ≥ 7 | 823 | 26.61 % | 25.17 % | **+1.44 pts** | **0.058** |

Treating these two legs as independent is defensible overall. It is **not** defensible when combining
a big favourite to cover with the over — which is exactly the parlay most people place.

### 2.5 Six strategies tested against the gate — zero survived
The gate was fixed in code before any result was inspected: minimum sample, a bootstrap CI excluding
zero, a Benjamini–Hochberg false-discovery correction across all strategies tried, a holdout-sign
match, and a real-price requirement.

| ID | Strategy | Bets | In-sample ROI | 95 % CI | p | Holdout ROI | Failed |
|---|---|---|---|---|---|---|---|
| C1 | Fade big road favourites | 237 | +3.75 % | −8.26 to +15.72 | 0.570 | +24.67 % | G2, G3, G5 |
| C2 | Back small home favourites | 513 | −7.18 % | −15.35 to +1.12 | 0.095 | −16.19 % | G2, G3, G5 |
| C3 | Under on short rest | 195 | −4.83 % | −18.61 to +8.77 | 0.491 | −2.60 % | G1, G2, G3, G5 |
| C4 | Home rest advantage | 300 | −5.56 % | −16.28 to +5.28 | 0.341 | −11.47 % | G2, G3, G5 |
| C5 | Division home dog | 426 | −4.30 % | −13.42 to +4.82 | 0.353 | +5.39 % | G2, G3, G4, G5 |
| C6 | Under in high totals | 797 | −2.21 % | −8.91 to +4.45 | 0.526 | −8.42 % | G2, G3, G5 |

**Zero of six cleared.** The most instructive failure is G5: only ~14 % of bets could be priced from a
recorded spread or total price, so the rest fall back to a standard −110 assumption. The gate exists to
stop that assumption quietly becoming fact.

A pricing bug was caught here too: the first run reported **+148 % ROI** because a *spread* bet was
priced off the *moneyline* — the price of a straight win, not of covering a handicap. A 148 % return on
a handicap market is not a discovery; it is a bug, and it was found only because the number was
implausible.

## 3. What is deliberately not published

- **No originated line.** We have the baseline; we do not have a model that beats it. Publishing
  "our number" before it can be shown to differ usefully from the close would be an unverified claim.
- **No surviving strategy.** Six were tested and none cleared the gate. The failures are published
  rather than deleted.
- **No prop single or prop combo.** No historical prop prices exist (Q02), so neither can be priced.
- **No player-prop correlation.** Outcomes exist; prop *prices* do not. A combo cannot be priced.

Each of these appears on the site as an explicit blocked state naming the reason — not as an empty
section.

## 4. Decisions requested

Sixteen suggestions are published; eight are implemented, eight await your decision. The ones that
need you:

| ID | Suggestion | Recommendation | Blocker |
|---|---|---|---|
| **S03** | Make the validation gate code-enforced (min N, bootstrap CI excluding zero, FDR correction, untouched holdout) | approve | Q03 — threshold undefined |
| **S06** | Label market-sourced vs model-originated prop lines unmissably | approve | Q02 — no prop price feed |
| **S07** | Build prop combos on outcomes first, price only when a real price exists | approve | priced legs need Q02 |
| **S11** | Score every signal as a residual against the closing line, not the raw outcome | approve | — |
| **S13** | Rank strategies by gate pass/fail, including failures, not by raw ROI | approve | — |
| **S12** | Test rest/travel signals and publish even null results | approve | — |
| **S04** | Split every result into in-sample and holdout columns | approve | — |
| **S15** | Add a "what changed" strip | defer | — |

## 5. The three answers that unblock everything

1. **Q02 — where do historical player-prop prices come from?** No licensed feed is in hand. Without
   it, prop singles and prop combos cannot be priced or tested.
2. **Q03 — what is the minimum sample and significance threshold before a strategy may claim skill?**
   This is a policy choice, not a computation. It must be fixed *before* any strategy is scored.
3. **Q05 — prop-leg correlations.** Computable from outcomes, but meaningless without Q02.

## 6. Suggested order of work

1. Approve S03 and S14 (gate + blank-and-flag rule). Policy first; it constrains everything.
2. Decide Q02: buy a licensed prop-price feed, or formally scope props out of version 1.
3. Fix Q03 in code, publish the number of strategies tried, and freeze a holdout.
4. Only then attempt line origination (S02), scored as a residual against the close (S11).
5. Extend the depth test from *appearance* to *out-snapped the backup* before claiming any
   replacement effect (Q07).

## 7. Honest limitations

- The sandbox cannot reach `release-assets.githubusercontent.com` or `www.nfl.com` via `curl`. Bulk
  downloads therefore run in GitHub Actions, which has open egress. Every run writes a per-section
  status report; a failed section appears on the site as failed rather than being silently absorbed.
- Two sessions started from stale checkouts of the same empty repository. Their work was merged, not
  overwritten; the collision and the two small cross-session file edits are logged in
  `COORDINATION.md`.
- No browser was available for screenshots, so rendering was verified structurally: HTML nesting,
  local link resolution, and the repository's own CI validator across 14 pages.
- Correlation and base rates cover 2015–2026; earlier seasons exist upstream and are not yet verified
  here.
- Name-based joins carry a residual mismatch. It is reported alongside every matched rate rather than
  hidden.

---

*Sources: [NFL injury report](https://www.nfl.com/injuries/) · [NFL Competition Committee injury-report revisions](https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-0ap3000000688693) · [NFL Football Operations](https://operations.nfl.com/) · [nflverse-data](https://github.com/nflverse/nflverse-data) (CC-BY-4.0) · [nflverse/nfldata](https://github.com/nflverse/nfldata) · [nflreadr schedules dictionary](https://nflreadr.nflverse.com/articles/dictionary_schedules.html) · [Pro Football Reference](https://www.pro-football-reference.com/) · [NIST/SEMATECH e-Handbook](https://www.itl.nist.gov/div898/handbook/)*
