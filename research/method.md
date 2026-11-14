# Method & Verification

## How the data was gathered

Everything on this site was read off official pages and transcribed. No value was inferred,
interpolated, or "filled in from context".

1. **Fetch.** Pages were retrieved with a browser-style page fetcher. Plain `curl` from the build
   sandbox fails (`OpenSSL SSL_connect: SSL_ERROR_SYSCALL`) because outbound access is limited to
   `github.com`, `registry.npmjs.org` and `pypi.org`. Every page actually used is listed on the
   [Sources](sources.html) page.
2. **Transcribe into JSON, immediately.** A fetched page is not persisted, so anything not written to
   `data/` in the same session is lost. Every data file has a `meta` block recording the source URL,
   the retrieval date, and the known caveats.
3. **Reconcile against a second official page.** Where a table's structure was ambiguous, the values
   were checked against an official page that *does* label its columns, and only published if the
   arithmetic reproduced the published figure.
4. **Replay.** The 137 games were replayed to regenerate the standings, and the result was compared
   to the official standings page.

## Verification performed

| Check | Method | Result | Source |
|---|---|---|
| Standings replay | Replay all 137 games in `data/games.json`; compare W-L-T, PF, PA to `data/standings.json` | **32/32 teams match exactly** | [standings](https://www.nfl.com/standings/division/2026/REG) |
| Game-log sums | Sum Drake Maye's per-game log; compare to his row on the official passing leaderboard | 178 Cmp, 272 Att, 2,282 Yds, 18 TD, 11 INT — **exact match** | [Maye log](https://www.nfl.com/players/drake-maye/stats/logs/2026/) · [leaderboard](https://www.nfl.com/stats/player-stats/category/passing/2026/reg/all/passingyards/desc) |
| Passing column labels | Cmp÷Att and Yds÷Att per team vs the published Cmp% / Y/A | reproduced for every team; SF verified as 163/236 = 69.07 → 69.1 published, 1980/236 = 8.39 → 8.4 published | [team stats](https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all) |
| Rushing column labels | Read the header row that the defense/rushing page *does* render | headers taken verbatim: Att, Rush Yds, YPC, TD, 20+, 40+, Lng, Rush 1st, Rush 1st%, Rush FUM | [defense rushing](https://www.nfl.com/stats/team-stats/defense/rushing/2026/reg/all) |
| No-look-ahead | Walk-forward harness refits at each week boundary from strictly earlier weeks; the training buffer is appended **after** each prediction | 32 week-1 and week-2 games correctly excluded as ungradeable | [by-week pages](https://www.nfl.com/schedules/2026/by-week/week-1) |
| Injury ↔ depth-chart cross-check | Intersect Out/Doubtful statuses with club charts | 12 conflicts and 3 missing players found (see Backup impact) | [injury report](https://www.nfl.com/injuries/league/2026/reg10) |
| Site link check | `tools/check_links.py` parses every built page | internal links verified; external URLs enumerated for manual review | [this repo](https://github.com/sassnarep3-star/FL2) |

## What counts as "verified" here

A value is published as verified only if it can be pointed at on an official page. Specifically:

* It was transcribed from an NFL.com (or, for depth charts, club) page **and** carries that URL.
* Or it is pure arithmetic on such values, in which case the page says so explicitly
  (all of `data/derived/analytics.json` is in this category).

If a figure cannot be traced to an official page, it is **not published**. The clearest example:
three official stat tables (offense/scoring, defense/scoring, defense/downs) rendered without header
rows, so their columns could not be identified and **the tables were withheld entirely** rather than
labelled by plausibility.

## Blank cells

A blank cell (`—`) on this site means one of exactly three things:

1. The source published no value for that field (very common on the injury report, where 185 of 345
   player rows carry no game status).
2. The game had not been played at retrieval time (13 of 14 Week 10 games).
3. The value exists but could not be confirmed, so it was withheld.

A blank injury status is **not** a statement that the player is healthy.

## Known limitations

* **No odds data.** A betting edge cannot be computed without market prices; none were reachable.
  Everything published is a probability or a benchmark, never an edge.
* **5 of 32 depth charts.** Requirement 5 is only partially satisfied and says so.
* **2 clubs, 5 players of game logs.** Prop correlations are illustrative; every confidence interval
  crosses zero.
* **One season, ten weeks.** 137 games is a small sample for everything except describing 2026 itself.

## Reproducing

```bash
python3 tools/analytics.py     # recomputes data/derived/analytics.json
python3 tools/backup_impact.py # recomputes data/derived/backup_impact.json
python3 tools/build_signals_site.py    # rebuilds fl2-signals/
python3 tools/check_signals_links.py  # verifies internal links, lists external URLs
```

All four use the Python standard library only. There is no network access and no dependency install.
