# Official-page capture log

Every number in this section traces to one of these reads. The clock time is the time the
fetch was requested; the *page state* is described separately because a cached or stale
render is exactly the failure mode this project has to be able to see.

| requested (UTC) | page | what it gave | state observed |
|---|---|---|---|
| 2026-11-16T01:12Z | https://www.nfl.com/injuries/ | Week 10 club-by-club report, 8 chunks; Lions rows for Kerby Joseph, Cade Mays, D.J. Reed | all three printed **Out** (Knee / Ankle / Hip, DNP), which is the evidence that closes the "blank game-status cell" flag |
| 2026-11-16T01:15Z | https://www.nfl.com/standings/division/2026/REG | W-L-T, PF, PA for all 32 clubs | PIT and CIN printed 6-2 with 180/144 and 240/175, i.e. the 8:20 PM ET game was not yet counted |
| 2026-11-16T01:16Z | https://www.nfl.com/schedules/2026/by-week/week-10 | 12 finals, 1 not-final, 1 upcoming; byes; the Munich label | PIT@CIN printed its kickoff time and no score; LAC@BAL listed as Monday upcoming |
| 2026-11-16T01:19Z | https://www.nfl.com/schedules/2026/by-week/week-11 | 13 games, kickoff times and broadcasters, 6 byes, the Mexico City label for MIN@SF | forward slate, unplayed |
| 2026-11-16T01:22Z | https://www.nfl.com/games/steelers-at-bengals-2026-reg-10 | Game Info: Location Cincinnati OH, Stadium Paycor Stadium; game-day A/Q/D/O markers for 8 named players | venue transcription pattern for R23; also the only per-player game-day status seen in a game centre at capture |
| 2026-11-16T01:26Z | https://www.nfl.com/news/2026-nfl-schedule-release-complete-slate-of-week-1-games | the league's dated schedule-release article: Wed Sep 9 kickoff at Lumen Field, SF@LA in Melbourne, Week 1 pairings | supports R24 |

## Deltas (what the next capture must publish)

The brief asks for a delta and never a level. A delta needs two captures of the *same*
page. There is one capture of each here, so **no delta is published** — R21/R55 stay
PARTIAL in the readiness table rather than pretending otherwise. The snapshot workflow
`fl2-lines-snapshot.yml` is the mechanism that produces capture #2 and #3.

## Not captured, deliberately

* No operator odds page exists on nfl.com (`/odds/` returns 404), so no market price in
  this repository comes from an official source. See `fl2-lines/data/prices/policy.md`.
* No league depth chart exists (`/teams/<club>/depth-chart` returns 404), so no depth
  claim here is labelled official.
