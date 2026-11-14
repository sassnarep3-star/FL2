# FL2

NFL lines, signals, and strategy research — collecting, organizing, and analyzing a full list of
requirements for originating NFL lines, with a verified-data foundation and a decision-support
documentation set.

**Live site:** https://sassnarep3-star.github.io/FL2/

## What this project does

- **Originate NFL lines** — research and develop strategies for generating useful betting signals.
- **Strategy competition** — a leaderboard that rewards top-performing strategies across single bets,
  parlays, and player-prop combinations. Every strategy must pass validation gates.
- **Correlation controls** — correlation values between signals are determined before combos are built.
- **Luck removal** — strategies are scored with skill-based metrics, not raw win rate.
- **Injury & depth tracking** — tracks injuries and deficiencies in offenses and defenses, including
  situations where 2nd-, 3rd-, or 4th-string backups must replace starters.
- **Decision support** — an executive summary, a questions/answers register, and a suggestions section
  so a reviewer can choose the best path before any change is implemented.

## Site structure

| Page | Purpose |
| --- | --- |
| `index.html` | Dashboard landing page with verified snapshot and navigation |
| `executive-summary.html` | Executive summary of the project state |
| `repo-review.html` | Line-by-line repository review with evidence links |
| `questions-answers.html` | Questions, information, and answers needed before decisions |
| `suggestions.html` | Suggestions section — review and choose a path before implementing |
| `strategies.html` | Signal strategy design, validation gates, correlation, luck removal |
| `leaderboard.html` | Strategy competition rules and ranking table |
| `injuries.html` | Verified Week 10 injury report and depth-deficiency tracking |
| `standings.html` | Verified 2026 standings (all 32 teams) |
| `schedule.html` | Verified Week 10 schedule |
| `flagged-review.html` | Irregularities and unverified items with source links |
| `verification.html` | Verification method, official sources, and scope |

## Data & verification

- Verified data records live in `data/verified/*.json`; each table row on the site carries a link to the
  official source where its value was verified.
- **Rule:** if a value cannot be confirmed from an official source, it is left blank and flagged on the
  Flagged for Review page. Nothing is inferred.
- Fetch and verification log: `data/verified/fetch-log.md`.
- Strategy designs, gate thresholds, and leaderboard rules are proposals pending review in the
  Suggestions section — they are labeled as such and not published as fact.

## Coordination

Multi-session coordination uses the task board in [COORDINATION.md](COORDINATION.md): task status,
ownership, claims, verification records, and the final integration log.

## GitHub Pages

GitHub Pages is enabled with source `main / /`. The site is static HTML/CSS/JS with no build step, so
pushing to `main` publishes automatically.
