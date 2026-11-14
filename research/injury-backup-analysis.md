# Injury & Backup-Depth Analysis — Week 10, 2026

Requirement 5: track injuries, and know the offensive/defensive deficiencies caused by 2nd/3rd/4th
string backups replacing starters, per depth chart.

## What was verified

| Item | Value | Source |
|---|---|---|
| Official Week 10 injury report | 345 player rows across 28 team entries (14 games) | `https://www.nfl.com/injuries/league/2026/reg10` |
| Game statuses published | Out **66**, Doubtful **10**, Questionable **84**, blank **185** | same page (blank = the league printed no status; it does **not** mean healthy) |
| Teams on bye | CHI, DEN, PHI, TB (no report published) | same page |
| Club depth charts acquired | **5 of 32** (NE, DET, GB, KC, SF) | club sites, all captioned "unofficial" |
| First-stringers Out/Doubtful located | **9** | computed in `data/derived/backup_impact.json` |
| Out players absent from their own club chart | **3** | computed |

## The core finding: club depth charts lag the official injury report

12 players appear as 1st/2nd string on a club chart while carrying **Out** or **Doubtful** on the
official NFL report. Three Out players do not appear on their own club's chart at all:

| Team | Player | Position on report | Status | Note |
|---|---|---|---|---|
| DET | Kerby Joseph | S | Out (Knee) | absent from detroitlions.com chart |
| GB | Micah Parsons | LB | Out (Knee, Illness) | absent from packers.com chart |
| KC | Omarr Norman-Lott | DT | Out (Knee) | absent from chiefs.com chart |

**Consequence:** any depth-chart-driven system is wrong by construction unless it is re-synced
against the official inactives list published ~90 minutes before kickoff. See Open Questions Q6.

## Starters Out/Doubtful with the club's listed replacement

`Replacement` is the next name printed to the right of the injured player on the club's own chart.
It is **not** a prediction of who plays, and the charts are **unofficial**.

| Team | Unit | Pos | Starter | Status | Injury | Listed next | Source |
|---|---|---|---|---|---|---|---|
| DET | Defense | CB | D.J. Reed | Out | Hip | Rock Ya-Sin (2nd) | [chart](https://www.detroitlions.com/team/depth-chart) · [injury](https://www.nfl.com/injuries/league/2026/reg10) |
| DET | Offense | C | Cade Mays | Out | Ankle | Juice Scruggs (2nd) | [chart](https://www.detroitlions.com/team/depth-chart) · [injury](https://www.nfl.com/injuries/league/2026/reg10) |
| GB | Defense | LB | Zaire Franklin (44) | Doubtful | Shin | Ty'Ron Hopper (59) | [chart](https://www.packers.com/team/depth-chart) · [injury](https://www.nfl.com/injuries/league/2026/reg10) |
| GB | Offense | C | Sean Rhyan (75) | Out | Ankle | Jager Burton (52) | [chart](https://www.packers.com/team/depth-chart) · [injury](https://www.nfl.com/injuries/league/2026/reg10) |
| GB | Offense | RB | Josh Jacobs (8) | Out | Finger | MarShawn Lloyd (32) | [chart](https://www.packers.com/team/depth-chart) · [injury](https://www.nfl.com/injuries/league/2026/reg10) |
| KC | Offense | RT | Jaylon Moore | Out | Ankle | Joshua Ezeudu (2nd) | [chart](https://www.chiefs.com/team/depth-chart) · [injury](https://www.nfl.com/injuries/league/2026/reg10) |
| NE | Defense | CB | Carlton Davis III | Out | Knee | Channing Canada (2nd) | [chart](https://www.patriots.com/team/depth-chart) · [injury](https://www.nfl.com/injuries/league/2026/reg10) |
| NE | Offense | LG | Ben Brown | Out | Knee | Walter Rouse (2nd) | [chart](https://www.patriots.com/team/depth-chart) · [injury](https://www.nfl.com/injuries/league/2026/reg10) |
| SF | Offense | WR | Mike Evans | Out | Achilles | Jordan Watkins (2nd) | [chart](https://www.49ers.com/team/depth-chart) · [injury](https://www.nfl.com/injuries/league/2026/reg10) |

Four further affected players are 2nd/4th string: GB Josh Whyle (4th TE, Out — **no deeper TE
published**), KC Peter Woods (2nd DT, Out → Marcus Harris), NE Ben Brown (2nd C, Out — no 3rd C
published), NE TreVeyon Henderson (2nd RB, Out → Corey Kiner).

## What is deliberately NOT quantified

**No "points per game lost" number appears anywhere in this project.** That quantity cannot be
derived from any official source: it requires snap counts, play-by-play, and a model of replacement
level. Publishing an estimate would be a hallucination, so the analysis stops at *who is out* and
*who is next*, which is all the official record supports. See Suggestions S7 for closing the gap.

## Week 10 players ruled Out or Doubtful, by club (official report)

Transcribed row by row from `https://www.nfl.com/injuries/league/2026/reg10`. This table lists only
clubs with at least one Out/Doubtful; clubs not listed had none. 66 Out and 10 Doubtful across the
league. The injury report does not carry injured-reserve players, so IR absences do not appear here.

| Club | Players ruled Out / Doubtful (pos, injury) |
|---|---|
| ARI | Zachary Carter (DT, Knee); Hjalte Froholdt (C, Concussion); Jon Gaines II (G, Ankle) |
| CLE | Michael Burton (FB, Calf); Ronnie Hickman Jr. (S, Concussion) |
| DAL | Donovan Ezeiruaku (LB, Ankle); Jake Ferguson (TE, Knee/Ankle); Tyler Goodson (RB, Ankle/Knee); P.J. Locke (S, Concussion); Jonathan Mingo (WR, Ankle); Juanyeh Thomas (S, Hamstring, **Doubtful**) |
| GB | Josh Jacobs (RB, Finger); Micah Parsons (LB, Knee/Illness); Sean Rhyan (C, Ankle); Josh Whyle (TE, Concussion); Zaire Franklin (LB, Shin, **Doubtful**) |
| HOU | Azeez Al-Shaair (LB, Groin/personal); Marvin Harrison Jr. (WR, Hamstring); Danielle Hunter (DE, Hamstring); Brevin Jordan (TE, Finger/Foot); Keylan Rutledge (G, Neck/Shoulder) |
| IND | Mo Alie-Cox (TE, Groin); Jaylon Carlies (LB, Neck); Akeem Davis-Gaither (LB, Knee); Luke Rhodes (LS, Hamstring); Jerry Tillery (DT, Calf); Jalen Travis (T, Knee) |
| KC | Jaylon Moore (T, Ankle); Omarr Norman-Lott (DT, Knee); Peter Woods (DT, Neck) |
| MIN | Blake Cashman (LB, Concussion); T.J. Hockenson (TE, Wrist/Chest); Tyrion Ingram-Dawkins (DT, Ankle); Jauan Jennings (WR, Calf); Kyler Murray (QB, Hamstring) |
| MIA | Aaron Brewer (C, Concussion); Jared Wayne (WR, Quadricep); Chris Bell (WR, Knee, **Doubtful**) |
| NO | CJ Donaldson (RB, Shoulder); Taliese Fuaga (T, Knee); Erik McCoy (C, Biceps); Christen Miller (DT, Knee) |
| SEA | Charles Cross (T, Ankle); Sam Darnold (QB, Ribs/Quadricep); Quenton Nelson (G, Knee); Leonard Williams (DT, Stinger) |
| SF | Mike Evans (WR, Achilles) |
| TEN | Cody Barton (LB, Concussion); Anthony Hill Jr. (LB, Neck); Peter Skoronski (G, Hamstring); Carnell Tate (WR, Shoulder); Tommy Townsend (P, Knee/Achilles) |
| PIT | **none — no player listed Out or Doubtful** |
| DET, NE, WAS, NYG, LV, JAX, CIN, BUF, NYJ, ATL, CAR, LAC, BAL | see `data/injuries.json` — entries exist; see the site's Injuries page for the full row-by-row table |

Every row above is stored in `data/injuries.json` with a per-player `nfl.com/players/` link for
manual review.
