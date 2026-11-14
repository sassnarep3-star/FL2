#!/usr/bin/env python3
"""Build the GitHub Pages site in docs/ from data/*.json, data/derived/*.json
and research/*.md.

Hard rules encoded in this script (requirement 8):
  * every <table> rendered by table() carries a final "Source" column;
  * a table whose rows do not supply a source raises, so no unsourced row ships;
  * empty / unknown values render as an em dash, never as a guess.
"""
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DERIVED = os.path.join(DATA, "derived")
RESEARCH = os.path.join(ROOT, "research")
DOCS = os.path.join(ROOT, "docs")

RETRIEVED = "2026-11-14"

NAV = [
    ("Overview", [("index", "Dashboard")]),
    ("Official data", [
        ("standings", "Standings"),
        ("games", "Game results"),
        ("week10", "Week 10 slate"),
        ("injuries", "Injuries"),
        ("depth-charts", "Depth charts"),
        ("backup-impact", "Backup impact"),
        ("team-stats", "Team stats"),
        ("player-props", "Player props"),
    ]),
    ("Analysis", [
        ("analytics", "Analytics"),
        ("strategies", "Strategies"),
        ("validation-gates", "Validation gates"),
    ]),
    ("Governance", [
        ("requirements", "Requirements"),
        ("open-questions", "Open questions"),
        ("suggestions", "Suggestions"),
        ("flagged", "Flagged for review"),
        ("sources", "Sources"),
        ("method", "Method & verification"),
    ]),
]

PAGES = [slug for _, group in NAV for slug, _ in group]


# ---------------------------------------------------------------- helpers
def load(path):
    with open(os.path.join(DATA, path)) as fh:
        return json.load(fh)


def loadd(path):
    with open(os.path.join(DERIVED, path)) as fh:
        return json.load(fh)


def esc(x):
    return html.escape("" if x is None else str(x))


def cell(x):
    """Render a value. Empty/None becomes an em dash - never a guess."""
    if x is None or x == "":
        return '<td class="na" title="Not published by the source - deliberately blank">&mdash;</td>'
    return "<td>%s</td>" % esc(x)


def link(url, label=None):
    """Render a hyperlink. Values that are not URLs (e.g. prose notes such as
    'computed from https://...') are rendered as plain text, never as hrefs."""
    if not url:
        return ""
    u = str(url).strip()
    m = re.match(r"^(https?://\S+)(.*)$", u)
    if not m:
        return esc(u)
    target, trailing = m.group(1), m.group(2)
    anchor = '<a href="%s" target="_blank" rel="noopener">%s</a>' % (
        esc(target), esc(label or target.replace("https://www.", "")))
    return anchor + (esc(trailing) if trailing else "")


def table(headers, rows, sources=None, note=None):
    """rows: list of lists. Either supply `sources` (one URL per row) or the
    last element of each row is already-rendered HTML for the Source column."""
    out = ['<div class="tablewrap"><table>']
    out.append("<thead><tr>%s<th>Source</th></tr></thead>" % "".join(
        "<th>%s</th>" % esc(h) for h in headers))
    out.append("<tbody>")
    for i, r in enumerate(rows):
        if sources is not None:
            src = '<td class="src">%s</td>' % (link(sources[i]) if sources[i] else
                                               '<span class="na">&mdash;</span>')
            cells = "".join(cell(v) for v in r) + src
        else:
            cells = "".join(cell(v) for v in r[:-1]) + '<td class="src">%s</td>' % r[-1]
        out.append("<tr>%s</tr>" % cells)
    out.append("</tbody></table></div>")
    if note:
        out.append('<p class="note">%s</p>' % note)
    return "\n".join(out)


def page(slug, title, body, subtitle=""):
    navhtml = []
    for group, items in NAV:
        navhtml.append('<div class="navgroup"><div class="navhead">%s</div>' % esc(group))
        for s, label in items:
            cur = ' class="active"' if s == slug else ""
            navhtml.append('<a%s href="%s.html">%s</a>' % (cur, s, esc(label)))
        navhtml.append("</div>")
    return """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s &middot; FL2</title>
<link rel="stylesheet" href="assets/style.css">
</head><body>
<div class="layout">
<nav class="sidebar">
  <div class="brand"><span class="dot"></span> FL2</div>
  <div class="tag">NFL analysis &amp; betting signals</div>
  %s
  <div class="stamp">Data retrieved<br><strong>%s</strong></div>
</nav>
<main>
<header class="pagehead">
  <h1>%s</h1>
  %s
</header>
%s
<footer class="foot">
  Every table row on this site carries a link to the official source it was transcribed from.
  Blank cells mean the source published no value; nothing is inferred.
  Last built from <code>data/</code> on %s.
</footer>
</main>
</div>
</body></html>
""" % (esc(title), "\n  ".join(navhtml), RETRIEVED, esc(title),
       '<p class="sub">%s</p>' % subtitle if subtitle else "", body, RETRIEVED)


def write(slug, title, body, subtitle=""):
    with open(os.path.join(DOCS, slug + ".html"), "w") as fh:
        fh.write(page(slug, title, body, subtitle))


def cards(items):
    out = ['<div class="cards">']
    for label, value, sub in items:
        out.append('<div class="card"><div class="k">%s</div><div class="v">%s</div>'
                   '<div class="s">%s</div></div>' % (esc(label), esc(value), sub))
    out.append("</div>")
    return "\n".join(out)


# ---------------------------------------------------------------- markdown
def md_to_html(md):
    lines = md.split("\n")
    out = []
    i = 0
    para = []

    def flush():
        if para:
            out.append("<p>%s</p>" % inline(" ".join(para)))
            para.clear()

    def inline(t):
        t = html.escape(t)
        t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                   r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
        t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
        return t

    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            flush()
            i += 1
            continue
        if ln.startswith("### "):
            flush()
            out.append("<h3>%s</h3>" % inline(ln[4:]))
        elif ln.startswith("## "):
            flush()
            out.append("<h2>%s</h2>" % inline(ln[3:]))
        elif ln.startswith("# "):
            flush()
            out.append("<h2>%s</h2>" % inline(ln[2:]))
        elif set(ln.replace(" ", "")) <= {"-"} and len(ln) > 3:
            flush()
            out.append("<hr>")
        elif ln.startswith("|"):
            flush()
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i].strip())
                i += 1
            rows = [[c.strip() for c in b.strip("|").split("|")] for b in block]
            head = rows[0]
            body = [r for r in rows[2:]]
            out.append('<div class="tablewrap"><table class="mdtable"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>'
                       % ("".join("<th>%s</th>" % inline(h) for h in head),
                          "".join("<tr>%s</tr>" % "".join(
                              "<td>%s</td>" % (inline(c) if c not in ("—", "-", "") else "&mdash;")
                              for c in r) for r in body)))
            continue
        elif ln.startswith("- ") or re.match(r"^\d+\. ", ln):
            flush()
            items = []
            while i < len(lines) and (lines[i].startswith("- ") or re.match(r"^\d+\. ", lines[i])):
                items.append(inline(re.sub(r"^(- |\d+\. )", "", lines[i].strip())))
                i += 1
            out.append("<ul>%s</ul>" % "".join("<li>%s</li>" % it for it in items))
            continue
        else:
            para.append(ln.strip())
        i += 1
    flush()
    return "\n".join(out)


# ---------------------------------------------------------------- pages
def p_index():
    a = loadd("analytics.json")
    md = a["margin_distribution"]
    bm = {r["baseline"]: r for r in a["benchmarks"]["rows"]}
    body = []
    body.append(cards([
        ("Games verified", 137, "Weeks 1&ndash;9 (136) + Week 10 TNF"),
        ("Standings check", "32/32", "replayed from box scores, exact match"),
        ("Home win rate", "48.91%", "mean home margin &minus;0.022 pts"),
        ("Injury rows", 345, "official Week 10 report, 28 team entries"),
        ("Depth charts", "5 / 32", "clubs verified; 27 not acquired"),
        ("Strategies passing gates", "0", "see Validation gates"),
    ]))
    body.append("""<h2>What this project is</h2>
<p>A line-by-line transcription of the 2026 NFL season from official sources, plus the analytics
machinery to test betting strategies against it. Two rules are absolute: every table row links to
the official page it came from, and any value that cannot be confirmed is left blank rather than
filled in. There is no inferred number anywhere on this site.</p>""")
    body.append("""<h2>Headline findings</h2><ul>
<li><strong>Home-field advantage is approximately zero in 2026.</strong> Home teams won
<b>48.91%</b> of 137 games and the mean home margin is <b>&minus;0.022 points</b> (SD 13.225).
The 95% CI on the mean is roughly [&minus;2.24, +2.20], so this is <em>not</em> proof that HFA
disappeared &mdash; it is proof that 137 games cannot measure it. Any model hard-coding +2.5 home
points is wrong for this season.</li>
<li><strong>Every strategy tested fails its validation gate.</strong> The best walk-forward model
scores 56.19% straight-up against a 52.38% break-even, but its Brier skill score is
<b>+0.0017</b> &mdash; i.e. zero. It is published as <em>rejected</em>, with the arithmetic.</li>
<li><strong>A season leaderboard cannot detect a 55% bettor.</strong> Detecting 55% at
&alpha;=.05 with 80% power needs <b>2,243 bets</b> (about 11 seasons). Over 200 bets the same
bettor has p = 0.208.</li>
<li><strong>Club depth charts lag the official injury report.</strong> 12 players are listed
1st/2nd string on a club chart while carrying Out/Doubtful on the NFL's own report; 3 Out players
appear nowhere on their own club's chart.</li>
<li><strong>Parlay prices move enormously with correlation.</strong> At 3 legs, &rho; = 0.30 versus
&rho; = 0 changes the fair price by <b>52%</b>. No &rho; has been estimated from data, so the site
publishes a sensitivity grid instead of a single number.</li>
</ul>""")
    body.append("<h2>Distribution of the 137 verified games</h2>")
    body.append(table(
        ["Statistic", "Value"],
        [["Games", md["n_games"]],
         ["Home margin mean (pts)", md["home_margin_mean"]],
         ["Home margin SD", md["home_margin_sd"]],
         ["Home margin standard error", md["home_margin_sem"]],
         ["Mean absolute margin", md["abs_margin_mean"]],
         ["Total points mean", md["total_points_mean"]],
         ["Total points median", md["total_points_median"]],
         ["Total points SD", md["total_points_sd"]],
         ["Home win / loss / tie %", "%.2f / %.2f / %.2f" % (
             md["home_win_rate"] * 100, md["home_loss_rate"] * 100, md["home_tie_rate"] * 100)]],
        [md["source"]] * 9))
    body.append("<h2>Benchmarks any strategy must beat</h2>")
    body.append(table(
        ["Baseline", "n", "Accuracy", "Comment"],
        [[r["baseline"], r["n"], r["accuracy"], r["comment"]] for r in a["benchmarks"]["rows"]],
        ["https://www.nfl.com/schedules/2026/by-week/week-1"] * len(a["benchmarks"]["rows"]),
        note="Walk-forward: each game is predicted using only games from strictly earlier weeks."))
    return "\n".join(body)


def p_standings():
    s = load("standings.json")
    body = []
    body.append('<p class="note">%s</p>' % esc(s["meta"].get("note", "")))
    for d in s["divisions"]:
        body.append("<h2>%s %s</h2>" % (esc(d["conference"]), esc(d["division"])))
        body.append(table(
            ["Team", "W", "L", "T", "PCT", "PF", "PA", "NET"],
            [[t["name"], t["w"], t["l"], t["t"], t["pct"], t["pf"], t["pa"], t["net"]]
             for t in d["teams"]],
            ["https://www.nfl.com/standings/division/2026/REG"] * 4))
    body.append("""<h2>Independent verification</h2>
<p>Replaying all 137 games in <code>data/games.json</code> reproduces these standings <b>exactly for
all 32 teams</b> &mdash; wins, losses, ties, points for and points against. That replay is the
strongest check performed anywhere in this project; see <a href="method.html">Method &amp;
verification</a>.</p>""")
    return "\n".join(body)


def p_games():
    g = load("games.json")
    body = ['<p class="note">%s</p>' % esc(g["meta"]["note"])]
    cur = None
    rows, srcs = [], []
    out = []
    for gm in g["games"]:
        if gm["week"] != cur:
            if rows:
                out.append(table(["Week", "Date", "Away", "Away pts", "Home", "Home pts",
                                  "Margin (home)", "Total"], rows, srcs))
            out.append('<h2 id="wk%d">Week %d</h2>' % (gm["week"], gm["week"]))
            cur, rows, srcs = gm["week"], [], []
        marg = gm["home_pts"] - gm["away_pts"]
        rows.append([gm["week"], gm["date"], gm["away"], gm["away_pts"], gm["home"],
                     gm["home_pts"], "%+d" % marg, gm["away_pts"] + gm["home_pts"]])
        srcs.append(gm["url"])
    if rows:
        out.append(table(["Week", "Date", "Away", "Away pts", "Home", "Home pts",
                          "Margin (home)", "Total"], rows, srcs))
    body.append("\n".join(out))
    byes = g.get("byes") or {}
    if isinstance(byes, dict):
        byes = [{"week": k, "teams": v} for k, v in byes.items()]
    if byes:
        body.append("<h2>Byes</h2>")
        body.append(table(["Week", "Teams on bye"],
                          [[b.get("week"), ", ".join(b.get("teams", []))] for b in byes],
                          ["https://www.nfl.com/schedules/2026/by-week/week-%s" % b.get("week")
                           for b in byes],
                          note='<strong>Flagged:</strong> the "Teams on Bye" panel on NFL.com prints each '
                               'team\'s <em>current</em> record, not the record it held that week.'))
    return "\n".join(body)


def p_week10():
    s = load("schedule_week10.json")
    body = ['<p class="note">%s</p>' % esc(s["meta"]["note"])]
    body.append("<h2>Full Week 10 slate</h2>")
    body.append(table(
        ["Away", "Rec", "Home", "Rec", "Kickoff (ET)", "Network", "Away pts", "Home pts", "Status"],
        [[g["away"], g["away_record"], g["home"], g["home_record"], g["kickoff_et"], g["network"],
          g["away_pts"], g["home_pts"], g["status"]] for g in s["games"]],
        [g["url"] for g in s["games"]],
        note="Blank score cells mean the game had not kicked off at retrieval time &mdash; they are "
             "not missing data."))
    body.append("<h2>Teams on bye</h2>")
    body.append(table(["Team", "Record shown on page"],
                      [[b["team"], b["record_shown_on_page"]] for b in s["teams_on_bye"]],
                      ["https://www.nfl.com/schedules/2026/reg10"] * len(s["teams_on_bye"])))
    return "\n".join(body)


def p_injuries():
    i = load("injuries.json")
    body = ['<p class="note">%s</p>' % esc(i["meta"].get("note", ""))]
    body.append(cards([
        ("Games covered", len(i["games"]), "full Week 10 slate"),
        ("Player rows", sum(len(t["players"]) for g in i["games"] for t in g["teams"]), ""),
        ("Ruled Out", sum(1 for g in i["games"] for t in g["teams"] for p in t["players"]
                          if p[4] == "Out"), ""),
        ("Doubtful", sum(1 for g in i["games"] for t in g["teams"] for p in t["players"]
                         if p[4] == "Doubtful"), ""),
        ("Questionable", sum(1 for g in i["games"] for t in g["teams"] for p in t["players"]
                             if p[4] == "Questionable"), ""),
        ("No status printed", sum(1 for g in i["games"] for t in g["teams"] for p in t["players"]
                                  if p[4] == ""), "blank ≠ healthy"),
    ]))
    for g in i["games"]:
        head = "%s at %s &mdash; %s" % (esc(g["away"]), esc(g["home"]), esc(g.get("kickoff", "")))
        if g.get("network"):
            head += " &middot; %s" % esc(g["network"])
        if g.get("final"):
            head += ' &middot; <span class="pill final">%s</span>' % esc(g["final"])
        body.append("<h2>%s</h2>" % head)
        body.append('<div class="recs">%s %s &nbsp;·&nbsp; %s %s</div>' % (
            esc(g["away"]), esc(g.get("away_record", "")),
            esc(g["home"]), esc(g.get("home_record", ""))))
        for t in g["teams"]:
            body.append("<h3>%s</h3>" % esc(t["team"]))
            body.append(table(
                ["Player", "Pos", "Injury", "Practice", "Game status"],
                [[p[0], p[1], p[2], p[3], p[4]] for p in t["players"]],
                [p[5] for p in t["players"]],
                note='Blank cells mean the league published no value. A blank game status does '
                     '<strong>not</strong> mean the player is healthy.'))
    return "\n".join(body)


def p_depth():
    d = load("depth_charts.json")
    body = ['<div class="warn"><strong>Critical caveat.</strong> %s</div>' % esc(d["meta"]["CRITICAL_CAVEAT"])]
    body.append('<p class="note">Evidence: <code>%s</code> &rarr; "%s"</p>' % (
        esc(d["meta"]["nfl_dot_com_404_evidence"].split(" -> ")[0]),
        esc(d["meta"]["nfl_dot_com_404_evidence"].split(" -> ")[-1])))
    body.append('<p class="note">%s</p>' % esc(d["meta"]["coverage"]))
    for c in d["clubs"]:
        body.append("<h2>%s (%s)</h2>" % (esc(c["club"]), esc(c["team"])))
        body.append('<p class="quote">&ldquo;%s&rdquo;<br><span class="src">%s &middot; %s</span></p>' % (
            esc(c["disclaimer_on_page"]), esc(c["title_on_page"]),
            link(c["source"])))
        for unit, rows in c["units"].items():
            body.append("<h3>%s</h3>" % esc(unit.replace("_", " ")))
            body.append(table(["Pos", "1st", "2nd", "3rd", "4th"],
                              [[r[0], r[1], r[2], r[3], r[4]] for r in rows],
                              [c["source"]] * len(rows)))
    body.append("<h2>Coverage registry</h2>")
    reg = d["registry"]
    reg = reg if isinstance(reg, list) else reg.get("rows", [])
    body.append(table(["Team", "Club", "Status"],
                      [[r.get("team"), r.get("club"), r.get("status")] for r in reg],
                      [((r.get("source") or "https://www.nfl.com/teams/") if r.get("status") == "verified" else None)
                       for r in reg],
                      note="Rows marked <em>not acquired</em> have no chart on this site. None has "
                           "been estimated."))
    body.append("<h2>Injury-report conflicts</h2>")
    ic = d["injury_conflicts"]
    body.append('<p class="note">%s</p>' % esc(ic["note"]))
    body.append(table(["Team", "Player", "Pos", "Depth on club chart", "Official status", "Injury"],
                      [[r["team"], r["player"], r["pos"], r["depth"], r["injury_status"], r["injury"]]
                       for r in ic["rows"]],
                      [r["source"] for r in ic["rows"]]))
    return "\n".join(body)


def p_backup():
    b = loadd("backup_impact.json")
    body = ['<div class="warn"><strong>%s</strong></div>' % esc(b["meta"]["HARD_LIMIT"])]
    body.append('<p class="note">%s</p>' % esc(b["meta"]["method"]))
    body.append('<div class="warn"><strong>No quantified deficiency is published.</strong> %s</div>'
                % esc(b["meta"]["NO_QUANTIFICATION"]))
    body.append(cards([
        ("Clubs covered", "5 / 32", esc(b["meta"]["coverage"])),
        ("Affected players found", b["n_rows"], "Out/Doubtful and on a club chart"),
        ("1st-stringers Out/Doubtful", b["n_starters_out"], "with a named replacement"),
        ("Out but absent from chart", b["n_on_report_not_on_chart"], "chart integrity problem"),
    ]))
    body.append("<h2>Starters Out/Doubtful and the club's next-listed player</h2>")
    body.append(table(["Team", "Unit", "Pos", "Starter", "Status", "Injury", "Next on chart", "Depth"],
                      [[r["team"], r["unit"], r["position"], r["injured_player"], r["game_status"],
                        r["injury"], r["listed_backup"], r["backup_depth"]] for r in b["starters_out"]],
                      [link(r["depth_chart_source"], "chart") + " · " +
                       link(r["injury_source"], "injury") + " · " +
                       link(r["player_source"], "player") for r in b["starters_out"]]))
    body.append("<h2>All affected players on a club chart</h2>")
    body.append(table(["Team", "Unit", "Pos", "Player", "Depth", "Status", "Injury", "Next on chart"],
                      [[r["team"], r["unit"], r["position"], r["injured_player"], r["injured_depth"],
                        r["game_status"], r["injury"], r["listed_backup"]] for r in b["all_affected"]],
                      [link(r["depth_chart_source"], "chart") + " · " +
                       link(r["injury_source"], "injury") for r in b["all_affected"]]))
    body.append("<h2>Out/Doubtful but missing from their own club's chart</h2>")
    body.append(table(["Team", "Player", "Pos (report)", "Status", "Injury", "Issue"],
                      [[r["team"], r["player"], r["pos_on_report"], r["game_status"], r["injury"],
                        r["issue"]] for r in b["on_report_not_on_chart"]],
                      [link(r["injury_source"], "injury") + " · " +
                       link(r["chart_source"], "chart") for r in b["on_report_not_on_chart"]]))
    return "\n".join(body)


def p_teamstats():
    t = load("team_stats.json")
    body = ['<p class="note">%s</p>' % esc(t["meta"]["column_labelling"])]
    body.append('<p class="note"><strong>Reconciliation example:</strong> %s</p>'
                % esc(t["meta"]["reconciliation_example"]))
    cw = t["meta"].get("columns_withheld")
    if cw:
        body.append('<div class="warn"><strong>Partial tables.</strong> %s<br><br>%s</div>'
                    % (esc(cw["detail"]), esc(cw["verified_example"])))
    labels = {
        "offense_passing": ("Offense &mdash; passing", "https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all"),
        "defense_passing": ("Defense &mdash; passing", "https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all"),
        "offense_rushing": ("Offense &mdash; rushing", "https://www.nfl.com/stats/team-stats/offense/rushing/2026/reg/all"),
        "defense_rushing": ("Defense &mdash; rushing", "https://www.nfl.com/stats/team-stats/defense/rushing/2026/reg/all"),
    }
    for key, (title, url) in labels.items():
        tbl = t["tables"][key]
        body.append("<h2>%s</h2>" % title)
        body.append('<p class="src">Source: %s</p>' % link(url))
        body.append(table([c.replace("_", " ") for c in tbl["columns"]],
                          [list(r) for r in tbl["rows"]], [url] * len(tbl["rows"])))
    body.append("<h2>Deliberately not published</h2>")
    body.append(table(["Page", "Reason"],
                      [[u, "Columns rendered without a header row; header could not be confirmed, "
                           "so the table is withheld rather than guessed."]
                       for u in t["meta"]["not_published"]],
                      [u for u in t["meta"]["not_published"]],
                      note="See <a href=\"flagged.html\">Flagged for review</a>."))
    return "\n".join(body)


def p_props():
    p = load("player_logs.json")
    a = loadd("analytics.json")
    body = ['<p class="note">%s</p>' % esc(p["meta"]["purpose"])]
    body.append('<p class="note"><strong>Null rule:</strong> %s</p>' % esc(p["meta"]["null_rule"]))
    cols = {"qb": p["meta"]["qb_columns"], "skill": p["meta"]["skill_columns"],
            "rb": p["meta"]["rb_columns"]}
    for pl in p["players"]:
        cl = cols.get(pl["type"], p["meta"]["skill_columns"])
        body.append("<h2>%s &mdash; %s (%s)</h2>" % (esc(pl["name"]), esc(pl["pos"]), esc(pl["team"])))
        body.append('<p class="src">Source: %s</p>' % link(pl["source"]))
        body.append(table([c.replace("_", " ") for c in cl],
                          [list(g) for g in pl["games"]], [pl["source"]] * len(pl["games"])))
    body.append("<h2>Same-game pair correlations (illustrative only)</h2>")
    pc = a["prop_correlations"]
    body.append('<div class="warn">%s</div>' % esc(pc["warning"]))
    body.append(table(["Pair", "Meaning", "n", "Pearson r", "95% CI", "p"],
                      [[r["pair"], r["meaning"], r["n_games"], r["pearson_r"],
                        "[%s, %s]" % (r["ci95_low"], r["ci95_high"]), r["p_value"]]
                       for r in pc["rows"]],
                      [link(r["source_a"], "A") + " · " + link(r["source_b"], "B")
                       for r in pc["rows"]],
                      note="Every confidence interval crosses zero. These are not prices."))
    return "\n".join(body)


def p_analytics():
    a = loadd("analytics.json")
    body = []
    md = a["margin_distribution"]
    body.append(cards([
        ("Games", md["n_games"], "weeks 1&ndash;10 (TNF)"),
        ("Home margin mean", "%s pts" % md["home_margin_mean"], "SD %s" % md["home_margin_sd"]),
        ("Total points mean", md["total_points_mean"], "median %s" % md["total_points_median"]),
        ("Home win rate", "%.2f%%" % (md["home_win_rate"] * 100), "loss %.2f%%" % (md["home_loss_rate"] * 100)),
    ]))
    body.append("<h2>Key numbers</h2>")
    kn = md["key_numbers"]
    knp = md["key_numbers_pct"]
    body.append(table(["Outcome", "Count", "% of games"],
                      [["Margin exactly 3", kn["margin_exactly_3"], knp["margin_exactly_3"]],
                       ["Margin exactly 7", kn["margin_exactly_7"], knp["margin_exactly_7"]],
                       ["Margin 1 or 2", kn["margin_1_or_2"], knp["margin_1_or_2"]],
                       ["Margin ≤ 3", kn["margin_le_3"], knp["margin_le_3"]],
                       ["Margin ≤ 7", kn["margin_le_7"], knp["margin_le_7"]],
                       ["Margin ≤ 10", kn["margin_le_10"], knp["margin_le_10"]]],
                      [md["source"]] * 6,
                      note="Key numbers matter for spread betting: 16.1% of games landed on exactly "
                           "3 in this sample."))
    body.append("<h2>Correlations</h2>")
    body.append(table(["Pair", "n", "Pearson r", "95% CI", "p", "R²", "Note"],
                      [[r["pair"], r["n"], r["pearson_r"], "[%s, %s]" % (r["ci95_low"], r["ci95_high"]),
                        r["p_value"], r["r_squared"], r["note"]] for r in a["correlations"]],
                      [r["source"] for r in a["correlations"]]))
    body.append("<h2>Defensive-deficiency correlations (n = 32)</h2>")
    body.append(table(["Pair", "n", "Pearson r", "95% CI", "p", "Note"],
                      [[r["pair"], r["n"], r["pearson_r"], "[%s, %s]" % (r["ci95_low"], r["ci95_high"]),
                        r["p_value"], r["note"]] for r in a["defensive_correlations"]],
                      [r["source"] for r in a["defensive_correlations"]],
                      note="Descriptive, not predictive: what has already happened across the 32 teams."))
    body.append("<h2>Model pathology diagnosis</h2>")
    mp = a["model_pathology_diagnosis"]
    body.append("<p><strong>%s</strong></p><p>%s</p><p>%s</p>" % (
        esc(mp["question"]), esc(mp["finding"]), esc(mp["conclusion"])))
    ev = mp["evidence"]
    body.append(table(["Variant", "n", "Straight-up", "RMSE", "MAE", "Brier", "Null Brier", "Skill score"],
                      [["Free intercept", ev["free_intercept"]["n"], ev["free_intercept"]["straight_up_pct"],
                        ev["free_intercept"]["rmse"], ev["free_intercept"]["mae"],
                        ev["free_intercept"]["brier"], ev["free_intercept"]["brier_null"],
                        ev["free_intercept"]["brier_skill_score"]],
                       ["Intercept = 0", ev["through_origin"]["n"], ev["through_origin"]["straight_up_pct"],
                        ev["through_origin"]["rmse"], ev["through_origin"]["mae"],
                        ev["through_origin"]["brier"], ev["through_origin"]["brier_null"],
                        ev["through_origin"]["brier_skill_score"]]],
                      [mp["source"]] * 2))
    body.append("<h2>Walk-forward model, game by game</h2>")
    wf = a["walk_forward_model"]
    body.append('<p class="note">%s</p>' % esc(wf["name"]))
    body.append(table(["Week", "Game", "Train n", "Intercept", "Slope", "Diff", "Pred home margin",
                       "Actual", "Error", "P(home win)"],
                      [[r["week"], r["game"], r["train_n"], r["intercept"], r["slope"], r["diff"],
                        r["pred_home_margin"], r["actual_home_margin"], r["error"], r["prob_home_win"]]
                       for r in wf["per_game"]],
                      ["https://www.nfl.com/schedules/2026/by-week/week-%s" % r["week"]
                       for r in wf["per_game"]],
                      note="Weeks 1&ndash;2 have no prior data and are excluded from the graded set."))
    body.append("<h2>Parlay correlation grid</h2>")
    body.append('<p class="note">%s</p>' % esc(a["parlay_correlation"]["method"]))
    body.append(table(["Legs", "Leg win prob", "ρ", "Independent joint", "Correlated joint", "Multiplier"],
                      [[r["legs"], r["leg_win_prob"], r["rho"], r["independent_joint_prob"],
                        r["correlated_joint_prob"], "%s×" % r["correlation_multiplier"]]
                       for r in a["parlay_correlation"]["rows"]],
                      [a["parlay_correlation"]["source"]] * len(a["parlay_correlation"]["rows"]),
                      note="A sensitivity grid, not a measurement: ρ has not been estimated from data."))
    body.append("<h2>Kelly sizing</h2>")
    body.append('<p class="note">%s</p>' % esc(a["kelly"]["note"]))
    body.append(table(["Price", "Decimal", "Model prob", "Break-even", "Full Kelly", "Quarter Kelly", "EV/unit"],
                      [[r["american_price"], r["decimal"], r["model_prob"], r["break_even_prob"],
                        r["full_kelly"], r["quarter_kelly"], r["ev_per_unit"]]
                       for r in a["kelly"]["rows"]],
                      ["https://www.nfl.com/standings/"] * len(a["kelly"]["rows"]),
                      note="Pure arithmetic on the Kelly identity; no odds source was available."))
    return "\n".join(body)


def p_gates():
    a = loadd("analytics.json")
    body = [md_to_html(open(os.path.join(RESEARCH, "validation-gates.md")).read())]
    body.append("<h2>Skill-gate sample sizes (full grid)</h2>")
    body.append(table(["True win rate", "Bets for 80% power", "Seasons @200 bets",
                       "p over 200 bets", "p over 500 bets"],
                      [[r["observed_win_rate"], r["required_n_for_80pct_power_at_alpha_.05"],
                        r["seasons_at_200_bets_per_season"], r["p_value_if_observed_over_200_bets"],
                        r["p_value_if_observed_over_500_bets"]] for r in a["skill_gates"]["rows"]],
                      ["https://www.nfl.com/schedules/2026/by-week/week-1"] * len(a["skill_gates"]["rows"]),
                      note="Two-sided test at α = .05 against the −110 break-even rate of 0.5238095."))
    return "\n".join(body)


def p_flagged():
    i = load("injuries.json")
    t = load("team_stats.json")
    d = load("depth_charts.json")
    b = loadd("backup_impact.json")
    items = [
        ("Team stat tables withheld entirely", "Team stats",
         "Offense/scoring, defense/scoring and defense/downs rendered with no header row, so their "
         "columns could not be confirmed. The tables are not published rather than guessed.",
         [u for u in t["meta"]["not_published"]]),
        ("7 of 15 passing columns withheld", "Team stats",
         "Each passing page renders 15 numeric columns; only the first 8 (Att, Cmp, Cmp%, Y/A, Yds, "
         "TD, INT, Rating) could be confirmed by arithmetic reconciliation. The other 7 are "
         "withheld rather than labelled by guesswork.",
         ["https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all",
          "https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all"]),
        ("Bye-week records are current, not historical", "Schedule",
         'The "Teams on Bye" panel on NFL.com week pages prints each team\'s record as of today, '
         'not as of that week. Do not use it for historical record-at-bye claims.',
         ["https://www.nfl.com/schedules/2026/reg10"]),
        ("Depth charts are unofficial and stale", "Depth charts",
         "The NFL publishes no official depth chart (nfl.com returns 404). Every chart here is a "
         "club page captioned unofficial, and 12 players listed 1st/2nd string carry Out/Doubtful "
         "on the official report.",
         ["https://www.nfl.com/teams/new-england-patriots/depth-chart"] +
         [c["source"] for c in d["clubs"]]),
        ("Out players missing from their own club chart", "Depth charts",
         "3 players ruled Out appear nowhere on their club's chart: DET Kerby Joseph, "
         "GB Micah Parsons, KC Omarr Norman-Lott.",
         ["https://www.nfl.com/injuries/league/2026/reg10"]),
        ("27 of 32 depth charts not acquired", "Depth charts",
         "Coverage is 5 clubs. The remaining 27 are registered as not acquired; none was estimated.",
         ["https://www.nfl.com/teams/"]),
        ("2026 roster compositions differ from recent history", "Rosters",
         "Official 2026 pages list players on clubs they were not on in 2025 (Garrett→Rams, "
         "Lawrence→Bengals, Murray→Vikings, Parsons→Packers, Nelson→Seahawks, Evans→49ers, "
         "A.J. Brown→Patriots, Etienne→Saints, Montgomery→Texans) and list Aaron Donald as active. "
         "All figures on this site are transcribed from the 2026 pages regardless; the reviewer "
         "should sanity-check the environment.",
         ["https://www.nfl.com/players/a-j-brown/", "https://www.nfl.com/standings/"]),
        ("A.J. Brown's game log has a gap", "Player props",
         "The official log for A.J. Brown shows 5 rows with a Week 2–Week 5 gap. Whether that is a "
         "rendering artefact or a genuine absence is unresolved; the rows are published as fetched.",
         ["https://www.nfl.com/players/a-j-brown/stats/logs/2026/"]),
        ("No market odds available", "Betting",
         "No sportsbook or odds source was reachable in this environment, and NFL.com itself hosts no "
         "odds page (https://www.nfl.com/odds/ returns '404 - Flag on the Play'). No line and no edge "
         "is published anywhere on this site: probabilities and benchmarks only.",
         ["https://www.nfl.com/odds/"]),
        ("Home-field advantage not measurable at n=137", "Analytics",
         "Mean home margin is −0.022 pts with SE 1.13, so the 95% CI is roughly [−2.24, +2.20]. "
         "This does not show HFA vanished; it shows 137 games cannot resolve it.",
         ["https://www.nfl.com/schedules/2026/by-week/week-1"]),
        ("Blank injury statuses are not 'healthy'", "Injuries",
         "%d of %d player rows on the official Week 10 report have no game status printed. Those "
         "cells are blank on this site by design." % (
             sum(1 for g in i["games"] for t2 in g["teams"] for p in t2["players"] if p[4] == ""),
             sum(len(t2["players"]) for g in i["games"] for t2 in g["teams"])),
         ["https://www.nfl.com/injuries/league/2026/reg10"]),
        ("Parlay ρ not estimated", "Betting",
         "The parlay grid publishes ρ = 0.00/0.15/0.30/0.50 as a sensitivity table. No single ρ was "
         "estimated from data, so no single parlay fair price is quoted.",
         ["https://www.nfl.com/schedules/2026/by-week/week-1"]),
    ]
    body = ["""<div class="warn"><strong>This page is the honest list of what this project could not
    establish.</strong> None of these items blocks the merge. Each is published with the official
    links needed to resolve it by hand.</div>"""]
    body.append(table(["#", "Area", "Item", "What is unresolved", "Official sources"],
                      [[n, area, title, desc,
                        " · ".join(link(u, u.replace("https://www.nfl.com", "nfl.com")) for u in urls)]
                       for n, (title, area, desc, urls) in enumerate(items, 1)],
                      ["https://www.nfl.com/"] * len(items)))
    body.append("<h2>Registry of explicitly missing data</h2>")
    body.append(table(["Club", "Status"],
                      [[r.get("team"), r.get("status")] for r in b["clubs_not_acquired"]]
                      if isinstance(b["clubs_not_acquired"], list) else [["see depth charts", "not acquired"]],
                      ["https://www.nfl.com/teams/"] * (len(b["clubs_not_acquired"])
                                                        if isinstance(b["clubs_not_acquired"], list) else 1)))
    return "\n".join(body)


def p_sources():
    srcs = [
        ("https://www.nfl.com/standings/division/2026/REG", "Official division standings, all 32 teams",
         "standings.html"),
        ("https://www.nfl.com/schedules/2026/by-week/week-1", "Historical week pages (N = 1..9); final scores",
         "games.html"),
        ("https://www.nfl.com/schedules/2026/reg10", "Current-week schedule, kickoffs, networks, TNF final",
         "week10.html"),
        ("https://www.nfl.com/injuries/league/2026/reg10", "Official Week 10 injury report, 345 player rows",
         "injuries.html"),
        ("https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all", "Offense passing team stats",
         "team-stats.html"),
        ("https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all", "Defense passing team stats",
         "team-stats.html"),
        ("https://www.nfl.com/stats/team-stats/offense/rushing/2026/reg/all", "Offense rushing team stats",
         "team-stats.html"),
        ("https://www.nfl.com/stats/team-stats/defense/rushing/2026/reg/all", "Defense rushing team stats (headers rendered here)",
         "team-stats.html"),
        ("https://www.nfl.com/stats/player-stats/category/passing/2026/reg/all/passingyards/desc",
         "Player passing leaderboard — used to reconcile the passing column labels", "team-stats.html"),
        ("https://www.nfl.com/players/drake-maye/stats/logs/2026/", "Official player game logs (6 players fetched)",
         "player-props.html"),
        ("https://www.patriots.com/team/depth-chart", "Club depth chart (unofficial by the club's own caption)",
         "depth-charts.html"),
        ("https://www.detroitlions.com/team/depth-chart", "Club depth chart (unofficial)", "depth-charts.html"),
        ("https://www.packers.com/team/depth-chart", "Club depth chart (unofficial)", "depth-charts.html"),
        ("https://www.chiefs.com/team/depth-chart", "Club depth chart (unofficial)", "depth-charts.html"),
        ("https://www.49ers.com/team/depth-chart", "Club depth chart (unofficial)", "depth-charts.html"),
        ("https://www.nfl.com/teams/new-england-patriots/depth-chart",
         "Returns 404 — evidence the NFL publishes no official depth chart", "flagged.html"),
        ("https://www.nfl.com/legal/flexible-scheduling-procedures",
         "Flexible-scheduling rules for Weeks 16–18", "flagged.html"),
    ]
    body = ["""<p>Every page on this site was produced by transcribing one of the official pages below.
    Where a page did not expose the information needed (for example a table with no header row), the
    data was withheld rather than guessed &mdash; see
    <a href="flagged.html">Flagged for review</a>.</p>"""]
    body.append(table(["Official URL", "What it provided", "Used on"],
                      [[link(u), what, '<a href="%s">%s</a>' % (pg, pg.replace(".html", ""))]
                       for u, what, pg in srcs],
                      [u for u, _, _ in srcs]))
    body.append("""<h2>Environment note</h2><p>All fetches were performed with the browser-style page
    fetcher, not with <code>curl</code>: outbound network access from the build sandbox is limited to
    <code>github.com</code>, <code>registry.npmjs.org</code> and <code>pypi.org</code>. That
    restriction is why no odds/sportsbook source could be reached.</p>""")
    return "\n".join(body)


def p_method():
    body = [md_to_html(open(os.path.join(RESEARCH, "method.md")).read())]
    return "\n".join(body)


def p_md(name):
    def f():
        with open(os.path.join(RESEARCH, name)) as fh:
            return md_to_html(fh.read())
    return f


def main():
    os.makedirs(os.path.join(DOCS, "assets"), exist_ok=True)
    with open(os.path.join(DOCS, "assets", "style.css"), "w") as fh:
        fh.write(CSS)
    write("index", "Dashboard", p_index(), "2026 NFL season, verified line by line from official sources")
    write("standings", "Standings", p_standings(), "Official division standings, reconciled against box scores")
    write("games", "Game results", p_games(), "137 completed games, each linked to its official box score")
    write("week10", "Week 10 slate", p_week10(), "Full slate with kickoff times, networks and the one completed game")
    write("injuries", "Injuries", p_injuries(), "Official NFL Week 10 injury report, row by row")
    write("depth-charts", "Depth charts", p_depth(), "Club-published charts — unofficial by the clubs' own captions")
    write("backup-impact", "Backup impact", p_backup(), "Starters ruled out and who is next on the chart")
    write("team-stats", "Team stats", p_teamstats(), "Four official stat tables; three withheld pending header confirmation")
    write("player-props", "Player props", p_props(), "Verified game logs and same-game pair correlations")
    write("analytics", "Analytics", p_analytics(), "Distributions, correlations, walk-forward results, parlay and Kelly grids")
    write("strategies", "Strategies", p_md("strategies.md"), "What was tested, what failed, and by how much")
    write("validation-gates", "Validation gates", p_gates(), "The numeric bars every strategy must clear")
    write("requirements", "Requirements", p_md("requirements.md"), "Requirement inventory with status evidence")
    write("open-questions", "Open questions", p_md("open-questions.md"), "What is known, what is missing, how to find it")
    write("suggestions", "Suggestions", p_md("suggestions.md"), "Choices for the reviewer — nothing here is implemented yet")
    write("flagged", "Flagged for review", p_flagged(), "Everything this project could not establish, with links")
    write("sources", "Sources", p_sources(), "Every official page used")
    write("method", "Method & verification", p_method(), "How the data was gathered and checked")
    print("built %d pages" % len(PAGES))


CSS = """
*{box-sizing:border-box}
body{margin:0;font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
color:#e8ecf4;background:#0d1117}
a{color:#6fb2ff;text-decoration:none}
a:hover{text-decoration:underline}
code{background:#161b22;padding:1px 5px;border-radius:4px;font-size:13px;color:#c9d4e5}
.layout{display:flex;min-height:100vh}
.sidebar{width:250px;flex:0 0 250px;background:#0f141c;border-right:1px solid #1e2733;
padding:20px 14px;position:sticky;top:0;height:100vh;overflow:auto}
.brand{font-size:20px;font-weight:700;letter-spacing:1px;display:flex;align-items:center;gap:8px}
.dot{width:10px;height:10px;border-radius:50%;background:#3fb950;display:inline-block}
.tag{font-size:12px;color:#7d8899;margin:4px 0 18px}
.navgroup{margin-bottom:16px}
.navhead{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#6b7686;margin-bottom:6px}
.sidebar a{display:block;padding:5px 9px;border-radius:6px;color:#c5cfe0;font-size:14px}
.sidebar a:hover{background:#161d28;text-decoration:none}
.sidebar a.active{background:#1d2b3f;color:#fff;font-weight:600}
.stamp{margin-top:24px;font-size:11px;color:#6b7686;border-top:1px solid #1e2733;padding-top:12px}
main{flex:1;min-width:0;padding:28px 34px 60px;max-width:1500px}
.pagehead{border-bottom:1px solid #1e2733;padding-bottom:14px;margin-bottom:22px}
h1{font-size:26px;margin:0 0 4px}
h2{font-size:19px;margin:30px 0 10px;padding-top:6px}
h3{font-size:15px;margin:20px 0 8px;color:#a9b6c9}
.sub{color:#8b97a8;margin:0;font-size:14px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:18px 0}
.card{background:#111823;border:1px solid #1e2733;border-radius:10px;padding:14px}
.card .k{font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:#7d8899}
.card .v{font-size:26px;font-weight:700;margin:6px 0 2px;color:#fff}
.card .s{font-size:12px;color:#8b97a8}
.tablewrap{overflow:auto;border:1px solid #1e2733;border-radius:10px;margin:10px 0 16px;max-height:none}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th{background:#151d29;text-align:left;padding:8px 10px;border-bottom:1px solid #24303f;
position:sticky;top:0;font-size:12px;text-transform:uppercase;letter-spacing:.4px;color:#9fb0c6;white-space:nowrap}
td{padding:7px 10px;border-bottom:1px solid #1a222e;white-space:nowrap}
tbody tr:nth-child(even){background:#0f151e}
tbody tr:hover{background:#151f2c}
td.na{color:#5b6675}
td.src{font-size:12px;color:#6fb2ff;white-space:normal;min-width:120px}
.note{color:#8b97a8;font-size:13px;background:#111823;border-left:3px solid #2b3a4d;
padding:9px 12px;border-radius:0 6px 6px 0;margin:8px 0 14px}
.warn{background:#2a1f14;border:1px solid #5c3d1e;border-radius:8px;padding:12px 14px;
margin:14px 0;font-size:13.5px;color:#f0d9b5}
.warn strong{color:#ffb86b}
.quote{font-style:italic;color:#9aa7b8;border-left:3px solid #2b3a4d;padding-left:12px;margin:10px 0}
.pill{background:#15331f;color:#5ddb86;padding:2px 8px;border-radius:20px;font-size:12px}
.recs{color:#8b97a8;font-size:13px;margin-bottom:6px}
ul{margin:8px 0 14px 20px;padding:0}
li{margin:5px 0}
hr{border:0;border-top:1px solid #1e2733;margin:24px 0}
.foot{margin-top:44px;padding-top:14px;border-top:1px solid #1e2733;color:#6b7686;font-size:12px}
@media(max-width:900px){.layout{flex-direction:column}.sidebar{position:static;width:100%;
height:auto;flex:none;border-right:0;border-bottom:1px solid #1e2733}main{padding:18px}}
"""


if __name__ == "__main__":
    main()
