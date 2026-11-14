# Source & verification ledger

Every number that appears anywhere in this project must be traceable to a row in
this file. If a value is not in here, it is blank on the site and listed on the
**Flagged for Review** page.

**Snapshot time:** 2026-11-14 03:00 UTC (2026 season, Week 10).
**Rule applied:** a value is `verified: true` only when it was read directly from
a T1/T2 source during this session. Repository facts were read programmatically
(no transcription), so they cannot drift.

---

## 1. What was actually reachable (and what was not)

The build environment's outbound network allow-list is limited to
`github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`,
`pypi.org`, `files.pythonhosted.org`. Consequences, measured rather than assumed:

| Host | Direct HTTP from build shell | HTTP via page-fetch tool | Used for |
|---|---|---|---|
| `api.github.com` | ✅ 200 | ✅ | repo facts, dataset downloads |
| `github.com` | ✅ 200 | ✅ | source links |
| `raw.githubusercontent.com` | ❌ `000` | n/a | **not used** |
| `objects.githubusercontent.com` (GitHub *release asset* redirect target) | ❌ `000` | n/a | **blocks nflverse release assets** |
| `www.nfl.com` | ❌ `000` | ✅ | injury report, standings, news, rosters |
| `www.pro-football-reference.com` | ❌ `000` | ✅ | team offense/defense tables |
| `www.espn.com` | ❌ `000` | ✅ (partial render) | schedule cross-check |
| sportsbooks / odds APIs | ❌ | ❌ | **no market prices obtainable** |

This is why:
* bulk player-level statistics (`player_stats`, `snap_counts`, `depth_charts`)
  could **not** be downloaded — they are published only as release assets;
* **no sportsbook price** is quoted anywhere in this project;
* every market number shown comes from the nflverse closing-line tables, which
  are themselves a historical aggregation, and is labelled as such.

---

## 2. Repository facts (verified via `gh`/`git`)

| Fact | Value | Command / source |
|---|---|---|
| Default branch | `main` | `gh api repos/sassnarep3-star/FL2` |
| Base commit of this session | `0f3d2f9e87f44409fa02fd94aa5d474f58b300a5` | `git log` |
| Branches present at start | `main`, `arena/4a77261b-fl2` | `git ls-remote origin` |
| Pages enabled | yes, `build_type: legacy`, source `main:/`, status `built` | `gh api repos/sassnarep3-star/FL2/pages` |
| Pages URL | https://sassnarep3-star.github.io/FL2/ | same |
| Files at base commit | `README.md` only (5 bytes, content `# FL2`) | `find`/`cat` |

Source: <https://github.com/sassnarep3-star/FL2>

---

## 3. Historical dataset used for all backtesting

| File | Rows | SHA-256 recorded in | Human-openable source |
|---|---|---|---|
| `games.csv` | 7,548 (1999–2026) | `data/manifest.json` | <https://github.com/nflverse/nfldata/blob/master/data/games.csv> |
| `closing_lines.csv` | ~10k line records (2006–2013 seasons present) | `data/manifest.json` | <https://github.com/nflverse/nfldata/blob/master/data/closing_lines.csv> |
| `initial_lines.csv` | 1,088 (2021 only) | `data/manifest.json` | <https://github.com/nflverse/nfldata/blob/master/data/initial_lines.csv> |
| `standings.csv` | — | `data/manifest.json` | <https://github.com/nflverse/nfldata/blob/master/data/standings.csv> |

**Column-convention verification (this is the highest-risk item in the project).**
`spread_line` is *not* a handicap; it is the **expected home margin**. Verified
against the sign of the moneyline on real rows:

| Season/week | Matchup | `home_moneyline` | `spread_line` | Reading |
|---|---|---|---|---|
| 2025 wk1 | DAL @ PHI | −425 | **+8.5** | home favourite priced −425, expected +8.5 margin ✅ |
| 2025 wk1 | KC @ LAC | +145 | **−3.0** | home underdog priced +145, expected −3.0 margin ✅ |
| 2025 wk1 | ARI @ NO | +220 | **−6.0** | home underdog, expected −6.0 ✅ |

Consequences encoded in `engine/run_backtest.py::self_check`, which **asserts**
these invariants before any modelling runs:

* home favourites must have `spread_line > 0`;
* home underdogs must have `spread_line < 0`;
* the naive home cover rate must lie in (0.44, 0.56).

Measured values (2011–2026, n = 4,055): home cover **0.4752**, home win
**0.5499**, over **0.4880**, home margin mean **+1.954** vs mean `spread_line`
**+1.918**. All plausible; a sign error would have produced absurd cover rates.

> **Irregularity corrected during this session.** The first implementation of the
> cover test used `home_margin + spread_line > 0`, which produced a 77% "divisional
> home underdog cover rate" — impossible. The sign was fixed and the assertion
> above was added so it cannot silently regress. It is logged on the Flagged for
> Review page as resolved.

---

## 4. 2026 Week 10 — official injury report

**Source:** <https://www.nfl.com/injuries/> (Official NFL injury report, Week 10
of the 2026 season; page title confirms "Official Latest NFL Injury Report for
Players — Week 10 of the 2026 Season").

Read verbatim: player, position, injury, practice status, game status.
Captured into `data/week10_lineups.json` → `injury_rows`
(76 rows: 66 Out, 10 Doubtful). Questionable counts per team are counted from the
same page (`QUESTIONABLE` map in `engine/build_week10.py`).

Rows are **not** paraphrased; positions and status strings match the page.

| Team | Player | Pos | Injury | Practice | Status |
|---|---|---|---|---|---|
| WAS | Lucas Patrick | C | Concussion | DNP | **Out** |
| WAS | Colson Yankoff | TE | Knee | DNP | **Out** |
| NE | Ben Brown | C | Knee | DNP | **Out** |
| NE | Carlton Davis III | CB | Knee | DNP | **Out** |
| NE | TreVeyon Henderson | RB | Illness | DNP | **Out** |
| DET | Kerby Joseph | S | Knee | DNP | **Out** |
| DET | Cade Mays | C | Ankle | DNP | **Out** |
| DET | D.J. Reed | CB | Hip | DNP | **Out** |
| KC | Jaylon Moore | T | Ankle | DNP | **Out** |
| KC | Omarr Norman-Lott | DT | Knee | Limited | **Out** |
| KC | Peter Woods | DT | Neck | DNP | **Out** |
| ATL | Zachariah Branch | WR | Hamstring | DNP | **Out** |
| ATL | Divine Deablo | LB | Forearm | DNP | Doubtful |
| MIN | Blake Cashman | LB | Concussion | Limited | **Out** |
| MIN | T.J. Hockenson | TE | Wrist, Chest | DNP | **Out** |
| MIN | Tyrion Ingram-Dawkins | DT | Ankle | DNP | **Out** |
| MIN | Jauan Jennings | WR | Calf | DNP | **Out** |
| MIN | Kyler Murray | QB | Hamstring | DNP | **Out** |
| GB | Josh Jacobs | RB | Finger | DNP | **Out** |
| GB | Micah Parsons | LB | Knee, Illness | Limited | **Out** |
| GB | Sean Rhyan | C | Ankle | DNP | **Out** |
| GB | Josh Whyle | TE | Concussion | DNP | **Out** |
| GB | Zaire Franklin | LB | Shin | DNP | Doubtful |
| JAX | Jessie Bates | S | Not injury related – resting player | Limited | **Out** |
| JAX | Jordan Davis | DT | Not injury related – resting player | Limited | **Out** |
| JAX | BJ Green II | DE | Forearm | Full | **Out** |
| TEN | Cody Barton | LB | Concussion | DNP | **Out** |
| TEN | Anthony Hill Jr. | LB | Neck | DNP | **Out** |
| TEN | Peter Skoronski | G | Hamstring | DNP | **Out** |
| TEN | Carnell Tate | WR | Shoulder | DNP | **Out** |
| TEN | Tommy Townsend | P | Knee, Achilles | DNP | **Out** |
| BUF | Spencer Brown | T | Ankle | DNP | Doubtful |
| NYJ | Trevin Wallace | LB | Groin | DNP | **Out** |
| MIA | Aaron Brewer | C | Concussion | DNP | **Out** |
| MIA | Jared Wayne | WR | Quadricep | DNP | **Out** |
| MIA | Chris Bell | WR | Knee | DNP | Doubtful |
| IND | Mo Alie-Cox | TE | Groin | DNP | **Out** |
| IND | Jaylon Carlies | LB | Neck | DNP | **Out** |
| IND | Akeem Davis-Gaither | LB | Knee | DNP | **Out** |
| IND | Luke Rhodes | LS | Hamstring | DNP | **Out** |
| IND | Jerry Tillery | DT | Calf | DNP | **Out** |
| IND | Jalen Travis | T | Knee | DNP | **Out** |
| CAR | Bobby Okereke | LB | Foot | DNP | **Out** |
| CAR | Jonathon Brooks | RB | Groin | Limited | Doubtful |
| CAR | Mike Jackson | CB | Groin | Limited | Doubtful |
| NO | CJ Donaldson | RB | Shoulder | DNP | **Out** |
| NO | Taliese Fuaga | T | Knee | DNP | **Out** |
| NO | Erik McCoy | C | Biceps | DNP | **Out** |
| NO | Christen Miller | DT | Knee | DNP | **Out** |
| HOU | Azeez Al-Shaair | LB | Groin, NIR – personal matter | DNP | **Out** |
| HOU | Marvin Harrison Jr. | WR | Hamstring | DNP | **Out** |
| HOU | Danielle Hunter | DE | Hamstring | DNP | **Out** |
| HOU | Brevin Jordan | TE | Finger, Foot | DNP | **Out** |
| HOU | Keylan Rutledge | G | Neck, Shoulder | DNP | **Out** |
| CLE | Michael Burton | FB | Calf | DNP | **Out** |
| CLE | Ronnie Hickman Jr. | S | Concussion | DNP | **Out** |
| LAR | Steve Avila | G | Hamstring | DNP | **Out** |
| LAR | Terrance Ferguson | TE | Ankle, Hamstring | DNP | **Out** |
| ARI | Hjalte Froholdt | C | Concussion | DNP | **Out** |
| ARI | Jon Gaines II | G | Ankle | DNP | **Out** |
| ARI | Zachary Carter | DT | Knee | Limited | **Out** |
| SEA | Charles Cross | T | Ankle | DNP | **Out** |
| SEA | Sam Darnold | QB | Ribs, Quadricep | DNP | **Out** |
| SEA | Quenton Nelson | G | Knee | DNP | **Out** |
| SEA | Leonard Williams | DT | Stinger | DNP | **Out** |
| SF | Mike Evans | WR | Achilles | DNP | **Out** |
| DAL | Donovan Ezeiruaku | LB | Ankle | DNP | **Out** |
| DAL | Jake Ferguson | TE | Knee, Ankle | DNP | **Out** |
| DAL | Tyler Goodson | RB | Ankle, Knee | DNP | **Out** |
| DAL | P.J. Locke | S | Concussion | DNP | **Out** |
| DAL | Jonathan Mingo | WR | Ankle | DNP | **Out** |
| DAL | Juanyeh Thomas | S | Hamstring | DNP | Doubtful |
| CIN | Kyle Dugger | S | Quadricep | DNP | **Out** |
| CIN | Jalen Davis | CB | Hamstring | Full | Doubtful |
| CIN | Andrei Iosivas | WR | Thumb | Full | Doubtful |
| CIN | Brian Parker II | G | Knee | Full | Doubtful |

Teams with **no Week 10 game** (verified: absent from the Week 10 injury report):
**PHI, TB, DEN, CHI**. Teams with no Out/Doubtful rows: **NYG, LV, PIT, LAC, BAL**.

---

## 5. Quarterback availability — official statements only

| Team | Week 10 starter | Official statement | Source |
|---|---|---|---|
| ARI | **Carson Beck** | "Carson Beck will start Sunday's game against the Rams… first career start in the NFL after he was selected in the third round of the 2026 draft." Kyler Murray listed **Out** (hamstring). | <https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-wednesday-nov-11> |
| CLE | **Deshaun Watson** | "Deshaun Watson will start Sunday against the Texans, the team announced." Shedeur Sanders started Week 9. | same |
| MIA | **Kyle McCord** | "Malik Willis was placed on injured reserve Tuesday due to a groin injury. With Willis shelved, second-year quarterback Kyle McCord will fill in, beginning Sunday on the road against the Indianapolis Colts." | <https://www.nfl.com/news/dolphins-place-qb-malik-willis-groin-on-injured-reserve-kyle-mccord-in-line-for-first-start> |
| MIN | **Kirk Cousins** | "QB Kirk Cousins will start Sunday's game against the Packers, head coach Kevin O'Connell announced." | <https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-friday-nov-13> |
| SEA | **Drew Lock** | "Drew Lock has no injury designation and will start Sunday… Jalen Milroe will be Seattle's backup." Sam Darnold ruled **Out** (ribs/quadricep). | <https://www.nfl.com/news/drew-lock-no-injury-designation-seahawks-raiders> |
| BAL | **not stated** | "Lamar Jackson is expected to miss 6-10 weeks after undergoing surgery to repair his broken and dislocated thumb…" The reviewed pages do not name the Week 10 starter → **left blank, flagged**. | <https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-friday-nov-13> |
| LAC | **not stated** | Headline only: "Justin Herbert avoids finger fracture" (Nov 9 roundup). No starter confirmation found → **left blank, flagged**. | <https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-monday-nov-9> |

---

## 6. 2026 standings (nfl.com/standings, REG, retrieved 2026-11-14)

Source: <https://www.nfl.com/standings/>

| Team | W | L | T | PF | PA | Streak |
|---|---|---|---|---|---|---|
| BUF | 7 | 1 | 0 | 256 | 187 | 4W |
| NE | 5 | 4 | 0 | 211 | 207 | 1L |
| NYJ | 2 | 7 | 0 | 182 | 223 | 4L |
| MIA | 1 | 7 | 0 | 126 | 200 | 2L |
| PIT | 6 | 2 | 0 | 180 | 144 | 4W |
| CIN | 6 | 2 | 0 | 240 | 175 | 4W |
| CLE | 5 | 4 | 0 | 161 | 196 | 2L |
| BAL | 4 | 5 | 0 | 189 | 236 | 4L |
| JAX | 6 | 2 | 0 | 229 | 121 | 2W |
| HOU | 3 | 5 | 0 | 209 | 192 | 1W |
| IND | 2 | 7 | 0 | 184 | 249 | 5L |
| TEN | 1 | 7 | 0 | 144 | 199 | 2L |
| DEN | 7 | 2 | 0 | 198 | 186 | 5W |
| KC | 6 | 2 | 0 | 202 | 143 | 1W |
| LV | 4 | 5 | 0 | 238 | 268 | 1L |
| LAC | 0 | 8 | 0 | 121 | 219 | 8L |
| NYG | 5 | 3 | 1 | 203 | 196 | 1L |
| DAL | 4 | 5 | 0 | 246 | 236 | 1W |
| WAS | 3 | 5 | 1 | 196 | 223 | 1W |
| PHI | 2 | 7 | 0 | 148 | 221 | 7L |
| CHI | 7 | 2 | 0 | 241 | 184 | 4W |
| DET | 6 | 2 | 0 | 222 | 189 | 4W |
| MIN | 6 | 2 | 0 | 146 | 116 | 2L |
| GB | 6 | 3 | 0 | 216 | 191 | 2W |
| CAR | 3 | 5 | 0 | 199 | 219 | 3L |
| NO | 3 | 5 | 0 | 185 | 216 | 1W |
| TB | 3 | 6 | 0 | 202 | 178 | 1L |
| ATL | 3 | 6 | 0 | 188 | 223 | 2L |
| LAR | 5 | 4 | 0 | 214 | 181 | 3W |
| ARI | 3 | 6 | 0 | 178 | 255 | 1L |
| SEA | 5 | 4 | 0 | 202 | 162 | 1W |
| SF | 7 | 1 | 0 | 235 | 156 | 1W |

---

## 7. Team defense (Pro-Football-Reference, `opp.htm`, 2026)

Source: <https://www.pro-football-reference.com/years/2026/opp.htm>
Columns used: `G`, `PA` (points allowed), `Yds`, passing `Yds`, rushing `Yds`, `TO`.

| Team | G | PA | Yds | Pass Yds | Rush Yds | TO |
|---|---|---|---|---|---|---|
| MIN | 8 | 116 | 2240 | 1289 | 951 | 13 |
| JAX | 8 | 121 | 2546 | 1832 | 714 | 15 |
| KC | 8 | 143 | 2463 | 1683 | 780 | 11 |
| PIT | 8 | 144 | 2445 | 1774 | 671 | 13 |
| SF | 8 | 156 | 2335 | 1688 | 647 | 12 |
| SEA | 9 | 162 | 2198 | 1396 | 802 | 13 |
| CIN | 8 | 175 | 2839 | 1826 | 1013 | 12 |
| TB | 9 | 178 | 2636 | 1924 | 712 | 21 |
| LAR | 9 | 181 | 2722 | 1788 | 934 | 10 |
| CHI | 9 | 184 | 2798 | 1978 | 820 | 13 |
| DEN | 9 | 186 | 3195 | 2076 | 1119 | 12 |
| BUF | 8 | 187 | 2643 | 1910 | 733 | 12 |
| DET | 8 | 189 | 2840 | 2087 | 753 | 8 |
| GB | 9 | 191 | 2906 | 1925 | 981 | 19 |
| HOU | 8 | 192 | 2709 | 1885 | 824 | 8 |
| NYG | 9 | 196 | 2751 | 1657 | 1094 | 12 |
| CLE | 9 | 196 | 2984 | 1809 | 1175 | 12 |
| TEN | 8 | 199 | 3059 | 2066 | 993 | 11 |
| MIA | 8 | 200 | 2609 | 1715 | 894 | 7 |
| NE | 9 | 207 | 2957 | 2087 | 870 | 8 |
| NO | 8 | 216 | 2964 | 1893 | 1071 | 9 |
| CAR | 8 | 219 | 2759 | 1692 | 1067 | 11 |
| LAC | 8 | 219 | 2746 | 1770 | 976 | 12 |
| PHI | 9 | 221 | 3181 | 2046 | 1135 | 5 |
| NYJ | 9 | 223 | 2932 | 1780 | 1152 | 10 |
| ATL | 9 | 223 | 3121 | 2052 | 1069 | 10 |
| WAS | 9 | 223 | 3137 | 2203 | 934 | 14 |
| BAL | 9 | 236 | 2967 | 2068 | 899 | 9 |
| DAL | 9 | 236 | 3354 | 2027 | 1327 | 8 |
| IND | 9 | 249 | 3256 | 2023 | 1233 | 6 |
| ARI | 9 | 255 | 3036 | 1939 | 1097 | 8 |
| LV | 9 | 268 | 3469 | 2108 | 1361 | 14 |

League context from the same page: **Avg Team 196.6 PA**, average 2,837.4 yds,
average 23.0 points per team per game.

---

## 8. Team offense — points for (source of record: nfl.com/standings)

Source: <https://www.nfl.com/standings/> (`PF`, `PA`). These are the exact values
the projection engine consumes (`pf_per_game`, `pa_per_game`), so the ledger and the
model cannot disagree.

*The PFR season-index `Yds`/`TO` columns were also read, but the two sources
disagree on game counts this week (PFR shows 8-9 games played with a different
split), so only one source is used per column. PFR is used for **defence**
(§7) and nfl.com for **offence** (§8) — each is internally consistent.*

| Rank | Team | G | PF | PF/G | PA | PA/G |
|---|---|---|---|---|---|---|
| 1 | BUF | 8 | 256 | 32.0 | 187 | 23.38 |
| 2 | DAL | 9 | 246 | 27.33 | 236 | 26.22 |
| 3 | CHI | 9 | 241 | 26.78 | 184 | 20.44 |
| 4 | CIN | 8 | 240 | 30.0 | 175 | 21.88 |
| 5 | LV | 9 | 238 | 26.44 | 268 | 29.78 |
| 6 | SF | 8 | 235 | 29.38 | 156 | 19.5 |
| 7 | JAX | 8 | 229 | 28.62 | 121 | 15.12 |
| 8 | DET | 8 | 222 | 27.75 | 189 | 23.62 |
| 9 | GB | 9 | 216 | 24.0 | 191 | 21.22 |
| 10 | LAR | 9 | 214 | 23.78 | 181 | 20.11 |
| 11 | NE | 9 | 211 | 23.44 | 207 | 23.0 |
| 12 | HOU | 8 | 209 | 26.12 | 192 | 24.0 |
| 13 | NYG | 9 | 203 | 22.56 | 196 | 21.78 |
| 14 | KC | 8 | 202 | 25.25 | 143 | 17.88 |
| 15 | SEA | 9 | 202 | 22.44 | 162 | 18.0 |
| 16 | TB | 9 | 202 | 22.44 | 178 | 19.78 |
| 17 | CAR | 8 | 199 | 24.88 | 219 | 27.38 |
| 18 | DEN | 9 | 198 | 22.0 | 186 | 20.67 |
| 19 | WAS | 9 | 196 | 21.78 | 223 | 24.78 |
| 20 | BAL | 9 | 189 | 21.0 | 236 | 26.22 |
| 21 | ATL | 9 | 188 | 20.89 | 223 | 24.78 |
| 22 | NO | 8 | 185 | 23.12 | 216 | 27.0 |
| 23 | IND | 9 | 184 | 20.44 | 249 | 27.67 |
| 24 | NYJ | 9 | 182 | 20.22 | 223 | 24.78 |
| 25 | PIT | 8 | 180 | 22.5 | 144 | 18.0 |
| 26 | ARI | 9 | 178 | 19.78 | 255 | 28.33 |
| 27 | CLE | 9 | 161 | 17.89 | 196 | 21.78 |
| 28 | PHI | 9 | 148 | 16.44 | 221 | 24.56 |
| 29 | MIN | 8 | 146 | 18.25 | 116 | 14.5 |
| 30 | TEN | 8 | 144 | 18.0 | 199 | 24.88 |
| 31 | MIA | 8 | 126 | 15.75 | 200 | 25.0 |
| 32 | LAC | 8 | 121 | 15.12 | 219 | 27.38 |

League check: mean PF/G across the 32 teams = 23.012; mean PA/G = 22.919.

---

## 9. Week 10 schedule

Source: <https://www.nfl.com/injuries/> (date/time/TV headers on the Week 10 page)

| Date (ET) | Time | Away | Home | TV | Note |
|---|---|---|---|---|---|
| Thu 2026-11-12 | 20:15 | WAS | NYG | Prime Video | |
| Sun 2026-11-15 | 09:30 | NE | DET | FOX | Munich |
| Sun 2026-11-15 | 13:00 | KC | ATL | CBS | |
| Sun 2026-11-15 | 13:00 | MIN | GB | FOX | |
| Sun 2026-11-15 | 13:00 | JAX | TEN | FOX | |
| Sun 2026-11-15 | 13:00 | BUF | NYJ | CBS | |
| Sun 2026-11-15 | 13:00 | MIA | IND | CBS | |
| Sun 2026-11-15 | 13:00 | CAR | NO | FOX | |
| Sun 2026-11-15 | 13:00 | HOU | CLE | FOX | |
| Sun 2026-11-15 | 16:05 | LAR | ARI | CBS | |
| Sun 2026-11-15 | 16:05 | SEA | LV | CBS | |
| Sun 2026-11-15 | 16:25 | SF | DAL | FOX | |
| Sun 2026-11-15 | 20:20 | PIT | CIN | NBC | |
| Mon 2026-11-16 | 20:15 | LAC | BAL | ESPN/ABC | |

---

## 10. Deliberately **not** used

| Source type | Why excluded |
|---|---|
| Wikipedia | Not an official source; used only as a cross-check for scoring-rule definitions, never for a table value. |
| ESPN power rankings / projections | Editorial, not measurement. |
| Any sportsbook site | Unreachable, and prices have no official publisher. |
| `raw.githubusercontent.com` mirrors | Unreachable in this environment; using a mirror we could not read would be unverifiable. |
| Model memory | **Never.** No number in this project was produced from recall. |
