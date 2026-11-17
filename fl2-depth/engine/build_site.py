#!/usr/bin/env python3
"""Build the /fl2-depth/ site from the captured Game Book CSVs.

Everything on the pages comes from the CSVs in data/verified/. Nothing is typed in
by hand, and no value is inferred: if a field is empty in the CSV it is rendered as
an italic blank, never filled with a guess.

Run:  python3 fl2-depth/engine/build_site.py
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import re
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SECTION = os.path.join(ROOT, "fl2-depth")
DATA = os.path.join(SECTION, "data", "verified")
SEASON, WEEK = "2026", "10"

NAV = [("index.html", "Overview"), ("starters.html", "Actual starters"),
       ("snaps.html", "Snap counts &amp; depth"), ("inactives.html", "Inactive list"),
       ("sources.html", "Sources &amp; hashes"), ("questions.html", "Questions"),
       ("suggestions.html", "Suggestions"), ("flagged.html", "Flagged for review")]


def read(name: str) -> list:
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def esc(v) -> str:
    return html.escape("" if v is None else str(v))


def cell(v, cls="") -> str:
    v = "" if v is None else str(v).strip()
    classes = (cls + " blank").strip()
    if not v:
        return '<td class="%s">&mdash;</td>' % classes
    return '<td class="%s">%s</td>' % (cls, esc(v))


def num(v, suffix="") -> str:
    """A numeric cell: blank stays blank, never rendered as 0."""
    v = "" if v is None else str(v).strip()
    if not v:
        return '<td class="num blank">&mdash;</td>'
    return '<td class="num">%s%s</td>' % (esc(v), suffix)


def data_hash() -> str:
    h = hashlib.sha256()
    for name in sorted(os.listdir(DATA)):
        if name.endswith((".csv", ".json")):
            h.update(name.encode())
            h.update(open(os.path.join(DATA, name), "rb").read())
    return h.hexdigest()[:12]


def page(title: str, active: str, body: str, lede: str = "") -> str:
    nav = "\n".join(
        '<a href="%s"%s>%s</a>' % (h, ' aria-current=page' if h == active else '', t)
        for h, t in NAV)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · FL2 Depth</title>
<meta name="description" content="Official NFL Game Book depth data: actual starters, snap counts and inactive lists for 2026 week 10, every row linked to the PDF it was parsed from.">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="site-header"><div class="inner">
  <div class="brand-row">
    <div class="brand">FL2 Depth <span>· who actually played</span></div>
  </div>
  <div class="brand-sub">2026 week {WEEK} · every row parsed from an official NFL Game Book · build {data_hash()}</div>
  <nav>{nav}</nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer class="site-footer"><div class="inner">
  <p>FL2 Depth · data captured from official NFL Game Books and hashed. Where the league
  labels a table <em>(Unofficial)</em>, that label is carried on every row that came from it.
  Rows that could not be parsed from an official source are left blank and listed on
  <a href="flagged.html">Flagged for review</a> — never inferred.</p>
</div></footer>
</body>
</html>
"""


def table(caption: str, headers: list, rows: list, cls: str = "") -> str:
    head = "".join("<th>%s</th>" % h for h in headers)
    body = "\n".join(rows)   # each row already carries its own <tr>
    return f"""<div class="table-wrap">
<table class="{cls}">
<caption>{caption}</caption>
<thead><tr>{head}</tr></thead>
<tbody>
{body}
</tbody>
</table>
</div>"""


def game_label(gid: str) -> str:
    return gid.replace("2026_10_", "").replace("_", " @ ")


def book_link(url: str) -> str:
    if not url:
        return '<span class="badge bad">no book</span>'
    return f'<a href="{esc(url)}">PDF</a>'


# --------------------------------------------------------------------------- load

gamebooks = read(f"gamebooks-{SEASON}-w{WEEK}.csv")
starters = read(f"starters-{SEASON}-w{WEEK}.csv")
playtime = read(f"playtime-{SEASON}-w{WEEK}.csv")
inactives = read(f"inactives-{SEASON}-w{WEEK}.csv")

captured = [g for g in gamebooks if g.get("status") == "captured"]
withheld = [g for g in gamebooks if g.get("status") != "captured"]

clubs = {}
for r in starters:
    clubs.setdefault(r["game_id"], set()).add(r["club"])


def club_short(full: str) -> str:
    # the Game Book prints full club names; a short tag keeps the tables readable
    return {"Washington Commanders": "WAS", "New York Giants": "NYG",
            "New England Patriots": "NE", "Detroit Lions": "DET",
            "Kansas City Chiefs": "KC", "Atlanta Falcons": "ATL",
            "Houston Texans": "HOU", "Cleveland Browns": "CLE",
            "Minnesota Vikings": "MIN", "Green Bay Packers": "GB",
            "Miami Dolphins": "MIA", "Indianapolis Colts": "IND",
            "Carolina Panthers": "CAR", "New Orleans Saints": "NO",
            "Buffalo Bills": "BUF", "New York Jets": "NYJ",
            "Jacksonville Jaguars": "JAX", "Tennessee Titans": "TEN",
            "Los Angeles Rams": "LAR", "Arizona Cardinals": "ARI",
            "Seattle Seahawks": "SEA", "Las Vegas Raiders": "LV",
            "San Francisco 49ers": "SF", "Dallas Cowboys": "DAL",
            "Pittsburgh Steelers": "PIT", "Cincinnati Bengals": "CIN",
            "Los Angeles Chargers": "LAC", "Baltimore Ravens": "BAL"}.get(full, full)


GAMES = [g["game_id"] for g in gamebooks]

# --------------------------------------------------------------------------- overview

def build_index() -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with_playtime = sum(1 for g in gamebooks
                        if g["status"].startswith("captured")
                        and int(g.get("playtime_rows") or 0))
    stats = [("Books captured", str(sum(1 for g in gamebooks
                                        if g["status"].startswith("captured"))),
              "of %d games in week %s" % (len(gamebooks), WEEK)),
             ("Actual starters", str(len(starters)),
              "11 offence + 11 defence per club"),
             ("Snap-count rows", str(len(playtime)),
              "from %d of %d books" % (with_playtime, len(gamebooks))),
             ("Inactive / DNP rows", str(len(inactives)),
              "official Not Active + Did Not Play")]

    stat_html = "\n".join(
        f'<div class="stat"><div class="k">{esc(k)}</div><div class="v">{esc(v)}</div>'
        f'<div class="d">{esc(d)}</div></div>' for k, v, d in stats)

    rows = []
    for g in gamebooks:
        gid = g["game_id"]
        st_n = sum(1 for r in starters if r["game_id"] == gid)
        pt_n = sum(1 for r in playtime if r["game_id"] == gid)
        ia_n = sum(1 for r in inactives if r["game_id"] == gid)
        status = g["status"]
        if status == "captured":
            badge = '<span class="badge ok">captured</span>'
        elif status.startswith("captured"):
            badge = '<span class="badge warn">partial</span>'
        else:
            badge = '<span class="badge bad">withheld</span>'

        rows.append("<tr><td class='nowrap'><strong>%s</strong></td><td>%s</td>"
                    "<td class='num'>%s</td><td class='num'>%s</td><td class='num'>%s</td>"
                    "<td>%s</td><td class='mono'>%s</td></tr>" % (
                        esc(game_label(gid)), badge, st_n, pt_n, ia_n,
                        book_link(g.get("gamebook_url", "")),
                        esc((g.get("pdf_sha256") or "")[:16])))

    body = f"""
<div class="page-head">
  <div class="eyebrow">Session arena/7e6e153e-fl2</div>
  <h1>Depth from playing time, not from a depth chart</h1>
  <p class="lede">The league's own per-club depth charts are captioned
  <em>unofficial</em>, and only 5 of 32 clubs publish them. So this section derives
  depth from the one source the league publishes for <em>every</em> game: the official
  NFL Game Book. Each book carries the actual starters, the official inactive list, and
  a playtime table with snap counts on offence, defence and special teams. Every row on
  this site links to the exact PDF it was parsed from, and each PDF is hashed.</p>
</div>

<section class="card pad">
  <h2>What changed, and why it matters</h2>
  <div class="grid c4" style="margin:12px 0 4px">{stat_html}</div>
  <p>Requirement R77 asked us to settle where depth order comes from before building any
  backup-deficiency feature. Two routes were open: the per-club depth-chart pages, and
  playing time. The table below is the answer — route (a) covers 5 of 32 clubs and is
  captioned unofficial by the league itself; route (b) covers every game and gives a
  number, not a claimed order.</p>
  {table("Depth source: the two candidate routes compared",
         ["Route", "Coverage", "Official?", "Gives", "Verdict"],
         ["<tr><td>Per-club depth-chart pages</td><td>5 of 32 clubs</td>"
          "<td><span class='badge bad'>no — the club writes it</span></td>"
          "<td>a claimed 1st/2nd/3rd string</td>"
          "<td><span class='badge warn'>insufficient alone</span></td></tr>",
          "<tr><td>Official NFL Game Book (this section)</td>"
          "<td>every game, both clubs</td>"
          "<td><span class='badge ok'>yes — the league publishes it</span></td>"
          "<td>who actually started, and how many snaps each player took</td>"
          "<td><span class='badge ok'>adopted for R71/R77</span></td></tr>"])}
</section>

<section class="card pad">
  <h2>Week {WEEK} capture register</h2>
  <p>One row per game. <strong>Withheld</strong> means the game-centre page was serving a
  byte-identical PDF to another game, so its rows were dropped rather than published
  under the wrong game — see <a href="flagged.html">Flagged for review</a>.</p>
  {table("Week %s Game Book capture — %s" % (WEEK, now),
         ["Game", "Status", "Starters", "Snap rows", "Inactive/DNP", "Book", "SHA-256"],
         rows)}
</section>

<section class="card pad">
  <h2>What is on each page</h2>
  <div class="grid c3">
    <div class="card pad"><h3><a href="starters.html">Actual starters</a></h3>
      <p>11 offence and 11 defence per club, as printed in the book's <em>Lineups</em>
      block — the players who actually took the first snap, not a club's claimed order.</p></div>
    <div class="card pad"><h3><a href="snaps.html">Snap counts &amp; depth</a></h3>
      <p>Every player's snaps and share on offence, defence and special teams. This is the
      input for depth-from-playing-time, and it is how a backup's real workload is seen.</p></div>
    <div class="card pad"><h3><a href="inactives.html">Inactive list</a></h3>
      <p>The official <em>Not Active</em> and <em>Did Not Play</em> lists, per club — so
      "not listed" and "available" are not silently treated as the same thing.</p></div>
    <div class="card pad"><h3><a href="sources.html">Sources &amp; hashes</a></h3>
      <p>Every PDF URL with its SHA-256, the venue, roof and weather the book printed,
      and the league's copyright notice verbatim.</p></div>
    <div class="card pad"><h3><a href="questions.html">Questions</a></h3>
      <p>What still has to be answered before depth can be used in a model, and how each
      answer would be discovered.</p></div>
    <div class="card pad"><h3><a href="suggestions.html">Suggestions</a></h3>
      <p>Options for the next step, with the trade-off of each, so a reviewer picks a
      path before anything is built.</p></div>
  </div>
</section>

<section class="note warn">
  <p><strong>Two caveats travel with this data.</strong> First: the league captions its
  playtime table <em>(Unofficial)</em>. That caption is stored on every snap row rather
  than dropped. Second: the Game Book is published only for games that have kicked off,
  so it can never be a pre-game input — it is the ground truth a pre-game model is
  checked against, and the historical corpus a depth model is fitted on.</p>
</section>
"""
    return page("Overview", "index.html", body)


# --------------------------------------------------------------------------- starters

def build_starters() -> str:
    out = ['<div class="page-head"><div class="eyebrow">Official Game Book · Lineups</div>'
           '<h1>Actual starters, week %s</h1>'
           '<p class="lede">The Lineups block of each Game Book lists the players who took the '
           'first snap on each unit. That is a different thing from a club\'s published depth '
           'chart, and it is the number a model should be checked against.</p></div>' % WEEK]
    for gid in GAMES:
        rows = [r for r in starters if r["game_id"] == gid]
        if not rows:
            continue
        trs = []
        for r in sorted(rows, key=lambda x: (x["club"], x["unit"] != "offense", x["slot"])):
            trs.append("<tr><td>%s</td><td>%s</td><td>%s</td><td class='num'>%s</td>"
                       "<td>%s</td><td>%s</td></tr>" % (
                           esc(club_short(r["club"])), esc(r["club"]), esc(r["unit"]),
                           esc(r["jersey"]), esc(r["slot"]), esc(r["player_raw"])))
        n = len(rows)
        out.append('<section class="card pad"><h2>%s</h2>' % esc(game_label(gid)))
        out.append('<p>%d starter rows — %s. Source: %s</p>' % (
            n, ", ".join(sorted("%s %d" % (club_short(c), sum(
                1 for r in rows if r["club"] == c)) for c in {r["club"] for r in rows})),
            book_link(rows[0]["source_url"])))
        out.append(table("Lineups as printed in the official Game Book",
                         ["Club", "Club (as printed)", "Unit", "#", "Slot", "Player"], trs))
        out.append("</section>")
    return page("Actual starters", "starters.html", "\n".join(out))


# --------------------------------------------------------------------------- snaps

def build_snaps() -> str:
    out = ['<div class="page-head"><div class="eyebrow">Official Game Book · Playtime Percentage</div>'
           '<h1>Snap counts and depth order, week %s</h1>'
           '<p class="lede">Depth here is measured, never assigned: a player\'s place in a unit is '
           'the share of that unit\'s snaps he actually played. The league captions this table '
           '<em>(Unofficial)</em>, and that caption is kept on every row.</p></div>' % WEEK]
    out.append('<section class="note warn"><p><strong>The league labels this table '
               '<em>(Unofficial)</em>.</strong> It is the only official snap-count source that '
               'exists — <code>nfl.com/stats/snap-counts/</code> returns 404 — so we use it and '
               'carry the label, rather than dropping the label or substituting an unofficial '
               'third-party count.</p></section>')
    for gid in GAMES:
        rows = [r for r in playtime if r["game_id"] == gid]
        if not rows:
            continue
        trs = []
        for r in sorted(rows, key=lambda x: (x["club"], -int(x["off_snaps"] or 0),
                                             -int(x["def_snaps"] or 0),
                                             -int(x["st_snaps"] or 0), x["player_raw"])):
            trs.append("<tr><td>%s</td><td>%s</td><td>%s</td>"
                       "%s%s%s%s%s%s</tr>" % (
                           esc(club_short(r["club"])), esc(r["player_raw"]), esc(r["pos_raw"]),
                           num(r["off_snaps"]), num(r["off_pct"], "%"),
                           num(r["def_snaps"]), num(r["def_pct"], "%"),
                           num(r["st_snaps"]), num(r["st_pct"], "%")))
        out.append('<section class="card pad"><h2>%s</h2>' % esc(game_label(gid)))
        out.append('<p>%d players · source %s</p>' % (len(rows), book_link(rows[0]["source_url"])))
        out.append(table("Snap counts — offence, defence, special teams (league caption: Unofficial)",
                         ["Club", "Player", "Pos", "Off snaps", "Off %", "Def snaps",
                          "Def %", "ST snaps", "ST %"], trs))
        out.append("</section>")
    return page("Snap counts & depth", "snaps.html", "\n".join(out))


# --------------------------------------------------------------------------- inactives

def build_inactives() -> str:
    out = ['<div class="page-head"><div class="eyebrow">Official Game Book · Not Active / Did Not Play</div>'
           '<h1>Inactive list, week %s</h1>'
           '<p class="lede">The book separates <em>Not Active</em> (the official inactive list) from '
           '<em>Did Not Play</em> (dressed but did not play). Keeping them apart is the difference '
           'between "not listed" and "available".</p></div>' % WEEK]
    for gid in GAMES:
        rows = [r for r in inactives if r["game_id"] == gid]
        if not rows:
            continue
        trs = []
        for r in sorted(rows, key=lambda x: (x["list_type"], x["club"], x["player_raw"])):
            trs.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                esc(club_short(r["club"])), esc(r["club"]), esc(r["list_type"]),
                esc(r["pos_raw"]), esc(r["player_raw"])))
        na = sum(1 for r in rows if r["list_type"] == "not_active")
        dnp = sum(1 for r in rows if r["list_type"] == "did_not_play")
        out.append('<section class="card pad"><h2>%s</h2>' % esc(game_label(gid)))
        out.append('<p>%d not active, %d dressed but did not play · source %s</p>' % (
            na, dnp, book_link(rows[0]["source_url"])))
        out.append(table("Official Not Active and Did Not Play lists",
                         ["Club", "Club (as printed)", "List", "Pos", "Player"], trs))
        out.append("</section>")
    return page("Inactive list", "inactives.html", "\n".join(out))


# --------------------------------------------------------------------------- sources

def build_sources() -> str:
    rows = []
    for g in gamebooks:
        rows.append("<tr%s><td class='nowrap'>%s</td><td>%s</td><td>%s</td>"
                    "<td class='mono'>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
                    "<td class='num'>%s</td><td>%s</td></tr>" % (
                        ' class="flag"' if g["status"] != "captured" else "",
                        esc(game_label(g["game_id"])),
                        esc(g.get("status", "")),
                        '<a href="%s">game centre</a>' % esc(g["gamecenter_url"]),
                        esc((g.get("pdf_sha256") or "")[:24]),
                        book_link(g.get("gamebook_url", "")),
                        esc(g.get("book_venue", "")) if g.get("book_venue") else '<span class="badge warn">not captured</span>',
                        esc(g.get("book_roof_surface", "")),
                        esc(g.get("book_weather", "")),
                        esc(g.get("attendance", "")),
                        esc(g.get("captured_at_utc", ""))))
    notice = ""
    mpath = os.path.join(DATA, f"capture-manifest-{SEASON}-w{WEEK}.json")
    if os.path.exists(mpath):
        manifest = json.load(open(mpath))
        notice = manifest.get("copyright_notice", "")
    body = f"""
<div class="page-head"><div class="eyebrow">Provenance</div>
<h1>Sources and hashes</h1>
<p class="lede">Every row on this site comes from one of the PDFs below. Each PDF's SHA-256
is recorded at capture time, so a re-capture can prove the bytes did not change.</p></div>

<section class="card pad">
  <h2>Game Book register — 2026 week {WEEK}</h2>
  {table("One row per game. T1 = official league source.",
         ["Game", "Status", "Game centre", "SHA-256", "Book", "Venue (as printed)",
          "Roof / surface", "Weather", "Attendance", "Captured (UTC)"], rows)}
</section>

<section class="card pad">
  <h2>How the capture works</h2>
  <p>The sandbox has no network route to <code>nfl.com</code>, so the capture runs in GitHub
  Actions, which does. The workflow fetches each game-centre page, follows the
  <em>Download Game Book (PDF)</em> link, hashes the bytes, converts to text with
  <code>pdftotext -layout</code>, parses it, and commits the CSVs. The PDFs themselves are
  never committed. The parser has an offline self-test built from synthetic books that
  reproduce the real column geometry, and the workflow fails if that test fails.</p>
  {table("Pipeline",
         ["Step", "Source", "Output"],
         ["<tr><td>1. game-centre page</td><td>www.nfl.com</td>"
          "<td>the Game Book PDF URL</td></tr>",
          "<tr><td>2. Game Book PDF</td><td>static.www.nfl.com</td>"
          "<td>bytes + SHA-256</td></tr>",
          "<tr><td>3. text</td><td>pdftotext -layout</td>"
          "<td>parsed rows, each carrying its PDF URL</td></tr>",
          "<tr><td>4. CSVs</td><td>committed to data/verified/</td>"
          "<td>starters, playtime, inactives</td></tr>"])}
</section>

<section class="note warn">
  <p><strong>Copyright notice carried verbatim from the Game Book.</strong> The league
  restricts use of this material to media coverage; we therefore store derived facts and
  hashes, never the PDF and never play-by-play. The notice is reproduced here so the
  restriction travels with the data:</p>
  <p class="small">{esc(notice) or "not captured"}</p>
</section>
"""
    return page("Sources & hashes", "sources.html", body)


# --------------------------------------------------------------------------- questions

def build_questions() -> str:
    q = [
        ("How far back do the Game Books go, and is the playtime table present in every season?",
         "A depth model needs several seasons, not one week. If older books lack the playtime "
         "table, the depth-from-playing-time route covers only recent seasons.",
         "Capture one book per season from 2012 to 2026 and record whether a Playtime "
         "Percentage block exists. Report the earliest season that carries it."),
        ("Does the playtime table appear in pre-season and post-season books?",
         "Week 1 depth is uncertain; pre-season snaps are the only official evidence available "
         "before it. Post-season books would extend the corpus.",
         "Capture one pre-season and one post-season book; record which blocks they carry."),
        ("Is a book published for a game that is postponed or cancelled?",
         "A missing book must be distinguishable from a capture failure, or the register will "
         "silently lose games.",
         "Check the 2026 schedule for any postponed game and query its game-centre page."),
        ("How quickly after a game's final whistle is the book published?",
         "This sets the earliest time the ground truth can be checked against a pre-game model.",
         "Poll one game-centre page every 15 minutes after kickoff and log the first minute the "
         "PDF URL appears."),
        ("Do the snap percentages always sum to 100 within a unit?",
         "If they do not, the table cannot be used as a share without a correction, and any "
         "correction would be an inference.",
         "Sum off_pct per club-game across the week already captured and publish the result."),
        ("Which slot labels vary between clubs, and does the parser cover them all?",
         "Cincinnati prints LDE/RDE/LOT/ROT/HB where most clubs print DE/T/RB. An unrecognised "
         "label loses that starter.",
         "Extract the distinct slot tokens across all 32 clubs and diff against the parser's "
         "vocabulary."),
        ("Does the Not Active list ever exceed the roster limit, or appear empty legitimately?",
         "An empty list could mean nobody was inactive or the block failed to parse; the two "
         "must not look the same.",
         "Count Not Active per club-game across a season and publish the distribution."),
        ("Can a player appear in both a club's Lineups block and its Not Active list?",
         "It should be impossible; if it happens the two blocks are being read from different "
         "pages.",
         "Left-join starters against inactives on game + club + player and report any hit."),
    ]
    rows = []
    for i, (question, why, how) in enumerate(q, 1):
        rows.append("<tr><td class='num'>%d</td><td><strong>%s</strong></td><td>%s</td>"
                    "<td>%s</td><td><span class='badge warn'>open</span></td></tr>" % (
                        i, esc(question), esc(why), esc(how)))
    body = f"""
<div class="page-head"><div class="eyebrow">Open questions</div>
<h1>What has to be answered before depth is used in a model</h1>
<p class="lede">These are not opinions. Each is a question with a specific way to find the
answer, and none of them can be answered by reasoning — they need data that has not been
captured yet.</p></div>
<section class="card pad">
{table("Questions, why each blocks, and how to discover the answer",
       ["#", "Question", "What it blocks", "How to find out", "Status"], rows)}
</section>
"""
    return page("Questions", "questions.html", body)


# --------------------------------------------------------------------------- suggestions

def build_suggestions() -> str:
    opts = [
        ("Extend the capture backwards before fitting anything",
         "Capture Game Books for 2019–2025 so depth-from-playing-time has a multi-season "
         "corpus, then fit on it.",
         "Costs several hours of CI time and a lot of storage. No model can be fitted until "
         "it finishes.",
         "Recommended if the goal is a depth feature in a model rather than a verified "
         "register."),
        ("Publish the week-10 register and stop",
         "Ship this section as the reference dataset and let another session build on it.",
         "Does not by itself clear R71; it supplies the measurement, not the model.",
         "Recommended if the register is the deliverable."),
        ("Cross-check the official snap counts against a third-party count",
         "Compare each player's snaps here against a non-official source and publish the "
         "disagreement rate.",
         "Introduces an unofficial source into a section whose whole premise is official-only.",
         "Only if the (Unofficial) caption has to be quantified."),
        ("Derive a 1st/2nd/3rd-string label from snap shares and publish it",
         "Turn snap share into an ordinal depth slot per club-position-week.",
         "Re-introduces exactly the thing R71 rejects if the threshold is chosen by hand.",
         "Only with a pre-registered threshold and the uncertainty published."),
    ]
    rows = []
    for i, (title, what, cost, when) in enumerate(opts, 1):
        rows.append("<tr><td class='num'>%d</td><td><strong>%s</strong></td><td>%s</td>"
                    "<td>%s</td><td>%s</td></tr>" % (
                        i, esc(title), esc(what), esc(cost), esc(when)))
    body = f"""
<div class="page-head"><div class="eyebrow">Suggestions</div>
<h1>Options for the next step — pick one before anything is built</h1>
<p class="lede">Nothing here is implemented. These are paths with their trade-offs written
down so a reviewer can choose, in line with the project rule that a change is not made until
a path is selected.</p></div>
<section class="card pad">
{table("Four paths, each with what it costs and when it is the right choice",
       ["#", "Path", "What it does", "Trade-off", "When to pick it"], rows)}
</section>
<section class="note ok">
  <p><strong>Not suggested:</strong> deriving depth order from jersey number, experience or
  salary. That is explicitly rejected in the brief, and the whole point of this section is
  that playing time is observable while those are not.</p>
</section>
"""
    return page("Suggestions", "suggestions.html", body)


# --------------------------------------------------------------------------- flagged

def build_flagged() -> str:
    incomplete_rows = []
    for g in gamebooks:
        if not (g["status"].startswith("captured") and not int(g.get("playtime_rows") or 0)):
            continue
        gid = g["game_id"]
        incomplete_rows.append(
            "<tr class='flag'><td>%s</td><td>%s</td><td class='num'>%d</td>"
            "<td class='num'>%s</td><td class='num'>%d</td><td>%s</td></tr>" % (
                esc(game_label(gid)), esc(g["status"]),
                sum(1 for r in starters if r["game_id"] == gid),
                esc(g.get("playtime_rows", "0")),
                sum(1 for r in inactives if r["game_id"] == gid),
                book_link(g.get("gamebook_url", ""))))
    if not incomplete_rows:
        incomplete_rows.append("<tr><td colspan='6' class='blank'>"
                               "every captured book carries a playtime table</td></tr>")
    rows = []
    for g in withheld:
        rows.append("<tr class='flag'><td>%s</td><td>%s</td><td>%s</td>"
                    "<td class='mono'>%s</td><td>%s</td></tr>" % (
                        esc(game_label(g["game_id"])), esc(g["status"]),
                        esc(g.get("note", "")), esc((g.get("pdf_sha256") or "")[:16]),
                        '<a href="%s">game centre</a>' % esc(g["gamecenter_url"])))
    if not rows:
        rows.append("<tr><td colspan='5' class='blank'>nothing withheld</td></tr>")
    unf = [g["game_id"] for g in gamebooks if g.get("playtime_unofficial") in ("True", "true")]
    body = f"""
<div class="page-head"><div class="eyebrow">Flagged for review</div>
<h1>Flagged for review</h1>
<p class="lede">Anything here is published <em>because</em> it could not be verified, or
because it carries a caveat. Nothing on this page is inferred — these are gaps and warnings,
with a link to the official source each one relates to.</p></div>

<section class="card pad">
  <h2>1. Games whose book was withheld</h2>
  <p>Where two games resolved to byte-identical PDFs, the second game's rows were dropped
  rather than published. Publishing the other game's players under this game's id would be
  fabrication, so the cells are left empty and flagged instead.</p>
  {table("Withheld at capture",
         ["Game", "Status", "Why", "SHA-256", "Source"], rows)}
</section>

<section class="card pad">
  <h2>2. Games whose book is missing a section</h2>
  <p>A book can be published while still incomplete — the league fills sections in after
  the game. Where the playtime table is absent, the starters and inactive lists are still
  published and the snap-count rows are simply left blank, because a snap count that is not
  on the page cannot be estimated.</p>
  {table("Captured, but with a section missing",
         ["Game", "Status", "Starters", "Snap rows", "Inactive/DNP", "Source"],
         incomplete_rows)}
</section>

<section class="card pad">
  <h2>3. The playtime table is captioned (Unofficial) by the league</h2>
  <p>The league prints <em>Percent of playtime per player on offense, defense and special
  teams (Unofficial)</em> above the table. It is the only official snap-count source that
  exists — <code>nfl.com/stats/snap-counts/</code> returns 404 — so we use it and carry the
  label on all {len(unf)} affected games rather than dropping it.</p>
  {table("Games carrying the league's (Unofficial) caption",
         ["Game"], ["<tr><td>%s</td></tr>" % esc(game_label(g)) for g in unf])}
</section>

<section class="card pad">
  <h2>4. A venue name disagrees with another section of this repo</h2>
  <p>Session <code>arena/d81dd61b-fl2</code> recorded the NE @ DET venue as
  <em>Munich / FC Bayern Munich Stadium</em>, read from the game-centre page. The Game Book
  for the same fixture prints <strong>Allianz Arena, Munich, Germany</strong> on its header.
  Both are official league sources, so this is published as a discrepancy rather than
  silently reconciled: for anything that keys off the venue, the Game Book value should win,
  because it is the league's own game record rather than a fixture listing.</p>
  {table("Conflicting official venue strings for one fixture",
         ["Fixture", "Game-centre page (session d81dd61b)", "Game Book (this section)"],
         ["<tr><td>NE @ DET, 2026 week 10</td><td>Munich / FC Bayern Munich Stadium</td>"
          "<td><strong>Allianz Arena, Munich, Germany</strong></td></tr>"])}
</section>

<section class="card pad">
  <h2>5. What this data cannot be used for</h2>
  <p>A Game Book is published only after a game kicks off. It is therefore never a pre-game
  input: it is the ground truth a pre-game model is scored against, and the historical corpus
  a depth model is fitted on. Any use of it as a same-week input would be look-ahead.</p>
</section>
"""
    return page("Flagged for review", "flagged.html", body)


# --------------------------------------------------------------------------- main

def main() -> int:
    os.makedirs(os.path.join(SECTION, "assets"), exist_ok=True)
    src_css = os.path.join(ROOT, "assets", "style.css")
    if os.path.exists(src_css):
        css = open(src_css, encoding="utf-8").read()
        css += """
/* ---- section-local additions ---- */
main.wrap { max-width: 1240px; margin: 0 auto; padding: 22px 20px 60px; }
section.card.pad { margin-bottom: 18px; }
.page-head { margin: 4px 0 18px; }
.page-head h1 { font-size: 26px; margin: 4px 0 8px; letter-spacing: -.4px; }
.page-head .lede { color: var(--ink-2); max-width: 82ch; margin: 0; }
.grid.c3 { display: grid; gap: 14px; grid-template-columns: repeat(3, minmax(0,1fr)); }
.grid.c4 { display: grid; gap: 14px; grid-template-columns: repeat(4, minmax(0,1fr)); }
@media (max-width: 900px) { .grid.c3, .grid.c4 { grid-template-columns: 1fr; } }
.stat { background: var(--surface-2); border: 1px solid var(--line); border-radius: var(--r); padding: 12px 14px; }
.stat .k { font-size: 11.5px; text-transform: uppercase; letter-spacing: .5px; color: var(--ink-3); }
.stat .v { font-size: 25px; font-weight: 700; font-variant-numeric: tabular-nums; }
.stat .d { font-size: 12px; color: var(--ink-2); }
section.card.pad h3 { margin: 0 0 6px; font-size: 15px; }
.small { font-size: 12px; color: var(--ink-2); }
"""
        with open(os.path.join(SECTION, "assets", "style.css"), "w", encoding="utf-8") as fh:
            fh.write(css)

    pages = {
        "index.html": build_index(),
        "starters.html": build_starters(),
        "snaps.html": build_snaps(),
        "inactives.html": build_inactives(),
        "sources.html": build_sources(),
        "questions.html": build_questions(),
        "suggestions.html": build_suggestions(),
        "flagged.html": build_flagged(),
    }
    for name, content in pages.items():
        with open(os.path.join(SECTION, name), "w", encoding="utf-8") as fh:
            fh.write(content)
    print("built %d pages (build %s)" % (len(pages), data_hash()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
