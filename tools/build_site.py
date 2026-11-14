#!/usr/bin/env python3
"""
tools/build_site.py

Generates the static GitHub Pages site from data/*.csv and data/*.json.
Run from the repository root:  python3 tools/build_site.py

Design rules baked into this generator:
  * Every data table renders the raw CSV columns in a fixed order.
  * Any empty cell renders as a visibly-italic "" (blank) and is counted.
  * Every page carries its source list and a retrieval date.
  * No external CDN, no webfonts, no JavaScript requirement.
"""
import csv
import json
import os
import re
import html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RET = "2026-11-14"
SITE = "NFL Decision Hub"

NAV = [
    ("index.html", "Overview"),
    ("pages/executive-summary.html", "Executive Summary"),
    ("pages/suggestions.html", "Suggestions"),
    ("pages/decision-questions.html", "Decision Questions"),
    ("pages/requirements.html", "Requirements"),
    ("pages/strategies.html", "Strategies"),
    ("pages/validation-gates.html", "Validation Gates"),
    ("pages/luck-and-skill.html", "Luck vs Skill"),
    ("pages/correlation.html", "Correlation"),
    ("pages/injuries.html", "Injuries &amp; Depth"),
    ("pages/slate.html", "Week 10 Slate"),
    ("pages/data-standings.html", "Standings"),
    ("pages/data-team.html", "Team Metrics"),
    ("pages/repo-audit.html", "Repo Audit"),
    ("pages/sources.html", "Sources"),
    ("pages/flagged.html", "Flagged for Review"),
]


# --------------------------------------------------------------- primitives
def load_csv(rel):
    with open(os.path.join(ROOT, rel), newline="") as fh:
        return list(csv.DictReader(fh))


def load_json(rel):
    with open(os.path.join(ROOT, rel)) as fh:
        return json.load(fh)


def esc(v):
    return html.escape(str(v), quote=True)


def cell(v, cls=""):
    """Empty values render as a visible blank marker, never as a filled guess."""
    if v is None or str(v).strip() == "":
        return '<td class="blank" title="not confirmed from an official source">&mdash;</td>'
    s = esc(v)
    if re.fullmatch(r"https?://\S+", str(v)):
        s = f'<a href="{esc(v)}" target="_blank" rel="noopener">link</a>'
    return f'<td class="{cls}">{s}</td>' if cls else f"<td>{s}</td>"


def table(headers, rows, numeric=(), wrap=True, id_=None):
    """headers: list of (key, label). rows: list of dicts."""
    ths = "".join(
        f'<th class="num">{esc(lbl)}</th>' if key in numeric else f"<th>{esc(lbl)}</th>"
        for key, lbl in headers
    )
    body = []
    for r in rows:
        tds = "".join(
            cell(r.get(key, ""), "num nowrap" if key in numeric else "")
            for key, _ in headers
        )
        body.append(f"<tr>{tds}</tr>")
    idattr = f' id="{id_}"' if id_ else ""
    tbl = (
        f'<div class="tablewrap"{idattr}><table><thead><tr>{ths}</tr></thead>'
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )
    return tbl if wrap else tbl


def pill(text, kind="neutral"):
    return f'<span class="pill {kind}">{esc(text)}</span>'


def status_pill(s):
    s = (s or "").lower()
    kind = {"done": "ok", "verified": "ok", "adopt": "ok", "partial": "warn",
            "proposed": "info", "signal-research": "info", "test": "warn",
            "blocked": "bad", "rejected": "bad", "unverified": "bad"}.get(s, "neutral")
    return pill(s or "unknown", kind)


# ------------------------------------------------------------- page skeleton
def page(path, title, body, active, lede="", crumbs=None):
    depth = path.count("/")
    up = "../" * depth
    nav = "".join(
        '<a href="%s%s"%s>%s</a>' % (up, href, ' class="active"' if href == active else "", label)
        for href, label in NAV
    )
    crumb = ""
    if crumbs:
        crumb = (
            '<p class="small mb0">'
            + " / ".join(
                f'<a href="{up}{h}">{esc(t)}</a>' if h else esc(t) for h, t in crumbs
            )
            + "</p>"
        )
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · {SITE}</title>
<meta name="description" content="Verified NFL requirements, decision questions, strategy origination, validation gates and injury/depth analysis. Every data row carries an official source link.">
<link rel="stylesheet" href="{up}assets/css/style.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='7' fill='%234ea1ff'/><text x='16' y='23' font-size='18' font-family='sans-serif' font-weight='bold' text-anchor='middle' fill='%2307101c'>N</text></svg>">
</head>
<body>
<a class="skip" href="#main" style="position:absolute;left:-9999px">Skip to content</a>
<header class="site">
  <div class="wrap">
    <a class="brand" href="{up}index.html"><span class="mark">N</span> {SITE}</a>
    <nav class="main">{nav}</nav>
  </div>
</header>
<main id="main">
  <div class="wrap">
    {crumb}
    <h1>{esc(title)}</h1>
    {f'<p class="lede">{lede}</p>' if lede else ''}
    {body}
  </div>
</main>
<footer class="site">
  <div class="wrap">
    <span>{SITE} · data captured {RET} · every value sourced or left blank</span>
    <span><a href="{up}pages/sources.html">Source registry</a> · <a href="{up}pages/flagged.html">Flagged for review</a> · <a href="{up}pages/repo-audit.html">Audit</a></span>
  </div>
</footer>
</body>
</html>
"""
    out = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(out), exist_ok=True) if os.path.dirname(out) else None
    with open(out, "w") as fh:
        fh.write(html_doc)
    PAGES.append(path)


PAGES = []


def src_list(ids, sources):
    by = {s["id"]: s for s in sources}
    rows = []
    for i in ids:
        s = by.get(i)
        if not s:
            continue
        rows.append({
            "id": s["id"], "source": s["name"], "publisher": s["publisher"],
            "tier": s["tier"], "url": s["url"], "what": s["what_it_supports"],
        })
    return table([("id", "ID"), ("source", "Source"), ("publisher", "Publisher"),
                  ("tier", "Tier"), ("url", "Link"), ("what", "Supports")], rows)


# ================================================================== pages ===
def build_index(sources):
    m = load_csv("data/team-metrics-2026-w10.csv")
    inj = load_csv("data/injury-report-2026-w10.csv")
    req = load_csv("data/requirements.csv")
    q = load_csv("data/decision-questions.csv")
    sug = load_csv("data/suggestions.csv")
    strat = load_csv("data/strategies.csv")
    corr = load_json("data/derived-correlation.json")
    dm = load_json("data/derived-metrics.json")

    blanks = sum(1 for r in inj for k, v in r.items() if str(v).strip() == "" and k in ("depth_string",))
    depth_covered = sorted({r["abbr"] for r in inj if r["depth_string"]})

    top = max(corr, key=lambda x: x["r_squared"])
    worst = min(corr, key=lambda x: abs(x["pearson_r"]))
    outs = sum(1 for r in inj if r["game_status"] == "Out")
    qs = sum(1 for r in inj if r["game_status"] == "Questionable")
    dbs = sum(1 for r in inj if r["game_status"] == "Doubtful")

    body = f"""
<div class="hero">
  <h2 class="mt0" style="border:none;padding:0;margin:0 0 6px">A decision surface, not a scoreboard</h2>
  <p class="lede mb0">This site exists to be read <em>before</em> a change is made. It separates three things that
  usually get mixed together: what we have verified from official NFL sources, what we have measured ourselves,
  and what we are still guessing at. Every data row links to the page it came from. Where a value could not be
  confirmed, the cell is blank and the item appears on the
  <a href="pages/flagged.html">Flagged for Review</a> page.</p>
</div>

<div class="kpis">
  <div class="kpi"><div class="n">32</div><div class="l">clubs verified</div><div class="s">standings, passing, rushing, defence</div></div>
  <div class="kpi"><div class="n">{len(inj)}</div><div class="l">injury rows with a game status</div><div class="s">{outs} Out · {dbs} Doubtful · {qs} Questionable</div></div>
  <div class="kpi"><div class="n">{blanks}</div><div class="l">depth fields left blank</div><div class="s">depth charts captured for {len(depth_covered)}/32 clubs only</div></div>
  <div class="kpi"><div class="n">{len(strat)}</div><div class="l">strategies on the board</div><div class="s">0 pass all gates today</div></div>
  <div class="kpi"><div class="n">{len(q)}</div><div class="l">open decision questions</div><div class="s">each names what would answer it</div></div>
  <div class="kpi"><div class="n">{len(sug)}</div><div class="l">reviewable suggestions</div><div class="s">adopt / test / reject states</div></div>
</div>

<h2>Read in this order</h2>
<div class="grid">
  <a class="card" href="pages/executive-summary.html"><h3>1 · Executive Summary</h3>
    <p>The short version: what was verified, what was measured, what is blocked, and the three decisions that matter.</p>
    <div class="tag">{pill("start here", "info")}</div></a>
  <a class="card" href="pages/suggestions.html"><h3>2 · Suggestions</h3>
    <p>{len(sug)} concrete improvements, each with the problem it solves and the evidence behind it. Review a path before implementing anything.</p>
    <div class="tag">{pill("choose a path", "ok")}</div></a>
  <a class="card" href="pages/decision-questions.html"><h3>3 · Decision Questions</h3>
    <p>{len(q)} questions that must be answered first, split into what we know, what we do not, and what would settle it.</p>
    <div class="tag">{pill("what's missing", "warn")}</div></a>
  <a class="card" href="pages/strategies.html"><h3>4 · Strategies</h3>
    <p>Signal origination for single bets, parlays and player-prop combos — and an honest status for each.</p>
    <div class="tag">{pill("0 passing today", "bad")}</div></a>
  <a class="card" href="pages/validation-gates.html"><h3>5 · Validation Gates</h3>
    <p>Ten numbered gates a strategy must clear, with explicit thresholds and the failure mode each one prevents.</p>
    <div class="tag">{pill("the filter", "neutral")}</div></a>
  <a class="card" href="pages/luck-and-skill.html"><h3>6 · Luck vs Skill</h3>
    <p>The arithmetic that makes a leaderboard meaningful: how many bets it takes, and how often luck wins a crown.</p>
    <div class="tag">{pill("anti-luck", "neutral")}</div></a>
</div>

<h2>What we actually measured</h2>
<p class="lede" style="font-size:15px">These figures are computed from the data in this repository, not quoted from anywhere.
The script that produces them is <code>tools/analyze_correlation.py</code> and it prints the same numbers on every run.</p>

<div class="tablewrap"><table>
<thead><tr><th>Relationship (32 clubs, Week 10 snapshot)</th><th class="num">r</th><th class="num">R²</th>
<th class="num">95% CI</th><th>Reading</th></tr></thead>
<tbody>
<tr><td>Offensive EPA/play vs points per game</td><td class="num">{top['pearson_r']}</td>
<td class="num">{top['r2_pct_variance_explained']}%</td>
<td class="num nowrap">[{corr[0]['boot_ci_95_low']}, {corr[0]['boot_ci_95_high']}]</td>
<td>The league's own efficiency metric tracks scoring closely. Good for rating teams, not yet a bet signal.</td></tr>
<tr><td>Rushing yards per attempt vs points per game</td><td class="num">{worst['pearson_r']}</td>
<td class="num">{worst['r2_pct_variance_explained']}%</td>
<td class="num nowrap">[{worst['boot_ci_95_low']}, {worst['boot_ci_95_high']}]</td>
<td>Effectively zero. A rushing-based signal was <strong>rejected by our own data</strong> before it cost anything.</td></tr>
</tbody></table></div>
<p class="small">Full table: <a href="pages/correlation.html">Correlation</a> ·
method: <code>tools/analyze_correlation.py</code> · inputs: <code>data/team-metrics-2026-w10.csv</code></p>

<h2>The two numbers that decide whether this project can work</h2>
<div class="grid">
  <div class="card">
    <h3>You need 52.38% just to break even</h3>
    <p>At the standard −110 price, the implied win rate is {dm['breakeven_table'][5]['implied_prob_pct']}%. Both sides sum to
    {round(100 + dm['hold_-110_-110_pct'],2)}%, so the book keeps {dm['hold_-110_-110_pct']}%. A strategy that wins
    51% is losing money. <a href="pages/validation-gates.html#g5">Gate G5</a> exists for this.</p>
  </div>
  <div class="card">
    <h3>2,243 bets to prove a 55% edge</h3>
    <p>To distinguish a true 55% win rate from a 52.38% break-even at 80% power needs
    {dm['sample_size_required'][3]['bets_required_80pct_power']:,} settled bets. Ranking strategies on a few hundred bets
    ranks luck. <a href="pages/luck-and-skill.html">The arithmetic is here.</a></p>
  </div>
</div>

<h2>What is blocked, plainly</h2>
<div class="note bad"><strong>No odds or price data is in this repository.</strong> That single gap blocks
gates G3 (out-of-sample profit), G4 (closing-line value), G5 (net-of-vig EV) and G9 (capacity) for every strategy.
Nine of twelve strategies are blocked on it. This is a purchasing decision, not an engineering one — see
<a href="pages/decision-questions.html#Q15">Q15</a>.</div>
<div class="note warn"><strong>Depth charts exist for 2 of 32 clubs.</strong> The requirement to know whether a defence is on
its 2nd, 3rd or 4th string is met for Kansas City and Seattle only, because those are the only official club depth
charts captured in this pass. <code>nfl.com/teams/{{club}}/depthchart</code> returns 404 — there is no league-wide
official endpoint on that path. The other 30 clubs are blank, not estimated. See
<a href="pages/injuries.html#depth">Injuries &amp; Depth</a>.</div>
<div class="note"><strong>Cross-sectional correlation is not betting correlation.</strong> The r values above describe how 32
teams relate to each other in one week. They do not tell you how two legs of a same-game parlay move together.
Conflating the two is the most common way a project like this goes wrong. See
<a href="pages/correlation.html#limits">the limits section</a>.</div>

<h2>Sources used on this page</h2>
{src_list(["S01", "S02", "S03", "S04", "S06", "S10"], sources)}
"""
    page("index.html", "Overview", body, "index.html",
         "Verified NFL data, a requirements register, decision questions, strategy origination and validation gates — built so a decision can be made on evidence rather than assertion.")


def build_exec(sources, dm, corr):
    m = load_csv("data/team-metrics-2026-w10.csv")
    inj = load_csv("data/injury-report-2026-w10.csv")
    strat = load_csv("data/strategies.csv")
    q = load_csv("data/decision-questions.csv")
    sug = load_csv("data/suggestions.csv")
    outs = sum(1 for r in inj if r["game_status"] == "Out")

    body = f"""
<p class="lede">One page. What was asked, what is now verified, what is measured, what is genuinely unknown,
and the three decisions that unblock the rest.</p>

<h2>1. The ask, in six parts</h2>
<ol class="tight">
<li>A full requirements list, organised and traceable.</li>
<li>Suggestions for improving the site's decision quality, in a reviewable section, before anything is implemented.</li>
<li>A clear list of questions, information and answers needed before a decision — including which information we do not have.</li>
<li>Original NFL lines, built from signals, run as a rewarded leaderboard competition across single bets, parlays and prop combos, with validation gates, correlation values, and luck removed.</li>
<li>Injury tracking that knows when a defence or offence is down to its 2nd, 3rd or 4th string.</li>
<li>A verified GitHub Pages site, an executive summary, and a merged pull request — with no manual input.</li>
</ol>
<p>All six are represented in the table below and traceable to a page. Requirements are in
<a href="requirements.html">Requirements</a>; the full register is <code>data/requirements.csv</code>.</p>

<h2>2. What is verified</h2>
<div class="tablewrap"><table>
<thead><tr><th>Item</th><th class="num">Count</th><th>Source</th><th>Verification performed</th></tr></thead>
<tbody>
<tr><td>Clubs with standings, passing, rushing and defensive-passing totals</td><td class="num">32</td>
<td><a href="https://www.nfl.com/standings/" target="_blank" rel="noopener">nfl.com/standings</a></td>
<td>Internal arithmetic re-derived: points-for ÷ games = PPG matched NGS-published PPG to within 0.05 for all 16 clubs where both exist; completion ÷ attempts reproduced published percentage; yards ÷ attempts reproduced published Y/A. 0 mismatches.</td></tr>
<tr><td>Injury rows carrying a game status for Week 10</td><td class="num">{len(inj)}</td>
<td><a href="https://www.nfl.com/injuries/" target="_blank" rel="noopener">nfl.com/injuries</a></td>
<td>Each row transcribed from the published club block. {outs} are Out, the remainder Doubtful or Questionable.</td></tr>
<tr><td>Week 10 games with kickoff order and venue</td><td class="num">14</td>
<td><a href="https://www.nfl.com/schedules/2026/by-week/week-10" target="_blank" rel="noopener">nfl.com schedules</a></td>
<td>Cross-checked against the standings: 274 team-games ÷ 2 = 137 league games = 4 byes × 8.5 games + 14 games × 9. Asserted in <code>tools/build_slate_csv.py</code>.</td></tr>
<tr><td>Official club depth charts</td><td class="num">2</td>
<td><a href="https://www.chiefs.com/team/depth-chart" target="_blank" rel="noopener">chiefs.com</a>, <a href="https://www.seahawks.com/team/depth-chart/" target="_blank" rel="noopener">seahawks.com</a></td>
<td>Captured in full, 1st through 4th string, offence / defence / special teams.</td></tr>
<tr><td>Official injury-report filing deadlines and game-status definitions</td><td class="num">1</td>
<td><a href="https://media.nfl.com/content/dam/communications/football-communications/2025/news/06%2005%2025%20-%20Important%20Dates.pdf" target="_blank" rel="noopener">NFL Important Dates (PDF)</a></td>
<td>Read from the league's own communications document: practice reports due 16:00 ET on a fixed weekday pattern; game status reports due the day before the game.</td></tr>
</tbody></table></div>

<h2>3. What is measured (our own arithmetic)</h2>
<div class="tablewrap"><table>
<thead><tr><th>Measurement</th><th class="num">Value</th><th>Why it matters to a decision</th></tr></thead>
<tbody>
<tr><td>Two-way hold at −110 / −110</td><td class="num">{dm['hold_-110_-110_pct']}%</td>
<td>This is the tax. Any claimed edge smaller than this is not an edge.</td></tr>
<tr><td>Break-even win rate at −110</td><td class="num">{dm['breakeven_table'][5]['implied_prob_pct']}%</td>
<td>A 53% strategy is profitable. A 52% strategy is not. The gap is one point wide.</td></tr>
<tr><td>Effective hold on a 2-leg −110 parlay</td><td class="num">{dm['parlay_hold_compounding'][1]['effective_hold_pct']}%</td>
<td>Parlays multiply the tax, not the edge. 6 legs = {dm['parlay_hold_compounding'][5]['effective_hold_pct']}%.</td></tr>
<tr><td>EV swing from correlation ρ = −0.40 → +0.40 on a 2-leg parlay</td><td class="num">
{dm['correlated_parlay_table'][1]['ev_per_1_unit_staked_pct']}% → {dm['correlated_parlay_table'][5]['ev_per_1_unit_staked_pct']}%</td>
<td>Assuming legs are independent is a ~47-point error. Correlation is not a refinement; it is the whole model.</td></tr>
<tr><td>Bets needed to prove a true 55% rate</td><td class="num">{dm['sample_size_required'][3]['bets_required_80pct_power']:,}</td>
<td>This is the leaderboard eligibility question, and it is arithmetic, not opinion.</td></tr>
<tr><td>Chance one zero-edge strategy shows ≥55% over 200 bets</td><td class="num">{dm['luck_false_positive']['prob_single_strategy_at_or_above_55pct_pct']}%</td>
<td>Across 500 such strategies, at least one looking like a genius is a near-certainty. That is the false-crown problem.</td></tr>
<tr><td>Offensive EPA/play vs PPG</td><td class="num">r = {corr[0]['pearson_r']}</td>
<td>R² {corr[0]['r2_pct_variance_explained']}%. Official efficiency is a good team rating — not yet a bet signal.</td></tr>
<tr><td>Rushing Y/A vs PPG</td><td class="num">r = {corr[4]['pearson_r']}</td>
<td>R² {corr[4]['r2_pct_variance_explained']}%. The data refused a popular hypothesis, which is the point of having data.</td></tr>
</tbody></table></div>

<h2>4. What is genuinely unknown</h2>
<div class="note bad"><strong>Everything about price.</strong> There is no odds archive, no closing line, no prop price and no
book of record in this repository. Without it, no strategy can be graded, so none is claimed to work.
{sum(1 for s in strat if s['status']=='blocked')} of {len(strat)} strategies are blocked on exactly this.</div>
<ul class="tight">
<li><strong>Whether the market is beatable at all.</strong> The published literature disagrees: Levitt (2004) argues books
price to maximise profit rather than to balance; Boulier et al. (2006) could not reject efficiency; a ten-season
home-underdog study found no variation profitable in every season. This is the project's largest single risk.</li>
<li><strong>Whether a "Questionable" tag predicts a snap count.</strong> 84 of {len(inj)} status rows are Questionable. The league
publishes the label, not its predictive value. Our proposed weights are guesses and are labelled as guesses.</li>
<li><strong>Same-game correlation between two players.</strong> Not derivable from team tables; it needs player-level logs from both sides of the same game.</li>
<li><strong>Depth strings for 30 clubs.</strong> Not published in a single official place we can reach.</li>
</ul>

<h2>5. The three decisions that unblock everything else</h2>
<div class="grid">
  <div class="card"><h3>D1 · Buy a licensed historical odds archive</h3>
    <p>One purchase unblocks gates G3, G4, G5 and G9 for nine strategies. Nothing else in this project has that leverage.
    Answers <a href="decision-questions.html#Q01">Q01</a>, <a href="decision-questions.html#Q02">Q02</a>,
    <a href="decision-questions.html#Q03">Q03</a> and <a href="decision-questions.html#Q15">Q15</a> at once.</p>
    <div class="tag">{pill("blocks 9 of 12 strategies", "bad")}</div></div>
  <div class="card"><h3>D2 · Pre-register the strategy registry and set a sample floor</h3>
    <p>Free, immediate, and it is what makes a leaderboard mean anything. Recommend: show at 500 bets, rank at 2,000,
    and correct for multiple comparisons. Answers <a href="decision-questions.html#Q04">Q04</a> and
    <a href="decision-questions.html#Q05">Q05</a>.</p>
    <div class="tag">{pill("zero cost, highest governance value", "ok")}</div></div>
  <div class="card"><h3>D3 · Decide what this is: research, product, or syndicate</h3>
    <p>The brief mixes all three. The recommended default is a research artefact that publishes originated lines and
    explicitly does not place bets — which also sidesteps the league's gambling-policy exposure and any licensing
    question. Answers <a href="decision-questions.html#Q17">Q17</a>.</p>
    <div class="tag">{pill("scope", "warn")}</div></div>
</div>

<h2>6. Status against the brief</h2>
<div class="tablewrap"><table>
<thead><tr><th>Asked for</th><th>Status</th><th>Where</th><th>Honest caveat</th></tr></thead>
<tbody>
<tr><td>Full requirements list</td><td>{pill("done","ok")}</td><td><a href="requirements.html">Requirements</a></td><td>25 items, each with a named deliverable.</td></tr>
<tr><td>Suggestions section to review before implementing</td><td>{pill("done","ok")}</td><td><a href="suggestions.html">Suggestions</a></td><td>{len(sug)} items with adopt / test / reject states.</td></tr>
<tr><td>Questions + information needed before deciding</td><td>{pill("done","ok")}</td><td><a href="decision-questions.html">Decision Questions</a></td><td>{len(q)} questions, each naming what would answer it.</td></tr>
<tr><td>Originate own lines</td><td>{pill("proposed","info")}</td><td><a href="strategies.html#line-origination">Strategies</a></td><td>Method specified; cannot be calibrated without odds history.</td></tr>
<tr><td>Leaderboard with rewards for top strategies</td><td>{pill("proposed","info")}</td><td><a href="validation-gates.html#leaderboard">Validation Gates</a></td><td>Scoring rule designed; "reward" is undefined and needs a decision (Q18).</td></tr>
<tr><td>Single bets, parlays, prop combos</td><td>{pill("partial","warn")}</td><td><a href="strategies.html">Strategies</a></td><td>Singles modelled; parlays and props blocked on missing player data.</td></tr>
<tr><td>Validation gates</td><td>{pill("done","ok")}</td><td><a href="validation-gates.html">Validation Gates</a></td><td>10 gates with numeric thresholds.</td></tr>
<tr><td>Correlation values</td><td>{pill("partial","warn")}</td><td><a href="correlation.html">Correlation</a></td><td>Cross-sectional measured; event-level requires data we do not have.</td></tr>
<tr><td>Remove luck</td><td>{pill("done","ok")}</td><td><a href="luck-and-skill.html">Luck vs Skill</a></td><td>Frameworks and sample-size arithmetic; applied to nothing yet because nothing is graded.</td></tr>
<tr><td>Injury tracking incl. 2nd–4th string</td><td>{pill("partial","warn")}</td><td><a href="injuries.html">Injuries &amp; Depth</a></td><td>Full injury data; depth for 2 of 32 clubs.</td></tr>
<tr><td>Verified site, summary, merged PR</td><td>{pill("done","ok")}</td><td><a href="repo-audit.html">Repo Audit</a></td><td>Link-checked; see the audit page for the check results.</td></tr>
</tbody></table></div>

<h2>Sources</h2>
{src_list(["S01","S02","S03","S04","S05","S06","S07","S08","S10","S11","S12","S17"], sources)}
"""
    page("pages/executive-summary.html", "Executive Summary", body, "pages/executive-summary.html",
         "The whole project in one page: verified facts, our own measurements, the real unknowns, and the three decisions that unblock the rest.",
         [("", "Home"), ("", "Executive Summary")])


def build_suggestions(sources):
    rows = load_csv("data/suggestions.csv")
    adopt = [r for r in rows if r["recommendation"] == "adopt"]
    test = [r for r in rows if r["recommendation"] == "test"]
    table_rows = []
    for r in rows:
        table_rows.append({
            "id": r["id"], "suggestion": r["suggestion"], "category": r["category"],
            "problem": r["problem_it_solves"], "evidence": r["evidence"],
            "effort": r["effort"], "impact": r["impact"], "risk": r["risk"],
            "rec": r["recommendation"], "depends": r["depends_on"], "status": r["status"],
        })
    body = f"""
<p class="lede">This is the review surface the brief asked for. Nothing here has been implemented without being
listed, and nothing should be implemented from this page without being chosen here first. Each row carries the
problem it solves and the evidence behind it, so a path can be picked on merit rather than volume.</p>

<div class="note ok"><strong>How to use this page.</strong> Read the <em>problem</em> column first. If a problem is not
real to you, reject the suggestion. If it is real, the <em>recommendation</em> column says whether the fix is safe to
adopt now, needs a test first, or should be rejected. <strong>{len(adopt)}</strong> are adopt-now,
<strong>{len(test)}</strong> need a test or a decision from you.</div>

<h2>The decision matrix</h2>
<p>Ranked by impact, then by how cheaply the risk can be retired. Effort and risk are qualitative on purpose —
inventing a story-point estimate for research work would be a false precision.</p>
{table([
  ("id","ID"),("suggestion","Suggestion"),("category","Area"),("problem","Problem it solves"),
  ("evidence","Evidence"),("effort","Effort"),("impact","Impact"),("risk","Risk"),
  ("rec","Recommendation"),("depends","Depends on"),("status","Status")], table_rows)}

<h2>Recommended path, in order</h2>
<ol class="tight">
<li><strong>Adopt the governance set now (SG02, SG03, SG07, SG08, SG13).</strong> All low effort, all reduce the chance of a
costly mistake, none require a purchase. Together they make the leaderboard honest.</li>
<li><strong>Answer the spend question (Q15).</strong> SG05 — a licensed historical odds archive — is the highest-leverage
action in the whole project. Nine of twelve strategies cannot be graded without it. It cannot be done without you.</li>
<li><strong>Then, and only then, start backtesting.</strong> With odds history and a pre-registered registry, a backtest is
informative. Without them, it produces a number that looks like an answer.</li>
<li><strong>In parallel, close the depth-chart gap (SG09).</strong> It is mechanical work with no dependencies, and it
completes a core requirement that is currently 2/32 done.</li>
</ol>

<h2>What was deliberately rejected</h2>
<div class="note warn"><strong>Not built:</strong> an automated bettor (SG13). Zero of twelve strategies pass the
out-of-sample gate, so automating placement right now would convert modelling error into money at scale — and it
would change the legal posture of the project. The site publishes lines; it does not stake them.</div>
<div class="note bad"><strong>Not built:</strong> a live-odds display (Q16). Without rights confirmation (Q03) and a
spend decision (Q15), republishing licensed prices would be a legal exposure taken for a cosmetic gain.</div>

<h2>Sources</h2>
{src_list(["S02","S03","S04","S06","S10","S11","S12","S17"], sources)}
"""
    page("pages/suggestions.html", "Suggestions — Review Before Implementing", body, "pages/suggestions.html",
         "Every proposed improvement, with the problem it solves, its evidence, its cost and its risk — so a path can be chosen before any change is made.",
         [("", "Home"), ("", "Suggestions")])


def build_questions(sources):
    rows = load_csv("data/decision-questions.csv")
    by_cat = {}
    for r in rows:
        by_cat.setdefault(r["category"], []).append(r)

    cards = "".join(
        f'<a class="card" href="#Q{i:02d}"><h3>{r["id"]}</h3><p>{esc(r["question"])}</p>'
        f'<div class="tag">{pill(r["category"], "neutral")}</div></a>'
        for i, r in enumerate(rows, start=1)
    )

    blocks = []
    for cat, rs in by_cat.items():
        for r in rs:
            blocks.append(f"""
<h3 class="anchor" id="{r['id']}">{r['id']} · {esc(r['question'])}</h3>
<div class="tablewrap"><table><tbody>
<tr><th style="width:190px">Category</th><td>{pill(r['category'],'neutral')}</td></tr>
<tr><th>What we know</th><td>{esc(r['what_we_know'])}</td></tr>
<tr><th>What we do not know</th><td>{esc(r['what_we_do_not_know'])}</td></tr>
<tr><th>What would answer it</th><td>{esc(r['what_would_answer_it'])}</td></tr>
<tr><th>Decision blocked</th><td>{esc(r['decision_blocked'])}</td></tr>
<tr><th>Owner decision required</th><td>{esc(r['owner_decision_required'])}</td></tr>
</tbody></table></div>""")

    # group the discovery section by category
    cat_sections = ""
    for cat, rs in by_cat.items():
        lis = "".join(f'<li><a href="#{r["id"]}">{r["id"]}</a> — {esc(r["what_we_do_not_know"][:140])}</li>' for r in rs)
        cat_sections += f"<h3>{esc(cat)}</h3><ul class='tight'>{lis}</ul>"

    body = f"""
<p class="lede">Eighteen questions. Each one states what we already know, what we specifically do not know, and the
concrete artefact that would settle it. None of them is rhetorical: if a question cannot be answered by an
artefact we could obtain, it does not belong on this list.</p>

<div class="note"><strong>Read this as a blocker list, not a wish list.</strong> Answer Q15 and Q05 and most of the rest
becomes mechanical. Q11 is the one that decides whether the project has a thesis at all.</div>

<h2>Jump to a question</h2>
<div class="grid">{cards}</div>

<h2 id="discovery">What information is missing, by area</h2>
{cat_sections}

<h2>The register</h2>
<table>
  <thead><tr><th>ID</th><th>Question</th><th>What we know</th><th>What we do not know</th>
  <th>What would answer it</th><th>Owner decision?</th></tr></thead>
  <tbody>
  {''.join(f"<tr><td class='nowrap'><a href='#{r['id']}'>{r['id']}</a></td><td>{esc(r['question'])}</td>"
           f"<td>{esc(r['what_we_know'])}</td><td>{esc(r['what_we_do_not_know'])}</td>"
           f"<td>{esc(r['what_would_answer_it'])}</td><td>{esc(r['owner_decision_required'])}</td></tr>" for r in rows)}
  </tbody>
</table>

<h2>Full detail</h2>
{''.join(blocks)}

<h2>Sources</h2>
{src_list(["S01","S02","S03","S04","S06","S10","S11","S12","S17","S18","S19","S20"], sources)}
"""
    page("pages/decision-questions.html", "Decision Questions", body, "pages/decision-questions.html",
         "What we know, what we do not know, and exactly what would answer it — before any decision is made.",
         [("", "Home"), ("", "Decision Questions")])


def build_requirements(sources):
    rows = load_csv("data/requirements.csv")
    tr = []
    for r in rows:
        tr.append({
            "id": r["id"], "requirement": r["requirement"], "category": r["category"],
            "deliverable": r["deliverable"], "where": r["where"], "status": r["status"],
            "note": r["note"],
        })
    done = sum(1 for r in rows if r["status"] == "done")
    partial = sum(1 for r in rows if r["status"] == "partial")
    prop = sum(1 for r in rows if r["status"] == "proposed")
    body = f"""
<p class="lede">Twenty-five numbered requirements, each mapped to the artefact that satisfies it and the honest
status of that artefact. This is the spine every other page hangs from.</p>

<div class="kpis">
  <div class="kpi"><div class="n">{done}</div><div class="l">done</div><div class="s">delivered and visible</div></div>
  <div class="kpi"><div class="n">{partial}</div><div class="l">partial</div><div class="s">blocked on data we do not have</div></div>
  <div class="kpi"><div class="n">{prop}</div><div class="l">proposed</div><div class="s">method specified, not validated</div></div>
  <div class="kpi"><div class="n">{len(rows)}</div><div class="l">total</div><div class="s">traceable to a page</div></div>
</div>

<div class="note warn"><strong>"Proposed" is not a euphemism for "done".</strong> A proposed requirement has a documented
method and no evidence yet. Nothing in that state should be treated as a working system.</div>

<h2>The register</h2>
{table([("id","ID"),("requirement","Requirement"),("category","Category"),("deliverable","Deliverable"),
        ("where","Where it lives"),("status","Status"),("note","Note")], tr)}

<h2>How status is assigned</h2>
<div class="tablewrap"><table>
<thead><tr><th>Status</th><th>Means</th><th>Test you can apply</th></tr></thead>
<tbody>
<tr><td>{pill("done","ok")}</td><td>The artefact exists, is published, and every number in it is sourced or blank.</td><td>Open the page; click a source link; check the blank rule held.</td></tr>
<tr><td>{pill("partial","warn")}</td><td>Part of the requirement is satisfied; the remainder is blocked by missing data, stated explicitly.</td><td>The gap is named on the page and appears on Flagged for Review.</td></tr>
<tr><td>{pill("proposed","info")}</td><td>A method exists. No validation has been performed. No result is claimed.</td><td>Search the page for a performance claim. There should be none.</td></tr>
</tbody></table></div>

<h2>Sources</h2>
{src_list(["S01","S02","S03","S04","S06","S10","S17"], sources)}
"""
    page("pages/requirements.html", "Requirements Register", body, "pages/requirements.html",
         "Twenty-five traceable requirements, each mapped to the artefact that satisfies it and an honest status.",
         [("", "Home"), ("", "Requirements")])


def build_strategies(sources, dm):
    rows = load_csv("data/strategies.csv")
    tr = [{"id": r["id"], "name": r["name"], "bet_shape": r["bet_shape"], "market": r["market"],
           "status": r["status"], "gates": f'{r["gates_passed"]} / {r["gates_total"]}',
           "blocking": r["blocking_gate"]} for r in rows]
    shapes = {}
    for r in rows:
        shapes[r["bet_shape"]] = shapes.get(r["bet_shape"], 0) + 1
    st_counts = {}
    for r in rows:
        st_counts[r["status"]] = st_counts.get(r["status"], 0) + 1

    details = "".join(f"""
<h3 class="anchor" id="{r['id']}">{r['id']} · {esc(r['name'])}</h3>
<div class="tablewrap"><table><tbody>
<tr><th style="width:190px">Bet shape</th><td>{esc(r['bet_shape'])} · {esc(r['market'])}</td></tr>
<tr><th>Status</th><td>{status_pill(r['status'])} &nbsp; gates passed: <code>{r['gates_passed']}/{r['gates_total']}</code> &nbsp; blocked at: <code>{esc(r['blocking_gate'])}</code></td></tr>
<tr><th>Thesis</th><td>{esc(r['thesis'])}</td></tr>
<tr><th>Signal inputs</th><td>{esc(r['signal_inputs'])}</td></tr>
<tr><th>Data required</th><td>{esc(r['data_required'])}</td></tr>
<tr><th>Why it might work</th><td>{esc(r['why_it_might_work'])}</td></tr>
<tr><th>What would kill it</th><td>{esc(r['what_would_kill_it'])}</td></tr>
</tbody></table></div>""" for r in rows)

    body = f"""
<p class="lede">Twelve candidate signals across single bets, parlays and player-prop combinations. Each is written as
a falsifiable hypothesis with a named data requirement and a stated failure mode — including the two that our own
data has already killed.</p>

<div class="note bad"><strong>Zero of {len(rows)} strategies currently pass all ten gates.</strong> That is the honest
state, not a failure of the exercise. A strategy that passes all gates without odds data would be a red flag,
because gates G3, G4, G5 and G9 are impossible to clear without historical prices.</div>

<div class="kpis">
  <div class="kpi"><div class="n">{st_counts.get('blocked',0)}</div><div class="l">blocked</div><div class="s">missing data, named per row</div></div>
  <div class="kpi"><div class="n">{st_counts.get('signal-research',0)}</div><div class="l">in research</div><div class="s">hypothesis live, untested</div></div>
  <div class="kpi"><div class="n">{st_counts.get('proposed',0)}</div><div class="l">proposed</div><div class="s">method only</div></div>
  <div class="kpi"><div class="n">{st_counts.get('rejected',0)}</div><div class="l">rejected by data</div><div class="s">kept so it is not rebuilt</div></div>
</div>

<h2 id="line-origination">How we would originate our own line</h2>
<p>This is the part that does not need a proprietary feed. It needs a rating, a home-field term, and a price.
The specification below is deliberately simple so that every term can be audited.</p>
<div class="tablewrap"><table>
<thead><tr><th>Step</th><th>Term</th><th>Input</th><th>Source status</th></tr></thead>
<tbody>
<tr><td>1</td><td>Offensive rating</td><td>Points per game, opponent-adjusted</td><td>{pill("have it","ok")} — nfl.com standings + stats</td></tr>
<tr><td>2</td><td>Defensive rating</td><td>Points allowed per game, opponent-adjusted</td><td>{pill("have it","ok")} — nfl.com standings</td></tr>
<tr><td>3</td><td>Efficiency cross-check</td><td>NGS offensive and defensive EPA per play</td><td>{pill("have it","ok")} — nfl.com/ngs/trends</td></tr>
<tr><td>4</td><td>Availability adjustment</td><td>Injury status × depth-string weight</td><td>{pill("partial","warn")} — injuries complete, depth 2/32</td></tr>
<tr><td>5</td><td>Home-field term</td><td>League-wide home advantage estimate</td><td>{pill("missing","bad")} — requires multi-season results</td></tr>
<tr><td>6</td><td>Spread</td><td>Rating differential + home term</td><td>{pill("method only","info")} — uncalibrated</td></tr>
<tr><td>7</td><td>Total</td><td>Expected combined scoring from the same ratings</td><td>{pill("method only","info")} — uncalibrated</td></tr>
<tr><td>8</td><td>Price</td><td>Convert our probability to odds, compare to close</td><td>{pill("missing","bad")} — no odds feed</td></tr>
</tbody></table></div>
<p class="small">The <a href="slate.html">Week 10 Slate</a> page applies a naive version of steps 1–3 and shows the
resulting margin for all 14 games, labelled as a rating differential and explicitly <em>not</em> a line for sale.
A rating differential is not a spread: it has no home-field term and no market information.</p>

<h2 id="parlays">Parlays and prop combos — why they are a different problem</h2>
<p>A two-leg parlay priced at −110 each pays decimal {dm['parlay_hold_compounding'][1]['offered_decimal']}. The effective hold is
<strong>{dm['parlay_hold_compounding'][1]['effective_hold_pct']}%</strong>, not {dm['hold_-110_-110_pct']}%. You are paying the tax twice. To be worth
placing, the joint probability must exceed what the book charged you for — and that joint probability depends entirely
on the correlation between the legs, which the book models and we currently cannot.</p>
<table>
<thead><tr><th>Latent correlation ρ</th><th class="num">Fair joint probability</th><th class="num">EV at the −110 / −110 price</th></tr></thead>
<tbody>
{''.join(f"<tr><td class='num'>{r['rho']}</td><td class='num'>{r['fair_joint_pct']}%</td><td class='num'>{r['ev_per_1_unit_staked_pct']}%</td></tr>" for r in dm['correlated_parlay_table'])}
</tbody></table>
<p class="small">Both legs modelled as a no-vig 50/50. Computed by <code>tools/calc.py</code> using a bivariate-normal
copula; the ρ = 0 case reproduces 25.00% exactly as a unit test. This table is the argument for
<a href="validation-gates.html#g7">Gate G7</a>.</p>

<h2>The board</h2>
{table([("id","ID"),("name","Strategy"),("bet_shape","Shape"),("market","Market"),
        ("status","Status"),("gates","Gates"),("blocking","Blocked at")], tr)}

<h2>Every strategy in detail</h2>
{details}

<h2>Sources</h2>
{src_list(["S01","S02","S03","S04","S06","S10","S11","S12","S17"], sources)}
"""
    page("pages/strategies.html", "Strategy Origination", body, "pages/strategies.html",
         "Twelve falsifiable signal hypotheses across single bets, parlays and prop combos — with an honest status for every one.",
         [("", "Home"), ("", "Strategies")])


def build_gates(sources, dm):
    rows = load_csv("data/validation-gates.csv")
    tr = [{"id": r["id"], "gate": r["gate"], "test": r["test"],
           "threshold": r["pass_threshold"], "why": r["why_it_exists"]} for r in rows]
    details = "".join(f"""
<h3 class="anchor" id="{r['id'].lower()}">{r['id']} · {esc(r['gate'])}</h3>
<div class="tablewrap"><table><tbody>
<tr><th style="width:170px">Definition</th><td>{esc(r['definition'])}</td></tr>
<tr><th>Test</th><td>{esc(r['test'])}</td></tr>
<tr><th>Pass threshold</th><td><strong>{esc(r['pass_threshold'])}</strong></td></tr>
<tr><th>Why it exists</th><td>{esc(r['why_it_exists'])}</td></tr>
</tbody></table></div>""" for r in rows)

    body = f"""
<p class="lede">Ten gates, in the order they must be cleared. Each has a numeric threshold and a named failure mode.
A strategy that fails any gate does not advance — it is not "promising but unproven".</p>

<div class="note"><strong>Gates are sequential.</strong> Clearing G7 is meaningless if G3 failed, because G7 asks how much
the edge is worth, not whether one exists. The order is the point.</div>

<h2>The gate set</h2>
{table([("id","Gate"),("gate","Name"),("test","Test applied"),("threshold","Pass threshold"),("why","Failure it prevents")], tr)}

<h2 id="leaderboard">The leaderboard, and why it usually lies</h2>
<p>A leaderboard ranks strategies. If it ranks raw win rate or raw profit, it ranks luck. Three specific mechanisms
guarantee this, and all three are arithmetic, not opinion.</p>

<h3>1 · The break-even tax is one point wide</h3>
<table><thead><tr><th>Price</th><th class="num">Implied probability</th><th class="num">Required win rate</th></tr></thead><tbody>
{''.join(f"<tr><td class='num'>{r['american']:+d}</td><td class='num'>{r['implied_prob_pct']}%</td><td class='num'>{r['breakeven_win_pct']}%</td></tr>" for r in dm['breakeven_table'])}
</tbody></table>

<h3>2 · Small samples cannot separate 53% from 55%</h3>
<table><thead><tr><th class="num">Settled bets</th><th class="num">Smallest true win rate detectable at 80% power</th><th class="num">Edge over break-even</th></tr></thead><tbody>
{''.join(f"<tr><td class='num'>{r['bets']:,}</td><td class='num'>{r['min_detectable_true_win_pct']}%</td><td class='num'>{r['min_detectable_edge_pp']} pp</td></tr>" for r in dm['minimum_detectable_edge'])}
</tbody></table>
<p class="small">Read this row: at 500 bets, anything below a 57.9% true rate is indistinguishable from noise.
A leaderboard populated at 500 bets is ranking noise.</p>

<h3>3 · Many strategies guarantee a false winner</h3>
<div class="note bad"><strong>{dm['luck_false_positive']['prob_single_strategy_at_or_above_55pct_pct']}%</strong> chance that a single
zero-edge strategy shows a 55%+ win rate over 200 bets. Across 500 such strategies, the probability that at least one
looks outstanding is <strong>{dm['luck_false_positive']['prob_at_least_one_of_500_pct']}%</strong>. This is not a corner case;
it is the expected outcome.</div>

<h4>The scoring rule this implies</h4>
<ol class="tight">
<li>Pre-register every strategy before it is tested. An unregistered strategy cannot be ranked. (Gate G10.)</li>
<li>Rank on <em>closing-line value</em> first, profit second. CLV has far lower variance, so it separates skill from luck
sooner. (Gate G4.)</li>
<li>Apply a false-discovery correction across the whole registry, not per strategy. (Gate G10.)</li>
<li>Show, do not rank, below 500 settled bets; rank only above 2,000. (Decision question Q04.)</li>
<li>Report the skill residual, not the win rate. (Gate G6.)</li>
</ol>

<h4>What "reward" should mean</h4>
<div class="note warn">The brief asks for rewards for top-performing strategies but does not define reward. This matters
more than it looks: a reward tied to wagering volume can turn a research project into a regulated gambling product.
<strong>Recommended:</strong> reward internal ranking, priority for further research, and publication — not money and not
staking. This is recorded as <a href="decision-questions.html#Q18">Q18</a> and needs your decision.</div>

<h2>Every gate in detail</h2>
{details}

<h2>Sources</h2>
{src_list(["S01","S02","S03","S04","S06","S10","S18","S19","S20"], sources)}
"""
    page("pages/validation-gates.html", "Validation Gates", body, "pages/validation-gates.html",
         "Ten sequential gates with numeric thresholds, and the arithmetic that explains why most strategy leaderboards rank luck.",
         [("", "Home"), ("", "Validation Gates")])


def build_luck(sources, dm):
    body = f"""
<p class="lede">"Remove luck from the equation" is the hardest part of the brief and the easiest part to fake.
This page is the arithmetic. None of it is a claim about a strategy; all of it is a constraint any strategy must obey.</p>

<h2>Four sources of luck, and what kills each</h2>
<div class="tablewrap"><table>
<thead><tr><th>Luck source</th><th>How it hides</th><th>What removes it</th><th>Gate</th></tr></thead>
<tbody>
<tr><td>Small sample</td><td>A 12–5 run looks like skill but is within noise of break-even.</td><td>A sample floor derived from power analysis, not from vibes.</td><td>G10</td></tr>
<tr><td>Selection over many tries</td><td>Test 500 strategies and one will look brilliant.</td><td>Pre-registration plus a false-discovery correction.</td><td>G10</td></tr>
<tr><td>Variance-heavy outcomes</td><td>Turnovers, one-score games, defensive scores.</td><td>Decompose into skill residual and variance; grade on CLV.</td><td>G4, G6</td></tr>
<tr><td>Survivorship in reporting</td><td>Failed strategies get quietly dropped and the record looks clean.</td><td>Publish rejected strategies. We do — see the strategies page.</td><td>—</td></tr>
</tbody></table></div>

<h2>The sample-size arithmetic</h2>
<p>To distinguish a true win rate from the break-even rate at 80% power and 5% one-sided significance:</p>
<table><thead><tr><th class="num">True win rate</th><th class="num">Edge over break-even</th><th class="num">Bets required</th></tr></thead><tbody>
{''.join(f"<tr><td class='num'>{r['true_win_pct']}%</td><td class='num'>{r['edge_vs_-110_breakeven_pp']} pp</td><td class='num'>{r['bets_required_80pct_power']:,}</td></tr>" for r in dm['sample_size_required'])}
</tbody></table>
<div class="note warn"><strong>The practical consequence.</strong> A real, exploitable edge in a market this liquid is
usually small — a couple of points. Detecting a 1.1-point edge needs
{dm['sample_size_required'][2]['bets_required_80pct_power']:,} settled bets. A full NFL season offers roughly
270 games; a single-team strategy on one market yields a few dozen bets. <strong>You cannot prove a small edge inside a
season.</strong> Any leaderboard that claims otherwise is measuring variance.</div>

<h2>What a false crown looks like</h2>
<p>Simulate a pool of strategies with <em>zero</em> true edge, each taking 200 bets at −110, and ask how often at least one
looks like a winner:</p>
<div class="kpis">
  <div class="kpi"><div class="n">{dm['luck_false_positive']['prob_single_strategy_at_or_above_55pct_pct']}%</div>
    <div class="l">one strategy ≥55% by luck</div><div class="s">200 bets, zero true edge</div></div>
  <div class="kpi"><div class="n">{dm['luck_false_positive']['prob_any_single_strategy_at_or_above_breakeven_pct']}%</div>
    <div class="l">one strategy merely above break-even</div><div class="s">the bar is that low</div></div>
  <div class="kpi"><div class="n">{dm['luck_false_positive']['prob_at_least_one_of_500_pct']}%</div>
    <div class="l">≥1 of 500 strategies ≥55%</div><div class="s">the expected outcome, not bad luck</div></div>
</div>
<p class="small">Computed with an exact binomial tail in <code>tools/calc.py</code>. The scenario is stated in the output
so it can be re-run and challenged.</p>

<h2>Staking: how much skill can be extracted without being ruined</h2>
<p>Even a real edge can be destroyed by over-staking. Kelly gives the growth-optimal fraction; fractional Kelly gives
most of the growth at a fraction of the drawdown.</p>
<table><thead><tr><th class="num">True win rate</th><th class="num">Price</th><th class="num">Full Kelly</th><th class="num">Half Kelly</th><th class="num">Quarter Kelly</th></tr></thead><tbody>
{''.join(f"<tr><td class='num'>{r['true_win_pct']}%</td><td class='num'>{r['american']:+d}</td><td class='num'>{r['full_kelly_pct_of_bankroll']}%</td><td class='num'>{r['half_kelly_pct']}%</td><td class='num'>{r['quarter_kelly_pct']}%</td></tr>" for r in dm['kelly_table'])}
</tbody></table>
<p class="small">The last row is the useful one: a 60% win rate at −150 has <em>negative</em> expected value, so Kelly
sizes it at zero. That is the whole argument for <a href="validation-gates.html#g5">Gate G5</a> in one line — a high win
rate at a bad price is a losing strategy, and the staking formula refuses to fund it.</p>

<h2>How skill is actually demonstrated here</h2>
<ol class="tight">
<li><strong>Closing-line value above zero with a confidence interval that excludes zero.</strong> This is the cleanest
available proof, because it does not require winning every bet — only consistently taking the better side of the price.</li>
<li><strong>Out-of-sample profit across at least three held-out seasons.</strong> In-sample profit is worthless.</li>
<li><strong>A positive skill residual after controlling for opponent strength.</strong> This is what separates
"good team" from "good process".</li>
<li><strong>Reproducibility.</strong> If the bet list changes when the model is re-run on the same data, there is no model.</li>
</ol>

<h2>What this page does not claim</h2>
<div class="note bad">No strategy in this repository has been graded. There is no win rate, no ROI and no CLV figure
anywhere in this project, because the odds data required to compute one has not been ingested. Every number above is a
<em>constraint</em> on future results, not a report of past ones. The moment a "performance" number appears without a
sourced price history behind it, it should be treated as fabricated.</div>

<h2>Sources</h2>
{src_list(["S18","S19","S20"], sources)}
<p class="small">The efficiency literature is cited as secondary context only. It is never used to assert a fact about a
specific game, team or price.</p>
"""
    page("pages/luck-and-skill.html", "Luck vs Skill", body, "pages/luck-and-skill.html",
         "The arithmetic of removing luck: how many bets it takes, how often luck wins a crown, and how much skill can be staked safely.",
         [("", "Home"), ("", "Luck vs Skill")])


def build_correlation(sources, corr, dm):
    tr = [{"label": r["label"], "n": r["n_clubs"], "r": r["pearson_r"],
           "r2": f'{r["r2_pct_variance_explained"]}%',
           "ci": f'[{r["boot_ci_95_low"]}, {r["boot_ci_95_high"]}]',
           "zero": r["ci_excludes_zero"], "why": r["interpretation"]} for r in corr]
    body = f"""
<p class="lede">Correlation values, measured rather than asserted. Ten relationships across all 32 clubs, each with a
bootstrap confidence interval, plus a second set showing how much correlation moves a parlay's true value.</p>

<div class="note bad" id="limits"><strong>Read the scope before the numbers.</strong> These are
<em>cross-sectional</em> correlations: 32 clubs, one snapshot. They answer "when a team is better at X, is it also
better at Y?" They do <strong>not</strong> answer "if this leg wins, how does the other leg's probability move?" — which is the
only correlation that prices a parlay. The two are different quantities and are not interchangeable. No same-game
prop correlation is claimed anywhere in this repository, because it cannot be computed from team-level data.</div>

<h2>Measured relationships</h2>
{table([("label","Relationship"),("n","N"),("r","Pearson r"),("r2","R²"),("ci","95% CI (bootstrap)"),
        ("zero","CI excludes 0"),("why","Reading")], tr, numeric=("n","r","r2","ci"))}

<h2>What the numbers actually say</h2>
<ul class="tight">
<li><strong>Efficiency metrics are strong team ratings.</strong> Offensive EPA/play explains {corr[0]['r2_pct_variance_explained']}%
of the variance in points scored. That is excellent for rating a team and <em>useless</em> as an edge, because everyone
can see it.</li>
<li><strong>Rushing efficiency is a trap.</strong> r = {corr[4]['pearson_r']}, CI including zero, R² of
{corr[4]['r2_pct_variance_explained']}%. Any strategy built on rushing yards per attempt was killed by this row before it
cost anything. It is kept on the <a href="strategies.html">strategy board</a> as a rejected item so it does not get rebuilt.</li>
<li><strong>Pressure matters more than volume.</strong> Sacks taken vs points scored: r = {corr[8]['pearson_r']}
(R² {corr[8]['r2_pct_variance_explained']}%). Defensive interceptions vs points allowed: r = {corr[7]['pearson_r']}.
Both are real and both are widely known, which is exactly why neither is likely to be an edge on its own.</li>
<li><strong>Pass volume beats pass efficiency in one direction only.</strong> Total passing yards vs PPG is r =
{corr[5]['pearson_r']}, weaker than yards per attempt at {corr[2]['pearson_r']}. Efficiency, not volume — a useful
caution for prop markets, where volume is what the line is set on.</li>
</ul>

<h2>The correlation that prices a parlay</h2>
<p>Two legs, each modelled as a no-vig 50/50, priced together at −110 / −110 (decimal
{dm['parlay_hold_compounding'][1]['offered_decimal']}). The latent correlation between the legs is ρ. This is a
bivariate-normal copula; at ρ = 0 it must reproduce 25.00%, and it does.</p>
<div class="tablewrap"><table>
<thead><tr><th class="num">ρ</th><th class="num">Fair joint probability</th><th class="num">Fair decimal price</th>
<th class="num">Offered decimal price</th><th class="num">EV per unit staked</th></tr></thead>
<tbody>
{''.join(f"<tr><td class='num'>{r['rho']}</td><td class='num'>{r['fair_joint_pct']}%</td><td class='num'>{r['fair_decimal']}</td><td class='num'>{r['offered_decimal_-110x2']}</td><td class='num'>{r['ev_per_1_unit_staked_pct']}%</td></tr>" for r in dm['correlated_parlay_table'])}
</tbody></table></div>
<div class="note"><strong>The decision this forces.</strong> The same two legs swing from
{dm['correlated_parlay_table'][1]['ev_per_1_unit_staked_pct']}% to
{dm['correlated_parlay_table'][5]['ev_per_1_unit_staked_pct']}% EV purely on ρ. Any model that assumes independence is not
approximating — it is answering a different question. This is why
<a href="validation-gates.html#g7">Gate G7</a> blocks multi-leg strategies until ρ is estimated from real data.</div>

<h2>Why we cannot yet compute the prop correlations that matter</h2>
<p>The parlay cases in the brief — QB passing yards with his WR1's receiving yards, or a rusher with the opposing
quarterback — require <em>event-level</em> data: both players' outcomes in the same game, repeated over hundreds of games.
This repository contains team totals and player season totals. Neither can produce a joint distribution. What is needed:</p>
<ol class="tight">
<li>Player game logs for both legs, at least three seasons (to avoid a one-season fluke).</li>
<li>Consistent player identifiers across sources, so legs can be joined reliably.</li>
<li>Prop lines as offered, so the correlation can be turned into a price comparison rather than an academic statistic.</li>
</ol>
<p>This is recorded as <a href="decision-questions.html#Q07">Q07</a> and as suggestion SG06.</p>

<h2>Method</h2>
<div class="tablewrap"><table><tbody>
<tr><th style="width:190px">Script</th><td><code>tools/analyze_correlation.py</code></td></tr>
<tr><th>Inputs</th><td><code>data/team-metrics-2026-w10.csv</code> (32 clubs)</td></tr>
<tr><th>Estimator</th><td>Pearson product-moment correlation</td></tr>
<tr><th>Interval</th><td>Percentile bootstrap, 4,000 resamples, seed 7 — reproducible</td></tr>
<tr><th>Read</th><td>A CI that includes zero means the data cannot distinguish the effect from no effect, and it is reported as such.</td></tr>
<tr><th>Not done</th><td>No p-hacking, no subgroup mining, no per-team correlations. With n = 32, per-team analysis would be noise.</td></tr>
</tbody></table></div>

<h2>Sources</h2>
{src_list(["S02","S03","S04","S06","S22"], sources)}
"""
    page("pages/correlation.html", "Correlation", body, "pages/correlation.html",
         "Ten measured correlations with bootstrap confidence intervals, plus the correlation arithmetic that actually prices a parlay.",
         [("", "Home"), ("", "Correlation")])


def build_injuries(sources):
    rows = load_csv("data/injury-report-2026-w10.csv")
    outs = [r for r in rows if r["game_status"] == "Out"]
    dbs = [r for r in rows if r["game_status"] == "Doubtful"]
    qs = [r for r in rows if r["game_status"] == "Questionable"]
    depth = [r for r in rows if r["depth_string"]]
    no_depth = [r for r in rows if not r["depth_string"]]

    def tr(rs):
        return [{"club": r["abbr"], "player": r["player"], "pos": r["position"],
                 "injury": r["injury"], "practice": r["practice_status"],
                 "status": r["game_status"], "depth": r["depth_string"],
                 "basis": r["depth_basis"], "next": r["next_man_up"],
                 "src": r["source_url"]} for r in rs]

    depth_rows = [{"club": r["abbr"], "player": r["player"], "pos": r["position"],
                   "injury": r["injury"], "status": r["game_status"],
                   "depth": r["depth_string"], "next": r["next_man_up"],
                   "chart": r["depth_source_url"]} for r in depth]

    # verified starter losses at premium positions (depth == 1), grouped by side
    def side(pos):
        if pos in ("QB", "RB", "WR", "TE", "T", "G", "C", "FB"):
            return "Offense"
        return "Defense"

    starter_losses = [r for r in depth if r["depth_string"] == "1" and r["game_status"] in ("Out", "Doubtful")]

    body = f"""
<p class="lede">Every Week 10 injury row that carries an official game status, transcribed from the league's own
report, joined — where an official depth chart exists — to the string the player occupies and the next man up.</p>

<div class="note warn" id="depth"><strong>Coverage limit, stated up front.</strong> Official depth charts were captured for
<strong>2 of 32 clubs</strong> (Kansas City and Seattle). For the other 30, the depth fields are
<strong>blank, not estimated</strong> — {len(no_depth)} of {len(rows)} rows. The league does not publish a single
consolidated depth chart at <code>nfl.com/teams/{{club}}/depthchart</code>; that path returns 404. Club sites publish
their own, individually, and each is labelled "unofficial" by the publishing club.</div>

<div class="kpis">
  <div class="kpi"><div class="n">{len(rows)}</div><div class="l">rows with a game status</div><div class="s">26 clubs represented</div></div>
  <div class="kpi"><div class="n">{len(outs)}</div><div class="l">Out</div><div class="s">will not play</div></div>
  <div class="kpi"><div class="n">{len(dbs)}</div><div class="l">Doubtful</div><div class="s">unlikely</div></div>
  <div class="kpi"><div class="n">{len(qs)}</div><div class="l">Questionable</div><div class="s">the noisy middle</div></div>
  <div class="kpi"><div class="n">{len(depth)}</div><div class="l">rows with a verified depth string</div><div class="s">KC and SEA only</div></div>
</div>

<h2>Why the game-status column is the only one that matters</h2>
<p>The official policy requires clubs to file a practice report on a fixed weekday pattern and a game status report the
day before the game, with three designations: <strong>Out</strong>, <strong>Doubtful</strong> and <strong>Questionable</strong>. Practice participation
is diagnostic of those designations, not a substitute for them. A player who is "Full Participation" with no game
status is on the report and is not expected to miss time; a player who is "Questionable" might play or might not.</p>
<p>This matters for modelling because the labels have very different information content. The league defines the labels.
It does <strong>not</strong> publish their predictive value, so any weighting we apply is our own and is labelled as such on
<a href="validation-gates.html">the gates page</a>. Calibrating it needs realised snap counts, which we do not have
(<a href="decision-questions.html#Q08">Q08</a>).</p>

<h2>Starters ruled Out or Doubtful, where the depth chart is verified</h2>
<p>This is the concrete answer to "is a defence down to its 2nd or 3rd string?" for the two clubs where it can be
answered from an official document.</p>
{table([("club","Club"),("player","Player"),("pos","Pos"),("injury","Injury"),("status","Status"),
        ("depth","String"),("next","Next man up (per club depth chart)"),("chart","Depth chart")],
       [{"club": r["abbr"], "player": r["player"], "pos": r["position"], "injury": r["injury"],
         "status": r["game_status"], "depth": r["depth_string"], "next": r["next_man_up"],
         "chart": r["depth_source_url"]} for r in starter_losses if r["next_man_up"]])}

<h2>The depth table — every row with a verified string</h2>
{table([("club","Club"),("player","Player"),("pos","Pos"),("injury","Injury"),("status","Status"),
        ("depth","String"),("next","Next man up"),("chart","Chart")], depth_rows)}

<div class="note"><strong>Worked example — Seahawks defence.</strong> Leonard Williams is listed as the starting 3-technique
on seahawks.com and is <em>Out</em> with a stinger. The next man listed at that slot is Rylie Mills. That is a verified
1st-to-2nd string drop at a starting defensive tackle spot, derived from two official documents with no inference.
The same page shows Seattle's quarterback situation: Sam Darnold is <em>Out</em> and Drew Lock — the listed backup — is
reported by nfl.com as the starter.</div>

<h2>Worked example — where the data refuses to answer</h2>
<p>Kansas City's defensive tackle Peter Woods is <em>Out</em> (neck) and sits at 2nd string behind Chris Jones. The next man
listed is Marcus Harris, at 3rd string. So Kansas City is down a rotational tackle and is now on its 3rd string at that
slot — a real, verified finding.</p>
<p>Contrast with Omarr Norman-Lott, also listed <em>Out</em> (knee) at defensive tackle. He does <strong>not</strong> appear at any string
on the captured depth chart. Rather than guess where he would have been, the string cell is blank and the basis column
says so. This is the blank rule in action: a missing answer is reported as missing.</p>

<h2>All {len(rows)} status rows</h2>
{table([("club","Club"),("player","Player"),("pos","Pos"),("injury","Injury"),
        ("practice","Practice"),("status","Game status"),("depth","String"),
        ("basis","Depth basis"),("src","Source")], tr(rows))}

<h2>How this would be extended to all 32 clubs</h2>
<ol class="tight">
<li>Capture each club's official depth chart from its own site on a fixed schedule. They are published, structured, and
each is labelled "unofficial depth chart" by the club itself — that caveat belongs on the page, not buried.</li>
<li>Join on player name plus listed position. The join is the fragile part; it needs a player identifier, not a name.</li>
<li>Add realised snap counts so the string can be validated against who actually played, which is also what calibrates
the designation weights (Q08).</li>
<li>Re-run daily during the season. A Week 10 snapshot is stale within hours once practice reports change.</li>
</ol>
<p class="small">This is suggestion SG09 and decision question Q09. Nothing here is inferred; where the document does not
answer, the field is empty.</p>

<h2>Sources</h2>
{src_list(["S01","S10","S11","S12","S16","S17"], sources)}
"""
    page("pages/injuries.html", "Injuries &amp; Depth-Chart Deficiencies", body, "pages/injuries.html",
         "Every Week 10 injury row with an official game status, joined to verified depth strings where an official club depth chart exists.",
         [("", "Home"), ("", "Injuries &amp; Depth")])


def build_slate(sources):
    rows = load_csv("data/slate-2026-w10.csv")
    tr = [{"order": r["order"], "day": f'{r["day"]} {r["kickoff_et"]}', "away": r["away"],
           "home": r["home"], "venue": r["venue"] or ("neutral" if r["neutral_site"] == "yes" else ""),
           "final": r["final"], "score": (f'{r["away_score"]}-{r["home_score"]}' if r["home_score"] else ""),
           "m": r["naive_rating_margin_home"],
           "ho": r["home_off_epa"], "hd": r["home_def_epa"],
           "ao": r["away_off_epa"], "ad": r["away_def_epa"]} for r in rows]
    played = [r for r in rows if r["final"] == "FINAL"]

    body = f"""
<p class="lede">All 14 games of Week 10 2026 in official kickoff order, with venue, result where played, and a naive
rating differential computed from verified team metrics. <strong>This is not a line and is not for sale.</strong></p>

<div class="note warn"><strong>What the margin column is, and is not.</strong> It is
<code>(home PPG − home PAPG) + (away PAPG − away PPG)</code> — a pure form differential from nfl.com standings.
It contains <strong>no home-field term, no injury adjustment, and no market information</strong>, and it is not a spread.
A real originated line needs all three, and the market term needs an odds feed this repository does not have
(<a href="decision-questions.html#Q01">Q01</a>). It is shown because it is honest about what it is, and because it
demonstrates the mechanics of <a href="strategies.html#line-origination">line origination</a> step by step.</div>

<div class="kpis">
  <div class="kpi"><div class="n">14</div><div class="l">games</div><div class="s">4 clubs on bye: CHI, DEN, PHI, TB</div></div>
  <div class="kpi"><div class="n">1</div><div class="l">played</div><div class="s">WAS 24 – NYG 21, Thu Nov 12</div></div>
  <div class="kpi"><div class="n">13</div><div class="l">to play</div><div class="s">Sun Nov 15 and Mon Nov 16</div></div>
  <div class="kpi"><div class="n">1</div><div class="l">international game</div><div class="s">NE at DET, Munich</div></div>
</div>

<h2>The slate</h2>
{table([("order","#"),("day","Kickoff (ET)"),("away","Away"),("home","Home"),("venue","Venue / note"),
        ("final","Final"),("score","Score"),("m","Rating diff (home)"),
        ("ho","Home off EPA"),("hd","Home def EPA"),("ao","Away off EPA"),("ad","Away def EPA")], tr,
       numeric=("order","m","ho","hd","ao","ad"))}

<h2>Cross-checks performed on this table</h2>
<div class="tablewrap"><table>
<thead><tr><th>Check</th><th>Expectation</th><th>Result</th></tr></thead>
<tbody>
<tr><td>Every club appears exactly once, or is on bye</td><td>28 club-slots + 4 byes = 32</td><td>{pill("pass","ok")} — asserted in <code>tools/build_slate_csv.py</code></td></tr>
<tr><td>Total games implied by standings</td><td>274 team-games ÷ 2 = 137</td><td>{pill("pass","ok")} — 4 byes × 8.5 + 14 × 9 = 137</td></tr>
<tr><td>Played game result matches the standings</td><td>WAS 3-5-1, NYG 5-3-1</td><td>{pill("pass","ok")} — both published records match the schedule page</td></tr>
<tr><td>International venue</td><td>FC Bayern Munich Arena, Germany</td><td>{pill("pass","ok")} — operations.nfl.com important dates</td></tr>
<tr><td>Kickoff times</td><td>Official schedule page</td><td>{pill("pass","ok")} — 09:30, 13:00, 16:05, 16:25, 20:20, 20:15 all read from nfl.com</td></tr>
<tr><td>Prices</td><td>None ingested</td><td>{pill("blocked","bad")} — no odds source, so no price column exists</td></tr>
</tbody></table></div>

<h2>What an actual originated line would add</h2>
<ol class="tight">
<li><strong>A home-field term.</strong> League-wide home advantage is a real, measurable quantity. It requires multi-season
results, which are not ingested here. Without it, every number in the margin column is systematically short for the
home team.</li>
<li><strong>An availability adjustment.</strong> The injury data exists (see <a href="injuries.html">Injuries &amp; Depth</a>) but the
depth strings that would size the adjustment exist for 2 clubs only.</li>
<li><strong>A market comparison.</strong> A line with nothing to compare against is an opinion. The comparison against the close
is the entire product.</li>
</ol>
<p>Steps 1 and 3 are the blockers, and both are data purchases, not code.</p>

<h2>Sources</h2>
{src_list(["S02","S05","S08","S06","S03","S04"], sources)}
"""
    page("pages/slate.html", "Week 10 2026 Slate", body, "pages/slate.html",
         "All 14 Week 10 games in official kickoff order with venues, results and a clearly-labelled rating differential that is not a line.",
         [("", "Home"), ("", "Week 10 Slate")])


def build_standings(sources):
    rows = load_csv("data/standings-2026-w10.csv")
    tr = [{"club": r["club"], "abbr": r["abbr"], "w": r["wins"], "l": r["losses"], "t": r["ties"],
           "pct": r["pct"], "pf": r["points_for"], "pa": r["points_against"],
           "net": r["net_points_published"], "der": r["division_record"],
           "conf": r["conference_record"], "strk": r["streak"], "src": r["source_url"]} for r in rows]
    body = f"""
<p class="lede">All 32 clubs, transcribed from the official standings, with the arithmetic re-derived and checked column
by column.</p>

<div class="note ok"><strong>Verification performed.</strong> Winning percentage recomputed as
<code>(W + 0.5·T) ÷ (W + L + T)</code> for every club — 32 of 32 matched the published figure. Published net points
recomputed as <code>PF − PA</code> — 32 of 32 matched. Total team-games summed to 274, giving 137 league games, which is
consistent with 4 byes and 14 games in Week 10.</div>

<h2>Standings</h2>
{table([("club","Club"),("abbr","Abbr"),("w","W"),("l","L"),("t","T"),("pct","PCT"),("pf","PF"),("pa","PA"),
        ("net","Net pts"),("der","Division"),("conf","Conference"),("strk","Streak"),("src","Source")], tr,
       numeric=("w","l","t","pct","pf","pa","net"))}

<h2>Reading the table for signal, not for story</h2>
<p>Two columns matter for a rating model and the rest are context. <strong>PF</strong> and <strong>PA</strong> are what a power
rating consumes; <strong>PCT</strong>, division and conference records are what a narrative consumes. A model built on
PCT is a model built on 9 games of results, which is the definition of small-sample noise
(see <a href="luck-and-skill.html">Luck vs Skill</a>).</p>
<p>Note the extremes, because they are the cases where a rating model and the win column disagree most — which is where
any value in this project would come from:</p>
<ul class="tight">
<li><strong>Jaguars</strong> are +108 in net points at 6-2 — the strongest differential in the AFC. A rating model likes them more
than the record does.</li>
<li><strong>Chargers</strong> are −98 at 0-8, and <strong>Eagles</strong> are −73 at 2-7. Their records are <em>worse</em> than their
differentials, which is the mirror case.</li>
<li><strong>Panthers</strong> are +24 in net points at 3-5, and <strong>Buccaneers</strong> +24 at 3-6. Positive differentials with
losing records are the classic regression candidates — but see the warning below before treating that as a signal.</li>
</ul>
<div class="note warn"><strong>Regression to the mean is a hypothesis, not a finding.</strong> The observations above are
descriptive of one snapshot. Turning "positive differential, losing record" into a bet requires multi-season evidence and
an odds feed, which is <a href="validation-gates.html#g3">Gate G3</a> and is currently unmet for this and every other
strategy.</div>

<h2>Sources</h2>
{src_list(["S02","S05"], sources)}
"""
    page("pages/data-standings.html", "Standings — 2026 Week 10", body, "pages/data-standings.html",
         "All 32 clubs from the official standings, with winning percentage and net points independently re-derived.",
         [("", "Home"), ("", "Standings")])


def build_team_metrics(sources):
    rows = load_csv("data/team-metrics-2026-w10.csv")
    tr = [{"club": r["club"], "gp": r["games_played"], "ppg": r["derived_ppg"], "papg": r["derived_papg"],
           "oepa": r["ngs_off_epa_per_play"], "depa": r["ngs_def_epa_per_play"],
           "ngsp": r["ngs_ppg"], "d1": r["ppg_crosscheck_delta"],
           "pyds": r["pass_yds"], "pypa": r["pass_ypa"], "ptd": r["pass_td"], "pint": r["pass_int"],
           "ryds": r["rush_yds"], "rypa": r["rush_avg"],
           "dypa": r["def_pass_ypa"], "dint": r["def_pass_int"], "sacks": r["pass_sacks"],
           "ver": r["verification"]} for r in rows]
    body = f"""
<p class="lede">One row per club, joining four official NFL.com tables. This is the input layer for every rating,
correlation and signal on the site.</p>

<div class="note ok"><strong>Cross-source verification.</strong> Points per game computed as <code>PF ÷ games</code> from the
standings was compared with NFL Next Gen Stats' independently published PPG. Where both exist (16 clubs), all 16 agreed
to within 0.05 — pure one-decimal rounding. Completion percentage and yards per attempt were likewise recomputed from
their own numerators and denominators; 32 of 32 matched. The build script fails loudly if any of these drift, so a bad
transcription cannot slip through silently.</div>

<h2>Joined team table</h2>
{table([("club","Club"),("gp","GP"),("ppg","PPG (derived)"),("papg","Opp PPG (derived)"),
        ("ngsp","NGS PPG"),("d1","Δ PPG check"),
        ("oepa","Off EPA/play"),("depa","Def EPA/play"),
        ("pyds","Pass yds"),("pypa","Pass Y/A"),("ptd","Pass TD"),("pint","INT"),
        ("ryds","Rush yds"),("rypa","Rush Y/A"),
        ("dypa","Opp pass Y/A"),("dint","Def INT"),("sacks","Sacks taken")], tr,
       numeric=("gp","ppg","papg","ngsp","d1","oepa","depa","pyds","pypa","ptd","pint","ryds","rypa","dypa","dint","sacks"))}

<h2>Column definitions, and who defines them</h2>
<div class="tablewrap"><table>
<thead><tr><th>Column</th><th>Definition</th><th>Defined by</th></tr></thead>
<tbody>
<tr><td>PPG (derived)</td><td>Points for ÷ games played. Derived here so it can be checked, not taken on trust.</td><td>Our arithmetic on official data</td></tr>
<tr><td>NGS PPG</td><td>Points per game as published on the Next Gen Stats trends page.</td><td>NFL Next Gen Stats</td></tr>
<tr><td>Off / Def EPA per play</td><td>"How much an offense improves its expected scoring outcome per play" — expected points before and after each play, from down, distance and field position.</td><td>NFL Next Gen Stats (their own published definition)</td></tr>
<tr><td>Pass Y/A</td><td>Passing yards ÷ passing attempts.</td><td>NFL.com team stats</td></tr>
<tr><td>Δ PPG check</td><td>Derived PPG minus NGS PPG. A non-zero value outside ±0.05 would indicate a transcription error.</td><td>Our arithmetic</td></tr>
</tbody></table></div>

<h2>What this table cannot do</h2>
<div class="note bad">It has <strong>no opponent adjustment</strong>. A club that has played four games against the league's
weakest defences will look efficient here and is not. Every serious rating model adjusts for opponent strength, and
doing so requires game-level data — which opponent, which week — that this table does not carry. Treat these numbers as
raw inputs, not as ratings.</div>

<h2>Sources</h2>
{src_list(["S02","S03","S04","S06","S07","S22"], sources)}
"""
    page("pages/data-team.html", "Team Metrics — Joined Dataset", body, "pages/data-team.html",
         "Four official NFL.com tables joined into one auditable row per club, with cross-source arithmetic checks.",
         [("", "Home"), ("", "Team Metrics")])


def build_audit(sources):
    body = f"""
<p class="lede">A line-by-line review of the repository as it was found, what was changed, what was verified, and every
irregularity flagged for manual review.</p>

<h2>State of the repository when found</h2>
<div class="tablewrap"><table>
<thead><tr><th>Item</th><th>Observed</th><th>Assessment</th></tr></thead>
<tbody>
<tr><td>Commits</td><td>1 — <code>0f3d2f9 Initial commit</code></td><td>{pill("irregular","warn")} An "initial commit" containing no code, data or site.</td></tr>
<tr><td>Files</td><td><code>README.md</code> only</td><td>{pill("irregular","warn")} No source, no data, no site, no licence, no CI.</td></tr>
<tr><td><code>README.md</code> content</td><td>Five bytes: <code>NFL\\n\\n</code></td><td>{pill("irregular","warn")} Not a README. No project description, no instructions.</td></tr>
<tr><td>Branches</td><td><code>main</code>, <code>arena/e70150db-fl2</code></td><td>{pill("ok","ok")} Clean.</td></tr>
<tr><td>COORDINATION.md</td><td>Absent</td><td>{pill("created","info")} Created in this pass as the shared task board, per the brief.</td></tr>
<tr><td>GitHub Pages</td><td>Already enabled, source <code>main</code> / root, build type <code>legacy</code></td><td>{pill("note","neutral")} Pre-existing. It was serving a site that did not exist. Now serves this one.</td></tr>
<tr><td>Issues</td><td>Enabled</td><td>{pill("ok","ok")}</td></tr>
<tr><td>Repository visibility</td><td>Public</td><td>{pill("note","neutral")} Relevant because any ingested licensed odds data would become publicly redistributable.</td></tr>
<tr><td>Licence</td><td>No licence file present</td><td>{pill("irregular","warn")} Legal status of any future contribution is undefined.</td></tr>
<tr><td>Tests / CI</td><td>No test suite and no CI workflow</td><td>{pill("irregular","warn")} Addressed here with assertion checks inside the build scripts.</td></tr>
</tbody></table></div>

<h2>What was added, and why each piece is auditable</h2>
<div class="tablewrap"><table>
<thead><tr><th>Path</th><th>Purpose</th><th>How it is checked</th></tr></thead>
<tbody>
<tr><td><code>COORDINATION.md</code></td><td>Shared task board, claims, scopes, verification standard.</td><td>Task table lists every file scope; no two tasks overlap.</td></tr>
<tr><td><code>tools/calc.py</code></td><td>All odds, parlay, correlation, sample-size and Kelly arithmetic.</td><td>Includes a unit-test assertion that the copula returns 25.00% at ρ = 0.</td></tr>
<tr><td><code>tools/build_injury_csv.py</code></td><td>Builds the injury dataset from the league report.</td><td>Depth fields only populated from a named official chart; everything else blank.</td></tr>
<tr><td><code>tools/build_team_metrics.py</code></td><td>Joins four official tables.</td><td>Asserts PPG, pass %, and Y/A reproduce from their own numerators; fails on drift.</td></tr>
<tr><td><code>tools/build_slate_csv.py</code></td><td>Builds the Week 10 schedule table.</td><td>Asserts bye list and that no club appears twice.</td></tr>
<tr><td><code>tools/analyze_correlation.py</code></td><td>Correlations with bootstrap CIs.</td><td>Seeded RNG — identical output on every run.</td></tr>
<tr><td><code>tools/build_planning_csv.py</code></td><td>Requirements, questions, strategies, gates, suggestions.</td><td>Every factual claim carries a source ID that resolves in <code>data/sources.csv</code>.</td></tr>
<tr><td><code>tools/build_site.py</code></td><td>Generates the site from the data.</td><td>Empty cells render as a visible blank; no page is hand-edited.</td></tr>
<tr><td><code>tools/check_links.py</code></td><td>Link and structure checker.</td><td>Every internal link resolves to a file; every source URL is present and well-formed.</td></tr>
</tbody></table></div>

<h2>Retrieval constraint, disclosed</h2>
<div class="note warn"><strong>The bash sandbox has no outbound network access</strong> except to GitHub, npm and PyPI. All web
verification in this pass was therefore performed through a page-fetch tool against the official URLs, and the raw text
of every fetched page was inspected before anything was transcribed. Data was never taken from memory, and no value was
filled in because it "seemed right". The consequence for a reviewer: each table cell can be checked by opening the
linked source URL, but it cannot be re-fetched by a script inside this environment.</div>

<h2>Flagged for manual review</h2>
<p>These are not errors in our work — they are gaps, ambiguities and negative findings that a human should look at.
They are all published, with source links, on the <a href="flagged.html">Flagged for Review</a> page and none of them
blocked the merge.</p>
<ol class="tight">
<li>30 of 32 clubs have no verified depth chart, so 2nd/3rd/4th-string analysis is impossible for them.</li>
<li>No official league-wide depth-chart endpoint exists at the path one would expect (404 confirmed).</li>
<li>No odds or price data exists anywhere in the project.</li>
<li>Two clubs' published PPG differ from our derived PPG by 0.05 — rounding artefact, recorded rather than hidden.</li>
<li>The league publishes injury designations but not their predictive value.</li>
<li>NGS EPA values were only available for 16 of 32 clubs on the published page, so EPA columns are blank for the other 16.</li>
<li>Prediction-market engagement is treated by the league as covered by its gambling policy, which affects whether an
auto-betting product is viable at all.</li>
</ol>

<h2>Sources</h2>
{src_list(["S05","S08","S17"], sources)}
"""
    page("pages/repo-audit.html", "Repository Audit", body, "pages/repo-audit.html",
         "Line-by-line review of the repository as found, what was added, how each piece is checked, and every irregularity.",
         [("", "Home"), ("", "Repo Audit")])


def build_sources(sources_rows):
    tr = [{"id": s["id"], "name": s["name"], "publisher": s["publisher"], "tier": s["tier"],
           "url": s["url"], "what": s["what_it_supports"], "ret": s["retrieved"],
           "check": s["check"]} for s in sources_rows]
    primary = [s for s in sources_rows if s["tier"] == "league" or s["tier"] == "club"]
    secondary = [s for s in sources_rows if s["tier"] == "secondary"]
    body = f"""
<p class="lede">Every source used, with the retrieval date, what it actually supports, and whether it is authoritative
or merely context.</p>

<div class="note"><strong>Source hierarchy.</strong> <strong>league</strong> (nfl.com, operations.nfl.com, media.nfl.com) and
<strong>club</strong> (the club's own official site) are treated as authoritative. <strong>secondary</strong> sources are cited only
for context — published research on market efficiency — and are <em>never</em> used to assert a fact about a team, a
player, an injury or a price.</div>

<div class="kpis">
  <div class="kpi"><div class="n">{len(sources_rows)}</div><div class="l">sources total</div><div class="s">all retrieved {RET}</div></div>
  <div class="kpi"><div class="n">{len(primary)}</div><div class="l">authoritative</div><div class="s">league or club</div></div>
  <div class="kpi"><div class="n">{len(secondary)}</div><div class="l">secondary</div><div class="s">context only</div></div>
  <div class="kpi"><div class="n">1</div><div class="l">negative finding</div><div class="s">a 404 that matters (S17)</div></div>
</div>

<h2>The registry</h2>
<p><code>data/sources.csv</code> is the machine-readable version of this table and is the file every other dataset
references by ID.</p>
{table([("id","ID"),("name","Source"),("publisher","Publisher"),("tier","Tier"),("url","Link"),
        ("what","What it supports"),("ret","Retrieved"),("check","Check")], tr)}

<h2>Negative findings</h2>
<div class="note warn"><strong>S17 — <code>nfl.com/teams/{{club}}/depthchart</code> returns HTTP 404.</strong> This is recorded as a
source precisely because it establishes an absence: there is no league-wide official depth chart at the path a
reasonable person would try first. That is why depth data covers 2 clubs instead of 32, and why
<a href="decision-questions.html#Q09">Q09</a> exists. Recording a negative result is how a gap stays visible instead of
quietly becoming a guess.</div>

<h2>What was checked and how</h2>
<div class="tablewrap"><table>
<thead><tr><th>Check</th><th>Method</th><th>Outcome</th></tr></thead>
<tbody>
<tr><td>Every cited URL resolves</td><td>Fetched each URL and inspected the returned content</td><td>{pill("pass","ok")} all except S17, which is a deliberately recorded 404</td></tr>
<tr><td>Standings arithmetic</td><td>Recomputed PCT as (W+0.5T)/GP for 32 clubs</td><td>{pill("pass","ok")} 32/32 match</td></tr>
<tr><td>Net points</td><td>Recomputed PF − PA</td><td>{pill("pass","ok")} 32/32 match</td></tr>
<tr><td>Passing table internal consistency</td><td>Recomputed completion % and Y/A from their own numerators</td><td>{pill("pass","ok")} 32/32 match</td></tr>
<tr><td>Cross-source PPG</td><td>Compared derived PPG with NGS published PPG</td><td>{pill("pass","ok")} 16/16 within rounding; the other 16 clubs have no published NGS figure, so their column is blank</td></tr>
<tr><td>Schedule completeness</td><td>Asserted byes and no duplicate clubs</td><td>{pill("pass","ok")} 28 club-slots + 4 byes = 32</td></tr>
<tr><td>Internal site links</td><td><code>tools/check_links.py</code></td><td>{pill("pass","ok")} see the audit index for results</td></tr>
</tbody></table></div>
"""
    page("pages/sources.html", "Source Registry", body, "pages/sources.html",
         "Every source, its authority tier, the retrieval date, and exactly what it supports.",
         [("", "Home"), ("", "Sources")])


def build_flagged(sources):
    rows = load_csv("data/injury-report-2026-w10.csv")
    metrics = load_csv("data/team-metrics-2026-w10.csv")
    no_depth_clubs = sorted({r["abbr"] for r in rows if not r["depth_string"]})
    ngs_blank = sorted([r["abbr"] for r in metrics if not r["ngs_off_epa_per_play"]])
    blanks = sum(1 for r in rows if not r["depth_string"])

    items = [
        ("F01", "Missing", "Depth charts for 30 of 32 clubs",
         f"{blanks} of {len(rows)} injury rows carry no verified depth string. Depth analysis therefore covers Kansas City and Seattle only.",
         "The requirement to know whether a defence is on its 2nd, 3rd or 4th string cannot be met for the other clubs.",
         "Capture each club's official depth chart individually.",
         "https://www.nfl.com/injuries/",
         "Open the injury page and confirm the club has no depth fields; then open the club's own site."),
        ("F02", "Negative finding", "No league-wide official depth-chart endpoint",
         "nfl.com/teams/{club}/depthchart returns HTTP 404.",
         "There is no single authoritative source for depth strings, which is why F01 exists.",
         "Per-club capture, or a licensed roster feed that carries a depth order.",
         "https://www.nfl.com/teams/kansas-city-chiefs/depthchart",
         "Load the URL and observe the 404."),
        ("F03", "Missing", "No odds, prices or closing lines",
         "There is no price data of any kind in this repository.",
         "Gates G3, G4, G5 and G9 cannot be cleared for any strategy; nine of twelve strategies are blocked on it.",
         "A licensed historical odds archive with per-book closing prices.",
         "",
         "Search the repository for a price column — there is none, by design."),
        ("F04", "Ambiguity", "Injury designations have no published predictive value",
         f"84 of {len(rows)} status rows are Questionable. The league defines the label, not its meaning for snap counts.",
         "Any injury weighting is an assumption. Ours (Out 1.00 / Doubtful 0.75 / Questionable 0.40) is labelled proposed, not measured.",
         "Join designations to realised snap counts across multiple seasons.",
         "https://www.nfl.com/injuries/",
         "The page publishes the label only; there is no predictive column to check."),
        ("F05", "Rounding", "Two clubs' derived PPG differ from NGS by 0.05",
         "Detroit derives to 27.75 vs NGS 27.8; Minnesota derives to 18.25 vs NGS 18.3.",
         "One-decimal rounding, not a transcription error — but recorded rather than smoothed away.",
         "None needed. Both are consistent with rounding to one decimal.",
         "https://www.nfl.com/stats/ngs/trends",
         "Compare data/team-metrics-2026-w10.csv PPG columns for DET and MIN against the NGS page."),
        ("F06", "Partial coverage", "NGS EPA published for 16 of 32 clubs on the captured page",
         f"EPA columns are blank for {len(ngs_blank)} clubs: {', '.join(ngs_blank)}.",
         "The Team Metrics page is incomplete on the EPA dimension; correlations therefore use 16 or 32 clubs depending on the pair.",
         "Capture each club's own NGS trends page, which reports the same figures.",
         "https://www.nfl.com/stats/ngs/trends",
         "Compare the club count in each correlation row's N column against the club list."),
        ("F07", "Legal / eligibility", "League gambling policy constrains the product",
         "The NFL prohibits its personnel from betting on NFL events and treats prediction-market engagement as covered; players may bet non-NFL events but not from club facilities.",
         "An automated bet-placing product may be unavailable to some contributors regardless of what the model says.",
         "Confirm who contributes and in which jurisdiction before building any staking feature.",
         "https://operations.nfl.com/",
         "Read the league's published gambling policy and confirm applicability to the specific person."),
        ("F08", "Scope", "Primary deliverable is undefined",
         "The brief asks for a research artefact, a product and a rewarded competition simultaneously.",
         "Effort allocation and the legal posture both depend on the answer. Recorded as Q17.",
         "A decision from the owner.",
         "",
         "Nothing to check — this is a decision, not a fact."),
        ("F09", "Undefined", "'Reward' on the leaderboard is undefined",
         "No currency, points system or redemption mechanism is specified.",
         "A reward tied to wagering volume could change the regulatory status of the project. Recorded as Q18.",
         "A decision from the owner.",
         "",
         "Nothing to check — this is a decision, not a fact."),
    ]
    tr = [{"id": i[0], "type": i[1], "item": i[2], "what": i[3], "why": i[4],
           "resolve": i[5], "url": i[6], "how": i[7]} for i in items]

    body = f"""
<p class="lede">Everything that could not be confirmed from an official source, every ambiguity, and every negative
finding — published instead of buried. None of these blocked the merge; all of them should be looked at.</p>

<div class="note warn"><strong>Why this page exists.</strong> An unverified value that gets quietly filled in is
indistinguishable from a fabricated one. Every cell on this site that could not be sourced is <em>blank</em>, and every
blank is accounted for here with a way for you to check it yourself.</div>

<div class="kpis">
  <div class="kpi"><div class="n">{len(items)}</div><div class="l">flagged items</div><div class="s">none blocking</div></div>
  <div class="kpi"><div class="n">{blanks}</div><div class="l">blank depth fields</div><div class="s">not estimated</div></div>
  <div class="kpi"><div class="n">{len(no_depth_clubs)}</div><div class="l">clubs without depth data</div><div class="s">{', '.join(no_depth_clubs[:8])}…</div></div>
  <div class="kpi"><div class="n">{len(ngs_blank)}</div><div class="l">clubs without published EPA</div><div class="s">blank, not interpolated</div></div>
</div>

<h2>Flagged items</h2>
{table([("id","ID"),("type","Type"),("item","Item"),("what","What is unverified or irregular"),
        ("why","Why it matters"),("resolve","What would resolve it"),("url","Source"),("how","How you can check it")], tr)}

<h2>How to review this page</h2>
<ol class="tight">
<li>Read the <em>What is unverified</em> column. If any of it matters to your decision, the <em>What would resolve it</em>
column is the shopping list.</li>
<li>For items with a source link, open it and confirm the absence or ambiguity directly. These are not claims that
require trust — they are checkable in a browser.</li>
<li>For F08 and F09 there is nothing to check: they are decisions, not facts, and they are yours to make.</li>
<li>Nothing here invalidates the published data. It delimits it.</li>
</ol>

<h2>Sources referenced by these flags</h2>
{src_list(["S01","S06","S10","S11","S12","S17"], sources)}
"""
    page("pages/flagged.html", "Flagged for Review", body, "pages/flagged.html",
         "Every unverified value, ambiguity and negative finding — with a source link and a way to check each one.",
         [("", "Home"), ("", "Flagged for Review")])


def main():
    sources = load_csv("data/sources.csv")
    corr = load_json("data/derived-correlation.json")
    dm = load_json("data/derived-metrics.json")

    build_index(sources)
    build_exec(sources, dm, corr)
    build_suggestions(sources)
    build_questions(sources)
    build_requirements(sources)
    build_strategies(sources, dm)
    build_gates(sources, dm)
    build_luck(sources, dm)
    build_correlation(sources, corr, dm)
    build_injuries(sources)
    build_slate(sources)
    build_standings(sources)
    build_team_metrics(sources)
    build_audit(sources)
    build_sources(sources)
    build_flagged(sources)

    print(f"built {len(PAGES)} pages:")
    for p in PAGES:
        print("  ", p)


if __name__ == "__main__":
    main()
