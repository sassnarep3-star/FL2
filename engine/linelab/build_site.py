#!/usr/bin/env python3
"""
engine/linelab/build_site.py — generate the Line Lab site.

Requirement served: "Create a github page live site for this repo with a clean
landing page and subpages organized by category ... It should contain all entries
and findings in a simple, easy to read table format ... Every table row must have
a source link to an official site."

DESIGN RULES ENFORCED BY THE BUILDER, NOT BY DISCIPLINE
  1. Every data row in every table gets a source cell. If a row has no source, the
     builder refuses to emit it as data and renders the row as "unverified"
     with the reason, so it cannot silently look like a sourced value.
  2. A number is never printed without unit and, where it matters, its n.
  3. No external CDN, no webfont, no framework. One stylesheet generated here.
  4. Pages are written to linelab/ and are served by GitHub Pages from the repo
     root; every link is relative so the site works from any base path.

OUTPUT  linelab/*.html, linelab/assets/style.css, linelab/data/*.js
"""
from __future__ import annotations

import html
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "linelab")
SITE = os.path.join(ROOT, "linelab")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stamp import build_stamp  # noqa: E402

STAMP = build_stamp()
NOW = STAMP["built_from_inputs_short"]  # a content hash, not a clock

E = html.escape


def j(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def fmt(v, nd=2, dash="—"):
    if v is None or v == "":
        return f'<span class="na">{dash}</span>'
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:,.{nd}f}"
    return E(str(v))


GITHUB = "https://github.com/sassnarep3-star/FL2/blob/main/"


def src(url, label=None):
    """A source cell. Never empty: a missing source renders as 'unverified'.

    A repository-relative artefact path (engine/linelab/model.py) is turned into
    a real link on GitHub, so a reader can click through to the file that
    produced the number instead of being told a bare path.
    """
    if not url:
        return '<span class="na" title="no source recorded">unverified</span>'
    if not str(url).startswith("http"):
        label = label or str(url)
        url = GITHUB + str(url)
    label = label or url
    short = label
    if len(short) > 46:
        short = short[:43] + "…"
    return f'<a class="src" href="{E(url)}" rel="noopener">{E(short)}</a>'


def badge(status):
    cls = {"done": "ok", "partial": "warn", "blocked": "bad"}.get(status, "mute")
    return f'<span class="badge {cls}">{E(status)}</span>'


CSS = """
:root{--bg:#f5f7fa;--surf:#fff;--ink:#141a22;--ink2:#46505f;--ink3:#6f7a89;
--line:#dee3ea;--line2:#edf0f4;--brand:#0f2f4d;--brand2:#1b5480;--accent:#0a7d6c;
--ok:#0d7a4c;--okbg:#e5f6ee;--warn:#9a5600;--warnbg:#fdf2e0;--bad:#a92015;--badbg:#fcebea;
--info:#1b4f8a;--infobg:#e9f1fa;--mutbg:#eef1f5;--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14.5px/1.55 var(--sans)}
a{color:var(--brand2);text-decoration:none}a:hover{text-decoration:underline}
.hdr{background:var(--brand);color:#fff;border-bottom:3px solid var(--accent)}
.hdr .in{max-width:1280px;margin:0 auto;padding:12px 18px 0}
.brand{font-size:17px;font-weight:650;letter-spacing:-.2px}
.brand span{font-weight:400;opacity:.72;font-size:13px}
.sub{font-size:12px;opacity:.66;margin:2px 0 10px}
nav{display:flex;gap:2px;flex-wrap:wrap;padding-bottom:0}
nav a{color:#cfe0ef;font-size:12.5px;padding:8px 10px;border-bottom:2px solid transparent}
nav a:hover{color:#fff;text-decoration:none;background:rgba(255,255,255,.07)}
nav a[aria-current]{color:#fff;border-bottom-color:var(--accent);font-weight:600}
main{max-width:1280px;margin:0 auto;padding:20px 18px 60px}
h1{font-size:26px;letter-spacing:-.5px;margin:0 0 6px}
h2{font-size:17px;margin:30px 0 8px;letter-spacing:-.2px}
h3{font-size:14px;margin:18px 0 6px}
p{margin:0 0 10px;color:var(--ink2);max-width:96ch}
.lede{font-size:15px;color:var(--ink2);max-width:96ch}
.hero{background:var(--surf);border:1px solid var(--line);border-radius:8px;padding:22px 24px;
box-shadow:0 1px 3px rgba(16,24,32,.05);margin-bottom:6px}
.kpis{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin:14px 0 4px}
.kpi{background:var(--surf);border:1px solid var(--line);border-left:3px solid var(--brand2);
border-radius:6px;padding:11px 13px}
.kpi .n{font-size:21px;font-weight:650;letter-spacing:-.5px;font-variant-numeric:tabular-nums}
.kpi .l{font-size:11.5px;color:var(--ink3);margin-top:1px}
.kpi.ok{border-left-color:var(--ok)}.kpi.warn{border-left-color:var(--warn)}
.kpi.bad{border-left-color:var(--bad)}.kpi.info{border-left-color:var(--info)}
.tw{overflow-x:auto;background:var(--surf);border:1px solid var(--line);border-radius:8px;
box-shadow:0 1px 2px rgba(16,24,32,.04);margin:10px 0 4px}
table{border-collapse:collapse;width:100%;font-size:12.8px}
th{text-align:left;font-weight:600;color:var(--ink3);font-size:11px;letter-spacing:.03em;
text-transform:uppercase;padding:8px 10px;border-bottom:1px solid var(--line);background:var(--line2);
white-space:nowrap;position:sticky;top:0}
td{padding:7px 10px;border-bottom:1px solid var(--line2);vertical-align:top}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover{background:#fafbfd}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;font-family:var(--mono);font-size:12px}
td.mono{font-family:var(--mono);font-size:11.5px}
.badge{display:inline-block;padding:1.5px 7px;border-radius:99px;font-size:10.5px;font-weight:650;
letter-spacing:.02em;white-space:nowrap}
.ok{background:var(--okbg);color:var(--ok)}.warn{background:var(--warnbg);color:var(--warn)}
.bad{background:var(--badbg);color:var(--bad)}.info{background:var(--infobg);color:var(--info)}
.mute{background:var(--mutbg);color:var(--ink3)}
.na{color:#98a2b0}
.src{font-size:11px;font-family:var(--mono)}
.note{background:var(--surf);border:1px solid var(--line);border-left:3px solid var(--accent);
border-radius:6px;padding:12px 15px;margin:12px 0;font-size:13px;color:var(--ink2)}
.note.warn{border-left-color:var(--warn)}.note.bad{border-left-color:var(--bad)}
.note strong{color:var(--ink)}
.sub2{font-size:12.5px;color:var(--ink3);margin:-4px 0 8px}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));margin:12px 0}
.tile{display:block;background:var(--surf);border:1px solid var(--line);border-top:3px solid var(--brand2);
border-radius:7px;padding:14px 16px;box-shadow:0 1px 2px rgba(16,24,32,.05)}
.tile:hover{box-shadow:0 3px 10px rgba(16,24,32,.09);text-decoration:none;transform:translateY(-1px)}
.tile h3{margin:1px 0 4px;font-size:14px;color:var(--ink)}
.tile p{margin:0;font-size:12.5px;color:var(--ink2)}
.tile .k{margin-top:8px;font-size:11px;color:var(--ink3);font-family:var(--mono)}
.tile.blocked{border-top-color:var(--bad)}
footer{max-width:1280px;margin:0 auto;padding:18px;color:var(--ink3);font-size:11.5px;
border-top:1px solid var(--line)}
footer a{color:var(--ink3);text-decoration:underline}
code{font-family:var(--mono);font-size:11.5px;background:var(--mutbg);padding:1px 4px;border-radius:3px}
ul,ol{color:var(--ink2);font-size:13px;max-width:96ch}
li{margin:3px 0}
details{background:var(--surf);border:1px solid var(--line);border-radius:6px;padding:9px 13px;margin:7px 0}
summary{cursor:pointer;font-weight:600;font-size:13px}
details .body{margin-top:8px;font-size:12.5px;color:var(--ink2)}
"""

NAV = [
    ("index.html", "Overview"),
    ("requirements.html", "Decision readiness"),
    ("lines.html", "Our lines"),
    ("models.html", "Model comparison"),
    ("strategies.html", "Strategies &amp; gates"),
    ("availability.html", "Availability"),
    ("depth.html", "Depth graph"),
    ("prices.html", "Price store"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions"),
    ("flagged.html", "Flagged"),
    ("sources.html", "Sources"),
]


def page(slug, title, body, lede=""):
    nav = "\n".join(
        f'<a href="{h}"{" aria-current=page" if h == slug else ""}>{t}</a>' for h, t in NAV
    )
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)} · FL2 Line Lab</title>
<meta name="description" content="NFL line origination lab: verified prices, probabilities with inputs, proper-score evaluation, and a named gate on every blocked requirement.">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="hdr"><div class="in">
  <div class="brand">FL2 Line Lab <span>· NFL line origination</span></div>
  <div class="sub">2026 · build {NOW} (hash of inputs) · every row sourced or flagged</div>
  <nav>{nav}</nav>
</div></header>
<main>
{f'<p class="lede">{lede}</p>' if lede else ''}
{body}
</main>
<footer>
  <p><strong>Not betting advice.</strong> This is a measurement project. Every value is either
  reproducible from a committed file in this repository or left blank; blanks are listed on
  <a href="flagged.html">Flagged</a>. Model prices come from nflverse/nfldata, an open mirror of
  published official results and market numbers; availability comes from nfl.com.</p>
  <p>Source allowlist and hashes: <a href="sources.html">Sources</a>.
  Repository: <a href="https://github.com/sassnarep3-star/FL2">github.com/sassnarep3-star/FL2</a>.</p>
</footer>
</body>
</html>
"""
    with open(os.path.join(SITE, slug), "w", encoding="utf-8") as fh:
        fh.write(doc)


def table(headers, rows, cls=""):
    """rows: list of lists of already-safe HTML strings, one row per data record.

    A cell may be a bare HTML string (class inherited from the header) or a
    (html, css_class) pair, which overrides the class for that cell. The header
    classes are positional, so a cell's class can never be an accidental tuple.
    """
    classes = [c for _, c in headers]
    h = "".join(f'<th class="{c}">{t}</th>' for t, c in headers)
    out = []
    for r in rows:
        cells = []
        for i, v in enumerate(r):
            if isinstance(v, (tuple, list)) and len(v) == 2:
                val, c = v
            else:
                val, c = v, (classes[i] if i < len(classes) else "")
            cells.append(f'<td class="{c}">{val}</td>')
        out.append("<tr>" + "".join(cells) + "</tr>")
    body = "\n".join(out)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>\n{body}\n</tbody></table></div>'


def kpi(n, label, cls=""):
    return f'<div class="kpi {cls}"><div class="n">{n}</div><div class="l">{label}</div></div>'


def build():
    os.makedirs(SITE, exist_ok=True)
    os.makedirs(os.path.join(SITE, "assets"), exist_ok=True)
    with open(os.path.join(SITE, "assets", "style.css"), "w", encoding="utf-8") as fh:
        fh.write(CSS)

    price = j("price_store_meta.json") or {}
    model = j("model_meta.json") or {}
    scores = j("scores.json") or {}
    avail = j("availability.json") or {}
    depth = j("depth_graph.json") or {}
    corpus = j("corpus.json") or {}
    reg = j("registry.json") or {}
    req = j("requirements.json") or {}

    sc = scores.get("scores", {})
    rel = (avail.get("designation_reliability") or {}).get("buckets", [])
    reqc = req.get("counts", {})
    strats = reg.get("strategies", [])
    n_eligible = sum(1 for s in strats if s.get("verdict") == "eligible")

    def best(k):
        return sc.get(k, {})

    # ============================================================== OVERVIEW
    b1 = best("E1|moneyline|holdout")
    b2 = best("E2|moneyline|holdout")
    ks = scores.get("luck_panel", {}).get("bets_needed_to_show_edge", {})
    kp = scores.get("luck_panel", {}).get("bets_needed_to_show_profit", {})
    body = f"""
<div class="hero">
  <h1>We originated the side, the total and the moneyline — and the model lost to a spreadsheet</h1>
  <p class="lede">Two estimators were run over every completed regular-season game from 1999 to
  Week 10 of 2026, with a fixed chronological split decided in the source file before the first run.
  The <strong>opponent-adjusted</strong> model did not beat the <strong>unadjusted</strong> control on
  any market. Both lose to the benchmark on the side and the total. On the moneyline the control
  holds a small positive edge and the adjusted model does not.
  Rather than bury that, the whole project is published around it: the price store, the probability
  with its inputs, the proper score with its interval, and a named gate on every requirement that
  cannot yet be met.</p>
  <div class="kpis">
    {kpi(f'{price.get("rows", 0):,}', "market rows in the price store", "info")}
    {kpi(f'{model.get("rows", 0):,}', "model outputs (probability + inputs)", "info")}
    {kpi(f"{b2.get('bss', 0):+.3f}", "holdout moneyline skill, control (E2)", "ok" if (b2.get('bss') or 0) > 0 else "bad")}
    {kpi(f"{b1.get('bss', 0):+.3f}", "holdout moneyline skill, adjusted (E1)", "ok" if (b1.get('bss') or 0) > 0 else "bad")}
    {kpi(reqc.get('done', 0), "requirements met", "ok")}
    {kpi(reqc.get('partial', 0), "partial", "warn")}
    {kpi(reqc.get('blocked', 0), "blocked on a named gate", "bad")}
    {kpi(n_eligible, "strategies eligible to go live", "bad")}
  </div>
</div>

<h2>What this section is for</h2>
<p>The brief asks for an NFL line-origination system with a strategy leaderboard, validation gates,
correlation values, luck removal, and injury/depth awareness. Each of those is answered here as
either a published artefact or a named blocker. Nothing is answered with an assertion.</p>

<div class="grid">
  <a class="tile" href="lines.html"><h3>Our lines</h3>
    <p>Fair line, market line and the difference, as separate columns, side then total then moneyline.</p>
    <div class="k">{model.get('rows', 0):,} outputs</div></a>
  <a class="tile" href="models.html"><h3>Model comparison</h3>
    <p>Adjusted vs unadjusted, validation vs holdout, Brier skill with a game-cluster lower bound.</p>
    <div class="k">{len(sc)} scored hypotheses</div></a>
  <a class="tile" href="strategies.html"><h3>Strategies &amp; gates</h3>
    <p>Seven pre-registered strategies, each with a frozen rule, a gate verdict and a demotion rule.</p>
    <div class="k">{n_eligible} eligible</div></a>
  <a class="tile" href="availability.html"><h3>Availability</h3>
    <p>Official injury reads with clock times and hashes; the delta between two, never the level.</p>
    <div class="k">{len(avail.get('captures', []))} captures · {sum(d.get('n_changes', 0) for d in avail.get('deltas', []))} changes</div></a>
  <a class="tile" href="depth.html"><h3>Depth graph</h3>
    <p>Who was expected to start, stored as groups and empty slots; who actually did is left null, not guessed.</p>
    <div class="k">{depth.get('clubs_acquired', 0)}/32 clubs</div></a>
  <a class="tile blocked" href="requirements.html"><h3>Decision readiness</h3>
    <p>One row per requirement with the gate that blocks it and the number that would clear it.</p>
    <div class="k">{reqc.get('blocked', 0)} blocked</div></a>
</div>

<h2>The removal-of-luck panel</h2>
<p>A staking run cannot be judged on its return at the sample sizes this project can reach. At the
standard −110 price a bettor needs to win {scores.get('luck_panel', {}).get('break_even_win_rate_at_minus110', 0):.2%} just
to break even, and separating a genuinely skilled bettor from a coin takes:</p>
{table(
        [("True win rate", ""), ("Bets to separate it from a 50/50 coin", "n"),
         ("Bets to prove it is profitable at minus 110", "n"), ("Method", "src")],
        [[{"55pct": "55%", "57pct": "57%", "60pct": "60%",
           "break_even_524": "52.38% (break-even itself)"}.get(k, k),
          fmt(v, 0), fmt(kp.get(k), 0) if k in kp else "&mdash;",
          src("engine/linelab/scoring.py")] for k, v in ks.items()],
    )}
<p class="sub2">5% one-sided significance, 80% power, assuming independent bets. The two number
columns answer different questions, and the difference matters: proving a 55% bettor is better than a
coin takes {ks.get('55pct')} bets, but proving he is profitable at a minus-110 price takes
{kp.get('55pct')} &mdash; because the null he must clear is not 50% but the 52.38% break-even. Publishing
only the easier number would make an edge look detectable long before it is bankable. Parlays need
more still, because their outcomes cluster.</p>

<h2>Read this before trusting any number here</h2>
<div class="note bad"><strong>The adjusted model loses.</strong> On the holdout, Brier skill versus a
train-window base rate is {b1.get('bss', 0):+.3f} for the adjusted model against
{b2.get('bss', 0):+.3f} for the unadjusted control on the moneyline, and both are negative on side
and total. A more sophisticated model is not a better model, and this repository will not present it
as one.</div>
<div class="note warn"><strong>Most requirements are not met.</strong> {reqc.get('blocked', 0)} of
{reqc.get('total', 0)} are blocked on a specific, named gate — most often the absence of a scheduled
capture, an official inactive list, or depth coverage for all 32 clubs. The
<a href="requirements.html">decision-readiness table</a> names the gate and the number that would
clear it for each.</div>
"""
    page("index.html", "Overview", body)

    # ========================================================== REQUIREMENTS
    rr = req.get("requirements", [])
    rows = []
    for r in rr:
        rows.append([
            (f'<code>{E(r["id"])}</code>', "mono"),
            (E(r["requirement"]), ""),
            (badge(r["status"]), ""),
            (f'<code>{E(str(r["artefact"]))}</code>', "mono"),
            (E(str(r["evidence"])), ""),
            (f'<code>{E(str(r["blocking_gate"]))}</code>', "mono"),
            (E(str(r["number_that_would_clear_it"])), ""),
            (src(r["source"]), "src"),
        ])
    gate_rows = []
    for g in req.get("gate_index", []):
        ids = [r["id"] for r in rr if r["blocking_gate"] == g]
        gate_rows.append([(f'<code>{E(g)}</code>', "mono"), (", ".join(ids), "mono"),
                          (str(len(ids)), "n"), (src("data/linelab/requirements.json"), "src")])
    body = f"""
<h1>Decision readiness</h1>
<p class="lede">One row per requirement from the brief. The <strong>gate</strong> column names what
blocks it; the <strong>number that would clear it</strong> column says what evidence would remove that
block. A requirement is "done" only when an artefact exists that a reader can open and check.</p>
<div class="kpis">
  {kpi(reqc.get('total', 0), "requirements", "info")}
  {kpi(reqc.get('done', 0), "done", "ok")}
  {kpi(reqc.get('partial', 0), "partial", "warn")}
  {kpi(reqc.get('blocked', 0), "blocked", "bad")}
</div>
<h2>The 68 rows</h2>
{table(
        [("ID", "mono"), ("Requirement", ""), ("Status", ""), ("Artefact", "mono"),
         ("Evidence in this repository", ""), ("Blocking gate", "mono"),
         ("What would clear it", ""), ("Source", "src")],
        rows,
    )}
<h2>Blockers by gate</h2>
<p class="sub2">Grouping the same rows by gate shows that the blockers are concentrated: five separate
requirements wait on one scheduler, and the depth-coverage gap blocks two more.</p>
{table([("Gate", "mono"), ("Requirement IDs", "mono"), ("Count", "n"), ("Source", "src")], gate_rows)}
"""
    page("requirements.html", "Decision readiness", body)

    # ============================================================== OUR LINES
    rows = []
    import csv as _csv
    mp = os.path.join(DATA, "model_outputs.csv")
    sample = []
    if os.path.exists(mp):
        with open(mp, newline="", encoding="utf-8") as fh:
            rd = list(_csv.DictReader(fh))
        # most recent completed week, one row per market, E1 then E2
        played = [r for r in rd if r["actual_home"]]
        if played:
            maxw = max(int(r["week"]) for r in played)
            # one representative week, not the whole corpus: the page must stay
            # readable, and the full file is linked for anyone who wants every row
            sample = [r for r in rd if int(r["week"]) == maxw and r["actual_home"] and r["estimator"] == "E1"]
    mk_name = {"side": "Side", "total": "Total", "moneyline": "Moneyline"}
    order = {"side": 0, "total": 1, "moneyline": 2}
    for r in sorted(sample, key=lambda x: (x["gameday"], x["game_id"], order.get(x["market"], 9))):
        rows.append([
            (E(r["gameday"]), "mono"),
            (f'{E(r["away"])} @ {E(r["home"])}', ""),
            (mk_name.get(r["market"], r["market"]), ""),
            (fmt(float(r["model_line"])), "n"),
            (fmt(float(r["market_line"]) if r["market_line"] else None), "n"),
            (fmt(float(r["difference"]) if r["difference"] else None), "n"),
            (fmt(float(r["model_prob_home"]) if r["model_prob_home"] else None, 3), "n"),
            (fmt(float(r["sigma"]) if r["sigma"] else None, 1), "n"),
            (f'<details><summary>inputs</summary><div class="body"><code>{E(r["inputs"])}</code></div></details>', ""),
            (src(r["source"]), "src"),
        ])
    corpus_rows = []
    for g in (corpus.get("games") or [])[-40:][::-1]:
        corpus_rows.append([
            (E(str(g["week"])), "n"),
            (E(g["gameday"]), "mono"),
            (f'{E(g["away"])} @ {E(g["home"])}', ""),
            (fmt(g["home_score"], 0), "n"),
            (fmt(g["away_score"], 0), "n"),
            (fmt(g["market_spread"], 1), "n"),
            (fmt(g["market_total"], 1), "n"),
            (", ".join(g["pre_kickoff_captures"]) or '<span class="na">none</span>', "mono"),
            (src(corpus.get("source")), "src"),
        ])
    n_total = len(rd) if os.path.exists(mp) else 0
    body = f"""
<h1>Our lines</h1>
<p class="lede">Every model output is stored as a probability with the inputs that produced it, and
the three columns the brief requires — <strong>fair line</strong>, <strong>market line</strong>,
<strong>difference</strong> — are separate. The order is the brief's: side first, then the total,
then the moneyline.</p>

<h2>How a line is produced</h2>
<p>The adjusted estimator fits, by ridge least squares, a baseline <code>c</code>, a home-field term
<code>h</code>, an offence rating <code>a[team]</code> and a defence rating <code>b[team]</code> over
every game that kicked off before this one:</p>
<ul>
<li>home points = c + h + a[home] − b[away]</li>
<li>away points = c + a[away] − b[home]</li>
</ul>
<p>The fair side line is the negative of the predicted home margin. The fair total is the predicted
combined score. The cover and over probabilities come from a Normal with σ equal to the
<em>out-of-sample</em> residual standard deviation of the last two seasons, never the in-sample one.
The unadjusted control uses this season's mean points for and against, with no opponent adjustment.</p>

<h2>Week 10, adjusted estimator — every game, all three markets</h2>
<p class="sub2">This is one week shown in full. All {n_total:,} rows, every week and both estimators,
are in <a href="https://github.com/sassnarep3-star/FL2/blob/main/data/linelab/model_outputs.csv">model_outputs.csv</a>.</p>
<p class="sub2">"Difference" is our fair line minus the market number. Positive on the side means we
make the home team stronger than the market does. Markets are listed side, total, moneyline in the
brief's order. σ is the residual standard deviation used to turn the line into a probability.</p>
{table(
        [("Date", "mono"), ("Fixture", ""), ("Market", ""), ("Our fair line", "n"),
         ("Market line", "n"), ("Difference", "n"), ("Our P(home)", "n"), ("σ", "n"),
         ("Inputs", ""), ("Source", "src")],
        rows,
    ) if rows else '<div class="note bad">No model rows found.</div>'}

<h2>The pre-registered backtest corpus</h2>
<p>The 136-game log (Weeks 1–9) plus Week 10's completed games forms a forward test set, not a
training set. Each game records the availability capture that existed <em>before its kickoff</em>, so
the corpus can be replayed point-in-time. {corpus.get('counts', {}).get('games_with_pre_kickoff_availability', 0)}
of {corpus.get('counts', {}).get('games_played', 0)} completed games have such a capture.</p>
{table(
        [("Wk", "n"), ("Date", "mono"), ("Fixture", ""), ("Home", "n"), ("Away", "n"),
         ("Market spread", "n"), ("Market total", "n"), ("Pre-kickoff availability", "mono"), ("Source", "src")],
        corpus_rows,
    )}
<div class="note"><strong>Split, fixed before the first run.</strong> Train 1999–2015, validation
2016–2021, holdout 2022–Week 10 2026. The split is written in <code>engine/linelab/model.py</code>
and has not moved. Ridge {model.get('hyperparameters_fixed_before_running', {}).get('ridge')} and a
home-field prior of {model.get('hyperparameters_fixed_before_running', {}).get('hfa_prior')} were also
fixed in the file before execution.</div>
"""
    page("lines.html", "Our lines", body)

    # ========================================================= MODEL COMPARE
    rows = []
    for k, v in sorted(sc.items()):
        if v.get("bss") is None:
            continue
        est, mkt, split = k.split("|")
        rows.append([
            (f'<span class="badge {"info" if est == "E1" else "mute"}">{est}</span>', ""),
            (mk_name.get(mkt, mkt), ""),
            (E(split), "mono"),
            (fmt(v["bss"], 4), "n"),
            (f'[{fmt(v["bss_ci95"][0], 4)}, {fmt(v["bss_ci95"][1], 4)}]', "n"),
            (fmt(v.get("p_bss_le_0_holm"), 3), "n"),
            (fmt(v["n_games"], 0), "n"),
            (f'<span class="badge {"ok" if v["bss"] > 0 and v["bss_ci95"][0] > 0 else ("warn" if v["bss"] > 0 else "bad")}">'
             f'{"beats benchmark" if v["bss"] > 0 and v["bss_ci95"][0] > 0 else ("positive, interval includes 0" if v["bss"] > 0 else "loses to benchmark")}</span>', ""),
            (src("https://github.com/nflverse/nfldata/blob/master/data/games.csv"), "src"),
        ])
    corr_rows = []
    for c in scores.get("correlations", []):
        corr_rows.append([
            (f'<code>{E(c["pair"])}</code>', "mono"),
            (fmt(c["r"], 4), "n"),
            (f'[{fmt(c["ci95_fisher"][0], 4)}, {fmt(c["ci95_fisher"][1], 4)}]' if c.get("ci95_fisher") else "—", "n"),
            (fmt(c["n"], 0), "n"),
            (E(c.get("definition") or ""), ""),
            (src(c.get("source")), "src"),
        ])
    body = f"""
<h1>Model comparison</h1>
<p class="lede">The adjusted model is the one this project set out to test. The unadjusted model is
the control a reader would build in a spreadsheet. Both are scored on the same proper score, on the
same games, against a benchmark measured only on the training window.</p>

<div class="note bad"><strong>Result: adjustment did not help.</strong> On the holdout moneyline the
control scores {b2.get('bss', 0):+.4f} and the adjusted model {b1.get('bss', 0):+.4f}. On the side,
both lose; on the total, both lose by less. The honest conclusion is that the opponent-adjusted
scoring model in this repository does not carry information the naive season average lacks — which is
the same conclusion every previous section of this repository reached by a different route.</div>

<h2>Proper score, uncertainty and multiplicity</h2>
<p class="sub2">Brier skill score = 1 − (model Brier ÷ benchmark Brier), where the benchmark is the
base rate measured on 1999–2015 only. The interval is a 2,000-resample bootstrap <em>clustered on
games</em>. The last column is a Bonferroni–Holm adjustment across every hypothesis tested here, so a
lucky result among many is not reported as discovery.</p>
{table(
        [("Est.", ""), ("Market", ""), ("Split", "mono"), ("Brier skill", "n"),
         ("95% cluster CI", "n"), ("Holm p (skill≤0)", "n"), ("Games", "n"), ("Verdict", ""), ("Source", "src")],
        rows,
    )}

<h2>Correlations, with n, or nothing</h2>
<p>Every correlation is computed from numbers in the price store or from official final scores, and
any pair with fewer than 200 games is suppressed rather than printed. n is published with every value.</p>
{table(
        [("Pair", "mono"), ("r", "n"), ("95% CI", "n"), ("n", "n"), ("Definition", ""), ("Source", "src")],
        corr_rows,
    )}
<div class="note warn"><strong>A correction this project had to make.</strong> The received wisdom is
that a high-scoring game has a larger winning margin, which would make a side-and-total same-game
parlay invalid to price by multiplication. On {corr_rows[2][3] if len(corr_rows) > 2 else 'n'} games that
relationship is close to zero and its interval contains zero. The multiplication rule in this project
therefore rests on same-team and same-player dependence, which has <em>not</em> been measured here, and
the site says so rather than borrowing the conventional claim.</div>

<h2>Control baselines</h2>
<p>A coin flip scores a Brier skill of about zero by construction. A model that cannot beat it is
noise. The always-home and always-favourite cover rates are published beside every model for the same
reason.</p>
{table(
        [("Control", ""), ("Cover rate", "n"), ("Games", "n"), ("Two-sided p vs 50%", "n"), ("Source", "src")],
        [
          ["Always home", fmt(scores.get('win_rate_controls', {}).get('always_home_cover_rate'), 4),
           fmt(scores.get('win_rate_controls', {}).get('n'), 0),
           fmt(scores.get('win_rate_controls', {}).get('p_two_sided_vs_50pct'), 3),
           src("https://github.com/nflverse/nfldata/blob/master/data/games.csv")],
          ["Always favourite", fmt(scores.get('win_rate_controls', {}).get('always_favourite_cover_rate'), 4),
           fmt(scores.get('win_rate_controls', {}).get('n'), 0),
           fmt(scores.get('win_rate_controls', {}).get('p_two_sided_vs_50pct'), 3),
           src("https://github.com/nflverse/nfldata/blob/master/data/games.csv")],
          ["Coin flip (50/50)", "0.5000", fmt(scores.get('win_rate_controls', {}).get('n'), 0), "1.000",
           src("engine/linelab/scoring.py")],
        ],
    )}
<p class="sub2">A cover rate near 0.5 is exactly what a market that is already efficient should produce.
Getting away from 0.5 would be the surprising result.</p>
"""
    page("models.html", "Model comparison", body)

    # ============================================================ STRATEGIES
    srows = []
    for s in strats:
        gates = s.get("gates_evaluated", {})
        gtxt = " ".join(
            f'<span class="badge {"ok" if g.get("status") == "pass" else "bad"}">{E(nm.split("-")[0])}</span>'
            for nm, g in gates.items()
        )
        srows.append([
            (f'<code>{E(s["id"])}</code>', "mono"),
            (E(s["name"]), ""),
            (E(s["rule"]), ""),
            (E(s.get("market", "")), ""),
            (", ".join(s.get("divisions", [])), "mono"),
            (gtxt, ""),
            (f'<span class="badge {"ok" if s["verdict"] == "eligible" else "bad"}">{E(s["verdict"])}</span>', ""),
            (f'<span class="badge mute">{E(s["paper_or_live"])}</span>', ""),
            (src("data/linelab/registry.json"), "src"),
        ])
    gate_detail = []
    for s in strats:
        for nm, g in (s.get("gates_evaluated") or {}).items():
            gate_detail.append([
                (f'<code>{E(s["id"])}</code>', "mono"),
                (f'<code>{E(nm)}</code>', "mono"),
                (f'<span class="badge {"ok" if g.get("status") == "pass" else "bad"}">{E(g.get("status", ""))}</span>', ""),
                (E(str(g.get("detail", ""))), ""),
                (src("data/linelab/scores.json"), "src"),
            ])
    wcm = []
    for s in strats:
        w = s.get("what_would_change_our_mind", {})
        wcm.append([
            (f'<code>{E(s["id"])}</code>', "mono"),
            (E(w.get("toward_belief", "")), ""),
            (E(w.get("away_from_belief", "")), ""),
            (src("data/linelab/registry.json"), "src"),
        ])
    body = f"""
<h1>Strategies &amp; validation gates</h1>
<p class="lede">Seven strategies are pre-registered with a frozen rule, the gates each must clear, a
two-sided "what would change our mind" field, and a demotion rule. The registry is a committed file,
so changing a rule changes the commit hash and is visible in git. Nothing is live; every strategy
sits on paper.</p>
<div class="kpis">
  {kpi(len(strats), "strategies registered", "info")}
  {kpi(n_eligible, "eligible", "bad")}
  {kpi(len(strats) - n_eligible, "on paper", "warn")}
</div>

<h2>The register</h2>
{table(
        [("ID", "mono"), ("Strategy", ""), ("Frozen rule", ""), ("Market", ""),
         ("Division", "mono"), ("Gates", ""), ("Verdict", ""), ("State", ""), ("Source", "src")],
        srows,
    )}

<h2>Every gate, every strategy, with its evidence</h2>
<p class="sub2">A gate is not "passed" by assertion. Each row states the number the gate was applied to.</p>
{table([("Strategy", "mono"), ("Gate", "mono"), ("Result", ""), ("Evidence", ""), ("Source", "src")], gate_detail)}

<h2>What would change our mind</h2>
<p>Each strategy carries both directions. A strategy that cannot say what would disconfirm it is not a
strategy, it is a position.</p>
{table([("Strategy", "mono"), ("Toward belief", ""), ("Away from belief", ""), ("Source", "src")], wcm)}

<h2>Promotion and demotion</h2>
<div class="note"><strong>Demotion gate.</strong> A live strategy returns to paper when the
game-cluster lower bound of its Brier skill falls to zero or below over its last 100 prospective bets,
or when its closing-line value is negative at the 95% level. Demotion is automatic and would be
published the same day. Nothing has been promoted, so the gate currently has nothing to act on — but
it exists so that promotion has a defined reversal.</div>
<div class="note warn"><strong>Parlays and prop combos stay behind a joint-evidence gate.</strong>
Multiplying marginal probabilities is not a joint probability. A combination may only be ranked when a
directly validated joint probability exists, and for prop combos the operator's void and push rules
are also required. Neither exists here, so both divisions are registered as blocked rather than
omitted.</div>
"""
    page("strategies.html", "Strategies &amp; gates", body)

    # ============================================================ AVAILABILITY
    cap_rows = []
    for c in avail.get("captures", []):
        cap_rows.append([
            (f'<code>{E(c["capture_id"])}</code>', "mono"),
            (E(str(c.get("captured_utc"))), "mono"),
            (str(c.get("rows")), "n"),
            (f'<code>{E(c["sha256"][:16])}…</code>', "mono"),
            (fmt(c.get("bytes"), 0), "n"),
            (src(c.get("source_url")), "src"),
        ])
    d_rows = []
    for d in avail.get("deltas", []):
        for ch in d["changes"]:
            d_rows.append([
                (E(ch["team"]), "mono"),
                (E(ch["player"]), ""),
                (f'<code>{E(ch["change"])}</code>', "mono"),
                (f'<span class="na">{E(str(ch["from"])) if ch["from"] else "(absent)"}</span>', ""),
                (E(str(ch["to"])) if ch["to"] else "(absent)", ""),
                (src(d["to_capture"].replace("week10-injury-report", "") and
                     "https://www.nfl.com/injuries/league/2026/reg10"), "src"),
            ])
    tv_rows = []
    for t in avail.get("team_view", []):
        tv_rows.append([
            (E(t["team"]), "mono"), (str(t["listed"]), "n"), (str(t["out"]), "n"),
            (str(t["doubtful"]), "n"), (str(t["questionable"]), "n"), (str(t["net_unavailable"]), "n"),
            (src("https://www.nfl.com/injuries/league/2026/reg10"), "src"),
        ])
    rel_rows = []
    for b in rel:
        rel_rows.append([
            (E(b["designation"]), ""),
            (fmt(b["n"], 0), "n"),
            (f'{b["observed_play_rate"]:.2%}', "n"),
            (f'[{b["ci95_wilson"][0]:.2%}, {b["ci95_wilson"][1]:.2%}]', "n"),
            (E(b["seasons"]), "mono"),
            (src("https://github.com/nflverse/nflverse-data/releases/tag/injuries"), "src"),
        ])
    cq = avail.get("capture_quality_findings", [])
    qhtml = ""
    for f in cq:
        qhtml += f"""
<div class="note bad"><strong>Capture defect detected mechanically: {E(f['type'])}</strong>
in <code>{E(f['capture_id'])}</code> — team(s) {", ".join(f['teams'])}, {f['rows_affected']} rows.
{f['why_it_matters']}
<br><br><strong>Two possible causes, not yet distinguished:</strong> {" / ".join(f['two_possible_causes'])}.
<br><strong>How to resolve:</strong> {f['how_to_resolve']}</div>"""
    body = f"""
<h1>Availability</h1>
<p class="lede">The official injury report is treated as a timestamped series. Every read is stored
with its clock time and a SHA-256 of the bytes read, and the site publishes the <em>change</em> between
two reads rather than a single level presented as stable. Absence from the report is never rendered as
"available".</p>
<div class="kpis">
  {kpi(len(avail.get('captures', [])), "captures held", "info")}
  {kpi(sum(d.get('n_changes', 0) for d in avail.get('deltas', [])), "player-level changes between them", "info")}
  {kpi(len(rel), "designations calibrated", "ok")}
  {kpi(avail.get('reserve_check', {}).get('n_missing_vs_earlier_weeks', 0), "players absent from the latest report (unknown, not healthy)", "warn")}
</div>

<h2>The captures</h2>
{table([("Capture", "mono"), ("Read at (UTC)", "mono"), ("Rows", "n"), ("SHA-256", "mono"), ("Bytes", "n"), ("Source", "src")], cap_rows)}

{qhtml}

<h2>What changed between the two captures</h2>
<p>Only {sum(d.get('n_changes', 0) for d in avail.get('deltas', []))} player-level changes separate the
two reads. They are listed in full rather than summarised, because a summary is where a real change
gets lost.</p>
{table([("Team", "mono"), ("Player", ""), ("Change", "mono"), ("Before", ""), ("After", ""), ("Source", "src")], d_rows)}

<h2>What "Questionable" actually means</h2>
<p>Rather than quoting an old percentage, the designation is joined to observed participation across
every season present in both files. A player counts as having played when a snap-participation row
exists for his team-week. This is a <strong>participation</strong> join: it proves he was on the field,
not that he started.</p>
{table([("Designation", ""), ("n player-weeks", "n"), ("Observed play rate", "n"), ("95% Wilson CI", "n"), ("Seasons", "mono"), ("Source", "src")], rel_rows)}
<p class="sub2">Out and Doubtful are near-certain absences, which is the useful finding: a Doubtful
player essentially never plays. Questionable is close to a coin flip, which means it carries almost no
information on its own and must be combined with practice participation to be a signal.</p>

<h2>Per team: who is out</h2>
<p class="sub2">"Net unavailable" counts Out plus Doubtful. Questionable is listed separately because
it is not an absence.</p>
{table([("Team", "mono"), ("Listed", "n"), ("Out", "n"), ("Doubtful", "n"), ("Questionable", "n"), ("Net unavailable", "n"), ("Source", "src")], tv_rows)}

<div class="note warn"><strong>What this section cannot yet do.</strong> The brief asks for at least
daily capture of the official report, club depth pages and inactive evidence. This repository holds
{len(avail.get('captures', []))} capture dates and cannot self-schedule. The cadence is the gap, not the
format: a scheduled job that fetches, hashes and commits daily closes the scheduling requirements
(R18, R28, R45, R52, R61) at once.</div>
"""
    page("availability.html", "Availability", body)

    # ================================================================= DEPTH
    slots = depth.get("slots", [])
    rep = depth.get("replacement_depth", [])
    reg_rows = []
    for r in depth.get("official_register", []):
        reg_rows.append([
            (E(r["team"]), "mono"),
            (E(r.get("club_name") or ""), ""),
            (src(r.get("url")), "src"),
            (E(str(r.get("caption_on_page") or ""))[:160] + ("…" if len(str(r.get("caption_on_page") or "")) > 160 else ""), ""),
            (fmt(r.get("page_date_published")), ""),
            (f'<span class="badge {"ok" if r.get("status") == "verified" else "warn"}">{E(str(r.get("status")))}</span>', ""),
            (f'<span class="badge {"bad" if not r.get("official") else "ok"}">{"club (unofficial)" if not r.get("official") else "official"}</span>', ""),
        ])
    rep_rows = []
    for r in rep:
        rep_rows.append([
            (E(r["team"]), "mono"),
            (E(r["unit"]), ""),
            (E(r["position"]), "mono"),
            (", ".join(r["expected_starter_group"]), ""),
            (", ".join(r["unavailable_per_official_report"]), ""),
            (", ".join(r["replacement_named_by_club"]) or "—", ""),
            (fmt(r["replacement_depth_rank"]), "n"),
            (str(len(r["expected_starter_group"])), "n"),
            (src(r["club_source"]), "src"),
            (src(r["official_source"]), "src"),
        ])
    ss = depth.get("slot_states", {})
    body = f"""
<h1>Depth graph</h1>
<p class="lede">Who was expected to start, stored as a first-class dataset. The two halves of that
question are treated differently: the expected starter comes from a club page and is cited; the actual
starter is <strong>null</strong> on every row, because no official inactive list or snap count is held
for 2026 and inferring one would be a fabrication.</p>
<div class="kpis">
  {kpi(f'{depth.get("clubs_acquired", 0)}/32', "clubs acquired", "warn")}
  {kpi(f'{len(slots):,}', "depth slots", "info")}
  {kpi(ss.get("group", 0), "grouped slots (club named more than one at rank 1)", "warn")}
  {kpi(ss.get("empty", 0), "empty slots (published empty, kept as rows)", "mute")}
  {kpi(len(rep), "slots where the expected starter is Out or Doubtful", "bad")}
</div>

<h2>Why "column 1 is the starter" is wrong on this data</h2>
<div class="note bad"><strong>{ss.get("group", 0)} slots list more than one player at rank 1.</strong>
Clubs publish groups — three receivers, two cornerbacks — and choosing one of them as "the starter"
would be an invention the club never made. Every such slot is stored as a group. {ss.get("empty", 0)}
slots are published empty and are kept as rows rather than skipped, because "nobody listed" is
information, not a gap.</div>

<h2>The club register, with source and page date</h2>
<p class="sub2">There is no league-official depth chart: nfl.com returns 404 for the per-team path
<code>/teams/TEAM/depth-chart</code>. Every chart below is club-published and several are captioned
"unofficial" by the club itself. The page date is null where the club prints none — which is most of
them, and that absence is why a dated transaction log is required to flag staleness.</p>
{table([("Team", "mono"), ("Club", ""), ("Source", "src"), ("The club's own caption", ""), ("Page date", ""), ("Status", ""), ("Basis", "")], reg_rows)}

<h2>Replacement depth: not just that a replacement exists, but how deep</h2>
<p>For every slot where the club's rank-1 group is out or doubtful per the official report, this shows
the rank of the man who would step in and whether he is himself unavailable.</p>
{table([("Team", "mono"), ("Unit", ""), ("Pos", "mono"), ("Expected starter(s)", ""), ("Unavailable", ""),
        ("Next man up", ""), ("His depth rank", "n"), ("Group size", "n"), ("Club source", "src"), ("Official source", "src")], rep_rows)}

<h2>The feature this section deliberately does not build</h2>
<div class="note warn"><strong>Backup deficiency: not built.</strong>
{depth.get('feature_status', {}).get('why')}
<h3>What would unblock it</h3>
<ul>{''.join(f'<li>{E(x)}</li>' for x in depth.get('feature_status', {}).get('what_would_unblock_it', []))}</ul>
<strong>Shortcut refused:</strong> {depth.get('feature_status', {}).get('anti_pattern_refused', '')}</div>
"""
    page("depth.html", "Depth graph", body)

    # ================================================================ PRICES
    pol = price.get("policy", {})
    cov = price.get("coverage", {})
    p_rows = []
    for season in sorted(cov)[::-1][:14]:
        v = cov[season]
        p_rows.append([
            (E(season), "mono"),
            (str(v.get("side:open_and_close", 0)), "n"),
            (str(v.get("side:open_only", 0)), "n"),
            (str(v.get("side:close_only", 0)), "n"),
            (str(v.get("side:single_line_only", 0)), "n"),
            (str(v.get("total:open_and_close", 0)), "n"),
            (str(v.get("total:open_only", 0)), "n"),
            (str(v.get("total:single_line_only", 0)), "n"),
            (str(v.get("moneyline:close_only", 0)), "n"),
            (src("https://github.com/nflverse/nfldata/blob/master/data/games.csv"), "src"),
        ])
    inp_rows = []
    for i in price.get("inputs", []):
        inp_rows.append([
            (E(str(i.get("file"))), "mono"),
            (src(i.get("source")), "src"),
            (f'<code>{E(str(i.get("sha256", ""))[:24])}…</code>' if i.get("sha256") else "—", "mono"),
            (E(str(i.get("note", ""))), ""),
        ])
    body = f"""
<h1>Price store</h1>
<p class="lede">Opening and closing numbers for every market we originate, with the basis of each
number stated explicitly. The price-data policy was decided before any backtest was published, and it
is the reason this page is mostly about what does <em>not</em> exist.</p>

<h2>The policy, in four rules</h2>
<div class="note"><strong>1. Four line families, never merged.</strong>
<code>games.spread_line</code> is a single undated line — labelled
<code>unspecified_single_line</code> and excluded from any open-to-close computation.
<code>sc_lines.csv</code> is a two-sided spread whose date is unstated — a fallback, never an opening
price. <code>initial_lines.csv</code> is a genuine opening price and covers 2021 only.
<code>closing_lines.csv</code> is a genuine closing price.</div>
<div class="note bad"><strong>2. There is no opening moneyline. Anywhere.</strong> Not for 2021, not for
any season. Moneyline is close-only, and its opening column is null on every row. This is published as
a fact about the data rather than worked around by inference.</div>
<div class="note bad"><strong>3. Not one game has both an opening and a closing side price.</strong>
Every opening number is from 2021 and every closing number is from 2006–2018, so the two sets do not
overlap: 272 games are open-only, 3,237 are close-only, and 3,621 carry only a single undated line.
Measuring our line's movement from open to close is therefore impossible for <em>any</em> game in this
data, not merely for current ones. A daily price capture is the only fix.</div>
<div class="note"><strong>4. No price is ever inferred.</strong> A market without a dated opening price
stores null. A closing price is never used as a stand-in for an opening one.</div>

<h2>Coverage by season</h2>
<p class="sub2">Each row counts games in that season by the price evidence available. "Single line only"
means the game has one undated number and nothing else.</p>
{table(
        [("Season", "mono"), ("Side: open+close", "n"), ("Side: open only", "n"), ("Side: close only", "n"),
         ("Side: single line", "n"), ("Total: open+close", "n"), ("Total: open only", "n"),
         ("Total: single line", "n"), ("Moneyline: close only", "n"), ("Source", "src")],
        p_rows,
    )}

<h2>Inputs and their hashes</h2>
{table([("File", "mono"), ("Source", "src"), ("SHA-256", "mono"), ("Note", "")], inp_rows)}

<div class="note"><strong>How this was obtained, and why it matters.</strong> The nflverse release
assets are the canonical long-run location, but they are served from a host this sandbox cannot reach.
The same publisher's repository copies were used instead, via a repository tarball, and their hashes
are on this page. The repository's existing GitHub Action runs where egress is open and can re-derive
these from the release — which is the correct long-run fix.</div>
"""
    page("prices.html", "Price store", body)

    # ============================================================= QUESTIONS
    q_rows = []
    for q in req.get("questions", []):
        q_rows.append([
            (E(q["q"]), ""),
            (E(q["a"]), ""),
            (f'<span class="badge {"ok" if q["state"].startswith("answered") else "warn"}">{E(q["state"])}</span>', ""),
            (src(q["source"]), "src"),
        ])
    body = f"""
<h1>Questions this project had to answer before deciding anything</h1>
<p class="lede">Each question below was blocking a decision. Each answer is derived from a committed
file, and where the answer was "the data cannot say", that is the answer.</p>
{table([("Question", ""), ("Answer, with its number", ""), ("State", ""), ("Evidence", "src")], q_rows)}
<div class="note"><strong>The questions that are still open</strong> are the ones inside the blocked
requirements: what the reserve list contains, what each club's depth chart says beyond the five
acquired, what the official inactives were, and what the league's 2026 kickoff rule text says. None of
them is guessed at here.</div>
"""
    page("questions.html", "Questions", body)

    # =========================================================== SUGGESTIONS
    s_rows = []
    for s in req.get("suggestions", []):
        s_rows.append([
            (f'<code>{E(s["id"])}</code>', "mono"),
            (f'<strong>{E(s["title"])}</strong>', ""),
            (E(s["why"]), ""),
            ("<br>".join(f'· {E(o)}' for o in s["options"]), ""),
            (E(s["recommendation"]), ""),
            (f'<span class="badge mute">{E(s["decision"])}</span>', ""),
            (src("data/linelab/requirements.json"), "src"),
        ])
    body = f"""
<h1>Suggestions, for review before anything is built</h1>
<p class="lede">These are proposals, not changes. Each names the problem, the options, and a
recommendation, so a reviewer can pick a path before work starts rather than after. Nothing on this
page has been implemented.</p>
{table([("ID", "mono"), ("Proposal", ""), ("Why it matters", ""), ("Options", ""), ("Recommendation", ""), ("Decision", ""), ("Source", "src")], s_rows)}
<div class="note"><strong>How to use this page.</strong> Mark a decision beside each proposal. The
recommended path is the one the evidence on this site supports; the alternatives are listed because
several of them are cheaper and one of them is free.</div>
"""
    page("suggestions.html", "Suggestions", body)

    # ================================================================ FLAGGED
    fl = []
    for f in avail.get("capture_quality_findings", []):
        fl.append({
            "id": "F" + str(len(fl) + 1).zfill(2),
            "what": f"Capture defect: {f['type']} in {f['capture_id']} — {', '.join(f['teams'])} "
                    f"({f['rows_affected']} rows with no designation at all)",
            "why": f["why_it_matters"],
            "state": f["status"],
            "resolve": f["how_to_resolve"],
            "source": "https://www.nfl.com/injuries/league/2026/reg10",
        })
    fl += [
        {"id": f"F{len(fl)+1:02d}", "what": "No opening moneyline exists for any game, any season",
         "why": "The moneyline market cannot be evaluated open-to-close, only at the close.",
         "state": "needs review", "resolve": "Capture a dated moneyline before kickoff for the games being tracked.",
         "source": "https://github.com/nflverse/nfldata/blob/master/data/closing_lines.csv"},
        {"id": f"F{len(fl)+2:02d}", "what": "No game has both an opening and a closing side price: openings are 2021-only, closes are 2006-2018-only",
         "why": "Line movement cannot be measured for ANY game from committed data, not just current ones.",
         "state": "needs review", "resolve": "A daily price capture from open to close.",
         "source": "https://github.com/nflverse/nfldata/blob/master/data/initial_lines.csv"},
        {"id": f"F{len(fl)+3:02d}", "what": "No league-official depth chart exists; nfl.com returns 404",
         "why": "Every depth claim rests on a club page the club itself may caption unofficial.",
         "state": "permanent limitation",
         "resolve": "Cite the club page on every row, as done here; license a structured feed if a full 32-club matrix is required.",
         "source": "https://www.nfl.com/teams/new-england-patriots/depth-chart"},
        {"id": f"F{len(fl)+4:02d}", "what": f"Only {depth.get('clubs_acquired', 0)} of 32 club depth charts are held",
         "why": "The matchup-deficiency matrix and the backup-deficiency feature cannot be built.",
         "state": "needs review", "resolve": "Acquire or license the remaining 27.",
         "source": "https://www.detroitlions.com/team/depth-chart"},
        {"id": f"F{len(fl)+5:02d}", "what": "No official inactive list or 2026 snap count is held",
         "why": "'Actually started' is null on every depth row; a replacement is suspected, never confirmed.",
         "state": "needs review", "resolve": "Capture the official inactive list weekly and a participation feed.",
         "source": "https://www.nfl.com/news/"},
        {"id": f"F{len(fl)+6:02d}", "what": "The margin/total correlation is near zero, contradicting the usual justification for banning side+total parlays",
         "why": "A rule this project inherited was not supported by its own data. Corrected on the models page.",
         "state": "resolved — corrected", "resolve": "The parlay ban now rests on same-team dependence, which is not yet measured.",
         "source": "engine/linelab/scoring.py"},
        {"id": f"F{len(fl)+7:02d}", "what": "The opponent-adjusted model does not beat the unadjusted control",
         "why": "Any claim that adjustment adds value would be false on this data.",
         "state": "resolved — reported", "resolve": "Publish both with a gap column; do not collapse to the adjusted model.",
         "source": "data/linelab/scores.json"},
        {"id": f"F{len(fl)+8:02d}", "what": "nflverse release assets are unreachable from the build sandbox",
         "why": "Data had to be taken from the publisher's repository rather than its release assets; hashes are published so the bytes can be confirmed.",
         "state": "needs review", "resolve": "Keep the GitHub Action that runs where egress is open.",
         "source": "https://github.com/nflverse/nfldata"},
        {"id": f"F{len(fl)+9:02d}", "what": "Two prior sessions recorded the opposite environment fact and left 43 unhashed data files",
         "why": "signal/data/*.csv were produced by a workflow whose raw inputs were never committed, so they cannot be re-derived in this repository. They are used here read-only and labelled as such.",
         "state": "needs review", "resolve": "Re-run the fetch workflow and commit its manifest, or stop citing those files.",
         "source": "signal/data/manifest.json"},
    ]
    f_rows = []
    for f in fl:
        f_rows.append([
            (f'<code>{E(f["id"])}</code>', "mono"),
            (E(f["what"]), ""),
            (E(f["why"]), ""),
            (f'<span class="badge {"warn" if "needs review" in f["state"] else ("ok" if "resolved" in f["state"] else "info")}">{E(f["state"])}</span>', ""),
            (E(f["resolve"]), ""),
            (src(f["source"]), "src"),
        ])
    body = f"""
<h1>Flagged for review</h1>
<p class="lede">Everything a reader should not take on trust, with the source that shows the problem
and what would resolve it. None of these blocks the site; all of them should be read before any number
here is used in a decision.</p>
<div class="note bad"><strong>Two of these are corrections of this project's own earlier claims</strong>
— a correlation that was assumed and turned out to be near zero, and a model that was expected to beat
its control and did not. They are listed here rather than quietly fixed, because a project that only
flags other people's errors is not being honest.</div>
{table([("ID", "mono"), ("What", ""), ("Why it matters", ""), ("State", ""), ("What would resolve it", ""), ("Source", "src")], f_rows)}
"""
    page("flagged.html", "Flagged", body)

    # ================================================================ SOURCES
    all_src = [
        ("https://www.nfl.com/injuries/", "T1 official league", "The official injury report; the page every availability capture is read from."),
        ("https://www.nfl.com/injuries/league/2026/reg10", "T1 official league", "The Week 10 2026 injury report, read in full (8 of 8 chunks) on 2026-11-16."),
        ("https://www.nfl.com/schedules/2026/reg10", "T1 official league", "Official Week 10 schedule and final scores, used to reconcile the corpus."),
        ("https://www.nfl.com/teams/new-england-patriots/depth-chart", "T1 official league", "Returns 404 — the evidence that no league-official depth chart exists."),
        ("https://github.com/nflverse/nfldata", "T2 open data", "Publisher of games.csv, closing_lines.csv, initial_lines.csv and sc_lines.csv: results and market numbers."),
        ("https://github.com/nflverse/nfldata/blob/master/data/games.csv", "T2 open data", "Results and the single undated spread/total/moneyline per game."),
        ("https://github.com/nflverse/nfldata/blob/master/data/closing_lines.csv", "T2 open data", "Closing prices with per-side odds, 2006–2018 games present."),
        ("https://github.com/nflverse/nfldata/blob/master/data/initial_lines.csv", "T2 open data", "The only genuine opening prices in the data: 2021 spread and total."),
        ("https://github.com/nflverse/nflverse-data/releases/tag/injuries", "T2 open data", "Multi-season weekly designations used for the designation-reliability join."),
        ("https://github.com/nflverse/nflverse-data/releases/tag/snap_counts", "T2 open data", "Participation used to measure the play rate per designation."),
        ("https://www.detroitlions.com/team/depth-chart", "T2 club", "Lions depth chart (club-published)."),
        ("https://www.patriots.com/team/depth-chart", "T2 club", "Patriots depth chart (club-published)."),
        ("https://www.packers.com/team/depth-chart", "T2 club", "Packers depth chart (club-published)."),
        ("https://www.chiefs.com/team/depth-chart", "T2 club", "Chiefs depth chart (club-published)."),
        ("https://www.49ers.com/team/depth-chart", "T2 club", "49ers depth chart (club-published)."),
    ]
    s_rows = []
    for u, tier, use in all_src:
        s_rows.append([(src(u), "src"), (E(tier), ""), (E(use), "")])
    body = f"""
<h1>Sources</h1>
<p class="lede">Every source used, what it provided, and how it is tiered. A T1 source is the league
or the official statistical registry; T2 is the publisher's open data or the club itself. No
commercial odds aggregator is used to fill a value anywhere on this site.</p>
{table([("Source", "src"), ("Tier", ""), ("What it provided", "")], s_rows)}
<h2>How to check any number here</h2>
<ol>
<li>Open the artefact named on the <a href="requirements.html">decision-readiness</a> row.</li>
<li>Re-run the builder that produced it. Every builder is deterministic and re-runnable:
<code>price_store.py</code>, <code>model.py</code>, <code>scoring.py</code>, <code>availability.py</code>,
<code>depth_graph.py</code>, <code>backtest.py</code>, <code>requirements.py</code>.</li>
<li>Compare the SHA-256 of any input against the value on <a href="prices.html">Price store</a> or
<a href="availability.html">Availability</a>.</li>
</ol>
<div class="note warn"><strong>What is reused read-only and cannot be re-derived here.</strong> The
43 files in <code>signal/data/</code> were produced by a workflow whose raw inputs were never committed.
This site uses three of them for the designation-reliability join and labels them as such. They are
listed on <a href="flagged.html">Flagged</a>.</div>
"""
    page("sources.html", "Sources", body)

    print("site built ->", SITE)


if __name__ == "__main__":
    build()
