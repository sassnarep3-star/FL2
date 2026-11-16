#!/usr/bin/env python3
"""Write the HTML pages in docs/ from one shared template.

Run before scripts/build_site.py. Pages load their data from docs/data/*.json
with relative paths, so the site works on GitHub Pages project URLs.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

NAV = [
    ("index.html", "Home"),
    ("executive-summary.html", "Executive summary"),
    ("injuries.html", "Injuries"),
    ("unit-exposure.html", "Unit exposure"),
    ("games.html", "Games"),
    ("news.html", "News"),
    ("strategies.html", "Strategies"),
    ("suggestions.html", "Suggestions"),
    ("questions.html", "Open questions"),
    ("sources.html", "Sources"),
    ("flagged.html", "Flagged for review"),
    ("../hub/index.html", "Decision Hub ↗"),
    ("../index.html", "Main site (Fourth & Signal)"),
]

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | NFL Analysis Dashboard</title>
<link rel="stylesheet" href="assets/style.css">
<script src="assets/app.js" defer></script>
</head>
<body>
<header class="top">
  <a href="index.html">NFL Analysis Dashboard</a>
  <nav class="menu">
{nav}
  </nav>
</header>
<main>
{body}
</main>
<footer>
  Analysis only, not betting advice. Data from NFL.com pages fetched 2026-11-14 unless a row says otherwise.
  Blank values are unverified and flagged. Last build: see data/meta.json.
</footer>
{page_script}
</body>
</html>
"""

NAV_HTML = "\n".join(f'    <a href="{href}">{label}</a>' for href, label in NAV)


def page(filename, title, body, script=""):
    page_script = f"<script>\n{script}\n</script>" if script else ""
    html = TEMPLATE.format(title=title, nav=NAV_HTML, body=body, page_script=page_script)
    (DOCS / filename).write_text(html, encoding="utf-8")


INDEX_BODY = """
<h1>NFL Analysis Dashboard - Week 10, 2026 season</h1>
<p class="lead">Organized by category. Every table row links to its official source. Values that cannot be verified are left blank and flagged.</p>

<div class="notice">Analysis only, not betting advice. Legal status of sports betting in Mexico City is <b>unverified</b> (see <a href="flagged.html">Flagged for review</a>, F-14).</div>

<div class="grid" id="stats"></div>

<h2>Categories</h2>
<div class="grid">
  <div class="card"><b>Data</b><p class="lead">Verified tables from NFL.com.</p>
    <p><a href="injuries.html">Injury report</a><br><a href="unit-exposure.html">Unit exposure (counts)</a><br><a href="games.html">Week 10 games</a><br><a href="news.html">Official news items</a></p></div>
  <div class="card"><b>Analysis</b><p class="lead">What the data says and does not say.</p>
    <p><a href="executive-summary.html">Executive summary</a><br><a href="strategies.html">Strategy framework and validation gates</a></p></div>
  <div class="card"><b>Planning</b><p class="lead">Choose before anything changes.</p>
    <p><a href="suggestions.html">Suggestions (awaiting your decision)</a><br><a href="questions.html">Open questions and missing information</a></p></div>
  <div class="card"><b>Governance</b><p class="lead">Where each value came from and what needs review.</p>
    <p><a href="sources.html">Source register</a><br><a href="flagged.html">Flagged for review</a></p></div>
</div>

<h2>Status at a glance</h2>
<div class="card">
  <ul>
    <li>Injury report: <b>verified</b> (NFL.com Week 10, fetched 2026-11-14).</li>
    <li>Starter vs backup: <b class="unverified">not verified</b> - no official depth chart collected yet (F-10).</li>
    <li>Betting lines and odds: <b class="unverified">no verified source</b> (F-11).</li>
    <li>Strategies validated: <b>0</b>. Validation is blocked until historical data exists (F-12).</li>
  </ul>
</div>
"""

INDEX_SCRIPT = """
document.addEventListener("DOMContentLoaded", async () => {
  const meta = await getJSON("data/meta.json");
  const s = meta.status_counts;
  const cards = [
    [meta.injury_rows, "Player entries on Week 10 report", "injuries.html"],
    [meta.injury_teams, "Teams with at least one entry", "unit-exposure.html"],
    [s.Out, "Listed Out", "injuries.html"],
    [s.Doubtful, "Listed Doubtful", "injuries.html"],
    [s.Questionable, "Listed Questionable", "injuries.html"],
    [meta.games, "Week 10 games (NFL.com)", "games.html"],
  ];
  document.getElementById("stats").innerHTML = cards.map(([n, l, h]) =>
    `<div class="stat"><div class="n">${esc(n)}</div><div class="l"><a href='${h}'>${esc(l)}</a></div></div>`).join("");
});
"""

EXEC_BODY = """
<h1>Executive summary</h1>
<p class="lead">Data pulled 2026-11-14. Facts below are from the official NFL.com pages listed in the source column. Items marked <span class="unverified">UNVERIFIED</span> are not yet confirmed.</p>

<div class="card">
<h2 style="margin-top:0">1. What is verified now</h2>
<ul>
  <li>The NFL.com Week 10 injury report lists <b>345</b> player entries across <b>28</b> teams. Of those, <b>66</b> are listed Out, <b>10</b> Doubtful and <b>84</b> Questionable as game status. Source: <a href="https://www.nfl.com/injuries/" target="_blank" rel="noopener">NFL.com injury report</a>.</li>
  <li>NFL.com lists <b>14</b> Week 10 games; teams on bye per NFL.com: CHI, DEN, PHI, TB. Source: <a href="https://www.nfl.com/schedules/2026/REG10" target="_blank" rel="noopener">NFL.com schedule</a>.</li>
  <li>Patrick Mahomes is listed with <i>Full Participation in Practice</i> and no injury on the Week 10 report, after an elbow sprain in Week 9 that NFL.com reported was not a major injury (MRI). Sources: <a href="https://www.nfl.com/injuries/" target="_blank" rel="noopener">report</a>; <a href="https://www.nfl.com/news/notable-injuries-news-sunday-week-9-games-2026" target="_blank" rel="noopener">NFL.com Week 9 news</a>.</li>
  <li>NFL.com news reports Ravens QB Lamar Jackson was placed on injured reserve (Nov 5 roundup). He is not on the Week 10 report. Source: <a href="https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-thursday-nov-5" target="_blank" rel="noopener">NFL.com</a>.</li>
  <li>Sam Darnold (SEA) is listed Out with ribs and quadricep injuries; NFL.com news says he is ruled out for Week 10 and Drew Lock is expected to start. Sources: <a href="https://www.nfl.com/injuries/" target="_blank" rel="noopener">report</a>; <a href="https://www.nfl.com/news/sam-darnold-ruled-out-for-seahawks-week-10-game-vs-raiders-drew-lock-expected-to-start-again" target="_blank" rel="noopener">NFL.com</a>.</li>
</ul>
</div>

<div class="card">
<h2 style="margin-top:0">2. Irregularities found (see Flagged for review)</h2>
<ul>
  <li>The Thursday game (Commanders 24, Giants 21) is FINAL on NFL.com but still appears in the Week 10 report with statuses (F-05).</li>
  <li>Two NFL.com headlines disagree on Lamar Jackson's timeline: 6-10 weeks vs 6-9 weeks (F-08).</li>
  <li>Puka Nacua has no injury shown on the report, while NFL.com news names knee and turf-toe injuries (F-06).</li>
</ul>
</div>

<div class="card">
<h2 style="margin-top:0">3. What we cannot yet conclude</h2>
<ul>
  <li><b>Starter vs backup</b> replacement effects on offense or defense: not verified. Counts by unit are shown, but they are not a starter analysis (F-10).</li>
  <li><b>Lines and edges</b>: no verified odds source; no lines have been originated. Closing line value and ROI cannot be measured (F-11).</li>
  <li><b>Strategies, parlays, prop combos and correlation values</b>: none evaluated. Validation needs multi-season history that is not in the repo yet (F-12).</li>
  <li><b>Legal status</b> of wagering in Mexico City: unverified (F-14).</li>
</ul>
</div>

<div class="card">
<h2 style="margin-top:0">4. Next decisions for you</h2>
<p>See the <a href="suggestions.html">Suggestions</a> page (10 options) and the <a href="questions.html">Open questions</a> page (12 items). Nothing on the suggestions list has been implemented. The critical ones are Q1 (legal status and purpose), Q4 (odds source and licence) and Q6 (official depth charts).</p>
</div>
"""

INJURIES_BODY = """
<h1>Injury report - Week 10, 2026</h1>
<p class="lead">All 345 entries from the NFL.com Week 10 report. Each row links to the player's NFL.com profile. Filters and search are above the table; click a column header to sort.</p>
<div class="notice">Game-status blanks mean NFL.com showed no game designation. Rows marked <b>Final game</b> belong to a game NFL.com lists as final (F-05). "Not injury related" rows are labelled by NFL.com (F-07 / Q7).</div>
<div id="tbl"></div>
"""

INJURIES_SCRIPT = """
document.addEventListener("DOMContentLoaded", async () => {
  const rows = await getJSON("data/injuries.json");
  const withCat = rows.map(r => ({
    ...r,
    category: r.not_injury_related ? "Not injury related" : (r.injury ? "Injury listed" : "No injury listed"),
    game_status_shown: r.game_status || "(none listed)",
    note: r.final_game_flag ? "Final game (F-05)" : "",
  }));
  renderTable({
    el: document.getElementById("tbl"),
    rows: withCat,
    countLabel: "entries",
    filters: [
      {key: "team", label: "Team"},
      {key: "game_status", label: "Game status"},
      {key: "unit", label: "Unit"},
      {key: "category", label: "Category"},
      {key: "note", label: "Notes"},
    ],
    columns: [
      {key: "team", label: "Team"},
      {key: "game", label: "Game"},
      {key: "player", label: "Player", render: r => srcLink(r.source_url, r.player)},
      {key: "position", label: "Pos"},
      {key: "unit", label: "Unit"},
      {key: "injury", label: "Injury", render: r => esc(r.injury || "(none listed)")},
      {key: "practice_status", label: "Practice"},
      {key: "game_status_shown", label: "Game status", render: r => r.game_status ? statusTag(r.game_status) : '<span class="tag">(none listed)</span>'},
      {key: "category", label: "Category", render: r => r.not_injury_related ? '<span class="tag nir">Not injury related</span>' : esc(r.category)},
      {key: "note", label: "Note", render: r => r.final_game_flag ? '<span class="tag final">Final game (F-05)</span>' : ""},
      {key: "source", label: "Source", render: r => srcLink(r.report_url, "NFL.com report") + " / " + srcLink(r.source_url, "profile"), sort: r => r.source_url},
    ],
  });
});
"""

UNIT_BODY = """
<h1>Unit exposure - counts only</h1>
<p class="lead">For each team and position group: how many entries are listed and how many are Out, Doubtful or Questionable. These are <b>descriptive counts from the NFL.com report</b>. They do not identify starters or backups, which is not yet verified (F-10).</p>
<div class="notice">"Flag" is a simple review rule, not a prediction: any QB Out or Doubtful, or 2+ Out or Doubtful in one unit. "Not injury related" entries are excluded from the status counts.</div>
<div id="tbl"></div>
"""

UNIT_SCRIPT = """
document.addEventListener("DOMContentLoaded", async () => {
  const rows = await getJSON("data/unit_exposure.json");
  renderTable({
    el: document.getElementById("tbl"),
    rows,
    countLabel: "team-unit rows",
    filters: [{key: "team", label: "Team"}, {key: "unit", label: "Unit"}, {key: "flag", label: "Flag"}],
    columns: [
      {key: "team", label: "Team"},
      {key: "game", label: "Game"},
      {key: "unit", label: "Unit"},
      {key: "listed", label: "Listed", num: true},
      {key: "out", label: "Out", num: true},
      {key: "doubtful", label: "Doubtful", num: true},
      {key: "questionable", label: "Questionable", num: true},
      {key: "dnp", label: "Did not practice", num: true},
      {key: "not_injury_related", label: "Not injury related", num: true},
      {key: "flag", label: "Flag", render: r => r.flag ? '<span class="tag high">' + esc(r.flag) + "</span>" : ""},
      {key: "source", label: "Source", render: r => srcLink(r.source_url, "NFL.com report")},
    ],
  });
});
"""

GAMES_BODY = """
<h1>Week 10 games</h1>
<p class="lead">Matchups in NFL.com order (away at home), with kickoff time in Eastern Time as shown on NFL.com.</p>
<div class="card">Teams on bye, per NFL.com: CHI, DEN, PHI, TB. <a href="https://www.nfl.com/schedules/2026/REG10" target="_blank" rel="noopener">Source: NFL.com schedule</a></div>
<div id="tbl"></div>
"""

GAMES_SCRIPT = """
document.addEventListener("DOMContentLoaded", async () => {
  const rows = await getJSON("data/games.json");
  renderTable({
    el: document.getElementById("tbl"),
    rows,
    countLabel: "games",
    filters: [{key: "date_et", label: "Date"}, {key: "status", label: "Status"}],
    columns: [
      {key: "date_et", label: "Date (ET)"},
      {key: "time_et", label: "Time (ET)"},
      {key: "network", label: "Network"},
      {key: "label", label: "Matchup (away at home)"},
      {key: "status", label: "Status"},
      {key: "source", label: "Source", render: r => srcLink(r.source_url, "NFL.com game page")},
    ],
  });
});
"""

NEWS_BODY = """
<h1>Official NFL.com news items</h1>
<p class="lead">Headlines listed on the Week 10 injury page and linked NFL.com articles. The "Date stated" column only shows a date when the headline or URL contains one; otherwise it is blank (not inferred).</p>
<div id="tbl"></div>
"""

NEWS_SCRIPT = """
document.addEventListener("DOMContentLoaded", async () => {
  const rows = await getJSON("data/news.json");
  renderTable({
    el: document.getElementById("tbl"),
    rows,
    countLabel: "items",
    columns: [
      {key: "date_stated", label: "Date stated", render: r => r.date_stated.startsWith("(none") ? '<span class="unverified">not stated</span>' : esc(r.date_stated)},
      {key: "headline", label: "Headline", render: r => srcLink(r.source_url, r.headline)},
      {key: "listed_on", label: "Listed on", render: r => srcLink(r.listed_on, "NFL.com injuries")},
      {key: "source_id", label: "Source ID"},
    ],
  });
});
"""

STRAT_BODY = """
<h1>Strategy framework and validation gates</h1>
<div class="notice bad"><b>No strategies have been evaluated and none are ranked.</b> The leaderboard is empty. Validation is blocked: there is no verified historical odds or outcome data in the repo (F-11, F-12). Correlation values are not computed.</div>
<h2>Signal families</h2>
<div id="signals"></div>
<h2>Validation gates (every strategy must pass before ranking)</h2>
<div id="gates"></div>
<h2>Leaderboard</h2>
<div class="card" id="board">Empty. No strategy has passed the gates.</div>
"""

STRAT_SCRIPT = """
document.addEventListener("DOMContentLoaded", async () => {
  const d = await getJSON("data/strategies.json");
  renderTable({
    el: document.getElementById("signals"), rows: d.signal_families, search: false,
    columns: [
      {key: "id", label: "ID"}, {key: "signal", label: "Signal"}, {key: "description", label: "Description"},
      {key: "data_required", label: "Data required"}, {key: "available_now", label: "Available now"},
      {key: "status", label: "Status"}, {key: "validation_status", label: "Validation"},
    ],
  });
  renderTable({
    el: document.getElementById("gates"), rows: d.validation_gates, search: false,
    columns: [
      {key: "id", label: "Gate"}, {key: "gate", label: "Name"}, {key: "rule", label: "Rule"}, {key: "threshold", label: "Threshold"},
    ],
  });
});
"""

SUGG_BODY = """
<h1>Suggestions - choose before anything changes</h1>
<p class="lead">Nothing here has been implemented. Each suggestion lists the data it needs and its risks. Decision column is for you to fill in (for example: "A").</p>
<div id="tbl"></div>
"""

SUGG_SCRIPT = """
document.addEventListener("DOMContentLoaded", async () => {
  const d = await getJSON("data/suggestions.json");
  renderTable({
    el: document.getElementById("tbl"), rows: d.suggestions.map(s => ({...s, opts: s.options.join(" | ")})),
    countLabel: "suggestions",
    columns: [
      {key: "id", label: "ID"}, {key: "title", label: "Suggestion"}, {key: "what", label: "What"},
      {key: "why", label: "Why"}, {key: "data_needed", label: "Data needed"}, {key: "effort", label: "Effort"},
      {key: "risk", label: "Risk"}, {key: "opts", label: "Options"}, {key: "decision", label: "Decision"},
    ],
  });
});
"""

QUEST_BODY = """
<h1>Open questions and missing information</h1>
<p class="lead">Questions that must be answered before a decision can reasonably be made. For each: what is verified, what is missing, and how to close the gap.</p>
<div id="tbl"></div>
"""

QUEST_SCRIPT = """
document.addEventListener("DOMContentLoaded", async () => {
  const d = await getJSON("data/questions.json");
  renderTable({
    el: document.getElementById("tbl"), rows: d.questions, countLabel: "questions",
    filters: [{key: "priority", label: "Priority"}, {key: "status", label: "Status"}],
    columns: [
      {key: "id", label: "ID"}, {key: "question", label: "Question"}, {key: "why_it_matters", label: "Why it matters"},
      {key: "known_verified", label: "Known (verified)"}, {key: "missing", label: "Missing"},
      {key: "how_to_close", label: "How to close the gap"}, {key: "priority", label: "Priority"}, {key: "status", label: "Status"},
    ],
  });
});
"""

SOURCES_BODY = """
<h1>Source register</h1>
<p class="lead">Every source used, how it was accessed, and how far it was verified. S7 was attempted but not used.</p>
<div id="tbl"></div>
"""

SOURCES_SCRIPT = """
document.addEventListener("DOMContentLoaded", async () => {
  const d = await getJSON("data/sources.json");
  renderTable({
    el: document.getElementById("tbl"), rows: d.sources, search: false, countLabel: "sources",
    columns: [
      {key: "id", label: "ID"}, {key: "title", label: "Title", render: r => srcLink(r.url, r.title)},
      {key: "publisher", label: "Publisher"}, {key: "type", label: "Type"}, {key: "used_for", label: "Used for"},
      {key: "how_verified", label: "How verified"}, {key: "verification_level", label: "Verification level"},
    ],
  });
});
"""

FLAG_BODY = """
<h1>Flagged for review</h1>
<p class="lead">Irregularities, gaps and unverified items. These do not block the site. Each row lists the source links so you can check them directly.</p>
<div id="tbl"></div>
"""

FLAG_SCRIPT = """
document.addEventListener("DOMContentLoaded", async () => {
  const d = await getJSON("data/flags.json");
  renderTable({
    el: document.getElementById("tbl"), rows: d.flags, countLabel: "flags",
    filters: [{key: "category", label: "Category"}, {key: "severity", label: "Severity"}, {key: "status", label: "Status"}],
    columns: [
      {key: "id", label: "ID"}, {key: "category", label: "Category"},
      {key: "severity", label: "Severity", render: r => '<span class="tag ' + esc(r.severity.toLowerCase()) + '">' + esc(r.severity) + "</span>"},
      {key: "item", label: "Item"}, {key: "detail", label: "Detail"}, {key: "status", label: "Status"},
      {key: "source_urls", label: "Source links", render: r => (r.source_urls && r.source_urls.length)
        ? r.source_urls.map((u, i) => srcLink(u, "Link " + (i + 1))).join("<br>") : '<span class="unverified">none</span>'},
    ],
  });
});
"""

PAGES = [
    ("index.html", "Home", INDEX_BODY, INDEX_SCRIPT),
    ("executive-summary.html", "Executive summary", EXEC_BODY, ""),
    ("injuries.html", "Injuries", INJURIES_BODY, INJURIES_SCRIPT),
    ("unit-exposure.html", "Unit exposure", UNIT_BODY, UNIT_SCRIPT),
    ("games.html", "Games", GAMES_BODY, GAMES_SCRIPT),
    ("news.html", "News", NEWS_BODY, NEWS_SCRIPT),
    ("strategies.html", "Strategies", STRAT_BODY, STRAT_SCRIPT),
    ("suggestions.html", "Suggestions", SUGG_BODY, SUGG_SCRIPT),
    ("questions.html", "Open questions", QUEST_BODY, QUEST_SCRIPT),
    ("sources.html", "Sources", SOURCES_BODY, SOURCES_SCRIPT),
    ("flagged.html", "Flagged for review", FLAG_BODY, FLAG_SCRIPT),
]


def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    for filename, title, body, script in PAGES:
        page(filename, title, body, script)
    print(f"wrote {len(PAGES)} pages")


if __name__ == "__main__":
    main()
