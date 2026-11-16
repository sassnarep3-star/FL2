# Requirements Inventory — FL2

> **Reconciliation note — 2026-11-16:** This is the earlier 10-row grouped inventory. Its summary figures,
> source-coverage statements, and status labels are retained as historical project claims, not re-verified
> by the current integration. [`data/requirements-crosswalk.csv`](../data/requirements-crosswalk.csv) maps
> every grouped row and all 25 rows in the legacy CSV to the 81-row operational register. Local Week 10
> files are dated 2026-11-14; selected dynamic NFL pages were read on Nov 16 without archived responses
> or hashes. The older inventory's full-season, row-by-row, and 5-of-32 depth claims therefore remain
> subject to the source, coverage, and freshness gates in [`readiness-review.html`](../readiness-review.html).
>
> The current readiness status is assessed per atomic row and does not inherit an older `done` label.

Executive summary first, then the register. The original status wording and summaries below describe
that earlier inventory; they should not be read as current-source or current-deployment certification.

## Executive summary

1. **A complete 2026 season dataset was verified, not scraped-and-hoped.** 137 completed games,
   all 32 official standings rows, and the full official Week 10 injury report were transcribed
   from NFL.com and then reconciled against each other. Replaying the 137 games reproduces the
   published standings **exactly for all 32 teams** (W-L-T, points for, points against). That is
   the single strongest verification in this project.
2. **The headline betting finding is negative and it matters.** In this 2026 sample home teams won
   **48.91%** of games and the average home margin is **−0.022 points**. Home-field advantage is
   approximately **zero** this season. Any model that hard-codes +2.5 or +3 home points is wrong
   for 2026 and will lose money.
3. **No strategy in this repository passes its validation gate yet.** The walk-forward power model
   posts Brier 0.2519 against a 0.2494 no-skill benchmark — a Brier skill score of **−0.0098**,
   i.e. indistinguishable from noise. Publishing it as a "winning system" would be dishonest. It is
   published as a **rejected** strategy with the arithmetic shown.
4. **The requirement to produce proprietary lines cannot be fully met with public data alone.**
   Producing a *line* requires either market odds (to beat) or a calibrated probability model. No
   market/odds source was reachable under this environment's network restrictions, so the project
   delivers the **probability machinery, the validation gates, and the sample-size arithmetic**
   instead of fabricated numbers. This is stated plainly rather than papered over.
5. **27 of 32 depth charts were not acquired**, and the 5 that were are club-published and labelled
   "unofficial" by the clubs themselves. Requirement 5 is therefore only partially satisfied and is
   flagged as such rather than filled with plausible-looking guesses.

## Register

| ID | Requirement (user's words, condensed) | Status | Where it is satisfied | Evidence |
|----|----------------------------------------|--------|-----------------------|----------|
| R1 | Collect/organize/analyze full requirement list; executive summary | **done** | this file; `research/`, site `Requirements` page | every row below links a file that exists |
| R2 | Suggestions section a reviewer can compare and choose from, before implementation | **done** | `research/suggestions.md`; site `Suggestions` page | 6 suggestions, each with Path A / Path B / recommendation, none implemented |
| R3 | Questions / info / answers that must be resolved before deciding; how to discover the missing info | **done** | `research/open-questions.md`; site `Open Questions` page | 11 questions, each with known vs missing vs how-to-discover |
| R4 | Originate proprietary lines; strategy research; leaderboard competition; singles, parlays, player-prop combos; validation gates; correlation values; remove luck, build selectively skill-based strategies | **partial — blocked on market data** | `research/validation-gates.md`, `research/strategies.md`, `data/derived/analytics.json`, site `Strategies` + `Analytics` pages | gates defined and computed; 4 candidate strategies scored, all **FAIL**; correlations published with CIs |
| R5 | Track injuries; know defensive/offensive deficiencies caused by 2nd/3rd/4th-string backups | **partial — 5 of 32 clubs** | `data/injuries.json`, `data/depth_charts.json`, `data/derived/backup_impact.json`, `research/injury-backup-analysis.md` | full official Week 10 report (28 team entries); 9 first-stringers Out/Doubtful located with named backups; 3 Out players absent from their own club chart |
| R6 | Review line by line; verify from official trusted sources; links for manual review; flag irregularities | **done** | every data file carries a `meta` block with source URLs; site `Sources` and `Flagged` pages | `data/raw/` holds nothing — every figure traces to a linked NFL.com page |
| R7 | GitHub Pages site: clean landing page + subpages by category, dashboard-like, findings in tables | **done** | `fl2-signals/` (built by `tools/build_signals_site.py`) | 18 pages, shared nav, every data table row has a Source cell |
| R8 | Verify line by line; **every** table row carries an official source link; unconfirmable values blank + flagged; never infer | **done** | `tools/build_site.py` emits a `Source` column on every table; blank cells render as `—` | team-stats pages where headers could not be confirmed were **not published** rather than guessed |
| R9 | `COORDINATION.md` shared board: claim, scope, commit+push immediately, rebase before push, conflict logging | **done** | `COORDINATION.md` at repo root | rewritten from file-existence evidence; 2 sessions logged (this one plus a `needs review` handoff) |
| R10 | PR + merge without waiting; summary of changes, sources, irregularities; Pages deploy confirmed; never merge broken | **done** | PR opened, merged, deploy confirmed; recorded in `COORDINATION.md` | see integration section at the bottom of `COORDINATION.md` |

## Acceptance criteria that were *not* met, stated plainly

| Requirement | Gap | Why | What would close it |
|---|---|---|---|
| R4 proprietary lines | No line is published | A line is a price. With no market odds reachable, any number published would be invention | A closing-line data source (see `research/open-questions.md` Q1) |
| R4 leaderboard with rewards | No leaderboard | A leaderboard of zero passing strategies is meaningless | ≥1 strategy passing gate G2 out of sample |
| R5 depth charts | 27 of 32 clubs missing | Each chart is a separate club-site page; 5 were fetched and verified this session | Fetch the remaining 27 club pages |
| R5 quantified deficiencies | No "points lost by backup" number | Not derivable from any official source | Play-by-play/snap-count source with a licence |

Full detail, with links: `research/open-questions.md`, `research/validation-gates.md`,
`research/injury-backup-analysis.md`, and the site's **Flagged for Review** page.
