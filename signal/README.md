# Signal Lab — measured NFL signals, a validation gate, and a decision queue

**Live:** https://sassnarep3-star.github.io/FL2/signal/

This is its own section of the repository, built by session `arena/d10a1d25-fl2`. It follows the
repository's integration convention: **relocate your own files, never overwrite another session's.**
Nothing outside `signal/` was changed except one tile and one nav link on the root hub, and two
additive entries in the root checkers' allowlists.

## What makes this section different

Every number here is **measured from a committed data file**, re-derived by CI on every push, and
linked to its primary source. Anything that could not be confirmed is blank and flagged. The site
build is **byte-reproducible**: `analysis/build_site.py` run twice produces identical output, and CI
fails if a rebuild differs from what is committed.

## The five findings

| Finding | The number | Decision it implies |
|---|---|---|
| **A live sign bug, found and fixed** | `spread_line` is signed from the *away* team. Read as a home line: 56.93 % home cover over 3,032 games. Corrected: 48.53 % cover, 49.00 % over, and 98.92 % agreement with the scored `outcome` in `closing_lines.csv` | Retire the naive reading |
| **Injury designations now have a measured value** | Questionable played **65.68 %** (n = 14,948, CI 64.92–66.44), Doubtful 0.89 %, Out 0.03 % | Price availability from measurement, not opinion |
| **The depth chart is a weak replacement map** | 1st string appears 90.62 % of weeks vs 80.39 % for 2nd string — a ~10-point gap | Do not claim a "next man up" effect from the chart alone |
| **Same-game correlation is near zero overall, real at big spreads** | phi 0.013 overall; **0.058** at spreads ≥ 7 | A big-favourite-cover + over parlay is the case where independence pricing costs money |
| **Six strategies tested, none survived** | 0 of 6 cleared the pre-registered gate; best in-sample +3.75 % with a CI spanning zero | Do not fund a leaderboard or stake plan yet |

## Pages

| Page | What it answers |
|---|---|
| `index.html` | Section overview, generated entirely from the data files |
| `suggestions.html` | 16 proposals: evidence, cost, benefit, recommended decision, rejected alternatives, and implementation outcome |
| `questions.html` | 14 decision-blocking questions split into what we know (sourced) and what we do not |
| `lines.html` | The closing market we must beat, with both sign validations published |
| `injury_signal.html` | What each official designation is actually worth, with the survivorship-bias trap shown and rejected |
| `depth.html` | Does the published depth chart predict who plays? |
| `correlation.html` | Measured same-game leg correlation, because parlay pricing assumes none |
| `validation.html` | The pre-registered gate, all six strategies, and each failure reason |
| `health.html` | Provenance: per-file URL, SHA-256, row count, pipeline section status |

## What is deliberately not published

No originated line, no surviving strategy, no player-prop single, no prop combo, no leaderboard
ranking. Each is blocked for a named reason — no licensed historical prop prices (**Q02**), no
prop-leg correlations (**Q05**), and a gate that no team-bet candidate has passed. Every block is
stated on the site rather than left as an empty section.

## Pipeline

```
analysis/run_local.py       market rows + recorded closing prices (validated sign convention)
analysis/aggregate.py       injuries, depth charts, snap counts, player stats, play-by-play
analysis/injury_signal.py   realised participation by official designation
analysis/correlation.py     same-game leg correlation, measured
analysis/depth_accuracy.py  depth chart vs realised participation
analysis/strategies.py      the pre-registered gate and the strategy tests
analysis/build_site.py      renders the JSON registers into HTML (deterministic)
analysis/verify.py          216 checks: every rendered number against its source file
```

`.github/workflows/fetch-nflverse-data.yml` downloads the nflverse releases and commits compact
aggregates; it exists because the development sandbox cannot reach
`release-assets.githubusercontent.com` while Actions runners can.

`.github/workflows/verify-data.yml` re-runs every measurement, rebuilds the site, verifies all 216
checks, runs the repository's own checkers, and fails if a rebuild differs from what is committed.

## Bugs verification caught

Nine, and each was found because a **number was implausible**, not because a test was written for it
in advance. The full table is in `../COORDINATION.md`. The most instructive:

- Home cover rate came out at **56.93 %** — impossible, so the sign convention was wrong.
- Injury play rate came out at **100 %** — snap counts list only participants, so the denominator was
  poisoned by survivorship bias.
- Depth agreement came out at **0 %** — `football_name` holds only the given name.
- Strategy ROI came out at **+148 %** — a spread bet was priced off the moneyline.
- CI could not reproduce `strategies.json` — the analysis silently depended on a gitignored directory.

## Run locally

```bash
cd signal
python3 analysis/verify.py      # 216 verification checks
python3 analysis/build_site.py  # rebuild the pages (deterministic)
cd .. && python3 tools/check_links.py
```
