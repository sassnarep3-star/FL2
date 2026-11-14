# Suggestions — Reviewer's choice register

**Nothing on this page has been implemented.** Each suggestion is presented with mutually exclusive
paths, the cost/evidence for each, and a recommendation. The reviewer picks a path; only then is it
built. This is the deliverable for requirement 2.

Site-improvement suggestions are grouped first (S1–S4, about this site), then
project-direction suggestions (S5–S8, about the betting-signal work).

---

## S1. Where should the "unverified" contract live?

*Context:* requirement 8 says every table row needs an official source link and unconfirmable values
must stay blank and flagged. Right now that contract is enforced in the site builder.

| Path | What it means | Cost | Risk |
|------|---------------|------|------|
| **A. Keep enforcement in `tools/build_site.py`** (current) | The builder refuses to render a table without a source cell; blank renders as `—` | Zero; already works | Contract lives in code, invisible to a reader |
| **B. Add a CI check** | A GitHub Action re-runs `tools/build_site.py` + `tools/check_links.py` and fails the build if any table row lacks a source | ~20 lines of YAML | Adds a workflow file to the repo |
| **C. Publish the contract as a data schema** | A JSON Schema per data file, validated in CI | Higher; needs schema authoring | More moving parts than this project needs |

**Recommendation: B.** It is the smallest change that turns a convention into an enforcement, and it
also catches a broken Pages build before merge — which requirement 10 explicitly demands.

---

## S2. How should the site present 137 games without a wall of numbers?

| Path | Meaning | Notes |
|------|---------|-------|
| **A. One long sortable table** (current) | All 137 rows on one page, week headings | Simplest; page is tall but every row keeps its source link |
| **B. Week-by-week subpages** | 10 pages, one per week | Cleaner pages, 10× the navigation |
| **C. Filter box + pagination** | Client-side JS filter by team/week | Best UX, adds JS and makes "view source" dependent on script |

**Recommendation: A for now, revisit if a second season is added.** With ~270 games/season the page
stays tolerable; JS filtering would break the "every row is auditable in the HTML" property.

---

## S3. Should the site auto-refresh, or stay frozen at retrieval time?

| Path | Meaning |
|------|---------|
| **A. Frozen snapshot** (current) | Every page prints "retrieved 2026-11-14"; numbers never silently change |
| **B. Scheduled rebuild** | A nightly Action re-fetches NFL.com and rebuilds `docs/` |

**Recommendation: A, with B as an additive later step.** B requires the fetcher to run inside GitHub
Actions (network reachable there, unlike this sandbox), and it introduces the risk of a silent data
change invalidating the analysis. If B is adopted, every page must print the build timestamp —
already the case.

---

## S4. Navigation depth

| Path | Meaning |
|------|---------|
| **A. Flat 13-page nav** (current) | Every page one click away |
| **B. Grouped nav** (Data / Analysis / Governance) | Fewer top-level items, two clicks |

**Recommendation: A** at 13 pages. Switch to B only past ~20 pages.

---

## S5. What should the project do about having no market odds?

*Context:* the single biggest blocker (see Open Questions Q1).

| Path | Meaning | Cost | Result |
|------|---------|------|--------|
| **A. Stay probability-only** (current) | Publish probabilities, gates, and sample-size math; publish **no** line | Zero | Honest but no "proprietary line" |
| **B. Human-supplied closing lines** | Reviewer commits a CSV of closing spreads/totals for Weeks 1–10 | One file from the reviewer | Unlocks real edge measurement immediately |
| **C. Paid odds API key** | Repo secret + Actions fetch | Money + setup | Automated, ongoing |

**Recommendation: B.** It is one file, it is free, and it converts every gate from theoretical to
measurable in a single afternoon. **This is the highest-leverage open decision in the project.**

---

## S6. How should the leaderboard be scored, given the sample-size arithmetic?

*Context:* at −110 the break-even rate is 0.5238. Detecting a 55% bettor at α=.05/80% power needs
**2,243 bets** — about 11 seasons at 200 bets/season.

| Path | Meaning | Notes |
|------|---------|-------|
| **A. Season leaderboard on raw win rate** | Normal, intuitive | **Statistically meaningless** — a season cannot separate 55% from luck |
| **B. Leaderboard on log-loss / Brier vs the market price** | Proper scoring rule | Far more efficient statistically; needs Path B of S5 |
| **C. No leaderboard until n ≥ 719 per strategy** | Publish only when an effect is detectable at 57% | Slowest, but never rewards luck |

**Recommendation: B if S5=B, otherwise C.** Explicitly **reject A** — publishing a leaderboard whose
winner is chosen by variance is the exact "luck" the requirements ask to remove.

---

## S7. What to do about the 27 missing depth charts?

| Path | Meaning | Cost |
|------|---------|------|
| **A. Leave them `not acquired`** (current) | 27 rows in the registry say so explicitly | Zero; honest |
| **B. Fetch all 27 club sites** | Each `https://www.<club>.com/team/depth-chart` is one fetch | 27 fetches; all still "unofficial" |
| **C. Wait for official inactives on game day** | Authoritative, but only fresh | Recurring effort |

**Recommendation: B, then C.** B closes the coverage gap (and the URL pattern is already verified on
5 clubs); C is the only authoritative answer to "who actually plays".

---

## S8. Should the walk-forward model be kept?

*Context:* after the intercept fix it scores 56.19% straight-up with a Brier skill score of +0.0017
— indistinguishable from no skill.

| Path | Meaning |
|------|---------|
| **A. Publish as REJECTED with full arithmetic** (current) | The failure is the finding |
| **B. Keep iterating until it passes** | Risk: overfitting 105 games until something looks good by chance |
| **C. Delete it** | Loses the diagnostic value |

**Recommendation: A.** Requirement 4 asks to "remove luck and build selectively skill-based
strategies"; the only defensible way to do that is to publish the failures with their numbers, so a
future strategy can be compared against a documented baseline rather than against memory.

---

### Decision table for the reviewer

| ID | Recommendation | Implemented? |
|----|----------------|--------------|
| S1 | Add a CI check that fails on any table row without a source | **No — awaiting your call** |
| S2 | One long sortable games table | Yes (revisit if a 2nd season is added) |
| S3 | Frozen snapshot with printed retrieval date | Yes |
| S4 | Flat nav | Yes |
| S5 | **Commit a CSV of closing lines** | **No — awaiting your call (highest leverage)** |
| S6 | Score on Brier/log-loss, or publish no leaderboard | **No — blocked on S5** |
| S7 | Fetch the remaining 27 club depth charts | **No — awaiting your call** |
| S8 | Publish the model as REJECTED with arithmetic | Yes |
