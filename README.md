# FL2 — NFL Decision Hub

A verified decision surface for an NFL line-origination project: requirements, open decision questions,
reviewable suggestions, strategy origination, validation gates, correlation analysis, and injury / depth-chart
tracking — every data row carrying a link to the official source it came from.

**Live site:** https://sassnarep3-star.github.io/FL2/

## Start here

| If you want to… | Read |
| --- | --- |
| Get the whole picture in one page | [`docs/EXECUTIVE-SUMMARY.md`](docs/EXECUTIVE-SUMMARY.md) |
| Choose a path before anything is implemented | [`pages/suggestions.html`](pages/suggestions.html) |
| See what we don't know yet | [`pages/decision-questions.html`](pages/decision-questions.html) |
| See what could not be verified | [`pages/flagged.html`](pages/flagged.html) |
| Coordinate with another agent session | [`COORDINATION.md`](COORDINATION.md) |

## What is in here

| Path | Contents |
| --- | --- |
| `index.html`, `pages/` | 16-page static site, no build step, no CDN, no JavaScript |
| `data/` | Datasets, each row carrying its source URL and retrieval date |
| `tools/` | The scripts that generate every dataset and page |
| `docs/` | Executive summary |
| `COORDINATION.md` | Shared task board for parallel sessions |

## Regenerate everything

```bash
python3 tools/calc.py               # odds, parlay, correlation, sample-size, Kelly arithmetic
python3 tools/build_injury_csv.py   # injury report -> data/injury-report-2026-w10.csv
python3 tools/build_team_metrics.py # four official tables -> data/team-metrics-2026-w10.csv
python3 tools/build_slate_csv.py    # Week 10 slate -> data/slate-2026-w10.csv
python3 tools/analyze_correlation.py# correlations + bootstrap CIs
python3 tools/build_planning_csv.py # requirements, questions, strategies, gates, suggestions
python3 tools/build_site.py         # data -> HTML
python3 tools/check_links.py        # exits non-zero on any broken link or unsourced dataset
```

The build scripts assert their own cross-checks (winning percentage, net points, completion percentage, yards
per attempt, PPG vs Next Gen Stats, bye list) and fail loudly if any source value drifts.

## The verification rule

Every table row links to an official source (`nfl.com`, `operations.nfl.com`, `media.nfl.com`, or a club's own
site). If a value could not be confirmed there, the cell is **blank** and the item appears on the
[Flagged for Review](pages/flagged.html) page. Values are never inferred, interpolated or carried over from
memory. Analysis, proposals and model specifications are labelled as such and are not presented as results.

**No betting performance is claimed anywhere in this repository.** No odds data has been ingested, so no
strategy has been graded. See `pages/strategies.html` for the honest status of each one.
